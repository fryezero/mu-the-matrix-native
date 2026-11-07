# RENDER-WORLDS-121: Test Area 121's two slots and Devias 0x67's action choice

Target: the executable SHA-256 `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`. Text and
second-image-data captures pinned in `scripts/pins.py` (capture09/run10). Method: static disassembly, then compiled
authored C compared with the original instructions under the strict Unicorn machine (`scripts/validate_worlds_121.py`,
`scripts/validate_worlds_slots3.py`), and the production runtime in a host (`native/tests/worlds_121_host.c`).
Labels: **verified** = instruction-compared, **static** = read from the disassembly only, **inference** = reasoning.

Follows [RENDER-WORLDS-SLOTS3](client-worlds-slots3.md) §5 and [RENDER-WORLDS-FOG](client-worlds-fog.md) §5, which
corrected its outline. The class slot census goes from **142/144 to 144/144**.

## 1. The custom slot `0x00d58bd8` (verified)

Class world-121 (vtable `0x01aa51fc`, slot 0x38), `thiscall(handler, object, model, index)`, `ret 0xc`, 1,972
instructions. It has **no world test**. The world manager passes types 0..300 only, so its cases 0x1a8..0x1ad and
0x836..0x83e/0x872..0x875 (the base `0x00d5c79c`) are never reached.

| Types | What it does |
|---|---|
| 6..12 | for every mesh `m < model+0x24` and normal `k < mesh+6`: `[0x06fd0918 + m·0xea60 + 4k] = 0.5`; object light `+0xec = (1, 1, 1)`; RenderBody(2, alpha, blend mesh, blend light, u, v, −1, −1) |
| 0x10 | frame ≥ 19: `SetAction(o, rand() % 2)`; RenderBody (hidden −1) |
| 0x11 | action ≤ 1 and frame ≥ 19: `r = rand() % 100`; `r < 90`: SetAction 0 or 1 by `r`'s parity, else 2 or 3. Action 2 at frame ≥ 97, action 3 at frame ≥ 98: `SetAction(rand() % 2)`. RenderBody |
| 0x13 | action 0: by frame window, CreateParticle at posed bones (below), then 0x801c (sub 8, scale 1.5) at every bone `k < model+0x22`; frame ≥ 19.5 writes action 1 directly (not SetAction). Action 1: `rand() % 40 == 30` writes action 0. RenderBody |
| 0x14 | meshes 0 and 1 (flags 2), mesh 1 with flags 0x280 and 0x44 and bitmap 0x800a; action 0: particles at bones 5, 6, 8, 11 (below), frame ≥ 19 writes action 1; action 1: `rand() % 40 == 25` writes 0. No RenderBody |
| 0x15 | action 0, frame in [4, 8]: ten particles at bones 7, 16, 17, 20..24; frame ≥ 19 writes action 1; action 1: `rand() % 40 == 19` writes 0. RenderBody |
| 0x2e, 0x35, 0x4c, 0x59 | the after flag `+0xa = 1`, nothing drawn |
| 0x39 | TransformPosition of bone 1 (its point unused), RenderBody (hidden `+0x68`) |
| 0x44, 0x45, 0x47 | RenderBody(2, alpha, 0, `(sin(T·0.001) + 1)·0.5 + 0.3`, u, v, −1) |
| 0x52 | RenderBody (hidden `+0x68`) |
| 0x53 | meshes 0, 1 (flags 2), meshes 2 and 3 with flags 0x42 as their own blend mesh; after flag |
| 0x5c | mesh 0 (flags 2); after flag |

Constants: 19 `0x01a82968`, 19.5 `0x01aa5290`, 97 `0x01aa4464`, 98 `0x01aa5294`, 1.0 `0x01a7dd48`, 0.5
`0x01a7df14`. T = `0x06fce370`, sine `0x009681bd`. Every branch with a draw answers 1.

