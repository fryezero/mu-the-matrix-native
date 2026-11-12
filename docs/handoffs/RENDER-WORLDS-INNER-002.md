# RENDER-WORLDS-INNER-002

Branch `codex/render-worlds-inner-002`, from main `d4af71dd`. Offline only, no subagents.

## WIP checkpoint

Owner update: stop by 02:30 on 2026-11-12. If not PR-ready at 02:15, push WIP by 02:30 and stop.

Done: full task/common briefs read; isolated worktree and private input links; authored Elbeland 51 and Swamp
of Calmness 56 producers and production adapter; initial 1,000 instruction cases pass. Root build passes, 30.06 s; expanded production host passes, 1.17 s. Baseline binary rebuilt
from `d4af71dd` with `make -C native -j4 world`, SHA-256
`4954601057b7ee7976c787157b321703d40c65dba68c46901b08d22adb1be76c`.
Baseline default tours and affected clock views recorded once in this lane's local scratch directory.

Full comparison: 5,000 cases, zero mismatches/stops; 27/27 compiled mutants caught, minimum 46 detections.
The first eight compiled before a nonunique anchor stopped setup, 49.78 s; the remaining nineteen ran after
the anchor was narrowed, 86.64 s. No successful mutant was recompiled.

Left: affected checks, after renders, final research/status updates,
latest-main integration, audit, PR and ready queue. No readiness claim yet.

At this checkpoint the 64 selected validators are running without mutants at `a15ef265`, with no failure
reported so far. The selection includes every fallback. Private native selection is 162 work items, so
**8d reduced** applies: run the changed production host module with the canonical private environment.
The rebuilt after binary SHA-256 is `619be48504bcca387c1fd2b17d97ad1fb062a51ed52b56fff92d7442aaca7044`.

Next: finish the foreground `checks.py` pipeline, which runs affected portable suites and focused private
modules after validators. Then run the lane's `renders.py`, inspect the PNGs and record identity/score results.
If interrupted, use `validators.log` and `verify-runs/lane-validators` to preserve completed checks. Do not
recompile the 27 completed mutants. All these local paths are under the lane's own scratch directory unless
repository-relative.
Local scratch: `~/Documents/MTM/mu-mac-tools/native/scratch/render-worlds-inner-002/`.

## Scope and what draws now

Pending final checks. Elbeland includes particles, owned smoke and posed-bone glows. Swamp includes particles,
owned smoke and five existing lightning subtypes. Elbeland 0x3a's unwritten stack colour stays an explicit
refusal unless the comparison supplies an authored colour input. No event-state model is added.
