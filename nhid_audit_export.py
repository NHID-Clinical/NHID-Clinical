"""``/v1/audit/log``, ``/v1/audit/export`` and ``/v1/audit/verify``.

These routes used to keep events in a Python list: lost on every restart, not
signed, and readable by any key holder until per-tenant keys arrived (#443).
They now write to the HMAC-chained ``AuditStore`` (SQLite), and, when
configured, to an external anchor (``src/audit_anchor.py``) so a deletion from
the end of a session is caught even if the database's own counter is edited.

Tenant isolation: every session is stored under ``<tenant>/<session_id>``, so
two customers can use the same session id without seeing or extending each
other's chain, and a customer asking for another's session gets 404.

Configuration (read per request, so a corrected environment needs no restart):

* ``AUDIT_STORE_PATH``: the SQLite file. Required in staging/production. In
  development, unset means a temporary file for this process, with a warning.
* ``AUDIT_SECRET_KEY_B64``: base64 32-byte key the events are signed with.
  Required in staging/production; ephemeral (and announced) in development.
* ``AUDIT_ANCHOR_PATH`` and ``AUDIT_ANCHOR_KEY_B64``: the external anchor file
  and its own signing key. Required in staging/production; optional together in
  development. The anchor path must not be the database path, and the anchor
  key should not be the event key.

A missing required setting refuses the audit routes with 503 rather than
writing an audit trail that cannot be verified later.
"""
import base64
import binascii
import csv
import io
import logging
import os
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from nhid_api_auth import tenant_of
from src.audit_anchor import FileAuditAnchor
from src.audit_integrity import AuditIntegrity
from src.audit_store import AuditStore, AuditStoreUnavailable
from src.webhook_security import STRICT_MODES, deployment_mode

logger = logging.getLogger(__name__)

router = APIRouter()

EVENT_TYPE = "API_AUDIT_EVENT"

_stores: Dict[Tuple, AuditStore] = {}
_stores_lock = threading.Lock()
_log_lock = threading.Lock()
_dev_dir: Optional[str] = None


class AuditEvent(BaseModel):
    session_id: str
    agent_id: str
    event_type: str
    transcript_text: Optional[str] = None
    action: Optional[str] = None
    timestamp: Optional[str] = None


def _unavailable(reason: str) -> HTTPException:
    return HTTPException(status_code=503, detail=f"Audit storage is not configured: {reason}")


def _key(env: str) -> Optional[bytes]:
    raw = (os.getenv(env) or "").strip()
    if not raw:
        return None
    try:
        key = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError):
        raise _unavailable(f"{env} is not valid base64")
    if len(key) != 32:
        raise _unavailable(f"{env} must decode to 32 bytes")
    return key


def _dev_path() -> str:
    global _dev_dir
    if _dev_dir is None:
        _dev_dir = tempfile.mkdtemp(prefix="nhid-audit-")
        logger.warning(
            "AUDIT_STORE_PATH is unset: audit events go to a temporary file in %s "
            "and are lost when this machine cleans it. Set AUDIT_STORE_PATH for "
            "any trail that must be kept.", _dev_dir)
    return os.path.join(_dev_dir, "audit_events.db")


def get_store() -> AuditStore:
    """The audit store for the current environment, built once per configuration."""
    strict = deployment_mode() in STRICT_MODES
    path = (os.getenv("AUDIT_STORE_PATH") or "").strip()
    secret = _key("AUDIT_SECRET_KEY_B64")
    anchor_path = (os.getenv("AUDIT_ANCHOR_PATH") or "").strip()
    anchor_key = _key("AUDIT_ANCHOR_KEY_B64")

    if strict:
        missing = [name for name, value in (
            ("AUDIT_STORE_PATH", path), ("AUDIT_SECRET_KEY_B64", secret),
            ("AUDIT_ANCHOR_PATH", anchor_path), ("AUDIT_ANCHOR_KEY_B64", anchor_key),
        ) if not value]
        if missing:
            raise _unavailable(", ".join(missing) + " unset")
    if bool(anchor_path) != bool(anchor_key):
        raise _unavailable("AUDIT_ANCHOR_PATH and AUDIT_ANCHOR_KEY_B64 must be set together")
    if anchor_key is not None and anchor_key == secret:
        raise _unavailable("AUDIT_ANCHOR_KEY_B64 must differ from AUDIT_SECRET_KEY_B64")

    path = path or _dev_path()
    if anchor_path and os.path.abspath(anchor_path) == os.path.abspath(path):
        raise _unavailable("AUDIT_ANCHOR_PATH must not be the audit database")

    config = (path, secret, anchor_path, anchor_key)
    with _stores_lock:
        store = _stores.get(config)
        if store is None:
            anchor = FileAuditAnchor(anchor_path, anchor_key) if anchor_path else None
            store = AuditStore(db_path=path, secret_key=secret, anchor=anchor)
            _stores[config] = store
        return store


