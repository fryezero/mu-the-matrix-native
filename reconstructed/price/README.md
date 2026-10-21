# reconstructed/price (NATIVE-LANG-002)

The client's item value and repair-cost routines, restated in C from the pinned restored text (capture09
`2bd5f2e9…3724`) and second section (run10 `c985e2e6…a0672f`). Finding:
[docs/research/client-lang-tables.md](../../docs/research/client-lang-tables.md#3-item-prices-verified).

| Function | Client routine | Status |
|---|---|---|
| `mu_item_price` | ItemValue `0x0169320b` (goldType 0 buy, 1 sell, 2 repair base) | verified, except three excellent-option compares displaced out of the restored image (inferred; see the header) |
| `mu_item_repair_cost` | ConvertRepairGold `0x016b8d16` | verified |
| `mu_item_repair_price` | the per-item repair price of `0x016c3cb5` | composition of the two (static) |
| `mu_price_format` | the zen formatter `0x016b8b26` for integral values | static |

```sh
make -C reconstructed/price                                  # libitemprice
python -m unittest discover -s reconstructed/price -p 'test_*.py'
tools/python/bin/python scripts/validate_item_price.py --game-root "$MU_GAME_ROOT" --mutations   # Unicorn
```

No client bytes or game data: the routines take the Item.bmd record the caller loaded.
