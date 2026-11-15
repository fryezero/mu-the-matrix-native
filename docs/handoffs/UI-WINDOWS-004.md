# UI-WINDOWS-004

## Delivered scope

Nine additional movies open through ten original NPC manager slots in the
offline native client. All providers and English labels are authored empty
fixtures. No item, recipe, catalogue, transaction or authoritative state is
implemented. Started from PR #391 head c3b29c40, merged main 4babc900 at
d14d3a67, then merged the completed #391 main a95880c4 at
36aabe4d88fa0905266a4e6328d86ece5506941d. The latter merge changes no compiled
input. The lane source and checks below refer to that integrated commit;
later commits finish documentation only.

The [research](../research/client-ui-windows.md) and
[134-row survey](../research/ui-window-route-survey.csv) distinguish route
proof, provider completeness and state refusals. Of the 118 rows unresolved
on entry:

| Classification | Rows |
|---|---:|
| Route proved + empty provider complete | 9 |
| Route proved + provider missing | 17 |
| State-dependent, refused | 30 |
| No route found by this bounded scan | 62 |

The inherited PlayGuide key/menu binding is also withdrawn. The fresh
registry proves PlayGuide is +0x1f0, while getter 0x00b3b39e, Ctrl+T and
menu 22 select EventMapEntranceUI +0x2ac. The previous comparison checked
the caller's toggle/sound but did not join its getter to the movie. No event
entry or external guide content replaces it. Thus the historical survey
changes from 16 bound / 118 unresolved to 24 bound / 110 unresolved.
The native registry rises 48 entries / 47 filenames -> 57 / 56, including
optional PlayGuide, which now has no proved original binding.

| Movie | Manager slot | Existing original NPC presentation route |
|---|---|---|
| GuardianMix | +0x20c | 7, open |
| MixAttributeScalp | +0xb4 | 8/9, flag then open, repeated close-all |
| HarmonyMix | +0x264 / +0x260 | 0x11 / 0x13, open |
| SocketMix | +0x208 | 0x17, open |
| MixSel | +0xac | 0x18 / 0x26 / 0x27, selector method boundary |
| ExchangeLuckCoin | +0x270 | 0x20, open |
| ElementalMix | +0x204 | 0x29, open |
| MuunExchange | +0x1ac | 0x33, toggle |
| RuudShopFrame | +0x1fc | 0x35, open |

One table drives all ten manager slots. The two Harmony registrations share
one empty first-page presentation. No original option/refining recipes or
page equivalence is claimed. The selector's buttons and all item, exchange,
buy, recipe and page requests are disabled or empty and also reject forged
callbacks. Close, Esc, readiness and NPC teardown are checked. Shared files
receive added lines; owned UI enum/registry rows and two prior test hosts
have the necessary small edits. The old four-window host keeps its original
four-window denominator, with the new nine covered separately.

## Static sweep

The reproducible pinned scan is `scripts/survey_ui_routes.py`. The text/data
pins are the same as UI-WINDOWS-003 and recorded in the research document.
It enumerates 137 registrations, 103 direct toggle calls, 1,042 lifecycle
sites/candidates, 415 manager-window receiver joins and 627 unresolved
receivers. It separately records 176 legacy manager calls with 47 recovered
immediate IDs and every entry of the 23-constant main-menu table.

The [service](../research/ui-window-services.csv),
[legacy](../research/ui-window-legacy.csv) and
[menu](../research/ui-window-menus.csv) ledgers retain addresses and candidate
status. They contain no captured bytes or movie content. A manager join
starts at the actual getter and stops at branches or unrelated calls.
The synthetic negative control proves an unrelated same-offset object does
not join. Unknown receivers, dynamic IDs, other indirect encodings,
uncaptured vtables and upstream triggers remain unresolved. These are scan
counts, not a claim that every indirect route in the client has been proved.
A no-route-found row is a bounded scan result, not proof of absence.

## Controller and sound checks

