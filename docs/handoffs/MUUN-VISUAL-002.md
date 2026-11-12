# MUUN-VISUAL-002

PR-ready verified subset. Branch `codex/muun-visual-002`, based on main `d4af71dd`; latest main still matched
that commit at the final check. The merge steward owns integration. Offline/static only: no installed-app
change, live client, network, protection work, original-data commit or README edit.

## What draws

The fifteen attachment appearances now use the original ordinary MuunMeshInfo passes and base-slot shadow.
Five appearances add eight ordered mesh passes: 174/178/184 one each, 176 two, 363 three. Six extra texture
overrides load, with pulsing blend light and 363's RGB/alpha passes. The other ten appearances need no extra
rows. All sixteen existing attachments and bone/owner safety remain intact.

`MU_MUUN_FIXTURE=<id>` selects the authored appearance. Adding `MU_MUUN_COMMAND_FIXTURE=50..55` supplies a
synthetic same-owner command every 100 logic steps. Categories 50/53 request action 3; 51/52/54/55 request
4; the existing animation-end state returns to idle. Fourteen actual models support both actions. Code 363
has only actions 0..2 and refuses both commands. [Addresses, field audit and class census](../research/client-muun.md).

The installed MuunInfo table has no auxiliary categories 50..99. The command category and target are therefore
explicit authored inputs, not inferred production behavior. No demo hero receives an implicit Muun record:
an in-scope source of authoritative owner slot selection was not established, so the permitted environment
switch remains.

## Final checks

All commands ran from the repository root, with nice 10, make at most four jobs and runners two workers.
Private checks source `~/Documents/MTM/mu-mac-tools/native/private-env.sh`. Resource guards caused waits.
No lane full gate or hosted workflow ran.

| Check | Result | Wall |
|---|---|---:|
| Final full build | pass | 9.42 s |
| Focused private native Muun module | 6/6 pass: all fifteen skeletons, sixteen attachments, exact matrices, owner retirement, command pose/end/refusal, bad mesh/missing texture controls, GL/software pixel differences | 13.28 s |
| Final installed-record comparator refresh | 1,406 cases, zero mismatches: 1,045 mesh-caller cases, 105 command cases, 256 shadow cases | 0.91 s |
| New `validate_muun_passes`, one-time mutants | 1,361 synthetic cases, zero mismatches; 15/15 compiled mutants caught under `-Werror` | 13.21 s |
| Affected portable batch | 1,412 tests: 1,170 passed, 242 skipped, zero failures/errors, 153 work items | 494.96 s including selection; 378.0 s execution |
| Affected private validators | 28/28 pass; 691,785 reported row cases, no requested mutant reruns | 697.47 s including selection |
| Native proof | 17 GL renders: fifteen appearances and two command examples; all visible, zero missing textures/refused meshes/refused bones; contact sheet inspected | 17.98 s |
| Default before sweep | 46 captures, no draw-all/live-time, 640x400 | 32.85 + 82.09 s |
| Default after sweep | 92/92 PNGs and 92/92 OBJECT/light dumps byte-identical | 28.65 + 66.38 s |
| Report environment control | Ferea final binary with baseline environment reproduces both PNGs, both dumps and path-normalized report exactly | 2.13 s |
| Repository audit | 2,187 staged files, zero rejected | 24.52 s |

**8d reduced:** native affected selection exceeds 40 items. The changed native Muun module ran privately;
the final installed-record comparison refresh used the completed checker. Shared-symbol grep found no other
host using the new Muun functions or changed struct fields. The broad portable selection and all selected
validator rows, including fallbacks, were retained.

The private validator batch records commit `28301444`; its compiled/checker inputs equal `27627248`.
The one-time mutant run records head `926c0612` with then-working checker/test edits subsequently committed
as `27627248`. Final target/checker contents are the ones tested; later edits are documentation only.
The unchanged base-slot comparison still passes its 912 original cases. No unchanged mutant set was rerun.

## Default identity and environment limit

Both binaries were explicitly built with `make -C native -j4 world` before their sweeps.
Before, main `d4af71dd`: `601057b7ee7976c787157b321703d40c65dba68c46901b08d22adb1be76c`.
After: `eb7853668e46c82d4c2581780c80cf033077b788a753c90aade75db6b4d98f85`.
These are different binaries. All 92 PNGs and all 92 OBJECT/light dumps match byte for byte.

