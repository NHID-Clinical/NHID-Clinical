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
| **Commit** | `e63b9840d7b949f4661e0bd8a2a2f8c112850ff7` (`e63b984`) |
| **Measured** | 2026-10-16 (previously `ed342b3`, 2026-09-06 — see §13) |
| **Method** | Commands in the "How to reproduce" section, run against a clean checkout |
| **Branch** | `main` |
| **Licence** | Apache-2.0 for code (`LICENSE`), CC BY 4.0 for specification and documentation prose (`LICENSE-DOCS`); split stated in `NOTICE` |

---

## 1. Versions

| Constant | Value | Source of truth |
|---|---|---|
| `NHID_SPEC_VERSION` | `1.3` | `src/nhid_policy_engine_v1.py` |
| `POLICY_ENGINE_VERSION` | `1.0.0` | `src/nhid_policy_engine_v1.py` |
| `UNIT_PUBLISHED` | `1834` | `scripts/validate_ci.py` — published-number reference, **not** a CI gate |
| `SKIP_EXPECTED` | `0` | `scripts/validate_ci.py` — CI starts the API, so a skip means it did not come up |
| `XFAIL_EXPECTED` | `0` | `scripts/validate_ci.py` — recorded divergences, see `skipped-test-audit.md` §8 |

## 2. Test suite

```
1834 passed, 0 skipped, 0 xfailed   # python -m pytest tests/ -q (API running)
1192 passed, 21 skipped             # ...the same command with no API listening (drift-ok: no-API measurement, not the published count)
1834 collected                # python -m pytest tests/ --collect-only -q
67 files                      # files under tests/ that pytest collects from
```

1834 collected, 1834 passed. Every published surface stating these numbers must
satisfy that arithmetic; `scripts/check_number_drift.py` enforces the passed
count, reads the text of every `specs/*.pdf`, and — as of `ed342b3` — also
covers this file and `MASTER-KNOWLEDGE-ARCHIVE.md`. Those two were outside its
surface list until then, which is why the archive carried a stale `987` through
four separate reconciliations: the guard was never looking at them.

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

Eight adapter modules exist: four active in `adapters/`, four archived under
`adapters/archive/` as working reference implementations that are no longer
maintained (the archive README says why: six vendor interfaces this project does
not control was a permanent cost for a framework with no deployments).
Five are wired to hosted routes, and the routes for the archived three still exist:

| Adapter | Module | Status | Hosted route |
|---|---|---|---|
| Twilio | `twilio_adapter.py` | active | `/v1/adapters/twilio/check` |
| VAPI | `vapi_adapter.py` | active | `/v1/adapters/vapi/check` |
| Vonage | `archive/vonage_adapter.py` | archived | `/v1/adapters/vonage/check` |
| Retell | `archive/retell_adapter.py` | archived | `/v1/adapters/retell/check` |
| Amazon Connect | `archive/amazon_connect_adapter.py` | archived | `/v1/adapters/connect/check` |
| ElevenLabs (post-call) | `archive/elevenlabs_postcall_adapter.py` | archived | none |
| Fabricate | `fabricate_adapter.py` | active | internal — corpus ingestion, incl. the voice-stress JSONL (`convert_voice_stress`) |
| Call progress | `call_progress_adapter.py` | active | internal — event type |

Any page describing an implemented adapter as "planned" contradicts this table;
any page describing an archived one as maintained contradicts it too.

## 5. Evidence — six distinct bodies, never to be merged

Collapsing these into a single "accuracy" number would misrepresent all six.

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
**23/32 detected = 71.9%. 0/5 compliant scenarios produced a false positive. 12 unexpected detections on violation scenarios — a separate quantity, see `governance-corpus-remediation.md`.**
Derived by *running* the corpus (`scripts/eval_corpus.py`), not from a constant.
Small and hand-authored: a research measurement, not a conformance claim,
certification, assurance score, or independent validation.

### 5.3 Adversarial corpus — evasion resistance
40 scenarios in `tests/adversarial_corpus_v1.json`.
Last recorded run: 23/23 attacks withstood, 0 bypasses, 0/17 false positives.

