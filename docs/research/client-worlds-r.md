# Scorched Canyon, Red Smoke Icarus, Temple of Arnil and Gray Aida primary handlers

RENDER-WORLDS-R, 2026-10-28. The three primary methods (create +2c, move +30, visual +34) of the world-131,
world-132, world-133 and world-134 classes are implemented in `reconstructed/objects/scorched_canyon.c`,
`red_smoke_icarus.c`, `temple_arnil.c` and `gray_aida.c` (declarations in `worlds_r.h`). All twelve have an
instruction-compared family: +12 primary methods and +4 classes; the
[inventory](world-handler-coverage.md) goes from 70/144 methods across 24/48 classes to 82/144 across 28/48 on
main `3d17cac`; with RENDER-WORLDS-P2 merged it reads **88/144 across 30/48**, 56 missing. Custom-render, after-render and invisible-sector slots of these classes stay missing.

## Selection and provenance

All four classes have a DATA-ACQ-002 arrival capture ([captures 2](client-world-captures-2.md)): Scorched Canyon
236,14 (7,111 objects), Red Smoke Icarus 130,116 (2,093), Temple of Arnil 125,57 (9,402) and Gray Aida 124,30
(3,889). Labels: **verified** = compared with the original instructions under Unicorn; **static** = read from
disassembly; **inference** = neither.

Target `main.exe` SHA-256 `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`. Capture09 text at
`0x00401000`, SHA-256 `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`; run10 data at
`0x01a7c000`, SHA-256 `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`. The validator pin-checks
both and reports each range's digest. Restored Linux/Wine x86 instructions, not native Windows evidence.

| Family | Original half-open range | SHA-256 prefix | Cases |
|---|---|---|---:|
| Scorched Canyon create | `0x00e432d9..0x00e4370c` | `b00c2943b4137209` | 1,000 |
| Scorched Canyon move | `0x00e4370c..0x00e43842` | `9c73f463e23b12d5` | 1,000 |
| Scorched Canyon visual | `0x00e43f8e..0x00e43fab` | `acdf57f13a0ce121` | 1,000 |
| Red Smoke Icarus create (jump table `0x00e00c22` included) | `0x00e00b4a..0x00e00cfe` | `3e0c14081325ed8e` | 1,000 |
| Red Smoke Icarus move | `0x00e00cfe..0x00e00d4c` | `6ad3cb655b085fde` | 1,000 |
| Red Smoke Icarus visual | `0x00e00e97..0x00e010b6` | `e6f3a93f37accd6c` | 1,000 |
| Temple of Arnil create (jump table `0x00d80c7c` included) | `0x00d809fc..0x00d80c9c` | `2c7e7941e8adb872` | 1,000 |
| Temple of Arnil move | `0x00d80c9c..0x00d80cea` | `7f891e32f678c465` | 1,000 |
| Temple of Arnil visual | `0x00d81c2c..0x00d81c49` | `acdf57f13a0ce121` | 1,000 |
| Gray Aida create | `0x00d84821..0x00d849e4` | `460b9178e3e3262d` | 1,000 |
| Gray Aida move | `0x00d849e4..0x00d84d0e` | `5c02f3fb254162ee` | 1,000 |
| Gray Aida visual | `0x00d84dd8..0x00d868f7` | `d59889343774627a` | 1,000 |

The 131 and 133 visual bodies are byte-identical (same digest): `object && model`, no world test, no request.
The 132 and 133 moves are the same shape with different world predicates. They are kept as separate small
functions, because each class must reject the other worlds.

## Verified behaviour

**World predicates** (static, executed in every family): `0x00e45d40` accepts 0x83, `0x00e0558b` 0x84,
`0x00d83ada` 0x85, `0x00d8b139` 0x86. Create and move return false for another world or a null object. Visual has
no world test: it returns false for a null object or a null model argument.

**Scorched Canyon (131).** Create: range -400 for 39 listed scenery types (0x0c … 0xad), then -300 for
0/2/3/5/8/0xa/0x46/0x4b/0x4e; types 0xa0..0xa7 hidden (-2); 0x4f, 0x28, 0x5a, 0xa8, 0xb2, 0xb3, 0xb5, 0xba, 0xc5,
0xc7 after-character; 0x6a after-character plus `+0x60 = (rand % 18 + 1) * 10`; 0x88, 0x8a..0x8c, 0x8e, 0x8f,
0x93..0x95 the same `+0x60` draw; 0xaa velocity / 3. Move returns false without the type's model (`0x00eaa8cf`);
type 0xa0 adds the Bloody Tarkan flicker light `(0.8s, 0.3s, 0.04s)`, `s = (rand % 4 + 3) * 0.1`, range 3.

