# mu-mac-kit: play Mu The Matrix on an Apple Silicon Mac

Repository path: `mac-play/installer/` (MAC-KIT-001, issue #63). This kit rebuilds the working CrossOver setup from scratch in a new bottle. The reference is the owner's hand-built `MuMatrix32` bottle (32-bit, .NET 4.8 launcher, mugl OpenGL batching proxy, matching resolution lists for the launcher and the game).

**Status.** The owner's local copy of this kit was verified live on 2026-10-17 (CrossOver 26.3.0.39832, macOS 27, M-series, 1800x1169 screen): a bottle built by it logs in and runs in world at the same or better fps than `MuMatrix32`. See "Live validation" at the end; those results are the owner's report and were not rerun for publication. This repository version is adapted to run from a checkout (see "Adaptations for the repository" below). It was itself run live on 2026-10-17 in a throwaway bottle, for all three DLL paths, up to the server-select screen (see "Live validation of the repository version").

| File | Purpose |
|---|---|
| `setup-mu-mac.sh` | Idempotent, step-wise installer. Every step checks the bottle first and skips work that is already done. Has `--dry-run`. |
| `verify-mu-mac.sh` | Read-only health check. It only reads files: it never runs wine and never starts or stops anything. Prints PASS/WARN/FAIL/INFO per item and exits 1 on any FAIL. |
| `registry/mu-mac.reg` | All registry changes, as one reviewable REGEDIT4 file imported with `regedit /S`. |
| `play-mu.sh` | What the Desktop launcher runs: refuses a second instance, resets the bottle's idle wineserver, starts `MuTheMatrix.exe` (log `~/Library/Logs/MuTheMatrix-BOTTLE.log`). |
| `lib/mukit.sh` | Shared parsers (Wine `.reg`, `cxbottle.conf`, `LauncherOption.if`, mode lists), pinned hashes and protected bottle names. |
| `tests/test-mukit.sh` | Tests: parser units, `.reg`/expectation sync, shell syntax, and a synthetic-bottle integration test with stub CrossOver and synthetic DLLs (no wine, no game, temp dirs only). Runs on macOS and Linux; CI runs it on both. |

No game files are ever downloaded. You point `--game-dir` at your own client folder. The repo does not document an official installer URL, so the kit does not offer one.

## Requirements

- Apple Silicon Mac with Rosetta 2, and CrossOver 26.3 in `/Applications`. Tested: CrossOver 26.3.0.39832 on macOS 27.
- `brew install winetricks`. This also pulls in `cabextract` and `p7zip`. Winetricks downloads .NET 4.0 (dotNetFx40, ~50 MB) and 4.8 (~70 MB) from Microsoft unless they are already in its cache. On macOS, winetricks 20260125 uses `~/.cache/winetricks`, not `~/Library/Caches/winetricks`. The kit passes `W_CACHE` explicitly (`$W_CACHE`, else `$XDG_CACHE_HOME/winetricks`, else `~/.cache/winetricks`) and seeds the 4.8 installer there.
- Your Mu The Matrix client folder, for example a Windows install or another bottle's `Program Files (x86)/Glitch Games Network/Mu The Matrix`. It must contain `main.exe` and `MuTheMatrix.exe`.
- MinGW-w64 and `make` for the default `--dll-source build` (`brew install mingw-w64`), plus `python3` (the public mugl's `gen.py`). They are not needed for `--dll-source prebuilt`.
- Optional: `make mac-diagnostics` builds `mac-play/diagnostics/build/diagnostics/muinput.exe`, which the kit copies to `C:\mutools` for the autologin tools (`--helpers-dir`).

Where each input comes from:

| Input | Source |
|---|---|
| winetricks shims `cxwine`, `cxwineserver` | the repository's `mac-play/` (they require `CX_BOTTLE` and a matching `WINEPREFIX`, which the setup supplies) |
| mscoree display-mode proxy | built from `mac-play/mumodes` (`--dll-source build`), or your `mscoree.dll` in `--dll-dir` (pinned SHA-256) |
| mugl OpenGL proxy, default | built from the repository's public `mac-play/mugl` (batching only, no hotpatches, no display-mode hook) |
| mugl, `--mugl-build private` | the DLL you generated yourself: `python3 mac-play/hotpatch/generate.py` from your own client dump, then `make -C mac-play/hotpatch private` (`mac-play/hotpatch/README.md`) |
| mugl, `--dll-source prebuilt` | your own `mugl-v72.dll` / `mugl-v71.dll` / `mugl-v70.dll` in `--dll-dir` (pinned SHA-256; they are not in the repository) |
| .NET 4.8 installer | winetricks downloads it, or pass your copy with `--dotnet-installer` (SHA-256 checked) |
| Desktop launcher | `play-mu.sh` in this directory, so keep the checkout where it is, or rerun setup after moving it |

> **Distribution note:** the prebuilt `mugl-v7x.dll` files and a private hotpatch build contain hotpatch tables derived from the client's unpacked memory. They are for their owner's own use. Per `docs/evidence-policy.md` they must never be committed to the repository or uploaded as a CI artifact; this repository holds only their SHA-256 values. Without them, the default public build (batching only) still works.

## Step by step for a new player

1. Install CrossOver and winetricks. Open CrossOver once so it finishes its own setup.
2. Preview what will happen (this changes nothing):
   ```sh
   ./mac-play/installer/setup-mu-mac.sh --dry-run \
       --game-dir "/path/to/Mu The Matrix"
   ```
3. Run it for real. On a fresh bottle the owner's run took about 4 minutes when the .NET installers were already cached (plus compile time for the default build). The .NET step is about 3 min 15 s of that; bottle creation is about 10 s, and the 6 GB client copy is an instant APFS clone. A rerun with nothing to do takes about 2 s.
   ```sh
   ./mac-play/installer/setup-mu-mac.sh --game-dir "/path/to/Mu The Matrix" [--account YourID]
   # with DLLs you own:  ... --dll-source prebuilt --dll-dir /path/to/your/dlls
   ```
   The default bottle is `MuMatrixKit`; pick another name with `--bottle NAME`. Rerun the same command any time: completed steps are skipped, and the launcher-skin check runs again on every run in case a game update restored the skin.
4. Setup ends by running `verify-mu-mac.sh --bottle MuMatrixKit`. Fix any FAIL lines using the troubleshooting table below.
5. Double-click **"Play Mu The Matrix (MuMatrixKit).command"** on the Desktop. Wait for the launcher's server time, press GAME START and log in. Only one client can run at a time across all bottles: `play-mu.sh` refuses to start while `main.exe` or `MuTheMatrix.exe` runs anywhere. Logging in with an account kicks that account's session in any other bottle.
6. The resolution is chosen from your screen. To change it, use the launcher's Settings: the entries there match the game's list. Or rerun setup with `--mode-index N --reset-config`.

### Options

| Option | Effect |
|---|---|
| `--bottle NAME` | Target bottle. Default `MuMatrixKit`. `MuMatrix32`, `Windows10MU`, `Steam` and `MuMatrixRecovery` are always refused, as is any existing bottle without the kit's `.mukit/owner` marker. |
| `--game-dir PATH` | Client source. Copied with an APFS clone (`cp -c`), falling back to `ditto` across volumes. The 3 GB `.mu-recovery-transfer.tar` is dropped. |
| `--modes "WxH ..."`, `--mode-index N` | Contents of `C:\mutools\mu-modes.txt` and the `DevModeIndex`. The default ladder is `960x600 1024x640 1280x800 1600x1000 1728x1080 1920x1200`. The first three are always listed; larger modes are listed only if the window fits (width + 16, height + 89). A 1800x1169 screen gives the live list with index 4 = 1728x1080. |
| `--account ID` | Prefills `ID:` in `LauncherOption.if`. Passwords are never stored and the kit knows no account or Keychain item name. The repository's `mac-play/automation/mu-autologin.sh` takes the account and Keychain service from `MU_ACCOUNT` and `MU_KEYCHAIN_SERVICE`. |
| `--dll-source build` (default) / `prebuilt` | `build` compiles the mscoree proxy from `mac-play/mumodes` and the mugl proxy from `mac-play/mugl` (or, with `--mugl-build private`, installs your own `mac-play/hotpatch/build/private/opengl32.dll`), using `-O2 -msse2 -mfpmath=sse` (SSE is mandatory), in `mac-play/installer/build/` (ignored by git). `prebuilt` installs the pinned DLLs from `--dll-dir` and refuses any file whose SHA-256 differs. |
| `--dll-dir DIR` | Directory with `mugl-v72.dll`, `mugl-v71.dll`, `mugl-v70.dll`, `mscoree.dll` (env `MU_DLL_DIR`). Required with `prebuilt`. Only the selected `mugl-VERSION.dll` must be there: without `mscoree.dll` the kit builds the mscoree proxy from `mac-play/mumodes` (public source; needs MinGW), so a plain folder of mugl builds works. |
| `--mugl-version v72\|v71\|v70` | Which pinned prebuilt mugl to install. `v72` (default) is the current best (v7.1 plus precise frame-pacing waits that hold 25 fps when the game is in the background, MAC-PERF-006). `v71` and `v70` are rollbacks. Switching back and forth is a normal rerun. |
| `--mugl-build public\|private` | Only with `--dll-source build`. `public` (default) is the batching-only proxy: no hotpatches and no display-mode hook, so `DevModeIndex` is capped at 2 (1280x800 is index 2 in both lists). A later run with another proxy raises it again, because the kit remembers the index it wrote and only keeps an index you changed yourself. |
| `--hotpatch-mask N` | Value written to `C:\mutools\mugl-hotpatch.txt` (0-67108863). The default 44916143 is v7.5's built-in default: v7.4's 875951 plus 2097152 native body shadows, 8388608 native terrain decals and 33554432 the specialised mesh-draw append (MAC-PERF-009). 875951 is v7.1's 7599 (1\|2\|4\|8 helpers/inlining/peephole/xform, 32\|128\|256 meshdraw, 1024 frame pacing fix, 2048\|4096 zero-copy/strided batches) plus 16384 terrain sort (v7.3), 65536 quad batching, 262144 deferred client-array enables and 524288 off-screen culling (v7.4, MAC-PERF-008). Older builds read fewer bits and see their own default (v7.4 875951, v7.3 23983, v7.1/v7.2 7599, v7.0 15). 6575 is v7.1's default without the frame pacing fix. A file holding an earlier kit default (15, 7599 or 875951) is upgraded. |
| `--dotnet-installer PATH`, `--helpers-dir DIR` | Optional local `ndp48` installer (SHA-256 checked) to seed winetricks' cache, and the directory of `muinput.exe`/`clickstart.exe`. |
| `--no-mugl`, `--no-stats` | Skip the GL proxy, or remove `MUGL_STATS`. |
| `--skip-verify` | Do not run `verify-mu-mac.sh` at the end of setup. |
| `--reset-config` | Overwrite edited `C:\mutools\*.txt` and `LauncherOption.if` values. By default, your later changes are kept. |
| `--launcher-name`, `--no-desktop` | Desktop `.command` handling. A `.command` file the kit did not write is never overwritten. |
| `--fast-x87`, `--timewalker-dir DIR` | **TODO hook.** Uses an existing rosetta-timewalker build in `DIR` (env `MU_TIMEWALKER_DIR`; then `MU_FAST_X87=1` in the Desktop launcher); does not build one. The repository's own route is `mac-play/install-fast-x87.sh`. The launcher reflects the options of the latest run, so pass `--fast-x87` on every rerun if you want to keep it. MuMatrix32 runs with fast x87, and the fps comparison below used it in both bottles. |
| `--ac-variant with-ac\|no-ac` | **TODO hook.** `with-ac` leaves the client untouched. `no-ac` is deliberately not implemented and exits with an error. |

## Troubleshooting

| Symptom | Cause | Fix (kit step) |
|---|---|---|
| `rosetta error: invalid gdt selector index 6` | 64-bit (`win10_64`) bottle. The client far-jumps to selector 0x33 (Heaven's Gate). | Use a 32-bit `win10` bottle. Setup step 1 refuses `WineArch` other than `win32`, and verify FAILs it. |
| New bottle is not `WineArch=win32` | The CrossOver template behaved differently (not seen live: CrossOver 26.3's `win10` template gives `win32`) | Delete the bottle (`cxbottle --bottle NAME --delete`). Try `cxbottle --create --template win10 --param 'Bottle:WineArch=win32'` (untested), then rerun setup. |
| Setup skips .NET but the launcher will not start | A fresh CrossOver bottle already registers `NDP\v4\Full Release=533320 Version=4.7.03190` for Wine's builtin mscoree, so the `Release` value alone looks like 4.8 | Fixed: setup and verify also require `Version 4.8.*`, `clr.dll` and a native `system32\mscoree.dll`. |
| winetricks: runtime rejects `WINEARCH=win32` | CrossOver's WoW64 runtime rejects that variable even in win32 bottles | Never export `WINEARCH`. Setup runs winetricks with `env -u WINEARCH`. |
| winetricks installs or assumes 64-bit | A fresh `win10` bottle has an empty `windows/syswow64`, which makes winetricks guess win64 | The .NET step removes it with `rmdir`, only when it is empty, right before winetricks runs. It does not come back. |
| winetricks downloads .NET again although the installer is in `~/Library/Caches/winetricks` | winetricks 20260125 on macOS really uses `~/.cache/winetricks` | Fixed: the kit passes `W_CACHE` and seeds that directory |
| Launcher: `A generic error occurred in GDI+`, Launcher Initialization `0xF0` | Native WIC (`winetricks windowscodecs`) breaks GDI+/WPF encoding | Keep builtin `windowscodecs`/`gdiplus` (step 2: `*windowscodecs`/`*gdiplus` = builtin). Never run `winetricks windowscodecs gdiplus`. |
| Launcher crashes or renders nothing (WPF) | WPF hardware path | `Avalon.Graphics\DisableHWAcceleration=1` (step 2) |
| Launcher constructor aborts right away | Custom animated-GIF skin `Data\Launcher\Design\Template.design` | Step 7 renames it to `.disabled`, or `.disabled.N` after an update |
| `.NET` error / launcher will not start | .NET 4.8 missing or `MuTheMatrix.exe.config` without v4.0 runtime | Steps 3 and 6. Verify checks `Release >= 528040`, `Version 4.8.*`, the files and the config. |
| Settings: Critical Error / `Win32Exception at MonitorFromWindow` after Mac sleep | Stale Wine display/monitor link | Close the game and launcher, then relaunch. `play-mu.sh` resets the bottle's wineserver before each start. |
| "Mu The Matrix is already running" dialog | `play-mu.sh` found `main.exe` or `MuTheMatrix.exe` running (in any bottle) | Close the running game first. Only one instance is supported. |
| `Unable to connect to localhost:55232`, or server disconnect after direct start | `main.exe` was started without the launcher session | Always start through the launcher (the Desktop `.command`) |
| ~4 fps in world, ~19 fps on server select | mugl not loaded: Wine thunks ~20k `glBegin` fans per frame | Step 10 plus AppDefaults `main.exe opengl32=native,builtin`. The first line of `C:\mutools\mugl-stats.txt` must say `real=C:\windows\system32\opengl32.dll`. |
| Game crashes or hangs at first frame after a GL change | The proxy was copied into `system32` and loads itself | `system32\opengl32.dll` must be the Wine builtin. Verify checks the marker and the hash against CrossOver's i386 builtin. Restore it from `opengl32.dll.wine-builtin` or recreate the bottle. |
| mugl loaded but slow | DLL built with MinGW's default x87 math | Build with `-msse2 -mfpmath=sse` (`--dll-source build` does) |
| Window bigger than the screen, UI cut off | Game picked 1920x1200 on an 1800x1169 screen | `C:\mutools\mu-modes.txt` plus `DevModeIndex` (steps 8 and 9). Lower it with `--mode-index`. |
| Launcher Settings resolution differs from the game | mscoree proxy missing, or no `MuTheMatrix.exe mscoree=native` | Steps 10 and 4. `modehook.log` should list both exes with "N modes hooked". |
| A crash spawns winedbg, which kills the game thread | AeDebug enabled | The registry step sets `AeDebug Auto=0`, `Debugger=""`. It now runs before the .NET installer, and is re-checked after it. |
| `taskkill /im MuTheMatrix.exe` does nothing | The launcher ignores WM_CLOSE (`main.exe` closes cleanly on it) | Close the launcher window itself, or send SIGTERM to that bottle's process only (the owner's local `mu-to-server.sh`, not in the repository, did this) |
| Launcher hangs with fast x87 | timewalker's x87 path breaks .NET/WPF | `TIMEWALKER_X87_ONLY=main.exe` (`play-mu.sh` sets it) |
| Game freezes while profiling with fast x87 on | eipprof plus timewalker | Don't profile with x87 on |
| Mesa llvmpipe/zink slower or broken | Tested and reverted | Stay on builtin Wine GL plus mugl. Leftover `MESA_LOG`/`ZINK_DEBUG` env values are harmless and not reproduced. |
| Setup: "Bottle ... was not created by this kit" | Name collision | Use a new `--bottle` name |
| Setup: "Setup lock exists" / "Incomplete copy at ...mukit-partial" | Interrupted run | Make sure no setup is running, remove the lock or partial folder, rerun |
| Autologin types the account into the wrong field | `LauncherOption.if ID:` prefills Account, and focus stays there | `mu-autologin.sh` detects this and presses Tab |

## Inventory: every manual tweak and the step that reproduces it

Status key: **R** = reproduced by setup; **C** = checked by verify only; **N** = intentionally not reproduced; **T** = TODO hook; **?** = needs a live fresh-bottle test (see Gaps).

| # | Manual tweak in MuMatrix32 | Setup step | Status |
|---|---|---|---|
| 1 | 32-bit bottle, template `win10`, `"WineArch" = "win32"` | 1 bottle (`cxbottle --create --template win10`; arch asserted) | R (live) |
| 2 | Empty `syswow64` removed before winetricks (a fresh `win10` bottle has one) | 3 dotnet48 | R (live) |
| 3 | .NET 4.8 via `winetricks dotnet48` through the `cxwine`/`cxwineserver` shims (Release 0x80eb1) | 3 dotnet48 (+ winetricks cache seeded from `downloads/`). Detection needs `Version 4.8.*` + native files, not just `Release` | R (live) |
| 4 | Windows version reports Windows 10 (19045) after .NET | 4 winver (`winetricks win10`) | R (live). Needed: a fresh bottle reports "Windows 10 Pro", and dotnet48 leaves win7. |
| 5 | `HKCU\Software\Microsoft\Avalon.Graphics DisableHWAcceleration=1` | 2 registry | R (live) |
| 6 | `FEATURE_BROWSER_EMULATION MuTheMatrix.exe=11001` | 2 registry | R (live) |
| 7 | Builtin `windowscodecs`/`windowscodecsext`/`gdiplus` overrides | 2 registry | R (live: launcher works with builtin files only). MuMatrix32 also has native WIC/gdiplus *files* from an early experiment; the kit never installs them (N). |
| 8 | AppDefaults `main.exe` `opengl32=native,builtin` | 2 registry | R (live) |
| 9 | AppDefaults `MuTheMatrix.exe` `mscoree=native` | 2 registry | R (live) |
| 10 | `HKCU\Environment MUGL_STATS=C:\mutools\mugl-stats.txt` | 2 registry (`--no-stats` removes it via `"MUGL_STATS"=-`) | R (live) |
| 11 | `AeDebug Auto=0, Debugger=""` | 2 registry (HKLM), before .NET; re-checked after .NET | R (live) |
| 12 | Global `*mscoree=native` | set by winetricks dotnet48; verify checks it | C |
| 13 | `C:\windows\system32\opengl32.dll` stays the Wine builtin (`.wine-builtin` backup in MuMatrix32) | 10 dlls refuses to deploy otherwise; verify checks marker and hash | C (backup copy N) |
| 14 | Client copied to `C:\MuTheMatrix` | 5 game (APFS clone, transfer tar excluded; `cp -c` itself falls back to a plain copy across volumes, `ditto` is a backstop) | R (live; HFS+ RAM-disk source tested) |
| 15 | `MuTheMatrix.exe.config` with `useLegacyV2RuntimeActivationPolicy` + v4.8 sku (already in the Windows10MU source) | 6 launcher config (writes only if v4.0 is missing) | R/C |
| 16 | `Data\Launcher\Design\Template.design` renamed | 7 skin (every run, numbered backups) | R |
| 17 | mugl proxy `C:\MuTheMatrix\opengl32.dll` (v7.x) | 10 dlls (`--dll-source build\|prebuilt`, `--mugl-build public\|private`, `--dll-dir`, `--mugl-version v72\|v71\|v70`) | R (live: prebuilt v7.1, build, mugl-repo) |
| 18 | mscoree proxy `C:\MuTheMatrix\mscoree.dll` (modehook for the .NET launcher) | 10 dlls | R (live: `modehook.log` lists both exes) |
| 19 | `C:\mutools\mu-modes.txt` = `960x600 1024x640 1280x800 1600x1000 1728x1080` | 8 mutools (picked from screen or `--modes`) | R |
| 20 | `C:\mutools\mugl-mode.txt` = `full+vbo` (MuMatrix32 currently has `full+vbo+time`, which adds per-call timing to the stats) | 8 mutools | R |
| 21 | `C:\mutools\mugl-hotpatch.txt` = `44916143` (v7.5 default) | 8 mutools writes `--hotpatch-mask` (default 44916143; earlier kit defaults `15`, `7599` and `875951` are upgraded). Verify: 44916143 is the norm; 7599, 6575, 23983 and 875951 are named as older defaults; any mask with the v7.0 bits 1\|2\|4\|8 passes, with a note on missing/extra bits. | R (live: `=== hotpatch mask 7599: funcs 9/9 sites 18583 peep 50977`, 0 unexpected) |
| 22 | `C:\mutools\muinput.exe`, `clickstart.exe` | 8 mutools | R |
| 23 | `LauncherOption.if` = `DevModeIndex:4`, `WindowMode:1`, `ID:<account>` (original in `LauncherOption.if.orig`) | 9 launcher options (launcher's own byte format; original kept as `.mukit-orig`; the kit-written index is recorded in `.mukit/launcher-options.done`) | R (live: game window 1722x1076 = mode 1728x1080) |
| 24 | Desktop `Play Mu The Matrix.command` → `play-mu.sh` | 11 desktop (`Play Mu The Matrix (BOTTLE).command`, `MU_BOTTLE=BOTTLE`) | R (live: `open` of the .command started the launcher in MuMatrixKit) |
| 25 | `play-mu.sh`: running-instance guard plus bottle-scoped `wineserver -k` before start (stale display) | reused as-is by the launcher | R |
| 26 | Fast x87 (rosetta-timewalker, `TIMEWALKER_X87_ONLY=main.exe`); the old "(fast).command" is gone and the owner's local `play-mu.sh` defaulted to `MU_FAST_X87=1`; the repository's defaults to 0 | `--fast-x87` uses an existing build only | T |
| 27 | Anti-cheat on/off test builds | `--ac-variant` | T (no-ac not implemented) |
| 28 | Dev account password in the macOS Keychain; autologin scripts | not handled by setup (no account or Keychain name is stored anywhere in the kit). The repository's `mac-play/automation/mu-autologin.sh` takes `MU_BOTTLE`, `MU_ACCOUNT` and `MU_KEYCHAIN_SERVICE` from the environment. The kit deploys `muinput.exe` (and `clickstart.exe` if you have one). | N (the owner's local equivalent reached the world in the kit bottle) |
| 29 | AppDefaults for test exes (glbench, glmix, enummodes, meshbench) and dev files in `C:\mutools` (profiles, dumps, old `opengl32.dll` v6.4, `probe.dll`, test exes) | dev-only | N |
| 30 | `MESA_LOG`, `ZINK_DEBUG` env values (reverted Mesa experiment) | | N |
| 31 | In-memory 25 fps frame-cap patch (research PR #56) | not part of the live setup | N |

## Relation to the published repo (`main-exe-study`, `mac-play/`, now on `origin/main` after PR #52)

Already published in the repo:

- `setup-crossover-32bit.sh`: win10/win32 bottle, dotnet48, software rendering, browser emulation, APFS clone, skin rename, public mugl.
- `start-launcher.sh`: guarded wineserver reset plus `MonitorCheck.exe` display probe.
- `install-fast-x87.sh` and `fast-x87.sh`: pinned, self-checking timewalker.
- `mumodes/`: modehook and mscoree proxy sources.
- `hotpatch/`: v7.0 sources plus private table regeneration.
- `automation/`: autologin tools.

Why this kit does not call `setup-crossover-32bit.sh`: that script uses a different layout (`C:\MuTheMatrix-NAME`, `C:\MuMatrixTools`, `Play.command` inside the bottle). It refuses bottles without its own marker, and it does not deploy the mscoree proxy, the mode list, `LauncherOption.if`, AeDebug or the v7.0 hotpatch build. The working bottle and all local play/automation scripts assume `C:\MuTheMatrix` and `C:\mutools`.

What the kit reuses instead:

- the repository's `cxwine`/`cxwineserver` shims directly (they are stricter than the owner's local originals: they refuse a missing `CX_BOTTLE` or a `WINEPREFIX` whose name differs)
- the same MinGW flags as the repo's `hotpatch/Makefile` (`private`/`modes` targets), building `mac-play/mumodes` and `mac-play/mugl` from a copy under `installer/build/`
- the DLL you generated with `mac-play/hotpatch` (`--mugl-build private`)
- `install-fast-x87.sh`, as the documented route for the fast-x87 TODO

Not in this kit but in the repo: the `MonitorCheck.exe` pre-launch display probe, a candidate addition.

## Expected hashes (SHA-256)

| File | Hash |
|---|---|
| `main.exe` (tested client) | `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a` |
| `MuTheMatrix.exe` (launcher IGCN 1.12.1.3) | `c32e99ee98fc0773f850f9e76b160a9a00c867f4d745bf9e66c4b15d7f74bc3e` |
| mugl v7.2 (`mugl-v72.dll` in your `--dll-dir`) | `e37cf5d52c990cf38c18137ba3faacb339bb0a949816297a40027fd7203d5a60` |
| mugl v7.1 (`mugl-v71.dll`) | `85a8e3b6ea2f7d2602b14fc27e33496cfe136f14f4488e3dc5baffd4f15d3ca2` |
| mugl v7.0 (`mugl-v70.dll`, rollback) | `c06534dfe7a101856028153c7ed9f4db1f33cd497a9e012a5ae872a0896db31c` |
| mscoree proxy (`mscoree.dll` in your `--dll-dir`) | `6f2d2acea2a48eb789ab7867a6c0a4e97d6db3263d1ae3b1a729f9cc7a5639ac` |
| CrossOver 26.3 i386 builtin `opengl32.dll` | `0965d21be959f804d0dedaa4a52da952befbc9b73df573229c0074390823ec56` |
| `ndp48-x86-x64-allos-enu.exe` | `95889d6de3f2070c07790ad6cf2000d33d9a1bdfc6a381725ab82ab1c314fd53` |

Verify also accepts:

- a DLL whose hash setup recorded in `.mukit/*.sha256` (a locally built public or private proxy)
- any other mugl or mscoree DLL as a WARN ("unknown build")

## Live validation (2026-10-17, the owner's local copy)

This section is the owner's report about the local copy of the kit that this directory was adapted from (its siblings were `../mugl`, `../mumodes`, `../muinput`, a local `cxwine`; options `--dll-source current` and `--mugl-repo`). It was not rerun for publication, and the repository version below has not been run live (see "Adaptations for the repository"). Account names are omitted.

CrossOver 26.3.0.39832, macOS 27, Apple Silicon, 1800x1169 screen. The client came from MuMatrix32's `drive_c/MuTheMatrix` via `--game-dir`. MuMatrix32 itself was only read and verified, except that its client was closed and later restored by autologin.

| # | Item | Result |
|---|---|---|
| 1 | `cxbottle --create --template win10` | PASS. Gives `WineArch=win32`, `#arch=win32` in both .reg files, "Windows 10 Pro". It does create an **empty `syswow64`**, which the .NET step removes. Takes about 10 s. |
| 2 | `winetricks dotnet48` via the `cxwine`/`cxwineserver` shims | PASS. Release 528049 / 4.8.03761, native mscoree, `*mscoree=native`. Takes **3 min 14 s** with dotnet40 and 4.8 cached; downloads add about 120 MB. dotnet48 leaves winver at win7, so step 4 (`winetricks win10`, 4 s) **is needed**. **Bug fixed:** a fresh bottle pre-registers Release 533320 (Version 4.7.03190) for Wine's builtin mscoree, so the old check skipped .NET entirely. |
| 3 | `regedit /S` import | PASS. All values land, including HKLM AeDebug (`Auto=0`, `Debugger=""`) and the `*`-prefixed overrides. `--no-stats` deletes `MUGL_STATS`, and the next plain run puts it back. `wineserver -w` flushes correctly. The registry step now runs before the .NET installer and is re-checked afterwards (still intact). |
| 4 | Launcher with builtin WIC/GDI+ | PASS. "Press GameStart to Play" with server time, with the Wine builtin `windowscodecs.dll`/`gdiplus.dll` and no native files. |
| 5 | Proxies, hotpatches, `LauncherOption.if` | PASS. `modehook.log` shows "5 modes hooked" for both exes. `mugl-stats.txt` has `real=C:\windows\system32\opengl32.dll` and `=== hotpatch mask 7599: funcs 9/9 sites 18583 peep 50977` with 0 unexpected sites; the sleep hook and frame pacing fix are on. The launcher accepted `DevModeIndex:4 WindowMode:1 ID:<account>`, and the game window is 1722x1076 (the 1728x1080 mode). |
| 6 | Desktop `.command`, login, fps | PASS. `open` of "Play Mu The Matrix (MuMatrixKit).command" (what a Finder double-click does) started the launcher in MuMatrixKit. the autologin script with `MU_BOTTLE=MuMatrixKit` reached the world in 1 min 34 s. At spawn (Twisted Karutan 120,120, fast x87 in both bottles, about 60 s samples), see the table below. |
| 7 | `--dll-source build`, `--mugl-repo`, copy fallback | PASS. `build` compiled the owner's working-tree mugl and the mscoree proxy in about 2 s; that mugl applied mask 7599 at 25 fps on server select. `--mugl-repo` (the repository's `origin/main`, exported) built the public mugl in a copy, which is what the default `--dll-source build` does now; it loaded (batching only) at about 19 fps on server select with plain Rosetta, and DevModeIndex was capped at 2. For the copy, macOS `cp -c` silently falls back to a normal copy from a non-APFS (HFS+ RAM disk) source, so the `ditto` branch is only a backstop. |

FPS comparison at spawn:

| Bottle | mugl-mode | work/frame | fps |
|---|---|---|---|
| MuMatrixKit (kit) | `full+vbo` | 27.2 ms (mean and median) | 24.9 (min 23.8; the game caps at 25) |
| MuMatrix32, session that had run for 30+ min | `full+vbo+time` | 34.5 ms median (37.0 mean) | 23.3 mean / 23.7 median |
| MuMatrix32, freshly restarted | `full+vbo+time` | 31.0 ms median | 22.7 median |
| Reference figure given for v7.1 | | about 33.6 ms | about 24-25 |

So the kit is at parity or better. Part of its lower work time is probably the reference's `+time` per-call timing.

Full timings: a from-scratch one-shot run (fresh throwaway bottle, everything cached) took **3 min 44 s** with exit 0 and verify at 0 FAIL. A rerun with nothing to do takes about 2 s and changes nothing.

Bugs found live and fixed in the scripts:

1. **.NET detection** trusted `Release`, which Wine pre-registers as 533320, so dotnet48 was skipped. Setup and verify now also require `Version 4.8.*`, `clr.dll` and a native `system32\mscoree.dll`; setup re-checks after winetricks.
2. **Winetricks cache path**: winetricks 20260125 uses `~/.cache/winetricks` on macOS, so seeding `~/Library/Caches/winetricks` did nothing. Setup now passes `W_CACHE` and seeds that directory.
3. **AeDebug ordering**: the registry import (AeDebug off) ran after the .NET installer. It now runs right after bottle creation, with a re-check after .NET.
4. **DLL ownership**: when the copied client already contained the wanted mugl/mscoree, no `.mukit/*.sha256` was recorded, so a later build switch made pointless `.mukit-backup-*` copies of the kit's own DLLs. It is now recorded.
5. **DevModeIndex after `--mugl-repo`**: the cap at 2 was later kept as if it were a user choice. The kit now records the index it wrote and keeps only an index you changed yourself.
6. **`--mugl-repo` dirtied the user's checkout** (`make` wrote `build/` into the repo). It now builds from a copy under `installer/build/`.
7. `cxbottle --create` output (about 20 "Using a 32-bit prefix" lines) now goes to `.mukit/bottle.log`.
8. Automation (the owner's local scripts, not in the repository): bottle selection through `MU_BOTTLE`, and closing only the selected bottle's game/launcher.

Static checks: the owner's local `tests/test-mukit.sh` passed 156/156 checks at the end of the session (this README said 154 earlier); the repository suite is a port with its own count. New ones cover v7.1/v7.0 pins and switching, the 7599/6575 masks, the old-15 upgrade, the .NET placeholder, `W_CACHE`, DLL ownership and the kit-written index.

Remaining gaps:

- The local `--dll-source current` option is not carried over to the repository version.
- A run without cached installers (download time) was not measured.
- After `--no-stats`, verify shows a WARN for the missing `MUGL_STATS` (by design; it cannot tell that you chose it).
- `--fast-x87` only reuses an existing timewalker build, and the Desktop launcher follows the latest run's flags. `--ac-variant no-ac` is not implemented (TODO hooks).
- `play-mu.sh` allows one client across all bottles, by design.

## Adaptations for the repository

What changed from the live-validated local copy when it was published as `mac-play/installer/` (MAC-KIT-001):

- **Paths.** The local kit assumed siblings (`../mugl`, `../mumodes`, `../muinput`, `cxwine`, `play-mu.sh`, `downloads/`, `third_party/`). It now uses the repository's `mac-play/` sources, its own `play-mu.sh`, and explicit parameters for anything that cannot be in a repository.
- **DLLs.** `--dll-source build` is now the default and builds from repository sources (public batching-only mugl, or your own `mac-play/hotpatch` private build with `--mugl-build private`). `prebuilt` takes `--dll-dir` and verifies SHA-256 pins; the prebuilt v7.x files themselves are never in the repository. `--dll-source current` and `--mugl-repo` are gone (the second one is the new default).
- **Parameters instead of constants.** Account (`--account`), Keychain service and account for autologin (`MU_KEYCHAIN_SERVICE`, `MU_ACCOUNT` in the repository's automation scripts), .NET installer, helper tools, timewalker directory and extra protected bottle names are options or environment values. No account ID, Keychain item name, password or machine-specific home path is in the tree (a test checks).
- **Tests.** `tests/test-mukit.sh` no longer needs a CrossOver install, real DLLs or macOS tools: it uses a stub `CX_ROOT`, synthetic DLLs with injected pins (`MUKIT_*_SHA256` test overrides; `MUKIT_SKIP_PLATFORM_CHECK=1` lets setup run on Linux), a portable `sed -i`, and skips `zsh -n` when zsh is missing. The `cp -c` clone falls back to a plain copy off macOS.
- **Live run.** See the next section. The default public mugl has no display-mode hook (`DevModeIndex` is capped at 2), unlike the hotpatch builds.
- **Relation to `setup-crossover-32bit.sh`.** That script (MAC-CROSSOVER-001) stays as is. This kit is the alternative that reproduces the `C:\MuTheMatrix` / `C:\mutools` layout of the hand-built bottle, with the mscoree mode proxy, mode list, `LauncherOption.if`, AeDebug and hotpatch configuration. Pick one per bottle; each refuses bottles it did not create.

## Live validation of the repository version (2026-10-17)

Run from a fresh worktree of `origin/main` (0c1b5c8) on the owner's Mac (CrossOver 26.3.0.39832, macOS 27, 1800x1169 screen), into a throwaway bottle, with the client copied from the owner's working bottle via `--game-dir`, `--dotnet-installer` and `--helpers-dir` given. Another bottle's client stayed logged in during the test, so each path was taken to the server-select screen only (no login; `play-mu.sh` refuses to start while any client runs, so the launcher was started with the same wine command, and once through the Desktop `.command` with `pgrep` stubbed).

| Path | Result |
|---|---|
| Fresh bottle, default `--dll-source build` (public mugl) | Exit 0 in 3 min 51 s (.NET 4.8 about 3 min; installers cached). AeDebug `Auto=0`/`Debugger=""` in `system.reg` before .NET ran; .NET placeholder detected and replaced; `win10` step needed and applied. Verify 36 PASS, 1 WARN (no `clickstart.exe` in `--helpers-dir`), 0 FAIL. Launcher, GAME START, server select at 1280x800 (index capped at 2), 19-20 fps with plain Rosetta; `mugl-stats.txt` `mode=merge` without hotpatch lines; `modehook.log` lists only the launcher (expected). |
| `--mugl-build private` (`generate.py` from the owner's pristine dump, then `make -C mac-play/hotpatch private`) | Generation 12 s, matches all pins (18,583 inline, 50,977 peephole, 9 helpers, 3 mesh-draw sites). DevModeIndex raised from the kit-written 2 to 4 automatically. Server select at 1722x1076, 25.0 fps; `=== hotpatch mask 7599: funcs 9/9 sites 18583 peep 50977`, mesh-draw native/direct with 0 fallbacks, sleep hook and `pace:` line present; `modehook.log` lists both exes. |
| `--dll-source prebuilt --dll-dir` (owner's `mugl-v72.dll` + pinned `mscoree.dll`) | Both pins accepted, installed `e37cf5d5...` / `6f2d2ace...`. Server select 25.0 fps, same hotpatch line, both exes hooked. |
| `--fast-x87 --timewalker-dir` + Desktop `.command` | Launcher written with `MU_FAST_X87=1` and the directory; `play-mu.sh` started the launcher through timewalker; server select 25.0 fps, work 12 ms (15 ms plain). |
| Reruns | About 2 s and nothing to do after the fixes below; verify 38 PASS, 0 WARN, 0 FAIL. |

Bugs found live and fixed:

1. **Builds were not reproducible**: MinGW stamps a PE timestamp, so every rerun of the default build produced new hashes and reinstalled both DLLs. The kit's mscoree command and `mac-play/mugl/Makefile` now link with `--no-insert-timestamp`; a test checks that a rerun leaves the DLLs alone.
2. **`--dll-dir` needed `mscoree.dll`** even though the proxy is public source; pointing it at a folder of mugl builds failed. The proxy is now built when it is missing (a pinned `mscoree.dll` in the folder is still checked and preferred). A failed DLL copy now stops setup instead of being ignored.
3. **The private-build refusal test depended on the checkout**: after a real `make -C mac-play/hotpatch private` it failed. The private build directory is now `MUKIT_PRIVATE_BUILD_DIR` (default `mac-play/hotpatch/build/private`) and the test points it elsewhere.
4. **`play-mu.sh` truncated a shared log**: every bottle wrote `~/Library/Logs/MuTheMatrix.log`, including the one of a client still running in another bottle. The log is now per bottle.
5. **Verify ignored the launcher's fast-x87 setting**: it reported "not built" while the Desktop launcher used timewalker. It now reads `MU_FAST_X87`/`MU_TIMEWALKER_DIR` from the bottle's launcher (PASS, or WARN if that build is gone, since `play-mu.sh` would then refuse to start).

