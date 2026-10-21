# One download for players: the disk image and a one-button first run (MAC-DMG-001)

**Result.** Players download one file, `Mu The Matrix.dmg` (about 130 MB), drag the app to Applications, open it,
click **Install** and play: the official launcher opens by itself when the installation has finished. Nothing in
the default path names Wine, a runtime, DLLs or patches. The app bundles the fast Wine runtime (CrossOver 26.3 build,
LGPL), so players download nothing but the game and Microsoft's .NET, and reach 25 fps without anything being
hosted. **The end-to-end install from the disk image has not been rehearsed yet** (the owner asked not to install
the game during this milestone); the disk image, the move to Applications and the first-run window were checked live
(see Verification).

## What changed

| Part | Before | Now |
|---|---|---|
| Download | `Mu The Matrix.zip` (2.3 MB) + the runtime from GitHub at install time | `Mu The Matrix.dmg` (about 130 MB, `make player-dmg`), runtime inside |
| Runtime | CX24 fallback (`MUKIT_RT_ARCHIVE_URL` empty), 17 fps in the busy reference scene | CX26 `winecx-26.3.0-mu1.tar.xz` bundled (`EMBED_RUNTIME`, SHA-256 `c50cb614…` pinned in `RuntimeFile`), installed with `--runtime-archive … --runtime-sha256 …` on every install and repair |
| Location | the app ran wherever it was opened | outside `/Applications` and `~/Applications` (disk image, Downloads, App Translocation) it offers to copy itself there, reopens, ejects the disk image |
| First window | settings window + "Install Mu The Matrix" window (source radio buttons, "Windows layer file" option, step list, log box) | one window: one sentence, **Install**, a small "Use a game folder I already have…" link |
| Progress | "Step 7 of 14: game files", per-step bar, log box | plain step names, one overall bar (time-weighted, download by bytes), size/speed/time left, Cancel |
| Failure | "The installation stopped: <installer error>" | a plain title and sentence, **Try Again**, **Show Details** (installer output, log folder) |
| End | "Done … close this window and press Play" | "Mu The Matrix is ready", the launcher starts by itself, the app quits |
| Menu | Settings…, Use Windows Layer File…, Open Log | About (with the runtime's license note), Settings…, Open Log, Hide, Quit; Edit menu |

Unchanged: later starts go straight to the launcher; ⌥ Option or **Settings…** shows the settings (FPS counter,
resolution, Repair…); opening the app while the game runs shows the settings; Cancel stops the installer's whole
process group; the Rosetta 2 offer; the headless `--install` and the other command-line modes.

## How it works

- **Bundled runtime.** `make player-app` refuses to build without `EMBED_RUNTIME`, checks its SHA-256 against
  `RuntimeFile.pinnedSHA256` (the Makefile reads name and hash from `Sources/Core.swift`), copies it to
  `Contents/Resources/runtime/winecx-26.3.0-mu1.tar.xz`, extracts its `COPYING.LIB` next to it (refusing an archive
  without one) and adds `licenses/wine-runtime-SOURCES.txt` as `SOURCES.txt` (the archive's own `SOURCES.txt` is a
  one-line stub from an earlier `build-wine.sh`; the note names the CrossOver 26.3.0 source archive and its hash,
  wine-gecko and the Sikarugir library sources). `--check-bundle` hashes the bundled runtime. `Installer.arguments`
  passes `--runtime-archive PATH --runtime-sha256 PIN`: the setup derives the runtime id `archive-c50cb6145767` from
  the pin without hashing, skips the step when that runtime is installed, and checks the hash before unpacking
  otherwise. A repair therefore never unpacks or downloads it again; an install made with the old zip (CX24) moves
  to the bundled runtime on the next Repair.
- **Move to Applications** (`AppMover`, `Sources/FirstRun.swift`). The app's real location comes from Security's
  `SecTranslocateIsTranslocatedURL` / `SecTranslocateCreateOriginalPathForURL` (looked up with `dlsym`; the path
  pattern `/AppTranslocation/` is the fallback). Outside the Applications folders it asks; the copy is `ditto`
  (keeps the ad-hoc signature), an older copy goes to the Trash, `com.apple.quarantine` is removed from the copy
  (the player approved the app already; a flagged copy would be translocated on every start, so the offer would
  loop), and the copy is opened with `NSWorkspace.openApplication` (`createsNewApplicationInstance`, the `MU_*` /
  `MUKIT_*` variables passed on). A disk image is ejected 3 s after the old copy quits (`hdiutil detach`). Found
  during testing: with no window open, `applicationShouldTerminateAfterLastWindowClosed` ended the app while
  `Process.waitUntilExit` spun the run loop during the copy; `AppMover.busy` now holds it open.
  `MU_APPLICATIONS_DIR` replaces the target folder (tests, rehearsals), `MU_SKIP_MOVE=1` disables the offer.
- **First-run window** (`InstallWindowController`). `applicationDidFinishLaunching`: the move offer first; then
  ⌥ Option → settings; game not installed → the install window alone; "start right away" off → settings; else start.
  The overall bar (`InstallProgress`) gives every installer step an estimated duration (`installStepInfo`: .NET
  240 s, the official installer 150 s, …) and the game download 2000 s scaled by the bytes received; the running step
  advances with elapsed time up to 90% of its estimate, and the bar never goes back. After success in install mode
  the window shows "Mu The Matrix is ready" for 1.2 s, then `onPlay` starts the launcher through the usual
  `mu-launch.sh --run` path (and the app quits). Repair mode (from Settings) ends with **Play** instead.
- **Disk image** (`dmg/make-dmg.sh`, `dmg/dmg-tool.swift`). Only built-in tools: `ditto`, `hdiutil` (UDRW HFS+ image,
  mounted `-nobrowse`, then `convert -format ULFO`), `tiffutil` (1x + 2x background), `xattr` (volume icon flag),
  `swiftc` for the helper. The background is drawn with AppKit at build time. The Finder layout is a `.DS_Store`
  written by `dmg-tool dsstore`: the "Bud1" buddy-allocator file with one B-tree leaf holding `bwsp` (window bounds,
  no toolbar/sidebar), `icvp` (icon view, 128 px icons, background type 2 with an Alias Manager record of
  `.background/background.tiff` that macOS itself creates with `FSNewAlias`, called through `dlsym` because the
  Swift headers no longer declare it), `vSrn`, `vstl`, and the `Iloc` positions of the app and the Applications
  link. Finder honoured it on the first mount (window size, background, positions; screenshot below). No Finder
  scripting is needed (asking Finder via AppleScript would need an Automation permission prompt).
- **Signing for notarization.** `SIGN_IDENTITY` re-signs the staged app inside out with `--options runtime
  --timestamp`: Mach-O files in `Resources` (the fast x87 helpers) with `dmg/helpers.entitlements`
  (`allow-dyld-environment-variables`, `disable-library-validation`, `allow-jit`, `allow-unsigned-executable-memory`),
  the app with `dmg/app.entitlements` (none). `NOTARY_PROFILE` notarizes the app (zip, `notarytool submit --wait`,
  `stapler staple`), builds the image, signs, notarizes and staples it, and runs `spctl --assess`. Wine itself is not
  signed by us: it is unpacked from the archive into Application Support without a download flag and never seen by
  Gatekeeper.

## Verification

- `mac-play/bundle/tests/test-bundle.sh`: 268 checks, all passing; new: the runtime embed (refusals: missing,
  wrong hash, no license; bundled name, license, sources note; `--check-bundle` hash check; install plan with the
  bundled runtime and no runtime download; a repair keeps the installed runtime), the first-run wiring and a jargon
  check of every player-facing string of the install window and the move offer, `--location` /
  `--move-to-applications` (signature kept, flag removed, older copy replaced), and `make-dmg.sh` (dry runs, argument
  checks, a real ad-hoc hardened image: format, volume name, contents, background reps, `.DS_Store` records, volume
  icon flag, hardened runtime and entitlements on the wrapper, `hdiutil verify`). `tests/test_mac_bundle.py` allows
  the new text file types and checks that no image, `.DS_Store` or archive is tracked.
- UI states were exercised with a stand-in installer (`MU_SETUP_SCRIPT`) and clicked through with System Events:
  welcome, progress, download progress, a failed download (Show Details), Cancel > Stop > Continue, success → start.

- Live checks with the real disk image (2026-10-21, macOS 27, Apple M5; scratch `MUKIT_FREE_HOME`, settings file and
  log folder through `open --env`, so the owner's install and settings were untouched):
  - Opened like a download (`com.apple.quarantine` `0083;…;Safari;…` on the image, mounted with `open`): Finder showed
    the laid-out window (background, arrow, both icons in place, volume icon). Opening the app from it showed macOS's
    **"Mu The Matrix.app" Not Opened** (only **Done** on a read-only volume).
  - With the user-approved bit set on the image's flag (`00c3`, standing in for **Open Anyway**), the app ran
    translocated from the disk image and offered **Move to Applications**; the copy (9 s for 130 MB) went to the test
    folder without the download flag, reopened from there, and the disk image was ejected.
  - The first-run window appeared alone (screenshot). In this run Install was also pressed before the owner's stop
    request arrived: the bundled runtime unpacked in 6 s (`archive-c50cb6145767`, no runtime download), and the steps
    up to "Installing components from Microsoft" ran with the plain progress view. The install was then stopped with
    Cancel > Stop (all processes ended, lock removed) and the scratch folder deleted. Not done: the game download and
    install, the automatic launcher start, the in-game fps check, and replacing the owner's `~/Applications` copy.

## Limits

- Notarization could not be run (no Apple Developer account here): the signed path is tested only ad hoc
  (`--sign -`) with the hardened runtime and the entitlements. Whether Apple's notary service objects to the
  unsigned Wine programs inside the bundled `.tar.xz` is unknown until the owner submits it; if it does, the
  fallback is to sign the runtime's Mach-O files before archiving (they are unpacked with their signatures).
- **Not yet rehearsed end to end:** a fresh install from the disk image through the game download to the automatic
  launcher start and in-world fps. The same installer path reached the world at 25 fps with this runtime in
  MAC-FREE-001; the new window code around it was exercised with a stand-in installer only.
- Without notarization, players still confirm the app once in System Settings > Privacy & Security (Open Anyway).
  In the rehearsal that approval was simulated by the user-approved bit of the download flag; the real Open Anyway
  click needs the owner's password and was not performed by an agent.
- The ~45-minute estimate in the first sentence is fixed; it assumes about 1 MB/s from `dl.muthematrix.com`.
- The progress bar's step durations are estimates from one Mac; on a much slower Mac the bar waits at 90% of a
  step longer.
- Rosetta 2 missing was tested with stand-ins only (the test Mac has it).
