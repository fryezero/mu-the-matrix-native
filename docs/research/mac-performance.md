# CrossOver performance: x87 experiments and OpenGL batching

MAC-PERF-001, issue #45; MAC-PERF-002, issue #48; MAC-PERF-003, issue #51;
MAC-PERF-004, issue #57; MAC-PERF-005, issue #59; MAC-PERF-006, issue #61; MAC-PERF-007.
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

## MAC-PERF-004: Claude v7.0 in-process CPU hotpatches

Issue #57 publishes existing local work on `codex/mac-hotpatch`, stacked on
OPEN PR #52, `codex/mac-gl-batching`. This is source publication, local table
regeneration and cross-build validation. No game was started, stopped, profiled,
patched or installed during this task. MuMatrix32 and its game/tool directories
were not changed. The reviewed #52 proxy remains the default setup build;
`mac-play/hotpatch` holds the opt-in v7.0 snapshot. Later meshdraw experiments
are excluded.

### Identity and evidence classes

The on-disk target remains SHA-256
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
Claude's `mugl.c` and saved `mugl_v70.c` match at SHA-256
`c83977712df1f046f66648175f53e20c2553e8430ce9018d139898da2e4ab6a1`.
The corresponding `xform.c` and `xform_v70.c` match at
`cce0902f2c2fe8b761b97e6d6d08408c1ed93470a2f89ff4117785e58c7cc624`.
`mac-play/hotpatch/source-provenance.json` records source hashes before packaging
adaptations. These are authored-source identities, not binary runtime proof.

The existing private pristine dump `/tmp/pristine.bin` maps offset zero to
`0x00400000`, has 46,137,344 bytes and SHA-256
`6e7957c9af8685f5a5fb14008131eab50470d40d2e6128397d5795a88160bfd4`.
Its selected text `0x00401000..0x01a7c000` has SHA-256
`338d16ec2c3c596e9d37e05f48913a22417ad2d1d910c079e9dc2c3887fc62f9`.
This is a separate CrossOver memory image, not the earlier Linux restored-text
capture. Full runtime dump hashes are session-specific. The private listings
`/tmp/calls.txt` and `/tmp/ptext.dis` and the local `mu-mac-tools` tree are
owner-supplied inputs, unavailable in a fresh clone. Their required identities
are in `mac-play/hotpatch/targets.json`. Publication logs/reference headers are
ignored under `runtime/mac-hotpatch/` in this worktree.

