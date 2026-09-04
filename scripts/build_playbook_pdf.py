#!/usr/bin/env python3
"""
Render the canonical Playbook to PDF from its markdown source.

The Playbook is written once, in `docs/NHID-Clinical-Playbook.md`. This renders
that file rather than restating it in reportlab calls, which is the whole point:
the other seven PDFs in `specs/` are built from Python literals, and that is
exactly how `NHID-Clinical-v1.3-Overview.pdf` came to claim "847 passing unit
tests" long after the suite had moved on four times. A generated document whose
prose lives only inside its generator cannot be diffed, reviewed, or corrected
by anyone reading the repository.

Supports the markdown the Playbook actually uses -- headings, paragraphs,
tables, fenced code, blockquotes, lists, horizontal rules, and inline bold /
italic / code / links. It is not a general markdown implementation and does not
pretend to be; anything it does not recognise is emitted as body text rather
than silently dropped.
"""
from __future__ import annotations

import html
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import (
    KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from generate_pdfs import (  # noqa: E402  reuse the house style
    AMBER, DGRAY, FONT_BOLD, FONT_DISPLAY, FONT_ITALIC, FONT_MONO, FONT_REGULAR,
    INK, LGRAY, LOGO_LIGHT_PATH, LOGO_PATH, NAVY, OUT_DIR, SLATE, TEAL_DEEP, WHITE,
    _cover, _cover_footer, _footer_canvas, _styles,
)
from reportlab.lib.styles import ParagraphStyle

SRC = os.path.join(os.path.dirname(__file__), "..", "docs", "NHID-Clinical-Playbook.md")
OUT = os.path.join(OUT_DIR, "NHID-Clinical-Playbook.pdf")

_INLINE_CODE = re.compile(r"`([^`]+)`")
_BOLD = re.compile(r"\*\*([^*]+)\*\*")
_ITALIC = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def inline(text: str) -> str:
    """Markdown inline formatting to reportlab markup, escaping first."""
    out = html.escape(text, quote=False)
    out = _INLINE_CODE.sub(
        lambda m: f'<font face="{FONT_MONO}" color="#0d7c86">{m.group(1)}</font>', out)
    out = _BOLD.sub(lambda m: f"<b>{m.group(1)}</b>", out)
    out = _ITALIC.sub(lambda m: f"<i>{m.group(1)}</i>", out)
    # Links render as their text: the destinations are repository-relative and
    # meaningless as clickable targets inside a downloaded PDF.
    out = _LINK.sub(lambda m: f"<b>{m.group(1)}</b>", out)
    return out


def split_row(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def build_table(rows: list[list[str]], body_style, avail: float) -> Table:
    header, *rest = rows
    cols = len(header)
    # Weight columns by the content they carry, so a narrow "#" column does not
    # get the same width as a paragraph of rationale.
    weights = []
    for i in range(cols):
        longest = max([len(header[i])] + [len(r[i]) if i < len(r) else 0 for r in rest])
        weights.append(max(longest, 6))
    total = sum(weights)
    # A column must be wider than its own padding. Weighting alone can drive a
    # narrow header like "#" below 10pt, at which point reportlab raises on a
    # negative available width. Give every column a floor, then take the
    # remainder back from the widest column so the row still fits the page.
    MIN_COL = 30.0
    widths = [max(MIN_COL, avail * w / total) for w in weights]
    overflow = sum(widths) - avail
    if overflow > 0:
        widest = widths.index(max(widths))
        widths[widest] = max(MIN_COL, widths[widest] - overflow)

    cell = ParagraphStyle("Cell", fontName=FONT_REGULAR, fontSize=7.4,
                          textColor=SLATE, leading=10.2)
    head = ParagraphStyle("CellHead", fontName=FONT_BOLD, fontSize=7.4,
                          textColor=WHITE, leading=10.2)

    data = [[Paragraph(inline(c), head) for c in header]]
    for r in rest:
        padded = (r + [""] * cols)[:cols]
        data.append([Paragraph(inline(c), cell) for c in padded])

    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dfe6ea")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LGRAY]),
    ]))
    return t


