# Model lighting inputs (NATIVE-LIGHT-001)

NATIVE-LOGIN-001 ([login scene](client-login-scene.md)) found the native login scene's sky about 1.6× darker and the
ship hull about 1.4× brighter than a window screenshot of the client, with equal body lights. This milestone traces
the inputs of the client's per-vertex light, finds two native errors that affect every lit model, fixes them in the
native scenes and measures the result against live screenshots of the login scene and of Lorencia.

Labels:

* **verified**: the client's instructions ran in Unicorn and matched the native values on every compared case;
* **live**: read from memory of a client this project started (read-only, plain game memory), or measured on a
  window-only screenshot of it;
* **static**: read from decoded instructions, not executed.

Inputs are the pinned restored text (`2bd5f2e9…3724`) and second image section (`c985e2e6…672f`).

## 1. What the per-vertex colour depends on

The mesh draw `0x012b8d1d` (verified in [CLIENT-MESHDRAW-EXEC-001](client-meshdraw-exec.md)) emits, per corner,
`colour = light[normal] × model +0x54` (the body light), unless the model's lighting byte `+0x50` is clear or the mesh
equals the model's `+0x94` byte (then the flat body light). `light[]` is written by the transform `0x012b5bde`
(verified in [client-skinning.md](client-skinning.md)):

```
L = (1.3, 0, 2) if [0x01cf1048] else ((0.5, -1, 1) if world == 30 else (0, -1.5, 0))
L1 = irotate(L, AngleMatrix(model +0x98))
light[n] = max(minimum, dot(rotate(normal[n], bone 3x3), L1) * scale + ambient)
```

The normal is rotated by its bone's 3×3 and **not renormalized**. So the inputs are: the light-override byte
`0x01cf1048`, the angle at model `+0x98`, the world, the bone matrices, and the transform's ambient, scale and minimum
arguments. Static readings for the writers:

* `0x01cf1048` has one reference in the restored text, the read at `0x012b5c05`. No instruction writes it.
* Model `+0x98` is written only by the constructor (`0x00cd881b`, zero), the destructor and the world-30 branch of the
  transform itself (`0x012b5ca2..0x012b5cd0`). The pose builder writes the object angle to `+0x84`, not `+0x98`.
* RenderObject's setup `0x017ec896` calls Animation with `!translate` (`0x017ed811`/`0x017ed880`) and
  Transform(bones, min, max, OBB, translate, 0, 0.4, `+0xe4`, `+0xe8`) (`0x017edc95`/`0x017edd08`, through the
  default-buffer wrapper `0x00966ea5`). Static objects are drawn with translate 0, so the pose builder `0x012b5064`
  multiplies the root bone's 3×3 by the body scale `+0x74` and sets its translation to the origin `+0x78`, and the
  transform runs without translate. These arguments are already in the compared render family
  ([client-objects-render.md](client-objects-render.md), the Animation and Transform events of `mu_obj_render`).
* RenderCharacter `0x01363260` draws a monster or NPC body with RenderObject(o, translate 1, …) (`0x01364163`; the
  translate byte `[ebp-0x3c]` is set to 1 at `0x013632fe`), and the in-world character light `CHARACTER +0x1b8` is
  RequestTerrainLight on the frame light (`0x016cb08d`, no 0.1 factor) plus the object light `+0xec`
  (`0x013675b4..0x01367683`).

## 2. Live read

The owner authorized live reads under `GAME-LOCK.md`. The lock was held 16:07:36–16:12:19 on 2026-10-18:
`mu-to-server.sh` to the server-select screen (scene 3, World95), two snapshots and two window-only screenshots; then
`mu-autologin.sh` (MuMatrix32, MTM-1, Nighty, who stood in Lorencia at 144,140), two snapshots and two screenshots; the
client was closed with `taskkill` (WM_CLOSE) and the launcher closed on its own. No character moved.

The new read-only tool `mac-play/diagnostics/lightread` (`make -C mac-play/diagnostics lightread`) copies the globals,
the model container `[0x01d1dbec]` (its `std::map<int, BMD *>` at `+4`, walked in order: 4,854 models), the live
CharactersClient entries (`[[0x01d1dbbc] + 8] + i × 0x3670`) and both terrain light grids. Findings (live):

| Input | Login (scene 3) | Lorencia (scene 6) |
|---|---|---|
| `0x01cf1048` light override | **1** | **1** |
| model `+0x98` | (0, 0, 0) for all 4,854 models | same |
| model `+0x94` | −1 for every model with meshes (0 only for 1,465 empty slots) | −1 for every model with meshes |
| model `+0xcb`, object `+0x3b` | 0 | 0 |
| object `+0xe4`/`+0xe8` | 0.8/0.2 for all 47 | 0.8/0.2 (objects and characters) |
| character light `+0x1b8` | | frame light + 0.2 for 11 other characters and the NPC; (1, 1, 1) for the hero |

