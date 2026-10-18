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
| `mu_move_set_action` | SetAction `0x012affa4` |
| (path finder) | Moved to [`reconstructed/path`](../path/README.md) (NATIVE-PATH-001), the single port of PathFinding2 `0x012b0e85` / FindPath `0x012b1c45`; `native/core/mu_walk.c` uses it. `scripts/validate_movement.py` still runs its path family against that library |
| `mu_player_run_counter`, `mu_player_stop_run_counter` | The run-counter prefix of SetPlayerWalk `0x0139002a..0x01390455` and SetPlayerStop's reset (NATIVE-PATH-002; compared by `scripts/validate_path.py`, families `run` and `speed_state`) |
| `mu_buff_set_has`, `mu_mount_from_buffs`, `mu_world_safe_zone_runs`, `mu_world_gloves_run`, `mu_world_forces_run`, `mu_class_never_runs`, `mu_pet_slots_ride`, `mu_move_speed_input_from` | The predicates: buff lookup `0x01295ade`, buff mount `0x0106c5e9`, worlds `0x00e0558b`/`0x016a88d3`/`0x009dacb8`, class values `0x0139bd24`, riding pet `0x0139fcbf`; CharacterMoveSpeed's input from character fields (family `predicates`) |
| `mu_player_walk_run`, `mu_player_walk_action`, `mu_player_stop_action`, `mu_player_stop_speed` | The unarmed, unmounted case of SetPlayerWalk `0x0139002a` and the stop selector `0x01391e55`, plus the stand PlaySpeeds of the player loader block `0x018311f7..0x018321e1` (tables taken under emulation for every class byte; isolated so the NATIVE-ACTOR-001 action tables can replace them) |

Build with `-ffp-contract=off` (binary32 operations in source order).
`atan`, `sqrt` and `sin` use host libm in place of the CRT wrappers; they
agreed on every compared case.

```sh
make -C reconstructed/movement
python3 -m unittest discover -s reconstructed/movement -p 'test_*.py'
MU_RECOVERY_INTEGRATION=1 python3 scripts/validate_movement.py --text ... --data ... --cases 1000 --mutations
```
