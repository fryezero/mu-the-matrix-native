# RENDER-EFFECTS-030

WIP: implementation and affected private validators pass. Final portable merge
checks, incoming private UI tests, refreshed proof renders, default identity,
repository audit and PR/cleanup are pending. No ready-prs entry yet.

Branch `codex/render-effects-030` began at EFFECTS-028 `32e36706` while #376
was open. Main at start was `d4af71dd`. Required parent/current main was merged
as `b5e53b91`, then AUDIO-003/INNER-002 as `92ef41f3`, and ITEMS-UI-001
(main `626abce1`) as `a06eaf2b`. No subagents or full lane gate.

## Skill audit and implemented boundary

[Complete inventory and original addresses](../research/client-render-effects-030.md):
28 learned entries plus ordinary attack; also every visible unlearned tree entry
and all 46 DK / 40 Elf brand aliases. The pinned catalogue contains 27 DK and
37 Elf class entries, with 37 entries outside the learned list. Shipped demo
class bytes are `0x01/0x02`, with no evolved record. Promoted fixture lists and
visual selectors are distinguished explicitly. Skill 47 is stale and refused.

The 29-row learned inventory moves 10 P / 4 L / 15 M to 11 P / 5 L / 13 M.
P/L/M concern bounded presentation, not eligibility or authoritative state.
The historical 23-route denominator remains 20 P / 3 L.

| Skill | Before -> after | New behavior and remaining boundary |
|---|---|---|
| 24 Triple Shot | L -> P | Original fallthrough and learned-index argument order; ordinary bow three -> four arrows, special fan four -> five; bow 0x12f9 sparks fifteen -> thirty |
| 51 Ice Arrow | M -> L | Single Arrow01 caller, saved client target index, draw and retirement; optional target ice/freeze response and general equipment context remain absent |
| 52 Penetration | M -> L | Step-3 charge request, frame-5 hold, five-step cutoff, subtype-2 arrow; charge 0x7fd0/0 and child 0x46c/0 are refused |
| 48 Swell Life | M -> M | Original 36 joints plus two effect requests; all 38 visual consumers refused; no primary aura pixels claimed |
| 344 Blood Storm | M -> M | Early cutoff and original destination/emitter request; emitter 0x583/0 refused; generic fixture action is not a recovered receive action |
| 416 / 424 | M -> L | Individually evidenced synthetic 416/52 and 424/51 selectors; retain the same base limits |

The module preserves complete ordered caller arguments, keys/default words,
owner and sound provenance. Only authored class/weapon/tile/learned-list context
is supplied. The native adapter scans active learned entries, capped at 150;
original stale entries past the learned count are outside admission.

Self-review corrected the saved Ice Arrow word from server key to client index.
Original accessor `0x009a13f4` resolves a 400-slot character table. The native
regression uses a nonzero session slot, requires a distinct server key, and
checks that the saved word equals the slot. The reconstructed module/header
rename changed neither ABI nor compiled bytes: library SHA-256 stayed
`5085c72b528733ff8d84755475e57243ccba7ad130617ed3e30741c45639b20d`.

## Original proof

Full new validator at `25353381`: 1,914 focused checks, zero mismatches,
18/18 compiled production-C mutants caught, zero original-machine stops,
29.47 s command wall. Accounting is 572 original step, 1,000 original end,
256 original create/move comparisons, 78 native selector controls and eight
retirement assertions. Thus 1,828 execute original record/caller instructions.
The additional private brand test executes six real `0x00bb1c32` walks over
synthetic lookup records: correct, swapped and zero-brand inputs for both aliases.

Eight arrow lifecycle sequences carry original records independently from
creation to retirement, including owner-death sequences. C never reseeds the
original records between ticks. Terrain, animation/model and arrow-hit services
remain declared synthetic inputs. This is not original GPU-image equivalence.
The full proof's compiled module is byte-identical after the metadata rename;
its 452-check registry sample passes on the current branch without mutants.

## Native fixture proof

