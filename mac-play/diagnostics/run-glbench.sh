#!/bin/bash
set -euo pipefail
SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd -P)
source "$SCRIPT_DIR/../fast-x87.sh"
source "$SCRIPT_DIR/bottle.sh"
[ "$#" -ge 1 ] && [ "$#" -le 4 ] || die 'Usage: run-glbench.sh BOTTLE [FRAMES [QUADS_PER_FRAME [QUADS_PER_BLOCK]]]'
diagnostic_bottle "$1"
shift
OUT=${MU_DIAGNOSTICS_OUT:-$WINEPREFIX/.mu-matrix-setup/diagnostics}
mkdir -p "$OUT"
"${MINGW_CC:-i686-w64-mingw32-gcc}" -O2 -msse2 -mfpmath=sse "$SCRIPT_DIR/glbench.c" -o "$OUT/glbench.exe" -lopengl32 -lgdi32
# Use a process-local override; never alter the bottle registry for A/B runs.
case "${MU_GL_BATCHING:-0}" in
    0) GL_OVERRIDE=opengl32=b ;;
    1) make -C "$SCRIPT_DIR/../mugl"
       cp "$SCRIPT_DIR/../mugl/build/opengl32.dll" "$OUT/opengl32.dll"
       GL_OVERRIDE=opengl32=n,b ;;
    *) die 'MU_GL_BATCHING must be 0 or 1' ;;
esac
fast_x87_select
"${MU_WINE[@]}" --bottle "$CX_BOTTLE" --dll "$GL_OVERRIDE" --workdir "$OUT" "$OUT/glbench.exe" "$@"
