# Extreme native scenes, NATIVE-PERF-002

The ordered character draw path costs less CPU time, and the offline demo can now exercise 80 equipped
players. **The 25 fps target is still open in every measured stress scenario.** This milestone supplies
reproducible workloads, profiling, measured optimizations and regression checks, with the shortfall recorded
below. It does not establish 25 fps in arbitrary worlds or the finished native client.

## Scope and provenance

Native C/OpenGL only, on an Apple M5, macOS, 2026-10-27. No original client or launcher was started, stopped,
read or driven. No networking, protection work, gameplay rules, item passes, reconstructed arithmetic,
quality settings, effects, geometry or draw order changed. The common port brief's worktree exception was
used: `codex/native-perf-002`, separate from the main checkout and other lanes.

Baseline is PERF-001's ordered immediate delivery for remote players, generic corner-event delivery and
heap scratch tables, selected with `MU_PERF_002_BASELINE=1` on the same binary. Terrain/hero batching and
PERF-001's frame cap stay enabled in both modes. The small state-op guard in the adapter is shared by both
modes, so this baseline conservatively omits its saving. It is not `MU_PERF_BASELINE=1`, which restores
PERF-001's older overlay and cap too.

The first sampling profile, `sample PID 3 1`, has 1,835 main-thread samples: 780 in `players_draw_gl`, 725
under its mesh/body draw, and repeated corner adaptation, state decoding and immediate GL entry points.
Skinning and Ruffle also appear. These are observations of the host implementation, not new conclusions
about original x86 behavior. Existing instruction comparisons remain the oracle for the reconstructed math.

## Changes

- Remote players upload their needed textures before a batch session, then send the same ordered
  shadow/part/glow streams through `gl_batch`. Helpers and later actors retain their existing boundaries.
  Texture recreation on viewport respawn still releases the old GL names.
- `mu_meshdraw` accepts an optional host corner sink. It sends the exact computed float values directly,
  avoiding a pack-to-words, callback, decode-to-floats and second callback per corner. State/begin/end still
  take the original route. Literal GL recorders and instruction comparisons keep the old event stream.
  The backend already maps both `glColor3f` and `glColor3fv` to its `color3` operation.
- Per-draw color/UV scratch tables use bounded stack storage, about 300 KB, instead of two large heap
  allocations on every mesh/glow pass. Edge-case table handling is unchanged. Other scene allocations remain.
- The authored offline player capacity is 80 instead of eight. This is not a server-viewport capacity claim.
- `mu-world --perf-fov 65` widens the offline camera beyond the reconstructed three-step wheel limit,
  without changing that reconstructed limit or INPUT-001. It changes the benchmark camera intentionally;
  both sides use the same override. It is not a complete interactive free-camera implementation.
- The perf log adds main-thread CPU time and an asynchronous eight-query world-GL timer ring. A result
  carries its source frame ID; unavailable samples are -1, never zero. Unsupported timer-query contexts
  retain CPU/phase logs. The report excludes GPU warm-up samples by their source frame. No query wait is
  introduced. Headless GFx advance time is now included in the GFx phase as well as render submission.

## Workloads and results

`native/tools/bench_stress.py` generates authored demo files. Every player has five +11 armor pieces,
a weapon with excellent glow and wings. Each scene has 32 wandering monsters, repeated skills 9/10/14/24/26,
area requests, particles and lightning joints. Existing demo damage/death/removal/respawn rules stay active;
32 is the initial monster population, not a promise of 32 living targets throughout the run. The hero HP
argument is an offline-demo fixture value only. No captured stats are modified.

`crowd40` is Lorencia at 182,128, 1280x800, inventory and character open. `crowd80` adds 40 players and
Master/fourth skill trees. `tormenta80` uses world 141 at 50,46 with the same windows. `retina80` requests
3456x2160 in the SDL developer window; this is a large render target on the attached display, not proof on
an attached Retina panel. The map opens at frame 60 in every scene, camera FOV 65, all normal effects,
objects, environment and names enabled. Audio output is disabled during timing.

Before and after are paired sequentially per scenario, 24 seconds each, first 50 frames excluded. The
benchmarks did not overlap each other. Other agents were running CPU-intensive validations on this Mac;
load averages were roughly 8 at the start. Thus these are shared-host measurements, with scheduling,
frequency and thermal variation. Do not infer a clean single-host speedup ratio from them. Frame counts
and binary hashes, exact commands and workload summaries are retained locally.

