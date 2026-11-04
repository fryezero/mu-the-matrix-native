# RENDER-ITEMS-002O

Base main `5cb6fa6d` (#284), branch/worktree `claude/render-items-002o` (Claude Opus 5.5). Checkpoints are pushed.
Only this lane is edited and built. No live client, launcher or hosted workflow is used.

Scope: the `validate_renderchar` regression INTEGRATION-GREEN-002 found (row 4, follow-up 1), a row expectation
that no longer drifts with item merges, then RENDER-ITEMS-002 part 15 (one slice of the remaining bodies).

## The regression: an oracle gap, not a C rule

`validate_renderchar` failed 2 of 390 item cases on main (4 of 398 on `d5ffde0a`). Both causes are in the
validator. `renderchar.c`'s glColor rule from #275 is right (verified).

- **Extra COLOR records (0x23ec, 0x2381; 0x2702, 0x10f6, 0x0ef9 on `d5ffde0a`).** The client does call glColor
  there. The plain `World` stubs `glColor3f/3fv/4f` like every other GL slot: as `('gl', ...)` entries in the
  `others` list, which the item comparison never checks. Only the part-13 generator and `validate_item_carry`
  record them as COLOR records (`gen_item_bodies.record_colours`). So the client stream lost the calls while
  `mu_rc_item_draws` kept them. With the calls recorded at call time, the two main cases match exactly:
  `0x23ec` calls `glColor3fv(model+0x54)` at `0x016e1805`, `0x2381` at `0x0175c4db`, both inside the body
  helper `0x016e036c` reached from RenderObjDraw's base call `0x017e16f2`. All five types are among the 46 body
  types whose recipes hold COLOR entries. #275's `validate_item_carry` already used the recording world, which
  is why it passed.
- **0x1c24 "draws nothing".** The client does not return. The 19 rank-5 bodies (`0x1c24..0x1c34`, `0x1c44`,
  `0x1c7a`, `item_pose_machine.TYPES`) run the real pose caller `0x012b5064`. The plain world has no bone
  tracks, so the client faults at `0x012b51a7` (read of address 8) with an empty stream. The check only noticed
  because `result['ok']` was false. `validate_item_next` compares these bodies with authored tracks.

## Fix (validator only; no `renderchar.c` change for it)

- `validate_renderchar.record_colours` and `ColourWorld`: the glColor recorder moves here from
  `gen_item_bodies` (which keeps the names as aliases; the generated table is unchanged). Every item
  comparison now records glColor calls as COLOR records, so the COLOR records are compared both ways.
- Rank-5 types run through `validate_item_next.rank5_world` (factored out of `rank5_cases`, same behaviour):
  authored tracks, scripted body random, the engine name lookup, compared with `mu_rc_item_draws_context` and
  the same rand count.
- Refused states are redrawn. A state the C refuses (`MU_RC_UNSUPPORTED`: record kinds, `a10/a11` on body
  types) is redrawn for the same type and counted as `refused`. Every request is now compared. The old
  `excluded` count drifted because body types refuse `a10/a11 != -1`, and every item merge adds body types. The
  character section redraws the same way.
- Two new sections, in the manifest row: `colours` (480 random states over the 46 COLOR-recipe body types)
  and `rank5` (480 over the 19 rank-5 types). `types` sweeps every generic type (not in the row).
  `--mutations` compiles the four COLOR-record mutants against all compared streams.

The row now expects fixed counts that a future item merge cannot move: 100 back checks, 60 characters,
86 light cases, 500 items, 480 colours, 480 rank-5, **1,706 comparisons**, 4 mutants. The private test
`test_private_original_render_instructions` asserts the same compared counts.

Before and after, default seed (`--cases 500`):

| Check | Before (main `5cb6fa6d`) | After |
|---|---|---|
| `items` | 2 of 390 compared mismatch (110 excluded) | 500 of 500 match (153 refused states redrawn) |
| `colours` (new) | old oracle: 451 of 480 would mismatch (every case with a COLOR record) | 480 of 480, 603 COLOR records |
| `rank5` (new) | old oracle: all fault at `0x012b51a7` | 480 of 480 |
| row expectation | stale (`excluded` 106 / `compared` 394 / 625) | fixed counts, 1,706 |

Further runs on this branch, all 0 mismatches: seed 20261017 with 5,000 item states and 1,500 per targeted
section (39 + 1,956 COLOR records, 1,515 rank-5 cases, 64 s); seeds 1 and 2 with 2,000 + 600 + 600 (25 s
each). Before part 15, a `types` sweep over every one of the 7,740 generic types with 8 random states each
compared 47,614 states with 0 mismatches (263 COLOR records, 83 rank-5 cases, 363 s).

## RENDER-ITEMS-002 part 15: body random scaling a constant body light

Bounded bodies increase **1,213 to 1,219 of 1,674** (+6: `0x171d..0x171f`, `0x1742..0x1744`). Skins stay
**17/17**, links stay **eighteen targets/twenty-four types**, **455 bodies remain**. The survey keeps 798
shapes; complete shapes go 497 to 500. The bodies set `model+0x54` to a constant vector (`0x00cfcead`), scale
it by `(rand() % 15) / 37.5 + 0.5` (`0x00cfcd74`, binary32 `mulss` in `0x00cfcb3c`), draw mesh 4 and restore
the light. `gen_item_bodies.parse_scale` reads the constants at the rand site and adds three **kind-5 scalar
programs** (kind-4 value times one constant). `renderchar.c` evaluates kind 5 in the scalar loop (one branch;
no extra rand). Details: [finding](../research/client-render-items.md#part-15-body-random-scaling-a-constant-body-light-render-items-002o).

## Checks (wall times on this Mac, `nice -n 10`)

| Check | Cases | Mismatches | Mutants | Time |
|---|---:|---:|---|---:|
| `validate_renderchar` (row, `--mutations`) | 1,706 | 0 | 4/4: colour drop/RGB/alpha 451, kind 73 | 61 s |
| `validate_item_product` (new row, `--mutations`) | 2,874 | 0 | 7/7: product off/constant/source/op/kind and mesh index 2,874, random phase 2,237 | 817 s |
| `validate_item_next` (no mutants; its world factory moved) | 14,992 | 0 | - | 915 s |
| `validate_item_carry` (no mutants; glColor recorder moved) | 114,388 (4,192 COLOR records) | 0 | - | 1,193 s |
| `validate_item_quality` (no mutants; shares the table parser) | 28,080 | 0 | - | 750 s |
| C-to-C, main library vs this one: 1,194 earlier bodies, 19 rank-5, 4 skins, 32 states each, with and without rand | 77,888 | 0 | - | 2 s |
| Admission over the 1,691 survey types: changes only for the 6 new types | 1,691 | - | - | <1 s |
| Survey re-export (`classify_item_bodies.py --tables-dir`) | 1,691 types | 6 rows flip to implemented | - | 69 s |
| Portable `reconstructed/renderchar` suite | 75 tests, 57 pass, 18 private skips | 0 failures | - | 1 s |
| `native/tests/test_native_item_textures` (portable) | 5 tests, 1 skip | 0 failures | - | 2 s |
| Build (`make -C reconstructed/renderchar`, `make -C native`) | - | ok | - | 15 s |
| `audit_repository.py` | 1,826 staged files | 0 rejected | - | 16 s |

Every validator above regenerates `item_bodies.h` from the pinned instructions without drift (most of each
wall time). Per the 2026-11-04 test budget no full gate was run in the lane, and the other renderchar rows were
not rerun: the C-to-C check shows the library is unchanged for every type they cover. The changed C is one
branch reached only by kind-5 programs, which only the 6 new types have.

## Limits and what is left

- 455 bodies remain: per part 14, 185 call body-owned effects/particles or matrix/transform services, and most
  of the rest are no-recipe count/phase clusters. The random bodies `0xb3b`, `0xb43`, `0xb45` draw rand at
  `0x011ff68d`, outside the body helpers, and stay refused.
- `validate_renderchar` still does not check the `others` list (effects and other services) of generic item
  states; glColor was the only GL call the library models in the stream.
- Wing `0x2491` (002N: only its golden frame, no feathers): not checked live. The instructions are unchanged and
  the original-client question still needs a window-only screenshot of a character that already wears it.
- `test_native_item_textures.test_private_installed_survey` (INTEGRATION-GREEN-002 row 5) belongs to
  RENDER-ITEMS-TEX-003. Texture registration was not touched, and the textures of the 6 new bodies were not
  surveyed here.

## Release

Main `5cb6fa6d` is the base and was still the latest `origin/main` at the final check (no merge needed).

Steward validators: validate_renderchar, validate_item_product, validate_item_next, validate_item_carry,
validate_item_quality (mutants only for validate_renderchar and validate_item_product; env
`MU_RECOVERY_INTEGRATION=1`, pinned captures through the `evidence` link; validate_renderchar also builds
`reconstructed/model-codec`).

Cleanup removes `mu-mac-tools/native/scratch/render-items-002o/` (no renders), the build directories, the
worktree and the local branch. No new local input needs to be kept.

