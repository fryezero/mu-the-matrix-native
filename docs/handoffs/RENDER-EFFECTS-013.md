# RENDER-EFFECTS-013

Two more bow joint kinds and Shiny01/3 particles. [Instruction evidence and remaining inputs](../research/client-render-effects-013.md).

Branch `codex/render-effects-013`, worktree `~/Documents/MTM/worktrees/render-effects-013`.
The branch starts at main `5a91b98d3f1f2e6e361746091b518d0a327ffb5b`, after #296 reported MERGED.
No fallback base, live client session, network work, memory write or installed-app change.
Shared `tools/python`, `evidence` and `input` links are ignored and never committed.

## Scope

- Joint 0x80e3/5: reconstruct create/move and expose the owning arrow's signed lifetime +0x6c.
- Joint 0x7f79/f: reconstruct create/move and both Shiny01/3 particle calls before fading.
- Particle 0x7f66/3: reconstruct create/move using the existing Shiny01 bitmap and native particle route.
- `validate_render_effects13`, registry row and portable native host. The host exercises owner refresh,
  expiration and the joint callback's two emissions into the legacy particle pool.
- No world-particle table growth, item executor, renderchar, HUD or runner changes.

## Validation method and test budget

No lane full gate. Heavy work used `nice -n 10`, make at most `-j4` and two affected-validator workers.
The baseline was measured once on the branch-base binary. The final tour sweep uses default draw, not draw_all.

The first 180-case sample found the missing Shiny01/3 move branch; the corrected sample passed.
The full comparison then passed 2,700 cases before entering mutants. Eight joint mutants passed once.
The particle phase stopped on a nonunique source-replacement anchor after its first mutant. The source
anchor was narrowed; the eight particle mutants ran, retaining the joint results. The alpha-death mutant
was not caught by that random sample. Explicit alpha inputs -0.1, 0, 0.001, 0.002, 0.5 and 1 now cover the
boundary. Only that mutant was rerun with another 180-case baseline sample. Final 16/16 caught,
zero equivalent and zero stopped; 1,920 cases in the retained mutant results.

This is a test-budget exception: the first particle mutant repeated after the interrupted report, and the
initially undetected alpha-death mutant repeated with directed coverage. No existing validator's mutants
were rerun. The new script now prints base and individual mutant results before a later failure can lose them.

The full comparison ran at `0c54ce2e`; subsequent commits change only the validator's anchors, progress output
and alpha sampler. Final boundary validation and unit tests use the code committed as `dad007dc`.

## Checks and scene measurements

| Check | Result | Wall time |
|---|---|---:|
| Baseline core / world builds | Passed | 43.15 / 4.55 s |
| Changed core build / final core build | Passed | 21.21 / 10.15 s |
| First 180-case instruction sample | Shiny01/3 move mismatch; corrected | 0.77 s |
| Corrected particle rebuild + 180-case sample | Zero mismatches | 0.98 s |
| Full new comparison and initial mutant phase | 2,700 comparisons, zero mismatches; 8 joint mutants caught; particle anchor error | 12.99 s |
| Resumed particle phase with 180-case comparison | Zero comparison mismatches; 7 particle mutants caught, death branch not sampled | 6.25 s |
| Directed alpha sample and death mutant | 180 comparisons, zero mismatches; final mutant caught | 1.02 s |
| Native callback host | 1/1 passed | 2.67 s |
| Focused unit modules | 142 tests, 128 passed, 14 private wrappers skipped | 22.50 s |
| Before scenes | 33 bows: 27 unsupported, 119 arrows; ten staff scenes: 0 unsupported | 58.39 s |
| Before default-draw tour | 32 tours, 64 PNG and 64 object/light dump hashes | 41.74 s |

The focused modules were `native.tests.test_render_effects13`, `test_render_effects12`,
`test_render_effects11`, `test_native_combat`, `test_native_joints`, `test_native_particles`,
`test_native_render_effects6`, `test_native_worlds_l`, `test_native_worlds_m`; plus
`reconstructed.joints.test_joints`, `reconstructed.particles.test_particles`,
`reconstructed.combat.test_skill_fx`, `reconstructed.combat.test_combat` and
`tests.test_validators_manifest`. The native modules share the `native.tests` prefix.
Private wrappers were disabled; direct validators supplied their separate original-code evidence.

