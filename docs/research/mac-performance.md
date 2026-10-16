# Fast x87 translation in CrossOver

MAC-PERF-001, issue #45. Investigation date 2026-10-16. This is an opt-in
compatibility path for the original client. A native editable game remains open.

## Target and reported observations

The client identity remains `main.exe` SHA-256
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
No game instructions or assets are changed by this work. Earlier restored
[record arithmetic](record-math.md) and [pose findings](pose-concat.md) establish
bounded math behaviors, not a profile of every in-world frame.

The owner and Claude supplied these observations on 2026-10-16. They were not
remeasured in the owner's bottle by this implementation task:

- MuMatrix32 supports login and actual gameplay. Karutan runs at about 4 FPS,
  server select at 18–20 FPS, with the main thread using about one core.
- The authored 32-bit immediate-mode GL probe measured 214 ns/call, about
  4.7 million calls/s. Mesa llvmpipe reached 12.9 FPS and zink failed at
  ChoosePixelFormat. Both experimental configurations were reverted.
- The authored transform probe measured 2.6 Mverts/s with x87 and 838 Mverts/s
  with SSE2. Under Rosetta Timewalker, x87 reached 268 Mverts/s with the same
  printed checksum. Those earlier compilation flags were not preserved here.

These observations strongly support x87 translation cost as a major bottleneck.
They do not establish that OpenGL never limits any scene, that every x87 opcode
uses the same slow path, or that a microbenchmark speedup transfers proportionally
to game FPS. The owner is testing actual gameplay separately. No post-patch
in-world frame rate is claimed here.

## Pinned implementation and scope

