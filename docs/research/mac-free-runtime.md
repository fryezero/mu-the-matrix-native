# Playing on a Mac without CrossOver: a free Wine runtime (MAC-FREE-001)

**Verdict.** The game runs on a Mac without CrossOver, with free (LGPL) Wine, at CrossOver speed. The runtime
must be CodeWeavers' open-source Wine, the code under CrossOver. Upstream WineHQ builds cannot run the game:
they only run 64-bit (wow64) prefixes, and in those the protected client stops during startup. CodeWeavers' Wine
can run a 32-bit prefix in wow64 mode, the configuration that works in CrossOver.

**Chosen runtime.** CrossOver 26.3.0's Wine, built from CodeWeavers' published sources by
`mac-play/installer/packaging/build-wine.sh`. It matches CrossOver 26.3 in fps, and with rosetta-timewalker's
fast x87 it reaches the game's 25 fps cap in the Tormenta boss area. Nobody publishes a build of it yet, so the
owner has to host the archive (132 MB). Until then the installer uses a public fallback: Sikarugir's build of
CrossOver 24.0.7's Wine. It works end to end but is about 20% slower, and fast x87 does not work with it.

Environment for every result below: macOS 27.0.1 (26A434), Apple M5, Rosetta 2, 1800x1169 main screen. The
client is the pinned `main.exe` `3cf91f3c…5527a` with launcher `MuTheMatrix.exe` `c32e99ee…bc3e`. Test prefixes
are under `~/Library/Application Support/MuTheMatrixFree/`. The CrossOver bottles `MuMatrix32` and `MuMatrixKit`
were not changed; `MuMatrixKit`'s client folder was only read, as the copy source.

## Candidates

| Runtime | Version | 32-bit prefix | Result |
|---|---|---|---|
| WineHQ wine-stable (Gcenx `macOS_Wine_builds` 11.0_1) | Wine 11.0, wow64 build | refused: `WINEARCH is set to 'win32' but this is not supported in wow64 mode` | 64-bit prefix, `main.exe` started directly: 100% CPU in a loop of repeated access violations in the packed startup code. It never reaches the launcher handshake. |
| WineHQ wine-devel (Gcenx 11.18) | Wine 11.18 | refused, same message | 64-bit prefix: the client's protection shows "WinLicense: An internal exception occured (Address: 0x7bf21135)". |
| Sikarugir engine `WS12WineSikarugir11.0_1` | Wine 11.0 (Sikarugir) | not supported (no 32-bit-prefix code in `ntdll.so`) | not run further |
| Sikarugir engine `WS12WineCX24.0.7_7` | CrossOver 24.0.7 source, Wine 9.0 base | **yes** (method below) | full chain works; 14.6 fps / 69 ms of work in the reference scene |
| CrossOver 26.3.0 sources, self-built | Wine 11.0 + CrossOver patches | **yes** | full chain works; 18.1 fps / 55 ms; with fast x87 25.0 fps / 34 ms |
| CrossOver 26.3.0 (paid, reference) | 26.3.0.39832 | yes (`cxbottle`) | 18.3 fps / 55 ms in the same prefix |

Only the start-up behaviour was observed: "runs past the protection" versus "stops". No protection or anti-cheat
code was analysed (no tracing of `IGC.dll`, `RGS.dll` or the packer). For a 64-bit-only Wine, the earlier CrossOver
finding (64-bit prefixes fail, `mac-crossover-32bit.md`) points to the same cause; this task did not investigate
it further.

### The 32-bit prefix in wow64 mode

All these runtimes are wow64 builds: an x86_64 loader with i386 PE DLLs, and no 32-bit Unix part. CodeWeavers'
`ntdll.so` contains a "Using a 32-bit prefix in Wow64 mode" path, which upstream lacks. The loader still refuses
`WINEARCH=win32`, so the prefix is created another way. The wineserver is started first with `WINEARCH=win32`
(`WINEARCH=win32 WINEPREFIX=P wineserver -p 5`); the server then writes `#arch=win32` registries. After that,
`wine wineboot -i` runs without the variable. The prefix has no `syswow64`, and every later process logs "Using
a 32-bit prefix in Wow64 mode". The game's protection then behaves as in the CrossOver 32-bit bottle: `main.exe`
started directly says `Unable to connect to localhost:55232`, waiting for the launcher.

