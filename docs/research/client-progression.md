# Character progression: experience, levels, stat points and the class formulas (NATIVE-PROGRESS-001)

Pinned inputs: restored text capture09 (`2bd5f2e9…3724`) at `0x00401000`, second image section run10
(`c985e2e6…a0672f`) at `0x01a7c000`. The GlobalText strings named below come from the NATIVE-LANG-001
plaintext (local, never committed).

Labels:

- **Verified**: the client's instructions ran in Unicorn (`scripts/validate_progress.py`) and equalled the C in
  `reconstructed/progress`.
- **Static**: a reading of the instructions that was not run.
- **Demo**: a choice of the native offline server (`native/core/mu_progress`), not client or server data.

## 1. Where the values live

The hero's numbers are in one record, CharacterAttribute: the global `0x01d1df1c`, which is CharacterMachine
`[0x01d1df18]` + 8. Its getters and setters sit at `0x00a00066..0x00a00278` (static, their users verified):

| Offset | Field | Notes |
|---|---|---|
| `+0x000` | level (int) | SetLevel `0x00a00031` stores at most 400, then refreshes the level window (`0x00a00386` → `0x00c8d968`) |
| `+0x008` / `+0x010` | experience / next (u64) | the experience counts **within the level** (section 3) |
| `+0x018` | master level | `0x00a000e9` returns it only when the attribute's class byte has bit 5 (third class) |
| `+0x020` / `+0x028` | master experience / next | |
| `+0x030`, `+0x034`, `+0x03c` | master words of the 0xA0 0x22 / 0x60 answers | |
| `+0x040..+0x04c` | HP, MP, SD, AG maxima of a third-class hero | setHPMP `0x00c71772` reads these instead (static; live: Nighty's 117916 / 18526 / 135603 / 19224) |
| `+0x068..+0x084` | HP, MP, HP max, MP max, SD, SD max, AG, AG max | from the server; setHPMP's `hp`, `mp`, `maxHp`, … (static; live: a level-1 Dark Knight 1100, 200, 1100, 200, 52, 52, 25, 25) |
| `+0x187` | class byte | low nibble class index, bits 4..7 evolution |
| `+0x18a..+0x192` | strength, agility, vitality, energy, command (u16) | |
| `+0x198..+0x19e`, `+0x1a4` | added stats (items, buffs) | |
| `+0x194`, `+0x196` | PvP attack rate, PvP defense rate | class formula |
| `+0x1b6`, `+0x1c2` | attack speed, magic speed | from the server (opcode 0x55 sub 0x94) |
| `+0x1b8` | attack rate | class formula |
| `+0x1ba..+0x1c0` | attack damage min/max, left then right hand | class formula |
| `+0x1c4..+0x1ca` | magic damage min/max, curse min/max | class formula |
| `+0x1da`, `+0x1dc` | defense rate, defense | class formula |
| `+0x1e2` | free points (LevelUpPoint) | |

The **level used by every formula** is `0x00a00367` = level + master level (verified). The character window's level
row shows the same sum (live: Nighty, level 400 and master level 1200, shows 1600).

## 2. The class formulas (verified)

CharacterMachine `+0x2d98` holds a stat machine, one C++ class per class index: `0x00a0088d(class)` news the
object (`0x1e4` bytes) and calls its constructor (table at `0x00a00e39`); the constructors store the class index
at `+0x1d4` and the class's maximum speed `0x009942bf(index)` at `+0x1d8`. The 16 vtables (`0x01a7e8bc`, …) share
the base vtable `0x01a7e690` except slots 0, 0x18, 0x28 and 0x2c and a few others.

CalculateAll `0x00993a45(e0..e4)` runs: slot 0x3c, a memset, the stat totals `0x0098d2c4`, the set-option manager
`0x0098d397`, **slot 0**, the formula table `0x00993099`, slot 4 (the equipment's options, `0x0098d506`), slot 0x18
(the hand damage), the speeds/defense of items (`0x0099058c`), the master tree (slot 0x28) and more. Only part of
this is reconstructed:

- **Slot 0 of all 16 classes** (verified, 500+ cases per run, all classes): the base values from the stats. The stat
  sums are kept in **16-bit** locals (`(stat + extra + added) & 0xffff`), divisions are signed integer divisions,
  the PvP rates single-precision floats truncated (`cvttss2si`), every result a 16-bit word. Examples:
  - class 0 (Dark Wizard): damage str/8 ~ str/4 (both hands), magic ene/9 ~ ene/4, attack rate
    level·5 + dex·3/2 + str/4, PvP attack level·3 + dex·4.0, defense dex/4, defense rate dex/3, PvP defense
    level·2 + dex·0.25;
  - class 1 (Dark Knight): str/6 ~ str/4, PvP attack dex·4.5, defense dex/3; under buff `0x145` str/9 ~ str/6
    and defense dex/2;
  - class 2 (Elf): a bow or crossbow in slot 0 (weapon kind 2 or 1, item byte `+0x38` set) uses dex/7 + str/14 ~
    dex/4 + str/8 (0 when `+0x38` is 0), else (str + dex)/7 ~ (str + dex)/4; the right hand is 0 when slot 1 holds
    kind `0x4b`;
  - class 4 (Dark Lord): command counts (cmd/7, cmd/5, cmd/15 in the attack rate), no 0xffff clamp;
  - class 5 (Summoner): buff `0x12d` swaps the magic (ene/9 ~ ene/4) and curse (ene/18 ~ ene/10) formulas;
  - class 6: vitality counts (vit/15, vit/12), attack rate level·3 + dex·5/4 + str/6;
  - class 10: buff `0x17c` raises magic to ene/6 ~ ene/3 and halves the defense; class 12 uses str/2 in the attack
    rate; class 13 puts str/5 into the defense; classes 14 and 15 use integer PvP rates.
  The full set is `reconstructed/progress/progress_calc.c`, one function per class.
- **Stat totals `0x0098d2c4`** (verified): machine `+0x1bc..+0x1cc` = stat + extra + added.
- **Boundaries** (modelled with random answers per case): the buff test `0x0139f66e(Hero, buff)` and the equipment
  queries `0x00993731` (item counts), `0x0139d95f` (weapon kind), item `+0x38`, `0x00987982` (item of kind).
- **Not reconstructed**: the equipment options (slot 4/8, 1,563 instructions), the item set/socket/pentagram
  managers, the data-driven formula table `0x00993099` (manager `0x01d1dcb0`, source not located), the master tree
  bonuses (slot 0x28), the hand damage of slot 0x18 and the defense of items (`0x0099058c`). The native values are
  therefore those of a hero without equipment, buffs or master skills.

The **attack and magic speeds** are not computed by the client: the server sends them (opcode **0x55 sub 0x94**,
`0x0122a13d`: `+4` attack speed → `+0x1b6`, `+8` magic speed → `+0x1c2`, verified). The character window's speed row
`0x00b40380` (verified) shows the magic speed for class indices 0, 5 and 8, else the attack speed, plus the master
tree node `0x3f0` (through GFx manager `+0x1f8`, `0x00c354b7`, `0x00c2a236`, `0x00b48a9e`), +20 when attribute byte
`+0x1a6` has bit 0 or 3, halved under effect `0xb0`, at most the machine's maximum `+0x1d8`, as GlobalText `0x10be`
("%d / %d") with the maximum, only when it changed (window `+0xbc`/`+0xbe`). The class constructors store
`0x009942bf(index)` there (284, 288, 275, 351, 290, 188, 441, 273, 274, 384, 280, 304, 290, 350, 329, 285,
verified through the constructors), but the live machine holds **400** for both characters read: a later writer
(a server packet, `0x00ed70c5` stores a packet word there, static) replaces it.

## 3. Experience and levels (verified)

- **Experience table `0x00a00e79(int64 level)`**: n = level − 1; 0 for n ≤ 0, else `(n + 9)·n²·10` (64-bit), plus
  `(m + 9)·m²·1000` for n > 255 with m = n − 255 (that product in 32 bits, sign-extended); a negative result
  becomes 0. Checked for every level −2..1500 and random 64-bit levels.
- **The level's experience `0x00a00f4a`**: experience = 0, next = table(level + 1) − table(level). The client keeps
  the experience *within the level*: the level-up handler calls this after the level is set.
- **Kill experience, opcode 0x16 (`0x01234c08`)**: `+3..+4` key (big endian; bit 15: the monster died →
  `0x01393a61`), `+5..+6` experience (u16), `+7..+8` damage (big endian). An unencrypted packet is refused with the
  report C1 4D 02 00 16. With the monster found: the hero's attack target fields (Hero `+0x20` = 2, `+0x148`,
  `+0x40`) or the death, the damage number (`0x016912ae`, colour (1, 0.6, 0), scale 15, unless the world hides it),
  `+0x23` = 1, `+0x38` = 0. The experience goes to the master experience for a third-class hero (class byte bit 5),
  else to the experience; the chat line is GlobalText `0x6d6` ("Master EXP achievement %lld") or `0x1e6` ("Obtained
  %lld Exp") — the client passes a **32-bit** value to `%lld`, so the high half is the stack word above the
  arguments (an unrelated local: 0 in the validator, garbage possible in the client); then the experience bar.
- **Level up, opcode 0xA0 sub 0x06 (`0x01250b05`)**: `+4` level (SetLevel), `+6` free points, `+8` HP max (also
  HP), `+0xa` MP max (also MP), `+0xc` SD max, `+0xe` AG max (maxima at least 1, HP/MP at least 0), the HP/MP orbs
  (`0x00c71772`), `+0x10..+0x16` four words into `+0x1ae..+0x1b4`, the four character-window refreshes, the chat line
  `0x1e6` with **next − experience** (taken before the reset), `0x00a00f4a`, the stat machine's recalculation flag
  (`0x00a00fb7` → machine `+0x1d2` = 1), then the effects and the sound:
  - a third-class hero: CreateJoint `0x7f78` (Flare) subtype `0x2d` once and subtype `0x2e` 19 times, scale 80;
  - otherwise CreateJoint `0x7f78` subtype 0 fifteen times (scale 40, key 2) and CreateEffect `0x7f84`
    (Magic_Ground2) subtype 0 at the hero;
  - PlayBuffer `0x98`.
  The `level == 1` test after the sound jumps over its block unconditionally (dead code).
- **Master level up, 0xA0 sub 0x22 (`0x01285b68`)**: `+4` master level, `+6`/`+8`/`+0xa` into `+0x30`/`+0x34`/`+0x3c`,
  the chat line `0x6d6` with master next − master experience (`0x0095f547`), three window refreshes, the third-class
  joints, the master tree windows (bit 6). **Master experience, 0xA0 sub 0x60 (`0x01285efa`)**: `+4` master level
  (window refresh when it changed), `+6..+0xd` master experience and `+0xe..+0x15` next (big endian), `+0x16` into
  `+0x34`, the tree windows and the experience bar. Both handlers contain 76 NOP bytes in the restored text
  (`0x01285bda`, `0x01286256`) whose original content is unknown (static: executed as NOPs).
- **The experience bar `0x00c5125b`** (setExpData on the main frame's bar; the routine's first instruction at
  `0x00c51256` jumps into IGC.dll and is entered after the standard prologue): the class stage `0x0139cb8a` (1 without
  evolution bits, else 2 + the highest bit's index); stage ≥ 3 shows the master experience and is "full" (0 / 0)
  when the master level reaches `0x016963bf` (400, 500 or **1350** by server type); the object `{ClassLevel, curExp,
  maxExp, page, rate}` with page = ⌊exp / (next/10)⌋ and rate = the remainder in percent of a tenth (doubles, the
  numbers as `%I64d`). The window's cache `+0x88` is compared but never written back; the bar is refreshed only
  by the five experience handlers (0x16, 0x9C, join, respawn, master), so after a level up it keeps the kill's
  numbers until the next experience packet.

## 4. Stat points (verified)

- **"+" buttons** (CharacterInfoFrame `onClickButton(row)`, `0x00b469c4`): nothing without free points (the word is
  zero-extended, so any non-zero value counts); the movie passes the **CharacterInfoSetup row id** as a number:
  8, 13, 24, 29, 42 request strength, agility, vitality, energy, command (a displaced `mov eax, [0x01d1df1c]` sits at
  `0x00b46a27`, an IGC.dll jump).
- **The request `0x00b48aca(stat)`**: at most one per 100 ms of GetTickCount (unsigned difference with
  `[0x01d22d4c]`), C1 [size] **01** | **00 STAT** (the last two bytes go through the builder's XOR), the click sound
  `0x19`.
- **The answer, 0xA0 sub 0x11 (`0x01223f04`)**: `+4` high nibble accepted, low nibble the stat; accepted: points − 1,
  vitality sets HP max from `+6`, energy MP max from `+6`, then AG max `+0xa` and SD max `+8`, the orbs; always the
  point text (`0x00b458f2`). The stat itself is **not** raised here:
- **The stat values, opcode 0x55 sub 0x57 (`0x0122a5f6` → `0x00b3ee5e`)**: base and added value of each stat
  (`+4..+0x16`) and a float (`+0x18`, row `0x39`); a changed stat (against the attribute or the window's own copy at
  `+0x119`) gets its row values (rows 8, 13, 24, 29, 42 through `0x00b3e773`/`0x00b3e935`/`0x00b3e2ed`), is written
  into the attribute and its total into the window (`+0xa8`); then the recalculation flag and
  `UpdateScorllList(3)`.

## 5. Verification

`tools/python/bin/python scripts/validate_progress.py --cases 500 --mutations` (the main checkout's Python with
Unicorn; about 50 s):

| Family | Client code | Cases | Result |
|---|---|---|---|
| calc | slot 0 of the 16 classes + `0x0098d2c4` | 500 | 0 mismatches |
| bar | `0x00c5125b` | 500 | 0 |
| table | `0x00a00e79` (levels −2..1500 + random) and `0x00a00f4a` | 3,003 | 0 |
| button | `0x00b469c4` + `0x00b48aca` | 500 | 0 |
| stats | `0x00b3ee5e` | 500 | 0 |
| speed | `0x00b40380` (machine from `0x00a0088d`), `0x0122a13d` | 500 | 0 |
| levelup | `0x01250b05` | 500 | 0 |
| point | `0x01223f04` | 500 | 0 |
| exp | `0x01234c08` (hero and monster records compared) | 500 | 0 |
| master | `0x01285b68` | 500 | 0 |
| master_exp | `0x01285efa` | 500 | 0 |
| options | winOption: `0x00c76115`, `0x00c76314`, `0x00c767d9`, `0x00c7635f`, `0x00c75bb2`, `0x00c75fa9`, setters `0x00c76022..0x00c760fa`, `0x00c765cc` | 600 | 0 |
| respawn | `0x0127bd9e` to `0x0127c048` (attribute record, money) | 600 | 0 |

8,003 cases, 0 mismatches; 12/12 planted mistakes (one or more per family) are caught. With the options and respawn
families (`--cases 600`): 13 families, 10,503 cases, 0 mismatches, 16/16 planted mistakes caught. The comparison covers the
attribute record (every byte), the stat machine, the window fields, the hero/monster records and every line
(effects, sounds, chat, window calls, GFx invokes). Portable tests: `reconstructed/progress/test_progress.py`
(independent statements of the rules) and `native/tests/test_native_progress.py` (mu-walk on the synthetic world).

The Magic_Ground2 subtype 0 effect of the level up was added to `reconstructed/combat/skill_fx.c` (its move has no
case for subtype 0; subtype 1 keeps the heal joints) and to `scripts/validate_skill_fx.py`'s kinds: all families
equal.

## 6. Native (`native/core/mu_progress`, mu-world/mu-client `--progress`)

The session keeps the attribute record and runs the reconstructed handlers on the DEMO server's packets (rules in
`mu_progress.h`): kill experience (L + 25)·L/3 with a demo monster level, level up at the client's next, five free
points (seven for class indices 3, 4, 6), demo HP/MP/SD/AG maxima, demo speeds from agility, a point accepted while
points remain. Lines go to the effect pools (`mu_combat_hero_joint`/`_effect`), the audio host (sound `0x98`, `0x19`)
and the chat; the GFx layer gets the client's setExpData object, the HUD maxima and the character window's rows
(class, level, points, the stats, attack power, attack rate, PvP rates, defense, defense rate, speed, magic, curse,
HP/MP/SD/AG). The window's "+" buttons go through `mu_prg_stat_button`/`mu_prg_stat_request`.

```sh
native/build/mu-world --game-root "$MU_GAME_ROOT" --gfx MOVIES --gfx-open character --progress --progress-class 0 \
    --progress-script "10:kill:5 20:kill:12 50:add:0 55:add:3" --combat
native/build/mu-walk --game-root ROOT --headless --progress --progress-script "2:kill:20 6:add:0"   # summary JSON
```

## 7. Live comparison (MTM-1, 2026-10-22, our session under the game lock)

Read with `live-readers/memread` (CharacterAttribute through `[0x01d1df1c]`, the hero object, the stat machine) and
window-only captures (local: `~/Documents/mu-mac-tools/native/renders/progress/live/`, dumps in
`scratch/progress/live/`). No point was spent and no option changed (the options window was opened and closed).

| | Nighty (class byte `0xf1`, level 400, master level 1200) | FryeZEN2 (Dark Knight `0x01`, level 1) |
|---|---|---|
| stats (+ added) | 18025 (+2639), 20419 (+641), 20000 (+4589), 4050 (+469) | 28, 20, 25, 10 |
| attack rate `+0x1b8` | 44756 = 1600·5 + 21060·3/2 + 20664/4 (**formula exact**) | 42 = 5 + 30 + 7 (**exact**) |
| PvP attack rate `+0x194` | 34034 = (1600·3 + 21060·4.5) & 0xffff = 99570 − 65536 (**exact, the 16-bit wrap**) | 93 (**exact**) |
| PvP defense rate `+0x196` | 13730 = 1600·2 + 21060·0.5 (**exact**) | 12 (**exact**) |
| defense `+0x1dc` / defense rate `+0x1da` | 7726 / 8494 (formula 7020 / 7020 + items) | 6 (**exact**) / 9 (formula 6 + the shield) |
| damage `+0x1ba..` | 11100 ~ 12970 (weapons) | 5 ~ 14 / 4 ~ 8 (the axe; formula 4 ~ 7) |
| speeds `+0x1b6`/`+0x1c2` | 361 / 309 (server) | 21 / 21 (server) |
| experience bar | "6369585199 / 980224359459" = the master experience/next of the record (stage 5); the reconstruction gives the same text with page 0, rate 6 | "100 / 100" (exp 100, next 100 = table(2) − table(1)) |
| window rows | ATK Rate 48587, PvP 38575, DEF 20135, DEF Rate 9061, PvP DEF 17135 (the window's builder adds options), ATK Speed "361 / 400" | ATK Rate 42, PvP 93, DEF 6, DEF Rate 9, PvP DEF 12, ATK Speed "21 / 400" |

The native session for the same Dark Knight (`--progress-class 1 --progress-points 200`) shows Dark Knight, level 1,
200 points, strength 28 … energy 10, ATK Rate 42, PvP ATK Rate 93, DEF 6, ATK Speed "21 / 400", PvP DEF Rate 12
(equal), ATK Power 4 ~ 7 and DEF Rate 6 (no axe or shield in the native session), HP 1100, MP 200, SD 52, AG 25 (the
demo maxima were set to the live values for this character). Side by side: `renders/progress/compare/side-by-side-dk1.png`
(local). The master experience next of Nighty is not the client's table: `0x00a00e79(1601) − 0x00a00e79(1600)` is 0
(the 32-bit product overflows to a negative value), so it comes from the server.

## 8. The options window and the system menu

**Options window (winOption), verified** (`reconstructed/progress/progress_options.c`, family `options`). The game
side of the window:

- the join's loaders `0x00c76115` (`./option.ini` `[DEFAULT]`: IsAutoAttack 1, IsWhisperSound 0, IsSlideHelp 1,
  IsPlayerInfo 1, IsMonsterInfo 1, IsMusicPlay 1, Volum 5, IsMute 0, IsUpdateData 0, IsSwitchMode 0, SwitchModeTime
  10, read with GetPrivateProfileIntA) and `0x00c76314` (`[OPTION] Effect`, default 4, clamped to 0..4);
- `InitText` `0x00c765cc` (GlobalText ids per label) and `setDatas` `0x00c767d9`: the volume is read back from the
  sound module's Effect group, `(int)(volume · 9 + 0.5)` (0 means muted), BGM from the Music group's mute; the
  object goes to the movie only while the window is shown;
- `onChange` → apply `0x00c7635f`: `[OPTION] Effect` is written (the only key the client writes); useHelpText on
  the main frame (slide help); hudPlayerName's monster info `0x00c83c86`; the Effect group's volume = volume / 9 (0
  when muted); the Music group's mute = !BGM; the auto switch (`0x00c435b4`/`0x00c435f1`);
- the setters `0x00c76022..0x00c760fa` (what the server's saved options, opcode `0xA0 sub 0x03` `0x0126f225`, call
  at the join; option byte +0x18 bit 0 auto attack, 1 whisper, 2 slide help, 3 player info, 4 monster info, 5
  switch mode; +0x19 the switch time) mark the update; the per-frame `0x00c75fa9` shows it (setDatas) at the next
  visible frame;
- the toggle `0x00c75fe2` (O): shown → hide, else show (`0x00be7079`).

The client keeps the toggles on the server and only `[OPTION] Effect` in `option.ini`; the save request
`0x0182ff32` is static.

**System menu (winSystemMenu)**: the NATIVE-CHARCREATE-001 code (`mu_csm_*`) with the world's scene (6: the
movie's SceneChange hides the Option button in the world, as live). Live (MTM-1): Exit Game / Select Server /
Switch Character / Close; Esc opens it, and when the options window is open Esc closes that first; O opens the
options window, as does the bottom-right popup (M Move, O Option, P Private Stores, ESC System).

**Native** (`native/world/world_gfx_options.{c,h}`, mu-world and mu-client with `--gfx`):

| Client | Native |
|---|---|
| `./option.ini` `[DEFAULT]` (read at the join), `[OPTION] Effect` (written by apply) | `~/Library/Application Support/MuTheMatrixNative/option.ini` (`MU_NATIVE_SETTINGS_DIR` overrides the folder), same sections and keys |
| the toggles saved on the server (`0xA0 sub 0x03`) | offline: written to `[DEFAULT]` on every onChange, read back at the next join through the client's own loader |
| sound module Effect group (`0x010ab1be`/`0x010ab2e3`), Music group mute | `mu_audio_set/get_group_volume`, `mu_audio_set/get_group_mute` of the native audio module (`reconstructed/audio`); the stored volume is applied at the first frame with audio |
| hudPlayerName monster info `0x00c83c86` | `mu_names_set_monster_view` |
| useHelpText on the main frame | the same invoke on `MU_GFX_MAIN` |
| Exit Game: the 5-second message `0x00b39b2f` (GlobalText 0x17c) and `0x009a5ab2(0)` | the chat line "You will exit game in 5 seconds.", then mu-world/mu-client quit |
| Switch Character `0x009a5ab2(1)` (the server's answer `0x0125294e` subcode 1) | mu-client: close the world, the character list (offline answer at once) |
| Select Server `0x009a5ab2(2)` | mu-client: back to the login scene |

The movies' onLoad runs inside the layer's open, before the host exists, so world_gfx replays it once the host is
attached. Without the GFx layer, Esc in mu-client keeps its old shortcut (back to character select). The
screenshot key of mu-client moved from O to Print Screen/F13 when the GFx layer is on (O opens the options window).

Headless checks: mu-world `--progress-script` verbs `key:VK`, `click:X*10000+Y`, `menu:N` (0 exit, 1 switch, 2
server, 3 close), `volume:N`, `monster:N`; `native/tests/options_host.c` (stub layer and audio over the real game
side) in `test_native_progress.py` (defaults, onChange → audio groups and file, the next session's read-back, the
Effect clamp, the menu's three requests and the countdown, Esc closing the options window first). Renders (local):
`renders/progress/options/` (the window at frame 20, the menu at frame 60); mu-client headless: Esc → menu → click
Switch Character → character select ("6 -> 5: menu: switch character").

**Live vs native** (`renders/progress/compare/side-by-side-option.png`, local): the same title, labels, check boxes
(Automatic Attack, Slide Help, Name display, Monster display, BGM checked; Whispering and Switch on not), "10 min",
the effect row with 13 selected and "5" under it. The volume differs: live shows 9 (the owner's Effect group
volume), the headless native run has no audio module and shows the `[DEFAULT] Volum` default 5; with the audio
module attached the read-back gives 9 for full volume, as live.

## 9. Death and respawn

**Respawn answer, `0xA0 sub 0x30` (`0x0127bd9e`)** — the attribute part is verified (family `respawn`, the run
stops at `0x0127c048`): +0xa HP, +0xc MP, +0xe SD, +0x10 AG (u16, `movzx`, so the client's `< 0` clamps do nothing)
into +0x68/+0x6c/+0x78/+0x80; the master experience is cleared (`0x00a00117(0)`), then the big-endian total at
+0x12..+0x19 becomes the master experience of a third-class hero (`0x0139d8ea`: class byte bit 5) or the experience
within the level for the others (total − `0x00a00e79(level)`, `0x00a00074`); +0x1c the money (CharacterMachine
+0x2d70). **Static**: the hero is re-created at +4 x, +5 y with the angle (+8 − 1) · 45 (`0x0137d8a1`, `0xa91`); when
+6 (the map, u16) differs from World `0x01cf15fc` the client changes the world (`0x0182876e`, the map's music and
windows).

The client has no respawn countdown text (no GlobalText entry; the dead counter and SetPlayerDie are the
NATIVE-COMBAT-001 code); the delay is the server's. No live death was provoked (no deaths or item loss on the
owner's characters).

**Native**: the combat demo's hero death (`--hero-hp N`) waits `hero_respawn_steps` (100 steps, 4 s, DEMO), then
calls the host (`mu_combat.hero_respawned`): `mu_map_respawn` picks the DEMO town (gate 17 Lorencia; 22 Devias for
world 2, 27 Noria for 3, 267 Elbeland for 51: the town gates of the classic servers' rule) and a tile of its
rectangle, the teleport is taken at the next step like a warp (world change included), and `mu_progress_respawn`
builds the answer (maxima, the total experience unchanged: DEMO, no death penalty; the money of the map session)
and runs `mu_prg_recv_respawn`. Render (local): `renders/progress/respawn/` (a Dark Knight killed by a Bull Fighter
at 182,127, back at 134,135 in Lorencia). Tests: `test_native_progress.Respawn` (a death in world 1 lands in world
0's town, same-world respawn).

## 10. Gaps

- The equipment, set, socket, buff, formula-table and master-tree contributions of CalculateAll, the hand damage of
  slot 0x18 and the character window's own value builder `0x00b40661` (the native rows map the attribute values by
  row id, a static reading of the labels; the server-sent rows such as critical/excellent rates stay "-").
- The third-class level-up joints (`0x7f78` subtypes `0x2d`/`0x2e`) are not in the joint module: they are counted
  as unsupported and not drawn.
- The real server's rules (experience per monster, points per level, maxima, speeds) are demo values.
- The join packet (`0xA0 sub 0x07` → `0x0124cc64`) and the second experience packet (`0x9C`, `0x0123504e`) are mapped
  but not reconstructed.
- The options save request `0x0182ff32` (the toggles to the server) is static and not sent offline; the switch
  mode (`0x00c435b4`/`0x00c435f1`) is kept but has no native effect; the Effect limitation value has no native
  consumer yet (the effect pools do not read it).
- The respawn handler after `0x0127c048` (hero re-creation, world change, windows) is static; the real server's
  death penalty and respawn rules are not known (DEMO town gates, no penalty).
