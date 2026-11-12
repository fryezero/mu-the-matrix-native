# RENDER-ACTORS-003

## Result and census

PR-ready.

Two robot actor recipes now draw in authored fixtures: classes 625 and 626,
models `0x5bc` and `0x5bd`, using `Data/Item/iron_robot.bmd` and
`Data/Item/iron_robot_gold.bmd`. Their original constructor context is kind 1,
class byte 0, level zero, empty equipment, scales 1.1 and 0.6. The original
class-2 and class-6 action hooks do not apply to that context. They remain
excluded transformed-player behavior, with explicit original-instruction controls.

Branch `codex/render-actors-003`, base/latest main `d4af71dd`. Source checks are
at `eecd1774` unless stated below; subsequent changes are documentation only.
Offline/static only. No installed app, live client, network route, Muun module,
item generator, effect consumer or canonical actor placement was changed.

The complete 32-row table moves from 26 admitted / six refused to 28 admitted /
four refused. Both totals include the two unchanged loader controls. This is a
bounded constructor table, not whole-client coverage or spawnability evidence.

| Class | Before | After | Detail |
|---|---|---|---|
| 14 | admitted | admitted | existing recipe retained |
| 15 | admitted | admitted | existing recipe retained |
| 16 | admitted | admitted | existing recipe retained |
| 34 | admitted | admitted | existing recipe retained |
| 55 | admitted | admitted | existing recipe retained |
| 56 | admitted | admitted | existing recipe retained |
| 229 | admitted | admitted | existing loader control |
| 236 | admitted | admitted | existing recipe retained |
| 247 | admitted | admitted | existing recipe retained |
| 249 | admitted | admitted | existing recipe retained |
| 257 | admitted | admitted | existing loader control |
| 258 | admitted | admitted | existing recipe retained |
| 297 | admitted | admitted | existing recipe retained |
| 371 | admitted | admitted | existing recipe retained |
| 372 | admitted | admitted | existing recipe retained |
| 373 | admitted | admitted | existing recipe retained |
| 374 | refused | refused | companion lifetime refused |
| 375 | admitted | admitted | existing recipe retained |
| 378 | refused | refused | cloth/aura branch refused |
| 414 | admitted | admitted | existing recipe retained |
| 464 | admitted | admitted | existing recipe retained |
| 503 | admitted | admitted | existing recipe retained |
| 548 | admitted | admitted | existing recipe retained |
| 616 | admitted | admitted | existing recipe retained |
| 617 | refused | refused | startup file unresolved |
| 625 | refused | admitted | new iron_robot, kind 1/class byte 0, scale 1.1 |
| 626 | refused | admitted | new iron_robot_gold, kind 1/class byte 0, scale 0.6 |
| 642 | refused | refused | companion lifetime refused |
| 646 | admitted | admitted | existing recipe retained |
| 706 | admitted | admitted | existing recipe retained |
| 806 | admitted | admitted | existing recipe retained |
| 807 | admitted | admitted | existing recipe retained |

## Evidence and implementation

