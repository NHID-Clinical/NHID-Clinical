# Ida, the reference caller-agent

Ida is an open reference agent for the canonical NHID-Clinical scenario. She
**places** a call to a payer's provider line for a fictional dental practice and
asks for one claim's status. The payer's representative receives the call, and
the patient is not on it. Ida is a demonstration. She is not a product, she is
not certified, and she holds no real credentials.

Ida exists for two reasons:

1. **To show the controls on a live call.** She says the disclosure first and asks
   the gate before she speaks any patient identifier.
2. **To show what proving authority looks like.** She carries a per-call
   delegation from the practice, and the payer side checks it before PHI moves.

A builder of a caller-agent can fork her. A payer can see what a caller-agent
that proves its authority would hand them.

## The three parties

| Party | Holds | Code |
| :-- | :-- | :-- |
| **The practice** (issuer) | its root signing key; signs one delegation per call | `src/reference_agent.py` `PracticeIssuer` |
| **Ida** (the caller-agent) | her own key; co-signs the passport and answers the gate's challenge | `src/reference_agent.py` `ReferenceAgentSigner` |
| **The payer gate** (verifier) | its trust anchors (`NHID_TRUST_ANCHORS`) and the challenges it issued | `functions/handler.py` `gate_turn`, `src/gate_challenges.py` |

In the demonstration, all three run in one deployment with separate keys, so
the flow can be shown end to end. In a real deployment each one is a different
organization. The code paths share no keys and no state.

## One gated turn

Before Ida says a member ID, a date of birth or a claim number, her `nhid_gate`
tool calls `POST /v1/ida/gate` with the sentence she plans to say. Then:

1. **Delegation.** The practice signs a delegation for this one call. It holds
   Ida's public key, the call id, the scope (`claim_status`, the claim-status
   workflow) and a 15-minute expiry. Ida co-signs it, and the result is an
   NHID-Auth v2 `AgentPassport`.
2. **Challenge.** The payer gate issues a fresh, random nonce for the call
   (`POST /v1/gate/challenge`). The verifier picks the nonce, never the caller.
3. **Proof of possession.** Ida signs the nonce with the key her delegation
   names (`PresentationProof`). Someone who captured her passport bytes cannot
   do this.
4. **Presentation.** The passport and the proof go to `POST /v1/gate/turn` with
   the sentence, out of band over HTTPS. The gate puts them in front of DLG-01
   with a `DelegationContext` that requires all of these:
   - a delegation, checked against the payer's own trust anchors;
   - a binding to this call's id;
   - a proof of possession over the gate's live challenge;
   - a revocation check;
   - scope enforcement, so PDX-01 lets through only what the delegation covers.

The answer is the engine's usual decision, plus `delegation_checked: true`.
DLG-01 denies when any of these is true, and the composite is then `DENY_DATA`:

- the passport is for another call;
- it has expired or been revoked;
- it was signed by a practice the payer does not trust;
- its scope was altered;
- the proof is missing, stale or signed by another key.

A request outside the scope, such as a prior authorization number on a
claim-status delegation, gets `PDX01_SCOPE_NOT_AUTHORIZED`. If the payer has no
trust anchors configured, a presented passport gets a 503, never a silent pass.
Without a passport, the gate behaves as before (`delegation_checked: false`).

`tests/test_ida_reference_agent.py` covers each of these cases.

## No new control

DLG-01 is the existing opt-in delegated-authority check. This change adds a way
to present a passport at the gate and nothing else. It adds no control, outcome
or score. The decision is still the most restrictive across the controls.

## Why not a spoken code, and why not the phone network

- **A code spoken on the call** can be heard, recorded and replayed, and the
  representative cannot check it.
- **STIR/SHAKEN and Rich Call Data** prove which number and which brand placed a
  call. They do not prove that this agent may receive this patient's
  information.
- **The pattern used here** is a short-lived delegation, bound to the call, with
  a proof over a verifier challenge, presented out of band. It is the same
  shape as OAuth token exchange (RFC 8693) and the IETF OAuth working group's
  identity-chaining draft. Mapping NHID-Auth to those profiles is open work.

## Run it

```
python scripts/ida_demo_credentials.py --selftest   # one gated turn, in-process, fresh keys
python -m pytest tests/test_ida_reference_agent.py -q
```

To deploy the demonstration line, run `python scripts/ida_demo_credentials.py`
and put the values it prints in the shell or the secret store, never in a file
or a commit. Then follow [`elevenlabs-demo.md`](elevenlabs-demo.md). Its
`nhid_gate` tool points at `/v1/ida/gate`.

## Fork it

**Open in this repository:**
- the prompt and first message (`agents/ida_system_prompt.md`);
- the config placeholder (`agents/ida.config.json`) and the loader
  (`src.reference_agent.load_definition`);
- the signer and issuer (`src/reference_agent.py`);
- the gate (`functions/handler.py`, `src/gate_challenges.py`);
- the credential script.

**Not in the repository:**
- the ElevenLabs agent ID, the webhook secret and the phone number;
- every private key.

To make Ida act for your own organization:
1. Mint your own issuer key and keep it in your own key store.
2. Give the payer your public key out of band, as an `NPI:public-key:kid` entry.
3. Swap in your practice details.
4. Narrow `IDA_SCOPE` to the workflow you need.

## Demonstration keys only

- `scripts/ida_demo_credentials.py` mints keys for a fictional practice with
  the fictional NPI `1234567893`.
- They live in environment variables or `NoEcho` deploy parameters, never in
  the repository.
- In the demonstration, one deployment holds both the issuer key and the
  verifier's trust anchor. It therefore shows the mechanism. It does not show
  that any real organization authorized Ida.

## Open questions

These are open, and nothing here closes them (each is a decision in
[`production-readiness.md`](production-readiness.md)):
- key custody in an HSM or KMS;
- trust-anchor discovery and revocation across organizations;
- a registry from NPI to key;
- carrying the credential on the call itself (SIP);
- a mapping to the HIPAA verification requirement.

The challenge store is in-process, so a scaled-out deployment needs a shared
store.

The project is at the Research stage (`claim-boundaries.md`).

**When the payer's AI answers.** The same gate, with `counterparty: "ai_agent"`, and a reference payer-side agent that releases only after a verified delegation: [`agent-to-agent-calls.md`](agent-to-agent-calls.md).
