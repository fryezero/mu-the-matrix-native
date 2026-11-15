# RENDER-ITEMS-002AB

Branch `claude/render-items-002ab`, based on RENDER-ITEMS-002AA (PR #404, `baec5c08`). Claude Fable 5.2,
no subagents. Offline/static only.

## WIP (checkpoint 2, 2026-11-15 15:25)

**Done** (28 bodies fitted and compared at full count; 1,530 -> 1,558 of 1,674 once the extraction confirms)
- Classified the 144 remaining bodies by the form they execute (11 classification states plus one forced
  record, hooks on every helper level-word comparison and every effect service).
- Guard group, 17 bodies, `validate_item_level_guards.py --mutations`: 56,888 comparisons, 0 mismatches,
  13 mutants caught, 330 s. Packed word `>= 9`: `0x0b34..0x0b36`, `0x1103`, `0x130e`, `0x1524`. Decoded
  level `>= 11` behind a `-1` guard (new recipe `level_split=3`): `0x239a..0x239d`, `0x239f`, `0x23a0`,
  `0x23a2..0x23a4`, `0x23a6`, `0x23a7`.
- Matrix-bracket group, 8 bodies (`0x0ef4`, `0x12fa`, `0x12fb`, `0x14f2`, `0x16f5`, `0x16f6`, `0x1711`,
  `0x24f1`): `0x012b7e53`/`0x012b7e65` are bare glPushMatrix/glPopMatrix calls; `matrix_brackets()` reads
  both helpers and each case. Scalar tails, 3 bodies (`0x10f3`, `0x1101`, `0x1703`).
  `validate_item_brackets.py --mutations`: 28,203 comparisons, 0 mismatches, 6 mutants caught, 108 s.
- New readers (limited to the 002AB lists): upper clamp, disp8 frame locals, widened binary64 tail, binary32
  clamp after a binary64 run, ternary minimum with a repeated wave evaluation, folded binary32 constants,
  integer ping-pong (clock op 39), shared `cmp/je` case chains in `case_extent()`.
- The recipe header omits trailing zero values; the compiled library is byte-identical for the 1,511 rows
  of #404 (SHA-256 `e58c21c6a3f5a675c9a9c0f4ffb55cda97ecaf8440be84ee55fadaf964947c9c` both ways).

**Left**
- `item_bodies.h` in this checkpoint is assembled (old rows parsed back plus 28 fitted rows, 1,539 rows,
  485,620 bytes); the full pinned extraction (about 33 minutes) must reproduce it byte for byte.
- Clock op 38 (`0x0184f927` minimum) is read but no admitted body uses it yet: admit `0x1523` (needs the
  reverse subtraction `1.0 - saved` across a helper call) or remove the op before the PR.
- Unittest modules, `validators.toml` rows, ledger, research part 42, classifier tables, status lines.
- Still refused in the groups touched: `0x0b38`, `0x0b39` (name gate `0x0195a3d0`, random-scaled vector),
  `0x1523`, `0x0afc`, `0x24ed`, `0x26ed`, `0x0b05`, `0x0ef0`, wings `0x239e`, `0x23a1`, `0x23a5`
  (transform service), and 18 of the 24 scalar/colour bodies.

**Next step**
- Flag-keep bodies (`0x231b`, `0x231c`, `0x24e3`), the sixths atlas (`0x0f19`, `0x1578`, `0x157a`), then the
  producer/service group (50).
