# UI-WINDOWS-005

## Delivered scope

Four additional original movies have empty, authored presentation providers:
PersonalShop, ArtifactFrame, MUMix and DuelWatch. Base main is `6900914e`.
Initial four-window UI/controller source is `c4cbe860`; the test-only layout
correction is `355f89bb`. Main df57ab8b, batch 115, merges cleanly at
`340db5b3a9592308d8bd218859a35d542fdb6616`. The final parent/scanner repair is
`009375ee`, with final scanner-store controls at `de4765cd`. Main 8844d3e9,
batch 116, merges cleanly at final compiled source
`db6b04508badab6785c0c0347a1c3dea0c2ba913`. Neither merge changes a UI controller.
The integration refreshes below identify imported compiled inputs separately.
The [research](../research/client-ui-windows.md),
[provider ledger](../research/ui-window-provider-groups.csv),
[route survey](../research/ui-window-route-survey.csv) and
[intermediate-call ledger](../research/ui-window-indirect.csv) retain the
per-row evidence and refusals. Registry entries rise 57 -> 61 and distinct
filenames 56 -> 60. These counts are not a client-completion percentage.

| Classification of the original 118 rows | Before | After |
|---|---:|---:|
| Route proved, empty provider complete | 9 | 13 |
| Route proved, provider missing | 17 | 33 |
| State-dependent, refused | 30 | 30 |
| No route found by the bounded searches | 62 | 42 |

Of the 17 entry provider gaps, three are admitted and fourteen retain their
specific missing owners. The second sweep proves routes for 20 entry
no-route rows; DuelWatch is admitted and nineteen remain provider-missing.
The historical 134-row survey changes 24 -> 28 bound, 110 -> 106 unresolved.
The separately withdrawn PlayGuide row remains unbound and outside the
118-row entry denominator.

| Movie | Original route | Fixture and refusal |
|---|---|---|
| PersonalShop | NPC result 0x30, +0x164 toggle; original menu 7 | Three empty catalogues, local shop/item tabs; search/community/item/purchase requests refuse |
| ArtifactFrame | Inventory onClickArtifact, +0x280 toggle at 0x00b97edf | Empty hex board and option tree, one page; item/bonus/page/expand operations refuse |
| MUMix | Goblin onClickGoblinMenu -> 0x00bd0a4b -> 0x00bd06ae, choice value 1; +0x290 open at 0x00bd07ff, then selector close | Empty category tree/default page; recipes, materials, chance, currency and results absent |
| DuelWatch | NPC result 0x21 -> method 0x00b54793; +0xe0 open tail 0x00b548ef..0x00b548f7 | Four empty match rows, all watch buttons disabled; no match source or entry |

The Goblin controller had routed value 1 to the older mix view. The original
selects MUMix for 1 and the older view for 0. The production callback now
preserves that split. Authored button labels identify the two destinations;
they are not inferred from display order. The existing legacy item-service
regression changes its trigger to original value 0 and retains all its
transaction assertions. No new transaction implementation is added.

## Static sweep and provider groups

The 17-row ledger groups two catalogues, six item/detail views, one mix view,
two forms, three HUD/notices, one account shop, one guide and one recovery
list. It names the absent layout/data/label/list/source owner for every row.
Reviewed movie methods alone do not supply an item, server reply or request
lifecycle. No sound-only deficit was established and no generic sound was
invented to complete a row.

The pinned second pass starts at 6,708 direct manager calls, checks captured
absolute function-pointer and adjacent register-immediate roots, follows
branches and saved receiver identities, resolves register-held virtual
methods, and follows one intermediate UI-controller method. Both `this` and
the vtable must belong to the same window. It finds 482 joined lifecycle
sites, 67 additional to 004, and zero extra manager roots through its bounded
indirect-root encodings. The final ledger reproduces exactly in 8.35 s. Eight
provenance controls pass in 0.10 s. Partial register, exchanged/implicit and
overlapping frame writes invalidate identities; unknown
memory aliases discard saved locals. Proved object fields preserve disjoint
frame saves. The stricter pass withdraws a tentative ResistPopup opener and
two close joins; the discarded opener stays no-route. Earlier 485/70 and
21-entry-route counts are superseded.

