/* glbench: measures per-call cost of legacy immediate-mode OpenGL (MU-like workload).
   Usage: glbench.exe [frames] [quads_per_frame] */
#include <windows.h>
#include <GL/gl.h>
#include <stdio.h>
#include <stdlib.h>
static LRESULT CALLBACK wp(HWND h, UINT m, WPARAM w, LPARAM l) { return DefWindowProcA(h, m, w, l); }
int main(int argc, char **argv) {
    int frames = argc > 1 ? atoi(argv[1]) : 120, quads = argc > 2 ? atoi(argv[2]) : 4000;
    if (frames <= 0 || quads <= 0) { fprintf(stderr, "Use positive frame and quad counts\n"); return 2; }
    WNDCLASSA wc = {0}; wc.lpfnWndProc = wp; wc.hInstance = GetModuleHandleA(0); wc.lpszClassName = "glb"; RegisterClassA(&wc);
    HWND w = CreateWindowA("glb", "glbench", WS_OVERLAPPEDWINDOW | WS_VISIBLE, 0, 0, 640, 480, 0, 0, wc.hInstance, 0);
    if (!w) { fprintf(stderr, "CreateWindow failed: %lu\n", GetLastError()); return 1; }
    HDC dc = GetDC(w);
    PIXELFORMATDESCRIPTOR pfd = { sizeof(pfd), 1, PFD_DRAW_TO_WINDOW | PFD_SUPPORT_OPENGL | PFD_DOUBLEBUFFER, PFD_TYPE_RGBA, 32 };
    pfd.cDepthBits = 24;
    int format = ChoosePixelFormat(dc, &pfd);
    if (!format || !SetPixelFormat(dc, format, &pfd)) { fprintf(stderr, "Pixel format failed: %lu\n", GetLastError()); return 1; }
    HGLRC rc = wglCreateContext(dc);
    if (!rc || !wglMakeCurrent(dc, rc)) { fprintf(stderr, "GL context failed: %lu\n", GetLastError()); return 1; }
    printf("GL_VENDOR=%s\nGL_RENDERER=%s\nGL_VERSION=%s\n", glGetString(GL_VENDOR), glGetString(GL_RENDERER), glGetString(GL_VERSION));
    LARGE_INTEGER f, t0, t1; QueryPerformanceFrequency(&f);
    long long calls = 0; MSG msg;
    QueryPerformanceCounter(&t0);
    for (int i = 0; i < frames; i++) {
        while (PeekMessageA(&msg, 0, 0, 0, PM_REMOVE)) DispatchMessageA(&msg);
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT); calls++;
        for (int q = 0; q < quads; q++) {
            float x = (q % 64) / 32.0f - 1.0f, y = (q / 64 % 64) / 32.0f - 1.0f;
            glBegin(GL_QUADS);
            glColor4f(1, (q & 7) / 7.0f, 0.5f, 1); glTexCoord2f(0, 0); glVertex3f(x, y, 0);
            glTexCoord2f(1, 0); glVertex3f(x + .02f, y, 0);
            glTexCoord2f(1, 1); glVertex3f(x + .02f, y + .02f, 0);
            glTexCoord2f(0, 1); glVertex3f(x, y + .02f, 0);
            glEnd();
            calls += 11;
        }
        SwapBuffers(dc); calls++;
    }
    glFinish();
    QueryPerformanceCounter(&t1);
    double s = (double)(t1.QuadPart - t0.QuadPart) / f.QuadPart;
    printf("frames=%d quads/frame=%d time=%.2fs fps=%.1f gl_calls/s=%.0f ns/call=%.0f\n", frames, quads, s, frames / s, calls / s, s * 1e9 / calls);
    GLenum error = glGetError();
    wglMakeCurrent(NULL, NULL); wglDeleteContext(rc); ReleaseDC(w, dc); DestroyWindow(w);
    if (error != GL_NO_ERROR) { fprintf(stderr, "GL error: %u\n", error); return 1; }
    return 0;
}
