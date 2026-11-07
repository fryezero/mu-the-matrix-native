# RENDER-ITEMS-002R

Branched from main `18ab0134`; merged main `3ecc205c` (#317-#320) and `ce0ebd71` (#323, #324; RENDER-EFFECTS-017's armour particle kinds reached `reconstructed/particles`, where the item rows use only the unchanged `mu_pt_transform_position`; after it: build, `test_native_renderchar` 16/16, the portable renderchar modules 19 tests, 3 private skips). Branch/worktree `claude/render-items-002r` (Claude Opus 5.5). No live client,
launcher, network or hosted workflow. No full gate in the lane (2026-11-04 test budget).

Scope: RENDER-ITEMS-002 part 18, the first group of part 17's "Next groups": effects that RenderObjDraw creates in
its own type case before the body draws, with an item-bone host for the `0x0150e746` bone sprites.
[Finding](../research/client-render-items.md#part-18-pre-draw-effect-programs-on-the-items-own-bones-render-items-002r).

## Result

Bodies **1,319 → 1,345 of 1,674** (+26: six swords `0x0b27`, `0x0b2a`, `0x0b4b`, `0x0b4c`, `0x0b57`, `0x0b59`; three
maces `0x0f1c`, `0x0f1d`, `0x0f2e`; four bows `0x1311`, `0x1312`, `0x1316`, `0x131d`; three shields `0x1748`,
`0x1749`, `0x1758`; ten wings `0x230b`, `0x2311`, `0x2382`..`0x2385`, `0x2394`, `0x2395`, `0x2494`, `0x2499`).
Skins 17/17, links eighteen targets/twenty-four types. **329 bodies remain.** Survey: 798 shapes, complete shapes 556 → 572; both TSVs flip exactly the 26 types.

- **Census** (scratch, four survey states): 91 of the 355 remaining types create effect services before their
  first draw, in RenderObjDraw's own case; 8 only after it; 220 call none (or only rand); 36 fault (31 in strlen).
- **Reader** (`scripts/gen_item_owner_fx.py`, pre-draw mode). A basic-block trace finds the case start (the block
  after the last type compare before the first effect); the case ends at the jump to the join. The part-17
  interpreter reads RenderObjDraw's frame and the new idioms: std::string names + `0x012bd35a`, `0x0150e746`,
  TransformPosition `0x012b6ef1` on `BoneTransform + 0x30·bone`, the wave `0x0185bdc4`, the clock, the CRT sine,
  the comparison abs `0x0184f8ff`, the alpha argument, `(float)(rand() % m)`, `rand() % 2^n` gates, vec3 set/scale,
  float/int arrays, the TestFrustrum2D flag `[ebp-0xd]` and loops over constant counters (decided statically).
  40 of the 91 read; ops 15..25; 16-bit registers; bone names in `mu_rc_fx_names`. The 43 part-17 programs'
  op rows are unchanged.
- **Draws** (`gen_item_bodies`): the 40 read types fitted with the effect requests set aside; the 292-state
  comparison keeps 26, 21 of them with the part-14 supplementary probes (`PRE_EXTENDED`) and 17 with the part-13
  carry rule (`PRE_CARRY`). The pre-draw block's own rand sites are left to the effect program. `0x1313`, `0x1317`,
  `0x1319` read but fit no probe option.
- **Executor** (`owner_fx.inc` `run_fx`, shared with part 17). `mu_rc_item_draws_owner` runs the pre-draw program
  first when the host has `item_transform` (no select/shadow/`a13`). Appended ABI: `mu_rc_owner_host.bone_named`,
  `.item_transform`, `.refuse`, `.visible`; `mu_rc_owner_fx.rotation`, `.blend`, `.owner`; `mu_rc_item_pre_fx()`.
  A request on a bone outside `0..item_bones-1`, or computed from such a position, goes to `refuse`.
- **Native** (`mu_renderchar.c`): with `env->particles`, an item-bone host (named bones from the BMD, the pose in
  the new `env->item_bones`, BodyScale/BodyOrigin; flag 1); sprites → `mu_world_particles_sprite`, particles →
  `mu_world_particles_create`; OBJECT-owned particles and requests without a pose are refused and counted
  (`env->pre_counts`). `mu-render character --world-render` passes the weapons'/wing's saved poses and prints
  `pre_effects`/`pre_refused`. `mu_item_textures.c`'s probe host gets the four NULL fields.
- **Oracle** (`validate_renderchar.World`): CreateEffect `0x013c0f19` (thiscall on the effect manager `0x0a4ca430`,
  eight arguments) is now a recording stub like CreateSprite/CreateParticle. The new COLOR-carrying rows shift
  `validate_renderchar`'s colour sample onto a level-gated state of wing `0x23ac` (an earlier body) whose
  RenderObjDraw case calls it through `0x013c0e0a` (`0x017c630e`); unstubbed, the client faulted at `0x0095d4f1`.
  Recorded, its draws equal the C's (colours 480/480). A state that reached the unstubbed call always stopped the
  client, so no earlier passing comparison changes; the affected rows were rerun on it anyway.

## Effects routed vs refused

| Request (static sites over the 26 programs, loops unrolled) | Native consumer | Result |
|---|---|---|
| Bone sprites `0x0150e746` (150: `0x7f7a` 74, `0x7ef7` 50, `0x80ba` 14, `0x8458` 6, `0x7fe0` 4, `0x810a` 2) | sprite pool | routed |
| CreateSprite after TransformPosition (86: `0x7ef7` 62, `0x7f78` 24) | sprite pool | routed |
| CreateParticle `0x7ffd`/27, no owner (1, bow `0x1316`) | particle pool | routed; refused when the pool creates none |
| CreateParticle owned by the OBJECT (4: `0x810a`/17, `0x81cf`/0; wings `0x2384`/`0x2385`) | none | refused, counted |
| Any request on a bone outside the item skeleton (missing name, short skeleton), or without `env->item_bones` | none | refused, counted |

In the validator's random skeletons: 9,956 requests created bit for bit, 4,532 refused (missing names, short
skeletons), 520 rand draws, 182 states with the frustum flag clear.

## Checks

Env: `MU_RECOVERY_INTEGRATION=1`, `MU_GAME_ROOT="$HOME/Library/Application Support/MuTheMatrix/prefix/drive_c/MuTheMatrix"`,
`MU_SECTION3="$HOME/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin"`,
`MU_EVIDENCE_DIR`=the main checkout's `evidence`, `MU_LANG_DIR="$HOME/Documents/MTM/mu-mac-tools/native/scratch/lang"`,
`MU_LANG3_SNAPSHOT="$MU_LANG_DIR/live/lang3.bin"` (validate_fidelity), `MU_VALIDATOR_CACHE` = the shared cache.
All heavy steps `nice -n 10`.

| Check | Cases / result | Wall time |
|---|---|---:|
| Census of the 355 remaining types (scratch, four survey states, service log) | 91 pre-draw, 8 after-draw only, 220 none/rand only, 36 faults | 9 s |
| Reader over the effect types (`extract_pre`) | 40 of 91 read; the 26 listed reproduce the header (`--check`); the 43 part-17 programs' op rows unchanged | 7 s |
| Body-table generation (`gen_item_bodies`) with the 26 types | 1,300 → 1,326 rows; earlier rows unchanged (C-to-C below) | 882 s |
| Probe screening (scratch library per type, 292 states) | 26 of 29 fitting candidates pass (5 default, 21 extended, 17 of them carry); `0x1313`, `0x1317`, `0x1319` fail | 7 min |
| `validate_item_predraw --mutations` (new row, at `d45932fc`) | 9,256 comparisons, 0 mismatches (bodies 7,592; pre-draw 1,664: 9,956 requests bit for bit, 4,532 refusals, 520 rand draws, 182 flag-clear states); 14/14 mutants caught, none equivalent, all compiled, anchors once; both tables reproduce | 901 s |
| `validate_item_ownerfx --mutations` (its executor and the `subtract` anchor changed; at `d45932fc`) | 14,964 comparisons, 0 mismatches; 14/14 mutants caught (same detection counts as part 17) | 897 s |
| C-to-C, main `18ab0134` library vs this one: 1,691 survey types × 32 states × with/without rand | 108,224 cases; 106,560 identical, the 1,664 different ones are exactly the 26 new types | 4 s |
| Survey export (`classify_item_bodies --tables-dir`) | 1,691 types, 798 shapes; exactly 26 rows flip; complete shapes 556 → 572 | 72 s |
| `run_test_suites.py --affected origin/main` (`MU_RECOVERY_INTEGRATION=0`, 2 jobs, at `d45932fc`) | 6 suites, 1,259 tests, 0 failures, 185 skips | 289 s |
| Portable `test_item_predraw` + `test_item_ownerfx` | 9 tests, 2 private skips | 0.1 s |
| Native `test_native_renderchar` (new `test_weapon_pre_draw_program`: sword `0x0b27` 4 sprites/0 refused; bow `0x1311` 0/1; wing `0x2394` 0/8 on the synthetic skeleton) | pass | 0.3 s |
| Native `test_native_item_textures` (installed survey; 6b: pins unchanged, 13 white types, 0 missing bitmaps, 0 with a wearer: none of the 26 bodies is white or misses a bitmap) | 7/7 | 47 s |
| Build `nice -n 10 make -j4` (after the `3ecc205c` merge) | pass | 18 s |

6b: the changed shared symbols (`mu_rc_owner_host`, `mu_rc_owner_fx`, `mu_rc_fx_op`, `item_owner_fx.h`,
`item_bodies.h`, `mu_renderchar_env`) are used by the item validators, `validate_render_effects5` (ctypes structs
follow), `mu_item_textures.c` (initializer follows) and the native modules above; all ran.

### Affected existing rows, without mutants (`--no-mutants --cache --jobs 2`, at `9e234371`)

30 rows run 22:08-22:56 (48 min wall, load 5-9) after the `3ecc205c` merge; `validate_renderchar` again at `a4cf11bd`
after its colour sample was fixed (below). Counts equal the earlier lanes' reports. A second run of all 31 at
`d2a6105f` (CreateEffect recorded in the shared world) passed the same 30 and showed that the stub belongs only in
`compare_cases`' world (the back-carry extraction then finishes link states its table never had); `a4cf11bd` keeps
the shared world as at `9e234371`.

| Validator | Cases | Seconds |
|---|---:|---:|
| `validate_item_types` | 135,176 | 35.2 |
| `validate_item_hiddenmesh` | 116,281 | 380.7 |
| `validate_item_carry` | 114,388 | 677.0 |
| `validate_item_clusters` | 74,292 | 345.6 |
| `validate_item_expansion` | 52,172 | 292.8 |
| `validate_item_derived` | 36,252 | 266.5 |
| `validate_item_chains` | 35,346 | 252.0 |
| `validate_item_wings_next` | 33,622 | 229.5 |
| `validate_item_coverage` | 31,724 | 222.6 |
| `validate_item_quality` | 28,080 | 179.4 |
| `validate_item_scalars` | 26,154 | 178.1 |
| `validate_item_continuation` | 25,772 | 921.4 |
| `validate_item_gear` | 25,256 | 169.5 |
| `validate_item_ranked` | 17,736 | 870.5 |
| `validate_item_next` | 14,992 | 225.0 |
| `validate_item_product` | 2,874 | 53.4 |
| `validate_renderchar` (at `a4cf11bd`: items 500/500, colours 480/480, rank-5 480/480, back 100/100) | pass | 42.6 |
| `validate_fidelity` | pass | 59.7 |
| `validate_render_effects5/7/9/10/11/12/13/14/15/16` | 1,190 / 596 / 304 / 154 / 176 / 64 / 180 / 660 / 509 / 424 | 5.4 / 1.8 / 1.1 / 0.5 / 0.4 / 0.5 / 0.4 / 1.0 / 0.7 / 3.1 |
| `validate_app_polish1/2/4` | 752 / 1,028 / 10,485 | 19.1 / 3.0 / 28.9 |

`--list-affected origin/main` selects 49 rows. Run: the 31 rows above (they build `reconstructed/renderchar`,
import the generators, include `renderchar.h`/`mu_renderchar.h`, or name `native/core` for item effects) plus the
two mutant rows. Not run, with reason: `meshdraw`, `model_edge`, `model_light`, `movement`, `path`, `terrain`,
`terrain_remaining`, `viewport_monsters`, `worlds_f`, `session_party`, `audio_callers`, `audio_combat`,
`audio_domains`, `audio_items`, `audio_charsel` reach `mu_renderchar.c`/`mu_item_textures.c` only through the
native archive; the native change only acts for the 26 new types with a particle pool (`mu_rc_item_pre_fx`), and
the texture probe's host keeps `item_transform` NULL. `icarus_c2` builds every `reconstructed/*` directory but
never calls the item library.

## Byte identity and renders

- C-to-C (above): no earlier type's stream changes, with or without a rand context.
- `mu-render ui inventory`, installed data, `MU_LANG_DIR` set, time 123456; "before" from main `3ecc205c` (temporary
  worktree). Control codes 0,1,2,3,7,8,4116,135 are byte-identical (`b38597f2…0a6a`, 1,676 triangles). New types
  (codes 102, 2091, 3170, 6318, 1078, 6187 = `0x0b4c`, `0x1311`, `0x1748`, `0x2394`, `0x0f1c`, `0x2311`; one does
  not fit the grid), before `775de48a…53ed` at every level (the plain fallback ignores it):
  - level 0: triangles 3,916 → 3,963, 2,955 pixels change, → `50446a8b…9d9a`;
  - level 9: triangles 3,916 → 10,755, 3,275 pixels change, → `3e8eb3b7…80f6`;
  - level 13: triangles 3,916 → 17,547, 3,486 pixels change, → `84e13c8a…2854`.
  - Window-only crops (before | after) in `~/Documents/MTM/mu-mac-tools/native/renders/render-items-002r/`
    (`crop_0.png`, `crop_9.png`, `crop_13.png`, 12-14 KB): the plain fallback becomes the recipes' lit and glow
    passes. Offline native renders, not original-client pixel comparisons. Inventory items have no particle pool,
    so no effects appear there.
- `mu-render character --world-render` on a synthetic 12-bone skeleton: sword `0x0b27` creates 4 bone sprites, 0
  refused; bow `0x1311` refuses its one named-bone request (`a02` absent); wing `0x2394` refuses its eight
  (`Point001`..`Point008` absent).

## Limits

- 329 bodies remain. Pre-draw programs run only with an item-bone host and the particle pools: the native
  callers outside `mu-render character` (world players/hero/actors/items, other lanes' code) do not pass
  `env->item_bones` yet, so their requests are refused and counted while the rand stream is kept.
- The TestFrustrum2D flag is 1 natively (a drawn item is in view); the client tests the 2D frustum at the OBJECT.
- Native sprites are not owner-bound (as part 17); OBJECT-owned particles have no native record.
- Bone indices outside the item skeleton are refused (the client reads the matrix before BoneTransform for -1, or
  stale bones past the count).
- Domain: the caller's OBJECT is the item's own object (`+0x5c` = type), as RenderLinkItem passes it.

## Next groups

1. **The 51 unread pre-draw types**: loops that create joints (CreateJoint `0x0153b02c`; the native joint pool
   exists, `mu_world_particles_joint`), integer clock chains with branches (`0x0b4f`..`0x0b53`), owner transforms
   `0x012b678d` on a named item bone (`0x0f1e`, `0x174a`, the wings `0x23a8`/`0x23a9`), light-pointer reads, more
   than 1,024 registers (`0x23ef`, `0x2400`, `0x2405`, `0x24be`, `0x24bf`), services before and after the draws
   (`0x0f23`..`0x0f2b`); plus the bows `0x1313`, `0x1317`, `0x1319` (fit the default probes, fail the 292-state
   comparison under every option) and the 11 read types whose draws fit no recipe (`0x0b29`, `0x0b4d`, `0x1314`,
   `0x230d`, `0x23ed`, `0x23ee`, `0x23fe`, `0x23ff`, `0x2403`, `0x2404`, `0x2497`).
2. **The 31 rank-5 set parts faulting in strlen `0x0195a4e0`** in the rank-5 pose world (not attempted here).
3. The 54 helper-group-count types; native callers passing `env->item_bones` (world parts lanes).

## Release

Steward validators: validate_item_predraw (new; ran with mutants at `d45932fc`), validate_item_ownerfx (ran with
mutants at `d45932fc`), validate_item_types, validate_item_gear, validate_item_ranked, validate_item_continuation,
validate_item_expansion, validate_item_clusters, validate_item_next, validate_item_coverage, validate_item_wings_next,
validate_item_scalars, validate_item_chains, validate_item_carry, validate_item_quality, validate_item_product,
validate_item_derived, validate_item_hiddenmesh, validate_render_effects5, validate_render_effects7,
validate_render_effects9, validate_render_effects10, validate_render_effects11, validate_render_effects12,
validate_render_effects13, validate_render_effects14, validate_render_effects15, validate_render_effects16,
validate_app_polish1, validate_app_polish2, validate_app_polish4, validate_fidelity (ran at `9e234371`, no mutants),
validate_renderchar (ran at `a4cf11bd`, no mutants). After `d45932fc` the compiled inputs of the two mutant rows
are unchanged (the merge brought only `validators.toml`; `validate_renderchar`'s change is a world class only
`compare_cases` uses). Mutants: none needed beyond those two rows. Env as under Checks.

Cleanup removes `mu-mac-tools/native/scratch/render-items-002r/` and the build directories. The crops in
`renders/render-items-002r/` are the only kept artifacts (small). The worktree stays until the steward merges.
No new input needs to be kept.
