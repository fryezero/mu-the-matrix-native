# Client-side combat: attacks, skills, hit reactions, death and damage text (NATIVE-COMBAT-001, NATIVE-COMBAT-002)

This milestone recovers what the client does in a fight and joins it to the native walk-around world:

- how the hero attacks: the attack range, facing the target, the attack action chosen from the weapon and class, the
  attack speed that sets its play speed, and the attack timer that decides when the visuals are created;
- skills: the action each skill takes and the visual its end of attack creates, for a representative set of classes;
- monster reactions: the hit reaction, the death action, the fade and the removal, and the monster attack;
- the floating damage text: colours, scales, the rise and fade, the font and its layout.

NATIVE-COMBAT-002 (section 8) adds the older effect system that draws skills and projectiles (effects, particles,
joints), the area skills, the hero's own hit and death, and the combat sounds.

SESSION-COMBAT-001 moves the synthetic server policy into the loopback fixture. Damage, death, rewards and
respawn reach the presentation through session frames. Earlier sections describe the original demo implementation;
section 9 records the migration and its plaintext boundary.

Labels used below:

- **verified**: authored C equals the client's instructions under Unicorn on every compared case;
- **static**: a reading of the decoded instructions that was not executed;
- **inference**: a name or an interpretation (for example the usual name of a skill number);
- **demo**: an input the server provides in the real game, made up here;
- **viewer choice**: native code that is not client behaviour.

## Identity

| Input | SHA-256 |
|---|---|
| `main.exe` (target) | `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a` |
| Restored text at `0x00401000` (capture09) | `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` |
| Second section at `0x01a7c000` (run10) | `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f` |

`scripts/validate_combat.py` refuses other inputs and reports the SHA-256 of every routine body it executes (18
bodies, for example SetAttackSpeed `e4df7811…`, SetPlayerAttack `939a9a61…`, RenderNumber `1d90abed…`).

## Routines

| Routine | Address | Status |
|---|---|---|
| MoveHero, attack case 3 (range, facing, attack start, attack packet) | `0x01697cab..0x01698096` in `0x01697c17` | static |
| In-range test (character, x, y, range) | `0x016a52a6` | verified |
| SetPlayerAttack(c) | `0x01392bde` | verified (Player branch, default monster branch, three special monsters) |
| Hero attack-speed adjustment (c) | `0x0138d9cf` | static |
| SetAttackSpeed(attack speed, magic speed) | `0x0138dc60` | verified (lifted by `scripts/combat_static.py`) |
| AttackTime in MoveCharacter, end-of-attack switch | `0x013a9036..0x013a90b7`, `0x013aea7a`, `0x013af035` | static |
| Per-step attack effects (sets the AttackTime limit 15) | `0x013966ea` | static |
| Action packet 0x78/0x79 (attack of another character) | `0x01222f53` in `0x01222b6d` | static |
| Magic receive / position-skill receive | `0x01253a92` / `0x0125c7b0` | static |
| SkillAction(c, skill, action, alternative), SetPlayerMagic(c, skill), attack start | `0x012b001a`, `0x013944d9`, `0x01392afd` | static |
| CreateArrows / CreateArrow | `0x0158d5bd` / `0x0158cf57` | static |
| CreateEffect (pool of 200 × `0x3d8` at `0x0a4ca430`), MoveEffect | `0x013c0f19`, `0x0142fd09` | static (cases read through `swres.py`, a jump-table resolver) |
| Damage packet | `0x01224455` | static |
| Damage colour (type, key, colour, flag a, flag b) | `0x01691738` | verified |
| Damage scale (type) | `0x01691bbe` | verified |
| ShowDamage (key, position, colour, scale, info) | `0x00a01a25` | verified |
| CreatePoint, MovePoints, RenderPoints (pool of 1000 × `0xb4` at `0x0a3ae150`) | `0x016912ae`, `0x016914a0`, `0x0169159e` | verified |
| RenderNumber (position, value, colour, alpha, scale, skew) | `0x0184cd2f` | verified |
| RenderSpriteUV (bitmap, position, w, h, uv, light, alpha, skew) | `0x0184ca6b` | static (its arguments are compared) |
| Thousands formatter | `0x016b8b26` | static |
| SetPlayerShock(c, damage, type) | `0x0138f92f` | static; its monster predicate `0x0139f3a0` verified |
| Die packet | `0x01234585` | static |
| Dead counter in MoveCharacter, SetPlayerDie(c) | `0x013a87c4..0x013a8819`, `0x01393a61` | static |
| Dead fade and removal (c, o, model) | `0x013a5ea1` | verified (default path) |
| Object alpha step | `0x012af883` | static |

Layouts used here (static, consistent with the earlier reconstructions):

- Character: `+0x04` safe-zone byte, `+0x12` class byte, `+0x21` AttackTime, `+0x23` Dead counter, `+0x26` skill
  (word), `+0x28` attack counter, `+0x38` movement, `+0x40` target index (word), `+0x146` monster class (word),
  `+0x14a` last damage (word), `+0x19ac` and `+0x19ac+0x3fc` weapon item indices (words, -1 none), `+0x1a8` fade timer,
  `+0x21a4` wing type (word), `+0x3324` float, object at `+0x3254`.
- Object: `+0x08` live byte, `+0x2a` action, `+0x5c` type (`0xa91` = Player), `+0x6c` effect lifetime, `+0xa0`
  scale, `+0xd0` frame, `+0xd8` alpha target, `+0xdc` alpha, `+0xf8` direction, `+0x158` position, `+0x164` angles.

## 1. The hero's attack

### MoveHero's attack case (static)

When the hero's mouse action `c+0x39` is 3 and a character is selected (`[0x01cf1164]`), MoveHero runs
`0x01697cab`:

