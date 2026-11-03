# INTEGRATION-GREEN-002

Verification lane: every private suite and every registered private validator on current main, with each failure
classed (a) stale expectation, (b) real regression or (c) missing local input. Branch
`claude/integration-green-002`. Started on main `34081544` (2026-10-28), resumed 2026-11-03 on main `d5ffde0a`
(merged as `fb691856`) after a clean rebuild (macOS 27.2, Apple clang 21.0.0). Everything below is on the merged
tree unless marked otherwise.

## Environment

Method and inputs as in [INTEGRATION-GREEN-001](INTEGRATION-GREEN-001.md). `S` = `~/Documents/MTM/mu-mac-tools/native/scratch`.

- `MU_RECOVERY_INTEGRATION=1`; `MU_GAME_ROOT` = Native Data `setup.json`'s game root (the free-runtime prefix's
  `drive_c/MuTheMatrix`); `MU_EVIDENCE_DIR` = the main checkout's `evidence/`.
- `MU_SECTION3` = `MU_EFFECTS_SECTION3` = `~/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin`;
  `MU_V14_MANIFEST`, `MU_EDGE_DIAGNOSTICS`, `MU_PATH_DIRECTIONS` as in INTEGRATION-GREEN-001.
- `MU_SNAPSHOT_DIR=$S`, `MU_LANG_SNAPSHOT=$S/lang/live/lang3.bin`, `MU_QUEST_SNAPSHOT=$S/lang/live/lang4.bin`,
  `MU_LIGHT_SNAPSHOT`, `MU_LIGHT_OBJECTS`, `MU_CHARSEL_DUMP_DIR`, `MU_LOGIN_DUMP_DIR`, `MU_OBJECTS_DUMP_DIR` as there.
- New: `MU_RENDER_TIME_OBJECTS=$S/fidelity2/live/plain` (RENDER-TIME-003) for the two render_time private classes.
- Export group only (kept out of the suite run so exports cannot reach synthetic tests): `MU_LANG_DIR=$S/lang`,
  `MU_OBJECTS_PLAIN_DIR=$S/objects/live/plain`, `MU_AUDIO_TABLE=<a current audio-tables.tsv>` and
  `SNAP=$MU_LANG_SNAPSHOT` (test_native_skill `Installed.test_validator`).
- A new worktree also needs the ignored `input/` (for `input/main.exe`, `reconstructed/boot`) symlinked from the
  main checkout, like `tools/python` and `evidence/`. Never committed.

## Failures and their classes

