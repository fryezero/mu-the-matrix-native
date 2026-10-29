# The map-object effect table and its attach (RENDER-EFFECTS-008)

RENDER-EFFECTS-008, 2026-10-29. Follows [RENDER-WORLDS-G3](client-worlds-g3.md) §1 (the Deep Dungeon dragon fire is a
`.ein` effect attached by `0x0183067e`), [RENDER-EFFECTS-006](client-render-effects-006.md) (the EffectManager
request, attach and update path) and [the effect manager](client-effect-manager.md) §6. Labels: **live** = read
from the running client this lane started; **verified** = compared with the original instructions under Unicorn;
**static** = read from the instructions; **inference** = not checked by a read or by execution.

## 1. Live reads

Two sessions under the shared game lock, Nighty on MTM-1, the free-runtime prefix and the DATA-ACQ-002 route
(`mu-autologin.sh` steps from local copies of its helpers, 1728 × 1080 launcher mode from a rollback copy):

| Session | Lock held | Route (Warps window only) | Reads |
|---|---|---|---|
| 1 | 00:22–00:27 | Lorencia 139,130 → Deep Dungeon 3 (123,123) → Deep Dungeon 5 → Burning Kethotum → Lorencia 144,127 | window shot, `objread`, world word and the table graph at each stop; the `+0x3d0` lists of two type-67 and one type-62 object (DD3) and one type-160 object (136) |
| 2 | 00:32–00:34 | Lorencia only | the table graph again with the fixed reader |

No fight, NPC, item or trade action; only warp costs; ended in Lorencia; read-only memory reads and window-only
shots. `LauncherOption.if` was restored byte for byte after each session; the game copies the launcher mode into
`HKCU\Software\Webzen\Mu\Config\DisplayDeviceModeIndex`, which was set back to the owner's 2 (the owner's launcher
writes it again at every start); after session 2 `user.reg` matches its pre-session copy except Wine's `#time`
lines.

**The table is filled at startup, not per world (live).** The graph rooted at `0x06fbb7b0` (`langread
graph:0x06fbb7b0=8,6,0`) is the same in all five reads (Lorencia, Deep Dungeon 3 and 5, Burning Kethotum, and
Lorencia in a second client run): 442/442 comparable types equal, byte for byte in every consumed field.

**Reader fix.** The first session's reads lack one vector (world 137 type 53): the bytes after that node's vector
read as a std::string header (size 0, capacity 0xbd), and `langread`'s graph scan took the string shape and skipped
the vector. A candidate of both shapes is now followed as both (it only copies more); the second session's read is
complete.

## 2. What the table holds (live)

EnchantEffect's `+0x5c` std::map at `0x06fbb7b0`: **38 worlds, 443 (world, type) keys, 758 entries, 263 distinct
`.ein` paths.** Worlds: 2, 8, 33, 37, 38, 51, 56, 63, 80, 113, 116–120, 122–138, 140–145 (Aquila's Temple 145 has the
most, 93 entries). Layout (static, `0x0183067e` and its helpers):

* outer map key: the world (int); record `+0x3c` (`0x010f4ae9`): the type map;
* type map key: the object's **int32** at `+0x5c` (the find compares signed ints, `0x0096ba31`; every captured object
  has 0 in the high half); value: `std::vector` of 0x54-byte entries (`0x01849998`, `0x01849a75`);
* entry: `+4` std::string path, `+0x1c` position, `+0x28` rotation, `+0x34` scale, `+0x38` bone, `+0x3c` follow byte,
  `+0x3d` tint byte, `+0x44` start frame, `+0x48` `std::vector<int>` actions; `+0` and `+0x3e..+0x43` are not read.

