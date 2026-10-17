#!/bin/bash
# Read only the named bottle's process list. Never reset a server here.
die() { printf 'Error: %s\n' "$*" >&2; exit 1; }
diagnostic_bottle() {
    [[ "$1" =~ ^[A-Za-z0-9][A-Za-z0-9_-]*$ ]] || die 'Invalid bottle name'
    case "$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')" in
        windows10mu|steam|mumatrixrecovery|mumatrix32) die 'Protected bottle' ;;
    esac
    export CX_ROOT=${CX_ROOT:-/Applications/CrossOver.app/Contents/SharedSupport/CrossOver}
    export CX_BOTTLE=$1 WINEPREFIX="$HOME/Library/Application Support/CrossOver/Bottles/$1"
    [ ! -L "$WINEPREFIX" ] &&
        [ "$(cat "$WINEPREFIX/.mu-matrix-setup/owner")" = mu-matrix-crossover-32bit-v2 ] || die 'Expected a setup-owned bottle'
    unset WINEARCH
    local tasks row
    tasks=$("$CX_ROOT/bin/wine" --bottle "$1" tasklist /fo csv /nh | tr -d '\r') || die 'Cannot query bottle'
    row='^"[^"]+","[0-9]+","[^"]*","[0-9]+","[^"]*"$'
    printf '%s\n' "$tasks" | grep -Eq "$row" &&
        ! printf '%s\n' "$tasks" | grep -Ev "$row|^[[:space:]]*$" >/dev/null || die 'Unrecognised process list'
    [ "${2:-idle}" != live-profile ] || return 0
    ! printf '%s\n' "$tasks" | grep -Eiq '^"(main|MuTheMatrix)\.exe",' || die 'Close the game/launcher in this bottle first'
}