[Research sections 9 and 10](../research/client-actors.md#9-the-six-refused-rows-render-actors-003)
record exact addresses, methods and the four refusal limits. Pins are verified
through `Pin.read`: text `2bd5f2e9...3724`, image data `c985e2e6...672f`, trig flag
and math feature word. No opaque protection route is followed.

CreateCharacter's class-byte-zero store is executed with an incoming `0x16`,
independently of the zero-filled constructor stub. The original class nibble
helper and the robot action branch execute over 270 authored states, including
`0x12`/`0x16`, neighbouring actions, signed target state and the counter byte.
The whole RenderCharacter plan, startup file identity, generic RenderObjDraw
stream and production native loader are compared for the admitted recipes.

Classes 374/642 still require companion follow/pose/draw/destruction and owner
reuse after their now-extracted allocation callers. Class 378 still requires
its two cloth objects and aura behavior; its eight-case check ends before cloth
allocation. Class 617 still lacks a proved file registration. None is admitted
as a body-only approximation. The exact next routines are in the research note.

Shared-file edit: only the existing `validate_actor_recipes` row of
`scripts/validators.toml`, to register 1,669 checks and 25 mutants. No native
core/header/ABI, Makefile, pins, particle consumer or item table changed. Brief
6b review found no changed existing constant, struct field or table size; the
recipe and shared-renderer private modules are covered below.

## Checks

All commands run from the repository root, heavy jobs at nice 10, make at most
four jobs, runner jobs two, one heavy command at a time. Resource-limit waits
were observed. No full lane gate was run; the steward owns that gate.

| Check | Result | Wall |
|---|---|---:|
| Delivery root build at `315cc0d4` | pass | 0.66 s |
| Explicit delivery `make -C native -j4 world` | pass | 0.31 s |
| Affected private validators at `5d98283c` | 17 other rows pass; actor result superseded below | 279.7 s total |
| Corrected actor row with mutants at `eecd1774` | 1,669 checks, zero mismatches; 25/25 compiled mutants caught | 297.3 s |
| Portable affected suites at `315cc0d4` | 1,452 tests, 1,208 passed, 244 private-data skips, zero failures/errors | 503.6 s including selection; runner 429.4 s |
| Private 8d reduced at `315cc0d4` | 27/27, zero skips | 74.7 s |
| Three isolated GL scenes, empty control + both robots | pass; both actors visually inspected | 3.5 s |
| Default identity sweep, 46 captured views | 92 PNGs, 92 dumps and 46 reports byte-identical | 92.1 s |
| Nine extra-opener research probes | extracted 15 secondary-model loads, no native admission | 0.05 s |
| Final staged repository audit | 2,184 files, zero rejected | 22.8 s |
| Final documentation-consumer modules | 36 tests, 35 passed, one expected private-data skip | 9.1 s |

The initial affected actor row compared all 1,669 states successfully but failed
its expected-count metadata after the constructor-default check was added while
the runner held the older row. The corrected full row above is the final result.
No mutant escaped and no runtime fix was needed.

Actor families: recipes 36, whole RenderCharacter plans 840, kind gates 264,
robot hooks 270, companion caller controls 16, appearance-prefix controls eight,
equipment plans 11, generic body streams 168, constructor default stores two,
startup checks 16, native loads 34, native refusals four. The hook/companion/
prefix families execute original callers with named service recorders; they do
not claim to port the excluded downstream behavior or establish original pixels.

**8d reduced:** 156 selected work items include 149 native modules, exceeding
the cap of 40. The private run sources the canonical environment and covers
`native.tests.test_actor_recipes` and `native.tests.test_native_renderchar`.

## Renders and byte identity

The GL demos use world 0, DemoKnight at 128,124, DemoActor at 129,125, direction 5,
640x480, two frames, start clock 123456 ms, names hidden, no environment/particles.
Against the empty fixture, class 625 changes 4,376 pixels and class 626 changes
1,219. Both textured robot bodies were visually inspected. This is native fixture
proof, not original screenshot or live-motion equivalence.

The one-time default baseline was captured before source changes, 640x400,
without draw_all or live_time, 78.9 s. Each side explicitly rebuilds `mu-world`:

- Before SHA-256: `4954601057b7ee7976c787157b321703d40c65dba68c46901b08d22adb1be76c`.
- After SHA-256: `1be079965a22399f472ca6c7d0f657fa67b62e46b9a47ba6f6c5e7b100d34440`.

The hashes differ. The 14 October-22 and 32 DATA-ACQ-002 views retain all 230
file hashes. Only each report's output-directory prefix is normalized.
No default scene places either newly admitted actor.

## Steward validators

Steward validators: validate_actor_recipes, validate_audio_callers, validate_audio_combat, validate_audio_domains, validate_audio_items, validate_charsel_items, validate_icarus_c2, validate_inventory_fx, validate_item_callers, validate_meshdraw, validate_model_edge, validate_movement, validate_render_effects16, validate_render_effects17, validate_render_effects18, validate_render_effects19, validate_render_effects24, validate_render_effects25

The 17 rows below pass at `5d98283c`; their compiled inputs are unchanged at
`eecd1774` and delivery. The actor row passes at `eecd1774`, 297.3 s, including
its 25/25 mutants. Only that row needs mutants; they have already run once.
Environment: `. ~/Documents/MTM/mu-mac-tools/native/private-env.sh`.

| Validator | Wall |
|---|---:|
| `validate_audio_callers` | 4.4 s |
| `validate_audio_combat` | 17.1 s |
| `validate_audio_domains` | 19.5 s |
| `validate_audio_items` | 3.4 s |
| `validate_charsel_items` | 6.0 s |
| `validate_icarus_c2` | 12.8 s |
| `validate_inventory_fx` | 7.2 s |
| `validate_item_callers` | 1.5 s |
| `validate_meshdraw` | 55.6 s |
| `validate_model_edge` | 110.1 s |
| `validate_movement` | 47.6 s |
| `validate_render_effects16` | 5.0 s |
| `validate_render_effects17` | 8.7 s |
| `validate_render_effects18` | 1.0 s |
| `validate_render_effects19` | 0.7 s |
| `validate_render_effects24` | 2.2 s |
| `validate_render_effects25` | 7.9 s |

## Limits and next

- Keep 374/642, 378 and 617 refused at the limits above. No synthetic actor state
  implies event state or ordinary spawnability.
- Class-2/6 transformed-player action services remain excluded; the new native
  actors use their proved constructor class byte 0.
- Whole-client actor coverage remains unknown. The optional nine-opener list is
  separate research input and is not added to the 32-row denominator.
- Temporary renders, reports and build outputs are removed at PR-ready. No new
  private input is needed by the next lane. The committed summaries retain the
  evidence, binary hashes, checks and next steps.

## Work log

The following WIP checkpoints are historical; the result above supersedes them.

### WIP checkpoint


Branch `codex/render-actors-003`, base `d4af71dd`. Offline/static only, no subagents.
The owner reinstated the 02:30 stop on 2026-11-12, with WIP by 02:30 if not
PR-ready by 02:15. Keep commit/push/WIP checkpoints every 20-30 minutes. No ready entry has been written.

Done: binding briefs, current handoffs and actor/Muun sources read. Baseline root
build and explicit `make -C native -j4 world` complete. One-time 46-map default sweep
saved as hashes, 230 files, 78.9 s. Before binary SHA-256
`4954601057b7ee7976c787157b321703d40c65dba68c46901b08d22adb1be76c`.

Classes 625/626 now have provisional recipes for the constructor's kind-1,
class-byte-0 fixture context, with startup files `Data/Item/iron_robot.bmd` and
`Data/Item/iron_robot_gold.bmd`. The first private iteration passes 734 checks,
zero mismatches, 53.5 s, including 34 native loads, textured robot bodies and four
native refusals. Two portable recipe tests pass in 1.1 s.

New bounded original-instruction audits pass separately: 270 robot action-hook
cases, 16 companion allocation/reuse controls, eight class-378 prefix controls.
The prefix ends before cloth allocation; it is not the complete 378 branch.
These new checks have not yet run in the full validator or through mutants.

Left: finish the four refusal investigations, review fixture-context boundaries,
full actor comparison and changed mutants, affected selection/checks, private 8d
under its cost cap, two robot demo renders, final rebuilt-binary identity sweep,
main integration, final documentation and PR-ready delivery. Whole-client actor
coverage and transformed-player hooks remain outside these recipes.

Next: retain 374/642 until companion update/draw/destruction is recovered, 378
until its cloth and aura path is recovered, and 617 until a startup model file is
proved. Do not supply them with a guessed body or file. Current bounded census
is provisionally 26 admitted / six refused to 28 admitted / four refused.

Local inputs for resuming: the one-time hashes and helper scripts in
`~/Documents/MTM/mu-mac-tools/native/scratch/render-actors-003/`. No live process,
installed app, Muun module, item generator or effect consumer was changed.

Checkpoint update, 20:55 on 2026-11-11: all 18 affected validator rows now have
passing results. Seventeen pass in the initial affected batch, 279.7 s total.
Its actor comparison passed all 1,669 checks but the row failed its expected
count because the constructor-default check was added after the runner loaded
its old metadata. The corrected row passes with all 25 compiled mutants caught,
297.3 s, at `eecd1774`. Other 17 compiled inputs remain those of `5d98283c`.
The final constructor check poisons class byte 0x16 and executes the original
store clearing it to zero, at 0x0137db50.

Portable selection is 156 work items, exceeding the private cap. Planned 8d
reduced modules are `native.tests.test_actor_recipes` and
`native.tests.test_native_renderchar`. Portable suites, private reduced modules,
renders, identity sweep, audit and PR-ready delivery are still pending.
Resource-limit waits have delayed the portable run. No ready entry exists.
