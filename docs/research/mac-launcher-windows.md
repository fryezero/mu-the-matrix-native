# Launcher windows under Wine's macOS driver (MAC-APP-004)

Owner report: the launcher (`MuTheMatrix.exe`, IGCN 1.12.1.3, SHA-256
`c32e99ee98fc0773f850f9e76b160a9a00c867f4d745bf9e66c4b15d7f74bc3e`) "sometimes stays on top of the game
windows even when a game window has focus", and "after minimize, clicking it in the Dock does not bring it back".
Both runtimes were affected: the free runtime (Wine CX 26.3 build `archive-c50cb6145767`) and the CrossOver 26.3
bottle MuMatrix32. Fixed in the mscoree proxy v2 (`mac-play/mumodes/winfix.c`).

## Method

The launcher was treated as a black box: no decompilation and nothing about its protection. The tools were:
- an `EnumWindows` dump (style, ex-style, owner, class, visibility, iconic) run inside the prefix;
- `CGWindowListCopyWindowInfo` for the macOS side (layer, alpha, on-screen);
- System Events for the Dock list (`AXMinimizedWindowDockItem`) and for Dock clicks;
- `WINEDEBUG=+win` and `+systray` traces of one minimize;
- the upstream winemac/win32u sources (`gitlab.winehq.org/wine/wine`, master, October 2026) to explain what
  was observed.

Window captures stayed local.

## Observations

Launcher windows (both runtimes, same layout):

| Window | Style / ex-style at start | Note |
|---|---|---|
| Main WPF window (`HwndWrapper[MuTheMatrix.exe;…]`, 794x584) | `16080000` / `000c0000` (`WS_EX_LAYERED \| WS_EX_APPWINDOW`), no owner | custom chrome, no `WS_MINIMIZEBOX` |
| News panel (`WindowsForms10.Window.8…`, 450x248) | `16010000` / `00010000`, owned by the main window | a WinForms form hosting the IE `WebBrowser` (Wine mshtml/Gecko), laid over the layered WPF window |

The launcher's **–** button (`+win` trace, one click) does the following:
1. It fades the news panel out: `SetLayeredWindowAttributes` alpha 238 … 0. The WPF window also fades (layered
   updates).
2. It calls `ShowWindow(main, SW_MINIMIZE)`. The window is parked at -32000,-32000.
3. WPF changes `ShowInTaskbar` to false: `SetWindowPos(SWP_HIDEWINDOW)`, then the owner becomes WPF's hidden
   "Hidden Window" and `WS_EX_APPWINDOW` is cleared (`SWP_FRAMECHANGED`), then `SetWindowPos(SWP_SHOWWINDOW)`.
4. It calls `ShowWindow(main, SW_HIDE)`.
5. It calls `Shell_NotifyIconW(NIM_ADD)` with the tooltip "Click to Restore Launcher". Wine's explorer created a
   status item, but no status-item window appeared in the window list and System Events showed no menu bar
   items for explorer.exe, so on this Mac (notch, crowded menu bar) the icon was not reachable.

Result (old proxy):
- The main window is iconic and hidden. Its Cocoa window is off screen and there is no Dock tile.
- The news panel stays visible on the Windows side, at alpha 0, and on screen on the macOS side.
- A Dock click on the launcher's icon ("wine") activates the app and restores nothing.

The tray-icon click (simulated with the message Wine's status item posts, WinForms `WM_USER+1024` with
`WM_LBUTTONDOWN`/`WM_LBUTTONUP`) runs the launcher's own restore:
- It shows the main window, sets `ShowInTaskbar` back to true and fades both windows in.
- It makes the news panel `TopMost` (`ex 00010008`).

From then on the panel sits at **macOS window layer 21**. That held with Finder frontmost. In the owner's session (found before testing) the panel was
TopMost at layer 21 above three game windows while the main window was minimized and hidden; it was faded
out then, but it floats visibly whenever the launcher is restored behind a game. After this restore the main WPF window was also stuck: it stayed
off screen as an `AXMinimizedWindowDockItem` while Windows reported it restored.

## Explanation (upstream source, matches the observations)

