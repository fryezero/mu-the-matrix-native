# RENDER-WORLDS-RAKLION: Raklion's custom and after slots are Test Area 121's

Target: the executable SHA-256 `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`. Text and
second-image-data captures pinned in `scripts/pins.py` (capture09/run10). Method:
- an instruction-by-instruction diff of the two slots (stack offsets normalised; jump targets mapped through the
  alignment; data addresses compared as addresses);
- compiled authored C compared with the original instructions under the strict Unicorn machine
  (`scripts/validate_worlds_raklion.py`, which reuses `validate_worlds_121.py`'s slot comparison);
- the production runtime in a host (`native/tests/worlds_121_host.c`);
- the October 22 live capture of Raklion (three views, read only).

Labels: **verified** = instruction-compared, **static** = read from the disassembly only, **live** = from the
read-only October 22 capture, **inference** = reasoning.

Follows [RENDER-EFFECTS-019](client-render-effects-019.md) §3, which found that Raklion's custom slot makes the same
28 CreateParticle calls as 121's, and [RENDER-WORLDS-121](client-worlds-121.md), which ported 121's slots.

## 1. The custom slot `0x00e949f8` against 121's `0x00d58bd8` (static, then verified)

Class world-57 (worlds 57/58, vtable `0x01aad9d0`, slot 0x38): 1,994 instructions against 121's 1,972.
- Aligned, 1,972 instructions are the same. All their immediates, call targets, float constants and data addresses
  are the same addresses, not just the same values (0 data-address differences).
- Their branch targets map onto each other through the alignment. The two exceptions jump to the start of an
  inserted block (below).
- The stack frame differs in layout only: the handler is spilled to `[ebp-0x4c]` instead of `[ebp-0x94]`, and the
  locals move by 4 bytes.

The 22 extra instructions and the one different call:

| Address | Raklion | 121 |
|---|---|---|
| `0x00e94a04..0x00e94a16` | `call 0x00ea233c` (current world `0x01cf15fc` in 0x39..0x3a); false: return 0, nothing drawn or written | no world test |
| `0x00e96083..0x00e96094` | types 0x1ab..0x1ad: handler byte +0x22 == 0 returns 1 without drawing | draws the body (flags 0x80) |
| `0x00e96242..0x00e96268` | type 0x52: handler byte +0x22 == 0 sets frame `+0xd0` and prior frame `+0xd4` to 0, then the same RenderBody (hidden `+0x68`) | RenderBody only |
| `0x00e96527` | default: the base `call 0x00e9ef04` | `call 0x00d5c79c` |

- The two bases: 121's `0x00d5c79c` answers 0. Raklion's `0x00e9ef04` draws only types 0x836..0x83e and
  0x872..0x875, and answers 0 for every other type.
- The world manager passes types 0..300 only, so neither base, nor the 0x1ab..0x1ad gate, is reachable from the
  render pass.

Everything else is 121's ([121](client-worlds-121.md) §1). That covers:
- types 6..12: per-vertex light 0.5 and object light (1, 1, 1);
- 0x10/0x11: the action choice through SetAction `0x012affa4`;
- 0x13..0x15: the 28 bone-placed CreateParticle sites, the direct action writes and the `rand() % 40` returns;
- 0x14: four meshes with bitmap 0x800a;
- the 0x39/0x44/0x45/0x47/0x52/0x53/0x5c draws, and the after flags of 0x2e, 0x35, 0x4c, 0x53, 0x59, 0x5c.

**The handler byte +0x22 (static).**
- The constructor sets it to 1 (`0x00e9eebd`).
- The event-state setter (`0x00ea165f`, `ret 8`) writes its state byte to +0x20 (11 writes +0x21 instead and
  returns, `0x00ea1675`). Then, at `0x00ea1725`, it calls `0x00ea174a`, which sets +0x22 = (+0x20 <= 6), and
  `0x00ea176f` (the timer arm that RENDER-WORLDS-E ported).
- So while Raklion's event is past state 6, type 0x52 stays at frame 0.

**The bitmap 0x800a (static).** The object loader's Raklion case registers `Effect\Chrome08.jpg` as 0x800a (filter
0x2601, wrap 0x2900, `0x0183f4e2`), as 121's case does (`0x018417cd`). The case starts at `0x0183f494`, entry 23
of the jump table `0x0184307f`.

