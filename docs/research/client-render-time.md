# Temporal world fidelity, RENDER-TIME-001

## Implemented native boundary

This milestone adds an opt-in measurement path, shared physical-input routes and a temporal regression
checker. It changes no reconstructed routine, RNG rule, simulation order, default render, gameplay or live
client. No original client was started, stopped or driven. There is no new instruction-equivalence claim.
The existing world-lane Unicorn findings remain the evidence for those routines.

The old [world tour](client-world-fidelity.md) scores saved arrival stills. C2 #189 showed why that cannot
score moving/random content: Icarus error against one original still varies with native phase, and adding
verified producers changes downstream RNG consumption. This measurement uses complete draw histories.
It does not remove moving regions to improve an image score.

`scripts/render_time/paths.json` covers fourteen capture views in thirteen worlds. Start tiles match the
saved tour's reviewed arrival metadata. Each view has its own authored INPUT-001 `.input` file, with no
private record data. At 640x480 drawable pixels and a 25 Hz input loop, the 201-iteration route stands,
clicks east on screen, zooms, clicks west and restores zoom. The hero's actual path and camera are observed,
not assigned. A blocked walk or absent zoom fails the checker. The two Devias views remain separate.

| View | World | Start tile |
|---|---:|---|
| Lorencia | 0 | 137,130 |
| Dungeon | 1 | 108,247 |
| Devias arrival | 2 | 71,181 |
| Devias town | 2 | 199,48 |
| Noria | 3 | 174,109 |
| Lost Tower | 4 | 208,79 |
| Atlans | 7 | 19,15 |
| Tarkan | 8 | 195,70 |
| Icarus | 10 | 15,13 |
| Aida | 33 | 84,11 |
| Kanturu | 37 | 19,218 |
| Elbeland | 51 | 53,224 |
| Raklion | 57 | 224,211 |
| Karutan | 80 | 125,123 |

## Capture and report contract

`mu-world` and `mu-walk --headless --time-series-every N` draw every iteration, including iterations that
produce no PNG or sample. This matters because drawing advances some visual lifecycle state and creates
particles. Samples run after drawing. They go to stdout as `time_series:1` JSON rows. The flag is limited
to headless runs of at most 10,001 iterations; N is 1..10,000. Without the flag, existing behavior remains.
`--time-series-start-ms MS` sets the virtual headless clock epoch, default 100000, range 1..2140000000.
It supplies time to the native clock; it does not restore pool history or the original shared random stream.

`scripts/render_time.py capture` runs a new output directory, rejects disk space below 5 GiB, captures 21
samples per view at frames 0,10,...,200, and saves only frames 0/100/200. It writes per-view `series.json`,
a combined `series.json` and a bounded diagnostic log. No object images, light grids or decoded tables
are written. `compare` writes a combined report and one report per map, each with thresholds and failures.
All of these outputs are private local evidence. Keep only compact summaries and three representative PNGs
per view while working, then follow the port brief's cleanup rule.

The series includes source, plan/binary SHA-256, script and placement/sidecar SHA-256 per view, world/tile, expected sample frames,
phase provenance and whether every iteration drew. Each sample records world, frame, WorldTime in ms and
logic-step ordinal, followed by these fixed vector layouts, indexed from zero:

| Group | Ordered values |
|---|---|
| camera, 9 | hero XYZ, hero animation frame, camera eye XYZ, FOV, pitch |
| objects, 19 | live count; sums of frame, prior frame, alpha, blend U/V, blend light, position XYZ, angle XYZ, light RGB, timer; visible count; action sum |
| particles, 10 | live count; sums of XYZ, rotation, alpha, scale, lifetime, type; live effect count |
| environment, 8 | live boid/fish count; sums of XYZ, frame, alpha; live weather count; weather rotation sum |
| lights, 6 | whole-map primary RGB means, whole-map frame-light RGB means |
| sky, 4 | environment clear RGB in 0..255, live joint count |
| rng, 5 | object seed, environment state, particle state, environment calls, particle calls |
| image, 48 | 4x4 grid, row-major RGB means in 0..255, from the actual RGBA readback |