Search limits are 1,024 bytes and 240 steps per explored span, 2,048 states
per manager root, and one intermediate method. Unknown writes kill facts;
calls clobber volatile registers; different branch paths do not share facts.
Synthetic controls cover register calls, branch saves, unrelated/clobbered
receivers, intermediate methods and captured function-pointer roots.
Dynamic table/message IDs, untyped callbacks, other root encodings and
uncaptured function pointers remain unresolved. No route-found result is
proof of an upstream key or permission to execute its state owner.

The original text/data pins are unchanged and recorded in the research.
No client bytes, movie content, original records or screenshots are committed.

## Controller, sound and mutant checks

One production route table preserves open versus toggle, readiness refusal,
Close/Esc and NPC teardown. Exclusive callback handling runs before foreign
NPC/item/social/command owners. Each synthetic and real-movie host refuses
88 forged callback/window combinations; hero, held-item and potion state
remain unchanged, with no foreign action delivery or extra controller sound.
Malformed tab values refuse. Real movie readback checks empty providers,
button state, local tab visibility, titles and the MUMix default page.

Instruction comparisons retain the original NPC close-all -> controller ->
sound 25 -> sound 28 order for PersonalShop and DuelWatch. Menu 7 uses the
existing common sound-25 site 0x00c716f6. Artifact's callback and the MUMix
opener/selector-close tail add no direct sound; unowned nested GFx sounds
remain outside the claim. No audio site outside UI controllers changes.

Twelve distinct compiled mutants are caught: wrong slot, wrong movie,
wrong open kind, missing readiness, lost close, accepting forged actions,
hidden-parent opening, invented sound, enabled watch, disabled local tabs,
wrong Goblin branch and malformed-parent fallthrough. The first mirror attempt followed symlinked normal
includes and is not passing evidence. The corrected nine-mutant run passes
in 27.35 s including normal/original tests. A native click then exposed
that search-disable also disabled tabs; the repair's separate mutant passes
in 4.76 s. The MUMix branch mutant and fifteen legacy consumers pass in
2.43 s. The final fallthrough mutant passes in 1.32 s. Twelve hidden/malformed-parent
controls run in each synthetic and real host. The two audit controls first
reproduce both failures in 2.08 s; after repair the six focused checks pass
in 1.75 s. Old unchanged mutants are not rerun. No registry mutant target changed.

## Native journeys and proof

Actual worktree native/build/mu-world, canonical private environment, real
read-only exported movies, headless window framebuffer, no audio, fixed GFx
clock, single buffering, public demo names and lane-local settings. No app
bundle or installed-app journey. Four completed journeys total 176 frames
and ten inspected 1024x768 proof frames; all are fully opaque.
PersonalShop opens via NPC result 0x30, changes to its empty Items tab and
closes. Inventory's actual Artifact button opens the empty board; Esc closes
it and reveals the existing bag. NPC result 0x21 opens DuelWatch, then closes.
NPC result 3 opens the Goblin selector; its value-1 button opens MUMix and
closes the selector; NPC teardown closes MUMix. No cast, pickup or travel
is scripted. Final integrated journey walls are 19.21 s for the first three and 6.02 s
for MUMix. All ten frames match the earlier inspected proofs byte for byte. Earlier probes and clipped-label captures are not final proof.

