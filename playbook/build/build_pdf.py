#!/usr/bin/env python3
"""Compile the NHID-Clinical playbook chapters into a single print-ready HTML
document (playbook/dist/book.html).

Portable, reproducible build step: paths are derived relative to this file, so
the tool runs from any checkout. render_pdf.py turns the HTML into the PDF and
stamps document metadata; validate_pdf.py checks structure. See README.md.
"""

import json
import re
import html
from pathlib import Path

import markdown

# Repo root = playbook/build/build_pdf.py -> parents[2].
REPO = Path(__file__).resolve().parents[2]
CHAPTERS_DIR = REPO / "playbook" / "chapters"
OUT_DIR = REPO / "playbook" / "dist"
OUT_HTML = OUT_DIR / "book.html"
OUT_META = OUT_DIR / "book.meta.json"
OUT_PDF = OUT_DIR / "NHID-Clinical-Operational-Playbook.pdf"

# --- Document identity: single source of truth for the title page AND the PDF
# metadata (render_pdf.py reads OUT_META). ----------------------------------
BRAND = "NHID-Clinical"
# NOTE (deferred positioning pass): SUBTITLE still carries the earlier
# "Trusted AI Voice Agents" framing. Aligning it with the current positioning
# (docs/positioning.md) is a one-line change here plus the Chapter 5 revision;
# until that lands, the final PDF is intentionally held (see build/README.md).
SUBTITLE = "The Operational Playbook for Trusted AI Voice Agents in Healthcare"
DOC_TITLE = f"{BRAND}: {SUBTITLE}"
AUTHOR = "Brianna Baynard"  # public byline; legal holder is Brianna Nicole Baynard
SUBJECT = (
    "An operational AI-governance framework for disclosed non-human actors "
    "operating under delegated authority in healthcare interactions."
)
KEYWORDS = (
    "NHID-Clinical, operational AI governance, non-human actor identity, "
    "delegated authorization, disclosure, auditability, impersonation latency, "
    "conformance testing, FHIR AuditEvent, NHID-Auth, healthcare"
)
CREATOR = "NHID-Clinical playbook build (playbook/build)"

PARTS = [
    ("Part I", "The Problem", [1, 2, 3, 4]),
    ("Part II", "The Framework", [5, 6, 7, 8]),
    ("Part III", "Implementation", [9, 10, 11, 12, 13]),
    ("Part IV", "Enterprise Adoption", [14, 15, 16, 17]),
    ("Part V", "The Future", [18, 19, 20]),
]

CHAPTER_FILES = sorted(CHAPTERS_DIR.glob("chapter-*.md"))
assert len(CHAPTER_FILES) == 20, f"expected 20 chapters, found {len(CHAPTER_FILES)}"

MD_EXTENSIONS = ["tables", "sane_lists", "fenced_code", "nl2br", "toc"]


def part_for_chapter(n):
    for label, title, nums in PARTS:
        if n in nums:
            return label, title
    raise KeyError(n)


def load_chapter(path):
    text = path.read_text(encoding="utf-8")
    # Pull the H1 title line, e.g. "# Chapter 1 — My Story: ..."
    m = re.search(r"^# (Chapter \d+ — .+)$", text, re.MULTILINE)
    title = m.group(1) if m else path.stem
    num = int(re.search(r"chapter-(\d+)", path.stem).group(1))
    # Strip the H1 and the "*Part X: ...*" line and the following "---" —
    # we render our own chapter-opener markup instead.
    text = re.sub(r"^# Chapter \d+ — .+\n", "", text, count=1, flags=re.MULTILINE)
    text = re.sub(r"^\*Part [IVX]+: [^*]+\*\n", "", text, count=1, flags=re.MULTILINE)
    text = re.sub(r"^\n---\n", "", text, count=1, flags=re.MULTILINE)
    return num, title, text.strip()


def md_to_html(text):
    return markdown.markdown(text, extensions=MD_EXTENSIONS)


def build_toc_entries(chapters):
    entries = []
    for label, title, nums in PARTS:
        entries.append(("part", label, title))
        for n in nums:
            ch_title = chapters[n]["title"]
            # "Chapter 1 — My Story: ..." -> split number/title for TOC columns
            m = re.match(r"Chapter (\d+) — (.+)", ch_title)
            entries.append(("chapter", m.group(1), m.group(2)))
    return entries


