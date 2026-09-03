# Visual regression capture

Screenshots representative pages at mobile / tablet / desktop and reports any
horizontal overflow. Built for the CSS consolidation work, where changes are
easy to make and hard to verify by reading.

## Running it

    bash scripts/build_pages_site.sh
    (cd _site && python3 -m http.server 8899 &)
    python3 scripts/visual/capture_pages.py /tmp/shots-before

Then make the change, rebuild, and capture to a second directory to compare.

## Two things that will mislead you if you skip them

**Serve over HTTP.** The pages link stylesheets by absolute path
(`/assets/css/...`). Opened as `file://`, those resolve to the filesystem root,
fail silently, and the browser renders an unstyled page. Measured that way the
homepage reports a 634px-wide body in a 390px viewport — a layout bug that does
not exist. The script asserts the site stylesheet actually parsed (`css=yes`)
before trusting any measurement, and that assertion is the point.

**External requests are aborted.** This environment has no egress, so webfonts
and analytics would hang the load. Faces fall back to system fonts, so these
shots verify layout, spacing, colour and overflow — not typographic fidelity.

## Requirements

Chromium is pre-installed at `/opt/pw-browsers/chromium-1194`. The script points
at it directly because the pip `playwright` package expects a newer build than
the one present; do not run `playwright install`.
