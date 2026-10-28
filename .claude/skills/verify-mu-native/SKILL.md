---
name: verify-mu-native
description: Drive the native Mu The Matrix executables on a synthetic game root or run session scenarios over the loopback fixture, and capture proof. Use to verify native behaviour, demonstrate or screenshot a native change, test session routes and inbound frames, or before merging native work.
---

# Verify the native client

The native track builds SDL2 + OpenGL 2.1 programs under `native/build/`. Users touch `mu-client` (title,
login, character select, loading, world), `mu-world` (walk-around in one world) and `mu-viewer` (one model,
or `--terrain`); `mu-walk`, `mu-render`, `mu-terrain` and `mu-proto` are headless CLIs over the same code.
Every window program also runs headless (`--headless --out-dir DIR`, software or offscreen-GL backend) with
the same scene code, takes scripted input (`--script "FRAME:ACTION ..."`), prints one JSON row per captured
frame and a final `{"summary": true, ...}` row on stdout, and logs actions and scene changes on stderr.
The separate `--fixture` drive runs `mu-session` over the in-process loopback transport. It proves session
apply functions and requests with a stub world port; it does not drive scene login or render the world.

The installed client is neither needed nor used. Every run drives a synthetic game root authored by the
fixtures in `native/tests` (`scripts/make-root.py`). Installed data (`MU_GAME_ROOT`) is an optional,
read-only extra for private checks and is reported as a separate run.

Read [`features/README.md`](features/README.md) before driving: it is the maintained map of user-facing
features, their entry points, the exact drive and the end state that proves each one.

## Hard rules

- Never touch the original client: no `live-readers/`, no signals or window interaction with the Wine app
  or Preview.app, no process lookups by name. The game lock belongs to the owner.
  For an explicit Preview refresh request, [preview-app.md](features/preview-app.md)
  covers a newly built app process you start in an isolated HOME and the separately
  authorized installation. Existing owner processes remain untouched.
- Never write into `MU_GAME_ROOT` or `~/Library/Application Support/MuTheMatrixNative`. Every drive goes
  through `scripts/run-tool.sh` (it points `MU_NATIVE_SETTINGS_DIR` into the run) and `mu-client` always
  gets `--no-store`.
- Stop only processes you started (`RUN/pids`). Keep every proof.
- Never weaken a journey to make it pass. An unmet precondition is a failure with its reason, recorded in
  that feature's Gotchas.

## Launch

Build once (clang, Crypto++, SDL2 and jpeg-turbo from Homebrew; `docs/setup.md`):

    make -C native && make -C native viewer

Ready means `native/build/mu-client mu-world mu-walk mu-viewer mu-render mu-proto mu-terrain mu-session` all exist.
Python is the project venv `tools/python/bin/python` (`python3 -m venv tools/python && tools/python/bin/python
-m pip install -r tools/requirements-lock.txt`). Keep the helper path short:

    V=.claude/skills/verify-mu-native/scripts
    RUN=$($V/new-run.sh scene-flow)

`new-run.sh` prints `verify-runs/<date>-<time>-scene-flow` and writes there: `root/` (synthetic game data:
World1 open ground, World94 character-select world, World95 login backdrop, `Player.bmd`, the title logo and
the textured model `Data/Verify/synthetic1_v12.bmd`), `session.txt` + `servers.txt` + `characters.txt` (the
offline session: servers S-1, S-closed, S-3; characters Alpha 0x00, Bravo 0x22, Charlie 0x03; joins into
world 0), `tmp/settings/`, `proof/` and `run.json` (commit, dirty flag, SHA-256 of each binary). About two
seconds. There is no server to keep alive: launch is build + new-run, and each drive is its own short-lived
process with its own `--out-dir`. Two runs never share state.

Teardown: `$V/cleanup.sh "$RUN"`.

## Doctor

    $V/doctor.sh "$RUN"

