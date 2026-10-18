# Reconstructed in-game interface routines (NATIVE-HUD-001)

In this client the in-game windows (inventory, character info, chat, the
bottom bar with the HP/MP orbs and skill bar, tooltips) are GFx (Scaleform)
movies. What remains game code, and is restated here, is the data and
legacy-GL side around them. The findings are in
[client-hud.md](../../docs/research/client-hud.md).

| File | Client routines |
|---|---|
| `inv_grid.c` | item grid of the GFx item windows: constructor `0x00ad322b`, Init `0x00ad341d`, fit tests, free-slot searches, counts, pixel mapping, place/remove |
| `item_slots.c` | window anchoring `0x00aae509`/`0x00aae601`, slot pass `0x00ab6130`, slot wrapper `0x016c23d5`, RenderItem3D `0x016c154e` (general path) |
| `item_pass.c` | per-window GFx render pass `0x00abfcca` (movie, orthographic item pass, overlay) |
| `tooltip_html.c` | InfoPopup HTML assembly `0x00b8d94b` and line builder `0x00ab4dc0` |
| `tooltip_format.c` | tooltip-text formatter `0x00f1098a`, 14 of its types |

`item_pass.c` reuses UI-001's state wrappers (`../ui/ui2d.c`).

Build with `make` (`libmu_hud.dylib` or `libmu_hud.so`). Compare with the client:

```sh
./tools/python/bin/python scripts/validate_hud.py --sections grid,slots,pass,item3d,html,format --cases 100
```

`test_hud.py` holds the portable checks; private checks run with `MU_RECOVERY_INTEGRATION=1`.
