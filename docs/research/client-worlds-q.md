# Acheron, Ferea, Swamp of Darkness and Kubera Mine: primary handlers and the Kubera light

RENDER-WORLDS-Q, 2026-10-28. Four factory classes captured by DATA-ACQ-002: Acheron (world 91), Ferea (112),
Swamp of Darkness (122) and Kubera Mine (123..127). The lane adds eleven of their twelve primary methods
and the elemental terrain-light rule that made Kubera the one capture whose primary light differed from the
live grid. Coverage goes from **61/144 to 72/144 primary methods** and from **21/48 to 25/48 classes** on main
`77c304a`; with RENDER-WORLDS-P and P2 merged the inventory reads **87/144 and 30/48**. Ferea's visual `0x00de6405` (2,328 instructions) is not reconstructed. Labels: **verified** =
compared with the original instructions under Unicorn or with a live capture; **static** = read from
disassembly or files; **inference** = neither.

## Provenance

Target `main.exe` SHA-256 `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`. Capture09 text at
`0x00401000` (SHA-256 `2bd5f2e9…3724`) and run10 data at `0x01a7c000` (SHA-256 `c985e2e6…672f`) are pin-checked by
both validators, whose reports also hash every body, type table and predicate below. No original client or
launcher was started; the live inputs are DATA-ACQ-002's arrival captures `91-acheron`, `112-ferea`,
`122-swamp-darkness` and `123-kubera` ([captures 2](client-world-captures-2.md)), only read.

## Kubera Mine terrain light (verified)

Captures 2 found primary light equal to the live grid in 31 of 32 worlds; Kubera differed by mean 0.035. The
differing cells hold different whole 8-bit levels, i.e. another image, not a scaled one. The cause is a
**world-specific light-file rule in OpenWorld**, not the shared folder: `Data\World124` (the folder of all five
Kubera worlds, `0x00e1e4b6` → folder 0x7c) holds `TerrainLight.OZB` and five elemental variants.

OpenWorld `0x0182876e` chooses the light path at `0x01828dc7..0x01828f07`: world 30 (`0x0095fb7c`) takes
`TerrainLight2`/`TerrainLight` by an event flag, world 0x22 takes `TerrainLight`/`1`/`2` by a local, and otherwise
the Kubera predicate `0x00e1e4b6` (worlds 0x7b..0x7f) selects `sprintf("%s\\%s", folder, name)` with the name
built by the Kubera handler's routine **`0x00e18e27(out, world)`**: 123 → `TerrainLight_Fire.bmp`, 124 → `_Water`,
125 → `_Earth`, 126 → `_Wind`, 127 → `_Dark` (strings `0x01aa9ae8..0x01aa9b48`). Every other world loads
`TerrainLight.bmp`; then `0x016cb561` reads it and `TerrainLight_2` follows as before.

Native: `mu_terrain_light_name(world)` (`reconstructed/terrain/terrain.c`) returns the stem and
`native/core/mu_terrain.c` loads `<stem>.OZB`. World 30 and 0x22 keep their previous behaviour (not modelled).
`scripts/validate_world_light_name.py` runs `0x00e18e27` (std::string helpers as recording stubs), `0x00e1e4b6` and
`0x0095fb7c` as original instructions for worlds −5..300: **304 cases equal, 0 stops**; worlds 30 and 0x22 reported
apart; the old rule fails exactly the 5 Kubera worlds; **4/4 compiled mutants caught**.

Effect at the Kubera arrival tile: primary light mean |Δ| **0.03515 → 0**, frame light near the hero
**0.1054 → 0**, image mean |Δ| **12.609 → 4.321** (share > 24: 0.0743 → 0.0474).

## Methods (verified)

| Family | Original range | Cases |
|---|---|---:|
| Acheron create / move / visual | `0x00d6a6d7..0x00d6a7aa` / `0x00d6a7aa..0x00d6ae34` / `0x00d6ae34..0x00d6c427` | 3 × 1,000 |
| Ferea create / move | `0x00de5cb0..0x00de5de2` / `0x00de5de2..0x00de6405` | 2 × 1,000 |
| Swamp of Darkness create / move / visual | `0x00e54429..0x00e54575` (+ table to `0x00e54646`) / `0x00e54646..0x00e54752` / `0x00e5540e..0x00e555d2` | 3 × 1,000 |
| Kubera create / move / visual | `0x00e19bb3..0x00e19dfb` (+ table to `0x00e19ed0`) / `0x00e19ed0..0x00e1a5df` / `0x00e1b5fb..0x00e1b6f5` | 3 × 1,000 |

