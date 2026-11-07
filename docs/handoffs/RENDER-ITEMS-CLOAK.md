# RENDER-ITEMS-CLOAK

Branch/worktree `claude/render-items-cloak` (Claude Opus 5.5), from `origin/claude/render-items-002t` (`53b9f7e7`,
#341); merged main `138b756e` (#338..#341) as `dd805a35` (clean). No live client, launcher, network or hosted workflow.
No full gate in the lane (2026-11-04 test budget).

Scope: the capes of wings `0x2382`..`0x2385`, `0x2394`, `0x2395` in the world, for players and the hero.
[Finding: client-render-items.md part 23](../research/client-render-items.md#part-23-the-wings-physics-capes-render-items-cloak).

## Result

- **Where the client draws the cape (verified).** Not from the item model: it is a **physics cloth** that
  RenderCharacter `0x01363260` owns per character.
  - MoveCloth `0x01362f24` (call `0x0136ab80`) steps every cloth of the OBJECT every frame: `Move2(0.005, 5)`
    (`0x00fd821e`).
  - Behind its cloth flag `[ebp-0x4d]` (`0x01366edf..0x01367530`), RenderCharacter calls RenderCloth `0x01363098`
    (`0x0136aba2`) after the body parts and before the linked items.
  - RenderCloth creates the cloths once through CreateCloth `0x01357ccc`'s wing switch (`0x0135b558`, `0x0135b79f`,
    `0x0135c419`), steps them again on that frame, and renders each one (virtual slot 8, `0x00fd8bc2`).
  - The cloth is a 10×10 mass-spring grid. Its top row hangs from Player bone 19. It has collision spheres on bone 17
    and is drawn as two-sided GL_QUADS with its own bitmap:
    - `0x83f6` `kundun_innocence2.tga`;
    - `0x83f7` / `0x83f8` `kundun_sparkle3(_1).tga` (two half-cloths for `0x2384`/`0x2385`);
    - `0x846b` `BlackCloak_3.tga`.
  - The wind is the physics manager's random walk: five steps per logic step in the frame driver `0x01851d39`.
  - The meshes that RenderObjDraw leaves out are the cloth meshes of the models (InnocenceCape mesh 0, SparkleCape
    mesh 1). No hidden-mesh flag selects them.
- **Cloth: yes.** Ported deterministically in `reconstructed/cloth` (binary32, the client's operation order, CRT
  sin/cos/sqrt through host libm as the other units):
  - Create, SetFixed, InitForces/InitForce, the force springs, integration, sphere collisions, constrain springs,
    apply, stretch limits;
  - Render's GL stream, the wind walk, CreateCloth's six cases and RenderCharacter's cloth flag.
- **Native** (`native/world/world_cloak.c`, hooks in `parts/hero.c`, `parts/players.c`, `world_rt.c`):
  - the cloths live with the OBJECT and are dropped when the wing or the viewport generation changes, and at travel;
  - `world_cloak_frame` runs every rendered frame after the logic steps (the wind, then MoveCloth for every wearer
    drawn since its OBJECT was made). A headless capture cadence therefore does not change the cloths;
  - the draw sits between the body parts and the linked items: the flag, CreateCloth, then Render through the backend
    (quads as two triangles, the four bitmaps in the cloak's own texture set, soft and GL).
  - Summary line: `{"cloak": true, "created", "steps", "drawn", "gated", "wind_steps", "wind"}`, printed only after a
    cloth wing was drawn.
- **Who gets a cape (as the client).** The flag needs a cloth class:
  - base class 0, 4, 6, 7, 8, 9, 0xb, 0xc, 0xd or 0xf, or skin 3/0x33/0x43;
  - otherwise one of the wings `0x23f1`/`0x2401`/`0x24c6`.
  A Dark Knight or Elf wearing InnocenceCape shows only the upper meshes, in the original too.

## Checks

Env: `. ~/Documents/MTM/mu-mac-tools/native/private-env.sh` (`MU_RECOVERY_INTEGRATION=1`, `MU_GAME_ROOT`,
`MU_SECTION3=$HOME/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin`,
`MU_EVIDENCE_DIR`, `MU_SNAPSHOT_DIR`, `MU_PATH_DIRECTIONS`, `MU_VALIDATOR_CACHE`, ...), `MU_LANG_DIR=$MU_SNAPSHOT_DIR/lang`
for the inventory render. Heavy steps `nice -n 10`, `make -j4`, `--jobs 2`; every command from the repository root.

| Check | Result | Wall |
|---|---|---:|
| Build `make -j4` (+ `make -C native client world`) | pass | 15.0 s |
| `validate_item_cloak --mutations` (new row, once, final `cloth.c`) | **2,090 cases, 0 mismatches, 0 stopped**: create 66, step 528, render 528, wind 200, gate 768; **38/38 mutants caught**, all compiled, every anchor once, none equivalent | 84.8 s |
| `run_validators.py --private --no-mutants --cache --affected origin/main --jobs 2` at `0557de1b` | **23/23 pass** (below) | 565 s |
| `run_test_suites.py --affected origin/main` (`MU_RECOVERY_INTEGRATION=0`, 2 jobs) | 7 suites, 1,343 tests, 1,139 passed, 204 skipped, 0 failures | 323.5 s (+86 s selection) |
| Private, from the root: `test_native_item_cloak` (new: 5 portable, 1 Unicorn, 1 scene), `test_native_world_predraw`, `test_native_hero_items`, `test_native_players`, `test_render_effects20`, `test_world_parts` | 53 tests OK | 224 s |
| Private `test_native_world`, `test_native_world2` | 22 tests OK | 15.6 s |
| `tests.test_validators_manifest` | 17 tests OK | 0.8 s |
| `scripts/audit_repository.py` | 2,085 staged files, 0 rejected | 17.7 s |

Rows at `0557de1b` (cases / s): terrain 583,500 / 430.0, audio_combat 19,548 / 36.0, meshdraw 14,619 / 53.7,
icarus_c2 8,400 / 15.0, movement 6,614 / 47.2, item_callers 6,013 / 1.5, audio_charsel 5,968 / 3.1, audio_callers
5,528 / 5.0, path 4,719 / 36.7, worlds_fog 4,044 / 7.5, audio_items 3,000 / 2.9, audio_domains 2,544 / 23.6,
terrain_remaining 2,147 / 4.0, item_cloak 2,090 / 72.9, viewport_monsters 1,963 / 8.1, worlds_f 1,818 / 0.4,
model_light 1,433 / 4.6, model_edge 954 / 110.3, render_effects17 618 / 10.2, render_effects18 540 / 1.6,
render_effects16 424 / 3.2, render_effects19 400 / 1.1, session_party 200 / 0.7.

`--list-affected origin/main` (symbol level, after `make`) selects these 23. Most come through `native/Makefile` and
libmunative (the new `cloth.c`); item_callers, render_effects18 and render_effects19 come through their `reconstructed/`
mutant copies. 6b/8b review: no existing exported symbol, struct field or table changed. The world runtime gains one
field (`cloak`) and the two parts gain a call. The modules that run world scenes with players and hero items are in
the private run above.

Mutants (all caught; each run stops at its first mismatch, in the family that compares its code): the force weight
(unsigned compare, +2), damping, gravity pick, calm clamp, integration order, constrain half, fixed-vertex count,
stretch factor and minimum, sphere push and swizzle, fixed-row swizzle and taper, grid taper and height, the drop
parabola, the second diagonal's first row, spring minimum and flags, force slack, the phase step and wrap, the wind
angle, wind y, world 0x37's wind, the v clamp, the back face's winding, the OBJECT alpha, the three wing cases
(origin, sparkle offset, sphere radius), the wind clamp, and the gate's class list, `+0x0e`, worlds, PK light and
glow classes.

## Scenes, byte identity, renders

- Lorencia scene (`mu-walk` soft 960×600, tile 128,124, `--class 0 --hero-item wing=Item/InnocenceCape.bmd`, players:
  class 0x00 with `0x2382`, class 0x04 with `0x2394`, class 0x01 with `0x2382`, 91 frames):
  - `created 3, steps 273, drawn 21, gated 7` (the Dark Knight on every drawn frame);
  - frames 45 and 90 are byte-identical when drawn every 15 or every 45 frames;
  - the same scene through headless GL `mu-world` draws the cape;
  - runs take 1.8 s (main) / 1.5 s (branch).
- Byte identity, one default-draw sweep (`fidelity_tour.py render`, no draw_all). The base is main `138b756e`
  (`mu-world` from a temporary detached worktree), and the manifests are copies with the pre-move paths
  `~/Documents/mu-mac-tools` → `~/Documents/MTM/mu-mac-tools`:
  - October 22 tour: 28/28 PNG, 28/28 OBJECT + light dumps, 14/14 reports identical (paths normalised). Wall
    18.7/18.7 s.
  - DATA-ACQ-002: 64/64, 64/64, 32/32. Wall 51.0/47.6 s.
  - No frame changed: the tours run `mu-world --no-audio` only (no players file, class-part heroes), so no wearer is
    in view.
- Inventory unchanged: `mu-render ui inventory` with codes 6300:0, 6301:13, 6302:0, 6303:13, 6318:0, 6319:9 (the six
  wings), time 123456. Main and branch are byte-identical (`e2d51ead…`), upper meshes only as the original (0.98 / 0.78 s).
- The demo is unchanged: no shipped demo player wears these wings (theirs are `0x22e9`, `0x230b`, `0x2311`). Among the
  test fixtures, `test_native_world_predraw`'s Seraph (class 0x00, `0x2384`) now gets two half-cloths; its DK
  (`0x2382`) and Elf (`0x2394`) wearers get none. That module counts effects, not pixels, and passes unchanged.
- Window-only crops (offline native renders, not original-client pixels), in
  `~/Documents/MTM/mu-mac-tools/native/renders/render-items-cloak/`:
  - `crop_hero_before_after.png` (main | branch, frame 45, the hero walking: the cape streams behind);
  - `crop_player_before_after.png` (frame 30: the class-0x00 player walking with its cape; the Dark Knight beside it
    keeps only the upper meshes);
  - `crop_inventory_after.png` (the six wings, identical on main).

## Limits

- **Flag inputs at rest.** The guild-war flags (`0x06fca13d`/`0x06fca13f`), the duel manager (`0x01d1e028`) and the
  hiding buff (`0x009c104e(c, 2, 1)`) are not ported. Native players have no buffs and sub-type 0. RenderCloth's draw
  tests are a static reading for those inputs. The gate family checks the flag with them at rest.
- **Not ported:**
  - the other CreateCloth cases (other wings, arg 4 = 1);
  - the armour cloths `0x0135ea29`/`0x01362755`;
  - the angle-matrix Create variant;
  - the glow and mesh passes;
  - sub-types `0x5bc`/`0x5bd`.
  `mu_cloth_render` refuses a cloth that would need a missing pass.
- **Wind.** It starts at 0 when the first cloth wing is drawn and uses its own MSVC rand() state. The client's shares
  the process rand() and has walked since start-up.
- **(inference) BodyScale/BodyOrigin.** The Player model's BodyScale/BodyOrigin at MoveCloth are taken to be the
  OBJECT's scale and position; the native host passes the character's.
- **Pose.** The pose is native's posed Player bones (`player_bones`, NATIVE-CHAR-001 / RENDERCHAR-001), not a capture.
- **Visibility.** A wearer is stepped from its first drawn frame until its OBJECT goes. The client steps characters
  RenderCharacter draws; the native player range stands in for that.
- **Untested floor.** The 0.01 floor of the sphere collision is ported but no random state reaches it (not mutated).
- **Quads.** GL_QUADS become triangles (0, 1, 2), (0, 2, 3).
- **No live comparison.** There is no live capture of a cape in motion.

## Release

Steward validators: validate_item_cloak (new; mutants once, 38/38, on the final `cloth.c`), validate_meshdraw,
validate_model_edge, validate_model_light, validate_movement, validate_path, validate_terrain,
validate_viewport_monsters, validate_terrain_remaining, validate_icarus_c2, validate_worlds_f, validate_audio_callers,
validate_audio_combat, validate_audio_domains, validate_audio_items, validate_session_party, validate_audio_charsel,
validate_render_effects16, validate_worlds_fog, validate_render_effects17, validate_item_callers,
validate_render_effects18, validate_render_effects19. All ran at `0557de1b` without mutants. Env: private-env.sh
(`MU_SECTION3` above, `MU_PATH_DIRECTIONS`).

Cleanup removes `mu-mac-tools/native/scratch/render-items-cloak/`, the base worktree `worktrees/cloak-base`, the
build directories and every render except the three crops. No new input needs to be kept. The worktree stays until
the steward merges.
