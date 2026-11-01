"""Share-safe evidence packs: ``nhid pilot --share-safe``.

The Tier 0 kit already runs on the payer's own machine and sends nothing
anywhere (``scripts/check_offline_kit.py``). What it did not do is check the
evidence pack it writes, the thing a payer then emails to someone else:

* ``per-call/<session_id>.json`` used the payer's own call identifiers as file
  names and contents;
* the report named the capture file;
* nothing verified that transcript text, member numbers or similar never found
  their way into an output file.

With ``--share-safe`` the pack is built in a staging directory, call ids are
replaced by keyed pseudonyms, every text file is scanned, and the pack is moved
to ``--out`` only if the scan passes. The pseudonym key and the lookup table go
to ``<out>.local/``, which is never part of the pack and must not be sent.

What the scan checks, and what it cannot
----------------------------------------
It refuses a pack in which any text file contains:

* a run of ``OVERLAP_WORDS`` consecutive words from any input transcript field;
* a raw ``session_id``, or an identifier-like token from the input text
  (letters and digits mixed, 6+ characters: member numbers, claim numbers);
* an SSN-like number, a slash-format date, a phone number, or an email address.

It is a pattern-and-overlap check, **not de-identification** under HIPAA's Safe
Harbor or Expert Determination methods. It cannot recognise a name, or an
identifier that matches no pattern and never appeared in the input. The
manifest says so, and the payer's privacy officer reviews it before sending.

A failure names the file, the line and the category, never the matched text:
an error message that quoted the leak would be a leak.

Offline, standard library only: listed in ``GUARDED`` in
``scripts/check_offline_kit.py``.
"""
from __future__ import annotations

import csv
import hashlib
import hmac
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

#: Consecutive words from an input transcript that may not appear in the pack.
OVERLAP_WORDS = 6

TEXT_FIELDS = ("speech_text", "disclosure_heard_text", "identity_assertion_text")

_WORD = re.compile(r"[a-z0-9']+")
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{4,}[A-Za-z0-9]")
PATTERNS = {
    "ssn-like number": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "slash-format date": re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b"),
    "phone number": re.compile(r"(?<![\w.])(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}\b"),
    "email address": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
}

PACK_STATEMENT = (
    "This pack contains aggregate measurements and per-call verdicts only. It "
    "contains no transcript text and no call identifiers: calls are named by "
    "keyed pseudonyms, and the key and the lookup table were written to a "
    "separate local directory that is not part of this pack. Every text file "
    "was scanned before release for transcript overlap, identifiers taken from "
    "the input, and common identifier patterns. This is a pattern-and-overlap "
    "check, not de-identification under HIPAA's Safe Harbor or Expert "
    "Determination methods: it cannot recognise a name, or an identifier that "
    "matches no pattern and never appeared in the input. Review before sending."
)

FILE_FIELDS = {
    "pilot_report.md": "aggregate metrics with denominators; report header fields you supplied",
    "metrics.json": "the same aggregate metrics, machine-readable",
    "per-call/": "per call: pseudonym, conformant (true/false), violated control ids",
    "pilot_report.pdf": "rendered from pilot_report.md after it passed the scan",
}


# ── pseudonyms ───────────────────────────────────────────────────────────────

def load_or_create_key(path: Optional[str], local_dir: Path) -> bytes:
    """A 32-byte pseudonym key: read from ``path``, or generated into ``local_dir``.

    A stable key file keeps pseudonyms stable across runs, so week-two results
    can be compared with week one. Without one, a fresh key is written to the
    local directory, so the payer can still map pseudonyms back.
    """
    if path:
        raw = Path(path).read_bytes().strip()
        key = bytes.fromhex(raw.decode("ascii")) if len(raw) == 64 else raw
        if len(key) != 32:
            raise ValueError("pseudonym key file must hold 32 bytes, or 64 hex characters")
        return key
    key = os.urandom(32)
    local_dir.mkdir(parents=True, exist_ok=True)
    (local_dir / "pseudonym.key").write_text(key.hex() + "\n", encoding="ascii")
    return key


