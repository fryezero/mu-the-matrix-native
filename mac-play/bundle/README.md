# Mu The Matrix.app

`mac-play/bundle/` (MAC-BUNDLE-001) builds a double-clickable macOS app that starts the original
launcher, `MuTheMatrix.exe`, in a CrossOver bottle. It replaces the Desktop `.command` files that run
`play-mu.sh`. The app ships no game files and does not create bottles: it starts a bottle made by
[`../installer/`](../installer/README.md) or a hand-built bottle with the same layout (`C:\MuTheMatrix`,
optionally `C:\mutools\mu-modes.txt`).

## Build

You need macOS 13 or later and the Command Line Tools (`xcode-select --install`), which provide
`swiftc`, `iconutil`, `plutil` and `codesign`. From the repository root:

```sh
make mac-bundle                 # mac-play/bundle/build/Mu The Matrix.app
make -C mac-play/bundle test    # the tests below
make -C mac-play/bundle install # copies the app to ~/Applications (INSTALL_DIR=... to change)
```

The build compiles `Sources/*.swift` for the host architecture and draws the icon with
`icon/make-icon.swift`. It then assembles the bundle, copies `mu-launch.sh`, `../installer/lib/mukit.sh`
and `../fast-x87.sh` into `Contents/Resources`, and signs the bundle ad hoc
(`codesign --sign -`). Everything is built from the sources in this directory, and the
output goes to the ignored `build/` directory. The icon is original artwork: a Greek mu over generated
digital rain, drawn with a fixed random seed. It uses no game art. A locally built app has no
quarantine flag, so Gatekeeper opens it without a prompt. If you copy it to another Mac, you have to
allow it in System Settings.

These build-time defaults apply until the settings window saves a settings file:

```sh
make -C mac-play/bundle DEFAULT_BOTTLE=MuMatrix32 DEFAULT_FAST_X87=1 \
    DEFAULT_TIMEWALKER_DIR=/path/to/rosetta-timewalker
```

They end up in `Info.plist` (`MUDefaultBottle`, `MUDefaultFastX87`, `MUDefaultTimewalkerDir`). Without
them, the app defaults to bottle `MuMatrixKit`, fast x87 off and the timewalker set to Auto.

## Use

Double-click **Mu The Matrix**. On the first run, the settings window opens. Choose the bottle and
press **Play**. Later double-clicks run a preflight check, start the launcher and quit the app. The
launcher and game keep running. To get the settings window back, hold **⌥ Option** while opening
the app. It also opens when "Start the game right away" is off, and from the error dialog.

| Setting | Effect |
|---|---|
| Bottle | Any CrossOver bottle. The list marks bottles that are not 32-bit or have no `C:\MuTheMatrix`. |
| Resolution | "Keep launcher setting" (default) changes nothing. A mode from the bottle's `C:\mutools\mu-modes.txt` sets `DevModeIndex` in `C:\MuTheMatrix\LauncherOption.if` before each start, in the launcher's own byte format, keeping `WindowMode` and `ID`. The first change saves the original as `LauncherOption.if.mu-app-backup`. With the public batching-only mugl, the kit caps the index at 2 (see the kit README). |
| Fast x87 | Off: plain CrossOver `wine`. On: `main.exe` runs through rosetta-timewalker with `TIMEWALKER_X87_ONLY=main.exe`; the .NET launcher stays on the plain loader. |
| Timewalker | With fast x87 on: a built rosetta-timewalker folder (`scripts/run-crossover.sh`, `build/libtimewalker.dylib`), as with `play-mu.sh` `MU_TIMEWALKER_DIR`. **Auto** uses the validated cache from `../install-fast-x87.sh` (checked with `fast_x87_ready` from `../fast-x87.sh`). |
| Start right away | Off: the window opens on every start. |

The settings are stored as an XML plist at `~/Library/Application Support/MuTheMatrix/Launcher.plist`,
with the keys `Bottle` (string), `FastX87` (bool), `TimewalkerDir` (string, empty = Auto), `Resolution`
(string `WxH`, empty = keep) and `StartImmediately` (bool). You can edit the file directly. Missing,
mistyped or unreadable values fall back to the defaults.

Each start does what `play-mu.sh` does:
1. It refuses to start while `C:\MuTheMatrix\main.exe` or `MuTheMatrix.exe` runs in any bottle, because
   only one client can run.
2. It restarts the selected bottle's wineserver with an explicit `WINEPREFIX`, which clears stale
   display state after sleep.
3. It starts the launcher with `--workdir C:\MuTheMatrix`.
4. It watches the launcher for 4 seconds, so a launcher that dies immediately is reported.