**Red Smoke Icarus (132).** Create through jump table `0x00e00c22`: type 0x1e (the sky plate) gets position z
-1600, `+0xcc` -3000, scale 3.25, angle z 340 and range -30000; types 6..0x3c except 0xb, 0x17..0x1c and
0x2c..0x2e set after-character. Move only tests world, object and model. Visual: types 0..4, while not hidden,
emit one burst of `0x7f89` particles (sub-type = the type, light (0.05, 0.02, 0.01), object scale, owned by the
object): 20 for types 0..2, 10 for 3..4. They then hide the emitter (-2). Type 0xa: TransformPosition of bone 3 (local zero) and a
`0x7ef7` particle there (light 1, sub-type 0, scale 1, no owner) on every visual call. Returns true.

**Temple of Arnil (133).** Create: type 6 sets after-character and clears light-full `+6`, light-enable `+5` and
the visible byte `+0xb`; 0x0e/0x7b/0x80/0x84/0x86/0x8f after-character; 0xa0..0xa9 hidden (0xa2..0xa9 through
jump table `0x00d80c7c`); range -500 for 34 listed types. Move only tests world, object and model.

**Gray Aida (134).** Create: range -50 (0x24/0x3b/0x3e), -80 (0x1f/0x2a/0x85), -150 for 17 types and type 0
(which also sets after-character); 0x19/0x29/0x4f/0x50..0x53 after-character. Move has no model test and always
returns true: 0x19/0x1c scroll blend V by -0.015; 0x29 alpha 0.5; 0x38/0x39/0x3a/0x43/0x46 hidden; 0x3f light
`(s + 0.4, s + 0.6, s + 0.4)`, `s = rand % 5 * 0.01`, range 2, then hidden; 0x40 velocity 0.05; 0x48 angle y +10;
0x49 blend mesh 0, angle y +5, alpha 0.6; 0x4a alpha 1, blend mesh 0, angle y +10.
Visual (returns true):
- 0x1e and 0x47: six TransformPositions (bones 6, 7, 8, 12, 13, 17 with local points (0,-3,1), (0,-3,0),
  (0,-3,0), (-3,-1,0), (-3,-3,0), (0,2,-8)). Each draws two `0x7f26` sprites: a large one (0x1e: scales
  5.5/4.5/4/4.5/4/4, light (0.1, 0.1, 0.3); 0x47: 6/5.5/5/5.5/5/5, light (0.5, 0, 0) for the first bone and
  (0.25, 0, 0) after) and one at scale 3 (light 0.15 grey, or (0.15, 0, 0) for 0x47).
- 0x38: one in two a `0x801f/2` particle; 0x39: a `0x801c/8` particle every call; 0x3a: one in three `0x801b/2`.
- 0x3b, 0x3e, 0x5c: one burst of ten `0x7f89/0x1a` particles owned by the object, then hidden. The light is
  (0.01, 0.03, 0.05), or 0.06 grey for 0x3e/0x5c.
- 0x3c: CreateEffect `0x193/3` (light 1, owned) while `(int)WorldTime % 1024` is in [0, 10); hidden always.
- 0x43: object light 0.3 and a `0x7f42/6` particle.
- 0x46: with `rand % 5 == 1` and `(int)WorldTime % 1024` in [0, 30), CreateEffect `0x199/0` with light 0.1 whose
  eighth argument is `(u16)(int)scale` (the other worlds pass 0 there).
- 0x49/0x4a: object light `sin(T·k)·0.2 + 0.2` with k = 0.0011, 0.0017, 0.0013 (sine `0x009681bd`), and a
  `0x7f26/2` particle at scale 1.3, light 0.5.
- 0x41/0x42/0x84/0x85 and 0x4d/0x4e: the model's StreamMesh byte `+0x94` goes to 0, then
  RenderMesh `0x00966e4a(0, 2, alpha, blend mesh, blend light, u, blend V, -1)`, then `+0x94 = 0xff`. Here
  `u = ((-(int)T) % 100000) · 5e-5` for the first group and `((int)T % 100000) · 0.0002` for the second.

## Comparison and mutants