Objects, particles and environment also have ordered FNV-1a-64 checksums of the selected fields. Lights
checksum both complete float grids. Image checksum is SHA-256 of the native RGBA readback. Checksums contain
no addresses, struct padding or raw records. They supplement sums, which can hide offsetting changes.
These checksums are only comparable between native runs with the same architecture and inputs. RNG states
are native module streams; the original has a shared stream. Particle sums exclude dead entries. Boid/fish
sums exclude dead entries; the weather checksum covers live positions/rotations. Effects and joints have
counts and image evidence, not complete record/phase coverage. Hidden details of those pools remain a limit.

## Thresholds and evidence classes

Native regression thresholds are active now. All expected maps, scripts and sample indices must agree;
clocks, steps and checksums must match exactly. Relative live step ordinals must also agree. Every numeric component must differ by at most `1e-6`.
Each route must move at least 50 world units in XY and span at least one degree of FOV. Nonfinite numbers,
missing/duplicate/reordered rows, schema mismatches and unaligned phase fail. The checker exits 1 for a
measured failure and 2 for invalid input or a failed capture. It does not treat a missing private input as
an integration pass. The default local gate runs authored synthetic cases and explicitly skips the private
capture unless integration is requested.

Live thresholds are a declared initial policy, not calibrated acceptance evidence. `LIVE_LIMITS` in the
checker is the exact component table: WorldTime absolute and relative error <=20 ms, camera position <=1 world unit,
hero/object animation <=0.05 frame, FOV/pitch <=0.01 degree, object position <=1 unit, object angles <=0.1
degree, alpha/UV/light <=0.01, timer <=0.05, and identical live/visible/action counts. Object sums divide by
live count. Particle/environment counts allow 10% relative error; their per-live-entry position means allow
5 units, alpha/scale/frame 0.05, rotation 2 degrees and particle lifetime 1 step. Particle type mean must
match. Weather rotation sum allows 2 degrees. Primary-light RGB means allow `1e-6`, frame-light means 0.05,
clear RGB 1/255, joint count 10%, and each coarse image RGB cell 8/255. Live RNG/checksums are diagnostic,
never compared as if pools or object ordering were identical.

A live comparison requires `source:live`, `mugl_patches:off`, and `phase:aligned` on both series with an
independently recorded alignment procedure. The native capture deliberately emits a fresh-world phase label,
so pairing it blindly with a live series fails. A phase label is a provenance assertion by the future live
adapter, not an algorithm that finds or proves phase equality. The report must retain unknown pool/RNG
phase as unaligned. No best-frame search, lag fitting, moving-region exclusion or retuning thresholds after
seeing scores is permitted. Coarse image means do not replace full-resolution pixel or per-object checks
in the still tour and world-lane validators. A report only covers its recorded fields and route.

## Reproduce without the live game

Use the repo Python and an owned worktree. Build `make -C native build/mu-world`. Set `MU_GAME_ROOT` to the
installed data directory and `MU_RENDER_TIME_OBJECTS` to the existing captured plaintext placements, without
copying either into the worktree. The installed `.obj` files are refused by the existing loader; missing
captured placements are not an acceptable substitute for this integration run.

```sh
./tools/python/bin/python -m unittest discover -s native/tests -p test_render_time.py -v
MU_RECOVERY_INTEGRATION=1 ./tools/python/bin/python -m unittest discover -s native/tests -p test_render_time.py -v
./tools/python/bin/python scripts/render_time.py capture --out "$LOCAL_OUT/baseline"
./tools/python/bin/python scripts/render_time.py capture --out "$LOCAL_OUT/candidate"
./tools/python/bin/python scripts/render_time.py compare "$LOCAL_OUT/baseline/series.json" \
  "$LOCAL_OUT/candidate/series.json" --report "$LOCAL_OUT/regression.json"
```

`LOCAL_OUT` must exist outside tracked source. A retained series from an accepted earlier binary can be
passed as `MU_RENDER_TIME_BASELINE` to the integration test. Binary hashes may differ intentionally; plan,
script, epoch and phase inputs must agree. Without that baseline, the installed-data check establishes
repeatability of the current binary, not preservation against an older revision. Portable expected-value
checks and planted data regressions exercise the checker independently of repeatability. The Icarus private
check additionally changes the sample cadence and requires equal common rows, catching sample-driven draws.
The full local gate discovers the portable suite through `native/tests`; no shared test list is added.

