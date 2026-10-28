# RENDER-ITEMS-002 part 8

In progress on isolated branch/worktree `codex/render-items-002h`, based on `a38ec75`.
Scope claimed in issue #218. Shared Python and evidence inputs are symlinks and never staged.
The complete owner brief and prior item handoffs are the implementation contract.
No original client or launcher is read, started, stopped or driven.

Baseline: 635/1,674 bodies, 17/17 skins, twelve link targets/seventeen types.
Next ranked clusters are being screened with the independent instruction comparison.
Rank 5 is being traced through the full lighting-dependent mesh branch. Its real pose
builder writes shared bones, while the mesh draws use the already transformed geometry;
there is no intervening transform call in `0x017479b1..0x0174a489`.
The model lighting byte, named texture lookup, random UV and owner-bone effects need
separate comparisons before the native adapter can admit this branch.

Local outputs are scoped to `mu-mac-tools/native/{scratch,renders}/render-items-002h/`.
Delete them, lane build outputs, worktree and local branch after merge. No new input needs retention.
