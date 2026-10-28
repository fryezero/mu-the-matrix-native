# Extreme native scenes, NATIVE-PERF-002

The offline demo can now exercise 80 equipped players through ordered batching and direct corner delivery.
**The 25 fps target is still open in the three 80-player scenes.** The serialized repeat's 40-player
scene passes the committed 25 Hz check, with frame pacing tails recorded below. This milestone supplies
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
Skinning and Ruffle also appear. A later 80-player profile on the pre-final `a2a1c00` snapshot identifies skinning, Ruffle AVM1 property
lookup/case folding, mesh drawing and batch vertex delivery among the remaining executing hot paths. These are observations of the host implementation, not new conclusions
about original x86 behavior. Existing instruction comparisons remain the oracle for the reconstructed math.
Two repeat `sample` attempts on the integrated binary produced no usable profile. One was stopped after
its demo exited; the other exceeded a 90-second timeout. The earlier completed profiles remain the sampling evidence.
A fresh integrated sampling profile is still needed.

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
- The authored offline player capacity is 80 instead of eight, and the native name pool is 128 instead
  of 64. All 80 plates plus 32 actors and the hero now fit. Earlier exploratory measurements silently
  admitted only 31 player plates and are excluded from the final comparison. This is not a server-viewport
  capacity claim. The additional names are an intended capacity fix, used equally by both benchmark modes.
- `mu-world --perf-fov 65` widens the offline camera beyond the reconstructed three-step wheel limit,
  without changing that reconstructed limit or INPUT-001. It changes the benchmark camera intentionally;
  both sides use the same override. It is not a complete interactive free-camera implementation.
- The perf log adds main-thread CPU time and an asynchronous eight-query world-GL timer ring. A result
  carries its source frame ID; unavailable samples are -1, never zero. Unsupported timer-query contexts
  retain CPU/phase logs. The report excludes GPU warm-up samples by their source frame. No query wait is
  introduced. Headless GFx advance time is now included in the GFx phase as well as render submission.

## Workloads and results

The earlier timing binary is from `4d556f3`, integrated through main `128679f`, including the expanded
item bodies, Icarus C2 and the monster/session migration. Both modes use this same binary. Upstream
session scheduling and intended item/effect differences belong to their own milestones; they occur on
both sides here. Legacy presentation capacity rises from eight models to 80. The earlier timing snapshot
from `a2a1c00` is retained locally, including its unfavorable large-target result.

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

Before and after are paired sequentially per scenario, first 50 frames excluded. Crowd40 uses 40-second
runs, the three 80-player scenes 60-second runs. Measured frame counts before/after are 333/397,
326/309, 209/304 and 201/309 respectively. The benchmarks did not overlap each other. Other agents and
this task ran CPU/GPU-intensive validation and build work on this Mac. Load, scheduling, frequency and
thermal conditions varied. These shared-host measurements do not isolate a causal speedup. Binary
hashes, commands, workload summaries and raw frame logs are retained locally.

| Scenario | Before fps | After fps | Before frame p50/p95/p99 ms | After frame p50/p95/p99 ms | CPU before/after ms | World GL before/after ms |
|---|---:|---:|---|---|---|---|
| crowd40 | 10.40 | 12.05 | 91.6/148.2/190.1 | 81.9/119.3/133.1 | 58.0/52.0 | 46.8/36.4 |
| crowd80 | 7.08 | 6.38 | 131.7/224.3/270.8 | 141.5/248.5/269.0 | 110.8/106.2 | 55.0/52.2 |
| tormenta80 | 4.61 | 6.76 | 218.6/289.9/332.0 | 146.0/204.5/235.5 | 126.1/110.1 | 82.5/51.1 |
| retina80 | 5.02 | 6.99 | 204.9/254.5/316.5 | 134.8/209.1/260.5 | 141.2/120.1 | 88.0/60.6 |

