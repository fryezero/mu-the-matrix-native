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
