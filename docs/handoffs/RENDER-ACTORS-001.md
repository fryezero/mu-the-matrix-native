# RENDER-ACTORS-001

## WIP (stopped 2026-11-09)

Stopped at the owner's explicit request. This branch is **WIP, not PR-ready**. No PR was opened and no
ready-prs.txt entry was written. The worktree and local/remote branch are retained.

### Done and verified

- Six whole skeleton-body mappings and nine additional equipment-loader admissions are implemented. The
  census lists all 32 recovered Player-model rows. Death King 55 gains Skeleton01 at scale 1.4.
- Initial new-row checks: 343 checks pass and 10/10 compiled mutants are caught at `55f7dcdc`, 58.1 s.
  On merged runtime source `6c2ca37a`, the new row passes again without mutants in 25.5 s.
- Initial 19 affected validators pass. After merging main `54a53e1a`, all 56 selected rows pass in
  1,415.7 s. Cumulative last passes: 58 rows, 960,016 cases. The per-row table below records wall times.
- Merged portable run: 1,432 tests, 1,189 passed, 243 skipped, no failures/errors, 305.3 s including selection.
  The earlier hard-coded pin-path policy failure was corrected; the standalone 16-test pin module and merged
  root suite pass. The reduced private run passes all 25 tests in 20.9 s, with no skips.
- Native before/control and after images were reviewed for 17 covered classes. The final merged after images
  match those reviewed images. Both default sweeps retain all 92 PNGs, 92 dumps and 46 reports byte-identically.
- Final documentation consumers: 36 tests, one skip, OK in 7.5 s. Final audit before this stop note:
  2,136 files, zero rejected, 18.8 s. No full lane gate, live client, installed app or protection work.

### Known correctness gap

A final static constructor cross-check found that Golden Archer 236 writes CHARACTER `+0x144 = 8` at
`0x01384306`. Its world-0 town branch `0x01367d85..0x01367e23` passes that word shifted by three to
RenderPartObject. The current recipe, native glow and original-reference fixture incorrectly use zero.
The passing comparisons therefore do **not** verify Golden Archer's town +8 glow. No correction to runtime
code or tests has been started after this discovery. The former statement that this constructor leaves
`+0x144` zero was wrong. CreateCharacter clears it, then this class constructor overwrites it.

Native also routes the non-item skeleton types through its plain-body fallback. Simply changing the stored
level is insufficient: the +8 body passes need the proper generic/original draw path. Outside the world-0
NPC branch the final skeleton branch passes level zero; preserve that condition. Fifteen later subtype
recipes remain unadmitted, and the generic pose/link/shadow/fade limits below still apply.

### Exact next steps and checks still required

1. In `scripts/validate_actor_recipes.py`, retain the constructor's `+0x144` value and populate it in the
   RenderCharacter reference record. Add world 0 versus nonzero-world cases for class 236. The expected
   town level argument must be `8 << 3`, rather than a copied zero from the authored fixture.
2. Correct `reconstructed/actors/actors.c` and `native/core/mu_world_actors.c` to carry the body level and
   its world condition. Recover/compare the +8 RenderObjDraw stream for model `0x423` and route it correctly
   through `native/core/mu_renderchar.c` or a narrow actor caller. The current plain fallback drops level passes.
3. Extend the owning validator and native host/tests to catch the level, world gate and draw-pass admission
   mistakes. Update manifest family/case/mutant counts from the actual chosen coverage. The prior 10-mutant
   result covers the old targets; changed targets need one new final mutant run.
4. From the repo root, source `~/Documents/MTM/mu-mac-tools/native/private-env.sh`; check resources, build with
   `nice -n 10 make -j4`, inspect post-build affected selections, then run only selected validators with
   `--private --no-mutants --cache --jobs 2`. Run changed-target mutants once after the fix is stable.
   Run affected portable suites and the reduced private native modules under the brief's 40-item cap.
5. Re-render Golden Archer in world 0 and at least one other world, at default and a second clock. Recheck
   the other actor images and the default capture identities only as compiled-input changes require.
   Refresh the handoff, PR body and current main integration; audit added/renamed files and documentation.
   Open a PR and write a ready-prs entry only when the corrected scope is fully checked.

