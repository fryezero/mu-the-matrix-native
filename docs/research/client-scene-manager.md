# The client's scene manager and the native scene flow (NATIVE-SHELL-001)

This milestone recovers how the client moves between its scenes (title, login and server select, character
select, loading, main game) and builds `mu-client`, a native macOS app that runs that flow end to end offline
over the existing native modules.

Labels used below:

* **verified**: the reconstruction in `reconstructed/scene` (or `reconstructed/ui`) was compared with the client's
  own instructions run in Unicorn (`scripts/validate_scene.py`) and matched on every case;
* **static**: read from decoded instructions, not executed;
* **native**: behaviour of the native client that is not a client fact (labelled where used).

## Identity

| Input | SHA-256 |
|---|---|
| `main.exe` (target) | `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a` |
| Restored text at `0x00401000` (capture09), 23,572,480 bytes | `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724` |
| Second section at `0x01a7c000` (run10), 2,557,764 bytes | `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f` |

Every executed routine body is pinned by SHA-256 in `scripts/validate_scene.py` (`PINNED_JSON`).

## 1. The scene state and its values

SceneFlag is the dword `[0x01d1df70]`. The WinMain idle loop calls the dispatcher `0x01859d8a` whenever the message
queue is empty ([frame loop](client-frame-loop.md)).

| Value | Scene | Routine run by the dispatcher | Per-scene routines |
|---:|---|---|---|
| 2 | title / startup loading | `0x0185ad63` (blocks until the startup data is loaded) | CreateTitleSceneUI `0x011e230d`, RenderTitleSceneUI `0x011e2c8c` |
| 3 | login and server select | frame driver `0x01851d39` | tick `0x01857236` (first step: creation `0x01851804`), render `0x01857ed9` |
| 4 | loading | `0x01851adc` (one frame, then 6) | CLoadingScene `0x00cdb6ca` / `0x00cdb74c` / `0x00cdb94f` |
| 5 | character select | frame driver `0x01851d39` | tick `0x01856e6c` (first step: CreateCharacterScene `0x01851540`), render `0x018576b3` |
| 6 | main game | frame driver `0x01851d39` | tick `0x0185613e` (first step: main-scene init), render `0x0185916b` |

Any other value runs nothing (**verified**: values −5..20 and 100). After the scene routine the dispatcher calls an
observer `0x00ac3bf7()->0x00ac9be9(SceneFlag)` (**verified**, opaque). Before it, it runs two per-loop service calls
(`0x00c74245`→`0x01185472`, `0x00aef92d`) and clears `[0x01d22d1e]`; in scene 6 it makes a three-character string
compare whose result is unused (both branches join). When `[0x06fc9e4c]` exceeds 31 its tail builds and sends a C1
packet; that send is network code (out of scope) and is collapsed into one record in the comparison.

Every writer of SceneFlag uses the same inlined setter: `if (SceneFlag != v) { SceneFlag = v; 0x00a05a22(&SceneFlag); }`.

**A second, separate scene variable.** `CUIMng::CreateLoginScene` `0x011e2dc0` sets the UI manager's own scene to 2 and
`CUIMng::CreateCharacterScene` `0x011e2f2a` to 4 ([widget finding](client-ui-widgets.md)); those values belong to
the legacy window manager, not to SceneFlag.

## 2. Transitions

