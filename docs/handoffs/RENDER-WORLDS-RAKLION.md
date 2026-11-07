# RENDER-WORLDS-RAKLION

Raklion's (worlds 57/58) custom slot `0x00e949f8` and after slot `0x00e96536`, ported whole by running Test Area
121's slot code with a per-class row. Before this lane, RENDER-WORLDS-A had ported only the after flags and the
0x53/0x5c first meshes, plus a separate copy of the after slot.

- Claude Opus 5.5 lane. Worktree `~/Documents/MTM/worktrees/render-worlds-raklion`, branch
  `claude/render-worlds-raklion`.
  - Branched from `origin/claude/render-effects-019` `d07e1b61` (#332: the particle kinds 0x801e/7, 0x801c/9,
    0x801b/5 and WATERFALL4).
  - Merged origin/main `ae5e6f36` (#331, #332 and #333 merged) as `2a5c3f8a`, before any checks ran. Every check
    below ran on the merged code.
- Input links `tools/python`, `evidence` and `input` point at the main checkout and are never committed.
- Finding: [client-worlds-raklion.md](../research/client-worlds-raklion.md), with the instruction diff, the addresses,
  the live comparison and the limits.

## The 121 vs Raklion diff (static, then verified)

| Address | Raklion `0x00e949f8` | 121 `0x00d58bd8` |
|---|---|---|
| `0x00e94a04` | world test `0x00ea233c` (57..58); else answers 0 | none |
| `0x00e96083` | 0x1ab..0x1ad: handler +0x22 == 0 answers 1 undrawn (unreachable: types > 300) | draws |
| `0x00e96242` | 0x52: handler +0x22 == 0 sets frame `+0xd0` and prior frame `+0xd4` to 0 before RenderBody | RenderBody |
| `0x00e96527` | base `0x00e9ef04` (types > 300 only) | base `0x00d5c79c` (answers 0) |

- Aligned, the other 1,972 instructions are equal, with the same constant and data addresses. The stack layout
  differs only by offsets.
- After slots `0x00e96536` / `0x00d5a6cc`: 198 instructions each, equal.
- Handler +0x22: the constructor `0x00e9eebd` sets it to 1. The event setter `0x00ea165f` calls `0x00ea174a`
  (+0x22 = state <= 6) after every state write except 11's.
- Bitmap 0x800a `Effect\Chrome08.jpg`: Raklion's loader `0x0183f4e2`, the same as 121's `0x018417cd`.

## What Raklion draws now

- Types 6..12: every mesh's per-vertex light 0.5, object light (1, 1, 1), RenderBody. Live confirms it: in the
  October 22 capture, exactly the type 6/7/12 objects that are or were in view hold (1, 1, 1).
- 0x10/0x11: the rand-driven action choice through the shared SetAction.
- 0x13..0x15: posed-bone particles at the 28 sites (WATERFALL5 0x801e/7 and its WATERFALL4 half, 0x801c/8,
  0x801c/9, 0x801b/5), the direct action writes and the `rand() % 40` returns. 0x14 draws its four meshes with
  0x800a.
- 0x39, 0x44/0x45/0x47 (the sine pulse), 0x52 (with the frame gate), 0x53/0x5c meshes, and the after flags of
  0x2e, 0x35, 0x4c, 0x53, 0x59, 0x5c.
- After pass (runs in 57/58): 0x2e/0x35 bodies, 0x4c's light pulse, 0x53/0x59/0x5c glow meshes, now from the shared
  routine.

## Shared lines (narrow seams)

- `reconstructed/objects/world_test_area_visual.c`:
  - `ta_class` rows: `TEST_AREA {0, -1, 0}` and `RAKLION {57, 58, 1}`;
  - `ta_custom(s, row, world)` and `ta_0x52`;
  - `ta_after` answers whether it drew;
  - `mu_slots_raklion_custom` / `mu_slots_raklion_after`;
  - the 0x800a bitmap and type 0x14's list for 57/58.
  
  121's behaviour is unchanged (its row has no test and no gate).
- `world_slots2_visual.c`: class 57 for worlds 57/58 in the SLOTS2 chain (custom, after, bitmaps).
  `world_visual_slots.h`: two declarations.
- Removed (now the class slot):
  - `mu_raklion_defer`, `mu_raklion_before` and `mu_raklion_after` (`world_raklion_visual.c`, `world_after.c`,
    `world_visual.h`);
  - Raklion's cases in `mu_world_defer` and `mu_world_after_render`.
  
  `mu_world_after_enabled` keeps 0x39/0x3a (the pose's light-skip mesh, unchanged). `mu_raklion_visual` (slot 0x34)
  is unchanged.
- `native/core/mu_objects_runtime.c`:
  - `slot_model` passes `raklion_state[0x22]` as `handler_state` in 57/58;
  - `class_custom_call` sends 57/58 through `test_area_custom_call`;
  - `mu_objects_start` sets +0x22 = 1;
  - removed: the Raklion `deferred` exception, the 0x53/0x5c option tweak and `mu_objects_first_meshes`' Raklion
    branch.
- `native/core/mu_objects_raklion.c`: `mu_objects_raklion_set_event` sets +0x22 = (event <= 6), except for 11.
- Validators:
  - new `scripts/validate_worlds_raklion.py` and its `scripts/validators.toml` row;
  - `validate_worlds_121.py`'s slot family takes a `Spec` (121's by default; two mutant anchors follow the code);
  - `validate_render_worlds_a.py`'s Raklion cases (`after_draw`, `first_draw`, `flags`) call `mu_class_after` /
    `mu_class_custom(0x39, …)`, and its two Raklion mutants moved to `world_test_area_visual.c`.
- Tests:
  - new `reconstructed/objects/test_worlds_raklion.py` (portable, plus the private comparison);
  - `native/tests/worlds_121_host.c` gains a Raklion section;
  - 6b: `test_worlds_after2.test_classes` lists 57, 58.
- Docs: the census row in `client-worlds-slots.md`, the Raklion entries in `world-handler-coverage.json`, a
  pointer each in `client-world-fidelity.md` and `client-render-effects-019.md`.

## Checks

Under the 2026-11-04 test budget: no lane gate. `nice -n 10`, `make -j4`, `--jobs 2`; load 1m 2–15 with other lanes
active. Code at `740283cf` (main `ae5e6f36` merged in `2a5c3f8a`); the later commits are docs only.

| Check | Result | Wall |
|---|---|---|
| `nice -n 10 make -j4` | pass (after the merge: 11 s) | 30 s |
| `validate_worlds_raklion --cases 200` (iterating) | 600 cases, 0 mismatches | < 1 s |
| Mutants once (`run_validators.py --private --cache --only validate_worlds_raklion,validate_worlds_121,validate_render_worlds_a --jobs 2`, at `740283cf`) | **validate_worlds_raklion** (new): 3 families × 1,000 = **3,000 cases, 0 mismatches/stops**; **15/15 mutants** caught (lowest 8, "0x13 bones 12..18"). **validate_worlds_121** (slot family now takes a Spec; two anchors follow the code): 4,000 cases, 0 mismatches; **31/31** (lowest 4). **validate_render_worlds_a** (Raklion cases on the class path): 9,000 cases, 0 mismatches; **13/13** (lowest 9). All mutants compile; every anchor matches exactly once (the two moved A anchors checked by hand: its runner asserts only ≥ 1) | 176 s (rows 88 / 176 / 64 s) |
| Affected rows, no mutants: `run_validators.py --private --no-mutants --cache --affected origin/main --jobs 2` after `make -j4` (TEST-SPEED-005 symbol selection: 59 rows, 30 of them symbol fallbacks; 8 pruned: audio_charsel, audio_combat, fidelity, item_textures, objects, path, session_party, viewport_monsters use no changed symbol), at `740283cf` | **59 pass**, 0 fail/error/skip; **1,007,750 cases** | 630 s (rows 1,038 s) |
| Unit modules (`MU_RECOVERY_INTEGRATION=1`): test_worlds_raklion (new), test_worlds_121, test_worlds_after2 (6b: class list), test_worlds_slots, test_worlds_slots2, test_worlds_j | 40 tests; the first run caught one wrong event index in the new test (fixed; test_worlds_raklion 5/5 again in 1 s), the other 35 OK | 352 s |
| `native/tests/test_native_worlds_121.py` (host with the Raklion section) | 1 test OK | 1 s |
| `run_test_suites.py --affected origin/main` (`MU_RECOVERY_INTEGRATION=0`, `MU_GATE_JOBS=2`) | 8 suites, 1,497 tests, 1,270 passed, 227 skipped, 0 failures | 329 s |
| `scripts/audit_repository.py` | 2,054 staged files, 0 rejected | 19 s |
| `world_handler_coverage.py` | 48 classes, 57 registrations, 288 addresses; markdown unchanged | < 1 s |
| Tours (default draw; `live_time` for Raklion too): before = main `ae5e6f36` binary, once | Raklion 3 + 3, October 22 13, DATA-ACQ-002 32 | 5 + 9 + 23 + 72 s |
| Tours after (at `740283cf`) | Raklion changed (below); **October 22 13/13 and DATA-ACQ-002 32/32 byte-identical** (PNG frames, OBJECT and light dumps, frame reports with the output path normalised) | 4 + 7 + 16 + 54 s |

Steward validators: validate_worlds_raklion (mutants: yes, new; done once at `740283cf`), validate_worlds_121 and
validate_render_worlds_a (mutants: done once at `740283cf`, their checks changed), and without mutants the 59 rows of
`--affected origin/main` (ran at `740283cf`): validate_charsel_world, validate_login_world, validate_meshdraw,
validate_model_edge, validate_model_light, validate_movement, validate_object_render, validate_terrain,
validate_world_fidelity, validate_terrain_remaining, validate_render_worlds_a, validate_icarus, validate_worlds_b,
validate_icarus_c2, validate_worlds_d, validate_worlds_e, validate_worlds_f, validate_worlds_g, validate_audio_callers,
validate_worlds_h, validate_worlds_i, validate_audio_domains, validate_worlds_j, validate_worlds_k, validate_audio_items,
validate_worlds_o, validate_worlds_n, validate_worlds_p, validate_worlds_r, validate_world_tile_folder,
validate_worlds_g2, validate_world_light_name, validate_worlds_p2, validate_worlds_r2, validate_worlds_q,
validate_worlds_q2, validate_worlds_after, validate_worlds_g3, validate_worlds_after2, validate_worlds_after3,
validate_worlds_after4, validate_worlds_after5, validate_worlds_after6, validate_app_polish1, validate_app_polish4,
validate_worlds_s, validate_worlds_s2, validate_worlds_s3, validate_worlds_slots, validate_worlds_slots2,
validate_worlds_slots3, validate_worlds_121, validate_worlds_raklion, validate_render_effects16, validate_worlds_fog,
validate_render_effects17, validate_item_callers, validate_render_effects18, validate_render_effects19.

Env:
- `MU_RECOVERY_INTEGRATION=1`;
- `MU_GAME_ROOT=<free-runtime prefix>/drive_c/MuTheMatrix`;
- `MU_SECTION3=~/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin`;
- `MU_EVIDENCE_DIR=<main checkout>/evidence`;
- `MU_OBJECTS_PLAIN_DIR=<mu-mac-tools>/native/scratch/objects/live/plain`;
- `MU_SNAPSHOT_DIR=<mu-mac-tools>/native/scratch`;
- `MU_LANG_DIR=<mu-mac-tools>/native/scratch/lang`, `MU_LANG3_SNAPSHOT=$MU_LANG_DIR/live/lang3.bin`;
- `MU_LIGHT_SNAPSHOT=$MU_SNAPSHOT_DIR/light/live/dumps/login-a.light`, `MU_LIGHT_OBJECTS=$MU_OBJECTS_PLAIN_DIR/EncTerrain95.plain`;
- `MU_PATH_DIRECTIONS=$MU_EVIDENCE_DIR/x86-guest-sec3-25/main-01ced000.bin`;
- `MU_VALIDATOR_CACHE=<mu-mac-tools>/native/cache/validators`.

## Fidelity (Raklion vs live, October 22 capture)

`fidelity_tour.py`, default draw and `live_time` (equal scores), `MU_LANG_DIR` = the canonical lang. Three views of
world 57: `57-raklion` (14-view tour), `57b-raklion-a/-b` (session 2). The live window PNGs of that session no longer
exist locally, so the live comparison is the per-field OBJECT scoreboard (1,521 objects matched per view) and the light
dumps.

| Field vs live | 57 before → after | 57b-a | 57b-b |
|---|---|---|---|
| Object light `+0xec` (live: types 6, 7, 12 at (1, 1, 1)) | 5 → **0** | 5 → **0** | 5 → **1** |
| Near-hero object light differences | 2 → 0 | 4 → 0 | 2 → 0 |
| Action `+0x2a` (one type 0x14 at action 1 in live) | 1 → 1 | 1 → 1 | 1 → 1 |
| Frame light near the hero, mean abs | 0.02574 (same) | 0.01049 (same) | 0.01517 (same) |
| Native object particles | 0 → 14 | 0 → 14 | 0 → 0 |

- Closer to live: the slot's object light now lands on the same objects as in the client.
- 57b-b's last light: a type-6 object (20314, 22009) lit while it was in view in 57b-a. Live keeps that light; the
  native tour starts fresh at b, where the object is out of view.
- The action: the visible 0x14 (19614, 21513) is at frame 19.2, action 1 in live, after a long run. The 25-frame
  tour reaches frame 3.84 (velocity 0.16); the frame >= 19 switch needs about 119 frames. The branch is compared in
  `actions_raklion`.
- Pixels: only the 0x14 statue's WATERFALL spray changes (window region x 915..1137, y 0..167; mean |Δ| ≈ 0.2..0.4
  per channel). The five lit type 6/7/12 objects are 500+ units below the hero (z −349..−403 against 159), not in
  sight (inference from the positions).