def reset_stores() -> None:
    """Forget cached stores (tests, or after rotating configuration)."""
    with _stores_lock:
        _stores.clear()


def _scoped(tenant: str, session_id: str) -> str:
    # Tenant ids cannot contain "/" (nhid_api_auth._TENANT_ID), so this cannot
    # collide across tenants.
    return f"{tenant}/{session_id}"


def _events_for(request: Request, session_id: str) -> Tuple[AuditStore, str, list]:
    store = get_store()
    scoped = _scoped(tenant_of(request), session_id)
    try:
        events = store.query_events(session_id=scoped, limit=10000)
    except AuditStoreUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    if not events:
        raise HTTPException(status_code=404, detail="No audit events found for session")
    return store, scoped, events


@router.post("/v1/audit/log")
def log_audit_event(event: AuditEvent, request: Request):
    tenant = tenant_of(request)
    store = get_store()
    entry = event.model_dump()
    entry["tenant_id"] = tenant
    entry["timestamp"] = datetime.now(timezone.utc).isoformat()
    scoped = _scoped(tenant, event.session_id)

    with _log_lock:
        try:
            prior = store.query_events(session_id=scoped, limit=10000)
        except AuditStoreUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc))
        previous = prior[-1]["event_id"] if prior else None
        event_id = str(uuid.uuid4())
        evidence = AuditIntegrity(store.secret_key).sign_event(
            event_id, entry["timestamp"], EVENT_TYPE, entry, previous)
        landed = store.write_event(
            event_id=event_id, session_id=scoped, event_type=EVENT_TYPE,
            timestamp=entry["timestamp"], agent_id=event.agent_id,
            organization_id=tenant, payload=entry,
            previous_event_id=previous, evidence_hash=evidence,
        )
    if not landed:
        raise HTTPException(status_code=503, detail="Audit event was not recorded durably")
    return {"logged": True, "timestamp": entry["timestamp"], "event_id": event_id}


@router.get("/v1/audit/verify/{session_id}")
def verify_audit_session(session_id: str, request: Request):
    store, scoped, events = _events_for(request, session_id)
    valid, error = store.verify_chain(scoped)
    return {
        "session_id": session_id,
        "events": len(events),
        "valid": valid,
        "error": error,
        "anchored": store.anchor is not None,
    }


@router.get("/v1/audit/export/{session_id}")
def export_audit_fhir(session_id: str, request: Request, format: str = "fhir"):
    _, _, stored = _events_for(request, session_id)
    events = [e["payload"] for e in stored]

    if format == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=events[0].keys())
        writer.writeheader()
        writer.writerows(events)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=audit_{session_id}.csv"}
        )

    # FHIR AuditEvent bundle
    fhir_bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {
                "resource": {
                    "resourceType": "AuditEvent",
                    "id": f"nhid-{e['session_id']}-{i}",
                    "action": "E",
                    "recorded": e["timestamp"],
                    "agent": [{"who": {"display": e["agent_id"]}, "requestor": True}],
                    "entity": [{"detail": [
                        {"type": k, "valueString": str(v)}
                        for k, v in e.items()
                    ]}]
                }
            }
            for i, e in enumerate(events)
        ]
    }
    return JSONResponse(content=fhir_bundle)
