# Legacy particles, sprites, blob shadows (NATIVE-PARTICLE-001)

Authored C for the client's older particle and sprite system, its billboard routine, the blob shadow, the bone
helpers and the object visuals that use them, compared with the client's instructions in Unicorn by
`scripts/validate_particles.py`. Findings, kind table and limits:
[docs/research/client-particles.md](../../docs/research/client-particles.md).

| File | Client routines |
|---|---|
| `particles.h` | API: particle record, host, list, sprites, GL stream callbacks, shadow meshes, visual host |
| `particles.c` | CreateParticle `0x0168fafd` (wrapper) / `0x015ae7b0` (core), MoveParticles `0x01616c80` (wind block, record body, MovePosition `0x012af52d`), RenderParticles `0x0159123f` (record body) |
| `sprites.c` | RenderSprite `0x0184c39c`, CreateSprite `0x01692eb7`/`0x01692508`, `0x01692887`, RenderSprites `0x0169270e` with the per-sprite draw `0x01692931` |
| `shadow.c` | RenderBodyShadow `0x012bc07a`, the bone name test of `0x0129f18a`, TransformPosition `0x012b6ef1` |
| `visual.c` | RenderObjectVisual `0x017f9758` (Lorencia), the Tormenta Island handler's slot 0x34 `0x00e4ef4b` |
| `layout.c` | client layouts of the particle (0xb4) and sprite (0x3d8) records, for the validator and tests |

Kinds: Fire01 `0x7f3c` 0..6, 17; smoke01 `0x7f5a` 0, 2, 3; rain02/rain03 `0x771c`/`0x771d` 0; Spark02 `0x7f25` 0;
Thunder01 `0x7f2b` 0; Spark03 `0x7f26` 0, 1 (`mu_pt_kind_supported`). Other kinds are reported unsupported.

Callers that create particles or sprites from other reconstructed routines (objects, environment, skills) pass
them to `mu_pt_create` / `mu_pt_sprite_create`; `native/core/mu_particles.*` does that for the native world.

```sh
make -C reconstructed/particles
python3 -m unittest discover -s reconstructed/particles -p 'test_*.py'
scripts/validate_particles.py --cases 3000 --heavy-cases 300 --output /tmp/particles.json
```

Build with `-ffp-contract=off`: the float arithmetic follows the client's binary32 order.
