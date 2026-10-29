# Temporal world fidelity, RENDER-TIME-001

## Implemented native boundary

This milestone adds an opt-in measurement path, shared physical-input routes and a temporal regression
checker. It changes no reconstructed routine, RNG rule, simulation order, default render, gameplay or live
client. No original client was started, stopped or driven. There is no new instruction-equivalence claim.
The existing world-lane Unicorn findings remain the evidence for those routines.

The old [world tour](client-world-fidelity.md) scores saved arrival stills. C2 #189 showed why that cannot
score moving/random content: Icarus error against one original still varies with native phase, and adding
verified producers changes downstream RNG consumption. This measurement uses complete draw histories.
It does not remove moving regions to improve an image score.

`scripts/render_time/paths.json` covers fourteen capture views in thirteen worlds. Start tiles match the
saved tour's reviewed arrival metadata. Each view has its own authored INPUT-001 `.input` file, with no
private record data. At 640x480 drawable pixels and a 25 Hz input loop, the 201-iteration route stands,
clicks east on screen, zooms, clicks west and restores zoom. The hero's actual path and camera are observed,
not assigned. A blocked walk or absent zoom fails the checker. The two Devias views remain separate.

| View | World | Start tile |
|---|---:|---|
| Lorencia | 0 | 137,130 |
| Dungeon | 1 | 108,247 |
| Devias arrival | 2 | 71,181 |
| Devias town | 2 | 199,48 |
| Noria | 3 | 174,109 |
| Lost Tower | 4 | 208,79 |
| Atlans | 7 | 19,15 |
| Tarkan | 8 | 195,70 |
| Icarus | 10 | 15,13 |
| Aida | 33 | 84,11 |
| Kanturu | 37 | 19,218 |
| Elbeland | 51 | 53,224 |
| Raklion | 57 | 224,211 |
| Karutan | 80 | 125,123 |

## Capture and report contract

`mu-world` and `mu-walk --headless --time-series-every N` draw every iteration, including iterations that
produce no PNG or sample. This matters because drawing advances some visual lifecycle state and creates
particles. Samples run after drawing. They go to stdout as `time_series:1` JSON rows. The flag is limited
to headless runs of at most 10,001 iterations; N is 1..10,000. Without the flag, existing behavior remains.
`--time-series-start-ms MS` sets the virtual headless clock epoch, default 100000, range 1..2140000000.
It supplies time to the native clock; it does not restore pool history or the original shared random stream.

`scripts/render_time.py capture` runs a new output directory, rejects disk space below 5 GiB, captures 21
samples per view at frames 0,10,...,200, and saves only frames 0/100/200. It writes per-view `series.json`,
a combined `series.json` and a bounded diagnostic log. No object images, light grids or decoded tables
are written. `compare` writes a combined report and one report per map, each with thresholds and failures.
All of these outputs are private local evidence. Keep only compact summaries and three representative PNGs
per view while working, then follow the port brief's cleanup rule.

The series includes source, plan/binary SHA-256, script and placement/sidecar SHA-256 per view, world/tile, expected sample frames,
phase provenance and whether every iteration drew. Each sample records world, frame, WorldTime in ms and
logic-step ordinal, followed by these fixed vector layouts, indexed from zero:

| Group | Ordered values |
|---|---|
| camera, 9 | hero XYZ, hero animation frame, camera eye XYZ, FOV, pitch |
| objects, 19 | live count; sums of frame, prior frame, alpha, blend U/V, blend light, position XYZ, angle XYZ, light RGB, timer; visible count; action sum |
| particles, 10 | live count; sums of XYZ, rotation, alpha, scale, lifetime, type; live effect count |
| environment, 8 | live boid/fish count; sums of XYZ, frame, alpha; live weather count; weather rotation sum |
| lights, 6 | whole-map primary RGB means, whole-map frame-light RGB means |
| sky, 4 | environment clear RGB in 0..255, live joint count |
| rng, 5 | object seed, environment state, particle state, environment calls, particle calls |
| image, 48 | 4x4 grid, row-major RGB means in 0..255, from the actual RGBA readback |

