# NATIVE-PERF-004 — WIP resume handoff

Native-only offline performance work. No original client or launcher was used.
[Finding and before/after tables](../research/native-performance-004.md),
[reviewed aggregate evidence](../research/native-performance-004-summary.json).

## Final state (2026-10-28 resume by Claude Opus 5.5)

- Branch `codex/native-perf-004`, merged to main through the PR named in
  `docs/status.md` after the locked final sequence (latest main merged, full
  Mac gate, `gh pr merge --merge`). Worktree, local branch and lane scratch are
  removed after merge.
- Strict all-scene 25 Hz acceptance is **not** met: only crowd40 passes. This
  merge ships the measured CPU reductions and the profile; pacing moves to
  NATIVE-PERF-005 (exact next measurements below).
- Resume work: a post-frame-650 crowd80 sample (4,559 main-thread samples)
  classifies the 1280x800 limit as main-thread CPU (draw submission and logic),
  with GL driver semaphore waits in the terrain flush and swap as a secondary
  cost and GPU-bound time added at retina. Slow frames grow in every phase at
  once, which points at host contention or core/frequency placement rather than
  one hot routine.
- One measured fix: `mu_session_sim_end` (about 4% of main samples, self time)
  compared every replicated session byte after each lease in a byte loop. Equal
  zones now pass one `memcmp`; a change still runs the unchanged byte loop and
  reports the same first byte, then aborts. `MU_PERF_004_BASELINE=1` restores
  the byte loop. A new test checks identical audit lines in both modes over
  three scenarios; a skip-everything mutant is caught.
- Controlled-clock full-frame pairs: 2,804/2,804 identical on the branch
  (`b65d56a`) and 2,804/2,804 on the source integrated with main `fa63719`.

### Before/after fps per scene (integrated `fdad6c1`, same binary)

| Scene | Before fps (r1 / r2) | After fps (r1 / r2) | Main CPU ms before → after (r1) | Strict after |
|---|---:|---:|---:|---|
| crowd40 | 24.99 / - | 24.93 / - | 25.97 → 22.19 | pass |
| crowd80 | 24.56 / 20.29 | 23.18 / 20.21 | 36.82 → 32.78 | fail |
| tormenta80 | 22.93 / 18.85 | 24.78 / 20.83 | 40.24 → 32.55 | fail |
| retina80 | 15.52 / 16.07 | 20.37 / 18.70 | 56.76 → 40.34 | fail |

Repeat 1 started at load 3.6-5.2, repeat 2 at 8-13 (other lanes' Python/clang
jobs; no Wine client). Neither host was quiet; tails track host load. The
capture-only pair at the 14:45 stop measured 24.90/24.96 fps. Full tables,
logic times and p99s are in the [finding](../research/native-performance-004.md).

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

## Next: NATIVE-PERF-005

Start from a fresh baseline on the merged main, on a quiet host (load under 2,
no other lane's builds/tests/Wine), all four scenes in both modes, two
counterbalanced repeats, with `native/tools/bench_stress.py --gpu-timing
--seconds 60` and `--perf-004-baseline` for the before path. Then measure, in
order: (1) `powermetrics` CPU-cluster residency/frequency alongside one crowd80
run, correlated per frame with >42 ms frames; (2) driver submission inside
remote-player draws (texture-bind flushes) and the terrain/swap semaphore
waits; (3) GFx advance (Ruffle mouse picking with a stationary pointer), the
per-draw `getenv` in `mu_scene_draw_model` and linear `mu_item_find`;
(4) a GPU-side measurement for retina80 before any CPU change there.
Inputs are the same as before: the converted GFx movies, language tables and
objects under other lanes' scratch (`gfx3/movies`, `quest2/lang`,
`objects/live/plain`) plus a `libmugfx.dylib` built with
`native/gfx/build-mugfx.sh`. This lane's own scratch is deleted.