### 5.4 Conformance suite — deterministic implementation tests
`conformance/nhid_conformance_test_suite_v1.yaml`. Distinct from all of the
above: it tests the implementation, not detection quality over a corpus.

### 5.5 Governance Evaluation Corpus v2 — hard cases, by construction
`tests/evaluation_corpus_v2.json`: 8 scenarios (2 compliant negative controls),
20 turns, 10 expected violations across five controls.
**5/10 detected = 50.0%. 0 false positives on the compliant scenarios; 0
unexpected detections.** Run by `tests/test_eval_corpus_v2.py`; findings in
`docs/validation/EVALUATION_CORPUS_V2_FINDINGS.md`.
The headline is low on purpose: v2 over-weights the failure modes the engine
is known not to reach — cross-turn disclosure contradiction and a later-turn
deceptive persona — and each carries its honest expected outcome. No expected
outcome was weakened to raise the rate. It is not a regression against §5.2.

### 5.6 Fabricate voice-stress corpus — staged, now measured
The staged JSONL corpus under `fixtures/voice-stress`, wired through
`adapters/fabricate_adapter.py` (`convert_voice_stress`) and
`scripts/confusion_matrix.py --voice-stress`:

| Control | Detected | Rate | False positives | FP rate |
|---|---|---|---|---|
| IDG-01 | 65/65 | 100.0% | 0/95 | 0.0% |
| PDX-01 | 8/8 | 100.0% | 0/95 | 0.0% |
| DBC-01 | 0/28 | **0.0%** | 0/95 | 0.0% | <!-- drift-ok: voice-stress corpus — a different measurement from the CSV-550 baseline in §5.1, which is the 91.5% the guard pins -->
| EIT-01 | 12/25 | 48.0% | 6/95 | 6.3% |

The pinned CSV-550 baseline in `scripts/check_baseline.py` (§5.1) was not
edited and did not move. The DBC-01 zero is the subject of
`docs/validation/DBC-01-SCOPE-AND-LIMITATIONS.md`: the control is kept and
scoped to transcript-based explicit or implied human-status claims; these
cases are outside that scope, and acoustic artifact detection is not claimed.
Findings: `docs/validation/FABRICATE_VOICE_STRESS_FINDINGS.md`.

## 6. Published artifacts

Three PDFs in `specs/`, all produced by `scripts/generate_pdfs.py`:
v1.3 Core Specification · Shadow Evaluation Guide · Playbook.
(Seven at `ed342b3`; the suite was cut when the withdrawn trust score left four
of them describing a control tier that no longer existed.)

They are **generated, not hand-maintained**. Regenerate after any change to a
published figure; `check_number_drift.py` now fails if a PDF's text disagrees
with `UNIT_PUBLISHED`.

## 7. Website shape

**12 published pages** (`PUBLISHED` in `tests/test_site_navigation.py`, which
also asserts the build emits exactly that set): home, about, specification,
shadow-evaluation guide, developers, evidence pack, regulatory alignment,
NHID-Auth, FAQ, downloads (`specs/index.html`), privacy, SMS opt-in. Downloads
is now in navigation.

**Retired from the build** (present in the repository, not published, and no
published page may link to them — the test fails if one does): `simulator.html`
and the `simulator/` app, `docs.html`, `technical-stack.html`, `for-payers.html`,
`script-examples.html`, `demo.html`, `interoperability.html`, `registry.html`,
`roadmap.html`, `news.html`, `community.html`, `identity-layer.html`,
`implementation-review.html`, `gov-sim.html`, `svg-preview.html`, `pilot.html`,
`conformance.html`, the `framework/` sub-pages other than `nhid-auth.html`, and
the `alignment/` and `platform/` stubs. The 45-page, 15-orphan shape recorded at
`ed342b3` is gone.

