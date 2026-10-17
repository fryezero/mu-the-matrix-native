#!/bin/zsh
# Launch Mu The Matrix from a bottle created by setup-mu-mac.sh (default bottle MuMatrixKit).
# The Desktop .command file written by the setup runs this script with MU_BOTTLE set.
#
#   MU_BOTTLE          bottle to start (default MuMatrixKit)
#   MU_FAST_X87=1      route main.exe through an existing rosetta-timewalker build (default 0)
#   MU_TIMEWALKER_DIR  that checkout/build (only with MU_FAST_X87=1)
#   CX_ROOT            CrossOver runtime directory
#   MU_DEBUGMSG        passed to wine --debugmsg
#
# It refuses a second instance (one client at a time, across all bottles) and restarts the bottle's idle
# wineserver first, because stale display state after sleep breaks the launcher. It starts the original
# launcher MuTheMatrix.exe in C:\MuTheMatrix; log: ~/Library/Logs/MuTheMatrix.log.
CX=${CX_ROOT:-/Applications/CrossOver.app/Contents/SharedSupport/CrossOver}
BOTTLE=${MU_BOTTLE:-MuMatrixKit}
if pgrep -f 'C:\\MuTheMatrix\\main.exe' >/dev/null || pgrep -f 'C:\\MuTheMatrix\\MuTheMatrix.exe' >/dev/null; then
  osascript -e 'display dialog "Mu The Matrix is already running. Close the game and launcher first, then launch again." buttons {"OK"} with title "Mu The Matrix"' >/dev/null 2>&1
  exit 1
fi
# stale display state after sleep breaks the launcher; restart this (idle) bottle's wineserver
WINEPREFIX="$HOME/Library/Application Support/CrossOver/Bottles/$BOTTLE" "$CX/bin/wineserver" -k 2>/dev/null
sleep 1
LOG=$HOME/Library/Logs/MuTheMatrix.log
DBG=(); [ -n "$MU_DEBUGMSG" ] && DBG=(--debugmsg "$MU_DEBUGMSG")
if [ "${MU_FAST_X87:-0}" = 1 ]; then
  [ -x "${MU_TIMEWALKER_DIR:-}/scripts/run-crossover.sh" ] || { echo "MU_FAST_X87=1 needs MU_TIMEWALKER_DIR with scripts/run-crossover.sh" >&2; exit 1; }
  export TIMEWALKER_X87_ONLY=main.exe
  exec "$MU_TIMEWALKER_DIR/scripts/run-crossover.sh" --bottle "$BOTTLE" "${DBG[@]}" --workdir 'C:\MuTheMatrix' 'C:\MuTheMatrix\MuTheMatrix.exe' >"$LOG" 2>&1
fi
exec "$CX/bin/wine" --bottle "$BOTTLE" "${DBG[@]}" --workdir 'C:\MuTheMatrix' 'C:\MuTheMatrix\MuTheMatrix.exe' >"$LOG" 2>&1
