# Rageful Blow, Triple Shot's fan and the Guardian wing

RENDER-EFFECTS-004 implements Rageful Blow's complete ordinary-world effect chain,
Triple Shot's arrow fan through the original CreateArrows/CreateArrow, and one pet
cosmetic consumer (Spirit of Guardian's wing). Native primary routes rise **18/23 to
20/23**; weighted primary coverage **56/77 to 65/77**.
[Inventory](client-skill-visual-coverage.md), [handoff](../handoffs/RENDER-EFFECTS-004.md).

## Identity and method

Same pinned target as client-render-effects-003.md: executable SHA-256
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`, capture09 text
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` at 0x00401000, run10
image data `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`.

Verified means authored compiled C compared with the original instructions under
Unicorn (`scripts/validate_render_effects4.py`), a fresh strict machine per family and
mutant, declared input regions and defined-byte masks. Record fields, ordered calls with
their arguments, the CreateEffect info key, RNG counts, the hero skill serial and the
restored object angle are compared. Terrain height, TerrainWall words, rand, sine/sqrt,
CreateEffect/Particle/Joint, PlayBuffer, the animation player, RequestTerrainLight, the
model pose, RenderPartObject and the skill-tree/item-option lookups are recorded services
with authored answers. The special-world predicate `0x009b0418` answers false (ordinary
worlds). No live game, capture, decoded table or client bytes are published.

| Family | Original bodies | Cases | Mismatches |
|---|---|---:|---:|
| CreateEffect, 16 kinds | 0x461 `0x013ce830`; 0x462..0x469 `0x013cea0a..0x013cec41`; 0x46a/0x46b `0x013c94a8`/`0x013c956a`; 0x460/4 `0x013e4f6f` | 16,000 | 0 |
| MoveEffect | 0x461 `0x01450a73..0x0145240b`; pieces `0x01452410..0x01453033`; 0x46a/0x46b `0x0144e1d7`/`0x0144e3d9`; 0x460/4 `0x0146b64c` | 10,000 | 0 |
| Item object initialiser | `0x016da00b`, 55 model types incl. every switch case | 1,000 | 0 |
| Weapon draw | RenderEffects `0x01532bd2` | 1,000 | 0 |
| CreateArrows | `0x0158d5bd`, 1/3/4/5-shot fans | 2,000 | 0 |
| CreateArrow | `0x0158cf57`, both bow tables, 0x49d and 0x6a9 shots | 2,000 | 0 |

Total **32,000** original-instruction comparisons, zero mismatches. Body SHA-256 prefixes
(local report): create `87f7c7de`, 0x461 move `9d117407`, pieces `f1edfd57`, wing
create/move `1536fc28`/`eb1ae1b9`, CreateArrows `538f7c27`, CreateArrow `6ae1ebac`,
initialiser `40de3442`, weapon draw `81153058`.

## Recovered behavior

**Caller.** MoveCharacter's area switch `0x013a94a4` stores the weapon (`+0x56`) and its
level (`+0x41`), creates 0x461 at the caster with the caster's angle and light, owner the
caster, key `+0x54`, then plays 0x95. The loader `0x0183451b..0x018345cf` maps 0x462..0x469
to `Data\Skill\EarthQuake01..08.bmd`, 0x46a to `flashing.bmd`, 0x46b to `tail.bmd`. 0x461 has
no model.

**0x461, the flying weapon.** Creation copies the angle to a second vector `+0x170`
(+80/+0/+180), the position to the impact point `+0x110`, sets lifetime 20, a random
subtype `rand()%100`, angle z +330, gravity 50, and takes and steps the hero skill serial.
Steps 20..12 hop over the impact point: `w = (20-t)*s` with t/s = 12.5/18 for lifetimes 10..15
(gravity flips at 15), else lifetime/15; direction y = `sin(w*3.141592/180)*260` (the
double constant is `0x400921fafc8b007a`, not π), position = impact + rotate(direction,
`+0x170`) + gravity + 200, gravity ±8 (minus only at exactly 12.5); angle x +80. At 13
(own hit test 0) eight `tail` pieces fall in two columns. At lifetime 11 (5 for skill 0x7fb)
the impact moves 25 forward/80 back along the owner's angle, sits 25 above the terrain,
emits Explosion01 (scale 0.5), eight 0x7fd5 joints and one Spark02, `flashing`, then (unless
the owner type is 0x804/0x962) EarthQuake03/01/02 owned by the weapon itself, and five
EarthQuake04/05 pairs at 72° steps, skipped when the TerrainWall word has bit 4, 8 or 0x10.
At 10 (4) four rings of five EarthQuake07/08 spread with random alternating turns, skipped
only when all three wall bits are set; lifetime becomes 0 and 0x97 plays. 0x461 skips the
generic animation and motion. Children scale by their info key / 100 (150, or
`rand()%50+40`, or 100). EarthQuake01 shakes the camera (`0x0bdb588c`); 02/05 drop stones
0x419/0x41a; 02/05/08 add a red terrain light (blue for owner type 0x804). `flashing` grows and
darkens the ground; `tail` falls faster each step.

**Weapon draw.** From step 11 on (not for skills 0x7f8/0x7fb or an own-hit arrow), RenderEffects
`0x01532bd2` draws the owner's weapon model (`+0x56 + 0xae6`) at the record: it temporarily sets
the record type to the item, runs the item object initialiser `0x016da00b` (light 0.3, scale 0.8
or the per-model preset, blend/UV presets from WorldTime or rand), restores gravity and type, and
lights the model with RequestTerrainLight + 0.3. The reinitialisation persists: impact pieces
created after the first drawn frame take light 0.3.

**Triple Shot.** End-of-attack case 0x18 (`0x013af9db`) calls CreateArrows(character, object,
0, skill, 1, 0). With an ordinary bow and no master skill 0x1a2 it fires three CreateArrow
shots at the object's angle +0°, +15°, −15° (the previous native viewer choice was −8/0/+8),
restores the angle and steps the hero serial once. Master/special-bow branches fire four
(+5, +15, −5, −15) or five shots; skills 0x7fc/0x7ff scale an 8/24 step. CreateArrow places the
shot on the terrain, picks the arrow model from two bow tables (bow 0x12e6 → Arrow01 0x43b,
crossbows 0x12ee/0x12ef → 0x43c, ...), and passes key/skill/flag/field8/tree value in the info
block; flag 1 makes the arrow test its own hits.

**Spirit of Guardian's wing.** The pet emits CreateEffect(0x460, subtype 4, scale 0.3, key −1)
each drawn frame. Creation scatters the position ±40, sets the direction to the normalised
pull back (`0x00cff0d3`), a truncated jitter that is zero in practice, scale ±30 %, lifetime 25,
alpha 0.3, gravity 0.1, random angles and a per-step spin `+0x194`. Each step fades light and
alpha by 0.97 and turns by the spin; the generic motion moves it. Model
`Data\Skill\darkwing_hetachi.bmd` (AccessModel `0x0183375e`).

## Compiled planted mistakes

Each mutant edits production C, compiles a separate library and runs the same comparator,
200 cases each: lifetime 21 (200), impact depth 26 (24), ring step 70° (13), quake wall gate
"any" (12), hop height 190 (150), EarthQuake03 sink at 12 (13), red light 0.5 (104), tail
gravity 50 (200), flashing scale 0.6 (200), wing fade 0.96 (200), wing drift ×3 (200),
Triple Shot ±8 (17), bow 0x12e8 → 0x43b (5), item scale 0.9 (110), weapon level << 2 (32).
**15/15 caught.**

## Native integration

`mu_combat` casts 42 through the verified chain, loads the nine piece models once, and draws
the flying weapon with the existing weapon model. Piece effects owned by the weapon read only
its type for the red light; natively the weapon's owner stands in. TerrainWall reads outside
the 256×256 grid answer open. Triple Shot uses CreateArrows/CreateArrow with the services the
session lacks answered as "no master-tree skill, no item option 0x54, tree value 0". The pet
host forwards the CreateEffect scale and key; the wing model loads once in the shared effect
pool. No per-frame allocation is added.

Fixture tests: Rageful Blow creates all ten types, twenty quake pieces per ring, eight joints,
zero unsupported emissions or invented damage, one unsent request; removing the piece models
changes pixels. Triple Shot creates three Arrow01 effects. The wing creates one effect per
drawn frame, keeps 25 live, and removing its model changes pixels. Installed-data GL frames were
inspected for all three (impact, quake ring, arrow fan, wing). Fire Ball and Twisting Slash
software frames at frame 21 are byte-identical before and after.

## Limits

- Ordinary worlds only: the special-world branches (`0x00deeb13` flat grid write, +100
  offsets) are not taken.
- The weapon draw's RenderPartObject level glow and head-angle use are drawn by the existing
  native weapon model path without the item-level overlay.
- Other bows' arrow models (0x43c..0x617) have no reconstructed create/move; those shots count as
  unsupported. Bow 0x12f9's fifteen bone sparks after the fan are not reconstructed. Master
  tree (0x1a2), skill-tree value, mastery and item option 0x54 come from authored state.
- Rudolph's 0x3fa (shared 0x3f4..0x3fa body `0x013de0ff`) and the pets' particle kinds remain
  undrawn; see client-pets.md.
- No live original-client image or session equivalence.