Initial installed-data before/after/repeat: seven scenes, 69.49 s command wall,
42/42 after/repeat PNG pairs identical. Hero names are DemoKnight/DemoArcher,
target DemoTarget; Lorencia tile 182,127, target 184,127, frames 0..90 at 40 ms.
Use GL, 960x600, no audio/items/players, save every 18 and step time series every 1.
One script cast on frame 2 and stop on frame 3 prevents a repeated cast.

| Skill | Arrows before -> after | New direct visual / arrow caller requests | Total refused before -> after |
|---|---:|---:|---:|
| 344 | 0 -> 0 | 1 / 0 | 0 -> 1 |
| 24 | 3 -> 4 | 0 / 2 | 0 -> 0 |
| 51 | 0 -> 1 | 0 / 1 | 0 -> 0 |
| 52 | 0 -> 1 | 1 / 1 | 0 -> 2 |
| 48 | 0 -> 0 | 38 / 0 | 0 -> 38 |
| 416 | 0 -> 1 | 1 / 1 | 0 -> 2 |
| 424 | 0 -> 1 | 0 / 1 | 0 -> 0 |

All after casts have zero sent requests, one unsent request, zero hits/kills
and unchanged target HP. Existing model/bitmap totals remain 29/39. Visual
inspection shows the existing Arrow01 body and orange trail for Ice Arrow;
no invented icy projectile is supplied. Close-target Penetration retires
immediately through the existing arrow-hit service. Its early-flight proof
with a farther authored target and the merged after/repeat refresh are pending.

## Completed checks and test budget

All heavy work uses nice 10, at most make -j4 and two validator/test jobs.
Load/memory guards are observed. Canonical private-env.sh is sourced from the
repository root; private data and tools/evidence/input links remain untracked.
No owner client, installed application, packet/power or protection work occurs.

| Check / tested commit | Result | Command wall |
|---|---|---:|
| Root build, `92ef41f3` | pass | 12.16 s |
| Root build after ITEMS-UI merge, `a06eaf2b` | pass, up to date | 1.05 s |
| New full focused proof, `25353381` | 1,914 checks; 18/18 mutants; zero stops | 29.47 s |
| Initial reduced private modules, `bee54942` | 21/21, zero skips/failures | 59.55 s |
| Merged reduced private modules, `92ef41f3` | 22/22, zero skips/failures | 74.05 s |
| Portable affected, `bee54942` | 163 items; 1,748 tests, 1,457 pass / 291 expected skips, zero failures/errors | 628.32 s (491.7 s runner) |
| Portable merge delta, `b5e53b91` | 159 items; 1,465 tests, 1,216 pass / 249 expected skips, zero failures/errors | 513.57 s (399.8 s runner) |
| Private affected current, `92ef41f3` | 58/58 rows, no failures/errors/skips; cache, no mutants | 920.51 s |
| Private merge extra, `a06eaf2b` | 53/53 rows, no failures/errors/skips; cache, no mutants | 326.32 s |

8d reduced: initial native selection was 152 items, above the 40-item cap.
The first private run covers the changed effect fixtures, all BowSession cases,
new caller/brand tests, installed combat and parent aura controls. It also
unintentionally included the unchanged EFFECTS-009 mutant method; that passed
and was not repeated. The new 18-mutant run occurs only once. The merged run
covers new Native cases and incoming actor, Muun and object-audio modules.
Incoming ITEMS-UI private tests and final portable delta are pending.

Current selection was inspected before its run. Main-merge selection since
`bee54942` was 82 rows (58.75 s); UI-only selection since `92ef41f3` was ten
(46.29 s). Additional runs are `(merge - current) union UI`: 49 new rows and
four changed-input rechecks. There are 107 distinct rows, not 111 distinct
validators. The four rechecks are audio_callers/domains/items and effects16.
Current row inputs are unchanged after `92ef41f3`, except these four, which
pass again at `a06eaf2b`. No unchanged consumer mutants were requested.

## Steward validators

