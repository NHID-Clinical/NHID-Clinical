# Playbook PDF build

Reproducible tooling that compiles the twenty playbook chapters into a single
print-ready PDF with a title page, front matter, table of contents, part
dividers, running headers, and page numbers.

> **The final PDF is intentionally gated.** The manuscript title/subtitle and
> Chapter 5 still carry the earlier "Trusted AI Voice Agents" framing (the
> deferred positioning-alignment pass). This tooling is committed and rehearsed
> now; a distributable PDF is **not** generated, committed, or published until
> that alignment lands. See the deferred-publish steps below.

## Layout

| File | Role |
| :-- | :-- |
| `build_pdf.py` | Chapters (`playbook/chapters/*.md`) → `playbook/dist/book.html` + `book.meta.json`. Holds the document-identity constants (title, subtitle, author, subject, keywords). |
| `render_pdf.py` | `book.html` → `playbook/dist/NHID-Clinical-Operational-Playbook.pdf`, then stamps PDF metadata from `book.meta.json`. |
| `validate_pdf.py` | Structural gate: page count, all 20 chapter titles, 5 part dividers, front matter/TOC, populated metadata, no blank pages. |
| `requirements.txt` | `markdown`, `playwright`, `pymupdf`. |

Output lands in `playbook/dist/`, which is git-ignored — nothing here commits a
PDF.

## Usage

```bash
pip install -r playbook/build/requirements.txt
make playbook-pdf        # build HTML + render PDF + stamp metadata
make playbook-validate   # structural + metadata checks
```

Or directly:

```bash
python playbook/build/build_pdf.py
python playbook/build/render_pdf.py
python playbook/build/validate_pdf.py
```

Chromium is resolved portably: Playwright's managed browser by default, else
`$CHROMIUM_PATH`, else a glob under `$PLAYWRIGHT_BROWSERS_PATH`.

## Licensing metadata

The build stamps the PDF's document properties (Title, Author, Subject,
Keywords, Creator) from a single source of truth in `build_pdf.py`, and the
artifact's front matter carries the full CC BY 4.0 notice and attribution
(© 2026 Brianna Nicole Baynard; public byline "Brianna Baynard";
NIST-2025-0035-0026 public-comment disclaimer).

## Deferred publish steps (do not run until the positioning pass lands)

1. Update the `SUBTITLE` constant in `build_pdf.py` (and the Chapter 5 framing);
   re-run `make playbook-pdf && make playbook-validate`.
2. Add a `.gitignore` exception `!specs/NHID-Clinical-Operational-Playbook.pdf`,
   copy the validated PDF to `specs/`, and commit it.
3. Add a `## [vX.Y] - YYYY-MM` entry to `CHANGELOG.md`.
4. *Optional (owner's choice):* add a download card to `specs/index.html`, and/or
   cut a git tag + GitHub Release with the PDF attached.

## Known cosmetic item (optional polish)

The running header currently repeats on the title page. Suppressing it on the
title/front-matter/TOC/part-divider pages would require a two-pass render
(front matter without header/footer) merged with PyMuPDF. Not required for the
gated phase; noted for the eventual final render.
