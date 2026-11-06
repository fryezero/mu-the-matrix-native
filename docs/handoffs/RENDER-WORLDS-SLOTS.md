# RENDER-WORLDS-SLOTS

The world classes' other slots after the primary methods: custom render (+0x38), after render (+0x3c) and
invisible move (+0x1c), the hook chain around the class slot, and Loren Market's outer RenderObjectVisual draw.
[Census, addresses, fidelity and limits](../research/client-worlds-slots.md).

- Claude Opus 5.5 lane. Worktree `~/Documents/MTM/worktrees/render-worlds-slots`, branch `claude/render-worlds-slots`,
  from origin/main `b8645181`. Merged origin/main `eb2a8e76` (#305/#306: combat and validator cache; docs conflicts kept both sides) as `a221e5b6`. Input links `tools/python`, `evidence` and `input` point at the
  main checkout and are never committed.
- **Census (verified/static):** all 48 classes × 3 slots, ordered by player reach. Before this lane 49/144 were
  native and compared (the coverage JSON still listed 9); **now 125/144**. 19 are missing, none in a captured or
  warp-reachable world.
- **Captured worlds' slots (verified):**
  - custom + after of Vulcanus 63, Loren Market 79 (with Event square 114, the same body), Ferea 112, Swamp of
    Darkness 122 and Kubera 123..127;
  - invisible move of 142, 143, 144 and 145.
  - Bitmaps: Kubera's loader table (61 bitmaps, per-world handler words), Ferea's statue, the crocodiles.
- **Trivial slots (verified):** 60 base or empty slots are compared under Unicorn and need no native code.
- **Hook chain (verified):** every hook around the class slot in RenderObjectVisual, the custom render and the
  after chain is a no-op in all 57 class registrations (1,881 runs). The direct class-slot dispatch is complete;
  no chain code was needed.
- **Loren Market RNG (verified, changed):** `0x017f9758` draws `rand() % 30` for every object with a model before
  its world switch. The native 79 branch now draws it too. Other branches without it are listed in the finding
  (§5) and left unchanged.
- **Shared lines:**
  - `world_slots_visual.c`: the slot helpers moved verbatim into `world_visual_slots.h`; three dispatch fallbacks
    and two bitmap fallbacks;
  - `world_visual.h`: three `mu_slot_model` fields (handler state, bone callback) and one declaration;
  - `object_render.{c,h}`: `mu_obj_handler_moves` for 142..145;
  - `mu_objects_runtime.c`: `class_custom_call` (Vulcanus bones, the sprite/particle requests to `consume_visual`),
    the slot model's new fields, the 145 step handler, the 79 outer draw;
  - `native/Makefile`: the `worlds-slots-host` rule;
  - `world-handler-coverage.json`: slot statuses (including AFTER..AFTER3's);
  - one validator row;
  - `docs/handoff.md`: a leftover merge-conflict block at the top resolved by keeping both sides.

## Checks

Under the 2026-11-04 test budget: no lane gate. `nice -n 10`, `make -j4`, `--jobs 2`; load 1m 6–19 with
three other lanes and the steward active. Env: `MU_RECOVERY_INTEGRATION=1`,
`MU_GAME_ROOT=<free-runtime prefix>/drive_c/MuTheMatrix`,
`MU_SECTION3=~/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin`,
`MU_OBJECTS_PLAIN_DIR=<mu-mac-tools>/native/scratch/objects/live/plain`,
`MU_LANG_DIR=<mu-mac-tools>/native/scratch/render-worlds-after5/lang`, `MU_EVIDENCE_DIR=<main checkout>/evidence`.

| Check | Result | Wall |
|---|---|---|
| `validate_worlds_slots --cases 1000 --mutations` (once, `run_validators.py --cache`, at `b2ac02f0`) | 19 families, **18,999 cases equal, 0 mismatches/stops**; 77/79 mutants detected | 355.1 s |
| Two undetected mutants replaced by non-equivalent ones (eyes chance `r<2` → `r<200`: `r==2` is 1 in 1000; Kubera's world-125 word moved to the `loaders` family, which compares the whole table) and their families rerun with mutants (`custom_63`, `loaders`: 18 mutants) | 1,118 cases equal, 18/18 detected (lowest: 1 in the fixed `loaders` family) | 72.2 s |
| Families: custom/after of 79, 114, 63, 112, 122, 123 (1,000 each); invisible 142..145 (1,000 each); trivial 1,000; loaders 118; chains 1,881 | as above | |
| Iteration runs (`--cases 200`/`600`) | all equal at the end | 4–5 s each |
| `run_validators.py --private --no-mutants --cache --jobs 2`, 6 rows at `75817a78` (final code) | 6 pass: worlds_slots 18,999, worlds_after2 32,216, worlds_after 13,424, worlds_after3 10,212, worlds_after4 9,181, object_render 1,984 cases | 31.6 s |
| `run_test_suites.py --affected origin/main` (`MU_RECOVERY_INTEGRATION=0`, `MU_GATE_JOBS=2`, after the merge) | 7 suites, 1,399 tests, 1,185 passed, 213 skipped, **1 failure**: `test_worlds_after2.test_classes` pinned the list of slot worlds (an intended change, updated) | 295.6 s |
| `run_test_suites.py reconstructed/objects` after the fix | 166 tests, 136 passed, 30 skipped, 0 failures | 1.4 s |
| `test_worlds_slots` (8 tests, the private one included) and `test_native_worlds_slots` (production host: first pass, after pass, Ferea state, Vulcanus bones refused/posed, 79's outer draw) | OK | 7.3 s + 0.4 s |
| 6b neighbours (in the suite run): hosts `worlds_g/i/j/l/n/q/s3/r2/s`, `render_light`; `test_worlds_after2/3` | pass | |
| `nice -n 10 make -j4` (final) | pass | 12.2 s |
| `scripts/audit_repository.py` | 1,938 staged files, 0 rejected | 25.3 s |
| `world_handler_coverage.py` | 48 classes, 57 registrations, 288 addresses; 144/144 primary | < 1 s |
| Fidelity "before" (main `b8645181` binary, once): DATA-ACQ-002 default / October 22 / live clock (10 maps) | | 58.5 / 19.7 / 33.7 s |
| Fidelity "after" (`b2ac02f0`) | finding §6: 25/32 and 14/14 byte-identical; 7 changed captures explained | 60.7 / 17.9 / 30.5 s |

Validator rows were chosen per brief 6b, not by `--list-affected` (it selects most rows through the shared library):
- my row;
- `worlds_after2` and `worlds_after3`, whose file `world_slots_visual.c` (helpers, dispatch, bitmap tables) and
  struct `mu_slot_model` changed;
- `worlds_after` (the after pass now runs for six more classes);
- `object_render` (`mu_obj_handler_moves`);
- `worlds_after4`, the objects + native row (the runtime changed).

Steward validators: validate_worlds_slots (mutants: yes, new; done once), validate_worlds_after2, validate_worlds_after3,
validate_worlds_after, validate_object_render, validate_worlds_after4 (no mutants) (ran at `75817a78`). Env as above
(`MU_SECTION3`, `MU_GAME_ROOT`).

## Remaining

- Custom/after of 62, Imperial Guardian 69..72 (70/71 forward to 69's 1,468-instruction custom slot), 82, Arca War
  92, Nars 110, Test Area 121, and the custom slots of 95 and 100. None has a capture.
- The outer RenderObjectVisual draw in the native branches of 57/58, 62, 63, 64, 82, 100/101, 128..130 and 137
  (finding §5).
- Ferea's door state writer (server messages; the state stays at its constructor value 0).

No original client or launcher was started; the DATA-ACQ-002 and October 22 inputs were only read. No shared
particle/effect/joint hook was added: Vulcanus' sprites and particles use the existing visual consumer.
