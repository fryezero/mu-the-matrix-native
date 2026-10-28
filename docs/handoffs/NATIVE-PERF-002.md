# NATIVE-PERF-002

PR [#182](https://github.com/fryezero/mu-the-matrix-native/pull/182) adds ordered player batching,
direct float-corner delivery, bounded scratch storage and an offline stress/measurement command.
**The complete 25 fps goal remains open.** Crowd40 passes the committed checker, with pacing tails;
all three 80-player scenes fail. Full tables, earlier unfavorable results and reproduction commands
are in [the finding](../research/native-performance-stress.md).

## Final result and source boundary

The final timing source is `e4c9471`, including main `2b8c8f5` and INPUT-001. Before/after fps are
24.98/24.98, 19.94/22.41, 18.46/21.17 and 13.95/15.98. Each run lasts 60 seconds, excluding 50 warm-up
frames. Mode order alternates between scenarios. This task's builds/tests/profiling do not overlap
timing. Other host activity was not controlled; these are paired observations, not a causal guarantee.
The earlier shared-load regressions and the first serialized repeat remain in the finding.

Latest main `a278d93` adds WORLD-ORDER-001's oracle/tests/comments, with runtime order numbers unchanged.
The final CLI repair `7493b3f` distinguishes file-valued `--input-script` from inline scripts. The timing
command does not use that file option. These changes leave the measured scene loop unchanged; a final
relink was not timed again. Final-source tests and renders are checked separately.

All 40/80 players have equipment and nameplate admission. Each scenario starts with 32 wandering
monsters, repeated area skills, particles/joints, real Ruffle windows and a map. Missing workload,
models/textures, particle drops or overflow reject timing. No quality reduction was introduced.
`--perf-fov 65` is an offline wide-camera override, not complete interactive camera unlocking.

Crowd40's after work p95/p99 is 30.4/32.6 ms, but its actual frame p99 is 45.3 ms. The checker passing
does not mean every frame takes at most 40 ms. After work p95/p99 in the 80-player scenes is 49.4/51.6,
51.8/60.4 and 67.9/70.6 ms. Their main-thread CPU means are 43.9/46.7/61.8 ms, already above the whole
40 ms budget. All four current after runs pass unchanged warning limits; the earlier Tormenta warning
failure is retained. Warning acceptance does not establish the 25 Hz target.

World-GL elapsed queries overlap CPU submission and exclude Ruffle/Metal, so this is not a complete
CPU/GPU split. Earlier sampling identifies skinning/corner submission and Ruffle AVM1 work. Three
integrated sampling attempts yielded no usable report, including a 180-second resumption attempt with
the target alive. Current sampling and complete Ruffle GPU timing remain open.

## Checks

- Final `bash scripts/local-macos-ci.sh`: 1,440 tests in 38 discovery runs, 174 explicit skips, six fixture
  scenarios, viewer/readers builds; publication audit 1,310 files, zero rejected. No hosted CI.
- Combined registry sweep and affected-source reruns: 89 passing root rows, 1,670,750 counted cases,
  zero failures/errors. The fresh input, haze and world-order families catch 24/24 mutants. This is
  accumulated evidence, not a claim that the entire registry ran again during resumption.
- Five root families lack private inputs: client LEA decode, model codec, effect tree, effects and
  objects. Sixteen social helper rows run through their parent. All 110 registry rows are accounted for.
- Direct-corner host: all 247 exact stream/table cases match, both mutants caught. Existing mesh-draw
  instruction family: 14,619 cases, four negative controls caught. Eight stress tests are in the gate.
- Twelve final-source PNG pairs match full-file SHA-256 at frames 0/60/120 across all scenarios. GFx is
  disabled in both pixel runs because Ruffle already varies with timing even between identical runs.
  Real Ruffle is enabled for all timing runs. Complete deterministic GFx frame equality is unverified.
- Nine private PERF-001 tests pass. All fourteen provenance tests pass; the file-script regression
  first fails on the old exemption. Quality admission covers eight presence/value combinations.
- Scratch Preview bundle rebuilt with real ABI-3 Ruffle; check-bundle and deep signature checks pass.
  Owner install, signing state and Native Data were left alone. No live client or launcher was used.

## Local artifacts

Private reports/renders remain under `~/Documents/MTM/mu-mac-tools/native/`, outside git:

- `scratch/native-perf-002/landing-{before,after}-*/`, `landing-results.json`, `landing-table.md`: final
  integrated commands, binary hashes, workload summaries, CPU/phase/GPU TSV and reports.
- `scratch/native-perf-002/resumed-*` and `integrated-*`: earlier results retained without filtering.
- `scratch/native-perf-002/gate-close.log`, `validator-combined-close.json`, `validators-close/`,
  `validators-landing/`, `private-perf-close.log`, `pixel-close.log`, `profile-resumed.log`.
- `renders/native-perf-002/landing-render-hashes/`: twelve final-source byte-identical frame pairs.
- `scratch/native-perf-002/release/`: rebuilt tools and ad-hoc signed Preview bundle, not installed.

## Next

Keep issue #176 open. Reach 25 fps in the three 80-player scenes and reduce crowd40's pacing tails.
Obtain a usable current sampling profile and complete Ruffle/Metal timing, then investigate validated
pose/skin caching, AVM1/movie work, scene allocations and corner submission. Cache keys must retain
shared-buffer side effects, attachments, light, alpha and roots. Broader worlds/skills/movement and
interactive free camera, complete GFx frame equality, separate extreme mu-client/Preview timing and
the five missing-input families remain unverified. This demo is not a live crowded-server trace.
Cleanup follows the common brief after merge; private reports and the scratch bundle are retained.
