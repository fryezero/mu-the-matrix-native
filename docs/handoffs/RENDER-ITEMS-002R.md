# RENDER-ITEMS-002R

Branched from main `18ab0134`. Branch/worktree `claude/render-items-002r` (Claude Opus 5.5). No live client,
launcher, network or hosted workflow. No full gate in the lane (2026-11-04 test budget).

Scope: RENDER-ITEMS-002 part 18, the first group of part 17's "Next groups": effects that RenderObjDraw creates in
its own type case before the body draws, with an item-bone host for the `0x0150e746` bone sprites.
[Finding](../research/client-render-items.md#part-18-pre-draw-effect-programs-on-the-items-own-bones-render-items-002r).

## Result

Bodies **1,319 → 1,345 of 1,674** (+26: six swords `0x0b27`, `0x0b2a`, `0x0b4b`, `0x0b4c`, `0x0b57`, `0x0b59`; three
maces `0x0f1c`, `0x0f1d`, `0x0f2e`; four bows `0x1311`, `0x1312`, `0x1316`, `0x131d`; three shields `0x1748`,
`0x1749`, `0x1758`; ten wings `0x230b`, `0x2311`, `0x2382`..`0x2385`, `0x2394`, `0x2395`, `0x2494`, `0x2499`).
Skins 17/17, links eighteen targets/twenty-four types. **329 bodies remain.** Survey: SURVEY_LINE.

- **Census** (scratch, four survey states): 91 of the 355 remaining types create effect services before their
  first draw, in RenderObjDraw's own case; 8 only after it; 220 call none (or only rand); 36 fault (31 in strlen).
- **Reader** (`scripts/gen_item_owner_fx.py`, pre-draw mode). A basic-block trace finds the case start (the block
  after the last type compare before the first effect); the case ends at the jump to the join. The part-17
  interpreter reads RenderObjDraw's frame and the new idioms: std::string names + `0x012bd35a`, `0x0150e746`,
  TransformPosition `0x012b6ef1` on `BoneTransform + 0x30·bone`, the wave `0x0185bdc4`, the clock, the CRT sine,
  the comparison abs `0x0184f8ff`, the alpha argument, `(float)(rand() % m)`, `rand() % 2^n` gates, vec3 set/scale,
  float/int arrays, the TestFrustrum2D flag `[ebp-0xd]` and loops over constant counters (decided statically).
  40 of the 91 read; ops 15..25; 16-bit registers; bone names in `mu_rc_fx_names`. The 43 part-17 programs'
  op rows are unchanged.
- **Draws** (`gen_item_bodies`): the 40 read types fitted with the effect requests set aside; the 292-state
  comparison keeps 26, 21 of them with the part-14 supplementary probes (`PRE_EXTENDED`) and 17 with the part-13
  carry rule (`PRE_CARRY`). The pre-draw block's own rand sites are left to the effect program. `0x1313`, `0x1317`,
  `0x1319` read but fit no probe option.
- **Executor** (`owner_fx.inc` `run_fx`, shared with part 17). `mu_rc_item_draws_owner` runs the pre-draw program
  first when the host has `item_transform` (no select/shadow/`a13`). Appended ABI: `mu_rc_owner_host.bone_named`,
  `.item_transform`, `.refuse`, `.visible`; `mu_rc_owner_fx.rotation`, `.blend`, `.owner`; `mu_rc_item_pre_fx()`.
  A request on a bone outside `0..item_bones-1`, or computed from such a position, goes to `refuse`.
- **Native** (`mu_renderchar.c`): with `env->particles`, an item-bone host (named bones from the BMD, the pose in
  the new `env->item_bones`, BodyScale/BodyOrigin; flag 1); sprites → `mu_world_particles_sprite`, particles →
  `mu_world_particles_create`; OBJECT-owned particles and requests without a pose are refused and counted
  (`env->pre_counts`). `mu-render character --world-render` passes the weapons'/wing's saved poses and prints
  `pre_effects`/`pre_refused`. `mu_item_textures.c`'s probe host gets the four NULL fields.

## Effects routed vs refused

| Request (static sites over the 26 programs, loops unrolled) | Native consumer | Result |
|---|---|---|
| Bone sprites `0x0150e746` (150: `0x7f7a` 74, `0x7ef7` 50, `0x80ba` 14, `0x8458` 6, `0x7fe0` 4, `0x810a` 2) | sprite pool | routed |
| CreateSprite after TransformPosition (86: `0x7ef7` 62, `0x7f78` 24) | sprite pool | routed |
| CreateParticle `0x7ffd`/27, no owner (1, bow `0x1316`) | particle pool | routed; refused when the pool creates none |
| CreateParticle owned by the OBJECT (4: `0x810a`/17, `0x81cf`/0; wings `0x2384`/`0x2385`) | none | refused, counted |
| Any request on a bone outside the item skeleton (missing name, short skeleton), or without `env->item_bones` | none | refused, counted |

In the validator's random skeletons: 9,956 requests created bit for bit, 4,532 refused (missing names, short
skeletons), 520 rand draws, 182 states with the frustum flag clear.

