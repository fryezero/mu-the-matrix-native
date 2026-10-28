# Built-in world visual producers, RENDER-WORLDS-K

## Scope and evidence

Verified against restored text SHA-256 `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` and second image section
SHA-256 `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`. This uses the existing compatibility-environment
captures, not native Windows or a running game. No live game or new capture was used.

| Family | Original interval, end exclusive | Cases | Mismatches / stops |
|---|---|---:|---:|
| losttower_visual | `0x17fa92b..0x17fb1a2` | 1,200 | 0 / 0 |
| tarkan_visual | `0x17fb2a4..0x17fb7e7` | 1,200 | 0 / 0 |
| icarus_flare | `0x17fbf34..0x17fc01e` | 1,200 | 0 / 0 |
| losttower_push | `0x17f6ca7..0x17f71d5` | 1,200 | 0 / 0 |
| atlans_dispatch | `0x17f9758..0x17fccce` | 1,200 | 0 / 0 |

The four producer/helper families and the Atlans dispatch family total **6,000 cases, zero mismatches/stops**.
All **18/18 compiled production-C mutants** are detected. The comparison checks the full OBJECT,
ordered output arguments, bone names and RNG state, including absent models, hidden guards, strict clock
boundaries, negative clocks, action boundaries, exact push radius, and bounded output capacity.
The Atlans family records the original switch landing at `0x017fcb5c`; it skips the common event/custom/factory
hook chain. It proves that world 7 has no dedicated visual switch case, not that every common hook is a no-op.
The inventory's earlier "remaining Atlans visual body" entry was incorrect.

`world_builtin_visual.c` contains authored source. Client instructions execute under Unicorn;
engine calls are recording stubs. Named-bone lookup and TransformPosition supply synthetic coordinates.
Scalar sine and square root use the established host-libm boundary. The final native C rounds the sine's
float input through double `sin` and back to float, matching the existing validator boundary. One `sinf`
result differed by one bit at the long-clock sample and was corrected before the final comparisons.

Lost Tower type 23 passes an unwritten local as TransformPosition's input in the pinned instructions.
The comparison records its bone name and supplies the synthetic origin without reading that local,
as the earlier Lorencia type-56 family does. Native uses the bone origin. Exact stack-dependent output
for that one transform is unverified. Missing named bones and poses also remain a host boundary;
no stale pose from another object is used.

## Reconstructed behavior and integration

Lost Tower visual `0x017fa92b` adds types 19/20's three pairs of counter-rotating lights, type 23's
two coincident flare sprites, and type 40/41's paired sprites at object position plus Z=260.
Type 19 uses bitmap `0x7f84`; type 20/40 uses `0x7f37`; type 41 uses `0x7f38`.
The helper `0x017f6ca7` is movement, despite its old VISUAL call label. Types 38/39 react within
50 units to hero actions 50..110 when their X velocity is below 0.1, emit sound `0x7c`, damp
translation/rotation velocities by 0.6 and apply them. The world part supplies the current hero action.
The original action/radius/velocity boundaries and sound arguments are compared, not inferred from an image.

Tarkan visual `0x017fb2a4` adds type 63's oscillating Bone02 lamp and types 60/70/76/83's
plume producers. Type 60 creates 20 particles once before hiding the mesh. Type 83 uses a strict
angle-shifted clock window, a secondary half-scale plume, then the original `0x419/0x41a` effect request.
Icarus type 10 transforms Bone01 and emits particle `0x7ef7/0`, size 1, white light, no owner.
Its existing cover hook still consumes the common brightness from the particle RNG; the added producer
does not reseed or consume it a second time. The other Icarus types retain the old cover route.

The native object preparation and movement paths consume these events through existing callbacks.
A synthetic four-bone model verifies current-pose world positions across two origins, missing-model guards,
Tarkan one-shot emission, Icarus's exact call record, and the real Lost Tower movement callback.
The log-capacity regression checks equal state/RNG at capacities 0, 1 and 64. Per-frame work adds no heap
allocation. No Raklion/Karutan, item, mesh, scene, effect, particle or joint implementation is changed by K.

Downstream ownership stays with EFFECTS-003. Before that lane merges, unsupported particles keep their
existing behavior. Required consumers are `0x7ef7` subtype **0** and `0x7f5a` subtypes **4/6/7/8**.
Required sprite registrations are `0x7f84`, `0x7f38`, `0x8021`. Pinned original LoadBitmap calls are
`0x01821599` for Magic_Ground2.jpg, `0x01822345` for lightning3.jpg and `0x01821f65` for Impack03.jpg,
respectively, each LINEAR/CLAMP with final flags 1,0. Those source facts were sent to the owning lane.
Producer comparisons and host callbacks do not claim those missing consumers draw.

