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
