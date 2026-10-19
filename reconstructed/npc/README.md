# reconstructed/npc (NATIVE-NPC-001)

The client side of talking to an NPC, restated in C from the pinned restored text
(capture09 `2bd5f2e9…3724`) and second section (run10 `c985e2e6…a0672f`). Finding:
[docs/research/client-npc-interaction.md](../../docs/research/client-npc-interaction.md).

| File | Client routine | Status |
|---|---|---|
| `npc_talk.c` `mu_npc_talk_result` | ReceiveTalk `0x01280659` (talk answer → window per result code, sounds, cursor) | verified (Unicorn, every result byte) |
| `npc_talk.c` `mu_npc_talk_window` | the same dispatch as a window table for hosts | derived |
| `npc_talk.c` `mu_npc_repair_shop`, `mu_npc_talk_refusal` | MoveHero's talk case `0x0169901c` (repair flag, local refusals) | static |
| `npc_pick.c` `mu_pick_axis_overlap`, `mu_pick_segment_obb` | `0x01850d88`, `0x018500bf` (segment/OBB separating axes) | verified |
| `npc_pick.c` `mu_npc_pick` | the character pick `0x016b47bf(kind)` | verified |
| `character_box_table.h`, `mu_character_box` | box section of the character create `0x0137d8a1` | executed table (Unicorn) |
| `mu_character_obb` | the transform's box `0x012b5bde` (CLIENT-SKIN-001), bounds mode != 2 | static use of a verified routine |

```sh
make -C reconstructed/npc                                    # libnpc
python -m unittest discover -s reconstructed/npc -p 'test_*.py'
tools/python/bin/python scripts/validate_npc.py --mutations  # Unicorn; needs the captures (evidence/ or MU_CLIENT_TEXT/MU_IMAGE_DATA)
tools/python/bin/python scripts/validate_npc.py --emit-box   # regenerates character_box_table.h
```

No client bytes: the table holds the boxes' constants only.
