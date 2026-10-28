# World input, INPUT-001

## Target and evidence boundary

Target: the restored client text pinned by `scripts/pins.py` as `text`, SHA-256
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`, base `0x00401000`.
Names come from the second-section pin `data`, SHA-256
`c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`, base `0x01a7c000`.
These are the existing compatibility-environment captures. No original client or live service ran.

**Verified:** `input_keys.c` against original instructions through `scripts/validate_input.py`:
528 whole-array scan cases, 135,168 key decisions, and 42 binding-block cases; zero mismatches;
7/7 compiled planted mistakes caught. The five scan mutants break press, release, foreground,
Esc/Tab suppression and disabled-scan behavior. Two binding mutants swap Y's window and Q's slot.
The manifest registers this comparison and the native private test runs it.

**Static:** Capstone reading of `0x00efbfd2..0x00efd4d0`, its called handlers and the
`0x00c714bd` menu switch. Names are joined through the manager getter's field offset to the registration
at `0x00ac4a79`, rather than guessed from familiar MU key layouts. The comparison executes individual
key-test blocks up to their dispatch calls. It does not execute all the context guards or window bodies.

The Ctrl+Z/X names are confirmed by `00c71a41/00c71c6d` invoking
`mcRide.setRideInfo` and `mcGiantRide.setRideInfo`. They are mount controls. The helper controller is the
separate Home path; bare Z opens MacroMain.

The current native item policy is extracted unchanged from the existing HUD callback and exposed as
`mu_gfx_layer_use_item_hotkey`. The router calls it on a press, with the recovered 0..3 slot. Slot 0
contains the demo potion; the other slots are explicitly empty. This does not invent an item-domain intent
or a request builder. The old callback still uses its existing slot-0 demo policy.

**Native policy:** SDL events and scripts share `mu_world_rt_input`. Text focus and preedit take first
refusal, followed by native UI adapters, then Alt/Space/combat, then the walk input. Keys already down do
not trigger gameplay again. Focus loss releases keys and cancels composition. Win32 polling is replaced
by SDL events; the scan's platform inputs are modeled in the instruction comparison. The router does
not claim instruction equality for this platform adaptation or for demo combat/server rules.

## Scan

`0x00ec5475..0x00ec5576` updates 256 bytes in the object at ECX. The enabled byte is
`0x06fc9cb5`. It reads GetAsyncKeyState's high bit and requires GetForegroundWindow equal to the
client HWND at `0x06fc9c94`. States are 0 up, 1 release edge, 2 press edge and 3 held. A pressed
0/1 becomes 2; 2 becomes 3. An unpressed 2/3 becomes 1; 1 becomes 0. Other byte values stay unchanged.
Esc and Tab leave a 0/1 state unchanged when `0x0bdc5982` is zero and active HWND equals foreground.
Disabled input leaves the entire array unchanged. `0x00ec53a7` queries state 2 through
`0x00ec55e2`; `0x00ec53bb` queries state 3 through `0x00ec5618`.

## Coverage table

Addresses identify the original key branch, then its handler. A menu number is not a virtual key.
Unavailable means the router recognizes the binding and returns -1 with its recovered name. It never
falls through to an unrelated spell or claims that a panel opened. This is deliberate coverage of
missing domain/window implementations, not proof of those panels. J is an actual empty client handler.
Existing UI adapters retain their own eligibility and close rules.

| Key | Client branch -> handler and recovered name | Native route and boundary |
|---|---|---|
| Y | `00efc559` -> menu 13 -> `00c739e3`, PetInventoryFrame, manager +1a8 | Unavailable; pet inventory view/domain absent |
| I | `00efc593` -> menu 14 -> `00c73a2f`, InventoryFrame | GFx inventory toggle |
| C | `00efc5cd` -> menu 1 -> `00c733cf`, CharacterInfoFrame; excludes held Shift | Existing character-window adapter |
| Q/W/E/R | `00efc86c/8a6/8e0/91a` -> menus 16..19 -> `00c557db`, item slots 0..3 | Existing native item-hotkey action with slots 0..3; slot 0 uses the demo potion, other slots explicitly empty. No authoritative item-use request claimed |
| Ctrl+Z | `00efc964` -> menu 20 -> `00c71eab`, mcRide mount toggle | Unavailable; replicated mount controller absent |
| Ctrl+X | `00efc9ad` -> menu 21 -> `00c71efb`, mcGiantRide mount toggle | Unavailable; replicated giant-mount controller absent |
| X | `00efc9e6` -> menu 0 -> `00c73193`, IngameShop | Unavailable; shop/account service absent |
| T | `00efca20` -> menu 2 -> `00c733fe`, MyQuestInfo | Existing quest window adapter; requires quest tables/session |
| M | `00efca5a` -> menu 4 -> `00c73699`, MoveCommand | Existing map view adapter |
| O | `00efca94` -> menu 5 -> `00c75fe2`, winOption | Existing options adapter, isolated settings in verification |
| J | `00efcace` -> menu 6 -> `00c73690`, empty body | Consumed no-op, explicitly logged |
| P | `00efcb08` -> menu 7 -> `00c73603`, PersonalShop, manager +164 | Existing offline store action while inventory is open; unavailable without that precondition. Corrects former native party alias |
| F | `00efcb42` -> menu 9 -> `00c738a4`, FriendMenu, manager +230 | Existing social/friends adapter |
| G | `00efcb7c` -> menu 10 -> `00b0aed2`, Guildmatching_2024, manager +2b0 | Unavailable; guild-matching view/domain absent |
| B | `00efcbb6` -> menu 11 -> `00aae767`, GensRanking, manager +bc | Unavailable; Gens view/domain absent |
| N | `00efcbf0` -> menu 12 -> `00c73aeb`, MatchingSelect, manager +14c | Unavailable; matching view/domain absent |
| K | `00efcc2a` -> menu 15 -> `00c73abc`, GremoryCase | Unavailable; case inventory view/domain absent |
| V | `00efcc64`, also `00efc62a` -> InventoryFrame virtual open/close | Existing inventory alias |
| S | `00efcd10`, also `00efc6d6` -> `00aae767`, PersonalShopProductList, manager +168, requires inventory | Existing offline personal-store list action while inventory open |
| H | `00efc715` -> `00aae767`, expanded StorageInven, manager +104, requires warehouse | Unavailable; expanded warehouse view absent; does not open a remote warehouse |
| A | `00efcd95` -> `00aae767`, MasterSkillTree; class/state guards | Existing native master-tree adapter; native demo guards retained |
| U | `00efcea8` -> `00aae767`, SkillStampFrame | Existing skill-imprint adapter |
| D | `00efcee8` -> `00aae767`, CommandWindow, manager +134, with world/state guards | Unavailable; command view/controller absent |
| Tab | `00efd09d/00efd10d`, contextual map paths | Existing base-movie/map input; no world-state fabrication |
| Home | `00efd1a7` -> helper controller, including `00c8de1c` and helper start/stop requests | Unavailable; helper domain absent; no request reconstructed in this lane |
| Z | `00efd3a4` -> `00aae767`, MacroMain, manager +144 | Unavailable; macro view/controller absent |
| End | `00efc39a`, also `0095523a` -> `00b8a5e2/00b8a8cf/00b8a8fc`, HuntRecord, manager +1d0 | Unavailable; hunt-record view/domain absent |
| Ctrl+T/J/I/A/F/V | `00efc0da/104/1ad/1d7/280/29c` -> PlayGuide, fifth-tree plus item viewer, item viewer, fourth tree, `009603a5`, store request | Ctrl+A toggles the existing fourth-tree view; Ctrl+J toggles the fifth-tree view. Its separate item viewer remains unavailable. Other listed modifier routes explicitly refuse. Original class/window/transport predicates are not ported here |
| F1 | `00f07398`, `00f24f64` -> `00f2b13e`, close legacy windows 24/25 when already open | Unavailable; these legacy views are absent. No invented F1-open binding |
| Alt | `00efc7d3` -> setItemView `00efdca1` | Existing local ground-label toggle |
| Space | `00efd9ab` -> nearest eligible ground item; selection at `00efdb94` | Existing native pick-up adapter; verified offline reply, no real item mutation |
| 1..0 | UI skill-bar listener; selected-skill controller `0107e99a` | GFx bar selection when interface present; prior numeric demo casts without GFx retained and labeled native policy |
| Right mouse | selected-skill controller `0107e99a`, existing skill checks | GFx mouse first, then selected skill at picked actor, then walk mouse fallback |
| Esc/Enter/Back/arrows | scan plus existing text/window/scene controllers | Text/window first; existing native scene navigation without interface |
| IME preedit, candidate digits, commit | GFx IME state/path names and `IME.swf` candidate movie are static evidence, not emulated here | SDL TEXTEDITING -> layer compose; preedit keys stay with the OS candidate path; Enter cannot prematurely submit chat and candidate digits cannot select a bar skill or cast; TEXTINPUT -> UTF-8 commit. macOS owns candidate selection. Original IME.swf remains unbound |

All other VK values return to the native walk input without a panel action. This table covers the recovered
world branch and existing native routes; it is not a claim to have reconstructed every key in every scene,
movie, development tool or legacy window.

## Shared input script, version 1

Use `--input-script FILE` in mu-client, mu-shell, mu-world or mu-walk. `--script "..."` remains an inline
alias for short schedules. Both front ends use the same schedule parser and world action decoder. The
Wine repository is untouched; its injector can adopt this contract without linking native game code.

A UTF-8/ASCII file contains `FRAME:ACTION` tokens separated by whitespace or semicolons. `#` starts a
comment through the newline. Limits: 64 KiB per file, 128 events, 63 bytes per action, nonnegative signed
32-bit frame numbers. Events at the same frame run in file order. Unsorted events are accepted. An event
outside the run's frame range never fires. Schedule overflow, malformed numbers and truncated actions are
errors. Frame numbers are front-end iterations since the script was armed, not server WorldTime. An
injector should use a 25 Hz input loop and record its arm epoch; cross-client alignment still needs the
join/tick journal specified by LIVE-PLAY-001. Windowed slow frames do not become a claimed wall-clock oracle.

