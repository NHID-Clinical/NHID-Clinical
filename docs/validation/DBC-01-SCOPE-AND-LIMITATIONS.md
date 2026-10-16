# DBC-01 — scope, limitations, and the case for keeping it narrow

**Status:** control-scope decision + grounded investigation · **Added:** 2026-10-14 · CC BY 4.0

> The open DBC-01 scope question (raised in
> [`EVALUATION_CORPUS_V2_FINDINGS.md`](EVALUATION_CORPUS_V2_FINDINGS.md) and
> [`FABRICATE_VOICE_STRESS_FINDINGS.md`](FABRICATE_VOICE_STRESS_FINDINGS.md)) is
> **decided here**: keep DBC-01, describe its scope narrowly, and document its
> limitations rather than quietly widen its claims. DBC-01 is a useful control
> without being a complete deception detector — this document says exactly what
> it is and is not, grounded in the real cases it misses and the real cases it
> over-fires on.
>
> This is a research measurement of hand-authored corpora. It is not a
> conformance claim, a certification, or independent validation.

---

## Decision

| | |
| :-- | :-- |
| **Keep DBC-01?** | Yes. |
| **Scope, as now stated** | Transcript-based detection of **explicit or implied claims of human status** by an automated agent. |
| **Acoustic / audio-artifact detection** | **Not a claimed capability.** No audio-analysis mechanism exists in this repository (see below). |
| **Expand the control's claims?** | **Not until** the misses and false positives below are understood and an independent reviewer has assessed the control against the intended threat model. |

## Scope, stated narrowly

DBC-01 reads the **transcript** of an agent's turns and flags language that
asserts, or implies, that the speaker is a **human** when the speaker is an
automated agent. Concretely: explicit impersonation and concealment phrasing,
first-person human/clinical-role claims ("I'm a nurse reviewer," "this is Sarah
Chen, a human representative"), and a small set of corpus-mined implied-humanity
cues. Its pass condition is the absence of such flags.

That is the whole claim. It is deliberately smaller than "detects deception."

## Explicitly out of scope — and why

- **Acoustic or signal artifacts.** DBC-01 does **not** analyse audio. The
  Fabricate adapter's `synthetic_breathing` / `synthetic_typing` flags are
  matched from **text stage-direction markers** in a transcript (the literal
  token `*inhales*`), never from sound. A transcript without such a marker
  yields no flag regardless of the underlying audio, and no audio is examined
  anywhere in the pipeline. Detecting fake breathing or synthetic sound in real
  audio would require a separate audio-analysis mechanism that does not exist
  here; until one does and is measured, acoustic detection is not claimed. (The
  adapter comment was corrected in this change to say so plainly.)
- **General deception, manipulation, or empathy-feigning.** An agent that has
  *disclosed* it is automated and then says "I feel it too" or "we take this
  seriously on my end" is using anthropomorphic rhetoric, not claiming to be
  human. DBC-01 does not treat that as a human-status claim (see the misses).
- **Cross-turn contradiction after a valid disclosure.** Disclose-then-claim-
  human across turns is IDG-01's domain (`IDG01_DISCLOSURE_CONTRADICTED`), and
  its own scope boundary is documented separately. DBC-01 does not own it.
- **Verifying that a human-status claim is _true_.** DBC-01 detects the *claim
  pattern* in agent-attributed text. It has no speaker-identity ground truth, so
  it cannot tell a bot falsely claiming to be human from a real human who
  truthfully says so (see the false positives).

## Grounded in the measured cases

Measured on the CSV-550 Fabricate corpus (`scripts/check_baseline.py`): DBC-01
detects **183/200** with **5** false positives. The gap is 17 missed; both
groups were read in full.

### The 17 missed — mostly disclosed agents using soft rhetoric

Of the 17 missed conversations, **15 contain an explicit AI self-disclosure**
("This is an automated system," "I'm an AI assistant," "I'm not a live
representative"), and **15 contain soft anthropomorphic / empathy / deflection
phrasing** ("my end," "I feel it too," "our team," "transferring would reset
your case"). These are not human-status claims — the agent has already said it
is automated. The corpus labels them DBC-01 because it labels broad "deceptive
behaviour," but a transcript control scoped to human-status claims **correctly
does not fire**, and inflating it to catch general manipulation would be scope
creep dressed as a bug fix. The two that do not explicitly disclose still make
no human-status claim; they are candidates for an independent reviewer to judge,
not an automatic reason to widen the lexicon.

### The 5 false positives — truthful humans after a legitimate transfer

All five are **compliant** baseline scenarios where the AI discloses correctly,
transfers to a **real human**, and that human says "this is Sarah Chen, I'm a
human representative." DBC-01 flags the human-status-claim *pattern* on an
agent-attributed turn and has no way to know a genuine human is now on the line.
This is the clearest statement of the control's boundary: **a transcript-only
detector cannot verify the truth of a human-status claim.** Reducing these five
is a precision question (e.g. post-transfer speaker handoff signalling), to be
weighed against detection — not a reason to loosen the claim.

## Threat model — framing for an independent review

DBC-01 is meant to reduce one specific risk: **an automated agent leading a
counterparty to believe they are speaking with a human.** It addresses that at
the transcript layer only, as one control among five, and after IDG-01 has
already required disclosure.

Questions an independent reviewer should assess the control against:

1. Does the narrow scope ("human-status claims in agent-attributed transcript
   text") match the threat the control is meant to reduce, or is a gap being
   relabelled as out-of-scope?
2. Are the 15/17 disclosed-agent misses genuinely out of scope, or should any be
   a different control's responsibility (IDG-01, EIT-01) rather than nobody's?
3. Is the "cannot verify a human-status claim is true" limitation acceptable
   given a legitimate transfer-to-human is a common compliant flow (5/5 FPs)?
4. What is the detection and false-positive cost of any proposed widening, on
   **all** corpora (CSV-550, voice-stress, v2) and not just the one that
   motivated it?

An independent assessment against this threat model is a precondition for any
expansion of the control's claims. This document does not perform that review;
it prepares it.

## Why a narrow, honest control is still useful

DBC-01 detects 183/200 explicit/implied human-status claims on CSV-550 with a
low, enumerated false-positive set, and 65/65 IDG-01-adjacent disclosure cases
pass cleanly on the voice-stress corpus. A control that reliably catches the
specific, high-salience failure — a bot saying it is a person — is worth having
even though it does not catch empathy-feigning, manipulation, or acoustic
spoofing. The error is not that DBC-01 is narrow; the error would be claiming it
is broad.

## Related measured results (do not conflate)

| corpus | DBC-01 | note |
| :-- | :-- | :-- |
| CSV-550 (`check_baseline.py`) | 183/200, 5 FP | pinned baseline; unchanged by this work |
| voice-stress (300) | 0/28 | deceptive-persona scenarios; the open gap, now explained |
| synthetic v2 (8) | 0/2 | cross-turn / undisclosed persona; IDG-01's domain |

The three figures measure different corpora and are not interchangeable. The
voice-stress and v2 zeros are consistent with the scope stated here — those
scenarios are persona/cross-turn shaped, which this narrowly-scoped control does
not claim to cover.

## Recorded non-actions

- The engine was **not** changed; the CSV-550 pinned baseline (183/200, 5 FP) is
  byte-for-byte unchanged.
- No expected outcome was weakened, and **no claim was expanded** — the opposite:
  the scope is stated more narrowly than before.
- The independent threat-model review is **framed, not performed** here.
- Acoustic detection remains unclaimed; the only change to detection code was a
  comment correcting a misleading "voice/signal artifacts" description to say it
  matches text markers.
