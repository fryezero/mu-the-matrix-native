# RENDER-EFFECTS-031

Final selected verification is in progress. The steward owns the combined gate and merge.
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
not rerun. The final new-row baseline is rerun without mutants after the sample correction.

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

| Clock | Mean RGB error /255, before to after | Off >24, before to after |
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
bundle or data copy was changed. No live client, protection, network, account, character power, audio,
UI, Muun producer, item tables, world producer or README work was done.

## Selected validation

Results, exact tested commits and Steward validators are appended after the selected runs finish.
The private native selection is 160 work items, so **8d reduced** runs nine focused modules, including
all five hosts that reference `MU_WORLD_PT_BITMAPS`, the changed skill modules and native particles/renderer.
All three conservative validator fallbacks are retained. Only the new validator's controls are compiled.


The other 76 selected rows pass at `1d997aded66c58ce87d89e66948c2cfd1a981240`, **742.521 s** command wall, jobs 2, private cache enabled, no optional mutants.

| Validator | Reported checks | Wall s |
|---|---:|---:|
| `validate_actor_composites` | 1427 | 6.5 |
| `validate_actor_recipes` | 1669 | 86.6 |
| `validate_app_polish1` | 752 | 25.3 |
| `validate_app_polish4` | 10485 | 28.4 |
| `validate_audio_callers` | 5528 | 7.1 |
| `validate_audio_combat` | 19548 | 51.9 |
| `validate_audio_domains` | 2544 | 37.8 |
| `validate_audio_items` | 3000 | 5.2 |
| `validate_audio_objects` | 4000 | 2.8 |
| `validate_charsel_items` | 8817 | 6.9 |
| `validate_icarus` | 5240 | 50.9 |
| `validate_icarus_c2` | 8400 | 33.4 |
| `validate_inventory_fx` | 8017 | 6.1 |
| `validate_item_callers` | 6013 | 1.1 |
| `validate_item_effects` | 1500 | 1.5 |
| `validate_items_ui` | 8517 | 9.8 |
| `validate_joints` | 180 | 2.2 |
| `validate_meshdraw` | 14619 | 72.1 |
| `validate_model_edge` | 954 | 145.2 |
| `validate_model_light` | 1433 | 7.7 |
| `validate_movement` | 6614 | 69.2 |
| `validate_particles` | 407 | 1.5 |
| `validate_render_effects` | 660 | 1.2 |
| `validate_render_effects10` | 154 | 0.6 |
| `validate_render_effects11` | 176 | 0.3 |
| `validate_render_effects12` | 64 | 0.4 |
| `validate_render_effects13` | 180 | 0.4 |
| `validate_render_effects14` | 660 | 1.1 |
| `validate_render_effects15` | 509 | 0.6 |
| `validate_render_effects16` | 424 | 2.8 |
| `validate_render_effects17` | 618 | 6.2 |
| `validate_render_effects18` | 540 | 0.9 |
| `validate_render_effects19` | 400 | 0.7 |
| `validate_render_effects20` | 148 | 0.2 |
| `validate_render_effects21` | 267 | 0.3 |
| `validate_render_effects22` | 202 | 5.4 |
| `validate_render_effects23` | 1174 | 7.0 |
| `validate_render_effects24` | 226 | 2.6 |
| `validate_render_effects25` | 202 | 8.3 |
| `validate_render_effects26` | 348 | 7.5 |
| `validate_render_effects27` | 424 | 1.0 |
| `validate_render_effects28` | 630 | 1.3 |
| `validate_render_effects3` | 720 | 2.1 |
| `validate_render_effects30` | 452 | 0.3 |
| `validate_render_effects4` | 1920 | 12.7 |
| `validate_render_effects5` | 1190 | 6.3 |
| `validate_render_effects6` | 1000 | 3.4 |
| `validate_render_effects7` | 596 | 3.4 |
| `validate_render_effects9` | 304 | 2.1 |
| `validate_render_worlds_a` | 9000 | 24.2 |
| `validate_skill_fx` | 660 | 2.4 |
| `validate_terrain` | 583500 | 456.7 |
| `validate_terrain_remaining` | 2147 | 8.8 |
| `validate_world_particle_consumers` | 900 | 1.3 |
| `validate_worlds_121` | 4000 | 3.4 |
| `validate_worlds_after` | 13424 | 10.2 |
| `validate_worlds_after2` | 32216 | 18.6 |
| `validate_worlds_after3` | 10212 | 5.2 |
| `validate_worlds_after4` | 9181 | 9.4 |
| `validate_worlds_after5` | 6000 | 6.7 |
| `validate_worlds_after6` | 7300 | 47.6 |
| `validate_worlds_d` | 2400 | 5.5 |
| `validate_worlds_e` | 4840 | 21.6 |
| `validate_worlds_f` | 1818 | 0.6 |
| `validate_worlds_fog` | 4044 | 6.1 |
| `validate_worlds_g3` | 4000 | 3.5 |
| `validate_worlds_inner` | 4000 | 2.2 |
| `validate_worlds_inner2` | 5000 | 2.6 |
| `validate_worlds_inner3` | 8000 | 4.8 |
| `validate_worlds_karutan` | 3000 | 2.5 |
| `validate_worlds_l` | 1260 | 1.9 |
| `validate_worlds_m` | 1080 | 1.3 |
| `validate_worlds_raklion` | 3000 | 2.5 |
| `validate_worlds_slots` | 18999 | 20.3 |
| `validate_worlds_slots2` | 33000 | 19.8 |
| `validate_worlds_slots3` | 36000 | 20.4 |

