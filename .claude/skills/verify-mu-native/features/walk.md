# Walk-around: click to move, walk and run, wheel zoom

`mu-world` (window and headless GL) and `mu-walk` (software) put the hero into one world with the client's
camera. A click on the ground walks the hero there along the client path finder at the client's speed; the
hero stands on arrival; class 3 characters start running after forty steps; the wheel zooms the camera to the
client's 30-degree field of view within half a second.

## Sub-features

- `walk-click` a click on a tile walks the hero there (12 units per step) and the hero stops on that tile.
- `walk-actions` action 50 (0x32, walk) while moving, action 1 (stand) after arrival.
- `walk-run` class 3: run counter grows outside the safe zone; action 79 (0x4f) from step forty.
- `walk-zoom` a wheel notch zooms from the world camera's FOV to 30 degrees.

## How to get to it (user POV)

- `mu-world --game-root ROOT [--world N --class C --tile X,Y]` opens the world window at that tile;
  left-click the ground to walk, use the wheel to zoom, Esc twice to quit, O saves a screenshot.
- Headless, the same program (or `mu-walk`) takes `--walk "X,Y ..."` and `--wheel "F:+1"` instead of the mouse.

## Driving it with run-tool.sh

Preconditions:

- `RUN` from `new-run.sh`, `doctor.sh "$RUN"` OK, `V=.claude/skills/verify-mu-native/scripts`.
- Every command below carries the same base:
  `--game-root "$RUN/root" --headless --backend gl --no-audio --every 1 --width 320 --height 200`.
  Write it out each time; do not bundle it in a shell variable (zsh does not split `$VAR` into words).

- **Click to move.** Start at 120,120 and click 124,123. Run
  `$V/run-tool.sh "$RUN" walk mu-world --game-root "$RUN/root" --headless --backend gl --no-audio --every 1 --width 320 --height 200 --tile 120,120 --walk 124,123 --frames 90 --out-dir "$RUN/proof/walk"`.
  `$V/summary.py "$RUN/proof/walk.stdout" --logs` prints `click-to-move: tile 124,123 (5 cells)` then
  `arrived: tile 124,123`. `--last` shows `tile [124, 123]`, `hero [12450.0, 12350.0, 60.0]`, `moving 0`,
  `action 1`. Summary `moves` 1, `arrivals` 1, `path_refused` 0, `units_per_step` 12.0, `renderer` the GL
  renderer name (`software` with `mu-walk`).
- **Actions while moving.** In the same capture, `--frames` rows with `moving 1` have `action 50` except the
  first (the click lands, then the walk action follows one step later); the final row has `action 1`; `run` is
  0 throughout (class 1 does not run); `safe` is 0 (tiles outside y 100..110).
- **Run after forty steps.** Class 3 walks 14 tiles. Run
  `$V/run-tool.sh "$RUN" walk-run mu-world --game-root "$RUN/root" --headless --backend gl --no-audio --every 1 --width 320 --height 200 --class 3 --tile 120,40 --walk 120,54 --frames 120 --out-dir "$RUN/proof/walk-run"`.
  Among the moving rows (after the first) both `action 50` and `action 79` occur, and the first row with
  `action 79` is the first row whose `run` is 40.
- **Wheel zoom.** One notch in at frame 3. Run
  `$V/run-tool.sh "$RUN" walk-zoom mu-world --game-root "$RUN/root" --headless --backend gl --no-audio --every 1 --width 320 --height 200 --wheel "3:1" --frames 30 --out-dir "$RUN/proof/walk-zoom"`.
  Frame 2 has `fov 37.0` (World1's own camera record), the last frame `fov 30.0` and a `pitch` below -48.5.
- **Proof.** `frame-0000.png`, a middle frame and `frame-0089.png` of `proof/walk/` show the camera gliding
  over the noise-textured ground; the frame rows are the position record. Software renders are deterministic:
  two `mu-walk` runs with the same arguments give identical `sha256` per frame.

## Gotchas

- Exit 2 with the usage text on stderr means the argument list reached the program wrong (an unsplit shell
  variable under zsh, or a flag without its value). Spell the arguments out.
- The hero has no body on the synthetic root (`Player.bmd` is a skeleton, there are no class parts), so the
  walk is visible as camera motion and in the JSON rows, not as a figure.
- `--every` defaults to 10: pass `--every 1` for one row per frame, or the action sequence has gaps.
- Positions are `tile * 100 + 50` units; ground height is 60 (1.5 x 40 from the synthetic height map).
- `--world 1` would load `World2`, which the root lacks (`EncTerrain2.map: missing or undecodable`, exit 1).
- A wall line at y 150 (x 60..199) and the safe-zone strip at y 100..110 are part of the fixture; paths that
  cross the wall are refused or stop short (`path_refused` counts them).
- `mu-world` plays audio unless `--no-audio`; the synthetic root has no sounds, so the flag only avoids noise
  on stderr.
