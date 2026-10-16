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

Issue #15 is implemented on `codex/client-record-math`. Read `research/record-math.md` and the module README. Actual helper/wrapper bytes and captured data match authored C in 1,680 cofactor and 1,050 inverse cases under PC53/RNE masked x87 state with an empty stack. A translation snapshot replacement fails 16 alias cases; PC24 differs in 1,471 comparisons. Evidence JSON and REA dossier stay ignored. Full arena, stack/register effects, control state and bounded accesses are checked. Original FP state, type/callers, NaN/trap/status and general underflow domains remain unverified. Tests discover 88 cases: 81 portable pass with seven private skips; all 88 local integration pass. Next recover genuine caller/type context or original FP-state evidence before widening the model.
