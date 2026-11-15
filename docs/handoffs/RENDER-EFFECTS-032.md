# RENDER-EFFECTS-032

PR-ready verified fixture subset. The steward owns the combined gate and merge.

Branch `codex/render-effects-032` starts at main `b7dfd2ed`. Main `2b0b2716`,
AUDIO-004 #388, is integrated through `8187e8e3` / registry resolution `fb561cff`.
Late main `4babc900`, ACTORS-005 #389 and INNER-004 #390, is integrated as
`fe83b2b9`. UI-WINDOWS-003 #391 main `a95880c4` is integrated as `28788cfc`.
UI-WINDOWS-004 #392 main `4480bf41` is integrated as `eaf8cdcf`.
The combined inputs pass the delta checks below.
Pure caller inputs are `8965554f`; native exceptional-item admission is `7e298c4d`.
Later commits contain delivery documentation only.
No subagents or full lane gate. Work uses nice 10, make at most four jobs and
two validator/test workers. Resource pauses are observed.

## Skill audit and implemented boundary

The same 29 learned/ordinary rows as EFFECTS-030 move **11 P / 5 L / 13 M to
11 P / 7 L / 11 M**, for this lane alone. P/L/M measure bounded presentation,
not eligibility or authoritative state. Consumer-only work in EFFECTS-031 is
excluded from this delta. [Original caller inventory](../research/client-render-effects-032.md).

| Skill | Before -> after | Implemented result or remaining boundary |
|---|---|---|
| 0 ordinary attack | P -> P | Unchanged |
| 19 Falling Slash | P -> P | Unchanged |
| 20 Lunge | P -> P | Unchanged |
| 21 Uppercut | P -> P | Unchanged |
| 22 Cyclone | P -> P | Unchanged |
| 23 Slash | P -> P | Unchanged |
| 41 Twisting Slash | P -> P | Unchanged |
| 42 Anger Strike | P -> P | Unchanged |
| 43 Death Stab | L -> L | General equipment/link selection remains open |
| 44 Crescent Moon Slash | M -> L | Pose 0x98, step spark joints/particles and both sounds; 0x49e/0 end consumer refused |
| 18 Defense | M -> L | Pose 0xd7 and sound, authored shield context; held-input lifetime and shield equipment rendering unproved |
| 47 stale entry | M -> M | Always refused, no invented record or cast |
| 48 Swell Life | M -> M here | Consumer-only row skipped for EFFECTS-031 |
| 49 Fire Breath | M -> M | Mount pose 0xf9 and frame cutoff; primary 0x8001/0 refused |
| 344 Blood Storm | M -> M here | Consumer-only row skipped for EFFECTS-031 |
| 24 Triple Shot | P -> P | Existing two requests retained; wing/kind action context added |
| 26 Heal | P -> P | Unchanged |
| 27 Greater Defense | L -> L | Existing fixture aura; general links/presence remain open |
| 28 Greater Damage | L -> L | Existing fixture aura; general links/presence remain open |
| 30 Summon Goblin | M -> M | Caster pose/sound; 0x7f84/3 refused, actor construction/lifetime absent |
| 31 Summon Stone Golem | M -> M | Same explicit summon boundary |
| 32 Summon Assassin | M -> M | Same explicit summon boundary |
| 33 Summon Elite Yeti | M -> M | Same explicit summon boundary |
| 34 Summon Dark Knight | M -> M | Same explicit summon boundary |
| 35 Summon Bali | M -> M | Same explicit summon boundary |
| 36 Summon Soldier | M -> M | Same explicit summon boundary |
| 51 Ice Arrow | L -> L | Wing/kind pose context; optional target visual remains EFFECTS-031 work |
| 52 Penetration | L -> L | Wing/kind pose context; charge/child remain EFFECTS-031 work |
| 2044 Raining Arrow of Saturation | P -> P | Unchanged |

Individual synthetic aliases 416/52 and 424/51 remain L, outside those 29 rows.
Unlearned catalogue IDs and all other aliases retain 030's separate inventory;
no icon, masked class nibble or shared consumer admits a new alias.

