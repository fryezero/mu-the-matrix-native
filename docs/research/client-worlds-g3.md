# Deep Dungeon dragon fire, Abyss 2 dark meshes, Scorched Canyon far objects, Vulcanus particles (RENDER-WORLDS-G3)

RENDER-WORLDS-G3, 2026-10-28. Follows [G2](client-worlds-g2.md) §5, [O](client-worlds-o.md) and
[R](client-worlds-r.md). Labels: **verified** = compared with the original instructions under Unicorn or with a live
capture; **static** = read from the pinned text/data; **live** = read from the DATA-ACQ-002 snapshots; **inference**
= not checked by either.

## 1. Deep Dungeon (116–120) dragon fire

**G2's four candidates are ruled out (static).** Each starts with its own world test, and none accepts 0x74..0x78:

| Candidate | World test | Accepts |
|---|---|---|
| singleton `0x00d53c8f` → `0x00d5404b` | `0x00d53d11` / `0x00d53d32` | 0x29, 0x2a |
| manager `0x00db747f` (vtable `0x01aa7a08`) slot +0x34 = `0x00db7656` | `0x0095fba9` | 0x2d..0x32, 0x62, 0x63 |
| `0x00e3116a` | `0x00e309a7` | 0x33, 0x49, 0x4a |
| `0x00e5f94b` | `0x00e5f48a` | 0x38 |

RenderObjectVisual `0x017f9758` switches on the world first (`0x017f97e2`): worlds above 0x37 other than 0x34/0x37
go straight to the tail `0x017fcb5c`, so for 116–120 the whole visual is the hook tail, which produces nothing.
The five Deep Dungeon class vtables (`0x01aaafe0`, `0x01aab0a8`, `0x01aab170`, `0x01aab240`, `0x01aab320`) have
class-specific slots only at +0 (destructor), +0x2c (create), +0x30 (move), +0x48 (monster creation for
classes 0x2ff/0x302/0x303) and +0x54 (monster effects for 0x8df/0x8e0); none touches map objects.

**Producer: the map-object effect table (static + live).** The world loaders (`0x00e21f75`, `0x0182876e`) call
`0x0183067e` after the map objects are created. For the current world it looks the world up in the std::map at
`0x06fbb7b0` (`0x010fa24c` contains, `0x010fa28a` at), walks the 256 sector lists `0x0bdb61f0`, looks every
object's type `+0x5c` up in the world's inner map, and for each entry builds an effect through the C++ effect
manager `0x00a797a0` (entry fields: name `+4`, position `+0x1c`, rotation `+0x28`, scale `+0x34`, bone `+0x38`,
follow-bone `+0x3c`, `+0x3d`, `+0x44`, `+0x48`) and attaches it with `0x0129f9c6(effect, bone, follow, 0, 0.0)`.
It then runs `0x0129f4cb` once. Per frame, RenderObjects `0x016d5020` updates the attached effects with
`0x0129f671(frame time)` when `0x00d99e3f` says the container at `+0x3d0` is not empty ([effect manager](client-effect-manager.md) §6).

Live evidence: the object's `+0x3d0` container is a std::list {head, size}. In the Deep Dungeon captures every
marker of types 62–67 carries exactly one attached effect (size 1), and no other type does:

| Capture | Objects with one attached effect, by type |
|---|---|
| 116 | 62: 18, 63: 23, 64: 14, 65: 14, 66: 20, 67: 4 |
| 118 | 62: 19, 63: 21, 64: 25, 65: 17, 66: 26, 67: 35 |
| 120 | 62: 59, 63: 56, 64: 35, 65: 44, 66: 41, 67: 35 |
| 63 (Vulcanus) | 69: 1, 71: 1, 74: 2 |

