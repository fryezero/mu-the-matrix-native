# RENDER-WORLDS-121

The last two class slots (Test Area 121's custom `0x00d58bd8` and after `0x00d5a6cc`), plus Devias 0x67's action
choice, which shares SetAction `0x012affa4`. The slot census goes from 142/144 to **144/144**; the classes stay 48/48.

- Claude Opus 5.5 lane. Worktree `~/Documents/MTM/worktrees/render-worlds-121`, branch `claude/render-worlds-121`,
  from origin/main `ce0ebd71` (#324 RENDER-WORLDS-FOG included).
- Input links `tools/python`, `evidence` and `input` point at the main checkout and are never committed.
- Finding: [client-worlds-121.md](../research/client-worlds-121.md). Read it for the addresses, the per-type table
  and the limits.

## What is drawn now

- **Test Area 121, custom slot (verified).**
  - Types 6..12: the model's per-vertex light 0.5 for every normal of every mesh, then the object light (1, 1, 1)
    and RenderBody. The terrain light of 121 is black, so before this change these objects drew black.
  - 0x10/0x11: the rand-driven action choice (`rand() % 2`; `rand() % 100` with the 90 split and its parity), then
    RenderBody.
  - 0x13..0x15: posed bones, the bone-placed CreateParticle requests (28 call sites), the direct action writes and
    `rand() % 40` returns, then RenderBody (0x14 draws four meshes with `Effect\Chrome08.jpg` 0x800a instead).
  - The body/mesh branches 0x39, 0x44/0x45/0x47, 0x52, 0x53, 0x5c, and the after flags of 0x2e, 0x35, 0x4c, 0x59.
- **The after slot (verified, never reached in a session).**
  - 0x2e/0x35 RenderBody, 0x4c with the object light pulse, 0x53/0x59/0x5c meshes.
  - The client's after pass `0x016d6949` skips world 121: 0x79 is outside its world list, and the class's handler
    byte +5 stays 0. The native gate is the same, so this slot is compared but draws nothing in practice. Objects of
    types 0x2e, 0x35, 0x4c and 0x59 are therefore not drawn in 121, as in the client.
- **Devias 0x67 (verified).** At the action's last key (`+0xb4 == keys − 1`), `SetAction(rand() % 32 == 0 ? 1 : 0)`,
  drawn from the object generator right after the outer draw.

## Shared lines (narrow seams)

- `reconstructed/objects/world_test_area_visual.c` (new):
  - both slots, `mu_devias_action_pick`, `mu_obj_frame_whole`;
  - picked up by the existing `world_*_visual.c` wildcard in both Makefiles.
- `world_slots2_visual.c`: class 121 chained behind the SLOTS2 classes (custom, after, bitmap 0x800a, type 0x14's
  list).
- `world_visual_slots.h` / `world_visual_slots2.h`: four declarations; the pseudo call `MU_OBJ_CALL_VERTEX_LIGHT`
  (`0x06fd0918`); `mu_obj_set_action`, `mu_devias_action_pick`, `mu_obj_frame_whole`.
- `world_visual.h`: `mu_slot_model` gains `bone_count` and `action_count`, appended at the end. The Python
  `SlotModel` structures of the other validators stay valid: only world 121 reads the new fields.
- `kanturu_underground.c`: its static `set_action` becomes the exported `mu_obj_set_action`, with the same body. This
  is the one shared SetAction wrapper; `q_set_action`/`wp_set_action` are untouched.
- `native/core/mu_objects_runtime.c` (the seam for RENDER-ITEMS-002R and RENDER-EFFECTS-018):
  - `slot_model` fills the two counts;
  - `test_area_custom_call` (world 121 only) runs a scratch log and routes particles, with `test_area_bone`
    answering NaN for a missing bone (refused and counted);
  - `slot_vertex_light` replays the vertex-light pseudo call after the pose and before `mu_draw_default_options`,
    gated on the event, which only 121 emits;
  - the Devias 0x67 call sits right after the outer draw.
  - Nothing in the mesh draw or `mu_model` changed: the replay writes through `mu_model_host`.
- `native/Makefile`: the `worlds-121-host` rule. `scripts/validators.toml`: one row. Coverage JSON: the two 121
  statuses.
- 6b test updates: `test_worlds_after2.test_classes`, `test_worlds_slots.test_dispatch` and
  `test_worlds_slots2.test_dispatch` (121 now has class slots).
- Not changed: `reconstructed/particles/visual.c` line 131 still says 0x67 is "not ported". A comment-only fix would
  pull ~36 particle validator rows into the affected set. The next lane that touches that file should fix it.

## Checks

Under the 2026-11-04 test budget: no lane gate. `nice -n 10`, `make -j4`, `--jobs 2`; load 1m 5–15 with other
lanes active. Env as below.

| Check | Result | Wall |
|---|---|---|
| `validate_worlds_121` with mutants (once, at `c7eabfbe`) | 4 families × 1,000 = **4,000 cases, 0 mismatches/stops** (`custom_121`, `actions_121`, `after_121`, `devias_67`); **31/31 mutants detected** (lowest 5, "Devias roll % 31"), all compiling, each anchor matching exactly once | 162 s |
| The first mutant run (at `fc631914`) | 28/31: three action/roll mutants never hit by the random cases. The focused family `actions_121` was added (window-edge frames, seeds whose first `rand()` lands on the compared residues), then the second run above | 176 s |
| `validate_worlds_slots3` with mutants (once, at `fc631914`; its compiled inputs are unchanged since) | 36 families × 1,000 = 36,000 cases, 0 mismatches/stops; `rng_2` now compares 0x67 whole (104 cases draw the choice); 22/22 mutants (lowest 44) | 141 s |
| `run_validators.py --private --no-mutants --cache --affected origin/main --jobs 2` (63 rows, at `fc631914`) | 63/63 pass, 1,040,924 cases, 0 mismatches. Brief 8b's native reach is included: meshdraw, model_edge/light, terrain(_remaining), viewport_monsters, movement, path, session_party, audio_*, icarus/icarus_c2, worlds_fog, render_effects16/17, app_polish1/4 | 862 s |
| `validate_icarus_c2`, `validate_audio_callers` again at `c7eabfbe` (flagged by `--list-affected-since fc631914` through the new unit test file only) | 2/2 pass | 23 s |
| `run_test_suites.py --affected origin/main` (`MU_RECOVERY_INTEGRATION=0`, `MU_GATE_JOBS=2`) | 8 suites, 1,456 tests, 1,239 passed, 217 skipped, 0 failures | 422 s |
| Private modules (`MU_RECOVERY_INTEGRATION=1`): test_worlds_121, test_worlds_slots, test_worlds_slots2, test_worlds_after2 (6b), native test_native_worlds_121, test_validators_manifest | 50 tests OK | 178 s |
| `native/tests/worlds_121_host.c` (synthetic model, production first pass, in the portable suite) | lit model: 0.5 per normal for types 6..12, the transform's lights for 0x52 and world 120 (restored on the next pose); 0x13 frame 3: 4 particles, frame 11.5: 2 served + 3 refused; Devias 0x67 draws once more only at the last key. Negative control: without `slot_vertex_light` it fails | < 2 s |
| `nice -n 10 make -j4` | pass | 23 s |
| `scripts/audit_repository.py` | 2,015 staged files, 0 rejected | 18 s |
| `world_handler_coverage.py` | 48 classes, 57 registrations, 288 addresses; primary 144/144; slots **144/144** (custom 48, after 48, invisible 48) | < 1 s |

**Fidelity** (default draw; "before" = the `ce0ebd71` binary, taken once):
- DATA-ACQ-002: 32/32 byte-identical (PNG frames, OBJECT and light dumps). Before / after: 63 / 42 s.
- October 22 tour: 14/14 byte-identical. Before / after: 18 / 26 s.
- Devias: both views (02, 02b) hold two type-0x67 objects at action 0, frame 0. The last key isn't reached there, so
  nothing changes; the object runtime refused 0 draws before and after.
- **World 121** (offline, demo layout of the 20 slot types that have a model, `--objects-dir`; not client placement):
  - before: every object black (the world's terrain light is black);
  - after: types 6..12 lit at 0.5, and the 0x801c/8 particles of 0x13..0x15 drawn;
  - 56 particles created, 36 refused (unsupported kinds), object runtime 0 refused, 25 frames.
  - Window PNGs (local): `~/Documents/MTM/mu-mac-tools/native/renders/render-worlds-121/png/world121-demo-before.png`
    and `world121-demo-after.png`.

Steward validators: validate_worlds_121 (mutants: yes, new; done once at `c7eabfbe`), validate_worlds_slots3 (mutants:
done once at `fc631914`), and without mutants the 63 rows of `--affected origin/main` (ran at `fc631914`; `c7eabfbe`
changes only `validate_worlds_121.py`, its unit test and its toml row, and the two rows that `--list-affected-since`
flags through the test file passed again at `c7eabfbe`).

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

## What's left

- Particle kinds 0x801e/7, 0x801c/9 and 0x801b/5 have no native consumer. The particle module refuses and counts them;
  only 0x801c/8 is served (4 of the 28 call sites).
- No live reference for world 121: no capture, no warp, and the installed `EncTerrain122.obj` does not decode
  natively. The frame above uses a demo layout.
- The particle visual's stale comment (above).
- Still open from SLOTS3: the Kanturu hook past its flames (37/40), Blood Castle's inline draws, and occasional named
  types in other classless worlds.

Local files kept: `~/Documents/MTM/mu-mac-tools/native/renders/render-worlds-121/png/world121-demo-{before,after}.png`
(window-only, 2 PNGs). Everything else (renders, scratch, the before binary, build dirs) is deleted.
