# Specification RAG — a reading aid for `docs/`

A question-answering index over the markdown in `docs/`. You ask where the
specification says something; it quotes the passage back with a file path.

## What this is not

It is **not the policy engine.** It does not evaluate a call, it produces no
control decision, and nothing it returns is a conformance result or a
certification of anything. `src/nhid_policy_engine_v1.py` is the engine, and
the five controls — IDG-01, PDX-01, DBC-01, EIT-01, ATR-01 — are what decide
whether an interaction passed.

An answer from here is a quotation with a path attached. It carries exactly the
authority of the document it came from and no more. If the corpus is wrong,
this repeats the error faithfully.

## Corpus

| | |
|---|---|
| Source | `docs/*.md`, top level only. Subdirectories (`docs/validation/`, `docs/pilot-kit/`) are not indexed |
| Indexed | **47 files, 959 chunks** (measured 2026-10-25 at `b53ad3b`; `/spec/health` reports the live figure) |
| Skipped | `docs/MASTER-KNOWLEDGE-ARCHIVE.md` — over the 200 KB cap |
| Skipped | `docs/spec-rag.md` — this file; the aid does not read its own manual |
| Skipped | `docs/maintainer-checklist-github.md` — a maintainer note, not specification (`EXCLUDED_FILES`) |
| Chunking | 800 characters, 100-character overlap, source path and chunk index stored |
| Provenance | the index records a `corpus_hash` (sha256 over indexed paths and contents) and the `commit` it was built from; both are on `/spec/health` and in every eval report |
| Freshness | `load_index` rebuilds when the corpus hash or the backend differs from what the saved index recorded, so an edited document is never quoted stale |

Files over 200 KB are skipped whole rather than truncated. A half-read document
is worse than an absent one: it answers confidently from whichever part
happened to fit. `GET /spec/health` names what it skipped, and why.

Anything else placed in `docs/` is indexed as evidence. That is a glob, not a
trusted-source registry, and it bit once (below). The registry is the roadmap's
Phase 3; until then `EXCLUDED_FILES` is the list, and every entry carries a
reason that `/spec/health` repeats.

## Embedding backends

| Backend | When | What it measures |
|---|---|---|
| `openai` | `OPENAI_API_KEY` is set | `text-embedding-3-small` |
| `local` | no key | deterministic hashed bag-of-words |

**The local score is not the OpenAI score.** It matches words, not meaning, so
a question phrased differently from the document scores worse than it deserves.
It exists so the index builds, the tests run and this eval reproduces on a
machine with no key — a fallback, not a second opinion. The CLI, `/spec/health`
and the eval script all state which backend produced a number.

## Retrieval

Top 4 by `0.60 × cosine + 0.40 × token_overlap`, plus a `0.15` boost when a
control id named in the question also appears in the chunk. The boost is large
enough to reorder near-ties and too small to float an irrelevant chunk into the
top 4.

## Answering, and refusing

There is no generative step. An answer is passages lifted from the retrieved
chunks with their source path inline, which is what makes every claim
checkable.

When the excerpts do not contain the answer, the reply is exactly:

```
the corpus does not contain the answer
```

The test for that is IDF-weighted coverage of the question's content words **by
a single chunk** — not pooled across all four. Pooling was the first
implementation and it failed in the way that matters most here:

> *"What is NHID-Clinical's HIPAA certification number?"* scored 0.70 pooled,
> because **HIPAA** appears in one file, **certification** in another and
> **number** in a third. It answered, citing two documents that together imply
> a certification this project does not have.

Requiring one passage to carry the question's distinctive vocabulary fixed it,
and is also just what grounding means: an answer is a quotation from somewhere,
not a sentence assembled from four places.

### Then this file broke it again

Writing the paragraph above into `docs/spec-rag.md` put it in the corpus, and
the refusal collapsed a second time — refusals went 5/5 to **4/5** on the next
run. The quoted question now appeared verbatim in an indexed chunk, so
single-chunk coverage scored **1.0** and the aid answered
*"What is NHID-Clinical's HIPAA certification number?"* citing this file.

The write-up of the failure mode had become its cause. A document explaining
why a question cannot be answered reads, to a retriever matching words, exactly
like a document answering it.

The fix is `SELF_DOCUMENTATION` in `src/nhid_spec_rag.py`: the aid excludes its
own manual from its corpus and says so on `/spec/health`. The corpus is the
specification, not the tooling that reads it. `test_the_aid_does_not_index_its_own_documentation` holds the line, and
asserts the file still exists — an exclusion that silently stops excluding
anything is worse than none.

