# Native stress performance, NATIVE-PERF-003

This continues [PERF-002](native-performance-stress.md). The measurements and
render comparisons below cover the authored offline stress scenes on this M5.
They do not establish finished native gameplay performance. No original client
or launcher was started, stopped, read or driven.

## Measurement boundaries

Verified host instrumentation records main-thread CPU time, world GL elapsed
time, a separate GFx GL compositor/item interval, and the complete Ruffle Metal
queue interval. Each asynchronous sample retains its source frame. Warm-up is
excluded by that frame, rather than the frame on which the result arrives.
Missing, unsupported, failed or duplicate samples cannot become zero time.
Cached GFx frames have an explicit zero-submission marker.

The Metal diagnostic places two private four-byte blit markers on the same
queue, around all movie renders in the host frame. It retains their command
buffers and reads Metal's GPUStartTime and GPUEndTime after completion. This
includes Ruffle's intermediate offscreen/filter submissions. It adds no frame
wait. Diagnostic shutdown drains outstanding samples. There are at most 64
pending intervals; exhaustion is recorded as missing data and fails the check.
Normal rendering creates no marker resources when MU_GFX_GPU_LOG is absent.

These are elapsed GPU/queue intervals, not isolated GPU busy times. The Metal
interval includes CPU encoding gaps, and GL intervals include pipeline bubbles.
The queues and CPU can overlap. Do not add these columns, subtract CPU from them,
or describe their sum as total GPU busy time. GPU utilization remains unmeasured.
The existing double-buffered IOSurface presentation policy is unchanged.

The interrupted timing WIP is superseded. Its first 64-QuerySet implementation
exhausted Metal counter-buffer allocation. Later pass markers returned invalid
or stale intervals. Those samples were rejected. The replacement synthetic
probe renders two frames, records a cached middle frame and closes immediately;
all three frame records must be complete after the shutdown drain. The separate
168-frame full-scene probe has zero missing Metal intervals.

## Changes

- The window host paces against the current frame's start plus 40 ms. Previously,
  the reconstructed clock's start-to-start elapsed value selected a sleep at the
  end of the render. Changing render cost could produce alternating long/short
  frames. The reconstructed clock, logic accumulator and headless timing remain
  unchanged. Both mu-world and mu-client use the host deadline. The sleep helper
  also releases its temporary Mach thread rights.
- Small draw-input arrays use bounded per-call stack storage, rebuilt from every
  current model/texture/pass input. Models above 16 meshes or 16 auxiliary
  bitmaps retain the allocating path. There is no pose or lighting cache.
- Skinning searches disjoint model memory regions in an order that reaches
  vertex and normal outputs earlier. Region addresses, pointers and bytes stay
  unchanged. Foreign, overlapping and externally supplied region lists keep
  their original precedence. There is no transformed-vertex or pose cache.
- Native macOS compilation uses O3 and ThinLTO, including the unchanged model
  math sources in the native library. Floating-point contraction stays disabled
  and fast math stays disabled. Portable builds retain O2. NATIVE_PERF_LTO=0
  selects the old native compiler flags; use a clean build when switching.
  The GFx release library uses ThinLTO and one codegen unit.
- The strict checker now requires frame p95 <=41 ms and p99 <=42 ms as well as
  its existing capped-fps and work-tail criteria. The M5 warning envelope is
  unchanged. Missing, negative and nonfinite metrics fail both checks.

MU_PERF_003_BASELINE=1 restores the old draw allocation and host pacing paths.
Compiler comparisons require the separately built O2/non-LTO artifacts. All
render geometry, effects, textures, draw order, animation rules and quality
settings remain enabled.

## Sampling and exploratory runs

Fresh completed steady-scene samples were taken after more than 180 rendered
frames, rather than during startup texture loading. Crowd80 has 1,882 main-thread
samples: 883 under the GFx window phase and 634 under world GL drawing. Tormenta80
has 1,959 main-thread samples, including 598 under world_gfx_frame and 729 under
world GL drawing. These inclusive counts describe the sampled host, not original
x86 behavior. GFx advance/mouse picking/property lookup, character skinning and
mesh delivery remain executing costs. The earlier resumed profiles sampled
startup directory scans and cannot substitute for these steady-scene profiles.

