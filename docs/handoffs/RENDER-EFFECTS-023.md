# RENDER-EFFECTS-023

PR-ready, offline/static only. Branch `codex/render-effects-023`; #354 was merged before branching from
`825c37b7`, then #355/main `127489e0` was merged at `041c1805`. No live client, installed app, launcher,
server-state work, protection analysis or memory writes. All displayed names are demo names.

## Scope and addresses

World bitmap slots for `0x7f7a` (flare03) and `0x80ba` (flare01_red) make their existing bone sprites draw.
Twelve further slots supply the new particles. The pool grows 79 to 93; indices 0..75 stay fixed, the fourteen
additions precede Fire06, and rain remains last. Original LINEAR filtering and CLAMP/REPEAT are retained.

Nineteen new particle pairs:

| Item | Pairs |
|---|---|
| `0x0f2a` | `0x85bc/5`, `0x83b8/8`, `0x85fc/1`, register-selected `0x8315..0x8317/4` |
| `0x0f24` | `0x7ffb/0` |
| `0x0f28` | `0x807e..0x8080/0x18`, `0x83b3/0x13` |
| `0x0f29` | `0x8109/0xe` |
| `0x0f2b` | `0x8081..0x8083/9`, `0x8549/1` |
| `0x0f2c` | `0x82f2/0x1a`, `0x810b/0xa`, `0x85fc/2` |

CreateParticle `0x015ae7b0`, MoveParticles `0x01616c80`, RenderParticles `0x0159123f` are compared under
Unicorn: defined record bytes, random consumption and ordered sprite/GL calls. The direct rings/shockwave
follow OBJECT `+0x1f4 + 12*arg8`, without the spark's birth offset (`0x015ac52a` / `0x015ace36`). Native
references check registry generations and three-point bounds. Four full named-bone synthetic skeletons compare
original and generated point stores, alternate OBJECT matrices and hidden states.

The character viewer supplies stable item OBJECT keys for worn parts and links, so the existing
`0x810a/0x25` spark and new rings draw there too. Attachments without their own item OBJECT retain their domain.
EFFECTS-022's particle logic is unchanged. All branch addresses, formulas, fourteen loader calls and pinned
text/data SHA-256 values are in research Part 32. Only pinned offline captures were read.

## Routed versus refused census

The admitted item-program tables contain **93 programs and 30 distinct particle pairs**. All 30 have native
consumers; the bounded static census has **zero unresolved bitmap expressions**. This adds nineteen pairs to
the previous eleven. `0x8180/5` deliberately draws no sprite, matching the original. This census covers
admitted programs, not every client item or possible input.

Two world sprite texture gaps remain outside the requested slots: `0x81ec` at three sites in `0x0f2a`
(`Effect\lightmarks_red.jpg`, loader `0x01823365`), and `0x854a` at four sites in `0x0f2b`. They remain
counted-only. All other sprite sites in these eight mace programs have world bitmap slots.
Hammer14 (`0x0f29`) contains exact bone name `up01 ` with a trailing space; its program asks for `up01`.
That one sprite refusal per draw remains. Missing bones, short skeletons, stale owners and out-of-domain inputs
retain their bounds/refusals; names are not normalized to invent a match.

## Native before/after renders

Lorencia 128,124, 61 consecutive draws, software backend 640x480, clocks 0 and 123456. Baselines taken once
from main: older maces and `0x0f2a` at `825c37b7`, new five at #355/main `127489e0` in a separate lane-owned
baseline worktree. After captures use this implementation with the respective merged programs.

