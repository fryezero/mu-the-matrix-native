# Arrow owner lifetime and Flare02's green particle trail

Target: Mu The Matrix `main.exe`, SHA-256
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
This continues [012](client-render-effects-012.md). The lane started from main `5a91b98d`
after GitHub reported #296 merged. No live client session was needed.

## Recovered contracts

The original instruction image supplies two of the four refused joint kinds:

| Kind | Original code | Contract |
|---|---|---|
| 0x80e3/5 | create `0x01550963`; move `0x01583f8d` | Caller width and colour, common white for null colour, life 20, eight tails, speed 70, reversed U. Move requires a non-null live owner with signed lifetime +0x6c greater than zero. Otherwise clear joint life/live, then run the closing tail shift, time increment and life decrement. |
| 0x7f79/f | create `0x0154ceaa`; move `0x0157d54d` inside `0x0157d2f5` | Signed key becomes lifetime, key clears; 16 tails, speed 70, additive colour (0.4,0.9,0.5). A live joint with an owner emits two Shiny01/3 particles before the life-below-15 fade. Dead owners clear live and suppress particles. Terrain light and closing tails still run; null owners skip those calls. |
| particle 0x7f66/3 | create `0x015e5d83`; move `0x016587b9` | Alpha 1, velocity `(rand%8-4,rand%4,rand%4)` in call order, life 30, scale `rand%10/20+0.5`. Common Shiny01 pitch 45, movement through MovePosition, colour /1.05, scale -0.04, alpha -0.001 and death at alpha <= 0; ordinary sprite rendering. |

`mu_jt_object` now exposes the owning effect's lifetime. `effect_object` refreshes it from the
arrow record at emission and after MoveEffects, before MoveJoints. The shared ctypes object
layout includes the appended field. The new validator defines the original OBJECT's +0x6c
and samples signed limits, -1, 0, 1, 2 and 20, alongside live/dead/null owners.

The native joint callback already reaches the legacy particle pool. Admitting Shiny01/3 completes
that route without a new bitmap: Shiny01 and force_Pillar were already registered. The portable
host exercises the real callback, owner-lifetime refresh and two-particle emission.

## Validation boundary

`scripts/validate_render_effects13.py` executes pinned CreateJoint, MoveJoint and RenderJoints,
including the full GL call stream, plus CreateParticle, MoveParticles and RenderParticles.
It checks state, recorded downstream calls, randomness and drawing. Original vector helpers
execute; controlled external services provide objects and terrain. Text SHA-256
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`, data SHA-256
`c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`.
The exact final counts and wall times belong in the [handoff](../handoffs/RENDER-EFFECTS-013.md).
Native scene comparisons establish regression behavior, not live-client pixel equivalence.

## Still open

- **0x7f78/b, twelve requests:** ambient clock, owner +0x110, write-back of owner position and collision
  service. The current read-only owner view cannot express the full contract. No substitute orbit was added.
- **0x7f79/e, three requests:** move `0x0157d379..0x0157d548` emits sprite 0x7f26, smoke01 subtypes
  0x22 and 0x23, then particle 0x7f26/0xa, with colour changes between calls. Those particle
  create/move/render contracts and the sprite route need comparison before admission.
- **Ground skills:** 0x70c still lacks native child effects 0x703..0x706, stones 0x419/0x41a subtype
  0x13, and the combat-session trigger for skills 0x7e7/0x7fc/0x7fd. The owner +0x64 clearing site is
  still unverified. This lane neither changes nor claims to validate its one-play sound lifecycle.
- **0x45e decal:** subtypes 3..7 still count 0x8002 but do not draw it. Bow-arrow subtypes do not use it.
- **Uruk:** a world-100 population/globals capture including weather `0x01cf15ec`, and a native feed
  for that value, are needed to validate keyed 0x806e/12 in context. Default weather remains zero.
- **Muun:** the 16 `muuneffects.tsv` records already exist. The `0x0114203d` consumer needs native
  Muun OBJECT ownership, type, lifetime and posed bone transforms to attach and retire effects.
  A Muun owner fixture/capture with its transform state is still needed; another table export is not.

The first 180-case sample rejected the assumed common Shiny01 sine movement. Subtype 3 has an earlier dedicated branch at `0x016587b9`; the port now follows that branch. No tolerance was changed.
