/* winfix.c — window fixes for the .NET launcher under Wine's macOS driver (MAC-APP-004).
 * Included by mscoree_proxy.c, so it runs only in MuTheMatrix.exe. Disable with MU_LAUNCHER_WINFIX=0.
 *
 * Observed with CrossOver/Wine CX 26.3 (free runtime and CrossOver bottle):
 *  - The launcher draws its news page in an owned WinForms window over the layered WPF window and
 *    makes it TopMost after every restore. winemac gives every WS_EX_TOPMOST window a level above the
 *    Dock (kCGDockWindowLevel + 1), also while the app is inactive; WindowsFloatWhenInactive does not
 *    lower it. So the panel floated over the game windows.
 *  - Its minimize button fades both windows out, minimizes, hides the minimized window and adds a
 *    tray icon ("Click to Restore Launcher"). A hidden window is no Dock tile and the faded panel
 *    stays on screen at alpha 0, so a Dock click had nothing to restore (Wine only unminimizes a
 *    window when no other window of the app is visible). The quick minimize/hide sequence could also
 *    leave a stale minimized Dock tile behind.
 * Fixes (hooks on user32's imports of win32u, plus a CBT hook and Shell_NotifyIconW):
 *  1. SetWindowPos(HWND_TOPMOST) on this process's top-level windows becomes HWND_NOTOPMOST. Owned
 *     windows stay above their owner anyway (winemac makes them Cocoa child windows).
 *  2. A minimized top-level window is never hidden (ShowWindow SW_HIDE / SWP_HIDEWINDOW): it stays
 *     minimized in the Dock. Its owned windows are hidden while it is minimized, as on Windows (Wine
 *     does that only for SC_MINIMIZE), and shown again on restore.
 *  3. Wine restores a Dock-clicked window with WM_SYSCOMMAND SC_RESTORE. If the launcher had sent
 *     that window to its tray icon, the click is also forwarded to the icon (left down + up, as
 *     winemac does for a menu-bar click), so the launcher's own restore code runs. */
#include <windows.h>
#include <shellapi.h>
#include <stddef.h>
#include <stdio.h>

typedef BOOL (WINAPI *WfShowFn)(HWND, INT);
typedef BOOL (WINAPI *WfPosFn)(HWND, HWND, INT, INT, INT, INT, UINT);
typedef BOOL (WINAPI *WfNotifyFn)(DWORD, PNOTIFYICONDATAW);
static WfShowFn wf_show; static WfPosFn wf_pos; static WfNotifyFn wf_notify;
static HWND wf_trayed;                     /* minimized window the launcher tried to hide (sent to its tray icon) */
static HHOOK wf_cbt; static int wf_shell_done;
static struct { HWND hwnd; UINT id, msg, version; } wf_icon;

/* Replace user32's import slot for win32u!name; returns the previous target. */
static void *wf_iat(HMODULE m, const char *dll, const char *name, void *hook)
{
    unsigned char *b = (unsigned char *)m;
    IMAGE_NT_HEADERS *nt = (IMAGE_NT_HEADERS *)(b + ((IMAGE_DOS_HEADER *)b)->e_lfanew);
    IMAGE_DATA_DIRECTORY dir = nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT];
    if (!dir.VirtualAddress) return NULL;
    for (IMAGE_IMPORT_DESCRIPTOR *d = (IMAGE_IMPORT_DESCRIPTOR *)(b + dir.VirtualAddress); d->Name; d++) {
        if (lstrcmpiA((const char *)(b + d->Name), dll) || !d->OriginalFirstThunk) continue;
        IMAGE_THUNK_DATA *names = (IMAGE_THUNK_DATA *)(b + d->OriginalFirstThunk), *slots = (IMAGE_THUNK_DATA *)(b + d->FirstThunk);
        for (; names->u1.AddressOfData; names++, slots++) {
            if (IMAGE_SNAP_BY_ORDINAL(names->u1.Ordinal)) continue;
            if (lstrcmpA((const char *)((IMAGE_IMPORT_BY_NAME *)(b + names->u1.AddressOfData))->Name, name)) continue;
            DWORD old; void *prev = (void *)slots->u1.Function;
            if (!VirtualProtect(&slots->u1.Function, sizeof(void *), PAGE_READWRITE, &old)) return NULL;
            slots->u1.Function = (ULONG_PTR)hook;
            VirtualProtect(&slots->u1.Function, sizeof(void *), old, &old);
            return prev;
        }
    }
    return NULL;
}

