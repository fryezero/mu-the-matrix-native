# RENDER-EFFECTS-017

The combat/effect leftovers after 016 and RENDER-ITEMS-002Q: the three particle kinds the armour owner-effect
programs request, fog on combat quads, and the software raster's linear GL_CLAMP edge.
[Instruction evidence and remaining inputs](../research/client-render-effects-017.md).

Branch `claude/render-effects-017`, worktree `~/Documents/MTM/worktrees/render-effects-017`, from main `18ab0134`
(#316). "Before" numbers were taken once at `18ab0134` from a detached base worktree. No live client session,
network work, memory write or installed-app change. The `tools/python`, `evidence` and `input` links are ignored and
never committed.

## Scope

- `reconstructed/particles/armour_kinds.inc` (new), `particles.c`, `particles.h`, `README.md`: 0x810a/7
  (create `0x015b143f`, move `0x0161a91d`), 0x810a/0xf (create `0x015b227a`, move `0x0161b3d8`), both drawn by the
  plain sprite `0x0159f7e9`, and Spark03 0x7f26/0x26 (create `0x015e1113`, move `0x01654b63`, plain sprite
  `0x015a531f`). Both bitmaps already had world particle slots; the owner route of 002Q now creates them.
- `native/core/mu_raster.c`: linear sampling of GL_CLAMP textures clamps both bilinear taps to the edge texels
  (GL_CLAMP_TO_EDGE, as its header and the combat GL part already said); before, the second tap wrapped to the
  opposite edge in the outer half texel. Nearest sampling and GL_REPEAT are unchanged.
- Fog: no code change. The wrappers' fog flag `0x0bdc597c` is only ever stored 0 (five stores, eleven gated reads, no
  pointer to it), so the wrappers never switch GL_FOG and native fog-off on combat quads already matches. The only
  in-game fog is world 0x1e's box fog `0x00d8cca8`, which no native renderer draws for any part of the scene (open).
- 0x70a's +0x38: not needed by any routine reconstructed here.
- `scripts/validate_render_effects17.py`, registry row, `native/tests/test_render_effects17.py` with host
  `effects17_host.c`. `test_native_renderchar.test_armour_owner_effect_program`: three frames now create the
  0x810a/7 request (effects 27 → 28, refused 1 → 0).
- Orchestrator request: `scripts/validate_render_effects11.py`'s mutant `mark_abs` anchor
  (`t = 0.0f > t ? -t : t;`) occurs three times in `bow_fx.inc` since #313; it now includes 0x70c's trailing comment
  (`/* 0x0184f8ff */`) and matches once. What it mutates is unchanged.
- No change to combat, joints, items, HUD, app, world objects or world slots/RNG (`outer_rand` untouched).

## Scene results

Native renders of the installed client (not original-client captures). Combat scenes as 016: Lorencia tile
182,128, a spider at 186,128 (`actor 3 186 128 2 label spider`), 640x400 software, world objects from
`MU_OBJECTS_PLAIN_DIR`, no audio/items/players, every fifth frame. Bows: class 2, `--combat-weapon bow --combat-bow
<item>`, `2:skill:24:spider;3:stop`, 30 frames, the 40 bows of CreateArrow's table. Staff: class 0, skills 1, 2, 3,
4, 5, 7, 8, 9, 10, 14. Ground: `2:skill:2044:spider` / `2045`, 40 frames, Bow01 0x12e6 and 0x12f7. The ground
counts reproduce 016's after numbers exactly (unsupported 0; arrows 14/14/11/11; effects 121/148/73/73).