## 2. The after slot `0x00e96536` (verified)

198 instructions, the same as 121's `0x00d5a6cc` instruction for instruction: no world test, the same constants and
the same branches. Unlike 121, the client's after pass `0x016d6949` runs in 57/58: they are in its world list
(`mu_world_after_gate`). RENDER-WORLDS-A had ported it on its own (`mu_raklion_after`). It is now the shared routine.

## 3. Native

- **One routine, one row per class.** `world_test_area_visual.c`'s `ta_custom` takes a `ta_class` row:
  - Test Area `{0, -1, 0}`: no world test, no gate;
  - Raklion `{57, 58, 1}`: the world test `0x00ea233c`, then 0x52's frame restart while `handler_state` (the handler
    byte +0x22) is 0 (`ta_0x52`).
  - `ta_after` serves both after slots and answers whether it drew.
  - `mu_slots_raklion_custom` / `mu_slots_raklion_after` are the class entry points. `world_slots2_visual.c` maps
    57/58 to class 57.
  - 0x800a and type 0x14's bitmap list now also answer for 57/58.
- **The RENDER-WORLDS-A pieces it replaces.** Raklion's slots were bounded A-route pieces:
  - `mu_raklion_defer` (the after flags);
  - `mu_raklion_before` (the 0x53/0x5c first meshes);
  - `mu_raklion_after` (a second copy of the after slot).
  
  These are removed, with their runtime special cases: the `deferred` exception, the 0x53/0x5c draw-option tweaks
  and `mu_objects_first_meshes`' Raklion branch. Raklion is now a class-slot world: `mu_class_slots(57/58)`, the
  class custom render in the first pass, and the class after render in `mu_objects_prepare_after`.
  - `mu_world_after_enabled` keeps 0x39/0x3a for the pose's light-skip mesh (unchanged).
  - `mu_world_after_special` keeps the 0x4c select.
  - `mu_raklion_visual` (slot 0x34) is unchanged.
- **Runtime** (`mu_objects_runtime.c`, `mu_objects_raklion.c`):
  - `slot_model` passes `raklion_state[0x22]` as `handler_state` in 57/58.
  - `class_custom_call` routes 57/58 through `test_area_custom_call`, the same posed-bone particle path and scratch
    log as 121.
  - `slot_vertex_light` replays the per-vertex light as for 121.
  - `mu_objects_start` sets +0x22 = 1 (the constructor).
  - `mu_objects_raklion_set_event` sets it to event <= 6, except for 11.
- The particle kinds 0x801e/7, 0x801c/8, 0x801c/9 and 0x801b/5 are served since RENDER-EFFECTS-019, so none of
  the 28 sites is refused in Raklion.

## 4. Instruction comparison (verified)

`validate_worlds_raklion` runs `validate_worlds_121`'s slot family with Raklion's spec (`Spec`: class 57, the two
entries, own worlds 57/58, other worlds 56/59/0/2/121/140, the handler byte):
- `custom_raklion`: the custom slot against `mu_class_custom(57, …)`.
  - The first 301 cases sweep the types 0..300. One case in five runs in another world, where the world test
    answers 0.
  - The handler (ecx) byte +0x22 is 0, 1, 2 or 0xff, and is given to the native as `handler_state`.
  - Compared: draws with the StreamMesh byte and colour, particles, TransformPosition's bone list, the per-vertex
    light buffer `0x06fd0918`, the answer, rand, object and model fields, and the bitmaps.
- `actions_raklion`: 0x10, 0x11, 0x13..0x15 and 0x52 at their window edges, with targeted rand seeds.
- `after_raklion`: the after slot against `mu_class_after(57, …)`.

