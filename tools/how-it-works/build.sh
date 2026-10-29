#!/usr/bin/env bash
# Build the interactive how-it-works player into assets/js/how-it-works/.
# The output is committed: the site is static and CI has no Node step.
#   cd tools/how-it-works && npm ci && ./build.sh
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
out="$here/../../assets/js/how-it-works"
rm -rf "$out" && mkdir -p "$out"
"$here/node_modules/.bin/esbuild" "$here/src/player.mjs" \
  --bundle --splitting --format=esm --minify --target=es2020 \
  --legal-comments=linked --chunk-names='[name]-[hash]' \
  --outdir="$out"
ls -l "$out"
