#!/bin/bash
# Build authored PE32 x87/SSE2 probes and run only in a setup-owned idle bottle.
set -euo pipefail
SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd -P)
source "$SCRIPT_DIR/../fast-x87.sh"
source "$SCRIPT_DIR/bottle.sh"
[ "$#" = 1 ] || die 'Usage: run-fpbench.sh BOTTLE (MU_FAST_X87=0, 1 or auto)'
diagnostic_bottle "$1"
OUT=${MU_DIAGNOSTICS_OUT:-$WINEPREFIX/.mu-matrix-setup/diagnostics}
mkdir -p "$OUT"
CC=${MINGW_CC:-i686-w64-mingw32-gcc}
"$CC" -O2 -fno-tree-vectorize -mfpmath=387 '-DMODE="x87"' "$SCRIPT_DIR/fpbench.c" -o "$OUT/fp_x87.exe"
"$CC" -O2 -fno-tree-vectorize -msse2 -mfpmath=sse '-DMODE="SSE2"' "$SCRIPT_DIR/fpbench.c" -o "$OUT/fp_sse.exe"
fast_x87_select
for mode in x87 sse; do
    "${MU_WINE[@]}" --bottle "$CX_BOTTLE" --workdir "$OUT" "$OUT/fp_$mode.exe"
done
