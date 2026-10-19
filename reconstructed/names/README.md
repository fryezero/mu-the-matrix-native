# Overhead names (NATIVE-NAMES-001)

Authored C port of the game side of the client's GFx movie `hudPlayerName`: name plates, the monster name/HP box and
chat bubbles. See [the finding](../../docs/research/client-overhead-text.md) for addresses, evidence levels and limits;
`native/core/mu_names.*` and `native/core/mu_world_names.*` use this library in the walk-around world.

| Function | Client routine | Evidence |
|---|---|---|
| `mu_hn_window_init` | handler constructor `0x00afaff8` | static |
| `mu_hn_add_info`, `mu_hn_info_json` | addInfo `0x00c82fd1` | verified |
| `mu_hn_update` | per-frame update `0x00c81d1e` (character part) | verified |
| `mu_hn_head_height` | `0x00c8526e` | verified |
| `mu_hn_name_text` | name builder `0x00c84d8a` | verified |
| `mu_hn_class_color`, `mu_hn_pk_color`, `mu_hn_guild_color` | `0x00c84f00`, `0x00c8502c`, `0x00c85093` | verified |
| `mu_hn_gens_frame`, `mu_hn_strife_gens`, `mu_hn_guild_text` | `0x00c84d08`, `0x00c851f4`, `0x00c8510c` | verified |
| `mu_hn_set_hp`, `mu_hn_remove`, `mu_hn_select` | `0x00c83afa`, `0x00c83a04`, `0x00c83c9a` | verified |
| `mu_hn_set_monster_view`, `mu_hn_track_selection` | `0x00c83c86`, `0x009a1618` | static |
| `mu_hn_chat_bubble` | `0x0169d87f` with setMessage `0x00c83d2a` | verified |
| `mu_hn_chat_route` | chat receive `0x00c6066a` | static |
| `mu_hn_monster_kind` | SetMonsterInfo `0x013b8ade` (kind; table lifted) | verified |

Build with `-ffp-contract=off` (binary32 operations in source order).

```sh
make -C reconstructed/names
python3 -m unittest discover -s reconstructed/names -p 'test_*.py'
MU_RECOVERY_INTEGRATION=1 python3 scripts/validate_names.py --cases 1000 --negative 100
```
