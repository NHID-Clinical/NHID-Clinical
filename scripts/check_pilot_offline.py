#!/usr/bin/env python3
"""Fail CI if the Tier 0 pilot measurement script gains network dependencies.

The pilot kit is intentionally offline. This guard checks the source AST rather
than grepping comments, so explanatory text does not trigger false positives.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "docs" / "pilot-kit" / "measure_pilot.py"
FORBIDDEN_MODULES = {
    "requests", "httpx", "aiohttp", "urllib", "socket", "websocket",
    "websockets", "ftplib", "smtplib",
}
FORBIDDEN_CALLS = {"urlopen", "urlretrieve", "create_connection", "connect_ex"}

def main() -> int:
    tree = ast.parse(TARGET.read_text(encoding="utf-8"), filename=str(TARGET))
    problems: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                if root in FORBIDDEN_MODULES:
                    problems.append(f"line {node.lineno}: network module import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".", 1)[0]
            if root in FORBIDDEN_MODULES:
                problems.append(f"line {node.lineno}: network module import from {node.module}")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_CALLS:
                problems.append(f"line {node.lineno}: network call {node.func.id}(...)")

    if problems:
        print("FAIL: Tier 0 pilot kit must remain offline:", file=sys.stderr)
        print("\n".join(f"  - {p}" for p in problems), file=sys.stderr)
        return 1

    print("PASS: Tier 0 pilot measurement script has no forbidden network imports/calls.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
