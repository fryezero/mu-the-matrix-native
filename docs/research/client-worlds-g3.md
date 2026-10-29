# Deep Dungeon dragon fire, Abyss 2 dark meshes, Scorched Canyon far objects, Vulcanus particles (RENDER-WORLDS-G3)

RENDER-WORLDS-G3, 2026-10-28 (work in progress). Follows [G2](client-worlds-g2.md) §5, [O](client-worlds-o.md) and
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
