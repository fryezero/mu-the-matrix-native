# Mu The Matrix.app

`mac-play/bundle/` (MAC-BUNDLE-001, MAC-FREE-001, MAC-DMG-001) builds a double-clickable macOS app that installs and
starts the original launcher, `MuTheMatrix.exe`, and the disk image players download (`Mu The Matrix.dmg`). **By
default it needs no CrossOver:** it bundles the [installer](../installer/README.md) and the Wine runtime, runs the
installer from a one-button install window, then starts the game from
`~/Library/Application Support/MuTheMatrix/prefix`. A CrossOver bottle (made by the installer's
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

Players cannot build the DLLs or the Wine runtime, so the server owner bundles them at build time. They go to
`Contents/Resources/dlls`, `Contents/Resources/fast-x87` and `Contents/Resources/runtime`, and the app passes them to
the installer (`--mugl-dll`, `--mscoree-dll`, `--fast-x87-dir`, `--runtime-archive` with `--runtime-sha256`). Build the
players' app with `player-app`, or straight to the disk image with `player-dmg`:

```sh
make player-dmg EMBED_MUGL=/path/to/mugl-v77.dll EMBED_MSCOREE=/path/to/mscoree.dll \
    EMBED_FAST_X87=/path/to/fast-x87 \
    EMBED_RUNTIME=/path/to/winecx-26.3.0-mu1.tar.xz    # DMG="/path/Mu The Matrix.dmg" to choose the output
# player-app: the same without the disk image; both also work as make -C mac-play/bundle ...
```

`player-app` refuses to build unless all four are given: both DLLs must exist and start with `MZ`, the fast x87
folder (from `../installer/packaging/package-fast-x87.sh`) must hold `libtimewalker.dylib`, `runtime_loader` and
`libRuntimeRosettax87`, and the runtime must be exactly the tested build: its name and SHA-256 are pinned in
`Sources/Core.swift` (`RuntimeFile`, `c50cb614…`; the Makefile reads them from there). The runtime archive's
`COPYING.LIB` (LGPL 2.1) is copied next to it, with `licenses/wine-runtime-SOURCES.txt` as `SOURCES.txt` (where the
corresponding sources are); the About panel points to them. After the build it runs the app's `--check-bundle`,
which also checks the runtime's hash. A plain `make` (or `make mac-bundle`) is a development build and says so:
without the DLLs a player's Mac installs a game that runs at about 4 fps and whose final check fails, and without
the runtime the installer downloads the slower fallback runtime. If such an app is run anyway, the install window
warns before installing ("This copy of Mu The Matrix is incomplete", **Cancel** / **Install Anyway**).

With the bundled runtime, every install and **Repair** uses it: nothing is downloaded for it, and an installed
runtime with the same hash (`runtime/archive-c50cb6145767`) is kept as it is. The app grows to about 135 MB (the
disk image is about 130 MB).

Use the v3 mscoree proxy (`mac-play/mumodes`, pinned in the installer README): besides the display-mode list it
fixes the launcher's windows on macOS (MAC-APP-004: its news panel no longer floats over the game, and minimize
sends the launcher to the Dock, from where a click restores it) and lets the launcher show the server's official
skin (MAC-APP-006: WIC stream fix). An app built with the v2 or v1 proxy still works with the default skin (the
installer keeps the official skin disabled then), and verify reports the proxy as a WARN.

A private mugl build contains client-derived bytes: distributing it to players is the owner's decision, and it
must never be committed. The mscoree proxy and the public mugl are authored sources (MIT); the timewalker files
are MIT (their licenses are copied along); the runtime is LGPL 2.1+ (see above). `x87-main-only-wrapper` is compiled
from `../x87-main-only-wrapper.c` during the build. Never commit the DLLs, the runtime archive or a disk image.

### The disk image (`make player-dmg`, `dmg/make-dmg.sh`)