| Inspected proof frame | SHA-256 |
|---|---|
| PersonalShop-final/frame-0016.png | d6c50c6f1ede183bf5a6b20a20f37463f61647759b5aae73be80d3ee29e230e5 |
| PersonalShop-final/frame-0032.png | 171983d56d6fd84d23ce98b43508ef0b1af90689e705dc0ec148af5fa59bcc5a |
| PersonalShop-final/frame-0047.png | c1265db328fa57fe4282b5a5b001c6c3f311e9da081c5636f7a6d6c0fa127220 |
| DuelWatch-final/frame-0016.png | c7a9352c5f362730e998190f4af29ef46179755f9886e4ecd92735dbfa559995 |
| DuelWatch-final/frame-0031.png | f8d69a98d83a2a42a7c0491eacbd7278b05d9ca6525288587fceafd881382f68 |
| ArtifactFrame-final/frame-0016.png | f1040374b12af0c77b96804ff3294e8fee061d01b8192d5fdbf532fd5e7d7233 |
| ArtifactFrame-final/frame-0031.png | c057fe41944321dcedf1b2238819dc47cfe847af96e04584a593f16acec46f07 |
| MUMix-final/frame-0016.png | 9d35ade5dab230237b4941df59d277e03ff9872f084ef26b7b89bd9bd4c49e36 |
| MUMix-final/frame-0032.png | 7f097cdf838495ae41ebd795eff95521eb87ce820f89559334dd32faa1df298f |
| MUMix-final/frame-0063.png | 71ac7a57dd518bf279802c1537b7551c35687af77eacd693daaaeda49c245a59 |


Reproduction uses `--headless --backend gl --no-audio --class 1 --tile 140,130
--width 1024 --height 768 --every 16 --hero-name "Demo Knight" --no-items`,
canonical game/objects/gfx paths and `MU_GFX_TEST_CLOCK=1`,
`MU_GFX_SINGLE_BUFFER=1`, `MU_GFX_PUBLIC_DEMO=1`. Use lane-local settings.
The authored placement is `actor 251 140 131 6 label Demo Keeper`; each NPC
fixture is `talk 251 RESULT`, with decimal results below.

| Journey | Frames / result | Input scripts |
|---|---|---|
| PersonalShop | 48 / 48 | NPC `2:talk:Demo Keeper 40:close`; mouse `20:ldown:453,93 21:lup:453,93` |
| DuelWatch | 32 / 33 | NPC `2:talk:Demo Keeper 24:close` |
| ArtifactFrame | 32 / none | `--gfx-open inventory`; `4:ldown:747,348 5:lup:747,348 24:key:27` |
| MUMix | 64 / 3 | NPC `2:talk:Demo Keeper 56:close`; mouse `20:ldown:507,266 21:lup:507,266` |

## Default identity and binary provenance

The baseline was explicitly built in this owned worktree at untouched main,
then preserved privately. No build in the main checkout and no installed
app. Baseline root/world builds take 26.01 / 3.89 s. Before binary SHA-256:
`1a7b20b52387fb7010574d45db4a7e99415ee3b06c7110da28bdc2877c25e484`.

Final integrated root/world builds take 23.18 / 6.34 s. An explicit fresh
world check immediately before the sweep takes 0.39 s. Final after SHA-256:
`3eabc633b0def6f904e3f07a7ae1bd31c830497a12efe77b72688915c6ccddf4`.
It differs from the genuine baseline binary. All 230 artifacts are identical:
92 PNGs, 92 binary dumps and 46 reports. Final after-only walls are 23.45 s
for October-22 and 55.02 s for DATA-ACQ-002, command wall 78.71 s. The
baseline resume reports 0.0 s: no successful before map is rerendered.

The pre-integration four-window binary
`94924d0f14f2d0ffb35d928fabc1b74ac7c0f9191bbcdd7c778d0e561edd2bf7`
also passes all 230 identities (after renders 16.05 / 45.52 s). Main changes
compiled world inputs afterward, so only the after renders are repeated on
the final integrated binary.

One successful default baseline per map covers 14 October-22 and 32
DATA-ACQ-002 maps, 640x400, no draw_all/live_time. The 32-map before run takes
50.58 s. The first October-22 command had an obsolete input path and
produced no usable baseline. After repairing it, seven maps completed before
a resource stop; only the seven unfinished maps were resumed. No successful
baseline map is rerendered. Identity normalizes output paths in reports only;
PNG pixels and binary dumps compare byte for byte. This is native regression
identity, not original-image equivalence or performance acceptance.

## Checks and wall times

