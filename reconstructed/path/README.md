# Click-to-move path finding and following (NATIVE-PATH-001)

Authored C ports of the client routines between a terrain click and the hero's
walk. Every function equals the client's instructions on the compared domain
(`scripts/validate_path.py`, Unicorn over the pinned restored text). See
[the finding](../../docs/research/client-path.md) for addresses, evidence
levels and limits.

| Function | Client routine |
|---|---|
| `mu_path_find` | FindPath `0x012b1c45` with its target marking `0x012b2584`, BuildPath `0x012b21c6` (flag 0), reset `0x012b2515` and the tree queue (insert `0x012b198d`, pop-minimum `0x012b240a`, remove/clear `0x01212a40..0x01213189`) |
| `mu_path_finding2` | PathFinding2 `0x012b0e85` (retry rule, 15-node `PATH_t`) |
| `mu_path_heuristic`, `mu_path_step_cost` | `0x012b1bcf`, `0x012b1b67` |
| `mu_path_move` | MovePath `0x012b0846` |
| `mu_path_create_angle`, `mu_path_angle_difference`, `mu_path_turn_angle` | `0x012aed9e`, `0x012af218`, `0x012aefff` |
| `mu_path_step_position` | MoveCharacterPosition `0x0137b351`, horizontal step |
| `mu_path_clear_characters`, `mu_path_stamp_character` | MoveCharacters `0x0137a7ce`, occupancy loop |

The client's queue is an unbalanced binary search tree whose pop order is
(cost, insertion order); the port uses a binary heap with that key. Build with
`-ffp-contract=off`. The square root is `(float)sqrt((double)x)` and the
arctangent `(float)atan((double)x)`, as in the client's float wrappers; host
libm agreed with the client's CRT on every compared case.

```sh
make -C reconstructed/path
python3 -m unittest discover -s reconstructed/path -p 'test_*.py'
MU_GAME_ROOT=... python3 scripts/validate_path.py --cases 1000 --mutations --worlds all
```

The validator reads `MU_CLIENT_TEXT`, `MU_IMAGE_DATA`, `MU_TRIG_FLAG` and
`MU_PATH_DIRECTIONS` (an unpacked capture of the third section that holds the
neighbour table `0x01cf1640`). Installed attribute maps come through
`native/build/mu-path att`.
