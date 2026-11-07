# Public README refresh, README-REFRESH-003

Documentation-only refresh on 2026-10-28. Source baseline: main `7d813a9`, the merge of PR #207.
Read the merged-PR list and all milestone handoffs for merged PRs #168 through #207. Gaps in those PR
numbers are not additional merged milestones. No new original-instruction, live-game or timing evidence
was acquired in this lane. The target executable and capture identities are unchanged.

## Claim sources

| Public claim | Merged source and evidence boundary |
|---|---|
| One world input router and shared input files | [INPUT-001](../handoffs/INPUT-001.md), PR #190; 570 instruction cases, 7/7 compiled mistakes. Platform routing and unavailable panels retain their separate limits |
| Session and loopback feeds | [Quests](../handoffs/SESSION-QUEST-001.md) #179, [players](../handoffs/SESSION-VIEWPORT-001.md) #183, [monsters/NPCs](../handoffs/VIEWPORT-MONSTER-001.md) #191, [combat](../handoffs/SESSION-COMBAT-001.md) #197, [skills](../handoffs/SESSION-SKILL-001.md) #204. Eight fixture scenarios, 67 inbound frames, zero unbound/undecodable in those scenarios; two unrecovered intents, six unsent frames. Opaque NPC quest lists and encrypted requests remain unavailable |
| World details | [A](../handoffs/RENDER-WORLDS-A.md) #187, [B](../handoffs/RENDER-WORLDS-B.md) #180, [C](../handoffs/RENDER-WORLDS-C.md) #181, [C2](../handoffs/RENDER-WORLDS-C2.md) #189, [D](../handoffs/RENDER-WORLDS-D.md) #188, [E](../handoffs/RENDER-WORLDS-E.md) #195, [F](../handoffs/RENDER-WORLDS-F.md) #193, [G](../handoffs/RENDER-WORLDS-G.md) #198, [H](../handoffs/RENDER-WORLDS-H.md) #206. H's inventory has 25/144 primary families across 9/48 classes, not 25 complete maps. Fresh synchronized live comparisons remain open |
| Terrain and world order | [Terrain](../handoffs/RENDER-TERRAIN-002.md) #175 and [order](../handoffs/WORLD-ORDER-001.md) #194; bounded instruction comparisons and explicit host inputs/order adapters, not complete world fidelity |
| Special item bodies/skins | [Part 6](../handoffs/RENDER-ITEMS-002F.md) #202, with preceding #173/#178/#184/#192/#199. 559/1,674 special bodies, 17/17 skins; 1,115 bodies remain, plus pose/owner/model limits |
| Sound | [Part 1](../handoffs/AUDIO-002.md) #185, [part 2](../handoffs/AUDIO-002B.md) #196, [part 3](../handoffs/AUDIO-002C.md) #207. Event music and session cue adapters; not all callers or original-client audio parity |
| Character-select runtime | [CHARSEL-RT-001](../handoffs/CHARSEL-RT-001.md) #170; extraction preserved render comparisons. Account/session migration remains separate |
| Python-free first run and Native Data | [DATA-ACQ-003](../handoffs/DATA-ACQ-003.md) #169 and [DATA-ACQ-004](../handoffs/DATA-ACQ-004.md) #174; temporary-home setup, exact converter outputs, build/input/output manifests and refusal. Guided acquisition and real second-user proof remain open |
| Private integration | [INTEGRATION-GREEN-001](../handoffs/INTEGRATION-GREEN-001.md) #200; 38/38 private-enabled directories green, 1,464 unique tests passed, 15 optional Ruffle/movie skips. This is the recorded #200 run, not a fresh private run by this documentation lane |
| 80-player performance | [NATIVE-PERF-003](../handoffs/NATIVE-PERF-003.md) #201; full-interface crowd80 18.37 fps and tormenta80 18.94 fps, rounded to 18.4/18.9. The 25 fps target and pacing tails remain open |
| README crowds | [README-STRESS-001](../handoffs/README-STRESS-001.md) #205; images 26/27 have 80 synthetic players. Closed-panel, eight-monster captures were not timed and postdate the historical benchmark's texture lookup |
| Fourth/fifth trees | [Fourth-tree finding](client-skills.md#12-the-fourth-tree-native-skill-003), PR #158, and session #204; fourth tree implemented within stated limits, fifth-tree card/item behavior unfinished |

The layout probe/manifest handoffs #168/#172 and fixture verification #171 were also read. Their record,
lease, generated-layout and journal details remain in technical docs rather than expanding the public README.

## Media and publication

No images added, generated or edited. Existing README images and `scripts/audit_repository.py` pins remain
byte-identical. The reviewed source/provenance is retained in DOCS-README-002's handoff and README-STRESS-001.
Images 26/27 were visually rechecked in this lane: synthetic short player names and the Preview hero, no account
name, private path or other players' chat. All 27 reviewed-media hashes match the unchanged audit pins.
The older world comparison caption now states that it predates the merged cloud/dragon/flame/haze work.
Older quest images illustrate their captured UI, not proof that opaque NPC-list decoding is complete.

The README separates instruction-case comparisons, fixture frames, private unittest results and measured
frame rate. Offline test coverage does not establish encrypted requests, real server policy, account lifetime,
full map/item rendering, clean-user installation or live-game parity. Network/live lanes remain with the owner.
No code, data, image, validator, pin, installed app, credential or signing state changes belong to this task.

## Verification

The milestone [handoff](../handoffs/README-REFRESH-003.md) records the final local gate and audit counts.
Latest main `237f094`, PR #211, was integrated under the merge lock before that gate; its runtime ownership
changes and both sets of shared-doc entries are preserved. The authored diff remains seven Markdown files.
The full Mac gate uses synthetic/offline tests; this documentation lane does not repeat #200's private run.

## README-REFRESH-004 claim sources

Documentation-only refresh on 2026-10-28 from main `fa63719`, the merge of PR #241. Read every merged PR
from #214 through #241 (19 merged PRs; the other numbers are issues) and their committed handoffs. No new
instruction, live-game or timing evidence was acquired.

| Public claim | Merged source and evidence boundary |
|---|---|
| Native Preview refresh | [APP-REFRESH-001](../handoffs/APP-REFRESH-001.md) #215; offline smoke runs, stale export lookup and MP/AG fixes. No gate-5, second-user or signing completion |
| Temporal checks | [RENDER-TIME-001](../handoffs/RENDER-TIME-001.md) #217; native half only, fourteen views/thirteen maps, 21 samples per view. LIVE half open |
| World coverage | [I](../handoffs/RENDER-WORLDS-I.md) #219, [J](../handoffs/RENDER-WORLDS-J.md) #227, [K](../handoffs/RENDER-WORLDS-K.md) #232, [L](../handoffs/RENDER-WORLDS-L.md) #238. 33/144 primary methods across 11/48 classes, 111 remain. Icarus full-draw error 26.897 → 23.154 is the only new image score; eleven original PNGs are unavailable |
| Skill visuals | [RENDER-EFFECTS-002](../handoffs/RENDER-EFFECTS-002.md) #221 and [003](../handoffs/RENDER-EFFECTS-003.md) #230; 18/23 primary, 56/77 weighted, bounded to the 23 native cast routes. Rageful Blow and variants remain |
| Special item bodies/links | [Part 7](../handoffs/RENDER-ITEMS-002G.md) #216, [H](../handoffs/RENDER-ITEMS-002H.md) #225, [I](../handoffs/RENDER-ITEMS-002I.md) #233, [J](../handoffs/RENDER-ITEMS-002J.md) #240. 880/1,674 bodies, 17/17 skins, 17 link targets / 22 types; 794 bodies and rank-5 owner effects remain |
| Session domains | [Ground items](../handoffs/SESSION-ITEMS-001a.md) #224, [minimap markers](../handoffs/SESSION-MAP-001a.md) #229, [party](../handoffs/SESSION-SOCIAL-001a.md) #237, plus [globals](../handoffs/SESSION-GLOBALS-001.md) #211. 11/11 fixture scenarios, 86 inbound frames, zero unbound/undecodable; two unrecovered intents and nine unsent requests. No pick-up answer, inventory insertion, zen credit or encrypted round-trip |
| Sound | [AUDIO-002D](../handoffs/AUDIO-002D.md) #228 and [AUDIO-002E](../handoffs/AUDIO-002E.md) #235; 76 caller adapters/sound-capable sites. Pick-up success, event/remote inputs, music 43/44 and FMOD parity remain |
| HelpWindow | [SYS-MISC-001b](../handoffs/SYS-MISC-001b.md) #241; 888 instruction cases, 18/18 mutants. Ctrl+H is a native binding; the original open route is not established |
| 80-player performance | [NATIVE-PERF-003](../handoffs/NATIVE-PERF-003.md) #201; crowd80 18.37 and tormenta80 18.94 fps, rounded to 18.4/18.9. No later PR re-timed them; 25 fps remains open |

[VERIFY-HARNESS-002](../handoffs/VERIFY-HARNESS-002.md) #239 is internal validator plumbing and is not
summarised in the README. No images were added, generated or edited; all README media and audit pins are
unchanged. Network, login, live play and owner-blocked lanes remain listed as open.

## README-REFRESH-005 claim sources

Images and text refresh on 2026-11-06 from main `18ab0134` (the merge of PR #316). Lane A covers the world, effect,
combat, mount, crowd, comparison and model images and the "What works today" numbers outside the login,
character and interface-window sections; README-IMAGES-B covers those. Every new native panel is a window-only
headless render of `mu-world` built from that main. No live game was started; the original-client panels are
crops of existing captures (October 18/22, DATA-ACQ-002 October 28).

| Public claim | Merged source and evidence boundary |
|---|---|
| World inventory 144/144 methods, 48/48 classes | [S3](../handoffs/RENDER-WORLDS-S3.md) #303 with [S](../handoffs/RENDER-WORLDS-S.md) #301 and [S2](../handoffs/RENDER-WORLDS-S2.md) #302; earlier N–R2 #248–#260. Class methods, not complete maps |
| Class render slots 142/144 | [SLOTS](../handoffs/RENDER-WORLDS-SLOTS.md) #308 (census 49 → 125), [SLOTS2](../handoffs/RENDER-WORLDS-SLOTS2.md) #311 (→ 142); Test Area 121's two slots remain |
| World table rows | [AFTER](../handoffs/RENDER-WORLDS-AFTER.md) #262, AFTER2–6 #270/#278/#281/#285/#291, [G3](../handoffs/RENDER-WORLDS-G3.md) #269, [Q](../handoffs/RENDER-WORLDS-Q.md) #259, [Q2](../handoffs/RENDER-WORLDS-Q2.md) #272, [EFFECTS-008](../handoffs/RENDER-EFFECTS-008.md) #271 |
| Kubera 4.321 → 2.037, 1.591 | SLOTS #308 (main `b8645181` before/after); 1.591 is [APP-REFRESH-006](../handoffs/APP-REFRESH-006.md)'s tour with the installed Native Data, not a like-for-like delta |
| 27/48 classes captured, 32 views in 31 worlds | [DATA-ACQ-002](../handoffs/DATA-ACQ-002.md) #244 |
| Live temporal half | [RENDER-TIME-002](../handoffs/RENDER-TIME-002.md) #249 and [003](../handoffs/RENDER-TIME-003.md) #258; `compare --mode live` still fails (phase unaligned) |
| Skill visuals 20/23 (65/77), rank-5 19/19 | [RENDER-EFFECTS-004](../handoffs/RENDER-EFFECTS-004.md) #247, [005](../handoffs/RENDER-EFFECTS-005.md) #257 |
| Bows: 0 unsupported in 40 bow scenes; 1,561 before | [007](../handoffs/RENDER-EFFECTS-007.md) #274, [009](../handoffs/RENDER-EFFECTS-009.md) #283, [010](../handoffs/RENDER-EFFECTS-010.md) #287 (1,561 → 553), 011–014 #292/#296/#300/#306 (→ 0), [015](../handoffs/RENDER-EFFECTS-015.md)/[016](../handoffs/RENDER-EFFECTS-016.md) #309/#313 (40 bows, 10 staff, 0). This lane's six bow renders also report 0 |
| Ground skill 2044: rain, rings, stones, craters, 2 cues, offline cast | 015 #309, 016 #313, [APP-POLISH-005](../handoffs/APP-POLISH-005.md) #314; this lane's scene: 14 arrows, 121 effects, 0 unsupported |
| Item bodies 1,319/1,674, links 18 / 24, 355 left | [RENDER-ITEMS-002Q](../handoffs/RENDER-ITEMS-002Q.md) #316, census [002P](../handoffs/RENDER-ITEMS-002P.md) #310 |
| White item types 1,431 → 13/1,691 | [TEX-001](../handoffs/RENDER-ITEMS-TEX-001.md) #263 (1,431 → 94), [TEX-003](../handoffs/RENDER-ITEMS-TEX-003.md) #286 (125 → 36), [HIDDENMESH](../handoffs/RENDER-ITEMS-HIDDENMESH.md) #295 (36 → 13 hair meshes) |
| HUD vitals, ItemTRSData icons, window title | [APP-POLISH-002](../handoffs/APP-POLISH-002.md) #294 (1,028 cases), [APP-POLISH-004](../handoffs/APP-POLISH-004.md) #307 |
| Preview reinstalled November 6 | [APP-REFRESH-006](../handoffs/APP-REFRESH-006.md) #312 |
| Music entries 43/44, effect sound sites | [AUDIO-002F](../handoffs/AUDIO-002F.md) #243, RENDER-EFFECTS-015 #309 |
| crowd80 23.18/20.21, tormenta80 24.78/20.83 fps | [NATIVE-PERF-004](../handoffs/NATIVE-PERF-004.md) #246; shared host, two repeats, strict 25 Hz only crowd40 |
| Test tooling timings | [TEST-SPEED-001](../handoffs/TEST-SPEED-001.md) #297 (item_ranked 665.9 → 22.1 s), [002](../handoffs/TEST-SPEED-002.md) #299 (meshdraw 367.99 → 57.21 s), 003 #305, 004 #315 |

Kept images and why: 16 (login: the native panel from today's main differs from the October one by a mean
of about 10/255 per channel, mostly ship/sea animation phase, with no visible improvement), 17 (mu-viewer
and the model decoders are unchanged since the image), 26/27 (rerunning README-STRESS-001's script on this main
gives the same crowd frames; the only visible change is the HUD orbs, which since APP-POLISH-002 read the
session's vitals and show `16960/0` because the stress fixture feeds no maxima, so the October frames stay).

## README-IMAGES-D claim sources and media

Images and text refresh on 2026-11-07 from main `02e4d94d` (the merge of #344 RENDER-ITEMS-CLOAK; the branch started
at `a7f7b247`, #343). Every image is a window-only headless GL render of `mu-world` built in the lane
(`nice -n 10 make -j4 -C native world`), with the installed APP-REFRESH-006 Native Data read-only (`objects/`,
`gfx/`, `lang/`) and `MU_GFX_PUBLIC_DEMO=1`. Camera: the world FOV, 39 (every frame report reads `fov 39.000`). No live
game, original client, account or network.

| Public claim | Merged source and evidence boundary |
|---|---|
| Item bodies 1,363/1,674, 311 left, links 18 / 24 | [RENDER-ITEMS-002T](../handoffs/RENDER-ITEMS-002T.md) #341 (1,359 → 1,363; 002R/002S before it) |
| Hero records: level, excellent option, ext; demo outfits | [APP-POLISH-008](../handoffs/APP-POLISH-008.md) #338; this lane's scene: hero slot 6 `0x0b2a` level 9 option 1, players 861 pre-draw effects / 0 refused over 91 frames |
| Inventory equipment slots with the hero's gear | [INVENTORY-FX](../handoffs/INVENTORY-FX.md) #343 |
| Cloak of Brilliance sparks; armour owner effects in the world | [RENDER-EFFECTS-020](../handoffs/RENDER-EFFECTS-020.md) #339, [RENDER-EFFECTS-021](../handoffs/RENDER-EFFECTS-021.md) #342; this lane's fixture: 164 owner effects / 0 refused, 419 pre-draw / 0 refused |
| Physics capes of `0x2382`..`0x2385`, `0x2394`, `0x2395` | [RENDER-ITEMS-CLOAK](../handoffs/RENDER-ITEMS-CLOAK.md) #344; this lane's fixture: `cloak` 5 created, 65 drawn, 0 gated |
| Raklion's whole custom slot, Karutan's 0x81 crystal | [RENDER-WORLDS-RAKLION](../handoffs/RENDER-WORLDS-RAKLION.md) #337, [RENDER-WORLDS-KARUTAN](../handoffs/RENDER-WORLDS-KARUTAN.md) #340 (text only, no image; see the handoff) |
| Preview reinstalled November 7 | [APP-REFRESH-009](../handoffs/APP-REFRESH-009.md) #345, built from `a7f7b247` (#343); #344's capes are not in the installed app |

Common environment (from the repository root, after `. ~/Documents/MTM/mu-mac-tools/native/private-env.sh`;
`D=$MU_NATIVE_DATA_DIR`, `MU_LANG_DIR=$D/lang`, `MU_GFX_PUBLIC_DEMO=1`):

- **08** (replaced, 780×800 PNG, pngquant 70–95): `mu-world --game-root "$MU_GAME_ROOT" --objects-dir "$D/objects"
  --headless --backend gl --no-audio --width 1280 --height 800 --class 1 --tile 138,123 --gfx "$D/gfx" --hero-name Preview
  --placement native/world/lorencia-demo-placement.txt --items --players <copy of lorencia-demo-players.txt without
  Aeris's party flag> --hero-item weapon0=Item/CookriShortSword.bmd@0:68:9:1 --hero-item
  weapon1=Item/Shield01.bmd@6:0:7 --hero-item wing=Item/Wing02.bmd@12:1 --gfx-open inventory --npc-script 50:tipinv:0
  --frames 61 --every 60` with `MU_GFX_LIB`, `MU_GFX_SINGLE_BUFFER=1`, `MU_GFX_TEST_CLOCK=1`; frame 60, crop x 500..1280.
  The party flag was dropped so the party list does not cover the inventory window (both sit top right).
- **31** (new, 1600×1000 JPEG): the app's demo arguments (`--placement`, `--npc --npc-demo
  native/world/lorencia-demo-npc.txt`, `--combat --progress --items`, `--players native/world/lorencia-demo-players.txt`)
  with Ironclad's three records as above, `--class 1 --angle 90 --tile 140,124 --hero-name Ironclad --frames 91 --every 5`,
  once at 1600×1000 (the frame) and once at 3200×2000 (the inset: region 1250,480–1950,980, scaled 0.8). Frame 90.
- **32** (new, 1600×1000 JPEG, test fixture): `--class 0 --angle 180 --tile 136,133 --hero-name Preview --hero-item
  wing=Item/InnocenceCape.bmd --players <fixture> --player-range 20 --frames 61 --every 5 --width 3200 --height 2000`,
  frame 30, region 200,250–2760,1850 scaled to 1600×1000. The fixture (local, not committed):

```
player Velvet   class=0x00 at=132,129 dir=3 pk=3 level=400 helm=7:10:7 armor=8:10:7 pants=9:10:7 gloves=10:10:7 boots=11:10:7 weapon0=0:102:7 wing=12:156:0 route=138,135;132,129 idle=4
player Seraph   class=0x00 at=140,133 dir=7 pk=3 level=400 helm=7:10:7 armor=8:10:7 pants=9:10:7 gloves=10:10:7 boots=11:10:7 wing=12:158:0 route=134,127;140,133 idle=4
player Nocturne class=0x04 at=131,132 dir=3 pk=3 level=400 helm=7:4:7 armor=8:4:7 pants=9:4:7 gloves=10:4:7 boots=11:4:7 wing=12:174:0 route=137,138;131,132 idle=4
player Thorne   class=0x01 at=137,128 dir=3 pk=3 level=400 helm=7:221:0 armor=8:221:0 pants=9:221:0
player Ashe     class=0x01 at=140,131 dir=3 pk=3 level=400 armor=8:402:0
```

JPEGs: quality 85, 4:2:0, optimized, progressive, no EXIF. SHA-256 (also the audit pins):
08 `f43c3dadbee8a9abf1f1552605c792bf44c8e1d3113c3d29de883a71708cb4f9` (402,126 bytes),
31 `1a6ef1b5cc1e5e58133022bf5e880673c6c75a98b368fea286e19e73fbef9377` (434,420 bytes),
32 `28b2c101a4a859662e184043d6f23e403b6895cd31b196c38bd78a33b77c1a05` (329,138 bytes).
The 31 and 08 source frames were rendered again after the #344 merge and are byte-identical (no cloth wing in them).
