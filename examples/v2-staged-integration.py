#!/usr/bin/env python3
"""
NHID-Auth v2 — Tier 2 Integration Example (≈ 60 lines)

Demonstrates the full cryptographic identity flow:
  1. Generate provider + agent key pairs
  2. Create a scoped delegation signed by the provider's private key
  3. Issue an agent passport (delegation + provider sig + agent self-sig)
  4. Verify the passport — returns provider NPI + scope on success

Run as a standalone script; requires the cryptography package.
  pip install cryptography
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agent_identity import AgentIdentityManager


def run_tier2_integration():
    manager = AgentIdentityManager()

    # ── Step 1: Generate key pairs ────────────────────────────────────────────
    # In production: provider generates their key once, stores private key securely.
    # Agent keys are generated per-deployment or per-call depending on scope needs.
    provider_private_key, provider_public_key = manager.generate_agent_keys()
    agent_private_key, agent_public_key = manager.generate_agent_keys()

    # ── Step 2: Create a scoped delegation ───────────────────────────────────
    # provider_npi is the 10-digit NPI from NPPES.
    # scope restricts what the agent is authorized to request.
    delegation = manager.create_delegation(
        provider_priv=provider_private_key,
        agent_id="beacon-agent-001",
        agent_pub=agent_public_key,
        scope=["eligibility", "claim_status"],
        provider_npi="1234567890",
        ttl_seconds=3600,           # delegation expires in 1 hour
    )

    # ── Step 3: Sign the delegation as the provider ───────────────────────────
    provider_sig = manager.sign_delegation(provider_private_key, delegation)

    # ── Step 4: Issue the agent passport ─────────────────────────────────────
    # The passport bundles: delegation + provider signature + agent self-signature.
    # This is the artifact the agent presents on each call.
    passport = manager.create_agent_passport(delegation, provider_sig, agent_private_key)

    # ── Step 5: Payer-side verification ──────────────────────────────────────
    # Payer retrieves provider_public_key from their NPI registry cache.
    # In production: public keys are registered via the NHID-Clinical key registry API.
    result = manager.verify_passport(passport, provider_public_key)

    if result.valid:
        print(f"PASS  provider_npi={result.provider_npi}")
        print(f"      agent_id={result.agent_id}")
        print(f"      scope={result.scope}")
    else:
        print(f"FAIL  error_code={result.error_code}")
        sys.exit(1)

    # ── Step 6: Test revocation ───────────────────────────────────────────────
    manager.revoke_delegation(delegation.delegation_id)
    revoked = manager.verify_passport(passport, provider_public_key)
    assert not revoked.valid, "Revoked delegation should fail verification"
    print(f"PASS  revocation confirmed (reason={revoked.reason})")


if __name__ == "__main__":
    run_tier2_integration()
