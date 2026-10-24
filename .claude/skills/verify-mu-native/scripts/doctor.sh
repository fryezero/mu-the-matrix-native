#!/bin/sh
# Read-only health check: is this checkout (and, with RUN, this run) worth driving?
#
#   .claude/skills/verify-mu-native/scripts/doctor.sh [RUN]
#
# Prints one line per check. Exit 0 with "DOCTOR OK" when every required check passes, exit 1 with
# "DOCTOR FAIL" otherwise. WARN lines do not fail the doctor; they explain results that may look wrong.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../../../.." && pwd)
RUN=${1:-}
fail=0
ok()   { echo "ok    $*"; }
warn() { echo "WARN  $*"; }
bad()  { echo "FAIL  $*"; fail=1; }

for b in mu-client mu-world mu-walk mu-viewer mu-render mu-proto mu-terrain; do
  if [ -x "$REPO/native/build/$b" ]; then ok "native/build/$b"; else bad "native/build/$b missing: make -C native && make -C native viewer"; fi
done

if [ -x "$REPO/native/build/mu-client" ]; then
  newest=$(find "$REPO/native" "$REPO/reconstructed" \( -name '*.c' -o -name '*.h' \) -not -path '*/build/*' \
           -newer "$REPO/native/build/mu-client" 2>/dev/null | head -3 | tr '\n' ' ')
  if [ -n "$newest" ]; then warn "sources newer than native/build/mu-client, rebuild first: $newest"; else ok "build newer than every native/ and reconstructed/ source"; fi
fi

PY="$REPO/tools/python/bin/python"
if [ -x "$PY" ] && "$PY" -c "import sys; sys.path.insert(0, '$REPO/native/tests'); import native_fixtures, PIL" 2>/dev/null; then
  ok "tools/python imports native/tests fixtures and Pillow"
else
  bad "tools/python missing or incomplete: python3 -m venv tools/python && tools/python/bin/python -m pip install -r tools/requirements-lock.txt"
fi

if command -v sdl2-config >/dev/null 2>&1; then ok "sdl2-config $(sdl2-config --version)"; else bad "sdl2-config missing: brew install sdl2"; fi

if pgrep -qf 'main\.exe' 2>/dev/null; then
  warn "a Wine client (main.exe) is running: this skill never reads, signals or launches it"
else
  ok "no Wine client process visible"
fi

if [ -n "$RUN" ]; then
  if [ -f "$RUN/run.json" ]; then ok "run.json present"; else bad "$RUN/run.json missing: create runs with scripts/new-run.sh"; fi
  head=$(git -C "$REPO" rev-parse HEAD)
  rec=$(sed -n 's/.*"commit": "\([0-9a-f]*\)".*/\1/p' "$RUN/run.json" 2>/dev/null)
  if [ "$head" = "$rec" ]; then ok "run commit matches HEAD $(echo "$head" | cut -c1-7)"; else warn "run commit $(echo "$rec" | cut -c1-7) differs from HEAD $(echo "$head" | cut -c1-7)"; fi
  for f in root/Data/World1/EncTerrain1.map root/Data/World94/EncTerrain94.map root/Data/World95/EncTerrain95.map \
           root/Data/Player/Player.bmd root/Data/Verify/synthetic1_v12.bmd session.txt; do
    if [ -f "$RUN/$f" ]; then ok "$f"; else bad "$RUN/$f missing (cleanup already ran? start a new run)"; fi
  done
  live=''
  for p in $(cat "$RUN/pids" 2>/dev/null); do kill -0 "$p" 2>/dev/null && live="$live $p"; done
  if [ -z "$live" ]; then ok "no tool from this run still running"; else warn "tools from this run still running:$live (cleanup.sh stops them)"; fi
  if [ -x "$REPO/native/build/mu-viewer" ] && [ -f "$RUN/root/Data/Verify/synthetic1_v12.bmd" ]; then
    out=$(MU_NATIVE_SETTINGS_DIR="$RUN/tmp/settings" "$REPO/native/build/mu-viewer" "$RUN/root/Data/Verify/synthetic1_v12.bmd" \
          --headless --backend gl --width 16 --height 16 2>&1)
    renderer=$(printf '%s\n' "$out" | sed -n 's/^GL renderer: //p')
    case "$out" in
      *'"backend": "gl"'*) ok "offscreen GL context (${renderer:-renderer unknown})";;
      *) bad "offscreen GL failed: $(printf '%s' "$out" | tr '\n' ' ' | cut -c1-200)";;
    esac
  fi
else
  warn "no RUN given: the synthetic root and the offscreen GL context were not checked"
fi

if [ $fail -eq 0 ]; then echo "DOCTOR OK"; exit 0; else echo "DOCTOR FAIL"; exit 1; fi