1. **Range in tiles.** 1; 2 when the hero's right-hand inventory item is in `0x600..0x7ff` (spears); 6 when the bow
   check `0x0139d994` (inventory item kind 8 or 9) is non-zero; 8 for an item with property `0x54`; 7 for character
   class word 9. Later rules win (`mu_hero_attack_range`).
2. **Gates.** Nothing happens when the hero is a transformed non-Player model in action 3 or 4, in the safe zone
   (`c+4 == 1`), with `c+0x38 == 1`, or when `0x0169da9c(1)` refuses.
3. **Range test** `0x016a52a6(c, x, y, range)` (verified): `range >= (float)sqrt(dx² + dy²)` over the tile
   differences (binary32 squares, CRT double square root rounded to binary32; NaN never passes).
4. **Out of range.** Classes 2 and 10 path toward the target with PathFinding2 and the range and send a move; other
   classes wait for the click handler's walk.
5. **In range.** `[0x0b437c0c] = [0x01cf1148]`, SetPlayerAttack(c), **AttackTime = 1**, the target position into
   `c+0x1ac`, the hero's heading = CreateAngle(hero, target) (`0x012aed9e`, already verified by NATIVE-PATH-001),
   `0x016a8904(0, 0)`, `c+0x38 = 0`, the target index into `c+0x40`, skill `c+0x26 = 0`, and the attack packet with
   the target key and the direction byte `((angle + 22.5) / 360 · 8 + 1) mod 8` (`mu_attack_direction`).

### SetPlayerAttack (verified)

For the Player model the routine first runs the attack-speed adjustment `0x0138d9cf` and, outside the safe zone, the
attack start `0x01392afd(c, 0, 1)`. The action (`mu_player_attack_action`) depends on the two weapon item indices
(groups of 512 from `0xae6`), the item attribute record of the right-hand weapon (present, two-handed byte `+0x253`),
the class nibble, the attack counter `c+0x28` and `rand()`:

| Weapon | Action |
|---|---|
| none | `0x6f`; classes 7, 8, 9, 12, 14: `0x70` |
| one-handed sword / axe / mace | `0x71 + counter % 2`; with a second one-handed weapon `0x71, 0x73, 0x72, 0x74` by `counter % 4`; class 9: `0x82` |
| two-handed sword / axe / mace | `0x75 + counter % 3`; items `0xafb, 0xb05, 0xafd, 0xaff`: `0x78` |
| one-handed weapon in the left hand only | `0x73 + rand() % 2` |
| staff | `0x71 + rand() % 2`; class 12: `0x70`; state `0x0129dd4a(1) == 0x72`: `0x88`; two-handed: `0xa3 + rand() % 2` |
| spear | `0x7b + counter % 3`; class 7: `0x7a`; items `0x10e7`, `0x10e8`: `0x79` |
| bow / crossbow (`0x0139d8f8` 1 / 2) | `0x7e` / `0x7f`; with wings (`c+0x21a4 != -1`) `0x80` / `0x81` |
| dual wield (`0x0139d9ed(c, 0)`) | `0x83 + (rand() % 10 == 0)`, `0x84`; with wings `0x85 + rand() % 2`, `0x86` |
| other | `0x6f`; no right-hand weapon in state 0x72: `0x87` |

The default monster branch takes action 3 when `counter % 3 == 0`, else 4, and increments the counter; the common tail
increments it again (`mu_monster_attack_action`). Model `0x7c5` chooses 3/4, 8 or 9 by `rand() % 8`; `0x2c1b` takes 3;
`0x28` takes 1. Sixteen world and event predicates can suppress the default branch.

### Attack speed (verified)

SetAttackSpeed `0x0138dc60(attack speed, magic speed)` stores the PlaySpeed of 175 Player actions (179 stores):
binary32 expressions such as the fist attacks `0x6f`/`0x70` = `0.6 + (attack speed >= 288 ? 1.148 : attack speed ·
0.004)` and the weapon attacks `0x71..0x86` = `0.25 + attack speed · 0.004` (same cap). `scripts/combat_static.py`
lifts the straight-line body (five counted loops, one two-way branch merged into a select) into
`reconstructed/combat/attack_speed_table.h`; the private test regenerates it byte for byte. Its caller `0x0138d9cf`
(static) passes the character attribute words `+0x1b6` (attack speed) and `+0x1c2` (magic speed) plus equipment
bonuses, `+20` for two state bits, and halves both under buff `0xb0`, capped by a skill-table value.

### When the hit lands (static)

The client has no animation-frame hit test for a normal attack. The attack request goes to the server when the attack
starts; the server answers with the damage packet, and the hit reaction and damage text appear when that packet is
processed. The client's own timeline is **AttackTime**:

1. AttackTime = 1 with the attack action (MoveHero for the hero; the action packet `0x78`/`0x79` and the magic
   packets for everyone else).
2. Every logic step while it is positive, MoveCharacter calls `0x013966ea` (skill-specific effects of the step; it
   stores the limit `[0x01cf1050] = 15`, a few skills change it) and increments it.
3. When it reaches the limit the target index becomes -1, AttackTime 0, and the end-of-attack switch on the base skill
   creates the visuals: arrows for the bow actions `0x7e..0x81`, the skill models and bitmaps below.

With one logic step per 40 ms, an attack lasts 14 steps (0.56 s) after its start step; the hero's next attack can start
then.

## 2. Skills (static)

The magic packet handler `0x01253a92` and the position-skill handler `0x0125c7b0` take the packet's skill number
through `0x00bb1c32` to a base skill, store the skill in `c+0x26`, the target in `c+0x40`, run the attack start
`0x01392afd(c, skill, 0)` and switch on the base skill. The skill record (getter `0x00961620` on `0x06fbb138`) is read
for: `+0x00` byte (1: only with the force flag), `+0x04` (passed to `0x01392add`) and `+0x90` type (0, 5, 7 gate the
start; 5 also exempts the facing turn). The skill text and range tables are `Skill(kor).txt` and `SkillRequire` in
the encrypted Lang.mpr package ([client-data-tables.md](client-data-tables.md)), out of reach; skill names below are
the usual names of the base numbers (inference).

