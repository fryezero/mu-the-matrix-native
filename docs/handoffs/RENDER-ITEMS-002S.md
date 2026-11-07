# RENDER-ITEMS-002S

Branched from `claude/render-items-002r` (`f5669f25`); merged main `6eaf3f2b` (#325, fast-forward) and `53cffd00`
(#326 RENDER-WORLDS-121, #327 TEST-SPEED-005). Branch/worktree `claude/render-items-002s` (Claude Opus 5.5). No live
client, launcher, network or hosted workflow. No full gate in the lane (2026-11-04 test budget).

Scope: RENDER-ITEMS-002 part 19, the first group of part 18's "Next groups": the unread pre-draw types.
[Finding](../research/client-render-items.md#part-19-integer-registers-runtime-branches-and-joints-in-pre-draw-programs-render-items-002s).

## Result

Bodies **1,345 → 1,359 of 1,674** (+14: swords `0x0b4f`, `0x0b50`, `0x0b53`; wings `0x22ec`, `0x230c`, `0x23ef`,
`0x2400`, `0x2405`, `0x248f`, `0x2496`, `0x24cf`, `0x24d6`; pet/item bodies `0x26f8`, `0x26f9`). Skins 17/17, links
eighteen targets/twenty-four types. **315 bodies remain.** Survey: 798 shapes, complete shapes 572 → 581; both TSVs
flip exactly the 14 types.

- **Screen first** (scratch): the 85 candidate types (53 refused by the reader, 14 read without fitting draws, 16
  after-draw, 2 CreateEffect faults) were fitted under the four probe options with a one-type library and the
  292-state comparison before any reader work. 19 fit; 14 of those now read and are admitted.
- **Reader** (`gen_item_owner_fx.py`): integer words (`cvttss2si`, `cvtsi2ss`, `cdq; idiv`, integer `rand()`, the bone
  count `+0x22`, integer add/sub/imul/shl), forward branches on runtime values (`cmp`/`test`, `comiss`/`ucomiss`,
  the `lahf` idiom) with lazily joined registers (a restart joins a slot only when it is read after the branch), if/else
  jumps, a 4,096-register file, `_itoa` names, the OBJECT position, CreateJoint `0x0153b02c`, CreateSprite with a
  rotation, `xmm1`, EH vector iterators. The 69 earlier programs read to the same op rows.
- **Executor** (`owner_fx.inc`): ops 26..41; `run_fx` takes the row's register count. An `idiv` fault refuses its
  result; a branch on a refused value refuses every later request.
- **ABI** (appended): `MU_RC_OWNER_JOINT = 3`, `mu_rc_owner_fx.target[3]`, `mu_rc_owner_host.position[3]`. ctypes in
  `validate_item_ownerfx`/`validate_render_effects5` follow; `mu_renderchar.c`'s and `mu_item_textures.c`'s positional
  initializers gain the zero position (`-Wmissing-field-initializers`).
- **Draws** (`gen_item_bodies`): the screen's options, `PRE_EXTENDED` +10, `PRE_CARRY` +8.
- **Native** (`mu_renderchar.c`): joints go to `mu_world_particles_joint` without a target object (-1); the pool does
  not reconstruct `0x7f7c`/0xe or `0x7fd3`/4, so they are routed and counted in `pre_refused`. The OBJECT position is
  the item model's origin.

## Effects routed vs refused

| Request (static sites over the 14 programs, loops unrolled) | Native consumer | Result |
|---|---|---|
| Bone sprites `0x0150e746` (170: `0x7ef7` 82, `0x8098` 44, `0x81ec` 32, `0x8180` 6, `0x8078` 5, `0x8149` 1) | sprite pool | routed (refused outside the item skeleton) |
| CreateSprite (66: `0x7f78` 24, `0x7fdd` 20, `0x7ef7` 16 + 2 rotated, `0x7f26` 4) | sprite pool | routed |
| CreateParticle, no owner (7: `0x7f66`/5 4, `0x8180`/5 3) | particle pool | routed; refused when the pool creates none |
| CreateJoint (40: `0x7f7c`/0xe 20, `0x7fd3`/4 20; wings `0x22ec`, `0x248f`), target object = the OBJECT | joint pool, target -1 | routed; unsupported kinds, counted as refused |

## Checks

Env: `MU_RECOVERY_INTEGRATION=1`, `MU_GAME_ROOT="$HOME/Library/Application Support/MuTheMatrix/prefix/drive_c/MuTheMatrix"`,
`MU_SECTION3="$HOME/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin"`,
`MU_EVIDENCE_DIR`=the main checkout's `evidence`, `MU_LANG_DIR="$HOME/Documents/MTM/mu-mac-tools/native/scratch/lang"`,
`MU_LANG3_SNAPSHOT="$MU_LANG_DIR/live/lang3.bin"` (validate_fidelity), `MU_VALIDATOR_CACHE` = the shared cache.
All heavy steps `nice -n 10`.

| Check | Cases / result | Wall time |
|---|---|---:|
| Census of the 329 remaining types with the part-18 reader (scratch) | 210 no effect service, 53 refused pre-draw, 14 read, 16 after-draw, 31 strlen, 2 CreateEffect, 3 other faults | 8 s |
| Draw screen of 85 candidates (4 probe options, one-type library, 292 states) | 19 fit (8 default/extended, 11 carry or both) | ~17 min |
| Reader over the 329 types after the extension | 36 read (14 admitted); `--check` reproduces the 69 earlier programs at every step | 8 s |
| Body-table generation (`gen_item_bodies`) | 1,326 → 1,340 rows; earlier rows unchanged (C-to-C below) | 996 s |
| `validate_item_predraw --mutations` (at `f116e667`) | 14,240 comparisons, 0 mismatches (bodies 11,680; pre-draw 2,560: 19,241 sprites, 269 particles, 2,196 joints bit for bit, 10,725 refusals, 1,011 rand draws, 280 flag-clear states); 25/25 mutants caught, none equivalent, all compiled, anchors once; both tables reproduce | 758 s |
| `validate_item_ownerfx --mutations` (shared executor; `gate-target` anchor narrowed; at `f116e667`) | 14,964 comparisons, 0 mismatches; 14/14 mutants, the same detection counts as parts 17/18 | 147 s |
| C-to-C, main `53cffd00` library vs this one: 1,691 survey types × 32 states × with/without rand | 108,224 cases; 107,328 identical, the 896 different ones are exactly the 14 new types | 3 s |
| Survey export (`classify_item_bodies --tables-dir`) | 1,691 types, 798 shapes; exactly 14 rows flip; complete shapes 572 → 581 | 78 s |
| Portable `test_item_predraw` + `test_item_ownerfx` | 14 tests, 2 private skips | 0.1 s |
| Native `test_native_renderchar` (new `test_wing_joint_and_random_bone_programs`: `0x22ec` 20 joints refused by the pool, sprites created; `0x23ef` 0 refused on 64 bones, 2 on 40), `test_native_item_textures` (installed survey; 6b pins unchanged), `test_native_fidelity` | 36 tests, 1 skip | 101 s |
| Build `nice -n 10 make -j4` (after the `53cffd00` merge) | pass | 19 s |

STEWARD_PLACEHOLDER

## Byte identity and renders

- C-to-C (above): no earlier type's stream changes, with or without a rand context.
- `mu-render ui inventory`, installed data, `MU_LANG_DIR` set, time 123456; "before" from main `53cffd00` (temporary
  worktree, removed). Control codes 0,1,2,3,7,8,4116,135 are byte-identical (framebuffer `b38597f2…0a6a`, 1,676
  triangles, as in 002R). New types (codes 105, 109, 6182, 6409, 6150, 6633, 7186 = `0x0b4f`, `0x0b53`, `0x230c`,
  `0x23ef`, `0x22ec`, `0x24cf`, `0x26f8`; one does not fit the grid), before `6dd298c9…f848` (2,319 triangles, the
  plain fallback ignores the level):
  - level 0: triangles 2,319 → 2,733, 486 pixels change, → `e9df018a…7e66`;
  - level 9: triangles 2,319 → 8,317, 901 pixels change, → `f8680298…fab3`.
  - Window-only crops (before | after) in `~/Documents/MTM/mu-mac-tools/native/renders/render-items-002s/`
    (`crop_0.png`, `crop_9.png`, 6-9 KB). Offline native renders, not original-client pixels. Inventory items have no
    particle pool, so no effects appear there.

## Limits

- 315 bodies remain. Not admitted although their draws fit: `0x0f1f`, `0x0f20`, `0x0f2a` (the random colour helper
  `0x00d01fc6`, arrays indexed by `rand() % 3`, the unsigned frame-counter gate `[0x0bdc5ebc] % 3` needing a host
  field); `0x130d`, `0x2713` (effects after the draws).
- The float condition and the join `jump` have no mutant: their one use (`0x0b53`) computes a value no request reads.
  No admitted program joins a value across a branch; the join machinery is exercised by the reader only.
- Joints: no native target object index, and the pool does not reconstruct these kinds (RENDER-JOINTS lanes). The
  OBJECT position natively is the model origin.
- As part 18: native world callers outside `mu-render character` do not pass `env->item_bones` (later lane); their
  requests are refused and counted, the rand stream kept. The TestFrustrum2D flag is 1 natively.

## Next groups

1. **The random colour helper `0x00d01fc6`** and `rand() % n` array indices (a `select` op over joined registers), plus
   a frame-counter host field: unlocks `0x0f1f`, `0x0f20`, `0x0f2a` (draws fit with carry).
2. **Effects after the draws** in RenderObjDraw (`0x130d`, `0x2713` fit by default; `0x0f23`..`0x0f2b` do not fit).
3. **Draw fits for read programs**: `0x23a8`/`0x23a9`, `0x0f1e`, `0x174a`, `0x2301`/`0x2302`, `0x23f0`/`0x23f2`,
   `0x0b51`/`0x0b52`, the bows `0x1313`/`0x1317`/`0x1319` and the part-18 eleven: they read (or nearly) but no probe
   option fits their draws.
4. **The 31 rank-5 set parts faulting in strlen `0x0195a4e0`** in the rank-5 pose world (not attempted here), and the
   54 helper-group-count types.
5. Native callers passing `env->item_bones` (world parts lanes); joint kinds `0x7f7c`/0xe and `0x7fd3`/4 in the pool.