## Fourteen-view tour

Base `3a61d99`, 25 steps, 1722 by 1048, unchanged tour masks, camera and objects/plain inputs.
Only three full-resolution original PNGs survive. A dash means unavailable, never a zero image error.
All fourteen primary-grid mean errors are zero; missing and extra placements are zero on both sides.
All OBJECT and light dump hashes remain equal. The following are errors against saved original inputs,
not a synchronized RNG/clock/pool replay.

| View | Image mean absolute error before / after | Static field differences before / after | Frame-light mean error before / after |
|---|---:|---:|---:|
| 00b-lorencia | - / - | 17 / 17 | 0.00713 / 0.00713 |
| 01-dungeon | 2.019 / 2.019 | 0 / 0 | 0.04404 / 0.04404 |
| 02-devias | - / - | 0 / 0 | 0.0 / 0.0 |
| 02b-devias-town | - / - | 4 / 4 | 0.00068 / 0.00068 |
| 03-noria | - / - | 23 / 23 | 0.02568 / 0.02568 |
| 04-losttower | - / - | 25 / 25 | 0.02683 / 0.02683 |
| 07-atlans | - / - | 57 / 57 | 0.01404 / 0.01404 |
| 08-tarkan | - / - | 3 / 3 | 0.0 / 0.0 |
| 10-icarus | 26.897 / 26.897 | 3 / 3 | 0.0 / 0.0 |
| 33-aida | - / - | 5 / 5 | 0.65117 / 0.65117 |
| 37-kanturu | 4.006 / 4.006 | 3 / 3 | 0.01387 / 0.01387 |
| 51-elbeland | - / - | 8 / 8 | 0.02078 / 0.02078 |
| 57-raklion | - / - | 6 / 6 | 0.02574 / 0.02574 |
| 80-karutan | - / - | 6 / 6 | 0.01493 / 0.01493 |

Lost Tower's two native PNG hashes change; all **26/26 unaffected first/final PNG hashes** are equal,
along with **14/14 OBJECT** and **14/14 light** hashes. Its new lights are visible at the arrival frame's
lower-right edge. The unchanged image scores are Dungeon **2.019**, Icarus **26.897**, Kanturu **4.006**.
Icarus's object-particle request count changes 0 to 46; this is expected call evidence, not visible output.
No measured original-image improvement is claimed for Lost Tower because its original PNG is absent.
Only a handful of representative PNGs were kept during work; the bulk tour frames were removed after hashing.

## Reproduction and remaining work

Run `tools/python/bin/python scripts/validate_worlds_k.py --cases 1200 --mutations --output <local-json>`,
or the registered `validate_worlds_k` row. `native/tests/test_native_worlds_k.py` uses authored models only.
The [handoff](../handoffs/RENDER-WORLDS-K.md) records the final latest-main gate and regression counts.
Reports live only in the lane's scratch/renders folders during work and are deleted after merge.

Remaining inputs for exact image claims: original Lost Tower/Atlans/Tarkan PNGs at the saved camera and size,
matching world time, RNG state and ordered particle/sprite/effect pools, and the Lost Tower type-23 transform
input or a separately captured executable revision which initializes it. Existing Aida light-reset history,
Elbeland captured speeds and other built-in after-character scope remain as previously documented.
The other 37 factory classes without captures are outside this milestone. DATA-ACQ-002 remains their input path.

## Post-J regression

J merge `26018b4f` is integrated as `d7853c0`. The combined G/H/I/J/K run passes **30,000 instruction
cases**, zero mismatches/stops, all **113 compiled mutants**. Ten native world-host tests pass with one
explicit private skip. A clean J-main build in this owned worktree supplies the new tour baseline;
only Lost Tower's first/final PNGs change with K. All 26 other PNGs, 14 OBJECT and 14 light hashes match.
The pre-J and post-J K tours differ only in the three Karutan artifacts documented by J.
The image scores remain 2.019 / 26.897 / 4.006; no new original image was acquired.

## Hidden Tarkan producers

A later lifecycle audit found that MoveObject hides Tarkan type 63 before rendering. The native host now
poses this lamp even when its mesh is hidden, so Bone02 comes from the current object rather than suppressing
the sprite request. Type 60 is also exempt from imported hidden sidecars until its first visual burst.
Authored native assertions cover both startup state and the hidden lamp's exact world position.
Removing either host clause in a separately compiled native mutant is detected: **2/2 host controls**,
followed by a restored production host pass. These are additional to the 18 instruction-compared mutants.
The first ad-hoc mutant attempt exposed same-second make caching; the final checks explicitly remove the
owned runtime object, archive and host executable before each compile, including restoration.
The final post-EFFECTS-003 tour and gate must cover these host fixes; the earlier tour counts above predate them.
