# A separate 32-bit CrossOver startup path

Issue [#39](https://github.com/fryezero/mu-the-matrix-recovery/issues/39),
MAC-CROSSOVER-001, adds authored setup under `mac-play/`. This is a compatibility
path for the original installed client. It does not implement a native game or
change the gameplay acceptance gates in `../roadmap.md`.

## Target and environment

The exact `main.exe` SHA-256 is
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
The source launcher's `MuTheMatrix.exe` SHA-256 is
`c32e99ee98fc0773f850f9e76b160a9a00c867f4d745bf9e66c4b15d7f74bc3e`.
The source installation is the user's `Windows10MU` bottle, under
`drive_c/Program Files (x86)/Glitch Games Network/Mu The Matrix`.

Local environment on 2026-10-16:

- CrossOver 26.3.0, build 39832. The application bundle reports `26.3.0.39832`.
- macOS 27.0.1, build 26A434, Apple M5.
- Winetricks 20260125, script SHA-256
  `431f82fc74000e6c864409f1d8fb495d696c03928808e3e8acffc45179312a7b`.
- Bottle template `win10`, with `"WineArch" = "win32"` in `cxbottle.conf`.

## Prior observations and supplied findings

The earlier isolated `MuMatrixRecovery` bottle used `win10_64`. Its direct and
WineDbg starts failed with `rosetta error: invalid gdt selector index 6`.
The local `runtime/direct-startup.log` shows `C:\windows\system32\ntdll.dll`
being mapped immediately before that error. Its relocation line identifies
preferred base `0x170000000`, consistent with the 64-bit module. This log was
read again for this investigation; the 64-bit failure was not rerun.

Claude's supplied 32-bit finding is also present in `runtime/mac32/run1.log`
in the original lab. It contains `Unable to connect to localhost:55232`, then
a launcher's .NET exception under the earlier dependency configuration. The
initial supplied finding associated .NET 4.8, WPF software rendering and native
windowscodecs with a visible launcher in `MuMatrix32`. The owner then reported
an inert START button and a Settings Critical Error. Later stepwise probes by
Claude reversed the windowscodecs recommendation. Native WIC breaks GDI+/WPF
encoding with `A generic error occurred in GDI+`, aborting the constructor with
Launcher Initialization code `0xF0`. Builtin windowscodecs passes that pipeline;
native gdiplus is unnecessary. The custom animated-GIF `Template.design` still
fails its design loader, so only the cloned skin must be disabled.

Claude reports that builtin codecs, .NET 4.8, software rendering and the default
IGCN skin now allow full initialization in `MuMatrix32`, show server time, connect
to `mtm2112.muthematrix.com:44206`, and check `dl.muthematrix.com:80` for updates.
GAME START awaits the owner's interactive test. These server/interactive findings
were supplied by Claude, not independently established by this task. Claude owns
that separate investigation, and this task did not modify `MuMatrix32`.

The launcher log `Data/Launcher/Log.txt` is linewise XOR-obfuscated according to
the supplied investigation. The supplied authored exact decoder is now included
under `mac-play/`, with fixed UTF-16LE XOR key `29 37 ec c9 3b`. Actual launcher
logs remain private. Decoding log messages does not recover the launcher source.

## Setup behavior and real validation

`mac-play/setup-crossover-32bit.sh` creates a new bottle with `cxbottle`, checks
its actual architecture, installs .NET 4.8 through shipped CrossOver adapters,
writes software-rendering and IE11 browser-emulation registry settings, and
clones the user's game with `cp -c -R`. The clone's Windows directory includes the bottle name so parallel
process-name diagnostics can distinguish it. It creates `Play.command` inside
the bottle. Named step functions and completion markers permit later fixes.
It keeps builtin windowscodecs and gdiplus. On every invocation it disables the
clone's `Template.design`, preserving prior `.disabled` copies with numbered
suffixes when an update restores the file. It never renames the source skin.

An existing bottle without the script's matching ownership/source marker is
refused. The four protected names are refused before any bottle operation.
Completed runs are idempotent. Interrupted copies and stale locks require local
inspection rather than automatic deletion. Source symlinks are refused to keep
the clone from referring back into another installation.

Practical failures and superseded attempts were preserved during validation:

1. Setting the environment variable `WINEARCH=win32` made the CrossOver runtime
   reject the first winetricks command, despite the win32 bottle configuration.
   The corrected script unsets that variable and validates `WineArch` instead.
2. The first launcher observation ended at 28.334 seconds while the separate
   investigation issued a process-name shutdown matching the shared Windows
   path. This is a confounded attempt, not a successful survival check or proof
   of an intrinsic launcher crash. The test bottle was stopped with an explicit
   `WINEPREFIX`, its logs saved, and it was deleted. The final setup uses a
   bottle-specific game path and was rerun from a fresh bottle.
3. The two initial bottles had native WIC installed under the original brief.
   They are superseded by Claude's later image-pipeline evidence. Both were
   deleted; the corrected final run started from a fresh bottle with no native
   WIC or gdiplus installation. The script uses a new ownership-marker version
   to refuse resuming a bottle created by the superseded setup.

The corrected fresh `MuMatrix32-ci-test` validation passed on 2026-10-16:

- Setup completed from the default source with the pinned main.exe digest.
  .NET's `Release` registry value is `0x80eb1`; software rendering is `0x1`;
  browser emulation is `0x2af9`, decimal 11001.
- All eight authored GDI+/WPF probe steps passed with synthetic images. Explicit
  `--debugmsg +loaddll` tracing identifies both `gdiplus.dll` and
  `windowscodecs.dll` as builtin. The supplied probe was built from the included
  source using .NET SDK 8.0.426; this version returns nonzero on any failed step.
- Executing the generated `Play.command` kept the launcher alive for 65.825
  seconds. Prefix-scoped Wine `tasklist` checks at approximately 0, 10, 20, 30,
  40, 50, 60 and 65 seconds all reported the same `MuTheMatrix.exe` task, Wine
  PID 424. The local screenshot shows the default skin, server time and
  `Press GameStart to Play`, without an initialization-error dialog. Finder
  double-click behavior was not separately exercised.
- Repeating setup with the explicit source path skipped completed steps.
  Restoring the source skin into the clone to simulate an update and rerunning
  setup created `Template.design.disabled.1`, preserving the first disabled
  copy. Another unchanged rerun succeeded. The source skin's before/after
  SHA-256 is unchanged, and the original file remains in place.
- All four protected names were refused. Temporarily withholding the ownership
  marker in the test bottle also caused refusal; it was restored for cleanup.
- The supplied exact decoder ran successfully on the copied historical log.
  That log contained no new entries for this healthy session, so it is not
  evidence for this run's network endpoints or session protocol.
- Only the test prefix's wineserver was stopped, using explicit `WINEPREFIX`.
  Setup logs/configuration were copied into the ignored validation directory,
  then `cxbottle --bottle MuMatrix32-ci-test --delete --force` succeeded. Both
  the bottle and setup lock are confirmed absent.
- `make test PYTHON=~/Documents/main-exe-study/tools/python/bin/python` passed
  134 portable tests with thirteen explicit private-input skips, 147 discovered.
  Its three separate `bash -n` checks passed. Private integration was not rerun
  for this compatibility setup. The staged repository audit passed all 138
  source files with zero rejections.

The setup removes `windows/syswow64` only through `rmdir`; a nonempty directory
stops the installation. Winetricks infers win64 from that directory's existence.
The wine adapter resolves relative installer filenames, passes `--workdir`,
and filters the known prefix banner from stderr. Both adapters require a prefix
and bottle, and wineserver receives the explicit `WINEPREFIX` even for `-k`.

Logs are ignored at `runtime/mac-crossover-32bit/` in the `mac-crossover`
worktree. They include setup/dependency logs, rerun/refusal results, registry
queries, launcher survival records and local selector scans. The original
lab checkout's working tree is unchanged. No game files or captures are tracked.

## Static selector-0x33 observations

A local Python byte scan used overlapping regex lookaheads for `EA .... 33 00`,
`9A .... 33 00`, and `6A 33 E8 00 00 00 00` followed by `CB` within 32 bytes.
The dots denote arbitrary bytes. A byte match alone is not an instruction or
evidence that the process executes it. No byte patching or execution occurred.

Inputs and matches:

- Original `input/main.exe`, target digest above. Far-jump-shaped bytes at file
  offset `0x5b1c5e`, computed PE image VA `0x009b265e`; far-call-shaped bytes at
  offset `0x1983157`, computed VA `0x0f752d57`. Neither boundary is established.
- Decoded protector `evidence/loader-recovery/themida-decoded.bin`,
  41,984,000 bytes, SHA-256
  `e42182c0b148ffc94fa6b9077fe81bebd471ef6ac9f30c682218259afea1bc31`,
  mapped base `0x0be3c000`. Far-jump-shaped offsets/VAs are
  `0x2335fca` / `0x0e171fca`, `0x255e4cc` / `0x0e39a4cc`, and
  `0x25b0bd7` / `0x0e3ecbd7`. A far-call-shaped match is at
  `0x267b177` / `0x0e4b7177`. These four are unvalidated raw candidates.
- Restored text from both `evidence/x86-capture-text-08/client-text.bin` and
  `evidence/x86-text-capture-09/client-text.bin`, 23,572,480 bytes each, SHA-256
  `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`,
  base `0x00401000`. Both identical captures contain one far-call-shaped match
  at offset `0x8c549d`, VA `0x00cc649d`, and no other searched pattern. Identical
  bytes are not independent corroboration of execution.

The decoded protector also contains two exact twelve-byte transition sequences,
both `6a 33 e8 00 00 00 00 83 04 24 05 cb`:

| Decoded offset | Computed VA | Computed return target |
|---|---|---|
| `0x20ceaae` | `0x0df0aaae` | `0x0df0aaba` |
| `0x2119d13` | `0x0df55d13` | `0x0df55d1f` |

Capstone in x86 mode decodes each as `push 0x33`, `call` to the following
instruction, `add dword ptr [esp], 5`, `retf`. The twelve-byte arithmetic puts
the next address and selector 0x33 on the stack for the far return. Decoding the
continuation in x64 mode yields `mov r8, rbx; mov rbx, rsp`, stack alignment and
argument setup, then `call rsi`. This is a local static observation at explicit
assumed instruction boundaries, not a traced branch. Local scan source, raw
matches and disassembly are retained under the ignored validation directory.

## Inference and remaining limits

Selector `0x33` has GDT index 6, because `0x33 >> 3` equals 6. The two decoded
sequences are consistent with a Heaven's Gate transition into x64 code.
Together with the 64-bit ntdll mapping and the difference between tested bottle
architectures, they support that explanation for the Rosetta failure. They do
not prove which instruction ran at the fault or that every 64-bit CrossOver
configuration fails. Runtime tracing at the transfer remains open.

The launcher is the entry point. Claude's analysis reports that it starts
`main.exe` with decimal argument `(Day * Month * Year) XOR 0x22894375`; direct
startup reaches `mtm2112.muthematrix.com:44205` and disconnects. Requiring an
active launcher session is an inference, not a verified server contract. This
setup does not construct or bypass that session and does not launch main.exe
directly.

Launcher UI survival does not prove START/Settings behavior, game login,
network/service compatibility, actual client rendering, or gameplay. The earlier
32-bit main.exe log shows startup beyond the observed Rosetta stop, not a playable
client. Full x86 guest captures remain compatibility-environment evidence;
native Windows equivalence and native macOS gameplay are still unverified.

## Settings and display-state recovery, MAC-CROSSOVER-002

Issue [#42](https://github.com/fryezero/mu-the-matrix-recovery/issues/42)
adds a guarded startup reset and a synthetic monitor check. The owner reports
pressing GAME START, logging in and playing in `MuMatrix32`. That is supplied
compatibility-gameplay evidence, not a native macOS build or an independent
login test by this task. Claude owns frame-rate work in that bottle. This task
issued no Wine commands, writes or shutdowns against `MuMatrix32`; it only read
its saved monitor-registry entry. All diagnostic mutations and shutdowns used
`MuSettings-test`, with a fresh `MuSettings-compare64` for comparison.

### Observed mechanism

The fresh win10/win32 bottle and fresh win10_64 bottle both report the Apple M5
adapter through `winemac.drv`. Both enumerate
`DISPLAY\APPA061\0000&0000`, with monitor class GUID
`{4D36E96E-E325-11CE-BFC1-08002BE10318}` and the corresponding Control\Class
monitor driver. `MonitorFromWindow` returns handle `0x1`, with a primary mode of
1800x1169 in the win32 check. The fresh win32 launcher opens Settings using
`clickstart.exe 30 0.713 0.946 12`; a single-window capture confirms it. A synthetic
WPF owner/CenterOwner child with a ComboBox also succeeds. The saved MuMatrix32
registry currently contains the same valid `APPA061` Enum entry. Architecture
alone does not reproduce the reported failure.

The display graph has several distinct registry views:

- `HKLM\System\CurrentControlSet\Enum\DISPLAY` contains monitor instances,
  class GUIDs, EDID and monitor properties.
- `HKLM\System\CurrentControlSet\Control\Video` identifies adapter/driver
  configuration; its sibling driver entry names `winemac.drv`.
- `HKLM\HARDWARE\DEVICEMAP\VIDEO`, value `\Device\Video0`, selects the
  current adapter source. The `HKCC\System\CurrentControlSet\Control\Video`
  view contains runtime source data including `GPUID`, `StateFlags`, modes and
  `MonitorID0`. This runtime linkage is essential; inspecting only the saved
  Enum entries misses the stale state.

A controlled fault in the isolated test bottle changed the active source's
`MonitorID0` from `DISPLAY\APPA061\0000&0000` to the reported
`DISPLAY\Default_Monitor\0000&0000`, which had no matching Enum instance.
Touching a diagnostic value under DEVICEMAP\VIDEO invalidated the display cache.
No host display mode, sleep setting or other bottle changed.

The native probe then returned a null `MonitorFromWindow` handle with last error
zero. Wine emitted the exact `find_monitor_from_path` error. Clicking Settings
in the already running launcher produced the exact decoded error:

```text
DispatcherUnhandledException
System.ComponentModel.Win32Exception (0x80004005): Success
at System.Windows.Window.MonitorFromWindow(IntPtr hwnd)
at System.Windows.Window.CalculateWindowLocation(...)
```

The launcher source was read locally at `di.cs`, method `ai`, which constructs
its Settings window, sets the launcher as Owner and calls Show. No launcher bytes
were patched or distributed. The pinned launcher digest remains
`c32e99ee98fc0773f850f9e76b160a9a00c867f4d745bf9e66c4b15d7f74bc3e`.
The synthetic WPF probe also fails in the corrupted state with an invalid-window
handle in `HwndDpiInfo.NearestMonitorInfoFromWindow` during window creation.
This establishes the monitor-link failure mechanism for both placement and WPF
resource initialization, without reproducing every frame of the supplied
ComboBox initialization stack.

Restoring the valid source link and invalidating the cache makes the authored
monitor check pass again without restarting the server. A prefix-scoped server
restart independently repairs the injected state by rebuilding the link from
the Mac driver. After stopping only the test launcher, the broken monitor state
persisted until reset. The final generated Play.command recovered from another
injection, passed its monitor check and opened Settings again. The captured
Settings window is visible, and no new launcher error log was created after the
previous failure log was archived. The earlier failure was decoded with the
shipped exact decoder and key `2937ecc93b`.

For source context, Wine 11.0's
[win32u display code](https://github.com/wine-mirror/wine/blob/wine-11.0/dlls/win32u/sysparams.c)
resolves source monitor paths against enumerated monitors in
`update_display_cache_from_registry` and `find_monitor_from_path`; `add_monitor`
uses `Default_Monitor` when EDID does not supply an ID. Its
[Mac display driver](https://github.com/wine-mirror/wine/blob/wine-11.0/dlls/winemac.drv/display.c)
feeds monitor geometry and EDID through `macdrv_UpdateDisplayDevices`. These are
upstream explanatory references, not a claim that the installed CrossOver binary
is byte-identical to that source. The live isolated registry/API/launcher results
above establish the behavior in CrossOver 26.3.

### Shipped workaround and checks

Setup compiles authored `diagnostics/MonitorCheck.cs` with the bottle's .NET 4.8
compiler in the versioned `display-check-v1` step. It needs no host SDK or MinGW.
The check creates a hidden synthetic window and validates MonitorFromWindow,
GetMonitorInfo and the primary EnumDisplaySettings mode. It returns nonzero for
the injected missing-monitor state and zero after repair. It contains no game
bytes and does not alter display configuration.

Setup also copies `start-launcher.sh` into its owned state directory and rewrites
Play.command on every rerun. The launcher serializes starts with `play.lock`,
queries that bottle's tasklist as CSV, and refuses to continue if `main.exe` or
`MuTheMatrix.exe` is present. Query failures or unrecognized output also refuse
the reset. It then runs wineserver `-k` and `-w` with the exported explicit
WINEPREFIX, checks the rebuilt display state and starts the cloned launcher.
A failed reset or monitor check prevents launch. Closing the launcher releases
the lock. A stale lock after a forced host interruption requires inspection.

There is no permanent guessed Enum/Control\Video patch. Display IDs and source
links belong to Wine's current topology and can change with connected displays.
The safe setup workaround rebuilds those runtime keys before each idle start and
checks the result. A running launcher is refused too, since it could start the
game between a process query and a shutdown. Keep this bottle dedicated to the
game; the reset terminates other programs in that same bottle.

Seven portable guard tests cover reset order/prefix, a running game, a running
launcher, failed/invalid process queries, reset failure and display-check failure.
A real synthetic `main.exe` sentinel in the test bottle retained its exact Wine
PID across a refused Play.command invocation, establishing that the running-game
guard did not kill it. This task did not start the actual game.

Validation artifacts are ignored under `runtime/mac-settings/` in the
`mac-settings` worktree, including registry snapshots, native and WPF probe
sources/results, injected and decoded launcher logs, click results, captures,
setup reruns, guard results and final checks. No original installation file was
modified. The final main.exe identity matches the pinned digest above.

The exact natural trigger after Mac sleep/display changes remains inferred from
the owner's error reports and the matching injected failure. Physical sleep or
host display changes were not induced while Claude was playing/testing in
MuMatrix32. The workaround protects startup; recovery during an active game,
Settings value persistence, Finder double-click behavior and actual gameplay in
the new test bottle remain unverified. The native recovery roadmap is unchanged.

Final local checks on 2026-10-16 passed `make test` with the configured lab Python:
154 discovered, 141 passed, thirteen explicit private-input skips, plus four Bash
syntax checks. Private integration was not rerun. Repeated setup skipped completed
steps, including display-check-v1, and rewrote the start helper successfully.
The final Settings capture used a PID-filtered ScreenCaptureKit window capture;
legacy screencapture returned an inconsistent parent surface for the same window
ID. The ScreenCaptureKit image shows the Settings controls and no error dialog.
No capture is tracked. Both MuSettings-test and MuSettings-compare64 were stopped
with their individual WINEPREFIX values, deleted through cxbottle, and confirmed
absent along with the setup lock. The four pre-existing bottles remain present.
The staged publication audit accepted all 141 source files with zero rejections.
