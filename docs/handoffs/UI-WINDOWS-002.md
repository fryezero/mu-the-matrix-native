# UI-WINDOWS-002

## Delivered scope

Eight presentation adapters now open in the offline native client: seven
additional surveyed movies and a second instance of StorageInven. All data
is authored demo data or the original empty state. Request, configuration,
item and guild-management actions are inert. Original Help's open route
remains unproved; existing native Ctrl+H keeps its native-policy label.

Started from UI-WINDOWS-001 `13721b04`, then integrated steward main
`6b75fbda`. Lane production source is `142c3aeb14de4d22ed7949d0f20f02d9f950c57e`. Publication
then integrated steward main `fb747e42` at `ee27cde402893d3a39d1106bad6b92d996416579`;
that merge adds world/audio work, with no further lane controller edits.
Final head is in PR metadata. The [research](../research/client-ui-windows.md)
records addresses, the provider boundary and every remaining survey row.
The registry has 44 entries / 43 distinct filenames. Twelve of the historical
134 baseline-absent survey rows are bound; 122 remain. This is a survey
count, not whole-client completion or full menu fidelity.

| Window | Proved route | Fixture / lifecycle |
|---|---|---|
| MacroMain | Z, `0x00efd3a4`, manager `+0x144` | Empty base-DK options, three local tabs, close; activation and saving refused |
| MacroSub | MacroMain `btnMenu`, `0x00ba7d89` -> `0x00ba6fcf` -> `0x00babb31` | Potion / condition child views; same-type toggle, different-type replacement, parent teardown; config actions refused |
| HuntRecord | End, `0x00efc39a`, manager `+0x1d0` | Original placed `scene`; zero current record, empty history, table/graph/total/per-second; full -> mini -> closed |
| Expanded storage | H, `0x00efc715`, getter `0x00c08ba8`, manager `+0x104` | Separate empty 120-cell view, only while an authored warehouse is open; close / parent teardown; H never acquires storage |
| MatchingParty | N -> selector Party; callback `0x00bc04f4` | Empty catalogue, search/recruit/party-info tabs, close; original requests replaced by empty provider |
| MatchingGuild | N -> selector Guild; callback `0x00bc0700` | Empty legacy catalogue and search/recruit tabs; fifteen authored Class 1..15 filter labels; requests refused |
| Guildmatching_2024 | G/menu 10, `0x00efcb7c` -> `0x00b0aed2` | Empty catalogue, recruit and nested guild-info/member/alliance/rival views; no guild authority |
| PlayGuide | Ctrl+T `0x00efc0da`; menu 22 `0x00c71576` | Original empty guide frame and close. External guide content/provider remains absent |

## Controller and sound checks

[Production controller](../../native/gfx/mu_gfx_windows2.inc) uses an exclusive
allowlist before the existing NPC/item/social/command handlers. Unknown
callbacks refuse. The [C host](../../native/tests/ui_windows2_host.c) lists
all 52 forged action names, tested against eight new windows: 416 action/window
combinations in each synthetic and real-movie host. Hero, held item, potion
and foreign-handler counters remain unchanged. Checks also cover readiness,
missing routes, parent teardown, tab bounds and direct/menu sound ownership.
All fifteen legacy class captions and HuntRecord's non-test state are read
back after ten real-movie ticks. HuntRecord already places `scene`; attaching
another clip creates a duplicate test panel and must not be done.

Thirty-four bounded original route/sound decisions pass, including Z/H/End,
menu 22's getter/toggle/sound sequence, and UI-WINDOWS-001's key/menu blocks.
These are bounded caller checks, not every original world/class/context gate.
Fixtures supply eligibility. Sound 25 uses `0x00c716f6` for menu dispatch,
`0x00efd43a` for Z and `0x00efc772` for eligible H, once per accepted event.
No guessed tab/child/close sound is added. The unowned GFx sound query
`0x00b49b97` remains unwired. Existing UI audio's 5,803 original comparisons,
release/hold/refusal/mute/detach and installed decode regressions pass.

