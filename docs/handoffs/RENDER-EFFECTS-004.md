# RENDER-EFFECTS-004

Implements Rageful Blow's ordinary-world effect chain (the last missing primary
skill), Triple Shot's fan through the original CreateArrows/CreateArrow, and
Spirit of Guardian's wing effect as a pet cosmetic consumer. Primary native routes
rise **18/23 to 20/23**; weighted primary coverage **56/77 to 65/77** (72.7% to
84.4%). [Finding](../research/client-render-effects-004.md),
[coverage inventory](../research/client-skill-visual-coverage.md).

Branch `claude/render-effects-004` from main `147005d`. No live game, no network,
no perf/mesh/scene changes. Fixed pools and load-time models only; no per-frame
allocation. Checkpoints pushed at f248d35, 9821de5, 80e5cde and 53e35eb.

## Verified checks

- `scripts/validate_render_effects4.py --cases 1000 --mutations`: **32,000**
  original-instruction comparisons, zero mismatches: CreateEffect 16,000 (16 kinds),
  MoveEffect 10,000, item initialiser 1,000, weapon draw 1,000, CreateArrows 2,000,
  CreateArrow 2,000. **15/15** compiled production-C mutants caught (counts in the
  finding). Registered as `validate_render_effects4` (60-case gate run: 1,920 cases).
- Existing validators after the record/object layout additions: `validate_skill_fx`
  (300 cases per family, all equal), `validate_render_effects` and
  `validate_render_effects3` (100 cases, all equal; their mutants still compile).
- Native tests (`native/tests/test_render_effects.py`, private checks on): Rageful Blow
  creates all ten types, twenty quake pieces per ring, eight joints, one unsent request,
  zero unsupported emissions/hits/kills, unchanged target HP; removing the piece models
  changes pixels. Triple Shot creates three Arrow01 shots. The wing creates one effect
  per drawn frame, keeps 25 live, and removing its model changes pixels.
  `test_native_combat`, `test_native_pets` and `reconstructed/combat` tests pass.
- Installed-data headless GL frames inspected: Rageful Blow impact (24, 28) and quake
  ring (40), Triple Shot fan (23), Guardian wing crop (50). Representative PNG SHA-256
  (local, renders/render-effects-004): rageful-24 `a396aeb8…`, rageful-28 `73babb6f…`,
  rageful-40 `d5d14397…`, triple-shot-23 `ea664d79…`, wing-crop `70f3d940…`.
- Hash preservation: Fire Ball (skill 4, staff) and Twisting Slash (41, sword) software
  frames at frame 21 on installed Lorencia are byte-identical between main `147005d`
  runtime sources and this branch: `88b81858…cf58` and `989dce94…b393`. No existing hash
  pin changed. Rageful Blow, Triple Shot (fan angles, arrow order and serial) and the
  pets' 0x460 effect intentionally change pixels/RNG/terrain lights.

## Integration notes

- `mu_jt_object` gains `angle` (+0x164) and `level` (+0x41); `mu_sfx_effect` gains the
  impact point, the second angle vector, `+0x04`, `+0xc0` and `+0x194`. Appended fields
  only; the native Makefile does not track these headers, so rebuild `native/build`
  from clean after merging.
- `mu_combat`: the 32-line combat log becomes 48 lines and the nine Rageful Blow model
  lookups log one summary line. Without this the fixture's death line was pushed out of
  the log (caught by `test_native_combat`).
- Shared hooks touched minimally: `mu_world_pets.c` r_effect forwards scale/key;
  `mu_particles.c` adds one effect model (count 11 → 12). No `renderchar.c`,
  `item_bodies.h` or `gen_item_bodies.py` change (RENDER-ITEMS-002K lane untouched).

## Remaining work

- Rank-5 item owner effects (scope item 3) were **not started**: they continue inside the
  rank-5 body after `0x0174a489` (readable OBJECT bones 35/26 through `+0x318`, particles
  `0x84e2`/`0x83de`, sprites `0x7fdd` shared with Uruk's `0x7fdd/3`, level-9 overlays and
  pose-state effects). That code sits in the body executor RENDER-ITEMS-002K owns now;
  it needs a hand-over from that lane or a separate owner-effect hook agreed with it.
- Arrows: other bows' arrow models (0x43c..0x617) need their create/move bodies; bow
  0x12f9's bone sparks; master-tree 0x1a2, skill-tree value, mastery and item option 0x54
  are authored inputs. The normal bow attack keeps its earlier single-arrow adapter.
- Buff auras (Greater Defense/Damage) need the authoritative buff feed; Death Stab trails
  and master/later-class selectors remain unaudited.
- Rageful Blow's special-world branches and the weapon's item-level glow; Rudolph's 0x3fa
  and the pets' particle kinds; live original-image comparison.

## Cleanup

Only the ignored `tools/python` and `evidence` symlinks are used; none is staged. No new
private input needs retention. After merge: remove renders/render-effects-004,
scratch/render-effects-004, `native/build`, this worktree and the local branch.
