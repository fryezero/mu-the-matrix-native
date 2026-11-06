# RENDER-EFFECTS-014

The last two bow joint kinds, their particles, 0x70c's rings and stones, the verified +0x64 lifecycle and a
ground-skill fixture. [Instruction evidence and remaining inputs](../research/client-render-effects-014.md).

Branch `claude/render-effects-014`, worktree `~/Documents/MTM/worktrees/render-effects-014`. PR #300 was still
open when the code started, so the branch began at `origin/codex/render-effects-013` (`506a46a1`). Main
`742ef666` was merged first (`ec8ccacd`), and the baseline was taken there once. After #299/#300/#301 merged, main
`83a21893` was merged in `354e03c8` (docs and `validators.toml` conflicts: both sides kept). No live client
session, network work, memory write or installed-app change. The `tools/python`, `evidence` and `input` links
are ignored and never committed.

## Scope

- `reconstructed/joints/bow_joints.inc`: joint 0x7f78/b (arrow 0x459's guided flares: ambient clock, pool
  ordinal, owner +0x110, sound 0x42, Shiny02/flare01 sprites, the skill-1 joint's owner write-back and
  CheckClientArrow) and 0x7f79/e (Spark03 sprite, smoke01 0x22/0x23, Spark03 0xa, colour changes).
  `joints.h`: `mu_jt_object.impact` (+0x110), `MU_JT_CALL_SOUND`, `MU_JT_CALL_CHECK_ARROW`. `joints.c`: the
  bow hook can go straight to the closing tail.
- `reconstructed/particles/particles.c`: smoke01 0x22/0x23 and Spark03 0xa create/move.
- `reconstructed/combat/bow_fx.inc`: effects 0x703, 0x704, 0x705/0, /1, /3 and 0x706. `skill_fx.c`: stones
  0x419/0x41a subtype 0x13.
- `native/core/mu_combat.{c,h}`: the arrow write-back route, `ambient_clock` = combat step, `Effect\Flare.jpg`
  (`MU_COMBAT_BITMAPS` 24 → 25), +0x110 in the arrow object view, and the ground-skill fixture (skills
  2044/2045 in `mu_combat_cast`). `native/tests/test_native_combat.py`: installed bitmap count 25.
- `scripts/validate_render_effects14.py` with registry row and portable test `native/tests/test_render_effects14.py`
  plus host `effects14_host.c`. `scripts/validate_skill_fx.py`: the shared ctypes `Object` gains `impact`.
- No world-particle table growth, item executor, renderchar, world object, HUD or runner changes.

## Scene results

Installed client, Lorencia tile 182,128, spider at 186,128, 30 frames, every fifth drawn, 640x400 software, no
audio/items/players; bows use class 2 and `2:skill:24:spider;3:stop`; ten staff scenes use skills
1, 2, 3, 4, 5, 7, 8, 9, 10, 14.

| Scenes | Before | After |
|---|---|---|
| 33 bows, unsupported requests | 15 (0x12f7: 12 × 0x7f78/b; 0x12fb: 3 × 0x7f79/e) | **0** |
| 33 bows, arrows | 119 | 119 |
| 0x12f7 | 0 joints, 0 sprites | 12 joints, 540 sprites |
| 0x12fb | 0 joints, 0 particles | 3 joints, 72 particles, 24 sprites |
| ten staff scenes, unsupported | 0 | 0 |

Only 0x12f7 and 0x12fb change pixels (frames 3..6 of 7). The other 31 bows and all staff scenes are byte-identical.
The ground-skill fixture (`2:skill:2044:spider`, Bow01) casts once: 3 arrows (2 hit), 0x70a counted as the only
unsupported request. Kept native renders (not original-client captures):
`~/Documents/MTM/mu-mac-tools/native/renders/render-effects-014/after-0x12f7-frame22.png` (blue flares around the
moving ring point) and `after-0x12fb-frame18.png` (yellow trails, red smoke, sparks).

## Checks

No lane full gate; the steward runs it. Heavy work used `nice -n 10`, make at most `-j4`, two validator workers.

| Check | Result | Wall time |
|---|---|---:|
| Base build `make -j4 -C native` at `ec8ccacd` | Passed | 16.02 s |
| Before scenes (33 bows + 10 staff) | 15 unsupported, 119 arrows, 0 staff | 56.07 s |
| Before default-draw tour sweep (DATA-ACQ-002, 32 tours) | 128 PNG + 64 dumps | 58.33 s |
| First sample (`--cases 30`, 450 comparisons) | 7 Flare/b move mismatches: the fade does not apply to subtype b (`0x0157c24e`); corrected | 1.26 s |
| Samples while iterating (`--cases 20..60`) | zero mismatches | ~1 s each |
| Full `validate_render_effects14` with mutants, at `b1df5ee7` | **9,900 comparisons, zero mismatches; 48/48 mutants caught, 0 equivalent, 0 stopped (5,370 mutant cases)** | 42.84 s |
| Focused unit modules (24 modules, below) | 227 tests, 198 passed, 29 skipped, 0 failures | 79.62 s |
| After scenes at `b1df5ee7` | 0 unsupported, 119 arrows, 0 staff; only 0x12f7/0x12fb changed | 42.54 s |
| After default-draw tour sweep at `b1df5ee7` | 32 tours: 128 PNG + 64 object/light dumps byte-identical to before | 52.49 s |
| Final build `make -j4` at `354e03c8` | Passed | 20.48 s |
| Affected validators, no mutants, cached, two workers, at `354e03c8` | 61/61 pass, 1,388,810 cases (below) | 3,126.58 s |
| `scripts/audit_repository.py` | 1,907 staged files, 0 rejected | 16.66 s |
| Docs-reading modules (`test_world_captures_2`, `test_repository_policy`, `test_native_item_textures` run from `native/tests`, `test_native_data_manifest`) | 32 tests, 0 failures | 10.03 + 1.59 s |

