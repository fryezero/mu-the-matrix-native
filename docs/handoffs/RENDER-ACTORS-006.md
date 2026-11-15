# RENDER-ACTORS-006

## WIP latest-main integration

Checkpoint 2026-11-15 01:46: main through UI-WINDOWS-004 `4480bf41` is integrated
as `f35c9e14`. Root build passes in 16.37 s. The final affected selection
retains 29 rows and prunes twelve unused-library consumers. Its main-delta
selection replays nineteen rows, all passing at `f35c9e14`, 338.63 s with
zero waits/failures/errors/skips. This includes the full 21,437-check actor
row. The other ten rows retain their named passes on unchanged inputs.

Permitted portable integration is running, 178 work items, with the app
packaging test excluded. Next: finish it, explicitly rebuild and refresh
the default identity/proof renders, refresh this handoff/status/plan, run
the final documentation checks and audit, then publish the PR/ready entry
and clean up. No PR or ready entry exists yet. The tables below are the
pre-UI-WINDOWS-004 snapshot and will be replaced by final per-row commits.
Prior publication checks pass: 36 documentation tests, 35 passed / one
expected skip in 17.94 s; audit 2,294 files / zero rejected in 25.40 s plus
a 120 s wait. Production actor code and nine control targets are unchanged.

## Result and census

The native world actor renderer now consumes generated, instruction-checked
single-body plans for 550 previously incomplete fixture selectors. Each row
has its own constructor, opener, caller, native file/texture and pass checks.
There are 82 ordinary monster selectors and 468 repeated-default selectors,
covering 51 distinct exact model files. Existing generic bodies retain their
geometry; this lane certifies and consumes their bounded draw plans.

| Native body classification | Before | After |
|---|---:|---:|
| Checked bounded body plan | 39 | 589 |
| Incomplete/unverified special passes | 905 | 355 |
| Refused by the loader | 80 | 80 |
| Fixture selector contexts | 1,024 | 1,024 |

Selectors include repeated defaults. These counts are neither unique creatures
nor a whole-client fidelity percentage. The constructor and opener inventories
retain their earlier meaning; an opener alone never establishes an actor plan.
The opener CSV's new `checked_plain_body_contexts` column counts callers that
passed this lane separately from opener extraction.

## Implemented group and evidence

The frozen before-population contains these disjoint groups:

| Initially missing checked plan | Rows |
|---|---:|
| Plain monster body | 203 |
| Repeated default body | 473 |
| NPC whole-body plan | 84 |
| Equipment/part constructor | 107 |
| Special appearance | 18 |
| Extra bitmap | 6 |
| Special appearance, bitmap and equipment | 4 |
| Bitmap and equipment | 4 |
| Secondary-model consumer/lifetime | 4 |
| Special appearance and equipment | 2 |
| Total initially incomplete | 905 |

The [per-row decisions](../research/actor-admission-groups.csv) preserve this
population. The [refined missing-plan groups](../research/actor-missing-plan-groups.csv)
partition all 905 selectors into thirty groups with explicit selector lists.
Equipment-only construction selects sixty right, 34 both and thirteen left
weapons. Classes 1/10 and 5 also need the sword-sprite caller and have separate
refined groups. Special-only construction splits into seven joint appearances,
six EffectManager overrides and five cloth/world appearances. Secondary paths
split into two type-226 death-effect lifetimes and two NPC model consumers.

Of the 676 plain candidates, 550 pass. The remaining 126 split into 27 extra
effect callers, four links, four body-plus-effect callers, eight extra body
passes, seven changed/suppressed body callers, 22 blend-mesh, two blend/light,
three hidden-mesh, 44 subtype overrides, one multiple-opener constructor,
one missing-texture body and three unresolved callers. The other 229 original
rows need their named attachment, appearance, bitmap or lifetime proof.
These labels identify missing checked plans, not absent native features.

