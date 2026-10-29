# RENDER-EFFECTS-005

This lane implements two items:

1. **Rank-5 item owner effects (all 19 types, all four type-list variants).** Owner bones 35/26,
   the `0x84e2` and `0x83de` particles, the `0x7fdd` flareBlue sprite and the level-9 overlay
   passes, added through a separate owner hook beside the body executor.
2. **Effect `0x43a` (DungeonStone)**, which Deep Dungeon object type 52 requests. It is consumed
   instead of refused.

Other bows' arrows, bow 0x12f9's sparks, Rudolph's 0x3fa and the pet particle kinds were
measured but not implemented (see "Remaining work"). [Finding](../research/client-render-effects-005.md).

Branch `claude/render-effects-005` (Claude Opus 5.5), from main `9d21ebb`. No live game, network,
perf, mesh or scene changes. Fixed pools only; no per-frame allocation. Checkpoints were pushed at
0d87850, then the native-host, test and DungeonStone commits.

## Coverage

| Measure | Before | After |
|---|---|---|
| Skill primary routes | 20/23 | 20/23 (unchanged; these are item/world effects with no skill credit) |
| Weighted skill coverage | 65/77 | 65/77 |
| Item bodies | 967/1,674 | 967/1,674 (unchanged) |
| Skins | 17/17 | 17/17 |
| Rank-5 owner effects | 0/19 types | 19/19 types (all four variants) |
| Deep Dungeon keyed effect | refused and counted | consumed |
| Native particle kinds | — | +2 (0x84e2/0, 0x83de/4) |
| Native effect kinds | — | +1 (0x43a/0) |

## Verified checks

`scripts/validate_render_effects5.py --cases 200 --particle-cases 2000 --stone-cases 500
--mutations` gives **10,800** original-instruction comparisons, zero mismatches:

| Family | Cases |
|---|---:|
| Owner (full RenderObjDraw, 19 types) | 3,800 |
| Particle create / move / render (0x84e2/0, 0x83de/4) | 2,000 each |
| DungeonStone create / move | 500 each |

Both LoadBitmap registrations match. **25/25** compiled production-C mutants are caught; the
detection counts are in the finding.

The manifest row `validate_render_effects5` is owned by
`native/tests/test_render_effects.py::RenderEffects.test_rank5_owner_original_instructions_and_compiled_mutants`.
Its gate run gives 1,190 cases and 25/25 mutants.

Existing validators were rerun on this branch:

- `validate_item_next --mutations`: 14,992 cases, all equal, 9/9 mutants. This is the rank-5
  no-owner domain, unchanged.
- `validate_worlds_m --cases 60 --mutations`: passes. Its mutant build copies `particles.c`,
  which now includes `owner_fx.inc` through `-I`.

Native tests:

- `test_native_renderchar.test_rank5_owner_effects_follow_owner_bones` (new). It checks:
  - unlit gives 0 effects; lit gives 6 per frame (18 over three frames);
  - a 35-bone owner stops before the effects;
  - +9 at quality 5 adds exactly 2 overlay passes; quality 1 adds none.
- `worlds_n_host`: type 52 is now forwarded (effect events 30..110, zero unsupported).
- `test_native_worlds_n`, `test_native_renderchar` (15 tests) and `test_render_effects` pass.

## Native frames inspected (local, renders/render-effects-005, deleted after merge)

`mu-render character` with the installed Player skeleton as the authored owner:

- **`ArmorMale161_elf.bmd` as 0x1c26 (blue).** Frames compared with and without the owner
  (owner bone count forced to 0 in a scratch build). In frame 7 the lighting01_10cha bolts sit at
  the shoulder points and the flareBlue glint and smoke_line03 smoke appear; 13,726 pixels change.
  Frame 0 changes by 8,812 pixels: the sprite is visible at creation, the particles start at
  scale 0.
- **`ArmorMale162.bmd` as 0x1c2b at +11.** Passes rise 48 → 54 over six frames (one overlay per
  frame) and the effects appear.
- **Saturation.** The lit rank-5 body saturates white natively because its 0x84d9.. textures are
  not in the native item texture set. That is the existing RENDER-ITEMS limit, not this lane's.