Fourteen October-22 path-normalized reports also match exactly. The DATA-ACQ-002 baseline inadvertently
omitted the canonical private environment. Its 32 reports differ only in `units`/`moves`/`gates` table counts,
an added quest summary row, and `session_skills.selected` 0 -> 19. All other fields match. The single-map
Ferea control, using the final binary with the baseline environment, reproduces the whole report as well as
its PNGs and dumps. Thus **14/46 reports are path-normalized identical**, with the other 32 carrying a named
environment difference. They are not claimed byte-identical. The before baseline was not rerun.

## Steward validators

Steward validators: validate_actor_recipes, validate_audio_callers, validate_audio_charsel, validate_audio_combat, validate_audio_domains, validate_audio_items, validate_charsel_items, validate_icarus_c2, validate_inventory_fx, validate_item_callers, validate_meshdraw, validate_model_edge, validate_model_light, validate_movement, validate_muun_passes, validate_muun_visual, validate_path, validate_render_effects16, validate_render_effects17, validate_render_effects18, validate_render_effects19, validate_render_effects24, validate_render_effects25, validate_session_party, validate_terrain, validate_terrain_remaining, validate_viewport_monsters, validate_worlds_f

All 28 rows below pass at `28301444`, with the compiled inputs from `27627248`. No mutants are needed in
the steward run; the new row's 15 compiled mutants already passed once. Canonical private-env.sh supplies
MU_GAME_ROOT, MU_SECTION3, MU_EVIDENCE_DIR, MU_NATIVE_DATA_DIR, MU_LANG_DIR and row-specific inputs.

| Validator | Reported cases | Wall |
|---|---:|---:|
| `validate_actor_recipes` | 1,300 | 102.1 s |
| `validate_audio_callers` | 5,528 | 7.4 s |
| `validate_audio_charsel` | 5,968 | 5.6 s |
| `validate_audio_combat` | 19,548 | 42.4 s |
| `validate_audio_domains` | 2,544 | 37.4 s |
| `validate_audio_items` | 3,000 | 4.9 s |
| `validate_charsel_items` | 8,817 | 12.3 s |
| `validate_icarus_c2` | 8,400 | 25.9 s |
| `validate_inventory_fx` | 8,017 | 6.9 s |
| `validate_item_callers` | 6,013 | 1.5 s |
| `validate_meshdraw` | 14,619 | 73.5 s |
| `validate_model_edge` | 954 | 186.0 s |
| `validate_model_light` | 1,433 | 8.4 s |
| `validate_movement` | 6,614 | 93.1 s |
| `validate_muun_passes` | 1,361 | 2.1 s |
| `validate_muun_visual` | 912 | 1.0 s |
| `validate_path` | 4,719 | 32.4 s |
| `validate_render_effects16` | 424 | 4.2 s |
| `validate_render_effects17` | 618 | 9.0 s |
| `validate_render_effects18` | 540 | 1.0 s |
| `validate_render_effects19` | 400 | 0.8 s |
| `validate_render_effects24` | 226 | 2.2 s |
| `validate_render_effects25` | 202 | 7.9 s |
| `validate_session_party` | 200 | 1.0 s |
| `validate_terrain` | 583,500 | 448.9 s |
| `validate_terrain_remaining` | 2,147 | 5.8 s |
| `validate_viewport_monsters` | 1,963 | 13.3 s |
| `validate_worlds_f` | 1,818 | 0.5 s |

## Limits and next

This PR delivers the verified base-slot mesh/shadow and same-owner pose subset. It does not close every
auxiliary Muun visual. The separate kind-1 secondary OBJECT, its action mapping, rider/mount-selection gate,
named attachment and model-specific effects are static-audited, not implemented or counted as complete.
That applies to eight other installed ids, 16/17/100..105, not the fifteen appearances proved here.

Remote-owner command motion, original helper timer parity and `0x47a` transition effects remain static.
Later special mesh models `0x2b7a/b`, `0x2b8d/e` and `0x2b90` remain refused by the ordinary extra-row adapter.
The native shadow fixture supplies ordinary owner kind 1 and option 0. `--no-particles` suppresses its shared
shadow renderer. Missing, dummy and out-of-range bones stay refused. No original full-scene/live-motion
or strict-performance equivalence is claimed. No packets, inventory, bonuses, damage or authoritative target feed.

The next bounded lane can add a synthetic kind-1 active-mount lease with both models, the separate action
mapping and exact attachment names. Production slot selection still requires a separately authorized input.

## Checkpoints and cleanup

WIP checkpoints were pushed at `926c0612` and `28301444`, each with done/left/next handoff content. The final
PR contains the verified subset rather than holding it for the remaining secondary-body work. No future-lane
input was created. Generated renders, reports, decoded scratch, build outputs, worktree and local branch are
removed after the ready queue entry; the remote PR branch remains for the steward.
