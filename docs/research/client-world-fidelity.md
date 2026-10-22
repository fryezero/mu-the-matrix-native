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

## 4. Gaps (ranked by visibility)

1. **Icarus clouds** (static reading). The cloud layer is not terrain: in Icarus MoveBoids spawns the boids of
   `0x00ca2154` (model `0x7c4`, NATIVE-ENV-001 left them unported), and RenderBoids `0x00c9fd8d` creates clouds
   particles (`Effect\clouds.jpg`, bitmap `0x7f89`) for them; the world-10 object routine `0x0180249e` gives the
   smoke-box types 0..5 a `cloudLight` sprite (`0x7f8a`) and two joints `0x7f7c` subtype 6 (the blue swirls) once in
   ten steps. None of these branches is reconstructed yet.
2. **Tarkan and Raklion haze**: the client's terrain is up to ~1.35× brighter, more toward the camera, although the
   primary and frame light grids are identical to the native ones and the textures are the same. Both folders hold a
   `Fog.OZJ` that no string in the captured code names. The source (a screen or world overlay, a per-world GL state)
   was not found.
3. Per-world object creation and move cases (BlendMesh, HiddenMesh, range, after-character draw, fires and their
   terrain lights) for worlds other than Lorencia and Tormenta Island.
4. Objects that world code creates (Devias 422–424, Raklion), the Kanturu/Karutan/Dungeon fires, Raklion's snow.
