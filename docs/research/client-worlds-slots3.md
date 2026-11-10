# RENDER-WORLDS-SLOTS3: RenderObjectVisual's outer draw in every world

Update: [RENDER-WORLDS-INNER-001](client-worlds-inner.md) recovers the Kanturu 37/40 hook and Blood Castle
11..17/52 switch left open in section 3. The other classless inner draws remain open.

Target: the executable SHA-256 `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`. Text and
second-image-data captures pinned in `scripts/pins.py` (capture09/run10). Method: static disassembly, a Unicorn probe,
then compiled authored C compared with the original instructions under the strict Unicorn machine
(`scripts/validate_worlds_slots3.py`), and the production runtime in a host (`native/tests/worlds_slots3_host.c`).
Labels: **verified** = instruction-compared, **static** = read from the disassembly only, **inference** = reasoning.

Follows [RENDER-WORLDS-SLOTS2](client-worlds-slots2.md) §1 (the outer draw in the class worlds).

## 1. Where the client draws it (verified)

`0x017f9758` looks up the object's model and returns at `0x017f9792` without one. Otherwise it calls `rand()` at
`0x017f9797` (return address `0x017f979c`; `l = (r % 30 + 70) · 0.01`) **before** its world switch `0x017f97e2`, in
every world. The switch has inline cases 0..4, 6, 8..17 (jump table `0x017fccd0`), 0x34 and 0x37; every other world
takes the default branch `0x017fcb5c` (the hooks, then the world manager). No draw precedes the outer one in any
world tried. So the client draws exactly one outer rand per object with a model, in every world, before any branch's
own draws.

## 2. What the native did, and does now

| World(s) | Native before | Native now |
|---|---|---|
| 0..3 (Lorencia, Dungeon, Devias, Noria), 141 Tormenta | the particle visual (`mu_pt_object_visual`) drew it from the **particle** generator | the object runtime draws it (object generator); the particle visual reads `host->outer_rand` |
| 10 Icarus | `icarus_cover` (`native/core/mu_particles.c`) drew it from the **particle** generator | the object runtime draws it; `icarus_cover` no longer draws |
| 37, 40 (0x25/0x28) | `world_flames` drew it (object generator) | the object runtime draws it at the top of the visual; `world_flames` no longer draws |
| 4, 7, 8 (Lost Tower, Atlans, Tarkan) | `mu_builtin_visual`'s first draw (object generator) | unchanged (correct place) |
| every other world without a class (6, 9, 11, 18, 24, 30, 31, 33, 34, 38, 39, 41, 42, 46, 51, 56, 65..68, 73, 74, 98, 102, …) | none | drawn by the object runtime |
| class worlds | drawn since RENDER-WORLDS-SLOTS2 | unchanged rule, now the same predicate |

`mu_obj_visual_flicker(world, has_model)` (`reconstructed/objects/world_slots2_visual.c`) answers 1 for every object
with a model in every world except 4, 7 and 8. The runtime (`native/core/mu_objects_runtime.c`) draws once, at the
top of `handler_visual` and in the non-primary branch, and stores the value in `rt.visual_outer_rand`;
`mu_world_particles_object_visual` takes it as an argument.

## 3. Instruction comparison (verified)

`validate_worlds_slots3` runs RenderObjectVisual from its entry (Tormenta 141 through its class slot 0x34
`0x00e4ef4b`) with the model lookup stubbed, labels each rand call outer (`0x017f979c`) or inner, and compares the
sequence and the generator state with the native composition on one generator.

- Compared whole (every branch the native ports): 0, 1, 2, 3, 4, 7, 8, 10, 37, 40, 141.
- Compared up to the switch (the native has no visual for the world): 6, 9, 11, 18, 24, 30, 31, 33, 34, 38, 39, 41,
  42, 46, 51, 56, 65..68, 73, 74, 98, 102, and `rng_other` for every remaining id 0..145 without a class.
- 36 families × 1,000 cases = 36,000 cases, 0 mismatches, 0 stops. The first 301 cases sweep types 0..300; one in
  eight has no model.
- 22 compiled mutants, all detected (fewest: "Kanturu flame 0x3b without its draw", 44 cases; "a world past 102"
  112; "without the model gate" 113).
- RENDER-WORLDS-SLOTS2's 16 rng families rerun on the new predicate: 16,000 cases, 0 mismatches; its 17 flicker
  mutants (re-anchored; "misses Vulcanus 63" and "misses Tormenta 141" replace "draws for 141") all detected.