## Native journeys and captures

Actual worktree `native/build/mu-client`, canonical read-only Native Data and
GFx library, `--no-store --no-audio`, `MU_GFX_SINGLE_BUFFER=1`,
`MU_GFX_TEST_CLOCK=1`, `MU_GFX_PUBLIC_DEMO=1`. Logical size 1024x768,
framebuffer 2048x1536. No installed bundle was replaced by this lane.
The final lane journey at `142c3aeb` has 222 frames and takes 25.90 s command
wall. Its UI controller inputs do not change in the publication merge.

Z opens Macro, its potion child and Other tab. End visits the full and mini
HuntRecord views and closes it. N opens both matching children; both Recruit
tabs work. G opens nested empty guild information. An authored empty storage
NPC opens the parent warehouse; H opens the expanded grid. The expanded,
parent and inventory close. Ctrl+T opens the guide and Esc closes it. Final
frames show all these views closed. Earlier exploratory runs also exercised
HuntRecord's Graph tab. No casts, transfers or live requests were introduced.

All fifteen final proof frames were inspected and are fully opaque. They are
window/framebuffer-only, with demo names. Local proof directory was
`~/Documents/MTM/mu-mac-tools/native/renders/ui-windows-002/`; captures are
removed after PR-ready per the owner. No screenshot or client asset is committed.

| Inspected capture | SHA-256 |
|---|---|
| `checked-closed.png` | `b8f2d129c080c0d8d9cd4477b2dfa2c27567cc6b5b14529baf0363f4cbd4957c` |
| `checked-end.png` | `4d95719004d99570371f605e705beb5c46563cb7a227bf6a57591b13731c414b` |
| `checked-expanded.png` | `eca022a40858e4370675560503fc64294c60db6e111100bd1336804b99aa282c` |
| `checked-guide.png` | `58c3b06702a28afb3273ea7bee3f4870ec047b8a7b442ff28f0227b18a59d3ad` |
| `checked-guild-info.png` | `e96bb56335cec3e4b9c56c7c949015a158561842d4cf671940f093d14787b352` |
| `checked-hunt.png` | `e378c3ca68cafc29925b6173d11e40a86fef976f507d7c5f8fd0de6c49e7c99e` |
| `checked-legacy-recruit.png` | `63279ac75eb3378f54d58f8cd025dc7e2e5cf96efbea7fabd2d6d0e37d18c925` |
| `checked-legacy.png` | `48561f7b6c3680b2d7d3a6bab4026fb103dce24c5a516d515fac7410730f2077` |
| `checked-macro.png` | `873909e7a609e25b9b0bc62a731458653d93dd303b85e7c9edef3c9934457278` |
| `checked-mini.png` | `07924b33f4ac72e055e0620d741fea58278a7f5ba1ff28a5ecfe01266a0397aa` |
| `checked-other.png` | `2c46176e9544105c5315d0c80d69882273257283e9433771ddc2c30c30436559` |
| `checked-party-recruit.png` | `967aeb2d0b8fb6a79d0148a7997014d2ebbbeac78c743136754b8bfc0f0f289d` |
| `checked-party.png` | `64a4395e7af654418dd4442f88a372d2d73e9df811cde352ec688528c79d84fa` |
| `checked-sub.png` | `679f01da2f9b29dbef4892e5ad36e8b616f94630fe157f3faa2b9886e926487f` |
| `checked-warehouse.png` | `500ce5065423f5962c8830240e80b272d5a97f8b6969cf78ac0ca82d5d9184d2` |

## Checks and wall times

All commands run from the repository root. Heavy jobs use `nice -n 10`.
Builds use `-j4` initially, then `-j2` after the 21:50..22:10 resource-guard
wait, using the common brief's twenty-minute fallback. Validator jobs = 2.
No full gate or hosted workflow ran in this lane.

