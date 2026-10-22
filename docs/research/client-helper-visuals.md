# Helper visuals: the mounts' passes and effects, the helpers' particle kinds (NATIVE-HELPERS-002)

NATIVE-HELPERS-001 ([client-helpers.md](client-helpers.md)) made the helpers move and drew their bodies. This
milestone adds what makes them look like the client: the particle kinds they create, the mounts' model passes and
class visuals, and a live comparison. The pets of the pet process are in [client-pets.md](client-pets.md), the Dark
Raven in [client-dark-spirit.md](client-dark-spirit.md).

Labels:

- **verified**: authored C equals the client's instructions under Unicorn on every compared case;
- **static**: a reading of the decoded instructions that was not executed;
- **live**: observed in the running client (window-only captures, kept local);
- **viewer choice**: native behaviour that is not a client reading.

## Identity

| Input | SHA-256 |
|---|---|
| `main.exe` (target) | `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a` |
| Restored text at `0x00401000` (capture09) | `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` |
| Second section at `0x01a7c000` (run10) | `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f` |

| Routine (names are ours) | Range | SHA-256 (first 16) |
|---|---|---|
| glow wave | `0x0185bdc4..0x0185be96` | `3f4d283cf28aa2dd` |
| random value in steps / direction / flat direction | `0x011ff622`, `0x00d01fc6`, `0x00d0221e` | `cf356bb264978793` / `af0da7183f94ec01` / `de3f5db3e293164a` |
| Shining Tail visuals (vtable +0x1c) | `0x01057fb0..0x01059fdc` | `ac1ce5bfd39b7e6c` |
| Shining Tail claw steps | `0x0105a0bb..0x0105a3b2` | `c148251e895c0286` |
| Dark Horse functor | `0x00a2eaa2` | `c5f1c929839b0e37` |
| Fenrir functors (four copies) | `0x00a335e9`, `0x00a34652`, `0x00a356bb`, `0x00a36724` | `62320e5f…`, `2f2ec415…`, `57146228…`, `775a029e…` |

`scripts/validate_mount_visuals.py` records the 24 functor bodies and these routines in its report.

## Short answers

- **The helpers' particle kinds** (verified). Spark02 `0x7f25` subtype 1 (the angel's sparkles: scale (r%4+4)·0.1,
  LifeTime r%8+8, then subtype 0's fall and bounce), smoke02 `0x7f5b` 0 (`Effect\smoke02.tga`, the mounts' dust outside
  world 2: LifeTime 32, a push of 3 along the creation angle, light LifeTime/32, scale +0.08, velocity ×0.9, and it
  sits on the terrain by half its height through the bitmap getter `0x00ebbec8`; drawn with the `0x0184abd5` blend),
  drop01 `0x7fcd` 0 (`Object8\drop01.jpg`, the Dark Horse's dust in Atlans: a 3×3 sheet cell `frame % 9`, rising
  jitter) and Spark03 `0x7f26` 0xf (Fenrir's sparks: one in three lives 35 steps and falls, dims by 1/1.05 and dies
  with its alpha). They join NATIVE-PARTICLE-001's module.
- **The render registry** (verified). RenderObject's draw `0x017edf43` hands an object type to a functor of the
  std::map `0x01d1e010` when one is registered (1,254 `0x00a16273(type, functor)` calls at start-up; the validator
  reads the 1,171 with two plain pushes, all 24 mount models among them). Every mount model has one: Uniria `0x00a2f501` returns 0 (the default body), Dinorant `0x00a318b8` draws the
  body; the others draw the body or its meshes and then glow passes through RenderMeshDefault `0x00966e4a` (flags
  0x42 additive texture, 0x44 additive chrome, 0x46 both) with the model colour +0x54 set per pass and texture
  overrides (`Effect\black_gold_crom02_mono.jpg`, `Skill\shiningtails_render.jpg`, `Item\texture\ursh_overlay.jpg`
  ... 34 bitmaps). The glow pulses with the wave `0x0185bdc4(period, phase)` = (±cos of the world time folded into
  one period + 1)/2. The mount's body pass (vtable +0x14) is only RenderObject's setup: the draw is the after-pass.
- **Per model**: the Dark Horse adds a golden chrome pass (colour (1, 0.8, 0.3)) on mesh 12 (meshes 13..15 do not
  exist) and a second blob shadow of mesh 8; subtype 1 draws it dark (0.2). Fenrir draws its two meshes (the gold
  one with a chrome pass), six flares at bones 11 and 13 (eyes and mane), two body-lightning effects `0x4ac` every
  frame in its colour (red, blue, gold, or yellow for black), the paws' effect `0x4ad` at fixed frames of its walk
  and run, and Spark03 0xf sparks at bone 14 while attacking. The later mounts pick their glow by the object
  subtype, which their model load (vtable +0x38) sets from the descriptor's state, the item level of the equipment
  packet (verified for states 0, 7 and 15; the ride-state transformations get −1).
