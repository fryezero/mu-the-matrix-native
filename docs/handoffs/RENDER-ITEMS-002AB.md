# RENDER-ITEMS-002AB

Branch `claude/render-items-002ab`, based on RENDER-ITEMS-002AA (PR #404, `baec5c08`). Claude Fable 5.2,
no subagents. Offline/static only.

## WIP (checkpoint 1, 2026-11-15 15:00)

**Done**
- Classified the 144 remaining bodies by the form they execute (11 classification states plus one forced
  record, hooks on every helper level-word comparison and every effect service).
- Two uniform guard groups found inside "variable body draw count": the 002AA packed word
  (`cmp [ebp+0x28], 9`: `0x0b34..0x0b36`, `0x0b38`, `0x0b39`, `0x1103`, `0x130e`, `0x1523`, `0x1524`) and a
  wing form at 23 sites (`cmp [ebp+0x28], -1; je; push; call 0x016a78c9; pop; cmp eax, 11; jge`:
  `0x239a..0x23a7`).
- Generator: `PACKED_GUARD_TYPES`, `DECODED_GUARD_TYPES` (recipe `level_split=3`), the instruction-checked
  `level_guards()` reader, scalar readers for an upper clamp, disp8 frame locals, a widened binary64 tail and
  folded binary32 constants in clock chains (all limited to the 002AB lists).
- Fourteen bodies fit and pass a small-sample comparison (`validate_item_level_guards.py --cases 40`):
  `0x0b34`, `0x0b36`, `0x1103`, `0x130e`, `0x1524`, `0x239a..0x239d`, `0x239f`, `0x23a2..0x23a4`, `0x23a6`.
- The recipe header omits trailing zero values; the compiled library is byte-identical for the 1,511 rows
  of #404 (SHA-256 `e58c21c6a3f5a675c9a9c0f4ffb55cda97ecaf8440be84ee55fadaf964947c9c` both ways).

**Left**
- `item_bodies.h` in this checkpoint is assembled (old rows parsed back plus fourteen fitted rows); the full
  pinned extraction (about 33 minutes) has not been run yet and must reproduce it byte for byte.
- Full-count validator run with mutants, unittest module, `validators.toml` row, ledger, research part 42,
  classifier tables, status lines.
- Remaining guard bodies `0x0b35`, `0x0b38`, `0x0b39`, `0x1523`, `0x23a0`, `0x23a7` (unread scalars) and the
  three wings with a transform service (`0x239e`, `0x23a1`, `0x23a5`); then the other groups.

**Next step**
- Read the remaining scalar forms of the guard groups, then take "producer/service programs" (50).
