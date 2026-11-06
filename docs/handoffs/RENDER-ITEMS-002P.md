# RENDER-ITEMS-002P

Base main `7d7d694b`, merged up to `0122f192` (#305-#308). Branch/worktree `claude/render-items-002p` (Claude Opus 5.5).
Only this lane is edited and built. No live client, launcher, network or hosted workflow is used. No full gate in
the lane (2026-11-04 test budget).

Scope: RENDER-ITEMS-002 part 16. A census of the 455 remaining bodies by blocker, then the largest group that
could be validated well. [Finding](../research/client-render-items.md#part-16-census-of-the-455-remaining-bodies-and-derived-body-programs-render-items-002p).

## Census

Every remaining type was run under Unicorn in the eleven survey states (services recorded), then through the
generator probes with rand scripted and the parsed per-type programs. First blocker per type:

| Blocker | Types | Weapon | Armour | Wing | Pet/item | Draws fit without the effects |
|---|---:|---:|---:|---:|---:|---:|
| Draw word one binary32 operation from an input (**implemented here**) | 57 | 40 | 10 | 3 | 4 | - |
| Helper-group count | 54 | 2 | 0 | 13 | 39 | - |
| Effects: bone sprite `0x0150e746` + CreateParticle `0x0168fafd` | 51 | 22 | 0 | 29 | 0 | 34 |
| Effects: bone sprite `0x0150e746` only | 50 | 30 | 0 | 20 | 0 | 33 |
| No recipe: other unexplained draw words | 50 | 39 | 4 | 3 | 4 | - |
| Effects: CreateParticle + CreateSprite `0x01692eb7` at owner bones `0x012b678d` | 42 | 0 | 38 | 4 | 0 | 40 |
| Random helper `0x011ff622` (rand at `0x011ff68d`) | 39 | 39 | 0 | 0 | 0 | - |
| Fault in CRT strlen `0x0195a4e0` (helm/pants/gloves/boots of the rank-5 sets) | 31 | 3 | 28 | 0 | 0 | - |
| No recipe: draw count varies within a phase | 18 | 7 | 0 | 11 | 0 | - |
| Effects: CreateSprite only | 16 | 2 | 5 | 6 | 3 | 16 |
| GL matrix services (`glPushMatrix`/`glPopMatrix`) | 13 | 10 | 0 | 0 | 3 | - |
| Effects: all three services | 9 | 0 | 0 | 9 | 0 | 0 |
| Faults at `0x016ddc73`/`0x016df9a0`/`0x016eef60` | 7 | 5 | 0 | 0 | 2 | - |
| Fit the probes, fail at quality 0 (`0x2003`, `0x2007`, `0x2009`, `0x200f`, `0x2010`) | 5 | 0 | 5 | 0 | 0 | - |
| Other rand sites | 4 | 4 | 0 | 0 | 0 | - |
| Effects with a fault | 4 | 0 | 0 | 4 | 0 | 0 |
| Model transform `0x00966ea5` | 3 | 0 | 0 | 3 | 0 | - |
| Effects: CreateParticle only | 2 | 2 | 0 | 0 | 0 | 0 |
| **Total** | **455** | 205 | 90 | 105 | 55 | 123 |

## Why the effect group was not taken (verified on samples)

The brief's first choice was to route body-owned effect requests through the existing hook surfaces. The census
shows why that is not a routing change:

- The bone sprites (`0x0150e746`, 110 types) are CreateSprite at TransformPosition of **the item's own** posed bones
  (BoneTransform `0x06fce398`). The existing body-side surface, `mu_rc_owner_host`, transforms with the OBJECT
  owner's bones (rank-5). Many bones are named lookups (`0x012bd35a(name, -1)`) and many lights are per-frame
  random or clock products. Every request would be a refusal behind the item executor today.
- The armour group `0x1bc3..0x1c78` (38 worn chest pieces) does use owner bones (`0x012b678d`, the owner-host
  transform). But each body is a small effect program: two sprites per owner bone, then `rand() % 2 == 0` gates,
  each followed by a particle whose scale or position jitter comes from `0x011ff622` and vec3 add/subtract/normalize.
  The particle angle is OBJECT `+0x164`, which `mu_rc_owner_fx` cannot carry. Four code templates cover the 38. A
  faithful implementation needs a per-type effect program inferred from call arguments with authored owner bones.
  That is the next lane's work, not a hook change.

The largest group that could be validated well was the no-recipe "derived word" cluster, so this part implements it.

## Implementation: kind-6 derived programs

- **Generator** (`scripts/gen_item_bodies.py`). For `DERIVED_TYPES`, when the parsed programs leave draw words
  unexplained, `derive` solves `word = f32(input op k)` for one constant across every probe of the phase. Inputs:
  float generic words, object alpha, pulsed light, clock scalars, earlier programs. Ops: mul/add/sub/div. A
  candidate is kept only if the text holds that `mulss/addss/subss/divss xmm, [abs]` on that constant
  (`sse_operands`). It becomes a kind-6 program `(6, input a, ((op, k),))`. Up to three rounds.
  `DERIVED_CARRY` (13 types) also writes back the last draw's model fields (part-13 rule). A kept kind-6 program
  keeps the program it reads. With `DERIVED_TYPES` empty, the edited generator renders all 1,200 earlier rows
  identically (only the header comment line differs).
- **Executor** (`reconstructed/renderchar/renderchar.c`). One branch in the scalar loop: kind 6 reads
  `input[a]`, then applies the binary32 chain (`derived_program`). No rand.
- **Survey** (`classify_item_bodies.py`). Counts part-16 types as implemented. Both TSVs flip exactly the 57
  types; shape identities are unchanged. Complete shapes go 500 to 543.

Bodies **1,219 → 1,276 of 1,674** (+57: 40 weapons, 10 armour, 3 wings, 4 pets). Skins 17/17. Links eighteen
targets/twenty-four types. **398 bodies remain.** Screening rejected 9 fitting candidates in the full comparison
(`0x0b36`, `0x1103`, `0x1524`, and the wings `0x239c`, `0x239f`, `0x23a2`, `0x23a3`, `0x23a4`, `0x23a6`: extra
draws at quality 2 the part-9 level split does not predict).

## Checks

Env: `MU_RECOVERY_INTEGRATION=1`, `MU_GAME_ROOT="$HOME/Library/Application Support/MuTheMatrix/prefix/drive_c/MuTheMatrix"`,
`MU_SECTION3="$HOME/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin"`,
`MU_EVIDENCE_DIR`=the main checkout's `evidence`, `MU_LANG_DIR="$HOME/Documents/MTM/mu-mac-tools/native/scratch/lang"`,
`MU_LANG3_SNAPSHOT="$MU_LANG_DIR/live/lang3.bin"` (validate_fidelity). All heavy steps `nice -n 10`.

| Check | Cases / result | Wall time |
|---|---|---:|
| Census pass 1 (11 survey states × 455 types) | 5,005 client runs | 28 s |
| Census pass 2 (probes with scripted rand) / pass 3 (with parsed programs) | 455 / 125 types | 151 s / 77 s |
| Base extraction with the edited generator, `DERIVED_TYPES` empty | 1,200 rows; table identical except the header comment | 639 s |
| Candidate fits / full-comparison screens | 66 of 125 fit; 57 pass 292 states | 105 s + 16 s / 57 s + 82 s |
| Full table generation | identical to the screened table | 731 s |
| `validate_item_derived --mutations` (new row, at `aabfa252`) | 36,252 comparisons, 0 mismatches; 7/7 mutants caught, none equivalent | 787 s |
| C-to-C, main `6ef9059e` library vs this one: 1,691 survey types × 32 states × with/without rand | 108,224 cases; 104,576 identical; the 3,648 different ones are exactly the 57 new types | 8 s |
| Portable `reconstructed/renderchar` suite | 82 tests, 62 pass, 20 private skips | 1 s |
| `test_item_derived` (portable part) | 4 tests, 1 private skip | 0.2 s |
| Native `test_native_item_textures` (private installed survey; 13 white types, 0 missing bitmaps; pins unchanged) | 7/7 | 61 s |
| Native `test_native_renderchar`, `_items`, `_hud`, `test_inventory_skin`, `test_native_character` | 36/36 | 65 s |
| `tests/` manifest and policy modules (`test_test_budget`, `test_validators_manifest`, `test_orphan_validators_private`, `test_repository_policy`) | 89 tests, 22 skips, 0 failures | 16 s |
| Build `nice -n 10 make -j4` (after the `72728f3f` merge) | pass | 13 s |

Mutant detections: derived off 35,910; source index 35,713; kind 35,789; multiply 30,778; add→subtract 5,088; one
operation short 35,910; carry off 907.

`run_test_suites.py --list-affected` selects every suite here, because `scripts/classify_item_bodies.py` is an
unmapped input. That one-line change only adds the part-16 list to the survey export's union. The renderchar suite
and the native item modules above are the ones whose code changed.

### Affected existing rows, without mutants (`--no-mutants --cache --jobs 2`, at `48e39c02`)

These rows build `reconstructed/renderchar` or import the generator. 24 pass, 0 fail. Wall time 1,619 s
(12:37:27-13:04:26), load 4-20. The counts equal the earlier lanes' reports.

| Validator | Cases | Seconds |
|---|---:|---:|
| `validate_item_types` | 135,176 | 33.6 |
| `validate_item_hiddenmesh` | 116,281 | 359.5 |
| `validate_item_carry` | 114,388 | 536.3 |
| `validate_item_clusters` | 74,292 | 309.2 |
| `validate_item_expansion` | 52,172 | 259.5 |
| `validate_item_chains` | 35,346 | 193.5 |
| `validate_item_wings_next` | 33,622 | 171.2 |
| `validate_item_coverage` | 31,724 | 162.7 |
| `validate_item_quality` | 28,080 | 166.7 |
| `validate_item_scalars` | 26,154 | 130.8 |
| `validate_item_continuation` | 25,772 | 149.9 |
| `validate_item_gear` | 25,256 | 140.5 |
| `validate_item_ranked` | 17,736 | 109.5 |
| `validate_item_next` | 14,992 | 174.0 |
| `validate_item_product` | 2,874 | 55.9 |
| `validate_renderchar` | 1,706 | 42.6 |
| `validate_render_effects5/7/9/10/11/12/13` | 1,190 / 596 / 304 / 154 / 176 / 64 / 180 | 3.6 / 1.3 / 0.9 / 0.4 / 0.2 / 0.3 / 0.4 |
| `validate_fidelity` | 991 | 52.5 |

The 16 other rows that `--list-affected` names through `renderchar.c`/`item_bodies.h` (`audio_*`, `meshdraw`,
`model_edge`, `model_light`, `terrain`, `viewport_monsters`) reach them only through the native archive. They do
not call the item body executor; the C-to-C check covers that executor. Every other row is selected only by the
unmapped `classify_item_bodies.py`. Audit: 1,938 staged files, 0 rejected, 17 s.

## Byte identity and renders

- C-to-C above: no earlier type's stream changes, with or without a rand context.
- Texture survey: unchanged pins (13 white hair-only types, 0 missing bitmaps, 0 with a wearer).
- `mu-render ui inventory`, installed data, `MU_LANG_DIR` set, time 123456. The "before" binary was linked once
  from main's `renderchar.c`/`item_bodies.h`. Control codes 0,1,2,3,7,8 are byte-identical
  (`df03a290…4930`). Gallery codes 4116, 135, 2719, 2725, 6599, 138 (types `0x1afa`, `0x0b6d`, `0x1585`,
  `0x158b`, `0x24ad`, `0x0b70`):
  - level 0: triangles 4,987 → 6,025, 1,989 of 1,804,656 pixels change, SHA-256 `f2a99c37…46c2` → `f6ac4417…9a38`;
  - level 13: triangles 4,987 → 34,761, 5,044 pixels change, `f2a99c37…46c2` → `d3e4a78d…ff02`. Before, the
    refused fallback ignored the level.
  - In the window-only crops (before | after), the armour `0x1afa` gets its lit passes (and +13 glow). The
    weapons' opaque black fallback quads become thin textured blades with glow passes, and the pet and wing get
    their own passes. Crops are kept locally in `~/Documents/MTM/mu-mac-tools/native/renders/render-items-002p/`
    (`crop_0_0.png`, `crop_13_0.png`, 17-25 KB). These are offline native renders, not original-client pixel
    comparisons.
- Codes 1095 (`0x0f2d`) and 3185 (`0x1757`) have no installed model and were left out of the gallery.

## Refusals and limits

- 398 bodies remain (census table minus the 57). Effects: 174 types (+13 GL matrix, +3 model transform).
- No new hook or consumer: the derived types draw no effects, so nothing is routed or refused natively.
- Derivations are one operation on one input. Two-operation, integer-field (`0x231b`, `0x231c` flags | 0x40,
  `0x24e3`) and quality-dependent words stay refused.

## Next groups

1. **Armour owner-bone effects** (`0x1bc3..0x1c78`, 38 worn chest pieces + 2 wings): a per-type effect program over
   `mu_rc_owner_host` (owner transform `0x012b678d`, sprite/particle requests, `rand() % 2` gates, `0x011ff622`
   values, vec3 sums), with an OBJECT-angle flag on `mu_rc_owner_fx`. The draws already fit for 40/42.
2. **Bone sprites on the item's own bones** (110 weapons/wings): needs an item-bone transform behind the item
   executor (the native link path has the bones) plus named-bone lookups.
3. **Rank-5-set parts faulting in strlen** (31, mostly armour `0x1a26..0x2244`): run them in the rank-5 pose world
   (`validate_item_next.rank5_world`) like the rank-5 chest pieces.
4. **Helper-group count** (54, mostly pets/wings) and the quality-0 armour types `0x2003..0x2010`.

## Release

Steward validators: validate_item_derived (ran with mutants at `aabfa252`; its inputs are unchanged since),
validate_item_types, validate_item_gear, validate_item_ranked, validate_item_continuation,
validate_item_expansion, validate_item_clusters, validate_item_next, validate_item_coverage, validate_item_wings_next,
validate_item_scalars, validate_item_chains, validate_item_carry, validate_item_quality, validate_item_product,
validate_item_hiddenmesh, validate_renderchar, validate_render_effects5, validate_render_effects7,
validate_render_effects9, validate_render_effects10, validate_render_effects11, validate_render_effects12,
validate_render_effects13 (ran at `48e39c02`, no mutants), validate_fidelity (rerun at `4917577a` after main
`0122f192` changed `native/core/mu_objects_runtime.c`: 991 cases, pass, 51 s). The `0122f192` merge changed no
renderchar, model-codec, record-math or item-harness file, so the item rows keep their `48e39c02` results. Mutants: none needed
(validate_item_derived's ran once). Env as under Checks.

Cleanup removes `mu-mac-tools/native/scratch/render-items-002p/` and the build directories. The two crops in
`renders/render-items-002p/` are the only kept artifacts (small). The worktree stays until the steward merges. No
new input needs to be kept.
