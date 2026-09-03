#!/usr/bin/env python3
"""Remove CSS rules whose selectors can never match anything the site builds.

  python scripts/visual/prune_unused_css.py --report   # list, change nothing
  python scripts/visual/prune_unused_css.py --apply

A class counts as USED if it appears in a class attribute anywhere in _site/,
or as an identifier in any script these stylesheets can reach. The second test
is deliberately broad: a class added at runtime by classList.add('is-open')
appears in no markup, and over-keeping is the safe direction. It is only sound
because nothing in that scope builds a class name by concatenation -- re-checked
on every run, and the tool refuses to prune if that stops being true.

"Can reach" means scripts on pages that actually link one of these stylesheets,
plus the shared site.js those pages load. Two places in the site are excluded by
that rule and would otherwise break it: the vendored React bundle under
_site/simulator/, and _site/assets/media/front-desk-walkthrough.html, a
self-contained page with its own styles. Both build class names by
concatenation. Neither loads these sheets, so neither can apply a class from
them; scanning them would trip the dynamic-name check and pin thousands of
unrelated identifiers as "used".

A selector is removed when every class it names is unused. Classes inside
:not() are ignored, since :not(.x) matches precisely when .x is absent. Using
"every" rather than "any" is the conservative choice: a selector like
`.dead .alive` can never match either, but leaving it costs only bytes, while
removing a live rule costs a broken page.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "_site"

# Sheets pruned here. assets/css/components.css is deliberately excluded: it is
# the vocabulary this redesign is being built with, and several of its classes
# (evidence-status-*, doc-shell, the surface-* set) are staged for pages not yet
# migrated. Unused there means "not yet", not "left over".
SHEETS = ["nhid-clinical-ui.css", "assets/css/premium.css"]

CLASS_IN_SELECTOR = re.compile(r"\.(-?[A-Za-z_][\w-]*)")
NOT_CLAUSE = re.compile(r":not\([^)]*\)")


def used_classes() -> set[str]:
    used: set[str] = set()
    scripts: list[str] = []
    governed = 0
    sheet_names = [Path(s).name for s in SHEETS]
    for p in SITE.rglob("*.html"):
        t = p.read_text(errors="replace")
        # class attributes are read from EVERY page, including ones that do not
        # load these sheets -- a page could start loading them tomorrow.
        for attr in re.findall(r'class\s*=\s*"([^"]*)"', t) + re.findall(r"class\s*=\s*'([^']*)'", t):
            used |= set(attr.split())
        if any(name in t for name in sheet_names):
            governed += 1
            scripts += re.findall(r"<script\b[^>]*>(.*?)</script\s*>", t, re.I | re.S)
            for m in re.findall(r'src\s*=\s*"(/[^"]*\.js)"', t):
                f = SITE / m.lstrip("/")
                if f.is_file():
                    scripts.append(f.read_text(errors="replace"))
    if governed < 30:
        raise SystemExit(f"FAIL: only {governed} pages load these sheets; expected the whole site")
    blob = "\n".join(scripts)
    if re.search(r"class(?:List|Name)[^;\n]*(?:\+|`)", blob):
        raise SystemExit(
            "FAIL: the site now builds a class name dynamically. A static scan "
            "cannot see those names; this tool is unsafe until that is handled."
        )
    return used | set(re.findall(r"[A-Za-z_][\w-]*", blob))


def selector_is_dead(selector: str, used: set[str]) -> bool:
    names = CLASS_IN_SELECTOR.findall(NOT_CLAUSE.sub("", selector))
    return bool(names) and all(n not in used for n in names)


def prune(text: str, used: set[str]) -> tuple[str, list[str]]:
    """Walk top-level rules, and rules one level inside @media/@supports."""
    out: list[str] = []
    removed: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        brace = text.find("{", i)
        if brace == -1:
            out.append(text[i:])
            break
        prelude = text[i:brace]
        # find the matching close brace
        depth = 0
        j = brace
        while j < n:
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        body = text[brace + 1:j]
        stripped = prelude.strip()
        at_rule = stripped.lstrip().startswith("@") or "@" in stripped.split("{")[0] and stripped.lstrip().startswith("@")

        if stripped.lstrip().startswith("@keyframes") or "@keyframes" in stripped:
            out.append(text[i:j + 1])
        elif stripped.lstrip().startswith("@"):
            inner, inner_removed = prune(body, used)
            removed += inner_removed
            if inner.strip():
                out.append(prelude + "{" + inner + "}")
            else:
                removed.append(stripped.strip() + " (emptied)")
            # keep any comment/whitespace that preceded the at-rule
        else:
            # Comments and whitespace before the selector must survive intact.
            # Split AFTER the last comment terminator, not after its first
            # character: "*/" is two bytes, and taking rfind("*/") + 1 leaves the
            # "/" on the selector side, so dropping the rule also drops it and
            # turns the comment above it into an unterminated one that swallows
            # the rest of the file. That shipped once and rendered as a 39px
            # header shift with the stylesheet still appearing to parse.
            close = prelude.rfind("*/")
            selector_start = max(prelude.rfind("}") + 1, close + 2 if close != -1 else 0)
            leading, selector = prelude[:selector_start], prelude[selector_start:]
            parts = [p for p in selector.split(",")]
            kept = [p for p in parts if not selector_is_dead(p, used)]
            if len(kept) == len(parts):
                out.append(text[i:j + 1])
            elif kept:
                removed += [p.strip() for p in parts if p not in kept]
                out.append(leading + ",".join(kept) + "{" + body + "}")
            else:
                removed += [p.strip() for p in parts]
                out.append(leading.rstrip(" ") if leading.strip() else "")
        i = j + 1
    return "".join(out), removed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    if not (args.apply or args.report):
        ap.error("pass --report or --apply")

    used = used_classes()
    total = 0
    for rel in SHEETS:
        p = ROOT / rel
        src = p.read_text()
        new, removed = prune(src, used)
        total += len(removed)
        saved = len(src) - len(new)
        print(f"{rel}: {len(removed)} selectors removed, {saved} bytes ({saved/len(src):.0%})")
        for r in removed[:200]:
            print(f"    {r}")
        if args.apply:
            # collapse the blank runs left where whole rules were dropped
            new = re.sub(r"\n{3,}", "\n\n", new)
            p.write_text(new)
    print(f"total selectors removed: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
