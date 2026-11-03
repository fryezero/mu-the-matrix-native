# RENDER-WORLDS-AFTER4: the whole draw-first predicate, a render-time terrain light, action keys and the velocity writer

RENDER-WORLDS-AFTER4, 2026-11-03. This continues [AFTER3](client-worlds-after3.md) §5 and [Q2](client-worlds-q2.md)
§2. Target `main.exe` SHA-256 `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`; capture09 text
and run10 data are pinned in `scripts/pins.py`.

Labels: **verified** = compared with the original instructions under Unicorn; **static** = read from the
disassembly; **inference** = neither.

## 1. The draw-first predicate `0x017fcd18` (verified, complete)

The render pass (`object_render.c`) draws an object before its frustum test when this predicate answers yes. The
predicate switches on the world `[0x01cf15fc]`. A world case that answers no falls through to the default chain at
`0x017fe2a8`, and so does every world without a case. The chain ends in the class slot 0x10 that Q2 reconstructed.

Own cases: a type list, then for some worlds the live byte +0 (`0x0095f977`), then
`TestFrustrum2D(x / 100, y / 100, range)` with the object's range +0xc0 or a constant.

| World | Types | Live byte | Range |
|---|---|---|---|
| 0, 0x21, 0x4a | 2 each (0x37/0x3c, 0x21/0x23, 0x62/0x81) | — | no frustum test: always first |
| 2 | 0x7a, 0x7b | — | +0xc0 |
| 0x25 | 6 types | — | +0xc0 |
| 0x33 | 5..0xe, 0x57..0x58 and 12 more | == 1 | −400 |
| 0x38 | 7 types | ≠ 0 | −1500 |
| 0x39, 0x3a | 0x1e, 0x1f | — | −600 |
| 0x49 | camera-distance fade (below) | — | −500 |
| 0x5b, 0x5c | 0x1b, 0x1d, 0x3c | — | +0xc0 |
| 0x64, 0x65 | 11 types | — | +0xc0 |
| 0x6e, 0x6f | 15 types | — | +0xc0 |
| 0x70 | 21 types | == 1 | +0xc0 |
| 0x71 | 30 types | — | +0xc0 |
| 0x7a | 48 types | — | +0xc0 |
| 0x83 | 48 types | — | +0xc0 |
| 0x84 | 0x1e | — | +0xc0 |
| 0x85 | 34 types (switch) | ≠ 0, tested after the frustum | +0xc0 |

**World 0x49.** Let d be the x/y distance from the camera position `[0x0bdc5ab4]` to the object (sqrt
`0x00961a07`, CRT sqrt).
- Types 0x7a..0x7c, 0x7e, 0x7f, 0x81 and 0x9f inside TestFrustrum2D(−500) with 4000 > d: +0xa8 and +0xd8 each step
  by 0.03, or are set to 1 once at or above it; the answer is yes.
- Otherwise any type ≤ 300 inside the frustum with 2000 > d: +0xd8 steps; the answer is yes.
- Otherwise, if d > 2000 and +0xd8 ≠ 0 (NaN counts as ≠): +0xa8, +0xdc and +0xd8 are cleared.

**Default chain.** Each step is its world test, a type list and the frustum test; when the step is false, the
next one runs.
- `0x009a645f` on `0x009a6ef3()+0x78`: world 0x27, state +4 not 3, 4 or 5. Types 0 and 0x4bc, no frustum test. The
  state's constructor value is 0 (`0x009a62f1`); its other writers are not traced.
- `0x00e94004` (0x3f): types 0x10, 0x43..0x45, −600. `0x00e3068f` (0x52..0x5a): types 0x10, 0x43, 0x44, −600.
- `0x016a887a` (0x74..0x78, Deep Dungeon): **every type** whose range is ≤ −400, with its range.
- `0x00e1e4b6` (0x7b..0x7f, Kubera): 22 types, +0xc0.
- `0x016a8325` (0x80..0x82, Abyss): live byte ≠ 0, 49 types, +0xc0.
- Then the class slot 0x10 through `0x00ea594b`/`0x00ea2788` (worlds 134..145, Q2).

