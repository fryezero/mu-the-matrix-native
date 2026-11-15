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

This census says what a row requests. It is static evidence. The ordered arguments, default words,
sound sites and frame gates of an admitted group are compared with the original instructions by
that group's verifier.

## Classification of the 37 rows

Full table: [skill-catalogue-classification.csv](skill-catalogue-classification.csv) (one line per
row: bodies, ordered receive and step/end requests, services, missing consumers, aliases).

27 of the 37 rows select the default step and both default end bodies. Their visual is in a receive
slice (as for skill 2044), or absent. The other ten have their own step or end body.

| Group | Rows | Members | What the row needs |
|---|---:|---|---|
| A caster-frame | 8 | DK 740; Elf 77, 651, 652, 727, 740, 2023, 2025 | Receive slice with at most one pose, one caster-owned effect at the caster's position, angle and light, and one sound. Constant words; 727, 2023 and 2025 pass the source key |
| B bone-frame buff | 3 | DK 1500, 1502, 1503 | Receive slice: pose `0x9c` (alternative `0x11d`), one target-owned effect at the source model's bone 17. A mount service can replace the position |
| C triple storm | 6 | DK and Elf 1125, 1126, 1127 | Receive slice: one target-owned effect and two unowned ground effects with computed positions |
| D heal family | 4 | Elf 234, 425, 430, 2024 | Receive slice: caster effect `0x8021`, pose `0xd9` or `0x106`, sound, one target effect. 234 also has a joint, four ground effects and a position case |
| E existing end body | 3 | Elf 432, 2026, 2027 | The buff start `0x0125594d` (sound `0x6f`, SetPlayerMagic) and an end body: 432 uses the summon end `0x013a9449` |
| F arrows | 4 | Elf 46, 235, 427, 2047 | Bow or penetration pose and an arrow or volley caller; 235 and 427 share a seven-effect volley block |
| G own step or end body | 5 | DK 232, 723, 1501, 2040, 2043 | Own attack-step body (723) or area-end body (232, 2040, 2043), hand trace |
| H mount context | 2 | DK 76, Elf 76 | Mount pose helper `0x0106c453` and a mounted end body; out of scope with Fire Breath |
| I no receive case | 2 | DK 813, Elf 426 | No case in either receive switch, default step and both default ends: nothing to request |

Aliases that map onto catalogue rows (not admitted by a shared base, as in EFFECTS-030): DK 807,
809, 1202 -> 232; 1072 -> 723; 801, 802 -> 1500; 1203 -> 1501; 810 -> 1502; 803..806, 1204 -> 1503;
Elf 441 -> 77; 411, 431, 1083 -> 235; 429, 1227 -> 426; 434 -> 427; 433, 1230 -> 430; 1085 -> 727;
1222 -> 2023; 876, 1223 -> 2025; 1224 -> 2026; 1225 -> 2027; and for both classes 1129, 1133, 1196,
1199 -> 1125; 1130, 1134, 1197, 1200 -> 1126; 1131, 1135, 1198, 1201 -> 1127.

## Missing consumers

[skill-catalogue-missing-consumers.csv](skill-catalogue-missing-consumers.csv) lists the 39 effect
and joint ids that these rows request and that the native consumers do not admit
(`mu_sfx_effect_kind_supported`, `mu_jt_kind_supported`), with the requesting rows. 34 are effects
and 5 are joints; the two Plasma Storm joints have a computed subtype. Requests whose consumer
exists today: effect `0x70a/0` (2023), `0x7f84/3` (432, 2026), `0x10e6/1` and `0x461` (723, 232,
2043). Arrow callers (46, 2047 and the default end) are checked by their verifier, not by this list.
