# Inventory icon bits and equipment cursor, ITEMS-UI-001

Offline/static work against the text and data pins in `scripts/pins.py`. No live process,
original launcher, installed app, packet data or character-power behavior is involved.
See [the lane handoff](../handoffs/ITEMS-UI-001.md) for measured checks and limits.

| Compared capture | SHA-256 |
|---|---|
| Restored text, capture09, base `0x00401000` | `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` |
| Second image section, run10, base `0x01a7c000` | `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f` |

## Icon appearance bits

The full ITEM level word already reaches the native icon adapter from authored equipment.
The original passes that word, excellent and set bits separately through RenderObjectScreen
and RenderPartObject, at `0x017e7932..0x017e7960` and `0x017e796a..0x017e7997`.
`mu_icon_glow_of` follows that separation. Its field named `option` is the excellent flag,
not the level word's low option/luck bits. INVENTORY-FX already connected it to rendering.

The original extracts the level at `0x0176cf4a..0x0176cf53` with arithmetic shift 3 and
mask 15. The helper `0x016a78c9..0x016a78d6` does the same. Direct level checks in the
special bodies `0x3895` and the +15 branches use the same shift/mask. Excellent is a
separate argument, tested in the tail beginning at `0x017e2c87`; ancient/set bits are
another argument. The `-1` sentinel tests are outside ordinary authored level words.

Instruction comparison in `validate_items_ui` flips every combination of bits `0x87`
for levels 0..15 on the ordinary sword, armour and level-14/15 special body `0x3895`.
It compares the original ordered mesh/body/colour stream against the existing native
stream with those bits removed, at a fixed clock, with separate excellent and ancient
controls. These use authored record kinds 0/0/0, quality 5 and clock 1,234 ms;
this is not a census of every item body. This establishes no additional visual
effect for these bits in that domain.
Adding a new glow or excellent interpretation would contradict this evidence.
The shared renderer and its tables therefore stay unchanged.

## Equipment hit region and tooltip

`0x00ec4bf2..0x00ec4c2c` compares the integer mouse globals `0x0bdc5ad8/0x0bdc5adc`
against the integer rectangle `[x,x+w) x [y,y+h)`. Endpoint additions wrap as x86 int32.
It is a rectangle. The missing detail was its coordinate conversion:

- The wrapper truncates each 640x480 slot field independently with CVTTSS2SI at
  `0x016c246e..0x016c2485`, then calls the test at `0x016c2486`.
- WM_MOUSEMOVE divides window coordinates by the screen/virtual-size scale, truncates,
  and clamps to 0..640/0..480. Compared ranges are `0x0121012c..0x0121016b` and
  `0x012101ab..0x012101f7`.
- After a hit, the slot wrapper raises the tooltip request at `0x016c24d7`, with
  the same independently truncated x/y/w/h. Equipment page type and final flag are zero.
- `0x00cda1cf` takes its ordinary rectangle path through `0x00cda471` with scale 1
  and margin 0. `0x00cda352` routes the ordinary item to `0x00b8c7f9`, which stores
  x/y into popup `+0x9c/+0xa0` at `0x00b8c845..0x00b8c85d`. InfoPopup converts
  the rectangle back to window coordinates, as already instruction-compared by
  `validate_hud`'s HTML family.

Native now tests these integer coordinates rather than the floating window rectangle.
It also supplies the equipment hover tooltip that the movie's grid-only rollover
callbacks could not supply. The current host suppresses equipment tooltip requests while
holding an item, awaiting an inventory service answer, or under a different picked movie.
Those gates use the existing native layer's state, not reconstructed GFx manager identity.
The tooltip uses the existing code/level HTML callback. It does not synthesize complete
ITEM bytes or additional item-stat option records from the appearance-only fields.

## Frame ordering and the opaque boundary

The captured main-game render `0x0185916b` has RenderSprites call sites at
`0x01859ab6` and `0x01859bb1`, both before the legacy UI pass at `0x01859ce7`. The next UI call at
`0x01859cf1` goes to opaque `0x10b3e920`; this lane does not follow it.

The original captured per-window pass `0x00abfcca` displays a movie, draws its 3D
items, then draws its overlay. This is already instruction-compared by `validate_hud`.
Its only direct captured caller is `0x00ac9666` inside `0x00ac964e`, whose sole direct
captured caller is `0x01858c99` in the selection scene. No captured pointer to either
routine was found in the text or second image section. Main-game GFx invocation through
the opaque hook is unresolved. `0x00aae6f9` is an interface state query that calls vtable
`+0x24`; it is not evidence of the manager's drawing pass. Older HUD notes label it too
broadly.

Native currently draws each window's items after that movie, higher windows and the
tooltip afterward, and the held item last. This lane leaves that ordering intact. Its
fixed-clock overlap capture checks native occlusion, not original main-game parity.
Icon sprite requests continue to join the world's list; no sprite is composited over
an icon. Exact same-frame/next-frame sprite scheduling through the original main-game
GFx hook cannot be established without crossing the excluded boundary.