Small local resume inputs, 38,574 bytes total, remain under
`~/Documents/MTM/mu-mac-tools/native/scratch/render-actors-001/wip-inputs/`:
`verified-ledger.json`, `baseline-hashes.json`, `render-metrics.json`, `merged-proof.json`.
The baseline file preserves the one-time `5ef84dff` PNG/dump hashes and normalized-report hashes, so a
future after sweep can compare against them without retaking the before numbers. Large reports, copied
binaries, screenshots/renders and build directories are removed at stop. These local inputs are not committed.

Branch `codex/render-actors-001`, based on main `5ef84dff`. Offline/static only. No live original client,
network/login/server-state/packet work, protection analysis, original-install tree, memory writes or installed app changes.

## Result and census

Death King 55 now has its original whole Skeleton01 body on Player bones, at scale 1.4, alongside its existing
weapon and CLOAK-004 cloth. Classes 14, 15, 16, 56 and 236 use the same recovered whole-body path. These six
have no five-piece armour recipe in the original branch. The five non-Golden classes use a level-zero whole-body call, flags 2. Golden Archer's +8 town body remains incorrect, as detailed in the WIP section. Eleven equipment rows use their extracted five-part body models and levels;
nine gain native admission, with 229 and 257 retained as existing-loader controls.

Of the 32 player-model rows in the class table, 14 have bounded body/loader fixes, Golden Archer is WIP,
2 are unchanged controls, and 15 remain unadmitted. This is the census of the bounded class table, not a claim that every virtual map processor,
world variant or transformed-player appearance is reconstructed. Shipped placements are unchanged.

Latest main `54a53e1a` was merged as `6c2ca37a`, preserving both lanes' status entries. The merged build passes
in 12.0 s. The post-build delta selector retains 56 rows in 63.9 s. All 56 pass without mutants in 1,415.7 s. The actor implementation and its compiled mutant targets are unchanged by that merge.

| Class | Result | Body recipe | Scale |
|---|---|---|---:|
| 14 | fixed | whole `0x422`, Skill/Skeleton01 | 0.95 |
| 15 | fixed | whole `0x423`, Skill/Skeleton02 | 1.1 |
| 16 | fixed | whole `0x424`, Skill/Skeleton03 | 1.2 |
| 34 | fixed | five parts `0x18e9..0x20e9`, +9 | 0.9 |
| 55 | fixed | whole `0x422`, Skill/Skeleton01 | 1.4 |
| 56 | fixed | whole `0x422`, Skill/Skeleton01 | 0.8 |
| 229 | unchanged control | five parts `0x18ef..0x20ef`, +7 | 0.9 |
| 236 | WIP | whole `0x423`, Skill/Skeleton02; +8 town level/passes missing | 1 |
| 247 | fixed | five parts `0x18ef..0x20ef`, +0 | 0.9 |
| 249 | fixed | five parts `0x18ef..0x20ef`, +0 | 0.9 |
| 257 | unchanged control | five parts `0x18fe..0x20fe`, +13 | 1 |
| 258 | fixed | five parts `0x18ef..0x20ef`, +0 | 0.9 |
| 297 | fixed | five parts `0x18e7..0x20e7`, +9 | 0.9 |
| 371 | fixed | five parts `0x18ef..0x20ef`, +0 | 0.9 |
| 372 | left | subtype `0x425`, kind/world/action hook unresolved | 0.95 |
| 373 | left | subtype `0x429`, kind/world/action hook unresolved | 0.95 |
| 374 | left | subtype `0x3ed`, kind/world/action hook unresolved | 0.85 |
| 375 | fixed | five parts `0x1904..0x2104`, +9 | 0.9 |
| 378 | left | subtype `0x3e9`, kind/world/action hook unresolved | 1 |
| 414 | fixed | five parts `0x18ef..0x20ef`, +0 | 0.9 |
| 464 | fixed | five parts `0x18ef..0x20ef`, +0 | 0.9 |
| 503 | left | subtype `0x541`, kind/world/action hook unresolved | 0.9 |
| 548 | left | subtype `0x552`, kind/world/action hook unresolved | 0.9 |
| 616 | left | subtype `0x5bb`, kind/world/action hook unresolved | 0.9 |
| 617 | left | subtype `0x5ba`, kind/world/action hook unresolved | 0.9 |
| 625 | left | subtype `0x5bc`, kind/world/action hook unresolved | 1.1 |
| 626 | left | subtype `0x5bd`, kind/world/action hook unresolved | 0.6 |
| 642 | left | subtype `0x5be`, kind/world/action hook unresolved | 0.9 |
| 646 | left | subtype `0x5bb`, kind/world/action hook unresolved | 0.9 |
| 706 | left | subtype `0x5bf`, kind/world/action hook unresolved | 0.9 |
| 806 | left | subtype `0x5c4`, kind/world/action hook unresolved | 1.1 |
| 807 | left | subtype `0x5c5`, kind/world/action hook unresolved | 0.9 |