Mutant runs: a test-budget exception, as in 013. The first `--mutations` attempt stopped before its first mutant:
re9's effect machine enlarges the shared Unicorn stack and broke the earlier machines. The second stopped after
24 joint mutants: the same cause in the particle phase. It also showed one joint mutant applied to the wrong
site, because `if (j->skill == 1) {` also occurs in 0x7f79/18's create. The validator now restores the stack size
and anchors that mutant uniquely; all 48 anchors are checked to occur exactly once. Only the third run is reported.

Focused modules (`MU_RECOVERY_INTEGRATION=0`, installed-data env set): `native.tests.test_render_effects14`, `13`,
`12`, `11`, `10`, `9`, `test_render_effects`, `test_native_combat`, `test_native_joints`, `test_native_particles`,
`test_native_render_effects6`, `test_native_worlds_l`, `test_native_worlds_m`, `test_native_worlds_o`,
`test_native_terrain`, `test_native_helpers`, `test_native_pets`, `test_world_parts`, `test_session_combat`;
`reconstructed.joints.test_joints`, `reconstructed.particles.test_particles`, `reconstructed.combat.test_skill_fx`,
`reconstructed.combat.test_combat`; `tests.test_validators_manifest`. The 6b grep covered `mu_jt_object`,
`MU_COMBAT_BITMAPS`/`bitmaps_loaded` and the ctypes `Object`. Users: `test_native_combat`, `test_native_terrain`,
`test_native_worlds_o` and the two hosts. No world-particle table size changed.

| Validator (no mutants, cached) | Cases | Wall time |
|---|---:|---:|
| `validate_item_ranked` † | 17,736 | 617.3 s |
| `validate_item_continuation` † | 25,772 | 651.3 s |
| `validate_item_expansion` † | 52,172 | 293.1 s |
| `validate_item_effects` | 1,500 | 1.1 s |
| `validate_item_clusters` † | 74,292 | 375.1 s |
| `validate_item_types` | 135,176 | 41.5 s |
| `validate_charsel_world` † | 1,200 | 5.4 s |
| `validate_combat` | 496 | 1.1 s |
| `validate_fidelity` † | 991 | 64.7 s |
| `validate_joints` | 180 | 2.2 s |
| `validate_login_world` † | 1,200 | 2.3 s |
| `validate_meshdraw` † | 14,619 | 57.3 s |
| `validate_model_edge` † | 954 | 113.1 s |
| `validate_model_light` † | 1,433 | 4.9 s |
| `validate_particles` | 407 | 0.8 s |
| `validate_renderchar` † | 1,706 | 42.7 s |
| `validate_skill_fx` | 660 | 1.3 s |
| `validate_terrain` † | 583,500 | 371.7 s |
| `validate_viewport_monsters` † | 1,963 | 11.5 s |
| `validate_render_worlds_a` | 9,000 | 14.4 s |
| `validate_icarus` | 5,240 | 30.8 s |
| `validate_icarus_c2` | 8,400 | 20.8 s |
| `validate_worlds_d` | 2,400 | 4.3 s |
| `validate_worlds_e` | 4,840 | 15.9 s |
| `validate_audio_callers` † | 5,528 | 5.0 s |
| `validate_item_gear` | 25,256 | 160.4 s |
| `validate_audio_combat` | 19,548 | 37.9 s |
| `validate_item_next` † | 14,992 | 768.7 s |
| `validate_render_effects` | 660 | 1.1 s |
| `validate_render_effects3` | 720 | 1.3 s |
| `validate_render_effects4` | 1,920 | 9.6 s |
| `validate_render_effects5` | 1,190 | 6.1 s |
| `validate_render_effects6` | 1,000 | 1.6 s |
| `validate_render_effects7` | 596 | 2.4 s |
| `validate_render_effects9` | 304 | 1.4 s |
| `validate_render_effects10` | 154 | 0.6 s |
| `validate_render_effects11` | 176 | 0.7 s |
| `validate_render_effects12` | 64 | 0.6 s |
| `validate_world_particle_consumers` | 900 | 1.8 s |
| `validate_audio_domains` † | 2,544 | 26.7 s |
| `validate_audio_items` † | 3,000 | 3.8 s |
| `validate_worlds_l` | 1,260 | 1.3 s |
| `validate_audio_charsel` † | 5,968 | 3.3 s |
| `validate_item_coverage` † | 31,724 | 732.5 s |
| `validate_item_wings_next` | 33,622 | 188.0 s |
| `validate_item_scalars` † | 26,154 | 151.8 s |
| `validate_item_chains` † | 35,346 | 196.2 s |
| `validate_worlds_m` | 1,080 | 0.8 s |
| `validate_worlds_after` † | 13,424 | 9.0 s |
| `validate_worlds_g3` | 4,000 | 2.9 s |
| `validate_worlds_after2` † | 32,216 | 22.7 s |
| `validate_worlds_after3` † | 10,212 | 5.1 s |
| `validate_worlds_after4` † | 9,181 | 13.7 s |
| `validate_worlds_after5` † | 6,000 | 12.1 s |
| `validate_worlds_after6` | 7,300 | 65.4 s |
| `validate_item_carry` † | 114,388 | 541.8 s |
| `validate_item_quality` † | 28,080 | 164.0 s |
| `validate_item_product` † | 2,874 | 37.0 s |
| `validate_app_polish1` | 752 | 19.1 s |
| `validate_render_effects13` | 180 | 0.5 s |
| `validate_render_effects14` | 660 | 1.3 s |

