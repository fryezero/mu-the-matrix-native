# Skill visual coverage, RENDER-EFFECTS-002

This is a reviewed coverage summary, not an export of Skill(Kor). The baseline is
main `a38ec75`, including SESSION-COMBAT-001 #197 and SESSION-SKILL-001 #204.
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

| Skill / primary visual | Eligible classes | Table level / use | Weight | Before | After | Rendered result or remaining gap |
|---|---|---|---:|---|---|---|
| 0 normal attack | All, weapon-dependent | All levels | 5 | P | P | Weapon actions; bow arrow model and trail |
| 1 Poison | DW, MG, RW, Mage, Alchemist | 30, early spell | 3 | M | P | Ten smoke01/1 particles at target; model 0x414 belongs to a monster branch |
| 2 Meteorite | DW, MG, Summoner, RW, Mage, Alchemist | 21, early spell | 3 | M | M | Fire01 subtype 0, distinct from Fire Ball subtype 1 |
| 4 Fire Ball | DW, MG, Summoner, RW, Mage, Alchemist | 5, early spell | 3 | P | P | Fire01/1, fire trail and impact stones |
| 7 Ice | DW, MG, Summoner, Light Wizard, Mage, Alchemist | 25, early/control | 3 | M | P | Ice01 and five Ice02 debris models, smoke and negative terrain light |
| 9 Evil Spirit | DW, MG, RW | 50, repeated area farming | 5 | P | P | Eight spirit ribbons, wide-spirit Laser01 and terrain light |
| 10 Hellfire | DW, MG, RW, Mage, Alchemist | 60, area spell | 2 | P | P | Circle01/02, fire and stones |
| 11 Power Wave | DW, MG, Summoner, Light Wizard, Mage, Alchemist | 9, early spell | 3 | M | P | One Magic02 model and four smoke01/3 particles per step |
| 12 Aqua Beam | DW, MG, Light Wizard, Alchemist | 74, directional spell | 3 | M | M | 0x7f4e beam family and per-step character case |
| 14 Inferno | DW, MG, RW, Mage, Alchemist | 88, recurring area spell | 4 | L | L | Inferno01 and ring stones; burst 0x013c07f4 absent |
| 17 Energy Ball | DW | 2, starting spell | 3 | P | P | Thunder01 and Spark03 particles |
| 19 Falling Slash | DK, MG, DL, RF, Crusader | 0, weapon skill | 2 | P | P | Weapon action 0x89; no separate model at audited end site |
| 20 Lunge | DK, MG, DL, GL, Slayer | 0, weapon skill | 2 | P | P | Weapon action 0x8a |
| 21 Uppercut | DK, MG, DL, Slayer | 0, weapon skill | 2 | P | P | Weapon action 0x8b |
| 22 Cyclone | DK, MG, DL, Slayer, Illusion Knight | 0, weapon skill | 2 | P | P | Weapon action 0x8c |
| 23 Slash | DK, MG | 0, weapon skill | 2 | P | P | Weapon action 0x8d |
| 24 Triple Shot | Elf | 0, recurring ranged farming | 5 | L | L | Three default arrows; item/skill-specific arrow choices and spread variants remain |
| 26 Heal | Elf | 8, recurring support | 4 | P | P | Target ground effect, three energy ribbons and arrival sprite |
| 27 Greater Defense | Elf | 13, recurring support | 4 | L | L | Cast animation/sound; persistent buff aura/authoritative buff feed absent |
| 28 Greater Damage | Elf | 18, recurring support | 4 | L | L | Cast animation/sound; persistent buff aura/authoritative buff feed absent |
| 41 Twisting Slash | DK, MG, Slayer, Crusader | 0, repeated melee farming | 5 | P | P | Weapon swirl, smoke, sparks, joint streaks |
| 42 Rageful Blow | DK, Slayer, Crusader | 170, later melee farming | 4 | M | M | 0x461 impact and character-step branch |
| 43 Death Stab | DK | 160, later melee combat | 4 | L | L | Action 0x9e; associated skill-step trails remain unaudited |

Totals: **12 P / 5 L / 6 M before; 15 P / 5 L / 3 M after**, out of 23
routes. Strict primary coverage rises from 52.2% to 65.2%. The sum of priority
weights is 77; primary-covered weight rises from 37/77 to 46/77, or 48.1% to
59.7%. Limited rows receive no primary-coverage credit. No percentage here applies
to all client skills, aliases, monsters, gear effects or worlds.

## Other client skill groups and class exposure

The snapshot has many upgrades, passives, item/event skills and shared base
skills. Counting all 973 as independent casts would inflate the denominator.
This table reports candidate records with brand 0 and use type 0/4/7/8/14, and
class-map value > 0. It is a static workload inventory, not a claim that every
candidate casts, is learned, or has a unique effect. Classes overlap.

| Class | Candidate records | Audited primary records before / after | Highest-priority remaining visuals |
|---|---:|---:|---|
| DW | 69 | 4 / 7 | Aqua Beam, Meteorite, Inferno burst, later area spells |
| DK | 63 | 6 / 6 | Rageful Blow, Death Stab trails, later combos |
| Elf | 73 | 1 / 1 | Buff auras, arrow variants, later bow area skills |
| MG | 79 | 9 / 12 | Aqua Beam, Meteorite, later blade/spell families |
| DL | 64 | 4 / 4 | Command/fire-chain and raven-specific combat visuals |
| Summoner | 64 | 1 / 3 | Summon/drain/lightning and later class spells |
| RF | 58 | 1 / 1 | Fist/charge/area families |
| GL | 57 | 1 / 1 | Lance/charge/area families |
| RW | 68 | 3 / 4 | Rune-specific area spells and Meteorite |
| Slayer | 54 | 4 / 4 | Class trails and Rageful Blow |
| Gun Crusher | 50 | 0 / 0 | Gun/projectile/area families |
| Light Wizard | 60 | 0 / 2 | Aqua Beam and class-specific light spells |
| Mage | 68 | 2 / 5 | Meteorite and class-specific spells |
| Illusion Knight | 43 | 1 / 1 | Illusion/weapon-copy families |
| Alchemist | 67 | 2 / 5 | Aqua Beam, Meteorite and alchemy families |
| Crusader | 54 | 2 / 2 | Rageful Blow and holy/charge families |

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

## New instruction evidence

Same pinned target as client-combat.md: executable SHA-256
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`,
text `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`,
data `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`.

| Family | Original entry / selected bodies | Cases | Mismatches |
|---|---|---:|---:|
| Effect create | 0x013c0f19; Ice 0x013d01a5, debris 0x013d5d55, Poison01 0x013d71c9, wave 0x013cf050 | 4,000, 1,000 per kind | 0 |
| Effect move | 0x0142fd09; Ice 0x0146b979, debris 0x0145d25b, Poison01 0x0144f50b, wave 0x01453c6c | 4,000, 1,000 per kind | 0 |
| Poison smoke create | 0x015ae7b0, subtype body 0x015c5f15 | 1,000 | 0 |
| Poison smoke move | 0x01616c80, record body, subtype 0x01634dc5 | 1,000 including head erasures | 0 |
| Poison smoke render | 0x0159123f, record body | 1,000 | 0 |

`validate_render_effects.py --cases 1000 --mutations` compares authored compiled C
with original instructions, record fields, ordered emitted calls and RNG counts.
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

## Native integration and limits

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
same end-of-attack path used by checked GFx casts. The full checked GFx skill-bar
interaction and a live original-client image comparison are separate limits.

New casts intentionally change pixels, RNG consumption, particles and terrain
lights. Existing spell, noncombat and golden outputs must retain their hashes.
