# RENDER-ITEMS-002U

Branched from `claude/render-items-002t` (`53b9f7e7`, PR #341); merged main `138b756e` (#338 APP-POLISH-008, #339
RENDER-EFFECTS-020, #340 RENDER-WORLDS-KARUTAN, #341 RENDER-ITEMS-002T; clean), `a7f7b247` (#342 RENDER-EFFECTS-021, #343
INVENTORY-FX; both struct fields kept) and `97b282e6` (#344 RENDER-ITEMS-CLOAK, #345, #346; docs only: main's parts
23-25 taken as they are, this lane's finding is part 26). No conflict markers. Branch/worktree
`claude/render-items-002u` (Claude Opus 5.5). No live client, launcher, network or hosted workflow. No full gate in the
lane (2026-11-04 test budget).

Scope: 002T's "Next groups" 1, 2 and 5 (joint kinds, the rendered-frame counter, world callers). Group 3 (draw fits of
read programs) and group 4 (rank-5 strlen parts) were not attempted.
Findings: [client-render-items.md part 26](../research/client-render-items.md#part-26-the-rendered-frame-counter-in-body-draws-the-wing-joints-and-the-world-callers-render-items-002u),
[client-joints.md section 12](../research/client-joints.md#12-the-wing-streaks-0x7f7c0xe-and-0x7fd34-render-items-002u).

## Result

- **Bodies 1,363 → 1,364 of 1,674** (+`0x0f2a`), **310 remain**. Survey: 798 shapes, complete 585 → 586; both TSVs
  flip exactly `0x0f2a`.
- **51 admitted bodies were right only at frame 0.** The client's streams at counter 0 against 7/13/22 (then 1 and
  0x80000000, 16 states per type) differ for 58 survey types; 51 were admitted (swords `0x0b66`..`0x0b73`, maces
  `0x0f2f`/`0x0f30`, `0x1109`/`0x110a`, bows `0x132b`/`0x132c`/`0x132e`, staffs `0x1560`..`0x158e`, shields
  `0x1739`..`0x175d`): their mesh u/v follow `[0x0bdc5ebc]` (scrolls `((counter + 1) % 60) / 60`, a 4 × 4 atlas). Every
  probe and validator held the counter at 0. They are regenerated with counter chains and checked with a moving counter.
- **Joints 0/40 → 40/40 drawn.** `0x7f7c`/0xe (`0x01544f3d`, move `0x0156d9ef`) and `0x7fd3`/4 (`0x01540b34`, no move
  case `0x01568ebe`) are in the joint pool: ten-tail streaks toward the target argument, LifeTime 0 (drawn once, twenty
  per wing per frame). Neither reads its target OBJECT, so the native target -1 draws the client's quads.
- **Frame counter: yes.** The client increments it in the frame driver after the logic steps, before the scene render
  (`0x01852501`). Natively `mu_world_rt.rendered_frames` does the same in `mu_world_rt_frame`; `world_rt_item_pre`
  hands it to every item it is called for. `mu-render character --frame-counter N` for the viewer.
- **World callers:** `world_rt_item_pre`'s condition now includes the post-draw types (`0x2713`'s program gets the item
  pose in the world), plus the counter line at its top.

## Causes and addresses

| What | Address | Cause / reading |
|---|---|---|
| Counter increment | `0x01852501..0x01852507` | frame driver `0x01851d39`: logic steps, glClear, GetTickCount, `++[0x0bdc5ebc]`, scene render; the only write of 225 references |
| Counter reads in body draws | `0x0172dd0c`..`0x01737116` (36 sites, RenderPartObjectBody), `0x01769c75`..`0x0176c12a` (maces) | `(counter + 1) % 60` unsigned (`xor edx, edx; div`), unsigned to binary64 (`shr 31; addsd [r*8 + 0x01bd3050]`), × 1/60, sometimes negated after the vec3 setter `0x00cfcead`; `0x1109`: (counter + 1) % 16 atlas; `0x0f2a`: (counter % 32) / 2 atlas |
| `0x7f7c`/0xe create | `0x01544f3d` (prologue `0x01543f00`) | step = (target argument − position) / 10, 9 tail shifts, head = +0x58 (not set from the argument when a target object is given, `0x0153b37f`) |
| `0x7f7c`/0xe move | `0x0156d391` → `0x0156d9ef` | MoveHumming(+0x58, 25) returns the distance; jitter (rand % 1024 − 512) / width; stops when 1.5 × velocity > distance (width 50: particles `0x7f2b`, `0x7f5a`) |
| `0x7fd3`/4 | `0x01540b34`, move `0x01568ebe` | as `0x7f7c`/0xe with render type 1; no move case |

