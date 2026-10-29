# RENDER-ITEMS-002 part 12

Base `f4eba8a`, branch/worktree `claude/render-items-002l` (Claude Opus 5.5). Checkpoints are
pushed. Only this lane is edited and built. No live client, launcher or hosted workflow is used.

## Coverage and implementation

Bounded bodies increase **967 to 1,053 of 1,674**, adding **86 types**. Skins stay **17/17**. Links
increase **seventeen targets/twenty-two types to eighteen/twenty-four**. **621 bodies remain.**
Exact membership is in `gen_item_bodies.CHAIN_TYPES` (66) and `LEVEL_TYPES` (20), and in both TSVs.

Selection followed the survey. A rerun of the part-11 screen classified the first failure of all
664 remaining non-stopping types; the table is in the
[finding](../research/client-render-items.md#part-12-clock-chain-and-level-split-bodies-two-link-rows-render-items-002l).
The largest bounded group was draw words computed from the clock: 196 types, 132 of them UV.

- **Clock chains (66 types).** The probes record every executed block that reads the clock
  global `0x06fce370`. `slice_block` statically walks the pinned bytes into a linear op chain with
  folded data constants, immediates, the signed remainder/quotient idioms (bytes checked exactly),
  `cdq; idiv`, and entry locals. Each entry local must also be stored as that immediate in the
  text. These cover integer UV clocks with any divisor, atlas frames with other periods and
  columns, and locals written in other branches before the block. Chains are program kind 3 in
  `mu_rc_body_scalars`, with up to nine op/constant pairs. `renderchar.c::clock_program`
  evaluates them inside the body executor. 106 types fitted the probes and 66 passed the full
  comparison.
- **Level split (20 types).** The 72 level-dependent count shapes were tried with the part-9 phase
  6/7 split. 55 fitted and 20 passed: the `0x1a25..0x2232` armour neighbours of the part-9 types.
- **Link table additions.** All 11,722 item/skin types were swept through RenderLinkItem
  `0x012bd910`. `0x0f0b` reuses `0x0eed`'s pulse rule at target `0x012cbb43`. `0x0ef3` is a
  sprite-chain row at the new target `0x012cc846`. Each needed a generator row and one line in the
  native attachment hook's type list (`native/core/mu_renderchar.c`).

Helper programs keep their part-11 order and chains follow, so all 948 earlier rows keep
identical recipes, flags and programs after re-indexing. The part-11 validator now counts only
part-11 rows; its results are unchanged. Outside the body executor, `renderchar.c` only gained the
updated chain-site comment. No texture registration or loading changed (RENDER-ITEMS-TEX-001).

## Checks

`scripts/validate_item_chains.py --mutations` has a manifest row and the private test
`ItemChains.test_original_instructions`. It passes **35,346 comparisons, zero mismatches**: 25,112
full body streams (86 types times 292 states, body random trapped), 2,714 divisor/INT_MIN/2^31/-0.0
clock edges across 59 distinct chains, 6,720 level-split boundary cases and 800 link caller cases.
All **17/17 separately compiled mutants** are caught (counts in the finding). The body, link and
pulse tables reproduce.

Inherited validators rerun on the final source: part 11 `validate_item_scalars` **26,154 cases,
zero mismatches, 11/11 mutants**; part 10 `validate_item_wings_next` **33,622 cases, zero
mismatches, 12/12 mutants**, both with identical counts. Together with this part:
**95,122 instruction comparisons, zero mismatches, 40/40 mutants**.

Compiled C-to-C, base `f4eba8a` library against this one: **952 earlier body/skin types in
30,464 random cases** and **440 link cases**, zero mismatches. Over all 1,691 survey types,
admission changes for exactly the 86 new types. Portable renderchar: **63 tests, fifteen
private skips**. The new portable tests check admission and refusal outside the domain, that every
chain reaches a draw word at eight clocks including INT_MIN/2^31, and the signed idioms.

## Native gallery

GALLERY

## Limits and coordination

Not claimed: body-owned effects/particles (157 types), immediate `glColor` calls (93), body light
that depends on quality branches, non-aligned helper phases (49) and the 89 probe-fitting
refusals. `0x12fa` (product of two scalars) and `0xafc` (further clock term) are not plain link
rows. Laser/17 and the clock/bone-state links stay partial. Rank-5 owner effects, Muun and nested
map-object tables, and earlier record, buff, selection, shadow, override, NewUI and Box of Luck
limits remain.

## Release

RELEASE