`MU_SKILL32_CONTEXT=bow_kind,wing,shield,mount` supplies four decimal appearance
service answers. Default is configured bow kind, wing -1 and no shield/mount.
Examples are `1,0,0,0` and `0,-1,1,0`. Wing zero is present, as in the original
comparison against -1. This does not equip a body or grant eligibility. New
callers require an active learned entry within min(count,150); stale capacity
and skill 47 remain refused. Default-step rows 18 and 30..36 also refuse
configured weapon 0x12fb (hero item 0x815), whose separate spark burst is outside
this subset. Native regression tests include an adjacent ordinary-item positive
control. Only authored class/weapon/tile context is used.

## Original proof

Final proof at `8965554f`: **4,433 checks, zero mismatches, 31/31 compiled
production-C mutants, zero original-machine stops, 71.71 s**.
Of these, 3,217 execute original instructions: 1,000 step, 1,000 end, 900 start,
117 pose and 200 interleaving cases. The remaining 1,216 are authored admission,
learned-count/cap and exact-selector controls. Registry sample is 1,723 checks.

Every effect/joint/particle argument is compared in order, including owner,
key, skill/default words, scale, sound site, frame/cutoff writes and RNG use.
The streaming family gives consumer services varying declared CRT draw counts
and compares the resulting requests and total RNG use. Native emits each pair
before the next pitch draw. The legacy particle constructor borrows/returns
combat CRT state, then restores the world pool's separate movement stream.
Whole-client RNG phase, pool allocation, terrain and GPU equivalence are not
claimed. No consumer source changes.

An initial 4,233-check/28-mutant proof, 31.32 s, did not model consumer RNG. Self-review
found the native integration gap. The final proof supersedes it, adding three
streaming mutants. The repeated mutant run follows a changed production path
and new comparator family. Other validators run without mutants. Exploratory
stops never count as evidence or caught mutants.

Combat dylib SHA-256:
`62936052baf3718000d820c5060f981e2d6def34b127932f6b55e5348e57fbb7`.
Original target/text/data pins and routine body hashes are described in the
research note and validator. Receive parsers, network and power code do not run.

## Native fixture proof

Twelve installed-data GL scenes, one cast at frame 2 and stop at frame 3,
Lorencia 182,127, target 184,127, 960x600, 60 frames saved every 12, draw every
logic frame. Names DemoKnight/DemoArcher and authored DemoTarget. No audio output,
other players or items. All after casts have zero sent / one unsent request,
zero hits/kills and unchanged target HP. Loaded models/bitmaps are 29/39, except Penetration is 30/39 with its arrow model.

| Scene | Visual requests | Refused | Result |
|---|---:|---:|---|
| Each of 30,31,32,33,34,35,36 | 1 | 1 | Caster pose/sound only; no summon body |
| 18 with shield context | 0 | 0 | Defense pose/sound in a finite fixture schedule |
| 44 | 89 | 1 | Eleven four-joint/four-particle steps, refused final 0x49e/0, two sounds |
| 49 with mount context | 1 | 1 | Mount pose/cutoff and sound, primary fire missing |
| 51 with wing/kind | One arrow caller | 0 | Existing projectile |
| 52 with wing/kind | Charge plus arrow caller | 2 | Existing projectile, refused charge/child |

Early wing scenes use target 187,127, frames 0..11 saved at 0/3/6/9/11.
The initial before/after/repeat proof passes 72 long-scene and ten early PNG
pairs, 63.47 s and 9.39 s. A root-path preflight
fails before producing an image and is not counted. The post-RNG after/repeat
refresh passes all 82 PNG pairs, 59.08 s, without repeating
any baseline. The final combined-main refresh passes 82/82 pairs again in
58.57 s; all 164 after/repeat PNGs also match the saved
pre-merge hashes. Visual inspection confirms Crescent's spark scatter, Defense's
pose, floating bow actions and the frame-6 Penetration projectile. The new RNG
ordering changes the active Crescent scatter as intended. The long Penetration
sample misses its short flight; the early scene covers it. These are native
repeatability/component controls, not original GPU images.

## Default identity and binaries

Both versions are explicitly built with `make -C native -j4 world`, in this
isolated worktree before/after edits. Root make alone is not the world rebuild.
The baseline is main b7dfd2ed, captured once; no successful baseline is repeated.
The final script rebuilds/checks the binary hash immediately before its sweep
and verifies the hash again afterward.

- Before SHA-256: `e341fc2000d2e7f035f1e1814ca5384231389c8e7409ed20557643b0485108d7`.
- After SHA-256: `794060748b4ef28c72ab90da9cfe4c4c285a92b99b0affd30f96d9938ad230f4`.