Values: follow 1 in 739 entries, 0 in 19; tint 1 in 87; bone 0 in 328, bone −1 in 2 (Ignis Volcano types 175 and
176, following). 419 entries have no actions and start-frame bits `0x00220000` (a denormal, ≈ 3.1e−39: the
loader's unset value, passed as is); the 339 with actions have start 0 or small frames (2–26, 50). Deep Dungeon
116–120: one entry per marker type, `fire01-green01` (62), `fire01-blue01` (63), `fire01-red02` (64),
`fire01-magenta01` (65), `fire01-yellow01` (66) and **`fire01-red01` (67), the dragon fire**, scale 50 (60 for
type 67 in Deep Dungeon 3), bone 0, follow. One Abyss of Atlans path ends in a space
(`smoke13-black01.ein `); Win32 path normalisation drops it, and the live lists show the effect attached
(§4). `sd_fog04-white01.ein` (world 145) is not in the installed `Data/Effect`.

**Cross-check of the attached lists (live).** The `+0x3d0` std::list of a Deep Dungeon 3 type-67 marker holds one
record {effect, ctrl, template scale 60, bone 0, follow 1, timed 0, lifetime 0} whose instance is named
`fire01-red01`; a type-62 marker holds `fire01-green01` (50, bone 0); a Burning Kethotum type-160 object holds
`fire09-red01` (50), `twinkle12-red01` (260), `smoke11-red01` (50) in that order: the table's vector order.

Muun: the read also holds MuunEffectInfo (`0x06fbb46c+0x38`, 16 records, identical to the lang snapshots);
`live_effect_table_to_plain.py` writes them as `muuneffects.tsv`.

## 3. The attach `0x0183067e` (verified)

For the current world, when the outer map holds it (`0x010fa24c`; otherwise it returns at once and **no list is
cleared**), for sectors i, j = 0..15 (sector i·16 + j, `0x0bdb61f0 + 0x10·s`, objects through `+0x354`), for every
object: clear its list `+0x3d0` (`0x009b0451`); find its int32 `+0x5c` in the type map; when found, for each entry in
vector order: get the manager (`0x00aee554`), copy the actions (`0x00a781ef`), call the factory `0x00a797a0(path,
position, rotation, scale, template transform 0, &type word, tint, actions, start)`, attach the effect when it is
valid (`0x00a78918`) with `0x0129f9c6(effect, bone, follow, 0, 0.0)`, release the factory's pointer (`0x00965b01`)
either way; after the vector, `0x0129f4cb` once (the first update, dt 0).

`reconstructed/objects/map_effects.c` makes the same calls through ops. `scripts/validate_map_effects.py` runs the
client routine (body SHA-256 prefix `1105527e111623dc`) in Unicorn with the std::maps, vectors, inline and heap
strings, the world word, sector table and object links built in memory; the map helpers and the shared-pointer test
run as client code, the engine calls are recording stubs:

* family `attach`: **300 cases, 0 mismatches**, 10,472 calls, 1,866 attaches; coverage: 65 absent worlds, 3,826
  objects (1,198 found), 444 keys with a high half, 537 negative table keys, 455 empty vectors, 779 invalid paths;
* **14/14 compiled mutants caught** (sector order, no clear, short type key, prime when not found, attach of a null
  effect, forced follow, timed, lifetime, release only when valid, entry order, type word, unsigned key compare,
  clearing on an absent world, prime before the entries);
* family `live` (local captures, not in the registry): the decoded live table over the real sector lists of all
  **32 DATA-ACQ-002 captures** and the three of this lane: 35/35 equal, and **every object's attach count equals its
  live `+0x3d0` list size** (149,735 + 15,996 objects; e.g. Deep Dungeon 3: 143 effects on 143 markers, Burning
  Kethotum 309 on 185 objects, Kanturu Underground 3,077 on 2,175).

## 4. Native consumer

* `native/core/mu_map_effects.{c,h}` loads `MU_LANG_DIR/mapeffects.tsv` (absent: nothing changes) and runs
  `mu_map_effects_attach` for the world when the particles part opens (after the objects exist, as the world loaders
  call it). The ops go to RENDER-EFFECTS-006's EffectManager scene: clear → the object's records leave the list,
  create → the factory clone with tint, actions and start frame (`mu_world_particles_ein_create`; null when the
  template does not load), attach → the list record (`mu_world_particles_ein_link`). The request path drops trailing
  spaces and dots (Win32 normalisation; the Abyss lists hold that effect live).
* **Update in every world (static):** RenderObjects calls `0x0129f671` after RenderObjectVisual for every visible
  object with a non-empty list (`0x016d51d8..0x016d51f5` and `0x016d534e..0x016d536b`), not only in the worlds whose
  visual runs through the objects runtime's handler. RenderObject animates the object before its `+0x68 == −2` test,
  so the table's hidden markers (every Deep Dungeon marker is −2 live) are posed for their bone; native now poses a
  listed object when its RenderObject log records the animation.
* **`+0x38` = 1 (static + live):** CreateObject calls Initialize `0x0129eb81` (`0x016d8606`), which writes
  `+0x38 = 1` (`0x0129efb1`); the effects' owner gate reads it. All 149,735 objects of the 32 captures hold 1.
  Native's CreateObject leaves the initializer's fields to the runtime, which now sets it (Burning Kethotum's 0xb5
  cycle still writes its own value).
* Capacity: the objects' scene holds 4,096 instances and links (Kanturu Underground needs 3,077; other scenes keep
  256).

Not modelled: `0x0129f4cb`'s dt-0 update at load (the first per-frame update runs before the first draw); bone −1
following (`0x0129faee`, two Ignis Volcano entries, counted `unposed`); the clear's effect on lists filled by other
paths before the table (none in the captured worlds); the Muun table's consumer (no native Muun owner yet).

