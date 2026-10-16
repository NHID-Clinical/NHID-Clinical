# Data Sources Inventory — healthcare voice / call data for NHID-Clinical

**Status:** validation reference · **Added:** 2026-10-14 · CC BY 4.0

> Where NHID-Clinical can get call/transcript data to exercise the five
> controls *without a shadow pilot*, and — just as important — which widely
> circulated "ready to use" datasets turn out not to exist as advertised.
> Every row is marked **VERIFIED** (I confirmed it against a primary source)
> or **UNVERIFIED** (I could not confirm the claim as stated). Nothing here is
> presented as available, licensed, or PHI-free unless a primary source says
> so. Pairs with [`evidence-provenance-matrix.md`](evidence-provenance-matrix.md),
> which governs what any of this data is allowed to *prove*.

---

## The short version

A popular "data acquisition strategy" for this project names six public
datasets. **Checked against primary sources, only two are real, and only one
of those is openly downloadable:**

- **INSURE-Dial** — real, the best fit, but **gated** (you must request access).
- **LingVarBench** — real as a *method/benchmark*, but its data is proprietary;
  there is no public dataset to download.
- **Four others** (a Kaggle "Hospital Inbound Patient Call-Center Records" set,
  a "syntech-ai" 3,000-conversation set, an "Oncology Support Voice" set of
  50,000 recordings, and a specific OpenCHS synthetic-helpline dataset) **could
  not be confirmed to exist as described.** Do not plan around them.

The honest usable shortlist is therefore small — but it is enough to exercise
all five controls on text, and one option even carries audio. See
[`evidence-provenance-matrix.md`](evidence-provenance-matrix.md) for how far
each source's results are allowed to reach.

---

## Fit to the five controls — what we actually need from data

NHID-Clinical governs a provider→payer AI voice call and evaluates observable
behaviour. To exercise the controls, a source needs **turn-level dialogue**
(who said what, in order). Audio is a bonus, not a requirement, for everything
except acoustic-robustness testing.

| Control | What the data must contain to exercise it |
| :-- | :-- |
| IDG-01 Identity Disclosure | turns where an agent does / does not disclose it is AI, and later turns that may contradict it |
| PDX-01 Pre-Data Exchange | a PHI request/exchange with a timestamp relative to disclosure/authorization |
| DBC-01 Deceptive Behavior | agent statements that can be checked against what the call context supports |
| EIT-01 Escalation | a request to reach a human and the agent's response to it |
| ATR-01 Audit Trail | per-turn metadata complete enough to build an audit record |

None of this requires real PHI. A faithful **synthetic** transcript with these
structures exercises the controls exactly as a real one does — which is why the
reproducible synthetic corpus (`tests/evaluation_corpus_v1.json`) is the
primary, always-available test bed and every public dataset below is
supplementary.

---

## VERIFIED — real sources

### INSURE-Dial · best fit · **gated**
- **What:** phase-aware benchmark for compliance of insurance
  benefit-verification voice calls: **50 real de-identified AI-initiated calls**
  with live insurance reps + **1,000 synthetic** calls, annotated with a
  phase-structured schema (IVR nav, patient ID, coverage, medication, agent
  identification) and Information/Procedural compliance labels.
- **Publisher / origin:** Dataframer; EACL 2026 (ACL Anthology
  `2026.eacl-long.237`, arXiv `2602.18448`).
- **Medium:** transcripts with phase annotations (not raw audio in the public
  release).
- **Control fit:** strong — agent-identification and compliance phases map
  directly onto IDG-01 / PDX-01 / DBC-01; the 1,000 synthetic calls are the
  bulk test bed.
- **Access / license:** **gated on Hugging Face** (`dataframer/insure-dial`) —
  you must request access and agree to data-sharing terms before download. Not
  a free `load_dataset(...)` call.
- **PHI risk:** publisher states HIPAA Safe-Harbor de-identification with manual
  verification on the real calls; still treat the real split as sensitive and
  read the dataset card's terms.
- **Action:** request access — drafted message in
  [`insure-dial-access-request.md`](insure-dial-access-request.md). I did not
  submit it.
- Primary sources: <https://aclanthology.org/2026.eacl-long.237/> ·
  <https://arxiv.org/abs/2602.18448> ·
  <https://huggingface.co/datasets/dataframer/insure-dial>

### Synth-DoPaCo · open · **carries audio**
- **What:** ~**8,800 synthetic doctor–patient dialogues**, ~1,329 hours of
  audio, with train/dev splits, on Hugging Face.
- **Publisher:** `Play-Your-Part/Synth-DoPaCo` (HF).
- **Medium:** transcripts **and audio** — the one real option here that lets
  you prototype an audio path (see [`audio-input-test-path.md`](audio-input-test-path.md)).
- **Control fit:** moderate. It is *clinical* doctor–patient dialogue, not
  provider→payer administrative calls, so it does not match NHID's exact
  boundary moment. Useful for audio-pipeline and ASR robustness prototyping,
  **not** for validating authorization behaviour. Confirm the license on the
  card before any use.
- Primary source: <https://huggingface.co/datasets/Play-Your-Part/Synth-DoPaCo>

