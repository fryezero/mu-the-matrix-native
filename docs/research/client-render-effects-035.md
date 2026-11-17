# Skill callers outside the learned set, RENDER-EFFECTS-035

Request side only. This lane owns the combat callers; RENDER-EFFECTS-034 owns the particle, joint,
effect and sprite consumers, and no consumer file is changed here. Base: main `bb86bbf7` (PR #406,
steward batch 120, which includes EFFECTS-033).

## Evidence and method

Pinned target SHA-256 `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`; text and
data identities come from `scripts/pins.py`, the same captures as
[EFFECTS-030](client-render-effects-030.md). All bytes stay private.

The denominator is the catalogue of EFFECTS-030: the class-tree skills that the stamp manager's
filters list for the two demo classes and that are not in a learned demo set. It has 14 Dark Knight
and 23 Elf rows (37), and 46 DK plus 40 Elf brand aliases.

`scripts/skill_catalogue_census.py` reads the pinned text only. For every row it walks five
switches with the base skill as the switch value, interpreting only the switch's own compare,
branch and table instructions:

| Switch | Head | Default body |
|---|---|---|
| Attack step | `0x01396742` in `0x013966ea` | `0x0139b454` |
| Area end | `0x013a90c0` | `0x013aea7a` |
| Targeted end | `0x013af035` | `0x013b1911` |
| Magic receive, visual slice | `0x01253f73` in `0x01253a92` | `0x0125c47c` (returns) |
| Position-skill receive, visual slice | `0x0125c9c3` in `0x0125c7b0` | `0x01260e10` (SetPlayerMagic) |

Each selected case body is followed up to the join of its switch, and every presentation request
in it is listed in address order with the constant words pushed in front of the call: effect
(`0x013c0eaa`), joint (`0x0153b02c`), sound (`0x00a6ac96`), SkillAction (`0x012b001a`), the pose
helpers and CreateArrows (`0x0158d5bd`). The packet prologues of the two receive handlers are not
read as behaviour: only the case body runs later in the comparison, on authored records. In those
handlers the source character and its OBJECT are the frame slots `-0x18` / `-0x10` (magic) and
`-0x14` / `-0x10` (position); the magic handler's target is `-0x24` / `-0x14`.

The census is static evidence of what a row requests. The ordered arguments, default words, sound
sites, guards and state writes of the admitted rows are compared with the original instructions
by `scripts/validate_render_effects35.py` (below).

## Classification of the 37 rows

Full table: [skill-catalogue-classification.csv](skill-catalogue-classification.csv) (one line per
row: bodies, ordered receive and step/end requests, services, missing consumers, aliases, hero
branch and request-side state).

27 of the 37 rows select the default step and both default end bodies. Their visual is in a receive
slice (as for skill 2044), or absent. The other ten have their own step or end body.

| Group | Rows | Members | What the row needs | Request side |
|---|---:|---|---|---|
| A caster-frame | 8 | DK 740; Elf 77, 651, 652, 727, 740, 2023, 2025 | Receive slice with at most one pose, one caster-owned effect at the caster's position, angle and light, and one sound. Constant words; 727, 2023 and 2025 pass a key word | Admitted, 8 |
| B bone-frame buff | 3 | DK 1500, 1502, 1503 | Receive slice: pose `0x9c` (mounted alternative `0x11d`), one target-owned effect at bone 17 of the source (1502: of the target). A mount service can replace the position | Admitted, 3 (unmounted) |
| C triple storm | 6 | DK and Elf 1125, 1126, 1127 | Receive slice: one target-owned effect and two unowned effects raised above the target | Admitted, 6 |
| D heal family | 4 | Elf 234, 425, 430, 2024 | Receive slice: caster effect `0x8021` in front of the hand, pose `0xd9` or `0x106`, sound, one target effect. 234 has nineteen joints, four ground effects and two random-bone effects, and a second case in the position switch | Admitted, 4 |
| E existing end body | 3 | Elf 432, 2026, 2027 | The buff start `0x0125594d` (sound `0x6f`, SetPlayerMagic) and an end body: 432 uses the summon end `0x013a9449` | Admitted, 3 |
| F arrows | 4 | Elf 46, 235, 427, 2047 | Bow or penetration pose and an arrow or volley caller; 235 and 427 share an eight-effect volley block | Admitted, 4 |
| G own step or end body | 5 | DK 232, 723, 1501, 2040, 2043 | Own attack-step body (723) or area-end body (232, 2040, 2043); 1501 and 2040 share a larger position body | Refused: hand trace left |
| H mount context | 2 | DK 76, Elf 76 | Mount pose helper `0x0106c453` and a mounted end body | Refused: out of scope with Fire Breath |
| I no receive case | 2 | DK 813, Elf 426 | No case in either receive switch, default step and both default ends | Refused: nothing to request |