## Effects routed vs refused (natively)

| Request | Before | After |
|---|---|---|
| CreateJoint `0x7f7c`/0xe 20, `0x7fd3`/4 20 (wings `0x22ec`, `0x248f`) | routed, refused (0/40) | created and drawn (40/40; 360 quads per wing per frame on a 64-bone skeleton) |
| `0x0f20`'s particles behind `counter % 3`/`% 5` (world) | refused (no counter) | run on the client's frames; refused for their kinds (`0x855d`/1, `0x84d1`/1 not in the pool) |
| `0x2713`'s sprites in the world | refused (no pose) | routed (item pose) |
| #339's combined particle rule (owner key, argument 8) | — | applies to particles only; joints unaffected |

## Checks

Env: `. ~/Documents/MTM/mu-mac-tools/native/private-env.sh` (MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT, MU_EVIDENCE_DIR,
MU_SNAPSHOT_DIR, MU_LANG_DIR, MU_LANG3_SNAPSHOT, MU_VALIDATOR_CACHE, ...), `MU_SECTION3="$HOME/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin"`.
All heavy steps `nice -n 10`.

| Check | Cases / result | Wall time |
|---|---|---:|
| Joint create/move/render, the two new kinds alone (scratch, iterating) | 3,000 cases, 0 mismatches (39 particle runs in move) | 9 s |
| `validate_joints --cases 3000 --mutations` (at `6dd45042`; joints unchanged since) | 9,000 cases, 0 mismatches; **38/38 compiled mutants** (16 new, anchors exactly once: three earlier ones lengthened) + 9 negative controls | 228 s |
| Counter scan, client vs client (scratch) | 1,691 types × 4 states × counters 7/13/22: 58 types differ; × 12 states × 1/0x80000000: 56, no new type | 98 s + 234 s |
| Body-table generation (`gen_item_bodies`, three runs: scalar limit, then compact rows) | 1,344 → 1,345 rows (`0x0f2a`); 51 rows gain counter chains | 823 s / ~800 s / ~800 s |
| `validate_item_predraw --mutations` (at `6dd45042`) | **32,372 comparisons, 0 mismatches**: bodies 13,140, hidden 1,168, frame 15,184 (52 types × 292, 6,408 counter values), predraw 2,880 (20,466 sprites, 512 particles, 2,222 joints, 11,849 refusals); **44/44 mutants**; both tables reproduce | 286 s |
| C-to-C, main `138b756e` library vs this one (1,691 types × 32 states × rand on/off × counter 0/non-zero) | 216,448 cases; 215,576 identical; counter 0: only `0x0f2a`; counter: exactly the 52 counter types | 5 s |
| C-to-C, wide-row table vs compact-row table (`814ff0d2`) | 216,448/216,448 identical | 5 s |
| Survey export (`classify_item_bodies --tables-dir`) | 1,691 types, 798 shapes; only `0x0f2a` flips in both TSVs; complete 585 → 586 | 69 s |
| Build `nice -n 10 make -j4` | pass | 16 s |
| `run_test_suites.py --affected origin/main` (`MU_RECOVERY_INTEGRATION=0`, 2 jobs, after the `a7f7b247` merge) | 12 suites, 1,650 tests: 2 pinned program counts failed (chains 59 → 61, scalar entries 89 → 110: the counter programs) and one test regex; fixed, `reconstructed/renderchar` 99 tests pass | 328 s + 1 s |
| Private native modules (`test_native_renderchar` with the new wing-joint and frame-counter tests, `test_native_joints`, `test_native_world_predraw`, `test_native_hero_items`, `test_native_item_textures`, `test_inventory_fx`; private-env.sh, from the root, after the merge) | 59 tests, 0 failures | 292 s |
| Portable `reconstructed/joints` (new `test_wing_streaks`), `test_item_predraw` (new `test_frame_counter_body_chains`) | 16 + 13 tests | <1 s |
| Audit | 2,086 staged files, 0 rejected (`item_bodies.h` 486,681 bytes) | 27 s |

### Affected rows, without mutants (`--no-mutants --cache --jobs 2`)

