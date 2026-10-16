# Continue from here

Read `status.md`, then choose a task from `roadmap.md`. Gameplay recovery needs runtime evidence. The user no longer has a Windows PC available, so do not make access to one a prerequisite for the next task. The full x86 Linux/Wine guest on this Mac has now restored readable client code; start with `research/restored-client-text.md` and `../runtime-linux/README.md`.

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
