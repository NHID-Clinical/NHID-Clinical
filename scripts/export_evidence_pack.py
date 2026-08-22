#!/usr/bin/env python3
"""
NHID-Clinical — Evidence Pack Export
====================================
Assembles a reproducible evidence bundle from data a deployment actually
produced, in a form a healthcare organization's security reviewer can verify
without trusting the party that generated it.

The bundle is an assembly job, not a new capability. Every artifact is produced
by a component that already exists:

  conformance results     src/cts_runner.py          run_cts()
  audit chain integrity   src/audit_store.py         AuditStore.verify_chain()
  FHIR R4 AuditEvent      src/fhir_audit_emitter.py  build_audit_bundle()
  policy decisions        src/nhid_policy_engine_v1  evaluate_all()
  control questionnaire   docs/vendor-trust-questionnaire.md

What this deliberately does NOT do
----------------------------------
It does not attest, certify, verify a vendor, or assert compliance with any
regulation or framework. It reports what a specific run produced and states
how to reproduce it. A reviewer's trust should come from re-running the
commands the manifest names, not from this file's say-so.

Any artifact that cannot be generated from the data present is recorded with
status "unavailable" and the reason why. Nothing is stubbed, defaulted, or
inferred — an absent artifact is reported as absent.

Usage
-----
    python scripts/export_evidence_pack.py --out evidence_pack/
    python scripts/export_evidence_pack.py --out evidence_pack/ \\
        --audit-db path/to/nhid_audit.db --session-id CA123
    python scripts/export_evidence_pack.py --out evidence_pack/ --no-conformance
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

EXPORT_FORMAT_VERSION = "1.0.0"

# Reproduction commands recorded in the manifest so a reviewer can re-derive
# each artifact independently. Kept as data, not prose, so they stay accurate.
REPRODUCTION_COMMANDS = {
    "conformance": "python -c \"from src.cts_runner import run_cts; print(run_cts())\"",
    "unit_tests": "python -m pytest tests/ -q",
    "corpus_baseline": "python scripts/check_baseline.py",
    "evidence_pack": "python scripts/export_evidence_pack.py --out evidence_pack/",
}


class Artifact(dict):
    """One evidence artifact: either present with content, or absent with a reason."""

    @classmethod
    def available(cls, name: str, content: Any, **meta: Any) -> "Artifact":
        return cls(name=name, status="available", content=content, **meta)

    @classmethod
    def unavailable(cls, name: str, reason: str) -> "Artifact":
        """An artifact that could not be produced. Never fabricate a substitute."""
        return cls(name=name, status="unavailable", reason=reason, content=None)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _git_revision() -> str | None:
    """The commit the evidence was generated from, when the tree is a git repo."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10, check=False,
        )
        return out.stdout.strip() or None
    except Exception:
        return None


def _git_is_dirty() -> bool | None:
    """True when uncommitted changes exist — a reviewer needs to know."""
    try:
        out = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=10, check=False,
        )
        return bool(out.stdout.strip())
    except Exception:
        return None


# ── Artifact collectors ───────────────────────────────────────────────────

def _executed_suite_path() -> str:
    """The suite file run_cts() actually reads, reported rather than assumed."""
    try:
        from src.cts_runner import _YAML_PATH

        return str(Path(_YAML_PATH).relative_to(Path(__file__).resolve().parent.parent))
    except Exception:
        return "unknown"


def collect_conformance() -> Artifact:
    """Run the conformance test suite and record the per-case outcome."""
    try:
        from src.cts_runner import run_cts
    except Exception as exc:
        return Artifact.unavailable("conformance_results", f"cts_runner unavailable: {exc}")

    try:
        results = run_cts()
    except Exception as exc:
        return Artifact.unavailable("conformance_results", f"conformance run failed: {exc}")

    return Artifact.available(
        "conformance_results",
        results,
        suite=_executed_suite_path(),
        suite_note=(
            "The repository carries two copies of the suite: the published "
            "conformance/ copy and the tests/ copy the runner executes. They "
            "are held semantically identical by a regression test. The path "
            "above is the one this run actually read."
        ),
        reproduce=REPRODUCTION_COMMANDS["conformance"],
    )


