# RENDER-EFFECTS-028

PR-ready. The final staged repository audit passed. Branch `codex/render-effects-028`,
base and latest merged main `d4af71dd`. The merge steward owns integration
and the full gate. The installed Native Preview and both Wine apps are untouched.

## What draws now

An opt-in hero appearance fixture casts Greater Defense 27 and Greater Damage
28 with independent authored expiry clocks. Defense draws five persistent
`0x472/4` orbiting ribbons and their midpoint `0x7fdd` flares. Damage draws
six `0x7f67` weapon-link sprites per complete frame. Its transient joint
requests follow the original's attack-only retirement behavior. The auras end
at authored expiry or hero death; a later respawn does not restore the flags.
No target HP, buff value, stat or authoritative state is changed.

Set `MU_AURA_FIXTURE_TICKS=20` for the demonstrated fixture. Absent, invalid,
zero or negative settings leave it disabled. A cast selects the hero's demo
flag even when a script names a synthetic target. This is not a cast result
or real buff duration. It uses five dedicated slots, ordinals 0..4, and authored
Player link bones 33/42. Missing/dummy bones are refused and counted.

[Research and addresses](../research/client-render-effects-028.md),
[coverage inventory](../research/client-skill-visual-coverage.md).

## Original evidence

Pinned text/data identities are recorded in the research note. The bounded
RenderCharacter consumer is `0x01370ccc..0x01371132`, presence accessor
`0x01295ade`, joint existence `0x01553b41`, subtype-4 creation
`0x01548998..0x01548a09`, movement `0x01569cda..0x0156c46a`, and the per-tail
height fade/midpoint flare at `0x0158a5a4..0x0158a955`. Texture startup calls
are `0x01822885` and `0x01822045`.

The validator compares ordered complete requests, bone queries, RNG, modeled
records, normalized GL calls and ten independent creation-to-removal sequences.
Each sequence carries original bytes through 37 moves, with moving owners,
expiry or owner-live removal, across every fixture ordinal. The selected
MoveJoint branch retires directly, rather than calling DeleteJoint.
The ordinary equipment lookup service answers NULL. General link selection,
equipment-driven subtype 9 and the null-owner render path remain unadmitted.
The latter reads an uninitialized local for its midpoint sprite color.

The initial comparator exposed the extra per-tail draw behavior. It was
implemented and compared before pixel proof. An initial mutant attempt stopped
on an ambiguous text anchor; the unique-anchor successful run below supersedes
that attempt. No stopped original-machine case counts as a caught mutant.

## Checks

Commands ran from the repository root. Heavy work used nice 10, make at most
four jobs, validator runners at two jobs, and one heavy lane command at a time.
Resource pauses were observed. No full gate ran in the lane.

| Check | Result | Wall seconds |
|---|---|---:|
| Root build | pass | 11.36 |
| Explicit world build | pass | 5.64 |
| World rebuild immediately before after sweep | pass | 0.22 |
| Full focused original proof | 4,390 cases, zero mismatches; 18/18 compiled production-C mutants caught, zero machine stops | 49.71 |
| Changed bitmap checker and mutants | 424 cases; all 39 combat bitmap slots checked, including the two added loader sites; 23/23 compiled mutants caught | 34.39 |
| Portable affected run | 162 work items; 1,742 tests, 1,453 passed, 289 skipped, zero failures/errors | 518.00 |
| Private focused native consumers | 4/4 passed: both aura fixture tests, bitmap host, installed-data combat | 9.33 |
| Affected private validators | 56/56 pass, 845,840 reported row cases, zero fail/error/skip | 1029.71 |
| Installed-data GL before/after/repeat fixtures | pass, ten after/repeat PNG pairs identical | 10.03 |
| Default before sweep | 46 captures | 121.17 |
| Default after sweep and comparison | 92 PNGs and 92 OBJECT/light dumps byte-identical; 46 output-path-normalized JSON streams identical | 79.22 |
| Repository audit | 2,190 staged files, zero rejected | 25.16 |

The portable wall is the outer command, including selection; the runner's
post-selection wall is 409.5 s. Validator row times appear below. The full
private command began at `4f616859`; all compiled inputs match `a3762b6a`.
The bitmap checker correction at `a3762b6a` preceded execution of that row and
its importers. Later checkpoints and final edits change docs only.