The app never runs a global `wineserver -k`, never logs in and never reads the Keychain.

## Errors

Every failure opens a dialog with a plain-language title, the reason, the log path, and the buttons
**Settings…**, **Open Log** and **Quit**. If CrossOver is missing, the dialog adds **Get CrossOver**.
These conditions are checked before anything is changed:

| Code | Title | Condition |
|---|---|---|
| 10 | CrossOver is not installed | `$CX_ROOT/bin/wine` or `wineserver` missing (default `/Applications/CrossOver.app/...`) |
| 11 | The CrossOver bottle was not found | no `Bottles/NAME/cxbottle.conf` |
| 12 | The bottle is not a 32-bit bottle | `WineArch` is not `win32` (64-bit bottles fail with the Rosetta GDT error) |
| 13 | Mu The Matrix is not installed in this bottle | no `C:\MuTheMatrix\MuTheMatrix.exe` |
| 14 | Mu The Matrix is already running | the game or launcher runs in any bottle |
| 15 | The fast x87 runtime is missing | fast x87 on, but the folder or validated cache is missing |
| 16 | This resolution is not available | no `mu-modes.txt`, or the mode is not in it |
| 17 | The resolution could not be saved | writing `LauncherOption.if` failed |
| 20 | The launcher stopped right away | the launcher exited with a non-zero status within the watch time |
| 2 | Could not be started | invalid setting or internal error |

## Logs

The logs are in `~/Library/Logs/MuTheMatrix/` and are visible in Console.app:
- `app.log`: app events, settings changes and the full preflight and start output. It is rotated to
  `app.log.1` at 512 KiB.
- `wine-BOTTLE.log`: the launcher's and game's Wine output. It is rewritten on each start of that
  bottle.

Your existing `play-mu.sh` logs (`~/Library/Logs/MuTheMatrix*.log`) are left alone.

## Command line and dry run

`Contents/MacOS/MuTheMatrix` also runs without a window. These options read the same settings:

```sh
APP="mac-play/bundle/build/Mu The Matrix.app/Contents/MacOS/MuTheMatrix"
"$APP" --print-settings   # effective settings, settings file and log directory
"$APP" --check            # preflight only; exit code as in the table above
"$APP" --dry-run          # preflight plus every planned action (MU-PLAN lines); changes nothing
"$APP" --version
```

The environment variables `MU_SETTINGS_FILE`, `MU_LOG_DIR`, `CX_ROOT`, `MUKIT_BOTTLES_DIR` and
`MU_LAUNCH_SCRIPT` override the file locations, which the tests use. `mu-launch.sh` also runs on its
own from a checkout, with the settings in `MU_BOTTLE`, `MU_FAST_X87`, `MU_TIMEWALKER_DIR` and
`MU_RESOLUTION` (see its header). It also has the options `--list-bottles` and `--list-modes`, which
the settings window uses.

## Tests

`tests/test-bundle.sh` runs as part of `make test`. Its first part runs on macOS and Linux. It uses a
synthetic bottle tree, a stub CrossOver whose `wine` and `wineserver` only record their arguments, and
a stub `pgrep`, so a running game cannot affect the results. It covers:
- every preflight error and its code;
- the bottle and mode listings;
- a dry run that leaves the bottle tree byte-identical and starts nothing;
- a stubbed start, which checks the scoped `wineserver -k`, the exact launcher arguments, the
  `LauncherOption.if` bytes and their backup, the fast-x87 routing, the early-exit error and the
  refusal while running.

The second part runs on macOS with `swiftc`, and `MU_BUNDLE_SKIP_BUILD=1` skips it. It builds the
app and checks:
- the bundle layout, `plutil -lint`, the `Info.plist` keys and the absence of unexpanded template
  fields;
- that the copied resources are identical to their sources;
- the ad-hoc signature (`codesign --verify --strict`);
- the icon's ten renditions, including 1024 px;
- the app's `--print-settings`, `--dry-run` and `--check` with a settings plist, the app log, and the
  fallback for a corrupt plist.

`tests/test_mac_bundle.py` checks the publication boundary: text sources only, and no personal paths
or credentials.

## Validation and limits

The test results and the live check are recorded in `docs/research/mac-crossover-32bit.md`
(MAC-BUNDLE-001). Known limits:
- The app is ad-hoc signed and not notarized.
- It is built for the host architecture only.
- The 4-second watch cannot detect a launcher that fails later; check `wine-BOTTLE.log` in that case.
- The resolution setting relies on the bottle's mscoree mode proxy, which makes the launcher's list
  match `mu-modes.txt`. In a bottle without the proxy, `DevModeIndex` refers to the launcher's own
  list.