def _resolve_audit_db(audit_db: str | None) -> tuple[str | None, str | None]:
    """Decide once, before any collector runs, whether the audit store exists.

    `AuditStore.__init__` creates its database file, so a collector that opens
    the store changes what a later collector observes. Resolving existence up
    front and passing the answer down removes that ordering dependency
    entirely, rather than guarding each collector individually.

    Returns (usable_path, unavailable_reason); exactly one is non-None.
    """
    if not audit_db:
        return None, (
            "no --audit-db supplied; session evidence is read from the audit "
            "store that recorded the call, never reconstructed"
        )
    if not Path(audit_db).exists():
        return None, f"audit store not found at '{audit_db}'"
    return audit_db, None


def collect_audit_chain(
    audit_db: str | None,
    session_id: str | None,
    db_reason: str | None = None,
    secret_key: bytes | None = None,
) -> Artifact:
    """Verify the hash chain over the audit events for one session.

    Requires the HMAC key the events were signed with. `AuditStore` generates a
    random key when none is given, so verifying with the wrong key returns the
    same "signature verification failed" as genuine tampering. Reporting that
    as `chain_valid: False` would tell a reviewer the record had been altered
    when it may be perfectly intact — so an absent key makes this artifact
    unavailable rather than failed. The two are not the same finding.
    """
    if db_reason:
        return Artifact.unavailable("audit_chain_verification", db_reason)
    if not audit_db:
        return Artifact.unavailable(
            "audit_chain_verification",
            "no --audit-db supplied; chain integrity cannot be verified without "
            "the audit store that recorded the session",
        )
    if not session_id:
        return Artifact.unavailable(
            "audit_chain_verification",
            "no --session-id supplied; chain verification is per-session",
        )
    if not secret_key:
        return Artifact.unavailable(
            "audit_chain_verification",
            "no audit signing key supplied (--audit-secret-key or "
            "NHID_AUDIT_SECRET_KEY). Chain signatures are HMACs over the key "
            "the writer used; without it, a valid chain and a tampered one are "
            "indistinguishable, so no verification result is reported.",
        )

    try:
        from src.audit_store import AuditStore

        store = AuditStore(db_path=audit_db, secret_key=secret_key)
        is_valid, error = store.verify_chain(session_id)
        events = store.query_events(session_id=session_id)
    except Exception as exc:
        return Artifact.unavailable(
            "audit_chain_verification", f"audit store read failed: {exc}"
        )

    if not events:
        return Artifact.unavailable(
            "audit_chain_verification",
            f"no audit events recorded for session '{session_id}'",
        )

    return Artifact.available(
        "audit_chain_verification",
        {
            "session_id": session_id,
            "chain_valid": bool(is_valid),
            "error": error,
            "event_count": len(events),
        },
        source=audit_db,
    )


def collect_session_evidence(
    audit_db: str | None, session_id: str | None, db_reason: str | None = None
) -> Artifact:
    """The policy decisions recorded for the session, in order."""
    if db_reason:
        return Artifact.unavailable("policy_decisions", db_reason)
    if not audit_db or not session_id:
        return Artifact.unavailable(
            "policy_decisions",
            "requires both --audit-db and --session-id; decisions are read from "
            "the audit store, never reconstructed",
        )

    try:
        from src.audit_store import AuditStore

        events = AuditStore(db_path=audit_db).query_events(session_id=session_id)
    except Exception as exc:
        return Artifact.unavailable("policy_decisions", f"audit store read failed: {exc}")

    if not events:
        return Artifact.unavailable(
            "policy_decisions", f"no events recorded for session '{session_id}'"
        )

    return Artifact.available("policy_decisions", events, session_id=session_id)