- **Class visuals** (vtable +0x1c, after the after-pass in the render loop `0x0106bc2b`; the classic four share the
  empty `0x0103d8be`). Reconstructed for the Shining Tail and Ghost Horse (verified): about 25 glints and flares on its bones
  (pin_star, bostar3_R, Shiny03, flare01), the eye joints `0x7fd6` 0x43 / 0x44 once, mist and sparks of its tails
  (particles `0x7f5a` 0x7f, `0x831d` 6, `0x83b3` 6, `0x7f26` 0x2a, `0x8086` 0x13, effect `0x6f6`, from the random
  helpers `0x011ff622` / `0x00d01fc6` / `0x00d0221e`), and the paws' rune circles: object +0xa4 rises by 0.05 per
  frame while it stands (to 1) and falls while it walks or runs; above 0 four `Effect\lightmarks_mzin.jpg` and four
  flare decals are laid on the terrain under the paws (RenderTerrainAlphaBitmap `0x016cdd5f`, additive), and in a 100 ms
  window of every second while it stands four effects `0x8438`. Its class move adds two claw effects `0x6f3` at `leg_nailfront*`
  (frames 4..5) and `leg_rear*` (9..10) while the mount walks or runs.
- **The Dark Horse's white glow** is the client's look. It is the horse's breath: the move `0x0103f457` creates a
  smoke01 (`0x7f5a` 0) at "Bone03" + (50, −4, 0) on one step in three while it stands (verified in NATIVE-HELPERS-001;
  the bone is in the head chain). smoke01 0 is drawn additive with light LifeTime/8, which starts at 2 and saturates
  white, so the puffs at the nose are bright. The native rate matches (73 created in 200 steps, about 6 live; the
  client's code gives 1/3 per step and LifeTime 16). A live check was not possible: the account has no Dark Lord.
  (The Dark Raven fork's render of the demo Dark Lord shows the same puffs.)

## Validation

`scripts/validate_mount_visuals.py --cases 300` (Unicorn through `validate_helpers.Machine`; report
`evidence/native-helpers2/mount-visuals-01.json`):

| Section | Cases | Result |
|---|---|---|
| registry pairs (the 24 mount models → functor) | 1,171 pairs read | all 24 match |
| functors (24 models × 300: type, subtype, action, frame, world, time, model colour) | 7,200, 66,129 calls | 0 mismatches |
| Shining Tail visuals (fade, joint flag, rand count) | 300, 20,390 calls | 0 mismatches |
| Shining Tail claw steps | 300, 820 calls | 0 mismatches |
| Ghost Horse visuals / claw steps | 300 / 300, 23,442 / 1,136 calls | 0 mismatches |
| negative controls (time + 40 / v + 0.25 on the functors; time + 100 on the visuals) | 40 / 40 / 30 | 40 / 40 / 30 detected |

`scripts/validate_particles.py --cases 3000 --heavy-cases 300` (NATIVE-PARTICLE-001's validator with the new kinds;
report `evidence/native-helpers2/particles-01.json`): create, move and render 3,000 / 3,000 each,
every other family unchanged; three new negative controls (the angel's sparkle living like subtype 0, smoke02
seated without half its height, drop01 drawn with the whole sheet) disagree.

`scripts/validate_helpers.py`: the mount_class section now compares the object subtype after the model load
(53 class/state entries with states 0, 7, 15); the rest is NATIVE-HELPERS-001's run.

Static only: the draw `0x017edf43`'s path to the registry (the buff path `0x017f746f`, the custom render
`0x017f76ec`, the tint `0x017f9375`, which answer nothing for the mounts in the native worlds).

Portable: `reconstructed/helpers/test_helpers.py` (functor and wave examples), `native/tests/test_native_helpers.py`
(Fenrir's passes, flares and effects in mu-walk).

## Completed particle, joint and effect paths

The same pinned text/data above is the reference. `evidence/native-helpers2/particles-final.json` compares
3,800 cases per create/move/render family over all 36 supported particle kinds, with zero mismatches. Added here:
Steam_01 `0x831d/6`, Smoke_line `0x83b3/6`, firehik_mono01 `0x8086/0x13` and `/0x18`, Spark03
`0x7f26/0x2a`, smoke01 `0x7f5a/0x7f`, and Ghost Horse breath `0x7f5a/0x75`. CreateParticle
`0x015ae7b0`, MoveParticles' record body `0x01616f7c..0x0168ee7d` and RenderParticles
`0x015912e9..0x015ae351` execute with strict declared memory, recorded calls and rand counts. The breath's
AngleToVector `0x00d015d5` executes too. New planted mistakes (wrong initial lifetime, missing glint alpha,
lost fire colour, missing breath direction) disagree in 420 / 270 / 69 / 69 cases.

`joints-final.json`: 1,800 cases per create/move/render family over 18 kinds, zero mismatches. The Dark Horse
ring `0x7f78/0` (`0x015496cb`, `0x01578049`) copies the mount's light, which ObjectInit leaves zero; the
native ring is therefore dark, matching those instructions. Subtype 1 stops the orbit and tail updates.
The eye trails `0x7fd6/0x43..0x44` (`0x0153d070`, `0x0153d168`; moves `0x0155a798`, `0x0155a85a`)
copy SetEye's two positions and the supplied colour, refresh their lifetime while the owner is live, and draw
JointLaser01. Swapped eyes and a missing lifetime refresh fail in 200 / 128 cases; the ring sine mistake fails
in 65. Full joint GL calls are compared, including vertices and texture coordinates.

`skill-final.json`: 1,500 cases each for effect create/move/decal selection, zero mismatches. The flying step
`0x8012/1`, Fenrir body lightning `0x4ac/0`, paw marks `0x4ad/1..5`, claws `0x6f3/0..2`, tail emitter
`0x6f6/0` and paw rune `0x8438/0` are reconstructed. Claws/runes/paw marks use the actual RenderEffects
blocks `0x01527c4e`, `0x0152d6a6`, `0x0151a5c7`; shock rings use `0x01514ded`. Render wrappers and the
terrain renderer are recording stubs: this family verifies decal arguments, not the terrain's emitted vertices
(the ordinary terrain renderer has its own validator). The tail emitter emits particles/sprites and has no model
pass. Missing claw shrink, rune growth, wrong tail particle and missing decal alpha fail in 84 / 30 / 46 / 483
cases; shock and lightning mistakes fail in 47 / 21. Reports retain routine ranges and complete hashes.

The alternate shock-ring path through `0x00deec1f` is selected in worlds `0x18..0x1d` and `0x24`.
Static inspection of `0x009f90cd..0x009f90dd` shows signed integer heights from a separate grid plus 400,
with 50-unit cells. The native loader lacks that grid, so native drawing explicitly skips this variant. An earlier
zero-height approximation was removed after review; its selector arguments alone did not validate geometry.

Ghost Horse's class visual `0x01048192` adds 33 bone flares, standing paw decals, sparks, level-dependent eyes
and breath; its step `0x010497b9` adds four named claw effects at frames 0..1. The normal flareBlue loader
`0x01822871` specifies GL_CLAMP; using repeat made a large tiled blue patch and was corrected.

## Native

- The mount's body pass poses; the after-pass runs the functor's call list through the scene draw (mesh passes with
  `mesh_plus_one`, the colour through `mu_draw_model_fields`, texture overrides as extra bitmaps of the model's
  `mu_textures`, appended after the specials), the second shadow over a mesh range (`mu_world_particles_shadow_range`),
  sprites, particles and effects to the particle module; then the class visuals, whose terrain decals go through
  `mu_terrain_decal` into the model's backend (fans as triangles, GL_CLAMP bitmaps).
- The class steps run in the move loop between the base move and the action map. The current mount is posed
  before every class step and named bone lookup; models are shared by mounts, so a previous owner's pose is unsafe.
- Rider offsets retain model-space bones; flying steps use scale plus object origin. Fenrir lightning carries the
  actual mount owner and resolves its bones. Bone indices are checked against the loaded skeleton's count.
  `native/tests/helper_fx_host.c` covers nonzero origins, two owners sharing a model, real flash ownership, the
  zero-light ring, eye colour/lifetime through native dispatch, and invalid Fenrir bone references (seven-bone synthetic skeleton, requests 53 and -1).
- `--helper ghost-horse | ice-dragon | pierce-lion | shining-tail | ur | leviathan | tauros | divine-horse` with
  `--helper-state LEVEL`; the Preview app's helper picker lists them with the pets and the raven.

Viewer choices: TransformPosition and TransformByObjectBone positions come from the native pose in world space;
object +0xa4 starts at 0 (the model load) and fades per drawn frame like the client; WorldTime advances 40 ms per step.

## Live comparison (2026-10-22)

Under the game lock, Nighty (MTM-1, Lorencia 138,135) rode its Shining Tail +10 (the item is "used" from the
inventory with a right click and summoned with Ctrl+Z in this client); memread showed the ride word `0x1853`, the
manager's map with one mount (vtable `0x1ab6e3c`, descriptor (1, `0x1853`, 10)) and its OBJECT (type `0x6f4`,
subtype 10, scale 1.2, +0xa4 1.0). Other players' pandas stood nearby. The native render at the same tile matches the
mount's shape, glow passes, the purple eye streak and the paws' rune circles; the live tails' blue sparkles were missing in that intermediate build. The completed native paths above now draw them. The panda pet matches in size, glow and placement. Captures and renders stay local
(`~/Documents/mu-mac-tools/native/renders/helpers2/live/`, `t-shiningtail3/`, `t-panda/`).

Fresh native GL renders: `~/Documents/mu-mac-tools/native/renders/helpers2/final-shining-tail/`,
`final-ghost-horse/`, `final-shining-tail-every-frame/`, `finish-fenrir-blue/` (local only). The final two mount
runs load all 44 effect bitmaps and report zero unsupported particles, effects and joints. They are native renders;
the historical live comparison above used the original game. No new original-game session was needed for finishing.

## Limits

- Ice Dragon, Pierce Lion, Ur, Leviathan, Tauros, Divine Horse and rare/transformed class visuals/moves remain
  unreconstructed; their registry functors are covered. Muun pets remain surveyed only (optional scope).
- Alternate-grid shock rings are selected but not drawn, as explained above.
- The buff path of the draw (`0x017f746f`) is not drawn.
