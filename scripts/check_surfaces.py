#!/usr/bin/env python3
"""Every change reaches every surface: the facts check.

docs/agents/surfaces.json lists the public facts (the stage, share-safe, the
no-network container, VER-01 inside DLG-01, key rotation, audit verification,
the capture vocabulary...) and, for each, the pages, PDF sources and docs that
must state it and the phrases that must no longer appear. This check reads
every listed surface and fails, naming the file and the missing phrase, when
one has fallen behind.

It complements, and does not replace:
  scripts/check_number_drift.py   published numbers
  tests/test_call_direction.py    the call always runs agent -> payer
  tests/test_pdf_freshness.py     PDFs rebuilt after their sources changed
  the generator --check modes     fixtures match the engine

    python scripts/check_surfaces.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "docs" / "agents" / "surfaces.json"


def problems() -> list[str]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    out: list[str] = []
    for fact in manifest["facts"]:
        for rel, phrases in fact.get("must_contain", {}).items():
            path = ROOT / rel
            if not path.exists():
                out.append(f"[{fact['id']}] {rel}: file listed in surfaces.json does not exist")
                continue
            text = path.read_text(encoding="utf-8")
            for phrase in phrases:
                if phrase not in text:
                    out.append(f"[{fact['id']}] {rel}: missing {phrase!r} ({fact['fact']})")
        for rel, phrases in fact.get("must_not_contain", {}).items():
            path = ROOT / rel
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            for phrase in phrases:
                if phrase in text:
                    out.append(f"[{fact['id']}] {rel}: still says {phrase!r} ({fact['fact']})")
    return out


def main() -> int:
    found = problems()
    if found:
        print("SURFACES FAIL: a public fact has not reached every surface that must state it.")
        for line in found:
            print("  " + line)
        print("Update the surface, or the manifest if the fact itself changed: docs/agents/surfaces.json")
        return 1
    count = len(json.loads(MANIFEST.read_text(encoding="utf-8"))["facts"])
    print(f"SURFACES PASS: {count} public facts present on every surface that must state them")
    return 0


if __name__ == "__main__":
    sys.exit(main())
