# CLOAK-002

Branch/worktree `claude/cloak-002` (Claude Opus 5.5), from `origin/main` `02e4d94d` (#344 RENDER-ITEMS-CLOAK). No
live client, launcher, network or hosted workflow. No full gate in the lane (2026-11-04 test budget).

Scope: the follow-up to RENDER-ITEMS-CLOAK:
- the rest of CreateCloth;
- the glow pass;
- the sub-types;
- the armour cloths (documented only);
- the wind.

[Finding: client-render-items.md part 27](../research/client-render-items.md#part-27-every-createcloth-case-and-the-glow-pass-cloak-002).

## Result

- **CreateCloth `0x01357ccc`: every case (verified).** 54 wing types in 34 case bodies (the switch `0x01357e5c` and
  its byte table `0x0135ea14`), plus the arg 4 = 1 robe (`0x01357d1d`, `Player\Robe01/02.jpg`).
  - 31 bodies are a table of their immediates (`cloth_defs` in `reconstructed/cloth/cloth.c`). Each entry holds
    Create's grid, bone, origin, size, bitmaps and type, then the uv scale/offset, push, SetGlow and spheres.
  - Three bodies have their own code:
    - `0x23ec`/`0x23fd`/`0x2402` scale every value by OBJECT `+0xa0` / 0.9 (/ 1.2 in character select, SceneFlag 5);
    - `0x23f1`/`0x2401` go through `0x013a0242`;
    - `0x24c6` uses the angle-matrix variant on bone 47.
  - Level glows: `0x2396` from +9; `0x239e`, `0x23a0`, `0x23a1`, `0x23a5`, `0x23a7` from +11.
- **Angle-matrix Create (verified).** Slot 1 `0x00fd77dc` calls Create, then writes AngleMatrix(angles) to `+0x48`
  and sets `+0x44`. Later SetFixed calls take slot 5 `0x00fd7d2a`: the row is rotated by that matrix, and the origin
  goes through RotatePosition `0x012b7019` and is added.
- **Sub-types (verified).**
  - SetFixed takes Models[OBJECT `+0x60`] for `0x5bc`/`0x5bd`.
  - RenderCloth's draw tests hide the cloths for:
    - the sub-types `0x431`/`0x432`;
    - skin-3 classes under the 14 sub-types of `0x009a0989`;
    - both actions `0xe4`;
    - the class indices `0x271`/`0x272`.
  - `mu_cloth_draw_allowed` now takes the class byte and the sub-type.
- **Glow pass (verified).** Render's `0x00fd9663` runs after the front and back faces. It calls EnableAlphaBlend
  (additive) and BindTexture(glow), sets `glColor4f(b, b, b, alpha)` with b = wave·(max − min) + min, wave =
  `0x0185bdc4(−speed, 0)`, then draws one front-wound GL_QUADS stream. `mu_cloth_render` draws it and now refuses
  only type `0x40000000` (flare sprites) and a mesh (`+0xc0`); no wing case uses either.
- **Native** (`native/world/world_cloak.c`; hooks: one argument more in `parts/hero.c` and `parts/players.c`):
  - CreateCloth gets the wing level (the hero's wing record, the player's wing slot), scene 6, sub-type 0 and the
    OBJECT scale.
  - The 59 cloth and glow bitmaps load the first time a cloth binds them, with LoadBitmap's filter and wrap. The GL
    set is uploaded again when a new bitmap arrives.
- **Armour cloths: no (documented, static).** `0x0135ea29` (every character: CreateCharacter sets OBJECT `+0x3b` at
  `0x0137dbd7`) and `0x01362755` fill the second list, OBJECT `+0x48`. MoveCloth steps both lists. RenderCloth draws
  that list with white light behind `0x01362edc`.
  - `0x0135ea29` switches on the base class (0, 3, 4, 8, 9, 0xc, 0xf) and the body-part skin at CHARACTER `+0x9bc`.
    It needs:
    - the mesh passes (`0x00fd7986`, `0x00fd9c61`, `0x00fd97de`);
    - the flare-sprite type `0x40000000`;
    - a second glow `0x00fd9f97`;
    - `0x013bb3fd`/`0x013bb4cd`;
    - a re-create path on body-part changes.
    That is not bounded for this lane.
  - `0x01362755` covers NPC/monster class indices `0x37`, `0x169` and `0x3a9`/`0x3ab..0x3ad`. Native draws those
    outside RenderCharacter, so it has no caller yet.
- **Wind.** The client's frame driver walks the wind five times per logic step in every scene from start-up, on the
  per-thread rand() that WinMain seeds with `srand(time)` (19 `srand` sites). No native stream can match it.
  - Native now walks from the frame driver's logic step 0 (`a->walk.frame.clock.logic_steps`), not from the first
    cloth draw. The wind at a frame depends on the steps since the runtime started, not on when a wearer came into
    view. The rand stream is still native's own; a first catch-up walks at most 2^20 logic steps.
- **Not this lane (at rest):** the guild-war flags, the duel manager and the hiding buff (part 25), and buff `0x12`
  of the draw test. Native characters have none.

## Checks

Env: `. ~/Documents/MTM/mu-mac-tools/native/private-env.sh`. That sets `MU_RECOVERY_INTEGRATION=1`, `MU_GAME_ROOT`,
`MU_SECTION3=$HOME/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin`, `MU_SNAPSHOT_DIR`,
`MU_VALIDATOR_CACHE` and the rest. Heavy steps ran with `nice -n 10`, `make -j4`, `--jobs 2`, every command from the
repository root.

| Check | Result | Wall |
|---|---|---:|
| `make -j4`, then `make -C native client world` | pass | incremental |
| `validate_item_cloak --mutations` (once, final `cloth.c`, at `fa07f862`'s code) | **5,694 cases, 0 mismatches, 0 stopped**: create 278, step 2,224, render 2,224, wind 200, gate 768; **65/65 mutants caught**, all compiled, every anchor once, none equivalent | 684.2 s |
| `--list-affected origin/main` (symbol level, after `make`) | 13 rows (3 by fallback); 11 libmunative rows use no changed symbol | 85.8 s |
| `run_validators.py --private --no-mutants --cache --affected origin/main --jobs 2` at `fa07f862` | 12/12 pass; `validate_item_cloak`'s registry total was mistyped (5,494); fixed in `ac5aa72b` and rerun: pass, 5,694 cases | 300.8 s + 140.3 s |
| `run_test_suites.py --affected origin/main` (`MU_RECOVERY_INTEGRATION=0`, 2 jobs) at `ac5aa72b` | 7 suites, 1,350 tests, 1,138 passed, 212 skipped, 0 failures | 379.9 s (454 s with selection) |
| Private, from the root: `test_native_item_cloak` (portable 11, Unicorn 1, scenes 2), `test_native_world_predraw`, `test_native_hero_items`, `test_native_players`, `test_world_parts`, `test_render_effects20`, `test_render_effects21` | 65 tests OK | 247.2 s |
| `tests.test_validators_manifest` | 17 tests OK | 0.7 s |
| `scripts/audit_repository.py` (after the main merge `90c5023b`) | 2,098 staged files, 0 rejected | 38.3 s |

Rows at `fa07f862` (s): icarus_c2 23.0, audio_callers 6.9, audio_domains 26.6, audio_items 4.6, movement 61.4,
render_effects16 3.9, worlds_fog 9.3, item_callers 1.8, render_effects17 7.9, render_effects18 1.6, render_effects19
1.1, inventory_fx 8.3; item_cloak 140.2 at `ac5aa72b`.

6b/8b review of the changed exported symbols:
- `mu_cloth_wing_create`, `mu_cloth_wing_cloths`, `mu_cloth_render` and `mu_cloth_draw_allowed` have new
  signatures.
- `mu_cloth_create_angles` and `mu_cloth_set_glow` are new.
- `mu_cloth`, `mu_cloth_host` and `MU_CLOTH_WINGS_MAX` changed layout.
- `world_cloak_draw` takes the wing level.
Their only users are `world_cloak.c`, the two parts, `test_native_item_cloak.py` and `validate_item_cloak.py`. The
modules that run world scenes with players and hero items are in the private run above.

Mutants (all caught): the earlier 38 (three wing anchors moved into the table) plus 27 new ones:
- table: an origin, a sphere radius and a glow minimum;
- an alias;
- the level test;
- glow: its state, brightness formula, period sign, cosine branch and speed gate;
- the character-select test and the 0.9 scale;
- the `0x23ec` negation;
- arg 4's back bitmap and the admangto sphere;
- `0x24c6`: its bitmap and angles;
- the custom flag, rotation, origin scale, origin swizzle and taper;
- the sub-type model and the draw test's sub-types and skin 3;
- the `0x8000` force and gravity 180.

## Scenes, byte identity, renders

- **Byte identity, one default-draw sweep** (`fidelity_tour.py render`, no draw_all). `mu-world` was built from main's
  six sources (base `02e4d94d`) and from this branch. The manifests are copies with the moved paths.
  - October 22: 28/28 PNG and 28/28 OBJECT/light dumps identical (21.3 / 19.1 s).
  - DATA-ACQ-002: 64/64 and 64/64 identical (44.4 / 42.7 s).
  - The tours have no wearer in view.
- **#344's six cloaks.** Lorencia `mu-walk` soft 960×600, the unit test's scene plus three players (91 frames,
  every 15):
  - frames 0..90 are byte-identical between main and the cases/glow commit `cc4002fb`;
  - the wind commit `ed9a54e8` walks the wind from logic step 0. Here that is one logic step (5 rand calls) more
    before the first draw, so the cape shapes differ: every frame changes;
  - counts are unchanged (created 5, steps 455, drawn 35, gated 7). These cloaks have no glow.
- **New cases.** One class-0 player (`dir=5`, +13) per case at tile 127,126, hero class 1 at 128,124, soft 1280×800,
  frame 60, main | branch. 27 item-range cases (50.8 s for 54 runs):
  - every one draws its cloths (created/drawn in the run report);
  - `0x2317`, `0x23f1` and `0x24c6` change only behind their wing models (2,535 / 699 / 1,436 pixels in the cape
    area);
  - `0x2490`/`0x2504` (`12:426`): the native player loader gives no wing for that record, so no crop;
  - `0x34e6..0x34eb` are beyond the item range: Unicorn only;
  - headless GL `mu-world` draws `0x239e` +13 (three cloths, glows).
- Window-only crops (offline native renders, not original-client pixels), in
  `~/Documents/MTM/mu-mac-tools/native/renders/cloak-002/`:
  - `crops_cases_before_after.png` (27 cases, main | CLOAK-002);
  - `crop_six_main_vs_final_f45.png` (the wind change on #344's cloaks);
  - `crop_gl_239e.png`.

## Limits

- **Armour cloths** `0x0135ea29`/`0x01362755`: not ported (above). Every character of base class 0, 3, 4, 8, 9, 0xc
  or 0xf with one of the listed body-part skins still lacks the client's armour cape (e.g. the Dark Lord's).
- **Flare sprites and mesh passes** (type `0x40000000`, `+0xc0`): only the armour cloths use them. `mu_cloth_render`
  refuses them.
- **Inputs at rest:** guild-war / duel / hiding buff (the flag and arg 4), buff `0x12` and buffs `0x3d`, `0x48`,
  `0xb2`, `0x118` (MoveCloth speed 0); sub-type 0 for native characters; scene 6.
- **Wind:** native's own rand stream (above); not the client's values.
- **Group-21 types** `0x34e6..0x34eb` and `0x2490`: compared in Unicorn, no native wearer.
- The part 25 limits (pose, BodyScale/BodyOrigin inference, the untested 0.01 floor, quads as two triangles, no live
  capture) still hold.

## Release

Steward validators: validate_item_cloak (new families and mutants; mutants once, 65/65, on the final `cloth.c`),
validate_icarus_c2, validate_audio_callers, validate_audio_domains, validate_audio_items, validate_movement,
validate_render_effects16, validate_worlds_fog, validate_item_callers, validate_render_effects17,
validate_render_effects18, validate_render_effects19, validate_inventory_fx. All ran without mutants at `fa07f862`
(validate_item_cloak again at `ac5aa72b`, registry total only). No other row needs mutants.

Cleanup: the scratch folder `mu-mac-tools/native/scratch/cloak-002/` and the build directories are removed, and only
the three crops above are kept. No new input needs to be kept. The worktree stays until the steward merges.
