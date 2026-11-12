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

At this checkpoint all 64 selected validators passed without mutants at `a15ef265` in 934.54 s,
1,023,171 reported cases plus worlds_o, whose report has no case total. The selection includes every fallback.
Portable affected suites passed in 427.26 s including selection, 356.5 s test wall: 1,634 tests,
1,355 passed / 279 expected skips, zero failures/errors. Private native selection is 162 work items, so
**8d reduced** applies: run the changed production host module with the canonical private environment.
The rebuilt after binary SHA-256 is `619be48504bcca387c1fd2b17d97ad1fb062a51ed52b56fff92d7442aaca7044`.

Private modules now pass: production host 1/1 in 0.31 s; producer 4/4, including 1,000 original cases,
in 0.90 s. Initial image outputs lacked the explicit demo-name argument and are being replaced, not counted
as final proof. Both corrected default sweeps and captured-clock views have finished. The corrected close-ups
are queued by the resource guard. The active foreground pipeline is `safe-renders.py` in this lane's scratch.
It uses `--hero-name Preview` and MU_GFX_PUBLIC_DEMO=1 for both binaries.

Next: finish `safe-renders.py`, rerun the local `summarize.py`, inspect the corrected close-ups, then run
`finalize-docs.py` once and check its numbers. Finish audit/latest-main check, final commit/push, PR/link,
ready-prs line and cleanup. Do not regenerate already-valid default sweeps or recompile mutants.
If interrupted, use `validators.log` and `verify-runs/lane-validators` to preserve completed checks. Do not
recompile the 27 completed mutants. All these local paths are under the lane's own scratch directory unless
repository-relative.
Local scratch: `~/Documents/MTM/mu-mac-tools/native/scratch/render-worlds-inner-002/`.

## Scope and what draws now

Pending final checks. Elbeland includes particles, owned smoke and posed-bone glows. Swamp includes particles,
owned smoke and five existing lightning subtypes. Elbeland 0x3a's unwritten stack colour stays an explicit
refusal unless the comparison supplies an authored colour input. No event-state model is added.
