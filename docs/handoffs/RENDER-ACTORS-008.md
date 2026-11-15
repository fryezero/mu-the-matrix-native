# RENDER-ACTORS-008

## WIP checkpoint (2026-11-15 16:40, not PR-ready)

Branch `claude/render-actors-008`, stacked on ACTORS-007 (`origin/codex/render-actors-007`, PR #405).

**Done**

- Request recorder `scripts/actor_caller_requests.py` and the published table
  `docs/research/actor-caller-requests.csv` (ids, anchors, lights, link services, native consumer yes/no).
- Fifth generation is final: 186 checked group plans (138 + 48), census 775 checked / 169 incomplete /
  80 refused, 73 caller sprite requests on 33 rows, 14 link-effect rows (item `0x10f0`), all families equal.
  Tables, decisions, groups, request table and both census CSVs are regenerated from that run.
- Corrections to ACTORS-007: RenderLinkItem passes level `<< 3` to RenderObjDraw; classes 1/5/10 are
  object-bone sprites and are admitted.
- The sixteen Monster71/72 rows use `Npc/` textures in worlds 18..23, 53 and 97 and RenderCharacter adds
  RenderPartObject model `0xa2a` there: they stay incomplete with that reason.
- Portable actor tests pass (`native.tests.test_actor_groups` has the new request test).

**Left**

- The one run with compiled mutants (`--mutations`, 34 controls expected) is in progress; then the
  validators.toml row (cases, mutants, families), affected validators, proof renders, the default identity
  sweep against a base build of `c4a2d89c`, research section 15 (draft in
  `scratch/render-actors-008/section15.md`), status lines, PR, ready line, cleanup.

**Next step**

Read `scratch/render-actors-008/verify1.log`; fix any uncaught control; then follow "Left" in order.
