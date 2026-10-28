# RENDER-WORLDS-E

Elbeland boid movement, native model drawing and typhoon clouds are implemented. Raklion's inherited event
arming, millisecond timer, ordered emitter requests and quake state are implemented behind an explicit event
input. Aida's largest near-hero light difference has an accumulation signature; no brightness adjustment was made.

## Evidence and checks

- `validate_worlds_e.py --cases 600 --mutations`: 4,840 comparisons, zero mismatches or stopped cases,
  12/12 compiled planted mistakes caught. Eight families have 600 cases each. The ninth has 40 Elbeland
  sessions of 20 ticks with movement and both render passes, 2,400 compared steps, 3,020 host calls and
  929 random calls. Directed cases include animation states, missing models, safe-zone gates and warps.
- Cloud create/move/render families execute original instructions against compiled production C, with owner
  tracking, range boundaries, random consumption, rotation and texture selection. Engine drawing and animation
  are recording stubs. The native synthetic host separately checks model loading/drawing, boid-owned cloud
  creation, owner refresh and particle drawing, plus Raklion dispatch, expiry, model skips and quake reset.
- The fourteen arrival views at 25 steps retain every final PNG hash, object score and light score. All views
  still have zero missing/extra objects and exact primary light. Aida's frame-light mean remains 0.65117;
  Elbeland 0.02078 and Raklion 0.02574. These snapshots contain no live boid pool or event timer state, and
  Elbeland's safe arrival view has zero native boids. No live-image improvement is claimed.
- Full Mac gate and registered validator/regression results are recorded below after the final combined-tree run.

## Implementation and limits

Per-world files: `reconstructed/environment/env_elbeland.c`, `reconstructed/particles/elbeland.c`,
`reconstructed/objects/raklion_event.*`, `native/core/mu_objects_raklion.c`. Shared changes dispatch these paths,
load Object52/sos3bi01 and typhoonall plus Effect/Map_Smoke1, and resolve particle owners in the boid pool.
The native world changes only feed the clock/hero angle and camera quake. No input routing changed.

Raklion follows `0x00ea176f`, `0x00ea17c0`, `0x00ea186c` and timer `0x00c9b4ac`. Expiry uses unsigned
millisecond subtraction with a strict `elapsed > duration` boundary, including wrap and the zero-start sentinel.
The inherited timer runs for each moved default object, as the original does, and skips types 22/70/80 and
objects whose generic move did not run. `mu_objects_raklion_set_event` is the explicit state input. It starts
inactive; authoritative event packet wiring is outside this lane. Emitter requests are forwarded with their
original scales. The downstream event-specific effect models/lifecycles remain outside this timer proof;
unsupported requests retain the existing particle/effect host counters.

Elbeland reads model action PlaySpeed before animation. The comparison supplies distinct synthetic per-action
speeds. The model reader leaves PlaySpeed unwritten, as recorded in client-actors.md; the native host uses
that host's explicit 0.25 default until a runtime action table is captured. This is a host choice, not recovered
Elbeland timing. Existing model mesh/render rules are reused, not re-proved here. The type-62 boid's original
zero body scale is preserved. The typhoon uses OBJECT +0xa0 for its body scale, independent of flight speed +0xbc.
Clouds keep a stable boid owner handle through movement and rendering.

Aida attribution is reproducible with `scripts/analyze_aida_light_history.py` over the saved object/light files.
The report records both input SHA-256 digests and the source tile. Three portable regressions exercise the
diagnostic with authored object/light snapshots and the production terrain C: one addition, 179 additions
across a partial reset, and rejection of incomplete grids or a non-Aida world.
The type-30 emitter at tile approximately 95.656,6.781 has a range-2 footprint. Green minus red per call is
0.2 times the radial falloff, independent of flicker. At x=94/95 the saved grid gives 1.000 effective update;
at x=96/97 it gives approximately 179.05..179.18. Red and blue agree to about 0.012 despite the large strength.
This supports accumulated additions across a reset boundary, not a missing high-intensity emitter. Original
terrain code resets only a visible rectangle and preserves the rest. The snapshots lack that rectangle and its
history, so its exact extent and the reason for the native/captured boundary difference remain unverified.
Do not fit a new brightness constant or claim complete Aida visual equivalence from this result.

The 2026-10-28 instruction recheck covers 3,000 MoveObject cases with zero mismatches/stops and 19/19
compiled mutants detected, including Aida's deliberately wrong source brightness. Terrain frame reset
`0x016ca4fa` matches in 8/8 cases; AddTerrainLight `0x016cacfc` matches in 160/160 cases. Both light-clamp
negative controls differ from the original. These verify the source/reset/add rules, not the captured reset
history. The supplemental reduced terrain run also reports one unrelated world-53 face-effect mismatch
and 29 generated-NaN sign-only cases. No terrain implementation changed in this lane; these are not counted
as zero-mismatch terrain coverage.

Pins: text `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`;
data `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`.
The report records routine addresses and body digests. CRT trigonometry uses the existing validator's host-libm
substitution for particles and the existing environment arithmetic. The original client/launcher was never
started, stopped, driven or read. No service, wire, protection or running-memory work was performed.

Reports/logs: `~/Documents/MTM/mu-mac-tools/native/scratch/render-worlds-e/`.
Renders and before/after scoreboards: `~/Documents/MTM/mu-mac-tools/native/renders/render-worlds-e/`.
Both remain local. No input symlinks, captured bytes, decoded assets or generated images are committed.

## Remaining work

A's flames/after-character pass and C2's Icarus work remain owned by those lanes. Other open work is the
authoritative Raklion state feed, its downstream event effect families, captured Elbeland action speeds,
the Aida reset-box/history input and fresh synchronized visual captures in a separately authorized run.
Tarkan/Raklion haze remains outside this lane. Self-review covers standards and the task scope; no independent
review or live gameplay validation is claimed.
