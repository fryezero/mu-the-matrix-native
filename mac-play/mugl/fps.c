/* In-game FPS counter (MAC-APP-003). Included by mugl.c and hotpatch/mugl.c; drawn from mugl_wglSwapBuffers.

   C:\mutools\mugl-fps.txt: "1" shows the counter, "0" (or no file) hides it; an optional second word picks the
   corner (tl, tr, bl, br; default tl). The file is re-read about once a second, so the Mac app can change it while
   the game runs. Ctrl+Shift+F in the game window toggles the counter and writes the file, so the choice is kept.

   The counter is the average over the last half second of frames presented (wglSwapBuffers calls), with the frame
   time in milliseconds, in a dark box: green from 24 fps, yellow from 15, red below. It is drawn with the real GL
   entry points (never the batching layer) inside glPushAttrib(GL_ALL_ATTRIB_BITS) / glPopAttrib and pushed
   projection/modelview matrices, so every piece of GL state the game or mugl tracks (current colour, matrix mode,
   enables, texture bindings on all units, viewport, blending) is exactly as before. About 60 GL calls per frame,
   all rectangles (glRectf); nothing at all while it is hidden. */

#ifndef GL_TEXTURE0
#define GL_TEXTURE0 0x84C0
#endif
typedef void (WINAPI *PFNfps_1u)(GLenum);
typedef void (WINAPI *PFNfps_geti)(GLenum, GLint *);
typedef void (WINAPI *PFNfps_bits)(GLbitfield);
typedef void (WINAPI *PFNfps_0)(void);
typedef void (WINAPI *PFNfps_4f)(GLfloat, GLfloat, GLfloat, GLfloat);
typedef void (WINAPI *PFNfps_vp)(GLint, GLint, GLsizei, GLsizei);
typedef void (WINAPI *PFNfps_ortho)(GLdouble, GLdouble, GLdouble, GLdouble, GLdouble, GLdouble);
typedef void (WINAPI *PFNfps_2e)(GLenum, GLenum);
typedef void (WINAPI *PFNfps_cmask)(GLboolean, GLboolean, GLboolean, GLboolean);

static int fps_on, fps_corner;            /* corner: 0 tl, 1 tr, 2 bl, 3 br */
static DWORD fps_file_checked;
static int fps_keys_down;                 /* Ctrl+Shift+F held at the last frame (edge detection) */
static LARGE_INTEGER fps_freq, fps_t0;
static long fps_frames;
static double fps_value = -1;             /* last half-second average; < 0 until the first one */
static void *fps_activetex;               /* glActiveTexture(ARB) if the game asked for it; see mugl_wglGetProcAddress */

/* 3x5 glyphs, one row per element (bit 2 = left column): 0-9, '.', 'F', 'P', 'S', 'M', ' ' */
static const unsigned char fps_font[16][5] = {
    {7,5,5,5,7}, {2,6,2,2,7}, {7,1,7,4,7}, {7,1,7,1,7}, {5,5,7,1,1}, {7,4,7,1,7}, {7,4,7,5,7}, {7,1,1,2,2},
    {7,5,7,5,7}, {7,5,7,1,7}, {0,0,0,0,2}, {7,4,6,4,4}, {7,5,7,4,4}, {7,4,7,1,7}, {5,7,7,5,5}, {0,0,0,0,0},
};
static int fps_glyph(char c)
{
    if (c >= '0' && c <= '9') return c - '0';
    switch (c) { case '.': return 10; case 'F': return 11; case 'P': return 12; case 'S': return 13; case 'M': return 14; }
    return 15;
}

static void fps_read_file(void)
{
    char a[8] = "", b[8] = "";
    FILE *f = fopen("C:\\mutools\\mugl-fps.txt", "r");
    int on = 0, corner = 0;
    if (f) {
        if (fscanf(f, "%7s %7s", a, b) >= 1) on = a[0] == '1';
        fclose(f);
        if (!strcmp(b, "tr")) corner = 1; else if (!strcmp(b, "bl")) corner = 2; else if (!strcmp(b, "br")) corner = 3;
    }
    if (on && !fps_on) { fps_frames = 0; fps_t0.QuadPart = 0; fps_value = -1; }
    fps_on = on; fps_corner = corner;
}

