# Hero movement (NATIVE-WORLD-001)

Authored C ports of the client routines that walk the hero. Every function
equals the client's instructions on the compared domain
(`scripts/validate_movement.py`, Unicorn over the pinned restored text). See
[the finding](../../docs/research/native-world.md) for addresses, evidence
levels and limits.

| Function | Client routine |
|---|---|
| `mu_create_angle`, `mu_far_angle`, `mu_turn_angle2` | CreateAngle `0x012aed9e`, FarAngle `0x012af218`, TurnAngle2 `0x012aefff` |
| `mu_move_path` | MovePath `0x012b0846` (path spline, tile update, turn toward the spline point) |
| `mu_request_terrain_height` | RequestTerrainHeight `0x016cc9e2` |
| `mu_character_move_speed` | CharacterMoveSpeed `0x013957b5` (subsystem predicates as inputs) |
| `mu_move_character_position` | MoveCharacterPosition `0x0137b351` (speed as input) |
| `mu_set_action` | SetAction `0x012affa4` |
| `mu_player_walk_run`, `mu_player_walk_action`, `mu_player_stop_action`, `mu_player_stop_speed` | The unarmed, unmounted case of SetPlayerWalk `0x0139002a` and the stop selector `0x01391e55`, plus the stand PlaySpeeds of the player loader block `0x018311f7..0x018321e1` (tables taken under emulation for every class byte; isolated so the NATIVE-ACTOR-001 action tables can replace them) |

Build with `-ffp-contract=off` (binary32 operations in source order).
`atan`, `sqrt` and `sin` use host libm in place of the CRT wrappers; they
agreed on every compared case.

```sh
make -C reconstructed/movement
python3 -m unittest discover -s reconstructed/movement -p 'test_*.py'
MU_RECOVERY_INTEGRATION=1 python3 scripts/validate_movement.py --text ... --data ... --cases 1000 --mutations
```
