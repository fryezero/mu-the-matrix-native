# RENDER-EFFECTS-034

**WIP, draft PR, no ready-prs line.** The owner ordered all lanes to finish at 18:07 on 2026-11-15; the
last verification steps after the final main merge were stopped. The consumers themselves are complete
and verified; see the WIP section for what is left.

## WIP (stopped 2026-11-15 18:10 by owner order)

**Done and verified**
- 27 consumer pairs (23 particles, 4 joints) and four bitmap bindings, the per-pair world refusal ledger,
  the grouped verifier, the native fixture host and tests. Everything is committed and pushed.
- Grouped verifier through the registry with all mutants, at `0a4e4ded` (same consumer sources as the
  head): 16,259 checks, 0 mismatches, 116 of 116 mutants detected, 178.6 s.
- Affected private validators, no mutants, cached: 89 of 89 rows at `5b6565ad` (1,366 s), then the delta
  after the batch-120 merge and the second particle group: 118 of 118 rows at `4b5598ee` (3,894 s).
- Portable affected suites (packaging module excluded): 1,888 tests with one stale joint admission
  expectation (fixed); 1,674 tests, 0 failures after the batch-119/120 merges; 1,816 tests with one stale
  particle admission expectation (fixed, suite rerun: 23 tests OK) after the second group.
- Scene refusal counts before/after and the default identity sweep (below) on the tree **before** the
  batch-120 merge and the second group.

**Not verified at the head** (merge `57d22d16` plus this documentation commit) (it adds the merge of main `708798ae`, batches 121/122: UI-WINDOWS-006
and HERO-ITEMS-002, a clean merge that touches no consumer file)
- The validator delta since `4b5598ee` selected 66 rows; 8 had passed and none had failed when it was
  stopped.
- The portable delta for that merge, the reduced private native modules (8d) and the repository audit
  were not run.
- The identity sweep was not repeated on the final tree; its numbers below are from binaries built before
  the batch-120 merge (before `d9783e95…`, after `3f15f0c0…`). The second group only adds pairs that no
  producer on main requests.

**Next step for the agent that resumes** (worktree kept at `~/Documents/MTM/worktrees/render-effects-034`;
scratch and builds were deleted)
1. `nice -n 10 make -j4`, then `run_validators.py --private --no-mutants --cache --affected-since 4b5598ee
   --jobs 2` (66 rows), `run_test_suites.py --affected-since 2ff9660d` without `test_native_app.py`, the
   private modules `test_render_effects34`, `test_native_worlds_inner`, `test_muun_transition`,
   `test_native_particles`, `test_render_effects16/20/22/23/24/26/31/33`, and `scripts/audit_repository.py`.
2. One default identity sweep: before-tree = head with `native/core/mu_particles.c/.h`,
   `native/world/parts/particles.c`, `reconstructed/particles/particles.c/.h` and
   `reconstructed/joints/joints.c` taken from `35ae89fe` and the two `consumer34_*.inc` files removed;
   `make -C native -j4 world` in both trees; record both SHA-256s. Expected: only Swamp of Calmness frame
   24 changes.
3. Fill the three marked sections below, merge main again if it moved, publish the PR and write the
   ready line.

