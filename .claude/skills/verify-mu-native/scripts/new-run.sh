#!/bin/sh
# Create a fresh verification run with its own synthetic game root.
#
#   RUN=$(.claude/skills/verify-mu-native/scripts/new-run.sh LABEL)
#
# Writes verify-runs/<date>-<time>-LABEL/ (ignored by git):
#   root/ session.txt servers.txt characters.txt   scratch: synthetic game root and offline session
#   tmp/settings/                                  scratch: MU_NATIVE_SETTINGS_DIR for every drive
#   proof/                                         evidence: kept by cleanup.sh
#   run.json                                       commit, dirty flag, binary digests, creation time
# Prints the run directory on stdout; everything else goes to stderr.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../../../.." && pwd)
PY="$REPO/tools/python/bin/python"
LABEL=$(printf '%s' "${1:-run}" | tr -c 'A-Za-z0-9_.-' '-')
RUN="$REPO/verify-runs/$(date +%Y%m%d-%H%M%S)-$LABEL"
if [ ! -x "$PY" ]; then
  echo "new-run: $PY missing. Create it: python3 -m venv tools/python && tools/python/bin/python -m pip install -r tools/requirements-lock.txt" >&2
  exit 2
fi
mkdir -p "$RUN/proof" "$RUN/tmp/settings"
"$PY" "$HERE/make-root.py" "$RUN" >&2
dirty=false
[ -n "$(git -C "$REPO" status --porcelain)" ] && dirty=true
{
  printf '{\n  "created": "%s",\n  "label": "%s",\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$LABEL"
  printf '  "commit": "%s",\n  "dirty": %s,\n' "$(git -C "$REPO" rev-parse HEAD)" "$dirty"
  printf '  "macos": "%s",\n  "binaries": {' "$(sw_vers -productVersion 2>/dev/null || echo unknown)"
  sep=''
  for b in mu-client mu-world mu-walk mu-viewer mu-render mu-proto mu-terrain; do
    f="$REPO/native/build/$b"
    if [ -x "$f" ]; then
      printf '%s\n    "%s": "%s"' "$sep" "$b" "$(shasum -a 256 "$f" | cut -c1-64)"
    else
      printf '%s\n    "%s": null' "$sep" "$b"
    fi
    sep=','
  done
  printf '\n  }\n}\n'
} > "$RUN/run.json"
echo "$RUN"
