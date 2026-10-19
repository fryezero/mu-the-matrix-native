# reconstructed/items (NATIVE-ITEMS-001)

The client's dropped items, authored in C from the client's instructions and compared with them in Unicorn
(`scripts/validate_items.py`). See [the finding](../../docs/research/client-ground-items.md).

| File | Contents |
|---|---|
| `ground_items.h/.c` | Item pool layout; packet 0x20 (`0x0122c216`), CreateItem `0x016daa27`, ItemObjectAttribute `0x016da00b`, MoveItems `0x017ea1aa` with the sparkle `0x017f7290`, RenderItems' per-item plan `0x017e9495`, SelectItem `0x016b4fc0`, TestFrustrum `0x016ccc14`, the label colour `0x00c84f00`, the label anchor and ItemNameMC layout (static readings), drop and pick-up sounds |
| `item_angle_table.h` | ItemAngle `0x01802a66`, lifted block by block by `scripts/items_static.py` (generated) |
| `item_name_table.h` | The name builder `0x017ea422` (label text and colour class), lifted by `scripts/items_static.py` (generated; one span hand-written) |
| `test_items.py` | Worked examples (portable) and a short private Unicorn run |

Regenerate the lifted headers (needs the pinned restored text and second section under `evidence/`):

```sh
./tools/python/bin/python scripts/items_static.py --emit-angle reconstructed/items/item_angle_table.h \
    --emit-name reconstructed/items/item_name_table.h
make -C reconstructed/items
./tools/python/bin/python scripts/validate_items.py --cases 3000 --heavy-cases 300
```

Engine services (terrain height and light, rand, sin, sqrt, Item.bmd records, GlobalText, sounds, the label window)
are callbacks; nothing here reads game data.
