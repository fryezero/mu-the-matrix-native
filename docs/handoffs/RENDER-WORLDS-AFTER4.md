# RENDER-WORLDS-AFTER4

The follow-up named in [AFTER3](RENDER-WORLDS-AFTER3.md) "Remaining": the whole draw-first predicate, a render-time
terrain-light consumer, the action record +8 proof and the velocity writer.
[Addresses, checks, fidelity and limits](../research/client-worlds-after4.md).

- Claude Opus 5.5 lane. Worktree `~/Documents/MTM/worktrees/render-worlds-after4`, branch
  `claude/render-worlds-after4`, from origin/main `d9389d55`, merged with origin/main `994460cb` (#279, app only,
  clean). Input links `tools/python` and `evidence` point at the main checkout and are never committed.
- **1. Draw-first predicate `0x017fcd18` (verified, complete):**
  - all 22 world cases and the true branches of the six default-chain steps, then Q2's class slot 0x10;
  - `reconstructed/objects/world_draw_first_visual.c`, `mu_draw_first`;
  - the native `render_first` now calls it for every world: camera = the frustum apex, tower state = its
    constructor value 0.
- **2. Velocity (+0xbc) writer (static; not ported):**
  - the writer is the action registry `0x01ec7d5c`: its SetAction handlers `0x00ce1460..0x00ce15c0` store entry +8;
  - they are reached by the create tail's SetAction(0) `0x00ce4a17` and the move tail's tick `0x00ce4b5b`;
  - the registry's (type, action) entries are filled at run time from a source not found statically;
  - field counts are unchanged (144: 40 near the hero; 142: 3).
- **3. Render-time terrain light:** the after pass's AddTerrainLight (143 type 0x71) now goes into the frame light
  grid at once (`mu_world_add_light`) and is counted in `rt.render_light_events`.
- **4. Action record +8 = BMD key count (verified):** the original reader over all 181 installed world-141
  (`Data/Object142`) models; type 0x2c has 32 keys.
- **Shared lines:**
  - `mu_objects_runtime.c`: `render_first` with `eye` in its context, and the after-pass light loop;
  - `mu_objects.h`: `render_light_events`, and `mu_objects_prepare_after` takes `mu_world *`;
  - `world_visual.h`: `mu_draw_first_inputs`;
  - `native/Makefile`: the `render-light-host` rule;
  - one validator row.

## Checks

- `validate_worlds_after4`: `draw_first` 9,000 + `action_keys` 181 = **9,181 cases equal, 0 mismatches/stops,
  40/40 compiled mutants**. Registered (needs `MU_GAME_ROOT`).
- Portable: `reconstructed/objects/test_worlds_after4.py` (5 + 1 private) and
  `native/tests/test_native_render_light.py` (production host).
- Private validators on the merge (`run_validators.py --private --jobs 2`, `MU_RECOVERY_INTEGRATION=1`,
  `MU_GAME_ROOT` = the installed client, `MU_SECTION3`): **6 pass, 0 fail**.

  | Validator | Result |
  |---|---|
  | `validate_worlds_after4` | pass |
  | `validate_worlds_after3` | pass |
  | `validate_worlds_after2` | pass |
  | `validate_worlds_after` | pass |
  | `validate_worlds_q2` | pass |
  | `validate_object_render` | pass |

- Gate on the merge (`nice -n 10 bash scripts/local-macos-ci.sh`): **38 suites, 1,812 tests, 1,572 passed, 240
  skipped, 0 failures/errors; fixtures, native viewer, live readers; audit 1,807 files, 0 rejected**. Only docs
  changed after the gate.
- Fidelity at the DATA-ACQ-002 arrival tiles, base `d9389d55` vs lane:

  | Capture | Default clock | Live clock |
  |---|---|---|
  | 112 Ferea | 2.250 → **2.241** | 2.250 → **2.241** |
  | 91 Acheron | 6.856 = (after-character differences 6 → 0) | 6.400 = (6 → 0) |
  | 12 more (113, 117..120, 122, 123, 129..131, 133, 56) | image equal, more first-pass draws (body-light copy fields) | image equal |
  | the other 18 | byte-identical (PNG, OBJECT, light) | byte-identical |

  With `draw_all`, Ferea goes 2.227 → 2.228, Acheron 6.856 = (6 → 0), and 143/144 stay identical. The 143 arrival
  tile has no visible 0x71 object, in live too.

## Remaining

- The velocity data source: who fills the registry map `0x01ec7d5c`+0x10 (static search), or a read-only live
  dump of its entries under GAME-LOCK. The entries are client data, so native would take them as a local sidecar or
  from their real source. The handlers themselves are simple (entry +8 → +0xbc, a random frame into +0x34).
- The writers of world 0x27's tower state (singleton `0x009a6ef3` +0x78 +4).
- A capture that shows a render-time light (143 type 0x71 in view).

No original client was started; the DATA-ACQ-002 inputs were only read. Renders, scratch and the base worktree
`worktrees/rwa4-base` are deleted at handoff; no local input needs keeping.