The measurements below are Claude's reported prior single-host observations,
supplied in the owner's task brief. This publication did not rerun them and did
not acquire their raw profiling/benchmark logs. Fresh compile and table checks
are listed separately below. The million-call observation is not attributed to
a new harness run or to Windows-native execution. The prior merged skinning
reconstruction and its bounded instruction/corpus comparisons are documented in
[PR #54](https://github.com/fryezero/mu-the-matrix-recovery/pull/54). They are a
separate evidence class from the live replacement report.

### Mechanism and publication boundary

After GL batching, Claude attributes the bottleneck to main.exe's unoptimized
MSVC `/Od` x86 code under Rosetta: constant idioms, trivial accessor wrappers
and uninlined vector arithmetic. About 2,950 downstream draws/frame consumed
6.4 ms in selected GL timing. This supports the CPU-code hypothesis for that
workload, not a universal claim that GL costs are negligible. Direct versus
indirect calls both measured about 1.25 ns in `callbench`, so indirect dispatch
alone did not explain the remaining frame time.

External `mach_vm_write` changed memory but did not change observed execution.
Claude inferred stale Rosetta translations. Applying patches inside mugl from
wglSwapBuffers after roughly 100 frames did take effect. The in-process path
verifies expected original/replacement bytes, changes protection, writes, restores
protection and flushes the instruction cache. Unexpected bytes are skipped.
This reports observed behavior; it does not establish Rosetta's internal cache
contract. Mask changes are per-site operations, not an atomic transaction.

`C:\mutools\mugl-hotpatch.txt` is polled roughly once per second. Bits are 1
for handwritten helpers, 2 for inline trivial calls, 4 for peepholes, 8 for
skinning and 16 for skinning comparison. The default private-build mask is 15.
The handwritten addresses are VectorRotate `0x00d000ad`, VectorTransform
`0x00d002b2`, self `0x00cfc94a`, index `0x00cfc922`, deref16 `0x00c9b276`,
equality `0x00c9b0e4`, and store8 `0x00c9aa15`/`0x00c9a992`/`0x00c9a9af`.
The original helper digests/lengths are in `targets.json`; `hp.S` contains authored
replacement bodies. Claude reports 900,000 randomized tests per helper with zero
mismatches in the existing `hptest.c`/`thunks.S` harness. The harness compares
selected final registers and memory, not a complete EFLAGS/access trace.
It was cross-built here, never executed.

The SSE C skinning replacement is at `0x012b5bde..0x012b678d`, using an entry
jump plus a trampoline into the original. It follows the semantics of the
already merged `reconstructed/model-codec/skinning.c` in PR #54, preserving
binary32 operation order and reusing original angle-matrix, inverse-rotate and
world-test helpers. Build with SSE math and `-ffp-contract=off`. Verify mode
computes into scratch buffers, runs the original and byte-compares selected
vertices, normals, lighting/scratch values and bounds. Claude reports zero
mismatches over more than one million real in-game calls. The source skips
comparison when the first stack argument is zero; total calls and checked calls
are distinct. Broad equivalence outside observed inputs remains unverified.

Final v7.0 has 18,583 inline sites and 50,977 constant-idiom sites. Intermediate
JSON holds 18,584/51,067. The final inline set excludes the ret4 call inside a
replaced helper, and the peep set excludes 90 sites inside the replaced skinning
body. The inline scan also reflects already-installed helper bodies. The local
generator derives objdump listings from the pristine dump, or accepts the pinned
private listings, and reproduces that scope using hashes instead of
publishing original callee patterns. It requires canonical record digests to
match the final headers. The peephole flags-dead scan remains Claude's heuristic;
whole-program flags equivalence is unverified.

No original-byte header, `.orig`, `.new`, memory dump, private site JSON, binary
or credential is committed. The xform entry prologue also moves out of source
into a locally generated header. `generate.py` accepts only pinned private
inputs and an ignored output directory, checks helper digests and checks final
record digests. The original-byte comparisons remain in the runtime installer.
Generated source and DLLs containing those bytes must remain private. The
publication audit rejects these specific table names and `.orig`/`.new` files.
A compile-only CI build uses empty tables and disables main.exe hotpatch/Sleep
installation. Default setup still installs #52's reviewed batching proxy.

The Sleep IAT hook reports per-frame `work=`/`sleep=`. Work is elapsed interval
time minus render-thread Sleep duration, including other waits and host
scheduling. It is not exclusive CPU time. The `+time` mode times selected real
GL calls with QPC; `full+vbo+time` enables VBO emulation and timing together.
`mumodes/modehook.c`, shared with the authored mscoree launcher proxy, uses
`C:\mutools\mu-modes.txt` for a curated EnumDisplaySettings list. The older
extra-mode implementation remains unused in v7.0. No mode hook or launcher
proxy was installed here. General GL state regression coverage from #52 has
not been rerun for this opt-in snapshot.

The reported test cap is 25 FPS / 40 ms. There is no identifiable cap installer
in the pinned v7.0 source; this publication does not invent one. The separately
merged [frame-loop analysis](https://github.com/fryezero/mu-the-matrix-recovery/blob/2e8d89e578204c80b6bcf6ce295193ad959bf2ea/docs/research/client-frame-loop.md)
locates the compiled-in cap and distinguishes rendering cadence from the fixed
40 ms game-logic step.

### Reported in-world results

Twisted Karutan hunting at approximately x=107..112, y=95..98, MU Helper
auto-attack enabled, 25 FPS / 40 ms cap:

| Mask | Reported FPS | Reported work/frame |
|---|---:|---:|
| 0 | about 20.5 | about 48.5 ms |
| 7 | about 24.1 | about 40.3 ms |
| 15 | about 24.7 | 37..39 ms |

At spawn 124,120, the client reached the 25 FPS cap. The earlier cross-session
history was roughly 4 FPS originally, 17 with batching, 23 with VBO emulation
and 24.7 with the current work. These are noisy observations from different
sessions, not controlled paired speedups. Hardware/runtime settings, sample
counts and raw logs were not independently re-established in this publication.
The cap can conceal headroom; neither capped FPS nor one spot proves gameplay
stability. Windows-native equivalence remains unverified.

### Remaining mesh cost and failed approaches

**Corrected by MAC-PERF-005 below: the 44.8% figure was a misattribution.**
Claude reported the remaining mesh draw routine `0x012b8d1d..0x012bb35a`,
`ret 0x2c`, about 2,713 instructions, at 44.8% of main-thread self-time
attribution using EBP walks. The routine submits per-corner texcoord/color/vertex
calls through many accessor thiscalls and switches on draw-mode cases 2, 4,
`0x1000`, `0x8000`, `0x80000`, `0x100000`. Relevant IAT slots:

| Address | Import |
|---|---|
| `0x01a7c750` | glBegin |
| `0x01a7c754` | glColor4f |
| `0x01a7c760` | glEnd |
| `0x01a7c76c` | glColor3f |
| `0x01a7c770` | glColor3fv |
| `0x01a7c774` | glTexCoord2f |
| `0x01a7c778` | glVertex3fv |

The x86_64 Mach profiler observed Rosetta keeping x86 EAX..EDI in ARM x0..x7
through thread_get_state flavor 1, ESP=x4 and EBP=x5. This is observed runtime
behavior, not a stable Apple interface. Scanning plausible call-preceded return
addresses initially misattributed mesh-draw samples to store8 helpers.
`EBPWALK=1` follows saved-EBP links and improved attribution. The 44.8% is a
reported attribution, not an independently verified current-instruction sample.
It is now known to be wrong: mugl was built without frame pointers, so the EBP walk
charged mugl's own code to the calling main.exe function (see MAC-PERF-005).

Other preserved failures: crashing test executables spawned winedbg, which
killed main.exe's thread; disable AeDebug before future tests in disposable
bottles. No registry change was made here. The old peep slice
`mem[a-base:end]` expanded generation to 49 GB; the local fixed version uses
`end-base`. A synthetic regression test covers the nonzero-base slice. External
patch writes and the stack-scan attribution failures must remain in the record.

Next, in a separately authorized task, port the mesh routine as an xform-style
C replacement with original-vs-replacement verification before performance
claims. No mesh replacement is published here. The owner authorized disabling
anti-cheat in prior testing and plans separate builds with and without it.
That is a plan only; this change implements neither variant and establishes
no anti-cheat compatibility.

### Publication checks

Local generation matches all nine helper original/replacement arrays and both
final v7.0 site tables. The private build cross-compiles the proxy and bit-exactness
harness without running either. The source-only build cross-compiles the proxy,
shared launcher mode proxy, mesh/call benchmarks and muinput. The Mach tools
compile as x86_64, without signing or attaching. Portable generator tests cover
input mismatch, overlapping/unequal patches, synthetic hook disabling, relative
call validation, live-flag rejection, the slice regression and Keychain-only
login plumbing. `make test PYTHON=tools/.venv/bin/python` and the staged
publication audit are recorded in the handoff after their final run.

Automation packaging requires explicit test-bottle/log/account selection, retains
runtime macOS Keychain password lookup and omits the original process-killing
restart helper. Login/movement helpers refuse MuMatrix32. No account name,
Keychain item name, password, screenshot or personal runtime log is published.

## MAC-PERF-005: Claude v7.1 mesh-draw loop, frame pacing and zero-copy batches

Issue #59 publishes Claude's saved v7.1 work (`mugl_v71.c`, `meshdraw_v71.c`,
`glstride.c`) under `mac-play/hotpatch` and `mac-play/diagnostics`, based on main
`f629ef9`. This is source publication, local private-table regeneration and
cross-build validation. No game was started, stopped, profiled, patched or
installed during this task, and MuMatrix32 and its game/tool directories were not
changed. Default setup still installs the reviewed #52 proxy; v7.1 is the opt-in
snapshot beside the v7.0 one. All runtime results below are Claude's supplied,
single-host reports from 2026-10-17; their raw logs were not acquired and nothing
was remeasured here.

### Correction to MAC-PERF-004

The v7.0 section above published "44.8% of main-thread self time" for the mesh
draw routine `0x012b8d1d`. That was a misattribution. mugl is compiled without frame
pointers, so the EBP-walking profiler charged samples in mugl's own code (notably
the immediate-mode emulation behind each `glTexCoord2f`/`glColor`/`glVertex3fv` call)
to the main.exe caller. With a frame-pointer build of mugl, Claude reports the
routine's own self time at about 3%. A routine timer (bit 512) puts the whole
original routine at 16.8-17.4 ms/frame at spawn (about 1,840 mesh calls and 0.98M
corners per frame), of which the native loop itself is about 4.0 ms and the rest is
batch submission and draws flushed from inside it. The v7.0 mask 15 results above
remain reported observations of that build; only the attribution is withdrawn.

