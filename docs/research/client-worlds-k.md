# Built-in world visuals, RENDER-WORLDS-K

Icarus's type-10 Bone01 flares now run through the native producer and particle host. In the final
full-draw tour, saved-original image error falls **26.897 to 23.154**, a 13.9% reduction. Lost Tower gains
its paired visual lights and hero-driven push helper; Tarkan gains lamp/plume producers, including its
hidden Bone02 lamp. Atlans's inventory is corrected: world 7 has no dedicated visual switch case.
This milestone adds no factory class and does not change the 33/144 primary-method count.

## Provenance and verified scope

Restored text SHA-256 `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`, based at `0x00401000`;
second image section SHA-256 `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`, based at `0x01a7c000`.
These are existing compatibility-environment captures, not native Windows evidence. No live game,
launcher, new capture, service, protection module or running-client memory was used.

| Family | Original interval, end exclusive | Cases | Mismatches / stops |
|---|---|---:|---:|
| losttower_visual | `0x17fa92b..0x17fb1a2` | 1,200 | 0 / 0 |
| tarkan_visual | `0x17fb2a4..0x17fb7e7` | 1,200 | 0 / 0 |
| icarus_flare | `0x17fbf34..0x17fc01e` | 1,200 | 0 / 0 |
| losttower_push | `0x17f6ca7..0x17f71d5` | 1,200 | 0 / 0 |
| atlans_dispatch | `0x17f9758..0x17fccce` | 1,200 | 0 / 0 |

The four producer/helper families and one dispatch family total **6,000 equal cases**, zero
mismatches/stops, and detect **21/21 compiled production-C mutants**. Full OBJECT bytes, ordered expanded
call arguments, bone names and RNG state are compared. Coverage includes absent models, hidden guards,
finite positive/negative clocks, signed nonzero angle offsets, strict clock/action/velocity/radius
boundaries and adjacent/default types. Mutants cover bitmap/scale/rotation, burst count, random divisor,
subtype, bone name, angle multiplier, strict bounds, damping and dispatch.

Original instructions execute under Unicorn. Model lookup, named-bone lookup/TransformPosition,
particle/sprite/effect/audio services are recording boundaries. Scalar sine and square root use the
established host-libm boundary. Native C rounds the sine's float input through double sin and back to
float, matching that boundary. The initial sinf implementation differed by one bit at a long clock;
the final implementation and corpus match.

The Atlans family observes the actual original switch landing at `0x017fcb5c`, including the model
and common-RNG prefix, then skips the common event/custom/factory hook chain. It proves no dedicated
Atlans visual case exists, not that every common hook is a no-op. The earlier "remaining Atlans visual
body" entry was incorrect.

Lost Tower type 23 passes an unwritten local into TransformPosition in the pinned instructions.
Its comparison records Box03 and supplies a synthetic origin without reading that local, as the
older Lorencia type-56 comparison does. Native uses the bone origin. Exact stack-dependent output
for that one transform remains unverified. Missing poses/named bones and captured animation phase
remain service boundaries. All nine required bone names exist in the five installed affected models.

## Reconstructed behavior and native integration

Lost Tower visual `0x017fa92b` adds three pairs of counter-rotating lights for types 19/20, two
coincident flare sprites for type 23, and paired sprites at object position plus Z=260 for types
40/41. Their bitmaps are 0x7f84, 0x7f37, 0x7ef7 and 0x7f38 as selected by the original branches.
Helper `0x017f6ca7` is movement despite its historical VISUAL call label. Types 38/39 react within
50 units to hero actions 50..110 when X velocity is below 0.1, emit sound 0x7c, damp translation
and rotation velocity by 0.6, and apply them. The object world part supplies the current hero action.

Tarkan visual `0x017fb2a4` adds type 63's oscillating Bone02 lamp and types 60/70/76/83's plume
producers. Type 60 creates 20 particles once before hiding its mesh. Type 83 uses a strict
angle-shifted clock window, a secondary half-scale plume and the original 0x419/0x41a effect request.
The native adapter poses type 63 even though MoveObject hides its mesh, so the attachment uses
this object's current bones. Imported hidden sidecars cannot pre-suppress type 60's first burst.

Icarus type 10 emits particle 0x7ef7/0 at Bone01, size 1, white light, no owner. Its existing cover
hook still consumes the common brightness from the particle RNG. The new producer does not consume
that prefix twice, and other Icarus types retain the C2 cover route.

Existing callbacks consume the new events. The authored native host verifies two posed origins,
missing/unloaded-model gates, one-shot startup, hidden-lamp world position, Icarus's exact request,
and the real Lost Tower movement callback. Zero/one/full log capacities preserve state and RNG.
Two separately compiled native host mutants remove the startup exemption or hidden-lamp pose;
both assertions fail, and the restored production host passes. Those **2/2 controls** are separate
from the 21 source mutants. The first ad-hoc attempt exposed same-second make caching; the final
controls explicitly removed the owned runtime object, archive and host executable before compiling.
No new per-frame heap allocation is added. The installed-model check finds **9/9 names in 5 models**.

