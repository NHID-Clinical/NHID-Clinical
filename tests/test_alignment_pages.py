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
def test_stir_shaken_has_governance_map_link():
    assert "ai-governance-map" in page_content("alignment/stir-shaken.html") or "governance-map" in page_content("alignment/stir-shaken.html")
def test_nist_page_has_governance_map_link():
    assert "ai-governance-map" in page_content("alignment/nist-ai-agent-standards.html") or "governance-map" in page_content("alignment/nist-ai-agent-standards.html")
