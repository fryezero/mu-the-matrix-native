# RENDER-EFFECTS-022

Offline/static port of the counter-gated mace particles and the rank-5 owner block in the world.
Branch `codex/render-effects-022`, base main `a55200e2` (#350); merged main `1e2a927a` (#351, CLOAK-003)
at `1968c78e` before readiness. Research [part 29](../research/client-render-items.md#part-29-counter-gated-mace-particles-and-rank-5-world-owners-render-effects-022). No live client, app install, launcher,
network, server-state, protection-module work or memory writes. No full gate in the lane.

## Scope and addresses

| Request | CreateParticle | MoveParticles | RenderParticles | Native result |
|---|---|---|---|---|
| Mace `0x0f1f`: `0x810a/0x25`, OBJECT owner, argument 8 = rand % 3 | `0x015b51f0` | `0x0161d801` | `0x0159f880` | Native particle, follows the selected current OBJECT point |
| Mace `0x0f20`: `0x855d/1` twice | `0x01610e81` | `0x01689aa8` | `0x015aa71c` | Native red sparks |
| Mace `0x0f20`: `0x84d1/1` | `0x0160c861` | `0x016855a9` | `0x015a743f` | Native red smoke |
| Rank-5 owner block | RenderPartObjectBody `0x01747d6d`, `0x0174888d`, `0x01749294`, `0x01749cc5` | Existing particle kinds | Existing particles/sprites | World players, hero and player-model actor callers |

The three kinds are in `reconstructed/particles/item_counter_kinds.inc`. The native counter was already
supplied by #350; its phase still starts at world-runtime creation.

`0x810a/0x25` needs more than the owner's position. Its render reads OBJECT `+0x1f4 + 12*arg8`, adds the
record's start vector and writes the particle position. The item-program generator now exports the nine
point-word stores as op 50 / `MU_RC_OWNER_POINT` through the existing emit callback. This preserves the host
and effect-record ABI. These state writes do not count as effects or consume rand. Item owner slots retain the
points between draws, and `mu_world_particles_create_args` preserves argument 8. Generation checks prevent
an old particle from following a reused slot. The same general store rule exports `0x0f2a`'s first point;
its other particle kinds are outside this lane.

The random vector of `0x855d/1` is `0x00d01fc6(out, 0, 1, 180, 0, 360, 0)`: min >= max fixes radius at 1,
without a radius rand. Theta, phi and speed follow the client order and binary32 intermediates.

The rank-5 owner adapter uses the existing `player_bones`, owner angle and part-model scale/origin. The
existing rank-5 implementation creates four `0x84e2/0` particles, a `0x7fdd` sprite and a `0x83de/4` particle,
and adds the level-9 overlay passes at the client's point. `world_rt_part_owner` now admits rank-5 types as
well as the 43 owner-program types. No rank-5 arithmetic or mesh recipe changed.

## Routed and refused census

Lorencia 128,124; offline native soft renderer, 640x480. Before = main `a55200e2` once per scene. After =
`fc5abc1c` compiled code. Fixtures use maces `0x0f1f` and `0x0f20`, and rank-5 armour `0x1c26` / `0x1c25` +9.

| Scene | Before: created / refused | After: created / refused |
|---|---|---|
| Both maces, 61 steps, render every 10, clock default | 189 / 6 | 195 / 0 |
| Same, clock starts at 123456 ms | 189 / 6 | 195 / 0 |
| Both maces, 16 consecutive rendered frames | 432 / 18 | 450 / 0 |
| Rank-5 players, 61 steps, render every 10, clock default | no owner block ran | 84 owner effects / 0 |
| Same, clock starts at 123456 ms | no owner block ran | 84 / 0 |

The every-10-frame sample never reaches counter % 5 == 0. The additional consecutive-frame sample does:
its counter 1..16 requests five `0x810a/0x25`, ten `0x855d/1` and three `0x84d1/1`. All 18 are created and drawn
at the last frame, versus none before. The pool's unsupported count falls 16 to 0; the program refusal count
falls 18 to 0, because the old adapter refused two owned requests for argument 8 before they reached the pool.
Sprites created remain 432; rand calls 114 to 170, including the new create branches. The new `0x855d` texture
also makes the mace's existing `0x855d` bone sprites visible, including frames before a particle gate opens.
The last frame's drawn sprite count rises 8 to 10. Two other bone-sprite textures still have no world slot:
`0x7f7a` has four requests per draw from `0x0f1f`, and `0x80ba` has thirteen from `0x0f20`. Over these 16 frames
those 64 + 208 requests remain counted-only. They are outside the three particle pairs.

Rank-5 players create 70 particles and 14 sprites, with 22 particles drawn at the last frame. Private installed
tests also exercise the hero with `armor=Item/ArmorMale161_elf.bmd@8:320:9`. Player-model actors are wired but
not rendered in this lane.

These zero refusal counts cover the fixture's requests, not every client item. In particular `0x0f2a`'s separate
kinds are still out of scope. Part 23's earlier kinds and #350's wing joints remain admitted.

## Renders and byte identity

Local before | after | 4x-difference crops were opened and inspected. The mace crop shows the red sparks/smoke
and the owned spark at the other mace; the rank-5 crop shows the blue owner glow. Crops contain demo labels or
no labels. A private hero label found in the first full frames was removed with those frames; the consecutive
proof uses `--hero-name DemoKnight`. No PNG is committed or kept after cleanup.

The consecutive sample's frame 15 changes 1,491 pixels, bounding box (274,114)-(368,259). Rank-5 frame 30 changes
1,358 pixels at the default clock, within (301,104)-(387,208); at clock 123456 it changes 1,349 pixels. The other
saved frames of both fixtures change only near their wearers' weapons/armour.

One default-draw sweep, no draw_all, no players file, 640x400:
- October 22 tour: 28/28 PNGs, 14/14 OBJECT dumps and 14/14 light dumps byte-identical.
- DATA-ACQ-002: 64/64 PNGs, 32/32 OBJECT dumps and 32/32 light dumps byte-identical.
- All 46 reports equal after normalizing output paths and removing the two expected new bitmap-presence slots
  from the after report. No other report field changes. None of these views wears the affected items.

Combined default sweeps plus the initial fixture renders: before 70.0 s, after 62.1 s. The additional consecutive
fixture is 1.36 / 1.18 s; its fresh detached baseline build is 6.93 s and the baseline worktree is already removed.

## Checks

Canonical private environment sourced from the repository root. Every heavy job uses `nice -n 10`, builds
use `-j4`, runners use two jobs. A load >14 pause was observed before continuing.

| Check | Result | Wall |
|---|---|---:|
| Lane production `nice -n 10 make -j4`, before main merge | pass | 6.92 s |
| Explicit mu-world/mu-walk render build | pass | 5.32 s |
| `validate_render_effects22 --cases 1000`, final sampler: all three argument-8 indices per kind | 10,002 comparisons, 0 mismatches: create 3,000, move 3,000, render 3,000, points 1,000, bitmap registrations 2 | 19.76 s |
| Registry `validate_render_effects22` with mutants, final sampler | 202 comparisons, 0 mismatches, 19/19 compiled mutants caught; none stopped; point-store mutant caught in 12/20 cases | 20.37 s |
| Portable `run_test_suites.py --affected origin/main`, integration off, two jobs | 148 selected work items, 9 reported suites, 1,607 tests: 1,346 passed, 261 skipped, 0 failures/errors | 278.9 s test wall; 327.19 s command including selection |
| Private native/tests from root with private-env.sh, 8d reduced plus 6b | 37 tests, 0 failures/skips | 27.65 s |
| Final private merged `test_render_effects22`, `test_native_armour_cloak`, `test_native_item_cloak` | 25 tests, 0 failures/skips; includes consecutive 450/0 request and 18 created/drawn assertions | 24.42 s |
| Checkpoint repository audit | 2,108 staged files, 0 rejected | 17.87 s |

8d reduced: selector chose 140 native/tests modules, above the 40-item cap (148 total work items). Changed/added native modules are `test_native_particles` and
`test_render_effects22`. The private run includes both, plus 6b consumers `test_native_renderchar`,
`test_native_world_predraw.FlagHeader`, `test_native_world_predraw.WorldPreDraw`, `test_render_effects20.Native`
and `test_render_effects16.Native`. The bitmap count assertion is updated 77 to 79. Grep also checked every
`MU_WORLD_PT_BITMAPS`, `mu_world_item_owner`, `mu_world_particles_create_owned` and owner-effect-kind consumer.
The portable selection covers the remaining native hosts. All tests/tools run from the repository root.

The initial op-50 mutant survived because the directed point fixture inherited `records=False` from a generic
probe state. No store ran. The fixed fixture supplies names, complete bone domains, alternate owner matrices
and hidden frames; the mutant is now caught. An earlier spherical-vector mismatch also caught a mistaken
random radius before the helper's fixed-radius branch was ported. Neither failed iteration is counted as a pass.

### Affected validator batch

The initial batch passed **75/75 rows**, **1,114,073 comparisons**, zero failures/errors/skips, without mutants; **3,067.64 s** wall
including selection. Production compiled inputs are at `fc5abc1c98bab5f972d5407828e67379f88f768e`.
The final new-row render sampler also cycles argument 8 over all three indices per kind; it was loaded by
the last row of this batch and is checked again below. The report records the runner’s starting commit.

| Validator | Comparisons | Wall |
|---|---:|---:|
| `validate_app_polish1` | 752 | 17.9 s |
| `validate_app_polish2` | 1,028 | 3.0 s |
| `validate_app_polish4` | 10,485 | 27.9 s |
| `validate_audio_callers` | 5,528 | 5.1 s |
| `validate_audio_domains` | 2,544 | 25.1 s |
| `validate_audio_items` | 3,000 | 4.0 s |
| `validate_fidelity` | 991 | 50.3 s |
| `validate_icarus_c2` | 8,400 | 14.4 s |
| `validate_inventory_fx` | 8,017 | 6.5 s |
| `validate_item_callers` | 6,013 | 1.3 s |
| `validate_item_carry` | 114,388 | 499.7 s |
| `validate_item_chains` | 35,406 | 286.3 s |
| `validate_item_cloak` | 5,694 | 127.9 s |
| `validate_item_clusters` | 74,292 | 288.8 s |
| `validate_item_continuation` | 25,772 | 893.4 s |
| `validate_item_coverage` | 31,724 | 193.7 s |
| `validate_item_derived` | 36,252 | 185.4 s |
| `validate_item_effects` | 1,500 | 0.8 s |
| `validate_item_expansion` | 52,172 | 235.8 s |
| `validate_item_gear` | 25,256 | 147.6 s |
| `validate_item_hiddenmesh` | 116,281 | 409.6 s |
| `validate_item_next` | 14,992 | 186.8 s |
| `validate_item_ownerfx` | 14,964 | 114.4 s |
| `validate_item_predraw` | 32,372 | 226.0 s |
| `validate_item_product` | 2,874 | 47.2 s |
| `validate_item_quality` | 28,080 | 138.7 s |
| `validate_item_ranked` | 17,736 | 853.0 s |
| `validate_item_scalars` | 26,274 | 197.0 s |
| `validate_item_types` | 135,176 | 28.1 s |
| `validate_item_wings_next` | 33,622 | 205.1 s |
| `validate_meshdraw` | 14,619 | 48.6 s |
| `validate_model_edge` | 954 | 102.2 s |
| `validate_movement` | 6,614 | 46.8 s |
| `validate_particles` | 407 | 0.8 s |
| `validate_render_effects` | 660 | 1.0 s |
| `validate_render_effects10` | 154 | 0.4 s |
| `validate_render_effects11` | 176 | 0.3 s |
| `validate_render_effects12` | 64 | 0.5 s |
| `validate_render_effects13` | 180 | 0.4 s |
| `validate_render_effects14` | 660 | 0.9 s |
| `validate_render_effects15` | 509 | 0.6 s |
| `validate_render_effects16` | 424 | 3.0 s |
| `validate_render_effects17` | 618 | 6.2 s |
| `validate_render_effects18` | 540 | 1.3 s |
| `validate_render_effects19` | 400 | 1.1 s |
| `validate_render_effects20` | 148 | 0.3 s |
| `validate_render_effects21` | 267 | 0.4 s |
| `validate_render_effects22` | 202 | 4.4 s |
| `validate_render_effects3` | 720 | 1.0 s |
| `validate_render_effects4` | 1,920 | 5.9 s |
| `validate_render_effects5` | 1,190 | 3.9 s |
| `validate_render_effects6` | 1,000 | 1.3 s |
| `validate_render_effects7` | 596 | 1.4 s |
| `validate_render_effects9` | 304 | 0.9 s |
| `validate_render_worlds_a` | 9,000 | 9.2 s |
| `validate_renderchar` | 1,706 | 40.4 s |
| `validate_world_particle_consumers` | 900 | 1.6 s |
| `validate_worlds_121` | 4,000 | 3.3 s |
| `validate_worlds_after` | 13,424 | 17.6 s |
| `validate_worlds_after2` | 32,216 | 42.5 s |
| `validate_worlds_after3` | 10,212 | 12.4 s |
| `validate_worlds_after4` | 9,181 | 14.0 s |
| `validate_worlds_after5` | 6,000 | 7.5 s |
| `validate_worlds_after6` | 7,300 | 46.7 s |
| `validate_worlds_e` | 4,840 | 14.8 s |
| `validate_worlds_fog` | 4,044 | 4.5 s |
| `validate_worlds_g3` | 4,000 | 6.5 s |
| `validate_worlds_k` | 6,000 | 5.0 s |
| `validate_worlds_karutan` | 3,000 | 2.2 s |
| `validate_worlds_l` | 1,260 | 1.7 s |
| `validate_worlds_m` | 1,080 | 1.6 s |
| `validate_worlds_raklion` | 3,000 | 2.6 s |
| `validate_worlds_slots` | 18,999 | 11.4 s |
| `validate_worlds_slots2` | 33,000 | 19.9 s |
| `validate_worlds_slots3` | 36,000 | 20.1 s |

The nine rows that build changed libraries but use no changed symbol are pruned: `validate_audio_charsel`,
`validate_audio_combat`, `validate_model_light`, `validate_path`, `validate_session_party`, `validate_terrain`,
`validate_terrain_remaining`, `validate_viewport_monsters`, `validate_worlds_f`. The movement row is retained
by its symbol fallback. Existing mutant targets are unchanged; only the new row needs mutants.

Steward validators: validate_item_ranked,validate_item_continuation,validate_item_expansion,validate_item_effects,validate_item_clusters,validate_item_types,validate_fidelity,validate_meshdraw,validate_model_edge,validate_movement,validate_particles,validate_renderchar,validate_render_worlds_a,validate_icarus_c2,validate_worlds_e,validate_audio_callers,validate_item_gear,validate_item_next,validate_render_effects,validate_render_effects3,validate_render_effects4,validate_render_effects5,validate_render_effects6,validate_render_effects7,validate_render_effects9,validate_render_effects10,validate_render_effects11,validate_render_effects12,validate_world_particle_consumers,validate_audio_domains,validate_worlds_k,validate_audio_items,validate_worlds_l,validate_item_coverage,validate_item_wings_next,validate_item_scalars,validate_item_chains,validate_worlds_m,validate_worlds_after,validate_worlds_g3,validate_worlds_after2,validate_worlds_after3,validate_worlds_after4,validate_worlds_after5,validate_worlds_after6,validate_item_carry,validate_item_quality,validate_item_product,validate_item_derived,validate_item_ownerfx,validate_item_predraw,validate_item_hiddenmesh,validate_app_polish1,validate_app_polish2,validate_app_polish4,validate_render_effects13,validate_render_effects14,validate_worlds_slots,validate_worlds_slots2,validate_worlds_slots3,validate_worlds_121,validate_worlds_raklion,validate_worlds_karutan,validate_render_effects15,validate_render_effects16,validate_worlds_fog,validate_render_effects17,validate_item_callers,validate_inventory_fx,validate_render_effects18,validate_render_effects19,validate_render_effects20,validate_render_effects21,validate_item_cloak,validate_armour_cloak,validate_render_effects22

### Main merge and final selection

After merging CLOAK-003, `nice -n 10 make -j4` passed in **9.69 s**. The `--list-affected-since fc5abc1c`
selector retained 15 rows (including the changed new-row sampler), 58.96 s selection. All **15/15 passed**, zero
failures/errors/skips, **56,486 comparisons**, without mutants, **147.68 s** wall at `1968c78e`:

| Validator | Comparisons | Wall |
|---|---:|---:|
| `validate_armour_cloak` | 4,448 | 39.6 s |
| `validate_audio_callers` | 5,528 | 6.0 s |
| `validate_audio_domains` | 2,544 | 23.2 s |
| `validate_audio_items` | 3,000 | 4.7 s |
| `validate_icarus_c2` | 8,400 | 22.6 s |
| `validate_inventory_fx` | 8,017 | 7.5 s |
| `validate_item_callers` | 6,013 | 1.4 s |
| `validate_item_cloak` | 5,694 | 117.8 s |
| `validate_movement` | 6,614 | 46.2 s |
| `validate_render_effects16` | 424 | 3.3 s |
| `validate_render_effects17` | 618 | 8.1 s |
| `validate_render_effects18` | 540 | 1.4 s |
| `validate_render_effects19` | 400 | 1.1 s |
| `validate_render_effects22` | 202 | 4.2 s |
| `validate_worlds_fog` | 4,044 | 7.7 s |

The post-build `--list-affected origin/main` selection is **76 rows** (77.11 s): the initial 75 plus
`validate_armour_cloak`. All are covered above. The movement fallback remains; the same nine rows are pruned.
The main merge changes cloth inputs, not the new particle or rank-5 production code. Default byte identity was
measured at `fc5abc1c`; CLOAK-003's own default 92-frame byte-identity result is recorded in its handoff. A second
default sweep is not claimed here.

At `1968c78e`, the final new-row proof passes **10,002 comparisons** (19.76 s), and its registry row passes
**202 comparisons, 19/19 mutants caught**, zero stopped (20.37 s). The point-store mutant is caught in 12/20
cases. All three owned argument-8 indices are sampled independently of the kind selection. The merged private
modules (`test_render_effects22`, `test_native_armour_cloak`, `test_native_item_cloak`) pass **25 tests**, zero
skips/failures, **24.42 s**. This includes both the new consecutive particle assertion and the merged cloth
hero/player cadence. Private 8d stays reduced; these are the changed native modules and their shared-struct
consumer, not all private native/tests.

Merged portable `MU_RECOVERY_INTEGRATION=0 MU_GATE_JOBS=2 run_test_suites.py --affected-since fc5abc1c`
passes **144 selected work items**, **7 reported suites**, **1,367 tests: 1,149 passed, 218 skipped, zero
failures/errors**. Wall **283.3 s** for tests, **334.80 s** including selection. Together with the initial
portable batch, this covers the original particle changes and the cloth inputs brought by main. The zero-test
`test_session_support.py` helper module is a selected work item, not a failure.

Final staged repository audit: **2,111 files, zero rejected, 19.34 s**. `git diff --check` is clean.
Manual diff review covers the particle admission/lifecycle/render hooks, point-state generator/interpreter,
owner-generation adapter, bitmap consumers, world callers and merged docs; no delegate was used.


## Limits and next

- Native renders are before/after comparisons, not original-client pixel comparisons. Particle record arithmetic,
  render calls and OBJECT point stores are compared with the pinned original instructions.
- Owner points follow the native item pose. This does not prove the native pose equals the original client's pose.
  Pre-draw requests on unknown/out-of-domain bones remain refused; rank-5 requires bones 35/26. An absent or stale item owner ends the owned spark.
- Argument 8 is hosted for the actual mace domain 0..2. Arbitrary original OBJECT memory is not hosted.
- `mu-render character` still has no item OBJECT registry and refuses the OBJECT-owned spark; its unowned kinds
  now exist. Player-model actors use the shared hook but have no installed render fixture in this lane.
- Add world bitmap slots for the maces' existing `0x7f7a` and `0x80ba` bone sprites, with their original loader mappings.
- `0x0f2a`'s additional requests (`0x85bc/5`, `0x83b8/8`, `0x85fc/1`, and its register-selected particle) remain
  separate work. Do not read a zero refusal count in the two-mace fixture as a whole-client census.
- The installed Native Preview and both Wine apps are untouched. The steward owns merging and the full gate.

## Cleanup

Remove this lane's scratch, render and build outputs after the final push and ready-prs line. No new private input
needs to be retained. Committed checks and reviewed render measurements are the handoff evidence; raw-frame hashes remain local until cleanup.
