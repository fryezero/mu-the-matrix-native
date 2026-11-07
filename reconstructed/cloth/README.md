# The wings' physics capes (RENDER-ITEMS-CLOAK, CLOAK-002)

Platform-neutral C for the client's physics cloth: the capes of every wing case of CreateCloth `0x01357ccc` (InnocenceCape,
SparkleCape, the Black Cloak and the 31 other wing cases). The client does not draw these capes from the item model; it
builds a mass-spring grid per character and steps and renders it every frame. Findings:
[docs/research/client-render-items.md part 25](../../docs/research/client-render-items.md#part-25-the-wings-physics-capes-render-items-cloak)
and [part 27](../../docs/research/client-render-items.md#part-27-every-createcloth-case-and-the-glow-pass-cloak-002).

| Routine | Address | Function | Status |
|---|---|---|---|
| CreateCloth: every wing case (34 case bodies, 54 wing types), arg 4 = 1 | `0x01357ccc` (switch `0x01357e5c`, byte table `0x0135ea14`) | `mu_cloth_wing_create`, `mu_cloth_wing_cloths` | verified |
| constructor and defaults | `0x00fd6c22`, `0x00fd6ca4` | `mu_cloth_init` | verified |
| Create (virtual slot 2), SetFixed (slot 4), SetSpring | `0x00fd6e60`, `0x00fd79bb`, `0x00fd8192` | `mu_cloth_create` | verified |
| Create with an angle matrix (slot 1), its SetFixed (slot 5), RotatePosition | `0x00fd77dc`, `0x00fd7d2a`, `0x012b7019` | `mu_cloth_create_angles` | verified |
| SetFixed's model: Models[OBJECT +0x60] for the sub-types `0x5bc` / `0x5bd` | `0x00fd7c73`, `0x00fd805b` | `mu_cloth_host.subtype` | verified |
| AddCollisionSphere, the texture / force setters, SetGlow | `0x00fd9ded`, `0x013bb4a2`, `0x013bb477`, `0x013bb44c`, `0x00fd9f50` | `mu_cloth_add_sphere`, fields, `mu_cloth_set_glow` | verified |
| Move2, the step, InitForces (slot 7), integration, constraints, collisions | `0x00fd821e`, `0x00fd825f`, `0x00fd8463`, `0x00fd85f0`, `0x00fd88ec`, `0x00fd9e98` | `mu_cloth_move2` | verified |
| CPhysicsVertex: InitForce, Move, distance, constrain, apply, stretch limit; sphere collision | `0x00fd59e8`, `0x00fd5f15`, `0x00fd5fb5`, `0x00fd63be`, `0x00fd65b1`, `0x00fd606f`; `0x00fd69e8` | (static, in `cloth.c`) | verified |
| Render (slot 8), RenderFace, RenderVertex, the glow pass and its wave | `0x00fd8bc2`, `0x00fd8fba`, `0x00fd90f5`, `0x00fd9663`, `0x0185bdc4` | `mu_cloth_render` | verified (GL stream) |
| the physics manager's wind walk | `0x00fdad7b` | `mu_cloth_wind_step` | verified |
| RenderCharacter's cloth flag, light and arg 4 | `0x01366edf..0x01367530` | `mu_cloth_gate` | verified (event / guild / duel / buff inputs at rest) |
| RenderCloth's draw tests (sub-types, actions, skin-3 sub-types `0x009a0989`, class index) | `0x01362e1d`, `0x01362e87` | `mu_cloth_draw_allowed` | verified (buff `0x12` at rest) |

Not ported: the armour cloths (`0x0135ea29`, `0x01362755`, OBJECT `+0x48`), the sprite pass of type `0x40000000`
and the mesh passes (`0x00fd9c61`, `0x00fd97de`; only the armour cloths set a mesh); `mu_cloth_render` refuses a cloth
that would need them.

`make` builds `libcloth` (with `../record-math/record_math.c` for AngleMatrix and the vector rotations). The native
world runs it through `native/world/world_cloak.c`. Tests: `native/tests/test_native_item_cloak.py` (portable;
private Unicorn row `validate_item_cloak`, `scripts/validate_item_cloak.py`; private scenes).