Canonical private env supplies MU_RECOVERY_INTEGRATION, MU_GAME_ROOT,
MU_NATIVE_DATA_DIR, MU_GFX_LIB, MU_LANG_DIR, MU_SECTION3 and evidence/snapshot
paths. Use --private --no-mutants --cache --jobs 2. No further mutants required.
The table gives each row's latest completed registered-check count and wall;
current = `92ef41f3`, extra = `a06eaf2b`. These counts mix original comparisons
and native/negative controls according to each row; they are not a single
original-instruction case total.

| Validator | Cases | Wall s | Selection |
|---|---:|---:|---|
| `validate_actor_recipes` | 1669 | 134.4 | current |
| `validate_app_polish1` | 752 | 22.0 | extra |
| `validate_app_polish2` | 1028 | 3.9 | extra |
| `validate_app_polish4` | 10485 | 41.8 | current |
| `validate_app_polish7` | 5120 | 1.9 | extra |
| `validate_audio_callers` | 5528 | 7.7 | extra |
| `validate_audio_charsel` | 5968 | 5.6 | current |
| `validate_audio_combat` | 19548 | 33.6 | current |
| `validate_audio_domains` | 2544 | 37.4 | extra |
| `validate_audio_items` | 3000 | 5.4 | extra |
| `validate_audio_objects` | 4000 | 5.4 | current |
| `validate_charsel_items` | 8817 | 9.2 | current |
| `validate_charsel_world` | 1200 | 4.9 | extra |
| `validate_combat` | 496 | 0.8 | current |
| `validate_gfx3` | - | 11.5 | extra |
| `validate_icarus` | 5240 | 37.6 | extra |
| `validate_icarus_c2` | 8400 | 23.8 | current |
| `validate_inventory_fx` | 8017 | 11.2 | current |
| `validate_item_callers` | 6013 | 1.4 | current |
| `validate_item_hiddenmesh` | 116281 | 509.1 | current |
| `validate_items` | 444 | 2.7 | current |
| `validate_items_ui` | 8517 | 18.6 | extra |
| `validate_login_world` | 1200 | 7.6 | extra |
| `validate_map_polish` | 876 | 2.7 | extra |
| `validate_meshdraw` | 14619 | 56.2 | current |
| `validate_model_edge` | 954 | 118.6 | current |
| `validate_model_light` | 1433 | 5.4 | current |
| `validate_movement` | 6614 | 57.6 | current |
| `validate_muun_passes` | 1361 | 1.7 | extra |
| `validate_muun_visual` | 912 | 1.6 | extra |
| `validate_object_render` | 1984 | 13.7 | extra |
| `validate_path` | 4719 | 33.7 | current |
| `validate_render_effects` | 660 | 1.4 | current |
| `validate_render_effects10` | 154 | 0.4 | current |
| `validate_render_effects11` | 176 | 0.3 | current |
| `validate_render_effects12` | 64 | 0.3 | current |
| `validate_render_effects13` | 180 | 0.6 | current |
| `validate_render_effects14` | 660 | 1.6 | current |
| `validate_render_effects15` | 509 | 1.1 | current |
| `validate_render_effects16` | 424 | 4.6 | extra |
| `validate_render_effects17` | 618 | 9.3 | current |
| `validate_render_effects18` | 540 | 1.7 | current |
| `validate_render_effects19` | 400 | 1.1 | current |
| `validate_render_effects20` | 148 | 0.3 | current |
| `validate_render_effects21` | 267 | 0.8 | current |
| `validate_render_effects22` | 202 | 7.1 | current |
| `validate_render_effects23` | 1174 | 9.6 | current |
| `validate_render_effects24` | 226 | 5.1 | current |
| `validate_render_effects25` | 202 | 10.7 | current |
| `validate_render_effects27` | 424 | 2.7 | current |
| `validate_render_effects28` | 630 | 2.9 | current |
| `validate_render_effects3` | 720 | 1.3 | current |
| `validate_render_effects30` | 452 | 0.5 | current |
| `validate_render_effects4` | 1920 | 7.0 | current |
| `validate_render_effects5` | 1190 | 4.3 | current |
| `validate_render_effects6` | 1000 | 1.5 | current |
| `validate_render_effects7` | 596 | 1.8 | current |
| `validate_render_effects9` | 304 | 1.0 | current |
| `validate_render_worlds_a` | 9000 | 23.4 | extra |
| `validate_session_party` | 200 | 0.9 | current |
| `validate_skill_fx` | 660 | 1.4 | current |
| `validate_terrain` | 583500 | 420.8 | current |
| `validate_terrain_remaining` | 2147 | 5.0 | current |
| `validate_viewport_monsters` | 1963 | 11.6 | current |
| `validate_world_fidelity` | 200 | 0.3 | extra |
| `validate_world_light_name` | 304 | 0.5 | extra |
| `validate_world_particle_consumers` | 900 | 0.9 | current |
| `validate_world_tile_folder` | 5700 | 36.7 | extra |
| `validate_worlds_121` | 4000 | 8.7 | extra |
| `validate_worlds_after` | 13424 | 17.0 | extra |
| `validate_worlds_after2` | 32216 | 33.0 | extra |
| `validate_worlds_after3` | 10212 | 10.4 | extra |
| `validate_worlds_after4` | 9181 | 15.0 | extra |
| `validate_worlds_after5` | 6000 | 13.1 | extra |
| `validate_worlds_after6` | 7300 | 77.4 | current |
| `validate_worlds_b` | 4000 | 3.9 | extra |
| `validate_worlds_d` | 2400 | 4.2 | current |
| `validate_worlds_e` | 4840 | 20.4 | extra |
| `validate_worlds_f` | 1818 | 0.5 | current |
| `validate_worlds_fog` | 4044 | 9.5 | current |
| `validate_worlds_g` | 6000 | 4.5 | extra |
| `validate_worlds_g2` | 2657 | 6.2 | extra |
| `validate_worlds_g3` | 4000 | 7.4 | extra |
| `validate_worlds_h` | 6000 | 4.5 | extra |
| `validate_worlds_i` | 6000 | 4.9 | extra |
| `validate_worlds_inner` | 4000 | 5.4 | extra |
| `validate_worlds_inner2` | 5000 | 6.8 | extra |
| `validate_worlds_j` | 6000 | 4.6 | extra |
| `validate_worlds_k` | 6000 | 5.4 | extra |
| `validate_worlds_karutan` | 3000 | 5.9 | extra |
| `validate_worlds_l` | 1260 | 1.5 | current |
| `validate_worlds_m` | 1080 | 2.6 | current |
| `validate_worlds_n` | 13000 | 9.7 | extra |
| `validate_worlds_o` | - | 7.3 | extra |
| `validate_worlds_p` | 10000 | 8.9 | extra |
| `validate_worlds_p2` | 6000 | 5.8 | extra |
| `validate_worlds_q` | 11000 | 14.4 | extra |
| `validate_worlds_q2` | 4000 | 8.9 | extra |
| `validate_worlds_r` | 12000 | 9.3 | extra |
| `validate_worlds_r2` | 9000 | 8.6 | extra |
| `validate_worlds_raklion` | 3000 | 7.1 | extra |
| `validate_worlds_s` | 11000 | 10.0 | extra |
| `validate_worlds_s2` | 10000 | 8.6 | extra |
| `validate_worlds_s3` | 22000 | 24.2 | extra |
| `validate_worlds_slots` | 18999 | 23.1 | extra |
| `validate_worlds_slots2` | 33000 | 38.8 | extra |
| `validate_worlds_slots3` | 36000 | 41.2 | extra |