Each five-part range advances by `0x200` per slot. The exact nine-slot records, including weapons and wings,
remain in `reconstructed/actors/monster_class_table.h`; the new code does not regenerate or edit that table.

## Evidence and implementation

See [research section 7](../research/client-actors.md#7-player-model-actor-body-recipes-render-actors-001).
Inputs are pinned by `scripts/pins.py`: text `2bd5f2e9...3724`, image data `c985e2e6...672f`, plus the pinned
trig flag and feature word. The validator loads and checks their full SHA-256 values.

- Generic constructors `0x0138366a`, `0x01383791`, `0x0138383a`, `0x013842a4` set the six skeleton subtypes.
- Startup loop `0x01832c28..0x01832c5d` loads Skeleton01..03 from Data/Skill into `0x422..0x424`.
- RenderCharacter `0x01369f98..0x0136a00d`, and Golden Archer's town branch `0x01367d85..0x01367e23`, supply the whole body.
- The eleven equipment recipes execute the existing constructor/processor chain and RenderCharacter's idle
  part/link plan at action 1, with authored record kind 0 and option/ext 0. Model lookup, strings and engine services are the existing named stubs; no opaque chain jump runs.
- `mu_actor_player_recipe` returns only the six recovered whole-body classes and rows with explicit body equipment.
  The native loader uses slot 0 for the whole mesh, preserves table levels/scales, and loads it on the same Player
  bone pose as the existing armour. Ordinary actors and the fifteen unresolved rows retain their prior route.
- The native host calls the production actor loader, poses each of the 17 covered actors, checks nonempty height
  bounds, exact loaded slot types/levels/scales, mesh counts and zero missing textures.

## Checks

Commands run from the repository root with canonical private-env.sh, nice 10,
make at most four jobs and validator runners two. No full lane gate. Resource pauses followed high load.

| Check | Result | Wall |
|---|---|---:|
| Main baseline `make -j4` | pass | 26.1 s |
| Initial lane `make -j4` | pass | 13.1 s |
| Merged `make -j4`, main `54a53e1a` integrated as `6c2ca37a` | pass | 12.0 s |
| Merge delta selection since `55f7dcdc` | 56 rows, 9 unused consumers pruned | 63.9 s |
| Merged selected validators, no mutants | 56/56 pass, 938,505 cases | 1,415.7 s |
| New validator, mutants once | 343 checks, 0 mismatches; 10/10 compiled mutants caught | 58.1 s |
| Post-build validator selection | 19 selected, 3 symbol fallbacks; 12 unused consumers pruned | 53.3 s |
| Affected private validators, no mutants, cached | 19/19 pass, 80,487 cases | 203.4 s including selection |
| Merged portable affected suites | 1,432 tests, 1,189 passed, 243 skipped, 0 failures/errors | 305.3 s including selection; 257.9 s tests |
| 8d reduced private modules, root with private-env.sh | 25 tests OK, 0 skipped | 20.9 s |
| Pin-policy repair rerun | test_pins, 16 tests OK | 0.73 s |
| Initial audit | 2,129 files, 0 rejected | 14.9 s |
| Pin-wrapper checkpoint audit | 2,133 files, 0 rejected | 17.0 s |
| Main-merge audit | 2,136 files, 0 rejected | 17.6 s |
| Final four documentation-consumer modules | 36 tests OK, 1 skipped | 7.5 s |

The new validator totals 307 original-instruction or extracted-constructor comparisons, 17 actual native loads
and 19 authored exclusion controls. Its families are recipes 36, body hook 240, equipment plan 11,
RenderObjDraw body stream 36, startup loader 3 and native loads 17. This is not 343 original pixel comparisons.
The original render pipeline for equipment is unchanged, so only the new row runs compiled mutants.

**8d reduced:** the native/tests selection is 146 work items, above the 40-item cap. The merged private run covers native.tests.test_actor_recipes and main's changed native.tests.test_native_renderchar, with private-env.sh from the repository root. Initial portable affected run: 1,449 tests, 1,210 passed, 238 skipped, one pin-policy failure; 336.0 s including selection, 284.8 s tests. The new validator's four default paths were moved to pins.py resolution and all four inputs now use Pin.read. All 16 tests in test_pins pass in 0.73 s. The merged portable run passes 1,432 tests with 243 explicit skips and no failures/errors. The two-module private run passes all 25 tests without skips. Brief 6b review found no changed existing
constant, struct layout or table size. The two new exported functions are consumed only by the new tests
and the actor loader; the unchanged actor/skin/cloth implementations retain their earlier coverage.
Static census cross-check: all 1,024 generic class keys give 31 immediate Player-model cases, all present in
this census. Class 297 is the additional recovered processor row. No protection boundary was followed.

## Renders and byte identity

All native captures use DemoKnight and authored demo actor placements,
640x480, two frames, GL, world 0 at 128,124 with each actor at 129,125, direction 5.
The before control admits the same class rows but omits the whole-body slot. It is an instrumented control,
not an unmodified-main image for classes that main refuses. Death King, Marlon and Shadow Phantom Soldier
already load on main. Six skeleton pairs gain body pixels; the eleven equipment control pairs are identical.
The unchanged main binary supplies the one-time before numbers for the default-draw capture sweep.


| Skeleton class | Changed pixels, frame 1 | Before / after wall |
|---|---:|---:|
| 14 | 1,319 | 1.026 / 1.027 s |
| 15 | 3,222 | 0.817 / 0.804 s |
| 16 | 2,792 | 0.788 / 0.791 s |
| 55 | 3,278 | 0.791 / 0.791 s |
| 56 | 1,000 | 0.782 / 0.883 s |
| 236 | 2,695 | 0.812 / 1.092 s |

All 17 before/after pairs were visually inspected, including the eleven identical equipment controls. Total render wall 29.9 s. The review used native window contents and actor crops, not a desktop screenshot.

One default-draw byte-identity sweep at 640x400, without draw_all or live_time:
- October 22: 28/28 PNGs, 28/28 OBJECT/light dumps and 14/14 normalized reports identical; 14.75 / 14.13 s.
- DATA-ACQ-002: 64/64 PNGs, 64/64 OBJECT/light dumps and 32/32 normalized reports identical; 39.03 / 44.37 s.

Reports normalize only their output-directory prefix. The capture-sweep commands supply no new actor placements.

After integrating main `54a53e1a`, only the after side is repeated because shared compiled render inputs changed.
The original before numbers are not taken again. Final merged results at source `6c2ca37a`:
- October 22: 28/28 PNGs, 28/28 dumps and 14/14 normalized reports still identical; 18.68 s.
- DATA-ACQ-002: 64/64 PNGs, 64/64 dumps and 32/32 normalized reports still identical; 48.28 s.
- Every one of the 17 actor frame-1 PNGs is byte-identical to its visually reviewed initial after image.
- Clock 123456 ms, same scene: class 34's before/after pair is identical, 1.049 / 1.121 s;
  class 55 changes the same 3,278 body pixels, 1.045 / 0.946 s. The original-body instruction comparisons
  also cover twelve time values for each of the three whole-body models.
- The final proof job totals 87.9 s, including the capture sweeps, 17 actor repeats and four clock renders.


Screenshots, inputs and local reports are under
`~/Documents/MTM/mu-mac-tools/native/{scratch,renders}/render-actors-001/`. Large outputs are removed at this owner-requested stop; the small resume inputs are listed above.
No original screenshot, pixel equivalence or live motion comparison is claimed.

## Limits and next

- Fifteen later subtype rows remain unadmitted. Next recover their exact NPC/player kind gates, world/action
  predicates and special mesh/effect hooks. The generic class table's world-0, rand-0 and virtual-processor limits
  remain. Its transformation proxy rows are not assumed to be ordinary spawnable monsters.
- Native Player-model actors retain the existing generic pose and weapon-link path. The original idle link plans
  are compared, but this lane does not establish original-equivalent walking, carried-weapon transforms, shadows,
  buffs, guild/duel state or native fade alpha. Their existing item passes and armour owner effects remain in use.
- Native cloth uses CLOAK-004's own wind/rand history. No original-pixel or temporal equivalence claim.
- Character stats and power, live services and protection code remain outside the lane. Original class equipment
  is used only for appearance; fixtures supply all placement and motion.

## Release

Steward validators: validate_actor_recipes, validate_app_polish1, validate_app_polish2, validate_app_polish4, validate_armour_cloak, validate_audio_callers, validate_audio_combat, validate_audio_domains, validate_audio_items, validate_fidelity, validate_icarus_c2, validate_inventory_fx, validate_item_callers, validate_item_carry, validate_item_chains, validate_item_cloak, validate_item_clusters, validate_item_continuation, validate_item_coverage, validate_item_derived, validate_item_expansion, validate_item_gear, validate_item_hiddenmesh, validate_item_named, validate_item_next, validate_item_ownerfx, validate_item_predraw, validate_item_product, validate_item_quality, validate_item_ranked, validate_item_scalars, validate_item_types, validate_item_wings_next, validate_meshdraw, validate_model_edge, validate_movement, validate_npc_cloak, validate_render_effects10, validate_render_effects11, validate_render_effects12, validate_render_effects13, validate_render_effects14, validate_render_effects15, validate_render_effects16, validate_render_effects17, validate_render_effects18, validate_render_effects19, validate_render_effects20, validate_render_effects21, validate_render_effects22, validate_render_effects23, validate_render_effects24, validate_render_effects5, validate_render_effects7, validate_render_effects9, validate_renderchar, validate_viewport_monsters, validate_worlds_fog.

All 58 rows passed across their last passes, 960,016 cases. The initial 19 pass at `55f7dcdc`; after main `54a53e1a` was merged as `6c2ca37a`, all 56 selected rows pass, 938,505 cases in 1,415.7 s. The initial-only rows are validate_audio_combat, validate_viewport_monsters.

Only validate_actor_recipes needs the lane's mutants, passed 10/10 at `55f7dcdc`. Its C targets are unchanged by the merge. The pin resolver wrapper is corrected and rechecked on the merged tree. All other rows run without mutants; unchanged upstream mutant targets are not repeated. Env: `. ~/Documents/MTM/mu-mac-tools/native/private-env.sh`.

| Validator | Cases | Wall | Tested source commit |
|---|---:|---:|---|
| `validate_actor_recipes` | 343 | 25.5 s | `6c2ca37a` |
| `validate_app_polish1` | 752 | 16.7 s | `6c2ca37a` |
| `validate_app_polish2` | 1,028 | 3.1 s | `6c2ca37a` |
| `validate_app_polish4` | 10,485 | 27.1 s | `6c2ca37a` |
| `validate_armour_cloak` | 4,448 | 38.4 s | `6c2ca37a` |
| `validate_audio_callers` | 5,528 | 4.5 s | `6c2ca37a` |
| `validate_audio_combat` | 19,548 | 26.5 s | `55f7dcdc` |
| `validate_audio_domains` | 2,544 | 19.7 s | `6c2ca37a` |
| `validate_audio_items` | 3,000 | 3.2 s | `6c2ca37a` |
| `validate_fidelity` | 991 | 54.0 s | `6c2ca37a` |
| `validate_icarus_c2` | 8,400 | 13.7 s | `6c2ca37a` |
| `validate_inventory_fx` | 8,017 | 6.1 s | `6c2ca37a` |
| `validate_item_callers` | 6,013 | 1.0 s | `6c2ca37a` |
| `validate_item_carry` | 114,388 | 354.4 s | `6c2ca37a` |
| `validate_item_chains` | 35,406 | 90.4 s | `6c2ca37a` |
| `validate_item_cloak` | 5,694 | 107.1 s | `6c2ca37a` |
| `validate_item_clusters` | 74,292 | 52.4 s | `6c2ca37a` |
| `validate_item_continuation` | 25,772 | 50.2 s | `6c2ca37a` |
| `validate_item_coverage` | 31,724 | 56.0 s | `6c2ca37a` |
| `validate_item_derived` | 36,252 | 179.0 s | `6c2ca37a` |
| `validate_item_expansion` | 52,172 | 50.7 s | `6c2ca37a` |
| `validate_item_gear` | 25,256 | 80.1 s | `6c2ca37a` |
| `validate_item_hiddenmesh` | 116,281 | 355.5 s | `6c2ca37a` |
| `validate_item_named` | 20,057 | 3.5 s | `6c2ca37a` |
| `validate_item_next` | 14,992 | 180.9 s | `6c2ca37a` |
| `validate_item_ownerfx` | 14,964 | 116.5 s | `6c2ca37a` |
| `validate_item_predraw` | 37,556 | 226.8 s | `6c2ca37a` |
| `validate_item_product` | 2,874 | 53.8 s | `6c2ca37a` |
| `validate_item_quality` | 28,080 | 145.1 s | `6c2ca37a` |
| `validate_item_ranked` | 17,736 | 49.7 s | `6c2ca37a` |
| `validate_item_scalars` | 26,274 | 45.9 s | `6c2ca37a` |
| `validate_item_types` | 135,176 | 32.0 s | `6c2ca37a` |
| `validate_item_wings_next` | 33,622 | 58.0 s | `6c2ca37a` |
| `validate_meshdraw` | 14,619 | 58.1 s | `6c2ca37a` |
| `validate_model_edge` | 954 | 121.6 s | `6c2ca37a` |
| `validate_movement` | 6,614 | 45.6 s | `6c2ca37a` |
| `validate_npc_cloak` | 2,619 | 26.3 s | `6c2ca37a` |
| `validate_render_effects10` | 154 | 0.4 s | `6c2ca37a` |
| `validate_render_effects11` | 176 | 0.3 s | `6c2ca37a` |
| `validate_render_effects12` | 64 | 0.3 s | `6c2ca37a` |
| `validate_render_effects13` | 180 | 0.4 s | `6c2ca37a` |
| `validate_render_effects14` | 660 | 0.9 s | `6c2ca37a` |
| `validate_render_effects15` | 509 | 0.6 s | `6c2ca37a` |
| `validate_render_effects16` | 424 | 2.5 s | `6c2ca37a` |
| `validate_render_effects17` | 618 | 6.1 s | `6c2ca37a` |
| `validate_render_effects18` | 540 | 0.9 s | `6c2ca37a` |
| `validate_render_effects19` | 400 | 0.7 s | `6c2ca37a` |
| `validate_render_effects20` | 148 | 0.2 s | `6c2ca37a` |
| `validate_render_effects21` | 267 | 0.2 s | `6c2ca37a` |
| `validate_render_effects22` | 202 | 4.9 s | `6c2ca37a` |
| `validate_render_effects23` | 1,174 | 5.5 s | `6c2ca37a` |
| `validate_render_effects24` | 226 | 1.9 s | `6c2ca37a` |
| `validate_render_effects5` | 1,190 | 3.6 s | `6c2ca37a` |
| `validate_render_effects7` | 596 | 1.5 s | `6c2ca37a` |
| `validate_render_effects9` | 304 | 0.9 s | `6c2ca37a` |
| `validate_renderchar` | 1,706 | 42.0 s | `6c2ca37a` |
| `validate_viewport_monsters` | 1,963 | 20.9 s | `55f7dcdc` |
| `validate_worlds_fog` | 4,044 | 4.3 s | `6c2ca37a` |

Stopped cleanup removes large lane outputs and build directories. The worktree and local/remote branch stay.
No ready-prs line is written. The four small local resume inputs are listed in the WIP section.

Self-review checked the changed C interfaces, constructor/loader/body evidence, resource and test budget,
all census outcomes and the final diff. No independent agent review or original-client pixel comparison is claimed.
