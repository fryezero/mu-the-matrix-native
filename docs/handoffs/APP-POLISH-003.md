# APP-POLISH-003

Codex GPT-6-Astra, xhigh. PR-ready for the merge steward. Based on main `2531746f`, then merged
`5a91b98d` with RENDER-EFFECTS-012. No full gate, installation or live original-client run.

## Player-facing result

The level-1 Dark Knight world fixture arrives with HP 1100/1100, MP 200/200, SD 52/52 and AG 25/25.
The old combination of combat's 400 current HP and progression's 1100 display maximum is gone.
A Hound counterattack lowers session and HUD HP to 1077/1100. No damage, regeneration or combat rule changed.
The default HP input to the preview's existing combat fixture is now the same recorded 1100.

The session maxima are displayed directly. The progression display fallback is retired. A standalone world
without a session leaves its existing layer values alone. No formula is added. The recorded profile is
class 1, level 1, stats 28/20/25/10/0; other classes/levels remain unverified and receive no invented maxima.
The synthetic selection list and the level-1 world session are still separate, as before this lane.

Toxic states 0x37 and 0x136 select the original movie's green HP texture. MP, SD and AG retain their colours.
The session has no replicated buff list, so the existing `--gfx-open buffs=55` or `buffs=310` fixture supplies
the new display input. Portable tests cover clearing it, including a state-only update with unchanged HP.
No poison application, damage, timer or packet route is added.

## Evidence and causes

[client-app-polish3](../research/client-app-polish3.md) records the full provenance and comparison boundaries.
The retained October 22 FryeZEN2 CharacterMachine dump, `scratch/progress/live/dk1-192dac80.bin`, has SHA-256
`188ed9d02ee7c6e1a281c6e7959b2f477b987cafe1e7dbb1b2972ebe0e434402`. This lane reread it. CharacterAttribute
starts at machine +8; its `+0x68..+0x84` is 1100,200,1100,200,52,52,25,25. This is observed server-supplied
data, not the progression demo's extrapolation. The dev seed now carries those values once at fixture join.

The intact updater checks 0x37 at `0x00c71798/9f`, then 0x136 at `0x00c717ab/b5`, through membership query
`0x00c54ea8` on `0x01d1df54`. Either sets the cache byte at `0x00c717c7..d1`. `0x00c718f5` supplies
`isToxic` and `0x00c719d6` invokes `setHPMP`. The native layer previously hardcoded false and omitted that
flag from cache invalidation. The original movie selects `guege_hp_green-nopack` versus `guege_hp-nopack`.
The patched entry `0x00c71772 → 0x10b14930` remains opaque and untouched.

## Fidelity

Own `mu-world` build, Lorencia 203,131, original demo Hound placement, real local Ruffle, read-only canonical
Native Data lang/objects, and APP-REFRESH-004 converted movies. No audio, owner option-file write or installed
app launch. The window-only captures read this process's SDL framebuffer before swap. Both were inspected
at 1504×936 after downscaling from Retina 3008×1872:

- `native/renders/app-polish-003/normal.png`, SHA-256 prefix `ef4c2f9ae54a460f`: full red HP, 1100/1100.
- `native/renders/app-polish-003/toxic.png`, prefix `53db27de9ad206c5`: full green HP, 1100/1100, poison icon.

Paths are under the shared tools directory and are deleted after queueing, per the brief. These are appearance
checks at different animation times, not original-client pixel-parity claims.

Final headless run and toxic window run, both with `40:attack:hound`:

| Time | Session HP/MP/SD/AG | HUD HP/MP/SD/AG | HUD maxima |
|---|---|---|---|
| 1–2 s | 1100,200,52,25 | 1100,200,52,25 | 1100,200,52,25 |
| 3–7 s | 1077,200,52,25 | 1077,200,52,25 | 1100,200,52,25 |

Each records five hero attacks, one monster attack and one hero hit. Headless runs 200 frames; the toxic
window runs 193 frames over eight seconds. The normal final window runs 67 frames under concurrent load,
records two attacks and no hero hit, and remains 1100/1100 throughout. Its screenshot confirms arrival fill.
Pre-merge normal and toxic windows also recorded one hero hit each, 1100 → 1077.

No 32-tour sweep was needed: the source diff changes only the HUD and offline session/fixture setup.
The two-line edit in `world_rt_default_options` is the fixture's HP input; no world draw, movement, object,
item or effect path changed. The effects changes merged from main remain owned by RENDER-EFFECTS-012.

