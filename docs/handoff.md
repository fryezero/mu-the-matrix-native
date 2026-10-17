# Continue from here

Read `status.md`, then choose a task from `roadmap.md`. Gameplay recovery needs runtime evidence. The user no longer has a Windows PC available, so do not make access to one a prerequisite for the next task. The full x86 Linux/Wine guest on this Mac has now restored readable client code; start with `research/restored-client-text.md` and `../runtime-linux/README.md`.

## Original launcher in CrossOver

Read [`research/mac-crossover-32bit.md`](research/mac-crossover-32bit.md) and
[`../mac-play/README.md`](../mac-play/README.md). The owner now reports GAME START,
login and gameplay in MuMatrix32. Claude owns frame-rate work there; do not edit
that bottle or stop its processes. This is compatibility gameplay, not a native
source build.

MAC-CROSSOVER-002 is issue #42, branch `codex/mac-launcher-settings`, isolated
worktree `~/Documents/mu-worktrees/mac-settings`. A fresh win32 and fresh win10_64
bottle both use winemac.drv and a valid APPA061 monitor. Injecting a stale runtime
MonitorID0 link to missing Default_Monitor reproduces the exact launcher Settings
MonitorFromWindow/Win32Exception Success stack and Wine find_monitor_from_path
error. A direct link repair works; a prefix-scoped server restart independently
rebuilds the source link. The exact natural sleep/display-change trigger remains
unverified because this task did not change the host display or sleep state.

Setup now installs a synthetic MonitorCheck.exe using the bottle's .NET compiler
and rewrites Play.command to use the shipped start helper. On an idle start it
runs a prefix-scoped wineserver -k/-w, verifies a hidden window's monitor and the
primary mode, then starts the launcher. A tasklist guard refuses a running game
or launcher, failed/invalid queries, and failed reset/display checks. A live
synthetic main.exe sentinel survived a refused start with the same Wine PID.
Settings was clicked and captured after reset, with no new launcher log after
archiving/decoding the injected failure. Settings value persistence and gameplay
in the test bottle were not exercised. Logs/captures are local and ignored at
`runtime/mac-settings/` in that worktree. Both test bottles and the setup lock
are deleted. After integrating the bone-track changes, portable checks pass
148/162 with fourteen private-input skips, plus four Bash syntax checks. See the
finding for the registry snapshots and capture details. Next, observe a natural
post-sleep idle start using Play.command;
do not trigger a host display change while another bottle is in use.

Keep builtin windowscodecs/gdiplus, .NET 4.8, software rendering and the built-in
IGCN skin from MAC-CROSSOVER-001, issue #39 / PR #41. Native WIC was a failed
hypothesis; recreate experimental bottles that installed it. Setup refuses
protected/unowned bottles, clones to a bottle-specific path and disables only
the cloned Template.design on every rerun. Original installations stay intact.
The previous MuMatrix32-ci-test validation passed all eight image steps and
65.8-second launcher survival before deletion. Source-recovery and native game
acceptance gates remain open. Two static selector-0x33 far-return sequences
support the Heaven's Gate hypothesis without proving the original Rosetta fault.

## Immediate-mode GL batching

MAC-PERF-003 is issue #51, branch `codex/mac-gl-batching`, worktree
`~/Documents/mu-worktrees/mac-mugl`. Read
[`research/mac-performance.md`](research/mac-performance.md) and
[`../mac-play/mugl/README.md`](../mac-play/mugl/README.md). The authored MIT proxy
and 361-export generator build with `make mugl`; generated sources/DLL stay
ignored. Portable tests compile the primitive conversion with host clang.
Setup is default-on, rechecks the Wine system32 builtin marker, installs beside
the cloned main.exe and records SHA-256. `MU_GL_BATCHING=0` removes the managed
proxy and override. It refuses an active game/launcher and unmanaged DLLs.

Validation uses the new setup-created MuMugl-test bottle, never MuMatrix32.
Three 240-frame pairs at 20,000 quads/frame have matching framebuffer hashes:
38.7/118.7 FPS at one quad/block, 65.2/118.9 at four and 76.8/119.6 at sixteen.
All thirty-six glcheck hashes match with no state failures or GL errors. Real setup
off/on/rerun checks pass. GAME START launched main.exe PID 888, with active fan
buffering and 25.0 FPS. Its last saved interval has 999,569 blocks and 8,966 draws,
with zero in-block fallbacks. No login/in-world test was performed. The bottle
was stopped with its explicit prefix, deleted by name and absence checked. The
final proxy digest is in the performance finding.
Raw logs/binaries are ignored in `runtime/mac-mugl/`. CrossOver's wrapper replaces
WINEDLLOVERRIDES; the diagnostic helper must use `--dll opengl32=b` or `n,b`.
Initial environment-only A/B runs were rejected because the proxy never loaded.
Native-only cannot load the real Wine builtin. Do not reuse those failed runs.

Both review axes found the wireframe triangulation issue; non-fill polygon modes
now permanently fall back, and the synthetic GL probe covers a wireframe quad.
Display lists compile without array conversion; in-block multitexture calls use
immediate replay.
Server/client texture selection and other-unit arrays are preserved; modern
buffer variants select a conservative process fallback. VAO binding is preserved
by submitting through saved/restored default-VAO state. The extension table has
4,096 slots because the client exceeds the prototype's 512 slots at startup.
Ordinary VBO bindings are preserved around
CPU array submission; GL2.1 compatibility shaders remain active. First-vertex
flat fans/strips keep their original primitive mode. Shared globals assume one
rendering thread
and one current context at a time. Float32 fixed-function inputs are the measured
domain. General GL equivalence, in-world FPS/stability and anti-cheat behavior
remain open. Claude's reported 73% in-world OpenGL sample share supersedes the
x87 bottleneck hypothesis. Native game recovery gates remain unchanged.

Next, the owner validates login, Karutan and other in-world scenes, comparing
builtin versus mugl with the same game settings and collecting optional stats.
Do not stop or change the owner's MuMatrix32 bottle to obtain those numbers.

## Fast x87 compatibility path

MAC-PERF-001 is issue #45 / merged PR #47. MAC-PERF-002 is issue #48, branch
`codex/mac-x87-main-only`, worktree `~/Documents/mu-worktrees/mac-x87-filter`.
Read [`research/mac-performance.md`](research/mac-performance.md).
The installer still requires clean rosetta-timewalker pin
`ab1a6a032e488c0d6eade54ce70a02d653277810`. Our separate MIT
`mac-play/x87-main-only-wrapper.c` is copied, compiled arm64 and ad-hoc signed
in the cache. Its source/binary join the identity checks. No third-party source
changes are needed. Upstream run-crossover.sh honors our wrapper override.

Selection exports the built wrapper and defaults `TIMEWALKER_X87_ONLY=main.exe`.
A case-insensitive substring in any argument after argv[0] selects fast
translation; nonmatches exec the real Wine loader directly. Caller overrides
are preserved, including empty to apply to everything. This avoids the verified
unfiltered .NET launcher/monitor hang. The installer's matching-filter check uses
`fp_x87`. Existing caches need reinstalling, and existing setup-owned bottles
need a setup rerun to copy the updated helper. Idle guards, prefix-scoped reset,
plain monitor check and explicit `MU_FAST_X87=0` fallback remain intact.

Local logs and the separate cache are ignored in `runtime/mac-x87-filter/` in
this worktree. The disposable bottle is `MuX87Filter-test`, created by setup
from Windows10MU's read-only source. MuMatrix32 and its processes are excluded.
The actual launcher window appeared under required-fast selection with the
default filter. PID-scoped window enumeration and a private capture confirmed
the normal launcher; MonitorCheck passed and no x87 translator activation
appeared during launcher startup. A post-setup matching `fp_x87` check measured
279.1 Mverts/s versus 2.7 plain, both printing 3.904312. The bottle was stopped
with its explicit prefix, deleted by name and absence checked. Six wrapper and
sixteen launcher tests pass; full make test passes 163/177 with fourteen private
skips. Both review axes pass; publication audit rejects no files.
See the finding for methods and limits. Next, the owner
continues in-world FPS/stability validation. Claude's reported GAME START and
profile improvement remain separately attributed; this task does not click
GAME START or use credentials.