Default draw, no draw_all/live_time, 640x400, 25 frames sampled at 0/24:

| Dataset | PNGs | OBJECT/light dumps | Normalized reports |
|---|---:|---:|---:|
| October 22, 14 views | 26/28 identical | 28/28 identical | 13/14 identical |
| DATA-ACQ-002, 32 views | 64/64 identical | 64/64 identical | 32/32 identical |

Before the actor/world/UI merges, all 230 artifacts match (after 69.74 s).
The final UI4-combined after-only sweep is 71.60 s:
**227/230 artifacts match**. The two Kanturu37 PNGs and one report change because
INNER-004 restores the original extra RGBA mesh. All 45 other views, all 92
OBJECT/light dumps and the remaining reports stay identical. Pixel differences:
oct/37-kanturu/frames/frame-0024.png: 7686 pixels, mean RGB 0.295926/255; oct/37-kanturu/frames/frame-0000.png: 7645 pixels, mean RGB 0.106052/255. The skill callers are inactive in these default views. Only output
prefixes are normalized in reports. The successful baseline runs once (74.61 s).
Two obsolete-path preflights produce no image; paths are rebased to canonical MTM.

## Completed checks and test budget

Commands run from the repository root with canonical private-env. No full gate.
Every selected validator, including symbol fallbacks, is retained. No unchanged
consumer mutant run is requested. Wall times exclude load-guard pauses.

| Check | Result | Command wall s |
|---|---|---:|
| Integrated root build | pass | 24.79 |
| Post-RNG-correction root build | pass | 12.70 |
| Final UI4-combined explicit world build | pass | 0.27 |
| Final original proof | 4,433 checks, 31/31 mutants, no stops | 71.71 |
| Initial focused native | 6/6 pass | 7.77 |
| Reduced private native after correction | 15/15 pass, zero skips | 25.75 |
| Portable affected | 170 items; 1,803 tests, 1,490 pass / 313 expected skips; zero failures/errors | 500.74 |
| Initial private affected, pre-correction | 23/23 pass, no mutants, fb40a57e | 358.29 |
| Pre-late-main private affected refresh | all selected rows pass | 290.45 |
| Late-main validator delta | 93 rows since 5c0dec22, no mutants | 1007.16 |
| Actor/world merge root build | pass | 21.13 |
| UI merge root build | pass | 8.39 |
| UI validator delta | 13/13 pass, no mutants | 168.14 |
| Admission guard root build | pass | 14.39 |
| Admission guard validator delta | 12/12 pass, no mutants | 266.30 |
| Combined reduced private native | 54/54 pass, zero skips | 201.69 |
| Combined portable delta since 5c0dec22 | 180 items, 1,837 tests; 1,496 pass / 341 expected skips, zero failures/errors | 541.36 |
| Final fixture refresh | 82/82 after/repeat pairs | 59.08 |
| Combined fixtures | 82 pairs repeat, 164 PNGs unchanged from premerge | 90.52 |
| Combined default after sweep | 227/230 identical; upstream Kanturu37 only | 89.38 |
| UI4 root build | pass | 14.88 |
| UI4 affected validator delta | 22/22 pass, no mutants | 193.71 |
| UI4 reduced private presentation/survey | 8/8 pass, zero skips | 21.91 |
| UI4 portable delta | see final result below | 417.53 |
| UI4 final fixture pairs | 82/82 repeat, 164 PNGs unchanged | 58.57 |
| UI4 default after sweep | 227/230 identical; upstream Kanturu37 only | 71.60 |
| Final staged repository audit | pass, see delivery audit ledger | 36.43 |

**8d reduced:** the private native selection is 174 work items, above the
40-item cap. Private run covers the changed test_render_effects32 module,
neighbouring test_render_effects30 caller/arrow cases and installed combat.
The pre-merge 15 tests pass with no skips. Combined refresh passes 54/54 tests
with zero skips in 201.69 s and covers those callers
plus the exceptional-item positive/negative controls, actor recipes, INNER-004,
item textures and UI-WINDOWS-001/002/003 presentation/original routes.
The UI mutant class is omitted because its source is unchanged in this lane.
After UI4, eight presentation/movie and static route-survey tests pass without
repeating the unchanged incoming-message comparison or mutant class.
Portable private skips are not private proof.

