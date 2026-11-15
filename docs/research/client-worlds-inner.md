# Classless inline world visuals

RENDER-WORLDS-INNER-001. Target executable SHA-256
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`. Restored text and image data are pinned
by `scripts/pins.py`. Method: bounded static disassembly, strict Unicorn execution against authored C, and a
synthetic production-runtime host. No live client, event feed or protected code is used.

## Scope

The Kanturu hook `0x00e75089..0x00e760aa`, worlds 37 and 40, after RenderObjectVisual's outer RNG draw.
The Blood Castle switch `0x017fc023..0x017fc71f`, worlds 11..17 and world 52, through RenderObjectVisual
`0x017f9758` from entry. The earlier wording "object type 0x34" meant world 0x34, corrected by the owner.
The switch's object types are 0x0b, 0x0d and 0x2a.

`world_inner_visual.c` records the calls and field writes. `mu_objects_runtime.c` routes requests through
existing consumers and appends extra meshes after the base body. The original outer draw stays in its existing
place, once per object with a model. The native clock input is the authored offline WorldTime tick.

## Kanturu

Verified call producer, `mu_kanturu_inner`:

| Type | Inner behavior |
|---|---|
| 0x25 | `timeGetTime() % 1024 < 10`: CreateEffect 0x193/3 owned by the object; hidden mesh becomes -2 regardless |
| 0x3b, 0x3d, 0x46 | Existing flame producer, unchanged: rand-gated 0x7f5a/21 and 0x8016/0, and two bone-6 flares |
| 0x3e | World 37: rand % 6 == 0, owned smoke 0x7f89/25. World 40: twenty owned 0x7f89/12 requests if hidden mesh != -2. Light 0.04 |
| 0x51, 0x52, 0x53 | White particles 0x801a/2 at rand % 2 == 0, 0x801c/4 always, 0x801b/2 at rand % 3 == 0 |
| 0x55 | Matrix push/pop wrappers, mesh 3 flags 0x42 then 0x84 with Chrome01 0x7f1f; wrappers do not change the matrix |
| 0x5c | Bone 1 -> bone 2 lightning 0x7f7c/18, scale 50, rand % 30 == 1 |
| 0x60 | StreamMesh 0, GREATER 0, mesh 0 flags 2, alpha 1, negative-clock V scroll over 20,000 ms; restore GREATER 0.25 and StreamMesh -1 |
| 0x62 | rand % 3 == 0, bone 1 particle 0x802a/2, scale 1, light 0.5/0.6/0.1 |
| 0x69 | Bone 4 particle 0x7f2b/0 and flare 0x7f26, grey pulse `(sin(T*0.001)+1)*0.5`; four RNG endpoint offsets then rand % 20 == 0 lightning 0x7f7c/8, scale 40 |
| 0x6b, 0x6c | Twenty owned smoke requests while hidden mesh != -2, 0x7f89/2 light 0.06 or /7 light 0.2 |
| 0x6e | Bone 1 flare 0x7ef7, scale 1.1, `(sin(T*0.002)+1.5)*0.5` times 0.6/1/0.8 |

## Blood Castle

Verified call producer, `mu_blood_castle_inner`:

- 0x0b: seven named bones `light`, `light01`..`light06`, local 0/0/2, each with a 0x7ef7 flare of scale 0.5.
  Light `(l,l*0.5,0)`, where `l = sin((angle.z*20+T)*0.001)*0.5+0.5`.
- 0x0d: `light01`, local zero, flare 0x7f78, scale `l+0.5`, grey `l = sin(T*0.001)*0.3+0.7`.
- 0x2a: two independent rand % 2 rolls. The first increments object +0xb4 and tests the prior value +2, truncated
  with cvttss2si, modulo 4. On zero: 0x8001/0 and 0x8000/0. The second tests and increments the resulting counter;
  on zero: 0x7f89/6, 0x8000/1 and 0x7f78/4 with scale 0.19 and light 1/0.8/0.8. The other scales are 1, light white.
- No event-state input is read or modelled by these bounded branches.

## Verification and limits

The strict harness compares ordered request/draw arguments, named and indexed bone-transform inputs, model
StreamMesh at each draw, the complete object/model bytes, RNG state, world tests and independent clock-call
count. String/vector helpers execute as original instructions, while the heap and engine leaves are stubbed.
Focused cases exercise rare clock/joint gates and counter boundaries. Portable tests exercise wrong-world
refusal, clock edges, log overflow and the production runtime.

- Missing named or indexed bones refuse requests with an explicit object-runtime count.
- Joint 0x7f7c/8 has no existing native kind, so the runtime refuses and counts it. /18 uses the existing consumer.
- Particle/effect kinds absent from the existing pools remain counted refusals in those consumers. This lane
  does not change item, particle or effect consumer code.
- The shared renderers fix alpha reference at 0.25. Type 0x60's additional mesh checks mesh 0's mapped texture slot and is served for RGB textures,
  for which GREATER 0 and 0.25 agree, and refused for RGBA textures. The base body remains drawable.
- The clock fixture is deterministic; it is not a captured process `timeGetTime` value.
- No original frame or event state is newly captured. Captured affected worlds are 37 and 40; Blood Castle
  has no captured image reference in the two existing tours.

Final checks and render results are recorded in [the lane handoff](../handoffs/RENDER-WORLDS-INNER-001.md).

## Negative checks

The first small comparison rejected the guessed 0.005 pulse frequency and angle multiplier 5. The original
uses 0.001 and, for Blood Castle's phase, 20. Focused cases then rejected type 0x62's guessed blue 0.3, which is
0.1. All four final families pass 1,000 cases each, with zero mismatches/stops, and 33/33 compiled mutants are
detected, minimum eight cases.

Production-host negative cases reproduced two adapter mistakes before correction: StreamMesh events alone
could bypass a hidden-object skip after an RGBA refusal, and the refusal initially assumed texture slot 0.
The host now requires hidden RGBA refusal while preserving hidden RGB/Chrome draws, and distinguishes a mapped
RGBA slot from a mapped RGB slot when slot 0 has the opposite component count.

## RENDER-WORLDS-INNER-002: Elbeland and Swamp of Calmness

Same executable/text/data pins and offline method as INNER-001. The owned producer is
`world_inner2_visual.c`; `mu_objects_runtime.c` runs it after the single existing outer RNG draw and routes its
requests through the existing sprite, particle and joint consumers. No event-state input is read by these two
world branches. Fixed synthetic stack colour is a comparison input only.

Elbeland was chosen first for its captured population: 5,175 objects, including 164 type 0x3c smoke bursts,
26 type 0x79 six-bone glows and six type 0x3f glows. Swamp has 4,236 captured objects, including 87/119 owned
smoke emitters of types 0x4d/0x4e and 59 raised-smoke emitters of type 0x48. These are object-list populations,
not counts visible from the capture camera.

### Elbeland 51

`0x00e3116a..0x00e31984`, reached from RenderObjectVisual at `0x017fcc89`.
The guard `0x00e309a7` also accepts 73/74, which `0x00e309d9` forwards to another handler. This lane owns
only world 51 and does not claim those forwarded worlds.

| Type | Complete inline producer in world 51 |
|---|---|
| 0 | rand % 3 == 0: particle 0x8016/0 at position, white, object scale |
| 0x36 | rand % 4 == 0: 0x801b/4 at position, white, object scale |
| 0x3a | 0x801e/0 at position, scale 1; light reads unwritten stack local `[ebp-0x10..-8]` |
| 0x3b | 0x801c/8 always, white, object scale |
| 0x3c | If hidden mesh != -2: ten owned 0x7f89/3 requests, light 0.06/0.07/0.08, object scale; then hidden mesh -2 |
| 0x3d | rand % 3 == 0: 0x8017/0, white, object scale |
| 0x3f | Bone 5, local -40/-10/0: 0x7ef7 sprite, scale object scale times 6, light p/p/p*0.6; p = (sin(T*0.001)+1)*0.3+0.4 |
| 0x6e | rand % 2 == 0: two more rolls, local x = cos(T*0.03)*(rand%5+30), y = sin(T*0.03)*(rand%5+30), z = 70; bone 0 -> owned 0x7ef7/11 particle, white, scale 0.6 |
| 0x79 | Bones 3..8, local 5/-4/-1: six 0x7ef7 sprites, scale p, light p/p*0.5/p*0.3; p = (sin(T*0.002)+1)*0.5+0.5 |

The existing Elbeland move handler hides type 0x3c before a normal visual pass. Its ten-request branch is
verified with authored pre-hidden state in the producer and production host; it is not claimed to fire in the
captured steady-state view.

Type 0x3a has no defined stack colour in this function. The whole guard and branch are compared with an authored
prior stack colour installed at the branch boundary `0x00e31358`, without replacing any instructions. This is
synthetic input evidence, not a recovered colour or an original frame claim. The native producer accepts that
input for comparison; production supplies no such value and emits a counted refusal instead of inventing white.

### Swamp of Calmness 56

`0x00e5f94b..0x00e6021c`, reached at `0x017fcc9f`; world test `0x00e5f48a` accepts only 56.

| Type | Complete inline producer in world 56 |
|---|---|
| 0x39 | rand % 3 == 0: 0x8016/5 then 0x7f5a/21, white, object scale |
| 0x47 | rand % 3 == 0: 0x8016/5, white, object scale |
| 0x48 | rand % 6 == 0: position.z + 50, 0x7f5a/49, light 0.03, object scale |
| 0x4a | rand % 3 == 0: 0x7f5a/21, white, twice object scale |
| 0x4d / 0x4e | rand % 6 == 0: owned 0x7f89/20, light 0.04/0.06/0.03 or 0.03/0.03/0.05, object scale |
| 0x63..0x67 | rand % 50 == 0: write object light 1/0.65/0; owned 0x7f7d joint, subtypes 26/16/17/24/25, identical position endpoints, object angle and scale |

All five joint subtypes already exist natively. Missing joint hooks and missing bone transforms remain counted
refusals. No particle consumer is added by this lane; absent particle kinds retain their existing pool refusals.

### Remaining inline work

This table is the end-of-INNER-002 snapshot. INNER-003 below closes 9/31/33/38.

Addresses below are static entry points for the next lane, not a claim that every branch needs new code.
The previous broad list included worlds that only reach the common chain. Recheck the call paths and guards
before implementing anything there.

| World | Entry or dispatch to inspect |
|---|---|
| 9 | RenderObjectVisual inline case `0x017fb7e7`, type 2 |
| 24 | Kalima `0x00def747`, guarded by `0x009b0418`, also accepts 25..29/36 |
| 30 | `0x00d8e640`; event byte getter `0x00d8b3e3` reads `0x01ec8ee7`, use an authored input only |
| 31 | `0x00dfc095`, types 3/0x31/0x35 |
| 33 | `0x00d622dd`, world guard also accepts 54 |
| 38 | `0x00e7df87`, guard `0x00e843df` |
| 39 | `0x00e84941`, guard `0x00e84513`; tower state is a separate fixture input |
| 41/42 | thiscall `0x00d5404b`, getter `0x00d53c8f`, world tests `0x00d53d11`/`0x00d53d32` |
| 46/98 | common chain `0x017fcb5c..0x017fccbc`, then manager `0x00ea2dc1`; no dedicated leaf identified here |

Kanturu type 0x60's extra RGBA pass still needs the coordinated GREATER 0 alpha-reference seam described in
INNER-001. This lane does not change shared mesh or raster state. The rest of the worlds above remain unported
by this lane. No event model, new capture, live client or installed-app change.

### INNER-002 final verification

Five families pass 5,000 original call comparisons, zero mismatches/stops. All 27 compiled mutants are caught,
minimum 46 detections. All 64 affected validators and the portable/private checks pass. The 44 unaffected
views are byte-identical. Elbeland's close-up glows and Swamp's six joints / 196 quads were visually inspected
in demo-labelled native frames. Elbeland has no original PNG; Swamp's captured image score is unchanged.
[Full counts, refusals, per-row walls and next addresses](../handoffs/RENDER-WORLDS-INNER-002.md).

## RENDER-WORLDS-INNER-003: Aida, Kanturu Remain, Trials and Devil Square

Same executable/text/data pins and offline method as INNER-001. New authored producer
`world_inner3_visual.c`, existing object-runtime adapter. Aida was first by captured population, 4,135 objects
including 160 type-30 twelve-glow objects, followed by Kanturu Remain, 2,121 objects. Trials and Devil Square
have no captured placement/image reference in the two existing tours and require authored proof layouts.
No event state is read. Clock-dependent requests use a fixed offline tick independently in the comparator,
and the authored WorldTime tick in production. These are not original/native temporal equivalence claims.

### Aida 33 and shared guard 54

Complete producer `0x00d622dd..0x00d63d6b`, reached at `0x017fcbc6`; guard `0x00d61f81` accepts 33/54.

| Type | Inline behavior |
|---|---|
| 0x1e / 0x47 | Six named transforms, Box07/08/09/13/14/18, two 0x7f26 sprites each. Type 0x1e uses blue/grey, large scales 5.5/4.5/4/4.5/4/4; 0x47 uses red, large scales 6/5.5/5/5.5/5/5. The small sprite scale is 3 |
| 0x38 / 0x39 / 0x3a | White particles 0x801a/2 at rand % 2 == 0; 0x801c/4 always; 0x801b/2 at rand % 3 == 0. Object scale |
| 0x3b / 0x3e / 0x3f | While hidden mesh != -2, twenty owned 0x7f89/26 requests. Colours 0.01/0.03/0.05, 0.05/0.05/0.05, 0.05/0.02/0.02. The visual leaf does not hide them |
| 0x3c | Clock % 1024 < 10: owned 0x193/3 request, white. Set hidden mesh -2 regardless |
| 0x41 / 0x42 | Matrix wrappers with argument 1, StreamMesh 0, mesh 0 flags 2 with object's alpha/blend fields, U = (-truncated time % 100000) * 0.00005; restore StreamMesh -1 |
| 0x43 | Object light becomes 0.3/0.3/0.3; 0x7f42/7 particle at object scale |
| 0x46 | Always obtain clock, then rand % 5 == 1 and clock % 1024 < 30: owned 0x199/0, light 0.1, word4 = low 16 bits of truncated object scale |
| 0x4b | Named Bone01, local zero, white 0x7f78 sprite, scale 3, rotation time / 10. The calculated sine pulse is overwritten before the draw |
| 0x4d / 0x4e | As 0x41/42, U = (truncated time % 100000) * 0.0002 |

The six local offsets are 0/-3/1, 0/-3/0, 0/-3/0, -3/-1/0, -3/-3/0, 0/2/-8.
The first large red glow has light 0.5/0/0, the other five 0.25/0/0; small red glows 0.15/0/0.
Blue large glows 0.1/0.1/0.3, small grey glows 0.15/0.15/0.15. All sprites here have the OBJECT owner.
The word4 request uses the existing keyed-effect channel, including word4 zero, and counts a missing hook.

### Kanturu Remain 38

Complete producer `0x00e7df87..0x00e7ed6e`, reached at `0x017fcc11`; guard `0x00e843df` accepts 38.

| Type | Inline behavior |
|---|---|
| 4 | Bone 1, local -1/0/0. Pulse p = (sin(time * 0.002) + 2) * 0.5. Light p*0.3/p*0.5/p; scale is binary64 p / 3.2 rounded to binary32. One 0x7ef7 and two identical 0x802b sprites |
| 8 | Bone 4, zero local. Grey p = (sin(time * 0.001) + 1) * 0.5; 0x7f2b/0 particle scale 1.5 and 0x7f26 sprite scale 10. Four RNG endpoint offsets, then rand % 20 == 0: 0x7f7c/18, scale 40, no owner |
| 0xa | rand % 6 == 0: position Z replaced with 410, white 0x801c/7 at object scale |
| 0x2d / 0x2e / 0x2f | While hidden mesh != -2, twenty owned 0x7f89 particles, subtypes 1/2/7; grey 0.06/0.06/0.2, object scale |
| 0x30 | rand % 3 == 0: owned 0x7f89/10, grey 0.2, object scale |
| 0x31 | While hidden mesh != -2, five owned 0x7f89/1, light 0/0.01/0.03, object scale |
| 0x32 | rand % 3 == 0, then a second roll: owned 0x7f89/11, light 0/0.01/(rand % 3 * 0.01 + 0.02), object scale |
| 0x34 / 0x35 | 0x801c/7 white at object scale, rand % 6 == 0; 0x802a/1 light 0.4/0.6/0.7 at scale 1, rand % 3 == 0 |
| 0x36 / 0x38 / 0x41 | rand % 20 == 0 for 0x36, % 10 == 0 otherwise, then scale rand % 10 + 30. Unowned 0x7f7d joints, subtypes 8/9/10, identical position endpoints |
| 0x37 | rand % 5 == 0: owned 0x4ac/1, light 0.8/0.8/1 |

Joint 0x7f7c/18 already has a native consumer. The three 0x7f7d subtypes 8/9/10 do not and remain counted
refusals. Missing posed bones refuse each dependent request. Missing particle/effect kinds retain existing
consumer refusals. No consumer code changes.

### Land of Trials 31

Complete producer `0x00dfc095..0x00dfc3ce`, reached at `0x017fcbad`; guard `0x00dfbbbb` accepts 31.

- Type 3 / 0x35: rand % 3 == 0, white 0x801c/3 or 0x7f5a/22 at object scale.
- Type 0x31: bone 3 with local 0/-10/0. Pulse sin(time * 0.002) * 0.35 + 0.65. Two red 0x7ef7 sprites,
  scales pulse * 1.2 + 0.3 and 0.5, OBJECT-owned. One grey-0.3 0x7f67 sprite of scale 1.2,
  rotation rand % 360, without an OBJECT owner.

### Devil Square 9

Inline type-2 branch `0x017fb7e7..0x017fba59` inside RenderObjectVisual `0x017f9758`.
Two independent rand % 4 == 0 gates transform Bip01 R UpperArm and Bip01 L UpperArm. The third right-arm
transform/request always occurs. Local -15/0/0, white 0x771d/0 particles, scale 1, no owner.
The comparator enters RenderObjectVisual itself and includes absent-model and the single outer-RNG gate.
The native adapter owns the inner requests, preserving the existing outer draw.

### Integration limits

No original frame or authoritative event context is newly captured. Missing named/indexed bones, missing
keyed-effect hook and missing joint kinds retain explicit counts. Other task worlds 24/30/39/41/42 remain
unported here. A static reread of `0x017fcb5c..0x017fccbc` confirms worlds 46/98 have no dedicated branch in
that chain; `0x00ea2dc1` does a registry lookup followed by the registered handler's slot 0x34. Their complete
registry/context coverage remains unverified. The Kanturu GREATER 0 alpha-reference seam stays deferred.

[Checks, fidelity results and remaining addresses](../handoffs/RENDER-WORLDS-INNER-003.md).

### INNER-003 verification

Eight families pass 8,000 original call comparisons, zero mismatches/stops. All 54 compiled mutants are caught,
minimum six detections, zero stopped mutants. The 68 affected validators pass, and portable checks pass 1,661
tests with zero failures/errors. The default sweep preserves all 44 unaffected views; only Remain's images
change. All 92 OBJECT/light dumps stay identical. Aida's close-up glows, Remain's core, Trials' lamp and Devil Square's arm particles are visible in
demo-labelled outputs. Remain also creates four joints and draws sixteen quads in the last frame. Original Remain image
scores increase slightly; its earlier object/placement/state residuals remain explicit in the handoff.

## RENDER-WORLDS-INNER-004: remaining inline leaves and alpha reference

Same executable/text/data pins and offline method as INNER-001. Authored producer
`world_inner4_visual.c`, existing object-runtime adapter. No remaining target world has a placement/reference
capture in the October 22 or DATA-ACQ-002 tours. Proof layouts are authored, with demo names only.
The first implemented leaf was shared Barracks/Refuge, with twelve active visual types and up to four requests
per smoke object, followed by the small Crywolf leaf, Kalima's bounded branches and the tower's bounded branches.
These are branch counts used to order work, not a measured world-population ranking.

### Crywolf 30

Complete visual producer `0x00d8e640..0x00d8ea2c`. Guard `0x0095fb7c`, event-byte getter `0x00d8b3e3`
reads `0x01ec8ee7`. The original getter executes in comparisons, with authored bytes 0/1/2/255.
Production fixes the input at authored byte 0. This does not establish the authoritative event state.

| Type | Inline behavior |
|---|---|
| 0 | Event byte zero, then rand % 3 == 0: white 0x8016/0, object scale |
| 0x29 | Blend light becomes sin(time * 0.002) * 0.3 + 0.7 |
| 0x2a | Event byte nonzero, then rand % 3 == 0: white 0x7f5a/21, object scale |
| 0x34 | Event byte zero: white 0x801e/6, object scale |
| 0x35 | Event byte nonzero, then rand % 3 == 0: white 0x8016/0, object scale |
| 0x36 | Event byte zero: white 0x801c or 0x801d, selected by another rand % 2, subtype 0, scale 1 |

All particles here have no owner. Model absence returns before the world test and random calls.

### Barracks 41 and Refuge 42

Complete visual producer `0x00d5404b..0x00d54e48`, thiscall instance from `0x00d53c8f`.
Tests `0x00d53d11`/`0x00d53d32` read the world, not event-instance fields. The comparator runs both tests
and the real static constructor for its authored instance. No getter initialization state is inferred.

| Type | Inline behavior |
|---|---|
| 2 / 3 | rand % 3 == 0: white 0x7f5a/13 or 0x8016/0, object scale |
| 5 | Two rand % 2 gates. First tests trunc(prior + 2) % 4 then increments OBJECT +0xb4, emits 0x8001/0 and 0x8000/0 on zero. Second tests trunc(current) % 4 then increments it, emits 0x7f89/6 and 0x8000/1 on zero. White, scale 1 |
| 6 | Unless hidden -2: four owned 0x7f89 requests, subtypes 1..4, grey 0.2, object scale. Set hidden -2 regardless |
| 0x3a / 0x3b | rand % 2 / % 3 == 0: white 0x801a/2 or 0x801b/1, object scale |
| 0x3c | White 0x801c/3, object scale |
| 0x55 | Two counter gates as type 5. First has an additional rand % 2 for black 0x8001/1, then red 0x8000/2. Second emits red 0x7f89/14 and 0x8000/2 at twice object scale. Other scales equal object scale |
| 0x58 | rand % 4 == 0: owned white 0x7f89/10, object scale |
| 0x59 | rand % 4 == 0: owned 0x7f89/11, red = rand % 3 * 0.01 + 0.015, other channels zero, object scale |
| 0x5a | rand % 3 == 0: angle = object angle + (rand % 40 + 120, 0, rand % 30). Owned 0x7fd5/4 joint at identical object-position endpoints, then unowned red 0x7f25/9 particle at that angle, object scale |
| 0x5c | (sin(time * 0.0005) + 1) * 0.5 > 0.9: two unowned 0x806d/0 effect requests, word4 = low 16 bits of truncated object scale |

Red is 1/0.4/0.4. Particles without an explicit owner above are unowned. The counter is +0xb4, not the
animation frame at +0xd0. Nonfinite/out-of-range truncation follows cvttss2si. The keyed-effect adapter already
carries word4, including zero; an absent hook is counted.

### Kalima 24..29 and 36, bounded subset

Parent `0x00def747..0x00deff29`, real world guard `0x009b0418`. Seven visual types are reconstructed.
Three helper-dependent types remain refused without changing their object or consuming inner RNG.

| Type | Inline behavior or refusal |
|---|---|
| 0x0c | Named Bone02, local zero: owned 0x7ef7 sprite, light 0.6/0.6/1, scale sin(time * 0.001) * 0.3 + 0.7 + 0.2 |
| 0x0f / 0x1d / 0x20 | Counted context refusal. Original `0x00dfa988` reads hero action/position and changes motion; `0x00deeb4e` samples a separate water manager. Type 0x20 also requests Bone02. No synthetic no-op or guessed water height is substituted |
| 0x23 | Owned 0x7ef7/6, light 0.3/0.6/1, scale 1; hidden -2 |
| 0x24 / 0x25 | White 0x8017/0 or 0x801e/0, scale 1; object scale becomes 0.5 afterward. Only 0x24 sets hidden -2 |
| 0x26 | rand % 2 == 0: white 0x801a/0, scale 1. Object scale becomes 0.5 regardless |
| 0x27 | White 0x801c or 0x801d, selected by rand % 2, subtype 0, scale 1. Object scale becomes 0.5 |
| 0x28 | rand % 4 == 0: white 0x801b/0, scale 1. Object scale becomes 0.5 regardless |

Particle requests not marked owned are unowned. The comparison excludes 0x0f/0x1d/0x20 explicitly rather than
claiming equality for their refusal. Sound calls `0x00a6ac96(0x1d6,0,0)` in types 0x25/0x26 are recorded at a
visual-only boundary; this lane does not reconstruct sound side effects. AUDIO-004 owns sound integration.

### Tower 39, bounded subset

Parent `0x00e84941..0x00e855f1`, real world guard `0x00e84513`. The byte at `0x01ec91ac` is authored as
0/1/2/255 in the comparator and fixed at 0 in production. Type 0 is a counted refusal. Its singleton +0x78
state and nested sequence `0x00e8d888` remain unreconstructed here. That helper also reaches hero
positions, sequence globals and many effect requests. No event model or guessed sequence is added.

| Type | Verified inline behavior |
|---|---|
| 1 / 0x0b / 0x2e / 0x31 / 0x32 | Unless hidden -2: owned 0x7f89 smoke, respectively 10/10/20/10/10 requests and subtypes 1/3/7/1/4. Colours 0/0.03/0.04, grey 0.1, grey 0.25, 0/0.06/0.1, grey 0.1. Object scale. Set hidden -2 regardless |
| 5 | Bone 1, local -1/0/0, p = (sin(time * 0.002) + 2) * 0.5. Owned 0x7ef7 and two 0x7f67 sprites, scale binary64 p / 2.4 rounded to binary32, light p*0.3/p*0.5/p. Second/third rotations trunc(time / 2) % 360 and trunc(time / 4) % 360 |
| 0x20 | rand % 3 == 0: unowned 0x802a/1, light 0.4/0.6/0.7, scale 1 |
| 0x2f / 0x4a | rand % 5 == 0: unowned 0x7f7d/11 joint, identical position endpoints, object angle, scale object scale * 15. For 0x4a, a nonzero authored hidden byte sets hidden -2 and bypasses RNG/request |
| 0x30 | rand % 3 == 0: owned 0x7f89/10, current object light and object scale |
| 0x34 / 0x35 | rand % 3 == 0: object light becomes 0.5/1/0.7 or grey 0.3, then unowned 0x8017/1 or 0x7f5a/46 at object scale |
| 0x36 | rand % 3 == 0: hidden becomes -1, then unowned 0x7f7c/19 joint with identical position endpoints, object angle, scale object scale * 10 |

### Worlds 46/98 registry boundary

Static factory `0x00ea488e..0x00ea5629` yields 48 concrete classes and 57 world registrations. Neither 46 nor 98
appears. This is rechecked from pinned instructions by a private test, not inferred from native support tables.
Manager `0x00ea2dc1..0x00ea2f07` checks the current world's registry entry and its enabled flag, then invokes
slot 0x34 at `0x00ea2eba`. The common inline chain has no dedicated 46/98 leaf. Dynamic registration/context
coverage is unverified. Each loaded object in these worlds gets one visual refusal; model absence does not.

### Alpha-reference seam

Kanturu type 0x60's original ordered GREATER 0, mesh, GREATER 0.25 calls were already instruction-compared
in INNER-001. The adapter now retains those state events alongside meshes. `slot_meshes` attaches the
reference to the extra mesh only; the base body uses its existing state. The scene driver calls the production
backend's reference callback around the draw and restores 0.25 even on a refused/faulted mesh.
Software updates its existing reference field. GL flushes pending batches before `glAlphaFunc`, including
captured/streamed batches. Defaults issue no new reference call. This adds no particle/joint consumer.

The synthetic host renders five alpha values 0/32/63/64/255 with default, zero-reference, restored-default
passes, across software, immediate GL and batched GL. Zero alpha stays rejected; low nonzero alpha draws only
with reference zero; the two GL images agree exactly and all three backends restore 0.25.

Full counts, compiled-mutant detections, render changes and reference scores belong in
[the lane handoff](../handoffs/RENDER-WORLDS-INNER-004.md). No whole-world or original/native temporal equivalence
is claimed for these authored contexts.

The new requested joint pairs 0x7fd5/4, 0x7f7d/11 and 0x7f7c/19 also have no native consumer on this base.
They remain counted refusals, alongside the existing INNER-003 missing pairs.

INNER-004 original comparisons pass 8,000 cases across eight families, zero mismatches/stops. All 42 compiled
producer mutants are detected, minimum two cases, and four compiled alpha-seam mutants are detected.

INNER-004 renders preserve all 45 unaffected tour views byte-for-byte. Kanturu 37 changes only through the
admitted extra RGBA pass; Remain 38 remains 6.190 at default clock and 6.192 at captured clock. The low
Kalima grids are water-occluded with no changed pixels; a separate seven-type proof at authored Z=500
visibly shows the glow/plume/spray and changes 46,966 pixels per alias. Crywolf, tower, Barracks and Refuge
have visible authored proof deltas. These layouts do not establish original placement or event fidelity.