CPU is mean main-thread execution time, not whole-process CPU. World GL is the mean asynchronous
`GL_TIME_ELAPSED` interval around the world draw. It overlaps CPU submission and can include GPU pipeline
bubbles. Ruffle renders through Metal outside that query. These columns cannot be added or subtracted
to derive total GPU execution or idle time. A complete Ruffle GPU split remains unmeasured.

After work p95/p99, excluding cap sleep: crowd40 119.3/133.1 ms; crowd80 248.5/269.0 ms;
Tormenta 204.5/235.5 ms; large target 209.1/260.5 ms. Every scenario fails the strict 40 ms target.
After GFx means are 29.4/77.1/70.8/57.4 ms. The 80-player Lorencia run regresses from 7.08 to 6.38 fps
although its main-thread CPU mean falls from 110.8 to 106.2 ms. The GFx phase alone exceeds the entire
40 ms budget in three scenes. The world-GL interval also exceeds 40 ms in those scenes, but overlaps
CPU submission and omits Ruffle's Metal work. Its contribution cannot be separated by subtraction.

The earlier `a2a1c00` large-target pair regressed from 7.71 to 4.89 fps, p99 198.6 to 441.4 ms. This
integrated repeat improves there but regresses in Lorencia. Neither result is discarded. Shared CPU/GPU
contention, real-time catch-up and Ruffle timing are not isolated. Repeat on an idle Mac before claiming
a causal speedup or a win in every scene. Main-thread CPU is lower in all four final pairs, but that
observation also remains subject to the shared-host conditions.

Per-object pose caching was not added: safe keys must account for shared bone/root buffers, attachment
state and every transform/light input. No cache with incomplete invalidation was shipped.

## Serialized repeat, 2026-10-28

The resumed run uses `f553b33`, which contains latest fetched main `f4b5c5c`, including the screen-haze
merge. The C binaries were rebuilt by the local gate. Every timing report pins the binary SHA-256;
both modes use the same binary. Each run lasts 60 seconds, excludes its first 50 frames and uses the
same full-quality workloads defined above. Before runs first in crowd40/Tormenta, after runs first in
crowd80/the large target. This task's builds, tests, rendering comparisons and sampling do not overlap
the timing matrix. Other machine activity was not controlled, so this remains one paired repeat,
not a causal experiment or a hardware-wide guarantee. Earlier unfavorable results above are retained.

| Scenario | Before fps | After fps | Before p50/p95/p99 ms | After p50/p95/p99 ms | CPU before/after ms | World GL before/after ms |
|---|---:|---:|---|---|---|---|
| crowd40 | 24.98 | 24.99 | 39.9/43.4/45.5 | 39.9/44.3/46.3 | 29.8/26.2 | 17.2/14.1 |
| crowd80 | 19.84 | 22.50 | 50.3/55.0/59.8 | 43.8/48.7/51.0 | 49.8/43.8 | 24.6/19.7 |
| tormenta80 | 18.44 | 21.55 | 54.3/58.8/66.8 | 45.9/51.0/53.7 | 53.7/46.1 | 27.3/21.1 |
| retina80 | 14.88 | 16.94 | 67.0/71.9/75.8 | 59.2/63.1/65.6 | 66.2/58.2 | 36.6/29.6 |

Measured frames before/after are 1,384/1,387, 1,044/1,192, 968/1,139 and 770/879. The CPU/world-GL
measurement boundaries above still apply. The GL interval overlaps submission and excludes Ruffle's
Metal work, so a complete CPU/GPU split remains unavailable.

