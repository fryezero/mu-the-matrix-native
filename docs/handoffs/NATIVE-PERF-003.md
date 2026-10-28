# NATIVE-PERF-003

Worktree: native-perf-003, branch codex/native-perf-003. Native-only offline
performance work; no original client or launcher used. Resumed work was
checkpointed and pushed before continuing. The unreviewed QuerySet timing WIP
has been replaced with native Metal command-buffer intervals.

Implementation, measurement boundaries, unfavorable pilots and reproduction
are in [the finding](../research/native-performance-003.md).

The final gate, paired measurements and every-frame comparison are in progress.
The 25 Hz target is not claimed from the short pilot. Hold the shared merge lock
for the final latest-main merge, full local gate and PR merge.

Checkpoint during render investigation: the clean 60-second compiler/stack/pacing
matrix completed. Crowd40 24.98 ->24.98 fps passes strict pacing after. Crowd80
23.53 ->24.45, Tormenta80 21.83 ->22.07, retina80 17.78 ->17.87 still fail strict
25 Hz. Each report has complete Metal intervals. The every-frame GFx comparison
found 46 edge pixels different in frame 0. An unchanged baseline repeat also
differs, so this is not yet attributed to an optimization. `continued/control.py`
and `continued/repro.py` drive the current differential loop. Do not claim pixel
identity or merge until this is settled. `mu_model.c` contains an unmeasured
region-search-order candidate, not part of the timed matrix. Preserve/reject it
only after a separate measurement. Full local gates already passed, but the
final lock-held latest-main merge/gate/PR sequence is still required.