A side effect, seen with both CodeWeavers runtimes: in such a prefix, the service processes (`services.exe`,
`svchost`, `winedevice`) do not exit after the last program, so `wineserver -w` never returns. The installer waits
at most 20 s, then stops the prefix's wineserver with `-k`, which saves the registry.

## Building CrossOver 26.3's Wine (`packaging/build-wine.sh`)

Sources: `crossover-sources-26.3.0.tar.gz` from media.codeweavers.com (SHA-256 `ac99c8ca…6872`); only
`sources/wine` is used. The build runs on the M5 under `arch -x86_64` with Apple clang (`-arch x86_64`), Homebrew
`bison` 3.x and `mingw-w64` (GCC 16) for the PE parts. The x86_64 freetype/gnutls libraries come from Sikarugir's
wrapper template, headers from Homebrew. Configure options: `--enable-archs=i386,x86_64` without
X11/Vulkan/GStreamer/cups and the like; the full list is in the script. A full build takes about 25 minutes.
Problems found, and their fixes (all in the script):

1. `configure` reads library sonames from `otool -L`. The current otool prints extra fields, so
   `SONAME_LIBFREETYPE` became the whole output line, and FreeType/GnuTLS would never load. The script pins
   `libfreetype.6.dylib` and `libgnutls.30.dylib` in `include/config.h`.
2. CodeWeavers' `win32u/vulkan.c` needs `SONAME_LIBVULKAN` even without Vulkan. The script defines it.
3. The build tool `sfnt2fon` links FreeType by its leaf name. `DYLD_*` variables do not survive `make`
   (SIP strips them), so the libraries are symlinked into the build directory.
4. Upstream configure builds `wineboot`, `services`, `rpcss`, `plugplay`, `conhost`, … for the host
   architecture only. A 32-bit prefix needs their i386 builds: without them `wineboot` fails with `c0000135`
   in a fresh prefix. The script sets `enable_wineboot=yes` and the same for the other eight.
5. `wineserver` and `winebus.so` link `libinotify.dylib` by leaf name. The packaging step changes it to
   `@rpath/libinotify.0.dylib` and re-signs ad hoc.

