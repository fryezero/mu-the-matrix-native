# NATIVE-PERF-004

## Checkpoint, 2026-10-28

Resumed the existing uncommitted worktree at main `237f094`. Native-only scope:
character-local pose workers, model-owned topology proof, process CPU telemetry,
and a hash-only full-frame comparison tool. No original client or launcher used.

The native world/client build passes. Two PERF-004 tests and sixteen stress tests
pass, including 247 mesh stream/table cases, two stream mutants and two topology
mutants. Serial and parallel character runs compare every mapped model region,
saved player bones and attachment bones over 32 frames with changing states.
All 604 full-quality deterministic frame pairs, frames 0 through 150 in each
of four workloads, are byte-identical. Paired window timings are in progress. The 25 Hz target is not yet claimed.

The previous agent's steady samples at 10:21/10:22 identify character drawing,
GL submissions, character skinning and GFx as remaining costs. Earlier timings
are retained in the lane scratch directory pending a reviewed final summary.

Local scratch: `~/Documents/MTM/mu-mac-tools/native/scratch/native-perf-004/`.
Private inputs and generated outputs must not be committed. Final merge gate,
latest-main integration, reviewed measurements and cleanup remain.
