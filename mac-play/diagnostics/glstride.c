/* glstride: framebuffer-hash test for mugl's batch submission formats. Renders 150 frames of GL_TRIANGLES
   blocks whose attributes vary so that every batch format is used (T2F_V3F, T2F_C4F_N3F_V3F, C4F_N3F_V3F,
   T2F_N3F_V3F, N3F_V3F, V3F), with texturing, lighting and alpha, and prints an FNV hash of the last frame.
   mugl applies C:\mutools\mugl-hotpatch.txt after frame 100, so the hash reflects that mask.
   Compare: builtin opengl32 (WINEDLLOVERRIDES=opengl32=b) vs the proxy under various masks. */
#include <windows.h>
#include <GL/gl.h>
#include <stdio.h>
static LRESULT CALLBACK wp(HWND h, UINT m, WPARAM w, LPARAM l) { return DefWindowProcA(h, m, w, l); }
static float fr(int i, int k) { unsigned x = (unsigned)(i * 2654435761u + k * 40503u); x ^= x >> 13; x *= 0x5bd1e995u; x ^= x >> 15; return (x & 0xffff) / 65535.0f; }
static void tri(int i, float ox, float oy, float s) { float x = ox + fr(i, 1) * 0.15f, y = oy + fr(i, 2) * 0.15f;
    glVertex3f(x, y, fr(i, 3) - 0.5f); glVertex3f(x + s, y + fr(i, 4) * s, 0); glVertex3f(x + fr(i, 5) * s, y + s, 0.2f); }
