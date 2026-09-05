# Can your reps tell whether an AI caller is authorized?

**A two-page brief for provider-services and payment-integrity leaders**
Brianna Baynard · NHID-Clinical · contact@nhid-clinical.org

---

## The gap

An AI voice agent calls your provider line for eligibility, claim status or
prior authorization. Your representative hears a fluent voice, takes an NPI and
a member identifier, and reads back protected health information.

Between the moment the agent starts talking and the moment your rep could know
it is not a person, protected data has already moved. That interval is the
problem this brief is about. We call it **impersonation latency**.

HIPAA governs who may access PHI and requires minimum-necessary use. It does
not define a real-time handshake that lets a representative confirm, during a
live call, that an automated caller holds delegated authority from the provider
it names. Nothing in the current payer–provider phone workflow closes that gap.

## What a representative can actually verify today

Very little, and less than most operations assume.

| Signal your rep hears | What it establishes |
|---|---|
| A provider NPI | Almost nothing. NPIs are public in NPPES. Anyone can recite a real practice's number. |
| A callback number or caller ID | The trunk, not the authority. It tells you which vendor is calling, not who authorized this call for this member. |
| A fluent, professional voice | Nothing. This is now inexpensive to produce. |
| "I'm calling on behalf of Dr. —" | An assertion. No verification path exists behind it. |

The practical result is that authorization is inferred from familiarity —
a recognized vendor, a plausible script, a number seen before. That is
institutional habit, not verification, and your reps are being asked to carry a
disclosure decision on it.

## What can be checked

NHID-Clinical is a voluntary open proposal — not a standard, not a
certification, not a product — that defines a small set of testable behaviors at
the point where an automated caller meets your organization:

- **Disclosure before data.** The agent identifies itself as automated *before*
  requesting protected information, rather than after.
- **Sequencing.** Protected-data exchange stays behind that disclosure.
- **No human impersonation.** The agent does not claim or imply it is a person.
- **Escalation is honored.** A request for a human is not deflected.
- **An audit record remains.** What was asked, what was disclosed, what was
  withheld, and on whose asserted authority.

There is also an optional cryptographic layer — a provider-signed, scoped,
expiring delegation bound to an NPI and to the call — which is a working
reference implementation, not deployed infrastructure. It is deliberately not
what this brief is asking you to adopt.

**Two things this does not do.** It does not detect a covert agent that never
identifies itself, and it does not prevent impersonation or fraud. It measures
observable conduct on the interaction, and produces evidence about it.

## The offer

**I would like to measure impersonation latency on your own call records, at no
cost, and give you the result.**

Concretely:

- **You provide** 200–1,000 transcripts you already hold from provider-line
  calls — the ones your QA function already reviews. Redacted is fine and
  preferred. De-identified is better.
- **Nothing goes to a cloud service.** There is no hosted scoring endpoint, and
  I am not asking you to send call audio anywhere. The analysis runs as an
  offline batch, in your environment if you prefer, using open-source code you
  can read before you run it.
- **You receive** a short report: how often protected data was requested before
  any disclosure, how often disclosure never occurred, the distribution of the
  interval itself, ten illustrative turns, and draft contract language you could
  put to your automated-caller vendors.
- **Timeline:** two to four weeks, depending on how your transcripts are stored.

**Why the offer is free.** No payer has published this measurement. The
distributions I can show you today come from an authored evaluation corpus I
built — useful for testing the method, not evidence about anyone's production
traffic. Yours would be the first real number. That is worth more to this work
than a fee.

## Why this is worth an hour

You are already making this decision, implicitly, on every automated call that
reaches a representative. The only question is whether you have measured it.

If the rate turns out to be negligible, you have retired a risk with a number
attached, cheaply, and I will say so plainly in the report. If it is not
negligible, you will have found it before an auditor, a regulator or a
journalist did — and you will have the evidence in a form you can act on with
your vendors.

## The ask

One conversation, thirty minutes, with whoever owns provider-line quality or
vendor management. If it goes well, one batch of transcripts.

**Brianna Baynard** — AIGP, ISC² CC. Background in healthcare payer operations;
this problem comes from watching it happen on live eligibility, claims and
prior-authorization lines.

contact@nhid-clinical.org · https://nhid-clinical.org
Code and conformance suite: https://github.com/NHID-Clinical/NHID-Clinical

---

<sub>NHID-Clinical is a voluntary open proposal (specification and documentation
CC BY 4.0; code Apache-2.0). It is not an accredited standard, not a
certification, and not a regulatory requirement. Audit records produced by these
controls may themselves contain PHI or other regulated context; retention,
access control and encryption remain the deploying organization's
responsibility under its own policy and applicable regulation.</sub>
