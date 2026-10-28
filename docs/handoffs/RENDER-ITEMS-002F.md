# RENDER-ITEMS-002 part 6

Part 6 adds 58 bounded item bodies, 27 armour and 31 other item-group models. Coverage is
**559/1,674 item bodies and 17/17 class skins**. Rank 9 is complete at twelve types; nine more
ranked shapes are complete overall. Two generated sprite-chain link targets, `0x012cb556` for
`0x0af9` and `0x012cb7ab` for `0x12f9`, bring complete native caller consumers to nine targets
covering fourteen types in the existing no-owner domain. Rank 5 remains refused.

The shared C recipe executor preserves omitted ancient phases, including when an item record is present.
The sprite-chain executor uses generated, instruction-checked parameters and preserves bone, offset,
colour, scale, conditional rotation and random-call order. The complete evidence and addresses are in
[the finding](../research/client-render-items.md#part-6-rank-9-armour-further-body-clusters-and-sprite-chains-render-items-002f).
The existing selection/shadow/buff/record-kind and mesh-override limits are unchanged.

Ground, software inventory and actual GFx item/FBO draws consume the two existing skin sprites through
a skin-only adapter. Character body and attachment hooks retain their saved-pose rules. The resumed review
fixed the GL ground callback's runtime pointer qualifier so it can allocate sprites and compile under
`-Werror`. The inherited JPEG-capability guard was reviewed, tested and committed.

## Checks

Fresh runs after the disk recovery use the pinned original text/data and compiled production C:

| Instruction family | Cases | Mismatches | Compiled mutants caught |
|---|---:|---:|---:|
| Part 6 bodies and new link chains | 17,736 | 0 | 6/6 |
| Part 5 bodies, skins and links | 25,772 | 0 | 9/9 |
| Part 4 bodies, skins and links | 52,172 | 0 | 7/7 |
| Part 3 bodies, links and offset transforms | 74,292 | 0 | 8/8 |

Part 6 consists of 16,936 full body streams across 58 types and 800 link caller streams. Mutant detection
counts are ancient phase 1,233; object alpha 11,680; chain bone 800; chain scale 400; random choice 360;
final white flare 400. Both generated tables reproduce. All 1,691 survey entries, including 17 skins,
agree with the compiled refusal function; size ranks and original survey identities are preserved.
The part-5 run interrupted by ENOSPC now completes with all nine mutants detected. The inherited part-3
`staff-choice` mutant anchor now selects only its original staff branch after the new chain introduced
a second matching expression; all eight original mutants are caught. Across these four validators,
169,972 instruction cases have zero mismatches and all 30 mutants are detected. The two errors in
an earlier body-test log do not reproduce on the recovered checkpoint.

Portable renderchar suite: 39 tests, nine expected private-input skips. Native character-render suite:
eight tests, one installed-client skip. Four additional native tests pass: both ground backends, software
inventory and the actual GFx item/FBO consumer. Each ground backend tests both quest-item codes at
level 1, three sprites for three draws, without additional random calls. Authored textured pixels verify
the sprite clock and repeated icon frames. Missing bones, bounded pools and random order remain covered.

The full preflight `bash scripts/local-macos-ci.sh` passes on the part-5 base plus this lane:
1,485 tests across 38 discovery runs, 182 explicit private/unavailable-input skips, seven fixture scenarios
passed, native viewer/readers built, and 1,379 publication-audit files with zero rejected. The fixture
journal records 53 inbound frames with zero unbound/undecodable; the existing two unrecovered intents and
five unsent frames remain explicit. The final latest-main integration and locked release gate remain
pending the merge lock. No hosted workflow is used.

Self-review of the recovered checkpoint and resumed changes against the brief and repository standards
found the GL qualifier build failure, the weak ancient-record test input and the ambiguous staff mutant
anchor, all corrected above. No further blocking issue was found within the implemented subset. Rank 5
and the owner/shared-state link branches remain partial as recorded below.

## Offline renders and cleanup

Representative native before/after renders were inspected and rerun after recovery. Rank-9 scenes replace
three refusals with implemented bodies, from 5 to 11 total passes; further ranked bodies go from 5 to 28.
Each changes 7,160/120,000 pixels on the authored fixture. Untextured geometry saturates white, so those
pixels do not establish material fidelity. The textured chain scene changes 58,547/120,000 pixels and
allocates 18 sprites at its fixed seed. The software inventory changes 7,744/786,432 pixels. The ordinary
character control remains byte-identical. These are native synthetic renders, not original-client pixels.

Animated synthetic models show an existing first-versus-cached pose difference; the static inventory fixture
isolates the sprite clock and does not claim that broader pose lifecycle is verified.

Reports and renders were scoped to `mu-mac-tools/native/{scratch,renders}/render-items-002f/`. They and the
lane's build outputs will be deleted after merge, followed by its worktree and local branch, per the owner
rule. No new input needs to be retained. The original shared input symlinks are never staged or deleted
recursively. Only the assigned existing worktree is edited/built; the main checkout and other worktrees
are untouched. No live game or launcher is started, stopped, driven or read.

## Remaining work

**1,115 bodies remain.** Rank 5's `0x017479b1..0x01747a0a` calls the real pose builder `0x012b5064`
with OBJECT action/frame/angles and writes shared bones `0x06fce398`. The current synthetic body oracle
lacks `model+0x30` action data and `model+0x2c` bone tracks. Populate those from authored synthetic models,
compare full pose/geometry, then add the native pose adapter before enabling its recipes. A pose recorder
alone would not verify geometry. Its nineteen types remain explicitly refused and tested.

The shared link target `0x012c8571` for `0x132f/0x14f2` also requests Laser `0x7fd6` subtype 17 with an
item owner, which the joint consumer refuses. Sword target `0x012c91fe` mutates shared clock/bone state
at `0x0a3a0e1c/20`; it is not a stateless sprite recipe. Further links, earlier mesh-override,
selection/shadow/buff/record-kind, hero-instance, owner/random, model-mapping, NewUI and Box of Luck limits
remain. Muun and nested map-object tables stay deferred.