The installer fetches
[aprilmaccydee/rosetta-timewalker](https://github.com/aprilmaccydee/rosetta-timewalker/tree/ab1a6a032e488c0d6eade54ce70a02d653277810),
full commit `ab1a6a032e488c0d6eade54ce70a02d653277810`. Its modified embedded
Lifeisawful/rosettax87_jit derives from
`a44f1eff28591a90f4a8c7297134294811da06b5`. Both projects declare MIT; embedded
math routines carry additional notices. See [third-party notices](../../THIRD_PARTY_NOTICES.md).
Nothing is vendored into this repository.

Upstream `scripts/run-crossover.sh` copies and ad-hoc signs user-cache Wine
loaders, redirects the loader chain through its x87 runtime, and injects its
library into those processes. Child-process forwarding is an upstream design
property, not an observed MU launcher-to-game result in this task. Patches affect
the selected process chain. SIP and system Rosetta files are unchanged. The
owner's MuMatrix32 bottle and its processes are outside the implementation scope.

The separate ARPL patch is UUID-pinned to Rosetta 367.8. On the measured macOS
version it prints `unsupported or inconsistent Rosetta runtime; refusing to patch`.
The same run logs `RosettaRuntimex87 built` and completes the x87 workload with
matching output. Thus that refusal does not disable the measured x87 path. It
would matter for software requiring the unsupported ARPL behavior.

## Reproduction and local evidence

Environment verified locally:

- macOS 27.0.1, build 26A434; Apple Silicon.
- CrossOver 26.3, standard `/Applications/CrossOver.app` installation.
- Rosetta runtime UUID `E933BC84-AE96-325A-A30E-90380DD274EB`.
- libRosettaRuntime UUID `A1DA2B2A-3D68-33CB-A631-FA772DCDD167`.
- Apple clang 21.0.0, `clang-2100.3.34.2`; MinGW GCC 16.2.0.

Create a disposable bottle using `mac-play/setup-crossover-32bit.sh`, then run
`mac-play/install-fast-x87.sh --bottle NAME`. The installer builds from the pin
in `~/Library/Caches/MuTheMatrix/fast-x87/COMMIT/source`, runs the upstream native
FLD smoke check and both authored PE32 floating-point variants, then runs x87
through the patched loader. It requires a matching printed checksum and observed
translator activation before writing `validated`. The native FLD probe passed.
The log also contains `MachExc: PT_THUPDATE failed: Invalid argument` after
successful workload output; no complete exception-handler correctness is claimed.

The authored `fpbench.c` executes 4,096 vertices for 4,000 iterations. It updates
one input component to prevent loop hoisting, and uses QueryPerformanceCounter.
Build flags are `-O2 -fno-tree-vectorize`, then `-mfpmath=387` for x87 or
`-msse2 -mfpmath=sse` for SSE2. The checksum is one printed output float,
`o[17][2]`, at six decimal places. Equality is a bounded regression check, not
bitwise equivalence for all intermediate values or x87 instructions.

The initial installer check, while .NET setup was still finishing, measured
2.6 Mverts/s plain x87, 496.3 Mverts/s plain SSE2 and 281.6 Mverts/s patched x87.
All printed `3.904312`. Repeat measurements after setup are recorded below. The scalar SSE2 flags differ from the earlier reported
838 Mverts/s run, so those numbers should not be compared as identical builds.

`glbench.c` is the supplied authored source with explicit window, pixel format,
context, argument and GL-error checks added. Its helper uses SSE2 for its own
arithmetic. It creates a 640×480 window, issues 4,000 immediate-mode quads per
frame for 120 frames, counts 11 calls per quad plus clear/swap, and waits with
`glFinish` before the end timestamp. Report vendor, renderer and version. The
aggregate includes swaps and completion; it is not an isolated driver-call timer.

## Completed throwaway-bottle measurements

`MuFastX87-test` was created by the setup script from the original Windows10MU
source, with the pinned main.exe digest above. Setup was rerun after helper
changes to verify resumability and the final copied helper files. Three paired
runs after setup, using the same newly built PE32 sources and no game/login,
printed these throughputs in Mverts/s:

| Run | Plain x87 | Fast x87 | Plain SSE2 | Fast SSE2 |
|---|---:|---:|---:|---:|
| 1 | 2.5 | 274.8 | 456.2 | 465.4 |
| 2 | 2.5 | 278.2 | 465.0 | 463.1 |
| 3 | 2.6 | 280.8 | 468.8 | 449.8 |
| Median | 2.5 | 278.2 | 465.0 | 463.1 |

All twelve checksum outputs were `3.904312`. Median x87 elapsed times were
6.499 s plain and 0.059 s fast, about 110× in this synthetic loop. Fast runs
logged translator activation. Sub-0.1-second timings are noisy; these are three
local observations, not a statistical confidence interval or game-frame estimate.

The final plain GL run reported Apple / Apple M5 / `2.1 Metal - 91.7`, 1.02 s,
118.1 synthetic FPS, 5,195,812 calls/s and 192 ns/call. An earlier run during
setup reported 222 ns/call and 4,509,774 calls/s. Both passed the added GL-error
checks. This corroborates high immediate-mode throughput on this machine without
measuring every game rendering dependency.

The plain .NET MonitorCheck passed with DISPLAY1, 1800×1169. Its fast-runtime
attempt produced activation logs but stayed near one core for over 40 seconds
without a result. A prefix-scoped test-bottle shutdown ended it. That is a failed
probe, not a passed display check, and is why the generated launcher retains
the plain display-validation path. This unfiltered .NET failure motivated
MAC-PERF-002 below.

The final setup-generated Play.command also passed an end-to-end synthetic
check. In the throwaway clone only, the original MuTheMatrix.exe was saved,
the authored SSE2 probe temporarily occupied its path, and Play.command ran with
`MU_FAST_X87=1`. Logs show the idle reset, plain display-check success, fast
translator activation and the probe checksum. The saved launcher was restored.
This validates dispatch and guard integration, not the real launcher-to-main
chain. The test bottle was then stopped with its explicit WINEPREFIX and deleted
with `cxbottle --bottle MuFastX87-test --delete --force`; absence was confirmed.

Local raw logs remain ignored in `runtime/mac-x87/`, including final FP runs,
GL output, failed fast monitor log/sample, plain monitor output and installer
logs. Portable source checks pass 155 of 169 discovered tests, with fourteen
explicit private-input skips. Fourteen launcher tests cover the guards,
plain-monitor/fast-launch sequence, stale and modified builds, explicit plain
mode, required-fast refusal and avoiding a duplicate launch after failure.
Both precommit review axes passed after correcting runtime fingerprints.
Linux CI also cross-builds the three authored PE32 probes.

## Filtered launcher behavior and fallback

MAC-PERF-002 is issue #48, following PR #47. Claude reported that the unfiltered
MuTheMatrix.exe launcher hangs at about one core without a window, consistent
with the failed MonitorCheck above. With fast translation restricted to
main.exe, Claude observed a normal launcher, GAME START spawning main.exe,
and main-thread translated-code samples falling from 37–54% to about 1%.
These are supplied observations, not remeasured profiles in this task. Server
selection stayed at 19–20 FPS on both paths. A busy-wait frame cap is a working
explanation; post-patch in-world FPS remains owner testing.

`mac-play/x87-main-only-wrapper.c` is authored MIT code. It reads
`TIMEWALKER_X87_RUNTIME_LOADER`, `TIMEWALKER_X87_REAL_LOADER` and
`TIMEWALKER_X87_ONLY`. A nonempty filter matches a case-insensitive substring
in any argument after argv[0]. A match execs `runtime_loader real_loader args...`;
a nonmatch execs `real_loader args...` directly. Both preserve argument boundaries,
including spaces and empty arguments. Empty/unset filters apply to everything.
This is an argument-routing rule, not verification of the launched executable.

The installer copies our source into the cache, compiles it with Apple clang
for arm64 and ad-hoc signs the binary. The upstream checkout stays at the same
clean pin. Its `scripts/run-crossover.sh` reads
`x87_wrapper=${TIMEWALKER_X87_LOADER_WRAPPER:-}` and forwards that wrapper through
WINELOADER, CX_WINELOADER and its child-process hooks. Selection exports our
wrapper path and defaults `TIMEWALKER_X87_ONLY` to `main.exe`. An explicit empty
override is preserved and will again route .NET through the fast translator.
The installer self-check sets `TIMEWALKER_X87_ONLY=fp_x87`, proving the matching
route still activates the translator without disabling the filter globally.

Setup copies `start-launcher.sh` and `fast-x87.sh` into the setup-owned bottle.
The existing process-list guard refuses a running game/launcher or failed query.
The reset remains prefix-scoped and completes before plain MonitorCheck.
Failed display validation blocks launch. Installation is the opt-in. A validated
cache enables automatic filtered selection for setup-generated launchers.
Selection fingerprints the authored wrapper source and binary, pinned tracked
upstream source and build outputs, macOS build, Rosetta runtime and CrossOver
loaders/server. Missing, changed, incomplete or stale entries fall back before
startup. Older caches lacking our wrapper must be reinstalled.

`MU_FAST_X87=0 Play.command` forces plain CrossOver; `MU_FAST_X87=1` requires a
validated entry. Remove `validated` to persistently disable selection. After a
macOS/CrossOver update, rebuild and rerun the self-check. A runtime failure after
selection returns its error without automatically retrying the launcher.

## MAC-PERF-002 local verification

The setup script created `MuX87Filter-test` from the read-only Windows10MU
installation, with the pinned main.exe SHA-256 above. Setup completed .NET 4.8,
software rendering, monitor compilation, skin disabling and the APFS game clone.
The copied start/fast helpers matched the worktree files byte-for-byte.
An isolated cache at `runtime/mac-x87-filter/cache` was seeded by an APFS clone
of the existing clean pinned upstream checkout/build. The installer verified the
pin and source cleanliness, reused the upstream build, compiled our new wrapper
and ad-hoc signed it. `file` reports arm64; `codesign --verify --strict` passes.
The upstream tracked source remained clean after verification. The repeated
post-setup run used a separate `TIMEWALKER_CACHE_DIR` for its signed Wine copies.

The native FLD check passed. The installer used the authored wrapper with
`TIMEWALKER_X87_ONLY=fp_x87`, observed `RosettaRuntimex87 built`, and measured
plain x87 6.180 s / 2.7 Mverts/s and filtered fast x87 0.059 s / 279.1 Mverts/s.
Both printed checksum `3.904312`. These are single local synthetic observations;
the initial overlapping-setup run is not the final measurement. The separate
ARPL UUID refusal and `PT_THUPDATE` diagnostics remain as described above.

The actual setup-generated `Play.command` ran with `MU_FAST_X87=1` and the
unset-filter default, using that isolated cache. Its plain MonitorCheck passed
DISPLAY1 at 1800×1169. The log recorded opt-in selection and no
`RosettaRuntimex87 built` lines during launcher startup. A PID-scoped CoreGraphics
window list found the actual cloned MuTheMatrix.exe process's on-screen layer-0
`MuTheMatrix` window at 794×584 logical pixels. A capture of that exact window
showed the rendered launcher with GAME START available. No launcher substitution,
GAME START click or login was used. Only the disposable bottle's server was
stopped, and the bottle was deleted with its named cxbottle command; absence
was confirmed. MuMatrix32 and its processes were not modified.

Portable `make test` discovers 177 tests: 163 pass and fourteen private-input
checks explicitly skip. Six compiled-wrapper tests cover matching/nonmatching
routing, exact argument lists, empty/unset filters, errors and exit propagation.
Sixteen launcher tests cover defaults, custom/empty overrides, modified or
missing wrapper files and the existing guards/fallback behavior. Both precommit
review axes found no implementation defects; their documentation-limits concern
was addressed below. The staged publication audit rejected no files.
Private screenshots, window/process records, setup/launcher/benchmark logs and
the cache stay ignored under `runtime/mac-x87-filter/` in this worktree.

## Risks and remaining limits

The translator patches undocumented Rosetta internals. New macOS versions can
break discovery, translation, exception handling or loader forwarding. An
identity match and smoke check do not prove compatibility with every instruction.
The x87 implementation can differ in extended precision, control/status words,
rounding, exceptions and transcendental operations. The one-value checksum does
not resolve those risks; prior recovered math equivalence results do not validate
this replacement runtime.

Injected loaders and runtime patches may conflict with a game's anti-cheat or
service rules. No anti-cheat compatibility or server acceptance claim follows
from a synthetic local run. Keep the ordinary CrossOver path available.

Login, extended stability, post-patch in-world FPS, natural sleep/display recovery
and native Windows equivalence remain outside these local routing checks.
The owner is testing in-world FPS. This task does not click GAME START, enter
credentials or claim native editable game recovery.
