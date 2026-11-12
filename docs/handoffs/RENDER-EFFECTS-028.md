# RENDER-EFFECTS-028

## WIP checkpoint

Branch `codex/render-effects-028`, base `d4af71dd`. Worktree
`~/Documents/MTM/worktrees/render-effects-028`.

Done: static aura consumer audit, isolated `aura_fx` reconstruction, opt-in
hero fixture adapter and original-instruction comparator authored. Baseline
world built before native adapter edits; default sweep running. Nothing is
PR-ready yet. No live client or installed app touched.

Original comparison: 4,390 cases, zero mismatches, 18/18 compiled C mutants
caught without original-machine stops, 49.71 s. Baseline default sweep: 230
artifacts across 46 captures, 121.17 s; binary SHA-256
`4954601057b7ee7976c787157b321703d40c65dba68c46901b08d22adb1be76c`.
Native root build passed, 11.36 s; rebuilt world passed, 5.64 s. Four
private native tests passed in 9.33 s, including both buffs drawing, expiry,
repeat identity, unchanged HP/requests and existing bitmap/combat consumers.
Portable affected suites are running; 56 affected validators remain queued.

Left: debug comparisons, compiled mutants, native fixture pixels, affected
checks, final sweep, research/status docs, merge current main and publish PR.
Next: inspect `scratch/render-effects-028` under the shared native tools for
baseline sweep and build outputs, check resource guard, run the small comparator.
