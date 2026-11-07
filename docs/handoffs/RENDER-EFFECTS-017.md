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

CHECKS_TABLE

## Steward

STEWARD_SECTION

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