The archive `winecx-26.3.0-mu1.tar.xz` (131.7 MB; 685 MB unpacked) holds `wine/{bin,lib,share}`, the dylibs,
the unpacked wine-gecko 2.47.4 x86 (for the launcher's embedded page), `.mu-runtime`, `SOURCES.txt` and
`COPYING.LIB`. The build used for the measurements had SHA-256 `c50cb614…6599`. The archive itself is not in the
repository.

## Fast x87 with the free runtime

rosetta-timewalker (MIT, pinned `ab1a6a03`; its x87 translator is based on rosettax87_jit, MIT) works with the
CrossOver 26.3 build. It does not need CrossOver's `run-crossover.sh`: every Wine process is started through the
authored `mac-play/x87-main-only-wrapper.c` (set as `WINELOADER`), with `TIMEWALKER_X87_REAL_LOADER` pointing to
the inner loader `wine/lib/wine/x86_64-unix/wine`. The other settings are
`TIMEWALKER_X87_RUNTIME_LOADER=runtime_loader`, `DYLD_INSERT_LIBRARIES=libtimewalker.dylib` and the four
`TIMEWALKER_CROSSOVER_*` loader/wineserver variables. Without the `TIMEWALKER_CROSSOVER_*` variables, the
translator is not applied. x87 benchmark (`fpbench`, 16.4 M transforms):

| | plain Rosetta | fast x87 |
|---|---|---|
| CrossOver 26.3 | 2.4 Mverts/s | 262 Mverts/s |
| CrossOver 26.3 Wine, self-built | 2.6 Mverts/s | 290–305 Mverts/s |
| CrossOver 24.0.7 engine (Sikarugir) | 1.0 Mverts/s | not applied (the engine re-executes a separate `wine-preloader`) |

The installer copies three binaries (`libtimewalker.dylib`, `runtime_loader`, `libRuntimeRosettax87`, collected
by `packaging/package-fast-x87.sh`) and builds the wrapper. The app bundles them when the owner builds it with
`EMBED_FAST_X87=…`. Fast x87 depends on undocumented Rosetta internals: a macOS update can stop it from working.
Players can then turn it off in the app.

## In-game measurements

All runs used the same scene: character Nighty at Tormenta Island 135,10 on MTM-1 (a busy PvP boss area), MU
Helper on (middle click), mugl v7.5 with mask 44916143, 1722x1076 window. Each run logged in with
`native/scratch/free/mu-free-login.sh`, then took mugl's own fps/work counters over 30 s. Every run held the
shared game lock and lasted under 3 minutes. Background load came from other agents. "Work" is the frame time
without the game's sleep; the game caps itself at 25 fps.

| Run | Runtime / prefix | fps | work | load avg |
|---|---|---|---|---|
| A | CX24 engine, `cx24w32` | 14.5 | 69.2 ms | 3.6 |
| B | CX24 engine, `cx24w32` (repeat) | 14.6 | 68.7 ms | 4.2 |
| C | CrossOver 26.3, `cxref` (clone of `cx24w32`) | 18.3 | 54.6 ms | 2.6 |
| D | CrossOver 26.3 Wine self-built, `cx26w32` (clone) | 18.1 | 55.4 ms | 4.0 |
| E | same + fast x87 | 25.0 | 33.6 ms | 2.7 |
| F | rehearsal 1 (official installer, CX24, started through the app's `mu-launch.sh`) | 15.3 | 65.7 ms | 10.0 |
| G | rehearsal 2 (CX26 archive + fast x87 through the app) | 25.0 | 35.3 ms | 4.6 |

The earlier MuMatrix32 figure (CrossOver + fast x87 + v7.5, MAC-PERF-009) was 25.0 fps at 33–35 ms of work in
this scene, so E and G match CrossOver's best setup. The scene was busy in all runs and other players' activity
changes the numbers; the A/B pairs are close in time. Runs A–E were started from zsh with `&`, which runs the
game at nice +5 (zsh `BG_NICE`); C ran the same way, so the comparison holds. Generated launchers now set
`setopt NO_BG_NICE` (point raised by MAC-PERF-010). The time from launcher start to in-world was 81–94 s in all
runs. It covers the launcher start, GAME START, the client start and the login script's fixed waits.

## The installer and its timing

`mac-play/installer/setup-mu-mac.sh` now defaults to `--runtime free` (CrossOver remains `--runtime crossover`).
`Mu The Matrix.app` bundles it and runs it from an Install window. Steps: runtime (pinned downloads), winetricks
20260125 (pinned), 32-bit prefix, registry, .NET 4.8 (winetricks; Microsoft's installers are downloaded from
Microsoft), Windows version, game, launcher config, skin, `C:\mutools`, `LauncherOption.if`, DLLs, fast x87,
verify.

**The game.** The server's download page (`webx.muthematrix.com/downloads`) links the official installer at
`https://dl.muthematrix.com/MuTheMatrix-21.1.2.12.exe`: 2,183,770,564 bytes, `Last-Modified` 2026-07-12, SHA-256
on 2026-10-18 `6594cf25…c8c2`. Mirrors: MediaFire, Google Drive, `www.muthematrix.com/descargas/`. The installer
(Actual Installer) runs silently with `/S` inside the prefix in about 2–3.5 minutes. It ignores `/D=` and installs
into `C:\Program Files\Glitch Games Network\Mu The Matrix`, which the setup moves to `C:\MuTheMatrix`. The
installed `main.exe` and `MuTheMatrix.exe` match the pinned identities. After a successful install the setup deletes
the downloaded installer (added after rehearsal 1, where the installed folder was 6.5 GB including the 2.3 GB of
downloads).

**Rehearsal 1, as a new player** (2026-10-18 01:30–02:16). This run used the app's headless `--install`, which
is the code path of the Install window, with a fresh `MUKIT_FREE_HOME` and a fresh winetricks cache. The
environment was minimal: `PATH=/usr/bin:/bin:/usr/sbin:/sbin`, no Homebrew, no CrossOver tools. The runtime was
the default CX24 download; mugl v7.5 and the mscoree proxy were bundled in the app.

| Step | Time |
|---|---|
| runtime download (172 + 96 MB) and unpack | 1 min 3 s |
| winetricks download | 1 s |
| 32-bit prefix | 14 s |
| registry | 21 s |
| .NET 4.0 + 4.8 (download 120 MB from Microsoft, install) | 4 min 8 s |
| Windows version, registry re-check | 26 s |
| official installer download (2.18 GB) | 35 min 22 s |
| official installer, silent | 2 min 1 s |
| move, configuration, DLLs, verify | 1 min 9 s |
| **total** | **44 min 50 s** (exit 0; verify 32 PASS, 2 WARN for the optional autologin helpers, 0 FAIL) |

Without the game download, setup takes about 9.5 minutes; the download time depends on the player's connection
and the server. The first start through the app's launch script reached the world 94 s after the launcher
started.

**Rehearsal 2, the recommended setup**: the app with the CX26 archive (through `MUKIT_RT_ARCHIVE_URL`), bundled
fast x87 and DLLs, and an existing game folder. 4 min 4 s, verify 0 FAIL, then in world at 25.0 fps (run G).
**Install window**: driven by the app's test hook `MU_AUTOTEST_INSTALL=1`, the same code path as the Install
button. Install from a folder took 5 min 12 s; the window showed the step progress, finished with "Done. Mu The
Matrix is installed.", and the settings window switched to "Installed / Repair…". Window screenshots were checked
and kept local.

## Gatekeeper

The app is ad-hoc signed, not notarized. A copy with a quarantine flag (as after a browser download) is rejected
by `spctl`. Opening it shows, on macOS 27: **"“Mu The Matrix.app” Not Opened. Apple could not verify “Mu The
Matrix.app” is free of malware that may harm your Mac or compromise your privacy."** with **Move to Trash** and
**Done**. Since macOS 15 the way through is: Done, then System Settings > Privacy & Security, scroll to
"Security", **Open Anyway** next to the message about Mu The Matrix.app, confirm with the password or Touch ID,
then **Open Anyway** in the next dialog. In this session the dialog and the Privacy & Security pane were
observed, but the buttons could not be clicked: no accessibility access for automation. The Open Anyway clicks
are therefore not verified here. The alternative was performed and works: `xattr -dr com.apple.quarantine
"/Applications/Mu The Matrix.app"`, after which the app opens normally. A launch attempted while the Gatekeeper
dialog was still open stayed blocked in `_dyld_start` until the dialog was dismissed. Binaries the installer
copies out of the app (fast x87) have their quarantine flag removed, and downloads made with `curl` carry none.
A seamless first start would need a paid Apple Developer ID, a Developer ID signature and notarization. That is
the owner's decision.

## Licenses (what may be redistributed)

| Part | License | Redistribution |
|---|---|---|
| Wine (CrossOver sources 24.0.7 and 26.3.0) | LGPL-2.1-or-later | allowed, with the corresponding source offered: CodeWeavers publishes it; the archive carries `SOURCES.txt` and `COPYING.LIB` |
| wine-gecko 2.47.4 | MPL-2.0 | allowed |
| freetype, gnutls, nettle, gmp, libpng, zlib, … (Sikarugir template dylibs) | FTL/GPL-2.0, LGPL, zlib, … | allowed with notices; sources: `Sikarugir-App/Sikarugir-foss-sources` |
| winetricks | LGPL-2.1-or-later | downloaded by the installer from the release tag |
| rosetta-timewalker, rosettax87_jit | MIT | allowed; licenses copied next to the binaries |
| .NET Framework 4.0/4.8 | Microsoft redistributable terms | not bundled; winetricks downloads it from Microsoft on the player's Mac |
| mugl, mscoree proxy (authored) | MIT (repository) | public builds yes; a private hotpatch build contains client-derived bytes (owner's decision; never committed) |
| game client | owner's | from the owner's official download |

## Limits and open points

- The CX26 archive needs hosting (a public repository release or the game's own download server), with its URL
  and SHA-256 set in `lib/mukit.sh`. Until then players get CX24 at about 15 fps in the busy reference scene and
  25 fps in quiet ones.
- One Mac, one macOS version (27.0.1), one screen size. Apple has said that macOS 27 is the last release with
  full Rosetta 2; later releases keep only a subset aimed at older games. The whole approach, CrossOver
  included, depends on it.
- The Gatekeeper "Open Anyway" clicks were not performed (see above).
- `muinput.exe`/`clickstart.exe` (autologin helpers) are not installed for players; verify shows them as WARN.
- The prefix's service processes keep running until the launcher's next start resets the prefix. They are idle.
