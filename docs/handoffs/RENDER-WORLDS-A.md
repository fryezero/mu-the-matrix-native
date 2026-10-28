# RENDER-WORLDS-A

Kanturu/Karutan flame calls, their five particle kinds/bitmap loads, and the Noria/Elbeland/Raklion/Karutan
after-character pass are implemented in isolated per-world files. Evidence and exact limits are in
[client-world-fidelity](../research/client-world-fidelity.md#render-worlds-a-2026-10-27).

Validation before integration: 9 families x 1,000 Unicorn cases, zero mismatches/stops; 13/13 compiled mutants.
Synthetic native tests exercise both flame pools and the four world groups' deferred draws. Character-select's
stale core-header dependency was fixed after its regression caught it. The final integrated local gate is pending.

Local artifacts: `~/Documents/MTM/mu-mac-tools/native/scratch/render-worlds/a-*.json`, `a-*.log`, and
`~/Documents/MTM/mu-mac-tools/native/renders/render-worlds-a/{before,after,warm}`. No live game used.

Kanturu live image error: 3.717 before; 4.006 after with sparse tour sampling; 3.444 after rendering all 25 frames.
Nine unaffected maps retain both frame hashes. Near-hero after-flag differences: Elbeland 12 -> 0, Raklion 10 -> 0;
Noria 15 and Karutan 6 remain for the documented selector/visibility reasons.

The owner confirmed missing live PNGs for Karutan/Noria/Elbeland/Raklion and authorized snapshot/report evidence
plus native before/after there. Next: fresh live captures of those maps under the game lock in a later run, then
phase-aligned multi-frame fidelity. Do not recreate them by running a live client during this milestone.