**Owner packaging exclusion:** the initial affected unit runner uses --affected
origin/main, and the combined-main delta uses --affected-since 5c0dec22, both
with MU_RECOVERY_INTEGRATION=0 / MU_GATE_JOBS=2. A task-local driver
filters only native/tests/test_native_app.py from its work-item list, because
that module packages Native Preview and this session's brief forbids packaging.
It changes no committed test or expectation. That exclusion is separate from
the reported skips: 313 initially, 341 in the combined delta. The combined
run executes ten suites in 428.7 s runner wall, 541.36 s command wall. No app bundle, install or installed-app journey occurs.

## Command wall ledger

This records selections, builds, superseded proof checkpoints and the failed
root-path preflight as well as final checks. Exit 1 for the first render attempt
produces no image and is followed by the corrected game-root invocation.
The successful baseline sweep is 74.61 s, recorded separately before edits.
The first combined artifact postprocessor stops on unavailable NumPy before
comparing anything. The corrected Pillow-only postprocessor reuses the finished
captures; it reruns no rendering.
Resource wait time is excluded. An interrupted portable preflight, before any
test execution, discovers the later UI merge and is replaced by the combined run.

| Command label | Wall s | Exit |
|---|---:|---:|
| `focused-native` | 7.77 | 0 |
| `original-mutants` | 31.32 | 0 |
| `root-build` | 24.79 | 0 |
| `world-build` | 6.20 | 0 |
| `fixture-renders` | 1.30 | 1 |
| `fixture-renders` | 63.47 | 0 |
| `validator-selection` | 68.24 | 0 |
| `early-arrow-renders` | 9.39 | 0 |
| `private-validators` | 358.29 | 0 |
| `stream-build` | 12.70 | 0 |
| `stream-sample` | 1.59 | 0 |
| `final-original-mutants` | 71.71 | 0 |
| `native-selection` | 61.91 | 0 |
| `private-native` | 25.75 | 0 |
| `portable-affected` | 500.74 | 0 |
| `final-world-build` | 0.21 | 0 |
| `final-fixture-renders` | 59.08 | 0 |
| `identity-after` | 69.74 | 0 |
| `final-validator-selection` | 89.82 | 0 |
| `final-private-validators` | 290.45 | 0 |
| `repository-audit` | 33.10 | 0 |
| `merge-root-build` | 21.13 | 0 |
| `merge-validator-selection` | 169.85 | 0 |
| `merge-private-validators` | 1007.16 | 0 |
| `ui-root-build` | 8.39 | 0 |
| `ui-validator-selection` | 46.71 | 0 |
| `ui-private-validators` | 168.14 | 0 |
| `admission-root-build` | 14.39 | 0 |
| `combined-private-native` | 201.69 | 0 |
| `admission-validator-selection` | 56.94 | 0 |
| `admission-private-validators` | 266.30 | 0 |
| `combined-portable` | 541.36 | 0 |
| `combined-world-build` | 0.42 | 0 |
| `combined-fixture-renders` | 90.52 | 0 |
| `combined-identity-after` | 89.38 | 0 |
| `combined-artifact-comparison` | 0.06 | 1 |
| `combined-artifact-comparison` | 0.29 | 0 |
| `delivery-validator-selection` | 70.12 | 0 |
| `combined-repository-audit` | 21.68 | 0 |
| `delivery-repository-audit` | 26.60 | 0 |
| `ui4-root-build` | 14.88 | 0 |
| `ui4-validator-selection` | 51.53 | 0 |
| `ui4-private-native` | 21.91 | 0 |
| `ui4-private-validators` | 193.71 | 0 |
| `ui4-portable` | 417.53 | 0 |
| `ui4-world-build` | 0.27 | 0 |
| `ui4-fixture-renders` | 58.57 | 0 |
| `ui4-identity-after` | 71.60 | 0 |
| `ui4-artifact-comparison` | 0.32 | 0 |
| `ui4-vs-ui3-identity` | 0.02 | 0 |
| `delivery-validator-selection` | 110.39 | 0 |
| `ui4-repository-audit` | 36.43 | 0 |

UI4 final portable selection is 178 work items, 417.53 s command wall.
run_test_suites: 7 suites, 1593 tests, 1291 passed, 302 skipped, 0 failures, 0 errors; 0 failed suite(s); 359.3s wall, jobs=2.

## Steward validators

