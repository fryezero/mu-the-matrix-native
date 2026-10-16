#!/bin/bash
# Opt-in, user-cache-only build. No system/Rosetta files or existing game bottle edits.
set -euo pipefail
umask 077
SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd -P)
source "$SCRIPT_DIR/fast-x87.sh"
source "$SCRIPT_DIR/diagnostics/bottle.sh"
[ "$#" = 2 ] && [ "$1" = --bottle ] || die 'Usage: install-fast-x87.sh --bottle SETUP_OWNED_IDLE_BOTTLE'
[ "$(uname -s)" = Darwin ] && [ "$(uname -m)" = arm64 ] || die 'Requires Apple Silicon macOS and Rosetta'
xcode-select -p >/dev/null || die 'Install Xcode Command Line Tools: xcode-select --install'
for tool in git make cmake brew i686-w64-mingw32-gcc; do
    command -v "$tool" >/dev/null || die "Missing $tool. Install prerequisites: brew install cmake llvm mingw-w64"
done
LLVM_BIN=$(brew --prefix llvm)/bin
[ -x "$LLVM_BIN/llvm-objcopy" ] && [ -x "$LLVM_BIN/llvm-mc" ] || die 'Install Homebrew LLVM'
diagnostic_bottle "$2"
mkdir -p "$FAST_X87_HOME"
mkdir "$FAST_X87_HOME/install.lock" || die 'Install lock exists; inspect before removing it'
trap 'rmdir "$FAST_X87_HOME/install.lock"' EXIT
# A failed rebuild/self-check disables automatic selection of this cache entry.
rm -f "$FAST_X87_HOME/validated"
SOURCE="$FAST_X87_HOME/source"
if [ ! -e "$SOURCE" ]; then
    git init "$SOURCE"
    git -C "$SOURCE" remote add origin https://github.com/aprilmaccydee/rosetta-timewalker.git
    git -C "$SOURCE" fetch --depth 1 origin "$FAST_X87_COMMIT"
    git -C "$SOURCE" checkout --detach FETCH_HEAD
fi
[ "$(git -C "$SOURCE" rev-parse HEAD)" = "$FAST_X87_COMMIT" ] || die 'Cache commit mismatch; choose a fresh MU_FAST_X87_HOME'
git -C "$SOURCE" diff --exit-code HEAD -- || die 'Cache source has local changes; choose a fresh MU_FAST_X87_HOME'
printf 'Verified external source commit %s\n' "$FAST_X87_COMMIT"
make -C "$SOURCE" -j4 all build/test_x87_fld \
    LLVM_OBJCOPY="$LLVM_BIN/llvm-objcopy" LLVM_MC="$LLVM_BIN/llvm-mc" JOBS=4 \
    > "$FAST_X87_HOME/build.log" 2>&1
"$SOURCE/build/x87/bin/runtime_loader" "$SOURCE/build/test_x87_fld" \
    > "$FAST_X87_HOME/fld-check.log" 2>&1
# Build/run authored probes in the caller's setup-owned bottle. These do not kill
# servers, change display state, or start a game. Upstream's ARPL UUID rejection
# on newer macOS is separate from the x87 path and is retained in the log.
MU_FAST_X87=0 "$SCRIPT_DIR/diagnostics/run-fpbench.sh" "$CX_BOTTLE" \
    2>&1 | tee "$FAST_X87_HOME/fp-plain.log"
OUT=${MU_DIAGNOSTICS_OUT:-$WINEPREFIX/.mu-matrix-setup/diagnostics}
TIMEWALKER_CROSSOVER_ROOT="$CX_ROOT" "$SOURCE/scripts/run-crossover.sh" \
    --bottle "$CX_BOTTLE" --workdir "$OUT" "$OUT/fp_x87.exe" \
    2>&1 | tee "$FAST_X87_HOME/fp-fast.log"
plain=$(sed -nE 's/^x87:.*\(chk ([^)]*)\).*/\1/p' "$FAST_X87_HOME/fp-plain.log" | tr -d '\r')
fast=$(sed -nE 's/^x87:.*\(chk ([^)]*)\).*/\1/p' "$FAST_X87_HOME/fp-fast.log" | tr -d '\r')
[ -n "$plain" ] && [ "$plain" = "$fast" ] &&
    [[ "$plain" =~ ^-?[0-9]+\.[0-9]+$ ]] || die 'x87 benchmark checksum mismatch or missing output'
grep -q 'RosettaRuntimex87 built' "$FAST_X87_HOME/fp-fast.log" || die 'Fast translator activation was not observed'
identity=$(fast_x87_identity) || die 'Cannot identify macOS/Rosetta/CrossOver runtime'
printf '%s\n' "$identity" > "$FAST_X87_HOME/validated.tmp"
mv "$FAST_X87_HOME/validated.tmp" "$FAST_X87_HOME/validated"
printf 'Fast x87 installed and self-checked. Logs: %s\n' "$FAST_X87_HOME"
printf 'Play.command selects it automatically. MU_FAST_X87=0 forces plain CrossOver.\n'
