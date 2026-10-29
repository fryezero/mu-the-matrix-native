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

- **Shared build fix (BUILD-DEPS-001 follow-up, orchestrator-approved):** the 36 `reconstructed/*/Makefile`s now use
  `-include ../deps.mk`. `deps.mk` only defines `DEPS` (an `-MM` pass) and `-include`s `*.d`, so a missing file just
  leaves `$(DEPS)` empty. With the plain `include`, every private validator that builds mutants from a temporary
  copy of single directories failed (`No rule to make target ../deps.mk`: camera, worlds b/e/g/h/i/j/k/n/p/p2/g2).

Left: the Deep Dungeon dragon fire at type-67 markers (producer not found; untraced hooks listed in the finding);
Abyss 2 types 3/4/6/24 dark meshes (textures resolve; BlendMesh/BlendMeshLight class fields, for the Abyss lane);
the name map's other startup routines and earlier-world history; other model loaders' lookup rules.

No original client or launcher was started; no live read was needed. The live captures of DATA-ACQ-002 were only
read. Renders and reports were under `~/Documents/MTM/mu-mac-tools/native/{renders,scratch}/render-worlds-g2` and are
deleted after merge with the worktree, the temporary base worktree `worktrees/g2-base` and the branch. No new local
input needs retention.

## Checks

Merge lock taken at 19:55 CDT (queue head). Latest main `5fa43cd` (BUILD-DEPS-001, RENDER-WORLDS-P/P2) merged as
`38410e0`; conflicts in `native/Makefile`, `reconstructed/objects/Makefile`, `scripts/validators.toml` and the
three status docs keep both sides. Clean `native/build` and reconstructed libraries before the gate.

- `bash scripts/local-macos-ci.sh` (merged tree, before the `-include` change): **1,698 tests across 38 discovery
  runs, 218 explicit skips, zero failures/errors; 11/11 fixture scenarios; publication audit 1,673 files, zero
  rejected**. A first run on the pre-merge branch had one `test_transport` allowlist failure that passes 3/3 alone
  (concurrent socket use by another lane's gate); a first merged run failed `test_native_build_deps` on libraries
  built before the merge (no `.d` files), passing after removing them. Final gate on `11c3a8e` (with `-include`): **1,698 tests / 38 runs, 218 skips, zero failures; 11/11 scenarios; audit 1,673 files, 0 rejected** (one earlier rerun hit the same transport flake). Only this checks section changed after the gate.
- Registered private validators, serial, on the merged tree with `-include`: **19/19 pass** (`validate_worlds_*`
  b–p2 and g2, `validate_world_tile_folder`, `validate_camera`, `validate_objects`), mutants detected in all.
- `validate_worlds_g2`: 5 families, 4,157 cases (default) / 2,657 (registered), zero mismatches/stops, 17/17 mutants.
- Portable `reconstructed/objects/test_worlds_g2.py` 3 pass + 1 private; native host `test_native_worlds_g2.py` passes.
