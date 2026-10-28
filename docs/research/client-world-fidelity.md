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

1. **Icarus's persistent soft grey coverage**: the named sky, cloudLight, blue-swirl and dragon instruction paths
   are ported in RENDER-WORLDS-C (section 3.5), but the screenshot's grey coverage remains unexplained. The ten
   accompanying boid emitters' `0x472/1` joint requests are counted by the native host, not rendered.
2. **Tarkan and Raklion haze**: the client's terrain is up to ~1.35× brighter, the darker light-map areas most, so
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
before the environment. Raklion's opaque meshes remain in the first pass and its glow meshes in the second.
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
