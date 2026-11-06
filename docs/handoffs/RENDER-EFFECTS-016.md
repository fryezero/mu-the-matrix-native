# RENDER-EFFECTS-016

The ground skills' leftovers after 015: 0x70c's stone particle Fire06 0x7f40/1..3, the alpha test of 0x70c's crater
decal, and the filter and wrap of every combat bitmap as its LoadBitmap call loads it. [Instruction evidence and
remaining inputs](../research/client-render-effects-016.md).

Branch `claude/render-effects-016`, worktree `~/Documents/MTM/worktrees/render-effects-016`. The work was traced and coded on `origin/claude/render-effects-015` while #309 was in steward batch 49 (first commits on that base); after #309 merged (`97e0a92a`, tree identical to 015's head `3ca5631a`) and #310 RENDER-ITEMS-002P followed, main `ad2968fc` was merged in `9b5876f2` (`validators.toml`: both sides kept). A first "before" at `3ca5631a` was superseded: #310 changes `reconstructed/renderchar` (in `libmunative`), so the scene and tour "before" numbers below were taken once at `ad2968fc` from a detached base worktree (its 54 scenes matched the `3ca5631a` run byte for byte). No live client
session, network work, memory write or installed-app change. The `tools/python`, `evidence` and `input` links are
ignored and never committed.

## Scope

- `reconstructed/particles/particles.{c,h}`: `MU_PT_BITMAP_FIRE06` 0x7f40, subtypes 1..3, through Fire01's create
  (`0x015ba585`), move (`0x016282c9`) and render (`0x01597855`) cases.
- `native/core/mu_particles.{c,h}`: the world particle table's Fire06 slot (`Data/Effect/Fire06.OZJ`, LINEAR, CLAMP;
  LoadBitmap `0x018229e5`); `MU_WORLD_PT_BITMAPS` 74 → 75 (before the two rain textures).
- `reconstructed/combat/bow_fx.inc`, `skill_fx.h`: `mu_sfx_render_state` and `mu_sfx_gl_state`, the GL state the
  wrappers EnableAlphaBlend `0x0184aa2b`, EnableAlphaTest `0x0184a990` and DisableAlphaBlend `0x0184a7f3` leave.
- `native/core/mu_combat.{c,h}`: every combat bitmap row carries its LoadBitmap filter and wrap
  (`mu_combat_bitmap.filter`, `.wrap`; Cratered NEAREST; Thunder01, Flare02, force_Pillar, !SwordEff and
  Swordeff_mono3 REPEAT, all others CLAMP); the decal sink follows `mu_sfx_render_state`, each decal quad carries its
  blend, alpha test and depth mask (`mu_combat_quad.alpha_test`, `.depth_mask`); the software path draws them with
  the raster's GREATER 0.25 test, depth writes and the bitmap's filter.
- `native/world/parts/combat.c` (GL only): each combat texture's filter and wrap from its row; per quad
  GL_ALPHA_TEST and glDepthMask.
- `scripts/validate_render_effects16.py`, registry row, `native/tests/test_render_effects16.py` with host
  `effects16_host.c`. `test_native_particles.py`: 75 slots. READMEs of `reconstructed/combat` and
  `reconstructed/particles`.
- No change to joints, the effects' create/move code, items, HUD, app, world objects or world slots/RNG.

## Scene results

Installed client, Lorencia tile 182,128, a spider placed at 186,128 (scratch placement `actor 3 186 128 2`),
640x400 software, world objects from `MU_OBJECTS_PLAIN_DIR`, no audio/items/players. Bows: class 2,
`2:skill:24:spider;3:stop`, 30 frames, every fifth drawn (7 PNGs), the 40 bows of CreateArrow's arrow table. Staff:
class 0, skills 1, 2, 3, 4, 5, 7, 8, 9, 10, 14. Ground skills: `2:skill:2044:spider` / `2045`, 40 frames (9 PNGs),
Bow01 0x12e6 and 0x12f7. These reproduce 015's after counts exactly.

