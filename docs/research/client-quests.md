# Quests: the quest system, guide, class upgrades and tracker

Sections 1-7 record NATIVE-QUEST-001. Section 8 supersedes its guide, class-upgrade, tracker, move and wrap gaps.

This note maps the client's quest system (the "MU quest" of MUQuest/MUQuestString: tutorial, rewarding and
repeatable quests given by NPCs), the quest packets' state updates, the windows that show it (NpcQuestProgress,
npcdialogue's quest list, MyQuestInfo) and how the native client plays it offline. There is no server: the
server's answers are a labelled local demo. The packet layer's encryption (C3/C4) and the XOR obfuscation of two
quest sub-codes stay out of scope.

Pinned inputs, as in [client-hud.md](client-hud.md): restored text capture09 `2bd5f2e9…3724` at `0x00401000`,
second image section run10 `c985e2e6…a0672f` at `0x01a7c000`; a live read of the running client (below).

Labels:

- **verified**: the client's instructions ran in Unicorn (`scripts/validate_quest.py`) and their result equalled
  `reconstructed/quest` (libquest);
- **runtime**: read from the running client's memory (the live snapshot) and equal to libquest's build;
- **static**: read from the decoded instructions (Ghidra/capstone), not executed;
- **modelled**: a validator stand-in, not client code;
- **demo**: a native stand-in for the server.

## 1. Data (runtime)

