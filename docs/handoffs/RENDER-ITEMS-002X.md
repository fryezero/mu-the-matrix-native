# RENDER-ITEMS-002X

## WIP (stopped 2026-11-09)

Stopped at the owner's explicit "finish work now" instruction. **WIP, not PR-ready.** PR #361 remains draft.
No ready-prs entry was written. Worktree `~/Documents/MTM/worktrees/render-items-002x` is retained; branch
`codex/render-items-002x`. The last compiled implementation checkpoint is `cdfbcb3f`; the stop commit adds this
handoff and the test correction described below. No compiled implementation changes follow that checkpoint.

### Resume verification, 2026-11-09

Resumed on the existing branch and worktree. Main `ff8e0543` is merged at `b4a95ec3`; the merge changes only
APP-REFRESH-011 docs and three native test modules, with no compiled implementation changes. The corrected
renderchar suite passes: 111 tests, 87 passed, 24 private skips, 1.32 s. Root build passes, 27.24 s.
The completed affected portable run selects 145 work items, including 140 native modules: 1,376 tests,
1,146 passed, 230 skipped, zero failures/errors, 349.78 s including selection and 303.3 s runner wall.
The canonical private renderer module passes 23/23 with no skips, 7.95 s. **8d reduced** remains applicable.
The post-build validator selection is unchanged at 52 rows, 42.32 s, including the movement symbol fallback;
nine unused-symbol rows are pruned. Fifty unchanged rows are now running without mutants at `b4a95ec3`.
The two changed mutant rows and final default identity sweep remain pending. This is still WIP, not ready.

Second resume checkpoint: 42/50 unchanged selected rows pass, 733,596 comparisons,
zero failures/errors/skips. The full batch is still running; partial reports are retained under
`verify-runs/resume-validators/`. The first resume audit passes, 2,136 files and zero rejected, 30.28 s.
No implementation edits follow `cdfbcb3f`; the merge and checkpoint edits do not change compiled inputs.

### Bodies and verified work

- Bodies **1,404 -> 1,424 / 1,674**, **250 left**: fourteen of the 21 read-program candidates and six of the
  historical 54 helper-count types admitted. Seven read-program, 48 helper-count and 195 other bodies remain.
  The four largest other groups screened add none. Rejected helper-call prototypes were removed.
- Both full tables generated, **868.00 s**. Body rows 1,385 -> 1,405; body header **482,415 bytes**, owner header
  **262,949 bytes**, both below the audit limit. No public ABI, scalar cap or operation cap change.
- New body screens: fourteen times 292 states, then six times 292 states, zero mismatches; **353.33 / 50.60 s**.
  Fourteen complete owned programs: **896 states**, exact draw/request/refusal/random streams, **6.58 s**.
- Root build passes, **9.23 s**. C-to-C against saved prerequisite main: **216,448 states**, **213,888 identical**,
  exactly twenty intended types change with 128 states each, **6.10 s**.
- Survey: **1,691 types / 798 shapes**, **67.17 s**. Export fixed to use `gen.ALL_TYPES`; exactly twenty memberships
  and nine shape totals change, complete shapes **600 -> 609**. Raw shapes, addresses and stopped states unchanged.
  Native-admission/export regression passes: three tests, one private skip, **0.10 s**.
- Targeted portable smoke: **18 tests, 16 passed, two private skips**, **0.17 s**. The stale derived-phase regression
  fails before the reset and passes after, **0.10 / 0.08 s**. Audits passed at the earlier checkpoints,
  **16.41 / 16.01 s**, 2,135 files and zero rejected.

### Interrupted and unrun checks

The portable affected run selected **145 / 192 work items**, including **140 native modules**, with two workers.
It was terminated at the owner stop, so it has **no passing aggregate result**. Recorded completed root suites:
model-codec 58 tests / eight skips / 4.4 s, path 30 / one / 1.4 s, movement 13 / one / 0.2 s and tests 275 /
42 / 57.8 s. Renderchar ran 111 tests with 24 private skips and one failure in 1.5 s: an old refusal example
still expected newly admitted `0x2301` to fail. Its example now uses still-unadmitted `0x230d`; this correction
**has not been rerun**. The native portion was interrupted. The owned test process tree was killed at stop.

