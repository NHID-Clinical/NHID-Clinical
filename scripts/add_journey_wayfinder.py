#!/usr/bin/env python3
"""
Journey wayfinder — make the arc navigable, not just true
=========================================================
The IA consolidation mapped every destination to a journey, but only in
`ia-disposition.md`. A reader arriving on `evidence-pack.html` from a search
result had no way to see that they were three steps into an arc, or what the
step before and after were.

This inserts one small `<nav>` at the foot of each destination's main content,
naming the question that page answers and offering the adjacent steps. It is
generated rather than hand-written so the order cannot drift between eleven
pages, and so adding a destination is one edit here rather than eleven.

The arc is the one the redesign brief names:

    What is this? → What problem? → What does it control? → How do I evaluate?
    → How do I implement? → Where is the evidence? → Where is the source?

Legal pages sit outside the arc and get no wayfinder; pretending privacy policy
is step eight would be worse than leaving it out.

Usage:
    python scripts/add_journey_wayfinder.py            # insert or refresh
    python scripts/add_journey_wayfinder.py --check    # verify, write nothing
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BEGIN = "<!-- BEGIN GENERATED journey-wayfinder -->"
END = "<!-- END GENERATED journey-wayfinder -->"

# (file, href, journey, the question this destination answers)
ARC = [
    ("index.html", "/", "Understand", "What is this?"),
    ("specification.html", "/specification.html", "Understand", "What does it control?"),
    ("shadow-evaluation-guide.html", "/shadow-evaluation-guide.html", "Evaluate", "How do I evaluate it?"),
    ("developers.html", "/developers.html", "Implement", "How do I implement it?"),
    ("evidence-pack.html", "/evidence-pack.html", "Validate", "Where is the evidence?"),
    ("regulatory-alignment.html", "/regulatory-alignment.html", "Validate", "How does it map to regulation?"),
    ("framework/nhid-auth.html", "/framework/nhid-auth.html", "Adopt", "What comes after v1.3?"),
    ("faq.html", "/faq.html", "Understand", "What is still open?"),
    ("specs/index.html", "/specs/", "All", "Where do I download it?"),
]

GITHUB = "https://github.com/NHID-Clinical/NHID-Clinical"


def render(position: int) -> str:
    """The wayfinder for the destination at `position` in the arc."""
    _, _, journey, question = ARC[position]
    out = [BEGIN,
           '      <nav class="wayfinder" aria-label="Where this page sits in the journey">',
           f'        <p class="wayfinder-here"><span class="wayfinder-journey">{journey}</span>'
           f'<span class="wayfinder-question">{question}</span></p>',
           '        <ul class="wayfinder-steps">']

    if position > 0:
        _, href, j, q = ARC[position - 1]
        out.append(f'          <li class="wayfinder-prev"><span>Before this</span>'
                   f'<a href="{href}">{q}</a></li>')
    if position < len(ARC) - 1:
        _, href, j, q = ARC[position + 1]
        out.append(f'          <li class="wayfinder-next"><span>Next</span>'
                   f'<a href="{href}">{q}</a></li>')
    out.append(f'          <li class="wayfinder-source"><span>Where is the source?</span>'
               f'<a href="{GITHUB}" target="_blank" rel="noopener noreferrer">'
               f'The repository &#8599;</a></li>')
    out.append("        </ul>")
    out.append("      </nav>")
    out.append(f"      {END}")
    return "\n".join(out)


def _slot(html: str) -> tuple[int, int] | None:
    """Where the wayfinder goes: an existing block, or just before </main>."""
    if BEGIN in html and END in html:
        return html.index(BEGIN), html.index(END) + len(END)
    close = html.rfind("</main>")
    return (close, close) if close != -1 else None


def apply(check: bool) -> int:
    changed, missing = [], []
    for position, (path, *_rest) in enumerate(ARC):
        page = ROOT / path
        if not page.exists():
            missing.append(path)
            continue
        html = page.read_text(encoding="utf-8")
        slot = _slot(html)
        if slot is None:
            missing.append(f"{path} (no </main>)")
            continue
        start, finish = slot
        fresh = render(position)
        current = html[start:finish]
        if current == fresh:
            continue
        if check:
            changed.append(path)
            continue
        sep = "" if BEGIN in html else "\n"
        page.write_text(html[:start] + fresh + sep + html[finish:], encoding="utf-8")
        changed.append(path)

    if missing:
        print(f"WAYFINDER FAIL: cannot place on {missing}", file=sys.stderr)
        return 1
    if check:
        if changed:
            print("WAYFINDER FAIL: stale or absent on "
                  f"{changed}. Run scripts/add_journey_wayfinder.py.", file=sys.stderr)
            return 1
        print(f"WAYFINDER PASS: all {len(ARC)} destinations carry the current arc")
        return 0
    print(f"Wayfinder written to {len(changed)} of {len(ARC)} destinations"
          + (f": {changed}" if changed else " (all current)"))
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    raise SystemExit(apply(ap.parse_args().check))
