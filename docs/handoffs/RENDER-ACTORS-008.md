# RENDER-ACTORS-008

## WIP (stopped 2026-11-15 18:1x on the owner's "finish all work now" order; draft PR, no ready line)

**Done and verified** (details and timings in the sections below)

- Request recorder and the published per-row request table
  `docs/research/actor-caller-requests.csv` (349 constructed selectors).
- 48 rows admitted: effect group 33 of 66, link group 15 of 25, opener group 0 of 18. Census 775 checked /
  169 incomplete / 80 refused. The lists of admitted rows and the reasons of the remaining rows are below.
- The missing-consumer id list (section "Request table and missing consumers").
- `validate_actor_groups`: 13,529 checks all equal at `1483f330` (after merging main batches 121 and 122);
  34/34 compiled controls caught once at `b07537b8`; all 35 affected private validators pass at `1483f330`;
  affected portable suites pass; default identity sweep 230/230 identical with different binaries; sixteen
  proof scenes per side rendered and inspected; repository audit passed at `249360f2`-era staging.

**Not verified / left**

- The reduced private native test finish (8d: `native.tests.test_actor_groups`,
  `native.tests.test_actor_monsters`) was interrupted: its verifier subprocess was terminated by the stop
  order. Four of five tests passed; `ClientComparison.test_original_instructions` must be rerun (about 12
  min). The same verifier passed as the registry row `validate_actor_groups` at `1483f330`.
- The repository audit has not been rerun on the final staged tree (two documents changed since).
- Status lines say "WIP"; change them to PR-ready, mark the PR ready, append the ready-prs.txt line, then
  remove the worktree and local branch.
