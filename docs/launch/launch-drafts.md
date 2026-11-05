# NHID-Clinical launch drafts

**Direction, every time:** the AI agent *places* the call to the insurer and asks for a patient's eligibility, claim or authorization status. The insurer's representative *receives* the call. The agent never answers a call, never speaks as the insurer, and never asks the representative for the patient's own identifiers. `tests/test_call_direction.py` checks this file.

These are drafts for you to post. Nothing has been posted. Every line was checked against `docs/claim-boundaries.md`, so:

- the project is described as a research project and open reference implementation that is pre-launch;
- the drafts never say "HIPAA compliant", "certified", "deployed" or "used by", and never name a payer;
- the statistics use only the wording approved in `docs/validation/voice-fraud-statistics.md`, and each one is marked as not being a measurement of NHID-Clinical.

Post on the same day, in this order: the X thread in the morning, Show HN about an hour later, Reddit in the afternoon. Link the repo everywhere: https://github.com/NHID-Clinical/NHID-Clinical

---

## 1. X thread (6 posts)

**1/**
AI agents are phoning insurance companies right now, asking for patients' eligibility and claim status.

The person who picks up has a few seconds to decide whether the caller is a human, an AI, or who it actually works for.

Usually nothing checks. So I built an open check for it. 🧵

**2/**
The scenario: "Hi, calling from Dr. Patel's office about a prior auth for member ID 4471-882. Can you tell me the status?"

Does it say it's automated? Before or after it asks for the patient's information? Does it claim to be a nurse? If the rep asks for a human, does it hand off?

**3/**
NHID-Clinical checks every turn against 5 open controls:

• IDG-01: disclose you're an AI
• PDX-01: no protected data before that disclosure
• DBC-01: don't claim to be a human or a licensed professional
• EIT-01: hand off to a human when asked
• ATR-01: leave an audit trail of every call

**4/**
It's deterministic and open source (Apache-2.0), and it runs offline.

Try it in 30 seconds:

pip install -e .
nhid pilot --demo

Out of 3 synthetic calls: one gave a member's ID and asked for the claim status before admitting it was automated, and one refused a human handoff.

**5/**
What it doesn't do: verify who the caller is, detect deepfaked audio, or make anything "compliant".

It measures disclosure and data sequencing, which is the baseline any later verification step builds on.

It's a research project, pre-launch, with an offline pilot kit available.

**6/**
If you build voice agents, run a payer contact center, or work on AI governance, I'd love your eyes on it. Stars and issues help a lot. ⭐

github.com/NHID-Clinical/NHID-Clinical

---

## 2. Standalone posts (one a day after launch)

**A, the stat hook** (vendor figure, quoted exactly as approved):
> Pindrop reported a 475% increase in synthetic voice fraud attacks on insurance companies in 2024, from its analysis of more than 1.2 billion customer calls (vendor-reported).
>
> Most payer phone lines still can't tell whether a caller is an AI. I'm building an open check for that moment: github.com/NHID-Clinical/NHID-Clinical

**B, the builder angle:**
> If your voice agent calls insurers, here's a free test: does it say it's automated *before* it asks for a patient's eligibility or claim status?
>
> `nhid pilot --demo` shows what a failing call looks like. Open source, offline.

**C, the "identity ≠ authority" point:**
> An AI saying "I'm an automated assistant for Lakeside Clinic" proves nothing about whether it's allowed to receive that patient's data. NPIs are public; anyone can quote one.
>
> Disclosure is step one, not the finish line. That distinction is built into NHID-Clinical's controls.

**D, the build-in-public post:**
> Measured my own privacy scanner today. I planted 520 fake identifiers in synthetic calls. The released pack contained 0 of them, but the backstop scan misses names, all-digit IDs and ISO dates. Wrote it all up instead of hiding it: [link to docs/validation/share-safe-leakage.md]

---

## 3. Show HN

**Title:**
Show HN: NHID-Clinical – open checks for AI agents that phone insurers for patient data

**Text:**
AI voice agents now call health insurers on behalf of providers, to check eligibility, claim status and prior auths. The rep on the other end has to decide in seconds whether the caller is a person or an AI, and whether it can receive what it's asking for.

NHID-Clinical is an open specification plus a deterministic Python reference implementation for that moment. It has five controls, evaluated on every turn:
- disclose that you're an AI;
- no protected data before that disclosure;
- don't pose as a human or a licensed professional;
- hand off to a human when asked;
- keep an audit trail.

The most restrictive decision wins (DENY_DATA > ESCALATE_HUMAN > …), and there is no composite score.

`pip install -e . && nhid pilot --demo` runs the measurement on synthetic calls offline. `--share-safe` produces a pack with pseudonymised call ids that is scanned before release. I measured that scan with planted values and published where it falls short.

Limits, stated up front:
- It reads transcripts, so it inherits the speech-to-text system's errors.
- It doesn't verify identity or authority on its own.
- It doesn't analyse audio for deepfakes.
- It isn't a certification.

It's a research project, pre-launch. I'd especially value feedback from people who run payer contact centers or build voice agents.

Code is Apache-2.0; spec and docs are CC BY 4.0.

---

## 4. Reddit

Post in r/healthIT first. Then r/VoiceAI and r/LocalLLaMA (lead with the offline part), and r/opensource. Read each subreddit's self-promotion rules first; some want a ratio of non-promo posts.

**Title:** I built open-source checks for AI agents that call insurance companies for patient data

**Body:** use the Show HN text, plus one line at the start: "Solo project, looking for honest feedback, especially from people on the payer side."

---

## 5. Reply templates (under big posts about voice AI or healthcare AI)

Replies only work if they add something to the post. Never paste the link alone.

- **Under a voice-agent launch** (Retell, Vapi, Bland, ElevenLabs agents):
  > Curious how this handles calls to insurers. Does the agent disclose it's an AI before it asks for a patient's eligibility or claim status? That ordering is exactly what payer reps can't check today. I've been building open tests for it.
- **Under "AI will handle all phone calls" takes:**
  > The receiving side is the gap. When an AI calls a payer, the rep has no way to know what it is or who it really works for. Disclosure-before-data is the minimum bar, and it's testable.
- **Under deepfake or voice-fraud news:**
  > Worth separating two problems: detecting a fake voice (acoustic), and making honest AI callers identify themselves before asking for data (behavioral). The second one is tractable today.

Add the link only if someone asks or the thread invites it.

---

## Before you post

- [ ] Merge the README PR, so the 30-second demo is the first thing visitors see.
- [ ] Pin the X thread on your profile.
- [ ] Add repo topics on GitHub: `ai-agents`, `voice-ai`, `healthcare`, `ai-governance`, `hipaa` (a topic tag, not a claim), `llm-safety`.
- [ ] Turn on GitHub Discussions, so curious visitors have somewhere to land.
- [ ] Don't ask for stars in replies, only in your own thread.
