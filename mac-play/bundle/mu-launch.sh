#!/bin/bash
# Start the Mu The Matrix launcher (MuTheMatrix.exe) in a CrossOver bottle. Part of MAC-BUNDLE-001:
# "Mu The Matrix.app" runs this copy from Contents/Resources; it also works on its own from a checkout.
# Bash 3.2 compatible (stock macOS /bin/bash). It does what mac-play/installer/play-mu.sh does, with
# preflight checks that report one machine-readable error line, a dry-run mode and the resolution setting.
#
# Usage: mu-launch.sh [--check | --dry-run | --run | --list-bottles | --list-modes]
#   --check         preflight only (CrossOver, bottle, 32-bit, game, fast x87, resolution, not running)
#   --dry-run       preflight, then print every action and the exact command; changes nothing
#   --run           (default) preflight, apply the resolution, reset the bottle's wineserver, start
#   --list-bottles  CrossOver bottles, one per line: NAME<TAB>ARCH<TAB>game|nogame
#   --list-modes    the bottle's C:\mutools\mu-modes.txt, one WxH per line, then "current N" if known
#
# Settings come from the environment (the app passes them from its settings plist):
#   MU_BOTTLE          bottle name (required)
#   MU_FAST_X87        1 = route main.exe through rosetta-timewalker's fast x87 translator; 0 (default) plain
#   MU_TIMEWALKER_DIR  timewalker checkout with scripts/run-crossover.sh; empty = the validated
#                      install-fast-x87.sh cache (mac-play/fast-x87.sh)
#   MU_RESOLUTION      WxH from mu-modes.txt: set LauncherOption.if DevModeIndex before starting; empty = keep
#   MU_LOG_DIR         log directory (default ~/Library/Logs/MuTheMatrix); the launcher's own output goes to
#                      wine-BOTTLE.log there
#   MU_START_WAIT      seconds to watch the launcher for an early exit (default 4)
#   MU_DEBUGMSG        passed to wine --debugmsg
#   CX_ROOT, MUKIT_BOTTLES_DIR  CrossOver runtime and bottle directory (defaults: the standard locations)
#
# Output: "MU-INFO text", "MU-PLAN action" (dry run) and, on failure, one "MU-ERROR CODE text" line.
# Exit codes: 0 ok, 2 bad setting, 10 CrossOver missing, 11 bottle missing, 12 not a 32-bit bottle,
# 13 game not in the bottle, 14 game already running, 15 fast x87 runtime missing, 16 resolution not
# available, 17 resolution could not be written, 20 launcher exited right away.
set -u
HERE=$(cd -- "$(dirname -- "$0")" && pwd -P)
# Resources layout (app) or checkout layout (mac-play/bundle next to mac-play/installer).
if [ -f "$HERE/mukit.sh" ]; then LIB="$HERE/mukit.sh"; FASTX87="$HERE/fast-x87.sh"
else LIB="$HERE/../installer/lib/mukit.sh"; FASTX87="$HERE/../fast-x87.sh"; fi
# shellcheck source=../installer/lib/mukit.sh
source "$LIB" || { echo "MU-ERROR 2 helper library missing: $LIB"; exit 2; }

MODE=run
case "${1:-}" in
    ''|--run) MODE=run ;; --check) MODE=check ;; --dry-run) MODE=dry ;;
    --list-bottles) MODE=bottles ;; --list-modes) MODE=modes ;;
    -h|--help) sed -n '2,/^set -u/p' "$0" | sed '$d; s/^# \{0,1\}//'; exit 0 ;;
    *) echo "MU-ERROR 2 unknown option: $1"; exit 2 ;;
esac

fail() { echo "MU-ERROR $1 $2"; exit "$1"; }
info() { echo "MU-INFO $*"; }
plan() { echo "MU-PLAN $*"; }

BOTTLES=$MUKIT_BOTTLES_DIR
LOG_DIR=${MU_LOG_DIR:-$HOME/Library/Logs/MuTheMatrix}
BOTTLE=${MU_BOTTLE:-}
FAST=${MU_FAST_X87:-0}
TW_DIR=${MU_TIMEWALKER_DIR:-}
RES=${MU_RESOLUTION:-}
WAIT=${MU_START_WAIT:-4}

if [ "$MODE" = bottles ]; then
    [ -d "$BOTTLES" ] || exit 0
    for d in "$BOTTLES"/*/; do
        d=${d%/}; [ -f "$d/cxbottle.conf" ] || continue
        arch=$(mukit_conf_get "$d/cxbottle.conf" WineArch) || arch=unknown
        game=nogame; [ -f "$d/drive_c/MuTheMatrix/MuTheMatrix.exe" ] && game=game
        printf '%s\t%s\t%s\n' "${d##*/}" "$arch" "$game"
    done
    exit 0
