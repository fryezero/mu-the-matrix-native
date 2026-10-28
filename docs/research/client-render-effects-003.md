# Priority skill visuals and coordinated world particles

RENDER-EFFECTS-003 implements Meteorite, Aqua Beam's primary sprite chain and
Inferno's ring bursts. It also supplies five particle consumers requested by
RENDER-WORLDS-K. Native cast-route primary coverage rises 15/23 to 18/23, weighted
46/77 to 56/77. [Inventory and class exposure](client-skill-visual-coverage.md).
Rageful Blow and the later buff/arrow/class groups remain open.

## Identity and method

Same owner-client target as client-combat.md, executable SHA-256
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
Capture09 text at 0x00401000 is
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`;
run10 image data at 0x01a7c000 is
`c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`.

Verified means authored compiled C compared with the original instructions in
Unicorn. Each family and mutant uses a fresh strict machine, declared input
regions and defined-byte masks. Host libm, terrain height, model/animation,
audio and nested creators are recorded services. Render comparisons check sprite
calls, order, blend/UV arguments and record fields, not the original GPU.
No new client capture, live game, decoded table or client bytes are published.
The focused scripts hash their selected instruction bodies in local reports.

| Family | Original entries / selected bodies | Cases | Mismatches |
|---|---|---:|---:|
| Skill effect create, Meteorite and Aqua | 0x013c0f19; 0x013d2f05 and 0x013c6a04 | 2,000 | 0 |
| Skill effect move | 0x0142fd09; Meteorite contact 0x0146c821 | 2,000 | 0 |
| Inferno subtype-0 burst | 0x013c07f4 | 1,000 | 0 |
| Aqua primary render body | 0x01519c06..0x0151a401 | 1,000 | 0 |
| Spark02/2 and Explosion01/0 create | 0x015ae7b0; 0x015dc299 and 0x015e42eb | 2,000 | 0 |
| Spark/explosion move | 0x01616c80 record body | 1,277 instruction + 723 native head-removal | 0 |
| Spark/explosion render | 0x0159123f record body | 2,000 | 0 |
| World consumers create | flare 0x015eec34; smoke 0x015c4c7b, 0x015c639e, 0x015c657d, 0x015c66df | 5,000 | 0 |
| World consumers move | flare 0x01662886; smoke 0x01635535..0x0163605e | 3,176 instruction + 1,824 native head-removal | 0 |
| World consumers render | 0x0159123f record body | 5,000 | 0 |

Total 24,453 original-instruction comparisons plus 2,547 native head-removal
checks, zero mismatches. Expired-at-head particles do not enter the original
record body and are not counted as instruction comparisons.

## Recovered behavior

Meteorite uses Fire01 subtype 0, lifetime 40, random scale, x offset 130..161,
z +400, fall direction z -50 and angle y 20. Terrain contact precedes generic
movement, clears direction, emits six random Stone01/02 models plus an explosion
80 units up, then kills the effect. Unlike Fire Ball, it has no target hit check.
This is the ordinary-world terrain path; the special-world +30 terrain offset
remains open. The blend brightness consumes an extra random number. Adding the original zero
to terrain height preserves signed-zero call arguments.

Aqua Beam uses lifetime 20, scale 16, color 0.5/0.7/1 and rotated direction
0/-50/0. Its primary RenderEffects body emits twenty Spark03 sprites, advancing
by direction after each sprite and emitting terrain light at the following point.
The native frame-light hook prepares these fixed-pool sprites before the sprite
pass. The caller offset -20/-90/100 is a static reading of 0x013ac8a2 and
0x013a08e0. Only ordinary-world subtype 0 is reconstructed here. The hero-only
area request and source-position writeback in 0x013c6e62 are excluded; the native
fixture already journals one encrypted cast request as unsent. Special-world
wall cutoffs, subtypes 1..4 and whole-character-loop equivalence remain open.

Inferno's eight-point ring now calls the subtype-0 burst at each point. A burst
emits twenty Spark02/2 particles with randomized pitch and roll, then one gray
Explosion01/0 when visible. Spark02/2 doubles scale and triples velocity before
rotation. Explosion01 lives 20 steps, selects a 4x4 UV cell every two steps and
adds terrain light. Its original sound call is recorded in the oracle and
counted by the native particle adapter. Actual sound delivery remains AUDIO-002D.
The original ring placement/caller is a static adapter, not a whole-loop oracle.

K's consumer additions are flare01 0x7ef7/0 and smoke01 0x7f5a/4/6/7/8. Flare
uses list wind, randomized drift, rise, scale fade and a live/lifetime cutoff.
The client drift constant is 0x39d1b718, one ULP above decimal 0.0004f; using the
usual literal caused five differences in a 5,000-case mixed move probe. Smoke/6
refreshes lifetime to 10, oscillates at its saved height and renders with zero
rotation. Smoke/4 tints the rising smoke; /7 falls and fades; /8 expands, damps
velocity and halves light near expiry. The native list forwards the updated x/y
wind after its wind step and uses zero for its otherwise absent z wind state.
Direct record comparisons vary all three wind inputs. World producers remain
owned and tested by RENDER-WORLDS-K; this change does not claim their placement.

## K sprite registrations

Three additional LoadBitmap calls executed under Unicorn with the pinned
path pointers and all six arguments recorded. Each matches filter GL_LINEAR
0x2601, wrap GL_CLAMP 0x2900 and final flags 1,0.

| Bitmap | Call | Original path | Pointer |
|---|---|---|---|
| 0x7f84 | 0x01821599 | Effect\Magic_Ground2.jpg | 0x01af16d0 |
| 0x7f38 | 0x01822345 | Effect\lightning3.jpg | 0x01af29dc |
| 0x8021 | 0x01821f65 | Effect\Impack03.jpg | 0x01af26a0 |

The native asset list resolves these to the installed OZJ files and retains
LINEAR/CLAMP metadata. A synthetic production-host test creates all five particle
subtypes and these three sprites, moves and draws them through native dispatch,
asserts eight quads and checks actual loaded sampling metadata. K owns the world
producer calls and their own comparisons. These three registration checks are
additional to the 24,453 instruction cases above.

## Compiled planted mistakes

Every mutant changes production C, compiles a separate library and runs the same
original-instruction comparator, 200 cases per mutant.

| Mutant | Disagreements |
|---|---:|
| Aqua speed -40 | 200 |
| Aqua chain 19 sprites | 200 |
| Meteorite lifetime 39 | 200 |
| Meteorite fall -40 | 200 |
| Meteorite five stones | 99 |
| Inferno 19 sparks | 200 |
| Inferno burst height 70 | 200 |
| Spark02/2 speed multiplier 2 | 200 |
| Explosion frame divisor 3 | 107 |
| Explosion missing UV inset | 169 |
| Flare lifetime one shorter | 200 |
| Flare ignores wind | 122 |
| Smoke/4 red tint 100 | 122 |
| Smoke/6 refresh 9 | 122 |
| Smoke/6 rotation 1 | 169 |
| Smoke/7 speed one lower | 200 |
| Smoke/8 scale 0.7 | 200 |

## Integration, regression and release

The fixture-session native tests assert one unsent encrypted request, zero
unsupported emissions, zero invented hits/kills, unchanged target HP, expected
effect types and changed pixels when models/particles are removed. Poison,
Ice/debris and Power Wave remain in the same regression. All pools are fixed
capacity; new bitmaps load once, including Explosion01 and the three K-requested sprites. There are no new
per-frame allocations or perf/mesh/scene changes.

Release commands, gate counts and representative image hashes are recorded in
[the handoff](../handoffs/RENDER-EFFECTS-003.md). No existing hash pin is changed.
Pixels, RNG consumption and terrain lights for the newly supported skill/world
subtypes intentionally change. The historical particle kind order is preserved;
the pre-existing mount-breath rounding difference remains unchanged and outside
this milestone's zero-mismatch claim.

## Remaining priority work

Rageful Blow's 0x461 creation and tail fragments are insufficient for its primary
impact. Static MoveEffect 0x01450a73 sets lifetime thresholds 11 and 10; those
branches emit 0x463..0x469 with terrain and owner services. Its owner-weapon draw
is 0x01532bd2. None of that partial port is retained or given coverage credit.
Next reconstruct those complete create/move families and renderer, then buff
auras, arrow/Death Stab trails and master/later-class session selectors. No live
original-client image or session equivalence is established here.
