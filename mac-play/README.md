# Original client in a 32-bit CrossOver bottle

This setup creates a separate CrossOver `win10` template bottle with
`WineArch=win32`. It installs .NET Framework 4.8, keeps Wine's builtin image
codecs and GDI+, selects WPF software rendering, clones your installation with
APFS copy-on-write, disables its custom skin, and writes a double-clickable
launcher. No game files are shipped.

The owner reports GAME START, login and gameplay in the separate MuMatrix32
bottle. The isolated setup tests verify Settings and startup recovery from an
injected stale monitor link. Natural sleep/display-change recovery during a game
and a native macOS build remain open. See
[the evidence and test report](../docs/research/mac-crossover-32bit.md).

## Alternative: reproducible kit with the working bottle layout

[`installer/`](installer/README.md) (MAC-KIT-001) is a second setup path. It reproduces the
owner's hand-built `MuMatrix32` layout (`C:\MuTheMatrix`, `C:\mutools`, the mscoree mode
proxy, mode list, `LauncherOption.if`, mugl hotpatch configuration) in a new bottle, with a
read-only `verify-mu-mac.sh` and a synthetic test suite that `make test` runs. It does not
replace `setup-crossover-32bit.sh` below; each refuses bottles it did not create. It ships no
DLL: it builds the public mugl and the mscoree proxy from these sources, or installs DLLs you
supply after a SHA-256 check. Its adaptation to a repository checkout has been exercised only
by dry runs and the synthetic suite, not live (see its README).

## Requirements and use

Use macOS with CrossOver installed, its required Rosetta support, an APFS volume
that supports `cp -c`, and `winetricks` on your PATH. Homebrew supplies winetricks
with `brew install winetricks`. The dependency installers need downloads or an
existing winetricks cache and can take several minutes. CrossOver itself and a
legally acquired matching installation are separate prerequisites. Default GL
batching also needs MinGW-w64 (`brew install mingw-w64`) and make. Use
`MU_GL_BATCHING=0` during setup to opt out.

From the repository root:

```sh
./mac-play/setup-crossover-32bit.sh
# Or choose a new bottle and your source installation directory:
./mac-play/setup-crossover-32bit.sh --bottle MyMuBottle '/path/to/Mu The Matrix'
```

The default bottle name is `MuTheMatrix`. The default source is:

```text
~/Library/Application Support/CrossOver/Bottles/Windows10MU/drive_c/Program Files (x86)/Glitch Games Network/Mu The Matrix
```

The source is read only by the setup. The destination is `drive_c/MuTheMatrix-NAME`
inside the new bottle. A SHA-256 mismatch for `main.exe` produces a warning;
the tested identity is
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
The warning permits testing a user's other installation but does not extend the
evidence to it.

Open the printed `Play.command` path in Finder, then double-click it. The file is
inside the bottle's hidden `.mu-matrix-setup` folder; Finder's Go to Folder accepts
the full path. The launcher invokes `MuTheMatrix.exe` with the cloned game
directory as its working directory. Before starting, it queries that bottle's
processes, refuses a running game or launcher, and resets its wineserver with an
explicit WINEPREFIX. This rebuilds stale display state after sleep/display
changes. A synthetic monitor check must pass before the launcher starts. Keep
the bottle in its original location and dedicate it to the game, since the reset
terminates other programs in that bottle too. Close the launcher/game before
starting again. If a forced interruption leaves `.mu-matrix-setup/play.lock`,
check that the bottle is idle before removing that lock.

## Isolation and reruns

The setup refuses pre-existing bottles without its own versioned ownership marker.
It always refuses `Windows10MU`, `Steam`, `MuMatrixRecovery` and `MuMatrix32`,
including case variants. It never edits those bottles or the source installation.
Choose a simple bottle name containing letters, digits, underscores or hyphens.

A rerun with the same bottle and source skips completed dependency and copy
steps, disables any restored custom skin, checks the cloned executable again,
and recreates `Play.command` plus its start helper. The versioned display-check
step compiles a synthetic monitor diagnostic using the installed .NET compiler.
Changing the source requires a new bottle. An interrupted dependency installation
can be retried. An interrupted clone leaves `drive_c/MuTheMatrix-NAME.partial`; inspect
and remove that partial copy inside this setup-owned bottle before retrying.
A stale setup lock beside the bottle also requires inspection before removal.
An interrupted initial bottle creation without an ownership marker is deliberately
refused; inspect/delete that new bottle before starting again.

