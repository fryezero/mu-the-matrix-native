# RENDER-ITEMS-002Y

Branch `codex/render-items-002y`, from prerequisite #361 head `d6c74e22` while the steward gates it.
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
- Four authored parser tests pass, 0.013 s. Full tests and instruction checks remain pending.
- Initial root and world builds pass. One baseline default sweep covers 46 maps, 92 PNGs, 92 dumps and
  46 reports, 104.19 s. Final identity, table reproduction, affected checks and changed-row mutants are pending.
- Next: finish the seven read-program candidates, then helper-count types, then the largest other groups.
  Run the full affected validation batch with enough time before the owner's deadline. This is not ready.

Lane-local progress inputs are under `~/Documents/MTM/mu-mac-tools/native/scratch/render-items-002y/`.
The baseline hashes, prerequisite C library, exploratory fit summaries and scripts are retained until finish.
No client bytes or captures are committed. Source canonical private environment from the repository root.
