# Overhead text: names, monster HP bars and chat bubbles (NATIVE-NAMES-001)

This finding answers how the pinned client draws the text over characters, monsters and NPCs, and joins it to the
native world:

- name plates (colours, when they show, where they sit, the font), guild and server lines, gens marks;
- the selected monster's name and HP box;
- chat bubbles above a character;
- the native session's wiring (`mu-world`, `mu-walk`, `mu-client`) and its stand-in drawing.

Labels used below:

- **verified**: authored C equals the client's instructions under Unicorn on every compared case
  (`scripts/validate_names.py`);
- **static**: a reading of the decoded instructions that was not executed;
- **live**: compared with a window capture of the running game (an existing capture of NATIVE-LIGHT-001, no new live
  run);
- **demo** / **viewer choice**: native inputs or drawing that are not client behaviour.

## Identity

| Input | SHA-256 |
|---|---|
| `main.exe` (target) | `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a` |
| Restored text at `0x00401000` (capture09) | `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` |
| Second section at `0x01a7c000` (run10) | `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f` |

`scripts/validate_names.py` refuses other inputs and records the SHA-256 (first 16 hex digits) of the bodies it runs:
head height `b4a85e6b…`, name builder `954ecb56…`, addInfo `5dd82f99…`, the update `1da4f9c1…`, setHp `e755cb43…`,
removeInfo `6f82d8aa…`, setTopMovie `f8979516…`, setMessage `c9f13cd4…`, the chat bubble `7d542051…`.

## Short answers

- **The 3D/2D layer draws no names.** Name plates, the monster name/HP box and chat bubbles are the GFx movie
  `hudPlayerName` (loaded by the base movie into `mcBottomHud`, NATIVE-GFX-003). The legacy `CreateChat`/
  `RenderBoolean` path of older MU clients is not used for them. The game side is the movie's handler (vtable
  `0x01a86478`, constructor `0x00afaff8`); it builds the plates' data and moves the clips every frame.
- **Who gets a plate.** `addInfo` takes object kinds 1 (player) and 2 (monster) only. `SetMonsterInfo` `0x013b8ade`
  gives NPC classes kind 4 (and traps 8, a few classes 0x80), so **NPCs have no overhead name** in this client. The
  live capture agrees: the town NPCs show nothing, the hero shows "Nighty", players with a personal store show the
  store box (`PlayerStore`).
- **Colours.** Players: by PK level (`0x00c8502c`: 0 `#96FFF0`, 1 `#568CEE`, 2 `#8CB1EE`, 3 `#FFDC00` (normal; the live
  "Nighty" is this yellow), 4 `#FF9600`, 5 `#FF4400`, else `#FF0000`), size 14. Monsters: plain white (the text
  field's colour), or `#FF3319` size 12 when their level is above the hero's level + master level (classes 0x2a9 and
  0x2b2 excepted). Guild lines: `< guild >` in `#C8FF00` for the hero, `#FF0000` for relations 2 and 8, `#FFFFFF` for
  0, `#C8FF00` otherwise; server lines `< server >`.
- **When they show.** Monster boxes: when the option "monster info" (handler byte `+0x44`, default 1, set from the
  option window or the option packet bit 0x10) is on, or the monster is the character under the cursor
  (`0x01cf1154`, through `+0x48`). World 0x8b creates monster boxes hidden. Player names: the option byte
  `[[0x01d22c7c]] + 0x23` (`setPlayerNameShow`). Player HP bars: a duel partner, a party member (party window HP) or,
  with two option flags, the hero's own bar. There is no Alt behaviour for characters (Alt is the item labels' view,
  NATIVE-ITEMS-001).
- **Where.** The clip sits at the projection (`0x0184a3ce`, window pixels) of the object position plus a head height
  on z: monsters use their name height (Npcname table `+0x1c`, copied to `c + 0x158` by SetMonsterInfo); players 180,
  205 with wings, 220..320 on rides, 300 in a special state, +20/+30 for some classes. Inside the movie the monster box
  hangs at (-62, -23) (name at +2, HP bar 109 × 11 at (6, 18)); the player's text sits centred 10 pixels above the
  clip, moved up by the HP bar when shown; the chat bubble sits above the name.
- **Font.** The movies' `$NormalFont` (GFx font library, NATIVE-GFX-002), 12 pixels in the text fields, the HTML
  `size` attributes above; no outline is set by the game.
- **Target info.** The selected monster's box is the same `MonsterInfoMC` (name, HP bar, attribute and resistance
  icons, a hidden HP text). The list of nearby monsters at the right of the live capture is another movie, not part of
  this milestone.
