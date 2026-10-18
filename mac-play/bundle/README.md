# Mu The Matrix.app

`mac-play/bundle/` (MAC-BUNDLE-001, MAC-FREE-001) builds a double-clickable macOS app that installs and starts
the original launcher, `MuTheMatrix.exe`. **By default it needs no CrossOver:** it bundles the
[installer](../installer/README.md) and runs it with the free Wine runtime from an Install window, then starts
the game from `~/Library/Application Support/MuTheMatrix/prefix`. A CrossOver bottle (made by the installer's
`--runtime crossover` or by hand, with `C:\MuTheMatrix` and optionally `C:\mutools\mu-modes.txt`) stays
selectable as the legacy runtime. The app ships no game files. Non-technical players: see
[`../PLAYER-GUIDE.md`](../PLAYER-GUIDE.md).

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

They end up in `Info.plist` (`MUDefaultRuntime`, `MUDefaultBottle`, `MUDefaultFastX87`, `MUDefaultTimewalkerDir`).
Without them, the app defaults to the free runtime (`DEFAULT_RUNTIME=free`; `crossover` for the legacy path),
bottle `MuMatrixKit` for the CrossOver runtime, fast x87 on for the free runtime (used when installed) and off for
CrossOver, and the timewalker set to Auto.

### A build for players (owner)

The installer needs DLLs for good speed, and players cannot build them. The server owner bundles them at build time;
they go to `Contents/Resources/dlls` and `Contents/Resources/fast-x87` and the Install window passes them to the
installer (`--mugl-dll`, `--mscoree-dll`, `--fast-x87-dir`). Build the players' app with `player-app`:

```sh
make player-app EMBED_MUGL=/path/to/mugl-v77.dll EMBED_MSCOREE=/path/to/mscoree.dll \
    EMBED_FAST_X87=/path/to/fast-x87     # from ../installer/packaging/package-fast-x87.sh
# same as: make -C mac-play/bundle player-app EMBED_...
```

`player-app` refuses to build unless all three are given: both DLLs must exist and start with `MZ`, and the fast
x87 folder must hold `libtimewalker.dylib`, `runtime_loader` and `libRuntimeRosettax87`. After the build it runs
the app's `--check-bundle`. A plain `make` (or `make mac-bundle`) is a development build and says so: without the
DLLs, a player's Mac (no MinGW) installs a game that runs at about 4 fps and whose final check fails. If such an
app is run anyway, the Install window warns before installing ("This copy of Mu The Matrix is incomplete", with
**Cancel** / **Install Anyway**) and, after the failed check, says that the app is incomplete instead of showing a
generic failure.

A private mugl build contains client-derived bytes: distributing it to players is the owner's decision, and it
must never be committed. The mscoree proxy and the public mugl are authored sources (MIT); the timewalker files
are MIT (their licenses are copied along). `x87-main-only-wrapper` is compiled from `../x87-main-only-wrapper.c`
during the build. Without `EMBED_*` the app installs without DLLs (low fps) unless the installer finds MinGW
(a development machine started from Terminal).

To hand the app to players, zip it so the bundle survives the download, and publish the zip:

```sh
ditto -c -k --keepParent "mac-play/bundle/build/Mu The Matrix.app" "Mu The Matrix.zip"
```

The players' steps (including allowing the unsigned app once) are in `../PLAYER-GUIDE.md`.

## Use

Double-click **Mu The Matrix**. On the first run with the free runtime, the Install window opens in front of the
settings window: choose "Download the game from the official site" or "Use a Mu The Matrix folder I already
have…", press **Install** and watch the steps (about 10 minutes plus the 2.2 GB game download, 45 minutes in total in the recorded test; the log is in
`~/Library/Logs/MuTheMatrix/app.log`). Then press **Play**.

The Install window, in more detail (MAC-APP-002):
- **Rosetta 2.** Before the installer starts, the app checks for Rosetta 2 (`arch -x86_64 /usr/bin/true`). If it is
  missing, it explains what Rosetta is and offers to install it: `softwareupdate --install-rosetta --agree-to-license`
  run through the standard macOS administrator prompt (`osascript … with administrator privileges`). If the player
  declines or the install fails, the window shows the Terminal command instead. The installer's own Rosetta error
  leads to the same offer.
