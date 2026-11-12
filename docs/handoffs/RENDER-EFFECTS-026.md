# RENDER-EFFECTS-026

Branch `codex/render-effects-026`, base main `d4af71dd`. Codex GPT-6.1 Sol, no subagents.
Offline/static only. The merge steward owns the full gate and merge. No installed app is changed.
Research is part 39 of [client-render-items](../research/client-render-items.md).

## WIP checkpoint

Done:
- Ported all five later pairs' create/move/render branches, two original bitmap registrations, and
  `0x8569/0`'s render-time OBJECT point. No names or authored scales change.
- Full focused proof: 15,008 checks, zero mismatches, 14.549 s. This is 14,640 original-instruction cases,
  360 directed native head-retirement cases, five native pool/raster checks, two loader checks and one census.
- New registry row: 308 checks, 32/32 compiled production-C mutants caught, zero original-machine stops.
  52.6 s row, 52.74 s command. This initial result is superseded by the expanded fourth-point proof described below.
- Root build passes in 12.87 s, explicit rebuilt mu-world in 5.84 s. The source header's new declaration
  is inside its C++ linkage guard. The native raster host draws the created scale/alpha without enlarging them.
- Static inventory covers the frozen 110 program identities / 37 particle pairs, all supported, zero unresolved
  bitmap expressions. Later inventory additions are reported separately.
- Full-draw baseline, sixteen consecutive draws per installed model: 13,151 accepted / 122 refused pre-draw
  requests; 2,784 accepted / zero refused owner requests. The exact authored model path for `0x1a78` is absent,
  including a trailing space in the filename. It is recorded as unavailable without trimming or substitution.
  Thus 109 installed models are measured and one row is unavailable in the 110-row scene census.
- Longer fourteen-program baseline, 61 full draws: 10,223 accepted / 485 refused pre-draw requests. Actual
  refused pairs rank `0x8500/2` 244, `0x810b/8` 122, `0x810a/12` 91, `0x8569/0` 16, `0x81cf/1` 12.
  The latter owner-point pair triggers at the 25-draw gate. The sixteen-draw baseline has zero such requests.
- Audit at first checkpoint: 2,183 files, zero rejected. First checkpoint pushed at `6ab65bb7`.

Left:
- Complete native after scenes, second clock and per-pair image/raster comparison.
- Default 46-view before/after identity sweep with rebuilt world binaries and recorded hashes.
- Post-build affected selectors, portable suites, private validators, reduced 8d and shared-symbol consumers.
- Final research/handoff/status counts, latest-main integration, audit, PR, ready-prs line, cleanup.

Next step: finish the running 110-row native after capture, then the retained longer fixtures and sweeps.
Local inputs and resumable summaries are in `~/Documents/MTM/mu-mac-tools/native/scratch/render-effects-026`
and `~/Documents/MTM/mu-mac-tools/native/renders/render-effects-026`. Valid full-draw baseline captures are
`full-before` and `later61-before`. Reuse them; do not rerender them. The helper checks fixture arguments when
resuming summaries. Early provisional captures lacking intermediate draws are superseded and are not evidence.

Clean baseline world binary SHA-256, built from `d4af71dd` before edits:
`4954601057b7ee7976c787157b321703d40c65dba68c46901b08d22adb1be76c`.
The diagnostic baseline adds only refusal logging and is kept separately. The current after binary SHA-256 is
`35496e0df40ecf9af86abf070946d696b1bbe2b6a5b29dbbbdb2e70ef5027f29`.
These are different binaries. No default identity result is claimed yet.

Initial iteration failures: native bitmap file count omitted the two new entries; the effect count now derives
from the bitmap total. The first focused sample caught `0x8500/2`'s spin mapped to a saved-angle field instead
of record word `+0x84`; that is corrected. The comparison was not relaxed. The synthetic host's first link
needed its PNG object and a successful native rebuild. Corrected full proof and mutants pass as above.

The scene fixture uses each armour/wing model's corresponding hero slot and a declared weapon slot for other
models. It measures native requests, not equipment eligibility. This is not EFFECTS-025's eight-wearer scene
and its counts must not be compared as the same denominator. No live client, opaque-module work, network,
server state, character-power feature, client-memory writes or owner app changes occurred.
No ready-prs line exists. Several shared-machine load-limit pauses have been necessary.

## WIP, fourth-point correction

Owner cutoff: all work stops by 02:30 on 2026-11-12. If not PR-ready by 02:15, push the WIP handoff and stop
by 02:30. Do not start a check that cannot finish in that window.

Done: the full-draw sixteen-frame after scene has 13,273 accepted / zero refused pre-draw requests,
2,784 / zero owner requests, 825 created / zero unsupported particles, 151.845 s. The initial 61-draw after
has 10,708 / zero pre-draw and 521 created / zero unsupported particles, 29.155 s. These after captures
precede the fourth-point correction and need replacement for the final evidence.

