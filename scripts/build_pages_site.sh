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
shopt -s nullglob
for f in "$ROOT"/*.html; do
  cp "$f" "$OUT/"
done
shopt -u nullglob

for f in site.js nhid-clinical-ui.css CNAME .nojekyll robots.txt sitemap.xml; do
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

copy_tree "$ROOT/alignment" "$OUT/alignment" \
  --exclude='*.pdf' \
  --exclude='*.zip' \
  --exclude='__pycache__' \
  --exclude='.DS_Store'

copy_tree "$ROOT/conformance" "$OUT/conformance" \
  --exclude='*.pdf' \
  --exclude='*.zip' \
  --exclude='__pycache__' \
  --exclude='.DS_Store'

copy_tree "$ROOT/framework" "$OUT/framework" \
  --exclude='*.pdf' \
  --exclude='*.zip' \
  --exclude='__pycache__' \
  --exclude='.DS_Store'

copy_tree "$ROOT/platform" "$OUT/platform" \
  --exclude='*.pdf' \
  --exclude='*.zip' \
  --exclude='__pycache__' \
  --exclude='node_modules' \
  --exclude='.DS_Store'

copy_tree "$ROOT/simulator" "$OUT/simulator" \
  --exclude='*.pdf' \
  --exclude='*.zip' \
  --exclude='__pycache__' \
  --exclude='node_modules' \
  --exclude='.DS_Store'

copy_tree "$ROOT/specs" "$OUT/specs" \
  --exclude='*.zip' \
  --exclude='__pycache__' \
  --exclude='.DS_Store'

# Ensure Jekyll does not run on Pages
touch "$OUT/.nojekyll"

BYTES="$(du -sb "$OUT" | cut -f1)"
MB="$(awk "BEGIN {printf \"%.2f\", $BYTES/1024/1024}")"
echo "Pages site assembled: $OUT (${MB} MB, $(find "$OUT" -type f | wc -l | tr -d ' ') files)"