- **Chat bubbles.** The chat receive handler `0x00c6066a` passes normal lines and `#` shouts to `0x0169d87f`, which
  finds the first live character with that name and calls `setMessage({msg: "name: text", time})` on its clip: 10000
  ms, or 40000 ms for `#`. Party `~`, alliance `@@`, guild `@` and gens `$` lines get no bubble. The hero's own line
  gets its bubble when the server echoes it back.

## Routines

| Routine | Address | Status |
|---|---|---|
| hudPlayerName handler constructor (heights, defaults) | `0x00afaff8` | static |
| addInfo (character creation: viewport packets `0x0122c426`, `0x0122d413`, `0x0122e633`, `0x0122f1b6`, the join packet `0x0124cc64` for the hero, through `0x009a16a6`) | `0x00c82fd1` | verified |
| per-frame update (vtable +0x0c), character part | `0x00c81d1e` | verified |
| per-frame update, item part (NATIVE-ITEMS-001) | `0x00c82d37..` | static (not compared here) |
| head height | `0x00c8526e` | verified |
| name builder (GlobalText 4595 `%s[%d]`) | `0x00c84d8a` | verified |
| class colours / PK colours / guild colours | `0x00c84f00` / `0x00c8502c` / `0x00c85093` | verified |
| gens frame / strife gens | `0x00c84d08` / `0x00c851f4` | verified |
| guild text (table `0x0b44a6f4`, records 0x58: name +9, second name +0) / server text (`c + 0x44`) | `0x00c8510c` / `0x00c850e1` | verified / static |
| removeInfo (character deletion `0x0137c276`/`0x0137c457`, SetPlayerDie `0x01393a61`, dead fade `0x013a5ea1`, through `0x009a176b`) | `0x00c83a04` | verified |
| setHp (monster HP packet `0x0126eecf`, SetPlayerDie with 0/0) | `0x00c83afa` | verified |
| setTopMovie handler (selected key `+0x48`) | `0x00c83c9a` | verified |
| the tick's selection wrapper (`0x0185613e` calls it; `0x01cf1154`) | `0x009a1618` | static |
| monster info option (`+0x44`; option window `0x00c7635f`, option packet `0x0126f225`) | `0x00c83c86` | static |
| setMessage | `0x00c83d2a` | verified |
| chat bubble (400 characters, first live name match) | `0x0169d87f` | verified |
| chat receive: prefixes, GM sender `0x00c61a71`, block list | `0x00c6066a` | static |
| SetMonsterInfo: Npcname record copy, object kind | `0x013b8ade` | verified (every class 0..4095 + random) |
| movie event handler (addMC/delMC fill the clip map `+0x54`) | `0x00c81842` | static |

### The handler object

Constructor `0x00afaff8`: `+0x1c` 35 and `+0x20` 5 (item labels), heights `+0x24` 180 (player), `+0x28` 205 (wing),
`+0x2c` 220, `+0x30` 225, `+0x34` 280, `+0x38` 240 (rides), `+0x3c` 300 (state 2), `+0x40` 320; `+0x44` monster view 1,
`+0x48` selected key -1, `+0x5c` item view 1; maps `+0x4c` (key → info entry), `+0x54` (key → clip), `+0x60`/`+0x68`
(items).

The info entry (constructor `0x00c8734a`): key, type, name HTML `+0x20`, last x/y `+0x38`/`+0x3c`, HP `+0x40`, show
`+0x44` (1), elemental `+0x48`, four resistances `+0x4c`, three damage types `+0x5c`, HP shown `+0x5f`, name shown
`+0x60`, strife `+0x61`, gens frame `+0x64`, guild text `+0x70`, server text `+0x88`, a flag `+0xa0` (0; no writer was
found).

### addInfo (verified)

1. Nothing for a key already present, for kinds other than 1/2, or for a player of class 0x396.
2. The name: the name builder (`name`, `name[level]` for name kind 1, `name[level + 600]` for kind 2, GlobalText 4595),
   then the colour HTML above.
3. z = position z + the name height word `c + 0x158`; for players a z of exactly 0 becomes 180 (`+0x24`).
4. x, y = the projection truncated to integers. isShow = the monster view byte. HP = `(float)hp / (float)max × 100`
   truncated (binary32, unsigned inputs). For a duel partner (`[0x06fca290]` key, partner name = hero name)
   isPlayerHpShow = 1.
5. elemental (`c + 0x3268`), the four resistances, the three damage types of the monster class (table `0x06fbb664`),
   isPlayerNameShow (the option byte), isStrifeGens, GensFrame, GuildName and ServerName (raw, not yet in `< >`).
6. The entry is inserted, then world 0x8b hides monsters in the movie's copy only.
7. `addInfo({key, type, name, GuildName, ServerName, elemental, mark, x, y, hp, isShow, isPlayerHpShow,
   isPlayerNameShow, isStrifeGens, GensFrame, attArray, damageTypeArray})`; the movie answers with `addMC`, which puts
   the clip into the map.