No world with its own case reaches a true chain step, because the chain's world tests exclude them and their class
slot 0x10 is the base (no). A mutant that skips the chain for those worlds is therefore equivalent, and is not
counted.

C: `mu_draw_first` (`reconstructed/objects/world_draw_first_visual.c`). The native `render_first` callback now calls
it for every world. The camera position is the frustum apex `vertex[0]`, which is VectorIRotate of the zero corner
plus the camera position, so it is exactly the camera. The tower state is 0. Login 0x5e and character select 0x5d
are not predicate worlds.

## 2. The render-time terrain light (static order; production host)

143's after slot 0x3c type 0x71 calls AddTerrainLight `0x016cacfc(x, y, L·(1, 0.2, 0.1), 3, frame light)`. This
happens in the after pass, which runs after RenderTerrain and the characters. Natively the light now goes straight
into the map's frame light grid (`mu_world_add_light`):
- objects drawn after it in the same pass read it;
- the next frame-light copy (`mu_world_frame`, the client's `0x016ca4fa` in the next logic step) replaces it;
- the `draw_unsupported` count is gone, and `rt.render_light_events` counts the calls instead;
- without a map, a call is refused and counted.

`mu_objects_prepare_after` now takes a writable `mu_world *`. Its callers already held one.

Check: `native/tests/test_native_render_light.py` (production runtime, synthetic BMD). The light lands at the
object's tile with the 1 : 0.2 : 0.1 ratio, a second frame without a copy adds to it, and a NULL map counts one
refusal.

## 3. Action record +8 is the BMD key count (verified)

Static:
- The model reader `0x012b3812` writes the action record (stride 16 at model +0x30) at `0x012b4149`: +8 is the
  stream's per-action int16, +0xa the lock byte, +0xc `keys·12` locked positions.
- The bone-track loop `0x012b4225` then reads each bone's `keys·12` positions and rotations per action
  (`bone_tracks.h`).
- The registry tick handlers (`0x00ce16b4`, `0x00ce1792`, …) also read `[model+0x30] + action·16 + 8` as the end
  of the action.

Data (`action_keys`): the original reader runs as client code (`validate_model_edge`'s machine) over every
installed `Data/Object142` model, all 181 of them (world 141). For every action, +8 equals native
`mu_bmd.actions[a].keys` and the layout walk's key count, and the reader consumes the whole stream. Type 0x2c
(`Object45.bmd`) has one action of 32 keys. AFTER3's inference is therefore confirmed, and native already passes
`bmd.actions[a].keys`.

## 4. The velocity (+0xbc) writer (static; data source open)

The live values differ per (world, type) (DATA-ACQ-002):
- 144: 0.07, 0.21, 0.3, 0.35, 0.4, 0.5;
- 142: 0.1 and 4.0 (type 107);
- 143: 0.18, 0.2;
- 140: 0.6 (type 67).

Native has CreateObject's 0.16 for all of these.

What was ruled out:
- No store of these constants reaches +0xbc anywhere in the text: no movss from a constant, no immediate (`push`
  or `mov`), no x87 `fst`, no wide store, no `lea` of the field in object code.
- CreateObject's own stores (0.16; 0.3; `1/+0xa0`·k) are already reconstructed.

The writer is the **action registry `0x01ec7d5c`**:
- The world manager's create tail `0x00ea2ad6` calls SetAction `0x00ce4a17(o, 0)`, and the move tail calls the
  tick `0x00ce4b5b`.
- These look up key `0x0112bbba(type, action)` in the registry's map (+0x10), copy its 0x20-byte entry and call a
  handler picked by the entry's handler id.
- The SetAction handlers registered by the constructor (`0x00ce4f39` into +0x24: `0x00ce1460`, `0x00ce147e`,
  `0x00ce149c`, `0x00ce1501`, `0x00ce1566` … `0x00ce15c0`) all store entry +8 into +0xbc. Some also pick a random
  frame within the entry's range into +0x34.
- The tick handlers go into +0x18.

The (type, action) → entry map itself is filled at run time:
- No code calls the registry's getter `0x00ce3dad` except the handlers and the three world-manager tails.
- The data section names no file for it.

Not ported: without the entries, a native SetAction would have nothing to apply.

## 5. Checks

`scripts/validate_worlds_after4.py --cases 9000 --mutations --game-root <client>` (registered
`validate_worlds_after4`):

| Family | Cases | Result |
|---|---:|---|
| `draw_first`: the whole predicate `0x017fcd18..0x017fe909` as original code (stubs: the manager singleton `0x00ea594b` as in Q2, and the event singleton `0x009a6ef3` with a tower state at +0x78+4; defined: camera `[0x0bdc5ab4]`, security cookie and the CRT's encoded user-matherr pointer for sqrt's NaN path) against `mu_draw_first`, AL and all OBJECT bytes. A deterministic sweep (6,052) comes first: every world 0..0x91, 0xff and −1, each listed type ±1 at the polygon centre with live bytes 1/0/2, and once more near a polygon edge solved for d next to a range. The rest are random worlds, types, ranges, positions, camera distances (around 2000/4000, NaN/inf), fade fields and tower states. | 9,000 | equal, 0 stops |
| `action_keys`: the original model reader over the 181 installed Object142 models against native `mu_bmd` and the layout walk | 181 | equal |

**9,181 cases equal, 0 mismatches, 0 stops; 40/40 compiled mutants detected** (lists, live tests, ranges, spans,
the 0x49 fade, the tower state and the chain tail; lowest count 1). `action_keys` compares data and has no compiled
mutants. Portable: `reconstructed/objects/test_worlds_after4.py` (5 + 1 private) and the host test of §2.

## 6. Fidelity (DATA-ACQ-002, 32 captures, base origin/main `d9389d55` vs lane)

| Capture | Default clock | Live clock | draw_all (default) |
|---|---|---|---|
| 112 Ferea | 2.250 → **2.241**, draws 60 → 82 | 2.250 → **2.241** | 2.227 → 2.228 |
| 91 Acheron | 6.856 = (after-character differences **6 → 0**, draws 55 → 62) | 6.400 = (6 → 0) | 6.856 = (6 → 0) |
| 113, 117..120, 122, 123, 129..131, 133, 56 | image equal; OBJECT dumps differ (more first-pass draws) | image equal | — |
| the other 18 | PNG, OBJECT and light byte-identical | byte-identical | 143, 144 identical |

- The OBJECT changes are only the body-light copy +0x1e8..+0x1f0 of the objects now drawn first. Acheron also
  changes +0xa of 6 objects, which now match live.
- The frame-light dumps of Ferea and Acheron move slightly towards live: cells over 0.05 go 61,356 → 61,355 and
  53,748 → 53,739.
- Velocity field differences are unchanged: 144 1,563 (40 near the hero), 142 123 (3), and the same for 143 and 140.
- The 143 arrival tile has no visible type 0x71 (the nearest is 2,580 units away, in live too), so the render-time
  light does not show there.

## 7. Limits and next

- **Velocity:** find the filler of the registry map `0x01ec7d5c`+0x10. It may be a run-time data loader or server
  data. The alternative is a read-only live dump of the map's nodes under GAME-LOCK. The entries are client data:
  native would need them as a local sidecar (as with `EncTerrain<n>.velocity`) or from their real source.
- The tower state of world 0x27 keeps its constructor value; its other writers are not traced.
- The render-time light is validated by the host test, not by a capture.

[Handoff](../handoffs/RENDER-WORLDS-AFTER4.md).