### Mechanism

Source `meshdraw.c` replaces the per-corner triangle loop `0x012ba8a0..0x012bb229`
of the mesh draw routine, entered after `glBegin(GL_TRIANGLES)` and left at the
`glEnd` call `0x012bb22e`. The 7 bytes at `0x012ba899` are replaced by a jump to a
stub that calls `md_hook(ebp)`: result 1 skips to the `glEnd` call, 0 re-executes
the displaced instruction and continues in the original loop. The routine frame
slots, mesh/triangle layouts, the light and texcoord tables, per-mode behavior and
vertex-flag paths are decoded in `mac-play/hotpatch/meshdraw-notes.md`.
Observation (Claude's decode of the pristine dump) versus inference: the layout
offsets and per-corner call order are decoded from instructions; that the
replacement is equivalent is supported only by the verify runs below, not a proof.

- Modes 2, 4, `0x1000`, `0x80000`, `0x100000` and the no-attribute modes 1 and `0x40`
  are done natively with single binary32 SSE operations in the original order
  (`-msse2 -mfpmath=sse -ffp-contract=off`). Mode `0x8000` and flag `0x400` call
  client code with side effects and always run the original loop. The vertex paths
  for flag `0x20` (planar shadow projection) and `0x200000` (low-corner cull) were
  never seen in game and run natively only with bit 8192, otherwise the original.
- Bit 128 appends straight into mugl's open batch buffer with SSE stores instead
  of calling mugl's GL entry points, only when the client's import slots point at mugl
  and a batched block is open.
- Bit 256 ports the per-normal light table precompute `0x012b968c..0x012b996c`
  (`T[n][k] = S[n]*C[k] + 0.2f` when `model[0xcb] == 1`, else `L[n]*C[k]`).
- Bit 64 verifies. Without 128, the loop's five import slots point at recorders
  while the original loop runs, and the (op, float bits) streams are compared at
  `glEnd`. With 128, the native loop writes a scratch vertex array and the original's
  appends to the real batch are compared byte for byte, with the current
  texcoord/colour state. The light table is computed into a scratch copy and
  compared with the real table at the next mesh hook of the same model and mesh.
  A mismatch is logged and counted. In verify mode the original loop always
  produces the rendered output.
- Bit 512 is a routine timer, off by default. Bits 2048 and 4096 stop packing the
  vertex buffer: bit 2048 draws `T2F_C4F_N3F_V3F` batches straight from the 48-byte
  vertex array and 4096 reads every format in place with stride 48 (a
  compile-time check pins `sizeof(Vtx) == 48`). Claude reports mugl's pack cost
  falling from 2.4 ms to 2.0 and then 1.2 ms per frame.
- Bit 1024, frame pacing. The frame driver `0x01851d39` sleeps 40 ms minus the
  *previous* frame's work, so alternating frame costs lose time and lowering the
  work reduced the observed frame rate (19.6 fps at 34 ms of work). With the bit,
  the driver's `Sleep` at `0x0185267a` (identified by return address
  `0x01852680`) is skipped after a frame that swapped in-world (scene state at
  `0x01d1df70` equals 6), and mugl instead paces swaps to a 40 ms schedule. Login
  and character screens keep the original sleep. GL output is unchanged and the
  logic accumulator still follows real time. The merged
  [frame-loop finding](client-frame-loop.md) records the driver and the cap; the 25
  fps rate remains the game's fixed 40 ms logic step.

