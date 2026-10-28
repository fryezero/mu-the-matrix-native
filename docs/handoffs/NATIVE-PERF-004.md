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
  **not** been integrated. An earlier fetch observed main `23f3e08` (eight later
  merges). This is not a current-main final gate or release.
- No PR, no merge to main. The owner explicitly requested no merge today.
  Strict all-scene 25 Hz acceptance remains open.
- No merge lock is held by this lane. Its queue entry was removed at 14:02
  under the owner's hard-stop instruction. Read the current common brief and
  queue before a future final sequence; append at the tail when ready.
- The eight-run timing matrix and clean build are complete. The current-source
  Mac script passes 1,386 tests with 181 explicit skips across 38 suites, 9/9
  fixtures, and an audit of 1,514 files with zero rejections. The rebuilt candidate
  matches all 2,804 full-frame pairs, 701 per scenario, with successful uploads
  and zero fallback. This WIP gate was outside a final merge sequence.

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
  The current rebuilt candidate additionally passes **2,804/2,804** pairs through
  frame 700, covering all 32 scripted skill events in every scenario.
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
- Current runtime `4bd5d38`, gate head `6787d03`: clean world/client build and the
  complete Mac script pass (1,386 pass, 181 skips, 38 suites; 9/9 fixtures;
  1,514 audited files, zero rejections). The first attempt reached all tests
  and fixtures but rejected absolute Metal log paths in the aggregate. Those
  references were sanitized and the entire script rerun successfully. The rerun
  also executes the headless-object case after the first script builds mu-viewer.

The first integrated paired table lowers mean CPU but fails strict acceptance
in every optimized 80-player scene. Four-job Tormenta repeats passed, while
crowd80 remained inconsistent. Shared-host contention is uncontrolled. Every
unfavorable result remains in the aggregate; warning and strict limits are
unchanged. Do not describe the milestone as complete.

Rejected experiments remain documented: client-array pointer memoization differed
in 98/151 crowd40 frames; scoped thread QoS gave no consistent gain; per-flush
VBOs preserved 604/604 frames but regressed timings with millions of uploads.
None of those production implementations remains. The ordered capture candidate
is a separate implementation; its full matrix and capture-only pair remain WIP
evidence, not all-scene acceptance.

## Resume inputs and exact next step

Private lane input directory:
`~/Documents/MTM/mu-mac-tools/native/scratch/native-perf-004/`.
The `data` directory links to existing objects, language tables and converted GFx
movies in other scratch lanes. Do not delete their targets. The installed root is
`~/Library/Application Support/MuTheMatrix/prefix/drive_c/MuTheMatrix`.
Worktree `evidence` and `tools/python` are untracked borrowed links; never stage.

The eight-run ordered-capture matrix is complete: all warning checks pass, but
strict optimized acceptance passes only crowd40. The retained implementation is
WIP; investigate the remaining 80-player pacing failures. The first next step
is a post-capture sampling profile after frame 650, correlated with the saved
crowd80 tail timings. The capture-only off/on pair measures
24.90/24.96 fps, 27.02/26.04 ms main CPU, and 43.50/40.42 ms frame p99.
Only on passes strict acceptance in this repeat; the full optimized matrix still
fails all three 80-player scenes. The complete table is in the finding. Reproduce with:

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


## Hard-stop cleanup and resume

Keep this worktree and branch. Owned bulk renders, raw reports, C build outputs,
the Rust target cache and the patched Ruffle worktree were removed before handback.
Only the existing data links, one 14 MiB `libmugfx.dylib`, a borrowed pristine
Ruffle link, and a small `resume/` folder remain in lane scratch. Nothing in the
borrowed data/evidence/Python targets is deleted. The library hash is recorded in
the aggregate; it reproduces this checkpoint, not unintegrated main changes.

`resume/` retains the completed gate log (compressed), the long frame hash report,
the previous pre-capture profile (compressed), final capture-only crowd80 timing
inputs (compressed), and `profile-capture.py`. From the worktree, rebuild world
then run that small profiling script with the repo Python for the first next
measurement. It uses the same full-quality scene and samples eight seconds after
frame 650. No post-capture sample has been collected yet.

The Rust `mugfx-shot` helper/cache are removed; rebuild with
`MU_GFX_DEPS="$HOME/Documents/MTM/mu-mac-tools/native/scratch/native-perf-004/deps" sh native/gfx/fetch-ruffle.sh` and
`MU_GFX_DEPS="$HOME/Documents/MTM/mu-mac-tools/native/scratch/native-perf-004/deps" sh native/gfx/build-mugfx.sh` when reproducing
the gate's optional built-binary coverage. Existing cached pristine source is
borrowed through the retained link. Never delete that target.

The owner requires the WIP checkpoint pushed by 14:40 and all agents stopped by
14:45 CDT. No lock or queue slot remains assigned to this lane. A future release
needs a new queue entry, latest-main integration, the full local gate and renewed
full-quality frame/timing acceptance.
