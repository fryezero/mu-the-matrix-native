# RENDER-WORLDS-L

Issue #231. Implements Karutan `0x801c/16`, Raklion `0x8086/2`, `0x8087/6`,
`0x8089/2`, and the optional recorded Market batch `0x801e/0`, `0x801c/8`,
`0x801b/4`. Registers `0x7f6b` as Shiny04, plus mono02/mono03/WATERFALL5.
All five loader mappings, including existing mono01, match original calls.
[Finding, provenance, checks and limits](../research/client-worlds-l.md).

Owns the new particle include, minimal shared admission/lifecycle hooks,
load-time bitmap registrations and dedicated validator/native host/test. No
world producer, perf/mesh/scene, item, session or audio implementation changes.
No per-frame allocation, original-client run or new capture. Worktree created
from origin/main `037a889`; ignored Python/evidence links are never staged.

## Evidence before the lock

- 21,000 checks, zero mismatches/stops: 19,390 original-instruction comparisons
  and 1,610 native removal checks. Seven kinds, 1,000 cases per kind/family.
- 13/13 compiled authored-C mutants caught; five original loader-call sequences.
- Native synthetic host: seven consumers, four registrations, eight quads,
  400 producer preparations, eight absent/unloaded-model checks, eight full-pool
  checks, absent assets and six unsupported-neighbor checks.
- Existing particle suite: 23 tests, two explicit private skips; prior effects
  suite: five tests, two explicit private skips. J producer host passes its
  3,600 preparations and refusal boundaries.
- Saved-tour baseline `037a889`: all 14 OBJECT/light hashes and 26 PNG hashes
  across 13 other views unchanged. Karutan's two PNGs intentionally change at
  the left edge, 377/692 pixels. Raklion's camera emits no particles; its PNG
  is regression evidence, with emitter coverage supplied by the native host.
- Three representative images visually inspected. No original Karutan PNG,
  image-fidelity score, live acceptance or synchronized-pool claim.

## Remaining work

Uruk's weather-keyed/colored consumers remain excluded. Karutan smoke subtypes
69/13, other nested consumers, missing world populations, original image and
phase evidence remain open. Primary-method coverage is unchanged by this lane.

## Integration and cleanup

Join the merge queue only after focused checks and review. Hold the common lock
for latest-main integration, the full local Mac gate, PR and merge; release it
immediately afterwards. Preserve the other active lanes' shared documentation
and build/validator entries. Final locked results are appended below.

After merge remove `mu-mac-tools/native/{scratch,renders}/render-worlds-l`, all
worktree builds/temp outputs, the worktree and local branch. No new retained
INPUT is required. Durable evidence lives in the committed finding/handoff and
PR body. Fast-forward the main checkout only if it is clean and on main.
