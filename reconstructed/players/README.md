# Other players: the client side of the player viewport (NATIVE-PLAYERS-001)

Platform-neutral C for the routines the client runs when the server tells it about another player, changes that
player's equipment, moves it or removes it. Finding: [docs/research/client-remote-players.md](../../docs/research/client-remote-players.md).

| Routine | Address | Function | Status |
|---|---|---|---|
| packet class byte -> class byte | `0x0139ca62` | `mu_rp_class_byte` | verified |
| item level code (0..7 -> 0, 3, 5, ... 15) | `0x01395741` | `mu_rp_item_level` | verified |
| class tier / default part skin | `0x0139cb8a`, `0x0139d6a2` | `mu_rp_class_index`, `mu_rp_class_skin` | verified |
| wing switch (equipment code -> item type, level) | `0x0137c7df` | `mu_rp_wing` | verified |
| ride state byte | `0x0129dc91` | `mu_rp_helper_state` | verified |
| ChangeCharacterExt (18 equipment bytes -> part slots) | `0x0137b68c` | `mu_rp_change_equipment` | verified (helper codes 0x20..0x80; 0xa0 inferred) |
| move packet, opcode 0x3d | `0x0126568e` | `mu_rp_move_packet` | verified (model 0x7d9 and the hero's auto-move list static) |
| MoveCharacters' remote step | `0x013b852a` | `mu_rp_move_step` | verified (dead model 0x7a7 static) |
| player viewport record, opcode 0x12 | `0x0122d413` | `mu_rp_viewport_record`, `mu_rp_viewport_apply`, `mu_rp_viewport_pose_action` | static |
| character create defaults | `0x0137d8a1` | `mu_rp_character_create` | static |
| viewport destroy, opcode 0x14 / DeleteCharacter | `0x01232986` / `0x0137c457` | `mu_rp_destroy_keys`, `mu_rp_delete_character` | static |
| store packets, opcode 0x3f / setStore | `0x0122e4da` / `0x00c84731` | `mu_rp_store_records`, `mu_rp_store_id_html` | static |

The routines take a `mu_rp_character` (the CHARACTER / OBJECT fields they read and write, client offsets in the
header) and an `mu_rp_env` with the engine services they call (the path finder, MovePath, SetPlayerWalk/Stop,
MoveCharacterPosition, SetAction); every engine call is also recorded in an `mu_rp_calls` list in the client's order.

* `make` builds `libremoteplayers.{dylib,so}` for the validator; the native build compiles `remote_players.c` into
  `libmunative.a`.
* `test_remote_players.py`: portable worked examples (ctypes).
* `scripts/validate_players.py`: the Unicorn comparison with the client's instructions (private captures).
* `native/core/mu_world_players.*`: the native session's use (demo server, models, plates).