| Scenes | Before (`ad2968fc`) | After (`9b5876f2`) |
|---|---|---|
| 40 bows, unsupported / arrows | 0 / 140 | 0 / 140; 274 of 280 frames byte-identical |
| 10 staff, unsupported | 0 | 0; all 70 frames byte-identical |
| bows 0x12f7 and 0x1303 | | frames 20, 25, 29 change (0x12f7: 1,837 / 550 / 3,477 pixels), the clamp below |

| Ground scene | Unsupported | Particles created | Arrows / effects / sounds / decal calls (tiles) | Frames changed |
|---|---|---|---|---|
| 2044, Bow01 0x12e6 | 53 → 0 | 140 → 193 | 14 / 121 / 2 / 252 (8,788), unchanged | 7 of 9 (from frame 10) |
| 2044, 0x12f7 | 46 → 0 | 0 → 46 | 14 / 148 / 48 / 270 (8,926), unchanged | 8 of 9 (from frame 5) |
| 2045, Bow01 0x12e6 | 27 → 0 | 88 → 115 | 11 / 73 / 2 / 150 (5,446), unchanged | 6 of 9 (from frame 15) |
| 2045, 0x12f7 | 13 → 0 | 0 → 13 | 11 / 73 / 47 / 98 (3,546), unchanged | 7 of 9 (from frame 10) |

Every request that was unsupported before was Fire06 0x7f40/1..3 (12/20/21, 18/18/10, 11/12/4, 2/4/7 for subtypes
1/2/3); each is now created as a particle and none is left. The ground frames change from the first crater on: the
Fire06 sprites, the crater's alpha test (its soft dark fringe below alpha 0.25 is dropped), its depth writes and
NEAREST sampling, and in the 0x12f7 scenes also the clamped Flare trails.

**The clamp frame changes, explained.** Bows 0x12f7 and 0x1303 shoot arrow 0x459, whose Flare/b joints (014) sample
`Effect\Flare.jpg`. LoadBitmap `0x01822545` loads it GL_CLAMP; the native loaded it GL_REPEAT. The trails' texture
coordinates leave [0, 1], so from frame 20 (the trails are long enough) their ends no longer wrap to the opposite
edge. With only Flare's row set back to REPEAT, the three changed frames of 0x12f7 are byte-identical to before (checked
with a one-off build). Every other bitmap whose wrap changed is drawn inside [0, 1] in these scenes, so their frames
did not change. Unchanged frames are byte-identical.