Skills do **not** use the EffectManager of NATIVE-FX-002: its factory `0x00a797a0` has 15 callers (CreateMonster and
three others). They use the older effect pools: CreateEffect `0x013c0f19` (3154 call sites of its wrapper
`0x013c0eaa`, pool of 200 effects of `0x3d8` bytes at `0x0a4ca430`, moved by MoveEffect `0x0142fd09` from MoveEffects
`0x0150ddb1`), CreateParticle `0x0168fafd` (3642 sites) and CreateJoint `0x0153b02c` (838 sites). Effect types are
model indices of the skill model table (`AccessModel(index, "Data\Skill\", name, number)`, for example `0x43b` Arrow01,
`0x412` Ice01, `0x413` Fire01, `0x414` Poison01, `0x41f` Magic02, `0x455` Blast01, `0x457` Inferno01) or bitmap indices
(`0x7f2b` `Effect\Thunder01.jpg`, `0x7f84` `Effect\Magic_Ground2.jpg`, `0x7f5a` `Effect\smoke01.jpg`).

| Base skill | Receive | Action | End of attack |
|---|---|---|---|
| 1 Poison | magic | SetPlayerMagic | `0x414` + smoke particle, sound `0x22` |
| 2 Meteorite, 4 Fire Ball | magic | SetPlayerMagic | `0x413` (subtype 1 for Fire Ball), sound `0x42` |
| 7 Ice | magic | SetPlayerMagic | `0x412` + `0x41b`, sound `0x78` |
| 11 Power Wave | magic | SetPlayerMagic | three `0x41f`, sound `0x76` |
| 17 Energy Ball | magic | SetPlayerMagic | Player: `0x7f2b`, sound `0x76`; some monster models `0x437`, `0x433`, `0x50d` |
| 19..23 Falling Slash, Lunge, Uppercut, Cyclone, Slash | magic | `0x89`, `0x8a`, `0x8b`, `0x8c`, `0x8d` (then `0x77`) | sounds `0x70..0x73` |
| 24 Triple Shot | position | SetPlayerMagic (default) | two CreateArrows calls (spread ±8 / ±24°) |
| 26 Heal, 27, 28 buffs | magic | SetPlayerMagic, sound `0x6f` | Heal: `0x7f84` on the target |
| 10 Hellfire, 12 Aqua Beam, 14 Inferno | position | `0xa9`, `0xa7`, `0xa8` | in the MoveCharacter switch |
| 41 Twisting Slash, 42 Rageful Blow, 43 Death Stab | position | `0x8e`, `0x8f`, `0x9e` | in the MoveCharacter switch |

SkillAction `0x012b001a(c, skill, action, alternative)` runs the attack start and SetAction (the alternative action in
a character-state mode); SetPlayerMagic `0x013944d9` runs the speed adjustment and takes `0xa5` (class 14: `0x10e`) when
`0x00b99205(class)` is non-zero, else `0xa1 + rand() % 2`; monsters take 3/4 by the counter. For a hero caster the
generic magic case sets no action: the hero already took it when casting.

Effect initialisation read from CreateEffect's cases (resolved through the compare and jump-table tree):

- **Arrow** (CreateArrow picks the model from the arrow or bolt item, `0x43b` by default): placed at
  `AngleMatrix(angle) · (-10, -60, 135)` from the archer, LifeTime 30.
- **MODEL_FIRE** default (Fire Ball): LifeTime 60, scale `(8 + rand() % 4) · 0.1`, z + 120, direction (0, -50, 0)
  along the effect angle (toward the target).
- **`0x7f2b`** (Energy Ball, Thunder01): LifeTime 20, z + 100, direction (0, -60, 0).
- **`0x7f84`** (Heal, Magic_Ground2) at the target, LifeTime 20.

How MoveEffect moves arrows, how each effect is drawn and how projectiles meet their target were not reduced.

## 3. Monster reactions

### Damage packet (static)

`0x01224455` reads: key `packet[3..4]` (bit 15 = the shock flag), damage dword `+8`, type `packet[0x0d] & 15`,
`packet[0x0d]` bits 4..7 and `packet[0x0c]` bits 0..2 as flags, `packet[0x10] == 1`, shield damage `+0x14`. When the
shock flag is set it calls SetPlayerShock; for the hero it lowers HP and SD in the character attributes. Then the
colour (`0x01691738`), the scale (50 for `packet[0x0d]` bit 7, else `0x01691bbe`), the damage information record and
ShowDamage; a positive shield damage adds a (0.8, 1, 0) point; the damage word goes to `c+0x14a`.

### Hit reaction (static, predicate verified)

SetPlayerShock `0x0138f92f(c, damage, type)` does nothing for a dead character, in eleven Player actions (`0x8f`,
`0x9c`, `0x9f`, `0xe2`, `0xe3`, `0xdc`, `0xe0`, `0xe1`, `0x11d`, `0x126`, `0x127`), or for damage ≤ 0 unless the type
is 12 or 15. Players take hit actions `0x134..0x13a` by state; a monster takes **action 5** when `0x0139f3a0(class,
action)` allows it (verified: not during its attacks 3 and 4; class `0x2fb` not in actions ≥ 8 or 4), then plays the
hit sound of its model's sound table.

### Death, fade and removal

- **Die packet** `0x01234585` (static): Dead `c+0x23 = 1`, `c+0x38 = 0`, the killing skill into `c+0x2a`, and world-
  specific death effects.
- **Dead counter** in MoveCharacter `0x013a87c4` (static): after the animation step, a positive Dead byte is
  incremented; from 15 on SetPlayerDie `0x01393a61` runs every step. For a monster it calls SetAction(6) (special
  models choose other actions or effects); SetAction ignores the repeats. The die action starts 14 steps (0.56 s)
  after the packet, after the hit animation.
