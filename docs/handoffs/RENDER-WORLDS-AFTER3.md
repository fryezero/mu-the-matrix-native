# RENDER-WORLDS-AFTER3

The custom (slot 0x38) and after (slot 0x3c) renders of the last five world classes: 133 Temple of Arnil,
141 Tormenta Island, 143 Kardamahal, 144 Swamp of Destruction and 145, with their bitmaps.
[Addresses, checks, fidelity and limits](../research/client-worlds-after3.md).

- Claude Opus 5.5 lane. Worktree `~/Documents/MTM/worktrees/render-worlds-after3`, branch
  `claude/render-worlds-after3`, from origin/main `7f18bf05`, merged with origin/main `d5ffde0a`. The only conflict
  was in `scripts/validators.toml` (both rows kept). Input links `tools/python` and `evidence` point at the main
  checkout and are never committed.
- **Slots (verified):** all ten slots plus the five bitmap loaders (`reconstructed/objects/world_slots_visual.c`).
  - 145's custom slot has no world test (alpha < 0.9 answers handled); 144's after slot needs the live byte.
  - Each class's 32 water bitmaps `Object<world+1>\wt%02d_R.jpg` animate with `(int)(WorldTime·0.015) % 32`.
  - 145 type 0x99 fades object +0x188 and plays 0x5b4.
  - 141 type 0x2c depends on the action's key count.
  - 143 after type 0x71 requests a terrain light.
  - Types above 300 (133's 0x199..0x19e, 141's 0x40e) are never passed by the world manager and are left out.
- **Shared lines:**
  - `world_visual.h`: three `mu_slot_model` fields and `MU_WORLD_SLOT_BITMAPS`.
  - `mu_objects_runtime.c`: the bitmap capacity, the `slot_model` fields, model +0xb4 in `slot_fields`, first-pass
    slot sounds, and the after-pass light count. These sit outside RENDER-JOINTS-001's `slot_meshes` lines.
  - `validate_worlds_after2.py`: the `SlotModel` struct and the bitmap buffer.
  - `test_worlds_after2.py`: the class list (an intended change).
  - One validator row. No per-world dispatch file changed.

## Checks

- `validate_worlds_after3`: 11 families, **10,212 cases equal, 0 mismatches/stops, 49/49 compiled mutants**.
  Registered.
- Portable `reconstructed/objects/test_worlds_after3.py`: 7 tests + 1 private.
- Private validators on the merge, after a clean rebuild (`run_validators.py --private --jobs 2`,
  `MU_RECOVERY_INTEGRATION=1`, `MU_GAME_ROOT` = the installed client): **5 pass, 0 fail**.

  | Validator | Cases | Mutants |
  |---|---:|---:|
  | `validate_worlds_after3` | 10,212 | 49 |
  | `validate_worlds_after2` | 32,216 | 33 |
  | `validate_worlds_after` | 13,424 | 21 |
  | `validate_worlds_q2` | 4,000 | 50 |
  | `validate_object_render` | 1,984 | — |

- Gate on the merge (`nice -n 10 bash scripts/local-macos-ci.sh`): **38 suites, 1,804 tests, 1,565 passed, 239
  skipped, 0 failures/errors; fixtures, native viewer, live readers; audit 1,800 files, 0 rejected**. After the
  gate only the mutant count in the registry row and the private test (51 → 49, a miscount) and the docs changed.
  The registry row was then rerun on its own: pass.
- Fidelity at the DATA-ACQ-002 arrival tiles, base `d5ffde0a` vs lane:

  | Capture | Default clock | Live clock |
  |---|---|---|
  | 143 Kardamahal | 10.911 → 10.299 | 10.911 → 10.236 |
  | 144 Swamp of Destruction | 12.395 → 12.394 | 12.396 → 12.394 |
  | 133 Temple of Arnil | 1.028 equal (frame changed) | 1.024 equal (frame changed) |

  The other 29 captures are byte-identical (PNG, OBJECT, light) on the default clock. 140 and 142 are identical on
  the live clock too. 144's OBJECT change is +0xb/+0x1e8 of its after-drawn types 0x20/0x40. There are no 141/145
  captures.

## Remaining (follow-up RENDER-WORLDS-AFTER4)

- The draw-first predicate `0x017fcd18`: its own world cases (0, 2, 0x21, 0x25, 0x33, 0x38..0x3a, 0x49, 0x4a,
  0x5b, 0x5c, 0x64, 0x65, 0x6e..0x71, 0x7a, 0x83..0x85) and the true branches of its default chain (`0x009a645f`,
  `0x00e94004`, `0x00e3068f`, `0x016a887a`, `0x00e1e4b6`, `0x016a8325`). Extend Q2's `render_first` family.
- The writer of the velocity (+0xbc) differences of 140 and 142..144 (still 40 in 144 and 3 in 142).
- A render-time terrain-light consumer (143 type 0x71).
- Confirming that action record +8 is the BMD key count.

No original client was started; the DATA-ACQ-002 inputs were only read. Renders, scratch and the base worktree
`worktrees/rwa3-base` are deleted at handoff; no local input needs keeping.