## Checks

Env: `MU_RECOVERY_INTEGRATION=1`, `MU_GAME_ROOT="$HOME/Library/Application Support/MuTheMatrix/prefix/drive_c/MuTheMatrix"`,
`MU_SECTION3="$HOME/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin"`,
`MU_EVIDENCE_DIR`=the main checkout's `evidence`, `MU_LANG_DIR="$HOME/Documents/MTM/mu-mac-tools/native/scratch/lang"`,
`MU_LANG3_SNAPSHOT="$MU_LANG_DIR/live/lang3.bin"` (validate_fidelity), `MU_VALIDATOR_CACHE` = the shared cache.
All heavy steps `nice -n 10`.

CHECKS_TABLE

## Byte identity and renders

RENDERS

## Limits

- 329 bodies remain. Pre-draw programs run only with an item-bone host and the particle pools: the native
  callers outside `mu-render character` (world players/hero/actors/items, other lanes' code) do not pass
  `env->item_bones` yet, so their requests are refused and counted while the rand stream is kept.
- The TestFrustrum2D flag is 1 natively (a drawn item is in view); the client tests the 2D frustum at the OBJECT.
- Native sprites are not owner-bound (as part 17); OBJECT-owned particles have no native record.
- Bone indices outside the item skeleton are refused (the client reads the matrix before BoneTransform for -1, or
  stale bones past the count).
- Domain: the caller's OBJECT is the item's own object (`+0x5c` = type), as RenderLinkItem passes it.

## Next groups

1. **The 51 unread pre-draw types**: loops that create joints (CreateJoint `0x0153b02c`; the native joint pool
   exists, `mu_world_particles_joint`), integer clock chains with branches (`0x0b4f`..`0x0b53`), owner transforms
   `0x012b678d` on a named item bone (`0x0f1e`, `0x174a`, the wings `0x23a8`/`0x23a9`), light-pointer reads, more
   than 1,024 registers (`0x23ef`, `0x2400`, `0x2405`, `0x24be`, `0x24bf`), services before and after the draws
   (`0x0f23`..`0x0f2b`); plus the bows `0x1313`, `0x1317`, `0x1319` (fit the default probes, fail the 292-state
   comparison under every option) and the 11 read types whose draws fit no recipe (`0x0b29`, `0x0b4d`, `0x1314`,
   `0x230d`, `0x23ed`, `0x23ee`, `0x23fe`, `0x23ff`, `0x2403`, `0x2404`, `0x2497`).
2. **The 31 rank-5 set parts faulting in strlen `0x0195a4e0`** in the rank-5 pose world (not attempted here).
3. The 54 helper-group-count types; native callers passing `env->item_bones` (world parts lanes).

## Release

STEWARD

Cleanup removes `mu-mac-tools/native/scratch/render-items-002r/` and the build directories. The crops in
`renders/render-items-002r/` are the only kept artifacts (small). The worktree stays until the steward merges.
No new input needs to be kept.