**None of the 52 selected private validator rows has run in this lane yet.** Their selection took **44.84 s**,
keeps the movement symbol fallback and prunes nine unrelated rows. Mutants remain unrun: `validate_item_predraw`
**49** and `validate_item_groups` **2**, once each. All other selected rows run without mutants.
The canonical private native renderer module is also unrun. **8d reduced:** 140 native items exceeds 40, so run
only the changed `native/tests/test_native_renderchar.py` privately. No full lane gate.

Only the default-draw **baseline** was taken: 46 maps, 92 PNGs, 92 dumps and 46 reports, **62.18 s**. The single
final identity sweep is **unrun**. Do not report byte identity as passed and do not rerun the baseline.
Full table reproduction through the affected validators, the final documentation/status lines and final audit
also remain pending. No steward handoff or merge is authorized by this WIP state.

### Exact next steps

1. From this worktree's root, check load/memory/disk and run `nice -n 10 make -j4` after the output cleanup.
   Run the corrected renderchar suite with `MU_RECOVERY_INTEGRATION=0 MU_GATE_JOBS=2` and
   `tools/python/bin/python scripts/run_test_suites.py reconstructed/renderchar`. Then complete the interrupted
   portable selection with `scripts/run_test_suites.py --affected origin/main`, the same portable env and nice.
2. Source `. ~/Documents/MTM/mu-mac-tools/native/private-env.sh` from the root. Set
   `MU_SECTION3="$HOME/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin"` where needed.
   Run `nice -n 10 tools/python/bin/python -m unittest discover -s native/tests -p test_native_renderchar.py`.
   This is the reduced private native pass; leave session/fixture/private duplicates out.
3. Recheck affected selection after build. Run its unchanged rows with
   `scripts/run_validators.py --private --no-mutants --cache --only "$ROWS" --jobs 2 --report verify-runs/resume-validators`.
   `$ROWS` is the selection below minus the two mutant rows. Then run those two once with
   `scripts/run_validators.py --private --cache --only validate_item_predraw,validate_item_groups --jobs 2 --report verify-runs/resume-mutants`.
   Use nice and the canonical private env. The committed headers are generated already; do not repeat a cold
   full extraction merely to build. The validators check reproduction using the shared original cache.
4. Build `nice -n 10 make -C native -j4 world`, then run the retained `tour.py after` under nice with the canonical
   env. It compares the final default draws to `before-tour.json`: 92 PNGs, 92 dumps and 46 normalized reports,
   no draw_all. The C-to-C comparison is already passed at `cdfbcb3f`; rerun it only if compiled inputs change.
5. Merge latest main, apply TEST BUDGET 6/8b/8c only to changed compiled inputs, and recheck research numbering
   against main before push. Current part 36 was free on main at the implementation push; RENDER-ACTORS-001 may
   take that number later. Finish status lines, per-validator case counts/wall times, audit, PR body and final
   push before any ready-prs line. Only then mark #361 ready and append once. Until then it stays WIP/draft.

### Retained local inputs and cleanup

Keep only small resume material in `~/Documents/MTM/mu-mac-tools/native/scratch/render-items-002x/`:
`before-tour.json`, `tour.py`, `run.py`, `times.jsonl`, `identity.json`, selection JSON/logs, `batch1.txt` and
`batch2.txt`, and the partial portable log. The batch files partition the unchanged selected validators, excluding
the two mutant rows; each runner still uses at most two workers. Partial module logs stay in the worktree's
`verify-runs/test-suites-20261109-025852-ks2fpf_0/`. They are diagnostics, not a completed result.
Large exploratory libraries, the raw survey JSON, lane renders, owned temporary test trees and build outputs are
removed at stop. The worktree and input/tool symlinks remain. Shared captures, shared validator cache, main,
Native Preview and Wine apps are untouched. No new private capture needs retention.

Steward validators (selected only, **not run**, not ready): validate_item_ranked, validate_item_continuation, validate_item_expansion, validate_item_clusters, validate_item_types, validate_fidelity, validate_meshdraw, validate_model_edge, validate_movement, validate_renderchar, validate_icarus_c2, validate_audio_callers, validate_item_gear, validate_item_next, validate_render_effects5, validate_render_effects7, validate_render_effects9, validate_render_effects10, validate_render_effects11, validate_render_effects12, validate_audio_domains, validate_audio_items, validate_item_coverage, validate_item_wings_next, validate_item_scalars, validate_item_chains, validate_item_carry, validate_item_quality, validate_item_product, validate_item_derived, validate_item_ownerfx, validate_item_predraw, validate_item_hiddenmesh, validate_render_effects13, validate_render_effects14, validate_render_effects15, validate_render_effects16, validate_render_effects17, validate_item_callers, validate_inventory_fx, validate_render_effects18, validate_render_effects19, validate_render_effects20, validate_render_effects21, validate_item_cloak, validate_armour_cloak, validate_render_effects22, validate_item_named, validate_npc_cloak, validate_render_effects23, validate_render_effects24, validate_item_groups.