## Prepared Windows capture path

Review and validate `windows-capture/capture-client.c` on Windows x64 against the pinned client. The helper identifies `main.exe` by SHA-256, opens the process for query/read access, and saves executable image regions from main.exe, IGC.dll and RGS.dll. It leaves the process running and writes a manifest with region digests and limitations. Build/smoke success under Wine does not prove native game capture.

Keep the capture local. Validate every file against `capture.json` before importing bytes into analysis. Live reads are not an atomic snapshot. Private executable allocations outside the selected image regions are not captured. Establish actual code restoration and build identity before declaring an unpacked program.

## Existing local artifacts

On the original workstation the lab directory is `main-exe-study`. Its ignored paths retain:

- `input/main.exe`: exact original analysis copy.
- `evidence/loader-recovery/recovery.json`: compression chunk mappings and identities.
- `evidence/loader-recovery/themida-decoded.bin`: 41,984,000-byte protector layer.
- `evidence/loader-recovery/emulation-04/`: corrected STOP-at-import trace and overlays.
- `evidence/rea-*.json`: full REA outputs, including failures and limitations.
- `asset-recovery/verified-v2/`: image scan manifest and selected exports.
- `model-recovery/verified-encrypted-v2/`: corrected complete model scan and selected exports.
- `runtime/`: isolated client copy and startup logs.

A GitHub clone contains source and reviewed summaries, not these artifacts. Reacquire private inputs or work on independent format/tests tasks when the lab data is unavailable.

## Traps already investigated

- The first unpacked layer is still the protector. Its matching size/hash does not establish gameplay recovery.
- Default Ghidra whole-region analysis exhausted a 2 GiB heap. A 4 GiB profile with two analyzers disabled completed, but returned short obfuscated call wrappers.
- An early emulator run treated unresolved IAT values as callable addresses and fell into zero data. Emulation-04 corrected this with STOP-only traps. The earlier run is not decryption evidence.
- V15 model payloads can leave a full sixteen-byte alignment trailer. Preserve it, retain block alignment, and validate the complete model structure.
- The original Mac filesystem is case-insensitive. Use file identity to deduplicate selected aliases such as Player.bmd/player.bmd.
- GitHub counts are not game-recovery percentages. Track proof for functions and behaviors, not a speculative overall completion number.

## End a work session

Record the branch/issue, change, input digest, decisive addresses/offsets, checks run, ignored artifact locations and next action. Update only the relevant findings, `status.md` and this handoff. Keep credentials, proprietary payloads and process dumps out of the repository.

## Original lab versus GitHub checkout

The original lab retains an archival local `lab/bootstrap` branch. The published
GitHub `main` branch is the collaboration baseline. For new development, clone
that repo or fetch and switch to `origin/main` once local Git authentication is
configured; preserve ignored lab artifacts separately.

## Published collaboration baseline

