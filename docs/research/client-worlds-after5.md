# RENDER-WORLDS-AFTER5: the action registry's data source, its handlers, and the tower-state writer

RENDER-WORLDS-AFTER5, 2026-11-04. This continues [AFTER4](client-worlds-after4.md) §4 and §7. Target `main.exe`
SHA-256 `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`; capture09 text and run10 data are
pinned in `scripts/pins.py`.

Labels: **verified** = compared with the original instructions under Unicorn; **static** = read from the
disassembly; **live** = read from the running client; **inference** = neither.

## 1. Who fills the registry map (static, then live)

AFTER4 found the writer of OBJECT +0xbc: the action registry `0x01ec7d5c`. Its map at +0x10 was filled at run time
from a source it could not find. This lane followed the map type instead of the getter.

- **Registry layout (static).** The getter `0x00ce3dad` is a thread-safe static: `[0x01ec7d5c]` holds a pointer to
  a 0x30-byte object built by `0x00ce38a8`:
  - +0 vtable `0x01aa1ce8` (destructor only);
  - +0x10 `std::map<uint32 key, entry>`;
  - +0x18 the tick handlers and +0x24 the SetAction handlers, both vectors of `std::function`, filled by
    `0x00ce4d20` and `0x00ce4f39`.

  No code reads `0x01ec7d5c` except the getter, and the getter has no other callers. So the map can only be
  replaced from outside through a getter caller: the world-manager tail `0x00ea28ca`.
- **The copy at world load (static).** `0x00ea280c` (world-manager load) runs only when the world has a factory
  class (`0x00ea64e7`). It takes `0x0112cd5b(0x06fbc434, world)` and assigns that loader's map into the registry
  (`0x00ea8de4`).
- **The table object `0x06fbc434` (static).** It is the Lang table manager `0x06fbaa60` + 0x19d4, filled by
  `0x0112cb08`, which the five language variants of the table-manager startup call (`0x0115f26c`, …):
  - for every world 0..0x91 it builds the name `"%s%d"` from `MapObjectAnimationInfo\MapObjectAnimationInfo` and
    world + 1;
  - it loads the table through the opaque table loader `0x010d68e1` into a local loader (vtable `0x01aada94`,
    0x40 bytes, map at +0x38);
  - it keeps the loader under key = world when its map is not empty;
  - the object is `{std::map<int world, loader>, default loader}`, 0x48 bytes.
- **The row parser `0x0112bc34` (static)** reads the columns into a 0x20-byte entry:

  | Offset | Field | Column |
  |---|---|---|
  | +0x00 | type | 1, `atoi` `0x00cd80e9` |
  | +0x04 | action | 2 |
  | +0x08 | float speed | 3, `atof` `0x010f77db` |
  | +0x0c | handler (index into both vectors) | 4 |
  | +0x10 | param | 5 |
  | +0x14 | `std::vector<int>` extra | the remaining columns |

  It inserts the entry under the key `0x0112bbba(type, action)` = 1000 · action + type. The factor is
  `(int)pow(10, digits of 300)`, cached at `0x06fbaa58`. A row reading "end" or "0" ends the table.
- **The source is `Data\Lang.mpr` (static).** The installed client has no `MapObjectAnimationInfo` files.
  [client-data-tables](client-data-tables.md) lists `MapObjectAnimationInfo\*` among Lang.mpr's 141 encrypted zip
  entries, whose password sits behind the protection boundary. Native therefore cannot port the source, so the
  lane took route 1b.
- **One read-only live read (live).** The free-runtime client was started to its server list (the Lang tables are
  built before it), without logging in. `langread <pid> anim.bin graph:0x06fbc434=0x48,4,0` was run once.
  `scripts/live_anim_table_to_plain.py` turns the snapshot into `mapanim.tsv`:
  - 10 worlds, 143 entries, handler ids {0, 1, 2, 5, 7, 8};
  - worlds 37, 51, 63, 138, 140, 141 (47 rows), 142, 143, 144 (29) and 145 (30).

  The values match every speed AFTER4 saw live:
  - 144: 0.07, 0.21, 0.3, 0.35, 0.4, 0.5;
  - 142: 0.1, and 4.0 for type 107;
  - 143: 0.18, 0.2;
  - 140: 0.6 for type 67.

  Worlds 37 and 51 have no factory class, so their rows never apply.

