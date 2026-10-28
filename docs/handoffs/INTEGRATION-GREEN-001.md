# INTEGRATION-GREEN-001

Verification lane. Branch `codex/integration-green-001`, resumed against main `c769a5d`.
The installed app's Native Data setup identifies the game root. Its `main.exe` matches
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.

## Changes and provenance

- Character-create already runs 300 cases on current main. Confirmed 4,368 cases, zero mismatches,
  all 6/6 mutants detected, including the code-page mutant. No further charsel change.
- Recovered the original capture-04 and model manifest in the older analysis directory. All original
  capture pins, including the full section-3 pin for objects, can be satisfied without a live read.
- Effects and tree validators pin only the exact 76,288 initialized bytes they map. A range-only file
  works; changes inside that range and truncation fail before emulation. The fresh guest range differs
  and still fails. Whole capture versus range-only comparison reports agree in every behavior result.
- Re-pinned the model manifest after two byte-identical strict scans. Direct comparison with the old
  manifest found only three export annotations and 17 improved error strings, with identical paths,
  ordering, source hashes, decoded hashes, statuses and model counts.

Full old/new digests, causes, methods and scanner identity are in
[the finding](../research/private-integration-inputs.md). No private bytes or manifests are committed.

## Focused checks

Five manifest validators pass, zero skipped/failed:

| Validator | Coverage | Result |
|---|---|---|
| charcreate | 4,368 cases, 6 mutants | zero mismatches, 6/6 caught |
| effects | 80 cases, 2,342 frames, 46,196 vertices | zero mismatches |
| effect_tree | 110 cases, 1,967 frames, 66,056 vertices | zero mismatches |
| model_codec | 4,048 synthetic cases, 180 v12 files, 3,176,971 payload bytes | zero mismatches |
| client_lea_decode | 1,152 scalar cases, 11,583 v15 files | zero mismatches |

The v15 corpus is compared with the independent native reader. The corpus comparison does not execute
original AVX instructions. Three existing-snapshot checks pass, without making new captures. Effects
unittest suite: 21 passed, zero skipped. Pin and manifest portable checks: 16 + 17 passed. Two input-boundary
regressions exercise both validators and verify rejection before emulation.

## Full gate

The historical 2026-10-24 result was 35/38 suites. On 2026-10-28, the installed target and all provenance
were rechecked, and a third strict scan reproduced the new manifest pin. The installed export baseline
at `8eac05c` passed 8/9 tests; only the old 17-texture expectation failed against 51 loaded textures.
The clean native build failed before generated session headers existed. A regression reproduces that
ordering defect; core objects now wait for generation.

The baseline `tests/` directory ran 150 tests: 140 passed and ten failed/errored because the data volume
ran out of disk space. This includes skill-tree, social, social2, terrain, terrain-remaining and five
synthetic pin checks. The remaining baseline was stopped after seven completed suites because resource
errors invalidate a comparison baseline. No client mismatch or legitimate input skip is inferred from
those resource errors. Full final private and local gates are still required before PR/merge.

## Local artifacts and reproduction

Task scratch directory: `~/Documents/MTM/mu-mac-tools/native/scratch/integration-green-001/`.
It holds `env.sh`, two independent scans, a metadata-only manifest diff, the extracted private effects range,
focused reports, original-loader effects reports, snapshot checks, full baseline suite logs and local gate logs.
The fresh baseline ran detached at `8eac05c` inside this same owned worktree. Its completed logs are in
`before-current/`; no second checkout was created.

Use the worktree's Python, set `MU_RECOVERY_INTEGRATION=1`, and supply `MU_GAME_ROOT`, `MU_EVIDENCE_DIR`,
`MU_SNAPSHOT_DIR`, `MU_SECTION3`, `MU_EFFECTS_SECTION3`, `MU_V14_MANIFEST`, `MU_EDGE_DIAGNOSTICS` and
`MU_PATH_DIRECTIONS`. `env.sh` records exact local locations. Run optional lang/object/audio export tests separately with the research export paths in
`raw-exports-env.sh`, so private export variables do not contaminate synthetic tests. The portable local
gate runs without those export variables or integration flags.

This establishes offline input/validator compatibility. It adds no gameplay fidelity, live service,
new capture, or native Windows evidence.
