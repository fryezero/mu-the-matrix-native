# RENDER-WORLDS-AFTER2: the class custom/after render slots, the slot bitmaps and the pre-move slot

Target: the executable SHA-256 `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`, text and second-image-data
captures pinned in `scripts/pins.py` (capture09/run10). Method: static disassembly of the pinned text, then compiled
authored C compared with the original instructions under the strict Unicorn machine (`scripts/validate_worlds_after2.py`).
Labels: **verified** = instruction-compared, **static** = read from the disassembly only, **inference** = reasoning.
Follows [RENDER-WORLDS-AFTER](client-worlds-after.md), which reconstructed the second pass and Abyss of Atlans' slots.

## 1. The custom render slot 0x38 and the after render slot 0x3c (verified)

The world manager calls the current class's slot 0x38 from the custom render `0x017f76ec` (`0x00ea2f07`) and slot
0x3c from the after chain (`0x00ea306c`), both only for object types 0..300 (static). Each slot is
`thiscall(handler, object, model, 0)`, starts with its own world test and draws with RenderBody `0x00966def` /
RenderMesh `0x00966e4a`. A true answer of slot 0x38 skips the first pass's RenderBody. Several slots also write
OBJECT +0xa (after-character) and +0x68 (hidden mesh): those are the after-character and hidden-mesh field differences the
per-world lanes left.

| World | Custom 0x38 | After 0x3c | World test | Notes |
|---|---|---|---|---|
| 91 Acheron | `0x00d6c427` | `0x00d6d3d7` | `0x00d6a614` (0x5b or 0x5c) | custom sets +0xa for 49 types; types 0x87e..0x888 go to `0x00d73cd7` (above 300: never reached from an object, not reconstructed); bitmaps 0x814f..0x8152, Chrome01 |
| 113 Nixies Lake | `0x00e347a8` | `0x00e3628c` | `0x00e34404` | Chrome09 0x8245 reflections, 0x8246/0x8247/0x8249/0x824a |
| 131 Scorched Canyon | `0x00e43842` | `0x00e43fab` | `0x00e45d40` | +0xa == 1 answers handled; per-mesh glow loop (texture sub record byte 1) |
| 132 Red Smoke Icarus | `0x00e00d4c` | `0x00e010b6` | `0x00e0558b` | +0xa answers handled; type 0x7c4 colour (unreachable) |
| 134 Gray Aida | `0x00d84d0e` | `0x00d868f7` | `0x00d8b139` | after draws RenderBody for every other selected type |
| 135 Old Kethotum | `0x00e3ae5e` | `0x00e3c739` | `0x00e3dd42` | colour save/set/restore around bitmap meshes 0x8341/0x8342 |
| 136 Burning Kethotum | `0x00d94eef` | `0x00d97384` | `0x00d99c0f` | the 135 cases plus a per-mesh loop (model +0x24/+0x28, sub record `0x00d99f0d`); 0x8343 |
| 137 Kanturu Underground | `0x00e092f4` | `0x00e0ab2a` | `0x00e0df03` | sets +0xa (20 types) and +0x68; after passes +0x68 as the texture of types 8, 0x5c..0x60 |
| 138 Ignis Volcano | `0x00e05f25` | `0x00e0709e` | `0x00e0895c` | +0xa answers handled; type 0xac drawn only for model frame 1 < f < 29 |
| 139 | `0x00d9c19a` (answers no) | `0x00d9c1b4` (nothing) | none | |
| 140 Bloody Tarkan | `0x00d9a2ed` | `0x00d9ac50` | `0x00d9bd83` | types 0x61/0x62 write OBJECT +0xb0 |
| 142 Twisted Karutan | `0x00e677a9` | `0x00e68c6a` | `0x00e6bd5a` | PlaySpeed 5.0 store (action table +0x30) for type 0x6b; colour restore around 0x8538 |

