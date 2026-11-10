# RENDER-ITEMS-002Y

Branch `codex/render-items-002y`, from prerequisite #361 head `d6c74e22` while the steward gates it.
Prerequisite #361 subsequently merged at `3732f82a`; its identical-tree main history is merged at `4e9fa043`.
Codex, GPT-6.1 Sol; no subagents. Offline/static only. Installed apps are untouched.
Research part 38 is reserved; recheck main before the final push.

## WIP checkpoint

- Base coverage is 1,424 of 1,674 bodies. No final admission count is claimed at this checkpoint.
- Six later read-program bodies pass 292 independent states each: `0x0b4d`, `0x1314`, `0x230d`, `0x23f0`,
  `0x23f2`, `0x2497`. The latter five complete owned programs pass 320 states, exact streams and random counts,
  2.96 s. Body screens 51.26 and 56.04 s. Tables are not regenerated yet.
- The scalar reader now handles a reversed wave result, constant phase with a lower clamp, and clock sine/abs
  chains, including signed division of constant entry locals. Scalar storage and operation-count caps are
  unchanged. `0x0b51` still needs its piecewise body-colour cycle; it remains unadmitted.
- All six complete owned programs pass 384 states, 4.05 s. Conditional abs preserves negative zero;
  the CRT fabs route clears it. They have separate scalar operations.
- Five authored parser tests cover phase, clamp, signed entry-local division and the two signed-zero routes.
  The first four pass, 0.013 s; the signed-zero addition awaits the finish run.
- Eight helper-count bodies pass 292 independent states each. `0x2368` has an omitted base draw and normal
  glow/tails, 6.87 s. `0x26e6..0x26ec` overwrite every positive effective level with 7 at `0x0176f2fc`, after
  earlier record/quality remapping; this is a body-caller rule, not a change to the closed scalar remap API.
- A three-level helper diagnostic finds 61 mismatching types, including stopped/effect paths. It is not a
  replacement denominator for the historical 48. A no-glow experiment across its usable candidates adds none,
  96.16 s. The late caller and omitted-base recovery are separate exact fits.
- Full tests and instruction checks remain pending. Provisional body delta is fourteen, subject to table
  generation, exhaustive forcing-record checks, changed-row mutants and final integration.
- The further-body screen now adds 27 candidates after 292 independent states each, including counter
  variation: `0x0b09`, `0x0b0b`, `0x0b28`, `0x0b40`, `0x0b42`, `0x0b43`, `0x0b45`, `0x0b61`,
  `0x0eed`, `0x0efa`, `0x0f0b`, `0x10f2`, `0x1102`, `0x1505`, `0x1506`, `0x1509`, `0x1576`, `0x1577`,
  `0x1736`, `0x1746`, `0x192f`, `0x1b2f`, `0x212f`, `0x2568..0x256b`.
  It screens 182 candidates in census size order, 1,203.62 s elapsed including a resource pause.
  Provisional total gain is 41, or 1,424 -> 1,465/1,674, leaving 209. Full tables and checks remain pending.
  The four largest shields and four armour cases still refuse. Fitted `0x1710` and `0x10fd` fail independent
  states 19 and 17; neither is admitted. No tolerance or cap changed.
- Initial root and world builds pass. One baseline default sweep covers 46 maps, 92 PNGs, 92 dumps and
  46 reports, 104.19 s. Final identity, table reproduction, affected checks and changed-row mutants are pending.
- Next: finish the seven read-program candidates, then helper-count types, then the largest other groups.
  Run the full affected validation batch with enough time before the owner's deadline. This is not ready.

Lane-local progress inputs are under `~/Documents/MTM/mu-mac-tools/native/scratch/render-items-002y/`.
The baseline hashes, prerequisite C library, exploratory fit summaries and scripts are retained until finish.
No client bytes or captures are committed. Source canonical private environment from the repository root.

## Stopped 2026-11-09 22:5x: Codex usage limit

The lane's agent stopped when Codex reported its usage limit (GPT-6.1 Sol unavailable until 2026-11-13 18:44).
The orchestrator committed the two uncommitted test edits as they were (`test_item_clusters.py`,
`test_item_types.py`: the refused-control type moves to `0x23f1`, because `0x2368` and `0x230d` are provisional
admissions). They are consistent only once the tables are regenerated, so those two tests may fail on this
checkpoint. A table generation run (`scratch/render-items-002y/generate.py`) was still in progress and its
output is not verified. Resume from "WIP checkpoint" above: regenerate the tables, then run the pending checks.