**8d reduced:** the private native selection is 163 work items, above the
40-item cap. The changed native consumers ran with canonical private-env;
the new original comparison is covered both by the full focused proof and by
the registry's 630-case private row. Portable private skips do not count as
private evidence. The bitmap checker groups the two added site checks with its
existing census, preserving its 424-case registry budget. Its changed checker
received its own 23-mutant run. Other affected rows ran without mutants.

## Native fixture render evidence

The GL scene uses the committed authored hero name, class 2, sword, tile
182,127, and `actor 3 184 127 0 label DemoTarget`. It runs one cast at frame 2,
stop at frame 3, 34 frames, 960 by 600, captures 0/10/20/30/33, and renders each
logic frame with `--time-series-every 1`. Audio, other players and items are
disabled. These are native renders, not original-client screenshots.

| Counter | Before 27 | After 27 | Before 28 | After 28 |
|---|---:|---:|---:|---:|
| Aura visual requests | 0 | 95 | 0 | 209 |
| Aura joint creations | 0 | 5 | 0 | 95 |
| Aura refusals | 0 | 0 | 0 | 0 |
| Live aura records at end | 0 | 0 | 0 | 0 |
| Global combat unsupported requests | 0 | 0 | 0 | 0 |
| Sent / unsent cast requests | 0 / 1 | 0 / 1 | 0 / 1 | 0 / 1 |
| Hits / kills | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| Loaded combat bitmaps | 37 | 39 | 37 | 39 |

Defense has five initial ribbons and 90 midpoint sprite requests. Damage has
95 transient joints and 114 bone sprites, matching nineteen active draws.
Both expire at authored logic step 22. The frame-33 report is step 34,
zero live records and zero aura sprites. Target HP remains fixed in the
portable integration tests. Those tests also check disabled/invalid settings.

All five saved PNGs for each after/repeat pair are byte-identical. For each
skill, frame zero and both expired captures match baseline, while the active
captures differ. Visual inspection shows the colored orbit/flares beside the
hero and the attack glints at the link points. No original GPU equivalence or
performance acceptance is claimed.

## Default identity

Both binaries were explicitly built with `make -C native -j4 world` in this
worktree. The baseline was built before native adapter edits and saved once.
The after build contains the completed adapter. Their hashes differ:

- Before SHA-256: `4954601057b7ee7976c787157b321703d40c65dba68c46901b08d22adb1be76c`.
- After SHA-256: `ddaa0ecdcfe75ec7ff81bd56942f240875b500cbc3e1b5f51385be651e7965c5`.

All 184 PNG/dump artifacts are byte-identical across the 46 default captures.
All 46 JSON streams also match after output-directory normalization. This
checks fixture-disabled identity. It does not establish original-client fidelity.
No before sweep was repeated. Main remained `d4af71dd` on the final fetch/merge.

## Limits and next

The strict skill coverage remains 20 P / 3 L / 0 M. The two new fixture auras
supply pixels and lifecycle controls; authoritative buff input, unrestricted
owner/link selection, equipment-driven subtype 9, real durations, master/later
variants and live image comparisons remain absent. Presence IDs 3, `0x12`,
`0x15a` and `0x15b` are comparator inputs only. No further buff was admitted.
A later lane can research the subtype-9 equipment context and broader owner
links before extending admission.

No protection analysis, network/login/server/packet work, character-power
features, client-memory writes, live client control or installed-app changes
occurred. Item/particle consumers, actor, world, Muun and UI files were not edited.
Shared Makefile and registry additions are minimal. No README work occurred.

## Steward validators

Steward validators: validate_actor_recipes, validate_app_polish4, validate_audio_callers, validate_audio_charsel, validate_audio_combat, validate_audio_domains, validate_audio_items, validate_charsel_items, validate_combat, validate_icarus_c2, validate_inventory_fx, validate_item_callers, validate_item_hiddenmesh, validate_items, validate_meshdraw, validate_model_edge, validate_model_light, validate_movement, validate_path, validate_render_effects, validate_render_effects10, validate_render_effects11, validate_render_effects12, validate_render_effects13, validate_render_effects14, validate_render_effects15, validate_render_effects16, validate_render_effects17, validate_render_effects18, validate_render_effects19, validate_render_effects20, validate_render_effects21, validate_render_effects22, validate_render_effects23, validate_render_effects24, validate_render_effects25, validate_render_effects27, validate_render_effects28, validate_render_effects3, validate_render_effects4, validate_render_effects5, validate_render_effects6, validate_render_effects7, validate_render_effects9, validate_session_party, validate_skill_fx, validate_terrain, validate_terrain_remaining, validate_viewport_monsters, validate_world_particle_consumers, validate_worlds_after6, validate_worlds_d, validate_worlds_f, validate_worlds_fog, validate_worlds_l, validate_worlds_m

