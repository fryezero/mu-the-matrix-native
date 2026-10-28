# RENDER-TIME-001 native side, 2026-10-28

## Scope and result

Native temporal measurement and regression checking are implemented. The LIVE half remains open.
No original client or launcher was started, stopped or driven. No gameplay, reconstructed routine, RNG rule,
network route, domain state or default render changed. The native tool gains opt-in measurement flags only.

- Fourteen authored INPUT-001 physical-input paths cover thirteen captured maps and both Devias views.
- Each 201-iteration route draws every iteration and samples 0,10,...,200. It retains three PNGs per view,
  compact time-series JSON and bounded logs, with no object/light frame dumps.
- Samples include hero/camera, animation, object alpha/UV/timer/visibility/action, particles/effects/joints,
  lights, boids/fish/weather, sky clear, RNG streams and image colours/checksums.
- Reports fail on missing fields/samples, unknown phase, changed script/input provenance, nonfinite values,
  stalled paths, clock offsets or exceeded thresholds. Per-map reports retain thresholds and failure counts.
- The normal gate discovers synthetic tests; opt-in private integration replays all paths on installed data.

[The finding](../research/client-render-time.md) defines every vector component, exact thresholds, commands,
and the future LIVE capture procedure. INPUT-001's parser is reused without adding privileged script actions.

## Verification

Focused portable run: 16 discovered tests, 15 passed and one explicit private skip. Private run: all 16 passed.
The checker catches 8 frozen-group controls and 5 changed-checksum controls. These are authored data mutants,
not compiled reconstruction mutants or new Unicorn cases. Additional checks cover missing/malformed data,
absolute/relative WorldTime, no walking/zoom, phase and mugl provenance, threshold boundaries, exact virtual
clock/input outcomes and PNG/sample-cadence independence. The default-mode suite remains the guard for
existing render behavior.

Installed-data integration runs fourteen views twice: 294 paired sample rows, 588 samples, 5,628 complete
native draw iterations. Every numeric component and all five native checksums agree at every paired sample.
All routes move 141.421356 world units in XY and span 9 degrees of FOV. Icarus additionally runs with a
five-frame sample interval: 41 samples, all 21 common samples exactly equal to its ten-frame run. This
exercises draw-driven particle production without conflating draw cadence and capture cadence.
A compiled tool mutant that draws only on samples was also exercised: 20/21 common Icarus rows differ,
so the cadence regression catches it. The production source and binary were restored afterward.

An Icarus CLI capture/report smoke also passes; its frame 100 was visually inspected for the clouds/ribbons.
That self-comparison only checks CLI delivery. The independent two-run private test supplies repeatability
evidence. The saved still tour and historical original-image scores were not recalculated or reclassified.
No earlier temporal baseline exists, so installed checks establish current-binary repeatability. Future
baseline-vs-candidate checks can use `MU_RENDER_TIME_BASELINE`; the comparator permits changed binary hashes.

## Final locked verification after resume

The resumed run acquired the merge lock at 10:49 CDT and integrated main `7ce87c6` in `96b2eb0`.
Shared-document conflicts preserve both milestones; the Makefile retains both new header dependencies.
The full `bash scripts/local-macos-ci.sh` passed on that tree: **1,544 tests across 38 suites,
189 explicit private/optional skips, zero failures**. The native suite contains 724 tests. All eight fixture
scenarios passed, with 67 inbound frames and zero unbound/undecodable frames. The existing two unrecovered
intents and six unsent frames remain reported. Viewer/read-only reader builds passed; readers were not run.
The repository audit checked **1,469 files, zero rejected**. No hosted workflow was dispatched.

The final private temporal rerun passed **16/16 tests, no skips**, after the main merge. Its fourteen views
again produced 294 equal sample pairs, 588 samples and 5,628 full draw iterations. The additional Icarus run
produced 41 samples over 201 iterations, with all 21 common rows equal across sample cadences. Every route
retained 141.421356 units of XY movement and 9 degrees of FOV span. These are installed-data repeatability
checks, not original-client comparisons. Self-review covered the scoped diff, defaults, full-draw guards,
thresholds, private-data boundary and merged ownership changes; no independent agent review is claimed.
Only evidence documentation changed after the final runtime gate. No new retained local input is needed.

## Native thresholds

All maps, sample indices, scripts, placement/sidecar hashes, WorldTime and logic ordinals must agree. Numeric
absolute delta <=1e-6; object/particle/environment/light checksums and image SHA-256 exact. Each path must walk
>=50 XY world units and span >=1 degree FOV. Live policy is separately defined in the finding and has no
passing original-client evidence. Its initial limits include 20 ms clock uncertainty, 1-unit camera error,
0.05-frame animation, 0.05 frame-light RGB mean and 8/255 coarse image RGB mean. Unknown pool/RNG phase
cannot pass by subtracting WorldTime epochs or selecting a favourable still.

## Inputs and cleanup

Private runs read the installed game selected by Native Data's `setup.json` and the existing fourteen-view
capture placements at `mu-mac-tools/native/scratch/fidelity2/live/plain`. Those inputs were not modified,
copied or committed. New scripts contain authored routes and reviewed start metadata only. No new input is
needed by future work. Temporary integration outputs clean themselves; milestone scratch/renders, builds,
links and the owned worktree are removed after merge under the port brief's cleanup rule.

## Remaining LIVE half

Acquire the shared game lock in a future authorized capture session, use mugl patches off with effective
configuration provenance, replay these same physical inputs, bracket post-draw samples with WorldTime, and
record join/arm/draw/logic-counter phase. The future exporter must supply the documented pool/light/object/
image summaries. Supply the observed native clock epoch and independently establish pool/animation/RNG
history. Separate native module RNG streams and absent saved pools currently prevent original-stream replay.
The existing still snapshots cannot supply it. Review live thresholds and image composition before scoring.
No live exporter, live session, full pool-state restoration or original-client temporal pass is claimed.