def collect_fhir_bundle(
    audit_db: str | None, session_id: str | None, db_reason: str | None = None
) -> Artifact:
    """FHIR R4 AuditEvent bundle, when there is a real session to emit one for."""
    if db_reason:
        return Artifact.unavailable("fhir_audit_bundle", db_reason)
    if not audit_db or not session_id:
        return Artifact.unavailable(
            "fhir_audit_bundle",
            "requires both --audit-db and --session-id; a FHIR bundle is emitted "
            "from recorded session data, not generated speculatively",
        )
    try:
        from src.audit_store import AuditStore

        events = AuditStore(db_path=audit_db).query_events(session_id=session_id)
    except Exception as exc:
        return Artifact.unavailable("fhir_audit_bundle", f"audit store read failed: {exc}")

    if not events:
        return Artifact.unavailable(
            "fhir_audit_bundle", f"no events recorded for session '{session_id}'"
        )

    try:
        from src.fhir_audit_emitter import build_audit_bundle

        bundle = build_audit_bundle(
            session={"turn_count": len(events)},
            event=events[0].get("payload", {}) if isinstance(events[0], dict) else {},
        )
    except Exception as exc:
        return Artifact.unavailable("fhir_audit_bundle", f"FHIR emission failed: {exc}")

    return Artifact.available(
        "fhir_audit_bundle",
        bundle,
        specification="HL7 FHIR R4 base specification 4.0.1",
        note=(
            "Conforms to the R4 base specification. No named Implementation "
            "Guide conformance is claimed."
        ),
    )


def collect_delegation_result(session_id: str | None) -> Artifact:
    """DLG-01 verification outcome for the session, if one was recorded.

    Delegation is opt-in, so its absence is the expected case and is reported
    plainly rather than as a failure.
    """
    return Artifact.unavailable(
        "delegated_authority_verification",
        "DLG-01 results are recorded per evaluation by the deployment that ran "
        "the engine. This exporter reads no live call state; attach the "
        "DelegationResult your integration recorded, or omit this artifact. "
        "It is absent by default because delegation verification is opt-in.",
    )


def collect_control_profile() -> Artifact:
    """The control questionnaire, with each control's implementation status.

    Status is derived from the engine's own rule set, so it cannot drift from
    what the code actually evaluates.
    """
    try:
        from src.nhid_policy_engine_v1 import (
            evaluate_atr01, evaluate_dbc01, evaluate_dlg01,
            evaluate_eit01, evaluate_idg01, evaluate_pdx01,
        )
    except Exception as exc:
        return Artifact.unavailable("control_profile", f"policy engine unavailable: {exc}")

    controls = {
        "IDG-01": {"name": "Identity Disclosure Gate", "evaluator": evaluate_idg01.__name__, "opt_in": False},
        "PDX-01": {"name": "Pre-Data Exchange Gate", "evaluator": evaluate_pdx01.__name__, "opt_in": False},
        "DBC-01": {"name": "Deceptive Behavior Check", "evaluator": evaluate_dbc01.__name__, "opt_in": False},
        "EIT-01": {"name": "Escalation Implementation Test", "evaluator": evaluate_eit01.__name__, "opt_in": False},
        "ATR-01": {"name": "Audit Trail Requirements", "evaluator": evaluate_atr01.__name__, "opt_in": False},
        "DLG-01": {"name": "Delegated Authority Gate", "evaluator": evaluate_dlg01.__name__, "opt_in": True},
    }
    return Artifact.available(
        "control_profile",
        controls,
        questionnaire="docs/vendor-trust-questionnaire.md",
        note=(
            "Lists which controls this build evaluates. It is a self-report of "
            "implementation, not an assessment, score, or certification."
        ),
    )


# ── Bundle assembly ───────────────────────────────────────────────────────

def resolve_secret_key(explicit: str | None = None) -> bytes | None:
    """The audit signing key, from the CLI flag or NHID_AUDIT_SECRET_KEY (hex)."""
    raw = explicit or os.environ.get("NHID_AUDIT_SECRET_KEY")
    if not raw:
        return None
    try:
        return bytes.fromhex(raw)
    except ValueError:
        return raw.encode("utf-8")


