# Skill visual coverage, RENDER-EFFECTS-004

This is a reviewed coverage summary, not an export of Skill(Kor). RENDER-EFFECTS-004 starts from
main `147005d` (EFFECTS-003 #230 included). The original baseline is
main `cf81357`, including RENDER-EFFECTS-002 #221, SESSION-COMBAT-001 #197 and SESSION-SKILL-001 #204.
The scope is the player cast's primary visible result, its particles/joints and its
session adapter. A working icon, sound, animation or CreateEffect call alone does
not establish a rendered spell. Damage policy and encrypted request delivery are
outside this rendering milestone.

## Sources and confidence

- **Verified**: the new C create/move cases and smoke particle create/move/render
  compare with original capture09 instructions under Unicorn. See section below.
- **Static**: caller selection in MoveCharacter, model-loader names and the existing
  RenderObject adapter. Their instruction addresses are recorded below; no claim
  of whole-character-loop or live-image equivalence follows.
- **Snapshot summary**: the existing `skill3/lang` plaintexts, produced by the
  documented langread process, contain 973 skill records and sixteen class maps.
  Level and class eligibility below summarize those local inputs. Level zero means
  the table imposes no level, not that weapon, quest or other requirements vanish.
- **Priority inference**: weights 1..5 estimate repeated visual exposure in ordinary
  play: 5 sustained farming/basic attacks, 4 recurring combat/support, 3 early
  progression or broad multi-class reuse, 2 transitional/specialized, 1 rare.
  They are engineering priorities, not measured player telemetry. Exact unlock and
  use still depend on the live server and the usability checks in client-skills.md.

## Audited native cast routes

P = primary visual implemented; L = limited visual, specific gaps remain;
M = primary visual missing. The 23 rows are exactly `mu_skill_visual_at`'s native
routes, including normal attack. They are not all 973 table records. "P" includes
intentional animation-only weapon skills, but does not certify every buff or
master upgrade variant. Class indices follow client-character-select.md. DW = 0,
DK = 1, Elf = 2, MG = 3, DL = 4, Summoner = 5, RF = 6, GL = 7, RW = 8,
Slayer = 9, Gun Crusher = 10, Light Wizard = 11, Mage = 12, Illusion Knight = 13,
Alchemist = 14, Crusader = 15.

| Skill / primary visual | Eligible classes | Table level / use | Weight | Before (003) | After (004) | Rendered result or remaining gap |
|---|---|---|---:|---|---|---|
| 0 normal attack | All, weapon-dependent | All levels | 5 | P | P | Weapon actions; bow arrow model and trail |
| 1 Poison | DW, MG, RW, Mage, Alchemist | 30, early spell | 3 | P | P | Ten smoke01/1 particles at target; model 0x414 belongs to a monster branch |
| 2 Meteorite | DW, MG, Summoner, RW, Mage, Alchemist | 21, early spell | 3 | P | P | Falling Fire01/0, six impact stones, Explosion01/0 |
| 4 Fire Ball | DW, MG, Summoner, RW, Mage, Alchemist | 5, early spell | 3 | P | P | Fire01/1, fire trail and impact stones |
| 7 Ice | DW, MG, Summoner, Light Wizard, Mage, Alchemist | 25, early/control | 3 | P | P | Ice01 and five Ice02 debris models, smoke and negative terrain light |
| 9 Evil Spirit | DW, MG, RW | 50, repeated area farming | 5 | P | P | Eight spirit ribbons, wide-spirit Laser01 and terrain light |
| 10 Hellfire | DW, MG, RW, Mage, Alchemist | 60, area spell | 2 | P | P | Circle01/02, fire and stones |
| 11 Power Wave | DW, MG, Summoner, Light Wizard, Mage, Alchemist | 9, early spell | 3 | P | P | One Magic02 model and four smoke01/3 particles per step |
| 12 Aqua Beam | DW, MG, Light Wizard, Alchemist | 74, directional spell | 3 | P | P | Ordinary-world 20-sprite Spark03 beam and terrain-light chain; hero area requests remain separate |
| 14 Inferno | DW, MG, RW, Mage, Alchemist | 88, recurring area spell | 4 | P | P | Inferno01, ring stones, eight bursts of 20 Spark02/2 particles plus Explosion01/0 |
| 17 Energy Ball | DW | 2, starting spell | 3 | P | P | Thunder01 and Spark03 particles |
| 19 Falling Slash | DK, MG, DL, RF, Crusader | 0, weapon skill | 2 | P | P | Weapon action 0x89; no separate model at audited end site |
| 20 Lunge | DK, MG, DL, GL, Slayer | 0, weapon skill | 2 | P | P | Weapon action 0x8a |
| 21 Uppercut | DK, MG, DL, Slayer | 0, weapon skill | 2 | P | P | Weapon action 0x8b |
| 22 Cyclone | DK, MG, DL, Slayer, Illusion Knight | 0, weapon skill | 2 | P | P | Weapon action 0x8c |
| 23 Slash | DK, MG | 0, weapon skill | 2 | P | P | Weapon action 0x8d |
| 24 Triple Shot | Elf | 0, recurring ranged farming | 5 | L | P | Verified CreateArrows fan (0, +15, -15) and CreateArrow bow table; other bows' arrow models remain |
| 26 Heal | Elf | 8, recurring support | 4 | P | P | Target ground effect, three energy ribbons and arrival sprite |
| 27 Greater Defense | Elf | 13, recurring support | 4 | L | L | Cast animation/sound; persistent buff aura/authoritative buff feed absent |
| 28 Greater Damage | Elf | 18, recurring support | 4 | L | L | Cast animation/sound; persistent buff aura/authoritative buff feed absent |
| 41 Twisting Slash | DK, MG, Slayer, Crusader | 0, repeated melee farming | 5 | P | P | Weapon swirl, smoke, sparks, joint streaks |
| 42 Rageful Blow | DK, Slayer, Crusader | 170, later melee farming | 4 | M | P | Flying weapon 0x461, EarthQuake01..08/flashing/tail impact, quake rings, eight joints; ordinary worlds |
| 43 Death Stab | DK | 160, later melee combat | 4 | L | L | Action 0x9e; associated skill-step trails remain unaudited |

Totals: **18 P / 4 L / 1 M before; 20 P / 3 L / 0 M after**, out of 23
routes. Strict primary coverage rises from 78.3% to 87.0%. Primary-covered
priority weight rises from **56/77 to 65/77**, or 72.7% to 84.4%. Limited rows
receive no primary-coverage credit. These percentages do not apply to all client
skills, variants, monsters, gear effects or worlds. Earlier milestones moved
12/23 and 37/77 (#221) and 15/23 and 46/77 (EFFECTS-003 baseline) to 18/23 and 56/77.

## Other client skill groups and class exposure

The snapshot has many upgrades, passives, item/event skills and shared base
skills. Counting all 973 as independent casts would inflate the denominator.
This table reports candidate records with brand 0 and use type 0/4/7/8/14, and
class-map value > 0. It is a static workload inventory, not a claim that every
candidate casts, is learned, or has a unique effect. Classes overlap.

| Class | Candidate records | Audited primary records before / after (004) | Highest-priority remaining visuals |
|---|---:|---:|---|
| DW | 69 | 10 / 10 | Later area spells |
| DK | 63 | 6 / 7 | Death Stab trails, later combos |
| Elf | 73 | 1 / 2 | Buff auras, other bows' arrow models, later bow area skills |
| MG | 79 | 15 / 15 | Later blade/spell families |
| DL | 64 | 4 / 4 | Command/fire-chain and raven-specific combat visuals |
| Summoner | 64 | 4 / 4 | Summon/drain/lightning and later class spells |
| RF | 58 | 1 / 1 | Fist/charge/area families |
| GL | 57 | 1 / 1 | Lance/charge/area families |
| RW | 68 | 6 / 6 | Rune-specific area spells |
| Slayer | 54 | 4 / 5 | Class trails |
| Gun Crusher | 50 | 0 / 0 | Gun/projectile/area families |
| Light Wizard | 60 | 3 / 3 | Class-specific light spells |
| Mage | 68 | 7 / 7 | Class-specific spells |
| Illusion Knight | 43 | 1 / 1 | Illusion/weapon-copy families |
| Alchemist | 67 | 8 / 8 | Alchemy families |
| Crusader | 54 | 2 / 3 | Holy/charge families |

These remaining class families have **missing session visual selection**. Some
share generic rendered weapon actions or already supported particle kinds, which
is insufficient to mark the skill rendered. Prioritize their frequently repeated
area/primary attack branches at weight 5; class buffs and secondary attacks at 4;
rare event/item skills at 1. Those group weights are provisional until their
caller branches are individually mapped. Master brand aliases and fourth/fifth
variants need explicit base selection and authoritative session context, rather
than assuming that a usable skill icon reaches one of the 23 native routes.

The two JSON EffectManager types, including their 370 installed effect trees,
are separately reconstructed in client-effects.md and client-effect-manager.md.
Their factory has no skill caller. They therefore add **zero** to skill cast
coverage; map/Muun attachment tables remain a separate gap. World, helper and gear
effects are tracked by their own finding documents. This inventory does not
claim those thousands of effect call sites are all implemented.

## RENDER-EFFECTS-002 instruction evidence

Same pinned target as client-combat.md: executable SHA-256
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`,
text `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`,
data `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`.

| Family | Original entry / selected bodies | Cases | Mismatches |
|---|---|---:|---:|
| Effect create | 0x013c0f19; Ice 0x013d01a5, debris 0x013d5d55, Poison01 0x013d71c9, wave 0x013cf050 | 4,000, 1,000 per kind | 0 |
| Effect move | 0x0142fd09; Ice 0x0146b979, debris 0x0145d25b, Poison01 0x0144f50b, wave 0x01453c6c | 4,000, 1,000 per kind | 0 |
| Poison smoke create | 0x015ae7b0, subtype body 0x015c5f15 | 1,000 | 0 |
| Poison smoke move | 0x01616c80, record body, subtype 0x01634dc5 | 619 instruction comparisons + 381 native head-removal checks | 0 |
| Poison smoke render | 0x0159123f, record body | 1,000 | 0 |

`validate_render_effects.py --cases 1000 --mutations` compares authored compiled C
with original instructions in 10,619 cases, checking record fields, ordered
emitted calls and RNG counts. An additional 381 cases check native head removal.
It uses a fresh strict machine for every family and mutant. Owner/no-owner,
terrain contact, animation completion, absent model, lifetime expiry and emission
branches vary. Particle render checks sprite calls/blend, not the original GPU.
Host libm, terrain height, animation/model services and creator calls remain
explicit stubs as in the existing validators. Smoke move's erased-at-head cases
check native removal without running a record body the client would skip.

Eight compiled mutants are caught: Ice lifetime 200/200, Poison01 blend 200/200,
wave speed 200/200, Ice fade 62/200, debris bounce spin 97/200, wave emission count
200/200, Poison smoke lifetime 200/200, Poison smoke blue tint 122/200. These are
mutated production C builds checked by the same comparison, not altered expected
values. Reports include full body hashes and remain local until cleanup.

## RENDER-EFFECTS-002 integration and limits

`mu_combat` loads Ice01/Ice02/Magic02 once, uses the existing fixed effect and
particle pools, and forwards smoke to the existing world particle renderer. No
per-frame allocations were added. Perf/mesh/scene code and joint logic are
unchanged. One Poison01 create/move family is recovered for completeness, but the
player adapter deliberately uses smoke. The monster-only model caller remains
unwired; it receives no player coverage credit.

Static caller corrections to older client-combat.md notes:

- 0x013afd61..0x013afe21 creates Ice at the target plus five debris pieces.
- 0x013aff75..0x013b0075 creates Poison01 only for monster model 0xa91, then
  ten smoke01/1 particles for the ordinary player path.
- 0x013b04d5..0x013b0635 creates side waves only for monster model 0x7b7.
  The player creates one forward wave, not three.

The portable native test casts 1/7/11 through the fixture-backed combat session,
checks exactly one encrypted request stays unsent, no invented damage/death,
expected model types/counts, no unsupported emissions, learned session state,
and changed software-rendered pixels when the new assets/particle pass are
removed. It uses synthetic authored assets, not client data. This shares the
same end-of-attack path used by checked GFx casts. Three additional headless
OpenGL/GFx runs use the existing converted `all-bridge` movies, authored tables
and one learned/initially selected skill per fixture session. Checked casts 1/7/11
all return OK, produce one unsent request each and zero unsupported emissions,
hits or kills. They create respectively 0/6/1 effects and 10/16/52 particles over
30 frames. The older movie's hotkey-change probe reported skill-zero callbacks
and retained the previous selection; these separate-session casts do not certify
hotkey selection. Full bar editing and a live original-client image comparison
remain outside this evidence.

New casts intentionally change pixels, RNG consumption, particles and terrain
lights. Existing spell, noncombat and golden outputs must retain their hashes.

## RENDER-EFFECTS-003 evidence and limits

[New finding](client-render-effects-003.md): 11,277 skill instruction comparisons
plus 723 native removal checks; 10/10 compiled mutants caught. Three fixture casts
reach the new draws without invented damage or delivered encrypted requests.
The K-coordinated world consumers add 13,176 instruction comparisons plus 1,824
removal checks, with 7/7 compiled mutants. They add no skill coverage credit.

Rageful Blow remains M. Static inspection of MoveEffect 0x01450a73 shows distinct
lifetime-11 and lifetime-10 impact branches producing 0x463..0x469, terrain-gated
pieces and owner-weapon rendering 0x01532bd2. Implementing only 0x461 create or its
eight tail fragments would leave the principal impact missing. No partial port
is retained. Buff auras, arrows, Death Stab trails, master/later-class selection
and live image comparison remain open. Aqua Beam here is subtype 0 in ordinary
worlds, without the special-world wall cutoff or hero-only area-request and
source-buffer-writeback services. Those are explicit limits, not additional
primary cast routes. The pre-existing mount-breath rounding difference is unchanged.

## RENDER-EFFECTS-004 evidence and limits

[New finding](client-render-effects-004.md): 32,000 original-instruction comparisons, zero
mismatches, 15/15 compiled mutants. Rageful Blow (42) is P for ordinary worlds: the caller
`0x013a94a4`, 0x461 and its nine piece kinds, the item initialiser and the weapon draw are
verified. Triple Shot (24) is P for the native bow: CreateArrows/CreateArrow are verified and the
fan changes from the old static -8/0/+8 to the client's 0/+15/-15. Other bows' arrow models,
master-tree/skill-tree/item-option branches (authored inputs) and bow 0x12f9's sparks remain.
Greater Defense/Damage stay L: their persistent auras need the authoritative buff feed.
Death Stab stays L: its skill-step trails are unaudited. Master/later-class selectors still need
explicit base selection and session context. The Spirit of Guardian wing (pet cosmetic) adds
no skill credit.

## RENDER-EFFECTS-005 evidence and limits

[New finding](client-render-effects-005.md): 10,800 original-instruction comparisons, zero mismatches,
25/25 compiled mutants. The rank-5 item owner block (19/19 types, four type-list variants) and Deep
Dungeon's DungeonStone 0x43a add no skill credit: primary routes stay 20/23 and weighted coverage
65/77. Triple Shot stays P for the native bow; the other 32 arrow models were measured (none shares
Arrow01's create/move) and remain open with bow 0x12f9's sparks, Rudolph 0x3fa and the pet particle
kinds.

## RENDER-EFFECTS-007 evidence and limits

[New finding](client-render-effects-007.md): 5,960 original-instruction comparisons, zero mismatches, 31/31 compiled
mutants. Triple Shot (24) stays P; its other bows now have their own arrows: 30 of the 32 models besides Arrow01
(bow arrow models with create/move 1/33 → 31/33; 0x615/0x617 need named model bones), and bow 0x12f9's fifteen
sparks are verified. Primary routes stay 20/23 and weighted coverage 65/77. The rank-5 pants have no owner block
(verified), EffectManager bone −1 attaches, and Rudolph's 0x3fa and its Shiny01 0x7f66/7 are pet cosmetics without
skill credit. The arrows' joint and particle kinds are created as calls but not yet native kinds.
