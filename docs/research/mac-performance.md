# CrossOver performance: x87 experiments and OpenGL batching

MAC-PERF-001, issue #45; MAC-PERF-002, issue #48; MAC-PERF-003, issue #51.
Investigation date 2026-10-16. This is an opt-in
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

These microbenchmarks established high x87 translation cost in the transform probe.
The later in-world EIP profile below supersedes the hypothesis that x87 cost
explains the game's low frame rate. Fast x87 did not improve the measured in-world FPS.
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
| 1 | 38.7 | 118.7 | 3.07x | `733b6dc5` |
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

## MAC-PERF-003: profile and immediate-mode batching

Claude supplied the following measurements on this Mac. They are attributed
observations, separate from the disposable-bottle validation recorded below:

- Fast x87 did not change in-world FPS. An in-bottle EIP sampler placed 73% of
  the main thread's in-world samples in OPENGL32.dll, 18% in main.exe and 9% in
  anonymous memory. Nearest-export mapping identified glTexCoord2f/glVertex3fv.
- The client sends roughly 20,000 four-vertex GL_TRIANGLE_FAN blocks per frame,
  plus QUADS and larger TRIANGLES blocks. glBindTexture and glPopMatrix are
  the main boundaries between compatible draws. Each GL call crosses WoW64.
- The prototype reduced server-select draws from roughly 20,000 to 180 per
  frame, raised server-select FPS from 19–20 to the 25 FPS cap and reduced
  main.exe CPU from about 95% to 48%. Owner in-world testing remains pending.
- Claude's SSE-built glbench measured 3.5–3.7x speedup with matching framebuffer
  hashes for one and four quads per block. This task reruns the authored build
  at one, four and sixteen quads per block, rather than reusing those numbers.

`mac-play/diagnostics/eipprof.c` snapshots the selected process's modules and
threads, suspends each thread, reads CONTEXT_CONTROL/EIP and resumes it before
hash aggregation. It samples at roughly one-millisecond intervals and writes
per-thread totals plus the 4,000 hottest 64-byte buckets. Snapshot timing,
thread-suspension latency and waiting threads bias wall-clock samples; these
percentages are not instrumented CPU-time attribution. The helper resolves a
process name only within its selected Wine bottle, so use a unique target name.
The module table is a startup snapshot; dynamic loads and new threads are not
followed. `pe_nearest_export.py` labels the nearest preceding exported RVA in a
PE32 file. It does not recover symbols, establish exact function extents or
classify the anonymous 9%. No raw process samples are published.

### Proxy design and equivalence boundary

The authored MIT proxy exports all 361 names from CrossOver 26.3's i386 OpenGL
manifest. `gen.py` generates pass-through assembly stubs, real-function slots and
the DEF file during `make mugl`. Custom entry points collect positions and
current 2D texture coordinates, RGBA colors and normals. A pending batch keeps
server GL state unchanged until synchronization. Any other export first flushes
pending geometry; a foreign call inside Begin/End replays that open block through
immediate mode and forwards the rest of the block. Unsupported current-attribute
calls invalidate the cache. Refresh reads actual current attributes and shading
state after list execution, PopAttrib or a context switch.

For zero-based input vertices, `triangles.c` emits:

| Input | Emitted triangle order |
|---|---|
| Fan / convex polygon | `(0,i,i+1)` for `i=1..n-2` |
| Strip | `(i,i+1,i+2)` for even `i`; `(i+1,i,i+2)` for odd `i` |
| Quad | `(i,i+1,i+2)`, `(i,i+2,i+3)`, advancing by four |
| Quad strip | `(i,i+1,i+3)`, `(i,i+3,i+2)`, advancing by two |

Fan/strip conversion preserves winding and the last provoking vertex for each
original triangle under the legacy last-vertex convention. When the application
selects first-vertex convention, flat fans/strips keep their original modes and
submit separately. Smooth fan/strip conversion is unaffected. The extension
callback and state refresh track the selected provoking convention. Quad/polygon conversion is permitted only under GL_SMOOTH. Flat
quads/polygons retain their original primitive mode and submit separately.
Incomplete independent lines/triangles are discarded at each block boundary;
incomplete quads/quad strips and too-short fans/polygons emit no extra triangle.
Hand-computed host tests exercise indices, winding, provoking order and
short/incomplete counts. They do not establish arbitrary-driver pixel equality.