Read from the model: body colour +0x54 (written by some slots), StreamMesh byte +0x94 (written, sometimes left set),
action +0xa8 and frame +0xac (the Animation frame argument), mesh count +0x24 and mesh array +0x28. Helpers that run
as client code: the wave `0x0185bdc4`, CRT sin `0x009681bd`, fabs `0x01983660`; glPushMatrix/glPopMatrix wrappers
`0x012b7e53`/`0x012b7e65` change no value.

C: `reconstructed/objects/world_slots_visual.c` (`mu_class_custom`, `mu_class_after`, `mu_class_slots`).

## 2. Bitmaps on model meshes (verified registrations)

RenderMesh's last argument binds a registered bitmap (LoadBitmap `0x0185baac`) instead of the mesh's texture. A class
registers its own files in slot 0x24 (`LoadBitmap("Data\" + name, index, GL_LINEAR, wrap, 1, 0)`; e.g. Abyss 1-3
`0x00d5cede`/`0x00d5eb7e`/`0x00d602c2`: 0x82de `Object131\HSCrystalPlantB_R.jpg`, 0x82df `Object131\so_light01.jpg`,
GL_REPEAT), and the shared ones come from single startup sites (0x802c..0x802e `Npc\khs_kan2gate00{1,3,4}.jpg`
`0x0183d0b5..`; 0x8245 `Effect\Chrome09.jpg` `0x018226db`; 0x8246..0x824a `Object114\...` `0x018413c2..`; 0x814f..0x8152
`Object92\...` `0x01840faa..`). 0x8341/0x8342 are registered per world folder (135: Object136, 136: Object137).
`mu_world_slot_bitmap` holds the table and `mu_world_slot_bitmaps` the bitmaps each (world, type) names. Natively they
load as texture extras of the models that name them (the mounts' mechanism, `mu_textures_add_extras`); the draw takes
RenderMesh's index through the existing `texture` option. Chrome01 0x7f1f is already a model texture special.

## 3. The pre-move slot 0x74 (verified, synthetic state)

`0x00ea2c2b` calls slot 0x74, the registry tick, then slot 0x30. Bounded slots, all PlayBuffer `0x00a6ac96` only:
Imperial Guardian 69 `0x00dd2fae` (worlds 0x48..0x4a: 0x38f; 0x45..0x47: 0x38b + handler +0x14 for states 1..3);
70/71/72 `0x00dd886b`/`0x00dde51d`/`0x00de5441` call the world-69 handler's slot (`0x00dd8a3c(0x45)`); Loren Market 79
`0x00e6dd0a` (world test result discarded: no effect); Karutan 80/81 `0x00e189af` (types 0x3a/0x42: 0x3db with the
object); Swamp of Darkness 122 `0x00e5e1a4` (0x1a: rand()%50 → 0x4d4; 0x83/0x84 action 1 → 0x4d2; 0x85: rand()%150 →
0x4d2; 0xa1 → 0x4d3; 0xa8 outside tiles x 0xa3..0xca, y 0..0x27 → 0x4d5). Arca 92 `0x00d7ed5c` delegates through the
manager's run-time registry (`this+0x1c`) and is not bounded (not reconstructed). Worlds 69..72 and 80/81 have no
capture: validated with synthetic objects and handler state only. C: `mu_class_premove`.

## 4. Native wiring

- First pass: for the slot worlds, RenderObject's custom-render answer is the class slot 0x38 (types 0..300); its
  Body/Mesh calls are kept per object and returned by `mu_objects_first_meshes` (up to 32), each with the body colour
  at the call. Abyss 1-3's two custom meshes now take the same path (type 0x34's 0x82df mesh is drawn).
- Second pass: `mu_world_after_native` includes the slot worlds; `mu_objects_prepare_after` calls slot 0x3c.
- The StreamMesh byte persists per model type (the slots leave it set); a mesh drawn while it is the StreamMesh is
  drawn without the scroll and counted in `draw_unsupported` (no native StreamMesh consumer). A texture argument
  without a native bitmap is refused and counted.
