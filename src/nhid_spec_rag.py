"""
nhid_spec_rag.py — a reading aid for the specification corpus in ``docs/``.

WHAT THIS IS NOT
----------------
This is **not the policy engine**. It does not evaluate a call, it does not
produce a control decision, and nothing it returns is a conformance result or a
certification of anything. ``src/nhid_policy_engine_v1.py`` is the engine; the
controls it implements (IDG-01, PDX-01, DBC-01, EIT-01, ATR-01) are what decide
whether an interaction passed. This module only helps a human find the passage
in ``docs/`` that says what a control is supposed to do.

An answer from here is a quotation with a file path attached. It carries exactly
the authority of the document it came from, and no more. If the corpus is wrong,
this will faithfully repeat the error.

WHAT IT DOES
------------
Reads ``docs/*.md`` (top level, skipping any file over 200 KB), splits each into
800-character chunks with 100 characters of overlap, embeds them, and answers a
question by quoting the retrieved text back with citations. When the retrieved
excerpts do not contain the answer it says so, in those words, rather than
assembling something plausible from adjacent material.

EMBEDDING BACKENDS
------------------
``openai``  — ``text-embedding-3-small``, used when ``OPENAI_API_KEY`` is set.
``local``   — a deterministic hashed bag-of-words. No network, no key, and
              **not semantically comparable to the OpenAI score**: it matches
              words, not meaning, so a question phrased differently from the
              document will score worse than it deserves. Every surface that
              reports a score says which backend produced it.

The local backend exists so the index builds, the tests run and the eval
reproduces on a machine with no API key. It is a fallback, not a second opinion.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
from collections import Counter
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

# ── Corpus and chunking ──────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = REPO_ROOT / "docs"
INDEX_PATH = REPO_ROOT / ".spec_rag_index.json"
LOG_PATH = REPO_ROOT / "logs" / "spec_rag.jsonl"

# Files above this are skipped whole rather than truncated. A half-read
# document is worse than an absent one: it answers confidently from the part
# that happened to fit. `docs/MASTER-KNOWLEDGE-ARCHIVE.md` is the only file in
# the corpus this currently excludes, and `GET /spec/health` reports it.
MAX_FILE_BYTES = 200 * 1024

# This module's own documentation lives in the corpus directory, and indexing it
# makes the aid answer questions *about itself* as though they were answers from
# the specification. That is not hypothetical: docs/spec-rag.md quotes the
# question "What is NHID-Clinical's HIPAA certification number?" verbatim, in the
# passage explaining why that question must be refused. Indexed, that passage
# covers the question's vocabulary perfectly (coverage 1.0) and the refusal
# collapses — the write-up of the failure mode becomes the thing that causes it.
# A reading aid for the specification does not read its own manual.
SELF_DOCUMENTATION = ("spec-rag.md",)

CHUNK_CHARS = 800
CHUNK_OVERLAP = 100

CONTROL_IDS = ("IDG-01", "PDX-01", "DBC-01", "EIT-01", "ATR-01")

# Dimensionality of the local hashed embedding. 1024 keeps collisions rare
# across a corpus this size while staying cheap to cosine in pure Python.
LOCAL_DIM = 1024

OPENAI_MODEL = "text-embedding-3-small"

TOP_K = 4

# Blend weights for the retrieval score. Cosine carries most of it; token
# overlap is kept as an independent term because it survives an embedding that
# has drifted or been built by the other backend.
W_COSINE = 0.60
W_OVERLAP = 0.40

# Added once when a control id named in the question also appears in the chunk.
# Deliberately large enough to reorder near-ties and too small to float an
# otherwise irrelevant chunk into the top 4.
CONTROL_BOOST = 0.15

# A question is answered only when the retrieved excerpts cover enough of its
# distinctive vocabulary. Coverage is IDF-weighted, so a question hinging on a
# word that appears nowhere in the corpus ("valuation", "Austerlitz") fails
# even when its common words all match. See `_coverage` for the rationale.
MIN_COVERAGE = 0.55
MIN_TOP_SCORE = 0.18

REFUSAL = "the corpus does not contain the answer"

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9\-_.]*")

# Short function words carry no retrieval signal and distort IDF coverage:
# without them a question is mostly its content, which is what should have to
# match.
_STOPWORDS = frozenset("""
a an the and or but if then than that this these those of in on at to for from
by with without as is are was were be been being do does did doing have has had
having it its it's they them their there here what which who whom whose when
where why how all any both each few more most other some such no nor not only
own same so too very can will just should now about into over under again
further once i me my we our you your he him his she her
""".split())


def _tokens(text: str) -> List[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS]


@dataclass
class Chunk:
    source: str          # repo-relative path, e.g. "docs/terminology.md"
    index: int           # 0-based position of this chunk within its source
    text: str
    embedding: List[float] = field(default_factory=list)

    @property
    def chunk_id(self) -> str:
        return f"{self.source}#{self.index}"


def iter_corpus_files() -> List[Path]:
    """Top-level ``docs/*.md``, sorted, excluding oversized files and this
    module's own documentation (see ``SELF_DOCUMENTATION``)."""
    if not CORPUS_DIR.is_dir():
        return []
    return [
        p for p in sorted(CORPUS_DIR.glob("*.md"))
        if p.stat().st_size <= MAX_FILE_BYTES and p.name not in SELF_DOCUMENTATION
    ]


def skipped_files() -> List[Dict[str, Any]]:
    """Files excluded by the size cap, reported rather than silently dropped."""
    if not CORPUS_DIR.is_dir():
        return []
    out = [
        {"source": str(p.relative_to(REPO_ROOT)), "bytes": p.stat().st_size,
         "reason": "over the size cap"}
        for p in sorted(CORPUS_DIR.glob("*.md"))
        if p.stat().st_size > MAX_FILE_BYTES
    ]
    out += [
        {"source": str(p.relative_to(REPO_ROOT)), "bytes": p.stat().st_size,
         "reason": "this module's own documentation"}
        for p in sorted(CORPUS_DIR.glob("*.md"))
        if p.stat().st_size <= MAX_FILE_BYTES and p.name in SELF_DOCUMENTATION
    ]
    return out


def chunk_text(text: str) -> List[str]:
    """Fixed 800-character windows with 100 characters of overlap.

    Fixed-width rather than paragraph-aware on purpose: the corpus mixes prose,
    tables and fenced code, and a splitter tuned for one mangles the others.
    The overlap is what stops a definition that straddles a boundary from being
    invisible to both neighbours.
    """
    if not text:
        return []
    stride = CHUNK_CHARS - CHUNK_OVERLAP
    out: List[str] = []
    pos = 0
    while pos < len(text):
        piece = text[pos:pos + CHUNK_CHARS]
        if piece.strip():
            out.append(piece)
        if pos + CHUNK_CHARS >= len(text):
            break
        pos += stride
    return out


def build_chunks() -> List[Chunk]:
    chunks: List[Chunk] = []
    for path in iter_corpus_files():
        rel = str(path.relative_to(REPO_ROOT))
        body = path.read_text(encoding="utf-8", errors="replace")
        for i, piece in enumerate(chunk_text(body)):
            chunks.append(Chunk(source=rel, index=i, text=piece))
    return chunks


# ── Embedding ────────────────────────────────────────────────────────────────

def active_backend() -> str:
    """``openai`` when a key is present, otherwise ``local``."""
    return "openai" if os.environ.get("OPENAI_API_KEY", "").strip() else "local"


def _l2_normalise(vec: List[float]) -> List[float]:
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0.0:
        return vec
    return [v / norm for v in vec]


def embed_local(texts: Sequence[str]) -> List[List[float]]:
    """Deterministic hashed bag-of-words. Lexical, not semantic.

    Each token is hashed to a bucket with a stable digest — not Python's
    ``hash()``, which is salted per process and would make the index
    irreproducible between runs.
    """
    vectors: List[List[float]] = []
    for text in texts:
        vec = [0.0] * LOCAL_DIM
        counts = Counter(_tokens(text))
        for token, n in counts.items():
            digest = hashlib.sha1(token.encode("utf-8")).digest()
            bucket = int.from_bytes(digest[:4], "big") % LOCAL_DIM
            sign = 1.0 if digest[4] & 1 else -1.0
            # Sublinear term frequency: a word repeated twenty times in one
            # chunk should not dominate the vector twenty-fold.
            vec[bucket] += sign * (1.0 + math.log(n))
        vectors.append(_l2_normalise(vec))
    return vectors


def embed_openai(texts: Sequence[str], *, batch: int = 128) -> List[List[float]]:
    """``text-embedding-3-small`` via the REST API.

    Uses httpx directly rather than the ``openai`` package so this module has
    one fewer import to break; httpx is already a hard dependency of the test
    client.
    """
    import httpx

    key = os.environ["OPENAI_API_KEY"].strip()
    out: List[List[float]] = []
    with httpx.Client(timeout=60.0) as client:
        for start in range(0, len(texts), batch):
            window = list(texts[start:start + batch])
            response = client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {key}"},
                json={"model": OPENAI_MODEL, "input": window},
            )
            response.raise_for_status()
            payload = response.json()
            # The API documents order preservation, but the index is only
            # correct if that holds, so sort by the returned index rather than
            # trusting arrival order.
            rows = sorted(payload["data"], key=lambda d: d["index"])
            out.extend(_l2_normalise(r["embedding"]) for r in rows)
    return out


def embed(texts: Sequence[str]) -> Tuple[List[List[float]], str]:
    backend = active_backend()
    if backend == "openai":
        return embed_openai(texts), backend
    return embed_local(texts), backend


# ── Index ────────────────────────────────────────────────────────────────────

@dataclass
class Index:
    chunks: List[Chunk]
    backend: str
    built_at: float
    idf: Dict[str, float] = field(default_factory=dict)
    skipped: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def chunk_count(self) -> int:
        return len(self.chunks)

    @property
    def source_count(self) -> int:
        return len({c.source for c in self.chunks})


def _compute_idf(chunks: Sequence[Chunk]) -> Dict[str, float]:
    """Inverse document frequency over chunks, used for refusal scoring.

    A question's rare words are the ones that say what it is actually asking.
    Weighting coverage by IDF is what separates "this corpus discusses HIPAA"
    from "this corpus states a HIPAA certification number" — the second hinges
    on a word the corpus never uses in that sense, and that absence has to
    outweigh the topical words that do match.
    """
    n = max(len(chunks), 1)
    seen = Counter()
    for c in chunks:
        for token in set(_tokens(c.text)):
            seen[token] += 1
    return {tok: math.log(n / df) for tok, df in seen.items()}


def idf_of(index: Index, token: str) -> float:
    """IDF for a token, with unseen tokens scored at the ceiling.

    A word absent from the whole corpus is maximally informative about what
    the corpus cannot answer, so it must not score zero.
    """
    ceiling = math.log(max(len(index.chunks), 1) / 1)
    return index.idf.get(token, ceiling)


def build_index(*, verbose: bool = True) -> Index:
    chunks = build_chunks()
    if not chunks:
        raise RuntimeError(f"no markdown found under {CORPUS_DIR}")

    vectors, backend = embed([c.text for c in chunks])
    for chunk, vec in zip(chunks, vectors):
        chunk.embedding = vec

    index = Index(
        chunks=chunks,
        backend=backend,
        built_at=time.time(),
        idf=_compute_idf(chunks),
        skipped=skipped_files(),
    )
    save_index(index)

    if verbose:
        print(f"indexed {index.chunk_count} chunks from {index.source_count} files "
              f"in {CORPUS_DIR.relative_to(REPO_ROOT)}/")
        for s in index.skipped:
            detail = (f"{s['bytes']:,} bytes > {MAX_FILE_BYTES:,}"
                      if s["reason"] == "over the size cap" else s["reason"])
            print(f"  skipped {s['source']} ({detail})")
        print(f"  embedding backend: {backend}")
        if backend == "local":
            print("  NOTE: the local hashed backend matches words, not meaning. "
                  "This score is NOT the OpenAI score — set OPENAI_API_KEY to use "
                  f"{OPENAI_MODEL}.")
        print(f"  index written to {INDEX_PATH.relative_to(REPO_ROOT)}")
    return index


def save_index(index: Index) -> None:
    INDEX_PATH.write_text(json.dumps({
        "backend": index.backend,
        "built_at": index.built_at,
        "idf": index.idf,
        "skipped": index.skipped,
        "chunks": [asdict(c) for c in index.chunks],
    }), encoding="utf-8")


def load_index(*, rebuild_if_missing: bool = True) -> Index:
    if not INDEX_PATH.exists():
        if not rebuild_if_missing:
            raise FileNotFoundError(f"{INDEX_PATH} missing; run python -m src.nhid_spec_rag")
        return build_index(verbose=False)
    raw = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    return Index(
        chunks=[Chunk(**c) for c in raw["chunks"]],
        backend=raw["backend"],
        built_at=raw["built_at"],
        idf=raw.get("idf", {}),
        skipped=raw.get("skipped", []),
    )


# ── Retrieval ────────────────────────────────────────────────────────────────

def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))  # both sides are L2-normalised


def token_overlap(question_tokens: Sequence[str], chunk_text_: str) -> float:
    """Fraction of the question's distinct content words present in the chunk."""
    q = set(question_tokens)
    if not q:
        return 0.0
    return len(q & set(_tokens(chunk_text_))) / len(q)


def controls_in(text: str) -> List[str]:
    upper = text.upper()
    return [cid for cid in CONTROL_IDS if cid in upper]


@dataclass
class Hit:
    chunk: Chunk
    score: float
    cosine: float
    overlap: float
    control_boost: float


def retrieve(index: Index, question: str, k: int = TOP_K) -> List[Hit]:
    q_tokens = _tokens(question)
    q_controls = set(controls_in(question))

    if index.backend == "openai":
        q_vec = embed_openai([question])[0]
    else:
        q_vec = embed_local([question])[0]

    hits: List[Hit] = []
    for chunk in index.chunks:
        cos = cosine(q_vec, chunk.embedding)
        ov = token_overlap(q_tokens, chunk.text)
        boost = CONTROL_BOOST if (q_controls & set(controls_in(chunk.text))) else 0.0
        hits.append(Hit(
            chunk=chunk,
            score=W_COSINE * cos + W_OVERLAP * ov + boost,
            cosine=cos,
            overlap=ov,
            control_boost=boost,
        ))

    hits.sort(key=lambda h: (-h.score, h.chunk.source, h.chunk.index))
    return hits[:k]


# ── Answering ────────────────────────────────────────────────────────────────

def _coverage(index: Index, question: str, hits: Sequence[Hit]) -> float:
    """Best single-chunk IDF-weighted coverage of the question's content words.

    Deliberately the maximum over chunks, not the union of them. Pooling the
    four retrieved chunks lets unrelated documents each contribute a different
    word and add up to a passing score: "What is NHID-Clinical's HIPAA
    certification number?" scored 0.70 pooled, because *HIPAA* appears in one
    file, *certification* in another and *number* in a third — and it answered,
    citing two documents that together imply a certification the project does
    not have. That is the single worst thing this module could do.

    Requiring one passage to carry the question's distinctive vocabulary is
    also just what grounding means: an answer is a quotation from somewhere,
    not a sentence assembled from four places.

    Returns 0.0 for a question with no content words, which refuses rather
    than matching everything.
    """
    q_tokens = set(_tokens(question))
    if not q_tokens:
        return 0.0
    total = sum(idf_of(index, t) for t in q_tokens)
    if total == 0.0:
        return 0.0
    best = 0.0
    for h in hits:
        present = set(_tokens(h.chunk.text))
        found = sum(idf_of(index, t) for t in q_tokens if t in present)
        best = max(best, found / total)
    return best


_SENTENCE_RE = re.compile(r"(?<=[.;:!?])\s+|\n(?=[-*|#\d])|\n{2,}")


# A passage shorter than this is a fragment — a JSON key, a table cell, a
# stray identifier. It can match the question's words without saying anything,
# so it is not quotable as an answer even when it ranks well.
MIN_PASSAGE_TOKENS = 6


def _best_excerpts(index: Index, question: str, hits: Sequence[Hit],
                   limit: int = 3) -> List[Tuple[str, str]]:
    """Pick the passages inside the retrieved chunks that address the question.

    Returns ``(source, passage)`` pairs. Quoting the chunk whole would bury the
    answer in 800 characters of neighbouring text; quoting nothing would make
    the citation unverifiable. This quotes the fragments that carry the
    question's own words.

    Scored by IDF, not by how many words matched. Counting matches rewards
    whichever fragment is shortest: asked "what does PDX-01 gate?", a bare
    ``"PDX-01",`` from a JSON example scored a perfect density and beat the
    sentence that defines the control. Weighting by IDF and normalising length
    only gently puts the definition back on top, and MIN_PASSAGE_TOKENS drops
    the fragments outright.
    """
    q = set(_tokens(question))
    scored: List[Tuple[float, str, str]] = []
    for h in hits:
        for raw in _SENTENCE_RE.split(h.chunk.text):
            passage = raw.strip()
            if len(passage) < 25:
                continue
            toks = set(_tokens(passage))
            if len(toks) < MIN_PASSAGE_TOKENS:
                continue
            matched = q & toks
            if not matched:
                continue
            weight = sum(idf_of(index, t) for t in matched)
            scored.append((weight / (len(toks) ** 0.35), h.chunk.source, passage))
    scored.sort(key=lambda s: -s[0])

    out: List[Tuple[str, str]] = []
    seen = set()
    for _, source, passage in scored:
        key = passage[:80]
        if key in seen:
            continue
        seen.add(key)
        out.append((source, passage))
        if len(out) >= limit:
            break
    return out


@dataclass
class Answer:
    answer: str
    citations: List[str]
    refused: bool
    backend: str
    coverage: float
    hits: List[Dict[str, Any]] = field(default_factory=list)


def ask(index: Index, question: str, k: int = TOP_K) -> Answer:
    """Answer from the retrieved excerpts, or refuse.

    There is no generative step. The answer is composed of passages lifted from
    the corpus with their source path attached, which is what makes every claim
    checkable — and what makes a refusal honest rather than a failure to
    phrase something.
    """
    question = (question or "").strip()
    hits = retrieve(index, question, k=k) if question else []
    coverage = _coverage(index, question, hits) if hits else 0.0
    top = hits[0].score if hits else 0.0

    hit_rows = [{
        "source": h.chunk.source,
        "chunk": h.chunk.index,
        "score": round(h.score, 4),
        "cosine": round(h.cosine, 4),
        "overlap": round(h.overlap, 4),
        "control_boost": h.control_boost,
    } for h in hits]

    if coverage < MIN_COVERAGE or top < MIN_TOP_SCORE:
        return Answer(
            answer=REFUSAL,
            citations=[],
            refused=True,
            backend=index.backend,
            coverage=round(coverage, 4),
            hits=hit_rows,
        )

    excerpts = _best_excerpts(index, question, hits)
    if not excerpts:
        return Answer(
            answer=REFUSAL, citations=[], refused=True, backend=index.backend,
            coverage=round(coverage, 4), hits=hit_rows,
        )

    # One citation per claim, inline, because a trailing source list lets a
    # reader attach the wrong path to the wrong sentence.
    lines = [f"{passage}  [{source}]" for source, passage in excerpts]
    citations: List[str] = []
    for source, _ in excerpts:
        if source not in citations:
            citations.append(source)

    return Answer(
        answer="\n\n".join(lines),
        citations=citations,
        refused=False,
        backend=index.backend,
        coverage=round(coverage, 4),
        hits=hit_rows,
    )


# ── Logging ──────────────────────────────────────────────────────────────────

def log_ask(question: str, answer: Answer) -> None:
    """Append one line per ask.

    Records the question, which sources were cited and whether it refused —
    enough to audit what the aid was asked and what it pointed at. No API key,
    no embedding, no document body: the log is for reviewing behaviour, not for
    reconstructing the corpus or the credential.
    """
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "question": question,
                "sources": answer.citations,
                "refused": answer.refused,
            }) + "\n")
    except OSError:
        # A read-only or full disk must not turn a successful answer into a
        # 500. The ask is the product; the log is bookkeeping.
        pass


# ── FastAPI router ───────────────────────────────────────────────────────────
#
# Mount it the way main.py mounts every other router:
#
#     import nhid_spec_rag_router           # or: from src import nhid_spec_rag
#     app.include_router(nhid_spec_rag.router, dependencies=[Security(get_api_key)])

try:
    from fastapi import APIRouter
    from pydantic import BaseModel, Field

    router = APIRouter(prefix="/spec", tags=["spec-rag"])

    class AskRequest(BaseModel):
        question: str = Field(..., min_length=1, max_length=2000)

    _INDEX: Optional[Index] = None

    def get_index() -> Index:
        global _INDEX
        if _INDEX is None:
            _INDEX = load_index()
        return _INDEX

    def reset_index_cache() -> None:
        """Drop the cached index. Used by tests after rebuilding."""
        global _INDEX
        _INDEX = None

    @router.get("/health")
    def spec_health() -> Dict[str, Any]:
        idx = get_index()
        return {
            "status": "ok",
            "chunks": idx.chunk_count,
            "sources": idx.source_count,
            "backend": idx.backend,
            "skipped_files": idx.skipped,
            "score_is_openai_score": idx.backend == "openai",
            "note": (
                "Reading aid for docs/. Not the policy engine, not a conformance "
                "result, not a certification."
            ),
        }

    @router.post("/ask")
    def spec_ask(body: AskRequest) -> Dict[str, Any]:
        idx = get_index()
        result = ask(idx, body.question)
        log_ask(body.question, result)
        return {
            "answer": result.answer,
            "citations": result.citations,
            "refused": result.refused,
            "backend": result.backend,
            "coverage": result.coverage,
        }

except ImportError:  # pragma: no cover - FastAPI absent; CLI and eval still work
    router = None  # type: ignore[assignment]


# ── CLI ──────────────────────────────────────────────────────────────────────

def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="python -m src.nhid_spec_rag",
        description="Build the specification index, or ask it a question.",
    )
    parser.add_argument("--ask", metavar="QUESTION",
                        help="query the existing index instead of rebuilding")
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.ask:
        index = load_index()
        if index.backend == "local":
            print(f"[backend=local] lexical hashed embedding — NOT the {OPENAI_MODEL} score.\n")
        result = ask(index, args.ask)
        print(result.answer)
        if result.citations:
            print("\nsources: " + ", ".join(result.citations))
        return 0

    build_index(verbose=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
