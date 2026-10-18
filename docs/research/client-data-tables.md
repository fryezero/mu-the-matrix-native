# Client data tables (NATIVE-DATA-001)

This milestone recovers how the client decodes its game data tables: the item list, item options and sets, skill and master-skill tooltips, quest text, the Muun tables, Mix and others. It also traces how an item index becomes a model file. Decoders are reconstructed in C (`reconstructed/data`). A native module and the CLI `native/build/mu-data` dump the tables locally. Decoded game text and tables are never committed. Tests use synthetic encoded files.

Labels used below:

- **Verified**: actual client instructions ran in Unicorn on the pinned restored text and matched the authored code.
- **Static**: a reading of the instructions that was not executed.
- **Matched**: an installed file agrees with a layout or key through the client's own checksum routine, but the loader was not located.

## Identity

| Input | Value |
|---|---|
| main.exe | SHA-256 `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a` |
| Restored text (capture 09) | VA `0x00401000`, 23,572,480 bytes, `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` |
| Second image section (capture 10) | VA `0x01a7c000`, 2,557,764 bytes, `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f` |
| CPU feature word (math capture) | `0x01cf6618`, `bce941d196c26696f1f5d701d21a8a9e414e81d6e15a48f3663313e3cd7cc4b9` |
| Installed tables | read only from `MU_GAME_ROOT` (MuMatrixKit bottle). Per-file digests are in the private report. |

## Codecs (verified)

| Routine | Body (exclusive end), SHA-256 | Behavior |
|---|---|---|
| `0x00976855` | `0x00976895`, `8d9eb0f5…ce0d` | `buf[i] ^= key[i % 3]` for `0 <= i < size` (signed `idiv`, signed bound). Key read from global `0x01cf0448`. cdecl `(buf, size)`. |
| `0x01072ebc` | `0x01072f0d`, `5708edde…04ea` | Same loop. Key `FC CF AB` stored as stack immediates. thiscall, `ret 8`, ECX unused. ServerList only. |
| `0x00976895` | `0x0097694a`, `28a45988…d624` | 32-bit checksum `(buf, size, key16)`, described below. |
| `0x00f1600f` | `0x00f16067`, `a4e4e90f…916e` | `buf[i] ^= key3[i % 3]; buf[i] ^= (uint8)key` (unsigned). key3 global `0x01cf0ea8`. |

Checksum: `r = k << 9`. For each word offset `i = 0, 4, …` while `i <= size-4` (unsigned):

1. Read a little-endian word `t`.
2. If `((i>>2)+k)` is even, `r ^= t`; otherwise `r += t`.
3. When `i % 16 == 0`, `r ^= (k + r) >> ((i>>2) % 8 + 1)`.

Trailing bytes beyond the last whole word are ignored. With `size < 4` the unsigned bound wraps (an unbounded read). That case is outside the authored contract; the C returns `k << 9` without reading.

The `.data` section that holds both key globals was not captured. The model supplies `FC CF AB` there. These are the immediates of `0x01072ebc`, and every installed table decodes with them. Each codec call restarts the key phase at the buffer start, so **the unit lengths a loader passes are part of the format**. For 24 of 40 loaders where it applies, decoding the whole payload in one call gives different bytes (negative control).

Comparisons cover:

- 11,120 synthetic codec cases. Sizes run 0–69, 255–257, 708, 1000 and 4099, plus negative sizes; all four alignments.
- Four key-table contents for `0x00976855` and two for `0x00f1600f`, to show the routines read the global.
- Eight checksum keys, including high bits that must be ignored.
- 170 whole installed-image cases.

All match the authored C byte for byte. Return value, guard bytes, callee-saved registers and stack cleanup (cdecl, or `ret 8`) are also checked.

## Loaders and layouts (verified)

Each loader's own body runs on the installed file. `fopen/fread/fclose/fseek/ftell/feof` and `operator new/malloc/free` are modelled over the file bytes. `memcpy/memset`, `std::string::c_str` and the codecs execute as client code. Other direct callees are skipped and return a dummy pointer: record constructors, container inserts and logging. Every codec call (length, bytes before and after) and checksum call (length, key, result) is compared in order with the unit schedule from `mu_data_decode`. Error decisions are checked with mutations: a flipped stored checksum, and a zero count where the loader tests it. Every mutation took the client's error path, either an import call (`MessageBoxA`) or a return with nothing decoded. Each time the authored status agreed.