Hotpatch mask: the v7.1 default is **7599** (bits 1, 2, 4, 8, 32, 128, 256, 1024,
2048, 4096). 6575 is the same without pacing. Bits 16, 64, 512 and 8192 are
diagnostic or unverified and off by default. The README table documents every bit,
and a test pins the table, the default and the 14-bit mask limit.

### Reported verification and coverage (not rerun here)

All with zero mismatches, on MuMatrix32 character sessions:

- Call-stream comparison (bit 64): 7.52M meshes (about 3.99G corners) at spawn and
  the hunting spot, then 2.03M meshes at the hunting spot, 9.55M meshes in total.
- Direct append (64|128): 1.55M + 1.13M + 1.15M + 3.78M + 0.58M meshes, about 8.2M,
  including the login/character-select screens.
- Light table: 265k + 270k + 1.46M + 0.48M meshes, about 2.5M, none unverified.
- Framebuffer hash with `glstride.c` (all six batch formats), builtin OpenGL versus
  the proxy: equal at masks 0, 15, 2063, 4111 and 6159.

Scenes were town spawn, the Twisted Karutan hunting spot with MU Helper combat and
skills, and login/character select. Mode coverage: 2 about 96%, 4 about 2.3%,
`0x1000` about 1.1%, `0x40` under 0.1%, no fallbacks. Mode `0x80000` was seen
once (50 meshes) and shares the `0x1000` code, so it was not verified directly.
Modes `0x100000`, `0x8000`, flag `0x400` and the `0x20`/`0x200000` vertex paths were
not observed. This is coverage of what the client did in those sessions, not a proof
for all inputs.