[Research section 13](../research/client-actors.md#13-table-driven-single-body-admission-render-actors-006)
records the original addresses, boundaries, generator and limits. The generator
checks world-0/rand-0 constructor instructions, exact model/scale/empty slots,
and constructor writes to appearance fields. That write audit excludes 27
hidden/blend-mesh and 44 subtype contexts which the provisional 621-row table
had missed. Only the final 550-row source and results are authoritative.

Each admitted opener executes in worlds 0/3/2/51/18/30 and agrees with the
compiled opener's complete synthetic model/action bytes and ordered AccessModel
and OpenTexture arguments. Each admitted full RenderCharacter entry runs
28 contexts across worlds 0/3/2/51 and actions 0..6. Both character sprite
emitters execute, rather than inheriting the shared harness's skip boundaries.
Extra parts, links, sprites, effects and unresolved caller state reject a row.
RenderObject remains the named base-body/pose boundary from ACTORS-004/005;
its arguments must be exactly `(OBJECT, 1, 0, 0, -1, -1)`. Optional recorded
ordinary shadows do not certify shadow/fade parity. Stateful map/helper
boundaries and deterministic RNG remain explicit.

Eight original RenderObjDraw streams per distinct model independently require
exactly one ordinary textured BODY pass, flags 2, requested alpha and no extra
service. The native host uses the production world loader, exact relative file,
binary32 scale, positive geometry, no attachments and complete texture slots.
It independently resolves and decodes every mesh bitmap and compares pixels,
dimensions, components and sampler state. Both world render backends consume
the generated options only for the matching model/scale and empty attachments.
No existing ABI, item recipe or effect consumer changes.

`validate_actor_plain` verifies 21,437 positive checks:

| Family | Checks |
|---|---:|
| Original kind/class defaults | 2 |
| Constructors | 550 |
| Openers | 3,300 |
| Whole caller contexts | 15,400 |
| Native assets/textures/geometry/alpha | 550 |
| Additional varied caller contexts | 200 |
| Distinct-model draw streams | 408 |
| Exact plan admission and exclusions | 1,026 |
| Table and decision reproduction | 1 |

Nine compiled controls are caught with zero emulator/native stops: admission,
over-admission of class 22, opener, model, scale, passes, translate, native flags
and native alpha. They ran once at `d3688570`; their target source is unchanged
by the main merges. Later positive replays use no mutants.

## Verification

All 29 final affected validators pass, **138,721 checks**, zero failures,
errors or skips. The per-row table below identifies the tested source commits.
Initial source `d3688570` passed 31 rows / 154,294 checks. After PR #389 merged,
the final selection pruned meshdraw/model-edge and retained 29 rows. The main
input-delta selector replayed 27 at `71a6d23f`, then nine UI-affected rows at
`04879bea`; audio-combat and viewport-monster retain their unchanged-input
passes at `d3688570`. The cleanup-publication correction in the test host has
the full 21,437-check positive replay at `4f9f92bb`.
Its output timing changes no check predicate or compiled-mutant target.

| Check | Result | Measured wall |
|---|---|---:|
| Final root build at `04879bea` | pass | 7.34 s runtime / 67.34 s command, 60 s wait |
| Final 550-row generation | 20,410 checks, 550 plans / 51 files | 212.21 s runtime, 60 s wait |
| Canonical census regeneration | 589 checked / 355 incomplete / 80 refused | 5.35 s runtime / 65.35 s command, 60 s wait |
| New-row comparison and compiled controls at `d3688570` | 21,437 checks; 9/9 caught, zero stops | 197.2 s row / 317.34 s command, 120 s wait |
| Other thirty initial affected rows | 132,857 checks, 30/30 pass | 403.89 s runtime / 523.89 s command, 120 s wait |
| Main integration replay at `71a6d23f` | 27/27 pass | 390.73 s runtime / 450.73 s command, 60 s wait |
| UI integration replay at `04879bea` | 9/9 pass | 128.15 s runtime / 248.15 s command, 120 s wait |
| Corrected host positive replay | 21,437 checks, pass | 168.8 s row / 168.88 s command, 0 s wait |
| Initial portable affected | 1,563 tests, 1,288 passed / 275 expected skips, zero failures/errors | 406.7 s runner / 479.69 s command |
| Permitted portable integration | 1,792 tests, 1,454 passed / 338 expected skips, zero failures/errors | 362.9 s runner / 850.37 s command, 360 s wait |
| Private 8d reduced at `0c7c2223` | 2/2 pass, zero skips | 165.64 s command, 0 s wait |
| Explicit rebuilt-world identity replay | 227/230 hashes, all 45 unaffected views identical | 70.93 s command, 0 s wait |
| Seven GL proof scenes | six actor representatives plus empty control, inspected | 6.37 s render / 126.45 s command, 120 s wait |
| Earlier staged source audit | 2,282 files, zero rejected | 29.25 s |

Command walls include the stated resource waits and selection where applicable.
Final publication audit and documentation-consumer results are recorded in the PR.


**8d reduced:** portable selection exceeds forty work items, so the private
finish runs the only native test module added by this lane,
`native.tests.test_actor_plain`, from repo root with
`. ~/Documents/MTM/mu-mac-tools/native/private-env.sh`. The broader portable
selection covers direct actor consumers, including world parts. No full lane
gate ran. The steward owns the combined gate.

The first portable run accidentally selected `test_native_app.py`. Its fixture
built and signed a temporary test bundle, ran eighteen synthetic tests and
skipped the installed-game test. Its teardown removed that bundle; no installed
Preview app changed. This was outside the brief's no-packaging scope. The
integration portable run explicitly excludes that module and performs no
further packaging.

| Steward validator | Checks | Wall | Tested commit |
|---|---:|---:|---|
| `validate_actor_composites` | 1,427 | 11.9 s | `71a6d23f` |
| `validate_actor_monsters` | 1,437 | 67.3 s | `71a6d23f` |
| `validate_actor_plain` | 21,437 | 168.8 s | `4f9f92bb` |
| `validate_actor_recipes` | 1,669 | 118.3 s | `71a6d23f` |
| `validate_app_polish1` | 752 | 26.0 s | `04879bea` |
| `validate_app_polish2` | 1,028 | 6.5 s | `04879bea` |
| `validate_app_polish4` | 10,485 | 54.5 s | `04879bea` |
| `validate_audio_callers` | 5,528 | 7.2 s | `04879bea` |
| `validate_audio_combat` | 19,548 | 45.3 s | `d3688570` |
| `validate_audio_domains` | 2,544 | 41.0 s | `04879bea` |
| `validate_audio_items` | 3,000 | 4.9 s | `04879bea` |
| `validate_audio_objects` | 4,000 | 5.1 s | `71a6d23f` |
| `validate_audio_objects4` | 10,093 | 8.4 s | `71a6d23f` |
| `validate_charsel_items` | 8,817 | 10.1 s | `71a6d23f` |
| `validate_icarus_c2` | 8,400 | 26.9 s | `71a6d23f` |
| `validate_inventory_fx` | 8,017 | 8.9 s | `71a6d23f` |
| `validate_item_callers` | 6,013 | 1.3 s | `71a6d23f` |
| `validate_items_ui` | 8,517 | 12.4 s | `71a6d23f` |
| `validate_movement` | 6,614 | 97.1 s | `04879bea` |
| `validate_render_effects16` | 424 | 5.5 s | `04879bea` |
| `validate_render_effects17` | 618 | 12.1 s | `71a6d23f` |
| `validate_render_effects18` | 540 | 1.4 s | `71a6d23f` |
| `validate_render_effects19` | 400 | 1.0 s | `71a6d23f` |
| `validate_render_effects24` | 226 | 3.0 s | `71a6d23f` |
| `validate_render_effects25` | 202 | 11.3 s | `71a6d23f` |
| `validate_render_effects26` | 348 | 10.6 s | `71a6d23f` |
| `validate_render_effects28` | 630 | 2.7 s | `71a6d23f` |
| `validate_viewport_monsters` | 1,963 | 13.4 s | `d3688570` |
| `validate_worlds_fog` | 4,044 | 12.9 s | `04879bea` |

Steward validators: validate_movement, validate_viewport_monsters, validate_icarus_c2, validate_audio_callers, validate_audio_combat, validate_audio_domains, validate_audio_items, validate_app_polish1, validate_app_polish2, validate_app_polish4, validate_render_effects16, validate_worlds_fog, validate_render_effects17, validate_item_callers, validate_inventory_fx, validate_render_effects18, validate_render_effects19, validate_render_effects24, validate_render_effects25, validate_actor_recipes, validate_charsel_items, validate_render_effects26, validate_actor_composites, validate_audio_objects, validate_render_effects28, validate_items_ui, validate_actor_monsters, validate_actor_plain, validate_audio_objects4

Mutants needed by steward: none. Use the canonical private environment from
repo root. Every validator result above is private with zero skips. The table
names the source commit for each retained or replayed result, so unchanged
compiled inputs need no redundant run.

## Identity and proof renders

The baseline at ACTORS-005 `e3347dd7` covers 46 views, 92 PNGs, 92 geometry
dumps and 46 normalized reports, 230 files, 79.36 s. Both sides explicitly run
`make -C native -j4 world` before hashing. Only report output-directory prefixes
are normalized.

- Before SHA-256: `f58907ce03d1fb3658445cdcfa3a9eaa86772f8738012769ecb756ba474f4fb5`.
- After SHA-256: `0b9bcf21d7766ce6da790a63e96826e5cd432183ea2ae21c56a5817b2516133d`.

The rebuilt binary hashes differ. Exactly 227/230 file hashes are unchanged:
90/92 PNGs, 92/92 geometry dumps and 45/46 normalized reports. All 45
unaffected views are identical. The only differences are world-37 Kanturu's
two PNGs and report, exactly the incoming INNER-004 RGBA seam change. The
comparison asserts that precise three-file set, not a general exclusion.
No default capture gains a change from the actor plan integration. The final
replay takes 70.88 s including the explicit world rebuild.

The seven GL proof scenes use world 0, DemoKnight at 128,124 and DemoActor
at 129,125, direction 5, 640x480, two frames, fixed clock 123456 ms, hidden
names and no extra players/environment/particles/helpers/audio. Ordinary
classes 2/3/308 and repeated-default classes 68/405/572 are visibly textured.
Against the empty control, changed pixels are 2 = 599, 3 = 859, 68 = 3,792, 308 = 4,980, 405 = 3,792, 572 = 3,792. The empty
control has zero changed pixels. All six bodies were visually inspected.
The render work takes 6.37 s. Temporary images/reports are removed
at cleanup; no new private input is needed by a later lane.

## Limits and next work

The plans certify selected fixture body contexts, not whole-world, buff,
motion, shadow/fade, temporal or original-pixel equivalence. Constructor state
outside the uniform group remains incomplete. Class 918's exact Monster411
body has two missing mesh textures; no substitute filename is guessed.

Classes 1/5/10 still need the sword sprite after the ordinary weapon caller.
Classes 595/635 still need the type-226 effect's move/draw/retirement path;
gnomedie is an owned death-effect lifetime, not a persistent attached body.
Classes 374/642 still require companion lifetime, 378 cloth/aura and 617 its
exact startup file. These four refusal boundaries stay unchanged. No hard
case beyond the uniform group was admitted.

Next work can batch another uniform missing-plan group using the published
selector lists, or complete one of those caller/lifetime paths. Preserve the
constructor state and missing-asset exclusions until their own proof passes.

## WIP checkpoints and delivery

Pushed checkpoints include `fabfdf96`, `a41224f5`, `ea62a672`, `e18e919a`,
`33f20c82`, `c936b407`, `0c7c2223` and `4f9f92bb`. Earlier provisional
admissions are superseded by the final 550-row result. The initial stack was PR #389 at `e3347dd7`; its merged
history is retained. Main through `a95880c4` is integrated at `04879bea`.
The test-host output correction is committed at `4f9f92bb`; its positive
replay passes. Later delivery changes are documentation only. All implementation
and source checks above pass. The final push and PR precede the ready entry;
no push follows it. The steward owns merge and the combined gate. Temporary
renders/reports/builds, this worktree and its local branch are removed at
readiness. The remote branch remains for the steward. Ready for steward.
