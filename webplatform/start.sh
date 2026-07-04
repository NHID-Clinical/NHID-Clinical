#!/usr/bin/env bash
# One-command launcher for the NHID-Clinical web platform.
# Brings the full platform up from a fresh clone. No code editing required.
set -euo pipefail

# Resolve repo root (this script lives in <repo>/webplatform/).
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$HERE/.." && pwd)"
cd "$REPO_ROOT"

PORT="${PORT:-8080}"
# Keep the demo's data isolated from the committed repo-root nhid_events.db.
export NHID_PLATFORM_DB="${NHID_PLATFORM_DB:-$HERE/nhid_platform.db}"

# Create/refresh a venv and install deps (repo + web layer).
PY="${PYTHON:-python3}"
if [ ! -d "$HERE/.venv" ]; then
  "$PY" -m venv "$HERE/.venv"
fi
# shellcheck disable=SC1091
source "$HERE/.venv/bin/activate"
pip install --quiet --upgrade pip
pip install --quiet -r "$REPO_ROOT/requirements.txt"
pip install --quiet -r "$HERE/requirements.txt"

echo ""
echo "  NHID-Clinical platform → http://localhost:${PORT}"
echo "  (Dashboard, Transcript Analyzer, Synthetic Generator, Vendor Verification, Audit Log)"
echo ""

# 'webplatform.app:app' — package name deliberately avoids shadowing stdlib 'platform'.
exec python -m uvicorn webplatform.app:app --host 0.0.0.0 --port "$PORT"