Objects, particles and environment also have ordered FNV-1a-64 checksums of the selected fields. Lights
checksum both complete float grids. Image checksum is SHA-256 of the native RGBA readback. Checksums contain
no addresses, struct padding or raw records. They supplement sums, which can hide offsetting changes.
These checksums are only comparable between native runs with the same architecture and inputs. RNG states
are native module streams; the original has a shared stream. Particle sums exclude dead entries. Boid/fish
sums exclude dead entries; the weather checksum covers live positions/rotations. Effects and joints have
counts and image evidence, not complete record/phase coverage. Hidden details of those pools remain a limit.

## Thresholds and evidence classes

Native regression thresholds are active now. All expected maps, scripts and sample indices must agree;
clocks, steps and checksums must match exactly. Relative live step ordinals must also agree. Every numeric component must differ by at most `1e-6`.
Each route must move at least 50 world units in XY and span at least one degree of FOV. Nonfinite numbers,
missing/duplicate/reordered rows, schema mismatches and unaligned phase fail. The checker exits 1 for a
measured failure and 2 for invalid input or a failed capture. It does not treat a missing private input as
an integration pass. The default local gate runs authored synthetic cases and explicitly skips the private
capture unless integration is requested.

Live thresholds are a declared initial policy, not calibrated acceptance evidence. `LIVE_LIMITS` in the
checker is the exact component table: WorldTime absolute and relative error <=20 ms, camera position <=1 world unit,
hero/object animation <=0.05 frame, FOV/pitch <=0.01 degree, object position <=1 unit, object angles <=0.1
degree, alpha/UV/light <=0.01, timer <=0.05, and identical live/visible/action counts. Object sums divide by
live count. Particle/environment counts allow 10% relative error; their per-live-entry position means allow
5 units, alpha/scale/frame 0.05, rotation 2 degrees and particle lifetime 1 step. Particle type mean must
match. Weather rotation sum allows 2 degrees. Primary-light RGB means allow `1e-6`, frame-light means 0.05,
clear RGB 1/255, joint count 10%, and each coarse image RGB cell 8/255. Live RNG/checksums are diagnostic,
never compared as if pools or object ordering were identical.
RENDER-TIME-002 reviewed this policy against two live runs without changing it; see the live-half section below.

A live comparison requires `source:live`, `mugl_patches:off`, and `phase:aligned` on both series with an
independently recorded alignment procedure. The native capture deliberately emits a fresh-world phase label,
so pairing it blindly with a live series fails. A phase label is a provenance assertion by the future live
adapter, not an algorithm that finds or proves phase equality. The report must retain unknown pool/RNG
phase as unaligned. No best-frame search, lag fitting, moving-region exclusion or retuning thresholds after
seeing scores is permitted. Coarse image means do not replace full-resolution pixel or per-object checks
in the still tour and world-lane validators. A report only covers its recorded fields and route.

## Reproduce without the live game

Use the repo Python and an owned worktree. Build `make -C native build/mu-world`. Set `MU_GAME_ROOT` to the
installed data directory and `MU_RENDER_TIME_OBJECTS` to the existing captured plaintext placements, without
copying either into the worktree. The installed `.obj` files are refused by the existing loader; missing
captured placements are not an acceptable substitute for this integration run.

```sh
./tools/python/bin/python -m unittest discover -s native/tests -p test_render_time.py -v
MU_RECOVERY_INTEGRATION=1 ./tools/python/bin/python -m unittest discover -s native/tests -p test_render_time.py -v
./tools/python/bin/python scripts/render_time.py capture --out "$LOCAL_OUT/baseline"
./tools/python/bin/python scripts/render_time.py capture --out "$LOCAL_OUT/candidate"
./tools/python/bin/python scripts/render_time.py compare "$LOCAL_OUT/baseline/series.json" \
  "$LOCAL_OUT/candidate/series.json" --report "$LOCAL_OUT/regression.json"
```