| Fixture | Accepted / refused, before → after | Created / unsupported particles, before → after | Last draw particles / sprites, before → after | After walls, clocks 0 / 123456 |
|---|---|---|---|---|
| Older two | 1,719 / 0 → 1,719 / 0 | 72 / 0 → 72 / 0 | 33 / 10 → 33 / 27 | 2.083 / 2.215 s |
| `0x0f2a` | 488 / 154 → 642 / 0 | 0 / 154 → 154 / 0 | 0 / 0 → 62 / 5 | 1.878 / 6.095 s |
| Five new | 2,988 / 322 → 3,249 / 61 | 60 / 261 → 321 / 0 | 24 / 24 → 96 / 44 | 2.376 / 2.410 s |

Before walls: older two 1.718 / 1.427 s; `0x0f2a` 1.324 / 1.312 s; new five 2.369 / 1.977 s. The 61
remaining refusals are the exact bone-name mismatch above, not unsupported particle kinds. Inspected
before/after/difference crops show glow, smoke, rings and glints. Changed pixels: older world maces 2,326,
`0x0f2a` world 1,799, new five world 10,784.

Viewer, 16 frames from counter 3: owned spark fixture 160 / 6 → 166 / 0 requests, six particles created/drawn
(before 0.998 s, after 1.422 s); `0x0f2a` 128 / 40 → 168 / 0, forty created/drawn (0.806 / 1.503 s).
Inspected differences change 24,449 and 36,431 pixels respectively.

One default-draw byte-identity sweep: October 22 **28/28 PNGs + 28/28 dumps**; DATA-ACQ-002 **64/64 PNGs +
64/64 dumps**. All normalized reports match: output paths replaced, only the fourteen expected added bitmap
presence entries removed, all remaining fields equal. No draw_all. Before/after walls: October 22
15.263 / 18.915 s; DATA-ACQ-002 37.166 / 48.854 s. These native before/after renders do not establish
original-client pixel or pose equivalence.

## Checks and test budget

All commands from the repo root, heavy jobs nice 10, builds at most `-j4`, runners `--jobs 2`. Resource waits
when load exceeded 14. No full lane gate. Canonical private env: `. ~/Documents/MTM/mu-mac-tools/native/private-env.sh`.

- Builds: baseline root 30.21 s + explicit render targets 4.40 s; implementation 11.09 s; merged-main 10.34 s.
- Small original sample: 11,414 comparisons, zero mismatches, 7.335 s.
- Full sample, once: **57,000** particle comparisons (19,000 each create/move/render), zero mismatches,
  **35.712 s**, `cd672c00`; **1,000** four-mace point cases + **14** loader mappings, zero mismatches,
  **12.048 s**, `041c1805`. Total **58,014** component comparisons. Incoming main changed no particle logic;
  the later particle-source edit only corrected an include comment, so the full proof was retained.
- New registry row: **1,174 comparisons, 31/31 unique compiled mutants caught, zero stopped, 32.1 s**,
  `041c1805`. Only this new row's mutants ran, once. All other rows without mutants.
- Initial affected selection 53/211 rows, 71.76 s. All 52 prior rows passed: **281,021** reported comparisons,
  **397.74 s** including selection, `cd672c00`. Final selection again **53/211 rows, 82.89 s**, retaining
  movement fallback. After main, only the 36 prior rows whose compiled inputs changed reran; results below.
- Initial portable affected run: **1,623 tests, 1,355 passed, 268 skipped, zero failures/errors**;
  **273.8 s** runner wall / **322.52 s** including selection. Selected 150 work items, 142 native modules.
- **8d reduced**: initial private shared consumers **34 tests OK, zero skipped, 25.675 s**. After main,
  **37 tests: 36 passed, one fixture-expectation failure, 47.336 s**. The exact Hammer14 name mismatch was
  traced without production changes; only that failed test reran, **1 test OK / 3.095 s**. Modules:
  `test_render_effects23`, `test_native_particles`, `test_render_effects22`, `test_render_effects16.Native`,
  `test_render_effects20.Native`, `test_native_renderchar`. The world test requires all eight programs.
- Manifest tests: **17 OK / 0.783 s**. The initial synthetic loaded host crashed with an empty draw target;
  the fixture now uses the real raster. Its three new native tests pass in subsequent private runs.

