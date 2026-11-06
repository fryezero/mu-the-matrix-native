# RENDER-EFFECTS-015

The ground skills' rain 0x70a with its rings and ring models, RenderEffects' terrain decals of 0x70a, 0x70c and 0x45e,
and the effect-sound sites. [Instruction evidence and remaining inputs](../research/client-render-effects-015.md).

Branch `claude/render-effects-015`, worktree `~/Documents/MTM/worktrees/render-effects-015`. The work was traced on
`origin/claude/render-effects-014` while #306 was in steward batch 45; after it merged, main `eb2a8e76` was merged
in `9e734234` (`validators.toml`: both rows kept) and the "before" numbers were taken there once, from a detached
base worktree. No live client session, network work, memory write or installed-app change. The `tools/python`,
`evidence` and `input` links are ignored and never committed.

## Scope

- `reconstructed/combat/bow_fx.inc`: CreateEffect and MoveEffect 0x70a (subtypes 0, 1), 0x700/0x701/0x702
  (0, 1) and 0x707/0; the aim `0x012af5cb`; `mu_sfx_effect_render_ops` (RenderEffects' wrappers and
  RenderTerrainAlphaBitmap calls of 0x70a, 0x70c and 0x45e/3..7); `mu_sfx_sound_site` (six PlayBuffer sites).
  `skill_fx.h`: `MU_SFX_CALL_CASTER`, `MU_SFX_CALL_CREATE_ARROW`, the render-op type, the sound site in `arg8`.
  `skill_fx.c`: `call_sound` passes the site.
- `native/core/mu_combat.{c,h}`: the caster answer (the hero's key, not dead), the rain's CreateArrow for the hero's
  bow owned by the rain's effect OBJECT, the landing flag on the rain record's own +0x64, the ring models
  `min_elf_skill_ring01..08` (`MU_COMBAT_MODEL_ELF_RING1..8`), eleven decal bitmaps loaded GL_CLAMP
  (`MU_COMBAT_BITMAPS` 25 → 36, `mu_combat_bitmap.wrap`), `mu_combat_decal_quads` (one quad per terrain tile,
  drawn in the software path), the sound route's site fallback, summary fields `decals`, `decal_quads`,
  `decal_quads_dropped`, one log line each for missing decal bitmaps and ring models.
- `native/world/parts/combat.c` (GL only): decal quads before the frame's quads; decal textures clamp to edge.
- `scripts/validate_render_effects15.py`, registry row, `native/tests/test_render_effects15.py` with host
  `effects15_host.c`. `effects14_host.c`: 0x70a is now created, not refused. `test_native_combat.py`: installed
  bitmaps 36, models 29.
- No change to reconstructed/joints, reconstructed/particles, the world particle table, item, HUD, app or world
  object code. RENDER-ITEMS-002P: if an item body effect lays a terrain decal, `mu_sfx_effect_render_ops` and
  `mu_combat_decal_quads` are the route.

## Scene results

Installed client, Lorencia tile 182,128, a spider placed at 186,128 (scratch placement), 640x400 software, no
audio/items/players. Bows: class 2, `2:skill:24:spider;3:stop`, 30 frames, every fifth drawn, all 40 bow items of
CreateArrow's arrow table (014's 33-bow list was not kept; these include them). Staff: class 0, skills 1, 2, 3, 4,
5, 7, 8, 9, 10, 14. Ground skills: `2:skill:2044:spider` / `2045`, 40 frames, Bow01 (0x12e6) and 0x12f7.