| Check | Result | Wall seconds |
|---|---|---:|
| Integrated root build / final root freshness | pass | 26.86 / 0.56 |
| Final graphical client and explicit world build | pass | 9.27 |
| Current-main baseline explicit world build | pass | 5.47 |
| Affected portable before main integration | 134 work items; 1,424 tests, 1,164 passed, 260 optional skips, no failures/errors, at `32c59170` | 385.5 execution / 464.59 command |
| Affected portable after main integration | 135 work items; 1,429 tests, 1,166 passed, 263 optional skips, no failures/errors, at `d9015c71` | 432.5 execution / 504.20 command |
| Focused private UI/windows/audio | 15/15, including original menu-22 block and UI audio | 71.70 |
| Final private new-window controller module | 4/4; both hosts, all fifteen dynamic captions and 416 refusals per host | 3.94 |
| Final affected private validators | 12/12, zero fail/error/skip, no mutants | 129.91 |
| Final actual native journey | 222 frames, eight adapters, final all-closed captures | 25.90 |
| Default identity, 46 maps | 92 PNG + 92 dumps + 46 normalised report identities | 168.47 |
| Final documentation-consumer modules | 36 tests, one optional skip, zero failures/errors | 7.65 |
| Lane audit before publication integration | 2,206 files, zero rejected | 29.57 |

The final changes after the broad integrated run were the original menu-22
allowlist, its original-instruction test and fixture text/caption completion.
Final focused controllers and all selected validators confirm that source.
**8d reduced:** 130 selected native work items exceed the 40-item cap.
The changed private UI modules plus UI audio run from the root with canonical
`private-env.sh`. The broad run includes shared GFx2/3, input/router, Help,
map, social, layout, session and shell consumers, per brief 6b. No validator
checks or original reconstruction target changed in this lane, so mutants
were not rerun.

| Steward validator | Cases / contracts, zero mismatches | Seconds |
|---|---:|---:|
| `validate_app_polish1` | 752 | 24.3 |
| `validate_app_polish2` | 1028 | 4.2 |
| `validate_app_polish4` | 10485 | 35.7 |
| `validate_app_polish7` | 5120 | 3.1 |
| `validate_audio_callers` | 5528 | 6.8 |
| `validate_audio_domains` | 2544 | 36.9 |
| `validate_audio_items` | 3000 | 4.6 |
| `validate_gfx3` | 6 skill + 18 window; loader/menu | 7.3 |
| `validate_map_polish` | 876 | 0.5 |
| `validate_movement` | 6614 | 71.8 |
| `validate_render_effects16` | 424 | 4.0 |
| `validate_worlds_fog` | 4044 | 9.9 |

Steward validators: validate_app_polish1,validate_app_polish2,validate_app_polish4,validate_app_polish7,validate_audio_callers,validate_audio_domains,validate_audio_items,validate_gfx3,validate_map_polish,validate_movement,validate_render_effects16,validate_worlds_fog.
All twelve lane rows passed at `142c3aeb14de4d22ed7949d0f20f02d9f950c57e`.
Publication integration checks below identify the five rerun rows and their
second tested commit; the other seven rows have unchanged compiled inputs.
Use canonical
`~/Documents/MTM/mu-mac-tools/native/private-env.sh` from the root.
Keep the selected `validate_movement` symbol-level fallback. After the
publication integration runs below, later commits only finish this ledger.

## Default identity and binary provenance

This lane-delta sweep precedes the publication integration. Before is
explicitly rebuilt main `6b75fbda`; after is rebuilt lane source `142c3aeb`. SHA-256 differs, so this is not a self-comparison.

- Before: `1785e14013da7b5caa263a89f95d9de3cc4e2b259a0568b5a2a4659621bc473b`.
- After: `2bc66a580f3e900b38df108ea9c2e71d372bcfd3d0c6e6e3025c214a95a545dd`.

