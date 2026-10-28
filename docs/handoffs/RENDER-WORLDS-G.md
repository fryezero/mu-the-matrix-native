# RENDER-WORLDS-G

The 48-class inventory and Santa Village/Vulcanus primary methods are implemented.
[Finding, addresses, comparison boundaries and DATA-ACQ-002 needs](../research/client-worlds-g.md).

- Existing worktree `~/Documents/MTM/worktrees/render-worlds-g`, branch `codex/render-worlds-g`.
  Resumed from unreviewed checkpoint `e92e08e`; repaired its empty header and missing Duel Arena source references.
  Kept the sound four create/move bodies, added both complete visual methods and minimal native dispatch.
- Latest main `8eac05c` merged under the merge lock as `7577837`. Shared conflicts preserve A's
  visual consumer/flame/deferred paths, E's event handling and the audio/combat/validator/status integrations. No main-checkout or sibling-worktree edits/builds, live game or launcher,
  network work, protection-module analysis, new captures or private bytes in commits.
- Coverage: **48 classes, 57 world registrations, 288 slot addresses checked; 7/48 classes with verified
  primary work, 19/144 verified primary families, 0 static-only and 125 missing**. Added six verified methods.
- Compiled production C against original Unicorn instructions: **6,000 cases, zero mismatches/stops;
  13/13 compiled mutants caught**. All three primary methods in each world are covered on synthetic objects.
- Coverage annotations also retain A's bounded Karutan visual and Raklion/Karutan custom/after families.
  This updates inventory only; no A/E implementation is changed.
- Synthetic public create/move dispatch and production native preparation tests pass. Hidden geometry still
  emits through real callbacks; missing models do not emit or consume RNG; sibling dispatch remains separate.
- Unaffected tour: **28/28 first/final PNG, 14/14 object dump, 14/14 light dump pairs identical** at the saved 25-frame endpoint.
  Santa/Vulcanus have no captured objects/images; their real-image fidelity is unmeasured.
- Four final registered A/E/G/world-order validators pass: **22,240 cases, zero mismatches/stops,
  48/48 compiled mutants caught**, no skips or errors.
- Full `bash scripts/local-macos-ci.sh` passes on the integrated tree: **1,466 tests in 38 discovery
  suites, 179 explicit skips, zero failures/errors; 7/7 fixture scenarios; viewer/readers build;
  publication audit 1,367 staged files, zero rejected**. Readers were built only. No hosted workflow was used.
  The earlier disk-exhausted gate is retained as prior failed evidence; no tests were excluded in this run.
  `final-local-gate.log` and `final-gate-summary.json` record the complete fresh run.

Reports/manifests are in `~/Documents/MTM/mu-mac-tools/native/scratch/render-worlds-g`, with PNGs in the sibling
`native/renders/render-worlds-g/final-{before,after}`. `final-registered/validate_worlds_g.json` carries
method hashes, case counts and mutation results; `final-fidelity-hashes.json` carries the fresh unchanged
digests against latest main. Earlier before/after artifacts retain their paths and bytes; identical files
were hardlinked to free 296,162,443 bytes. `resume2-dedup.json` records that lossless cleanup.

Next: DATA-ACQ-002 world 62/63 object/model/clock/pool/camera capture and image replay. Continue the inventory's
125 missing primary methods and separately marked custom/after/invisible slots. No claim of full world-class
completion, full nested effect rendering or captured RNG/clock parity. The A/E and previously finished worlds
remain outside this lane.

Self-review of standards, specification, staged paths and integration conflicts found no remaining scoped
defects. No independent review is claimed. The uncommitted host-test change was reviewed, passed and
committed as `2218dfe`; the combined main integration was checkpointed and pushed.