Thirteen eligible presentation result paths execute the original owner
0x01280659 through the existing instruction harness and compare against the
compiled production adapter. Manager/window services are recording stubs;
selector methods are bounded at their presentation entry. Their recipe and
transaction internals are not executed. No packet parser, service path or
new acquisition is added.

The original sequence is close-all, controller open/toggle, then sound 25
and sound 28. The graphical NPC host opts into that order, including repeated
close-all for 8/9. The legacy headless recording callback contract remains
available. Existing sound counters and sites keep their core owner; the
new controllers emit no extra sound. Core OTHER-kind `not_played` accounting
is historical and is not a census of these new visible movie adapters.

The synthetic and actual-movie hosts each refuse 153 forged callback/window
combinations. Hero values, held item, potion count, foreign handler counters
and extra sound count remain unchanged. Real movie readback checks empty
providers, disabled actions and authored titles. Missing readiness refuses;
Muun toggles while ordinary open routes remain open on repeated calls.

All eight distinct compiled mutants are caught: wrong slot, wrong movie,
lost toggle, missing readiness, forged action acceptance, lost close,
enabled exchange and sound before open. The passing normal host and original
route test run in the same final command. Four tests pass in 20.86 s.
Earlier focused private UI/census regression: 19 tests, 17 passed, two optional
mutant classes skipped, zero failures/errors, 22.11 s.

## Native journeys and captures

Actual worktree `native/build/mu-world`, headless GL with the real exported
movies, canonical private environment, no audio, fixed GFx clock,
single-buffer and public demo names. Framebuffer 1024x768. No installed app
was launched, packaged or replaced. Each of nine runs uses an authored NPC
fixture beside the demo hero, talk at frame 2 and close at frame 24. There
are 32 frames per run; frame 16 proves the open view and frame 31 proves
closure. No cast, pickup or travel action is scripted.

All nine layouts were inspected, as were their nine close frames. All are
fully opaque. The close PNGs are byte-identical, confirming the same final
closed scene. Nine completed journeys total 48.50 s. Private commands and
reports were under `~/Documents/MTM/mu-mac-tools/native/scratch/ui-windows-004/`;
proof frames were under the corresponding `renders/ui-windows-004/`.
They are removed during cleanup, never committed.

| Movie | Inspected open-frame SHA-256 |
|---|---|
| ElementalMix | 7bf7496e2730a7248ce82eb96af8732e424b4595f1d998023c195fc8a0dbe91e |
| ExchangeLuckCoin | ba64368495377f6e6952c4c0bbcaddcf28c2bbbdecc1106a0bf9cd906004962a |
| GuardianMix | d8e2bff576428fb532bdbad99b88097f5814009bee0921652a6cb840ca5aa839 |
| HarmonyMix | 2a1de15c10e13fbc5a61c0da4e809695b9a3910924e2acf3cb2adaceb76260fe |
| MixAttributeScalp | a4a610528ae5c41372c9f79e541e802f6952a8a7514f65b79784dfbe64d3d350 |
| MixSel | 0841811bc32b16f211303d56bde9a64a628b0a0518eea3c0fa696c9e2b5ad390 |
| MuunExchange | a289864ae6f9ad54f9a2e883313319a78a5b9c207e48898f1e12338c23db7c81 |
| RuudShopFrame | b18ebfdefccde2ca167af70ef09d44de1bc580966068dd41be72cd2ca82f2e72 |
| SocketMix | a736c7d94ad99d7413fefc0b9e31c4847ca38823d8dbe82bef02cbbb4930ef05 |

All nine closed-frame SHA-256: `2b42dc20b07424cd923ca2f5f1e992aff1d2dc7561e973f9918d5d220bf15659`.

## Default identity and binary provenance

The pre-edit world was explicitly built in the owned worktree at d14d3a67,
then preserved privately. No main checkout build or second baseline render.
Before SHA-256:
75ca1d88bb09c47a9e41358cceaa49bedf9a014039237563e4c0c3cd2435cf09.
The explicitly rebuilt integrated world has after SHA-256:
98ebed1527e6f36566b38dc5230994a499116536f63b3f580a013572d0c06c3f.
They differ, so the sweep is not a binary self-comparison. The final world
freshness command passes in 0.29 s. The #391 merge adds no compiled delta.