| # | Check | Class | Resolution |
|---|---|---|---|
| 1 | `test_native_combat` `InstalledTests.test_lorencia_fight`: `models_loaded` 21, expected 9 | (a) | Not #263. RENDER-EFFECTS-002 (#221) added Ice01/Ice02/Magic02, RENDER-EFFECTS-004 (#247) Rageful Blow's 9 models; 21 is every `MU_COMBAT_MODELS` slot (20 `Data/Skill` files, all installed, + the weapon). Expectation updated. |
| 2 | `test_audio_cues.test_original_domain_audio_callers` (`validate_audio_callers.py` link error: `mu_abyss_*`, `mu_ignis_*`, `mu_nixies_*` ...) | (b) fixed | The validator hard-coded `reconstructed/objects` sources (patched once before in `244f20a8`) and RENDER-WORLDS-O/R/R2 added more. It now reads `reconstructed/objects/Makefile` `SOURCES`. 5,528 cases, 0 mismatches, 18/18 mutants. |
| 3 | `test_native_particles` `InstalledLorenciaFires.test_fires`: 62 bitmap slots, Map_Smoke1 at 50 | (a) | RENDER-EFFECTS-005 (#257, `5dd35606`) added smoke_line03 0x83de and lighting01_10cha 0x84e2 before Map_Smoke1; both load. Export-gated, so no lane ran it. Expectation updated. |
| 4 | `validate_renderchar` (and the owning `test_renderchar` private test): 4 of 398 item cases mismatch | **(b) open** | From RENDER-ITEMS-002M (#275, `efc48920`). The C emits `MU_RC_ENTRY_COLOR` (glColor) records where the client calls no glColor: types 0x2702 (level -0x2f, quality 5), 0x10f6 (level 0x7a, q 4), 0x0ef9 (render type 0x40042, q 2); without the COLOR records the streams are identical. 0x1c24 (level 8, ext 0x36, q 9): the client draws nothing, the C draws 5 entries. #275 verified its glColor rule with `validate_item_carry` (292 fixed states per type); the generic random states here reach other branches. Not fixed here: it needs the client's glColor branch conditions re-derived (RENDER-ITEMS lane). The row's `items.excluded/compared` expectation (106/394) is also stale: it is a seeded sample over the generic item population, which grows with every item merge (generic types 7,665 at `4c602ded`, 7,751 after #265, 7,860 after #275; excluded/compared 112/388, 116/384, 102/398). Left as is until the mismatch is fixed; the fix lane re-records them. |
| 5 | `test_native_item_textures.test_private_installed_survey`: `white_types` 111, expected < 30 | **(b) open** | #266 (RENDER-ITEMS-TEX-002) measured 28 on its branch head `37a1a0aa` (984 implemented types). Main gives 67 from #266's own merge (`c77c3d26`, with #265's 1,070 implemented types) and 111 after #275 (1,179). 77 of the 111 white types break the test's own invariant (white only for special meshes or the unregistered index 0): the new item types draw meshes bound to 56 bitmap indices (0x7fe7, 0x8186, 0x82e3, 0x8531 ...) that TEX-002's registration does not resolve. Not a stale number; needs the item texture registration extended (RENDER-ITEMS-TEX lane). |
| 6 | `test_native_app` `PreviewAppPrivate.test_smoke_over_the_installed_game` | (c) | Setup refuses `$S/lang`, `$S/objects/live/plain` and `$S/audio/tables`: they have no Native Data manifest (DATA-ACQ-004, #174, by design). With an empty `MU_NATIVE_SCRATCH` the same smoke passes (`smoke: ok`). Needs those exports regenerated with manifests per `docs/native-data.md` "Regenerate"; the test always uses the default scratch. |
| 7 | `test_native_audio.test_private_installed_audio` with `MU_AUDIO_TABLE=$S/audio/tables/audio-tables.tsv`: music index 44 unresolved | (c) | That table is from 2026-10-17, before AUDIO-002F resolved index 44. A table regenerated with `scripts/extract_audio_tables.py` (1,515 sites, 1,514 resolved) passes. Same regeneration as 6. |
| 8 | `reconstructed/boot` decoder test: `input/main.exe` missing | (c) local link | Symlink `input/` from the main checkout. Passes. |
| 9 | `test_render_time` `InstalledDataTests`, `test_render_time_003` setUpClass | (c) env | `MU_RENDER_TIME_OBJECTS` was unset; with it both pass. |

## Private suites

`run_test_suites.py`, `MU_GATE_JOBS=2`, the environment above (export variables unset).

| Suite | Ran | Pass | Skip | Fail/err | Note |
|---|---:|---:|---:|---:|---|
| reconstructed/boot | 5 | 5 | 0 | 0 | after the `input/` link (8) |
| asset-recovery 12, model-recovery 36, client-memory 10, record-math 23, model-codec 58, camera 18, path 30, actors 16, audio 36, ui 26, data 13, effects 21, movement 13 | 312 | 312 | 0 | 0 | |
| tests | 185 | 185 | 0 | 0 | |
| reconstructed/renderchar | 67 | 66 | 0 | 1 | `test_private_original_render_instructions` runs `validate_renderchar`: (b) open, 4 |
| charsel 28, hud 19, objects 108, scene 11, combat 38, environment 15, particles 23, items 12, joints 15, names 9, npc 12, price 5, mix 18, helpers 13, raven 6, pets 7, quest 10, skill 16, map 11, social 6, progress 14 | 396 | 396 | 0 | 0 | |
| native/tests | 831 | 803 | 26 | 2 | `test_native_item_textures` (b) open, 5; `test_native_app` private smoke (c), 6. Fixed: 1, 2. |
| **Total, 38 suites** | **1,796** | **1,767** | **26** | **3** | |

Export group, separately with the export variables: PrivateTables, PrivateTravel, LiveReadPrivateTests,
PrivateCharselTests (2), InstalledTormentaJoints, InstalledLorenciaFires, test_native_skill Installed (2),
InstalledLoginSceneTests, test_private_installed_audio: 11/11 pass after 3 and with a regenerated audio table (7).

Remaining skips (26 in `native/tests`): 11 need `native/gfx/mugfx` / a pinned Ruffle checkout, 2 the Metal GFx
library, 2 converted quest/names movies; the other 11 are the export group above, which passes when run with it.

## Private validators

`run_validators.py --private --jobs 2` on the merged tree: **165 rows: 148 pass, 16 skip (helper modules, run
through their parents), 1 fail (`validate_renderchar`, 4 above)**. 157 rows in one run (stopped by the 2-hour
background limit), the last 8 (`validate_item_carry`, `item_textures`, `worlds_after`, `worlds_after2`,
`worlds_g3`, `worlds_q`, `worlds_q2`, `worlds_r2`) with `--only`. No row skipped for a missing input.

## Gate

`nice -n 10 bash scripts/local-macos-ci.sh` on the merged tree (`14dbe280` + docs), private variables unset: **38 suites, 1,796 tests, 1,558 pass, 238 explicit skips, 0 failures**; fixture scenarios ok; viewer and live-reader builds ok; audit 1,798 staged files, 0 rejected.

## Follow-ups (named, not fixed here)

1. RENDER-ITEMS-002M fix: the glColor record conditions in `reconstructed/renderchar/renderchar.c` for the
   generic states in 4 (cases above reproduce with `validate_renderchar --cases 500` at the default seed), and
   0x1c24's empty client stream; then re-record `validate_renderchar`'s `items.excluded/compared`.
2. RENDER-ITEMS-TEX: register the 56 bitmap indices the post-#265/#275 item types bind (5), and restore
   `white_types < 30` (or re-measure it with a reason).
3. DATA: regenerate the default scratch exports (`lang`, `objects/live/plain`, `audio/tables`) with Native Data
   manifests (6, 7). Owner data; this lane did not overwrite it.

## Cleanup

Lane scratch deleted except `env.sh`/`env-export.sh` (the environment above). No renders. Probe worktrees used
for the bisections were removed.
