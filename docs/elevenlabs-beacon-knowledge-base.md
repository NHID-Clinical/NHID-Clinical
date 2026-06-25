# Beacon — ElevenLabs Knowledge Base Setup

Operational checklist for adding a Knowledge Base to the Beacon agent
(`agent_4001krn32nmwe5t8mqzgee0w84rj`, see `agents/beacon_system_prompt.md`).
Like `docs/elevenlabs-compass-setup.md`, this is a checklist, not new product
code — it's a one-time dashboard configuration, with the document content
drafted below so it can be pasted in directly.

## Why this is different from Compass's Knowledge Base

Compass is a general FAQ widget: a Knowledge Base closes the gap between "what's
hardcoded in the prompt" and "what a site visitor might ask." Beacon is not that
kind of agent — it's a narrow, scripted outbound caller (disclosure → consent →
verification → claim status → end call) whose IDG-01/PDX-01/DBC-01/EIT-01/IDG-02
behavior is run through the CTS conformance runner and must be deterministic.

That means the Knowledge Base for Beacon has a **strict scope boundary**:

- It supplies answers to off-script questions a payer rep might reasonably ask
  during the call (e.g. "what's your callback number," "what's your Tax ID")
  that the scripted prompt doesn't already cover.
- It must **never** supply or alter the disclosure, consent, or escalation
  wording itself. Those stay fixed, locked strings in the `prompt` fence in
  `agents/beacon_system_prompt.md` — ElevenLabs' Knowledge Base retrieval is
  RAG-based and not deterministic, which is incompatible with a conformance
  suite that expects the same gate behavior every run.
- If anything in a Knowledge Base document ever appears to conflict with the
  prompt fence's disclosure/consent/escalation text or the locked
  "Impersonation Latency" term, the prompt fence wins, full stop.

## What to load in

Beacon doesn't reference any site URLs during a call, so this isn't a URL-scrape
list like Compass's. These are three short **pasted-text** documents — paste
each one as-is into the dashboard's **Knowledge Base → Add document → Paste
text** flow. All three use the same synthetic/demo placeholder values already
established in the prompt fence (NPI `1234567890`, member ID `MID7890123`,
"123 Ocean Blvd, New York") — none of this is real PHI or a real practice.

### Document 1 — Provider & Practice Reference

```text
Provider & Practice Reference (demo data)

Practice: a provider's office on behalf of a dental facility
Address: 123 Ocean Blvd, New York
Billing NPI: 1234567890
Tax ID (EIN): 12-3456789
Callback number: (555) 010-7890
Fax: (555) 010-7891
Business hours: Monday-Friday, 9:00 AM - 5:00 PM Eastern

Use this only to answer a payer representative's direct ad hoc questions during
a call (e.g. "what's your Tax ID," "what's your fax number," "what are your
hours"). Never use it to alter or skip the disclosure, consent, or verification
steps defined in the system prompt — those happen exactly as scripted regardless
of what's in this document.
```

### Document 2 — NHID-Auth v2 Authorization Detail

```text
NHID-Auth v2 Authorization Detail (IDG-02 backup reference)

Beacon operates under a provider-issued Ed25519 agent passport. If asked for
more detail than the standard IDG-02 disclosure already gives:
- The passport binds Beacon's operating identity to the authorizing provider's
  NPI (1234567890 in this demo).
- The delegation chain scope for this demo is limited to: initiating outbound
  claim-status verification calls on the provider's behalf. It does not grant
  authority to negotiate claims, authorize payments, or change PHI/PII on file.
- A payer representative (or their compliance team) can independently verify a
  presented passport via POST /v1/identity/verify-passport, and check whether a
  delegation has been revoked via the same conformance API
  (see functions/handler.py and src/agent_identity.py in the NHID-Clinical repo,
  https://github.com/NHID-Clinical/NHID-Clinical).

This is supplementary detail only. The IDG-02 disclosure itself (that Beacon
holds a provider-issued passport, the NPI binding, and the delegation scope) is
already given proactively per the system prompt when asked — this document
exists for follow-up questions that go deeper than that baseline disclosure.
```

### Document 3 — Alternative Contact Path

```text
Alternative Contact Path (EIT-01 no-transfer fallback)

This demo has no live human transfer destination configured. When Beacon tells
a caller "please call back during business hours or contact us at a different
number," the number/hours it means are:

Callback number: (555) 010-7890
Business hours: Monday-Friday, 9:00 AM - 5:00 PM Eastern

If the payer representative asks "what number is that" or "what hours," give
these. Do not invoke any transfer tool — none is configured, and a transfer
attempt with no destination leaves the line dead instead of resolving the
request (this is the EIT-01 control requirement in the system prompt).
```

## Configuration once documents are added

1. **Usage mode**: leave each document set to **Auto** (retrieved only when
   relevant), same as Compass — never **Prompt** mode, which would inject all
   three documents into every single turn regardless of whether the payer rep
   asked anything that needs them.
2. **RAG toggle**: the combined size of these three documents is small enough
   that RAG isn't strictly necessary the way it is for Compass's much larger
   page set, but turning it on is harmless and keeps the configuration
   consistent across both agents. Leave Advanced embedding-model defaults as-is.
3. **Source attribution**: optional here — unlike Compass, Beacon isn't citing
   pages back to a human researching a claim, so this is lower-value than it is
   for Compass, but it doesn't hurt to enable it for consistency.
4. **Do not** add any document containing the disclosure, consent, or
   escalation script text itself, or anything that paraphrases the locked
   "Impersonation Latency" term — that content's only home is the `prompt`
   fence in `agents/beacon_system_prompt.md`, where the CTS runner expects it.

## Why this isn't already wired into `scripts/sync_agent_config.py`

Same reasoning as Compass's setup doc: Knowledge Base documents are a separate
ElevenLabs resource (`POST /v1/convai/knowledge-base/text`, returning a
`document_id`) attached to an agent via its `conversation_config.agent.prompt
.knowledge_base` array, not part of the agent object the sync script already
pushes (`voice_id`/`llm`/`text_only`/`workflow`). Setting it up once through the
dashboard, with the three short documents above, is lower-risk than writing and
testing new sync-script code against an API this repo has never had a live key
to exercise. Once confirmed working, pulling the resulting `document_id`s into
`agents/beacon.config.json` (mirroring the existing pattern) is a reasonable
follow-up, not a blocker for this checklist.
