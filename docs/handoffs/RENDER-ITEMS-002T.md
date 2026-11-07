# RENDER-ITEMS-002T

Branched from `claude/render-items-002s` (`e34e3c78`, PR #331); merged main `ae5e6f36` (#331 RENDER-ITEMS-002S,
#332 RENDER-EFFECTS-019, #333 APP-POLISH-007; clean, only `mu_particles.*` among this lane's inputs) and `0c3c2777`
(HERO-ITEMS-001, #335-#337; the finding conflict resolved by keeping both: HERO-ITEMS-001 is part 21, this lane part 22). Branch/worktree
`claude/render-items-002t` (Claude Opus 5.5). No live client, launcher, network or hosted workflow. No full gate in the
lane (2026-11-04 test budget). Paused by the owner at 02:3x and resumed at 05:1x (no state lost).

Scope: RENDER-ITEMS-002 part 22, groups 1 and 2 of part 20's "Next groups", plus APP-POLISH-007's hidden-mesh finding.
[Finding](../research/client-render-items.md#part-22-frame-counter-object-bone-positions-random-vectors-and-post-programs-render-items-002t).

## Result

Bodies **1,359 → 1,363 of 1,674** (+4: maces `0x0f1f`, `0x0f20`; bow `0x130d`; `0x2713`). Skins 17/17, links
eighteen targets/twenty-four types. **311 bodies remain.** Survey: 798 shapes, complete shapes 581 → 585; both TSVs flip exactly the four types.

- **Group 1** (random helper, `rand() % 3` indices, frame counter): `0x0f1f` and `0x0f20` admitted. The helper
  `0x00d01fc6` is a random spherical vector, not a colour (op 44). New: bounded array selects with integer range
  tracking (op 45), the rendered-frame counter `[0x0bdc5ebc]` (op 42), `0x012b678d` on item bones with a NULL local
  point (op 43), CreateParticle with a computed bitmap and argument 8 (ops 46/47). `0x0f2a` reads, but its body draws
  an atlas from the frame counter that the body probes never vary: not admitted (next group).
- **Group 2** (effects after the draws): `0x130d` and `0x2713` are owner blocks in RenderPartObjectBody's case, read
  with the pre-draw idioms (`POST_FX_TYPES`, post programs): TransformPosition on the OBJECT's own bone via
  `0x0129f12c` (op 49), a register bitmap (op 48), item bones and the OBJECT light.
- **Hidden mesh** (APP-POLISH-007's finding): wings `0x2382`..`0x2385` with OBJECT +0x68 = 1 or 2 drew nothing (the
  library refused hidden values outside -1/0/own); they draw only explicit meshes and their streams equal the
  client's at any +0x68, so they join the `0x2322`..`0x2327` exemption.
- **Native**: `mu_renderchar.c` hosts the new callbacks (the item's own pose for `0x012b678d`, owner bones for op 49
  only with an OBJECT owner, the optional frame counter); `rank5_owner.inc` now clears its effect record (the appended
  `extra`, and 002S's `target`, were left uninitialized there, and native refused particles with a non-zero argument 8:
  `test_rank5_owner_effects_follow_owner_bones` caught it); `mu-render character` opens its particle pool for post types.
- **Not done**: group 3 (draw fits of read programs), group 4 (joint kinds `0x7f7c`/0xe, `0x7fd3`/4: the 40 routed
  CreateJoint requests stay refused, 0/40 drawn), group 5 (rank-5 strlen parts). See Next groups.

ABI (appended): `mu_rc_owner_fx.extra`; `mu_rc_owner_host.object_transform`, `.frame`, `.frame_known`,
`.owner_item_transform`; `mu_rc_item_post_fx()`; `mu_renderchar_env.frame_counter` (NULL default, callers unchanged).
ctypes in `validate_item_ownerfx`/`validate_render_effects5` follow; `mu_item_textures.c`'s and `mu_renderchar.c`'s
positional initializers gain the zero fields.

## Effects routed vs refused (natively)

| Request (static sites, loops unrolled) | Native consumer | Result |
|---|---|---|
| `0x0f1f`: bone sprites `0x7f7a` 4, `0x810a` 6 | sprite pool | routed (named bones; refused when absent) |
| `0x0f1f`: CreateParticle `0x810a`/0x25 owned by the OBJECT, argument 8 = rand() % 3, behind `[0x0bdc5ebc] % 3` | none | refused, counted (owner; argument 8; no native counter) |
| `0x0f20`: bone sprites 17, CreateParticle `0x855d`/1 ×2 and `0x84d1`/1 at `0x012b678d` positions behind `% 3`/`% 5` tests | sprite / particle pool | sprites routed; particles refused without a frame counter (env `frame_counter` NULL by default) |
| `0x130d`: CreateSprite `0x8081 + rand() % 3` at the OBJECT's bone 4 | sprite pool | routed only with an OBJECT owner (worn); weapons drawn without one do not run it |
| `0x2713`: CreateSprite `0x7ef7` ×3 at item bones 8, 10, 11, light from the OBJECT light | sprite pool | routed (refused outside the skeleton) |
| CreateJoint `0x7f7c`/0xe, `0x7fd3`/4 (002S, wings `0x22ec`, `0x248f`; 40) | joint pool | unchanged: routed, refused (kinds not reconstructed) |

## Checks

Env: `MU_RECOVERY_INTEGRATION=1`, `MU_GAME_ROOT="$HOME/Library/Application Support/MuTheMatrix/prefix/drive_c/MuTheMatrix"`,
`MU_SECTION3="$HOME/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin"`,
`MU_EVIDENCE_DIR`=the main checkout's `evidence`, `MU_LANG_DIR="$HOME/Documents/MTM/mu-mac-tools/native/scratch/lang"`,
`MU_LANG3_SNAPSHOT="$MU_LANG_DIR/live/lang3.bin"`, `MU_SNAPSHOT_DIR="$HOME/Documents/MTM/mu-mac-tools/native/scratch"`,
`MU_VALIDATOR_CACHE` = the shared cache. All heavy steps `nice -n 10`.

| Check | Cases / result | Wall time |
|---|---|---:|
| Reader over the candidates (scratch) | `0x0f1f`, `0x0f20`, `0x0f2a` read (132/245/234 ops), `0x130d`, `0x2713` read as post programs (15/47 ops); `--check` reproduces the 83 earlier programs at every step | 10 s |
| Draw screen (one-type library, 292 states) | maces: carry fits, 0 differing states (the supplementary probes do not fit); `0x130d`, `0x2713`: default fits, 0 differing | ~3 s per option (cached) |
| Body-table generation (`gen_item_bodies`) | 1,340 → 1,344 rows (exactly the four types); earlier rows unchanged (C-to-C below) | 767 s |
| `validate_item_predraw --mutations` (at `33e6b4c4`) | 16,832 comparisons, 0 mismatches: bodies 12,848 (44 types × 292), hidden 1,168 (4 wings × 292, +0x68 = 1/2/3/7), pre-draw 2,816 (44 × 64: 20,240 sprites, 370 particles, 2,222 joints bit for bit, 11,539 refusals, 1,488 rand draws, 308 flag-clear states, random frame counter, OBJECT bone arrays in some states); **39/39 mutants caught**, none equivalent, all compiled, anchors once; both tables reproduce | 173 s |
| `validate_item_ownerfx --mutations` (gate anchor changed; at `33e6b4c4`) | 14,964 comparisons, 0 mismatches; 14/14 mutants | 129 s |
| Hidden-mesh check (scratch, before the family existed) | wings `0x2382`..`0x2385` × +0x68 ∈ {1, 2, 3, 7, 0x7fffffff} × 60 states: 1,200 equal to the client (before: all 480 at 1/2 refused) | 30 s |
| C-to-C, main `ae5e6f36` library vs this one: 1,691 survey types × 32 states (OBJECT hidden random in -1/0/1/2) × with/without rand | 108,224 cases; 107,898 identical; the 326 different ones are the four new types (256) and the four wings' hidden-1/2 states (70) | 3 s |
| Portable renderchar suite (`test_item_predraw` with the new post-program and frame-counter tests, `test_item_ownerfx`, `test_item_types`, …) | 98 tests, 22 private skips | 0.3 s |
| Native `test_native_renderchar` (new `test_post_program_and_frame_counter_gate`), `test_native_item_textures`, `test_native_fidelity`, `test_native_world_predraw` | 44 tests, 1 skip | 102 s |
| Build `nice -n 10 make -j4` | pass | 15 s |
| `run_test_suites.py --affected origin/main` (`MU_RECOVERY_INTEGRATION=0`, 2 jobs, after the `0c3c2777` merge) | 7 suites, 1,337 tests, 0 failures, 204 skips | 267 s |
| Survey export (`classify_item_bodies --tables-dir`) | 1,691 types, 798 shapes; exactly 4 rows flip in each TSV; complete shapes 581 → 585 | 65 s |
| Docs-reading modules after the export (`test_native_item_textures`, `test_repository_policy`) and `test_native_hero_items` (6b: HERO-ITEMS-001's module uses `mu_renderchar_env`) | 27 tests | 137 s |
| Audit | 2,064 staged files, 0 rejected | 20 s |

6b: the changed shared symbols (`mu_rc_owner_fx` + `extra`, `mu_rc_owner_host` + four fields, `mu_renderchar_env` +
`frame_counter`, `mu_rc_item_post_fx`, `item_owner_fx.h`/`item_bodies.h` contents, the rank-5 record now cleared) are
used by the item validators, `validate_render_effects5` (ctypes follow), `mu_item_textures.c`/`mu_renderchar.c`
(initializers follow; the build would fail on a missing one), the world parts that fill `mu_renderchar_env`
(build), `item_textures_host.c` and the native modules above; all ran. The joint pool is unchanged.

### Affected rows, without mutants (`--no-mutants --cache --jobs 2`)

`--list-affected origin/main` (symbol level, after `make -j4`) selects 45 rows; `validate_meshdraw`, `validate_model_edge`
and `validate_movement` are kept by the symbol fallback; 9 rows build the library but use no changed symbol. All 45
ran at `eba6b606` (2,615 s wall, load 7-15): 44 passed; `validate_item_predraw` compared clean but failed the
manifest's stale expectations (main still pinned 002R's 7,592/1,664; 002S never updated them), now 12,848/1,168/2,816
with 39 mutants. After the `0c3c2777` merge (#335 REGRESS-002, #336 APP-REFRESH-008, #337 RENDER-WORLDS-RAKLION and
HERO-ITEMS-001: native/core objects, world, hero) `--only <the 45> --list-affected-since eba6b606` named 16; all
passed at `66d38864` (234 s wall). After the merge `--list-affected origin/main` selects the same 45 (no new main row
uses a changed symbol). The later commit `738fa457` changes docs only.

| Validator | At `eba6b606` (s) | At `66d38864` (s) |
|---|---:|---:|
| `validate_item_ranked` | 138.6 |  |
| `validate_item_continuation` | 182.8 |  |
| `validate_item_expansion` | 322.1 |  |
| `validate_item_types` | 40.1 |  |
| `validate_fidelity` | 67.7 |  |
| `validate_item_clusters` | 395.9 |  |
| `validate_meshdraw` | 71.5 | 52.9 |
| `validate_movement` | 72.1 | 48.6 |
| `validate_model_edge` | 150.3 | 112.7 |
| `validate_icarus_c2` | 24.1 | 18.7 |
| `validate_audio_callers` | 6.4 | 4.7 |
| `validate_renderchar` | 48.7 |  |
| `validate_item_gear` | 168.0 |  |
| `validate_render_effects5` | 4.0 |  |
| `validate_render_effects7` | 1.8 |  |
| `validate_render_effects9` | 1.6 |  |
| `validate_render_effects10` | 0.4 |  |
| `validate_render_effects11` | 0.6 |  |
| `validate_render_effects12` | 0.5 |  |
| `validate_audio_domains` | 26.1 | 24.8 |
| `validate_audio_items` | 5.7 | 3.0 |
| `validate_item_next` | 207.4 |  |
| `validate_item_coverage` | 201.8 |  |
| `validate_item_wings_next` | 220.9 |  |
| `validate_item_scalars` | 162.2 |  |
| `validate_item_chains` | 245.2 |  |
| `validate_item_quality` | 193.1 |  |
| `validate_item_product` | 53.6 |  |
| `validate_item_derived` | 230.7 |  |
| `validate_item_carry` | 664.4 |  |
| `validate_item_ownerfx` | 177.2 |  |
| `validate_item_predraw` | 199.0 (expectations stale; fixed, see right) | 136.3 |
| `validate_app_polish1` | 17.2 | 18.3 |
| `validate_app_polish2` | 3.0 |  |
| `validate_app_polish4` | 26.8 | 28.0 |
| `validate_render_effects13` | 0.4 |  |
| `validate_render_effects14` | 1.0 |  |
| `validate_render_effects15` | 0.7 |  |
| `validate_render_effects16` | 2.7 | 2.8 |
| `validate_worlds_fog` | 4.2 | 6.2 |
| `validate_render_effects17` | 5.8 | 7.4 |
| `validate_item_callers` | 1.3 | 1.1 |
| `validate_render_effects18` | 1.2 | 1.0 |
| `validate_render_effects19` | 0.6 | 0.6 |
| `validate_item_hiddenmesh` | 437.4 |  |


## Release

Steward validators: validate_item_ranked, validate_item_continuation, validate_item_expansion, validate_item_types, validate_fidelity, validate_item_clusters, validate_meshdraw, validate_movement, validate_model_edge, validate_icarus_c2, validate_audio_callers, validate_renderchar, validate_item_gear, validate_render_effects5, validate_render_effects7, validate_render_effects9, validate_render_effects10, validate_render_effects11, validate_render_effects12, validate_audio_domains, validate_audio_items, validate_item_next, validate_item_coverage, validate_item_wings_next, validate_item_scalars, validate_item_chains, validate_item_quality, validate_item_product, validate_item_derived, validate_item_carry, validate_item_ownerfx, validate_item_predraw, validate_app_polish1, validate_app_polish2, validate_app_polish4, validate_render_effects13, validate_render_effects14, validate_render_effects15, validate_render_effects16, validate_worlds_fog, validate_render_effects17, validate_item_callers, validate_render_effects18, validate_render_effects19, validate_item_hiddenmesh (all 45 ran at `eba6b606` without mutants; the 16 whose inputs the `0c3c2777` merge changed — validate_meshdraw, validate_model_edge, validate_movement, validate_icarus_c2, validate_audio_callers, validate_audio_domains, validate_audio_items, validate_item_predraw, validate_app_polish1, validate_app_polish4, validate_render_effects16, validate_worlds_fog, validate_render_effects17, validate_item_callers, validate_render_effects18, validate_render_effects19 — again at `66d38864`). Mutants: validate_item_predraw (39/39) and validate_item_ownerfx (14/14) ran with mutants at `33e6b4c4`; afterwards only the rank-5 record clear (`rank5_owner.inc`), the native host and the viewer tool changed, and both rows passed without mutants at `eba6b606` (predraw again at `66d38864`). No other row needs mutants. Env as under Checks.

Cleanup removes `mu-mac-tools/native/scratch/render-items-002t/` and the build directories. The two crops in `renders/render-items-002t/` are the only kept artifacts (small). No new input needs to be kept; the worktree stays until the steward merges.

## Byte identity and renders

- C-to-C (above): no earlier type's stream changes, with or without a rand context; the wings change only at hidden 1/2.
- `mu-render ui inventory`, installed data, `MU_LANG_DIR` set, time 123456; "before" from main `0c3c2777` (temporary
  detached worktree, removed). Control codes 0,1,2,3,7,8,4116,135 are byte-identical (PNG `97f9c25c…`, 1,676
  triangles). New types (codes 1081, 1082, 2087, 7213 = `0x0f1f`, `0x0f20`, `0x130d`, `0x2713`), before `426628a5…`
  (3,383 triangles at both levels: the plain fallback ignores the level):
  - level 0: triangles 3,383 → 3,529, 69 pixels change, → `b00b171c…`;
  - level 9: triangles 3,383 → 14,347, 829 pixels change, → `38010372…` (the recipes' glow passes: red mace, gold `0x2713`).
  - Window-only crops (before | after) in `~/Documents/MTM/mu-mac-tools/native/renders/render-items-002t/`
    (`crop_new0.png`, `crop_new9.png`, 1-6 KB). Offline native renders, not original-client pixels. Inventory items
    have no particle pool, so no effects appear there. No joint is drawn by this lane, so there is no world-scene crop.
- `mu-render character --world-render` on a synthetic skeleton: `0x2713` creates its 3 sprites on 12 bones, 1 created/2
  refused on 10; mace `0x0f20` creates none and refuses its counter-gated particles and absent named bones.

## Limits

- 311 bodies remain. `0x0f2a` reads, but its body draws an atlas from the rendered-frame counter
  (`0x0176b676`: f = ([0x0bdc5ebc] % 32) / 2), an input the body recipes do not have; not admitted.
- The body probes and the other item validators hold `[0x0bdc5ebc]` at 0. `validate_item_predraw` now randomises it
  for its 44 types (no other body there reads it); the other ~1,300 admitted bodies were never compared with a
  moving counter (the client reads it at 225 sites, mostly in RenderPartObjectBody and RenderObjDraw).
- No native rendered-frame counter: `mu_renderchar_env.frame_counter` is NULL unless a caller sets it, so the requests
  behind `0x0f1f`'s/`0x0f20`'s counter tests are refused and counted. A C refusal that matches the client's kind and
  bitmap passes the comparison by design (part 18), so the "unknown counter" refusal is covered by the portable
  `test_frame_counter_gate`, not by a mutant.
- `0x012b678d` natively uses the item's own pose (the native item has no OBJECT bone array +0x318) and the model origin
  for the OBJECT position. `0x0f1f`'s three positions written into OBJECT +0x1f4..+0x218 and `0x2713`'s OBJECT light
  (+0xec) are interpreter memory only; nothing native reads them.
- `0x130d`'s sprite needs the OBJECT's own bones: it runs only with an OBJECT owner (worn parts through
  `mu_renderchar_draw_item_owner`); weapons drawn without an owner skip it, as the client would crash on a NULL matrix
  without one. The owner gate's item-bone exemption for post programs is static (the validator's OBJECT model is the
  item model, so both counts are equal there).
- The world callers (`world_rt_item_pre`, RENDER-ITEMS-CALLERS-001) pass the item pose only for pre-draw types; post
  programs on item bones (`0x2713`) therefore run without a pose in the world, and their requests are refused (not
  counted there). Caller code was out of scope here; the fix is one condition (`|| mu_rc_item_post_fx(type)`).
  `mu-render character` (the viewer tool) now opens its particle pool for post types.
- Joints unchanged: the 40 CreateJoint requests of `0x22ec`/`0x248f` (`0x7f7c`/0xe, `0x7fd3`/4) stay refused, 0/40
  drawn.

## Next groups

1. **The joint kinds `0x7f7c`/0xe and `0x7fd3`/4** (group 4, not attempted): CreateJoint cases at `0x01544f3d`
   (`0x7f7c` jump table `0x015538e8`, subtype 0xe: LifeTime 0, width = scale, 10 tails, angle 0, light (0.3, 0.3, 1),
   +0x24 = (target − position) / max tails per axis, then a tail loop; static reading) and
   `0x01540b34` (`0x7fd3` jump table `0x01553814`, subtype 4; render type 3); MoveJoint and RenderJoints cases still to
   locate; `validate_joints` drives new kinds by listing them in `KINDS`. The target object is the item's OBJECT.
2. **A frame-counter body input** (and a native counter): unlocks `0x0f2a` and lets the item validators vary
   `[0x0bdc5ebc]`.
3. **Draw fits for read programs** (part 20's group 3, not attempted): `0x23a8`/`0x23a9`, `0x0f1e`, `0x174a`,
   `0x2301`/`0x2302`, `0x23f0`/`0x23f2`, `0x0b51`/`0x0b52`, the bows `0x1313`/`0x1317`/`0x1319`, part 18's eleven.
4. **The 31 rank-5 parts faulting in strlen `0x0195a4e0`** (rank-5 pose world) and the 54 helper-group-count types.
5. **World callers for post programs**: pass the item pose for `mu_rc_item_post_fx` types in `world_rt_item_pre`.