EFFECTS-003, PR #230, merge `037a8899ffbd461338cddf25498f76ac03c56020`, supplies create/move/render
consumers for 0x7ef7 subtype 0 and 0x7f5a subtypes 4/6/7/8, plus sprite registrations 0x7f84, 0x7f38,
0x8021. Original loader sites are 0x01821599 Magic_Ground2.jpg, 0x01822345 lightning3.jpg and
0x01821f65 Impack03.jpg, each LINEAR/CLAMP/1,0. K changes no effect, particle, joint, item, mesh,
scene or audio implementation; those incoming lane changes are preserved.

Static remaining binding: Stone01/Stone02 lifecycle exists in reconstructed/combat/skill_fx.c,
and the combat renderer loads both. The separate world-particle fx_model_files table lacks slots
for 0x419/0x41a, so that renderer skips their model draws. K compares and emits the calls without
claiming that nested model output or expanding the effect lane.

## Final fourteen-view tour

Fresh baseline `037a8899`, built by temporarily detaching this owned worktree, then returning to K
and clean-building again. No main or other checkout was built or edited. Both runs use all 25 draw
frames at 1722 by 1048, unchanged masks/camera/objects inputs, `--time-series-every 25`, and only
first/final PNG outputs. This prevents skipped-render frame-sprite accumulation. The earlier
capture-only checkpoint scores and 26 unaffected hashes remain historical evidence from that mode;
they are not mixed into this final comparison.

A dash means the original PNG is unavailable, never zero error. All fourteen primary light grids
have zero mean error over 65,536 cells each. Every view has zero missing and zero extra objects on
both sides. Camera/object/light comparison entries and all 14 OBJECT/14 light hashes are identical.

| View | Image error before / after | Static field differences before / after | Frame-light error before / after |
|---|---:|---:|---:|
| 00b-lorencia | - / - | 17 / 17 | 0.00713 / 0.00713 |
| 01-dungeon | 2.021 / 2.021 | 0 / 0 | 0.04404 / 0.04404 |
| 02-devias | - / - | 0 / 0 | 0.0 / 0.0 |
| 02b-devias-town | - / - | 4 / 4 | 0.00068 / 0.00068 |
| 03-noria | - / - | 23 / 23 | 0.02568 / 0.02568 |
| 04-losttower | - / - | 25 / 25 | 0.02683 / 0.02683 |
| 07-atlans | - / - | 57 / 57 | 0.01404 / 0.01404 |
| 08-tarkan | - / - | 3 / 3 | 0.0 / 0.0 |
| 10-icarus | 26.897 / 23.154 | 3 / 3 | 0.0 / 0.0 |
| 33-aida | - / - | 5 / 5 | 0.65117 / 0.65117 |
| 37-kanturu | 3.444 / 3.444 | 3 / 3 | 0.00637 / 0.00637 |
| 51-elbeland | - / - | 8 / 8 | 0.02078 / 0.02078 |
| 57-raklion | - / - | 6 / 6 | 0.02574 / 0.02574 |
| 80-karutan | - / - | 6 / 6 | 0.00883 / 0.00883 |

Only Lost Tower and Icarus first/final PNGs change. All **24/24 unaffected PNG hashes**, **14/14
OBJECT hashes** and **14/14 light hashes** match. J's Karutan changes are already in both builds.
Icarus's particle request count rises 0 to 575, exactly 23 visible type-10 objects over 25 draws.
The three surviving original-image scores are Dungeon **2.021 → 2.021**, Icarus **26.897 → 23.154**,
Kanturu **3.444 → 3.444**. These are masked RGB mean absolute differences, lower is better.
The measured gain is the whole K change, including its resulting particle/RNG/pool state, not an
ablation attributing every changed pixel to the direct flare draw. No clock or brightness tuning
was used to fit the still.

Final native Lost Tower/Icarus views and a separate Tarkan Bone02 lamp view at tile 14,206 were
visually inspected. The hidden lamp's blue sprite draws above its model. That custom view is native
integration evidence only; it has no original PNG. Only a handful of representative PNGs remain
during work, and all lane outputs are deleted after merge.

## Checks and remaining work

The final registered G/H/I/J/K run passes **30,000 instruction cases**, zero mismatches/stops,
**116/116 compiled source mutants**. The registered consumer regression adds **900 checks and
7/7 mutants**. All six rows pass with no errors/skips. Native world-host discovery passes 10 tests
with one explicit private skip. The [handoff](../handoffs/RENDER-WORLDS-K.md) records the final
locked Mac gate, audit, publication and cleanup.

Reproduce K with `tools/python/bin/python scripts/validate_worlds_k.py --cases 1200 --mutations
--output <local-json>` or its registered validator row. The production fixture is
native/tests/test_native_worlds_k.py. Reports and images live only in the lane's local scratch/renders
folders during work and are deleted after merge. No new local input needs retention.

Remaining exact-fidelity inputs: the eleven missing original PNGs, synchronized clock/RNG/ordered
effect pools, original hero/equipment state beyond the existing masks, and the Lost Tower type-23
transform input or an executable revision which initializes it. Aida reset history and Elbeland
captured speeds retain their earlier limits. The other 37 factory classes without captures are
outside K; their 111 primary methods and separately inventoried custom/after/invisible slots need
DATA-ACQ-002 evidence. World-host Stone01/02 model binding remains separate as stated above.