- **Acheron** (predicate `0x00d6a614`: world 91 or 92; no object null test). Create clears +0x64; range −3000 for
  27/29, −428.571442 for 60..62; HiddenMesh −2 for 38/54..57/69/80; returns true. Move: AddTerrainLight
  flicker `(rand%n+3)·0.1` for 9, 16, 73, 100 (ranges 2/3/3/2); BlendMesh V/U scrolls for 22..26 and 78; types
  16 and 52 count +0x64 down and alternate SetAction 0/1 at the end of the action (the action-1 sine in type 16
  is computed and discarded). Visual (ret 8): Spark04 `0x8155` sprites at bones (9, 16, 31, 89 twice per bone, 93,
  100), type 52's flare/particles, 73's rotating sprites and 0x8017 particle, particles of 38/54/55/56/69/80, and
  type 57's CreateEffect `0x59a`.
- **Ferea** (no world test). Create: range −400 for 21 types; type 39 stores itself in handler +0x50 and takes
  handler state +0x48 as its action. Move: hidden types; lights of 17, 72 and 123 (`0x011ff622` random scale; 123
  at a point 80 units behind the object along angle z, colour (0.3, 0.3, 0.3) in state 3 because `0x00cfcede`
  assigns the scalar to all three); 43 scroll; 51 alpha target 0.1 while the hero tile is in 21..48 × 106..138.
- **Swamp of Darkness** (world 122). Create table: range −400, after-character, hidden; 131..133 seed +0x64 with
  `(int)rand_range(4, 10, 1)`; 88 picks its type by handler +0x78 (constructor 1 → stays 88, as live). Move of
  131..133: action-end counter with SetAction 0/1. Visual: 83 `0x59a` on rand%100 == 0; 176 `0x199` keyed by scale
  when rand%5 == 1 and timeGetTime % 1024 < 30.
- **Kubera** (worlds 123..127). Create table: range −300 (entry `0x00e19c21` sits inside the after-character case),
  after-character, velocity 0.35, 158 copies position/angle to +0x110/+0x140, registers itself and sets handler
  +0x14; 15/47/52 set every action of their model to PlaySpeed 0.3 without loop. Move (false without a model):
  15/47 four-action cycle with rand%10+5 holds; 47 sounds 0x4f4/0x4f3 within 900 of the hero; 52 opens within
  500 (StopBuffer 0x4f2, PlayBuffer 0x4f1, actions 1 → 2) and closes otherwise (action 3, sounds at half its keys,
  then 0); 100/145 timers on frame time; 127/132/134/135 restart; 158 by +0x64. Visual: 161 `0x195` on rand%80 == 1.

`scripts/validate_worlds_q.py` compares AL, all 0x3d8 OBJECT bytes, the handler members, the model action table,
ordered recorded calls (AddTerrainLight, CreateParticle, CreateSprite, CreateEffect with its constant arguments
asserted, PlayBuffer, StopBuffer, register, TransformPosition bones) and the final MSVC RNG. Run as original
instructions: predicates, SetAction `0x012affa4`, `0x00eaaa44`/`0x012bcf9d`, `0x011ff622`, ftol `0x0191c5e0` (both
CRT ISA paths), sin/cos/sqrt/fabs and the vector helpers. Cases mix sampled and directed types, worlds, null
objects/models, action tables of 0..8 records, frames around the action end, hero distances at 500/900, hero tiles
at the Ferea bounds, timeGetTime phases and WorldTime. **11 families, 11,000 cases equal, 0 mismatches, 0 stops;
45/45 compiled mutants caught.** Not sampled (the original faults or leaves the modelled state): Acheron's move of
16/52 without a model or with an action outside the table (unchecked record copy), Kubera's move with an action ≥
the table count (unchecked read), and type-16 action-1 cases with zero keys (sin(∞) enters the CRT error path; the
value is discarded).

## Native consumption

`mu_objects_runtime.c` calls `mu_worlds_q_create` when `mu_obj_create` leaves worlds 91/112/122/123..127 unsupported
(models are loaded before creation, so Kubera's PlaySpeed writes reach the native model's client-layout table),
and `mu_worlds_q_move` after consuming the generic part's events, so the animation tick precedes the slot as in
MoveObject. Handler members live in `rt.q_handler` (Ferea state 0, Swamp variant 1 as constructed). The hero tile
for Ferea's type 51 is `(int)(hero / 100)`; frame time is the render pass's 0.1. Worlds 91/122/123..127 are
primary-visual worlds: one outer RenderObjectVisual `rand()` for objects with a model, then the slot; Acheron's
bone types need a posed model with enough bones, else the request is counted in `draw_unsupported`. World 92 has
its own class (`0x01aa6154`) and is not dispatched here, although Acheron's predicate accepts it.