| File | Loader | Layout (units in brackets) | R | Checksum key |
|---|---|---|---|---|
| Item.bmd | `0x00cd4f2a` | u32 n, n·[R], u32 chk | 708 | `0xe2f1` |
| ItemAddOption.bmd | `0x00cd4bff` | one [0x2c000] | — | — |
| ExcellentCommonOption / ExcellentWingOption.bmd | `0x00cd51fe` | counted | 120 | `0xe2f1` |
| FormulaData.bmd | `0x0117b199` | u32 records, u32 groups, chk over `records·260+groups·8`; per group [4][4] then count·[260] | 260 | `0xe2f1` |
| PentagramMixNeedSource.bmd | `0x00fc6a61` | counted | 188 | `0xe2f1` |
| MuunOption / MuunAddOption / MuunInfo / MuunTooltipInfo | `0x009b3a26` / `0x009b3cb1` / `0x009b3f7e` / `0x009b41e7` | counted | 836 / 40 / 60 / 32 | `0xe2f1` |
| MuunExchange.bmd | `0x009b0fd5` | u32 a, u32 b, (a+b)·[16], chk | 16 | `0xe2f1` |
| MuunRenderInfo / MuunMeshInfo | `0x009b90d5` / `0x009b9510` | counted | 612 / 300 | `0xe2f1` |
| StatOption / StatOptionText | `0x00995776` / `0x00995a29` | counted | 52 / 260 | `0xe2f1` |
| Quest.bmd | `0x009f4866` | 200·[1000], no checksum | 1000 | — |
| SocketItem.bmd | `0x010a9926` | 3×50·[168] into fixed slots | 168 | — |
| PlayGuide.bmd | `0x009d7096` | counted | 260 | `0xe2f1` |
| EvolutionMonsterBox.bmd | `0x00a9d8d2` | u32 n, one [n], chk | — | `0xc4a2` |
| MuRummyOption / Card / Slot | `0x00bcc159` / `0x00bcc2a5` / `0x00bcc44d` | counted (no zero-count test) | 8 / 60 / 11 | `0xe2f1` |
| MonsterSkill.bmd | `0x01692f3c` | signed u32 n, n·[48], no checksum | 48 | — |
| MasterSkillTreeData / MasterSkillTooltip | `0x00baf58c` / `0x00baf73e` | 2048·[R], chk | 24 / 808 | `0x2bc1` |
| NPCDialogue / QuestProgress | `0x00fdcbb4` / `0x00fdccc1` | [R] until a short read | 88 / 41 | — |
| QuestWords.bmd | `0x00fdcdc8` | repeated [6: u32 id, u16 len][len] | — | — |
| SkillTooltipText.bmd | `0x0117d758` | counted | 808 | `0xe2f1` |
| ItemSetType / ItemSetOption | `0x009ddde0` / `0x009ddf86` | N·[R], chk | 10×11264 / 468×1000 | `0xe5f1` / `0xa2f1` |
| ItemSetOptionText | `0x009df9ca` | counted | 102 | `0xe2f1` |
| InfoTooltip / InfoTooltipText | `0x00ab3411` / `0x00ab35fc` | counted | 42 / 258 | `0xa4c6` |
| helpdata.bmd | `0x00b8968b` | 512·[136], chk | 136 | `0xc4f7` |
| RuudShopViewInfo.bmd | `0x00c0f48a` | counted | 240 | `0xe2f1` |
| MapCharacters.bmd | `0x00cdd16b` | repeated [4 key][4 n] n·[4] (every field its own unit) | 4 | — |
| Mix.bmd | `0x00d0aea2` | [88] = 22 signed counts; group rejected if `feof` or count > 3000 ("Version not matched"); counts[g]·[928] | 928 | — |
| petdata.bmd | `0x00eb0a7d` | 32·[48], chk | 48 | `0x3bb2` |
| pet.bmd | `0x012a9c1b` | u32, u32 n, u32 count, count·[8n+16], chk | — | `0x7f1d` |
| itemtooltip.bmd | `0x00f0ada4` | 11264·[136], chk; decoding stops after the first record whose byte 4 is zero | 136 | `0xe2f1` |
| itemtooltiptext.bmd | `0x00f0afe2` | counted, each record through `0x00f1600f` with key `0xe2f1` | 260 | `0xe2f1` |
| JewelOfHarmonyOption.bmd | `0x011dfd13` | one [135000] | — | — |
| ServerList.bmd | `0x01072501` | repeated [39 header][signed u16 at 37] with the local-key codec | — | — |
| Lang.mpr | `0x00ffaeb8` | chk over size−4 (key `0x12dc`), then one `0x00f1600f` unit with key `0x12dc` | — | `0x12dc` |

"Counted" means u32 count (not decoded), then count·[R], then u32 checksum over the records. A zero count is rejected where the loader tests it.

Totals:

- 45 installed files, 43,968 decode units and 12,346,759 decoded bytes, all matching.
- 51 mutations.
- 96 of 96 loader cases match.

Two loop conditions read results of skipped container inserts: the itemtooltip/itemtooltiptext insert flags at `0x00f0af5f` and `0x00f0b1f6`. The harness forces those results to "inserted" and counts each forcing (4,950 and 1,386). The MuRummyCard loader runs a post-processing loop over its skipped container after decoding. That loop is cut after 5,000 skipped calls with no codec call; all 35 records had already been decoded.