Kept native renders (640x400, not original-client captures) in
`~/Documents/MTM/mu-mac-tools/native/renders/render-effects-016/keep/`: `before-2044-bow01-frame15.png`,
`after-2044-bow01-frame15.png`, `before-after-crater-2044-bow01-frame20.png` (zoomed: the crater's alpha test),
`before-after-bow-0x12f7-frame29.png` (zoomed: the clamped Flare trail ends), `after-2045-0x12f7-frame25.png`.

## Checks

No lane full gate; the steward runs it. Heavy work used `nice -n 10`, make at most `-j4`, two validator workers.

| Check | Result | Wall time |
|---|---|---:|
| Base build `make -C native world` (detached worktree at `ad2968fc`) | Passed | 3.85 s |
| Before scenes at `ad2968fc` (40 bows, 10 staff, 4 ground) | counts above | 78.37 s |
| Before default-draw tour sweep (DATA-ACQ-002, 32 tours) at `ad2968fc` | 64 PNG + 64 object/light dumps | 43.69 s |
| Samples while iterating (`--cases 5`) | 139 comparisons, zero mismatches on the first run | 2.6 s |
| Full `validate_render_effects16` with mutants, registry run at `82177c53` | **424 comparisons, zero mismatches; 23/23 mutants caught, 0 equivalent, 0 stopped, all compiled; every anchor unique (checked before the run)** | 36.0 s |
| Affected validators, no mutants, cached, two workers, at `9b5876f2` | 44/44 pass, 957,808 cases, 0 mismatches (below) | ~425 s |
| After scenes at `9b5876f2` | ground 0 unsupported; bows/staff as above | 109.24 s |
| After default-draw tour sweep at `9b5876f2` | 32 tours: 64 PNG + 64 object/light dumps byte-identical to before | 56.49 s |
| Focused unit modules (29, below), `MU_RECOVERY_INTEGRATION=0` | 259 tests, 226 passed, 33 skipped, 0 failures | 82.99 s |
| Installed-data tests: `test_native_particles.InstalledLorenciaFires` (75 slots), `test_native_combat.InstalledTests` (bitmaps 36) | 2 tests, passed | 2.61 s |
| Installed-data `test_native_worlds_l`, `test_native_worlds_m` (6b: the particle table grew) | 4 tests, passed | 20.69 s |
| Build `make -j4` (top level) at `9b5876f2` | Passed | 0.44 s (up to date) |
| `scripts/audit_repository.py` | 1,956 staged files, 0 rejected | 18.01 s |

The mutant run's targets (`reconstructed/particles`, `reconstructed/combat/bow_fx.inc`, `native/core/mu_combat.c`,
`mu_particles.c`) did not change after `82177c53`; the merge of `ad2968fc` changed `reconstructed/renderchar`, which
`libmunative` (the row's host) links, so the row was rerun without mutants at `9b5876f2` (424 cases, 2.6 s).

Focused modules: `native.tests.test_render_effects16`, `15`, `14`, `13`, `12`, `11`, `10`, `9`,
`test_render_effects`, `test_native_combat`, `test_native_joints`, `test_native_particles`,
`test_native_render_effects6`, `test_native_worlds_l`, `test_native_worlds_m`, `test_native_worlds_o`,
`test_native_terrain`, `test_native_helpers`, `test_native_pets`, `test_world_parts`, `test_session_combat`,
`test_audio_cues`, `test_app_polish4`; `reconstructed.joints.test_joints`, `reconstructed.particles.test_particles`,
`reconstructed.combat.test_skill_fx`, `reconstructed.combat.test_combat`; `tests.test_validators_manifest`,
`tests.test_repository_policy`. The 6b grep covered `mu_combat_quad`, `mu_combat_bitmap`, `MU_COMBAT_BITMAPS`,
`MU_WORLD_PT_BITMAPS`, `bitmap_present`, `mu_sfx_render_state`, `MU_PT_BITMAP_FIRE06` and 0x7f40: users are
`test_native_particles` (updated: 75 slots), the effects15/16 hosts and the world parts (built).
`run_test_suites.py --affected origin/main` selected 140 of 169 items, mostly through textual matches ("quotes
'native' and 'world'" for `native/world/parts/combat.c`), so the focused list above was run instead.

| Validator (no mutants, cached, at `9b5876f2`) | Cases | Wall time |
|---|---:|---:|
| `validate_app_polish1` | 752 | 17.7 s |
| `validate_app_polish4` | 10,485 | 36.0 s |
| `validate_audio_callers` | 5,528 | 5.6 s |
| `validate_audio_charsel` | 5,968 | 3.1 s |
| `validate_audio_combat` | 19,548 | 22.9 s |
| `validate_audio_domains` | 2,544 | 20.7 s |
| `validate_audio_items` | 3,000 | 2.7 s |
| `validate_combat` | 496 | 0.7 s |
| `validate_icarus_c2` | 8,400 | 14.3 s |
| `validate_item_clusters` | 74,292 | 33.4 s |
| `validate_item_effects` | 1,500 | 1.2 s |
| `validate_item_types` | 135,176 | 31.9 s |
| `validate_item_wings_next` | 33,622 | 36.6 s |
| `validate_meshdraw` | 14,619 | 54.9 s |
| `validate_model_edge` | 954 | 113.1 s |
| `validate_model_light` | 1,433 | 6.1 s |
| `validate_particles` | 407 | 0.9 s |
| `validate_render_effects` | 660 | 0.8 s |
| `validate_render_effects3` | 720 | 0.9 s |
| `validate_render_effects4` | 1,920 | 5.7 s |
| `validate_render_effects5` | 1,190 | 3.5 s |
| `validate_render_effects6` | 1,000 | 1.2 s |
| `validate_render_effects7` | 596 | 1.3 s |
| `validate_render_effects9` | 304 | 0.7 s |
| `validate_render_effects10` | 154 | 0.4 s |
| `validate_render_effects11` | 176 | 0.2 s |
| `validate_render_effects12` | 64 | 0.3 s |
| `validate_render_effects13` | 180 | 0.5 s |
| `validate_render_effects14` | 660 | 0.9 s |
| `validate_render_effects15` | 509 | 0.6 s |
| `validate_render_effects16` | 424 | 2.6 s |
| `validate_render_worlds_a` | 9,000 | 8.7 s |
| `validate_session_party` | 200 | 0.7 s |
| `validate_skill_fx` | 660 | 0.8 s |
| `validate_terrain` | 583,500 | 323.7 s |
| `validate_viewport_monsters` | 1,963 | 6.8 s |
| `validate_world_particle_consumers` | 900 | 0.6 s |
| `validate_worlds_after` | 13,424 | 9.6 s |
| `validate_worlds_after6` | 7,300 | 51.1 s |
| `validate_worlds_d` | 2,400 | 3.0 s |
| `validate_worlds_e` | 4,840 | 15.3 s |
| `validate_worlds_g3` | 4,000 | 3.4 s |
| `validate_worlds_l` | 1,260 | 0.9 s |
| `validate_worlds_m` | 1,080 | 0.8 s |

## Steward

Steward validators (all without mutants; ran at `9b5876f2`): `validate_render_effects16`, `validate_combat`, `validate_skill_fx`, `validate_particles`, `validate_render_effects`, `validate_render_effects3`, `validate_render_effects4`, `validate_render_effects5`, `validate_render_effects6`, `validate_render_effects7`, `validate_render_effects9`, `validate_render_effects10`, `validate_render_effects11`, `validate_render_effects12`, `validate_render_effects13`, `validate_render_effects14`, `validate_render_effects15`, `validate_worlds_d`, `validate_world_particle_consumers`, `validate_worlds_l`, `validate_worlds_m`, `validate_worlds_after`, `validate_worlds_after6`, `validate_worlds_e`, `validate_worlds_g3`, `validate_render_worlds_a`, `validate_icarus_c2`, `validate_item_clusters`, `validate_item_effects`, `validate_item_types`, `validate_item_wings_next`, `validate_app_polish1`, `validate_app_polish4`, `validate_meshdraw`, `validate_model_edge`, `validate_model_light`, `validate_terrain`, `validate_viewport_monsters`, `validate_audio_callers`, `validate_audio_combat`, `validate_audio_domains`, `validate_audio_items`, `validate_audio_charsel`, `validate_session_party`.

Selection: `--list-affected` picked 99 rows, most through textual matches. Kept: (A) rows that compile or load `libcombat` (`bow_fx.inc`, `skill_fx.h`: 015's 21 rows); (B) rows whose run loads or builds `libclient_particles` (`particles.c/.h`: `validate_particles`, the item rows that load it themselves (`item_clusters`, `item_effects`, `item_types`, `item_wings_next`), `icarus_c2`, `worlds_e`, `worlds_g3`, `worlds_after`, `render_worlds_a`; the combat/world rows are in A); (C) rows whose native targets compile `mu_combat.c` or `mu_particles.c` or include their headers (`libmunative.a`, `mu-terrain`, `mu-render`, `meshdraw-info-batch`, `mu-session`; `app_polish4` includes both headers). Not kept: rows selected only because their scripts quote "native" and "world" next to `native/world/parts/combat.c` (GL world binaries only, which none of them builds), or that import `validate_particles` for its structures without loading the library (the other item rows, `worlds_after2..5`, `worlds_slots`, `worlds_k`). `validate_render_effects16` is the only row with mutants, run once above (23/23).

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

See the finding's [still-open list](../research/client-render-effects-016.md#still-open): fog on combat quads, the
software raster's linear GL_CLAMP edge, 0x70a's +0x38, Uruk's weather capture and the Muun owner fixture (both still
need the inputs 013 named; neither is small).

After the final push: one ready-prs.txt line, then no further push. Scratch, the base worktree and build products of
this lane are removed; the kept PNGs are listed above. No private input needs to survive cleanup.
