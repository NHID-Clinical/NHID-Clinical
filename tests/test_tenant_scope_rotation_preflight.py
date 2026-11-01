"""
Tenant scoping for attestations and screening, key rotation, and startup checks.

1. ``/v1/attest/verify`` and ``/v1/payer/screen`` read one ``attestations``
   table with no tenant column, so any key holder could inspect or screen any
   customer's reference id. Each attestation now records its tenant, and both
   routes see only the caller's own.
2. A tenant's API key, and the audit signing keys, could not be changed without
   breaking clients or making older audit records read as tampered.
3. A staging or production API with a security setting missing started anyway
   and failed route by route. It now refuses to start and names every gap.
"""
from __future__ import annotations

import base64
import json
import os
import sqlite3
import sys
import types

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:  # same shim as tests/test_framework_auth.py
    import openai  # noqa: F401
except ImportError:  # pragma: no cover
    _openai = types.ModuleType("openai")
    _openai.OpenAI = type("OpenAI", (), {"__init__": lambda self, *a, **k: None})
    sys.modules["openai"] = _openai

import main  # noqa: E402
import nhid_attest  # noqa: E402
import nhid_audit_export  # noqa: E402
from nhid_api_auth import DEFAULT_TENANT, authenticate, hash_api_key  # noqa: E402
from src import preflight  # noqa: E402
from src.audit_anchor import FileAuditAnchor  # noqa: E402
from src.audit_integrity import key_id  # noqa: E402
from src.audit_store import AuditStore  # noqa: E402

KEY_A, KEY_A2, KEY_B = "payer-a-key-1", "payer-a-key-2", "payer-b-key"
A, B = {"X-API-Key": KEY_A}, {"X-API-Key": KEY_B}
OLD_EVENT, NEW_EVENT = b"o" * 32, b"n" * 32
OLD_ANCHOR, NEW_ANCHOR = b"p" * 32, b"q" * 32
ATTEST_BODY = {"delegating_entity": "1234567893", "authorized_actor": "agent-x",
               "scope": ["eligibility"], "expires_at": "2099-01-01T00:00:00+00:00"}

ENV = ("NHID_API_KEY", "NHID_API_KEYS", "DEPLOYMENT_MODE", "TWILIO_AUTH_TOKEN",
       "NHID_PUBLIC_BASE_URL", "NHID_ENABLE_DEBUG_REPLAY", "NHID_ATTEST_ENABLED",
       "NHID_JWT_SECRET", "AUDIT_STORE_PATH", "AUDIT_SECRET_KEY_B64",
       "AUDIT_SECRET_KEYS_RETIRED_B64", "AUDIT_ANCHOR_PATH", "AUDIT_ANCHOR_KEY_B64",
       "AUDIT_ANCHOR_KEYS_RETIRED_B64")


def b64(key: bytes) -> str:
    return base64.b64encode(key).decode()


def tenants(monkeypatch, table):
    monkeypatch.setenv("NHID_API_KEYS", json.dumps(table))


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    for var in ENV:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(nhid_attest, "DB_PATH", str(tmp_path / "attest.db"))
    monkeypatch.setenv("AUDIT_STORE_PATH", str(tmp_path / "audit.db"))
    nhid_audit_export.reset_stores()
    yield
    nhid_audit_export.reset_stores()


@pytest.fixture
def client(monkeypatch):
    tenants(monkeypatch, {"payer-a": hash_api_key(KEY_A), "payer-b": hash_api_key(KEY_B)})
    monkeypatch.setenv("NHID_ATTEST_ENABLED", "1")
    monkeypatch.setenv("NHID_JWT_SECRET", "s" * nhid_attest.MIN_SECRET_LENGTH)
    with TestClient(main.app) as c:
        yield c


# ── 1. Attestations and screening are per tenant ─────────────────────────────

