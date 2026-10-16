# Roadmap and work queue

## Destination and acceptance gates

1. Understand the exact Windows client with source-bound code and data evidence.
2. Reconstruct editable modules that build reproducibly and match observed behavior.
3. Demonstrate the reconstructed client behaving correctly against the expected services and data.
4. Separate confirmed platform dependencies and implement a native macOS client.
5. Verify representative gameplay, state persistence interactions, input, rendering/audio, installation and restart on macOS.

The later macOS goal does not replace exact-version source recovery. No completion date or guarantee of full recovery is established by the current artifacts. An offline replacement server is not assumed to be requested.

## Ready tasks

| ID | Work | Completion evidence | Dependencies |
|---|---|---|---|
| RUNTIME-X86 | Implemented: full x86 Debian/Wine runtime on the Mac | Exact client startup, GL/bitness checks, egress blocked, labeled capture limits | PR #6 merged; continue code mapping under CAP-002 |
| MAC-CROSSOVER-001 | Implemented: original-launcher setup in a new win10/win32 bottle | Authored isolated setup, builtin WIC/GDI+, cloned-skin workaround, 8/8 synthetic image steps, 65.8-second launcher survival, test bottle deleted | Issue #39; GAME START and gameplay require owner validation; native acceptance gates unchanged |
| MAC-PERF-001 | Implemented: opt-in fast x87 cache build and launcher path | Pinned external commit, matching synthetic checksum, activation log, authored FP/GL probes, preserved idle/display guards and tested fallback | Issue #45; actual patched launcher-to-main forwarding, in-world FPS, precision and anti-cheat compatibility remain unverified |
| CAP-001 | Validate the read-only capture helper on Windows x64 with the pinned client | Exact target hash, readable manifest, region hashes, explicit failures and actual Windows test notes | Windows reference machine, unavailable; preserved as an optional validation path |
| CAP-002 | Implemented: bounded map and first reconstructed copy behavior | REA record, eleven nearby routines mapped, 393 instruction comparisons, negative control | PR #8 merged after passing macOS/Linux CI |
| CLIENT-MEMORY-002 | Implemented: clear64 and bounded reference search | 768 scalar/SSE/DF comparisons; no direct/absolute references found in selected inputs | PR #10 merged after passing macOS/Linux CI |
| CLIENT-MAP-001 | Implemented: first 64 KiB candidate/reference map | 803 labeled candidates, 31-entry REA comparison, selected record-operation dossier | PR #13 merged after passing macOS/Linux CI |
| CLIENT-MATH-001 | Implemented: capture selected image constants | Fixed 76-byte scope, pinned restored text before/after, early refusal and legacy regression | PR #14 merged after passing macOS/Linux CI |
| CLIENT-MATH-002 | Implemented: controlled cofactor/reciprocal source | 1,680 helper + 1,050 wrapper comparisons, alias negative control and PC24 boundary | PR #16 merged after passing macOS/Linux CI |
| CLIENT-DATA-001 | Implemented: fixed second image section | Repeated digest, early refusal, identity checks and legacy scope regression | PR #20 merged; next issue #21 validates model-loader references |
| CLIENT-LOADER-001 | Implemented: BMD call path and v12 source | Three bounded REA dossiers; 4,048 synthetic and 180 installed instruction comparisons; 312 negative-control failures | PR #23 merged after passing macOS/Linux CI |
| CLIENT-DISPATCH-001 | Implemented: observed v15 jump targets | Fixed eight-byte scope, repeat/legacy digests, early refusal; targets inside pinned text | PR #26 merged after passing macOS/Linux CI |
| MODEL-HIERARCHY-001 | Implemented: selected bone/pose slot flow | Exact field/control-flow checks; unknown prior-state dependency preserved | PRs #25 and #28 merged; strict acceptance unchanged |
| CLIENT-LEA-KEY-001 | Implemented: observed v15 key setup | 1,320 actual-instruction cases; 1,248 wrong-order failures; public vectors | PR #30 merged; ECB result follows under #31 |
| CLIENT-LEA-DECODE-001 | Implemented: batch ECB source | 12,960 actual-code guest cases; 1,152 scalar cases; 11,583 independent-reader payload matches | PR #32 merged; complete model loading remains open |
| CLIENT-POSE-MATH-001 | Implemented: controlled 3x4 composition | 5,176 actual-instruction matches; 24 out-of-domain attempts; 2,464 snapshot failures | PR #34 merged; original live pose/FP state remains open |
| CLIENT-TRIG-STATE-001 | Implemented: selected math dispatch flag capture | Four-byte repeat, early refusal, all legacy scopes unchanged | Issue #35, PR #36 merged; consumed by CLIENT-ROTATION-001 |
| CLIENT-ROTATION-001 | Implemented: Euler-to-quaternion helper `0x00d00724` | 8,012 actual-instruction matches with real client trig, 2,816 alias/alignment, 256 FP-state variants; 7,547 wrong-axis-order failures | Issue #37, PR #38 merged; client SSE2 trig source, out-of-domain/non-finite angles and live caller FP state open |
| CLIENT-BONE-TRACK-001 | Implemented: BMD bone-track loop `0x012b4225..0x012b4441` | 342 synthetic and 11,962 installed v12/v14/v15 actual-instruction matches (4,759,146 rotations, no client stubs); zero-allocation-eliding control fails 57 | Issue #40; allocation failure, real heap/memcpy feature state, 17 rejected v15 files and pose-builder interpolation `0x012b5064` open |
| MODEL-014 | Implemented: all 216 BMD v14 files decode and parse | 91 synthetic oracle vectors, full corpus comparison, source-bound research | PR #4 merged after passing macOS/Linux CI |
| MODEL-EDGE | Field diagnosis implemented; recover client handling of the 17 rejected v15 records | Exact field offsets, 17 native/Python matches; preserve unsupported semantics | Issue #17 diagnoses fields; original client model/transform code still needed |
| TERRAIN-001 | Explain three rejected terrain images and terrain formats | Exact layouts and bounded parsers checked against original files | Matching local files |
| EFFECT-001 | Recover runtime interpretation of effect JSON | Source/runtime links for enum meanings, curves, blending and transforms | Relevant code or runtime evidence |

## Next after a valid capture

Inventory restored functions and imports. Pick one bounded behavior with a usable reference and reconstruct it through tests. Expand the function/type map and subsystem boundaries only as evidence supports them. Track initialization and companion-library behavior separately from gameplay.

## Later, intentionally unspecified

Whole-client reconstruction, faithful renderer/input/audio modules, network/service integration, platform separation, native macOS graphics/windowing choices, packaging and end-to-end gameplay verification. These depend on code that has not yet been recovered.

## Coordinating agents

Use issue IDs matching these task IDs, claim a scope before editing, and name the owned directories and output paths. Independent tasks can run on separate branches/worktrees. Dependent tasks should consume a reviewed interface or evidence result. A PR closes a task only when its completion evidence is present; partial research belongs in a handoff with open questions.