| Scenes | Before (`eb2a8e76`) | After |
|---|---|---|
| 40 bows, unsupported / arrows | 0 / 140 | 0 / 140; all frames byte-identical |
| 10 staff, unsupported | 0 | 0; all frames byte-identical |
| bows 0x12f7, 0x1303: sound cues | 0 | 12 each (Flare/b's 0x42 at `0x01579fa1`; frames identical) |

| Ground scene | Unsupported | Arrows | Effects | Particles | Sounds | Decal calls (tiles) | Unsupported kinds after |
|---|---|---|---|---|---|---|---|
| 2044, Bow01 | 1 → 53 | 3 → 14 | 3 → 121 | 42 → 140 | 0 → 2 | 0 → 252 (8,788) | Fire06 0x7f40/1, /2, /3: 12, 20, 21 |
| 2044, 0x12f7 | 20 → 46 | 3 → 14 | 30 → 148 | 0 → 0 | 0 → 48 | 0 → 270 (8,926) | Fire06: 18, 18, 10 |
| 2045, Bow01 | 1 → 27 | 0 → 11 | 0 → 73 | 0 → 88 | 0 → 2 | 0 → 150 (5,446) | Fire06: 11, 12, 4 |
| 2045, 0x12f7 | 1 → 13 | 0 → 11 | 0 → 73 | 0 → 0 | 0 → 47 | 0 → 98 (3,546) | Fire06: 2, 4, 7 |

Before, the only unsupported request of the Bow01 scenes was 0x70a itself (0x12f7's own skill-0x7fc arrows already
landed 0x70c before, hence its Fire06 requests). After, 0x70a rains 11 arrows; their landings make 0x70c with its
rings 0x703..0x706 and stones, 0x70a's own rings 0x700..0x702/0x707 rise and sink, and the decals lie on the
terrain. The unsupported count rises because the scenes now contain 0x70c's stones: every remaining request is the
stones' Fire06 particle (not reconstructed). Kept native renders (640x400, not original-client captures) in
`~/Documents/MTM/mu-mac-tools/native/renders/render-effects-015/keep/`: `before-2044-bow01-frame15.png`,
`after-2044-bow01-frame15.png` (the rain, landing craters, the rings), `after-2045-bow01-frame25.png` (landing
flashes and rings), `after-2044-0x12f7-frame20.png`.

## Checks

No lane full gate; the steward runs it. Heavy work used `nice -n 10`, make at most `-j4`, two validator workers.

| Check | Result | Wall time |
|---|---|---:|
| Base build `make world` in a detached worktree at `eb2a8e76` | Passed | 10.62 s |
| Before scenes at `eb2a8e76` (40 bows, 10 staff, 4 ground) | 0 bow/staff unsupported, 140 arrows; ground counts above | 80.89 s |
| Before default-draw tour sweep (DATA-ACQ-002, 32 tours) at `eb2a8e76` | 128 PNG + 64 object/light dumps | 60.71 s |
| Samples while iterating (`--cases 5..30`) | First full run: 3 of 2,700 creates differed (a −0 x/y kept by the rings' lift; the client adds the whole vector); fixed, signed-zero cases added | ~1 s each |
| Full `validate_render_effects15` with mutants, at `ecc51919` | **7,509 comparisons, zero mismatches; 34/34 mutants caught, 0 equivalent, 0 stopped (4,062 mutant cases)**; anchors checked unique before the run | 54.56 s |
| Registry size (`--cases 20`) | 509 comparisons, zero mismatches | 0.6 s |
| Focused unit modules (26 modules, below) at `8d4c6bd7` | 244 tests, 213 passed, 31 skipped, 0 failures | 77.43 s |
| `test_native_combat.InstalledTests` (installed data) | 1 test, passed (bitmaps 36, models 29) | 1.72 s |
| Affected validators, no mutants, cached, two workers, at `8d4c6bd7` | 32/32 pass, 662,238 cases, 0 mismatches (below) | 423.62 s |
| After scenes at `8d4c6bd7` | bows/staff byte-identical to before, 0 unsupported; ground counts above (identical to a first after run) | 101.04 s |
| After default-draw tour sweep at `8d4c6bd7` | 32 tours: 128 PNG + 64 dumps byte-identical to before | 69.57 s |
| Build `make -j4` (top level) at `8d4c6bd7` | Passed | 0.45 s (up to date) |
| `scripts/audit_repository.py` | 1,935 staged files, 0 rejected | 18.48 s |
| Main `0122f192` merged (`709f1eae`; #307 APP-POLISH-004, #308 RENDER-WORLDS-SLOTS) | the 13 rows whose build inputs it changed (`native`, `reconstructed/objects`): 13/13 pass, 648,957 cases, 0 mismatches; focused modules again: 244 tests, 0 failures (84.87 s); installed combat test passed (1.48 s) | 324.88 s |

The first full mutant attempt is not counted as a mutant run: its base comparison failed (the signed zero above), so
no mutant ran; after the fix the single run above is the one reported.

Focused modules (`MU_RECOVERY_INTEGRATION=0`, installed-data env set): `native.tests.test_render_effects15`, `14`,
`13`, `12`, `11`, `10`, `9`, `test_render_effects`, `test_native_combat`, `test_native_joints`,
`test_native_particles`, `test_native_render_effects6`, `test_native_worlds_l`, `test_native_worlds_m`,
`test_native_worlds_o`, `test_native_terrain`, `test_native_helpers`, `test_native_pets`, `test_world_parts`,
`test_session_combat`, `test_audio_cues`; `reconstructed.joints.test_joints`, `reconstructed.particles.test_particles`,
`reconstructed.combat.test_skill_fx`, `reconstructed.combat.test_combat`; `tests.test_validators_manifest`. The 6b
grep covered `MU_COMBAT_BITMAPS`/`bitmaps_loaded`, `MU_COMBAT_MODELS`/`models_loaded`, `mu_combat_bitmap`,
`render_decals` and the new skill_fx symbols: users are `test_native_combat` (updated), `test_render_effects`
(fixture root, still 3 models), the hosts and `parts/combat.c`. The combat log (48 lines) holds 41 in the fixture
fight (39 before): missing decal bitmaps and ring models each log one summary line. No world-particle table, joint
or particle code changed.

| Validator (no mutants, cached) | Cases | Wall time |
|---|---:|---:|
| `validate_app_polish1` | 752 | 17.8 s |
| `validate_audio_callers` | 5,528 | 4.4 s |
| `validate_audio_charsel` | 5,968 | 4.8 s |
| `validate_audio_combat` | 19,548 | 17.8 s |
| `validate_audio_domains` | 2,544 | 21.6 s |
| `validate_audio_items` | 3,000 | 4.7 s |
| `validate_combat` | 496 | 1.6 s |
| `validate_meshdraw` | 14,619 | 71.8 s |
| `validate_model_edge` | 954 | 169.5 s |
| `validate_model_light` | 1,433 | 5.8 s |
| `validate_render_effects` | 660 | 0.7 s |
| `validate_render_effects10` | 154 | 0.3 s |
| `validate_render_effects11` | 176 | 0.2 s |
| `validate_render_effects12` | 64 | 0.2 s |
| `validate_render_effects13` | 180 | 0.4 s |
| `validate_render_effects14` | 660 | 1.1 s |
| `validate_render_effects15` | 509 | 0.6 s |
| `validate_render_effects3` | 720 | 0.7 s |
| `validate_render_effects4` | 1,920 | 4.4 s |
| `validate_render_effects5` | 1,190 | 3.6 s |
| `validate_render_effects6` | 1,000 | 0.9 s |
| `validate_render_effects7` | 596 | 1.1 s |
| `validate_render_effects9` | 304 | 0.7 s |
| `validate_session_party` | 200 | 1.4 s |
| `validate_skill_fx` | 660 | 1.2 s |
| `validate_terrain` | 583,500 | 344.7 s |
| `validate_viewport_monsters` | 1,963 | 7.3 s |
| `validate_world_particle_consumers` | 900 | 0.6 s |
| `validate_worlds_after6` | 7,300 | 57.4 s |
| `validate_worlds_d` | 2,400 | 5.9 s |
| `validate_worlds_l` | 1,260 | 1.8 s |
| `validate_worlds_m` | 1,080 | 1.1 s |

## Steward

Steward validators (all without mutants): `validate_combat`, `validate_skill_fx`, `validate_render_effects`, `validate_render_effects3`, `validate_render_effects4`, `validate_render_effects5`, `validate_render_effects6`, `validate_render_effects7`, `validate_render_effects9`, `validate_render_effects10`, `validate_render_effects11`, `validate_render_effects12`, `validate_render_effects13`, `validate_render_effects14`, `validate_render_effects15`, `validate_worlds_d`, `validate_world_particle_consumers`, `validate_worlds_l`, `validate_worlds_m`, `validate_worlds_after6`, `validate_app_polish1`, `validate_meshdraw`, `validate_model_edge`, `validate_model_light`, `validate_terrain`, `validate_viewport_monsters`, `validate_audio_callers`, `validate_audio_combat`, `validate_audio_domains`, `validate_audio_items`, `validate_audio_charsel`, `validate_session_party`.

Tested commits: the 13 rows that build `native` or `reconstructed/objects` ran at `709f1eae` (after main `0122f192`):
`validate_audio_callers`, `validate_audio_charsel`, `validate_audio_combat`, `validate_audio_domains`, `validate_audio_items`, `validate_meshdraw`, `validate_model_edge`, `validate_model_light`, `validate_terrain`, `validate_viewport_monsters`, `validate_session_party`, `validate_worlds_after6`, `validate_worlds_d`. The other 19 ran at `8d4c6bd7`; the merge changed none of their build inputs
(`reconstructed/combat`, `particles`, `joints`, `renderchar`, `model-codec` are unchanged since; only
`reconstructed/combat/README.md`, a doc): `validate_combat`, `validate_skill_fx`, `validate_render_effects`, `validate_render_effects3`, `validate_render_effects4`, `validate_render_effects5`, `validate_render_effects6`, `validate_render_effects7`, `validate_render_effects9`, `validate_render_effects10`, `validate_render_effects11`, `validate_render_effects12`, `validate_render_effects13`, `validate_render_effects14`, `validate_render_effects15`, `validate_world_particle_consumers`, `validate_worlds_l`, `validate_worlds_m`, `validate_app_polish1`.

Selection: `--list-affected origin/main` picked 76 rows. Kept: (A) the 21 rows that compile and compare
reconstructed/combat (`bow_fx.inc`, `skill_fx.c/.h`) or load it through their scripts; (B) the 11 rows whose native
targets compile `native/core/mu_combat.c` and `skill_fx.c` (`libmunative.a`, `mu-terrain`, `mu-render`,
`meshdraw-info-batch`, `mu-session`). Not kept: 44 rows selected only because their scripts quote "native" and
"world" next to `native/world/parts/combat.c`; their build directories hold none of the changed files, and the
`parts/combat.c` change is inside `#ifndef MU_WORLD_NO_GL` (GL world binaries only), which none of them builds.
`validate_render_effects15` is the only row with mutants, run once above (34/34). No world-particle table changed.

Environment, private inputs read-only:

```sh
export MU_RECOVERY_INTEGRATION=1
export MU_GAME_ROOT="$HOME/Library/Application Support/MuTheMatrix/prefix/drive_c/MuTheMatrix"
export MU_SECTION3="$HOME/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin"
export MU_EVIDENCE_DIR="$HOME/Documents/MTM/mu-the-matrix-native/evidence"
export MU_OBJECTS_PLAIN_DIR="$HOME/Documents/MTM/mu-mac-tools/native/scratch/objects/live/plain"
export MU_SNAPSHOT_DIR="$HOME/Documents/MTM/mu-mac-tools/native/scratch"
export MU_LIGHT_OBJECTS="$MU_OBJECTS_PLAIN_DIR/EncTerrain95.plain"
export MU_LIGHT_SNAPSHOT="$MU_SNAPSHOT_DIR/light/live/dumps/login-a.light"
```

## Remaining work and cleanup

See the finding's [still-open list](../research/client-render-effects-015.md#still-open): Fire06 0x7f40/1..3
(0x70c's stone particle), the crater decal's alpha test, the other combat bitmaps' clamp, Uruk's weather capture and
the Muun owner fixture.

After the final push: one ready-prs.txt line, then no further push. Scratch, the base worktree and build products of
this lane are removed; the four PNGs above stay. No private input needs to survive cleanup.