def _mint(client, headers=A):
    r = client.post("/v1/attest", json=ATTEST_BODY, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["reference_id"]


def _screen(client, ref, headers):
    return client.post("/v1/payer/screen", headers=headers, json={
        "caller_npi": ATTEST_BODY["delegating_entity"], "reference_id": ref,
        "requested_scope": "eligibility"}).json()


def test_the_minting_tenant_sees_and_screens_its_own_attestation(client):
    ref = _mint(client)
    assert client.get(f"/v1/attest/verify/{ref}", headers=A).json()["valid"] is True
    assert _screen(client, ref, A)["recommended_action"] == "accept"


def test_another_tenant_cannot_verify_or_screen_it(client):
    ref = _mint(client)
    assert client.get(f"/v1/attest/verify/{ref}", headers=B).status_code == 404
    screened = _screen(client, ref, B)
    assert screened["recommended_action"] == "reject"
    assert screened["reason"] == "No attestation found for this reference ID"


def test_a_foreign_reference_reads_exactly_like_a_missing_one(client):
    ref = _mint(client)
    foreign = client.get(f"/v1/attest/verify/{ref}", headers=B)
    missing = client.get("/v1/attest/verify/no-such-reference", headers=B)
    assert (foreign.status_code, foreign.json()) == (missing.status_code, missing.json())


def test_rows_from_before_tenant_scoping_belong_to_the_legacy_tenant(monkeypatch):
    conn = sqlite3.connect(nhid_attest.DB_PATH)
    conn.execute("""CREATE TABLE attestations (reference_id TEXT PRIMARY KEY,
        delegating_entity TEXT NOT NULL, authorized_actor TEXT NOT NULL, scope TEXT NOT NULL,
        expires_at TEXT NOT NULL, issued_at TEXT NOT NULL, revoked INTEGER NOT NULL DEFAULT 0)""")
    conn.execute("INSERT INTO attestations VALUES ('old-ref','1234567893','agent-x',"
                 "'eligibility','2099-01-01T00:00:00+00:00','2026-01-01T00:00:00+00:00',0)")
    conn.commit()
    conn.close()
    assert nhid_attest.find_attestation("old-ref", DEFAULT_TENANT) is not None
    assert nhid_attest.find_attestation("old-ref", "payer-a") is None
    monkeypatch.setenv("NHID_API_KEY", KEY_A)  # the legacy single key is tenant "default"
    with TestClient(main.app) as c:
        assert c.get("/v1/attest/verify/old-ref", headers=A).json()["valid"] is True


# ── 2a. API key rotation ─────────────────────────────────────────────────────

def test_a_tenant_can_hold_its_old_and_new_keys_during_rotation(monkeypatch):
    tenants(monkeypatch, {"payer-a": [hash_api_key(KEY_A2), hash_api_key(KEY_A)]})
    assert authenticate(KEY_A) == authenticate(KEY_A2) == "payer-a"


def test_removing_the_old_hash_revokes_the_old_key(monkeypatch):
    tenants(monkeypatch, {"payer-a": [hash_api_key(KEY_A2)]})
    with TestClient(main.app) as c:
        assert c.get("/v1/compliance/states", headers={"X-API-Key": KEY_A2}).status_code == 200
        assert c.get("/v1/compliance/states", headers=A).status_code == 403


@pytest.mark.parametrize("table", [
    {"payer-a": []},
    {"payer-a": [hash_api_key(f"k{i}") for i in range(5)]},
    {"payer-a": hash_api_key(KEY_A), "payer-b": [hash_api_key(KEY_A)]},
    {"payer-a": [hash_api_key(KEY_A), "plaintext"]},
])
def test_a_bad_rotation_table_fails_closed(monkeypatch, table):
    tenants(monkeypatch, table)
    with TestClient(main.app) as c:
        assert c.get("/v1/compliance/states", headers=A).status_code == 503


# ── 2b. Audit key rotation ───────────────────────────────────────────────────

def _write(store, n, previous, session="sess-rot"):
    ts, payload = f"2026-08-01T10:00:{n:02d}Z", {"step": n}
    assert store.write_event(
        event_id=f"evt-{n}", session_id=session, event_type="POLICY_DECISION", timestamp=ts,
        agent_id="agent", organization_id="org", payload=payload, previous_event_id=previous,
        evidence_hash=store._integrity.sign_event(f"evt-{n}", ts, "POLICY_DECISION",
                                                  payload, previous))


def _rotated(tmp_path, keep_retired=True):
    path, anchor_path = str(tmp_path / "rot.db"), str(tmp_path / "anchor" / "rot.anchor")
    before = AuditStore(db_path=path, secret_key=OLD_EVENT,
                        anchor=FileAuditAnchor(anchor_path, OLD_ANCHOR))
    _write(before, 1, None)
    _write(before, 2, "evt-1")
    after = AuditStore(
        db_path=path, secret_key=NEW_EVENT,
        retired_keys=[OLD_EVENT] if keep_retired else [],
        anchor=FileAuditAnchor(anchor_path, NEW_ANCHOR,
                               [OLD_ANCHOR] if keep_retired else []))
    return after


def test_events_signed_before_a_rotation_still_verify_after_it(tmp_path):
    store = _rotated(tmp_path)
    _write(store, 3, "evt-2")
    assert store.verify_chain("sess-rot") == (True, None)
    ids = [e["key_id"] for e in store.query_events(session_id="sess-rot")]
    assert ids == [key_id(OLD_EVENT), key_id(OLD_EVENT), key_id(NEW_EVENT)]


def test_the_anchor_chain_runs_unbroken_across_a_rotation(tmp_path):
    store = _rotated(tmp_path)
    _write(store, 3, "evt-2")
    with open(store.anchor.path, encoding="utf-8") as fh:
        kids = [json.loads(line)["kid"] for line in fh]
    assert kids == [key_id(OLD_ANCHOR)] * 2 + [key_id(NEW_ANCHOR)]
    assert store.anchor.verify() == (True, None)


def test_without_the_retired_keys_old_records_fail(tmp_path):
    """The control: rotation works because the retired key is kept, not by accident."""
    store = _rotated(tmp_path, keep_retired=False)
    valid, error = store.verify_chain("sess-rot")
    assert not valid and "signature" in error


def test_a_retired_key_never_signs(tmp_path):
    store = _rotated(tmp_path)
    assert store._integrity.key_id == key_id(NEW_EVENT)
    _write(store, 3, "evt-2")
    assert store.anchor.latest("sess-rot")["kid"] == key_id(NEW_ANCHOR)


@pytest.mark.parametrize("current, retired, env", [
    (NEW_EVENT, NEW_EVENT, "AUDIT_SECRET_KEYS_RETIRED_B64"),
    (NEW_ANCHOR, NEW_ANCHOR, "AUDIT_ANCHOR_KEYS_RETIRED_B64"),
])
def test_a_key_cannot_be_current_and_retired(client, monkeypatch, current, retired, env):
    monkeypatch.setenv("AUDIT_SECRET_KEY_B64", b64(NEW_EVENT))
    monkeypatch.setenv("AUDIT_ANCHOR_PATH", str(os.path.dirname(nhid_attest.DB_PATH) + "/a.anchor"))
    monkeypatch.setenv("AUDIT_ANCHOR_KEY_B64", b64(NEW_ANCHOR))
    monkeypatch.setenv(env, b64(retired))
    r = client.post("/v1/audit/log", headers=A,
                    json={"session_id": "s", "agent_id": "a", "event_type": "e"})
    assert r.status_code == 503 and env in r.json()["detail"]


def test_a_retired_event_key_cannot_be_an_anchor_key(client, monkeypatch, tmp_path):
    monkeypatch.setenv("AUDIT_SECRET_KEY_B64", b64(NEW_EVENT))
    monkeypatch.setenv("AUDIT_SECRET_KEYS_RETIRED_B64", b64(OLD_ANCHOR))
    monkeypatch.setenv("AUDIT_ANCHOR_PATH", str(tmp_path / "x.anchor"))
    monkeypatch.setenv("AUDIT_ANCHOR_KEY_B64", b64(OLD_ANCHOR))
    r = client.post("/v1/audit/log", headers=A,
                    json={"session_id": "s", "agent_id": "a", "event_type": "e"})
    assert r.status_code == 503


# ── 3. Startup checks ────────────────────────────────────────────────────────

def _fully_configured(monkeypatch, tmp_path):
    tenants(monkeypatch, {"payer-a": hash_api_key(KEY_A)})
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "twilio-token")
    monkeypatch.setenv("NHID_PUBLIC_BASE_URL", "https://voice.example.org")
    monkeypatch.setenv("AUDIT_SECRET_KEY_B64", b64(NEW_EVENT))
    monkeypatch.setenv("AUDIT_ANCHOR_PATH", str(tmp_path / "anchor" / "prod.anchor"))
    monkeypatch.setenv("AUDIT_ANCHOR_KEY_B64", b64(NEW_ANCHOR))


