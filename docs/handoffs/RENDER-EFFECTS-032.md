# RENDER-EFFECTS-032

## WIP late-main integration

Main advanced during final audit. ACTORS-005 #389 and INNER-004 #390 main
`4babc900` are integrated as `fe83b2b9`. The combined root build passes, 21.13 s.
A 93-row private validator delta since `5c0dec22` is selected and awaiting its
resource guard. Portable merge delta, focused incoming private modules and
after-only render/identity replay remain pending. The reconstructed skill
module and comparator are unchanged, with the same dylib SHA-256, so no new
skill mutants are needed. INNER-004 documents an expected Kanturu 37 extra
RGBA mesh delta. Do not claim final readiness from the earlier tables below.

The earlier 23-row refresh passes 23/23, 290.45 s; the first staged audit passes
2,276 files, zero rejected, 33.10 s. Those checks precede this late merge.
Baselines stay fixed. The existing foreground delta job/log must be checked
before starting any duplicate on resume.

Verification checkpoint. Final staged audit and PR delivery remain pending.

Branch `codex/render-effects-032` starts at main `b7dfd2ed`. Main `2b0b2716`,
AUDIO-004 #388, is integrated through `8187e8e3` / registry resolution `fb561cff`.
Caller source inputs are `8965554f`, unchanged through the delivery metadata.
No subagents or full lane gate. Work uses nice 10, make at most four jobs and
two validator/test workers. Resource pauses are observed.

## Skill audit and implemented boundary

The same 29 learned/ordinary rows as EFFECTS-030 move **11 P / 5 L / 13 M to
11 P / 7 L / 11 M**, for this lane alone. P/L/M measure bounded presentation,
not eligibility or authoritative state. Consumer-only work in EFFECTS-031 is
excluded from this delta. [Original caller inventory](../research/client-render-effects-032.md).

| Skill | Before -> after | Implemented result or remaining boundary |
|---|---|---|
| 0 ordinary attack | P -> P | Unchanged |
| 19 Falling Slash | P -> P | Unchanged |
| 20 Lunge | P -> P | Unchanged |
| 21 Uppercut | P -> P | Unchanged |
| 22 Cyclone | P -> P | Unchanged |
| 23 Slash | P -> P | Unchanged |
| 41 Twisting Slash | P -> P | Unchanged |
| 42 Anger Strike | P -> P | Unchanged |
| 43 Death Stab | L -> L | General equipment/link selection remains open |
| 44 Crescent Moon Slash | M -> L | Pose 0x98, step spark joints/particles and both sounds; 0x49e/0 end consumer refused |
| 18 Defense | M -> L | Pose 0xd7 and sound, authored shield context; held-input lifetime and shield equipment rendering unproved |
| 47 stale entry | M -> M | Always refused, no invented record or cast |
| 48 Swell Life | M -> M here | Consumer-only row skipped for EFFECTS-031 |
| 49 Fire Breath | M -> M | Mount pose 0xf9 and frame cutoff; primary 0x8001/0 refused |
| 344 Blood Storm | M -> M here | Consumer-only row skipped for EFFECTS-031 |
| 24 Triple Shot | P -> P | Existing two requests retained; wing/kind action context added |
| 26 Heal | P -> P | Unchanged |
| 27 Greater Defense | L -> L | Existing fixture aura; general links/presence remain open |
| 28 Greater Damage | L -> L | Existing fixture aura; general links/presence remain open |
| 30 Summon Goblin | M -> M | Caster pose/sound; 0x7f84/3 refused, actor construction/lifetime absent |
| 31 Summon Stone Golem | M -> M | Same explicit summon boundary |
| 32 Summon Assassin | M -> M | Same explicit summon boundary |
| 33 Summon Elite Yeti | M -> M | Same explicit summon boundary |
| 34 Summon Dark Knight | M -> M | Same explicit summon boundary |
| 35 Summon Bali | M -> M | Same explicit summon boundary |
| 36 Summon Soldier | M -> M | Same explicit summon boundary |
| 51 Ice Arrow | L -> L | Wing/kind pose context; optional target visual remains EFFECTS-031 work |
| 52 Penetration | L -> L | Wing/kind pose context; charge/child remain EFFECTS-031 work |
| 2044 Raining Arrow of Saturation | P -> P | Unchanged |

Individual synthetic aliases 416/52 and 424/51 remain L, outside those 29 rows.
Unlearned catalogue IDs and all other aliases retain 030's separate inventory;
no icon, masked class nibble or shared consumer admits a new alias.

`MU_SKILL32_CONTEXT=bow_kind,wing,shield,mount` supplies four decimal appearance
service answers. Default is configured bow kind, wing -1 and no shield/mount.
Examples are `1,0,0,0` and `0,-1,1,0`. Wing zero is present, as in the original
comparison against -1. This does not equip a body or grant eligibility. New
callers require an active learned entry within min(count,150); stale capacity
and skill 47 remain refused. Only authored class/weapon/tile context is used.

## Original proof

