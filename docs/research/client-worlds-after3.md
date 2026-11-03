# RENDER-WORLDS-AFTER3: the custom/after render slots of 133, 141, 143, 144 and 145

RENDER-WORLDS-AFTER3, 2026-10-29 / 2026-11-03. This continues [AFTER2](client-worlds-after2.md), which covered the
slots of 91, 113, 131, 132, 134..140 and 142. Target `main.exe` SHA-256
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`; capture09 text and run10 data are pinned in
`scripts/pins.py`.

Labels: **verified** = compared with the original instructions under Unicorn; **static** = read from the
disassembly; **inference** = neither.

## 1. Slots, world tests and loaders (verified)

The slot addresses come from the class vtables (`scripts/world_handler_coverage.py`). Every slot is
`thiscall(handler, object, model, 0)` and draws with RenderBody `0x00966def` / RenderMesh `0x00966e4a`, as in AFTER2.

| World | Custom 0x38 | After 0x3c | Bitmap loader 0x24 | World test |
|---|---|---|---|---|
| 133 Temple of Arnil | `0x00d80cea` | `0x00d81c49` | `0x00d807f5` | `0x00d83ada` (0x85) |
| 141 Tormenta Island | `0x00e4cbd7` (types 0x7d..0x9a through the table `0x00e4eed3`) | `0x00e4f952` | `0x00e4c08c` | `0x00e54061` (0x8d) |
| 143 Kardamahal | `0x00e0f4bc` | `0x00e118fd` | `0x00e0e5d6` | `0x00e136f3` (0x8f) |
| 144 Swamp of Destruction | `0x00e46e94` | `0x00e48f1c` (also needs the live byte +0) | `0x00e464be` | `0x00e4bb8d` (0x90) |
| 145 | `0x00d76059` (no world test, no null test; alpha +0xdc < 0.9 answers handled with no draw) | `0x00d77d18` | `0x00d75679` | `0x00d79e40` (0x91) |

Per-type behaviour (static, then verified by the families below):

- **Water bodies.** Each class has a water body: 133 types 6/0xaa, 143 type 0. It sets the object light +0xec to
  0.2 and StreamMesh to 0, then draws `RenderBody(0x42, ..., u = −t, v = wave(−1.5)·0.011 − t)` with
  `t = (int)WorldTime % N · k` (133: 1,000,000 · 1e-5; 143: 500,000 · 2e-5). 143 also clears +5/+6.
- **Water bitmaps.** Each class has 32 water bitmaps `Object<world+1>\wt%02d_R.jpg` (GL_LINEAR, GL_REPEAT),
  registered in a loop and bound as `base + (int)(WorldTime · 0.015) % 32`:

  | World | Base | Type (after slot) |
  |---|---|---|
  | 133 | 0x8320 | 0x8f |
  | 141 | 0x848e | 0x41 |
  | 143 | 0x8589 | 0x1c |
  | 144 | 0x8348 | 0x40 |
  | 145 | 0x838a | 0x31 |

- **133 StreamMesh walk.** Types 0x91/0x94 set StreamMesh to k before mesh k. The u/v scroll is
  `(int)WorldTime % 1200 · 0.00083` with factors 2, −4, 1, −2, 1. 0x94 stops after mesh 3 and leaves the byte set.
- **143 colour copies.** The custom slot saves and restores the body colour through a vector object
  (`0x0095ea8e` .. `0x0095eda9`) around its textured meshes. The values are exact copies.
- **144 colour copies.** Types 0x89/0x8a save, set grey and restore around the 0x8341/0x8342 meshes. Types 0x86/0x87
  copy the colour out and back with no change in between.
- **145 type 0x99.**
  - Object +0x188 is a fade value: +0.03 while the model action is not 0, otherwise −0.01. It is then clamped
    with `0x0184f93f` (max with 0) and `0x0184f927` (min with 1).
  - The glow mesh 1 uses that value as its alpha and light.
  - Model action 2 with `(float)(short)` model +0xb4 > 1 plays PlayBuffer 0x5b4. Model +0xb4 is Animation's
    `(short)(int)frame` (`0x012b5128`).
- **141 type 0x2c** is drawn only while `frame ≥ 1` and `keys > frame`. `keys` is the short at action record +8
  of the object's action (model +0x30 table). Inference: this is the BMD key count; native passes
  `bmd.actions[a].keys`.
- **143 after type 0x71** calls AddTerrainLight `0x016cacfc(x, y, L·(1, 0.2, 0.1), 3, frame light)` with
  `L = (rand() % 4 + 3) · 0.1 · 0.4 + 0.4`. It draws nothing.
- **Unreachable types.** Types above 300 are never passed by the world manager (`0x00ea2f07`/`0x00ea306c`) and
  are not reconstructed: 133's 0x199..0x19e and 141's 0x40e.

The bitmap paths come from running each loader as client code (`--dump-loaders`). The folders are `World+1`
(`Object134`, `Object142`, `Object144`, `Object145`, `Object146`); 141's own files are `Object142\so*`. The files
exist in the installed client.

C: `reconstructed/objects/world_slots_visual.c`, section "RENDER-WORLDS-AFTER3". `mu_slot_model` gains
`action_frames`, `rand_fn` and `rand_context`. `MU_WORLD_SLOT_BITMAPS` is 36.

## 2. Native wiring

All five worlds are now `mu_class_slots` worlds. The first pass takes slot 0x38's answer and draws its meshes, and
the second pass draws slot 0x3c. 133 passes the after gate's 0x7a..0x85 range; 141..145 pass through the class byte.

`mu_objects_runtime.c` changes:
- the bitmap extras take up to 36 per type;
- `slot_model` fills the key count and rand;
- `slot_fields` writes model +0xb4;
- the first pass sends slot sounds to the object sound hook.

The after pass counts 143's render-time terrain light in `draw_unsupported`; there is no render-time light
consumer.

## 3. Checks

`scripts/validate_worlds_after3.py --cases 1000 --mutations` (registered as `validate_worlds_after3`):

- 10 slot families of 1,000 cases each. The first 301 cases sweep types 0..300; the rest draw case types, with
  145's 0x99, 141's 0x2c and 143's 0x71 weighted up.
- Leaves recorded: PlayBuffer, AddTerrainLight and rand (shared MSVC rand).
- The `loaders` family (212 cases) runs the five loaders with LoadBitmap recorded and sprintf formatted by the stub.
  Every bitmap a slot names must be registered with the same path, filter and wrap.

Result: **10,212 cases equal, 0 mismatches, 0 stops; 49/49 compiled mutants detected** (lowest count 1, both in
the loader family; the lowest slot-family counts are 3). Portable: `reconstructed/objects/test_worlds_after3.py`
(7 + 1 private).

## 4. Fidelity (DATA-ACQ-002, 32 captures, base origin/main `d5ffde0a` vs lane)

| Capture | Default clock | Live clock (`live_time`) |
|---|---|---|
| 143 Kardamahal | 10.911 → **10.299** | 10.911 → **10.236** |
| 144 Swamp of Destruction | 12.395 → 12.394 | 12.396 → 12.394 |
| 133 Temple of Arnil | 1.028 → 1.028 (frame changed) | 1.024 → 1.024 (frame changed) |
| 140 Bloody Tarkan / 142 Twisted Karutan | 5.225 / 7.145, identical | 5.225 / 6.394, identical |
| the other 27 | PNG, OBJECT and light dumps byte-identical | not run |

144's OBJECT dump differs only in +0xb (visible) and +0x1e8 (body-light copy) of its 29 type-0x20/0x40 objects,
which the after pass now draws. The live comparison's field counts are unchanged, velocity included (144: 40,
142: 3). There are no captures for 141 or 145.

## 5. Limits and next (RENDER-WORLDS-AFTER4)

- The own world cases and the true branches of the default chain of the draw-first predicate `0x017fcd18` (see
  [Q2](client-worlds-q2.md) §2, §8).
- The writer of the velocity (+0xbc) differences of 140 and 142..144.
- No render-time terrain-light consumer for 143 type 0x71.
- The meaning of action record +8 is inferred.
- 141/145 are validated with synthetic state only (no captures).

```sh
tools/python/bin/python scripts/validate_worlds_after3.py --cases 1000 --mutations --output <json>
tools/python/bin/python scripts/validate_worlds_after3.py --dump-loaders
```

[Handoff](../handoffs/RENDER-WORLDS-AFTER3.md).
