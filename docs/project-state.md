# NHID-Clinical — Project State

**Purpose.** A single verifiable record of what this repository contains, so that
a new session (or a new person) can establish context without re-deriving it and
without trusting a conversation transcript that has expired.

Every figure below was measured from the repository at the commit named. Nothing
here is carried over from planning threads, prior summaries, or external audits.
Where the repository does not settle a question, this file says **UNKNOWN**
rather than inferring.

| | |
|---|---|
| **Commit** | `aaad25a3d9b9005502470faaa4d05af3d6b7722d` (`aaad25a`) |
| **Measured** | 2026-09-03T09:37:59Z |
| **Method** | Commands in the "How to reproduce" section, run against a clean checkout |
| **Branch** | `claude/nhid-clinical-july-deadline-che6r8` |

---

## 1. Versions

| Constant | Value | Source of truth |
|---|---|---|
| `NHID_SPEC_VERSION` | `1.3` | `src/nhid_policy_engine_v1.py` |
| `POLICY_ENGINE_VERSION` | `1.0.0` | `src/nhid_policy_engine_v1.py` |
| `UNIT_PUBLISHED` | `998` | `scripts/validate_ci.py` — published-number reference, **not** a CI gate |
| `SKIP_EXPECTED` | `0` | `scripts/validate_ci.py` — CI starts the API, so a skip means it did not come up |
| `XFAIL_EXPECTED` | `7` | `scripts/validate_ci.py` — recorded divergences, see `skipped-test-audit.md` §8 |

## 2. Test suite

```
1094 passed, 0 skipped, 0 xfailed   # python -m pytest tests/ -q (API running)
1002 passed, 18 skipped             # ...the same command with no API listening
1005 collected                # python -m pytest tests/ --collect-only -q
55 files                      # files under tests/ that pytest collects from
```

1094 collected, 1094 passed. Every published surface stating these numbers must
satisfy that arithmetic; `scripts/check_number_drift.py` enforces the passed
count, and as of `aaad25a` also reads the text of every `specs/*.pdf`.

**The skip count means one thing:** integration tests that need a live server.
It is not a general "not applicable" bucket. Checks that do not apply to a file
must be excluded from parametrisation rather than skipped at runtime, or this
figure stops meaning what every page says it means.

## 3. Controls

Six control identifiers appear in the engine:

`IDG-01` · `PDX-01` · `DBC-01` · `EIT-01` · `ATR-01` · `DLG-01`

**Five are canonical. `DLG-01` is opt-in** — it is evaluated only when a
deployment configures delegated authority, and otherwise returns
`DLG01_NOT_EVALUATED` and changes nothing.

`ATR-01` is canonical, not supplemental. The archive records a correction dated
2026-08-22: §2.1 previously read "The Four Controls". Any document describing
four canonical controls is either historical or wrong — see the claims register.

## 4. Adapters

Eight adapter modules exist in `adapters/`. Five are wired to hosted routes:

| Adapter | Module | Hosted route |
|---|---|---|
| Twilio | `twilio_adapter.py` | `/v1/adapters/twilio/check` |
| VAPI | `vapi_adapter.py` | `/v1/adapters/vapi/check` |
| Vonage | `vonage_adapter.py` | `/v1/adapters/vonage/check` |
| Retell | `retell_adapter.py` | `/v1/adapters/retell/check` |
| Amazon Connect | `amazon_connect_adapter.py` | `/v1/adapters/connect/check` |
| ElevenLabs (post-call) | `elevenlabs_postcall_adapter.py` | none |
| Fabricate | `fabricate_adapter.py` | internal — corpus ingestion |
| Call progress | `call_progress_adapter.py` | internal — event type |

Any page describing an implemented adapter as "planned" contradicts this table.

## 5. Evidence — four distinct bodies, never to be merged

Collapsing these into a single "accuracy" number would misrepresent all four.

### 5.1 Fabricate Battle-Test Corpus — CI-gated baseline
550 conversations; 127 labelled compliant (the false-positive population).
Detection and false positives are measured on **disjoint populations**.