The private repository is [fryezero/mu-the-matrix-recovery](https://github.com/fryezero/mu-the-matrix-recovery). All 58 source/documentation files were downloaded from GitHub and compared byte for byte with the reviewed local snapshot. [The first CI run](https://github.com/fryezero/mu-the-matrix-recovery/actions/runs/38826951964) passed on macOS and Linux at commit `358354a009836105f2d9928397a4fe3f083326e7`. Setup actions were then updated to Node 24 versions to remove runtime deprecation warnings. Private game inputs and raw evidence remain in the original lab only.

## Latest model recovery

MODEL-014 is implemented on `codex/model-v14`. All 216 v14 models decode through the bounded Crypto++ wrapper and pass strict structural parsing, matching the separately compiled pinned upstream oracle. The complete scan is `model-recovery/verified-v14/manifest.json`; independent comparison is `evidence/v14-source/project-oracle-comparison.json`. The new public fixture has 91 synthetic vectors covering every cipher pair, thresholds, overlapping windows and selector aliases. Portable tests pass 43/47 with four explicit private skips; local integration passes all 47.

The runtime experiment is isolated under `runtime/x86/`, with a verified Debian base, a working overlay, a localhost-only SSH forward and a read-only game transfer mount. Preserve the existing guest while checking progress; do not start duplicate QEMU instances on its disk or port. The copied client launches far enough to restore its first code section. No login/gameplay or complete source rebuild is established.

## Continue after the Mac-only capture

RUNTIME-X86 is tracked in GitHub issue #5. The first executable section is repeatably restored, SHA-256 `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`. The successful bounded REA record is `evidence/rea-restored-client-prefix.json`. The verified scoped capture and durable manifest are `evidence/x86-capture-text-08/`. The authored Linux reader is `runtime-linux/capture_text.py`; it selects only that section and writes durable identity/hash metadata. Read the restored-code report before importing bytes. Preserve original captures and failed attempts separately. The current client reaches an unresolved localhost connection and no demonstrated login window.

GitHub CLI now authenticates as the repository owner through the macOS keychain. Git fetch/push and PR/check operations work directly; use them instead of browser uploads. The current development branches track their real GitHub history; older `lab/` branches retain the initial archival snapshots. Never print or commit the authentication token. PR #4 contains the model work and its corrected Linux build.

The runtime work is [PR #6](https://github.com/fryezero/mu-the-matrix-recovery/pull/6), stacked on model PR #4. Both pass macOS/Linux CI. Both are now merged into main, in dependency order. Runtime tests discover 55 cases, with 51 passing and four private-input skips in a source-only checkout; opt-in local integration passes all 55. The final capture08 binds the mapped header to the pinned file device/inode before and after reading and reproduces the earlier restored digest. The guest shut down cleanly after transfer and local verification. CAP-002 results follow below.

## First source behavior from restored instructions

CAP-002 / issue #7 is merged into main through [PR #8](https://github.com/fryezero/mu-the-matrix-recovery/pull/8). Read `research/client-copy64.md` and `../reconstructed/client-memory/README.md`. The authored 64-byte copy matches the pinned captured routine in 393 synthetic cases under Unicorn 2.1.4, including both overlap directions and sub-word alignment. An intentionally wrong `memmove` replacement fails 158 cases. REA decompilation is retained in `evidence/rea-client-copy64.json`; the generic profile missed the explicit pointer return/ECX role, which were checked from instructions and emulation.

Portable tests pass 57/62 with five explicit private skips; local integration passes all 62. Original class/callers and real-game invocation are unresolved. PRs #4, #6 and #8 are merged. PR #8 passed macOS/Linux CI. Continue with [issue #9](https://github.com/fryezero/mu-the-matrix-recovery/issues/9) to recover caller/type context or validate the adjacent clear routine, then approach x87 arithmetic with precision/control-word checks. Merge authority is recorded in AGENTS.md.

## Clear routine and reference search

Issue #9 is merged into main through PR #10 after passing macOS/Linux CI. Read `research/client-clear64.md`. The full wrapper/helper match authored clear64 in 768 cases across scalar/SSE feature branches, all 64 alignments and both DF states. The actual global feature value is unknown. No helper stub is used; execution hooks check branch coverage and memory access. Exact absolute-address scans of the original executable and restored text found no references to the first copy/clear/length entries. Original type/callers remain unresolved. Local evidence paths and REA identity are in the finding. Tests pass 59/65 with six explicit private skips and all 65 with opt-in local inputs. Next broaden the bounded function/data map to find useful subsystem entry points.

## Bounded window map

CLIENT-MAP-001 / issue #11 is merged into main through PR #13 after passing macOS/Linux CI. Read `research/client-window-map.md`; current local map is `evidence/client-map-64k/candidate-map-v5.json`. The first 64 KiB yields 803 explicitly labeled candidates, not recovered symbols. REA's initial 31-entry inventory overlaps 29; two entries are missed by the authored heuristic. A separately seeded REA dossier for `0x004013d0` suggests a cofactor/reciprocal 4-by-4 record operation, whose global double/template at `0x01a7dd40` and `0x01cf3b00` are outside the text capture and remain unknown. Next capture those selected image-data ranges with verified process/file identity before validating nontrivial arithmetic. Static map tests cover loops, segmented references and explicit unresolved paths. Portable dependencies now include Capstone through `tools/requirements-portable.txt`; full analysis still adds Unicorn.

## Selected record constants captured

Issue #12 is merged into main through PR #14 after passing macOS/Linux CI. Read `research/client-math-data.md`. The fixed `math-data` scope saves only 8+64+4 bytes and requires the restored-text hash before and after reading. Capture09 passed all identity/mapping/source checks, was transferred and hash-verified; the same source also repeated the legacy text scope. An early packed-state attempt was correctly refused with no payload. The guest shut down cleanly. Captured bias equals positive double zero, template equals a public identity matrix construction and feature bit1 is set in this Wine run. Original bytes remain ignored. Next reconstruct the selected cofactor/reciprocal operation, with explicit x87 control-state and overlapping-buffer checks.

## Controlled record arithmetic

Issue #15 is merged into main through PR #16 after passing macOS/Linux CI. Read `research/record-math.md` and the module README. Actual helper/wrapper bytes and captured data match authored C in 1,680 cofactor and 1,050 inverse cases under PC53/RNE masked x87 state with an empty stack. A translation snapshot replacement fails 16 alias cases; PC24 differs in 1,471 comparisons. Evidence JSON and REA dossier stay ignored. Full arena, stack/register effects, control state and bounded accesses are checked. Original FP state, type/callers, NaN/trap/status and general underflow domains remain unverified. Tests discover 88 cases: 81 portable pass with seven private skips; all 88 local integration pass. Next recover genuine caller/type context or original FP-state evidence before widening the model.

## Rejected model fields

Issue #17 is merged into main through PR #18 after passing macOS/Linux CI. Read `research/model-edge.md`. All 17 v15 rejections now identify their decisive decoded field offset. Thirteen complete structural records contain 66 direct edges to dummy parents; the other four have a NaN animation position, an active normal index and unsupported normal/vertex bone values. Native and Python decryptions agree for every complete payload. Raw diagnostics/probe stay in `evidence/model-edge/`. New errors preserve acceptance and expose `BmdError.offset` for these paths. Five independent synthetic regressions cover field offsets and indirect dummy ancestry. Next recover original model-loading/hierarchy behavior before accepting sentinel or dummy-parent semantics.

## Second image section acquired

Issue #19 is merged into main through PR #20 after passing macOS/Linux CI. Read `research/client-image-data.md`. The fixed second section at VA0x01a7c000, length2557764, repeats SHA-256 `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`. All identity flags, restored-text checks, early refusal, transfer digests and legacy math/text modes pass. Guest shut down cleanly. Ignored evidence is `evidence/image-data-run10/`; the local ASCII catalog has candidate BMD strings at 0x01aef904,0x01aefab4,0x01aefc6c. Next inspect bounded pinned-text references to those addresses and confirm instruction/function boundaries before inferring loader semantics. Do not relax the rejected-model checks without client evidence.

Continue with GitHub issue #21, CLIENT-LOADER-001. Local raw literal matches occur at 0x018202c7,0x018203f0,0x01830aef; nearest prologue candidates are 0x018202b4,0x018203e0,0x01830aa6. Linear decode reaches candidate PUSH instructions, but control flow/function boundaries remain unverified. The ignored `model-loader-literal-candidates.json` and `model-loader-prologue-candidates.json` retain these observations. Validate bounded REA dossiers before assigning loader semantics. Main is the reviewed baseline; guest is shut down.

## Client-linked v12 source

Issue #21 is merged into main through PR #23 after passing macOS/Linux CI. Read
`research/client-model-loader.md` and `../reconstructed/model-codec/README.md`.
The BMD filename caller at `0x018202b4` calls `0x012b3812`, whose v12 branch
calls `0x0098c5f2` for both length query and decode. REA dossiers are local under
`evidence/model-loader-first/`, `evidence/model-loader-callee/` and
`evidence/model-codec/`. The 194-byte leaf decoder matches authored C in 4,048
synthetic cases and all 180 installed v12 payloads, totaling 3,176,971 bytes.
A feedback-before-store replacement fails 312 overlap cases. The C API preserves
signed-length query/nonpositive behavior and read-after-write alias effects.
The comparator checks full arena, two reads/one write per byte, saved registers,
caller return, stack cleanup and both DF states, without decoder substitutes.
Portable tests pass 94/102 with eight private skips; all 102 local integration
pass. Complete model loading, original types and hierarchy acceptance remain
open. Next follow v14 target `0x016ced37` or v15 setup/decode
`0x0091a6c0`/`0x0091a730`, or validate a bounded v10 loader path with explicit
I/O/allocation dependencies.

## v15 jump slots resolved

Issue #24 is merged into main through PR #26 after passing macOS/Linux CI. Read
`research/model-dispatch.md`. Two fixed four-byte slots at `0x01d04e14` and
`0x01d04df4` repeat targets `0x0092a430` and `0x0092be30`, both inside pinned
text. Capture11, repeat, all three legacy scopes and transferred hashes pass;
a controlled second startup refused known packed text with an empty manifest
and no slot payload. Guest shut down cleanly. Raw artifacts are under
`evidence/model-dispatch-run11/`; original preflight failure and corrected
readiness attempt remain in `evidence/client-lea/` logs. A bounded decode-target
REA dossier is in `evidence/client-lea-resolved/`. Next inspect key setup and
its eight/four/single-block helpers, validate actual argument passing and
compare authored behavior against original code before claiming a v15 decoder.
Hierarchy findings landed in PR #25; review corrections follow below.

## Hierarchy review and shared baseline

PR #25 landed while the dispatch work was integrating. Post-merge independent
reviews verified the core selected-loop observations and found two evidence
accuracy issues, addressed under #27 in `codex/review-model-hierarchy` and merged
through PR #28. Both platform checks passed on commit
`6fd939d2c757b268f1c000f4efdd4d8439025936`, CI run `38892589220`.
Raw E8/PUSH searches remain heuristic candidates; PUSH lookahead now stops at
control transfers, including LOOP and traps. The v2 report keeps 314 raw call
candidates and 300 buffer-push candidates, with explicit unverified provenance.
Prior dummy-slot contents remain unknown, and child output is a composition
with that prior input, not necessarily equal to it. Read
`research/model-hierarchy.md` and `handoffs/claude-model-hierarchy.md`.
Strict parser acceptance is unchanged. Raw verification and test logs are in
`evidence/hierarchy-review/` and `evidence/hierarchy-review-*.txt` in the original
lab. Next continue v15 key/decode source using the resolved dispatch targets;
actual pose-buffer state during affected-model rendering remains unobserved.

## Client-linked v15 key context

Issue #29 / `codex/client-lea-key` merged through PR #30 after macOS/Linux CI
run `38893633476`. It adds authored C key setup for the observed
`0x0092a430` target. Read `research/client-lea-key.md`. The 6,446-byte original
body matches 1,320 synthetic cases across 16/24/32-byte keys, all word alignments,
both DF states and null/unsupported gates. It writes forward keys plus round
count at byte 768, leaving unused context bytes untouched. An independently
compiled reversed-order variant fails 1,248 valid cases. Key/context spans must
be disjoint; ECB payload decoding and native Windows behavior remain unverified.
Raw probe, reports and test logs are under `evidence/client-lea-key/`; REA is
`evidence/client-lea-resolved/rea-key.json`. Next validate eight/four/single-block
helper argument passing and batch alias behavior, starting at resolved wrapper
`0x0092be30` and helpers `0x00927060`, `0x00929370`, `0x0093bb20`. No VM startup is
needed for the captured instruction bytes. Guest remains shut down.

## Client-linked v15 ECB source

Issue #31 / `codex/client-lea-decode` merged through PR #32 after macOS/Linux CI
run `38895766466`. It adds authored batch ECB source. Read
`research/client-lea-decode.md` and `../runtime-linux/lea-compare/README.md`.
The relocated original wrapper and AVX/scalar helpers match 12,960 valid and
46 no-op guest cases. The ABI bridge rejects its own bad callee; wrong scalar
batching differs in 4,094 cases. Host Unicorn checks 1,152 scalar cases with
memory hooks, but refuses AVX. A separate host C corpus comparison matches all
11,583 v15 payloads, 655,268,704 bytes, against the independent reader. Original
instructions were not run on that entire corpus; structural rejections remain.

The guest runner only reads pinned text, copies four selected bodies into a
shared relocated window, and checks output/ABI with page guards and read-only
context. It has no inside-arena read trace. Static pinned-byte checks validate
relocation and the BMD caller's 32-byte public key. Original-address mapping
conflicted with runner allocations; that failed probe and Unicorn AVX failures
are retained. Guest run14, scalar/corpus reports and all test logs are ignored
under `evidence/client-lea-decode/`; earlier probe failures are under
`evidence/client-lea-key/`. Guest is shut down after verification.

The suite discovers 135 tests, 124 portable passes plus eleven private skips;
all 135 opt-in private checks pass. A clean source checkout is checked separately.
Next recover original record-loading/allocation paths or the actual hierarchy
matrix concatenate at `0x00cff83e`. Keep unknown prior dummy-slot state explicit;
a decoder result does not justify relaxing the parser or claiming rendering.

## Controlled hierarchy composition

Issue #33 / `codex/pose-concat` merged through PR #34 after macOS/Linux CI
run `38898823896`. It adds `mu_pose_concat` to record-math, reusing byte
storage helpers without changing cofactor/inverse behavior. Read
`research/pose-concat.md`. Original `0x00cff83e..0x00cfff3b` matches 5,176 controlled
RNE binary32 cases. A separately compiled input-snapshot variant fails 2,464.
Of 5,200 attempts, 24 leave the finite normal/zero domain and are recorded
separately. Initial NaN differences exposed incomplete emulator status reporting;
new instruction hooks inspect arithmetic results directly instead of trusting
MXCSR status alone. Raw failures, corrected report and REA are in ignored
`evidence/pose-concat/`. Standalone validation also verifies three selected
hierarchy call instructions. No live pose-buffer state or actual renderer is
claimed. Guest remains shut down; this check uses existing captured bytes.

Next recover rotation helper `0x00d00724` or bounded original record-loading /
allocation behavior. Native game source, simulation and services remain open.

## Rotation dispatch flag captured

Issue #35 / `codex/trig-state-capture` adds the fixed `trig-state` scope. Read
`research/client-trig-state.md`. The four-byte main-image flag at `0x0bdd1cc8`
repeats value 1 with digest `67abdd721024f0ff4e0b3f4c2fc13bc5bad42d0b7851d456d88d203d15aaa450`.
Restored text and every identity flag pass. An early attempt saves only an empty
incomplete manifest on the known packed hash; all four legacy modes repeat
run11 formats/digests. Transfer verification and raw results are ignored in
`evidence/trig-state-15/`; guest shut down cleanly.

Rotation candidate `0x00d00724` reads three floats scaled by captured 0.5, calls
float wrappers `0x009681bd`/`0x009fa223` three times each, and writes four floats.
REA in `rea-rotation.json` suggests Euler-to-quaternion behavior; no authored
source equivalence yet. Wrappers call `0x01985700`/`0x0198c4d0`, which test the
captured flag plus x87/MXCSR state. Next emulate with actual text/data/flag under
explicit FP settings, following actual trig code and stopping on unknown reads.
Fallbacks also reference `0x0bdcfbc8`, not yet captured. Do not assume a live path
from the flag alone or substitute host sine/cosine as proof. Full game recovery
remains incomplete. Suite:141 total,129portable/twelve private skips; all141
local integration pass. Original raw bytes stay local.

A private smoke probe now runs the full rotation candidate and its actual trig
helpers on three synthetic angle triples with flag 1, x87 PC53/RNE and MXCSR
`0x1f80`. All return, including zero input yielding `(0,0,0,1)`. It stops on any
read of uncaptured bytes in the flag's page; none occurred in those cases.
`evidence/trig-state-15/probe-rotation.py` and `rotation-probe.json` preserve this
lead. It is not an authored-source equivalence or complete ABI/access check.
The next concrete task is now C reconstruction plus a bounded comparison suite
using those actual helpers, without stubs. Do not count three smoke cases as a
validated quaternion implementation.

## Rotation conversion reconstructed

Issue #37 / `claude/rotation-reconstruct` (worktree
`~/Documents/mu-worktrees/rotation`) adds `mu_rotation_quaternion` and
`mu_rotation_quaternion_using` to record-math. It also adds
`scripts/validate_rotation.py` and `scripts/scan_trig_midpoints.c`. Read
`research/client-rotation.md`. The helper converts three binary32 angles to
the x,y,z,w quaternion of Rz(a2)·Ry(a1)·Rx(a0). Each half angle is rounded to
binary32, and products are rounded separately in the original order.

Unicorn runs the actual 411-byte body, both float wrappers and the actual
client trig entries without stubs. It uses captured flag 1, x87 `0x027f`,
MXCSR `0x1f80`, the full pinned text and the verified second section. Any other
read stops a case. All 8,012 SSE2-domain cases match bitwise, including arena,
ABI, ordered stores and bounded access checks. Another 2,816 alias/alignment
and 256 PC64/PC24/register/status variants also match. Wrong axis order fails
7,547, and binary64 products with one final rounding fail 3,460. Five
caller CALLs are verified statically.

The C uses host libm sine/cosine. The client SSE2 results differ from macOS
libm by one binary64 ULP in 718 of 48,072 calls. All agree after binary32
rounding, including 112 scanned host-midpoint candidates run with both signs in
every axis. Angles with |a| >= 180,224 and ±inf enter the x87 fallback, which
stops at uncaptured `0x0bdcfbc8`. NaN returns through it, but that path is not claimed.
Unicorn reports no MXCSR status bits. The first harness run aborted on that
NaN path; the cause is recorded in the finding.

Raw reports (`comparison-01-no-midpoints.json`, `comparison-02.json`), scanner
output, notes and test logs are ignored under `evidence/client-rotation/` in that
worktree. Its `evidence/` and `input/` entries otherwise symlink to the main
lab for read-only use. Portable: 147 discovered, 134 pass, 13 explicit skips.
Opt-in integration passes 142. Five installed-model checks need `MU_GAME_ROOT`
data, which was not available outside the CrossOver bottle and was not used.
No guest or CrossOver run.

Next: recover the BMD bone-track loop `0x012b42ae..0x012b4441`. Per action it fills
position (12×keys), rotation (12×keys) and 16×keys entries via `0x00d00724`.
Compare it against installed v12/v14 bone data before moving into pose-builder
interpolation at `0x012b5064`. Alternatively, reconstruct client SSE2 sine/cosine
`0x019a72f8`/`0x019acd58` exactly to remove the libm substitution. The
public-constant relationship must first be established against the private tables.

## Bone-track loop reconstructed

Issue #40 / `claude/bone-track-loop` (worktree `~/Documents/mu-worktrees/bone-tracks`)
adds `mu_bone_tracks_read` in `reconstructed/model-codec/bone_tracks.{c,h}`,
built as `libbonetracks` with record-math. It also adds
`scripts/validate_bone_tracks.py`. Read `research/client-bone-tracks.md`.
The loop `0x012b4225..0x012b4441` writes these bone fields:

* `+0x22`, the dummy flag, written first and tested from the record;
* for non-dummy bones only, the name at `+0x00`, the raw parent at `+0x20` and
  a track-array pointer at `+0x24`.

The track array has 12 bytes per action. Its three pointers lead to positions
(12 bytes/key), Euler rotations (12 bytes/key) and quaternions (16 bytes/key)
from `0x00d00724`. Each non-dummy bone makes 1+3×actions operator-new calls,
with saturating sizes. Zero counts still allocate 1-byte blocks. Nothing is
bounds-checked.

Unicorn runs the actual loop, memcpy `0x0194c200`, operator new/malloc and the
rotation/trig helpers. Only the HeapAlloc import (stub `0x7bc275e0`), the
uncaptured heap handle `0x0bdcfc10` and memcpy feature word `0x0bdcb284`
(values 0/1/2) are modeled. Every other uncaptured or undefined read stops a
case.

Results: 342 synthetic comparisons match. Installed models matching through the
existing readers: v12 180/180, v14 216/216 and v15 11,566/11,566 (17
reader-rejected v15 not run), totalling 4,759,146 rotations. An
eliding-zero-allocation control differs in 57 comparisons. Allocation failure
stops at uncaptured CRT state (`0x0bdcf8f0` new mode, TLS errno), as does a
beyond-SSE2 angle (`0x0bdcfbc8`).

The full report `comparison-v12-v14-v15.json` (SHA-256 `323e7c3f…dbbf`), its log
and the test logs are ignored under `evidence/client-bone-tracks/` in that
worktree. `model-recovery/verified-v14` there is a read-only symlink to the
main lab, made for the model-codec integration check. Portable: 155 discovered,
141 pass, 14 explicit skips. Opt-in integration with `MU_GAME_ROOT` (read-only
`runtime/client`) passes all 155. No guest, CrossOver or
main-checkout change.

Next: pose-builder interpolation at `0x012b5064`, which consumes these
per-action arrays (rotation calls at `0x012b53c9` and `0x012b53d8`). Use the
same harness boundaries, seeding the model from this loop's output. Alternatives:

* run the 17 rejected v15 files through the loop with a non-validating locator;
* compare the sibling plaintext reader's bone loop `0x012b35c7..0x012b37e3`
  against all 701 v10 models.

## Pose builder reconstructed

Issue #46 / `claude/pose-builder` (worktree `~/Documents/mu-worktrees/pose-builder`)
adds `mu_pose_build` in `reconstructed/model-codec/pose_builder.{c,h}`, built as
`libposebuilder` with the bone-track loop and record-math. Record-math gains
`mu_quaternion_compare`, `mu_quaternion_slerp[_using]`, `mu_quaternion_matrix`
and `mu_angle_matrix[_using]`. The validator is `scripts/validate_pose_builder.py`.
Read `research/client-pose-builder.md`.

The builder is thiscall on the model (eight stack arguments, `ret 0x20`). Per
non-dummy bone it takes q1/p1 from (prior action, prior frame) and q2/p2 from
(current action `+0xa8`, integer frame). It slerps by the frame fraction unless
all components agree within 0.001 (then it copies q1), and lerps positions.
Out-of-range frames reset to key 0 but keep the fraction. Bone 0 can lock x/y
to the current action's key 0, and special bone `+0x60` rebuilds its quaternions
from head-adjusted Euler angles. The quaternion goes to global `0x075a90d8+16*i`.
The matrix composes with the root global `0x078965ac` (rebuilt from model
angles unless keep-root) or with `output+parent*0x30`.

Every case first runs the actual bone-track loop; the builder then runs with all
client callees (compare/fabs, slerp/acos/sin, matrix helpers, rotation,
composition) and no stubs. Only the two uncaptured globals and caller memory
are modeled. Results: 483 synthetic calls, 1,822 direct helper calls and 47,833
installed calls on 180 v12, 216 v14 and 11,566 v15 models all match. Lerp differs
in 364 and modulo frame wrap in 60. Host-libm trig agrees after binary32
rounding in every observed call (binary64 differs by at most one ULP).
Zero-key actions read uninitialized 1-byte heap blocks; t beyond the SSE2
domain and far parents stop as characterization.

The report `comparison-v12-v14-v15.json` (SHA-256 `d93ceb8e…0615`), its log,
synthetic reports, disassembly listings and test logs are ignored under
`evidence/client-pose-builder/` in that worktree. `model-recovery/verified-v14`
there is a read-only symlink to the main lab. After rebasing onto the fast-x87
changes: portable 190 discovered, 175 pass, 15 explicit skips. Opt-in
integration with `MU_GAME_ROOT` (read-only `runtime/client`) passes all 190.
No guest, CrossOver or main-checkout change.

Next: trace the builder's callers (314 raw candidates) to recover how the
prior frame/action and keep-root flag are chosen per animation tick. Then
follow the output matrices and quaternion table into the skinning/renderer
consumer. Alternatives: the second builder `0x012bcffb` (action-0 only), the
17 rejected v15 files with a non-validating locator, or the v10 sibling loop.

## Skinning path reconstructed

Issue #53 / `claude/skinning-path` (worktree `~/Documents/mu-worktrees/skinning`)
adds:

* `mu_model_transform` and `mu_animation_tick` in
  `reconstructed/model-codec/skinning.{c,h}`, built as `libskinning` together
  with the pose builder, the bone-track loop and record-math;
* record-math vector helpers `mu_vector_rotate`, `mu_vector_transform` and
  `mu_vector_irotate`;
* `scripts/validate_skinning.py`, which runs the actual instructions;
* `scripts/client_render_static.py`, a static map of callers, import slots and
  GL order.

Read `research/client-skinning.md`.

Callers. All 314 raw builder candidates sync, in 105 functions:

* 300 write the shared bone buffer `0x06fce398`;
* 117 take frame, prior frame, prior action, angles and head angles from one
  object (`+0xd0`, `+0xd4`, `+0x2c`, `+0x164`, `+0x170`);
* 140 take a computed frame, 108 of them `object+0xd0` minus a local;
* 19 use `(int)frame - 1` as the prior;
* 12 are bind poses and 26 are other.

The tick `0x012b4dd3` has 91 candidates and is the prior-frame writer. When the
integer frame changes, `*prior_action = model+0xa8` and
`*prior_frame = old integer`. Keep-root calls (25) follow root setter
`0x012b7019`, which copies a parent bone matrix into root global `0x078965ac`
for attachments.

Skinning. The transform `0x012b5bde` is reached through wrapper `0x00966ea5`
with buffers vertices `0x078978a0`, normals `0x0812cce0` and light
`0x06fd0918`, at per-mesh strides `0x2bf20`/`0xea60`. Each vertex uses one bone,
with no blending. Normals are rotated only. Light is a clamped Lambert term and
also goes to a secondary table at `0x075a9ee8`.

Comparisons. The actual transform, tick and vector helpers run with no client
stubs. Installed models chain through the actual bone-track loop and actual
builder, and the transform reads the builder's real output window. Results:

* 903 direct helper calls, 226 synthetic transforms, 24 builder-chained
  synthetic models and 481 synthetic ticks match;
* installed v12 180, v14 216 and v15 11,566 transforms match, covering
  3,814,006 vertices and 3,988,165 normals, plus 35,871 installed ticks;
* the transposed-rotation, translated-normal, prior-every-tick and ignore-lock
  controls fail in 210, 223, 259 and 35 cases.

Draw. The mesh draw `0x012b8d1d` (wrapper `0x00966e4a`, 6,361 raw calls) was
not executed. Statically it sets cached GL state, binds the texture through
`0x0184acf6`, issues one `glBegin(GL_TRIANGLES)`, and per corner calls
glTexCoord2f, then glColor3fv or glColor4f, then glVertex3fv on the transform
output, then glEnd. The body `0x012bb35a` brackets the mesh draws with
glPushMatrix/glPopMatrix and makes no matrix call between them.

The import slots are named against Debian Wine `8.0~repack-4` i386 opengl32/glu32,
matching the guest. All 81 + 4 slots resolve, and the first slot equals the file's
only static import name. The `.deb` (`c992aad6…8d57`, matching the bookworm
`Packages` hash), the extracted DLLs, the report `comparison-v12-v14-v15.json`
(`4b225477…c036`), the static report `static-05.json` and the logs are ignored
under `evidence/client-skinning/`. A first run with v14 reader-rejected (unbuilt
`libmodulus`) is kept as `run-01-v14-unbuilt/`.

`model-recovery/verified-v14` in that worktree is an untracked read-only
symlink to the main lab; do not stage it. Portable: 209 discovered, 192 pass,
17 explicit skips. Opt-in integration with `MU_GAME_ROOT` (read-only
`runtime/client`) passes all 209. No guest, CrossOver or main-checkout change.

Next: execute the mesh draw `0x012b8d1d` and body `0x012bb35a` under Unicorn,
with the OPENGL32 IAT targets mapped to an authored GL-call recorder. Seed them
with the actual transform output on installed models, and compare against an
authored C emitter of the same GL stream (per-corner texcoord/colour/vertex,
state and binds). Alternatives:

* trace the action-change code that writes object `+0x2a`, `+0x2c` and `+0xd4`;
* identify the 24 immediate GL_TRIANGLE_FAN routines behind the profiled
  four-vertex fans;
* trace the main loop and frame cap.

## Frame loop and hot draw sites mapped

Issue #55 (CLIENT-FRAME-001), branch `claude/frame-loop`, worktree
`~/Documents/mu-worktrees/frameloop`. Read
[`research/client-frame-loop.md`](research/client-frame-loop.md). The work is
static; no client code ran and nothing was patched.

**Loop.** The WinMain loop uses `PeekMessageW(PM_REMOVE)`. When the queue is empty
it calls the scene dispatcher `0x01859d8a`. Scene states 3, 5 and 6 go to the frame
driver `0x01851d39`, state 4 to the loading screen and state 2 to the intro. The
frame driver works like this:

* `[0x0bdc5ec0]` accumulates elapsed time, and game logic runs once per 40 ms
  step (`0x01851d6b`, `0x01851f90`);
* GetTickCount at frame start is stored in `[0x0bdc5e64]`;
* the scene render is followed by SwapBuffers at `0x01852653`;
* if elapsed < 40, it calls `Sleep(40 - elapsed)` (`0x0185267a`) and sets elapsed to 40.

**Cap.** The cap is the immediates at `0x0185266b`, `0x0185266f` and `0x01852690`,
with the branch `7D 26` at `0x0185266c`. The 44-byte block has SHA-256
`37978e18…2e14`. It does not occur in the Themida-packed file, so the only way to
change it is an in-memory write after unpacking, for example from the owner's mugl
proxy at the first wglSwapBuffers, after verifying the block. The rendered-frame
counter `[0x0bdc5ebc]` has 225 readers and would speed up with the frame rate.
Logic and the wall-clock float `[0x06fce370]` would not. `IGC.dll` hooks the
function at `0x01851d5e` and `0x018526e7`.

**Draws.** The fans come from three places:

* the terrain renderer `0x016cd468`, which walks the frustum box in 4×4-tile
  blocks and emits one fan per tile per layer through `0x016cf46c` and friends,
  plus a grass quad;
* terrain decals `0x016cdd5f` (460 callers), one fan per covered tile;
* 2D helpers `0x0184d9bb`/`0x0184dcb1`/…, with 243 and 170 callers.

Quads are mostly the sprite routine `0x0184c39c` (433 calls in `0x0159123f`) and
effects. All 51 sites carry return addresses for runtime attribution.

**VBOs.** The calls go through data-import function-pointer slots
`0x01a7cb54..0x01a7cc14` (GLEW-style). There is no glBufferSubData name string.
The effect system streams two GL_STREAM_DRAW buffers:

* sprite: 144 B at object `0x01d1e2c8`, a whole-buffer update per draw;
* emitter: 144,000 B at `0x01d1e6f8`, an `n*144` prefix per draw;

each followed by `glDrawArrays(GL_QUADS)` with client arrays at offsets 0, 12 and 20,
stride 36.

**Checks.** `scripts/client_frame_static.py` takes about 30 s. Its report is
`evidence/client-frame/static-02.json` (`9627bb4f…0abe`, ignored), with the pinned
Wine DLLs extracted alongside. Portable: 218 discovered, 200 pass, 18 explicit
skips. The new private check passes with `MU_RECOVERY_INTEGRATION=1` and
`MU_GAME_ROOT=runtime/client`. The full opt-in suite was not rerun. No guest,
CrossOver bottle or main-checkout change.

**Next.**

* Add an opt-in glBegin return-address counter to mugl and map the counts through
  `static-02.json`. This settles the terrain/decal/UI split and attributes the
  unexplained glViewport/glOrtho and glActiveTexture calls (`IGC.dll` or the
  third-party renderer).
* Extend mugl's buffer orphaning to offset-0 prefix updates of the 144,000-byte
  effect buffer.
* If the owner wants a higher menu cap, prototype the verified in-memory write
  in a test bottle, not MuMatrix32.

## MAC-PERF-004 publication handoff

Issue #57 / `codex/mac-hotpatch`, worktree `~/Documents/mu-worktrees/mac-hotpatch`,
is stacked on OPEN PR #52 (`codex/mac-gl-batching`, base `d1c86a3`). The owned
scope is `mac-play/hotpatch`, `mumodes`, `machprof`, `automation`, generator/policy
tests, CI cross-build and the shared performance/status/roadmap/evidence notes.
This publishes Claude's saved v7.0 work. No main.exe or Wine process was started,
stopped, attached to or patched, and neither MuMatrix32 nor its C:\MuTheMatrix /
C:\mutools directories were modified. Default setup remains PR #52's proxy.

Read `research/mac-performance.md`, MAC-PERF-004, and
`../mac-play/hotpatch/README.md`. `source-provenance.json` pins the pre-packaging
authored sources. v7.0 mugl is `c8397771…b6a1`; xform is `cce0902f…c624`.
The owner-supplied pristine memory dump remains `/tmp/pristine.bin`, SHA-256
`6e7957c9af8685f5a5fb14008131eab50470d40d2e6128397d5795a88160bfd4`.
The source generator derives objdump listings from that dump, verifies identities
and reproduces exactly nine helper patches, 18,583 inline sites and 50,977
peepholes. The old cached `/tmp/calls.txt` differs from the derived call list by
one nonmatching target; both listing identities are pinned and yield identical
final tables. Original templates become length/hash metadata. The xform original
prologue and all original/replacement tables are generated under ignored
`mac-play/hotpatch/build/private`, never committed or uploaded.

Actual local checks: `make test PYTHON=tools/.venv/bin/python` discovers 208 tests,
193 pass and fifteen explicitly skip private inputs. `make mac-hotpatch` builds
the compile-only proxy, mscoree mode proxy, mesh/call benchmarks and muinput.
`make -C mac-play/hotpatch private` cross-builds the private proxy and hptest;
neither was executed. `make -C mac-play/machprof` compiles all three x86_64 Mach
tools without signing/attachment. All five automation scripts pass zsh parsing.
The final staged publication audit and diff check pass. Existing compiler warnings
are an unused legacy extra-mode installer and compact hptest indentation.
Fresh private tables match all eighteen original/replacement helper arrays and
both final v7.0 tables byte for byte. Full generation also succeeds using only
`--dump`, with locally derived listings. Verification logs and reference headers
are ignored under `runtime/mac-hotpatch/`.

Claude's prior 900k/helper comparison, >1M live skinning comparison, hunting FPS,
6.4 ms GL timing, 44.8% mesh attribution and Rosetta behavior are supplied reports,
not rerun measurements here. Raw measurement logs were not acquired. The
performance finding keeps those claims separate from actual publication checks.
The pinned v7.0 source does not contain an identifiable frame-cap patch installer;
the 25 FPS/40 ms cap remains a reported condition and the merged frame-loop
analysis is linked. Flags-dead analysis remains heuristic and full EFLAGS/access
identity is unverified. Broad GL equivalence and Windows-native behavior remain
unverified. Anti-cheat variants are a plan only.

Review the PR and its macOS/Linux CI before integration. Do not merge the child
while #52 is open without preserving that dependency. No independent reviewer
approval is supplied by this implementation task. Next performance task, under
separate authorization, is an original-vs-C mesh draw comparison at
`0x012b8d1d..0x012bb35a` before measuring speed. Use EBP walks, retain the old
stack-scan misattribution, and disable AeDebug only in disposable test bottles
before crash-prone probes. The original process-killing restart helper and later
meshdraw experiment remain omitted. Login/movement scripts select an explicit
test bottle and refuse MuMatrix32; login reads the password from Keychain.

After #58 was merged into `codex/mac-gl-batching` and `main` (with #54/#56) was merged in, the combined tree discovers 236 tests: 218 pass and 18 explicitly skip private inputs (`make test PYTHON=tools/.venv/bin/python`). The earlier counts above are per-PR snapshots.

## MAC-PERF-005 publication handoff

Issue #59 / `claude/mac-meshdraw`, worktree `~/Documents/mu-worktrees/mac-meshdraw`,
based on main `f629ef9` (PR #52/#58 merged). The owned scope is `mac-play/hotpatch`
(`meshdraw.c`, v7.1 `mugl.c`, `meshdraw-notes.md`, generator/targets/provenance),
`mac-play/diagnostics/glstride.c`, the audit and tests, and the shared
performance/status/roadmap/evidence/notices notes. This publishes Claude's saved v7.1
work. No main.exe or Wine process was started, stopped, attached to or patched, and
neither MuMatrix32 nor its C:\MuTheMatrix / C:\mutools directories were modified. Default
setup remains PR #52's proxy. `~/Documents/mu-mac-tools` was read only.

Read `research/mac-performance.md`, MAC-PERF-005, and `../mac-play/hotpatch/README.md`
and `meshdraw-notes.md`. `source-provenance.json` pins `mugl_v71.c` (`62798456...`),
`meshdraw_v71.c` (`ac3f115b...`) and `glstride.c` (`f8393505...`); `xform.c` is
unchanged from v7.0. The three patch-site original byte sequences that `meshdraw_v71.c`
embedded (7/6/10 bytes at `0x012ba899`, `0x012b968c`, `0x012b8d1d`) are now length plus
SHA-256 in `targets.json` (`meshdraw_sites`); `generate.py` verifies the owner-supplied
dump `/tmp/pristine.bin` (SHA-256 `6e7957c9...160bfd4`) against them and writes an
ignored `build/private/meshdraw-orig.h`, and the synthetic header is zeros. The audit
and tests reject that header name as a source file.

Actual local checks: `make test PYTHON=tools/.venv/bin/python` discovers 241 tests,
223 pass and eighteen skip private inputs (five tests are new). `make mac-hotpatch
mac-diagnostics` cross-builds the compile-only proxy and `glstride.exe`. Full private
generation from the dump reproduces nine helpers, 18,583 inline sites, 50,977
peepholes and the three new digests, and `make -C mac-play/hotpatch private` builds.
That private DLL, rebuilt at image base `0x69680000`, has the same size as Claude's
`mugl-v71.dll` and an identical disassembly modulo data addresses. Nothing was
executed or installed. `local_integration_passed` in the evidence index is the earlier
value; private integration was not rerun for this change.

Everything about runtime behavior (zero verification mismatches, framebuffer-hash
equality, fps and work-time tables, the frame-pointer profile, the Winsock 10049
reconnect during a known outage) is Claude's supplied report. Notable record points:
the spawn "full v7.1" row is mask 4015 (not the 7599 default), the 8111 mask (adds
strided arrays) measured lower fps than 4015, and the spawn rows include the bit-512
timer. The v7.0 44.8% attribution is withdrawn: mugl had no frame pointers. Not
established: the `0x20`/`0x200000` vertex paths, mode `0x8000`, inputs outside the
reported sessions, EFLAGS or access-trace equivalence, Windows-native behavior,
anti-cheat and server compatibility.

Next work: no single dominant hotspot is reported. The remaining main.exe self time is
spread over indirect/vtable calls (mostly from `0x00ea27ac`), `0x012bc07a`,
`0x016d197d`, terrain decals `0x016cdd5f` and `0x016cc9e2`. Frame rate is bounded by
the 40 ms logic step, so any further gain needs the logic step itself (see the
frame-loop finding) rather than more render-path work. Dual anti-cheat builds remain a
plan only. Use disposable bottles for any crash-prone probe.

## MAC-PERF-006 publication handoff

Issue #61 / `claude/mac-pacing-v72`, worktree `~/Documents/mu-worktrees/mac-pacing`, based on
main `5b96c26` (PR #60 merged). The owned scope is `mac-play/hotpatch/mugl.c` (v7.1 to v7.2
diff only), the v7.2 section of `mac-play/hotpatch/meshdraw-notes.md` and the README,
`source-provenance.json`, the new `PrecisePacingTests` and the performance/status/roadmap/
evidence/notices notes. A separate PR (reproducible Mac setup kit under `mac-play/`) does not
touch these files. No main.exe or Wine process was started, stopped, attached to or patched,
and neither MuMatrix32 nor MuMatrixKit was modified. `~/Documents/mu-mac-tools` was read only.

Read `research/mac-performance.md`, MAC-PERF-006, and `meshdraw-notes.md` (v7.2). Cause as
reported from Claude's diagnostic builds: with the game not frontmost, macOS coalesces the
timers behind Wine's `Sleep` (7-14 ms took 17-45 ms), which made bit-1024 pacing jitter and
fall to 17-22 fps. The inactive-window throttle (`[0x01cf0fc0]` stayed 1; the inactive branch
at `0x0120ee34` has no Sleep) and double sleeping (only the driver's Sleep, return `0x01852680`)
were ruled out. The fix waits on a waitable timer to the exact 40 ms deadline, with a `Sleep`
fallback, and routes any other render-thread `Sleep(ms>0)` through it. `Sleep(0)` and other
threads are unchanged, and there are no GL changes or new patch sites. `source-provenance.json`
pins `mugl_v72.c` (`9eeed0c5...138dbdfd`) and marks `mugl_v71.c` superseded.

Actual local checks: `make test PYTHON=tools/.venv/bin/python` discovers 245 tests, 227
pass and eighteen skip private inputs (four are new); `make mugl mac-diagnostics mac-hotpatch`
cross-builds; the audit passes. The new code was compiled, not executed, because it only
runs inside a private build in the game. All fps, histogram and overshoot figures are Claude's
supplied report (spawn, about 28-29 ms of work: background 19.3-21.1 fps with pacing off,
about 24.5 with v7.1 and half the frames late, 25.00 over 140 s with v7.2; frontmost 25.0,
25.0 and 24.95).

Not established: other hosts, macOS versions or power states, runs beyond the reported 140 s,
login and character-select numbers, Windows-native behavior, anti-cheat and server
compatibility. Next work: no new performance lever is reported; 25 fps remains the fixed
40 ms logic step. A 6-minute background hunting-spot soak is now reported (see
`research/mac-performance.md`); an hour-long, heavier-load run would still extend the evidence.

## MAC-KIT-001 publication handoff

Issue #63 / `claude/mac-setup-kit`, worktree `~/Documents/mu-worktrees/mac-setup-kit`, stacked after
PR #62 (MAC-PERF-006), based on main `6f4344d`. The owned scope is the new `mac-play/installer/`
(`setup-mu-mac.sh`, `verify-mu-mac.sh`, `play-mu.sh`, `lib/mukit.sh`, `registry/mu-mac.reg`, `README.md`,
`tests/`), `tests/test_mac_installer.py`, the `make test` hook, `.gitignore`/`.gitattributes` entries and
the shared notes. `~/Documents/mu-mac-tools` was read only. No main.exe, Wine process or game was
started and neither MuMatrix32 nor MuMatrixKit was touched; the only bottle name used for the
real-CrossOver dry run (`MuRepoDryRun`) does not exist and was not created.

Read `research/mac-crossover-32bit.md` (MAC-KIT-001) and `../mac-play/installer/README.md`. Differences
from the owner's live-validated local copy: paths now come from the repository (`mac-play/cxwine`,
`cxwineserver`, `mumodes`, `mugl`, `hotpatch`) or parameters (`--dll-dir`, `--dotnet-installer`,
`--helpers-dir`, `--timewalker-dir`, `--mugl-build`); `--dll-source build` is the default and builds the
public batching-only mugl (DevModeIndex capped at 2); `--dll-source current` and `--mugl-repo` are gone;
`play-mu.sh` is part of the kit and defaults to plain Rosetta; the pins stay in `lib/mukit.sh` with
`MUKIT_*_SHA256` environment overrides that exist only for the synthetic tests. Account ID and Keychain
item names appear nowhere in the tree; autologin uses the existing `MU_ACCOUNT`/`MU_KEYCHAIN_SERVICE`.
Prebuilt DLL hashes (v7.2 `e37cf5d5...`, v7.1 `85a8e3b6...`, v7.0 `c06534df...`, mscoree `6f2d2ace...`)
were checked against the owner's files read-only.

Actual local checks: `make test PYTHON=tools/.venv/bin/python` discovers 254 tests (236 pass, 18 explicit
private skips; the 9 new tests are `tests/test_mac_installer.py`) and runs the 180-check shell suite;
the same suite passed 180/180 in an Ubuntu 24.04 container with MinGW, python3 and zsh, and 166/166
without them (those checks skipped); `python3 scripts/audit_repository.py`; `--dry-run` of the setup
against the real CrossOver tree and a synthetic client folder. Not run: a live bottle build, the
repository shims under winetricks, the new default build path's DLL in the game, any game start.

Next work: on a throwaway bottle (never MuMatrix32 or MuMatrixKit, game not running), run the kit once
with `--dll-source build` and once with `--dll-source prebuilt --dll-dir ...`, record timings and the
verify output, and delete the bottle; then decide whether to retire the older setup or merge the two.
The `MonitorCheck.exe` pre-launch display probe in `start-launcher.sh` is not in the kit. Fast-x87
and the anti-cheat variants stay TODO hooks. Use disposable bottles for any crash-prone probe.


## MAC-KIT-001 live-validation follow-up

Branch `claude/kit-live-fixes`, worktree `~/Documents/mu-worktrees/kit-live`, based on main `0c1b5c8` (PR #64).
The repository version of the kit was run live in a throwaway bottle (all three DLL paths and `--fast-x87`, to
the server-select screen; not logged in because the account was in use elsewhere; MuMatrix32 and its processes
untouched). It found five bugs, fixed here: PE timestamps made builds non-reproducible
(`--no-insert-timestamp` in the kit's mscoree command and `mac-play/mugl/Makefile`), `--dll-dir` demanded
`mscoree.dll` (the public proxy is now built when missing, and a failed DLL copy aborts), a test depended on
a real private build in the checkout (`MUKIT_PRIVATE_BUILD_DIR`), `play-mu.sh` shared one log between bottles
(`MuTheMatrix-<bottle>.log`), and verify ignored the launcher's fast-x87 setting. Results and timings are in
the kit README ("Live validation of the repository version") and `research/mac-crossover-32bit.md`; the shell
suite is 190 checks. The pre-existing README-wording test was updated to the new status text. Also recorded
in `research/mac-performance.md` (MAC-PERF-006): a reported 6-minute background soak with v7.2.

Next: log in with a kit-built bottle and measure in-world fps against MuMatrix32 once the account is free;
run a long (an hour or more) session, with heavier monster load, to settle stability; decide whether to
retire `setup-crossover-32bit.sh`. The private hotpatch build output stays in the ignored
`mac-play/hotpatch/build/private/` and must never be committed.

## Native model viewer (NATIVE-VIEW-001)

Branch `claude/native-viewer`, worktree `~/Documents/mu-worktrees/native-viewer`. Read
[`research/native-viewer.md`](research/native-viewer.md) and [`../native/README.md`](../native/README.md).

**Built.**

* `native/core`: portable C. It covers the checked BMD loader, client-memory layout around `mu_bone_tracks_read`/`mu_animation_tick`/`mu_pose_build`/`mu_model_transform`, the `mu_meshdraw` corner-loop port, the scene driver, the software rasterizer, textures, PNG and SHA-256.
* `native/viewer`: SDL2 + GL 2.1 window and CGL headless rendering.
* `native/tools/mu_render.c`: headless CLI with the `info`, `dump`, `corners`, `render`, `image` and `scan` commands.
* `native/tests`: fixtures, the golden reference harness, the independent mesh-draw model and 16 tests (12 portable, 4 private).

**Checks.**

* `make test PYTHON=tools/.venv/bin/python` passes on macOS: 270 discovered, 22 explicit skips.
* `native/tests` also passes in Ubuntu 24.04 arm64 and x86_64 containers, with identical pinned render hashes. The harness script and logs are in `~/Documents/mu-mac-tools/native/scratch/`.
* The private checks pass with `MU_RECOVERY_INTEGRATION=1 MU_GAME_ROOT=<MuTheMatrix>`. The full golden run used `MU_NATIVE_GOLDEN_PER_VERSION=100000 MU_NATIVE_GOLDEN_MAX_VERTICES=100000` (466 s). The corpus scan takes 6 s.
* Local renders of installed models are in `~/Documents/mu-mac-tools/native/renders/` and are never committed.

**CI.** The macOS job installs `sdl2` and `jpeg-turbo` and builds the window viewer with `make native-viewer`. Linux installs `libjpeg-dev`. The viewer test skips without `sdl2-config`.

**Next.**

* Execute the mesh draw and body under Unicorn with a GL recorder. Compare against `mu_meshdraw` and `mu_scene_draw_model` to settle mode selection, state, texture parameters and the `0x072acfd8` normal-texcoord writer.
* Then do character assembly (Player skeleton, parts, keep-root attachments), followed by terrain.

No game, CrossOver bottle or registry was touched.

## Post-merge review of PR #66 (NATIVE-VIEW-001)

PR #66 was opened at 18:09:58Z and merged at 18:11:39Z without the independent review that
`CONTRIBUTING.md` asks for, and with no tracking issue. Its PR and push CI were green before the merge.
The review is a comment on PR #66. Branch `claude/native-viewer-review-fixes` fixes what it found:

* `native/core/mu_image.c`: a TGA whose image-ID length (byte 0) runs past the end of the data made
  the uncompressed path read past the buffer, because the unsigned `size - offset` wrapped.
  AddressSanitizer showed it with an 18-byte file, and `mu-render image` returned success with garbage
  pixels. The decoder now rejects the file. A regression test covers raw and RLE files, plain and
  OZT-wrapped, and fails without the fix.
* The golden tests now assert equal mesh counts before comparing meshes with `zip()`.
* `THIRD_PARTY_NOTICES.md` now lists SDL2 (zlib) and libjpeg-turbo (IJG/BSD-3/zlib, IJG
  acknowledgement for binary distribution). Both are linked, not vendored.
* `research/native-viewer.md`, `roadmap.md` and `status.md` now separate CI-verified claims from
  reported single-run ones: the full private corpus, installed textures and GL counts, Linux arm64
  hashes, and the authorship independence of the mesh-draw model.

**Checks run in the review:**

* `make test`: 270 run, 22 skips, all OK on macOS.
* A clean `make -C native all viewer` builds with `-Werror` and no warnings.
* `python3 scripts/audit_repository.py`: 0 rejected.
* An ASan/UBSan build passed the portable native tests, apart from two environment-only cases: the
  ctypes dylib, and the CGL viewer, which hangs under ASan. It also passed about 2,200 mutated BMD
  inputs and 4,000 mutated TGA/BMP/OZT/OZB inputs. The TGA bug above was its only finding.
* Private tests were not re-run, because the review touched no game data.

**Next:** unchanged from the NATIVE-VIEW-001 entry above.

## Character assembly (NATIVE-CHAR-001)

Branch `claude/native-char`, worktree `~/Documents/mu-worktrees/native-char`. Read
[`research/native-character.md`](research/native-character.md) and [`../native/README.md`](../native/README.md).

**Built.**

* `reconstructed/model-codec/character.{c,h}` (`libcharacter`): the rotation position `0x012b7019`, the transform position `0x012b6ef1`, and the class tier, skin index and tier-2 skip helpers; also the part type/file table of the loader `0x01830aa6`.
* `scripts/validate_character.py`: Unicorn comparison of those routines and the loader loop, plus installed `Player.bmd` → part and `Player.bmd` → item chains through the actual bone-track loop, builder, root setter and transform.
* `native/core/mu_character.*`, `mu_model` share/keep-root/rotation-position hooks, `mu-render character|chardump`, character options and the viewer's character mode.
* Tests: `reconstructed/model-codec/test_character.py` (4 portable, 1 private) and `native/tests/test_native_character.py` with `character_reference.py` (4 portable, 2 private).

**Checks.**

* The validator passes everything (ignored report `evidence/native-char/character-full-02.json`, `bca220a3…94ae3b`, 90 s).
* The private character tests pass with `MU_RECOVERY_INTEGRATION=1 MU_GAME_ROOT=…`.
* Local renders are in `~/Documents/mu-mac-tools/native/renders/char/` and are never committed.

**Next.**

* Trace the player stand/attack action selection, to name actions.
* Implement the world-path weapon specifics of `0x012bd910`: item lighting flag 0, draw `0x0176ce74`, per-part animation state, and the attribute 0x54/0x59/0x72 branches.
* Add the safe-zone back-carry matrices of `0x0139db9a`.
* Executing `0x0139be7a` under Unicorn with recorded draw calls would settle the render-flow reading.

No game, CrossOver bottle or registry was touched.
