#!/bin/bash
# SPDX-License-Identifier: MIT
set -euo pipefail
SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd -P)
source "$SCRIPT_DIR/bottle.sh"
[ "$#" -ge 1 ] && [ "$#" -le 3 ] || die 'Usage: run-eipprof.sh BOTTLE [EXE_NAME [SECONDS]]'
# Profiler explicitly needs a live target. Keep ownership/protected-bottle checks,
# but omit the idle-game guard used by the synthetic benchmarks.
diagnostic_bottle "$1" live-profile
OUT=${MU_DIAGNOSTICS_OUT:-$WINEPREFIX/.mu-matrix-setup/diagnostics}
mkdir -p "$OUT"
"${MINGW_CC:-i686-w64-mingw32-gcc}" -O2 -msse2 -mfpmath=sse "$SCRIPT_DIR/eipprof.c" -o "$OUT/eipprof.exe"
"$CX_ROOT/bin/wine" --bottle "$CX_BOTTLE" "$OUT/eipprof.exe" "${2:-main.exe}" "${3:-10}" "$("$CX_ROOT/bin/wine" --bottle "$CX_BOTTLE" winepath -w "$OUT/eipprof.txt" | tr -d '\r')"
