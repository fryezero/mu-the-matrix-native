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
| CAP-001 | Validate the read-only capture helper on Windows x64 with the pinned client | Exact target hash, readable manifest, region hashes, explicit failures and actual Windows test notes | Windows reference machine, unavailable; preserved as an optional validation path |
| CAP-002 | Implemented: bounded map and first reconstructed copy behavior | REA record, eleven nearby routines mapped, 393 instruction comparisons, negative control | PR #8 merged after passing macOS/Linux CI |
| CLIENT-MEMORY-002 | Implemented: clear64 and bounded reference search | 768 scalar/SSE/DF comparisons; no direct/absolute references found in selected inputs | PR #10 merged after passing macOS/Linux CI |
| CLIENT-MAP-001 | Implemented: first 64 KiB candidate/reference map | 803 labeled candidates, 31-entry REA comparison, selected record-operation dossier | PR #13 merged after passing macOS/Linux CI |
| CLIENT-MATH-001 | Implemented: capture selected image constants | Fixed 76-byte scope, pinned restored text before/after, early refusal and legacy regression | PR #14 merged after passing macOS/Linux CI |
| CLIENT-MATH-002 | Implemented: controlled cofactor/reciprocal source | 1,680 helper + 1,050 wrapper comparisons, alias negative control and PC24 boundary | PR #16 merged after passing macOS/Linux CI |
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
