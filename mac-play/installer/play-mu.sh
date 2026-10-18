#!/bin/zsh
# Launch Mu The Matrix from a prefix created by setup-mu-mac.sh. The Desktop .command file written by the
# setup runs this script; Mu The Matrix.app does the same through its own mu-launch.sh.
#
#   MU_RUNTIME         free (default: the free Wine runtime) | crossover (legacy CrossOver bottle)
#   MU_PREFIX          free runtime: the prefix (default ~/Library/Application Support/MuTheMatrix/prefix)
#   MUKIT_FREE_HOME    free runtime folder (default ~/Library/Application Support/MuTheMatrix)
#   MU_BOTTLE          crossover: bottle to start (default MuMatrixKit)
#   MU_FAST_X87=1      crossover: route main.exe through an existing rosetta-timewalker build (default 0)
#   MU_TIMEWALKER_DIR  that checkout/build (only with MU_FAST_X87=1)
#   CX_ROOT            CrossOver runtime directory
#   MU_DEBUGMSG        crossover: passed to wine --debugmsg; free: WINEDEBUG
#
# It refuses a second instance (one client at a time, across all prefixes) and restarts the prefix's idle
# wineserver first, because stale display state after sleep breaks the launcher. It starts the original
# launcher MuTheMatrix.exe in C:\MuTheMatrix; log: ~/Library/Logs/MuTheMatrix-<name>.log (per prefix, so
# starting one never truncates another one's running log).
for _v in ${(k)parameters[(I)CLAUDE*]}; do unset $_v; done; unset _v
RUNTIME=${MU_RUNTIME:-free}
if pgrep -f 'C:\\MuTheMatrix\\main.exe' >/dev/null || pgrep -f 'C:\\MuTheMatrix\\MuTheMatrix.exe' >/dev/null; then
  osascript -e 'display dialog "Mu The Matrix is already running. Close the game and launcher first, then launch again." buttons {"OK"} with title "Mu The Matrix"' >/dev/null 2>&1
  exit 1
fi
if [ "$RUNTIME" = free ]; then
  HOME_DIR=${MUKIT_FREE_HOME:-$HOME/Library/Application Support/MuTheMatrix}
  PREFIX=${MU_PREFIX:-$HOME_DIR/prefix}
  RT="$HOME_DIR/runtime/$(cat "$HOME_DIR/runtime/current" 2>/dev/null | tr -d '\r\n ')"
  [ -x "$RT/wine/bin/wine" ] || { echo "No Wine runtime in $HOME_DIR/runtime (run setup-mu-mac.sh)" >&2; exit 1; }
  [ -f "$PREFIX/drive_c/MuTheMatrix/MuTheMatrix.exe" ] || { echo "Mu The Matrix is not installed in $PREFIX" >&2; exit 1; }
  export WINEPREFIX="$PREFIX" WINEDEBUG=${MU_DEBUGMSG:--all}
  unset WINEARCH WINEDLLOVERRIDES
  "$RT/wine/bin/wineserver" -k 2>/dev/null
  sleep 1
  LOG=$HOME/Library/Logs/MuTheMatrix-${PREFIX:t}.log
  cd "$PREFIX/drive_c/MuTheMatrix" || exit 1
  exec "$RT/wine/bin/wine" MuTheMatrix.exe >"$LOG" 2>&1
fi
CX=${CX_ROOT:-/Applications/CrossOver.app/Contents/SharedSupport/CrossOver}
BOTTLE=${MU_BOTTLE:-MuMatrixKit}
# stale display state after sleep breaks the launcher; restart this (idle) bottle's wineserver
WINEPREFIX="$HOME/Library/Application Support/CrossOver/Bottles/$BOTTLE" "$CX/bin/wineserver" -k 2>/dev/null
sleep 1
LOG=$HOME/Library/Logs/MuTheMatrix-$BOTTLE.log
DBG=(); [ -n "$MU_DEBUGMSG" ] && DBG=(--debugmsg "$MU_DEBUGMSG")
if [ "${MU_FAST_X87:-0}" = 1 ]; then
  [ -x "${MU_TIMEWALKER_DIR:-}/scripts/run-crossover.sh" ] || { echo "MU_FAST_X87=1 needs MU_TIMEWALKER_DIR with scripts/run-crossover.sh" >&2; exit 1; }
  export TIMEWALKER_X87_ONLY=main.exe
  exec "$MU_TIMEWALKER_DIR/scripts/run-crossover.sh" --bottle "$BOTTLE" "${DBG[@]}" --workdir 'C:\MuTheMatrix' 'C:\MuTheMatrix\MuTheMatrix.exe' >"$LOG" 2>&1
fi
exec "$CX/bin/wine" --bottle "$BOTTLE" "${DBG[@]}" --workdir 'C:\MuTheMatrix' 'C:\MuTheMatrix\MuTheMatrix.exe' >"$LOG" 2>&1
