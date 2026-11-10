# RENDER-ACTORS-001

## Result and census

PR-ready on `codex/render-actors-001`, with main `ff8e0543` integrated as `73882b3f`.
Tested source is `9daf92aa90635185dfd09c309836cd0996a0f606`. Offline/static only.

Death King 55 now draws its whole Skeleton01 body on Player bones at scale 1.4, alongside its existing
weapon and CLOAK-004 cloth. Classes 14, 15, 16, 56 and 236 use the same recovered whole-body path.
Golden Archer 236 draws the +8 town body in world 0, including the `0x44` glow pass, and level zero in
other worlds. Eleven equipment recipes retain their extracted models and levels; nine gain native
admission, with Marlon 229 and Shadow Phantom Soldier 257 retained as existing-loader controls.

The 32-row Player-model census has 15 bounded fixes, two unchanged controls and 15 unadmitted later
subtypes. Shipped placements are unchanged. This is a bounded class-table census, not coverage of every
virtual map processor, transformed-player appearance or world variant.

| Class | Result | Body recipe | Scale |
|---|---|---|---:|
| 14 | fixed | whole `0x422`, Skill/Skeleton01 | 0.95 |
| 15 | fixed | whole `0x423`, Skill/Skeleton02 | 1.1 |
| 16 | fixed | whole `0x424`, Skill/Skeleton03 | 1.2 |
| 34 | fixed | five parts `0x18e9..0x20e9`, +9 | 0.9 |
| 55 | fixed | whole `0x422`, Skill/Skeleton01 | 1.4 |
| 56 | fixed | whole `0x422`, Skill/Skeleton01 | 0.8 |
| 229 | unchanged control | five parts `0x18ef..0x20ef`, +7 | 0.9 |
| 236 | fixed | whole `0x423`, Skill/Skeleton02; +8 in world 0, +0 elsewhere | 1 |
| 247 | fixed | five parts `0x18ef..0x20ef`, +0 | 0.9 |
| 249 | fixed | five parts `0x18ef..0x20ef`, +0 | 0.9 |
| 257 | unchanged control | five parts `0x18fe..0x20fe`, +13 | 1 |
| 258 | fixed | five parts `0x18ef..0x20ef`, +0 | 0.9 |
| 297 | fixed | five parts `0x18e7..0x20e7`, +9 | 0.9 |
| 371 | fixed | five parts `0x18ef..0x20ef`, +0 | 0.9 |
| 372 | left | subtype `0x425`, kind/world/action hook unresolved | 0.95 |
| 373 | left | subtype `0x429`, kind/world/action hook unresolved | 0.95 |
| 374 | left | subtype `0x3ed`, kind/world/action hook unresolved | 0.85 |
| 375 | fixed | five parts `0x1904..0x2104`, +9 | 0.9 |
| 378 | left | subtype `0x3e9`, kind/world/action hook unresolved | 1 |
| 414 | fixed | five parts `0x18ef..0x20ef`, +0 | 0.9 |
| 464 | fixed | five parts `0x18ef..0x20ef`, +0 | 0.9 |
| 503 | left | subtype `0x541`, kind/world/action hook unresolved | 0.9 |
| 548 | left | subtype `0x552`, kind/world/action hook unresolved | 0.9 |
| 616 | left | subtype `0x5bb`, kind/world/action hook unresolved | 0.9 |
| 617 | left | subtype `0x5ba`, kind/world/action hook unresolved | 0.9 |
| 625 | left | subtype `0x5bc`, kind/world/action hook unresolved | 1.1 |
| 626 | left | subtype `0x5bd`, kind/world/action hook unresolved | 0.6 |
| 642 | left | subtype `0x5be`, kind/world/action hook unresolved | 0.9 |
| 646 | left | subtype `0x5bb`, kind/world/action hook unresolved | 0.9 |
| 706 | left | subtype `0x5bf`, kind/world/action hook unresolved | 0.9 |
| 806 | left | subtype `0x5c4`, kind/world/action hook unresolved | 1.1 |
| 807 | left | subtype `0x5c5`, kind/world/action hook unresolved | 0.9 |


Each five-part range advances by `0x200` per slot. The exact nine-slot equipment records remain in
`reconstructed/actors/monster_class_table.h`; this lane does not regenerate or edit that table.

## Evidence and implementation

