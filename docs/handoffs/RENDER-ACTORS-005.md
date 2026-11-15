# RENDER-ACTORS-005

## Result and census

Six authored monster classes now draw their complete selected body/weapon
assemblies: 0, 4, 6, 7, 9 and 17. The existing textured bodies retain their
constructor scales and animation; the missing weapons use the original
constructor's model indices and per-model hand bones. Both native backends
render them through the existing item passes with actor alpha. Class 7 draws
both hands from independently preserved body poses. Canonical placements are
unchanged. The standalone `mu-render actor` command retains its existing
explicit `--actor-weapon` interface; these assemblies are in the world loader.

| Native body classification | Before | After |
|---|---:|---:|
| Checked bounded body plan | 33 | 39 |
| Incomplete/unverified special passes | 911 | 905 |
| Refused by the loader | 80 | 80 |
| Fixture selector contexts | 1,024 | 1,024 |

The denominator includes repeated/default selectors, not unique creatures or a
visual-fidelity percentage. The 477 repeated default contexts are not upgraded
merely because they share Monster01. The constructor inventory remains 963
resolved / 61 unresolved, and the opener inventory remains 748 contexts,
711 extracted, 29 without an own file and eight unresolved mesh-state cases.
Its sixteen secondary openers request 42 secondary loads. The two CSVs now
separate the nine monster secondary consumers from complete native assemblies.

## Implemented group and evidence

| Class | Body | Scale | Right/left bones | Weapons |
|---|---|---:|---|---|
| 0 | Monster01, `0x7a5` | 0.8 | 42 / 33 | `0x0cec`, empty |
| 4 | Monster01, `0x7a5` | 1.15 | 42 / 33 | `0x10ed`, empty |
| 6 | Monster05, `0x7a9` | 0.85 | 41 / 32 | `0x14e8`, empty |
| 7 | Monster06, `0x7aa` | 1.6 | 41 / 32 | `0x0ce8`, `0x0ce8` |
| 9 | Monster05, `0x7a9` | 1.1 | 41 / 32 | `0x14e9`, empty |
| 17 | Monster11, `0x7af` | 0.9 | 41 / 32 | `0x0cee`, empty |

Body paths are original `Data/Monster/<name>.bmd` registrations. Weapon paths
come from their exact ItemModelFile rows in `Data/Local/Item.bmd`; the existing
item texture resolver supplies their bitmaps. No item body table/recipe, effect
consumer, Muun routine or world-object routine was changed. Shared registry and
status edits add this lane's own row/lines only.

