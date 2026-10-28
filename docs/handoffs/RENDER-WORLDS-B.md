# RENDER-WORLDS-B

Implemented Devias doors/flicker, Tarkan moves, Elbeland move/boid creation, Raklion move/create, code-created
placements and Raklion snow. Per-world source and verified addresses are in
[the finding](../research/client-world-fidelity.md#5-render-worlds-b-2026-10-27).

- `scripts/validate_worlds_b.py --cases 500 --mutations`: 8 families, 4,000 equal, no stopped cases or mismatches,
  10/10 compiled mutants detected.
- Existing object validator: 10 families, 19,839 comparisons equal, zero mismatches or stopped; 19/19 compiled mutants detected.
- Fourteen-map fidelity tour: Devias missing 3 to 0, Raklion 2 to 0; Devias town frame-light error 0.00386 to
  0.00068, Elbeland 0.03336 to 0.02078; primary light unchanged/equal everywhere. Nine unaffected-world final PNG
  hashes unchanged. Live PNGs from the old manifest are missing, so fresh live-image mean error is unavailable.
- `bash scripts/local-macos-ci.sh` passed. Synthetic model-loading/deduplication checks cover worlds 2, 57 and 58; the final merged-main gate is rerun before merge.

Private reports: `~/Documents/MTM/mu-mac-tools/native/scratch/render-worlds-b/`.
Native GL renders and before/after scoreboards: `~/Documents/MTM/mu-mac-tools/native/renders/render-worlds-b/`.
Both remain local. No live game, launcher, service or protection work.

Remaining: nested warp-model effect lifecycle/rendering, Elbeland boid mover/model drawing, the missing archived
live PNGs, the haze and separate visual-pass/sibling work. Creation-effect calls are forwarded, with unsupported
kinds still reported by the existing effect factory. Shared object-host sound calls remain counted.