| From → to | Where | Condition | Status |
|---|---|---|---|
| 2 → 3 | end of `0x0185ad63` | startup data loaded | verified |
| 3 → 5 | scene-3 tick tail `0x01857621..0x018576a7` | protocol state `[0x06fca2c4] == 0x14` (set by the network layer's login answer): logs "> Request Character list", sends the list request (`0x00988c5c`→`0x00988d22`), SceneFlag 5, then `0x01287a66`, `0x00aab55d(0x008e7f90(0x01d1df24))`, `0x0182a4f1`, `0x0137c276(-1)` | verified |
| 5 → 4 | `0x0185a75a(1)` | the join answer: start loading (below) | verified |
| 4 → 6 | `0x01851adc` | after its one frame | verified |
| 6 → 5 | handler `0x0125294e` subcode 1 | the server's answer to "select character" (GFx game menu); SceneFlag 5, InitCharacterScene `0x0bdc5ca2` = InitMainScene `0x0bdc5ca3` = `[0x0bdc5eb8]` = 0, protocol 0 | static |

The character-select tick and render call `0x0185a75a(0)` on Enter or a double click (verified in
[NATIVE-CHARSEL-001](client-character-select.md)). **`0x0185a75a(0)` does not change the scene** (verified): it looks up
SelectedHero `[0x01cf1864]` through `0x0095f6db`/`0x009a13f4`, sends the join request with the character's name (network)
and stores SelectedHero in the GFx state (`[0x00ac3bf7()+0x22c]+0x98`). The packet handlers `0x01285814`/`0x0128590d`
(static) call `0x0185a75a(1)` with the answer. With argument 1 the routine (verified):

1. looks the character up again; a character whose flag byte `+0x14` has bit 0 set opens message box `0x84` instead;
2. copies it into the Hero `[0x01d1df1c]`: level `+0x144` through `0x00a00031`, class byte `+0x12` → Hero `+0x187`,
   skin `+0x13` → `+0x188`, the name through `0x0129deaa`/`0x00a0033e` and `strcpy(Hero+0x88, c+0x44)`;
3. calls `0x0182a85e`, clears InitLoading `[0x0bdc5b87]`, sets SceneFlag 4 and resets the GFx state (`0x00b4c117`,
   `+0x49` = 0, `0x00b49bf4(0)`, virtual call `+0x44`, `0x009a595b()->+0xc` = 0).

The protocol-state values are what the scenes test: the scene-3 tail needs `0x14`, the scene-5 tick and render need
`0x33` or more (static, [character select](client-character-select.md)). Their names are readings of these tests.

## 3. The title scene and the startup progress (scene 2)

`0x0185ad63` (verified) runs a ResourceGuard check on `data\local\Gameguard.csr` (opaque; its failure branch is
unreachable because an unconditional jump skips it), loads the 14 title textures `0x7b81..0x7b8e` (the
`MuBattle_loading01..06` pictures instead of `lo_back_s5_im01..06` when `0x0095f75d()->+4 == 1`) and
`newui_black_letter_box.jpg` (`0x7c80`), creates the title UI, then calls the startup data loader `0x0182049e(hdc)`.
That loader renders the title screen with progress **0, 1, …, 8 of 9** at fixed points between its loading blocks
(static: step 0 at its start `0x018204ce`, step 1 at `0x01823397` after the interface and effect textures, steps 2..7
at `0x018282a9`..`0x01828319` between further loaders, step 8 at `0x01828720`; the later sites are in its callees). After the
loader, CreateFonts `0x0182a0da` and an options call, the routine renders the final frame **9 of 9**, releases the title
UI, deletes `0x7b81..0x7b8e` (`0x7c80` stays), sets SceneFlag 3 and stores GetTickCount in the frame tick `[0x0bdc5e64]`.
The title screen's layout is [NATIVE-UI-001](client-ui-2d.md)'s verified CreateTitleSceneUI/RenderTitleSceneUI.

## 4. The login scene (scene 3)

The tick's first step (`[0x0bdc5b86]` clear) calls `0x01851804` (verified):

* world `0x5e` (folder **World95**, the 3D login world) in `[0x01cf15fc]` and `[0x01cf1600]`, OpenWorld `0x0182876e`;
* the login data `0x0182a34c` (logo, font and server-window textures) and `CUIMng::CreateLoginScene`;
* protocol state 0, then the server connection `0x0121c055(address, port)` (network);
* when the remember-ID option `[0x01cf0fac]` is 0, the saved account name from the options object is copied into the
  account buffer `0x0b436580` with its length in `[0x0b4371b0]`;
* MoveMainCamera, the overlay fade `[0x0bdc5b80]` = 0, **PlayMp3(`data\music\login_theme.mp3`)** (music table entry 32),
  and GFx calls.

The server list arrives through the network; its handler `0x0127ec2f` shows the server-select window
([NATIVE-UI-002](client-ui-widgets.md)). Choosing a server emits the connect event; the account dialog is a GFx movie
(`onLoginOkClick`/`onLoginCloseClick`, `SetLoginInputVisible`; the legacy `CLoginWin::Create` has no callers), so the
account entry follows the server choice (inference from the handler names and the window flow). **Esc** in the tick
(`0x00ec53a7(0x1b)`, sound 0x19) closes the credits window or opens the GFx menu (static).

## 5. The loading scene (scene 4)

`0x01851adc` (verified):

1. first call (InitLoading clear): LoadingWorld `[0x0b437c14]` = 9999999, InitLoading = 1, the picture variant
   `rand() % 1 + 1` (always 1), `sprintf("Interface\LSBg0%d_%d.JPG")` → `Interface\LSBg01_1..4.JPG` as `0x7b81..0x7b84`,
   **StopMp3(login theme)**, `new` 0x2a8 bytes → CLoadingScene at `CUIMng+0x6598` and its Create;
2. every call: BeginOpengl(0, 0, 640, 480), clear to black, BeginBitmap, CLoadingScene::Render, EndBitmap,
   `0x0184b6dd`, SwapBuffers;
3. destroys the object (scalar deleting destructor), sets SceneFlag 6, deletes the four textures, `0x016a5524(1)`.

So the loading scene draws **exactly one frame and has no progress bar**. The world itself is loaded by the
join-map handlers that call OpenWorld (`0x0124d493`, `0x0127c260`, `0x012818a6`, static) and by the main scene's
first tick, whose initialisation ends with the log line "> Main Scene init success." (static); the loading picture
stays on screen during those blocking loads because nothing else is swapped.

**CLoadingScene** (verified, `reconstructed/ui/ui_loading.c`): four CSprites (vector at `+8`) on `0x7b81..0x7b84`,
400×512, 400×512, 400×88, 400×88 virtual pixels, scale = screen height / 600, positioned at
`x = ((W − 800·scale) / 2) / scale` and `x + 400`, rows 0 and 512 (datum 3): the 800×600 picture scaled to the screen
height and centred horizontally.

## 6. Music per scene

| Scene | Music | Where | Status |
|---|---|---|---|
| 3 | PlayMp3(login theme) at creation | `0x01851804` | verified |
| 3, 5 | PlayMp3(login theme) every rendered frame (no-op when already playing) | frame driver `0x0185276c..0x0185280c` | verified |
| 2, 4, 6 and others | StopMp3(login theme) every frame | same block | verified |
| 4 | StopMp3(login theme) on its first call | `0x01851adc` | verified |
| 6 | field music per world and tile | `0x0185280c..` ([audio](client-audio.md)) | verified earlier |

## 7. Verification

`scripts/validate_scene.py --cases 1000 --loading-ui-cases 120 --mutations` (private captures, report
`evidence/scene/validate-scene-01.json`, ignored):

| Routine | Cases | Calls compared | Object writes | Notes |
|---|---:|---:|---:|---|
| dispatcher `0x01859d8a` | 1,000 | 5,949 | 0 | SceneFlag −5..20 and 100; 150 network-send tails |
| intro/title `0x0185ad63` | 1,000 | 50,802 | 0 | both picture variants, every start scene |
| login creation `0x01851804` | 1,000 | 17,388 | 0 | remember-ID on and off |
| scene-3 tick tail | 1,000 | 2,185 | 0 | 209 transitions to 5 |
| frame music block | 1,000 | 1,000 | 0 | scenes 0..7 |
| start loading `0x0185a75a` | 1,000 | 5,893 | 1,099 | both arguments, blocked characters, missing characters; 239 join requests |
| loading `0x01851adc` | 1,000 | 22,316 | 1,093 | first/later calls, failed `new` |
| CLoadingScene Create/Render | 120 | 5,880 GL calls | | 13 window sizes; GL streams word for word |

Zero mismatches; 7 of 7 planted mistakes in the C inputs (one per routine) and a planted height error in the loading
screen were detected. Undefined reads of uncaptured globals stop a case, so the globals list in `mu_scenemgr_globals`
is complete for these routines. Portable checks: `reconstructed/scene/test_scene.py` (behaviour through a recording
host) and `native/tests/test_native_shell.py`.

## 8. The native client: `mu-client`

`native/client/shell.c` runs `mu_scenemgr_dispatch` as the WinMain loop does, with itself as the host: the host calls
of the reconstructed routines drive the native modules.

| Scene | Native module | Host calls implemented |
|---|---|---|
| 2 | 2D layer (`reconstructed/ui`) | LoadBitmap, Create/RenderTitleSceneUI; the startup loader's nine progress frames (the native client has no startup data to load: **native**) |
| 3 | 2D layer: login overlay, CServerSelWin | OpenWorld's music volume, login data, CreateLoginScene, connect (the session's list arrives), PlayMp3 |
| 5 | `charsel/charsel_embed.c` (mu-charsel's session) + CCharSelMainWin | the scene tick's Enter → start loading (0) → the session's join answer → (1) |
| 4 | 2D layer: CLoadingScene | LSBg textures, StopMp3, CLoadingScene, swap |
| 6 | `world/world_embed.c` (mu-world's session) | the Hero's class from start loading's copy, the session's join position and the character's equipment |

`world_embed.c` and `charsel_embed.c` compile mu-world's and mu-charsel's `main.c` unchanged into their own
translation units and wrap their static load/frame/draw routines, so mu-client shows exactly what mu-world and
mu-charsel show and follows their changes without copies (mu-world itself is not edited).

**Offline session** (`native/client/offline-session.*`). The client waits for the network at four points: the server
list, the login answer (protocol 0x14), the character list (0x33) and the join answer (`0x0185a75a(1)`, world and
position). The real answers come from the server through the network protocol, which is out of scope; the offline
session answers them locally from `native/client/demo-session.txt` (servers in `mu-render ui servers --list` format,
characters in `mu-charsel --list` format, `join SLOT WORLD X,Y [ANGLE]`). The login is an **OFFLINE DEMO panel**
(placeholder for the GFx account dialog): any input is accepted, typed characters are only counted for the masked
display and never stored or sent.

**Native shortcuts** (labelled in the code): Enter on the server list picks the first open server; Esc in character
select returns to the server list (the client's GFx menu asks the server); Esc in the world returns to character
select at once (the client waits for handler `0x0125294e`'s answer); Esc twice on the server list quits.

**Front ends.** `build/mu-client` opens an SDL2 + OpenGL 2.1 window: the 3D view (character select or world) is drawn
with the embed's GL renderer, read back, and the 2D layer (the deterministic software GL subset, as in the headless
tools) is composited over it; the title and loading frames are presented from inside the dispatcher like the client's
swaps. `--headless --backend gl|soft` renders the same frames offscreen with scripted input (`--auto` plays the whole
flow, `--script "F:ACTION ..."`), captures PNGs and can write the music to a WAV file. `build/mu-shell` is the
software-only headless build used by the portable tests. Local captures: `~/Documents/mu-mac-tools/native/renders/shell/`.

## 9. Limits and next steps

* **3D login world.** World95 (`0x5e`) behind the login and server-select screens is not drawn (black); its camera uses
  the record path of MoveMainCamera like character select, so the charsel session could host it.
* **The startup loader** `0x0182049e` itself (what each progress step loads) is a static reading of its call sites only.
* **Main-scene init** (`0x0185613e` first step) and the handler `0x0125294e` are static readings; the GFx menus and the
  GFx account dialog are not reconstructed.
* **Network.** Every server answer is simulated by the offline session; a real session would come from the network
  layer (protocol encryption and login packets are out of scope).
* GlobalText strings are the ones observed on the live screen (`Data\Lang.mpr` is not decoded).
