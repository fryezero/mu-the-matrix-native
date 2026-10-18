# JSON effect system (NATIVE-FX-001)

Authored C ports of the client's `Data/Effect/*.ein` effect code: the JSON
loader, the particle system (type 0) and the billboard sprite (type 1), with
every component, emitter shape and curve routine they reach, and the vertex
fill and draw state of both draw routines. Every installed `.ein` file is type
0 or 1. The per-frame particle records, VBO bytes, draw state and `rand()`
call counts equal the client's instructions on every compared case
(`scripts/validate_effects.py`, Unicorn over the pinned restored text). See
[the finding](../../docs/research/client-effects.md) for addresses, evidence
levels and limits.

| File | Client routines |
|---|---|
| `effects_json.c` | JsonCpp-style reader conversions (`0x0093f7e8` parse, `0x0093e3aa` member, `asFloat`/`asInt`/`asUInt`/`asBool` `0x0093d773`/`0x0093d1ed`/`0x0093d361`/`0x0093d917`); base load `0x00a760b2`; particle load `0x00a88fda`; billboard load `0x00a6f3e1`; component loaders |
| `effects.c` | node update `0x00a75708`, transform `0x00a76dfe`, restart `0x00a76898`; particle update `0x00a88443`, loop `0x00a8a273`, emitter `0x00a80752`, emission count `0x00a8185f`, shapes (box `0x00a7dcae`, cone `0x00a7f50b`, hemisphere `0x00a84629`, point `0x00a8503b`, sphere `0x00a860a7`), start values (colour `0x00a86ae1`, ranges `0x00a87647`/`0x00a87cad`/`0x00a88089`), lifetime components (colour `0x00a7eeba`, force `0x00a83e91`, rotation `0x00a85240`, size `0x00a85819`, speed `0x00a85c5b`, tiles `0x00a8d371`), terrain collider `0x00a8ce2d`; billboard update `0x00a6ea2c`, reset `0x00a6fcfd`; fills `0x00a8a55c` (particles) and `0x00a70036` (billboard); curves `0x00a74a3f`, gradients `0x00a73b41`/`0x00a73ca4`; MSVC `rand` `0x01989721` |
| `effects_tree.c` | NATIVE-FX-002: transform with parent/external matrix `0x00a76dfe`, node update `0x00a75708` (owner action gate, bounding boxes `0x00a88970`/`0x00a6ed9b`, octree maintenance, children), owner `0x00a76a30`, clone `0x00a75934` (emitter constructor `0x00a81787`), frustum `0x00a8d821`/`0x00a8d7c8`, octree `0x00a8df54`/`0x00a8e4d7`/`0x00a8e59f`, EffectManager render pass `0x00a7a30e`, texture upload `0x00a90987` |
| `effects_internal.h` | Shared client scalar/vector helpers |
| `effects_capi.c` | Flat handle API for the validators and tests (`mu_fx_open`, ...; `mu_fxt_*` scenes of trees for NATIVE-FX-002) |

Notes:

* The update needs the previous draw (the client's `drawn` flag at PS `+0x114`
  / BB `+0x144`), so drive it as update, draw, update, draw.
* An emitter without `Frequency` computes `rand() % 0`. In the client this is
  an integer divide fault at `0x00a80790`; here the effect is marked
  `faulted` and stops updating. 39 of the 370 installed files reach it within
  20 frames.
* Build with `-ffp-contract=off` (binary32 operations in source order).
  `sqrt`, `sin` and `cos` use host libm; they agreed with the client's CRT
  wrappers on every compared case.

Trees (`Children`), parentduration, owners, instances and the EffectManager's
octree and render pass are NATIVE-FX-002, compared by
`scripts/validate_effect_tree.py`; see
[the finding](../../docs/research/client-effect-manager.md).

```sh
make -C reconstructed/effects
python3 -m unittest discover -s reconstructed/effects -p 'test_*.py'
python3 scripts/validate_effects.py --text evidence/x86-text-capture-09/client-text.bin \
    --data evidence/image-data-run10/data-capture-10/client-image-data.bin \
    --section3 evidence/x86-linux-capture-04/main-01ced000.bin --game-root "$MU_GAME_ROOT" \
    --mutations 1500 --frames 60 --output /tmp/effects.json
python3 scripts/validate_effect_tree.py --text evidence/x86-text-capture-09/client-text.bin \
    --data evidence/image-data-run10/data-capture-10/client-image-data.bin \
    --section3 evidence/x86-linux-capture-04/main-01ced000.bin --game-root "$MU_GAME_ROOT" \
    --mutations 600 --clones 400 --scenes 300 --frames 30 --output /tmp/effect-tree.json
```
