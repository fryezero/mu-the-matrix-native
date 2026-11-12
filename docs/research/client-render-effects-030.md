# Demo-class skill visual audit and callers

RENDER-EFFECTS-030 starts from EFFECTS-028 `32e36706`, with main `d4af71dd`.
The first deliverable is the complete selectable demo inventory below. This is
an offline presentation audit. No original client, service or installed app is used.

## Evidence and denominator

The pinned executable SHA-256 is
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
Capture09 text is
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`.
Run10 image data is
`c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`.
All bytes and decoded tables remain private. Addresses below are static
instruction readings until a comparison family explicitly verifies them.

`native/fixture/skills_model.c` supplies fourteen DK learned entries.
`native/client/demo-skills.txt` supplies fourteen Elf entries, including 2044.
These are the complete learned sets that the demo can select and assign to
its hotbar, regardless of whether usability checks permit a cast. A visible
unlearned tree icon is not a selectable learned cast. Skill 0 is separately
included because ordinary attacks are always available.

The shipped `demo-characters.txt` uses DK byte `0x01` and Elf byte `0x02`.
It contains no evolved byte. The fixture list selector uses `class_byte & 15`,
so synthetic promoted bytes `0x11/0x21/0x31/0x41` and
`0x12/0x22/0x32/0x42` inherit those lists. This does not establish their visual
selectors. Death Stab currently explicitly refuses every byte except `0x01`.
Master/fourth/fifth trees do not automatically add a learned skill or a cast
route. Skill 47 is a stale fixture entry absent from the pinned language table.

P means the bounded primary cast visual is present. L means a specific visual
or context remains missing. M means the primary cast visual is missing. Before this lane that normally
also means the native adapter refuses the skill. A recovered caller whose
consumers all refuse still remains M.
These labels concern presentation only. Authoritative buffs, power, target
state and service eligibility are excluded. They do not change the historical
23-route denominator in the earlier coverage table.

D = attack-step default `0x0139b454`; A = area-end default `0x013aea7a`;
E = targeted-end default `0x013b1911`. The corresponding dispatchers are
`0x013966ea`, `0x013a90c0` and `0x013af035`. Addresses name the entry of the
selected body, including leading field reads. Buffs have a separate persistent
RenderCharacter consumer. Priorities estimate repeated use, not telemetry.

| Class | Skill | Priority | Before | Original step / end body | Native result or missing part |
|---|---|---:|---|---|---|
| Both | 0 ordinary attack | 5 | P | SetPlayerAttack `0x01392bde`; A | Weapon action or the demo bow's verified arrow |
| DK | 19 Falling Slash | 2 | P | D / A, E; receive `0x01253a92` | Action `0x89` |
| DK | 20 Lunge | 2 | P | D / A, E; receive `0x01253a92` | Action `0x8a` |
| DK | 21 Uppercut | 2 | P | D / A, E; receive `0x01253a92` | Action `0x8b` |
| DK | 22 Cyclone | 2 | P | D / A, E; receive `0x01253a92` | Action `0x8c` |
| DK | 23 Slash | 2 | P | D / A, E; receive `0x01253a92` | Action `0x8d` |
| DK | 41 Twisting Slash | 5 | P | D / `0x013aba81` | Swirl, smoke, sparks and joints |
| DK | 42 Anger Strike, previously labelled Rageful Blow | 4 | P | D / `0x013a94a4` | Flying weapon and quake family, ordinary worlds |
| DK | 43 Death Stab | 4 | L | `0x0139959c` / A, E | Base-DK bone-33 fixture draws 189 requests; general link selector missing |
| DK | 44 Crescent Moon Slash | 2 | M | `0x0139a76f` / `0x013ad798` | Missing action/caller and selected effect consumers |
| DK | 18 Defense | 3 | M | D / A, E; action path separate | Missing shield action admission; absence of an end effect is not proof of a complete cast |
| DK | 47 stale fixture entry | 1 | M | D / A, E | Absent skill record; no invented name, selector or cast |
| DK | 48 Swell Life | 4 | M | `0x0139a51f` / `0x013aa0e1` | Missing 36 joint requests and presence consumer; no real buff values admitted |
| DK | 49 Fire Breath | 1 | M | `0x0139a6f8` / `0x013aba0c` | Missing mount-context caller |
| DK | 344 Blood Storm | 5 | M | `0x0139b2fd` / `0x013a9f25` | Missing `0x583/0` emitter, children and adapter |
| Elf | 24 Triple Shot | 5 | L | D / `0x013af9db` | Existing arrow fan; audit found the caller falls through into `0x013af9fe`, requiring a second request and actual skill/learned-index argument order |
| Elf | 26 Heal | 4 | P | D / `0x013afaab` | Ground effect and energy ribbons |
| Elf | 27 Greater Defense | 4 | L | D / `0x013afb06`; persistent `0x01370ccc` | EFFECTS-028 authored aura; general links/presence input absent |
| Elf | 28 Greater Damage | 4 | L | D / `0x013afcea`; persistent `0x01370ccc` | EFFECTS-028 authored aura; general links/presence input absent |
| Elf | 30 Summon Goblin | 1 | M | D / `0x013a9449` | Actor construction/lifetime outside this lane's owned files |
| Elf | 31 Summon Stone Golem | 1 | M | D / `0x013a9449` | Same summon owner gap |
| Elf | 32 Summon Assassin | 1 | M | D / `0x013a9449` | Same summon owner gap |
| Elf | 33 Summon Elite Yeti | 1 | M | D / `0x013a9449` | Same summon owner gap |
| Elf | 34 Summon Dark Knight | 1 | M | D / `0x013a9449` | Same summon owner gap |
| Elf | 35 Summon Bali | 1 | M | D / `0x013a9449` | Same summon owner gap |
| Elf | 36 Summon Soldier | 1 | M | D / `0x013a9449` | Same summon owner gap |
| Elf | 51 Ice Arrow | 4 | M | D / `0x013afa2c` | Missing target-index write and single-arrow caller |
| Elf | 52 Penetration | 4 | M | `0x01399ca2` / `0x013af9fe` | Missing step-3 charge `0x7fd0/0`, five-step cutoff and subtype-2 arrow caller |
| Elf | 2044 Raining Arrow of Saturation | 5 | P | Receive visual slice `0x0125f5d1`; `0x014d1a18` | Authored ground-volley route, rings, rain, landings and decals |

The before inventory is 10 P, 4 L, 15 M across 29 class/skill rows, counting
ordinary attack once. The DK list has fourteen entries, Elf fourteen, plus zero.
The historical P label for Triple Shot covered the fan component but missed its
caller fallthrough. This wider audit records that limitation rather than treating
component verification as proof of the whole caller.

## Work order and limits

Research Blood Storm first, then the repeated Elf arrow callers and Swell Life.
If a required item/particle consumer is absent, record its exact counted refusal
for EFFECTS-026. Do not add that lane's consumer. Actor summons remain an actor
follow-up. Later-class aliases require individually compared synthetic selector
inputs; a masked class nibble alone is not admission evidence.

## Recovered caller slices

The new `demo_skill_fx` module accepts an explicit raw/base pair, owner, learned
slot, target client index and visual state. Compared pairs are 24/24, 48/48, 51/51,
52/52, 344/344, 416/52 and 424/51. The last two match the installed brand
links but are synthetic selector inputs in the proof. Every other tested pair
is refused. This does not grant a learned skill, authoritative class or power.

- Blood Storm sets AttackTime to 15 at `0x0139b2fd`. Its area-end body
  `0x013a9f25..0x013aa064` uses the caster's light array as a destination point:
  x/y = target tile plus 0.5, times 100, z = caster z. It requests `0x583/0`,
  owned by the caster, key and info word8 -1, scale 0. The missing emitter
  constructor is `0x013f2b83`, with lifetime 70, child `0x584/0` and sound
  `0x2b0`. The native refusal is retained; no primary Blood Storm pixels are
  claimed. Its generic fixture cast action is not a recovered receive action.
- Swell Life's step body `0x0139a51f` ends the attack after step 9 only for
  Player actions `0x9c/0x11d`. The end body `0x013aa0e1..0x013aa2af` requests
  36 `0x7fd3/2` joints, caster z +100, angles -10/0/n*10, width 60, key 0,
  skill 0 and the remaining original defaults. At ordinals 0 and 20 it also
  requests `0x7f84/4` at the caster. The final sound is `0x7f`, null owner,
  at `0x013aa2a7`. All 38 visual consumers are currently refused. No persistent
  Swell Life presence, duration, health value or target state is supplied.
- Penetration's step body `0x01399ca2..0x01399d80` holds Player actions
  `0x6f <= action < 0x133` at frame 5, prior frame 4, once frame >=5.
  Step 3 requests `0x7fd0/0` and sound `0x81` owned by the caster. Cutoff is 5.
  The charge constructor is `0x013c8b17`, mover `0x01442503`, and is absent.
  The subtype-2 arrow also requests missing child `0x46c/0`. Both refusals are
  counted. The existing arrow body and its motion are reused.
- Ice Arrow's end body `0x013afa2c..0x013afa66` copies CHARACTER target index
  `+0x40` to OBJECT `+0x364`, then requests one arrow. The existing CreateArrow selector
  uses this word for base 51. No freeze, target animation or target buff is set.
- Triple Shot's `0x013af9db` requests CreateArrows with learned-list index,
  flag 1 and final selector 0. It falls through to `0x013af9fe`, which requests
  learned-list index, flag 0 and actual raw skill ID. This is three fan shots
  plus one straight shot for the ordinary fixture bow. The old adapter emitted
  only three and passed the skill ID as a learned index.

The learned-index lookup is the original `0x016a782e` service. It searches
only 150 slots, returns the first match and falls back to slot zero. The native
adapter searches active learned entries with the same 150-slot cap. Stale
entries beyond the learned count are outside native admission. No live learned
list is acquired.

## Native boundaries

Only the authored demo's class and weapon context admits these new callers.
Bow/crossbow actions are the unwinged choices in `0x013946ee` and
`0x013947d8`; Swell Life uses the base fixture action `0x9c` from the
SkillAction call at `0x0125738f`. This is a bounded visual adapter, not the
whole receive handlers. The live target's optional Ice Arrow response is absent.
Audio request provenance is preserved for the two new step/end sounds; the
older arrow helper's ignored sound decisions remain outside this change.

Missing consumers are explicit follow-ups for the effects-consumer lane,
not substitutes or successes. No new item/particle consumer, actor, world,
Muun or UI source is added. New visible results reuse the existing arrow
construction/movement and model pass. Static selector evidence, native
repeatability and original GPU fidelity remain distinct.

## Complete tree catalogue and alias audit

The initial learned set above is narrower than the tree catalogue. Applying
the native stamp manager's actual filters, `fill_basic` and `fill_special`,
to the pinned class maps produces 26 basic and one special entry for DK,
36 basic and one special for Elf. Use type 7 records are excluded by this
UI path, unlike the old workload estimate. Class nibble lookup gives the same
catalogue for the synthetic promoted bytes described above.

Every catalogue row outside the learned set is listed here. Each is M before
and after: no cast admission exists for its exact ID in this bounded native
adapter. A shared effect kind does not establish its caller. A visible
unlearned icon cannot itself become a hotbar cast. The addresses are the
selected static step and area/targeted end bodies for that base ID, without
executing receive or power logic. This is a reviewed visual coverage summary,
not a copy of the skill table or its requirements.

| Class | Unlearned catalogue skill | Before / after | Step body | Area / targeted end body |
|---|---|---|---|---|
| DK | 76 Plasma Storm | M / M | `0x0139b454` | `0x013ad018` / `0x013b1911` |
| DK | 232 Strike of Destruction | M / M | `0x0139b2fd` | `0x013a99b4` / `0x013b1911` |
| DK | 723 Fire Blow | M / M | `0x01397e0b` | `0x013aea7a` / `0x013b1911` |
| DK | 740 Archangel's will | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| DK | 813 Rush | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| DK | 1125 Poison Storm | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| DK | 1126 Frozen Slayer | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| DK | 1127 Bloodying Hit | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| DK | 1500 Sword's Fury | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| DK | 1501 Sword Blow | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| DK | 1502 Strong Belief | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| DK | 1503 Solid Protection | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| DK | 2040 Sword Blow of Saturation | M / M | `0x0139b454` | `0x013a955a` / `0x013b1911` |
| DK | 2043 Destruction of Gale | M / M | `0x0139b2fd` | `0x013a99b4` / `0x013b1911` |
| Elf | 46 Starfall | M / M | `0x0139b454` | `0x013aea7a` / `0x013afa6b` |
| Elf | 76 Plasma Storm | M / M | `0x0139b454` | `0x013ad018` / `0x013b1911` |
| Elf | 77 Infinity Arrow | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| Elf | 234 Recovery | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| Elf | 235 Multi-Shot | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| Elf | 425 Cure | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| Elf | 426 Party Healing | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| Elf | 427 Poison Arrow | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| Elf | 430 Bless | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| Elf | 432 Summon Satyros | M / M | `0x0139b454` | `0x013a9449` / `0x013b1911` |
| Elf | 651 Shadow Step | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| Elf | 652 Evasion | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| Elf | 727 Focus Shot | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| Elf | 740 Archangel's will | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| Elf | 1125 Poison Storm | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| Elf | 1126 Frozen Slayer | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| Elf | 1127 Bloodying Hit | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| Elf | 2023 Raining Arrow | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| Elf | 2024 Dex Booster | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| Elf | 2025 Holy Bolt | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| Elf | 2026 Improve Elemental Attack Power | M / M | `0x0139b454` | `0x013aea7a` / `0x013b18a2` |
| Elf | 2027 Improve Elemental Defense | M / M | `0x0139b454` | `0x013aea7a` / `0x013b16c1` |
| Elf | 2047 Holy Bolt of Gale | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |

The class maps also expose 46 DK and 40 Elf brand aliases. The table below
lists every alias, grouped only when its base, original bodies and coverage
are the same. Only 416 and 424 gain explicit synthetic visual selection in
this lane; the others remain M. These records replace a learned base entry
when supplied by the authored fixture. Their presence in a decoded table does
not make them learned. No master/fourth/fifth power or state is synthesized.

| Class | Alias IDs | Base | Before / after | Step body | Area / targeted end body |
|---|---|---:|---|---|---|
| DK | 328 | 19 | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| DK | 329 | 20 | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| DK | 326 | 22 | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| DK | 327 | 23 | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| DK | 330, 332, 811 | 41 | M / M | `0x0139b454` | `0x013aba81` / `0x013b1911` |
| DK | 331, 333, 812, 1069 | 42 | M / M | `0x0139b454` | `0x013a94a4` / `0x013b1911` |
| DK | 336, 339, 342, 1071 | 43 | M / M | `0x0139959c` | `0x013aea7a` / `0x013b1911` |
| DK | 356, 360, 363 | 48 | M / M | `0x0139a51f` | `0x013aa0e1` / `0x013b1911` |
| DK | 807, 809, 1202 | 232 | M / M | `0x0139b2fd` | `0x013a99b4` / `0x013b1911` |
| DK | 340, 343 | 337 | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| DK | 346 | 344 | M / M | `0x0139b2fd` | `0x013a9f25` / `0x013b1911` |
| DK | 1072 | 723 | M / M | `0x01397e0b` | `0x013aea7a` / `0x013b1911` |
| DK | 1129, 1133, 1196, 1199 | 1125 | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| DK | 1130, 1134, 1197, 1200 | 1126 | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| DK | 1131, 1135, 1198, 1201 | 1127 | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| DK | 801, 802 | 1500 | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| DK | 1203 | 1501 | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| DK | 810 | 1502 | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| DK | 803, 804, 805, 806, 1204 | 1503 | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| Elf | 414, 418, 1081 | 24 | M / M | `0x0139b454` | `0x013aea7a` / `0x013af9db` |
| Elf | 413, 1226 | 26 | M / M | `0x0139b454` | `0x013aea7a` / `0x013afaab` |
| Elf | 417, 423, 1229 | 27 | M / M | `0x0139b454` | `0x013aea7a` / `0x013afb06` |
| Elf | 420, 422, 1228 | 28 | M / M | `0x0139b454` | `0x013aea7a` / `0x013afcea` |
| Elf | 424 | 51 | M / L, explicit selector only | `0x0139b454` | `0x013aea7a` / `0x013afa2c` |
| Elf | 416 | 52 | M / L, explicit selector only | `0x01399ca2` | `0x013aea7a` / `0x013af9fe` |
| Elf | 441 | 77 | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| Elf | 411, 431, 1083 | 235 | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| Elf | 429, 1227 | 426 | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| Elf | 434 | 427 | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| Elf | 433, 1230 | 430 | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| Elf | 1085 | 727 | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| Elf | 1129, 1133, 1196, 1199 | 1125 | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| Elf | 1130, 1134, 1197, 1200 | 1126 | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| Elf | 1131, 1135, 1198, 1201 | 1127 | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| Elf | 1222 | 2023 | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| Elf | 876, 1223 | 2025 | M / M | `0x0139b454` | `0x013aea7a` / `0x013b1911` |
| Elf | 1224 | 2026 | M / M | `0x0139b454` | `0x013aea7a` / `0x013b18a2` |
| Elf | 1225 | 2027 | M / M | `0x0139b454` | `0x013aea7a` / `0x013b16c1` |

The composite Triple Shot correction also affects special bows. Their existing
four-shot fan is followed by the same one-shot request, so five arrows result.
Bow `0x12f9` executes its existing fifteen-spark suffix on each CreateArrows
call, thirty sparks total. The original fan/arrow consumer comparisons remain
unchanged; the new caller proof observes both requests and their distinct
arguments. The special-bow regression expectations follow that composition.

## After status in the learned demo set

| Skill | Before -> after | Result and remaining visual limit |
|---|---|---|
| 24 Triple Shot | L -> P | Both original requests; four ordinary arrows or five with the special fan; original learned-index argument order |
| 51 Ice Arrow | M -> L | Arrow with a saved client target index now draws and retires; optional target-side ice/freeze receive visual and general equipment context remain unadmitted |
| 52 Penetration | M -> L | Step gate, short cutoff and subtype-2 projectile draw; charge and `0x46c/0` child remain refused |
| 48 Swell Life | M -> M | Caller now requests the original 38 visuals and counts all 38 refusals; no primary aura pixels claimed |
| 344 Blood Storm | M -> M | Original emitter request and early cutoff, one refused emitter; no primary Blood Storm pixels claimed |
| 416 / 424 | M -> L | Individually evidenced synthetic selector pairs only, with the same base limits |

All other learned rows retain their before label. This is 11 P / 5 L / 13 M
across the 29-row learned inventory. The separate historical 23-route total
stays 20 P / 3 L; its Triple Shot primary component label is now supported by
the corrected composite caller too. No percentage for all client skills follows.

The separate private alias test also executes the real base walk
`0x00bb1c32..0x00bb1c9e` over authored lookup records, not a stubbed base result.
It supplies only each record's index and brand at `+4/+0x5c`, with undefined
bytes elsewhere. Correct 416->52 and 424->51 chains are accepted. Swapped chains
and brand-zero records are refused by the new selector. These six original
cases prove the individual synthetic selector inputs without class or power state.

## Focused proof accounting

The full new validator passes 1,914 checks in 29.47 s: 572 original step
comparisons, 1,000 original end-caller comparisons, 256 independent original
arrow create/move comparisons, 78 native selector controls and eight terminal
retirement assertions. Thus 1,828 checks execute original caller/record
instructions. The six additional real brand-walk cases are separate private
test evidence. All 18 compiled production-C mutants are caught with zero
original-machine stops. Unchanged consumers receive no new mutant run.

The eight lifecycle sequences cover base and master-selected ordinary arrows,
with each original record carried forward independently. C never reseeds an
original record between ticks. Normal expiry and an owner dying during flight
are both included. Host terrain/model/animation and arrow-hit services remain declared
synthetic inputs. The original caller comparator observes every request
argument in order, including both key/default words. Sound owners and call
sites are checked as part of that stream. These are component proofs, not
original GPU-image equivalence or whole-client acceptance.

The saved Ice Arrow word is a client character-table index. The original accessor
`0x009a13f4` bounds it to 400 entries and resolves `table + index * 0x3670`;
`0x009a143b` returns that character's OBJECT. The native adapter uses the
authored actor's `session_slot`, preserving this namespace rather than copying
its server key. The native fixture explicitly asserts that the slot and server
key differ and that the saved word equals the slot. No target-side visual or
state is added by this metadata correction.

Final native evidence and all 108 affected validator row timings are in the
[handoff](../handoffs/RENDER-EFFECTS-030.md). Seven merged scenes preserve all
42 earlier after images and repeat byte-identically; Penetration and alias 416
have a visually inspected frame-6 projectile with a farther authored target.
The default sweep has exactly the incoming INNER-002 Elbeland/Swamp delta,
with every other view identical. These are native determinism/component checks.