- **Fade** `0x013a5ea1` (verified on its default path), before the animation step while Dead > 0: the timer `c+0x1a8`
  grows by 0.02 per step (0.05 for model `0x7c5` in world 7; 0.01 / 0.02 for models `0x7e5`, `0x940` by `o+0x6c`);
  from 1 on the alpha `o+0xdc = 1 - (t - 1)` (model `0x819` keeps it); while alpha ≥ 0.01 the object sinks 0.4 per
  step; then a character other than the hero is removed (effects off, `c+0x2a = 0`, live byte 0, `o+0x44 = 0`, list
  removal unless a world predicate, slot freed). The fade starts 50 steps (2 s) after the packet and the removal comes
  after 100 steps (4 s).
- The object alpha step `0x012af883` (static) moves the alpha toward `o+0xd8` linearly (±0.05) or exponentially
  (`o+0xe0`), and clamps `o+0xa8`.

### The monster's attack (static)

The action packet handler `0x01222b6d` switches on `packet[6]`: actions `0x78`/`0x79` call SetPlayerAttack(c), set
AttackTime 1, clear `c+0x3324`, store the target; `0x7a`/`0x7b` call SetPlayerStop. The packet's direction byte sets
the angle `(dir - 1) · 45`.

## 4. Damage text

### Colour and size (verified)

| Condition | Colour |
|---|---|
| `packet[0x10] == 1` | (1, 1, 0); with `packet[0x0c]` bit 1: (0.99, 0.89, 0.98) |
| `packet[0x0c]` bit 1 | type 2 (0.97, 0.58, 0.93), type 3 (1, 0.96, 0.59), other (0.99, 0.89, 0.98) |
| type 0 | red (1, 0, 0) on the hero, orange (1, 0.6, 0) on others |
| type 1 / 2 / 3 / 4 / 5 / 6 / 11 | (0, 1, 1) / (0, 1, 0.6) / (0, 0.6, 1) / (1, 0, 1) / (0, 1, 0) / (0.7, 0.4, 1) / (0.5, 0.5, 0.75) |
| other | white |

Scale 50 for types 1..3, 80 for type 11, 15 otherwise. In the S6 naming types 1..4 are ignore-defence, excellent,
critical and reflected damage (inference).

### ShowDamage (verified)

Damage 0 shows one bitmap point: RESIST (type 7), BLOCK (8), PARRY (9), ABSORB (10), nothing (12), else MISS, in white
for the hero and grey (0.5) for others, scale 1. A positive damage shows one point, or stacks of two (`packet[0x0d]`
bit 6) or three (bit 7: darker colours and scales +0/+15/+25; `packet[0x0c]` bit 0: brighter), each 7 units higher,
after the offsets of `packet[0x10] == 1` (scale ×1.5), `packet[0x0c]` bit 1 (-35, -35, +25) and type 5 (z - 25).

### The rise and fade (verified)

CreatePoint `0x016912ae` takes the first free record of the 1000-record pool: position + 140 in z, gravity 10, delay
0, the floor RequestTerrainHeight + 140. MovePoints `0x016914a0` runs once per logic step: z += gravity (when the move
flag is set), gravity -= 0.3, the point dies when gravity ≤ 0, and the scale drops by 5 per step to a floor of 15
(except HIT). A point therefore lives **34 steps (1.36 s)**, rises 171.7 units, and a critical number "pops" from 50 to
15 in 7 steps. RenderPoints `0x0169159e` draws every live point with alpha = gravity · 0.4: opaque while gravity ≥ 2.5
(the first 25 steps), fading over the last 8. It sets the blend `0x0184a990` (SRC_ALPHA, ONE_MINUS_SRC_ALPHA) and turns the depth
test off; mode 1 hides points above 350, mode 2 below 300, mode 0 those under their floor.

### The font (verified)

RenderNumber `0x0184cd2f` draws values -11..-1 as one bitmap (stun `font_stun.tga` … miss `font_miss.tga`, HIT
`Hit.tga`, RESIST/BLOCK/PARRY/ABSORB `resist/block/parry/absorb.tga`; width scale · 3.2 to 6.4, height scale · 1.6 or
1.7). Other values are formatted with thousands separators (`0x016b8b26`: "%d" then ",%03d"), the start moves left by
length · 5 and by length · scale / 8 (x and y), and each digit is a scale × 1.5·scale sprite of
`Interface\font_damage.tga` (bitmap `0x7534`) at u = digit / 11 of the 11-cell strip; commas use `FontSC.tga` (`0x7dfe`)
smaller. The position advances by scale / 2 in x and y per character, so numbers run diagonally. RenderSpriteUV
`0x0184ca6b` transforms the position by the camera matrix `0x0bdc5918` and draws an eye-space quad (GL_QUADS,
`glColor4f(light, alpha)`).

## 5. Verification

`scripts/validate_combat.py --cases 3000 --heavy-cases 300` (Unicorn, strict machine of `scripts/actor_machine.py`
plus helpers for x87 returns and argument-slot writes), single private run, 47 s:

| Family | Client routine | Cases | Equal | Negative control (disagreements) |
|---|---|---:|---:|---|
| damage_color | `0x01691738` | 3000 | 3000 | hero damage in orange: 22 |
| damage_scale | `0x01691bbe` | 3000 | 3000 | criticals at 15: 175 |
| create_point | `0x016912ae` | 300 | 300 | floor without +140: 283 |
| move_points | `0x016914a0` | 300 | 300 | HIT shrinks: 263 |
| render_points | `0x0169159e` | 300 | 300 | alpha = gravity: 192 |
| render_number | `0x0184cd2f` | 3000 | 3000 | digits in a row: 1574 |
| show_damage | `0x00a01a25` (CreatePoint as client code) | 300 | 300 | one point for bit 7: 42 |
| attack_speed | `0x0138dc60` | 3000 | 3000 | no 288 cap: 1896 |
| player_attack | `0x01392bde` | 3000 | 3000 | two-handed ignored: 221 |
| in_range | `0x016a52a6` | 3000 | 3000 | Chebyshev distance: 156 |
| shock_allowed | `0x0139f3a0` | 3000 | 3000 | always reacts: 615 |
| dead_fade | `0x013a5ea1` | 3000 | 3000 | 0.05 per step: 2079 |