/* Hot-patch a function with 5 bytes of padding before it (Wine's i386 layout): a jmp to the hook in
   the padding and a short jmp over the first instruction(s), which must be one of the known
   position-independent prologues (copied to the trampoline):
   "mov edi,edi", "push ebp; mov ebp,esp" (free runtime build), "lea ecx,[esp+4]" (CrossOver's build,
   stack realignment). Returns a pointer that calls the original, or NULL (nothing patched). */
static void *wf_hotpatch(void *fn, void *hook)
{
    unsigned char *p = (unsigned char *)fn, *t; DWORD old; int skip;
    for (int i = 1; i <= 5; i++) if (p[-i] != 0x90 && p[-i] != 0xCC) return NULL;
    if (p[0] == 0x8B && p[1] == 0xFF) skip = 2;
    else if (p[0] == 0x55 && ((p[1] == 0x89 && p[2] == 0xE5) || (p[1] == 0x8B && p[2] == 0xEC))) skip = 3;
    else if (p[0] == 0x8D && p[1] == 0x4C && p[2] == 0x24 && p[3] == 0x04) skip = 4;
    else return NULL;
    if (!(t = VirtualAlloc(NULL, 16, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE))) return NULL;
    memcpy(t, p, skip); t[skip] = 0xE9; *(int *)(t + skip + 1) = (int)((p + skip) - (t + skip + 5));
    if (!VirtualProtect(p - 5, 8, PAGE_EXECUTE_READWRITE, &old)) return NULL;
    p[-5] = 0xE9; *(int *)(p - 4) = (int)((unsigned char *)hook - p);
    *(volatile WORD *)p = 0xF9EB;                         /* jmp short p-5 */
    VirtualProtect(p - 5, 8, old, &old); FlushInstructionCache(GetCurrentProcess(), p - 5, 8);
    return t;
}

static BOOL WINAPI wf_Notify(DWORD op, PNOTIFYICONDATAW d)
{
    if (d && d->cbSize >= offsetof(NOTIFYICONDATAW, hIcon)) {
        if (op == NIM_ADD || (op == NIM_MODIFY && (d->uFlags & NIF_MESSAGE))) {
            wf_icon.hwnd = d->hWnd; wf_icon.id = d->uID; wf_icon.msg = (d->uFlags & NIF_MESSAGE) ? d->uCallbackMessage : 0;
            if (op == NIM_ADD) wf_icon.version = 0;
        } else if (op == NIM_SETVERSION && d->hWnd == wf_icon.hwnd && d->cbSize >= offsetof(NOTIFYICONDATAW, dwInfoFlags))
            wf_icon.version = d->uVersion;
        else if (op == NIM_DELETE && d->hWnd == wf_icon.hwnd && d->uID == wf_icon.id) wf_icon.hwnd = NULL;
    }
    return wf_notify(op, d);
}

static void wf_tray_click(void)
{
    static const UINT seq[2] = { WM_LBUTTONDOWN, WM_LBUTTONUP };
    if (!wf_icon.hwnd || !wf_icon.msg || !IsWindow(wf_icon.hwnd)) return;
    POINT pt; GetCursorPos(&pt);
    for (int i = 0; i < 3; i++) {
        UINT m = i < 2 ? seq[i] : NIN_SELECT;
        if (i == 2 && !wf_icon.version) break;
        WPARAM wp = wf_icon.id; LPARAM lp = m;
        if (wf_icon.version >= NOTIFYICON_VERSION_4) { wp = MAKEWPARAM(pt.x, pt.y); lp = MAKELPARAM(m, wf_icon.id); }
        PostMessageW(wf_icon.hwnd, wf_icon.msg, wp, lp);
    }
}

