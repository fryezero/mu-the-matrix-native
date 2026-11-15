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

### WIP after the bounded remainder

- Done: supplied remote-buff values now control the exact four raw-byte visibility groups. No class,
  team or predicate meaning is inferred. A guarded authored rider action reaches the fifth proved
  seat interval; action 280 exists in the canonical player model and restores the hero pose.
- Done: the complete caller comparison passes 388 visibility cases plus 29 fifth-interval boundary
  cases. Eight visibility controls were caught in 39.96 s; the two new seat-boundary controls were
  caught separately in 3.82 s. The combined baseline has 417 cases. New private fixture checks pass
  4/4 in 25.63 s, including GL/software visibility, fifth pose, restoration and invalid flag contexts.
  Source build passed in 13.72 s. None of the earlier bone/transition controls was repeated.
- Left: integrate incoming AUDIO-005 main update, refresh checks whose compiled inputs changed,
  inspect persistent proofs, run the rebuilt default after sweep, finish docs/PR/ready entry/cleanup.
- Next: wait for the shared-host resource guard, audit this source checkpoint, merge origin/main
  with both registry additions retained, then rebuild before the affected selectors.

### WIP during the final source refresh

- Done: audited 2,340 staged files, zero rejected, 50.00 s. Pushed the final bounded implementation
  at `819f2caf`. Merged AUDIO-005 main `8844d3e9` cleanly at `bee48677`; both registry additions survive.
  The integrated root build passed in 22.62 s. No source changes follow that merge.
- Done: affected-since preview from the previously tested `abf4654f` selected 74 rows in 51.72 s,
  including the worlds-r2 symbol fallback. All are retained. Thirty-eight rows have passed so far,
  including the new 417-case visibility row and both incoming audio rows; shared native rows remain.
  Six unchanged earlier Muun rows retain their passing results, giving an 80-row evidence union.
- Running: cached, no-optional-mutants refresh at `bee48677`, two workers, local report prefix
  `scratch/muun-visual-005/validators-refresh`. Terrain and render-effects31 are currently active.
- Left: finish the refresh, portable refresh selection/run without app packaging, all 29 private Muun
  tests, explicit world build, persistent proof inspection and default after identity, final docs/PR/queue
  and cleanup. A complete final handoff draft and render/comparison drivers are in task-local scratch.
- Next: inspect all refresh row outcomes, then recheck resources before the next heavy command.

### WIP after the integrated validator refresh

- Done: all 74 refresh rows pass, 1,203,243 reported cases, zero failures/errors/skips, 1,318.35 s.
  Their compiled source is `bee48677`. Sixty-nine rows disable optional mutants; five have no switch.
  The 80-row latest-result union has 1,208,131 reported cases, with six unchanged Muun functions
  carrying their `abf4654f` results. Local `steward-table.md` records every wall/case count/commit.
- Running: portable affected-since preview from `abf4654f`. The previous 172-item passing portable
  result remains recorded separately; the final source/main refresh has not run yet.
- Left: portable refresh, private 29-test Muun run, persistent proof inspection, final rebuilt after
  identity, completed handoff/status/PR/ready entry and removal of all task-local outputs.
- Next: inspect the portable selection, retain fallback items, exclude the app-packaging module,
  recheck resources and run it with two workers and MU_RECOVERY_INTEGRATION=0.

### WIP portable checkpoint

- Done: the refresh portable preview selects 183 items, including 175 native modules, in 94.33 s.
  Excluding only `native/tests/test_native_app.py` leaves 182 items. Every earlier selected item remains;
  ten added items cover incoming audio/session changes and the new Muun module. No fallback is dropped.
- Running: portable refresh with integration disabled and two workers. Audio, environment, objects and
  tests/ suites have passed; native modules continue without a reported failure. Logs and result prefix
  are local `scratch/muun-visual-005/portable-refresh`. Compiled inputs remain `bee48677`.
- Left: complete portable, run all seven private Muun modules, render/inspect persistent proofs, explicitly
  rebuild world and compare the single default after sweep, then final docs/status/PR/ready entry/cleanup.
- Next: inspect the portable summary, check resources, then build world and run the 29 private tests
  under canonical private-env.sh. `proof.py` and prepared after manifests are in task-local scratch.

### WIP after proofs and the later main update