Step logs and markers live in `.mu-matrix-setup` inside the new bottle. Keep them
private. The script does not launch the game, log in, delete bottles or perform a
global wineserver shutdown. Do not point the setup at a source tree containing
symlinks to another installation.

`CX_ROOT` can select a CrossOver runtime directory other than
`/Applications/CrossOver.app/Contents/SharedSupport/CrossOver`.
`WINETRICKS` can select a winetricks executable. The bottle location is the normal
per-user CrossOver location, independent of any inherited `WINEPREFIX`.

## Compatibility steps

The shipped `cxwine` and `cxwineserver` adapters require both `CX_BOTTLE` and
`WINEPREFIX`. They preserve the selected prefix for winetricks, make relative
installer paths absolute, pass the current directory to CrossOver, and hide only
the known 32-bit-prefix diagnostic on stderr. CrossOver's version output is kept.
`WINEARCH` is unset because CrossOver's WoW64 runtime rejects `WINEARCH=win32`;
the script instead checks `WineArch` in `cxbottle.conf` before installation.

Winetricks uses the existence of `windows/syswow64` to infer architecture. The
setup removes that directory with `rmdir` only when empty. A nonempty directory
stops setup without deleting its contents. .NET's winetricks verb can change
Wine's reported Windows version to Windows 7; the bottle remains a win32 bottle
created from the requested `win10` template.

WPF software rendering is selected with:

```text
HKCU\Software\Microsoft\Avalon.Graphics
DisableHWAcceleration = DWORD 1
```

The setup also selects IE11 browser emulation for the launcher's embedded page
with `FEATURE_BROWSER_EMULATION`, value `MuTheMatrix.exe = DWORD 11001`, under
`HKCU\Software\Microsoft\Internet Explorer\Main\FeatureControl`. Claude's
probe identifies this as an optional fix for a harmless NullReferenceException.

Keep Wine's builtin `windowscodecs` and `gdiplus`. Installing native WIC with
`winetricks windowscodecs` breaks GDI+/WPF image encoding in the tested setup.
Do not install `gdiplus` either. If you used an earlier experimental setup that
installed native WIC, create a fresh bottle; this script refuses its old marker.

The clone's `Data/Launcher/Design/Template.design` contains the custom skin that
still fails Wine's design loader. Setup renames it to `Template.design.disabled`
so the launcher uses its built-in IGCN skin. This check runs on every invocation,
including after a game update. If `.disabled` already exists, the next disabled
copy receives a numbered suffix, preserving both. The original installation
keeps its skin. Always start via `Play.command`; direct `main.exe` startup does
not reproduce the launcher's session and arguments.

Later compatibility fixes can be authored as functions and added through
`run_step` in `main`. Use a new step name when changing an already completed
step's behavior. Keep fixes independent of private game bytes and test them in a
new bottle. Portable `make test` checks the Bash helpers with `bash -n` and exercises the
start/reset guard with a fake runtime. Dependency installation and UI behavior
require an explicit local Mac run.

## Local diagnostics

`diagnostics/MonitorCheck.cs` creates a hidden synthetic window and checks
MonitorFromWindow, GetMonitorInfo and the primary EnumDisplaySettings mode. Setup
compiles it as `C:\MuMatrixTools\MonitorCheck.exe` in the new bottle. The start
helper runs it after resetting the selected bottle and refuses launch on failure.
It returns nonzero for the reproduced stale/missing-monitor state. It does not
change monitor configuration. A permanent hardcoded monitor-registry patch is
avoided because the Mac driver rebuilds those topology-dependent entries.

`diagnostics/gdipprobe/` contains Claude's authored synthetic image-pipeline
probe, with a nonzero exit on any failed step added here. It needs a .NET SDK to
build and downloads the pinned .NET Framework reference-assemblies package.
Run its x86 `net48` output in the new bottle with the shipped adapter:

```sh
dotnet build mac-play/diagnostics/gdipprobe/gdipprobe.csproj -c Release
CX_BOTTLE=MuTheMatrix \
WINEPREFIX="$HOME/Library/Application Support/CrossOver/Bottles/MuTheMatrix" \
    ./mac-play/cxwine "$PWD/mac-play/diagnostics/gdipprobe/bin/Release/net48/gdipprobe.exe"
```