The pool families compare every field of all 1000 records and the bytes the client defines; the player_attack family
reached all 33 Player outcomes (actions `0x6f..0x88`, `0xa3`, `0xa4`, none) and the monster branches. Any two NaNs
compare equal (x86 SSE creates the negative indefinite NaN, AArch64 the positive default NaN; the same choice as
`scripts/validate_effects.py`). The ignored report is `evidence/native-combat/report-02.json` (SHA-256 `083bde12…2e0b`).

Portable checks: `reconstructed/combat/test_combat.py` (worked examples and independent Python statements: the
colours, the rise curve, the digit layout, ShowDamage's stacks, the attack-speed header evaluated statement by
statement in binary32, the attack actions, the death and fade timeline, the attack timer) and
`native/tests/test_native_combat.py` (the session below on synthetic data). Private: the Unicorn comparison (60 cases
per family), the regenerated header, and a Lorencia fight with installed data.

## 6. Native module and mu-world

`native/core/mu_combat.*` joins `reconstructed/combat` to the `mu_walk` session and the demo-placed actors:

- **Client behaviour.** The click on a monster selects it; MoveHero's attack case runs before the walk and click code
  (a pre-step hook in `mu_walk`); out of range the hero walks with the client path finder, in range it stops, faces
  the target and takes the SetPlayerAttack action with the SetAttackSpeed PlaySpeed; skills take their actions;
  AttackTime counts to 15 and the end of the attack creates arrows (bow actions), the Fire01 model, the Thunder01 and
  Magic_Ground2 bitmaps with their lifetimes, start points and directions. Damage packets go through the colour,
  scale, ShowDamage and CreatePoint; every step MovePoints; every frame RenderPoints, RenderNumber and RenderSpriteUV
  with the session's camera. Monsters react with SetPlayerShock's action 5, die through the dead counter (action 6),
  fade, sink and are removed; a monster's attack takes SetPlayerAttack's monster action and AttackTime.
- **Demo.** The damage (30..95, 10 % miss, 10 % critical, 10 % excellent, 5 % stacked), 260 hit points, a 4-step
  latency of the damage and die messages, the respawn 125 steps after removal, the monsters' counter-attack (within 1.5
  tiles every 50 steps), the skill ranges (2 for melee skills, 6 otherwise), repeating the attack while the target
  lives, and the picking (a cylinder of 70 × 200 units around the actor).