The Linux run capture of the data section (`x86-linux-capture-04/main-01ced000.bin`) also holds 1 at `0x01cf1048`.
It is initialised data that the code only reads. So every lit model draw in the game uses the light vector
(1.3, 0, 2), not (0, −1.5, 0).

The NPC's model colour equals its `+0x1b8` (frame light + 0.2), as RenderObject's body light with `+5/+6/+7 = 1`
gives. The hero's `(1, 1, 1)` comes from a branch of RenderCharacter that was not traced. A model's `+0x50` in a
snapshot is only the last write: RenderObject sets it from object `+5` before Animation. Models that were not drawn
since load read 0.

## 3. The two native errors

1. **Light vector.** The native model parameters used override 0, so lit models were shaded with (0, −1.5, 0). That
   lights faces that point to −y and leaves upward faces at the ambient term.
2. **Normal scale of static objects.** The native objects runtime posed every static object without translate, and
   the transform then applied scale and origin. Vertex positions are the same, but the normals stayed at unit length.
   In the client they carry the body scale, so the Lambert term grows with the scale. The login sky (scale 14.84)
   saturates at the body light. The far ship (0.23) is dark. Lorencia's houses and walls, at scales around 1, change
   mostly through the light vector.

Ablation on the login scene (native/live mean colour, `renders/light/ablation/`):

| Region | Before | Light vector only | Normal scale only | Both |
|---|---:|---:|---:|---:|
| sky top right | 0.62 | 0.55 | 1.00 | 1.00 |
| island beam | 0.71 | 0.66 | 1.00 | 1.00 |
| right ship sails | 1.53 | 1.21 | 1.23 | 1.01 |
| right ship hull | 1.48 | 1.04 | 1.34 | 0.99 |
| left far ship | 0.99 | 0.72 | 1.02 | 1.01 |
| foreground deck | 0.33 | 0.98 | 0.33 | 0.97 |

## 4. Native changes

* `mu_model_scene_params` (`native/core/mu_model.*`): default parameters plus `MU_CLIENT_HIGH_LIGHT` = 1. The game
  scenes use it: objects, the world hero and characters (part models take the Player model's override), character
  select, monsters/NPCs, ambient creatures, combat models. `mu_model_default_params` keeps 0. The viewer, the CLI
  model tools and the client-verified mesh-draw digests used that input.
* Objects (`mu_objects_runtime.c` `pose_object`): the pose takes Animation's translate and Transform's arguments from
  `mu_obj_render`'s compared call log. The after-character setup uses the static-object values. The lantern bone
  positions now read `matrix × local`. The NATIVE-OBJECTS-001 placement path (`mu_objects_place`) uses the same
  arguments.
* Monsters/NPCs (`mu_world_actors.c`): colour = `mu_obj_terrain_light` on the frame light + 0.2, light
  0.4/0.8/0.2, pose without translate (RenderObject translate 1).
* Ambient creatures (`mu_env.c`): RenderObject's translate per call (fish `a1 = 0` with the scale in the bones,
  boids `a1 = 1` without). Their body light stays the viewer choice of NATIVE-ENV-001.
* Reports: `mu-terrain render … --object-steps N --light-report 1` prints one line per drawn object (pose and light
  inputs, frame, model file, per-normal lights). `mu-world`/`mu-walk` actor rows add `light` and `light_override`.

## 5. Verified: native object light = the client's transform under the live state

`scripts/validate_model_light.py` takes every object the native runtime draws, then runs the actual client bone-track
loop, pose builder `0x012b5064` and transform `0x012b5bde` in Unicorn on the installed model file. The chain is the
one of `validate_skinning.py`, with the object's action, frames, angle, scale and origin, and RenderObject's arguments
from the native report. The light-override byte, the world and the model's `+0x98` come from the live snapshot. The
check requires the client's per-normal light to equal the native value bit for bit. A negative control repeats each
case with the old inputs (override 0, scale applied by the transform).

| World (snapshot) | Objects | Normals compared | Equal | Lit normals | Old inputs differ |
|---|---:|---:|---:|---:|---:|
| Login, World95 (`login-a`) | 19 | 1,433 | 1,433 | 1,170 | 1,170 |
| Lorencia (`world-a`) | 2,780 | 170,469 | 170,469 | 134,035 | 134,035 |