Implementation checkpoint, not ready for steward. Branch `codex/render-items-002x`, from `54a53e1a`, after
prerequisite PR #360 reported MERGED. Codex, GPT-6.1 Sol; no subagents. Offline/static only. The installed
Native Preview and Wine apps are untouched. No full gate in the lane.

## Result

Bodies **1,404 -> 1,424 of 1,674**, leaving **250**. Skins stay 17/17; links stay eighteen targets/twenty-four types.
Both complete tables are generated from pinned instruction extraction. Recipe rows 1,385 -> 1,405; `item_bodies.h`
is 482,415 bytes, below 512 KiB. Survey membership changes for exactly twenty types; nine shape totals change,
complete shapes 600 -> 609 of 798. Raw shapes, classifications and stopped states are unchanged.

Fourteen types also pass their complete owned pre-program comparison. Final affected suites, private rows,
mutants and the single final default-draw identity sweep are pending.

Read-program types: `0x0b29`, `0x0b52`, `0x0f1e`, `0x174a`, `0x2301`, `0x2302`, `0x23a8`, `0x23a9`,
`0x23ed`, `0x23ee`, `0x23fe`, `0x23ff`, `0x2403`, `0x2404`. They need extended probes, correct nested-range
random attribution and, except the two swords, carried model fields. Existing binary32 scalar/products retain
exact draw words. The seven other candidates remain rejected.

No-glow types: `0x232c..0x2330` and `0x26f5`. They bypass the ordinary level-glow helper chain, including
fixture records with kind B `0x26/0x5b`. Their new validator checks both random states and those records.

## Checks so far

- Baseline root build: pass, 28.71 s; world target: pass, 4.06 s.
- Baseline default tours: 46 maps, 92 PNGs, 92 dumps and 46 reports hashed once, 62.18 s. Images removed.
- Read-program screen: 21 candidates; 14 pass 292 independent body states each, 353.33 s.
- Owned program screen: all fourteen pass 64 states each, 896 total, 6.58 s. Ordered draw/request/refusal streams
  and exact random consumption agree. Counts are harness requests, not native particle-pool creations.
- No-glow screen: 23 candidates; six pass 292 independent body states each, 50.60 s.
- Consecutive-helper experiments: no admissions, 120.71 / 168.11 s. Prototype removed.

The largest-group screen adds no body: twelve types in four groups, 210.20 s including a stale-phase exception;
the corrected two-type tail completes in 13.16 s. A portable regression fails before the phase reset and passes
after it, 0.10 / 0.08 s. The rejected helper-group prototype is absent from the source.

Additional implementation checks:

- Complete table extraction: pass, 868.00 s.
- Root build after table generation: pass, 9.23 s.
- C-to-C against saved prerequisite main library: 216,448 states, 213,888 identical; exactly the intended twenty
  types change, 128 states each, 6.10 s.
- Targeted portable modules: 18 tests, 16 passed and two private skips, 0.17 s.
- Full survey: 1,691 types / 798 shapes, 67.17 s. The old export's hand-maintained membership list omitted the
  named and no-glow lists. It now uses `gen.ALL_TYPES`; a portable test compares the exported membership with
  native `mu_rc_item_special` over all 1,691 types. Three tests pass, one private skip, 0.10 s. Re-export uses the
  saved raw survey, without a second instruction survey.

## Limits

Affected portable/native checks, private validators, mutants and the one final byte-identity sweep are pending. The checkpoint is not a readiness claim. No comparison was relaxed.
The later groups retain unresolved input/model state and effect/matrix work. Existing pose/bone/record/buff,
selected-item, process-random and process-counter limits remain. No new particle consumer is claimed.

## Next groups

Resume only the remaining verification sequence in the WIP section above. Table generation and the ordered
implementation screens are complete. Do not start another admission group or queue this draft without resuming
the stopped task and completing its required checks.