With no input it creates its own images and checks PNG save, ImageConverter,
WPF BitmapImage and PngBitmapEncoder, GDI+ bitmap conversion and ColorMatrix.
An optional absolute image path checks a user's local image instead. The probe
does not test the private skin container, networking, or gameplay. Build outputs
are ignored and must not be committed.

`decode_launcher_log_exact.py` is the authored log decoder supplied by Claude.
It XORs UTF-16LE message bytes with the fixed five-byte key `29 37 ec c9 3b`;
prefixes and continuation lines are parsed separately. Pass the known key
explicitly because a healthy log need not contain its fallback plaintext crib:

```sh
python3 mac-play/decode_launcher_log_exact.py '/path/to/copied/Data/Launcher/Log.txt' 2937ecc93b
```

Keep the decoded output local. It may contain installation paths or session
information. The decoder does not patch or change the log.

## Removing a test bottle

For a setup-owned test bottle only, close its programs, then scope any required
shutdown explicitly before deleting it:

```sh
CX='/Applications/CrossOver.app/Contents/SharedSupport/CrossOver'
WINEPREFIX="$HOME/Library/Application Support/CrossOver/Bottles/MuMatrix32-ci-test" \
    "$CX/bin/wineserver" -k
"$CX/bin/cxbottle" --bottle MuMatrix32-ci-test --delete --force
```

Never run `wineserver -k` without the intended test `WINEPREFIX`.

## Opt-in fast x87 translation

Apple Silicon users can build the pinned external Rosetta Timewalker runtime
in their user cache. Create a setup-owned bottle first, close its game/launcher,
then run:

```sh
xcode-select --install # if Command Line Tools are missing
brew install cmake llvm mingw-w64
./mac-play/install-fast-x87.sh --bottle MyMuBottle
```

The installer fetches exactly `ab1a6a032e488c0d6eade54ce70a02d653277810`, verifies
HEAD and tracked source cleanliness, builds with CMake/Homebrew LLVM, runs the
upstream native x87 FLD smoke check and the authored PE32 transform benchmark.
It also builds our MIT `x87-main-only-wrapper.c` with `xcrun clang -arch arm64`
and ad-hoc signs it in the cache, leaving the pinned upstream source unchanged.
The fast benchmark uses this wrapper with `TIMEWALKER_X87_ONLY=fp_x87`.
It enables automatic selection only when plain and patched x87 runs print the
same checksum and the patched run logs translator activation. This is a bounded
self-check, not proof of full x87 precision or game compatibility. It refuses
protected bottles, including MuMatrix32. It does not reset a wineserver or start
a game. Run it while the selected setup-owned bottle is idle.

Rerun setup for an older setup-owned bottle to copy the new launcher helpers.
`Play.command` keeps the idle-process guard and prefix-scoped display reset,
runs the existing display probe through plain CrossOver, then uses the selected
runtime for the launcher chain. The authored wrapper applies fast translation
only when an argument contains `main.exe`, case-insensitively. MuTheMatrix.exe
and its .NET dependencies use the real Wine loader directly. Applying the fast
translator to the .NET launcher hangs on this host. The filter is inherited by
child processes; matching any argument is a routing rule, not an executable
identity check.

A validated cache enables this filtered path for setup-generated launchers.
`TIMEWALKER_X87_ONLY` overrides the substring; an explicitly empty value applies
the fast runtime to everything, including .NET. For a matching diagnostic:

```sh
MU_FAST_X87=1 TIMEWALKER_X87_ONLY=fp_x87 ./mac-play/diagnostics/run-fpbench.sh MyMuBottle
```

The original MuMatrix32 quick launcher is separate and is never modified by these scripts.

The cache is `~/Library/Caches/MuTheMatrix/fast-x87/COMMIT`. Build, FLD and
benchmark logs stay there. `MU_FAST_X87_HOME` overrides that directory for both
installation and launching. Changes to the macOS build, Rosetta runtime,
CrossOver loaders/server, built translator or authored wrapper source/binary
invalidate validation. A missing, incomplete, modified or stale
installation falls back to plain CrossOver before starting the launcher.
`MU_FAST_X87=1` requires a validated install and refuses to start otherwise.
To force plain CrossOver:

```sh
MU_FAST_X87=0 '/path/printed/by/setup/.mu-matrix-setup/Play.command'
```

