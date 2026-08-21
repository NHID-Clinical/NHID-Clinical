"""
Evidence pack export — regression tests
=======================================
The property under test throughout is honesty: an artifact that cannot be
produced from the data present must be reported as unavailable with a reason,
never stubbed, defaulted, or inferred. A bundle that quietly substitutes
placeholder content for missing evidence is worse than no bundle, because a
reviewer cannot tell the difference.
"""
import json
import sqlite3

import pytest

from scripts.export_evidence_pack import (
    EXPORT_FORMAT_VERSION,
    Artifact,
    build_bundle,
    main,
    write_bundle,
)

SESSION_ID = "CA-evidence-0001"
AUDIT_KEY = b"0" * 32


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def audit_db(tmp_path):
    """An audit store holding a small, intact hash chain."""
    from src.audit_store import AuditStore

    db_path = str(tmp_path / "audit.db")
    store = AuditStore(db_path=db_path, secret_key=AUDIT_KEY)
    previous = None
    for i in range(3):
        event_id = f"evt-{i}"
        payload = {"turn": i, "action": "CONTINUE_AI"}
        timestamp = f"2026-08-21T10:00:0{i}Z"
        # write_event accepts evidence_hash=None, but verify_chain checks the
        # signature on every event, so an unsigned event can never verify. A
        # realistic fixture signs, exactly as a real writer must.
        store.write_event(
            event_id=event_id,
            session_id=SESSION_ID,
            event_type="POLICY_DECISION",
            timestamp=timestamp,
            agent_id="agent-001",
            organization_id="org-001",
            payload=payload,
            previous_event_id=previous,
            evidence_hash=store._integrity.sign_event(
                event_id=event_id,
                timestamp=timestamp,
                event_type="POLICY_DECISION",
                payload=payload,
                previous_event_id=previous,
            ),
        )
        previous = event_id
    return db_path


# ── Artifact honesty ───────────────────────────────────────────────────────

def test_unavailable_artifact_carries_a_reason_and_no_content():
    a = Artifact.unavailable("thing", "because reasons")
    assert a["status"] == "unavailable"
    assert a["content"] is None
    assert a["reason"] == "because reasons"


def test_available_artifact_carries_content():
    a = Artifact.available("thing", {"k": "v"})
    assert a["status"] == "available" and a["content"] == {"k": "v"}


# ── Successful export ──────────────────────────────────────────────────────

def test_export_without_session_still_produces_a_valid_bundle():
    """Conformance and the control profile need no session data."""
    bundle = build_bundle()
    assert "control_profile" in bundle["manifest"]["artifacts_available"]
    assert "conformance_results" in bundle["manifest"]["artifacts_available"]


def test_conformance_results_are_real_not_summarized():
    bundle = build_bundle()
    results = bundle["artifacts"]["conformance_results"]["content"]
    assert results["total"] == 18
    assert results["failed"] == 0
    assert len(results["results"]) == results["total"]


def test_control_profile_lists_dlg01_as_opt_in():
    """The profile must not imply delegation is verified by default."""
    profile = build_bundle()["artifacts"]["control_profile"]["content"]
    assert profile["DLG-01"]["opt_in"] is True
    assert all(profile[c]["opt_in"] is False for c in ("IDG-01", "PDX-01", "ATR-01"))


def test_control_profile_matches_the_engines_actual_evaluators():
    """Derived from the engine, so it cannot drift from what the code runs."""
    profile = build_bundle()["artifacts"]["control_profile"]["content"]
    assert profile["DLG-01"]["evaluator"] == "evaluate_dlg01"
    assert profile["PDX-01"]["evaluator"] == "evaluate_pdx01"


def test_session_artifacts_present_when_audit_data_exists(audit_db):
    bundle = build_bundle(
        audit_db=audit_db, session_id=SESSION_ID, secret_key=AUDIT_KEY
    )
    available = bundle["manifest"]["artifacts_available"]
    assert "policy_decisions" in available
    assert "audit_chain_verification" in available
    chain = bundle["artifacts"]["audit_chain_verification"]["content"]
    assert chain["chain_valid"] is True
    assert chain["event_count"] == 3


# ── Missing and invalid evidence ───────────────────────────────────────────

def test_missing_session_data_is_marked_unavailable_not_fabricated():
    bundle = build_bundle()
    for name in ("policy_decisions", "audit_chain_verification", "fhir_audit_bundle"):
        artifact = bundle["artifacts"][name]
        assert artifact["status"] == "unavailable"
        assert artifact["content"] is None
        assert artifact["reason"]


def test_nonexistent_audit_db_is_reported_not_raised(tmp_path):
    bundle = build_bundle(audit_db=str(tmp_path / "nope.db"), session_id=SESSION_ID)
    artifact = bundle["artifacts"]["audit_chain_verification"]
    assert artifact["status"] == "unavailable"
    assert "not found" in artifact["reason"]


def test_unknown_session_id_is_reported_not_fabricated(audit_db):
    bundle = build_bundle(
        audit_db=audit_db, session_id="CA-does-not-exist", secret_key=AUDIT_KEY
    )
    artifact = bundle["artifacts"]["audit_chain_verification"]
    assert artifact["status"] == "unavailable"
    assert "no audit events" in artifact["reason"]