def main():
    chapters = {}
    for path in CHAPTER_FILES:
        num, title, body_md = load_chapter(path)
        chapters[num] = {
            "title": title,
            "html": md_to_html(body_md),
        }

    toc_entries = build_toc_entries(chapters)
    toc_html_parts = []
    for kind, a, b in toc_entries:
        if kind == "part":
            toc_html_parts.append(
                f'<div class="toc-part">{html.escape(a)} — {html.escape(b)}</div>'
            )
        else:
            toc_html_parts.append(
                f'<div class="toc-chapter"><span class="toc-num">Chapter {a}</span>'
                f'<span class="toc-dots"></span><span class="toc-title">{html.escape(b)}</span></div>'
            )
    toc_html = "\n".join(toc_html_parts)

    body_sections = []
    current_part = None
    for label, title, nums in PARTS:
        part_num_word = label.split()[1]
        body_sections.append(f"""
        <section class="part-divider">
          <div class="part-divider-inner">
            <div class="part-kicker">{html.escape(label)}</div>
            <div class="part-title">{html.escape(title)}</div>
          </div>
        </section>
        """)
        for n in nums:
            ch = chapters[n]
            m = re.match(r"Chapter (\d+) — (.+)", ch["title"])
            ch_num, ch_title = m.group(1), m.group(2)
            body_sections.append(f"""
            <section class="chapter" id="chapter-{ch_num}">
              <div class="chapter-kicker">{html.escape(label)}: {html.escape(title)}</div>
              <div class="chapter-number">Chapter {ch_num}</div>
              <h1 class="chapter-title">{html.escape(ch_title)}</h1>
              <div class="chapter-body">
                {ch["html"]}
              </div>
            </section>
            """)

    body_html = "\n".join(body_sections)

    full_html = HTML_TEMPLATE.format(
        doc_title=html.escape(DOC_TITLE),
        brand=html.escape(BRAND),
        subtitle=html.escape(SUBTITLE),
        author=html.escape(AUTHOR),
        toc=toc_html,
        body=body_html,
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(full_html, encoding="utf-8")

    # Sidecar metadata: single source of truth consumed by render_pdf.py so the
    # PDF's document properties match the title page exactly.
    OUT_META.write_text(
        json.dumps(
            {
                "title": DOC_TITLE,
                "author": AUTHOR,
                "subject": SUBJECT,
                "keywords": KEYWORDS,
                "creator": CREATOR,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Wrote {OUT_HTML} ({len(full_html):,} bytes)")
    print(f"Wrote {OUT_META}")


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{doc_title}</title>
<style>
@page {{
  size: 6.25in 9.25in;
  margin: 0.85in 0.75in 0.9in 0.75in;
}}

:root {{
  --ink: #1a1d23;
  --ink-soft: #4a5160;
  --rule: #c9cdd6;
  --accent: #0b6ebc;
  --accent-dark: #0a4f87;
  --paper: #ffffff;
  --tint: #f4f6f8;
  --serif: Georgia, 'Times New Roman', Times, serif;
  --sans: 'Helvetica Neue', Arial, 'Segoe UI', sans-serif;
  --mono: 'Menlo', 'Consolas', monospace;
}}

* {{ box-sizing: border-box; }}

html, body {{
  margin: 0;
  padding: 0;
  background: var(--paper);
  color: var(--ink);
  font-family: var(--serif);
  font-size: 10.6pt;
  line-height: 1.52;
  -webkit-font-smoothing: antialiased;
}}

/* ---------- Title page ---------- */

.titlepage {{
  height: 7.15in;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: flex-start;
  page-break-after: always;
  break-after: page;
}}
.titlepage .kicker {{
  font-family: var(--sans);
  letter-spacing: 0.18em;
  text-transform: uppercase;
  font-size: 9.5pt;
  color: var(--accent);
  font-weight: 600;
  margin-bottom: 0.55in;
}}
.titlepage h1 {{
  font-family: var(--serif);
  font-size: 30pt;
  line-height: 1.16;
  margin: 0 0 0.28in 0;
  font-weight: 700;
  color: var(--ink);
  max-width: 5.1in;
}}
.titlepage .subtitle {{
  font-family: var(--serif);
  font-style: italic;
  font-size: 13.5pt;
  color: var(--ink-soft);
  max-width: 4.6in;
  line-height: 1.4;
  margin-bottom: 0.65in;
}}
.titlepage .meta {{
  font-family: var(--sans);
  font-size: 9pt;
  color: var(--ink-soft);
  border-top: 1pt solid var(--rule);
  padding-top: 0.18in;
  width: 3.4in;
  line-height: 1.6;
}}
.titlepage .meta strong {{ color: var(--ink); }}

/* ---------- Front-matter / notice page ---------- */

.frontmatter {{
  page-break-after: always;
  break-after: page;
  padding-top: 0.4in;
}}
.frontmatter h2 {{
  font-family: var(--sans);
  font-size: 11pt;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--accent-dark);
  border-bottom: 1pt solid var(--rule);
  padding-bottom: 0.08in;
  margin: 0.3in 0 0.14in 0;
}}
.frontmatter h2:first-child {{ margin-top: 0; }}
.frontmatter p {{
  font-size: 9.6pt;
  color: var(--ink-soft);
  line-height: 1.55;
  margin: 0 0 0.13in 0;
}}
.frontmatter p.lead {{
  color: var(--ink);
  font-size: 10.2pt;
}}
.frontmatter ul {{
  font-size: 9.4pt;
  color: var(--ink-soft);
  margin: 0 0 0.15in 0;
  padding-left: 0.2in;
}}
.frontmatter li {{ margin-bottom: 0.05in; }}

/* ---------- Table of contents ---------- */

.toc-page {{
  page-break-after: always;
  break-after: page;
  padding-top: 0.4in;
}}
.toc-page h2 {{
  font-family: var(--sans);
  font-size: 20pt;
  font-weight: 700;
  margin: 0 0 0.35in 0;
  color: var(--ink);
}}
.toc-part {{
  font-family: var(--sans);
  font-size: 9.5pt;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--accent);
  margin: 0.24in 0 0.08in 0;
}}
.toc-part:first-child {{ margin-top: 0; }}
.toc-chapter {{
  display: flex;
  align-items: baseline;
  font-size: 10pt;
  margin: 0.045in 0;
  color: var(--ink);
}}
.toc-num {{
  font-family: var(--sans);
  font-weight: 600;
  color: var(--ink-soft);
  min-width: 1.05in;
  flex-shrink: 0;
}}
.toc-dots {{
  flex: 1;
  border-bottom: 1pt dotted var(--rule);
  margin: 0 0.08in;
  transform: translateY(-0.03in);
}}
.toc-title {{ flex-shrink: 0; }}

/* ---------- Part dividers ---------- */

.part-divider {{
  height: 7.15in;
  display: flex;
  align-items: center;
  justify-content: center;
  page-break-before: always;
  break-before: page;
  page-break-after: always;
  break-after: page;
}}
.part-divider-inner {{
  text-align: center;
}}
.part-kicker {{
  font-family: var(--sans);
  font-size: 11pt;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--accent);
  font-weight: 700;
  margin-bottom: 0.2in;
}}
.part-title {{
  font-family: var(--serif);
  font-size: 26pt;
  font-weight: 700;
  color: var(--ink);
}}

/* ---------- Chapters ---------- */

.chapter {{
  page-break-before: always;
  break-before: page;
  padding-top: 0.15in;
}}
.chapter-kicker {{
  font-family: var(--sans);
  font-size: 8.3pt;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--accent);
  font-weight: 600;
  margin-bottom: 0.12in;
}}
.chapter-number {{
  font-family: var(--sans);
  font-size: 10.5pt;
  font-weight: 700;
  color: var(--ink-soft);
  letter-spacing: 0.04em;
}}
.chapter-title {{
  font-family: var(--serif);
  font-size: 22pt;
  font-weight: 700;
  line-height: 1.18;
  color: var(--ink);
  margin: 0.03in 0 0.3in 0;
  border-bottom: 1.5pt solid var(--ink);
  padding-bottom: 0.16in;
}}