One baseline render only: 74.64 s. Final after render:
93.83 s. A valid earlier after render at `e658680e` was superseded
when visual review required the dynamic-caption fix; baseline hashes were
retained and never rerendered. Both existing manifests resolve their original
local inputs. Resolution 640x400, default draw, no draw_all/live_time.
PNG and dump bytes compare directly; report output and binary paths are
normalised. All 230 file identities match. This does not establish original
image equivalence, UI pixel parity or performance acceptance. The later
publication merge intentionally changes world visuals inherited from main,
so these identities are not a claim about that merged tree. Its explicitly
rebuilt mu-world SHA-256 is
`fe480a83bab827fe6a3a1bae1a9704f301aa759fe42ebcb603b3aa89e71ffd08`.

## Limits, next and cleanup

Help's only direct getter caller is `0x00b6b744`; it reads auxiliary
EventMapHelper rows and does not open Help. Menu 3 is a sound-only epilogue,
8 opens SystemMenu, 22 opens PlayGuide. Indirect or other-scene Help routes
remain unproved. No F1 or guessed Help menu binding was added.

AutomaticMacro/Home activation remains inert; an independent presentation
open lifecycle is unproved. ExtensionBagFrame needs its child route and grid
owner. The separate fifth-tree item viewer needs its card/item lifecycle,
with power features excluded. The other 119 left rows keep their individual
untraced-route/provider reasons in the research survey. No authoritative
macro timing/configuration, hunting history, matching catalogue, storage
expansion state or guide content is reconstructed. Labels are authored English
fixtures; full localisation, all class/world predicates and other window
sizes remain unproved.

No original client, protection module, live memory, Wine play/staged app or
installed Native Preview bundle was changed by this lane. No README work.
No raw assets, data rows, screenshots or private-input symlinks are committed.

WIP checkpoints `88b70c06`, `620c4cd5`, `32c59170`, `d9015c71`,
`e658680e` and final source above were pushed before readiness, with done /
left / next-step sections preserved in their history. The four shared status
conflicts during the main merge kept both lanes' entries. This is PR-ready
for the merge steward, not merged. Finish before the owner's 02:30 stop.

After the ready-prs entry, push nothing further. Cleanup removes this lane's
renders/scratch, its detached baseline tree, build outputs, worktree and
local branch. The remote PR branch stays for the steward. No new input needs
retaining. The next APP-REFRESH lane can include these views after the merge.

## Publication integration checks

Latest steward main `fb747e42` brings AUDIO-003 and RENDER-WORLDS-INNER-002.
Merge `ee27cde402893d3a39d1106bad6b92d996416579` retains both sides of three
shared status conflicts. There are no controller changes from `142c3aeb`.
The final integrated root build passes in 23.44 s; the explicit graphical
client/world rebuild passes in 12.80 s. No compiled inputs change afterward.

The portable rerun uses `--affected-since 142c3aeb`: 157 work items,
1,650 tests, 1,365 passed, 285 optional skips, zero failures/errors.
Wall: 382.1 s execution / 443.33 s command. Private UI-WINDOWS-001,
UI-WINDOWS-002 and UI audio pass 15/15 in 36.05 s, including the original
routes, both inert-action hosts, dynamic captions and sound regressions.
The native selection exceeds forty items, so **8d reduced** still applies.

Within the twelve lane validator rows, `--list-affected-since 142c3aeb`
selects these five; all pass at `ee27cde402893d3a39d1106bad6b92d996416579`,
zero mismatch/fail/error/skip, no mutants, 56.12 s command wall:

| Rerun validator | Cases | Seconds |
|---|---:|---:|
| `validate_audio_callers` | 5,528 | 6.0 |
| `validate_audio_domains` | 2,544 | 26.3 |
| `validate_audio_items` | 3,000 | 4.3 |
| `validate_movement` | 6,614 | 56.0 |
| `validate_render_effects16` | 424 | 3.5 |

The other seven rows retain their `142c3aeb` results: their compiled inputs
are unchanged. Default identity and window captures above identify the
pre-integration lane source; no new baseline render is taken. Steward main's
world/audio changes retain their own handoffs and gate provenance.

The final `--list-affected origin/main` confirms the same twelve steward rows
(26.36 s), including the movement fallback.

Final staged audit: 2,216 files, zero rejected, 15.44 s. The final ledger
bytes also pass the audit per-file checks before staging.
