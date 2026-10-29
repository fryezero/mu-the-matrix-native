# RENDER-ITEMS-002 part 13

Base `9b821b19`, branch/worktree `claude/render-items-002m` (Claude Opus 5.5). Checkpoints are pushed. Only
this lane is edited and built. No live client, launcher or hosted workflow is used.

## Coverage and implementation

Bounded bodies increase **1,053 to 1,162 of 1,674**, adding **109 types**. Skins stay **17/17** and links stay
**eighteen targets/twenty-four types**. **512 bodies remain** (469 non-stopping). Exact membership is in
`gen_item_bodies.CARRY_TYPES` (89) and `COLOUR_TYPES` (20) and in both TSVs. The survey has 461 complete shapes,
up from 362. Shape identities, ranks and stops are unchanged.

Selection followed the survey. All 578 remaining non-stopping types were probed with glColor recorded. 175 fit
the probes. In the full comparison, 155 failed, all at quality 0-2 (the probes use quality 9). Body light of a
later helper was 97 of them. The details are in the
[finding](../research/client-render-items.md#part-13-carried-model-fields-and-immediate-glcolor-records-render-items-002m).

- **Carried model fields (89 types).** The client model keeps BodyLight, level word, shade and `+0xca` after
  the body's draws. The ancient pass, PartObjectColor2 and the other helpers start from them. Rows gain a `carry`
  column. `emit_parameter_body` writes the last BODY/MESH draw of each recipe back to the model. The generator
  infers with the probe entry `mu_rc_item_draws_carry`, which is the generic path with the client's last-draw
  fields written back after each helper. Carry is off for every earlier row.
- **Immediate glColor records (20 types; 32 of the 109 emit them).** `glColor3f/3fv/4f` calls join the stream
  as COLOR records (`MU_RC_ENTRY_COLOR`, kind/alpha/RGB at call time), inferred like other draw words. The
  native item consumer sends them to the backend's current colour and GL recorder. The texture prober skips
  them. They are visible only through mesh mode `0x40` with lighting on, or to later GL consumers. In the gallery
  they change zero pixels.

`renderchar.c` changes are confined to the recipe executor: COLOR entries in `apply_recipe`, `write_back`, the
carry probe entry and the part_body probe route. `validate_renderchar.c_stream/client_stream` understand COLOR
records and the optional carry list. Earlier worlds never produce either. The part-11/12 validators' row regex
now allows the new column.

## Checks

`scripts/validate_item_carry.py --mutations` has a manifest row and the private test
`ItemCarry.test_original_instructions`. It passes **114,388 comparisons, zero mismatches**: 31,828 full body
streams (109 types times 292 states, body random trapped, glColor recorded), 79,744 carry boundary cases (16
levels, 7 qualities, 4 option/ext pairs, 2 flag words) and 2,816 colour-extreme cases with 4,192 COLOR records.
All **12/12 separately compiled mutants** are caught (counts in the finding). Four equivalent candidate mutants
are documented and not counted. The body table reproduces from the pinned instructions.

Inherited validators were rerun on the final merged source through `scripts/run_validators.py --private`. Each
gives identical counts: part 12 `validate_item_chains` **35,346 cases, zero mismatches, 17/17 mutants**; part 11
`validate_item_scalars` **26,154, zero, 11/11**; part 10 `validate_item_wings_next` **33,622, zero, 12/12**.
With this part, that makes **209,510 instruction comparisons, zero mismatches, 52/52 mutants**.

Compiled C-to-C, base `9b821b19` library against this one: **1,038 earlier types (1,034 bodies and 4 skin
types) in 33,216 random cases** and 960 link cases, zero mismatches. Over all 1,691 survey types, admission
changes for exactly the 109 new types. Portable `test_item_carry.py`: **4 tests, one private skip**. It checks
admission and refusal outside the domain, the COLOR records of the 32 colour types, and that carry types leave
the model at the fields of the last body draw. Portable renderchar suite in the gate: **67 tests, sixteen private skips**.

## +13 glow finding

The "+13 saturated white" of parts 11/12 is not a glow-pass bug. The passes match the original: body at 0.9,
additive chrome `0x240`/`0x1040` at 0.9/0.81, then additive Shiny01/Chrome01 `0x48`/`0x44` in the EnchantEffect
colour. GL-style clamping and all six special bitmaps load. The offline renders lacked `MU_LANG_DIR`, so
`mu_lang` was NULL and the enchant colour stayed `env.glow_color = (1,1,1)`. With the local decoded tables, code
0 glows orange (table default 1, 0.5, 0) and code 28 pale lavender (0.8, 0.8, 1). White pixels in the crop fall
from 241 to 89. `mu-render ui inventory` now prints a stderr warning when the table is missing. Its JSON output
and hashes are unchanged.

## Native gallery

`mu-render ui inventory` with installed geometry and textures and `MU_LANG_DIR` set rendered codes 26, 46,
1547, 3098, 3643 and 7196 (types `0x0b00, 0x0b14, 0x10f1, 0x1700, 0x1921, 0x2702`) at time 123456. All six
models are drawn and none are missing. The before binary uses the `9b821b19` item sources with the same
surrounding renderer.

- **Level 0:** triangles go **1,858 to 2,695** and **4,415 of 1,804,656 pixels** change. The refused fallback
  drew `0x0b00`'s effect meshes as an opaque black quad; now its blade and translucent passes are drawn.
  Framebuffer SHA-256 is `28663481…5ccc` before and `38a89608…36f2` after.
- **Level 13:** triangles go **1,858 to 14,623** and **6,728 pixels** change, with coloured +13 glow passes.
  SHA-256 `28663481…5ccc` before, `33e5f254…ce16` after.
- Ignoring the COLOR records natively leaves the level-0 framebuffer byte-identical (`38a89608…`).

The ordinary control (codes 0,1,2,3,7,8, 162 triangles) is byte-identical, framebuffer SHA-256
`df03a29015909de199d353d327efd2b852f79f813bd5260d0358622313b14930`. Two crop pairs were inspected. These are
offline native renders, not original-client pixel comparisons.

## Limits and what is left

Of the 469 non-stopping refusals, 187 fit no recipe (non-aligned phases, unexplained words), 169 have
body-owned effects/particles, 56 consume body random, 25 fit but differ at quality 1-2 (mostly wings
`0x23xx/0x24xx`), 17 fit but have the 1-ulp quality-0 blend precision, 13 need matrix/transform services and 2
differ in body light. The quality-dependent recipes (blend precision, wing quality-1 draws) need a probe set with
qualities 0-2 and a per-quality recipe column. Body effects need consumers outside the draw-record ABI. Rank-5
owner effects, Muun and nested map-object tables, and the earlier limits are unchanged.

## Release

Latest main **8eb54978** (RENDER-EFFECTS-008, RENDER-WORLDS-G3/AFTER2/Q2) was merged in **730e13d6**. The only
conflict was the appended rows in `scripts/validators.toml`; both sides are kept. No item body, link or
executor source changed in main. Main **7f18bf05** (SPRITE-DRAW-001) was then merged in **ce25c5be**. The only
conflict was the plan row next to SPRITE-DRAW-001; both rows are kept.

After the first merge, `nice -n 10 bash scripts/local-macos-ci.sh` passed 1,788 tests and all four private
validators above passed. On the final merge it passes **1,789 tests across 38 suites, 237 explicit skips, zero
failures**. Fixtures, native viewer and live readers pass, and the publication audit accepts **1,788 staged
files, zero rejected**. `validate_item_carry` passes again with the same counts. The second merge touched no
input of the part-10/11/12 validators.

Steward validators: validate_item_carry, validate_item_chains, validate_item_scalars, validate_item_wings_next
(env `MU_RECOVERY_INTEGRATION=1`; pinned captures through the `evidence` link).

Cleanup removes `mu-mac-tools/native/{scratch,renders}/render-items-002m/`, the build directories, the worktree
and the local branch. The shared Python/evidence symlinks are never committed. No new local input needs to be
kept. The gallery used the existing decoded tables in `mu-mac-tools/native/scratch/lang/` (NATIVE-LANG-001's),
which this lane does not own and does not delete.
