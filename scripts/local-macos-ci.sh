#!/bin/sh
# Run the full CI locally on a Mac; this is the merge gate (the hosted workflow is
# manual-only). Usage: scripts/local-macos-ci.sh [PYTHON]
set -eu
cd "$(dirname "$0")/.."
PY="${1:-${PYTHON:-tools/.venv/bin/python}}"
[ "$(uname)" = Darwin ] || { echo "local-macos-ci: run this on macOS" >&2; exit 2; }
make test PYTHON="$PY"
make native-viewer
make live-readers
"$PY" scripts/audit_repository.py
echo "local-macos-ci: all macOS checks passed"