**CreateParticle** `0x0168fafd(type, point, the object's angle +0x164, light (1, 1, 1), sub, scale, 0, 0)` at a
point from TransformPosition `0x012b6ef1` of the zero vector on bone k. There are 28 call sites and 24 TransformPosition
sites:

| Type | Window (action 0) | Bones → (type, sub, scale) |
|---|---|---|
| 0x13 | frame in [2, 5] / [11, 12] / [13, 14] / [15, 17] (else-if) | every bone / 6, 7, 8 / 9, 10, 11 / 12..19 → (0x801e, 7, 1.0); then every bone → (0x801c, 8, 1.5) |
| 0x14 | always / frame ≤ 8 / frame ≥ 12 / frame ≤ 15 | 5 → (0x801c, 8, 2.0); 6 → (0x801c, 8, 1.5), (0x801e, 7, 0.1); 6 → (0x801c, 8, 2.0), (0x801e, 7, 0.1); 8 and 11 → (0x801c, 9, 2.0), (0x801e, 7, 0.1) |
| 0x15 | frame in [4, 8] | 7 → (0x801c, 9, 0.5), (0x801e, 7, 1.0); 7, 16, 17, 20, 21, 22, 23, 24 → (0x801b, 5; 1.0, 0.5, 0.7, 0.3, 0.3, 0.5, 0.3, 0.3) |

**SetAction `0x012affa4`** (37 instructions): the object's model (`0x00966cc4` → `0x00eaa8cf`); with
`action < model+0x26` and `action ≠ o+0x2a`: `o+0x2c = o+0x2a`, `o+0xd4 = o+0xd0`, `o+0x2a = action`, `o+0xd0 = 0`.

**Bitmap 0x800a.** World 121's case of the object loader registers `Effect\Chrome08.jpg` as 0x800a (filter 0x2601,
wrap 0x2900, `0x018417cd`). Raklion 57/58 load the same file under the same index (`0x0183f4e2`).

## 2. The after slot `0x00d5a6cc` (verified; never reached in the client)

198 instructions, no world test: 0x2e and 0x35 RenderBody (flags 2, hidden `+0x68`); 0x4c writes the object light
`+0xec[k] = sin(T·s_k)·0.2 + 0.5` with `s = (0.002, 0.0015, 0.0014)` (`0x01a7ed78`, `0x01a800a0`, `0x01aa528c`; a
`0x01a7df08`, b `0x01a7df14`) through `0x009681bd`, then the same RenderBody; 0x53, 0x59, 0x5c RenderMesh 4, 0, 1
(flags 0x42, the mesh as its own blend mesh).

**Static.** The after pass `0x016d6949` never runs in world 121. Its world list covers 0x7a..0x85 but not 0x79, and its
class answer (slot 8 `0x00d5cb7c`, handler byte +5) is 0: the class's constructor `0x00d584f1` calls only the base
constructor `0x00d5c99f`, which clears +5. So the after flags that the custom slot sets for 0x2e, 0x35, 0x4c, 0x53,
0x59 and 0x5c select nothing, and in 121 the types 0x2e, 0x35, 0x4c and 0x59 are drawn by nobody. The native has the
same gate (`mu_world_after_gate(121, mu_world_class_after(121))` is 0), so the ported after slot is compared but
never draws in a session.

## 3. Devias 0x67's action choice (verified)

