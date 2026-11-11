"""
The call always runs one way: the AI agent PLACES the call to the payer.

CLAUDE.md §1: the caller-agent telephones a payer and asks for a patient's
eligibility, claim status or other PHI; the payer's representative receives
it. In 2026-11 more than fifty agent lines across the corpora, the website,
the demo data and the launch drafts had the agent speaking as the party that
RECEIVED the call ("Thank you for calling…", "What's your member ID?",
"Your authorization is approved") or asking the payer for the patient's own
identifiers. They were rewritten (archive §19.27). This test keeps them out.

It looks for receiver-voice phrases in two places:

* every agent turn in every corpus and demo payload the project ships;
* every published page, generated page, launch draft and current-state doc.

A phrase spoken by the payer's representative ("Claims department, how can I
help?") is fine; that is why "how can I help" is only checked in agent turns.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# The agent speaking as the receiver, or asking the payer for the patient's
# own identifiers.
RECEIVER_VOICE = re.compile(
    r"thank you for calling"
    r"|you'?ve reached the"
    r"|your authori[sz]ation is (approved|denied)"
    r"|look up your (authori[sz]ation|account|record)"
    r"|what'?s your member id"
    r"|(can|may) i (have|get) (your|the) (member id|npi|date of birth)"
    r"|can i get the npi"
    r"|(can|could) you confirm the (member id|date of birth|dob|npi)",
    re.IGNORECASE,
)
AGENT_ONLY = re.compile(r"how can i help", re.IGNORECASE)

CORPORA = [
    "tests/evaluation_corpus_v1.json",
    "tests/evaluation_corpus_v2.json",
    "tests/adversarial_corpus_v1.json",
    "tests/adversarial_cases.json",
]
AGENT_ROLES = {"agent", "bot", "assistant", None}

# Pages and docs a reader meets. The archive and the threat model quote the
# old lines as history and as recorded conflicts; payer-initiated-calls.md is
# the documented reverse-direction extension.
EXEMPT_DOCS = {
    "docs/MASTER-KNOWLEDGE-ARCHIVE.md",
    "docs/canonical-threat-model.md",
    "docs/payer-initiated-calls.md",
}


def _published_pages() -> list[Path]:
    script = (ROOT / "scripts" / "build_pages_site.sh").read_text(encoding="utf-8")
    block = re.search(r"RETIRED_PAGES=\((.*?)\)", script, re.S).group(1)
    retired = set(block.split())
    pages = [p for p in ROOT.glob("*.html") if p.name not in retired]
    pages += list((ROOT / "assets" / "media").glob("*.html"))
    pages += list((ROOT / "framework").glob("*.html"))
    return pages


def _surfaces() -> list[Path]:
    files = _published_pages() + [ROOT / "README.md", ROOT / "scripts" / "generate_pdfs.py"]
    files += [p for p in (ROOT / "docs").glob("*.md")
              if p.relative_to(ROOT).as_posix() not in EXEMPT_DOCS]
    for sub in ("launch", "pilot-kit", "validation", "agents"):
        files += list((ROOT / "docs" / sub).glob("*.md"))
    return sorted(set(files))


def _agent_lines():
    for name in CORPORA:
        data = json.loads((ROOT / name).read_text(encoding="utf-8"))
        items = data if isinstance(data, list) else [
            x for v in data.values() if isinstance(v, list) for x in v if isinstance(x, dict)]
        for item in items:
            turns = item.get("turns") or (item.get("payload") or {}).get("turns") or []
            ident = item.get("scenario_id") or item.get("case_id")
            for i, turn in enumerate(turns):
                if turn.get("speaker") in AGENT_ROLES:
                    for field in ("speech_text", "identity_assertion_text", "identity_assertion"):
                        if isinstance(turn.get(field), str):
                            yield f"{name}:{ident}[{i}].{field}", turn[field]
    for path in sorted((ROOT / "tests" / "demo_scenarios").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for i, msg in enumerate(data.get("messages") or data.get("transcript") or []):
            if (msg.get("role") or msg.get("speaker")) in {"bot", "agent"}:
                yield f"{path.name}[{i}]", msg.get("message") or msg.get("text") or ""
    # The home-page hero is generated from a script, not a corpus.
    from scripts.build_gateway_fixture import HERO_TURNS
    for i, turn in enumerate(HERO_TURNS):
        if turn["speaker"] == "agent":
            yield f"hero[{i}]", turn["speech_text"]
    from src.pilot_measure import demo_records
    for rec in demo_records():
        if rec["speaker"] == "agent":
            yield f"demo:{rec['session_id']}[{rec['turn_index']}]", rec["speech_text"]


def test_no_agent_line_speaks_as_the_receiver():
    bad = [f"{where}: {text!r}" for where, text in _agent_lines()
           if RECEIVER_VOICE.search(text) or AGENT_ONLY.search(text)]
    assert not bad, "agent lines that run the call backwards:\n" + "\n".join(bad)


@pytest.mark.parametrize("path", _surfaces(), ids=lambda p: p.relative_to(ROOT).as_posix())
def test_no_published_surface_runs_the_call_backwards(path):
    text = path.read_text(encoding="utf-8")
    bad = [f"line {n}: {line.strip()[:120]}"
           for n, line in enumerate(text.splitlines(), 1) if RECEIVER_VOICE.search(line)]
    assert not bad, f"{path.relative_to(ROOT)} runs the call backwards:\n" + "\n".join(bad)


def test_the_check_would_catch_the_lines_it_replaced():
    for line in ("Thank you for calling. I'm an AI assistant.",
                 "Can I have your member ID and date of birth to look up your authorization?",
                 "Your authorization is approved.",
                 "You've reached the claims system.",
                 "Hi, can I get the member ID and NPI?",
                 "Can you confirm the member ID on claim 48213 so I can check its status?",
                 "Thank you. Could you confirm the member ID on file?"):
        assert RECEIVER_VOICE.search(line), line
    assert not RECEIVER_VOICE.search("The member ID is MBR-482913. What's the claim status?")


# ── The other half: the human who ANSWERED must not sound like the caller ──
#
# The receiver is the payer's representative, a person, who picked up. In the
# live ElevenLabs runner (tests/elevenlabs_cts_runner.py) the representative's
# scripted lines said "Hello, calling about a prior authorization", "The member
# ID is 12345678. Can you look that up?", and the driver threw away Ida's
# opening line. That wired Ida as the party answering a call from a human.
# Fixed 2026-11-05. An AI answering for the payer is a separate scenario,
# deferred; it is not part of the canonical model.
CALLER_VOICE = re.compile(
    r"\bcalling (about|for|regarding|to)\b"
    r"|\bi'?m calling\b"
    r"|\bi have an? [\w ]{0,20}(request|claim|question) for\b"
    r"|\b(member id|date of birth|dob|diagnosis code) is \S"
    r"|\bcan you (look|pull) (that|this|it) up\b"
    r"|\bpull up the member"
    r"|\bwe received an incoming\b",
    re.IGNORECASE,
)


def _runner_receiver_lines():
    import sys
    sys.path.insert(0, str(ROOT / "tests"))
    sys.path.insert(0, str(ROOT))
    from elevenlabs_cts_runner import SCENARIOS
    for sc in SCENARIOS:
        for i, (role, text) in enumerate(sc["turns"]):
            if role == "user":
                yield f"elevenlabs_cts_runner:{sc['id']}[{i}]", text


def test_the_representative_never_speaks_as_the_caller():
    bad = [f"{where}: {text!r}" for where, text in _runner_receiver_lines()
           if CALLER_VOICE.search(text)]
    assert not bad, ("lines for the payer's representative that place the call, or hand "
                     "Ida the patient's identifiers:\n" + "\n".join(bad))


def test_the_caller_check_would_catch_the_lines_it_replaced():
    for line in ("Hello, calling about a prior authorization.",
                 "Hi, I have a prior auth request for a member.",
                 "The member ID is 12345678. Can you look that up?",
                 "Can you pull up the member's eligibility? Member ID is 98765432.",
                 "Hello, we received an incoming prior auth call."):
        assert CALLER_VOICE.search(line), line
    assert not CALLER_VOICE.search("Provider services, this is Dana. How can I help you?")
    assert not CALLER_VOICE.search("Okay, go ahead with the member ID.")


def test_ida_speaks_first_in_the_live_runner():
    """The driver records Ida's opening line (her disclosure) before the
    representative's first turn: she placed the call."""
    import asyncio
    import json as _json
    import sys
    sys.path.insert(0, str(ROOT / "tests"))
    import elevenlabs_cts_runner as runner

    class FakeWS:
        def __init__(self):
            self.inbox = [{"type": "conversation_initiation_metadata"},
                          {"type": "agent_response", "agent_response_event": {
                              "agent_response": "Hi, this is Ida, an automated AI assistant calling about a claim."}}]
            self.sent = []

        async def send(self, raw):
            self.sent.append(_json.loads(raw))
            if "user_transcript" in raw:
                self.inbox.append({"type": "agent_response", "agent_response_event": {
                    "agent_response": "The member ID is RVD-204-7731."}})

        async def recv(self):
            if not self.inbox:
                raise asyncio.TimeoutError
            return _json.dumps(self.inbox.pop(0))

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration

    class FakeModule:
        @staticmethod
        def connect(uri):
            return FakeWS()

    orig = (runner._WS_OK, getattr(runner, "websockets", None))
    runner._WS_OK, runner.websockets = True, FakeModule
    try:
        transcript = asyncio.run(runner._run_conversation_ws(
            [("user", "Provider services, this is Dana.")], "test-key"))
    finally:
        runner._WS_OK, runner.websockets = orig
    assert transcript[0]["role"] == "agent"
    assert "automated" in transcript[0]["message"]