Twelve families, **12,000 cases, 12,000 equal, zero mismatches or stopped cases**. Each compares AL, all 984
OBJECT bytes, ordered output calls and the final MSVC RNG. The calls are particle, sprite, light, CreateEffect
(type, vectors, sub-type, owner, eighth and eleventh argument), RenderMesh with the StreamMesh byte at the call
and after it. Visual families also compare the bone-query order and local points, and the whole model block when
no mesh is drawn. World predicates, the vector helpers (`0x00cfc922`, `0x00cfc94a`, `0x0095ea8e`, `0x00cfcead`,
`0x00cfcede`, `0x00a0c1d0`) and the sine `0x009681bd` execute as original code. Model lookup, TransformPosition,
CreateParticle/Sprite/Effect, AddTerrainLight and RenderMesh are recording boundaries. Samples cover signed type
extremes, every listed type and its two neighbours, sibling worlds 130..135 and 0, null objects, absent models,
hidden/visible emitters, scales that truncate past 65535 or below zero, and WorldTime at the edges of the
[0, 10) and [0, 30) windows (including non-finite and out-of-range clocks for the non-sine types).

**77/77 separately compiled planted mistakes are detected** (lowest count 4), with zero mutant stops. They
cover world gates, every type list's boundary members, range values, RNG divisors, the velocity division,
the sky-plate fields, particle counts/ids/sub-types/owners/lights, bones and local points, sprite scales and
lights, the hidden gates of the one-shot bursts, both phase windows, both scroll rates, the stream reset,
the mesh flags, the effect's scale argument, the sine rates and the model gates. The first run missed one mutant
(Temple of Arnil hidden range 0xa0..0xaa); directed boundary types (0x9f/0xaa, 0x5/0x3d, 0xae) fixed it.
Three planted changes were equivalent or did not compile under `-Werror` and were replaced.

## Tick order (the RENDER-WORLDS-P question)

None of the twelve methods reads the frame, action or model action table (static), so the native order needs no
deferral. 131/132/133 move only test the model, which the generic part already requires (`mu_obj_move_generic`
returns before the class without one). 134 move writes alpha, angle, velocity, blend V and hidden mesh. The
animation tick takes its speed before the class move in both orders, so a velocity written this frame applies
from the next tick, as in the original. Only the 131 create is deferred, because it draws from the RNG and
`mu_obj_create` has none. The objects host runs it right after CreateObject with the shared seed.

## Native consumption

`mu_obj_create`/`mu_obj_move` dispatch 132..134 creates and the 131/134 moves directly (131 lights and 134 lights
use the existing move-log light path). The production object host treats 131..134 as primary-visual worlds:
after RenderObject it consumes the outer RenderObjectVisual flicker draw (`0x017f9758` draws `rand % 30` before
its world dispatch whenever the type has a model), then calls the class visual with the current bones. A bone
case without enough bones (132 type 0xa needs > 3, 134 types 0x1e/0x47 need > 17) is refused and counted.
Sprites, particles and the `0x193` effect go to the existing hooks. **Refused and counted** (`draw_unsupported`):
the 134 extra RenderMesh of types 0x41/0x42/0x84/0x85/0x4d/0x4e (no native extra-mesh draw from the visual slot)
and the 134 `0x199` effect with its scale-derived eighth argument (its mapping into the effect info block is not
traced). Both are compared as requests; neither is approximated.

The host test (`native/tests/worlds_r_host.c`, authored twenty-bone model) checks the deferred 131 create
(RNG phase and after-character), the 0xaa velocity, the 131/134 lights, the 132 sky plate, the 133 type-6 flags,
134 alpha/turning and eleven visual runs of 200 preparations each. Those runs cover one-shot bursts that hide,
per-call bone particles and sprites, the 0x3c effect, the 0x49 light, mesh and keyed-effect refusals, model-gate
RNG stability and a missing-bone refusal. Portable tests check the public dispatch, the 131 deferral, exactly one
generic tick and log-capacity independence.

## Saved-capture fidelity (DATA-ACQ-002 arrival tiles)

Same method and readers as [captures 2](client-world-captures-2.md): `scripts/fidelity_tour.py run` at each
captured arrival tile, 1722 × 1048, 25 logic steps, the DATA-ACQ-002 plaintexts and installed assets. Before =
a clean build of main `3d17cac`; after = this branch on the same base. Camera eye/pitch/FOV/far equal live in all
four (eye distance ≤ 0.005).