| Control | Detected | Rate | False positives | FP rate |
|---|---|---|---|---|
| IDG-01 | 70/70 | 100.0% | 0/127 | 0.0% |
| PDX-01 | 41/41 | 100.0% | 0/127 | 0.0% |
| DBC-01 | 183/200 | 91.5% | 5/127 | 3.9% |
| EIT-01 | 169/171 | 98.8% | 5/127 | 3.9% |

`ATR-01` is absent because this corpus cannot measure it — a stated structural
limitation, not a score of zero.
Source of truth: `EXPECTED` in `scripts/check_baseline.py`, gated in CI.

### 5.2 Governance Evaluation Corpus — research measurement
25 scenarios (5 compliant, 20 violation), 55 turns, 32 expected violations.
**30/32 detected = 93.8%. 0/5 compliant scenarios produced a false positive. 12 unexpected detections on violation scenarios — a separate quantity, see `governance-corpus-remediation.md`.**
Derived by *running* the corpus (`scripts/eval_corpus.py`), not from a constant.
Small and hand-authored: a research measurement, not a conformance claim,
certification, assurance score, or independent validation.

### 5.3 Adversarial corpus — evasion resistance
40 scenarios in `tests/adversarial_corpus_v1.json`.
Last recorded run: 23/23 attacks withstood, 0 bypasses, 0/17 false positives.

### 5.4 Conformance suite — deterministic implementation tests
`conformance/nhid_conformance_test_suite_v1.yaml`. Distinct from all of the
above: it tests the implementation, not detection quality over a corpus.

## 6. Published artifacts

Seven PDFs in `specs/`, all produced by `scripts/generate_pdfs.py`:
Evidence Pack · Knowledge Archive · Operational Blueprint v1.3 ·
Shadow Evaluation Guide · v1.3 Core Specification · v1.3 Overview ·
NHID-Auth v2 Technical Reference.

They are **generated, not hand-maintained**. Regenerate after any change to a
published figure; `check_number_drift.py` now fails if a PDF's text disagrees
with `UNIT_PUBLISHED`.

## 7. Website shape

45 published pages, ~18,000 words of body content — page count is inflated
relative to substance.

**15 pages are orphans** (nothing on the site links to them). Two carry real
content and are simply unreachable:

- `script-examples.html` — 748 words, sixth-largest page. Concrete disclosure
  phrasing and the patterns that create impersonation latency.
- `specs/index.html` — the PDF download index. There is no downloads page in
  navigation; PDFs are linked ad-hoc from six other pages.

The rest are redirect stubs (`pilot.html`, `conformance.html`,
`conformance/index.html`), a Search Console verification file, dev artifacts
(`svg-preview.html`), the retired `gov-sim.html`, `implementation-review.html`,
and four `alignment/*` stubs of 37–61 words each.

**Retired from the build** (present in the repository, not published):
`simulator.html`, the `simulator/` app, and `docs.html`.

The five-layer stack visual appears on 5 pages, not on every page.
`technical-stack.html` is 155 words carrying it four times, which is why its
rendering diverges from the homepage's.

## 8. Maturity — what the repository does and does not establish

**Established:** a deterministic policy engine; five canonical controls plus one
opt-in; five hosted adapter routes; four separate evidence bodies with published
methodology and stated limitations; FHIR R4 AuditEvent output; a conformance
suite; CI guards against published-number drift.

**Not established anywhere in this repository — do not infer:**

| Question | Repository answer |
|---|---|
| Production deployments | **UNKNOWN.** No evidence of any. `index.html` states "no production-scale deployment". |
| Named adopters, customers, design partners | **UNKNOWN.** No evidence of any. |
| Independent security audit | **UNKNOWN.** No evidence of one. |
| Independent validation of any metric | **UNKNOWN.** All figures are self-measured. |
| Certification or accreditation status | **None.** The project is a voluntary open framework. |
| Regulatory endorsement | **None.** |
| Performance under production load | **UNKNOWN.** Reference implementation; not load-tested. |
| NHID-Auth v2 production readiness | Reference implementation, early testing. No production issuers. |

## 9. Environment constraints

Recorded because they change what a session can verify:

