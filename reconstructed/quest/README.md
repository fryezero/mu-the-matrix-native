# reconstructed/quest (NATIVE-QUEST-001)

The client's quest system, restated in C from the pinned restored text (capture09 `2bd5f2e9…3724`) and second
section (run10 `c985e2e6…a0672f`). Finding: [docs/research/client-quests.md](../../docs/research/client-quests.md).

| File | Client routine | Status |
|---|---|---|
| `quest_data.c` | MUQuest / MUQuestString / ItemLevelTooltip records (plaintext of a live read) | data layout from the record builder `0x0113eb75` and the consumers |
| `quest_system.c` | the quest system `[0x01ec2e60]`: category `0x00fe1a06`, build `0x00fe249e` + `0x00fe138b` + `0x00fe15e9` (dialogue `0x00fe764a`), lookups `0x00fe14d4` / `0x00fe1695` / `0x00fe1506` / `0x00fe1555`, activation `0x00fe16e4` / `0x00fe17db` / `0x00fe18c4`, values `0x00fe1984` / `0x00fe19a3` | verified (Unicorn; also against the running client's own quest system in the snapshot) |
| `quest_text.c` | goal line `0x00fe1a52`, reward lines `0x00fe1e92`, HTML line `0x0096fe90` | verified |
| `quest_packets.c` | receive dispatcher `0x01287ead`, opcode F6: `0x6f` `0x012510fe`, `0x70` `0x0125313f` (decoded), `0x71` `0x0126d65c` (decoded), `0x72` `0x01222933`, `0x73` `0x0122287a`, `0x74` `0x0122adf5`, `0x75` `0x01253577`, `0x81` `0x012533c9`, `0x82` `0x01253713`, `0x83` `0x01253113` | verified |
| `quest_ui.c` | NpcQuestProgress (`0x00bee2b3`, `0x00bee333`, `0x00bee614`, `0x00bee997`, `0x00bedfb4`, `0x00bee1fa`, `0x00bedd69`, `0x00beebc2`, `0x00beec0b`, `0x00beea7a`), npcdialogue's quest list (`0x00be9c75`, `0x00be8bdc`, `0x00be8724`, the list part of `0x00be906d`), MyQuestInfo (`0x00be420e`, `0x00be42dc`, `0x00be3ab5`, `0x00be4922`, `0x00be4732`, the quest tab `0x00d4f16e`: `0x00d4f285`, `0x00d4f485`, `0x00d4f2e0`, `0x00d4fa92`, `0x00d4fe25`, `0x00d4f3ac`, `0x00d501c8`, `0x00d50067`, `0x00d5060e`, the give-up box `0x00be436d`) | verified; the callbacks' value decoding (`0x00beec8c`, `0x00be4b89`) static |

```sh
make -C reconstructed/quest                                   # libquest
python -m unittest discover -s reconstructed/quest -p 'test_*.py'
tools/python/bin/python scripts/validate_quest.py --snapshot LOCAL/lang4.bin --mutations   # Unicorn, about 2 min
```

No client bytes: tests use synthetic plaintext.
