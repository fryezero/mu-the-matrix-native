# reconstructed/map (NATIVE-MAP-001)

The client's map overlay, Move window, gates and teleport fields, restated in C from the pinned restored text
(capture09 `2bd5f2e9…3724`) and second section (run10 `c985e2e6…a0672f`). Finding:
[docs/research/client-maps.md](../../docs/research/client-maps.md).

| File | Client routines | Status |
|---|---|---|
| `map_hud.c` | hudMap window: per-frame `0x00c6af22`, pixels `0x00c6ba5c`/`0x00c6ba7d`, addUnit `0x00c6baa6`, 0xE7 records `0x00c6b550`/`0x00c6b5c5`, AddDetectedUnit `0x00c6b6c2`, blocked areas `0x00c6bc46`, showMap `0x00c6aba6`, InitData `0x00c6b89f`; navimap name `0x00c6b116` | verified (name: static) |
| `map_move.c` | move manager ctor `0x00d3b4cb`, sort `0x00d3b325` (MSVC std::sort), availability `0x00bdc0c7`, rows `0x00bdd08d`, favourites `0x00bdcaf3`, special rule `0x00bdc7bd`, click `0x00bdc813`, request `0x00b3b866`; strife lists `0x00bdbf82` | verified (strife: static) |
| `map_gate.c` | gate entrance test `0x016a4608`; teleport fields `0x0128136d` | verified (teleport: static) |

```sh
make -C reconstructed/map                                  # libmap
python -m unittest discover -s reconstructed/map -p 'test_*.py'
tools/python/bin/python scripts/validate_map.py --snapshot lang4.bin --cases 500 --mutations   # Unicorn, private
```

No client bytes: constants and rules only. `MU_MAP_MUTATION` plants the validator's mistakes (0 in builds).