The new full baseline and boundary follow-up are recorded above; its final no-mutant registry baseline is still pending.

Steward validators: validate_item_effects,validate_joints,validate_meshdraw,validate_model_edge,validate_model_light,validate_movement,validate_particles,validate_skill_fx,validate_terrain,validate_terrain_remaining,validate_render_worlds_a,validate_icarus,validate_icarus_c2,validate_worlds_d,validate_worlds_e,validate_worlds_f,validate_audio_callers,validate_audio_combat,validate_render_effects,validate_render_effects3,validate_render_effects4,validate_render_effects5,validate_render_effects6,validate_render_effects7,validate_render_effects9,validate_render_effects10,validate_render_effects11,validate_render_effects12,validate_world_particle_consumers,validate_audio_domains,validate_audio_items,validate_worlds_l,validate_worlds_m,validate_worlds_after,validate_worlds_g3,validate_worlds_after2,validate_worlds_after3,validate_worlds_after4,validate_worlds_after5,validate_worlds_after6,validate_app_polish1,validate_app_polish4,validate_render_effects13,validate_render_effects14,validate_worlds_slots,validate_worlds_slots2,validate_worlds_slots3,validate_worlds_121,validate_worlds_raklion,validate_worlds_karutan,validate_render_effects15,validate_render_effects16,validate_worlds_fog,validate_render_effects17,validate_item_callers,validate_inventory_fx,validate_render_effects18,validate_render_effects19,validate_render_effects20,validate_render_effects21,validate_render_effects22,validate_render_effects23,validate_render_effects24,validate_worlds_inner,validate_render_effects27,validate_render_effects25,validate_actor_recipes,validate_charsel_items,validate_render_effects26,validate_actor_composites,validate_worlds_inner2,validate_audio_objects,validate_render_effects28,validate_render_effects30,validate_worlds_inner3,validate_items_ui,validate_render_effects31.

## WIP

Done: implementation, original/native fixtures, scene/fidelity measurements, 69 controls across the full run and focused recheck, and 76 affected private validators.

Left: focused portable repair rerun, 8d reduced, audit, final new-row baseline, latest-main integration, final documentation, PR, ready line and cleanup.

The first portable run completes 1,822 tests: 1,498 passed, 319 skipped, four failures and one error,
406.540 s command / 353.2 s test wall. All five are old admission expectations: particle Spark03/2,
joint spark/5, the Remain callback whitelist, worlds-M clouds/26 and Imperial Guardian's spark count.
Update the two admission tests with all new positive pairs and adjacent unsupported subtypes.
The Remain host checks original owner/scale/position arguments and keeps its missing-hook refusal;
the Guardian host requires positive groups of four spark joints with the original callback arguments.
Production code and validator targets are unchanged. The five affected suites pass on focused rerun: 43 tests, 39 passed/four expected skips, 3.836 s.
The reduced private run grows to twelve real modules to include these three changed world hosts.
The first private attempt reports 37 entries in 165.330 s: 35 passed, one stale 97-slot bitmap assertion,
and a mistaken `test_native_renderer` module path. Update the exact vector to 99 slots while retaining
Map_Smoke1's world-specific zero; run the corrected fires assertion and actual `test_native_renderchar`.
Those 25 tests pass in 13.052 s. Across the twelve real modules, all 60 unique tests pass.
The corrected full new-validator baseline passes 66,051 checks at `26abb75d`, 255.993 s without mutants.
Its revised sample contains 62,185 original executions and 3,815 C head-removal checks, plus the same
51 native/census/loader checks.

Main has advanced to AUDIO-004 `2b0b2716`, #388. Merge and rerun only the incoming compiled-input overlap;
all production consumer code, bitmap/model registrations and previously successful control targets remain unchanged.

Next: wait for the existing foreground check queue, then run the corrected new-row baseline without mutants.
