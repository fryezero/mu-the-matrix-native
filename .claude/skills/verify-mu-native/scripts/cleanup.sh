#!/bin/sh
# Tear down what a run created, keeping its proof.
#
#   .claude/skills/verify-mu-native/scripts/cleanup.sh RUN
#
# Stops only the processes listed in RUN/pids (started by run-tool.sh; never by name), removes the
# synthetic root, the offline session files and tmp/, and keeps RUN/proof and RUN/run.json.
set -u
RUN=${1:-}
if [ -z "$RUN" ] || [ ! -d "$RUN" ]; then echo "usage: cleanup.sh RUN (an existing verify-runs directory)" >&2; exit 2; fi
case "$RUN" in */verify-runs/*) ;; *) echo "cleanup: refusing to clean $RUN: not under verify-runs/" >&2; exit 2;; esac
for p in $(cat "$RUN/pids" 2>/dev/null); do
  if kill -0 "$p" 2>/dev/null; then kill "$p" 2>/dev/null && echo "stopped pid $p"; fi
done
rm -rf "$RUN/root" "$RUN/tmp" "$RUN/pids" "$RUN/pids.next" "$RUN/session.txt" "$RUN/servers.txt" "$RUN/characters.txt"
count=$(find "$RUN/proof" -type f 2>/dev/null | wc -l | tr -d ' ')
echo "cleaned $RUN; kept proof/ ($count files) and run.json"
