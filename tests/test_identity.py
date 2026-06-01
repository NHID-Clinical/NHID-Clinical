import pytest
import time
from src.agent_identity import (
    AgentIdentityManager,
    ERR_EXPIRED, ERR_REVOKED, ERR_INVALID_SIG,
    ERR_NONCE_MISMATCH, ERR_SCOPE_VIOLATION, ERR_INVALID_NPI,
    ERR_CHAIN_NARROWING, ERR_CHAIN_TOO_LONG, MAX_CHAIN_DEPTH,
)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_passport(m, agent_id="agent-x", scope=None, ttl=86400,
                   npi="", call_sid="", provider_priv=None, provider_pub=None):
    if scope is None:
        scope = ["eligibility"]
    if provider_priv is None:
        provider_priv, provider_pub = m.generate_agent_keys()
    agent_priv, agent_pub = m.generate_agent_keys()
    d = m.create_delegation(provider_priv, agent_id, agent_pub, scope,
                            ttl_seconds=ttl, call_sid=call_sid, provider_npi=npi)
    sig = m.sign_delegation(provider_priv, d)
    passport = m.create_agent_passport(d, sig, agent_priv)
    return passport, provider_pub, agent_priv, agent_pub


# ── Existing tests (unchanged) ────────────────────────────────────────────────

def test_key_generation():
    m = AgentIdentityManager()
    priv, pub = m.generate_agent_keys()
    assert priv is not None

def test_delegation_creation():
    m = AgentIdentityManager()
    prov_priv, prov_pub = m.generate_agent_keys()
    agent_priv, agent_pub = m.generate_agent_keys()
    delegation = m.create_delegation(prov_priv, "agent-1", agent_pub, ["eligibility"])
    sig = m.sign_delegation(prov_priv, delegation)
    passport = m.create_agent_passport(delegation, sig, agent_priv)
    result = m.verify_passport(passport, prov_pub)
    assert result.valid
    assert result.agent_id == "agent-1"

def test_expired():
    m = AgentIdentityManager()
    prov_priv, prov_pub = m.generate_agent_keys()
    agent_priv, agent_pub = m.generate_agent_keys()
    delegation = m.create_delegation(prov_priv, "agent-2", agent_pub, ["eligibility"], ttl_seconds=0)
    sig = m.sign_delegation(prov_priv, delegation)
    passport = m.create_agent_passport(delegation, sig, agent_priv)
    result = m.verify_passport(passport, prov_pub)
    assert not result.valid
    assert "expired" in result.reason.lower()

def test_revoked():
    m = AgentIdentityManager()
    prov_priv, prov_pub = m.generate_agent_keys()
    agent_priv, agent_pub = m.generate_agent_keys()
    delegation = m.create_delegation(prov_priv, "agent-3", agent_pub, ["eligibility"])
    sig = m.sign_delegation(prov_priv, delegation)
    passport = m.create_agent_passport(delegation, sig, agent_priv)
    m.revoke_agent("agent-3")
    result = m.verify_passport(passport, prov_pub)
    assert not result.valid
    assert "revoked" in result.reason.lower()


def test_nonce_binds_to_call_sid():
    m = AgentIdentityManager()
    prov_priv, prov_pub = m.generate_agent_keys()
    agent_priv, agent_pub = m.generate_agent_keys()
    delegation = m.create_delegation(prov_priv, "agent-4", agent_pub, ["eligibility"], call_sid="CA123")
    assert delegation.nonce != ""
    sig = m.sign_delegation(prov_priv, delegation)
    passport = m.create_agent_passport(delegation, sig, agent_priv)
    assert m.verify_passport(passport, prov_pub, call_sid="CA123").valid
    assert not m.verify_passport(passport, prov_pub, call_sid="CA999").valid


def test_no_nonce_without_call_sid():
    m = AgentIdentityManager()
    prov_priv, prov_pub = m.generate_agent_keys()
    agent_priv, agent_pub = m.generate_agent_keys()
    delegation = m.create_delegation(prov_priv, "agent-5", agent_pub, ["eligibility"])
    assert delegation.nonce == ""
    sig = m.sign_delegation(prov_priv, delegation)
    passport = m.create_agent_passport(delegation, sig, agent_priv)
    assert m.verify_passport(passport, prov_pub).valid
