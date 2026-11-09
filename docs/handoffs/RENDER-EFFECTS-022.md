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

Pending final render/check measurements.

## Checks

Canonical private environment sourced from the repository root. Every heavy job uses `nice -n 10`, builds
use `-j4`, runners use two jobs. A load >14 pause was observed before continuing.

Pending final check table and Steward validators.

## Limits and next

- Native renders are before/after comparisons, not original-client pixel comparisons. Particle record arithmetic,
  render calls and OBJECT point stores are compared with the pinned original instructions.
- Owner points follow the native item pose. This does not prove the native pose equals the original client's pose.
  Unknown/out-of-domain bones are still refused. An absent or stale item owner ends the owned spark.
- Argument 8 is hosted for the actual mace domain 0..2. Arbitrary original OBJECT memory is not hosted.
- `mu-render character` still has no item OBJECT registry and refuses the OBJECT-owned spark; its unowned kinds
  now exist. Player-model actors use the shared hook but have no installed render fixture in this lane.
- `0x0f2a`'s additional requests (`0x85bc/5`, `0x83b8/8`, `0x85fc/1`, and its register-selected particle) remain
  separate work. Do not read a zero refusal count in the two-mace fixture as a whole-client census.
- The installed Native Preview and both Wine apps are untouched. The steward owns merging and the full gate.

## Cleanup

Remove this lane's scratch, render and build outputs after the final push and ready-prs line. No new private input
needs to be retained. Committed checks, hashes and reviewed render measurements are the handoff evidence.