Steward validators: validate_actor_recipes,validate_app_polish1,validate_app_polish2,validate_app_polish4,validate_app_polish7,validate_audio_callers,validate_audio_charsel,validate_audio_combat,validate_audio_domains,validate_audio_items,validate_audio_objects,validate_charsel_items,validate_charsel_world,validate_combat,validate_gfx3,validate_icarus,validate_icarus_c2,validate_inventory_fx,validate_item_callers,validate_item_hiddenmesh,validate_items,validate_items_ui,validate_login_world,validate_map_polish,validate_meshdraw,validate_model_edge,validate_model_light,validate_movement,validate_muun_passes,validate_muun_visual,validate_object_render,validate_path,validate_render_effects,validate_render_effects10,validate_render_effects11,validate_render_effects12,validate_render_effects13,validate_render_effects14,validate_render_effects15,validate_render_effects16,validate_render_effects17,validate_render_effects18,validate_render_effects19,validate_render_effects20,validate_render_effects21,validate_render_effects22,validate_render_effects23,validate_render_effects24,validate_render_effects25,validate_render_effects27,validate_render_effects28,validate_render_effects3,validate_render_effects30,validate_render_effects4,validate_render_effects5,validate_render_effects6,validate_render_effects7,validate_render_effects9,validate_render_worlds_a,validate_session_party,validate_skill_fx,validate_terrain,validate_terrain_remaining,validate_viewport_monsters,validate_world_fidelity,validate_world_light_name,validate_world_particle_consumers,validate_world_tile_folder,validate_worlds_121,validate_worlds_after,validate_worlds_after2,validate_worlds_after3,validate_worlds_after4,validate_worlds_after5,validate_worlds_after6,validate_worlds_b,validate_worlds_d,validate_worlds_e,validate_worlds_f,validate_worlds_fog,validate_worlds_g,validate_worlds_g2,validate_worlds_g3,validate_worlds_h,validate_worlds_i,validate_worlds_inner,validate_worlds_inner2,validate_worlds_j,validate_worlds_k,validate_worlds_karutan,validate_worlds_l,validate_worlds_m,validate_worlds_n,validate_worlds_o,validate_worlds_p,validate_worlds_p2,validate_worlds_q,validate_worlds_q2,validate_worlds_r,validate_worlds_r2,validate_worlds_raklion,validate_worlds_s,validate_worlds_s2,validate_worlds_s3,validate_worlds_slots,validate_worlds_slots2,validate_worlds_slots3