### Reported measurements (not controlled paired speedups)

Same-session A/B (work ms / fps, 25 fps cap):

| Scene | Mask | Work ms | fps |
|---|---|---:|---:|
| Spawn 124,120 | 15 | 38.8 | 23.1 |
| | 943 (meshdraw direct + light, + timer) | 34.3 | 19.6 |
| | 1967 (+ pacing) | 33.8 | 24.2 |
| | 4015 (+ zero-copy) | 33.6 | 24.2 |
| | 8111 (+ strided) | 32.7 | 23.6 |
| Hunting spot 116,101, MU Helper on, 4 interleaved 20 s rounds | 15 | 42.4 | 22.6 |
| | 431 (meshdraw only) | 35.8 | 22.0 |
| | 7599 (v7.1 default) | 33.8 | 24.1 |

The spawn rows 943, 1967, 4015 and 8111 all include the routine timer (bit 512), so its
overhead is part of those numbers; the hunting-spot rows do not. Meshdraw alone cut work by 4-7 ms but did not raise fps until pacing was fixed.
The spawn "full v7.1" 33.6 ms / 24.2 fps row is mask 4015, not the 7599 default, and no
7599 spawn run is among the recorded rows. The 8111 row (adds strided arrays) lowered work
to 32.7 ms but measured 23.6 fps, so strided arrays are not shown to raise fps.
Routine time 17 to 10.7 ms/frame. The headroom against the 40 ms step is about 6-8 ms.

A fresh frame-pointer profile (mask 7599, hunting spot, 30 s) reports about 42% of
samples in the Rosetta runtime (sleeping/blocking and translated Wine/GL code), about
25% in mugl plus Wine 32-bit DLLs and 28% in main.exe. Top main.exe self-time: indirect
and vtable calls (mostly from `0x00ea27ac`) 5.2%, `0x012bc07a` 4.8%, `0x016d197d` 4.6%,
`0x016cdd5f` terrain decals 4.1%, `0x016cc9e2` 4.1%, `0x005520d0` 3.1%, `0x012b8d1d`
2.9%, `0x00d3215b` 2.6%, `0x00cd7be6` 2.5%, `0x009681bd` (sin) 2.4%. No single
dominant hotspot remains. Claude's conclusion is that 25 fps is the game's fixed 40 ms
logic-step cap and v7.1 only restores the headroom to reach it; the profile and the
conclusion are reports, not independently checked.

Incidental: one login failed and the client reconnected twice with Winsock error
10049 during a known home internet outage; two 6-minute tests, with and without
pacing, had no disconnects. Nothing links the failure to the patches, and this is not
an anti-cheat or server-compatibility result.

### Publication boundary and checks run here

The three patch-site original byte sequences that `meshdraw_v71.c` kept inline
(7, 6 and 10 bytes at `0x012ba899`, `0x012b968c` and `0x012b8d1d`) are not in source.
`targets.json` pins address, length and SHA-256; `generate.py` checks the pristine
dump against them and writes an ignored `meshdraw-orig.h`; the compile-only build gets
zeros and installs nothing (`MUGL_PRIVATE_TABLES` gates every hotpatch and Sleep-IAT
installation). `meshdraw.c` still refuses to write a site whose live bytes are not the
expected original or replacement. The audit rejects that header name.