If the selected fast runtime fails during startup, the launcher returns its
failure without a second launch attempt. Close the bottle's launcher/game,
then retry with `MU_FAST_X87=0`. To disable automatic selection persistently,
remove the cache's `validated` marker. Reinstall and self-check after updates.
No SIP setting or system Rosetta file changes. This runtime depends on
undocumented internals and may change x87 precision or interact with anti-cheat.
See [measurements, risks and limits](../docs/research/mac-performance.md).

## Performance diagnostics

With MinGW-w64 installed, these helpers build authored PE32 executables in the
named setup-owned bottle and run them there. They reject protected bottles and
a running game/launcher. They do not reset servers. Avoid concurrent workloads
when comparing results. Both accept `MINGW_CC` and `MU_DIAGNOSTICS_OUT` overrides.

```sh
MU_FAST_X87=0 ./mac-play/diagnostics/run-fpbench.sh MyMuBottle
MU_FAST_X87=1 ./mac-play/diagnostics/run-fpbench.sh MyMuBottle
MU_FAST_X87=0 ./mac-play/diagnostics/run-glbench.sh MyMuBottle 120 4000
```

`fpbench.c` runs 16,384,000 dependent matrix/vertex transforms. The helper uses
GCC `-O2 -fno-tree-vectorize`, then `-mfpmath=387` or
`-msse2 -mfpmath=sse`. It prints elapsed time, Mverts/s and one output checksum.
`glbench.c` measures immediate-mode call throughput including frame swaps and
final `glFinish`. Its helper uses SSE2 arithmetic to reduce x87 overhead in the
probe itself. Report renderer/vendor/version with the result. Context/pixel
format failures return nonzero. Neither synthetic workload establishes game FPS.

## Default OpenGL batching

Setup now requires MinGW-w64 (`brew install mingw-w64`) and builds the authored
MIT [mugl proxy](mugl/README.md) with SSE math. It installs the generated DLL beside
`main.exe` in the cloned game directory and sets its app-specific OpenGL override.
The system32 OpenGL DLL must still carry Wine's builtin marker; setup refuses a
foreign replacement. Every rerun rechecks deployment and records both DLL hashes
under `.mu-matrix-setup`. Close that bottle's game/launcher before rerunning.

To opt out, including removing a previously managed installation:

```sh
MU_GL_BATCHING=0 ./mac-play/setup-crossover-32bit.sh --bottle MyMuBottle
```

This opt-out does not require MinGW. Batching reduces immediate-mode thunk calls.
The owner still needs to validate in-world performance and stability. It does not
satisfy the native source-build acceptance gates.

For an A/B test, the GL helper accepts a third numeric argument, quads per block.
It uses process-local DLL overrides and copies the proxy into its diagnostics
directory, without changing the game's registry settings:

```sh
MU_FAST_X87=0 MU_GL_BATCHING=0 ./mac-play/diagnostics/run-glbench.sh MyMuBottle 120 4000 4
MU_FAST_X87=0 MU_GL_BATCHING=1 ./mac-play/diagnostics/run-glbench.sh MyMuBottle 120 4000 4
make mac-diagnostics
```

Compare `fbhash` within the same block-size case as well as FPS. Hashes are FNV-1a
of the final 640x480 RGBA back buffer; they establish equality for that synthetic
scene and driver, not arbitrary game rendering. The source validates its window,
pixel format, context and final GL error. `diagnostics/glcheck.c` additionally
checks current attributes, incomplete blocks, display lists, client-state
restoration, VBO/VAO bindings, conventional-attribute shaders, provoking
conventions, flat primitives and foreign calls inside a block. Run it with builtin
and proxy overrides and compare its hashes. A second invocation with argument
`multitexture` exercises extension fallback in a fresh process.

The sampling helper runs only in a named setup-owned bottle, including while its
game is active. It refuses protected bottles and never resets a server:

```sh
./mac-play/diagnostics/run-eipprof.sh MyMuBottle main.exe 10
```

It suspends each target thread briefly, reads EIP and resumes it, then aggregates
64-byte buckets and module ranges. Output is private in the bottle's diagnostics
folder. This is intrusive wall-clock sampling, includes waiting threads and is
not a CPU-time profiler or a native Windows profile. Threads/modules are captured
once; later arrivals are not sampled. `pe_nearest_export.py DLL RVA...` maps a
bucket's module-relative address to the nearest preceding export, not a proven
function boundary. The profiler must finish normally so every suspended thread
can resume. Do not use it during latency-sensitive gameplay.