### Final results (2026-11-06, code `dad007dc`)

`origin/main` was still `5a91b98d` at the final fetch (#297/#298 open), so no main merge was needed
and the build inputs did not change after the focused unit modules and host passed.

| Check | Result | Wall time |
|---|---|---:|
| Final `make world` (mu-world relink, 24 world objects) | Passed | 4.01 s |
| After scenes | 33 bows: 15 unsupported (was 27), 119 arrows (unchanged); ten staff scenes: 0 unsupported | 59.75 s |
| After default-draw tour | 32 tours, 64 PNG and 64 object/light dump hashes byte-identical to before | 39.05 s |
| `validate_render_effects13` registry row, no mutants | 180 comparisons, zero mismatches | 0.37 s |
| 44 affected rows, no mutants, two workers | 44/44 passed, 922,184 cases | 1,477.22 s + 282 s retry |
| Docs-reading modules (`test_world_captures_2`, `test_repository_policy`, `test_native_item_textures`, `test_native_data_manifest`) | 32 tests, 31 passed, 1 skipped | 7.15 s |
| `scripts/audit_repository.py` | 1,877 staged files, 0 rejected | 15.12 s |

Scene detail: bows 0x12fc, 0x130a and 0x131e each went from 4 unsupported requests to 0 and now create
four joints; 0x12fc also creates 56 Shiny01/3 particles. Their frame hashes change as intended.
The other 30 bow scenes and all ten staff scenes keep identical frame hashes and summaries.
0x12f7 (12, joint 0x7f78/b) and 0x12fb (3, joint 0x7f79/e) remain unsupported; see the finding's
still-open list. Kept native renders (640x400, frame 3 of each scene, not original-client captures):
`~/Documents/MTM/mu-mac-tools/native/renders/render-effects-013/{before,after}-{0x12fc,0x130a}.png`.

Affected rows ran through the steward's no-mutant helper (pins from `scripts/pins.py`, compiled-mutant
switches removed). That helper does not build: `validate_terrain` and `validate_audio_items` first
failed only because `reconstructed/terrain` and `reconstructed/items` had not been built in this
worktree. After `make -C` of both (0.31 / 0.29 s) they passed (280.27 / 2.37 s). No other row was rerun.

| Validator | Cases | Wall time |
|---|---:|---:|
| `validate_item_effects` | 1,500 | 1.36 s |
| `validate_item_types` | 135,176 | 31.93 s |
| `validate_combat` | 496 | 0.85 s |
| `validate_crypto` | 568 | 25.05 s |
| `validate_item_models` | 4,881 | 14.67 s |
| `validate_joints` | 180 | 2.07 s |
| `validate_meshdraw` | 14,619 | 444.01 s |
| `validate_model_edge` | 954 | 104.24 s |
| `validate_model_light` | 1,433 | 4.34 s |
| `validate_npc_dialogue` | 18,444 | 1.93 s |
| `validate_particles` | 407 | 0.74 s |
| `validate_protocol` | 800 | 2.03 s |
| `validate_skill_fx` | 660 | 0.78 s |
| `validate_terrain` | 583,500 | 280.27 s |
| `validate_viewport_monsters` | 1,963 | 6.67 s |
| `validate_render_worlds_a` | 9,000 | 9.15 s |
| `validate_icarus` | 5,240 | 36.73 s |
| `validate_icarus_c2` | 8,400 | 17.13 s |
| `validate_worlds_d` | 2,400 | 3.55 s |
| `validate_worlds_e` | 4,840 | 15.78 s |
| `validate_audio_callers` | 5,528 | 4.38 s |
| `validate_item_gear` | 25,256 | 929.90 s |
| `validate_audio_combat` | 19,548 | 33.15 s |
| `validate_render_effects` | 660 | 1.31 s |
| `validate_render_effects3` | 720 | 1.23 s |
| `validate_render_effects4` | 1,920 | 7.36 s |
| `validate_render_effects5` | 1,190 | 4.24 s |
| `validate_render_effects6` | 1,000 | 1.59 s |
| `validate_render_effects7` | 596 | 1.76 s |
| `validate_render_effects9` | 304 | 1.04 s |
| `validate_render_effects10` | 154 | 0.49 s |
| `validate_render_effects11` | 176 | 0.40 s |
| `validate_render_effects12` | 64 | 0.36 s |
| `validate_world_particle_consumers` | 900 | 1.02 s |
| `validate_audio_domains` | 2,544 | 24.35 s |
| `validate_audio_items` | 3,000 | 2.37 s |
| `validate_worlds_l` | 1,260 | 1.46 s |
| `validate_audio_charsel` | 5,968 | 3.66 s |
| `validate_item_wings_next` | 33,622 | 915.56 s |
| `validate_worlds_m` | 1,080 | 0.72 s |
| `validate_worlds_g3` | 4,000 | 3.08 s |
| `validate_worlds_after4` | 9,181 | 8.99 s |
| `validate_worlds_after6` | 7,300 | 67.12 s |
| `validate_app_polish1` | 752 | 20.49 s |