28 rows are admitted on the request side and 9 stay refused.

Aliases that map onto catalogue rows (not admitted by a shared base, as in EFFECTS-030): DK 807,
809, 1202 -> 232; 1072 -> 723; 801, 802 -> 1500; 1203 -> 1501; 810 -> 1502; 803..806, 1204 -> 1503;
Elf 441 -> 77; 411, 431, 1083 -> 235; 429, 1227 -> 426; 434 -> 427; 433, 1230 -> 430; 1085 -> 727;
1222 -> 2023; 876, 1223 -> 2025; 1224 -> 2026; 1225 -> 2027; and for both classes 1129, 1133, 1196,
1199 -> 1125; 1130, 1134, 1197, 1200 -> 1126; 1131, 1135, 1198, 1201 -> 1127. The planner refuses
every pair whose raw id differs from its base. One alias fact is static only: the position case of
232 selects action `0xb2` when the raw skill word equals the base and `0xb3` otherwise.

## Missing consumers

[skill-catalogue-missing-consumers.csv](skill-catalogue-missing-consumers.csv) lists the 39 effect
and joint ids that these rows request and that the native consumers do not admit
(`mu_sfx_effect_kind_supported`, `mu_jt_kind_supported`), with the requesting rows. 34 are effects
and 5 are joints; the two Plasma Storm joints have a computed subtype. Requests whose consumer
exists today: effect `0x70a/0` (2023), `0x7f84/3` (432, 2026), `0x10e6/1` and `0x461` (723, 232,
2043). Two arrow callers are also not compared consumers: CreateArrows with the volley word `0x7ff`
(2047) and with base 46 (Starfall); the native adapter keeps both requests and refuses them.

## The hero branch of a receive slice

Ten rows read the hero CHARACTER pointer `0x0a39d754` inside the slice (CSV column `hero_branch`).
The magic receive handler runs for every character; when the source is the hero itself, part of
the body is skipped:

- 727 skips the whole body; 740 skips it when the hero's key equals the record's source key or
  the two key words are equal (`0x012598ab`, the hero key sign-extended).
- 425, 430 and 234 skip the caster part (hand effect, pose `0xd9`, AttackTime) and keep the
  target part. 2024 has no branch.
- The buff start `0x0125594d` (432, 2026, 2027) plays its sound for both and poses only a source
  that is not the hero.

The skipped part belongs to the hero's own use routines (class routines `0x01080169` and
`0x01085bc3` under the dispatcher `0x0107f400..0x0107f638`, with further sites of the same effect
ids). Those routines also hold the request sends. They are named here as static pointers only and
are not traced, reconstructed or executed. The planner therefore takes "the source is the hero" as
an explicit input and both values are compared with the original.

## Recovered callers

`reconstructed/combat/catalogue_skill_fx.c` has one table, one row per admitted skill, and one
small emitter per group. S is the source record, T the target record.

