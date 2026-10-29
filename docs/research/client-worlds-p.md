# Old Kethotum, Burning Kethotum and Bloody Tarkan primary handlers

RENDER-WORLDS-P, 2026-10-28. The three primary methods (create +2c, move +30, visual +34) of the world-135,
world-136 and world-140 classes are implemented in `reconstructed/objects/old_kethotum.c`,
`burning_kethotum.c` and `bloody_tarkan.c` (shared move template in `worlds_p_internal.h`). All nine have an
instruction-compared family; the [inventory](world-handler-coverage.md) records the new counts. Custom-render,
after-render and invisible-sector slots of these classes stay missing.

## Selection and provenance

All three classes have a DATA-ACQ-002 arrival capture ([captures 2](client-world-captures-2.md)): Old Kethotum
128,17 (4,940 objects), Burning Kethotum 127,17 (3,784) and Bloody Tarkan 128,38 (3,055). Labels:
**verified** = compared with the original instructions under Unicorn; **static** = read from disassembly;
**inference** = neither.

Target `main.exe` SHA-256 `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`. Capture09 text at
`0x00401000`, SHA-256 `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`; run10 data at
`0x01a7c000`, SHA-256 `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`. The validator pin-checks
both and reports each range's digest. Restored Linux/Wine x86 instructions, not native Windows evidence.

| Family | Original half-open range | SHA-256 prefix | Cases |
|---|---|---|---:|
| Old Kethotum create | `0x00e3a4dc..0x00e3a719` | `bbaa87fc07acb8ae` | 1,000 |
| Old Kethotum move | `0x00e3a719..0x00e3ae5e` | `0b174f76510e7adf` | 1,000 |
| Old Kethotum visual | `0x00e3c137..0x00e3c739` | `a01ed0d28fb2ccfc` | 1,000 |
| Burning Kethotum create | `0x00d9381e..0x00d93b31` | `aefcbc5bce5540a8` | 1,000 |
| Burning Kethotum move | `0x00d93b31..0x00d94eef` | `0d7e838c6454cbf8` | 1,000 |
| Burning Kethotum visual | `0x00d97186..0x00d97384` | `8eeddee27900228e` | 1,000 |
| Bloody Tarkan create | `0x00d9a022..0x00d9a0ad` | `58dba7d4bc98702e` | 1,000 |
| Bloody Tarkan move | `0x00d9a0ad..0x00d9a2ed` | `8db6802f11bba5f8` | 1,000 |
| Bloody Tarkan visual | `0x00d9ac33..0x00d9ac50` | `131b2883c83a66aa` | 1,000 |
| Clamped AddTerrainLight | `0x016caeae..0x016cb08d` | `4fb18dd82fbd4656` | 1,000 |

## Verified behaviour

**World predicates** (static, executed in every family): `0x00e3dd42` accepts 0x87, `0x00d99c0f` 0x88,
`0x00d9bd83` 0x8c. Create and move return false for another world or a null object.

**Kethotum create** (135 and 136). With a model, every action PlaySpeed (action table +0x30, entry +4) becomes 0.3.
Types 0xa0..0xaa are hidden (-2). Range -300/-600 for the listed scenery. Types 0x16/0x29/0x5c/0x74 scale action 1 by
1.03, set the after-character byte and draw a rest count `rand % 10 + 15` into +0x34; 0x77/0x81 scale action 1 by 1.01.
135 types 0xf/0x10 draw a phase `rand % 10 * 300` into +0x64. 136 types 0x99..0x9c draw `(rand % 18 + 1) * 10`
into +0x60; 0xb5 draws `rand % 4 + 1` into +0x34, scales action 1 by 0.9 and sets after-character. Both return true.
Types that scale action 1 dereference the model unconditionally (the original faults without one; never sampled).