## 5. Fidelity (DATA-ACQ-002 captures)

`fidelity_tour.py` over the 32 captures, mean |Δ| (8-bit, masked client area). Base = origin/main `9b821b1` built
separately; this branch without `MU_LANG_DIR` is **pixel-identical to base in 32/32 captures in both modes**; "after"
= this branch with the local `mapeffects.tsv`. Normal mode draws two frames; `draw_all` draws all 25 steps, as the
client, so the effects have run 2.5 s.

| Capture | Attached | Normal | draw_all | Visible |
|---|---:|---|---|---:|
| 113 Nixies Lake | 1,224 | 7.001 → 7.001 | 7.001 → **5.840** | 11 |
| 116 Deep Dungeon 1 | 93 | 2.592 → 2.592 | 2.592 → 2.592 | 6 |
| 117 Deep Dungeon 2 | 95 | 2.534 → 2.534 | 2.534 → 2.520 | 6 |
| 118 Deep Dungeon 3 | 143 | 3.203 → 3.203 | 3.203 → **3.026** | 6 |
| 119 Deep Dungeon 4 | 133 | 2.545 → 2.545 | 2.545 → **2.343** | 6 |
| 120 Deep Dungeon 5 | 270 | 2.687 → 2.687 | 2.687 → 2.655 | 9 |
| 122 Swamp of Darkness | 1,022 | 1.709 → 1.581 | 1.709 → 1.597 | 11 |
| 123 Kubera Mine | 187 | 4.321 → **3.854** | 4.321 → **3.852** | 18 |
| 131 Scorched Canyon | 477 | 8.068 → 8.068 | 8.068 → 7.985 | 2 |
| 132 Red Smoke Icarus | 858 | 26.373 → 26.373 | 26.373 → 26.364 | 3 |
| 134 Gray Aida | 1 | 13.072 → 13.022 | 13.072 → 12.932 | 5 |
| 135 Old Kethotum | 441 | 2.388 → 2.388 | 2.388 → 2.224 | 3 |
| 136 Burning Kethotum | 309 | 8.661 → 8.664 | 8.661 → 8.669 | 7 |
| 137 Kanturu Underground | 3,077 | 5.790 → 5.681 | 5.790 → 5.842 | 38 |
| 138 Ignis Volcano | 954 | 4.139 → 4.065 | 4.139 → 3.898 | 36 |
| 142 Twisted Karutan | 1,031 | 13.480 → 13.480 | 13.437 → 13.496 | 41 |
| 143 Kardamahal | 995 | 10.911 → **9.787** | 10.911 → **10.107** | 73 |
| 144 Swamp of Destruction | 2,320 | 12.415 → 12.311 | 12.386 → 12.213 | 64 |
| 56 Swamp of Calmness | 40 | 7.196 → 7.143 | 7.196 → 7.127 | 25 |

Pixel-identical to base although the table attaches there: 38 (7 attached), 63 Vulcanus (8) and 128–130 Abyss of
Atlans (194, 860, 867), where no listed effect passes the scene's frustum at the arrival tile, and 140 Bloody Tarkan
(220), where two do but change no pixel (inference: hidden by nearer geometry). Temple of Arnil 133 (894 attached,
10 visible) changes pixels but not the mean at three decimals. Unchanged because the table holds nothing for the
world: 6, 40, 79 (two captures), 91, 112.

The Deep Dungeon 3 shot: the dragon heads' fires (type-67 markers at (12129, 12055, 259) and (12137, 11755, 259))
burn at the same places as live. Three captures move away from live in draw_all: Burning Kethotum (+0.008: the
crystal base's `fire09-red01`/`smoke11-red01` glow is drawn where the live shot shows the `Lighting` entries'
yellow arc), Kanturu Underground (+0.052) and Twisted Karutan (+0.059), where many large haze/fog effects are drawn
and the 2.5 s of native effect time differs from the live client's minutes (particle phase and density); recorded,
not tuned.

## 6. Limits and what is left

* The effects' own look is RENDER-EFFECTS-006 / NATIVE-FX-002's (the `.ein` tree update and render); their
  particle phase at the capture time is not reproducible (the client had run the effects since the world load).
* Bone −1 following (`0x0129faee`) for Ignis Volcano types 175/176; `0x0129f4cb`'s dt-0 first update.
* The table is decoded game data: it stays local (`mapeffects.tsv` in the lang directory). Without it the native
  world draws what it drew before.
* Muun per-object table `0x0114203d`: the 16 records are exported (`muuneffects.tsv`); its consumer needs native
  Muun owners (pets), not present yet.
