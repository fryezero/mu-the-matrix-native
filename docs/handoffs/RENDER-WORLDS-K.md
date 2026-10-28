# RENDER-WORLDS-K

## Result

Implements built-in Lost Tower sprites and hero-driven push, Tarkan lamp/plume producers and the
Icarus type-10 Bone01 flare. Atlans's inventory is corrected: its switch selects the default hook
chain, not a dedicated visual case. The 37 uncaptured factory classes remain outside this lane.
[Finding and complete fourteen-view scoreboard](../research/client-worlds-k.md).

Final full-draw image error: Dungeon **2.021 → 2.021**, Icarus **26.897 → 23.154**, Kanturu
**3.444 → 3.444**. Icarus improves 13.9%. Eleven original PNGs are unavailable, so those image
scores remain unavailable. Only Lost Tower/Icarus endpoint PNGs change. All **24/24 unaffected
PNG**, **14/14 OBJECT** and **14/14 light** hashes match the fresh main baseline.
Every camera/object/light comparison entry is unchanged; all fourteen primary grids remain exact,
and every view retains zero missing/extra objects. No synchronized live-fidelity claim is made.

## Locked integration and checks

Acquired the queued merge lock at **12:53 CDT**, removed only K's queue entry and integrated latest
main **037a8899ffbd461338cddf25498f76ac03c56020** as **d8a2008**. This includes J #227,
audio #228, map overlays #229 and EFFECTS-003 #230. Conflicting shared status entries and registry
rows retain both sides. J's Raklion/Karutan per-world files are untouched by K.

- `bash scripts/local-macos-ci.sh`: **1,585 tests across 38 discovery runs**, **201 explicit
  private/optional skips**, zero failures/errors; **10/10 fixture scenarios**; native viewer and
  read-only reader builds; publication audit **1,537 files, zero rejected**. Readers were built,
  never run. No hosted workflow was dispatched.
- Final registered G/H/I/J/K: **30,000 original-instruction cases**, zero mismatches/stops,
  **116/116 compiled source mutants**, five passes. K contributes five families, **6,000 cases
  and 21 mutants**. Signed nonzero angle offsets and strict clock/action/velocity/radius boundaries
  are included. Original client instructions are never mutated.
- Registered world-particle consumer regression: **900 checks**, zero differences, **7/7 compiled
  mutants**. All six registered rows pass with zero errors/skips. The larger consumer corpus and
  exact original texture registrations belong to EFFECTS-003's published evidence.
- Native world-host discovery: **10 tests**, one explicit private skip. K's authored model host
  checks current pose across two origins, missing/unloaded models, one-shot startup, hidden Tarkan
  lamp position, Icarus's exact request and real Lost Tower movement. Bounded logs preserve state/RNG.
- **2/2 separately compiled native host controls** catch removal of the type-60 startup exemption
  or type-63 hidden-lamp pose. The restored production host passes. The first ad-hoc attempt exposed
  same-second make caching; final controls explicitly rebuild the runtime object/archive/executable.
- Offline installed-model inspection: **9/9 required named bones across five models** are present.
  Seventeen portable registry tests and the publication audit pass after resolving incoming rows.

No runtime code changed after the final gate. Final evidence/status documentation and generated coverage
wording are checked with the audit before publication. Self-review covers standards, scope, call order,
model/pose/startup gates and evidence limits. No independent delegated review is claimed.

## Tour method and visible checks

Clean-built baseline 037a8899 by temporarily detaching this owned worktree, then returned to K and
clean-built it. Main and other agents' checkouts were never built or edited. Both tours run 25 full
draw frames at 1722 by 1048 with unchanged camera/masks/objects, `--time-series-every 25`, and only
first/final PNG outputs. The earlier capture-only checkpoint's Dungeon/Kanturu scores and 26 unaffected
hashes are historical evidence from that mode and are not mixed with the final full-draw comparison.

The Icarus request counter changes 0 to **575**, exactly 23 visible type-10 objects over 25 draws.
Final Lost Tower/Icarus and a separate native Tarkan lamp view at tile **14,206**, 1280 by 720,
were visually inspected. The hidden Bone02 lamp's blue sprite draws above the model. The custom view
has no original PNG and supplies integration evidence only. Bulk PNGs are deleted once hashed/scored;
only a handful of endpoints are retained during work. The complete per-view scores are in the finding.

## Scope and limits

The shared object dispatcher changes are limited to these built-in routes, current named bones and
hero-action plumbing. Existing callbacks consume the producers. Type-60 sidecars cannot suppress the
initial plume; type-63's hidden mesh still gets a current pose. No new per-frame allocation is added.
EFFECTS-003 supplies particle 0x7ef7/0 and 0x7f5a/4/6/7/8 consumers plus sprite registrations
0x7f84/0x7f38/0x8021. K changes no particle/effect/joint, item, perf/mesh/scene or audio implementation.

Lost Tower type 23's original transform input is unwritten. Its comparison treats the transform as
an engine boundary; native uses the bone origin. Exact stack-dependent output remains unverified.
Atlans compares only the model/RNG prefix and switch landing; common event/custom/factory hooks
are outside that family. Scalar trig/sqrt and model/bone services retain their stated boundaries.

Remaining: eleven missing original PNGs, synchronized clock/RNG/ordered effect pools, original
hero/equipment beyond the current masks, the type-23 transform input, earlier Aida reset history and
Elbeland speeds. The world-particle renderer still lacks Stone01/02 model slots for type 83's nested
0x419/0x41a requests, although their lifecycle and combat-host models exist. The other 37 uncaptured
factory classes, 111 primary methods and separate custom/after/invisible slots need DATA-ACQ-002.
No new capture or live original client/launcher action was performed.

## Reproduction and cleanup

Use repo Python with `scripts/validate_worlds_k.py --cases 1200 --mutations --output <local-json>`
or the registered row. `native/tests/test_native_worlds_k.py` generates only authored synthetic BMDs.
Checkpoints include b741954, 0383327, d7853c0, de0d939, 8273cb0, b23a5aa, 881f0f4, 53bc671,
9f84f04 and d8a2008. The PR retains the final gate and counts.

After merge, delete the entire lane directories
`~/Documents/MTM/mu-mac-tools/native/{scratch,renders}/render-worlds-k`, all owned build/temporary outputs,
input symlinks, this worktree and its local branch. No new local input needs retention. Committed docs
and the PR are the durable evidence. The final reply confirms cleanup.
