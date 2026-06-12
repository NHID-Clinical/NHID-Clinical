"""
NHID-Clinical – Public CAS Badge Generator
============================================
Generates embeddable SVG badges showing a vendor's NHID-CAS compliance
tier, plus copy-paste HTML embed snippets.

The badge is shields.io-style: a grey label segment ("NHID-CAS") and a
colored value segment showing the score and tier.

Usage:
  from src.nhid_badge_generator import generate_badge_svg, generate_badge_html_snippet
  svg = generate_badge_svg("vendor_acme", 0.87, "Conditional Trust")
  snippet = generate_badge_html_snippet("vendor_acme")

NHID-Clinical is a voluntary open proposal. CC BY 4.0.
Not an accredited standard. Not a regulatory requirement.
"""

from __future__ import annotations

from src.nhid_cas import _tier_for_cas

# Badge value-segment color per tier
_TIER_COLORS = {
    "Verified Trust": "#2da44e",       # green
    "Conditional Trust": "#0b6ebc",    # blue
    "Review Required": "#d4a72c",      # amber
    "Denied / Degraded": "#cf222e",    # red
}
_DEFAULT_COLOR = "#6e7781"  # grey for unknown / no data

_API_BASE = "https://dc2ipcqs7k.execute-api.us-east-2.amazonaws.com/prod"


def generate_badge_svg(vendor_id: str, score: float, tier: str | None = None) -> str:
    """
    Render an embeddable SVG badge for a vendor's CAS score.

    Args:
        vendor_id: Public vendor identifier (rendered in the SVG title).
        score: CAS score in [0, 1].
        tier: Tier label; derived from score via _tier_for_cas when omitted.

    Returns:
        SVG markup as a string.
    """
    score = max(0.0, min(1.0, float(score)))
    if tier is None:
        tier, _ = _tier_for_cas(score)

    color = _TIER_COLORS.get(tier, _DEFAULT_COLOR)
    label = "NHID-CAS"
    value = f"{score:.2f} · {tier}"

    # Approximate text widths (6.5px per char + padding) — keeps the SVG
    # dependency-free; exact kerning is not required for a badge.
    label_w = int(len(label) * 6.5) + 20
    value_w = int(len(value) * 6.5) + 20
    total_w = label_w + value_w

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{total_w}" height="20" role="img" aria-label="{label}: {value}">
  <title>{vendor_id} — {label}: {value}</title>
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="r"><rect width="{total_w}" height="20" rx="3" fill="#fff"/></clipPath>
  <g clip-path="url(#r)">
    <rect width="{label_w}" height="20" fill="#555"/>
    <rect x="{label_w}" width="{value_w}" height="20" fill="{color}"/>
    <rect width="{total_w}" height="20" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11">
    <text x="{label_w / 2}" y="14">{label}</text>
    <text x="{label_w + value_w / 2}" y="14">{value}</text>
  </g>
</svg>"""


def generate_badge_html_snippet(vendor_id: str) -> str:
    """Return a copy-paste HTML embed snippet pointing at the live badge endpoint."""
    badge_url = f"{_API_BASE}/v1/public/vendor/{vendor_id}/badge"
    return (
        f'<a href="https://nhid-clinical.org" title="NHID-Clinical CAS badge">\n'
        f'  <img src="{badge_url}" alt="NHID-CAS compliance badge for {vendor_id}" />\n'
        f"</a>"
    )
