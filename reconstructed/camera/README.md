# Camera, picking, input and frame timing (NATIVE-FRAME-001)

Authored C ports of the client routines a native frame loop needs. Every
function equals the client's instructions on the compared domain
(`scripts/validate_camera.py`, Unicorn over the pinned restored text). See
[the finding](../../docs/research/client-camera-input.md) for addresses,
evidence levels and limits.

| File | Client routines |
|---|---|
| `client_camera.*` | glViewport2 `0x01849ec4`, gluPerspective2 `0x01849d76`, BeginOpengl `0x0184adc7` (camera part), GetOpenGLMatrix `0x0184a569`, CreateScreenVector `0x01849f08`, projections `0x0184a244`/`0x0184a2e8`/`0x0184a3ce`/`0x0184a455`, FaceNormalize `0x00d01206`, InsideTest `0x018506bc`, CollisionDetectLineToFace `0x0184f96c`, RenderTerrainTile picking `0x016ccda5` |
| `client_world_camera.*` | MoveMainCamera `0x0185498e` (ordinary in-world path), wheel zoom `0x018588d9`/`0x0185a9bf`, timer `0x018519ff`/`0x00c9b4ac`, lerp `0x0185047d`, ease `0x018504c6` |
| `client_input.*` | key scan `0x00ec5475` and queries, window-procedure mouse globals of `0x0120fee3` |
| `client_frame.*` | frame-driver accumulator and 40 ms cap of `0x01851d39` |

The GL matrices (glRotatef, glTranslatef, gluPerspective) are driver work, not
client code; they are computed with the Mesa/SGI reference formulas and
labelled as such. Build with `-ffp-contract=off` (binary32 operations in source
order). Trigonometry uses host libm, which agreed with the client's CRT on every
compared case.

```sh
make -C reconstructed/camera
python3 -m unittest discover -s reconstructed/camera -p 'test_*.py'
MU_RECOVERY_INTEGRATION=1 python3 scripts/validate_camera.py --text ... --data ... --cases 1000 --mutations
```