.chapter-body h2 {{
  font-family: var(--sans);
  font-size: 13pt;
  font-weight: 700;
  color: var(--accent-dark);
  margin: 0.32in 0 0.12in 0;
  page-break-after: avoid;
}}
.chapter-body h3 {{
  font-family: var(--sans);
  font-size: 11pt;
  font-weight: 700;
  color: var(--ink);
  margin: 0.22in 0 0.08in 0;
  page-break-after: avoid;
}}
.chapter-body p {{
  margin: 0 0 0.11in 0;
  text-align: justify;
  hyphens: auto;
  orphans: 3;
  widows: 3;
}}
.chapter-body p em:first-child {{
  color: var(--ink-soft);
}}
.chapter-body ul, .chapter-body ol {{
  margin: 0 0 0.14in 0;
  padding-left: 0.28in;
}}
.chapter-body li {{
  margin-bottom: 0.06in;
  text-align: justify;
}}
.chapter-body li p {{ margin: 0; }}
.chapter-body strong {{ color: var(--ink); }}
.chapter-body hr {{
  border: none;
  border-top: 0.75pt solid var(--rule);
  margin: 0.22in 0;
}}
.chapter-body blockquote {{
  margin: 0.15in 0;
  padding: 0.05in 0 0.05in 0.18in;
  border-left: 2pt solid var(--accent);
  color: var(--ink-soft);
  font-style: italic;
}}
.chapter-body code {{
  font-family: var(--mono);
  font-size: 8.6pt;
  background: var(--tint);
  padding: 0.01in 0.03in;
  border-radius: 2pt;
}}
.chapter-body pre {{
  background: var(--tint);
  padding: 0.1in;
  border-radius: 3pt;
  font-size: 8.2pt;
  overflow-x: auto;
  page-break-inside: avoid;
}}
.chapter-body pre code {{ background: none; padding: 0; }}

