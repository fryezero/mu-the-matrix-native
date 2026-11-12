# RENDER-ITEMS-002Y

Branch `codex/render-items-002y`, following #361 at `3732f82a`. Codex, GPT-6.1 Sol; no subagents.
Offline/static only. Research is [part 38](../research/client-render-items.md#part-38-later-read-programs-and-body-caller-helper-flow-render-items-002y).
Main `626abce17f0a` is merged at `0ac7cc03d775`. The lane runs affected checks; the merge steward owns the full gate and merge.

## Result

Bodies **1,424 -> 1,465 of 1,674**, leaving **209**. Six later read programs, eight helper-count bodies
and 27 further bodies are admitted. Skins remain 17/17; links remain eighteen targets/twenty-four types.
Complete pinned extraction emits 1,446 type rows, a 514,029-byte body header and a 295,763-byte owner
header. The 24-scalar, twelve-operation, sixteen-draw and 512-KiB audit limits are unchanged.

The six read types are `0x0b4d`, `0x1314`, `0x230d`, `0x23f0`, `0x23f2` and `0x2497`.
The scalar reader preserves separate wave phase, reversed wave, lower clamp, signed local division,
clock sine, conditional abs and CRT fabs. It follows only the reviewed pure calls and stores.
The six complete owned programs also retain exact ordered requests/refusals and scripted random use.

`0x2368` omits its base draw. Types `0x26e6..0x26ec` force a positive effective level to seven in the
body caller, after record and quality remapping; zero stays zero. The public scalar-remap function
keeps its existing contract. Forcing fixtures enumerate both kind-B records, kind A 0/6, all sixteen
levels, qualities 0/1/2/9 and both tail settings. Raw input items and records remain unchanged.

The 27 further bodies and their carry rules are listed in part 38. Every new body passes the 292-state
independent sample. Directed clocks and counters supplement the forcing-record cases. Negative-zero
probes distinguish six final positive-zero additions from otherwise identical saved intermediates.
This preserves the original helper semantics rather than normalizing all zeros. Five earlier bodies
now use direct clock-sine chains; all 57 historical derived types retain their original comparisons,
and the explicit kind-6 count changes from 118 to 113.

The native C-to-C sample changes exactly 41 memberships, 128 states each, and no earlier result.
The classifier changes exactly 41 memberships and 31 shape totals: complete shapes 609 -> 640 of 798.
Raw survey shapes, addresses, classifications and stopped-state summaries stay unchanged.
The survey's 1,691 denominator includes the seventeen skins; the body denominator is 1,674.

## Checks and environment

All test/tool commands run from the repository root. Private commands source
`~/Documents/MTM/mu-mac-tools/native/private-env.sh`, including `MU_SECTION3`, `MU_GAME_ROOT`,
`MU_EVIDENCE_DIR`, `MU_NATIVE_DATA_DIR`, snapshot and render-time inputs. Heavy work runs at nice 10,
make at most four jobs and validator runners two workers. Load, memory and disk checks precede jobs;
load above 14 caused cooldowns. No full lane gate or hosted workflow ran.

Brief 6b consumer review includes `test_native_renderchar.py` and `test_app_polish8.py`. The initial
private native selection is 147 work items, above the forty-item cap, so this lane uses **8d reduced**
and runs those two modules privately from the root. Portable selection and instruction validators are
separate runs; private mutants are not accidentally repeated by the portable suite.

| Check | Result | Wall |
|---|---|---:|
| Complete body and owner table regeneration | 1,446 type rows; unchanged caps | 1,296.19 s |
| Old-fold directed-clock preflight | 120 cases match saved prerequisite C and original instructions | 1.54 s |
| Portable renderchar suite | 126 tests, 99 passed / 27 private skips | 0.44 s |
| Full classifier export | 1,691 types / 798 shapes, exactly 41 membership and 31 shape-total changes | 81.68 s |
| Initial affected portable run | 152 work items; 1,421 tests, 1,180 passed / 241 skipped | 523.96 s |
| First main-merge root build | Pass | 23.93 s |
| Latest main-merge root build | Pass | 11.97 s |
| Final main-merge root build | Pass | 0.58 s |
| Latest affected portable run | 173 work items; 1867 tests, 1550 passed / 317 skipped, zero failures/errors | 572.00 s |
| Canonical private renderer and App Polish 8 | 33/33 passed, zero skips; 8d reduced | 14.54 s |
| Genuine-main renderchar build | Pass | 0.60 s |
| Genuine-main explicit world build | Pass | 7.14 s |
| Genuine-main default sweep | 46 captures, draw_all=false, live_time=false | 97.61 s |
| Restored branch root build | Pass | 21.72 s |
| Restored branch explicit world build | Pass | 8.49 s |
| Fresh-main C-to-C admission delta and old-fold clocks | 216,448 states: 211,200 identical, 5,248 admissions on exactly 41 types; 120 additional old-fold clocks match original and main | 23.78 s |
| Final default identity | 92 PNGs, 92 mesh dumps and 46 normalized reports identical | 78.89 s |
| Affected no-mutant validators at `90f61f89a399` | 59/59 passed, zero failures/errors | 3,626.11 s |
| Merged no-mutant validators at `80510f6ffb56` | 63/63 passed, zero failures/errors | 917.38 s |
| Latest no-mutant validators at `763d33303ea9` | 66/66 passed, zero failures/errors | 763.74 s |
| Post-ui no-mutant validators at `0ac7cc03d775` | 10/10 passed, zero failures/errors | 63.10 s |

Documentation consumers pass: 36 tests, 35 passed / 1 skipped, zero failures/errors, 12.41 s. Final source audit is recorded in the PR body.

The latest portable runner wall is 438.1 s; wrapper times include selection where selection is part of the command. Resource cooldowns are outside these job timings.
The final PR selection contains 62 rows and 991,788 recorded cases. Unchanged rows retain their earlier passing result; the merge selectors rerun every row whose compiled inputs changed. These are finite recorded case totals, not a unique whole-client state count.

Changed-row mutants ran once per final target: helper groups 6,432 cases / 4 mutants, 36.0 s; historical derived bodies 36,252 cases / 7 mutants, 314.6 s; corrected read programs 5,352 cases / 6 mutants, 30.0 s; corrected other bodies 24,084 cases / 3 mutants, 108.0 s. All twenty compiled mutants are caught. The final read/other batch wall is 108.11 s. The derived metadata recheck is 0.07 s; its 113-program expectation preserves all 57 historical type comparisons. No steward mutants are requested.

## Default identity provenance

Genuine main `626abce17f0a0c874c5481cd73b59ec129409f61` is built inside this lane worktree by temporarily overlaying only the three runtime files that differ from main: `renderchar.c`, `item_bodies.h` and `item_owner_fx.h`. Their committed branch bytes are saved and restored in `finally`; the index stays on the branch. Main and all other worktrees remain untouched. Each side explicitly runs `make -C native -j4 world`, reduced to two jobs if required by the resource cooldown.

- Before `mu-world` SHA-256: `0486f35e813b641f2500df6b0107515c33d3fb37d2cc3683005c8b91b08b10ef`.
- After `mu-world` SHA-256: `7a6d245c7e85eb024f0ae42f6f9e7ad20f65bfcf0b23ef2f34a5bc11a43b8528`.

The hashes differ. Both sweeps use the same canonical private environment, 640 x 400 dimensions, default draw and fixed time over both existing capture manifests. Every capture has two PNGs, two mesh dumps and one report. Output-directory text is normalized in reports; no other report fields or bytes are removed. All 230 artifacts match. No original-client pixel equivalence is claimed.

## Steward validators

Steward validators: validate_item_ranked,validate_item_continuation,validate_item_expansion,validate_item_clusters,validate_item_types,validate_fidelity,validate_meshdraw,validate_model_edge,validate_movement,validate_renderchar,validate_item_read_programs,validate_icarus_c2,validate_audio_callers,validate_item_gear,validate_item_next,validate_render_effects5,validate_render_effects7,validate_render_effects9,validate_render_effects10,validate_render_effects11,validate_render_effects12,validate_audio_domains,validate_audio_items,validate_item_coverage,validate_item_wings_next,validate_item_scalars,validate_item_chains,validate_item_carry,validate_item_quality,validate_item_product,validate_item_derived,validate_item_ownerfx,validate_item_predraw,validate_item_hiddenmesh,validate_render_effects13,validate_render_effects14,validate_render_effects15,validate_render_effects16,validate_render_effects17,validate_item_callers,validate_inventory_fx,validate_render_effects18,validate_render_effects19,validate_render_effects20,validate_render_effects21,validate_item_cloak,validate_armour_cloak,validate_render_effects22,validate_item_named,validate_npc_cloak,validate_render_effects23,validate_render_effects24,validate_render_effects27,validate_item_groups,validate_render_effects25,validate_actor_recipes,validate_item_helper_groups,validate_item_other_bodies,validate_charsel_items,validate_audio_objects,validate_render_effects28,validate_items_ui

Use the canonical private environment above, `--private --no-mutants --cache --jobs 2`. Source commits and walls are recorded per row below. The latest merge leaves this lane's three runtime files unchanged; selectors establish which earlier compiled inputs remain identical. Every fallback retained by the final selector is kept in this list.

| Validator | Cases | Wall | Tested source |
|---|---:|---:|---|
| `validate_item_ranked` | 17,736 | 229.6 s | `90f61f89a399` |
| `validate_item_continuation` | 25,772 | 285.5 s | `90f61f89a399` |
| `validate_item_expansion` | 52,172 | 390.6 s | `90f61f89a399` |
| `validate_item_clusters` | 74,292 | 504.4 s | `90f61f89a399` |
| `validate_item_types` | 135,176 | 49.6 s | `90f61f89a399` |
| `validate_fidelity` | 991 | 92.5 s | `90f61f89a399` |
| `validate_meshdraw` | 14,619 | 82.1 s | `763d33303ea9` |
| `validate_model_edge` | 954 | 151.0 s | `763d33303ea9` |
| `validate_movement` | 6,614 | 50.2 s | `763d33303ea9` |
| `validate_renderchar` | 1,706 | 43.5 s | `90f61f89a399` |
| `validate_item_read_programs` | 5,352 | 19.7 s | `90f61f89a399` |
| `validate_icarus_c2` | 8,400 | 22.4 s | `763d33303ea9` |
| `validate_audio_callers` | 5,528 | 9.3 s | `0ac7cc03d775` |
| `validate_item_gear` | 25,256 | 207.4 s | `90f61f89a399` |
| `validate_item_next` | 14,992 | 259.3 s | `90f61f89a399` |
| `validate_render_effects5` | 1,190 | 3.1 s | `80510f6ffb56` |
| `validate_render_effects7` | 596 | 1.6 s | `80510f6ffb56` |
| `validate_render_effects9` | 304 | 1.0 s | `80510f6ffb56` |
| `validate_render_effects10` | 154 | 0.3 s | `80510f6ffb56` |
| `validate_render_effects11` | 176 | 0.2 s | `80510f6ffb56` |
| `validate_render_effects12` | 64 | 0.3 s | `80510f6ffb56` |
| `validate_audio_domains` | 2,544 | 31.9 s | `0ac7cc03d775` |
| `validate_audio_items` | 3,000 | 5.2 s | `0ac7cc03d775` |
| `validate_item_coverage` | 31,724 | 331.2 s | `90f61f89a399` |
| `validate_item_wings_next` | 33,622 | 356.0 s | `90f61f89a399` |
| `validate_item_scalars` | 26,274 | 244.0 s | `90f61f89a399` |
| `validate_item_chains` | 35,406 | 282.0 s | `90f61f89a399` |
| `validate_item_carry` | 114,388 | 902.8 s | `90f61f89a399` |
| `validate_item_quality` | 28,080 | 243.2 s | `90f61f89a399` |
| `validate_item_product` | 2,874 | 143.2 s | `90f61f89a399` |
| `validate_item_derived` | 36,252 | 268.8 s | `90f61f89a399` |
| `validate_item_ownerfx` | 14,964 | 319.2 s | `90f61f89a399` |
| `validate_item_predraw` | 42,540 | 435.6 s | `90f61f89a399` |
| `validate_item_hiddenmesh` | 116,281 | 532.6 s | `80510f6ffb56` |
| `validate_render_effects13` | 180 | 0.4 s | `80510f6ffb56` |
| `validate_render_effects14` | 660 | 1.0 s | `80510f6ffb56` |
| `validate_render_effects15` | 509 | 0.6 s | `80510f6ffb56` |
| `validate_render_effects16` | 424 | 5.2 s | `0ac7cc03d775` |
| `validate_render_effects17` | 618 | 8.3 s | `763d33303ea9` |
| `validate_item_callers` | 6,013 | 3.0 s | `763d33303ea9` |
| `validate_inventory_fx` | 8,017 | 9.7 s | `763d33303ea9` |
| `validate_render_effects18` | 540 | 2.5 s | `763d33303ea9` |
| `validate_render_effects19` | 400 | 1.4 s | `763d33303ea9` |
| `validate_render_effects20` | 148 | 0.2 s | `80510f6ffb56` |
| `validate_render_effects21` | 267 | 0.3 s | `80510f6ffb56` |
| `validate_item_cloak` | 5,694 | 151.5 s | `90f61f89a399` |
| `validate_armour_cloak` | 4,448 | 50.6 s | `90f61f89a399` |
| `validate_render_effects22` | 202 | 6.1 s | `80510f6ffb56` |
| `validate_item_named` | 20,057 | 182.4 s | `90f61f89a399` |
| `validate_npc_cloak` | 2,619 | 46.7 s | `90f61f89a399` |
| `validate_render_effects23` | 1,174 | 6.6 s | `80510f6ffb56` |
| `validate_render_effects24` | 226 | 4.7 s | `763d33303ea9` |
| `validate_render_effects27` | 424 | 1.0 s | `80510f6ffb56` |
| `validate_item_groups` | 4,824 | 33.1 s | `90f61f89a399` |
| `validate_render_effects25` | 202 | 10.6 s | `763d33303ea9` |
| `validate_actor_recipes` | 1,669 | 128.3 s | `763d33303ea9` |
| `validate_item_helper_groups` | 6,432 | 24.2 s | `90f61f89a399` |
| `validate_item_other_bodies` | 24,084 | 85.0 s | `90f61f89a399` |
| `validate_charsel_items` | 8,817 | 9.2 s | `763d33303ea9` |
| `validate_audio_objects` | 4,000 | 4.1 s | `763d33303ea9` |
| `validate_render_effects28` | 630 | 2.3 s | `763d33303ea9` |
| `validate_items_ui` | 8,517 | 12.0 s | `0ac7cc03d775` |

Rows without a case-count field are marked not reported and are excluded from summed case totals.

Additional rows required only by merged-main changes are also passing; they are not added to the PR selection.

| Merge-only validator | Cases | Wall | Tested source |
|---|---:|---:|---|
| `validate_app_polish1` | 752 | 41.7 s | `0ac7cc03d775` |
| `validate_app_polish2` | 1,028 | 5.9 s | `0ac7cc03d775` |
| `validate_app_polish4` | 10,485 | 62.0 s | `80510f6ffb56` |
| `validate_app_polish7` | 5,120 | 3.4 s | `0ac7cc03d775` |
| `validate_audio_charsel` | 5,968 | 4.0 s | `80510f6ffb56` |
| `validate_audio_combat` | 19,548 | 33.0 s | `80510f6ffb56` |
| `validate_charsel_world` | 1,200 | 2.6 s | `763d33303ea9` |
| `validate_combat` | 496 | 0.9 s | `80510f6ffb56` |
| `validate_gfx3` | not reported | 10.5 s | `0ac7cc03d775` |
| `validate_icarus` | 5,240 | 33.1 s | `763d33303ea9` |
| `validate_items` | 444 | 2.4 s | `80510f6ffb56` |
| `validate_login_world` | 1,200 | 2.8 s | `763d33303ea9` |
| `validate_map_polish` | 876 | 0.7 s | `0ac7cc03d775` |
| `validate_model_light` | 1,433 | 5.7 s | `763d33303ea9` |
| `validate_muun_passes` | 1,361 | 2.0 s | `80510f6ffb56` |
| `validate_muun_visual` | 912 | 2.3 s | `80510f6ffb56` |
| `validate_object_render` | 1,984 | 3.8 s | `763d33303ea9` |
| `validate_path` | 4,719 | 29.9 s | `80510f6ffb56` |
| `validate_render_effects` | 660 | 1.4 s | `80510f6ffb56` |
| `validate_render_effects3` | 720 | 1.2 s | `80510f6ffb56` |
| `validate_render_effects4` | 1,920 | 7.4 s | `80510f6ffb56` |
| `validate_render_effects6` | 1,000 | 1.5 s | `80510f6ffb56` |
| `validate_render_worlds_a` | 9,000 | 13.6 s | `763d33303ea9` |
| `validate_session_party` | 200 | 0.9 s | `80510f6ffb56` |
| `validate_skill_fx` | 660 | 1.1 s | `80510f6ffb56` |
| `validate_terrain` | 583,500 | 440.4 s | `763d33303ea9` |
| `validate_terrain_remaining` | 2,147 | 4.6 s | `763d33303ea9` |
| `validate_viewport_monsters` | 1,963 | 11.1 s | `80510f6ffb56` |
| `validate_world_fidelity` | 200 | 0.2 s | `763d33303ea9` |
| `validate_world_light_name` | 304 | 0.5 s | `763d33303ea9` |
| `validate_world_particle_consumers` | 900 | 1.0 s | `80510f6ffb56` |
| `validate_world_tile_folder` | 5,700 | 51.5 s | `763d33303ea9` |
| `validate_worlds_121` | 4,000 | 4.7 s | `763d33303ea9` |
| `validate_worlds_after` | 13,424 | 16.0 s | `763d33303ea9` |
| `validate_worlds_after2` | 32,216 | 32.9 s | `763d33303ea9` |
| `validate_worlds_after3` | 10,212 | 10.2 s | `763d33303ea9` |
| `validate_worlds_after4` | 9,181 | 15.1 s | `763d33303ea9` |
| `validate_worlds_after5` | 6,000 | 11.6 s | `763d33303ea9` |
| `validate_worlds_after6` | 7,300 | 52.8 s | `763d33303ea9` |
| `validate_worlds_b` | 4,000 | 3.7 s | `763d33303ea9` |
| `validate_worlds_d` | 2,400 | 4.3 s | `763d33303ea9` |
| `validate_worlds_e` | 4,840 | 17.7 s | `763d33303ea9` |
| `validate_worlds_f` | 1,818 | 0.5 s | `763d33303ea9` |
| `validate_worlds_fog` | 4,044 | 12.0 s | `80510f6ffb56` |
| `validate_worlds_g` | 6,000 | 4.2 s | `763d33303ea9` |
| `validate_worlds_g2` | 2,657 | 8.3 s | `763d33303ea9` |
| `validate_worlds_g3` | 4,000 | 6.2 s | `763d33303ea9` |
| `validate_worlds_h` | 6,000 | 4.3 s | `763d33303ea9` |
| `validate_worlds_i` | 6,000 | 4.7 s | `763d33303ea9` |
| `validate_worlds_inner` | 4,000 | 4.1 s | `763d33303ea9` |
| `validate_worlds_inner2` | 5,000 | 4.9 s | `763d33303ea9` |
| `validate_worlds_j` | 6,000 | 4.4 s | `763d33303ea9` |
| `validate_worlds_k` | 6,000 | 4.9 s | `763d33303ea9` |
| `validate_worlds_karutan` | 3,000 | 4.0 s | `763d33303ea9` |
| `validate_worlds_l` | 1,260 | 1.5 s | `80510f6ffb56` |
| `validate_worlds_m` | 1,080 | 1.4 s | `80510f6ffb56` |
| `validate_worlds_n` | 13,000 | 9.4 s | `763d33303ea9` |
| `validate_worlds_o` | not reported | 6.8 s | `763d33303ea9` |
| `validate_worlds_p` | 10,000 | 8.9 s | `763d33303ea9` |
| `validate_worlds_p2` | 6,000 | 5.7 s | `763d33303ea9` |
| `validate_worlds_q` | 11,000 | 20.9 s | `763d33303ea9` |
| `validate_worlds_q2` | 4,000 | 8.7 s | `763d33303ea9` |
| `validate_worlds_r` | 12,000 | 9.9 s | `763d33303ea9` |
| `validate_worlds_r2` | 9,000 | 10.5 s | `763d33303ea9` |
| `validate_worlds_raklion` | 3,000 | 4.4 s | `763d33303ea9` |
| `validate_worlds_s` | 11,000 | 9.3 s | `763d33303ea9` |
| `validate_worlds_s2` | 10,000 | 8.9 s | `763d33303ea9` |
| `validate_worlds_s3` | 22,000 | 20.7 s | `763d33303ea9` |
| `validate_worlds_slots` | 18,999 | 21.2 s | `763d33303ea9` |
| `validate_worlds_slots2` | 33,000 | 37.3 s | `763d33303ea9` |
| `validate_worlds_slots3` | 36,000 | 36.3 s | `763d33303ea9` |

## History and limits

The November 9 session stopped with provisional screens and interrupted generation. Those provisional
counts are superseded by complete regeneration and the checks above. The first resume comparison batch
found an unsupported record-kind-4 clock fixture, an obsolete 118-program expectation and a real signed-zero
fit ambiguity. The clock fixture now uses the declared supported record, all forcing-record cases remain,
and the five direct clock folds are explicitly enumerated. Added negative-zero samples retain every prior
probe and select the caller's final addition. Corrected rows and their mutants pass. No tolerance or cap
was relaxed. The historical failed aggregate is not reported as a passing batch.

The preliminary `f7fed588` sweep had prerequisite tables with the branch C file. It is not clean-main
identity evidence and is superseded by the genuine main overlay/rebuild described above. Main checkouts,
other worktrees, the owner's client and installed apps were not edited or driven.

Remaining: one read-program candidate, forty historical helper-count types and 168 other bodies, total 209.
Next is `0x0b51`: its body starts a 6,000-tick piecewise colour cycle at `0x0175f2e6`, with branches at
`0x0175f320..0x0175f42c`. Implement an instruction-checked piecewise scalar reader/runtime form before
admission; reading its pre-program alone is insufficient. Then revisit helper counts and the largest other
groups. The 61-type three-level diagnostic is a lead, not a replacement denominator. `0x1710` and `0x10fd`
remain excluded after independent-state failures; the largest shield and armour candidates still refuse.
The owner prioritized the verified 41-body PR over a further unverified group under the stop deadline.

These are finite instruction and C-to-C comparisons within declared contexts. Host-free read bodies use
the declared zero random sequence; complete owned programs separately compare nonzero scripted requests
and random consumption. Selected-item, record, buff, pose, owner/bone, invalid-context and absolute
random/counter-phase limits remain. Native consumers can still refuse unsupported contexts. This is not
original pose/pixel equivalence, a whole-item effect completion claim, or native Windows evidence.
No service, packet, account, protection, character-power or original-client process work is involved.

All local reports, generated prototypes and render intermediates are disposable and removed at handoff,
along with this worktree and its build outputs. No new private input is needed by the next lane.
