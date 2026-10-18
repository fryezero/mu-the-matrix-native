# Scene manager (NATIVE-SHELL-001)

Authored C for the client routines that own the scene-state global SceneFlag `[0x01d1df70]` and move the
client between its scenes. See [the finding](../../docs/research/client-scene-manager.md).

| Routine | Address | Reconstruction | Evidence |
|---|---|---|---|
| Scene dispatcher (WinMain idle loop) | `0x01859d8a` | `mu_scenemgr_dispatch`, `mu_scenemgr_dispatch_target` | verified |
| Intro/title scene (startup loading, then scene 3) | `0x0185ad63` | `mu_scenemgr_intro` | verified |
| Login-scene creation (world 0x5e, login music) | `0x01851804` | `mu_scenemgr_login_create` | verified |
| Scene-3 tick tail (protocol 0x14 → scene 5) | `0x01857621..0x018576a7` | `mu_scenemgr_login_tick_tail` | verified |
| Frame-driver music block (login theme in scenes 3/5) | `0x0185276c..0x0185280c` | `mu_scenemgr_frame_music` | verified |
| Start loading (join request / hero copy, scene 4) | `0x0185a75a` | `mu_scenemgr_start_loading` | verified |
| Loading scene (one frame, then scene 6) | `0x01851adc` | `mu_scenemgr_loading` | verified |
| Return to character select (handler subcode 1) | `0x0125294e` | `mu_scenemgr_return_to_character` | static |

The loading screen object itself (CLoadingScene `0x00cdb6ca`/`0x00cdb74c`/`0x00cdb94f`) is in
`reconstructed/ui/ui_loading.c` (it is four CSprites).

Every call into another subsystem goes through `mu_scenemgr_host.call` as a `mu_scenemgr_call` named by the callee's
client address; reads and writes of objects the routines do not own go through `peek`/`poke`. The native client
(`native/client`) implements the calls it needs; `scripts/validate_scene.py` runs the client's instructions in
Unicorn and compares the call/write stream and the globals. Network sends (the protocol is out of scope) are one
`MU_SCENE_NET_SEND` record.

`make` builds `libscene`; `test_scene.py` holds the portable checks and the opt-in private comparison.

NATIVE-LOGIN-001 adds the login scene's 3D part: `mu_scenemgr_login_render_3d` (the render `0x01857ed9` up to
BeginBitmap, with the camera far plane `0x0098ac45` inlined) and `mu_scenemgr_login_tick_head` (the tick `0x01857236`
up to MoveCharacterCamera); see `docs/research/client-login-scene.md`.