- PlaySpeed store of 142 type 0x6b: applied to the type's action-0 PlaySpeed; other actions counted.
- Pre-move: called per moved object before slot 0x30's events are applied; sounds go to the object sound hook.
  The Imperial Guardian state is not modelled (0).

## 5. Checks

`scripts/validate_worlds_after2.py --cases 1000 --mutations`: **33 families, 32,216 cases equal, 0 mismatches, 0 stops**
(custom/after of 91, 113, 131, 132, 134, 135, 136, 137, 138, 139, 140, 142 at 1,000 each, the first 301 cases sweeping
types 0..300; pre-move 69, 70, 71, 72, 79, 80, 81, 122 at 1,000 each; bitmaps 216: every table row against the
LoadBitmap sites, and every slot texture checked against the use table inside the slot families); **33/33 compiled
mutants detected**. `reconstructed/objects/test_worlds_after2.py`: 7 portable tests + 1 private.

## 6. Fidelity (DATA-ACQ-002, base origin/main `61d5bb49` vs lane, same tour)

| Capture | Image mean \|Δ\| | First-pass draws | Field differences (whole map) |
|---|---|---|---|
| 91 Acheron | 6.905 → 6.856 | 86 → 55 | after-character 58 → 6 |
| 113 Nixies Lake | 7.001 → 6.910 | 232 → 232 | none before or after |
| 131 Scorched Canyon | 8.068 → 8.010 | 197 → 197 | none |
| 132 Red Smoke Icarus | 26.373 → 23.020 | 137 → 1 (272 after meshes) | none |
| 134 Gray Aida | 13.072 → 13.053 | 209 → 206 | none |
| 135 Old Kethotum | 2.388 → 1.936 | 86 → 80 | none |
| 136 Burning Kethotum | 8.661 → 6.532 | 59 → 53 | none |
| 137 Kanturu Underground | 5.790 → **6.362** | 212 → 204 | hidden mesh 24 → 0, after-character 20 → 0, blend light 11 → 11 |
| 138 Ignis Volcano | 4.139 → 3.825 | 166 → 153 | none |
| 140 Bloody Tarkan | 5.225 → 5.225 (PNG identical) | 83 → 79 | velocity 2 → 2 |
| 142 Twisted Karutan | 13.480 → 7.145 | 303 → 211 | range 5,047 → 3,868 (class 142's selector writes, now run), velocity 123 |

The other 22 captures (Bloody Tarkan included: its moved bodies are opaque): PNG, OBJECT and light dumps byte-identical (Abyss 1-3 included: no type 0x29/0x34 object is
drawn at their arrival tiles, so the bound bitmaps do not show there; Acheron's 0x814f meshes and Karutan's 0x8538
are drawn). Kanturu Underground is worse because the type-0xa crystals are now drawn as their meshes with blend light
from OBJECT +0xa8, which native leaves at 0.9 where the live object has 0.1 (the remaining blend-light difference, a
move-slot value, not these slots): the live crystals are pale and translucent, the old native ones opaque red, the
new ones pale but too bright (inference from the frames).

## 7. Limits and next

- Not reconstructed: the custom/after slots of 141, 143, 145 (about 2,300 instructions each), 133, 144 and the
  classes outside the second-pass list (57/58 beyond the A-world handlers, 62..64, 69..72, 79..82, 92..95, 100, 110,
  112, 114, 121..127), whose first pass still draws RenderBody; Acheron's `0x00d73cd7` (types 0x87e..0x888); Arca 92's
  pre-move delegation; the Imperial Guardian handler state.
- No native StreamMesh (+0x94) consumer; per-action PlaySpeed stores outside 135/136.
- The tour keeps the frame time 0.1 and renders 2 of 25 steps (as in AFTER).
