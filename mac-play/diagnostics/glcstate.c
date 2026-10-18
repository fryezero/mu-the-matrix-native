/* glcstate: framebuffer-hash test for mugl's deferred client-array enables (hotpatch bit 262144) and off-screen batch
   culling (bit 524288, v7.4). Part 10 draws immediate-mode triangle batches under a perspective projection, placed
   inside, across the edges, fully outside each side and behind the eye, with matrix calls of every kind between.
   Each frame mixes the client's effect pattern (glEnableClientState x3, glDrawArrays, glDisableClientState x3 with
   matrix and state calls between draws) with cases that observe or reset array state: a disabled color array falling
   back to the current color, glArrayElement inside glBegin/glEnd, client attribute push/pop, glInterleavedArrays,
   a second client texture unit, glDrawElements, a VBO-sourced draw, and glIsEnabled/glGetIntegerv answers that steer
   later colors. Prints an FNV hash of the last of 150 frames. mugl applies C:\mutools\mugl-hotpatch.txt after
   frame 100. Compare the builtin opengl32 (WINEDLLOVERRIDES=opengl32=b) with the proxy at masks with and without
   262144. Run it in a test bottle without MUGL_STATS: the private stats code reads client addresses. */
#include <windows.h>
#include <GL/gl.h>
#include <stdio.h>
static LRESULT CALLBACK wp(HWND h, UINT m, WPARAM w, LPARAM l) { return DefWindowProcA(h, m, w, l); }
static float fr(int i, int k) { unsigned x = (unsigned)(i * 2654435761u + k * 40503u); x ^= x >> 13; x *= 0x5bd1e995u; x ^= x >> 15; return (x & 0xffff) / 65535.0f; }
typedef ptrdiff_t GLsizeiptr_;
static void (WINAPI *p_genb)(GLsizei, GLuint *), (WINAPI *p_bindb)(GLenum, GLuint), (WINAPI *p_bdata)(GLenum, GLsizeiptr_, const void *, GLenum);
static void (WINAPI *p_cat)(GLenum), (WINAPI *p_at)(GLenum);
static float quads[64][4][9];   /* t2 c4 v3 */
static GLuint vbo;
static void effect_quad(int i)
{
    float m[16] = {1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, fr(i, 20) * 0.2f - 0.1f, fr(i, 21) * 0.2f - 0.1f, 0, 1};
    glPushMatrix(); glMultMatrixf(m);
    if (i & 1) glBlendFunc(GL_ONE, GL_ONE); else glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    glEnableClientState(GL_VERTEX_ARRAY); glEnableClientState(GL_COLOR_ARRAY); glEnableClientState(GL_TEXTURE_COORD_ARRAY);
    glTexCoordPointer(2, GL_FLOAT, 36, quads[i & 63][0]); glColorPointer(4, GL_FLOAT, 36, quads[i & 63][0] + 2); glVertexPointer(3, GL_FLOAT, 36, quads[i & 63][0] + 6);
    glDrawArrays(GL_QUADS, 0, 4);
    glDisableClientState(GL_VERTEX_ARRAY); glDisableClientState(GL_COLOR_ARRAY); glDisableClientState(GL_TEXTURE_COORD_ARRAY);
    glPopMatrix();
}
static void scene(int f)
{
    glClearColor(0.1f, 0.12f, 0.15f, 1); glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
    glEnable(GL_TEXTURE_2D); glEnable(GL_BLEND); glBindTexture(GL_TEXTURE_2D, 1);
    for (int i = 0; i < 40; i++) {   /* 1. effect pattern, immediate blocks in between */
        effect_quad(i + f);
        if (i % 7 == 3) { glBegin(GL_TRIANGLES); glColor4f(fr(i, 1), 0.5f, 0.3f, 0.8f); glTexCoord2f(0, 0); glVertex2f(-0.9f + i * 0.04f, -0.9f);
                          glTexCoord2f(1, 0); glVertex2f(-0.85f + i * 0.04f, -0.9f); glTexCoord2f(0, 1); glVertex2f(-0.87f + i * 0.04f, -0.8f); glEnd(); }
    }
    /* 2. color array off: the current color applies */
    glColor4f(0.2f, 0.8f, 0.4f, 1);
    glEnableClientState(GL_VERTEX_ARRAY); glEnableClientState(GL_COLOR_ARRAY); glDisableClientState(GL_COLOR_ARRAY);
    glVertexPointer(3, GL_FLOAT, 36, quads[3][0] + 6); glDrawArrays(GL_QUADS, 0, 4);
    glDisableClientState(GL_VERTEX_ARRAY);
    /* 3. glArrayElement inside a block after deferred enables */
    glEnableClientState(GL_VERTEX_ARRAY); glEnableClientState(GL_COLOR_ARRAY);
    glVertexPointer(3, GL_FLOAT, 36, quads[5][0] + 6); glColorPointer(4, GL_FLOAT, 36, quads[5][0] + 2);
    glBegin(GL_QUADS); for (int k = 0; k < 4; k++) glArrayElement(k); glEnd();
    glDisableClientState(GL_COLOR_ARRAY); glDisableClientState(GL_VERTEX_ARRAY);
    /* 4. push / change / pop, then draw what the pop restored (vertex on, color off) */
    glEnableClientState(GL_VERTEX_ARRAY);
    glPushClientAttrib(GL_CLIENT_VERTEX_ARRAY_BIT);
    glEnableClientState(GL_COLOR_ARRAY); glDisableClientState(GL_VERTEX_ARRAY);
    glPopClientAttrib();
    glColor4f(0.9f, 0.1f, 0.6f, 1); glVertexPointer(3, GL_FLOAT, 36, quads[7][0] + 6); glDrawArrays(GL_QUADS, 0, 4);
    glDisableClientState(GL_VERTEX_ARRAY);
    /* 5. interleaved arrays set the enables; then drop the color array */
    glInterleavedArrays(GL_T2F_C4F_N3F_V3F, 0, NULL);   /* pointers replaced below */
    glDisableClientState(GL_NORMAL_ARRAY);
    glTexCoordPointer(2, GL_FLOAT, 36, quads[9][0]); glColorPointer(4, GL_FLOAT, 36, quads[9][0] + 2); glVertexPointer(3, GL_FLOAT, 36, quads[9][0] + 6);
    glDisableClientState(GL_COLOR_ARRAY); glColor4f(0.3f, 0.3f, 0.9f, 1);
    glDrawArrays(GL_QUADS, 0, 4);
    glDisableClientState(GL_TEXTURE_COORD_ARRAY); glDisableClientState(GL_VERTEX_ARRAY);
    /* 6. second client unit: enable its texcoords, switch back, toggle unit 0 */
    if (p_cat && p_at) {
        p_cat(0x84C1); glEnableClientState(GL_TEXTURE_COORD_ARRAY); glTexCoordPointer(2, GL_FLOAT, 36, quads[11][0]);
        p_cat(0x84C0); glEnableClientState(GL_TEXTURE_COORD_ARRAY); glDisableClientState(GL_TEXTURE_COORD_ARRAY);
        glEnableClientState(GL_VERTEX_ARRAY); glVertexPointer(3, GL_FLOAT, 36, quads[11][0] + 6); glDrawArrays(GL_QUADS, 0, 4);
        p_cat(0x84C1); glDisableClientState(GL_TEXTURE_COORD_ARRAY); p_cat(0x84C0); glDisableClientState(GL_VERTEX_ARRAY);
    }
    /* 7. glDrawElements */
    static const GLushort idx[6] = {0, 1, 2, 0, 2, 3};
    glEnableClientState(GL_VERTEX_ARRAY); glEnableClientState(GL_COLOR_ARRAY); glDisableClientState(GL_COLOR_ARRAY); glEnableClientState(GL_COLOR_ARRAY);
    glVertexPointer(3, GL_FLOAT, 36, quads[13][0] + 6); glColorPointer(4, GL_FLOAT, 36, quads[13][0] + 2);
    glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_SHORT, idx);
    glDisableClientState(GL_COLOR_ARRAY); glDisableClientState(GL_VERTEX_ARRAY);
    /* 8. VBO-sourced draw */
    if (vbo) {
        p_bindb(0x8892, vbo);
        glEnableClientState(GL_VERTEX_ARRAY); glEnableClientState(GL_COLOR_ARRAY);
        glColorPointer(4, GL_FLOAT, 36, (const void *)(15 * 144 + 8)); glVertexPointer(3, GL_FLOAT, 36, (const void *)(15 * 144 + 24));
        glDrawArrays(GL_QUADS, 0, 4);
        glDisableClientState(GL_VERTEX_ARRAY); glDisableClientState(GL_COLOR_ARRAY);
        p_bindb(0x8892, 0);
    }
    /* 9. queries steer colors: a deferred enable must be visible to them */
    glDisableClientState(GL_COLOR_ARRAY); glEnableClientState(GL_NORMAL_ARRAY);
    GLboolean on = glIsEnabled(GL_NORMAL_ARRAY); GLint vi = 0; glGetIntegerv(GL_COLOR_ARRAY, &vi);
    glDisableClientState(GL_NORMAL_ARRAY);
    glDisable(GL_TEXTURE_2D); glColor4f(on ? 1.0f : 0.0f, vi ? 1.0f : 0.0f, 0.5f, 1);
    glBegin(GL_TRIANGLES); glVertex2f(0.6f, 0.6f); glVertex2f(0.9f, 0.6f); glVertex2f(0.75f, 0.9f); glEnd();
    /* 10. perspective batches in and out of view */
    glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity(); glFrustum(-0.1, 0.1, -0.1, 0.1, 0.1, 100.0);
    glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity(); glTranslatef(0, 0, -5); glRotatef((float)f * 7.0f, 0, 1, 0);
    glEnable(GL_DEPTH_TEST); glDisable(GL_BLEND); glEnable(GL_TEXTURE_2D);
    for (int i = 0; i < 48; i++) {
        float cx = (fr(i, 30) - 0.5f) * 30.0f, cy = (fr(i, 31) - 0.5f) * 30.0f, cz = (fr(i, 32) - 0.5f) * 14.0f, sz = 0.3f + fr(i, 33) * 2.5f;
        if (i % 5 == 0) { glPushMatrix(); glScalef(1.0f, 1.0f + fr(i, 34), 1.0f); }
        if (i % 7 == 0) { static float m[16] = {1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 9.0f, 0, 0, 1}; glMultMatrixf(m); }   /* large: a stale matrix culls wrongly */
        if (i % 11 == 5) glRotatef(90.0f, 0, 1, 0);
        glBindTexture(GL_TEXTURE_2D, (i & 1) ? 0 : 1);
        glBegin(GL_TRIANGLES);
        for (int k = 0; k < 12; k++) {
            glColor3f(fr(i * 12 + k, 35), fr(i * 12 + k, 36), fr(i * 12 + k, 37)); glTexCoord2f(fr(i * 12 + k, 38), fr(i * 12 + k, 39));
            glVertex3f(cx + (fr(i * 12 + k, 40) - 0.5f) * sz, cy + (fr(i * 12 + k, 41) - 0.5f) * sz, cz + (fr(i * 12 + k, 42) - 0.5f) * sz);
        }
        glEnd();
        if (i % 5 == 0) glPopMatrix();
    }
    glDisable(GL_DEPTH_TEST);
    glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW); glPopMatrix();
}
int main(void)
{
    WNDCLASSA wc = {0}; wc.lpfnWndProc = wp; wc.hInstance = GetModuleHandleA(0); wc.lpszClassName = "glc"; RegisterClassA(&wc);
    HWND w = CreateWindowA("glc", "glcstate", WS_OVERLAPPEDWINDOW | WS_VISIBLE, 0, 0, 512, 512, 0, 0, wc.hInstance, 0);
    HDC dc = GetDC(w);
    PIXELFORMATDESCRIPTOR pfd = { sizeof(pfd), 1, PFD_DRAW_TO_WINDOW | PFD_SUPPORT_OPENGL | PFD_DOUBLEBUFFER, PFD_TYPE_RGBA, 32 };
    pfd.cDepthBits = 24; SetPixelFormat(dc, ChoosePixelFormat(dc, &pfd), &pfd);
    HGLRC rc = wglCreateContext(dc); wglMakeCurrent(dc, rc);
    p_genb = (void *)wglGetProcAddress("glGenBuffersARB"); p_bindb = (void *)wglGetProcAddress("glBindBufferARB");
    p_bdata = (void *)wglGetProcAddress("glBufferDataARB"); p_cat = (void *)wglGetProcAddress("glClientActiveTextureARB");
    p_at = (void *)wglGetProcAddress("glActiveTextureARB");
    for (int q = 0; q < 64; q++) for (int k = 0; k < 4; k++) {
        float *d = quads[q][k]; float cx = fr(q, 1) * 1.6f - 0.8f, cy = fr(q, 2) * 1.6f - 0.8f, s = 0.05f + fr(q, 3) * 0.1f;
        d[0] = (k == 1 || k == 2); d[1] = (k >= 2); d[2] = fr(q, 4); d[3] = fr(q, 5); d[4] = fr(q, 6); d[5] = 0.4f + fr(q, 7) * 0.6f;
        d[6] = cx + ((k == 1 || k == 2) ? s : 0); d[7] = cy + (k >= 2 ? s : 0); d[8] = 0;
    }
    if (p_genb && p_bindb && p_bdata) { p_genb(1, &vbo); p_bindb(0x8892, vbo); p_bdata(0x8892, sizeof quads, quads, 0x88E4); p_bindb(0x8892, 0); }
    static unsigned char tex[64 * 64 * 4];
    for (int i = 0; i < 64 * 64; i++) { tex[i * 4] = (unsigned char)(i * 7); tex[i * 4 + 1] = (unsigned char)((i / 64) * 4); tex[i * 4 + 2] = (unsigned char)(((i % 64) ^ (i / 64)) * 4); tex[i * 4 + 3] = (unsigned char)(128 + (i & 127)); }
    GLuint t; glGenTextures(1, &t); glBindTexture(GL_TEXTURE_2D, t);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST); glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, 64, 64, 0, GL_RGBA, GL_UNSIGNED_BYTE, tex);
    for (int f = 0; f < 150; f++) {
        MSG msg; while (PeekMessageA(&msg, 0, 0, 0, PM_REMOVE)) DispatchMessageA(&msg);
        scene(f % 3);
        if (f == 149) {
            static unsigned char px[512 * 512 * 4]; unsigned h = 2166136261u;
            glReadPixels(0, 0, 512, 512, GL_RGBA, GL_UNSIGNED_BYTE, px);
            for (int k = 0; k < (int)sizeof px; k++) h = (h ^ px[k]) * 16777619u;
            printf("glcstate fbhash=%08x err=%04x\n", h, glGetError()); fflush(stdout);
        }
        SwapBuffers(dc);
        Sleep(10);
    }
    return 0;
}