## LIVE half procedure, not executed here

1. In a future authorized live session, read `mu-mac-tools/GAME-LOCK.md` and the
   [service contract](service-contract.md). Acquire the shared game lock with the documented `mkdir`/owner
   protocol and matching `MU_AGENT`/`MU_LOCK_ID`. It is distinct from the native merge lock. Leave any client
   the operator did not start alone. Use one logged-in client at a time, runs <=3 minutes and the lock <=15
   minutes. Split the fourteen views across lock sessions. Do not expose account/character names in outputs.
2. Use a dedicated capture setup in the Wine track. Save its configuration, disable mugl hotpatches before
   the capture process starts, and verify the effective configuration in its logs. The current hotpatch build
   reads `C:\mutools\mugl-hotpatch.txt`; write mask `0` in that dedicated setup, rather than deleting the file,
   which selects the default mask. `MUGL_MASK=0` applies to test programs, not main.exe. `MUGL_MODE=off` only
   disables GL buffering and does not disable CPU patches or intercepted integer/double conversions. For a
   strict original-GL reference use the Wine track's documented real-driver path without mugl. Record DLL
   provenance, effective mask and buffering mode. Do not enable performance or clock patches for scoring.
   Do not change a running player's setup. Restore the saved capture configuration afterward.
3. Reach the named world/start tile with the interface. Record client dimensions and exact camera values.
   The shared scripts require a 640x480 drawable client area, with title-bar/Retina coordinates translated by
   the injector. Arm INPUT-001's 25 Hz physical-input loop at a recorded WorldTime boundary. Do not replace
   physical clicks with position writes. Confirm the world/tile, walking and camera path after replay.
4. Capture post-draw samples at the declared frame ordinals. Bracket each window-only screenshot/read batch
   with WorldTime reads at `0x06fce370`; retain the bracket and actual logic ordinal. Reject batches whose
   uncertainty exceeds 20 ms. Record the join/entry epoch, first draw, arm epoch, WorldTime per sample and
   ambient logic counter `0x0bdc5eb0`, which C2 identified as a logic ordinal, not elapsed milliseconds.
   Export objread's time-varying fields and lightread's primary/frame grids to the same compact summaries.
   Add explicit legacy particle, effect, joint, boid/fish/weather and sprite pool observations where available.
   Summarize and delete raw intermediate dumps promptly; save only three screenshots per view.
5. Match samples by the recorded arm epoch and relative WorldTime, never by minimum image error. Supply the
   native epoch through `start_world_time_ms` in a private plan, using the observed first-sample WorldTime.
   This aligns the clock input, not prior state. Draw every native iteration and preserve the observed tick
   and draw ordering. Verify step ordinals and absolute phase for periodic functions. An 8-second relative
   time match alone does not align a sine driven by absolute WorldTime.
6. Establish pool ages, animation starts, ambient-counter phase and RNG provenance independently. Current
   saved snapshots lack those inputs, and native module RNG streams are separate. If they cannot be aligned,
   leave phase unaligned and retain diagnostics. Do not relabel a fresh native world as aligned. A future
   replay/adapter is required before claiming temporal equality. Likewise, coarse image scoring requires
   identical image composition, dimensions, HUD/hero policy and grid orientation on both sides. Do not score
   an original HUD against a native no-HUD view as if composition matched.
7. The future live adapter must export the schema above, input/script/plan hashes, effective patch provenance,
   WorldTime brackets and phase evidence. Run `compare --mode live` only after reviewing that evidence and
   approving the threshold policy. Release the game lock and restore the capture setup. No exporter, live
   capture, original-pool restoration or live score was implemented or run in this native milestone.

The final locked tree includes main `7ce87c6`. The full Mac gate passed 1,544 tests across 38 suites with
189 explicit skips and zero failures. The post-merge private temporal rerun passed 16/16 tests, including
294 equal sample pairs across fourteen views and 21 equal common Icarus samples across two cadences.
Full counts and measured native coverage are in [the milestone handoff](../handoffs/RENDER-TIME-001.md).