- Optional brief item 3 (lane 11's groups) was not started. Research section 15 classifies the eighteen NPC
  opener rows (thirteen open an own texture directory before `Npc/`).

**Next step**

In the kept worktree: merge the latest `origin/main`, `nice -n 10 make -j4`, then from the repository root
with private-env.sh run `tools/python/bin/python -m unittest native.tests.test_actor_groups
native.tests.test_actor_monsters`, then `scripts/audit_repository.py`. If main brought changes into
`native/core`, `reconstructed/actors` or `reconstructed/renderchar`, rerun
`scripts/run_validators.py --private --no-mutants --cache --affected origin/main --jobs 2` first.

## Result and census

The world actor renderer consumes 48 further generated bounded fixture plans
from ACTORS-007's caller-service groups, and the caller's requests of every
constructed selector are now published row by row.

| Native body classification | Before | After |
|---|---:|---:|
| Checked bounded body plan | 727 | 775 |
| Incomplete/unverified special passes | 217 | 169 |
| Refused by the loader | 80 | 80 |
| Fixture selector contexts | 1,024 | 1,024 |

Selectors include aliases and repeated defaults; they do not count unique
creatures or establish whole-client fidelity. An opener alone never admits an
actor. Distinct body model indices of the group plans rise from 108 to 124.

## Group sizes and admitted rows

The three uniform groups of the brief, by ACTORS-007's recorded reason:

| ACTORS-007 reason | Before | Admitted | Still incomplete |
|---|---:|---:|---:|
| additional caller services: effect | 66 | 33 | 33 |
| additional or different RenderLinkItem services | 25 | 15 | 10 |
| monster opener has extra load or different texture context | 18 | 0 | 18 |
| all other reasons | 108 | 0 | 108 |
| Total | 217 | 48 | 169 |

Admitted selectors:

- Effect group (33): 1, 5, 10, 18, 31, 45, 46, 47, 51, 151, 160, 161, 180,
  181, 188, 189, 196, 197, 238, 266, 267, 274, 337, 338, 439, 441, 442, 443,
  501, 557, 560, 724, 783. They send 73 sprite requests in all. Summon
  candidates 10 and 151 are among them as bodies only; no skill-to-actor
  mapping is added.
- Link group (15): 145, 148, 175, 178, 183, 186, 191, 194, 261, 264, 269, 272,
  332, 336 (item `0x10f0`, level 7, eight link sprites each) and 433 (item
  `0x14e6`, level 11, no request).

By the refined missing-plan groups of
[actor-missing-plan-groups.csv](../research/actor-missing-plan-groups.csv):
right weapon/link 54 to 37, both weapons/link 22 to 8, additional caller
effect requests 27 to 16, NPC whole body 31 to 29, left weapon/link 13 to 12,
both sword-sprite groups 3 to 0. Every other group is unchanged.

Remaining rows of the three groups, each with its exact reason in
[actor-group-decisions.csv](../research/actor-group-decisions.csv):

| Reason | Rows |
|---|---|
| Caller requests vary with action, world, clock or rand (27 effect rows) | 69, 88, 94, 105, 111, 117, 123, 129, 142, 237, 356, 416, 422, 423, 432, 440, 444..449, 555, 558, 559, 720, 784 |
| Sprites at computed positions | 452, 453 |
| Sprite bitmap `0x7f69` has no native slot | 41 |
| Native RGB draw path lacks the alpha callback (as 22/866) | 70 |
| RenderLinkItem of item `0x0af4` takes a second rand value | 40 |
| No reconstructed RenderObjDraw stream for bow `0x12e9` at level 1 or 3 | 64, 85, 91, 97, 114, 120, 126, 139, 429 |
| Item `0x14f1`: nine link sprites outside the link generator, second rand | 275 |
| Npc-directory worlds add RenderPartObject model `0x0a2a` (slot 0) | 162..173, 426, 427, 644, 645 |
| Type-226 secondary model and lifetime (unchanged refusal) | 595, 635 |

## Request table and missing consumers

[actor-caller-requests.csv](../research/actor-caller-requests.csv) has one
line per ordered distinct request of each constructed selector (349 of the
355-row population; six constructors do not resolve): phase (caller, right or
left link, opener), service, id, subtype, call site, anchor (OBJECT bone,
posed link bone, OBJECT field or computed vector), local offset, scale,
light, light model, owner, rotation, blend, axes, count, contexts in which it
appears, further rand call sites and `native_consumer`.

Ids that incomplete rows request and no native consumer serves today (for
RENDER-EFFECTS-034/036; rows in brackets):

- Sprite bitmaps without a slot: `0x7f69` (41, 48, 71, 74, 80, 301, 496),
  `0x8002` (105), `0x8149` (595, 635).
- Particles (type/subtype): `0x7ef7/12`, `0x7ef7/13` (416); `0x7f26/3` (69);
  `0x7f5a/50` and `0x807e/0` (440, 444, 445, 446, 559, 561); `0x7ffd/6`,
  `0x807e/1`, `0x807f/1`, `0x8080/1` (448); `0x806e/0` (422).
- Joints (type/subtype): `0x7f79/4` (72); `0x7f7c/7` (73); `0x7f7c/10` (71,
  74, 301, 496); `0x7fd6/6` (237, 720); `0x7fd6/55`, `/56`, `/57` (561).
- Effects recorded without a consumer query: `0x801d/0` and `0x413/10`.
- Bone-effect helper `0x0150e746`: the Monster58 family (88, 94, 111, 117,
  123, 129, 142, 432) calls it twice per frame beside time-scaled sprites.
- Link programs: item `0x14f1` (275). RenderObjDraw stream: item `0x12e9`.
- Part model `0x0a2a` in worlds 18..23, 53 and 97 (sixteen rows).

A consumer alone does not admit the varying rows: their programs take random
offsets or gates, so they also need a hand-traced request program.

## Implemented evidence

[Research section 15](../research/client-actors.md#15-caller-service-groups-render-actors-008)
has the instruction addresses and the method. In short:

- Recorder: `scripts/actor_caller_requests.py`. TransformPosition `0x012b6ef1`
  returns markers, so each request position resolves to its bone and offset;
  the clock and the rand value are authored per run; rand call sites are
  recorded. 28 contexts per row, 34 for a row with requests.
- Admission: a row passes only when every request is a sprite at an OBJECT
  bone with translate 1, the list is identical in all 34 contexts, no rand is
  taken beyond RenderCharacter's one flicker value, the light matches the
  compiled constant/flicker/pulse function bit for bit in every context, and
  the bitmap has a native slot whose file the production particle module loads.
- Corrections to ACTORS-007: RenderLinkItem passes its level argument `<< 3`
  (the native weapon level is the slot byte; 007's fifteen rows had level 0);
  the sword sprite of 1/5/10 is anchored on the OBJECT's own bone, which
  RenderLinkItem never writes (zero writes in every admitted hand).
- Link requests: a hand's own sprite list must equal the renderchar link
  generator at four clock/rand fixtures; then the existing item link consumer
  serves it on the hand's posed bones (`link_effect_mask`).
- A recorded weapon animation speed is accepted only with a one-key native
  weapon action.
- Native: `mu_world_actor_caller_fx` and `mu_world_actor_weapon_effects`,
  called by both render backends of `parts/actors.c`. No particle, joint,
  effect, item-table or recipe file changes.

`validate_actor_groups` has 13,529 positive checks:

| Family | Checks |
|---|---:|
| Original defaults | 2 |
| Weapon native contexts | 300 |
| Original link runs (services, level shift, bone writes, link lists) | 304 |
| Weapon draw streams | 152 |
| Exact plans and exclusions | 1,026 |
| Caller request rows and compiled light | 2,148 |
| Generated table/decision/group/request reproduction | 5 |
| Constructors | 186 |
| Openers | 1,116 |
| Whole callers | 5,208 |
| Clock/rand caller variations | 198 |
| Actual native assets, textures, geometry, alpha and requests | 186 |
| Original body reader | 1,488 |
| Distinct-model draw streams | 992 |
| Additional varied callers | 200 |
| Sword request audit | 12 |
| Type-226 counter/request audit | 6 |

All 34 compiled controls are caught with zero stops: twenty on the plan
library (the thirteen of 007, `link_mask`, and six on the request table and
light: admission, over-admission, count, flicker, pulse, constant) and
fourteen on the native loader/renderer (the eight of 007, request bone,
offset, guard and light, link consumer, weapon level).

The 34 controls ran once, at the tree of `b07537b8` (916.7 s with the positive
families). Later changes are the group host's failure-naming line for rows
without a plan, the verify-mode naming of such failures, documents and the two
merges of main; no control's target line changed. Later positive replays run
without mutants.

## Verification

| Check | Result | Measured wall |
|---|---|---:|
| Request-only recording (349 selectors, 999 table lines at that point) | pass | 144.5 s runtime |
| Final generation on merged main `9664e26c` | 10,350 trial checks, 186 plans, 124 model indices; every generated file byte-identical to the previous generation | 655.9 s runtime / 656 s command |
| Verifier with compiled controls at `b07537b8` | 34/34 caught, zero stops; 13,527 of 13,529 positives (two reproduction lines differed only in the naming of native failures, fixed next) | 916.7 s runtime |
| Verifier replay at `249360f2` | 13,529 positives, all equal, 5/5 reproduction | 694.6 s runtime / 695 s command |
| Census regeneration | 775 / 169 / 80; both CSVs written | 5.6 s |
| Root build after batch 122 merge `1483f330` | pass | 31 s |
| Explicit world rebuilds (baseline main `708798ae`, branch `1483f330`) | pass | 7 s each |
| Default identity sweep, both sides | 230/230 hashes identical | 63 s baseline / 64 s branch |
| Proof renders, 16 scenes per side | see below | 17 s baseline / 15 s branch |
| Affected portable suites at `1483f330` | 1,654 tests: 1,320 pass / 334 expected skips, zero failures or errors | 452.6 s runner / 553 s command |
| Repository audit | 2,412 staged files, 0 rejected | 32 s |
| Affected private validators at `1483f330`, no mutants | 35/35 pass, 312,864 checks | 1,356 s command |
| Reduced private native tests (8d) | NOT completed: the verifier subprocess of `test_actor_groups.ClientComparison` was terminated (signal 15) when the owner stopped the session; the other four tests passed | 396 s |

Heavy commands use nice 10, build jobs 4 and validator/portable jobs 2. No
full lane gate runs; the steward owns the combined gate.

**8d reduced:** the portable selection is 188 work items, 179 of them private
native items, above the forty-item cap. `native/tests/test_native_app.py` is
excluded (187 run). The private finish runs the native modules this lane
changed: `native.tests.test_actor_groups` and `native.tests.test_actor_monsters`. This run did not complete (see the table) and must be repeated.

| Steward validator | Checks | Wall | Tested commit |
|---|---:|---:|---|
| `validate_actor_composites` | 1,427 | 9.0 s | `1483f330` |
| `validate_actor_groups` | 13,529 | 768.5 s | `1483f330` |
| `validate_actor_monsters` | 1,437 | 63.5 s | `1483f330` |
| `validate_actor_plain` | 21,437 | 187.9 s | `1483f330` |
| `validate_actor_recipes` | 1,669 | 116.3 s | `1483f330` |
| `validate_app_polish1` | 752 | 24.2 s | `1483f330` |
| `validate_app_polish2` | 1,028 | 4.7 s | `1483f330` |
| `validate_app_polish4` | 10,485 | 43.7 s | `1483f330` |
| `validate_audio_callers` | 5,528 | 6.8 s | `1483f330` |
| `validate_audio_combat` | 19,548 | 35.8 s | `1483f330` |
| `validate_audio_domains` | 2,544 | 24.9 s | `1483f330` |
| `validate_audio_items` | 3,000 | 4.2 s | `1483f330` |
| `validate_audio_kubera` | 1,000 | 2.6 s | `1483f330` |
| `validate_audio_monsters` | 38,315 | 28.3 s | `1483f330` |
| `validate_audio_monsters6` | 55,392 | 58.2 s | `1483f330` |
| `validate_audio_objects` | 4,000 | 5.7 s | `1483f330` |
| `validate_audio_objects4` | 10,093 | 10.4 s | `1483f330` |
| `validate_charsel_items` | 8,817 | 8.4 s | `1483f330` |
| `validate_icarus_c2` | 8,400 | 32.6 s | `1483f330` |
| `validate_inventory_fx` | 8,017 | 9.4 s | `1483f330` |
| `validate_item_callers` | 6,013 | 1.4 s | `1483f330` |
| `validate_items_ui` | 8,517 | 13.4 s | `1483f330` |
| `validate_movement` | 60 | 71.5 s | `1483f330` |
| `validate_render_effects16` | 424 | 5.2 s | `1483f330` |
| `validate_render_effects17` | 618 | 9.1 s | `1483f330` |
| `validate_render_effects18` | 540 | 1.5 s | `1483f330` |
| `validate_render_effects19` | 400 | 1.1 s | `1483f330` |
| `validate_render_effects24` | 226 | 2.8 s | `1483f330` |
| `validate_render_effects25` | 202 | 10.6 s | `1483f330` |
| `validate_render_effects26` | 348 | 11.3 s | `1483f330` |
| `validate_render_effects28` | 630 | 2.3 s | `1483f330` |
| `validate_render_effects31` | 66,051 | 275.6 s | `1483f330` |
| `validate_render_effects33` | 6,410 | 27.3 s | `1483f330` |
| `validate_viewport_monsters` | 1,963 | 13.3 s | `1483f330` |
| `validate_worlds_fog` | 4,044 | 9.3 s | `1483f330` |

Steward validators: validate_actor_composites, validate_actor_groups, validate_actor_monsters, validate_actor_plain, validate_actor_recipes, validate_app_polish1, validate_app_polish2, validate_app_polish4, validate_audio_callers, validate_audio_combat, validate_audio_domains, validate_audio_items, validate_audio_kubera, validate_audio_monsters, validate_audio_monsters6, validate_audio_objects, validate_audio_objects4, validate_charsel_items, validate_icarus_c2, validate_inventory_fx, validate_item_callers, validate_items_ui, validate_movement, validate_render_effects16, validate_render_effects17, validate_render_effects18, validate_render_effects19, validate_render_effects24, validate_render_effects25, validate_render_effects26, validate_render_effects28, validate_render_effects31, validate_render_effects33, validate_viewport_monsters, validate_worlds_fog

Mutants needed by steward: none. Use the canonical private environment from
the repository root. Main through batch 121 `c49fa188` is merged at `9664e26c`
and batch 122 `708798ae` at `1483f330`; the validators above ran after both.

## Identity and proof renders

Both sides have an explicit `make -C native -j4 world`. The SHA-256s differ:

- Baseline, main `708798ae`: `c5f5f0699c69bf4a8b7ef5a60bdd0dff669029c4ade037edb25f85e52566752b`.
- Branch `1483f330`: `19485073771c9b450d5fb9b3f056d13bcb9036c4b41ab5300ac473d4950d1fe0`.

The one default sweep has 46 views (14 October, 32 DATA-ACQ-002) and 230
files per side at 640x400, 25 frames, saving frames 0/24, no draw_all and the
default clock. All 92 PNGs, 92 OBJECT/light dumps and 46 reports are
byte-identical; report comparison removes only the output path fields. The
default views place no actor of the admitted rows, so no image change is
expected. No original-pixel fidelity score is inferred.

Sixteen GL proof scenes per side use world 0, the hero at 128,124, DemoActor
at 129,125, direction 5, 640x480, six steps saving frames 0/5, particle seed
2026, hidden names and no environment, players, helpers or audio. The
baseline draws these classes with the unchecked fallback body and no weapon.
Changed pixels in the last frame and sprites created per rendered frame:

| Class | Changed pixels | Sprites per frame | What appears |
|---|---:|---:|---|
| 1 | 1,139 | 1 | sword and tip sprite |
| 5 | 2,361 | 1 | sword, shield and tip sprite |
| 10 | 60 | 1 | sword and tip sprite |
| 18 | 1,419 | 1 | weapon and its `0x7f67` sprite |
| 45 | 2,445 | 2 | pulse sprites on bone 9 |
| 46 | 1,644 | 6 | pulse sprites on both hands |
| 47 | 5,280 | 6 | staff and six flicker sprites |
| 151 | 6,160 | 6 | staff and six flicker sprites |
| 160 | 2,510 | 2 | two swords and two tip sprites |
| 238 | 958 | 1 | pulse sprite |
| 439 | 3,972 | 2 | two constant sprites on bone 15 |
| 501 | 26,335 | 3 | three `0x8098` sprites |
| 145 | 5,027 | 8 | item `0x10f0` and its eight link sprites |
| 433 | 155 | 0 | item `0x14e6` at level 11 |
| 13 (007 control) | 0 | 0 | unchanged |
| empty control | 0 | 0 | unchanged |

A before/after contact sheet of eight scenes was inspected. Temporary renders
and reports are removed at cleanup; no new private input is needed by later
lanes.

## Limits and next work

These plans certify bounded authored fixture contexts: 28 world/action
contexts per row plus six clock/rand variations for rows with requests. The
request recorder names its boundaries; no consumer is executed. Sprite order
and blending inside the frame's sprite pass, the sprite owner argument, the
client's rand stream position, pooled-object reuse, buff tint, shadows and
original pixels are not certified. The flicker value is one rand() of the
native particle module per drawn actor.

All 169 incomplete selectors retain a specific reason. For the next lanes:

- RENDER-EFFECTS-034/036: the id list above. A slot for sprite `0x7f69` would
  admit class 41 without further work in this verifier; the other ids belong
  to varying programs.
- A hand-traced reader per family for the 27 varying effect rows. The largest
  are the Monster58 family (eight rows: time-scaled sprites plus two
  bone-effect calls) and the `0x00e6…` monster visual functions (440, 444..449,
  558, 559, 784: particles at random offsets).
- The sixteen Monster71/72 rows need the part model `0x0a2a` reader and a
  world-restricted plan (their textures exist only under `Data/Npc`).
- Bow `0x12e9` needs a RenderObjDraw stream at levels 1 and 3 (nine rows);
  item `0x14f1` a link program (275); item `0x0af4` its second rand (40).
- Lane 11's groups are untouched: eighteen NPC opener rows, six constructor
  render-state overrides, ten extra-bitmap rows. The request table already
  lists the caller requests of those rows that construct.

Refusals 374/642, 378, 617, 546/918 and 22/866 are unchanged, and class 70
joins the 22/866 alpha boundary. Classes 595/635 keep their type-226 lifetime
refusal. Rows behind unresolved callers `0x00fdab58`, `0x01377aef` and
`0x0095d4f1` stay. No filename, spawn state, statistic, network input or
protection behaviour is inferred.

## WIP checkpoints and delivery

Pushed checkpoints: `e1fa35d6` (recorder, request table, first admissions),
`b07537b8` (186 plans, census), `249360f2` (reproducible tables, registry row,
research section), `9664e26c` and `1483f330` (merges of main). The final
delivery commit changes documents only after the tested source. The lane
stopped on the owner's 18:07 order before readiness: the PR is a draft and
there is no ready-prs.txt line. Scratch, renders, build outputs and the
baseline worktree are removed; the worktree
`~/Documents/MTM/worktrees/render-actors-008` is kept for the next agent.
