"""
NHID-Clinical site navigation regression guards.

Below the nav breakpoint the whole site's navigation is the drawer: the header
links are hidden and the hamburger is the only way to reach anything. That makes
the binding between three files load-bearing and easy to break silently --
`site.js` looks the button up by class, `nhid-clinical-ui.css` shows it by the
same class, and every page has to render it. Renaming the button in the markup
(which is exactly what happened, and shipped) leaves a button that renders,
reports `aria-expanded="false"`, and does nothing at all.

Static checks by design: they read the selector out of `site.js` rather than
restating it, so drift on either side of the binding fails here rather than in
a browser nobody ran.
"""
import os
import re

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {"_site", "node_modules", ".git", "simulator", "webplatform"}


def read(rel):
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as f:
        return f.read()


def published_pages():
    """Every published page that ships the drawer markup."""
    found = []
    for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for name in filenames:
            if not name.endswith(".html"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, name), REPO_ROOT)
            if 'id="mobile-nav"' in read(rel):
                found.append(rel)
    return sorted(found)


PAGES = published_pages()


def drawer_button_selector():
    """The class `site.js` binds the drawer toggle to, read from the source."""
    m = re.search(r"menuBtn\s*=\s*document\.querySelector\(\s*['\"]\.([\w-]+)['\"]", read("site.js"))
    assert m, "site.js no longer looks the drawer toggle up by class; update this guard"
    return m.group(1)


def test_pages_with_a_drawer_were_found():
    """A path change that finds zero pages would make every check below vacuous."""
    assert len(PAGES) >= 30, f"only {len(PAGES)} pages carry the drawer markup"


@pytest.mark.parametrize("page", PAGES)
def test_drawer_toggle_uses_the_class_site_js_binds_to(page):
    cls = drawer_button_selector()
    content = read(page)
    assert re.search(rf'<button[^>]*class="[^"]*\b{re.escape(cls)}\b', content), (
        f'{page} renders no button with class "{cls}", so site.js binds no click '
        f"handler and the drawer cannot be opened below the nav breakpoint"
    )


@pytest.mark.parametrize("page", PAGES)
def test_drawer_toggle_points_at_the_drawer_it_opens(page):
    """aria-controls is how a screen-reader user is told the button opens the drawer."""
    content = read(page)
    m = re.search(r"<button[^>]*\bmenu-button\b[^>]*>", content)
    assert m, f"{page} has no drawer toggle"
    assert 'aria-controls="mobile-nav"' in m.group(0), (
        f"{page}: the drawer toggle does not name the element it controls"
    )
    assert 'aria-expanded=' in m.group(0), (
        f"{page}: the drawer toggle has no aria-expanded state for site.js to update"
    )


def test_the_stylesheet_reveals_the_toggle_below_the_nav_breakpoint():
    """
    The button is hidden by default and revealed inside the nav breakpoint. If the
    two ever disagree the site loses its navigation on every narrow viewport.
    """
    css = read("nhid-clinical-ui.css")
    cls = drawer_button_selector()
    block = re.search(
        r"@media \(max-width: 1240px\) \{(.*?)\n\}", css, re.S
    )
    assert block, "the nav breakpoint block is gone from nhid-clinical-ui.css"
    body = block.group(1)
    assert re.search(rf"\.{re.escape(cls)}\s*\{{[^}}]*display:\s*inline-flex", body), (
        f".{cls} is not revealed inside the nav breakpoint"
    )
    assert re.search(r"\.nav-links\s*\{[^}]*display:\s*none", body), (
        ".nav-links is not hidden inside the nav breakpoint"
    )


def test_narrow_viewport_rule_keeps_the_toggle_visible():
    """
    The phone tier hides the optional icon buttons. It must keep excluding the
    drawer toggle -- otherwise a phone visitor sees a header with no links and
    no way to open the drawer, which is what shipped.
    """
    css = read("nhid-clinical-ui.css")
    cls = drawer_button_selector()
    assert f".icon-button:not(.{cls})" in css, (
        f"the phone-tier icon-button rule no longer spares .{cls}"
    )


# ── The retired visual-system prefix must not come back ────────────────────

def test_no_ctl_prefix_survives_in_published_css_or_markup():
    """
    `ctl-` stood for a visual language that is no longer the site's identity.
    The classes, the tokens and the stylesheet filename were renamed to say what
    they are instead. A stray `ctl-` reintroduced by a copied snippet would
    reference a selector that no longer exists -- silently unstyled, since CSS
    has no error for an unmatched class.
    """
    offenders = []
    for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for name in filenames:
            if not name.endswith((".html", ".css", ".js")):
                continue
            rel = os.path.relpath(os.path.join(dirpath, name), REPO_ROOT)
            for i, line in enumerate(read(rel).splitlines(), 1):
                if re.search(r"(?<![\w-])--?ctl-[a-z0-9-]", line) or "cinematic-trust-lattice.css" in line:
                    offenders.append(f"{rel}:{i}")
    assert not offenders, (
        "the retired ctl-/cinematic-trust-lattice naming reappeared in: "
        + ", ".join(offenders[:10])
    )


# ── Stylesheets must be structurally intact ────────────────────────────────

@pytest.mark.parametrize("sheet", [
    "nhid-clinical-ui.css", "assets/css/premium.css", "assets/css/components.css",
])
def test_stylesheet_is_structurally_intact(sheet):
    """
    Balanced braces, no empty declarations, and -- the one that matters --
    balanced comment delimiters.

    An unterminated `/*` comments out every rule after it until the next `*/`,
    and nothing else notices: the browser reports no error, and a brace-counting
    check passes because the stripper's `/\\*.*?\\*/` happily matches across to a
    later terminator. scripts/visual/prune_unused_css.py shipped exactly that
    once, by splitting a rule's prelude one byte inside `*/` and leaving the `*`
    behind. It rendered as a 39px header shift on every page.
    """
    src = read(sheet)
    assert src.count("/*") == src.count("*/"), (
        f"{sheet}: {src.count('/*')} comment openers vs {src.count('*/')} closers "
        f"-- an unterminated comment silently disables every rule that follows it"
    )
    body = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    depth = low = 0
    for ch in body:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            low = min(low, depth)
    assert depth == 0 and low == 0, f"{sheet}: unbalanced braces (final {depth}, min {low})"
    assert not re.findall(r"[\w-]+\s*:\s*;", body), f"{sheet}: empty declaration"
    assert not re.findall(r",\s*\{", body), f"{sheet}: selector list ends in a dangling comma"
