# RENDER-ITEMS-002 part 8

Base `a38ec75`, isolated branch/worktree `codex/render-items-002h`, issue #218.
Checkpoints `8f108c7` and `25793c8` were pushed. Only this lane was edited/built.
No live game or launcher was read, started, stopped or driven. No hosted CI was used.

## Coverage and implementation

Bounded bodies increase **635 to 662 of 1,674**, all **17/17 skins** remain,
and consumed links increase **twelve targets/seventeen types to fourteen/nineteen**.
The additions are nineteen rank-5 types and eight armour types at size ranks 83/88.
All 1,691 survey memberships agree with compiled admission. Historical identities,
ranks and stopped-state observations are preserved. The five rejected ancient-tail
candidates remain refused. See the [finding](../research/client-render-items.md#part-8-rank-5-mesh-streams-and-further-links-render-items-002h).

Rank-5 mesh streams now run in the existing no-owner body domain, with lighting,
exact-name Blue mesh lookup, random blend light, signed UV frames and generic tails.
The real original pose builder executes in the comparison. The native adapter keeps
incoming geometry because the original does not re-transform it between its internal
pose call and its mesh draws. The omitted pose writes feed later owner effects;
neither persistent pose-state equivalence nor those effects are claimed here.

The native adapter borrows the existing particle random stream. Without one, the
standalone viewer has an explicit zero random input. New paths allocate no storage
per frame. No effect/particle/joint implementation, perf, mesh or scene file changed.
Minimal body hooks provide the random stream to hero/remote/NPC/ground/GFx callers.
Two more saved-pose character links run: spear 0x10f0 at 0x012cd341, shield 0x16f5
at 0x012cb9d7. Their unrelated body branches remain refused.

## Checks

The new original-instruction validator has a manifest row and owning private test:

| Family | Cases | Mismatches |
|---|---:|---:|
| Rank-5 full no-owner mesh streams, nineteen types, both lighting states | 11,096 | 0 |
| Rank-5 supported records and signed/conversion clock boundaries | 760 | 0 |
| Eight further ranked armour bodies | 2,336 | 0 |
| Two complete link callers | 800 | 0 |
| Total | 14,992 | 0 |

The combined **14,992 cases** reproduce both generated tables and detect **9/9
compiled mutants**. Detection counts: base mesh count 11,856; lighting branch
11,856; pulse period 5,681; UV period 4,355; random range 4,731; named mesh 2,184;
body alpha 2,336; link bone 800; link scale 800.

Inherited part 6 passes **17,736 cases, 6/6 mutants**; part 7 passes **25,256 cases,
10/10 mutants**. Together these runs cover **57,984 comparisons, zero mismatches,
25/25 mutants**. Every family has zero mismatches. All **635 existing generated
rows** retain identical recipes and scalar flags after re-indexing; only eight
rows are added. The preflight local Mac gate passes **1,548 tests across 38
runs, 191 explicit skips**, viewer/readers and publication audit, **1,472 files,
zero rejected**. The final serialized integration gate remains below.
Portable renderchar: **47 tests, eleven explicit skips**. Native renderer:
**ten tests, one installed-client skip**. Ground skin backends, software inventory
and actual GFx icon FBO: **four tests, zero skips**. Native links check saved
translations, offsets, missing bones and full pools. Rank-5 checks distinguish
lighting, missing/present names, clock pixels and repeated frames.

## Renders

Six PNGs compare three authored scenes, with baseline item sources from `a38ec75`
linked against the same surrounding renderer. The ordinary control stays identical,
SHA-256 `308aad6447474892fd2f7cabf6dff610b9e59fa602a05c04552c5aeff25a62c9`.
Rank-5/ranked armour replaces two refusals with zero, increases passes 17 to 36,
and changes 7,490/120,000 pixels. Untextured additive geometry saturates white;
this is no claim of material fidelity. Spear/shield links allocate ten sprites,
change 25,912 pixels with authored textures and retain two unrelated body refusals.
These are inspected offline native renders, not original-client pixels.

## Remaining work and cleanup

**1,012 bodies remain.** Full rank-5 owner rendering remains incomplete: readable
OBJECT bones 35/26 lead to 0x84e2/0x83de particles, 0x7fdd sprites, additional
level-9 overlays and pose-state effects. The no-owner result is not proof of these
paths. Further links include owner-dependent Laser/17 at 0x012c8571 and shared
clock/bone state at 0x012c91fe. Authoritative hero instances, owner/global-random
synchronization, model mappings, selection/shadow/buff/record-kind and mesh-override
limits, NewUI and external Box of Luck remain. Muun/nested map-object work is deferred.

Local scratch/renders are scoped to `mu-mac-tools/native/{scratch,renders}/render-items-002h/`.
After merge, delete both folders, lane build/verification outputs, worktree and local
branch; release the merge lock. Shared Python/evidence symlinks are never staged or
traversed during cleanup. No new local input needs retention.
