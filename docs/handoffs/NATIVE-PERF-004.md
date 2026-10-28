# NATIVE-PERF-004

Native-only offline performance work. No original client or launcher used.
[Finding and measurements](../research/native-performance-004.md),
[aggregate evidence](../research/native-performance-004-summary.json).

## Resume checkpoint, 2026-10-28

The interrupted work at main `237f094` was reviewed, built, tested and pushed.
The retained runtime has joined character-local pose workers and model-owned
exact topology validation. Fully proved models avoid edge-view allocation.
Process CPU telemetry includes worker CPU separately from main-thread CPU.
The benchmark records `--perf-004-baseline`; `compare_stress.py` checks every
full-frame hash without writing bulk PNGs. No quality or acceptance limit changed.

Verified:
- Native world/client builds pass. Three PERF-004 and sixteen stress tests pass;
  four edge tests pass with one explicit private-corpus skip.
- Initial 604/604 full-frame pairs and allocation-path 604/604 pairs match.
  Frames 0..150 include all four workloads, GFx, combat, names and the map.
- 247 pinned mesh stream/table cases match, with 2/2 stream and 2/2 topology
  mutants caught. Serial/parallel runs compare every mapped model window and
  saved attachment/player bone output over changing states, hidden/missing
  models, empty/small lists and worker thresholds.
- Fresh instruction oracle: 843 draw cases, 247 pinned cases, 13,529 texture
  names; zero mismatches, every draw branch reached, 4/4 controls caught.
  Fourteen installed models are explicit exclusions. Runtime math/mesh routines
  are unchanged by intervening main commits checked so far.
- Fresh baseline and optimized sampling profiles are summarized in the finding.

The initial 60-second paired matrix fails strict acceptance in every optimized
scene. Lower mean CPU cost does not close the 25 Hz goal. Shared-host contention
is uncontrolled. Earlier unfavorable observations are retained in the summary.

A GL client-array pointer memoization experiment was committed as a checkpoint,
then rejected: the synthetic GL test passed but 98/151 full crowd40 frames differed.
It and its experiment-only tests are removed. Current runtime equals `6ba4690`;
`c68f68b` records the rejection and preserves its measurements. No GL pointer or
state setup optimization remains.

## Next sequence

Wait for the common merge lock, acquire it with a standalone checked command,
merge latest origin/main, resolve conflicts preserving both lanes, then run the
full local Mac gate and the final integrated frame/timing matrix. The earlier
attempt to merge locally after a failed lock acquisition was immediately aborted;
no PR or main merge occurred. Never repeat that command-chain error.

Known integration conflicts against then-main `3162017`: keep all upstream
status/handoff rows and our own row. In `native/world/world_tool.c`, keep all
RENDER-TIME-001 sampling hooks, adding only `!getenv("MU_PERF_HASH_ONLY")` around
PNG encoding/writing when `save` is true. Hashing, drawing, readback and sampling
must stay active. The path/hash buffers are initialized empty already.

Private lane scratch is `~/Documents/MTM/mu-mac-tools/native/scratch/native-perf-004/`.
It contains `data`, the built `libmugfx.dylib`, original and resumed profiles,
all paired reports, frame reports and the oracle. Existing `profile.py` and
benchmark command JSON name the local installed input. Do not commit inputs,
raw reports, snapshots or images. Worktree `evidence` and `tools/python` are
untracked local links; never stage them.

After the lock-held gate and reviewed final evidence, create/merge the PR,
release only our lock, delete the entire lane scratch/render trees and build
outputs, then remove the worktree and local branch. Update this handoff with
final counts and limitations before publication. Keep no new large local input.