This was found by re-running the eval after writing the documentation, not by
reading the code. It is the reason the eval is a script and not a paragraph.

### Then the specification broke it a third time (2026-10-25)

On 25 October the refusal collapsed again, to **4/5**, and nothing noticed for
four merges because the eval ran in no CI job. The cause was not tooling this
time but the specification itself: `docs/canonical-threat-model.md` ends with

> *Nothing here claims production deployment, healthcare-provider adoption,
> HIPAA certification or independent validation.*

A sentence written to **deny** a claim carries exactly the vocabulary of the
question that asks for it. Single-chunk coverage reached 0.69 and the aid
answered, citing that footer. The same day a maintainer's checklist of GitHub
settings landed in `docs/` and crossed the threshold independently.

Two changes followed, and the eval measured both:

1. **A denial is not evidence.** Coverage now counts a question word only where
   a retrieved chunk *asserts* it: a word that appears solely inside a negated
   clause (`not`, `no`, `never`, `nothing`, `none`, `neither`, `nor`, `cannot`)
   does not count. A clause ends at sentence punctuation, a blank line, a table
   cell or a line that starts a list item; it does **not** end at a plain line
   break, because the markdown is hard-wrapped and the denial above spans three
   lines. The rule applies to the answer-or-refuse gate only. Applying it to
   passage selection as well was tried first and removed the right sentence from
   eight answers ("does not perform speech recognition", "write once, never
   modify" are limits, and limits are answers); the eval caught it and the
   change was reverted before it shipped.
2. **Declared exclusions.** `EXCLUDED_FILES` names the maintainer note with its
   reason, reported on `/spec/health`.

Known limit, accepted: a question whose honest answer *is* a denial ("does
NHID-Clinical claim HIPAA certification?") may now be refused at the gate.
Refusing a question a denial would have answered is the cheaper error.

## Results

Measured by `eval/run_spec_rag_eval.py` against the 35 questions in
`eval/spec_rag_questions.jsonl` (20 answerable, 15 unanswerable), on the
**local** backend (no API key set), 2026-10-25, commit `b53ad3b`, corpus hash
`619a9317…`. The same numbers are recorded in `eval/baseline-local.json`, which
CI checks every run.

| Metric | Result | What it measures |
|---|---|---|
| **File hit @ k=4** | **18/20** | `expected_source` in the top 4. Unchanged since 2026-10-10, same two misses |
| **Accepted hit @ k=4** | **19/20** | any of `accepted_sources` in the top 4 (q14 has five documents that define EIT-01) |
| **Passage hit** | **11/20** | the answer contains `expected_passage_contains`. New; first measure of whether the quoted text is the useful part. Two answerable questions (q08, q17) are refused outright, seven quote the right file's wrong passage |
| **MRR** | **0.79** | rank of `expected_source` within the top 4 |
| **Refusals** | **15/15** | the original 5 plus 10 denial-shaped questions added 2026-10-25 |
| **Unsupported answers** | **0/15** | the number that must stay at zero |

The OpenAI backend has never been measured. Running the eval with
`OPENAI_API_KEY` set reports it separately; the two are not comparable and are
never averaged.

### Before the 2026-10-25 fix, for the record

Same questions, same backend, same day, before the polarity rule: file hit
18/20, refusals **4/5** of the original five (r02 answered), passage hit 11/20.
The fix changed refusals only; no hit moved in either direction.

### The two misses, not buried

**q14 — "What does the EIT-01 escalation implementation test check?"**
Expected `docs/CONTROL_DECISION_TABLE.md`; retrieved
`docs/nhid-clinical-technical-specification.md` first. That file *does* define
EIT-01 correctly:

> `| **EIT-01** | Escalation Implementation Test | A human escalation path must be communicated and, when requested, honored | CRITICAL |`

So this is the eval being strict — it allows one expected source per question
where two documents genuinely answer — rather than the retriever being wrong.
The label was left alone. Relabelling it after seeing the result would make the
90% meaningless.

**q11 — "Which claims should be avoided when describing NHID-Clinical?"**
Expected `docs/claim-boundaries.md`, which has a *Claims to make / claims to
avoid* section. Retrieved `docs/claims-register.md`, which does not contain the
word "avoid". **This one is a real miss.** Two documents with near-identical
names and overlapping subject matter, and the retriever picked the wrong one.

### What the hit rate does and does not measure

It measures retrieval only: whether the right file came back in the top 4. It
says nothing about whether the quoted passage is the *useful* part of that
file. Answer quality is not scored here, and the known weakness is that the
local backend favours chunks where a term is dense — tables and JSON examples —
over the prose that defines it. Asked *"What does PDX-01 gate?"*, it returns
rows from the FHIR mapping table before the definition in the decision table.

Two changes were tried and reverted, both caught by the eval: IDF-weighting the
retrieval overlap term (hit rate unchanged, refusals 5/5 → 4/5), and applying
the polarity rule to passage selection (passage hit 11/20 → 9/20).

`--check` applies the roadmap's acceptance rule: a drop in file, accepted or
passage hits, a drop in refusals, or any rise in unsupported answers fails.
Nothing is optimised alone.

## Usage

Build the index — required once, and after any change to `docs/`:

```bash
python -m src.nhid_spec_rag
```

Ask from the command line:

```bash
python -m src.nhid_spec_rag --ask "What is the pass condition for PDX-01?"
```

Re-run the eval:

```bash
python eval/run_spec_rag_eval.py                                  # table + totals
python eval/run_spec_rag_eval.py --json eval/baseline-local.json  # record a new baseline, deliberately
python eval/run_spec_rag_eval.py --check eval/baseline-local.json # what CI runs
```

Run the tests:

```bash
python -m pytest eval/ -v
```

### Why the tests live in `eval/` and not `tests/`

`scripts/validate_ci.py` runs `pytest tests/` and gates on the result matching
`UNIT_PUBLISHED`, the unit-test count published on the website, in the README
and in the PDFs. Putting these twelve tests in `tests/` would have moved that
number, which describes the *conformance and invariant* suite — the engine's
coverage. A reading aid over `docs/` says nothing about the engine, so folding
its tests into that figure would inflate a public claim with unrelated work.
They sit beside the eval harness instead. Moving them into `tests/` later will
break `validate_ci.py` until every published surface is renumbered; that is the
guard working, not a bug.

## Routes

Mounted in `main.py` behind the same dependency as every other router:

```python
from src import nhid_spec_rag
app.include_router(nhid_spec_rag.router, dependencies=[Security(get_api_key)])
```

`docs/` is public, so authentication is not protecting the content. It is
protecting the surface: an unauthenticated route would reintroduce the gap
`main.py` records closing on the attestation router, and `/spec/ask` is a
free-text endpoint that writes a log line per call.

### `GET /spec/health`

```json
{
  "status": "ok",
  "chunks": 915,
  "sources": 45,
  "backend": "local",
  "skipped_files": [
    {"source": "docs/MASTER-KNOWLEDGE-ARCHIVE.md", "bytes": 209598, "reason": "over the size cap"},
    {"source": "docs/maintainer-checklist-github.md", "bytes": 2168, "reason": "maintainer note, not specification"},
    {"source": "docs/spec-rag.md", "bytes": 11000, "reason": "this module's own documentation"}
  ],
  "corpus_hash": "619a9317…",
  "commit": "b53ad3b",
  "score_is_openai_score": false,
  "note": "Reading aid for docs/. Not the policy engine, not a conformance result, not a certification."
}
```

### `POST /spec/ask`

```json
{"question": "What is the pass condition for PDX-01?"}
```

Returns `answer`, `citations`, `refused`, plus `backend` and `coverage`.

## Retrieved text is data, not instructions

There is no generative step, so nothing in a document can steer an answer
today. The rule is written down now because the day a generative step is added,
every file in `docs/` becomes an instruction channel. `eval/adversarial/` holds
three planted documents — embedded instructions, a fake certification record,
a near-duplicate specification table with one row changed — that are never
indexed by default; `eval/test_spec_rag.py` indexes them into a temporary corpus
and asserts that every returned line is a verbatim quotation with its source
named, that the fake certification is answered **from the planted file, by
name** (a quotation carries the authority of its source and no more; the
defense against a poisoned source is a trusted-source registry, not the
retriever), and that conflicting sources are each cited inline.

## Logging

One JSON line per ask, appended to `logs/spec_rag.jsonl`:

```json
{"timestamp": "2026-10-10T06:00:00Z", "question": "...", "sources": ["docs/..."], "refused": false}
```

The question, the cited sources and whether it refused — enough to audit what
the aid was asked and what it pointed at. No API key, no embedding, no document
body. A log write that fails does not fail the request: the ask is the product,
the log is bookkeeping.