**Client draws after the outer one that the native does not port (counted, verified).**
- Devias 0x67: the action pick `0x012affa4` (236 of 1,000 Devias cases take it and are compared up to the switch).
- The Kanturu hook `0x00e75089` past its flames in 37/40: types 0x25, 0x3e, 0x51, 0x53, 0x5c, 0x62, 0x69.
- Blood Castle 11..17 and 0x34 (`0x017fc023`); occasional named types in 9, 24, 30, 31, 33, 38, 39, 41, 42, 46, 51,
  56 and 98.
- Worlds 18, 34, 73 and 74 mostly stop after the switch (a hook reads an unmapped global): counted, not compared
  past it.

## 4. Fidelity (verified, default draw)

"Before" is the `4da302f9` binary (main + #313), taken once.
- DATA-ACQ-002: 32/32 captures byte-identical (PNG frames, OBJECT and light dumps), including the classless 6, 38,
  40 and 56 and the live clock for those four.
- October 22 tour: 7 of 14 views identical (Devias 2, Lost Tower, Atlans, Tarkan, Kanturu 37, Raklion, Karutan).
  Seven change:

| View | Objects changed (fields) | Frame-light words | Frame 24 mean \|Δ\| (px) | Particle-generator rand calls |
|---|---|---|---|---|
| 00b Lorencia | 64 (light copy +0x1e8; 0xa8 ×7) | 873 | 0.092 | 608 → 237 |
| 01 Dungeon | 17 (+0x1e8) | 285 | 0.352 | 288 → 117 |
| 02b Devias town | 15 (+0x1e8; 0xa8 ×4) | 156 | 0.002 | 356 → 164 |
| 03 Noria | 0 | 0 | 0.010 | 747 → 199; sparkles 8 → 0 |
| 10 Icarus | 0 | 0 | 19.6 | 2,329 → 9,315; created 312 → 408 |
| 33 Aida | 16 (+0x1e8) | 75 | 0 | — |
| 51 Elbeland | 19 (+0x1e8) | 252 | 0 | — |

A control build with the new plumbing but the old draw placement reproduced the "before" outputs byte for byte,
14/14. So every change is the RNG phase: the object generator's flicker lights and BlendMeshLight shift, and the
particle generator loses one draw per visual, which re-phases Noria's sparkles and Icarus' cloud cover (large sprites,
hence the pixel delta). The live RNG state is not captured, so the phase has no live reference (**inference**: the
new placement is the client's order, so the phase is closer to it, but no capture can show that).

## 5. Test Area 121 (static; not ported, slots stay 142/144)

The custom slot `0x00d58bd8`:
- Types 6..12: for every mesh `m` (model +0x24) and entry `k` < mesh+6, `[0x06fd0918 + m·0xea60 + 4k] = 0.5`; object
  light +0xec = (1, 1, 1); RenderBody.
- 0x10, 0x11: rand, then the action pick `0x012affa4` (7 calls in all; 0x11 branches on a value 0x5a), RenderBody.
- 0x13..0x15: 24 TransformPosition and 28 CreateParticle (bone-placed), one rand each, RenderBody/RenderMesh (0x14:
  four meshes).
- Body/mesh-only branches: 0x2e, 0x35, 0x4c, 0x39; 0x44, 0x45, 0x47 (call `0x009681bd`); 0x1a8..0x1ad (colour from
  three vector indexes); 0x52, 0x53, 0x59, 0x5c. Types above 300 are never passed.

`0x06fd0918` is the model's per-vertex light (`MU_MODEL_LIGHTS`); its readers are the RenderBody/RenderMesh wrappers
`0x00966e2c`.. and the mesh renderer `0x0151b2ca..0x0152beab`. Raklion (`0x00e94a8f`) and world 82 (`0x00e31a55`)
write it too.

Porting it needs: (1) a slot event "set the per-vertex light of every mesh to v" applied after the transform and
before the body draw; (2) a port of `0x012affa4` (also Devias 0x67); (3) posed bones in the custom pass for
0x13..0x15 and CreateParticle to the existing consumer, refusals counted; (4) the after slot `0x00d5a6cc` (198
instructions). 121 has no capture and no warp.

## 6. Limits

- The action pick `0x012affa4` is not ported (Devias 0x67, Test Area 121 0x10/0x11). Since RENDER-WORLDS-121 it is:
  [client-worlds-121.md](client-worlds-121.md).
- The inner draws listed in §3 have no native visual; their worlds compare only up to the switch.
- No live RNG reference for the phase changes in §4.
