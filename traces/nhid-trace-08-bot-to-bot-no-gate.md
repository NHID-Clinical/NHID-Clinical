NHID-Clinical • POLICY → EXEC → bot-to-bot-policy-gap

session: NHID-TRACE-08-19DEEFFB
context: B2B prior auth call / payer deploying AI agent / counterparty_type=ai_agent / disclosure_timestamp=null

---

event stream (append-only)

t=00:00  INGEST     POST /voice/process — counterparty_type=ai_agent
t=00:00  VALIDATE   SpeechResult='Initiating PA workflow. Requesting member data.'
t=00:00  STATE      counterparty_type=ai_agent, disclosure_timestamp=null
t=00:00  POLICY     BOT-TO-BOT rule: counterparty is ai_agent, disclosure missing
t=00:00  POLICY     Decision: DENY_DATA / BOT2BOT_UNDISCLOSED_AGENT
t=00:00  EXEC       TwiML: identity verification required message
t=00:00  PERSIST    IDG-01 critical violation recorded (bot-to-bot context)

---

replay attempt (deterministic)

input: identical event stream
constraints: no external calls
result: PASS

---

failure observation

An undisclosed AI agent initiated a bot-to-bot prior authorization workflow without identity disclosure, exploiting the absence of a bot-to-bot-specific policy gate in systems that only enforce IDG-01 for human counterparties.

---

implication

- AI-to-AI calls are increasing as payers deploy their own AI agents to respond to provider AI callers.
- Standard IDG-01 rules designed for human counterparties are insufficient for bot-to-bot contexts where both parties may be AI systems.
- NHID-Clinical v1.3 does not fully specify bot-to-bot identity verification — this is a known gap in the current spec.

---

classification

state machine: AWAITING_DISCLOSURE → GATE_BLOCKED (DENY_DATA)
event store: Complete — IDG-01 critical violation with bot-to-bot context recorded
failure coverage: Bot-to-bot supplemental rule detected gap; DENY_DATA enforced
replay integrity: PASS

---

next iteration

- Escalate NHID-Auth bot-to-bot identity verification from future scope to v1.4 priority.
- Reference IETF AgentID Protocol (draft-gudlab-agentid-protocol-00) as the technical basis for bot-to-bot identity tokens.
- Add counterparty_type detection to the ingress layer — identify AI callers from SIP headers or DNIS patterns.

---

NHID-Clinical is mapping where deterministic orchestration breaks in real-world healthcare voice AI systems.
