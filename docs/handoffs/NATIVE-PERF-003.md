# NATIVE-PERF-003

Worktree native-perf-003, branch codex/native-perf-003. Native-only offline
performance work; no original client or launcher used. Checkpoints are pushed
regularly because provider failures can interrupt the lane.

[Finding, experiments and boundaries](../research/native-performance-003.md).
Reviewed run locations were mu-mac-tools/native/scratch/native-perf-003/continued
and mu-mac-tools/native/renders/native-perf-003. They are removed after merge.
[Retained aggregate evidence](../research/native-performance-003-summary.json).

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
- Focused rebuilt checks: perf 11 tests, 2 private skips; stress/Metal/clock
  16 tests, zero skips; GFx 2 15 tests, 2 skips for private fonts and the absent
  pristine dependency checkout. The full final gate is recorded below.

The original meshdraw instruction validator completed in continued/oracle-final:
843/843 draw cases, 247/247 pinned cases, 13,529/13,529 texture names, zero
mismatches, all four negative controls detected and no uncovered draw branches.
Fourteen installed models were explicitly skipped. This compares the reconstructed
draw library with x86 instructions; the separate native full-frame comparison
covers the host/compiler changes.

Disk recovery removed the lane's rebuildable Rust outputs, duplicate experimental
libraries and bulk frames. Numerical logs, per-frame hashes and eight representative
before/after PNGs were retained for the final review. The owner then required
complete lane cleanup after merge. The later README-candidate request adds the
explicit future-input exception listed below. Reviewed summaries and provenance
remain committed.
Rust target output is now ignored explicitly.

The final-source 60-second pairs are complete with normal wall clock: crowd40
24.78 ->24.90, crowd80 16.52 ->18.37, Tormenta80 15.40 ->18.94 and retina80
13.59 ->17.58 fps. All eight pass the unchanged regression warning envelope;
none passes strict work/pacing acceptance in this shared-host repeat. Full frame
percentiles and CPU/GL/Metal costs are in the finding. Every measured frame has
a complete Metal interval. The 80-player 25 Hz goal and crowd40 tails stay open.

## Final lock-held gate

Lock acquired 2026-10-28 08:31 CDT after the integration lane released it. Merged
latest main `cb4bd9c` cleanly as checkpoint `df94a20`. That main change affects
tests, validator inputs and native build prerequisites, not the measured runtime
sources. The normal wall-clock timing matrix therefore retains its exact recorded
source identity; no new whole-frame performance claim is inferred from the merge.

`bash scripts/local-macos-ci.sh` passes: 1,489 tests in 38 suites, 170 explicit
private/optional skips, zero failures. Seven fixture scenarios pass all 50
expectations with 53 inbound frames, zero unbound/undecodable frames; the existing
two unrecovered intents and five unsent frames remain reported. Native viewer and
live-reader build checks pass. Repository audit: 1,384 files, zero rejections.
No hosted workflow was dispatched and no original client/launcher was used.

The first final gate caught a stale GFx 3 expectation of seven patches. Its test
now recognizes the eighth comparison-clock patch while keeping the old two-patch
provenance assertions scoped correctly. Focused GFx 3 checks pass, 12 tests and
two skips, followed by the complete passing gate above. The gate includes the
built Metal drain and AS2 clock probes. The final code change is this test fix;
final documentation adds these counts and the retained evidence summary.

After merge, release the lock and delete the complete native-perf-003 scratch and
render trees, build outputs and worktree, then the local branch. Only the named
README input exception below survives. The main checkout remains untouched.

## README follow-up inputs

Keep only these four full-resolution native captures and their small reproduction
metadata in `~/Documents/MTM/mu-mac-tools/native/renders/readme-candidates/stress80/`.
No `README.md` change is included. All four were inspected visually, contain 80
fully equipped players and combat, retain normal HUD/names, and have no debug
overlays. Existing bright armour/name overlap remains visible; these are unedited
native-renderer outputs. Missing scenery/GFx attempts were rejected.

| File | Scenario | Frame / FOV | Resolution | Matching full-UI benchmark fps |
|---|---|---|---|---:|
| `perf003-crowd80-f0180.png` | crowd80, Lorencia | 180 / 65 | 1280 x 800 | 18.37 |
| `perf003-tormenta80-f0180.png` | tormenta80, Tormenta arena | 180 / 65 | 1280 x 800 | 18.94 |
| `perf003-retina80-f0180.png` | retina80, Tormenta arena | 180 / 65 | 3456 x 2160 | 17.58 |
| `perf003-crowd80-wide-f0120.png` | crowd80, wider view | 120 / 80 | 1280 x 800 | 18.37 context only |

Capture throughput is **not measured**. These headless presentation captures close
the inventory/character/skill panels and map to expose the crowd; the normal stress
benchmark keeps them open. The fps column is context from the timed full-UI
workload, not a performance claim for the screenshots or wider view.

Each image's exact capture argv/environment and SHA-256 are in `commands.json`.
Keep `regenerate.py` and `capture-notes.md` as the small reproduction inputs. The
capture command below regenerates all views in a new output directory after the
main native world and patched GFx release library have been built. It uses existing
raw research exports and creates authored crowd/monster fixtures; it does not use
the original client or alter installed Native Data.

```sh
ROOT="$HOME/Documents/MTM"
CAND="$ROOT/mu-mac-tools/native/renders/readme-candidates/stress80"
"$ROOT/mu-the-matrix-native/tools/python/bin/python" "$CAND/regenerate.py" \
  --repo "$ROOT/mu-the-matrix-native" --out "$CAND/regenerated" \
  --objects "$ROOT/mu-mac-tools/native/scratch/objects/live/plain" \
  --gfx "$ROOT/mu-mac-tools/native/scratch/gfx3/movies" \
  --lang "$ROOT/mu-mac-tools/native/scratch/quest2/lang" \
  --game-root "$HOME/Library/Application Support/MuTheMatrix/prefix/drive_c/MuTheMatrix"
```

The object exports for worlds 0 and 141 and main movie match the existing installed
copies by SHA-256. The installed legacy Native Data set lacks its required manifest
and was refused without modification. The original combined PERF-002 data folder
was removed externally after the completed timing matrix. Follow-up timing needs
a freshly prepared complete research data root or a verified Native Data set.
