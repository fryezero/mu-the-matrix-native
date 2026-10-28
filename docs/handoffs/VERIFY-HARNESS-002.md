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

All eight installed-capture callers exit 0 before and after. Python 3.12.15 and Capstone 5.0.7
are the same for both runs. Six complete reports are byte-identical. The only changes in the other two
reports are `widgets.server_window.seconds`, 4.6 to 4.8, and
`charsel_window.charsel_window.seconds`, 7.1 to 7.3. Removing exactly those fields makes all eight
parsed reports equal. No result, count, mutant, assertion or metadata field is dropped.

| Caller | Before report SHA-256 | After report SHA-256 |
|---|---|---|
| `map` | `62a9711a6e9953e299649e8a8dd532173d8b42c7700ae077408a46e8a1822733` | `62a9711a6e9953e299649e8a8dd532173d8b42c7700ae077408a46e8a1822733` |
| `hierarchy_scan` | `b64d2b8c54e7322325af1f67deca75de7ba07092d74c9f8cc5cc6d4f53300c2c` | `b64d2b8c54e7322325af1f67deca75de7ba07092d74c9f8cc5cc6d4f53300c2c` |
| `hierarchy_verify` | `0dd56167e9149152357b59dd7bced0dd7d33931b827194dcd140b3b51718d279` | `0dd56167e9149152357b59dd7bced0dd7d33931b827194dcd140b3b51718d279` |
| `render_static` | `924b0b0b5cd6e1b0ac0a1ce44778753e77af6285d06674a0b4489f8b2c2f1b30` | `924b0b0b5cd6e1b0ac0a1ce44778753e77af6285d06674a0b4489f8b2c2f1b30` |
| `frame_static` | `080dbe9ab2d7b2eaad751c36eb2820465d0f203e239b309b210f0a2f61e2af72` | `080dbe9ab2d7b2eaad751c36eb2820465d0f203e239b309b210f0a2f61e2af72` |
| `ui` | `3d594160b46acdacf901df194f4994391e0e9abc42e1a2b252b61febe26704b9` | `3d594160b46acdacf901df194f4994391e0e9abc42e1a2b252b61febe26704b9` |
| `widgets` | `f5b79ad1e0bf49229ccd2b214357f8fdf5074440d21c058b328f8ec61ed705be` | `c9786a637e232e5ac5a910544d461b412c66dab4abd5e0cda0ab7efeafb2bd0a` |
| `charsel_window` | `4da08cf0711b8f2052f92de28683f6ebf83eb237c65481e253ce8ac64848c0e4` | `45f33fa0af52ba9d6c4c8b1c2dffeb9b6cb203c69483ee3e70e6f8425b2fea37` |

All eleven exported metadata constants match before/after, including text/data bases, sizes and all
three input/target digests. The window map still has 803 candidates, 19,110 decoded instructions
and 1,167 calls. The hierarchy report passes all six body and twelve instruction-claim groups.
UI compares 687 cases, widgets 630, and character-select window 20, with all seven existing mutants
caught in both runs. These are existing comparisons, not new reconstruction coverage.

Five recorded failure outcomes are equal before/after:

| Input/caller | Before and after behavior |
|---|---|
| Hierarchy wrong size | `PinError`, `{path}: expected 4 bytes, found 3`, before digest checking |
| Hierarchy wrong digest | `PinError`, `{path}: SHA-256 {found} does not match pinned {digest}` |
| Hierarchy missing file | Exact native `FileNotFoundError`, errno 2, filename and message preserved |
| Mapper unpinned input | Exit 2, `Capture does not match the pinned restored client text`, no output |
| Mapper missing file | Exit 1, native `FileNotFoundError` and missing path, no output |

Post-migration focused portable checks pass 84 tests with three explicit private skips, including
all 17 validator-manifest checks. Unchanged owning tests with private inputs enabled pass 72/72:
45 mapper/hierarchy/static tests, 26 UI/widget tests and the one character-select window check.
No private skip or failure occurs in those 72. Reconstruction definitions outside the two loader
entry points match the baseline AST exactly. A self-review against AGENTS.md, CONTRIBUTING.md and
the task scope found no unresolved standards or spec issues.


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

Implementation, capture comparison and private owning tests are complete and pushed. The lane is
queued for the serialized final sequence. Full local gate, PR merge and cleanup remain pending.
Task-local reports live under `mu-mac-tools/native/scratch/verify-harness-002` only until delivery;
they contain private derived reports and are deleted after merge. No new input needs to be retained.

## What remains

Eight `UNMIGRATED` entries and the shared Unicorn machine consolidation remain. The excluded
protector-loader scripts are not proposed for this scope. No replay-oracle, live-client, renderer
or new reconstruction coverage is claimed. INTEGRATION-GREEN-001 supersedes the old private-input
failures in the historical VERIFY-HARNESS-001 run.
