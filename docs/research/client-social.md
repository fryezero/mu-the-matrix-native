# Social systems in the native client

NATIVE-SOCIAL-001 adds parties, trade, friends and whispers to `mu-world` and `mu-client` through GFx.
`reconstructed/social` holds game-side receives, `native/core/mu_social` holds offline server policy and
`native/world/world_gfx_social` drives the movies. The `--players` characters are demo partners.

This branch is WIP. Original party request/accept/leave/kick actions and messenger receives still need
instruction-led reconstruction. The demo policy and local room do not satisfy those parts of the task.

## Evidence and boundaries

Target `main.exe` SHA-256: `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
Inputs are restored Linux/Wine capture09 text, VA `0x00401000`, SHA-256
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`, and run10 image data, VA
`0x01a7c000`, SHA-256 `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`.
The validator checks both hashes. These are compatibility-environment captures, not native Windows evidence.
No client bytes, decoded data or captures are committed. Protection modules, network encryption and login
were not entered. No live character item transfer, trade or drop was performed.

"Executed" means client instructions ran under Unicorn and matched the C. "Static" means disassembly or
extracted ActionScript was read. "Modelled" identifies validator boundaries and native choices.

## Party

The dispatcher at `0x01288a7e..0x01288abf` maps `40/42/43/44` to
`0x01270d06/0x012719c9/0x0127178c/0x01271711`, a static reading.

| Routine | Observation | Execution coverage |
|---|---|---|
| `0x01270d06` | Big-endian request key at bytes 3/4 is stored before the block check; blocked requests suppress the prompt | Whole receive; shared handles, block lookup and popup modelled |
| `0x00c77c65..0x00c77e23` | Party-record fields and HP/MP arithmetic | Slice; names, allocation and insertion excluded |
| `0x00c7a7a2` | Server zero gives state 2; otherwise in-view exactly 1 gives state 1, others state 3 | Whole method; object lookup modelled |
| `0x00c789e2..0x00c78a80` | Clamp HP/MP percentages to 100 | Slice; enclosing count loop and name matching static, synthetic-tested |
| `0x00c6b2cc`, helpers `0x00c6ba5c..0x00c6baa6` | Skip hero/other server/world; type 10, slot key, name, `2*x`, `2*(256-y)` markers | Whole builder and coordinate helpers; STL, strings and GFx values modelled |

Static envelope: `C2 42` count at 4, 44-byte records from 5. Each record has name[10], number at 10,
world u16 at 14, tile bytes 16/17, signed i32 HP/max HP at 20/24, server at 28, MP/max MP at 32/36,
control at 40 and special at 41. Percentages truncate separately rounded binary32 `(100/max)*value`.
HP requires positive max HP; MP tests nonzero max MP. `C1 44` count at 3 has 13-byte records from 4,
HP/MP bytes then name[10]. `43` clears the party. Native guards reject malformed lists without changes.

The HUD uses `winParty`, placed at `_level0.instance1`. `SetMemberInfo` takes one array containing
sortIndex, name, channel, HP/MP, leader/me/state and buffs. `MastetrIsHero` is the movie's spelling.
Using `_level0.win` left test rows visible; the corrected path shows Hero and the demo party in native renders.
The legacy `PartyFrame` asset is not this HUD. Movie API claims are static ActionScript readings.

Demo request/accept/decline, leader kick and leave update the HUD, name-plate HP lookup and Tab markers.
Markers refresh after map clearing even when the party is stationary, because `delAllUnit` also hides the
party icon container. Social state survives world unload/load; the GFx host detaches and rebinds players.
Travel cancels a trade and restores reserved items. Leadership policy and demo HP/MP are authored server
choices. Original outbound request serialization and all original party dialog callbacks remain unverified.

## Trade

These addresses establish this executable's layouts; trade-open is opcode `54`.

| Routine | Observation | Execution coverage |
|---|---|---|
| `0x012822f4` -> `0x00c455e7` | Incoming request passes name[10] at +3 to the window | Static |
| `0x01282b17` -> `0x00c4577a` | `54` reply 1 opens/resets; name +4, level u16 +14, guild i32 +16; 0/2/4 select notices | Static |
| `0x01282bb0` | `38` partner removal, slot +3 | Whole receive wrapper; item-window boundary recorded |
| `0x01282b76` | `39` partner insertion, slot +3, item bytes +4 | Whole wrapper; item conversion/window boundary recorded |
| `0x01282b45` | `3b` partner zen, i32 +4 | Whole wrapper |
| `0x01282ae4` | `73` own zen answer; false clears, true uses proposed amount | Whole wrapper |
| `0x01282be3` -> `0x00c45b3e` | `3e` partner lock state | Whole wrapper and lock method |
| `0x012823f7` -> `0x00c45c09` | `bd` result | Whole result method; dispatcher/wrapper static |

Lock states 0/1 clear/set partner OK. State 2 warns once, clears both OK flags and sets a 25-frame wait.
GFx setters, warning display and sound are modelled. Result always closes. Result 1 succeeds without notice;
0/2/3/4/5/6/7 choose GlobalText `1ec/1ef/1f0/83c/1f0/e8f/e90`. The validator records IDs and close calls.

