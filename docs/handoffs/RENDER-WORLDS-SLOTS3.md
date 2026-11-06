# RENDER-WORLDS-SLOTS3

RENDER-WORLDS-SLOTS2's follow-ups: RenderObjectVisual's outer `rand() % 30` (`0x017f9797`) in the worlds without a
class, and Test Area 121's two slots.

- Claude Opus 5.5 lane. Worktree `~/Documents/MTM/worktrees/render-worlds-slots3`, branch `claude/render-worlds-slots3`.
- Branched from `origin/claude/render-effects-016` (#313, still open), merged origin/main `7e6a9292` (#311) as
  `4da302f9`.
- Input links `tools/python`, `evidence` and `input` point at the main checkout and are never committed.

## WIP (stopped by owner, 2026-11-06 14:4x)

No PR yet; no `ready-prs.txt` line. Code, hosts and the validator are committed and pushed.

### Done and verified

**Original (verified, Unicorn probe and `validate_worlds_slots3`).** `0x017f9758` draws the outer rand for every
object with a model in every world, before the switch `0x017f97e2`. The switch has inline cases 0..4, 6, 8..17 (jump
table `0x017fccd0`), 0x34 and 0x37. Every other world takes the default branch `0x017fcb5c`: the hooks, then the world
manager. No draw precedes the outer one in any world tried.

**Native before (static + Unicorn).**
- Worlds 0..3 and Tormenta 141: the particle visual drew the outer rand from the particle generator.
- Icarus 10: `icarus_cover` (`native/core/mu_particles.c`) drew it from the particle generator.
- 0x25/0x28: `world_flames` drew it from the object generator.
- 4/7/8: `mu_builtin_visual`'s first draw, object generator (correct place).
- Every other classless world drew none.

**Native now (`50fd4472`, `5c3ae8d1`).**
- `mu_obj_visual_flicker(world, has_model)` answers for every world with a model except 4/7/8.
- The runtime draws it once, at the top of `handler_visual` and in the non-primary branch, and stores the value in
  `rt.visual_outer_rand`.
- `world_flames` no longer draws it itself.
- Particle module, only the stand-in changed: `mu_pt_visual_host.outer_rand` is new. `visual.c` reads
  `l = (outer_rand % 30 + 70) * 0.01` instead of drawing it. `mu_world_particles_object_visual` takes the value, and
  `icarus_cover` no longer draws.

**`scripts/validate_worlds_slots3.py`** (new; row in `validators.toml`, 36 families, 22 mutants):
- Families:
  - `rng_<w>` for 0, 1, 2, 3, 4, 7, 8, 10, 37, 40 and 141, compared whole;
  - `rng_<w>` for 6, 9, 11, 18, 24, 30, 31, 33, 34, 38, 39, 41, 42, 46, 51, 56, 65..68, 73, 74, 98 and 102, compared
    up to the switch;
  - `rng_other` for the remaining classless ids 0..145.
- Iteration runs only:
  - 15 families × 120 cases, all equal;
  - all 36 families × 200 cases, all equal (0 mismatches, 0 stops).
- Mutants at 200 cases: all 22 compile and match their anchor once. 21 were detected. "Kanturu flame 0x3b without
  its draw" was not detected at 200 cases (type 0x3b is hit once in the sweep). The 1,000-case run draws named types
  60% of the time; check it there.
- Unported inner draws, counted: Devias 0x67 (`0x012affa4`) and the Kanturu hook `0x00e75089` past its flames
  (0x25, 0x3e, 0x51, 0x53, 0x5c, 0x62, 0x69).
- Hook and inline worlds whose client draws more after the outer one (probe; native has none of these visuals):
  - 11..17 and 0x34 (Blood Castle `0x017fc023`);
  - Lorencia-like 0x69 in 37/40;
  - occasional types in 30, 31, 33, 38, 46, 51, 56 and 98.
- 18, 34, 39 and 73 stop after the switch (a hook reads unmapped globals); they are counted, not compared.

**`validate_worlds_slots2.py`.**
- `rng_drawn` lost its 141 special case.
- The 16 flicker mutants were re-anchored on the new rule; "misses Vulcanus 63" and "misses Tormenta 141" were added
  in place of "draws for 141". Mutants 62 → 63.
- 200-case run of the 16 rng families: all equal. Its mutants have not run yet.

**`validate_particles.py` / `test_particles.py`.** VisualHost gained `outer_rand`. The native side now draws it
before the visual. The unit tests pass (23, 2 skipped); the validator has not been run yet.

**Tests run.**
- `reconstructed/objects/test_worlds_slots2.py` (flicker rule updated) and `test_worlds_slots3.py` pass.
- `tests/test_validators_manifest.py` passes (17).
- Native host modules, 99 tests: all worlds_* (d..s3, slots, slots2), particles, icarus, render_light, map_effects,
  render_effects6, render_effects (+9..16), helpers, sprite_draw, renderchar, effect and inventory_skin. Result: OK
  after one intended update (`worlds_i_host.c`: world 73's object generator advances by the outer draw). 450 s.
- New `native/tests/worlds_slots3_host.c` + `test_native_worlds_slots3.py` pass. They cover 29 worlds × model/no
  model, with particles attached: one object draw with a model, none without, and no particle-generator draw. Also:
  Lorencia 0x38's flare scale is `l·5` from the object generator's value, Tormenta's slot draws only its own rand, and
  Kanturu 0x3b draws the outer + the flame rand on the object generator.
- `make -j4` and `make -C native build/mu-world`: pass.

**Fidelity** (default draw). "Before" is the `4da302f9` binary (main + #313), taken once. Wall times before / after:
DATA-ACQ-002 60 / 63 s, October 22 19 / 22 s, live clock for 6/38/40/56 11 / 12 s.
- DATA-ACQ-002: **32/32 byte-identical** (PNG frames, OBJECT and light dumps), including the classless 6, 38, 40
  and 56. The live clock for those four is identical too.
- October 22: 7 of 14 views identical (Devias 2, Lost Tower, Atlans, Tarkan, Kanturu 37, Raklion, Karutan). 7 changed:

| View | Objects changed (fields) | Frame-light words | Frame 24 mean \|Δ\| (px) | Particle-generator rand calls | Static fields ≠ live |
|---|---|---|---|---|---|
| 00b Lorencia | 64 (light copy +0x1e8; 0xa8 ×7) | 873 | 0.092 (84,296) | 608 → 237 | 14 → 15 (blend_light, type 122) |
| 01 Dungeon | 17 (+0x1e8) | 285 | 0.352 | 288 → 117 | 0 → 0 |
| 02b Devias town | 15 (+0x1e8; 0xa8 ×4) | 156 | 0.002 | 356 → 164 | 4 → 5 (blend_light, type 78) |
| 03 Noria | 0 | 0 | 0.010 (frame 0: 0.030) | 747 → 199; sparkles 8 → 0 | 23 → 23 |
| 10 Icarus | 0 | 0 | 19.6 (frame 0: 18.8) | 2,329 → 9,315; created 312 → 408, effects 1 → 7 | 0 → 0 |
| 33 Aida | 16 (+0x1e8) | 75 | 0 | — | 0 → 0 |
| 51 Elbeland | 19 (+0x1e8) | 252 | 0 | — | 0 → 0 |

- The October 22 tour has no live PNG locally, so there are no image scores against live. Frame-light error near
  the hero moves slightly (Lorencia 0.0052 → 0.0066, Dungeon 0.046 → 0.043).
- **Explained by the RNG streams only (verified).** A control build kept the new plumbing but restored the old draw
  placement: the particle generator drew for 0..3/141 and in `icarus_cover`, and the object generator drew only for
  the class worlds and 0x25/0x28. It reproduced the "before" outputs byte for byte, 14/14.
- So the changes come from the moved and added draws:
  - the object generator's flicker lights and BlendMeshLight (move pass) shift phase;
  - the particle generator loses one draw per visual, which re-phases Noria's sparkles and Icarus' cloud cover
    (large-area sprites, hence the big pixel delta).
- The live RNG state is not captured, so the phase has no reference.

### Test Area 121 (not ported; slots stay 142/144)

Static outline of the custom slot `0x00d58bd8`:
- Types 6..12:
  - every mesh `m` (model +0x24) and entry `k` < mesh+6: `[0x06fd0918 + m·0xea60 + 4k] = 0.5`;
  - object light +0xec = (1, 1, 1);
  - RenderBody.
- 0x10 and 0x11: rand, then the action pick `0x012affa4` (7 calls in all; 0x11 branches on a value 0x5a), then
  RenderBody.
- 0x13..0x15: 24 TransformPosition and 28 CreateParticle (bone-placed), one rand each, RenderBody/RenderMesh (0x14:
  four meshes).
- Body/mesh-only branches: 0x2e, 0x35, 0x4c, 0x39; 0x44, 0x45, 0x47 (call `0x009681bd`); 0x1a8..0x1ad (colour from
  three vector indexes); 0x52, 0x53, 0x59, 0x5c.
- Types above 300 are never passed.

`0x06fd0918` is the model's per-vertex light (`MU_MODEL_LIGHTS`). Its readers are the RenderBody/RenderMesh wrappers
`0x00966e2c`.. and the mesh renderer `0x0151b2ca..0x0152beab`. Raklion (`0x00e94a8f`) and world 82 (`0x00e31a55`)
write it too.

What it needs:
1. A slot event "set the per-vertex light of every mesh to v" that the runtime applies to the posed model's light
   array after the transform and before the body draw.
2. A port of `0x012affa4` (also Devias 0x67).
3. Posed bones in the custom pass for 0x13..0x15, and CreateParticle to the existing consumer, refusals counted.
4. The after slot `0x00d5a6cc` (198 instructions).

121 has no capture and no warp.

### Pending (in order)

1. Final validator runs, at the code's head after the last main merge; env as below:
   - `nice -n 10 tools/python/bin/python scripts/run_validators.py --private --cache --only validate_worlds_slots3 --jobs 2 --report verify-runs/lane-mutants`
     (1,000 cases × 36 families + 22 mutants, once).
   - `scripts/validate_worlds_slots2.py --cases 1000 --mutations --only rng_57,rng_58,rng_62,rng_63,rng_64,rng_82,rng_100,rng_101,rng_128,rng_129,rng_130,rng_137,rng_93,rng_94,rng_empty,rng_drawn`
     (the 17 flicker mutants), then the `validate_worlds_slots2` row without mutants.
   - `--no-mutants --cache --only validate_particles,validate_worlds_after4,validate_render_effects16`.
   - Selection reason: `mu_obj_visual_flicker` is called only by slots2/3; `mu_pt_object_visual`/VisualHost only by
     validate_particles; worlds_after4 runs the objects runtime; render_effects16 compiles `mu_particles.c`.
     `--list-affected` over-selects through #313's combat diff and quoted paths.
2. If the Kanturu 0x3b mutant is still undetected at 1,000 cases, add more 0x3b cases or change the mutant.
3. `run_test_suites.py reconstructed/objects reconstructed/particles`, then the audit (new files: the validator, two
   tests, a host, this handoff).
4. Write `docs/research/client-worlds-slots3.md` from the sections above. Update the status lines (`docs/status.md`,
   `docs/handoff.md`, roadmap, plan row). Note that `doc/validators.toml` merges keep both sides.
5. Merge origin/main once #313 has merged (rerun only what the merge touches). Open the PR with "Steward validators:
   validate_worlds_slots3 (mutants: yes, new), validate_worlds_slots2 (mutants: flicker only), validate_particles,
   validate_worlds_after4, validate_render_effects16 (no mutants) (ran at <sha>)". Write the `ready-prs.txt` line.

Env:
- `MU_RECOVERY_INTEGRATION=1`;
- `MU_GAME_ROOT=<free-runtime prefix>/drive_c/MuTheMatrix`;
- `MU_SECTION3=~/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin`;
- `MU_EVIDENCE_DIR=<main checkout>/evidence`;
- `MU_OBJECTS_PLAIN_DIR=<mu-mac-tools>/native/scratch/objects/live/plain`;
- `MU_LANG_DIR=<mu-mac-tools>/native/scratch/render-worlds-after5/lang`.

The fidelity numbers above are final for this code. Rerun them only if the runtime changes.

Local files kept: `<mu-mac-tools>/native/scratch/render-worlds-slots3/` (env.sh, tour manifests, probe scripts; small).
The renders were deleted.
