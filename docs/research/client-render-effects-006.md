# World objects' owned effects and EffectManager requests (RENDER-EFFECTS-006)

RENDER-EFFECTS-006, 2026-10-28. The world lanes N–R2 refused and counted two kinds of request they could not
hand to a native consumer. This lane consumes both:

1. **CreateEffect with the object as owner and info word4**: the bat `0x195/0`, the shoal `0x199/0` and `/1` and
   the sea leaf `0x59a/3`, requested by Acheron 57, Swamp of Darkness 83/176, Kubera 161, Gray Aida 0x46,
   Old Kethotum 0xa5, Twisted Karutan 196, Kardamahal 161 and Swamp of Destruction 185.
2. **C++ EffectManager (`.ein`) requests**: Burning Kethotum (136) type 0xb5's four red effects.

It also adds the four particle kinds these effects and Old Kethotum type 15 emit: flare01 `0x7ef7/9`, Spark02
`0x7f25/15`, `0x7efa/2` and Spark03 `0x7f26/14`.

Evidence labels: **verified** = equal to the client's instructions under Unicorn (`scripts/validate_render_effects6.py`);
**static** = read from the disassembly only; **live** = read from the DATA-ACQ-002 captures (read-only).

| Input | SHA-256 |
|---|---|
| Restored text at `0x00401000` (capture09) | `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` |
| Second section at `0x01a7c000` (run10) | `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f` |

## 1. What the owner and word4 do (verified)

The wrapper `0x013c0eaa(type, position, angle, light, sub, owner, key, skill, word4, word6, scale, field8, ...)`
builds the info block; the world visuals pass `(…, object, -1, 0, (u16)(int)scale, 0, 0.0, -1, 0, 0)`.
CreateEffect `0x013c0f19`'s common part stores the owner pointer at `+0x34c`, copies the owner's position into
`+0x1d0` with the terrain height, and the info words: key → `+0x54`, word4's low byte → `+0x3b`, skill → `+0x3c`,
field8 → `+0x364`. MoveEffect `0x0142fd09` refreshes `+0x1d0` from the owner each step. Neither routine
de-duplicates by key, and the owner does not tie the effect's life to the object: each request is a new record of
the 200-record pool with its own lifetime.

Per kind:

| Kind | Create | Move | Owner / word4 use |
|---|---|---|---|
| `0x199` shoal (`0x013c39d9`) | `+0x3b` = 0 (word4 overwritten), lifetime 1000, speed 1, swings 1/1, position ± rand % 200 − 100 (z, y, x), angle z + rand % 360, drift y `(rand % 8) · 0.1 − 5`, scale + (rand % 5) / 40, start point `+0x110`, light from its blend light (0.1, 0.1, 0.25); subtype 1 keeps the caller's light | `0x01435aed`: one step in 40 each swing reverses the speed and redraws yaw (5..7) or pitch (1..3) swing; 500 units from the start point it turns back once (`+0x3b` = 1, 50 steps left); yaw/pitch sway with `sin(((int)t % 10000) · 0.0001)`; a flare01 `0x7ef7/9` particle at its scale every step; then the generic animation and rotated motion | none |
| `0x195` bat (`0x013c3d67`) | lifetime 150, speed 0.3, angle z + rand % 60, its model posed once, drift y = −20 × owner scale | `0x01435e18`: its animation, the rotated motion, z + (rand % 15) · 0.3; `0x014ecc0f`'s list skips the generic animation and motion | owner scale `+0xa0`, read without a null test; word4 stays in `+0x3b` (unused) |
| `0x59a` sea leaf (`0x013f5b63`) | lifetime 250, speed 0.3, unlit (`+5` = 0), `+0x3b` = rand % 2 (word4 overwritten), drift y = −5 × owner scale, scale 0.35 | generic animation, then `0x014ed512`: turns ±rand % 10 by `+0x3b`, bobs (one step in 32 a new climb, ±0.2 jitter, pushed back at terrain + 50 / + 150, z jitter 0.3); subtype 3 draws a flare01 sprite (light `l·(0.6, 1.2, 1.2)`, `l = (rand % 32 + 64) · 0.01`) owned by the effect and one step in three a Spark02 `0x7f25/15` spark (scale 1.1) owned by the effect; then the rotated motion | owner scale `+0xa0`, no null test |