`dmg/make-dmg.sh --app APP --out DMG` uses only tools that come with macOS and the Command Line Tools: it stages
the app (`ditto`) and a link to `/Applications`, draws the window background at build time (`dmg/dmg-tool.swift
background`, 660 x 400 points, 1x and 2x combined with `tiffutil`; no artwork is committed), creates a read-write
HFS+ image named "Mu The Matrix" (`hdiutil create`), mounts it without showing it, writes the Finder layout
(`dmg-tool dsstore`: a `.DS_Store` with icon view, window size, the background picture as an alias record made by
macOS itself, and the two icon positions), sets the app icon as the volume icon (`.VolumeIcon.icns` plus the
"custom icon" Finder flag), then converts the image to a compressed, read-only one (`ULFO`, LZFSE; `--format UDZO`
for zlib) and checks it with `hdiutil verify`. `--dry-run` prints the plan; `--no-layout` skips the window layout.

Signing and notarization (optional, needs a paid Apple Developer account):

```sh
xcrun notarytool store-credentials mu-notary --apple-id ... --team-id ...   # once; keeps the notary credentials in the Keychain
make player-dmg EMBED_...=... SIGN_IDENTITY="Developer ID Application: NAME (TEAMID)" NOTARY_PROFILE=mu-notary
```

