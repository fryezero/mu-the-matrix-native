# RENDER-EFFECTS-023

Implementation checkpoint, not PR-ready. Branch `codex/render-effects-023`, initially based on main `825c37b7`;
#355/main `127489e0` is now merged. The sections below retain the earlier checkpoint evidence. Offline/static only; no live client,
launcher, installed app, server-state work, protection analysis or memory writes.

Scope: world bitmap slots for `0x7f7a` and `0x80ba`; the 19 remaining mace particle pairs in
`reconstructed/particles/item_mace_kinds.inc`; 12 other bitmap slots for those particles; direct OBJECT point
following for `0x7ffb/0`, `0x85fc/1,/2`; per-item OBJECT keys in `mu-render character`. RENDER-ITEMS-002W keeps
the blend-light input and body-fit work. Existing EFFECTS-022 consumers are unchanged.

The source/include, native point adapter, bitmap table, viewer caller, synthetic host and new validator are
implemented. The generator/table point comparisons for #355's newly admitted maces, affected checks, final
mutants, renders and census remain pending. No ready-prs entry has been written.

## Checkpoint evidence

- Baseline build: root `nice -n 10 make -j4`, 30.21 s; render targets, 4.40 s. Implementation build: 11.09 s.
- Small original sample on the implementation: 11,414 comparisons, zero mismatches, 7.335 s. Create/move/render
  each 3,800; 14 static original loader mappings. The full sample and compiled mutants have not run yet.
- Synthetic native tests: viewer registry and no-asset generation tests pass. The loaded-bitmap host initially
  used an empty draw target and crashed on the first loaded quad; it now uses the real raster target. The failed
  loader test passes alone, 1 test in 1.927 s, with all 19 particle draws and distinct file/filter/wrap checks.
- Baseline, Lorencia 128,124, 61 consecutive draws at default and clock 123456: the two older maces create 72
  particles, zero refused, last frame 33 particles and 10 sprites drawn; `0x0f2a` has 488 accepted sprite requests
  and 154 refused particles, with zero particles and zero sprites drawn. The missing texture requests are
  counted separately from kind refusals.
- One baseline default-draw tour sweep is captured: October 22, 28 PNGs and 28 dumps; DATA-ACQ-002, 64 PNGs
  and 64 dumps. Their hashes and normalized reports are local; bulk tour outputs are already removed.
- Viewer baseline, 16 frames starting counter 3: owned-spark fixture 160 effects / 6 refused; `0x0f2a` fixture
  128 / 40. Native before/after images do not establish original-client pixel equivalence.

All test/tool commands run from the repository root. Builds use at most four jobs, runners at most two,
heavy commands nice 10. Shared `tools/python`, `evidence` and `input` are symlinked and not staged.


## Second checkpoint

The full particle-only sample passes **57,000 comparisons**, zero mismatches, **35.712 s**, at `cd672c00`:
19,000 create, 19,000 move, 19,000 render. Four-mace point-store checks and compiled mutants remain pending
#355. No full gate has run.

The first affected selector retains **53 rows**, with the movement fallback; 31 unchanged-symbol rows are
pruned. Selection wall 71.76 s. The **52 available rows all pass**, zero errors/failures/skips, **397.74 s**
including the runner's own selection. `validate_render_effects23` is the remaining row, pending #355's programs.
The portable unit selection is **150 work items**, including **142 native modules** (49.67 s selection).
8d reduced applies. Private from the root, canonical env: `test_render_effects23.Native`, `test_native_particles`,
`test_render_effects22`, `test_render_effects16.Native`, `test_render_effects20.Native`, `test_native_renderchar`:
**34 tests OK, zero skipped, 25.675 s**, after the synthetic host correction. The viewer test now uses a private
binary copy, as does the pending all-mace world test.

Native after results at this code, 61 consecutive draws:

| Fixture | Requests created / refused | Last draw: particles / sprites | Wall default / clock 123456 |
|---|---|---|---:|
| Two older maces | 1,719 / 0, same request counts as before | 33 / **27**, sprites were 10 | 2.083 / 2.215 s |
| `0x0f2a` | **642 / 0**, was 488 / 154 | **62 / 5**, was 0 / 0 | 1.878 / 6.095 s |

Viewer after, 16 frames from counter 3: spark fixture **166 / 0**, 6 created/drawn particles (1.422 s);
`0x0f2a` **168 / 0**, 40 created/drawn (1.503 s). The inspected before/after/4x-difference crops change 2,326
pixels for the older world maces, 1,799 for `0x0f2a` in the world, 24,449 for the viewer spark and 36,431 for
viewer `0x0f2a`, around the weapons/effects. These are native render differences.

Static sprite-slot census over the eight mace programs identifies two further bitmap gaps, outside the requested
slots: `0x81ec` at three bone-sprite sites of `0x0f2a` (`Effect\lightmarks_red.jpg`, loader `0x01823365`) and
`0x854a` at four sites of `0x0f2b`. They remain counted-only. Every other sprite site in these eight programs
has a world bitmap slot. Particle kind coverage and missing sprite textures are separate counts.

### Initial affected validator results

52 rows, 281,021 reported comparisons, at `cd672c007190e2166c8aef7ea2c68f9abc4b7730`. No mutants in this batch.

