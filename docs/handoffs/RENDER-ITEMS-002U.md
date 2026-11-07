# RENDER-ITEMS-002U

Branched from `claude/render-items-002t` (`53b9f7e7`, PR #341); merged main `138b756e` (#338 APP-POLISH-008, #339
RENDER-EFFECTS-020, #340 RENDER-WORLDS-KARUTAN, #341 RENDER-ITEMS-002T; clean, no conflict markers). Branch/worktree
`claude/render-items-002u` (Claude Opus 5.5). No live client, launcher, network or hosted workflow. No full gate in the
lane (2026-11-04 test budget).

Scope: 002T's "Next groups" 1, 2 and 5 (joint kinds, the rendered-frame counter, world callers). Group 3 (draw fits of
read programs) and group 4 (rank-5 strlen parts) were not attempted.
Findings: [client-render-items.md part 23](../research/client-render-items.md#part-23-the-rendered-frame-counter-in-body-draws-the-wing-joints-and-the-world-callers-render-items-002u),
[client-joints.md section 12](../research/client-joints.md#12-the-wing-streaks-0x7f7c0xe-and-0x7fd34-render-items-002u).

## Result

- **Bodies 1,363 → 1,364 of 1,674** (+`0x0f2a`), **310 remain**. Survey: 798 shapes, complete 585 → 586; both TSVs
  flip exactly `0x0f2a`.
- **51 admitted bodies were right only at frame 0.** The client's streams at counter 0 against 7/13/22 (then 1 and
  0x80000000, 16 states per type) differ for 58 survey types; 51 were admitted (swords `0x0b66`..`0x0b73`, maces
  `0x0f2f`/`0x0f30`, `0x1109`/`0x110a`, bows `0x132b`/`0x132c`/`0x132e`, staffs `0x1560`..`0x158e`, shields
  `0x1739`..`0x175d`): their mesh u/v follow `[0x0bdc5ebc]` (scrolls `((counter + 1) % 60) / 60`, a 4 × 4 atlas). Every
  probe and validator held the counter at 0. They are regenerated with counter chains and checked with a moving counter.
- **Joints 0/40 → 40/40 drawn.** `0x7f7c`/0xe (`0x01544f3d`, move `0x0156d9ef`) and `0x7fd3`/4 (`0x01540b34`, no move
  case `0x01568ebe`) are in the joint pool: ten-tail streaks toward the target argument, LifeTime 0 (drawn once, twenty
  per wing per frame). Neither reads its target OBJECT, so the native target -1 draws the client's quads.
- **Frame counter: yes.** The client increments it in the frame driver after the logic steps, before the scene render
  (`0x01852501`). Natively `mu_world_rt.rendered_frames` does the same in `mu_world_rt_frame`; `world_rt_item_pre`
  hands it to every item it is called for. `mu-render character --frame-counter N` for the viewer.
- **World callers:** `world_rt_item_pre`'s condition now includes the post-draw types (`0x2713`'s program gets the item
  pose in the world), plus the counter line at its top.

## Causes and addresses

| What | Address | Cause / reading |
|---|---|---|
| Counter increment | `0x01852501..0x01852507` | frame driver `0x01851d39`: logic steps, glClear, GetTickCount, `++[0x0bdc5ebc]`, scene render; the only write of 225 references |
| Counter reads in body draws | `0x0172dd0c`..`0x01737116` (36 sites, RenderPartObjectBody), `0x01769c75`..`0x0176c12a` (maces) | `(counter + 1) % 60` unsigned (`xor edx, edx; div`), unsigned to binary64 (`shr 31; addsd [r*8 + 0x01bd3050]`), × 1/60, sometimes negated after the vec3 setter `0x00cfcead`; `0x1109`: (counter + 1) % 16 atlas; `0x0f2a`: (counter % 32) / 2 atlas |
| `0x7f7c`/0xe create | `0x01544f3d` (prologue `0x01543f00`) | step = (target argument − position) / 10, 9 tail shifts, head = +0x58 (not set from the argument when a target object is given, `0x0153b37f`) |
| `0x7f7c`/0xe move | `0x0156d391` → `0x0156d9ef` | MoveHumming(+0x58, 25) returns the distance; jitter (rand % 1024 − 512) / width; stops when 1.5 × velocity > distance (width 50: particles `0x7f2b`, `0x7f5a`) |
| `0x7fd3`/4 | `0x01540b34`, move `0x01568ebe` | as `0x7f7c`/0xe with render type 1; no move case |

## Effects routed vs refused (natively)

| Request | Before | After |
|---|---|---|
| CreateJoint `0x7f7c`/0xe 20, `0x7fd3`/4 20 (wings `0x22ec`, `0x248f`) | routed, refused (0/40) | created and drawn (40/40; 360 quads per wing per frame on a 64-bone skeleton) |
| `0x0f20`'s particles behind `counter % 3`/`% 5` (world) | refused (no counter) | run on the client's frames; refused for their kinds (`0x855d`/1, `0x84d1`/1 not in the pool) |
| `0x2713`'s sprites in the world | refused (no pose) | routed (item pose) |
| #339's combined particle rule (owner key, argument 8) | — | applies to particles only; joints unaffected |

## Checks

Env: `. ~/Documents/MTM/mu-mac-tools/native/private-env.sh` (MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT, MU_EVIDENCE_DIR,
MU_SNAPSHOT_DIR, MU_LANG_DIR, MU_LANG3_SNAPSHOT, MU_VALIDATOR_CACHE, ...), `MU_SECTION3="$HOME/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin"`.
All heavy steps `nice -n 10`.

CHECKS_TABLE

## Release

RELEASE

## Byte identity and renders

RENDERS

## Limits

- 310 bodies remain; the six counter types not admitted (`0x0f24`, `0x0f28`, `0x0f29`, `0x0f2b`, `0x0f2c`, `0x1588`)
  fit no probe option yet.
- The native counter starts with the world runtime; the client's counts from process start (login and character
  select included), so only the periods are faithful. Inventory, the texture survey and `mu-render character` without
  `--frame-counter` keep 0.
- The streaks' +0x58: with the item's OBJECT the client ends the head at a former joint's +0x58 (record memory);
  natively it is the target argument. It only feeds the releasing MoveJoint (and, at width 50, its particles'
  positions), never a drawn quad.
- The counter scan covers the survey's unselected/no-buff domain, 16 states per type.
- Group 3 (draw fits of read programs) and group 4 (rank-5 strlen parts) not attempted.

## Next groups

1. The six counter types: read the maces' RenderObjDraw effect programs (`0x0f24`, `0x0f28`, `0x0f29`, `0x0f2b`,
   `0x0f2c`) and find `0x1588`'s probe option.
2. Draw fits for read programs: `0x23a8`/`0x23a9`, `0x0f1e`, `0x174a`, `0x2301`/`0x2302`, `0x23f0`/`0x23f2`,
   `0x0b51`/`0x0b52`, the bows `0x1313`/`0x1317`/`0x1319`, part 18's eleven.
3. The 31 rank-5 parts faulting in strlen `0x0195a4e0` and the 54 helper-group-count types.
4. Native particle kinds `0x855d`/1, `0x84d1`/1, `0x810a`/0x25 (RENDER-EFFECTS lanes).
