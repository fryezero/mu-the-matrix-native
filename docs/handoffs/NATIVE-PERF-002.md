# NATIVE-PERF-002

Ordered player batching, direct corner delivery and bounded scratch storage are implemented. The strict
25 fps target remains open in the full 80-player scenes. See [the finding](../research/native-performance-stress.md)
for methods, before/after metrics, workload integrity and timing limitations.

## Scope

Owned worktree and branch only. No live client, launcher, wire/protection work or captured stat changes.
`mu-world`, `mu-client` and the Preview bundle share the optimized core/runtime. The extreme timing matrix
measures mu-world, not a separate Preview autoplay performance claim. All nameplates are admitted; particle
creation, drops/overflow, inventory models and actual GFx/map workloads are checked before accepting a run.

Minimal integration fixes: only open the remote-player batch when its session exists, allow all crowd
nameplates, and stop the Native Data guard interpreting long script/walk/wheel text as filesystem paths.
Existing owner Native Data was not changed. Validation uses a scratch clone with a build-pinned manifest.

## Checks

Final check totals and extended timing results are being collected. The earlier Mac gate passed 1,355 tests,
157 explicit skips, plus fixtures, viewer, readers and audit. Nine private PERF-001 checks pass after the
batch-boundary fix. Twelve merged-scene before/after renders match exactly at frames 0/60/120, including
the 3456x2160 target. The literal mesh-draw comparison passes 14,619 cases with four negative controls and
unchanged pinned stream groups. These counts will be reconciled with the completed validator runner.

## Local artifacts

All private files stay outside git under `~/Documents/MTM/mu-mac-tools/native/`:

- `scratch/native-perf-002/`: commands, reports, profiles, logs, fresh validated data copy and bundle.
- `renders/native-perf-002/merged-renders/`: the twelve exact frame comparisons.
- `scratch/native-perf-002/validators/`, `validators-new/`, `validators-path/`: original-code comparisons.

## Next

Finish extended measurements and checks, merge the latest main, then open/merge the PR and remove the
owned worktree. The 25 fps target needs further GFx/character profiling and verified caching. No quality
reduction, incomplete cache, lost effect, or hidden missing-name result is accepted as success.