The five-layer stack figure is one canonical SVG, used on three pages; the
`technical-stack.html` page that carried it four times is retired.

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
python -m uvicorn app:app --port 8000 &         # required, or 21 tests skip
python -m pytest tests/ -q                      # 1834 passed, 0 skipped, 0 xfailed
python -m pytest tests/ --collect-only -q       # 1834 collected
python scripts/validate_ci.py                   # CI PASS
python scripts/check_baseline.py                # Fabricate baseline
python scripts/check_number_drift.py            # drift + corpus + PDFs
python scripts/check_fixture_integrity.py       # fixture shape + join keys
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
| Suite passing | **1834** | `python -m pytest tests/ -q` with the API running |
| Recorded divergences | **0** | both contracts resolved; see `skipped-test-audit.md` §8 |
| Skipped | **0** | same run |
| Collected | **1834** | `--collect-only -q`; equals the passing count |
| IDG-01 | 70/70, 0 FP | `scripts/check_baseline.py` |
| PDX-01 | 41/41, 0 FP | `scripts/check_baseline.py` |
| DBC-01 | 183/200 = 91.5%, 5 FP | `scripts/check_baseline.py` |
| EIT-01 | 169/171, 5 FP | `scripts/check_baseline.py` |
| Fabricate corpus | **550** conversations, 4838 turns | row count of `fixtures/fabricate/conversations.csv` / `turns.csv` |
| Fabricate compliant | **127** | conversations with `0` on all five `*_violation` columns |
| Voice-stress corpus | **300** scenarios, **1582** turns, **2071** assertions | row count of `fixtures/voice-stress/*.csv` |
| Voice-stress scoreable | **118** of 205 positives | positives declaring an IDG/PDX/DBC/EIT expectation; 87 cannot be scored (67 target the still-proposed NHID-Auth) |
| Governance corpus | **25** scenarios, **55** turns | `scripts/eval_corpus.py` |
| Governance detection | **23/32 = 71.9%** | `scripts/eval_corpus.py` |
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

## 12. State change — 2026-09-06 (`ed342b3`)

Three pull requests merged since §11 was written. None changed the engine, the
controls, the corpora, or any published count.

| PR | Change | Verifiable by |
|---|---|---|
| **#383** | Evidence Diagram System adopted; four generated figures replacing asserted ones; `.reveal` inverted so nothing depends on JavaScript to be visible | `docs/visual-system.md`; `python scripts/build_evidence_visuals.py --check` |
| **#384** | Legacy visual layer retired — five models replacing seven external asset references; generated latency figure added | `docs/visual-system.md` §9 records each retired file's status |
| **#386** | Repository dual-licensed; nightly-verify shallow-clone bug fixed; `docs/payer-brief.md` added | `LICENSE`, `LICENSE-DOCS`, `NOTICE`; `.github/workflows/nightly-verify.yml` |

**Licence split.** Code is Apache-2.0; specification and documentation prose stay
CC BY 4.0. The repository was previously CC BY 4.0 throughout, including every
Python file — a licence Creative Commons advises against applying to software,
carrying no patent grant and no warranty disclaimer written for code. That is a
review an adopting organisation's counsel can only end one way, for reasons
unrelated to the work.

**Nightly-verify was failing, and for longer than the failure suggested.** Issue
#385 reported `1147 passing` against a published `1148`. <!-- drift-ok: quotes the failure figure from issue #385 --> The API was healthy; the
cause was the default shallow clone, under which
`tests/test_control_set_completeness.py` cannot reach `ba93e21` and skips. The
same bug had already been fixed in `ci.yml` — `nightly-verify.yml` never received
`fetch-depth: 0`. The failing step was also short-circuiting the three guards
below it, so the nightly had been verifying **less than it claimed**, not merely
reporting red. Proven fixed by `workflow_dispatch` before merge (run
`33994318931`): all four steps green where three had been silently skipped.

**Retired visual assets are not deleted.** They remain in the repository and in
git history, unreferenced by any live destination. Deletion is a retention
decision recorded as open in `docs/visual-system.md` §9.

## 13. State change — 2026-10-16 (`e63b984`)

