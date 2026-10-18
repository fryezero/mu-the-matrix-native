/* glvbench: cost of submitting MU-sized mesh batches from client memory, by vertex layout and transport.
   Usage: glvbench.exe variant [frames draws verts]
   A frame is `draws` GL_TRIANGLES draws of `verts` vertices (default 1700 x 690, the zoomed-out mesh load), each
   with a texture switch, from one reused 48-byte T2F_C4F_N3F_V3F buffer like mugl's batch. Variants:
     0 interleaved stride 48 (mugl zero-copy)      1 stride 48, normal array off
     2 packed 36-byte T2F C4F V3F                  3 stream VBO stride 48 (orphan per frame, BufferSubData per draw)
     4 stream VBO packed 36                        5 per-draw BufferData of the batch, stride 48
     6 stride 48, normal off, colour as 4 ubyte (not exact; size reference)
   Prints the CPU submission time per frame, the swap time and a glFinish time. Not a correctness test. */
#include <windows.h>
#include <GL/gl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef ptrdiff_t GLsizeiptr_; typedef ptrdiff_t GLintptr_;
static LRESULT CALLBACK wp(HWND h, UINT m, WPARAM w, LPARAM l) { return DefWindowProcA(h, m, w, l); }
static float fr(unsigned i) { i = i * 2654435761u; i ^= i >> 13; i *= 0x5bd1e995u; i ^= i >> 15; return (i & 0xffff) / 65535.0f; }
int main(int argc, char **argv)
{
    int var = argc > 1 ? atoi(argv[1]) : 0, frames = argc > 2 ? atoi(argv[2]) : 100, draws = argc > 3 ? atoi(argv[3]) : 1700,
        verts = argc > 4 ? atoi(argv[4]) : 690;
    WNDCLASSA wc = {0}; wc.lpfnWndProc = wp; wc.hInstance = GetModuleHandleA(0); wc.lpszClassName = "gvb"; RegisterClassA(&wc);
    HWND w = CreateWindowA("gvb", "glvbench", WS_OVERLAPPEDWINDOW | WS_VISIBLE, 0, 0, 1728, 1080, 0, 0, wc.hInstance, 0);
    HDC dc = GetDC(w);
    PIXELFORMATDESCRIPTOR pfd = { sizeof(pfd), 1, PFD_DRAW_TO_WINDOW | PFD_SUPPORT_OPENGL | PFD_DOUBLEBUFFER, PFD_TYPE_RGBA, 32 };
    pfd.cDepthBits = 24; SetPixelFormat(dc, ChoosePixelFormat(dc, &pfd), &pfd);
    HGLRC rc = wglCreateContext(dc); wglMakeCurrent(dc, rc);
    void (WINAPI *genb)(GLsizei, GLuint *) = (void *)wglGetProcAddress("glGenBuffersARB");
    void (WINAPI *bindb)(GLenum, GLuint) = (void *)wglGetProcAddress("glBindBufferARB");
    void (WINAPI *bdata)(GLenum, GLsizeiptr_, const void *, GLenum) = (void *)wglGetProcAddress("glBufferDataARB");
    void (WINAPI *bsub)(GLenum, GLintptr_, GLsizeiptr_, const void *) = (void *)wglGetProcAddress("glBufferSubDataARB");
    GLuint tex[8]; glGenTextures(8, tex);
    unsigned *img = malloc(256 * 256 * 4);
    for (int t = 0; t < 8; t++) {
        for (int i = 0; i < 256 * 256; i++) img[i] = 0xff000000u | (unsigned)(fr(i + t * 77777) * 0xffffff);
        glBindTexture(GL_TEXTURE_2D, tex[t]); glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, 256, 256, 0, GL_RGBA, GL_UNSIGNED_BYTE, img);
    }
    /* per draw a fresh set of small triangles: 48-byte source records */
    float *src = malloc(sizeof(float) * 12 * verts * 8);
    for (int i = 0; i < verts * 8; i++) {
        float *d = src + 12 * i; int t = i / 3; float cx = fr(t * 3 + 1) * 2 - 1, cy = fr(t * 3 + 2) * 2 - 1;
        d[0] = fr(i * 5 + 1); d[1] = fr(i * 5 + 2); d[2] = fr(i * 7 + 1); d[3] = fr(i * 7 + 2); d[4] = fr(i * 7 + 3); d[5] = 1;
        d[6] = 0; d[7] = 0; d[8] = 1; d[9] = cx + fr(i * 11) * 0.02f; d[10] = cy + fr(i * 13) * 0.02f; d[11] = fr(t) * 0.5f;
    }
    float *vb = malloc(sizeof(float) * 12 * verts); float *pk = malloc(sizeof(float) * 9 * verts);
    unsigned char *ub = malloc(28 * verts);
    GLuint vbo = 0; size_t vbocap = (size_t)draws * verts * 48;
    if (var >= 3 && var <= 5) { if (!genb) { printf("no VBO\n"); return 1; } genb(1, &vbo); bindb(0x8892, vbo); }
    glEnable(GL_DEPTH_TEST); glEnable(GL_TEXTURE_2D); glDepthFunc(GL_LEQUAL);
    LARGE_INTEGER f, a, b, c, d; QueryPerformanceFrequency(&f); MSG msg;
    double sub = 0, swp = 0, fin = 0;
    for (int fr_ = 0; fr_ < frames + 10; fr_++) {
        while (PeekMessageA(&msg, 0, 0, 0, PM_REMOVE)) DispatchMessageA(&msg);
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
        QueryPerformanceCounter(&a);
        size_t off = 0;
        if (var == 3 || var == 4) bdata(0x8892, (GLsizeiptr_)vbocap, NULL, 0x88E0 /* STREAM_DRAW */);
        for (int k = 0; k < draws; k++) {
            memcpy(vb, src + 12 * (size_t)verts * (k & 7), sizeof(float) * 12 * verts);   /* mugl's batch fill */
            glBindTexture(GL_TEXTURE_2D, tex[k & 7]);
            const char *base = (const char *)vb; int stride = 48, tn = 0, toff = 0, coff = 8, voff = 36, ubc = 0;
            if (var == 2 || var == 4) {   /* pack T2 C4 V3 */
                for (int i = 0; i < verts; i++) { memcpy(pk + 9 * i, vb + 12 * i, 24); memcpy(pk + 9 * i + 6, vb + 12 * i + 9, 12); }
                base = (const char *)pk; stride = 36; voff = 24;
            } else if (var == 6) {
                for (int i = 0; i < verts; i++) { float *s = vb + 12 * i; unsigned char *o = ub + 24 * i; memcpy(o, s, 8);
                    for (int q = 0; q < 4; q++) o[8 + q] = (unsigned char)(s[2 + q] * 255 + 0.5f); memcpy(o + 12, s + 9, 12); }
                base = (const char *)ub; stride = 24; voff = 12; ubc = 1;
            } else tn = var == 0 || var == 3 || var == 5;
            if (var >= 3 && var <= 5) {
                size_t sz = (size_t)stride * verts;
                if (var == 5) { bdata(0x8892, (GLsizeiptr_)sz, base, 0x88E0); base = NULL; }
                else { bsub(0x8892, (GLintptr_)off, (GLsizeiptr_)sz, base); base = (const char *)off; off += sz; }
            }
            glEnableClientState(GL_TEXTURE_COORD_ARRAY); glEnableClientState(GL_COLOR_ARRAY); glEnableClientState(GL_VERTEX_ARRAY);
            if (tn) glEnableClientState(GL_NORMAL_ARRAY); else glDisableClientState(GL_NORMAL_ARRAY);
            glTexCoordPointer(2, GL_FLOAT, stride, base + toff);
            glColorPointer(4, ubc ? GL_UNSIGNED_BYTE : GL_FLOAT, stride, base + coff);
            if (tn) glNormalPointer(GL_FLOAT, stride, base + 24);
            glVertexPointer(3, GL_FLOAT, stride, base + voff);
            glDrawArrays(GL_TRIANGLES, 0, verts);
        }
        QueryPerformanceCounter(&b); SwapBuffers(dc); QueryPerformanceCounter(&c);
        if (fr_ % 10 == 9) glFinish();
        QueryPerformanceCounter(&d);
        if (fr_ >= 10) { sub += (double)(b.QuadPart - a.QuadPart) / f.QuadPart; swp += (double)(c.QuadPart - b.QuadPart) / f.QuadPart; fin += (double)(d.QuadPart - c.QuadPart) / f.QuadPart; }
    }
    printf("variant=%d draws=%d verts=%d submit=%.2fms swap=%.2fms finish(1/10 frames)=%.2fms total=%.2fms/frame\n", var, draws, verts,
           sub * 1000 / frames, swp * 1000 / frames, fin * 1000 / frames, (sub + swp + fin) * 1000 / frames);
    return 0;
}