`LOCAL_OUT` must exist outside tracked source. A retained series from an accepted earlier binary can be
passed as `MU_RENDER_TIME_BASELINE` to the integration test. Binary hashes may differ intentionally; plan,
script, epoch and phase inputs must agree. Without that baseline, the installed-data check establishes
repeatability of the current binary, not preservation against an older revision. Portable expected-value
checks and planted data regressions exercise the checker independently of repeatability. The Icarus private
check additionally changes the sample cadence and requires equal common rows, catching sample-driven draws.
The full local gate discovers the portable suite through `native/tests`; no shared test list is added.

## LIVE half, RENDER-TIME-002 (2026-10-28)

The live half was run under the shared game lock. It produced live series for Lorencia (world 0) and a native
twin of each. **Result: `compare --mode live` fails for both scored runs.** The first error is the phase gate:
pool ages, animation starts and the shared `rand()` stream were not aligned, so the live series is
`phase: unaligned`. The component checks also fail, mostly for causes listed below that are not render-fidelity
errors. The numbers, provenance hashes and local file SHA-256s are in
[client-render-time-live.json](client-render-time-live.json). Checks and session details are in the
[handoff](../handoffs/RENDER-TIME-002.md).

**Exporter (synthetic tests; run live).** `live-readers/rtsample` reads only (`mach_vm_read_overwrite`) and emits
the schema's sums and counts, never records.

- *Post-draw point.* mugl's presented-frame counter, whose address mugl writes to `C:\mutools\mugl-shm.txt`. It is
  incremented at the start of `wglSwapBuffers`, after the scene's draw calls.
- *Bracket.* Each read is bracketed before and after by WorldTime `0x06fce370`, the logic counter `0x0bdc5eb0`, the
  rendered-frame counter `0x0bdc5ebc` and the presented counter.
- *Sources.*
  - Hero: `[0x0a39d754]`, with its OBJECT at `+0x3254`.
  - Camera: eye `0x0bdc5ab4`, angle `0x0bdc58f0`, FOV `0x01cf1634`.
  - Static objects: the 256 sector lists.
  - Particles: the `std::list` at `0x0a3a9adc`. Statically, begin = `[[list]]` (`0x01690f45`) and end = `[list]`
    (`0x0169103a`), with the shared record pointer at node `+8`. In every live read the walked count equalled the
    stored size.
  - Pools: effects `0x0a4ca430` (200), joints `0x0a4fa4f0` (500), boids `0x0bdb71f0` (40), fish `0x0bdc0bb0` (10)
    and weather leaves `0x0a3a0e28` (200).
  - Lights: both light grids.
- *Input diagnostics.* Each sample also records MouseWheel `0x0bdc59a4`, the zoom index `0x0bdc5914`, the
  zoom-settled flag `0x0bdc5ed8` and the hero action.
- *Every-edge mode.* `--all-edges` samples every post-draw edge after arm.

`live-readers/rtinput/rtinput.c` is a Wine-side helper built with mingw. It only uses `SetCursorPos`/`SendInput`.
It replays the plan's events at the arm signal + 40 ms × frame, at the plan's client-area fractions. The arm signal
is a file that rtsample creates after its frame-0 post-draw read.

`scripts/render_time_live.py` provides `schedule`, `export`, `pair` and `summarize`. Three components are declared
unavailable and reported as `not_compared`; they are not scored:

- the clear colour, which is an immediate in the render scene, so there is no memory to read;
- the shared CRT `rand()` state;
- the image grid, because the live window has the HUD, the hero's equipment and other players.

**Capture setup (deviations from the plan in bold).**

