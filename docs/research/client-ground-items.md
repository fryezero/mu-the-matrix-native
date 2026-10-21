# Dropped items: creation, fall, render, labels and pick-up (NATIVE-ITEMS-001)

This milestone recovers what the client does with items on the ground and joins it to the native walk-around world:

- how a dropped item is created from the server's item viewport message (model per item code, the special models,
  the fall from 180 units, the drop sound), how it moves every logic step (the fall, the spin, the resting pose, the
  sparkle) and how it renders every frame (the item render passes, the zen pile, the selection light);
- the name label: the text and colour class the client builds at creation, the colour strings, where the label sits,
  how hovering and the Alt key change it;
- picking up: the click, the space bar, the answer; despawn;
- the monster hurt and death sounds left unwired by NATIVE-COMBAT-002.

There is no server. Which items drop, when and where, the zen amounts and the pick-up answer are a clearly labelled
demo; the client's side of each message is reconstructed.

Labels used below: **verified** (authored C equals the client's instructions under Unicorn on every compared case),
**static** (a reading of the decoded instructions that was not executed), **inference**, **demo** (made up in place
of the server), **viewer choice** (native code that is not client behaviour).

## Identity

| Input | SHA-256 |
|---|---|
| `main.exe` (target) | `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a` |
| Restored text at `0x00401000` (capture09) | `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` |
| Second section at `0x01a7c000` (run10) | `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f` |

`scripts/validate_items.py` refuses other inputs and reports the SHA-256 of the 14 routine bodies it executes (for
example CreateItem `c684bd75…`, ItemAngle `b94e00e2…`, the name builder `39dda9ef…`, RenderItems `52d5c76e…`,
MoveItems `36ba5cde…`).

## Routines

| Routine | Address | Status |
|---|---|---|
| Receive dispatcher case 0x20 → ReceiveCreateItemViewport | `0x01288587` → `0x0122c216` | verified |
| Item code of the 15 item bytes | `0x00f09ddc` | verified (inside the viewport and create families) |
| CreateItem(ITEM_t, bytes, position, drop flag) | `0x016daa27` | verified (one runtime-patched instruction, below) |
| ItemObjectAttribute(o) | `0x016da00b` | verified |
| ItemAngle(o): the resting pose | `0x01802a66` | verified (lifted, `item_angle_table.h`) |
| The name builder (label text, colour class), then hudPlayerName addItem | `0x017ea422` → `0x00c83e2a` | verified (lifted, `item_name_table.h`); addItem static |
| MoveItems, and the per-item sparkle | `0x017ea1aa`, `0x017f7290` | verified |
| RenderItems: per-item plan, zen pile, RenderPartObject calls, screen position | `0x017e9495` | verified |
| TestFrustrum(position, range) | `0x016ccc14` | verified |
| SelectItem (selection light, mouse-ray hit) | `0x016b4fc0` | verified |
| SelectObjects (Alt prefers items) | `0x016b5157` | static |
| Label colour class → `"#RRGGBB"` | `0x00c84f00` | verified |
| hudPlayerName window: constructor fields, per-frame label position loop, setItemView | `0x00afaff8`, `0x00c81d1e`, `0x00efdca1` | static |
| Alt toggles the label view; space picks up | `0x00efc7d3` in `0x00efbca1`; `0x00efd9ab` | static |
| MoveHero's pick-up case (range 1.5, the request) | `0x01698376..` in `0x01697c17` | static |
| Delete (0x21) and pick-up answer handlers | `0x012338bc`, `0x012424bd` (and `0x012420a5`, `0x01242ea8`, `0x00b0fd9e`) | static |
| ClearItems | `0x017ea38b` | static |
| SetPlayerShock / SetPlayerDie, monster branches (hurt and death sounds) | `0x0138f92f`, `0x01393a61` | verified |
| SetMonsterSound(model, ten slots) from OpenMonsterModel | `0x018329fa` in `0x0180b0f4` | extracted (100 model types, `monster_sound_table.h`) |
| Shiny01 particle (the sparkle) | CreateParticle `0x015e5c73`, MoveParticles `0x016599cd` | verified by NATIVE-JOINT-001's particle families (same kind) |

### The item pool (static, consistent with every routine)

1000 records of `0x560` bytes at `0x0b4780c8`: `+0x000` key (word), `+0x004` the ITEM (`+0x10` code, `+0x14` level byte or
zen amount, `+0x38` durability, `+0x3a` excellent options, `+0x3b` ancient bits, `+0x72` packet byte 5 bit 3,
`+0x73..` five socket bytes, `+0x84` element, `+0x98` the flag `0x00cd0995(1)` tests), `+0x130` the OBJECT,
`+0x508` the label view byte, `+0x509` the label text (`0x53` bytes), `+0x55c` the label colour class.

## 1. Creation

**Packet 0x20** (verified): count = `packet[4]` capped at 75; 19-byte entries from `+5`: key big-endian (bit 15 = the
drop flag; `key & 0x7fff`, keys ≥ 1000 become 0), tile x, y, 15 item bytes. Position `((x + 0.5) · 100, (y + 0.5) ·
100)`. The handler resets the ITEM (`0x00ccc144`), stores the key and the label window's view byte (1 without a
window), then calls CreateItem. Item code = `b0 | (b3 & 0x80) << 1 | (b5 & 0xf0) << 5 | (b5 & 1) << 13`.

