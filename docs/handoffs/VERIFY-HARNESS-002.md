# VERIFY-HARNESS-002 handoff

Branch `codex/verify-harness-002`, created from `origin/main` at `5d35f5d`.
Scope is limited to the pin/loader lines in `scripts/map_client_window.py` and
`scripts/model_hierarchy_common.py`, their two `UNMIGRATED` entries and focused regression checks.
The original owning tests and all reconstruction assertions are unchanged.

## Evidence

See [input identities, method and limits](../research/validator-loader-followup.md).
Baseline focused portable run: 61 tests, three explicit private skips, zero failures.
Six additional synthetic checks cover caller-patched region constants and exact size, digest,
missing-file and argparse failures. The baseline passes these six contract checks.

Installed-capture before/after reports, metadata and error outcomes: pending comparison.

## Reproduction

Use the same installed text/data files for both revisions, through ignored `evidence` and
`tools/python` symlinks. Neither link is staged. No game root is configured.

- Mapper: documented three-seed 64 KiB command in [client-window-map](../research/client-window-map.md).
- Hierarchy scan and verify: explicit `--text`, `--data` where required, and new `--output` paths.
- Static frame and render tools: owning test commands with the pinned installed Wine DLL directories.
- UI: owning test command with `--tga-limit 40 --jpeg-large 1 --jpeg-small 25`, without `--game-root`.
- Widgets: `--cases 10`; character-select window: `--cases 20 --mutations`.
- Contract and owning tests: `python -m unittest -v tests.test_harness_loaders
  tests.test_client_window_map tests.test_model_hierarchy tests.test_client_frame_static
  tests.test_client_render_static tests.test_pins`, then private-enabled owning suites.
- Final gate: `bash scripts/local-macos-ci.sh` under the merge queue and lock.

## Delivery and cleanup

Final gate, PR and cleanup: pending.
Task-local reports live under `mu-mac-tools/native/scratch/verify-harness-002` only until delivery;
they contain private derived reports and are deleted after merge. No new input needs to be retained.

## What remains

Eight `UNMIGRATED` entries and the shared Unicorn machine consolidation remain. The excluded
protector-loader scripts are not proposed for this scope. No replay-oracle, live-client, renderer
or new reconstruction coverage is claimed. INTEGRATION-GREEN-001 supersedes the old private-input
failures in the historical VERIFY-HARNESS-001 run.
