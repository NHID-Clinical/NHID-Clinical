# Pilot offer: measure what AI callers are doing on your lines

**For:** payer operations, contact-center and provider-services leaders
**Stage:** NHID-Clinical is in the Research stage, an independent research project and
open reference implementation with a commercial product in development. A Tier 0 shadow
pilot is available. See [claim-boundaries.md](claim-boundaries.md#stage) for what that
means and what it does not.

> **Keep your data.** You run one container on your own machine, with networking
> switched off. Your call data never leaves your building. If you choose to share
> results, you send an aggregate pack that your privacy team has reviewed first.

---

## The problem

AI voice cloning is now cheap. In February 2024 the FCC ruled that calls using
AI-generated voices are "artificial" under the TCPA. Pindrop reported a 475% increase in
synthetic-voice fraud attacks on insurance companies in 2024, from more than 1.2 billion
calls it analysed. Both are sourced, with what they do and do not measure, in
[voice-fraud-statistics.md](validation/voice-fraud-statistics.md). Neither is a
measurement of NHID-Clinical.

Automated callers now phone payer lines and ask for eligibility, claim status and other
protected health information on behalf of providers. Your representatives have to decide,
in the moment, whether the caller is who it says it is and whether it may receive what it
asks for. A caller that sounds like a person, or quotes a provider's public NPI, has
established neither.

Most teams cannot yet answer simple questions about this traffic: how many calls are
automated, how long before the caller says so, and how often protected data moves before
it does.

## The pilot

A **Tier 0 shadow pilot**: two to four weeks, observe-only.

- **Nothing changes on your calls.** No vendor changes, no live enforcement, no new
  step for representatives.
- **It runs on your machine.** You export call turns you already capture into a simple
  per-turn format ([minimal-event-schema.json](pilot-kit/minimal-event-schema.json)) and
  run one command. The kit makes no network calls; a build check enforces that.
- **What you share is up to you, and checked first.** `nhid pilot --share-safe` writes a
  pack with call identifiers replaced by pseudonyms, scans every file for transcript text
  and identifier patterns, and releases it only if the scan passes. Your privacy team
  reviews its manifest before anything is sent. The scan is a pattern check, not
  de-identification; the [kit README](pilot-kit/README.md#sharing-the-pack-without-patient-data)
  says exactly what it can and cannot catch.

## Running it

```bash
docker build -f Dockerfile.pilot -t nhid-pilot .
docker run --rm --network none -v "$PWD:/data" nhid-pilot \
    pilot /data/calls.jsonl --share-safe --out /data/pilot-evidence
```

`--network none` gives the container no network interface except loopback, so it cannot
reach anything outside your machine, whatever the code inside it does. Without Docker, `pip install -e .` and `nhid pilot` run the same kit.

## What you get back

Measured on your own traffic, each figure with its own denominator:

- **Impersonation Latency**: turns and seconds until an automated caller first discloses
  that it is automated.
- **First-turn disclosure rate** and **never-disclosed rate**.
- **Calls with protected data requested before disclosure.**
- **Escalation honor rate**: when a human was asked for, was one provided.
- **Per-control findings** against the open controls (IDG-01, PDX-01, DBC-01, EIT-01,
  ATR-01), call by call.

These are measurements of your traffic, not a certification, a compliance finding or a
score. The accuracy of the replay depends on your transcription; the report records how
much of it was checked. How much a phone line and a transcriber change detection is being
measured separately on synthetic speech
([phone-audio-robustness.md](validation/phone-audio-robustness.md)); that measurement has
not been run with real speech engines yet.

## What we never receive

Transcripts, recordings, member data or your call identifiers. If you choose to share
results, you send the share-safe pack yourself. Nothing sends it for you.

## What this is not

Not a certification, not a standard, not a compliance product, and not yet deployed in
production anywhere. It does not verify a caller's identity on its own: the pilot
measures disclosure and data-sequencing behaviour, which is the baseline a later
verification step builds on.

## What we ask of you

- A sponsor in operations or the contact center, and someone who can export call turns.
- About two hours of setup time and a short review call at the end.
- Permission, or not, to describe the pilot. You are never named without written consent.

**Terms:** *[to be set per pilot]*

## Next step

A 30-minute call to see whether your call data can be mapped to the capture format.
Contact: contact@nhid-clinical.org