### NoteChat · open · transcripts
- **What:** synthetic patient–physician conversations conditioned on clinical
  notes.
- **Publisher:** NoteChat (HF `akemiH/NoteChat`; arXiv `2310.15959`).
- **Control fit:** weak for NHID (clinical encounter, not payer admin). Listed
  because it is real, open, and sometimes conflated with the fictitious
  "syntech-ai" set below. Confirm license on the card.
- Primary source: <https://huggingface.co/papers/2310.15959>

### LingVarBench · real **method**, no public data
- **What:** a synthetic-data *generation pipeline + benchmark* for structured
  entity extraction from healthcare phone-call transcripts, with curated
  verbalization patterns (disfluencies, digit-by-digit vs grouped readouts).
- **Publisher:** EACL 2026 Industry track (arXiv `2508.15801`).
- **Use to us:** the **method** is directly reusable for generating
  linguistically varied synthetic turns (noise, self-corrections, pauses) to
  harden the corpus. The authors' own evaluation data is **proprietary** — there
  is no dataset to download.
- Primary source: <https://arxiv.org/abs/2508.15801>

### Kaggle — Healthcare Appointment Booking Calls · real, adjacent
- **What:** transcripts of calls to a generic medical clinic with speaker
  labels and timestamps; PII described as redacted (suggesting real, redacted
  calls, not synthetic).
- **Control fit:** weak — scheduling/intake, not provider→payer; no disclosure
  or authorization structure. Listed as the real thing that the fictitious
  "Hospital Inbound Patient Call-Center Records" set below is probably a garbled
  memory of. Verify license/terms before use.
- Primary source:
  <https://www.kaggle.com/datasets/ammarshafiq/healthcare-appointment-booking-calls-dataset>

### FutureBeeAI — scripted healthcare monologue speech · real, vendor
- **What:** scripted healthcare speech prompts (human speakers, ~60 for US
  English), sold for voice-assistant/customer-service training.
- **Control fit:** none for authorization behaviour; usable only as **generic
  acoustic material** if testing ASR/audio conditions — and generic speech does
  not validate healthcare authorization behaviour, which must be stated wherever
  it is used.
- Primary source:
  <https://www.futurebeeai.com/dataset/monologue-speech-dataset/healthcare-scripted-speech-monologues-english-usa>

---

## UNVERIFIED — claims I could not confirm (do not plan around these)

Each of these appears in the circulating "data strategy" with specific numbers.
I searched primary sources and could not confirm any of them as described. They
are listed so nobody wastes days chasing them.

| Claimed dataset | Claim | What I found |
| :-- | :-- | :-- |
| **Kaggle "Hospital Inbound Patient Call-Center Records"** | 25,000 synthetic + 5,000 test, with `Chief_Complaint` / `Call_Transcript_Summary` | **No such dataset found.** Nearest real thing is *Healthcare Appointment Booking Calls* (above), which has none of those fields or counts. Treat the specific claim as fabricated. |
| **"syntech-ai" Doctor–Patient Synthetic Conversations** | 3,000 conversations, CC-BY-NC-4.0 | **No dataset found under that publisher/name/size/license.** Real synthetic doctor–patient sets exist (Synth-DoPaCo, NoteChat) but none match the stated specifics. |
| **OpenCHS Synthetic Helpline Call Classification Dataset** | a usable synthetic dataset for escalation-logic testing | **Only partially real.** An OpenCHS model references `synthetic_helpline_qa_scoring_v1`, but it has no public dataset card, license, or size, and the domain is child-helpline / Swahili QA — weak fit, unconfirmed availability. |
| **Oncology Support Voice Dataset** | 50,000 synthesized recordings, 500 speakers, scripted | **No such dataset found.** Nearest real things are human-voice sets (FutureBeeAI ~60 speakers; a Databricks 250-hour human set; the COPE oncology study of ~435 *real* encounters) — none synthesized at that scale. |

Tools named alongside these (voicetest, voxprobe, Tonic Textual, Hamming,
Bluejay, Roark, Salesforce eVerse) are **test harnesses / vendors, not
datasets**, and are out of scope for this inventory; if any is adopted it gets
its own verified entry.

---

## Recommended path, given the above

1. **Synthetic corpus first** (`tests/evaluation_corpus_v1.json`) — the
   always-available, reproducible, PHI-free test bed that exercises all five
   controls. This is being expanded; it does not depend on any external source.
2. **Request INSURE-Dial** — the one real, high-fit public benchmark. Drafted
   request in [`insure-dial-access-request.md`](insure-dial-access-request.md).
3. **Consented volunteer calls** for genuine audio with the hard cases
   (interruptions, overlap, mid-call contradiction) — protocol in
   [`volunteer-call-protocol.md`](volunteer-call-protocol.md).
4. **Synth-DoPaCo** only to prototype the *audio pipeline*, never to claim
   authorization-behaviour validation.

What each of these is then allowed to *prove* is fixed by
[`evidence-provenance-matrix.md`](evidence-provenance-matrix.md). No source
here establishes production adoption, certification, or that any healthcare
organization has deployed or evaluated NHID-Clinical.
