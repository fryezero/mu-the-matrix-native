# RENDER-ITEMS-002 part 10

Base `9e0cceb`, isolated branch/worktree `codex/render-items-002j`, issue #234.
Checkpoints `752d4d8` and `f8523d5` are pushed. Only this lane is edited/built. No live client,
launcher or hosted workflow is used.

## Coverage and implementation

Bounded bodies increase **769 to 880 of 1,674**, adding **111 types**: 104 armour,
one weapon and the six requested types `0x2322..0x2327`. All **17/17 skins** remain.
Links increase **fifteen targets/twenty types to seventeen/twenty-two**.
The survey now has 228 complete shapes, up from 192. Exact membership is in the
C rules and both TSVs. Original identities, ranks, service sites and stopped
observations are preserved. **794 bodies remain.**

The survey calls the six requested types wings by model-index inference. The
installed Item.bmd model getter instead maps them to elemental seeds, item codes
6204..6209 and `Data/Item/s30_seed.bmd`. This is a mapping observation, not a new
weapon/equipment feed. The initial arbitrary wing-model gallery is discarded.
The final gallery uses the recorded seed mapping and the real native inventory
renderer. It must not be reported as six new wearable wings.

Their body branch `0x016f5f3e..0x016f6253` emits two fixed-colour passes, flags
2/0x44, and suppresses ordinary level glow. Excellent/ancient tails still run.
OBJECT hidden mesh `+0x68` is now an explicit input for these six types only.
The native viewer supplies -1 so the seed model's only mesh is visible. Independent
full functions vary -1/0/2 separately from flags and clocks. The old fixed-zero
boundary would hide the only mesh. Other body families keep their previous domain.
No generic hidden-mesh/texture override support is claimed.

The ranked armour additions include ranks 39, 42, 57, 64, 65, 67, 76, 77, 78,
84 and 89. Rank-39/42 atlas meshes use signed truncated time: `(tick%600)/20`
with a 6-column 0.167/0.2 grid, and `(tick%455)/35` with a 4-column 0.25 grid.
Their ancient meshes retain preceding body light while preserving model shade
separately. Fourteen types have that explicit flag; it does not alter older rows.
Other new scalar paths are strict absolute sine at time*0.0008, the -6 wave
with remainder -1047 and binary64 0.9 plus binary32 0.1, clamped above one,
and the existing -4 wave without its caller offsets. Only requested scalars run.
The generator uses thirteen scalar bits and still emits bounded stack-only draws.

The first independent screen admitted 97 of 166 candidates and rejected 69.
After correcting the atlas ancient-light handling, all fourteen atlas types pass;
the other **55 probe-fitting candidates stay refused**. Earlier ancient-tail
exclusions remain refused. Hidden-mesh probes are independent of render flags;
the full comparison caught a constant fit when those inputs were correlated.

## Further shield links

- `0x16f7`, target `0x012db542..0x012dba1c`: bones 4..10 emit 0x7ef7 at scale
  1.5 with RGB (0.8,0.6,0.2); bones 1/2/3 emit 0x7fe0 at scales 0.5/0.3/0.3,
  with strict abs(sin(time*0.0005)) grey.
- `0x16fb`, target `0x012dc0f3..0x012dc628`: bones 4..7 emit 0x7ef7 at scale
  1.2 with `(abs(sin(time*0.001))+0.1)*(0.2,0.2,0.8)`; bones 8..13 use scale
  1.4 and multipliers (0.2,0.6,0.6).

Both consume the common random intensity once although unused. Caller comparisons
include hand/back-carry variants and the original differing sprite owner arguments.
These one-frame sprites use the existing native no-owner pool. Their position
helper `0x012b678d` is compared separately with production transform math, with
absent owner overrides, nonzero saved translations, model scale and object origin.
No persistent owner-follow claim is made. No new bitmap or particle consumer is
needed. Native admission, saved-pose, bounds, full-pool and random-count tests
cover both links. Ground/inventory retain body rules, not character-link sprites.

## Checks

Pinned executable/text/data identities in the [finding](../research/client-render-items.md)
apply unchanged. The new validator has an owning private test and manifest row.
The strict run passes **33,622 comparisons, zero mismatches**:

| Family | Cases | Mismatches |
|---|---:|---:|
| Full body streams, 111 types times 292 states, including seed hidden-mesh variants | 32,412 | 0 |
| Signed/atlas/conversion and negative-zero clock boundaries | 210 | 0 |
| Two full shield callers, random sequences and hand variants | 800 | 0 |
| Real shield position helper versus compiled production transform math | 200 | 0 |

