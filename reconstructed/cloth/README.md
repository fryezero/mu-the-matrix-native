# The wings' physics capes (RENDER-ITEMS-CLOAK)

Platform-neutral C for the client's physics cloth: the capes of wings `0x2382`..`0x2385`, `0x2394` and `0x2395`
(InnocenceCape, SparkleCape, the Black Cloak models). The client does not draw these capes from the item model; it
builds a mass-spring grid per character and steps and renders it every frame. Finding:
[docs/research/client-render-items.md part 24](../../docs/research/client-render-items.md#part-24-the-wings-physics-capes-render-items-cloak).

| Routine | Address | Function | Status |
|---|---|---|---|
| CreateCloth: the wing cases `0x2382`/`0x2383`, `0x2384`/`0x2385`, `0x2394`/`0x2395` | `0x01357ccc` (`0x0135b558`, `0x0135b79f`, `0x0135c419`) | `mu_cloth_wing_create` | verified |
| constructor and defaults | `0x00fd6c22`, `0x00fd6ca4` | `mu_cloth_init` | verified |
| Create (virtual slot 2), SetFixed (slot 4), SetSpring | `0x00fd6e60`, `0x00fd79bb`, `0x00fd8192` | `mu_cloth_create` | verified |
| AddCollisionSphere, the texture / force setters | `0x00fd9ded`, `0x013bb4a2`, `0x013bb477`, `0x013bb44c` | `mu_cloth_add_sphere`, fields | verified |
| Move2, the step, InitForces (slot 7), integration, constraints, collisions | `0x00fd821e`, `0x00fd825f`, `0x00fd8463`, `0x00fd85f0`, `0x00fd88ec`, `0x00fd9e98` | `mu_cloth_move2` | verified |
| CPhysicsVertex: InitForce, Move, distance, constrain, apply, stretch limit; sphere collision | `0x00fd59e8`, `0x00fd5f15`, `0x00fd5fb5`, `0x00fd63be`, `0x00fd65b1`, `0x00fd606f`; `0x00fd69e8` | (static, in `cloth.c`) | verified |
| Render (slot 8), RenderFace, RenderVertex | `0x00fd8bc2`, `0x00fd8fba`, `0x00fd90f5` | `mu_cloth_render` | verified (GL stream) |
| the physics manager's wind walk | `0x00fdad7b` | `mu_cloth_wind_step` | verified |
| RenderCharacter's cloth flag, light and arg 4 | `0x01366edf..0x01367530` | `mu_cloth_gate` | verified (event / guild / duel / buff inputs at rest) |
| RenderCloth's draw tests | `0x01362e1d`, `0x01362e87` | `mu_cloth_draw_allowed` | static (no buffs, sub-type 0) |

Not ported: the other CreateCloth cases (other wings, arg 4 = 1), the armour cloths (`0x0135ea29`, `0x01362755`),
the angle-matrix Create variant (slot 1 / 5), the glow pass (`0x00fd9663`) and the mesh passes
(`0x00fd9c61`, `0x00fd97de`); `mu_cloth_render` refuses a cloth that would need them.

`make` builds `libcloth` (with `../record-math/record_math.c` for AngleMatrix and the vector rotations). The native
world runs it through `native/world/world_cloak.c`. Tests: `native/tests/test_native_item_cloak.py` (portable;
private Unicorn row `validate_item_cloak`, `scripts/validate_item_cloak.py`; private scene).