RenderObjectVisual's Devias case `0x017f9bdc`, after the outer draw: type 0x67 (`0x017f9d79`). When the model's
whole frame `+0xb4` (Animation's `(short)(int)frame`) equals the action's last key (`[model+0x30] + 16·action + 8`,
minus 1), the client calls `rand()` and `SetAction(o, rand() % 32 == 0 ? 1 : 0)`. Natively the object runtime does it
right after its outer draw, from the object generator (the particle visual draws only 0x64).

## 4. Native

- `reconstructed/objects/world_test_area_visual.c`: both slots, `mu_devias_action_pick` and `mu_obj_frame_whole`.
  `world_slots2_visual.c` chains class 121 behind its classes, with the bitmap and the type list.
- **SetAction is shared, not copied:** kanturu_underground.c's wrapper over `mu_move_set_action` is now the exported
  `mu_obj_set_action`. The slot and Devias call it. `q_set_action` and `wp_set_action` are unchanged.
- **Per-vertex light seam.** The slot emits the pseudo call `MU_OBJ_CALL_VERTEX_LIGHT` (args[0] = 0.5).
  - The runtime poses and transforms after the custom slot, unlike the client, which transforms before it.
  - So `slot_vertex_light` (`mu_objects_runtime.c`) replays the write after the pose and before the draw: every
    normal of every mesh in the model's light region (`MU_MODEL_LIGHTS`).
  - No other slot emits the call, so every other world's draw is unchanged.
  - Stale values behave as in the client. An unlit model's Transform leaves the buffer alone, and the mesh draw reads
    it only when the model is lit.
- **Particles.** World 121 runs its custom slot through `test_area_custom_call`.
  - The slot runs into a scratch log sized from the model (48 + 2 × bones + 32), since 0x13 can create two particles
    per bone before its body.
  - CreateParticle goes to the visual pass's consumer, and the draws go to the slot log.
  - 0x13..0x15 are posed with `test_area_bone`. A bone the model lacks answers NaN, and that request is refused and
    counted (`draw_unsupported`).
  - The particle module serves the kind 0x801c/8 (4 of the 28 call sites). It refuses 0x801e/7, 0x801c/9 and
    0x801b/5 (`mu_pt_kind_supported` 0) and counts them in its `unsupported` counter.
- `mu_slot_model` gains `bone_count` (model +0x22) and `action_count` (+0x26), filled by the runtime's
  `slot_model`.

## 5. Instruction comparison (verified)

`validate_worlds_121`:
- `custom_121`: the custom slot against `mu_class_custom(121, …)`. Compared: draws with the StreamMesh byte and colour,
  particles, TransformPosition's bone list, answer, rand generator, object and model fields. The per-vertex light
  buffer is mapped at `0x06fd0918` and read at every draw and at the end, so the write's place in the sequence and
  its exact extent (mesh +6 normal counts, model +0x24 meshes) are compared. SetAction runs as client code.
- `actions_121`: the custom slot for 0x10..0x15 only, with frames at their window edges and seeds whose first
  `rand()` lands on the compared residues.
- `after_121`: the after slot, compared the same way.
- `devias_67`: RenderObjectVisual in Devias, as `validate_worlds_slots3`'s `rng_2`.

One case in five runs in another world, since neither slot tests the world. `validate_worlds_slots3`'s `rng_2` now
compares type 0x67 whole: the model has an action table, action count and whole frame, and the object after the call
is compared.

Counts in the [handoff](../handoffs/RENDER-WORLDS-121.md#checks).

## 6. Fidelity

- DATA-ACQ-002 32/32 and the October 22 tour 14/14 are byte-identical (PNG frames, OBJECT and light dumps), Devias
  included. Both October Devias views hold two type-0x67 objects at action 0, frame 0, and their actions' last key is
  not 0, so the choice draws nothing there.
- **World 121** has no capture and no warp, and its installed `EncTerrain122.obj` does not decode natively (the
  NATIVE-OBJECTS-001 boundary). An offline frame with a demo layout (one object of each slot type with a model, 20
  types, not client placement; `--objects-dir`) shows the change. The terrain light of 121 is black, so before the
  change every object drew black. Now types 6..12 draw at the slot's per-vertex light 0.5 and object light 1, and the
  0x801c/8 particles of 0x13..0x15 appear. The particle module counted 36 refused requests in 25 frames; the object
  runtime counted 0.

## 7. Limits

- Bones beyond the model's bone count are refused natively. The client reads whatever bone matrix lies there.
- Devias with an action at or beyond the model's action count: the client reads past the action table; the native
  refuses and counts it.
- Three of the four particle kinds have no native consumer (refused and counted).
- No live reference for world 121, and the after slot never draws in a session (§2).
