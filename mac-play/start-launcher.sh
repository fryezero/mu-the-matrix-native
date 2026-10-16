#!/bin/bash
# Copied into the owned bottle by setup. Reset only that idle bottle's server.
set -euo pipefail
umask 077
die() { printf 'Error: %s\n' "$*" >&2; exit 1; }
: "${CX_ROOT:?}" "${CX_BOTTLE:?}" "${WINEPREFIX:?}" "${MU_GAME_DIR:?}"
[ "$(basename "$WINEPREFIX")" = "$CX_BOTTLE" ] || die 'Bottle/prefix mismatch'
STATE="$WINEPREFIX/.mu-matrix-setup"
[ -d "$STATE" ] && [ ! -L "$STATE" ] || die 'Missing setup state'
[ -f "$MU_GAME_DIR/MuTheMatrix.exe" ] || die 'Missing cloned launcher'
[ -f "$WINEPREFIX/drive_c/MuMatrixTools/MonitorCheck.exe" ] || die 'Missing display check; rerun setup.'
unset WINEARCH
SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd -P)
source "$SCRIPT_DIR/fast-x87.sh"
fast_x87_select
mkdir "$STATE/play.lock" 2>/dev/null || die 'Launcher already active or stale play.lock; inspect before removing it.'
TASKS=
trap 'if [ -n "$TASKS" ]; then rm -f -- "$TASKS"; fi; rmdir "$STATE/play.lock"' EXIT
TASKS=$(mktemp "$STATE/tasks.XXXXXX")
# Query through this bottle, never the host/global process list. Refuse a failed
# or unrecognisable query, since that cannot establish that killing is safe.
"$CX_ROOT/bin/wine" --bottle "$CX_BOTTLE" --workdir "$MU_GAME_DIR" tasklist /fo csv /nh > "$TASKS" ||
    die 'Cannot query bottle processes; display state was not reset.'
tr -d '\r' < "$TASKS" > "$TASKS.clean"
mv -- "$TASKS.clean" "$TASKS"
ROW='^"[^"]+","[0-9]+","[^"]*","[0-9]+","[^"]*"$'
grep -Eq "$ROW" "$TASKS" && ! grep -Ev "$ROW|^[[:space:]]*$" "$TASKS" > /dev/null ||
    die 'Unrecognised process list; display state was not reset.'
# Also refuse an existing launcher: it could start main.exe after the query.
if grep -Eiq '^"(main|MuTheMatrix)\.exe",' "$TASKS"; then
    die 'Game or launcher already running in this bottle. Close it before restarting.'
fi
printf 'Resetting display state for bottle %s\n' "$CX_BOTTLE"
# WINEPREFIX is exported by Play.command. Both operations are prefix-scoped.
"$CX_ROOT/bin/wineserver" -k
"$CX_ROOT/bin/wineserver" -w
# Keep the known-good .NET display probe on ordinary CrossOver. The optional
# translator is for the launcher chain; its .NET probe can stall on this host.
"$CX_ROOT/bin/wine" --bottle "$CX_BOTTLE" --workdir "$MU_GAME_DIR" \
    "$WINEPREFIX/drive_c/MuMatrixTools/MonitorCheck.exe" ||
    die 'Display validation failed; launcher was not started.'
cd -- "$MU_GAME_DIR"
"${MU_WINE[@]}" --bottle "$CX_BOTTLE" --workdir "$MU_GAME_DIR" "$MU_GAME_DIR/MuTheMatrix.exe"
