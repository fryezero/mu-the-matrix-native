# RENDER-EFFECTS-026

Branch `codex/render-effects-026`, base main `d4af71dd`. Codex GPT-6.1 Sol, no subagents.
Offline/static only. The merge steward owns the full gate and merge. No installed app is changed.

## WIP checkpoint

Done:
- Captured the fourteen later item programs, each in a declared single-model hero fixture for sixteen draws.
  Actual refused particles rank `0x8500/2` 8, `0x810b/8` 4, `0x810a/12` 3, `0x81cf/1` 2.
  `0x8569/0` does not trigger in this window and still needs a longer counter fixture.
- Extended that capture to the 110-program inventory. The exact authored model path for `0x1a78` is absent,
  including a trailing space in the filename; the row is marked unavailable, never trimmed or substituted.
  The remaining 109 fixtures have 1,639 accepted / 17 refused pre-draw requests. This fixture differs from
  EFFECTS-025's eight-wearer scenes and is not the same denominator.
- Implemented the five create/move/render branches, two bitmap slots, and `0x8569/0`'s render-time owner point.
- Wrote the focused original comparator, 29 planned compiled mutants, native pool/owner/raster host and tests.
- First 308-check sample: create 80/100, move 82/100, render 100/100, native 5/5, static 3/3.
  The comparison found `0x8500/2`'s spin word mapped to the wrong field. Corrected to `+0x84`, rerun pending.
  The initial native build also caught the effect-file array count; it now derives from the bitmap count.

Left:
- Final focused sample, full comparisons and changed-target mutants.
- Longer later-program scene including `0x8569/0`; before/after installed scenes, synthetic per-pair PNGs,
  raster differences, default 46-view identity sweep with explicitly rebuilt binaries and hashes.
- Affected selectors, portable suites, private validators, reduced 8d, shared-symbol consumers, audit.
- Research part 39, final handoff/status lines, latest-main integration, PR, ready-prs line and cleanup.

Next step: finish the corrected build, then run the focused proof before starting the affected checks.
Local inputs and resumable baseline summaries are in `~/Documents/MTM/mu-mac-tools/native/scratch/render-effects-026`
and `~/Documents/MTM/mu-mac-tools/native/renders/render-effects-026`. The scene helper skips completed summaries;
valid baseline captures must not be rerendered. The clean baseline world binary SHA-256 is
`4954601057b7ee7976c787157b321703d40c65dba68c46901b08d22adb1be76c`.
The diagnostic baseline adds only refusal logging. Both binaries are retained locally for pending captures.
No ready-prs line exists at this checkpoint. Several load-limit pauses have been necessary.

Checkpoint correction: the corrected 308-check focused sample passes completely. The scene helper review
found that its first runs saved only first/last draws. Those census numbers above are provisional and are
superseded by the pending full-draw captures. The helper now explicitly enables every intermediate draw and
uses each armour/wing model's corresponding slot. No valid full-draw baseline exists yet. Default identity
sweeps deliberately retain the standard default draw rather than draw_all.
