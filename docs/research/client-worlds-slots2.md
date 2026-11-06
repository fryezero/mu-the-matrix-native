# RENDER-WORLDS-SLOTS2: RenderObjectVisual's outer draw in every class world, and 17 more class slots

Target: the executable SHA-256 `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`. Text and
second-image-data captures pinned in `scripts/pins.py` (capture09/run10). Method: static disassembly, then compiled
authored C compared with the original instructions under the strict Unicorn machine
(`scripts/validate_worlds_slots2.py`), and the production runtime in a host (`native/tests/worlds_slots2_host.c`).
Labels: **verified** = instruction-compared, **static** = read from the disassembly only, **inference** = reasoning.

Follows [RENDER-WORLDS-SLOTS](client-worlds-slots.md) (§1 census, §5 the outer draw).

## 1. The outer RenderObjectVisual draw (verified)

`0x017f9758` looks up the object's model (`0x00966cc4` → `0x00eaa8cf`) and returns at `0x017f9792` without one.
Otherwise it calls `rand()` at `0x017f9797` (`(r % 30 + 70) · 0.01`, used only by the inline world cases) **before**
its world switch (`0x017f97e2`: cases ≤ 0x11, 0x34, 0x37). Every class world is above 0x37, so it takes the default
branch `0x017fcb5c`: 14 hooks (all answer no, RENDER-WORLDS-SLOTS §4), then the world manager `0x00ea2dc1`, which
calls the class's slot 0x34. So in every class world the client draws exactly one rand per object with a model
before the class slot's own draws.