| Capture | Static-field differences, whole map (near hero) before → after | Missing / extra | Image mean \|Δ\| / > 24 before → after | Light dumps |
|---|---|---|---|---|
| Scorched Canyon 236,14 | 4,374 (84) → **0 (0)**: range 4,192, after-character 181, velocity 1 | 0 / 0 both | 7.624 / 0.0280 → **8.562 / 0.0623** | identical |
| Red Smoke Icarus 130,116 | 1,812 (45) → **0 (0)**: after-character | 1 / 1 both | 26.344 / 0.3854 → 26.373 / 0.3859 | identical |
| Temple of Arnil 125,57 | 6,475 (166) → **0 (0)**: range 6,143, after-character 332 | 0 / 0 both | 1.028 / 0.0019 both | identical |
| Gray Aida 124,30 | 2,926 (135) → **1 (0)**: range 2,889, after-character 34, blend light 3 → 1 | 0 / 0 both | 13.153 / 0.2030 → **13.072 / 0.2018** | identical |

- Every created object's static fields now equal the live client's (15,587 → 1). The remaining Gray Aida field
  is one type-0x29 object's blend light: native 0.55, live 1.0. The render pass caps blend light to the alpha
  that the move sets (0.5, stepped to 0.55). The three other type-0x29 objects match live at 0.55. Inference:
  the live frame did not draw this one. None of these methods writes blend light (static).
- Scorched Canyon's image error rose. The correct ranges let ten more objects pass the native frustum test
  (266 → 276 drawn). Three of them lie 4,100–4,900 units from the eye in the ground plane, beyond the 3257.8 far
  plane: types 0x9b, 0x9b and 0x4b near x ≈ 19,400–20,350. The live frame marks those three not visible with the
  same range and camera. The after render shows a new dark translucent overlay in the lower left. Inference: these
  objects draw it, and the cause is native TestFrustrum2D/far-plane parity, not these methods (the G2 lane owns
  the far plane). The static fields of all 7,111 objects equal live.
- Temple of Arnil draws 104 more objects (487 → 591) with an unchanged image score, and Gray Aida 28 more
  (412 → 440) with a slightly lower one. Red Smoke Icarus changes only after-character, which has no native
  second pass in these worlds (`mu_world_defer` has no 131..134 branch), and gains its visual requests. Inference:
  the small image change comes from the new particles; live pools are not captured.
- Light dumps are byte-identical: no 131 type-0xa0 or 134 type-0x3f emitter lies in a moved sector at the
  arrival tiles (0 object lights in both builds).
- The 28 other DATA-ACQ-002 views: **56/56 frame PNGs, 28/28 OBJECT and 28/28 light dumps byte-identical**. The new
  branches test worlds 0x83..0x86 or the deferred-create event only.

WorldTime, RNG and animation phase differ from the live frame, so pulses, particles and phase windows are not
compared live.

## Limits and follow-ups

- The custom-render (`0x00e43842`, `0x00e00d4c`, `0x00d80cea`, `0x00d84d0e`), after-render (`0x00e43fab`,
  `0x00e010b6`, `0x00d81c49`, `0x00d868f7`) and invisible-sector slots of the four classes remain missing.
  So does the after-character second pass for 131..134.
- Refused requests that need native consumers: the 134 visual RenderMesh with StreamMesh (types
  0x41/0x42/0x84/0x85/0x4d/0x4e) and the 134 `0x199` CreateEffect eighth argument.
- Static consumer audit only (RENDER-EFFECTS lifecycles not re-verified): particles `0x7f89/0..4`,
  `0x7f89/0x1a`, `0x7ef7/0`, `0x801f/2`, `0x801c/8`, `0x801b/2`, `0x7f42/6`, `0x7f26/2`, sprite `0x7f26`, effect
  `0x193/3`.
- Scorched Canyon frustum/far-plane parity for the three far objects above.
- Captures with RNG/animation phase and particle pools would let the visual requests be compared live.

```sh
tools/python/bin/python scripts/validate_worlds_r.py --cases 1000 --mutations --output <json>
MU_RECOVERY_INTEGRATION=1 tools/python/bin/python scripts/run_validators.py --private --only validate_worlds_r
tools/python/bin/python -m unittest reconstructed/objects/test_worlds_r.py native/tests/test_native_worlds_r.py
```

[Handoff, gate and cleanup](../handoffs/RENDER-WORLDS-R.md).
