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
def test_alignment_route_still_resolves(page):
    """
    The four alignment routes were retired into regulatory-alignment.html by the
    Phase B consolidation (2026-09-05). They were 195 words across four routes,
    all four orphaned -- nothing on the site linked them -- and each was a stub
    that sent the reader onward rather than answering anything. That is content,
    not a destination.

    The files stay, as redirect stubs, so existing links and search results
    resolve instead of 404ing. These tests moved with the content: they used to
    assert each stub carried a disclaimer and a route into the controls, and
    they now assert the reader still arrives somewhere that does.
    """
    assert os.path.exists(page_path(page)), f"Missing: {page}"
    c = page_content(page)
    assert 'http-equiv="refresh"' in c, f"{page} should be a redirect stub"
    assert "/regulatory-alignment.html" in c, (
        f"{page} must send the reader to the page that now holds its content"
    )
    assert 'rel="canonical"' in c, f"{page} needs a canonical link for search"


def test_the_destination_carries_what_the_stubs_used_to():
    """
    What the retired stubs each asserted individually, the destination must now
    assert once: the honest-status disclaimer, and a route into the controls.
    Without this, retiring the stubs would have quietly dropped both.
    """
    c = page_content("regulatory-alignment.html")
    assert "early-stage" in c or "not an accredited" in c or "open proposal" in c, (
        "regulatory-alignment.html lost the disclaimer the alignment stubs carried"
    )
    assert "specification.html" in c, (
        "regulatory-alignment.html offers no route into the NHID-Clinical controls"
    )


def test_the_four_subjects_survived_the_merge():
    """
    Retiring a route must not retire its subject. Each stub's topic has to be
    findable on the destination, or the consolidation lost content.
    """
    c = page_content("regulatory-alignment.html").lower()
    for subject in ("stir/shaken", "cms-0057", "nist", "evidence pack"):
        assert subject in c, f"regulatory-alignment.html no longer covers {subject!r}"


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
