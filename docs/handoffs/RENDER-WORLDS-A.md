# RENDER-WORLDS-A

Kanturu/Karutan flame calls, their five particle kinds/bitmap loads, and the Noria/Elbeland/Raklion/Karutan
after-character pass are implemented in per-world files. Exact instruction boundaries and limits are in
[client-world-fidelity](../research/client-world-fidelity.md#render-worlds-a-2026-10-27).

The integrated instruction comparison passes 9 families x 1,000 cases with zero mismatches/stops; all 13 compiled
mutants are caught. Three synthetic native tests cover ten sessions: both flame pools, and deferred object draws
for four world groups on GL/software. Eight world-part checks pin the combined viewport and deferred draw hooks.
Character-select's stale core-header dependency was corrected, matching the sibling C fix.

Final local macOS gate passes on main `0b7edfc`: **1,397 tests in 38 discovery runs, 166 explicit skips, zero failures; audit 1,261 files, zero rejected**. Fixture scenarios and native viewer/readers build
also pass. The log is `a-isolated-gate.log`. The earlier world-part count error was fixed; a later parallel run
exhausted disk space, then passed after owned intermediate PNG cleanup and an isolated temporary directory.
Siblings B/C, viewport, item and audio integrations are retained. Self-review found no remaining scope/standards
findings; no independent review is claimed.

Local reports are in `~/Documents/MTM/mu-mac-tools/native/scratch/render-worlds/`: `a-final-validate.json`,
`a-final-{before,after}*.json`, `a-final-hashes.json`, `a-final-render-sha256.json` and the gate logs. Renders stay under
`~/Documents/MTM/mu-mac-tools/native/renders/render-worlds-a/final-{before,after}*`. No live game was used.

The tour baseline `54ae63f` includes B/C and SESSION-VIEWPORT-001. With every frame rendered on both builds,
Kanturu's masked live-image error is 3.717 -> 3.444; share off by more than 24 is 0.0275 -> 0.0245. The default
sparse two-render tour gives 3.717 -> 4.006 because particles are emitted during rendering. Phases are not synchronized.
After the item/audio merges all 53 final native frames repeat byte-for-byte.
All eighteen PNG hashes from nine unaffected maps remain unchanged; Raklion's two frames also remain unchanged.
Primary terrain light equals the captured grid on all fourteen maps.

Near-hero after-flag differences are Elbeland 12 -> 0, Raklion 10 -> 0, Noria 15 -> 15 and Karutan 6 -> 6.
Noria type 19 is explicitly selected before the flag test; its separate flag writer remains unknown. Karutan's
six after differences are different records from the six before differences. Exact capture-history/visibility
causes remain unverified. The four maps' native before/after frames were inspected locally.

The owner confirmed that live PNGs for Karutan/Noria/Elbeland/Raklion were deleted on October 23. Object/light
snapshots and old score reports are the live evidence for those maps; Kanturu uses the surviving full-resolution
README source. Next: fresh live captures of the four missing maps under the game lock in a later authorized run,
then phase-aligned multi-frame fidelity. No live capture belongs in this run. Other handlers, creation effects,
region import and the shadow/custom registries remain outside A. Scope claim: issue #177.

## Resume integration, 2026-10-28

Merged current main `0a85441` into the existing branch. Kept both validator registrations and the
WORLD-ORDER-001 recorded-order tests, including A's hook signatures and 24-part count. The deferred pass now
anchors to original call `0x016d6949` and follows the environment in both draw columns, at order 85.
The GL viewer marker follows that pass. Existing helper adapters remain explicit. Reordering environment and
deferred-object calls must change both projected draw expectations. Sibling input/performance, world and
session integrations remain present. The registered A validator now expects 9,000 total cases, correcting its stale per-family count of 1,000.
The initial runner rejected only that count; all nine comparisons and thirteen mutants already passed.
Validation and refreshed fidelity results follow below.