One default sweep covers 14 October-22 maps and 32 DATA-ACQ-002 maps,
640x400, no draw_all or live_time. Before command wall 93.59 s,
27.07 + 66.44 s rendering; after 78.42 s, 18.87 + 59.50 s rendering.
All 92 PNGs, 92 dumps and 46 reports are identical. Only report binary/output
paths are normalised. Pixels and dumps compare byte for byte. This does not
establish original-image equivalence, UI pixel parity or performance acceptance.

## Checks and steward validators

Heavy work uses nice -n 10 and one heavy job at a time. Initial builds use
-j4; after twenty minutes of resource waits the common brief's -j2 fallback
is used. Python and validator pools use two jobs. No full gate, hosted
workflow, installed app journey or app-packaging test runs in this lane.

| Check | Result | Wall seconds |
|---|---|---:|
| Root build after final source | pass | 14.19 |
| Explicit client/world build | pass | 13.33 |
| Final world freshness | pass | 0.29 |
| Focused private UI/census regressions | 17 passed, two optional skips | 22.11 |
| Final normal + original + eight compiled mutants | four tests pass, all mutants caught | 20.86 |
| Affected portable selection, app packaging excluded | 177 work items; 1,584 tests, 1,281 passed / 303 optional skips, zero failures/errors | 485.28 command / 394.9 execution |
| Reduced private consumer checks | 22/22 pass, including 5,803 original UI audio comparisons and offline NPC consumers | 36.55 |
| Nine actual native journeys | 288 frames, 18 inspected proof frames | 48.50 |
| Default before / after sweep | 230 identities match | 93.59 / 78.42 |

## Limits and next

Help's indirect original opener, Home activation, the separate fifth-tree
inventory and event inventory remain refused. There is no guessed Help key
or menu. EventMapEntranceUI remains state-dependent and no longer masquerades
as PlayGuide. Macro timing/configuration, hunt history, matching catalogues,
storage expansion authority, guide content, transactions, stat formulas and
power features remain excluded. Other sizes, full localisation and original
class/world eligibility are unproved. Remaining rows keep their individual
missing-provider or route reasons. Best small-provider leads are documented,
including MiniGameHelpWindow content, DivideWindow item/count owner and
GuildCreateFrame emblem/form owner, rather than invented bindings.

No original/live client, protection module, live memory, owner Wine app,
staged Wine app or installed Native Preview was touched. No README work,
subagent or hosted workflow. Only authored code, synthetic fixtures and
reviewed address summaries are committed. No new private input needs retaining.

## WIP

Done: implemented scope, original comparison, eight mutants, static census,
all nine native layouts and the default identity sweep pass. Main through
#391 is integrated, with no compiled input changes.
Left: selected validator execution, staged audit, final status/PR publication
and cleanup. Portable and reduced private consumers pass. The 55.84 s selector
chooses 22 rows, including the native-library seed-header IR fallbacks;
none is dropped. Their no-mutant, cached, two-job run is in progress.

8d reduced: the portable affected selection has 177 work items, over forty
native modules. The changed UI hosts, census and original instruction checks
ran privately above. UI-WINDOWS-001, UI audio, and the existing NPC Session,
Windows and offline game-data class ran as 22 additional private consumer
tests in 36.55 s. The old NPC validator's unchanged mutants were not rerun.
The affected portable command excludes only native/tests/test_native_app.py,
per the lane's explicit app-packaging prohibition. No full gate ran.
Next step: inspect the affected run, run its selected validators with no
mutants, then replace this WIP section with the completed check ledger.
Checkpoint pushes ed6c81b9 and 6c40aed5 preserve the earlier done / left / next
state. No ready-prs entry exists yet. Stop by 02:30 on 2026-11-15; push WIP
by 02:15 if final verification remains unfinished.