Checks actually run: `make test PYTHON=tools/.venv/bin/python` (241 discovered, 223
pass, 18 explicit private skips), `make mac-hotpatch mac-diagnostics` (compile-only
v7.1 proxy and `glstride.exe`), `python3 scripts/audit_repository.py`. With the pinned
dump, private generation reproduces the 18,583/50,977 tables and matches all three
new site digests. A private rebuild at the reference image base
(`0x69680000`) has the same file size (1,760,063 bytes) as Claude's `mugl-v71.dll`
and its disassembly is identical apart from .rdata-relative addresses (the three
byte arrays are placed differently now that they come from a header, which shifts
some data by 32 bytes); that check compares instruction streams, not runtime
behavior. Neither DLL was executed or installed. Five new portable tests cover the
hash-pinned sites, zero-filled synthetic headers, mask-bit documentation and
default, the private-build gate with the fallbacks, and provenance entries.

Not established: the 0x20/0x200000 paths, mode `0x8000`, equivalence for inputs
the sessions never produced, Windows-native behavior, anti-cheat or server
compatibility, EFLAGS-level equivalence of the loop, and any hash-level check beyond
the six `glstride` formats. The pacing fix changes timing, not GL output, but has
only the reported six-minute disconnect-free runs as stability evidence.

## MAC-PERF-006: Claude v7.2 precise frame-pacing waits

Issue #61 publishes Claude's saved v7.2 `mugl.c` (SHA-256 `9eeed0c5...138dbdfd`) as the new `mac-play/hotpatch/mugl.c`, based on main
`5b96c26` (#60 merged). The change from v7.1 is small: precise waiting code for hotpatch bit
1024 and a stats line. There is no new patch site, no original byte, no GL change and no new mask bit
(default still 7599). This task did source publication and cross-build/portable checks only; no game,
Wine process or bottle was started, changed or profiled, and `~/Documents/mu-mac-tools` was read only.
Every runtime number below is Claude's supplied single-host report from 2026-10-17; raw logs were not
acquired and nothing was remeasured here.

### Symptom

With mask 7599 (bit 1024, frame pacing from MAC-PERF-005) fps fell to 17-22 in the world although the frame
work was about 26-28 ms, well under the 40 ms budget.

### Cause, from Claude's diagnostic builds

Two obvious explanations were ruled out:

- **Not the client's inactive-window throttle.** The active flag `[0x01cf0fc0]` stayed 1, and the inactive
  branch of the message loop at `0x0120ee34` has no `Sleep`.
- **Not double sleeping.** The only render-thread `Sleep` was the frame driver's, return address
  `0x01852680`, skipped on every eligible frame, and there was one logic step per frame.

What the builds did show: when main.exe is not the frontmost macOS application, Wine's `Sleep()` (timed in
the calling process with `select()`) is stretched by macOS background timer coalescing, an App-Nap-like
behavior. `Sleep(7..14)` took 17-45 ms, and 170 ms of requested sleep per 2 s measured 635 ms. With the game
frontmost every wait was within 2 ms. The muinput `activate` helper only activates the window inside Wine,
so macOS still treats the process as background. Waitable timers, alertable `SleepEx` and event waits
with a timeout stayed under 1 ms late in the background, because the wineserver times them. Observation:
the wait overshoots in these diagnostic runs; inference: macOS timer coalescing of the Wine client process
is the mechanism (the process-level cause was not examined with an Apple-side trace).

### Change (still bit 1024)

- `pace_wait` waits on a waitable timer to the exact 40 ms deadline (relative 100 ns units, no
  millisecond rounding) and falls back to `Sleep` if the timer cannot be created or set.
- With bit 1024, any other render-thread `Sleep(ms > 0)` also goes through the precise timer. This
  fixes the driver's own cap on the login and character-select screens. `Sleep(0)` and every other
  thread are untouched; the eligible driver sleep is still skipped by return address.
- New stats line: `pace: logic steps=.. waits=.. late=.. restarts=.. overshoot avg=..ms (...) |
  frame ms <30 30-38 38-42 42-50 50-60 60-80 80+` giving a swap-to-swap histogram. Logic steps read the
  driver counter at `0x0bdc5eb0`.

### Reported results (spawn, 28-29 ms of work; not rerun here)

| Build / mask | Background (not frontmost) | Frontmost |
|---|---|---|
| Pacing off (6575) | 19.3-21.1 fps | 25.0 fps |
| v7.1, 7599 | about 24.5 fps average; about 50% late frames with 60-80 ms spikes (17-22 observed) | 25.0 fps |
| v7.2, 7599 | 25.00 fps over 140 s: 69 periods, minimum 25.0; 3,468 of 3,482 frames at 38-42 ms; mean overshoot 0.08 ms | 24.95 fps |

