# RENDER-ACTORS-008

## WIP checkpoint (2026-11-15 16:00, not PR-ready)

Branch `claude/render-actors-008`, stacked on ACTORS-007 (`origin/codex/render-actors-007`, PR #405).

**Done**

- `scripts/actor_caller_requests.py`: per-row recorder of RenderCharacter's ordered sprite, particle, joint,
  effect and bone-effect requests. TransformPosition `0x012b6ef1` is a marker recorder, so each request
  position resolves to its OBJECT bone and local offset. Clock `0x06fce370` and the CRT rand value are authored
  per run; rand call sites are recorded. RenderLinkItem `0x012bd910` runs per hand with the same recorder.
- `docs/research/actor-caller-requests.csv`: the request table (ids, subtypes, call sites, anchors, offsets,
  scales, lights, light model, link services, native consumer yes/no) for every constructed selector of the
  355-row population. RENDER-EFFECTS-034 can read the missing ids from the `native_consumer` column.
- `validate_actor_groups.py` admits a row whose caller requests are all object-bone sprites with a compiled
  constant/flicker/pulse light and a native sprite bitmap; generated `reconstructed/actors/caller_fx_table.h`;
  `mu_world_actor_caller_fx` emits them in both render backends.
- Correction to ACTORS-007: RenderLinkItem passes its level argument `<< 3` to RenderObjDraw (recorded per
  row). The native weapon level is the slot byte itself.
- Second generation: 172 checked group plans (138 + 34), 73 caller sprite requests on 33 rows, all families
  equal. Classes 1/5/10 are among them.

**Left**

- Third generation is running: adds RenderLinkItem's own sprite requests through the existing item link
  consumer (items `0x10f0`, `0x12f9`), `link_effect_mask` in the group plan.
- World-selected texture directory (Monster71/72 use `Npc/` in the Chaos Castle worlds): the opener reader is
  written, but those rows lack mesh textures in `Data/Monster` outside those worlds, so they need a
  world-restricted plan and caller runs in those worlds.
- Regenerate both census CSVs, update `native/tests/test_actor_groups.py` counts, validators.toml row
  (cases, mutants, families), compiled mutants once, proof renders, identity sweep, research section 15,
  status lines, PR.

**Next step**

Read the third generation's summary (`scratch/render-actors-008/gen3.log`), fix whatever fails, then run
`scripts/validate_actor_groups.py --mutations` once without `--generate`.
