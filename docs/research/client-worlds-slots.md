# RENDER-WORLDS-SLOTS: the world classes' custom render, after render and invisible move

Target: the executable SHA-256 `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`. The text and
second-image-data captures are pinned in `scripts/pins.py` (capture09/run10). Method: static disassembly of the
pinned text, then compiled authored C compared with the original instructions under the strict Unicorn machine
(`scripts/validate_worlds_slots.py`).
Labels: **verified** = instruction-compared, **static** = read from the disassembly only, **inference** = reasoning.

With RENDER-WORLDS-S/S2/S3, every class's primary create/move/visual methods are native (144/144, 48/48). This lane
takes each class's other three slots: the custom render (vtable +0x38), the after render (+0x3c) and the
invisible-sector move (+0x1c). It also covers the hook chain around the class slot, and Loren Market's RNG draw.

## 1. Census (all 48 classes × 3 slots)

The table lists, per slot: the entry, the instruction count, and the status.
- Counts come from a scan to the first `ret` followed by padding. 122's custom slot is the exception: its `ret` is
  followed by a jump table, so its real end `0x00e553e4` is pinned.
- `V <lane>`: native and instruction-compared, by that lane.
- `T`: trivial (answers no and draws nothing, or empty), compared under Unicorn by this lane's `trivial` family.
  Native needs no slot for these.
- `base`: the base class methods (`0x00d5cc8e` custom answers no, `0x00d5cc60` after is empty, `0x00d5cbbc`
  invisible move answers no).
- `M`: missing.
- Capture: C = DATA-ACQ-002 live capture, E = earlier live read, N = not reachable by warp.
- Classes are ordered by player reach: captured first.

