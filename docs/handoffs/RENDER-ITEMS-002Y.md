# RENDER-ITEMS-002Y

Branch `codex/render-items-002y`, from prerequisite #361 head `d6c74e22` while the steward gates it.
Prerequisite #361 subsequently merged at `3732f82a`; its identical-tree main history is merged at `4e9fa043`.
Codex, GPT-6.1 Sol; no subagents. Offline/static only. Installed apps are untouched.
Research part 38 is reserved; recheck main before the final push.

## WIP checkpoint 2026-11-11, signed-zero correction

Done: source and initial regenerated tables are pushed at `a37e63ca`. The changed-row run takes
314.76 s. The helper row passes 6,432 comparisons and all four mutants in 36.0 s. The historical
derived row completes 36,252 comparisons with zero mismatches and catches all seven mutants in 314.6 s;
its remaining failure is metadata: kind-6 program count is 113, with five programs now exact clock chains,
rather than the historical 118. The manifest now records the actual 113. No state comparison is removed.

The read-program row stops after 34.4 s on a clock fixture with record kind 4, an explicitly unsupported
domain. Directed clocks now use the reviewed neutral record; forcing-record enumeration is unchanged.
The other-body row stops after 111.9 s at negative-zero time for `0x2568`. Isolated sine and conditional
abs both preserve negative zero, 12 helper cases, 0.09 s. Caller tracing, 0.11 s, finds the final
`xorps; addss` at `0x016fce1b..0x016fce1e`: positive zero plus the saved product clears its zero sign.
The reader already captures this operation, but the fit had selected its indistinguishable pre-add
intermediate over positive-clock probes. Extra negative-zero probes now distinguish those values for
all six later read bodies and 27 other bodies, while retaining every previous probe and the existing caps.
No runtime arithmetic changed. The new portable observable regression is red on the old table, 0.16 s.
A third other-body mutant will remove zero additions to establish that the final comparison catches it.

Left: regenerate both tables with the added probes, pass the regression and remaining changed-row
checks, affected portable/private validators, reduced private native modules, final rebuilt identity,
final docs and PR. The generated tables and failed-check reports remain provisional.
Next step: one full table run, then the changed rows and affected batch. The 02:15/02:30 deadline is
restored. Prioritize the verified body set over further groups. Keep the baseline hashes and prerequisite
library under the lane scratch path until final identity and C-to-C checks pass.

## Resumed 2026-11-11

Main `d4af71dd` is merged at `f7fed588`. The registry append conflict preserves both lanes' rows;
28 registry tests pass in 6.25 s. Root build passes in 16.64 s and the explicit world build in 4.67 s.
A fresh pre-regeneration default sweep covers all 46 maps in 57.29 s. Its rebuilt `mu-world` SHA-256 is
`c244aec9e8b89e014dd0e88139d0da26fa2df06aff728e35b3aa5039d0011020`.
The historical sweep is superseded because it did not record its binary hash. The fresh baseline is the
merged lane with the prerequisite item tables; the admission C-to-C check will separately cover earlier items.
Complete generation passes in 1,265.21 s including cache flush and the checkpoint pause. It emits 1,446
recipe rows, a 513,963-byte body header and a 295,763-byte owner header. Both remain below the audit limit.
The regenerated root build passes in 10.74 s. The corrected portable renderer passes 125 tests, 27 private
skips, in 0.42 s. The first portable run found stale pre-program and derived-program structure assertions.
There are 71 pre-programs. Five historical bodies (`0x0b0c`, `0x16fc..0x16fe`, `0x1b33`) now use one exact
clock-sine chain rather than an intermediate kind-6 program; tests enumerate those replacements explicitly.
The derived validator retains all original state comparisons and will run its mutants once too.

The C-to-C check passes 216,448 states in 9.78 s: 211,200 identical, with exactly the 41 intended newly
admitted types changing in 128 states each. Survey membership includes the 17 skin cases, 1,441 -> 1,482;
body coverage alone is 1,424 -> 1,465 of 1,674. No earlier type changes in this finite comparison.
The full classifier/export delta passes in 81.68 s: 1,691 types, 798 shapes, exactly 41 memberships and
31 shape totals change; complete shapes 609 -> 640. Raw shape/address/stopped-state summaries are unchanged.
Forcing-record/clock/counter/owned comparisons, changed-row mutants, affected validators, private native
checks and final identity remain pending. Generated outputs are still provisional until those checks pass.
The owner restored the stop time: stop by 02:30 on 2026-11-12; if not ready at 02:15, push WIP and stop. No PR or ready-prs entry exists yet.

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