.chapter-body table {{
  border-collapse: collapse;
  width: 100%;
  margin: 0.14in 0 0.2in 0;
  font-size: 9pt;
  page-break-inside: avoid;
}}
.chapter-body th {{
  font-family: var(--sans);
  font-weight: 700;
  text-align: left;
  background: var(--tint);
  border-bottom: 1.25pt solid var(--ink-soft);
  padding: 0.06in 0.08in;
}}
.chapter-body td {{
  border-bottom: 0.5pt solid var(--rule);
  padding: 0.055in 0.08in;
  vertical-align: top;
  text-align: left;
}}
.chapter-body tr:last-child td {{ border-bottom: none; }}

.chapter-body p:last-of-type em {{
  color: var(--ink-soft);
}}
</style>
</head>
<body>

<div class="titlepage">
  <div class="kicker">The Operational Playbook</div>
  <h1>{brand}</h1>
  <div class="subtitle">{subtitle}</div>
  <div class="meta">
    Grounded in the NHID-Clinical v1.3 specification and reference implementation<br>
    <strong>Draft manuscript</strong> &middot; compiled from <code>playbook/</code><br>
    Twenty chapters &middot; Five parts &middot; Editorial reviews completed<br>
    {author} &middot; CC BY 4.0 &middot; nhid-clinical.org
  </div>
</div>

<div class="frontmatter">
  <h2>About this manuscript</h2>
  <p class="lead">This is a working draft, compiled directly from the chapter files
  in the NHID-Clinical repository's <code>playbook/</code> directory. It is an
  operational guide &mdash; not a specification, standards document, or research
  paper &mdash; explaining why NHID-Clinical exists, the operational problem it
  solves, and how healthcare organizations can implement it.</p>
  <p>NHID-Clinical itself is a <strong>voluntary, open framework</strong> &mdash;
  not an accredited standard, certification, or regulatory requirement. Claims
  about its maturity, test counts, and API status reflect a snapshot at the time
  of writing; consult the project's current materials before relying on any
  specific figure.</p>
  <h2>How to read the evidence in this book</h2>
  <p>Scenarios and examples fall into a few classes: those directly supported by
  the framework's reference materials and measured data; composite illustrations
  constructed to make a mechanism concrete; and anticipated dynamics reasoned
  from the framework's structure but not yet observed at scale. Chapters mark
  constructed scenarios explicitly where they appear. Nothing in this manuscript
  should be read as a reported industry statistic unless it is attributed to a
  specific repository artifact.</p>
  <h2>Not legal or regulatory advice</h2>
  <p>This manuscript describes operational practice. It is not legal advice, and
  nothing in it should be read as a determination of how any law, regulation, or
  contractual obligation applies to a specific organization&rsquo;s data flows.
  Consult qualified counsel for those determinations.</p>
  <h2>Licensing and attribution</h2>
  <p>&copy; 2026 Brianna Nicole Baynard. Licensed under the Creative Commons
  Attribution 4.0 International License (CC BY 4.0). You are free to share and
  adapt this material for any purpose, provided you give appropriate credit.
  Submitted as public comment to NIST (NIST-2025-0035-0026) &mdash; a public
  comment, not a NIST endorsement, adoption, or certification.</p>
</div>

<div class="toc-page">
  <h2>Contents</h2>
  {toc}
</div>

{body}

</body>
</html>
"""

if __name__ == "__main__":
    main()
