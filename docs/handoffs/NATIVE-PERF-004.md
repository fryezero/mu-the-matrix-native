# NATIVE-PERF-004 — WIP resume handoff

Native-only offline performance work. No original client or launcher was used.
[Finding and before/after tables](../research/native-performance-004.md),
[reviewed aggregate evidence](../research/native-performance-004-summary.json).

## State at the owner's 2026-10-28 hard stop

- Branch: `codex/native-perf-004`, pushed to `origin`; worktree:
  `~/Documents/MTM/worktrees/native-perf-004`.
- Runtime source checkpoint: `4bd5d38`; subsequent checkpoint changes are
  documentation/evidence only unless this section says otherwise.
- Integrated main is `26018b4`, merged in `4f37645`. Later main changes have
  **not** been integrated. A 14:12 fetch observed main `23f3e08` (eight later
  merges). This is not a current-main final gate or release.
- No PR, no merge to main. Strict all-scene 25 Hz acceptance remains open.
- No merge lock is held by this lane. Its queue entry was removed at 14:02
  under the owner's hard-stop instruction. Read the current common brief and
  queue before a future final sequence; append at the tail when ready.
- Latest ordered-capture timing and extended frame/gate results are recorded
  below when completed. Never infer a new candidate's proof from an old one.

## Retained implementation

Character-local animation/skinning uses four joined, strided dispatch jobs.
Placement, names, RNG, effects, GL and draw order stay on the ordered thread.
Small lists/non-Apple retain serial execution. `MU_PERF_004_POSE_TASKS` and the
benchmark's `--pose-tasks` are diagnostics; no shared pose/equipment cache exists.

A model-owned exact topology proof compares triangle bytes and all index bounds
on every hit. Fully proved models avoid redundant scans and edge-view allocation.
Changed/invalid inputs and allocation failures retain the existing checked path.
Transform/light/color/alpha are rebuilt normally. Model close frees the cache.

The latest WIP candidate captures state/draw commands inside the existing GL
batch-session contract. It copies packed vertices into immutable chunks, uploads
once per chunk, then replays all commands in original order. Public flush/end
remain submission barriers. Allocation/upload failure drains the captured prefix
and preserves rendering through client arrays. Context-owned buffers are deleted
before context destruction; foreign array-buffer bindings are restored. No Ruffle
movie/bridge/nameplate or quality/acceptance threshold changed.

`MU_PERF_004_BASELINE=1` disables all three changes on the same binary.
`--perf-004-vbo-baseline` isolates command capture from the other changes.
Tools require successful uploads and zero fallback in the optimized path.
Process CPU includes workers; main CPU, GL and Metal intervals overlap and must
not be added. GPU busy time remains unmeasured.

## Verification and limits

- Native world/client builds pass on `4bd5d38`.
- Three targeted GL tests pass, including forced upload and command-allocation
  failures, chunk crossings, a public flush barrier and foreign binding restore.
  All three wrong-UV/binding/blend mutants are caught.
- Ordered-capture preflight: **604/604** full-frame pairs (151 per scenario),
  successful uploads, zero fallback. This includes GFx, the map, effects, models,
  nameplates and combat; deterministic AS2 time and single-buffer presentation.
- Pose tests compare every mapped model window plus saved player/attachment
  bones, serial versus 1/4/8/80 requested jobs, over changing states, hidden and
  missing models; counts 0/1/7/8/9 cover the worker threshold.
- Topology host: 12 checks and 2/2 stale-byte/count mutants caught. The pinned
  mesh stream/table comparison has 247 cases and 2/2 stream mutants caught.
- Fresh original-instruction oracle: 843 draw cases, 247 pinned cases, 13,529
  texture names; zero mismatches, all draw branches, 4/4 controls caught.
  Fourteen installed models are explicit exclusions. This oracle covers the
  unchanged reconstructed routines, not the new native delivery mechanism.
- First integrated lock-held gate (`4f37645`): 38 suites, 1,566 invocations,
  1,384 passes and 182 explicit skips; 9/9 fixtures; 1,514 audited files,
  zero rejections. Its 2,804/2,804 frame pairs cover all 32 scripted skill events.
  That gate predates bounded jobs and both VBO candidates.

The first integrated paired table lowers mean CPU but fails strict acceptance
in every optimized 80-player scene. Four-job Tormenta repeats passed, while
crowd80 remained inconsistent. Shared-host contention is uncontrolled. Every
unfavorable result remains in the aggregate; warning and strict limits are
unchanged. Do not describe the milestone as complete.

Rejected experiments remain documented: client-array pointer memoization differed
in 98/151 crowd40 frames; scoped thread QoS gave no consistent gain; per-flush
VBOs preserved 604/604 frames but regressed timings with millions of uploads.
None of those production implementations remains. The ordered capture candidate
is a separate implementation and needs its own timing decision.

## Resume inputs and exact next step

Private lane input directory:
`~/Documents/MTM/mu-mac-tools/native/scratch/native-perf-004/`.
The `data` directory links to existing objects, language tables and converted GFx
movies in other scratch lanes. Do not delete their targets. The installed root is
`~/Library/Application Support/MuTheMatrix/prefix/drive_c/MuTheMatrix`.
Worktree `evidence` and `tools/python` are untracked borrowed links; never stage.

The eight-run ordered-capture matrix is complete: all warning checks pass, but
strict optimized acceptance passes only crowd40. The retained implementation is
WIP; isolate capture with its disable switch and investigate the remaining
80-player pacing failures. The complete before/after table is in the finding. Reproduce with:

```sh
./tools/python/bin/python native/tools/compare_stress.py \
  --game-root "$HOME/Library/Application Support/MuTheMatrix/prefix/drive_c/MuTheMatrix" \
  --data "$HOME/Documents/MTM/mu-mac-tools/native/scratch/native-perf-004/data" \
  --gfx-lib "$HOME/Documents/MTM/mu-mac-tools/native/scratch/native-perf-004/libmugfx.dylib" \
  --out "$HOME/Documents/MTM/mu-mac-tools/native/scratch/native-perf-004/resume-frames" \
  --frames 701
```

Build with `make -C native world client`. Timing uses `native/tools/bench_stress.py`
with the same three input arguments, a fresh external `--out`, `--gpu-timing`,
60 seconds per scene, and normal asynchronous presentation. Add
`--perf-004-baseline` for the full before path, or `--perf-004-vbo-baseline` for
capture-only ablation. Do not overlap timing with this lane's builds/tests/profiles.

Once targets are met, queue fairly, acquire the lock, merge latest main keeping
both lanes' hooks/rows, clean-build, complete `bash scripts/local-macos-ci.sh`,
repeat full frames and timing on the integrated source, then PR/merge. Release
only this lane's lock. After merge delete all owned scratch/build outputs,
worktree and local branch. The earlier merge begun after a failed lock acquisition
was immediately aborted; the recorded `4f37645` integration/gate was lock-held.