See [research section 7](../research/client-actors.md#7-player-model-actor-body-recipes-render-actors-001).
The validator verifies full pinned SHA-256 values through `Pin.read`: text `2bd5f2e9...3724`, image data
`c985e2e6...672f`, the trig flag and feature word. No protection boundary is followed.

- Generic constructors `0x0138366a`, `0x01383791`, `0x0138383a`, `0x013842a4` supply the six skeleton subtypes.
- Startup loop `0x01832c28..0x01832c5d` loads Skeleton01..03 from Data/Skill into `0x422..0x424`.
- RenderCharacter's final skeleton branch `0x01369f98..0x0136a00d` passes level zero. Its world-0 town
  branch `0x01367d85..0x01367e23` passes CHARACTER `+0x144 << 3` for kind 4.
- Golden Archer's constructor writes `+0x144 = 8` at `0x01384306`. The earlier zero-filled reference fixture
  missed that overwrite. The corrected reference retains the constructor's level and kind, including
  the kind-2 classes 15, 16 and 55 whose stored 1 is ignored by their later level-zero branch.
- The recipe stores Golden Archer's town level, the native loader applies the world condition, and
  `mu_renderchar.c` routes the three skeleton models to the existing generic RenderObjDraw stream.
  They remain outside the item-body census. Equipment and ordinary unsupported-model routes are retained.
- The native host loads and poses all 17 covered classes, checks exact types/levels/scales, nonempty
  height and mesh counts, zero missing textures, and the skeleton draw-pass admission. It repeats the
  six skeletons in world 3 to catch leakage of the town level.

The eleven equipment recipes compare the existing constructor/processor chain with RenderCharacter's idle
part/link plan at action 1, authored record kind 0 and option/ext 0. Model lookup, strings and engine services
are named stubs. No opaque processor jump is executed.

## Checks

All commands run from the repository root. Private commands source
`~/Documents/MTM/mu-mac-tools/native/private-env.sh`. Heavy work uses nice 10, make at most four jobs,
validator runners two jobs, one heavy lane command at a time. High load caused a pause.
No full lane gate was run; that belongs to the steward.

| Check | Result | Wall |
|---|---|---:|
| Post-fix `make -j4` | pass | 11.1 s |
| Post-build validator selection | 21 selected, three symbol fallbacks, ten unused consumers pruned | 83.1 s |
| Affected validators, private, cached, no mutants | 21/21 pass, 96,078 checks | 273.4 s including selection |
| Actor validator, final mutants once | 361 checks, zero mismatches; 12/12 compiled mutants caught | 100.5 s |
| Focused portable regression | three tests pass | 0.8 s |
| Portable affected suites | 1,459 tests, 1,219 passed, 240 skipped, zero failures/errors | 356.1 s including selection |
| Private native modules, 8d reduced | 26 tests pass, zero skips | 29.9 s |
| Repository audit | 2,137 files, zero rejected | 19.0 s |
| Four documentation-consumer modules | 36 tests, 35 passed, one skipped | 8.2 s |
| Default identity sweep and 20 actor scenes | pass | 72.4 s |

The actor row's families are recipes 36, body hook 240, equipment plan 11, RenderObjDraw body stream 48,
startup loader three and native loads 23. Of 361 checks, 319 are original-instruction or extracted-constructor
comparisons, 23 are actual native loads and 19 are authored exclusions. These are not original pixel comparisons.
The twelve draw clocks cover all three level-zero bodies and Golden Archer's +8 body, with varying alpha/light.
The body-hook comparisons cover worlds 0, 2, 3 and 51.

Only `validate_actor_recipes` runs compiled mutants. Its twelve mutations cover body mappings, level,
recipe/slot admission, body file/directory, the native world gate and generic draw-path admission.
All other selected rows run without mutants. Brief 6b review found no changed existing struct layout,
constant or table size. The new recipe exports are used by the actor loader and their owning tests.

**8d reduced:** 146 native work items exceed the 40-item cap. The private run covers the
changed `native.tests.test_actor_recipes` and `native.tests.test_native_renderchar` modules with the canonical
environment. The portable run retains the selector's affected modules. Main's merge adds documentation and
three private-fixture repairs; it changes no runtime source beyond the already tested `54a53e1a` base.

## Renders and byte identity

The resumed default-draw sweep uses the saved one-time `5ef84dff` baseline hashes. It does not retake before
numbers. At 640x400, without draw_all or live_time:

- October 22: 28/28 PNGs, 28/28 OBJECT/light dumps and 14/14 normalized reports byte-identical;
  15.7 s.
- DATA-ACQ-002: 64/64 PNGs, 64/64 dumps and 32/32 normalized reports byte-identical;
  40.7 s.

Only the output-directory prefix is normalized in reports. No new actors are placed in that sweep.
Twenty native actor scenes at 640x480, two frames, GL, use DemoKnight at 128,124 and DemoActor at 129,125,
direction 5. All 17 covered classes are re-rendered in world 0. Golden Archer is also rendered in world 3
and at a second 123456 ms start clock in both worlds. All 17 body/equipment scenes and all four Golden Archer
views were visually inspected. The town glow is visible; the nonzero-world body retains its plain textured pass.
The native host verifies two passes for the town +8 body and one for the nonzero-world body; the synthetic
native renderer test verifies the extra pass changes pixels deterministically.

The earlier whole-body control omitted the body slot while admitting the same class rows. It was an
instrumented control, not unmodified main for classes main refuses. Those reviewed pairs gained
1,319/3,222/2,792/3,278/1,000 body pixels for classes 14/15/16/55/56; all eleven equipment pairs were
identical. Golden Archer's earlier zero-level picture is superseded by this corrected town render.
No original screenshot, original pixel equivalence or live motion comparison is claimed.

## Steward validators

Steward validators: validate_actor_recipes, validate_app_polish1, validate_app_polish2, validate_app_polish4, validate_audio_callers, validate_audio_combat, validate_audio_domains, validate_audio_items, validate_icarus_c2, validate_inventory_fx, validate_item_callers, validate_meshdraw, validate_model_edge, validate_movement, validate_render_effects16, validate_render_effects17, validate_render_effects18, validate_render_effects19, validate_render_effects24, validate_viewport_monsters, validate_worlds_fog.

All rows below pass at `9daf92aa90635185dfd09c309836cd0996a0f606`. The three fallback rows are
`validate_movement`, `validate_audio_combat`, `validate_render_effects17`, and all are included.
Only `validate_actor_recipes` needs mutants, passed 12/12 at that same source. Environment:
`. ~/Documents/MTM/mu-mac-tools/native/private-env.sh`.

| Validator | Checks | Wall |
|---|---:|---:|
| `validate_actor_recipes` | 361 | 35.8 s |
| `validate_app_polish1` | 752 | 19.9 s |
| `validate_app_polish2` | 1,028 | 3.7 s |
| `validate_app_polish4` | 10,485 | 31.6 s |
| `validate_audio_callers` | 5,528 | 5.3 s |
| `validate_audio_combat` | 19,548 | 29.6 s |
| `validate_audio_domains` | 2,544 | 22.1 s |
| `validate_audio_items` | 3,000 | 4.1 s |
| `validate_icarus_c2` | 8,400 | 17.8 s |
| `validate_inventory_fx` | 8,017 | 6.6 s |
| `validate_item_callers` | 6,013 | 1.5 s |
| `validate_meshdraw` | 14,619 | 52.6 s |
| `validate_model_edge` | 954 | 106.5 s |
| `validate_movement` | 6,614 | 48.4 s |
| `validate_render_effects16` | 424 | 2.9 s |
| `validate_render_effects17` | 618 | 6.4 s |
| `validate_render_effects18` | 540 | 1.5 s |
| `validate_render_effects19` | 400 | 0.9 s |
| `validate_render_effects24` | 226 | 2.5 s |
| `validate_viewport_monsters` | 1,963 | 10.7 s |
| `validate_worlds_fog` | 4,044 | 4.6 s |

## Limits and next

- Fifteen later subtype rows remain unadmitted. Recover their exact kind/world/action gates and special
  mesh/effect hooks before admission. The table's world-0, rand-0 and virtual-processor limits remain.
- Native Player-model actors retain the existing generic pose and weapon-link path. Compared idle plans
  do not establish original-equivalent walking, carried-weapon transforms, shadows, buffs, guild/duel state
  or native fade alpha. Existing armour owner effects and CLOAK-004 cloth retain their own coverage.
- Cloth wind/rand history is native; no original temporal or pixel equivalence is claimed.
- Appearance uses extracted equipment and authored fixtures only. Character power, live services,
  protection modules, memory writes and installed app changes remain outside this lane.
- Temporary renders, scratch reports and build outputs are removed at PR-ready. No new local input is
  required by a future lane. The remote branch remains for the steward; no push follows the ready-prs entry.

Self-review covered the constructor reference, world gate, draw admission, bounds, census and final diff.
No independent subagent review is claimed. Ready for steward; merge and installation belong to their lanes.