| Action | Meaning |
|---|---|
| `key:VK`, `down:VK`, `up:VK` | Tap, press, release. VK is decimal/0x hex, 1..255, or one alphabetic key. Digits use numeric VK, e.g. 49 for the 1 key |
| `move:X,Y` | Drawable-pixel mouse position, signed 16-bit coordinates |
| `ldown:X,Y`, `lup:X,Y`, `rdown:X,Y`, `rup:X,Y` | Explicit button edge and position |
| `wheel:N` | Signed wheel detents, -100..100 |
| `text:UTF8` | Committed text; percent-encode spaces, semicolons, percent signs and non-ASCII bytes |
| `compose:CURSOR:UTF8` | Preedit; cursor is a code-point index, -1 to cancel, percent encoding as above |
| `focus:0`, `focus:1` | Lost/gained focus; loss clears held input and preedit |

For example:

```text
# scene flow aliases are mu-client/mu-shell only
10:enter 14:enter 30:enter
40:move:361,237 42:rdown:361,237 43:rup:361,237
200:key:32
210:key:13 211:compose:1:%E4%B8%AD 212:key:49 213:text:%E4%B8%AD 214:key:13
```

Coordinates and timings depend on the fixture and viewport. They are inputs, not actor/item identifiers.
There is no privileged cast, grant-item, stat-write or server-packet action in this format. Legacy
`--combat-script`, `--item-script` and other subsystem fixtures remain development adapters, not this
cross-track input format. The native-data guard treats arbitrary argv values as possible paths; very long
inline schedules can hit the filesystem filename limit, so files are the canonical interface.

`mu_world_rt_input` returns 1 consumed, 0 walk/unbound, -1 known but unavailable; the action decoder also
returns -2 malformed. Scripted world actions report the result. `input_state` and `input_items` rows in
mu-client report casts, selected-skill success/refusal, pick-up requests/completions and demo drops. GFx
logs and actual state transitions, rather than the return code alone, establish whether a panel opened.

## Verification and remaining work

See [the milestone handoff](../handoffs/INPUT-001.md) for the final gate, retained proof and exact counts.
The unavailable rows remain work for their named domain/GFx milestones. They are deliberately not
reported as working panels. A full original-candidate UI comparison and live cross-track playback remain
open; this lane proves the native focus/commit path and blocks gameplay fallthrough.
