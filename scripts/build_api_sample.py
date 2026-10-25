#!/usr/bin/env python3
"""
Developers page API sample: a real response, recorded, not typed
=================================================================
The "Try the live API" panel on developers.html shows one request to the
hosted adapter route and the answer. The answer is not written by hand: this
script runs the request through `functions.handler.lambda_handler`, the same
function the hosted route calls, and writes what came back between markers on
the page and into `assets/data/api-sample.json`. `--check` fails CI when the
recorded answer no longer matches the engine, so "real response" stays true.

The transcript is synthetic. The identifiers are not real. No PHI.

Usage:
    python scripts/build_api_sample.py            # write the sample
    python scripts/build_api_sample.py --check    # verify, write nothing
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from functions.handler import lambda_handler  # noqa: E402

OUT = ROOT / "assets" / "data" / "api-sample.json"
PAGE = ROOT / "developers.html"
BEGIN = "<!-- BEGIN GENERATED api-sample -->"
END = "<!-- END GENERATED api-sample -->"

ROUTE = "/v1/adapters/vapi/check"
#: The page's own example: an agent asking for protected data before it has
#: disclosed, then disclosing too late. Synthetic; nothing here is a real call.
REQUEST = {
    "call": {"id": "call_demo", "startedAt": "2026-06-09T10:00:00Z"},
    "messages": [
        {"role": "bot", "message": "Hi, can I get the member ID and NPI?", "secondsFromStart": 0.3},
        {"role": "user", "message": "NPI is 1234567890.", "secondsFromStart": 3.1},
        {"role": "bot", "message": "Thanks. I am an automated system.", "secondsFromStart": 5.8},
    ],
}


def build() -> dict:
    response = lambda_handler({"httpMethod": "POST", "path": ROUTE, "body": json.dumps(REQUEST)}, None)
    return {
        "generated_by": "scripts/build_api_sample.py",
        "handler": "functions/handler.py :: lambda_handler",
        "note": "Synthetic request; recorded response. No real call data and no PHI.",
        "route": ROUTE,
        "request": REQUEST,
        "status": response["statusCode"],
        "response": json.loads(response["body"]),
    }


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render(sample: dict) -> str:
    req = _esc(json.dumps(sample["request"], indent=2))
    res = _esc(json.dumps(sample["response"], indent=2))
    action = _esc(sample["response"].get("action", ""))
    reason = _esc(sample["response"].get("reason_code", ""))
    return "\n".join([
        BEGIN,
        f'            <div class="console-bar"><span><b>Request</b> &middot; synthetic transcript</span><code>POST {_esc(sample["route"])}</code></div>',
        f"            <pre><code>{req}</code></pre>",
        f'            <div class="console-bar"><span><b>Response</b> &middot; recorded from the handler</span><code>HTTP {sample["status"]}</code></div>',
        f"            <pre><code>{res}</code></pre>",
        f'            <p class="case-result is-fail"><span class="state-chip is-red">{action}</span> <code>{reason}</code> is the engine&rsquo;s composite decision for this transcript.</p>',
        f"            {END}",
    ])


def inject(sample: dict) -> bool:
    page = PAGE.read_text(encoding="utf-8")
    if BEGIN not in page or END not in page:
        raise SystemExit(f"{PAGE.name} has no generated api-sample block; add {BEGIN} / {END} markers first")
    start, finish = page.index(BEGIN), page.index(END) + len(END)
    fresh = render(sample)
    if page[start:finish] == fresh:
        return False
    PAGE.write_text(page[:start] + fresh + page[finish:], encoding="utf-8")
    return True


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="fail if the committed sample is missing or stale")
    args = ap.parse_args(argv)
    fresh = build()
    if args.check:
        if not OUT.exists():
            print(f"API SAMPLE FAIL: {OUT.relative_to(ROOT)} does not exist. Run scripts/build_api_sample.py.", file=sys.stderr)
            return 1
        committed = json.loads(OUT.read_text(encoding="utf-8"))
        for key in ("route", "request", "status", "response"):
            if committed.get(key) != fresh[key]:
                print(f"API SAMPLE FAIL: {OUT.relative_to(ROOT)} field {key!r} no longer matches the handler. "
                      "Re-run scripts/build_api_sample.py and commit the result.", file=sys.stderr)
                return 1
        page = PAGE.read_text(encoding="utf-8")
        if BEGIN not in page or END not in page:
            print(f"API SAMPLE FAIL: {PAGE.name} has lost its generated block.", file=sys.stderr)
            return 1
        if page[page.index(BEGIN):page.index(END) + len(END)] != render(fresh):
            print("API SAMPLE FAIL: the sample on developers.html no longer matches the handler's output. "
                  "Re-run scripts/build_api_sample.py and commit the result.", file=sys.stderr)
            return 1
        print(f"API SAMPLE PASS: developers.html shows the handler's answer for {ROUTE} "
              f"({fresh['response'].get('action')} / {fresh['response'].get('reason_code')})")
        return 0
    OUT.write_text(json.dumps(fresh, indent=2) + "\n", encoding="utf-8")
    changed = inject(fresh)
    print(f"Wrote {OUT.relative_to(ROOT)}; developers.html {'updated' if changed else 'already current'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
