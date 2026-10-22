# Helpers: pets and mounts (NATIVE-HELPERS-001)

Platform-neutral C for the client's helpers: the Guardian Angel that circles its owner (the "bugs") and the mounts of
the mount manager (Uniria, Dinorant, Dark Horse, Fenrir and the later ride items) with their rider poses and lift.
Finding: [docs/research/client-helpers.md](../../docs/research/client-helpers.md).

| Routine | Address | Function | Status |
|---|---|---|---|
| CreateBug / CreateBugSub | `0x00c9d8df` / `0x00c9d42a` | `mu_hp_create_bug` | verified |
| MoveBugs / MoveBug | `0x00c9e24a` / `0x00c9d95a` | `mu_hp_move_bugs` | verified |
| RenderBugs / RenderBug | `0x00c9e4e3` / `0x00c9e28a` | `mu_hp_render_bugs` | verified |
| DeleteBug, the type list | `0x00c9ea70`, `0x00ca211e` | `mu_hp_delete_bug`, `mu_hp_bug_type` | verified |
| mount kind, descriptor, factory | `0x0106cc24`, `0x0106cc74`, `0x0106cde5` | `mu_hp_mount_kind`, `mu_hp_mount_class` | verified (every ride item and state) |
| class model, play speeds, rider offset | vtable `+0x38`, `+8` with `0x0103dbf4`, `+0x10` | `mount_classes.h`, `mu_hp_mount_model`, `mu_hp_mount_speed`, `mu_hp_mount_offset` | verified (21 classes, extracted by execution) |
| base move | `0x0103d45a` | `mu_hp_mount_move_base` | verified |
| class moves (dust, flying steps, Dark Horse ring) | `0x01064b6d`, `0x0104009b`, `0x0103f2a4`, `0x010438c1` | `mu_hp_mount_move` | verified (the four classic classes; the others run the base move) |
| action map, mount SetAction | `0x0103d931` / `0x0106c4b6`, `0x0103d9eb` / `0x010401c6` / `0x010406cf` | `mu_hp_mount_follow_action`, `mu_hp_mount_set_action` | verified |
| rider action | `0x0106c382` -> `0x0103dd6b` / `0x0103ddde` | `mu_hp_rider_action` | verified |
| rider lift | `0x0103da5c` with `0x0103dc68` | `mu_hp_mount_place_owner`, `mu_hp_mount_lifts` | verified |
| render: body, shadow, after-pass | `0x0103d6d5`, `0x0103d281`, `0x0103d830` | `mu_hp_mount_render` | verified |
| mount init / set / reset | `0x0103cf7a`, `0x0106b85d`, `0x0106ba49` | `mu_hp_mount_init`, `mu_hp_mount_set`, `mu_hp_mount_reset` | static (the factory and class parts verified) |
| the Imp on the shoulder | BackCarry `0x0139db9a`, block `0x0139ef04..0x0139f2d9` | `mu_hp_imp_link_plan` | static |

The routines take the client state they read as plain inputs (`mu_hp_inputs`, the owners' `mu_hp_owner`) and call the
host (`mu_hp_host`, `mu_hp_render_host`) for the engine services; rand() is the MSVC LCG kept in `mu_helpers`.

* `make` builds `libclient_helpers.{dylib,so}` for the validator; the native build compiles `helpers.c` into
  `libmunative.a`.
* `test_helpers.py`: portable worked examples (ctypes).
* `scripts/validate_helpers.py`: the Unicorn comparison with the client's instructions (private captures);
  `--emit-classes` regenerates `mount_classes.h`, `--mutations` checks the planted mistakes (`-DMU_HP_MUTATION=n`).
* `native/core/mu_world_helpers.*`: the native session's use (models, owners, draw).
