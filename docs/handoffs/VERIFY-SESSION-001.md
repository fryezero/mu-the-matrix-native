# VERIFY-SESSION-001 handoff

Branch: `codex/verify-session-001`. Base: `a9128ef`. Scope: discovered full-stack fixture suites and
verification skill support. Work was confined to the dedicated worktree. No native runtime source changed.

## Result

- `scripts/run_fixture_scenarios.py` discovers scenarios and checks every ops domain has a scenario by
  filename. Later domain lanes add files without editing a central list.
- `make test` runs every scenario via `native/tests/test_fixture_scenarios.py`. The local Mac gate also
  runs the suite explicitly and retains reports under `verify-runs/ci-fixtures-*/suite/`.
- Two hero scenarios, all eight bound hero routes, 17 inbound plaintext frames, 21 expectations,
  zero unbound and undecodable frames on each scenario.
- `verify-mu-native` supports `run-tool.sh RUN NAME --fixture [SCENARIO]`, optional inbound script events,
  per-route journal rows, totals and `unrecovered_by_intent`. The feature map and recipe describe the
  seeded session/stub-world boundary. `new-run.sh` records the session binary digest.
- Each scenario reports one unrecovered `master_point` intent. The progress scenario still has two
  unsent crypto-dependent reports. Those counts remain visible for later milestones.

## Verification

- Baseline `bash scripts/local-macos-ci.sh tools/python/bin/python`: 1,283 tests, 155 skips, pass.
- Targeted new suites: 8 portable policy tests and 8 native end-to-end tests, pass.
- Verification skill recipes: 27 drives across scene flow, walk/run/zoom, model, terrain, protocol and
  fixture modes, pass with their expected refusals. Model GL comparison: 8 pixels over 8/255,
  mean channel difference 0.0034. Terrain: 3,960/64,000 pixels over 8/255. All three documented software
  model hashes unchanged. The settings file listing and digests were unchanged before/after the drives.
- Visually inspected the model, terrain, login and windowed-world PNGs. They show the documented
  synthetic geometry/noise and offline labels. No real-client screenshot was taken.
- `bash scripts/local-macos-ci.sh` at `6b0169d`: 1,299 tests, 154 skips, pass. The additional explicit
  discovered fixture suite passed both scenarios; the repository audit rejected zero files.
- Integrated gate at `83734e0`, including main through DATA-ACQ-003 merge `ce337ba`: 1,313 tests,
  155 skips, zero failures. Both scenarios passed again with the counts above; audit: 1,128 files,
  zero rejected. The earlier post-layout gate at `afc84cd` passed 1,301 tests with 155 skips.
- Final gate at `e7be7a5`, after CHARSEL-RT-001 merge `47c7b00`: 1,313 tests, 155 skips, zero failures;
  both scenarios passed; audit: 1,142 files, zero rejected. All 27 skill drives were re-proven again
  on these integrated binaries, with the same model/terrain thresholds, software hashes and unchanged
  settings. Final proof is in renders `recipes-final/`; the suite is in scratch `charsel-integrated-suite/`.
- Final self-review against AGENTS.md and the milestone scope found no remaining standards or spec
  defects. The timeout test uses a deterministic control; tab-separated fixture directives have explicit
  scheduling and endpoint checks. No independent review or new private validation is claimed.

## Evidence

Local, ignored proof is retained outside the disposable worktree under
`~/Documents/MTM/mu-mac-tools/native/scratch/verify-session-001/`. It includes the gate logs, recipe driver,
the two suite journals and schema-1 summary. Recipe renders and full helper proof are in
`~/Documents/MTM/mu-mac-tools/native/renders/verify-session-001/recipes/`, recorded at code checkpoint
`6b0169d` with binary digests in `run.json`. Authored code and synthetic scenarios alone
are committed. The Python worktree symlink is not committed.

The final gate's suite is copied to scratch `integrated-suite/`. Every run, including failed recipe
attempts, is archived under renders `worktree-verify-runs/`. The session binary digest still matches the
recipe run. The main checkout is on another lane's `codex/input-001`; cleanup leaves it unchanged.

The runner records the current commit, dirty state and binary/script digests; the skill's `run.json`
records the native binaries. The finding explains the JSON contract and limits:
[native-session-verification](../research/native-session-verification.md).

## Next steps and limits

- Each migrated domain adds `<domain>-*.scn` files with inbound frames and end-state expectations.
- Reduce the reported `master_point` unrecovered counts when its request body is reconstructed.
- Wire crypto, session-fed product world/scene flow, the recovered dispatcher and replay oracle remain
  separate work. No live-service or new original-instruction equality claim is made here.
- The pre-existing progress handler comparisons remain unchanged and are referenced by SESSION-CORE-001.