| Group | Body | Ordered requests |
|---|---|---|
| A 740 | `0x012598ab` | Guard above. SkillAction `0x9a` / `0x12c`; effect `0x608/0` at S with light `0.7, 0.7, 1`, owner S |
| A 77, 652 | `0x012575bc`, `0x012591f6` | Effect `0x4b3/0` (652: `/2`) at S, owner S; sound `0x2e1`. 77 first writes hero data `+0x2ded = 10` |
| A 651 | `0x0125983f` | Source AttackTime = 1 only |
| A 727 | `0x01255ba2` | Not the hero: SetPlayerAttack; the target key is pushed onto the source OBJECT's `+0x1dc` list; effect `0x70e/0` at S, owner S, key word = target key |
| A 2023 | `0x0125f710` | SkillAction `0x107`; effect `0x70a/0` at S, owner S, key word = source key, scale 1 |
| A 2025 | `0x0125f82c` | SetPlayerMagic; effect `0x708/0` at S, owner S, key word = the record word at frame `-0x28`; sound `0x55f` |
| B 1500, 1502 | `0x01254c46`, `0x01254e31` | No model: nothing. Target OBJECT `+0x364` = source index; bone 17 of S (1502: of T); effect `0x69d/1` (`0x69c/1`) at the bone, T angle and light, owner T; SkillAction `0x9c` / `0x11d` |
| B 1503 | `0x0125501c` | Bone 17 of S; SkillAction first; effect `0x69e/0` at the bone, owner T |
| C 1125..1127 | `0x01259964`, `0x01259b1b`, `0x01259cd2` | Effect `0x635..0x637/0` at T, owner T; two effects `0x8263..0x8265/0` at T with z raised by `(float)word(T CHARACTER +0x158) + 30`, white light, no owner |
| D 425, 430 | `0x01258d76`, `0x01258fbc` | Not the hero: effect `0x8021/1` (`/3`) at S + rotate(`0, -220, 130`), light `0.2, 1, 0.4` (`1, 0.92, 0.4`), owner S; SkillAction `0xd9` / `0x125`; AttackTime of the source and of the hero = 1. Always: sound `0x334`; effect `0x593/0` (`0x594/0`) at T, owner T |
| D 2024 | `0x0125bf1c` | SkillAction `0x106`; effect `0x8021/3` as above; sound `0x334`; effect `0x594/0` at S, owner S |
| D 234 | `0x012552d1`, position `0x0125ddd7` | Not the hero: effect `0x8021/0`, light `0.7, 0.6, 0`, pose, source AttackTime = 1. Then at T (position case: at S): nineteen joints `0x7f78/0x2f` (width 40, key word 2); effects `0x4bd/0`, `0x809e/0, 1, 2` with light `0.3, 0.2, 0.1`, no owner; twice: one CRT draw modulo the model's bone count, that bone's position, effect `0x7f78/3` there. A missing model ends the body. The position case adds sound `0x350` |
| E start | `0x0125594d` | Sound `0x6f` unless the source's class word is `0x4d`; not the hero: SetPlayerMagic and source frame = 0; AttackTime = 1 |
| E 432 end | `0x013a9449` | Effect `0x7f84/3` at S, owner S (the summon end) |
| E 2026 end | `0x013b18a2` | Unless presence `0x12` on the source: effect `0x7f84/3` at T, owner T |
| E 2027 end | `0x013b16c1` | Needs source CHARACTER `+7`; unless presence `0x12`: effect `0x7f84/2` at T; then five joints `0x472/4` (width 20, fourth word = the source's signed target-index word) unless T has presence 2 and a live `0x472/4` or `/9` joint |
| F 46 | `0x01256da0`, end `0x013afa6b` | Penetration pose helper, AttackTime = 1; end: CreateArrows(source, target, learned index, 0, skill) and sound `0x2af` |
| F 235, 427 | `0x01260e65`, `0x0125856e` | Bow pose helper; 427 stores the target OBJECT at source `+0x34c`. Light `0.8, 0.9, 1.6`: two `0x38b6/0` at S + rotate(`0, 20, 0`), three `0x38b4/0` at S, two `0x38b5/0` at S + rotate(`0, 20, 0`), no owner; `0x4ba/1` (427: `/2`) at S + rotate(`0, -120, 145`), owner S, key word = the source's own slot in the 400-entry character table. 235: sound `0x34f`. 427: effect `0x591/0` at S raised 145, light `0.3, 1, 0.1`, same key word, scale 1 |
| F 2047 | `0x0125f798` | As 2025 with the base skill as the effect's second word, then CreateArrows(source, no target, `0x7ff`, 1, 0) |

All 28 rows select the default attack step `0x0139b454`: AttackTime becomes 15 at frame >= 1 for
Player action `0x8f`, or at frame >= 5 for Player actions `0x6f..0x132` and for model types
`0x7a5..0x9fc` with actions 3 and 4. The cutoff written at `0x01396738` is 15.

SkillAction `0x012b001a` starts the attack and sets the action; it sets the alternative only when
the mount service answers and CHARACTER `+0x31e8` is zero and the alternative is not -1. The
alternative is therefore the mounted pose. The second and third volley points in 235 / 427 are
written as `(0, -20, 0)` and then overwritten with zero before use; the comparison found that.

## Second group: the link selector and the learned buffs

The three learned L rows named the "general equipment-link selector" as their gap.

- A CHARACTER has two weapon link slots `0x3fc` apart. The link bone of slot n is the byte at
  `+0x19b1 + n * 0x3fc`. The only routine that fills it with other than zero is the character
  setup's type switch `0x0137eefc..0x0137f5f4` (jump table `0x0137f5f9` for model types
  `0x7a5..0x7ed`, then a compare chain) with two default helpers, `0x00df230b` (five types) and
  `0x00d9013e`. Every store is an immediate chosen by the OBJECT model type. No item, class or
  skill word is read. There are 55 type cases; three of them store slot 0 only. Any other type,
  including the Player model `0xa91`, gets 33 and 42.
