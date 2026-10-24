#!/bin/sh
# Run one native tool inside a run, isolated, with its evidence captured.
#
#   .claude/skills/verify-mu-native/scripts/run-tool.sh RUN NAME TOOL [ARGS...]
#
# TOOL is a program under native/build (mu-client, mu-world, mu-walk, mu-viewer, mu-render, mu-proto,
# mu-terrain). The tool runs with MU_NATIVE_SETTINGS_DIR=RUN/tmp/settings so it never touches
# ~/Library/Application Support/MuTheMatrixNative; its pid is listed in RUN/pids while it runs; the
# command line, stdout, stderr and exit code are stored as RUN/proof/NAME.cmd .stdout .stderr .exit.
# The directory named after --out-dir and the parent of an --out path are created first (the windowed
# programs do not create them). stdout is echoed; the exit code is the tool's.
set -u
if [ $# -lt 3 ]; then echo "usage: run-tool.sh RUN NAME TOOL [ARGS...]" >&2; exit 2; fi
RUN=$1; NAME=$2; TOOL=$3; shift 3
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../../../.." && pwd)
BIN="$REPO/native/build/$TOOL"
if [ ! -x "$BIN" ]; then echo "run-tool: $BIN missing (make -C native && make -C native viewer)" >&2; exit 127; fi
mkdir -p "$RUN/proof" "$RUN/tmp/settings"
prev=''
for a in "$@"; do
  case "$prev" in
    --out-dir) mkdir -p "$a" ;;
    --out) mkdir -p "$(dirname "$a")" ;;
  esac
  prev=$a
done
{ printf '%s' "$TOOL"; for a in "$@"; do printf ' %s' "$a"; done; echo; } > "$RUN/proof/$NAME.cmd"
MU_NATIVE_SETTINGS_DIR="$RUN/tmp/settings" "$BIN" "$@" > "$RUN/proof/$NAME.stdout" 2> "$RUN/proof/$NAME.stderr" &
PID=$!
echo "$PID" >> "$RUN/pids"
wait "$PID"
CODE=$?
echo "$CODE" > "$RUN/proof/$NAME.exit"
if [ -f "$RUN/pids" ]; then grep -v "^$PID\$" "$RUN/pids" > "$RUN/pids.next" 2>/dev/null; mv "$RUN/pids.next" "$RUN/pids"; fi
cat "$RUN/proof/$NAME.stdout"
exit $CODE
