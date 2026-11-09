# RENDER-ITEMS-002V

Branch `codex/render-items-002v`, worktree `~/Documents/MTM/worktrees/render-items-002v`, from main `a55200e2`
(PR #350). Implementation by Codex, GPT-6.1 Sol. No subagents, live client, launcher, protected-component work or
hosted workflow. No full gate in the lane, per the test budget. The installed Native Preview and both Wine apps
are untouched.

Scope: 002U's six remaining counter bodies. The next 24 read-program candidates were screened, with none admitted.
The rank-5 strlen group was not attempted. [Finding, part 30](../research/client-render-items.md#part-30-the-six-remaining-counter-bodies-and-quantised-random-colours-render-items-002v).

Research numbering: both parallel branches had used part 28 at the checkpoint. This lane uses part 30, leaving
room for the steward to preserve both parallel findings without sharing this section number. Main is rechecked
before the final push.

## Result

- Bodies **1,364 -> 1,370 of 1,674**, adding `0x0f24`, `0x0f28`, `0x0f29`, `0x0f2b`, `0x0f2c` and `0x1588`.
  **304 remain**; skins 17/17 and links eighteen targets/twenty-four types are unchanged.
- The five maces gain their pre-draw effect programs. The reader distinguishes body range calculations from effect
  requests, unrolls a constant loop inside an open counter gate and reduces an exactly bounded unsigned conversion
  to the existing integer-to-float op. The full conversion sequence and its zero correction are checked.
- Body recipes retain the inclusive quantised range `0x011ff622`, its `0x0185caa4` wrapper and the intermediate
  binary32 products of colour, clock and random inputs. The staff uses exit-field probes for its ancient pass.
- The staff needs 22 scalar slots, so the internal cap is 24. Clock chains remain at 12 ops. The generator still
  writes only used op/k slots. No exported ABI or ctypes structure changes.
- No new particle kind or installed app is part of this change. RENDER-EFFECTS-022 owns its parallel mace-particle work.

## Causes and addresses

The full address table and arithmetic are in research part 30. Mace pre-program bounds:
`0x017d5675..0x017d62b7`, `0x017d8bfc..0x017d94dc`, `0x017d94f1..0x017d9dcb`,
`0x017dab03..0x017db6cf`, `0x017db6e4..0x017dc347`.
The staff's colour setter is `0x01736abc`, its random-wrapper returns `0x01736b46` and `0x01736c5f`, and its
counter scroll begins at `0x0173691a`. The owner/clock domain and pinned text/data are unchanged from 002U.

## Effects routed vs refused (natively)

| Request | Native route | Limit |
|---|---|---|
| Five maces' bone sprites and transformed-position sprites | Existing sprite pool through the item host | Missing named bones, short skeletons and unavailable textures remain refusals. |
| Five maces' particles, including counter-gated requests | Existing particle pool through the same host and rand stream | A routed request can still be refused for its kind, owner or argument. No new particle kind is reconstructed here. |
| `0x1588` | Body mesh passes only | Its two random colour scales consume the body's rand context; it adds no effect program. |
| 002U wing joints and 002T post programs | Unchanged | No joint-pool or world-caller code changes. |

The isolated owned comparison checks all requests and exact rand consumption. It recorded 1,355 sprites, 283
particle requests and 1,582 refusals in 320 states; those are harness counts, not native-pool creation counts.

## Checks

Env, from the repository root:
`. ~/Documents/MTM/mu-mac-tools/native/private-env.sh` and, for rows that require it,
`MU_SECTION3="$HOME/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin"`.
Heavy commands use `nice -n 10`, make at most `-j4`, validator runners `--jobs 2`. Steps wait at load >14 or free
memory <25%. The original-side cache stays in the shared tools directory.

Validation is in progress. Final counts, wall times, tested commit and the exact steward selection will replace
this paragraph before the ready-prs entry.

6b: `MU_RC_BODY_SCALARS` is used only by `reconstructed/renderchar/renderchar.c`'s input storage. The new scalar
kind and body tables reach the renderchar validators, the native item renderer and its hosts through the normal
compiled dependencies. The affected selectors run after the build; kept fallback rows remain in the selection.
The native renderer test adds all six admissions with a high-bit counter and checks deterministic repeat renders.

## Release

Steward validators: pending final post-build selection. No ready-prs line has been written.

## Byte identity and renders

The baseline uses main `a55200e2`'s tables and sources, with the new scalar branches still unused. Its default world
renders were taken once before table admission. A separately compiled main renderchar library is the C-to-C base.
The final default-draw sweep and inventory comparison are pending table generation and the build. These are offline
native renders, not original-client pixels.

## Limits

- 304 bodies remain. The 24 read-program candidates are not admitted. Twenty-two read; `0x2301`/`0x2302` refuse
  in the wave reader. `0x23a8`/`0x23a9` and bows `0x1313`/`0x1317`/`0x1319` fit initial probes but fail independent
  states under all three carry options. The remaining nineteen candidates do not fit those initial probes or
  do not read. Rejection is not passing coverage.
- The five maces' host-free body checks use zero rand results, since their native pre-program is absent without an
  item host. Owned comparisons use the same nonzero sequence for the entire original and C program. The staff
  compares nonzero body sequences and consumption directly.
- The counter's absolute process phase and process rand phase remain different from the client. Selected items,
  buffs and unavailable bones retain the earlier bounds/refusals. New native particle kinds remain separate work.
- The 31 rank-5 strlen parts and 54 helper-group-count types remain. No new private capture is needed or retained.

## Next groups

1. Draw fits for the 24 read-program candidates, including the wave-reader operand case for `0x2301`/`0x2302`.
2. The 31 rank-5 strlen parts, then the 54 helper-group-count types.
3. Native consumers for the newly routed mace particle kinds, separate from RENDER-EFFECTS-022's owned subset.
