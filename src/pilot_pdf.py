#!/usr/bin/env python3
"""
Markdown -> PDF, for the documents this project publishes
=========================================================
One markdown renderer, used by two callers: `nhid pilot` (the Tier 0 evidence
pack) and `scripts/build_playbook_pdf.py` (the Playbook). It supports the
markdown those documents actually use — headings, paragraphs, tables, fenced
code, blockquotes, lists, horizontal rules, and inline bold / italic / code /
links. It is not a general markdown implementation and does not pretend to be;
anything it does not recognise is emitted as body text rather than silently
dropped.

WHY A PDF AT ALL
----------------
The artifact that circulates inside a health plan is a PDF. A markdown file in
a terminal is not something a security reviewer forwards to their director, so
a pilot that ends at markdown ends one step short of being used.

WHY THE RENDERER LIVES HERE AND NOT IN scripts/
-----------------------------------------------
It was defined inside `scripts/build_playbook_pdf.py`, which is a script, not
an importable home for shared code. Two documents now need it, and two copies
of a markdown renderer drift. The house style it draws on (fonts, colours,
cover, footers) still lives in `scripts/generate_pdfs.py` and is imported from
there, unchanged.

NO SUBPROCESS, DELIBERATELY
---------------------------
`build_playbook_pdf.main()` shells out to `git rev-parse` for its version line.
Nothing here does, because this module is covered by
`scripts/check_offline_kit.py` and `subprocess` is on its forbidden list — a
module the Tier 0 kit imports must not be able to execute anything. Callers
pass their version line in as a string.

reportlab is an OPTIONAL dependency (`pip install 'nhid-clinical[pdf]'`).
Importing this module requires it, so callers import this module inside a
try/except and fall back to markdown rather than failing — see
`src/cli.py`. A kit that cannot render a PDF must still produce the report.

NHID-Clinical is a voluntary open proposal. This module is licensed
Apache-2.0 (see LICENSE).
"""

from __future__ import annotations

import html
import re

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from scripts.generate_pdfs import (  # the house style, unchanged
    AMBER, FONT_BOLD, FONT_MONO, FONT_REGULAR, INK, LGRAY, LOGO_LIGHT_PATH,
    LOGO_PATH, NAVY, SLATE, WHITE, _cover, _cover_footer, _footer_canvas,
    _styles,
)

PDF_EXTRA_HINT = (
    "PDF rendering needs reportlab, which is an optional extra so that a vendor "
    "embedding the policy engine in a call path does not inherit it. Install it "
    "with:  pip install 'nhid-clinical[pdf]'"
)

_INLINE_CODE = re.compile(r"`([^`]+)`")
# Non-greedy `.+?`, not `[^*]+`: the old pattern could not match a bold span
# containing an italic one, so `**bold with *italic* inside**` failed to match
# and the asterisks reached the page as literal text. The Playbook's own
# opening paragraph does this, and the published PDF showed `**` to readers.
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_ITALIC = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

# Private-use codepoint standing in for a markdown hard line break while a
# paragraph is inlined. Chosen so html.escape and the inline regexes above
# all pass over it; swapped for <br/> once inlining is done.
_HARD_BREAK = "\ue000"


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


def render(md: str, story: list, styles, avail: float, *,
           page_break_on_h1: bool = True) -> None:
    """Append `md` to a reportlab story.

    `page_break_on_h1` suits a long multi-chapter document like the Playbook,
    where every H1 opens a chapter. A short report has one H1 — its title —
    and breaking the page there would open the document on a blank sheet, so
    the pilot pack turns it off.
    """
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
    # (text, hard_break): markdown's two-trailing-spaces line break. Without
    # it a block of labelled fields — "Organization: …", "Workflow: …" — joins
    # into one run-on paragraph, which is exactly what the pilot report's
    # header block is made of.
    para: list[tuple[str, bool]] = []
    quoted: list[str] = []

    def flush_para():
        if para:
            # Join the whole paragraph BEFORE inlining, with a placeholder
            # where the hard breaks go. Inlining each line separately looks
            # equivalent and is not: `**a phrase spanning\ntwo lines**` then
            # presents the bold regex with two unmatched halves and the
            # asterisks survive into the PDF as literal text. The placeholder
            # is a private-use codepoint, so html.escape and every inline
            # regex pass over it untouched.
            joined = ""
            for idx, (text, hard) in enumerate(para):
                joined += text
                if idx < len(para) - 1:
                    joined += _HARD_BREAK if hard else " "
            story.append(
                Paragraph(inline(joined).replace(_HARD_BREAK, "<br/>").strip(), BODY))
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
                if page_break_on_h1:
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

        para.append((stripped, line.endswith("  ")))
        i += 1

    flush_para()
    flush_quote()


def render_markdown_pdf(
    md: str,
    out_path,
    *,
    title: str,
    subtitle: str = "",
    version: str = "",
    footer_note: str = "",
    author: str = "",
    cover_date: str = "",
    page_break_on_h1: bool = False,
) -> str:
    """Render markdown to a cover-paged PDF at `out_path`. Returns the path.

    `footer_note` is the provenance line on the cover. It is passed in rather
    than discovered, because discovering it would mean running `git`, and a
    module the offline kit imports must not be able to execute anything.
    """
    out_path = str(out_path)
    doc = SimpleDocTemplate(
        out_path, pagesize=letter,
        leftMargin=0.85 * inch, rightMargin=0.85 * inch,
        topMargin=0.7 * inch, bottomMargin=0.7 * inch,
        title=title, author=author or title,
    )
    avail = letter[0] - 1.7 * inch
    styles = _styles()
    story: list = []

    import os
    _cover(
        story, title, subtitle, version, footer_note,
        logo_path=LOGO_LIGHT_PATH if os.path.exists(LOGO_LIGHT_PATH) else LOGO_PATH,
        # A report generated today should not say it was released in the month
        # the PDF suite was. Passing nothing keeps the suite's own date.
        date=cover_date or None,
    )

    # The cover already carries the title, so drop a leading H1 from the body
    # rather than printing the document's name twice.
    body = md.split("\n", 1)[1] if md.startswith("# ") else md
    render(body, story, styles, avail, page_break_on_h1=page_break_on_h1)

    doc.build(story, onFirstPage=_cover_footer, onLaterPages=_footer_canvas)
    return out_path