## 2. SetAction and the tick (verified)

`reconstructed/objects/action_registry.c`.

**SetAction `0x00ce4a17(object, action)`:**
- returns without effect when the type has no model (GetModel `0x00966cc4`/`0x00eaa8cf`) or when action is not
  below the model's action count (signed);
- on a new action, saves +0x2a → +0x2c and +0xd0 → +0xd4, then sets +0x2a and +0xd0 = 0;
- then looks up (type, action) and calls SetAction handler [entry +0xc]:

| Id | Handler | Effect |
|---|---|---|
| 0, 1, 4..7 | `0x00ce1460`.. | +0xbc = speed |
| 2, 3 | `0x00ce149c`, `0x00ce1501` | +0xbc = speed; +0x30 = 0; +0x34 = extra[0] + rand() % (extra[1] − extra[0]) |
| 8 | `0x00ce15de` | with more than six extras: +0xe0 (alpha rate) = extra[6] · 0.01; speed untouched |

**The tick `0x00ce4b5b(object)`:**
- looks up (type, +0x2a);
- returns 1 when there is an entry and a model, and calls tick handler [entry +0xc].

"At the end" means frame +0xd0 ≥ keys − speed, where keys is the action record +8. Tick handlers 6 and 7 subtract 1
from keys first when the record's lock byte +0xa is set. NaN is never at the end. "→ back" means
SetAction(extra.back()), through the `std::function` the tick builds.

| Id | Handler | Behaviour |
|---|---|---|
| 0 | `0x00ce1646` | nothing |
| 1 | `0x00ce165c` | at the end → back |
| 2 | `0x00ce1737` | at the end: if +0x30 ≥ +0x34 → back; then +0x30 += 1 |
| 3 | `0x00ce1830` | as 2, with a random extra[2 + rand() % (n − 2)] |
| 5 | `0x00ce1b61` | by extra[0]: 0 hero nearer than param → back; 1, 3 at the end → back; 2 hero farther → back |
| 7 | `0x00ce20c2` | as 5, but 0 → back only while +0x34 = 0 (+0x34 is cleared once the hero is farther); 2 at the locked end → +0x34 += 1, back |
| 4, 6, 8 | `0x00ce1947`, `0x00ce1e4b`, `0x00ce23ad` | the hero's box against the object's (`0x018500bf`): **not ported**, counted |

- Hero distance: the x/y distance from `[[0x0a39d754] + 0x33ac]`, with the sqrt `0x00961a07` rounding the root of
  the widened sum to binary32.
- The live tables use 4/6 nowhere. Handler 8 appears only in world 145, which has no capture; its SetAction half is
  ported.

**Native wiring** (`native/core/mu_objects_anim.c`, three runtime lines):
- `mu_objects_start` loads the rows of its world from `MU_LANG_DIR/mapanim.tsv`;
- after each object's create, it calls SetAction(0) (the create tail `0x00ea2ad6`);
- after the generic Animation tick, and before slot 0x30's events, the step calls the registry tick (the move
  tail `0x00ea2c2b`);
- both run only in the factory class worlds;
- without the file the runtime is unchanged.

## 3. World 0x27 tower state (static; not ported)

The only writer of `0x009a6ef3()+0x78` +4 is `0x009a649a(state, …)`: its +4 = state, and state 1 also resets
+8/+0xc. Its only caller is `0x00e8d845` (state = byte, arg = byte), which `0x0124eeda` and `0x0124ef61` call with
the message's bytes +4/+5.

Those two are cases 2 and 3 of the server-message sub-switch at `0x0128bb6f`, keyed by byte [3] of a C1 packet or
[4] of a C2. That sub-switch sits in the packet dispatcher module of `0x0128b204` (Q2). The state is therefore a
server message's. Offline the constructor value 0 is correct; native keeps it.

