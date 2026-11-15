# MUUN-VISUAL-005

WIP on `codex/muun-visual-005`, based on MUUN-VISUAL-004 `cf4a7b3c` while #397 awaits its steward.
Offline/static/authored fixtures only. No app refresh, installed-app work, live client or service work.

## WIP

- Done: read both task briefs and their required references. Published the complete 386-row initial
  appearance/model classification in `docs/research/muun-appearance-census.csv`, with group sizes in
  `client-muun.md`. The native census loads 379 rows, with six absent assets and one absent item binding.
  All loaded textures resolve. Nine mesh rows and unavailable actions retain explicit refusals.
- Done: authored the four bone-effect rows and the single `0x47a/0` consumer. Added whole-caller original
  verifiers, planned compiled mutants, native request counters and fixture controls. The first native
  source build passed in 12.21 s. Bone rows pass the 51-case small original comparison, including all
  four installed rows and ordered caller samples. These are iteration results, not finish checks.
- Done: explicitly rebuilt baseline `mu-world`, SHA-256
  `459bb5cf69db13136f43223c33aa63e078c06e893024878838a79d1ec48fd50f`.
  Baseline build 41.52 s root, 8.00 s world/host. The 46-view default before sweep took 28.03 + 58.80 s.
  No draw-all/live-time. Canonical private inputs, 640x400, demo names.
- Done: `0x47a` small original comparison passes 60/60 after its OBJECT +0xbc input was correctly
  mapped to velocity.
- Left: run the final full focused comparisons, changed compiled mutants once, private Muun controls and
  fixture proofs. Build and run affected selectors/checks, reduced private tests, final after identity,
  audit, complete docs/status and PR delivery. Merge origin/main once #397 is merged, per task brief.
- Next step: check load/free memory, rebuild `reconstructed/combat`, rerun the small transition comparison,
  then run both final focused verifiers. Inspect every mutant result; a failed compile is not a caught mutant.

## Limits and next

Current code is not PR-ready. Missing meshes/actions stay refused, including `lalaUp.bmd` mesh 3 and
`dandelionUp.bmd` actions 3/4. Secondary particles `0x8081/1`, `0x8082/1`, `0x7ef7/19` remain requested and
refused by existing consumers. Bone effects may expose further missing consumers; report their exact ids.
No original RNG/process-phase, full-scene, live-motion or performance equivalence is claimed.

## Checkpoints and cleanup

Scratch/renders are local under `~/Documents/MTM/mu-mac-tools/native/{scratch,renders}/muun-visual-005`.
No decoded records, models or images are committed. No future-lane input has been created. Finish docs
and all pushes before the ready-prs entry, then remove generated outputs/builds/worktree/local branch.

### Verification progress after the first checkpoint

Both full original comparisons pass: 221 bone cases and 400 transition cases. All 21 bone and seven
transition mutants compile and are caught. The child subtype mutant initially survived because the
sample's random branch was never entered; the deterministic corpus now covers that branch and only
that mutant was retried. Walls: 6.18 + 0.88 s bone runs, 9.10 s transition run. No other mutant was repeated.
New private controls initially passed 4/5 in 15.12 s; the disabled remote control correctly omitted its
report, so its assertion was corrected and that one test passed in 5.38 s. A stronger report check then
passed 24/25 overall in 120.20 s but inspected the final-only effect-model report after expiry. It now
runs a separate 81-frame scene while the effect is alive, plus a 90-frame expired scene; this assertion
still needs its integrated run. Do not call that prior 24/25 batch a pass.

#397 merged during this work. Next checkpoint must merge `origin/main` `df57ab8b` and preserve its
consumer additions. The initial portable selector chose 179 items, 168 native modules, above the 8d cap.
Its wall was 100.47 s. Exclude `native/tests/test_native_app.py` from the portable run as instructed.

### Integrated WIP checkpoint

- Done: resolved main integration by keeping RENDER-EFFECTS-031's already verified `0x47a/0,1` consumer
  and its single model slot, removing this lane's duplicate consumer and slot. Consumer files now match
  origin/main exactly. Both validator registry additions survive. Main's other additions remain intact.
- Done: integrated root build 20.16 s, explicit world build 7.79 s, focused transition private tests
  2/2 pass in 16.52 s. The live 81-frame scene draws one effect model; the 90-frame scene expires it.
  Both GL and software pass the enabled/disabled pixel and post-expiry identity controls.
- Left: final affected selection/run against integrated main, one unchanged-bone mutant result carry,
  new transition verifier controls against main's consumer source, all 25 private Muun tests, persistent
  proof images/inspection, after identity and attribution of imported main deltas, final docs/PR/cleanup.
- Next: inspect resources, run `--list-affected origin/main` for both runners. Record their exact row
  lists, retain fallback rows, exclude app-packaging tests, use 8d reduced, then finish within scope.

### WIP checkpoint during the affected run

- Done: integrated transition comparison 400/400, all seven compiled controls caught, 11.82 s.
  These controls target main's retained consumer; the removed duplicate is not the final implementation.
  The unchanged bone helper retains 221 passing cases and all 21 compiled controls.
- Done: final affected previews against origin/main select 42 validators in 37.48 s and 173 portable
  work items in 116.07 s. All 42 validator rows are retained. The portable run will exclude only
  `native/tests/test_native_app.py`, leaving 172 items. Native selection is 168 modules, so 8d reduced.
- Running: the 42-row private, cached, no-optional-mutants validator batch at source commit `abf4654f`.
  At least 24 rows have passed with no failure. The terrain row and later actor/effect/Muun rows remain.
  Report prefix is local `scratch/muun-visual-005/lane-validators`; the log is `lane-validators.log`.
- Left: complete that runner, integrated 25-test private Muun run, the 172-item portable run, proof
  rendering/inspection, after identity, final docs/status/PR/ready entry and cleanup.
- Next: wait on the current runner, inspect every row and wall time. Run no second heavy job concurrently.
  This checkpoint changes documentation only; compiled inputs remain the audited `abf4654f` source.

### WIP after the first complete check batches

- Done: all 42 affected validators pass, 808,930 reported cases, 942.69 s, source `abf4654f`.
  All 25 private Muun tests pass with zero skips in 127.51 s. The 172-item portable batch passes
  1,509 tests, 1,215 passed / 294 expected skips, zero failures/errors, 416.33 s. App packaging excluded.
- New bounded remainder found during the final limits audit: the remote buff visibility gate has
  four raw-byte groups under supplied predicate/buff inputs, and the fifth seat interval has no pose
  in the default four-category cycle. Both are fixture-admissible without authoritative input.
  Their classification is published in client-muun.md before implementation.
- Left: add/compare the raw visibility gate and a guarded authored fifth-interval pose, compiled
  controls and native proofs; refresh only checks affected by those final source additions. Then
  persistent proof inspection, after identity, final docs/PR/ready entry/cleanup.
- Next: add a pure visibility helper and full original caller verifier. Keep byte +0x16/predicate
  meanings opaque; author their values explicitly. Do not alter actor/item files or production selection.
