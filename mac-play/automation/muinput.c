/* muinput: scripted input for windows inside a Wine bottle (no macOS permissions needed).
   Usage: muinput.exe <command> [args...] ...   commands are executed left to right:
     wait <title-substring> <timeout_s>   wait for a top-level window whose title contains the text; make it the target
     focus                                bring target to foreground
     click <fx> <fy>                      left click at fraction of the target's client area
     dclick <fx> <fy>                     double click
     mclick <fx> <fy>                     middle click (MU Helper / auto-hunt toggle)
     type <text>                          type text (Unicode key events)
     key <vk-hex>                         press and release a virtual key (e.g. 0d Enter, 09 Tab, 1b Esc)
     kdown <vk-hex> / kup <vk-hex>        press / release a virtual key (e.g. hold 10 Shift around wheel steps)
     wheel <fx> <fy> <steps>              mouse wheel at a client fraction, one notch (120) per step, negative = toward user
     sleep <ms>
     rect                                 print target client rect in screen coordinates
   Exit code 2 if a wait times out. */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static HWND target; static const char *want; static int hold_ms = 250;
static BOOL CALLBACK enum_cb(HWND h, LPARAM l) {
    char t[256]; (void)l;
    if (!IsWindowVisible(h)) return TRUE;
    GetWindowTextA(h, t, sizeof t);
    if (strstr(t, want)) { target = h; return FALSE; }
    return TRUE;
}
static void client_point(double fx, double fy, int *x, int *y) {
    RECT r; GetClientRect(target, &r); POINT p = { (LONG)(r.right * fx), (LONG)(r.bottom * fy) };
    ClientToScreen(target, &p); *x = p.x; *y = p.y;
}
static void mouse(DWORD flags) { INPUT in = {0}; in.type = INPUT_MOUSE; in.mi.dwFlags = flags; SendInput(1, &in, sizeof in); }
static void click_at(double fx, double fy, int times) {
    int x, y; client_point(fx, fy, &x, &y);
    SetCursorPos(x, y); Sleep(120);
    for (int i = 0; i < times; i++) { mouse(MOUSEEVENTF_LEFTDOWN); Sleep(hold_ms); mouse(MOUSEEVENTF_LEFTUP); Sleep(150); }
    printf("click %.3f,%.3f -> %d,%d\n", fx, fy, x, y);
}
static void mclick_at(double fx, double fy) {
    int x, y; client_point(fx, fy, &x, &y);
    SetCursorPos(x, y); Sleep(120);
    mouse(MOUSEEVENTF_MIDDLEDOWN); Sleep(hold_ms); mouse(MOUSEEVENTF_MIDDLEUP); Sleep(150);
    printf("mclick %.3f,%.3f -> %d,%d\n", fx, fy, x, y);
}
static void vkey(WORD vk) {
    INPUT in[2] = {0};
    in[0].type = INPUT_KEYBOARD; in[0].ki.wVk = vk; in[0].ki.wScan = (WORD)MapVirtualKeyA(vk, 0);
    in[1] = in[0]; in[1].ki.dwFlags = KEYEVENTF_KEYUP;
    SendInput(1, &in[0], sizeof(INPUT)); Sleep(hold_ms / 2); SendInput(1, &in[1], sizeof(INPUT)); Sleep(80);
}
static void type_text(const char *s) {
    for (; *s; s++) {
        SHORT v = VkKeyScanA(*s);
        if (v != -1) {   /* virtual-key path (games often read WM_KEYDOWN/WM_CHAR from real key events) */
            BOOL shift = (v >> 8) & 1;
            if (shift) { INPUT d = {0}; d.type = INPUT_KEYBOARD; d.ki.wVk = VK_SHIFT; SendInput(1, &d, sizeof d); }
            vkey((WORD)(v & 0xff));
            if (shift) { INPUT u = {0}; u.type = INPUT_KEYBOARD; u.ki.wVk = VK_SHIFT; u.ki.dwFlags = KEYEVENTF_KEYUP; SendInput(1, &u, sizeof u); }
        } else {
            INPUT in[2] = {0}; in[0].type = INPUT_KEYBOARD; in[0].ki.wScan = (WCHAR)(unsigned char)*s; in[0].ki.dwFlags = KEYEVENTF_UNICODE;
            in[1] = in[0]; in[1].ki.dwFlags |= KEYEVENTF_KEYUP; SendInput(2, in, sizeof(INPUT));
        }
        Sleep(70);
    }
    printf("typed %d chars\n", (int)strlen(s - 0) );
}
int main(int argc, char **argv) {
    for (int i = 1; i < argc; i++) {
        const char *c = argv[i];
        if (!strcmp(c, "wait") && i + 2 < argc) {
            want = argv[++i]; int t = atoi(argv[++i]); target = NULL;
            for (int k = 0; k < t * 4 && !target; k++) { EnumWindows(enum_cb, 0); if (!target) Sleep(250); }
            if (!target) { printf("wait timeout: %s\n", want); return 2; }
            char title[256]; GetWindowTextA(target, title, sizeof title); printf("window: %s\n", title);
        } else if (!strcmp(c, "move") && i + 2 < argc) { double fx = atof(argv[++i]), fy = atof(argv[++i]); int x, y; client_point(fx, fy, &x, &y); SetCursorPos(x, y); Sleep(200); printf("move -> %d,%d\n", x, y);
        } else if (!strcmp(c, "pclick") && i + 2 < argc) {   /* posted client-area button messages */
            double fx = atof(argv[++i]), fy = atof(argv[++i]); RECT r; GetClientRect(target, &r);
            int x = (int)(r.right * fx), y = (int)(r.bottom * fy); int sx, sy; client_point(fx, fy, &sx, &sy); SetCursorPos(sx, sy); Sleep(100);
            LPARAM lp = MAKELPARAM(x, y);
            PostMessageA(target, WM_MOUSEMOVE, 0, lp); Sleep(80);
            PostMessageA(target, WM_LBUTTONDOWN, MK_LBUTTON, lp); Sleep(hold_ms);
            PostMessageA(target, WM_LBUTTONUP, 0, lp); Sleep(150);
            printf("pclick %.3f,%.3f -> client %d,%d\n", fx, fy, x, y);
} else if (!strcmp(c, "activate")) {   /* tell the game it is the active app (macOS focus may be elsewhere) */
            SendMessageA(target, WM_ACTIVATEAPP, TRUE, 0); SendMessageA(target, WM_NCACTIVATE, TRUE, 0);
            SendMessageA(target, WM_ACTIVATE, WA_ACTIVE, 0); SendMessageA(target, WM_SETFOCUS, 0, 0);
            DWORD me = GetCurrentThreadId(), tt = GetWindowThreadProcessId(target, NULL);
            AttachThreadInput(me, tt, TRUE);
            BringWindowToTop(target); SetForegroundWindow(target); SetFocus(target); SetActiveWindow(target);
            AttachThreadInput(me, tt, FALSE);
            printf("foreground now %p (target %p)\n", (void *)GetForegroundWindow(), (void *)target); Sleep(300);
} else if (!strcmp(c, "focus")) { ShowWindow(target, SW_RESTORE); SetForegroundWindow(target); Sleep(300); }
        else if (!strcmp(c, "click") && i + 2 < argc) { double fx = atof(argv[++i]), fy = atof(argv[++i]); click_at(fx, fy, 1); }
        else if (!strcmp(c, "mclick") && i + 2 < argc) { double fx = atof(argv[++i]), fy = atof(argv[++i]); mclick_at(fx, fy); }
        else if (!strcmp(c, "dclick") && i + 2 < argc) { double fx = atof(argv[++i]), fy = atof(argv[++i]); click_at(fx, fy, 2); }
        else if (!strcmp(c, "type") && i + 1 < argc) type_text(argv[++i]);
        else if (!strcmp(c, "key") && i + 1 < argc) vkey((WORD)strtoul(argv[++i], 0, 16));
        else if ((!strcmp(c, "kdown") || !strcmp(c, "kup")) && i + 1 < argc) {
            INPUT in = {0}; in.type = INPUT_KEYBOARD; in.ki.wVk = (WORD)strtoul(argv[++i], 0, 16);
            in.ki.wScan = (WORD)MapVirtualKeyA(in.ki.wVk, 0); if (c[1] == 'u') in.ki.dwFlags = KEYEVENTF_KEYUP;
            SendInput(1, &in, sizeof in); Sleep(80);
        } else if (!strcmp(c, "wheel") && i + 3 < argc) {
            double fx = atof(argv[++i]), fy = atof(argv[++i]); int n = atoi(argv[++i]), x, y; client_point(fx, fy, &x, &y);
            SetCursorPos(x, y); Sleep(120);
            for (int k = 0; k < (n < 0 ? -n : n); k++) { INPUT in = {0}; in.type = INPUT_MOUSE; in.mi.dwFlags = MOUSEEVENTF_WHEEL; in.mi.mouseData = (DWORD)(n < 0 ? -WHEEL_DELTA : WHEEL_DELTA); SendInput(1, &in, sizeof in); Sleep(120); }
            printf("wheel %d at %d,%d\n", n, x, y);
        }
        else if (!strcmp(c, "sleep") && i + 1 < argc) Sleep(atoi(argv[++i]));
        else if (!strcmp(c, "hold") && i + 1 < argc) hold_ms = atoi(argv[++i]);
        else if (!strcmp(c, "rect")) { RECT r; GetClientRect(target, &r); POINT p = {0, 0}; ClientToScreen(target, &p); printf("client %ld,%ld %ldx%ld\n", p.x, p.y, r.right, r.bottom); }
        else { printf("bad command %s\n", c); return 1; }
    }
    return 0;
}
