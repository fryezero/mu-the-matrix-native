# World call order

WORLD-ORDER-001 reconstructs the order-only control flow of MoveMainScene and
RenderMainScene. It uses `mu_scenemgr_host` from `../scene/scene.h`; the native
runtime does not link this family. Calls record routine/import identity or a
virtual slot. Opaque host returns and original-address reads control branches.

`parts_order.py` translates a compiled ordinary record stream into the native
part order. Every moved part or native addition has a reason there. Composite
native passes and the GL/software helper placements are deliberate adapters.

Portable part, hook and adapter regressions:

```sh
./tools/python/bin/python -m unittest discover -s native/tests -p test_world_parts.py -v
```

Pinned private original-instruction comparison and compiled mutants:

```sh
MU_RECOVERY_INTEGRATION=1 ./tools/python/bin/python scripts/run_validators.py \
  --private --only validate_world_order --report verify-runs/world-order
```

The validator builds C in its own temporary directory. It requires clang,
Unicorn and Capstone plus the two inputs resolved by `scripts/pins.py`.
See `docs/research/client-world-order.md` for the evidence boundary and counts.
