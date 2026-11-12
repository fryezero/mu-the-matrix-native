# RENDER-WORLDS-INNER-002

Branch `codex/render-worlds-inner-002`, from main `d4af71dd`. Offline only, no subagents.

## WIP checkpoint

Done: full task/common briefs read; isolated worktree and private input links; authored Elbeland 51 and Swamp
of Calmness 56 producers and production adapter; initial 1,000 instruction cases pass. Root build passes, 30.06 s; expanded production host passes, 1.17 s. Baseline binary rebuilt
from `d4af71dd` with `make -C native -j4 world`, SHA-256
`4954601057b7ee7976c787157b321703d40c65dba68c46901b08d22adb1be76c`.
Baseline default tours and affected clock views recorded once in this lane's local scratch directory.

Left: full comparisons/mutants, affected checks, after renders, final research/status updates,
latest-main integration, audit, PR and ready queue. No readiness claim yet.

Next: run the new validator's full comparisons and compiled mutants, then select affected checks.
Local scratch: `~/Documents/MTM/mu-mac-tools/native/scratch/render-worlds-inner-002/`.

## Scope and what draws now

Pending final checks. Elbeland includes particles, owned smoke and posed-bone glows. Swamp includes particles,
owned smoke and five existing lightning subtypes. Elbeland 0x3a's unwritten stack colour stays an explicit
refusal unless the comparison supplies an authored colour input. No event-state model is added.
