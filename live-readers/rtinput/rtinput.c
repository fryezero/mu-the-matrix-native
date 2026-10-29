/* rtinput.exe <title-substring> <schedule.txt> <go-file> <log.txt>: RENDER-TIME-002 physical-input replay inside Wine.
   Build (macOS host, optional): i686-w64-mingw32-gcc -O2 -o rtinput.exe rtinput.c -lwinmm
   The schedule is written by scripts/render_time_live.py from an INPUT-001 script: one "FRAME VERB X Y" line per
   event (verbs move, ldown, lup, wheel; X Y in 640x480 drawable pixels; wheel uses X as the signed detent count).
   It waits for the window, makes it active (the script's 0:focus:1), parks nothing, then polls for the go file the
   sampler creates after its frame-0 post-draw sample. Event k fires at go + 40 ms * frame (the 25 Hz input loop);
   each event's scheduled and actual offset are logged. Only SetCursorPos / SendInput: no memory access. */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static HWND target; static const char *want;
static BOOL CALLBACK enum_cb(HWND h, LPARAM l)
{
    char title[256]; (void)l;
    if (!IsWindowVisible(h)) return TRUE;
    GetWindowTextA(h, title, sizeof title);
    if (strstr(title, want)) { target = h; return FALSE; }
    return TRUE;
}
static void mouse(DWORD flags, DWORD data)
{
    INPUT in = {0}; in.type = INPUT_MOUSE; in.mi.dwFlags = flags; in.mi.mouseData = data; SendInput(1, &in, sizeof in);
}
int main(int argc, char **argv)
{
    if (argc != 5) { printf("usage: rtinput title schedule go log\n"); return 2; }
    want = argv[1];
    for (int k = 0; k < 120 && !target; k++) { EnumWindows(enum_cb, 0); if (!target) Sleep(250); }
    if (!target) { printf("wait timeout\n"); return 2; }
    int frame[128], x[128], y[128], n = 0; char verb[128][8];
    FILE *s = fopen(argv[2], "r");
    if (!s) { printf("no schedule\n"); return 2; }
    while (n < 128 && fscanf(s, "%d %7s %d %d", &frame[n], verb[n], &x[n], &y[n]) == 4) n++;
    fclose(s);
    for (int i = 0; i < n; i++)
        if (strcmp(verb[i], "move") && strcmp(verb[i], "ldown") && strcmp(verb[i], "lup") && strcmp(verb[i], "wheel")) {
            printf("unsupported verb %s\n", verb[i]); return 2;
        }
    FILE *log = fopen(argv[4], "w");
    if (!log) return 2;
    SendMessageA(target, WM_ACTIVATEAPP, TRUE, 0); SendMessageA(target, WM_NCACTIVATE, TRUE, 0);
    SendMessageA(target, WM_ACTIVATE, WA_ACTIVE, 0); SendMessageA(target, WM_SETFOCUS, 0, 0);
    DWORD me = GetCurrentThreadId(), tt = GetWindowThreadProcessId(target, NULL);
    AttachThreadInput(me, tt, TRUE);
    BringWindowToTop(target); SetForegroundWindow(target); SetFocus(target); SetActiveWindow(target);
    AttachThreadInput(me, tt, FALSE);
    RECT r; GetClientRect(target, &r); POINT origin = {0, 0}; ClientToScreen(target, &origin);
    fprintf(log, "client %ld %ld %ld %ld foreground %d\n", origin.x, origin.y, r.right, r.bottom, GetForegroundWindow() == target);
    fflush(log);
    timeBeginPeriod(1);
    LARGE_INTEGER f, t0, now; QueryPerformanceFrequency(&f);
    DWORD waited = GetTickCount();
    while (GetFileAttributesA(argv[3]) == INVALID_FILE_ATTRIBUTES) {
        if (GetTickCount() - waited > 120000) { fprintf(log, "go timeout\n"); fclose(log); return 3; }
        Sleep(1);
    }
    QueryPerformanceCounter(&t0);
    for (int i = 0; i < n; i++) {
        double due = frame[i] * 40.0, ms;
        for (;;) {
            QueryPerformanceCounter(&now);
            ms = (now.QuadPart - t0.QuadPart) * 1000.0 / f.QuadPart;
            if (ms >= due) break;
            if (due - ms > 2) Sleep(1);
        }
        int sx = origin.x + x[i] * r.right / 640, sy = origin.y + y[i] * r.bottom / 480;
        if (!strcmp(verb[i], "wheel")) mouse(MOUSEEVENTF_WHEEL, (DWORD)(x[i] * WHEEL_DELTA));
        else {
            SetCursorPos(sx, sy);
            if (!strcmp(verb[i], "ldown")) mouse(MOUSEEVENTF_LEFTDOWN, 0);
            if (!strcmp(verb[i], "lup")) mouse(MOUSEEVENTF_LEFTUP, 0);
        }
        fprintf(log, "event %d %s %d %d due %.1f sent %.1f\n", frame[i], verb[i], x[i], y[i], due, ms);
    }
    fclose(log);
    timeEndPeriod(1);
    return 0;
}