**CreateItem** (verified, 3000 cases):

- reset, code; **no Item.bmd record: return** (nothing else runs, not even SetLive);
- zen (`0x1c0f`): amount `b6 << 24 | b1 << 16 | b2 << 8 | b4`; sound `0x1f` with the drop flag;
- other items: level `b1`, durability `b2`, excellent `b3 & 0x7f`, ancient `b4`, `+0x72`; kinds 8/0x19/0x1a copy the
  element (`b6 & 15`) and look up pentagram data (not reproduced; elements 0..5 of those kinds are excluded); type 2
  and kind B 0x2b copy the socket bytes; `0x00cd1534` (runtime-patched, an input) sets `+0x98` from `b3 & 0x3f` or the
  first socket bytes; the drop sound: jewels `0x45`, `0x1c29` `0x2d3`, `0x1cfe`/`0x1d00..0x1d06`/`0x1d09..0x1d0c`
  `0x5a`, else `0x1e`;
- SetLive(1), model `code + 0xae6`, sparkle counter 1; special models: Box of Luck `0x1c0b` by level (`0x3894`,
  `0x3895`, `0x3896`, `0x3898`, `0x3899` firecrackers, `0x389a`), `0x1c20..0x1c22` level 1 → `0x38a5..`, `0x1a13`
  (levels 0/1/2 → models `0x14f0`/`0xaf9`/`0x12f8` with the level cleared), `0x1c15`, `0x1c17`, `0x1c18`, `0x1a14`,
  `0x1c09`, `0x1a0e`, `0x1a0b`, `0x1c29..0x1c2c` → `0x270f..0x2712`;
- ItemObjectAttribute, bounding box ±30, position; **with the drop flag z = height + 180, gravity 20** (the
  firecracker boxes: two effects `0x467`/`0x465` and z = height + 3, gravity 50); without it z = the terrain height;
- ItemAngle, then the name builder.

The instruction at `0x016dad9b` is a jump into an unanalysed module in the capture (runtime patch); the bytes left
after it (`00 00`) are the end of an immediate. The validator writes back `cmp dword ptr [ebp-0x18], 0x1c0d`: the low
word is inferred from the same jewel list in the pick-up handler `0x012424bd`, which starts with `0x1c0d`.

**ItemObjectAttribute** (verified): light 0.3, LightEnable 1, alpha 1, blend mesh -1, blend light 1, hidden mesh -1,
scale 0.8 (0.7 for `0x10e6..0x14f3`), then a type switch: blend meshes, blend lights from `sin(time · 0.004)` or
`rand() % 11 · 0.1`, UV scrolls, hidden meshes, scales (1.0 for `0xa99..0xaa1`, 0.5 for `0x26fb`, ...).

**ItemAngle** (verified, lifted): the pose an item rests in. Default `(0, 0, -45)`; weapons `0xae6..0xee5` lean 60°;
a chain of 260 type tests, 15 Item.bmd kind tests (scale 0.5 for kind B `0x2b`, ...), a range helper and one
per-index table (`0x009c2aea`/`0x01807c32`: scale and z angle for kind A 0xc). The routine returns no value (its
internal flag byte is not returned on every path). Armour parts (`0x18e6..0x22e5`) rest with the default angles and
stand upright: RenderItems poses them on the Player skeleton.

## 2. Every logic step: MoveItems (verified)

