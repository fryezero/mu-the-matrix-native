# RENDER-ITEMS-002AB

Branch `claude/render-items-002ab`, based on RENDER-ITEMS-002AA (PR #404, `baec5c08`). Claude Fable 5.2,
no subagents. Offline/static only.

## WIP (checkpoint 7, 2026-11-15 17:10)

Main `c49fa188` (batch 121, which merged #404) is merged into this branch at `9ac99348`.

**Done** (60 bodies fitted and compared at full count with mutants; 1,530 -> 1,590 of 1,674)
- [Ledger of all 144](../research/item-body-groups-002ab.tsv) and
  [research part 43](../research/client-render-items.md#part-43-level-guards-matrix-brackets-scalar-forms-gated-producers-and-low-level-callers-render-items-002ab).
- `validate_item_level_guards.py`, 18 bodies: 60,234 comparisons, 0 mismatches, 16 mutants, 332 s.
- `validate_item_brackets.py`, 28 bodies (9 matrix brackets, 16 scalar forms, 3 flag programs): 54,916
  comparisons, 0 mismatches, 11 mutants, about 270 s.
- `validate_item_gated_programs.py`, 5 producers: 5,384 comparisons, 0 mismatches, 10 mutants, 39 s.
- `validate_item_mesh_callers.py`, 9 low-level callers: 22,698 comparisons, 0 mismatches, 15 mutants, 151 s.
- Four unittest modules (13 portable tests pass), four `validators.toml` rows.
- Recipe header format: trailing zero values and unsigned suffixes omitted; compiled library byte-identical
  for the 1,511 rows of #404 (SHA-256 `e8f2ea6b2ffce2b1fd64d51f728cb9db6cd2ac6e6c768bd1c76ca100e0537cb7`).

**Left**
- The official full extraction (`gen_item_bodies.py --output`, started 17:08 on the merged tree) must
  reproduce the committed assembled `item_bodies.h` (1,562 rows, 493,428 bytes) byte for byte.
- Classifier tables, status lines, final handoff, affected validators (`--affected origin/main`, cache),
  portable affected tests, 8d reduced private tests, default identity sweep, item proof renders, PR.

**Next step**
- When the extraction ends: compare the header, run `scripts/classify_item_bodies.py`, then the affected
  validator run once.