Short 20-second compiler pilots excluded the first 50 frames. Results are kept
even where they regress. The first Rust/pacing pilot, before to after fps, is
24.18 to 22.38 in crowd80, 24.89 to 24.95 in crowd40, 18.52 to 20.28 in Tormenta,
and 13.04 to 17.60 at the large target. Crowd40 after passed the strict checker.
A later O2 / native-host-LTO-plus-stack / both-LTO pilot measured 20.96 / 21.04 /
20.85, 20.73 / 20.55 / 21.70 and 17.83 / 18.75 / 19.64 in the three 80-player
scenes. That native compiler experiment still used O2 for the reconstructed
library objects. The final native build also enables ThinLTO there.

These pilots ran on a shared host with changing load. They do not isolate a
causal speedup for each component or establish a win in every scene. No limits
were widened to hide the unfavorable results.

## Render equivalence and the comparison clock

Verified: all 604 full frames, 0 through 150 in each of the four workloads, are
byte-identical between O2/non-LTO reference and optimized builds. Every frame
includes the full GFx, nameplates, equipped crowd, item icons, combat effects,
world objects and map opened at frame 60. The comparison uses synchronous
single-buffer presentation and fixed AS2 simulation time. It does not prove
that asynchronous presentation chooses the same completed frame under arbitrary
host scheduling.

The initial comparison failed on 46 HUD edge pixels in frame 0. A repeat of the
unchanged reference also differed, excluding an optimization-only explanation.
Ruffle's AS2 getTimer reads real wall time even with a fixed date and tick delta;
the UI tweens therefore received different time inputs during model loading.
Patch 0008 exposes an optional host clock. MU_GFX_TEST_CLOCK pins getTimer to the
movie's accumulated advance time while keeping its frames, timers, busy-loop
offset and animations enabled. The first-frame control and all 604 frame pairs
then match exactly. Normal players retain wall time. An authored GetTime probe
returns 0, 0, 40 across a real delay and a 40 ms advance only in comparison mode;
the normal-mode probe confirms wall time still advances. The timing benchmark
rejects this test-clock environment variable, including an empty value.

## Region-search experiment

The window ABBA experiment is retained locally in region-*. It did not establish
a whole-scene speedup on the changing shared-host load. Crowd80 reference / new /
new / reference fps are 19.31 / 18.14 / 15.74 / 14.45; Tormenta80 is 21.68 / 16.77 /
16.83 / 21.74. These unfavorable observations are not discarded.

An in-process, thread-CPU probe isolates the actual production transform wrapper
on the installed HelmClass09 model with a fixed pose. Eight alternating batches
make 120,000 successful transform calls, 60,000 per mode. Mean CPU time per 15,000
calls is 552.265 ms with canonical search and 404.728 ms with reordered search,
26.7% lower. Each batch's complete mapped regions equals the reference bytes.
This is a local transform cost result, not a 26.7% frame-rate claim. Fourteen
synthetic dump cases also compare every transform output byte in both modes.
The optimized version preserves all 604 full-frame hashes above.

## Final timing

Final-source window repeats use normal AS2 wall time and asynchronous double-buffer
presentation. Each run lasts 60 seconds, drops the first 50 frames and checks the
complete workload. Reference and optimized builds use the same source at
`1529b8c`; the reference selects O2/non-LTO, 16 Rust codegen units and
`--perf-003-baseline`. The optimized build uses the default macOS O3/ThinLTO,
region search, bounded storage and deadline pacing. Run order alternates by
scenario. Build hashes and commands are in `continued/resume-builds.json` and
`continued/resume-*/`.

