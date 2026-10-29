# RENDER-WORLDS-Q2: Ferea's visual, the class draw-first slot 0x10, the Kanturu blend light and the world leftovers

RENDER-WORLDS-Q2, 2026-10-29. The world leftovers of [Q](client-worlds-q.md), [R](client-worlds-r.md),
[R2](client-worlds-r2.md) and [AFTER2](client-worlds-after2.md). Target `main.exe` SHA-256
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`; capture09 text and run10 data pinned in
`scripts/pins.py`. Labels: **verified** = compared with the original instructions under Unicorn or with a live
capture; **static** = read from the disassembly; **inference** = neither.

## 1. Ferea's visual slot 0x34, `0x00de6405..0x00de8a10` (verified)

2,328 instructions, `thiscall(handler, object, model)`, ret 8. The method is bounded: no world test, false without
object or model, 23 type cases, true for each, false otherwise. Its size comes from vector-class code (the
`0x0098a0e5`/`0x00cfc94a`/`0x0095eda9` constructors, accessors and destructors, 111 accessor calls) and from
`std::string`/`std::vector<std::string>` bone-name lists, not from unbounded work.

| Type | Requests |
|---|---|
| 6 | none (true) |
| 9 | `timeGetTime % 100 < 30` and `rand_range(0, 10, 1) == 0`: particle 0x7f89 sub 0x1c, light (0.05, 0.05, 0), owner |
| 17 | `s = rand_range(0.58, 0.76, 100) · scale`; bone `mansionA007`: CreateEffect 0x413 (sub 0xa, no owner, scale s, light 1), sprite 0x7ef7 at +25 z (2·scale, (1, 0.2, 0)); then 71's smoke |
| 28 / 32 / 33 / 130 | `rand_range(0, 4, 1) == 0`: particle 0x7f89 sub 0x1b, lights (0, 0.03, 0) / (0.03, 0, 0.06) / (0.05, 0, 0) / (0.03, 0.03, 0.07) |
| 36 | bones `e01`..`e06` (k = 0..5): `s = |sin((float)((+0x64 + WorldTime) · 0.0002 · k))| · 0.4` (fabs `0x0184f8ff` keeps −0 and NaN signs); two sprites 0x7f26 per bone: scale 2 with (1.3, 1.3, 1.9)·s, scale 1.5 with 0.15 |
| 71 | `rand_range(0, 4, 1) == 0`: particle 0x7f5a sub 0x45 at +110 z, light (0.3, 0.2, 0.2), owner |
| 72 | CreateEffect 0x413 (sub 0xa, scale) and sprite 0x7ef7 (2·scale, (1, 0.2, 0)) at the object |
| 75 / 81 | `rand_range(0, 1, 1) != 0`: particle 0x7efa sub 6 scale 1, light (0.5, 0.8, 1) / 81: (1, 0.5, 0); bones `Point02`, `Point03`, `objSphere002`: sprite 0x7ef7 1.5 (0.5, 0.8, 1) |
| 87 | bone `Bone21`: particle 0x801c sub 0xe at +30 z (0.7·scale), on `rand_range(0, 2, 1) == 0` 0x801b sub 2 at the bone (0.4·scale); bone `Bone01`: the same at +45 z with scale 1, both at +45 |
| 95 | bones `e01, e02, e04, e03`: 0x801c sub 0xe (0.5·scale) and gated 0x801b sub 2 at the bone; bones `e05, e06, e08, e07`: 0x801c at the bone (scale), gated 0x801b at +15 z |
| 123 | light (0.1, 0.9, 0.9), (0.9, 0.2, 0.2) in handler states 2 and 3; `s = rand_range(0.546, 0.714, 1000) · scale`; bone `Crowd01` (local 0): CreateEffect 0x413 sub 0x11 scale s; gated particle 0x7f5a sub 0x45 at +40 z with 0.3·light |
| 128 | `rand_range(0, 34, 1) == 0`: `r = rand_range(0.03, 0.48, 100)`, particle 0x7dea sub 0 light r |
| 129 | `w = sin((angle z · 5 + WorldTime) · 0.002) · 0.3 + 0.7`; bone `Bone02`: sprite 0x8021 scale 1.5w, light (w/1.7, w, w) |
| 140 / 141 / 142 | particle 0x801a sub 2 on `rand_range(0, 1, 1) == 0` / 0x801c sub 4 always / 0x801b sub 2 on `rand_range(0, 2, 1) == 0`, light 1, no owner |
| 148 | bone `E01`; `r = (int)WorldTime % 3600 · 0.1`; sprite 0x7f67 (scale·0.4·1.2, (0.4, sin(WorldTime·0.7)·0.2 + 0.3 + 0.5, 0.4), rotation −r); sprite 0x8145 (scale·0.4·0.35, (0.1, 0.4, 0.98), r); gated particle 0x8017 at +15 z (scale·0.4·1.8, (0.4, 0.4, 1)) |

Particles are CreateParticle(bitmap, position, angle, light, sub, scale, owner object or 0, 0), sprites
CreateSprite(bitmap, position, scale, light, object, rotation, 0, 4, {1, 1, 1.0}) and the effect is CreateEffect(0x413,
position, angle, light, sub, 0, −1, 0, 0, 0, scale, −1, 0, 0), the scaled unowned form the native
`effect_scaled` hook already consumes. The named bones go through `0x0129f18a(std::string, 0)`: the type's model
(`0x00966cc4`/`0x00eaa8cf`), its bone records (+0x2c, 0x8c bytes, name at +0, count +0x22), first equal name,
`0x06fce398 + 0x30·k`. A model without the name returns a null matrix and TransformPosition faults in the client.

C: `mu_ferea_visual` and `mu_ferea_visual_bones` (`reconstructed/objects/ferea.c`); `mu_q_inputs` gains
`bone_index(context, name)`. When a named bone is missing (or no posed model), the C answers −1 before any request,
and the runtime counts it in `draw_unsupported`.

## 2. The draw-first answer `0x017fcd18` and the class slot 0x10 (verified)

R2 recorded Twisted Karutan's range −800 as unresolved, with no `+0xc0` store in its create, move, visual or
invisible-move slot. A byte scan of the pinned text for `−800.0` (one constant, `0x01aa91a8`) finds two class-142
stores. One is the second-pass selector slot 0x14 (`0x00e67293`), already native (`world_after.c`). The other is
**slot 0x10, `0x00e67005`**. Its only caller is the manager wrapper `0x00ea2788`. That wrapper's only caller is the
tail `0x017fe8f7` of the render pass's draw-first predicate `0x017fcd18`, which native modelled for world 0 only.

`0x017fcd18`: worlds 0, 2, 0x21, 0x25, 0x33, 0x38, 0x39, 0x3a, 0x49, 0x4a, 0x5b, 0x5c, 0x64, 0x65, 0x6e..0x71, 0x7a,
0x83..0x85 have their own cases (not modelled here). Every other world runs a default chain: `0x009a645f`
(world 0x27, tower state), `0x00e94004` (0x3f), `0x00e3068f` (0x52..0x5a), `0x016a887a` (0x74..0x78), Kubera
`0x00e1e4b6`, `0x016a8325` (0x80..0x82). When each of these is false, the answer is the current class's slot 0x10.
The base `0x00d5cbc9` answers no. The twelve overrides belong to worlds 134..145: a type list, then
`TestFrustrum2D(x/100, y/100, range)`. 142 first stores range −800, 145 requires the live byte, and 137, 139 and 140
answer no. An object answered yes is drawn before the frustum test, and the subsequent test uses the stored range.

C: `mu_class_first` / `mu_class_first_owned` (`reconstructed/objects/world_first_visual.c`), wired into the native
`render_first` callback for worlds 134..145 (the callback context now carries the frustum inputs).

## 3. Kanturu Underground's type-0xa blend light (verified, no code change)

The move slot (`mu_kanturu_ug_move`, validated in P2) writes `clamp(sin(WorldTime · 0.0015) + 1, 0.1, 0.9)`. The
live capture's WorldTime (`0x06fce370`) is 2,189,675, so `sin(3284.5125) + 1 = 0.0003` clamps to **0.1, the live
value**. The headless tour ends at tick ≈ 100,960 (clock start 100,000, 40 ms steps), which gives 1.6 and clamps to
0.9. The writer is correct; the remaining difference was the tour's clock. `scripts/fidelity_tour.py` gains an
opt-in manifest key `"live_time": true`: it starts the clock (`--time-series-start-ms`) so that the last step's
reported tick equals the capture's WorldTime. The frame cap depends on the clock, so the start is corrected from
the reported tick, up to six passes; all 32 captures land exactly.

## 4. Ferea's door states and Swamp of Darkness' variant (static: server-driven, not ported)

- Ferea handler +0x48 is a state object {state, last frame, door object (+0x50)}. Slot 0x28 `0x00de5b82` steps it
  with `0x00dee69a`: the door in action 1 plays 0x475 and settles to state 0 at frame ≥ 11 (or a stalled frame), in
  action 2 plays 0x476 and settles to state 3 at frame ≥ 12.5, otherwise `SetAction(door, state)`. It then
  decrements +0x14 in state 3 and switches the BGM `Feria_BGM`/`Feria_BGM_Boss` with sounds 0x46f/0x470. States 1
  and 2 are written only by `0x00dee662` (3 → 1) and `0x00dee67e` (0 → 2), called from `0x00dee27b`. That handler is
  reached from the packet dispatcher at `0x0128b204` through `0x012146ca(0x70)`, with payload byte +4 = 0 → open,
  1 → close (+ `0x00dede9a(0)`). Offline the constructor `0x00dee633` state 0 is the right value.
- Swamp of Darkness +0x78: besides the constructor (`0x00e54359`, 1), the only writer is `0x00e5eef9`. The class
  message method `0x00e5ea8f` calls it on sub-code 0x25; payload byte +4 maps 0..2 → 0, 3 → 1, 4 → 2, and it retypes
  the live 0x58/0x6b/0x6c objects. Both writers are network messages, out of scope; constructor values remain.

## 5. Acheron's bone sprites (measured, cause narrowed)

The Q inference "inside the meshes" is **refuted**. With temporary local switches (not committed) on the 91
capture: sprite depth test off, all sprites ×20 scale, and every step drawn (`draw_all`), the saved frames stay
byte-identical. The visual creates them (150 over a draw-all run; 12 positions within 1,700 units of the hero, in
the view direction), the shared sprite pass counts 6 drawn per frame, and Spark04 (0x8155) is a registered startup
bitmap. The quads reach `mu_pt_sprites_render` but no pixel changes. The cause is in the shared sprite/particle
draw path (RENDER-EFFECTS area): next, trace the GL sink of `mu_world_particles_draw` for object-owned sprites.

## 6. Checks

`scripts/validate_worlds_q2.py --cases 1000 --mutations` (registered `validate_worlds_q2`):

| Family | Cases | Result |
|---|---:|---|
| `ferea_visual`: the slot and its helpers as original code (SEH, vector/string/vector-of-string helpers, `0x0129f18a` over a synthetic bone table with decoys and duplicate names, `0x011ff622`, CRT sine, fabs); recording stubs rand, model container, CreateParticle/Sprite/Effect, TransformPosition, timeGetTime, CRT malloc `0x019a4da0` (bump) and free `0x0191c490` (every block must come back) | 1,000 | equal, 0 stops |
| `class_first`: slot 0x10 of the class of a sampled world (twelve overrides + base, vtables from the factory), TestFrustrum2D as original code; a sweep of every listed type ±1 first | 2,000 | equal, 0 stops |
| `render_first`: the whole `0x017fcd18` for worlds reaching its default chain (manager singleton `0x00ea594b` stubbed with a handler of the world's vtable) | 1,000 | equal, 0 stops |

**4,000 cases equal, 0 mismatches, 0 stops; 50/50 compiled mutants detected** (34 Ferea, 16 slot 0x10; lowest
counts 1). `validate_worlds_q` keeps its 11,000 cases and 45 mutants (its `Inputs` gained the trailing
`bone_index`). Portable: `reconstructed/objects/test_worlds_q2.py` (3 + 1 private) and new Ferea checks in
`test_worlds_q.py`; the production host `native/tests/worlds_q_host.c` now asserts Ferea's primary visual (type 141's
CreateParticle replaces the generic hook). Coverage: **109/144 primary methods** verified (was 108).

## 7. Fidelity (DATA-ACQ-002, 32 captures, 25 steps, 1722 × 1048)

Base = origin/main `9b821b19` + AFTER2 (`f9e8ed71`), lane = this branch, same tour. Default clock:

| Capture | Image mean \|Δ\| | Notes |
|---|---|---|
| 112 Ferea | 2.348 → **2.250** (share > 24: 0.0043 → 0.0034) | the visual now runs (primary-visual world) |
| 142 Twisted Karutan | 7.145 → 7.145 | range differences **3,868 → 0**; first-pass draws 211 → 803, frame changed but the mean is equal at 3 decimals; velocity 123 remains |
| 144 Swamp of Destruction | 12.415 → **12.395** | draws 160 → 237 |
| 135 / 136 / 138 | 1.936 / 6.532 / 3.825 unchanged | draws 80 → 82 / 53 → 55 / 153 → 224, PNG identical (OBJECT dumps differ: frames/actions of the extra draws) |
| 143 Kardamahal | 10.911 → 10.911 | draws 294 → 303 |
| 137 Kanturu Underground | 6.362 → 6.362 | blend light 0.9 vs 0.1 remains on the default clock (§3) |
| the other 25 | — | PNG, OBJECT and light dumps byte-identical |

Live clock (`live_time`, both binaries): Kanturu Underground **6.362 → 5.043** with zero blend-light differences
(base and lane equal: §3 needs no C change); Twisted Karutan 6.394 with zero range differences on the lane (base:
3,868); Ferea 2.348 → 2.250; Acheron 6.400, Burning Kethotum 5.403, Old Kethotum 1.798 (time-dependent fields closer
to live; same in base and lane). 25/32 captures stay byte-identical base → lane under the live clock too.

## 8. Limits and next

- `0x017fcd18`'s own world cases (0, 2, 0x21, 0x25, 0x33, 0x38..0x3a, 0x49, 0x4a, 0x5b, 0x5c, 0x64, 0x65,
  0x6e..0x71, 0x7a, 0x83..0x85) and the true branches of its default chain are not modelled (world 0 keeps its
  static types 0x37/0x3c).
- Velocity differences of 140, 142..144 (0.6/0.1/0.2/0.3/0.07 against the generic 0.16) are not written by the
  slots read here; next: the generic move's velocity source.
- Ferea door / Swamp variant: server messages (§4).
- Acheron sprites: shared sprite draw path (§5).
- Not done (time): the custom/after slots of 133 and 144 and of 141, 143, 145 (about 2,300 instructions each).
- No original client or launcher was started; the DATA-ACQ-002 inputs were only read.

```sh
tools/python/bin/python scripts/validate_worlds_q2.py --cases 1000 --mutations --output <json>
MU_RECOVERY_INTEGRATION=1 tools/python/bin/python scripts/run_validators.py --private --only validate_worlds_q2,validate_worlds_q
tools/python/bin/python -m unittest reconstructed/objects/test_worlds_q2.py reconstructed/objects/test_worlds_q.py native/tests/test_native_worlds_q.py
```

[Handoff](../handoffs/RENDER-WORLDS-Q2.md).