[Research section 12](../research/client-actors.md#12-secondary-consumers-and-ordinary-monster-weapons-render-actors-005)
records the original addresses, pins, methods and remaining consumer work.
CreateCharacter's kind/class defaults and link-bone switch execute as original
instructions. CreateMonster's selected model, scale and equipment match the
native recipe. Whole RenderCharacter plans cover worlds 0/3/2/51, actions
0/2/3/4/6, frames and alpha. Separate RenderLinkItem and RenderObjDraw checks
cover the exact selected passes. RenderObject is a named base/pose recorder;
stateful map services explicitly decline, as in ACTORS-004.

`validate_actor_monsters` has 1,437 checks:

| Family | Checks | Evidence |
|---|---:|---|
| secondary_openers | 9 | Fifteen original secondary model/file registrations, extracted |
| clone_prefix | 6 | Effect-constructor counter/alpha/speed prefix, extracted |
| secondary | 6 | Gnome death counter/emission/removal-service prefix, extracted |
| defaults | 2 | Original CreateCharacter kind and class stores |
| recipes | 1,026 | Six constructor comparisons and 1,020 exclusions |
| openers | 4 | Original primary body registrations |
| render | 240 | Whole RenderCharacter selected body/link plans |
| draw | 80 | Original body/weapon RenderObjDraw streams |
| links | 28 | RenderLinkItem hand pose, transform, lighting and draw request |
| native | 36 | Actual files/textures, scales, frames, both hand poses and alpha |

Thus 360 original instruction/plan checks, 21 extracted secondary controls,
1,020 exclusions and 36 native contexts. No original pixel or temporal
comparison is claimed. Native hand vertices match isolated per-hand replays
byte for byte. The body bone array must also match the isolated body after
both attachments, preserving later native body consumers. Allocation failure
and actor-cache cleanup release the attachments, textures and shared storage.

## Verification

All 29 affected validators pass at **`f86f0109`**, 122,764 row checks, zero
failures/errors/skips, **454.1 s including selection**. Later commits are
documentation only. All three selector fallbacks are included: movement,
audio_combat and render_effects17. Ten unused-library consumers are pruned.
No full lane gate ran; the steward owns that gate. Heavy commands use nice 10,
make at most four jobs and runners two; resource waits precede heavy steps.

| Check | Result | Wall |
|---|---|---:|
| Root build | pass | 6.57 s |
| Explicit final `make -C native -j4 world` | pass | 0.30 s |
| Affected private validators | 29/29, 122,764 checks, zero skips | 454.1 s |
| Portable affected suites | 1,554 tests, 1,282 passed, 272 expected private-data skips, zero failures/errors | 437.0 s command / 377.6 s runner |
| Private 8d reduced | 8/8, zero skips | 79.73 s |
| Full new-row comparison/control run | 1,437 positive checks pass; seven valid controls caught, one equivalent control rejected | 256.0 s |
| Corrected control replay | 1,221 iteration checks pass; body_restore caught | 88.28 s |
| Seven before / seven after GL proof scenes | pass; all six assemblies inspected | 4.95 / 5.27 s |
| Default identity replay | 230/230 hashes unchanged, distinct rebuilt binaries | 83.45 s |
| Source staged audit at `f86f0109` | 2,270 files, zero rejected | 27.64 s |

Times exclude preceding resource waits unless stated. The final delivery audit,
census reproduction and documentation-consumer results are recorded in the PR.

**8d reduced:** selection has 169 work items, including 161 native modules,
exceeding the cap of forty. The private run sources
`. ~/Documents/MTM/mu-mac-tools/native/private-env.sh` from repo root and covers
`test_actor_monsters`, `test_actor_recipes` and `test_actor_composites`.
Brief 6b also finds `test_world_parts`; it passes in the portable affected run.
No existing constant, table size or renderchar ABI was changed. The actor struct gains a private weapon
owner pointer; its direct actor host consumers are covered above.

Current compiled controls are admission, load, body_restore, bone, scale,
alpha, hand and draw. All eight are caught without an emulator stop. The
initial omitted-left-restore control was equivalent for these short weapon
skeletons. It was replaced by omitting the final body-pose restoration, with a
new whole-body pose preservation assertion. Only the replacement was replayed;
the other seven passing controls were retained, with their assertions unchanged.
No production fix was needed for that test correction.

| Steward validator | Checks | Wall at `f86f0109` |
|---|---:|---:|
| `validate_actor_composites` | 1,427 | 8.4 s |
| `validate_actor_monsters` | 1,437 | 51.5 s |
| `validate_actor_recipes` | 1,669 | 125.0 s |
| `validate_app_polish1` | 752 | 22.1 s |
| `validate_app_polish2` | 1,028 | 4.0 s |
| `validate_app_polish4` | 10,485 | 39.6 s |
| `validate_audio_callers` | 5,528 | 7.2 s |
| `validate_audio_combat` | 19,548 | 32.8 s |
| `validate_audio_domains` | 2,544 | 25.2 s |
| `validate_audio_items` | 3,000 | 4.1 s |
| `validate_audio_objects` | 4,000 | 3.6 s |
| `validate_charsel_items` | 8,817 | 6.8 s |
| `validate_icarus_c2` | 8,400 | 24.7 s |
| `validate_inventory_fx` | 8,017 | 16.6 s |
| `validate_item_callers` | 6,013 | 1.6 s |
| `validate_items_ui` | 8,517 | 12.6 s |
| `validate_meshdraw` | 14,619 | 66.5 s |
| `validate_model_edge` | 954 | 144.6 s |
| `validate_movement` | 6,614 | 67.7 s |
| `validate_render_effects16` | 424 | 3.8 s |
| `validate_render_effects17` | 618 | 8.7 s |
| `validate_render_effects18` | 540 | 1.8 s |
| `validate_render_effects19` | 400 | 1.9 s |
| `validate_render_effects24` | 226 | 7.9 s |
| `validate_render_effects25` | 202 | 15.6 s |
| `validate_render_effects26` | 348 | 10.6 s |
| `validate_render_effects28` | 630 | 2.3 s |
| `validate_viewport_monsters` | 1,963 | 12.8 s |
| `validate_worlds_fog` | 4,044 | 7.2 s |

Steward validators: validate_actor_composites, validate_actor_monsters, validate_actor_recipes, validate_app_polish1, validate_app_polish2, validate_app_polish4, validate_audio_callers, validate_audio_combat, validate_audio_domains, validate_audio_items, validate_audio_objects, validate_charsel_items, validate_icarus_c2, validate_inventory_fx, validate_item_callers, validate_items_ui, validate_meshdraw, validate_model_edge, validate_movement, validate_render_effects16, validate_render_effects17, validate_render_effects18, validate_render_effects19, validate_render_effects24, validate_render_effects25, validate_render_effects26, validate_render_effects28, validate_viewport_monsters, validate_worlds_fog

Mutants needed by steward: none. The eight current changed-row controls have
already passed. Use the canonical private env from repo root. All row results
above are private runs with zero skips. Unchanged compiled inputs retain their
pass at `f86f0109`.

## Identity and proof renders

The before default sweep at base `b7dfd2ed` covers 46 views, 92 PNGs, 92 geometry
dumps and 46 normalized reports, 230 files, 67.56 s. Only
report output-directory prefixes are normalized. Each side explicitly rebuilds
`mu-world` before hashing:

- Before SHA-256: `e341fc2000d2e7f035f1e1814ca5384231389c8e7409ed20557643b0485108d7`.
- After SHA-256: `f58907ce03d1fb3658445cdcfa3a9eaa86772f8738012769ecb756ba474f4fb5`.

The hashes differ. All 230 file hashes match in the final default replay.
No default capture places one of the newly assembled fixtures.

The six GL proofs use world 0, DemoKnight at 128,124 and DemoActor at 129,125,
direction 5, 640x480, two frames, fixed clock 123456 ms, hidden names, no extra
players/environment/particles/helpers/audio. Against each original body-only
scene, changed pixels are 0 = 20, 4 = 238, 6 = 98, 7 = 715, 9 = 370 and
17 = 99. The empty control is byte-identical. Each textured assembly was
visually inspected. Temporary proof images, hashes and reports are removed
at cleanup; no new private input is needed by a later lane.

## Limits and next work

No composite monster secondary is admitted by this lane. The nine openers lead
to debris, death replacement or owned effect lifetimes. Type 226, classes
595/635, emits gnomedie after its counter reaches 26, resets the counter and
invokes the live-state service. That is not a persistent attached body. The
prefix audit stops before its particle/debris loop. The clone prefix for
`0x59f..0x5a3` likewise does not establish owner follow/render/destruction.
Complete those downstream consumers before moving their census rows to checked.

Classes 1/5/10 still have a character-caller sprite outside the ordinary weapon
assembly and remain incomplete. Classes 374/642 need companion lifetime, 378
needs cloth/aura and 617 needs an exact startup file. Their refusals are
unchanged. No filename is guessed. Generic walking, head links, buff-driven
appearance, fade/shadow parity and world override state remain outside these
bounded selected body/weapon plans.

Next concrete work: recover the sword sprite branch after the ordinary link
caller, or the type-226 effect's move/draw/retirement path. Preserve the four
refusal boundaries until their missing evidence is complete.

## WIP checkpoints and delivery

Pushed checkpoints: `2c3e4363` at 21:37, `f86f0109` at 21:48 and `86c92a0f`
at 22:14 on 2026-11-14. Their WIP sections are superseded by this final handoff.
Latest integrated main is `b7dfd2ed`; no incoming code delta required a replay.
All implementation and source checks listed above pass. The PR records the
final publication checks. The ready entry is written only after the final push;
no push follows it. The steward owns merge and the combined gate. Temporary
renders/reports/builds, worktree and local branch are removed at readiness.
The remote branch remains for the steward. Ready for steward.
