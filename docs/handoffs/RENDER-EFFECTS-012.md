# RENDER-EFFECTS-012

PR-ready: ten bow joint kinds, multishot02/1 and 0x45e's white model colour.
[Finding and addresses](../research/client-render-effects-012.md).

The 33 bow scenes now have **77 → 27 unsupported requests**, with **119 → 119 arrows**.
The 50 removed refusals are 39 joint requests across ten kinds and 11 multishot02 effects.
The ten other combat scenes remain at zero unsupported requests and have identical images.
No pet-specific code changed. Nine bow scenes change visually; the other 24 remain byte-identical.

Started from `origin/claude/render-effects-011` at `a1fe59cb5816abbd7cce89fb39549e87136a4f58` using the
owner-authorized fallback after batch 32 reported failure with PR #292 still open. The fallback includes
011 and its known limits; 012 depends on it. The baseline was taken once from that unchanged base.
After #292 merged at 2026-11-06 03:11:38 UTC, main `9e93e6c9` was merged in `fbb7c282`.
That merge changed no files (`git diff 02a8463f..fbb7c282` is empty), so source checks remain valid.
Worktree: `~/Documents/MTM/worktrees/render-effects-012`, branch `codex/render-effects-012`.
Shared `tools/python`, `evidence`, `input` links are never committed.

## Scope and integration

- `reconstructed/joints/bow_joints.inc`: 0x80e3/4, 0x80e4/1, 0x814c/a, 0x8182/a, 0x8185/a,
  0x85cc/0, 0x828c/2, 0x7f79/c, /12, /16. Subtypes here are hexadecimal.
- `joints.c`: admission/create/move hooks and Flare02/c's per-tail colour in the existing renderer.
- `arrow_fx.inc`: 0x38b5/1 create/move. This model effect is explicitly excluded from arrow counting.
- `native/core/mu_combat.{c,h}`: eight bitmap slots (16 → 24), emitted joint key/skill/colour,
  multishot02's model slot and emitted scale/key, model draw above 0x7a4, and white 0x45e colour.
- `validate_render_effects12`, registry row and portable synthetic tests. The installed combat test's bitmap
  expectation now reads 24. No changes to the world particle table or the other lanes' owned code.

## Scene measurements

All scenes: 640x400 software renderer, Lorencia tile 182,128, actor 3 at 186,128, 30 frames, every fifth frame,
no audio/items/remote players; each bow uses class 2 and `2:skill:24:spider;3:stop`. The ten staff scenes use
skills 1,2,3,4,5,7,8,9,10,14. Inputs are the installed client and the read-only plain objects directory.

| Bow | Unsupported before → after |
|---|---:|
| 0x1300 | 8 → 0 |
| 0x1304, 0x12fd, 0x12ff, 0x1305, 0x130c, 0x132c | 4 → 0 each |
| 0x12fa | 3 → 0 |
| 0x130e | 15 → 0 |
| 0x12f7 | 12 → 12 (0x7f78/b) |
| 0x12fb | 3 → 3 (0x7f79/e) |
| 0x12fc | 4 → 4 (0x7f79/f) |
| 0x130a, 0x131e | 4 → 4 each (0x80e3/5) |
| Other 19 bows | 0 → 0 |

Nine bows above improve; 0x1300 contains two new joint kinds. Those nine scenes change visually.
Four small window-only native PNGs (before/after for 0x1300 and 0x12fa) are kept at
`~/Documents/MTM/mu-mac-tools/native/renders/render-effects-012/`, as requested. These are native renders,
not live-client comparison captures. The black arrow-model surfaces visible on 0x1300 also occur in the baseline.

## Checks

No lane full gate. The steward runs the only combined full gate. All heavy checks used `nice -n 10`,
make at most `-j4`, and at most two validator workers.

