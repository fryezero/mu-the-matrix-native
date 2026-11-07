# RENDER-WORLDS-FOG

World 0x1e's box fog `0x00d8cca8`, the last in-game fog no native renderer drew (RENDER-EFFECTS-017's open item),
and Test Area 121's two slots (left, below).

- Claude Opus 5.5 lane. Worktree `~/Documents/MTM/worktrees/render-worlds-fog`, branch `claude/render-worlds-fog`,
  from origin/main `3ecc205c`.
- Input links `tools/python`, `evidence` and `input` point at the main checkout and are never committed.
- Finding: [client-worlds-fog.md](../research/client-worlds-fog.md).

## Final state (PR-ready)

**Original (verified).** Not geometry: RenderMainScene `0x0185916b` tests the world (0x1e, `Data/World31`) and the
hero OBJECT's Position once before the scene (`0x018596b4..0x01859797`) and once after it (`0x01859bfa..0x01859cb3`).
Inside x 16100..19000, y 18900..21700 (ends included, NaN outside, z not tested) it calls StartFog `0x00d8cca8`
(glEnable(GL_FOG), black colour, GL_LINEAR as the float 9729, start 2000, end 2700) before the perspective setup, and
EndFog `0x00d8cd12` (glDisable) after the combat effects, before the haze `0x00def268` and the 2D interface. Outside
the box in world 0x1e the first test calls glDisable(GL_FOG); other worlds make no fog call. Every 3D part between
(terrain, objects, characters, items, helpers, environment, particles, effects) is fogged with its own blend/depth
state.

**Native now.**
- `reconstructed/environment/env_fog.{c,h}`: `mu_env_scene_fog_begin` / `mu_env_scene_fog_end` (the two tests and
  StartFog's parameters). Linked into `libmunative.a` (native/Makefile).
- `native/world/world_rt.c`: the GL draw issues StartFog's calls or the glDisable before the first part and EndFog
  before the first part ordered at or after the haze (`fog_end_here`, boundary `MU_PART_haze`); the software draw sets
  the raster's fog the same way.
- `native/viewer/gl_backend.c`: the mesh backend (immediate and batched) no longer forces GL_FOG to the mesh state's
  fog bit (always 0) at every draw; the client's wrappers never touch GL_FOG (flag `0x0bdc597c` only stored 0).
- `native/core/mu_raster.{c,h}`: a minimal GL_LINEAR fog stage, off by default (`fog`, `fog_start`, `fog_end`,
  `fog_color`): per fragment, `c = |z_eye|` (perspective-correct), RGB only, after texturing, before alpha test and
  blending. With `fog` 0 the arithmetic of every other fragment is unchanged.

### Checks (final code)

Validators at `2190f6d1` (the head's compiled inputs are the same; later commits are docs only).

| Check | Result | Wall |
|---|---|---|
| `validate_worlds_fog` (mutants) | 4 families: begin 2,000 (309 StartFog, 1,077 glDisable, 614 no call), end 2,000 (279 EndFog), placement 40, sites 4 = 4,044 cases, 0 mismatches/stops; 23/23 mutants detected (fewest 2: "Fog ends after the names"), none stopped, every anchor matched once | 54.5 s |
| `run_validators.py --private --no-mutants --cache --affected origin/main --jobs 2` | 36 rows selected: 35 pass, 0 fail; `validate_path` skipped for its input `MU_PATH_DIRECTIONS`, rerun with it: pass | 553 s + 25.8 s |
| `run_test_suites.py --affected origin/main` (`MU_RECOVERY_INTEGRATION=0`, 2 jobs) | 8 suites, 1,456 tests, 1,235 passed, 221 skipped, 0 failures | 328.6 s (425 s total) |
| `test_env_fog` + `test_world_parts`, `MU_RECOVERY_INTEGRATION=1` | 20 tests OK (the private comparison at 300 cases included) | 18.8 s |
| `audit_repository.py` | 0 rejected | 19 s |
| `make -j4` | pass | 40 s |

Validator selection: `run_validators.py --list-affected origin/main` selects 36 rows (`mu_raster.c/h`, `world_rt.c`,
`gl_backend.c`, the native Makefile, `reconstructed/environment/`); all were run without mutants, as selected.
Mutants only for the new row `validate_worlds_fog`. Unit selection `run_test_suites.py --affected origin/main`; brief
6b: the changed symbols (`mu_raster` fields, `mu_env_scene_fog_*`, gl_backend's prepare) have no other consumer in
tests beyond what that selection compiles; the private modules `test_env_fog` and `test_world_parts` ran with
`MU_RECOVERY_INTEGRATION=1`. No slot count changed.

**Fidelity** (default draw; "before" = main `3ecc205c` built once in this worktree):
- World 0x1e, tile 176,190 (inside the box) with three demo players: GL before/after mean |Δ| 17.6 per channel, the
  far floor black from 2000 units, the characters dimmed, the name plates unfogged; software 17.6; GL vs software
  after 0.009 (before 0.028). Tile 150,200 (outside): GL and software byte-identical before/after. No capture is in
  world 0x1e, so there is no live reference.
- DATA-ACQ-002: 32/32 captures byte-identical (PNG frames, OBJECT and light dumps); October 22 tour 14/14 identical.
  Wall times before / after: DATA-ACQ-002 49 / 65 s, October 22 21 / 23 s.
- Screenshots (window-only, kept locally, 0.2–0.5 MB): `~/Documents/MTM/mu-mac-tools/native/renders/render-worlds-fog/`
  `world30-box-before-gl.png`, `world30-box-after-gl.png`, `world30-box-after-soft.png`.

## What's left

1. **Test Area 121's two slots** (custom `0x00d58bd8`, after `0x00d5a6cc`; slots stay 142/144). Corrected outline in
   the finding §5: `0x012affa4` is SetAction (already reconstructed three times), so 0x10/0x11 need only the rand-driven
   action choice; the after slot is body/mesh calls only (0x4c with a sine-pulsed object light) and fits the existing
   slot events. The custom slot still needs a per-vertex light slot event (`MU_MODEL_LIGHTS`, plumbing through the
   object runtime and the mesh draw; no slot writes it today), the 0x10/0x11 choice, and posed bones with 28
   CreateParticle calls for 0x13..0x15. 121 has no capture and no warp.
2. **Devias 0x67's action choice** (the same SetAction around a rand; `reconstructed/particles/visual.c`).
3. A live capture inside world 0x1e's box would give the fogged frame a reference (and settle the original driver's
   eye distance, `|z_eye|` assumed).
4. RENDER-EFFECTS-017's finding lists the box fog as still open; #322 was not on main when this lane branched.

Env for the validators:
- `MU_RECOVERY_INTEGRATION=1`;
- `MU_GAME_ROOT=<free-runtime prefix>/drive_c/MuTheMatrix`;
- `MU_SECTION3=~/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin`;
- `MU_EVIDENCE_DIR=<main checkout>/evidence`;
- `MU_OBJECTS_PLAIN_DIR=<mu-mac-tools>/native/scratch/objects/live/plain`;
- `MU_SNAPSHOT_DIR=<mu-mac-tools>/native/scratch`; `MU_LANG_DIR=<mu-mac-tools>/native/scratch/render-worlds-after5/lang`.

Local files: only the three PNGs above (no input a later lane needs); scratch, tour renders and the "before" build
deleted.