For each live item: `z += gravity; gravity -= 6;` floor = RequestTerrainHeight + 30 (+40 for `0xae6..0x16e5`); when
floor ≥ z, z = floor and ItemAngle runs (every step on the ground; the gravity keeps falling, z stays clamped);
otherwise the spin: Angle[1] (shields `0x16e6..0x18e5`) or Angle[0] = -gravity · 10. A drop from 180 units lands
after 7 steps (0.28 s). Then the sparkle `0x017f7290`: when the counter `+0x60` % 48 is 0 (before its increment) two
Shiny01 particles (`0x7f66`, subtypes 0 and 1, light 1, scale 1) at position + VectorRotate((rand%32+16, 0,
rand%32+16), AngleMatrix(Angle)); Shiny01 lives 18 steps with scale `sin(LifeTime · 10°)` (subtype 1 at ¾ and turning
12° a step) and draws additive.

## 3. Every frame: RenderItems (verified)

For each live item: Visible = TestFrustrum(position, 400) against CreateFrustrum's five planes; the pose model is the
item's (armour: the Player model `0xa91`; `0x26f2` by level `0x3890`/`0x3891`); a NULL model leaves the routine (all
later items are skipped); skin = the hero's base class; head offset `+0x90` by armour group (-160, -100, -50, -70);
Animation(BoneTransform, frame, prior frame, prior action, Angle, HeadAngle). Light = RequestTerrainLight + the
object's light (0.2, or 1.5 when selected: the hovered item lights up). **Zen** draws a pile: `n = clamp((int)sqrt(amount)
/ 2, 3, 80)` coins, n - 1 around the item (z angle `table[(i·20 + j) % 100] % 360`, distance `table[(i + j) % 100] % (n
+ 20)` with the 100-entry table `0x06fc9cb8` that WinMain fills with `rand() % 360` after `srand(time)`) and one at the
item. Some types draw with light 1. Worlds 10/0x84 (and 0x27 under a predicate) float the item `sin((i·1237 +
time)·0.002)·10`; worlds of `0x009b0418` place it at `0x00deeb4e + 180`. Every call is RenderPartObject(o, type, 0,
light, alpha, level, excellent ≠ 0, ancient, 1, 1, 1, 0, 2, -1/-1 or the pentagram fields, 0) — NATIVE-RENDERCHAR-001's
item render with its level glow, excellent and ancient passes. The screen position (position + 30 z through
`0x0184a244`) goes to `+0x50`/`+0x52`.

**SelectItem** (verified): every live, visible item gets LightEnable 1 and light 0.2; the first whose OBB (`+0x31c`)
the mouse ray hits (`0x018500bf`) gets LightEnable 0 and light 1.5 and becomes SelectedItem. SelectObjects (static)
asks items first when Alt is held, otherwise characters first.

## 4. The label

The labels are the **hudPlayerName** GFx movie's item list, not 2D text of the game loop (static reading of the window
class and the movie's ActionScript):

- at creation the name builder (verified, 5000 cases) sets the **colour class** `+0x55c` and the **text** `+0x509`:
  zen "`%s %d`" (record name, amount), special items GlobalText strings, plain items the record name (with the set
  prefix `0x009e0551` when one applies) plus "` +%d`" for levels ≥ 1, then GlobalText `0xb0` (skill), `0xb1` (option
  or excellent bit 6), `0xb2` (luck), element and socket suffixes; classes: grey `0xa` for +0, white for +1..+2,
  orange `0xd` for +3..+4, blue `1` for +5..+6 or with skill/luck/option, gold `3` for +7 and up and for zen/jewels/
  boxes (and more types), `0xd` for consumables, `4`/`0xc` excellent (`+0x98`), `9` ancient, `0x11` PC-room items,
  `0x12`/`0x13` set tiers;
- `0x00c84f00` (verified) maps the class to `#FFFFFF #7FB2FF #FF3319 #FFCC19 #19FF7F #A00000 #FF19FF #0000A0 #A06600
  #00FF00 #B2B2B2 #CC7FCC #B266FF #E56B0A #800080 #FFFF00 #00B0F0 #00B050 #CCFF00 #00FFFF #BCBCBC #C1C469`;
- addItem `0x00c83e2a` (static) sends `{key, name: "<font color='%s'>%s</font>", x, y}`, x/y the float projection
  (`0x0184a3ce`) of position + (0, 0, 35) (window `+0x1c` = 35 from the constructor `0x00afaff8`);
- every frame (`0x00c81d1e`, static) each label moves to that projection, except the hovered item's, which follows
  the cursor at (mouse x · scale x, (mouse y - 5) · scale y) (`+0x20` = 5);
- ItemNameMC (movie ActionScript): an autoSize HTML text field, width textWidth + 6, height textHeight + 4, centred on
  the anchor and 14 px above it, over a background 3 px wider and 2 px taller on each side; labels do not stack;
- **Alt** (static): each press toggles setItemView (window `+0x5c`, on by default), which shows or hides every item
  label; removeItem on delete or pick-up, clearAllItem in ClearItems.

