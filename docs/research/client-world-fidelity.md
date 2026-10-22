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

1. **Icarus's soft cloud layer** (section 3.4): the rising puffs are ported; the grey cloud layer, `0x018016b0`
   (cloud model, lightning), the `cloudLight` sprites and the blue swirls (`0x0180249e`'s joints `0x7f7c` subtype 6)
   are not. The Icarus dragons (boids `0x7c4`, `0x00ca2154`) remain unported (NATIVE-ENV-001).
2. **Tarkan and Raklion haze**: the client's terrain is up to ~1.35× brighter, the darker light-map areas most, so
   the contrast is compressed; the pattern stays with the ground when the hero moves (second session, two positions
   per map). The primary and frame light grids equal the native ones, the light-offset grid `0x0bc35430` is all zero,
   FogEnable is off and the fog globals are the BeginOpengl defaults (live reads), and the textures are the same. Both
   folders hold a `Fog.OZJ` that no string in the captured code names. The source (a GL state, a second pass, an
   overlay) was not found; a GL call trace of the Wine-track `mugl` layer in these two worlds is the next step.
3. The brazier and torch flames themselves in Kanturu and Karutan (their lights are ported; the flames come from
   RenderObjectVisual `0x017f9758`'s world cases, not ported), and the visual-pass flags (`+0xa` drawn after the
   characters in Noria, Elbeland, Raklion, Karutan).
4. Move cases of Devias (doors, flicker), Tarkan, Elbeland (`0x00e30b86`) and Raklion (handler slot `0x00e94619`);
   objects that world code creates (Devias 422–424, Raklion); Raklion's snow.
