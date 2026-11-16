# RENDER-WORLDS-PICK-001

Branch `claude/render-worlds-pick-001`, from main `c5b9d5ca` (#400, batch 118), integrated through main
`708798ae` (#408, batch 122). PR-ready. Implementation and checks by Claude Fable 5.2, without subagents.
Worktree `~/Documents/MTM/worktrees/render-worlds-pick-001`. Merge belongs to the steward.

Findings: [box, handlers and census](../research/client-worlds-pick.md);
[chain hook 11](../research/client-worlds-inner.md) (last section);
[census CSV](../research/world-inner-census.csv).

## What changed

**1. Map-object box and mouse input (the brief's step 1).**
- `reconstructed/objects/object_pick.{c,h}`: the box write at the end of BMD::Transform `0x012b5bde` as
  RenderObject's setup calls it, the mode-2 vertex bounds, and the exported segment test.
- The object runtime writes OBJECT `+0x31c` where the setup reaches its Transform call
  (`mu_objects_runtime.c` `write_obb`), and the walk frame's mouse segment reaches the registry's tick handlers
  4 and 6 through `rt.mouse_start` / `rt.mouse_end`.
- Three facts from the original, all verified:
  - the box is axis-aligned in the game: box minimum + position, box extents; the object's turn and scale do
    not enter it (bounds mode `0x0b437bfc` is only ever compared, never stored);
  - a segment that touches the box counts as over it;
  - an object not drawn yet has an all-zero box, and that box is over for every segment.
- **No live action row uses handlers 4 or 6** (the local table: 143 rows, handlers 0, 1, 2, 5, 7, 8). This
  completes an adapter gap. Nothing visible changes in any captured world.

**2. The all-world inner-object census (step 2).**
- `scripts/world_inner_census.py` walks every routine RenderObjectVisual can reach for a map object (its own
  world cases, the 13 chain hooks, the 48 class visual slots) on the pinned text and lists, per world, the
  types each treats specially, the case address and its requests. Native status comes from the consumer
  oracles and a `mu-world` probe per (world, type).
- **Totals: 62 routines, 730 rows, 941 (world, type) pairs: 420 drawn, 213 partial, 308 refused.**
  Refused: 274 no native producer (chain hooks 1 and 6), 15 every draw refused, 13 no model file, 6 not
  probed. 66 distinct consumer pairs are missing (53 particle, 9 effect, 4 joint); ids are in the CSV and the
  finding.

**3. Chain hook 11, the 46/98 handler (step 3).**
- The census found the handler INNER-004/005 could not: the eleventh chain hook is a virtual call on the
  singleton `0x01ec9118` (vtable `0x01aa7a08`, visual slot `0x00db7656`), for worlds 45..50 and 98..99.
- `reconstructed/objects/world_inner6_visual.c` `mu_chain11_inner` ports its eleven types; the runtime routes
  those eight worlds through it and no longer counts a refusal per draw in 46 and 98.
- Producer only. Of its requests, 0x7f89/16, 0x7f5a/0 and the 0x7ef7 sprite have consumers. Ten pairs do not
  and stay counted by the pools: particles 0x8022/0, 0x8022/3, 0x7f89/15, 0x7f89/17, 0x7dea/0, 0x7dec/0,
  0x801c/2, 0x801d/2; effects 0x4cc/0, 0x4cc/1. They belong to RENDER-EFFECTS-033 or its successor.

Shared files, added lines only: `native/Makefile` (one source, one host rule), `mu_objects_anim.c` (two
lines), `world/parts/objects.c` (two lines), `reconstructed/objects/Makefile`, `action_registry.c` (the
exported wrapper), `scripts/validators.toml` (two rows). `mu_objects_runtime` gains two pointers and one
counter at its end; the step-input struct is unchanged. `native/tests/worlds_inner_host.c` replaces the 46/98
refusal assertion with hook 11 assertions.

## Checks

All commands ran from the repo root with nice 10, make at most four jobs and validator/test jobs 2, behind a
load / free-memory guard (1-minute load at most 14, free memory at least 25 percent). Private commands source
`~/Documents/MTM/mu-mac-tools/native/private-env.sh`. No full lane gate, no app packaging. The machine was shared
with five other lanes; the walls are not performance figures.

Main moved four times while the lane finished (batches 119 to 122). Each merge got the affected rerun the
test budget asks for, so the table has four tested commits: `0d4168cb` (batch 119 merged), `09014501` (batch
120), `4b01da82` (batch 121) and `f1cda80b` (batch 122, the PR head's code).

| Check | Result | Wall s |
|---|---|---:|
| Root build, final tree | Pass | 23.2 |
| `validate_worlds_pick` with mutants (once) | 3,000 cases (box, segment, pick) equal, 0 stops; 23/23 mutants, lowest 23 | 343.4 |
| `validate_worlds_inner6` with mutants (once) | 2,000 cases (chain11, chain11_focus) equal, 0 stops; 37/37 mutants, lowest 6; world test: exactly 45..50, 98, 99 | 284.3 |
| Affected validators at `0d4168cb`, no mutants, cached | 92/92 rows pass, 1,316,455 reported cases | 1,579.9 |
| Rows whose inputs batch 120 changed, at `09014501` | 63/63 pass, 1,139,725 reported cases | 1,151.5 |
| Rows whose inputs batch 121 changed, at `4b01da82` | 15/15 pass, 101,776 reported cases | 309.9 |
| Rows whose inputs batch 122 changed, at `f1cda80b` | 33/33 pass, 292,713 reported cases | 640.0 |
| Affected portable suites at `0d4168cb` | 183 work items selected, 182 run: 1,809 tests, 1,454 passed / 355 expected skips, 0 failures, 0 errors | 431.5 |
| Portable items batch 120 changed, at `09014501` | 193 selected, 192 run: 1,955 tests, 1,579 passed / 376 expected skips, 0 failures, 0 errors | 465.0 |
| Portable items batch 121 changed, at `4b01da82` | 164 selected, 163 run: 1,613 tests, 1,272 passed / 341 expected skips, 0 failures, 0 errors | 396.3 |
| Portable items batch 122 changed, at `f1cda80b` | 187 selected, 186 run: 1,628 tests, 1,293 passed / 335 expected skips, 0 failures, 0 errors | 440.3 |
| Private modules (8d reduced), at each of the four commits | 14 tests, 0 skips: `test_native_worlds_pick`, `test_native_worlds_inner`, `test_native_anim`, `test_worlds_inner4`, `test_worlds_inner5` | 2.7 |
| Census walk and probes at `09014501` | 62 routines, 730 rows; one probe per (case, object folder, type); the CSV is byte-identical to the `0d4168cb` run | 750.2 |
| Base sweep (main `708798ae`) | 46 views, no failures | 72.5 |
| Lane sweep (`f1cda80b`) | 46 views, no failures | 61.24 |
| Hook 11 proofs, worlds 46 and 98, both binaries | 4 runs | 4.5 |
| Repository audit | 2,421 staged files, 0 rejected | 19.4 |
| Documentation consumers, after the last doc edit | 36 tests, 35 passed / 1 expected skip | 15.1 |

- **Mutants ran once each**, for the two validators this lane created. `validate_worlds_pick`'s run is at
  `5eaeb445`, `validate_worlds_inner6`'s at `0d4168cb`. No later merge or commit changes their compiled inputs
  (`reconstructed/objects`); both rows also pass without mutants at `0d4168cb`.
- Before those counted runs, three planted mistakes were repaired: two `validate_worlds_pick` mutants and one
  `validate_worlds_inner6` mutant left a parameter unused and did not compile under `-Werror`, and one
  `validate_worlds_pick` mutant (`e >= 1` for `e > 0`) is equivalent on integer-valued boxes and was replaced.
  A first `validate_worlds_inner6` runner call stopped at that compile error after four mutants; the counted
  run is the complete second one.
- The portable selections exclude only `native/tests/test_native_app.py` (it builds and signs a bundle).
- **8d reduced:** the private native selection is far above the 40-item cap (`mu_objects.h` and the native
  Makefile select most of `native/tests`), so the modules this lane changed or added ran privately, plus the
  two INNER tests that pin the factory inventory (48 classes, 57 registrations, neither 46 nor 98).
- 6b: `mu_objects_runtime` gained fields at its end only. No test or script mirrors its layout; the one
  existing consumer of its last field (`worlds_s3_host.c`, `imperial_frame`) is in the portable runs. The
  ctypes mirror of `mu_anim_inputs` (`validate_worlds_after5/6`) is unchanged: that struct was not touched.
- A first census run and a first chain of checks ran on the pre-merge tree and were stopped when batch 119
  landed; nothing from them is reported here.
- The census was not walked again after `09014501`: batches 121 and 122 change nothing under
  `reconstructed/objects`, `reconstructed/particles`, `reconstructed/joints`, `reconstructed/combat`, the object
  runtime, `native/core/mu_particles.c` or the script.

## Renders and fidelity

Both binaries were built with `make -C native -j4 world` in this lane's own tree: the base from a detached
checkout of main `708798ae`, the lane from the merged branch.

- Base, main `708798ae`: `c5f5f0699c69bf4a8b7ef5a60bdd0dff669029c4ade037edb25f85e52566752b`.
- Lane, `f1cda80b`: `ff08c50ed447668f27d070744d0d91a592093590d88c5c204a5731e50237d477`.

The same comparison was made at the three earlier integration points and gave the same counts: base
`b6549bcd...` (main `c255e4dd`) against lane `436244f5...` (`0d4168cb`), base `2ea68441...` (main `bb86bbf7`)
against lane `6bb25918...` (`09014501`), and base `acc4754f...` (main `c49fa188`) against lane `7436fbea...`
(`4b01da82`).

**Default identity sweep.** The 14-view October tour and the 32-view acquisition tour, 640x400, 25 steps
sampled at 0 and 24, without draw-all.

| Compared | Result |
|---|---|
| PNG frames | 92/92 identical |
| Normalized reports | 46/46 identical |
| Light dumps | 46/46 identical |
| OBJECT dumps | 0/46 identical, by intent |

No view changes. Every OBJECT dump changes because drawn objects now carry their box. The attribution compared
all 203,694 object images of base and lane: 8,708 differ, in 151,414 bytes, **all inside `+0x31c..+0x34b`**; no
byte elsewhere differs, and every one of those boxes was all zero before.

**Hook 11 proofs (authored).** The eleven named types in a row at (12350 + 150 k, 12750, 500), hero tile
128,128, 1280x800, draw-all, 40 steps. Worlds 46 and 98 only: the other six have no terrain in the installed
data. Fixed authored contexts, no placement or event claim. Demo names only; nothing is committed.

| World | Draws refused | Particles created / refused | Sprites | Effect requests refused | Frame 0 / 39 pixels changed | Mean RGB difference 0 / 39 |
|---|---|---|---:|---:|---:|---:|
| 46 | 440 -> 0 | 0 / 0 -> 25 / 430 | 0 -> 80 | 0 -> 15 | 198,346 / 739,352 | 2.608 / 7.044 |
| 98 | 440 -> 0 | 0 / 0 -> 25 / 430 | 0 -> 80 | 0 -> 15 | 198,346 / 369,865 | 2.608 / 5.213 |

- Visible after: the red and blue 0x7ef7 glows of types 76 / 77 and the black 0x7f89/16 smoke of type 74.
  Frame 39 of world 46 was inspected next to the base frame.
- The refused particle and effect requests are the ten missing consumer pairs.
- The installed models of these types are plain marker cubes. Whether the singleton's unported create slot
  hides them was not determined; create (11) and move (429) refusals are unchanged by this lane.

## Limits and next

- Handlers 4 and 6 have no live row and no capture. Their end-to-end evidence is the chain family and the
  host test. The mouse segment is one frame old at the tick, like handler 8's camera.
- Hook 11's eight worlds have no capture or placement file; six of them have no terrain in the installed
  data. Its create, move, custom-render and after-render slots (`0x00dbba0c`, `0x00dbba8c`, `0x00dba13d`,
  `0x00dbc1b1`) are not ported; the census probe still counts create and move refusals there.
- Census limits are listed in the finding: an authored 40-draw probe, 83 pairs probed in a sibling world, 9
  rows cut at the walk's step limit, 27 rows with a run-time request id.
- **Next, from the census:**
  1. chain hook 1 `0x009db8b1` (Chaos Castle worlds 18..23, 53, 97; 12 cases, 272 pairs). It needs the state
     byte `0x01cf0467` as an authored input and the bone named `light`;
  2. chain hook 6 `0x00dac0a2` (world 34; types 41 and 84), which reads process counters;
  3. the ten hook 11 consumer pairs and the other 56 missing pairs, for the effects lane;
  4. the 15 pairs refused on every draw (Gray Aida's scrolled meshes, classes 69..72 type 50, Red Smoke Icarus
     type 10, Elbeland 58, Kanturu 40 types 70 / 105 / 110).

## Integration, checkpoints and cleanup

Four merges of main, merge commits only:

| Merge | Main | Batch | Conflicts (both sides kept) |
|---|---|---|---|
| `0d4168cb` | `c255e4dd` | 119: AUDIO-006 #401, MUUN-VISUAL-005 #402 | the registry's appended rows |
| `09014501` | `bb86bbf7` | 120: EFFECTS-033 #403, ITEMS-002AA #404, ACTORS-007 #405, NEXT-GAPS-002 #406 | the registry; the three status files; the rewritten gap list (main's text, this lane's row updated) |
| `4b01da82` | `c49fa188` | 121: UI-WINDOWS-006 #407 | the three status files |
| `f1cda80b` | `708798ae` | 122: HERO-ITEMS-002 #408 | the three status files |

No merge changed `reconstructed/objects`, `native/core/mu_objects*` or `native/world/parts/objects.c`. The
registry parses 261 rows.

Pushed checkpoints: `eef0b982`, `5eaeb445`, `7e724649`, `dfa7859e`, `0d4168cb`, `93ed9f20`, `09014501`,
`4b01da82`, `f1cda80b`, then the delivery commit (this handoff). No lane source the checks compile changes after
`0d4168cb`, except one planted-mistake string in `validate_worlds_inner6.py` (in `93ed9f20`).

All documentation and PR text precede the ready-prs entry. No push follows it. No input is kept for later
lanes: the census is reproducible from the script. Lane-owned scratch, renders, `verify-runs` reports and
build outputs, the worktree and the local branch are removed after queuing. Shared captures, the validator
cache and the remote branch remain. Private input links were never committed. No README, consumer, item,
actor, combat, Muun, UI, audio, installed-app or packaging change.

## Steward validators

Canonical private env, jobs 2, cache on, no mutants. No steward mutants requested. The last column is the
latest commit each row ran at: `0d4168cb` = `0d4168cb150b2096ee9f94d3def06f1df1a67c33`, `09014501` = `09014501f07a6566d03dcc40b8a10a4a1a832f53`, `4b01da82` = `4b01da8268a202e4e2f00914769071a507b2e814`,
`f1cda80b` = `f1cda80bfef7d3c0dd6ac120e9c24befcbc18404`. A row tested
at an earlier commit has no compiled input the later merges changed (`--list-affected-since`).

| Validator | Reported cases | Wall s | Tested |
|---|---:|---:|---|
| `validate_actor_composites` | 1,427 | 10.2 | `f1cda80b` |
| `validate_actor_monsters` | 1,437 | 39.7 | `f1cda80b` |
| `validate_actor_plain` | 21,437 | 216.9 | `f1cda80b` |
| `validate_actor_recipes` | 1,669 | 138.9 | `f1cda80b` |
| `validate_app_polish1` | 752 | 19.9 | `f1cda80b` |
| `validate_app_polish4` | 10,485 | 33.6 | `f1cda80b` |
| `validate_audio_callers` | 5,528 | 6.6 | `f1cda80b` |
| `validate_audio_charsel` | 5,968 | 5.5 | `0d4168cb` |
| `validate_audio_combat` | 19,548 | 29.5 | `09014501` |
| `validate_audio_domains` | 2,544 | 23.6 | `f1cda80b` |
| `validate_audio_items` | 3,000 | 3.8 | `f1cda80b` |
| `validate_audio_kubera` | 1,000 | 1.4 | `f1cda80b` |
| `validate_audio_monsters` | 38,315 | 19.5 | `f1cda80b` |
| `validate_audio_monsters6` | 55,392 | 50.7 | `f1cda80b` |
| `validate_audio_objects` | 4,000 | 7.3 | `f1cda80b` |
| `validate_audio_objects4` | 10,093 | 7.7 | `f1cda80b` |
| `validate_charsel_items` | 8,817 | 8.1 | `f1cda80b` |
| `validate_charsel_world` | 1,200 | 3.1 | `0d4168cb` |
| `validate_fidelity` | 991 | 69.3 | `09014501` |
| `validate_icarus` | 5,240 | 39.3 | `09014501` |
| `validate_icarus_c2` | 8,400 | 21.7 | `f1cda80b` |
| `validate_inventory_fx` | 8,017 | 7.8 | `f1cda80b` |
| `validate_item_callers` | 6,013 | 1.4 | `f1cda80b` |
| `validate_item_textures` | 10,598 | 190.5 | `0d4168cb` |
| `validate_items_ui` | 8,517 | 11.7 | `f1cda80b` |
| `validate_login_world` | 1,200 | 3.7 | `0d4168cb` |
| `validate_meshdraw` | 14,619 | 89.2 | `f1cda80b` |
| `validate_model_edge` | 954 | 150.4 | `f1cda80b` |
| `validate_model_light` | 1,433 | 5.3 | `09014501` |
| `validate_movement` | 6,614 | 58.8 | `f1cda80b` |
| `validate_object_render` | 1,984 | 4.9 | `0d4168cb` |
| `validate_objects` | not reported | 55.1 | `0d4168cb` |
| `validate_path` | 4,719 | 42.1 | `0d4168cb` |
| `validate_render_effects16` | 424 | 5.6 | `f1cda80b` |
| `validate_render_effects17` | 618 | 7.5 | `f1cda80b` |
| `validate_render_effects18` | 540 | 1.3 | `f1cda80b` |
| `validate_render_effects19` | 400 | 1.0 | `f1cda80b` |
| `validate_render_effects24` | 226 | 3.0 | `f1cda80b` |
| `validate_render_effects25` | 202 | 13.4 | `f1cda80b` |
| `validate_render_effects26` | 348 | 10.8 | `f1cda80b` |
| `validate_render_effects28` | 630 | 2.2 | `f1cda80b` |
| `validate_render_effects31` | 66,051 | 296.8 | `f1cda80b` |
| `validate_render_worlds_a` | 9,000 | 14.5 | `09014501` |
| `validate_session_party` | 200 | 0.9 | `f1cda80b` |
| `validate_terrain` | 583,500 | 461.0 | `09014501` |
| `validate_terrain_remaining` | 2,147 | 4.7 | `09014501` |
| `validate_viewport_monsters` | 1,963 | 12.6 | `09014501` |
| `validate_world_fidelity` | 200 | 0.2 | `0d4168cb` |
| `validate_world_light_name` | 304 | 0.9 | `0d4168cb` |
| `validate_world_tile_folder` | 5,700 | 75.6 | `0d4168cb` |
| `validate_worlds_121` | 4,000 | 5.8 | `09014501` |
| `validate_worlds_after` | 13,424 | 15.7 | `09014501` |
| `validate_worlds_after2` | 32,216 | 28.8 | `09014501` |
| `validate_worlds_after3` | 10,212 | 10.9 | `09014501` |
| `validate_worlds_after4` | 9,181 | 16.9 | `09014501` |
| `validate_worlds_after5` | 6,000 | 13.2 | `09014501` |
| `validate_worlds_after6` | 7,300 | 74.2 | `09014501` |
| `validate_worlds_b` | 4,000 | 3.7 | `0d4168cb` |
| `validate_worlds_d` | 2,400 | 4.4 | `09014501` |
| `validate_worlds_e` | 4,840 | 14.9 | `09014501` |
| `validate_worlds_f` | 1,818 | 0.5 | `09014501` |
| `validate_worlds_fog` | 4,044 | 8.2 | `f1cda80b` |
| `validate_worlds_g` | 6,000 | 4.5 | `0d4168cb` |
| `validate_worlds_g2` | 2,657 | 11.2 | `0d4168cb` |
| `validate_worlds_g3` | 4,000 | 5.8 | `09014501` |
| `validate_worlds_h` | 6,000 | 4.0 | `0d4168cb` |
| `validate_worlds_i` | 6,000 | 5.8 | `0d4168cb` |
| `validate_worlds_inner` | 4,000 | 4.3 | `09014501` |
| `validate_worlds_inner2` | 5,000 | 5.1 | `09014501` |
| `validate_worlds_inner3` | 8,000 | 9.5 | `09014501` |
| `validate_worlds_inner4` | 8,000 | 7.5 | `09014501` |
| `validate_worlds_inner5` | 4,000 | 7.5 | `09014501` |
| `validate_worlds_inner6` | 2,000 | 1.7 | `09014501` |
| `validate_worlds_j` | 6,000 | 7.1 | `0d4168cb` |
| `validate_worlds_k` | 6,000 | 9.0 | `0d4168cb` |
| `validate_worlds_karutan` | 3,000 | 4.1 | `09014501` |
| `validate_worlds_n` | 13,000 | 16.1 | `0d4168cb` |
| `validate_worlds_o` | not reported | 10.8 | `0d4168cb` |
| `validate_worlds_p` | 10,000 | 14.3 | `0d4168cb` |
| `validate_worlds_p2` | 6,000 | 8.8 | `0d4168cb` |
| `validate_worlds_pick` | 3,000 | 17.1 | `09014501` |
| `validate_worlds_q` | 11,000 | 14.2 | `0d4168cb` |
| `validate_worlds_q2` | 4,000 | 7.0 | `0d4168cb` |
| `validate_worlds_r` | 12,000 | 11.7 | `0d4168cb` |
| `validate_worlds_r2` | 9,000 | 10.1 | `0d4168cb` |
| `validate_worlds_raklion` | 3,000 | 5.9 | `09014501` |
| `validate_worlds_s` | 11,000 | 8.9 | `0d4168cb` |
| `validate_worlds_s2` | 10,000 | 8.1 | `0d4168cb` |
| `validate_worlds_s3` | 22,000 | 21.9 | `0d4168cb` |
| `validate_worlds_slots` | 18,999 | 18.5 | `09014501` |
| `validate_worlds_slots2` | 33,000 | 36.6 | `09014501` |
| `validate_worlds_slots3` | 36,000 | 37.9 | `09014501` |

Steward validators: validate_actor_composites,validate_actor_monsters,validate_actor_plain,validate_actor_recipes,validate_app_polish1,validate_app_polish4,validate_audio_callers,validate_audio_charsel,validate_audio_combat,validate_audio_domains,validate_audio_items,validate_audio_kubera,validate_audio_monsters,validate_audio_monsters6,validate_audio_objects,validate_audio_objects4,validate_charsel_items,validate_charsel_world,validate_fidelity,validate_icarus,validate_icarus_c2,validate_inventory_fx,validate_item_callers,validate_item_textures,validate_items_ui,validate_login_world,validate_meshdraw,validate_model_edge,validate_model_light,validate_movement,validate_object_render,validate_objects,validate_path,validate_render_effects16,validate_render_effects17,validate_render_effects18,validate_render_effects19,validate_render_effects24,validate_render_effects25,validate_render_effects26,validate_render_effects28,validate_render_effects31,validate_render_worlds_a,validate_session_party,validate_terrain,validate_terrain_remaining,validate_viewport_monsters,validate_world_fidelity,validate_world_light_name,validate_world_tile_folder,validate_worlds_121,validate_worlds_after,validate_worlds_after2,validate_worlds_after3,validate_worlds_after4,validate_worlds_after5,validate_worlds_after6,validate_worlds_b,validate_worlds_d,validate_worlds_e,validate_worlds_f,validate_worlds_fog,validate_worlds_g,validate_worlds_g2,validate_worlds_g3,validate_worlds_h,validate_worlds_i,validate_worlds_inner,validate_worlds_inner2,validate_worlds_inner3,validate_worlds_inner4,validate_worlds_inner5,validate_worlds_inner6,validate_worlds_j,validate_worlds_k,validate_worlds_karutan,validate_worlds_n,validate_worlds_o,validate_worlds_p,validate_worlds_p2,validate_worlds_pick,validate_worlds_q,validate_worlds_q2,validate_worlds_r,validate_worlds_r2,validate_worlds_raklion,validate_worlds_s,validate_worlds_s2,validate_worlds_s3,validate_worlds_slots,validate_worlds_slots2,validate_worlds_slots3.

Env: source `~/Documents/MTM/mu-mac-tools/native/private-env.sh` from the repo root. All original inputs and
Native Data remain read-only.