## 5. Picking up, despawn

- A click while an item is selected puts MoveHero in pick-up mode (`0x01cf1148 = 6`) toward the item's tile; within
  1.5 tiles (`0x016a52a6`) it sends the pick-up request (zen and items through different packets) (static).
- The space bar (`0x00efd9ab`, static) takes the nearest live, visible item within 300 units (3D) of the hero through
  the same branch with the range test skipped (`0x0b43656d = 1`).
- The answer (`0x012424bd`, static) plays `0x45` for jewels, `0x2d3` for `0x1c29`, else `0x1d`, and removes the label.
  The delete message (0x21, `0x012338bc`) resets the item, SetLive(0) and removeItem: items vanish without an effect.

## 6. Monster hurt and death sounds (verified)

OpenMonsterModel sets ten sound slots on the model (`+0xb6`) through SetMonsterSound `0x018329fa`; the Bull Fighter's
are 0..4 (mBull1, mBull2, mBullAttack1/2, mBullDie). SetPlayerShock's monster branch (after action 5): when
`c + 0x3324 == 0`, a skeleton form (`o + 0x60` in `0x422..0x428`) plays `0x7b`, model `0x7b3` and models without slot 2
nothing, else `0xd2 + (o+0x60 == 9 ? 5 : 0) + slot[2 + rand() % 2]` (the attack sounds). SetPlayerDie's default
monster branch (after action 6): `0x5e + rand() % 2` in the worlds of `0x009dacb8`, else `0xd2 + … + slot[4]`, then
`c + 0x3324 = 0.001` (not when the model is missing: it returns first), so the death sound plays once.

## 7. Verification