- **Progress.** Step lines read "Step 7 of 14: game files". The app runs the installer with `MUKIT_PROGRESS=lines`,
  so downloads report `MU-PROGRESS BYTES TOTAL NAME` once a second; the window shows the size so far, the total, the
  speed (average of the last 20 s) and the time left, and the bar moves within the step. The window title and the
  Dock icon show the overall percentage. The Mac does not idle-sleep while the installer runs.
- **Cancel.** The installer runs in its own process group (`posix_spawn` with `POSIX_SPAWN_SETPGROUP`). **Cancel >
  Stop**, closing the window or quitting the app sends SIGTERM to the whole group, waits up to 10 s
  (`MU_CANCEL_GRACE`), sends SIGKILL to what is left, then runs `setup-mu-mac.sh --runtime free --stop`: it stops
  this prefix's wineserver (`wineserver -k` with an explicit `WINEPREFIX`; Wine's server leaves the process group)
  and removes the setup lock. Partial downloads are kept, so **Try Again** continues them; no restart is needed.
- **Failures** show the installer's last `Error:` line instead of an exit status. Later double-clicks run a preflight check, start the launcher and quit the app. The
launcher and game keep running. To get the settings window back, hold **⌥ Option** while opening
the app. It also opens when "Start the game right away" is off, and from the error dialog.

| Setting | Effect |
|---|---|
| Runtime | **Free Wine runtime** (default) or **CrossOver bottle (legacy)**. With the free runtime the Game row shows whether it is installed and offers **Install…** / **Repair…** (rerunning the installer skips finished steps). |
| Bottle | CrossOver runtime only: any CrossOver bottle. The list marks bottles that are not 32-bit or have no `C:\MuTheMatrix`. |
| Resolution | "Keep launcher setting" (default) changes nothing. A mode from the bottle's `C:\mutools\mu-modes.txt` sets `DevModeIndex` in `C:\MuTheMatrix\LauncherOption.if` before each start, in the launcher's own byte format, keeping `WindowMode` and `ID`. The first change saves the original as `LauncherOption.if.mu-app-backup`. With the public batching-only mugl, the kit caps the index at 2 (see the kit README). |
| Fast x87 | Free runtime: on (default) uses the installed translator in `fast-x87/` for `main.exe` when the runtime has the inner loader (CrossOver 26.3 build), otherwise plain Rosetta with a note. CrossOver: off = plain `wine`; on = `main.exe` runs through rosetta-timewalker with `TIMEWALKER_X87_ONLY=main.exe`; the .NET launcher stays on the plain loader. |
| Timewalker | With fast x87 on: a built rosetta-timewalker folder (`scripts/run-crossover.sh`, `build/libtimewalker.dylib`), as with `play-mu.sh` `MU_TIMEWALKER_DIR`. **Auto** uses the validated cache from `../install-fast-x87.sh` (checked with `fast_x87_ready` from `../fast-x87.sh`). |
| FPS counter | Shows or hides mugl's in-game FPS counter: writes `C:\mutools\mugl-fps.txt` of the selected prefix or bottle at once (`mu-launch.sh --fps-counter on\|off`), so it also works while the game runs. The checkbox mirrors the file. Disabled until the game is installed. Opening the app while the game runs shows this window, so the counter can be changed during play. |
| Start right away | Off: the window opens on every start. |

**Mu The Matrix > Use Windows Layer File…** (or the checkbox in the Install window) installs a Wine runtime archive the
player already has, such as the CrossOver 26.3 build (`winecx-26.3.0-mu1.tar.xz`) before it has a public download. The
installer runs with `--runtime-archive FILE`; on an installed game only the runtime step does work. A file whose SHA-256
differs from `RuntimeFile.testedSHA256` gets a warning first. Later repairs without a file keep the installed archive runtime.

