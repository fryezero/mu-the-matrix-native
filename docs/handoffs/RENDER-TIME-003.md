# RENDER-TIME-003, 2026-10-28

## Scope and result

RENDER-TIME-002 found two concrete behaviour differences between the live client and native. This milestone
closes both. The [finding section](../research/client-render-time.md#zoom-refusal-and-visible-objects-render-time-003-2026-10-28)
holds the addresses and every number.

1. **Zoom refusal.** WM_MOUSEWHEEL first goes to the UI layer `0x01d22c60` (handler `0x00aefb79`). That layer
   consumes it when the GFx dispatch handles it or when base.swf hit-tests at the cursor (client point, then
   the raw lParam). Only then does the window procedure's case `0x0121069d` run. That case adds its own guards:
   - the chat `InMouseViewBox`;
   - the GFx input object, which must exist and must not be type-6 flagged;
   - the handler `0x018588d9`: window 0x3e, world 0x8b, then the camera's existing rules.

   The live read showed every memory-held guard clear at the refused wheels. By elimination, base.swf's hit
   test in the UI layer took the wheel. This is an inference: the Scaleform hit result cannot be read.
2. **Visible-object gap.** Both counters sum object byte `+0x0b`, so they measure the same thing. The world
   render sizes CreateFrustrum and CreateFrustrum2D with GetScreenWidth `0x016bc355`, which works in 640x480
   units (640 with no side window). Native used the window width, so at 960x600 its frustum was 1.5× wider.
   After the fix, the run 3 twin's visible count equals live at every standing sample (198 / 177 / 182).
3. **Comparison.** `compare --mode live` still fails, but component failures drop from 477 to 400 (run 3) and
   433 to 390 (run 4):
   - camera eye z / FOV / pitch: 24 → 0 per run;
   - visible objects: 21 → 0 / 1.

   Phase alignment, other players, the pools and the WorldTime policy remain known limits. One new failure is
   a plan consequence: the plan needs ≥1° of native zoom, and the faithful twin no longer zooms.

## Changes

- `reconstructed/camera/client_wheel.{c,h}`: GetScreenWidth and the complete WM_MOUSEWHEEL route (UI layer,
  case, handler, common exit). Scaleform calls are callbacks.
- `scripts/validate_wheel_route.py` (+ `validators.toml` row, `test_client_wheel.py`): the Unicorn comparison.
- Native:
  - `native/core/mu_frame.c` routes the wheel through `mu_client_mouse_wheel`. It adds the world 0x8b refusal
    and logs refused wheels. With no UI layer attached, the layer declines, as in the client without its base
    movie.
  - `native/world/parts/terrain.c` uses `mu_client_screen_width` for the frustums.
  - `mu-world --wheel-ui-hit` declares that the reproduced client's base.swf is under the cursor.
- `scripts/render_time.py` and `scripts/render_time_live.py`: live twin plans carry `"wheel_ui_hit": true`;
  capture passes the flag, and the plan loader requires a boolean.
- `live-readers/rtguard.c`: a read-only poller of the guard states, numbers only.
- Docs: client-render-time.md (finding), client-camera-input.md and client-input.md (pointers).

Intended render change: native frames at window widths other than 640 cull with the client's 640-unit frustum.
640x480 output is unchanged. Wide native renders (for example 960x600 or 1722x1048 fidelity tours) change at
object/terrain culling edges. The 960x600 twin frame still shows terrain to every edge. Lanes that keep native
"before" renders at those sizes should expect this. The synthetic env clear-colour test moved to the map edge,
because at 320x200 the terrain now fills the frame.

## Live session (shared game lock)

- **Preflight.** `pgrep` was empty and both lock paths absent. About 96 GB free.
- **Timing.** Lock taken 20:08:21, released 20:16:01. Each probe run lasted under 15 s.
- **Route.** RENDER-TIME-002's route: `login.sh` with the free-runtime prefix, plain Rosetta, `mugl-hotpatch.txt`
  set to `0` and 960x600. The password stayed in the Keychain and was used by the helper only.
- **Probes.** The Events window was closed with its Close button. Wheel probes ran at four spots by
  `SetCursorPos`/`SendInput` (`rtinput`), with `rtguard` reading.
- **Second probe.** A second probe added window 0x3e's byte. A third added the dispatcher path flag. After
  that, rtinput stopped starting (a Wine helper stall), so the session ended.
- **End state.** The hero stayed in Lorencia 139,130, with no walking, fight, NPC, item or trade action.
- **Cleanup.** The client, launcher and the session's wineserver were stopped. `mugl-hotpatch.txt`,
  `mu-modes.txt` and `LauncherOption.if` were restored byte for byte (`cmp` same).
- Reads only. No packet or traffic capture.

## Verification

- Wheel route / GetScreenWidth: 1,801 comparisons, 0 mismatches.
  - 600 + 1 GetScreenWidth cases.
  - 1,200 route cases: stages 355 / 352 / 239 / 254.
  - 10/10 compiled mutants caught.
  - The registered `--cases 60` run gives 181 comparisons and 10 mutants.
- Portable: `test_client_wheel.py` 5 checks; `test_render_time_live.py` 16 (2 new assertions/tests).
- Private: `test_render_time_003.py` 2/2 (wheel refused/zooms, visible count independent of the window size, 198 at
  run 3's camera); `test_client_wheel` private comparison.
- Gate: `nice -n 10 bash scripts/local-macos-ci.sh` on main `eb4b53a` merged in. **1,707 tests across 38 suites,
  221 explicit skips, 0 failures**; 11/11 fixture scenarios; repository audit 1,680 files, 0 rejected.
- Private: `run_validators.py --private --only validate_wheel_route,validate_camera` passes 2/2.
  `test_render_time*.py` with installed data passes 34/34, including RENDER-TIME-001's fourteen-view repeat with
  `MU_RENDER_TIME_OBJECTS` set to the fidelity2 placements.
- Merge process: by the MERGE-STEWARD (brief, 20:50 update). This lane left the queue and did not merge.

## Next steps

1. Phase alignment (RENDER-TIME-001 procedure step 6) and owner-split pools remain the blockers for a passing
   live comparison.
2. Revise the live plan's coverage rule: the client refuses the wheel wherever base.swf is under the cursor, so
   the zoom part of the path needs another input route or a spot where base.swf does not hit.
3. Confirm the base.swf hit directly: build libmugfx and test native base.swf hit-testing at the recorded spots.
   Alternatively, read Scaleform's hit result in a live session.
4. Port the NewUI window-open states into GetScreenWidth when native gains legacy NewUI side windows.

## Inputs kept for a later lane

Kept and untouched: `~/Documents/MTM/mu-mac-tools/native/scratch/render-time-002/`. Kept from this lane:
`~/Documents/MTM/mu-mac-tools/native/scratch/render-time-003/reexport/` holds the regenerated run 3/4 exports and
plans with `wheel_ui_hit`, about 0.2 MB. Everything else from this lane was deleted.
