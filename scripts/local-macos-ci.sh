#!/bin/sh
# Run the full CI locally on a Mac; this is the merge gate (the hosted workflow is
# manual-only). Usage: scripts/local-macos-ci.sh [PYTHON]
# MU_GATE_JOBS=N (default min(4, cores/2)) runs `make test`'s suites in a pool of N (scripts/run_test_suites.py)
# and, after `make test`, the fixture scenarios, the viewer and live-reader builds and the audit side by side.
# MU_GATE_JOBS=1 is the sequential gate, step by step as before. Run it under `nice -n 10` on a shared Mac.
set -eu
cd "$(dirname "$0")/.."
PY="${1:-${PYTHON:-tools/python/bin/python}}"
[ "$(uname)" = Darwin ] || { echo "local-macos-ci: run this on macOS" >&2; exit 2; }
make test PYTHON="$PY"
mkdir -p verify-runs
FIXTURES="$(mktemp -d "$PWD/verify-runs/ci-fixtures-XXXXXX")/suite"
if [ "${MU_GATE_JOBS:-}" = 1 ]; then
  "$PY" scripts/run_fixture_scenarios.py --report "$FIXTURES"
  make native-viewer
  make live-readers
  "$PY" scripts/audit_repository.py
  echo "local-macos-ci: all macOS checks passed"
  exit 0
fi
# These four only read what `make test` built (the viewer targets are already built by native/tests) and write
# disjoint outputs: native/build viewer binaries, live-readers/build, a fresh verify-runs folder, nothing.
LOGS="$(mktemp -d "$PWD/verify-runs/ci-stages-XXXXXX")"
"$PY" scripts/run_fixture_scenarios.py --report "$FIXTURES" >"$LOGS/fixtures.log" 2>&1 & P1=$!
make native-viewer >"$LOGS/native-viewer.log" 2>&1 & P2=$!
make live-readers >"$LOGS/live-readers.log" 2>&1 & P3=$!
"$PY" scripts/audit_repository.py >"$LOGS/audit.log" 2>&1 & P4=$!
FAILED=""
for stage in fixtures:$P1 native-viewer:$P2 live-readers:$P3 audit:$P4; do
  name=${stage%%:*}
  if wait "${stage#*:}"; then
    echo "local-macos-ci: $name ok ($(tail -n 1 "$LOGS/$name.log" | cut -c 1-100))"
  else
    FAILED="$FAILED $name"
    echo "local-macos-ci: $name FAILED; last lines of ${LOGS#"$PWD"/}/$name.log:" >&2
    tail -n 40 "$LOGS/$name.log" >&2
  fi
done
[ -z "$FAILED" ] || { echo "local-macos-ci: failed:$FAILED" >&2; exit 1; }
echo "local-macos-ci: all macOS checks passed"
