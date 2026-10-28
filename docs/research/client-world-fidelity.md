# World fidelity tour: the native world against the live client, map by map (NATIVE-FIDELITY-002)

Earlier live-versus-native checks were made almost only in Lorencia. This milestone builds a repeatable comparison of
the native world with the running client across the main maps, ranks what differs and fixes the most visible
differences from the client's own code.

Labels, as in the other notes:

- **verified**: the client's instructions ran in Unicorn and equalled the authored C in every compared case;
- **static**: read from decoded instructions, not executed;
- **live**: read from (or seen in) the running client this project started, under the game lock;
- **gap**: a difference whose client logic was not found; it is documented, not imitated.

Inputs: the pinned restored text (`2bd5f2e9…3724`) at `0x00401000` and the second image section (`c985e2e6…672f`) at
`0x01a7c000`.

## 1. Method

### Live side (2026-10-22, one session, lock held 12:36–12:43)

`mu-autologin.sh` (Nighty, MTM-1), then the Move window (M) for each map; the window's list was scrolled with a
mouse-wheel command added to a local copy of `muinput` (`scratch/fidelity2/muinput`, not in the bottle's own tools).
At each warp arrival tile, with the default camera and the window at the bottle's default 1722 × 1048 client area
(1722 × 1076 with the title bar), a local script (`scratch/fidelity2/live/cap.sh`) took:

- a window-only shot (`winshot.swift`) and the HUD crop (map name and tile);
- `objread` (static objects in the 256 sector lists, plus the scene globals: camera angle and position, FOV, far
  plane, WorldTime, scene flag);
- `lightread` (the model container, the characters, and the primary and frame terrain light grids).

Maps (world index, arrival tile): Lorencia (0, 137,130), Dungeon (1, 108,247), Devias 4 (2, 71,181), Devias town
(2, 199,48), Noria (3, 174,109), Lost Tower (4, 208,79), Atlans (7, 19,15), Tarkan (8, 195,70), Icarus (10, 15,13),
Aida (33, 84,11), Kanturu Ruins (37, 19,218), Elbeland (51, 53,224), Raklion (57, 224,211), Karutan (80, 125,123).
Vulcanus (PvP) and event maps were not visited. No fight, no item action; only the warp costs were spent; Nighty
ended in Lorencia; client and launcher were closed before the lock was released.

The object snapshots are the first live placements of eleven of these worlds (NATIVE-OBJECTS-001 had read only
Lorencia, the character-select and login worlds and Tormenta Island). `scripts/live_objects_to_plain.py` turns them
into the local `EncTerrain<n>.plain` files every native front end loads (`--objects-dir`). In every world the number
of linked objects equals the count global, and the count fits the installed file's length for exactly one record
version, as before; Devias (2,308 linked for 2,305 in the file) and Raklion (1,521 for 1,519) have objects that
world code creates itself (types 422–424 in Devias).

### Native side

`mu-world --headless --backend gl` at the same tile, window size and world, with the local plaintexts, 25 logic
steps. The new `--fidelity-dump PREFIX` option writes, at the end of the run, the native OBJECT images in `objread`'s
layout (`PREFIX-obj.bin`) and the primary and frame light grids in `lightread`'s layout (`PREFIX-light.bin`), so both
sides are compared with the same readers.

### The tour script

`scripts/fidelity_tour.py` (`manifest`, `render`, `compare`, `run`) takes a JSON manifest (format in the script's
docstring) and writes, per map, `side.png` (live | native client areas) and `diff.png` (|Δ| × 4, HUD masks greyed),
and a `scoreboard.json` / `scoreboard.md`:

| Measure | From |
|---|---|
| camera: eye distance, pitch, FOV and far-plane differences | objread globals against the native frame report |
| image: masked mean \|Δ\|, share of pixels off by more than 24/255, colour cast, luminance quantiles, 4 × 4 region grid | the shots; HUD and hero masked |
| objects: missing (live only), extra (native only), per-field differences of the static OBJECT fields (flags, HiddenMesh, BlendMesh, render mode, range, velocity, alpha target, light, angle, position…), near the hero and map-wide | objread snapshot against the native dump, matched by type and start position |
| light: primary grid (light map × terrain normal term) map-wide, frame grid (with dynamic lights) around the hero | lightread against the native dump |

Portable tests: `native/tests/test_native_fidelity2.py` (synthetic snapshots, light grids, images and a synthetic
world through `mu-walk --fidelity-dump`). The live captures, renders and scoreboards stay local:
`~/Documents/mu-mac-tools/native/renders/fidelity2/{live,before,after*}/`.

## 2. What the first tour found (before)

The camera agrees everywhere: eye within 0.007 world units of the live camera, pitch −48.5, FOV 39, far plane
3257.8 (Elbeland 3220) in all fourteen captures. The **primary terrain light equals the live grid exactly in every
world** (mean |Δ| 0.0 over the 65,536 cells), which confirms the terrain light-map path on eleven more worlds.

| Map | Mean \|Δ\| | Off > 24 | Most visible differences, ranked |
|---|---:|---:|---|
| Icarus | 67.7 | 0.86 | **whole screen**: native draws a grass terrain; the client draws none (sky colour, clouds, pillars) |
| Raklion | 22.7 | 0.27 | whole screen paler/brighter in the client (white haze, snow sparkles); see gaps |
| Tarkan | 22.5 | 0.35 | whole screen brighter in the client, strongest near the camera (sand haze); see gaps |
| Noria | 19.4 | 0.20 | 2,726 objects with a BlendMesh the native leaves −1; 16 drawn after the characters |
| Elbeland | 18.0 | 0.19 | players; 572 objects with another TestFrustrum2D range, 265 HiddenMesh |
| Lorencia | 13.6 | 0.14 | players and their effects; terrain and objects match |
| Kanturu | 9.9 | 0.13 | brazier fires and their red terrain light missing; 760 range, 77 HiddenMesh differences |
| Atlans | 7.7 | 0.09 | 812 HiddenMesh, 27 BlendMesh, 21 BlendMeshLight differences (crystals) |
| Dungeon | 6.9 | 0.14 | wall torches' fire and their light missing (frame light near the hero off by 0.084 mean, 149 tiles > 0.05) |
| Karutan | 4.9 | 0.04 | brazier fire missing; 66 HiddenMesh |
| Devias | 3.6 | 0.03 | 201 BlendMesh; three code-created objects missing |
| Aida | 3.4 | 0.04 | an object light source (frame light up to 60 in one tile); 70 HiddenMesh |
| Lost Tower | 0.3 | 0.00 | 42 BlendMesh |

(Mean |Δ| in 8-bit units over the masked client area; the live shots include other players, their pets and shops,
which the native world does not have.)

## 3. Fixes

### 3.1 No terrain in Icarus (verified)

The main render scene `0x0185916b` chooses its terrain and first object pass in `0x018597c2..0x0185985e`:

```
if [0x01ec9188] (0x00deeaff) is clear:
    world 0x27:                 RenderTerrain(0) unless the Kanturu event state 0x009a645f answers 1
    worlds 10, 0x84 and -1:     nothing
    otherwise:                  RenderObjects first in worlds 0x3f and 0x52..0x5a (0x00e94004 / 0x00e3068f),
                                then RenderTerrain(0)
RenderObjects, unless the world is 0x3f or 0x52..0x5a
```

Icarus (world 10) has no terrain at all: the clear colour (3, 25, 44)/256 is the sky between the pillars.
`reconstructed/terrain` `mu_terrain_scene_passes` restates the slice; `mu-world`/`mu-walk`/mu-client skip the
terrain where it says so.

`scripts/validate_world_fidelity.py --only scene` runs the slice as client code (the three predicates execute;
RenderTerrain, RenderObjects and the Kanturu singleton/state are recorded stubs) for random and listed worlds, both
top-flag states and both Kanturu answers: **500 / 500 equal**; planted mistakes (Icarus draws the terrain; objects
first only in 0x3f) are detected in 6 and 28 of 300 cases.

Icarus after the fix: mean |Δ| 67.7 → 61.8. The structures, their positions and the sky now match; the clouds that
fill the client's screen are still missing (gap 1).

### 3.2 Per-world object creation (verified)

CreateObject `0x016d8538` has its own cases for worlds 1, 2, 3, 7, 8 and 0x37 (`0x016d8e3a..0x016d99bf`); other
worlds go through a chain of world-group hooks and then the world manager's handler (slot 0x2c). The world handler
classes and their worlds were mapped from the handler factory `0x00ea488e` (48 classes, world → constructor →
vtable; e.g. Raklion 0x39/0x3a vtable `0x01aad9d0`, Karutan 0x50/0x51 `0x01aa9a4c`). Of the toured worlds only
Kanturu (hook `0x00e74a58`, world 0x25) and Elbeland (hook `0x00e30a02`, 0x33) set fields at creation; the Raklion and
Karutan slots only create effects for code-made types.

`reconstructed/objects` `mu_obj_create` now restates them: BlendMesh of Noria (types 1, 9, 0x11..0x13, 0x25) and
Devias (0x13, 0x36, 0x38, 0x4e, 0x5c, 0x5d), HiddenMesh −2 and operable registration (Dungeon 0x3c, Devias 0x5b,
0x64, Noria 0x26, Atlans 0x27, Tarkan 0x61, 0x68, Elbeland 0x8f, 0xa5), Devias's door angles, the drawn-after flag
and speed of Tarkan 0x59/0x5d, ranges (Devias 0x7a/0x7b −600, Kanturu −400/−100, Elbeland −300), world 0x37's two
fixed objects, and the CreateEffect calls of type 0x1a8 in Devias and Noria (logged; their effect objects are the
three Devias objects the tour finds missing). `validate_object_render.py --only create`: **3,000 / 3,000** equal over
worlds 0, 1, 2, 3, 7, 8, 0x25, 0x33, 0x37, 0x8d (the Kanturu and Elbeland chains run as client code, the runtime
singletons are stubbed), 157 CreateEffect calls compared; three new planted mistakes detected.

### 3.3 Per-world object moves: torches, braziers, crystals (verified)

MoveObject `0x017ff238` switches on the world (`0x017ff8ad`, jump table `0x01801668`) and falls back to the same
hook chain. Restated now (`mu_obj_move`):

| World | Cases |
|---|---|
| 1 Dungeon | wall torches 0x29/0x2a: CreateFire (0, −30, 240) / (0, 0, 190), i.e. flames and their terrain light; 0x3d BlendMesh 4 with a u scroll; 0x16..0x18 StreamMesh and v scroll; hidden markers; 0x34 an effect one step in three |
| 3 Noria | 0x12 v scroll; 0x1a8 particle `0x7f26` |
| 4 Lost Tower | BlendMesh of 0x12/0x17 and 0x13/0x14 (with u scroll); 0x18 effect `0x7f42` one step in 64; hidden markers; 0x26/0x27 call `0x017f6ca7` (logged, not reconstructed) |
| 7 Atlans | bubble emitter 0x16 (timer, particle `0x7fcd`, HiddenMesh −2); crystals 0x17/0x20/0x22/0x28 BlendMesh with a sine-pulsed BlendMeshLight |
| 0x21/0x36 Aida (hook `0x00d6202f`) | two light sources (range 2), v scrolls, hidden markers, ambient sound |
| 0x25/0x28 Kanturu (hook `0x00e74ae0`) | brazier and torch lights 0x3c/0x3d/0x46 (ranges 3/4), pulsing lights, bubbles, scrolls, hidden markers, ambient sounds |
| 0x50/0x51 Karutan (handler slot `0x00e13a9e`) | brazier light 0x71 (range 3), hidden markers, a sound |

`validate_object_render.py --only move`: **3,000 / 3,000** equal (worlds 0, 1, 3, 4, 7, 0x21, 0x25, 0x28, 0x36, 0x50,
0x51, 0x8d complete, 19 worlds up to the switch; the client's `sin` wrapper runs as client code; the Karutan slot runs
on the object the chain leaves); six new planted mistakes detected (3–15 of 600 cases each). The full validator
(nine families, 2,000 cases each) passes with all 15 planted mistakes detected.

The native sidecar of hidden types (`EncTerrain<n>.hidden`) is kept outside Lorencia, Tormenta and the two scene
worlds: most of those −2 values are written when an object is drawn (emitters), which the move cases now reproduce
only for the ported worlds.

### 3.4 Icarus's rising cloud puffs (verified; live)

A third live session (2026-10-22, lock 13:38–13:41, Nighty in Icarus then back to Lorencia) read the effect pool
`0x0a4ca430` six times 0.4 s apart: every live effect was `0x7ef7` (flare) subtype 0 (20–25 of them, scale 3,
light 0.3, LifeTime up to 400, drifting up), none of the cloud model `0x1a1`. Their source is MoveObjects' pre-pass
`0x01802168`: in world 10, after `0x018016b0`, one step in ten a CreateEffect `0x7ef7` subtype 0 at the hero +
(rand % 5000 − 2500, rand % 5000 − 2500, −1000) (`0x018021c3..0x01802302`). Reconstructed and verified:

| Piece | Client | C | Unicorn |
|---|---|---|---|
| pre-pass, sky worlds | `0x01802168` (world 10, 0x84; `0x018016b0` recorded) | `mu_obj_move_pre_sky` | 2,000 / 2,000; planted mistake (z −900) caught in 35 / 600 |
| puff effect create | CreateEffect `0x013c7082`: light 0.3, direction from 70° / 30° and (rand % 5 + 9) · 0.5, scale 3, LifeTime 400 | `mu_sfx_effect_create` | in 600 / 600 |
| puff effect move | MoveEffect `0x0144ce38`: position += direction, rise slows by 0.01, a flare particle subtype 1 per move, dies when the rise passes −2; LifeTime path `0x0150cb88` moves it again on an odd LifeTime | `mu_sfx_effect_move` | in 600 / 600; new negative control (one move only) 18 differ |
| flare particle subtype 1 | CreateParticle `0x015eee83` (LifeTime 50), MoveParticles `0x016635ad` (light × 0.9, scale × 0.95), RenderParticles | `reconstructed/particles` | create/move/render in 1,500 cases each |

MoveEffect's frame is 0x16eb4 bytes, so the effect validator now runs with a deeper emulated stack. The particle run
has one 1-ulp difference (1 / 1,500 move cases) in an unrelated kind, smoke `0x7f5a` subtype 0x75, whose motion goes
through the host-libm substitution of the client's sin/cos (AngleToVector); it is reported, not hidden.

`mu-world` feeds the pre-pass into its world effect pool (the module of NATIVE-JOINT-001). After 400 steps in Icarus the
tour's mean |Δ| is 54.7 (61.8 with the terrain skip only). Still missing there (static reading): `0x018016b0`, which
one step in fifty adds a terrain light, the cloud model effect `0x1a1` (CreateEffect `0x013d7a72`: scale 14, LifeTime 2,
reconstructed and verified, not yet created natively) and lightning joints `0x7f7d` subtype 10; the `cloudLight`
sprites and `0x7f7c` joints of the world-10 object routine `0x0180249e`; and the soft grey cloud layer of the live view,
whose source was not identified.

### 3.5 Icarus sky and dragons, RENDER-WORLDS-C

The named sky paths now execute in native C: `0x018016b0` emits its light, cloud model `0x1a1`, and two
`0x7f7d` joints of subtype **0**, correcting the earlier static subtype-10 label. The world-10 object slice
`0x0180249e..0x01802692` creates `cloudLight` sprites and `0x7f7c/6` swirls. The existing move-pass events now
reach the native hosts. `0x00ca2154` creates three dragons, with the existing shared flight/steering, and ten
emitter records whose mover `0x00ca3189` is also reconstructed. OpenMonster(31) loads Monster32, not Monster31.

Evidence uses the same text/data pins as section 1. `scripts/validate_icarus.py` compares the compiled C and
ordered host calls, including random consumption. The existing joint and environment validators cover the
lifecycle. The scoped run passes 5,240 comparisons with zero mismatches and 8/8 compiled mutants; its 40 dragon
sessions exercise 20 ticks each, alternating clean/fuzzed pools and directed warps. Exact commands and limitations are in [the handoff](../handoffs/RENDER-WORLDS-C.md).

This is not a claim that the persistent grey layer matches the capture. At 25 steps the image error regresses
61.760 → 62.030, and at 400 steps 54.673 → 60.935. The verified sky helper emits only once in fifty steps and
its cloud model lives two steps. Its port, cloud lights and dragons do not explain the persistent coverage in
the screenshot. Other thirteen capture hashes remain unchanged. Full joint/sprite/attached-tree state at the
screenshot frame is still needed; no live capture was attempted here.

### Before and after

| Map | Mean \|Δ\| before → after | Off > 24 | Frame light Δ near hero | Object field differences (map-wide) |
|---|---|---|---|---|
| Dungeon | 6.9 → **2.0** | 0.136 → 0.008 | 0.084 → 0.044 | 0 |
| Kanturu | 9.9 → **3.7** | 0.129 → 0.028 | 0.057 → 0.011 | 841 → 3 |
| Atlans | 7.7 → **5.6** | 0.089 → 0.056 | 0.014 | 861 → 57 (pulsing light values) |
| Karutan | 4.9 → 4.5 | 0.043 → 0.037 | 0.022 → 0.013 | 72 → 6 |
| Noria | 19.4 → 19.2 | | | 2,749 → 23 |
| Elbeland | 18.0 | | | 856 → 19 |
| Devias (4 / town) | 3.6 / 3.5 | | | 203 / 212 → 0 / 6 |
| Lost Tower | 0.34 → 0.31 | | | 42 → 25 |
| Icarus | 67.7 → 61.8 (terrain) → 54.7 (puffs, after 400 steps) | 0.857 → 0.760 | | |

Remaining field differences are values the client changes while it draws or animates (pulsing lights, alpha and speed
of objects the client has not moved yet, Raklion and Tarkan's drawn-after flags of types the visual pass sets).

## 4. Gaps (ranked by visibility)

1. **Icarus cover and emitter gap closed by RENDER-WORLDS-C2** (section 7). The remaining image error includes
   unsynchronised cloud rotation, puff distribution, ribbons, dragons and uncaptured hero equipment. The earlier
   RENDER-WORLDS-C results in section 3.5 are historical.
2. **Tarkan and Raklion haze**: RENDER-WORLDS-F recovers the missing additive screen passes. See [the verified finding](client-world-haze.md) for instruction evidence, native measurements and unavailable original-image scores. The following diagnosis is historical.

   The earlier observation was that the client's terrain is up to ~1.35× brighter, the darker light-map areas most, so
   the contrast is compressed; the pattern stays with the ground when the hero moves (second session, two positions
   per map). The primary and frame light grids equal the native ones, the light-offset grid `0x0bc35430` is all zero,
   FogEnable is off and the fog globals are the BeginOpengl defaults (live reads), and the textures are the same. Both
   folders hold a `Fog.OZJ` that no string in the captured code names. Two further live sessions:
   - a `mugl` GL trace of one frame in Lorencia and one in Tarkan (`C:\mutools\mugl-trace.txt`) shows the same
     terrain call families (RenderFace `0x016cfab3` / alpha face `0x016cfb53`, grass `0x016d16bf`) and the same state
     and texture-environment calls; Tarkan only adds 75 RenderPlane3D quads (`0x0184c2bc`, its leaves, 16 × 16
     texels) and two screen quads (`0x0184f707`). No extra terrain pass, fog or lighting state.
   - an A/B in Tarkan at one tile with the Wine-track `mugl` batching (`mugl-mode.txt` `off`) and all its code
     hotpatches (`mugl-hotpatch.txt` 0) switched off, restored afterwards: the masked mean |Δ| against the native frame
     drops from 18.8 to 13.2 and some regions darken by up to 10 %; others stay brighter than the native, and a capture
     after reloading the map without the JPEG hotpatch is still brighter. Part of the difference therefore comes from
     the Wine-track renderer (to report to the mu-the-matrix-mac track); the rest is not explained. Fine shading
     comparisons against the Mac-hosted client should take this into account.
3. The brazier and torch flames themselves in Kanturu and Karutan (their lights are ported; the flames come from
   RenderObjectVisual `0x017f9758`'s world cases, now covered by RENDER-WORLDS-A below), and the visual-pass flags (`+0xa` drawn after the
   characters in Noria, Elbeland, Raklion, Karutan).
4. RENDER-WORLDS-B reconstructs the Devias, Tarkan, Elbeland and Raklion move cases, code-created placements
   and Raklion snow. See section 5 for verified coverage and remaining nested-effect and comparison limits.

## 5. RENDER-WORLDS-B, 2026-10-27

**Verified.** Per-world C is in `reconstructed/objects/{devias,tarkan,elbeland,raklion}.c`; snow is in
`reconstructed/environment/raklion_snow.c`. `scripts/validate_worlds_b.py` compares compiled production C to the
same pinned text and second image section used above, without starting the client. Eight families, 500 cases each,
**4,000 equal, zero mismatches, zero stopped; all 10 compiled planted mistakes detected**.

| Family | Original instructions | Compared |
|---|---|---|
| Devias move | `0x017fffda..0x018006dd` | doors at 200-unit boundary and cardinal/noncardinal headings, bounds gate, flicker, fire and two particle calls; object bytes, ordered calls, RNG |
| Tarkan move | `0x01800bf8..0x018013a0` | all 18 special types, both light ranges, scroll moduli, sine and signed cosine clock; object bytes, ordered calls |
| Elbeland move | `0x00e30b86..0x00e31169`, helper `0x00e34169` | world-51 sound/safe-zone gates, lights, scrolls, pulse, hidden markers, type 62's boid slot 1 creation; dead/live pool bytes and RNG |
| Raklion move | `0x00e94619..0x00e946a5` | type 22 pulse, hidden types 70/80, default path |
| Devias placements | `0x018394d3..0x01839797` | the three complete constructor records, types 422, 423, 424 |
| Raklion placements | `0x0183f710..0x0183fa87` | worlds 57/58, two constructor records per world |
| Raklion create | `0x00e943c0..0x00e94616` | three effect calls of type 427, offsets and full argument tails |
| Raklion snow | `0x00e9ec6a..0x00e9ee77` | scale branches, hero-relative position, angle, rotated velocity, untouched leaf bytes and RNG |

The Devias/Tarkan families enter their switch branches after the generic tick with a declared caller frame.
They do not re-prove the generic tick. Engine services are recording stubs. World membership answers are supplied
explicitly. Handler state is seeded with its event-timer flag clear. The boid live setter/getter, trigonometric
wrappers, AngleMatrix, VectorRotate and door
TurnAngle2 execute as original instructions. Raklion's inherited handler timer is covered only with flag `+0x23` clear;
its active event timer is outside this static-world reconstruction. Placement families execute the loader slices and record the
constructor arguments; model/texture loading and CreateObject allocation are stubbed. Fixed placement cases are
repeated, not distinct worlds or assets. Mutants cover the door boundary, flicker, placement coordinate, terrain
light range, scroll rate, live-slot guard, pulse rate, effect height and snow velocity.

**Native integration.** The object loader adds code-created records before model loading, skips exact type/position
duplicates in `--keep-all` exports, and loads their named NPC models. The native type capacity includes 422–427.
Shared dispatch changes call the per-world routines. A two-line world hook supplies Elbeland's shared boid pool and
safe-zone bit. Raklion's leaf creator feeds the existing MoveLeaves, default movement and billboard rendering.
Creation effects are queued until the native effect callback exists. Only this group's worlds use that queue.

**Snapshot and render checks.** The fourteen-map tour ran before and after on this branch against the local
2026-10-22 object/light captures. The orchestrator confirms that the original live PNGs were deleted in the 2026-10-23 cleanup. The object/light
snapshots and retained score reports are the authoritative live evidence. Therefore fresh image mean error against the live client is
**unavailable**, not zero or copied from the old report. Native GL frames were inspected for Devias town, Elbeland
and Raklion. All nine unaffected worlds' final PNG SHA-256 values are unchanged. Devias 4 and Tarkan also have
unchanged final PNGs at their arrival cameras; their new behavior is covered by instruction cases elsewhere.

| Capture | Missing objects before → after | Near-hero frame-light mean absolute difference before → after |
|---|---:|---:|
| Devias 4 | 3 → 0 | 0 → 0 |
| Devias town | 3 → 0 | 0.00386 → 0.00068 |
| Tarkan | 0 → 0 | 0 → 0 |
| Elbeland | 0 → 0 | 0.03336 → 0.02078 |
| Raklion | 2 → 0 | 0.02574 → 0.02574 |

The local Mac gate on the combined branch passed 1,364 tests with 159 explicit skips and no failures;
publication audit accepted 1,203 files with none rejected. Native fixture, viewer and read-only reader checks passed.

No extra placements in these captures; primary light remains exactly equal in all fourteen captures. Devias town's
static-field differences fall 6 → 4, with time-dependent flicker remaining. Tarkan has three new BlendMesh
comparisons of type 82, which the verified move case sets to zero but the old live snapshot retained as -1.
This is reported rather than forcing the snapshot value. Raklion now has actual snow motion instead of live
zero-initialized leaf records. No live game was used, and no renders or captured bytes are committed.

**Remaining boundaries.** The nested warp-model effects `0x1a8..0x1ad` now reach the existing effect callback, whose
factory still rejects these unreconstructed effect kinds. Their effect lifecycle/rendering is not claimed here.
Elbeland's `0x1a3` boid creation is wired, but its separate environment mover/model renderer remains unported.
Sound calls are compared and counted by the object host, as before. The Tarkan/Raklion haze, visual-pass fields,
other world-handler classes and siblings A/C remain separate work. Next step: take fresh live captures of Devias, Tarkan, Elbeland and Raklion under the shared game lock in a
separate authorized run, then rerun the image-error tour. This run did not start a client.

## RENDER-WORLDS-A, 2026-10-27

Authored per-world files in `reconstructed/objects/world_*_visual.c` implement the scoped Kanturu/Karutan
visuals and the deferred body/mesh handlers. `world_after.c` dispatches only the four requested world groups.
The native object runtime consumes their particle/sprite logs and draws the second pass after characters/items,
after the environment, matching RenderMainScene's recorded `0x016d6949` call. Raklion's opaque meshes remain in the first pass and its glow meshes in the second.
Elbeland's deferred lamps also reach the sprite pool. Existing login/character-select dispatch remains intact.

### Verified instruction comparisons

The executable target remains SHA-256 `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
Text and second-image-data use the repository's capture09/run10 pins. `validate_render_worlds_a.py` records
complete routine hashes with its report and compares compiled authored C against the original instructions.

| Family | Cases | Boundary |
|---|---:|---|
| Kanturu flames, `0x00e75089` | 1,000 | Types 59 smoke subtype 21, 61 fantaF, 70 bone-6 glow; type 60 has no visual call here; worlds 37/40 |
| Karutan brazier, `0x00e13be4` | 1,000 | Type 113, flare sprite and firehik01/02/03 particle choice; worlds 80/81 |
| Second pass, `0x016d6949` | 1,000 | Worlds 3/51/57/58/80/81; sectors, objects, counter, live/flag checks, special predicate and draw calls |
| Deferred draw bodies/meshes | 1,000 | Noria `0x016d67c7`, Elbeland `0x00e321bb`, Raklion `0x00e96536`, Karutan `0x00e1543e`; object writes and calls, including Elbeland bone sprites |
| Flag-writing branches | 1,000 | Elbeland/Raklion/Karutan type sets, including negative types and pre-existing flag values; only the flag byte is claimed by this family |
| Raklion first meshes | 1,000 | Types 83/92 at `0x00e949f8`; the body meshes before their deferred glow |
| Particle creation | 1,000 | Smoke01/21, fantaF/0, firehik01/0, firehik02/4, firehik03/0 |
| Particle movement | 1,000 | Same five kinds, lifetime/fade/scale/rise/rotation and existing common motion |
| Particle rendering | 1,000 | Same kinds, bitmap/state/Sprite call; smoke21 uses subtract blending |

**9,000 cases, zero mismatches, zero stopped cases; 13/13 compiled planted mistakes detected.** Bone transforms,
particle/sprite leaf calls and mesh/body calls are explicit recording boundaries. Sine executes as original code;
the C uses the repository's established float-rounded host-sine equivalent. The new bitmap names are static reads
of LoadBitmap at `0x01820fcf`, `0x0182188f`, `0x01821b2f`, `0x01821b4f`, not guessed assets.

The synthetic native regression exercises hidden Kanturu emission, Karutan particle/sprite creation and drawing,
and all four world groups' after-pass bodies on both GL and software backends, ten native sessions in three tests.
The earlier local gate passed 1,397 tests with 166 explicit skips and no failures; the audit accepts
1,261 files with no rejection. Item/audio integration preserves all 53 final native frame hashes.
The character-select build dependency now uses `HEADERS`, replacing undefined `CORE_HDR`, so changes to the
particle table's struct layout rebuild every character-select consumer.

### Fidelity and remaining evidence limits

No original client or launcher ran. Local artifacts are under `mu-mac-tools/native/scratch/render-worlds/` and
`mu-mac-tools/native/renders/render-worlds-a/`; none are committed.

The owner confirmed the October 23 image cleanup. Only Dungeon, Icarus and Kanturu survive at full resolution in
`renders/readme-sources/`. The surviving Kanturu image is the live visual oracle; object/light snapshots and
historical score reports remain the live evidence for Karutan/Noria/Elbeland/Raklion. Native before/after frames
cover those four maps. Fresh live captures of them, under the game lock in a later run, remain the next step.

The final tour baseline is main `54ae63f`, including siblings B/C and SESSION-VIEWPORT-001. At the tour's
25 logic steps and two rendered frames, Kanturu masked mean error is **3.717 -> 4.006**. That sparse sampling
creates only two particles. Rendering every frame on both builds gives **3.717 -> 3.444**, and the share of pixels
off by more than 24 falls **0.0275 -> 0.0245**. The after build creates 53 particles, visibly at the captured torch
positions. These are unsynchronised particle phases, not exact frame equality.

The nine unaffected tour entries retain both frame hashes, eighteen unchanged PNGs. Raklion also retains both
hashes at this camera, while its deferred flags are corrected. Primary terrain light equals the captured grid in
all fourteen maps. The native before/after images for the four maps without live PNGs were inspected locally.

Near-hero `after_character` field differences against the October 22 snapshots are Noria **15 -> 15**,
Elbeland **12 -> 0**, Raklion **10 -> 0**, Karutan **6 -> 6**. Noria type 19 is selected by `0x017fece6` before
any live/flag gate; this port reproduces that selector without inventing the separate capture's flag writer.
Karutan's remaining six differences are on different records: before they are live 1/native 0; after they are
live 0/native 1. The unchanged count does not mean that no flags were written. Capture history and the native
pass's visibility are not synchronized, so the exact remaining cause needs a fresh capture. Other per-world body
effects, world handlers, creation effects, region import and shadow/custom registries are outside A. Sibling B/C
implementations were retained during integration.

See [the milestone handoff](../handoffs/RENDER-WORLDS-A.md) for the integrated gate and merge record.

### Resume integration, 2026-10-28

Latest main `0a85441` and source checkpoint `c235421` were rebuilt separately in the existing A worktree.
`parts.def` now places the deferred draw at 85 in both backends, after the environment. The order adapter
anchors it to the recorded original `0x016d6949` call. Missing-anchor and call-reordering tests cover it;
the GL viewer marker follows the deferred pass. Other native order adapters remain unchanged.
Both A and input validator registrations survive the merge. A's manifest now expects 9,000 total cases,
correcting the prior per-family count of 1,000, without changing the comparison itself.

Registered validators pass 9,000 A cases and 2,400 order cases, zero mismatches/stops, 23/23 compiled mutants
caught and 294/294 order branch edges. Full Mac gate: 1,444 tests across 38 discovery suites, 175 explicit skips, zero failures; audit 1,324 files, zero rejected.
All six fixture scenarios and native viewer/readers builds pass. No reader was run against a client.

The refreshed fourteen-view tour reproduces the reported fidelity numbers against the surviving Kanturu PNG:
sparse error 3.717 -> 4.006 and share over 24 of 0.0275 -> 0.0287; continuous 25-frame error
3.717 -> 3.444 and share 0.0275 -> 0.0245. All fourteen primary light grids match exactly and all views
have zero missing/extra placements. Eighteen unaffected frame hashes plus Raklion's two are unchanged.
Near-hero after-flag counts remain Noria 15, Elbeland 0, Raklion 0 and Karutan 6. Final native frames were
visually inspected; missing live PNGs, capture history and unsynchronised phases remain explicit limits.
Reports and artifact paths are in the [updated handoff](../handoffs/RENDER-WORLDS-A.md).

## 6. RENDER-WORLDS-D, 2026-10-27

### Tour and ranking

The initial baseline was main `952868f`. After #181 merged, both the main baseline `5f6b0cf` and D's
combined branch were rebuilt in D's worktree and the full tour repeated. This includes B #180, terrain #175
and C #181; no builds ran in the main checkout.
`scripts/fidelity_tour.py run` rendered all fourteen captured views of thirteen maps at their arrival cameras,
25 logic steps, GL, 1722 x 1048. It compared the retained 2026-10-22 OBJECT/global/light snapshots.
Only Dungeon, Icarus and Kanturu have surviving live PNGs, under `renders/readme-sources/`.
No new live capture was taken. A blank image score for the other eleven views means unavailable.

Ranked by supported visible scope, rather than treating unlike measurements as one score:

1. **Icarus sky/clouds/dragons and Kanturu/Karutan flames/after-character flags.** The retained image errors
   are Icarus 62.030, Kanturu 3.717 and Dungeon 2.019 at 25 steps. The Icarus and flame/after-character work
   is now C2's remaining Icarus lane and A's flame/after-character lane; D leaves both intact. After-character field counts are Noria 16,
   Kanturu 3, Elbeland 19, Raklion 10 and Karutan 6.
2. **Missing Noria warp placement and rejected nested warp effects.** One Noria object of type 424 was absent;
   Devias and Raklion each rejected three startup effect calls. These have direct placement/lifecycle code
   and model evidence, so D fixes both. The portal cameras confirm the native effects draw.
3. **Aida frame-light outliers and remaining frame light.** Aida has the largest near-hero grid error, 0.65117,
   concentrated in 21 of 600 cells above 0.05; its worst cell differs by 88.12099. Its object light calls are
   already reconstructed. The snapshots lack the transient effect/source state needed to attribute this
   outlier to an additional emitter or capture timing. D does not fit arbitrary brightness to this sample.
   Dungeon follows at 0.04404; other maps are in the table below. Primary light is exact everywhere.
4. **Tarkan/Raklion haze and timing-dependent fields.** Eleven arrival views lack live PNGs, so the old image
   ranking remains historical evidence only. Lost Tower's 25 BlendMesh differences and Atlans's 22 BlendMesh
   differences include objects the original snapshot had not moved. Atlans also has 35 pulse differences;
   Lorencia, Devias, Tarkan, Aida and Raklion have the remaining light, pulse, speed or action differences
   listed in the local detailed scores. Existing instruction comparisons take precedence over forcing a
   captured time-dependent field. No new unsupported move branch was established by this tour.
5. **Raklion active event timer and Elbeland boids.** The object/light capture format contains no handler timer
   state, so the tour cannot assign an active timer image score. Static reading: Raklion's default move calls
   inherited `0x00ea17c0`; `+0x23` enables its timer, `+0x20` selects event behavior, and `0x00ea186c` emits the
   event effects/quake. That active lifecycle remains unimplemented, below the reproducible placement/effect
   defects for this slice. After C #181 merged, Elbeland was reassessed. This arrival view has zero native boids, a safe-zone hero
   and no live boid-pool snapshot or live PNG. The tour therefore supplies no measured boid deficit. Its
   now-unblocked movers `0x00ca33c3` and `0x00ca3ce1`, model registration and draw path remain a lower-ranked
   follow-up that can reuse C's shared flight/render loop. No Elbeland movement equivalence is claimed.

### Verified reconstruction and host integration

Production C lives in `reconstructed/objects/world_warp.c` and `noria.c`. The shared effect factory/mover
only dispatches the warp cases. Model mappings are static readings of AccessModels
`0x0183943f`, `0x018397d1` and `0x0183f529`: types `0x1a8/0x1ab`, `0x1a9/0x1ac`, `0x1aa/0x1ad`
use Npc/warp01, warp02, warp03. Only worlds 2, 3, 57 and 58 load these native effect models.

| Family | Original instructions | Compared |
|---|---|---|
| Warp create | Full CreateEffect `0x013c0f19`, branches `0x013c38ef/0x013c391b` | 600 records, all six kinds and subtypes 0/1/default; caller-light clear after copy, lifetime, mesh, RNG, owner/info fields, ordered calls |
| Warp move | Full MoveEffect `0x0142fd09`, branch `0x01435834` | 600 records; clock pulses, rotation, owner/height, model/animation, motion, expiry, ordered calls and RNG |
| Warp render selection | `0x015182c6` through the type switch to `0x01518d73`; TestFrustrum `0x016ccc14` executes | 600 records; five 3D planes, exact radius boundary, live/visible and alpha/mesh gates, RenderObject arguments |
| Noria placement | `0x01839870..0x01839952` | 600 repeated fixed constructor comparisons, including position, angle and record tail |

All **2,400 comparisons equal; zero mismatches, zero stopped cases; 8/8 compiled planted mistakes detected**.
The placement cases repeat one fixed record, not 600 distinct assets. The common constructor is stubbed as
zero initialization; engine allocation, animation playback, terrain height and drawing are recording stubs.
The trigonometric wrappers use the existing host-libm substitution. RenderObject's mesh implementation is
existing native code, not re-proved by the render-selection family. Pins:

- Text SHA-256 `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`.
- Second-section SHA-256 `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`.

The mutable light argument is explicit at the reconstructed factory. Native hosts supply a local copy;
these map-created source records already start with zero light. Runtime mutation of arbitrary caller-owned
nonzero light is not claimed. The Noria placement reuses B's exact type/position deduplication and named-model
loading. Noria's five creation calls now join the existing deferred startup queue. The two lines added in
`native/world/parts/particles.c` pass the current render frustum; no input flow is changed.

The first integration probe exposed a wrong 2D culling assumption. It was replaced with the original five-plane
3D test and added to the executed comparison. Four synthetic world sessions now create/live/draw respectively
3/5/3/6 effects with no rejected kinds, and repeat runs have identical stdout and image hashes.
Native GL portal views were inspected for Devias, Noria and Raklion. The local world-58 installed view has no
placement input, so its 6-effect integration is synthetic evidence only.

### Scoreboard before and after

| Capture | Missing before / after | Extra before / after | Static field differences before / after | Frame-light mean near hero before / after |
|---|---:|---:|---:|---:|
| 00b-lorencia | 0 / 0 | 0 / 0 | 17 / 17 | 0.00713 / 0.00713 |
| 01-dungeon | 0 / 0 | 0 / 0 | 0 / 0 | 0.04404 / 0.04404 |
| 02-devias | 0 / 0 | 0 / 0 | 0 / 0 | 0.0 / 0.0 |
| 02b-devias-town | 0 / 0 | 0 / 0 | 4 / 4 | 0.00068 / 0.00068 |
| 03-noria | 1 / 0 | 0 / 0 | 23 / 23 | 0.02568 / 0.02568 |
| 04-losttower | 0 / 0 | 0 / 0 | 25 / 25 | 0.02683 / 0.02683 |
| 07-atlans | 0 / 0 | 0 / 0 | 57 / 57 | 0.01404 / 0.01404 |
| 08-tarkan | 0 / 0 | 0 / 0 | 3 / 3 | 0.0 / 0.0 |
| 10-icarus | 0 / 0 | 0 / 0 | 0 / 0 | 0.0 / 0.0 |
| 33-aida | 0 / 0 | 0 / 0 | 5 / 5 | 0.65117 / 0.65117 |
| 37-kanturu | 0 / 0 | 0 / 0 | 3 / 3 | 0.01144 / 0.01144 |
| 51-elbeland | 0 / 0 | 0 / 0 | 19 / 19 | 0.02078 / 0.02078 |
| 57-raklion | 0 / 0 | 0 / 0 | 16 / 16 | 0.02574 / 0.02574 |
| 80-karutan | 0 / 0 | 0 / 0 | 6 / 6 | 0.01339 / 0.01339 |

All primary-grid mean errors remain 0 over 65,536 cells per view. Every frame-grid score is unchanged.
Noria missing objects falls 1 to 0; all fourteen captures now have zero missing and zero extra objects.
The thirteen other final PNG SHA-256 values are unchanged, including all ten views outside the changed worlds.
Noria's arrival camera is away from the new portal; its changed frame reflects the new particle RNG consumption,
not a measured live-image improvement. Devias/Raklion's arrival frames also remain unchanged, while separate
portal-camera runs draw 3/5/3 native effect models. Do not substitute those views for live comparisons.
The three available live-image mean errors remain 2.019 / 62.030 / 3.717 for Dungeon / Icarus / Kanturu.

The existing create/move effect families also pass 1,200 comparisons, zero mismatches. The new validator passes
through `scripts/run_validators.py`, with its manifest counts and mutants checked. Synthetic placement/dedup
checks now include Noria. The combined-tree local Mac gate through main #185 passed 1,395 tests across 38 suites with 166 explicit skips, both fixture
scenarios and viewer/readers builds. The B handler regression retains 4,000 equal comparisons and 10/10
compiled mutants; the existing object validator passes 2,980 comparisons and 19/19 mutants.
The post-#183/#184/#185 tour retains the same thirteen unchanged image hashes and every light score.
Counts and artifact paths are also recorded in the milestone handoff.

### Reproduction and remaining work

Reports/manifests/logs: `~/Documents/MTM/mu-mac-tools/native/scratch/render-worlds-d/`.
GL frames and complete scoreboards: `~/Documents/MTM/mu-mac-tools/native/renders/render-worlds-d/`.
Both are local only. Run `scripts/validate_worlds_d.py --cases 600 --mutations --output <local-report>`
with the repo Python, or its manifest row with private integration enabled.

Next work: A-owned visual paths and C2-owned remaining Icarus paths; unblocked Elbeland mover/model draw; the inherited Raklion event
lifecycle, including the event-state and timer inputs; attribute Aida's transient frame light from existing
source/effect code or a separately authorized future capture; fresh locked live images of the changed worlds.
No live game, launcher, network, service, protection module or running-client memory was touched.



## 7. RENDER-WORLDS-C2: persistent Icarus cover and emitter ribbons

**Verified.** The persistent grey cover comes from RenderObjectVisual's world-10 branch,
`0x017fba5e..0x017fbf34`, rather than the rare two-step cloud model. Types 0..2 create 20 `clouds`
`0x7f89` particles each; types 3..5 create 10 each, subtype = object type, light `(0.1, 0.1, 0.1)`,
owner = source OBJECT. Creation only runs while HiddenMesh is not -2, then sets it to -2. The native visual
dispatcher previously excluded world 10. Its imported hidden-type sidecar also set -2 before the first draw,
which would suppress this producer even after adding the handler. Native startup now leaves these six types
for their verified visual handler to hide.

`reconstructed/particles/icarus_clouds.inc` implements their creation and movement. The initial lifetime is 30;
while the source's visible byte is exactly 1, movement resets it to 50 before the common decrement. Once the
source stays invisible until lifetime 1, the particle dies and resets the source HiddenMesh to 0, allowing
re-entry to create its cover again. Size is `(rand % 20 + 180) * 0.01`, independent of requested size; vertical
motion uses `sin((WorldTime + gravity) / 5000) * 20`. Subtypes 1/4 and 2/5 turn in opposite directions in the
mover; subtype 0 uses the render ordinal's parity, and subtype 3 turns in RenderParticles. The renderer now
receives WorldTime and the list ordinal. These kinds use their supplied light directly, without the alpha
multiplication of the older login-mist subtype 20. The existing additive RGB texture path and sprite-pass order
remain in use; no opacity, spawn-rate or lifetime tuning was introduced to fit the still.

**Verified.** `0x472/1` creation, movement and rendering now use the shared joint pool: target-relative animated
head, 30 tails, `JointSpirit01`, lifetime 999999, light `(0.2, 0.2, 0.2)` at creation and the client's per-segment
geometry/fade. Native boid owner handles are distinct from map-object, actor, helper and hero handles, so the
joint follows the boid and terminates when it dies. The native Icarus ambient clock previously used elapsed
milliseconds. The writer `0x01851f82..0x01851f8d` increments `0x0bdc5eb0` once per 40 ms logic step; the host
now supplies the logic ordinal, with zero as the fresh-world phase. The captured session's starting counter is
unknown. Other worlds' host clocks are unchanged.

`scripts/validate_icarus_c2.py`, registered in `scripts/validators.toml`, freezes the production C and compares
seven families at 1,200 cases each: cover producer, cloud create/move/render and emitter joint create/move/render.
**8,400 equal, zero mismatches/stops, all 8 compiled planted mistakes caught.** It covers all six cloud subtypes,
hidden guards, source visibility 0/1/2, source reset, positive/negative WorldTime, both render ordinals, live/dead/
absent joint owners, and signed/wrapped clocks and pool indices. Engine services are recording stubs. The joint's
character resolver answers absent, and the non-Icarus event-world predicate answers false for world 10. Scalar
trig uses the existing validator's host-libm boundary. Native integration tests cover sidecar initialization,
80 visible ticks without duplication, expiry/re-entry, real boid-to-joint creation, owner death and the separate
clock. Exact commands, additional checks and limits are in [the handoff](../handoffs/RENDER-WORLDS-C2.md).

### Image diagnosis

All scores below use the surviving full-resolution README-source PNG, 1722 by 1048 client area, the tour's
unchanged HUD/hero masks and original mean absolute difference. Lower is better. No live client was used.

| Logic steps | Before #181 | #181 | C2 |
|---|---:|---:|---:|
| 25 | 61.760 | 62.030 | 26.897 |
| 400 | 54.673 | 60.935 | 27.663 |

The #181 regression is localised by one fixed mask made from its before/after frame difference, threshold >1
in any RGB channel. At 25 steps this footprint covers 11,280 of 1,178,576 scored pixels, 0.957%; its error rises
29.802 to 58.026, accounting for the whole +0.270 regression. The other 1,167,296 pixels score 62.069 on both
sides. At 400 steps the footprint covers 552,285 pixels, 46.860%; its error rises 59.271 to 72.617. Outside it,
error changes only 50.617 to 50.633. The broad late-frame change agrees with the sky helper's added RNG calls
changing where the existing puff system emits; dragons and ribbons are also phase dependent. This is an image
measurement and source-based inference about phase, not a replay of the captured random stream.

C2 draw-only ablations preserve all simulation and RNG calls. They isolate the missing cover from moving
ribbons and creatures; masks are the exact changed RGB footprints, intersected with the existing HUD masks.
They supplement the whole-scene score. Overlapping layer contributions must not be added together.

| Omitted draw layer | 25-step error | 400-step error |
|---|---:|---:|
| Persistent cover | 61.798 | 60.919 |
| Emitter ribbons | 26.674 | 27.664 |
| Dragons | 26.557 | 27.597 |
| Rising puff particles | 26.897 | 26.801 |
| Blue swirls | 26.897 | 27.788 |

The cover footprint spans 1,138,288 / 1,136,661 scored pixels at these frames; it accounts for most of the missing
brightness. The added moving elements can improve or worsen a single-frame score: at 400 steps omitting puffs
improves it by 0.862, whereas omitting swirls worsens it by 0.125. This does not justify removing either verified
behavior. Across 307 consecutive full-resolution native frames, steps 1..307, error ranges 26.481..32.609 with
mean 28.691. The separate 400-step endpoint is 27.663. No live time series survives, so this measures sensitivity
to native phase against one still, not temporal equivalence. The older full effect pool snapshots identify rising
puffs but lack this separate particle list and the boid/joint/sprite pools.

Camera, primary light and static-object comparisons stay in the tour. All thirteen other capture PNG hashes are
unchanged against #181 before the parallel D merge. After D #188, all thirteen match its new main baseline,
including its Noria change, and Icarus retains the same two scores. `fidelity_tour.py` now accepts optional `element_masks` per map and reports their areas
and errors without replacing the whole-scene metric; `icarus_fidelity.py` produces the phase and ablation report.
No moving-region exclusion is used to claim the target passed. Local inputs, frame reports, masks, selected
renders and the full 307-row score series remain under the C2 scratch/render directories. Renders and captures
are not committed. Remaining limits are exact captured RNG/clock/pool phase, the hero/equipment mask, and the
unported world-10 type-10 bone flare. Sibling worlds and after-character rendering remain with lanes A/D.