Worn-armour scenes (new; 002Q measured synthetic parts and inventory renders only): `mu-render character
--game-root … --class 1 --part 2 <model> --item-type armor=<type>` (helms `--part 1 … helm=<type>`),
`--world-render --world-time 0 --frames 24 --frame-steps 2`, 320x240, one strip of the 24 frames. Models from
`mu_hud_item_model_path` (Item.bmd); 42 of the 43 types (0x1a78's helm has no installed model).

| Scenes | Before (`18ab0134`) | After |
|---|---|---|
| 42 worn armour scenes: owner effects / refused | 3,408 / **665** | 4,088 / **0** (the new particles draw rand, so later `rand() % 2` gates differ) |
| armour PNGs (42 frame-0 + 42 strips) | | 4 helms byte-identical (their programs make sprites only); 38 strips change by the particles; the clamp adds ±1 in 76 of 84 PNGs (8,787 pixels, item textures' clamped edges) |
| 40 bows, unsupported / arrows | 0 / 140 | 0 / 140; combat and particle counters identical; 240 of 280 frames change (clamp, below) |
| 10 staff, unsupported | 0 | 0; 60 of 70 frames change (clamp) |
| 4 ground scenes, unsupported | 0 | 0; counters identical; 32 of 36 frames change (clamp) |

Every refusal before was one of the three kinds; all are now created. Frame 0 of every combat scene is
byte-identical.

**Clamp frame changes, explained.** Only software-raster frames change, and only where a linear GL_CLAMP texture is
sampled in its outer half texel: sprites and quads drawn larger than their texture, and coordinates clamped outside
[0, 1]. The edge pixel there used to mix the opposite edge's texel; it now keeps the edge texel.

| Scenes | Frames changed | Pixels changed | Largest channel change |
|---|---:|---:|---:|
| bows | 240 / 280 | 48,201 | 126 (0x12f6/0x12f8/0x12f9: the cyan seams along Spark sprite edges vanish) |
| staff | 60 / 70 | 6,802 | 33 |
| ground | 32 / 36 | 137,184 | 46 (crater and flash decals' edges; most pixels change by ≤ 7) |
| armour (clamp part only) | 76 / 84 | 8,787 | 1 |

The common change in every bow scene from frame 20 (380 pixels, ≤ 7) is the borders of the Fire01 sprites along
skill 24's flame trail and of the camp fire's flames. The GL
paths (and so the DATA-ACQ-002 tours) do not use the raster's sampler.

Kept native renders (before | after | amplified difference), `~/Documents/MTM/mu-mac-tools/native/renders/render-effects-017/keep/`:
`armour-0x1bc4-frame23-before-after-diff.png` and `armour-0x1bf4-frame23-before-after-diff.png` (the new sparks),
`bow-0x12f9-frame25-clamp-before-after-diff.png` (seams gone), `ground-2044-bow01-frame25-clamp-before-after-diff.png`.

## Checks

No lane full gate; the steward runs it. Heavy work used `nice -n 10`, make at most `-j4`, two workers.

| Check | Result | Wall time |
|---|---|---:|
| Base build `make -C native` + `world` (detached worktree at `18ab0134`) | Passed | 13.6 s + 3.9 s |
| Before scenes at `18ab0134` (40 bows, 10 staff, 4 ground, 42 worn armour) | counts above | 87.8 s |
| Before default-draw tour sweep (DATA-ACQ-002, 32 tours) at `18ab0134` | 64 PNG + 64 object/light dumps | 60.7 s |
| Samples while iterating (Unicorn traces of the three cases) | all equal on the first run (40 per kind and family) | ~2 s each |
| Full `validate_render_effects17` with mutants (registry run at `067dadbe`; rerun once after replacing an equivalent mutant) | **618 comparisons, zero mismatches; 20/20 mutants caught, 0 equivalent, 0 stopped, all compiled; every anchor unique (checked before the run)** | 39.4 s |
| `validate_render_effects11` with mutants (the narrowed `mark_abs` anchor) | 176 comparisons, zero mismatches; 75/75 mutants caught (`mark_abs` 7/40) | 65.8 s |
| Affected validators, no mutants, cached, two workers, at `067dadbe` | 67/67 pass, 1,629,670 cases, 0 mismatches (below) | 46 min 12 s (+25.2 s `validate_path`) |
| After scenes (native and particle code as at `ed24c82e`, unchanged since) | armour 665 → 0 refused; combat counters identical; frame changes above | 90.2 s |
| After default-draw tour sweep at `067dadbe` | 32 tours: 64 PNG + 64 object/light dumps byte-identical to before | 54.8 s |
| `run_test_suites.py --affected origin/main`, `MU_RECOVERY_INTEGRATION=0`, two jobs | 9 suites, 1,465 tests, 1,246 passed, 219 skipped, 0 failures | 289.7 s |
| Installed-data modules (6b: the raster is in every software render): `test_native_viewer`, `_ui`, `_login`, `_objects`, `_particles`, `_combat`, `_joints`, `_worlds_l`, `_worlds_m`, `_renderchar`, `_gfx`, `_gfx2`, `_gfx3`, `_npc`, `_lang2` | 154 tests, 141 passed, 13 skipped, 0 failures (pinned viewer/UI render hashes unchanged) | 206.2 s |
| After merging main `3ecc205c` (`f785e530`): build `make -j4` + `world` | Passed | 19.9 s |
| After the merge: `validate_render_effects17`, `11`, `16`, `validate_particles`, `validate_worlds_slots2`, `validate_worlds_slots3`, no mutants | 6/6 pass: 618, 176, 424, 407, 33,000, 36,000 cases, 0 mismatches | 35.5 s |
| After the merge: `test_render_effects17`, `test_native_renderchar`, `test_native_worlds_slots3`, `reconstructed.particles.test_particles` (portable); `test_native_particles`, `test_native_combat` (installed) | 41 tests OK (4 skipped); 20 tests OK | 6.4 s; 15.4 s |
| `scripts/audit_repository.py` | 1,986 staged files, 0 rejected | 19.1 s |

The merge of main `3ecc205c` (#317..#320) brings RENDER-WORLDS-SLOTS3's `outer_rand` (`reconstructed/particles/visual.c`,
`particles.h`, `validate_particles.py`, `native/core/mu_objects_runtime.c`, `mu_particles.c`) and APP-POLISH-006's HUD;
neither touches the armour kinds or the raster, and the rows above that build both were rerun.

| Validator (no mutants, cached, at `067dadbe`) | Cases | Wall time |
|---|---:|---:|
| `validate_app_polish1` | 752 | 19.2 s |
| `validate_app_polish4` | 10,485 | 29.2 s |
| `validate_audio_callers` | 5,528 | 4.5 s |
| `validate_audio_charsel` | 5,968 | 3.1 s |
| `validate_audio_combat` | 19,548 | 17.1 s |
| `validate_audio_domains` | 2,544 | 19.9 s |
| `validate_audio_items` | 3,000 | 2.4 s |
| `validate_fidelity` | 991 | 66.9 s |
| `validate_icarus_c2` | 8,400 | 13.2 s |
| `validate_item_carry` | 114,388 | 491.6 s |
| `validate_item_chains` | 35,346 | 191.6 s |
| `validate_item_clusters` | 74,292 | 360.8 s |
| `validate_item_continuation` | 25,772 | 670.6 s |
| `validate_item_coverage` | 31,724 | 187.4 s |
| `validate_item_derived` | 36,252 | 164.5 s |
| `validate_item_effects` | 1,500 | 0.8 s |
| `validate_item_expansion` | 52,172 | 275.4 s |
| `validate_item_gear` | 25,256 | 143.6 s |
| `validate_item_hiddenmesh` | 116,281 | 376.9 s |
| `validate_item_next` | 14,992 | 166.3 s |
| `validate_item_ownerfx` | 14,964 | 109.6 s |
| `validate_item_product` | 2,874 | 39.5 s |
| `validate_item_quality` | 28,080 | 135.2 s |
| `validate_item_ranked` | 17,736 | 641.8 s |
| `validate_item_scalars` | 26,154 | 135.4 s |
| `validate_item_types` | 135,176 | 40.4 s |
| `validate_item_wings_next` | 33,622 | 197.3 s |
| `validate_meshdraw` | 14,619 | 62.6 s |
| `validate_model_edge` | 954 | 116.9 s |
| `validate_model_light` | 1,433 | 4.7 s |
| `validate_movement` | 6,614 | 47.3 s |
| `validate_particles` | 407 | 0.8 s |
| `validate_path` | 4,719 | 25.2 s |
| `validate_render_effects` | 660 | 0.8 s |
| `validate_render_effects10` | 154 | 0.3 s |
| `validate_render_effects12` | 64 | 0.2 s |
| `validate_render_effects13` | 180 | 0.4 s |
| `validate_render_effects14` | 660 | 1.0 s |
| `validate_render_effects15` | 509 | 0.6 s |
| `validate_render_effects16` | 424 | 3.2 s |
| `validate_render_effects3` | 720 | 0.7 s |
| `validate_render_effects4` | 1,920 | 4.6 s |
| `validate_render_effects5` | 1,190 | 3.1 s |
| `validate_render_effects6` | 1,000 | 0.9 s |
| `validate_render_effects7` | 596 | 1.2 s |
| `validate_render_effects9` | 304 | 0.7 s |
| `validate_render_worlds_a` | 9,000 | 8.4 s |
| `validate_renderchar` | 1,706 | 40.8 s |
| `validate_session_party` | 200 | 0.8 s |
| `validate_terrain` | 583,500 | 311.7 s |
| `validate_terrain_remaining` | 2,147 | 3.5 s |
| `validate_viewport_monsters` | 1,963 | 7.0 s |
| `validate_world_particle_consumers` | 900 | 0.6 s |
| `validate_worlds_after` | 13,424 | 10.7 s |
| `validate_worlds_after2` | 32,216 | 19.6 s |
| `validate_worlds_after3` | 10,212 | 5.9 s |
| `validate_worlds_after4` | 9,181 | 14.2 s |
| `validate_worlds_after5` | 6,000 | 7.5 s |
| `validate_worlds_after6` | 7,300 | 49.5 s |
| `validate_worlds_e` | 4,840 | 12.2 s |
| `validate_worlds_f` | 1,818 | 0.4 s |
| `validate_worlds_g3` | 4,000 | 3.1 s |
| `validate_worlds_k` | 6,000 | 2.9 s |
| `validate_worlds_l` | 1,260 | 0.8 s |
| `validate_worlds_m` | 1,080 | 0.9 s |
| `validate_worlds_slots` | 18,999 | 11.3 s |
| `validate_worlds_slots2` | 33,000 | 26.1 s |

Selection: `--list-affected origin/main` picked 69 rows: every row that builds `libmunative.a`, a native binary or
`libclient_particles` (the raster and the particle kinds are in all of them), so none was dropped.
`validate_render_effects11` and `17` ran with mutants; `validate_path` needs `MU_PATH_DIRECTIONS="$MU_SECTION3"` (its
pin's documented source).

## Steward

Steward validators (ran at `067dadbe`; the six that build the merge's changes reran at `f785e530`; all without mutants except `validate_render_effects17` and `validate_render_effects11`, which ran with them): validate_render_effects17, validate_app_polish1, validate_app_polish4, validate_audio_callers, validate_audio_charsel, validate_audio_combat, validate_audio_domains, validate_audio_items, validate_fidelity, validate_icarus_c2, validate_item_carry, validate_item_chains, validate_item_clusters, validate_item_continuation, validate_item_coverage, validate_item_derived, validate_item_effects, validate_item_expansion, validate_item_gear, validate_item_hiddenmesh, validate_item_next, validate_item_ownerfx, validate_item_product, validate_item_quality, validate_item_ranked, validate_item_scalars, validate_item_types, validate_item_wings_next, validate_meshdraw, validate_model_edge, validate_model_light, validate_movement, validate_particles, validate_path, validate_render_effects, validate_render_effects10, validate_render_effects11, validate_render_effects12, validate_render_effects13, validate_render_effects14, validate_render_effects15, validate_render_effects16, validate_render_effects3, validate_render_effects4, validate_render_effects5, validate_render_effects6, validate_render_effects7, validate_render_effects9, validate_render_worlds_a, validate_renderchar, validate_session_party, validate_terrain, validate_terrain_remaining, validate_viewport_monsters, validate_world_particle_consumers, validate_worlds_after, validate_worlds_after2, validate_worlds_after3, validate_worlds_after4, validate_worlds_after5, validate_worlds_after6, validate_worlds_e, validate_worlds_f, validate_worlds_g3, validate_worlds_k, validate_worlds_l, validate_worlds_m, validate_worlds_slots, validate_worlds_slots2. `validate_path` needs `MU_PATH_DIRECTIONS="$MU_SECTION3"`. Mutants needed again: none.

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
export MU_VALIDATOR_CACHE="$HOME/Documents/MTM/mu-mac-tools/native/cache/validators"
```

## Remaining work and cleanup

See the finding's [still-open list](../research/client-render-effects-017.md#still-open): world 0x1e's box fog (a
whole-scene feature, both renderers), whether the original's driver shows GL_CLAMP's border colour (one edge-pixel
capture), Uruk's weather and the Muun owner fixture from 016, and the armour programs outside the bone domain.

After the final push: one ready-prs.txt line, then no further push. Scratch, the base worktree and build products of
this lane are removed; the kept PNGs are listed above. No private input needs to survive cleanup.