Read-only. Checks that the eight binaries exist, warns when a source under `native/` or `reconstructed/` is
newer than the build, checks that the venv imports the fixtures and Pillow, `sdl2-config`, the run's root
files and recorded commit, that no tool from this run is still running, and that an offscreen GL context can
be created (it renders the run's model at 16x16 and names the GL renderer). Ends with `DOCTOR OK` (exit 0) or
`DOCTOR FAIL` (exit 1). Run it before trusting any failed drive.

## Drive

Every drive is `$V/run-tool.sh "$RUN" NAME TOOL ARGS...`. It stores `proof/NAME.cmd`, `.stdout`, `.stderr`
and `.exit`, echoes stdout and exits with the tool's code. Pass `--out-dir "$RUN/proof/NAME"` for frames;
run-tool.sh creates that directory (and the parent of an `--out` path) first, because the windowed programs
do not. Spell every argument out: a shell variable holding several flags is not split into words under zsh,
and the program then prints its usage and exits 2.

Headless GL (`--headless --backend gl`) is the default: the real OpenGL renderer through an offscreen CGL
context, virtual 40 ms ticks (deterministic), a PNG per captured frame. `--backend soft` is the software
rasterizer (host-independent hashes, no GL). For a real window drop `--headless`, add `--seconds S` so the
program quits by itself, and use `shot:NAME` in the script to capture the window into `--out-dir`.

### mu-client, the game flow

    $V/run-tool.sh "$RUN" flow mu-client --game-root "$RUN/root" --session "$RUN/session.txt" \
        --headless --backend gl --no-audio --no-store --width 320 --height 240 \
        --frames 300 --every 25 --out-dir "$RUN/proof/flow" --auto

Scenes: 2 title, 3 login (server select, then the OFFLINE DEMO panel), 5 character select, 4 loading,
6 world. `--auto` plays the whole journey (group 0, server 0, account, Tab, password, Enter, Right, Enter,
wheel, Esc, Enter, quit). `--script "FRAME:ACTION ..."` sends actions at headless frame numbers: `enter`
`esc` `left` `right` `tab` `back`, `text:STRING`, `click:X,Y`, `dblclick:X,Y`, `click:group:N`,
`click:server:N`, `click:row:N`, `dblclick:row:N`, `wheel:N`, `quit`; windowed only `shot:NAME`,
`resize:W,H`, `fullscreen`. Frames are saved every `--every` frames, on the first frame of each scene, on
every scene change and on the last frame, named `frame-NNNN-sS-TAG.png`. stderr logs `frame N (scene S):
ACTION` and `scene A -> B (reason)`. Summary keys: `transitions` ("A -> B at T ms: reason"), `visits`,
`scene_frames`, `presents`, `logins`, `server`, `hero_slot`, `hero_class`, `selected_hero`, `world`,
`status`, `charsel`, `charcreate`.

Windowed, a real window on the Mac's display for four seconds:

    $V/run-tool.sh "$RUN" flow-window mu-client --game-root "$RUN/root" --session "$RUN/session.txt" \
        --no-audio --no-store --width 640 --height 400 --seconds 4 --title "verify-mu-native" \
        --out-dir "$RUN/proof/flow-window" --script "10:enter 14:enter 30:enter 60:shot:world"

### mu-world and mu-walk, the walk-around

`mu-world` is the window build (GL and headless GL); `mu-walk` is the software-only build with the same
options and output. `--world N` loads `Data/World{N+1}`; the synthetic root has world 0 (World1).

    $V/run-tool.sh "$RUN" walk mu-world --game-root "$RUN/root" --headless --backend gl --no-audio \
        --tile 120,120 --walk 124,123 --frames 90 --every 1 --width 320 --height 200 --out-dir "$RUN/proof/walk"

`--walk "X,Y X,Y"` clicks those tiles in turn (window-procedure mouse globals, client pick, path finder);
`--wheel "F:+1 F:-1"` zooms at frame F; `--class C` sets the hero class byte. Frame rows carry `tile`, `hero`
(x, y, z in world units), `action` (1 stand, 50 walk, 79 run), `moving`, `run`, `safe`, `fov`, `pitch`;
`{"log": ...}` rows say `click-to-move: tile X,Y (N cells)` and `arrived: tile X,Y`. Summary: `moves`,
`arrivals`, `path_refused`, `picks`, `hits`, `walked`, `units_per_step`, `world_fov`, `renderer`. Combat,
items, NPC, skill, progression, social and travel scripts exist too (see the usage text); their windows need
`--gfx` with converted movies, which the synthetic root does not have.

### mu-viewer, one model or the terrain

    $V/run-tool.sh "$RUN" model mu-viewer "$RUN/root/Data/Verify/synthetic1_v12.bmd" --headless --backend gl \
        --compare --width 320 --height 240 --out "$RUN/proof/model.png"
    $V/run-tool.sh "$RUN" terrain mu-viewer --terrain "$RUN/root" --world 0 --headless --backend gl \
        --compare --width 320 --height 200 --out "$RUN/proof/terrain.png"

`--compare` renders the other backend as well and reports `differing_pixels`, `pixels_over_8`,
`max_channel_diff`, `mean_channel_diff` (model) or `pixels_over_8`, `pixels` (terrain). View options:
`--yaw D --pitch D --zoom F --action N --frame F --width --height` (full list: `native/build/mu-render` with
no arguments). `mu-render info MODEL` prints the parsed layout as JSON.

### mu-proto, the protocol CLI

    $V/run-tool.sh "$RUN" proto-build mu-proto build C1 F1 010203

Commands: `build HEAD OPCODE PAYLOAD [--xor]`, `parse FRAME`, `dechunk STREAM`, `xor-encode OBJ`,
`xor-decode OBJ`, all hex. A head outside C1..C4 gives `status: BAD` and exit 1.

### Fixture sessions

    $V/run-tool.sh "$RUN" fixtures --fixture
    $V/run-tool.sh "$RUN" hero --fixture native/fixture/scenarios/hero-progress.scn \
        --script '60:inbound:c10c55941500000015000000'

Read [the fixture recipe](features/fixture-session.md) for the JSON contract, count checks and how later
domain lanes add scenarios. The same runner is part of `make test` and `scripts/local-macos-ci.sh`.

## Evidence

Everything under `$RUN/proof/` is the proof and survives cleanup: `NAME.cmd` (what ran), `NAME.stdout`
(frame rows and summary), `NAME.stderr` (actions, scene changes, missing textures), `NAME.exit`, the PNG
frames in `NAME/`, and `run.json`. Read summaries with
`$V/summary.py "$RUN/proof/NAME.stdout" [KEY...|--frames|--logs|--last]`.

Standards:

- Exercise the real user path: scripted keys and clicks through the scene code, not the `native/tests`
  hosts, ctypes calls or internal setters. Those are regression tests, not proof.
- Fixture drives exercise the dev session tool's seeded path. Report them as session evidence, separate
  from scene or rendering proof. Their inbound journal rows have `jnl: frame_in`; the final row has
  `summary: true`, `journal` totals and per-scenario `results` with journal counts and route hits.
- Capture the action and the state it caused: the stderr action line, the frame saved on the scene change,
  and the summary field that changed. A final screen alone is not proof.
- Verify side effects: list `~/Library/Application Support/MuTheMatrixNative` before and after (unchanged),
  `MU_GAME_ROOT` untouched, and the out-dir holding exactly the frames the save rule predicts.
- Look at the PNGs. Synthetic textures are seeded noise, so terrain and skinned meshes look like coloured
  static; that is the data, not a renderer bug. A flat background with only the banner text means nothing
  drew (`Player.bmd` alone has no meshes).
- Judge numbers against the thresholds in the feature files; they mirror `native/tests` (GL against software:
  under 1/200 of the pixels over 8/255 for a model, under 10 % for terrain). Software hashes are
  host-independent; GL hashes are not, so never pin them.
- State the run label, commit and binary digests from `run.json` with the result.

## Cleanup

    $V/cleanup.sh "$RUN"

Stops only the pids `run-tool.sh` recorded (for example a windowed run without `--seconds`), removes
`root/`, the session files and `tmp/`, keeps `proof/` and `run.json`. Run it after every failed attempt too.
Delete `verify-runs/<id>` by hand when its proof is no longer needed; `verify-runs/` is git-ignored.

## Helpers

| Script | Invocation | Does |
|---|---|---|
| `scripts/new-run.sh` | `RUN=$($V/new-run.sh LABEL)` | run directory, synthetic root, offline session, `run.json` |
| `scripts/make-root.py` | `tools/python/bin/python $V/make-root.py DIR` | the synthetic root and session alone (used by new-run) |
| `scripts/doctor.sh` | `$V/doctor.sh "$RUN"` | read-only health check |
| `scripts/run-tool.sh` | `$V/run-tool.sh "$RUN" NAME TOOL ARGS...` | isolated drive with captured evidence and pid tracking |
| `scripts/summary.py` | `$V/summary.py FILE [KEY...]` | read the summary, frames or logs of a captured stdout |
| `scripts/cleanup.sh` | `$V/cleanup.sh "$RUN"` | stop own pids, remove scratch, keep proof |

## Maintenance

The feature map is the repository's verification source. When a feature, flag or output row changes, update
its file in the same change. Keep the map honest with `/pstack:maintain-verification-skill`.
