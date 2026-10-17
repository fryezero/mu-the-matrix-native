#!/bin/sh
# Run the macOS half of CI locally (the hosted macOS job is manual-only to save
# Actions minutes). Usage: scripts/local-macos-ci.sh [PYTHON]
set -eu
cd "$(dirname "$0")/.."
PY="${1:-${PYTHON:-tools/.venv/bin/python}}"
[ "$(uname)" = Darwin ] || { echo "local-macos-ci: run this on macOS" >&2; exit 2; }
make test PYTHON="$PY"
make native-viewer
make -C mac-play/machprof
"$PY" scripts/audit_repository.py
echo "local-macos-ci: all macOS checks passed"
