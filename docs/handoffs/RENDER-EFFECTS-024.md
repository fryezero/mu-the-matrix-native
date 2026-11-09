# RENDER-EFFECTS-024

PR-ready on `codex/render-effects-024`, base and latest fetched main `6736cb57`; production inputs committed at
`79f6f832`. Explicit native validator build targets are committed at `1b12f2ac`; no compiled source changed.
Offline/static only. No installed app, live client, launcher, network, server-state, protection-module work or memory writes.

## Scope and addresses

- Two world sprite slots, original LINEAR/CLAMP loader mappings: `0x81ec`, `Effect\lightmarks_red.jpg`, call
  `0x01823365`; `0x854a`, `Effect\light_blue.jpg`, call `0x0182ec0d`. Native files use the OZJ envelope.
- Ferea's one-step `0x413/10` fire emitter: CreateEffect `0x013d2f05` and `0x013d3b33..0x013d3b58`;
  MoveEffect `0x0146d6b9..0x0146d7f5`, shared advance and immediate lifetime retirement.
- Its rand-selected children are `0x8084/3`, `0x806e/4`, `0x8085/0`. The latter two already have consumers.
  New `0x8084/3`: create `0x015d45a8..0x015d4748`, move `0x01646f7f..0x0164723a`, existing sprite render.
- Hammer14's exact `up01 ` versus requested `up01` refusal remains. No guessed name normalization or model swap.
- RENDER-ITEMS-002W owns `0x0f2a` blend light and item draw fits; those are unchanged here.

## Routed versus refused census

Initial instrumented baseline is main `6736cb57`. Diagnostic logging was lane-local and removed from production.
The 14 October 22 views plus 32 DATA-ACQ-002 views, default draw, reported six `0x413/10` refusals and one
`0x7f89/28` particle refusal, all in Ferea. The 61-consecutive-draw Lorencia demo and eight-mace fixture added
no unsupported particle kinds. This is a bounded scene census, not a whole-client census.
The 93 admitted item programs and 30 item particle pairs from EFFECTS-023 are unchanged.

| Scene | Before | After |
|---|---|---|
| Eight maces, Lorencia 128,124, 61 consecutive draws, both clocks | 5,610 accepted / 61 refused program requests; 547 particles created, zero unsupported; last draw 76 sprites | Same program and particle counts; last draw 83 sprites |
| Same maces, missing sprite slots | Two slots, seven counted-only sprite sites per draw | Zero missing slots; all seven sites draw, 427 additional sprite draws over the run |
| Shipped Lorencia demo, 61 draws, both clocks | 2,989 accepted / zero refused player requests, 693 particles created / zero unsupported, last draw 114 sprites | Identical counts and four saved PNGs |
| Ferea arrival 236,152, 61 consecutive draws, both clocks | Zero fire effects created / 183 refused; 34 particles created / 11 refused; last draw 34 particles | 183 fire effects created / zero refused; 214 particles created / 11 refused; last draw 68 particles |
| Ferea closer view 241,154, 41 draws, both clocks | Zero fire effects created / 205 refused; 43 particles created / 14 refused; last draw 43 particles | 205 fire effects created / zero refused; 243 particles created / 14 refused; last draw 99 particles |

The arrival scene creates 180 child particles from the first 180 fire effects; three newly requested effects wait
for the next step at the final draw. The closer scene creates 200 children; five wait. The new effect/particle
rand calls advance the native stream, so later smoke phases differ too. The remaining particles are clouds/28;
missing-bone requests remain separately counted in the object runtime.

The only installed authored Hammer14 candidate under Data is `Item/Hammer14.bmd`, SHA-256
`9c294b8ea5d4db8c7ad35543e102076800d3a042fae6ce81b349cc72eab4220c`.
Its 15 bones include bone 9 `up01 `, not `up01`. No authored Hammer14 variant supplies the exact requested name.
That one sprite refusal per draw remains. The private test searches the installed Data tree and compares the
unmodified parsed names. This does not claim that no different, unavailable asset could contain that name.

## Renders and byte identity

