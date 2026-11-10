# RENDER-WORLDS-INNER-001

Implementation checkpoint, checks in progress. Branch `codex/render-worlds-inner-001`, from origin/main
`ff8e0543`. Owned files: `reconstructed/objects/world_inner_visual.*`, the object-runtime seam, new validator
and synthetic tests. Shared Makefile and validator registry changes are added lines only. Input links point
at the main checkout and are not committed. Installed apps and live clients are untouched.

[Research, addresses, call table and explicit consumer limits](../research/client-worlds-inner.md).

Done: complete authored call producers for Kanturu 0x00e75089 in 37/40 and the Blood Castle inline switch
0x017fc023 in 11..17/52; bounded original comparison; native emitters and extra mesh adapter; portable production
host. Small comparisons exposed and corrected pulse/light constants. The production host passes.

Left: full original counts and changed mutants once, affected suites/validators, reduced private native tests,
render comparison and one default byte-identity sweep, final self-review/docs/PR/ready line, cleanup.

## Verification checkpoint

Merged origin/main `a2ad8814` as `2145b9b7`; the validator-registry append conflict retained both this lane's row
and ACTORS-001's row. Compiled inputs have not changed since that merge.

| Check | Result | Wall |
|---|---|---|
| Build from merged main, `nice -n 10 make -j4` | Pass | 11.25 s |
| `make -C native -j4 build/mu-world` | Pass | 4.77 s |
| Full original call comparison without mutants | Four families, 4,000 cases, zero mismatches/stops | 2.09 s |
| `validate_worlds_inner`, mutants once, at `2145b9b7` | 4,000 cases, zero mismatches/stops; 33/33 compiled mutants detected, minimum eight detections | 156.0 s |
| Portable production host | Blood Castle world/model/bone gates and counter; Kanturu effect, joint, mesh order and explicit refusals | 1.14 s |
| Portable new object module | Two passed, one private skip | 0.24 s |

The current merged-main affected run selects 61 validator rows, including symbol fallbacks and ACTORS-001's
new row. It is in progress. Portable selection is 149 work items. Private native/tests exceeds 40 items:
**8d reduced**, run the newly added native module with the canonical private env.

Before outputs were taken once from `ff8e0543`: DATA-ACQ-002 32 views, 66.85 s; October 22 14 views, 20.39 s;
affected capture clocks, world 40 2.52 s and world 37 3.04 s. The first October manifest attempt used obsolete
local paths and failed before rendering; correcting those paths produced the recorded baseline. After comparisons
and synthetic Blood Castle views are pending. All bulk outputs will be deleted before handoff.

## Adapter review fix

The first affected run passed all 61 rows at `2145b9b7`, 685.61 s wall, with 1,008,213 reported cases;
`validate_worlds_o` has no case-count field in its runner row. Portable affected checks at `bc4c8f0b` passed
1,598 tests, 1,328 passed / 270 skipped, zero failures/errors, 446.11 s including selection, 328.0 s test wall.

Self-review found a hidden-object edge: after refusing the type-0x60 RGBA extra mesh, its two StreamMesh events
alone could bypass RenderObject's hidden skip. The new host assertion reproduced it, 1.07 s. The adapter now
requires a BODY or MESH event to bypass that skip. The expanded host also covers accepted hidden RGB and Chrome
passes; it passes with `private-env.sh`, 1.30 s. This is the **8d reduced** private native module, one test.
Final build after the fix passes, 10.54 s. The authored producer and all 33 mutant targets are unchanged.
Merged latest origin/main `9d6ce467` as `652ec5c9`; docs only, no additional compiled inputs. Follow-up selection
from `bc4c8f0b`, final renders and audit are pending.