def build_bundle(
    audit_db: str | None = None,
    session_id: str | None = None,
    include_conformance: bool = True,
    secret_key: bytes | None = None,
) -> dict[str, Any]:
    """Assemble the evidence bundle. Deterministic apart from the timestamp."""
    resolved_db, db_reason = _resolve_audit_db(audit_db)

    artifacts = [
        collect_control_profile(),
        collect_conformance() if include_conformance
        else Artifact.unavailable("conformance_results", "skipped via --no-conformance"),
        collect_session_evidence(resolved_db, session_id, db_reason),
        collect_delegation_result(session_id),
        collect_fhir_bundle(resolved_db, session_id, db_reason),
        collect_audit_chain(resolved_db, session_id, db_reason, secret_key),
    ]

    available = [a["name"] for a in artifacts if a["status"] == "available"]
    unavailable = [a["name"] for a in artifacts if a["status"] == "unavailable"]

    return {
        "manifest": {
            "export_format_version": EXPORT_FORMAT_VERSION,
            "generated_at": _utc_now(),
            "git_revision": _git_revision(),
            "working_tree_dirty": _git_is_dirty(),
            "session_id": session_id,
            "artifacts_available": available,
            "artifacts_unavailable": unavailable,
            "reproduction_commands": REPRODUCTION_COMMANDS,
            "boundaries": [
                "This bundle reports what one run produced. It is not an "
                "attestation, certification, audit opinion, or assurance "
                "engagement, and it asserts no regulatory compliance.",
                "NHID-Clinical does not verify vendors, providers, or NPIs "
                "against any external registry.",
                "Artifacts marked 'unavailable' were not produced by this run. "
                "No placeholder or inferred content is substituted for them.",
                "Verify by re-running the commands in reproduction_commands "
                "against the named git revision.",
            ],
        },
        "artifacts": {a["name"]: dict(a) for a in artifacts},
    }


def _canonical_json(bundle: dict[str, Any]) -> str:
    return json.dumps(bundle, indent=2, sort_keys=True, default=str)


def write_bundle(bundle: dict[str, Any], out_dir: str) -> Path:
    """Write the bundle plus a checksum over its canonical serialization."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    payload = _canonical_json(bundle)
    bundle_path = out / "evidence-pack.json"
    bundle_path.write_text(payload, encoding="utf-8")

    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    (out / "evidence-pack.sha256").write_text(
        f"{digest}  evidence-pack.json\n", encoding="utf-8"
    )
    return bundle_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export a reproducible NHID-Clinical evidence pack.",
    )
    parser.add_argument("--out", required=True, help="output directory")
    parser.add_argument("--audit-db", default=None, help="path to the audit store")
    parser.add_argument("--session-id", default=None, help="session to export")
    parser.add_argument(
        "--audit-secret-key", default=None,
        help="hex HMAC key the audit events were signed with "
             "(or set NHID_AUDIT_SECRET_KEY); required to verify the chain",
    )
    parser.add_argument(
        "--no-conformance", action="store_true",
        help="skip the conformance run (it is recorded as unavailable)",
    )
    args = parser.parse_args(argv)

    bundle = build_bundle(
        audit_db=args.audit_db,
        session_id=args.session_id,
        include_conformance=not args.no_conformance,
        secret_key=resolve_secret_key(args.audit_secret_key),
    )
    path = write_bundle(bundle, args.out)

    manifest = bundle["manifest"]
    print(f"Evidence pack written: {path}")
    print(f"  available:   {', '.join(manifest['artifacts_available']) or 'none'}")
    print(f"  unavailable: {', '.join(manifest['artifacts_unavailable']) or 'none'}")
    if manifest["working_tree_dirty"]:
        print("  note: generated from a dirty working tree — commit before sharing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