The quest definitions are two Lang.mpr tables (NATIVE-LANG-002's survey: MUQuest "map", MUQuestString "read").
Their records come from a live read: `live-readers/langread` gained two options, `node:OFF=BYTES` (MUQuest's
nodes carry 0x104-byte records; the old read copied the table's span, 0x40 bytes) and `map:PTR+OFF=BYTES[,obj=N]`
(a std::map behind a pointer variable, with the node values' objects). The read (2026-10-21, lock 19:17:58–19:20:10,
one client at the server list for about 90 s, closed with taskkill; plaintext local):

```sh
langread PID lang4.bin node:0x137c=0x118 'map:0x1ec2e60+4=0x18,obj=0x38' 'map:0x1ec2e60+0xc=0x18,obj=0xc' \
    'map:0x1ec2e60+0x14=0x18,obj=0x6c' 'map:0x1ec2e60+0x1c=0x18' 'map:0x1ec2e60+0x24=0x18'
scripts/live_lang_to_plain.py lang4.bin --out LOCAL/lang      # adds quests.tsv, queststrings.tsv, itemleveltip.tsv
```

**MUQuest** (`0x06fbbddc`, map +0x38, 484 records; the record builder `0x0113eb75` takes three script lines per
quest, static): `+0` index, `+4` name (std::string), `+0x1c`/`+0x20` (0 in every record), `+0x24` the accept block
(30 ints, first 0), `+0x9c` the goal block (26 ints, first 1). Read by their consumers: accept[1] is the group the
requests carry, accept[4] picks MyQuestInfo's button label, accept[5] the NPC class NpcQuestProgress names;
goal[1] the goal type, goal[2]/goal[3] the item or monster, goal[4] the count, goal[8] the world (type 8),
goal[11]/goal[12]/goal[13] exp, zen and contribution, goal[14..22] three reward items (group, index, level).
The other fields (accept[6..7] look like level bounds, accept[14..29] like class flags, goal[7..10] like the move
target) have no consumer in the reconstructed code.

**MUQuestString** (`0x06fbbd9c`, map +0x38, 1,975 records): `+0` index, `+4` text, `+0x1c` type, `+0x20` quest index.
**ItemLevelTooltip** (`0x06fbb9b0`, map +0x38, 105 records): `+0` name, u16 `+0x18` group, `+0x1a` index, `+0x1c`
level (the reward text names level items by it).

Plaintext (MU_LANG_DIR, local): `quests.tsv` (index, name, +0x1c, +0x20, the two blocks), `queststrings.tsv` (index,
type, quest, text), `itemleveltip.tsv`.

## 2. The quest system (verified, runtime)

A function-local singleton `[0x01ec2e60]` (getter `0x00be6fc4`, 0x2c bytes, constructor `0x00fe249e`, its init
`0x00fe25b5` creates categories 2, 3 and 4), built while MUQuest loads: the record builder calls `0x00fe138b`
(quest object) and `0x00fe15e9` (dialogue object) for every record.

| Member | Content |
|---|---|
| +4 map index → quest | 0x38-byte objects (`0x00fdfc65`): +0 record, +4 index, +8 name, +0x20/+0x24 record +0x1c/+0x20, +0x28 category, +0x2c state, +0x30 count, +0x34 seen |
| +0xc map id → category | 0xc bytes: +0 id, +4 map index → quest of the **active** quests |
| +0x14 map index → dialogue | 0x6c bytes (`0x00fe74cb`/`0x00fe764a`): MUQuestString of the quest in index order: type 1 title (+4), 2 pages (map +0x64), 3 progress text (+0x1c), 4 complete text (+0x34), 5 summary (+0x4c); assignments, the last record wins |
| +0x1c map item code → value | item goals (type 1) of active quests: the code → accept[1], inserted when absent (`0x00fe2711`), erased when the value matches (`0x00fe2763`) |
| +0x24 map index → value | set by F6 0x82, erased by F6 0x83 (no reader found) |

Routines: category `0x00fe1a06` (1..199 → 2, below 400 → 3 — also index ≤ 0 —, 400..599 → 4, 600..999 → 3, else −1);
lookups `0x00fe14d4` (quest), `0x00fe1695` (dialogue), `0x00fe1506` (category), `0x00fe1555` (item value, −1);
activation `0x00fe16e4` (category set, item map, the summary HUD's add `0x00c89ff9`), `0x00fe17db` (removal, the
summary's remove `0x00c8a072`), `0x00fe18c4` (clear every set and the item map, the summary's clear). The state
values: 0 not taken, 1 in progress, 2 complete (reward), 3 and 4 (NpcQuestProgress treats 4 like 0).

The live snapshot holds the client's own system: 484 quest objects, 484 dialogues, three empty categories; libquest
builds the same from the plaintext (section *Verification*).

## 3. Packets (verified unless noted)

The receive dispatcher `0x01287ead` sends opcode **0xF6** to the sub-dispatch at `0x0128a429` (packet[3]):

| Sub | Handler | Effect |
|---|---|---|
| 0x6f | `0x012510fe` | quest +6: reset, state 1, activate; MyQuestInfo's tab refresh, UpdateQuestChecked |
| 0x70 | `0x0125313f` | the character's quests (decoded payload: count +4, 10-byte entries from +6: quest +2, count +6, state +8, seen +9): clear, set, activate each; the open tab's refresh |
| 0x71 | `0x0126d65c` | an NPC's quests (count +4, 6-byte entries: quest +2, state +4) → npcdialogue's quest list `0x00be9c75` |
| 0x72 | `0x01222933` | accept answer (+8 result): 0 → state 1, count 0, NpcQuestProgress shows the quest (SetContents + open, or page + refresh), activate, MyQuestInfo refresh; 1 → notice GlobalText 0x118b |
| 0x73 | `0x0122287a` | give-up answer: 0 → remove, the tab's refresh |
| 0x74 | `0x0122adf5` | complete answer: 0 → close NpcQuestProgress, remove, refresh; 1..4 → message boxes (GlobalText 0xb00; 0x177/0x13d5/0xb17 with 0x176) and the button back to "Close" |
| 0x75 | `0x01253577` | progress: count +8, state +10; NpcQuestProgress page + refresh, the tab re-selects the quest it shows, the summary's update |
| 0x81 | `0x012533c9` | notice "Cannot move to %s." (GlobalText 0x154a, map name of +4) |
| 0x82 / 0x83 | `0x01253713` / `0x01253113` | value map +0x24 set / erase |
| 0x1c, 0x50/0x51, 0x56/0x7b | `0x0124cbb0`, `0x00be45c7`, inline | classic (job change) quest list, the guide quest tab, the hero's auto-move: static, not played |

0x70 and 0x71 first XOR the bytes after the header with a key hashed from the packet's last four bytes and three
bytes at `0x06fca280` (`0x00d50954`/`0x00d509b6`/`0x00d50b0b`): out of scope; libquest takes the decoded payload.

Requests the client sends (C1, verified): F6 0x71 (NPC: the dialogue's request 901, `0x00bea599`), F6 0x72 (accept
when no page is left: accept[1], quest), F6 0x74 (complete: NPC accept[5] or 0 from MyQuestInfo, accept[1], quest),
F6 0x7d (complete for accept[4] = 2), F6 0x73 (give up), F6 0x77 (seen), C1 0x54 (an NPC window closed); F6 0x01
from the inventory insert handler for item goals (`0x01227c51`, static).

**The NPC flow.** A talk ends with the NPC dialogue packet **F9 01** (handler `0x0126d5da`: dialogue NPC +4,
contribution +8; it opens npcdialogue `0x00be842c` when that is closed, static). The NPC's NPCDialogue.bmd state 0
offers request 901 → F6 71 → the quest list ("1. [Q]title" per quest) → a choice → NpcQuestProgress with the
quest's pages ("1. Yes / 2. No", the last "1. Accept") → F6 72 → the conditions → F6 75 progress → the NPC again →
state 2: the complete text and "Complete" → F6 74.

## 4. Texts (verified)

**Goal line `0x00fe1a52`** → {font [0x06fc9ca4], colour, text}: colour 0xff67bfdf in state 2, else 0xff1e1eff;
by goal type: 1 item "%s %s x %d/%d" (item name, GlobalText 0x1244), 2 monster (Npcname, 0x1077), 3 "Level: %d %s"
(0xafc), 4/5 0xcb1, 6 0x153d, 7 0x153f, 8 0x153c with the world's name, 9 0x153e, 10..16 0x1540..0x1546 (count,
need); anything else 0x551 in 0xff67bfdf. **Reward lines `0x00fe1e92`** → font [0x06fc9ca8]: "Exp.: %d",
"Zen: %d", three items "%s: %s x %d" (element items with GlobalText 0xe81..0xe85, "+%d" for kinds 1 and 3, the
ItemLevelTooltip name when one matches), GlobalText 0xbb2 (contribution), joined with "\n". **HTML line
`0x0096fe90`**: "" for an empty text or "\n", '<' → "&lt;", the colour ABGR → RGB "%06x",
`<font color='#…'>…</font>` (bold variant), `<BR>`.

## 5. The windows (verified; the movies' ActionScript read with JPEXS, static)

**NpcQuestProgress** (manager +0x10c, handler 0x168 bytes, vtable `0x01a95784`): SetContents `0x00bee2b3` (the quest,
its dialogue pages into a deque), ShowPage `0x00bee333` (states 0/4: the next page with SetQuestMentDivide(text, "#")
and the choices "1. Yes|Accept;2. No;", or the accept request when none is left; other states: the progress or
complete text and the conditions `0x00bee614`: SetUPCText, SetConditionRewardText, the button "Complete"/"Close"
`0x00beea7a`; SetUIType 1/2), refresh `0x00bee997` (SetQuestMent with the movie's wrapped text, SetSelectBtnContent),
open `0x00bedfb4` (SetUIOpenText: GlobalText 0xd84, the title, the NPC's name, the hero), close `0x00bee1fa` (C1 54),
OnLoad `0x00bedd69`, the choice `0x00beebc2`, the confirm `0x00beec0b`, the keys `0x00bede37` (1..9, Esc; static).

**npcdialogue's quest list** `0x00be9c75`: list mode +0x1d04, QuestWords 0x5dd/0x5de as text, "%d. [Q]" + the
dialogue title (or the quest name) per quest, wrapped to 500 pixels (`0x011ff794`, modelled: one line), pages of 13
lines (`0x00be8bdc`), SetDialogueMent/SetSelectBtnContent (`0x00be8724`). The loop's "leave" branch (QuestWords
0x3ef) is dead code: it tests the entry index against the entry count inside a loop that stops before it. The
choice (`0x00be906d`, list mode) opens NpcQuestProgress and closes the dialogue.

**MyQuestInfo** (manager +0x114, handler 0x88 bytes, vtable `0x01a94f70`; T in the native client): tabs 0 guide quest
(GuideQuest table, not played), 1 class upgrade (classic Quest.bmd, not played), 2/3/4 the quest categories
(GlobalText 0x1522..0x1524, tab objects `0x00d4f16e`). Open `0x00be420e`, close `0x00be42dc`, OnLoad `0x00be3ab5`
(InitText object, SetPosCenter, CreateTabButtons `0x00be4922`), UpdateQuestChecked `0x00be4732`, the tab's list
`0x00d4f485` (SetMyQuestList objects {Index, QuestIndex, Name "%d. %s", NewQuest}, or GlobalText 0xb09), select
`0x00d4f3ac` (SetMyQuestDivide of the summary or title), show `0x00d4f2e0` (seen → F6 77, conditions `0x00d4fa92`,
buttons `0x00d4fe25`: "Give Up Quest", "Go Now"/"Get Reward"/"Move to NPC"), the action `0x00d50067` (complete
request or the move `0x00d5029b`, static), give up `0x00be436d`, QuestTextWidth `0x00d4f43e`.

Mapped, not played: QuestProgressInfo (+0x118, a notice movie), QuestSummary/winQuestSummary (the summary HUD the
system notifies; its handler `0x00c89f..0x00c8b0`), NpcJobChangeQuest (+0x108, classic quests with Dialog(kor)),
NpcGateKeeper.

**Quest marks over NPCs: not found.** The models questionmark_1/2 (`0x734`/`0x735`) belong to the mix window's
random-result display (`0x00d17b31`), and the GFx image `quest!.ozd` is referenced by no converted movie and by no
string of the client. No NPC quest mark is drawn natively.

## 6. Native

- `reconstructed/quest` (libquest): the data, the system, the packets, the texts and the windows' game side; every
  client effect is a log line (`invoke WINDOW METHOD [JSON args]`, `value …`, `show`/`hide`, `send …`, `notice`,
  `msgbox`, `summary …`), also delivered to a sink as it happens, so a movie's callback reaches the client code
  before it goes on, as in the client.
- `native/core/mu_quest`: the session (tables from MU_LANG_DIR) and the **demo server**: the NPC's list from the demo
  file's `quest NPC QUEST[:STATE] …` lines, accept, complete (state 2 only; a labelled chat line with the reward),
  give up, progress from monster kills (goal type 2 by class, 8 by world; talk goals 4..6 complete when accepted).
- `native/core/mu_npc`: demo rows `dialog SERVER-CLASS DIALOGUE-NPC [contribution]` answer with F9 01; `quest` lines.
- The GFx layer: NpcQuestProgress and MyQuestInfo as optional movies driven by libquest's invokes; their callbacks,
  npcdialogue's wrapped text and window keys go to the host (`quest_call`, `dialog_wrapped`, `window_key`).
- `world_gfx` (mu-world, mu-client): the session, the 901 request, T (layer choice: the client's key scan is not
  reconstructed), 1..9/Esc on NpcQuestProgress, script verbs `qnext qno qok qclose qwin qtab:N qsel:QUEST qgo
  qgiveup qkill:CLASS qset:QUEST:COUNT`; `mu_combat` reports kills.
- Lorencia demo: a Guardsman (224) stands in for the Shadow Phantom Soldier (257 is not in the extracted class
  table) with `dialog 224 257` and `quest 257 7 10 440` (Budge Dragon, Hound, Spider hunts).

## Verification

`scripts/validate_quest.py --snapshot lang4.bin --sequences 80 --length 30 --text-rounds 3 --mutations`
(2026-10-21):

| Family | Client code | Cases | Result |
|---|---|---:|---|
| category | `0x00fe1a06`, −10..1100 and 200 random | 1,311 | equal |
| runtime | the running client's quest system (snapshot) vs libquest's build | 974 | equal |
| build | `0x00fe249e` + `0x00fe138b` + `0x00fe15e9` (+ `0x00fe764a`) for every record | 974 | equal |
| lookup | `0x00fe14d4`, `0x00fe1695`, `0x00fe1506`, `0x00fe1555` | 1,480 | equal |
| text | `0x00fe1a52`, `0x00fe1e92`, every quest × 3 random states/counts/item answers | 2,904 | equal |
| html | `0x0096fe90` | 300 | equal |
| packets | the ten handlers: 80 sequences × 30 random F6 packets (effects, quest objects, maps after each) | 7,200 | equal |
| windows | the windows' routines: 80 sequences × 30 window actions and packets (effects, state) | 5,904 | equal |

21,047 cases, 0 mismatches, about 2 min 16 s. The report counts every effect kind the client produced (all invokes of the
three windows, the five requests F6 72/73/74/77/7d, C1 54, message boxes, notices, the summary calls, the move).
Six planted mistakes in the C are caught (category boundary, the exp line, the page choice text, the progress
packet's count offset, the dead "leave" entry, the give-up button). Modelled (not client code): the heap, the
iostreams and boost::format of the formatter, sprintf, the UTF-8 conversion, the GDI font calls and text
wrap/fit, the item manager's names and kind answers, the map-name function, the GFx manager and Scaleform values,
the packet send, message boxes, notices, the summary HUD, QuestWords, the hero's name, the 0x70/0x71 key hash.

Tests: `reconstructed/quest/test_quest.py` (synthetic plaintext: category, parsing, dialogues, texts, HTML, the
accept/progress/complete packets, MyQuestInfo's list); `native/tests/test_native_quest.py` (the session on synthetic
tables, F9 01 rows in mu-walk; private: the validator and the Lorencia demo in mu-world).

## Renders (local)

`~/Documents/mu-mac-tools/native/renders/quest/`: `flow/` (the NPC's list, NpcQuestProgress pages, the conditions,
MyQuestInfo with the quest, 3/3 progress, the complete page, the empty list; `run.jsonl`), `combat/` (real kills
counting), `validate-quest.json`.

```sh
export MU_GFX_LIB=…/libmugfx.dylib MU_LANG_DIR=…/lang MU_GFX_SINGLE_BUFFER=1
native/build/mu-world --game-root "$MU_GAME_ROOT" --headless --backend gl --no-audio \
    --placement native/world/lorencia-demo-placement.txt --npc-demo native/world/lorencia-demo-npc.txt \
    --gfx MOVIES --tile 133,127 --npc-script "5:click:soldier 60:option:1 90:option:0 120:qnext 130:qnext \
    140:qnext 150:qnext 170:qclose 180:qwin 200:qtab:2 215:qsel:7 240:qkill:2 245:qkill:2 250:qkill:2 270:qwin \
    280:click:soldier 330:option:1 360:option:0 390:qok" --frames 460 --every 10 --out-dir DIR
```

Movies: convert `NpcQuestProgress MyQuestInfo` with the NATIVE-GFX-002 options next to the NPC set.

## NATIVE-QUEST-001 gaps at handoff

- Not played: the guide quest tab (GuideQuest is not in the snapshot), the class-upgrade (classic Quest.bmd) quests
  and NpcJobChangeQuest, the quest summary HUD (QuestSummary/winQuestSummary), QuestProgressInfo, the move-to-target
  button (`0x00d5029b`), the event-map tab, the 0x1c/0x50/0x51/0x56/0x7b sub-codes, the 0x70/0x71 XOR layer.
- The movies' callback decoding (`0x00beec8c`, `0x00be4b89`) is a static reading; the native host maps the same names.
- The text wrap and fit use the client's font metrics (modelled: one line; no "..." cut).
- The demo server's rules (which quests an NPC offers, progress, rewards) are choices; reward items and the zen/exp
  update packets are not sent.
- No quest marks over NPCs were found in this build.


## 8. Guide, class upgrades, tracker and Go Now, NATIVE-QUEST-002

Implemented 2026-10-22 in `quest_guide.c`, `quest_classic.c`, `quest_summary.c`, `quest_move.c` and `quest_wrap.c`.
The pinned text and image captures above remain the instruction oracle. `lang5.bin` is a local live snapshot
from 2026-10-22. No original-client gameplay was performed during this implementation finish.

### Data and executed routines

GuideQuest at `0x06fbb3d0` has a vector at +0x38 of chapter vectors. Its 0xf4-byte steps contain strings at
+0x0c/+0x60/+0xd0, class flags at +0x78 and reward item triples at +0xe8. The snapshot holds 186 steps in four
chapters. GuideQuestString at `0x06fbb414` has chapter titles in vector +0x44 and names in map +0x50, 196 records.
`langread` now supports `deep:` and `ptr:` captures. The converter writes `guidequest.tsv`, `guidestrings.tsv`
and `dialoganswers.tsv` locally. Quest.bmd has 200 XOR-decoded 1,000-byte class-quest records, read by the
client's loader `0x009f4866`. Dialog(kor)'s answer action and next-dialogue fields drive class quest choices.

| Component | Client instructions compared with authored C |
|---|---|
| Guide tab 0 | Constructor `0x00d4c27a`; init/list/chapter/check/state/text/conditions/buttons `0x00d49610..0x00d4ad11`; give-up `0x00d4b942`, box `0x00be436d`, Go Now `0x00d4bed6` |
| Guide packets | F6 50/51 through `0x00be45c7`; outgoing F6 51..57, including chapter abort 53 and cross-map target 54 |
| Tracker | QuestSummary routines `0x00c89f80..0x00c8ae30`, guide and MU quest entries, visibility, title, click and close lock; QuestProgressInfo onload and animation request |
| Quest Go Now | `0x00d4ffea`, `0x00d5029b`, `0x00d5060e`; walk/arrival/helper choices and cross-map F6 7A |
| Class upgrades | Manager `0x009f4244..0x009f52fe`; C1 C0/A1/A4/86 and F6 1C; NpcJobChangeQuest `0x00beb8b6..0x00becb32`; tab 1 `0x00d4dd38`, conditions `0x00d4e45c` |
| Text wrapping | `0x011ff794` and line cutter `0x01193941`; delimiters, measured width, scale, bullet, indentation, truncation; npcdialogue uses the same wrap |

The F6 1C refresh effect reaches the visible class tab without sending another F6 1C. The client's
`0x00be4901` dispatches tab vtable +0x30, `0x00d4e44a` forwards to the verified `0x00d4e45c` condition refresh.
The validator records the dispatcher effect and compares that condition routine independently.

### Native integration

Both mu-world and mu-client use `world_gfx` to play MyQuestInfo tabs 0/1, `winQuestSummary`, QuestProgressInfo
and NpcJobChangeQuest. The tracker movie uses `_level0.win` and the second UI callback channel `QuestSummary`.
Its loader globals and `onFileLoad` are supplied as the original MovieLoader does. The reward movie calls
`gotoAndPlay(0)`, which Ruffle leaves stopped at frame 1 with alpha 0. A local movie probe confirmed that
`gotoAndPlay(1)` advances the authored animation; the GFx adapter supplies that compatibility call and restores
the root's visibility for each reward. No movie bytes are changed.

The host measures text through the interface font, counts inventory items by code and level, and passes
same-map movement to `mu_walk_auto_move_ex`. Cross-map guide and quest requests call
`mu_map_travel_to(session, world, x, y)` from NATIVE-MAP-001. The host consumes `mu_map_take_teleport`, rebinds
walk/map sessions, and uses the live walk world for the arrival callback so one Go Now produces one transfer.
The map window continues to use `mu_map_travel_move`. Demo guide rewards update local zen/exp; server quest
rules and answers remain local choices. The native demo has no confirmation movie, so chapter-abort box
0x2e uses an explicit accept fallback; the insufficient-level warning 0x2f only displays its message.

The Lorencia demo now places the actual NPC 257. The CreateMonster extraction records a Player model 0xa91,
class byte 0x12, scale 1.0, armour set 24 at +13 and wing item 12:3. `validate_actors.py` now records CreateJoint
and the wing slot. The extracted call is one joint type 0x7f78, subtype 42; the earlier x5 handoff estimate was
incorrect. The native renderer uses the existing player parts and item glow renderer. Class mentor 229 uses
the same player-NPC path. Other player-model classes retain their previous unsupported status.

Demo rows are `guide STEP[:COUNT[:STATE]]`, `classic QUEST:STATE` and `classicnpc SERVER_CLASS`. In addition to
the existing quest verbs, scripts support `qtrack`, `qclass`, `qcnext:N`, `qcok`, `qgset:STEP:COUNT:STATE` and
`qcheck`. `qgiveup` routes to the guide handler on tab 0. Class quest counters only count while accepted and
clear on completion. Portable fixtures cover malformed A1/86 IDs 200..255 and exact-size wrap output buffers.

### Verification and limits

`validate_quest2.py --snapshot lang5.bin --sequences 30 --length 30 --wrap-cases 2000 --mutations` runs every
family in a fresh machine with its own stubs and RNG. Sharing one machine had leaked wrap's CRT thread and
import setup into the classic family. The isolated families reproduce the same result together or alone.
The C1 86 message box's callback owner is null, not its MsgBoxes receiver.

The single guide mismatch was an invalid caller state: checked chapter abort after the guide list was empty.
At `0x00d4ba15..0x00d4ba2a` the client reads vector[-1]. Two such operations are excluded; the native code
returns safely. Four random tracker sequences retained a pointer into a chapter vector after it was rebuilt;
the client later reads destroyed strings. Those sequences end at the dangling pointer, and the exclusion
counts are in the report. The native tracker retains safe values. The classic client can also step below
quest zero when random class/state combinations have no allowed record. Those sequences stop and are counted
in coverage. These undefined-memory states are not claimed equal.

The heap, CRT/iostream formatting, GFx value/window calls, item and map names, helper availability, path/send
results, GDI per-byte metrics and message boxes are modelled. Native CoreText shaping, Ruffle composition,
map loading and demo server rules are integration checks, separate from instruction comparisons. The wrap
return may report max_lines + 1 like the client; native indentation stays inside the supplied buffer.

The local reports and render runs are under `~/Documents/mu-mac-tools/native/renders/quest2/`. The
NATIVE-QUEST-001 regression report there has 12,914 cases, zero mismatches and 6/6 planted mistakes caught.
The final NATIVE-QUEST-002 run compares 7,004 cases with zero mismatches and catches 5/5 planted mistakes.

| Family | Cases |
|---|---:|
| guide-data | 383 |
| guide | 832 |
| summary | 847 |
| move | 900 |
| wrap | 2,000 |
| dialog-wrap | 900 |
| classic-data | 400 |
| classic | 742 |

The classic count includes 35 direct tab-refresh calls. Coverage also records eight sequences stopped when the
client's current quest wrapped below zero. Mutation checks use wrong guide count offsets, tracker visibility,
move coordinates, wrap scale and packed class-state masks. Portable checks cover the public packet dispatcher,
class mentor's normal logging, untaken/completed kill accounting, exact-size wrap output, malformed state IDs,
the second-layer tracker callbacks and inventory membership while an item is held.

Local render folders `guide/`, `travel/`, `walk/` and `notice/` contain frames and `run.jsonl`. The guide run opens
Sebina through an NPC talk, shows tab 1 and aborts a guide chapter through F6 53. The travel run reaches Noria
168,86 with one transfer, counts three hunt kills and grants two guide rewards. The walk run reaches Lorencia
149,126 without a transfer. The notice run plays the completion banner twice.

Remaining gaps are the event-map tab, F6 56/7B auto-move answer details, real server rules and reward item
insertion. NPC 257's cosmetic joint is recorded but not attached in the native scene. No quest marks over
NPCs were found. The 70/71 hash layer and network encryption remain outside this milestone.
