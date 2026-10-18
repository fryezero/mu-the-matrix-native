# Character-select scene (NATIVE-CHARSEL-001)

Authored C for the client routines of the character-select scene (scene state 5). See
[the finding](../../docs/research/client-character-select.md).

| Routine | Address | Reconstruction |
|---|---|---|
| CGMCharacterScene_Ex constructor (vectors) | `0x00daa127` | `mu_charsel_scene_init` |
| CGMCharacterScene_Ex::CreateObject (slot markers 13..17) | `0x00daa2b2` | `mu_charsel_create_object` |
| SetCharacterPosition (marker 1 for every slot) | `0x00da9ff3` | `mu_charsel_set_character_position` |
| SetCharacterScale (1.7 in scene 5) | `0x01394f6f` | `mu_charsel_character_scale` |
| CreateHero | `0x0137f824` | `mu_charsel_create_hero` |
| RenderCharacterScene (lights, heights, shown character, selection highlight) | `0x018576b3` | `mu_charsel_render` |
| scene-5 logic tick (Enter/Esc selection logic) | `0x01856e6c` | `mu_charsel_tick_step` |

Characters are client-layout byte images (0x3670-byte records). Calls into other subsystems are logged
(`mu_charsel_log`) with their arguments instead of executed, and the values they return are inputs.
`scripts/validate_charsel.py` runs the client's instructions in Unicorn and compares the logs, every record
byte, the scene and map objects, the written globals and the return values. The camera of the scene is the
record path of MoveMainCamera in `reconstructed/camera` (`scene_angle`/`scene_position`).

`make` builds `libcharsel`; `test_charsel.py` holds the portable checks and the opt-in private comparison.