static void scene(void)
{
    glClearColor(0.1f, 0.12f, 0.15f, 1); glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
    glEnable(GL_TEXTURE_2D); glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    glColor4f(0.9f, 0.8f, 0.7f, 1);
    for (int b = 0; b < 6; b++) {   /* 1. T2F_V3F: texcoords vary, constant colour (merged blocks) */
        glBegin(GL_TRIANGLES);
        for (int i = 0; i < 30; i++) { int k = b * 30 + i; float x = -1 + (k % 15) * 0.13f, y = 0.55f + (k / 15) * 0.035f;
            glTexCoord2f(fr(k, 6) * 3, fr(k, 7)); glVertex3f(x, y, 0); glTexCoord2f(fr(k, 8), fr(k, 9) * 2); glVertex3f(x + 0.1f, y, 0);
            glTexCoord2f(fr(k, 10), fr(k, 11)); glVertex3f(x + 0.05f, y + 0.09f, 0); }
        glEnd();
    }
    glDisable(GL_BLEND); glEnable(GL_BLEND);   /* state change: ends the batch */
    for (int b = 0; b < 4; b++) {   /* 2. T2F_C4F_N3F_V3F: texcoords and colours (3fv and 4f with alpha) vary */
        glBegin(GL_TRIANGLES);
        for (int i = 0; i < 60; i++) { int k = 1000 + b * 60 + i; float c[3] = {fr(k, 1), fr(k, 2), fr(k, 3)};
            if (k & 1) glColor3fv(c); else glColor4f(c[0], c[1], c[2], 0.5f + fr(k, 4) * 0.5f);
            glTexCoord2f(fr(k, 5), fr(k, 6)); if (i % 3 == 2) glTexCoord2f(fr(k, 7) * 4, fr(k, 8));
            glVertex3f(-1 + fr(k, 9) * 1.8f, -0.2f + fr(k, 10) * 0.6f, 0); }
        glEnd();
    }
    glDisable(GL_TEXTURE_2D);
    for (int b = 0; b < 3; b++) {   /* 3. C4F_N3F_V3F: colours vary, no texcoords */
        glBegin(GL_TRIANGLES);
        for (int i = 0; i < 30; i++) { int k = 2000 + b * 30 + i; glColor4f(fr(k, 1), fr(k, 2), fr(k, 3), 0.7f); tri(k, -1 + (i % 10) * 0.2f, -0.45f + b * 0.06f, 0.06f); }
        glEnd();
    }
    glEnable(GL_LIGHTING); glEnable(GL_LIGHT0); glEnable(GL_COLOR_MATERIAL);
    for (int b = 0; b < 3; b++) {   /* 4. N3F_V3F: normals vary (lit) */
        glBegin(GL_TRIANGLES);
        for (int i = 0; i < 30; i++) { int k = 3000 + b * 30 + i; glNormal3f(fr(k, 1) - 0.5f, fr(k, 2) - 0.5f, 1); tri(k, -1 + (i % 10) * 0.2f, -0.7f + b * 0.06f, 0.06f); }
        glEnd();
    }
    glEnable(GL_TEXTURE_2D);
    for (int b = 0; b < 3; b++) {   /* 5. T2F_N3F_V3F: normals and texcoords vary */
        glBegin(GL_TRIANGLES);
        for (int i = 0; i < 30; i++) { int k = 4000 + b * 30 + i; glNormal3f(fr(k, 1) - 0.5f, 0.3f, 1); glTexCoord2f(fr(k, 2), fr(k, 3)); tri(k, -1 + (i % 10) * 0.2f, -0.95f + b * 0.06f, 0.06f); }
        glEnd();
    }
    glDisable(GL_LIGHTING); glDisable(GL_TEXTURE_2D);
    glColor3f(0.2f, 0.9f, 0.3f);
    glBegin(GL_TRIANGLES); for (int i = 0; i < 40; i++) tri(5000 + i, 0.2f + (i % 8) * 0.1f, 0.1f + (i / 8) * 0.05f, 0.04f); glEnd();   /* 6. V3F */
    glBegin(GL_TRIANGLES); for (int i = 0; i < 40; i++) tri(5100 + i, 0.2f + (i % 8) * 0.1f, 0.35f + (i / 8) * 0.03f, 0.04f); glEnd();
}
int main(void)
{
    WNDCLASSA wc = {0}; wc.lpfnWndProc = wp; wc.hInstance = GetModuleHandleA(0); wc.lpszClassName = "gls"; RegisterClassA(&wc);
    HWND w = CreateWindowA("gls", "glstride", WS_OVERLAPPEDWINDOW | WS_VISIBLE, 0, 0, 512, 512, 0, 0, wc.hInstance, 0);
    HDC dc = GetDC(w);
    PIXELFORMATDESCRIPTOR pfd = { sizeof(pfd), 1, PFD_DRAW_TO_WINDOW | PFD_SUPPORT_OPENGL | PFD_DOUBLEBUFFER, PFD_TYPE_RGBA, 32 };
    pfd.cDepthBits = 24; SetPixelFormat(dc, ChoosePixelFormat(dc, &pfd), &pfd);
    HGLRC rc = wglCreateContext(dc); wglMakeCurrent(dc, rc);
    static unsigned char tex[64 * 64 * 4];
    for (int i = 0; i < 64 * 64; i++) { tex[i * 4] = (unsigned char)(i * 7); tex[i * 4 + 1] = (unsigned char)((i / 64) * 4); tex[i * 4 + 2] = (unsigned char)(((i % 64) ^ (i / 64)) * 4); tex[i * 4 + 3] = 255; }
    GLuint t; glGenTextures(1, &t); glBindTexture(GL_TEXTURE_2D, t);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR); glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, 64, 64, 0, GL_RGBA, GL_UNSIGNED_BYTE, tex);
    for (int f = 0; f < 150; f++) {
        MSG msg; while (PeekMessageA(&msg, 0, 0, 0, PM_REMOVE)) DispatchMessageA(&msg);
        scene();
        if (f == 149) {
            static unsigned char px[512 * 512 * 4]; unsigned h = 2166136261u;
            glReadPixels(0, 0, 512, 512, GL_RGBA, GL_UNSIGNED_BYTE, px);
            for (int k = 0; k < (int)sizeof px; k++) h = (h ^ px[k]) * 16777619u;
            printf("glstride fbhash=%08x err=%04x\n", h, glGetError()); fflush(stdout);
        }
        SwapBuffers(dc);
        Sleep(15);
    }
    return 0;
}