**Kethotum move**, one template with class-specific sound ids. Hero distance is the 2-D float distance through
`0x00961a07` sqrt. Ambient sounds: 135 type 0x17 `0x557` within 800 (returns false), 136 type 0x19 `0x558`
within 800 (false), type 0x28 scrolls blend V by -0.02 and plays `0x54c` within 1300, type 0xa0 `0x54b` within 400.
Swinging types 0x16/0x29/0x5c/0x74: while swinging and within 1000, 0x16 plays `0x549` and 0x5c plays `0x548`
in frames (0.85, 1). Then, with frame >= keys - (speed + frame time): rest (action 0) counts loops in +0x30 and
starts swinging when it equals +0x34; swinging returns to rest with a new count `rand % 10 + 15`. Gates 0x77/0x81:
within 300 they open (0 → 1 with `0x55b`, 1 → 2 at its end, 3 → 1 with `0x55b`); at 300 or beyond (and for a NaN
distance's near branch) they close (1 at its end or 2 → 3 with `0x55c`, 3 → 0 at its end). SetAction `0x012affa4`
runs as original code: bounded by the model's action count, no-op for the same action.

136 adds braziers 0xa5: `0x54b` within 400, warm light `(s, 0.6s, 0.2s)`, `s = (rand % 4 + 3) * 0.1`, range 1 below
scale 1.15, 2 below 1.35 (double compare), else 3. Type 0xb5 is a rest/rise/fall cycle on actions 0..2 with the glow
flag +0x38 and level +0xc8 driven by the frame time (rise +0.5 dt above 0.65 sets the flag; fall -0.4 dt, re-rise
in the first fifth of action 2 clamped to 1, flag off below 0.1), sounds `0x559` (action 0, frame > 3, < 1200) and
`0x55a` (action 2, frames (7, 8), <= 1200), and the loop/rest counters +0x30/+0x34. Before that, when the object's
attached-effect container `0x00d99e3f` is empty, it asks the C++ effect manager `0x00a797a0` for four red `.ein`
effects (`fire09-red01`, `Sparkle21-red01`, `smoke17-red01`, `twinkle10-red02`; offsets (0,0,-20)/(0,0,0); lives
35/50/50/200) and attaches them through `0x0129f9c6(effect, 0x14, 1, 0, 0.0)` only when all four are valid.

**Visual** (all three return false). 135 type 0xf: TransformPosition of bone 4; one in seven a `0x7efa/2` particle
(scale 0.25); a `0x7ef7` sprite of scale `1.5 + 0.1 sin(((int)t % 3000) * 0.0010466667)`; a `0x7f26/14` particle
(angle (0,0,1), scale 0.06) while `sin(0.001 t + phase) > 0.5`. Type 0x10: bones 5, 6, 7, 11, 14, 15, pulse
`|sin(float((phase + t) * 0.0002 * k))| * 0.4` (the original comparison-based absolute value `0x0184f8ff` keeps
negative zero), `0x7f26` glows at scale 2 and dim overlays at 1.5. Type 0xa5: one in a hundred CreateEffect `0x59a`
subtype 3 owned by the object. Both 0xf/0x10 return before any RNG without a model. 136 type 0xa5: the Karutan-like
brazier (`0x7ef7` flare at twice the object scale, then one of `0x8084/0`, `0x806e/4`, `0x8085/0`). 140 has no
visual case. The slot's model argument gates all three.

**Bloody Tarkan.** Create sets after-character on 0x11/0x12/0x44/0x46 and hides 0x51/0x52/0x5f/0x64/0x65.
Move: type 0x51 warm flicker `(0.8s, 0.3s, 0.04s)` range 3; type 0x13 pulse `sin((angle_z * 100 + t) * 0.002) *
0.15 + 0.65` into blend light with blend mesh 0, and a range-3 light through `0x016caeae`: AddTerrainLight with
each channel clamped to 0..1 (verified as its own family on full 256 × 256 grids).

## Comparison and mutants

Ten families, **10,000 cases, 10,000 equal, zero mismatches or stopped cases**. Each compares AL, all 984 OBJECT
bytes, ordered output calls (particle, sprite, light, clamped light, effect, sound, `.ein` create/attach) and final
MSVC RNG; create also compares the model's action table, and visual the bone-query order and local points.
World predicates, vector accessors, sqrt, sine, the absolute-value helper, SetAction and the validity test
`0x00a78918` execute as original code. Model lookup, TransformPosition, emission services, the effect manager,
string/vector constructors and destructors and the attach call are recording boundaries. Samples cover signed type
extremes, sibling worlds, null object, missing model, action counts 0..8, actions 0..3 and 5, exact distance
thresholds on integer positions, frames at key boundaries, signed-zero and finite clocks within ±1,000,000.
The `.ein` boundary proves the requests and the all-valid condition, not the effect system.

**51/51 separately compiled planted mistakes are detected**, with zero mutant stops: gates, ranges, hidden ranges,
speeds, RNG divisors, sound ids, distance comparisons (> vs >=), SetAction targets and bounds, frame-time terms,
bones, scales, the `fabsf` signed-zero error, `.ein` lives and validity mask, glow thresholds, the 0xb5 counters,
the brazier range, the Bloody Tarkan pulse/blend/light terms, its visual return and the clamp/falloff of
`0x016caeae`. The first run left six mutants undetected; four were boundary cases the sampling rarely reached
(exact distances, frame 0.85, glow 0.65, the first fifth of action 2), fixed with directed samples. One planted
change (`1.35` double vs `1.35f` compare) is equivalent, since no float lies between the two, and was replaced.

## Native consumption

`mu_obj_create`/`mu_obj_move` run Bloody Tarkan directly. For 135/136 they log a deferred request: the objects host
(`native/core/mu_objects_worlds_p.c`) runs the class create with the type's model action table and the shared RNG
right after CreateObject, and the class move right after the object's animation tick, the original order (the move
compares frames the tick just advanced). The written action speeds (16 per type) feed the generic move's PlaySpeed
lookup for actions 1/2 of the swinging, gate and 0xb5 types. Frame time is the native constant 0.1 (`0x01cf103c`).
The visual pass poses 135 objects (also hidden ones), consumes the outer RenderObjectVisual flicker draw (as Karutan),
refuses and counts missing bones, and routes sprites/particles/effects to the existing hooks. Clamped lights carry
`MU_OBJECT_LIGHT_CLAMPED` and apply through the verified C. There is no native `.ein` effect system: the container
stays empty and each 0xb5 request is counted in `move_unsupported`, never approximated.

The production host test uses an authored sixteen-bone, four-action model: create speeds and rest counts, a full
rest→swing cycle with its sound after real ticks, the gate's open/close cycle with sounds, the counted `.ein`
refusal, brazier and clamped lights, 200-preparation visual runs for five world/type pairs, model-gate RNG stability,
missing-bone refusal and sibling-world dispatch. Portable tests check public deferral, exactly one generic tick and
log-capacity independence.

## Saved-capture fidelity (DATA-ACQ-002 arrival tiles)

FIDELITY_TABLE

## Downstream and continuation

Static consumer audit (not part of the instruction proof): particle `0x7efa/2` and `0x7f26/14` of 135, effect
`0x59a/3` and the 136 brazier kinds `0x8084/0`, `0x806e/4`, `0x8085/0` go to the existing particle/effect hooks;
whether each has a native lifecycle is RENDER-EFFECTS work. The `.ein` effect system (four red effects on 0xb5) has
no native consumer. Open: the classes' custom/after/invisible slots, the per-type model PlaySpeeds before create
(loader, not traced), captured RNG/animation phase and particle pools, and a synchronized live image comparison.
