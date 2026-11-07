# README-REFRESH-005-B: README interface and menu images re-shot

Docs and media lane, 2026-11-06. Worktree `worktrees/readme-images-b`, branch `claude/readme-images-b`, from
origin/main `18ab0134` (#316 RENDER-ITEMS-002Q merged in steward batch 55 before any render). Claude Opus 5.5.
Offline only: no original client, launcher, live read, account, network or protection work. The installed Native
Preview, the Wine play app and the staged Wine app were not touched. The companion lane README-IMAGES-A
(`docs/handoffs/README-REFRESH-005.md`) owns the world/combat/effects/comparison/crowd/viewer images and the
README progress text; this lane changed only image files 02-25 of its share, their audit pins and the alt text and
captions of its README sections.

## How the images were made

- Binaries: `mu-world` and `mu-client` built in this worktree from `18ab0134` (`nice -n 10 make -j4 world client`,
  10.7 s). GFx: the real Ruffle library the app refreshes bundle (`scratch/polish/libmugfx.dylib`).
- Data: the installed APP-REFRESH-006 Native Data, read-only: converted movies, objects and `MU_LANG_DIR` (with
  Lang's `itemtrs.tsv`, so inventory icons use ItemTRSData as in the app).
- Environment: `MU_GFX_PUBLIC_DEMO=1` (hero Preview, authored HUD maxima), `MU_GFX_SINGLE_BUFFER=1`,
  `MU_GFX_TEST_CLOCK=1`, `--hero-name Preview`, headless GL, 1280×800 (02/03: 1504×936), the Lorencia demo
  placement, NPC table and demo players. Window-only renders; no desktop screenshots.
- Scripts (the documented verbs of each window's research note): `--npc-script` (dialogue, shop, `tipinv`,
  `bufftip`, mix, personal store, quest verbs), `--skill-script` (`open`, `tree`, `treeclick`, `treeover`),
  `--travel-script` (`tab`, `mwin`), `--social-script` (trade, `partner-item`, `trade-tip`, mailbox, messenger),
  `--progress-script` (Options, Esc menu), mu-client `--script` for character creation.
- Composition: the 2026-10-22 layouts (`renders/readme-sources/scripts/build.py`) re-used with the same crops,
  sizes and labels; JPEG quality 85, PNGs 8-bit palette (pngquant), each ≤ 690 KB.

Inputs that are fixture state, not new client behaviour:

- 13/21: `MU_QUEST_SCENARIO=native/fixture/scenarios/quest-progress.scn` (as `test_native_quest` uses) puts quest 7
  at 3/3. For 21's banner a local copy of that scenario adds one synthetic guide reward reply `c1 07 f6 51 00 00 01`
  (result 1: QuestProgressInfo). Kept outside the repository.
- 08: `damage:0:53` (an existing offline fixture verb) sets the Blade +9 to 53/53. See finding 1.
- 20: `--class 0x81` gives the demo hero a master-stage class; without it the session hero (class 0x01) has no tree.
- 24: a partner item as 15 wire bytes `004f3143000000ffffffffff000000` (Kris +9, durability 49, luck/option,
  two excellent options, empty sockets).

## Image by image

| Image | Old (2026-10-21/22) | New | Decision |
|---|---|---|---|
| 02 login/server select | native login, server list | same scene, same movie | **Kept**: mean pixel difference 9/255, only the water phase moves; nothing visibly better |
| 03 character select | GFx character list | same scene; only the hint line gained "Create / Delete (local store), Esc: the menu" | **Kept**: same pixels apart from that line |
| 04a character creation | panel over a black void with broken water planes | panel over the full character-select scene (waterfalls, trees, temple) | Replaced |
| 04b all classes | 16 busts on black | the same 16 crops with the scene behind each | Replaced |
| 07 character window, buffs | the owner's character name and vitals, town objects missing, buff popup with a raw `%d` | hero Preview, demo players, Lorencia buildings, a formatted Potion of Soul popup | Replaced |
| 08 inventory tooltip | bare ground without town objects, owner's name, real zen | town objects and demo players, ItemTRSData icon sizes, Preview, demo zen | Replaced |
| 09 dialogue and shop | owner's name and real HP/MP/exp in the HUD | Preview, public-demo HUD, demo players, buildings | Replaced |
| 13 My Quests | real HP/exp numbers, quest at 0/3 | public HUD, quest 3/3 with Move to NPC and the tracker | Replaced |
| 14 Skill Imprint | owner's name and real HUD | Preview, demo players, public HUD | Replaced |
| 19 maps | owner's name, real HUD, empty town | Preview, demo players, scenery under the overlay | Replaced |
| 20 Master tree | the owner's master level/exp in the header and HUD | the same tree and tooltip with demo values, the town behind | Replaced (tree pixels themselves unchanged) |
| 21 quests guide/tracker | owner's name, NPC 257 drawn white | Preview; NPC 257 textured (+13 armour, wings); banner and two tracker rows | Replaced |
| 23 mix and personal store | white item silhouettes in the inventory, owner's name, real HUD | textured inventory items, Preview, public HUD | Replaced |
| 24 party/trade/mail/whisper | owner's real HUD numbers | textured scenery and demo players, Preview in the messenger | Replaced |
| 25 progression/options/menu | the owner's character name in the window title | Preview; Options and menu from today's build | Replaced; the "Original client" half is the same reviewed live crop as before |

## Privacy review

Every encoded file was opened and read after encoding. Names visible: Preview (the hero), the demo fixture players
(Aeris, Kyra, Redhand, Mordred, Shopkeep, "Hero" in the social party list), NPC names from the client's tables and
the offline-demo server labels. No account name, real player name, server address, chat from other players,
local path or personal data. 25's "Original client" half (the only non-native pixels) is unchanged from the
published image and has no names. Earlier images 07-25 showed the owner's character name and real vitals; those are
gone.

## Findings for other lanes

1. Demo inventory items start at durability 1 (`mu_gfx_layer.c` add-item default, since ed9ed6be), so every
   inventory tooltip in the offline demo reads e.g. "Durability: [1/53]"; the old 08 read 53/53. Cosmetic demo
   state, not a renderer change; this lane did not change code.
2. The October quest script (`5:click:soldier … 240:qkill:2`) no longer reaches an accepted quest without
   `MU_QUEST_SCENARIO`; quests now arrive through the session (SESSION-QUEST-001). The research note's command
   still omits that variable.

## Checks

Docs/media PR (TEST BUDGET rule 6c), with `MU_RECOVERY_INTEGRATION=1`:

- `scripts/audit_repository.py`: 1,981 staged files, 0 rejected, 13 s;
- `tests/`: `test_world_captures_2`, `test_repository_policy`: 13 tests OK, 0.5 s;
- `native/tests/`: `test_native_item_textures`, `test_native_data_manifest`: 23 tests OK, 54 s;
- README targets: 65 local link/image targets, all 27 images present, 0 missing.

No runtime source changed. Steward validators: none.

## Cleanup

Renders, scratch and the worktree build were deleted after the ready line; the worktree stays until the steward
merges. No local input needs keeping; the commands above and the 2026-10-22 layout script reproduce the images.