- `cocoa_app.m adjustWindowLevels:` raises every floating (`WS_EX_TOPMOST`) window to at least
  `kCGDockWindowLevel + 1` = 21 ("should have a window level higher than the macOS dock"), whatever
  `minimumLevelForActive:` returns. So `HKCU\Software\Wine\Mac Driver\WindowsFloatWhenInactive=none` cannot
  lower it. **Failed hypothesis, tested live in the free prefix:** with `none` set, the TopMost panel stayed at
  layer 21 while Finder was frontmost. The value was removed again.
- `applicationShouldHandleReopen:` (Dock click) calls `unminimizeWindowIfNoneVisible`. That function returns
  early if any Wine window of the app `isVisible` with content, and alpha is not considered. The faded panel
  therefore blocks it. Even without the panel there was nothing to deminiaturize, because the minimized main
  window had been hidden.
- On Windows an owned window is hidden while its owner is minimized. Wine does that only in DefWindowProc's
  `SC_MINIMIZE` path (`win32u/defwnd.c`: `NtUserShowOwnedPopups(hwnd, FALSE)`), not for an application's own
  `ShowWindow(SW_MINIMIZE)`, which is what WPF does.
- `setMacDrvState:` starts an animated `miniaturize:`. The hide, show and hide calls that follow within
  milliseconds (steps 3 and 4) reach `doOrderOut`/`doOrderIn` while it is still running. This can leave a
  miniaturized Cocoa window behind that Wine considers restored (inference from the stuck Dock tile; the exact
  interleaving was not traced).
- A Dock click on a miniaturized Wine window ends in `macdrv_window_did_unminimize`. If the window is
  `WS_MINIMIZE|WS_VISIBLE`, it calls `SetActiveWindow` and sends `WM_SYSCOMMAND SC_RESTORE`. DefWindowProc runs
  the CBT `HCBT_SYSCOMMAND` hook first, then re-shows owned popups and restores the window.
- Tested by hand (helper tool, old proxy): with the main window re-shown minimized and the panel hidden, a Dock
  click restored the main window. The launcher's state stayed "in tray", though: WPF content transparent, owner
  still the hidden window, tray icon still there. Only its tray-click handler restores the launcher completely.

## Fix (mscoree proxy v2, loads only in the launcher)

`winfix.c` swaps user32's import slots for `win32u!NtUserShowWindow`/`NtUserSetWindowPos`. In Wine,
`user32!ShowWindow`/`SetWindowPos` are `jmp [IAT]` thunks into win32u. It also installs a thread CBT hook and
hot-patches `shell32!Shell_NotifyIconW`. The free runtime's shell32 starts with `push ebp; mov ebp,esp`,
CrossOver's with `lea ecx,[esp+4]`; both are accepted, and anything else is left alone.

1. `SetWindowPos(HWND_TOPMOST)` on the process's own top-level windows becomes `HWND_NOTOPMOST`. The panel stays
   above the launcher as an owned window (a Cocoa child window).
2. Hiding a minimized top-level window (`SW_HIDE`, `SWP_HIDEWINDOW`) is ignored, so the window stays a Dock
   tile. Owned windows are hidden on minimize and shown on restore, as on Windows.
3. `HCBT_SYSCOMMAND SC_RESTORE` for the window the launcher sent to its tray posts the recorded tray-icon
   click: left down and up, which is what winemac posts for a status-item click. The launcher then restores
   itself completely.

`C:\mutools\winfix.log` records `window fix on` and `tray icon hook on`. `MU_LAUNCHER_WINFIX=0` disables the
fix.

## Live verification (2026-10-18)

Free runtime and MuMatrix32, same results. Three minimize/restore cycles each:
- a Dock click on the launcher's icon;
- a click on the minimized-window Dock tile;
- the tray-icon click.

Every cycle went: minimize gives one `AXMinimizedWindowDockItem` and the panel hidden. Restore gives the main
window visible with `WS_EX_APPWINDOW` back and no owner, the panel at alpha 1 and layer 0 with no
`WS_EX_TOPMOST`, and no leftover Dock tile. Afterwards GAME START was pressed and focus switched with System
Events:
- game frontmost: the game window is above both launcher windows, all at layer 0;
- launcher frontmost: the launcher is above the game.

## Open

- Whether the macOS menu bar shows Wine's status item at all on this macOS version was not established (no
  full-screen capture). The Dock is now the documented way back.
- Topmost windows created with `WS_EX_TOPMOST` in `CreateWindowEx` (not through `SetWindowPos`) are not
  changed. The launcher does not create any.
- The exact Cocoa interleaving behind the stale minimized tile was inferred, not traced.