Models (static, loaders): `0x195` hs_flybatA from `Data\Object124\` (Kubera's class loader `0x00e196c8`, before its
123..127 switch) and `Data\Object144\` (Kardamahal `0x00e0e603`; that file is **not installed**, the model getter
then returns an empty model and nothing is drawn); `0x59a` zu_sealeaf04 from `Data\Object92\` (OpenWorldModels
`0x01840f53`, worlds 91, 92) and `Data\Object123\` (`0x01841845`, world 122, and the class loader `0x00e3a40f`);
`0x199` Fish02 only in Atlans and the abyss (`0x018399bf`, `0x01841a7a`). In the worlds that request `0x199` (122, 134,
142, 144) and `0x59a` in 135 the index has no model: the getter `0x00eaa8cf` returns an empty model (not NULL),
PlayAnimation returns true without a step, and only the effect's sprites and particles show (static).

## 2. The four particle kinds (verified)

Located by tracing the client blocks the harness executes for each kind:

* flare01 `0x7ef7/9` (create `0x015eece3`, move `0x01663eaf`): lifetime `(int)(40 · scale)`; shrinks 0.011 per
  step, dies at scale ≤ 0 or not live; light × 1.05 while lifetime ≥ 75, else ÷ 1.05.
* Spark02 `0x7f25/15` (create `0x015dc098`/`0x015dce61`, move `0x0165006b`): lifetime rand % 12 + 12, the given
  scale, start colour = light; light = lifetime/16 × start colour, falls 2 per step, bounces off the terrain
  (×−0.6, lifetime −4).
* `0x7efa/2` (create `0x015c336e`, move `0x016329f8`): scale 0.1, `+0x88` = the given scale, lifetime rand % 10 + 20,
  position ± 25, gravity 1, random angles, velocity rotate((0.4, 0.4, 0.4)), rotation ±10; scale =
  `sin(lifetime · 2 · π/180) · +0x88`. RenderParticles' table `0x015ae4bf` sends subtype 2 past the sprite: only
  its blend state is set, nothing is drawn.
* Spark03 `0x7f26/14` (create `0x015de717`, move `0x01651e01`): one call in two keeps the common LifeTime 2;
  otherwise alpha 1, velocity (rand % 4 − 4, rand % 4, rand % 4), lifetime 30, scale (rand % 5)/10 + 0.4; light ÷ 1.05,
  scale − 0.01, alpha − 0.001, dead at alpha ≤ 0.

## 3. The EffectManager requests of 136 type 0xb5

RENDER-WORLDS-P verified the request boundary: while the object's effect list `+0x3d0` is empty (`0x00d99e3f`),
each move asks the factory `0x00a797a0` for `fire09-red01` (scale 35), `Sparkle21-red01` (50), `smoke17-red01`
(50) and `twinkle10-red02` (200), all at (0, 0, −20), rotation 0; only when all four are valid does it attach them
with `0x0129f9c6(effect, bone 0x14, follow 1, timed 0, lifetime 0.0)`. NATIVE-FX-002 already ports the factory
(template cache and clone) and the node update. This lane adds the request path between them:

* **Create**: the native factory's template load decides validity first (the factory returns a null effect when the
  `.ein` cannot be loaded), so the all-valid gate holds without creating instances that would be dropped. With four
  valid templates the four clones are created and attached; otherwise the request is refused and counted
  (`move_unsupported`) and repeated next step, as in the client.
* **Attach** (`0x0129f9c6`, static): the record {effect, template scale = the effect's scale, bone, follow, timed,
  lifetime} joins the object's list; the owner of the tree is the object.
* **Update** (`0x0129f671`, static), called by RenderObjects right after RenderObjectVisual (`0x016d51d8..0x016d51f5`,
  dt `[0x01cf103c]` = 0.1): timed records lose dt and leave the list at zero; the effect's scale becomes template
  scale × object scale `+0xa0`; with follow bone b ≥ 0 the external matrix is `0x0129fd4f`: the bone's 3×4 from the
  pose buffer transposed into a column-major 4×4 (`+0x318` is 0 for map objects, so the shared pose buffer
  `0x06fce398 + 0x30·b` that RenderObject has just filled), multiplied by the object's position/scale matrix only when
  the predicate `0x012a0d29` (`+0x350 == 0 && +0x354 == 0`) holds. **Live**: in the 136 capture these two words are
  the sector-list links and are set on 3,575 of 3,784 objects (all five 0xb5), so the bone matrix alone places the
  effect; the native pose already holds the body origin and scale (RenderObject's Animation translate, verified in
  the render family). The owner fields the effect reads (`+5`, `+6`, action `+0x2a`, visible `+0x38`, frame `+0xd0`,
  colour `+0x1e8`) are refreshed from the object: for 0xb5, `+0x38` is the glow flag of its rise/fall cycle, so the
  red effects draw only while it glows.
* **Destroy**: the world's close frees the objects' scene (the client clears the manager on world change,
  `0x00a7a1b4`); an expired timed record's effect is no longer updated and is hidden through its owner gate (the
  native scene keeps its slot).

The 0xb5 model is the burning ballista; bone 20 is the bolt head. Not modelled: bone −1 (the object's world matrix
`0x0129faee`), which no world-object request in these worlds uses; it is refused and counted.

The DATA-ACQ-002 capture of 136 has its five 0xb5 objects invisible with empty lists (no effects attached in that
frame), while 185 objects of types 123 and 160–166 carry non-empty lists: those come from the per-map table
`0x0183067e` (NATIVE-FX-002 §6), whose entries are not decoded. They are not part of this lane.

## 4. Native consumer

* `mu_objects_runtime.effect_word4` (new hook): the Q/R/R2 visual events (`MU_Q_KEYED_EFFECT`, `MU_WR_EFFECT_SCALED`,
  `MU_R2_EFFECT`) reach `mu_world_particles_effect` with the info block `{key −1, skill 0, word4, 0, −1}`, scale 0
  and the object as owner, instead of `draw_unsupported`. Without the hook they are still refused and counted. P's
  `0x59a/3` already went through `effect_scaled`; the pool now supports it.
* The owner view of the world-object effects carries the object's scale (`mu_jt_object.scale`, `+0xa0`).
* Models: `0x195` (123..127 from Object124, 143 from Object144) and `0x59a` (91/92 Object92, 122 Object123).
* `.ein`: the hooks `ein_listed`, `ein_valid`, `ein_attach`, `ein_update` of the objects runtime; the particle module
  owns the objects' EffectManager scene (created on the first request), the list records, and its render pass
  after the sprite section (soft and GL). Viewer choice: the client renders all manager effects in one pass after
  the world (`0x0185916b`); the native objects' scene renders at the end of the particle part, depth-tested with
  depth writes off, as the actors' scene.

## 5. Comparison and mutants

`scripts/validate_render_effects6.py --cases 200 --particle-cases 200 --mutations` (manifest row
`validate_render_effects6`):

| Family | Client routine | Cases | Mismatches |
|---|---|---:|---:|
| fx_create | CreateEffect `0x013c0f19` (0x195/0, 0x199/0, 0x199/1, 0x59a/3) | 200 | 0 |
| fx_move | MoveEffect `0x0142fd09` | 200 | 0 |
| pt_create | CreateParticle core `0x015ae7b0` (the four kinds) | 200 | 0 |
| pt_move | MoveParticles record body | 200 | 0 |
| pt_render | RenderParticles record body | 200 | 0 |

**1,000 cases, zero mismatches; 34/34 compiled mutants caught** (20 effect, 14 particle: lifetimes, spreads and
their order, light split, subtype-1 light, drifts and owner scale, the unlit flag, the 500-unit radius, swings,
pitch divisor, trail scale, climb, the skip list, the leaf's 50/150 bounds, glow colour, spark rate and owner,
particle lifetimes, colours, bounce, pulse, fade, and the 0x7efa sprite skip). Directed samples: the owner scale
(including 0, −1, NaN), start points inside and beyond 500, terrain heights at the 50/150 bounds, the flare's
75-step switch, scale/alpha zero crossings. A run at 400/400 cases: 2,000 cases, zero mismatches. The shared
harness gained the owner scale (`+0xa0`) in its object region, the record's `+0xcc`, and a render compare that
honours a record without a sprite (`sprites == 0`, which the production `mu_pt_render_all` already did).

## 6. Native evidence

`native/tests/test_native_render_effects6.py` runs `render_effects6_host` (authored 21-bone model, synthetic `.ein`
files under the four client names) through the production objects runtime and particle module, 400 steps per world:

| World (kind) | Refused before | Refused after | Effects created | Unsupported effects / particles |
|---|---:|---:|---:|---|
| 91 Acheron (0x59a/3) | 3 | 0 | 3 | 0 / 0 |
| 122 Swamp of Darkness (0x59a/3, 0x199/0) | 87 | 0 | 87 | 0 / 0 |
| 123 Kubera (0x195/0) | 5 | 0 | 5 | 0 / 0 |
| 134 Gray Aida (0x199/0) | 70 | 0 | 70 | 0 / 0 |
| 142 Twisted Karutan (0x199/0) | 7 | 0 | 7 | 0 / 0 |
| 143 Kardamahal (0x195/0) | 5 | 0 | 5 | 0 / 0 |
| 144 Swamp of Destruction (0x199/1) | 4 | 0 | 4 | 0 / 0 |
| 135 Old Kethotum (0x59a/3, forwarded; was unsupported in the pool) | — | 0 | 9 | 0 / 0 |
| 136 0xb5 `.ein`, files present | 5 (per 5 steps) | 0 | 4 attached once | updates 1,600, unposed 0 |
| 136 0xb5 `.ein`, files absent | 5 | 400 (one per step) | 0 | 1,600 invalid requests |

The host also checks each effect's owner index, the owner gate and action mirrored from the object, the scale
35 × 1.5, the bone-20 records, and that a model without bone 20 is counted instead of using a stale matrix.

Installed-data frames (local, `native/scratch/render-effects-006`, deleted): world 136 at tile (104, 70), the
ballista beside the arrival: frames 146 and 243 show the four red effects on the bolt head while it glows (6,079 and
4,872 pixels differ from the same frames with the objects' scene pass disabled), frame 39 (rest) shows none. See
the handoff for the other worlds' frames.

## 7. Limits

* `0x0129f9c6`/`0x0129f671`/`0x0129fd4f` are static readings (their record layout and matrix choice; the predicate is
  backed by the live capture); the factory's file path and the node update are NATIVE-FX-002's.
* Bone −1 (`0x0129faee`) and the per-map/Muun effect tables (`0x0183067e`, `0x0114203d`) are not implemented.
* The shoal's 1,000-step lifetime fills the 200-record pool in long sessions in 134/142/144 as the client would;
  not separately measured live.
* The `0x199` Fish02 model is not loaded in the requesting worlds (static reading of the loaders); a client that
  visited Atlans earlier in the session might still hold it (not checked live).