## Remaining verification and next lane

- Complete final portable merge delta and private ITEMS-UI module.
- Explicitly build mu-world, record final SHA-256, refresh merged after/repeat
  fixtures and observe early Penetration flight.
- Compare the single starting baseline: before binary SHA-256
  `6f1f9d6a6367e54078a8848b3398dddff92d75ffb6cbf47bf5fd49956a6d43e7`;
  root/world builds 31.92/4.54 s. Baseline 46 captures, 92 PNGs, 92 dumps:
  October 16.18 s, DATA-ACQ-002 44.12 s, no draw_all or live_time. It is never
  rerun. INNER-002's expected Elbeland PNG/dump and Swamp report deltas must be
  distinguished from this lane's inactive default skill routes.
- Final repository audit, status docs, PR body, push, ready entry and cleanup.
- EFFECTS-026 owns the missing charge/child, Swell Life joint/effect and Blood
  Storm emitter consumers. Research lists constructor/mover addresses. Blood
  Storm's static constructor lifetime 70/child 0x584/0/sound 0x2b0 is not a
  validated native lifecycle. No primary pixels are claimed for refused routes.
- Other M/L inventory rows, summons, shield/mount actions, general equipment,
  optional target ice/freeze response and unadmitted aliases remain open.

## WIP checkpoint, 00:06 local, November 12

Implementation, original proof and all 107 distinct affected private rows pass.
Latest main fetched at 00:00 is `626abce1`, merged as `a06eaf2b`. Native/core and
combat inputs did not change in that UI merge. This checkpoint includes
the final UI merge and the consolidated private evidence. Host load has stayed
above 14 since the last batch ended at 00:00; free memory remains above 25%.
Next: private UI and final portable delta when the resource guard permits, then
renders, audit and PR. The 20-minute fallback permits own builds at -j2 if
load has not fallen by 00:20. No source edits or pending original mutants.
