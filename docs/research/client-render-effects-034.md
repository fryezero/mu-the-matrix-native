# Consumers that producers already request, RENDER-EFFECTS-034

Offline fixtures only. Base: RENDER-EFFECTS-033 `35ae89fe` plus main `bb86bbf7` (batches 119 and 120,
which bring the Muun producers of MUUN-VISUAL-005 and the item producers of RENDER-ITEMS-002AA). Target,
text and data identities are the pinned ones of `scripts/pins.py`:

- Target `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
- Text `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`.
- Data `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`.

Labels: **verified** means compared with the original instructions under Unicorn with compiled mutants;
**static** means read from the original instructions without an executed comparison.

## The table

[render-effects-034-consumers.csv](render-effects-034-consumers.csv) lists every refused consumer pair
known on this base: kind, type/subtype, original create/move/draw addresses, the producers that request
it, the lane that reported it, and refusal counts in the fixture scenes before and after.

| Status | Pairs | What |
|---|---:|---|
| Admitted, verified | 27 | 23 particle pairs and 4 joint pairs |
| Bound | 2 | sprite bitmaps `0x810d`, `0x8003` (plus the two new particle bitmaps) |
| Refused, particle | 6 | `0x8084/28` (owner bones), `0x8145/1` (combat pool bitmap row), the owner-position form `0x807e/1`, `0x807f/1`, `0x8080/1`, `0x7ffd/6` |
| Refused, joint | 7 rows | actor joints `0x7f7c/10`, `0x7f79/4`, `0x7f7c/7`, `0x7fd6/6,55,56,57`; skill joints `0x472/0x12,4`, `0x7f78/0x2f`, and the variable-subtype `0x4ae`, `0x7fde` |
| Refused, effect side | 21 rows | the 17 ids of the RENDER-EFFECTS-036 list, effect `0x454/-1,1..4` found here, the actors' type 226, `0x801d/0`, `0x413/10`, and the 34 catalogue-skill effect pairs of RENDER-EFFECTS-035 (one row) |

The table has 63 rows; some rows stand for several ids (the blur's eleven bones, the four `0x7fd6`
subtypes, the 34 catalogue effects).

Sources: the handoffs of RENDER-WORLDS-INNER-001/004/005, MUUN-VISUAL-005, RENDER-ITEMS-002AA,
RENDER-EFFECTS-032/033 and RENDER-ACTORS-006, the two CSVs that RENDER-ACTORS-008
(`actor-caller-requests.csv`) and RENDER-EFFECTS-035 (`skill-catalogue-missing-consumers.csv`) pushed on
their WIP branches during this run, the orchestrator's NEXT-GAPS-002 id list (each id
checked against those handoffs), and a new native ledger: the world particle module now records each
refused request by pair (`{"world_unsupported": [[routine, type, subtype, count], ...]}`), as the combat
module already did.

The ledger added three things the handoffs did not name:

- `0x8016/5` is refused in the **default** Swamp of Calmness view (object types 0x39/0x47): the brazier had
  no flame.
- `0x7ef7/11` is refused in the default Elbeland view (object type 0x6e).
- Twisting Slash with the installed sword model requests effect `0x454` subtypes -1, 1, 2, 3, 4 (subtype 0
  is supported). Effect side; listed for RENDER-EFFECTS-036.

Rank by requesting producers and visible effect: the two default-view particles first, then the eight
item particles (five producers, 36 to 120 refusals each in a 60-step scene), the Muun pairs (three
appearances and the mount style), the four world joints, the three tower particles (event-gated).

## Method

`CreateParticle` core `0x015ae7b0`, `MoveParticles`' record body `0x01616f7c` and `RenderParticles`'
record body `0x015912e9` dispatch on the type and then on the subtype. For each pair the original
routine was executed once per family under Unicorn with a code hook, which gives the exact instruction
path of that pair; untaken branches inside the case were then read statically. `CreateJoint`
`0x0153b02c`, `MoveJoint` `0x01556c26` and `RenderJoints` `0x01589b56` were handled the same way. The
pairs fall into five particle forms and one joint group, each written once as a table-driven consumer
(`reconstructed/particles/consumer34_kinds.inc`, `reconstructed/joints/consumer34_joints.inc`).

## Particle forms (verified)

**Plain** (the pair's own short case, the plain sprite):

| Pair | Create | Move |
|---|---|---|
| `0x8016/5` | life 20, then subtype 0's body: velocity x `(rand % 10 - 5) * 0.4`, z `(rand % 10 + 5) * 0.2`, start = position | subtype 0's body: scale - 0.02 (floor 0), velocity x/y * 0.95, z + 1, light = life / 25 |
| `0x7ef7/11` | life `rand % 10 + 130`, gravity `rand % 2 + 2`, scale `(rand % 20 + 20) / 100 * scale` | z + gravity, scale - 0.0005 |
| `0x7f5a/43` | draws Clud64 `0x7ffd`; life 40, rotation `rand % 360`, angle x 90, velocity `(rand % 20 / 10 - 1, 2, 15)` | light / 1.02, scale + 0.08 |
| `0x7f5a/47` | draws `0x7f84`; life 5, scale + `rand % 50 * 0.01`, rotation `rand % 360` | light / 1.02; life 0 when `0.05 >= light[0]`; scale + 1 |
| `0x7f54/1` | subtype 0's constructor (life 20, sound 0x40 unless scene 3) | frame `(20 - life) / 2` only: no terrain light (`0x01623b56`) |
| `0x7efa/3` | life 20, velocity `rand % 4 - 2` per axis | scale + 0.02 above life 10, else - 0.021; **no sprite**: the draw's subtype table `0x015ae4bf` sends 3 to the exit after the blend state |

**Plain, requested by the actor caller services** (RENDER-ACTORS-008's request table; six pairs that
were small and fully read):

| Pair | Create | Move |
|---|---|---|
| `0x7f26/3` | life 5 | scale * 0.8 |
| `0x7f5a/50` | life 20, scale `(rand % 32 + 32) * 0.01 * scale`, rotation `rand % 360`, gravity `(rand % 16 + 16) * 0.1`, alpha 0, colour saved, light 0 | alpha - 0.1 below life 10, else + `(rand % 3 + 2) * 0.1` up to 0.5; dies below 0.1; light = saved colour * alpha; scale + 0.02; z + gravity |
| `0x807e/0` | life 35 (25 in world 0x3f), scale `(rand % 96 + 96) * 0.01 * scale`, rotation, gravity `(rand % 16 + 12) * 0.1`, alpha 0, colour saved | the same alpha program with `rand % 5` and ceiling 0.7; scale + `(rand % 3 + 6) * 0.01`; z + gravity |
| `0x806e/0` | life `rand % 12 + 8`, velocity 0, scale `(rand % 30 + 20) * 0.01`, rotation, gravity `(rand % 15 + 15) * 0.01` | scale - `(rand % 20 + 10) * 0.001`; z + 10 * gravity |
| `0x7ef7/12` | life `rand % 10 + 100`, gravity and scale as `/11` | scale + 0.02 above life 80, else - 0.005 |
| `0x7ef7/13` | as `/12` | y - gravity, z + gravity, scale - 0.001 |

**Item** (initial lifetime/scale words +0x4c/+0x1c, alpha +0x44, the light times alpha at draw; ranges
are the client's quantised `0x011ff622`):

| Pair | Create | Move |
|---|---|---|
| `0x8616/0` | life 4, scale = argument, alpha 1 | alpha - 1 / initial life |
| `0x7fe0/10` | life 16, step = scale / life, alpha 1, rotation and three angles `range(0, 360)`, velocity z `range(1.5, 3)` | alpha - 1 / initial life, scale - step |
| `0x84d1/2` | life 30, alpha 0, step = (1.2 scale - scale) / life, rotation `range(0, 360)`, angle 0, velocity z `range(1.5, 2.5)` | alpha + 1 / half above half life, else - 1 / half; scale + step |
| `0x850b/5` | as `0x84d1/2` with life 20 and factor 2; the angle is kept | same |
| `0x807e`, `0x807f`, `0x8080` `/14` | life 20, scale `range(50, 100) * 0.01 * scale`, rotation `range(0, 360)`, alpha 1, velocity z 2.5 | alpha - 1 / half below half life; scale - initial scale / initial life |

**Follow** `0x855d/2`: the form of the existing `0x810a/0x25`. A NULL owner clears live in all three
routines. Create: life `rand % 11 + 20`, scale 0, step = scale / (life / 2), alpha 1, rotation
`range(0, 360)`, start = position. Move: scale + step above half life, else - step; alpha - 1 / initial
life. Draw `0x015aa801`: the position becomes OBJECT `+0x1f4 + 12 * arg8` plus the record's start, then
the item sprite. The native side supplies the retained item-owner point, as for the existing follow kinds.

**Pulse** `0x8081/1`, `0x8082/1` (life 5) and `0x7ef7/19` (life 7): create saves the argument colour in
+0x7c..+0x84 and zeroes the light; peak scale = `scale - scale / 10 * (rand % 5)`, rotation `rand % 360`.
Move: with `span = life0 - life0 / 2` and `t = (life0 - life) / span` above half life, else `life / span`:
alpha `0.9 t + 0.1`, scale `(0.5 t + 0.5) * peak scale`, live 0 when alpha < 0.1, light = saved colour *
alpha.

## Joints (verified)

| Pair | Create | Move |
|---|---|---|
| `0x7f7c/8` | width 5, velocity `rand % 10 + 6`, life `rand % 8 + 8`, two tails, white | no case (`0x0156d3a9`): the head's forward motion and the closing tail only |
| `0x7f7c/19` | the type's head (width = argument), 30 tails, life 2, velocity 3 * width, start = position | `/18`'s tail loop `0x0156d9ef` with a turn of width + 25 (`0x0156e071`) and an angle jitter `(rand % 1024 - 512) / width` on all three axes (`0x0156eba0`); no arrival branch and **no terrain light** (`0x0156f2ba`) |
| `0x7fd5/4` | width `2 * scale + 4`, velocity `rand % 5 + 4`, life `rand % 10 + 8`, four tails, colour (1, 0.2, 0.2) | velocity + 0.1; light[0] / 1.1 copied to the other two |
| `0x7f7d/11` | width = argument, draws `0x7f7c`, velocity `rand % 20 + 80`, blue + 0.2, life 5, 30 tails, target = argument | a straight run of `tails - 5` steps of `R(angle)(0, width / 1.3, 0)` fixes the far end; the drawn bolt repeats it with a jitter of `rand % 2a - a`, `a = (int)(width / 8)`, per axis, and ends at the far end |

`0x7f7d/11` divides by `2a`: a width below 8 faults in the client. The producers pass 15 times the
object scale. The native consumer's modulo helper returns 0 for a zero divisor; that domain is outside the
comparison.

## Bitmap bindings

The world table grows 100 to 104 entries, inserted before Fire03 so the later anchors stay:
`0x8616` Effect/FireSphere1 (`LoadBitmap` `0x01826fc9`), `0x850b` Item/texture/smoke_line03_1
(`0x01827bc3`), `0x810d` Effect/pin_star02_yellow (`0x0182e29f`), `0x8003` Effect/Hole (`0x01822a25`); all
LINEAR/CLAMP, as the startup table in `native/core/mu_item_bitmaps.inc` records. All four files, and
every bitmap the new pairs draw, load from the read-only game data; none is missing, and no Native Data
refresh is involved.

## Pairs that stay refused

- **`0x8084/28`** (Muun appearance 375). Static: create `0x015d68df` sets life = (int) `range(3, 7)`,
  scale `range(0.15, 0.3)`, rotation, alpha 0.1, the owner word and the saved colour. Move `0x01649d2c`
  reads the owner OBJECT's bone matrices 11 and 18 through `0x0129f12c` and `TransformPosition`
  `0x012b6ef1` and places the particle between them before the alpha/scale program. The native Muun
  request carries no owner and the particle host has no owner-bone service; both belong to the Muun lane.
  270 refusals in the 90-step scene, unchanged.
- **`0x8145/1`** (Blood Storm body). Static form: life 14, scale 0 then + 0.2 per step, alpha - 0.0714,
  light = saved colour * alpha, plain sprite. The combat pool has no bitmap row for `0x8145`, and
  `native/core/mu_combat.c` belongs to RENDER-EFFECTS-035. Left with the Blood Storm rest.
- **Owner-position form** `0x807e/1`, `0x807f/1`, `0x8080/1` (create `0x015ce0d7`, move `0x01640ddf`)
  and `0x7ffd/6` (`0x015c0fcd`, `0x0162f448`). Static: both read the owner OBJECT's position +0x158
  directly in create and move and carry the particle with the owner (position - start, start = owner
  position, position + start), with scale and alpha branches that were not all read. Requested only by
  actor callers that are not on main; left as one form for the next consumer lane.
- **Joints** from the two late CSVs: actor joints `0x7f7c/10` (72 request rows), `0x7f79/4`, `0x7f7c/7`,
  `0x7fd6/6,55,56,57`; skill joints `0x472/0x12`, `0x472/4`, `0x7f78/0x2f`; `0x4ae` and `0x7fde` have a
  variable subtype in the request and are not statically complete. None was traced here.
- **Effect side** (RENDER-EFFECTS-036): Blood Storm `0x585/0`, `0x586/0`, `0x4b7/1`, blur `0x814b`;
  Crescent `0x49e/0`; Fire Breath `0x8001/0`; the ten tower effects `0x4be/0`, `0x4bf/0`, `0x419/2`,
  `0x41a/2`, `0x4c0/0`, `0x4c1/0`, `0x4c2/0`, `0x4c5/0x4c0`, `0x4c5/0x4c1`, `0x4c5/0x4c2`; effect `0x454`
  subtypes -1, 1, 2, 3, 4; the actors' type 226. Effect consumers live in `reconstructed/combat`, which
  RENDER-EFFECTS-035 owns during this run.

## Verification

`scripts/validate_render_effects34.py` is one grouped, table-driven comparison: per pair, create, move
and draw against the original instructions (record fields, ordered calls, `rand()` counts, draw calls;
the follow pair also compares the owner-point position write of the draw), the joint families of
`validate_joints.py`, a native host (`native/tests/effects34_host.c`: pool admission, bitmap routing,
the item-owner point, raster output, retirement, the refusal ledger) and an admission census. At 200
cases per pair: **16,259 checks, 0 mismatches**, no original-machine stop. **116 compiled mutants** (three
per pair plus form and native controls), all detected.

The comparison covers the stated instruction slices and the native adapter contracts. It does not claim
original GPU pixels, the client's shared RNG phase, pool equivalence, or which requests a live session
would issue.