The logic clock stays real time: 50.4-50.5 logic steps per about 2.01 s, i.e. 25 Hz, so the improvement is not
produced by running the game logic faster.

### Publication boundary and checks run here

`mugl_v72.c` is identical to Claude's local `mugl.c`. Publication keeps the packaging adaptation
from v7.0/v7.1 (`private-build.h` include, hotpatch and Sleep-IAT installation gated on
`MUGL_PRIVATE_TABLES`), so the compile-only CI build still installs nothing and never reaches the new timer
code. One further adaptation, found in review: Claude's `pace_stats` read the driver's logic counter at
`0x0bdc5eb0` on every stats tick, before checking `pace_fix`. With `MUGL_STATS` set (it is a bottle-wide
environment value) a proxy loaded by any other process, for example the GL probes, would dereference a client
address that may be unmapped there. The read is now gated on `MUGL_PRIVATE_TABLES` (a test pins it), so the
published compile-only build never reads a client address; private builds behave as Claude's. The v7.1 to
v7.2 diff adds addresses and arithmetic only (no byte arrays); the hotpatch targets and digests
(`targets.json`) are unchanged.

Checks actually run: `make test PYTHON=tools/.venv/bin/python` (245 discovered, 227 pass, 18
explicit private-input skips; four new portable tests pin the timer wait with its `Sleep` fallback, the
`hook_sleep` routing and untouched `Sleep(0)`/other threads, the unchanged default and absence of byte
tables, and the documented cause and limits), `make mugl mac-diagnostics mac-hotpatch` (CI's
cross-build set) and `python3 scripts/audit_repository.py`. The new code was compiled but not
executed: it only runs in a private build inside the game.

**Background soak (reported, not rerun here).** Claude reports a 6-minute (not 60-minute) background run with MU
Helper on, standing at Twisted Karutan 119,100, with mugl v7.2 (mask 7599): fps median 25.00 in every sample; one
2-second interval dipped to 6.3 fps (a 142 ms frame) and recovered by itself; work median 25-30 ms; memory fell from
380 to 298 MB (no growth); CPU 67-77%; 0 deaths, disconnects or crashes; 0 mesh-draw fallbacks or mismatches.
The monster load was light. This extends the 140 s figure but is one short run on one host, so long-session
stability (an hour or more, heavier load) remains open.

Not established: other hosts, macOS versions or power states (single host); runs longer than the reported 140 s
and the 6-minute soak above;
login/character-select pacing is reported to be fixed but the numbers above are spawn only;
Windows-native behavior (the cause is specific to Wine on macOS); anti-cheat and server compatibility; and
any effect of the waitable timer's wineserver round trips on CPU use. The MAC-PERF-005 v7.1 pacing
figures (24.1-24.2 fps) do not record whether the game was frontmost; read them with this finding.

## MAC-PERF-007: Claude v7.3 hitch analysis, terrain sorting and thread priority

Claude's live work on 2026-10-17 in MuMatrix32 (character Nighty), twelve short sessions under the game lock, each
run 3 minutes or less. Source: `mac-play/hotpatch/terrain.c`, `stall.c` and `mugl.c` (v7.3),
`mac-play/machprof/stallprof.c`, `muinput` `wheel`/`kdown`/`kup`. Other agents were loading the Mac throughout
(load average 6-15 on 4 performance + 6 efficiency cores), so absolute numbers are low and noisy. Every
comparison below is a same-session interleaved A/B. "v7.2 config" means the v7.3 DLL with mask 7599 and normal priority.

**The soak "142 ms hitch" was a ~2.9 s frame.** 142.26 ms was the mean `work` of a 2-second stats interval
that held 25 frames at 6.3 fps: 24 frames of 38-42 ms and one frame of about 2.9 s. The mesh-draw mode counters
show `0x80000` meshes only in that interval, which is consistent with a first-use model load. This is an
inference: the soak had no I/O logging. The new `stall:` log (frames of 100 ms or more, with optional
file-open, read and texture-upload counters) showed these classes:

- Map warps: 0.44-3.3 s, with up to 1,235 file opens, 27 MB read and 509 texture uploads. File I/O took about
  200 ms and uploads 45 ms. `stallprof` samples put most of the remaining CPU time in libjpeg (Huffman decode
  and IDCT around `0x018bb7a0`) and in the Rosetta runtime.
