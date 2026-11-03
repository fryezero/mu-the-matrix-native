# RENDER-ITEMS-002 part 14

Base main `d5ffde0a` (includes part 13, #275), branch/worktree `claude/render-items-002n` (Claude Opus 5.5).
Checkpoints are pushed. Only this lane is edited and built. No live client, launcher or hosted workflow is used.
The macOS 27.2 toolchain (Apple clang 21) was clean-rebuilt first. The base table reproduces byte for byte
under it.

## Coverage and implementation

Bounded bodies increase **1,162 to 1,213 of 1,674**, adding **51 types**. Skins stay **17/17** and links stay
**eighteen targets/twenty-four types**. **461 bodies remain** (418 non-stopping). Membership is in
`gen_item_bodies.QUALITY_TYPES` (51) and `EXIT_TYPES` (34 of them) and in both TSVs. The survey has 497
complete shapes, up from 461. Shape identities, ranks and stops are unchanged.

The refusals part 13 labelled "quality 1-2" and "1-ulp quality 0" have other causes (verified, details in the
[finding](../research/client-render-items.md#part-14-recordquality-probes-exit-model-fields-and-body-random-render-items-002n)).
Wing records of kind B 0x26/0x5b force glow level 9, a helper phase the record-free probes never sampled.
The binary32 per-type pulse agreed with the shared binary64 pulse at every probe clock. Some bodies leave the
model at fields other than their last draw's.

- **Supplementary probes** (part-14 types only): records `(0,0,0)/(0,0x26,0)/(0,0x5b,0)` × qualities 0/1/2/9
  × levels 0/7/13 with six further seeds, plus excellent/ancient tails at qualities 1/2/9. Wings, precision
  and UV-clock bodies fit through them (17 types without EXIT).
- **EXIT entry** (34 types): model fields at the return sites of RenderObjDraw's helper calls, inferred as a
  recipe pseudo-record. `apply_recipe` entry 4 writes them to the model and draws nothing. A probe-only fix
  makes the plain `part_body` fallback write back and advance the phase when `probe_carry` is set.
- **Body random** (2 types, `0x0b22`, `0x0f0d`): scalar kind 4, `(float)(rand() % n)` then binary32
  constants, parsed at the rand return site. The executor draws through `mu_rc_item_context.random` once per
  program in client order, only in the program's phases mask. A program row gains a `phases` byte, zero for
  every earlier row. `v.c_stream` takes an optional random source.

`renderchar.c` changes are confined to the recipe executor (EXIT, kind 4, the scalar loop after the level split)
and the probe-only fallback. The part-11/12 validators' program-row regexes accept the new field. Part 13's
table parser knows entry 4.

## Checks

`scripts/validate_item_quality.py --mutations` has a manifest row and the private test
`ItemQuality.test_original_instructions`. Client and C get the same rand sequence and must consume the same
number of results. It passes **28,080 comparisons, zero mismatches**: 14,892 full body streams (51 × 292
states), 13,056 kind-B 0x26/0x5b record cases (qualities 0/1/2/9, levels 0-15, two tail pairs), and 132
random-edge cases with 132 rand results compared. **11/11 separately compiled mutants** are caught (counts in
the finding). Omitting the EXIT level write is equivalent here (RenderObjDraw rewrites it) and is not
counted. The body table reproduces.

Inherited validators were rerun on this source through `scripts/run_validators.py --private`, with counts
and mutant detections identical to part 13's report: part 13 `validate_item_carry` **114,388, zero, 12/12**;
part 12 `validate_item_chains` **35,346, zero, 17/17**; part 11 `validate_item_scalars` **26,154, zero,
11/11**; part 10 `validate_item_wings_next` **33,622, zero, 12/12**. Each regenerates the full table without
drift. With this part: **237,590 instruction comparisons, zero mismatches, 63/63 mutants**.

Compiled C-to-C, main `d5ffde0a` library against this one: **1,147 earlier types (1,143 bodies and 4 skin
types) in 36,704 random cases**, each with and without a rand context, zero mismatches. Over all 1,691
survey types, admission changes for exactly the 51 new types. Portable `test_item_quality.py`: **5 tests,
one private skip**. It checks admission and refusal, the record helper phase on wings, EXIT fields versus the
last draw (`0xb10`), and one rand result per body pass for the random types.

## Native gallery

`mu-render ui inventory` with installed data (`MU_GAME_ROOT` = the free-runtime prefix) and `MU_LANG_DIR` set
rendered codes 42, 60, 1062, 2691, 6185 and 6571 (types `0x0b10, 0x0b22, 0x0f0c, 0x1569, 0x230f, 0x2491`) at
time 123456. All six models are drawn and none are missing. The before binary uses main's `renderchar.c` and
`item_bodies.h` with the same surrounding renderer.

- **Level 0:** triangles go **3,052 to 4,672** and **6,617 of 1,804,656 pixels** change. The sword draws its
  translucent blade passes. The refused fallback's opaque black disc becomes the blue orb of `0x0b22`. SHA-256
  `179cd9db…54af` before, `b3f28efc…d8df8` after.
- **Level 13:** triangles go **3,052 to 17,480** and **6,977 pixels** change, with coloured glow passes. SHA-256
  `179cd9db…54af` before, `b4c5cb32…19e6db` after.
- `0x2491` now draws only its frame. Its own body code draws BODY with constant hidden mesh 0 and then mesh 1
  (no effect calls), so that matches the instructions. Whether the original inventory shows feathers through
  another path needs a live look.

The ordinary control (codes 0,1,2,3,7,8, 162 triangles) is byte-identical, framebuffer SHA-256
`df03a29015909de199d353d327efd2b852f79f813bd5260d0358622313b14930`. Two crop pairs were inspected. These are
offline native renders, not original-client pixel comparisons.

## Limits and what is left

461 bodies remain. At the probe stage of the 469 part-13 refusals, 185 call body-owned effects/particles or
matrix/transform services. Most of the rest are no-recipe clusters (draw count/phase mismatches,
unexplained words). Nine random bodies (`0xb3b, 0xb43, 0xb45, 0x171d..f, 0x1742..4`) fit no recipe with
scripted rand. `0x171d` scales the body-light vector by its rand value (`0x00cfcd74`), which needs a product
source. Next useful steps: a product/vector-scale source for those random bodies, then the count/phase
clusters (`diag.py` reasons). The supplementary probes and EXIT inference apply only to part-14 types. Rank-5
owner effects, Muun and nested map-object tables, and the earlier limits are unchanged.

## Release

RELEASE_LINE

Steward validators: validate_item_quality, validate_item_carry, validate_item_chains, validate_item_scalars,
validate_item_wings_next (env `MU_RECOVERY_INTEGRATION=1`; pinned captures through the `evidence` link).

Cleanup removes `mu-mac-tools/native/{scratch,renders}/render-items-002n/`, the build directories, the worktree
and the local branch. The shared Python/evidence symlinks are never committed. No new local input needs to be
kept. The gallery used NATIVE-LANG-001's decoded tables in `mu-mac-tools/native/scratch/lang/`, which this lane
does not own and does not delete.