Final results at `5c0dec228af414f129ce061f3a400cefdef07624 / 3e1a10d71591a1f692e6c7a2ca828dec6abaa607 / 45b13d855bc695d6076d61ffc8a1d8027c3b8ca1 / 7e298c4d39a1aef29d9be9e85d9cc8bda9750a52 / eaf8cdcfb55b4e835ad3b276cadd7ae404dd2c85`.
Canonical private-env supplies evidence, MU_SECTION3, MU_GAME_ROOT,
MU_NATIVE_DATA_DIR, MU_LANG_DIR and snapshots. Run --private --no-mutants --cache
--jobs 2. **No further mutants needed.** The final current-main selection has 24 rows and is the queue list.
All 98 rows below preserve the original and merged-main delta results, with
PR rows marked. Counts below mix original comparisons
and each row's native controls; they are not one original-instruction total.

| Validator | Cases | Wall s | Tested | Status | Role |
|---|---:|---:|---|---|---|
| `validate_actor_composites` | 1427 | 9.8 | `eaf8cdcf` | pass | PR |
| `validate_actor_monsters` | 1437 | 50.3 | `eaf8cdcf` | pass | PR |
| `validate_actor_recipes` | 1669 | 120.6 | `eaf8cdcf` | pass | PR |
| `validate_app_polish1` | 752 | 20.9 | `eaf8cdcf` | pass | merge delta |
| `validate_app_polish2` | 1028 | 3.2 | `eaf8cdcf` | pass | merge delta |
| `validate_app_polish4` | 10485 | 37.4 | `eaf8cdcf` | pass | PR |
| `validate_app_polish7` | 5120 | 1.5 | `eaf8cdcf` | pass | merge delta |
| `validate_app_polish9` | 4668 | 3.9 | `eaf8cdcf` | pass | merge delta |
| `validate_audio_callers` | 5528 | 4.9 | `eaf8cdcf` | pass | PR |
| `validate_audio_combat` | 19548 | 32.3 | `3e1a10d7` | pass | PR |
| `validate_audio_domains` | 2544 | 21.0 | `eaf8cdcf` | pass | PR |
| `validate_audio_items` | 3000 | 2.8 | `eaf8cdcf` | pass | PR |
| `validate_audio_objects` | 4000 | 3.0 | `eaf8cdcf` | pass | PR |
| `validate_audio_objects4` | 10093 | 6.0 | `eaf8cdcf` | pass | PR |
| `validate_charsel_items` | 8817 | 9.6 | `3e1a10d7` | pass | PR |
| `validate_charsel_world` | 1200 | 3.8 | `3e1a10d7` | pass | merge delta |
| `validate_gfx3` | - | 5.0 | `eaf8cdcf` | pass | merge delta |
| `validate_icarus` | 5240 | 39.8 | `3e1a10d7` | pass | merge delta |
| `validate_icarus_c2` | 8400 | 17.4 | `3e1a10d7` | pass | PR |
| `validate_inventory_fx` | 8017 | 7.2 | `3e1a10d7` | pass | PR |
| `validate_item_callers` | 6013 | 1.3 | `3e1a10d7` | pass | PR |
| `validate_items_ui` | 8517 | 10.7 | `3e1a10d7` | pass | PR |
| `validate_login_world` | 1200 | 4.0 | `3e1a10d7` | pass | merge delta |
| `validate_map_polish` | 876 | 0.6 | `eaf8cdcf` | pass | merge delta |
| `validate_meshdraw` | 14619 | 79.0 | `3e1a10d7` | pass | merge delta |
| `validate_model_edge` | 954 | 149.2 | `3e1a10d7` | pass | merge delta |
| `validate_model_light` | 1433 | 7.5 | `3e1a10d7` | pass | merge delta |
| `validate_movement` | 6614 | 57.0 | `eaf8cdcf` | pass | PR |
| `validate_object_render` | 1984 | 4.0 | `3e1a10d7` | pass | merge delta |
| `validate_path` | 4719 | 31.5 | `3e1a10d7` | pass | merge delta |
| `validate_render_effects10` | 154 | 0.4 | `3e1a10d7` | pass | merge delta |
| `validate_render_effects11` | 176 | 0.3 | `3e1a10d7` | pass | merge delta |
| `validate_render_effects12` | 64 | 0.3 | `3e1a10d7` | pass | merge delta |
| `validate_render_effects13` | 180 | 0.6 | `3e1a10d7` | pass | merge delta |
| `validate_render_effects14` | 660 | 1.5 | `3e1a10d7` | pass | merge delta |
| `validate_render_effects15` | 509 | 1.0 | `3e1a10d7` | pass | merge delta |
| `validate_render_effects16` | 424 | 2.7 | `eaf8cdcf` | pass | PR |
| `validate_render_effects17` | 618 | 7.5 | `eaf8cdcf` | pass | PR |
| `validate_render_effects18` | 540 | 1.4 | `3e1a10d7` | pass | merge delta |
| `validate_render_effects19` | 400 | 1.0 | `3e1a10d7` | pass | merge delta |
| `validate_render_effects20` | 148 | 0.3 | `3e1a10d7` | pass | merge delta |
| `validate_render_effects21` | 267 | 0.4 | `3e1a10d7` | pass | merge delta |
| `validate_render_effects22` | 202 | 6.0 | `3e1a10d7` | pass | merge delta |
| `validate_render_effects23` | 1174 | 7.0 | `3e1a10d7` | pass | merge delta |
| `validate_render_effects24` | 226 | 2.2 | `eaf8cdcf` | pass | PR |
| `validate_render_effects25` | 202 | 9.5 | `eaf8cdcf` | pass | PR |
| `validate_render_effects26` | 348 | 10.1 | `eaf8cdcf` | pass | PR |
| `validate_render_effects27` | 424 | 1.1 | `3e1a10d7` | pass | merge delta |
| `validate_render_effects28` | 630 | 1.4 | `3e1a10d7` | pass | merge delta |
| `validate_render_effects32` | 1723 | 0.8 | `5c0dec22` | pass | PR |
| `validate_render_effects7` | 596 | 1.9 | `3e1a10d7` | pass | merge delta |
| `validate_render_effects9` | 304 | 0.9 | `3e1a10d7` | pass | merge delta |
| `validate_render_worlds_a` | 9000 | 13.6 | `3e1a10d7` | pass | merge delta |
| `validate_terrain` | 583500 | 409.1 | `3e1a10d7` | pass | merge delta |
| `validate_terrain_remaining` | 2147 | 4.7 | `3e1a10d7` | pass | merge delta |
| `validate_viewport_monsters` | 1963 | 12.6 | `3e1a10d7` | pass | merge delta |
| `validate_world_fidelity` | 200 | 0.2 | `3e1a10d7` | pass | merge delta |
| `validate_world_light_name` | 304 | 0.3 | `3e1a10d7` | pass | merge delta |
| `validate_world_tile_folder` | 5700 | 24.3 | `3e1a10d7` | pass | merge delta |
| `validate_worlds_121` | 4000 | 5.4 | `3e1a10d7` | pass | merge delta |
| `validate_worlds_after` | 13424 | 8.9 | `3e1a10d7` | pass | merge delta |
| `validate_worlds_after2` | 32216 | 19.8 | `3e1a10d7` | pass | merge delta |
| `validate_worlds_after3` | 10212 | 15.1 | `3e1a10d7` | pass | merge delta |
| `validate_worlds_after4` | 9181 | 16.6 | `3e1a10d7` | pass | merge delta |
| `validate_worlds_after5` | 6000 | 13.5 | `3e1a10d7` | pass | merge delta |
| `validate_worlds_after6` | 7300 | 56.5 | `3e1a10d7` | pass | PR |
| `validate_worlds_b` | 4000 | 4.6 | `3e1a10d7` | pass | merge delta |
| `validate_worlds_d` | 2400 | 4.9 | `3e1a10d7` | pass | merge delta |
| `validate_worlds_e` | 4840 | 21.2 | `3e1a10d7` | pass | merge delta |
| `validate_worlds_f` | 1818 | 0.4 | `3e1a10d7` | pass | merge delta |
| `validate_worlds_fog` | 4044 | 5.9 | `eaf8cdcf` | pass | PR |
| `validate_worlds_g` | 6000 | 7.7 | `3e1a10d7` | pass | merge delta |
| `validate_worlds_g2` | 2657 | 4.5 | `3e1a10d7` | pass | merge delta |
| `validate_worlds_g3` | 4000 | 3.3 | `3e1a10d7` | pass | merge delta |
| `validate_worlds_h` | 6000 | 6.9 | `3e1a10d7` | pass | merge delta |
| `validate_worlds_i` | 6000 | 7.7 | `3e1a10d7` | pass | merge delta |
| `validate_worlds_inner` | 4000 | 2.9 | `3e1a10d7` | pass | merge delta |
| `validate_worlds_inner2` | 5000 | 3.3 | `3e1a10d7` | pass | merge delta |
| `validate_worlds_inner3` | 8000 | 6.8 | `3e1a10d7` | pass | merge delta |
| `validate_worlds_inner4` | 8000 | 4.8 | `3e1a10d7` | pass | merge delta |
| `validate_worlds_j` | 6000 | 3.9 | `3e1a10d7` | pass | merge delta |
| `validate_worlds_k` | 6000 | 6.0 | `3e1a10d7` | pass | merge delta |
| `validate_worlds_karutan` | 3000 | 3.7 | `3e1a10d7` | pass | merge delta |
| `validate_worlds_n` | 13000 | 10.2 | `3e1a10d7` | pass | merge delta |
| `validate_worlds_o` | - | 10.6 | `3e1a10d7` | pass | merge delta |
| `validate_worlds_p` | 10000 | 5.0 | `3e1a10d7` | pass | merge delta |
| `validate_worlds_p2` | 6000 | 3.1 | `3e1a10d7` | pass | merge delta |
| `validate_worlds_q` | 11000 | 7.3 | `3e1a10d7` | pass | merge delta |
| `validate_worlds_q2` | 4000 | 4.3 | `3e1a10d7` | pass | merge delta |
| `validate_worlds_r` | 12000 | 5.1 | `3e1a10d7` | pass | merge delta |
| `validate_worlds_r2` | 9000 | 4.3 | `3e1a10d7` | pass | merge delta |
| `validate_worlds_raklion` | 3000 | 4.7 | `3e1a10d7` | pass | merge delta |
| `validate_worlds_s` | 11000 | 9.3 | `3e1a10d7` | pass | merge delta |
| `validate_worlds_s2` | 10000 | 12.3 | `3e1a10d7` | pass | merge delta |
| `validate_worlds_s3` | 22000 | 25.1 | `3e1a10d7` | pass | merge delta |
| `validate_worlds_slots` | 18999 | 30.2 | `3e1a10d7` | pass | merge delta |
| `validate_worlds_slots2` | 33000 | 47.3 | `3e1a10d7` | pass | merge delta |
| `validate_worlds_slots3` | 36000 | 40.0 | `3e1a10d7` | pass | merge delta |