- First appearance of monsters or NPCs: 361-454 ms (560-753 opens).
- Opening the warp window: 126-141 ms.
- A `vmmap` of main.exe froze it for 2.1-3.0 s, reproduced once. `footprint` and `ps` did not.
- Frames of 100-300 ms with no I/O, caused by CPU contention: 1 in 110 s at load ~7, but 5-33 per 15 s at
  load 10-15.

The client loads assets synchronously, so the load stalls remain (gap). Running the render thread at
`THREAD_PRIORITY_HIGHEST` removes the contention stalls; the wineserver maps it to Mach precedence. At spawn,
load ~14, normal priority gave 14.3 fps, 70.5 ms work and 5-9 stalls; HIGHEST gave 24.5 fps, 37.4 ms and 0.
This is the v7.3 default, and `C:\mutools\mugl-prio.txt` overrides it.

**Terrain sorting (bit 16384, default in v7.3).** A GL-stream trace (`mugl-trace.txt`) showed that terrain
used 1,380 of 3,038 draws per frame in the default view and 3,921 of 6,411 zoomed out (F6 camera,
Shift+wheel). The cause is the per-tile alternation of the layer-1 face (`0x016cfab3`) and the alpha face
(`0x016cfb53`), with their state and texture. `terrain.c` draws a recorded run as opaque faces, then alpha
faces, each grouped by texture. The preconditions, the in-place handling of back-facing pairs and the
pixel argument are in `../../mac-play/hotpatch/README.md`. Bit 32768 compared both orders offscreen, color
and depth of every pixel. Across five sessions, 1,565 runs gave 0 differing pixels. The scenes were Twisted
Karutan spawn (default and zoomed out), the hunting spot with MU Helper, Devias, and Lorencia, where 8
back-facing alpha pairs per frame are drawn in place. 964 of those runs used the final in-place-pair code.
Depth ties between different tiles are covered only by this check, not excluded analytically.

| Scene (load) | Before | After |
|---|---|---|
| Zoomed out, sort only (~6) | 55.0 ms work; 6,265 draws, glDrawArrays 16.2 ms | 47.5 ms; 2,835 draws, 9.2 ms |
| Default view, sort only (~10) | 2,880 draws, GL draw 13.4 ms | 1,745 draws, 9.5-12.3 ms |
| Spawn, v7.2 config vs v7.3 (~14) | 11.8 fps, 85.8 ms, 25-33 stalls/15 s | 22.1 fps, 44.9 ms, 0 |
| Zoomed out, v7.2 config vs v7.3 (~14) | 8.2 fps, 124 ms, 101-107 stalls/15 s | 18.2 fps, 55 ms, 0-1 |
| Hunting spot, MU Helper, sort only (~10) | 17.3-22.0 fps, 45-60 ms | 18.6-19.2 fps, 52-55 ms (no clear change) |

Lorencia and Loren Market were empty on MTM-3, at 25 fps with 19-22 ms of work, so no busy town could be
measured (gap). The remaining bottlenecks are below 25 fps when zoomed out and at the hunting spot. Zoomed out
after sorting there are about 13.5 ms of GL calls: 1,693 mesh draws carrying 1.19M vertices, 635 additive
sprite quads and 421 blended grass quads. The mesh loop takes 6 ms. At the hunting spot, wglSwapBuffers takes
5.6 ms (1 ms elsewhere), which suggests the GPU is the limit for the skill effects. The additive sprite quads
(blend ONE/ONE, depth mask off) are the next order-independent candidate.

**Fast x87 is active in the play path.** `play-mu.sh` (default `MU_FAST_X87=1`) starts main.exe as a child
of timewalker's `runtime_loader`, and the patched libRosettaRuntime pages are dirty. In a relaunch A/B at
spawn (load ~7), off measured 71.7 and 52.5 ms of work (14.1 and 19.3 fps) and on measured 50.5 and 41.0 ms
(19.9 and 23.8 fps). Nothing was changed; `MU_FAST_X87=0` is the rollback.

Checks run: `make test`, `make mugl mac-diagnostics mac-hotpatch`, the private build, and
`scripts/audit_repository.py`. Not established: Windows-native behavior, other hosts, busy towns,
analytical exclusion of depth ties, and stability past the short runs.