### The per-frame update (verified)

For every clip key (ascending) with an entry and a character (the key → index → character lookup), else the next key;
an undefined clip ends the whole update:

- monsters: show = monster view, or 1 when selected; on change `_info` visibility;
- players: the clip is made visible if hidden; `setPlayerNameShow` on an option change; the HP bar (`setHp`,
  `setHpShow`, `_hp` visibility) for the duel partner, party members (when names are shown) or the hero with the two
  flags; `setElemental`, `setGensFrame`, `setGuildName("<font color='…' size='12'>&lt; guild &gt;</font>")`,
  `setServerName` (only when the server flag `0x0095f75d()->0x0095fb99()` is 1) and `setStrifeGens` on change;
- every type: the projection of (x, y, z + head height); when x or y differ (NaN counts as different) the clip gets
  `SetDisplayInfo(x, y, visible)`.

### Head height (verified)

Non-players: the name height word. Players: 300 in state 2 (manager `0x01d1dce0`, `0x0106b9f7(c, 2, 1)`); without a
ride (`c + 0x322e` = 0xffff) 205 with a wing, else 180, plus `c + 0x158 - 180` for classes 0x271/0x272, or +20 for base
classes 6/11 and +30 for 15; rides `0x1a02` 220, `0x1a03` 225, `0x1a04 0x19d7 0x184b 0x184c 0x1853 0x1854 0x185d 0x185e
0x28f7` 280, `0x1833..0x1836` 320, others 240, plus `(c + 0x158 - 180) / 2` for classes 0x271/0x272.

### Chat (verified bubble, static routing)

`0x00c6066a` reads the sender (10 bytes at +3) and the text (60 bytes at +0xd), drops blocked senders, and routes:
`~` party (type 5), `@@` alliance (7), `@` guild (6), `$` gens (9) without bubbles; `#` shout: the `#` is removed, a
40 s bubble (type 1), or 10 s for a GM sender (type 8); other lines 10 s (type 1, 8 for a GM). `0x0169d87f` builds
`name + ": " + text`.

## The movie side (static reading of the AS2 code)

`HUD.hudPlayerName` keeps three containers (monsters, items, players, in that depth order). `PlayerName` /
`PlayerNameMC`: `setData` sets the clip position and `_visible = isShow`; `updateMoviePos` joins
`[server<br>][guild<br>]name` (the name and guild disappear for strife gens), sizes the text field (width 200,
autosize), centres it, puts it 10 pixels above the origin and above the HP bar, and places the gens mark left and the
elemental icon right of the text. `MonsterName` / `MonsterInfoMC`: name text centred in a 121-pixel field, HP bar
(`TweenProgress.setValue(hp, 100)`), elemental, resistance and damage-type icons. `HudChat`: autosized text, a
scaled background, kept until `setInterval(validateNow, time)` removes it. Both clip classes scale to 83% when the
stage is lower than 700 pixels.

Positions in the movie's sprites (pixels, from the converted SWF): MonsterName `_info` (-62, -23), `_mark` (-25, -85);
MonsterInfoMC `_txName` (2, 2), `_hp` (6, 18), `_attribute` (118, 1), `_txHP` (2, -16); PlayerNameMC `_hp` (-54, 0),
`_txPlayerName` (-57, -19), `_GensMark` (-86, -27.5), `_attribute` (62, -21); HudChat `_txt` (-108, -112), `_bg`
(-118, -119); the HP frame is 109 × 11 with the value bar at (3, 3).

## Validation

`scripts/validate_names.py` runs the client routines in Unicorn (`scripts/client_ui_machine.py`) and compares each
result with `reconstructed/names/libnames` on the same synthetic CHARACTER records, handler state and host answers.
Modelled explicitly: the GFx value and display-info API, std::string/std::wstring and the formatter (`%s`/`%d`
substitution; the level is fed as `unsigned short`, `0x00b3cc1f`), the std::map nodes and iterators, the key →
character lookup, the projection (verified by NATIVE-FRAME-001; here a recorded function of its input, whose inputs
are compared too), the party window, option and singleton flags, the damage-type table, the Npcname getters and
GlobalText. Any other block outside the allowlist stops the case. Twelve planted mistakes (PK colour shift, name kind,
name height, base class, ride ids, resistance order, name option, hero HP, world 0x8b, gens option, server flag, level
+600) must be detected.

Private run (`--cases 1000 --negative 100`, about one minute):

