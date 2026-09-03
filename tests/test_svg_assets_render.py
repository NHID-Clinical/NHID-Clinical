"""Every published SVG must be well-formed XML.

SVG is XML, so a single malformed attribute is a fatal parse error: the browser
fetches the file, fails to decode it, and reports naturalWidth 0 while
`complete` stays true. Nothing errors. The <img> collapses to the height of its
alt text and the page looks like it was designed with a gap in it.

That shipped: assets/images/3d-svg/latency-split.svg carried
`filter="..." filter="..."` on one <g>, and the hero diagram on both
for-payers.html and shadow-evaluation-guide.html silently did not render.
Neither the link checker (the file existed) nor the visual capture (no
horizontal overflow) could see it.
"""
import xml.etree.ElementTree as ET
import os

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {"_site", "node_modules", ".git", "simulator"}


def svg_files():
    found = []
    for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        found += [
            os.path.relpath(os.path.join(dirpath, n), REPO_ROOT)
            for n in filenames if n.endswith(".svg")
        ]
    return sorted(found)


SYMBOL = "{http://www.w3.org/2000/svg}symbol"


def is_sprite_sheet(rel):
    """
    A hidden root holding <symbol> elements, pulled in by <use href="...#id">.
    Each symbol carries its own viewBox; the root deliberately has no size.
    """
    try:
        root = ET.parse(os.path.join(REPO_ROOT, rel)).getroot()
    except ET.ParseError:
        return False
    return root.find(f".//{SYMBOL}") is not None and "display:none" in (root.get("style") or "")


SVGS = svg_files()
# Sprite sheets are excluded from the size check rather than skipped inside it.
# A runtime skip would raise the suite's skip count, and that number is published
# as "integration tests not run without a live server" -- a sprite sheet is not
# one of those, and blurring the two makes the published figure mean less.
SIZED_SVGS = [s for s in SVGS if not is_sprite_sheet(s)]


def test_svg_assets_were_found():
    """A path change finding zero files would make the check below vacuous."""
    assert len(SVGS) >= 25, f"only {len(SVGS)} SVG assets found"


@pytest.mark.parametrize("rel", SVGS)
def test_svg_is_well_formed_xml(rel):
    try:
        ET.parse(os.path.join(REPO_ROOT, rel))
    except ET.ParseError as exc:
        pytest.fail(
            f"{rel} is not well-formed XML ({exc}). A browser will fetch it, fail to "
            f"decode it, and render nothing where the diagram should be."
        )


@pytest.mark.parametrize("rel", SIZED_SVGS)
def test_svg_declares_intrinsic_size(rel):
    """
    Without viewBox (or width+height) an <img> has no intrinsic ratio to lay out
    against, so it collapses or stretches depending on the surrounding CSS.

    Sprite sheets are excluded from this parametrisation -- see is_sprite_sheet.
    """
    root = ET.parse(os.path.join(REPO_ROOT, rel)).getroot()
    assert root.get("viewBox") or (root.get("width") and root.get("height")), (
        f"{rel} declares neither viewBox nor width+height"
    )