Refused and counted (no native consumer): CreateEffect `0x59a` (Acheron 57, Swamp 83, key 0), `0x199` (Swamp 176)
and `0x195` (Kubera 161) with the object as owner and their keys (`draw_unsupported`), and StopBuffer
`0x4f1`/`0x4f2` (Kubera 52, `move_unsupported`).

## Fidelity at the captured arrival tiles

`scripts/fidelity_tour.py` with the DATA-ACQ-002 manifest, installed data, 25 steps, 1722 × 1048, base `77c304a`
against this branch, both built in the worktree. The base run reproduces captures 2.

| Capture | Image mean \|Δ\| / share > 24 | Static field differences (near hero) | Primary light | Frame light near hero | Objects drawn |
|---|---|---|---|---|---|
| Acheron 91 | 7.706 / 0.0424 → 7.706 / 0.0424 | range 27 + after-character 58 (39) → after-character 58 (39) | 0 → 0 | 0.0147 → 0.0147 | 165 → 165 |
| Ferea 112 | 2.370 / 0.0043 → 2.365 / 0.0043 | range 944 (18) → **0** | 0 → 0 | 0.0150 → 0.0152 | 75 → 79 |
| Swamp of Darkness 122 | 1.709 / 0.0113 → 1.709 / 0.0113 | range 2,411 + after-character 97 (47) → **0** | 0 → 0 | 0 → 0 | 101 → 121 |
| Kubera Mine 123 | 12.609 / 0.0743 → **4.321 / 0.0474** | range 498 + after-character 73 + velocity 1 (16) → **0** | 0.0352 → **0** | 0.1054 → **0** | 164 → 165 |

- Every static OBJECT field the tour compares now equals live in Ferea, Swamp of Darkness and Kubera (10,744 objects,
  zero missing/extra). Swamp's type-88 object stays type 88 with the after-character flag, as live (variant 1).
- Acheron's remaining 58 after-character differences are written by its custom-render slot `0x00d6c427` (20 such
  writes, static), not by a primary method. Acheron's visual now creates its bone sprites (24 created, 12 drawn
  over the run) but the captured frames are byte-identical; inference: they fall inside or behind the object
  meshes at these poses; the shared sprite renderer was not investigated.
- Swamp of Darkness draws 20 more objects (range −400) with an identical frame: inference, they lie outside the
  unmasked view.
- The other 28 DATA-ACQ-002 captures: **56/56 PNG, 28/28 OBJECT and 28/28 light dumps identical** between base and
  branch.

## Limits and follow-ups

| Item | Status |
|---|---|
| Ferea visual `0x00de6405` | Static only; 2,328 instructions of vector-class light/particle producers (111 data-pointer calls, 22 particles, 20 random ranges, 10 bone transforms). Next lane. |
| CreateEffect `0x59a`/`0x199`/`0x195` with owner and key | Refused and counted; needs a keyed owned-effect consumer (RENDER-EFFECTS). |
| StopBuffer `0x00a6ad76` | Refused and counted; needs a native stop hook. |
| Ferea state machine (handler +0x48, slot `0x00de5b82`) and Swamp variant writer | Not ported; constructor values used. |
| Custom render (`0x00d6c427` Acheron with the after-character flags, `0x00de8a10`, `0x00e54752`, `0x00e1a5df`) and after render | Missing, outside the primary count. |
| Light-file branches of worlds 30 and 0x22 | Not modelled (unchanged). |
| Acheron sprites invisible in the captured frames | Inference above; shared sprite path. |

Each capture is one arrival frame without pool, RNG phase or time synchronisation, so particles, sprites and
sounds are not compared live.

```sh
tools/python/bin/python scripts/validate_worlds_q.py --cases 1000 --mutations --output <json>
tools/python/bin/python scripts/validate_world_light_name.py --mutations --output <json>
MU_RECOVERY_INTEGRATION=1 tools/python/bin/python scripts/run_validators.py --private --only validate_worlds_q,validate_world_light_name
tools/python/bin/python -m unittest reconstructed/objects/test_worlds_q.py native/tests/test_native_worlds_q.py
```

[Handoff, gate and cleanup](../handoffs/RENDER-WORLDS-Q.md).
