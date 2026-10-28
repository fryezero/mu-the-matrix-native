# Native client verification map

This directory is the maintained source for verifying the user-facing behaviour of the native Mu The Matrix
programs under `native/build/`. Read this index before driving, then use the matching feature file as the
recipe. The skill body (`../SKILL.md`) explains the helpers and the hard rules.

## Baseline preconditions

- Build: `make -C native && make -C native viewer` finished; `tools/python/bin/python` exists.
- `V=.claude/skills/verify-mu-native/scripts` and `RUN=$($V/new-run.sh LABEL)`: a fresh run with its own
  synthetic root (`$RUN/root`: World1 as world 0, World94, World95, `Player.bmd`, `Data/Verify/synthetic1_v12.bmd`)
  and offline session (`$RUN/session.txt`: servers S-1 / S-closed / S-3; characters Alpha 0x00, Bravo 0x22,
  Charlie 0x03; slot 0 joins world 0 at tile 120,120, slot 1 at 128,128).
- `$V/doctor.sh "$RUN"` printed `DOCTOR OK`.
- No `MU_GAME_ROOT` is read unless a feature file says so; the original client is never touched.

## Driving conventions

- Every command runs as `$V/run-tool.sh "$RUN" NAME TOOL ARGS...`; NAME is the proof file stem.
- Default backend is headless GL (`--headless --backend gl`); `--backend soft` when GL is unavailable or a
  host-independent hash is wanted; drop `--headless` and add `--seconds S` for a real window.
- `mu-client` always gets `--no-audio --no-store`; frame captures go to `--out-dir "$RUN/proof/NAME"`.
- Treat every command as literal: keep tile numbers, frame numbers, flags and action spellings unchanged.
- World numbering: `--world N` means folder `World{N+1}`; the synthetic root has world 0 only (plus 94/95 for
  character select and login).

## Proof and skip reporting

- Proof is the `.cmd`, `.stdout`, `.stderr`, `.exit` quadruple plus the PNG frames under `$RUN/proof/`, and
  `run.json` for the commit and binary digests.
- Capture the action and the resulting state: the stderr action line, the frame saved on the change, and the
  summary field (`$V/summary.py FILE KEY`).
- Side-effect proof: `ls -la ~/Library/Application\ Support/MuTheMatrixNative` before and after is identical.
- Record the sub-feature ID and the entry point used with every artifact.
- Report an unreachable path with the attempted command and the unmet precondition. Do not report a skipped
  entry point as verified through a different path.

## Feature entry contract

Each feature file starts with an H1 title and one paragraph describing the user-visible behaviour, then uses
exactly four H2 sections in this order:

1. `Sub-features`: short IDs, one line each.
2. `How to get to it (user POV)`: every user entry point.
3. `Driving it with run-tool.sh`: `Preconditions:` then labelled bullets pairing each user action with the
   exact command and the observable result.
4. `Gotchas`: traps that waste or invalidate a run.

Values marked "at the sync commit" were observed at commit `024e949` with the synthetic root of
`scripts/make-root.py`; a change in them is a signal to look, not automatically a failure.

## Features

- [Scene flow](./scene-flow.md): title, login, character select, loading and world in `mu-client`, scripted
  and automatic, headless and windowed.
- [Walk-around](./walk.md): click-to-move, walk and run actions, wheel zoom in `mu-world` / `mu-walk`.
- [Model viewer](./model-viewer.md): load, render, GL-versus-software agreement, view and pose changes in
  `mu-viewer`, layout in `mu-render info`.
- [Terrain view](./terrain-view.md): a world's terrain in `mu-viewer --terrain`, with backend agreement.
- [Protocol CLI](./protocol-cli.md): frame building, parsing, dechunking and send obfuscation in `mu-proto`.
- [Fixture sessions](./fixture-session.md): discovered full-stack session suites, inbound script events,
  per-route hits and journal counts in `mu-session`. This path uses no renderer or socket listener.

- [World input](./input.md): shared input files, cast, pick-up, right-click skills, panel coverage and native IME focus.
- [Preview refresh](./preview-app.md): owner-requested app build, no-Python first run,
  manifest refusal, real window/panel/click-travel checks and installation boundary.
