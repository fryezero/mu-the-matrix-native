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

## Final evidence

Final timings and frame comparisons are recorded after the serialized runs.

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