Final proof at `8965554f`: **4,433 checks, zero mismatches, 31/31 compiled
production-C mutants, zero original-machine stops, 71.71 s**.
Of these, 3,217 execute original instructions: 1,000 step, 1,000 end, 900 start,
117 pose and 200 interleaving cases. The remaining 1,216 are authored admission,
learned-count/cap and exact-selector controls. Registry sample is 1,723 checks.

Every effect/joint/particle argument is compared in order, including owner,
key, skill/default words, scale, sound site, frame/cutoff writes and RNG use.
The streaming family gives consumer services varying declared CRT draw counts
and compares the resulting requests and total RNG use. Native emits each pair
before the next pitch draw. The legacy particle constructor borrows/returns
combat CRT state, then restores the world pool's separate movement stream.
Whole-client RNG phase, pool allocation, terrain and GPU equivalence are not
claimed. No consumer source changes.

An initial 4,233-check/28-mutant proof, 31.32 s, did not model consumer RNG. Self-review
found the native integration gap. The final proof supersedes it, adding three
streaming mutants. The repeated mutant run follows a changed production path
and new comparator family. Other validators run without mutants. Exploratory
stops never count as evidence or caught mutants.

Combat dylib SHA-256:
`62936052baf3718000d820c5060f981e2d6def34b127932f6b55e5348e57fbb7`.
Original target/text/data pins and routine body hashes are described in the
research note and validator. Receive parsers, network and power code do not run.

## Native fixture proof

Twelve installed-data GL scenes, one cast at frame 2 and stop at frame 3,
Lorencia 182,127, target 184,127, 960x600, 60 frames saved every 12, draw every
logic frame. Names DemoKnight/DemoArcher and authored DemoTarget. No audio output,
other players or items. All after casts have zero sent / one unsent request,
zero hits/kills and unchanged target HP. Loaded models/bitmaps stay 29/39.

| Scene | Visual requests | Refused | Result |
|---|---:|---:|---|
| Each of 30,31,32,33,34,35,36 | 1 | 1 | Caster pose/sound only; no summon body |
| 18 with shield context | 0 | 0 | Defense pose/sound in a finite fixture schedule |
| 44 | 89 | 1 | Eleven four-joint/four-particle steps, refused final 0x49e/0, two sounds |
| 49 with mount context | 1 | 1 | Mount pose/cutoff and sound, primary fire missing |
| 51 with wing/kind | One arrow caller | 0 | Existing projectile |
| 52 with wing/kind | Charge plus arrow caller | 2 | Existing projectile, refused charge/child |

Early wing scenes use target 187,127, frames 0..11 saved at 0/3/6/9/11.
The initial before/after/repeat proof passes 72 long-scene and ten early PNG
pairs, 63.47 s and 9.39 s. A root-path preflight
fails before producing an image and is not counted. The **final after/repeat
refresh passes all 82 PNG pairs, 59.08 s**, without repeating
any baseline. Visual inspection confirms Crescent's spark scatter, Defense's
pose, floating bow actions and the frame-6 Penetration projectile. The new RNG
ordering changes the active Crescent scatter as intended. The long Penetration
sample misses its short flight; the early scene covers it. These are native
repeatability/component controls, not original GPU images.

## Default identity and binaries

Both versions are explicitly built with `make -C native -j4 world`, in this
isolated worktree before/after edits. Root make alone is not the world rebuild.
The baseline is main b7dfd2ed, captured once; no successful baseline is repeated.
The final script rebuilds/checks the binary hash immediately before its sweep
and verifies the hash again afterward.

- Before SHA-256: `e341fc2000d2e7f035f1e1814ca5384231389c8e7409ed20557643b0485108d7`.
- After SHA-256: `bb5470bf11a199bc3d6a241da9206d2548e39ed28ef874dfcb779b99fa45368c`.

Default draw, no draw_all/live_time, 640x400, 25 frames sampled at 0/24:

| Dataset | PNGs | OBJECT/light dumps | Normalized reports |
|---|---:|---:|---:|
| October 22, 14 views | 28/28 identical | 28/28 identical | 14/14 identical |
| DATA-ACQ-002, 32 views | 64/64 identical | 64/64 identical | 32/32 identical |

All **230 artifacts match**, normalizing only output-directory prefixes in JSON.
No default view changes: the new skill callers are inactive there. Incoming
AUDIO-004 also preserves these defaults. Before sweep 74.61 s; after command
69.74 s. Two old-path preflights produced no baseline image;
local manifest paths were rebased to the canonical MTM tools directory.

## Completed checks and test budget

Commands run from the repository root with canonical private-env. No full gate.
Every selected validator, including symbol fallbacks, is retained. No unchanged
consumer mutant run is requested. Wall times exclude load-guard pauses.