static void fps_write_file(void)
{
    static const char *cn[4] = {"tl", "tr", "bl", "br"};
    FILE *f = fopen("C:\\mutools\\mugl-fps.txt", "w");
    if (f) { fprintf(f, "%d %s\n", fps_on, cn[fps_corner & 3]); fclose(f); }
}

/* Ctrl+Shift+F, only while a window of this process is in front (so typing elsewhere never toggles it). */
static void fps_poll_keys(void)
{
    int down = 0;
    if (GetAsyncKeyState(VK_CONTROL) & 0x8000) {
        HWND fg = GetForegroundWindow(); DWORD pid = 0;
        if (fg) GetWindowThreadProcessId(fg, &pid);
        down = pid == GetCurrentProcessId() && (GetAsyncKeyState(VK_SHIFT) & 0x8000) && (GetAsyncKeyState('F') & 0x8000);
    }
    if (down && !fps_keys_down) {
        fps_on = !fps_on; fps_frames = 0; fps_t0.QuadPart = 0; fps_value = -1;
        fps_write_file(); fps_file_checked = GetTickCount();
    }
    fps_keys_down = down;
}

static void fps_text(char *out, size_t n)
{
    if (fps_value < 0) { snprintf(out, n, "FPS"); return; }
    double ms = fps_value > 0.05 ? 1000.0 / fps_value : 0;
    snprintf(out, n, "%.1f FPS %.1f MS", fps_value > 999.9 ? 999.9 : fps_value, ms > 999.9 ? 999.9 : ms);
}

