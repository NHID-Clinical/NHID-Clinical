"""
NHID-Clinical FHIR R4 AuditEvent Emitter
==========================================
Converts NHID-Clinical CTS run data into HL7 FHIR R4 AuditEvent resources
bundled in a FHIR R4 Bundle (type: collection).

Each call session produces one Bundle containing one AuditEvent per
conformance milestone reached:

  1. nhid-session-start         — call session initialised
  2. nhid-identity-disclosure   — IDG-01 gate evaluated
  3. nhid-auth-verification     — NHID-Auth v2 credential check (when provider NPI present)
  4. nhid-phi-gate              — PDX-01 pre-data-exchange gate decision
  5. nhid-phi-exchange          — PHI exchange begins (gate cleared + PHI accessed)
  6. nhid-escalation            — EIT-01 escalation event (when triggered)
  7. nhid-call-end              — session terminated

Validation:
  Validated against HL7 FHIR R4 base specification (version 4.0.1).
  Does NOT claim conformance to any HL7 Implementation Guide.

NHID-Clinical is a voluntary open proposal. CC BY 4.0.
Not a certified standard. Not a regulatory requirement.
See nhid-clinical.org.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any


# ── FHIR code system URIs ──────────────────────────────────────────────────

_DCM      = "http://dicom.nema.org/resources/ontology/DCM"
_AE_TYPE  = "http://terminology.hl7.org/CodeSystem/audit-entity-type"
_OBJ_ROLE = "http://terminology.hl7.org/CodeSystem/object-role"
_SRC_TYPE = "http://terminology.hl7.org/CodeSystem/security-source-type"

# NHID-Clinical custom code systems (stable URIs, not resolvable in CI)
_NHID_BASE    = "https://nhid-clinical.org/fhir"
_NHID_SUBTYPE = f"{_NHID_BASE}/CodeSystem/audit-event-subtype"
_NHID_ROLE    = f"{_NHID_BASE}/CodeSystem/agent-role"
_NHID_SESSION = f"{_NHID_BASE}/sessions"
_NHID_AGENTS  = f"{_NHID_BASE}/agents"
_NHID_SYSTEMS = f"{_NHID_BASE}/systems"

# DICOM audit event type codes used in this profile
_DCM_APPLICATION_ACTIVITY = ("110100", "Application Activity")
_DCM_SECURITY_ALERT       = ("110113", "Security Alert")
_DCM_USER_AUTHENTICATION  = ("110114", "User Authentication")
_DCM_PATIENT_RECORD       = ("110110", "Patient Record")
_DCM_SOURCE_ROLE_ID       = ("110153", "Source Role ID")
_DCM_DEST_ROLE_ID         = ("110152", "Destination Role ID")


# ── Primitive builders ─────────────────────────────────────────────────────

def _now_instant() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _coding(system: str, code: str, display: str) -> dict[str, str]:
    return {"system": system, "code": code, "display": display}


def _ae_id(session_id: str, milestone: str) -> str:
    """Deterministic, R4-safe AuditEvent id (max 64 chars)."""
    digest = hashlib.sha256(f"{session_id}:{milestone}".encode()).hexdigest()[:16]
    return f"nhid-ae-{digest}"


def _bundle_id(session_id: str) -> str:
    digest = hashlib.sha256(session_id.encode()).hexdigest()[:20]
    return f"nhid-bundle-{digest}"


def _ae_full_url(ae_id: str) -> str:
    """Deterministic urn:uuid fullUrl for a Bundle entry (required by R4 collection bundles)."""
    h = hashlib.sha256(ae_id.encode()).hexdigest()
    return f"urn:uuid:{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


# ── Reusable structural elements ───────────────────────────────────────────

def _source_element() -> dict[str, Any]:
    """AuditEvent.source — the NHID-Clinical policy engine."""
    return {
        "site": "nhid-clinical.org",
        "observer": {
            "identifier": {
                "system": _NHID_SYSTEMS,
                "value": "nhid-policy-engine-v1",
            },
            "display": "NHID-Clinical Policy Engine v1",
        },
        "type": [_coding(_SRC_TYPE, "4", "Application Server")],
    }


def _session_entity(session_id: str, description: str | None = None) -> dict[str, Any]:
    """Entity carrying the call/transaction reference."""
    e: dict[str, Any] = {
        "what": {
            "identifier": {"system": _NHID_SESSION, "value": session_id}
        },
        "type": _coding(_AE_TYPE, "2", "System Object"),
        "role": _coding(_OBJ_ROLE, "20", "Job"),
    }
    if description:
        e["description"] = description
    return e


def _agent_ai(agent_id: str, agent_name: str | None = None) -> dict[str, Any]:
    """Agent slice: the AI voice agent (requestor=true, DCM Source Role)."""
    return {
        "type": {"coding": [_coding(_DCM, *_DCM_SOURCE_ROLE_ID)]},
        "who": {
            "identifier": {"system": _NHID_AGENTS, "value": agent_id},
            "display": agent_name or agent_id,
        },
        "requestor": True,
    }


def _agent_payer(payer_name: str | None = None) -> dict[str, Any]:
    """Agent slice: the payer system (requestor=false, DCM Destination Role)."""
    return {
        "type": {"coding": [_coding(_DCM, *_DCM_DEST_ROLE_ID)]},
        "who": {"display": payer_name or "Payer Organization"},
        "requestor": False,
    }


def _agent_provider(npi: str, name: str | None = None) -> dict[str, Any]:
    """Agent slice: provider organisation on whose behalf the agent calls."""
    return {
        "type": {
            "coding": [
                _coding(_NHID_ROLE, "principal", "Principal Organization (on behalf of)")
            ]
        },
        "who": {
            "identifier": {
                "system": "http://hl7.org/fhir/sid/us-npi",
                "value": npi,
            },
            "display": name or f"Provider NPI {npi}",
        },
        "requestor": False,
    }


# ── Outcome helpers ────────────────────────────────────────────────────────

def _outcome_from_decision(decision: Any) -> tuple[str, str]:
    """
    Map a PolicyDecision to (outcome_code, outcome_desc).

    FHIR R4 outcome codes:
      "0"  = Success
      "4"  = Minor failure
      "8"  = Serious failure (security policy violated)
      "12" = Major failure (not used here)
    """
    if decision is None:
        return "0", "No policy decision recorded"
    action_val = getattr(decision, "action", None)
    if action_val is None:
        return "0", "No policy action"
    action_str = str(getattr(action_val, "value", action_val))
    violations = getattr(decision, "violations", [])
    has_critical = any(
        str(getattr(v, "severity", "")).lower() == "critical" for v in violations
    )
    if action_str == "CONTINUE_AI":
        return "0", "Policy gate cleared — no violations"
    if action_str == "ESCALATE_HUMAN":
        return "0", "Human escalation initiated successfully"
    if action_str == "LOG_ONLY" and not has_critical:
        return "4", "Policy: LOG_ONLY — minor deviation recorded"
    if has_critical:
        return "8", f"Policy action: {action_str} — critical violation detected"
    return "4", f"Policy action: {action_str}"


def _violation_rule_ids(decision: Any) -> set[str]:
    if decision is None:
        return set()
    return {str(getattr(v, "rule_id", "")) for v in getattr(decision, "violations", [])}


# ── Milestone constructors ─────────────────────────────────────────────────

def _make_ae(
    session_id: str,
    milestone: str,
    dcm_type: tuple[str, str],
    action: str,
    outcome: str,
    outcome_desc: str,
    recorded: str,
    agents: list[dict[str, Any]],
    entities: list[dict[str, Any]],
) -> dict[str, Any]:
    milestone_display = milestone.replace("nhid-", "").replace("-", " ").title()
    return {
        "resourceType": "AuditEvent",
        "id": _ae_id(session_id, milestone),
        "type": _coding(_DCM, *dcm_type),
        "subtype": [_coding(_NHID_SUBTYPE, milestone, f"NHID {milestone_display}")],
        "action": action,
        "recorded": recorded,
        "outcome": outcome,
        "outcomeDesc": outcome_desc,
        "agent": agents,
        "source": _source_element(),
        "entity": entities,
    }


def _standard_agents(
    agent_id: str,
    provider_npi: str | None,
    provider_name: str | None,
) -> list[dict[str, Any]]:
    agents: list[dict[str, Any]] = [
        _agent_ai(agent_id),
        _agent_payer(),
    ]
    if provider_npi:
        agents.append(_agent_provider(provider_npi, provider_name))
    return agents


# ── Public API ─────────────────────────────────────────────────────────────

def build_audit_bundle(
    session: dict[str, Any],
    event: dict[str, Any],
    decision: Any = None,
    provider_npi: str | None = None,
    provider_name: str | None = None,
) -> dict[str, Any]:
    """
    Build a FHIR R4 Bundle[type=collection] from one NHID-Clinical trace event.

    Parameters
    ----------
    session:       NHID-Clinical session context (turn_count, escalation_path, …)
    event:         One NHID-Clinical trace event (conforming to nhid_trace_schema_v1)
    decision:      PolicyDecision returned by evaluate_all() — used for outcome coding
    provider_npi:  NPI of the provider organisation on whose behalf the agent calls
    provider_name: Display name for the provider org (optional)

    Returns
    -------
    dict  FHIR R4 Bundle as a Python dict. Serialise with json.dumps(bundle, indent=2).
    """
    session_id = (
        event.get("session_id")
        or session.get("session_id")
        or "unknown-session"
    )
    agent_id  = event.get("actor_id") or session.get("actor_id", "unknown-agent")
    recorded  = event.get("timestamp") or _now_instant()
    gov       = event.get("healthcare_governance") or {}
    disc_ts   = gov.get("disclosure_timestamp")
    assertion = gov.get("identity_assertion_text") or ""
    phi_acc   = gov.get("phi_accessed") or []
    esc_ts    = gov.get("escalation_timestamp")
    esc_out   = gov.get("escalation_outcome")
    # Combine violation IDs from the PolicyDecision AND the raw event boundary_violations
    # (event violations are present when running against pre-computed trace data)
    event_viol_ids = {
        v.get("rule_id", "") for v in (event.get("boundary_violations") or [])
    }
    rule_ids = _violation_rule_ids(decision) | event_viol_ids

    agents = _standard_agents(agent_id, provider_npi, provider_name)
    base_entity = [_session_entity(session_id, "NHID-Clinical call session")]

    entries: list[dict[str, Any]] = []

    # ── 1. Session Start ───────────────────────────────────────────────────
    entries.append(_make_ae(
        session_id, "nhid-session-start",
        _DCM_APPLICATION_ACTIVITY, "E",
        "0", "Call session initialised",
        recorded, agents, base_entity,
    ))

    # ── 2. Identity Disclosure (IDG-01) ────────────────────────────────────
    if disc_ts is not None or "IDG-01" in rule_ids:
        if disc_ts and assertion:
            idg_outcome, idg_desc = "0", "AI identity disclosed and assertion text confirmed"
        elif disc_ts:
            idg_outcome, idg_desc = "4", "Disclosure timestamp set but assertion text absent"
        else:
            idg_outcome, idg_desc = "8", "IDG-01 violation: identity not disclosed before data exchange"
        disc_entities = list(base_entity)
        if assertion:
            disc_entities.append({
                "what": {
                    "identifier": {"system": _NHID_SESSION, "value": session_id}
                },
                "type": _coding(_AE_TYPE, "4", "Other"),
                "description": assertion[:200],
            })
        entries.append(_make_ae(
            session_id, "nhid-identity-disclosure",
            _DCM_SECURITY_ALERT, "E",
            idg_outcome, idg_desc,
            disc_ts or recorded, agents, disc_entities,
        ))

    # ── 3. Authorization Verification (NHID-Auth v2, when provider NPI present) ──
    if provider_npi:
        entries.append(_make_ae(
            session_id, "nhid-auth-verification",
            _DCM_USER_AUTHENTICATION, "E",
            "0", f"Provider NPI authorization reference recorded: {provider_npi}",
            recorded, agents, base_entity,
        ))

    # ── 4. PHI Gate Decision (PDX-01) ──────────────────────────────────────
    if phi_acc or "PDX-01" in rule_ids:
        if disc_ts and phi_acc:
            pdx_outcome = "0"
            pdx_desc = "PDX-01 gate cleared — disclosure confirmed before PHI exchange"
        elif not disc_ts and phi_acc:
            pdx_outcome = "8"
            pdx_desc = "PDX-01 violation: PHI exchange attempted before identity disclosure"
        else:
            pdx_outcome = "8"
            pdx_desc = "PDX-01 violation: PHI gate triggered — disclosure missing"
        entries.append(_make_ae(
            session_id, "nhid-phi-gate",
            _DCM_SECURITY_ALERT, "E",
            pdx_outcome, pdx_desc,
            recorded, agents, base_entity,
        ))

    # ── 5. PHI Exchange Start (only when gate cleared + PHI accessed) ──────
    if phi_acc and disc_ts:
        phi_entity = list(base_entity)
        phi_entity.append({
            "what": {
                "identifier": {"system": _NHID_SESSION, "value": session_id}
            },
            "type": _coding(_AE_TYPE, "1", "Person"),
            "description": f"PHI categories accessed: {', '.join(phi_acc)}",
        })
        entries.append(_make_ae(
            session_id, "nhid-phi-exchange",
            _DCM_PATIENT_RECORD, "R",
            "0", f"PHI exchange begun — categories: {', '.join(phi_acc)}",
            recorded, agents, phi_entity,
        ))

    # ── 6. Escalation (EIT-01, when triggered) ─────────────────────────────
    if esc_ts or "EIT-01" in rule_ids:
        if esc_ts and esc_out == "connected":
            eit_outcome, eit_desc = "0", "Human escalation connected successfully"
        elif esc_ts and esc_out in ("unavailable", "timeout"):
            eit_outcome, eit_desc = "4", f"Escalation attempted but outcome: {esc_out}"
        elif "EIT-01" in rule_ids:
            eit_outcome, eit_desc = "8", "EIT-01 violation: escalation path unavailable"
        else:
            eit_outcome, eit_desc = "4", "Escalation initiated — outcome unknown"
        entries.append(_make_ae(
            session_id, "nhid-escalation",
            _DCM_APPLICATION_ACTIVITY, "E",
            eit_outcome, eit_desc,
            esc_ts or recorded, agents, base_entity,
        ))

    # ── 7. Call End ────────────────────────────────────────────────────────
    end_outcome, end_desc = _outcome_from_decision(decision)
    entries.append(_make_ae(
        session_id, "nhid-call-end",
        _DCM_APPLICATION_ACTIVITY, "E",
        end_outcome, end_desc,
        recorded, agents, base_entity,
    ))

    return {
        "resourceType": "Bundle",
        "id": _bundle_id(session_id),
        "type": "collection",
        "timestamp": recorded,
        "entry": [{"fullUrl": _ae_full_url(e["id"]), "resource": e} for e in entries],
    }


def emit_cts_bundle(
    test_id: str,
    session: dict[str, Any],
    event: dict[str, Any],
    decision: Any,
    output_dir: str | None = None,
    provider_npi: str | None = None,
    provider_name: str | None = None,
) -> dict[str, Any]:
    """
    Emit a FHIR R4 Bundle for a single CTS test execution.

    If output_dir is given, writes the bundle to
    ``{output_dir}/{test_id}-fhir-bundle.json``.
    """
    bundle = build_audit_bundle(session, event, decision, provider_npi, provider_name)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, f"{test_id}-fhir-bundle.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(bundle, fh, indent=2)
    return bundle
