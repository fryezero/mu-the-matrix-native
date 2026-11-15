# AUDIO-006: whole monster sound owners and ownership groups

Branch `codex/audio-006`, started from main `8844d3e9` with AUDIO-005 and
RENDER-ACTORS-006 merged. Latest main `c5b9d5ca` is merged at `2ffecb3e`.
This is an offline verified fixture subset. Ready for steward.

## Census

Reproduce with `scripts/audio_caller_census.py --report <local>` and
`scripts/audio_owner_groups.py --report <local>`. The reviewed
[entry ledger](../research/audio-006-entry-groups.csv) preserves all 891 scoped
candidates, 546 unresolved + 279 class refusals + 66 class-use sites. Future
runs use this authored CSV without a deleted private before-report.
The 1,980 denominator is a syntactic E8-target scan, not a whole-program CFG.

| Owner bucket | AUDIO-005 entry | Integrated AUDIO-006 |
|---|---:|---:|
| UI | 51 | 53 |
| Hero/shared actions | 43 | 43 |
| Skills/effect timelines | 338 | 364 |
| Monsters/NPC voices | 848 | 848 |
| World objects/ambient | 135 | 137 |
| Items | 15 | 15 |
| Events/progression | 4 | 4 |
| Unresolved owner | 546 | 516 |
| Total | 1,980 | 1,980 |

Classified candidates rise **1,434 -> 1,464**, unresolved **546 -> 516**.
This lane identifies 26 exact shared-timeline and two registered UI lifecycle
sites. Incoming INNER-005 independently identifies two world sites in
`0x00e8d888`. All 30 are ownership classifications without new delivery gates.
The final latest-main baseline alone is 1,436 classified / 544 unresolved.
The 546 entry unresolved candidates occupy 359 prologue groups; proximity never
supplies semantic ownership or admission. The remaining 516 stay owner-unknown.

Enumerated play boundaries rise **411 -> 593**, through **182 new monster play
sites**. The separate two AUDIO-005 stop sites are unchanged. Existing complete
class methods rise 21 -> 32 of 40, with class sites 245 -> 427 of 524. Shared
sites count once across model/world aliases. These figures do not measure
whole-client audio completion.

## Wired and refused groups

| Entry class-refusal group | Sites | Result |
|---|---:|---|
| Scalar world/distance/conditional audio RNG | 182 | Admitted through eight sounding and three silent complete methods |
| Delegated owner/context | 47 | Four whole owners remain refused |
| Marker fields or other services | 47 | Three whole owners remain refused |
| Prior action and ordered stop | 3 | One whole owner remains refused |
| Missing native actor only | 0 | No AUDIO-005 whole-owner refusal had this sole cause |
| Existing class-use controllers | 66 | All remain unwired; target/buff/request/timing owner is absent |