`scripts/validate_items.py --cases 3000 --heavy-cases 300` (Unicorn over the strict machine of
`scripts/actor_machine.py` with `scripts/validate_combat.py`'s x87 helpers), single private run, 2 min 7 s: **22,200 cases, 0 mismatches, 11/11 negative controls detected**:

| Family | Client routine | Cases | Equal | Negative control (disagreements) |
|---|---|---:|---:|---|
| item_angle | `0x01802a66` | 3000 | 3000 | record tests ignored: 724 |
| label_color | `0x00c84f00` | 3000 | 3000 | classes shifted by one: 1924 |
| object_attr | `0x016da00b` | 3000 | 3000 | scale 1 for all: 2839 |
| name | `0x017ea422` | 3000 | 3000 | no level suffix: 1853 |
| create | `0x016daa27` | 3000 | 3000 | one drop sound for all: 248 |
| viewport | `0x0122c216` | 300 | 300 | no count cap: 93 |
| move | `0x017ea1aa` + `0x017f7290` (1000-record pool) | 300 | 300 | weapon height for all: 1443 |
| render | `0x017e9495` (pool) | 300 | 300 | one coin per pile: 81 |
| select | `0x016b4fc0` (pool) | 300 | 300 | last hit instead of first: 94 |
| frustum | `0x016ccc14` | 3000 | 3000 | range ignored: 4 |
| monster_voice | `0x0138f92f`, `0x01393a61` | 3000 | 3000 | hurt from the idle slot: 481 |

Every case compares bit for bit the bytes the routine writes (any written byte no compared field covers is a
mismatch), the calls in client order with their arguments, and the rand() count. Lifted code: `scripts/items_static.py`
translates ItemAngle (230 blocks, 260 type tests) and the name builder (159 blocks, 58 sprintf, 56 GlobalText) over a
closed instruction subset; its output is what the validator compares. The ignored report is
`evidence/native-items/report-02.json` (SHA-256 `8f65103a…5984`); the patched site is recorded there (capture bytes
`e9 60 35 44 0f 00 00`, written back `81 7d e8 0d 1c`).

Portable checks: `reconstructed/items/test_items.py` (packet parse, sounds, CreateItem's zen and remaps,
ItemObjectAttribute, ItemAngle, the name builder's classes and texts, the colour table, the fall timeline and sparkle,
the zen pile and armour pose, the ItemNameMC layout, TestFrustrum, SelectItem, the Bull Fighter's voices) and
`native/tests/test_native_items.py` (`mu-walk` on synthetic data: fall, landing heights, poses, labels, sparkle,
click/space pick-up, Alt, combat drops, determinism); private: a short Unicorn run and a Lorencia fight with installed
data.

## 8. Native module and mu-world

`native/core/mu_items.*` keeps the pool and runs the reconstruction in the session: the demo server's item viewport
messages → CreateItem (default hooks, then the name builder); every logic step MoveItems with the sparkle (through the
particle module's Shiny01), the pick-up mode and despawn; every frame SelectItem over the mouse ray, RenderItems' plan
with TestFrustrum against the frame's planes, each RenderPartObject call drawn through `mu_renderchar_draw_item` (armour
parts skinned on a Player mannequin), the labels with the client's colours, anchor and layout. mu-world draws the items
after the characters and the labels as a screen overlay; mu-walk blends the labels into the software frame. The
monsters' hurt and death sounds go through `mu_combat`'s SND_Play.

- **Demo.** A monster's death message schedules a drop after 14 steps at its position ± 40 units from a 12-entry
  table (zen 20..3000, jewels, apple, potion, short sword, katana, small axe, a shield, a helm, boots; levels up to
  +9 with skill/luck/option bits, 15 % excellent, 5 % ancient); the pick-up answer after 4 steps; despawn after 1500
  steps; `--item-seed` seeds the demo choices and the client rand() (the client seeds with `time()`).
- **Viewer choices.** The mouse ray is tested against the ±30 bounding box (the client's OBB is computed by the
  render); armour models load their bitmaps from `Data/Player` when `Data/Item` lacks them (the classic
  `OpenTexture(…, "Player\\")`; this client's texture folder rule is not traced); `0x00cd1534` (patched) is answered
  with the grade test its leftover code shows (grades 1, 3, 5, 6, 7, 8); the label text uses mu_ui_font with a stand-in
  face and a black 50 % background; GlobalText, the skill names (`0x00961620`) and NPC names (`0x011427c7`) come from
  NATIVE-LANG-001's local tables when `MU_LANG_DIR` is set (the installed strings give e.g. "Short Sword
  +9+Skill+Option+Luck"), otherwise English stand-ins (" +Skill", " +Option", " +Luck") and `[Text n]`; the set
  prefix and set tier tables are not wired; the special models (`0x3890..0x38a7`, `0x270f..0x2712`) do not resolve to
  files through Item.bmd and are not drawn (counted as `model_missing`); demo monsters carry no `o + 0x60`.

```sh
native/build/mu-world --game-root "$MU_GAME_ROOT" --placement native/world/lorencia-demo-placement.txt \
    --tile 182,127 --class 1 --combat-weapon sword         # kill monsters: items drop; click or space picks up, Alt toggles labels
native/build/mu-world --game-root "$MU_GAME_ROOT" --tile 133,127 --items --headless --backend gl --frames 140 \
    --out-dir DIR --item-script "2:drop:0x1c0f:0:134,126;4:drop:1:0xcf:135,127;40:hover:0;70:pick:0;120:alt"
```

`--items` turns the module on without `--combat`, `--no-items` off; `--item-script` items are `F:drop:CODE[:LEVEL
[:X,Y]]` (level byte as in the packet), `F:alt`, `F:space`, `F:hover:N`, `F:pick:N` (N-th live item); `--item-latency`,
`--item-despawn`. Headless runs add an `items_frame` line per saved frame and an `items` summary.

**Local renders** (`~/Documents/mu-mac-tools/native/renders/items/`, not committed; contact sheets and MP4s with the
session's sound): `gallery` (zen pile, jewels, potion, weapons with glow, shield, standing armour, labels in their
colours), `gallery-soft` (software rasterizer), `pickup` (hover lights the item and the label follows the cursor,
click → walk → pick-up, Alt hides and shows the labels), `combat-drops` (Lorencia kills drop zen and a sword, monster
voices, space pick-up).

## 9. Not established

- **Live comparison.** No game run (none planned): label pixels, the GFx font and background, and item sizes on screen
  are not compared with the client.
- **Runtime patches.** The compare at `0x016dad9b` (inferred) and `0x00cd1534` are patched by an unanalysed module.
- **Static only.** The addItem HTML and anchor, the per-frame label loop, setItemView and the Alt toggle,
  SelectObjects, MoveHero's pick-up case and the request packets, the answer and delete handlers, the space-bar
  pick-up, ClearItems, the AS layout.
- **Closed by NATIVE-FIDELITY-001** ([client-fidelity.md](client-fidelity.md)): the set-item prefix `0x009e0551`
  (verified), the "set tier" (PentagramOption `0x011447ac`), the suffix spacing (GlobalText 176–178), the special
  models' files (the loader `0x0183220e`, verified).
- **Not reproduced.** The pentagram/errtel lookups of CreateItem; the item OBB (`+0x31c`) and the ray test `0x018500bf`; the model getter's texture folder for item models;
  the inventory side of a pick-up (NATIVE-GFX-003's interface is not fed).