static LRESULT CALLBACK wf_cbt_proc(int code, WPARAM wp, LPARAM lp)
{
    if (code == HCBT_SYSCOMMAND && (wp & 0xFFF0) == SC_RESTORE && wf_trayed && IsIconic(wf_trayed)) {
        wf_trayed = NULL;                                 /* Dock click: let the launcher restore itself */
        wf_tray_click();
    }
    return CallNextHookEx(wf_cbt, code, wp, lp);
}

static BOOL wf_mine(HWND h)
{
    DWORD pid = 0;
    return h && GetWindowThreadProcessId(h, &pid) && pid == GetCurrentProcessId() && !(GetWindowLongW(h, GWL_STYLE) & WS_CHILD);
}

static void wf_late_init(HWND h)
{   /* outside the loader lock, on the window's thread */
    if (!wf_shell_done) {
        wf_shell_done = 1;
        HMODULE s = LoadLibraryA("shell32.dll"); void *f = s ? (void *)GetProcAddress(s, "Shell_NotifyIconW") : NULL;
        if (f) wf_notify = (WfNotifyFn)wf_hotpatch(f, (void *)wf_Notify);
        FILE *lf = fopen("C:\\mutools\\winfix.log", "a");
        if (lf) { fprintf(lf, "  tray icon hook %s\n", wf_notify ? "on" : "off (Dock click restores the window only)"); fclose(lf); }
    }
    if (!wf_cbt && GetWindowThreadProcessId(h, NULL) == GetCurrentThreadId())
        wf_cbt = SetWindowsHookExW(WH_CBT, wf_cbt_proc, NULL, GetCurrentThreadId());
}

static BOOL WINAPI wf_ShowWindow(HWND h, INT cmd)
{
    if (!wf_mine(h)) return wf_show(h, cmd);
    wf_late_init(h);
    BOOL iconic = IsIconic(h);
    if (cmd == SW_HIDE && iconic && IsWindowVisible(h)) { wf_trayed = h; return TRUE; }   /* stay in the Dock */
    BOOL r = wf_show(h, cmd);
    if (cmd == SW_MINIMIZE || cmd == SW_SHOWMINIMIZED || cmd == SW_SHOWMINNOACTIVE || cmd == SW_FORCEMINIMIZE) {
        if (!iconic && IsIconic(h)) ShowOwnedPopups(h, FALSE);
    } else if (cmd != SW_HIDE && iconic && !IsIconic(h)) {
        if (wf_trayed == h) wf_trayed = NULL;
        ShowOwnedPopups(h, TRUE);
    }
    return r;
}

static BOOL WINAPI wf_SetWindowPos(HWND h, HWND after, INT x, INT y, INT cx, INT cy, UINT fl)
{
    if (wf_mine(h)) {
        if (after == HWND_TOPMOST && !(fl & SWP_NOZORDER)) after = HWND_NOTOPMOST;
        if ((fl & SWP_HIDEWINDOW) && IsIconic(h) && IsWindowVisible(h)) fl &= ~SWP_HIDEWINDOW;   /* WPF ShowInTaskbar refresh */
    }
    return wf_pos(h, after, x, y, cx, cy, fl);
}

/* returns 1 when the hooks are installed */
static int winfix_install(void)
{
    char v[8];
    if (GetEnvironmentVariableA("MU_LAUNCHER_WINFIX", v, sizeof v) && v[0] == '0') return 0;
    HMODULE u = GetModuleHandleA("user32.dll");
    if (!u || !GetModuleHandleA("win32u.dll")) return 0;     /* Wine only */
    void *s = wf_iat(u, "win32u.dll", "NtUserShowWindow", (void *)wf_ShowWindow);
    if (!s) return 0;
    wf_show = (WfShowFn)s;
    void *p = wf_iat(u, "win32u.dll", "NtUserSetWindowPos", (void *)wf_SetWindowPos);
    if (p) wf_pos = (WfPosFn)p;
    else { wf_iat(u, "win32u.dll", "NtUserShowWindow", s); return 0; }
    return 1;
}
