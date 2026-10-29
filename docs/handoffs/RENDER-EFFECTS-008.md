# RENDER-EFFECTS-008

The map-object effect table (EnchantEffect +0x5c, `0x06fbb7b0`) read live, decoded, its attach `0x0183067e`
reconstructed and compared, and its effects drawn in the native world, starting with the Deep Dungeon dragon fires.
[Finding, addresses, fidelity and limits](../research/client-render-effects-008.md).

- Claude Opus 5.5 lane. Branch `claude/render-effects-008`, worktree `~/Documents/MTM/worktrees/render-effects-008`,
  from origin/main `9b821b1`, merged with `79a6b47` (RENDER-WORLDS-G3 #269, RENDER-WORLDS-AFTER2 #270). Input links
  `tools/python` and `evidence` from the main checkout, never staged.
- Owned: `reconstructed/objects/map_effects.{c,h}`, `native/core/mu_map_effects.{c,h}`,
  `scripts/live_effect_table_to_plain.py`, `scripts/validate_map_effects.py`,
  `native/tests/{map_effects_host.c,test_native_map_effects.py}`, `tests/test_effect_table_plain.py`, this handoff
  and the finding.
- Minimal shared lines: `langread.c` graph scan (a string/vector candidate followed as both); `native/Makefile`
  (two `+=` source lines, the host rule); `mu_particles.{c,h}` (`ein_create`/`ein_link`/`ein_clear` split out of
  RENDER-EFFECTS-006's attach, links 64 → 4,096, the objects' scene capacity); `mu_effect_scene.{c,h}`
  (`instance_limit`, default 256 unchanged); `mu_objects_runtime.c` (`update_effects` after RenderObjectVisual in
  every world, posing listed hidden objects; `+0x38 = 1` at start); `world/parts/particles.c` (load and attach at
  open); the registry row; one line each in `client-effect-manager.md` and `client-render-items.md`.

## Live sessions (game lock, Nighty on MTM-1)

- 2026-10-29 00:22–00:27: Lorencia → Deep Dungeon 3 → Deep Dungeon 5 → Burning Kethotum → Lorencia (Warps window).
- 2026-10-29 00:32–00:34: Lorencia only (table re-read with the fixed reader).

No fight, NPC, item or trade action; only warp costs; ended in Lorencia; read-only reads and window-only shots; no
packet capture. `LauncherOption.if` restored byte for byte; `DisplayDeviceModeIndex` set back to the owner's 2;
client, launcher and wineserver closed; lock removed after each session.

## Result

- The table (live): 38 worlds, 443 types, 758 entries, 263 `.ein` paths, filled at startup (identical in five reads
  and two client runs). Deep Dungeon 116–120: `fire01-*` per marker type 62–67, the dragon fire is
  `fire01-red01` on type 67. Cross-checked against the `+0x3d0` lists of type-67/62 markers and a 136 type-160 object.
- `0x0183067e` (verified): **300 cases, 0 mismatches, 14/14 compiled mutants**; live family over the 32
  DATA-ACQ-002 captures and this lane's 3: every object's attach count equals its live list size.
- Native: the table's effects attach through RENDER-EFFECTS-006's path and update in every world after
  RenderObjectVisual; hidden markers are posed like RenderObject does; `+0x38 = 1` from Initialize `0x0129eb81`.
  Deep Dungeon 3 draw_all **3.203 → 3.026**, Deep Dungeon 4 **2.545 → 2.343**, Kardamahal normal **10.911 → 9.787**,
  Kubera **4.321 → 3.854**, Nixies Lake draw_all **7.001 → 5.840**; without the table the branch is pixel-identical to
  base in 32/32 captures (both modes). Full table and the three regressions (136 +0.008, 137 +0.052, 142 +0.059 in
  draw_all) in the finding §5.

## Inputs for later lanes (local, never commit)

Under `~/Documents/MTM/mu-mac-tools/native/scratch/render-effects-008/`:

- `live/s2-lorencia-fxt.bin`: the complete table graph (langread `graph:0x06fbb7b0=8,6,0`, 6.5 MB);
  `plain-s2-lorencia/{mapeffects,muuneffects}.tsv`: its plaintext (point `MU_LANG_DIR` at a lang dir holding
  `mapeffects.tsv`, e.g. copy it next to the other lang tables).
- `live/{118-dd3,120-dd5,136-bk}-{obj,glob}.bin`, `.png`, `-time.txt`: arrival captures of this run.
- `keep/*.png`: live | before | after strips of Deep Dungeon 3, Kardamahal and Burning Kethotum.
- `bin/`: this lane's session scripts (DATA-ACQ-002's, with the table read in `cap.sh` and the `+0x3d0` read
  `att.sh`).

Rerun the live family: `validate_map_effects.py --snapshot <scratch>/live/s2-lorencia-fxt.bin --objects
<capture>-obj.bin ...`.

## Left

Bone −1 following (`0x0129faee`, Ignis Volcano types 175/176); `0x0129f4cb`'s dt-0 first update; the Muun table
`0x0114203d` consumer (16 records exported as `muuneffects.tsv`; needs native Muun owners); per-effect look and
particle phase belong to the `.ein` port (NATIVE-FX-002 / RENDER-EFFECTS-006).

## Checks

On the tree merged with origin/main `79a6b47`:

- `MU_GATE_JOBS=2 nice -n 10 bash scripts/local-macos-ci.sh`: **38 suites, 1,780 tests, 1,545 passed, 235 skipped,
  0 failures, 0 errors**; fixtures ok; native viewer built; audit **1,775 files, 0 rejected**.
- `MU_RECOVERY_INTEGRATION=1 run_validators.py --private --jobs 2`: **3/3 pass**: `validate_map_effects` 300 cases /
  14 mutants, `validate_render_effects6` 1,000 / 34 (the shared ein path), `validate_object_render`.
- Portable: `native/tests/test_native_map_effects.py` (host: loader, sector and vector order, hidden markers posed in
  both render branches, trailing-space path, missing file, absent world), `tests/test_effect_table_plain.py` (2),
  `test_native_render_effects6` unchanged and passing.
- Live family (local, not in the registry): 35 captures, every object's attach count = live `+0x3d0` size.
- Fidelity tours on base `9b821b1` (built separately) vs this branch, 32 captures, normal and draw_all (finding §5).

Steward validators: validate_map_effects, validate_render_effects6 (env: `MU_RECOVERY_INTEGRATION=1`).
