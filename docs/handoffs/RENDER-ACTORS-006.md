# RENDER-ACTORS-006

## WIP

This lane is stacked on ACTORS-005, PR #389 at `e3347dd7`. The assigned
worktree and branch are `render-actors-006` and `codex/render-actors-006`.
No subagents, live process, network/service acquisition or installed app work.

Done: read the full lane/common brief, resume, actor handoffs and research;
classify all 905 initially incomplete selectors into disjoint groups; build
the base; rebuild `mu-world` and capture the 230-file default identity baseline.
The baseline binary SHA-256 is
`f58907ce03d1fb3658445cdcfa3a9eaa86772f8738012769ecb756ba474f4fb5`.
Baseline sweep takes 79.36 s; the initial root build takes 26.64 s.
A failed first tour used stale local capture paths and produced no baseline;
only the corrected lane-local manifest contributes to these counts.

The draft verifier/generator checks each selector's constructor, original
opener arguments and action/model bytes, whole RenderCharacter caller, actual
native files, complete texture uploads and draw/alpha. It executes both
character sprite emitters that the shared character verifier normally skips.
Rows failing any uniform check will stay incomplete with a recorded reason.
Generation is currently queued behind the load guard. No admission is claimed.

Left: finish generation and inspect rejected rows; integrate the generated
native plan API and both backends; compiled mutants; affected checks; private
8d reduced; representative proof renders; final identity replay; main
integration, audit, final documentation, PR and ready entry. No ready entry.
Next: inspect the generation report under the lane's external scratch folder.

## Initial groups

| Missing checked plan | Rows |
|---|---:|
| Plain monster body | 203 |
| Repeated default body | 473 |
| Plain NPC body | 84 |
| Constructor equipment/parts | 107 |
| Special appearance | 18 |
| Extra bitmap | 6 |
| Special appearance, extra bitmap and equipment | 4 |
| Extra bitmap and equipment | 4 |
| Secondary model with auxiliary/action lifetime | 4 |
| Special appearance and equipment | 2 |
| Total initially incomplete | 905 |

These are fixture selectors, including repeats. Construction labels identify
which checked body/attachment/appearance proof is missing, rather than
asserting a known missing visual for every row. Plain construction alone does
not certify later rendering. The detailed before-population and per-row
outcomes are in `docs/research/actor-admission-groups.csv`.

Checkpoint 2026-11-14 22:48: the initial uniform run verifies 622 rows and 102
models, 8,482 positive checks, 45.00 s. It rejects 54 monster/default candidates
with explicit reasons, including class 918's two missing textures. The generated
plan API and both native backend call sites build in 20.88 s. The expanded
28-context-per-row run is queued behind the load guard. The table and counts
remain provisional until that run and the final compiled controls pass.
The construction/opener CSVs have not yet been regenerated. All final checks,
proofs, identity replay, main integration, audit and publication remain pending.

Checkpoint 2026-11-14 23:08: source commit `55535150` supersedes the provisional
622-row result. The expanded run verifies 621 plans / 101 model files with
23,366 positive checks, 223.99 s plus a 60 s resource wait. Both census CSVs
reproduce 660 checked / 284 incomplete / 80 refused, 5.56 s plus a 120 s wait.
Accepted groups are 153 ordinary monster and 468 repeated-default contexts;
five repeated-default selectors fail independently. Source audit: 2,276 files,
zero rejected, 19.53 s. Portable new-module check: one passed and one expected
private skip, 0.08 s. The 30-row affected validator run is in progress at
`55535150`; three symbol fallbacks remain selected. Portable selection is
170 work items / 162 native modules, so the private finish uses 8d reduced.
Left: finish validators, constructor appearance-state audit, compiled controls,
portable affected suites, reduced private modules, proof renders, identity,
latest-main integration, final audit/docs and PR/ready publication. No ready
entry and no completion claim.

Checkpoint 2026-11-14 23:30: the 621-row source/result is provisional and is
superseded by the constructor write audit. It found 27 hidden/blend-mesh
contexts and 44 subtype contexts that the earlier constructor recorder had
not checked. These 71 rows are excluded, with explicit offsets in the decision
CSV. The revised generator verifies 550 plans / 51 actual model files,
20,410 positive checks, 212.21 s plus a 60 s resource wait. The final API replay
will have 21,437 checks and nine compiled controls, still pending. Latest main
through AUDIO-004 (`2b0b2716`) is merged; both lanes' status/validator entries
are retained. The merge-resolution follow-up removes all markers and parses
the registry with the repository Python. PR #389 remains unmerged.

The rebuilt 550-row library, canonical census regeneration and final checks
are queued behind the resource guard. Until that command finishes, the class
and opener CSVs in this WIP checkpoint still contain the old 621-row counts.
Expected final census is 589 checked / 355 incomplete / 80 refused. Do not use
the earlier 30-row/147,157-check result as validation of this revised table.
Next: finish the queued rebuild/census/focused test, audit and commit the
consistent revised source, then run the selected validators and new-row
controls once on that source. Portable affected, 8d reduced, proof renders,
identity, final documentation/audit, PR and ready entry remain unfinished.

