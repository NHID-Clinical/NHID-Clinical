# NHID-Clinical — instructions for Claude Code sessions

Read this before changing code, documentation, website content, diagrams, demos, tests
or presentations in this repository.

---

## 1. The canonical scenario — never reverse these roles

**A caller-agent telephones a payer and asks for a patient's protected information.**

The **caller** is an agent that contacts a payer's customer service agent or medical
claims associate. It claims to be a healthcare provider, or to be acting on behalf of
one, and requests a patient's eligibility information, claim status or other protected
health information (PHI). **Its identity and its authority to receive that information
have not yet been sufficiently established.**

The **receiving party** is the payer's customer service agent or medical claims
associate, who takes the request and must apply the identity, authorization and
disclosure controls.

NHID-Clinical addresses the risk that **the receiving party, or a connected workflow,
discloses PHI to an unverified or unauthorized requesting agent.**

### The five actors

| Actor | Role |
| :-- | :-- |
| **Requesting caller-agent** | The party whose identity and authority must be established. Places the call. |
| **Receiving payer employee** | The customer service agent or medical claims associate handling the incoming request. |
| **Patient** | The person whose eligibility, claim status or PHI is being requested. **Not necessarily on the call.** |
| **Provider or represented organization** | The organization the caller claims to represent or act for. **A claim of affiliation establishes neither identity nor delegated authority.** |
| **Protected asset** | Patient eligibility information, claim status, and other applicable PHI. |

### Never

- Never reverse the caller and the receiver.
- Never describe the scenario as a patient calling a voice agent, or as the agent
  answering an incoming call, **unless** you are explicitly documenting a separate
  scenario outside this canonical model.
- The one documented exception already in the repository is
  [`docs/payer-initiated-calls.md`](docs/payer-initiated-calls.md), a policy-extension
  guide for the reverse direction (a payer's agent calling a provider). It names the
  canonical direction first and labels itself an extension. Keep it that way.

Full statement, with the known conflicts recorded:
[`docs/canonical-threat-model.md`](docs/canonical-threat-model.md).

---

## 2. The control objective

**Evaluate the requesting agent's identity and authority before permitting disclosure of
protected information.**

Three distinctions that are not interchangeable, and that the controls do not collapse:

- **Identity disclosure is not identity verification.** IDG-01 establishes that the
  agent said what it is. It does not establish that the claim is true.
- **Identity verification is not authorization.** NHID-Auth can verify a signature and a
  provider binding. That does not establish authority to receive *this* information.
- **An asserted provider affiliation establishes neither.** NPIs are public; anyone can
  quote one.

When the required checks are not satisfied, apply the existing policy outcome — denying
data access or escalating to a human. **Logging an event, or disclosing identity, does
not authorize disclosure.** `docs/terminology.md` states the same point for Impersonation
Latency: a disclosed agent may still be unauthorized, and an undisclosed one may be
perfectly authorized.

---

## 3. Preserve, do not reinvent

- **Five controls**: IDG-01, PDX-01, DBC-01, EIT-01, ATR-01. DLG-01 is opt-in. There is
  no sixth control: VER-01 call verification, when enabled
  (`DelegationContext.require_call_verification`), runs inside DLG-01.
  Outcome-truthfulness remains a named non-capability.
- **Enforcement ladder**: `DENY_DATA > ESCALATE_HUMAN > DISCLOSE_IDENTITY > LOG_ONLY >
  CONTINUE_AI`. The composite is the most restrictive decision across the controls.
- **There is no composite score.** The Call Authorization Score, its trust tiers and its
  badges are withdrawn, and nothing replaces them under another name — guarded
  structurally by `tests/test_v132_scope_corrections.py`.
- Do not invent new controls, outcomes, metrics or guarantees. Do not change control
  semantics to make a test pass.
- **Pinned baselines** (`scripts/check_baseline.py`) move only with a recorded decision
  in `docs/MASTER-KNOWLEDGE-ARCHIVE.md` §9.1, in the same commit.
- Before pushing: `python scripts/verify_all.py` (expects 9/9). The suite's 0-skipped
  invariant holds only with the API running — `uvicorn app:app --port 8000`.

---

## 4. Positioning and accuracy constraints

NHID-Clinical is an early-stage healthcare technology project built on an open
reference implementation. Its stage is always stated, never implied, and moves only on
evidence:

1. **Research** (current): an **independent research project and reference
   implementation**.
2. **Pilot-ready**: a supervised Tier 0 shadow pilot can be offered. It runs on the
   payer's own machine and produces a share-safe pack (`nhid pilot --share-safe`).
3. **Piloting**: an organization is named only with its written consent.
4. **Deployed**: production use, with evidence on file.

Early-stage product development and marketing are allowed: describing the pilot offer,
the product in development and what the kit measures. Never claim production deployment,
healthcare-provider or payer adoption, HIPAA compliance or HIPAA certification, or
independent validation without verifiable evidence. `docs/claim-boundaries.md` is the
authority for the current stage, what may be claimed at it and in what words; check any
external-facing change against it.

**If an existing implementation or document conflicts with this threat model, flag the
conflict rather than silently redefining the system's behavior.** One such conflict is
already recorded: see the `caller_role` note in `docs/canonical-threat-model.md`.

---

## Agent skills

### Issue tracker

Issues live in GitHub Issues for NHID-Clinical/NHID-Clinical. See `docs/agents/issue-tracker.md`.

### Triage labels

The five default triage labels: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context. The glossary is `docs/terminology.md` and decisions are recorded in `docs/MASTER-KNOWLEDGE-ARCHIVE.md` §19. See `docs/agents/domain.md`.

---

<!-- BEGIN AWS Agent Toolkit rules -->
## AWS Guidance

- Where these AWS rules conflict with the project's own instructions, the
  project's instructions take precedence.
- Prefer the AWS MCP Server for AWS interactions — it provides sandboxed
  execution, observability, and audit logging. If unavailable, use the
  AWS CLI directly.
- Before starting a task, check whether a relevant AWS skill is available.
  Load the skill with `retrieve_skill` and prefer its guidance over
  general knowledge.
- When uncertain about specific AWS details (API parameters, permissions,
  limits, error codes), verify against documentation rather than guessing.
  State uncertainty explicitly if you cannot confirm.
- When creating infrastructure, prefer infrastructure-as-code (AWS CDK or
  CloudFormation) over direct CLI commands.
- When working with infrastructure, follow AWS Well-Architected Framework
  principles.
- Do not use em dashes in AWS resource names or descriptions. Use
  hyphens instead.

### Secret Safety

- MUST load the `aws-secrets-manager` skill first for any secret,
  credential, API key, token, or password task. MUST NOT call
  `secretsmanager get-secret-value` or `batch-get-secret-value`, and MUST
  NOT hit the Secrets Manager Agent daemon directly. MUST use
  `{{resolve:secretsmanager:secret-id:SecretString:json-key}}` with
  `asm-exec` so the secret resolves at runtime without entering context.
<!-- END AWS Agent Toolkit rules -->