| Check | Result | Wall seconds |
|---|---|---:|
| Final root / explicit world build | Pass at db6b0450 | 23.18 / 6.34 |
| Final world freshness check | Same final binary; before and after hashes recorded | 0.39 |
| Final portable, 196 selected work items | 2024 tests: 1650 passed / 374 skipped, zero failures/errors | 610.39 including selection; 477.8 execution |
| Final private, 8d reduced, 14 modules | 85 tests: 82 passed / 3 optional mutant classes skipped | 516.27 |
| Audit negative controls before repair | Both failures reproduced | 2.08 |
| Focused controls after parent/partial-write repair | Six pass | 1.75 |
| Final synthetic provenance / complete ledger reproduction | Eight pass / all 482 rows identical | 0.10 / 8.35 |
| Corrected initial nine compiled mutants + normal/original checks | All caught / pass | 27.35 |
| Disabled local-tab compiled mutant | Caught | 4.76 |
| Wrong Goblin branch mutant + fifteen legacy consumers | Caught / 16 tests pass | 2.43 |
| Final parent-fallthrough compiled mutant | Caught; twelve distinct mutants total | 1.32 |
| Initial twelve lane validators | Twelve pass at c4cbe860 | 123.74 |
| First main integration validators | 94 pass at 340db5b3 | 3422.95 |
| Final selected validators | 76 pass at db6b0450 | 1230.57 |
| Final native journeys | Four movies, 176 frames, ten opaque inspected proofs | 19.21 + 6.02 |
| Final default identity | 230 identical artifacts; same preserved baseline | 78.71 |
| Final staged repository audit | 2346 staged files, zero rejected | 52.01 |
| Final four documentation consumers | 36 tests: 35 passed / 1 skipped | 11.70 |

8d reduced: the final affected selection contains 180 native work items, above the
forty-item cap. The reduced private run uses fourteen changed modules and
direct UI consumers. Changed/new private modules and relevant UI/audio/layout
consumers run from the repository root with canonical private-env.sh.
The portable runner uses the normal affected selection and excludes only
native/tests/test_native_app.py, as required. Its earlier three-window run
was interrupted when MUMix was recovered; only the complete four-window run
is reported as passing. No full gate or hosted workflow runs in this lane.
Heavy commands use nice -n 10, initial make -j4 and at most two Python workers, one
heavy lane command at a time. After over twenty minutes of accumulated
resource deferrals the brief's -j2 fallback applies, with a lane-local make
shim enforcing two build jobs. Memory remains above 25%; no quiet-machine
performance claim is made. Resource waits and the baseline stop are noted.

The private layout matrix initially reports the extra child movie 44 at all
seventeen size/backing-scale points. A host compiled from unchanged main
6900914e reproduces inventory auto-opening that bag in 5.02 s. The stale
exact-set expectation predates UI-WINDOWS-003. It now explicitly requires
BAG and applies the existing bounds checks to it; no geometry assertion is
removed. The initial 55-test private command takes 124.35 s; the repaired
17-point matrix passes in 45.50 s and its portable module in 1.30 s. At that repair only the failed matrix and its portable module are
rerun; the final merge-private run later covers the matrix again.


The fourteen final private modules, with `PYTHONPATH=native/tests`, are
`native.tests.test_actor_plain`, `native.tests.test_audio_kubera`,
`native.tests.test_audio_monsters`, `native.tests.test_muun_riding`,
`native.tests.test_muun_secondary`, `native.tests.test_muun_special`,
`native.tests.test_render_effects32`, `native.tests.test_ui_indirect`,
`native.tests.test_ui_windows5`, `native.tests.test_ui_windows4`,
`native.tests.test_ui_windows3`, `native.tests.test_ui_route_survey`,
`native.tests.test_native_item_services` and `native.tests.test_app_polish9`.
The new mutant harness is `native.tests.test_ui_windows5.MutationSensitivity`,
opted in with `MU_UI_WINDOWS5_MUTANTS=1`; final separate repair runs filter
with `MU_UI_WINDOWS5_MUTANT_ONLY`. Unchanged Windows3/4 mutants stay off.

For the portable selection, the normal runner is retained with one owner-required
exclusion. The exact filter, from the root with `MU_RECOVERY_INTEGRATION=0`
and `MU_GATE_JOBS=2`, is:

