"""Tests for the specification RAG reading aid.

Covers the three behaviours a reader depends on: the index reports its own
size, an in-corpus question comes back with a citation, and a question the
corpus cannot answer is refused in those exact words rather than answered
approximately.
"""
from __future__ import annotations

import json
import os
import re
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


def test_the_fixed_width_splitter_is_still_the_fallback_not_the_default():
    assert rag.CHUNKING == "heading"


_DOC = """Preamble line before any heading, long enough to stand as its own section.

# Title

Intro paragraph under the title. """ + ("Words about the title section. " * 20) + """

## Alert Thresholds

| Metric | Threshold (Alert) | Action |
| --- | --- | --- |
| False-positive rate | > 0.2% | Review |

```bash
# this is a shell comment, not a heading
echo ok
```
""" + ("More words inside the alert thresholds section. " * 15) + """

### Future Compliance

- HITRUST CSF certification

## Long section

""" + ("A sentence that keeps going so the section must be windowed. " * 60)


def test_no_chunk_spans_two_headings():
    for body, _ in rag.chunk_document(_DOC, min_chars=0):
        headings, in_fence = [], False
        for ln in body.splitlines():
            if ln.startswith("```"):
                in_fence = not in_fence
            elif not in_fence and re.match(r"^#{1,6} ", ln):
                headings.append(ln)
        # at most one heading line, and only as the first line of the body
        assert len(headings) <= 1
        if headings:
            assert body.splitlines()[0] == headings[0]


def test_a_hash_inside_a_code_fence_is_not_a_heading():
    paths = [path for _, path in rag.chunk_document(_DOC, min_chars=0)]
    assert not any("shell comment" in p for p in paths)
    alert = [b for b, p in rag.chunk_document(_DOC, min_chars=0)
             if p == "Title > Alert Thresholds"]
    assert alert and "# this is a shell comment" in alert[0]


def test_the_heading_path_is_carried_and_the_heading_line_kept():
    pieces = rag.chunk_document(_DOC, min_chars=0)
    paths = [p for _, p in pieces]
    assert paths[0] == ""                       # the preamble
    assert "Title > Alert Thresholds" in paths
    assert "Title > Alert Thresholds > Future Compliance" in paths
    body = dict((p, b) for b, p in pieces)["Title > Alert Thresholds"]
    assert body.startswith("## Alert Thresholds")


def test_a_short_section_is_folded_into_the_one_before_it():
    folded = rag.chunk_document(_DOC, min_chars=400)
    paths = [p for _, p in folded]
    assert "Title > Alert Thresholds > Future Compliance" not in paths
    alert = dict((p, b) for b, p in folded)["Title > Alert Thresholds"]
    assert "HITRUST CSF certification" in alert


def test_a_long_section_is_capped_inside_itself_on_word_boundaries():
    long_pieces = [b for b, p in rag.chunk_document(_DOC, min_chars=0)
                   if p == "Title > Long section"]
    assert len(long_pieces) > 1
    assert all(len(b) <= rag.SECTION_CAP for b in long_pieces)
    source = _DOC
    for b in long_pieces[1:]:
        at = source.index(b[:60])
        assert source[at - 1].isspace()          # starts on a word boundary
    # consecutive windows overlap
    assert long_pieces[0][-40:].split()[-1] in long_pieces[1]


def test_stemming_is_for_ranking_and_never_reaches_the_gate():
    assert rag._stem("milestones") == rag._stem("milestone")
    assert rag._stem("mapping") == rag._stem("map") == "map"
    assert rag._stem("policies") == "policy"
    assert rag._stem("process") == "process"
    assert rag._stem("pdx01_phi_gate_triggered") == "pdx01_phi_gate_triggered"
    # The refusal gate reads unstemmed words: "milestones" asserts itself only.
    assert "milestones" in rag.asserted_tokens("Mapped per conformance milestones and events")
    assert "mileston" not in rag.asserted_tokens("Mapped per conformance milestones and events")


def test_a_heading_line_is_scored_but_never_quoted(index):
    for chunk in index.chunks:
        if chunk.text.startswith("#") and chunk.section:
            hit = rag.Hit(chunk=chunk, score=1.0, cosine=1.0, overlap=1.0,
                          control_boost=0.0)
            question = chunk.text.splitlines()[0].lstrip("# ")
            for _, passage in rag._best_excerpts(index, question, [hit]):
                assert not passage.startswith("#")
            break
    else:
        pytest.fail("no chunk starts with its heading line")


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


# ── a denial is not evidence ─────────────────────────────────────────────────

def test_a_negated_clause_asserts_nothing():
    """The failure of 2026-10-25: a footer saying "Nothing here claims ... HIPAA
    certification" covered the question "What is the HIPAA certification
    number?" at 0.69 and the aid answered it. The same sentence, hard-wrapped
    across lines the way the markdown is, must still read as one denial."""
    denial = ("*NHID-Clinical is an independent research project. Nothing\n"
              "here claims production deployment, healthcare-provider adoption, "
              "HIPAA certification or\nindependent validation.*")
    asserted = rag.asserted_tokens(denial)
    assert "certification" not in asserted
    assert "hipaa" not in asserted
    assert "deployment" not in asserted
    # The first sentence is an assertion and keeps its words.
    assert "independent" in asserted and "research" in asserted


