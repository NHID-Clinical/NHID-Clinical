# Consented Volunteer Call Protocol

**Status:** protocol for your review, NOT executed · **Added:** 2026-10-14 · CC BY 4.0

> A minimal-cost way to get a small amount of **real conversational audio** —
> real people, a real audio channel, the hard acoustic cases — without touching
> a single real patient, real PHI, or any healthcare organization. Volunteers
> act out a provider→payer administrative call using **fictional identities and
> synthetic insurance records**. This produces **tier-4** evidence
> ([`evidence-provenance-matrix.md`](evidence-provenance-matrix.md)): it proves
> the pipeline handles real speech, not that real agents behave this way.
>
> **I have not run any of this.** No calls placed, no participants recruited, no
> recordings made, no organizations contacted. This is a protocol for you to
> review (and, if your jurisdiction/employer requires, run past an ethics/IRB
> or legal reviewer) before you run it.

---

## What this does and does not establish

- **Does:** exercise the audio-input path and the five controls against real
  human speech with background noise, interruptions, overlapping speech,
  pauses, disclosure-timing variation, mid-call contradiction, escalation
  requests, and abrupt termination.
- **Does not:** demonstrate that production healthcare voice agents behave this
  way, or constitute a pilot, deployment, or clinical validation. Acted ≠ real.
  Every result is labelled "scripted consented volunteers, fictional
  identities."

## Hard rules

1. **Adults only, explicit consent**, recorded before any recording begins
   (see [`consent-script.md`](consent-script.md)).
2. **Fictional identities only.** Invented names, synthetic member IDs (clearly
   fake, e.g. `MBR-TEST-0001`), fictional plans, fictional NPIs that are
   format-valid but unassigned. **No real patient, provider, member, or payer
   data, ever.** No participant uses their own real insurance details.
3. **Do not call any real organization.** Both legs are volunteers (or one
   volunteer + your own test agent). Never dial a real payer, provider, clinic,
   or insurer line.
4. **No PHI.** Because identities are fictional, there is no PHI — keep it that
   way; a volunteer must not ad-lib a real person's health information.
5. **Recording consent on both legs**, and comply with your jurisdiction's
   call-recording law (many require all-party consent).

## Roles

- **Caller (agent side):** plays the provider's AI voice agent — or is your
  actual test agent (Retell/VAPI/etc.) if you have one. Follows a scenario card
  that dictates whether/when it discloses it is AI.
- **Receiver (payer side):** plays the payer representative. Follows a card that
  dictates when to ask for identity, when to request escalation, and when to
  push for PHI early.
- **Observer (you):** does not speak; starts/stops recording, logs the scenario
  id and timestamps, and later labels the ground truth.

## Channel

- A real audio channel: a conference bridge, two phones, or a softphone +
  recorder. Stereo capture (one speaker per channel) if possible — it makes
  turn attribution and overlap analysis far cleaner.
- Keep it cheap: a free conferencing tool with local recording is sufficient.
  **No paid service is required**, and none should be purchased on anyone's
  behalf without authorization.

## Session flow (per call, ~5–10 min)

1. Observer states the recording notice; both participants give verbal consent
   on tape.
2. Observer announces the scenario id (e.g. `vol_idg_contradiction_01`) — spoken
   so it is on the recording, and the real identities stay off it.
3. Participants run the scenario card. Inject the planned hard case (noise,
   interruption, contradiction, escalation, early-PHI, hangup).
4. Observer stops recording, notes start/stop times and anything notable.
5. Immediately file the session in the retention log (below).

## The scenarios

Run the matrix in [`scenario-matrix.md`](scenario-matrix.md). It covers, at
minimum: clean disclosed call (negative control), disclosure-then-contradiction
(IDG-01), PHI requested before identity/authorization (PDX-01), valid provider
id but unauthorized for PHI (DLG-01/PDX-01), legitimate escalation request
(EIT-01), abrupt termination, and a social-engineering override attempt — each
with and without an acoustic stressor (noise / interruption / overlap).

## Recording, labelling & retention

- **Store recordings outside this repository**, access-controlled. Never commit
  audio.
- Filename: `vol_<scenario-id>_<take>.wav`, no participant names.
- **Labelling:** for each call, the observer records the ground-truth expected
  control outcomes (which control should fire, at which turn, why) in a sidecar
  JSON matching the corpus scenario shape, so results are comparable to the
  synthetic corpus.
- **Retention:** keep only as long as needed to evaluate; delete raw audio on a
  stated schedule (suggest: delete within 30 days of transcription + labelling
  unless a participant withdraws consent sooner). Transcripts, once stripped of
  the spoken consent segment and verified identity-free, may be kept as
  synthetic-equivalent fixtures.
- **Withdrawal:** any participant may withdraw; on withdrawal, destroy their
  audio and derived transcripts.

## From recording to evidence

1. Transcribe (locally if possible).
2. Confirm the transcript is identity-free (fictional only).
3. Label ground truth → sidecar JSON in the corpus scenario shape.
4. Score through the engine exactly as the synthetic corpus is scored.
5. Report as **tier-4** evidence with the standard four labels (tier, data
   classification = `synthetic` since identities are fictional, denominator,
   limitation). Never as deployment or healthcare-use evidence.

**Recorded non-actions:** no participants recruited, no calls placed, no
recordings made, no organizations contacted, no services purchased.