Loaders that read records without checking `fread` are noted only through their short-read behavior. MonsterSkill, Quest, ItemAddOption, JewelOfHarmonyOption and SocketItem decode their fixed unit counts regardless of file length. For short files the authored code returns `truncated` instead of decoding stale bytes, an authored choice.

## Startup order and callers (static, unresolved)

The `.rdata` strings at `0x01ad7b24..0x01ad7f18` list, in order:

Text.bmd, Macro.txt, Item, ExcellentCommonOption, ExcellentWingOption, FormulaData, PentagramMixNeedSource, MuunOption, MuunAddOption, MuunInfo, MuunTooltipInfo, MuunExchange, StatOption, StatOptionText, Quest, SocketItem, PlayGuide, EvolutionMonsterBox, MuRummyOption/Card/Slot, MonsterSkill, MasterSkillTreeData, MasterSkillTooltip, NPCDialogue, QuestProgress, QuestWords, SkillTooltipText.

The strings are interleaved with sound and NPC name tables. That pattern is consistent with one initialization routine, but the order is a reading of string placement, not an observed call sequence. Neither these strings nor most loader entries have any direct, thunk, absolute-text or `.rdata` reference in the restored text. The Lang.mpr table loader `0x010d68e1` begins with `jmp 0x0e02edde` into a non-restored section. The callers are therefore taken to be in code this capture does not restore. Per scope they were not analysed. Loaders are entered directly with a path argument. Text.bmd is not installed; its role has moved to Lang.mpr (`Text(kor).txt`).

## Lang.mpr (envelope verified; contents blocked)

The decoded payload is a zip archive with 141 entries: `\Text(kor).txt`, `\Skill(kor).txt`, `\Gate.txt`, `\movereq(kor).txt`, `\npcName(kor).txt`, `\Dialog(kor).txt`, the `EffectInfo\*` and `MapObjectAnimationInfo\*` scripts and others. It is opened from memory through the bundled minizip, and `mu-data mpr` lists its directory. Every entry has general-purpose flag bit 0 set, which means traditional PKWARE encryption. The only password call site seen, `0x00ffabf1`, pushes the absolute value `0x10c7c8ef`. That address lies outside every PE section of the image, and its bytes are in no capture. The localized text, skill, gate/move and NPC-name tables therefore stay undecoded. Recovering the password would mean inspecting the protected region and was not attempted.

## Files not handled by located loaders

