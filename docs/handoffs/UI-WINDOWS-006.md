# UI-WINDOWS-006

## Delivered scope

Base main `c5b9d5ca` (PR #400 merged). The restored text/data pins are
unchanged. The [research](../research/client-ui-windows.md), the
[missing-piece ledger](../research/ui-window-missing-pieces.csv), the
[trigger ledger](../research/ui-window-triggers.csv), the
[state ledger](../research/ui-window-state-needs.csv), the
[parameterised-open ledger](../research/ui-window-parameterised.csv) and the
[route survey](../research/ui-window-route-survey.csv) hold the per-row
evidence. No client bytes, movie content, original records or screenshots are
committed.

The brief expected several static groups among the 33 "route proved, provider
missing" rows. Reading every opener shows one: 32 rows need state that is not
static. One movie is admitted, two no-route rows gain a proved route, and
every remaining row has its exact missing piece on record.

| Classification of the original 118 rows | Before | After |
|---|---:|---:|
| Route proved, empty or authored provider complete | 13 | 14 |
| Route proved, provider missing | 33 | 34 |
| State-dependent, refused | 30 | 30 |
| No route found by the bounded searches | 42 | 40 |

MapName leaves the provider-missing class; EventMapHelper and MiniGameRummy
enter it from no-route. The historical 134-row survey changes 28 -> 29 bound,
106 -> 105 unresolved. Registry entries rise 61 -> 62 and distinct filenames
60 -> 61. These counts are not a client-completion percentage.

## Missing pieces of the 33 rows

Trigger roots come from `scripts/survey_ui_triggers.py` (bounded direct-caller
chains to the receive dispatcher `0x01287ead`, a stored table entry or no
caller; 136 sites). Each opener was then read; nothing is inferred from a
root kind alone.

| Group | Rows | Kind | Movies |
|---|---:|---|---|
| Server answer, no offline owner | 17 | authoritative | ArkaResultInfo, CursedTempleResult, CursedTempleScore, Duel, EventMapRoundCount, GoldArcher, GuildCreateFrame, ImageNotice, IngameShop, ListofMatches, ProgressFrame, RebuyList, RewardItemExchange, StrongestMatchRank, StrongestMatchResult, SwitchMode, TimeCounter |
| Server answer, offline owners exist | 1 | static | MapName (admitted) |
| Item or slot record of one kind | 8 | authoritative | ArtifactInfoPopup, PetInfoPopup, DivideWindow, MonsterSoulReward, Pentagram, SlottedWingInfo, SkillTree5thLevelUpPopup, SkillTree5thSlotClickPopup |
| World or HUD state | 3 | authoritative | BossHpUI, QuickCommand, DeathPenaltyExpRecovery |
| Parent window not bound | 2 | parent has no static route | GuildPosition, MiniGameHelpWindow |
| Pending transaction step | 1 | transaction | PersonalShopCaution |
| Upstream caller unresolved | 1 | unknown | NpcGateKeeper |

No row lacks only a label table, a layout family or a sound. The static
pieces of the 32 refused rows (labels, layouts) do not make them admissible,
because nothing offline produces their trigger or their records. Two leads
for a later decision: QuickCommand needs only world picking of a demo player
(Alt + right button, all command buttons disabled), and EventMapHelper needs
a static row table plus an NPC dialogue page with its two buttons.

## MapName

| Movie | Original route | Provider and refusal |
|---|---|---|
| MapName | `+0x128`; join answer `0x0124cc64` at `0x0124e15e`, respawn answer `0x0127bd9e` at `0x0127c567`, teleport answer `0x0128136d` at `0x01281ea7` only for a non-zero number, after both close-alls; open method `0x00baee4a`; update `0x00baf120` closes after 5000 ms | Map name from the map-name function `0x016baaa6` (the table the top menu already uses). Strife line and occupying guild stay empty: one needs a server-mode flag, the other a server answer. No banner in world `0x28` or for a world named from runtime state |

The three handlers already have offline owners (hero join, demo respawn, the
map session's teleport answer), so no new owner is added. Added lines only in
shared files: the first location feed in `world_gfx.c` reports the join,
`parts/combat.c` the respawn and `world_rt.c` the two travel branches.
`native/gfx/mu_gfx_windows6.inc` holds the controller.

Native choices, stated as such: the offline join precedes the movie's UIInit,
so that open is held until the movie is ready (the latest arrival wins). The
banner sits in registrar group 3 with InfoPopup; it takes no pointer input and
is not closed by Esc or the NPC close-all. Whether the original close-all
list contains group-3 movies is unproved. The movie fades in over its first
frames, so a capture needs about sixteen frames after the trigger.

## Third sweep: parameterised opens

Idea not tried by 004/005: a window class may have a virtual method other
than `+0x40` / `+0x44` that takes arguments and opens its own window through
`this`. `self_open_slots` finds such methods; the manager-rooted pass then
accepts virtual calls through exactly those vtable offsets. The default pass
and its 482-row ledger are unchanged.

Two methods, both `+0x4c`: EventMapHelper `0x00b6b656` and MiniGameRummy
`0x00bca125`; five manager-qualified callers. EventMapHelper opens from the
NpcDialogue callbacks `onClickbtnEnterTime` / `onClickbtnEnterLevel` and from
an EventMapEntranceUI method; MiniGameRummy from a server-answer handler. The
already-bound NpcQuestProgress is the control: naming its `+0x4c` rediscovers
the known quest-progress owners. The strict walk does not prove that control
method by itself (an unknown store precedes its open). Forty rows stay
no-route: eight with a manager slot, 32 without a joined registration.

## State-dependent rows

The 30 rows stay refused; the state ledger has one line each. Sixteen are
opened only by server answers, five by server answers among other owners,
nine from callbacks, input or NPC-click owners that only apply inside an
event. OrdealSquareBattleEnter's opener is the already reconstructed talk
result `0x34`; its page needs schedule, entry count and party eligibility.

## Controller, sound and mutant checks

`native.tests.test_ui_windows6` has a synthetic host, the real movie and the
original instructions. The host checks the held join, the three owners, the
numbered-teleport rule, world `0x28`, a restart on a second arrival, the
5000 ms close (open at 4960 ms, closed at 5000 ms), the overlay limits and 13
forged callbacks. Hero, held item and potion state are unchanged; no foreign
action and no sound is delivered. The real movie reads back the name and the
two empty lines.

Original comparisons, every service stubbed: the open method in ten cases
(five worlds; strife and guild combinations; world `0x28`), the update method
in 24 cases (loaded, open, six elapsed times) and the three owner tails (four
teleport numbers with both close-alls first, respawn, join with both flag
values). The native invoke trace equals the original's for the fixture case.
The comparison also shows what the provider leaves out: `SetStrife` and
`SetOccupyGuild`.

Seventeen compiled mutants are caught, each by a host assertion or a differing
invoke trace: short-lifetime, late-close, no-restart, world-40,
unnumbered-teleport, lost-init-text, timer-after-name, invented-strife,
invented-sound, dropped-hold, stale-hold, forged-close, forged-action,
escape-closes, npc-close-all, pointer-press, pointer-hover. Thirteen are in
the controller, four in the shared layer files. The first harness looked only
at the host's exit code and let four trace-only mutants pass; it is not
passing evidence. One planted guard was redundant and was removed from the
code instead of kept as an uncatchable mutant. No registry mutant target
changed; older window mutants are not rerun.

`native.tests.test_ui_triggers` covers the third pass and the trigger census:
synthetic controls for saved-`this` opens, virtual opens, toggles, refused
receivers, unknown stores, the extra-offset join and the three root kinds
with the depth bound, plus the pinned results above.

## Native journeys and proof

Actual worktree `native/build/mu-world`, canonical private environment, real
read-only exported movies, headless window framebuffer, no audio, fixed GFx
clock, single buffering, public demo names. No app bundle or installed-app
journey.

One completed journey, 496 frames, 32 captures at 1024x768, six inspected
proof frames, all fully opaque, 6.77 s. Join shows the Lorencia banner and it
closes after 5 s; a numbered teleport to Noria closes nothing else and shows
the Noria banner; the respawn answer shows it again; each closes after 5 s.
No cast, pickup or NPC transaction is scripted. Two earlier probe runs found
the working capture offsets and are not final proof.

| Inspected proof frame | Shows | SHA-256 |
|---|---|---|
| journey/frame-0016.png | Lorencia banner after join | 77247fae7dc59361c12a6f28f7d72a973229a929aafce6a1dc40480203488836 |
| journey/frame-0144.png | closed after 5 s | 05b5bf2ec6f554fb88b78c651942d53fb26c870beaf6894df585510dbbf93605 |
| journey/frame-0176.png | Noria banner after the numbered teleport at frame 150 | 0699382ed2c907408f4f38ea4a38e39a2bd502aa003d75ff441fee6751cea520 |
| journey/frame-0288.png | closed after 5 s | 2512449ade478b2a7819977d20b33d1628a0a7e89e6cee77796e93bd4ae2c58b |
| journey/frame-0352.png | Noria banner after the respawn at frame 330 | a215c56fe0b5e3b961c6ba99f7b1ad5db8d8edb79b2778be2b89a7cd44a84835 |
| journey/frame-0464.png | closed after 5 s | 278e054c015df7891b9051ae8c44bd81c9afda2cf86f0f26d86570b8518dc75d |

Reproduction: `--headless --backend gl --no-audio --class 1 --tile 140,130
--width 1024 --height 768 --frames 496 --every 16 --hero-name "Demo Knight"
--no-items --travel-script "150:to:3:172:114 330:respawn"`, canonical
game/objects/gfx paths and `MU_GFX_TEST_CLOCK=1`, `MU_GFX_SINGLE_BUFFER=1`,
`MU_GFX_PUBLIC_DEMO=1`.

## Default identity and binary provenance

The baseline was built in this worktree at untouched main `c5b9d5ca` before
any compiled change and kept privately; no build in the main checkout and no
installed app. Baseline root/world builds take 36.00 / 5.55 s. Before binary
SHA-256: `0b67fc1e9ec614d2c318fb51d31f1205c7f8d5fd4921aa34834b969a23519c8a`.

The final binary was rebuilt with `make -C native -j4 world` immediately
before the after renders (0.27 s, already current). After SHA-256:
`1f4752dd5cc97a791a0d0b39d3112929a8acb53ed3ece6dff98fbf67e078e486`. It
differs from the baseline binary and is the binary of the proof journey.

All 276 artifacts are identical: 92 PNGs, 92 binary dumps and 92 reports,
over 14 October-22 and 32 DATA-ACQ-002 maps at 640x400, default draw, no
draw_all or live_time. Before renders take 23.99 + 70.22 s, after renders
16.51 + 52.55 s. Baselines were rendered once and never rerun. Reports compare
after normalising the output folder name only; PNG pixels and dumps compare
byte for byte. The tours run without the GFx layer, so the banner cannot
appear in them. This is native regression identity, not original-image
equivalence or performance acceptance.

## Checks and wall times

| Check | Result | Wall seconds |
|---|---|---:|
| Baseline root / world build at `c5b9d5ca` | Pass | 36.00 / 5.55 |
| Root / world build with the banner; final freshness check | Pass; same final binary | 6.76 / 6.38; 0.48 / 0.27 |
| Portable affected selection, 157 work items | 1579 tests: 1254 passed / 325 skipped, zero failures/errors | 473.55 including selection; 368.1 execution |
| Private, 8d reduced, 13 modules | 91 tests: 86 passed / 4 optional mutant classes skipped / 1 load timeout | 166.51 |
| Rerun of that one module's class (17-point layout matrix) | 2 tests pass | 62.52 |
| Banner module with its 17 compiled mutants | 6 tests pass; all mutants caught | 27.71 |
| Original banner comparisons alone | 3 tests, 10 + 24 + 7 cases | 2.55 |
| Third pass, trigger census and existing survey tests | 19 tests pass | 15.83 |
| Affected validators | 43 rows pass | 307.76 |
| Ledger reproduction: indirect and parameterised / triggers | 482 rows identical after line-ending normalisation, 7 rows identical / 136 sites identical | 12.60 / 0.26 |
| Native journey | 496 frames, six inspected opaque proofs | 6.77 |
| Default identity | 276 identical artifacts against the single baseline | 94.21 before; 69.06 after |
| Staged repository audit | 2361 staged files, zero rejected | 28.25 |
| Four documentation consumers | 36 tests: 35 passed / 1 skipped | 15.13 |

8d reduced: the affected native selection is far above the forty-item cap (a
layer change selects 152 native modules). The reduced private run, from the
repository root with canonical `private-env.sh` and `PYTHONPATH=native/tests`,
uses `native.tests.test_ui_windows6`, `test_ui_triggers`, `test_ui_windows5`,
`test_ui_windows4`, `test_ui_windows3`, `test_ui_windows2`, `test_ui_windows`,
`test_ui_indirect`, `test_ui_route_survey`, `test_native_item_services`,
`test_app_polish9`, `test_native_map` and `test_native_progress`. The one
failure was `test_app_polish9.LayoutSweep` at 1280x1024: the main movie did
not report its path in time while the 1-minute load was above 14. It does not
open the banner (the layer host has no arrival owner). Rerun alone at load 11
it passes all 17 points. It is reported as a load timeout, not as a pass of
the first run.

The portable runner uses the normal affected selection and excludes only
`native/tests/test_native_app.py`, as required, with the same wrapper as 005
(`--affected origin/main`). The banner mutants are opted in with
`MU_UI_WINDOWS6_MUTANTS=1`; `MU_UI_WINDOWS6_MUTANT_ONLY` filters by name. No
full gate or hosted workflow runs in this lane. Heavy commands use
`nice -n 10`, `make -j4` and at most two Python workers, one heavy lane
command at a time; three starts were held until the 1-minute load was at most 14.
Memory stayed above 25%. No quiet-machine performance claim is made.

## Limits and next

Thirty-two of the 33 entry rows keep a missing piece that is not static, and
the two newly routed rows join them. The 30 state-dependent rows stay refused.
Forty entry rows have no proved route, plus the separately withdrawn
PlayGuide. Help's original opener/F1, Home activation, the separate
fifth-tree inventory and the event-inventory openers remain refused; no new
static evidence completes them. No guessed binding. No transactions, stateful
data, stat formulas or power features.

MapName limits: the strife line and the occupying guild are never shown; the
close-all interaction is unproved; the held join is a native load-order
choice; other sizes, localisation and visual equivalence with the original
are unproved. The name is ASCII-folded like the top menu's.

Decisions for the owner, not evidence gaps: whether any server-answer window
should get an authored offline owner (17 + MiniGameRummy), whether fixture
items of the eight item kinds are wanted, and whether QuickCommand should
follow world picking.

No original/live client, protected module, live memory, owner Wine app,
staged Wine app, installed Native Preview, Native Data refresh, README work,
subagent or hosted workflow. Only authored code, fixtures and reviewed
summaries are committed. No new private input needs retaining.

## Steward validators

All 43 affected rows pass in 307.76 s (408.1 s summed over two workers) with
canonical `private-env.sh`, the cache, two jobs and no registry mutants. They
ran on the final tree; its compiled inputs are those of `13553cab`, the last
commit that changes compiled sources. The twelve rows marked "yes" compile the
GFx layer and were also 005's lane rows. The other 31 are selected because
they compile `native/world/world_rt.c` or `native/world/parts/combat.c`, each
of which gains one or three added lines. No registry mutant target changed.

| Validator | Cases/contracts, zero mismatches | Wall seconds | Lane row |
|---|---:|---:|---|
| validate_app_polish1 | 752 | 18.7 | yes |
| validate_app_polish2 | 1028 | 3.4 | yes |
| validate_app_polish4 | 10485 | 40.3 | yes |
| validate_app_polish7 | 5120 | 1.6 | yes |
| validate_app_polish9 | 4668 | 4.6 | yes |
| validate_audio_callers | 5528 | 5.1 | yes |
| validate_audio_domains | 2544 | 21.8 | yes |
| validate_audio_items | 3000 | 2.5 | yes |
| validate_gfx3 | 6 skill / 18 window + loader/menu | 5.0 | yes |
| validate_map_polish | 876 | 0.6 | yes |
| validate_movement | 6614 | 46.2 |  |
| validate_render_effects | 660 | 0.8 |  |
| validate_render_effects10 | 154 | 0.3 |  |
| validate_render_effects11 | 176 | 0.2 |  |
| validate_render_effects12 | 64 | 0.3 |  |
| validate_render_effects13 | 180 | 0.4 |  |
| validate_render_effects14 | 660 | 1.0 |  |
| validate_render_effects15 | 509 | 0.7 |  |
| validate_render_effects16 | 424 | 3.8 | yes |
| validate_render_effects17 | 618 | 7.7 |  |
| validate_render_effects18 | 540 | 1.5 |  |
| validate_render_effects19 | 400 | 1.0 |  |
| validate_render_effects20 | 148 | 0.4 |  |
| validate_render_effects21 | 267 | 0.5 |  |
| validate_render_effects22 | 202 | 8.4 |  |
| validate_render_effects23 | 1174 | 10.1 |  |
| validate_render_effects24 | 226 | 2.4 |  |
| validate_render_effects25 | 202 | 9.3 |  |
| validate_render_effects26 | 348 | 10.1 |  |
| validate_render_effects27 | 424 | 1.2 |  |
| validate_render_effects3 | 720 | 0.7 |  |
| validate_render_effects30 | 452 | 1.0 |  |
| validate_render_effects31 | 66051 | 168.4 |  |
| validate_render_effects32 | 1723 | 0.8 |  |
| validate_render_effects4 | 1920 | 4.5 |  |
| validate_render_effects5 | 1190 | 3.2 |  |
| validate_render_effects6 | 1000 | 0.9 |  |
| validate_render_effects7 | 596 | 1.3 |  |
| validate_render_effects9 | 304 | 0.9 |  |
| validate_world_particle_consumers | 900 | 0.6 |  |
| validate_worlds_fog | 4044 | 14.2 | yes |
| validate_worlds_l | 1260 | 0.9 |  |
| validate_worlds_m | 1080 | 0.8 |  |

Steward validators: validate_app_polish1,validate_app_polish2,validate_app_polish4,validate_app_polish7,validate_app_polish9,validate_audio_callers,validate_audio_domains,validate_audio_items,validate_gfx3,validate_map_polish,validate_movement,validate_render_effects,validate_render_effects10,validate_render_effects11,validate_render_effects12,validate_render_effects13,validate_render_effects14,validate_render_effects15,validate_render_effects16,validate_render_effects17,validate_render_effects18,validate_render_effects19,validate_render_effects20,validate_render_effects21,validate_render_effects22,validate_render_effects23,validate_render_effects24,validate_render_effects25,validate_render_effects26,validate_render_effects27,validate_render_effects3,validate_render_effects30,validate_render_effects31,validate_render_effects32,validate_render_effects4,validate_render_effects5,validate_render_effects6,validate_render_effects7,validate_render_effects9,validate_world_particle_consumers,validate_worlds_fog,validate_worlds_l,validate_worlds_m

Required environment: source the canonical `private-env.sh` from the repository
root (`MU_RECOVERY_INTEGRATION=1` and its pinned capture/data variables). No
additional private input or mutant switch is required.

## Publication, checkpoints and cleanup

Checkpoints `f560caf1`, `8e0c9713`, `13553cab` and `e15e9fa9` pushed the WIP
history with done / left / next steps. Compiled runtime inputs are unchanged
after `13553cab`; later commits add scripts, tests' pinned results, ledgers
and documentation. The ready-prs line is written after the final push and PR
creation, then no further push. Cleanup removes this lane's scratch, renders,
reports, build outputs, worktree and local branch. The remote branch stays for
the steward. Ready for steward.