def pseudonym(session_id: str, key: bytes) -> str:
    return "call-" + hmac.new(key, session_id.encode("utf-8"), hashlib.sha256).hexdigest()[:12]


def pseudonymise_calls(calls: Sequence[dict], key: bytes) -> List[dict]:
    return [{**call, "session_id": pseudonym(call["session_id"], key)} for call in calls]


def write_session_map(calls: Sequence[dict], key: bytes, local_dir: Path) -> Path:
    local_dir.mkdir(parents=True, exist_ok=True)
    path = local_dir / "session-map.csv"
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["pseudonym", "session_id"])
        for call in calls:
            writer.writerow([pseudonym(call["session_id"], key), call["session_id"]])
    return path


# ── the scan ─────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Finding:
    file: str
    line: int
    category: str

    def __str__(self) -> str:  # never includes the matched text
        return f"{self.file}:{self.line}: {self.category}"


def _words(text: str) -> List[str]:
    return _WORD.findall(text.lower())


def _ngrams(words: Sequence[str], n: int) -> Iterable[tuple]:
    return (tuple(words[i:i + n]) for i in range(len(words) - n + 1))


def _identifier_tokens(text: str) -> set:
    return {t for t in _TOKEN.findall(text)
            if any(c.isdigit() for c in t) and any(c.isalpha() for c in t)}


def scan_pack(pack_dir: Path, records: Sequence[dict]) -> List[Finding]:
    """Every reason this pack must not leave the machine. Empty means it may."""
    overlap: set = set()
    identifiers: set = set()
    for rec in records:
        if rec.get("session_id"):
            identifiers.add(str(rec["session_id"]))
        for field in TEXT_FIELDS:
            text = rec.get(field) or ""
            overlap.update(_ngrams(_words(text), OVERLAP_WORDS))
            identifiers.update(_identifier_tokens(text))

    findings: List[Finding] = []
    for path in sorted(p for p in pack_dir.rglob("*") if p.is_file()):
        rel = path.relative_to(pack_dir).as_posix()
        if path.suffix not in {".md", ".json"}:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if overlap and any(g in overlap for g in _ngrams(_words(line), OVERLAP_WORDS)):
                findings.append(Finding(rel, number, "transcript text"))
            if any(ident in line for ident in identifiers):
                findings.append(Finding(rel, number, "identifier from the input"))
            for category, pattern in PATTERNS.items():
                if pattern.search(line):
                    findings.append(Finding(rel, number, category))
        if any(ident in rel for ident in identifiers):
            findings.append(Finding(rel, 0, "identifier from the input (in the file name)"))
    return findings


# ── the manifest ─────────────────────────────────────────────────────────────

def write_manifest(pack_dir: Path, *, kit_version: str, calls: int) -> Path:
    files = []
    for path in sorted(p for p in pack_dir.rglob("*") if p.is_file()):
        rel = path.relative_to(pack_dir).as_posix()
        key = "per-call/" if rel.startswith("per-call/") else rel
        files.append({
            "path": rel,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "contains": FILE_FIELDS.get(key, "see file"),
        })
    manifest = {
        "kind": "nhid-clinical share-safe pilot pack",
        "kit_version": kit_version,
        "calls": calls,
        "statement": PACK_STATEMENT,
        "scan": {
            "result": "passed",
            "checks": [
                f"no run of {OVERLAP_WORDS} consecutive words from any input transcript field",
                "no raw session id, and no identifier-like token from the input text",
                *[f"no {name}" for name in PATTERNS],
            ],
        },
        "not_in_this_pack": ["transcripts", "session ids", "pseudonym key", "session-map.csv"],
        "files": files,
    }
    path = pack_dir / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return path
