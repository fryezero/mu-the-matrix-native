# RENDER-ITEMS-002Q

Branched from `claude/render-items-002p` (`e198d35e`) while #310 was queued; merged main `ad2968fc` (#310, #309)
and `7e6a9292` (#311). Branch/worktree `claude/render-items-002q` (Claude Opus 5.5). No live client, launcher,
network or hosted workflow. No full gate in the lane (2026-11-04 test budget).

Scope: RENDER-ITEMS-002 part 17, the first group of part 16's "Next groups": the armour owner-bone effect bodies.
[Finding](../research/client-render-items.md#part-17-owner-effect-programs-of-the-armour-bodies-render-items-002q).

## Result

Bodies **1,276 → 1,319 of 1,674** (+43: the 38 worn chest pieces `0x1bc3..0x1c78` and the helms `0x19f4`,
`0x19fa`, `0x1a00`, `0x1a1f`, `0x1a78`). Skins 17/17, links eighteen targets/twenty-four types. **355 bodies
remain.** Survey: 798 shapes, complete shapes 543 → 556; both TSVs flip exactly the 43 types.

- **Reader** (`scripts/gen_item_owner_fx.py` → `reconstructed/renderchar/item_owner_fx.h`). Unicorn locates
  each type's effect block in RenderPartObjectBody and snapshots the frame at its start in four survey states.
  An abstract interpreter then reads the block's MSVC idioms into an op program: binary32 constants (folded),
  owner transform `0x012b678d`, CreateSprite `0x01692eb7`, CreateParticle `0x0168fafd`, `rand() % 2` and
  `% 5` gates, `0x011ff622` ranges, vec3 add/subtract/normalize and the OBJECT angle. Any other instruction,
  call, operand or a state-dependent frame word refuses the type. Thirteen blocks, seven distinct programs.
- **Executor** (`owner_fx.inc`, included by `renderchar.c`). It runs after the type's base body draws (phases
  0/5/6/7), only through `mu_rc_item_draws_owner`, with the host's random in client order. It runs only when
  the program's highest bone is below both `host->bones` and the new `host->item_bones`.
  `mu_rc_item_owner_fx(type)` reports the need.
- **ABI** (appended fields): `mu_rc_owner_fx.angle[3]` (zero for the rank-5 block); `mu_rc_owner_host.item_bones`
  and `.angle[3]` (OBJECT +0x164). `validate_render_effects5`'s ctypes structs follow; the texture probe passes
  `item_bones` 0 (draws only).
- **Draws** (`gen_item_bodies.OWNER_FX_TYPES`). The client's effect requests are set aside in the probes; all 43
  fit the generic recipes.
- **Native** (`mu_renderchar.c`, `mu-render character --world-render`). Requests go to the existing consumers:
  `mu_world_particles_sprite` and `mu_world_particles_create`, which now receives the request's angle.
  `mu_renderchar_owner` gains `refused` and the OBJECT angle; the tool prints `owner_refused` and opens the
  particle pool for owner-effect types.

## Effects routed vs refused

| Request (sites in the seven programs) | Native consumer | Result |
|---|---|---|
| CreateSprite `0x7f7a` (15), `0x8109` (4), `0x810a` (5) | sprite pool | routed |
| CreateParticle `0x810a`/7 (4, OBJECT angle) | none | refused, counted |
| CreateParticle `0x810a`/15 (4, normalized bone-19→26 direction) | none | refused, counted |
| CreateParticle `0x7f26`/0x26 (2, OBJECT angle) | none | refused, counted |
| Programs outside the bone domain (part/OBJECT model without the highest bone) | none | refused, counted once |

Native check (synthetic 50-bone part, `0x1bc3`): frame 0 creates 9 sprites (odd gate), three frames 27 sprites
and 1 refused particle; a 35-bone part creates nothing and counts 1 refusal. The missing particle kinds
(`0x810a`/7, `0x810a`/15, `0x7f26`/0x26 through CreateParticle) belong to the RENDER-EFFECTS lanes.

## Checks

Env: `MU_RECOVERY_INTEGRATION=1`, `MU_GAME_ROOT="$HOME/Library/Application Support/MuTheMatrix/prefix/drive_c/MuTheMatrix"`,
`MU_SECTION3="$HOME/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin"`,
`MU_EVIDENCE_DIR`=the main checkout's `evidence`, `MU_LANG_DIR="$HOME/Documents/MTM/mu-mac-tools/native/scratch/lang"`,
`MU_LANG3_SNAPSHOT="$MU_LANG_DIR/live/lang3.bin"` (validate_fidelity), `MU_VALIDATOR_CACHE` = the shared cache.
All heavy steps `nice -n 10`.

| Check | Cases / result | Wall time |
|---|---|---:|
| Reader, 43 types (+ refused `0x0f1e`, `0x174a`, `0x23a8`, `0x23a9`, `0x24c6`) | 43 read, 7 programs; `--check` reproduces the header | 3 s |
| Body-table generation with the 43 types | 1,257 → 1,300 rows, all fit; earlier rows unchanged (C-to-C below) | 627 s |
| `validate_item_ownerfx --mutations` (new row, at `121f24f7`) | 14,964 comparisons, 0 mismatches; 14/14 mutants caught, none equivalent, all compiled | 671 s |
| C-to-C, main `ad2968fc` library vs this one: 1,691 survey types × 32 states × with/without rand | 108,224 cases; 105,472 identical; the 2,752 different ones are exactly the 43 new types | 4 s |
| Survey export (`classify_item_bodies --tables-dir`) | 1,691 types, 798 shapes; exactly 43 rows flip, complete shapes 543 → 556 | 74 s |
| Portable `reconstructed/renderchar` suite | 86 tests, 65 pass, 21 private skips | 1 s |
| Native `test_native_renderchar` (+ new owner-effect test), `_items`, `_hud`, `test_inventory_skin`, `test_native_character` | 37/37 | 48 s |
| Native `test_native_item_textures` (installed survey; pins unchanged: 13 white types, 0 missing bitmaps, 0 with a wearer) | 7/7 | 55 s |
| Native `test_native_fidelity` (loads `librenderchar`) | 12, 1 skip | 11 s |
| Build `nice -n 10 make -j4` | pass | 11 s |
| After the `7e6a9292` merge (#311 changed native/core): build, the five native modules again, audit | build pass; 37/37; 1,965 staged files, 0 rejected | 11 s / 42 s / 19 s |

6b: the changed shared symbols (`mu_rc_owner_fx`, `mu_rc_owner_host`, `mu_renderchar_owner`, `owner_effects`,
`item_bodies.h`) are used by the modules above, the item validators and `validate_render_effects5`; all ran.
The texture survey's pinned counts are unchanged: the 43 bodies now draw their recipes and none of them is
white or missing a bitmap.

### Affected existing rows, without mutants (`--no-mutants --cache --jobs 2`, at `121f24f7`)

30 rows, run 13:57-14:35 (`run_validators.py --private --no-mutants --cache --jobs 2`), load 7-17. Counts equal
the earlier lanes' reports.

| Validator | Cases | Seconds |
|---|---:|---:|
| `validate_item_types` | 135,176 | 36.1 |
| `validate_item_hiddenmesh` | 116,281 | 506.3 |
| `validate_item_carry` | 114,388 | 528.5 |
| `validate_item_clusters` | 74,292 | 348.4 |
| `validate_item_expansion` | 52,172 | 266.5 |
| `validate_item_derived` | 36,252 | 199.4 |
| `validate_item_chains` | 35,346 | 211.1 |
| `validate_item_wings_next` | 33,622 | 202.0 |
| `validate_item_coverage` | 31,724 | 177.0 |
| `validate_item_quality` | 28,080 | 135.7 |
| `validate_item_scalars` | 26,154 | 152.3 |
| `validate_item_continuation` | 25,772 | 142.2 |
| `validate_item_gear` | 25,256 | 170.2 |
| `validate_item_ranked` | 17,736 | 105.5 |
| `validate_item_next` | 14,992 | 182.4 |
| `validate_item_product` | 2,874 | 42.5 |
| `validate_renderchar` | pass | 63.2 |
| `validate_fidelity` | pass | 84.0 |
| `validate_render_effects5/7/9/10/11/12/13/14/15` | 1,190 / 596 / 304 / 154 / 176 / 64 / 180 / 660 / 509 | 4.2 / 1.8 / 1.2 / 0.7 / 0.3 / 0.3 / 0.4 / 1.0 / 0.6 |
| `validate_app_polish1/2/4` | 752 / 1,028 / 10,485 | 17.2 / 2.8 / 28.1 |

`--list-affected origin/main` selects every row, because `scripts/classify_item_bodies.py` is an unmapped
input (it only adds `OWNER_FX_TYPES` to the survey's union). The rows above build `reconstructed/renderchar` or
import the generator, include `renderchar.h`/`mu_renderchar.h` (app_polish2/4), or name `native/core`
(render_effects9-15, app_polish1). The `audio_*`, `meshdraw`, `model_edge`, `model_light`, `terrain` and
`viewport_monsters` rows reach `mu_renderchar.c` only through the native archive and never call the item
executor or the owner path.

## Byte identity and renders

- C-to-C above: no earlier type's stream changes, with or without a rand context.
- `mu-render ui inventory`, installed data, `MU_LANG_DIR` set, time 123456; "before" from main `ad2968fc`.
  Control codes 0,1,2,3,7,8,4116,135 are byte-identical (`b38597f2…0a6a`, 1,676 triangles). New types (codes
  4317, 4318, 4366, 4443, 3854 = `0x1bc3`, `0x1bc4`, `0x1bf4`, `0x1c41`, `0x19f4`):
  - level 0: triangles 4,275 → 6,651, 859 pixels change, `e8fa736d…ea72` → `033e2836…04a6`;
  - level 13: triangles 4,275 → 37,379, 4,709 pixels change, → `7927adfd…5403` (before, the refused fallback
    ignored the level);
  - level 9, adding `0x1bf0` (code 4362) and the generic, unchanged `0x1bd4` (code 4334): triangles 8,180 →
    30,648, 5,424 pixels change.
  - Window-only crops (before | after) in `~/Documents/MTM/mu-mac-tools/native/renders/render-items-002q/`
    (`crop_0.png`, `crop_9.png`, `crop_13.png`, 18-30 KB): the dark refused fallback becomes the armour's lit
    and glow passes. Offline native renders, not original-client pixel comparisons. Inventory items have no
    owner host, so no effects appear there.

## Limits

- 355 bodies remain. Effects run only for worn parts (owner host); inventory/ground bodies create none (the
  client would, at BoneTransform positions).
- States whose part or OBJECT model lacks the program's highest bone are refused (no effects, no rand).
- The three particle kinds above have no native consumer yet (counted as `owner_refused`).

## Next groups

1. **Effects before the body helper** (RenderObjDraw's own type switch): `0x0f1e`, `0x174a`, the wings
   `0x23a8`/`0x23a9`, and 76 of the 80 traced bone-sprite types. The reader needs a block start at the case
   label (the first jump-entered basic block before the first effect, found by a block trace). The executor
   needs a pre-draw hook in `mu_rc_item_draws_*`, and the bone sprites (`0x0150e746`: CreateSprite at
   TransformPosition of BoneTransform[bone] with the item model's scale/origin, no bone check) need an
   item-bone host: the item's own posed bones plus named-bone lookups `0x012bd35a`, on the native weapon/wing
   path.
2. **Native particle kinds** `0x810a`/7, `0x810a`/15, `0x7f26`/0x26 (RENDER-EFFECTS lanes), so the armour
   particles stop being refusals.
3. **Rank-5-set parts faulting in strlen** (31) in the rank-5 pose world, then the helper-group count types (54).

## Release

Steward validators: validate_item_ownerfx (ran with mutants at `121f24f7`), validate_item_types, validate_item_gear, validate_item_ranked, validate_item_continuation, validate_item_expansion, validate_item_clusters, validate_item_next, validate_item_coverage, validate_item_wings_next, validate_item_scalars, validate_item_chains, validate_item_carry, validate_item_quality, validate_item_product, validate_item_derived, validate_item_hiddenmesh, validate_renderchar, validate_render_effects5, validate_render_effects7, validate_render_effects9, validate_render_effects10, validate_render_effects11, validate_render_effects12, validate_render_effects13, validate_render_effects14, validate_render_effects15, validate_app_polish1, validate_app_polish2, validate_app_polish4, validate_fidelity (ran at `121f24f7`, no
mutants). Mutants: none needed beyond validate_item_ownerfx's. Env as under Checks.

Cleanup removes `mu-mac-tools/native/scratch/render-items-002q/`, the build directories and the temporary main
worktree `worktrees/render-items-002q-base`. The three crops in `renders/render-items-002q/` are the only kept
artifacts (small). The worktree stays until the steward merges. No new input needs to be kept.
