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
