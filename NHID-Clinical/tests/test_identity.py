import pytest
from src.agent_identity import AgentIdentityManager

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
