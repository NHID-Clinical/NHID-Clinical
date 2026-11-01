"""
The external audit anchor and persistent, tenant-scoped audit storage.

Before: ``verify_chain`` caught a deletion from the end of a session only by
comparing against a counter in the same SQLite file, so deleting the last event
and lowering the counter (two edits, one file) verified clean. That limit is
still asserted, for a store with no anchor, in
``tests/test_audit_store.py::test_the_anchor_shares_a_file_with_what_it_describes``.

With ``FileAuditAnchor`` the witness is a separate, signed, hash-chained file.
These tests show the same attacks failing against it, the attacks on the anchor
file itself being caught, and what is still out of reach (stated, not hidden).

Separately, ``/v1/audit/*`` kept events in a Python list; they now persist in
the signed store, scoped per tenant.
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

from src.audit_anchor import ERR_AUDIT_ANCHOR_INVALID, KIND_PRUNE, FileAuditAnchor  # noqa: E402
from src.audit_store import (  # noqa: E402
    ERR_AUDIT_ANCHOR_MISMATCH,
    ERR_AUDIT_EVENTS_MISSING,
    ERR_AUDIT_UNANCHORED_EVENTS,
    AuditStore,
)

EVENT_KEY = b"e" * 32
ANCHOR_KEY = b"a" * 32
SESSION = "sess-anchor"


def _sign(store, event_id, timestamp, payload, previous):
    return store._integrity.sign_event(
        event_id=event_id, timestamp=timestamp, event_type="POLICY_DECISION",
        payload=payload, previous_event_id=previous)


def _write(store, n, previous, session_id=SESSION, retention_days=90):
    timestamp = f"2026-08-01T10:00:{n:02d}Z"
    payload = {"step": n}
    assert store.write_event(
        event_id=f"evt-{n}", session_id=session_id, event_type="POLICY_DECISION",
        timestamp=timestamp, agent_id="agent-demo", organization_id="org-demo",
        payload=payload, previous_event_id=previous,
        evidence_hash=_sign(store, f"evt-{n}", timestamp, payload, previous),
        retention_days=retention_days,
    )


def _anchored(tmp_path, count=3):
    anchor = FileAuditAnchor(str(tmp_path / "anchor" / "audit.anchor"), ANCHOR_KEY)
    store = AuditStore(db_path=str(tmp_path / "audit.db"), secret_key=EVENT_KEY, anchor=anchor)
    previous = None
    for n in range(1, count + 1):
        _write(store, n, previous)
        previous = f"evt-{n}"
    return store, anchor


def _sql(store, *statements):
    conn = sqlite3.connect(store.db_path)
    for stmt, params in statements:
        conn.execute(stmt, params)
    conn.commit()
    conn.close()


# ── The store against the anchor ─────────────────────────────────────────────

def test_an_untouched_anchored_trail_verifies(tmp_path):
    store, anchor = _anchored(tmp_path)
    assert store.verify_chain(SESSION) == (True, None)
    assert anchor.latest(SESSION)["event_count"] == 3
    assert anchor.head()["seq"] == 3


def test_deleting_the_tail_and_lowering_the_counter_is_now_caught(tmp_path):
    """The two coordinated edits that defeat the in-file counter."""
    store, _ = _anchored(tmp_path)
    _sql(store,
         ("DELETE FROM audit_events WHERE event_id = 'evt-3'", ()),
         ("UPDATE audit_sessions SET event_count = 2 WHERE session_id = ?", (SESSION,)))
    valid, error = store.verify_chain(SESSION)
    assert not valid and error.startswith(ERR_AUDIT_EVENTS_MISSING)


def test_a_correctly_signed_row_the_anchor_never_saw_is_caught(tmp_path):
    """An attacker holding the event key can forge a valid next link. The
    anchor, signed with a different key, never recorded it."""
    store, _ = _anchored(tmp_path)
    ts, payload = "2026-08-01T10:00:04Z", {"step": 4}
    _sql(store,
         ("INSERT INTO audit_events (event_id, session_id, event_type, timestamp, agent_id, "
          "organization_id, payload, previous_event_id, evidence_hash) VALUES (?,?,?,?,?,?,?,?,?)",
          ("evt-4", SESSION, "POLICY_DECISION", ts, "agent-demo", "org-demo",
           json.dumps(payload), "evt-3", _sign(store, "evt-4", ts, payload, "evt-3"))),
         ("UPDATE audit_sessions SET event_count = 4 WHERE session_id = ?", (SESSION,)))
    valid, error = store.verify_chain(SESSION)
    assert not valid and error.startswith(ERR_AUDIT_UNANCHORED_EVENTS)


def test_rewriting_the_latest_event_with_a_valid_signature_is_caught(tmp_path):
    store, _ = _anchored(tmp_path)
    ts, payload = "2026-08-01T10:00:03Z", {"step": "rewritten"}
    _sql(store, ("UPDATE audit_events SET payload = ?, evidence_hash = ? WHERE event_id = 'evt-3'",
                 (json.dumps(payload), _sign(store, "evt-3", ts, payload, "evt-2"))))
    valid, error = store.verify_chain(SESSION)
    assert not valid and error.startswith(ERR_AUDIT_ANCHOR_MISMATCH)


def test_without_an_anchor_the_old_boundary_still_holds(tmp_path):
    """The control: the same edits pass on an unanchored store, as documented."""
    store = AuditStore(db_path=str(tmp_path / "plain.db"), secret_key=EVENT_KEY)
    _write(store, 1, None)
    _write(store, 2, "evt-1")
    _sql(store,
         ("DELETE FROM audit_events WHERE event_id = 'evt-2'", ()),
         ("UPDATE audit_sessions SET event_count = 1 WHERE session_id = ?", (SESSION,)))
    assert store.verify_chain(SESSION) == (True, None)


# ── Attacks on the anchor file ───────────────────────────────────────────────

def _lines(anchor):
    with open(anchor.path, encoding="utf-8") as fh:
        return fh.read().splitlines()


def _rewrite(anchor, lines):
    with open(anchor.path, "w", encoding="utf-8") as fh:
        fh.write("".join(line + "\n" for line in lines))


def test_editing_a_checkpoint_invalidates_the_anchor(tmp_path):
    store, anchor = _anchored(tmp_path)
    lines = _lines(anchor)
    rec = json.loads(lines[-1])
    rec["event_count"] = 2
    lines[-1] = json.dumps(rec, sort_keys=True, separators=(",", ":"))
    _rewrite(anchor, lines)
    valid, error = store.verify_chain(SESSION)
    assert not valid and error.startswith(ERR_AUDIT_ANCHOR_INVALID)


def test_removing_a_checkpoint_from_the_middle_invalidates_the_anchor(tmp_path):
    _, anchor = _anchored(tmp_path)
    lines = _lines(anchor)
    _rewrite(anchor, lines[:1] + lines[2:])
    assert anchor.verify()[0] is False


def test_a_checkpoint_signed_with_another_key_is_rejected(tmp_path):
    _, anchor = _anchored(tmp_path)
    impostor = FileAuditAnchor(anchor.path, b"x" * 32)
    ok, error = impostor.verify()
    assert not ok and "signature" in error


def test_cutting_the_anchor_tail_is_caught_while_the_events_remain(tmp_path):
    store, anchor = _anchored(tmp_path)
    _rewrite(anchor, _lines(anchor)[:-1])
    valid, error = store.verify_chain(SESSION)
    assert not valid and error.startswith(ERR_AUDIT_UNANCHORED_EVENTS)


def test_cutting_both_tails_consistently_is_the_stated_limit(tmp_path):
    """Truncating the anchor and the database together is not detected here.
    Append-only storage for the anchor, and witnessing ``head()`` elsewhere,
    is what closes it; both are deployment work. Asserted so it stays said."""
    store, anchor = _anchored(tmp_path)
    witnessed = anchor.head()
    _rewrite(anchor, _lines(anchor)[:-1])
    _sql(store,
         ("DELETE FROM audit_events WHERE event_id = 'evt-3'", ()),
         ("UPDATE audit_sessions SET event_count = 2 WHERE session_id = ?", (SESSION,)))
    assert store.verify_chain(SESSION) == (True, None)
    # ...but a head copied out earlier no longer matches.
    assert anchor.head() != witnessed


# ── Operational paths ────────────────────────────────────────────────────────

def test_retention_pruning_is_not_reported_as_tampering(tmp_path):
    store, anchor = _anchored(tmp_path, count=2)
    _sql(store, ("UPDATE audit_events SET expires_at = datetime('now', '-1 day') "
                 "WHERE event_id = 'evt-1'", ()))
    assert store.cleanup_expired() == 1
    assert store.verify_chain(SESSION) == (True, None)
    latest = anchor.latest(SESSION)
    assert latest["kind"] == KIND_PRUNE and latest["event_count"] == 1


def test_pruning_no_longer_breaks_an_unanchored_store_either(tmp_path):
    store = AuditStore(db_path=str(tmp_path / "plain.db"), secret_key=EVENT_KEY)
    _write(store, 1, None)
    _write(store, 2, "evt-1")
    _sql(store, ("UPDATE audit_events SET expires_at = datetime('now', '-1 day') "
                 "WHERE event_id = 'evt-1'", ()))
    store.cleanup_expired()
    assert store.verify_chain(SESSION) == (True, None)


def test_a_failed_checkpoint_reports_the_write_and_flags_the_session(tmp_path, monkeypatch):
    store, anchor = _anchored(tmp_path, count=1)

    def broken(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(anchor, "record", broken)
    ts, payload = "2026-08-01T10:00:02Z", {"step": 2}
    assert store.write_event(
        event_id="evt-2", session_id=SESSION, event_type="POLICY_DECISION", timestamp=ts,
        agent_id="agent-demo", organization_id="org-demo", payload=payload,
        previous_event_id="evt-1", evidence_hash=_sign(store, "evt-2", ts, payload, "evt-1"),
    ) is False
    monkeypatch.undo()
    valid, error = store.verify_chain(SESSION)
    assert not valid and error.startswith(ERR_AUDIT_UNANCHORED_EVENTS)


def test_the_anchor_cannot_be_the_database(tmp_path):
    path = str(tmp_path / "same.db")
    with pytest.raises(ValueError):
        AuditStore(db_path=path, secret_key=EVENT_KEY, anchor=FileAuditAnchor(path, ANCHOR_KEY))


# ── The API: persistent and tenant-scoped ────────────────────────────────────

try:  # same shim as tests/test_framework_auth.py
    import openai  # noqa: F401
except ImportError:  # pragma: no cover
    _openai = types.ModuleType("openai")
    _openai.OpenAI = type("OpenAI", (), {"__init__": lambda self, *a, **k: None})
    sys.modules["openai"] = _openai

import main  # noqa: E402
import nhid_audit_export  # noqa: E402
from nhid_api_auth import hash_api_key  # noqa: E402

KEY_A, KEY_B = "key-for-payer-a", "key-for-payer-b"
A, B = {"X-API-Key": KEY_A}, {"X-API-Key": KEY_B}


@pytest.fixture
def api(monkeypatch, tmp_path):
    for var in ("NHID_API_KEY", "DEPLOYMENT_MODE", "AUDIT_ANCHOR_PATH", "AUDIT_ANCHOR_KEY_B64"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("NHID_API_KEYS",
                       json.dumps({"payer-a": hash_api_key(KEY_A), "payer-b": hash_api_key(KEY_B)}))
    monkeypatch.setenv("AUDIT_STORE_PATH", str(tmp_path / "api-audit.db"))
    monkeypatch.setenv("AUDIT_SECRET_KEY_B64", base64.b64encode(EVENT_KEY).decode())
    monkeypatch.setenv("AUDIT_ANCHOR_PATH", str(tmp_path / "elsewhere" / "api.anchor"))
    monkeypatch.setenv("AUDIT_ANCHOR_KEY_B64", base64.b64encode(ANCHOR_KEY).decode())
    nhid_audit_export.reset_stores()
    with TestClient(main.app) as client:
        yield client
    nhid_audit_export.reset_stores()


def _log(client, headers, session="sess-1", n=1):
    for i in range(n):
        r = client.post("/v1/audit/log", headers=headers, json={
            "session_id": session, "agent_id": "agent-x", "event_type": "disclosure",
            "action": f"step-{i}"})
        assert r.status_code == 200, r.text


def test_logged_events_survive_a_restart(api):
    _log(api, A, n=2)
    nhid_audit_export.reset_stores()  # a new process sees only what is on disk
    bundle = api.get("/v1/audit/export/sess-1", headers=A).json()
    assert [e["resource"]["resourceType"] for e in bundle["entry"]] == ["AuditEvent"] * 2


def test_two_tenants_can_share_a_session_id_without_sharing_a_trail(api):
    _log(api, A, n=2)
    _log(api, B, n=1)
    assert len(api.get("/v1/audit/export/sess-1", headers=A).json()["entry"]) == 2
    assert len(api.get("/v1/audit/export/sess-1", headers=B).json()["entry"]) == 1
    for headers in (A, B):
        result = api.get("/v1/audit/verify/sess-1", headers=headers).json()
        assert result["valid"] is True and result["anchored"] is True


def test_another_tenants_session_is_not_found(api):
    _log(api, A, session="only-a")
    assert api.get("/v1/audit/export/only-a", headers=B).status_code == 404
    assert api.get("/v1/audit/verify/only-a", headers=B).status_code == 404


def test_verify_reports_a_tail_deletion_through_the_api(api, tmp_path):
    _log(api, A, n=3)
    conn = sqlite3.connect(str(tmp_path / "api-audit.db"))
    last = conn.execute("SELECT event_id FROM audit_events WHERE session_id = 'payer-a/sess-1' "
                        "ORDER BY id DESC LIMIT 1").fetchone()[0]
    conn.execute("DELETE FROM audit_events WHERE event_id = ?", (last,))
    conn.execute("UPDATE audit_sessions SET event_count = 2 WHERE session_id = 'payer-a/sess-1'")
    conn.commit()
    conn.close()
    result = api.get("/v1/audit/verify/sess-1", headers=A).json()
    assert result["valid"] is False and result["error"].startswith(ERR_AUDIT_EVENTS_MISSING)


@pytest.mark.parametrize("unset", ["AUDIT_STORE_PATH", "AUDIT_SECRET_KEY_B64",
                                   "AUDIT_ANCHOR_PATH", "AUDIT_ANCHOR_KEY_B64"])
def test_strict_modes_refuse_audit_writes_without_full_configuration(api, monkeypatch, unset):
    monkeypatch.setenv("DEPLOYMENT_MODE", "production")
    monkeypatch.delenv(unset)
    r = api.post("/v1/audit/log", headers=A, json={
        "session_id": "s", "agent_id": "a", "event_type": "disclosure"})
    assert r.status_code == 503 and unset in r.json()["detail"]


def test_the_anchor_key_must_differ_from_the_event_key(api, monkeypatch):
    monkeypatch.setenv("AUDIT_ANCHOR_KEY_B64", base64.b64encode(EVENT_KEY).decode())
    r = api.post("/v1/audit/log", headers=A, json={
        "session_id": "s", "agent_id": "a", "event_type": "disclosure"})
    assert r.status_code == 503
