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
It and its experiment-only tests are removed. The PERF-004-authored runtime equals `6ba4690`;
`c68f68b` records the rejection and preserves its measurements. No GL pointer or
state setup optimization remains.

## Integrated checkpoint

Latest main `26018b4` is merged in `4f37645`, under the lane's merge lock acquired
at 11:57 on 2026-10-28. Both lanes' status lines and Makefile targets are kept.
The world tool retains every temporal sampling hook and suppresses only PNG
encoding/writing in hash-only mode. No upstream behavior is discarded.

The full local macOS gate passes: 38 suites, 1,566 test invocations comprising
1,384 passes and 182 explicit skips; 9/9 fixture scenarios; repository audit
1,514 files, zero rejected. Native world/client are built from this source.
The 701-frame comparison passes all 2,804 pairs. The eight 60-second timing
runs in `final-paired/` pass warning limits but strict acceptance fails in all
three optimized 80-player scenes. Mean CPU falls; tails regress. The finding and
aggregate summary retain every result. No PR is opened on this result.

The final sequence is aborted and the lane's lock is released. Next test a
bounded pose-worker team, verify model buffers and frames, then reacquire the
lock for current-main integration and the complete final sequence. The earlier
uncommitted merge after a failed lock acquisition was aborted; the actual
integration and gate above were correctly lock-held.

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

## Bounded-team checkpoint

The candidate now bounds poses to four strided jobs. Three focused tests pass
with serial and 1/4/8/80-job requests, and 604/604 new preflight frames match.
The team ablations lower process CPU but do not consistently fix pacing.
Tormenta passes strict acceptance for both 4 and 80 jobs; crowd80 still fails
with 1/2/4/80 jobs in the current repeats. Reports are `team-paired/` and
`team-repeat/`; the aggregate summary retains all results. Next investigate
scoped main-render scheduling before claiming the target.

The updated common brief was reread. The lane is queued after RENDER-EFFECTS-003,
RENDER-WORLDS-K and RENDER-ITEMS-002I. Follow MERGE QUEUE before acquiring: only
when first or empty, remove own line immediately after acquisition; re-append
on abort. No lock is currently held by this lane.