| Scenario | Before fps | After fps | Before frame p50/p95/p99 ms | After frame p50/p95/p99 ms | CPU before/after ms | World GL before/after ms |
|---|---:|---:|---|---|---|---|
| crowd40 | 20.71 | 23.81 | 47.2/60.2/72.2 | 41.5/53.0/60.8 | 45.9/38.6 | 25.6/19.4 |
| crowd80 | 13.67 | 21.62 | 70.4/92.3/120.8 | 45.1/56.0/63.2 | 71.0/45.5 | 32.9/20.4 |
| tormenta80 | 16.17 | 19.45 | 61.0/69.6/76.0 | 51.3/58.0/65.3 | 61.3/50.8 | 30.2/22.7 |
| retina80 | 14.05 | 16.50 | 69.0/75.9/126.8 | 60.4/65.8/68.9 | 69.6/59.7 | 39.1/30.7 |

CPU is mean main-thread execution time, not whole-process CPU. World GL is the mean asynchronous
`GL_TIME_ELAPSED` interval around the world draw. It overlaps CPU submission and can include GPU pipeline
bubbles. Ruffle renders through Metal outside that query. These columns cannot be added or subtracted
to derive total GPU execution or idle time. A complete Ruffle GPU split remains unmeasured.

After work p95/p99, excluding cap sleep: crowd40 49.6/54.9 ms; crowd80 56.0/63.2 ms;
Tormenta 58.0/65.3 ms; large target 65.8/68.9 ms. Every scenario fails the strict 40 ms target.
For the large target the remaining mean phases include logic 9.8, terrain 6.9, objects 9.7,
characters 13.0 and GFx 18.1 ms. The GFx phase and repeated character/skin/mesh work still consume too much
of the budget. Per-object pose caching was not added: safe keys must account for shared bone/root buffers,
attachment state and every transform/light input. No cache with incomplete invalidation was shipped.

## Reproduction and regression gates

Use local installed inputs and the already converted Native Data. Raw reports, profiles and renders must
stay outside the repository. `MU_GFX_LIB` must name the existing ABI-3 Ruffle build; the tool refuses silent
fallback, omitted players, absent combat effects, missing inventory models and an unopened map.

```sh
make -C native world client
./tools/python/bin/python native/tools/bench_stress.py \
  --game-root "$MU_GAME_ROOT" --data "$NATIVE_DATA" --gfx-lib "$MU_GFX_LIB" \
  --out "$PERF_OUTPUT" --check-regression
# Same workloads, reference delivery paths:
# add --baseline, with a fresh output directory.
# Strict goal acceptance, currently FAILS:
# use --check instead of --check-regression.
# Deterministic uncapped GL throughput:
# add --headless --frames 300; this is not measured capped fps.
```

The committed `stress_m5_limits.json` separates the measured M5 regression envelope from the 25 Hz goal.
The measured after runs pass all four regression envelopes. They fail all four goal checks. The envelope
allows about 15-25 percent scheduling variation, with independent frame-tail and CPU limits; it catches
large draw-path regressions without pretending the current baseline meets the target. Synthetic tests
exercise fast/slow, missing workload and both threshold paths. Recalibrate on other hardware or an idle
Mac, preserving the strict 25 Hz check. The JSON limits are reviewed summaries, not proprietary data.

## Verification

Verification results and retained artifact paths are listed in [the handoff](../handoffs/NATIVE-PERF-002.md).
The direct-corner comparison normalizes only Color3f/Color3fv to the backend's shared color3 operation;
all other stream words and scratch-table bytes must match. Dropping a vertex or replacing alpha with 1
must fail. Existing software hashes and literal instruction-stream digests are unchanged.

Private frame comparisons use the same scene/camera/logic clock at frames 0,60,120. They disable GFx in
both modes because Ruffle already has timing-dependent frame differences between identical runs, as
recorded in PERF-001. GFx code is unchanged here; actual open-window timing uses the real Ruffle library.
No visual difference is intended by the optimization. No client assets or renders are committed.

## Remaining work

- Hold 25 fps in these scenes on an idle Mac, then repeat under realistic concurrent load. The present
  measurements explicitly do not satisfy that finish condition.
- Profile the remaining Ruffle AVM/movie updates and Metal work, with full GPU timing, before changing it.
- Investigate validated per-object pose/skin caches or less corner dispatch/scene allocation work while
  retaining shared-buffer side effects, lighting, alpha and attachment behavior.
- Broaden the world matrix, moving-player mixes and skill/effect coverage. Existing unsupported skill
  branches remain visible in the combat summaries. The demo is not a live crowded-server trace.
- `mu-client` and the Preview bundle share the optimized runtime/core. The extreme matrix measures
  `mu-world`; separate extreme autoplay/Preview-app timing and full interactive unlocked-camera coverage
  remain open. Existing flow/render and bundle checks cover integration, not those performance claims.