@pytest.mark.parametrize("mode", ["staging", "production"])
def test_a_strict_mode_with_nothing_set_names_every_problem_and_will_not_start(monkeypatch, mode):
    monkeypatch.delenv("AUDIT_STORE_PATH")
    monkeypatch.setenv("DEPLOYMENT_MODE", mode)
    found = " | ".join(preflight.problems())
    for name in ("NHID_API_KEYS", "TWILIO_AUTH_TOKEN", "AUDIT_STORE_PATH",
                 "AUDIT_SECRET_KEY_B64", "AUDIT_ANCHOR_PATH", "AUDIT_ANCHOR_KEY_B64"):
        assert name in found
    with pytest.raises(RuntimeError, match="refusing to start"):
        with TestClient(main.app):
            pass


def test_a_fully_configured_production_api_starts(monkeypatch, tmp_path):
    _fully_configured(monkeypatch, tmp_path)
    monkeypatch.setenv("DEPLOYMENT_MODE", "production")
    assert preflight.problems() == [] and preflight.warnings() == []
    with TestClient(main.app) as c:
        assert c.get("/health").status_code == 200


@pytest.mark.parametrize("env, value, needle", [
    ("NHID_API_KEYS", "not json", "NHID_API_KEYS is malformed"),
    ("NHID_ATTEST_ENABLED", "1", "NHID_JWT_SECRET"),
    ("AUDIT_SECRET_KEYS_RETIRED_B64", "%%%", "AUDIT_SECRET_KEYS_RETIRED_B64"),
])
def test_each_misconfiguration_is_named(monkeypatch, tmp_path, env, value, needle):
    _fully_configured(monkeypatch, tmp_path)
    monkeypatch.setenv("DEPLOYMENT_MODE", "production")
    monkeypatch.setenv(env, value)
    assert any(needle in p for p in preflight.problems())


def test_production_warnings_do_not_block_startup(monkeypatch, tmp_path):
    _fully_configured(monkeypatch, tmp_path)
    monkeypatch.setenv("DEPLOYMENT_MODE", "production")
    monkeypatch.setenv("NHID_ENABLE_DEBUG_REPLAY", "1")
    monkeypatch.delenv("NHID_PUBLIC_BASE_URL")
    assert len(preflight.warnings()) == 2
    with TestClient(main.app) as c:
        assert c.get("/health").status_code == 200


def test_development_is_never_blocked(monkeypatch):
    assert preflight.problems() == []
    with TestClient(main.app) as c:
        assert c.get("/health").status_code == 200
