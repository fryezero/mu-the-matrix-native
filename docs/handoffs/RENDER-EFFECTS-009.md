# RENDER-EFFECTS-009

The combat-effect leftovers of RENDER-EFFECTS-007: the named-bone service, arrows 0x615/0x617, bow 0x12f9's sparks
in the native session with that bow's joint and particle kinds, and the white 0x5b0/0x5b1 arrow quads.
[Finding, addresses, measurements and limits](../research/client-render-effects-009.md).

Claude Opus 5.5 lane.

- Branch `claude/render-effects-009`, worktree `~/Documents/MTM/worktrees/render-effects-009`, from origin/main
  `f858e134`, merged with `2bd386f5` (#281 RENDER-WORLDS-AFTER4).
- Input links `tools/python` and `evidence` come from the main checkout and are never staged.
- No live game, network, item/stat or inventory operation.

## What landed, per scope item

1. **Named-bone service: verified.**
   - `native/core/mu_named_bones.{c,h}` holds `0x012bd35a` (index by name, fallback), `0x0129f18a` (matrix by name,
     global or own buffer) and `0x0129f12c` (the owner bone's range check).
   - The skill environment gains `bone_named` / `bone_transform` (TransformPosition `0x012b6ef1`).
   - The combat session answers them from the effect's own posed model (inference for the client's global
     BoneTransform).
2. **Arrows 0x615 and 0x617: verified.**
   - Create (0x616's body; 0x617's light is 1) and move (Line003; red_01, red_02, t1..t5; `0x0150e746`) are in
     `arrow_fx.inc`.
   - Their models, with 0x613/0x614/0x616's, load natively (`mu_combat_arrow_file`).
   - `--combat-bow 0x1329` / `0x132f` now fire four arrows each, where 0 fired before.
3. **Bow 0x12f9's sparks in the session.**
   - After the shots, 15 Spark02 sparks fire at TransformPosition(hero bone, (0, 10, −130), 1). The bone is the
     stand-in 0 for a byte of another CharactersClient slot (see limits).
   - Joint 0x7fd5/3 (the sparks') and joint 0x7fd6/5 (the trails of arrows 0x458/0x471/0x474) are **verified**.
     The native maps an arrow's "this effect" joint owner to an effect object.
   - Particle 0x7f5a/0xd (Carow's smoke) is **verified**.
   - Bow 0x12f9's scene: **unsupported 130 → 0**. 0x12f8 goes 4 → 0 and 0x12f6 3 → 0.
4. **0x5b0/0x5b1 white quads.** The cause is texture resolution:
   - `devil_arrow.jpg` and `arrows_angelic.jpg` are not in `Data\Skill\`.
   - OpenTexture's later steps find them. 0x5b1's comes from `Data\Item\Texture\` (mu_texture_names). 0x5b0's comes
     from the bitmap-name map: startup `LoadBitmap("Effect\devil_arrow.jpg", 0x8182)` at `0x01833b47` (static).
   - The combat loader retries the bow arrow's missing meshes this way (`arrow_textures_retried`). The arrows now
     draw textured.
5. **Not done:** the six pet particle kinds, and the 007 arrow paths (the ground test of skills
   0x7e7/0x7fc/0x7fd, the arc skill 0x2d8, 0x442 with a straight skill, 0x45e's render-time particles and decal).

## Checks

- `scripts/validate_render_effects9.py --cases 20 --mutations` (recorded run): **3,040** original-instruction cases,
  zero mismatches; **25/25** compiled mutants caught.
  - Per family: CreateEffect 120, MoveEffect 120, named bones 400, joint create/move/render 400 each (0x7fd5/3 and
    0x7fd6/5), particle create/move/render 400 each (0x7f5a/0xd).
  - Registered as `validate_render_effects9`. The gate run (`--cases 2`) gives 304 cases and 25/25.
  - Owner test: `native/tests/test_render_effects9.py::BowSession.test_original_instructions_and_compiled_mutants`.
- Portable tests (new, `native/tests/test_render_effects9.py`, 6 tests):
  - the named-bone worked examples (3);
  - bow 0x12f9 in a synthetic world: 4 arrows, 15 sparks, trails, 0 unsupported;
  - 0x617's named-bone sprites;
  - 0x5b0's texture from the name map (pixels change without it).
- Private validators rerun on the merged tree (`run_validators.py --private --jobs 2`, env below): **18 pass, 0 fail.**
  - validate_render_effects9, validate_render_effects, 3, 4, 5, 6 and 7;
  - validate_skill_fx, validate_particles, validate_joints, validate_combat;
  - validate_world_particle_consumers, validate_map_effects, validate_pets, validate_effects;
  - validate_item_effects, validate_helpers, validate_raven.
- Before → after (installed data, base `f858e134` built separately):
  - **33 bows:** see the finding's table. Arrows 111 → 119. Unsupported requests over the 31 bows that fired before:
    1,564 → 1,427.
  - **Ten other combat scenes:** byte-identical PNGs.
  - **DATA-ACQ-002 32 tours:** normal and `draw_all`, PNGs, OBJECT, light and reports byte-identical.
- Gate: see the PR body.

## Hash and behaviour changes (intended)

- **Combat summary.** New fields `bow_sparks` and `arrow_textures_retried`, and a new line
  `{"combat_unsupported": [[routine, type, subtype, count], ...]}`.
- **Bows 0x12f9 / 0x12f8 / 0x12f6 / 0x1300 / 0x12ff / 0x1329 / 0x132f.** Their frames change: sparks, trails,
  smoke, textured 0x5b0/0x5b1, and the new arrows.
- **No other scene changes.** The joint kinds 0x7fd5/3 and 0x7fd6/5 and the particle kind 0x7f5a/0xd are
  consumed in every world, but no DATA-ACQ-002 capture requests them.

## Integration notes (shared files, minimal hooks)

- `reconstructed/combat/skill_fx.h`: two appended env hooks. `scripts/validate_skill_fx.py` gains the matching
  ctypes fields.
- `reconstructed/combat/arrow_fx.inc`: 0x615/0x617 create and move, plus the bone helpers.
- `reconstructed/joints/joints.c`: 0x7fd5/3 and 0x7fd6/5, in the existing SPARK/LASER cases.
- `reconstructed/particles/particles.c`: 0x7f5a/0xd, in the existing smoke cases.
- `native/core/mu_combat.{c,h}`:
  - the arrow model table (+0x613..0x617, texture subfolders);
  - the texture retry;
  - the bone services;
  - `bow_sparks`;
  - the effect objects (`objects[]` + MU_SFX_EFFECTS);
  - the JointLaser01 bitmap (`MU_COMBAT_BITMAPS` is now full, 16/16);
  - the unsupported tally.
- `native/Makefile`: one source. `scripts/validators.toml`: one row.

## Steward

Steward validators: validate_render_effects9, validate_render_effects7, validate_render_effects6,
validate_render_effects5, validate_render_effects4, validate_skill_fx, validate_particles, validate_joints,
validate_combat, validate_world_particle_consumers, validate_map_effects, validate_pets, validate_effects.

Env: `MU_RECOVERY_INTEGRATION=1`, `MU_SECTION3=/Users/frye/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin`,
`MU_GAME_ROOT="/Users/frye/Library/Application Support/MuTheMatrix/prefix/drive_c/MuTheMatrix"`.

## Remaining

- **The spark bone.** A live read of `[[0x0a39d754] + 0x9c4d]`, the byte `Weapon[33].LinkBone` lands on, with the
  hero in Lorencia. Then replace `MU_COMBAT_SPARK_BONE`.
- **0x615's particles 0x8081..0x8083/8** (310 requests in its scene) and 0x617's 0x85fb/2 and 0x8450/4.
- **The other bows' unsupported kinds.**
  - Particles: 0x7fcd/1 (0x12f3/0x12f4), 0x7f73..0x7f75/0 (0x12ec), 0x7f78/5, 0x7f26/0x1e, 0x7f5a/0x18, 0x4e,
    0x7a, 0x86, 0x8184/1, 0x8085/0x11, 0x8081..0x8083/0, 0x810a/0xe and 0x24, 0x810c, 0x83b3/1, 0x8155/2,
    0x83b8/2, 0x8084/0x1e.
  - Joints: 0x7f78/0xb; 0x7f79/0xc, 0xe, 0xf, 0x12, 0x16; 0x80e3/4, 5; 0x80e4/1; 0x828c/2; 0x814c, 0x8182,
    0x8185/0xa; 0x85cc/0.
  - Effects: 0x477/3, 4; 0x45f/0, 1; 0x60b; 0x611; 0x38b5/1.
- **The 0x615/0x617 glow meshes** draw dark natively (BlendMesh −1, mesh draw).
- **The six pet particle kinds**, the 007 arrow paths and a live comparison.

## Cleanup

- Deleted after the PR: `renders/render-effects-009` and `scratch/render-effects-009`, except
  `renders/render-effects-009/keep` until the steward has the PR.
- Also deleted: the base worktree `worktrees/re009-base`, `native/build`, this worktree and the local branch.
- No new local input needs to be kept.
