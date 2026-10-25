# VERIFY-HARNESS-001 handoff

**Lane:** verification.
**Branch:** `claude/verify-harness`, built on `origin/claude/architect-native-port` (PR #161).
**Plan row:** `docs/design/native-port/plan.md`, section K: "one manifest-driven validator runner; pins in `scripts/pins.py` instead of the pasted digests; `docs/evidence-index.json` regenerated from runs; the orphan validators referenced by tests."

## Result

- Every `scripts/validate_*.py` (91) has a row in `scripts/validators.toml`:
  - 75 rows are runnable validators;
  - 16 are helper modules that `validate_social2.py` imports and runs.
- Every validator row names an owning test inside a `make test` directory, so `make integration` reaches it. A portable test enforces this.
- The capture pins live only in `scripts/pins.py`. A grep test fails as soon as a registered digest is pasted into any other script.
- Private run on this Mac, offline (2026-10-25):
  - **69 pass, 1 fail, 5 skip** of the 75 validators;
  - 1,285,087 compared cases and 678 planted mistakes or negative controls in the passing rows;
  - 117.5 minutes of validator time, about 70 minutes of wall time at 3 jobs.
- The same manifest was also run on an unmodified copy of the tree (`git archive 8efe6e7`). Every report came out identical after dropping timing fields. The one exception is `validate_skill_later`'s seven `slowest.case` entries, which record which case was slowest and so are timing as well. The pin/loader migration moved no result.
- `docs/evidence-index.json`: `validation.validators` is regenerated from that run.

## What changed

### `scripts/pins.py` (new): the one home of the pinned inputs

**The pins.** Each `Pin` holds the SHA-256, the size, the default location, the environment variables that move it, the client address of its first byte, and a description. The registry is `pins.PINS`:

| Pin | Input |
|---|---|
| `text` | restored text, capture 09 |
| `text08` | capture 08, same bytes as `text` |
| `data` | second image section |
| `flag` | trig dispatch flag |
| `feature` | CPU feature word, run10 math capture |
| `feature09` | capture 09, same bytes as `feature` |
| `record_bias`, `record_template` | math-capture records |
| `section3` | x86-linux-capture-04 |
| `directions` | a 64-byte *region* pin at 0x01cf1640 inside any third-section read |
| `target` | main.exe |
| `v14_manifest`, `edge_diagnostics` | model-corpus manifest and diagnostics |
| `lang3`, `lang4`, `quest_lang5`, `skill_lang5`, `skill_tree4` | langread snapshots |
| `light_login`, `objects_login` | NATIVE-LIGHT-001's login-scene snapshot and its decoded object file |

`MATH_CAPTURE_TOOL_SHA256` is also kept here.

**Resolution order:**
1. an explicit path;
2. the pin's environment variables (the names validators and tests already used: `MU_CLIENT_TEXT`, `MU_IMAGE_DATA`/`MU_CLIENT_IMAGE_DATA`, `MU_TRIG_FLAG`, `MU_SECTION3`/`MU_DATA_SECTION`, `MU_PATH_DIRECTIONS`, `MU_LIGHT_SNAPSHOT`, …);
3. `MU_EVIDENCE_DIR`, which defaults to `<repo>/evidence`.

Snapshots resolve under `MU_SNAPSHOT_DIR` and have no default.

**Errors:**
- A missing input raises `PinMissing`, a `FileNotFoundError`. It names the pin, the path tried and the variables that would move it. Nothing falls back to another directory.
- Different bytes raise `PinMismatch`, a `ValueError`.

**Shared loader.** `pins.loader(error, message)` is the one body behind the old `load_pinned`/`check_identity` copies. Each validator keeps the exception type and message that its callers and tests expect.

`pins.load(path, size, digest, mismatch=...)` covers the inline checks. It still takes the module's own constants, which `reconstructed/record-math/test_record_math.py` patches.

**Other helpers:**
- `pins.work_dir(name)` replaces the hardcoded `/tmp` work directories (`MU_VALIDATOR_WORK`).
- `scripts/pins.py --check` lists every pin, where it resolves, and whether that file is present and matching.

### Validators and machines: pin and loader lines only

- **64 `validate_*.py` plus `actor_machine.py` and `renderchar_machine.py`:**
  - their constants are now aliases (`TEXT_SHA256 = pins.TEXT.sha256`, `TEXT_BYTES = pins.TEXT.size`, …). The names are kept because other modules, reports and tests read them;
  - their argparse defaults come from pins;
  - their loaders delegate to pins.
- **The rest:**
  - the other validators use the migrated families' loaders (`am.`, `tracks.`, `tables.`, `vl.`, `vh.`, `vc.`, `common.`), or have no inputs of their own (the social2 helpers);
  - `client_ui_machine.py` had no pins.
- Every `Path.home()/'Documents/main-exe-study/evidence'` fallback is gone. Thirteen validators had one, and that directory no longer exists: social and social2 could not start without explicit paths.
- The `/tmp` defaults of validate_progress and validate_environment are gone.
- **Behaviour changes, all at the input boundary:**
  - validate_fidelity now verifies the flag and feature words (`pins.FLAG.read()`, `pins.FEATURE09.read()`) instead of reading the first 4 bytes unchecked;
  - validators that ignored `MU_CLIENT_TEXT`/`MU_IMAGE_DATA` (combat, skill_fx, names, items, …) now honour them;
  - validate_npc_dialogue no longer substitutes a home-directory feature file when `--feature` is absent: it reports the missing pin.
- `git diff` of the validators touches only these lines. The before/after report comparison below is the proof that nothing else moved.

### `scripts/validators.toml` and `scripts/run_validators.py` (new)

**A manifest row** carries:
- `test`: the owning test, as `file::Class.method`;
- `pins`, `families`, and the expected `cases`/`mutants`, located by `cases_at`/`mutants_at` in the report;
- `needs`, `build` and an optional `prepare` (validate_rotation compiles `scan_trig_midpoints.c` there);
- `args`: the owning test's arguments, with placeholders;
- `expect`: the owning test's report assertions in a small path language (`*` fan-out, `same_as`, `min`, `truthy`, `$stdout contains`, …).

**The runner** takes:
- `--list`;
- `--only` (names or globs);
- `--private`, which refuses to run without `MU_RECOVERY_INTEGRATION=1`;
- `--report DIR`, which writes `<name>.json`, `<name>.log` and `summary.json`;
- `--jobs`;
- `--resume`, which reruns the missing and system-killed rows;
- `--recheck DIR`, which re-judges a finished run against the current manifest without rerunning;
- `--index FILE --from DIR [--note]`, which rewrites only `validation.validators` and `updated`. The rest of the file keeps its layout byte for byte; it is spliced, and the result is checked.

A row whose input is absent is a skip naming the input. A row whose input differs from its pin is a fail. A count that differs from the row's `cases`/`mutants` is also a fail.

### Tests

**`tests/test_pins.py`** (portable, 16 tests):
- resolution, identity, region pins, and the loader and error contracts;
- **the grep tests**: no digest registered in pins.py appears in any other `scripts/*.py`; no script joins its own evidence path or falls back to `main-exe-study`; no validator or machine declares a module-level input digest. The only exception is the `FUNCTION_SHA256` routine-body constants;
- ten scripts outside this lane's ownership still paste pins or evidence paths and are listed in `UNMIGRATED`, each with what it pastes: `combat_static`, `extract_audio_tables`, `items_static`, `loader_emulate`, `loader_inspect`, `loader_recover`, `loader_trace_static`, `loader_validate`, `map_client_window`, `model_hierarchy_common`. A companion test fails when one is migrated but left on the list.

**`tests/test_validators_manifest.py`** (portable, 17 tests):
- every validator has a row and every row has a validator;
- every owning test exists, names its validator, has the named class and method, and lies in a `make test` directory;
- every helper is imported by its family;
- orphan rows point at the orphan suite;
- manifest shape errors are reported;
- the expectation operators, input skip/fail, `--private` refusal, index regeneration, and layout preservation, all on synthetic data.

**`tests/test_orphan_validators_private.py`** (private):
- one method per orphan row, run through the manifest row. These are the 20 validators that no test ran: `helpers`, `item_price`, `item_services`, `map`, `map_polish`, `mix`, `mix_manager`, `mount_visuals`, `pets`, `players`, `progress`, `protocol`, `quest2`, `quest_polish`, `raven`, `skill_later`, `skill_tree`, `social`, `social2`, `terrain`;
- ten of these are the brief's list. The other ten were only imported for ctypes helpers or named in a docstring; their tests never ran the comparison. The 16 social2 helpers run inside `test_social2`;
- skips without `MU_RECOVERY_INTEGRATION`;
- under integration, missing text/data is an error; other absent inputs (snapshot, game root, compiler) are a named skip.

### `docs/evidence-index.json`

- `validation.validators` holds:
  - generator, date, commit, provenance note, environment;
  - totals and the pin digests;
  - per validator: status, owning test, cases/mutants where the report counts them, expectations passed, the reason (local paths replaced by `$MU_EVIDENCE_DIR`, `<repo>`, `~`), and pins;
  - the helper list.
- `updated` is now 2026-10-25.
- The findings and the other `validation` fields are unchanged. They are from 2026-10-17, and no report proves or disproves them.

## Checks actually run

1. **`make test`** (portable, full build, worktree): exit 0. 38 suites, 1,224 tests, 153 skipped.
2. **Private runner, migrated tree**, with `MU_RECOVERY_INTEGRATION=1`, `MU_GAME_ROOT=~/Documents/MTM/mtmOriginal`, `MU_EVIDENCE_DIR=<main checkout>/evidence`, `MU_SNAPSHOT_DIR=~/Documents/MTM/mu-mac-tools/native/scratch` and `MU_PATH_DIRECTIONS=<evidence>/x86-guest-sec3-25/main-01ced000.bin`. No live game, no game lock, no network.

   Results:

   | Result | Validators |
   |---|---|
   | pass (69) | every validator not listed below |
   | **fail (1)** | `charcreate` |
   | **skip (5)** | `effects`, `effect_tree`, `objects`, `client_lea_decode`, `model_codec` |

   Why:
   - **`charcreate` fails:** the owning test's 60 cases catch 5 of 6 planted mistakes and miss the code page one. This is the known cause from 2026-10-24; 300 cases catch 6 of 6.
   - **`effects`, `effect_tree`, `objects` skip:** pin `section3` is missing (x86-linux-capture-04). The 2026-10-24 guest rebuild did not reproduce its whole-file digest.
   - **`client_lea_decode`, `model_codec` skip:** pin `v14_manifest` is missing. The install now scans to 27afde53 instead of the pinned fffcbad9.

   These are the three known causes behind 2026-10-24's 35 of 38. The memory note filed the first under "charsel"; it is charcreate, in the same test directory.
3. **The same run on the unmigrated tree** (a `git archive` of 8efe6e7, built separately) gave 69/1/5 with the same reasons. `compare_runs.py`: 69 reports identical after dropping timing keys, and `skill_later` differing only in `slowest.case`. The 5 skips and 16 helpers have no reports and the same status.
4. **In-process private suites** under integration: `reconstructed/client-memory` (10), `reconstructed/record-math` (23) and `reconstructed/scene` (11), all OK. They call `validate()`/`main()` directly, so they also cover the loader contracts.
5. **Orphan suite** under integration (`python -m unittest -v tests.test_orphan_validators_private`, same environment): **20 tests, all OK, 2,638 s**. Without `MU_RECOVERY_INTEGRATION` all 20 skip, as part of check 1.

Per-validator numbers come from the migrated run. "Cases" and "mutants" are what each report counts at its `cases_at`/`mutants_at`.

| Validator | Result | Cases | Mutants | Seconds | Owning test |
|---|---|---:|---:|---:|---|
| `actors` | pass | 22542 | 3 | 18.3 | `reconstructed/actors/test_actors.py` |
| `audio` | pass | 10367 | 232 | 19.3 | `reconstructed/audio/test_client_audio.py` |
| `bone_tracks` | pass | 738 |  | 4.6 | `reconstructed/model-codec/test_bone_tracks.py` |
| `camera` | pass | 2180 | 13 | 12.5 | `reconstructed/camera/test_client_camera.py` |
| `character` | pass | 1532 | 1 | 42.9 | `reconstructed/model-codec/test_character.py` |
| `charcreate` | fail | 1488 | 6 | 27.5 | `reconstructed/charsel/test_charcreate.py` |
| `charsel` | pass | 360 | 12 | 9.3 | `reconstructed/charsel/test_charsel.py` |
| `charsel_gfx` | pass | 420 | 5 | 6.4 | `reconstructed/charsel/test_charsel_gfx.py` |
| `charsel_window` | pass | 20 | 7 | 28.7 | `reconstructed/charsel/test_charsel.py` |
| `charsel_world` | pass | 1200 |  | 2.8 | `tests/test_charsel_world_private.py` |
| `client_clear` | pass | 768 |  | 0.6 | `reconstructed/client-memory/test_clear64.py` |
| `client_copy` | pass | 393 |  | 0.2 | `reconstructed/client-memory/test_copy64.py` |
| `client_lea_decode` | skip |  |  |  | `reconstructed/model-codec/test_client_lea_decode.py` |
| `client_lea_key` | pass | 1320 |  | 0.8 | `reconstructed/model-codec/test_client_lea.py` |
| `combat` | pass | 496 | 12 | 1.1 | `reconstructed/combat/test_combat.py` |
| `data_tables` | pass | 266 | 51 | 59.1 | `tests/test_data_tables_private.py` |
| `effect_tree` | skip |  |  |  | `reconstructed/effects/test_effect_tree.py` |
| `effects` | skip |  |  |  | `reconstructed/effects/test_effects.py` |
| `environment` | pass | 400 | 10 | 829.8 | `reconstructed/environment/test_environment.py` |
| `fidelity` | pass | 991 |  | 66.4 | `native/tests/test_native_fidelity.py` |
| `gfx3` | pass |  | 5 | 7.1 | `native/tests/test_native_gfx3.py` |
| `helpers` | pass | 8667 | 11 | 253.8 | `tests/test_orphan_validators_private.py` |
| `hero_sound` | pass | 2000 |  | 3.8 | `reconstructed/audio/test_hero_sound.py` |
| `hud` | pass | 48 |  | 113.5 | `reconstructed/hud/test_hud.py` |
| `item_fields` | pass | 4881 |  | 26.0 | `tests/test_data_tables_private.py` |
| `item_models` | pass | 4881 |  | 19.6 | `tests/test_data_tables_private.py` |
| `item_price` | pass | 290639 | 5 | 335.8 | `tests/test_orphan_validators_private.py` |
| `item_services` | pass | 29952 | 6 | 4.2 | `tests/test_orphan_validators_private.py` |
| `items` | pass | 444 | 11 | 3.1 | `reconstructed/items/test_items.py` |
| `joints` | pass | 180 | 9 | 2.6 | `reconstructed/joints/test_joints.py` |
| `lang` | pass | 47276 | 8 | 59.3 | `native/tests/test_native_lang.py` |
| `login_world` | pass | 1200 |  | 3.1 | `tests/test_login_world_private.py` |
| `map` | pass | 5001 | 10 | 219.6 | `tests/test_orphan_validators_private.py` |
| `map_polish` | pass | 876 | 3 | 1.6 | `tests/test_orphan_validators_private.py` |
| `meshdraw` | pass | 14619 | 4 | 504.5 | `native/tests/test_native_viewer.py` |
| `mix` | pass | 52533 | 11 | 20.6 | `tests/test_orphan_validators_private.py` |
| `mix_manager` | pass | 16021 | 6 | 13.3 | `tests/test_orphan_validators_private.py` |
| `model_codec` | skip |  |  |  | `reconstructed/model-codec/test_model_codec.py` |
| `model_edge` | pass | 954 |  | 151.6 | `reconstructed/model-codec/test_model_reader.py` |
| `model_light` | pass | 1433 |  | 6.5 | `tests/test_model_light_private.py` |
| `mount_visuals` | pass | 8400 |  | 10.0 | `tests/test_orphan_validators_private.py` |
| `movement` | pass | 6614 | 16 | 314.8 | `reconstructed/movement/test_client_movement.py` |
| `names` | pass |  | 12 | 16.2 | `reconstructed/names/test_names.py` |
| `npc` | pass | 16127 | 5 | 25.3 | `native/tests/test_native_npc.py` |
| `npc_dialogue` | pass | 18444 | 5 | 11.1 | `native/tests/test_native_lang2.py` |
| `object_render` | pass | 1984 |  | 5.0 | `tests/test_object_render_private.py` |
| `objects` | skip |  |  |  | `tests/test_objects_private.py` |
| `particles` | pass | 407 | 22 | 1.6 | `reconstructed/particles/test_particles.py` |
| `path` | pass | 4719 | 30 | 230.8 | `reconstructed/path/test_client_path.py` |
| `pets` | pass | 1062 | 9 | 290.0 | `tests/test_orphan_validators_private.py` |
| `players` | pass | 4768 | 7 | 8.4 | `tests/test_orphan_validators_private.py` |
| `pose_builder` | pass | 2055 | 2 | 11.9 | `reconstructed/model-codec/test_pose_builder.py` |
| `pose_concat` | pass | 5176 |  | 8.1 | `reconstructed/record-math/test_pose_concat.py` |
| `progress` | pass | 10503 | 16 | 173.4 | `tests/test_orphan_validators_private.py` |
| `protocol` | pass | 800 |  | 3.1 | `tests/test_orphan_validators_private.py` |
| `quest` | pass | 8203 | 6 | 130.8 | `native/tests/test_native_quest.py` |
| `quest2` | pass | 7004 | 5 | 521.2 | `tests/test_orphan_validators_private.py` |
| `quest_polish` | pass | 2001 | 2 | 4.3 | `tests/test_orphan_validators_private.py` |
| `raven` | pass | 4000 | 4 | 160.4 | `tests/test_orphan_validators_private.py` |
| `record_math` | pass | 2730 |  | 6.0 | `reconstructed/record-math/test_record_math.py` |
| `renderchar` | pass | 638 |  | 44.7 | `reconstructed/renderchar/test_renderchar.py` |
| `rotation` | pass | 8012 |  | 13.0 | `reconstructed/record-math/test_rotation.py` |
| `scene` | pass |  |  | 1.5 | `reconstructed/scene/test_scene.py` |
| `skill` | pass | 9696 | 11 | 351.8 | `native/tests/test_native_skill.py` |
| `skill_fx` | pass | 660 | 20 | 1.5 | `reconstructed/combat/test_skill_fx.py` |
| `skill_later` | pass | 2935 | 10 | 471.6 | `tests/test_orphan_validators_private.py` |
| `skill_server` | pass | 548 | 6 | 74.0 | `native/tests/test_native_skill.py` |
| `skill_tree` | pass | 7876 | 3 | 249.8 | `tests/test_orphan_validators_private.py` |
| `skinning` | pass | 2303 | 4 | 12.6 | `reconstructed/model-codec/test_skinning.py` |
| `social` | pass | 7000 | 10 | 4.5 | `tests/test_orphan_validators_private.py` |
| `social2` | pass | 29700 | 36 | 489.0 | `tests/test_orphan_validators_private.py` |
| `terrain` | pass | 583500 |  | 298.2 | `tests/test_orphan_validators_private.py` |
| `ui` | pass | 794 |  | 146.4 | `reconstructed/ui/test_ui.py` |
| `ui_widgets` | pass | 630 |  | 77.0 | `reconstructed/ui/test_ui_widgets.py` |
| `world_fidelity` | pass | 200 | 2 | 1.0 | `tests/test_world_fidelity_private.py` |

## Artifacts

All in ignored, local-only directories:
- `~/Documents/MTM/mu-the-matrix-native/verify-runs/20261025-verify-harness-001/`:
  - `baseline/` and `migrated/`: each validator's `<name>.json` report, `<name>.log` and `summary.json`;
  - `compare.txt`;
  - `compare_runs.py` and `env.sh`, the run environment.
- The unmigrated copy of the tree used for the baseline was a session scratch directory and is not kept.

To reproduce:
```
. verify-runs/20261025-verify-harness-001/env.sh
scripts/run_validators.py --private --report DIR --jobs 3
scripts/run_validators.py --index docs/evidence-index.json --from DIR
```
Use three jobs at most. Six jobs, alongside other lanes' runs, got validators killed by macOS memory pressure (exit -9). That is what `--resume` is for.

## Deviations from the plan and the sketch

- **"A shared Unicorn machine for the 19 standalone setups":** not done. It was the optional step 5, and it is left out entirely: no machine was restructured.
- **Scope of the grep test:**
  - It covers `scripts/*.py`. Ten scripts outside this lane's ownership are on an explicit, self-checking `UNMIGRATED` list.
  - Test files elsewhere still contain the text digest, e.g. `reconstructed/actors/test_actors.py`. Docs and generated headers carry digests by design: the evidence rules require the target SHA-256 to be stated.
  - Single-routine body digests (`ROUTINES`/`BODIES` tables, `FUNCTION_SHA256`) stay with their families, because they define what is compared rather than which input is loaded.
- **Manifest rows that differ from the owning test's argv:**
  - every row writes a JSON report;
  - `client_clear`, `client_copy`, `record_math` and `scene` use the command-line form of the test's in-process call;
  - `renderchar` merges its three test invocations into one run, and `fidelity` merges two;
  - `skill` and `skill_server` pass `--snapshot {lang3}`, where the test relies on the `SNAP` variable;
  - `model_light` uses the login-scene pins;
  - **`environment`** runs the documented 400-case, 10-mutant run. The test's 8-case run reaches 46 of 94 branch probes. The validator reports that as exit 1, and the test ignores the exit.
- **New pins without documented digests.** `lang3`, `skill_tree4`, `light_login` and `objects_login` were pinned from the local copies, the ones the existing findings came from; the docs never recorded their SHA-256. `lang4`, `quest_lang5` and `skill_lang5` match `docs/research/client-maps.md`.
- **One evidence variable name.** pins uses `MU_EVIDENCE_DIR`, as the brief says. The effects tests read `MU_EVIDENCE`. They were left alone because they are not owned by this lane.

## Open items

- **Other lanes' new scripts.** `validate_dispatch.py`, `validate_crypto.py`, `validate_decode.py` and `validate_account*.py` are not on this branch. When they merge they need:
  - a manifest row each: `test_validators_manifest` fails for a `validate_*.py` without one;
  - their inputs from `scripts/pins.py`: `test_pins` fails if they paste a registered digest or an evidence path. Missing pins should be added to `pins.PINS` there.
- **`reconstructed/charsel/test_charcreate.py`** should use `--cases 300`, where the mutant set is complete. It is not owned by this lane. The manifest row mirrors the test, so it shows the failure.
- **Missing pinned inputs:**
  - `section3` blocks effects, effect_tree and objects. movement's optional data-section check also skips quietly without it; that is the validator's own optional semantics, and its report records `data_section: null`. Re-pinning to `x86-guest-sec3-25` needs a decision, because that read has a different whole-file digest. The region-pin approach used for `directions` may serve objects and effects.
  - `v14_manifest` blocks lea_decode and model_codec: the verified-v14 corpus needs regenerating.
- **Migrate the ten `UNMIGRATED` scripts**, pin and loader lines only, then remove them from the list.
- **Runtime.**
  - The orphan suite adds about an hour to `make integration`. social2, quest2 and skill_later take roughly 8 minutes each.
  - `skill_later` runs 25 cases per family, not the documented 6,510 (21 parallel processes). All 10 mutants are still caught.
- **Manifest notes for the orphan rows (from the surveys):**
  - `terrain` always exits 0, so only its expectations can fail it;
  - `raven --mutations` rebuilds `reconstructed/raven` in place;
  - `protocol` exits 0 without a report when its inputs are absent, which the runner reports as "no JSON report".
- **For the orchestrator to fold into `docs/setup.md`:** `MU_EVIDENCE_DIR`, `MU_SNAPSHOT_DIR`, `MU_VALIDATOR_WORK`, `scripts/pins.py --check` and `scripts/run_validators.py`.

## Next step

VERIFY-REPLAY-001, after LAYOUT-001 lands. `scripts/replay_oracle.py` gets its pins (text, data, the layout snapshot) from `scripts/pins.py` and its own manifest row. Before that: add the manifest rows and pins for the wire and crypto lanes' validators as they merge.