```python
import sys
sys.path.insert(0, 'scripts')
import run_test_suites as runner
normal = runner.run_parallel
def without_packaging(suites, jobs, logdir, only=None):
    assert only is not None
    return normal(suites, jobs, logdir, set(only) - {'native/tests/test_native_app.py'})
runner.run_parallel = without_packaging
raise SystemExit(runner.main(['--affected-since', '355f89bb',
                             '--logs', 'verify-runs/ui-windows-005-portable-merge']))
```

## Limits and next

Fourteen of the original seventeen providers remain missing, as do nineteen
newly routed providers. The original thirty state-dependent rows stay
refused. Forty-two entry rows have no proved route, plus the separate
withdrawn PlayGuide. Help's original opener/F1, Home activation, separate
fifth-tree inventory and event-inventory openers remain refused. No guessed
binding. Macro timing/configuration, hunt history, matching catalogue,
storage authority, guide content, transactions, stat formulas and power
features remain excluded. Other sizes, localisation, exact original context
eligibility and visual equivalence remain unproved.

No original/live client, protected module, live memory, owner Wine app,
staged Wine app, installed Native Preview, Native Data refresh, README work,
subagent or hosted workflow. Only authored code, fixtures and reviewed
summaries are committed. No new private input needs retaining.

## Steward validators

The original 12-row lane run passes at `c4cbe860` in 123.74 s. The first
main integration selects 94 rows, all passing at `340db5b3` in 3422.95 s.
The final callback repair and batch 116 integration select 76 rows, all passing
at compiled source `db6b04508badab6785c0c0347a1c3dea0c2ba913` in 1230.57 s.
Forty of the earlier rows are refreshed and 36 newly selected rows pass;
54 earlier rows retain unchanged inputs. This is 130 distinct covered rows.
All runs use canonical private-env.sh, cache enabled, two jobs and no registry
mutants. The twelve lane rows are marked below; no registry mutant target changed.