Review found a real coverage gap: `0x8569/0` emits argument 8 values 0..3. Original call `0x017cd01f`
refreshes a fourth cr002 point at OBJECT +0x218 every draw. Native storage previously had only three
points, and the earlier comparator only exercised indices 0..2. The capture queue was stopped before
any default sweep or affected check. The fourth point now has storage, continuous caller refresh and
render routing. The generated tables and item generator remain untouched. The new caller comparison
observes twelve words and complete streams. Its first 348-check sample passes, including 40 original
caller comparisons. A native adapter assertion for ungated frame refresh was added afterward.

Left: full 17,008-check proof, 37 compiled mutants after this correction, final after scenes and both
clock fixtures, default 46-view sweep, affected checks and final docs/PR/ready entry/cleanup. The guarded
proof controller is waiting for resource limits, with logs under the lane scratch directory. The old
32-mutant result does not stand in for the expanded proof. Baseline captures remain valid and must be
reused. Next step: inspect fourth-full-proof.json / proof-steps.json when the guarded run completes.

WIP update, 21:22: the expanded proof passes all 17,008 checks, 47.950 s script / 48.020 s command,
including 2,000 complete original caller streams with twelve point words. Final registry proof passes
348 checks and 37/37 compiled mutants, zero original-machine stops, 92.6 s row / 92.802 s command.
These supersede the narrower initial proof. Source targets are at `8d370d6f`; only public-header comments
and research wording change afterward. Mutants need no further rerun without a target/check change.

Final after scenes are `full-final-after`, `later61-final`, `later61-clock-final`; clock baseline is
`later61-clock-before`. All have zero unsupported particles. Sixteen-draw pre counts are 13,151 / 122 ->
13,273 / zero, owner counts 2,784 / zero unchanged, particles 703 / 122 -> 825 / zero. The later 61-draw
fixture at both clocks is 10,223 / 485 -> 10,708 / zero, particles 36 / 485 -> 521 / zero. Last submitted
particles across the fourteen scenes are 14 -> 223. Full census still has the one unavailable model.

QA passes in 2.50 s. Default sweep: 92/92 PNGs and 92/92 dumps byte-identical, 46 views, 25 default draws,
no draw_all. Before / after walls 61.706 / 87.626 s. Explicit after-world rebuild before sweep 5.441 s.
After binary SHA-256 `52d3a94dac2ab14bcaa0a4d4b61a8fc97a94d097b27c735d500894a59fc548c9`, distinct from
baseline `4954601057b7ee7976c787157b321703d40c65dba68c46901b08d22adb1be76c`. Full item scene has 209/218
saved PNGs byte-identical; both longer scenes have 19/28 identical. Only the six expected caller models
change. The five synthetic native raster controls also pass with the created scale and alpha.

Post-build selection: 86/223 validators, 75.721 s, with movement's shell-object fallback retained;
161/200 suite work items, 153 native modules, 60.758 s. 8d reduced applies. Root build, reduced private
modules, affected portable suites and all 86 affected no-mutant validators are next. Main is still
`d4af71dd`. Final handoff/status/PR/ready entry and cleanup remain after those checks and visual inspection.

## WIP checkpoint, 21:42

Done: final root build passes in 12.407 s. Reduced private run passes all 43 tests, zero skips,
54.529 s command. Affected portable run passes 1,690 tests: 1,400 passed, 290 skipped, zero failures/errors;
353.122 s command including selection, 294.9 s runner wall. Source inputs are at `cd8d586f`.
The 86-row affected private no-mutant batch is running, 31 rows passed so far, no failure reported.
All proofs, 37 mutants and render checks above are complete; representative spark, ring and wing
before/after/difference images were opened and inspected. Do not repeat completed mutants.

Left: finish the affected validator batch and queued audit, replace this WIP history with the final
handoff and status lines, fetch/merge latest main with only required delta checks, final audit/PR/ready
entry/cleanup. Next step: inspect check-steps.json and verify-runs/lane-validators/summary.json when the
running batch ends. Resource guard and the 02:15/02:30 owner cutoff remain binding.

## WIP checkpoint, 22:06

Done: the affected private validator batch has passed 50 of 86 selected rows, zero failures/errors/skips,
863,980 cases so far. The completed proof, 37 mutants, native scenes, identity sweep, root build, 43-test
private pass and 1,690-test portable pass remain as recorded above. Source targets remain unchanged.

Left: finish the remaining affected rows and queued audit, integrate latest main, finalize handoff/research
status, final audit, PR/ready entry and cleanup. Next step: resume the existing guarded check controller;
do not launch a second heavy job. Shared load is above 14, so new checks wait. Owner cutoff remains 02:30.

## WIP checkpoint, 22:26

