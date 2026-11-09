# RENDER-EFFECTS-022

Offline/static port of the counter-gated mace particles and the rank-5 owner block in the world.
Branch `codex/render-effects-022`, base main `a55200e2` (#350). No live client, app install, launcher,
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
Sprites remain 432; rand calls 114 to 170, including the new create branches. The new `0x855d` texture
also makes the mace's existing `0x855d` bone sprites visible, including frames before a particle gate opens.
Its separate `0x80ba` sprite has no world bitmap slot and remains counted-only, outside the three particle pairs.

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
| `nice -n 10 make -j4` | pass; final compiled source | 6.92 s |
| Explicit mu-world/mu-walk render build | pass | 5.32 s |
| `validate_render_effects22 --cases 1000`, final directed point fixtures | 10,002 comparisons, 0 mismatches: create 3,000, move 3,000, render 3,000, points 1,000, bitmap registrations 2 | 17.06 s |
| Registry `validate_render_effects22` with mutants, once after fixing the fixture coverage | 202 comparisons, 0 mismatches, 19/19 compiled mutants caught; none stopped; point-store mutant caught in 12/20 cases | 26.75 s |
| Portable `run_test_suites.py --affected origin/main`, integration off, two jobs | 148 selected work items, 9 reported suites, 1,607 tests: 1,346 passed, 261 skipped, 0 failures/errors | 278.9 s test wall; 327.19 s command including selection |
| Private native/tests from root with private-env.sh, 8d reduced plus 6b | 37 tests, 0 failures/skips | 27.65 s |
| New private module after adding the explicit demo hero label | 5 tests, 0 failures/skips | 8.31 s |
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

Steward validators: pending final affected-row report. Selection is 75 rows, including the movement symbol
fallback. The nine rows that build changed libraries but use no changed symbol are not selected. Existing
mutant targets are unchanged; the new particle and op-50 targets are covered by the 19 mutants above.

## Limits and next

- Native renders are before/after comparisons, not original-client pixel comparisons. Particle record arithmetic,
  render calls and OBJECT point stores are compared with the pinned original instructions.
- Owner points follow the native item pose. This does not prove the native pose equals the original client's pose.
  Pre-draw requests on unknown/out-of-domain bones remain refused; rank-5 requires bones 35/26. An absent or stale item owner ends the owned spark.
- Argument 8 is hosted for the actual mace domain 0..2. Arbitrary original OBJECT memory is not hosted.
- `mu-render character` still has no item OBJECT registry and refuses the OBJECT-owned spark; its unowned kinds
  now exist. Player-model actors use the shared hook but have no installed render fixture in this lane.
- Add a world bitmap slot for the `0x0f20` program's existing `0x80ba` sprite, with its original loader mapping.
- `0x0f2a`'s additional requests (`0x85bc/5`, `0x83b8/8`, `0x85fc/1`, and its register-selected particle) remain
  separate work. Do not read a zero refusal count in the two-mace fixture as a whole-client census.
- The installed Native Preview and both Wine apps are untouched. The steward owns merging and the full gate.

## Cleanup

Remove this lane's scratch, render and build outputs after the final push and ready-prs line. No new private input
needs to be retained. Committed checks, hashes and reviewed render measurements are the handoff evidence.
