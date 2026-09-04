#!/usr/bin/env bash
# Assemble a slim GitHub Pages artifact — static site files only, no Python/tests/fixtures.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/_site"

rm -rf "$OUT"
mkdir -p "$OUT"

copy_tree() {
  local src="$1"
  local dest="$2"
  shift 2
  if [[ ! -d "$src" ]]; then
    return 0
  fi
  mkdir -p "$dest"
  rsync -a "$@" "$src/" "$dest/"
}

# Root pages + shared assets
#
# Retired from the site. Everything here stays in the repository and in git
# history; it is simply no longer published, and every route gets a redirect
# (see scripts/ia/redirects.txt) so inbound links do not 404.
#
#   simulator.html, docs.html  a side demonstration that competed with the
#                              framework for attention, and a Swagger page whose
#                              bundle loads from a CDN and renders nothing when
#                              that fails.
#   the rest                   merged into canonical destinations by the IA
#                              consolidation (docs/ia-disposition.md Part 4).
#                              Their content moved; only the routes are gone.
RETIRED_PAGES=(
  simulator.html docs.html
  about.html technical-stack.html
  for-payers.html script-examples.html demo.html
  interoperability.html registry.html
  roadmap.html news.html community.html
  identity-layer.html implementation-review.html
  gov-sim.html svg-preview.html pilot.html conformance.html
)

shopt -s nullglob
for f in "$ROOT"/*.html; do
  skip=""
  for r in "${RETIRED_PAGES[@]}"; do
    [[ "$(basename "$f")" == "$r" ]] && skip=1
  done
  [[ -n "$skip" ]] && continue
  cp "$f" "$OUT/"
done
shopt -u nullglob

for f in site.js nhid-clinical-ui.css CNAME .nojekyll robots.txt sitemap.xml feed.xml; do
  if [[ -f "$ROOT/$f" ]]; then
    cp "$ROOT/$f" "$OUT/"
  fi
done

# Site directories (exclude dev-only / PDF-generator / dead weight)
copy_tree "$ROOT/assets" "$OUT/assets" \
  --exclude='fonts/' \
  --exclude='badges-dark.jpg' \
  --exclude='badges-light.jpg' \
  --exclude='media/impersonation-latency-trap.mp4' \
  --exclude='media/video.mp4' \
  --exclude='*.pdf' \
  --exclude='*.zip' \
  --exclude='*.tar.gz' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='node_modules' \
  --exclude='.DS_Store'

# alignment/ retired: four stubs totalling 195 words across four routes, now
# sections of regulatory-alignment.html.

copy_tree "$ROOT/conformance" "$OUT/conformance" \
  --exclude='*.pdf' \
  --exclude='*.zip' \
  --exclude='__pycache__' \
  --exclude='.DS_Store'

# framework/: index, controls, conformance-suite and reference-implementation
# are merged into index.html, specification.html, evidence-pack.html and
# developers.html respectively. Only nhid-auth.html remains a route.
copy_tree "$ROOT/framework" "$OUT/framework" \
  --exclude='index.html' \
  --exclude='controls.html' \
  --exclude='conformance-suite.html' \
  --exclude='reference-implementation.html' \
  --exclude='*.pdf' \
  --exclude='*.zip' \
  --exclude='__pycache__' \
  --exclude='.DS_Store'

# platform/ retired entirely. TrustLayer has no verified design partners,
# customers, deployments or external validation, so it has no standalone public
# product route at this stage; presenting one would imply substance that does
# not exist. The pages remain in the repository.

# registry.html fetches /content/registry_entries.json. Without this the fetch
# 404s and the page only looks right because its catch handler happens to fire;
# real entries would never appear.
copy_tree "$ROOT/content" "$OUT/content" \
  --exclude='__pycache__' \
  --exclude='.DS_Store'

# (the simulator app directory is retired along with simulator.html — see RETIRED_PAGES)

copy_tree "$ROOT/specs" "$OUT/specs" \
  --exclude='*.zip' \
  --exclude='__pycache__' \
  --exclude='.DS_Store'

# Ensure Jekyll does not run on Pages
touch "$OUT/.nojekyll"

BYTES="$(du -sb "$OUT" | cut -f1)"
MB="$(awk "BEGIN {printf \"%.2f\", $BYTES/1024/1024}")"
# Redirects for every retired route, emitted last so nothing overwrites them.
python3 "$ROOT/scripts/ia/make_redirects.py" "$OUT"

echo "Pages site assembled: $OUT (${MB} MB, $(find "$OUT" -type f | wc -l | tr -d ' ') files)"