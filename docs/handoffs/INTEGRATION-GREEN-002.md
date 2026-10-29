# INTEGRATION-GREEN-002 (WIP, stopped on owner request 2026-10-29 ~02:50)

Verification lane. Branch `claude/integration-green-002`. The suite baseline ran on main `34081544`. Validators ran
after merging main `9b821b19` (#265–#268). Method and inputs are those of
[INTEGRATION-GREEN-001](INTEGRATION-GREEN-001.md). The game root is Native Data `setup.json`'s free-runtime prefix
`C:\MuTheMatrix`, with `MU_RECOVERY_INTEGRATION=1`. Also set: `MU_SECTION3` and `MU_EFFECTS_SECTION3` (capture-04
`main-01ced000.bin`), plus the `MU_V14_MANIFEST`, `MU_EDGE_DIAGNOSTICS`, `MU_PATH_DIRECTIONS` and `MU_SNAPSHOT_DIR`
snapshot variables listed there. New for this lane: `MU_RENDER_TIME_OBJECTS=$MU_SNAPSHOT_DIR/fidelity2/live/plain`
(RENDER-TIME-003). The worktree also needs the ignored `input/` symlinked from the main checkout
(`input/main.exe`, for `reconstructed/boot`).

## Private suites (`run_test_suites.py`, MU_GATE_JOBS=2)

| Suite | Pass | Skip | Fail/err | Note |
|---|---:|---:|---:|---|
| reconstructed/boot | 5 | 0 | 0 | first run errored: `input/main.exe` not linked in the worktree (c, local link) |
| asset-recovery, model-recovery, client-memory, record-math, model-codec, camera, path, actors, audio, ui, data, effects, movement | all | 0 | 0 | |
| tests | 183 | 0 | 0 | |
| renderchar 59, charsel 28, hud 19, objects 95, scene 11, combat 38, environment 11, particles 23, items 12, joints 11, names 9, npc 12, price 5, mix 18, helpers 13, raven 6, pets 7, quest 10, skill 16, map 11, social 6, progress 14 | all | 0 | 0 | |
| native/tests | 788 | 26 | 1 + 3 | see failures; skips = Ruffle/mugfx not built, export-group env not set |

## Failures and classes

1. `test_native_combat.InstalledTests.test_lorencia_fight`: `models_loaded` 21, expected 9. **(a) stale.** This
   was not caused by #263. RENDER-EFFECTS-002 (#221) added Ice01, Ice02 and Magic02. RENDER-EFFECTS-004 (#247)
   added Rageful Blow's 9 models. 21 is every `MU_COMBAT_MODELS` slot: 20 `Data/Skill` files, all present in the
   installed client, plus the weapon. Expectation updated; passes.
2. `test_audio_cues.test_original_domain_audio_callers`: `validate_audio_callers.py` no longer linked (undefined
   `mu_abyss_*`, `mu_ignis_*`, `mu_nixies_*`, ...). **(b) harness regression, fixed.** It hard-coded the objects
   dependencies, and later world lanes (RENDER-WORLDS-O/R/R2...) added sources. It now reads
   `reconstructed/objects/Makefile` `SOURCES`. Result: 5,528 cases, 0 mismatches, 18/18 mutants. Passes.
3. `test_native_app.PreviewAppPrivate.test_smoke_over_the_installed_game`: **(c) missing local input.** Setup
   refuses the default scratch's unversioned `lang/`, `objects/live/plain/` and `audio/tables/` exports, by
   DATA-ACQ-004 (#174) design. With an empty `MU_NATIVE_SCRATCH`, the same smoke passes (`smoke: ok`). Fix: the
   owner or a data lane re-exports them with manifests, per `docs/native-data.md` "Regenerate". Test unchanged.
4. `test_render_time.InstalledDataTests` and `test_render_time_003` setUpClass: **(c) env.** `MU_RENDER_TIME_OBJECTS`
   was not set in this run. It is now in the lane env. Not rerun yet.

## Private validators (`run_validators.py --private --jobs 2`, on merged main 9b821b19)

Rows run: 128 pass, 16 skip (all helper rows), 1 fail. Stopped before the last 17 rows.

- `validate_renderchar` fail: items excluded 116 / compared 384, expected 106 / 394. All 384 compared rows match.
  Likely **(a)**: the generic item population changed with the renderchar sources merged in `4d9c2195`
  (probably #265 RENDER-ITEMS-002L). **Not yet verified.** Next step: run the row on the pre-merge commit
  `4c602ded` (this branch's first commit) to confirm 106/394 there, then update `validators.toml` with the PR cited.
- Not run yet: validate_item_chains, item_scalars, item_textures, world_light_name, world_tile_folder,
  worlds_after, worlds_after2, worlds_g2, worlds_g3, worlds_m, worlds_n, worlds_o, worlds_p, worlds_p2, worlds_q,
  worlds_r, worlds_r2.

## Next steps

1. Confirm and update the `validate_renderchar` counts, or classify them (b) if the pre-merge run also gives 116/384.
2. Run the 17 remaining validator rows: `--only <list above>`.
3. Rerun `native/tests` (render_time, with `MU_RENDER_TIME_OBJECTS`) and the export group (`MU_LANG_DIR`,
   `MU_OBJECTS_PLAIN_DIR`, `MU_AUDIO_TABLE`, as in INTEGRATION-GREEN-001).
4. Merge the latest main, rerun the affected suites and the gate, then go PR-ready (status lines and
   `Steward validators: validate_audio_callers,validate_renderchar`).

Local: worktree kept; lane env in `~/Documents/MTM/mu-mac-tools/native/scratch/integration-green-002/env.sh`.