## 4. The render-time light capture (not reachable)

The Warps window offers one Kardamahal destination, gate 704, the arrival tile 119..127 × 16..24. Its nearest type
0x71 object is 2,580 units away and not visible, both live and natively (AFTER4). Every other route into 143 needs
walking or an in-map gate (707 → 708), which the live-game rules forbid on the PvP server. No capture was taken.

## 5. Checks

`scripts/validate_worlds_after5.py --cases 3000 --mutations` (registered `validate_worlds_after5`, pins text,
data, feature09):

| Family | What runs as client code | Cases | Result |
|---|---|---:|---|
| `set_action` | SetAction and all nine handlers over the registry its constructor `0x00ce38a8` built (operator new as a bump allocator), with a case tree of MSVC map nodes. The key factor is computed from scratch each case (`to_string`, `pow`, `__ftol2`); random types, actions (incl. −1 and ≥ count), models, entries, extras and key aliases (type + 1000). | 3,000 | equal |
| `tick` | the tick and handlers 0, 1, 2, 3, 5, 7, with the nested SetAction through `std::function`; frames at and around the end (± 1e-3, lock −1, NaN); hero at param ± 0.5; loop counters around each other | 3,000 | equal |
| `live_rows` (private, `--lang-dir`) | every one of the 143 live rows in its own world's table, through SetAction and the tick at four frames | 1,084 | equal |

- **7,084 cases equal, 0 mismatches, 0 stops; 29/29 compiled mutants detected** (lowest count 5; no equivalent
  mutants).
- Stubs: the getter, GetModel and rand (the MSVC LCG on both sides). Compared: all OBJECT bytes, the tick's return
  value and the rand sequence.
- Portable tests: `reconstructed/objects/test_worlds_after5.py` (8 + 1 private), `tests/test_anim_table_plain.py`
  (2, synthetic snapshot) and `native/tests/test_native_anim.py`. The last one is a production host: world 144
  with and without a synthetic `mapanim.tsv`, plus the classless world 51.

## 6. Fidelity (DATA-ACQ-002, 32 captures, origin/main `5cb6fa6d` vs lane with `mapanim.tsv`)

| Capture | Velocity differences, map (near hero) | Image, default | Image, live_time | Image, draw_all |
|---|---|---|---|---|
| 144 Swamp of Destruction | 1,563 (40) → **0 (0)** | 12.394 → **12.391** | 12.394 → 12.391 | 12.397 → 12.394 |
| 142 Twisted Karutan | 123 (3) → **0 (0)** | 7.145 = (frame changed) | 6.394 = | 7.131 = |
| 143 Kardamahal | 88 (0) → **0** | 10.299 = (PNG identical) | 10.236 = | 10.299 = |
| 140 Bloody Tarkan | 2 (0) → **0** | 5.225 = (PNG identical) | 5.225 = | 5.225 = |
| 138 Ignis, 63 Vulcanus | 0 → 0 (+0x34 loop limits only) | PNG identical | identical | identical |
| the other 26 | — | byte-identical (PNG, OBJECT, light) | — | — |

- No other OBJECT field changes against live: the action, frame and alpha fields stay as they were.
- The changed OBJECT bytes are:
  - +0xbc (144: 5,159 objects);
  - +0x34 (the handler-2 loop limits);
  - +0xd0/+0xd4 of the objects whose speed changed.
- Without `MU_LANG_DIR` the lane is byte-identical to main on all 32 captures.

## 7. Limits

- Tick handlers 4, 6 and 8 (hero box collision `0x018500bf`) are not ported. They are unused in the live tables
  except handler 8 in world 145, which has no capture.
- The table is decoded Lang.mpr data: a local `mapanim.tsv` (MU_LANG_DIR), never committed. A client update that
  changes Lang.mpr needs a new read.
- The client's rand() is one global sequence; native draws the create-time limits from its own LCG, so per-object
  loop limits differ from the live ones.
- The tower state of world 0x27 is a server message's (§3).
- The render-time light still has no capture (§4).

[Handoff](../handoffs/RENDER-WORLDS-AFTER5.md).