| Scenario | Build | Frames | fps | Frame p50 / p95 / p99 ms | CPU mean ms | World GL mean ms | GFx GL mean ms | Metal queue mean ms |
|---|---|---:|---:|---|---:|---:|---:|---:|
| crowd40 | before | 1,355 | 24.78 | 40.20 / 48.50 / 52.80 | 30.79 | 15.62 | 0.46 | 4.02 |
| crowd40 | after | 1,363 | 24.90 | 40.01 / 40.64 / 43.74 | 29.23 | 15.18 | 0.46 | 3.96 |
| crowd80 | before | 856 | 16.52 | 59.64 / 75.39 / 99.22 | 57.66 | 22.93 | 0.67 | 7.11 |
| crowd80 | after | 943 | 18.37 | 53.62 / 65.24 / 75.56 | 52.27 | 22.05 | 0.67 | 6.70 |
| tormenta80 | before | 762 | 15.40 | 61.75 / 88.64 / 106.45 | 61.55 | 25.58 | 0.68 | 7.26 |
| tormenta80 | after | 978 | 18.94 | 52.15 / 63.18 / 68.42 | 51.36 | 22.20 | 0.69 | 6.24 |
| retina80 | before | 688 | 13.59 | 71.19 / 93.39 / 111.66 | 68.11 | 30.34 | 2.35 | 10.51 |
| retina80 | after | 899 | 17.58 | 56.77 / 62.81 / 65.62 | 52.26 | 25.56 | 2.85 | 10.22 |

All eight runs pass the existing M5 regression warning envelope. None passes the
strict 25 Hz work/pacing acceptance in this repeat. Even crowd40's optimized
24.90 fps has failing tails; its earlier 24.98 fps strict pass remains an earlier
observation. The three optimized 80-player scenes remain below 25 fps. Their
results are shared-host observations, not isolated causal estimates or proof of
a fixed speedup. No acceptance limit or visual-quality setting was relaxed.

All measured frames have complete Metal intervals. CPU means are main-thread
CPU time. World GL, GFx GL and Metal queue columns are separate elapsed intervals
that overlap CPU work and can overlap one another; do not add them into a GPU
total. Queue/busy-time limits remain as described above.

The earlier complete compiler/storage/pacing matrix remains in `final-*` and
measured crowd40 24.98 ->24.98, crowd80 23.53 ->24.45, Tormenta80 21.83 ->22.07
and retina80 17.78 ->17.87 fps. It preceded region search and is retained as
historical evidence rather than substituted for the final-source repeat.

## Final verification and disk recovery

The completed original-instruction meshdraw validator in `continued/oracle-final`
has 843/843 draw cases, 247/247 pinned cases and 13,529/13,529 texture names,
zero mismatches, no uncovered draw branches and all four negative controls
caught. Fourteen installed models are explicitly skipped. The reconstructed draw
library is compared with x86 instructions; the 604-frame native comparison above
separately covers the host/compiler changes.

The ENOSPC recovery removes rebuildable Rust output, duplicated experimental
libraries/source and raw frame dumps. Keep all numerical reports and supporting
logs, per-frame hashes and eight representative before/after images. The final
lock-held Mac gate and merge provenance are recorded in the milestone handoff.

## Reproduction

Use the PERF-002 workloads and local installed inputs. Benchmark outputs and
renders must stay outside the repository. Build the O2 reference from the same
merged source with NATIVE_PERF_LTO=0 and the Rust release LTO/codegen overrides,
then preserve the artifacts before rebuilding the normal optimized targets.
For the reference benchmark, select that binary/library and
--perf-003-baseline. For both sides, --gpu-timing requires the Metal extension
and rejects an incomplete frame set. --check enforces the 25 Hz goal, while
--check-regression enforces only the unchanged M5 warning envelope.

Local evidence is under mu-mac-tools/native/scratch/native-perf-003/continued
and mu-mac-tools/native/renders/native-perf-003. It includes commands, exact
binary/library SHA-256 values, raw phase and Metal logs, completed samples,
failed timing experiments, gates and per-frame image hashes. No original data,
render or capture is committed.
