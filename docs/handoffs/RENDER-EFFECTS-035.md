# RENDER-EFFECTS-035

**WIP, not PR-ready.** Stopped by the owner's "finish all work now" order of 2026-11-15 18:07,
during the last merge-delta checks. Draft PR, no ready-prs line. Request side only.

Branch `claude/render-effects-035` starts at main `bb86bbf7` (PR #406, steward batch 120, with
EFFECTS-033), merges main `c49fa188` (PR #407, batch 121) at `fc459bc6` and main `708798ae`
(PR #408, HERO-ITEMS-002, batch 122) at `00fd9faf`. No subagents, no full lane gate. Heavy work
used nice 10, make at most four jobs and two validator or test workers.

## WIP

Done (all code is in; everything below "Original proof" was verified at `fc459bc6`, before the
last main merge):
- The 37-row classification and the two CSVs; 28 rows admitted on the request side (groups A-F),
  9 refused with reasons (G 5, H 2, I 2); 39 missing consumer ids published.
- Planner `reconstructed/combat/catalogue_skill_fx.c`, link selector
  `reconstructed/combat/link_selector.c`, verifier `scripts/validate_render_effects35.py` with its
  registry row, native adapter in `native/core/mu_combat.c`, fixture tests
  `native/tests/test_render_effects35.py`, research note.
- Second group: link selector wired into Death Stab and the auras; 27 / 28 cast end bodies.
- Verified at `fc459bc6`: the verifier with all 93 mutants, the 74 affected validators, the
  portable affected suites, eight private native modules, fourteen asset scenes, and the default
  identity pair against rebuilt main `c49fa188`.

Left:
- Checks for the merge of main `708798ae` at `00fd9faf` (it changes `native/core/mu_character.c`,
  `native/world/world_rt.c` and `reconstructed/hero-equipment`, no combat file). The root build
  passes. The merge-delta validator run (`--affected-since fc459bc6`, 37 rows) was stopped after
  4 passing rows (`validate_app_polish2`, `validate_hero_items`, `validate_actor_plain`,
  `validate_render_effects31`); 33 rows are not rerun. Not rerun on the merged tree: the fixture
  and private native modules, the portable affected suites, the asset scenes, the identity pair.
- `scripts/audit_repository.py` has not been run on this branch (new files were added).
- Status lines in `docs/status.md`, `docs/handoff.md`, `docs/roadmap.md` and
  `docs/design/native-port/plan.md`; final PR body; ready-prs line; cleanup of the worktree.
- Rows not admitted: group G (232, 723, 1501, 2040, 2043), H (76 twice), I (813, 426).

Next step: from the worktree root, with `private-env.sh` sourced, run
`scripts/run_validators.py --private --no-mutants --cache --affected-since fc459bc6 --jobs 2`,
the fixture modules `native/tests/test_render_effects35.py`, `27`, `28`, `30`, `32`, `33`,
`test_native_combat.py` and `test_audio_combat.py`, the portable
`scripts/run_test_suites.py --affected-since fc459bc6` (drop `native/tests/test_native_app.py`
from the work list, owner rule) and `scripts/audit_repository.py`. Then rebuild `mu-world` in an
export of main `708798ae` and in this tree (`make -C native -j4 world`, record both SHA-256s) and
repeat the 46-view default sweep (tour manifests `fidelity2/tour-after6.json` and
`data-acq-002/tour.json` under the lane scratch root, 640x400, 25 frames sampled 0/24,
`--no-audio --hero-name DemoKnight`, no draw_all or live_time). Then write the four status lines,
turn this section into the final handoff, mark the PR ready and add the ready-prs line. The lane's
scratch drivers were deleted with the scratch folder; they were thin wrappers around
`scripts/fidelity_tour.py` and `scripts/run_test_suites.py`.

## Classification and admitted boundary

The denominator is the 37 class-tree skills outside the learned demo sets (DK 14, Elf 23) of
EFFECTS-030. All 37 are classified by step body, end bodies, receive slice, ordered requests,
services and consumer availability:
[classification CSV](../research/skill-catalogue-classification.csv),
[missing consumers CSV](../research/skill-catalogue-missing-consumers.csv),
[research note](../research/client-render-effects-035.md). 27 rows use the default step and both
default ends.

| Group | Rows | Members | Request side |
|---|---:|---|---|
| A caster-frame | 8 | DK 740; Elf 77, 651, 652, 727, 740, 2023, 2025 | Admitted 8 |
| B bone-frame buff | 3 | DK 1500, 1502, 1503 | Admitted 3 (unmounted) |
| C triple storm | 6 | DK and Elf 1125, 1126, 1127 | Admitted 6 |
| D heal family | 4 | Elf 234, 425, 430, 2024 | Admitted 4 |
| E existing end body | 3 | Elf 432, 2026, 2027 | Admitted 3 |
| F arrows | 4 | Elf 46, 235, 427, 2047 | Admitted 4 |
| G own step or end body | 5 | DK 232, 723, 1501, 2040, 2043 | Refused: hand trace left |
| H mount context | 2 | DK 76, Elf 76 | Refused: mount body, out of scope |
| I no receive case | 2 | DK 813, Elf 426 | Refused: nothing to request |

**28 rows admitted on the request side, 9 refused.** "Admitted" means the row's receive case body
(and end body, where it has one) is reconstructed as ordered requests, compared with the original
instructions and reachable through an authored fixture. It is not a P/L/M label: a request whose
consumer is missing stays a counted refusal and draws nothing.

What draws today, through consumers that already exist:

| Row | Result |
|---|---|
| Elf 2023 Raining Arrow | Pose `0x107` and effect `0x70a/0`: the existing rain, landings, rings and decals |
| Elf 432 Summon Satyros | Start sound and the summon ground `0x7f84/3` with its ribbons; no summon body, as for 30..36 |
| Elf 2026 Improve Elemental Attack Power | Start sound and ground `0x7f84/3` on the record's target |

The other 25 admitted rows request only missing consumers (39 ids) or refused arrow callers. Their
poses, sounds and counted refusals are in place for the consumer lane (EFFECTS-036).

No alias is admitted: the planner refuses every pair whose raw id differs from its base. The 46 DK
and 40 Elf aliases keep the EFFECTS-030 inventory; the CSV lists the aliases of each catalogue row.

### Learned rows (second group)

The general link selector is recovered once: the link bone of a weapon slot is the byte at
CHARACTER `+0x19b1 + slot * 0x3fc`, written from the OBJECT model type alone by the type switch
`0x0137eefc..0x0137f5f4` (55 cases, Player default 33 / 42), and the slot is picked by
`0x013a5658` from the action. What it completes:

| Skill | Before -> after | Boundary |
|---|---|---|
| 43 Death Stab | L -> P | Bone through the selector (slot 0, bone 33). The selector reads no class word, so promoted DK class bytes are admitted with the same link; a weapon is still required |
| 28 Greater Damage | L -> L | Link bones through the selector; the cast end body `0x013afcea` now requests `0x7f84/3`, which draws. Presence stays an authored clock |
| 27 Greater Defense | L -> L | Link bones through the selector; the cast end body `0x013afb06` requests `0x7f84/2`, which has no consumer (counted refusal) |

The 29-row learned table of EFFECTS-033 therefore moves **14 P / 6 L / 9 M to 15 P / 5 L / 9 M**.
27 and 28 keep L because EFFECTS-033 names the authoritative presence feed as open for them; that
is server state and stays an authored clock. If the owner counts an authored clock as enough (as
for Ice Arrow's target ice), 28 would be P; that is a labelling decision, not new behaviour.

## Demo learned set: owner decision

Nothing in this lane adds a catalogue skill to a learned list, a hotbar or a default scene. The
rows are reachable only when a fixture supplies the learned entry (tests use the fixture skills
file, `MU_SKILL_DEMO`). Whether an extended learned set ships in the demo is the owner's decision.
Such a change would involve:

- `native/client/demo-skills.txt` (Elf `list 2 ...` line, and its `keys` line if a hotbar slot is
  wanted) and the built-in lists in `native/fixture/skills_model.c` (DK);
- per row, the skill table's own requirements still gate the hotbar cast (weapon kind, stats in
  `demo-session.txt`), as for 2044;
- useful candidates today are only 2023, 432 and 2026 (existing consumers); the other rows would
  cast with a pose and no effect until their consumers exist;
- the tests that pin the learned counts and the hotbar (`test_native_skill`, `test_session_skills`,
  `test_app_polish5`) and the README skill description would need the new numbers.

## Authored fixture inputs

- `MU_SKILL35_CONTEXT=remote,self`, two 0/1 words, default `0,0`. Ten receive slices branch on
  "the source is the hero" (the hero's own part of those casts is in its use routines, which are
  not traced). `remote=1` presents the slice as for a source that is not the hero. `self=1` makes
  the receive record's target the source; otherwise the target is the cast's actor.
- Bone services exist only for the hero's Player model: 1502 and 234 are counted context refusals
  unless `self=1`. Mounted bone-frame rows are refused by the planner.
- Presence answers of 2026 / 2027, the hero's character-table slot and the word at target
  CHARACTER `+0x158` are authored zero. No buff state, eligibility or power value is read.
- 27 / 28 end bodies target the hero, the character the EFFECTS-028 aura fixture buffs; presence
  answers come from `MU_AURA_FIXTURE_TICKS`. Without it the five joints of 27 are counted refusals.

## Original proof

`scripts/validate_render_effects35.py` runs each original case body under the strict machine on
authored CHARACTER/OBJECT records and an authored frame, entered at the case body and left at its
switch join. The receive parsers never run. One table drives all rows.

- Registry sample, 40 cases per body: **4,424 checks, zero mismatches**. 2,840 execute original
  instructions (1,160 receive, end and position bodies of the 28 rows; 432 step dispatcher cases;
  80 learned-buff end bodies; 1,096 link-selector model types; 32 slot-index cases; 40 SkillAction
  cases). 1,584 are authored admission controls (selector, learned cap, refusals).
- Larger sample, 200 cases per body, no mutants: **10,152 checks, zero mismatches**, 28.7 s.
- **93/93 compiled mutants caught, zero original-machine stops**, 500.0 s for the whole run with
  mutants (83 plants in the planner, 10 in the link selector; each mutant reruns only the
  families its source file can change). An earlier pass caught 92; the missed plant was the
  400-slot table bound, and a case with slot 400 exactly was added before the final pass. Mutants
  ran once more because that changed the comparison; no other mutant run is needed.

Compared per case: every effect, joint, sound, pose, bone, key-list, CRT draw and arrow request in
order with all argument words (owner, key and default words, scale, sound site), and the state the
body writes (source and hero AttackTime, target-index word, hero byte, frame reset, target link).
Both values of "the source is the hero", the hero-key sign extension, equal key words, a missing
model, presence and joint-search answers, bone counts 0 and negative, and a source outside the
400-slot table are covered. The step family checks that all 28 rows select the default step with
no request. The link family runs the type switch for every model type `0x700..0xb3f` plus eight
outliers; its routine has no SEH frame, so that one harness check is excluded for it and stated.

Authored, not original: animation and model answers, bone positions, mount, presence and joint
search results, the learned index and the character-table slot. The second link setter's answer
for types `0x7ee` / `0xa2f` is a static reading of its two compares. This proves the stated
instruction slices and the planner's requests, not original GPU appearance, whole-client RNG phase,
eligibility or authoritative state. libcombat SHA-256
`79851a863adc90f3435a0b41e3114ea6c4caa16d42b0447fcc7d120be572f677`.

## Native fixture proof

Verified at `fc459bc6` (not repeated after the last merge). Portable fixture module
`native/tests/test_render_effects35.py`: 15 tests pass, 2 private tests skipped in portable mode
and passing with the private environment (verifier sample and census check against the CSVs).

Fourteen read-only game-asset scenes, DemoKnight / DemoArcher at Lorencia 182,127, authored target
at 184,127, 512x320, software backend, 100 frames saved every three, one cast at frame 2, stop at
frame 3, no audio, items or other players; 476 PNGs, 53.7 s. Every scene: zero sent / one unsent
request, zero hits and kills, constant target HP, empty effect, joint and particle pools at the
last frame. Frames of 2023, 432 and 28 were inspected visually.

| Scene | Requests | Refused | Result |
|---|---:|---:|---|
| 2023 Raining Arrow | 1 | 0 | Pose `0x107`, rain with landings and rings, peak 44 effects |
| 432 Summon Satyros | 1 | 0 | Ground ribbons at the caster, peak 36 joints; no pose for a hero source |
| 2026, default and self target | 1 | 0 | Ground ribbons at the record's target |
| 28 Greater Damage, aura clock 60 | 1 | 0 | Cast end ground on the hero plus the aura |
| 27 Greater Defense, aura clock 60 | 1 | 1 | `0x7f84/2` refused; aura joints already exist |
| 43 Death Stab, class byte `0x11` | - | 0 | Trails as for the base byte, peak 14 effects / 103 joints |
| 740, remote source | 1 | 1 | Pose `0x9a`; `0x608/0` refused |
| 1500, self target | 1 | 1 | Pose `0x9c`; `0x69d/1` refused |
| 1125 | 3 | 3 | `0x635/0` and two `0x8263/0` refused |
| 2024 | 2 | 2 | Pose `0x106`; `0x8021/3`, `0x594/0` refused |
| 234, remote and self | 26 | 26 | Pose `0xd9`; nineteen joints and seven effects refused |
| 235 | 8 | 8 | Bow pose `0x7e`; volley block refused |
| 46 | 1 | 1 | Penetration pose `0x93`; arrow caller refused |

## Default identity and binaries

Verified for the first merge only. Both binaries were built with `make -C native -j4 world`
(baseline: an export of main `c49fa188`; after: this tree at `fc459bc6`, rebuilt after the last
source change) and hash-checked again after rendering.

- Before SHA-256: `acc4754f7a9b251091997650bf77cf2ec840657c0199445cdd869c6be673d02b`.
- After SHA-256: `91766dd50fe9e0c70b66ec2f8f979754aac21f1819d054d7e74f0b82271e0510`.

Default draw, explicit DemoKnight name, no draw_all or live_time, 640x400, 25 frames sampled 0/24,
46 views (fourteen October 22, thirty-two DATA-ACQ-002): **276/276 artifacts identical** (92 PNGs,
92 OBJECT/light dumps, 46 reports with the output prefix normalised, 46 logs). Before 120.5 s,
after 113.5 s. **Not repeated against main `708798ae`**: that pair is left.

## Completed checks and test budget

Commands ran from the repository root with the canonical private environment. No full gate.

| Check | Tree | Result | Wall s |
|---|---|---|---:|
| Root build | `fc459bc6` | pass | 15.8 |
| Verifier, 40 cases, all mutants | planner code of `1b11b537` | 4,424 equal; 93/93 mutants; zero stops | 500.0 |
| Verifier, 200 cases | `fc459bc6` | 10,152 equal | 28.7 |
| Affected private validators | `fc459bc6` | 74/74 pass, no mutants | 1,474.5 |
| Portable affected suites | `fc459bc6` | 12 suites, 1,935 tests, 1,555 pass / 380 expected skips, 0 failures | 539.1 |
| Private native, eight modules (8d reduced) | `fc459bc6` | 62 tests: 61 pass, one stale expectation, below | 135.1 |
| Corrected `test_native_combat.py`, private | `fc459bc6` | 15/15 pass | 15.1 |
| Asset scenes | `fc459bc6` | 14 scenes, 476 PNGs | 53.7 |
| Identity before / after | `c49fa188` / `fc459bc6` | 276/276 identical | 120.5 / 113.5 |
| Root build after the second merge | `00fd9faf` | pass | not timed |
| Merge-delta validators | `00fd9faf` | stopped: 4 of 37 rows pass, 33 not run | - |

**8d reduced:** the private native selection is 190 work items, above the forty-item cap. Eight
modules ran: `test_render_effects35`, `27`, `28`, `30`, `32`, `33`, `test_native_combat`,
`test_audio_combat`. **Packaging exclusion:** only `native/tests/test_native_app.py` was dropped
from the portable work list (190 items kept), by a task-local filter.

Stale expectation: `test_native_combat.InstalledTests.test_lorencia_fight` expected 29 loaded
models and gets 31. It fails the same way on an export of main `c49fa188`; EFFECTS-033 added
`Piercing.bmd` and `blood_storm_sword.bmd`. The expectation is corrected to 31 here.

Two existing tests changed with intent: `test_render_effects27` (class byte `0x11` now admitted
for Death Stab; classes 0 and 2 and a missing weapon stay refused) and `test_render_effects28`
(the Greater Damage run is longer so that its new ground effect retires).

Not run: `scripts/audit_repository.py`.

## Steward validators

Not final: the list is the selection at `fc459bc6`; the merge-delta rows must be rerun first (see
WIP). Canonical `private-env.sh`; `scripts/run_validators.py --private --no-mutants --cache
--affected origin/main --jobs 2`. No further mutants are needed for `validate_render_effects35`
unless its checks or the planner change.

| Validator | Cases | Wall s |
|---|---:|---:|
| `validate_actor_composites` | 1427 | 10.0 |
| `validate_actor_groups` | 8451 | 233.7 |
| `validate_actor_monsters` | 1437 | 43.1 |
| `validate_actor_plain` | 21437 | 248.1 |
| `validate_actor_recipes` | 1669 | 121.6 |
| `validate_app_polish1` | 752 | 20.1 |
| `validate_app_polish4` | 10485 | 37.4 |
| `validate_audio_callers` | 5528 | 7.3 |
| `validate_audio_charsel` | 5968 | 3.5 |
| `validate_audio_combat` | 19548 | 41.6 |
| `validate_audio_domains` | 2544 | 31.2 |
| `validate_audio_items` | 3000 | 4.3 |
| `validate_audio_kubera` | 1000 | 1.6 |
| `validate_audio_monsters` | 38315 | 27.6 |
| `validate_audio_monsters6` | 55392 | 80.8 |
| `validate_audio_objects` | 4000 | 5.4 |
| `validate_audio_objects4` | 10093 | 12.7 |
| `validate_charsel_items` | 8817 | 12.5 |
| `validate_combat` | 496 | 1.5 |
| `validate_icarus_c2` | 8400 | 26.2 |
| `validate_inventory_fx` | 8017 | 8.8 |
| `validate_item_callers` | 6013 | 1.5 |
| `validate_item_hiddenmesh` | 116281 | 512.4 |
| `validate_items` | 444 | 4.8 |
| `validate_items_ui` | 8517 | 17.3 |
| `validate_meshdraw` | 14619 | 73.7 |
| `validate_model_edge` | 954 | 144.0 |
| `validate_model_light` | 1433 | 7.0 |
| `validate_movement` | 6614 | 69.0 |
| `validate_muun_transition` | 400 | 1.4 |
| `validate_path` | 4719 | 33.6 |
| `validate_render_effects` | 660 | 1.6 |
| `validate_render_effects10` | 154 | 2.4 |
| `validate_render_effects11` | 176 | 1.3 |
| `validate_render_effects12` | 64 | 1.2 |
| `validate_render_effects13` | 180 | 0.7 |
| `validate_render_effects14` | 660 | 1.7 |
| `validate_render_effects15` | 509 | 1.2 |
| `validate_render_effects16` | 424 | 4.8 |
| `validate_render_effects17` | 618 | 8.7 |
| `validate_render_effects18` | 540 | 1.6 |
| `validate_render_effects19` | 400 | 1.2 |
| `validate_render_effects20` | 148 | 0.3 |
| `validate_render_effects21` | 267 | 0.4 |
| `validate_render_effects22` | 202 | 7.5 |
| `validate_render_effects23` | 1174 | 9.9 |
| `validate_render_effects24` | 226 | 3.0 |
| `validate_render_effects25` | 202 | 10.6 |
| `validate_render_effects26` | 348 | 13.1 |
| `validate_render_effects27` | 424 | 1.9 |
| `validate_render_effects28` | 630 | 2.8 |
| `validate_render_effects3` | 720 | 1.5 |
| `validate_render_effects30` | 452 | 0.6 |
| `validate_render_effects31` | 66051 | 323.9 |
| `validate_render_effects32` | 1723 | 1.2 |
| `validate_render_effects33` | 6410 | 24.0 |
| `validate_render_effects35` | 4424 | 5.3 |
| `validate_render_effects4` | 1920 | 8.3 |
| `validate_render_effects5` | 1190 | 7.3 |
| `validate_render_effects6` | 1000 | 2.5 |
| `validate_render_effects7` | 596 | 3.8 |
| `validate_render_effects9` | 304 | 3.3 |
| `validate_session_party` | 200 | 0.8 |
| `validate_skill_fx` | 660 | 1.5 |
| `validate_terrain` | 583500 | 413.9 |
| `validate_terrain_remaining` | 2147 | 5.2 |
| `validate_viewport_monsters` | 1963 | 12.9 |
| `validate_world_particle_consumers` | 900 | 1.3 |
| `validate_worlds_after6` | 7300 | 72.0 |
| `validate_worlds_d` | 2400 | 5.2 |
| `validate_worlds_f` | 1818 | 0.6 |
| `validate_worlds_fog` | 4044 | 8.5 |
| `validate_worlds_l` | 1260 | 1.6 |
| `validate_worlds_m` | 1080 | 2.0 |

Steward validators (at `fc459bc6`): validate_combat,validate_items,validate_meshdraw,validate_model_light,validate_model_edge,validate_movement,validate_skill_fx,validate_path,validate_viewport_monsters,validate_terrain_remaining,validate_icarus_c2,validate_worlds_d,validate_worlds_f,validate_audio_callers,validate_audio_combat,validate_render_effects,validate_render_effects3,validate_render_effects4,validate_render_effects5,validate_render_effects6,validate_render_effects7,validate_render_effects9,validate_render_effects10,validate_render_effects11,validate_render_effects12,validate_world_particle_consumers,validate_audio_domains,validate_audio_items,validate_worlds_l,validate_session_party,validate_audio_charsel,validate_worlds_m,validate_worlds_after6,validate_terrain,validate_app_polish1,validate_app_polish4,validate_render_effects13,validate_render_effects14,validate_render_effects15,validate_render_effects16,validate_worlds_fog,validate_render_effects17,validate_item_callers,validate_inventory_fx,validate_render_effects18,validate_render_effects19,validate_render_effects20,validate_render_effects21,validate_render_effects22,validate_render_effects23,validate_render_effects24,validate_render_effects27,validate_render_effects25,validate_actor_recipes,validate_charsel_items,validate_render_effects26,validate_actor_composites,validate_audio_objects,validate_render_effects28,validate_render_effects30,validate_items_ui,validate_item_hiddenmesh,validate_audio_objects4,validate_audio_monsters,validate_audio_kubera,validate_actor_monsters,validate_muun_transition,validate_render_effects32,validate_render_effects31,validate_actor_plain,validate_audio_monsters6,validate_render_effects33,validate_render_effects35,validate_actor_groups

## Limits and next lane

- Group G: 232 and 2043 share the area-end body `0x013a99b4` (two `0x51a/0`, `0x461` with skill
  word `0x7fb`, two sounds) and the step `0x0139b2fd`; 2043 also writes a target position from a
  key lookup and terrain height. 1501 and 2040 share the position body `0x0125d1b5` (bone, mount,
  target and terrain services, two `0x6a2/0`); 2040 adds the area end `0x013a955a`. 723 has the
  Death-Stab-like step body `0x01397e0b` (`0x472/0x12`, `0x10e6/1`, `0x406/5`). Each is a single
  hand trace; the verifier's harness (authored frame, switch-join exits) applies as is.
- 76 (both classes) needs the mount pose helper and a mount body; 813 and 426 have no case in
  either receive switch.
- The hero's own use routines (`0x01080169`, `0x01085bc3`, dispatcher `0x0107f400..0x0107f638`)
  hold the hero-side part of the ten branching rows and of 813. They also hold request sends and
  are outside this lane: static pointers only.
- Missing consumers: 34 effects and 5 joints in the CSV, plus the arrow callers for the volley
  word `0x7ff` and base 46. The second link setter `0x00d9013e` (types `0x7ee`, `0xa2f`) is not
  recovered.
- Unchanged: skill 47 and stale entries, Defense's held input, the summons' actor spawn, Fire
  Breath's mount body, eligibility, damage, mana, cooldown, server keys, packets, power.

## Delivery

Draft PR, WIP. The lane's scratch, renders and build outputs are deleted; the worktree
`~/Documents/MTM/worktrees/render-effects-035` and the branch are kept for the next agent. No new
private input needs keeping.
