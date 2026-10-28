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

Implementation checkpoint: eight further ranked armour bodies and nineteen rank-5 mesh
streams are admitted in the existing no-owner domain, raising bounded body coverage
to 662/1,674. Two sprite-only links, spear 0x10f0 at 0x012cd341 and shield 0x16f5
at 0x012cb9d7, raise native caller consumption to fourteen targets/nineteen types.
Rank-5 lighting, named mesh lookup, random blend-light and UV order pass 11,096
original full-function cases; eight armour types pass 2,336 and links pass 800.
The mutation/regeneration run is in progress. Owner-bone particle calls beyond this
domain remain open; full rank-5 owner effects are not claimed complete.
Portable renderchar: 47 tests, eleven explicit skips. Native renderer: ten tests,
one installed-client skip. Synthetic rank-5 pixels distinguish lighting and clocks;
repeat frames are stable. The new paths allocate no per-frame storage.