Inputs tested at `a3762b6a`, unchanged through the final docs commit. No further
mutants are needed. Source `~/Documents/MTM/mu-mac-tools/native/private-env.sh`.

| Validator | Wall seconds |
|---|---:|
| `validate_actor_recipes` | 121.9 |
| `validate_app_polish4` | 35.0 |
| `validate_audio_callers` | 5.7 |
| `validate_audio_charsel` | 5.4 |
| `validate_audio_combat` | 30.9 |
| `validate_audio_domains` | 32.3 |
| `validate_audio_items` | 4.0 |
| `validate_charsel_items` | 8.4 |
| `validate_combat` | 1.1 |
| `validate_icarus_c2` | 29.4 |
| `validate_inventory_fx` | 12.0 |
| `validate_item_callers` | 1.6 |
| `validate_item_hiddenmesh` | 505.8 |
| `validate_items` | 3.5 |
| `validate_meshdraw` | 70.3 |
| `validate_model_edge` | 186.1 |
| `validate_model_light` | 9.4 |
| `validate_movement` | 98.1 |
| `validate_path` | 44.9 |
| `validate_render_effects` | 2.1 |
| `validate_render_effects10` | 0.6 |
| `validate_render_effects11` | 0.4 |
| `validate_render_effects12` | 0.4 |
| `validate_render_effects13` | 0.7 |
| `validate_render_effects14` | 1.6 |
| `validate_render_effects15` | 1.0 |
| `validate_render_effects16` | 3.7 |
| `validate_render_effects17` | 8.9 |
| `validate_render_effects18` | 1.7 |
| `validate_render_effects19` | 1.2 |
| `validate_render_effects20` | 0.3 |
| `validate_render_effects21` | 0.4 |
| `validate_render_effects22` | 7.9 |
| `validate_render_effects23` | 8.8 |
| `validate_render_effects24` | 3.0 |
| `validate_render_effects25` | 9.8 |
| `validate_render_effects27` | 1.6 |
| `validate_render_effects28` | 2.2 |
| `validate_render_effects3` | 2.1 |
| `validate_render_effects4` | 7.9 |
| `validate_render_effects5` | 5.7 |
| `validate_render_effects6` | 1.7 |
| `validate_render_effects7` | 2.0 |
| `validate_render_effects9` | 1.2 |
| `validate_session_party` | 0.9 |
| `validate_skill_fx` | 1.4 |
| `validate_terrain` | 477.9 |
| `validate_terrain_remaining` | 8.5 |
| `validate_viewport_monsters` | 22.9 |
| `validate_world_particle_consumers` | 1.1 |
| `validate_worlds_after6` | 92.3 |
| `validate_worlds_d` | 3.9 |
| `validate_worlds_f` | 0.4 |
| `validate_worlds_fog` | 8.0 |
| `validate_worlds_l` | 1.8 |
| `validate_worlds_m` | 1.7 |

## Checkpoints and cleanup

Pushed checkpoints `6c596e2f`, `4f616859`, `a3762b6a` and `16c15d81` preserved
implementation and the WIP done/left/next handoff while checks progressed.
The final push includes the completed docs before the ready-prs entry. Nothing
is pushed after that entry.

Local reports, renders and saved baseline binary under the shared native tools'
`scratch/render-effects-028` and `renders/render-effects-028`, this worktree's
build outputs, the worktree and its local branch are removed after the ready
entry. No new input needs retaining. Shared captures, cache, main checkout and
other lanes are preserved. Reproduce with the canonical private environment,
the documented fixture, `validate_render_effects28.py --cases 1000 --mutations`,
and TEST-BUDGET's affected commands. The steward runs the full gate.