Post-main validator rerun: **36 passed, 190,569 comparisons, zero failures/errors/skips, 326.19 s** including selection.
Portable merge delta (`--affected-since 19d3ff5f`): **1,591 tests, 1,331 passed, 260 skipped, zero failures/errors**;
**293.2 s** runner wall / **346.69 s** including selection, 146 work items. Final audit/documentation checks pending.


## Affected validator results

Initial head `cd672c007190e2166c8aef7ea2c68f9abc4b7730`; post-main head 86f0c40e75514b94007cbc6da033691b2bf136a0. New row at `041c1805`.
A dash retains the initial proof because the merge selector pruned that row. No compiled logic changed afterward.

| Validator | Comparisons initial / post-main | Wall initial / post-main |
|---|---:|---:|
| `validate_app_polish1` | 752 / — | 19.2 s / — |
| `validate_app_polish4` | 10,485 / — | 34.5 s / — |
| `validate_audio_callers` | 5,528 / 5,528 | 6.1 s / 6.5 s |
| `validate_audio_domains` | 2,544 / 2,544 | 21.2 s / 24.2 s |
| `validate_audio_items` | 3,000 / 3,000 | 4.4 s / 5.9 s |
| `validate_icarus_c2` | 8,400 / 8,400 | 19.1 s / 21.4 s |
| `validate_inventory_fx` | 8,017 / 8,017 | 7.8 s / 9.0 s |
| `validate_item_callers` | 6,013 / 6,013 | 1.8 s / 1.2 s |
| `validate_item_effects` | 1,500 / — | 3.2 s / — |
| `validate_meshdraw` | 14,619 / 14,619 | 59.8 s / 66.5 s |
| `validate_model_edge` | 954 / 954 | 120.2 s / 144.3 s |
| `validate_movement` | 6,614 / 6,614 | 57.5 s / 70.7 s |
| `validate_particles` | 407 / — | 1.1 s / — |
| `validate_render_effects` | 660 / — | 1.3 s / — |
| `validate_render_effects10` | 154 / 154 | 0.4 s / 0.4 s |
| `validate_render_effects11` | 176 / 176 | 0.4 s / 0.3 s |
| `validate_render_effects12` | 64 / 64 | 0.3 s / 0.3 s |
| `validate_render_effects13` | 180 / 180 | 0.6 s / 0.5 s |
| `validate_render_effects14` | 660 / 660 | 1.4 s / 1.2 s |
| `validate_render_effects15` | 509 / 509 | 1.0 s / 0.8 s |
| `validate_render_effects16` | 424 / 424 | 3.5 s / 3.0 s |
| `validate_render_effects17` | 618 / 618 | 7.5 s / 8.2 s |
| `validate_render_effects18` | 540 / 540 | 1.4 s / 1.2 s |
| `validate_render_effects19` | 400 / 400 | 1.1 s / 0.9 s |
| `validate_render_effects20` | 148 / 148 | 0.3 s / 0.2 s |
| `validate_render_effects21` | 267 / 267 | 0.4 s / 0.3 s |
| `validate_render_effects22` | 202 / 202 | 4.5 s / 5.9 s |
| `validate_render_effects23` | — / 1,174; 31/31 mutants | — / 32.1 s |
| `validate_render_effects3` | 720 / — | 1.0 s / — |
| `validate_render_effects4` | 1,920 / — | 6.0 s / — |
| `validate_render_effects5` | 1,190 / 1,190 | 4.2 s / 4.7 s |
| `validate_render_effects6` | 1,000 / — | 1.3 s / — |
| `validate_render_effects7` | 596 / 596 | 1.5 s / 1.5 s |
| `validate_render_effects9` | 304 / 304 | 1.0 s / 1.1 s |
| `validate_render_worlds_a` | 9,000 / — | 12.9 s / — |
| `validate_world_particle_consumers` | 900 / — | 1.0 s / — |
| `validate_worlds_121` | 4,000 / 4,000 | 6.2 s / 5.7 s |
| `validate_worlds_after` | 13,424 / — | 11.6 s / — |
| `validate_worlds_after2` | 32,216 / 32,216 | 23.2 s / 28.8 s |
| `validate_worlds_after3` | 10,212 / 10,212 | 6.0 s / 11.8 s |
| `validate_worlds_after4` | 9,181 / 9,181 | 11.5 s / 14.1 s |
| `validate_worlds_after5` | 6,000 / 6,000 | 9.4 s / 11.1 s |
| `validate_worlds_after6` | 7,300 / — | 59.9 s / — |
| `validate_worlds_e` | 4,840 / 4,840 | 16.4 s / 16.9 s |
| `validate_worlds_fog` | 4,044 / — | 7.8 s / — |
| `validate_worlds_g3` | 4,000 / 4,000 | 3.4 s / 4.1 s |
| `validate_worlds_karutan` | 3,000 / 3,000 | 3.4 s / 3.0 s |
| `validate_worlds_l` | 1,260 / — | 1.3 s / — |
| `validate_worlds_m` | 1,080 / — | 1.3 s / — |
| `validate_worlds_raklion` | 3,000 / 3,000 | 3.9 s / 4.5 s |
| `validate_worlds_slots` | 18,999 / 18,999 | 18.5 s / 18.7 s |
| `validate_worlds_slots2` | 33,000 / 33,000 | 31.7 s / 31.4 s |
| `validate_worlds_slots3` | 36,000 / — | 34.4 s / — |