One validator bug was found and fixed during this work. `validate_pose_builder.make_setup` declares its synthetic
prior matrices over the angle and head slots, so the earlier installed chains ran with arbitrary root angles. That
was harmless there, because client and authored code saw the same bytes. Here the validator declares the angles
again.

## 6. Comparison with live screenshots

**Login** (window-only, 1722×1048 client area, local script `~/Documents/mu-mac-tools/native/scratch/light/compare_login.py`; native headless software and
`mu-client` GL agree within 4% except the pulsing beam):

| Region | Before | After (soft) | After (`mu-client` GL) |
|---|---:|---:|---:|
| sky top right | 0.62 | 1.00 | 1.00 |
| sky right of logo | 0.62 | 1.00 | 1.00 |
| sea right / centre (terrain) | 1.00 / 1.04 | 1.00 / 1.04 | 1.00 / 1.04 |
| island beam | 0.71 | 1.00 | 0.90 (pulse phase) |
| right ship sails | 1.53 | 1.01 | 0.99 |
| right ship hull | 1.48 | 0.99 | 0.95 |
| left far ship | 0.99 | 1.01 | 1.00 |
| foreground deck | 0.33 | 0.97 | 0.99 |
| gold statue (after-pass glow) | 0.80 | 1.07 | 1.07 |

The flags of the right ship are lit red and gold as in the client, where they had been black.

**Lorencia 144,140** (Nighty's spot, same camera: eye, pitch, FOV and far plane equal the live globals; GL 1722×1048,
`~/Documents/mu-mac-tools/native/scratch/light/compare_world.py`, shift 0):

| Region | Before | After |
|---|---:|---:|
| pillar + plaque | 1.29 | 1.03 |
| fence + grass bed | 0.98 | 1.00 |
| fence rails | 1.11 | 1.02 |
| building column | 2.57 | 1.00 |
| roof right | 0.38 | 1.00 |
| wall top centre | 1.86 | 0.74 (live: a store player's fire wings next to it) |
| ground (terrain, control) | 1.02 | 1.02 |

The iron fences, which were silver-gold before, are dark like the client's. The live frame light near the hero
equals the native frame light within the flicker of the street lamps. A local run that replaced the native frame
light with the live grid gave the same region values.

**Character select** (live screenshot of NATIVE-CHARSEL-001): the purple trees go from 0.48–0.66 to 0.93–1.08 of the
live brightness. The native framing at 1722×1048 differs from the client's, so these are rough region values.

## 7. Side check: pale terrain at 1280×800

Not reproduced (as in NATIVE-LOGIN-001): Lorencia 147,137 in GL and software and Tormenta 135,10 at 1280×800 and
1600×1000 show the same terrain apart from scale, before and after this change (`renders/light/pale-check/`). One
candidate explanation: the old light vector left upward grass and plant meshes at the ambient term, so they looked
grey. That would explain "grey grass", but without the original command it remains a guess.

## Tests

* Portable: `native/tests/test_native_light.py`. A one-bone model with axis normals placed at scales 1, 0.5 and 3
  gives exactly `max(0.2, 0.4 + 0.8·scale·dot(n, (1.3, 0, 2)))` through `mu-terrain --light-report`. Demo-placed
  monsters and NPCs get the frame light + 0.2 with override 1.
* Private: `tests/test_model_light_private.py` runs `validate_model_light.py` with `MU_LIGHT_OBJECTS`,
  `MU_LIGHT_SNAPSHOT` and `MU_LIGHT_WORLD`. The existing native suites pass unchanged, including the private login,
  objects, world, character-select and mesh-draw execution checks.

Local renders (not committed), `~/Documents/mu-mac-tools/native/renders/light/`: `before/`, `after/` (login soft and
GL, comparisons), `ablation/`, `lorencia/` (before/after, live client area, live-grid runs), `charsel/`,
`monsters/` (Lorencia field and town, before/after), `pale-check/`, `live/` (the four window screenshots).
Snapshots: `~/Documents/mu-mac-tools/native/scratch/light/live/dumps/`.

## Limits and next steps

* The hero's `(1, 1, 1)` character light in the world was observed live, but its branch in RenderCharacter was not
  traced. The native hero keeps (1, 1, 1).
* The body light of ambient creatures (RenderObject's 0x017ec3d8 on the boid/fish objects) and their `+0xe4`/`+0xe8`
  are not read. NATIVE-ENV-001's colour and the default light arguments remain.
* HUD item models (RenderItem3D, NATIVE-GFX-003's `world_gfx_game.c`) were not checked.
* The client's GL driver state (texture environment, sRGB) was not captured. It was not needed: the remaining
  login-scene differences are within 5% except the animated after-pass glow.