| Check | Result | Command wall s |
|---|---|---:|
| Integrated root build | pass | 24.79 |
| Post-RNG-correction root build | pass | 12.70 |
| Final explicit world build | pass, up to date | 0.21 |
| Final original proof | 4,433 checks, 31/31 mutants, no stops | 71.71 |
| Initial focused native | 6/6 pass | 7.77 |
| Reduced private native after correction | 15/15 pass, zero skips | 25.75 |
| Portable affected | 170 items; 1,803 tests, 1,490 pass / 313 expected skips; zero failures/errors | 500.74 |
| Initial private affected, pre-correction | 23/23 pass, no mutants, fb40a57e | 358.29 |
| Final private affected refresh | all selected rows pass | 290.45 |
| Final fixture refresh | 82/82 after/repeat pairs | 59.08 |
| Default after sweep | 230/230 artifacts identical | 69.74 |
| Staged repository audit | pending | pending |

**8d reduced:** the private native selection is 174 work items, above the
40-item cap. Private run covers the changed test_render_effects32 module,
neighbouring test_render_effects30 caller/arrow cases and installed combat.
All 15 tests pass with no skips. Portable private skips are not private proof.

**Owner packaging exclusion:** the affected unit runner is used with --affected
origin/main and MU_RECOVERY_INTEGRATION=0 / MU_GATE_JOBS=2. A task-local driver
filters only native/tests/test_native_app.py from its work-item list, because
that module packages Native Preview and this session's brief forbids packaging.
It changes no committed test or expectation. That exclusion is separate from
the 313 reported skips. No app bundle, install or installed-app journey occurs.

## Steward validators

Final results at `5c0dec228af414f129ce061f3a400cefdef07624`.
Canonical private-env supplies evidence, MU_SECTION3, MU_GAME_ROOT,
MU_NATIVE_DATA_DIR, MU_LANG_DIR and snapshots. Run --private --no-mutants --cache
--jobs 2. **No further mutants needed.** Counts below mix original comparisons
and each row's native controls; they are not one original-instruction total.

| Validator | Cases | Wall s | Status |
|---|---:|---:|---|
| `validate_actor_composites` | 1427 | 7.6 | pass |
| `validate_actor_recipes` | 1669 | 99.4 | pass |
| `validate_app_polish4` | 10485 | 45.5 | pass |
| `validate_audio_callers` | 5528 | 4.6 | pass |
| `validate_audio_combat` | 19548 | 39.8 | pass |
| `validate_audio_domains` | 2544 | 20.8 | pass |
| `validate_audio_items` | 3000 | 5.9 | pass |
| `validate_audio_objects` | 4000 | 2.6 | pass |
| `validate_audio_objects4` | 10093 | 5.4 | pass |
| `validate_charsel_items` | 8817 | 7.2 | pass |
| `validate_icarus_c2` | 8400 | 15.8 | pass |
| `validate_inventory_fx` | 8017 | 7.4 | pass |
| `validate_item_callers` | 6013 | 1.8 | pass |
| `validate_items_ui` | 8517 | 9.5 | pass |
| `validate_movement` | 6614 | 51.8 | pass |
| `validate_render_effects16` | 424 | 4.8 | pass |
| `validate_render_effects17` | 618 | 6.4 | pass |
| `validate_render_effects24` | 226 | 2.5 | pass |
| `validate_render_effects25` | 202 | 8.1 | pass |
| `validate_render_effects26` | 348 | 8.7 | pass |
| `validate_render_effects32` | 1723 | 0.8 | pass |
| `validate_worlds_after6` | 7300 | 53.4 | pass |
| `validate_worlds_fog` | 4044 | 4.4 | pass |

Steward validators: validate_actor_composites,validate_actor_recipes,validate_app_polish4,validate_audio_callers,validate_audio_combat,validate_audio_domains,validate_audio_items,validate_audio_objects,validate_audio_objects4,validate_charsel_items,validate_icarus_c2,validate_inventory_fx,validate_item_callers,validate_items_ui,validate_movement,validate_render_effects16,validate_render_effects17,validate_render_effects24,validate_render_effects25,validate_render_effects26,validate_render_effects32,validate_worlds_after6,validate_worlds_fog

## Limits and next lane

Summon actor construction/lifetime and ground subtype 3, Fire Breath's 0x8001/0
and Crescent's 0x49e/0 remain absent. Defense's held-input lifetime and shield
body are unproved. General Death Stab links, buff equipment/presence services,
full shared-client RNG/pool/time phase and original GPU comparisons remain open.
Swell Life, Blood Storm, charge/child and target ice belong to EFFECTS-031.
Authored appearance inputs never grant eligibility, power, mana, cooldown,
damage, server keys or target state. Skill 47/stale learned capacity stay refused.
No actor, item table, world, Muun, UI/audio or particle/joint/effect consumer file is edited.
No protection, live client, owner Wine app, README or installed-app work occurs.

## Delivery

Not PR-ready until the pending refresh/audit and publication finish.
All source inputs remain `8965554f`; later commits update documentation only.
The PR targets main. Finish every doc/push before the one ready-prs entry, then
push nothing more. Remove this lane's scratch, renders, ignored builds,
worktree and local branch; retain the remote PR branch. No new private input
needs retaining. Local paths before cleanup are the matching
`~/Documents/MTM/mu-mac-tools/native/scratch/render-effects-032/` and
`renders/render-effects-032/` directories.
