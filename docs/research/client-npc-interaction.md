# Talking to NPCs: picking, the talk walk, the talk result and its windows (NATIVE-NPC-001)

This note maps what the client does when the player clicks an NPC, up to the window that opens, and how the native
client reproduces it. There is no server: the server's answers are a labelled local demo. The network side is out of
scope; packets are named only where the client builds or reads them.

Pinned inputs, as in [client-hud.md](client-hud.md): restored text capture09 `2bd5f2e9…3724` at `0x00401000`, second
image section run10 `c985e2e6…a0672f` at `0x01a7c000`.

Labels:

- **verified**: the client's instructions ran in Unicorn (`scripts/validate_npc.py`) and their output equalled the
  authored C (`reconstructed/npc`);
- **executed table**: values read by running a client section in Unicorn;
- **static**: read from the decoded instructions, not executed;
- **demo**: a native stand-in for the server, chosen here.

## 1. Selecting an NPC (verified)

The selection pass `0x016b5157` (called from the main-game render at `0x01859cb3`) clears the selections and, on the
normal path, picks in this order (static): an item (`0x016b4fc0`, unless a window at manager `+0xd4` is busy), then
`SelectedNpc [0x01cf1150] = 0x016b47bf(4)`, then `SelectedCharacter [0x01cf1154] = 0x016b47bf(0x22)`, then
`0x016b47bf(1)`, then an operable object (`0x016b5509`).

**The character pick `0x016b47bf(kind mask)`** walks the 400 characters (getter `0x0095f6db`/`0x009a13f4`; the object
is the character `+0x3254`):

1. Every candidate whose object kind `o+0x3b` is a subset of the mask, live, visible (`o+0xb`) and not transparent
   (`o+0xdc > 0`) gets `o+5 = 1` and a highlight light in `o+0xec` by the character word `+0x144`: 0 → 0.2 grey,
   1 → −0.4 grey, 2 → (0.2, −0.6, −0.6), 3 → 1.5 grey, 4 → (0.3, 0.2, −0.5); `c+0x1f >= 6` → −0.4 grey.
2. The selectable ones (also not dead `c+0x23`, without buff `0x1b`, not the hero unless the scene is 5, `c+0x10` set)
   have their oriented box `o+0x31c` adjusted **in place** for a few models (`0xa40`: start.z += 300; `0x81b/0x81c`:
   start.z += 200; `0xa3e`: start.x −= 100, start.z += 100, X.x += 100, Z.z += 100; world `0x5d`: Z.z += 100;
   `0xa64`: X.x += 100, Z.z += 100; repeated calls in one frame add again).
