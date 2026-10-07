"""Specification RAG for NHID-Clinical.

Answers questions from the repository docs. It does not evaluate a call,
does not replace the policy engine, and does not certify conformance.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
INDEX = ROOT / "data" / "spec_rag_index.json"
LOG = ROOT / "logs" / "spec_rag.jsonl"
REFUSAL = "the corpus does not contain the answer"
CHUNK = 800
OVERLAP = 100
DIM = 256

router = APIRouter(prefix="/spec", tags=["spec-rag"])


class SpecQuestion(BaseModel):
    question: str


def _chunks(text: str):
    text = text.strip()
    start = 0
    while start < len(text):
        piece = text[start : start + CHUNK].strip()
        if piece:
            yield piece
        if start + CHUNK >= len(text):
            break
        start += CHUNK - OVERLAP


def _local(text: str) -> list[float]:
    vec = [0.0] * DIM
    for token in text.lower().split():
        digest = hashlib.sha256(token.encode()).digest()
        vec[int.from_bytes(digest[:2], "big") % DIM] += 1.0 if digest[2] % 2 == 0 else -1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _embed(texts: list[str]) -> list[list[float]]:
    if not os.getenv("OPENAI_API_KEY"):
        return [_local(t) for t in texts]
    from openai import OpenAI

    client = OpenAI()
    out: list[list[float]] = []
    for i in range(0, len(texts), 64):
        batch = texts[i : i + 64]
        response = client.embeddings.create(model="text-embedding-3-small", input=batch)
        out.extend(item.embedding for item in response.data)
    return out


def build_index() -> int:
    records, docs = [], []
    for path in sorted(DOCS.rglob("*.md")):
        if path.stat().st_size > 200_000:
            continue
        for i, chunk in enumerate(_chunks(path.read_text(encoding="utf-8", errors="ignore"))):
            docs.append(chunk)
            records.append({"source": str(path.relative_to(ROOT)), "text": chunk, "chunk": i})
    vectors = _embed(docs)
    for record, vector in zip(records, vectors):
        record["embedding"] = vector
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    INDEX.write_text(json.dumps({"chunks": records}), encoding="utf-8")
    return len(records)


def _load() -> list[dict]:
    if not INDEX.exists():
        build_index()
    return json.loads(INDEX.read_text(encoding="utf-8"))["chunks"]


def retrieve(question: str, k: int = 4) -> list[dict]:
    records = _load()
    vector = _embed([question])[0]
    terms = {t.strip(".,:;?()").lower() for t in question.split() if len(t) > 2}
    ids = set(re.findall(r"[a-z]{2,}-\d+", question.lower()))
    scored = []
    for record in records:
        cosine = sum(a * b for a, b in zip(vector, record["embedding"]))
        text = record["text"].lower()
        overlap = len(terms & set(text.split())) / (len(terms) or 1)
        ident = 2.0 if ids and all(i in text for i in ids) else 0.0
        scored.append((cosine + overlap + ident, record))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [
        {"source": r["source"], "text": r["text"], "score": round(s, 4)}
        for s, r in scored[:k]
    ]


def answer(question: str, hits: list[dict]) -> dict:
    citations = [{"source": h["source"], "score": h["score"]} for h in hits]
    if not os.getenv("OPENAI_API_KEY"):
        terms = [t for t in question.lower().split() if len(t) > 3]
        best = max(hits, key=lambda h: sum(t in h["text"].lower() for t in terms), default=None)
        overlap = sum(t in best["text"].lower() for t in terms) if best else 0
        text = REFUSAL if overlap < 2 or not best else f"{' '.join(best['text'].split())[:500]} (source: {best['source']})"
        return {"answer": text, "citations": citations, "refused": text == REFUSAL}
    from openai import OpenAI

    excerpts = "\n\n".join(f"[{h['source']}] {h['text']}" for h in hits)
    response = OpenAI().chat.completions.create(
        model=os.getenv("CHAT_MODEL", "gpt-4o-mini"),
        temperature=0,
        messages=[
            {"role": "system", "content": "Answer only from the NHID-Clinical excerpts. If they do not contain the answer, say exactly: the corpus does not contain the answer. Cite the source path."},
            {"role": "user", "content": f"Excerpts:\n{excerpts}\n\nQuestion: {question}"},
        ],
    )
    text = (response.choices[0].message.content or "").strip()
    return {"answer": text, "citations": citations, "refused": REFUSAL in text.lower()}


@router.get("/health")
def spec_health():
    count = len(_load()) if INDEX.exists() else 0
    return {"status": "ok", "chunks": count, "scope": "NHID-Clinical docs only"}


@router.post("/ask")
def spec_ask(body: SpecQuestion):
    hits = retrieve(body.question)
    result = answer(body.question, hits)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"ts": datetime.now(timezone.utc).isoformat(), "question": body.question, "sources": [h["source"] for h in hits], "refused": result["refused"]}) + "\n")
    return result


if __name__ == "__main__":
    print(f"indexed {build_index()} chunks")
