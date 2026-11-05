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
    r"|can i get the npi",
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
                 "Hi, can I get the member ID and NPI?"):
        assert RECEIVER_VOICE.search(line), line
    assert not RECEIVER_VOICE.search("The member ID is MBR-482913. What's the claim status?")