| Validator | Comparisons | Wall |
|---|---:|---:|
| `validate_app_polish1` | 752 | 19.2 s |
| `validate_app_polish4` | 10,485 | 34.5 s |
| `validate_audio_callers` | 5,528 | 6.1 s |
| `validate_audio_domains` | 2,544 | 21.2 s |
| `validate_audio_items` | 3,000 | 4.4 s |
| `validate_icarus_c2` | 8,400 | 19.1 s |
| `validate_inventory_fx` | 8,017 | 7.8 s |
| `validate_item_callers` | 6,013 | 1.8 s |
| `validate_item_effects` | 1,500 | 3.2 s |
| `validate_meshdraw` | 14,619 | 59.8 s |
| `validate_model_edge` | 954 | 120.2 s |
| `validate_movement` | 6,614 | 57.5 s |
| `validate_particles` | 407 | 1.1 s |
| `validate_render_effects` | 660 | 1.3 s |
| `validate_render_effects10` | 154 | 0.4 s |
| `validate_render_effects11` | 176 | 0.4 s |
| `validate_render_effects12` | 64 | 0.3 s |
| `validate_render_effects13` | 180 | 0.6 s |
| `validate_render_effects14` | 660 | 1.4 s |
| `validate_render_effects15` | 509 | 1.0 s |
| `validate_render_effects16` | 424 | 3.5 s |
| `validate_render_effects17` | 618 | 7.5 s |
| `validate_render_effects18` | 540 | 1.4 s |
| `validate_render_effects19` | 400 | 1.1 s |
| `validate_render_effects20` | 148 | 0.3 s |
| `validate_render_effects21` | 267 | 0.4 s |
| `validate_render_effects22` | 202 | 4.5 s |
| `validate_render_effects3` | 720 | 1.0 s |
| `validate_render_effects4` | 1,920 | 6.0 s |
| `validate_render_effects5` | 1,190 | 4.2 s |
| `validate_render_effects6` | 1,000 | 1.3 s |
| `validate_render_effects7` | 596 | 1.5 s |
| `validate_render_effects9` | 304 | 1.0 s |
| `validate_render_worlds_a` | 9,000 | 12.9 s |
| `validate_world_particle_consumers` | 900 | 1.0 s |
| `validate_worlds_121` | 4,000 | 6.2 s |
| `validate_worlds_after` | 13,424 | 11.6 s |
| `validate_worlds_after2` | 32,216 | 23.2 s |
| `validate_worlds_after3` | 10,212 | 6.0 s |
| `validate_worlds_after4` | 9,181 | 11.5 s |
| `validate_worlds_after5` | 6,000 | 9.4 s |
| `validate_worlds_after6` | 7,300 | 59.9 s |
| `validate_worlds_e` | 4,840 | 16.4 s |
| `validate_worlds_fog` | 4,044 | 7.8 s |
| `validate_worlds_g3` | 4,000 | 3.4 s |
| `validate_worlds_karutan` | 3,000 | 3.4 s |
| `validate_worlds_l` | 1,260 | 1.3 s |
| `validate_worlds_m` | 1,080 | 1.3 s |
| `validate_worlds_raklion` | 3,000 | 3.9 s |
| `validate_worlds_slots` | 18,999 | 18.5 s |
| `validate_worlds_slots2` | 33,000 | 31.7 s |
| `validate_worlds_slots3` | 36,000 | 34.4 s |

## Combined-main checkpoint

Main #355 is incorporated. The four-mace OBJECT point-store proof passes 1,000 cases plus 14 loader checks,
12.048 s. The new registry row passes 1,174 comparisons and catches 31/31 unique compiled mutants, zero
stopped, 32.1 s, at `041c1805`. The full 57,000 particle proof remains valid: incoming main changes no particle
logic. Static census: 93 programs, 30 particle pairs supported, zero unresolved bitmap expressions.

The portable initial run passed 1,623 tests (1,355 passed, 268 skipped), 273.8 s runner wall / 322.52 s including
selection. After main, the private reduced run passed 36 of 37 tests and exposed the all-mace fixture's overly
strict zero-refusal expectation. Hammer14 has `up01 ` with a trailing space, whereas the program requests `up01`:
that one bone-sprite refusal per draw is retained. The corrected world test passes alone, 3.095 s; no production
bone-matching change. Five new maces, 61 draws at both clocks: 3,249 accepted / 61 refused, 321 particles created,
zero unsupported, last draw 96 particles / 44 sprites. Before: 2,988 / 322, 60 created, 261 unsupported, 24 / 24.

The final default sweep matches 92/92 PNGs and 92/92 object/light dumps. Reports match after normalizing output
paths and removing the fourteen expected added bitmap-presence entries. October 22 after 18.915 s;
DATA-ACQ-002 after measurement is retained locally for the final handoff. The new five-mace before/after crop
changes 10,784 pixels, visibly adding smoke, rings and glints. No original-client pixel claim.

Final selection retains 53 rows including movement fallback, 82.89 s. The 36 initial rows whose compiled inputs
changed after main are being rerun without mutants. Final portable merge-delta checks and docs/audit remain.
