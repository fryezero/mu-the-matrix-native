# Native stress performance, NATIVE-PERF-004

This continues [PERF-003](native-performance-003.md) on the native macOS client.
All scenes use the full-quality [PERF-002 workloads](native-performance-stress.md).
No original client or launcher was started, stopped, read or driven.

## Implementation and correctness boundary

Remote characters now prepare their placement in list order, update their own
pose and skin buffers with joined macOS dispatch workers, then update nameplates
in list order. Workers never execute session, RNG, effect, nameplate or GL work.
Each character retains its own model windows, shared-within-character root,
quaternion and bone storage, saved player bones and attachment outputs. Fewer
than eight entries and non-Apple builds retain serial execution. No arithmetic,
attachment rules, animation clocks or draw order changes.

A model-owned mesh cache proves that the current topology needs no MODEL-EDGE
extension. A hit compares every triangle byte and all vertex, normal and UV
bounds used by the index validator. Changed inputs require a fresh validation.
Fully proved models also avoid the per-draw edge-view allocation. Invalid
topology and absent/failed cache allocations retain the checked edge path. Transform, light, texture, color, alpha and GL state are rebuilt normally;
none is cached. The literal mesh entry points remain checked. Each model frees
its own cache. Identical equipment is not assumed to have identical poses.

The GL batch sets vertex, UV and color array pointers once per session and again
when the backing buffer moves. Every draw still reads the current vertex bytes.
The first flush always restores all pointers because other GL users may have
changed them between sessions. No primitive, state transition or draw is removed.
A synthetic repeated-session test grows the buffer and overwrites all three GL
pointers between sessions; removing session invalidation is detected.

`MU_PERF_004_BASELINE=1` restores all prior paths on the same binary.
`bench_stress.py --perf-004-baseline` records that choice explicitly. Main-thread
and whole-process CPU time are separate columns; dispatch/driver worker CPU is
included only by the latter. CPU intervals overlap the GL and Metal queue
intervals and must not be added to them. GPU busy time remains unmeasured.

`compare_stress.py` uses fixed AS2 time and synchronous presentation, renders and
reads back every full frame, hashes its RGBA bytes and omits PNG encoding/storage.
It rejects missing, repeated or unordered frame IDs and quality-omission flags.
Timing uses normal wall time and asynchronous double-buffered presentation.
Exact comparison establishes pixel equality for the same simulation inputs;
it does not establish identical completed-surface selection under arbitrary
asynchronous scheduling. No quality or regression threshold is relaxed.

## Steady sampling

The resumed lane retained fresh 3-second, 1 ms sampling profiles taken at 10:21
and 10:22 on 2026-10-28 after more than 180 rendered frames. Crowd80 has 1,771
main-thread samples: 890 under world drawing, 524 under remote-player drawing,
243 under remote pose updates and 233 under GFx updates. Tormenta80 has 1,833:
1,002 world drawing, 504 remote drawing, 233 remote pose updates and 226 GFx.
These inclusive counts are not additive percentages or original-x86 evidence.
They motivate eliminating repeated topology walks and moving character-local
pose/skin work off the ordered render thread. GL submissions remain a major
cost; effects and RNG remain ordered. No speculative pose-sharing cache shipped.

## Verification

The initial native world/client build and 18 focused tests passed. All 604
full-quality frames, 0 through 150 in all four scenes, are byte-identical between
PERF-004 reference and optimized modes. Comparisons retain GFx, all crowd models,
nameplates, equipped glow, world objects, combat effects and the map opened at
frame 60. The 247 pinned synthetic mesh cases preserve complete normalized GL
streams and scratch-table bytes; dropped vertices and forced alpha are caught.
The topology regression catches stale triangle and vertex-bound proofs.

The expanded synthetic suite also covers zero, one, seven and eight entries,
hidden entries and temporarily missing models, in addition to nine-character
32-frame repeated runs. The edge suite passes four tests with one explicit
private-corpus skip. Final integrated verification is recorded below.

## Initial paired repeat

Eight sequential 60-second window runs use the same binary at `55a8e99`, normal
wall time and asynchronous GFx presentation. The first 50 frames are excluded.
Before runs first in crowd40/Tormenta; after runs first in crowd80/retina80. This
task runs no builds, tests or sampling concurrently. Other lanes run on the same
host, including a merge gate, so causal gains are not isolated. All eight runs
pass the unchanged warning envelope; every optimized run fails strict acceptance.

| Scenario | Before fps | After fps | Before frame p99 ms | After frame p99 ms |
|---|---:|---:|---:|---:|
| crowd40 | 24.99 | 24.58 | 40.04 | 56.16 |
| crowd80 | 20.99 | 22.25 | 111.62 | 88.65 |
| tormenta80 | 22.13 | 22.50 | 98.22 | 100.36 |
| retina80 | 18.62 | 21.57 | 164.89 | 113.65 |

The interrupted agent's earlier baseline measured 24.60/24.99/24.98/22.35 fps
in crowd40/crowd80/Tormenta/retina. Only crowd80 passed strict acceptance there.
Those observations and every unfavorable paired result remain in the
[aggregate evidence](native-performance-004-summary.json). Raw logs are removed
after merge under the disk cleanup rule. No threshold is widened.

The final source additionally avoids edge-view allocation for fully proved
models. The integrated repeat below measures that version against its own
PERF-004 reference on the same binary and current main quality/content.


## Resumed profile and instruction comparison

Fresh optimized profiles at 11:12 contain 1,508 main-thread samples in crowd80
and 1,660 in Tormenta80. Remote pose update occupies 43 and 36 inclusive main
samples, versus 243 and 233 in the earlier profiles. These are separate shared-
host observations, not a normalized cost ratio. Tormenta has 993 samples under
world drawing and 237 under GFx; GL driver submissions remain a leading cost.
This motivated the client-array pointer setup change. No profile overlaps a
timing matrix from this task.

The fresh original-instruction validator passes all 843 draw cases, 247 pinned
cases and 13,529 texture names, zero mismatches, every draw branch reached and
4/4 negative controls caught. Fourteen installed models are explicit exclusions.
The reconstructed instruction paths are unchanged; native-host optimizations
are checked separately through exact streams, model buffers and full frames.

The 20-second pointer/combined pilot measured crowd80 14.73 to 16.79 fps and
Tormenta80 11.17 to 15.59 fps. Every run fails strict acceptance. These short
shared-host observations are retained in the aggregate evidence; they do not
establish a causal speedup or substitute for the final matrix.
