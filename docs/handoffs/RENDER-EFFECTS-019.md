# RENDER-EFFECTS-019

Two effect-placement gaps found by recent lanes: the map-object update's records that do not follow their bone
(RENDER-EFFECTS-018 §1, "found, not changed") and Test Area 121's three refused particle kinds (RENDER-WORLDS-121
§4, §7). [Finding, addresses and limits](../research/client-render-effects-019.md).

- Claude Opus 5.5 lane. Branch `claude/render-effects-019`, worktree `~/Documents/MTM/worktrees/render-effects-019`,
  from origin/main `53cffd00` plus `origin/claude/render-effects-018` (bf4744a9, to reuse its verified
  `mu_object_effect_matrix`); fast-forwarded to `5c0f7e9e` (#328 merged; docs only after bf4744a9, including the
  fixed `docs/handoff.md`). Input links `tools/python`, `evidence` and `input` come from the main checkout and are
  never staged.
- No live client, network, memory write or installed-app change. Inputs: the pinned text/data captures, the local
  decoded `mapeffects.tsv` (RENDER-EFFECTS-008's export, read only), DATA-ACQ-002 and the October 22 tour (read only).

## What landed

1. **Map-object records, verified (unfollowed 19/19 placed as the client).** `reconstructed/objects/map_effects.{c,h}`:
   `mu_map_effects_in_sector` (the sector predicate `0x012a0d29` from the runtime's sector lists: false only for an
   object alone in its sector) and `mu_map_effect_matrix` (the OBJECT image's scale/position/angle, no own bones, the
   pose as the shared buffer `0x06fce398`, then 018's `mu_object_effect_matrix`). `native/core/mu_particles.c`'s
   `o_ein_update` uses both:
   - not following, bone ≥ 0: the bone's posed translation (`0x012a0030`), no longer the object position;
   - alone in its sector: the position is added again (unfollowed) or the position/scale product applied (following
     `0x0129fd4f`), as the client does;
   - a bone ≥ 0 without the pose, and a follower below −1, are refused and counted (`unposed`).
   Bone −1 records keep the same matrices (the same formula).
2. **Test Area 121's particle kinds, verified (3/3).** `reconstructed/particles/test_area_kinds.inc` (new; three hook
   lines in `particles.c`): 0x801e/7 (create `0x015f236c` picks WATERFALL4 0x801d or WATERFALL5 for `+0x10`; move
   `0x016684c6` + the 0x801e gates), 0x801c/9 (`0x015f4466`/`0x015f496e`/`0x015f5079`; move `0x0166b810`), 0x801b/5
   (`0x015f27cb..`/`0x015f30e0`; move `0x01668bc8`). Render needs no change (subtype-independent cases).
   `native/core/mu_particles.{c,h}`: bitmap 0x801d `Data/Effect/WATERFALL4.OZJ` (LoadBitmap `0x01822aa5`,
   LINEAR/CLAMP), `MU_WORLD_PT_BITMAPS` 75 → 76, placed before Fire06 so RENDER-EFFECTS-016's `fire06_slot` anchor
   stays unique.
3. **Who else asks (static):** of 3,642 CreateParticle sites, only the 121 slot and its copy in Raklion's custom slot
   `0x00e949f8` (worlds 57/58, the same 28 sites) request these kinds. Raklion's types 0x13..0x15 are not ported
   natively, so no other world was refused today.

## Checks (wall times)

| Check | Result | Wall time |
|---|---|---:|
| `nice -n 10 make -j4` | passed | 37 s (first), incremental after |
| `validate_render_effects19 --cases 20 --mutations` (registry row; once, on the code of `284cd293`; later commits do not touch `map_effects.c` or `test_area_kinds.inc`) | 260 cases (map_update 80, ta_pt_create/move/render 60 each), 0 mismatches; **25/25 compiled mutants caught**, none equivalent, all compiling, every anchor exactly once (lowest: `in_sector_next` 1, `fall_bright_gate` 3) | 14.4 s |
| `validate_render_effects19 --cases 200 --lang-dir <local lang>` (full count, no mutants) | **4,116 cases, 0 mismatches**: map_update 800, map_records 1,516 (all 758 decoded entries alone and in a list), ta_pt_create/move/render 600 each | 4.9 s |
| `validate_map_effects` (registry row, its build now links `muun_effects.c`) | 300 cases, 0 mismatches, 14/14 mutants | 30.2 s |
| Affected unit suites (`run_test_suites.py --affected origin/main`, integration off) at `284cd293` | 9 suites, 1,507 tests: 1,278 passed, 229 skipped, 0 failures, 0 errors | 371 s |
| Integration modules (6b): test_native_map_effects, test_native_particles, test_native_render_effects6, test_native_worlds_121, test_render_effects16, test_render_effects17, test_render_effects18 (MuunHost, InstalledMuun), test_render_effects19 (portable) at `6c6dc794` | 22 tests OK (the first run caught the 76-slot bitmap pin, the map-effects validator build and 016's mutant anchor; fixed in `6c6dc794`) | 153 s |
| Affected validator rows at `6c6dc794` after `make -j4`: `run_validators.py --private --no-mutants --cache --affected origin/main --jobs 2` (TEST-SPEED-005 symbol-level selection: 71 rows + the fallback `validate_movement`; 29 item/terrain/path rows pruned, they use no changed symbol; 8b: `validate_app_polish4` and `validate_worlds_fog` (mu_particles.h) are in the selection) | **72 pass**, 0 fail/error/skip; 423,419 cases | 474.8 s |
| `scripts/audit_repository.py` | 2,040 staged files, 0 rejected | 26.4 s |
| Before tours, main binary (`bf4744a9` = main + #328, docs-only to `5c0f7e9e`), default draw, `MU_LANG_DIR` = canonical lang + `mapeffects.tsv` | DATA-ACQ-002 32, October 22 14 | 63.8 s + 21.4 s |
| After tours at `6c6dc794` | **31/32 + 14/14 byte-identical** (PNG frames, OBJECT and light dumps); 136 changed | 53.6 s + 19.3 s |

## Fidelity

- **136 Burning Kethotum vs live** (masked mean |Δ|, the earlier world lanes' metric): **6.534 → 6.444**. The type-25
  record (lighting02-yellow03, bone 29, not following) moves from the object position (z 184) to its bone (z 440),
  the crystal's top, where the live window shows the glow.
- The other captures with unfollowed records stay byte-identical, and each has a cause (a temporary debug print,
  not committed):
  - Bone 0 is the model origin, so its posed translation is the object position: 135 (0 units), 56 and 144 (≤ 1 unit).
  - 140 and 143 have no unfollowed record in view at the arrival tile.
  - The eight followed records on objects alone in their sector (122, 133, 144) are not in view.
- **World 121** (no capture): demo layout of the 23 slot types (20 with a model) at tile 128,128, 25 frames:
  particles created **56 → 92**, refused **36 → 0**; the object runtime refused 0 before and after.
- PNGs (local, window-only): `~/Documents/MTM/mu-mac-tools/native/renders/render-effects-019/png/136-live-before-after.png`,
  `world121-demo-before-after.png`.

## Shared files (minimal hooks)

- `native/core/mu_particles.c`: `o_ein_update`'s matrix block, one include, one bitmap id and file.
  `native/core/mu_particles.h`: `MU_WORLD_PT_BITMAPS` 76.
- `reconstructed/particles/particles.c`: one include, the supported/create/move hooks.
- `reconstructed/objects/map_effects.{c,h}`: two functions.
- `scripts/validate_map_effects.py`: its temp build also compiles `muun_effects.c`.
- `native/tests/test_native_particles.py`: the Lorencia bitmap pin (one more loaded slot).
- `scripts/validators.toml`: one row.

Steward validators: validate_app_polish1,validate_app_polish4,validate_audio_callers,validate_audio_domains,validate_audio_items,validate_charsel_world,validate_icarus,validate_icarus_c2,validate_item_effects,validate_login_world,validate_map_effects,validate_meshdraw,validate_model_edge,validate_movement,validate_object_render,validate_particles,validate_render_effects,validate_render_effects10,validate_render_effects11,validate_render_effects12,validate_render_effects13,validate_render_effects14,validate_render_effects15,validate_render_effects16,validate_render_effects17,validate_render_effects18,validate_render_effects19,validate_render_effects3,validate_render_effects4,validate_render_effects5,validate_render_effects6,validate_render_effects7,validate_render_effects9,validate_render_worlds_a,validate_world_fidelity,validate_world_light_name,validate_world_particle_consumers,validate_world_tile_folder,validate_worlds_121,validate_worlds_after,validate_worlds_after2,validate_worlds_after3,validate_worlds_after4,validate_worlds_after5,validate_worlds_after6,validate_worlds_b,validate_worlds_d,validate_worlds_e,validate_worlds_fog,validate_worlds_g,validate_worlds_g2,validate_worlds_g3,validate_worlds_h,validate_worlds_i,validate_worlds_j,validate_worlds_k,validate_worlds_l,validate_worlds_m,validate_worlds_n,validate_worlds_o,validate_worlds_p,validate_worlds_p2,validate_worlds_q,validate_worlds_q2,validate_worlds_r,validate_worlds_r2,validate_worlds_s,validate_worlds_s2,validate_worlds_s3,validate_worlds_slots,validate_worlds_slots2,validate_worlds_slots3 (ran at `6c6dc794`, no mutants; `validate_render_effects19` mutants: yes, new, done once (25/25); `validate_map_effects` ran its registry mutants 14/14 after its build fix).

Env:
- `MU_RECOVERY_INTEGRATION=1`;
- `MU_GAME_ROOT=<free-runtime prefix>/drive_c/MuTheMatrix`;
- `MU_SECTION3=~/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin`;
- `MU_EVIDENCE_DIR=<main checkout>/evidence`;
- `MU_OBJECTS_PLAIN_DIR=<mu-mac-tools>/native/scratch/objects/live/plain`;
- `MU_SNAPSHOT_DIR=<mu-mac-tools>/native/scratch`;
- `MU_PATH_DIRECTIONS=$MU_EVIDENCE_DIR/x86-guest-sec3-25/main-01ced000.bin`;
- `MU_VALIDATOR_CACHE=<mu-mac-tools>/native/cache/validators`;
- optional `MU_LANG_DIR` with RENDER-EFFECTS-008's `mapeffects.tsv` for the private `map_records` family (`--lang-dir`) and the tours; the registry row needs none.

## What's left

- Raklion's custom slot `0x00e949f8` types 0x13..0x15 (the same 28 CreateParticle sites as 121; Raklion holds
  2/3/8 such objects): port them through the 121 slot code; the particle kinds are now served.
- World 145 (Aquila): three unfollowed records and the slot's `0x0129fd4f(6)` without the alone-in-sector placement;
  no capture.
- A record on a bone beyond the posed model, and a follower below −1, stay refused (the client reads a stale pose or
  an uninitialised matrix).

Local files kept: the two PNGs above. Everything else (renders, scratch, the before binary, build dirs) is deleted.