def render(md: str, story: list, styles, avail: float) -> None:
    H1, H2, BODY, SMALL, DISC = styles
    h3 = ParagraphStyle("H3", fontName=FONT_BOLD, fontSize=9.5, textColor=INK,
                        spaceBefore=8, spaceAfter=3)
    quote = ParagraphStyle("Quote", fontName=FONT_REGULAR, fontSize=8.2,
                           textColor=SLATE, leading=12, leftIndent=10,
                           borderColor=AMBER, borderWidth=0, backColor=colors.HexColor("#fffbf0"),
                           borderPadding=6, spaceBefore=4, spaceAfter=6)
    code = ParagraphStyle("Code", fontName=FONT_MONO, fontSize=7.2, textColor=INK,
                          leading=10, backColor=colors.HexColor("#f4f7f8"),
                          borderPadding=6, spaceBefore=4, spaceAfter=6)
    bullet = ParagraphStyle("Bullet", parent=BODY, leftIndent=12, bulletIndent=3,
                            spaceAfter=2)

    lines = md.split("\n")
    i = 0
    para: list[str] = []
    quoted: list[str] = []

    def flush_para():
        if para:
            story.append(Paragraph(inline(" ".join(para)), BODY))
            para.clear()

    def flush_quote():
        if quoted:
            story.append(Paragraph(inline(" ".join(quoted)), quote))
            quoted.clear()

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_para(); flush_quote()
            i += 1
            block = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                block.append(html.escape(lines[i], quote=False))
                i += 1
            story.append(Paragraph("<br/>".join(block).replace(" ", "&nbsp;"), code))
            i += 1
            continue

        if stripped.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|$", lines[i + 1].strip()):
            flush_para(); flush_quote()
            rows = [split_row(stripped)]
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(split_row(lines[i].strip()))
                i += 1
            story.append(Spacer(1, 0.04 * inch))
            story.append(build_table(rows, BODY, avail))
            story.append(Spacer(1, 0.08 * inch))
            continue

        if stripped.startswith(">"):
            flush_para()
            quoted.append(stripped.lstrip("> ").strip())
            i += 1
            continue
        flush_quote()

        if stripped.startswith("#"):
            flush_para()
            level = len(stripped) - len(stripped.lstrip("#"))
            text = stripped[level:].strip()
            if level == 1:
                story.append(PageBreak())
                story.append(Paragraph(inline(text), H1))
            elif level == 2:
                story.append(Spacer(1, 0.06 * inch))
                story.append(Paragraph(inline(text), H2))
            else:
                story.append(Paragraph(inline(text), h3))
            i += 1
            continue

        if stripped in ("---", "***", "___"):
            flush_para()
            story.append(Spacer(1, 0.10 * inch))
            i += 1
            continue

        m = re.match(r"^[-*]\s+(.*)", stripped) or re.match(r"^(?:\d+\.)\s+(.*)", stripped)
        if m:
            flush_para()
            story.append(Paragraph(inline(m.group(1)), bullet, bulletText="•"))
            i += 1
            continue

        if not stripped:
            flush_para()
            i += 1
            continue

        para.append(stripped)
        i += 1

    flush_para()
    flush_quote()


def main() -> int:
    with open(SRC, encoding="utf-8") as f:
        md = f.read()

    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                capture_output=True, text=True,
                                cwd=os.path.dirname(SRC)).stdout.strip() or "unknown"
    except Exception:  # noqa: BLE001
        commit = "unknown"

    doc = SimpleDocTemplate(OUT, pagesize=letter,
                            leftMargin=0.85 * inch, rightMargin=0.85 * inch,
                            topMargin=0.7 * inch, bottomMargin=0.7 * inch,
                            title="NHID-Clinical Playbook",
                            author="Brianna Baynard")
    avail = letter[0] - 1.7 * inch
    styles = _styles()
    story: list = []

    _cover(
        story,
        "NHID-Clinical Playbook",
        "Evaluation, Implementation, and Evidence Guide",
        "1.0",
        f"Framework v1.3  ·  source commit {commit}",
        logo_path=LOGO_LIGHT_PATH if os.path.exists(LOGO_LIGHT_PATH) else LOGO_PATH,
    )

    # The cover is rendered by _cover(); the body starts after the title block,
    # and every H1 opens a new page, so drop the front matter heading itself.
    body = md.split("\n", 1)[1] if md.startswith("# ") else md
    render(body, story, styles, avail)

    doc.build(story, onFirstPage=_cover_footer, onLaterPages=_footer_canvas)
    print(f"  ✓  {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
