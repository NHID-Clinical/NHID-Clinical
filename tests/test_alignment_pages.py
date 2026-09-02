"""
NHID-Clinical Alignment Pages Tests (14 tests)
"""
import pytest, os
ALIGNMENT_PAGES=["alignment/stir-shaken.html","alignment/cms-0057-f.html","alignment/nist-ai-agent-standards.html","alignment/vendor-evidence-pack.html"]
REPO_ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def page_path(r): return os.path.join(REPO_ROOT,r)
def page_content(r):
    with open(page_path(r),encoding="utf-8") as f: return f.read()
@pytest.mark.parametrize("page",ALIGNMENT_PAGES)
def test_alignment_page_exists(page): assert os.path.exists(page_path(page)),f"Missing: {page}"
@pytest.mark.parametrize("page",ALIGNMENT_PAGES)
def test_alignment_page_has_disclaimer(page):
    c=page_content(page)
    assert "early-stage" in c or "not an accredited" in c or "open proposal" in c
@pytest.mark.parametrize("page",ALIGNMENT_PAGES)
def test_alignment_page_links_to_spec(page):
    c=page_content(page)
    assert "specification.html" in c or "nhid-clinical.org/spec" in c
def test_alignment_pages_link_to_nhid_controls_not_external_projects():
    """
    These pages used to end by sending the reader to the AI Governance Map, a
    separate project on its own deployment. NHID-Clinical's alignment pages
    should resolve into NHID-Clinical's own control text instead — a visitor
    reading about STIR/SHAKEN scope should land on the controls, not on another
    project's site.
    """
    for page in ALIGNMENT_PAGES:
        c = page_content(page)
        assert "specification.html" in c or "controls.html" in c, (
            f"{page} offers the reader no route into the NHID-Clinical controls"
        )


# ── External projects must stay out of the NHID-Clinical site ──────────────

def test_no_external_project_links_in_published_pages():
    """
    The AI Governance Map and the other formerly Vercel-hosted projects are
    separate projects with their own deployments. They were carried in the nav
    and footer of every page here, which made NHID-Clinical read as one of
    several loosely related tools rather than as a project in its own right.

    This guards the boundary: no published page links to those deployments, and
    nothing regenerates them. A link to a genuinely separate project may be
    added back deliberately, but not by a template that puts it on all 35 pages.
    """
    import pathlib
    root = pathlib.Path(__file__).resolve().parent.parent
    skip = {"_site", ".git", "node_modules", "docs", "vendor"}
    offenders = []
    for path in root.rglob("*.html"):
        if skip & set(path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if "ai-governance-map" in text or "vercel.app" in text:
            offenders.append(str(path.relative_to(root)))
    assert not offenders, (
        "external-project links found in published pages: " + ", ".join(sorted(offenders))
    )