- **Viewer choices** (NATIVE-COMBAT-001, replaced by the client's effect code in section 8). Projectiles fly straight at their static speed and disappear at or behind their target; arrows at
  60 units per step; the Fire01 model is laid along its flight and drawn with the additive flag `0x42`; the Thunder01
  billboard is 120 units and Heal a 220-unit ground quad, both additive.

```sh
native/build/mu-world --game-root "$MU_GAME_ROOT" --placement native/world/lorencia-demo-placement.txt \
    --tile 182,127 --class 1 --combat-weapon sword          # click a monster; keys 1..6 cast skills
native/build/mu-world --game-root "$MU_GAME_ROOT" --headless --backend gl --frames 420 --every 2 --out-dir DIR \
    --placement native/world/lorencia-demo-placement.txt --tile 182,128 --class 2 --combat-weapon bow \
    --combat-script "6:attack:hound;150:skill:24:spider;300:skill:26:budge dragon"
```

Keys 1..6 cast Fire Ball (4), Energy Ball (17), Cyclone (22), Twisting Slash (41), Triple Shot (24) and Heal (26) at
the target. `--combat-weapon none|sword|twohand|spear|bow|crossbow|staff` equips a demo weapon (item index and model);
`--attack-speed`, `--combat-seed`; `--combat-script` items are separated by `;` (`F:attack:ACTOR`,
`F:skill:N:ACTOR`, `F:click:ACTOR`, `F:stop`). Headless runs add a `combat_frame` line per saved frame (hero action,
AttackTime, monsters' HP, action, Dead, alpha, z, the live points) and a `combat` summary.

**Local renders** (`~/Documents/mu-mac-tools/native/renders/combat/`, not committed): `dk-sword` (click, sword hits,
shock, death, fade, respawn), `elf-bow` (arrows, Triple Shot, Heal), `dw-spells` (Fire Ball, Energy Ball), `dk-skills`
(Cyclone, Twisting Slash, counter-attacks in red), each with a contact sheet and an MP4, and `dk-sword-soft` (the
software rasterizer; the same summary as the GL run). The window ran at 24.95 FPS (cap 25) during a fight.

## 7. Not established

- **Live comparison.** No live capture of a fight was made (no game run in this milestone).
- **Server timing.** When the damage packet arrives relative to the animation depends on the server; the demo uses a
  fixed latency.
- **Effects.** MoveEffect's arrow branch, how each effect is drawn (blend, billboard size, model orientation), impact
  effects, CreateParticle/CreateJoint visuals and the skills handled in MoveCharacter's own switch (Evil Spirit,
  Twister, Hellfire, Aqua Beam, Inferno, Twisting Slash) were not reduced (NATIVE-COMBAT-002: most reduced, section 8). The per-step attack routine `0x013966ea` is
  mapped (it sets the AttackTime limit) but its skill cases are not.
- **Skill data.** The skill table (names, ranges, mana) is in the encrypted Lang.mpr; skill names are inference.
  Whether `0x00b99205(class)` selects `0xa5` for a class, and the base-skill mapping `0x00bb1c32` for master skills,
  were not traced.
- **Player hit and death actions** (`0x134..0x13a`, `0x142..0x147`) and the sounds of hits, attacks and deaths are
  recorded only (NATIVE-COMBAT-002: reconstructed, section 8).
- **Static readings** that were not executed: the attack case of MoveHero, the receive handlers, the dead counter, the
  alpha step, the thousands formatter and RenderSpriteUV's vertex part.

## 8. The older effect system, area skills, the hero's hit and death, sounds (NATIVE-COMBAT-002)

NATIVE-COMBAT-002 swaps the display choices of section 6 for the client's own effect code
(`reconstructed/combat/skill_fx.*`) and adds the area skills, the hero's own hit and death, and the combat sounds.

### Routines

| Routine | Address | Status |
|---|---|---|
| CreateEffect, types `0x43b` (Arrow01) sub 0/2, `0x413` (Fire01) sub 1, `0x7f2b` (Thunder01) sub 0, `0x7f84` (Magic_Ground2) sub 1, `0x41c`/`0x41d` (Circle01/02), `0x457` (Inferno01), `0x421` (Laser01), `0x453`/`0x454` (Twisting Slash spawner and swirl), `0x419`/`0x41a` (Stone01/02) sub 0/1 | `0x013c0f19` | verified |
| MoveEffect, the same types: prologue (Luminosity `(rand%4+7)*0.1`), owner StartPosition, type cases, the effect-model animation, the rotated move `0x0150df8e`, lifetime | `0x0142fd09` | verified (the PlayAnimation call is compared as a call) |
| CheckClientMagic (2D distance ≤ 100 to the owner, LifeTime 1, impact: 2 stones for Fire Ball, a Spark03 burst for Energy Ball) | `0x013be199` | verified |
| CheckClientArrow (an arrow ends within 100 of a live visible character) | `0x013bd374` | static |
| Heal's three JointEnergy01 ribbons | `0x0142d83b` | verified (inside MoveEffect) |
| CreateParticle `0x7f3c` sub 0/5, `0x7f2b` sub 0, `0x7f26` sub 0/1 (core of the wrapper `0x0168fafd`) | `0x015ae7b0` | verified |
| MoveParticles, those types (time step 0.1, gravity, frame strips, scale fade) | `0x01616c80` | verified (per-particle part from `0x01616f7c`) |
| RenderParticles → RenderSprite (strip UVs, rotation, additive) | `0x0159123f`, `0x0184c39c` | verified (per-particle part from `0x015912e9`) |
| CreateJoint `0x7fd8` sub 1 (Heal), `0x7fd3` sub 0 (Evil Spirit, also the purple `0x7f5` variant) | `0x0153b02c` | verified |
| MoveJoint (MoveHumming `0x012af2f1`, tail shift `0x01553ba6`, wide spirit's Laser01 per step and area request every 15 steps, the wall stop) | `0x01556c26` | verified |
| RenderJoints (500-record pool, tail quads, UVs, render type and blend) | `0x01589b56` | verified |
| RenderEffects → RenderObject → RenderBody (flags 2 or `0x82` when `+0x80 == 0x80`, alpha `+0xdc`, BlendMesh `+0x74`, BlendMeshLight `+0xa8`, UV scroll `+0xac/+0xb0`) | `0x015181fa`, `0x016d4fe4` | static |
| Area skills in MoveCharacter's AttackTime switch: Evil Spirit 9, Hellfire 10, Aqua Beam 12, Inferno 14, Twisting Slash 41, Rageful Blow 42 | `0x013a90c0` → `0x013acd62`, `0x013abb52`, `0x013ac8a2`, `0x013acc46`, `0x013aba81`, `0x013a94a4` | static |
| Inferno ring | `0x0142da3e(pos, 0)` | static |
| Area attack request (skill, range, position, serial, key, 0, 5, 0) | `0x013bc25e` | static (reported as a call; the native demo applies damage in range) |
| SetPlayerShock, Player branch (actions `0x134/0x136/0x138/0x13a`, voices) | `0x0138f92f` | verified |
| SetPlayerDie, Player branch (actions `0x142/0x144..0x147`, voices, `+0x3324 = 0.001`) | `0x01393a61` | verified |
| SetPlayerAttack's sound tail (bow `0x55`, crossbow `0x56`, staff `0x76`, light sword `0x3e`, swords `0x3c+rand%2`; world `0x49` silent) | `0x01393924` | verified |
| Class check (class nibbles 2, 5, 7, 8, 9, 12, 14) | `0x00b99205` | verified (inside the voice family) |

Lifetimes (verified): arrow 30, Fire Ball 60, Energy Ball 20, Heal 20, Circle01 45, Circle02 40, Inferno01 15, Laser01
1, Twisting Slash spawner 5 and swirl 25, stones `rand%16+32`. Fire Ball (and the flare `0x7ef7`) decrements the
lifetime before the test; the others test first (an arrow lives 31 steps). Hellfire's Circle01 and Inferno01, when the
hero owns them, take the hero's skill serial and request an area attack of range 300 and 400; Evil Spirit's wide
spirits request one of range 150 every 15 steps.

### Verification

`scripts/validate_skill_fx.py --cases 3000` (Unicorn, `scripts/actor_machine.py` strict regions, the x87 and libm
helpers of `scripts/validate_combat.py`), single private run, 34 s; it reports the SHA-256 of 12 routine bodies (for
example CreateEffect `55df5b8b…`, MoveEffect `972e9d6b…`, CreateParticle `c0c5836e…`, RenderSprite `58680480…`):

| Family | Client routine | Cases | Equal | Negative control (disagreements) |
|---|---|---:|---:|---|
| effect_create | `0x013c0f19` (15 type/subtype pairs × 200) | 3000 | 3000 | arrow speed 60: 400; Energy Ball not lifted: 199 |
| effect_move | `0x0142fd09` | 3000 | 3000 | decrement first: 244; unrotated move: 2582 |
| check_magic | `0x013be199` (217 hits) | 3000 | 3000 | 3D distance: 193 |
| particle_create | `0x015ae7b0` | 3000 | 3000 | Fire01 scaled by the argument: 484 |
| particle_move | `0x01616c80` | 3000 | 3000 | rise without the ×10: 706 |
| particle_render | `0x0159123f` + `0x0184c39c` | 3000 | 3000 | full-width strip: 972 |
| joint_create | `0x0153b02c` | 3000 | 3000 | first tail from the new width: 2574 |
| joint_move | `0x01556c26` | 3000 | 3000 | forward along +y: 2214 |
| joint_render | `0x01589b56` | 3000 | 3000 | UVs over the drawn tails: 849 |
| player_voice | `0x0138f92f`, `0x01393a61`, `0x01393924` | 3000 | 3000 | always action 5: 630 |

The ignored report is `evidence/native-combat/report-skillfx-01.json` (SHA-256 `eab5ebc7…d539`). Portable checks:
`reconstructed/combat/test_skill_fx.py` (worked examples: the bow offset, the arrow's 31 steps, Fire Ball's 60, Energy
Ball's light, the hit check, the area lifetimes, Fire01's strip and rise, Spark03's scale death, the joints' first
tail and ribbon UVs, the voices and swing sounds) and `native/tests/test_native_combat.py` (area skills, the hero's hit,
death at Dead 15 and respawn); private: the Unicorn comparison (60 cases per family).

### Native module and mu-world

- **Client behaviour.** `native/core/mu_combat.*` keeps the three pools (200 effects, 2048 particles, 500 joints) and
  moves them each logic step in the client order (effects, joints, particles); the end of the attack creates what the
  client's blocks create (arrows, Fire01, Thunder01, Magic_Ground2, Evil Spirit's eight spirits, Hellfire's circles,
  Inferno's ring and Inferno01, the Twisting Slash spawner) with the client's sounds; effect lights go to the terrain
  light grid (AddTerrainLight `0x016cacfc`); effect models draw with RenderObject's flags, alpha, blend mesh and UV
  scroll; particles as RenderSprite quads; joints as their tail quads with the client blend of each render type. The
  hero's hits and death run SetPlayerShock/SetPlayerDie (action, voice; death from Dead 15). Sounds go through
  `reconstructed/audio` (SND_Play by the sound table index): swings, bow and crossbow, casts (`0x42`, `0x75`, `0x77`,
  `0x73`, `0x95`), the hero's voices.
- **Demo.** A projectile's damage arrives at its hit check (40-step deadline), area damage at the client's area
  requests within their range, Twisting Slash within 250 units; the hero's 400 hit points (`--hero-hp`), and a
  respawn at the home tile 100 steps after death.
- **Viewer choices.** Effect models play their first action at the client speed; Triple Shot's spread of ±8 degrees
  is static.

Keys 7, 8, 9, 0 cast Evil Spirit (9), Hellfire (10), Inferno (14) and Cyclone (22) besides keys 1..6.

**Local renders** (`~/Documents/mu-mac-tools/native/renders/combat2/`, not committed; contact sheet, MP4 with the
session's sound): `dw-spells` (Fire Ball with its fire trail and stones, Energy Ball, Evil Spirit), `dw-area`
(Hellfire's pentagram and fire, Inferno's ring), `elf-bow` (Triple Shot fire trails, Heal's blue ribbons, arrows),
`dk-swirl` (Twisting Slash, Cyclone), `hero-death` (hits, voice, death pose, respawn).

### Not established (NATIVE-COMBAT-002)

- **Live comparison.** None: Nighty stands in a PvP area, so no fight was run.
- **CreateSprite** `0x01692eb7` (Heal's flash, the swirl's flare) is not reconstructed; the swirl's smoke and spark
  particles (`0x7f5a` sub 3, `0x7f25`) and `0x7fd5` joints, the stones' Fire01 subtypes 1..3 and Inferno's burst
  `0x013c07f4` are counted as unsupported and not drawn.
- **Monster sounds** (hurt and death come from the model's sound slots from `+0xb6`) are not wired (NATIVE-ITEMS-001:
  reconstructed, verified and wired, [client-ground-items.md](client-ground-items.md#6-monster-hurt-and-death-sounds-verified)); skeleton-form and
  transformed-ring voices are excluded; the arrow skills `0x7e7`, `0x7fc`, `0x7fd`, `0x2d8` are not reduced.
- **Static readings**: RenderObject's draw of effect models, the swirl's draw of the caster's weapon
  (`0x015332ac`), CheckClientArrow, the AttackTime switch cases and the Inferno ring.

### NATIVE-JOINT-001

The joint code moved to `reconstructed/joints` (one implementation; `mu_sfx_joint` is `mu_jt_joint` and the
`mu_sfx_joint_*` functions wrap `mu_jt_*`). `mu_combat` creates, moves and draws its joints through
`native/core/mu_joints.*`, so the Twisting Slash swirl's spark streaks `0x7fd5` draw (Spark01). Correction: Heal's
arrival flash is CreateSprite(Shiny02, …, blend 0, axes 4), not (…, 0, 0). See [client-joints.md](client-joints.md).

## Reproduce

```sh
make -C reconstructed/combat && make -C native && make -C native world
./tools/python/bin/python scripts/combat_static.py --emit-c reconstructed/combat/attack_speed_table.h
./tools/python/bin/python scripts/validate_combat.py --cases 3000 --heavy-cases 300 --output /new/local/report.json
./tools/python/bin/python scripts/validate_skill_fx.py --cases 3000 --output /new/local/report-skillfx.json
python3 -m unittest discover -s reconstructed/combat -p 'test_*.py'
python3 -m unittest native.tests.test_native_combat
```


## 9. SESSION-COMBAT-001, 2026-10-28

### Scoped routing, static evidence

Only the two owner-authorized reverse lookups were performed. In the pinned capture09 text, the dispatcher
prefix at `0x01287eed..0x01287f0a` bounds the opcode to `0xfd` and indexes `0x0128e59d + opcode * 4` directly.
The lookup compared table destinations against the call blocks for the two requested handler addresses.
Only the matching blocks and their two seed rows are retained. No dispatcher generator, table export,
sub-dispatch recovery or other routing changes belong to this milestone.

| Opcode | Slot address | Selected block | Handler call | Handler |
|---|---|---|---|---|
| `F3` | `0x0128e969` | `0x012885f7` | `0x012885fa` | `0x01224455` |
| `C5` | `0x0128e8b1` | `0x01288613` | `0x01288619` | `0x01222b6d` |

These two rows in `native/net/dispatch.seed.def` remain `MU_STATIC`. Body comparisons do not promote routing
evidence to a full dispatcher comparison. Existing `17`, `16`, `20` and `A4` seed rows are reused unchanged.
Within the action body, only action bytes `78` and `79` were selected: the selector bytes at `0x0122385b/5c`
both select case 1 at `0x01222f53` through `0x0122374d`. Other actions remain ignored by this domain.

### Instruction comparisons, verified within the stated bounds

`native/session/domains/combat_wire.c` contains the record writes and pre-transform request construction.
`scripts/validate_session_combat.py` executes the captured bodies with synthetic records and independent service
stubs, fresh per family and mutant run. Die/action reset fields start nonzero. Its AddData stub records plaintext inputs and checks the encode argument; neither keyed AddData,
receive decode nor the Send wrap is executed. The action switch now executes its real two selected branches;
the interrupted WIP had jumped directly to the case and tested only action `78`.

| Family | Original entry | Cases | Compared output |
|---|---|---:|---|
| Damage | `0x01224455` | 1,000 | key/shock/type/flags, last-damage word, hero HP/SD subtraction and clamp |
| Die | `0x01234585` | 1,000 | dead/movement/reset fields, killing-skill byte and skill 40/59/392 flag |
| Action `78/79` | `0x01222b6d` | 1,000 | no-target direction, position snap, attack-time, voice reset and target index |
| Attack request | `0x016b6214` | 1,000 | blocked gate, opcode `43`, target bytes, action `78`, direction, Send flags |
| Position cast | `0x016b6361` | 1,000 | `D7` and type-11 `C9`, coordinates, skill byte, encrypted Send flag |
| SendMove | `0x016b5cd0` | 1,000 | counts 0..15, clamp to 14, path nibbles, final direction, delay and Send flags |

Total 6,000 comparisons, zero mismatches; all six compiled planted mistakes fail. Mutants change the damage
word, dead byte, attack-time byte, attack opcode, cast opcode and move start coordinate. The existing combat
families also pass: 25,200 comparisons, 12/12 mutants; skill/effect families 33,000 comparisons, 20/20 mutants.
The latter includes the required 30,000 effect cases plus 3,000 player-voice cases. All have zero mismatches.
The text/data hashes in Identity are unchanged. Reports are local under
`~/Documents/MTM/mu-mac-tools/native/scratch/session-combat-001/`.

Engine/UI/effect services and their event/world predicates are stubbed in the new body comparator. Damage
uses the packet flag-8 text branch; the existing combat families cover the other text scales. Action target
geometry is supplied to the body; session tests separately exercise facing a known target and both action bytes.
The new comparator verifies the no-target original path. Special-world side effects, the rest of the action
handler, target-based cast variants and live behavior remain outside the claim.

### Session, fixture and presentation

The combat domain owns ordered damage/die/action/drop outputs, a bounded event history with explicit loss,
and the combat fields absent from the current CHARACTER projection. It projects/restores existing CHARACTER
fields through the layout adapters. Damage never causes death. The world combat part submits attack/cast/move
intents and renders session results. Both local kill paths are gone: combat no longer generates damage/death,
experience or quest kills, and ground items no longer watch combat dead flags to invent drops. Projectile and
area effect completion produces presentation only.

`fixture/behaviors/combat.c` owns synthetic HP, damage rolls, latency, counters, respawn and rewards. Its
attack/move requests use a fixture-only plaintext callback before the fixture's legacy decode path. The session
checks the actual in-process fixture transport, so a loopback TCP address alone cannot send these bytes.
Casts are journaled with `needs_crypto` and remain unsent without entering keyed transformation or encryption.
Product combat requests are likewise journaled unsent. The existing hero domain's plaintext `16` refusal/report
is preserved: this scenario observes an experience frame and its unsent report, not a plaintext experience gain.

`combat-fight.scn` joins the discovered VERIFY-SESSION suites and checks attack, action, damage, die, `16`, `20`
and quest `A4` frames, zero unbound/undecodable, one consumed request, two unsent requests and one quest kill.
Portable tests also check malformed-frame atomicity, damage without death, known/absent targets and event loss.
Ground ownership/pickup remains SESSION-ITEMS-001; `20` currently hands validated rows to the existing view.
Remote HP bars use only session viewport HP/max values. The synthetic viewport has zero HP/max, so its bar
remains zero instead of estimating HP from damage. The separate HP-update route was not recovered or bound.
The old character fixture now emits the complete nine-byte die frame. The seed-only combat transport check
has one explicit include-audit allowance; product-library checks still reject fixture symbols.

Intentional output changes: combat frame timing and RNG ownership now follow the fixture, cast visuals cannot
kill while their encrypted requests are unsent, remote HP is no longer fabricated, the synthetic drop is one Short Sword row, and respawn reaches
the view one poll after the server emits it. Native regression expectations record those changes. Existing
render/hash fixtures outside the fight remain required by the full local gate. No live client was used.
