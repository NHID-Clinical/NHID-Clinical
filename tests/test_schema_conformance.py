"""
The published schemas, actually enforced
========================================
This repository publishes two JSON Schemas and, until now, validated nothing
against either of them:

* `schema/nhid_trace_schema_v1.json` — the strict contract for an emitted
  pipeline event. Its own description says "All pipeline stages (INGEST through
  PERSIST) emit objects conforming to this schema."
* `docs/pilot-kit/minimal-event-schema.json` — the permissive Tier 0 capture
  record, one call turn.

`jsonschema` was a declared dependency imported by **no file in the
repository**, so the schemas were documentation that nothing could contradict.
That matters more than an unused dependency: the policy engine's design
*reasons from* the trace schema. `src/nhid_policy_engine_v1.py` argues that a
delegation belongs in `session` rather than `event` because the schema sets
`additionalProperties: false` and "a passport in the event would be a v1 schema
break". That argument is only sound if the schema really is strict and the
events really do conform — neither of which was checked.

So these tests pin three agreements rather than one schema:

1. each schema is a valid Draft 2020-12 schema;
2. the canonical event validates against the trace schema **and** is accepted
   by `evaluate_all`, so the schema and the engine describe the same object;
3. the strictness the engine's design cites is real, asserted by negative
   controls — a missing required field and an extra field both fail.
"""
import json
from pathlib import Path

import jsonschema
import pytest

from src.nhid_policy_engine_v1 import PolicyAction, evaluate_all
from src.pilot_measure import demo_records

ROOT = Path(__file__).resolve().parents[1]
TRACE_SCHEMA_PATH = ROOT / "schema" / "nhid_trace_schema_v1.json"
CAPTURE_SCHEMA_PATH = ROOT / "docs" / "pilot-kit" / "minimal-event-schema.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


TRACE_SCHEMA = _load(TRACE_SCHEMA_PATH)
CAPTURE_SCHEMA = _load(CAPTURE_SCHEMA_PATH)


def canonical_trace_event():
    """One fully-populated POLICY-stage event, in the published shape.

    Every field the schema requires is present. This is the object the schema
    and the engine must agree about, which is why it lives here rather than in
    either of them.
    """
    return {
        "event_id": "11111111-2222-3333-4444-555555555555",
        "timestamp": "2026-10-21T10:00:00.000Z",
        "session_id": "CA-schema-0001",
        "request_id": "req-schema-0001",
        "event_type": "POLICY",
        "actor_id": "nhid-conformance",
        "counterparty_type": "human_operator",
        "state_before": "AWAITING_DISCLOSURE",
        "state_after": "AWAITING_DISCLOSURE",
        "partial_failure": False,
        "boundary_violations": [],
        "replay_mode": "live",
        "external_calls_cached": False,
        "execution_context": {
            "pipeline_version": "1.0.0",
            "policy_engine_version": "1.0.0",
            "nhid_schema_version": "1.0",
        },
        "healthcare_governance": {
            "disclosure_timestamp": None,
            "identity_assertion_text": None,
            "deceptive_artifact_flags": [],
            "escalation_timestamp": None,
            "escalation_outcome": None,
            "phi_accessed": [],
        },
        "input_payload": {
            "speech_text": "I need the member ID for this authorization",
            "raw_form_fields": None,
        },
        "output_payload": None,
        "error": None,
        "policy_decision": None,
    }


# ── The schemas themselves ────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "name,schema",
    [("trace", TRACE_SCHEMA), ("capture", CAPTURE_SCHEMA)],
)
def test_the_schema_is_a_valid_draft_2020_12_schema(name, schema):
    """A published schema nothing validates against can also be a schema
    nothing has checked is well-formed."""
    jsonschema.Draft202012Validator.check_schema(schema)
    assert schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema"


def test_the_trace_schema_is_strict():
    """The engine's design cites this exact property.

    `evaluate_dlg01` reads the agent passport from `session` rather than
    `event`, and the stated reason is that the published event schema forbids
    additional properties. If that stopped being true the reasoning would be
    stale without anything failing.
    """
    assert TRACE_SCHEMA["additionalProperties"] is False


def test_the_capture_schema_is_deliberately_permissive():
    """The opposite choice, also deliberate: a pilot capture carries whatever
    the vendor's platform records alongside the fields NHID needs."""
    assert CAPTURE_SCHEMA.get("additionalProperties") is not False


# ── The trace schema and the engine agree ─────────────────────────────────────

def test_the_canonical_event_validates():
    validator = jsonschema.Draft202012Validator(TRACE_SCHEMA)
    errors = sorted(validator.iter_errors(canonical_trace_event()),
                    key=lambda e: list(e.path))
    assert errors == [], "; ".join(
        f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errors
    )


def test_the_engine_accepts_the_canonical_event():
    """The bridge. A schema the engine cannot consume describes nothing, and an
    engine whose input the schema rejects is undocumented."""
    decision = evaluate_all(
        {"turn_count": 3, "escalation_path_available": True},
        canonical_trace_event(),
    )
    # Asks for a member ID with no disclosure recorded: PDX-01's gate.
    assert decision.action == PolicyAction.DENY_DATA


@pytest.mark.parametrize("field", sorted(TRACE_SCHEMA["required"]))
def test_dropping_any_required_field_fails_validation(field):
    """Negative control per required field, so "required" is not decorative."""
    event = canonical_trace_event()
    del event[field]
    validator = jsonschema.Draft202012Validator(TRACE_SCHEMA)
    assert list(validator.iter_errors(event)), (
        f"removing required field {field!r} still validated"
    )


def test_an_extra_top_level_field_fails_validation():
    """Proves the strictness the engine's design relies on — in particular that
    a passport could not simply be added to the event."""
    event = canonical_trace_event()
    event["agent_passport"] = {"delegation": {}}
    validator = jsonschema.Draft202012Validator(TRACE_SCHEMA)
    errors = list(validator.iter_errors(event))
    assert errors, "an unknown top-level field was accepted"
    assert any("agent_passport" in e.message for e in errors)


# ── The capture schema and the pilot kit agree ────────────────────────────────

def test_the_pilot_kits_own_demo_records_validate():
    """`src/pilot_measure.demo_records()` is what `nhid pilot --demo` measures
    and what the Tier 0 documentation shows. It must satisfy the schema the
    pilot kit publishes beside it."""
    validator = jsonschema.Draft202012Validator(CAPTURE_SCHEMA)
    records = demo_records()
    assert records, "demo_records() returned nothing to validate"
    failures = []
    for index, record in enumerate(records):
        for error in validator.iter_errors(record):
            failures.append(
                f"record {index} ({record.get('session_id')}) "
                f"{'/'.join(map(str, error.path)) or '<root>'}: {error.message}"
            )
    assert failures == [], "; ".join(failures[:8])


@pytest.mark.parametrize("field", sorted(CAPTURE_SCHEMA["required"]))
def test_dropping_any_required_capture_field_fails(field):
    record = dict(demo_records()[0])
    del record[field]
    validator = jsonschema.Draft202012Validator(CAPTURE_SCHEMA)
    assert list(validator.iter_errors(record)), (
        f"removing required capture field {field!r} still validated"
    )
