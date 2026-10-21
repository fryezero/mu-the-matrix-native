# Native preview app (NATIVE-APP-001)

`Mu The Matrix Native Preview.app` packages the native client `mu-client` (NATIVE-SHELL-001 and everything
after it) so the owner can try the native port by double-clicking, without flags or the command line. It is a
packaging milestone: no client routine was reconstructed or changed, so there is no Unicorn comparison; the
evidence is the bundle checks and runs below.

## What it is

- `native/app/Sources/*.swift`: a small AppKit launcher (`Contents/MacOS/MuNativePreview`). It finds the game
  folder (the free install `~/Library/Application Support/MuTheMatrix/prefix/drive_c/MuTheMatrix`, read-only;
  otherwise an open panel, remembered in `~/Library/Application Support/MuTheMatrixNative/settings.json`),
  prepares the local *Native Data* folder once, builds mu-client's command line and starts it as a child
  process inside the bundle (its own Dock icon and menu bar with the app's name and icon; the launcher becomes
  an accessory and only watches it). A crash or an error exit brings up an alert with the log's last lines.
  Option at launch (or `--settings`) opens a settings window: game folder, Native Data folder, "Prepare again",
  window size, ten feature switches.
- Native Data (default `~/Library/Application Support/MuTheMatrixNative/Native Data`, outside the repository and
  the bundle): `gfx/` (all 179 installed `.ozg` movies converted by the bundled `gfxconvert.py` with the HUD
  options, about 30 s; or copies of movies converted earlier), `lang/` (NATIVE-LANG-001 plaintext),
  `objects/` (decoded `EncTerrain<n>.plain` with sidecars), `sound/audio-tables.tsv`; the last three are copied
  from `~/Documents/mu-mac-tools/native/scratch` when present. `setup.json` records the result.
- Defaults: GFx interface on when the bundle has libmugfx and the movies exist (otherwise the stand-ins), combat
  demo, dropped items, names, NPC talk (the Lorencia demo table and placement), environment, particles, objects
  per scene (login 95, character select 94, the worlds; a scene without its file gets no option), game text,
  sound. Window: 16:10 inside 90 % of the screen's visible area, at most 1600 × 1000 points. The label
  "OFFLINE PREVIEW - no server connection" replaces the shell's offline line in every scene, and the window title
  reads "Mu The Matrix Native Preview — OFFLINE PREVIEW (no server connection)".
- `mu-client` gained `--combat --items --npc --npc-demo --no-names --no-env --no-particles` (mu-world's options,
  passed through the shell to the world embed; the combat weapon kind follows the session character's weapon) and
  `--label`/`--title`. The world embed now starts from mu-world's defaults: before, mu-client's world had
  `joint_demo` 0, a demo lightning bolt above the hero every 20 steps.
- Logs: `~/Library/Logs/MuTheMatrixNative/` (`launcher.log`, one `mu-client-<time>.log` per run with the command
  line, `nonet-<time>.json`; the newest 20 are kept).

## No network

The network protocol is out of scope and the preview promises no connection. Three layers:

1. Static: no Mach-O in the bundle except the guard imports `socket`, `connect`, `connectx`, `getaddrinfo`,
   `gethostbyname`, `sendto`, `bind`, `listen` or `accept` (`nm -u`; checked by the tests). libmugfx uses Ruffle's
   navigator without network (`native/gfx/mugfx/src/navigator.rs`).
2. Run time: `Frameworks/libmu-nonet.dylib` is loaded into mu-client with `DYLD_INSERT_LIBRARIES` (the bundle is
   ad-hoc signed without the hardened runtime, so dyld honours it) and interposes `socket`, `socketpair`,
   `connect`, `connectx` and `getaddrinfo`: every family but `AF_UNIX` fails with `EACCES`, lookups fail with
   `EAI_FAIL`, each refusal is logged, and the report counts them.
3. Observed: every run so far reports `inet_denied`, `other_denied`, `connects_denied`, `lookups_denied` = 0. The
   only socket is one `AF_UNIX` socket: a backtrace in strict mode (`MU_NONET_STRICT=1`) shows it is the system's
   own logging (`_simple_asl_connect` ← `os_log_simple` ← `rootless_check` ← `gfxInitializeLibrary` ←
   `CGLChoosePixelFormat`, local IPC to syslogd). Strict mode refuses it too and the client still runs.

## Bundle

`make -C native preview-app` (`native/app/Makefile`, modelled on `mac-play/bundle`): swiftc launcher, the guard,
mu-client, the icon drawn by `mac-play/bundle/icon/make-icon.swift`, the demo session and the Lorencia demo
tables, the converter with `model-recovery/libmodulus.dylib`. `bundle-dylibs.sh` copies Homebrew's Crypto++,
libjpeg and sdl2-compat into `Contents/Frameworks` with `@rpath` load commands, plus SDL3, which sdl2-compat loads
at run time from `@loader_path/libSDL3.dylib`; afterwards no Mach-O names a library outside `/System`, `/usr/lib`
and the bundle. libmugfx comes from `MUGFX_LIB` (default this checkout's `native/gfx/mugfx/target/release`,
built by `native/gfx/fetch-ruffle.sh && native/gfx/build-mugfx.sh`); without it the app uses the stand-ins.
Inner code is signed first, then the app; `codesign --verify --strict --deep` passes. `make -C native/app install`
copies it to `~/Applications` (replacing it) and runs `--setup` from the shell.

macOS asks before an app opened from Finder reads `~/Documents`. On the first real run the GUI setup waited at that
consent prompt while copying the scratch tables. `make install` therefore prepares Native Data from the shell, and
the setup window says that "Don't Allow" only skips the local tables.

## Checks

- `native/tests/test_native_app.py` (macOS; built with the stand-in libmugfx): Info.plist, layout, no data or caches
  in the bundle, ad-hoc signature without the runtime flag, self-containment, network imports, `--check-bundle`,
  the guard on a probe program (AF_INET/AF_INET6 `EACCES`, lookup refused, AF_UNIX allowed, strict mode), setup
  from a synthetic scratch folder with the read-only game folder unchanged (size and mtime snapshot), the plan's
  defaults, toggles and fallback, and `--smoke` over a synthetic game folder: title → login → character select →
  loading → world, the guard loaded with zero refusals.
- Private (`MU_RECOVERY_INTEGRATION=1 MU_GAME_ROOT=<free install>`): `--smoke --backend gl` with a fresh Native Data
  (the 179-movie conversion included), passed in 37 s.
- By hand: headless GL with every feature reached the world with GFx (`Apple M5`); a windowed run of 22 s reported 484
  frames and status 0 with the guard report clean.

## Limits

The demo server stays a demo (no network layer). The GFx account dialog, menus and the character list
(NATIVE-CHARSEL-003) arrive with their milestones; the app passes `--gfx` and picks them up. The window is not
resizable and there is no full-screen mode. A crash of the launcher itself leaves the client running.