fi

# ---------------------------------------------------------------- settings
[ -n "$BOTTLE" ] || fail 2 "No bottle is selected. Choose one in Settings."
mukit_valid_bottle_name "$BOTTLE" || fail 2 "Invalid bottle name '$BOTTLE' (letters, digits, _ and - only)."
case "$FAST" in 0|1) ;; *) fail 2 "Fast x87 must be 0 or 1, not '$FAST'." ;; esac
[[ "$WAIT" =~ ^[0-9]{1,2}$ ]] || fail 2 "MU_START_WAIT must be 0-99 seconds."
[ -z "$RES" ] || mukit_mode_valid "$RES" || fail 2 "Resolution '$RES' is not of the form WIDTHxHEIGHT."

PREFIX="$BOTTLES/$BOTTLE"
GAME="$PREFIX/drive_c/MuTheMatrix"
MODES_FILE="$PREFIX/drive_c/mutools/mu-modes.txt"
LOPT="$GAME/LauncherOption.if"

read_modes() { [ -f "$MODES_FILE" ] && tr -s ' \t\r\n' ' ' < "$MODES_FILE" | sed 's/^ //; s/ $//'; }

# ---------------------------------------------------------------- preflight
[ -x "$CX_ROOT/bin/wine" ] && [ -x "$CX_ROOT/bin/wineserver" ] ||
    fail 10 "CrossOver was not found at $CX_ROOT. Install CrossOver in /Applications and open it once."
[ -d "$PREFIX" ] && [ -f "$PREFIX/cxbottle.conf" ] ||
    fail 11 "The CrossOver bottle '$BOTTLE' does not exist. Choose another bottle in Settings or create it with mac-play/installer/setup-mu-mac.sh."
arch=$(mukit_conf_get "$PREFIX/cxbottle.conf" WineArch) || arch=unset
[ "$arch" = win32 ] || fail 12 "Bottle '$BOTTLE' is not a 32-bit bottle (WineArch=$arch). The game needs a 32-bit win10 bottle."
[ -f "$GAME/MuTheMatrix.exe" ] || fail 13 "Mu The Matrix is not installed in bottle '$BOTTLE' (C:\\MuTheMatrix\\MuTheMatrix.exe is missing)."

if [ "$MODE" = modes ]; then
    modes=$(read_modes) || fail 16 "Bottle '$BOTTLE' has no C:\\mutools\\mu-modes.txt."
    mukit_modes_valid "$modes" || fail 16 "C:\\mutools\\mu-modes.txt in '$BOTTLE' is not a list of WxH modes."
    for m in $modes; do echo "$m"; done
    cur=$(mukit_lopt_get "$LOPT" DevModeIndex 2>/dev/null) && [[ "$cur" =~ ^[0-9]+$ ]] && echo "current $cur"
    exit 0
fi

RUNNER=("$CX_ROOT/bin/wine")
X87_ENV=()
if [ "$FAST" = 1 ]; then
    if [ -n "$TW_DIR" ]; then
        [ -x "$TW_DIR/scripts/run-crossover.sh" ] && [ -f "$TW_DIR/build/libtimewalker.dylib" ] ||
            fail 15 "Fast x87 is on, but $TW_DIR has no built rosetta-timewalker (scripts/run-crossover.sh, build/libtimewalker.dylib). Choose its folder in Settings or turn fast x87 off."
        RUNNER=("$TW_DIR/scripts/run-crossover.sh")
        X87_ENV=(TIMEWALKER_X87_ONLY=main.exe)
    else
        # shellcheck source=../fast-x87.sh
        { [ -f "$FASTX87" ] && source "$FASTX87" && fast_x87_ready 2>/dev/null; } ||
            fail 15 "Fast x87 is on, but no validated runtime was found. Run mac-play/install-fast-x87.sh, choose a timewalker folder in Settings, or turn fast x87 off."
        RUNNER=("$FAST_X87_HOME/source/scripts/run-crossover.sh")
        X87_ENV=(TIMEWALKER_CROSSOVER_ROOT="$CX_ROOT" TIMEWALKER_X87_LOADER_WRAPPER="$FAST_X87_HOME/x87-main-only-wrapper" TIMEWALKER_X87_ONLY=main.exe)
    fi
fi

