# A living native world: sound, culling, monsters, NPCs and effects (NATIVE-WORLD-002)

NATIVE-WORLD-001 ([native-world.md](native-world.md)) walked the hero across Lorencia in a silent, empty world.
This milestone joins the merged modules into that session, at the points of the client loop where the client runs
them:

- the client's own audio decisions: the hero's footsteps every logic step and the per-frame ambient and music block
  after the frame cap, played through SDL2 audio in the window and written to a WAV file headless;
- RenderTerrain's view: the client frustum, its block and tile tests, and the per-frame terrain update over that box;
- monsters and NPCs, animated with the client action tables, from a clearly labelled demo placement file;
- the EffectManager effects that the creation of some classes attaches.

The footstep routines that the integration needed were not recovered yet. They are reconstructed in
`reconstructed/audio/hero_sound.c` and compared with the client's instructions in Unicorn.

Labels used below:

- **Verified** means the authored C equals the client's instructions on every compared case.
- **Extracted** means the client's code was run under Unicorn with recording stubs, without an authored C to compare.
- **Static** means a reading of decoded instructions that was not executed.
- **Demo** means an input the server provides in the real game, made up here and labelled.
- **Viewer choice** means native code that is not client behaviour.

## Identity

| Input | SHA-256 |
|---|---|
| `main.exe` (target) | `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a` |
| Restored text at `0x00401000` (capture09) | `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` |
| Second section at `0x01a7c000` (run10) | `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f` |

`scripts/validate_hero_sound.py` pins the SHA-256 of the 11 routine bodies it executes; they are in its `BODIES`
table and in its report.

## 1. The hero's footsteps (verified)

### Where the client plays them

There are only two calls to PlayWalkSound `0x013b1f61`. Both sit in one block of the per-character routine
`0x013b23f8`. All nine SND_Play call sites that pass the walk sound ids are inside PlayWalkSound.

The order inside one logic step of the in-world tick `0x0185613e` is a static reading:

1. **MoveHero `0x016a9150`.** Its tail stores HeroTile (see below).
2. **MoveCharacters `0x0137a7ce`.** For every live character, `0x0137a716` runs these in order:
   - the visibility byte `o+0xb`, from TestFrustrum2D at the character's tile;
   - the mover `0x013b852a`, which skips the hero;
   - MoveCharacter `0x013a85a9`. It animates through `0x013a763e`: the animation step `0x013960d2`, then the foot
     reset;
   - `0x013b23f8`, which holds the footstep trigger.

So the trigger sees the animation frame after this step's tick. `0x013b23f8` reaches the trigger unless the model is
missing or has no actions, or the character is not visible (static).

### The four pieces (verified)

**Footstep trigger `0x013b8090..0x013b8187`.** The trigger fires only when all of these hold:

- the object is the Player model (`o+0x5c == 0xa91`);
- the character is the hero (`c == [0x0a39d754]`);
- the action is a walk or a run, `0x32..0x3e` or `0x4f..0x6e`.

Then two checks run in order:

- At frame `o+0xd0 >= 1.5`, if foot flag `c+0xc` is clear, it sets the flag and calls PlayWalkSound.
- At frame `>= 4.5`, if foot flag `c+0xd` is clear, it does the same with that flag.

The compares are `comiss` followed by `jb`, so a NaN frame never plays.

**Foot reset `0x013a773c..0x013a777e`.** When the animation step returns AL = 0, `c+0x168 = -1` and both foot flags
are cleared. AL = 0 means the tick wrapped or clamped. With both pieces together, a walk cycle plays two steps.

**PlayWalkSound `0x013b1f61`.** The rules apply in this order; the first match decides:

| Condition | Sound id |
|---|---|
| hero action `0x59..0x5f` | none |
| `0x0106b9f7(hero, 2, 1)` on the singleton `0x009c104e` is true (an external character-state manager, not analysed further) | none |
| world 2 (Devias), HeroTile not 3 and below 10 (signed) | 10 `pWalk(Snow)` |
| world 0 (Lorencia) or 3 (Noria), HeroTile 0 | 9 `pWalk(Grass)` |
| water world (`0x016a88d3`: Atlans 7 and `0x80..0x82`, `0x18..0x1d`, `0x24`) and not in the safe zone (`c+4`) | 11 `pSwim` |
| worlds `0x39`, `0x3a` (`0x00ea233c`), `0x79`, `0x3e` (`0x00e42f6d`) | 10 |
| world `0x7a`, attribute `0x8000` at `((y & 0xff) << 8) + (x & 0xff)` of the hero tile | `0x4d1` (`swampDark_bridge`) |
| world `0x7a`, other attribute | 8 `pWalk(Soil)` |
| otherwise | 8 `pWalk(Soil)` |

