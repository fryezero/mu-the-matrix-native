# RENDER-WORLDS-PICK-001

Branch `claude/render-worlds-pick-001`, from main `c5b9d5ca` (#400, batch 118), integrated through main
`c255e4dd` (#402, batch 119). PR-ready. Implementation and checks by Claude Fable 5.2, without subagents.
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

| Check | Result | Wall s |
|---|---|---:|
| Root build, merged tree | Pass | 17.4 |
| `validate_worlds_pick` with mutants (once) | 3,000 cases (box, segment, pick) equal, 0 stops; 23/23 mutants, lowest 23 | 343.4 |
| `validate_worlds_inner6` with mutants (once) | 2,000 cases (chain11, chain11_focus) equal, 0 stops; 37/37 mutants, lowest 6; world test: exactly 45..50, 98, 99 | 284.3 |
| Affected validators, no mutants, cached | 92/92 rows pass, 1,316,455 reported cases | 1,579.9 |
| Affected portable suites | 183 work items selected, 182 run: 1,809 tests, 1,454 passed / 355 expected skips, 0 failures, 0 errors | 431.5 |
| Private modules (8d reduced) | 14 tests, 0 skips: `test_native_worlds_pick`, `test_native_worlds_inner`, `test_native_anim`, `test_worlds_inner4`, `test_worlds_inner5` | 4.8 |
| Census walk and probes | 62 routines, 730 rows; one probe per (case, object folder, type) | 644.8 |
| Base sweep (main `c255e4dd`) | 46 views, no failures | 65.6 |
| Lane sweep (merged) | 46 views, no failures | 177.9 |
| Base re-render for the dump attribution | 46 views, no failures | 113.1 |
| Hook 11 proofs, worlds 46 and 98, both binaries | 4 runs | 6.1 |
| Repository audit | 2,385 staged files, 0 rejected | 16.1 |
| Documentation consumers, after the last doc edit | 36 tests, 35 passed / 1 expected skip | 8.2 |

- **Mutants ran once each**, for the two validators this lane created. `validate_worlds_pick`'s run is at
  `5eaeb445`; its compiled inputs (`object_pick.c`, `action_registry.c`) did not change afterwards.
  `validate_worlds_inner6`'s run is on the merged tree.
- Before those counted runs, three planted mistakes were repaired: two `validate_worlds_pick` mutants and one
  `validate_worlds_inner6` mutant left a parameter unused and did not compile under `-Werror`, and one
  `validate_worlds_pick` mutant (`e >= 1` for `e > 0`) is equivalent on integer-valued boxes and was replaced.
  A first `validate_worlds_inner6` runner call stopped at that compile error after four mutants; the counted
  run is the complete second one.
- The portable selection excludes only `native/tests/test_native_app.py` (it builds and signs a bundle).
- **8d reduced:** the private native selection is far above the 40-item cap (`mu_objects.h` and the native
  Makefile select most of `native/tests`), so the modules this lane changed or added ran privately, plus the
  two INNER tests that pin the factory inventory (48 classes, 57 registrations, neither 46 nor 98).
- 6b: `mu_objects_runtime` gained fields at its end only. No test or script mirrors its layout; the one
  existing consumer of its last field (`worlds_s3_host.c`, `imperial_frame`) is in the portable run. The
  ctypes mirror of `mu_anim_inputs` (`validate_worlds_after5/6`) is unchanged: that struct was not touched.
- The first census run and a first chain of checks ran on the pre-merge tree; main moved to batch 119 while
  they ran, so they were stopped and everything in the table was run again on the merged tree.

## Renders and fidelity

Both binaries were built with `make -C native -j4 world` in this lane's own tree: the base from a detached
checkout of main `c255e4dd`, the lane from the merged branch.

- Base, main `c255e4dd`: `b6549bcdb452b518ae7026fdb912fb005a8a7788e90eb889daf16f6f403cb7a3`.
- Lane, merged `0d4168cb`: `436244f5c28a5a2e4144a2ced40edb6adf6b01dce6a9904208ab98eceef94967`.

**Default identity sweep.** The 14-view October tour and the 32-view acquisition tour, 640x400, 25 steps
sampled at 0 and 24, without draw-all.

| Compared | Result |
|---|---|
| PNG frames | 92/92 identical |
| Normalized reports | 46/46 identical |
| Light dumps | 46/46 identical |
| OBJECT dumps | 0/46 identical, by intent |

No view changes. Every OBJECT dump changes because drawn objects now carry their box. The attribution
re-rendered the base and compared all 203,694 object images: 8,708 differ, in 151,414 bytes, **all inside
`+0x31c..+0x34b`**; no byte elsewhere differs, and every one of those boxes was all zero before.

**Hook 11 proofs (authored).** The eleven named types in a row at (12350 + 150 k, 12750, 500), hero tile
128,128, 1280x800, draw-all, 40 steps. Worlds 46 and 98 only: the other six have no terrain in the installed
data. Fixed authored contexts, no placement or event claim. Demo names only; nothing is committed.

| World | Draws refused | Particles created / refused | Sprites | Effect requests refused | Frame 0 / 39 pixels changed | Mean RGB difference 0 / 39 |
|---|---|---|---:|---:|---:|---:|
| 46 | 440 -> 0 | 0 / 0 -> 25 / 430 | 0 -> 80 | 0 -> 15 | 198,346 / 739,352 | 2.608 / 7.044 |
| 98 | 440 -> 0 | 0 / 0 -> 25 / 430 | 0 -> 80 | 0 -> 15 | 198,346 / 369,865 | 2.608 / 5.213 |

- Visible after: the red and blue 0x7ef7 glows of types 76 / 77 and the black 0x7f89/16 smoke of type 74.
  Frame 39 of world 46 was inspected next to the base frame.
- The 430 refused particle requests and 15 refused effect requests are the ten missing consumer pairs.
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

Main `c255e4dd` (batch 119: AUDIO-006 #401, MUUN-VISUAL-005 #402) is merged at `0d4168cb`. The one conflict,
the registry's appended rows, keeps both sides (255 rows parse). The merge brought no change under
`reconstructed/objects`, `native/core/mu_objects*` or `native/world/parts/objects.c`.

Pushed checkpoints: `eef0b982`, `5eaeb445`, `7e724649`, `dfa7859e`, the merge `0d4168cb`, then delivery
commits (docs, the census CSV on the merged binary, one mutant string in `validate_worlds_inner6.py`). No lane
source the checks compile changes after `0d4168cb`.

All documentation and PR text precede the ready-prs entry. No push follows it. No input is kept for later
lanes: the census is reproducible from the script. Lane-owned scratch, renders, `verify-runs` reports and
build outputs, the worktree and the local branch are removed after queuing. Shared captures, the validator
cache and the remote branch remain. Private input links were never committed. No README, consumer, item,
actor, combat, Muun, UI, audio, installed-app or packaging change.

## Steward validators

Canonical private env, jobs 2, cache on, no mutants; all 92 rows at
`0d4168cb` = `0d4168cb150b2096ee9f94d3def06f1df1a67c33`. No steward mutants requested.

| Validator | Reported cases | Wall s |
|---|---:|---:|
| `validate_actor_composites` | 1,427 | 11.1 |
| `validate_actor_monsters` | 1,437 | 53.1 |
| `validate_actor_plain` | 21,437 | 185.6 |
| `validate_actor_recipes` | 1,669 | 161.1 |
| `validate_app_polish1` | 752 | 18.7 |
| `validate_app_polish4` | 10,485 | 35.4 |
| `validate_audio_callers` | 5,528 | 6.7 |
| `validate_audio_charsel` | 5,968 | 5.5 |
| `validate_audio_combat` | 19,548 | 37.8 |
| `validate_audio_domains` | 2,544 | 36.5 |
| `validate_audio_items` | 3,000 | 6.3 |
| `validate_audio_kubera` | 1,000 | 1.0 |
| `validate_audio_monsters` | 38,315 | 13.2 |
| `validate_audio_monsters6` | 55,392 | 52.3 |
| `validate_audio_objects` | 4,000 | 4.2 |
| `validate_audio_objects4` | 10,093 | 4.8 |
| `validate_charsel_items` | 8,817 | 13.2 |
| `validate_charsel_world` | 1,200 | 3.1 |
| `validate_fidelity` | 991 | 80.4 |
| `validate_icarus` | 5,240 | 45.9 |
| `validate_icarus_c2` | 8,400 | 26.7 |
| `validate_inventory_fx` | 8,017 | 11.7 |
| `validate_item_callers` | 6,013 | 1.4 |
| `validate_item_textures` | 10,598 | 190.5 |
| `validate_items_ui` | 8,517 | 18.3 |
| `validate_login_world` | 1,200 | 3.7 |
| `validate_meshdraw` | 14,619 | 117.1 |
| `validate_model_edge` | 954 | 184.1 |
| `validate_model_light` | 1,433 | 7.4 |
| `validate_movement` | 6,614 | 84.7 |
| `validate_object_render` | 1,984 | 4.9 |
| `validate_objects` | not reported | 55.1 |
| `validate_path` | 4,719 | 42.1 |
| `validate_render_effects16` | 424 | 4.6 |
| `validate_render_effects17` | 618 | 9.9 |
| `validate_render_effects18` | 540 | 1.4 |
| `validate_render_effects19` | 400 | 1.1 |
| `validate_render_effects24` | 226 | 3.5 |
| `validate_render_effects25` | 202 | 14.0 |
| `validate_render_effects26` | 348 | 14.9 |
| `validate_render_effects28` | 630 | 3.4 |
| `validate_render_effects31` | 66,051 | 213.7 |
| `validate_render_worlds_a` | 9,000 | 19.7 |
| `validate_session_party` | 200 | 1.2 |
| `validate_terrain` | 583,500 | 600.0 |
| `validate_terrain_remaining` | 2,147 | 5.4 |
| `validate_viewport_monsters` | 1,963 | 13.6 |
| `validate_world_fidelity` | 200 | 0.2 |
| `validate_world_light_name` | 304 | 0.9 |
| `validate_world_tile_folder` | 5,700 | 75.6 |
| `validate_worlds_121` | 4,000 | 5.8 |
| `validate_worlds_after` | 13,424 | 14.5 |
| `validate_worlds_after2` | 32,216 | 22.1 |
| `validate_worlds_after3` | 10,212 | 7.1 |
| `validate_worlds_after4` | 9,181 | 10.8 |
| `validate_worlds_after5` | 6,000 | 7.8 |
| `validate_worlds_after6` | 7,300 | 59.3 |
| `validate_worlds_b` | 4,000 | 3.7 |
| `validate_worlds_d` | 2,400 | 7.4 |
| `validate_worlds_e` | 4,840 | 24.7 |
| `validate_worlds_f` | 1,818 | 0.7 |
| `validate_worlds_fog` | 4,044 | 8.9 |
| `validate_worlds_g` | 6,000 | 4.5 |
| `validate_worlds_g2` | 2,657 | 11.2 |
| `validate_worlds_g3` | 4,000 | 4.0 |
| `validate_worlds_h` | 6,000 | 4.0 |
| `validate_worlds_i` | 6,000 | 5.8 |
| `validate_worlds_inner` | 4,000 | 5.0 |
| `validate_worlds_inner2` | 5,000 | 9.2 |
| `validate_worlds_inner3` | 8,000 | 11.7 |
| `validate_worlds_inner4` | 8,000 | 6.0 |
| `validate_worlds_inner5` | 4,000 | 5.4 |
| `validate_worlds_inner6` | 2,000 | 1.4 |
| `validate_worlds_j` | 6,000 | 7.1 |
| `validate_worlds_k` | 6,000 | 9.0 |
| `validate_worlds_karutan` | 3,000 | 4.6 |
| `validate_worlds_n` | 13,000 | 16.1 |
| `validate_worlds_o` | not reported | 10.8 |
| `validate_worlds_p` | 10,000 | 14.3 |
| `validate_worlds_p2` | 6,000 | 8.8 |
| `validate_worlds_pick` | 3,000 | 14.6 |
| `validate_worlds_q` | 11,000 | 14.2 |
| `validate_worlds_q2` | 4,000 | 7.0 |
| `validate_worlds_r` | 12,000 | 11.7 |
| `validate_worlds_r2` | 9,000 | 10.1 |
| `validate_worlds_raklion` | 3,000 | 4.0 |
| `validate_worlds_s` | 11,000 | 8.9 |
| `validate_worlds_s2` | 10,000 | 8.1 |
| `validate_worlds_s3` | 22,000 | 21.9 |
| `validate_worlds_slots` | 18,999 | 21.1 |
| `validate_worlds_slots2` | 33,000 | 39.8 |
| `validate_worlds_slots3` | 36,000 | 41.5 |

Steward validators: validate_actor_composites,validate_actor_monsters,validate_actor_plain,validate_actor_recipes,validate_app_polish1,validate_app_polish4,validate_audio_callers,validate_audio_charsel,validate_audio_combat,validate_audio_domains,validate_audio_items,validate_audio_kubera,validate_audio_monsters,validate_audio_monsters6,validate_audio_objects,validate_audio_objects4,validate_charsel_items,validate_charsel_world,validate_fidelity,validate_icarus,validate_icarus_c2,validate_inventory_fx,validate_item_callers,validate_item_textures,validate_items_ui,validate_login_world,validate_meshdraw,validate_model_edge,validate_model_light,validate_movement,validate_object_render,validate_objects,validate_path,validate_render_effects16,validate_render_effects17,validate_render_effects18,validate_render_effects19,validate_render_effects24,validate_render_effects25,validate_render_effects26,validate_render_effects28,validate_render_effects31,validate_render_worlds_a,validate_session_party,validate_terrain,validate_terrain_remaining,validate_viewport_monsters,validate_world_fidelity,validate_world_light_name,validate_world_tile_folder,validate_worlds_121,validate_worlds_after,validate_worlds_after2,validate_worlds_after3,validate_worlds_after4,validate_worlds_after5,validate_worlds_after6,validate_worlds_b,validate_worlds_d,validate_worlds_e,validate_worlds_f,validate_worlds_fog,validate_worlds_g,validate_worlds_g2,validate_worlds_g3,validate_worlds_h,validate_worlds_i,validate_worlds_inner,validate_worlds_inner2,validate_worlds_inner3,validate_worlds_inner4,validate_worlds_inner5,validate_worlds_inner6,validate_worlds_j,validate_worlds_k,validate_worlds_karutan,validate_worlds_n,validate_worlds_o,validate_worlds_p,validate_worlds_p2,validate_worlds_pick,validate_worlds_q,validate_worlds_q2,validate_worlds_r,validate_worlds_r2,validate_worlds_raklion,validate_worlds_s,validate_worlds_s2,validate_worlds_s3,validate_worlds_slots,validate_worlds_slots2,validate_worlds_slots3.

Env: source `~/Documents/MTM/mu-mac-tools/native/private-env.sh` from the repo root. All original inputs and
Native Data remain read-only.
