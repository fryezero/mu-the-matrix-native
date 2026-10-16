#!/bin/bash
set -euo pipefail
SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd -P)
source "$SCRIPT_DIR/../fast-x87.sh"
source "$SCRIPT_DIR/bottle.sh"
[ "$#" -ge 1 ] && [ "$#" -le 3 ] || die 'Usage: run-glbench.sh BOTTLE [FRAMES [QUADS_PER_FRAME]]'
diagnostic_bottle "$1"
shift
OUT=${MU_DIAGNOSTICS_OUT:-$WINEPREFIX/.mu-matrix-setup/diagnostics}
mkdir -p "$OUT"
"${MINGW_CC:-i686-w64-mingw32-gcc}" -O2 -msse2 -mfpmath=sse "$SCRIPT_DIR/glbench.c" -o "$OUT/glbench.exe" -lopengl32 -lgdi32
fast_x87_select
"${MU_WINE[@]}" --bottle "$CX_BOTTLE" --workdir "$OUT" "$OUT/glbench.exe" "$@"
