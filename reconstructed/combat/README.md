# Combat (NATIVE-COMBAT-001, NATIVE-COMBAT-002)

Authored C ports of the client's combat routines: floating damage text, attack speed, attack actions, the in-range
test, the monster hit predicate, the dead fade, plus static readings of the attack timeline, the death counter and the
skill-to-visual mapping; and (NATIVE-COMBAT-002, `skill_fx.*`) the older effect system that draws skills and
projectiles (effects, particles, joints), the area skills' effects and the hero's hit/death actions and voices. See [the finding](../../docs/research/client-combat.md) for addresses, evidence levels and
limits; `native/core/mu_combat.*` uses this library in the walk-around world.

| Function | Client routine | Evidence |
|---|---|---|
| `mu_damage_color`, `mu_damage_scale` | `0x01691738`, `0x01691bbe` | verified |
| `mu_point_create`, `mu_points_move`, `mu_points_render` | CreatePoint `0x016912ae`, MovePoints `0x016914a0`, RenderPoints `0x0169159e` | verified |
| `mu_render_number`, `mu_format_thousands`, `mu_sprite_corners` | RenderNumber `0x0184cd2f`, formatter `0x016b8b26`, RenderSpriteUV `0x0184ca6b` | verified / static / static |
| `mu_show_damage` | ShowDamage `0x00a01a25` | verified |
| `mu_set_attack_speed` (`attack_speed_table.h`, generated) | SetAttackSpeed `0x0138dc60` | verified |
| `mu_player_attack_action`, `mu_monster_attack_action` | SetPlayerAttack `0x01392bde` | verified |
| `mu_player_magic_action` | SetPlayerMagic `0x013944d9` | static |
| `mu_in_range`, `mu_hero_attack_range`, `mu_attack_direction` | `0x016a52a6`; MoveHero's attack case `0x01697cab` | verified / static / static |
| `mu_monster_shock_allowed`, `mu_shock_action` | `0x0139f3a0`; SetPlayerShock `0x0138f92f` | verified / static |
| `mu_dead_step`, `mu_dead_fade` | MoveCharacter `0x013a87c4`; `0x013a5ea1` | static / verified |
| `mu_attack_time_step`, `mu_skill_visual_*` | MoveCharacter's AttackTime and end-of-attack switch (incl. the area skills `0x013a90c0`) | static |
| `mu_sfx_effect_create`, `mu_sfx_effect_move`, `mu_sfx_effect_advance` | CreateEffect `0x013c0f19`, MoveEffect `0x0142fd09`, `0x0150df8e` | verified |
| `mu_sfx_check_magic` | CheckClientMagic `0x013be199` | verified |
| `mu_sfx_particle_create`, `mu_sfx_particle_move`, `mu_sfx_particle_render`, `mu_sfx_sprite_corners` | `0x015ae7b0`, MoveParticles `0x01616c80`, RenderParticles `0x0159123f` / RenderSprite `0x0184c39c` | verified |
| `mu_sfx_joint_create`, `mu_sfx_joint_move`, `mu_sfx_joint_render` | CreateJoint `0x0153b02c`, MoveJoint `0x01556c26`, RenderJoints `0x01589b56` | verified |
| `mu_player_shock`, `mu_player_die`, `mu_player_attack_sound`, `mu_class_check` | SetPlayerShock `0x0138f92f`, SetPlayerDie `0x01393a61` (Player branches), `0x01393924`, `0x00b99205` | verified |

Build with `-ffp-contract=off` (binary32 operations in source order); `sqrt` uses host libm in place of the CRT.

```sh
make -C reconstructed/combat
python3 -m unittest discover -s reconstructed/combat -p 'test_*.py'
./tools/python/bin/python scripts/combat_static.py --emit-c reconstructed/combat/attack_speed_table.h
MU_RECOVERY_INTEGRATION=1 ./tools/python/bin/python scripts/validate_combat.py --cases 3000 --heavy-cases 300
./tools/python/bin/python scripts/validate_skill_fx.py --cases 3000
```