3. The box is tested against the mouse segment `0x0bdc5984 → 0x0bdc5990` with the separating-axis test `0x018500bf`:
   the axes (p2 − p1) × X, × Y, × Z and X, Y, Z; on each axis `0x01850d88` overlaps the segment's interval
   [min(d1, d2), max(d1, d2)] with the box's [start + negative projections, start + positive projections]
   (binary32, the client's operation order and its comiss min/max).
4. The nearest candidate by the squared distance from the camera position `0x0bdc5ab4` wins (start 999999995904,
   strict less). In world 2 a candidate on a map byte (`0x0b735420`, tile `(int)y/100 << 8 + (int)x/100`) of 3 that
   differs from `[0x0b437c10]` is refused unless that value is `0xb`.

**The box.** The model transform `0x012b5bde` (verified by CLIENT-SKIN-001) writes the OBB from the object's box
`o+0x128`/`o+0x134` and its position: start = min + origin, axes = diag(max − min) (bounds mode ≠ 2;
RenderPartObject's calls pass these fields, static). The box per model type comes from the character create
`0x0137d8a1`: its section `0x0137dfe1..0x0137ed7e` writes the default (−60, −60, 0)..(50, 50, 150) and a switch on the
model index. Executing that section in Unicorn for every index 0..0x3af6 gives 43 non-default boxes
(`reconstructed/npc/character_box_table.h`, executed table), e.g. the Player `0xa91` (−60, −60, 0)..(40, 40, 120) and
the castle gates `0x0a56..0x0a5d`.

## 2. The click and the walk (static)

MoveHero's NPC branch (`0x016aae09`) runs when `SelectedNpc` is set:

- nothing happens while **NpcShop** (`+0xf4`) or **StorageInven** (`+0x100`) is visible (the chain moves on to the
  other selections);
- without buff `0x1b` the hero's movement type `c+0x39` becomes **2** (talk); `TargetNpc [0x01cf1168] = SelectedNpc`;
  the target tile is the NPC's tile (`+0x180/+0x184`); `[0x0b437c40]` and `[0x0b437c44]` keep its model index and angle;
- model `0xa3e`: within 550 units (xy) Action runs at once;
- otherwise **PathFinding2(hero tile, NPC tile, distance 0, level 2)**; with a path the hero walks (SendMove), without
  one (a path of one node: already beside it) Action runs at once.

**Why the walk ends beside the NPC.** MoveCharacters `0x0137a7ce` clears bit 2 of every TerrainWall entry each step and
sets it again on the tile of every live, not dead character whose kind is not 8 (static). The NPC's own tile then fails
FindPath's first search (`level <= TerrainWall`) and the second search falls back to the best-heuristic node beside it
(NATIVE-PATH-001).

**The end of the walk.** When MovePath arrives, MoveHero stops the hero (`0x016a8904(c, 1)`, SetPlayerStop) and calls
**Action(c, o, 0)** `0x01697c17`, which dispatches on `c+0x39`; case 2 is the talk.

## 3. The talk case (static)

Action's case 2 (`0x0169901c..0x0169c094`):

1. `[0x01cf1148] = 0xc`; a busy window at manager `+0xd4` is reset; unless two event predicates hold, SetPlayerStop and
   `c+0x38 = 0`.
2. The target must be an NPC (character `+0x328f == 4`).
3. **Local refusals** (a message, no request): DivideWindow (`+0x250`) visible → GlobalText `0x148c`; class 238
   (Chaos Goblin) below level 10 → GlobalText `0x297` with `%d` = 10; class ≠ 0 with MUMix (`+0x290`) visible →
   GlobalText `0xfd8` (`mu_npc_talk_refusal`).
4. **NpcShop's repair flag** `0x00bf172e`: 1 for classes 243, 246, 251, 416, 578, 686, 687, else 0
   (`mu_npc_repair_shop`).
5. A legacy NewUI window 4 closes; a packet `0x41` may go out first (a predicate on `0x00a99ebe`).
6. Special classes take their own branches (`0x1d4..0x1db`, `0x1d6`, `0x1d7`, `0x1de`, `0x223`, `0x243`, `0x283`, …,
   `0x3ad`; quest, event and gate NPCs) — not ported.
7. The generic request: NpcShop `+0xbc` = the NPC's key, then the talk request packet (C1 `0x95`: key high, key low, 0).
   In worlds `0x62..0x63` and `0x2d..0x32` another handler takes it.
8. Class `0xe5` sets `[0x01d1de8c]`; class `0xe2` (the pet trainer) sends `0xd3` requests for pet items;
   `TargetNpc = -1`.

**No turn, no talk animation.** The case has no CreateAngle and no SetAction: the hero keeps the heading of its walk
and the stand action SetPlayerStop gave it. NPCs have no talk reaction in this path either. The sounds of a talk
come with the answer (section 4).

## 4. The answer: ReceiveTalk `0x01280659` (verified)

The dispatcher `0x01287ead` sends the talk answer (case `0xdf` in this build's opcode table) to `0x01280659(packet,
encrypted)`:

- an answer that did not come through the C3/C4 decryption (`encrypted == 0`) is reported back with packet `0x4d`
  {2, 0, `0xb2`} and nothing opens;
- unless EventMapEntranceUI (`+0x2ac`) is visible, every GFx window (`0x00ac9c74`) and every legacy NewUI window
  (`0x00f2b53d`) closes first;
- `packet[3]` selects the window:

| Result | Window (GFx manager slot, registry movie) | Call |
|---|---|---|
| 0x00, 0x01, 0x0a, 0x0b, 0x0e..0x10, 0x14, 0x1a..0x1f, 0x2a..0x2f, 0x32, 0x3a..0x3f, 0x41..0xfe | NpcShop (`+0xf4`) | `0x00bf17c2(packet[0xb])` (tabs), Open |
| 0x02 | StorageInven (`+0x100`) | Open |
| 0x03 | MixGoblinSel (`+0xb0`) | Open (when the slot is set) |
| 0x04 / 0x06 | EventMapEntranceUI (`+0x2ac`) | `0x00b04bd2(2)` / `(1)` |
| 0x05 | object `[0x06fc9eb0]` | `0x011e04c7(0xe)` |
| 0x07 | GuardianMix (`+0x20c`) | Open |
| 0x08 / 0x09 | MixAttributeScalp (`+0xb4`) | close all, `0x00bd0006(result == 8)`, Open |
| 0x0c | legacy NewUI window 0x17 | `0x00f2abcd(0x17)` |
| 0x0d | — | packet `0x83` {2} |
| 0x11 / 0x13 | HarmonyMix (`+0x264` / `+0x260`) | Open |
| 0x15 / 0x16 / 0x31 | MixInventoryFrame (`+0xa8`) | `[0x01ec8d78]` = 8 / 9 / 13, Open |
| 0x17 | SocketMix (`+0x208`) | Open |
| 0x18 / 0x26 / 0x27 | MixSel (`+0xac`) | `0x00bd72a3` (null-checked) / `0x00bd7408` / `0x00bd709c` |
| 0x19 | — | `0x0121405e(&local)` |
| 0x20 | ExchangeLuckCoin (`+0x270`) | Open |
| 0x21 | duelwatch (`+0xe0`) | `0x00b54793` |
| 0x22 | NpcShop | byte `+4` of `0x00aabe9b()` = 1, Open |
| 0x23 | EventMapEntranceUI or legacy window 0x3f | index `packet[4]·60 + packet[5]`; hero tile x 0x34..0x4b and y 0xe4..0xfa → NewUI 0x3f; else mode 3 and `0x00b04ded(3, index, packet[0xc] != 0, 0, 1)` |
| 0x25 | handler at `+0xec` (no movie) | `0x00baeb44` |
| 0x28 / 0x36 / 0x37 / 0x39 / 0x40 | npcdialogue (`+0xf0`) | dialogue NPC `0x248` / `0x2fc` / `0x2fd` / `0x3ab` / `0x3ac` (`0x00fdc96c`), open `0x00be842c` |
| 0x29 | ElementalMix (`+0x204`) | Open |
| 0x30 / 0x33 / 0x34 | PersonalShop / MuunExchange / OrdealSquareBattleEnter | `0x00aae767` |
| 0x35 | RuudShopFrame (`+0x1fc`) | Open |
| 0x12, 0x24, 0x38, 0xff | — | — |

- **Common tail:** SND_Play(25, `iButtonClick.wav`), SND_Play(28, `iCreateWindow.wav`), then, unless
  `[0x01cf0fc0]` is set, SetCursorPos(`(mouse_x·260/640)·W/640`, `mouse_y·H/480`) with `[0x0bdc5ad8]`/`[0x0bdc5adc]`
  (the client's integer arithmetic); EAX = 1.

Which result an NPC gets is the server's decision; the client side is this table. "Open" is the window's vtable
`+0x40`. NpcShop's Open `0x00bf0354` also opens the inventory (static).

## 5. The windows and their movies (static readings of the handlers and the movies' ActionScript)

The GFx registry `0x00ac4a79` (139 windows, NATIVE-HUD-001) holds the NPC windows; all use alignment 9 (no
SetAlign/SetWindowSize), so the window creator only applies SetScale(83) below 700 pixels:

| Window | Slot | Handler | Movie | Notes |
|---|---|---|---|---|
| npcdialogue | `+0xf0` | ctor `0x00be7f69` (0x1d80 bytes) | NpcDialogue.ozg | title, text, 13 select buttons |
| NpcShop | `+0xf4` | ctor `0x00bef75b`, vtable `0x01a958f8`, item frame `0x00ab7277(8, 8, 15, 5)` | NpcShop.ozg | 8 × 15 slots, 5 tabs, repair box |
| StorageInven | `+0x100` (+ `+0x104`) | item frame `(9, 8, 15, 1)` | StorageInven.ozg | 8 × 15 slots, zen, deposit/withdraw |
| MixInventoryFrame | `+0xa8`, `+0xb8` | item frames | MixInventoryFrame.ozg | not played natively |
| NpcJobChangeQuest, NpcQuestProgress, NpcGateKeeper | `+0x108`, `+0x10c`, `+0x110` | — | — | quest NPCs; the Dialog(kor) table's consumer is NpcJobChangeQuest (`0x00bec46a`) |

**npcdialogue.** The open `0x00be842c` sends `SetTitle` (the dialogue NPC's Npcname, stored by `0x00fdc96c`),
`VisibleContribute(0)` only for the dialogue NPCs `0x248, 0x2fc, 0x2fd, 0x3ab, 0x3ac`, then `0x00be86de` →
`0x00be89f7` `SetDialogueMentDivide(text, ";")` (the client's dialogue text separates lines with `;`; the movie wraps
it to its width and answers `NPCDialogTextWidth(lines, wrapped)`), `0x00be8724` `SetDialogueMent("%s %d")` and
`SetSelectBtnContent("1. …;2. …;")`, then `SetPosLeftCenter`. The movie calls back `onClickSelectBtn(index, uid)`,
`onClickbtnNext/Previous`, `onClickbtnSelNext/Previous` and `CloseWindow`. The choice goes to the server (packet `0xf8`
in `0x00be829f`). The text comes from the dialogue manager `0x01ec9858`'s string map (`0x00fdc9c1`/`0x00fdca1b`),
fed by `Data\Local\NPCDialogue.bmd` (88-byte records: state, NPC class, text id, answer/next pairs — layout read
from the decoded file; its text ids are not GlobalText and not Dialog(kor), a Lang table NATIVE-LANG-001 did not
read).

**NpcShop / StorageInven** extend `Common.Base.MUSlotComponent`, as InventoryFrame does: `UIInit`,
`requestWindowPos`, `requestSlotInfo` (per page), `requestItemSlotClick/ClickR/Over/Out`, `SetSlotStateAll`; NpcShop
adds `SetVisibleRepair`, `SetAvailableTabs`, `InitTitle`, `InitTax`, `InitBtnTitle`, `onClickBtnTab`; the vault adds
`InitText`, `InitButton`, `SetKeepZen`, `SetCharge`. The shop list arrives in a separate packet (the item-list handler
`0x0128245c` fills 120 entries at `0x0b5d6338` and calls NpcShop `0x00bf1819(packet[6])`; its type 3 fills the chaos
machine).

## 6. Native

`reconstructed/npc` (libnpc): `mu_npc_talk_result` (ReceiveTalk), `mu_npc_talk_window` (its table for hosts),
`mu_npc_repair_shop`, `mu_npc_talk_refusal`, `mu_pick_axis_overlap`, `mu_pick_segment_obb`, `mu_npc_pick`,
`mu_character_box`, `mu_character_obb`.

`native/core/mu_npc` runs the session in mu-world/mu-walk (`--npc`, `--npc-demo FILE`, `--npc-script`):

- every logic step with a fresh click, the pick over the actors (kind 4 NPC, 2 monster; box from the table at the
  actor's position) before the combat and walk code; a click on an NPC is consumed;
- MoveHero's branch with `mu_walk_path_to` (PathFinding2), MoveCharacters' character bit on `frame.walls`, the talk at
  the walk's arrival, the refusals and the repair flag;
- **demo:** the answer `latency` (4) steps later, from `native/world/lorencia-demo-npc.txt` (talk result per server
  class, shop and vault contents, Dialog(kor) indices for the dialogue, an extra placement line for Sir Lesnar);
  NPCs without a row answer `0xff`;
- the answer through `mu_npc_talk_result`: close-all, SND_Play 25/28 through the session's audio host, the window.

The GFx layer (`native/gfx/mu_gfx_layer.c`) plays NpcDialogue, NpcShop and StorageInven when they are converted:

- the dialogue with the handler's invoke order and the movie's own paging (6 lines a page: layer choice);
- the shop and the vault as 8 × 15 slot windows over the reconstructed item grid (page types 8 and 9 in the slot pass),
  item models through the host's items callback (NATIVE-GFX-003's RenderItem3D path), tooltips through
  `core/mu_hud_tip`, the inventory opened beside them;
- **demo actions:** a click on a shop item buys it (inventory first free place; price from Item.bmd's value fields
  `+0x28c`/`+0x288`, +50 % per level — the client's price routine is not reconstructed); a right click on an
  inventory item sells it for a third while the shop is open, or stores it while the vault is open; a click on a vault
  item takes it. The client asks the server for each instead. The dialogue's options close it after the last one.
- Titles: Npcname (MU_LANG_DIR) of the clicked NPC, or for npcdialogue of the dialogue NPC the result names. The
  dialogue text is Dialog(kor) lines from the demo table, joined with `;` (labelled demo: the client's text table for
  npcdialogue is not read).

Not played natively (named in the log and the `npc_open` report): every other window of the table (mix windows, event
entrances, Ruud shop, …), the special-class branches of the talk case, the shop's repair and rebuy buttons, tabs, the
vault's zen moves.

## Verification

`scripts/validate_npc.py --cases 3000 --talk-cases 16 --pick-cases 1000 --mutations` (2026-10-18, about 40 s):

| Section | Client code | Cases | Result |
|---|---|---:|---|
| talk | ReceiveTalk `0x01280659`, every result byte × 16 random states (encrypted or not, EventMapEntranceUI visible, null slots, hero tile, cursor lock, mouse and screen) | 4,096 | every call, argument, memory write and EAX equal |
| axis | `0x01850d88` | 3,000 | equal |
| segment | `0x018500bf` | 3,000 (1,497 hits) | equal |
| pick | `0x016b47bf` on synthetic scenes of up to 400 characters (stacks on one ground point, worlds 0/2/0x5d, masks 4/0x22/1/6) | 1,000 (251 picks) | index, o+5, o+0xec and in-place box adjustments equal |
| box | section `0x0137dfe1..0x0137ed7e` | 15,095 model indices | equal to the committed table |

Five planted mistakes are caught: StorageInven's slot, the second sound, a strict axis test, the pick distance
without its height term, the box table ignored. Modelled, not client code: the GFx and NewUI manager getters, the
window methods, SND_Play, the packet builder, SetCursorPos, the character getters and the buff test.

Tests: `reconstructed/npc/test_npc.py` (independent statements: the window table, the cursor arithmetic, the refusals,
a slab test against the segment/OBB test on 3,000 boxes, the pick's nearest rule and in-place adjustment);
`native/tests/test_native_npc.py` (mu-walk on synthetic NPC models: pick, walk beside, talk at arrival, answer
after the latency, windows by result, the window gate, sounds; the windows on the stand-in libmugfx; private: the
Lorencia demo and the validator).

## Renders (local)

`~/Documents/mu-mac-tools/native/renders/npc/`: `dialog/` (Sir Lesnar's npcdialogue with Dialog(kor) text, MU_LANG_DIR),
`dialog-nolang/`, `shop/` (Hanzo the Blacksmith's NpcShop with item models, buy, sell), `storage/` (the vault, take,
put), `goblin/` (MixGoblinSel: not played; the world only). Each has `report.json`.

```sh
export MU_GFX_LIB=…/libmugfx.dylib MU_LANG_DIR=…/lang MU_GFX_SINGLE_BUFFER=1
native/build/mu-world --game-root "$MU_GAME_ROOT" --headless --backend gl --no-audio \
    --placement native/world/lorencia-demo-placement.txt --npc-demo native/world/lorencia-demo-npc.txt \
    --gfx MOVIES --tile 138,123 --npc-script "5:click:smith 60:buy:0 80:sell:0 110:close" --frames 120 --every 10 --out-dir DIR
```

Movies: convert `NpcDialogue NpcShop StorageInven` with the NATIVE-GFX-002 options next to the HUD set.

## Gaps

- The NPC dialogue text table (NPCDialogue.bmd's text ids) and the shop list packet's item records are not read; the
  demo supplies text and items.
- The talk case's special classes, the event-world handler, the quest windows (NpcJobChangeQuest, NpcQuestProgress,
  NpcGateKeeper) and the mix windows are mapped, not played.
- The client's price routine, repair, rebuy and the shop tabs are not reconstructed.
- The OBB's bounds mode for characters (≠ 2) is a static reading of RenderPartObject's calls; NPC greetings by voice
  were not found in the talk path (the only sounds are 25 and 28).
- The world-2 map bytes `0x0b735420` are not filled natively (the refusal never applies).