- Done: portable refresh passes 1,827 tests, 1,472 passed / 355 expected skips, zero failures/errors,
  458.75 s. All 29 private Muun tests pass, zero skips, 147.95 s. Persistent proof has 35 scene PNGs
  plus an inspected contact sheet, 19.83 s; inspected 356/357 separately. All pixel controls pass.
- Done: explicit world checks 0.37 / 0.38 s, binary SHA-256
  `90991825c3fe21ee051c40ee66dfaca702a5bc49a5f3549523b8f9e6df1be52d`.
  The default after sweep takes 21.11 + 50.66 s, compare 0.23 s: 91/92 PNGs, 92/92 dumps, 46/46 stderr
  identical. All 46 reports gain the imported 97-to-99 bitmap vector. Only Remain frame 24 and its
  particle counters also change: accepted/refused 4/3 -> 7/0, matching EFFECTS-031's documented result.
  Every field is retained. No new live capture or second before sweep was made.
- New main integration: batch 117 `d3ec9950` arrived during final verification. Merged at `78a336a5`,
  retaining both registry appends and parsing all 252 rows. The integrated root build passes, 20.08 s.
  Muun sources/checks are unchanged. This is the pinned finish-line base; later main belongs to the steward.
- Left: selectors/checks whose inputs changed from `bee48677`, reduced private Muun plus world-host
  consumer refresh, explicit world/proof/after-only refresh and comparison with the inspected outputs,
  final handoff/status/PR/ready entry/cleanup. Earlier passing evidence is retained for unselected rows.
- Next: wait for the resource guard after the build, preview affected-since `bee48677` for both runners,
  retain fallback rows and exclude app packaging. Do not repeat any unchanged mutation controls.

### WIP pinned-main refresh checkpoint

- Done: post-INNER validator preview selects 78 rows in 90.14 s, including all 42 symbol-level
  fallbacks for the new object source. Nineteen rows are new to this lane's evidence; 21 prior rows
  are unselected and retain their results. The prospective latest-result union is 99 rows.
- Running: cached no-optional-mutants `inner-validators`, two workers, tested HEAD `6633aaf2`, native
  source `78a336a5`. Completed rows pass, including INNER-005, terrain, effect31, actor plain/recipes,
  movement, meshdraw and model-edge. The final summary is still pending. Active exec session is local.
- Prepared: `run-inner-portable.py` expects `test-inner-selection.txt`; app packaging remains excluded.
  The inspected proof and first after sweep were retained as `proof-pre-inner` and `after-pre-inner`.
  `finish.py` builds the final handoff/status/PR prose only once all required successful reports exist.
- Left: finish validators, group the three new registry entries without changing their parsed values,
  preview/run affected portable since `bee48677`, private seven Muun modules plus incoming world host
  and helper module, rebuild world, replay proof/after-only outputs and compare, final audit/docs/PR/queue.
- Next: inspect the final validator summary, then regroup registry, inspect resource guards and run the
  portable preview. Keep main pinned at `d3ec9950` for this finish pass; later main is steward work.

### WIP final test results, resource pause

- Done: all 78 INNER refresh rows pass, 1,196,795 reported cases plus Worlds O without an aggregate
  case count, zero failures/errors/skips, 1,320.55 s. The latest-result union is 99 passing rows,
  1,338,652 reported cases plus Worlds O. No unavailable count is invented.
- Done: grouped the new visibility row beside bones/transition. Parsed values for all 252 entries
  are exactly equal before/after; registry diff from pinned main is still 45 added / zero deleted lines.
  Portable preview selects 178 items, 171 native modules, in 76.22 s. All 177 retained items pass after
  excluding app packaging: 1,764 tests, 1,417 passed / 347 expected skips, zero failures/errors, 443.10 s.
- Waiting: resource guard remains above load 14. No heavy job is running in this lane.
- Left: explicit world build/hash, 35 private tests across seven Muun modules plus native world host
  and reconstructed inner5 helper module, replay proof and both after tours, compare to retained inspected
  outputs, `finish.py --draft`, documentation check, final audit, `finish.py`, commit/push/PR/ready/cleanup.
- Next: recheck resources, then build world and run the private 35-test set. Use the filenames expected
  by `finish.py` and preserve the pre-INNER render directories until comparisons are complete.
