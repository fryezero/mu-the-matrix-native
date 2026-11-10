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

The mapped-texture host case also reproduced a slot-0 assumption in the RGBA refusal, 1.13 s. The adapter now
checks mesh 0's `texture_index` and its bounds. Both mapped RGBA refusal and mapped RGB acceptance pass.
The preliminary 14-row follow-up was stopped to test this final version; no result from that interrupted run
is used as passing evidence. The recovered producer and all mutant sites remain unchanged.

## Render checkpoint and late main

At `0e96c91a`, the 14 selected follow-up rows pass, 623,786 cases, zero failures/errors/skips, 466.33 s wall.
Final private native host: 1 test, 1.16 s. New object module with the private env: 3 tests, including 800 original
cases, 0.51 s. Build: 12.77 s, render executable 4.32 s. The producer and its 33 mutant sites remain unchanged.

One default sweep: DATA-ACQ-002 64/64 PNGs and 64/64 dumps identical; October 22 26/28 PNGs and 28/28 dumps
identical. Only world 37's two PNGs change. Last-frame delta: 2,087 pixels, mean absolute RGB 0.041796/255.
World 40's captured-clock PNGs/dumps are identical; world 37's clock PNGs change, with identical dumps,
2,095 pixels and mean absolute RGB 0.040111/255. After tour walls: 56.15 / 23.27 s; clocks 2.47 / 3.04 s.

Authored Blood Castle fixture: three models load, object-runtime refusals 0. Drawn sprites 10 -> 18, created
sprites 20 -> 36 across the two sampled draws. Three new particle requests are refused by the existing pool.
The candle glow is visible. Last-frame delta: 5,851 pixels, mean absolute RGB 0.147890/255; +0xb4 changes the
OBJECT dump, light dump unchanged. Before / after walls: 1.36 / 1.47 s. This is a demo layout, not client placement.

Latest main advanced to `3732f82a` (#361 ITEMS-002X) during rendering. It changes shared renderchar headers.
The registry append conflict retained both rows. The lane is rebuilding and selecting affected follow-up checks.
No ready line has been written.
