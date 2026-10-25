# WORLD-RT-001 handoff: the world runtime (`mu_world_rt`)

Lane: world (stage 1). Branch `claude/world-rt`, built on PR #161 (`claude/architect-native-port`, the design in
`docs/design/native-port/`). Milestone row: [plan.md, section D](../design/native-port/plan.md).

## What changed

`native/world/main.c` (3,622 lines, one file-static `app`, compiled three ways: `mu-world`, `mu-walk` with
`-DMU_WORLD_NO_GL`, and textually into mu-client/mu-shell by `world_embed.c`'s `#define main mu_world_cli_main` +
`#include "main.c"`, plus a fourth time by `native/tests/quest_travel_host.c`) is now one module:

| File | What it is |
|---|---|
| `native/world/mu_world_rt.h` | The public API: `mu_world_rt_options` (the one options struct), `mu_world_rt_default_options`, `open`/`close`, `message`/`key`/`hotkey`/`right_button`, `resize`, `set_clock`, `frame`, `end_frame`, `draw_soft`, `draw_gl`/`gl_setup`/`gl_teardown`/`set_gfx` (GL builds), sound mix, `walk`, `folder` |
| `native/world/world_rt_internal.h` | `struct mu_world_rt` (main.c's `app` without the CLI's script state and without the GL handles, field names kept), the part enum from `parts.def`, the internal functions shared by the module's files |
| `native/world/world_part.h` | `mu_world_part_ops`: `open`, `close`, `pre_tick`, `tick`, `frame`, `draw_gl`, `draw_soft`, `gl_setup`, `gl_teardown`, `report_frame`, `report_summary`; `mu_world_draw` (the pass context: size, open perf phase, terrain faces, raster) |
| `native/world/parts.def` | THE list: 21 rows `MU_PART(id, ops, pre_tick, tick, frame, draw_gl, draw_soft, report)`; the row order is the open order |
| `native/world/world_rt.c` | load / unload / travel / the frame / both draw passes / GL lifetime / reports / the GFx attachment, each dispatching the parts through a column (`EACH(COL_TICK, i)` ...). Builds and checks the column orders once (`seq_build`: a hook exactly where a column has a number, no shared numbers) |
| `native/world/parts/*.c` | `terrain`, `hero`, `sound`, `npc` (rows `npc_demo`, `npc`), `actors` (rows `actors`, `actor_effects`), `objects`, `env`, `particles`, `combat`, `progress`, `items` (rows `items`, `item_labels`), `names`, `players`, `social`, `helpers`, `map`, `gfx` (row `quest_step`), `marker`: main.c's code for each subsystem at each place, with the part's GL handles and caches as its own state |
| `native/world/input.c` | Today's input handling exposed: window messages and key states to the walk, `mu_world_rt_hotkey` (Alt, Space, 1..0 from mu-world's window), `mu_world_rt_right_button` (NATIVE-SKILL-001's right-click cast) |
| `native/world/world_tool.c` | `mu-world` / `mu-walk`: every flag, usage text, every `--*-script` driver, the headless loop on the virtual clock, the window, SDL audio, the WAV |

Deleted: `native/world/main.c`, `native/world/world_embed.c`, `native/world/world_embed.h`. No `#define main`
remains in `native/world` or its users (`quest_travel_host.c` now opens the runtime).

One options struct: `client/main.c` parses the world flags straight into `front.world` (a `mu_world_rt_options`
from `mu_world_rt_default_options`); `mu_shell_config.world` carries it unchanged; `shell.c open_world` copies it
and adds only the join (world, class, tile, angle, equipment, name, level), the drawable size, the audio switch and
`quiet`; `mu_world_rt_open` reads it.  `world_options()`, `mu_world_embed_config` and the fourteen world fields of
`mu_shell_config` are gone (the Swift LaunchPlan, layer 1, still passes the same flags; APP-LIVE-001 removes them).

mu-client and mu-shell reach the keys mu-world reaches: `shell.c world_frame` sends each key press to
`mu_world_rt_hotkey` after the key state and message (as mu-world's window does), and `mu_shell_mouse_button` sends
a right press to `mu_world_rt_right_button` first (consumed only over a monster with the GFx layer and combat on).
Headless mu-client scripts cannot press those keys (`enter esc left right tab back` only), so no recorded output
changes; in the window, Alt/Space/1..0 and the right-click cast now work in mu-client as in mu-world.

Makefile (`native/Makefile`, block "WORLD-RT-001"): `WORLD_RT_SRC`/`WORLD_RT_HDR`, objects in `build/world-rt`
(no GL: mu-walk, quest-travel-host) and `build/world-rt-gl` (mu-world); `CLIENT_SRC` lists `$(WORLD_RT_SRC)`
instead of `world/world_embed.c`; the mu-world, mu-shell and mu-client rules remove a stale `world/main.o` or
`world_embed.o` of an earlier build before linking their `*.o` globs.

## Checks actually run

All on this Mac (Apple M5, macOS, clang), the worktree of branch `claude/world-rt`. "Baseline" is the branch point
`8efe6e7` (PR #161's head over `f997742`) built before any change; its `mu-walk`, `mu-world`, `mu-client`,
`mu-shell` and `quest-travel-host` were kept and compared with the new ones.

1. **Baseline**: `native/tests` 478 tests OK (77 skipped: private inputs, mugfx not built).
2. **verify-mu-native recipes** (synthetic root only, `scripts/new-run.sh` + `run-tool.sh`): the feature map's
   headless drives (model viewer 5, protocol CLI 7, terrain 2, scene flow 5, walk-around 3) plus 16 more over the
   world (the flows in `--backend soft` and through `mu-shell`, a world visit with `--combat --items --npc
   --progress` in mu-client and mu-shell, the walk drives in `mu-walk` and in `mu-world --backend soft`, one
   `mu-walk` and one `mu-world` GL drive with item, progress, travel, social and chat scripts, `--boots`,
   `--auto-move` and `--fidelity-dump`, the legacy box with `--no-env --no-particles --no-names --no-map
   --joint-demo`, and four usage/error exits): 38 drives, 846 files (stdout, stderr, exit, command, every PNG and
   the fidelity dumps). The baseline twice: 0 differences (headless GL is deterministic here). Baseline against
   the new build: **0 differences**.
3. **Differential test suite**: every `native/build` tool replaced by a stub that runs the baseline binary (output
   paths, `--store`, `MU_NATIVE_SETTINGS_DIR` and the GFx log files moved into a shadow directory) and then the new
   binary (whose output the test sees), comparing exit code, stdout, stderr and every file written. All
   `native/tests` modules except `test_native_app` (it bundles `build/mu-client`):
   - portable: 475 tests OK (74 skipped); **200 headless invocations byte-identical** (155 mu-walk, 36 mu-shell,
     6 mu-client, 1 mu-world, 2 quest-travel-host; 9,594 files);
   - portable with GL twins (each mu-walk / mu-shell invocation replayed through mu-world / mu-client
     `--backend gl`, baseline against new, on the test's own fixture): **391 invocations byte-identical**, 19,033
     files;
   - private (`MU_RECOVERY_INTEGRATION=1`, `MU_GAME_ROOT=~/Documents/MTM/mtmOriginal`, `MU_OBJECTS_PLAIN_DIR` = the
     local decoded objects) with GL twins: **449 invocations byte-identical** (58 of them on the installed game),
     22,503 files. 475 tests: 1 failure, 1 error, both pre-existing (below);
   - private plus `MU_LANG_DIR` (the local Lang tables): **449 invocations byte-identical**, 22,503 files; 2
     failures, 3 errors, all pre-existing or environment (below).
   The pre-existing ones, each confirmed by running the test on the baseline binaries: `test_native_particles
   InstalledLorenciaFires.test_fires` expects 17 particle bitmaps, the runtime reports 44 (stale test);
   `test_native_combat ...test_hero_hit_death_and_respawn` fails only with `MU_LANG_DIR` set (respawn tile
   122,120, test expects 120,120). Environment: `test_native_map PrivateTravel` and `test_native_skill Installed`
   raise `KeyError: 'MU_LANG_DIR'` in a one-process run (an earlier test removes it from `os.environ`), and
   `test_native_viewer PrivateInstalledTests` needs `evidence/` captures, which the worktree does not have.
4. **`test_native_app`** with the real binaries: portable 11 tests OK (1 skipped, the private smoke); private 11
   tests OK, including the bundled mu-client's smoke run over the installed game.
5. **Windowed** (a real window, wall clock): `mu-world --seconds 6 --walk ...` baseline 150 frames, 24.98 fps,
   150 logic steps; new 150 frames, 24.99 fps, 150 logic steps, the same summary row (the 25 fps cap). The
   skill's `mu-client` flow-window (8 s, enter the world, Esc, enter again): 169 frames in 8.04 s for both, the two
   window captures byte-identical between baseline and new.
6. **`native/tests/test_world_parts.py`** (new, 8 tests): every parts.def column equals main.c's order, numbers
   unique, hooks exactly where the columns have numbers, each hook still makes main.c's call at that place, the
   runtime dispatches through the columns, `main.c`/`world_embed.*` are gone. Planted mistakes: 7/7 caught (tick
   swap, draw_soft move, open-order swap, report reorder, a dropped pre_tick hook, a combat tick calling the
   pre-step, the names frame losing its call).
7. `make test PYTHON=tools/python/bin/python`: exit 0; 38 suites OK, `native/tests` 486 tests OK (75 skipped,
   the private and mugfx ones; 478 of the baseline plus the 8 new).
8. `scripts/audit_repository.py` on the staged tree: 1,070 staged files, 0 rejected.

## Artifact locations

Local, not committed:
- Scratchpad of this session (`/private/tmp/claude-501/-Users-frye-Documents-MTM-mu-the-matrix-native/5220ae2f-15da-4e2a-96fc-70f84fdfe82a/scratchpad/`):
  `world-baseline/bin/` (the baseline binaries), `world-baseline/native-tests.log`, `world-diff/` (the
  differential logs `log-portable-1.jsonl`, `log-portable-gl.jsonl`, `private-1/`, `private-lang/`, the app
  and `make test` logs), `world-lane/` (the recipe, compare, stub-install, wrapper and runner scripts).
- Worktree `verify-runs/` (ignored): `20261025-090121-baseline-a`, `...-baseline-b` (baseline recipes),
  `...-after-1` (new recipes), `20261025-101639-after-commit` (the recipes again on the committed tree: 846 files,
  0 differences), `20261025-101024-windowed-perf` (the windowed runs and captures).

## Deviations from the sketch (docs/design/native-port/sketch/native/world)

The sketch assumes the session (SESSION-CORE-001, another lane). This milestone does not add `native/session`, so
every deviation below is "the session is not there yet" unless it says otherwise. None needed a redesign.

1. **`mu_world_rt_open(options, error)`** instead of `open(session, assets, options)`. The assets (game root,
   objects, sound table) and the join (world, class, tile, angle, equipment, name, level) are fields of the one
   options struct until the session provides the place and the hero (the brief asks for one struct). `parts_off`
   is not there: the existing feature switches (`combat`, `ground_items`, `no_env`, ...) are kept as they are,
   because removing them would change the existing headless outputs.
2. **No `mu_world_rt_input`** (INPUT-001). `input.c` holds today's handling: `mu_world_rt_message` / `_key` (the
   walk session), `mu_world_rt_hotkey` (Alt, Space, 1..0) and `mu_world_rt_right_button` (the right-click cast).
   mu-world's window and mu-client/mu-shell (shell.c `world_frame`, `mu_shell_mouse_button`) call them.
3. **Extra public calls**: `gl_setup`/`gl_teardown` (the front end owns the GL context, and travel re-creates the
   textures), `set_gfx` (the front end still opens `world_gfx`; the sketch's gfx part opens it once the session
   feeds the windows), `set_clock`, `has_sound`/`sound_rate`/`mix`, `walk`, `folder`, `default_options`. The
   sketch's `mu_world_rt_report(json)` is internal (`world_rt_report_frame/summary` print main.c's rows).
   `draw_gl` exists only in GL builds instead of returning 0 without GL.
4. **`world_part.h`**: the orders are parts.def columns only (not ops fields); the hooks are `open`, `close`,
   `pre_tick`, `tick`, `frame(now)`, `draw_gl`, `draw_soft`, `gl_setup`, `gl_teardown`, `report_frame`,
   `report_summary`. No `mu_sim` argument (no lease without the session), `frame` gets the clock instead of dt
   (names and terrain need it), and the draw hooks share a `mu_world_draw` pass context (the open perf phase and the
   terrain's face count cross part boundaries exactly where main.c's phases did). No `input` hook (INPUT-001).
5. **parts.def has six order columns, not two**: main.c ran the subsystems in different orders in
   `combat_pre_step`, `on_step`, `advance`, `draw_gl`, `draw_soft` and the reports (draw_gl and draw_soft already
   differ for the helpers and the marker), and behaviour preservation needs all six. The row order is the open
   order (`load()`).
6. **21 rows, not the sketch's 17**: no `characters` row (the single MoveCharacters loop over the viewport is
   SESSION-VIEWPORT-001's planned fidelity change; today's actor and player steps stay at their own places);
   added `terrain`, `hero`, `marker` (draw passes the sketch left implicit), and second rows where one subsystem
   acts at two places of a pass (`npc_demo` before the actors, `npc` after the names; `actor_effects`;
   `item_labels`). The sketch's `gfx` row is `quest_step` only (the world_gfx quest step at tick 40); the GFx views
   (map, social, names) are frame hooks of their own parts.
7. **Parts keep cross-references through runtime fields**: the unmigrated demo subsystems (`mu_combat`,
   `mu_world_items`, `mu_npc`, `mu_world_players`, `mu_world_names`, `mu_world_helpers`, `mu_map_session`, ...) and
   the engine services (actors, objects, env, particles, sound) are fields of `struct mu_world_rt`, not part state,
   because they still point into each other (combat -> walk, character, actors; names -> combat; players -> names,
   combat, social; items -> particles, frustum; helpers -> players, particles, character). Each part owns its
   hooks and its GL handles and caches. The sketch's "a part never holds a pointer into another part" holds once
   each domain migration moves its subsystem behind the session (stage 2).
8. **`world_tool.c` uses the internal header** for its `--*-script` drivers (they poke the demo subsystems
   directly, as main.c's did). They become fixture scenarios and input scripts with SESSION-CORE-001/INPUT-001.
9. **shell.c**: besides `open_world`/`close_world`/`world_frame`, the world branches of `mu_shell_mouse_move`,
   `_mouse_button`, `_wheel`, `mu_shell_resize`, `mu_shell_end_frame`, `mu_shell_mix` and `mu_shell_world` changed
   (renamed calls; the right-button cast). All are world plumbing; nothing else in shell.c changed.
10. **`native/tests/quest_travel_host.c`** (not in the lane's owned list) had to change: it was a fourth
    `#define main` + `#include "../world/main.c"`. It now opens the runtime with the same bare options (a zeroed
    struct with the same fields set as before) and reads the same internals; its output is byte-identical (differential run).

## Open items

- Documents outside this lane that still describe the embed or `world/main.c`: `native/README.md` (lines 505,
  712), `docs/research/client-scene-manager.md:168-170`, `docs/research/native-gfx2.md:168`,
  `docs/research/client-maps.md:101`, `docs/research/client-overhead-text.md:204`,
  `docs/research/client-remote-players.md:181`. The orchestrator folds the new paths in with status/handoff.
- mu-client's window now has mu-world's world keys (Alt, Space, 1..0 with `--combat`, the right-click cast with
  `--gfx --combat`). Headless outputs cannot reach them (the scripts send `enter esc left right tab back` only), so
  the equality above does not cover them; they run the same functions mu-world's window runs.
- Kept as main.c had them (behaviour preservation): the map GFx view is never closed and the map session is never
  freed (one per runtime); the runtime's process-global helpers state (`imps[]`) and `mu_lang_shared` are
  SESSION-GLOBALS-001's.
- The demo subsystems are still runtime fields shared by the parts (deviation 7); each stage-2 domain migration
  moves one behind the session and into its part.
- The Swift `LaunchPlan` still passes the feature flags (layer 1 of the old four); APP-LIVE-001 removes them.
- `--*-script` drivers still poke the demo subsystems from `world_tool.c`; they become fixture scenarios and input
  scripts with SESSION-CORE-001 and INPUT-001.
- Registration now: a new part is one parts.def row, its `parts/<file>.c`, its entry in the Makefile's
  `WORLD_RT_SRC`, and, only when it has a switch, a field of `mu_world_rt_options` plus its flag in `world_tool.c`
  and `client/main.c` (was about 14 places).

## Next step

INPUT-001 (this lane's next milestone): replace `input.c`'s message/key/hotkey/right-button exposure with
`mu_world_rt_input` over `mu_input_msg` (GFx first refusal, the key scan `0x00ec5475`, panel bindings, part
`input` hooks in parts.def order), make mu-world's window and the shell call only that, and add the missing keys
(Y, Q/W/E/R, Z, X, J, G, B, N, K, H, D, S, Home/End, F1) with the coverage table. WORLD-ORDER-001 then replaces
`test_world_parts.py`'s literal tick and draw lists with the order recorded from MoveMainScene/RenderMainScene.
