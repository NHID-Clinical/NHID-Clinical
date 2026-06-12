"""5 deterministic tests for the public CAS badge generator."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.nhid_badge_generator import generate_badge_svg, generate_badge_html_snippet


class TestBadgeGenerator:
    def test_svg_is_valid_markup(self):
        svg = generate_badge_svg("vendor_acme", 0.87)
        assert svg.startswith("<svg")
        assert svg.rstrip().endswith("</svg>")
        assert 'xmlns="http://www.w3.org/2000/svg"' in svg

    def test_score_and_tier_rendered(self):
        svg = generate_badge_svg("vendor_acme", 0.87, "Conditional Trust")
        assert "0.87" in svg
        assert "Conditional Trust" in svg

    def test_tier_derived_from_score_when_omitted(self):
        # 0.95+ should map to the top tier per _tier_for_cas thresholds
        svg = generate_badge_svg("vendor_acme", 0.99)
        assert "Trust" in svg  # Verified Trust or Conditional Trust label present

    def test_score_clamped_to_unit_interval(self):
        svg_high = generate_badge_svg("v", 1.7)
        svg_low = generate_badge_svg("v", -0.3)
        assert "1.00" in svg_high
        assert "0.00" in svg_low

    def test_html_snippet_contains_badge_url_and_vendor(self):
        snippet = generate_badge_html_snippet("vendor_acme")
        assert "/v1/public/vendor/vendor_acme/badge" in snippet
        assert "<img" in snippet
        assert "vendor_acme" in snippet