Static `Trade.swf` APIs provide two 8 x 4 grids, names, zen and lock controls. Item models use movie slot
coordinates plus window position/scale. Inventory clicks reserve existing items in the first fitting offer
rectangle. Any covered offer cell can return the item. Cancel restores its original inventory cells. At result
time an atomic inventory exchange removes offers and inserts incoming items before zen/results change.
Insertion failure restores the inventory and refuses the trade, including purchases made after locking.
Reopening cannot erase/duplicate an item. The partner offers one 1 x 1 potion through `partner-item`. Full incoming dimensions/options,
original tradeability checks and outbound serialization remain open. The reconstruction keeps incoming item
data as 15 opaque bytes; the demo renderer extracts code/level only. Without GFx the headless session uses
a separate two-item synthetic offer fixture, not the visible inventory.

Completion emits a chat result. Zen and partner timing are demo policy. Social zen is independent of existing
map/shop demo balances. Input zen explains `/zen AMOUNT`; the original numeric dialog is not ported.

## Friends, messenger and whisper

Executed list loop `0x0124123e..0x012412c8`: count byte 6, records from 7 with name[10] and server byte.
Native bounds cap at 50. Count/name/server iteration executes; copy and manager insertion are modelled.
Surrounding UI updates are static.

Executed whole whisper method `0x00c609b5`, caller `0x0122ab8e`: name +3[10], text +13[60]. The external
block predicate suppresses delivery unless the supplied option bypasses it. Chat type is 2. Strings,
option/block lookup and final chat call are modelled. Native `/w NAME TEXT` and the movie's `wisper` field
use that representation and do not create public name-plate bubbles.

`FriendMenu` and `FriendWindow` are the client's movies. Static ActionScript establishes `AddFriends`,
`AddChatRoom1`, `AddFriendAtChatRoom`, `SetChatTitle`, `AddChatText` and callbacks. Demo friends can be added
or removed. Talk selects a whisper recipient and opens one local room; its messages echo locally. GFx focus
routes text and keys to messenger input. Mail, invite/minimize lists, persistent friends, original messenger
receive handlers and room transport remain open. Unsupported controls send nothing.

## Reproduce and coverage

```sh
make -C reconstructed/social
python scripts/validate_social.py --cases 500 --mutations --output /LOCAL/social-validation.json
tools/.venv/bin/python -m unittest discover -s native/tests -p test_native_social.py -v
```

The private validator needs Unicorn and both captures; absence/hash mismatch is an error. The 2026-10-22
run passed **7,000 comparisons, zero mismatches, 10/10 planted mistakes**. Each family has 500 cases except
the five `trade_packets` wrappers, totaling 2,500. Families: party_request, party_fields, party_state,
party_bars, markers, trade_lock, trade_packets, trade_result, friends, whisper. Seed 1, marker seed 2.
Mutations change request byte order, field offset, state, clamp, map filter, lock wait, zen offset, result
notice, friend server byte and whisper blocking. This does not establish complete protocol equivalence.

Five reconstructed tests cover malformed input and state. Three native regressions cover request/leadership,
actual inventory reservation/cancel/commit, multi-cell offers, local messenger/whisper callbacks, stationary
marker refresh, host detach/rebind and two-world party persistence. Recording GFx tests are synthetic;
the real movies were checked separately in offline GL renders.
Regression probes also cover capacity changing between lock and result, and escaped quotes, backslashes,
newlines and Unicode in messenger callbacks. The draw decoder now preserves byte 3/5 item-code bits;
extended-code visual output has not been captured. Remaining review gaps are original party
actions and messenger handlers, not transport encryption.

Launch with the usual game root, `--players native/world/lorencia-demo-players.txt --gfx MOVIES`. P toggles
party, F opens friends, Y/N answers a request. Chat accepts `/party NAME`, `/trade NAME`, `/accept`, `/decline`,
`/leave`, `/kick NAME`, `/friend NAME`, `/unfriend NAME`, `/messenger NAME`, `/w NAME TEXT`, `/zen AMOUNT`,
`/ok`, `/cancel`. Click inventory items to offer, own trade cells to return. Script example:
`--social-script '1:trade:Aeris;3:accept;6:offer:0;8:partner-item;40:ok;40:partner-ok'`.
Other demo actions: `health:NAME,HP,MP`, `incoming-party:NAME`, `incoming-trade:NAME`, `partner-zen:N`,
`receive-whisper:NAME TEXT`. World embedding gives `mu-client` the same host and chat controls.

Local evidence: `~/Documents/mu-mac-tools/native/scratch/social/` and renders under
`~/Documents/mu-mac-tools/native/renders/social/checked-{trade,messenger,map,travel}/`.
Use `MU_GFX_SINGLE_BUFFER=1` for sparse headless captures; otherwise the first capture after showing a
window can contain its previous asynchronous texture. No live game was needed.