Branch `claude/render-effects-034` starts from RENDER-EFFECTS-033 `35ae89fe` (PR #403, merged during the
run in batch 120) and merges main twice: `c255e4dd` (batch 119: MUUN-VISUAL-005, AUDIO-006) at `7ae65313`
and `bb86bbf7` (batch 120: #403, RENDER-ITEMS-002AA, NEXT-GAPS-002) at `4965314e`. Implementation by
Claude Fable 5.2, no subagents, no full lane gate. Heavy work ran at nice 10, make at most four jobs,
two validator/test workers, with load waits.

Orchestrator order during the run: finish the particle/joint/sprite ids as one PR-ready unit; stay out of
`reconstructed/combat` and `native/core/mu_combat.c` (RENDER-EFFECTS-035 owns them); the effect-side ids
go to RENDER-EFFECTS-036 unless time remains; check the CSVs of RENDER-ACTORS-008 and RENDER-EFFECTS-035
once, late. Effect consumers live in `reconstructed/combat`, so none was taken here.

## Consumer table

[Table (CSV)](../research/render-effects-034-consumers.csv) and
[research note](../research/client-render-effects-034.md): every refused consumer pair known on this
base, with original addresses, requesting producers and refusal counts per fixture scene.

| | Rows |
|---|---:|
| Refused before (all table rows) | 63 |
| Admitted here, verified against the original | 27 (23 particles, 4 joints) |
| Sprite bitmaps bound | 2 (`0x810d`, `0x8003`) |
| Refused after | 34 rows: 6 particles, 7 joint rows, 21 effect-side rows |

Some rows stand for several ids (the blur's eleven bones, four `0x7fd6` subtypes, the 34 catalogue-skill
effects of RENDER-EFFECTS-035). The orchestrator's 22-id list was checked id by id against the lanes'
handoffs: 21 are done, and Muun particle `0x8084/28` stays refused. The new native ledger added two pairs
refused in **default** world views, `0x8016/5` and `0x7ef7/11`; both are done. Of the ids in the two late
CSVs, six actor-requested particle pairs were small and fully read and are done; the rest are listed.

## Pairs added, by group

| Group | Pairs | Requested by |
|---|---|---|
| Plain particles (6) | `0x8016/5`, `0x7ef7/11`, `0x7f5a/43`, `0x7f5a/47`, `0x7f54/1`, `0x7efa/3` | Swamp of Calmness, Elbeland, tower 39, Muun 377 |
| Item particles (7) | `0x8616/0`, `0x7fe0/10`, `0x84d1/2`, `0x850b/5`, `0x807e/14`, `0x807f/14`, `0x8080/14` | item producers `0x0f22`, `0x0f23`, `0x0f25`, `0x24be/0x24bf` |
| Follow particle (1) | `0x855d/2` | item producer `0x0f22` |
| Pulse particles (3) | `0x8081/1`, `0x8082/1`, `0x7ef7/19` | Muun mount style and secondary particles |
| Actor-requested plain particles (6) | `0x7f26/3`, `0x7f5a/50`, `0x807e/0`, `0x806e/0`, `0x7ef7/12`, `0x7ef7/13` | actor caller services (RENDER-ACTORS-008 request table, 23 request rows) |
| Joints (4) | `0x7f7c/8`, `0x7f7c/19`, `0x7fd5/4`, `0x7f7d/11` | Kanturu 37/40, tower 39, Barracks 41 / Refuge 42 |
| Bitmap bindings (4) | sprites `0x810d`, `0x8003`; particle bitmaps `0x8616`, `0x850b` | Muun 376/377; the two new item particles |

One table-driven consumer per kind: `reconstructed/particles/consumer34_kinds.inc` (a row per pair with
its form) and `reconstructed/joints/consumer34_joints.inc`; `0x7f54/1` is one line in the existing
Explosion case. `0x7efa/3` sets its blend state and draws no sprite, as the original's subtype table
does. `0x855d/2` follows the retained item-owner point at draw, like the existing `0x810a/0x25`. The world
bitmap table grows 100 to 104 (inserted before Fire03; the Fire06 and rain anchors keep their relative
place). Pool caps are unchanged.

The world particle module now keeps a per-pair refusal ledger (`refused_kinds`, 96 rows, overflow
counted) and reports `{"world_unsupported": [[routine, type, subtype, count], ...], "lost": n}` after the
joint summary line. Totals in `stats` are unchanged.

## Scenes: refusals before and after

Installed read-only game data, demo names only. "Before" is the same tree with the lane's six consumer
source files reverted to `35ae89fe` (main did not touch them) and the two new include files removed. The
world and skill pairs come from the ledger on the pre-change tree.

| Scene | Refused before | Refused after |
|---|---:|---:|
| Elbeland default view, 25 steps | 2 (`0x7ef7/11`) | **0** |
| Elbeland, draw-all, 61 steps | 32 | **0** |
| Swamp of Calmness default view, 25 steps | 1 (`0x8016/5`) | **0** |
| Swamp of Calmness, draw-all, 61 steps | 64 | **0** |
| Other 44 views, default and draw-all (88 runs) | 0 | 0 |
| Item `0xf22` in hand, 60 steps | 80 (`0x855d/2`, `0x7fe0/10`) | **0** |
| Item `0xf23` in hand, 60 steps | 60 (`0x8616/0`) | **0** |
| Item `0xf25` in hand, 60 steps | 36 (`0x84d1/2`, `0x850b/5`) | **0** |
| Wings `0x24be` and `0x24bf`, 60 steps | 120 each (`0x807e/14`, `0x807f/14`, `0x8080/14`) | **0** each |
| Muun 16 with the mount style, 90 steps | 180 (`0x8081/1`, `0x8082/1`) | **0** |
| Muun appearance 376, 90 steps | 720 (sprite `0x810d`) | **0** |
| Muun appearance 377, 90 steps | 102 (90 sprite `0x8003`, 12 particle `0x7efa/3`) | **0** |
| Muun appearance 375, 90 steps | 270 (`0x8084/28`) | 270 |
| Inline world host: Kanturu type 0x69, tower 0x36, 0x2f, Barracks 0x5a | 1 each (joints) | **0** each, joint routed |
| Skill 344 Blood Storm, 100 steps | 1,883 | 1,883 |
| Skills 44, 49, 41 (real sword model) | 1, 1, 5 | 1, 1, 5 |
| Other 27 skill scenes | 0 | 0 |

**Scenes whose refusals reached zero (16):** Elbeland and Swamp of Calmness, default and draw-all (so all
92 world-view runs are at zero); the five item scenes; Muun 16 mount style, Muun 376 and Muun 377; and
the four inline world joint cases. The tower particles are event-gated (production fixes the sequence
inactive) and the six actor-requested pairs wait for RENDER-ACTORS-008's producers; both are covered by
the original comparison and the native fixture only.

Proof renders (local, not committed, deleted with the lane's scratch): before/after frames of the Swamp
of Calmness brazier (the flame now draws), the five item scenes (red stars, sphere glow, red smoke, wing
smoke lines) and Muun 16 mount, 376 and 377; and the native host's images for every admitted pair and
binding, with the test bitmaps and again with the installed textures. All were looked at. The host images
are camera-space raster controls (a quad over the frame, or the joint's ribbon): they show that a pair
reaches the raster with its bitmap, colour and alpha, not a world placement.

## Original proof

`scripts/validate_render_effects34.py`, registry row `validate_render_effects34`, 200 cases per pair and
family: **16,259 checks, 0 mismatches, no original-machine stop**. Create, move and draw of every particle
pair (record fields, ordered calls, `rand()` counts, draw calls; the follow pair also compares the draw's
owner-point position write); `CreateJoint`, `MoveJoint` and `RenderJoints` for the four joints (record,
ordered calls, full GL stream); 32 native host rows (23 particles, 4 joints, 4 bitmap bindings, the
ledger); a 27-row admission census.

**116 compiled mutants, all detected, zero original stops**: three per pair (removed create, changed move,
removed draw), 31 form controls (lifetimes, thresholds, the pulse floor and colour, the follow start and
NULL owner, the alpha ceiling and fall, the world-0x3f lifetime, the arc's turn/jitter/speed, the bolt's
far end and jitter) and four native controls (follow hook, two swapped bitmap files, the ledger). The
complete set ran once through the registry in 178.6 s. Before that, during development: one control was
aimed at the wrong family (`clud_texture`, draw instead of create) and was corrected and rerun alone; one
native control needed a ledger fixture in the host before it could be detected; the first registry run
was judged failed only because the row declared 115 controls instead of 116, and the same report was
re-judged after the count was corrected.

Target SHA-256 `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`, text
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`, data
`c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`.

This proves the stated instruction slices and the native adapter contracts. It is not a claim about
original GPU pixels, the client's shared RNG phase, pool equivalence or which requests a live session
issues.

## Default identity and binaries

Both trees ran `make -C native -j4 world` right before their sweep; hashes were read again after
rendering.

- Before (consumer files at `35ae89fe`): `d9783e95d396df78393d23ad1d00f62be39d321fbaf9d0cfd054b71820862274`.
- After: `3f15f0c09928576a3a742f3b854f5b5880b1f914bab152024205734c09dbd7cf`.

These binaries are from the tree at `5b6565ad` (after the batch-119 merge, before batch 120 and the second
particle group). **To be repeated at the head** (WIP step 2); before 72.1 s, after 63.9 s.

Default world draw, DemoKnight, no draw-all, default clock, 640x400, 25 steps sampled at 0 and 24; the
14-view October tour and the 32-view DATA-ACQ-002 tour.

| | Identical |
|---|---:|
| PNGs | 91 of 92 |
| OBJECT/light dumps | 92 of 92 |
| Logs | 46 of 46 |
| Reports | 0 of 46 raw; 44 differ only by the ledger line and the four bitmap slots |

**Views that change, and why.** Swamp of Calmness frame 24: the brazier's `0x8016/5` particle was refused
and now draws (2,667 pixels inside x 24..95, y 0..48; mean RGB difference 0.183 of 255). Its report gains
one created/drawn particle and two `rand()` calls. Elbeland's report gains two created/drawn `0x7ef7/11`
particles and six `rand()` calls; its two saved frames stay byte-identical. Every report gains the
`world_unsupported` line and four loaded bitmap entries at slots 96..99; the rest of each bitmap list is
equal after removing those four. This is native-to-native identity, not original image equivalence.

## Tests changed in other lanes' files

Three expectations followed the new consumers; each is a few lines:

- `native/tests/worlds_inner_host.c`: the four inline joint cases now expect the joint routed and no
  refusal (as RENDER-EFFECTS-031 did for `0x7f7d/8,9,10`); the host's joint hook checks their owner and
  width.
- `reconstructed/joints/test_joints.py`: the four pairs moved from the refused list to the admitted one.
- `native/tests/test_muun_transition.py`: Muun 16's pulse particles now draw and take rotation and size
  from the world's one `rand()` stream, which the transition's own requests advance. The end-frame
  identity of the two runs is now asserted outside the Muun's particle box, plus zero live and drawn
  transition models.

No world object routine, Muun module, item table, actor, UI, audio or combat source file was edited.

## Completed checks and test budget

Commands ran from the repository root with the canonical `private-env.sh`. No full gate.

| Check | Result | Wall s |
|---|---|---:|
| Root build after each merge | pass | 19 to 36 |
| Grouped verifier via registry, 200 cases, all mutants (`0a4e4ded`) | 16,259 equal; 116/116 mutants; zero original stops | 178.6 |
| Affected private validators, no mutants (`5b6565ad`) | 89/89 pass | 1,366.1 |
| Private validator delta after batch 120 and the second group (`4b5598ee`) | 118/118 pass | 3,894.4 |
| Private validator delta after batches 121/122 (head) | **stopped**: 8 of 66 passed, none failed | - |
| Portable affected, first run | 1,888 tests; 1 stale joint expectation, fixed | 480.6 |
| Portable delta after batches 119/120 | 1,674 tests, 1,343 passed / 331 skipped, 0 failures | 457.8 |
| Portable delta after the second group | 1,816 tests; 1 stale particle expectation, fixed and rerun | 413.6 |
| Portable delta after batches 121/122 | **not run** | - |
| `test_render_effects34` with private env | 3 tests pass | 10.3 |
| Muun modules with private env (after batch 119) | 29 tests; 1 end-frame expectation, fixed and rerun | 123.0 + 16.7 |
| Refusal census: 31 skill scenes / 92 world runs before; 123 scenes after | counts in the scene table | 47.5 / 221.4 / 351.3 |
| Item scenes (5 types, both binaries) and Muun scenes (4, both binaries) | counts in the scene table | 20.7 / about 60 |
| Identity sweep before / after (pre-batch-120 tree) | 46 views each | 72.1 / 63.9 |
| Repository audit | **not run** | - |

**8d reduced:** not run at the head. Run so far with the private environment: `test_render_effects34`,
`test_native_worlds_inner` and the seven Muun modules (after batch 119).

**Packaging exclusion:** only `native/tests/test_native_app.py` was removed from the portable affected
work list, by a task-local wrapper (not committed). No package, signing, install, installed-app journey,
Native Data refresh or README work.

## Steward validators

`private-env.sh` supplies MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT, MU_SECTION3, MU_EVIDENCE_DIR,
MU_NATIVE_DATA_DIR, MU_LANG_DIR and the row-specific paths. Run
`scripts/run_validators.py --private --no-mutants --cache --affected origin/main --jobs 2`.
**Mutants: only `validate_render_effects34`, already run once here; none needed from the steward.**

Rows that passed here (no mutants), at `4b5598ee` or, for rows only in the first selection, `5b6565ad`:

validate_actor_composites, validate_actor_groups, validate_actor_monsters, validate_actor_plain, validate_actor_recipes, validate_app_polish1, validate_app_polish2, validate_app_polish4, validate_armour_cloak, validate_audio_callers, validate_audio_combat, validate_audio_domains, validate_audio_items, validate_audio_kubera, validate_audio_monsters, validate_audio_monsters6, validate_audio_objects, validate_audio_objects4, validate_charsel_items, validate_fidelity, validate_icarus, validate_icarus_c2, validate_inventory_fx, validate_item_caller_groups, validate_item_callers, validate_item_carry, validate_item_chains, validate_item_cloak, validate_item_clusters, validate_item_continuation, validate_item_coverage, validate_item_cycle, validate_item_derived, validate_item_direct_bodies, validate_item_effects, validate_item_expansion, validate_item_falloff, validate_item_gear, validate_item_groups, validate_item_helper_groups, validate_item_hiddenmesh, validate_item_named, validate_item_next, validate_item_other_bodies, validate_item_ownerfx, validate_item_predraw, validate_item_product, validate_item_quality, validate_item_random_levels, validate_item_ranked, validate_item_read_programs, validate_item_remainder_programs, validate_item_scalars, validate_item_types, validate_item_wings_next, validate_items_ui, validate_joints, validate_meshdraw, validate_model_edge, validate_model_light, validate_movement, validate_muun_transition, validate_npc_cloak, validate_particles, validate_render_effects, validate_render_effects10, validate_render_effects11, validate_render_effects12, validate_render_effects13, validate_render_effects14, validate_render_effects15, validate_render_effects16, validate_render_effects17, validate_render_effects18, validate_render_effects19, validate_render_effects20, validate_render_effects21, validate_render_effects22, validate_render_effects23, validate_render_effects24, validate_render_effects25, validate_render_effects26, validate_render_effects27, validate_render_effects28, validate_render_effects3, validate_render_effects30, validate_render_effects31, validate_render_effects32, validate_render_effects33, validate_render_effects34, validate_render_effects4, validate_render_effects5, validate_render_effects6, validate_render_effects7, validate_render_effects9, validate_render_worlds_a, validate_renderchar, validate_skill_fx, validate_terrain, validate_terrain_remaining, validate_viewport_monsters, validate_world_particle_consumers, validate_worlds_121, validate_worlds_after, validate_worlds_after2, validate_worlds_after3, validate_worlds_after4, validate_worlds_after5, validate_worlds_after6, validate_worlds_d, validate_worlds_e, validate_worlds_f, validate_worlds_fog, validate_worlds_g3, validate_worlds_inner, validate_worlds_inner2, validate_worlds_inner3, validate_worlds_inner4, validate_worlds_inner5, validate_worlds_karutan, validate_worlds_l, validate_worlds_m, validate_worlds_raklion, validate_worlds_slots, validate_worlds_slots2, validate_worlds_slots3.

The 66-row selection after batches 121/122 still has to run (WIP step 1).

## Limits and next lane

- `0x8084/28` (Muun 375) stays refused: its move reads the owner OBJECT's bones 11 and 18 each step
  (`0x0129f12c`, `TransformPosition` `0x012b6ef1`). The native Muun request carries no owner and the
  particle host has no owner-bone service. Request-side note for the Muun lane: pass the Muun as the
  particle owner and expose its posed bone points; the consumer's create and alpha/scale program are in
  the research note.
- `0x8145/1` (Blood Storm) stays refused: the particle form is recovered (research note), but the combat
  pool has no `0x8145` bitmap row and `native/core/mu_combat.c` was out of bounds. One row plus the pair's
  admission closes it.
- The owner-position form `0x807e/1`, `0x807f/1`, `0x8080/1`, `0x7ffd/6` (actor callers) reads the owner
  position in create and move; its branches were not all read. One form, four pairs, for the next
  consumer lane.
- Joints not traced: actor `0x7f7c/10` (72 request rows), `0x7f79/4`, `0x7f7c/7`, `0x7fd6/6,55,56,57`;
  skill `0x472/0x12`, `0x472/4`, `0x7f78/0x2f`. `0x4ae` and `0x7fde` have a variable subtype in the request.
- RENDER-EFFECTS-036 list: Blood Storm `0x585/0`, `0x586/0`, `0x4b7/1`, blur `0x814b`; Crescent `0x49e/0`;
  Fire Breath `0x8001/0`; tower effects `0x4be/0`, `0x4bf/0`, `0x419/2`, `0x41a/2`, `0x4c0/0`, `0x4c1/0`,
  `0x4c2/0`, `0x4c5/0x4c0`, `0x4c5/0x4c1`, `0x4c5/0x4c2`. New: effect `0x454` subtypes -1, 1, 2, 3, 4
  (Twisting Slash with the installed sword model, from the ledger); the actors' type 226, `0x801d/0` and
  `0x413/10`; the 34 catalogue-skill effect pairs of RENDER-EFFECTS-035's CSV.
- `0x7f7d/11` with a width below 8 divides by zero in the client; the native modulo helper returns 0
  there. Producers pass 15 times the object scale.
- Eligibility, damage, mana, cooldowns, server keys, packets, protection, live client state and owner
  apps are outside this fixture subset.

## Delivery

Draft PR, no ready-prs entry. The lane's scratch (census, traces, proof renders, the exported before-tree)
and build outputs were deleted by owner order; the worktree and branch are kept for the resume. The
original-instruction tracer used to read the cases lived in scratch; the research note records the
method and every case address. No new private input needs retaining. Paths: `~/Documents/MTM/mu-mac-tools/native/scratch/render-effects-034` and
`~/Documents/MTM/worktrees/render-effects-034`.
