# RENDER-EFFECTS-021

The item programs' last particle requests without a native kind, and the armour owner programs in the world.
[Finding: client-render-items.md part 23](../research/client-render-items.md#part-23-pre-draw-particles-without-an-owner-and-armour-owner-programs-in-the-world-render-effects-021).

Branch/worktree `claude/render-effects-021` (Claude Opus 5.5), from `claude/render-effects-020` `ca941c4b` (#339).
Merged main `035c1964` (#338 APP-POLISH-008) as `85452359` and `9b2807fd` (#339, #340 RENDER-WORLDS-KARUTAN) as
`42f2860e`. "Before" numbers come once from a detached base worktree at `ca941c4b`. Validator selections use a
local base `ad99fbae` (= `ca941c4b` merged with `035c1964`, not pushed): `git diff ad99fbae..85452359` is exactly
this lane's 10 files. No live client, launcher, network or hosted workflow. No full gate in the lane (2026-11-04
test budget). The `tools/python`, `evidence` and `input` links come from the main checkout and are never staged.

## Scope 1: the three particle kinds

Census of the 83 programs (static, every op): the only particle requests left without a kind were
`0x7ffd`/0x1b (bow `0x1316`), `0x7f66`/5 (`0x230c`, `0x2496`) and `0x8180`/5 (`0x23ef`, `0x2400`, `0x2405`), all
without an owner. Sprites go to the sprite pool, OBJECT-owned particles to part 22's slots; the joint kinds
`0x7f7c`/0xe and `0x7fd3`/4 stay refused (RENDER-ITEMS-002T).

| Kind | Create (`0x015ae7b0`) | Move (`0x01616c80`) | Render (`0x0159123f`) |
|---|---|---|---|
| Clud64 `0x7ffd`/0x1b | `0x015c304a`: initial LifeTime 15, LifeTime 15, rotation `rand() % 360`, alpha 1, velocity `0x011ff622(-0.5, 0.5, 1)` × 3 (always 0) | `0x0163274d`: alpha = LifeTime / 15, Scale += 0.04 | `0x0159504f`: light × alpha |
| Shiny01 `0x7f66`/5 | `0x015e5c73` head (LifeTime 18, angle x 45), `0x015e60e5`: LifeTime `rand() % 10 + 10`, Scale `(rand() % 10)·0.02 + scale`, x/y `+= rand() % 10 - 5`, gravity `-(rand() % 10)·0.3` | `0x01658bd3`: rotation += 10, z += gravity, light /= 1.02, Scale -= 0.01 | default sprite `0x015ae2bf` |
| shiny06 `0x8180`/5 | table `0x016167a0`[5] → switch end `0x015e93ab`: the common block (LifeTime 2) | `0x0168f700`[5] → `0x0165c194`: nothing | `0x015ae50f`[5] → `0x0159a5a6`: bind + blend state, no sprite |

Native: `reconstructed/particles/item_predraw_kinds.inc` (new), included by `particles.c` with
supported/create/move/render hooks (shiny06/5 returns "no sprite"). No bitmap slot was added: Clud64 and Shiny01
already have one, and shiny06/5 draws nothing.

## Scope 2: armour owner programs in the world (done)

The 38 armour types `0x1bc3..0x1c78` and the five helms `0x19f4`, `0x19fa`, `0x1a00`, `0x1a1f`, `0x1a78`
(`mu_rc_item_owner_fx`) now run their RENDER-ITEMS-002Q programs for players, the hero and player-model actors.
- Client: `0x012b678d(out, OBJECT, bone, local)` (thiscall on the part model) reads OBJECT `+0x318 + 0x30·bone`
  through `0x0129f12c` (when the OBJECT's model, via `+0x5c`, has the bone and `+0x318` is set; else BoneTransform
  `0x06fce398`), × part model `+0x74`, + OBJECT `+0x158`; nothing when the bone is not below the part model's
  `+0x22`. The particles take OBJECT `+0x164`.
- Native host adapter `world_rt_part_owner` (`native/world/world_rt.c`): the character's `player_bones` (posed
  Player.bmd) and bone count, `params.angles`. The part model's body scale and origin are already the character's
  (`slot_params`). `world_rt_part_owner_done` adds the counts; the report gains an `item_owner_fx` line only when a
  program ran.
- Hooks: `native/world/parts/{players,hero,actors}.c` draw body parts with `mu_renderchar_draw_item_owner` (NULL
  owner = the previous call). No `native/core` or renderchar change; the joint pool is untouched.
- Only owner-program types get the owner, so the rank-5 owner block (RENDER-EFFECTS-005: bones 35/26 plus level-9
  overlay passes) is unchanged in the world. None of the 43 types is rank-5.

## Census of refusals (before `ca941c4b` → after)

Lorencia 128,124; `mu-walk` soft 320×240 or GL `mu-world` 640×400; pre_effects / refused.

| Scene | Before | After |
|---|---|---|
| CALLERS-001 crowd fixture, 60 frames: players / ground | 93 / 0, 18 / 0 | identical |
| Crowd, a frame every 10 | 325 / 0, 113 / 0 | identical |
| Crowd GL, 41 frames every 5 | players 417 / **5**, ground 146 / 0 | 423 / **0**, 148 / 0 |
| Archer only (bow `0x1316`), GL, every frame, 61 frames | 854 / **17** | 876 / **0** |
| Wearers of `0x230c`, `0x2496`, `0x23ef`, `0x2400`, `0x2405`: soft every 10 / GL every 5 / test fixture | 483 / **10**, 621 / **12**, 138 / **3** | 487 / **0**, 634 / **0**, 142 / **0** |
| Shipped Lorencia demo players (#338 outfits): soft every 10 / GL every 5 | 343 / 0, 441 / 0 | identical (none of these types, no owner-program armour) |
| Armour wearers `0x1bc3`, `0x1bc4`, `0x1bde`, `0x1c41`, `0x1c78`: soft every 10 / GL every 5 / test fixture | no program ran | owner effects 144 / 190 / 41, **0 refused** |
| Hero `armor=Item/ArmorMale135.bmd` (`0x1bc3`): soft every 10 / test fixture | no program ran | 68 / 20, **0 refused** |

Crops (before | after | 4× difference, nearest), local only in
`~/Documents/MTM/mu-mac-tools/native/renders/render-effects-021/`:
`scope1-crowd-bow-0x1316-clud64-before-after.png` (the Archer's Clud64 puff at the bow, frame 35, 4×),
`scope1-wings-shiny01-before-after.png` (a Shiny01 glint, frame 30, 3×),
`scope2-armour-owner-fx-before-after.png` (the 0x7f7a/0x8109 sprites and 0x810a particles on four wearers,
frame 30, 2×). These are offline native renders, not compared with the original client.

## Checks

Env: `. ~/Documents/MTM/mu-mac-tools/native/private-env.sh`, plus `MU_LANG_DIR=$MU_SNAPSHOT_DIR/lang` and
`MU_LANG3_SNAPSHOT=$MU_LANG_DIR/live/lang3.bin`. All heavy steps `nice -n 10`, `make -j4`, `--jobs 2`.

| Check | Result | Wall |
|---|---|---:|
| Build `make -j4` (+ `build/mu-world`) | pass, no warnings; after the `42f2860e` merge too | 11.6 s; 15 s |
| `validate_render_effects21 --cases 1000` (full count, no mutants) | **13,007 cases, 0 mismatches**: pre_create 3,000, pre_move 3,000, pre_render 3,000, tables 7, owner_host 4,000 (owner bones 1,753; BoneTransform fallback 526; unwritten 1,721) | 8 s |
| `validate_render_effects21` registry row with mutants (`run_validators.py --private --cache --only`, once, at `85452359`) | 267 cases, 0 mismatches; **19/19 mutants caught**, none stopped, all compiled, every anchor once | 12.9 s |
| `run_validators.py --private --no-mutants --cache --affected-since ad99fbae --jobs 2` at `85452359` | **48/48 pass**, 259,177 cases (below) | 357 s (+58 s selection) |
| After the `9b2807fd` merge: `--affected-since 85452359`, no mutants, at `42f2860e` | **59/59 pass**, 996,661 cases (below) | 613 s |
| `run_test_suites.py --affected-since ad99fbae` (`MU_RECOVERY_INTEGRATION=0`, 2 jobs) | 9 suites, 1,549 tests, 1,307 passed, 242 skipped, 0 failures | 272.9 s (+45 s selection) |
| Private modules from the root: `test_render_effects21` (new), `test_native_world_predraw`, `test_native_particles`, `test_native_players`, `test_native_hero_items`, `test_app_polish8`, `test_render_effects20`, `test_render_effects17`, `test_native_renderchar`, `test_world_parts` | 84 tests OK, 0 skipped | 256 s |
| After the merge: `test_render_effects21`, `test_native_world_predraw`, `test_app_polish8` | 21 tests OK | 29 s |
| `tests.test_validators_manifest` | 17 tests OK (before and after the merge) | 0.7 s |
| `scripts/audit_repository.py` (with the docs staged) | 2,080 staged files, 0 rejected | 23 s |
| `tests.test_repository_policy` | 9 tests OK | 0.5 s |

Rows at `85452359` (cases / s): worlds_slots3 36,000 / 28.0, worlds_slots2 33,000 / 30.8, worlds_after2 32,216 /
17.8, worlds_slots 18,999 / 11.8, meshdraw 14,619 / 79.6, worlds_after 13,424 / 8.4, worlds_after3 10,212 / 5.2,
worlds_after4 9,181 / 9.1, render_worlds_a 9,000 / 12.0, icarus_c2 8,400 / 14.0, worlds_after6 7,300 / 48.0,
movement 6,614 / 55.3, item_callers 6,013 / 1.3, worlds_after5 6,000 / 6.9, audio_callers 5,528 / 4.6, worlds_e
4,840 / 12.8, worlds_fog 4,044 / 4.9, worlds_121 4,000 / 3.1, worlds_g3 4,000 / 3.0, audio_items 3,000 / 3.4,
worlds_raklion 3,000 / 2.4, audio_domains 2,544 / 20.3, render_effects4 1,920 / 4.4, item_effects 1,500 / 2.5,
worlds_l 1,260 / 0.8, render_effects5 1,190 / 3.5, worlds_m 1,080 / 0.8, render_effects6 1,000 / 0.9, model_edge
954 / 147.7, world_particle_consumers 900 / 0.6, app_polish1 752 / 16.1, render_effects3 720 / 0.7, render_effects
660 / 1.6, render_effects14 660 / 0.9, render_effects17 618 / 5.8, render_effects7 596 / 1.1, render_effects18 540 /
0.9, render_effects15 509 / 0.6, render_effects16 424 / 2.5, particles 407 / 0.7, render_effects9 304 / 0.7,
render_effects21 267 / 0.2, render_effects19 260 / 0.5, render_effects13 180 / 0.4, render_effects11 176 / 0.2,
render_effects10 154 / 0.3, render_effects20 148 / 0.2, render_effects12 64 / 0.2. `validate_movement` is the
symbol-level fallback row. Not selected (build a changed library, use no changed symbol): the 29 rows the selector
lists (renderchar, item_*, terrain, path, ...); this lane changes no `native/core` file and no renderchar file.

Rows at `42f2860e` (the merge brought #340's `native/core/mu_objects_runtime.c` and `reconstructed/objects`):
terrain 583,500 / 300.6, worlds_slots3 36,000 / 46.9, worlds_slots2 33,000 / 42.2, worlds_after2 32,216 / 32.8,
worlds_s3 22,000 / 11.8, worlds_slots 18,999 / 30.1, meshdraw 14,619 / 51.4, worlds_after 13,424 / 21.0, worlds_n
13,000 / 5.2, worlds_r 12,000 / 4.9, worlds_q 11,000 / 7.8, worlds_s 11,000 / 6.3, worlds_after3 10,212 / 7.0,
worlds_p 10,000 / 5.0, worlds_s2 10,000 / 5.4, worlds_after4 9,181 / 24.3, render_worlds_a 9,000 / 19.4, worlds_r2
9,000 / 4.5, icarus_c2 8,400 / 22.0, worlds_after6 7,300 / 70.2, movement 6,614 / 62.0, item_callers 6,013 / 1.1,
worlds_after5 6,000 / 14.0, worlds_g/h/i/j/k 6,000 each / 2.4-2.9, worlds_p2 6,000 / 3.3, world_tile_folder 5,700 /
24.2, audio_callers 5,528 / 4.8, icarus 5,240 / 24.9, worlds_e 4,840 / 20.5, worlds_121 4,000 / 4.0, worlds_b 4,000 /
2.2, worlds_g3 4,000 / 4.8, worlds_q2 4,000 / 4.6, audio_items 3,000 / 2.8, worlds_karutan 3,000 / 2.2,
worlds_raklion 3,000 / 3.1, worlds_g2 2,657 / 4.8, audio_domains 2,544 / 29.6, worlds_d 2,400 / 2.7,
terrain_remaining 2,147 / 3.4, object_render 1,984 / 2.5, worlds_f 1,818 / 0.4, model_light 1,433 / 4.5,
charsel_world 1,200 / 4.9, login_world 1,200 / 5.0, model_edge 954 / 98.2, app_polish1 752 / 20.3,
render_effects17 618 / 7.2, render_effects18 540 / 1.0, render_effects16 424 / 2.7, render_effects19 400 / 0.7,
world_light_name 304 / 0.3, map_effects 300 / 2.0, world_fidelity 200 / 0.1, worlds_o (no case count) / 3.9.

Mutants (detections of 120): admit_clud 120, admit_shiny06 120, clud_life 120, clud_rotation 59, clud_alpha 120,
clud_velocity 106, shiny_angle 120, shiny_life 120, shiny_scale 120, shiny_jitter 120, shiny_gravity 120,
clud_fade 85, clud_grow 96, shiny_spin 96, shiny_rise 76, shiny_dim 96, shiny_shrink 96, render_clud_alpha 76,
render_shiny06_draws 98.

6b: changed shared symbols are `mu_pt_kind_supported`/create/move/render (new kinds only) and the `mu_world_rt`
struct (`item_owner_fx`). Every module and host that names the new kinds, the world parts or the item callers ran
above. The `absent` kind lists of `worlds_l_host.c`, `worlds_m_host.c`, `effects16/17/20_host.c` do not list
these kinds.

## Byte identity

One default-draw sweep (`fidelity_tour.py render`, no draw_all), base `ca941c4b`, after `85452359`:
- October 22 tour: 28/28 PNG, 28/28 OBJECT/light dumps, 14/14 reports (paths normalised);
- DATA-ACQ-002: 64/64, 64/64, 32/32.

No wearer is in view: the tours have no players file and their heroes wear class parts. Wall before/after:
October 22 21 / 15 s, DATA-ACQ-002 38 / 41 s.

## Limits

- `0x8180`/5 draws nothing, in the client too. Native also skips its bind and blend state (shiny06 has no world
  slot); in the client the next record's render resets both.
- The world's posed skeleton is taken as the client's `+0x318`, as for the rank-5 bones and the `0x389c`/`0x389d`
  link effects. This lane verifies the transform and the bone-domain rule, not the pose.
- The five helms run through the same hook, but no scene wears them; player-model actors are wired, but no
  installed actor wears these armours.
- The rank-5 owner block still runs only in `mu-render character`.
- The joint kinds `0x7f7c`/0xe and `0x7fd3`/4 stay refused (RENDER-ITEMS-002T). The OBJECT-owned particles stay
  refused in `mu-render character` (part 22).

## Next

- The rank-5 owner block (`0x84e2` particles, `0x7fdd` sprite, `0x83de`/4, level-9 overlay passes) in the world,
  through the same hook.
- A demo outfit wearing an owner-program armour, if the offline demo should show it.
- RENDER-ITEMS-002T's joint kinds.

## Release

Steward validators: the 48 rows of `--affected-since ad99fbae` (ran at `85452359`, no mutants;
`validate_render_effects21` with mutants once there) and the 59 rows of `--affected-since 85452359` after the
`9b2807fd` merge (ran at `42f2860e`, no mutants): 80 distinct rows, listed in the PR body. Mutants needed again:
none. Env as above. Cleanup removes `mu-mac-tools/native/scratch/render-effects-021/`, the base worktree
`worktrees/rfx21-before` and the build directories. The three crops are the only kept artifacts; no new input
needs to be kept. The worktree stays until the steward merges.
