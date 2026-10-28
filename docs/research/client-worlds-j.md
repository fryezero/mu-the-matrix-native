# Captured Raklion and Karutan primary handlers

RENDER-WORLDS-J, 2026-10-28, issue #220. Completes the missing Raklion visual and Karutan create entries,
and expands Karutan's existing move/flame subsets into complete primary methods. Coverage advances from
**31/144 to 33/144 primary methods**, with **11/48 classes unchanged**, zero static-only entries and 111 missing.
All eleven covered classes now have a family for each primary slot; older bounded scopes remain bounded.

## Selection and provenance

The available DATA-ACQ-002 tour has thirteen worlds and fourteen views. Its only incomplete concrete primary
groups were Karutan and Raklion. Karutan's saved population has 2,143 objects, including 6 type-66 lamps,
86 type-72 lamps, 59 braziers, and 15/9/66/6 objects of types 114/115/116/118. Raklion has 1,521 objects,
including four type-80 emitters and no type-70 emitter. Population size determines this selection; no visit
frequency was measured. No class lacking a usable saved capture was implemented in this lane.

Target `main.exe` SHA-256 `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`, also checked
against the installed asset root used by the tour. Capture09 text at `0x00401000`, SHA-256
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`. Run10 data at `0x01a7c000`, SHA-256
`c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`. Both full captures are pin-checked.
Reports also hash the individual instruction ranges. These are restored Linux/Wine x86 instructions,
not native Windows evidence. No live client or launcher was used.

| Family | Original half-open range | Cases |
|---|---|---:|
| Karutan create | `0x00e13a87..0x00e13a9e` | 1,000 |
| Karutan move | `0x00e13a9e..0x00e13be4` | 1,000 |
| Karutan visual | `0x00e13be4..0x00e14596` | 1,000 |
| Raklion visual | `0x00e946a8..0x00e949f8` | 1,000 |
| Raklion create, existing B family | `0x00e943c0..0x00e94617` | 1,000 |
| Raklion move, existing B family | `0x00e94619..0x00e946a6` | 1,000 |

## Verified methods and boundaries

Karutan create returns false without changing the object, including for a null pointer. Move accepts worlds
80/81, emits the warm random range-3 light for 113, hides 113/114/115/116/118/135, plays sound `0x5a5` for 135,
and returns false for default types. The production dispatch still runs the generic movement/tick exactly once.
The move body was relocated from the shared switch without changing its behavior.

Karutan visual accepts 80/81 and handles these complete branches:

- Type 66 transforms local `(10,0,-6)` and `(10,0,6)` through bones 13/14, then requests `0x7f6b` sprites at
  fixed scale 1.2. Its RGB factors are 1.9/1.1/1.1 times the clock pulse.
- Type 72 transforms `(20,0,0)` through bones 11/7. It requests paired `0x7ef7`/`0x7f26` glows with fixed
  scales 2/4 and dim `0x7f26` overlays at scale 1.5. RGB factors are 1.3/1.3/1.9 times the pulse.
- The pulse uses a double multiply by 0.0004, rounds to float before sine, rounds sine to float, takes its
  comparison-based absolute value, then multiplies by 0.4. The comparison preserves negative zero. The first
  compiled comparison rejected `fabsf`, which changed signed-zero output arguments; a dedicated mutant catches it.
- Type 113 reuses the previously verified flare/fire branch. Type 114 randomly requests `0x801c/16` at a
  one-in-three gate. Type 115 requests twenty owned cloud particles only while hidden mesh is not -2.
- Type 116 uses one one-in-eight gate for two `0x7f5a` requests: subtype 69 with fixed green light and object
  scale, then subtype 13 with OBJECT light, double scale and object ownership. Type 118 requests four owned
  cloud particles only while hidden mesh is not -2. Handled branches return true even when their gate is silent.

Raklion visual has a model gate and no world predicate. Types 70/80 use blue/warm light respectively, choose
one of `0x8086/2`, `0x8087/6`, `0x8089/2`, then always request a second `0x8086/2`. Both particles have object
position/angle/scale and no owner. Default types return false without consuming RNG. The original B create/move
families are rerun unchanged; their prior scope, including the move predicate service boundary and void C return,
is retained rather than promoted to a new AL claim.

The four new/expanded method families compare AL, all 984 OBJECT bytes, ordered expanded service arguments,
bone query order/local points and final MSVC RNG. Vector accessors, world predicates, sine and the original
absolute-value helper execute under Unicorn. TransformPosition supplies deterministic synthetic positions
through a recording boundary. Particle/sprite/light/audio services record calls; sprite descriptors and fixed
particle tails are asserted. This proves the method logic and its requests, not the nested engine implementations.
Samples include signed type extremes, off-world/model-null gates where present in the original method,
positive/negative/zero scale, signed zero and finite clocks within +/-1,000,000. Nonfinite/extreme clocks and
captured random/animation phase remain unverified.

Six families pass **6,000 cases, zero mismatches or stops**. **30/30 separately compiled planted mistakes**
are caught across all six methods. They cover world/model/type gates, AL, positional offsets, clock/pulse and
signed zero, bone/local points, sprite size, light strength, hidden fields, sound, RNG divisors, burst counts,
particle kinds/subtypes and scale. Original instructions are never mutated.

## Native consumption and saved scenes

The existing native object part calls the new methods after RenderObject, including hidden emitters. Karutan
retains its preexisting outer flicker RNG draw. The partial flame path is replaced by the full class visual,
so braziers emit once. Bone lamps require the current object's successful pose and enough bones. Failure is
counted and never substitutes object origin or a previous object's matrices. No new per-frame allocation,
shared callback ABI, particle/effect source or other active lane implementation is introduced.

The synthetic production host uses an authored fifteen-bone/two-key model and runs 18 world/type combinations
for 200 preparations each, **3,600 preparations**, with callback arguments/ownership/scales and ordered current
bone positions. It also checks absent/unloaded models with stable RNG, changed object origin, missing-bone
refusal and sibling-world dispatch. Portable tests check public create/move, exactly one generic tick and
zero/one/full-capacity log independence for state, random consumption and bone order.

The saved tour retains **26/26 PNG, 13/13 OBJECT and 13/13 light hashes** in the thirteen unaffected views,
including Raklion. Karutan's first PNG is also identical. Its final PNG, OBJECT and frame-light dumps change
as the added class RNG requests alter subsequent brazier light samples. All changed OBJECT bytes belong to
42 objects' body-light copies at +0x1e8..+0x1f3. Primary terrain light remains identical in all fourteen views.
Every view retains zero missing/extra placements. The thirteen unaffected complete scoreboard entries are
identical; Karutan retains camera/static-field results while its native OBJECT hash and frame-light scores change.
The Karutan final native-to-native RGB mean absolute differences are 0.02126/0.01018/0.00265 per channel.
Both representative final frames were visually inspected. Existing cyan spheres in Karutan are present before
and after this lane, not introduced here.

Original screenshots are absent at the retained manifest paths, so original-to-native image error is unavailable.
These are populated saved-object/light regressions with intended Karutan differences, not a claim of improved
live image fidelity or synchronized full particle pools. Local manifests repair only relocated input paths.

Static downstream audit, separate from primary-method coverage:

| Request | Consumer limitation |
|---|---|
| Raklion `0x8086/2`, `0x8087/6`, `0x8089/2` | Missing particle lifecycles, existing unsupported counter |
| Karutan 66 sprite `0x7f6b` | Missing bitmap in the native particle host's texture registry; callback is wired, pixels unavailable |
| Karutan 114 `0x801c/16` | Missing particle lifecycle |
| Karutan 116 `0x7f5a/69` and `/13` | Missing particle lifecycles |

Karutan clouds `0x7f89/0`, the old three flame kinds and type-72 sprite bitmaps use existing consumers. This is
an availability audit and callback proof, not a new instruction proof of their nested rendering. Particle/effect
and bitmap consumers belong to the active effects lane and were not changed here.

## Skipped capture worlds and continuation

The other 37 concrete classes have no usable population/light/camera capture in the available tour and are
skipped. Their factory-registered worlds are 69, 70, 71, 72, 91, 92/96/101/111, 95, 110, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123/124/125/126/127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 142, 143, 144, 145.

Worlds 62/63, 64/82 and 79/100 retain the G/H/I acquisition requests. In particular **79 and 100 still need
DATA-ACQ-002 captures**. Acquire full OBJECTs, loaded models/actions/bones, camera/PNG, primary/frame light,
clock/RNG/weather as applicable and simultaneous effect/particle/joint/sprite pools. No new capture was taken.
The 111 missing primary methods and separately inventoried custom/after/invisible slots remain open.

Reproduce with `scripts/run_validators.py --private --only validate_worlds_j,validate_worlds_i,validate_worlds_h,validate_worlds_g`,
`world_handler_coverage.py`, the J portable/native tests and `bash scripts/local-macos-ci.sh`, using the repository Python.
[Handoff and final locked gate](../handoffs/RENDER-WORLDS-J.md). Reports/renders remain local under the lane scratch/render
folders until merge, then are deleted with the worktree. No new local INPUT needs retention.
