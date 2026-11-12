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