Done: all 86 affected private no-mutant validators pass, 1,166,680 case checks, zero failures/errors/skips,
2,354.564 s command. The pre-final-doc audit passes: 2,194 files, zero rejected, 24.805 s. Latest main
`710ac816` (#372 UI windows) merges cleanly at `7f94e87d312d711fbf3e21631d25462d96a22bc9`. Root/world
builds pass in 6.182 / 5.434 s. No particle/caller proof target changed, so completed mutants are retained.
Post-merge selection is 12/223 validators (31.043 s), 134/201 suite work items (75.971 s), including 129 native
modules; 8d reduced still applies. The portable delta run is active, with no failures reported.
The earlier sweep's "25 default draws" means 25 simulation frames with default drawing and first/last saves.

Left: finish post-merge portable and reduced-private checks, twelve selected integration validators and an
after-only default sweep against the retained original baseline. Then finalize docs/status/audit, PR, ready
entry and cleanup. Next step: inspect postcheck-steps.json and the existing sequential controller. Load is
above 14, so it waits before new checks. The final handoff draft with all 86 row timings is in lane scratch.

## WIP checkpoint, 22:46

Done: UI-main delta passes 1,424 portable tests (1,167 passed / 257 skipped, zero failures/errors),
459.368 s command / 376.4 s runner; 46 private tests pass with zero skips, 57.897 s command. All twelve
selected integration validators pass, 40,415 cases, 92.894 s command, source `5bf576d6`. Rebuilt world
after-only sweep passes 92/92 PNGs and 92/92 dumps byte-identical, 79.611 s capture / 0.240 s comparison.
Its SHA-256 is `a3512931e8a49e3a68688c6a6ca9e6006f210d2b6fe43482544067d902b54f0e`; original baseline
captures are retained and have not been rerun.

Latest main advanced to `6b75fbda` (batch 103: actors, Muun, aura and app-refresh). It is merged locally,
with registry resolution at `d5e29d71a752bbf872b3881186eabe60fc436a1c`. The registry parses with the repo
Python; all upstream rows/actor expectations survive, and this lane adds 17 lines / deletes zero versus
main. No particle or caller proof target changed. The batch-103 build/selection controller has waited
for load > 14 since roughly 22:34; no heavy lane job ran during that pause.

Left: build and select the latest-main compiled delta, run only its affected checks and a final after
identity sweep, then final docs/status/audit/PR/ready entry/cleanup. Next step: inspect batch103-build-steps.json
and the current controller. The completed 17,008-check / 37-mutant proof and census are still authoritative
for their unchanged targets. Resource and 02:15/02:30 cutoff rules remain binding.

## WIP checkpoint, 23:06

Done: batch-103 root/world builds pass in 15.278 / 7.564 s. Main-delta selection is 59/225 validator
rows (49.363 s), 165/202 suite items (118.776 s). Fresh lane selection is 87/225 rows (113.683 s);
`validate_render_effects28` is the one new lane row and is already in the 59-row delta batch. No row is
uncovered by the initial results plus queued refresh. Particle/caller proof targets still have no
behavior change; the 17,008 checks and 37 mutants remain valid. Report wording now says cases against
original instructions, avoiding an unsupported claim about counted emulator entry calls.

The affected portable delta run is active. Repository policy, model-codec, actor, combat, joint, item
and object suites have passed so far; no failure is reported. Shared resource guards continue to pause
between heavy steps. Source was compiled at `69377e74`; current changes are documentation only.

Left: finish this portable run, the reduced-private modules, 59 delta validators, explicit world rebuild
and final after-only sweep/comparison. Then run the prepared final documentation writer, stage/audit,
fetch/check latest main, commit/push, PR/link/ready entry and cleanup. Next step: resume the existing
sequential controller and inspect batch103-check-steps.json. Finalization refuses incomplete checks.
The 02:15/02:30 cutoff remains binding; no ready-prs entry exists.

## WIP checkpoint, 23:32

Done: all batch-103 checks pass. Portable: 1,773 tests, 1,481 passed / 292 skipped, zero failures/errors,
519.424 s command / 416.7 s runner. Reduced private: 43/43 tests, zero skips, 30.998 s. All 59 delta
validators pass 848,830 cases, zero failures/errors/skips, 882.643 s, source `7a21ba0c`. The rebuilt final
after sweep still matches all 92 PNGs and 92 dumps, 54.788 s capture / 0.185 s comparison; binary SHA-256
`fd290c2a2a7e02e26219c154bf0e8b40a695d3a090b08cd0bf6e0e8c6da8e393`. Original baselines are retained.

Final fetch brought main `fb747e42` (AUDIO-003 and INNER-002). Merged as
`ac51b0dc0bc5e5b6e4a3af57230a622eca0ee45d`; the registry parses with all rows retained, and our diff is
still 17 added registry lines / zero deletions. These incoming changes affect world-object producers and
audio delivery, not the five particle/caller proof targets. INNER-002 documents an intended Elbeland last
PNG change (348 pixels) and its two dumps; 44 unaffected views remain identical. The final sweep must
report this incoming-main difference honestly instead of asserting full old-main identity. Neither new
world producer names any of the five new pairs. No baseline capture or completed mutant is rerun.

Left: build/select the batch-104 compiled delta, run overlapping lane checks and reduced private/portable
checks, then final after sweep with the documented upstream Elbeland difference. Finalize docs/status and
audit, fetch/check main, push/PR/link/ready entry/cleanup afterward. Next step: the prepared batch-104
build/selection controller; all earlier proof/census/render/check reports remain in lane scratch.
No ready-prs entry exists. The 02:15/02:30 cutoff still applies.