With `SIGN_IDENTITY` the script re-signs the staged app inside out with the hardened runtime and a secure timestamp:
the Mach-O helpers in `Resources/fast-x87` with `dmg/helpers.entitlements` (`allow-dyld-environment-variables`: the
x87 wrapper is Wine's loader and must keep `DYLD_INSERT_LIBRARIES` for the processes it starts;
`disable-library-validation`: it loads libraries of other teams or unsigned ones; `allow-jit` and
`allow-unsigned-executable-memory`: Rosetta's x87 translation writes code at run time), then the app with
`dmg/app.entitlements` (no exceptions: the app only runs scripts and system tools; Wine and the helpers are separate
processes with their own signatures). The disk image is signed too. With `NOTARY_PROFILE` it submits the app (as a
zip) with `notarytool submit --wait`, staples the ticket to the app, builds the disk image, submits and staples that
too, and checks it with `spctl --assess`. **Notarization is what removes the "Open Anyway" step**: without it
(today, ad-hoc signed) players confirm the app once in System Settings > Privacy & Security. The Wine runtime inside
the app is a `.tar.xz` whose programs are unpacked into Application Support and run without a download flag, so
Gatekeeper does not check them; whether Apple's notary service inspects the archive's unsigned Wine binaries could
not be tested without an account. `--sign -` signs ad hoc with the same hardened runtime and entitlements, to test
them locally.

## Use

**First start (MAC-DMG-001).** A player opens the disk image, drags **Mu The Matrix** to Applications and opens it.
- **Move to Applications.** If the app runs from anywhere outside `/Applications` and `~/Applications` (the disk
  image, Downloads; a downloaded app then runs from a random read-only copy, "App Translocation", which the app
  recognises with Security's `SecTranslocate` functions), it first asks "Move Mu The Matrix to your Applications
  folder?". **Move to Applications** copies it (`ditto`, keeping the signature) to `/Applications`, or to
  `~/Applications` when `/Applications` is not writable, replaces an older copy (moved to the Trash), removes the
  download flag from the copy (the player already approved the app; a flagged copy would be translocated again on
  every start), opens the copy and quits; a disk image is ejected a few seconds later. From the disk image or a
  translocated copy the other button is **Quit**: nothing is installed from there. From another writable folder it
  is **Not Now**. `MU_APPLICATIONS_DIR` replaces the target folder (tests, rehearsals); `MU_SKIP_MOVE=1` turns the
  offer off (development builds started from `build/`).
- **One window.** If the game is not installed, the only window says "Mu The Matrix needs to download the game
  (about 2.2 GB) and set itself up. This takes about 45 minutes." with one **Install** button and a small "Use a
  game folder I already have…" link (copies that folder instead of downloading). No settings window opens behind it.
- **Rosetta 2.** Before the installer starts, the app checks for Rosetta 2 (`arch -x86_64 /usr/bin/true`). If it is
  missing, it explains what Rosetta is and offers to install it: `softwareupdate --install-rosetta --agree-to-license`
  run through the standard macOS administrator prompt (`osascript … with administrator privileges`). If the player
  declines or the install fails, the window says so and offers Try Again; Show Details has the Terminal command.
- **Progress.** One view: a plain step name ("Getting ready", "Installing components from Microsoft", "Downloading
  the game", "Installing the game", "Finishing", "Checking that everything works"; `installStepInfo` in
  `Sources/FirstRun.swift` maps the installer's `== N/M` steps), one overall bar (`InstallProgress`: finished steps
  count with their estimated time, the running one by elapsed time, the game download by bytes), the download's
  size, speed and time left (the installer runs with `MUKIT_PROGRESS=lines`, so downloads report
  `MU-PROGRESS BYTES TOTAL NAME` once a second), and **Cancel**. The window title and the Dock icon show the
  percentage. The Mac does not idle-sleep while the installer runs.
- **Cancel.** The installer runs in its own process group (`posix_spawn` with `POSIX_SPAWN_SETPGROUP`). **Cancel >
  Stop**, closing the window or quitting the app sends SIGTERM to the whole group, waits up to 10 s
  (`MU_CANCEL_GRACE`), sends SIGKILL to what is left, then runs `setup-mu-mac.sh --runtime free --stop`: it stops
  this prefix's wineserver (`wineserver -k` with an explicit `WINEPREFIX`; Wine's server leaves the process group)
  and removes the setup lock. Partial downloads are kept, so **Continue** goes on where it stopped.
- **Failures** show a plain message (not enough space, a download that did not finish, or a general one) with **Try
  Again** and **Show Details** (the installer's output and **Open Log Folder**).
- **Done.** "Mu The Matrix is ready", then the app starts the official launcher by itself and quits. Later starts
  run a preflight check, start the launcher and quit the app; the launcher and game keep running.

The settings window is not part of the first run. It opens from **Mu The Matrix > Settings…** (⌘,), when **⌥ Option**
is held while opening the app, when "Start the game right away" is off, from an error dialog, and when the app is
opened while the game runs (to change the FPS counter). Its **Repair…** button opens the same window in repair mode
(**Repair**, then **Play**).

| Setting | Effect |
|---|---|
| Runtime | **Free Wine runtime** (default) or **CrossOver bottle (legacy)**. With the free runtime the Game row shows whether it is installed and offers **Install…** / **Repair…** (rerunning the installer skips finished steps). |
| Bottle | CrossOver runtime only: any CrossOver bottle. The list marks bottles that are not 32-bit or have no `C:\MuTheMatrix`. |
| Resolution | "Keep launcher setting" (default) changes nothing. A mode from the bottle's `C:\mutools\mu-modes.txt` sets `DevModeIndex` in `C:\MuTheMatrix\LauncherOption.if` before each start, in the launcher's own byte format, keeping `WindowMode` and `ID`. The first change saves the original as `LauncherOption.if.mu-app-backup`. With the public batching-only mugl, the kit caps the index at 2 (see the kit README). |
| Fast x87 | Free runtime: on (default) uses the installed translator in `fast-x87/` for `main.exe` when the runtime has the inner loader (CrossOver 26.3 build), otherwise plain Rosetta with a note. CrossOver: off = plain `wine`; on = `main.exe` runs through rosetta-timewalker with `TIMEWALKER_X87_ONLY=main.exe`; the .NET launcher stays on the plain loader. |
| Timewalker | With fast x87 on: a built rosetta-timewalker folder (`scripts/run-crossover.sh`, `build/libtimewalker.dylib`), as with `play-mu.sh` `MU_TIMEWALKER_DIR`. **Auto** uses the validated cache from `../install-fast-x87.sh` (checked with `fast_x87_ready` from `../fast-x87.sh`). |
| FPS counter | Shows or hides mugl's in-game FPS counter: writes `C:\mutools\mugl-fps.txt` of the selected prefix or bottle at once (`mu-launch.sh --fps-counter on\|off`), so it also works while the game runs. The checkbox mirrors the file. Disabled until the game is installed. Opening the app while the game runs shows this window, so the counter can be changed during play. |
| Start right away | Off: the window opens on every start. |

Another Wine runtime archive can still be installed from the command line (`--install --runtime-archive FILE`); the
"Use Windows Layer File…" menu item and checkbox of earlier versions are gone, because the player build bundles the
runtime.

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
"$APP" --install [DIR]    # install without a window (what the install window runs); Ctrl-C cancels like Cancel
"$APP" --install --runtime-archive FILE [DIR]  # same, with another Wine runtime file instead of the bundled one
"$APP" --check-bundle     # exit 0 when mugl, the mscoree proxy, fast x87 and the pinned runtime are bundled
"$APP" --location         # where the app runs from (translocated?) and whether it is in an Applications folder
"$APP" --move-to-applications  # the copy step of "Move to Applications" (no dialog, no relaunch)
"$APP" --fps-counter [on|off]  # show / hide the in-game FPS counter (no argument: print the state)
"$APP" --rosetta-status   # exit 0 when Rosetta 2 is installed
"$APP" --install-rosetta  # install Rosetta 2 through the administrator prompt
"$APP" --version
```

The environment variables `MU_SETTINGS_FILE`, `MU_LOG_DIR`, `MUKIT_FREE_HOME`, `CX_ROOT`, `MUKIT_BOTTLES_DIR`,
`MU_LAUNCH_SCRIPT`, `MU_SETUP_SCRIPT` and `MU_APPLICATIONS_DIR` override the file locations, which the tests use
(`MU_RUNTIME_SHA256` replaces the runtime pin for the synthetic tests only). `MU_CANCEL_GRACE` sets the
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
  synthetic embeds (a synthetic runtime archive with the real layout); `player-app` refusing to build without them,
  with an incomplete fast x87 folder, with a runtime that is not the pinned build or without its `COPYING.LIB`; the
  bundled runtime, license and sources note; `--install-dry-run` installing the bundled runtime (no runtime download)
  and keeping an installed one on a repair;
- the first run's wiring (move offer first, the install window alone when the game is missing, the game started after
  the install, no "Use Windows Layer File") and every player-facing text of the install window and the move offer
  checked for technical words;
- `--location` and `--move-to-applications`: the copy keeps a valid signature, loses the download flag and replaces
  an older copy;
- `dmg/make-dmg.sh`: dry runs (plain, and Developer ID with notarization), argument checks, and a real disk image of
  the synthetic player app signed with `--sign -`: format ULFO, volume name, app, Applications link, the 1x/2x
  background, the `.DS_Store` records, the volume icon and its flag, hardened runtime on the app and the x87 wrapper
  with its entitlements, `hdiutil verify`;
- `--rosetta-status` and `--install-rosetta` with a stubbed check and install (installed, declined, already there);
- Cancel with a fake long-running installer that starts children, one of which ignores SIGTERM: the installer leads
  its own process group, Ctrl-C stops all of them (at once, or by SIGKILL after the grace when the installer itself
  ignores SIGTERM), and the `--stop` clean-up runs.

`tests/test_mac_bundle.py` checks the publication boundary: text sources only, and no personal paths
or credentials.

## Validation and limits

The test results and the live check are recorded in `docs/research/mac-crossover-32bit.md`
(MAC-BUNDLE-001). Known limits:
- The app is ad-hoc signed and not notarized: players must allow it once (see `../PLAYER-GUIDE.md`). A first start
  without that step needs an Apple Developer ID and notarization (`SIGN_IDENTITY`/`NOTARY_PROFILE`, owner's decision;
  the signed path is tested ad hoc with the hardened runtime, real notarization was not).
- It is built for the host architecture only.
- The 4-second watch cannot detect a launcher that fails later; check `wine-BOTTLE.log` in that case.
- The resolution setting relies on the bottle's mscoree mode proxy, which makes the launcher's list
  match `mu-modes.txt`. In a bottle without the proxy, `DevModeIndex` refers to the launcher's own
  list.