Every sound goes through `SND_Play(id, 0, 0)`. SND_Play plays one instance per id (see
[client-audio.md](client-audio.md)), so a step that is still sounding is not restarted.

**HeroTile `0x0b437c10` (MoveHero tail `0x016ad7a5..0x016ad81f`).** The tail computes:

- `index = ((int)y / 100 << 8) + (int)x / 100`, from the hero position `+0x33ac`, with `cvttss2si` and a truncating
  `idiv`, wrapped to 32 bits;
- a negative index reads 0 and an index above `0xffff` reads `0xffff` (the `jns` tests the add's sign);
- HeroTile = `TerrainMappingLayer1[index]` (`0x0b735420`).

There are 17 early exits from MoveHero that skip the tail, for example a dead hero or a stopping buff. The
per-frame audio block reads HeroTile too: the Lorencia pub floor is tile 4.

### Verification

`scripts/validate_hero_sound.py --cases 10000` uses `scripts/actor_machine.py`, the strict machine:

- an undefined read, an undeclared access or an unmapped access stops a case;
- only the fields each routine reads are defined.

These run as client code: the world predicates, the safe-zone getter, the tile index and the vector accessor. These
are recording stubs: SND_Play, the singleton getter and its predicate (returning the case's AL), and the animation
step (returning the case's AL with poisoned upper bits).

| Piece | Cases | Equal | Negative controls detected |
|---|---:|---:|---|
| PlayWalkSound, from its entry (worlds incl. boundary tiles, actions, safe bytes, manager AL, attribute grids) | 10,000 | 10,000 | no action gate 1,994; no manager 1,584; `<= 10` on Devias 48; Noria soil 76; swim in the safe zone 1,027; swapped bridge index 216 |
| footstep trigger, in `0x013b23f8`'s frame, with PlayWalkSound underneath | 10,000 | 10,000 | thresholds 1.0/4.0: 193; strict `>`: 100; NaN plays: 90; runs up to `0x6f`: 98 |
| foot reset, in `0x013a763e`'s frame (AL 0, 1, 2, `0xff`) | 1,250 | 1,250 | reset on non-zero AL: 1,250 |
| HeroTile tail, in MoveHero's frame (positions incl. negative, huge, NaN, infinite) | 10,000 | 10,000 | floor division 373; swapped axes 2,486; wrap instead of clamp 7,451 |

The run took 45 s; the report is local (`native/scratch/world2/reports/hero-sound-10000.json`). The portable tests
are `reconstructed/audio/test_hero_sound.py`: worked examples and the validator's Python statements on random cases.
A 600-case private comparison runs with `MU_RECOVERY_INTEGRATION=1`.

## 2. Sound in the native session

`native/core/mu_world_audio.*` (in `libmuaudio`) runs the reconstructed rules on the native engine at the client's
points:

- **Every logic step.** A step hook at the end of `mu_walk_step`, after MoveHero and the hero's animation step, runs
  HeroTile, the foot reset with the AL of the hero's tick, the trigger and PlayWalkSound → `SND_Play`. The sound ids
  are registered at startup by the loader `0x018433ed`; the native host loads them from the table on first use.
- **Every rendered frame.** After the frame cap, the per-frame block `0x0185280c..0x01854498` runs, as it does after
  `0x01852668` in the frame driver (verified in [client-audio.md](client-audio.md)), then `System::update`. Its
  inputs are the world, HeroTile, the hero's safe-zone byte and tile, and the attribute word at the hero tile.
- **World entry.** OpenWorld's Music-group volume (0.4 for Lorencia). Then `Data/Sound/Option.ini` is applied as the
  audio host does.

The native session has no weather system and no character-state manager. These inputs are fixed and labelled in the
code:

- rain `0x0a3a9acc` = 0;
- `0x0106b9f7` returns false;
- no boss zone.

**Output.** The window opens an SDL2 audio device (float, stereo, 44.1 kHz). Each frame, the main thread mixes the
frames due at the clock plus 120 ms and queues them with `SDL_QueueAudio`, so only the game thread touches the
engine (viewer choice). Headless runs mix the same amount per virtual frame and write a 16-bit WAV (`--wav`). The
sound ids and music indices resolve through the table that `scripts/extract_audio_tables.py --tsv` extracts locally
(`--sound-table`, never committed). Without it the decisions still run and the session is silent.

**Lorencia result** (installed data, demo route below, 60 s):

- The main theme starts at frame 1 (music index 21, `main_theme.mp3`).
- `Pub.mp3` (index 0) plays when the hero steps on the pub floor, layer-1 tile 4; the wind loop stops there.
- The main theme comes back outside the pub.
- 51 footsteps: 45 `pWalk(Soil)` on the town stone and the pub floor, 6 `pWalk(Grass)` in the field east of town.

The WAV of the GL run and of the software run are byte-identical.

## 3. Terrain in the walk view (terrain parts compared in client-terrain-frame.md)

`mu-world`/`mu-walk` now draw the terrain the way RenderTerrain sets it up:

- **CreateFrustrum `0x016cba24`.** Built from the modelview that MoveMainCamera/BeginOpengl leave, read the way
  `0x0184a569` reads it. The inputs are aspect = window width / 640, far = the far plane MoveMainCamera set
  (3,257.8 in Lorencia), and the camera FOV.
- **CreateFrustrum2D `0x016d20d9`.** Built around the hero in zoom mode 0, with the scale and distance taken from the
  world camera record (static readings of `0x0098ac7c` and `0x0098ac45`):
  - scale = width / 640 · Distance · Z_Distance · 1;
  - distance = 2400 · Distance · Z_Distance.
  Which zoom mode the client is in, `[0x0bdb5880]`, was not traced; mode 0 is an assumption.
- **Visibility tests.** The 4×4 block and tile tests of TestFrustrum2D (`mu_terrain_render`) apply in scene state 6.
- **Per-frame update `0x016ca4fa`, over the frustum box.** The light copy and the waves run over that box. The water
  UV scroll and the animated-layer counter follow the world time (one step per 40 ms).

In Lorencia at tile 150,127 at 1280×800, the client box (112,108)–(168,160) draws 1,834 faces. The NATIVE-WORLD-001
square, which `--legacy-box` still selects, draws 5,184 faces.

## 4. Monsters and NPCs

**The placement file (demo).** In the real game the server places every monster and NPC and sends their paths.
`native/world/lorencia-demo-placement.txt` stands in for those packets. Its first line says it is a demo placement,
not client data, and every line gives a server class, a tile, a direction and an optional wander radius. The
Lorencia demo places:

- six town NPCs: smith, wizard, storage, guild master, gambler, and a goblin in the pub;
- the two effect classes below;
- four field monsters east of town: Bull Fighter, Hound, Budge Dragon and Spider.

`native/core/mu_world_actors.*` handles each line with client rules:

- **Class to model, opener and scale.** The CreateMonster table of NATIVE-ACTOR-001, or for the effect classes the
  extraction below.
- **Action speeds and loop flags.** OpenMonsterModel and OpenNpc with the class speeds (`mu_actor`).
- **Every 40 ms step.** SetAction `0x012affa4` and the animation step `0x013960d2` with the tick.
- **Movement.** MovePath `0x012b0846` and MoveCharacterPosition `0x0137b351` at CharacterMoveSpeed with the
  MoveSpeed word 10. Character create stores 10 (`0x0137dbb2`, static).

These parts are demo or inference, not client readings:

- The wander targets, and the straight cell runs toward them that stop before walls and safe cells, are demo inputs:
  they stand in for the server's paths.
- Action 2 while moving and 0 while standing follow the action-index inference of [client-actors.md](client-actors.md).
- NPCs stand in action 0.

Three NPC files are not used: `Female01`, `Man01` and `Girl01` have no meshes of their own, because their parent
case assembles them from part models.

### Effect classes (extracted)

The NATIVE-ACTOR-001 class extraction stopped classes 750–753, 758, 838, 873 and 925 at the EffectManager singleton
getter `0x00aee554`. `scripts/extract_effect_classes.py` reruns the same extraction with the factory `0x00a797a0` and
the attach `0x0129f9c6` as recording stubs. The vec3 constructor and the shared-pointer test run as client code.

| Class | Model (OpenNpc) | Effects (scale, position) | Attach |
|---|---|---|---|
| 750–753 | `0xa89` `hs_dimensiondoorA` | `twister02-cyan01` (90), `twister03-cyan01` (230), at (0, 0, 0) | bone 1, follow, not timed |
| 758 | `0xa88` `hs_dimensiondoorB` | `twister02-magenta01` (90), `twister03-magenta01` (230) | bone 1, follow |
| 873 | `0xa52` `new_maple` | `leaf_particle_F2e` (9, (0, 0, 70)) | bone 1, follow |

The extraction also shows these details:

- every effect has rotation 0, no template transform, no tint and start frame 0;
- the object scale is 0.9 for the doors and 1.0 for the maple;
- 838 and 925 read a per-monster list from an uncaptured static (`0x0bdcfc10`) and stay out.

The values agree with the static reading in [client-effect-manager.md](client-effect-manager.md). They are generated
into `reconstructed/actors/effect_class_table.h`; the private test regenerates the header byte for byte.

## 5. Effects in the walk view

Each effect-class actor gets its effects as clones from the EffectManager scene (`mu_effect_scene`: template cache,
clones, octree). Every frame:

- the owner path sets the external matrix to the object scale at the bone's point;
- the node update runs with dt 0.1, the client's `[0x01cf103c]`;
- the render pass queries the octree with the camera's frustum and draws the visible effects in octree order, with
  depth writes and alpha test off.

The OpenGL front end draws through a new callback (`mu_effect_scene_render_to`). The software rasterizer uses the
existing path.

The bone's point is its matrix translation times the body scale, plus the origin, which is where the transform places
a vertex on that bone. This is a viewer choice: the bone matrix path of `0x0129fd4f` was not traced, so the bone
rotation is not applied. In Lorencia the dimension door shows its cyan twister inside the ring, and the maple tree
sheds red leaves.

## Running it

```sh
make -C native && make -C native world
G="$MU_GAME_ROOT"; T=/local/audio-tables.tsv     # scripts/extract_audio_tables.py --tsv (local only)
native/build/mu-world --game-root "$G" --placement native/world/lorencia-demo-placement.txt --sound-table "$T"
native/build/mu-world --game-root "$G" --headless --backend gl --frames 1500 --every 5 --out-dir DIR \
    --placement native/world/lorencia-demo-placement.txt --sound-table "$T" --wav DIR/walk.wav \
    --walk "130,124 125,131 130,131 134,129 138,128 142,128 146,130 150,127 154,127 158,127 162,127 166,127 170,127 174,127 178,127 182,128 185,126"
```

Other options:

- `--no-audio` disables sound;
- `--legacy-box` draws the NATIVE-WORLD-001 terrain square.

Every frame report adds HeroTile, the footstep count, the active voices, the last music index, the faces drawn, the
frustum box and the visible effects. The summary adds the sound and actor statistics.

## Tests

**Portable** (`make test`):

- `reconstructed/audio/test_hero_sound.py`;
- `reconstructed/actors/test_effect_class_table.py`;
- `native/tests/test_native_world2.py`, which runs `mu-walk` on the synthetic world of `test_native_world.py` with
  synthetic sounds, table, models and effect. It checks:
  - every footstep against an independent statement of the trigger and reset over the per-step reports;
  - grass and soil ids, and silence while standing;
  - the WAV length and its wind and footstep content;
  - actor resolution, the speeds, wander moves and arrivals, the effect instance, and refused placement lines;
  - the frustum box, culling against the legacy square, and determinism.

**Private** (`MU_RECOVERY_INTEGRATION=1`, `MU_GAME_ROOT`, optional `MU_AUDIO_TABLE`):

- the 600-case Unicorn comparison;
- the regenerated effect table;
- a Lorencia walk into the pub and out to the field: 16 arrivals, grass and soil footsteps, HeroTile 0, 3 and 4, 12
  actors, 3 effect instances, the main theme again after the pub.

## Local renders

These are in `~/Documents/mu-mac-tools/native/renders/world2/` and are not committed:

- **`lorencia-gl/`.** 301 OpenGL headless frames at 1280×800, every 5th frame of a 1,500-frame walk (60 s), with
  per-frame state in `lorencia-gl.jsonl`. The route goes from the town square into the pub, past the maple tree and
  the dimension door, out of the east gate to the field monsters. It has 17 clicks and 17 arrivals, at 12.0000 units
  per step.
- **`lorencia-walk.wav`.** The walk's audio: main theme, pub music, wind, 51 footsteps.
- **`lorencia-soft/`.** The same run with the software rasterizer at 960×600, every 15th frame. Its WAV is
  byte-identical to the GL run's.
- **`lorencia-gl-contact.png`.** 16 frames of the walk.
- **`culling-client/`, `culling-legacy/`.** The same view with the client frustum and with the legacy square.

**Window.** With 12 actors, 3 effect instances and the SDL2 audio device (SDL's dummy driver in the check run),
`mu-world` ran at 24.92 FPS over 8 s standing and 24.45 FPS over 10 s while walking into the pub (cap 25). It queued
8.15 s and 10.14 s of audio.

## Unresolved

- **Live comparison.** No live side-by-side capture was made for this milestone, because the game lock was held and
  the character's location was not checked (see the handoff).
- **Static readings.** The zoom mode in `[0x0bdb5880]`, the MoveSpeed default and the visibility condition of the
  trigger are static readings. The character-state predicate `0x0106b9f7` is opaque.
- **Not ported.**
  - SND_Play sites of other game events: skills, monsters, NPC voices and items.
  - The monster sounds that OpenMonsterModel registers.
  - The bone rotation of the effect owner path `0x0129fd4f`.
  - NPCs assembled from part models.
  - Classes 838 and 925.
  - Rain and the event-world audio managers.
- **Demo.** The placement and the monster wander are demo stand-ins for the server.