After work p95/p99 are 31.1/32.6, 48.7/51.0, 51.0/53.7 and 63.1/65.6 ms. Crowd40 passes the committed
25 Hz checker in both modes; its frame p99 of 46.3 ms after optimization still shows pacing jitter.
Passing this checker does not mean every frame takes at most 40 ms. The three 80-player scenes fail
both its capped-fps and work-tail criteria. All four after runs pass the unchanged M5 warning envelope.
GFx means after are 6.9/15.4/15.4/17.1 ms. CPU work still exceeds 40 ms in the 80-player scenes.

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
All four serialized-repeat after runs pass its committed warning envelopes. The earlier shared-load
Tormenta run fails the fps floor, frame tails and CPU ceiling. Those failures remain visible and the
limits were not widened. Three serialized-repeat strict 25 Hz goal checks fail. Passing a warning envelope establishes neither an
optimization win nor 25 Hz acceptance. It is a repeatable warning check against the earlier full-nameplate,
expanded-item workload; shared-host load can exceed it. Synthetic tests
exercise fast/slow, missing workload and both threshold paths. Recalibrate on other hardware or an idle
Mac, preserving the strict 25 Hz check. The JSON limits are reviewed summaries, not proprietary data.

## Verification

The expanded item-body classifier changes the seeded generic candidate list of the existing renderchar
validator. All 500 requested item cases are accounted for: 106 existing record-type-4 exclusions and
394 exact comparisons, all matching. With back/character/light cases the total is 625, rather than the
stale manifest value 638. The manifest now pins those counts and light equality explicitly. New special
bodies are separately compared by the item-cluster validator; no mismatch was waived.


The final parallel merges also exposed an incremental-build dependency typo: the software character-select
objects named undefined `CORE_HDR` rather than `HEADERS`. They retained the old `mu_objects` layout after
the rendering lane enlarged it, so two existing object-lifecycle tests failed. The one-word Makefile fix
rebuilds those consumers; all four targeted character-select lifecycle/snapshot tests then pass. It changes
no scene behavior.


A long `--combat-script` exposed a new main-branch Native Data integration issue: script text was probed
as a filesystem path and failed with ENAMETOOLONG. The guard now skips text-valued script/walk/wheel
options, with a portable regression using 32 valid script entries. The owner's legacy Native Data folder
was left unchanged; a fresh scratch clone was stamped against the pinned installed build for validation.

Review during resumption also found that inherited `MU_GFX_PLAIN_ITEMS` could omit inventory glow
passes without being rejected. The benchmark now rejects this flag and every existing quality-omission
flag by presence, matching the renderer's `getenv` checks even for empty values. One regression test
covers all eight flag/value combinations before the benchmark reads binaries or creates output.

Verification results and retained artifact paths are listed in [the handoff](../handoffs/NATIVE-PERF-002.md).
The committed direct-corner host compares all 247 pinned synthetic cases, including full stream words
and scratch-table bytes. It normalizes Color3f/Color3fv only, as the backend already does. Both planted
mistakes, a dropped vertex and forced alpha 1, are caught. Existing software hashes and literal
instruction-stream digests are unchanged. Synthetic and private
render comparisons cover the host optimization. A private comparison caught a new batch session clearing
the hero's pending geometry when no remote-player session existed. The fix requires that session before
opening the batch; a dedicated absent-players regression now covers it.

Private frame comparisons use the same scene/camera/logic clock at frames 0,60,120. They disable GFx in
both modes because Ruffle already has timing-dependent frame differences between identical runs, as
recorded in PERF-001. GFx code is unchanged here; actual open-window timing uses the real Ruffle library.
No visual difference is intended by the optimization. No client assets or renders are committed.

## Remaining work

- Hold 25 fps in the three 80-player scenes, reduce crowd40's pacing tails, then repeat under realistic
  concurrent load. The present measurements do not satisfy the complete finish condition.
- Profile the remaining Ruffle AVM/movie updates and Metal work, with full GPU timing, before changing it.
- Investigate validated per-object pose/skin caches or less corner dispatch/scene allocation work while
  retaining shared-buffer side effects, lighting, alpha and attachment behavior.
- Broaden the world matrix, moving-player mixes and skill/effect coverage. Existing unsupported skill
  branches remain visible in the combat summaries. The demo is not a live crowded-server trace.
- `mu-client` and the Preview bundle share the optimized runtime/core. The extreme matrix measures
  `mu-world`; separate extreme autoplay/Preview-app timing and full interactive unlocked-camera coverage
  remain open. Existing flow/render and bundle checks cover integration, not those performance claims.
