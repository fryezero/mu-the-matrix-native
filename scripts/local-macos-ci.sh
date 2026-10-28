#!/bin/sh
# Run the full CI locally on a Mac; this is the merge gate (the hosted workflow is
# manual-only). Usage: scripts/local-macos-ci.sh [PYTHON]
set -eu
cd "$(dirname "$0")/.."
PY="${1:-${PYTHON:-tools/python/bin/python}}"
[ "$(uname)" = Darwin ] || { echo "local-macos-ci: run this on macOS" >&2; exit 2; }
make test PYTHON="$PY"
mkdir -p verify-runs
"$PY" scripts/run_fixture_scenarios.py --report "$(mktemp -d "$PWD/verify-runs/ci-fixtures-XXXXXX")/suite"
make native-viewer
make live-readers
"$PY" scripts/audit_repository.py
echo "local-macos-ci: all macOS checks passed"