- The owner's free-runtime prefix ran on plain Rosetta, fast x87 off.
- Rollback copies were made of `mugl-hotpatch.txt`, `mu-modes.txt` and `LauncherOption.if`.
- `mugl-hotpatch.txt` was set to `0` before start. mugl logged
  `=== hotpatch mask 0: funcs 9/9 sites 18583 peep 50977`; with mask 0 those counts are sites verified in their
  original bytes.
- The buffering mode stayed `full+vbo` (GL batching, not CPU patches).
- All three files were restored byte for byte after each session.
- **The client offers no 640×480 mode.** Its mode hook lists 960×600..1728×1080, and 640×480 appended to that
  list fell back to 960×600. The live client area is therefore 960×600. rtinput replayed the plan's positions as
  the same client-area fractions (400,240 → 600,300; 260,240 → 390,300).
- **The native twin runs at 960×600** with that scaled script, the live start tile and `start_world_time_ms` = the
  first live sample's WorldTime. Both script SHA-256s are recorded.

**Observed live timing.**

- *Frame rate.* The client drew 19.1–20.9 fps (153–167 post-draw edges for 200 logic steps), with no idle time
  between frames.
- *WorldTime moves after the swap.* WorldTime (`(float)timeGetTime()`) changed during the read, 1–4 ms after the
  swap, in 24 of run 3's 167 reads. The counters had not moved, so the next frame had begun. The exporter rejects
  such reads (bracket > 20 ms) and takes the next accepted edge: 5 rejected in run 3, 1 in run 4.
- *Reads.* Reads took ≤ 4.0 ms; none was torn by a counter.
- *Late samples.* Logic steps coalesce. Six (run 3) and three (run 4) samples fell one to four steps after their
  plan frame; their actual ordinal is recorded, not relabelled.
- *Inputs.* Inputs were sent ≤ 4.4 ms after their due time.

**Pairing (changed from step 5).** A live sample cannot fall on every exact plan frame. The native twin therefore
samples every iteration, and `pair` keeps the native row at each live sample's recorded relative logic ordinal.
Only recorded ordinals are used, never errors.

| Field | Run 3 (start 137,129) | Run 4 (start 138,129) | Reading |
|---|---|---|---|
| Hero and eye XY | exact at standing samples; 13 units mid-walk (frame 50); 100 units after frame 130 | exact at standing samples; 17 units mid-walk (frame 50) | Same path tile for tile. Run 3's second click landed one tile apart only because native had zoomed. A native twin without the wheel matches live exactly at 20/21 samples (13 units mid-walk). |
| Walk distance | 223.606798 = 223.606798 | 223.606798 = 223.606798 | equal |
| FOV / pitch / eye height | live 39 / −48.5 / 1015 throughout; native 30 / −59.16 / 814 between frames 100 and 160 | same | The wheel reached the client (MouseWheel +1 then −1), but the zoom index stayed 2 with zoom settled 1, so the client refused the zoom. Native zoomed. |
| Primary light means | 0 error | 0 error | exact |
| Frame-light means | live +0.19..+0.49 | live +0.35..+0.93 | AddTerrainLight from other characters and hero equipment, which native does not draw |
| Objects | 2,833 = 2,833. Position, angle and light mean error ≤ 0.0013. Frame/prior frame 0.062/0.065 | Frame/prior frame 0.053/0.077 | Counts and placement agree. The animation phase is not aligned (limit 0.05). |
| Visible objects | live 177–198, native 249–289 | live 176–182, native 260–290 | open discrepancy (identical camera at standing samples) |
| Particles / effects / joints | live 205–257 / ≤ 6 / ≤ 10; native 0 at frame 0, then up to 232 / 0 / 0 | live 185–235 / ≤ 7 / ≤ 6; native up to 215 / 0 / 0 | Native starts with an empty pool (a fresh world), so pool age differs. Live also holds entries owned by other players, pets and the hero's wings. |
| Live boids/fish; weather leaves | live 5, native 3–5; live 75–80, native 80 | 4–5 and 4–5; live 74–80, native 80 | counts within 10% except early native boid spawns; positions follow the unaligned RNG |
| Hero animation frame | ≤ 4.9 frames | ≤ 5.4 frames | idle animation phase not aligned |
| Relative WorldTime | −36..+5 ms | −24..+13 ms | see below |