def test_audit_db_without_session_id_is_unavailable(audit_db):
    bundle = build_bundle(audit_db=audit_db)
    assert bundle["artifacts"]["audit_chain_verification"]["status"] == "unavailable"


def test_tampered_chain_reports_invalid_rather_than_omitting_the_artifact(audit_db):
    """A broken chain is evidence too. It must be reported, not hidden."""
    conn = sqlite3.connect(audit_db)
    conn.execute(
        "UPDATE audit_events SET payload = ? WHERE event_id = ?",
        (json.dumps({"turn": 99, "action": "TAMPERED"}), "evt-1"),
    )
    conn.commit()
    conn.close()

    bundle = build_bundle(
        audit_db=audit_db, session_id=SESSION_ID, secret_key=AUDIT_KEY
    )
    artifact = bundle["artifacts"]["audit_chain_verification"]
    assert artifact["status"] == "available"
    assert artifact["content"]["chain_valid"] is False


def test_missing_signing_key_is_unavailable_not_reported_as_tampering(audit_db):
    """The decisive distinction: "cannot verify" must never be published as
    "chain invalid". AuditStore returns the same signature failure for a wrong
    key as for genuine tampering, so an absent key yields no verdict at all."""
    bundle = build_bundle(audit_db=audit_db, session_id=SESSION_ID)
    artifact = bundle["artifacts"]["audit_chain_verification"]
    assert artifact["status"] == "unavailable"
    assert artifact["content"] is None
    assert "indistinguishable" in artifact["reason"]


def test_wrong_signing_key_does_not_silently_claim_tampering(audit_db):
    """With a wrong key the tool does report invalid — it cannot tell. The
    manifest's reproduction commands are what let a reviewer resolve it."""
    bundle = build_bundle(
        audit_db=audit_db, session_id=SESSION_ID, secret_key=b"9" * 32
    )
    assert bundle["artifacts"]["audit_chain_verification"]["content"]["chain_valid"] is False


def test_secret_key_resolves_from_hex_and_env(monkeypatch):
    from scripts.export_evidence_pack import resolve_secret_key

    assert resolve_secret_key("30" * 32) == AUDIT_KEY
    assert resolve_secret_key(None) is None
    monkeypatch.setenv("NHID_AUDIT_SECRET_KEY", "30" * 32)
    assert resolve_secret_key(None) == AUDIT_KEY


def test_delegation_artifact_is_absent_by_default_with_an_explanation():
    artifact = build_bundle()["artifacts"]["delegated_authority_verification"]
    assert artifact["status"] == "unavailable"
    assert "opt-in" in artifact["reason"]


def test_no_conformance_flag_marks_it_unavailable_not_passing():
    bundle = build_bundle(include_conformance=False)
    artifact = bundle["artifacts"]["conformance_results"]
    assert artifact["status"] == "unavailable"
    assert artifact["content"] is None


# ── Determinism and reproducibility ────────────────────────────────────────

def test_bundle_structure_is_deterministic():
    """Only the timestamp and tree state may differ between runs."""
    volatile = {"generated_at", "working_tree_dirty"}
    a = build_bundle(include_conformance=False)["manifest"]
    b = build_bundle(include_conformance=False)["manifest"]
    assert {k: v for k, v in a.items() if k not in volatile} == \
           {k: v for k, v in b.items() if k not in volatile}


def test_conformance_results_are_reproducible():
    first = build_bundle()["artifacts"]["conformance_results"]["content"]
    second = build_bundle()["artifacts"]["conformance_results"]["content"]
    assert first == second


def test_manifest_records_reproduction_commands():
    manifest = build_bundle(include_conformance=False)["manifest"]
    assert manifest["reproduction_commands"]["unit_tests"] == "python -m pytest tests/ -q"
    assert manifest["export_format_version"] == EXPORT_FORMAT_VERSION


def test_manifest_states_its_boundaries():
    """Claim hygiene is part of the artifact, not just the docs."""
    text = " ".join(build_bundle(include_conformance=False)["manifest"]["boundaries"]).lower()
    for phrase in ("not an attestation", "certification", "no regulatory compliance"):
        assert phrase.split()[-1] in text
    assert "does not verify vendors" in text


# ── Output path handling ───────────────────────────────────────────────────

def test_write_creates_missing_directories(tmp_path):
    target = tmp_path / "nested" / "deeper"
    path = write_bundle(build_bundle(include_conformance=False), str(target))
    assert path.exists()
    assert json.loads(path.read_text())["manifest"]["export_format_version"]


def test_checksum_matches_the_written_bundle(tmp_path):
    import hashlib

    path = write_bundle(build_bundle(include_conformance=False), str(tmp_path))
    recorded = (tmp_path / "evidence-pack.sha256").read_text().split()[0]
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    assert recorded == actual


def test_rewrite_to_same_directory_overwrites_cleanly(tmp_path):
    write_bundle(build_bundle(include_conformance=False), str(tmp_path))
    write_bundle(build_bundle(include_conformance=False), str(tmp_path))
    assert json.loads((tmp_path / "evidence-pack.json").read_text())


def test_cli_entry_point_writes_a_bundle(tmp_path, capsys):
    exit_code = main(["--out", str(tmp_path), "--no-conformance"])
    assert exit_code == 0
    assert (tmp_path / "evidence-pack.json").exists()
    assert "Evidence pack written" in capsys.readouterr().out
