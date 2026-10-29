# RENDER-WORLDS-G2

Object-model texture lookup, brazier fires and the Vulcanus far plane from the DATA-ACQ-002 comparison.
[Addresses, provenance, fidelity numbers and limits](../research/client-worlds-g2.md).

- Claude Opus 5.5 lane. Worktree `~/Documents/MTM/worktrees/render-worlds-g2`, branch `claude/render-worlds-g2`, from
  origin/main `3735625`, later merged with `77c304a` (RENDER-WORLDS-O). Input links `tools/python` and `evidence`
  from the main checkout, never committed.
- Root causes: (1) native object textures came only from the model's folder; the original OpenTexture `0x0181fbe9`
  then asks the bitmap-name map (startup models such as `Data\Skill\Skeleton01..03` → `bons.jpg`, and the world
  pass's own extras such as `Data\Object2\DungeonStone01` → `deep_wall01.jpg` in 116–120), then `Data\Item\`, then
  `Data\Item\Texture\`; (2) object textures come from `Object<folder(world)>`, not the model folder (Abyss 1 types
  0x42..0x46); (3) the camera's `event_world` input (`world == 0x3f || 0x52..0x5a`, far 3700) was never set;
  (4) Vulcanus' brazier flames exist natively but the headless tour draws 2 of 25 steps, and RenderObjectVisual's
  emitters run while drawing.
- New `reconstructed/objects/texture_lookup.{h,c}` + generated `texture_preload.inc`, `native/core/mu_texture_names.{h,c}`,
  changes in `mu_objects.c`, `mu_textures.{h,c}`, `mu_walk.c`, `client_world_camera.{h,c}`, the objects summary
  line, and an opt-in `"draw_all"` in `scripts/fidelity_tour.py`.
- **Object texture folder ownership (WORLDS-O coordination):** WORLDS-O's tile-folder rule (`0x01829457`) and this
  lane's object texture rule are separate code paths; no shared helper was needed. Both use the client's folder
  numbers (`mu_objects_folder` here).
- `scripts/validate_worlds_g2.py` (registered `validate_worlds_g2`): 5 families, 4,157 cases by default, zero
  mismatches/stops, **17/17 compiled mutants detected**. It needs the section-3 pin (as `validate_objects`): set
  `MU_SECTION3=~/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin`.
- Fidelity at the DATA-ACQ-002 tiles (image mean |Δ| before → after): 63 2.665 → 1.841 (far 3257.8 → 3700),
  116 5.570 → 2.815, 117 4.081 → 2.601, 118 13.475 → 3.233, 119 9.440 → 2.490, 120 6.665 → 2.777,
  128 7.922 → 5.386, 131 7.624 → 7.121, 56 7.310 → 7.196, 91 7.706 → 6.905; others unchanged. Zero unresolved
  object textures in all 19 affected captures (before: 1–21 empty meshes per world).
- October 22 fourteen-view tour, base `77c304a` vs lane: 14/14 OBJECT and light dumps identical, 12/14 PNG;
  Elbeland (51) and Karutan (80) change as intended (Item-folder weapon/medicine/bottle textures).

Left: the Deep Dungeon dragon fire at type-67 markers (producer not found; untraced hooks listed in the finding);
Abyss 2 types 3/4/6/24 dark meshes (textures resolve; BlendMesh/BlendMeshLight class fields, for the Abyss lane);
the name map's other startup routines and earlier-world history; other model loaders' lookup rules.

No original client or launcher was started; no live read was needed. The live captures of DATA-ACQ-002 were only
read. Renders and reports were under `~/Documents/MTM/mu-mac-tools/native/{renders,scratch}/render-worlds-g2` and are
deleted after merge with the worktree, the temporary base worktree `worktrees/g2-base` and the branch. No new local
input needs retention.

## Checks