Both generated tables reproduce. All **12/12 separately compiled mutants** fail:
hidden mesh 1,170 detections; atlas ancient light 1,443; level suppression 941;
atlas period 3,974; atlas frame 718; fast pulse 21,013; strict absolute sine 3,250;
mesh index 30,870; object alpha 32,330; ancient phase 7,021; shield pulse 300;
shield bone 800. Body random consumption is explicitly trapped and absent in
this subset; shield callers each retain one random call.

All **750 earlier generated recipe rows** retain their complete rules and
metadata after re-indexing, with the new retain-ancient flag zero. The inherited part-9 validator passes **31,724 cases, zero mismatches and 9/9
compiled mutants**, and reproduces both tables on the final source. Together,
these runs provide **65,346 instruction comparisons, zero mismatches and 21/21
mutants**. The serialized gate remains pending below.

Portable renderchar: **56 tests, thirteen explicit private-input skips**.
Native character renderer: **13 tests, one installed-client skip**. The new
single-mesh seed regression checks visible triangles and different seed colours;
it fails with the inherited hidden-zero adapter. All 1,691 survey memberships
agree with compiled admission. Compiled C-to-C checks on the final item record cover all 786 previous
body/skin types in 25,152 cases with zero mismatches.

## Representative native renders

Eight PNGs, four before/after pairs, are scoped to this lane. The seed inventory
uses installed geometry/textures and the recorded Item.bmd mapping. It draws all
six models, with zero missing models; triangles increase **96 to 288** and **431
pixels change** to the six prescribed colours. The atlas scene replaces one
refusal with zero, **5 to 10 passes**, and **6,335 pixels change**. Untextured
synthetic armour saturates white, so its pixels do not establish material fidelity.
The shield scene allocates **twenty sprites** with installed effect textures and
changes **49,519/120,000 pixels**. One unrelated shield body remains refused.
The ordinary control is byte-identical, framebuffer SHA-256
`44061fca1b7785a415ca53e4091b7eb9f71aec5fc65e6e32db0eb27c7eb4d3e2`.
These are inspected offline native renders, not original-client pixel comparisons.

## Limits and cleanup

**794 bodies**, further links, authoritative hero instances, owner/global-random
synchronization, model availability and prior record/buff/selection/shadow/override,
NewUI and external Box of Luck limits remain. Rank-5 owner bones 35/26, particles
0x84e2/0x83de, sprites 0x7fdd, level-9 overlays and pose-state handling belong to
the effects continuation. Muun and nested map-object tables remain deferred.

Only item-render paths changed. No perf/mesh/scene, world/particle, audio or session
implementation changed; no shared caller/build hook or per-frame allocation was
added. The added OBJECT field is appended to the item-render record, with matching
native initialization and comparison ABI. Old callers are rebuilt by the header
dependency. No new private input needs retention.

Local reports, fixtures, baseline binaries and renders are under
`mu-mac-tools/native/{scratch,renders}/render-items-002j/`. After merge release the
lock immediately, delete both directories and lane build/verification outputs,
then remove the worktree/local branch. Shared input symlinks are never committed
or traversed during deletion. Final latest-main gate and merge remain pending.


## Deadline and queue

The owner requires a stop by 14:45 CDT on 2026-10-28, with the final checkpoint
and handoff by 14:40 if unmerged. This lane joined the fair queue after strict
validation, behind RENDER-WORLDS-L, VERIFY-HARNESS-002 and NATIVE-PERF-004.
Do not start a locked sequence that cannot finish before 14:45. If unmerged,
push all verified changes, remove this lane's queue entry, release any owned lock,
remove unnecessary bulk outputs, retain the worktree and record the exact next step.


## Stable preflight

With source frozen after the hidden-mesh correction, `bash scripts/local-macos-ci.sh`
passes **1,597 tests across 38 suites, 203 explicit skips, zero failures** on the
original part-9 base plus this lane. All **10/10 fixture scenarios and 77
expectations** pass, with 80 inbound frames, zero unbound/undecodable frames and
the existing two unrecovered intents/seven unsent frames explicit. Native
viewer/readers build; audit accepts **1,544 staged files, zero rejected**.
All four final native after-images retain their hashes/counters on this build.
The final serialized latest-main gate remains required. No hosted CI is run.