- The attack step picks the slot with `0x013a5658`: slot 1 for Player actions `0x73` and `0x74`,
  else slot 0.

`reconstructed/combat/link_selector.c` holds both. The second helper `0x00d9013e` claims types
`0x7ee` and `0xa2f` (its two compares, static reading); it is another setter and is not recovered:
`mu_link_bones` reports those two types as not handled.

What this completes:

- 43 Death Stab reads its bone through the selector (Player type, action `0x9e`: slot 0, bone 33)
  instead of an authored constant. Because the selector reads no class word, the promoted DK class
  bytes use the same link; the fixture admission is now the DK class nibble instead of byte 1 only.
- 27 / 28: the aura fixture's two link bones come from the selector. Their cast end bodies were not
  requested before; they are the two bodies of 2027 and 2026 again at `0x013afb06` and `0x013afcea`
  (instruction-for-instruction the same apart from two loop slots and the exit) and are now run
  through the same emitter. 28 requests `0x7f84/3`, which has a consumer. 27 requests `0x7f84/2`,
  which has none, and the five `0x472/4` joints.

## Native boundaries

`native/core/mu_combat.c` runs the receive case body at the cast, as for 2044, and the end body at
the end of the attack. Only a pose the body requests changes the hero's action. Missing consumers
stay counted refusals (`skill35` report line).

- Admission: the exact catalogue id for the class nibble, an active learned entry within
  min(count, 150), not the exceptional item `0x12fb` (default-step spark burst), and for group F
  the authored bow kind. No default list contains a catalogue id; tests supply the entry through
  the fixture skills file (`MU_SKILL_DEMO`).
- `MU_SKILL35_CONTEXT=remote,self` (two 0/1 words, default `0,0`) is the authored receive record:
  `remote` presents the slice as for a source that is not the hero (the hero key word is then the
  source key plus one); `self` makes the record's target the source. Without `self` the target is
  the cast's actor.
- Services: only the hero's Player model can answer bone requests. 1502 (target bone) and 234
  (target bone count and random bones) are counted context refusals unless the record targets the
  source. Mounted bone-frame rows are refused by the planner. Presence answers for 2026 / 2027 are
  authored zero; the character-table slot of the hero is authored 0; the word at target CHARACTER
  `+0x158` is authored 0.
- Not modelled, no native reader: the hero byte of 77, the target-index word of 1500 / 1502, the
  key list of 727, the target link of 427.
- 27 / 28: the aura fixture buffs the hero, so the end body's record targets the hero; presence
  answers come from the fixture's authored clock. Without that clock the five joints of 27 are
  counted refusals.

## Limits

No eligibility, damage, mana, cooldown, server key, packet or power feature. The receive parsers
never run. The hero's own use routines are not traced. Group G (232, 723, 1501, 2040, 2043) keeps
its recorded reasons; 76 needs a mount body; 813 and 426 have nothing to request in either receive
switch. Skill 47, stale entries, Defense's held input, the summons' actor spawn and Fire Breath's
mount body are unchanged. Whether an extended learned set ships in the demo is the owner's
decision; nothing here adds one.
