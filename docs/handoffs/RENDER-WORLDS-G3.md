# RENDER-WORLDS-G3

Deep Dungeon dragon fire producer, Abyss 2 dark meshes, Scorched Canyon recheck, Vulcanus particle requests.
[Finding, addresses, fidelity and limits](../research/client-worlds-g3.md).

- Claude Opus 5.5 lane. Branch `claude/render-worlds-g3`, worktree `~/Documents/MTM/worktrees/render-worlds-g3`, from
  origin/main `2f3fdee`, merged with `61d5bb4` and `9b821b1` (RENDER-EFFECTS-006). Input links `tools/python` and
  `evidence` from the main checkout, never staged.
- Owned: `reconstructed/environment/env_body.c`, `reconstructed/environment/test_env_body.py`,
  `scripts/validate_worlds_g3.py`, this handoff and the finding. Minimal shared lines: the `mu_env_render_body`
  declaration in `env.h`; `env_body.c` in `reconstructed/environment/Makefile` and `native/Makefile`; `r_object` in
  `native/core/mu_env.c`; the clouds 0xb kind/create/move lines in `reconstructed/particles/particles.c`; one kind
  in `scripts/validate_particles.py`; the registry row.

Findings:
1. **Deep Dungeon dragon fire**: not the four G2 candidates (each has a world test outside 116..120) and not
   RenderObjectVisual (its world switch sends 116..120 to the empty hook tail). It is an EffectManager `.ein`
   effect attached to every type-62..67 marker by the map-object table (`0x0183067e`, std::map `0x06fbb7b0`): the
   live `+0x3d0` list holds exactly one effect on those types (35 type-67 markers in Deep Dungeon 3). The table's
   writer is not in the restored text; the consumer belongs to RENDER-EFFECTS-006 (which lists it as remaining).
2. **Abyss 2 dark meshes**: not objects 3/4/6/24 (their live fields are defaults; they are starfish, coral and
   seaweed). They are MoveFishs' swimmers 0x19f/0x1a0, whose BlendMesh 0 / BlendMeshLight the native
   environment drawer ignored. Fixed through `mu_env_render_body`.
3. **Scorched Canyon**: already fixed by RENDER-TIME-003; 8.068, all 7,111 visible bytes equal live.
4. **Vulcanus**: the 11 refused requests are clouds `0x7f89/0xb` of the type-3 visual; now created, moved and drawn.

Fidelity (DATA-ACQ-002, base `9b821b1`): Abyss 2 **4.412 → 3.975** (both modes); Vulcanus draw_all **1.830 → 1.798**,
refused requests **11 → 0**; normal mode 31/32 PNG, 32/32 OBJECT, 32/32 light identical; draw_all 30/32 PNG,
32/32 OBJECT, 32/32 light.

Left: the dragon fire's effect names (one live read of a type-67 object's `+0x3d0` node; for RENDER-EFFECTS) and its
consumer; clouds subtype 0x10; the Scorched Canyon colour cast; the custom-render chain head (runtime item map)
as client code.

No original client or launcher was started; no live read was needed. DATA-ACQ-002 inputs were only read. Local
outputs under `~/Documents/MTM/mu-mac-tools/native/{scratch,renders}/render-worlds-g3` are deleted at cleanup (the
temporary base worktree is already removed); no new local input needs retention.

## Checks

On the tree merged with origin/main `9b821b1`:

- `nice -n 10 bash scripts/local-macos-ci.sh`: **38 suites, 1,768 tests, 1,535 passed, 233 skipped, 0 failures,
  0 errors**; fixtures ok; native viewer and live readers built; audit **1,759 files, 0 rejected**.
- `MU_RECOVERY_INTEGRATION=1 MU_SECTION3=<x86-linux-capture-04 main-01ced000.bin> run_validators.py --private --jobs 2`:
  **6/6 pass**: `validate_worlds_g3` 4,000 cases / 22 mutants, `validate_particles` 407 / 22 (with the new kind),
  `validate_environment` 400 / 12, `validate_object_render` 1,984, `validate_worlds_after` 13,424 / 21,
  `validate_render_effects6` 1,000 / 34.
- Portable `reconstructed/environment/test_env_body.py`: 3 pass + 1 private.
- Fidelity tours (32 DATA-ACQ-002 captures, normal and `draw_all`, base `9b821b1` built separately): numbers in the
  finding §6.

Not merged by this lane: the MERGE-STEWARD merges it.