All fixtures use demo names, software backend, 640x480. Clocks start at 0 or 123456 ms. Before images were taken
once from main; the saved lane-owned baseline binary supplies only the additional closer scene and the second
arrival clock. No original-client pixels or live client were used.

Opened and inspected before | after | 4x-difference images. The mace texture additions change 2,131 / 2,123 pixels
at clocks 0 / 123456, bounding box (249,150)-(331,227). The closer Ferea view shows fire and a changed smoke phase:
6,499 / 6,490 pixels, bounding box (281,0)-(361,138). The arrival view's 640x480 final frame is identical because
the fire is outside that camera's horizontal view; its created/drawn counts are not a claim of visible pixels there.
The default 640x400 Ferea view does show the fire, 222 changed pixels at (617,152)-(636,171).

One default-draw sweep, no draw_all, 640x400:
- October 22: 28/28 PNGs and 28/28 OBJECT/light dumps byte-identical. All normalized reports equal.
- DATA-ACQ-002: 63/64 PNGs and 64/64 OBJECT/light dumps byte-identical. Only Ferea's second PNG changes as intended;
  only its report changes. Other reports equal after replacing output paths and removing the two new bitmap
  presence entries at slots 90/91. Total: 91/92 PNGs, 92/92 dumps. No unrelated image or state changes.

Tour walls from the capture script: before October 22 / DATA-ACQ-002 16.383 / 34.409 s, after 34.671 / 32.792 s.
The after October 22 wall includes a pause while the validator selector completed; it is not a performance result.
Eight-mace renders, before -> after: default 2.547 -> 2.681 s; clock 123456 2.367 -> 2.370 s.
Demo: 1.983 -> 1.966 s and 1.964 -> 1.969 s. Ferea arrival: 2.010 -> 2.809 s and 2.407 -> 2.811 s.
Closer Ferea: 1.824 -> 1.833 s and 1.830 -> 1.970 s. These short native measurements do not establish a speed claim.

## Checks and test budget

Commands run from the repo root. Heavy jobs use nice 10, make at most four jobs, validator runners two.
A two-minute pause and resource recheck followed load >14. No full lane gate. Canonical private env:
`. ~/Documents/MTM/mu-mac-tools/native/private-env.sh`.

| Check | Result | Wall |
|---|---|---:|
| Final root build, then explicit mu-world/mu-walk/mu-render targets | Pass | 0.83 s + 4.54 s |
| Full new proof, once | 11,006 component comparisons, zero mismatches: 11,000 Unicorn, two static loader registrations, four native loader/pool checks | 12.217 s script / 12.26 s command |
| New registry row, mutants once | 226 comparisons, zero mismatches, 18/18 compiled mutants caught, zero stopped | 30.5 s row / 30.62 s command |
| Private changed modules plus bitmap/struct consumers | 15 tests: 14 passed, one fixture-path expectation failed; corrected failed test rerun passes | 18.795 s / 1.899 s rerun; command walls 18.87 / 1.94 s |
| Checkpoint audit | 2,129 staged files, zero rejected | 17.66 s |

The private modules are `test_render_effects24`, `test_native_particles`, `test_render_effects23.Native`,
`test_render_effects22.Native`, `test_render_effects20.Native`, `test_render_effects16.Native`. The new world test
initially passed October 22 placements to Ferea, yielding no emitter requests. It now explicitly requires
`MU_SNAPSHOT_DIR/data-acq-002/plain`. Only that failed test reran. Production code and original proofs did not change.
**8d reduced**: the selector chooses 155 work items, including 144 native modules, above the 40-item cap
(selection wall 45.21 s). Both changed/added native modules are covered privately, plus the four shared consumers
required by the bitmap count/struct search. The full private native/tests run belongs to the app-refresh lane.

The 18 mutants are seven effect admission/create/move mutants, five child admission/create/move mutants and six
native ID/file/filter/wrap mutants. They compile production C; none relies on a changed expected value. Existing
mutant targets are unchanged and were not rerun. Shared `MU_WORLD_PT_BITMAPS` consumers were searched by hand.