## Checks and budget

| Check | Result | Wall time |
|---|---|---|
| Initial root build / GL world and client build | pass | 28.28 / 8.51 s |
| Latest-main root build / GL world and client build | pass | 14.09 / 11.62 s |
| Expanded validate_app_polish2 | 1,024 vital/state cases + 4 viewports, 0 mismatches; 14/14 compiled mutants caught, none equivalent | 22.33 + 9.17 s |
| Existing validate_app_polish1, no mutants | 752 cases, 0 mismatches | 23.83 s |
| Existing validate_gfx3, no mutants | 6 skill + 18 window cases; loadlist 12 movies/5 slots, menu 6 groups/19 entries; all match | 5.32 s |
| App-polish1 dependent host module | 4 tests, 0 failures | 4.56 s |
| Shared-symbol consumer tests | 142 tests, 0 failures, 0 errors, 11 optional skips | 127.78 s |
| Post-merge app, combat, world2, polish2 and registry tests | 62 tests, 0 failures | 103.79 s |
| Final headless / normal window / toxic window | results above | 6.11 / 13.60 / 11.55 s |
| Initial headless / normal window / toxic window | 1100 → 1077, one hero hit each | 4.58 / 11.58 / 11.40 s |
| Final staged repository audit | 1,875 staged files, 0 rejected | 24.35 s |

Mutant execution was interrupted by a harness compile error at mutant 10: the new copied-layer substitution
also replaced the identifier `demo` with `1`. The first nine were already caught, and the full 1,028 cases
had passed. After restricting that substitution to the intended demo configuration, only mutants 10–14 ran.
No successful mutant was repeated. Development used 20-case samples. The initial screenshot harness emitted
no PNG because macOS stripped DYLD_INSERT_LIBRARIES at `/usr/bin/nice`; the final driver inherits nice 10
and loads the capture helper only in its own child. No production capture code was changed.

TEST BUDGET 6b searched native/tests, reconstructed and tests for the changed seed/header consumers,
`mu_session_seed`, `mu_dom_hero_seed`, `mu_gfx_hero`, `mu_world_rt_default_options`, `is_toxic` and `vitals`.
Ran modules: app_polish2, native_app, session_includes, session_core, audio_domains, audio_items,
session_party, session_combat, session_items, session_map_overlay, session_characters, session_skills,
native_gfx2, native_gfx3, native_lang, native_world2, native_combat and world_parts.
Also ran app_polish for its indirect GFx-layer host dependency.
Eleven unchanged original-validator test methods that hardcode mutants were deliberately excluded;
their host and portable tests ran. The affected existing compiled validators are validate_gfx3 and validate_app_polish1,
which calls gfx3.layer_log and compiles the same layer.
Other session validators compile unchanged wire/domain adapters, not the changed hero seed or GFx layer.
The seed-only header does not change their product-domain compilations. The expanded app_polish2 is the
third affected row. The main merge changed none of these comparisons' compiled sources; mutants were not repeated.

Steward validators: validate_app_polish1,validate_app_polish2,validate_gfx3

Steward mutants: none. Run all three without mutant flags. The steward helper currently hardcodes its own
worktree, so this lane ran the existing rows' exact arguments directly with `--mutations`/`--mutants` omitted.
Environment: `MU_RECOVERY_INTEGRATION=1`,
`MU_SECTION3=~/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin`,
`MU_GAME_ROOT=~/Library/Application Support/MuTheMatrix/prefix/drive_c/MuTheMatrix`.
Native Data: `~/Documents/MTM/mu-mac-tools/native/scratch/native-data/export`, read-only.
Builds used nice 10 and at most make -j4; validator/test workers were serial. No full gate.

## APP-REFRESH-005 and remaining scope

Rebuild/reinstall only in the refresh lane. Existing Native Data and converted movies remain usable.
Check the class-1 world session at arrival, Hound damage and a travel rebind. For colour, use the explicit
buff fixture; do not claim live poison replication. Remaining: session buff-list application/expiry,
other join profiles, selection/world/CharacterInfo ownership, and the opaque updater entry.
No network/login/dispatch, protection-module work, live memory write, power feature or owner-app reinstall.

After the ready-prs line there are no further pushes. Remove this lane's scratch, renders, build outputs,
worktree and local branch. The recorded live dump is an existing canonical input and remains untouched.