Steward validators: validate_app_polish1, validate_app_polish4, validate_audio_callers, validate_audio_domains, validate_audio_items, validate_icarus_c2, validate_inventory_fx, validate_item_callers, validate_item_effects, validate_meshdraw, validate_model_edge, validate_movement, validate_particles, validate_render_effects, validate_render_effects10, validate_render_effects11, validate_render_effects12, validate_render_effects13, validate_render_effects14, validate_render_effects15, validate_render_effects16, validate_render_effects17, validate_render_effects18, validate_render_effects19, validate_render_effects20, validate_render_effects21, validate_render_effects22, validate_render_effects23, validate_render_effects3, validate_render_effects4, validate_render_effects5, validate_render_effects6, validate_render_effects7, validate_render_effects9, validate_render_worlds_a, validate_world_particle_consumers, validate_worlds_121, validate_worlds_after, validate_worlds_after2, validate_worlds_after3, validate_worlds_after4, validate_worlds_after5, validate_worlds_after6, validate_worlds_e, validate_worlds_fog, validate_worlds_g3, validate_worlds_karutan, validate_worlds_l, validate_worlds_m, validate_worlds_raklion, validate_worlds_slots, validate_worlds_slots2, validate_worlds_slots3

No steward mutants requested. Use canonical private-env.sh from the root. Tested commits and row walls permit
reuse where compiled inputs have not changed. The combined full gate remains the steward's responsibility.

## Limits and next

The two sprite texture gaps, exact-name/unavailable-bone refusals, native/original pose and absolute counter/random
phase differences, and OBJECT memory outside three hosted points remain. RENDER-ITEMS-002W owns `0x0f2a` blend-light
and item draw fits. No blend-light default, body recipe, item fit or atlas clock changed here. Native Preview
and Wine apps were untouched.

Next: original-loader world slots for `0x81ec` and `0x854a` with native file/filter/wrap checks; investigate
whether an authored model variant supplies exact `up01`, without normalizing names; extend the refusal census
as programs are admitted. Native visibility is not original-client pixel equivalence.

Lane-owned temporary worktree, builds, scratch and renders are removed after the final push and ready-prs entry.
No lane input needs retention. Shared tools/python, evidence and input symlinks were never staged.