The visible dragon fires of the Deep Dungeon 3 shot are at the type-67 markers with x-rotation 80 (for example
(12129, 12055, 259) and (12137, 11755, 259)); the type-52 objects (CreateEffect `0x43a`, the falling stone of
N's move method) are elsewhere. Types 62–66 are the coloured-light markers of the same move method; their attached
effects are the other coloured glows.

**Table source: not in the restored text (static).** The only references to `0x06fbb7b0` are the two reads in
`0x0183067e`; it is not a member reached through another referenced global (the only nearby global,
`0x06fbb754`, is the item enchant-effect manager with its own `EnchantEffectTool` script). The writer is outside
the pinned text (inference: a startup routine outside the capture or a protection-side module, both out of
scope). The effect names per type are therefore not known. A live read of the list node behind `+0x3d0` of a
type-67 object (node → effect instance → template path) would name them.

**Consumer: RENDER-EFFECTS-006.** These are `.ein` effect-manager instances attached to world objects, which is
RENDER-EFFECTS-006's lane (effect manager, `.ein`, owner/key requests). This lane does not add a consumer.

## 2. Abyss of Atlans 2 (129) dark meshes

**They are not map objects (verified by elimination, rendered).** The live object fields of types 3/4/6/24 near
the hero are the defaults (BlendMesh −1, BlendMeshLight 1, alpha 1, render mode 0), and their models are
starfish, coral and seaweed (`Data/Object131/Object04.bmd` `star01.jpg`, `Object07.bmd` `bu02.tga`,
`Object25.bmd` `bu03.tga`). Native renders with types 3/4/6, then type 24, then every object within 1,500 units
removed still draw the five dark bodies. They are the environment's swimmers: MoveFishs `0x00ca05b3` in worlds
0x80..0x82 creates types 0x19b..0x19e (attribute 0x800) or 0x19f/0x1a0 (attribute 0x1000), and gives 0x19f/0x1a0
**BlendMesh `+0x74` = 0 and BlendMeshLight `+0xa8` = 1.0** (MoveFishs then pulses `+0xa8`); the same holds in
Atlans (world 7). The live frame shows them as translucent cyan jellyfish.

**Root cause.** RenderFishs `0x00ca1cf7` draws each swimmer with RenderObject `0x016d4fe4(o, 0, …)`. Its custom
render `0x017f76ec` has no case for these types (static: no compare against 0x196..0x1a0 or 0x1b3 in
`0x017f76ec..0x017f9758`; the Abyss class slots 0x38/0x3c that end its chain answer no for them, verified), so the
draw `0x017edf43` calls the generic `RenderBody(2, alpha +0xdc, BlendMesh +0x74, BlendMeshLight +0xa8, U +0xac,
V +0xb0, HiddenMesh +0x68, −1)`: mesh 0 is drawn as the additive blend mesh. The native environment drawer passed
only the alpha, so mesh 0 was drawn opaque and nearly black.

**Fix.** `reconstructed/environment/env_body.c` `mu_env_render_body`: RenderObject's setup alpha step (Chaos
Castle `0x009dacb8` with the hero's flag 1: −0.15) and test (`0.01 > alpha` skips), the draw's HiddenMesh −2 skip,
and RenderBody's eight arguments. `native/core/mu_env.c` `r_object` uses it for every boid and swimmer. The
environment objects never write `+0x03`, `+0x80`, `+0xac`, `+0xb0`; ObjectInit `0x0129eb81` stores 0 into them
before its first call (`0x0129ee24`) (verified), so the helper uses flags 2 and U = V = 0. The native host has no
Chaos Castle hero flag (as the objects runtime), so it passes 0.

## 3. Scorched Canyon (131) far objects

**Resolved on current main (measured).** RENDER-WORLDS-R measured 7.624 → 8.562 with three far objects passing the
native frustum. After RENDER-TIME-003 (`f4eba8a`, the 640-unit GetScreenWidth frustum) the capture measures
**8.068**, the OBJECT visible byte `+0x0b` equals the live one for all 7,111 matched objects, and camera eye, pitch,
FOV and far plane equal live (far 3257.8). No culling change is needed. The remaining error is a near-camera
structure at the left edge and a uniform colour cast (native − live ≈ −7 in each channel), outside this lane.

## 4. Vulcanus particle requests

**Identified (traced).** At the arrival tile (124, 129), with `draw_all`, all 11 refused requests are CreateParticle
`0x7f89` (clouds) subtype 0xb, scale 1, owned by two type-3 objects: Vulcanus' type-3 visual (and world 82's) emits
one dim red haze (`light = (rand % 3 · 0.01 + 0.015, 0, 0)`) one call in four.

**Consumed (verified).** Create `0x015eb21b`: lifetime 500; position += `(float)(rand % 400 − 200)` per axis; start
= position; scale = `(float)(rand % 15 + 15) / 30 + scale`; velocity = (d, d, 0), d = `(float)(rand % 10 + 5) · 0.12`.
Move `0x0165f1a9`: position += velocity; `+0x7c` = 1.5; rotation = `((float)(rand % 2) + 0.5) + rotation`; dies
when `(float)sqrt(|position − start|²)` exceeds 500. Render: the clouds' default branch `0x01599ac0` (already
reconstructed). The black smoke subtype 0x10 of type 2 is not requested at this tile and stays refused.

