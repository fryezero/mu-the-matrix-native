# RENDER-EFFECTS-020

OBJECT-owned item particles: the last requests the item effect programs refused. Wings `0x2384`/`0x2385` (Cloak of
Brilliance, `SparkleCape.bmd`) create `0x810a`/0x11 and `0x81cf`/0 with their own OBJECT as owner; since
RENDER-ITEMS-CALLERS-001 (#330) and HERO-ITEMS-001 (#334) the world callers ran these programs but refused the two
requests.
[Finding: client-render-items.md part 22](../research/client-render-items.md#part-22-object-owned-item-particles-render-effects-020).

Branch/worktree `claude/render-effects-020` (Claude Opus 5.5), from main `f2370871`. Merged main `8623fced`
(#335, #336: tests and docs only) as `f58b83f8` and `0c3c2777` (#337 RENDER-WORLDS-RAKLION) as `23f9ea60`.
"Before" numbers come once from a detached base worktree at `f2370871`. No live client, launcher, network or
hosted workflow. No full gate in the lane (2026-11-04 test budget). The `tools/python`, `evidence` and `input`
links come from the main checkout and are never staged.

## Census (scope 1)

Over the 83 program types (43 owner programs of RENDER-ITEMS-002Q, 40 pre-draw programs of 002R/002S, 3,245
ops), the OBJECT is passed as an owner by:

| Request | Sites | Before | After |
|---|---:|---|---|
| CreateParticle `0x810a`/0x11, OBJECT owner (`0x2384`, `0x2385`; `rand() % 3` gate under the frustum flag) | 1 op row, both types | refused, counted | created, owned by the item OBJECT |
| CreateParticle `0x81cf`/0, OBJECT owner (same types; `rand() % 7` gate) | 1 op row, both types | refused, counted | created, same owner |
| CreateSprite / bone sprites with the OBJECT as sprite owner | 275 | routed | unchanged: one-frame records, the draw never reads `+0x34c` (part 19) |
| CreateJoint with the OBJECT as target (`0x22ec`, `0x248f`) | 20 | routed, target −1 | unchanged: kinds `0x7f7c`/0xe, `0x7fd3`/4 are RENDER-ITEMS-002T's |

Library run over the 83 types (scratch tool: random bone names, rand streams and frustum flag; 32 states per type):
`0x2384` 3 × `0x81cf`/0 and 2 × `0x810a`/0x11, `0x2385` 5 and 1 (1,000 states: 129/291, 131/292). Types without a
program make no request.

Scenes (refused = requests the programs could not create; native renders, `mu-walk` soft 320×240, Lorencia
128,124, CALLERS-001's four demo players and three drops unless said):

| Scene | Caller | Before (`f2370871`) pre_effects / refused | After |
|---|---|---|---|
| Crowd, 60 frames (the `test_native_world_predraw` fixture) | players | 92 / **2** | 93 / **0** |
| | ground | 18 / **1** | 18 / **0** |
| Crowd, a frame every 10 | players | 322 / **5** (4 owned + bow `0x1316`'s `0x7ffd`/0x1b) | 325 / **0** |
| | ground | 108 / **3** | 113 / **0** |
| Hero `--hero-item wing=Item/SparkleCape.bmd` (`0x2384`), every 10 | hero | 70 / **3** | 74 / **0** |
| GL `mu-world` 640×400 crowd, 41 frames, every 5 | players | 414 / **9** | 417 / **5** (all bow `0x1316`'s `0x7ffd`/0x1b) |
| | ground | 144 / **4** | 146 / **0** |
| Player-model actors | actors | wired like players (key = actor index × 16 + slot); no installed actor wears these wings | — |

Every OBJECT-owned refusal is gone. The counts after differ by a few requests because each created `0x810a`/0x11
draws eight `rand()` (crowd: 133 → 141), which moves later gates. Refusals that remain are not OBJECT-owned and
have no native kind: `0x7ffd`/0x1b (bow `0x1316`), `0x7f66`/5 (`0x230c`, `0x2496`), `0x8180`/5 (`0x23ef`,
`0x2400`, `0x2405`), plus the two joint kinds above.

## Client semantics (scope 2, verified)

| Kind | Create (`0x015ae7b0`) | Move (`0x01616c80`) | Render (`0x0159123f`) |
|---|---|---|---|
| `0x810a`/0x11 | `0x015b25a3`: initial LifeTime 30 (+0x4c), LifeTime 30; Scale `0x011ff622(0.5, 1, 100)` × argument, kept at +0x1c; alpha 1; rotation `0x011ff622(0, 360, 1)`; position += `0x011ff622(−10, 10, 1)` per axis; velocity `0x011ff622(−15, 15, 1)` × 0.2 per axis | `0x0161b6ba`: Scale −= initial Scale / 30; alpha −= 1 / 30; the common MovePosition turns the velocity by the request's angle | `0x0159faca`: light × alpha |
| `0x81cf`/0 | `0x0160baa3`: LifeTime 20, initial 20, initial Scale = argument, Scale 0, alpha 1 | `0x0168418b`: NULL owner (+0x50) → live 0; else Scale += initial Scale / 20; LifeTime < 10 → alpha −= 1 / 10 | `0x015a5eec`: light × alpha |

- **What they read from the OBJECT owner each frame: only `+0x158`.** The common blocks of create
  (`0x015aeb5e..0x015aebd6`) and MoveParticles (`0x01616fee..0x01617071`) copy its x, y into the record's `+0x54`
  with z = RequestTerrainHeight. A Unicorn read hook over the owner records exactly `+0x158..+0x163` for both
  kinds' create and move. The angle `+0x164`, bones `+0x318`, scale `+0x74` and the live/visible bytes are never
  read; `+0x54` is not read afterwards; the particles do not follow the owner.
- **Retirement:** by LifeTime at MoveParticles' loop head (20 and 30 steps). `0x81cf`/0 also ends when the owner
  word is NULL. The client's owner is a pointer into the character array (the link OBJECT `PART + 0x24`) or the
  ground-item array, so it is not NULL while the wearer or drop exists, and it does not retire the particle when
  the wearer leaves.
- **Angle argument:** both requests pass OBJECT `+0x164` (op 12). RenderLinkItem `0x012bd910` stores 0.0 there at
  eleven sites before its RenderObjDraw call `0x012c6a83` (type `0x44f`'s z = WorldTime is the only other store) and
  reaches it only through the accessors `0x00cfc922`/`0x00cfc94a`, so worn wings pass (0, 0, 0). A ground drop
  passes its own angle.
- `0x81cf` is a startup bitmap: `0x018249a3` in `0x0182049e`, `Effect\magic_ground12.JPG`, GL_LINEAR, GL_CLAMP.

## Native (scope 3)

- `reconstructed/particles/item_owned_kinds.inc` (new): both kinds; `particles.c` gets one include and the
  supported/create/move/render hooks.
- `native/core/mu_particles.{c,h}`: 256 item-owner slots. `mu_world_particles_item_owner(key, position)` returns
  `0x40000000 + (generation << 8) + slot`; `_refresh` updates a key's `+0x158`. `fx_object` resolves the index to a
  live, visible object at that position, or to none when the generation no longer matches. A slot is reused only
  after 64 unrefreshed steps (both kinds live at most 30), with generation + 1. A full table returns −1 (the
  request is refused and counted in `item_owners_full`). Bitmap `0x81cf` gets a world slot (77, before Fire06 so
  016's mutant anchor still matches once).
- `native/core/mu_renderchar.{c,h}` (the minimal routing hook): `mu_renderchar_env.item_owner` (key, 0 = none) and
  `.item_angle` (OBJECT `+0x164`). `owner_emit` sends op 25 to `mu_world_particles_create_owned` with the item's
  owner index; without a key it refuses as before. The pre-draw host takes `item_angle`.
- `native/world/world_rt.c` `world_rt_item_pre(..., object)`: the key is `(caller + 1) << 24 | object` (hero slot,
  player or actor index × 16 + slot, ground pool index), refreshed with the model origin (the OBJECT position, part
  19) on every draw. `parts/{hero,players,actors,items}.c` pass the identity; `parts/items.c` passes the drop's
  angle through `mu_world_item_draw.index`/`.angle` (`native/core/mu_items.{c,h}`).
- Still refused, and why: `mu-render character` (the offline viewer has no item OBJECT registry, so no key); a full
  slot table; every non-owned request whose kind no pool reconstructs (list above).

**Scope 4 (owner angle of the armour subtype-7 particles):** nothing to change. RENDER-ITEMS-002Q added
`mu_rc_owner_fx.angle`; the consumer passes `fx->angle` and `mu-render character` sets the owner angle from the
character's angles (`native/tools/mu_render_world.c`). Part 16's "passes zero" note predates it. The world parts do
not run the armour owner programs (they have no OBJECT bone host), which is outside this lane.

## Checks

Env (all heavy steps `nice -n 10`, `make -j4`, `--jobs 2`):

```sh
export MU_RECOVERY_INTEGRATION=1
export MU_GAME_ROOT="$HOME/Library/Application Support/MuTheMatrix/prefix/drive_c/MuTheMatrix"
export MU_SECTION3="$HOME/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin"
export MU_PATH_DIRECTIONS="$MU_SECTION3"
export MU_EVIDENCE_DIR="$HOME/Documents/MTM/mu-the-matrix-native/evidence"
export MU_OBJECTS_PLAIN_DIR="$HOME/Documents/MTM/mu-mac-tools/native/scratch/objects/live/plain"
export MU_SNAPSHOT_DIR="$HOME/Documents/MTM/mu-mac-tools/native/scratch"
export MU_LANG_DIR="$MU_SNAPSHOT_DIR/lang"
export MU_LANG3_SNAPSHOT="$MU_LANG_DIR/live/lang3.bin"
export MU_VALIDATOR_CACHE="$HOME/Documents/MTM/mu-mac-tools/native/cache/validators"
```

| Check | Result | Wall |
|---|---|---:|
| Build `make -j4` (final code; after the `0c3c2777` merge) | pass | 11.5 s; 16.1 s |
| `validate_render_effects20 --cases 1000` (full count, no mutants) | **6,420 cases, 0 mismatches**: item_create 2,000, item_move 2,000, item_render 2,000, owner_reads 400, link_angle 19, bitmap 1 | 3.9 s |
| `validate_render_effects20` registry row with mutants (`run_validators.py --cache --only`, once) | 148 cases, 0 mismatches; **14/14 mutants caught**, none stopped, all compiled, every anchor once (checked before the run) | 10.0 s |
| `run_validators.py --private --no-mutants --cache --affected origin/main --jobs 2` at `59415e20` | **48/48 pass**, 267,423 cases (below) | 485.5 s |
| `validate_renderchar` (6b: `mu_renderchar.c` changed; the selector pruned it) at `59415e20` | pass, 1,706 cases | 55.4 s |
| `run_test_suites.py --affected origin/main` (`MU_RECOVERY_INTEGRATION=0`, 2 jobs) | 9 suites, 1,543 tests, 1,303 passed, 240 skipped, 0 failures | 314.0 s (+77 s selection) |
| Private modules from the root: `test_render_effects20` (new), `test_native_world_predraw`, `test_native_particles`, `test_native_hero_items`, `test_native_players`, `test_native_items`, `test_native_joints`, `test_native_renderchar`, `test_render_effects17`, `test_render_effects16` | 67 tests OK, 0 skipped | 245.9 s |
| `tests.test_validators_manifest` | 17 tests OK | 0.6 s |
| After the `0c3c2777` merge (#337 brought `native/core/mu_objects_*.c`, `reconstructed/objects`): `--affected-since 59415e20`, no mutants, at `23f9ea60` | **59/59 pass**, 1,007,750 cases (terrain 405 s, the worlds/after/slots rows, render_effects16..19, item_callers, worlds_raklion, ...) | 834.1 s |
| After the merge: `test_render_effects20`, `test_native_world_predraw`, `test_native_particles` | 14 tests OK | 20.9 s |
| `scripts/audit_repository.py` | 2,068 staged files, 0 rejected | 23.2 s |

Rows at `59415e20` (cases / s): worlds_slots3 36,000 / 39.8, worlds_slots2 33,000 / 37.2, worlds_after2 32,216 /
33.2, worlds_slots 18,999 / 21.3, meshdraw 14,619 / 75.8, worlds_after 13,424 / 16.8, app_polish4 10,485 / 35.3,
worlds_after3 10,212 / 12.1, worlds_after4 9,181 / 17.2, render_worlds_a 9,000 / 16.2, icarus_c2 8,400 / 24.5,
worlds_after6 7,300 / 64.7, movement 6,614 / 69.6, item_callers 6,013 / 1.3, worlds_after5 6,000 / 14.3,
audio_callers 5,528 / 6.0, worlds_e 4,840 / 18.6, worlds_fog 4,044 / 7.9, worlds_121 4,000 / 5.8, worlds_g3 4,000 /
5.5, audio_items 3,000 / 4.5, audio_domains 2,544 / 26.7, render_effects4 1,920 / 8.2, item_effects 1,500 / 2.1,
worlds_l 1,260 / 1.5, render_effects5 1,190 / 4.5, worlds_m 1,080 / 1.8, app_polish2 1,028 / 3.6, render_effects6
1,000 / 1.6, model_edge 954 / 144.0, world_particle_consumers 900 / 1.7, app_polish1 752 / 22.6, render_effects3
720 / 1.4, render_effects 660 / 1.3, render_effects14 660 / 1.5, render_effects17 618 / 8.2, render_effects7 596 /
1.8, render_effects18 540 / 1.5, render_effects15 509 / 1.3, render_effects16 424 / 3.5, particles 407 / 1.6,
render_effects9 304 / 1.0, render_effects19 260 / 0.8, render_effects13 180 / 0.6, render_effects11 176 / 0.4,
render_effects10 154 / 0.5, render_effects20 148 / 0.3, render_effects12 64 / 0.4. Meshdraw, model_edge and
movement are the selector's symbol-level fallback rows. A first run at `f58b83f8` found
`validate_render_effects16`'s `fire06_slot` anchor matching twice after the new slot went between Fire06 and the
rain textures; the slot moved before Fire06 (`59415e20`) and the 48 rows reran.

Mutants (detections of 120): admit_17 120, create17_scale 115, create17_jitter 120, create17_velocity 120,
create17_life 120, create0_scale 120, create0_keep 78, move0_owner 75, move0_grow 29, move0_half 10, move0_fade 6,
move17_shrink 92, move17_fade 89, render_alpha 69.

## Byte identity and renders

- One default-draw sweep (`fidelity_tour.py render`, no draw_all), base `f2370871`: October 22 tour 28/28 PNG,
  28/28 OBJECT/light dumps, 14/14 report rows; DATA-ACQ-002 64/64, 64/64, 32/32. No 0x2384/0x2385 wearer is in view
  in any tour (the heroes wear class parts). The report rows are identical once paths are normalised, except the
  particle summary's `bitmaps` array, which gains the `0x81cf` slot (loaded: 1). Wall before/after: October 22
  23.7 / 21.9 s, DATA-ACQ-002 50.1 / 50.4 s.
- Crop (before | after | 4× difference, GL `mu-world` 640×400, frame 30, 2× nearest):
  `~/Documents/MTM/mu-mac-tools/native/renders/render-effects-020/crowd-0x2384-owned-before-after.png`: Seraph's
  cloak and the dropped Cloak of Brilliance gain the pin_star03 sparks and the magic_ground12 ring. An offline
  native render, not a comparison with the original client.

## Limits

- A reused slot resolves to no object, where the client would read the reused memory; no item-owned particle lives
  long enough to meet it. A wearer that leaves keeps its last position, as the client's slot memory does.
- `mu-render character` keeps refusing OBJECT-owned particles (no registry in the offline viewer).
- The link OBJECT's `+0x164` before RenderLinkItem's first store and stores outside RenderLinkItem were not traced.
- Ground drops now pass their angle to every pre-draw program that reads op 12 (`0x1316`, `0x22ec`, `0x230c`,
  `0x23ef`, `0x2400`, `0x2405`, `0x248f`, `0x2496`, `0x2384`, `0x2385`); in the scenes only the two cloaks are
  dropped.
- Player-model actors are wired but no installed actor wears these wings; inventory/UI items stay unwired.

## Next

- Kinds for the non-owned requests still refused: `0x7ffd`/0x1b (bow `0x1316`), `0x7f66`/5 (`0x230c`, `0x2496`),
  `0x8180`/5 (`0x23ef`, `0x2400`, `0x2405`).
- The armour owner programs in the world (an OBJECT bone host for players and the hero).
- An item OBJECT registry for `mu-render character`, if the offline viewer should show these particles.

## Release

Steward validators: the 48 rows of `--affected origin/main` (ran at `59415e20`, no mutants; `validate_render_effects20` with mutants once there) plus `validate_renderchar` (6b), and the 59 rows of `--affected-since 59415e20` after the #337 merge (ran at `23f9ea60`); the PR body lists them. Mutants needed again: none. Env as above. Cleanup removes
`mu-mac-tools/native/scratch/render-effects-020/` (scenes, tours, census tool), the base worktree and the build
directories; the crop is the only kept artifact. The worktree stays until the steward merges. No new input needs to
be kept.