Steward validators: validate_actor_composites,validate_actor_monsters,validate_actor_recipes,validate_app_polish4,validate_audio_callers,validate_audio_combat,validate_audio_domains,validate_audio_items,validate_audio_objects,validate_audio_objects4,validate_charsel_items,validate_icarus_c2,validate_inventory_fx,validate_item_callers,validate_items_ui,validate_movement,validate_render_effects16,validate_render_effects17,validate_render_effects24,validate_render_effects25,validate_render_effects26,validate_render_effects32,validate_worlds_after6,validate_worlds_fog

## Limits and next lane

Summon actor construction/lifetime and ground subtype 3, Fire Breath's 0x8001/0
and Crescent's 0x49e/0 remain absent. Defense's held-input lifetime and shield
body are unproved. General Death Stab links, buff equipment/presence services,
full shared-client RNG/pool/time phase and original GPU comparisons remain open.
Swell Life, Blood Storm, charge/child and target ice belong to EFFECTS-031.
Authored appearance inputs never grant eligibility, power, mana, cooldown,
damage, server keys or target state. Skill 47/stale learned capacity stay refused.
No actor, item table, world, Muun, UI/audio or particle/joint/effect consumer file is edited.
No protection, live client, owner Wine app, README or installed-app work occurs.

## Delivery

Ready for steward after final publication and queue entry.
Pure caller source inputs remain `8965554f`; native admission is `7e298c4d`.
The row table names each tested commit; subsequent changes are documentation only.
The PR targets main. Finish every doc/push before the one ready-prs entry, then
push nothing more. Remove this lane's scratch, renders, ignored builds,
worktree and local branch; retain the remote PR branch. No new private input
needs retaining. Local paths before cleanup are the matching
`~/Documents/MTM/mu-mac-tools/native/scratch/render-effects-032/` and
`renders/render-effects-032/` directories.
