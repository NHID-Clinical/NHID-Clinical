# NHID-Clinical Tier 0 Shadow Pilot Kit

Run a meaningful shadow pilot in 2–4 weeks with minimal integration and produce
usable data: Impersonation Latency, CAS distribution, and top control violations
from your own call traffic. Observe-only — no vendor changes, no live enforcement.

> NHID-Clinical is a voluntary open baseline (CC BY 4.0). Pilot numbers are
> **measurements against your own traffic**, not conformance certifications.

## What's in the kit

| Artifact | Purpose |
| :--- | :--- |
| [`minimal-event-schema.json`](minimal-event-schema.json) | The per-turn capture record to extract from your existing call logs |
| [`measure_pilot.py`](measure_pilot.py) | Replays captured turns through the real policy engine and computes all Tier 0 metrics |
| [`pilot-report-template.md`](pilot-report-template.md) | The short internal report you fill in (or generate) at the end |
| [`../../tools/pilot_report_generator.py`](../../tools/pilot_report_generator.py) | Turns per-call results into a markdown report automatically |

Quick sanity check that everything runs (no data needed):

```bash
pip install -r requirements.txt
python docs/pilot-kit/measure_pilot.py --demo
```

## Disclosure timeliness bands

Impersonation Latency is reported as a raw measurement *and* bucketed into four bands, so a
delayed-but-present disclosure is not flattened into the same bucket as never disclosing at all.

| Band | Disclosure | Reported as |
| :--- | :--- | :--- |
| `pass` | turn 0, before any data request | conformant |
| `delayed` | present, within 10s, before any PHI | observation |
| `late` | present, after 10s, before any PHI | human review |
| `critical` | PHI exchanged before disclosure, or never disclosed | violation |

**These bands are a reporting convention, not a gate.** The policy engine has no seconds-based
rule; every pass/fail verdict still comes from `evaluate_all()`. The normative target remains
`IL(turns) = 0` — disclosure before any data is requested. The 10-second threshold exists so that
an agent which disclosed a little slowly reads differently in a pilot report from one that never
disclosed. Where a capture source has no usable timestamps, classification falls back to the turn
form.

## What Tier 0 measures

- **Impersonation Latency** — time and turns until the first valid non-human
  disclosure (`Δt(interaction_start → identity_resolution)`)
- **First-turn disclosure rate** and **never-disclosed rate**
- **Pre-disclosure PHI exposure** — sensitive fields requested before disclosure
- **Escalation honor rate** — human-handoff requests honored vs. requested
- **Per-control violations** — IDG-01 (Identity Disclosure Gate), PDX-01
  (Pre-Data Exchange Gate), DBC-01 (Deceptive Behavior Check), EIT-01
  (Escalation Implementation Test)
- **CAS distribution** — the disclosure-level Call Authorization Score per call,
  bucketed by trust tier (≥0.90 Verified Trust · ≥0.75 Conditional Trust ·
  ≥0.50 Review Required · ≥0.20 Denied/Degraded · below: Hard Denial)

Two honest limitations to keep in mind:
- **ATR-01** (Audit Trail Requirements) cannot be exercised from transcript
  replay — the kit synthesizes complete audit envelopes by construction. Audit
  completeness is assessed at Tier 1+ against your real event pipeline.
- **DBC-01 voice artifacts** (Tier A) require voice-forensics flags your stack
  may not produce; text heuristics (Tier B) still run on transcripts. Residual
  implicit-impersonation cases are a known human-review area, not a solved
  detection problem.

## How the capture schema maps to the engine (important)

The capture schema is deliberately flat so it's easy to fill from call logs.
`measure_pilot.py` maps it into the engine's real event contract
([`schema/nhid_trace_schema_v1.json`](../../schema/nhid_trace_schema_v1.json)).
Do **not** feed flat records to the engine yourself — the behavioral controls
read a nested block, and flat fields are silently ignored:

| Capture field | Where the engine reads it | Mapping rule |
| :--- | :--- | :--- |
| `disclosure_timestamp` | `event.healthcare_governance.disclosure_timestamp` | **Sticky**: once set, carried forward to every later turn |
| `identity_assertion_text` | `event.healthcare_governance.identity_assertion_text` | Agent turns default to their own `speech_text`; caller turns carry the sticky disclosure sentence |
| `deceptive_artifact_flags` | `event.healthcare_governance.deceptive_artifact_flags` | Copied into the nested block (top-level flags are ignored by the engine) |
| `phi_accessed` | `event.healthcare_governance.phi_accessed` | Copied per turn |
| `escalation_requested` + `escalation_honored` | `session.escalation_path_available` | `False` only when a request was explicitly not honored |
| `speech_text` | `event.input_payload.speech_text` | Drives text heuristics (DBC-01 Tier B, EIT-01 triggers, PHI speech signals) |

## The evaluation workflow

An **ordered sequence**, not a schedule. Each stage depends on the one before
it; none has a required length, and an evaluation may legitimately stop after
any of them. Sample sizes below are sizes, not durations — how long it takes to
gather them is yours to determine.

> This replaces a "30-day pilot plan" that prescribed Week 1–2 / Week 3 /
> Week 4. The approved observe-only methodology does not impose a mandatory
> 30-, 60- or 90-day duration, and the stages here depend on each other rather
> than on a calendar.

**Stage 1 — capture and baseline**
- Pull 500–2,000 historical or live shadow calls from one workflow
  (prior auth, claims status, or billing)
- Map each call's turns to `minimal-event-schema.json` records (one JSONL line
  per turn); validate a sample against the schema
- Run `measure_pilot.py calls.jsonl` for the baseline Impersonation Latency and
  violation rates

*Stop condition:* a sample replays cleanly and the baseline numbers are produced.

**Stage 2 — analyse**
- Re-run with `--results-dir out/` and generate the report:
  `python tools/pilot_report_generator.py out/ pilot_report.md`
- Read the CAS tier distribution and the top-3 violations per workflow
- Spot-check 10–20 flagged calls by hand — confirm the violations are real
  before drawing conclusions

*Stop condition:* the flagged calls have been read by a person, not only counted.

**Stage 3 — decide and write up**
- Fill in [`pilot-report-template.md`](pilot-report-template.md) (or edit the
  generated report) with observations and recommendations
- Decide the follow-up: move to Tier 1 controls, require disclosure language
  from vendors, or expand the sample

*Stop condition:* someone who did not run the evaluation can read the report and
know what was and was not established.

## What "good enough" pilot data looks like

You can act on the pilot when all of these hold:
- **Sample**: ≥500 calls from one workflow, ≥2 weeks of traffic
- **Coverage**: <10% of calls dropped for unmappable/missing fields
- **Verification**: hand-review of a sample of flagged calls confirms the
  violations (target: most flags confirmed; document the false-positive rate
  you observe rather than assuming zero)
- **Stability**: week-over-week median Impersonation Latency within ±1 turn

If any of these fail, extend the capture window before making vendor or policy
decisions — a small or noisy sample overstates whatever it happens to contain.

## Next steps after Tier 0

- [5-minute quickstart](../5-minute-quickstart.md) — run the engine locally
- [v2 integration guide](../v2-integration-guide.md) — Tier 0 → Tier 2 ladder
- [Shadow evaluation guide](https://nhid-clinical.org/shadow-evaluation-guide.html) — the full evaluation sequence
- Live adapter routes (VAPI/Twilio/Vonage/Retell/Connect) — evaluate calls via
  the hosted API instead of local replay
