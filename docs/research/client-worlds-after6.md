# RENDER-WORLDS-AFTER6: the registry's mouse and camera handlers, the sprite mark, the attach's dt-0 update

RENDER-WORLDS-AFTER6, 2026-11-04. This continues [AFTER5](client-worlds-after5.md) §2 (tick handlers 4, 6 and
8), [SPRITE-DRAW-001](client-sprite-draw.md) §5 (the "frustum test" of `0x01692887`) and
[RENDER-EFFECTS-008](client-render-effects-008.md) §4 (bone −1 following, `0x0129f4cb`). Target `main.exe`
SHA-256 `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`; capture09 text and run10 data are
pinned in `scripts/pins.py`.

Labels: **verified** = compared with the original instructions under Unicorn; **static** = read from the
disassembly; **inference** = neither.

## 1. Tick handlers 4, 6 and 8 (verified)

AFTER5 named all three "the hero box collision `0x018500bf`". The disassembly says otherwise: `0x018500bf` is the
segment-against-OBB test (six separating axes `0x01850d88`, as NATIVE-NPC-001's `mu_pick_segment_obb`), and the
three handlers feed it different segments.

**`0x018500bf`'s globals (static).**
- `0x0bdc5984` is MousePosition, written from the camera matrix `0x0bdc5918` at `0x0184a0ed`.
- `0x0bdc5990` is MouseTarget, written by `0x01849f08` from the mouse x/y `0x0bdc5ad8`/`0x0bdc5adc`.
- `0x0bdc5ab4` is CameraPosition.

These are the same names the camera port (`reconstructed/camera`, `mu_client_view`) already uses.

| Id | Handler | By extra[0] |
|---|---|---|
| 4 | `0x00ce1947` | 0: the mouse segment meets the object's OBB `+0x31c` → back; 1, 3: at the end → back; 2: the mouse is **not** over it → back |
| 6 | `0x00ce1e4b` | 0: over it and latch `+0x34` = 0 → `+0x34` += 1, then back; otherwise `+0x34` = 0. 1, 3: at the end → back; 2: at the locked end (keys − 1 when the record's `+0xa` is set) → back |
| 8 | `0x00ce23ad` | (no step) the camera → hero fade below |

"Back" is SetAction(extra.back()), and "at the end" is AFTER5's frame ≥ keys − speed. Other steps do nothing.

**Handler 8, the fade (static, then verified).** It runs only with exactly seven extras: size x, y, z; offset x,
y, z; rate. The rate is the SetAction half's alpha rate, from AFTER5. The hero is `[[0x0a39d754] + 0x33ac]` x, y, z.
1. **Coarse box.** start = position − (s/2, s/2, 0) + offset, with s = 2 · max(x, y, z), axes (s, 0, 0),
   (0, s, 0), (0, 0, max). The max is `0x0184f93f` twice. When the segment CameraPosition → hero misses this box,
   nothing is written.
2. **The object's box.** Eight corners (±x·scale/2, ±y·scale/2, 0 or z·scale), each plus offset · scale. Each is
   turned by `0x0185c113(out, in, angle +0x164)`, a degree rotation with the CRT sin/cos wrappers, and then
   placed at the position `+0x158`.
3. **Faces.** `0x0184f957` sets the nearest parameter `0x0bdc58c8` to 9,999,999. Six face normals come from
   FaceNormalize `0x00d01206` on corners (0,1,3) (4,5,6) (0,4,6) (1,5,7) (2,3,7) (0,1,5). Then
   CollisionDetectLineToFace `0x0184f96c(camera, hero, 4, a, b, c, d, N, 0)` tests the quads (0,1,3,2)
   (4,5,7,6) **(0,4,6,3)** (1,5,7,3) (2,3,7,6) (0,1,5,4) in that order, stopping at the first hit.
   - The third quad closes on corner 3, not 2. That is the client's list.
   - It only matters when the segment ends inside the box and leaves through that face (the validator places
     the hero or the camera inside the box to reach it).
4. **Write.** A face hit sets `+0xd8` (alpha target) to 0.1, otherwise 1.0. The alpha step then fades the object
   at the handler 8 rate.

The live tables use 4 and 6 nowhere; world 145 uses 8 on 15 types (13, 14, 17, 36, 37, 50, 61, 62, 70, 107, 110,
122, 125, 126, 158).

`reconstructed/objects/action_registry.c` ports the three handlers. The picking primitives are restated as static
functions in the same file, because libobjects is built from its own directory, and so are ~25 validators' mutant
copies. The same routines are verified on their own in `reconstructed/npc` and `reconstructed/camera`.
`mu_anim_inputs` gains the hero's z, `camera` and the mouse segment. Without them the branches that need them are
counted as unsupported.

**Native wiring.**
- `mu_objects_step_inputs.camera` is set to the walk frame's `view.position` (CameraPosition) by the world's
  object tick (`native/world/parts/objects.c`) and reaches the registry tick.
- Charsel, login and the terrain tool pass NULL; none of them has handler 8 rows.
- Map objects carry no OBB `+0x31c` natively (the client writes it in the render Transform `0x012b5bde`). The
  mouse handlers therefore get no segment and count as unsupported. No live row uses them.

## 2. `0x01692887` has no frustum test (verified)

SPRITE-DRAW-001 left "the frustum test of `0x01692887`". The routine (thiscall on the sprite array `0x0a3da070`)
is a loop over 1,000 records of 0x3d8 bytes. It sets `+0xb` (visible) = 1 where `0x0095f977` (the byte `+0`, live)
is not 0, and nothing else. `mu_pt_sprites_mark_visible` already does exactly that.

The family `sprite_visible` runs it against the native one: live bytes 1, 2, 0x80, 0xff, visible bytes 0, 1, 7,
and all other record bytes poisoned and compared unchanged. The alpha ramp's input is therefore exact; nothing was
left to reconstruct.

## 3. Bone −1 and the attach's dt-0 update

**Bone −1 following (`0x0129faee`, Ignis Volcano types 175/176) is already on main.** RENDER-EFFECTS-007
(`07cccda8`) wires `mu_effect_object_world_matrix` into the per-frame update for a following record with bone −1,
verified there. RENDER-EFFECTS-008's "Left" line predates that merge.

**`0x0129f4cb` (static, then verified).** The attach `0x0183067e` calls it once per found object, after its table
entries (thiscall on the object, no dt argument). For every record of the object's `+0x3d0` std::list:
- The external matrix is chosen by the record's follow byte `+0x10`, whatever its bone:
  - following: `0x0129faee`'s world matrix (rotation · scale, position);
  - otherwise: the scale matrix `0x00cef956(+0xa0 × 3)` with the position `+0x158` in elements 12..14
    (`0x00a72313`).
- It then calls the node update `0x00a75708(0.0, &matrix, object)` on the record's effect.
- Unlike the per-frame `0x0129f671`, it does not write the effect scale (the instance keeps the template scale)
  and does not age timed records.

**Native.**
- `mu_effect_prime_matrix` (`native/core/mu_effect_scene.c`) picks the matrix.
- `mu_world_particles_ein_prime` sets the owner fields from the object image (the client hands the object
  itself), attaches the matrix and runs `mu_effect_scene_update_one(…, 0.0)`.
- The map-effects attach's `prime` op now calls it, where it only counted before.

## 4. Checks

`scripts/validate_worlds_after6.py --cases 3000 --mutations` (registered `validate_worlds_after6`, pins text,
data, feature09). Every routine named above runs as client code. The stubs are as in AFTER5 (the registry getter,
GetModel, rand), and the prime family stubs the node update `0xa75708` as a recorder.

| Family | What runs as client code | Cases | Result |
|---|---|---:|---|
| `hover` | the tick `0x00ce4b5b` → handlers 4 and 6, `0x018500bf`/`0x01850d88` on a random OBB and mouse segment (through the box, beside it, a point, NaN), latch 0/1/2/−1, frames around the (locked) end | 3,000 | equal |
| `camera` | the tick → handler 8 with the registry's nested SetAction: coarse box, `0x0185c113` turns, FaceNormalize, CollisionDetectLineToFace, InsideTest; extras 7 (and 0/6/8), turned/unturned boxes, hero or camera inside the box, NaN | 3,000 | equal (no coarse hit 889, coarse only 858, face hit 1,155) |
| `sprite_visible` | `0x01692887` + `0x0095f977` over 1,000 records | 300 | equal |
| `prime` | `0x0129f4cb` with its list iterators, `0x0129faee` (CRT sin/cos), `0x00cef956`, `0x00a72313` over 0..5 records (follow 0/1/2/0xff, bones 0/−1/3) | 1,000 | equal |
| `live_rows` (private, `--lang-dir`) | the 15 world-145 handler 8 rows in their world's table, 40 camera/hero placements each | 600 | equal |

- **7,900 cases equal, 0 mismatches, 0 stops** (live_rows: no coarse hit 46, coarse only 245, face hit 309).
- **30/30 compiled mutants caught** (lowest count 14, none stopped). They cover the axis test, the cross product,
  the OBB offset, handler 4's leave branch, handler 6's latch, reset and lock, handler 8's size, coarse box, half
  sizes, offset, turn order/axes, face list, normals and write, the line parameter, range and plane, the
  InsideTest flip, the sprite live test, and the prime's follow and scale.
- Five first-round mutants were equivalent: `e > 0` vs `>= 0` adds 0; `t > 0` vs `>= 0`; dropping one range axis
  that the other axis already pins; a sixth-digit change of the degree constant; a guard that only degenerate
  boxes reach. They were replaced, and the replacements run once on their own.

Portable tests:
- `reconstructed/objects/test_worlds_after6.py`: 7 synthetic tests (face hit, coarse only, turned box, far/sizes/no
  camera, handler 4 over/leave, handler 6 latch, the locked end), plus 1 private.
- `native/tests/test_native_anim.py`: anim_host now also runs a handler 8 row in the production runtime. With a
  camera the object's `+0xd8` becomes 0.1; without one, the ticks count as unsupported.
- `native/tests/test_native_map_effects.py`: right after the attach, every linked instance holds the prime's
  external matrix and keeps the template scale (4, 1, 0 links in the three worlds).

## 5. Fidelity (DATA-ACQ-002)

Base = origin/main `1e247ae9` (built separately), lane = this branch before merging `32b7f34d`.
`MU_LANG_DIR` = `mapanim.tsv` (AFTER5) + `mapeffects.tsv` (RENDER-EFFECTS-008).

| Tour | Captures | Result |
|---|---|---|
| with the lang tables, default clock | the 27 captures of worlds in the effect table, plus 138 and 91 | 26/27 byte-identical (PNG frames, OBJECT and light dumps); 144: 291 px differ (max Δ 3, inside the masked HUD rectangle at the top left, an effect quad), OBJECT and light identical, image 11.769 = 11.769 |
| with the lang tables, live_time clock | the same 27 | the same: 26/27 identical; 144 291 px (max Δ 3); 11.77 = 11.77 |
| without `MU_LANG_DIR`, default draw (byte-identity sweep) | all 32 | 32/32 byte-identical |

- World 145, the only world with handler 8 rows, has no capture.
- The installed `EncTerrain146.obj` is not decoded natively: `mu-world --world 145` loads 0 objects. Handler 8's
  end-to-end check is therefore the host test plus the `camera`/`live_rows` families.
- Ignis Volcano (138) and Acheron (91, the SPRITE-DRAW-001 world) are byte-identical: nothing in this lane changes
  their draw.

## 6. Limits

- Map objects have no OBB `+0x31c` natively, so handlers 4 and 6 do not run in the native world (no live row uses
  them). Porting the render Transform's box write `0x012b5bde` for map objects would enable them.
- The mouse-over handlers would also need the native world's MouseTarget each step. The walk frame has one; it is
  not passed.
- World 145 has neither a capture nor a decoded object file, so the fade was not seen in a native render.
- The picking globals `0x0bdc58c8`/`0x0bdc58e4`, which the client writes in handler 8, are not native state and are
  not compared.
- The dt-0 update's visible effect in the captures is limited to Swamp of Destruction's effect quads (291 px).

[Handoff](../handoffs/RENDER-WORLDS-AFTER6.md).