- **Outbound to `nhid-clinical.org` is blocked** by the working environment's
  proxy. The live site cannot be fetched; deployment is confirmed only from
  GitHub Actions workflow conclusions.
- Web search works, but see the claims register on how to treat vendor content.
- **Cannot be produced here:** video recording or editing, image generation,
  design comps.
- The three statute URLs cited on the homepage
  (`leginfo.legislature.ca.gov`, `docs.fcc.gov`, `eur-lex.europa.eu`) have
  **never been opened by anyone** and are live in production. They are the
  canonical official locations but remain unverified.

## 10. How to reproduce every figure here

```bash
git rev-parse HEAD
python -m uvicorn app:app --port 8000 &         # required, or 18 tests skip
python -m pytest tests/ -q                      # 1094 passed, 0 skipped, 0 xfailed
python -m pytest tests/ --collect-only -q       # 1005 collected
python scripts/validate_ci.py                   # CI PASS
python scripts/check_baseline.py                # Fabricate baseline
python scripts/check_number_drift.py            # drift + corpus + PDFs
python scripts/eval_corpus.py                   # Governance Evaluation Corpus
python scripts/redteam_corpus.py                # adversarial corpus
bash scripts/build_pages_site.sh                # _site/
python scripts/visual/check_internal_links.py   # internal links
ls adapters/*_adapter.py; ls specs/*.pdf
```

---

## 11. Metric verification — 2026-09-03

Every public figure re-derived from its source on this date, at commit `dc136ca`.
`origin/main` was `6985644`; its tree is **byte-identical** to this branch's base
`79d81a6`, so "verified against `main`" and "verified against this branch's base"
are the same statement here. The three intervening commits on `main` are merges
that introduced no net change.

| Figure | Value | Derived by |
|---|---|---|
| Suite passing | **1094** | `python -m pytest tests/ -q` with the API running |
| Recorded divergences | **0** | both contracts resolved; see `skipped-test-audit.md` §8 |
| Skipped | **0** | same run |
| Collected | **1094** | `--collect-only -q`; equals the passing count |
| IDG-01 | 70/70, 0 FP | `scripts/check_baseline.py` |
| PDX-01 | 41/41, 0 FP | `scripts/check_baseline.py` |
| DBC-01 | 183/200 = 91.5%, 5 FP | `scripts/check_baseline.py` |
| EIT-01 | 169/171, 5 FP | `scripts/check_baseline.py` |
| Fabricate corpus | **550** conversations, 4838 turns | row count of `fixtures/fabricate/conversations.csv` / `turns.csv` |
| Fabricate compliant | **127** | conversations with `0` on all five `*_violation` columns |
| Governance corpus | **25** scenarios, **55** turns | `scripts/eval_corpus.py` |
| Governance detection | **30/32 = 93.8%** | `scripts/eval_corpus.py` |
| Governance false positives | 0 of 5 compliant scenarios | `scripts/eval_corpus.py` |
| Adversarial corpus | **40** scenarios | length of `tests/adversarial_corpus_v1.json` |

**One figure could not be reconciled and is not published.** A metric of
*"1,005 automated conformance tests passing · 18 currently skipped"*, and a
related *"98.2% of 1,023 automated tests"*, were raised for use on public
surfaces. Neither reconciles with anything this repository produces:

- **1,005 is the collected total, not the passing count.** It was 987 + 18
  before this change and is 998 + 7 after. Publishing 1,005 as *passing* would
  count the skipped — and now the failing — tests as passes.
- **1,023 does not appear anywhere.** No file, corpus, or command yields it, and
  1,005 + 18 = 1,023 suggests the collected total was added to the skips it
  already contains.
- **98.2% of 1,023 is 1,004.6**, which rounds to neither figure quoted.

Per the rule against resolving contradictions by silent selection, these are
recorded as **UNKNOWN in origin** rather than adopted, averaged, or quietly
replaced. The measured figure is 998 of 1005 (99.3%), and 99.3% is not published
either — a percentage invites reading the remaining 0.7% as flaw rather than as
two documented open decisions.

---

*Maintenance: update this file in the same commit as any change to the figures
it records. If it disagrees with the repository, the repository is right and this
file is stale.*
