#!/usr/bin/env python3
"""
check_offline_kit.py — the Tier 0 kit must never gain the ability to phone home.

WHY THIS GUARD EXISTS
---------------------
`docs/pilot-kit/measure_pilot.py` runs on a payer's own machine, over their own
transcripts, and sends nothing anywhere. That is not a convenience — it is why
the kit needs no BAA, why its security review is short, and why "nothing leaves
your network" is a true sentence rather than a marketing one.

A single well-meaning `requests.post` would make that sentence false, and the
person who added it would not necessarily know what they had cost. Prose in a
README does not stop that. This does.

WHY IT PARSES INSTEAD OF GREPPING
---------------------------------
A grep for "requests" fails on the sentence "this kit does not use requests",
which is exactly the sentence an honest README should contain. Punishing the
documentation for describing the guarantee is a guard that teaches people to
delete the guarantee. So this walks the AST: only real imports, real attribute
access and real calls count. Comments, docstrings and string literals are
invisible to it, by design.

SCOPE AND LIMITS, STATED PLAINLY
--------------------------------
This catches the realistic accident: someone adds an HTTP client, a socket, or
a subprocess shelling out to curl. It is a static check and it is not a sandbox.

It will NOT catch:
  * dynamic dispatch — `getattr(__import__("requests"), "post")`
  * a file written to a directory that something else uploads
  * code reached through a module this list does not name

The second of those used to read "an exfiltration path hidden in a dependency
the kit imports", which was true when one file was guarded. GUARDED now names
the kit's whole import closure — the engine, the eval-loop wiring, the audit
trail and its integrity helper — so a dependency of the kit can no longer grow
a network client unnoticed. What remains unguarded is listed, with reasons,
beside GUARDED below; read that list rather than assuming the closure is
complete.

Defeating it requires deliberate effort, which is the correct bar for a guard
like this: it is here to stop a mistake, not a determined author. The real
assurance is that the kit's dependency surface stays small enough to read.

Run:  python scripts/check_offline_kit.py
Exit: 0 clean, 1 if the kit could reach the network.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Files that must stay offline. Add to this list; never remove from it without
# saying in the commit message what changed about the promise.
#
# This is the Tier 0 kit's IMPORT CLOSURE, not just its entry point. Guarding
# one file left the honest caveat below ("an exfiltration path hidden in a
# dependency") wide open: `measure_pilot.py` could stay spotless while the
# engine it calls grew an HTTP client. Every module the kit pulls in is
# standard-library-only today, so naming them all here costs nothing and locks
# that in.
GUARDED = [
    # The kit itself: the documented entry point, the measurement, the report,
    # and the PDF renderer.
    "docs/pilot-kit/measure_pilot.py",
    "src/pilot_measure.py",
    "src/pilot_report.py",
    "src/pilot_pdf.py",
    # The `nhid pilot` dispatcher. Guarded because that subcommand is the kit's
    # one-command front door, and a phone-home added there would be just as
    # false as one added to the kit. If another subcommand ever genuinely needs
    # subprocess or a network client, put that work in a module outside this
    # list and call it from here — do not drop cli.py from the list.
    "src/cli.py",
    # The engine the kit replays through, and its own imports. The kit's claim
    # rests on these as much as on its own files.
    "src/nhid_policy_engine_v1.py",
    "src/synthetic_eval_loop.py",
    "src/nhid_audit_trail.py",
    "src/audit_integrity.py",
]

# NOT guarded, and why — so the next person does not have to re-derive it:
#
#   scripts/generate_pdfs.py — `src/pilot_pdf.py` imports it for the house
#   style (fonts, colours, cover, footers). It does use `subprocess`, but only
#   inside its `if __name__ == "__main__":` block, to re-run the Playbook
#   build when it is executed as a script. An import cannot reach that code.
#   This checker walks the AST and has no notion of a __main__ guard, so
#   listing the file would fail the build for a path that does not exist.
#   Verified at scripts/generate_pdfs.py (the only `subprocess` uses in the
#   file are under that guard); re-check it if that changes.
#
#   reportlab — the one third-party package in the kit's PDF path, and an
#   optional extra. It writes a file; it does not open a socket.

# Modules that can open a connection or hand the job to something that can.
FORBIDDEN_MODULES = {
    "socket", "ssl", "http", "urllib", "urllib2", "urllib3", "ftplib",
    "telnetlib", "smtplib", "imaplib", "poplib", "xmlrpc", "asyncio",
    "requests", "httpx", "aiohttp", "websockets", "websocket", "grpc",
    "paramiko", "boto3", "botocore", "google", "azure", "subprocess", "ctypes",
}

# Attribute calls that reach out even without an obvious import.
FORBIDDEN_CALLS = {
    "urlopen", "urlretrieve", "getaddrinfo", "create_connection", "connect_ex",
    "check_output", "check_call", "Popen", "run", "system", "popen",
}

# Of those, the ones that are unambiguous enough to flag as a BARE call --
# `urlopen(url)` after a `from ... import urlopen`. The import itself is
# already caught, so this is belt-and-braces; it is restricted to names that
# cannot plausibly be a local helper, which is why `run` and `Popen` are absent.
FORBIDDEN_BARE_CALLS = {
    "urlopen", "urlretrieve", "getaddrinfo", "create_connection", "connect_ex",
}
# `run` and `system` are common words. Only flag them on a module that could
# actually execute something.
CALL_NEEDS_MODULE = {"run": {"subprocess", "os"}, "system": {"os"},
                     "popen": {"os", "subprocess"}}


class NetworkReachVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.findings: list[tuple[int, str]] = []
        self._aliases: dict[str, str] = {}

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            root = alias.name.split(".")[0]
            self._aliases[(alias.asname or alias.name).split(".")[0]] = root
            if root in FORBIDDEN_MODULES:
                self.findings.append((node.lineno, f"imports {alias.name!r}"))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        root = (node.module or "").split(".")[0]
        if root in FORBIDDEN_MODULES:
            names = ", ".join(a.name for a in node.names)
            self.findings.append(
                (node.lineno, f"imports {names!r} from {node.module!r}"))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in FORBIDDEN_CALLS:
            owner = func.value.id if isinstance(func.value, ast.Name) else None
            owner = self._aliases.get(owner or "", owner)
            required = CALL_NEEDS_MODULE.get(func.attr)
            if required is None or (owner in required):
                where = f"{owner}.{func.attr}" if owner else func.attr
                self.findings.append((node.lineno, f"calls {where}()"))
        if isinstance(func, ast.Name) and func.id in FORBIDDEN_BARE_CALLS:
            self.findings.append((node.lineno, f"calls {func.id}()"))
        # A bare __import__("requests") is dynamic, but the literal form is
        # common enough in a careless patch to be worth catching.
        if isinstance(func, ast.Name) and func.id == "__import__":
            if node.args and isinstance(node.args[0], ast.Constant):
                mod = str(node.args[0].value).split(".")[0]
                if mod in FORBIDDEN_MODULES:
                    self.findings.append(
                        (node.lineno, f"dynamically imports {mod!r}"))
        self.generic_visit(node)


def check(path: Path) -> list[tuple[int, str]]:
    visitor = NetworkReachVisitor()
    visitor.visit(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
    return visitor.findings


def main() -> int:
    failures = 0
    checked = 0
    for rel in GUARDED:
        path = REPO_ROOT / rel
        if not path.is_file():
            print(f"OFFLINE GUARD FAIL: {rel} is missing. If the kit moved, "
                  f"update GUARDED in this script in the same commit.")
            failures += 1
            continue
        checked += 1
        findings = check(path)
        if findings:
            failures += 1
            print(f"OFFLINE GUARD FAIL: {rel} can reach the network.")
            for lineno, what in findings:
                print(f"  {rel}:{lineno}  {what}")
            print("  The Tier 0 kit must send nothing. 'It runs in your "
                  "environment and nothing reaches us' is the reason it needs "
                  "no BAA; a network call makes that false.")
        else:
            print(f"  ok   {rel} — no import or call that could reach out")

    if failures:
        print(f"\nOFFLINE GUARD FAIL: {failures} problem(s).")
        return 1
    print(f"\nOFFLINE GUARD PASS: {checked} file(s) verified offline. "
          f"Static check only — see this script's docstring for its limits.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
