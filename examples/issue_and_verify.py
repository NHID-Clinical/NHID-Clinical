"""
NHID-Clinical v2 — Agent Passport: issue, verify, revoke

Run this directly:
    python examples/issue_and_verify.py

What it demonstrates:
    1. Generate provider and agent keypairs
    2. Issue a scoped, NPI-bound delegation
    3. Verify the passport (happy path)
    4. Verify with a scope check (passes and fails)
    5. Revoke one delegation, verify another for the same agent still works
    6. Build and validate a 2-hop delegation chain
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.agent_identity import AgentIdentityManager, ERR_SCOPE_VIOLATION, ERR_REVOKED

PROVIDER_NPI = "1234567890"


def section(title):
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


def main():
    m = AgentIdentityManager()

    # ── 1. Key generation ─────────────────────────────────────────
    section("1. Generate keypairs")
    prov_priv, prov_pub = m.generate_agent_keys()
    agent_priv, agent_pub = m.generate_agent_keys()
    print(f"  Provider pubkey : {m.public_key_to_b64(prov_pub)[:24]}…")
    print(f"  Agent pubkey    : {m.public_key_to_b64(agent_pub)[:24]}…")

    # ── 2. Issue delegation ────────────────────────────────────────
    section("2. Issue NPI-bound delegation")
    delegation = m.create_delegation(
        prov_priv, "voice-agent-001", agent_pub,
        scope=["eligibility", "claim_status"],
        provider_npi=PROVIDER_NPI,
        ttl_seconds=3600,
    )
    print(f"  NPI             : {delegation.provider_npi}")
    print(f"  Delegation ID   : {delegation.delegation_id}")
    print(f"  Scope           : {delegation.scope}")
    print(f"  Expires in      : {(delegation.expires_at - delegation.created_at) // 60} minutes")

    # ── 3. Sign and package as passport ───────────────────────────
    section("3. Create agent passport")
    sig = m.sign_delegation(prov_priv, delegation)
    passport = m.create_agent_passport(delegation, sig, agent_priv)
    print(f"  Provider sig    : {passport.signature_b64[:24]}…")
    print(f"  Agent sig       : {passport.agent_signature_b64[:24]}…")

    # ── 4. Verify — happy path ─────────────────────────────────────
    section("4. Verify passport (happy path)")
    result = m.verify_passport(passport, prov_pub)
    print(f"  Valid           : {result.valid}")
    print(f"  Reason          : {result.reason}")
    print(f"  Provider NPI    : {result.provider_npi}")
    print(f"  Agent ID        : {result.agent_id}")
    assert result.valid

    # ── 5. Verify — scope enforcement ─────────────────────────────
    section("5. Scope enforcement")

    r_pass = m.verify_passport(passport, prov_pub, required_scope=["eligibility"])
    print(f"  eligibility     : {'PASS' if r_pass.valid else 'FAIL'} (expected: PASS)")
    assert r_pass.valid

    r_fail = m.verify_passport(passport, prov_pub, required_scope=["prior_auth"])
    print(f"  prior_auth      : {'PASS' if r_fail.valid else 'FAIL'} (expected: FAIL)")
    print(f"  Reason          : {r_fail.reason}")
    assert not r_fail.valid
    assert ERR_SCOPE_VIOLATION in r_fail.reason

    # ── 6. Delegation-level revocation ────────────────────────────
    section("6. Per-delegation revocation")

    # Issue a second delegation for the same agent
    delegation2 = m.create_delegation(
        prov_priv, "voice-agent-001", agent_pub,
        scope=["eligibility"],
        provider_npi=PROVIDER_NPI,
    )
    sig2 = m.sign_delegation(prov_priv, delegation2)
    passport2 = m.create_agent_passport(delegation2, sig2, agent_priv)

    # Revoke only the first delegation
    m.revoke_delegation(delegation.delegation_id)

    r1 = m.verify_passport(passport, prov_pub)
    r2 = m.verify_passport(passport2, prov_pub)
    print(f"  Passport 1 (revoked)  : {r1.reason} (expected: {ERR_REVOKED})")
    print(f"  Passport 2 (active)   : {'PASS' if r2.valid else 'FAIL'} (expected: PASS)")
    assert not r1.valid and r1.reason == ERR_REVOKED
    assert r2.valid

    # ── 7. Two-hop delegation chain ───────────────────────────────
    section("7. Two-hop delegation chain (monotonic narrowing)")

    mid_priv, mid_pub = m.generate_agent_keys()
    leaf_priv, leaf_pub = m.generate_agent_keys()

    # Provider → mid-agent (broad scope)
    d1 = m.create_delegation(prov_priv, "orchestrator-001", mid_pub,
                             scope=["eligibility", "claim_status", "prior_auth"],
                             provider_npi=PROVIDER_NPI)
    s1 = m.sign_delegation(prov_priv, d1)
    p1 = m.create_agent_passport(d1, s1, mid_priv)

    # Mid-agent → leaf (narrowed scope — only eligibility)
    d2 = m.create_delegation(mid_priv, "voice-leaf-001", leaf_pub,
                             scope=["eligibility"])
    s2 = m.sign_delegation(mid_priv, d2)
    p2 = m.create_agent_passport(d2, s2, leaf_priv)

    chain_result = m.validate_chain([p1, p2], prov_pub)
    print(f"  Chain valid     : {chain_result.valid}")
    print(f"  Root NPI        : {chain_result.provider_npi}")
    print(f"  Leaf agent      : {chain_result.agent_id}")
    print(f"  Effective scope : {chain_result.scope}")
    assert chain_result.valid
    assert chain_result.provider_npi == PROVIDER_NPI
    assert chain_result.scope == ["eligibility"]

    # ── Done ──────────────────────────────────────────────────────
    section("All checks passed")
    print()
    print("  An attacker with only public NPPES data cannot produce")
    print("  a valid Ed25519 signature over the delegation payload.")
    print("  That is the core v2 guarantee.")
    print()


if __name__ == "__main__":
    main()