`validate_worlds_121`'s families now take that spec (121's is the default). `validate_render_worlds_a`'s Raklion
cases (`after_draw`, `first_draw`, `flags`) call the class entry points. Counts are in the
[handoff](../handoffs/RENDER-WORLDS-RAKLION.md#checks).

## 5. Fidelity against the October 22 capture (live)

Three views of world 57: `57-raklion` (the 14-view tour), and `57b-raklion-a` / `57b-raklion-b` (session 2).
- The live window screenshots of that session no longer exist locally. The comparison uses the OBJECT dumps
  (`fidelity_tour.py`'s per-field object scoreboard) and the light dumps.
- The default draw and the `live_time` clock give the same scores.

| Live field (objects, 1,521 matched per view) | 57 before → after | 57b-a | 57b-b |
|---|---|---|---|
| Object light `+0xec` (types 6, 7, 12 at (1, 1, 1) in live) | 5 → **0** | 5 → **0** | 5 → **1** |
| Action `+0x2a` (one type 0x14 at action 1 in live) | 1 → 1 | 1 → 1 | 1 → 1 |
| Near-hero object light differences | 2 → 0 | 4 → 0 | 2 → 0 |
| Frame light near the hero (mean abs) | 0.02574 → 0.02574 | 0.01049 → 0.01049 | 0.01517 → 0.01517 |
| Native object particles | 0 → 14 | 0 → 14 | 0 → 0 |

- **Live confirms the slot runs in Raklion.** In live, exactly the type 6/7/12 objects that are or were in view
  hold object light (1, 1, 1); the others hold 0. Before this lane, the native left all of them at 0.
- **The one light left in 57b-b.** It is a type-6 object at (20314, 22009). It was in view in 57b-a, and live keeps
  the light it got there. The native tour starts fresh at view b, where the object is out of view, so the slot never
  ran on it.
- **The action left.** The visible type 0x14 at (19614, 21513) is at action 1, frame 19.2 in live: the slot's
  frame >= 19 switch after a long history. The 25-frame native tour starts it at frame 0 and reaches 3.84
  (velocity 0.16). The switch needs about 119 frames; the code path is compared in `actions_raklion`.
- **Image.**
  - The only pixels that change at the arrival tile are the WATERFALL spray of that 0x14 statue (window region
    x 915..1137, y 0..167; mean |Δ| per channel ≈ 0.2 to 0.4 over the frame).
  - The five type 6/7/12 objects that pass the 2D range test are lit (light_enable 1). They sit at z −349..−403,
    500+ units below the hero (z 159), so they are not in sight at this tile (inference from the positions). Their
    changed light shows in the OBJECT fields, not in pixels.
- **Byte identity.** The other 13 October 22 views and all 32 DATA-ACQ-002 captures are byte-identical
  (PNG frames, OBJECT and light dumps).

## 6. Census

[RENDER-WORLDS-SLOTS](client-worlds-slots.md) §1 listed Raklion's custom slot `0x00e949f8` as "V A", and the
census counted it in 142/144 and then 144/144. RENDER-WORLDS-A had compared only its flag branches and the 0x53/0x5c
first meshes. Types 6..12, 0x10, 0x11, 0x13..0x15, 0x39, 0x44/0x45/0x47 and 0x52 were not native: they fell to the
generic RenderBody.
- So the census counted an entry address as covered while most of the slot was missing. The JSON scope said so
  ("bounded … remaining branches stay open"); the census line did not.
- The row now reads "V RAKLION", whole. The number stays 144/144.
- Karutan's custom slot `0x00e14596` ("V A") is in the same bounded state. Its JSON scope says so, and it is not
  this lane's. Since ported whole by [RENDER-WORLDS-KARUTAN](client-worlds-karutan.md) (its own code, not 121's).

## 7. Limits

- The 0x1ab..0x1ad gate and the base `0x00e9ef04` are not reachable (types > 300) and are not ported.
- The native has no authoritative feed of Raklion's event state (RENDER-WORLDS-E). +0x22 follows
  `mu_objects_raklion_set_event`, so in normal native play it stays 1 and 0x52 animates.
- The October 22 live PNGs are gone, so there is no live image metric for Raklion. History-dependent fields (a long
  animation, a light from an earlier view) remain as explained in §5.
- Bones beyond the model's bone count are refused natively, as for 121.
