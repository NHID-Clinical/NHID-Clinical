"""The actor roles are stated, and nothing reverses them.

Why this test exists
--------------------
The canonical scenario is a caller-agent telephoning a **payer** and asking for a
patient's PHI, while claiming to be or to act for a **provider**. The payer's customer
service agent or claims associate **receives** that request and applies the controls.
Reverse those roles — a patient calling a voice agent, or the agent answering the phone —
and the controls are for something else entirely.

Two things made that reversal easy to fall into:

1. The repository carried **no project-level instructions at all**. `CLAUDE.md` did not
   exist, so nothing stated the model to a new session.
2. The published capture schema declares ``speaker: ["agent", "caller"]`` and documented
   only ``"agent"``. ``"caller"`` was undefined and in fact denotes the payer-side human —
   so a reader meeting ``speaker: "caller"`` would reasonably conclude the human placed
   the call and the agent answered it. Exactly backwards.

The prose on the main surfaces was already right; the gap was that nothing held it there.
This is the same shape of defect as `test_control_set_completeness.py` guards: every
surface internally consistent, and the *model* behind them unasserted.

The reversal scan below carries one exemption, `docs/payer-initiated-calls.md`, which
documents the reverse call direction on purpose. Following the `drift-ok` convention in
`scripts/check_number_drift.py`, the exemption states its reason and is itself asserted —
that file must still name the canonical direction and label itself an extension — so the
exemption cannot quietly become a hole.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
INSTRUCTIONS = ROOT / "CLAUDE.md"
THREAT_MODEL = ROOT / "docs" / "canonical-threat-model.md"
CAPTURE_SCHEMA = ROOT / "docs" / "pilot-kit" / "minimal-event-schema.json"

#: The five actors, exactly as the canonical model names them.
ACTORS = (
    "Requesting caller-agent",
    "Receiving payer employee",
    "Patient",
    "Provider or represented organization",
    "Protected asset",
)


# ── 1. The instructions exist and state the model ───────────────────────────

def test_project_instructions_exist():
    """There were none. A session that inherits nothing can get this backwards."""
    assert INSTRUCTIONS.is_file(), (
        "CLAUDE.md is missing, so no tooling session inherits the threat model"
    )


def test_the_instructions_name_every_actor():
    text = INSTRUCTIONS.read_text(encoding="utf-8")
    missing = [a for a in ACTORS if a not in text]
    assert not missing, f"CLAUDE.md does not name: {missing}"


def test_the_instructions_state_the_call_direction():
    text = INSTRUCTIONS.read_text(encoding="utf-8").lower()
    assert "telephones a payer" in text or "calls a payer" in text, (
        "CLAUDE.md does not say which party places the call"
    )
    assert "never reverse" in text


def test_the_instructions_keep_the_three_distinctions_apart():
    """Disclosure is not verification; verification is not authorization; an
    asserted affiliation is neither."""
    text = INSTRUCTIONS.read_text(encoding="utf-8").lower()
    for claim in (
        "identity disclosure is not identity verification",
        "identity verification is not authorization",
    ):
        assert claim in text, f"CLAUDE.md no longer states: {claim!r}"


def test_the_instructions_keep_the_accuracy_constraint():
    text = INSTRUCTIONS.read_text(encoding="utf-8").lower()
    assert "independent research project" in text
    for forbidden_claim in ("hipaa certification", "independent validation"):
        assert forbidden_claim in text, (
            f"CLAUDE.md no longer disclaims {forbidden_claim!r}"
        )


# ── 2. The two copies do not drift ──────────────────────────────────────────

def _actor_labels(path: Path) -> set[str]:
    """Bolded first-column labels from the actor table in a markdown file."""
    return {
        m.group(1).strip()
        for m in re.finditer(r"^\|\s*\*\*(.+?)\*\*\s*\|", path.read_text(encoding="utf-8"),
                             re.MULTILINE)
    }


def test_the_threat_model_document_exists():
    assert THREAT_MODEL.is_file()


def test_the_document_and_the_instructions_agree_on_the_actors():
    """Two copies of a definition drift. This is the assertion that catches it."""
    in_instructions = _actor_labels(INSTRUCTIONS)
    in_document = _actor_labels(THREAT_MODEL)
    expected = set(ACTORS)
    assert expected <= in_instructions, (
        f"CLAUDE.md's actor table is missing {sorted(expected - in_instructions)}"
    )
    assert expected <= in_document, (
        f"canonical-threat-model.md is missing {sorted(expected - in_document)}"
    )


def test_the_instructions_link_to_the_document():
    assert "canonical-threat-model.md" in INSTRUCTIONS.read_text(encoding="utf-8")


def test_the_document_distinguishes_itself_from_the_audit_threat_model():
    """SECURITY.md has its own 'Threat Model' section about ATR-01 storage. Two
    documents under one name invite the wrong one being cited."""
    text = THREAT_MODEL.read_text(encoding="utf-8")
    assert "SECURITY.md" in text, (
        "the document does not distinguish itself from SECURITY.md's threat model"
    )


# ── 3. The capture schema defines both of its speaker values ────────────────

def test_the_schema_defines_both_speaker_values():
    schema = json.loads(CAPTURE_SCHEMA.read_text(encoding="utf-8"))
    speaker = schema["properties"]["speaker"]
    assert set(speaker["enum"]) == {"agent", "caller"}, (
        "the speaker vocabulary changed; update this guard and the threat model "
        "document together"
    )
    description = speaker["description"]
    assert "'agent'" in description and "'caller'" in description, (
        "the schema documents only one of its two speaker values"
    )


def test_the_schema_says_which_party_placed_the_call():
    description = json.loads(CAPTURE_SCHEMA.read_text(encoding="utf-8"))[
        "properties"]["speaker"]["description"].lower()
    assert "placed the call" in description
    assert "received" in description
    for payer_side in ("customer service agent", "claims associate"):
        assert payer_side in description, (
            f"the schema does not identify the 'caller' as the payer's {payer_side}"
        )


# ── 4. Nothing on a published surface reverses the roles ────────────────────

#: Watched prose. The reversal is a content defect, so this reads the surfaces a
#: reader actually meets rather than every file in the tree.
WATCHED = (
    "README.md",
    "index.html",
    "faq.html",
    "specification.html",
    "docs/nhid-clinical-technical-specification.md",
    "docs/terminology.md",
    "docs/pilot-kit/README.md",
    "docs/canonical-threat-model.md",
    "CLAUDE.md",
)

#: Exempt because it documents the reverse direction deliberately. Asserted
#: below, so the exemption cannot become a hole.
REVERSE_DIRECTION_DOC = "docs/payer-initiated-calls.md"

#: Assertions that the canonical scenario runs the other way. Narrow on purpose:
#: "inbound calls" and "receiver-side" are CORRECT (the payer receives), so the
#: patterns target the patient as caller and the agent as answerer, not the
#: direction words.
REVERSALS = (
    re.compile(r"patients?\s+(?:calls?|calling|dials?|phones?)\s+"
               r"(?:the\s+|an?\s+|our\s+)?(?:ai\s+|voice\s+)?agent", re.I),
    re.compile(r"members?\s+(?:calls?|calling|dials?)\s+"
               r"(?:the\s+|an?\s+|our\s+)?(?:ai\s+|voice\s+)?agent", re.I),
    re.compile(r"\bagent\s+(?:answers|receives|takes|picks\s+up)\s+"
               r"(?:the\s+|an?\s+)?(?:incoming\s+)?call\s+from\s+"
               r"(?:a\s+|the\s+)?(?:provider|patient|member)", re.I),
)


#: Cues that the sentence FORBIDS the reversal rather than asserting it. Without
#: this, the guard failed on its own documentation: CLAUDE.md's rule reads "Never
#: describe the scenario as a patient calling a voice agent", and the pattern
#: matched the thing being prohibited. A guard that cannot tell a prohibition
#: from an assertion makes the model harder to write down, not easier.
NEGATIONS = re.compile(
    r"\b(?:never|not|n't|avoid|rather than|instead of|unless|reversed?|"
    r"incorrect(?:ly)?|wrong|mistak\w*|do not|don't|must not|no longer)\b",
    re.I,
)

#: How far back to read for a negation cue. One sentence's worth.
NEGATION_WINDOW = 180


def _asserted_reversals(text: str) -> list[str]:
    """Reversal phrases the text asserts, skipping ones it forbids."""
    asserted = []
    for pattern in REVERSALS:
        for match in pattern.finditer(text):
            before = text[max(0, match.start() - NEGATION_WINDOW):match.start()]
            # Read back only to the start of the current sentence or list item,
            # so a negation three sentences earlier does not excuse this one.
            sentence = re.split(r"(?<=[.!?])\s|\n\s*[-*|]\s|\n\n", before)[-1]
            if NEGATIONS.search(sentence):
                continue
            asserted.append(match.group(0))
    return asserted


@pytest.mark.parametrize("relative", WATCHED)
def test_no_watched_surface_reverses_the_roles(relative):
    path = ROOT / relative
    if not path.is_file():
        pytest.skip(f"{relative} is not present")
    asserted = _asserted_reversals(path.read_text(encoding="utf-8", errors="replace"))
    assert not asserted, (
        f"{relative} asserts the reversed scenario: {asserted}. The caller is the "
        f"agent; the payer's employee receives. See docs/canonical-threat-model.md"
    )


def test_the_reverse_direction_doc_still_labels_itself_an_extension():
    """The one exemption, asserted. If this file stops naming the canonical
    direction, the exemption is covering a real reversal."""
    text = (ROOT / REVERSE_DIRECTION_DOC).read_text(encoding="utf-8")
    assert "outbound to a payer" in text, (
        "the reverse-direction guide no longer states the canonical direction first"
    )
    assert "reverse direction" in text.lower()
    assert "policy-extension" in text.lower() or "extension guide" in text.lower()


def test_the_reversal_patterns_actually_match_a_reversal():
    """A guard that has never failed has not been tested."""
    for sample in (
        "In this flow a patient calls the AI agent to check eligibility.",
        "A member calls our voice agent about a claim.",
        "The agent answers an incoming call from a provider.",
    ):
        assert _asserted_reversals(sample), sample


def test_a_prohibition_is_not_an_assertion():
    """The guard's first run failed on CLAUDE.md's own rule forbidding the
    reversal. Stating the rule must stay possible."""
    for sample in (
        "Never describe the scenario as a patient calling a voice agent.",
        "Do not write that the agent answers an incoming call from a provider.",
        "It is wrong to say a member calls our voice agent.",
        "This is the reversed shape: a patient calls the AI agent.",
    ):
        assert not _asserted_reversals(sample), sample


def test_a_negation_in_an_earlier_sentence_does_not_excuse_a_later_reversal():
    """Otherwise one 'never' at the top of a file would exempt the whole file."""
    sample = (
        "Never reverse the roles. The controls are deterministic and replayable. "
        "In this flow a patient calls the AI agent to check eligibility."
    )
    assert _asserted_reversals(sample) == ["patient calls the AI agent"]


def test_the_reversal_patterns_leave_the_correct_framing_alone():
    """These all describe the canonical model correctly and must not trip it."""
    for sample in (
        "A payer or provider can run it receiver-side on inbound calls.",
        "the B2B scenario where an AI agent calls a payer office on behalf of a provider",
        "Log incoming calls. Identify which callers are AI voice agents.",
        "a payer's AI agent calling a provider",  # the documented reverse direction
        "INGRESS LAYER: Accept incoming call.",
    ):
        assert not _asserted_reversals(sample), sample


# ── 5. The distinction stays stated where it already was ────────────────────

def test_terminology_keeps_the_authorization_disclaimer():
    """`docs/terminology.md` states it for Impersonation Latency. It predates
    this guard and must not be dropped on the grounds that CLAUDE.md now says it."""
    text = (ROOT / "docs" / "terminology.md").read_text(encoding="utf-8")
    assert "establish authentication or authorization" in text
    assert "may still be unauthorized" in text
