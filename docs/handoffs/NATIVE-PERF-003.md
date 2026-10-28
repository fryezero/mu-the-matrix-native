# NATIVE-PERF-003

Worktree native-perf-003, branch codex/native-perf-003. Native-only offline
performance work; no original client or launcher used. Checkpoints are pushed
regularly because provider failures can interrupt the lane.

[Finding, experiments and boundaries](../research/native-performance-003.md).
Local source/logs: mu-mac-tools/native/scratch/native-perf-003/continued.
Local images/hashes: mu-mac-tools/native/renders/native-perf-003.

Verified so far:
- Full Metal queue intervals, including Ruffle offscreen work; 168-frame scene
  probe and synthetic cached-frame/shutdown probe have no missing frames.
- Deadline pacing. The first clean 60-second repeat passes strict crowd40 tails
  at 24.98 fps. Its three 80-player scenes remain below 25 fps.
- 604/604 frames identical with the comparison clock and synchronous presentation.
  The initial real-time GFx edge mismatch was reference nondeterminism caused by
  AS2 getTimer. Patch 0008 supplies an opt-in clock; the benchmark rejects it.
- Region search: 120,000 production transform calls in eight CPU-timed batches,
  output regions unchanged; 552.265 ->404.728 ms per 15,000 calls. Fourteen
  synthetic dump pairs are equal. Shared-host window ablations are unfavorable
  and retained; no whole-frame speedup is inferred from that microprobe.
- Focused checks: perf 11 tests, 2 private skips; stress/Metal/clock 16 tests;
  GFx 2 15 tests, 2 skips. Full gates passed before the final clock addition.

The original meshdraw instruction validator completed in continued/oracle-final:
843/843 draw cases, 247/247 pinned cases, 13,529/13,529 texture names, zero
mismatches, all four negative controls detected and no uncovered draw branches.
Fourteen installed models were explicitly skipped. This compares the reconstructed
draw library with x86 instructions; the separate native full-frame comparison
covers the host/compiler changes.

Disk recovery removed the lane's rebuildable Rust outputs, duplicate experimental
libraries and bulk frames. Numerical logs, per-frame hashes and eight representative
before/after PNGs remain. Rust target output is now ignored explicitly.

The final-source 60-second pairs are complete with normal wall clock: crowd40
24.78 ->24.90, crowd80 16.52 ->18.37, Tormenta80 15.40 ->18.94 and retina80
13.59 ->17.58 fps. All eight pass the unchanged regression warning envelope;
none passes strict work/pacing acceptance in this shared-host repeat. Full frame
percentiles and CPU/GL/Metal costs are in the finding. Every measured frame has
a complete Metal interval. The 80-player 25 Hz goal and crowd40 tails stay open.

Next: lock-held latest-main merge, full local gate, PR and merge.
