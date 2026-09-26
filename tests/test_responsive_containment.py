"""
Responsive containment — regression guards
==========================================
Four destinations scrolled horizontally at a 390px viewport before the Phase D
containment fixes: faq.html to 574px, sms-opt-in.html to 459px, developers.html
to 446px, evidence-pack.html to 417px.

A horizontal scrollbar on a phone is not a cosmetic defect. It is the symptom of
a box that refused to shrink, and the pages it appeared on were the ones a payer
operations reader reaches first.

These tests assert the *causes* rather than re-measuring in a browser, so they
run in CI without one. Each names the page it was found on.
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
UI_CSS = (ROOT / "nhid-clinical-ui.css").read_text(encoding="utf-8")
COMPONENTS_CSS = (ROOT / "assets" / "css" / "components.css").read_text(encoding="utf-8")


def _block(css: str, selector: str) -> str:
    """The declaration block for a selector, or '' if the selector is absent."""
    m = re.search(re.escape(selector) + r"[^{}]*\{([^}]*)\}", css)
    return m.group(1) if m else ""


# ── The checkbox that ate the row (sms-opt-in.html) ────────────────────────

def test_the_generic_input_rule_still_sets_full_width():
    """The fix below only matters while this rule exists; if it goes, so can they."""
    assert re.search(r"input,\s*select,\s*textarea\s*\{[^}]*width:\s*100%", UI_CSS), (
        "the generic input rule changed — re-check whether the checkbox override "
        "is still needed, and delete it if not"
    )


@pytest.mark.parametrize("selector", ['input[type="checkbox"]', 'input[type="radio"]'])
def test_checkboxes_and_radios_are_not_stretched_to_full_width(selector):
    """
    `input, select, textarea { width: 100% }` is right for a phone field and
    wrong for a checkbox. On sms-opt-in.html the consent checkbox computed to
    320px, and because it also carried `flex-shrink: 0` it consumed the whole
    flex row and left the label text zero width to overflow out of the page.
    """
    block = _block(UI_CSS, selector)
    assert block, f"{selector} has no rule; the generic 100% width applies again"
    assert re.search(r"width:\s*auto", block), f"{selector} must not inherit width: 100%"


# ── min-width: auto on flex and grid items ─────────────────────────────────

@pytest.mark.parametrize("selector,page", [
    (".faq-item", "faq.html"),
    (".consent-row", "sms-opt-in.html"),
    (".consent-copy", "sms-opt-in.html"),
])
def test_prose_containers_may_shrink_below_their_content(selector, page):
    """
    A flex or grid item defaults to `min-width: auto` and so refuses to shrink
    below the max-content width of the prose inside it. That is what made
    .faq-item render 564px wide inside a 390px viewport.
    """
    css = COMPONENTS_CSS if selector in COMPONENTS_CSS else UI_CSS
    block = _block(css, selector)
    assert block, f"{selector} is gone; {page} may overflow again"
    assert re.search(r"min-width:\s*0", block), (
        f"{selector} needs min-width: 0 or {page} cannot shrink to the viewport"
    )


# ── Long unbreakable tokens ────────────────────────────────────────────────

def test_inline_code_breaks_long_tokens():
    """
    developers.html carried an import line 603px wide and evidence-pack.html a
    407px file path. An unbreakable token is the one thing on the line that
    cannot wrap, so it is the one thing allowed to break.
    """
    assert re.search(r"(?<!pre )\bcode\s*\{[^}]*overflow-wrap:\s*anywhere", COMPONENTS_CSS)


def test_preformatted_blocks_still_scroll_rather_than_break():
    """
    A <pre> holds commands meant to be copied. Breaking those mid-token would
    corrupt them, so pre scrolls inside its own box instead.
    """
    assert re.search(r"pre\s+code\s*\{[^}]*overflow-wrap:\s*normal", COMPONENTS_CSS)


# ── The visually-hidden caption that sized a table ─────────────────────────

def test_a_visually_hidden_caption_does_not_size_its_table():
    """
    `position: absolute` does not take a <caption> out of table layout the way
    it does a <div>, so the 663px of nowrap caption text on evidence-pack.html
    set the table's minimum width. The caption stays in the accessibility tree.
    """
    block = _block(COMPONENTS_CSS, "caption.visually-hidden")
    assert block, "the caption override is gone; evidence-pack.html may overflow again"
    assert re.search(r"white-space:\s*normal", block)
    assert re.search(r"clip-path:\s*inset\(50%\)", block), (
        "the caption must stay hidden visually while remaining readable to a screen reader"
    )


# ── The markup that carried the bug ────────────────────────────────────────

def test_the_consent_row_uses_the_named_component():
    """
    The consent row was an inline `display:flex` with no containment on either
    the label or its text. Naming it moved the fix into the design system, where
    the next page to use a checkbox-plus-copy row inherits it.
    """
    page = (ROOT / "sms-opt-in.html").read_text(encoding="utf-8")
    assert 'class="consent-row"' in page
    assert 'class="consent-copy"' in page
    assert "display:flex;gap:.6rem;align-items:flex-start" not in page, (
        "the inline flex is back; the containment no longer travels with the component"
    )
