# RENDER-EFFECTS-034

WIP. Branch `claude/render-effects-034`, started from RENDER-EFFECTS-033 `35ae89fe` (PR #403, which
already contains main `c5b9d5ca`). Implementation by Claude Fable 5.2, no subagents.

## WIP (checkpoint 1)

Done:
- Per-pair refusal ledger in the world particle module (`refused_kinds`, report line
  `{"world_unsupported": [[routine, type, subtype, count], ...]}`), next to the existing totals.
- Refusal census before any consumer change: 46 default views (default draw and draw-all) and 31
  skill scenes. World views refuse particle `0x7ef7/11` (Elbeland) and `0x8016/5` (Swamp of Calmness)
  only; skill scenes refuse the Blood Storm rest, Crescent `0x49e/0`, Fire Breath `0x8001/0` and
  Twisting Slash `0x454/-1,1..4` with real assets.
- Original instruction paths of the particle group traced (create / move / render per pair).

Left: particle group (19 pairs), joints `0x7f7c/8`, `0x7f7c/19`, `0x7fd5/4`, `0x7f7d/11`, sprite
bitmap bindings `0x810d`, `0x8003`, grouped verifier with mutants, fixtures, identity sweep, docs.
The 17 effect-side ids are for RENDER-EFFECTS-036 unless time remains (orchestrator order;
`reconstructed/combat` and `native/core/mu_combat.c` belong to RENDER-EFFECTS-035).

Next step: add `reconstructed/particles/effects34_kinds.inc` with the traced cases and
`scripts/validate_render_effects34.py` (pattern of `validate_render_effects31.py`).
