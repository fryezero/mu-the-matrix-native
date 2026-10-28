# RENDER-ITEMS-002 part 11

Base `fa63719`, branch/worktree `claude/render-items-002k` (Claude Opus 5.5). Checkpoints
`8d98896` and `c083322` are pushed. Only this lane is edited and built. No live client, launcher or
hosted workflow is used.

## Coverage and implementation

Bounded bodies increase **880 to 967 of 1,674**, adding **87 types**: 41 weapon, 22 armour
and 24 survey `pet/item`. All **17/17 skins** remain. Links stay at **seventeen targets/twenty-two
types**. The survey has **293 complete shapes**, up from 228. Exact membership is in
`gen_item_bodies.SCALAR_TYPES` and both TSVs. Original shape identities, ranks, service sites and
stopped observations are preserved. **707 bodies remain.**

The largest group of refusals was not a shape cluster but one mechanism. 377 of the 751 remaining
non-stopping types draw only generic helper calls, yet one draw word (mostly mesh blend light or
body light) matches no shared input. That word is straight-line SSE code after the wave helper
`0x0185bdc4(a, 0)` or the sin wrapper `0x009681bd(time*k)`, with per-type constants. Earlier parts
hard-coded single instances (the -4/-1/-6 waves, `sin(time*0.0015)`).

The generator now records the return sites of both calls hit by its probes and parses each one
from the pinned bytes. It accepts the exact argument loads, `fstp`/reload of one local, then up to
four `mulss/addss/subss/divss` constants, or the binary64 `addsd/mulsd .. cvtsd2ss` form. Constants
come from the pinned data image. Only the zero phase argument is accepted: its term adds a signed
zero to the clock and cannot change the truncated tick. A type that fails the shared inputs is
probed again with its parsed programs as extra inputs; only used programs are kept.
`item_bodies.h` gains 89 programs and `scalar_first/scalar_count` per row. Recipe sources 36..
select them. `renderchar.c` evaluates them in `body_scalar`, using a generic `client_wave` next
to the existing `client_sin`. This is the only renderchar.c change and it sits inside the body
executor. All 897 earlier rows keep identical recipes and flags; their new columns are zero.

Screening: 176 types fit the probes (67 shared-input fits, 109 with programs). Independent
292-state full-function comparisons rejected 89. These are all 67 shared-input fits (earlier
refusals stay refused) and 22 program fits that differ outside the probes: 62 body light,
12 draw words, 11 draw counts and 4 bodies that consume the random stream. Only the 87 that
pass are admitted.

## Checks

The executable/text/data identities in the [finding](../research/client-render-items.md#part-11-per-type-wave-and-sine-scalar-bodies-render-items-002k)
apply unchanged. `scripts/validate_item_scalars.py --mutations` has a manifest row and the private
test `ItemScalars.test_original_instructions`. **26,154 comparisons, zero mismatches**:

| Family | Cases | Mismatches |
|---|---:|---:|
| Full body streams, 87 types times 292 states, body random trapped | 25,404 | 0 |
| Period edges, INT_MIN, -0.0 and 2^31 for one type per distinct program (25), flags 2/0x40042 | 750 | 0 |

All **11/11 separately compiled mutants** are caught: wave period 14,169; wave sign 14,960; wave
scale 7,631; sine argument 11,090; single multiply 24,282; single add 25,510; binary64 form 322;
scalar slot 610; scalar count 26,154; mesh index 24,634; object alpha 15,200. The body table
reproduces from the pinned instructions.

The inherited part-10 validator passes on the final source: **33,622 cases, zero mismatches,
12/12 compiled mutants**, with identical detection counts, and both generated tables reproduce.
Together the two runs give **59,776 instruction comparisons, zero mismatches and 23/23 mutants**.

Compiled C-to-C checks of the base `fa63719` library against this one cover all **897 earlier
body/skin types in 28,704 random cases, zero mismatches**. Over all 1,691 survey types, admission
changes only for the 87 new types. All 1,691 survey memberships agree with compiled admission.
Portable `test_item_scalars.py`: three tests, one private skip. It checks admission and refusal
outside the domain, and that every program reaches a draw word for six clocks.

## Native gallery

The real native inventory renderer (`mu-render ui inventory`) used installed geometry and textures,
codes 28, 2711, 4305, 4398, 7333 and 3103. The debug listing shows model = code + 0xae6 for all six
(0xb02, 0x157d, 0x1bb7, 0x1c14, 0x278b, 0x1705), all drawn and none missing. The before
binary uses the `fa63719` item sources with the same surrounding renderer. Triangles increase
**2,869 to 3,432** and **1,656 of 1,804,656 pixels** change (armour glow, pet item and blade
highlight). The framebuffer SHA-256 is `1300f276…5bf1` before and `21ed1ac2…bdac` after. The
ordinary control (codes 0,1,2,3,7,8, 162 triangles) is byte-identical, framebuffer SHA-256
`df03a29015909de199d353d327efd2b852f79f813bd5260d0358622313b14930`. Two small crops were inspected.
These are offline native renders, not original-client pixel comparisons.

## Limits and coordination

**707 bodies** remain. The other program-like refusals need their own forms: integer UV clocks
`-(tick % N)/N`, atlas frames with other periods and columns, locals written in other branches,
level-dependent draw counts (72 shapes), immediate `glColor` calls and body-owned
effects/particles. No new link target was added. Laser/17 and the shared clock/bone-state links stay
partial, and no further RenderLinkItem target was surveyed in this part. Rank-5 owner bones 35/26,
0x84e2/0x83de particles, 0x7fdd sprites and level-9 overlays belong to RENDER-EFFECTS-004. No
runtime/viewer hook, effect consumer, perf/mesh/scene or session code changed. Muun and nested
map-object tables remain deferred, as do the earlier record, buff, selection, shadow, override,
NewUI and Box of Luck limits.

## Stable preflight

With the source frozen, `bash scripts/local-macos-ci.sh` on the `fa63719` base passes **1,633 tests
across 38 suites, 209 explicit skips, zero failures**. All **11/11 fixture scenarios** pass, with 86
inbound frames and zero unbound or undecodable frames. The existing two unrecovered intents and
nine unsent frames stay explicit. Viewer and readers build. The publication audit accepts **1,588
staged files, zero rejected**. Portable renderchar: **59 tests, fourteen private skips**. Native
character renderer: **13 tests, one installed-client skip**.

GATE_PLACEHOLDER