| Class | Worlds | Capture | Custom 0x38 | After 0x3c | Invisible move 0x1c |
|---|---|---|---|---|---|
| Vulcanus | 63 | C | `0x00e8f515` 741, V SLOTS | `0x00e8ff20` 78, V SLOTS | base, no (T) |
| Loren Market | 79 | C | `0x00e6ce2d` 154, V SLOTS | `0x00e6d062` 200, V SLOTS | base, no (T) |
| Acheron | 91 | C | `0x00d6c427` 2078, V AFTER2 | `0x00d6d3d7` 1066, V AFTER2 | base, no (T) |
| Ferea | 112 | C | `0x00de8a10` 1333, V SLOTS | `0x00de9eab` 381, V SLOTS | base, no (T) |
| Nixies Lake | 113 | C | `0x00e347a8` 1780, V AFTER2 | `0x00e3628c` 762, V AFTER2 | base, no (T) |
| Deep Dungeon 1..5 | 116..120 (one class each) | C | base, no (T) | base, empty (T) | base, no (T) |
| Swamp of Darkness | 122 | C | `0x00e54752` 846, V SLOTS | `0x00e555d2` 223, V SLOTS | base, no (T) |
| Kubera | 123..127 | C | `0x00e1a5df` 1054, V SLOTS | `0x00e1b6f5` 542, V SLOTS | base, no (T) |
| Abyss of Atlans 1/2/3 | 128/129/130 | C | `0x00d5d2f6` 168 / `0x00d5ef96` 164 / `0x00d606da` 168, V AFTER | `0x00d5d5ad` / `0x00d5f23a` / `0x00d60991` 94, V AFTER | base, no (T) |
| Scorched Canyon | 131 | C | `0x00e43842` 496, V AFTER2 | `0x00e43fab` 286, V AFTER2 | base, no (T) |
| Red Smoke Icarus | 132 | C | `0x00e00d4c` 92, V AFTER2 | `0x00e010b6` 645, V AFTER2 | base, no (T) |
| Temple of Arnil | 133 | C | `0x00d80cea` 967, V AFTER3 | `0x00d81c49` 406, V AFTER3 | base, no (T) |
| Gray Aida | 134 | C | `0x00d84d0e` 65, V AFTER2 | `0x00d868f7` 216, V AFTER2 | base, no (T) |
| Old Kethotum | 135 | C | `0x00e3ae5e` 1241, V AFTER2 | `0x00e3c739` 307, V AFTER2 | base, no (T) |
| Burning Kethotum | 136 | C | `0x00d94eef` 2436, V AFTER2 | `0x00d97384` 865, V AFTER2 | base, no (T) |
| Kanturu Underground | 137 | C | `0x00e092f4` 1159, V AFTER2 | `0x00e0ab2a` 535, V AFTER2 | base, no (T) |
| Ignis | 138 | C | `0x00e05f25` 1150, V AFTER2 | `0x00e0709e` 49, V AFTER2 | base, no (T) |
| Bloody Tarkan | 140 | C | `0x00d9a2ed` 619, V AFTER2 | `0x00d9ac50` 220, V AFTER2 | base, no (T) |
| Twisted Karutan | 142 | C | `0x00e677a9` 1428, V AFTER2 | `0x00e68c6a` 796, V AFTER2 | `0x00e673b4` 43, **V SLOTS** |
| Kardamahal | 143 | C | `0x00e0f4bc` 2333, V AFTER3 | `0x00e118fd` 304, V AFTER3 | `0x00e0e539` 47, **V SLOTS** |
| Swamp of Destruction | 144 | C | `0x00e46e94` 906, V AFTER3 | `0x00e48f1c` 122, V AFTER3 | `0x00e46a9f` 241, **V SLOTS** |
| Raklion | 57, 58 | E | `0x00e949f8` 1994, V RAKLION (was V A: flags and first meshes only) | `0x00e96536` 198, V RAKLION (121's, was V A) | base, no (T) |
| Karutan | 80, 81 | E | `0x00e14596` 969, V A | `0x00e1543e` 502, V A | base, no (T) |
| Character scene | 93 | E | `0x00dab4d7` 79, V A | `0x00dab5ed` 95, V A | base, no (T) |
| Login scene | 94 | E | `0x00e254bb` 113, V A | `0x00e25639` 474, V A | base, no (T) |
| Tormenta Island | 141 | E | `0x00e4cbd7` 3081, V AFTER3 | `0x00e4f952` 900, V AFTER3 | `0x00e4bfff` 43, V (object render) |
| Event square | 114 | N | `0x00e1f6ca` 154, V SLOTS | `0x00e1f8ff` 200, V SLOTS | base, no (T) |
| Duel Arena | 64 | N | `0x00dc6a2e` 19, T (asks `0x00dc6bfa`, answers no) | `0x00dc6a5b` empty, T | base, no (T) |
| Deep Dungeon class 115 | 115 | N | base, no (T) | base, empty (T) | base, no (T) |
| Santa Village | 62 | N | `0x00e426cf` 133, M | `0x00e428af` empty, T | base, no (T) |
| Debenter | 95 | N | `0x00dbee19` 279, M | base, empty (T) | base, no (T) |
| Uruk Mountain | 100 | N | `0x00e702eb` 793, M | base, empty (T) | base, no (T) |
| Imperial Guardian | 69 | N | `0x00dc8b33` 1468, M | `0x00dc9f33` 131, M | base, no (T) |
| Imperial Guardian | 70 / 71 | N | `0x00dd57fa` 48 / `0x00dda8f5` 30, M (both forward to world 69's slot 0x38) | `0x00dd5888` / `0x00dda93e` 131, M | base, no (T) |
| Imperial Guardian | 72 | N | `0x00de08df` 432, M | `0x00de0ff6` 131, M | base, no (T) |
| World 82 | 82 | N | `0x00e2caaf` 638, M | `0x00e2d4a8` 120, M | base, no (T) |
| Arca War | 92, 96, 101, 111 | N | `0x00d7c02e` 2035, M | `0x00d7de81` 28, M | base, no (T) |
| Nars | 110 | N | `0x00e28bb2` 262, M | `0x00e28faf` 396, M | base, no (T) |
| Test Area | 121 | N | `0x00d58bd8` 1972, M | `0x00d5a6cc` 198, M | base, no (T) |
| Boss Battle | 139 | N | `0x00d9c19a` 7, V AFTER2 | `0x00d9c1b4` 6, V AFTER2 | base, no (T) |
| Aquila's Temple | 145 | N | `0x00d76059` 1816, V AFTER3 | `0x00d77d18` 272, V AFTER3 | `0x00d7565d` 13, **V SLOTS** |

**Totals: before this lane, 49/144 of these slots were native and compared** (the A worlds, AFTER, AFTER2 and
AFTER3, plus Tormenta's 0x1c). Note that `docs/research/world-handler-coverage.json` still listed only 9 of them;
it now records all. **After: 125/144.** This lane adds:
- 12 custom/after slots of six classes;
- 4 invisible-move slots;
- 60 trivial/base slots, compared and needing no native code: 43 base 0x1c, 7 custom, 10 after.

**Missing: 19, none of them in a captured or warp-reachable world:**
- 62 custom;
- Imperial Guardian 69..72 (8 slots; the four after slots are one body, and 70/71's custom slots forward to 69's
  1,468-instruction slot);
- 82 (2);
- Arca War 92 (2);
- 95 custom and 100 custom;
- Nars 110 (2);
- Test Area 121 (2).

Natively a class's custom and after slots come as a pair, because `mu_class_slots` turns on both the first-pass
callback and the after pass.

## 2. The slots (verified)

Every slot is `thiscall(handler, object, model, index)`, `ret 0xc`. It starts with its class's world test on
`[0x01cf15fc]`, except Ferea, which has none (as 145's custom). Logged as in AFTER2/AFTER3:
- RenderBody `0x00966def` / RenderMesh `0x00966e4a` with eight arguments;
- the StreamMesh byte +0x94 and the body colour +0x54 at each call;
- the CreateSprite/CreateParticle requests (Vulcanus).

The world manager calls the slots for types 0..300 only, so these branches are left out: Ferea's 0x607/0x8c6/0x8c7
and Vulcanus' 0x842..0x848. `glColor3fv(model +0x54)` changes no value. C:
`reconstructed/objects/world_slots_more_visual.c`. The slot helpers moved, unchanged, into
`world_visual_slots.h`, shared with `world_slots_visual.c`.

| Class | Slot | Range | Body SHA-256 (16) | What it does |
|---|---|---|---|---|
| Loren Market 79 / Event square 114 | custom | `0x00e6ce2d..0x00e6d062` / `0x00e1f6ca..0x00e1f8ff` | `aa98d5c680ad790a` / `54cfd6fadc327b77` | 8, 0x1e: `+0xa = 1`, answer yes, no draw; 0x32: meshes 0/1/3, mesh 2 blend −2 at `BL·min(wave(−1.2)+0.4, 1)` |
| | after | `0x00e6d062..0x00e6d345` / `0x00e1f8ff..0x00e1fbe2` | `24de4a06fc59ab78` / `e18fe2afff65875a` | 8: meshes 2..4 (u, v 0), mesh 1 flags 0x42 v-scroll `(−T % 10000)·0.001`, mesh 0 flags 0x42 `sin` waves; 0x1e: RenderBody; 0x44: mesh 0 flags 0x42 |
| Vulcanus 63 | custom | `0x00e8f515..0x00e8ff20` | `77d616ffc22bdbf5` | 0xf: StreamMesh 0, body v-scroll; 0x43/0x44: StreamMesh 1 body, mesh 0, red 0x44 glow (alpha 0.2), two sprites 0x7ef7 on bone 6 (origin and −350 z), scale·5; 0x43: frame 35..37 sets `+0x54 = −1`; at frames 1..2 with `+0x54 ≠ 1` the frame resets to 1 and `rand%1000 < 2` opens (1); spark 0x7f5a from bone 4 (−150, 0, 0) at frames 35..50, sub 0x3f; 0x44: two `rand%20 − 30` offsets, spark sub 0x12 at frames 7..13; 0x46: answer yes |
| | after | `0x00e8ff20..0x00e90043` | `3b7ed0e85550740a` | 0x10: RenderBody blend 0, light `(sin(T·0.002)+1)·0.5`; 0x46: RenderBody |
| Ferea 112 | custom | `0x00de8a10..0x00de9eab` | `bb8a4ef7bee0c831` | 0x27 door: meshes at alpha 1, v ± 0.1 for actions 1/2 written to the object, StreamMesh 3; 0x2b/0x33/0x72 answer yes; 0x7b statue: `hs_statueB` 0x8225 while the handler's door state (+0x48) is 2 or 3; 0x4b/0x51, 0x57/0x5f, 0x73, 0x8a, 0x99..0x9b glows and scrolls (one double-precision blend in 0x9a) |
| | after | `0x00de9eab..0x00dea4d4` | `a056ef94e063a7fc` | 0x2b/0x33 bodies; 0x4b/0x51, 0x57, 0x72, 0x99 (the client passes U as v for mesh 2), 0x9b scrolls `(T % n)·1e-4·k·2 − 1` |
| Swamp of Darkness 122 | custom | `0x00e54752..0x00e553e4` | `28a5637fa04ad931` | 0x27/0x29/0x70 answer yes; 0x3b, 0x58, 0x6b..0x6d glows (1/3/3/2), 0x7b..0x80 glows, 0x7e Chrome09 0x8245 reflection (flags 6), 0x83..0x85 crocodiles: body and three `hsCrocodileA_R` 0x8273 glows |
| | after | `0x00e555d2..0x00e55913` | `0a095ebf9725fa6e` | 0x27/0x29, 0x58/0x6b, 0x6c glows; 0x70: RenderBody at `wave(−0.6)·0.5+0.5` |
| Kubera 123..127 | custom | `0x00e1a5df..0x00e1b5fb` | `9110a246bbbd63f5` | 15 types answer yes; 0x2f/0x34 gem mesh 5/7 scrolls while action 1 (backwards) or 3 plays from frame 3 to the last key; 0x4c, 0x8c glows; 0x71..0x75 the world's crystal bitmaps (handler +0x1c..+0x34), then chrome 0x829a with flags 0x20000; 0x8b handler +0x24 |
| | after | `0x00e1b6f5..0x00e1bef1` | `fb8afd251e261f9c` | bodies; gates 0x6d/0x76..0x79 (per-type colour bitmaps on meshes 8/9, glow on 0xd); 0xa0 with the handler's +0x38..+0x48; 0x86 glows |
| Twisted Karutan 142 / Kardamahal 143 / Swamp of Destruction 144 | invisible | `0x00e673b4..0x00e67447` / `0x00e0e539..0x00e0e5d6` / `0x00e46a9f..0x00e46e94` | `3bee1d43aabaea50` / `2b33635e3352636b` / `2040a4ed9135dcf6` | TestFrustrum2D(x·0.01, y·0.01, range) for their own types (0xa0/0xa1; 0x71/0x80 after a null-object test; 68 types, 0x8d listed twice) |
| 145 | invisible | `0x00d7565d..0x00d75679` | `7e0687d9479c4efb` | answers the object's last render visibility (+0xb) |

Body hashes are the first 16 hex digits of the SHA-256 of the range in the pinned text. The validator report's `bodies` also hashes the trivial bodies (62/64 after `d2d92841c8cbf889`, the base after the same, 64 custom `5f5cfddef3393279`, base custom `6c2b4d37b00242c4`, base invisible move `8fe906e7160a7e38`).

**Handler state (verified).**
- Kubera's slots read the handler words +0x1c..+0x48. The class loader `0x00e18efb` (slot 0x24) writes them per world
  0x7b..0x7f after 61 LoadBitmap calls; the constructor `0x00e18da5` clears +0x1c..+0x24 and +0x38..+0x48.
  The C keeps the loader's table (`mu_slots_more_handler`).
- Ferea's statue reads handler +0x48 field 0 (`0x00dee9ee`), the door state of RENDER-WORLDS-Q2's
  `mu_q_handler.ferea_state`. It is constructed 0, and its packet-driven writer is not ported.

**Bitmaps (verified).** `mu_world_slot_bitmap` / `mu_world_slot_bitmaps` now also answer:
- Kubera's 61 registrations, all under `Object124`, wrap 0x2900 for the ten colour sheets;
- Ferea's `Object113\hs_statueB.jpg` (loader `0x00de5977`);
- Swamp of Darkness's `Object123\hsCrocodileA_R.jpg`, from the shared site `0x0184187c`;
- the global Chrome09 0x8245.

Native loads them as model texture extras, as AFTER2 does.

## 3. Native wiring

- **Dispatch.** `mu_class_slots(world)` covers the new classes (Kubera's five worlds map to class 123).
  `mu_world_after_native` therefore runs the whole `0x016d6949` for 63, 79, 112, 122 and 123..127, and its world
  gate lists them all. 114's gate is closed: Event square's flagged 8/0x1e objects are skipped in the first pass
  and never drawn, as in the client.
- **Vulcanus' statues** read posed bones in the custom render, as RenderObject's Animation posed them before it.
  - `class_custom_call` poses the object (models with more than 6 bones) and passes `visual_bone`.
  - The slot's sprite/particle requests go at once to the visual pass's existing consumer (`consume_visual`) and
    leave the slot log.
  - Without enough bones they are refused and counted in `draw_unsupported`. The draws, rand draws and object
    writes stay.
- **Invisible move.** `mu_obj_handler_moves` answers for 142..145. The production step handler asks it, and no
  longer needs a frustum for 145.

## 4. The hook chains around the class slot (verified: no-ops in every class world)

AFTER verified CreateObject's and MoveObject's chains (`chain_predicates`, `chain_noop`). This lane runs every hook
the client calls around the world manager's class slot in the other three methods. Each run covers all 57 class
registrations, on a poisoned object and model (`chains` family, 1,881 runs): every hook answers 0 and writes
neither the object nor the model.

- **RenderObjectVisual `0x017f9758` default branch (`0x017fcb5c..`):** `0x009db8b1`, `0x00def747`, `0x00d8e640`,
  `0x00dfc095`, `0x00d622dd`, `0x00dac0a2`, `0x00e75089`, `0x00e7df87`, `0x00e84941`, `0x00d5404b` on the static
  `0x01ec8eb8` (getter `0x00d53c8f`, built by its constructor `0x00d53c61`), the singleton's slot 0x34
  `0x00db7656`, `0x00e3116a`, `0x00e5f94b`. Then the world manager `0x00ea2dc1` calls the class's slot 0x34.
- **Custom render `0x017f76ec` (`0x017f8f15..`, arguments model, object, flag):** `0x00deff29`, `0x00d8ea2c`,
  `0x00dfc3cf`, `0x00d63d6c`, `0x00dac3c1`, `0x00e760aa`, `0x00e7ed6f`, `0x00e855f1`, `0x00d54e48`, singleton
  slot 0x38 `0x00dba13d`, `0x00e31985`, `0x00e6021d`.
  - `0x00a9c6c9` (on `0x01d1e738`) is not a world hook. It is the render registry: four run-time-registered
    renderers' +0x1c. RENDER-OBJECT already models it (`mu_obj_draw_inputs.registry`), so it is not in the family.
- **After chain `0x016d67c7`:** `0x00e765eb`, `0x00e7f718`, `0x00e86aac`, `0x00d550ea`, singleton slot 0x3c
  `0x00dbc1b1`, `0x00e321bb`, `0x00e60ab0`, the manager `0x00ea306c`, then `0x00d63f5f`.
- The singleton `0x00db747f`'s constructor needs the heap. Its slots run on the fake handler, as AFTER's
  `chain_noop` ran its slots 0x2c/0x30. Each returns at its own world test.

So the native dispatch's direct call of the class slot is complete for all 48 classes: no chain code was needed.

## 5. Loren Market's outer RenderObjectVisual draw (verified, changed)

`0x017f9758` looks up the object's model (`0x00966cc4` → `0x00eaa8cf`) and returns if there is none. Otherwise it
draws `rand() % 30` (`0x017f9797`) before its world switch. For world 0x4f the switch takes the default branch to
the hooks and the class slot 0x34. The native 79 branch drew no rand, unlike Event square (114) and the other
primary-visual worlds. It now draws it. 79 is captured. Its capture output changes only by this draw and by the
slots above (§6).

The same outer draw is also absent from these native branches (static reading, not changed here; each changes the
RNG phase of its world):
- 57/58 Raklion;
- 62 Santa Village;
- 63 Vulcanus;
- 64 Duel Arena;
- 82;
- 100/101 Uruk/Arca;
- 128..130 Abyss;
- 137 Kanturu Underground.

A later lane should check each branch against `0x017f9758`'s model gate.

## 6. Fidelity

Base = origin/main `b8645181` (its `mu-world`, taken once), lane = `b2ac02f0` (the lane code; the later main merge
brought only combat code). Inputs: the DATA-ACQ-002 arrival tiles (32 captures, 25 steps, 1722 × 1048, default draw,
`MU_LANG_DIR` as AFTER5) and the October 22 fourteen-view tour. Comparison: PNG frames, comparison images, OBJECT dumps
and light dumps per map. The live clock ran for the worlds this lane can change.

| Capture | Image mean \|Δ\| (default / live clock) | Share > 24 | Static field differences vs live | First-pass draws | Why it changed |
|---|---|---|---|---|---|
| 123 Kubera | **4.321 → 2.037** / 4.321 → 1.967 | 0.0474 → 0.0105 | 0 → 0 | 108 → 101 | 7 flagged objects leave the first pass; the crystals, gates and gems draw with their slot bitmaps |
| 122 Swamp of Darkness | **1.709 → 1.543** / 1.704 → 1.528 | 0.0113 → 0.0086 | 0 → 0 | 103 → 100 | the custom glows and after-pass bodies |
| 79b Event square (world 79) | **3.604 → 3.545** / 3.637 → 3.568 | 0.0171 → 0.0165 | after-character **3 → 0** | 122 → 119 | types 8/0x1e flagged (+0xa) and drawn by the after slot |
| 79 Loren Market | 4.361 = (frame identical) / 4.382 = | 0.0389 = | after-character **1 → 0** | 99 → 98 | one type-0x1e object gets +0xa (as live); the outer rand draw changes no dumped field and no pixel at this tile |
| 142 Twisted Karutan | 7.145 → 7.143 / 6.394 → 6.393 | 0.0473 = | 0 → 0 | 803 = | slot 0x1c: 66 objects of invisible sectors (types 0xa0/0xa1 and their neighbours' lights) now move; their light copy +0x1e8 changes |
| 143 Kardamahal | 10.299 = / 10.236 = | 0.0857 = | 0 → 0 | 280 = | slot 0x1c: 11 objects move (frame +0xd0, light copy) |
| 144 Swamp of Destruction | 12.391 → 12.388 / 12.391 → 12.388 | 0.0229 → 0.0230 | 0 → 0 | 201 = | slot 0x1c: 2,631 objects of 68 types animate off screen (frame +0xd0) |

Static field differences against the live capture stay 0 everywhere, except the after-character fields above, which
go to 0. Near-hero frame-light means change by < 0.004 in 142..144, from the lights of the objects that now move.

**Byte identity (default draw):**
- The other 25 DATA-ACQ-002 captures are identical in PNG, OBJECT and light: 6, 38, 40, 56, 63, 91, 112, 113,
  116..120, 128..138, 140.
- 63 Vulcanus and 112 Ferea have slot types in their populations, but none is visible at the arrival tile (OBJECT
  +0xb, verified on the lane's dump). Their frames and dumps are identical.
- The October 22 tour is **14/14 identical** in PNG, OBJECT and light.

## 7. Checks

See the [handoff](../handoffs/RENDER-WORLDS-SLOTS.md) for counts and wall times.

## 8. Limits and next

- 19 slots are missing (§1): 62, Imperial Guardian 69..72, 82, Arca War 92, 95, 100, Nars 110 and Test Area 121.
  None is in a captured or warp-reachable world.
- Ferea's door state (handler +0x48) is constructed 0 natively. Its writer is packet-driven (Q2 §4), so the statue
  bitmap shows only through an explicit input.
- Vulcanus' flares and sparks need posed bones (models with more than 6 bones); otherwise they are refused and counted.
- The outer RenderObjectVisual draw of the branches listed in §5.
- Types above 300 in the slots (Ferea 0x607/0x8c6/0x8c7, Vulcanus 0x842..0x848) are never passed by the world
  manager.
