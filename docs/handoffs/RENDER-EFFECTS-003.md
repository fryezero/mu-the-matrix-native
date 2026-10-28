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
