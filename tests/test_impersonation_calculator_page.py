"""`impersonation-cost.html` stays a calculator of assumptions, not a claim.

The page is generated from `src/impersonation_cost.py` by
`scripts/build_impersonation_calculator.py`. These checks cover the two ways it
could go wrong between now and someone editing it in six months:

* **Drift.** The browser repeats the model's arithmetic in JavaScript. If the
  page is hand-edited, or the model changes and nobody rebuilds, the figures on
  screen stop being the figures the Python tests verify. The staleness check is
  the same device `scripts/seo/seo_head.py` and the fixture generators already
  use here.
* **Claim creep.** Every figure is a user-supplied assumption, and the project
  has measured none of them (`docs/claim-boundaries.md`: **Research** stage).
  The disclaimer has to be present verbatim, every output has to be marked
  illustrative, and the page must not acquire the vocabulary of savings,
  measurement or vendor comparison.

Cross-implementation agreement between the JavaScript and the Python was
checked by driving the built page in a browser against the model over several
input sets. That needs a browser, so it is not asserted here; the staleness
check is what keeps the verified pairing intact.
"""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "impersonation-cost.html"


def _generator():
    spec = importlib.util.spec_from_file_location(
        "build_impersonation_calculator",
        ROOT / "scripts" / "build_impersonation_calculator.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def page() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_the_committed_page_matches_a_fresh_render_of_the_model():
    """A hand-edit here, or a model change without a rebuild, fails this.

    Either would leave the page doing arithmetic that
    `tests/test_impersonation_cost.py` has not verified.
    """
    assert _generator().main(check=True) == 0, (
        "impersonation-cost.html no longer matches src/impersonation_cost.py "
        "(run python scripts/build_impersonation_calculator.py)")


def test_the_disclaimer_appears_verbatim(page):
    from src.impersonation_cost import DISCLAIMER
    assert page.count(DISCLAIMER) >= 1, "the page does not carry the disclaimer sentence"


def test_every_assumption_is_an_editable_input(page):
    """No figure is baked in: each of the four is a control the reader can change."""
    from src.impersonation_cost import INPUTS
    for field in INPUTS:
        pattern = rf'<input[^>]*\bid="in-{re.escape(field.name)}"'
        assert re.search(pattern, page), f"{field.name} is not an editable input"


def test_every_output_is_marked_illustrative(page):
    """An unlabelled number on this page would read as a finding."""
    from src.impersonation_cost import FIELDS
    for field in FIELDS:
        block = re.search(
            rf'<output id="out-{re.escape(field.name)}".*?</dd>', page, re.S)
        assert block, f"{field.name} has no output element"
        assert "illustrative, not measured" in block.group(0), (
            f"{field.name} is rendered without the illustrative label")


def test_the_page_says_what_it_is_not(page):
    """The three readings that would be wrong are refused on the page itself."""
    for phrase in ("It is not a saving.",
                   "It is not a measurement.",
                   "It does not compare vendors."):
        assert phrase in page, f"the page no longer states: {phrase}"


def test_the_page_claims_no_saving_measurement_or_ranking(page):
    """Vocabulary that would turn an assumption into a result.

    Checked on the reader-visible text only: the page's own "It is not a
    saving" headings and the generator's comments legitimately contain these
    words in order to rule them out.
    """
    text = re.sub(r"<script.*?</script>", " ", page, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    sentences = re.split(r"(?<=[.!?])\s+", text)
    negation = re.compile(
        r"\b(?:not|never|no|n't|does not|do not|without|rather than|instead of)\b", re.I)
    forbidden = ("saving", "savings", "roi", "return on investment",
                 "payback", "we measured", "measured on live traffic",
                 "vendor ranking", "best vendor")
    offenders = [
        (word, sentence.strip()[:120])
        for sentence in sentences
        for word in forbidden
        if word in sentence.lower() and not negation.search(sentence)
    ]
    assert not offenders, f"the page asserts {offenders}"


def test_the_placeholder_defaults_are_not_presented_as_estimates(page):
    assert "round placeholders" in page, (
        "the page no longer says its starting numbers are placeholders, so a "
        "reader could take them for figures the project stands behind")