61/61 pass, 1,388,810 cases, 0 mismatches. † selected through a broad `native` build or a script naming a changed directory, not a `reconstructed/joints|particles|combat` build declaration.

## Steward

Steward validators (all without mutants; ran at `354e03c8`): `validate_item_ranked`, `validate_item_continuation`, `validate_item_expansion`, `validate_item_effects`, `validate_item_clusters`, `validate_item_types`, `validate_charsel_world`, `validate_combat`, `validate_fidelity`, `validate_joints`, `validate_login_world`, `validate_meshdraw`, `validate_model_edge`, `validate_model_light`, `validate_particles`, `validate_renderchar`, `validate_skill_fx`, `validate_terrain`, `validate_viewport_monsters`, `validate_render_worlds_a`, `validate_icarus`, `validate_icarus_c2`, `validate_worlds_d`, `validate_worlds_e`, `validate_audio_callers`, `validate_item_gear`, `validate_audio_combat`, `validate_item_next`, `validate_render_effects`, `validate_render_effects3`, `validate_render_effects4`, `validate_render_effects5`, `validate_render_effects6`, `validate_render_effects7`, `validate_render_effects9`, `validate_render_effects10`, `validate_render_effects11`, `validate_render_effects12`, `validate_world_particle_consumers`, `validate_audio_domains`, `validate_audio_items`, `validate_worlds_l`, `validate_audio_charsel`, `validate_item_coverage`, `validate_item_wings_next`, `validate_item_scalars`, `validate_item_chains`, `validate_worlds_m`, `validate_worlds_after`, `validate_worlds_g3`, `validate_worlds_after2`, `validate_worlds_after3`, `validate_worlds_after4`, `validate_worlds_after5`, `validate_worlds_after6`, `validate_item_carry`, `validate_item_quality`, `validate_item_product`, `validate_app_polish1`, `validate_render_effects13`, `validate_render_effects14`.

`validate_render_effects14` is the only row that needs mutants (its own, already run once above).
Rows selected only through a broad `native` build declaration or a script that names a directory: the 29 rows marked † in the table above.

Environment, private inputs read-only:

```sh
export MU_RECOVERY_INTEGRATION=1
export MU_GAME_ROOT="$HOME/Library/Application Support/MuTheMatrix/prefix/drive_c/MuTheMatrix"
export MU_SECTION3="$HOME/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin"
export MU_EVIDENCE_DIR="$HOME/Documents/MTM/mu-the-matrix-native/evidence"
export MU_OBJECTS_PLAIN_DIR="$HOME/Documents/MTM/mu-mac-tools/native/scratch/objects/live/plain"
export MU_SNAPSHOT_DIR="$HOME/Documents/MTM/mu-mac-tools/native/scratch"
export MU_LIGHT_OBJECTS="$MU_OBJECTS_PLAIN_DIR/EncTerrain95.plain"
export MU_LIGHT_SNAPSHOT="$MU_SNAPSHOT_DIR/light/live/dumps/login-a.light"
```

## Remaining work and cleanup

See the finding's [still-open list](../research/client-render-effects-014.md#still-open): effect 0x70a (the
rain whose 0x7e7 arrows make 0x70c natively) with its render, 0x70c's render and the ring models' loading, the
0x45e decal's native draw (contract recorded), Uruk's weather capture and the Muun owner fixture.

After the final push: one ready-prs.txt line, then no further push. Scratch and build products of this lane are
removed. The worktree and local branch stay until the steward merges; the two PNGs above stay in
`renders/render-effects-014/`. No private input needs to survive cleanup.
