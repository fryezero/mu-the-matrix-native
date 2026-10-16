#!/bin/bash
# Shared by the installer, diagnostics and the copied bottle launcher.
FAST_X87_COMMIT=ab1a6a032e488c0d6eade54ce70a02d653277810
FAST_X87_HOME=${MU_FAST_X87_HOME:-$HOME/Library/Caches/MuTheMatrix/fast-x87/$FAST_X87_COMMIT}

fast_x87_identity() {
    local loader="$CX_ROOT/lib/wine/x86_64-unix/wine" server="$CX_ROOT/bin/wineserver-x86"
    if [ -x "$CX_ROOT/lib/wine/x86_64-unix/wine.app/Contents/MacOS/wine" ]; then
        loader="$CX_ROOT/lib/wine/x86_64-unix/wine.app/Contents/MacOS/wine"
    fi
    [ -x "$server" ] || server="$CX_ROOT/bin/wineserver"
    sw_vers -buildVersion &&
        cksum "$CX_ROOT/bin/wine" "$loader" "$server" \
            "$CX_ROOT/lib/wine/x86_64-unix/ntdll.so" /Library/Apple/usr/libexec/oah/libRosettaRuntime \
            "$FAST_X87_HOME/source/build/libtimewalker.dylib" \
            "$FAST_X87_HOME/source/build/x87-loader-wrapper" \
            "$FAST_X87_HOME/source/build/x87/bin/runtime_loader" \
            "$FAST_X87_HOME/source/build/x87/bin/libRuntimeRosettax87"
}

fast_x87_ready() {
    local identity
    identity=$(fast_x87_identity) || return 1
    [ -f "$FAST_X87_HOME/validated" ] &&
        [ "$(cat "$FAST_X87_HOME/validated")" = "$identity" ] &&
        [ "$(git -C "$FAST_X87_HOME/source" rev-parse HEAD)" = "$FAST_X87_COMMIT" ] &&
        git -C "$FAST_X87_HOME/source" diff --quiet HEAD -- &&
        [ -x "$FAST_X87_HOME/source/scripts/run-crossover.sh" ] &&
        [ -f "$FAST_X87_HOME/source/build/libtimewalker.dylib" ] &&
        [ -x "$FAST_X87_HOME/source/build/x87-loader-wrapper" ] &&
        [ -x "$FAST_X87_HOME/source/build/x87/bin/runtime_loader" ] &&
        [ -x "$FAST_X87_HOME/source/build/x87/bin/libRuntimeRosettax87" ]
}

fast_x87_select() {
    MU_WINE=("$CX_ROOT/bin/wine")
    case "${MU_FAST_X87:-auto}" in
        0) printf 'Using plain CrossOver (MU_FAST_X87=0).\n' ;;
        auto|1)
            if fast_x87_ready 2>/dev/null; then
                export TIMEWALKER_CROSSOVER_ROOT="$CX_ROOT"
                MU_WINE=("$FAST_X87_HOME/source/scripts/run-crossover.sh")
                printf 'Using opt-in fast x87 (%s).\n' "$FAST_X87_COMMIT"
            elif [ "${MU_FAST_X87:-auto}" = 1 ]; then
                printf 'Fast x87 is not validated for this system; rerun install-fast-x87.sh or use MU_FAST_X87=0.\n' >&2
                return 1
            else
                printf 'Fast x87 unavailable or stale; using plain CrossOver.\n'
            fi
            ;;
        *) printf 'MU_FAST_X87 must be auto, 0 or 1.\n' >&2; return 1 ;;
    esac
}