Portable affected selection: **155/192 work items**, **144 native modules**, **45.21 s**. The affected run covers
**12 reported suites, 1,702 tests: 1,421 passed, 280 skipped, one failure, zero errors**, **252.5 s** test wall /
**297.44 s** command including selection. Every native module passed: 920 tests, 759 passed and 161 skipped.
The sole failure was `test_native_rows_have_target_provenance`: the new row named native without its explicit
archive targets. Commit `1b12f2ac` adds `build/libmunative.a` and `build/libmusession_world.a`; the failed test alone
passes, **1 test / 2.081 s**, **2.18 s** command. No C, comparator or mutant target changed. Thus all 1,422 eligible
portable tests are covered by passing results; 280 portable private-input skips remain expected. No full gate.
The corrected registry row passes at `1b12f2ac54dd8a0e66a95f30ffe3787119fdcc75`: **226 comparisons, zero
mismatches, no mutants, 2.0 s row / 2.13 s command**. The 57 prior proofs remain valid because only manifest build
target metadata changed. Latest main remains `6736cb57`; the final merge reports already up to date.
Final staged audit: **2,129 files, zero rejected, 15.65 s**. `git diff --check` is clean. Manual review covers
the original branch formulas, preserved existing flame paths, loader IDs/files/filter/wrap, native pool handoff,
strict bone names, tests, manifest build targets and the selected rows. No delegate was used.

## Affected validators

At `79f6f83269d6f943a8afd4c22eec2d6aa4f06388`: **57/57 pass**, **305,029 reported comparisons**, zero
failures/errors/skips, without mutants. Command wall including selection **363.62 s**. Explicit initial selection
**57/213 rows, 62.77 s**, including the movement symbol fallback. The selector prunes 33 other library rows
because they use no changed symbols. The new row repeats only its no-mutant proof here.

| Validator | Comparisons | Wall |
|---|---:|---:|
| `validate_app_polish1` | 752 | 22.9 s |
| `validate_app_polish4` | 10,485 | 28.8 s |
| `validate_audio_callers` | 5,528 | 5.2 s |
| `validate_audio_combat` | 19,548 | 19.4 s |
| `validate_audio_domains` | 2,544 | 20.9 s |
| `validate_audio_items` | 3,000 | 3.0 s |
| `validate_icarus_c2` | 8,400 | 14.5 s |
| `validate_inventory_fx` | 8,017 | 6.4 s |
| `validate_item_callers` | 6,013 | 1.4 s |
| `validate_item_effects` | 1,500 | 1.9 s |
| `validate_meshdraw` | 14,619 | 54.8 s |
| `validate_model_edge` | 954 | 108.4 s |
| `validate_movement` | 6,614 | 49.4 s |
| `validate_particles` | 407 | 0.8 s |
| `validate_render_effects` | 660 | 0.8 s |
| `validate_render_effects10` | 154 | 0.4 s |
| `validate_render_effects11` | 176 | 0.3 s |
| `validate_render_effects12` | 64 | 0.3 s |
| `validate_render_effects13` | 180 | 0.4 s |
| `validate_render_effects14` | 660 | 1.0 s |
| `validate_render_effects15` | 509 | 0.6 s |
| `validate_render_effects16` | 424 | 3.0 s |
| `validate_render_effects17` | 618 | 6.4 s |
| `validate_render_effects18` | 540 | 0.9 s |
| `validate_render_effects19` | 400 | 0.7 s |
| `validate_render_effects20` | 148 | 0.2 s |
| `validate_render_effects21` | 267 | 0.3 s |
| `validate_render_effects22` | 202 | 4.2 s |
| `validate_render_effects23` | 1,174 | 5.6 s |
| `validate_render_effects24` | 226 | 2.6 s |
| `validate_render_effects3` | 720 | 0.8 s |
| `validate_render_effects4` | 1,920 | 4.9 s |
| `validate_render_effects5` | 1,190 | 3.7 s |
| `validate_render_effects6` | 1,000 | 1.0 s |
| `validate_render_effects7` | 596 | 1.3 s |
| `validate_render_effects9` | 304 | 0.9 s |
| `validate_render_worlds_a` | 9,000 | 9.6 s |
| `validate_skill_fx` | 660 | 0.8 s |
| `validate_world_particle_consumers` | 900 | 0.6 s |
| `validate_worlds_121` | 4,000 | 3.4 s |
| `validate_worlds_after` | 13,424 | 9.4 s |
| `validate_worlds_after2` | 32,216 | 19.9 s |
| `validate_worlds_after3` | 10,212 | 5.9 s |
| `validate_worlds_after4` | 9,181 | 10.1 s |
| `validate_worlds_after5` | 6,000 | 8.3 s |
| `validate_worlds_after6` | 7,300 | 50.7 s |
| `validate_worlds_d` | 2,400 | 2.9 s |
| `validate_worlds_e` | 4,840 | 13.5 s |
| `validate_worlds_fog` | 4,044 | 6.5 s |
| `validate_worlds_g3` | 4,000 | 3.5 s |
| `validate_worlds_karutan` | 3,000 | 2.3 s |
| `validate_worlds_l` | 1,260 | 0.9 s |
| `validate_worlds_m` | 1,080 | 0.8 s |
| `validate_worlds_raklion` | 3,000 | 2.7 s |
| `validate_worlds_slots` | 18,999 | 12.0 s |
| `validate_worlds_slots2` | 33,000 | 20.6 s |
| `validate_worlds_slots3` | 36,000 | 20.9 s |