| Validator | Cases/contracts, zero mismatches | Wall seconds | Last passing compiled source | Lane row |
|---|---:|---:|---|---|
| validate_actor_composites | 1427 | 14.8 | `db6b0450` |  |
| validate_actor_monsters | 1437 | 82.8 | `db6b0450` |  |
| validate_actor_plain | 21437 | 218.0 | `db6b0450` |  |
| validate_actor_recipes | 1669 | 133.3 | `db6b0450` |  |
| validate_app_polish1 | 752 | 48.2 | `db6b0450` | yes |
| validate_app_polish2 | 1028 | 4.8 | `db6b0450` | yes |
| validate_app_polish4 | 10485 | 43.8 | `db6b0450` | yes |
| validate_app_polish7 | 5120 | 2.3 | `db6b0450` | yes |
| validate_app_polish9 | 4668 | 6.6 | `db6b0450` | yes |
| validate_armour_cloak | 4448 | 61.1 | `340db5b3` |  |
| validate_audio_callers | 5528 | 8.3 | `db6b0450` | yes |
| validate_audio_charsel | 5968 | 5.0 | `db6b0450` |  |
| validate_audio_combat | 19548 | 40.3 | `db6b0450` |  |
| validate_audio_domains | 2544 | 35.7 | `db6b0450` | yes |
| validate_audio_events | 70980 | 7.3 | `db6b0450` |  |
| validate_audio_items | 3000 | 5.5 | `db6b0450` | yes |
| validate_audio_kubera | 1000 | 1.5 | `db6b0450` |  |
| validate_audio_monsters | 38315 | 20.6 | `db6b0450` |  |
| validate_audio_music | 4291 | 0.6 | `db6b0450` |  |
| validate_audio_objects | 4000 | 5.1 | `db6b0450` |  |
| validate_audio_objects4 | 10093 | 9.3 | `db6b0450` |  |
| validate_audio_ui | 5803 | 19.3 | `db6b0450` |  |
| validate_audio_voices | 2182 | 0.1 | `db6b0450` |  |
| validate_charsel_items | 8817 | 12.3 | `db6b0450` |  |
| validate_fidelity | 991 | 73.1 | `340db5b3` |  |
| validate_gfx3 | 6 skill / 18 window + loader/menu | 8.8 | `db6b0450` | yes |
| validate_helpers | 8667 | 285.2 | `340db5b3` |  |
| validate_icarus_c2 | 8400 | 32.3 | `db6b0450` |  |
| validate_inventory_fx | 8017 | 13.4 | `db6b0450` |  |
| validate_item_callers | 6013 | 1.2 | `db6b0450` |  |
| validate_item_carry | 114388 | 654.8 | `340db5b3` |  |
| validate_item_chains | 35406 | 158.8 | `340db5b3` |  |
| validate_item_cloak | 5694 | 169.6 | `340db5b3` |  |
| validate_item_clusters | 74292 | 80.5 | `340db5b3` |  |
| validate_item_continuation | 25772 | 112.5 | `340db5b3` |  |
| validate_item_coverage | 31724 | 109.8 | `340db5b3` |  |
| validate_item_cycle | 6936 | 53.7 | `340db5b3` |  |
| validate_item_derived | 36252 | 305.3 | `340db5b3` |  |
| validate_item_direct_bodies | 15352 | 12.7 | `340db5b3` |  |
| validate_item_expansion | 52172 | 78.4 | `340db5b3` |  |
| validate_item_gear | 25256 | 101.3 | `340db5b3` |  |
| validate_item_groups | 4824 | 30.8 | `340db5b3` |  |
| validate_item_helper_groups | 6432 | 44.6 | `340db5b3` |  |
| validate_item_hiddenmesh | 116281 | 516.3 | `340db5b3` |  |
| validate_item_named | 20057 | 5.5 | `340db5b3` |  |
| validate_item_next | 14992 | 274.2 | `340db5b3` |  |
| validate_item_other_bodies | 24084 | 133.3 | `340db5b3` |  |
| validate_item_ownerfx | 14964 | 191.4 | `340db5b3` |  |
| validate_item_predraw | 42540 | 394.4 | `340db5b3` |  |
| validate_item_product | 2874 | 159.0 | `340db5b3` |  |
| validate_item_quality | 28080 | 279.9 | `340db5b3` |  |
| validate_item_ranked | 17736 | 110.5 | `340db5b3` |  |
| validate_item_read_programs | 5352 | 22.7 | `340db5b3` |  |
| validate_item_scalars | 26274 | 112.5 | `340db5b3` |  |
| validate_item_types | 135176 | 43.2 | `340db5b3` |  |
| validate_item_wings_next | 33622 | 128.0 | `340db5b3` |  |
| validate_items_ui | 8517 | 21.7 | `db6b0450` |  |
| validate_map_polish | 876 | 0.5 | `db6b0450` | yes |
| validate_meshdraw | 14619 | 79.5 | `db6b0450` |  |
| validate_model_edge | 954 | 154.9 | `db6b0450` |  |
| validate_model_light | 1433 | 7.6 | `db6b0450` |  |
| validate_mount_visuals | 8400 | 11.3 | `340db5b3` |  |
| validate_movement | 6614 | 72.1 | `db6b0450` |  |
| validate_muun_passes | 1361 | 1.0 | `340db5b3` |  |
| validate_muun_riding | 890 | 0.6 | `340db5b3` |  |
| validate_muun_secondary | 873 | 0.5 | `340db5b3` |  |
| validate_muun_special | 452 | 0.8 | `340db5b3` |  |
| validate_muun_visual | 912 | 1.2 | `340db5b3` |  |
| validate_npc_cloak | 2619 | 42.2 | `340db5b3` |  |
| validate_path | 4719 | 43.4 | `db6b0450` |  |
| validate_pets | 1062 | 166.9 | `340db5b3` |  |
| validate_raven | 4000 | 163.5 | `340db5b3` |  |
| validate_render_effects10 | 154 | 0.5 | `340db5b3` |  |
| validate_render_effects11 | 176 | 0.4 | `340db5b3` |  |
| validate_render_effects12 | 64 | 0.4 | `340db5b3` |  |
| validate_render_effects13 | 180 | 0.7 | `340db5b3` |  |
| validate_render_effects14 | 660 | 1.8 | `340db5b3` |  |
| validate_render_effects15 | 509 | 1.3 | `340db5b3` |  |
| validate_render_effects16 | 424 | 4.2 | `db6b0450` | yes |
| validate_render_effects17 | 618 | 13.1 | `db6b0450` |  |
| validate_render_effects18 | 540 | 1.6 | `db6b0450` |  |
| validate_render_effects19 | 400 | 1.2 | `db6b0450` |  |
| validate_render_effects20 | 148 | 0.4 | `340db5b3` |  |
| validate_render_effects21 | 267 | 0.6 | `340db5b3` |  |
| validate_render_effects22 | 202 | 9.4 | `340db5b3` |  |
| validate_render_effects23 | 1174 | 9.7 | `340db5b3` |  |
| validate_render_effects24 | 226 | 2.9 | `db6b0450` |  |
| validate_render_effects25 | 202 | 13.4 | `db6b0450` |  |
| validate_render_effects26 | 348 | 15.3 | `db6b0450` |  |
| validate_render_effects27 | 424 | 2.0 | `340db5b3` |  |
| validate_render_effects28 | 630 | 3.5 | `db6b0450` |  |
| validate_render_effects31 | 66051 | 296.4 | `db6b0450` |  |
| validate_render_effects32 | 1723 | 1.0 | `340db5b3` |  |
| validate_render_effects5 | 1190 | 4.6 | `340db5b3` |  |
| validate_render_effects7 | 596 | 1.8 | `340db5b3` |  |
| validate_render_effects9 | 304 | 1.0 | `340db5b3` |  |
| validate_renderchar | 1706 | 40.1 | `340db5b3` |  |
| validate_session_party | 200 | 0.8 | `db6b0450` |  |
| validate_terrain | 583500 | 450.3 | `db6b0450` |  |
| validate_terrain_remaining | 2147 | 4.9 | `db6b0450` |  |
| validate_viewport_monsters | 1963 | 17.5 | `db6b0450` |  |
| validate_world_light_name | 304 | 0.5 | `db6b0450` |  |
| validate_world_tile_folder | 5700 | 55.8 | `db6b0450` |  |
| validate_worlds_121 | 4000 | 4.1 | `db6b0450` |  |
| validate_worlds_after3 | 10212 | 15.4 | `db6b0450` |  |
| validate_worlds_after4 | 9181 | 17.8 | `db6b0450` |  |
| validate_worlds_after6 | 7300 | 88.6 | `db6b0450` |  |
| validate_worlds_b | 4000 | 4.5 | `db6b0450` |  |
| validate_worlds_e | 4840 | 18.2 | `db6b0450` |  |
| validate_worlds_f | 1818 | 0.4 | `db6b0450` |  |
| validate_worlds_fog | 4044 | 11.0 | `db6b0450` | yes |
| validate_worlds_g | 6000 | 4.4 | `db6b0450` |  |
| validate_worlds_h | 6000 | 4.5 | `db6b0450` |  |
| validate_worlds_i | 6000 | 5.0 | `db6b0450` |  |
| validate_worlds_inner | 4000 | 3.6 | `db6b0450` |  |
| validate_worlds_inner2 | 5000 | 4.4 | `db6b0450` |  |
| validate_worlds_inner3 | 8000 | 8.6 | `db6b0450` |  |
| validate_worlds_inner4 | 8000 | 7.3 | `db6b0450` |  |
| validate_worlds_j | 6000 | 4.7 | `db6b0450` |  |
| validate_worlds_karutan | 3000 | 2.9 | `db6b0450` |  |
| validate_worlds_q | 11000 | 17.0 | `db6b0450` |  |
| validate_worlds_q2 | 4000 | 11.6 | `db6b0450` |  |
| validate_worlds_r2 | 9000 | 11.8 | `db6b0450` |  |
| validate_worlds_raklion | 3000 | 3.3 | `db6b0450` |  |
| validate_worlds_s | 11000 | 12.0 | `db6b0450` |  |
| validate_worlds_s2 | 10000 | 13.2 | `db6b0450` |  |
| validate_worlds_s3 | 22000 | 35.0 | `db6b0450` |  |
| validate_worlds_slots | 18999 | 30.4 | `db6b0450` |  |
| validate_worlds_slots2 | 33000 | 39.8 | `db6b0450` |  |
| validate_worlds_slots3 | 36000 | 38.9 | `db6b0450` |  |

