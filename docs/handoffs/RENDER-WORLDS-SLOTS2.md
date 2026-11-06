# RENDER-WORLDS-SLOTS2

RENDER-WORLDS-SLOTS's follow-ups. RenderObjectVisual's outer rand in every class world, and 17 of the 19 missing class
slots. [Finding, addresses, fidelity and limits](../research/client-worlds-slots2.md).

- Claude Opus 5.5 lane. Worktree `~/Documents/MTM/worktrees/render-worlds-slots2`, branch `claude/render-worlds-slots2`.
- Started from `origin/claude/render-worlds-slots` `83f8f1d9`, while #308 was queued.
- Merged origin/main `0122f192` (#307 and the #308 merge) as `a953eb59`: HUD/app code only, no compiled input of my
  checks. Merged `97e0a92a` (#309, combat) as `e53759b8`; `validators.toml` kept both rows.
- Input links `tools/python`, `evidence` and `input` point at the main checkout and are never committed.

## What changed

- **Outer draw (verified, changed).** `0x017f9758` draws `rand() % 30` (`0x017f9797`) for every object with a model,
  before its world switch. All 57 class registrations reach their slot 0x34 through the default branch after it.
  - The native branches of 57/58, 62, 63, 64, 82, 100/101, 128..130 and 137 drew none: confirmed under Unicorn and
    fixed.
  - Also found and fixed: the character/login scenes 93/94, and the class worlds whose slot 0x34 answers no (113,
    115..120, 138, 139).
  - The scene visuals 93/94 no longer run without a model; the client returns first.
  - Now one call (`mu_obj_visual_flicker`) at the top of the runtime's class visual replaces the per-branch draws.
  - Tormenta 141's draw stays in the particle visual.
- **Slots (verified).** 125/144 → **142/144**. New:
  - Santa Village 62 custom;
  - Imperial Guardian 69..72 custom + after (70/71 forward to 69's slot, 72 forwards and then its own types);
  - 82 custom + after;
  - Arca War 92 (worlds 92/96/101/111) custom + after, which forward to the base world's slots;
  - Debenter 95 custom, Uruk 100 custom, Nars 110 custom + after.
- **Shared lines:**
  - `mu_objects_runtime.c`: the one outer draw (and the per-branch ones removed), the scene visuals' model gate,
    Imperial Guardian's bone-9 pose, CreateEffect requests to the existing consumer;
  - `world_slots_more_visual.c`: the dispatch/bitmap fallbacks chain to `world_slots2_visual.c`;
  - `world_visual_slots.h`: five declarations;
  - `native/Makefile`: the `worlds-slots2-host` rule;
  - `world-handler-coverage.json`: 17 statuses;
  - one validator row.
  - 6b test updates: `test_worlds_after2.test_classes` (the class list), `test_worlds_slots.test_trivial_slots`
    (62/95/100 custom now draw), `worlds_slots_host.c` (Vulcanus' seed +1 draw), `worlds_s3_host.c` (IG 72's 0x73
    now emits 0x52d).
- Ferea's door state is unchanged: an explicit input, constructed 0.

## Checks

Under the 2026-11-04 test budget: no lane gate. `nice -n 10`, `make -j4`, `--jobs 2`; load 1m 5–18 with other lanes
and the steward active.

Env:
- `MU_RECOVERY_INTEGRATION=1`;
- `MU_GAME_ROOT=<free-runtime prefix>/drive_c/MuTheMatrix`;
- `MU_SECTION3=~/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin`;
- `MU_EVIDENCE_DIR=<main checkout>/evidence`;
- `MU_OBJECTS_PLAIN_DIR=<mu-mac-tools>/native/scratch/objects/live/plain`;
- `MU_LANG_DIR=<mu-mac-tools>/native/scratch/render-worlds-after5/lang`.

| Check | Result | Wall |
|---|---|---|
| `validate_worlds_slots2 --cases 1000 --mutations` (once, `run_validators.py --cache`, code of `600ddb01`) | 33 families, **33,000 cases equal, 0 mismatches/stops** (16 RNG families: 14 worlds, `rng_empty`, `rng_drawn`; 17 slot families); 61/62 mutants detected (lowest 5) | 279.1 s |
| The one undetected mutant (Uruk 0x2c's intermediate hidden mesh 2, reset to −1 before the slot returns and read by no draw: equivalent) replaced by the reset value, `custom2_100` rerun with its 7 mutants | 1,000 equal, 7/7 detected (lowest 21) | 24 s |
| The first full run | stopped at mutant 1, which did not compile (the model gate left `has_model` unused); the mutant was rewritten. Families equal | 38 s |
| Iteration runs (`--cases 200`/`400`) | all equal at the end | 2–5 s each |
| `run_validators.py --private --no-mutants --cache --jobs 2`, 5 rows at `600ddb01` | 5 pass: worlds_slots 18,999 (11.1 s), worlds_after2 32,216 (19.4 s), worlds_after 13,424 (9.1 s), worlds_after3 10,212 (5.8 s), worlds_after4 9,181 (17.0 s) | 31 s |
| `run_test_suites.py reconstructed/objects` (`MU_RECOVERY_INTEGRATION=0`) | 174 tests, 143 passed, 31 skipped, 0 failures (2 failures before the 6b updates) | 1.4 s |
| `test_worlds_slots2` + `test_worlds_slots` private (`MU_RECOVERY_INTEGRATION=1`) | 16 tests OK | 9 s |
| Native hosts using the first pass (21 modules: map_effects, render_effects6, render_light, worlds g/h/i/j/k/l/m/o/p/p2/q/r/r2/s/s2/s3/slots/slots2) | 29 tests OK after the two host updates (2 errors before: intended) | 106 s |
| `tests/test_world_captures_2.py`, `tests/test_validators_manifest.py` | 21 tests OK | 0.6 s |
| `world_handler_coverage.py` | 48 classes, 57 registrations, 288 addresses; 144/144 primary | < 1 s |
| `nice -n 10 make -j4` (native) and `build/mu-world` | pass | 25 s (first build) |
| `scripts/audit_repository.py` (after staging the new files) | 1,951 staged files, 0 rejected | 29 s |
| Fidelity "before" (`83f8f1d9` binary, once): DATA-ACQ-002 default / October 22 / live clock (12 maps) | | 61 / 31 / 36 s |
| Fidelity "after" (outer draw `07531681`, then final `c0d8cc66`) | 26/32 and 14/14 byte-identical; 6 changed captures explained (finding §3); the final code gives the same as the outer-draw build | 73+25 / 59+19 / 41 s |

Validator rows were chosen by what the diff compiles, not `--list-affected`, which also lists rows through quoted
paths (worlds_s2/s3, render_effects14: joints/particles/combat, not this code):
- my row;
- `worlds_slots`, the trivial and slot dispatch (`mu_class_custom`/`after`, bitmap fallbacks);
- `worlds_after2` and `worlds_after3`, whose dispatch and bitmap tables now chain further;
- `worlds_after`, whose after pass runs for 13 more worlds through `mu_class_slots`;
- `worlds_after4`, the objects + native row (the runtime changed).

Steward validators: validate_worlds_slots2 (mutants: yes, new; done once), validate_worlds_slots, validate_worlds_after2,
validate_worlds_after3, validate_worlds_after, validate_worlds_after4 (no mutants) (ran at `600ddb01`; later commits
touch only native/tests hosts, the coverage JSON and docs; after merging #309 (`mu_combat.c`, built by the native
row) validate_worlds_after4 passed again at `e53759b8`, 9,181 cases, 18 s). Env as above.

## Remaining

- Test Area 121's custom (`0x00d58bd8`, 1,972 instructions) and after (`0x00d5a6cc`, 198). They need the global
  per-vertex light buffer `0x06fd0918` that the custom slot fills for types 6..12 (no native consumer) and 28
  bone-placed particles. No capture.
- RenderObjectVisual's rand in worlds without a class (the particle visual's generator or none; finding §1).
- Ferea's door state writer (server-driven).

No original client or launcher was started; the DATA-ACQ-002 and October 22 inputs were only read. No shared
particle/effect/joint hook was added.

Local files kept for a later lane: none. The before binary, renders and scratch are deleted.