**Threshold review.** No limit was changed in code; the result above is under the declared policy. A revised
policy must be fixed before the next scored run.

*Limits that hold on this evidence:*

- primary light at 1e-6 (exact);
- object count, action, position, angle and light;
- weather count (10%), and boid/fish counts once the spawn history is aligned;
- camera/hero position at 1 unit on standing samples;
- the relative logic ordinal, under logic-ordinal pairing.

*Limits that should change, and why:*

1. **WorldTime at 20 ms cannot hold while the client draws below 25 fps.** Live WorldTime is the wall time at
   frame start, while logic advances in 40 ms quanta (observed −36..+13 ms). Keep 20 ms as the read-bracket rule.
   Compare clock phase with a tolerance of one observed live frame interval at that sample (≤ 60 ms here), and
   match samples by logic ordinal.
2. **Mid-walk position at 1 unit.** Clicks arrive by wall clock, so the logic step that consumes a click can
   differ by one, and mid-walk samples differed by 13–17 units. Either record the consuming step (read the
   client's path/input state) or allow one step of walking motion on samples taken while the hero is walking.
   Standing samples keep 1 unit.
3. **Composition-dependent components** (particles, effects, joints, frame light, image) can't be scored while
   other characters are present. Split live pool sums by owner (`+0x50` / `+0x34c`) and score only world-owned
   entries. Use a scene with no other characters, or draw them natively. Until then, declare these components
   unavailable.
4. **Object frame and hero animation at 0.05 frame** remain untested until animation starts are aligned (step 6);
   keep the limit.
5. **Visible-object count stays exact.** The 25–30% gap at an identical camera was a real discrepancy, the native
   2D frustum at 960×600. RENDER-TIME-003 closed it (see below).

**Not done.** No pool, animation or RNG phase was restored, so no aligned live comparison exists. The live scene
had other characters. There is no live-vs-live repeat from one start tile; runs 1–2 used the earlier
target-only sampler and could not be exported. Only Lorencia was captured; the other thirteen views were not.

## Zoom refusal and visible objects, RENDER-TIME-003 (2026-10-28)

Target: the pinned restored text (`scripts/pins.py` `text`, base `0x00401000`) and second section (`data`). Live
reads came from the owner's client: main.exe SHA-256 `3cf91f3c…`, Lorencia safe zone, mugl patches off,
960x600, under the game lock.

### The wheel route (verified under Unicorn; the live state read)

WM_MOUSEWHEEL never reaches the window procedure's own wheel case first. The procedure `0x0120fee3` sends 0x20a
to its default case `0x012102cf`, which first calls the UI layer `0x01d22c60`'s handler `0x00aefb79`. If that
returns 1, the procedure clears LPush/LButton, sets LPop and `0x0b436573`, and returns 0. The game's zoom code
is never reached.

**UI layer (`0x00aefb79`, wheel entry `0x00aefff8` of its message table `0x00af0219`).** It declines (returns 0) when:

- the hero byte `+0x190` is set;
- its base movie (`+0x88`, the movie loaded from `base.swf`) is absent;
- the GFx manager's window `+0x254` is shown.

Otherwise it converts lParam to a client point, `lParam - ClientToScreen(0,0)` (import slot `0x01a7c7e0`), and:

1. It consumes the event when the GFx mouse dispatch `0x00ac9800` reports it handled.
2. Otherwise it sends base.swf a wheel event: type 4, x, y, lines = `((delta << 7) / 120) / 120 * 3`.
3. It stores MouseWheel `0x0bdc59a4` = delta / 120.
4. It consumes the event when base.swf `HitTest(x, y, 3)` (vtable `+0xc0`) is true at the client point. The
   second test uses the raw 16-bit lParam, which for this message is a screen point. Each hit sends event 8.

**Game case `0x0121069d`.** It computes the same client point. It calls the zoom handler only when all of
these hold:

- the second dispatch did not take the event;
- the chat window `[0x01d22c6c]` byte `+0x68` is 0. This is `InMouseViewBox`, set by the chat movie's callback
  at `0x00c5fbee` from its `"hit"` argument.
- the GFx input object `[0x01d22c0c]+0x70` exists;
- that object's byte `+0xc` is 0. It is set at `0x00ac0406` when the hit window's type is 6.

It then stores MouseWheel. The handler `0x018588d9` refuses while NewUI window 0x3e is open (its IsVisible
`0x00eb5aba` returns byte `+8`) or in world 0x8b (`0x00da9d49`), and then applies the camera's existing rules.

**The two exclusive movies.** The GFx dispatcher `0x00abffce` feeds an event only to two movies when either is
shown, and then reports it handled at `0x00ac01d5`:

- "Caution" (manager `+0x88`, built at `0x00ac4d36`);
- "DivideWindow" (`+0x250`, built at `0x00ac4f6f`).

In every other case `handled` comes from each window's HandleMouse (base `0x00aaddc5`, vtable `+0x2c`). That
sets it only when its movie hit-tests at the cursor.

**Comparison.** `scripts/validate_wheel_route.py` (registered in `validators.toml`) executes the whole procedure
for WM_MOUSEWHEEL. The UI layer, the case, the handler, `0x0185a9bf` and the common exit `0x01211083` all run
in Unicorn against `reconstructed/camera/client_wheel.c`.

- The comparison covers the stage, MouseWheel, the button globals, `0x0b436573` and the camera/zoom state. It
  also covers the ordered dispatch calls with packed points, the base.swf events and hit tests, and the window
  0x3e queries.
- 1,200 cases, 0 mismatches. They cover all four stages: 355 UI layer, 352 case guard, 239 handler guard,
  254 zoom.
- GetScreenWidth: 601 cases, 0 mismatches, comparing the result and the ordered window queries.
- 10/10 compiled mutants are caught.
- Stubs, listed in `EXTRA_STUBS`: the GFx dispatch and base.swf's HitTest, which are Scaleform inputs; GetVisible;
  the message hooks; the log tail.

**Live read (session 20:08–20:16).** The new read-only `live-readers/rtguard` polled every guard state at 10 ms
while `rtinput` sent wheel +1/−1 at four spots: the run 3 spot, upper centre, the chat box and the Quest Info
panel. MouseWheel moved every time, and the zoom index stayed at 2 every time. At the world spots every
memory-held guard was clear:

- world 0, scene 6, settled 1;
- chat `InMouseViewBox` 0, type-6 flag 0;
- window 0x3e closed (byte +8 = 0);
- the GFx input object present;
- the dispatcher's path flag (input object `+0x20`) = 1. That is the normal per-window path, not the
  Caution/DivideWindow path.
- No GFx window hit (`[manager+0x2e4]` = 0).

Because MouseWheel was written, the UI layer's first dispatch did not take the event. By elimination the
wheel was consumed by base.swf's own hit test in the UI layer (`0x00af013b` or `0x00af01c3`). **Inference:** the
Scaleform hit result itself is not readable in memory. A later dispatch-side handling in the game case is not
excluded by the reads, but it needs the same GFx state that had just declined. The custom cursor clip of
`ExternalBase` sets `hitTestDisable` (decompiled `common/CustomMouse.as`), so it is not the hit.

**Native port.**

- `mu_frame_world_message` routes the wheel through `mu_client_mouse_wheel`. With no UI layer attached, the
  layer declines, as the client does without its base movie.
- Native gains the world 0x8b refusal. It also logs refusals.
- `mu-world --wheel-ui-hit` declares the recorded client's state: base.swf under the cursor. The live exporter
  writes `"wheel_ui_hit": true` into every live twin plan, and `render_time.py capture` passes the flag.
- With the GFx layer (`--gfx`), the existing first refusal (`mu_gfx_layer_mouse` kind 3) stays the native stand-in
  for dispatch and base hit. Whether native base.swf hit-tests where the client's does is untested, because no
  libmugfx build was available.

Tests:

- `reconstructed/camera/test_client_wheel.py`: five portable checks. A base hit or raw-lParam hit refuses; the
  free route zooms; the hero byte bypasses the layer; the case and handler guards refuse.
- `native/tests/test_render_time_003.py` (private): mu-world zooms without `--wheel-ui-hit` and refuses with it.

### Visible objects (verified static, native measured)

Both counters sum the same byte, object `+0x0b`, the TestFrustrum2D result of the render pass. So they measure
the same thing. The gap came from the frustum's width. The world render passes **GetScreenWidth `0x016bc355`**
(640x480 units) to:

- BeginOpengl;
- CreateFrustrum as aspect = width / 640 (`0x0185784f`, `0x018596ac`);
- CreateFrustrum2D's mode-0 scale through `0x0098c6b4` → `0x0098ac7c`.

GetScreenWidth's results are 640 / 450 / 260 / 70, depending on the NewUI side windows open. It never depends
on the window size. Native's `world/parts/terrain.c` used the window width (960), so its 2D frustum was 1.5×
wider. It now calls the ported `mu_client_screen_width`, with no NewUI window open natively.

At 640x480 nothing changes. At 960x600 the run 3 twin now matches live at every standing sample:

| Frames | Live visible | Native before | Native after |
|---|---|---|---|
| 0–40 | 198 | 249 | 198 |
| 60–120 | 177 | 262–289 | 177 |
| 140–200 | 182 | 257–280 | 182 |

Mid-walk samples differ by 1 (183/182), which is the known mid-walk path offset.
`test_render_time_003.py` checks the frame-0 count, 198, at both window sizes.

### Comparison on run 3 / run 4

The runs were re-exported from the kept raw samples with the new plan field. Every scored value equals the
RENDER-TIME-002 export: only the plan hash changed, and the image summaries were carried over.

| Component (failing samples) | Run 3 before | Run 3 after | Run 4 before | Run 4 after |
|---|---|---|---|---|
| **Total** (`compare --mode live`) | 477 | **400** | 433 | **390** |
| camera eye z / FOV / pitch | 8 / 8 / 8 | 0 / 0 / 0 | 8 / 8 / 8 | 0 / 0 / 0 |
| camera hero/eye x, hero/eye y | 0/0, 9/9 | 0/0, 1/1 | 1/1, 1/1 | 1/1, 1/1 |
| hero animation frame | 14 | 6 | 13 | 13 |
| objects visible | 21 | 0 | 21 | 1 |
| objects frame / prior frame | 3 / 3 | 0 / 0 | 1 / 2 | 0 / 0 |
| particles (10 sums) | 194 | 195 | 185 | 188 |
| environment (6) | 101 | 97 | 101 | 101 |
| frame light (3) | 63 | 63 | 63 | 63 |
| sky[3] | 16 | 16 | 13 | 13 |
| WorldTime/step rows | 20 | 20 | 6 | 6 |
| path coverage (≥1° zoom) | 0 | 1 | 0 | 1 |

`compare --mode live` still fails on:

- the phase gate: unaligned;
- unaligned pools, animation and RNG;
- other characters' particles and frame light;
- the WorldTime policy (items 1–2 above).

These limits are unchanged. One new failure is a plan-design consequence: the Lorencia plan requires ≥1° of
native zoom, and the faithful twin no longer zooms. A later live plan must not rely on the wheel at a spot
where base.swf takes it.

## LIVE half procedure, as planned by RENDER-TIME-001

1. In a future authorized live session, read `mu-mac-tools/GAME-LOCK.md` and the
   [service contract](service-contract.md). Acquire the shared game lock with the documented `mkdir`/owner
   protocol and matching `MU_AGENT`/`MU_LOCK_ID`. It is distinct from the native merge lock. Leave any client
   the operator did not start alone. Use one logged-in client at a time, runs <=3 minutes and the lock <=15
   minutes. Split the fourteen views across lock sessions. Do not expose account/character names in outputs.
2. Use a dedicated capture setup in the Wine track. Save its configuration, disable mugl hotpatches before
   the capture process starts, and verify the effective configuration in its logs. The current hotpatch build
   reads `C:\mutools\mugl-hotpatch.txt`; write mask `0` in that dedicated setup, rather than deleting the file,
   which selects the default mask. `MUGL_MASK=0` applies to test programs, not main.exe. `MUGL_MODE=off` only
   disables GL buffering and does not disable CPU patches or intercepted integer/double conversions. For a
   strict original-GL reference use the Wine track's documented real-driver path without mugl. Record DLL
   provenance, effective mask and buffering mode. Do not enable performance or clock patches for scoring.
   Do not change a running player's setup. Restore the saved capture configuration afterward.
3. Reach the named world/start tile with the interface. Record client dimensions and exact camera values.
   The shared scripts require a 640x480 drawable client area, with title-bar/Retina coordinates translated by
   the injector. Arm INPUT-001's 25 Hz physical-input loop at a recorded WorldTime boundary. Do not replace
   physical clicks with position writes. Confirm the world/tile, walking and camera path after replay.
4. Capture post-draw samples at the declared frame ordinals. Bracket each window-only screenshot/read batch
   with WorldTime reads at `0x06fce370`; retain the bracket and actual logic ordinal. Reject batches whose
   uncertainty exceeds 20 ms. Record the join/entry epoch, first draw, arm epoch, WorldTime per sample and
   ambient logic counter `0x0bdc5eb0`, which C2 identified as a logic ordinal, not elapsed milliseconds.
   Export objread's time-varying fields and lightread's primary/frame grids to the same compact summaries.
   Add explicit legacy particle, effect, joint, boid/fish/weather and sprite pool observations where available.
   Summarize and delete raw intermediate dumps promptly; save only three screenshots per view.
5. Match samples by the recorded arm epoch and relative WorldTime, never by minimum image error. Supply the
   native epoch through `start_world_time_ms` in a private plan, using the observed first-sample WorldTime.
   This aligns the clock input, not prior state. Draw every native iteration and preserve the observed tick
   and draw ordering. Verify step ordinals and absolute phase for periodic functions. An 8-second relative
   time match alone does not align a sine driven by absolute WorldTime.
6. Establish pool ages, animation starts, ambient-counter phase and RNG provenance independently. Current
   saved snapshots lack those inputs, and native module RNG streams are separate. If they cannot be aligned,
   leave phase unaligned and retain diagnostics. Do not relabel a fresh native world as aligned. A future
   replay/adapter is required before claiming temporal equality. Likewise, coarse image scoring requires
   identical image composition, dimensions, HUD/hero policy and grid orientation on both sides. Do not score
   an original HUD against a native no-HUD view as if composition matched.
7. The future live adapter must export the schema above, input/script/plan hashes, effective patch provenance,
   WorldTime brackets and phase evidence. Run `compare --mode live` only after reviewing that evidence and
   approving the threshold policy. Release the game lock and restore the capture setup. No exporter, live
   capture, original-pool restoration or live score was implemented or run in this native milestone.

The final locked tree includes main `7ce87c6`. The full Mac gate passed 1,544 tests across 38 suites with
189 explicit skips and zero failures. The post-merge private temporal rerun passed 16/16 tests, including
294 equal sample pairs across fourteen views and 21 equal common Icarus samples across two cadences.
Full counts and measured native coverage are in [the milestone handoff](../handoffs/RENDER-TIME-001.md).