- **DungeonStone** is created with scale 0.0 by the original call, so it has no visible pixels
  (static inference from RenderEffects). The native evidence is effect-pool and rand consumption,
  not pixels.

## Hash and behavior changes (intended)

- **Owner frames.** Rank-5 lit body parts drawn with an owner of more than 35 bones now emit owner
  effects. This changes those frames and the shared random stream. The no-owner and unlit
  domains are unchanged.
- **Particle steps.** `mu-render character` steps particles between frames. Frame 0, whose SHA is
  printed, is unchanged. Later frames of link-effect particle types now move as in the client
  (they were previously frozen).
- **Deep Dungeon.** `move_unsupported` no longer counts type 52; `effect_events` does.
- **No existing hash pin changed.** The Fire Ball and Twisting Slash combat paths are untouched
  (`skill_fx.c` only adds the 0x43a case and its admission).

## Integration notes (shared files, minimal hooks)

**`reconstructed/particles/particles.c`.** Five one-line hooks: include, kind, create, move and
render. The bodies live in `owner_fx.inc`.

**`reconstructed/renderchar/renderchar.c`.** Three small edits; the body executor's rules are not
changed:

- a thread-local owner host and a forward declaration;
- the end of `rank5_body` calls the owner hook only when that host is set (it replaces the former
  "outside this no-owner context" comment);
- `#include "rank5_owner.inc"` at the end of the file.

**`native/core/mu_particles.{c,h}`.**

- Two effect bitmaps (0x83de, 0x84e2) are inserted after lightmarks. The relative-to-end slots
  used by the consumers, worlds-L and worlds-M hosts are unchanged. `MU_WORLD_PT_BITMAPS` goes
  60 → 62.
- One effect model entry (DungeonStone, worlds 116–120). `MU_WORLD_FX_MODELS` goes 12 → 13.
- On conflicts, keep both sides and recount these two constants.

**Other files.**

- `mu_renderchar.{c,h}`: a new `mu_renderchar_draw_item_owner`. `mu_renderchar_draw_item` is
  unchanged for its callers.
- `mu_objects_runtime.c`: the Deep Dungeon event goes to `effect_scaled`.
- The native Makefile does not track the `.inc` files. Rebuild `native/build` from clean after
  merging.

**Coordination with RENDER-WORLDS-G2.** `0x43a` is DungeonStone, not the brazier fire, so nothing
is left for G2 from this item. The Deep Dungeon brazier visuals remain G2's.

## Remaining work

- **Other bows' arrows, 0x43c–0x617 (32 models).**
  - Create is one shared body `0x013cb34d..0x013cd66f` with per-type branches: blend mesh
    1/−2/0/−1 by type, lifetime/subtype branches for 0x45c/0x45d/0x45e/0x442, angle changes for
    0x47f.
  - Each move differs. Some add sprites (0x443, 0x60a, 0x616), some scale ramps (0x60e..0x614),
    some light changes (0x45b, 0x471), some position steps (0x458, 0x474, 0x441, 0x47f, 0x45a,
    0x525, 0x60d).
  - Routing all 32 through Arrow01's case matches **0 of 32** types (40 cases each, both
    families). A scratch library proved this; it was not kept.
- **Bow 0x12f9's fifteen bone sparks** (`0x0158dfdc`).
- **Rudolph's 0x3fa** (shared `0x013de0ff` body) and the pet particle kinds. Cosmetic subset only.
- **Rank-5 group 9.** The raw group-9 path `0x0174a4bc` is outside `mu_rc_item_rank5`.
- **Owner binding.** No equipment feed, so native owners are authored. The client binds the
  sprite to the OBJECT; native sprites are owner-free.
- **Live comparison.** None against the original client.

## Cleanup

Only the ignored `tools/python` and `evidence` symlinks are used (excluded through
`info/exclude`); neither is staged. No new private input needs to be kept. After merge, remove:

- `renders/render-effects-005` and `scratch/render-effects-005`;
- `native/build`;
- this worktree and the local branch.