## Steward

Affected rows are selected from changed `native`, `reconstructed/joints` and `reconstructed/particles`
compiled sources, plus `reconstructed/combat` because it compiles the changed `mu_jt_object` header.
The registry's broad `native` declarations include rows that are otherwise unrelated. The shared-symbol
search also selected the worlds L/M hosts, joint/particle tests and combat hosts.

Environment, private inputs read-only:

```sh
export MU_RECOVERY_INTEGRATION=1
export MU_GAME_ROOT="$HOME/Library/Application Support/MuTheMatrix/prefix/drive_c/MuTheMatrix"
export MU_SECTION3="$HOME/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin"
export MU_OBJECTS_PLAIN_DIR="$HOME/Documents/MTM/mu-mac-tools/native/scratch/objects/live/plain"
export MU_SNAPSHOT_DIR="$HOME/Documents/MTM/mu-mac-tools/native/scratch"
export MU_LIGHT_OBJECTS="$MU_OBJECTS_PLAIN_DIR/EncTerrain95.plain"
export MU_LIGHT_SNAPSHOT="$MU_SNAPSHOT_DIR/light/live/dumps/login-a.light"
```

No map-effect code changed; these checks do not require `MU_LANG_DIR`.
All listed steward validators should run without mutants if the steward needs them.

Steward validators (all without mutants; ran at `dad007dc`): `validate_item_effects`, `validate_item_types`, `validate_combat`, `validate_crypto`, `validate_item_models`, `validate_joints`, `validate_meshdraw`, `validate_model_edge`, `validate_model_light`, `validate_npc_dialogue`, `validate_particles`, `validate_protocol`, `validate_skill_fx`, `validate_terrain`, `validate_viewport_monsters`, `validate_render_worlds_a`, `validate_icarus`, `validate_icarus_c2`, `validate_worlds_d`, `validate_worlds_e`, `validate_audio_callers`, `validate_item_gear`, `validate_audio_combat`, `validate_render_effects`, `validate_render_effects3`, `validate_render_effects4`, `validate_render_effects5`, `validate_render_effects6`, `validate_render_effects7`, `validate_render_effects9`, `validate_render_effects10`, `validate_render_effects11`, `validate_render_effects12`, `validate_world_particle_consumers`, `validate_audio_domains`, `validate_audio_items`, `validate_worlds_l`, `validate_audio_charsel`, `validate_item_wings_next`, `validate_worlds_m`, `validate_worlds_g3`, `validate_worlds_after4`, `validate_worlds_after6`, `validate_app_polish1`, `validate_render_effects13`.

## Remaining work and cleanup

The [finding](../research/client-render-effects-013.md#still-open) names every remaining contract:
Flare/b owner writes and collision; Flare02/e smoke01/0x22, /0x23 and 0x7f26/0xa; ground children,
stone/0x13, native ground-skill route and unverified +0x64 clearing; 0x45e's 3..7 decal;
Uruk's world-100 weather input and Muun owner/pose fixtures.

After the final push, append one ready-prs.txt line, then no further push. Remove this lane's scratch
and build products. Keep the worktree, its `input` link and the local branch until the steward merges;
then remove them. Retain the remote branch and four requested 640x400 native viewport PNGs in
`~/Documents/MTM/mu-mac-tools/native/renders/render-effects-013/`.
These are native renders, not original-client captures. No new private input needs to survive cleanup.
