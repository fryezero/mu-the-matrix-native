# The Dark Raven (NATIVE-HELPERS-002)

Platform-neutral C for the client's Dark Raven (Dark Spirit, item 13,5): the pet object a Dark Lord carries, that
flies around and above its owner, sparkles, and in a safe zone becomes the soul model that follows the owner's
shoulder. Finding: [docs/research/client-dark-spirit.md](../../docs/research/client-dark-spirit.md).

| Routine | Address | Function | Status |
|---|---|---|---|
| pet byte (item and level word) | `0x00c92bea` | `mu_rv_set_type` | verified |
| create / delete | `0x00c92a29` / `0x00c9321b` | `mu_rv_create` / `mu_rv_delete` | verified (delete as a recorded stub) |
| Dark Raven constructor, CreatePetPointer | `0x009ecbdf`, `0x009ec0b0` | `mu_rv_create` → `mu_rv_create_pointer` | verified (modelled fields) |
| MovePet (AI 0 / 1 fly, 3 sit, the lost counter) | `0x009ecfe9` | `mu_rv_move_pet` | verified (AI 2 / 4 / 5: static, not ported) |
| per-character move, model check | `0x00c930df`, `0x00c92e04` | `mu_rv_move`, `mu_rv_model_fits` | verified |
| per-character render, RenderPet | `0x00c9314f`, `0x009ef6d5` | `mu_rv_render` | verified (the attack effects `0x009ef9a5`: static) |
| render functors (registry `0x01d1e010`) | `0x00a2eea5` (0x411), `0x00a55f03` (0x748) | `mu_rv_draw_raven`, `mu_rv_draw_soul` | verified |

The routines take the client state they read as plain inputs (`mu_rv_owner`, `mu_rv_inputs`) and call the host
(`mu_rv_host`, `mu_rv_render_host`, `mu_rv_draw_host`) for the engine services; rand() is the MSVC LCG kept in
`mu_raven`.

* `make` builds `libclient_raven.{dylib,so}` for the validator; the native build compiles `raven.c` into `libmunative.a`.
* `test_raven.py`: portable worked examples (ctypes).
* `scripts/validate_raven.py`: the Unicorn comparison with the client's instructions (private captures); `--mutations`
  checks the planted mistakes (`-DMU_RV_MUTATION=n`), `--negative N` the planted world.
* `native/core/mu_world_raven.*`: the native session's use (owners, models, draw), hung off `mu_world_helpers`.