Eighteen pull requests merged since §12. The suite went 1148 → 1213 (API
running), 67 collected files; the no-API run 1127 → 1192 with the same 21
skips. No control definition changed. Each row is verifiable from the
repository, not from this file.

| PR | Change | Verifiable by |
|---|---|---|
| **#389** | NHID-Auth v2 claims brought down to what the implementation does | `framework/nhid-auth.html`, `src/agent_identity.py` |
| **#390** | Fail closed: every router authenticates; nothing mints with a known secret | `app.py`; `tests/test_*auth*.py` |
| **#391** | Trust score, tiers, badges, and the DBC-01 self-reported artifact sub-check withdrawn | README "Enforcement Profile" note; `docs/CONTROL_DECISION_TABLE.md` |
| **#392** | Downstream-artifact failures caught locally; DBC-01 said the same way everywhere | `scripts/verify_all.py` |
| **#393 / #394** | Site moved under `site/` and moved back | repository root |
| **#395** | About page, JSON-LD, canonical, meta description, SVG brand mark | `about.html`, `index.html` `<head>` |
| **#396 / #397** | Control count corrected; sprint status out of the README; copy straightened | `README.md` |
| **#398** | `/spec` reading aid; site copy rewrite | `specification.html` |
| **#399–#401** | Pilot kit repaired after the withdrawal; offline promise guarded over the kit's import closure; analytics disclosed; 300-scenario corpus measured | `docs/pilot-kit/`, `tests/test_pilot_kit_offline.py`, `privacy.html` |
| **#402** | `nhid pilot`: one command, an evidence pack out | `src/pilot_measure.py`, `src/pilot_report.py`, `src/pilot_pdf.py`, `src/cli.py` |
| **#403** | Token-exchange answer in the integration guide; the slot UDAP leaves open | `docs/v2-integration-guide.md` §3.2 and Part 3; `src/udap_agent_extension.py` |
| **#404** | Trust Gateway walkthrough flattened to terminal chrome; fixture byte-identical to engine output | `tests/test_trust_gateway.py`; `verify_all` check 4 |
| **#405** | Validation path: ten documents in `docs/validation/`, corpus v2 (§5.5), voice-stress measurement (§5.6), DBC-01 scope statement, `eval_corpus.py --report` | `tests/test_eval_corpus_v2.py`, `tests/test_fabricate_voice_stress.py`, `scripts/check_number_drift.py` (corpus report byte-check) |
| **#406** | NIST AI RMF Playbook crosswalk; a wrong subcategory corrected | `docs/nist-ai-rmf-playbook-crosswalk.md` |

**Adapters archived, routes kept.** Four adapters moved to `adapters/archive/`
(§4). Their hosted routes were not removed, so an integrator who already calls
one is not broken; the archive README states that they are not maintained.

**PDFs: seven → three.** Evidence Pack, Knowledge Archive, Operational
Blueprint, v1.3 Overview and the NHID-Auth v2 Technical Reference are no longer
generated; the Playbook is new. All three are text-checked by the drift guard.

**Companion repositories, same day.** `NHID-Clinical-SaaS` #26 — RFC 8693
token exchange beside the API key, issuing an opaque hashed token, no new
secret; #27 — `data_classification` on pilot runs (`synthetic` ·
`deidentified` · `production_derived`), additive migration 0006. Both merged
2026-10-16. The Simulator's README was rewritten to describe the five modules.

**Open.** NHID-Clinical #407, the homepage recomposed as an instrument console
(ink bands, the Trust Gateway isometric figure as the hero, a trust-stack system
map, a four-pane trace console of real `evaluate_all()` output). Green on all
checks; carries this file's count.

**Not established by any of the above:** a shadow-evaluation partner, a
production deployment, dataset access, or an independent review of DBC-01
against its threat model. The corpus v2 figure (50%) measures hard cases chosen
to be hard and is not comparable to §5.1 or §5.2.

---

*Maintenance: update this file in the same commit as any change to the figures
it records. If it disagrees with the repository, the repository is right and this
file is stale.*
