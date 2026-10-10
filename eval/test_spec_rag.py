"""Tests for the specification RAG reading aid.

Covers the three behaviours a reader depends on: the index reports its own
size, an in-corpus question comes back with a citation, and a question the
corpus cannot answer is refused in those exact words rather than answered
approximately.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src import nhid_spec_rag as rag  # noqa: E402

fastapi_testclient = pytest.importorskip("fastapi.testclient")


@pytest.fixture(scope="module")
def index():
    return rag.load_index()


@pytest.fixture(scope="module")
def client():
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(rag.router)
    rag.reset_index_cache()
    return fastapi_testclient.TestClient(app)


# ── health ───────────────────────────────────────────────────────────────────

def test_health_reports_chunk_count(client):
    response = client.get("/spec/health")
    assert response.status_code == 200
    body = response.json()

    assert body["status"] == "ok"
    assert isinstance(body["chunks"], int) and body["chunks"] > 0
    assert isinstance(body["sources"], int) and body["sources"] > 0
    assert body["backend"] in ("local", "openai")
    # The disclaimer is part of the contract, not decoration: this endpoint is
    # the first thing an integrator reads.
    assert "not the policy engine" in body["note"].lower()


def test_health_declares_whether_the_score_is_the_openai_score(client):
    body = client.get("/spec/health").json()
    assert body["score_is_openai_score"] == (body["backend"] == "openai")


def test_excluded_files_are_reported_with_a_reason(client):
    """An excluded file must be named *and* say why, not silently dropped."""
    body = client.get("/spec/health").json()
    skipped = {s["source"] for s in body["skipped_files"]}
    assert skipped, "the corpus has known exclusions; an empty list means they went quiet"
    for entry in body["skipped_files"]:
        assert entry["reason"]
        if entry["reason"] == "over the size cap":
            assert entry["bytes"] > rag.MAX_FILE_BYTES
    # Every indexed file is under the cap and not itself an exclusion.
    for path in rag.iter_corpus_files():
        assert path.stat().st_size <= rag.MAX_FILE_BYTES
        assert str(path.relative_to(REPO_ROOT)) not in skipped


def test_the_aid_does_not_index_its_own_documentation(client):
    """Found by running the eval, not by reading the code.

    docs/spec-rag.md quotes "What is NHID-Clinical's HIPAA certification
    number?" verbatim, in the passage explaining why that question must be
    refused. Indexed, that passage covers the question's vocabulary perfectly
    and the refusal collapses: the write-up of the failure mode becomes its
    cause. Refusals went 5/5 to 4/5 the moment the write-up landed in docs/.
    """
    indexed = {p.name for p in rag.iter_corpus_files()}
    assert "spec-rag.md" not in indexed
    assert (rag.CORPUS_DIR / "spec-rag.md").is_file(), \
        "the exclusion is only meaningful while the file exists"

    reasons = {s["source"]: s["reason"] for s in client.get("/spec/health").json()["skipped_files"]}
    assert reasons.get("docs/spec-rag.md") == "this module's own documentation"

    body = client.post("/spec/ask", json={
        "question": "What is NHID-Clinical's HIPAA certification number?",
    }).json()
    assert body["refused"] is True
    assert "docs/spec-rag.md" not in body["citations"]


# ── an in-corpus question ────────────────────────────────────────────────────

def test_in_corpus_question_answers_with_a_citation(client):
    response = client.post("/spec/ask", json={
        "question": "What is the pass condition for PDX-01?",
    })
    assert response.status_code == 200
    body = response.json()

    assert body["refused"] is False
    assert body["answer"] != rag.REFUSAL
    assert body["citations"], "an answered question must cite something"
    for citation in body["citations"]:
        assert citation.startswith("docs/")
        assert (REPO_ROOT / citation).is_file()
        # Every claim carries its source inline, so the path appears in the
        # answer body and not only in the citations list.
        assert citation in body["answer"]


def test_control_id_in_the_question_boosts_matching_chunks(index):
    hits = rag.retrieve(index, "What does ATR-01 require?")
    assert hits
    boosted = [h for h in hits if h.control_boost > 0]
    assert boosted, "a question naming a control should boost chunks mentioning it"
    for hit in boosted:
        assert "ATR-01" in hit.chunk.text.upper()


# ── a refusal ────────────────────────────────────────────────────────────────

def test_out_of_corpus_question_is_refused_exactly(client):
    response = client.post("/spec/ask", json={
        "question": "What was the outcome of the Battle of Austerlitz?",
    })
    assert response.status_code == 200
    body = response.json()

    assert body["refused"] is True
    assert body["answer"] == "the corpus does not contain the answer"
    assert body["citations"] == []


def test_refuses_a_certification_question_rather_than_implying_one(client):
    """The failure mode that matters most for this project.

    "HIPAA", "certification" and "number" each appear somewhere in docs/, so a
    retriever pooling four chunks will cover the question's vocabulary and
    answer — citing documents that together imply a certification that does
    not exist. Grounding in a single passage is what prevents it.
    """
    body = client.post("/spec/ask", json={
        "question": "What is NHID-Clinical's HIPAA certification number?",
    }).json()
    assert body["refused"] is True
    assert body["answer"] == rag.REFUSAL


# ── chunking and logging ─────────────────────────────────────────────────────

def test_chunks_are_800_chars_with_100_overlap():
    text = "".join(f"{i:04d}-----" for i in range(400))  # 4000 chars, no spaces
    pieces = rag.chunk_text(text)
    assert all(len(p) <= rag.CHUNK_CHARS for p in pieces)
    assert len(pieces[0]) == rag.CHUNK_CHARS
    # The tail of one chunk is the head of the next.
    overlap = rag.CHUNK_OVERLAP
    assert pieces[0][-overlap:] == pieces[1][:overlap]


def test_chunks_record_source_and_index(index):
    assert index.chunks
    for chunk in index.chunks[:20]:
        assert chunk.source.startswith("docs/")
        assert isinstance(chunk.index, int) and chunk.index >= 0
    first = [c for c in index.chunks if c.source == index.chunks[0].source]
    assert [c.index for c in first] == list(range(len(first)))


def test_ask_is_logged_without_secrets(client, tmp_path, monkeypatch):
    log = tmp_path / "spec_rag.jsonl"
    monkeypatch.setattr(rag, "LOG_PATH", log)
    monkeypatch.setenv("OPENAI_API_KEY_PROBE", "sk-should-never-be-logged")

    client.post("/spec/ask", json={"question": "What is the enforcement ladder?"})

    lines = [l for l in log.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert set(entry) == {"timestamp", "question", "sources", "refused"}
    assert entry["question"] == "What is the enforcement ladder?"
    assert isinstance(entry["refused"], bool)
    # No credential, and no document body, reaches the log.
    blob = lines[0]
    assert "sk-" not in blob
    for key in ("OPENAI_API_KEY", "embedding", "api_key"):
        assert key not in blob


def test_local_backend_is_deterministic_across_processes():
    """The hashed embedding must not use Python's per-process salted hash()."""
    first = rag.embed_local(["IDG-01 identity disclosure gate"])[0]
    second = rag.embed_local(["IDG-01 identity disclosure gate"])[0]
    assert first == second
    assert abs(sum(v * v for v in first) - 1.0) < 1e-9  # L2-normalised


def test_empty_question_refuses_rather_than_matching_everything(index):
    result = rag.ask(index, "   ")
    assert result.refused is True
    assert result.answer == rag.REFUSAL
