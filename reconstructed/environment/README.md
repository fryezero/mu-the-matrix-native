# Ambient life and weather (NATIVE-ENV-001)

Authored C for the client's environment routines, compared with the client's instructions in Unicorn by
`scripts/validate_environment.py`. Findings, per-world table and limits:
[docs/research/client-environment.md](../../docs/research/client-environment.md).

| File | Client routines |
|---|---|
| `env.h` | API: state (`mu_env`), the modelled object and particle fields, host and render-host callbacks |
| `env_core.c` | rand() `0x01989721`, ObjectInit `0x0129eb81` (modelled fields), SetLive `0x0129f4a5`, client layouts |
| `env_boids.c` | MoveBoids `0x00c9eb04`, movers `0x00ca2acd`/`0x00ca2ba7`/`0x00ca2dcb`, flight `0x00ca3e2f`, flock `0x012af9a9`, CreateAngle `0x012aeced`, TurnAngle `0x012aef0c`, AtlansShoal `0x00ca27b1`, FadeAlpha `0x012af883`, RenderBoids `0x00c9fd8d` |
| `env_fish.c` | MoveFishs `0x00ca05b3`, RenderFishs `0x00ca1cf7` |
| `env_leaves.c` | MoveLeaves `0x01537a43`, creators `0x0153959d`/`0x0153939c`/`0x01539ace`/`0x015398de`, Tormenta `0x00e5377c`/`0x00e53c14`, movers `0x0153a634`/`0x0153ac06`/`0x00e538ec`, RenderLeaves `0x01538145`, RenderPlane3D `0x0184c121` and RenderSprite `0x0184c39c` geometry |
| `env_world.c` | per-world table (static readings), model and bitmap file names |
| `env_test_host.c` | deterministic host for the tests and the validator (not client code) |

```sh
make -C reconstructed/environment
python3 -m unittest discover -s reconstructed/environment -p 'test_*.py'
scripts/validate_environment.py --text "$MU_CLIENT_TEXT" --data "$MU_IMAGE_DATA" --cases 400 --ticks 60 --mutations
```

Build with `-ffp-contract=off`: the float arithmetic follows the client's binary32 order.
