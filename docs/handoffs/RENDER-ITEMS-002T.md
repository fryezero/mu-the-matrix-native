# RENDER-ITEMS-002T

Branched from `claude/render-items-002s` (`e34e3c78`, PR #331); merged main `ae5e6f36` (#331 RENDER-ITEMS-002S,
#332 RENDER-EFFECTS-019, #333 APP-POLISH-007; clean, only `mu_particles.*` among this lane's inputs). Branch/worktree
`claude/render-items-002t` (Claude Opus 5.5). No live client, launcher, network or hosted workflow. No full gate in the
lane (2026-11-04 test budget). Paused by the owner at 02:3x and resumed at 05:1x (no state lost).

Scope: RENDER-ITEMS-002 part 21, groups 1 and 2 of part 20's "Next groups", plus APP-POLISH-007's hidden-mesh finding.
[Finding](../research/client-render-items.md#part-21-frame-counter-object-bone-positions-random-vectors-and-post-programs-render-items-002t).

## Result

Bodies **1,359 → 1,363 of 1,674** (+4: maces `0x0f1f`, `0x0f20`; bow `0x130d`; `0x2713`). Skins 17/17, links
eighteen targets/twenty-four types. **311 bodies remain.** SURVEY

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

CHECKS

## Release

RELEASE

## Byte identity and renders

RENDERS

## Limits

LIMITS

## Next groups

NEXT