The settings are stored as an XML plist at `~/Library/Application Support/MuTheMatrix/Launcher.plist`,
with the keys `Runtime` (string `free` or `crossover`), `Bottle` (string), `FastX87` (bool), `TimewalkerDir` (string, empty = Auto), `Resolution`
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
| 13 | Mu The Matrix is not installed in this bottle ("… is not installed yet" with the free runtime) | no `C:\MuTheMatrix\MuTheMatrix.exe` |
| 14 | Mu The Matrix is already running | the game or launcher runs in any bottle |
| 15 | The fast x87 runtime is missing | fast x87 on, but the folder or validated cache is missing |
| 16 | This resolution is not available | no `mu-modes.txt`, or the mode is not in it |
| 17 | The resolution could not be saved | writing `LauncherOption.if` failed |
| 20 | The launcher stopped right away | the launcher exited with a non-zero status within the watch time |
| 30 | Mu The Matrix is not installed yet | free runtime: no runtime in `runtime/current` (the dialog offers **Install…**) |
| 31 | The game folder is missing or damaged | free runtime: the prefix is missing or not 32-bit (`#arch=win32`) |
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
"$APP" --status           # free runtime: runtime / prefix / game installed?
"$APP" --install-dry-run  # the installer's plan (download the official game); changes nothing
"$APP" --install [DIR]    # install without a window (what the Install window runs); Ctrl-C cancels like Cancel
"$APP" --install --runtime-archive FILE [DIR]  # same, with a Wine runtime file you already have
"$APP" --check-bundle     # exit 0 when mugl, the mscoree proxy and fast x87 are bundled (a player build)
"$APP" --fps-counter [on|off]  # show / hide the in-game FPS counter (no argument: print the state)
"$APP" --rosetta-status   # exit 0 when Rosetta 2 is installed
"$APP" --install-rosetta  # install Rosetta 2 through the administrator prompt
"$APP" --version
```

The environment variables `MU_SETTINGS_FILE`, `MU_LOG_DIR`, `MUKIT_FREE_HOME`, `CX_ROOT`, `MUKIT_BOTTLES_DIR`,
`MU_LAUNCH_SCRIPT` and `MU_SETUP_SCRIPT` override the file locations, which the tests use. `MU_CANCEL_GRACE` sets the
seconds between SIGTERM and SIGKILL on a cancel (default 10); `MU_ROSETTA_CHECK` and `MU_ROSETTA_INSTALL` replace the
Rosetta check and install commands (shell commands; the tests use stand-ins). `mu-launch.sh` also runs on its
own from a checkout, with the settings in `MU_RUNTIME` (default free; `MU_BOTTLE` alone selects CrossOver), `MU_PREFIX`, `MU_BOTTLE`, `MU_FAST_X87`, `MU_TIMEWALKER_DIR` and
`MU_RESOLUTION` (see its header). It also has the options `--list-bottles` and `--list-modes`, which
the settings window uses.

## Tests

`tests/test-bundle.sh` runs as part of `make test`. Its first part runs on macOS and Linux. It uses a
synthetic bottle tree, a stub CrossOver whose `wine` and `wineserver` only record their arguments, and
a stub `pgrep`, so a running game cannot affect the results. It covers:
- every preflight error and its code, for both runtimes;
- the free runtime: status, a stubbed start (explicit `WINEPREFIX`, launcher started from the game folder, scoped
  `wineserver -k`), the fast-x87 fallback and the fast-x87 environment;
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
  fallback for a corrupt plist;
- `--check-bundle` on the development build (lists what is missing) and on a `make player-app` build with
  synthetic embeds; `player-app` refusing to build without them or with an incomplete fast x87 folder;
- `--rosetta-status` and `--install-rosetta` with a stubbed check and install (installed, declined, already there);
- Cancel with a fake long-running installer that starts children, one of which ignores SIGTERM: the installer leads
  its own process group, Ctrl-C stops all of them (at once, or by SIGKILL after the grace when the installer itself
  ignores SIGTERM), and the `--stop` clean-up runs.

`tests/test_mac_bundle.py` checks the publication boundary: text sources only, and no personal paths
or credentials.

## Validation and limits

The test results and the live check are recorded in `docs/research/mac-crossover-32bit.md`
(MAC-BUNDLE-001). Known limits:
- The app is ad-hoc signed and not notarized: players must allow it once (see `../PLAYER-GUIDE.md`). A seamless
  first start needs an Apple Developer ID and notarization (owner's decision).
- It is built for the host architecture only.
- The 4-second watch cannot detect a launcher that fails later; check `wine-BOTTLE.log` in that case.
- The resolution setting relies on the bottle's mscoree mode proxy, which makes the launcher's list
  match `mu-modes.txt`. In a bottle without the proxy, `DevModeIndex` refers to the launcher's own
  list.