Checkpoint 2026-11-14 23:50: consistent source is `d3688570`, with 550 admitted
selector plans / 51 exact model files, 82 ordinary and 468 repeated-default
contexts. Canonical CSV regeneration now confirms 589 checked / 355 incomplete /
80 refused, 5.35 s plus a 60 s wait. Root rebuild: 10.53 s plus 420 s of waits.
The focused census test passes, with one expected private skip, 0.08 s.
Audit: 2,282 staged files, zero rejected, 29.25 s.

The final new-row run passes all 21,437 checks and catches all nine compiled
controls with zero unexpected stops, 197.2 s plus a 120 s wait. Final post-build
selection has 31 rows, including AUDIO-004's new object-audio validator. The
other thirty selected rows are running without mutants at the same source;
no optional controls from unchanged validators are replayed. No code change
has followed the new-row pass. Left: finish those rows, portable affected
suites, 8d reduced, rebuilt-world identity and representative proof renders,
latest-main check, final docs/audit, PR/ready entry and cleanup. No PR or ready
entry exists yet. All earlier provisional admissions are superseded by 550.

Checkpoint 2026-11-15 00:13: the frozen actor source `d3688570` passes all
31 selected rows: 154,294 checks, zero failures/errors/skips, with nine current
compiled controls caught once. The other thirty rows take 403.89 s plus a
120 s wait; the new row takes 197.2 s plus a 120 s wait. Portable affected:
171 work items, 1,563 tests, 1,288 passed / 275 expected skips, zero failures or
errors, 406.7 s runner / 479.69 s command. The new grouped summary partitions
all 905 original rows and refines the 107 weapon plans into 60 right / 34 both /
13 left; it also separates joints, EffectManager, cloth/world and secondary
consumer gaps. These are missing checked plans, not a whole-client percentage.

Latest main is now `4babc900`, including merged PR #389 and INNER-004's
scene/raster alpha-reference changes. Main integration and affected-input
rechecks are next. The earlier default baseline remains recorded at ACTORS-005;
any incoming world/alpha changes must be distinguished from this actor lane's
identity. Private 8d reduced, final identity/proofs, final documentation/audit,
PR/ready entry and cleanup remain pending. No PR or ready line exists yet.

Checkpoint 2026-11-15 00:44: main through `4babc900`, including merged #389 and
INNER-004, is integrated as `71a6d23f`. Post-merge root build passes, 16.53 s
plus 720 s of waits. Final actor selection has 29 rows; the input-delta selector
keeps 27 for replay and retains audio-combat and viewport-monster passes from
`d3688570`. The 27-row no-mutant replay is running. Current shared status files
match main's order, and the registry diff adds only this lane's row.

Scope exception: the first portable selection included `test_native_app.py`.
It built/signed a temporary test bundle and passed eighteen synthetic tests;
its installed-game test was skipped. The fixture's teardown removes the
bundle. No installed Preview app was changed. This temporary packaging was
outside the lane's no-packaging boundary and is not repeated. The local
integration portable wrapper explicitly excludes that module.

UI-WINDOWS-003 has since merged as `a95880c4`; do not merge it while the current
validator processes read the tree. Next: finish the frozen replay, integrate UI,
recheck only its affected compiled inputs, run the permitted portable delta,
private 8d reduced, identity/proofs and final docs/audit, then publish/queue/clean.
No PR or ready entry exists. The nine actor controls remain at `d3688570`; their
target source is unchanged by the renderer integration.

Checkpoint 2026-11-15 00:58: main through UI-WINDOWS-003 `a95880c4` is integrated
as `04879bea`. Its nine affected validator rows pass, 128.15 s plus a
120 s resource wait. The earlier 27-row integration replay also passes,
390.73 s plus a 60 s wait. Final selected coverage is 29 rows / 138,721
checks with zero failures/errors/skips. Per-row tested commits are retained.
The refined census separates classes 1/5/10 sword-sprite work and partitions
all 905 initial rows into thirty groups. Portable integration is waiting on
load; the wrapper excludes temporary app packaging. Left: permitted portable
integration, private 8d reduced, identity/proofs, final docs/audit and PR/ready
publication and cleanup. No PR or ready entry exists yet.

Checkpoint 2026-11-15 01:16: portable integration passes 1,792 tests, 1,454 passed /
338 expected skips / zero failures or errors, 362.9 s runner and 850.37 s
command including 360 s resource wait. Private 8d reduced passes both actor
tests, zero skips, 165.64 s command. Explicitly rebuilt identity passes
227/230 file hashes and all 45 unaffected views; the three differences are
exactly INNER-004 Kanturu-37 PNGs/report. After binary is
`0b9bcf21d7766ce6da790a63e96826e5cd432183ea2ae21c56a5817b2516133d`.
Proof rendering is waiting on load. Final review moves the native test host
result publication after resource cleanup, so a cleanup failure cannot leave
a successful row in the batch. This output-only host correction needs the
new-row positive replay; production code, checks and compiled-mutant targets
are unchanged. Left: proof renders, focused positive replay, final docs/audit,
PR/ready publication and cleanup. No PR or ready entry exists yet.