- **Checksum key matched, loader not located** (`MU_DATA` catalog excludes them):
  - skill.bmd: whole minus 4, key `0x5a18`;
  - minimap.bmd: key `0xce54`;
  - counted files with key `0xe2f1`: bonusexp (R 12), arcabattlebootymix (20), attributevariation (3140), elementalmixlist (12), itemtrsdata (32);
  - arcabattlescript: counted, R 264, key `0xa4c6`;
  - itemleveltooltip: whole minus 4, key `0xe2f1`.
  
  Keys came from the checksum agreement with `0x00976895` over all 65,536 keys. Their decode units are not observed. NATIVE-DATA-002 found no checksum call, key immediate or path string for them in the restored text ([details](client-item-attributes.md#skillbmd-minimapbmd-movereqbmd-loaders-static)). movereq.bmd and parts of minimap.bmd show `buf ^ key3 ^ 0x98` patterns, which fits the `0x00f1600f` codec with a key whose low byte is `0x98` (inference from file bytes only).
- **Not referenced by any restored path string**: credit.bmd, mixold.bmd (the Mix loader leaves 864 bytes unread), jewelofharmonysmelt.bmd (named only in an error message) and G_Camera_Angle_Position.bmd.
- **Another format**: CustomText, CustomRank, DailyReward, ItemBank, ItemOptionSystem_Exc, ItemPriceSystem, ServerInfo, ServerListDisplay and Lang.template share an identical 64-byte prefix. Their names do not occur in main.exe's restored strings. Presumably IGC.dll loads them; that module is opaque by scope.
- **Other agents' areas, located but not catalogued**: terrain `.att`/`.map`/`.obj` loaders, `*.mapack` (`0x00975391`, key `0xb6fd`) and `*.mab` (`0x0097db09`, key `0xe7ca`).
- **Not data tables**: `0x009cc48a`, `0x011e9342`, `0x00c1d3a6` and similar apply `0x00976855` to 10/20-byte account and packet fields.

## Item index to model (verified)

Model getter `0x00eaa8cf` (thiscall on the model cache):

1. It accepts model indexes `0..0x3af6`.
2. It looks up the item code `index − 0xae6` in the item-script manager (singleton `0x01ec7a60`, `std::map` keyed by the record's u32 at +0, lookup `0x00cd5d29`).
3. It calls model loader `0x00cd558e(index, record+0x008, record+0x10c)`, which is folder and file.
4. A valid index with no item record yields an empty model object; out of range yields NULL.

The loader copies each decoded 708-byte record over a constructed object, so object and file layouts coincide. The insert keeps the first record for a repeated code.

The validator runs the manager constructor, the Item.bmd loader with real container inserts, the lookup, the cache constructor and the getter. The singleton accessor returns the constructed manager, and `0x00cd558e` is replaced by an argument recorder. Results:

- All 4,881 installed codes are found, and two absent codes are not.
- The getter's 15,099 indexes produce exactly 4,881 loader calls. Their (index, folder, file) equal `mu-data item-models`.
- 10,214 empty-model indexes and NULLs outside the range match.
- A duplicate-code mutation keeps the first record in both implementations.

Static, inside `0x00cd558e`:

- It loads the BMD through `0x012b3812(folder, file, 1)` and logs `ItemModelFile does not exist : [(section, index) "folder" "file"]`.
- Mesh textures load from `folder + "Texture\" + name`.
- Texture-name prefixes select fixed texture slots instead of a file:
  - `skin_` and `level` → `0x7725`;
  - `hid` → `0x791a`;
  - `hair_` → `0x7776`;
  - `HQskin_`, `HQskin` and `HQlevel` → `0x77c7`;
  - `HQskin3` → `0x7869`;
  - `HQskin2` → `0x7818`;
  - `HQhair_` and `HQhair` → `0x78ba`.
- `nude_`, `cotton_` and `cotton2_` set per-mesh values 1, 2 and 3.
- `field_` also loads the name without the prefix, with a `.tga` extension.
- Other textures load through `0x00c97689` with arguments `0x2600`/`0x2900`, the GL_NEAREST and GL_CLAMP values.

**Item record** (static, from constructor `0x01184277`):

- u32 code `+0x000`, u16 section `+0x004`, u16 index `+0x006`;
- char[260] folder `+0x008`, char[260] file `+0x10c`, char[64] name `+0x210`;
- 45 zero-initialised scalar fields from `+0x250` to `+0x2c0`, with widths 1/2/4. NATIVE-DATA-002 names them, and the arrays and flags the constructor misses, from their consumers; see [client-item-attributes.md](client-item-attributes.md).

## Native module and CLI

`native/core/mu_data.{h,c}` (no Crypto++/image dependencies) and `native/build/mu-data`:

```sh
make -C native build/mu-data
native/build/mu-data list "$MU_GAME_ROOT"                 # catalog + decode status of every installed table
native/build/mu-data dump "$MU_GAME_ROOT/Data/Local/item.bmd" --out /tmp/item.json
native/build/mu-data item-models "$MU_GAME_ROOT/Data/Local/item.bmd" --json
native/build/mu-data model "$MU_GAME_ROOT/Data/Local/item.bmd" 2790
native/build/mu-data mpr "$MU_GAME_ROOT/Data/Lang.mpr"
native/build/mu-data decode FILE --out /tmp/decoded.bin
```

JSON strings carry client bytes ≥ 0x80 as `\u00XX`; the code page is not converted. Outputs belong in local temporary paths only.

## Reproduce

```sh
make -C reconstructed/data && make -C native build/mu-data
./tools/python/bin/python scripts/validate_data_tables.py --game-root "$MU_GAME_ROOT" --output /tmp/tables.json
./tools/python/bin/python scripts/validate_item_models.py --game-root "$MU_GAME_ROOT" --output /tmp/models.json
MU_RECOVERY_INTEGRATION=1 MU_GAME_ROOT=... python3 -m unittest tests.test_data_tables_private
```

Defaults read the private captures under `evidence/` (`--text/--data/--feature` override). Portable tests:

- `reconstructed/data/test_data_tables.py`: an independent Python model of the codecs, plus every schedule kind on synthetic files;
- `native/tests/test_native_data.py`: synthetic Item.bmd, words, map lists, a synthetic zip package, corrupt and unknown inputs.

Private reports stay under `evidence/client-data-tables/`.

## Limits and next steps

- Callers and startup order are not observed. Loader inputs are the installed files, entered directly.
- The `.data` key bytes are a model. The emulator runs in a Linux/Wine-derived capture, which says nothing about native Windows equivalence.
- Record fields: Item.bmd and 27 other layouts are named in NATIVE-DATA-002 ([client-item-attributes.md](client-item-attributes.md)), with per-field evidence classes.
- The Lang.mpr contents (localized text, skills, gates/moves, NPC names) need the package password, which sits behind the protection boundary.
- skill.bmd, minimap.bmd, movereq.bmd and the other matched-only files need their loaders. Those are presumably in non-restored code; a capture of the routine that loads them would close this.
