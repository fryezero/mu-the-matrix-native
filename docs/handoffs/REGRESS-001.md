# REGRESS-001: the quest-accept regression and the dark edge in README 26/27

Branch `claude/regress-001`, worktree `~/Documents/MTM/worktrees/regress-001`. It started from main `84a7f05d`
and merged `3ecc205c` (#320). No live game was used: the existing captures answered both questions.

## 1. Quest accept: bisected, fixed

**Symptom.** APP-POLISH-006 found that the scripted Lorencia dialogue in `test_native_quest.LorenciaDemo` reports
`"accepted":0` on unmodified main. `60:option:1` asks for the NPC's quest list (request 901), but `90:option:0`
reaches dialogue request 902.

**Bisect.** The first-parent bisect ran the test's own `mu-world` command with clean builds per commit:

| Commit | Result |
|---|---|
| `f7043cc5` (#178) | accepted 1, completed 1, progress 3 |
| `5ebc2b61` (#179) | accepted 0, 2 undecodable |

Inside #179, `707b82ca` (the branch base) is good and `2a916b52` is bad. `2a916b52` is SESSION-QUEST-001's "Move
quest state and window actions into the session". The private test was never green after that commit: its
expectations were rewritten there, but the test never passed at any commit.

**Cause.** The migration put the dialogue's quest traffic on the session's wire path. Offline, that path drops
two things:

1. **The NPC list never applied.** The session journals the NPC quest-list answer **F6 71** as `body_undecoded`,
   because the real client first XORs F6 70/71 with a key that includes three unknown bytes at `0x06fca280`.
   npcdialogue never entered list mode, so option 0 fell through to the dialogue state's own request 902.
2. **The accept request was never sent.** The accept **F6 72**, give-up **F6 73** and complete **F6 74** go
   through `Send(1, ..)`, the C3 wrap. Without NET-DECODE's wrap, `mu_net_send` refuses them
   (`MU_SEND_NEEDS_CRYPTO`), so they stay journaled as unsent. The fixture never sees them.

The test also exported `MU_QUEST_SCENARIO=quest-progress.scn`. That scenario accepts quest 7 itself at fixture
step 3. Even with 1 and 2 fixed, the scripted choice would then open quest 7's progress page, not its accept pages.

**Fix: the offline local quest lane.** The fix is in `session/domains/quest.{c,h}`, `quest_state.h`, the facade
`core/mu_quest.h` / `fixture/behaviors/quest.c`, and the world tools `world/world_gfx.c` and `world/parts/gfx.c`.

- The new call is `mu_session_quest_offline_local(s, on)`. It exists only in seed builds; the product library has
  no lane and no fixture symbol.
- The lane is active only while the session's transport is the in-process fixture on a loopback endpoint (the
  same gate as combat's plain offline lane).
- While it is active, wrapped quest requests go to the local fixture as plain frames, and the fixture's F6 70/71
  bodies apply as the plaintext the fixture wrote. The fixture never applies the `0x06fca280` XOR. Each use is
  journaled ("offline local: ...").
- The world tools (`world_gfx` and the headless quest part) turn the lane on through
  `mu_quest_session_offline_local`.
- Off is the default. `mu-session` scenarios, raw `send` frames and every other transport keep the wire rules, so
  `quest-routes.scn`'s opaque 70/71, `quest-progress.scn`'s unsent complete request and
  `test_opaque_npc_list_does_not_apply_decoded_state` are unchanged.

**The test.** `LorenciaDemo` no longer exports `MU_QUEST_SCENARIO`. Its script plays the whole quest with the
world's local fixture: list at step 60, accepted at 150, kills at 240/245/250, list at 330, completed at 390. That
is the pre-migration (#178) log line for line. The test expects `(accepted, completed, progress) = (1, 1, 3)`,
no active quest, 0 undecodable, request 901 at frame 60 and no request 902.

A new portable test, `Session.test_offline_local_lane_lists_accepts_and_completes`, plays the list, the accept,
three kills and the complete through the lane. It catches both halves: with either the request lane or the 70/71
lane disabled, the test fails (checked once, two planted mistakes).

The APP-POLISH-006 quest-capture command (`client-quests.md`) still works with the scenario and shows quest 7 at
3/3. Without the scenario it now plays the whole quest.

## 2. Dark edge in README 26/27: what the original draws, no renderer change

**Where it comes from.** The left of the Lorencia bridge and Tormenta's far-right corner show the world's clear
colour because the README framing uses `--perf-fov 65`. That is a native-only camera stress override
(`world_tool.c`, range 20..90). The client cannot reach it.

- The in-world zoom `0x0185a9bf` picks from {20, 30, world FOV}, so the world FOV is the largest.
- The live Lorencia globals of the October 22 capture read FOV 39.0 at `0x01cf1634` and far 3257.8 at
  `0x01cf1630`, the same as native.

**What the client does at that edge (verified by the instructions):**

- RenderMainScene `0x0185916b` calls GetScreenWidth `0x016bc355` (640 units with no NewUI side window).
- It then picks glClearColor in `0x01859419..0x0185967b` (import slot `0x01a7c6cc`) and calls BeginOpengl
  `0x0184adc7(0, 0, width, 480)` and CreateFrustrum `0x016cba24(width / 640.0f [0x01a7e684], ...)`.
- RenderTerrain `0x016cd468` draws only the tiles inside CreateFrustrum2D `0x016d20d9`'s polygon, tested by
  TestFrustrum2D `0x016ccce7`.
- That polygon comes from the camera record: 2400 × Distance × Z_Distance, widths 1190 / 540 × GetScreenWidth /
  640. **It does not depend on the FOV.**
- No fog is enabled (the scene clears FogEnable `0x0bdc597c`; only world 0x1e takes the fog path at `0x018596b4`).
  In native, which follows RenderMainScene's call order (verified by WORLD-ORDER-001), no other pass covers that
  area in worlds 0 and 141. There is no live frame at FOV 65 to confirm this for the client.
- So wherever a wider FOV sees past the polygon, the client shows its clear colour. That is (10, 20, 14)/256 in
  Lorencia and black in Tormenta (0x8d takes the final default branch).
- Native already does all of this: README 26's dark pixels are exactly (10, 20, 14).

**Measured.** All measurements are native renders at 1,600×1,000, the README tiles, frame 0, no players:

| FOV | Lorencia clear-colour pixels | Tormenta black pixels |
|---|---|---|
| 39 (world FOV) | 0 | 1,281 (models; the baseline) |
| 45 | 0 | 1,037 |
| 48 | 1,101 | 2,298 |
| 65 (README) | 225,308 (14.1%) | 146,776 (9.2%) |

Widening only CreateFrustrum2D's scale to 2.5 (the pre-#258 1600/640) brings back the water left of the bridge. The
dark area then shrinks to 8.0%, the band beyond the polygon's far edge. So the polygon is the cull that leaves the
edge. RENDER-TIME-003's 640-unit frustum stays: it was verified against live counts, and the original applies the
same routines.

**Against live.** At the 32 DATA-ACQ-002 live cameras (world FOV, 1,722×1,048), the top 8 rows outside the HUD masks
hold 890 native and 1,648 live pixels at the world's clear colour, out of 225,280. These are scattered dark texels;
no view shows an uncovered region on either side. No live capture of Lorencia or Tormenta at FOV 65 can exist.

**README 26/27.** The images should change if the README is meant to show only what the client can show. A later
README lane can re-shoot both at `--perf-fov 45` (both frames fill; the crowd framing needs a look) or at the world
FOV 39. This lane did not re-shoot them.

## Checks (wall times in the PR body)

- Quest: `test_native_quest` (incl. private LorenciaDemo) + `test_session_quest` 16 tests, 1 skip (the quest
  validator needs `MU_QUEST_SNAPSHOT`).
- Touched modules and 6b users: 13 modules, 115 tests, 3 private skips. `test_app_polish6` was run again with
  `MU_NATIVE_DATA_DIR`: 5/5.
- New `validate_scene_clear`: 4,000 cases, 0 mismatches, 8/8 call sites; the only third-section read is
  `0x01cf15fc`. Mutants: 6/6 detected (run once).
- The terrain cull routines: `validate_terrain`'s families frustum_2d 300, test_frustum_2d 15,000, frustum_3d 200,
  render_frustum 20 and render_terrain 2, all matching. `validate_wheel_route`: GetScreenWidth 61 and route 120
  cases, 0 mismatches.
- Fidelity: one byte-identity sweep, main `84a7f05d` vs branch, default draw. DATA-ACQ-002 64/64 PNGs and the
  October 22 tour 28/28 PNGs are identical.

## Limits

- The lane is offline-only: no wire, wrap or 0x70/0x71 XOR work. The three bytes at `0x06fca280` are still unknown.
  Real sessions keep F6 70/71 undecoded and wrapped quest requests unsent.
- The fixture's server rules (offers, rewards) are still the demo's choices.
- The Tormenta black-pixel counts at FOV ≤ 45 are model pixels, not cull. The FOV-45 suggestion is from these two
  tiles only.
- The optional live look at the bridge edge was not taken.

## Cleanup

Renders, scratch (`native/scratch/regress-001`, `native/renders/regress-001`), the bisect worktree and the build
directories were deleted after the ready line. No local input needs keeping. The worktree stays until the steward
merges.
