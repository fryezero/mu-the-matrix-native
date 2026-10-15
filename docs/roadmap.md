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
| CAP-001 | Validate the read-only capture helper on Windows x64 with the pinned client | Exact target hash, readable manifest, region hashes, explicit failures and actual Windows test notes | Windows reference machine |
| CAP-002 | Validate and import a captured image into native analysis | File hashes, VA mappings, observed restored-code coverage, unresolved regions | CAP-001 and a private capture |
| MODEL-014 | Investigate BMD v14 envelopes | Primary-source-backed decoder plus full structural checks and malformed-input tests | Matching local files; source lead in model report |
| MODEL-EDGE | Explain the 17 rejected v15 records | Case-specific evidence and tests; preserve unresolved semantics rather than broad acceptance | Matching local files |
| TERRAIN-001 | Explain three rejected terrain images and terrain formats | Exact layouts and bounded parsers checked against original files | Matching local files |
| EFFECT-001 | Recover runtime interpretation of effect JSON | Source/runtime links for enum meanings, curves, blending and transforms | Relevant code or runtime evidence |

## Next after a valid capture

Inventory restored functions and imports. Pick one bounded behavior with a usable reference and reconstruct it through tests. Expand the function/type map and subsystem boundaries only as evidence supports them. Track initialization and companion-library behavior separately from gameplay.

## Later, intentionally unspecified

Whole-client reconstruction, faithful renderer/input/audio modules, network/service integration, platform separation, native macOS graphics/windowing choices, packaging and end-to-end gameplay verification. These depend on code that has not yet been recovered.

## Coordinating agents

Use issue IDs matching these task IDs, claim a scope before editing, and name the owned directories and output paths. Independent tasks can run on separate branches/worktrees. Dependent tasks should consume a reviewed interface or evidence result. A PR closes a task only when its completion evidence is present; partial research belongs in a handoff with open questions.