Steward validators: validate_actor_composites,validate_actor_monsters,validate_actor_plain,validate_actor_recipes,validate_app_polish1,validate_app_polish2,validate_app_polish4,validate_app_polish7,validate_app_polish9,validate_armour_cloak,validate_audio_callers,validate_audio_charsel,validate_audio_combat,validate_audio_domains,validate_audio_events,validate_audio_items,validate_audio_kubera,validate_audio_monsters,validate_audio_music,validate_audio_objects,validate_audio_objects4,validate_audio_ui,validate_audio_voices,validate_charsel_items,validate_fidelity,validate_gfx3,validate_helpers,validate_icarus_c2,validate_inventory_fx,validate_item_callers,validate_item_carry,validate_item_chains,validate_item_cloak,validate_item_clusters,validate_item_continuation,validate_item_coverage,validate_item_cycle,validate_item_derived,validate_item_direct_bodies,validate_item_expansion,validate_item_gear,validate_item_groups,validate_item_helper_groups,validate_item_hiddenmesh,validate_item_named,validate_item_next,validate_item_other_bodies,validate_item_ownerfx,validate_item_predraw,validate_item_product,validate_item_quality,validate_item_ranked,validate_item_read_programs,validate_item_scalars,validate_item_types,validate_item_wings_next,validate_items_ui,validate_map_polish,validate_meshdraw,validate_model_edge,validate_model_light,validate_mount_visuals,validate_movement,validate_muun_passes,validate_muun_riding,validate_muun_secondary,validate_muun_special,validate_muun_visual,validate_npc_cloak,validate_path,validate_pets,validate_raven,validate_render_effects10,validate_render_effects11,validate_render_effects12,validate_render_effects13,validate_render_effects14,validate_render_effects15,validate_render_effects16,validate_render_effects17,validate_render_effects18,validate_render_effects19,validate_render_effects20,validate_render_effects21,validate_render_effects22,validate_render_effects23,validate_render_effects24,validate_render_effects25,validate_render_effects26,validate_render_effects27,validate_render_effects28,validate_render_effects31,validate_render_effects32,validate_render_effects5,validate_render_effects7,validate_render_effects9,validate_renderchar,validate_session_party,validate_terrain,validate_terrain_remaining,validate_viewport_monsters,validate_world_light_name,validate_world_tile_folder,validate_worlds_121,validate_worlds_after3,validate_worlds_after4,validate_worlds_after6,validate_worlds_b,validate_worlds_e,validate_worlds_f,validate_worlds_fog,validate_worlds_g,validate_worlds_h,validate_worlds_i,validate_worlds_inner,validate_worlds_inner2,validate_worlds_inner3,validate_worlds_inner4,validate_worlds_j,validate_worlds_karutan,validate_worlds_q,validate_worlds_q2,validate_worlds_r2,validate_worlds_raklion,validate_worlds_s,validate_worlds_s2,validate_worlds_s3,validate_worlds_slots,validate_worlds_slots2,validate_worlds_slots3

Required environment: source the canonical `private-env.sh` from the repository
root (`MU_RECOVERY_INTEGRATION=1` and its pinned capture/data variables).
No additional private input or mutant switch is required.

## Publication, checkpoints and cleanup

Checkpoints c9d56be4, 1c01db4a, 391ccd0b, c4cbe860, 014f1b49, 355f89bb,
91548b12, 5fada08f, b9c4a5d6, de4765cd and 15b7745f push the WIP history
with done / left / next steps. Latest main `8844d3e9` is integrated at `db6b0450`.
The twelve first validator checks refer to source c4cbe860. The layout-test
repair, final scanner controls and imported-main refreshes are recorded
separately. Compiled runtime inputs stay unchanged after `db6b0450`; the
final commits after `de4765cd` finish documentation and status only. The ready-prs line is written after final push/PR creation,
then no further push. Cleanup removes this lane's scratch, renders, reports,
build outputs, worktree and local branch. The remote branch stays for the
steward. Ready for steward.
