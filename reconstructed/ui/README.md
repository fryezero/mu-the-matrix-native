# Reconstructed 2D interface layer (NATIVE-UI-001)

This directory holds C restatements of the client's 2D routines. Each one emits the
client's OpenGL, GLU and GDI calls through `mu_ui_sink`, in the client's order and
with its exact argument words. The findings and evidence are in
[client-ui-2d.md](../../docs/research/client-ui-2d.md).

| File | Client routines |
|---|---|
| `ui2d.c` | GL state wrappers, BindTexture, BeginBitmap/EndBitmap, ConvertX/Y, RenderBitmap, RenderColor, RenderColorBitmap, CSprite, CGaugeBar, title scene |
| `ui_text.c` | CUIRenderTextOriginal RenderText/WriteText/UploadText, CreateFonts sizes |
| `ui_texture.c` | OpenTga, OpenJpeg (pixel handling and uploads; JPEG decoding is a callback) |
| `ui_login.c` | 2D overlay of the login-scene render `0x01857ed9` |
| `ui_widget.c` | CButton, CWin, CWinEx, CutText (NATIVE-UI-002; CSprite frames are in `ui2d.c`) |
| `ui_server.c` | CServerSelWin: Create, SetPosition, UpdateDisplay, UpdateWhileActive, RenderControls |
| `ui_credit.c` | CCreditWin: Create, Show, fades and credit blocks, RenderControls |
| `ui_probe.c` | flat object-state views for `scripts/validate_ui_widgets.py` (not part of the native module) |

Build with `make` (produces `libmu_ui.dylib` or `libmu_ui.so`; uses `-ffp-contract=off`).

To check the reconstruction against the client's instructions on the pinned captures:

```sh
./tools/python/bin/python scripts/validate_ui.py [--game-root "$MU_GAME_ROOT"]
```

`scripts/validate_ui_widgets.py` does the same for the window/widget layer
([client-ui-widgets.md](../../docs/research/client-ui-widgets.md)).

`test_ui.py` and `test_ui_widgets.py` hold the portable checks. Private checks run when
`MU_RECOVERY_INTEGRATION=1` is set.
