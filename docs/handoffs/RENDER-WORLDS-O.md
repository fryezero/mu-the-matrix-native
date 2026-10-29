# RENDER-WORLDS-O

Abyss of Atlans 1-3 (worlds 128/129/130): the nine primary create/move/visual methods, and the tile-bitmap folder
that gives Abyss 2 and 3 their terrain. [Finding, addresses, fidelity numbers and limits](../research/client-worlds-o.md).

- Branch `claude/render-worlds-o`, worktree `~/Documents/MTM/worktrees/render-worlds-o`, from origin/main `38d08a9`.
  Ignored `tools/python` and `evidence` are symlinks to the main checkout and are never staged.
- Owns `reconstructed/objects/abyss_atlans.c`, `worlds_o.h`, `test_worlds_o.py`, `scripts/validate_worlds_o.py`,
  `scripts/validate_world_tile_folder.py`, `native/tests/{test_native_worlds_o.py,worlds_o_host.c}`. Minimal shared
  lines: create/move dispatch in `object_render.c`; primary-visual list and one visual branch in
  `mu_objects_runtime.c`; `mu_terrain_tile_folder` in `reconstructed/terrain/terrain.{c,h}`; the tile directory in
  `native/core/mu_terrain.c`; the `tile_folder` report field (`mu_terrain.h`, `mu-terrain info`); Makefile and
  validator-registry rows; world-handler coverage for these three classes only.
- Coverage: **33 → 42/144 primary methods, 11 → 14/48 classes** on `38d08a9`; **61/144, 21/48** after merging RENDER-WORLDS-N.

## Checks

- `validate_worlds_o`: 9 families × 1,000 = **9,000 cases equal, 0 mismatches/stops, 24/24 compiled mutants**.
- `validate_world_tile_folder`: original `0x01829457` for 19 world globals × folders 0..299 = **5,700 cases equal,
  0 stops**, 1,077,300 recorded bitmap loads; remapped folders exactly 130 → 129 and 131 → 129; the old own-folder
  rule fails 38 cases.
- Both registered and passing through `run_validators.py --private`.
- `reconstructed/objects/test_worlds_o.py` has 5 tests (public create/move with one generic tick and the drop
  particle, log-capacity independence, the tile-folder table, and two private instruction runs).
- `native/tests/test_native_worlds_o.py` has 3 tests: synthetic Data tree with tiles only in World129 (worlds
  129/130 draw every face textured, world 131 none); production host visual (type 39 hidden only in 128..130,
  model gate, generic hook untouched elsewhere); private installed root (all three load World129's tiles).
- Fidelity at the DATA-ACQ-002 arrival tiles, base → branch: image mean |Δ| **Abyss 1 7.946 → 7.922, Abyss 2
  82.170 → 4.412, Abyss 3 47.984 → 2.230**. Field differences 276/512/455 → 79/134/101; after-character → 0.
  The other 29 captures keep 58/58 PNG, 29/29 OBJECT and 29/29 light hashes. The October 22 fourteen-view
  snapshots are no longer at their manifest paths, so that tour was not rerun.

## Remaining

Custom-render/after-render/invisible-move slots and the after-character second pass for 128..130; Abyss 2 dark
meshes of types 3/4/6/24 and the Abyss 1 cyan pillar (pre-existing, now visible); live pool/RNG/time-synchronised
comparison. No live game was used. No nested particle work was needed: `0x7fcd/0` is an existing consumer.

## Cleanup

After merge, remove `native/{scratch,renders}/render-worlds-o`, the worktree (including its builds and input links)
and the local branch. No new local INPUT needs retention. DATA-ACQ-002's inputs were only read.

## Final locked gate

Merge lock taken at 19:14 CDT after the FIFO queue. Merged main `3735625` (RENDER-WORLDS-N, RENDER-EFFECTS-004,
NATIVE-PERF-004; conflicts in Makefiles, includes, registry and status docs keep both sides, coverage markdown
regenerated) and then `9d21ebb` (RENDER-ITEMS-002K) cleanly. After `make -C native clean`, `bash scripts/local-macos-ci.sh`
passes: **38 unittest runs, 1,680 tests, 216 explicit optional/private skips, zero failures; 11 fixture scenarios;
viewer/reader builds (readers not run); 1,637 audited files, zero rejected**. `validate_worlds_o` (9,000 cases,
24/24 mutants) and `validate_world_tile_folder` (5,700 cases) pass again on the integrated tree. So do
`validate_worlds_n`/`_i`, checked after the first merge. The 32-capture tour against a fresh build of main `3735625`
repeats the numbers above: only the three Abyss views change (8 of 128 artifacts), and the merged binary reproduces
7.922 / 4.412 / 2.230. No hosted workflow and no original client were run.
