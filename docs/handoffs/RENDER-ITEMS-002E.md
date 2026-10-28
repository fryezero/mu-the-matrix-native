# RENDER-ITEMS-002 part 5

Implementation checkpoint. Scope claimed on `codex/render-items-002e`, isolated worktree
`~/Documents/MTM/worktrees/render-items-002e`, based on main `831343b`.

Owned work: reconstructed item-body recipes and link callers, their native shared adapters,
generated rendering tables, validators/tests, this handoff and the milestone's documentation rows.
No live client, launcher, Muun, nested map-object, terrain or per-world object work.

Baseline focused renderer suite: 26 tests, six explicit private skips. Full Mac gate and offline
candidate screening are in progress. Coverage remains 426/1,674 bodies and 11/17 skins at this checkpoint.
Local reports/renders use `mu-mac-tools/native/{scratch,renders}/render-items-002e/`.

Second checkpoint: all six remaining skins pass 3,072 complete body/sprite cases. Two new link callers,
`0x012c807d` and `0x012c8d7b`, pass 800 cases for types `0x0afd/0x0afe`. The body screen accepts 75 types
at 292 cases each, 21,900 comparisons. Seven probe-fitting candidates were rejected and disabled:
`0x230f/0x2317/0x248e/0x2490/0x2492/0x2504/0x270f`. Generator reproduction, mutations, final regressions,
local renders and the stable full gate remain pending. This checkpoint is not the release result.