The 279 class refusals partition **182 + 47 + 47 + 3**; 97 candidates in eight
owners remain refused. The exact blockers, ids and semantic owner evidence are
in [client-audio](../research/client-audio.md#audio-006-whole-owners-and-grouped-remainder-2026-11-15).
Unknown-id overlays are nine in unknown owners, eight in the recovered group,
four in marker/service owners and eleven in class-use controllers. These overlap
the primary blockers and cannot be added to the denominators.

| Complete sounding method | World | Sites |
|---|---|---:|
| `0x00e9e3d5` | 57, 58 | 28 |
| `0x00e92b75` | 63 | 21 |
| `0x00e30389` | 82 | 9 |
| `0x00dd2776` | 69 | 46 |
| `0x00e1829b` | 80, 81 | 32 |
| `0x00e21d13` | 115 | 13 |
| `0x00d8aba2` | 134 | 26 |
| `0x00e4b1c3` | 144 | 7 |

The complete silent methods are `0x00e42a9e` world 62, `0x00dc6b34` world 64
and `0x00e6dc49` world 79. Actor eligibility was checked against merged
RENDER-ACTORS-006. RENDER-ACTORS-007 is not merged at the final main fetch.
AUDIO-005 already supports BY_MONSTER fixture loading; actor plans alone do not
close its unsupported whole-owner operations. All 48 models referenced by this
new admission actually load. Earlier absent files `0x90a..0x90c` and effect alias
`0x356` remain refused in their separate contexts.

`monster_audio_extended.py` emits authored decision nodes from a restricted
instruction-checked interpreter. It rejects foreign writes, fields and services.
Original whole-owner execution compares ordered site/id/object/loop arguments,
AL, signed remainders and conditional draw consumption for every emitted edge.
Native production uses nonnegative MSVC 15-bit RNG. Its reachable summary has
142 registered ids. Negative scripted arithmetic controls have three extra id
outcomes, including unregistered 155; those are not production outcomes.

The complete outer dispatcher consumes strict distance >500 before class lookup
and before audio RNG. Inner distance gates and original caller tails retain their
order. Native hooks use existing loaded actor/model/action/frame/position inputs
and an audio-only RNG stream. Shared combat and character files contain added
sound-call lines and includes only. The existing cosmetic death latch now covers
the complete extended owners; animation and replicated records are unchanged.
Once-only combat gates, sound ordering, independent cursors, mute/disabled
draining, detached no-backlog delivery and active-id suppression retain their
contracts. Held original frame windows can request repeatedly under that policy.

Existing `mu_skill_book_check_cast`, `mu_skill_book_cast`, ordinary
`mu_combat_cast` target fixtures and viewport buff snapshots do not own the
original class-use controller. All 66 candidates remain unwired. Guardian's
three earlier handler-state sites retain their fixture limit. The 182 new sites
operate only when a matching actor already exists and is loaded. No placement,
server-class construction, request route, event feed, pickup answer, transformed
input or server state is introduced. The virtualised interval
`0x01854279..0x018542c2` remains excluded and unfollowed.

## Music

No music selector or mixer change. The 142 production ids resolve and decode
with nonzero combined PCM against read-only installed inputs. This verifies
availability and delivery, without claiming FMOD mixer parity or an original
client's global random-stream phase.

## Verification

All heavy commands run at nice 10, make capped at two jobs and validators at
two jobs. Shared-host load/free-memory guards precede them. No lane full gate,
app-packaging module, original live client or installed app operation runs.
Audio compiled inputs are checked at `17da1ea04ad74d72f62b4adf36ff4226290f8dbc`;
the UI-WINDOWS-005 merge delta is checked at
`2ffecb3e88608c572790a0b34846a544cafec4d4`. Identity uses
`8f3b66ccdb1845628ed7cbd5841c5a30882343c1`. Later edits are metadata and docs.
The final main fetch still reports `c5b9d5ca`.

| Check | Result | Wall seconds |
|---|---|---:|
| Root build after INNER-005 merge | Pass | 19.49 |
| Root build after UI-WINDOWS-005 merge | Pass | 14.76 |
| New original comparison | 55,392 cases, 182 sites, 11 owners, zero mismatches/stops | 77.1 |
| Legacy scalar original comparison | 38,315 cases, 245 sites | 25.1 |
| First changed-target mutation phase | 18 compiled controls caught before final helper setup stop | 80.34 |
| New completion-control resume | 2,640 caller controls pass; last new mutant caught | 10.84 |
| Updated legacy completion control | Mutant caught | 4.56 |
| Private audio/model/delivery checks | 15 native checks pass; 48 models load; 142 ids decode | 23.80 combined run |
| Corrected historical census mask | 2/2 pass | 3.41 |
| Final entry-ledger/census module | 3/3 pass | 4.90 |
| Standalone public-ledger grouping | Exact groups and current ownership pass | 1.84 |
| Primary affected validators | 30/250 rows pass, 339,112 cases/checks | 656.13 incl. selection |
| Primary affected portable tests | 1,563 run, 1,263 pass / 300 explicit skips, zero failures/errors | 541.53 incl. selection |
| UI merge affected validators and portable tests | 12 rows pass, 38,469 cases/checks; 1,412 tests, 1,111 pass / 301 skips | 513.16 incl. both selections |
| UI merge reduced private modules | 38 tests, 36 pass / two explicit skips | 130.07 |
| Rejudge saved primary reports after metadata change | All 30 pass | 0.08 |
| Final document consumers | 36 tests, 35 pass / one explicit skip, zero failures/errors | 15.26 |
| Staged repository audit | 2,360 files, zero rejected | 23.40 |

New original cases comprise 26,442 whole-owner, 26,310 full outer-dispatch and
2,640 caller-tail cases. The report SHA-256 is
`50164fc2a1d247c14e506aa52571990c89d93a4ee6af84d47a5ab7df51dd9b38`.
There are **19 new compiled mutants plus one updated legacy mutant, 20 total**.
Completed controls are not repeated after the harness-only setup fixes.

Primary post-build selection takes 95.70 s and retains all ten symbol fallback
rows. Primary portable selection has 176 work items / 170 native modules;
removing `test_native_app.py` leaves 175 / 169. Selection is 81.06 s, runner
458.1 s. The UI merge selects only its changed paths: 12 validator rows in
44.04 s, 145 portable items / 142 native modules in 62.35 s. Removing the app
module leaves 144 / 141; that portable runner takes 345.4 s.

**8d reduced:** both native selections exceed the 40-item private cap. The
focused fifteen audio/native checks, census controls and five changed UI modules
supply private coverage using canonical `private-env.sh` from repository root.
Optional mutants are disabled in unaffected validators and UI integration tests.
No AUDIO-005 mutant set is repeated except the single changed completion control.

Early proof attempts stopped in test setup: a misspelled module constant at
70.21 s, a read-only push audit at 3.98 s, and an unqualified Plan name at
14.16 s. The first mutation phase caught eighteen controls before its final
helper referenced an out-of-scope variable. Focused resumes complete the missing
controls. The 23.80 s private run's sole failure was the historical census mask
omitting INNER-005's header reference; all fifteen native tests passed. The
corrected census runs above pass. None required weakening runtime expectations.

Source/spec self-review covers semantic ownership, original provenance/order,
conditional RNG, class AL, outer consume, caller latches, loaded-model/action
guards and shared-file ownership. No independent reviewer is claimed. Finite
geometry and NaN frame controls are covered; NaN geometry is not compared.

### Default identity

A control binary uses exact main `c5b9d5ca` compiled inputs in this worktree.
The three existing C files changed by this lane temporarily use their main
blobs; a finally block restores every production byte. Added audio headers
remain unreferenced by the control. Main itself is never edited or built in.

Both binaries explicitly rebuild with `nice -n 10 make -C native -j2 world`.
Control build **5.82 s**, production **5.69 s**. SHA-256 hashes are distinct and
rechecked after rendering:

- Control `0b67fc1e9ec614d2c318fb51d31f1205c7f8d5fd4921aa34834b969a23519c8a`.
- Production `7d8bb97dd1aa89a5259e0bbbdea68989cbe93623789a09f7e75c768fbbf477c5`.

Default draw, no draw_all/live_time, 640x400, 25 frames sampled at 0/24, demo
name Preview. October's fourteen and DATA-ACQ-002's 32 views all exit 0 in both
runs. Only output-directory prefixes are normalized in JSONL, with every scene
row/field retained. **92/92 PNGs, 92/92 OBJECT/light dumps and 46/46 reports
match**, 230 artifacts total. Control renders take **92.39 s**, production
**76.67 s**; full identity including builds/comparison **180.73 s**.

An earlier preflight stopped before rendering on an unused original PNG path,
14.36 s. Task-local path resolution now checks the 138 scene snapshot files
actually consumed. A later ancestry guard caught incoming UI-WINDOWS-005 before
any source overlay; main was merged and its delta verified before this accepted
sweep. These controls verify default repeatability without original-client
fidelity or a visual claim about omitted actor contexts.

### Steward validators

The union is **38 rows / 366,085 cases or checks**. Twenty-six primary rows
retain unchanged compiled inputs; twelve rows use the newer UI merge report,
including four overlaps. The table records actual commits and wall times.
Use canonical `~/Documents/MTM/mu-mac-tools/native/private-env.sh` from repository
root. No extra optional mutants are needed.

Steward validators: validate_actor_composites,validate_actor_monsters,validate_actor_plain,validate_actor_recipes,validate_app_polish1,validate_app_polish2,validate_app_polish4,validate_app_polish7,validate_app_polish9,validate_audio_callers,validate_audio_domains,validate_audio_events,validate_audio_items,validate_audio_kubera,validate_audio_monsters,validate_audio_monsters6,validate_audio_music,validate_audio_objects,validate_audio_objects4,validate_audio_voices,validate_charsel_items,validate_gfx3,validate_icarus_c2,validate_inventory_fx,validate_item_callers,validate_items_ui,validate_map_polish,validate_movement,validate_render_effects16,validate_render_effects17,validate_render_effects18,validate_render_effects19,validate_render_effects24,validate_render_effects25,validate_render_effects26,validate_render_effects28,validate_render_effects31,validate_worlds_fog

| Validator | Cases/checks | Wall seconds | Tested source |
|---|---:|---:|---|
| `validate_actor_composites` | 1427 | 11.9 | `17da1ea0` |
| `validate_actor_monsters` | 1437 | 39.9 | `17da1ea0` |
| `validate_actor_plain` | 21437 | 251.3 | `17da1ea0` |
| `validate_actor_recipes` | 1669 | 127.0 | `17da1ea0` |
| `validate_app_polish1` | 752 | 20.3 | `2ffecb3e` |
| `validate_app_polish2` | 1028 | 3.6 | `2ffecb3e` |
| `validate_app_polish4` | 10485 | 34.2 | `2ffecb3e` |
| `validate_app_polish7` | 5120 | 1.7 | `2ffecb3e` |
| `validate_app_polish9` | 4668 | 4.3 | `2ffecb3e` |
| `validate_audio_callers` | 5528 | 5.9 | `2ffecb3e` |
| `validate_audio_domains` | 2544 | 27.3 | `2ffecb3e` |
| `validate_audio_events` | 70980 | 5.9 | `17da1ea0` |
| `validate_audio_items` | 3000 | 3.5 | `2ffecb3e` |
| `validate_audio_kubera` | 1000 | 1.8 | `17da1ea0` |
| `validate_audio_monsters` | 38315 | 25.1 | `17da1ea0` |
| `validate_audio_monsters6` | 55392 | 77.1 | `17da1ea0` |
| `validate_audio_music` | 4291 | 0.5 | `17da1ea0` |
| `validate_audio_objects` | 4000 | 4.7 | `17da1ea0` |
| `validate_audio_objects4` | 10093 | 9.4 | `17da1ea0` |
| `validate_audio_voices` | 2182 | 0.2 | `17da1ea0` |
| `validate_charsel_items` | 8817 | 9.3 | `17da1ea0` |
| `validate_gfx3` | - | 5.5 | `2ffecb3e` |
| `validate_icarus_c2` | 8400 | 24.1 | `17da1ea0` |
| `validate_inventory_fx` | 8017 | 9.3 | `17da1ea0` |
| `validate_item_callers` | 6013 | 1.8 | `17da1ea0` |
| `validate_items_ui` | 8517 | 15.8 | `17da1ea0` |
| `validate_map_polish` | 876 | 0.6 | `2ffecb3e` |
| `validate_movement` | 6614 | 73.3 | `17da1ea0` |
| `validate_render_effects16` | 424 | 5.3 | `2ffecb3e` |
| `validate_render_effects17` | 618 | 9.6 | `17da1ea0` |
| `validate_render_effects18` | 540 | 1.6 | `17da1ea0` |
| `validate_render_effects19` | 400 | 1.2 | `17da1ea0` |
| `validate_render_effects24` | 226 | 3.4 | `17da1ea0` |
| `validate_render_effects25` | 202 | 13.4 | `17da1ea0` |
| `validate_render_effects26` | 348 | 12.2 | `17da1ea0` |
| `validate_render_effects28` | 630 | 2.7 | `17da1ea0` |
| `validate_render_effects31` | 66051 | 319.5 | `17da1ea0` |
| `validate_worlds_fog` | 4044 | 6.3 | `2ffecb3e` |

## Next

Future audio work starts from the 516 unresolved owner candidates, 97 refused
class candidates and 66 unwired class-use sites, retaining the earlier Guardian,
model/effect and protection limits.

## Delivery

The pushed checkpoints preserve resumable WIP at the required cadence. Final
documentation and all checks are complete before the readiness entry. The PR
targets main; the merge steward owns the merge. Temporary outputs, renders,
builds, worktree and local branch are removed after that entry. The remote branch
is retained for the steward. Ready for steward.
