# Conformance suite — clean-environment run record

The published conformance metric comes from this run and no other. It is not an
intermediate figure from the middle of the remediation, and it is not assembled
from several partial runs.

| | |
|---|---|
| **Commit tested** | `cd3c611f7a3b014c62a7ca8b991fa6b508854aa5` |
| **Date** | 2026-09-03 |
| **Checkout** | fresh `git clone`, checked out at that SHA |
| **Interpreter** | CPython 3.11.15 |
| **Platform** | Linux-6.18.44-fc-v24-x86_64-with-glibc2.39 |
| **Environment** | fresh `python -m venv`, `pip install -r requirements.txt` only |

## Result

| Outcome | Count |
|---|---|
| **Collected** | **1020** |
| **Executed** | **1020** |
| **Passed** | **1020** |
| Failed | **0** |
| Skipped | **0** |
| xfailed | **0** |
| xpassed | **0** |

Collected equals executed equals passed. Nothing was deselected, deferred,
marked, or excluded.

## Exact commands

```bash
git clone <repo> cleanclone && cd cleanclone
git checkout cd3c611f7a3b014c62a7ca8b991fa6b508854aa5

python -m venv ../cleanenv
../cleanenv/bin/pip install -r requirements.txt

# The API must be running: 18 integration tests exercise it, and without a
# server they silently skip. NHID_REQUIRE_SERVER=1 makes that a hard error
# instead of a quiet 18-test hole.
../cleanenv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8011 &

../cleanenv/bin/python -m pytest tests/ --collect-only -q      # 1020 collected
NHID_REQUIRE_SERVER=1 NHID_BASE_URL=http://127.0.0.1:8011 \
  ../cleanenv/bin/python -m pytest tests/ -q --disable-warnings -rsxX
```

The clean clone carries **no `nhid_events.db`** — it is gitignored, so the
event store was created from nothing during the run. The audit-trail tests
therefore exercised a genuinely empty starting state.

## Dependencies as installed

```
PyJWT==2.13.0  PyYAML==6.0.3  Pygments==2.21.0  annotated-doc==0.0.5
annotated-types==0.8.0  anyio==4.15.0  attrs==26.1.0  certifi==2026.7.22
cffi==2.1.1  charset-normalizer==3.5.1  click==8.5.0  cryptography==50.0.1
fastapi==0.141.1  h11==0.16.0  httpcore==1.0.9  httpcore2==2.12.0
httpx==0.28.1  httpx2==2.12.0  idna==3.19  iniconfig==2.3.0  jiter==0.16.0
jsonschema==4.26.0  jsonschema-specifications==2025.9.1  openai==3.8.0
packaging==26.3  pdfminer.six==20260107  pluggy==1.6.0  pycparser==3.0
pydantic==2.13.5  pydantic_core==2.46.5  pytest==9.1.1  pytest-asyncio==1.4.0
python-dotenv==1.2.3  python-multipart==0.0.32  referencing==0.37.0
rpds-py==2026.6.3  sniffio==1.3.1  starlette==1.6.0  truststore==0.10.4
typing-inspection==0.4.4  typing_extensions==4.16.0  uvicorn==0.52.4
```

## How the number got here

987 → 1020, and the path matters because it is not simple growth.

| Step | Effect |
|---|---|
| Started CI's API so the 18 integration tests actually ran | +11 passing, 7 failing, 18 skips → 0 |
| Resolved the CallSid contract | 5 failures → passing, +2 new tests |
| Resolved the `/debug/replay` contract | 2 failures → passing, +1 new test |
| Added the control-set completeness guard | +12 tests |
| Governance-corpus instrumentation | +0 (measurement only) |

**Nothing on that list is a denominator change.** No test was deleted, skipped,
xfailed, weakened, deselected, or excluded to produce a green result, and the
count rose because tests were added and previously-unrun ones were made to run.

## What this number is not

- **Not a governance detection rate.** That is 29/32 = 90.6% on the Governance
  Evaluation Corpus, a separate research measurement — see
  `governance-corpus-remediation.md`.
- **Not a false-positive rate.** That is 0/5 compliant scenarios, with 8
  unexpected detections on violation scenarios reported separately.
- **Not a Fabricate detection figure.** That is IDG-01 70/70, PDX-01 41/41,
  DBC-01 183/200, EIT-01 169/171 — see below.
- **Not a count of controls, scenarios, or requirements.**

Conflating any of these with the conformance pass count would misrepresent all
of them.

---

# Fabricate baseline — preserved, then compared

The baseline was **not** regenerated during remediation. An anchor was taken
before any work began and the artifact was generated once, at the end, from the
final commit.

## Anchor, taken before remediation

```
47e8beee37c95763bc6ee6f3d049cb9e75a4b987297b4327bdea9a2416cd777e  fixtures/fabricate/conversations.csv
5117a4aab950255d34b40c7f23298b4e9c2e622b5a5b947caed3997a9c4b337d  fixtures/fabricate/turns.csv
```

## Generated from the final commit, in the clean environment

| Control | Detection | False positives on 127 clean conversations |
|---|---|---|
| IDG-01 | 70/70 = 100.0% | 0/127 = 0.0% |
| PDX-01 | 41/41 = 100.0% | 0/127 = 0.0% |
| DBC-01 | 183/200 = 91.5% | 5/127 = 3.9% |
| EIT-01 | 169/171 = 98.8% | 5/127 = 3.9% |

Corpus: 550 conversations, 127 of them compliant.

## Differences

**None.** Every figure is identical to the preserved baseline, and both fixture
files still hash to the anchor values above.

That is not coincidence, and it was checked rather than assumed. The one engine
change attempted during this work — generalising IDG-01 to require an
affirmative non-human assertion — was scoped to run only when a harness reports
which turn carried the disclosure. The Fabricate replay path does not report it,
takes the permissive default, and never reaches the check. The change was
subsequently reverted anyway (`governance-corpus-remediation.md` §2.1), so the
engine is byte-identical to its pre-remediation state.

**No unexplained drift exists.** No new evidence artifact was created merely
because an intermediate metric moved.