Submission saves client array state, packs the varying attributes, calls
`glInterleavedArrays` and `glDrawArrays`, restores client state, then restores
current color, normal and texture coordinates. Constant attributes use current
values instead of arrays. Values specified between consecutive blocks participate
in the varying-attribute check. Attributes changed in a zero-vertex block are
still sent on synchronization. Batch boundaries preserve order around textures,
matrices, queries and swaps. Stats report interval totals, not per-frame counts.

The implementation follows the primitive assembly and flatshading rules in the
[Khronos OpenGL 1.1 specification](https://registry.khronos.org/OpenGL/specs/gl/glspec11.pdf),
sections 2.6.1 and 2.13.7. State submission uses the reference contracts for
[glInterleavedArrays](https://registry.khronos.org/OpenGL-Refpages/gl2.1/xhtml/glInterleavedArrays.xml)
and [display lists](https://registry.khronos.org/OpenGL-Refpages/gl2.1/xhtml/glNewList.xml).
Smooth shading alone does not promise identical tessellation of arbitrary quads
and polygons. Nonplanar quads, nonuniform smooth interpolation, polygon smoothing
and driver-selected diagonals remain outside the measured equality claim.

Display-list compilation is forwarded as immediate calls and never rewritten as
array draws. List execution flushes first and invalidates current/shading state.
`glPolygonMode` line/point rendering permanently disables batching to avoid visible
triangulation diagonals or repeated points. A state refresh catches these modes
when applied inside a list. Selection/feedback render modes also disable batching
because merged draws would change their records.

`wglGetProcAddress` results use x86 trampolines that preserve integer registers and
flags, synchronize, then jump to the real stdcall entry point. Server texture
selection is preserved while current unit-zero coordinates are queried. Client submission selects unit zero and temporarily disables enabled
coordinate arrays on other units, since immediate mode ignores those arrays.
Client selector, enables and pointers are restored with the saved client state.
Their cached snapshot is invalidated by client-state changes and context switches.
Multitexture coordinate calls inside Begin/End use the immediate replay fallback;
between blocks synchronization preserves the driver's other-unit current values.
The proxy does not buffer per-vertex multitexture coordinates. Ordinary
`glBindBuffer/ARB` bindings are saved around CPU array submission; PopClientAttrib
invalidates that binding cache. GL2.1 conventional-attribute shaders remain active,
and provoking convention is tracked explicitly. Modern BindBuffer variants
select a permanent process fallback. For VAOs,
submission saves the application binding, uses the default VAO for client-memory
arrays, saves/restores that default client state and restores the application
VAO afterward. This avoids the ARB nonzero-VAO/client-memory restriction. The
trampoline passes a read-only pointer to caller stack arguments and preserves
the original call ABI. A failed or
exhausted trampoline allocation disables batching before returning a raw pointer.
The table holds 4,096 entries; the original 512-entry limit was insufficient for
the client's startup extension catalog.
General modern extension state, generic attribute arrays and vertex-ID-dependent
shaders are not supported by this narrow compatibility proxy. These checks do
not establish universal GL interposition.

Other limits: global buffers assume a single rendering thread and one current
context at a time; there is no per-thread/context state store. The observed path
uses finite float32 coordinates and in-range colors. Intercepted double/integer
variants convert through float32 even in `MUGL_MODE=off`. True A/B uses CrossOver's
`--dll opengl32=b` option for the builtin DLL, or `--dll opengl32=n,b` for the
proxy. Its wrapper overwrites inherited WINEDLLOVERRIDES, so environment-only
overrides silently failed to select the proxy in the initial discarded runs.
Error behavior for malformed GL calls, color-index modes,
edge flags/evaluators, all lighting/material interactions and arbitrary
multicontext applications is unverified. Memory allocation failure aborts the
process rather than continuing with a corrupt draw. Native Windows and game
anti-cheat acceptance are separate from the local compatibility checks.

### Setup boundary

Default-on setup builds with mandatory `-O2 -msse2 -mfpmath=sse`, copies the DLL
only into its setup-owned idle bottle's cloned game directory and writes
`HKCU\Software\Wine\AppDefaults\main.exe\DllOverrides`, `opengl32=native,builtin`.
`C:\windows\system32\opengl32.dll` must retain Wine's builtin DOS marker. The
proxy loads that absolute path and rejects missing real exports. Setup refuses
an unmanaged game DLL or non-builtin system DLL. It records proxy and builtin
SHA-256, and rechecks them on rerun. `MU_GL_BATCHING=0` removes only a managed game
proxy and the main.exe override value. Original files and MuMatrix32 stay intact.

### Local validation of the repository build

Setup created new `MuMugl-test` from the original read-only Windows10MU
installation. .NET 4.8, the monitor check, cloned default skin, default-on proxy
and AppDefaults override completed. The clone's main.exe retained the target
SHA-256 above. MuMatrix32 and its processes were not stopped or modified.
The final generated proxy SHA-256 is
`347f72467ec5a31c42289bae4eb6f04a6b608ffb64109b3caa55017a4e0d1405`.
The installed DLL and recorded `mugl.sha256` match; system32 remained builtin.

Measured on Apple M5, macOS 27.0.1 / CrossOver 26.3, Apple OpenGL 2.1 Metal 91.7.
Every run used SSE-built glbench, plain CrossOver translation (`MU_FAST_X87=0`),
240 frames, 20,000 quads/frame and a 640x480 client framebuffer. Each pair has
the same final FNV-1a framebuffer hash:

| Quads/block | Builtin FPS | Proxy FPS | Ratio | Both fbhash |
|---:|---:|---:|---:|---|
| 1 | 38.7 | 118.7 | 3.07x | `733b6dc5` |
| 4 | 65.2 | 118.9 | 1.82x | `1c55adc5` |
| 16 | 76.8 | 119.6 | 1.56x | `96e9fdc5` |

These are single serial pairs on a shared host, include frame swaps and final
readback, and are not confidence intervals or in-world FPS. Proxy results cluster
near 119 FPS, so presentation pacing may limit the measured ratios. Logs confirm
`mugl loaded; real=C:\windows\system32\opengl32.dll mode=merge` and frame/draw
stats. The initial environment-only override runs did not load the proxy and
were rejected. Native-only `--dll opengl32=n` also fails because loading the real
Wine builtin requires the builtin fallback. The corrected helper uses `n,b`.

`glcheck.exe` ran in separate builtin/proxy processes both normally and with its
`multitexture` argument. All thirty-six labeled framebuffer hashes match, both proxy invocations
report `state-failures=0 gl-error=0`, and the proxy load log is present. Cases
cover attribute changes between merged blocks, incomplete triangle blocks,
zero-vertex attribute changes, PopAttrib, display-list compile/execute,
unintercepted color setters, client vertex-array restoration, foreign calls in
Begin/End, flat strips/fans/quads/quad strips/polygons, a wireframe quad and a
multitexture extension trampoline in a fresh process. Additional final probes
cover bound/restored array buffers, GLSL120 conventional-attribute shaders and
first-vertex provoking convention under flat/smooth shading. A nonzero APPLE
VAO retains its binding, vertex pointer, VBO association and enable state after
submission. The multitexture probe uses a GLSL120 shader reading
`gl_MultiTexCoord1` while a different unit's client coordinate array is enabled;
its framebuffer, client selector, enable and pointer all match builtin behavior.
This is synthetic coverage of these paths, not exhaustive OpenGL equivalence.

Actual setup reruns with off, on and on again completed. The managed DLL was
removed/reinstalled, the main.exe override restored, and the final recorded hash
matched. Synthetic deployment tests also reject a foreign system DLL, symlinks,
unmanaged game DLLs and an active game. Portable tests total 201, with 186 passes
and fifteen explicit private-input skips. The generated PE has 361 named exports.
Linux CI cross-builds mugl and all three diagnostics in addition to portable tests.

Play.command passed the monitor check and started the real launcher. The
provided clickstart helper clicked GAME START at window fractions
`0.8753,0.9264`, after initialization. Wine tasklist showed main.exe PID 888.
The final proxy logged its system32 builtin load, buffered four-vertex fans during
loading, and reached 25.0 FPS after loading. Its last saved reporting interval
contains 999,569 blocks, 6,035,276 input vertices and 8,966 submitted draws, with
zero in-block fallbacks. Those are interval totals, not per-frame values. A
roughly two-second, 25 FPS interval corresponds to about 20,000 blocks and 180
draws/frame. No login or in-world performance/stability test was performed.

Startup testing exposed overbroad fallbacks for buffer, program, provoking,
texture-unit and VAO initialization, and exhaustion of the 512-entry prototype
extension table. These were replaced by the state-preserving paths described
above and a 4,096-entry table. The final main.exe run has no batching-disable
message after its load. This prevents a successful load alone from being
mistaken for active batching. The three-second profiler smoke run sampled
main.exe, reporting 69 modules, 24 threads and 192 occupied buckets; it is not a
new in-world profile.

The setup-owned bottle was stopped with its explicit prefix, deleted by name,
and its absence checked. Raw logs, diagnostics and copied setup state are ignored
in `runtime/mac-mugl/`. A fresh clone
contains neither game inputs nor these machine-specific logs.