NEW_LOPT=
if [ -n "$RES" ]; then
    modes=$(read_modes) || fail 16 "Resolution $RES was chosen, but bottle '$BOTTLE' has no C:\\mutools\\mu-modes.txt. Choose \"Keep launcher setting\"."
    idx=; i=0
    for m in $modes; do [ "$m" = "$RES" ] && { idx=$i; break; }; i=$((i + 1)); done
    [ -n "$idx" ] || fail 16 "Resolution $RES is not in bottle '$BOTTLE''s mode list ($modes). Choose another one in Settings."
    if [ -f "$LOPT" ]; then
        cur_idx=$(mukit_lopt_get "$LOPT" DevModeIndex) || cur_idx=
        cur_wm=$(mukit_lopt_get "$LOPT" WindowMode) || cur_wm=1
        cur_id=$(mukit_lopt_get "$LOPT" ID) || cur_id=
    else cur_idx=; cur_wm=1; cur_id=; fi
    [ "$cur_idx" = "$idx" ] || NEW_LOPT=$(mukit_lopt_render "$idx" "${cur_wm:-1}" "$cur_id")
fi

# One client at a time across all bottles (same rule as play-mu.sh): both executables are checked.
if pgrep -f 'C:\\MuTheMatrix\\main.exe' >/dev/null 2>&1 || pgrep -f 'C:\\MuTheMatrix\\MuTheMatrix.exe' >/dev/null 2>&1; then
    fail 14 "Mu The Matrix is already running. Close the game and the launcher first, then start again."
fi

LOG="$LOG_DIR/wine-$BOTTLE.log"
info "bottle $BOTTLE (win32), CrossOver $CX_ROOT"
info "fast x87 $([ "$FAST" = 1 ] && echo "on (${RUNNER[0]})" || echo off)"
if [ -n "$RES" ]; then info "resolution $RES = DevModeIndex $idx$([ -z "$NEW_LOPT" ] && echo ' (already set)')"; else info 'resolution: keep launcher setting'; fi
[ "$MODE" = check ] && { info 'preflight ok'; exit 0; }

DBG=(); [ -n "${MU_DEBUGMSG:-}" ] && DBG=(--debugmsg "$MU_DEBUGMSG")
CMD=("${RUNNER[@]}" --bottle "$BOTTLE" ${DBG[@]+"${DBG[@]}"} --workdir 'C:\MuTheMatrix' 'C:\MuTheMatrix\MuTheMatrix.exe')

if [ "$MODE" = dry ]; then
    [ -z "$NEW_LOPT" ] || plan "write $LOPT DevModeIndex:$idx (backup ${LOPT##*/}.mu-app-backup if none exists)"
    plan "WINEPREFIX=$PREFIX $CX_ROOT/bin/wineserver -k"
    plan "env ${X87_ENV[*]:-} ${CMD[*]} > $LOG"
    info 'dry run: nothing was changed'
    exit 0
fi

# ---------------------------------------------------------------- run
mkdir -p "$LOG_DIR" || fail 2 "Cannot create log directory $LOG_DIR."
if [ -n "$NEW_LOPT" ]; then
    { [ ! -f "$LOPT" ] || [ -f "$LOPT.mu-app-backup" ] || cp -p "$LOPT" "$LOPT.mu-app-backup"; } &&
        printf '%s' "$NEW_LOPT" > "$LOPT.mu-app-tmp" && mv -f "$LOPT.mu-app-tmp" "$LOPT" ||
        { rm -f "$LOPT.mu-app-tmp"; fail 17 "Could not write $LOPT."; }
    info "LauncherOption.if DevModeIndex set to $idx ($RES)"
fi
# Stale display state after sleep breaks the launcher: restart this (idle) bottle's wineserver only.
WINEPREFIX="$PREFIX" "$CX_ROOT/bin/wineserver" -k >/dev/null 2>&1
sleep 1
info "starting ${CMD[*]}"
{ echo "== $(date '+%Y-%m-%d %H:%M:%S') mu-launch.sh: bottle $BOTTLE fast-x87 $FAST resolution ${RES:-keep}"; } > "$LOG"
nohup env ${X87_ENV[@]+"${X87_ENV[@]}"} "${CMD[@]}" >>"$LOG" 2>&1 </dev/null &
pid=$!
t=0
while [ "$t" -lt "$WAIT" ]; do
    kill -0 "$pid" 2>/dev/null || break
    sleep 1; t=$((t + 1))
done
if ! kill -0 "$pid" 2>/dev/null; then
    wait "$pid"; rc=$?
    # CrossOver's wine wrapper may hand the program to an already running server and return 0.
    [ "$rc" = 0 ] || fail 20 "The launcher exited right away (status $rc). See $LOG."
fi
info "launcher started (log $LOG)"
exit 0
