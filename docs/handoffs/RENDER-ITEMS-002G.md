# RENDER-ITEMS-002 part 7

Part 7 adds **76 item bodies**, one weapon, 50 armour and 25 `pet/item` model-group types.
Bounded coverage is **635/1,674 item bodies**, **17/17 class skins** and **twelve link targets/seventeen types**
with native consumers. [The finding](../research/client-render-items.md#part-7-stress-gear-clock-driven-bodies-and-pose-boundary-render-items-002g)
records formulas, addresses and evidence boundaries. Worktree/branch `render-items-002g`, base `40f34a9`.
No live game or launcher was started, stopped, driven or read.

The only refused body in the committed README-STRESS-001 kits was mace `0x0eee`, group 2/index 8.
Every kit body is now admitted. This is bounded command-stream coverage, not a claim that arbitrary gear,
record configurations or model mappings are complete. Twelve more survey shapes are complete at size ranks
11, 12, 16, 27, 28, 31, 35, 40, 41, 53, 58 and 447, for 134 complete shapes. All 1,691 membership rows,
including skins, agree with compiled admission. Original survey identities, ranks and stop counts are preserved.

## Implementation and integration

The shared parameterized body executor adds lazy sine, signed UV-remainder and clamped-wave inputs.
Per-type generated recipes preserve OBJECT blend-light writes across glow tails. The recipe bound grows
from eight to sixteen draws; native output capacity remains 32. Independent cases exposed a saturated-clock
probe fit on flag 0x40000. Additional below-clamp clocks fix generation, and the exact failed original word
at time 791240 has a regression. Five fitting ancient-tail candidates remain refused:
`0x230f/0x248e/0x2490/0x2504/0x270f`.

Three generated pulse-link callers are consumed by the existing saved-pose native adapter:
`0x012cca07` for `0x0afa`, `0x012cbb43` for `0x0eed`, and `0x012cbd11` for `0x0eee`.
The parameterized scalar evaluator preserves colour, scale, bone, offset, rotation and random-call count.
Native hero/remote-player/NPC bodies, ground items and both inventory paths retain the shared body renderer.
Weapon link sprites remain character attachments. The standalone effect-pool admission includes all three.
Missing bones, full pools, saved poses, offsets, clocks and rendered pixels have native checks.

The ground-armour Player-folder fallback now resolves the six glow textures from `Data/Effect`, correcting
the analogous lookup identified by README-STRESS-001. The real synthetic ground loader passes at 6/6
loaded textures. A temporary original-directory compiled mutant fails the same check at 0/6, then the
restored production code passes again. This is native integration evidence, not additional x86 behavior.

## Original-instruction checks

The executable/text/data identities are unchanged. `validate_item_gear.py --mutations` compares compiled
production C with pinned instructions:

| Family | Cases | Mismatches |
|---|---:|---:|
| Complete bounded body streams, 76 types times 292 states | 22,192 | 0 |
| Three full link callers, including random counts | 1,200 | 0 |
| Negative, remainder and signed-conversion clock boundaries | 40 | 0 |
| Rank-5 real pose caller, nineteen types | 608 | 0 |
| Real TransformPosition on authored points after those poses | 1,216 | 0 |
| Total | 25,256 | 0 |

All **10/10 compiled instruction mutants** are detected. Detection counts are mesh index 14,328;
object alpha 18,698; sine frequency 4,672; armour clamp 5,268; UV period 14,013; link bone 1,200;
link scale 1,200; link rotation 300; pose root 608; prior frame 361. Both generated tables reproduce.
The new validator has a manifest row and owning private test. Its body/caller, pose-matrix and authored-point
families retain separate boundaries; they do not compare graphics-driver output or every persistent byte.

Rank 5 now has authored action/bone-track inputs and executes the real pose builder without a pose stub.
The oracle reserves that track storage from CRT allocations and exercises negative/fractional/out-of-range
frames, action clamps and retained roots. The synthetic model has lighting byte zero and an empty named-mesh
registry. Full named-mesh dispatch, lighting-dependent passes, later random/clock rules and native re-pose/
transform/restoration ordering remain unresolved. All nineteen bodies stay refused and uncounted in coverage.

## Native checks and renders

Portable renderchar suite: **44 tests, 10 explicit private-input skips**. Native character renderer:
**9 tests, one installed-client skip**. Ground-item suite: **5 tests, one installed-client skip**.
Both ground skin backends, software inventory and the actual GFx item/FBO consumer: **4 tests, no skips**.
The focused ground-loader negative control is separate from the ten instruction mutants.

Six representative offline before/after PNGs were inspected on authored geometry. The ordinary control
is byte-identical, framebuffer hash `44061fca1b7785a415ca53e4091b7eb9f71aec5fc65e6e32db0eb27c7eb4d3e2`.
The ranked scene replaces three refusals with zero, increases total passes 13 to 44, and changes 6,061 of
120,000 pixels. Its untextured additive geometry saturates white, so these pixels do not prove material
fidelity. The linked-mace scene allocates four sprites and changes 3,672 pixels with authored flare/Shiny02
JPEGs. Its second weapon still has an unrelated refused body and lacks the required bones for that link.
The separate native host exercises all three new links with sufficient bones, then missing bones/full pools.
These are offline native renders, not live-client fidelity comparisons. Earlier images are untouched.

## Release checks

Baseline local macOS gate passes: 1,511 tests across 38 discovery runs, 187 explicit skips, native viewer/readers
and publication audit, 1,429 files and zero rejections. No hosted workflow was dispatched.
Preflight on the part-7 branch passes: **1,518 tests across 38 discovery runs**, **187 explicit skips**,
native viewer/readers and publication audit, **1,435 files, zero rejected**.

Fresh inherited instruction comparisons all have zero mismatches:

| Family | Cases | Compiled mutants caught |
|---|---:|---:|
| Part 3 bodies, links and transforms | 74,292 | 8/8 |
| Part 4 bodies, skins and links | 52,172 | 7/7 |
| Part 5 bodies, skins and links | 25,772 | 9/9 |
| Part 6 bodies and link chains | 17,736 | 6/6 |

Including part 7, this run has **195,228 instruction comparisons**, zero mismatches, and **40/40 compiled
instruction mutants caught**. Self-review against the owner brief, repository standards and the bounded
native consumers found no blocking issue after correcting the saturated-clock probe fit. Complete rank-5
rendering remains partial as stated above.

The resumed release acquired the merge lock and integrated main `89a6ed9` in `ef54116`. The only conflict
was the appended validator manifest entries; both item-gear and combat-audio entries are retained and load.
The locked full Mac gate passes: **1,528 tests across 38 discovery runs**, **188 explicit skips**, zero
failures, viewer/readers built and **1,449 audit files, zero rejected**. Eight fixture scenarios pass all
61 expectations with 67 inbound frames, zero unbound/undecodable frames, and the existing two unrecovered
intents and six unsent frames explicit. The fixture dirty marker reflects only the untracked shared-input
symlinks, not tracked source edits. No hosted workflow was dispatched.

A fresh resumed part-7 run reproduces all **25,256 cases**, zero mismatches, **10/10 mutants** and both
generated tables. All **1,691** TSV memberships independently agree with compiled admission. Re-rendering
on the integrated native build preserves all six before/after PNG hashes and counters, including the
ordinary control, ranked scene and pulse links. No additional private input needs retention.


## Remaining work and cleanup

**1,039 item bodies remain**, including complete rank-5 rendering. Further link targets include the owner-dependent
Laser/17 caller `0x012c8571` and shared-clock/bone-state sword `0x012c91fe`. Authoritative hero instances,
owner-follow/global-random synchronization, model mappings, selection/shadow/buff/record-kind and mesh-override
limits, NewUI and Box of Luck remain. Muun and nested map-object tables stay deferred.

The first checkpoint was pushed as `0a15798`. Only this lane's worktree is edited or built; the audio and
session-global sources remain separate. Reports, six PNGs, authored fixtures and the small baseline binary
are confined to `mu-mac-tools/native/{scratch,renders}/render-items-002g/`. After merge, delete those folders,
lane build/verification outputs, worktree and local branch, and release the merge lock. No new local input
needs retention. Shared Python/evidence symlinks are never staged or traversed during cleanup.
