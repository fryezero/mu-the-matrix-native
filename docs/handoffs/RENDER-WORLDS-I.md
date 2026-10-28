# RENDER-WORLDS-I

Implemented Loren Market/world-79 and Uruk Mountain/world-100 primary create, move and visual methods.
[Finding, exact addresses, service boundaries and DATA-ACQ-002 needs](../research/client-worlds-i.md).

- Owned worktree `~/Documents/MTM/worktrees/render-worlds-i`, branch `codex/render-worlds-i`, from
  origin/main `7d813a9`. Scope claim: issue #209. Per-world C, minimal dispatch/build hooks.
- Six original-instruction families at 1,000 cases each: **6,000 equal, zero mismatches/stops,
  33/33 compiled mutants detected**. AL, OBJECT, ordered output arguments, bone-query order and final RNG
  are compared. Engine/pose boundaries and the native key/color refusals are explicit in the finding.
- Inventory: **48 classes, 57 world registrations, 288 slot addresses checked; 11/48 classes with primary
  coverage; 31/144 verified primary methods, zero static-only and 113 missing**.
- Public lifecycle/log-capacity tests pass. The synthetic production host exercises 21 emitter types at
  200 preparations each, 4,200 total, missing/unloaded models with unchanged RNG, and the real sector-move,
  animation-tick and current-bone light/sprite paths. Changed object origin and missing bones are covered.
- First checkpoint `e6dc48a` was pushed before saved-capture regression and final integration.

Saved October 22 fourteen-view regression against a clean rebuild of base `7d813a9`: **28/28 first/final PNG
hashes, 14/14 OBJECT dump hashes, 14/14 light dump hashes and every complete scoreboard entry identical**.
No world-79/world-100 image score is claimed. Registered G/H/I regression passes **18,000 instruction cases,
zero mismatches/stops, 65/65 compiled mutants**, three pass with no skips/errors. Focused native world tests
pass 8 checks with one private skip; reconstructed world tests pass 11 checks with six private skips.

Preflight full local Mac gate passes on `7d813a9` plus this lane: **1520 tests across 38 discovery runs,
189 explicit skips, zero failures/errors; eight fixture scenarios, viewer/readers builds and the
1,440-file audit with zero rejected**. Readers were built only. The final locked main integration/gate
is recorded below and supersedes these preflight counts.

Supplementary installed-asset GL probes load all seven Market and fourteen Uruk synthetic-object models;
four representative frames were rendered and both final frames were inspected. Placements are authored, not captured. The Market tile-120
probe has zero terrain faces and isolated emitters, so it supplies no town-scene fidelity claim. Uruk's
normal terrain and supported sprite/particle callbacks render; weather remains inactive in this runtime
probe. The C/native host, rather than these views, exercises active weather and key/color refusal.

No original client or launcher was started, stopped, driven or read. No service, wire, protection-module,
main-checkout build or sibling-worktree work. No private bytes, assets, captures, decoded tables, renders
or input links are committed. Self-review covers repository standards, original behavior, host ordering
and evidence boundaries. No independent review is claimed.

Remaining: the 113 other primary methods and separately inventoried custom/after/invisible slots;
DATA-ACQ-002 world 79/100 populations/models/actions/bones/light/clock/RNG/pools/camera/PNG;
Uruk weather state feed, keyed effect and colored joint consumers; requested nested particle lifecycles
and synchronized image replay. The class predicate also accepts world 101, whose registered class remains
separate. The finding records exact acquisition inputs and downstream limits.

During execution, reports/logs are under `~/Documents/MTM/mu-mac-tools/native/scratch/render-worlds-i`,
with renders under the sibling `renders/render-worlds-i`. Both entire task folders, build outputs,
worktree and local branch are removed after merge. No newly created local input needs to survive;
these committed summaries and the PR retain the evidence.

## Final locked verification after resume

The resumed run acquired the merge lock at 10:57 CDT and integrated main `a38ec75` in `e93f7b4`.
Conflicts retain both milestones' documentation and all world/session host targets. The full
`bash scripts/local-macos-ci.sh` passed: **1,548 tests across 38 discovery runs, 191 explicit skips,
zero failures/errors**. The two additional skips since preflight are the newly merged opt-in item-gear
instruction and installed-data temporal tests. All eight fixture scenarios passed, with 67 inbound frames,
zero unbound/undecodable frames, and the existing two unrecovered intents/six unsent frames reported.
Viewer/readers builds passed; readers were not run. The audit checked **1,478 files, zero rejected**.
No hosted workflow was dispatched.

The final registered G/H/I rerun passes **18,000 instruction cases, zero mismatches/stops,
65/65 compiled mutants**, with three passes and no errors/skips. This lane contributes six families,
6,000 cases and 33 mutants. The coverage inventory remains 31/144 primary methods across 11/48 classes.
The final integrated fourteen-view tour matches a fresh rebuild of main `7ce87c6`: **28/28 PNG,
14/14 OBJECT and 14/14 light hashes**, with all complete scoreboard entries equal. The later
RENDER-TIME-001 merge preserves default rendering, and its default-mode tests pass in the full gate.
The original base-`7d813a9` regression above remains historical evidence. No new-world capture or fidelity
score is claimed. Only evidence documentation changes after the final runtime gate.

Checkpoint `b3e26fb` commits the reviewed downstream particle audit; `e93f7b4` checkpoints the integration.
Cleanup removes the entire lane scratch/renders and worktree, including its local builds and input links.
No new local input needs retention. The remaining capture, weather-feed, key/color-consumer, nested-particle
and other-primary-method limits above remain open.
