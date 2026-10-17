/* meshbench: MU-like model workload (GL_TRIANGLES blocks of ~565 verts, per-vertex attribute calls).
   Usage: meshbench.exe frames blocks verts attrs   (attrs: letters t c n, e.g. "tc")
   Prints ms/frame and ns/vertex for the submission side only (vertex data is precomputed). */
#include <windows.h>
#include <GL/gl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static LRESULT CALLBACK wp(HWND h, UINT m, WPARAM w, LPARAM l) { return DefWindowProcA(h, m, w, l); }
int main(int argc, char **argv) {
    int frames = argc > 1 ? atoi(argv[1]) : 40, blocks = argc > 2 ? atoi(argv[2]) : 1700, verts = argc > 3 ? atoi(argv[3]) : 564;
    const char *at = argc > 4 ? argv[4] : "tc";
    int ut = !!strchr(at, 't'), uc = !!strchr(at, 'c'), un = !!strchr(at, 'n'), none = !!strchr(at, '0');
    WNDCLASSA wc = {0}; wc.lpfnWndProc = wp; wc.hInstance = GetModuleHandleA(0); wc.lpszClassName = "mb"; RegisterClassA(&wc);
    HWND w = CreateWindowA("mb", "meshbench", WS_OVERLAPPEDWINDOW, 0, 0, 640, 480, 0, 0, wc.hInstance, 0);
    HDC dc = GetDC(w);
    PIXELFORMATDESCRIPTOR pfd = { sizeof(pfd), 1, PFD_DRAW_TO_WINDOW | PFD_SUPPORT_OPENGL | PFD_DOUBLEBUFFER, PFD_TYPE_RGBA, 32 };
    pfd.cDepthBits = 24; SetPixelFormat(dc, ChoosePixelFormat(dc, &pfd), &pfd);
    HGLRC rc = wglCreateContext(dc); wglMakeCurrent(dc, rc);
    float *data = malloc(sizeof(float) * 12 * verts);
    for (int i = 0; i < verts; i++) { float *d = data + 12 * i;
        d[0] = (i % 7) / 7.f; d[1] = (i % 5) / 5.f; d[2] = .5f + (i % 3) * .1f; d[3] = .6f; d[4] = .7f; d[5] = 0; d[6] = 0; d[7] = 1;
        d[8] = (i % 30) / 15.f - 1; d[9] = (i / 30 % 30) / 15.f - 1; d[10] = 0; d[11] = 1; }
    glEnable(GL_DEPTH_TEST); glEnable(GL_TEXTURE_2D);
    LARGE_INTEGER f, t0, t1, a, b; QueryPerformanceFrequency(&f); MSG msg; double swap = 0;
    QueryPerformanceCounter(&t0);
    for (int fr = 0; fr < frames; fr++) {
        while (PeekMessageA(&msg, 0, 0, 0, PM_REMOVE)) DispatchMessageA(&msg);
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
        for (int k = 0; k < blocks; k++) {
            if (!none) { glBindTexture(GL_TEXTURE_2D, 1 + (k & 3)); glBegin(GL_TRIANGLES); }
            for (int i = 0; i < verts; i++) { const float *d = data + 12 * i;
                if (none) continue;
                if (ut) glTexCoord2f(d[0], d[1]);
                if (uc) glColor3fv(d + 2);
                if (un) glNormal3fv(d + 5);
                glVertex3fv(d + 8); }
            if (!none) glEnd();
        }
        QueryPerformanceCounter(&a); SwapBuffers(dc); QueryPerformanceCounter(&b); swap += (double)(b.QuadPart - a.QuadPart) / f.QuadPart;
    }
    glFinish(); QueryPerformanceCounter(&t1);
    double s = (double)(t1.QuadPart - t0.QuadPart) / f.QuadPart;
    printf("attrs=%s blocks=%d verts=%d frames=%d ms/frame=%.2f (swap %.2f) ns/vertex=%.1f\n", at, blocks, verts, frames,
           s * 1000 / frames, swap * 1000 / frames, s * 1e9 / ((double)frames * blocks * verts));
    return 0;
}
