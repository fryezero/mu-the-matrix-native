# RENDER-EFFECTS-003

Checkpoint: Meteorite falling Fire01/0, six impact stones and Explosion01/0;
Inferno ring bursts with twenty Spark02/2 particles and one Explosion01/0 each.
Fixed pools and load-time assets only. No per-frame allocation, perf/mesh/scene,
item, audio or live-client work.

Initial verification: 9,000 focused cases, zero mismatches, eight compiled
production-C mutants caught. Particle move includes explicit native head-removal
checks, to be separated in final instruction counts. Four native tests pass with
private checks, including fixture-session casts and rendered-pixel removal checks.

Aqua Beam and Rageful Blow instruction/caller inspection is in progress. Their
primary coverage remains missing until the complete visual reaches native draws.
Existing mount-breath rounding behavior is unchanged. Coverage/documents, final
regressions, locked gate and release checks follow before merge.

Second checkpoint: Aqua Beam's ordinary-world primary 20-sprite chain is now
implemented and fixture-rendered. Skill checks: 12,000 cases, zero mismatches,
10/10 compiled mutants caught. K-requested consumers 0x7ef7/0 and smoke01/4/6/7/8
pass 15,000 cases with 7/7 compiled mutants. Across the two new corpora this is
24,453 original-instruction comparisons plus 2,547 native head-removal checks.
Rageful Blow remains missing: its lifetime-11/10 impacts require 0x463..0x469,
terrain rules and the owner-weapon renderer. No partial 0x461 port is retained.
The primary inventory will move 15/23 to 18/23 and weighted 46/77 to 56/77.