Symbol-level `--list-affected origin/main` after `make -j4`: 62 rows before the `a7f7b247` merge (3 by the symbol fallback:
`validate_meshdraw`, `validate_model_edge`, `validate_movement`; 6 build a changed library without using a changed symbol), 64
after it (+`validate_inventory_fx`, +`validate_render_effects21`, #343/#342 rows that now reach my symbols). 6b/8b reviewed:
`mu_rc_item` (appended `frame`) is mirrored only by `validate_renderchar.CItem` (others import it); `mu_world_rt`
(appended `rendered_frames`) is internal; the joint pool's kind set reaches combat/skill_fx/world rows (all selected).

- `6dd45042` (pre-merge code): 60 rows (all but joints/predraw, which ran with mutants above), 40 min wall: 58 pass;
  `validate_item_scalars`/`validate_item_chains` failed in their table parsers (single-digit op counts; chains now have
  10 ops) and their pinned case counts; parsers fixed, both reran clean with mutants, counts 26,154 → 26,274 and 35,346 →
  35,406 (the counter programs of the regenerated rows).
- `7aa9b04d` (after merging `a7f7b247`): the 33 rows whose inputs the merge changed plus the 2 new rows: 35/35 pass, 169 s.
- `814ff0d2` (final code; the compact table changed `gen_item_bodies.py` and the header text): the 42 rows affected
  since `7aa9b04d`: 42/42 pass, 38 min wall.
- `a8874f91` (after merging main `97b282e6`: #344 RENDER-ITEMS-CLOAK, #345, #346): the selection grows to 65
  (+`validate_item_cloak`); the 20 rows whose inputs that merge changed: 20/20 pass, 6.5 min wall. Private native
  `test_native_renderchar`, `test_native_world_predraw`, `test_native_item_cloak`, `test_native_joints`: 38 tests, 25 s.

| Validator | `6dd45042` | `7aa9b04d` (merge a7f7b247) | `814ff0d2` (final code) | `a8874f91` (merge 97b282e6) |
|---|---:|---:|---:|---:|
| `validate_app_polish1` | 20.1s | 17.3s |  |  |
| `validate_app_polish2` | 4.1s | 3.8s |  |  |
| `validate_app_polish4` | 33.1s | 28.7s |  |  |
| `validate_audio_callers` | 5.7s | 5.0s | 4.6s | 4.5s |
| `validate_audio_combat` | 21.4s |  |  | 29.9s |
| `validate_audio_domains` | 21.9s | 21.4s | 19.9s | 32.1s |
| `validate_audio_items` | 3.8s | 4.2s | 3.1s | 2.3s |
| `validate_fidelity` | 52.7s |  | 48.9s |  |
| `validate_icarus` | 25.9s |  |  |  |
| `validate_icarus_c2` | 18.3s | 15.3s | 13.1s | 19.0s |
| `validate_inventory_fx` |  | 6.2s | 6.1s | 6.0s |
| `validate_item_callers` | 1.2s | 1.1s | 1.1s | 1.2s |
| `validate_item_carry` | 531.8s |  | 644.4s |  |
| `validate_item_chains` | parser fail; fixed: 288.5 s with 17/17 mutants |  | 228.9s |  |
| `validate_item_cloak` |  |  |  | 62.8s |
| `validate_item_clusters` | 447.7s |  | 425.7s |  |
| `validate_item_continuation` | 172.6s |  | 216.3s |  |
| `validate_item_coverage` | 166.7s |  | 253.8s |  |
| `validate_item_derived` | 178.4s |  | 236.2s |  |
| `validate_item_expansion` | 394.4s |  | 330.1s |  |
| `validate_item_gear` | 143.1s |  | 179.1s |  |
| `validate_item_hiddenmesh` | 438.6s |  | 483.4s |  |
| `validate_item_next` | 180.9s |  | 198.9s |  |
| `validate_item_ownerfx` | 137.2s |  | 142.9s |  |
| `validate_item_predraw` | 286 s (32,372 cases, 44/44 mutants) |  | 237.9s |  |
| `validate_item_product` | 44.7s |  | 48.8s |  |
| `validate_item_quality` | 165.2s |  | 215.2s |  |
| `validate_item_ranked` | 127.2s |  | 132.3s |  |
| `validate_item_scalars` | parser fail; fixed: 199.8 s with 11/11 mutants |  | 157.0s |  |
| `validate_item_types` | 39.4s |  | 28.6s |  |
| `validate_item_wings_next` | 180.8s |  | 223.5s |  |
| `validate_joints` | 228 s (3,000/family, 38/38 mutants) |  |  |  |
| `validate_meshdraw` | 67.3s | 50.2s |  | 64.5s |
| `validate_model_edge` | 127.8s | 102.0s |  | 107.0s |
| `validate_model_light` | 5.0s |  |  | 4.3s |
| `validate_movement` | 49.8s | 47.3s | 62.2s | 56.7s |
| `validate_render_effects` | 1.1s | 0.8s |  |  |
| `validate_render_effects10` | 0.4s | 0.3s | 0.3s |  |
| `validate_render_effects11` | 0.3s | 0.2s | 0.2s |  |
| `validate_render_effects12` | 0.3s | 0.2s | 0.2s |  |
| `validate_render_effects13` | 0.6s | 0.4s | 0.4s |  |
| `validate_render_effects14` | 1.5s | 1.0s | 0.9s |  |
| `validate_render_effects15` | 0.9s | 0.6s | 0.6s |  |
| `validate_render_effects16` | 3.7s | 3.7s | 2.3s | 2.3s |
| `validate_render_effects17` | 8.0s | 6.5s | 6.2s | 6.1s |
| `validate_render_effects18` | 1.4s | 0.9s | 0.9s | 0.8s |
| `validate_render_effects19` | 1.1s | 0.7s | 0.7s | 0.6s |
| `validate_render_effects20` | 0.3s | 0.2s | 0.2s |  |
| `validate_render_effects21` |  | 0.4s | 0.2s |  |
| `validate_render_effects3` | 1.0s | 0.7s |  |  |
| `validate_render_effects4` | 5.9s | 5.3s |  |  |
| `validate_render_effects5` | 3.8s | 3.5s | 3.1s |  |
| `validate_render_effects6` | 1.3s | 1.0s |  |  |
| `validate_render_effects7` | 1.5s | 1.5s | 1.1s |  |
| `validate_render_effects9` | 0.9s | 0.7s | 0.7s |  |
| `validate_renderchar` | 43.6s |  | 38.7s |  |
| `validate_skill_fx` | 1.2s |  |  |  |
| `validate_terrain` | 322.2s |  |  | 375.7s |
| `validate_terrain_remaining` | 3.6s |  |  | 3.6s |
| `validate_world_particle_consumers` | 0.9s | 0.6s |  |  |
| `validate_worlds_d` | 3.6s |  |  |  |
| `validate_worlds_f` | 0.4s |  |  | 0.3s |
| `validate_worlds_fog` | 6.8s | 4.4s |  | 4.2s |
| `validate_worlds_l` | 1.1s | 0.9s |  |  |
| `validate_worlds_m` | 0.8s | 0.8s |  |  |

## Release

Steward validators: validate_app_polish1, validate_app_polish2, validate_app_polish4, validate_audio_callers, validate_audio_combat, validate_audio_domains, validate_audio_items, validate_fidelity, validate_icarus, validate_icarus_c2, validate_inventory_fx, validate_item_callers, validate_item_carry, validate_item_chains, validate_item_cloak, validate_item_clusters, validate_item_continuation, validate_item_coverage, validate_item_derived, validate_item_expansion, validate_item_gear, validate_item_hiddenmesh, validate_item_next, validate_item_ownerfx, validate_item_predraw, validate_item_product, validate_item_quality, validate_item_ranked, validate_item_scalars, validate_item_types, validate_item_wings_next, validate_joints, validate_meshdraw, validate_model_edge, validate_model_light, validate_movement, validate_render_effects, validate_render_effects10, validate_render_effects11, validate_render_effects12, validate_render_effects13, validate_render_effects14, validate_render_effects15, validate_render_effects16, validate_render_effects17, validate_render_effects18, validate_render_effects19, validate_render_effects20, validate_render_effects21, validate_render_effects3, validate_render_effects4, validate_render_effects5, validate_render_effects6, validate_render_effects7, validate_render_effects9, validate_renderchar, validate_skill_fx, validate_terrain, validate_terrain_remaining, validate_world_particle_consumers, validate_worlds_d, validate_worlds_f, validate_worlds_fog, validate_worlds_l, validate_worlds_m (ran at `a8874f91`, after the last merge: validate_audio_callers, validate_audio_combat, validate_audio_domains, validate_audio_items, validate_icarus_c2, validate_inventory_fx, validate_item_callers, validate_item_cloak, validate_meshdraw, validate_model_edge, validate_model_light, validate_movement, validate_render_effects16, validate_render_effects17, validate_render_effects18, validate_render_effects19, validate_terrain, validate_terrain_remaining, validate_worlds_f, validate_worlds_fog; the others at `814ff0d2` (final code) or,
with inputs unchanged since, at `7aa9b04d`/`6dd45042`, see the table). No row needs
mutants from the steward: validate_joints (38/38), validate_item_predraw (44/44), validate_item_scalars (11/11) and
validate_item_chains (17/17) ran theirs once in the lane. Env: private-env.sh plus
`MU_SECTION3=$HOME/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin`.

Cleanup removes `mu-mac-tools/native/scratch/render-items-002u/`, the base worktree `worktrees/rii002u-base` and the
build directories. The three crops in `renders/render-items-002u/` are the only kept artifacts (2-8 KB). No new input
needs to be kept; the worktree stays until the steward merges.

## Byte identity and renders

"Before" = main `a7f7b247` (detached worktree `rii002u-base`, removed at cleanup); "after" = this branch at `814ff0d2`
(before the `97b282e6` merge, whose #344 capes belong to wings `0x2382`..`0x2385`/`0x2394`/`0x2395`, none in these
views). Offline native renders, not original-client pixels.

- `mu-render ui inventory`, installed data, `MU_LANG_DIR` set, time 123456, 1024×768: control codes
  0,1,2,3,7,8,4116,135 byte-identical (`7bfbb2cb…`, 1,672 triangles); six counter types (codes 128, 1571, 1093, 2117,
  4691, 5714) byte-identical (the inventory tool keeps the counter at 0). `0x0f2a` (code 1092): level 0 1,532 → 1,685
  triangles, 241 pixels; level 9 1,532 → 8,033 triangles, 634 pixels (its recipe replaces the plain fallback). Crops
  (before | after): `~/Documents/MTM/mu-mac-tools/native/renders/render-items-002u/crop_new0.png`, `crop_new9.png`.
- World scene (test fixture): `mu-walk` Lorencia at 128,124, soft backend 640×480, one demo player wearing wing
  `0x22ec` (`wing=12:6:0`) next to the hero, 31 steps: players' requests 28 created / 40 refused → 68 / 0; frames 0 and
  30 change only inside the wing's box (1,729 / 1,770 pixels: the blue streaks). Crop:
  `renders/render-items-002u/crop_world_22ec.png`.
- One default-draw sweep (`fidelity_tour.py render`, no draw_all): October 22 tour 28/28 PNG, 14/14 OBJECT and 14/14
  light dumps byte-identical; DATA-ACQ-002 64/64 PNG, 32/32 OBJECT, 32/32 light byte-identical; the frame reports
  differ only in their output paths. No counter or wing wearer is in those views. Wall before/after: October 22 16 /
  16 s, DATA-ACQ-002 40 / 40 s.

## Limits

- 310 bodies remain; the six counter types not admitted (`0x0f24`, `0x0f28`, `0x0f29`, `0x0f2b`, `0x0f2c`, `0x1588`)
  fit no probe option yet.
- The native counter starts with the world runtime; the client's counts from process start (login and character
  select included), so only the periods are faithful. The world's inventory window (INVENTORY-FX's caller) reads it;
  `mu-render ui inventory`, the texture survey and `mu-render character` without `--frame-counter` keep 0.
- The streaks' +0x58: with the item's OBJECT the client ends the head at a former joint's +0x58 (record memory);
  natively it is the target argument. It only feeds the releasing MoveJoint (and, at width 50, its particles'
  positions), never a drawn quad.
- The counter scan covers the survey's unselected/no-buff domain, 16 states per type.
- Group 3 (draw fits of read programs) and group 4 (rank-5 strlen parts) not attempted.

## Next groups

1. The six counter types: read the maces' RenderObjDraw effect programs (`0x0f24`, `0x0f28`, `0x0f29`, `0x0f2b`,
   `0x0f2c`) and find `0x1588`'s probe option.
2. Draw fits for read programs: `0x23a8`/`0x23a9`, `0x0f1e`, `0x174a`, `0x2301`/`0x2302`, `0x23f0`/`0x23f2`,
   `0x0b51`/`0x0b52`, the bows `0x1313`/`0x1317`/`0x1319`, part 18's eleven.
3. The 31 rank-5 parts faulting in strlen `0x0195a4e0` and the 54 helper-group-count types.
4. Native particle kinds `0x855d`/1, `0x84d1`/1, `0x810a`/0x25 (RENDER-EFFECTS lanes).