| Check | Result | Wall time |
|---|---|---:|
| Final core build, `make -j4` at `c76a168f` | Passed | 9.65 s |
| GL world rebuild after HUD-only main merge, `3bb9cc01` | Passed | 3.94 s |
| New full private comparison, `c76a168f` | 3,000 creates + 3,000 moves + 3,000 full GL streams + 300 effect creates + 300 effect moves; zero mismatches | 33.99 s including mutants |
| New compiled mutants | 22/22 caught, zero equivalent, zero stopped; 3,540 mutant comparison cases; compiled/run once | Included above |
| Initial affected unit modules | 136 tests: 121 passed, 15 private/installed checks skipped | 30.58 s |
| Installed combat and joint tests | 2/2 passed | 8.32 s |
| Focused tests after normalizer correction and APP-POLISH-001 merge | 94 tests: 88 passed, 6 skipped | 52.57 s |
| Installed combat after merge | 1/1 passed | 1.48 s |
| APP-POLISH-002 merge tests + registry manifest | 19 tests: 18 passed, 1 private check skipped | 2.35 s |
| Before / after 33 bows + 10 combat scenes | 77 → 27 / 0 → 0 unsupported; 119 arrows retained | 59.81 / 61.70 s |
| Final 0x130e scene after normalizer correction | Zero unsupported; summary and all image hashes unchanged from the earlier after run | 1.29 s |
| DATA-ACQ-002 baseline / one final default-draw sweep | 32/32 tours, 64 PNGs and 64 object/light dumps byte-identical | 49.19 / 43.44 s |
| Final repository audit | 1,872 files, zero rejected | 15.64 s |

The first full new comparison found three one-ULP 0x828c/2 move differences (20.75 s), corrected by following
0x00cff0d3's component division. The targeted 600-move check then passed in 1.48 s, followed by the successful
full run above. The failing run compiled no mutants. The 22-mutant pass ran once, after the correction.
Earlier small, mutation-free samples were 320 cases (1.42 s) and 640 cases (2.23 s).

The initial unit modules were `native.tests.test_render_effects12`, `test_native_combat`, `test_native_joints`,
`test_render_effects9`, `test_render_effects10`, `test_render_effects11`, `test_render_effects`,
`test_native_render_effects6` (all under `native.tests`), `reconstructed.combat.test_combat`,
`reconstructed.combat.test_skill_fx`, `reconstructed.joints.test_joints`, and `tests.test_validators_manifest`.
The post-correction set was `native.tests.test_render_effects12`, `test_native_combat`, `test_native_joints`,
`test_app_polish`, `test_native_app`, `test_native_data_manifest`, `reconstructed.joints.test_joints`, and
`tests.test_validators_manifest`. The final merge check was `native.tests.test_app_polish2` plus the manifest.
Private wrappers were disabled so they could not repeat compiled mutants; private comparisons ran separately.
The shared-symbol grep covered `MU_COMBAT_BITMAPS`, `MU_COMBAT_MODELS`, the model slot enums,
`mu_jt_kind_supported`, `mu_sfx_is_arrow`, and draw users. The installed bitmap assertion was the only fixed
count to update. No world-particle bitmap size changed.

## Affected registry rows and commits

Thirty existing rows pass their registry expectations, with 697,027 cases in their latest per-row results.
The local runner used the repository's pin resolver/evaluator with compiled-mutant switches removed and two
workers. Meshdraw's numeric `--mutations 300` is randomized input coverage, retained as in the steward tool.
Its initial malformed argument attempt took 0.1 s; model-light and audio-domains initially skipped until their
existing snapshot paths were supplied. Only those three rows were retried. Batch wall times: 415.90 s initial,
330.36 s retries, 25.39 s for the four joint-directory rows after the normalizer correction. Row times below
are the latest successful results, not summed parallel durations.

