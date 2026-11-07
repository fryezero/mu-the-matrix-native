# RENDER-EFFECTS-018

The two effect consumers refused since RENDER-EFFECTS-008/011 because "their inputs are missing": the Muun table's
`0x0114203d` (with its slot gate and the OBJECT update that places the effects on the posed Muun) and Uruk Mountain's
weather-driven keyed effect 0x806e/12. [Finding, addresses and limits](../research/client-render-effects-018.md).

- Claude Opus 5.5 lane. Branch `claude/render-effects-018`, worktree `~/Documents/MTM/worktrees/render-effects-018`,
  from origin/main `b18b6b45` (#321); merged with `ce0ebd71` (#324 RENDER-WORLDS-FOG, #323) in `a4aeed6b` (it
  brought only `native/core/mu_raster.{c,h}` and the native Makefile into this lane's build inputs) and with
  `6eaf3f2b` (#325 RENDER-ITEMS-002R) in `5cb92708` (renderchar and `native/core/mu_renderchar.c`,
  `mu_item_textures.c`; none of its programs requests 0x8084 or 0x806e) and with `53cffd00` (#326 RENDER-WORLDS-121,
  #327 TEST-SPEED-005) in `2353e836` (`docs/status.md` conflict: both sides kept; `mu_objects_runtime.c` merged
  automatically, the Test Area hunks are separate from this lane's). **Final code: `2353e836`.**
  Input links `tools/python`, `evidence` and `input` come from the main checkout and are never staged.
- No live client, network, memory write or installed-app change. The validators' inputs are synthetic owner and
  weather fixtures plus the local decoded `muuneffects.tsv` (read only, never written out).

## What landed

1. **Muun table consumer, verified.** `reconstructed/objects/muun_effects.{c,h}` (new): `0x0114203d` (equal_range,
   factory, attach, release), the slot gate `0x009af699` (OBJECT `+0x08`, owner `+0x04`, render-info record `+0x0c`,
   byte `+0x10`, key `+0x1c` = owner `+0x3244`), the clear `0x009af6f6`, and the OBJECT update `0x0129f671`: timed
   expiry, template scale × OBJECT scale, the external matrix by bone and follow flag (world matrix for bone −1; bone
   matrix `0x0129fd4f` from the OBJECT's own transforms `+0x318` or the shared pose `0x06fce398`, placed by position
   and scale outside a sector list; bone position `0x012a0030` for unfollowed records).
   `native/core/mu_muun_effects.{c,h}` (new) loads `MU_LANG_DIR/muuneffects.tsv` and drives an owner's list through an
   EffectManager scene. **Muun records: 0/16 → 16/16 supported** (every record's code attaches; with the installed
   data all 16 `.ein` templates load, attach and follow a fixture pose, 480 node updates, every external matrix equal
   to the reconstruction).
2. **Uruk's weather word, static + live.** `0x01cf15ec` is an int32 event state; the data image and DATA-ACQ-002's 32
   live reads hold −1; reset `0x017ebfd2` to −1; set only by server handlers (`0x0127edf3` in worlds 100/101: 0 or
   1; `0x00d53216`: 1; two others 36). The native default `mu_objects_runtime.uruk_weather` is now −1 (was 0; both
   off). The reader is compared over −1, 0, 1, 2, 36 and the int32 extremes.
3. **Uruk's keyed effect 0x806e/12, verified.** `reconstructed/combat/uruk_fx.inc` (new; LifeTime 20, one flame a
   step, no render) and `reconstructed/particles/uruk_flames.inc` (new; 0x8084/1 and 0x806e/5; 0x8085/1 is
   RENDER-EFFECTS-010's). `mu_objects_runtime.c` hands the keyed event to the owned-effect hook. **Uruk host: 39
   keyed requests refused → 39 effects created**; their moves create all three flame kinds, none refused.

## Checks (wall times)

| Check | Result | Wall time |
|---|---|---:|
| `nice -n 10 make -j4` (after the first merge) | passed | 11.6 s |
| `validate_render_effects18` registry row (`--cases 20 --mutations`) | 540 cases, 0 mismatches; 35/35 compiled mutants caught, none equivalent, every anchor exactly once | 24.7 s |
| `validate_render_effects18 --cases 200 --lang-dir <local lang>` (full count, no mutants) | 5,484 cases, 0 mismatches (attach 800, gate 800, update 800, records 84, reader 400, flames 3 × 600, effect 2 × 400) | 6.6 s |
| Affected existing rows at `a4aeed6b`, no mutants, `--cache --jobs 2` (76 reviewed rows) | 75 pass + `validate_path` skipped for its `directions` pin, rerun with `MU_PATH_DIRECTIONS` = capture 04: pass; 1,665,939 cases | 1,710.6 s + 28.6 s |
| `validate_worlds_fog`, `validate_app_polish4` (brief 8b, `mu_objects.h`) at `a4aeed6b` | 2 pass; 4,044 + 10,485 cases | 30.0 s |
| **Final selection at `2353e836`** after `make -j4`: `run_validators.py --list-affected origin/main` (TEST-SPEED-005's symbol-level pruning; 80 rows incl. fallbacks; 22 item/renderchar rows pruned: they use no changed symbol), no mutants, `--cache --jobs 2` | 80 pass, 0 fail/error/skip; 1,044,815 cases (`validate_render_effects18` 540, `validate_worlds_i` 6,000, `validate_worlds_m` 1,080, `validate_worlds_121` 4,000, `validate_terrain` 583,500, `validate_meshdraw` 14,619, ...) | 543.4 s |
| `nice -n 10 make -j4` at `2353e836` | passed | 15.5 s |
| Affected unit suites (`run_test_suites.py --affected origin/main`, integration off) at `a4aeed6b` | 12 suites, 1,538 tests: 1,314 passed, 224 skipped, 0 failures, 0 errors | 379.2 s (474.6 s with builds) |
| Integration modules at `a4aeed6b`: `test_render_effects18` (MuunHost, InstalledMuun), `test_native_worlds_m`, `test_native_worlds_i`, `test_native_particles`, `test_native_map_effects` | 12 tests, 11 passed, 1 skipped (`InstalledLorenciaFires`: no `MU_OBJECTS_PLAIN_DIR` in that run) | 47.3 s |
| Same modules at `2353e836` (with `MU_OBJECTS_PLAIN_DIR`) | 12 tests, all passed, no skips | 47.6 s |
| `scripts/audit_repository.py` | 2,019 staged files, 0 rejected | 27.8 s |
| Before tours at main `ce0ebd71` (base worktree), default draw | DATA-ACQ-002 32 maps, October 22 14 maps | 63.0 s + 18.4 s |
| After tours at `a4aeed6b` | 64 + 28 PNGs and 64 + 28 object/light dumps byte-identical; frame reports differ only in their output path | 48.8 s + 26.0 s |

Mutant runs: the first two `--mutations` attempts stopped before finishing (a shared Unicorn machine outlived the
effect families' stack resize; a mutant with a duplicate `case` label did not compile); the third found one
equivalent mutant (`model_bones >= 0` was redundant with the −1 encoding), which was removed from the C instead.
The fourth run is the one reported. No other validator's mutants ran.

Refusals before → after: Muun records 0/16 → 16/16; Uruk keyed 0x806e/12 (weather 1, host) 39 refused → 0; default
worlds unchanged (weather off, no Muun OBJECT): every tour counter identical.

## Shared files (minimal hooks)

- `reconstructed/combat/skill_fx.c`: one include, the supported/create/move hooks.
- `reconstructed/particles/particles.c`: one include, the supported/create/move hooks.
- `native/core/mu_objects_runtime.c`: the keyed event to `owned_effect`; `uruk_weather = -1` at start.
  `native/core/mu_objects.h`: the field's comment.
- `native/Makefile`: two source lines, the Muun host rule.
- `native/tests/worlds_m_host.c`, `test_native_worlds_m.py`: the keyed refusal pin becomes created effects and the
  three flame kinds (6b).
- `scripts/validators.toml`: one row.

## Steward

Steward validators (all without mutants; ran at `2353e836`; the `--list-affected origin/main` selection incl. fallback rows): validate_app_polish1, validate_app_polish4, validate_audio_callers, validate_audio_charsel, validate_audio_combat, validate_audio_domains, validate_audio_items, validate_charsel_world, validate_icarus, validate_icarus_c2, validate_item_effects, validate_login_world, validate_meshdraw, validate_model_edge, validate_model_light, validate_movement, validate_object_render, validate_particles, validate_path, validate_render_effects, validate_render_effects10, validate_render_effects11, validate_render_effects12, validate_render_effects13, validate_render_effects14, validate_render_effects15, validate_render_effects16, validate_render_effects17, validate_render_effects18, validate_render_effects3, validate_render_effects4, validate_render_effects5, validate_render_effects6, validate_render_effects7, validate_render_effects9, validate_render_worlds_a, validate_session_party, validate_skill_fx, validate_terrain, validate_terrain_remaining, validate_viewport_monsters, validate_world_fidelity, validate_world_light_name, validate_world_particle_consumers, validate_world_tile_folder, validate_worlds_121, validate_worlds_after, validate_worlds_after2, validate_worlds_after3, validate_worlds_after4, validate_worlds_after5, validate_worlds_after6, validate_worlds_b, validate_worlds_d, validate_worlds_e, validate_worlds_f, validate_worlds_fog, validate_worlds_g, validate_worlds_g2, validate_worlds_g3, validate_worlds_h, validate_worlds_i, validate_worlds_j, validate_worlds_k, validate_worlds_l, validate_worlds_m, validate_worlds_n, validate_worlds_o, validate_worlds_p, validate_worlds_p2, validate_worlds_q, validate_worlds_q2, validate_worlds_r, validate_worlds_r2, validate_worlds_s, validate_worlds_s2, validate_worlds_s3, validate_worlds_slots, validate_worlds_slots2, validate_worlds_slots3.

No row needs another mutant pass: `validate_render_effects18`'s 35 mutants ran once (above); no other row's checks or mutant targets changed. An earlier run of 76 reviewed rows at `a4aeed6b` (before TEST-SPEED-005 and the last two merges) also passed and is kept in the table for reference; a 52-row run at `5cb92708` was stopped when main moved again and is not counted.

Environment:

```sh
export MU_RECOVERY_INTEGRATION=1
export MU_GAME_ROOT="$HOME/Library/Application Support/MuTheMatrix/prefix/drive_c/MuTheMatrix"
export MU_SECTION3="$HOME/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin"
export MU_EVIDENCE_DIR="$HOME/Documents/MTM/mu-the-matrix-native/evidence"
export MU_OBJECTS_PLAIN_DIR="$HOME/Documents/MTM/mu-mac-tools/native/scratch/objects/live/plain"
export MU_SNAPSHOT_DIR="$HOME/Documents/MTM/mu-mac-tools/native/scratch"
export MU_VALIDATOR_CACHE="$HOME/Documents/MTM/mu-mac-tools/native/cache/validators"
export MU_LANG_DIR="$HOME/Documents/MTM/mu-mac-tools/native/scratch/native-data/export/lang"   # holds muuneffects.tsv
export MU_PATH_DIRECTIONS="$MU_SECTION3"   # validate_path's directions pin
```

The private records family runs with `scripts/validate_render_effects18.py --lang-dir "$MU_LANG_DIR"`; the registry
row does not pass it, so its case count stays 540. `InstalledMuun` needs `MU_GAME_ROOT` and `MU_LANG_DIR`.

## What's left

- A native Muun OBJECT (server-created, `0x01219294`), its model, follow logic and pose: no scene draws the 16
  effects yet; the consumer, update and requests are ready for it.
- The Muun OBJECT's owner bytes for the effects (006's `ein_owner`) for Muun owners.
- The native map-object update places unfollowed records at the position; the client uses the shared pose's bone
  translation for map objects (finding §1). Not changed (it would change world captures).
- Uruk's server value (`0x0127edf3`) is not ported; the native world keeps −1 unless a caller sets it. Uruk has no
  capture.

## Cleanup

Deleted after the final checks: this lane's `renders/render-effects-018` and `scratch/render-effects-018` (tours,
reports, logs, the copied `muuneffects.tsv`), the base worktree `re018-base` and build products. No new private input
needs to survive. The worktree and local branch stay until the steward merges.
