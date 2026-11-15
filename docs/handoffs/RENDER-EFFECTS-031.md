# RENDER-EFFECTS-031

PR-ready: implementation, selected verification, private checks, render proofs and audit pass.
The steward owns the combined gate and merge.
Branch `codex/render-effects-031` began at main `b7dfd2ed`, #387. No subagents or full lane gate.

## Implemented boundary

Existing producers can now use 22 additional consumer pairs:

- Eleven particles: `0x801c/3,4,7`, `0x7f89/7,10,16,26`, `0x7f42/7,12`, `0x802a/1`, `0x7f26/2`.
- Six joints: Remain `0x7f7d/8,9,10`, old spark `0x7fd5/5`, Swell spirit `0x7fd3/2` and child flare `0x7f78/2`.
- Five effects: Swell ground `0x7f84/4`, Penetration charge `0x7fd0/0`, word4 emitter `0x7f42/6`, transition `0x47a/0,1`.

[Particle instructions and loaders](../research/client-particles.md#render-effects-031-consumers-already-requested-by-worlds-and-skills) and
[joint/effect instructions and limits](../research/client-joints.md#render-effects-031-remain-old-spark-and-swell-life-consumers).
The high-ID effects have no own body draw. The transition uses the original DarkLordSkill model.
Native world and combat adapters preserve the charge OBJECT as its Spark03 child owner.
Null/out-of-range map owners remain counted refusals for the owner-dependent particles.

Pool caps stay 4,096 particles, 500 joints, 200 effects and 1,000 sprites. Existing private RNG/counter
sources and phases remain in place; newly admitted routines consume their original calls from those
streams. These are private native streams, not a reconstruction of the client's shared global RNG.
Bitmap count grows 97 to 99, model registrations 18 to 19. Leading bitmap indices stay stable;
Fire06 and the rain tail shift by two. The old frozen item census stays **110 programs / 37 pairs**,
all supported. The separate selected world/skill census has **25 pairs: 22 admitted / 3 refused**.
Neither denominator claims every case in the original switch.

## Original and native proof

At `d7aaa0d5`, the full new proof passes **66,051 focused checks**, zero mismatches. Accounting:
62,118 original-machine executions, 3,882 C head-removal checks, 22 native fixture rows,
26 census checks and three static original loader checks. Constructor/mover comparisons include
record fields, ordered child calls and RNG counts. Particle/joint draw comparisons include wrappers,
textures, quads, colors, rotation and UVs. Effect draw dispatch proves the original RenderObject/no-body
boundary. Existing comparison tolerances and defined-byte masks are unchanged.

The full control run takes **284.976 s**. It catches 68 of 69 compiled controls; the life-10 control
has no live, in-range record at exactly life 10 in that sample. A deterministic boundary record fixes
that coverage gap. The **1,371-check / one-control follow-up** takes **6.348 s**, catches that remaining
control in 16 cases and has zero original stops. Production C is unchanged. Successful controls are
not rerun. The corrected full baseline passes without mutants at `26abb75d`, 255.993 s. It contains
62,185 original-machine executions, 3,815 C head-removal checks and the same 51 native/census/loader checks.
The full row passes again after the main integrations; see the final table.

Native fixtures exercise each new particle and joint through actual pool admission, bitmap routing,
raster output and retirement. Three effect pairs correctly have no own body draw; their child/no-op
paths are checked. Both transition subtypes have synthetic model/raster controls and installed-model
proofs. Pool exhaustion retains the existing caps and particle constructor-before-overflow RNG behavior.
The bitmap fixtures use distinct grayscale images; particle raster controls recenter geometry and
supply a camera-space light control where required. Those transforms are not original-world placements.
The flare fixture waits for its original life-25 rise and uses an oblique view to expose its ribbon.

The installed transition test passes in **1.917 s**. Exported native proofs contain 24 rows, including
both installed transition variants with 448 raster fragments each. All new consumers have a rendered
fixture. The Swell ring, charge sprites, Remain effects, Trials mist/flame and transition model were
visually inspected. No original GPU pixel equivalence or whole-world fidelity is claimed.

## Scene refusals and output

Installed game data, demo names only. Skill scenes use Lorencia tile 182,127, DemoTarget at 184,127,
960x600, frames 0..90, one frame-2 cast and frame-3 stop, with every intermediate frame drawn.

| Scene | Before | After |
|---|---:|---:|
| Remain default capture, 25 steps | 4 accepted / 3 refused particles | 7 / 0 |
| Remain tile 111,90, 61 steps, draw_all | 183 accepted / 64 refused particles | 247 / 0 |
| Authored Trials, 61 steps, draw_all | 18 accepted / 22 refused particles | 40 / 0 |
| Swell Life 48, direct and total combat refusals | 38 | 0 |
| Penetration 52 | 2 | 1 |
| Alias 416 | 2 | 1 |
| Blood Storm 344 | 1 | 1 |

Swell creates 72 joints including 36 children and 756 sprites. Penetration and 416 each accept 33 charge
particles and 33 sprites, with zero legacy particle refusals, then retire. Every skill scene has zero sent
requests, one unsent request, zero hits/kills and unchanged target HP. No authoritative state is supplied.
The same Aida close-up stays unchanged: zero particle/joint refusals before and after. Some added rare
world pairs are exercised by the per-pair native fixtures rather than these finite world runs.

Trials has no original captured placement/image reference. Its plain version-0 records are types
3/49/53 at 12850,12850,223.5; 13050,12850,223.5; 12850,13050,223.5. Angles zero, scale one,
hero tile 128,128. All three models load and draw. This fixture is authored, not an original capture.
Scene counts are actual cumulative counts; new accepted routines can change later RNG consumption and
child requests. They are not a promise that the complete request stream is frozen.

## Identity and fidelity

Both world binaries were explicitly built with `make -C native -j4 world` before their sweeps:

- Before `e341fc2000d2e7f035f1e1814ca5384231389c8e7409ed20557643b0485108d7`.
- After `151d54f4df743061c705bcc72615ec808e5dfae4e2398fd9e348abcbadaefdfe`.

The 14-view October and 32-view DATA-ACQ-002 default sweeps use 640x400, 25 frames, save 0/24,
no draw_all and the default clock. **91/92 PNGs and 92/92 OBJECT/light dumps are byte-identical**.
Only Remain frame 24 changes. All 45 unaffected reports differ only in the bitmap-vector addition;
Remain also gains the expected particle/RNG/counter fields. This is not a claim that all JSON is identical.
Path comparison removes only output `png` and `fidelity_dump` paths.

The after sweep plus close-ups and skills takes **90.570 s**: default October 18.651 s, DATA-ACQ 51.692 s,
Aida close-up 6.014 s, Remain close-up 3.989 s and four skills 10.133 s. Skill PNG identity is 18/24;
Swell changes four saved frames, Penetration/416 one each, Blood Storm none. Aida close-up stays 2/2;
Remain close-up changes its final frame. Initial before driver errors repeated default renders while
fixing manifest paths; the final completed before set is retained. Its last run reports 96.338 s, with
retained earlier output. It is not presented as a clean one-pass baseline timing.

Full-resolution Remain reference, 1722x1048, unchanged masks and 25 steps:

| Clock | Mean RGB error, 0..255, before to after | Off >24, before to after |
|---|---|---|
| Default | 6.064 to 6.065 | .0563 to .0563 |
| Captured | 6.067 to 6.067 | .0564 to .0564 |

Both clocks match all 2,121 objects with zero missing/extra. The small default increase is retained.
Extra native renders, both-clock reference comparisons and authored Trials take **15.151 s** including
host compilation; **12.965 s** for the scene portion. Reference processing writes scalar scores only,
without copying an original-name PNG. No new original capture was made.

## Remaining limits

Blood Storm `0x583/0` and child `0x584/0` remain refused. Lifetime 70, child and sound in its static
constructor do not validate its lifecycle. The child reads owner byte +0x3b at `0x014a1b47`, outside the
declared owner view. Penetration child `0x46c/0` still needs its owner action/live/position lifecycle.
Optional target ice remains unwired and is not counted as a newly admitted consumer.

The frozen Native Data copy lacks `DarkLordSkill.bmd`, `Flame01.OZJ` and `water.OZJ`. Full read-only game
data supplies them for these proofs. A later data-refresh lane must include those assets; no installed
bundle or data copy was changed. No lane-authored live-client, protection, network, account, character-power, audio, UI, Muun-producer,
item-table, world-producer or README changes were made. Incoming main changes are recorded below.

## Main integration and final replay

AUDIO-004 main `2b0b2716` merges as `ae0374dd`. Shared conflicts retain both lane status lines
and both complete validator rows. Its 50-row overlap passes at `7cffa6fa`, 840.572 s execution;
incoming portable checks pass 1,764 tests, 1,448 passed / 316 expected skips, zero failures/errors,
448.606 s execution / 392.3 s test wall. Thirteen private modules pass 67 tests in 169.483 s.
Its 89.141 s replay preserves all 120 prior after PNGs and 96 OBJECT/light dumps. The binary is
`bd558fc4b3028a42a7f534f775d3854192beda69c6b8741a977aa8726ac34e94`.

ACTORS-005 #389 and INNER-004 #390 main `4babc900` merge cleanly as `bfb2a6bb`. The current selection
is 80 rows: the prior 77 plus `validate_actor_monsters`, `validate_audio_objects4`, `validate_worlds_inner4`.
The 64-row compiled overlap plus those three rows passes at `9cb0b2c2`, 904.746 s. Thirteen prior
rows have unchanged compiled inputs. Build and current/overlap selectors take 300.738 s. No authored
consumer C, bitmap/model registration or successful control target changes in either integration.

Latest incoming portable: 537.788 s execution, 120.008 s resource wait.

Latest reduced private: 240.257 s execution, 0.002 s resource wait.

Latest replay: 88.754 s execution, 120.008 s resource wait.

Latest audit: 47.615 s execution, 0.003 s resource wait.

The latest core portable result is **1,789 tests: 1,467 passed / 322 expected skips**, zero failures/errors,
413.1 s runner wall (537.788 s complete command). The fifteen-module private run passes **70 tests**.
The ACTORS/INNER replay preserves **118/120 PNGs and 96/96 OBJECT/light dumps**. Only the two Kanturu-37
PNGs change, from incoming INNER-004's alpha seam; all Remain, close-up and skill outputs are identical.
Its rebuilt world binary is `147fecd58d9fe512d28d8a846f1afe27dedcf758b9dd64acdc3cda7ec9fc9a41`.
Relative to the original b7dfd2ed baseline, the final default tour retains 89/92 PNGs and all 92 dumps:
one Remain frame is this lane's new mist, two Kanturu frames are the incoming alpha change.

UI-WINDOWS-003 #391 main `a95880c4` merges as `62e6a250`. It changes UI, input, tests and docs, with no
consumer/core changes. The rebuilt eight-row overlap and focused UI tests pass; successful consumer
controls are not repeated. Build and overlap selectors take 114.207 s. Final UI replay preserves all
**120/120 PNGs and 96/96 OBJECT/light dumps** versus the preceding ACTORS/INNER build. Final binary:
`57ec477123776f34161091a0f8fca96df9b351253a084fdf89d21b33d8db4fb6`.

UI overlap, eight rows: 75.656 s execution, 360.044 s resource wait.

UI affected portable: 462.925 s execution, 0.003 s resource wait.

UI reduced private: 8.986 s execution, 240.025 s resource wait.

UI replay: 124.741 s execution, 0.002 s resource wait.

UI portable: 6 suites, 1506 tests, 1211 passed, 295 skipped, 0 failures, 0 errors; 0 failed suite(s), 387.9 s runner wall. UI private: 13 tests, 12 passed / 1 expected skips, 8.948 s unittest wall.

The final staged audit result and wall time are recorded in the PR validation.

Execution wall times exclude the separately recorded resource-guard waits. Every heavy command is
nice 10; builds use at most four jobs and validator/test runners at most two. No full lane gate runs.

## Selected validation

The first 76 selected private rows pass at `1d997ade`, 742.521 s. The corrected new row and later
main-overlap passes bring the final selection to 80 green rows. The table gives each row's latest
actual tested commit, reported check count and execution wall. Optional mutants are disabled in
these row runs; the 69 new controls are accounted for separately above. Conservative movement,
actor-recipe and actor-composite fallbacks remain in the selection.

The first portable run reports 1,822 tests: 1,498 passed / 319 expected skips, four failures and one error,
406.540 s complete command / 353.2 s runner wall. Its five stale admission expectations are: Spark03/2, spark joint/5, the Remain
callback whitelist, clouds/26 and Imperial Guardian's spark count. All five affected suites pass the
focused repair run, 43 tests / 39 passed / four expected skips, 3.836 s. New positive pairs and adjacent
unsupported subtypes are asserted. Original callback arguments and missing-hook refusals remain checked.
The initial private run takes 165.330 s and reports 35 passes, one failure and one import error in 37 entries.
It finds an old 97-slot vector and a mistaken renderer module path; the corrected
99-slot vector retains Map_Smoke1's world-specific zero. The corrected fires assertion and actual
renderchar module pass 25 tests in 13.052 s. Twelve real modules then have 60 unique green tests.
Later integration runs execute the corrected modules together.

**8d reduced:** the native private selections exceed 40 work items, so focused modules cover the changed
skill/particle tests, all five hosts using `MU_WORLD_PT_BITMAPS`, renderchar, the changed world hosts and
incoming audio/actor/alpha hosts. The latest run has fifteen modules. Canonical environment is sourced
from `~/Documents/MTM/mu-mac-tools/native/private-env.sh`, from the repository root.

| Validator | Reported checks | Wall s | Tested commit |
|---|---:|---:|---|
| `validate_actor_composites` | 1427 | 10.3 | `9cb0b2c2` |
| `validate_actor_monsters` | 1437 | 53.5 | `9cb0b2c2` |
| `validate_actor_recipes` | 1669 | 94.7 | `9cb0b2c2` |
| `validate_app_polish1` | 752 | 21.4 | `48d91b76` |
| `validate_app_polish4` | 10485 | 28.7 | `48d91b76` |
| `validate_audio_callers` | 5528 | 5.8 | `48d91b76` |
| `validate_audio_combat` | 19548 | 40.5 | `9cb0b2c2` |
| `validate_audio_domains` | 2544 | 25.4 | `48d91b76` |
| `validate_audio_items` | 3000 | 3.9 | `48d91b76` |
| `validate_audio_objects` | 4000 | 4.8 | `9cb0b2c2` |
| `validate_audio_objects4` | 10093 | 12.5 | `9cb0b2c2` |
| `validate_charsel_items` | 8817 | 8.5 | `9cb0b2c2` |
| `validate_icarus` | 5240 | 31.2 | `9cb0b2c2` |
| `validate_icarus_c2` | 8400 | 22.5 | `9cb0b2c2` |
| `validate_inventory_fx` | 8017 | 9.5 | `9cb0b2c2` |
| `validate_item_callers` | 6013 | 2.2 | `9cb0b2c2` |
| `validate_item_effects` | 1500 | 1.5 | `1d997ade` |
| `validate_items_ui` | 8517 | 11.2 | `9cb0b2c2` |
| `validate_joints` | 180 | 2.2 | `1d997ade` |
| `validate_meshdraw` | 14619 | 70.5 | `9cb0b2c2` |
| `validate_model_edge` | 954 | 156.7 | `9cb0b2c2` |
| `validate_model_light` | 1433 | 5.6 | `9cb0b2c2` |
| `validate_movement` | 6614 | 52.4 | `48d91b76` |
| `validate_particles` | 407 | 1.5 | `1d997ade` |
| `validate_render_effects` | 660 | 1.2 | `1d997ade` |
| `validate_render_effects10` | 154 | 0.5 | `9cb0b2c2` |
| `validate_render_effects11` | 176 | 0.4 | `9cb0b2c2` |
| `validate_render_effects12` | 64 | 0.4 | `9cb0b2c2` |
| `validate_render_effects13` | 180 | 0.6 | `9cb0b2c2` |
| `validate_render_effects14` | 660 | 2.4 | `9cb0b2c2` |
| `validate_render_effects15` | 509 | 1.0 | `9cb0b2c2` |
| `validate_render_effects16` | 424 | 3.5 | `48d91b76` |
| `validate_render_effects17` | 618 | 8.0 | `9cb0b2c2` |
| `validate_render_effects18` | 540 | 1.6 | `9cb0b2c2` |
| `validate_render_effects19` | 400 | 1.0 | `9cb0b2c2` |
| `validate_render_effects20` | 148 | 0.3 | `9cb0b2c2` |
| `validate_render_effects21` | 267 | 0.4 | `9cb0b2c2` |
| `validate_render_effects22` | 202 | 6.8 | `9cb0b2c2` |
| `validate_render_effects23` | 1174 | 8.1 | `9cb0b2c2` |
| `validate_render_effects24` | 226 | 3.2 | `9cb0b2c2` |
| `validate_render_effects25` | 202 | 13.3 | `9cb0b2c2` |
| `validate_render_effects26` | 348 | 10.0 | `9cb0b2c2` |
| `validate_render_effects27` | 424 | 2.5 | `9cb0b2c2` |
| `validate_render_effects28` | 630 | 2.5 | `9cb0b2c2` |
| `validate_render_effects3` | 720 | 2.1 | `1d997ade` |
| `validate_render_effects30` | 452 | 0.3 | `1d997ade` |
| `validate_render_effects31` | 66051 | 288.6 | `9cb0b2c2` |
| `validate_render_effects4` | 1920 | 12.7 | `1d997ade` |
| `validate_render_effects5` | 1190 | 6.3 | `1d997ade` |
| `validate_render_effects6` | 1000 | 3.4 | `1d997ade` |
| `validate_render_effects7` | 596 | 2.4 | `9cb0b2c2` |
| `validate_render_effects9` | 304 | 0.8 | `9cb0b2c2` |
| `validate_render_worlds_a` | 9000 | 13.7 | `9cb0b2c2` |
| `validate_skill_fx` | 660 | 2.4 | `1d997ade` |
| `validate_terrain` | 583500 | 418.9 | `9cb0b2c2` |
| `validate_terrain_remaining` | 2147 | 6.3 | `9cb0b2c2` |
| `validate_world_particle_consumers` | 900 | 1.3 | `1d997ade` |
| `validate_worlds_121` | 4000 | 5.0 | `9cb0b2c2` |
| `validate_worlds_after` | 13424 | 14.3 | `9cb0b2c2` |
| `validate_worlds_after2` | 32216 | 23.9 | `9cb0b2c2` |
| `validate_worlds_after3` | 10212 | 8.1 | `9cb0b2c2` |
| `validate_worlds_after4` | 9181 | 25.5 | `9cb0b2c2` |
| `validate_worlds_after5` | 6000 | 12.9 | `9cb0b2c2` |
| `validate_worlds_after6` | 7300 | 78.8 | `9cb0b2c2` |
| `validate_worlds_d` | 2400 | 4.5 | `9cb0b2c2` |
| `validate_worlds_e` | 4840 | 16.8 | `9cb0b2c2` |
| `validate_worlds_f` | 1818 | 0.5 | `9cb0b2c2` |
| `validate_worlds_fog` | 4044 | 8.0 | `48d91b76` |
| `validate_worlds_g3` | 4000 | 5.9 | `9cb0b2c2` |
| `validate_worlds_inner` | 4000 | 4.2 | `9cb0b2c2` |
| `validate_worlds_inner2` | 5000 | 4.0 | `9cb0b2c2` |
| `validate_worlds_inner3` | 8000 | 6.9 | `9cb0b2c2` |
| `validate_worlds_inner4` | 8000 | 9.6 | `9cb0b2c2` |
| `validate_worlds_karutan` | 3000 | 3.9 | `9cb0b2c2` |
| `validate_worlds_l` | 1260 | 1.9 | `1d997ade` |
| `validate_worlds_m` | 1080 | 1.3 | `1d997ade` |
| `validate_worlds_raklion` | 3000 | 3.3 | `9cb0b2c2` |
| `validate_worlds_slots` | 18999 | 28.3 | `9cb0b2c2` |
| `validate_worlds_slots2` | 33000 | 27.5 | `9cb0b2c2` |
| `validate_worlds_slots3` | 36000 | 30.9 | `9cb0b2c2` |

Steward validators: validate_actor_composites,validate_actor_monsters,validate_actor_recipes,validate_app_polish1,validate_app_polish4,validate_audio_callers,validate_audio_combat,validate_audio_domains,validate_audio_items,validate_audio_objects,validate_audio_objects4,validate_charsel_items,validate_icarus,validate_icarus_c2,validate_inventory_fx,validate_item_callers,validate_item_effects,validate_items_ui,validate_joints,validate_meshdraw,validate_model_edge,validate_model_light,validate_movement,validate_particles,validate_render_effects,validate_render_effects10,validate_render_effects11,validate_render_effects12,validate_render_effects13,validate_render_effects14,validate_render_effects15,validate_render_effects16,validate_render_effects17,validate_render_effects18,validate_render_effects19,validate_render_effects20,validate_render_effects21,validate_render_effects22,validate_render_effects23,validate_render_effects24,validate_render_effects25,validate_render_effects26,validate_render_effects27,validate_render_effects28,validate_render_effects3,validate_render_effects30,validate_render_effects31,validate_render_effects4,validate_render_effects5,validate_render_effects6,validate_render_effects7,validate_render_effects9,validate_render_worlds_a,validate_skill_fx,validate_terrain,validate_terrain_remaining,validate_world_particle_consumers,validate_worlds_121,validate_worlds_after,validate_worlds_after2,validate_worlds_after3,validate_worlds_after4,validate_worlds_after5,validate_worlds_after6,validate_worlds_d,validate_worlds_e,validate_worlds_f,validate_worlds_fog,validate_worlds_g3,validate_worlds_inner,validate_worlds_inner2,validate_worlds_inner3,validate_worlds_inner4,validate_worlds_karutan,validate_worlds_l,validate_worlds_m,validate_worlds_raklion,validate_worlds_slots,validate_worlds_slots2,validate_worlds_slots3.

The eight UI-overlap rows use `48d91b76`; all other rows retain the tested commit shown above.
No changed-row mutants remain to run. A later steward integration needs only the rows whose compiled
inputs changed since the table's tested commit. Successful controls are not repeated.

Private inputs remain in their existing shared locations. Task-local scratch, renders and ignored build
reports are disposable; cleanup follows the final push and single ready-prs line. The remote branch
stays for the steward. No new private input is needed to reproduce these tests.