**Family `rng_<world>` (verified).** RenderObjectVisual runs as client code from its entry: model lookup stubbed
(present or absent), the 14 hooks as client code (the static `0x01ec8eb8` built by its constructor, the singleton's
slot 0x34 the client's `0x00db7656`), and the world manager entered as the class's slot 0x34 (thiscall on the class
handler, `ret 8`). Each rand call is labelled by its return address and phase (outer `0x017f979c` / hook / slot).
The native side is the composition the runtime uses: `mu_obj_visual_flicker` (its draw) and then the slot 0x34
routine the runtime calls for that world, on one generator. 1,000 cases per world (the first 301 sweep types
0..300), one in eight without a model. Arca War 101 runs its slot with the registry lookup returning Uruk's handler
(slot 0x34 = the client's `0x00e6f3d5`), as `uruk_arca_visual` forwards natively.

| World(s) | Class slot 0x34 | Client: outer draw | Native before | Native now |
|---|---|---|---|---|
| 57, 58 Raklion | `0x00e946a8` | yes | none | drawn |
| 62 Santa Village | `0x00e423d8` | yes | none | drawn |
| 63 Vulcanus | `0x00e8ece1` | yes | none | drawn |
| 64 Duel Arena | `0x00dc6790` | yes | none | drawn |
| 82 | `0x00e2c002` | yes | none | drawn |
| 100 Uruk / 101 Arca War | `0x00e6f3d5` / `0x00d7be80` | yes | none | drawn |
| 128..130 Abyss of Atlans | `0x00d5d564` / `0x00d5f1f1` / `0x00d60948` | yes | none | drawn |
| 137 Kanturu Underground | `0x00e0a4bb` | yes | none | drawn |
| 93 character scene, 94 login scene | `0x00daa9dd` / `0x00e24be1` | yes | none; the scene visual also ran without a model | drawn; the scene visual only with a model |
| 113, 115..120 (`0x00d5cc9b`), 138 Ignis (`0x00e07081`), 139 (`0x00d9c1a7`) | answer no | yes | none (no class visual call) | drawn (`rng_empty`) |
| 69..72, 79..81, 91, 92, 95, 96, 110..112, 114, 121..127, 131..136, 140, 142..145 | various | yes | drawn per branch | drawn once at the top (`rng_drawn`, up to the manager) |
| 141 Tormenta | `0x00e4ef4b` | yes | the particle visual draws it (`reconstructed/particles/visual.c`) | unchanged |

- Every branch the task listed (57/58, 62, 63, 64, 82, 100/101, 128..130, 137) is confirmed: the client draws, the
  native did not.
- Also found: 93/94 and the empty-slot class worlds 113, 115..120, 138, 139. 113, 116..120 and 138 are DATA-ACQ-002
  captures.
- The scene visuals 93/94: `mu_csw_visual` / `mu_login_visual` ran without a model and drew rand (93, 2 of 200
  cases at the first run). The client returns before the slot. They now run only with a model.
- No hook draws a rand in any class world (no `hook` label in 16,000 cases).

**Native.** `mu_obj_visual_flicker(world, has_model)` (`world_slots2_visual.c`) answers for the 56 class
registrations other than 141. The runtime calls it once:
- at the top of `handler_visual`, replacing the per-branch draws (79, 80/81, 142..145, 69..72, 114, 121, 0x83..0x88,
  0x8c and the Q worlds drew it already, in the same place relative to their slot);
- in the other class worlds at the point their visual hook runs.

The order relative to the other draws stays the client's: RenderObject (the custom slot) first, then this draw, then
the slot 0x34, then the attached effects. Static: `handler_visual` is the only caller of the class visuals.

**Not changed: the other worlds.** Worlds without a class registration (e.g. 6, 38, 40, 56) also draw this rand in
the client.
- Natively, Lorencia, Dungeon, Devias, Noria and Tormenta draw it in the particle generator (the particle visual).
- 0x25/0x28 (Kanturu flames) and 4/7/8 draw it in the object generator.
- The other worlds draw it in neither.

Changing them would touch the particle visual (another lane's code). The native keeps two generators (objects,
particles), so neither stream is the client's single stream anyway.

## 2. The slots (verified)

Every slot is `thiscall(handler, object, model, index)`, `ret 0xc`, and runs only for types 0..300 (the world
manager's range). Branches for higher types are left out. Logged as in RENDER-WORLDS-SLOTS (RenderBody/RenderMesh
with eight arguments, StreamMesh byte and body colour at each call). Direct model-colour writes are logged as colour
events. C: `reconstructed/objects/world_slots2_visual.c`, dispatched behind RENDER-WORLDS-SLOTS's classes.

| Class | Slot | Range | Body SHA-256 (16) | What it does (types 0..300) |
|---|---|---|---|---|
| Santa Village 62 | custom | `0x00e426cf..0x00e428af` | `652eb3f30f0fd271` | world 62; 0x10: meshes 0..2, colour (0, 0.5, 0.5), mesh 2 flags 0x44 |
| Imperial Guardian 69 | custom | `0x00dc8b33..0x00dc9efd` (jump table after) | `226a7215020453cd` | worlds 69..74 (four world tests); 0/1/3/0x2c/0x51 flag the after pass; 0x25, 0x29 (colour × `sin(T·0.002)·0.5+0.6`), 0x2f/0x30 (grey 1.2 / 1.1), 0x31/0x46, 0x37 body, 0x40 (red, 0x44 twice); 0x73/0x75: meshes, two v-scrolls written to the object (`(T % 25000)·±0.0004`), StreamMesh 1 and 3/4, TransformPosition on bone 9, CreateEffect(0x52d, sub 0, the object) while the frame is in (0, 0.4) and +0x60 is 0x64 (then 0x65); back to 0x64 in (7, 7.5) |
| Imperial Guardian 70 / 71 | custom | `0x00dd57fa..0x00dd5888` / `0x00dda8f5..0x00dda93e` | `91eaaa31abfc27fc` / `dbdde7ed56bb35b1` | own world test, then world 69's handler (`0x00dd8a3c(0x45)`) slot 0x38 |
| Imperial Guardian 72 | custom | `0x00de08df..0x00de0ff6` | `bc0397fff1333fd3` | worlds 72..74; world 69's slot first; then 0x60/0x61/0x64: grey `0x3e2e789e` (0.170382), body |
| Imperial Guardian 69 / 70 / 71 / 72 | after | `0x00dc9f33..` / `0x00dd5888..0x00dd5a75` / `0x00dda93e..0x00ddab2b` / `0x00de0ff6..0x00de11e3` | `e08983feeabc2ea0` (69's range overruns to 0x00dca120) / `67febcf73436b07e` / `388a29392fb7ef1e` / `a24498d3f3702c97` | one body behind each class's world test: 0/1/3/0x2c meshes 0, 1 and mesh 2 flags 0x42 at `(sin(T·0.0015)+1)·0.4+0.2`; 0x51 body |
| 82 | custom | `0x00e2caaf..0x00e2d4a8` | `3c32040be983344d` | worlds 82..90; 0xa/0x13/0x14/0x1f/0x21 flag the after pass; 0xf body with `(−T % 10000)·1e-4` (StreamMesh 0); 0x10 body at `(sin(T·0.002)+1)·0.3+0.4`; 0x46 meshes and red 0x44 twice; 0x48 mesh 0 and a 0x42 glow at alpha·0.1 with `Effect\chovolcano_02_R.jpg` 0x8144 |
| 82 | after | `0x00e2d4a8..0x00e2d681` | `ca97540e02779e66` | 0x10 pulsing body; 0xa/0x13/0x14/0x1f body; 0x21 mesh 0 flags 0x42 with `(T % 10000)·1e-4` (StreamMesh 0) |
| Arca War 92 (92, 96, 101, 111) | custom | `0x00d7c02e..0x00d7de81` | `2fcf1affb349b172` | Arca world test (its world list), then the base world's (handler +0x1c, `world − 1`) slot 0x38 through the registry `0x00ea594b`/`0x00ea4679`; its own cases are types > 300 |
| Arca War 92 | after | `0x00d7de81..0x00d7dece` | `ae873d71b2ae919e` | the base world's slot 0x3c the same way |
| Debenter 95 | custom | `0x00dbee19..0x00dbf27b` | `5c37fe33c1522ff0` | worlds 95/96; 0x38..0x43 answer yes; 0xb body (hidden 2), StreamMesh 2, mesh 2 three times with `−(T % 10000)·1e-4` (the remainder negated: differs from `(−T) % n` at INT_MIN); 0x25 body with `(T % 25000)·4e-5`; 0x32 mesh 0 lit by alpha, then `Object96\solight02_R.jpg` 0x81a7 at `|sin(T·0.001)|·0.4+0.3` (double product, fabs `0x01983660`) |
| Uruk Mountain 100 | custom | `0x00e702eb..0x00e70f4a` | `2e3f1d290cfe0507` | worlds 100/101; 0x10 (v nudged −0.005 and back on the object), 0x2c/0x48/0x49 hidden-mesh writes around mesh blocks (0x49: `(−T % 2000)·5e-4` four times), 0x31/0x39/0x3a/0x46/0x47 two bodies with a clamped pulse (`> 1` → 1, NaN kept), 0x54..0x56 body |
| Nars 110 | custom | `0x00e28bb2..0x00e28faf` | `c3985ed7005b4f99` | worlds 110/111; 0/0x4d mesh 0 under StreamMesh 0; 6; 0x11; 0x17/0x18 (hidden 2); 0x22..0x26 meshes 0..2 |
| Nars 110 | after | `0x00e28faf..0x00e295da` | `eb900c7937a8d6a2` | 0x22..0x26: StreamMesh 4 scroll, mesh 3 three times, two Chrome01 0x7f1f meshes (flags 0x20080, alpha 1) inside glPushMatrix/glPopMatrix (no value); 0x17/0x18 and 0x8e pulses; 6/0x10/0x11/0x15/0x16/0x1b/0x96 mesh 0 blend 0 |

The world tests (static, then compared): 62 `0x00e42f6d`; 69 `0x00dd38c5`, 70 `0x00dd897d`, 71 `0x00dde62f`, 72
`0x00de5519` (72..74); 82 `0x00e3068f` (82..90); 95 `0x00dbd14d` (95, 96); 100 `0x00e6efb9` (100, 101); 110
`0x00e2602d` (110, 111). Bitmaps (shared LoadBitmap sites): 0x8144 `0x01842420`, 0x81a7 `0x018410ae`, Chrome01 0x7f1f
`0x018220db`. In the Arca worlds the slots name the base world's bitmaps.

**Census: 125/144 → 142/144.** Left: Test Area 121's custom (`0x00d58bd8`, 1,972 instructions) and after
(`0x00d5a6cc`, 198) — §4.

**Native wiring.** `mu_class_slots` now also answers 62, 69..72, 82, 92, 95, 96, 100, 101, 110, 111.
- The runtime passes the world as the class; the four Arca worlds map to class 92.
- Imperial Guardian's 0x73/0x75 pose the object for bone 9 (more than 9 bones). Without them the effect is refused
  and counted; the draws and the latch stay.
- The 0x52d CreateEffect goes to the visual pass's existing effect consumer, as Vulcanus' sprites/particles do.
  No new hook.

## 3. Fidelity (DATA-ACQ-002 default draw, October 22 tour; base = main with RENDER-WORLDS-SLOTS, `83f8f1d9`)

Only the outer draw reaches a capture: none of the 17 slots is in a captured or warp-reachable world.

| Capture | Image mean \|Δ\| | Share > 24 | Static field differences vs live | Changed in the native dumps |
|---|---|---|---|---|
| 116 Deep Dungeon 1 | 2.592 → 2.511 | 0.0069 = | 0 → 0 | 231 light-grid words; 20 objects' light copy +0x1e8..0x1f0 |
| 117 Deep Dungeon 2 | 2.534 → 2.553 | 0.0051 → 0.0052 | 0 → 0 | 348 words; 31 objects |
| 118 Deep Dungeon 3 | 3.203 → 3.033 | 0.0126 → 0.0125 | 0 → 0 | 324 words; 19 objects |
| 119 Deep Dungeon 4 | 2.545 → 2.431 | 0.0089 = | 0 → 0 | 282 words; 16 objects |
| 120 Deep Dungeon 5 | 2.687 → 2.839 | 0.0068 = | 0 → 0 | 513 words; 61 objects |
| 138 Ignis Volcano | 3.825 = | 0.0300 = | 0 → 0 | 84 words; 12 objects |

Why: the move pass's flicker lights draw from the same object generator, after the visual pass's new draws.
- Deep Dungeon types 62..67: `(rand % 4 + 3)·0.1` (`deep_dungeon.c`). Ignis: the same form (`ignis_volcano.c`).
- So their AddTerrainLight strengths shift phase. The light grid and the objects' copy of it (+0x1e8) differ.
- No other OBJECT field and no draw count changes.
- The phase has no live reference (the live RNG state is not captured), so the image means can move either way.
- The live clock gives the same numbers.

**Byte identity:**
- The other 26 DATA-ACQ-002 captures are identical in PNG, OBJECT and light dumps. That includes 63, 113, 128..130
  and 137, which gained the draw but have no object-generator consumer at their arrival tiles.
- The October 22 tour is 14/14 identical, Raklion 57 included.
- The final code (with the slots) gives the same result as the outer-draw-only build.

## 4. Limits and next

- **Test Area 121's two slots.** The custom slot writes 0.5 into the global per-vertex light buffer `0x06fd0918`
  (mesh · 0xea60 + vertex) for types 6..12. It also emits 28 bone-placed CreateParticle calls and seven rand draws
  across types 0x10..0x15, plus 0x12affa4 helper calls.
- Natively the vertex-light buffer has no consumer. Natively a class's custom and after slots come as a pair. Both
  stay missing; 121 has no capture and is not warp-reachable.
- **Non-class worlds** draw RenderObjectVisual's rand only in the particle generator (0..3, 0x8d) or not at all (§1).
- **Ferea's door state** stays an explicit input (constructed 0, server-set).
- Types above 300 in these slots are never passed by the world manager.
- Arca War's base world is the production `world − 1`. The validator does not try other handler bases.
