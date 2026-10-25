"""
Chunking ablation for the specification reading aid, measured in memory.

Each variant sets the module's switches, builds an index without writing
.spec_rag_index.json, and scores it with the same `evaluate()` the eval runner
uses, so every row is comparable with eval/baseline-local.json. Nothing here is
run in CI; it exists so the table in docs/spec-rag.md can be reproduced.

    python eval/experiments/chunking_ablation.py               # every variant
    python eval/experiments/chunking_ablation.py A H           # some variants
    python eval/experiments/chunking_ablation.py --detail H    # per-question

Variants (local hashed backend unless OPENAI_API_KEY is set):

  A  fixed 800/100 windows, cosine + overlap (Phase 1, the old baseline)
  B  heading-aware chunks, heading path prefixed into the quoted body
  G  heading-aware, heading line out of the body, path scored not quoted,
     stemmed ranking
  K  G with the heading line kept in the body
  N  K with short sections folded, ranking unstemmed
  F  K with sections under 400 chars folded into the previous one (shipped)

Also measured while building Phase 2 and removed because they changed no
number: judging the refusal gate over a chunk's whole section (folded sections
almost always fit in one chunk, so there was nothing to add), and a heading
tie-break in excerpt selection.
"""
from __future__ import annotations

import sys
import time
from contextlib import contextmanager
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "eval"))

import src.nhid_spec_rag as rag  # noqa: E402
from run_spec_rag_eval import evaluate, load_questions  # noqa: E402

MIN = 400

VARIANTS = {
    "A": dict(CHUNKING="fixed", STEM_RANKING=False, HEADING_IN_BODY=False,
              MIN_SECTION_CHARS=0),
    "B": dict(CHUNKING="heading", STEM_RANKING=False, HEADING_IN_BODY=False,
              MIN_SECTION_CHARS=0, _prefix=True),
    "G": dict(CHUNKING="heading", STEM_RANKING=True, HEADING_IN_BODY=False,
              MIN_SECTION_CHARS=0),
    "K": dict(CHUNKING="heading", STEM_RANKING=True, HEADING_IN_BODY=True,
              MIN_SECTION_CHARS=0),
    "N": dict(CHUNKING="heading", STEM_RANKING=False, HEADING_IN_BODY=True,
              MIN_SECTION_CHARS=MIN),
    "F": dict(CHUNKING="heading", STEM_RANKING=True, HEADING_IN_BODY=True,
              MIN_SECTION_CHARS=MIN),
}

SWITCHES = ("CHUNKING", "STEM_RANKING", "HEADING_IN_BODY", "MIN_SECTION_CHARS")


@contextmanager
def configured(settings):
    saved = {k: getattr(rag, k) for k in SWITCHES}
    try:
        for k in SWITCHES:
            setattr(rag, k, settings[k])
        yield
    finally:
        for k, v in saved.items():
            setattr(rag, k, v)


def build_in_memory(settings) -> "rag.Index":
    chunks = rag.build_chunks()
    if settings.get("_prefix"):
        for c in chunks:
            if c.section:
                c.text = f"{c.section}\n{c.text}"
                c.section = ""
    vectors, backend = rag.embed([c.scoring_text for c in chunks])
    for c, v in zip(chunks, vectors):
        c.embedding = v
    return rag.Index(
        chunks=chunks, backend=backend, built_at=time.time(),
        idf=rag._compute_idf(chunks), skipped=rag.skipped_files(),
        corpus_hash=rag.corpus_hash(), commit=rag.repo_commit(),
    )


def q11_rank(index) -> str:
    row = next(r for r in load_questions() if r["id"] == "q11")
    hits = rag.retrieve(index, row["question"], k=len(index.chunks))
    for rank, h in enumerate(hits, 1):
        if h.chunk.source == row["expected_source"]:
            return str(rank)
    return "-"


def run(name):
    settings = VARIANTS[name]
    with configured(settings):
        index = build_in_memory(settings)
        report = evaluate(index, load_questions())
        report["q11_rank"] = q11_rank(index)
    return report


def main(argv) -> int:
    detail = "--detail" in argv
    names = [a for a in argv if not a.startswith("--")] or list(VARIANTS)
    rows = []
    for name in names:
        r = run(name)
        rows.append((name, r))
        if detail:
            print(f"\n== {name}")
            for q in r["per_question"]:
                if q["answerable"]:
                    state = "pass" if q["passage_hit"] else ("REFUSED" if q["refused"] else "wrongpsg")
                    print(f"  {q['id']}  rank={q['rank']}  cov={q['coverage']}  {state}")
                elif not q["refused"]:
                    print(f"  {q['id']}  ANSWERED cov={q['coverage']}  {q['cited']}")
    print(f"\nbackend: {rows[0][1]['backend']}   commit: {rows[0][1]['commit']}\n")
    print("| Variant | chunks | file | accepted | passage | MRR | refusals | unsupported | q11 rank |")
    print("| :-- | --: | :-- | :-- | :-- | :-- | :-- | :-- | :-- |")
    for name, r in rows:
        a, u = r["answerable"], r["unanswerable"]
        print(f"| {name} | {r['chunks']} | {r['file_hits']}/{a} | {r['accepted_hits']}/{a} | "
              f"{r['passage_hits']}/{a} | {r['mrr']:.2f} | {r['refusals']}/{u} | "
              f"{r['unsupported_answers']} | {r['q11_rank']} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