static void fps_draw(HDC dc)
{
    RECT rc; HWND w = WindowFromDC(dc);
    if (!w || !GetClientRect(w, &rc) || rc.right <= 0 || rc.bottom <= 0) return;
    int W = rc.right, H = rc.bottom;
    /* Room on the attribute and both matrix stacks, or the pops below would take the game's entries. */
    static GLint max_attrib, max_proj, max_mv;
    PFNfps_geti geti = (PFNfps_geti)real_glGetIntegerv;
    if (!max_attrib) { geti(GL_MAX_ATTRIB_STACK_DEPTH, &max_attrib); geti(GL_MAX_PROJECTION_STACK_DEPTH, &max_proj); geti(GL_MAX_MODELVIEW_STACK_DEPTH, &max_mv); }
    GLint da = 0, dp = 0, dm = 0;
    geti(GL_ATTRIB_STACK_DEPTH, &da); geti(GL_PROJECTION_STACK_DEPTH, &dp); geti(GL_MODELVIEW_STACK_DEPTH, &dm);
    if (da >= max_attrib || dp >= max_proj || dm >= max_mv) return;
    char text[32]; fps_text(text, sizeof text);
    int len = (int)strlen(text);
    float s = (float)(H >= 480 ? H / 240 : 2);              /* pixel size: 4 at 1080 rows */
    float pad = 2 * s, tw = len * 4 * s - s, th = 5 * s;
    float bw = tw + 2 * pad, bh = th + 2 * pad, m = 4 * s;
    float x0 = (fps_corner & 1) ? W - m - bw : m, y0 = (fps_corner & 2) ? H - m - bh : m;   /* top-left origin */

    ((PFNfps_bits)real_glPushAttrib)(GL_ALL_ATTRIB_BITS);
    if (fps_activetex)                                       /* texturing off on every unit, then unit 0 active */
        for (int u = 3; u >= 0; u--) { ((PFNfps_1u)fps_activetex)(GL_TEXTURE0 + u); ((PFNfps_1u)real_glDisable)(GL_TEXTURE_2D); }
    static const GLenum off[] = {GL_TEXTURE_2D, GL_DEPTH_TEST, GL_LIGHTING, GL_FOG, GL_CULL_FACE, GL_ALPHA_TEST, GL_SCISSOR_TEST,
                                 GL_STENCIL_TEST, GL_TEXTURE_GEN_S, GL_TEXTURE_GEN_T, GL_COLOR_LOGIC_OP, GL_COLOR_MATERIAL,
                                 GL_CLIP_PLANE0, GL_CLIP_PLANE1, GL_CLIP_PLANE2, GL_CLIP_PLANE3, GL_CLIP_PLANE4, GL_CLIP_PLANE5};
    for (size_t i = 0; i < sizeof off / sizeof off[0]; i++) ((PFNfps_1u)real_glDisable)(off[i]);
    ((PFNfps_1u)real_glEnable)(GL_BLEND);
    ((PFNfps_2e)real_glBlendFunc)(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    ((PFNfps_2e)real_glPolygonMode)(GL_FRONT_AND_BACK, GL_FILL);
    ((PFNfps_cmask)real_glColorMask)(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE);
    ((PFNfps_vp)real_glViewport)(0, 0, W, H);
    ((PFNfps_1u)real_glMatrixMode)(GL_PROJECTION); ((PFNfps_0)real_glPushMatrix)(); ((PFNfps_0)real_glLoadIdentity)();
    ((PFNfps_ortho)real_glOrtho)(0, W, H, 0, -1, 1);
    ((PFNfps_1u)real_glMatrixMode)(GL_MODELVIEW); ((PFNfps_0)real_glPushMatrix)(); ((PFNfps_0)real_glLoadIdentity)();

    PFNfps_4f rect = (PFNfps_4f)real_glRectf, color = (PFNfps_4f)real_glColor4f;
    color(0, 0, 0, 0.6f); rect(x0, y0, x0 + bw, y0 + bh);
    if (fps_value < 0) color(0.85f, 0.85f, 0.85f, 1);
    else if (fps_value >= 24) color(0.35f, 1, 0.35f, 1);
    else if (fps_value >= 15) color(1, 0.85f, 0.2f, 1);
    else color(1, 0.35f, 0.3f, 1);
    float x = x0 + pad, y = y0 + pad;
    for (int i = 0; i < len; i++, x += 4 * s) {
        const unsigned char *g = fps_font[fps_glyph(text[i])];
        for (int r = 0; r < 5; r++) {                        /* one rectangle per horizontal run */
            for (int c = 0; c < 3; ) {
                if (!(g[r] >> (2 - c) & 1)) { c++; continue; }
                int e = c; while (e < 3 && (g[r] >> (2 - e) & 1)) e++;
                rect(x + c * s, y + r * s, x + e * s, y + (r + 1) * s);
                c = e;
            }
        }
    }

    ((PFNfps_0)real_glPopMatrix)();
    ((PFNfps_1u)real_glMatrixMode)(GL_PROJECTION); ((PFNfps_0)real_glPopMatrix)();
    ((PFNfps_0)real_glPopAttrib)();                           /* restores matrix mode, active texture unit, colour, ... */
}

/* Called once per frame before the real wglSwapBuffers, after the batch was flushed (mugl_sync). */
static void fps_frame(HDC dc)
{
    DWORD now = GetTickCount();
    if (!fps_file_checked || now - fps_file_checked >= 1000) { fps_read_file(); fps_file_checked = now ? now : 1; }
    fps_poll_keys();
    if (!fps_on) return;
    LARGE_INTEGER t; QueryPerformanceCounter(&t);
    if (!fps_freq.QuadPart) QueryPerformanceFrequency(&fps_freq);
    if (!fps_t0.QuadPart) { fps_t0 = t; fps_frames = 0; }
    else {
        fps_frames++;
        double secs = (double)(t.QuadPart - fps_t0.QuadPart) / fps_freq.QuadPart;
        if (secs >= 0.5) { fps_value = fps_frames / secs; fps_frames = 0; fps_t0 = t; }
    }
    fps_draw(dc);
}