def test_an_assertion_keeps_its_words_and_a_list_item_is_its_own_clause():
    text = ("Compliant with HIPAA audit trail requirements.\n"
            "- Write once, never modify\n"
            "- No deletion of audit events\n"
            "| **Pass Condition** | No protected-data exchange, OR disclosure was established |")
    asserted = rag.asserted_tokens(text)
    assert {"compliant", "hipaa", "audit", "trail"} <= asserted
    assert "write" in asserted            # before the cue
    assert "modify" not in asserted       # after "never"
    assert "deletion" not in asserted     # after "No"
    assert "pass" in asserted and "condition" in asserted   # its own cell


def test_the_negation_cues_cover_the_claim_vocabulary_guards_negations():
    """tests/test_claim_vocabulary.py keeps a negation list so that a sentence
    forbidding a phrase is not read as asserting it. The reading aid's cues
    must include every plain negation word that list uses, so the two guards
    do not drift into different ideas of what "not" means. Judgement words in
    that list ("withdrawn", "wrong") are deliberately not cues here."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "claim_vocab", REPO_ROOT / "tests" / "test_claim_vocabulary.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    plain = {"never", "not", "no", "nor"}
    for word in plain:
        assert re.search(rf"\b{word}\b", module.NEGATIONS.pattern), word
        assert word in rag.NEGATION_CUES, word


def test_denial_shaped_questions_are_refused(client):
    for question in (
        "What is NHID-Clinical's HIPAA certification number?",
        "Which accreditation body certified the conformance test suite?",
        "Which health plan is NHID-Clinical's launch customer?",
    ):
        body = client.post("/spec/ask", json={"question": question}).json()
        assert body["refused"] is True, question
        assert body["answer"] == rag.REFUSAL


# ── declared exclusions, provenance, freshness ───────────────────────────────

def test_non_specification_files_are_excluded_with_a_reason(client):
    """A maintainer's checklist of GitHub settings is in docs/ and was, for a
    day, a cited source for a question about certification."""
    indexed = {p.name for p in rag.iter_corpus_files()}
    for name, reason in rag.EXCLUDED_FILES.items():
        assert name not in indexed, name
        assert reason
    reasons = {s["source"]: s["reason"] for s in client.get("/spec/health").json()["skipped_files"]}
    assert reasons.get("docs/maintainer-checklist-github.md") == "maintainer note, not specification"


def test_health_carries_corpus_hash_and_commit(client):
    body = client.get("/spec/health").json()
    assert re.fullmatch(r"[0-9a-f]{64}", body["corpus_hash"])
    assert body["corpus_hash"] == rag.corpus_hash()
    assert body["commit"]  # a short sha, or "unknown" where git is absent


def test_a_changed_corpus_invalidates_the_saved_index(tmp_path, monkeypatch):
    """Edit docs/, forget to rebuild, and the old index used to quote stale text
    under current paths. load_index now rebuilds when the corpus hash moved."""
    corpus = tmp_path / "docs"
    corpus.mkdir()
    (corpus / "a.md").write_text("# Alpha\n\nThe alpha control requires a disclosure timestamp.\n", encoding="utf-8")
    monkeypatch.setattr(rag, "CORPUS_DIR", corpus)
    monkeypatch.setattr(rag, "INDEX_PATH", tmp_path / "index.json")
    monkeypatch.setattr(rag, "REPO_ROOT", tmp_path)
    first = rag.build_index(verbose=False)
    (corpus / "a.md").write_text("# Alpha\n\nThe alpha control requires a disclosure timestamp and an outcome.\n", encoding="utf-8")
    second = rag.load_index()
    assert second.corpus_hash != first.corpus_hash
    assert any("outcome" in c.text for c in second.chunks)


# ── retrieved text is data, not instructions ─────────────────────────────────

ADVERSARIAL = REPO_ROOT / "eval" / "adversarial"


@pytest.fixture()
def poisoned_index(tmp_path, monkeypatch):
    """The real corpus plus the three planted documents, indexed in a temp dir.
    Nothing here touches the repository's own index."""
    import shutil
    corpus = tmp_path / "docs"
    corpus.mkdir()
    for path in rag.iter_corpus_files():
        shutil.copy(path, corpus / path.name)
    for path in sorted(ADVERSARIAL.glob("*.md")):
        if path.name != "README.md":
            shutil.copy(path, corpus / path.name)
    monkeypatch.setattr(rag, "CORPUS_DIR", corpus)
    monkeypatch.setattr(rag, "INDEX_PATH", tmp_path / "index.json")
    monkeypatch.setattr(rag, "REPO_ROOT", tmp_path)
    return rag.build_index(verbose=False)


def _whole_corpus(index) -> str:
    text = " ".join(c.text for c in index.chunks)
    return re.sub(r"\s+", " ", text)