Steward validators: validate_app_polish1,validate_app_polish4,validate_audio_callers,validate_audio_combat,validate_audio_domains,validate_audio_items,validate_icarus_c2,validate_inventory_fx,validate_item_callers,validate_item_effects,validate_meshdraw,validate_model_edge,validate_movement,validate_particles,validate_render_effects,validate_render_effects10,validate_render_effects11,validate_render_effects12,validate_render_effects13,validate_render_effects14,validate_render_effects15,validate_render_effects16,validate_render_effects17,validate_render_effects18,validate_render_effects19,validate_render_effects20,validate_render_effects21,validate_render_effects22,validate_render_effects23,validate_render_effects24,validate_render_effects3,validate_render_effects4,validate_render_effects5,validate_render_effects6,validate_render_effects7,validate_render_effects9,validate_render_worlds_a,validate_skill_fx,validate_world_particle_consumers,validate_worlds_121,validate_worlds_after,validate_worlds_after2,validate_worlds_after3,validate_worlds_after4,validate_worlds_after5,validate_worlds_after6,validate_worlds_d,validate_worlds_e,validate_worlds_fog,validate_worlds_g3,validate_worlds_karutan,validate_worlds_l,validate_worlds_m,validate_worlds_raklion,validate_worlds_slots,validate_worlds_slots2,validate_worlds_slots3

No steward mutants requested. Use canonical private-env.sh from the repo root, including MU_SECTION3,
MU_SNAPSHOT_DIR and the original-side cache. Tested compiled inputs are at the commit above; final documentation
commits change no compiled input. The steward may reuse rows whose compiled inputs are unchanged.


## Limits and next

`0x7f89/28` cloud motion, exact-name and unavailable-bone refusals, native/original pose and process-random/counter
phase differences remain. The new emitter has no world Fire mesh slot; its native consumer supplies the verified
particle request. Native before/after visibility does not establish original-client pixel equivalence.
No `0x0f2a` blend light, body fit, atlas clock, installed Native Preview or Wine app changes here.

Next: recover CreateParticle/MoveParticles/RenderParticles for Ferea clouds/28, including its orbit/position helper
and original record lifetime. Expand the scene census when admitting more programs. Keep the exact-name refusal
unless the corresponding authored asset supplies the requested name. The merge steward owns the full gate and merge.

## Cleanup

Lane-owned renders, scratch and build outputs are removed after the final push and ready-prs entry, followed by
the worktree and local branch. No new private input needs retention. Shared evidence, input links, Python and the
original-side validator cache are not removed.