- PNGs (local, window-only, half size, before | after): `~/Documents/MTM/mu-mac-tools/native/renders/render-worlds-raklion/png/57-raklion-before-after.png`,
  `57b-raklion-a-before-after.png`. There is no live panel: the October 22 window shots are gone.

## Census

The slot census counted Raklion's custom `0x00e949f8` as "V A" in 142/144 and 144/144. RENDER-WORLDS-A had compared
only its flag and first-mesh branches, so types 6..12, 0x10, 0x11, 0x13..0x15, 0x39, 0x44/0x45/0x47 and 0x52 were
counted as covered while they fell to the generic RenderBody.
- The row now reads "V RAKLION" (whole), and the JSON scope and source point at the shared routine. The count
  stays 144/144.
- Karutan's custom `0x00e14596` ("V A") is in the same bounded state; its JSON scope says so.

## What's left

- No authoritative feed of Raklion's event state (RENDER-WORLDS-E), so +0x22 stays 1 in native play unless
  `mu_objects_raklion_set_event` is called.
- The 0x1ab..0x1ad gate and the base `0x00e9ef04` (types > 300) are unreachable and not ported.
- History-dependent live fields (a long animation, a light from an earlier view) cannot be reproduced by a 25-frame
  tour from a fresh start.
- The October 22 live window PNGs are gone, so there is no live image metric for Raklion. A future capture session
  could re-shoot 57 at tile 224,211.
- Karutan's custom slot is still bounded (above).
- Still open from 121: the particle visual's stale comment (`reconstructed/particles/visual.c` line 131).

Local files kept: `~/Documents/MTM/mu-mac-tools/native/renders/render-worlds-raklion/png/57-raklion-before-after.png`
and `57b-raklion-a-before-after.png` (window-only, half size, before | after). Everything else (tour renders, scratch,
the before binary and its worktree, build dirs) is deleted.