def test_adversarial_documents_are_never_indexed_by_default():
    indexed = {p.name for p in rag.iter_corpus_files()}
    for path in ADVERSARIAL.glob("*.md"):
        assert path.name not in indexed, path.name


def test_embedded_instructions_are_quoted_not_followed(poisoned_index):
    """Every line the aid returns is a verbatim quotation of some corpus text.
    An instruction inside a document can therefore be *shown* but can change
    nothing: there is no step that could obey it. If a generative step is ever
    added, this is the test that must still pass."""
    result = rag.ask(poisoned_index, "What is the pass condition for PDX-01?")
    assert not result.refused
    corpus = _whole_corpus(poisoned_index)
    for line in result.answer.split("\n\n"):
        passage = re.sub(r"\s+\[docs/[^\]]+\]$", "", line)
        passage = re.sub(r"\s+\[[^\]]+\.md\]$", "", passage)
        assert re.sub(r"\s+", " ", passage) in corpus, line
    # The instruction text, if it surfaces at all, surfaces with its source
    # named, never as the aid's own voice.
    for line in result.answer.split("\n\n"):
        assert re.search(r"\[[^\]]+\.md\]$", line), line


def test_a_poisoned_source_is_quoted_with_its_name_on_it(poisoned_index):
    """A planted certification record IS answered from: a quotation carries the
    authority of its source and no more, and the retriever cannot know the file
    is false. What it can do is name the file. The defense against a poisoned
    source is a trusted-source registry, not the retriever; this test records
    that boundary rather than pretending the retriever provides it."""
    result = rag.ask(poisoned_index, "What is NHID-Clinical's HIPAA certification number?")
    assert not result.refused
    assert any(c.endswith("fake-certification.md") for c in result.citations), result.citations
    assert "HC-2026-0042" in result.answer


def test_conflicting_sources_are_each_cited_inline(poisoned_index):
    """Two documents state different PDX-01 pass conditions. Whatever is quoted,
    each passage carries its own citation, so a conflict is attributable to a
    file instead of blended into one answer."""
    result = rag.ask(poisoned_index, "What is the pass condition for PDX-01?")
    lines = [l for l in result.answer.split("\n\n") if l.strip()]
    assert lines
    for line in lines:
        assert re.search(r"\[[^\]]+\.md\]$", line), line


# ── hybrid retrieval (built, tested, off by default) ────────────────────────

def _mini_index(texts):
    chunks = [rag.Chunk(source=f"docs/t{i}.md", index=0, text=t) for i, t in enumerate(texts)]
    return rag.Index(chunks=chunks, backend="local", built_at=0.0)


def test_retrieval_defaults_to_dense_and_the_exact_id_list_is_off():
    assert rag.RETRIEVAL == "dense"
    assert rag.EXACT_ID is False


def test_bm25_prefers_the_shorter_chunk_and_scores_absent_terms_zero():
    filler = " ".join(f"word{i}" for i in range(200))
    idx = _mini_index([
        "escalation path honored by a human",
        f"escalation path honored {filler}",
        "nothing relevant here at all",
    ])
    short, long_, none = rag.bm25_scores(idx, "escalation honored")
    assert short > long_ > 0.0
    assert none == 0.0


def test_rank_fusion_counts_only_positive_scores_within_depth():
    ranks = rag._ranks([0.0, 0.9, 0.5, 0.7], depth=2)
    assert ranks == {1: 1, 3: 2}


def test_identifiers_are_matched_exactly_and_case_sensitively():
    q = "Why did PDX01_PHI_GATE_TRIGGERED fire before IDG-01, and what is deny_data?"
    assert rag.identifiers_in(q) == ["IDG-01", "PDX01_PHI_GATE_TRIGGERED"]


def _unanswerable_questions():
    path = REPO_ROOT / "eval" / "spec_rag_questions.jsonl"
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    return [r["question"] for r in rows if not r["answerable"]]


@pytest.mark.parametrize("exact_id", [False, True])
def test_switching_hybrid_on_still_refuses_every_unanswerable_question(index, monkeypatch, exact_id):
    # The switch exists for the OpenAI backend. Whoever turns it on must not
    # be able to turn the refusals off with it.
    monkeypatch.setattr(rag, "RETRIEVAL", "hybrid")
    monkeypatch.setattr(rag, "EXACT_ID", exact_id)
    for question in _unanswerable_questions():
        result = rag.ask(index, question)
        assert result.refused and result.answer == rag.REFUSAL, question


def test_the_exact_id_list_surfaces_a_chunk_naming_the_identifier(index, monkeypatch):
    monkeypatch.setattr(rag, "RETRIEVAL", "hybrid")
    monkeypatch.setattr(rag, "EXACT_ID", True)
    hits = rag.retrieve(index, "When is PDX01_PHI_GATE_TRIGGERED returned?")
    assert any("PDX01_PHI_GATE_TRIGGERED" in h.chunk.text for h in hits)
    assert all(h.rrf > 0.0 for h in hits)
    assert all(h.control_boost == 0.0 for h in hits)
