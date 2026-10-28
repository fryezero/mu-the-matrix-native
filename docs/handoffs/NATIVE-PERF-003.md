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

In progress at this checkpoint: the full original meshdraw instruction validator
is running in continued/oracle-final. Do not claim its result before reading the
summary. Next: latest-source real-time matrix with normal wall clock, then the
lock-held final latest-main merge, full local gate, PR and merge. Do not claim
the 80-player 25 Hz goal from the earlier compiler-only timings.
