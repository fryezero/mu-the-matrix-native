# Pets: the pet process (NATIVE-HELPERS-002)

Platform-neutral C for the client's data-driven pets: the Demon, the Spirit of Guardian, Pet Rudolph, Pet Panda, Pet
Unicorn, Pet Skeleton and the PC-room Panda / Skeleton. Finding:
[docs/research/client-pets.md](../../docs/research/client-pets.md).

| Routine | Address | Function | Status |
|---|---|---|---|
| petdata.bmd loader, checksum, BuxConvert | `0x00eb0a7d`, `0x00976895`, `0x00976855` | `mu_pet_data_load`, `mu_pet_checksum`, `mu_pet_bux` | verified |
| info map, lookup | `0x00eb0c52`, `0x00eb0cdb` | `mu_pet_data_find` | static |
| CreatePet, DeletePet | `0x00eb0e78`, `0x00eb1015` | `mu_pets_create`, `mu_pets_delete` | static (the std::map keyed by c->key * 10000 + item) |
| PetObject::Create | `0x00eac071` | `mu_pet_create_object` | verified |
| PetObject::Update (FadeAlpha, model tick, move, pick-up sound) | `0x00eac414`, `0x00eac84d`, `0x00eac902`, `0x00eaeacf` | `mu_pet_update`, `mu_pet_move` | verified |
| the collector's zen search | `0x00eac65a` | `mu_pet_find_target` | verified |
| PetObject::Render, the visuals | `0x00eac4e0`, `0x00eaeaf8` | `mu_pet_render`, `mu_pet_visuals` | verified |
| UpdatePets, RenderPets | `0x00eb0d64`, `0x00eb0dee` | `mu_pets_update`, `mu_pets_render` | static (map order) |

The routines take the client state they read as plain inputs (`mu_pet_inputs`, the owners' `mu_pet_owner`, the ground
items) and call the host (`mu_pet_host`, `mu_pet_render_host`) for the engine services; rand() is the MSVC LCG kept in
`mu_pets`. The pet's OBJECT is the helpers' `mu_hp_object`.

* `make` builds `libclient_pets.{dylib,so}` (with `../helpers/helpers.c`, the movement and record-math sources) for the
  validator; the native build compiles `pets.c` into `libmunative.a`.
* `test_pets.py`: portable worked examples (ctypes).
* `scripts/validate_pets.py`: the Unicorn comparison with the client's instructions (private captures);
  `--mutations` checks the planted mistakes (`-DMU_PET_MUTATION=n`).
* `native/core/mu_world_pets.*`: the native session's use (owners from the helpers module, models, draw).