| Section | Cases | Result |
|---|---|---|
| helpers: head height, name, guild colour, gens frame, strife, guild text | 6,000 each; class/PK colours 35 values each | 0 mismatches |
| addInfo | 6,000 calls (2,850 plates, 3,150 skipped), every member and the inserted entry | 0 mismatches |
| update | 1,000 worlds × 4 frames, 11,632 operations in order, entries after every frame | 0 mismatches |
| setHp / removeInfo / setTopMovie / monster view | 1,625 / 1,621 / 3,154 / 1,600 calls | 0 mismatches |
| SetMonsterInfo | classes 0..4095 and 1,000 random larger ones: kind, name, height, mark, byte | 0 mismatches |
| chat bubble + setMessage | 4,000 calls (1,634 bubbles) | 0 mismatches |
| negative controls | 12 planted mistakes | 12 detected |

Portable checks: `reconstructed/names/test_names.py` (worked examples of every helper and routine) and
`native/tests/test_native_names.py` (mu-walk on the synthetic world: creation, projection, HP packets, removal at the
dead counter 15, respawn, bubbles and their 10 s expiry, options, stand-in drawing, determinism). Private: the short
Unicorn run, Lorencia with the demo placement (hero + four monsters, eight NPC/effect classes skipped), and the GFx
route against the real movie (`MU_NAMES_GFX_MOVIES`).

## Native integration

- `reconstructed/names` is the platform-neutral handler; `native/core/mu_names` runs it for the session's characters,
  keeps a model of what the movie shows (each call's AS2 effect) and forwards every call to a sink;
  `native/core/mu_world_names` feeds it from mu-world: the hero (kind 1) and the placed actors (kind from SetMonsterInfo),
  positions, the demo combat's HP, deaths and respawns, the actor under the cursor and chat lines.
- With `--gfx` (base movie), `native/world/world_names_gfx.c` sends the calls to the real `hudPlayerName` through the
  layer: `addInfo`/`removeInfo` on the movie, `setHp`, `setHpShow`, `setGuildName`, … on `clip._info`, `setTopMovie` and
  `setMessage` on the clip, display-info changes as `_x`/`_y`/`_visible` (window pixels / Retina scale). The clips are
  addressed by the movie's names (`playerContainer.ply_<key>`, `container.mon_<key>`); the client keeps the `addMC`
  clip value instead. The movie loads asynchronously: the plates created before are replayed once its channel appears.
  `mu-client --gfx` attaches the same sink to the embedded world (`mu_world_embed_set_gfx`).
- Without the movie (headless software renders, CI), `mu_names_draw` composites a stand-in with the shared label
  helper `native/core/mu_label` (the movies' HTML subset through the GDI text boundary; one-pixel shadow, bar and box
  colours are viewer choices), laid out from the sprite positions above.
- The chat input's local echo (GFX-002/003) now also reaches the bubble (`mu_gfx_layer_set_chat_hook`); headless runs
  use `--chat-script "F:text;F:text"`.
- **Demo**: keys (hero 0x1234 as mu_combat, actors 0x100 + index), the hero's name (`--hero-name`, or the character
  select entry in mu-client) and level 400, monster levels 0 (never coloured), monster HP (mu_combat's demo points;
  100/100 without combat) sent after every change, the hero's chat echo, the option bytes (names shown, monster view
  on; `--monster-info 0`). Monster names and heights come from the Npcname table (`npcnames.tsv` of NATIVE-LANG-001 in
  `MU_LANG_DIR`); without it the placement label and height 200 are placeholders. The cursor pick is mu_combat's
  cylinder test, not the client's OBB selection.

Renders stay local under `~/Documents/mu-mac-tools/native/renders/names/`: `soft1/` (mu-walk, stand-in: bubble, hero
plate, monster boxes and HP), `gfx1/` (mu-world headless GL with the real movie: "Nighty" in `#FFDC00`, Bull
Fighter/Budge Dragon/Hound boxes with HP bars, the bubble, the Hound's box removed at its death), `client/` (mu-client:
the chosen character's plate, the town NPCs without plates, as in the live capture).

## Limits and next steps

- The item part of the update (labels following the cursor, `setItemView`) belongs to NATIVE-ITEMS-001; it is not
  compared here.
- Player stores (`setStore`, `0x00c84731`/`0x00c848fa`), castle marks (`0x00c84222`), `setPlayerName`
  (`0x00c8443d`) and `setMonsterName` (`0x00c84990`) are mapped, not reconstructed; the native session has no other
  players.
- The chat receive routing, the option byte sources and the hero-HP-bar flags are static; the native option bytes are
  demo values.
- The stand-in does not draw gens marks, elemental or resistance icons (the movie does with `--gfx`).
- The right-hand monster list of the live capture is another movie (not identified here).
- Next: wire NATIVE-LANG-001's `mu_lang` for the Npcname table once merged (the TSV reader reads its files), player
  stores and other players when a server or replay exists, and a live capture of a monster box and a chat bubble for a
  pixel comparison.
