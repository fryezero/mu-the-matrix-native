#!/bin/bash
# package-fast-x87.sh TIMEWALKER_CHECKOUT OUT_DIR - collect rosetta-timewalker's built x87 translator for players.
# TIMEWALKER_CHECKOUT is a built checkout of github.com/aprilmaccydee/rosetta-timewalker at the commit pinned in
# mac-play/fast-x87.sh (build: make && make x87, or mac-play/install-fast-x87.sh's cache). OUT_DIR receives
# libtimewalker.dylib, runtime_loader, libRuntimeRosettax87 and the licenses (all MIT), for
# setup-mu-mac.sh --fast-x87-dir or make -C mac-play/bundle EMBED_FAST_X87=OUT_DIR. Never commit the output.
set -euo pipefail
TW=$1 OUT=$2
HERE=$(cd -- "$(dirname -- "$0")" && pwd -P)
PIN=$(sed -n 's/^FAST_X87_COMMIT=//p' "$HERE/../../fast-x87.sh")
HEAD=$(git -C "$TW" rev-parse HEAD)
[ "$HEAD" = "$PIN" ] || { echo "timewalker checkout is at $HEAD, expected the pinned $PIN" >&2; exit 1; }
# Only the upstream loader wrapper may differ (it is not shipped; mac-play/x87-main-only-wrapper.c replaces it).
git -C "$TW" diff --quiet HEAD -- . ':!src/x87_loader_wrapper.c' || { echo "timewalker checkout has local changes" >&2; exit 1; }
mkdir -p "$OUT"
cp "$TW/build/libtimewalker.dylib" "$TW/build/x87/bin/runtime_loader" "$TW/build/x87/bin/libRuntimeRosettax87" "$OUT/"
cp "$TW/LICENSE" "$OUT/LICENSE"
cp "$TW/third_party/rosettax87_jit/LICENSE" "$OUT/LICENSE-rosettax87_jit"
cp "$TW/THIRD_PARTY_NOTICES.md" "$OUT/THIRD_PARTY_NOTICES.md"
printf 'rosetta-timewalker %s (MIT), built from https://github.com/aprilmaccydee/rosetta-timewalker\n' "$PIN" > "$OUT/SOURCE.txt"
(cd "$OUT" && shasum -a 256 libtimewalker.dylib runtime_loader libRuntimeRosettax87)