## 5. Validation

`scripts/validate_worlds_g3.py` (registered `validate_worlds_g3`), strict Unicorn machine over the pinned text
and data, **4 families × 1,000 = 4,000 cases equal, 0 mismatches, 0 stops; 22/22 compiled mutants detected**
(lowest 9 cases):

| Family | What runs as client code | Compared |
|---|---|---|
| object_init | ObjectInit `0x0129eb81` up to `0x0129ee24` on poisoned objects | `+0x03`, `+0x68`, `+0x74`, `+0x80`, `+0xa8`, `+0xac/+0xb0` against the helper's constants |
| env_render | RenderObject `0x016d4fe4` (setup and draw) on environment-object images (zero bytes, ObjectInit's head, the C object's fields) in worlds 7, 0x80..0x82, the Chaos Castle worlds and others; custom render `0x017f76ec` and the render registry stubbed "not taken" | RenderBody called or not, its eight arguments, the modelled object fields afterwards |
| clouds_ember | CreateParticle, MoveParticles, RenderParticles for `0x7f89/0xb` (validate_particles' families; half the moved records start within 500 units of their start) | the particle record, the draw |
| abyss_fish | Abyss custom slots `0x00d5d2f6/0x00d5ef96/0x00d606da` and after slots for types 0x196..0x1a0, 0x1b3 | answer, calls, object bytes |

Mutants: alpha bound and inclusiveness, HiddenMesh −2, Chaos step size, flag test and omission, flags 0x82, blend
mesh dropped, blend light from alpha, U = 1, HiddenMesh argument dropped, last argument; for the haze: not kept,
lifetime, jitter, start, scale divisor, upward drift, spin rate and step, distance bound, no drift. Static:
`fish_type_compares = []`. `validate_particles` gains the kind `(0x7f89, 0xb)` in its tables.

Portable: `reconstructed/environment/test_env_body.py` (3 tests + the private run).

## 6. Fidelity at the DATA-ACQ-002 arrival tiles

Base = origin/main `9b821b1` built in a temporary detached worktree; lane = this branch merged with it. 32
captures, 25 steps, 1722 × 1048, both in the normal mode and with `draw_all`.

| Capture | Mode | Image mean \|Δ\| / > 24 before → after | Other |
|---|---|---|---|
| Abyss of Atlans 2 129 | normal and draw_all | **4.412 / 0.0130 → 3.975 / 0.0081** | the five dark bodies become translucent cyan jellyfish as live; OBJECT and light dumps identical |
| Vulcanus 63 | draw_all | **1.830 / 0.0088 → 1.798 / 0.0087** | particle requests refused 11 → **0** |
| Vulcanus 63 | normal | 1.841 / 0.0089 (unchanged) | the type-3 visual runs while drawing; the normal mode draws 2 of 25 steps |
| Scorched Canyon 131 | both | 8.068 / 0.0548 (unchanged) | see §3 |
| Deep Dungeon 116–120 | both | unchanged | see §1 |

Normal mode: **31/32 PNG, 32/32 OBJECT, 32/32 light identical**; draw_all: **30/32 PNG, 32/32 OBJECT, 32/32 light**.
Abyss 1 and 3 and the other worlds with environment objects are byte-identical at these tiles (no 0x19f/0x1a0 and
no alpha < 0.01 or HiddenMesh −2 swimmer in view). The October 22 fourteen-view snapshots are not at their manifest
paths (as recorded by RENDER-WORLDS-O/AFTER), so that tour was not rerun.

## 7. Limits

| Item | Status |
|---|---|
| Deep Dungeon dragon fire | Producer found (map-object `.ein` table `0x06fbb7b0`, attach `0x0183067e`); table writer outside the restored text; effect names need one live read of a type-67 object's `+0x3d0` list node; the consumer is RENDER-EFFECTS-006's (its handoff lists `0x0183067e` as remaining) |
| Custom render `0x017f76ec` before the class slot | Static for the fish types (no type compare); the item-map lookup at its head is a runtime map |
| Chaos Castle hero flag | Not set by the native host (0), as in the objects runtime |
| Clouds 0x10 (Vulcanus type 2 black smoke) and world 82 | Not requested at the captured tiles; 0x10 stays refused |
| Scorched Canyon residual | Near-camera structure and a −7 colour cast; not culling |