The initial rows used production commit `fbb7c282`; the three retries finished at `b9308616` (only the new
validator's seed changed). `c76a168f` includes the normalizer correction and main `d69eb2c7` (#293).
The four existing rows declaring `reconstructed/joints` were rerun there. The APP-POLISH-001 merge brought
Swift app code, tests and demo placement, not changes to these validators' compiled C; the scene uses its own
placement. The APP-POLISH-002 merge to `3bb9cc01` brings main `2531746f` (#294): only the `--gfx` adapter changes
in production. Its build and focused tests pass. The default tours omit `--gfx`, so that path is not opened
(`world_tool.c` requires `gl && t->gfx_dir`); no second sweep was run. The tours used the `c76a168f` binary.

| Validator | Cases | Wall time | Tested commit |
|---|---:|---:|---|
| `validate_combat` | 496 | 1.2 s | `fbb7c282` |
| `validate_crypto` | 568 | 26.8 s | `fbb7c282` |
| `validate_item_models` | 4,881 | 14.4 s | `fbb7c282` |
| `validate_joints` | 180 | 1.8 s | `c76a168f` |
| `validate_meshdraw` | 14,619 | 330.3 s | `b9308616` |
| `validate_model_edge` | 954 | 121.0 s | `fbb7c282` |
| `validate_model_light` | 1,433 | 5.7 s | `b9308616` |
| `validate_npc_dialogue` | 18,444 | 4.2 s | `fbb7c282` |
| `validate_protocol` | 800 | 3.3 s | `fbb7c282` |
| `validate_skill_fx` | 660 | 2.6 s | `fbb7c282` |
| `validate_terrain` | 583,500 | 378.7 s | `fbb7c282` |
| `validate_viewport_monsters` | 1,963 | 7.2 s | `fbb7c282` |
| `validate_icarus` | 5,240 | 25.3 s | `c76a168f` |
| `validate_icarus_c2` | 8,400 | 12.9 s | `c76a168f` |
| `validate_worlds_d` | 2,400 | 3.9 s | `fbb7c282` |
| `validate_audio_callers` | 5,528 | 5.2 s | `fbb7c282` |
| `validate_audio_combat` | 19,548 | 43.8 s | `fbb7c282` |
| `validate_render_effects` | 660 | 1.2 s | `fbb7c282` |
| `validate_render_effects3` | 720 | 1.3 s | `fbb7c282` |
| `validate_render_effects4` | 1,920 | 10.7 s | `fbb7c282` |
| `validate_render_effects5` | 1,190 | 5.4 s | `fbb7c282` |
| `validate_render_effects6` | 1,000 | 1.7 s | `fbb7c282` |
| `validate_render_effects7` | 596 | 2.0 s | `fbb7c282` |
| `validate_render_effects9` | 304 | 0.7 s | `c76a168f` |
| `validate_render_effects10` | 154 | 0.8 s | `fbb7c282` |
| `validate_render_effects11` | 176 | 0.4 s | `fbb7c282` |
| `validate_audio_domains` | 2,544 | 24.5 s | `b9308616` |
| `validate_audio_items` | 3,000 | 6.0 s | `fbb7c282` |
| `validate_audio_charsel` | 5,968 | 4.9 s | `fbb7c282` |
| `validate_worlds_after4` | 9,181 | 18.0 s | `fbb7c282` |
| `validate_render_effects12` | 9,600 | 33.99 s | `c76a168f` |

Steward validators: validate_combat, validate_crypto, validate_item_models, validate_joints, validate_meshdraw, validate_model_edge, validate_model_light, validate_npc_dialogue, validate_protocol, validate_skill_fx, validate_terrain, validate_viewport_monsters, validate_icarus, validate_icarus_c2, validate_worlds_d, validate_audio_callers, validate_audio_combat, validate_render_effects, validate_render_effects3, validate_render_effects4, validate_render_effects5, validate_render_effects6, validate_render_effects7, validate_render_effects9, validate_render_effects10, validate_render_effects11, validate_render_effects12, validate_audio_domains, validate_audio_items, validate_audio_charsel, validate_worlds_after4

All listed rows should run **without compiled mutants** at the steward; none needs another mutant pass.
Use the steward helper or `run_validators.py --no-mutants` after TEST-SPEED-001 lands. This lane did not edit
that runner, its cache, or the item executor.

Environment (private inputs remain read-only):

```sh
export MU_RECOVERY_INTEGRATION=1
export MU_GAME_ROOT="$HOME/Library/Application Support/MuTheMatrix/prefix/drive_c/MuTheMatrix"
export MU_SECTION3=$HOME/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin
export MU_OBJECTS_PLAIN_DIR=$HOME/Documents/MTM/mu-mac-tools/native/scratch/objects/live/plain
export MU_SNAPSHOT_DIR=$HOME/Documents/MTM/mu-mac-tools/native/scratch
export MU_LIGHT_OBJECTS=$HOME/Documents/MTM/mu-mac-tools/native/scratch/objects/live/plain/EncTerrain95.plain
export MU_LIGHT_SNAPSHOT=$HOME/Documents/MTM/mu-mac-tools/native/scratch/light/live/dumps/login-a.light
```

No map-effect change requires `MU_LANG_DIR` in this lane.

## Remaining work

The 27 requests above stay explicitly unsupported. See the finding for their missing owner-state and particle
contracts. Ground skills still need 0x703..0x706, stone/0x13, their native route and the +0x64 clearing site.
0x45e's decal is still counted but not drawn for subtypes 3..7. Uruk needs weather input/capture; Muun needs
owners. No live session, network work, memory write, protection work or installed-app change was performed.

## Cleanup

After final push and ready entry: remove this lane's scratch/build directories, shared-input links and owned
worktree/local branch. Preserve the remote branch for the steward and the four requested PNGs above. There are
no new private inputs a later lane needs to retain.
