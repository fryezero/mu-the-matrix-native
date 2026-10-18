/* glcaps: framebuffer-hash test for mugl's deferred enables and redundant texture-parameter filter (hotpatch bit
   1073741824, v7.6). Each frame toggles caps back and forth with and without geometry in between (immediate blocks
   that mugl batches, client glDrawArrays, glClear under a toggled scissor test), observes them (glIsEnabled,
   glGetBooleanv, glPushAttrib/glPopAttrib of the enable bit, a display list compiled with enables inside), and sets
   texture filters and wraps repeatedly on two texture objects, around a glPushAttrib/glPopAttrib of the texture bit
   and a glTexParameterf, and pushes and pops matrices around nothing, geometry, queries, mode switches, state calls and
   glDrawElements/glDrawRangeElements and extension calls, with repeated and changed viewports (these cases caught a
   since-removed matrix-call queue that did not flush before element and extension draws). Prints an FNV hash of the last of 400 frames and a checksum of every query answer. mugl
   applies the mask after frame 100; in a test program MUGL_MASK (environment) overrides C:\mutools\mugl-hotpatch.txt.
   Compare the builtin opengl32 (WINEDLLOVERRIDES=opengl32=b) with the proxy (opengl32=n,b next to the exe) at masks
   with and without 1073741824. */
#include <windows.h>
#include <GL/gl.h>
#include <stdio.h>
static LRESULT CALLBACK wp(HWND h, UINT m, WPARAM w, LPARAM l) { return DefWindowProcA(h, m, w, l); }
static float fr(int i, int k) { unsigned x = (unsigned)(i * 2654435761u + k * 40503u); x ^= x >> 13; x *= 0x5bd1e995u; x ^= x >> 15; return (x & 0xffff) / 65535.0f; }
static unsigned qsum = 2166136261u;
static void q(unsigned v) { qsum = (qsum ^ v) * 16777619u; }
static GLuint texa, texb, list;
static void (WINAPI *p_mtc)(GLenum, const GLfloat *); static void (WINAPI *p_dre)(GLenum, GLuint, GLuint, GLsizei, GLenum, const void *);
static float arr[4][9];
static void tri(int i, int ccw, float z)
{
    float x = fr(i, 1) * 1.6f - 0.8f, y = fr(i, 2) * 1.6f - 0.8f, s = 0.06f + fr(i, 3) * 0.08f;
    glBegin(GL_TRIANGLES);
    glColor4f(fr(i, 4), fr(i, 5), fr(i, 6), 0.3f + fr(i, 7) * 0.7f);
    glTexCoord2f(0, 0); glVertex3f(x, y, z);
    if (ccw) { glTexCoord2f(1, 0); glVertex3f(x + s, y, z); glTexCoord2f(0, 1); glVertex3f(x, y + s, z); }
    else { glTexCoord2f(0, 1); glVertex3f(x, y + s, z); glTexCoord2f(1, 0); glVertex3f(x + s, y, z); }
    glEnd();
}
static void params(GLuint t, GLint minf, GLint magf, GLint wrap)
{
    glBindTexture(GL_TEXTURE_2D, t);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, minf); glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, magf);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, wrap); glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, wrap);
}
static void scene(int f)
{
    glClearColor(0.1f, 0.12f, 0.15f, 1); glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
    glEnable(GL_TEXTURE_2D); glEnable(GL_DEPTH_TEST); glDepthFunc(GL_LEQUAL);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA); glAlphaFunc(GL_GREATER, 0.5f);
    for (int i = 0; i < 60; i++) {
        int k = (i + f) % 9;
        /* 1. cancelled toggles, then geometry */
        glDisable(GL_CULL_FACE); glEnable(GL_CULL_FACE); if (k & 1) glDisable(GL_CULL_FACE);
        glEnable(GL_BLEND); glDisable(GL_BLEND); if (k & 2) glEnable(GL_BLEND);
        if (k == 4) { glEnable(GL_ALPHA_TEST); glBindTexture(GL_TEXTURE_2D, texb); glDisable(GL_ALPHA_TEST); }
        params((i & 1) ? texa : texb, (i & 1) ? GL_NEAREST : GL_LINEAR, GL_NEAREST, (k & 4) ? GL_CLAMP : GL_REPEAT);
        tri(i, i & 1, -0.1f * (i % 5));
        tri(i + 100, !(i & 1), 0.05f);
        /* 2. queries after deferred changes */
        if (k == 3) { glEnable(GL_ALPHA_TEST); q(glIsEnabled(GL_ALPHA_TEST)); glDisable(GL_ALPHA_TEST); q(glIsEnabled(GL_ALPHA_TEST)); }
        if (k == 5) { GLboolean b; glDisable(GL_BLEND); glGetBooleanv(GL_BLEND, &b); q(b); glEnable(GL_BLEND); glGetBooleanv(GL_BLEND, &b); q(b); }
        /* 3. enable-bit push/pop around deferred changes */
        if (k == 6) {
            glEnable(GL_CULL_FACE);
            glPushAttrib(GL_ENABLE_BIT); glDisable(GL_CULL_FACE); glEnable(GL_ALPHA_TEST); tri(i + 200, 0, 0.1f); glEnable(GL_CULL_FACE); glPopAttrib();
            q(glIsEnabled(GL_CULL_FACE)); q(glIsEnabled(GL_ALPHA_TEST)); tri(i + 300, 0, 0.12f);
        }
        /* 4. scissored clear under a toggled scissor test */
        if (k == 7) {
            glScissor(16 + i * 3, 16 + i * 2, 40, 30); glEnable(GL_SCISSOR_TEST); glDisable(GL_SCISSOR_TEST); glEnable(GL_SCISSOR_TEST);
            glClearColor(fr(i, 9), 0.2f, 0.5f, 1); glClear(GL_COLOR_BUFFER_BIT); glDisable(GL_SCISSOR_TEST);
        }
        /* 5. client array draw after deferred enables */
        if (k == 8) {
            glDisable(GL_BLEND); glEnable(GL_BLEND); glDisable(GL_CULL_FACE);
            for (int v = 0; v < 4; v++) { arr[v][0] = (v == 1 || v == 2); arr[v][1] = v >= 2; arr[v][2] = fr(i, 10); arr[v][3] = 0.6f; arr[v][4] = 0.3f; arr[v][5] = 0.7f;
                                          arr[v][6] = fr(i, 11) * 1.5f - 0.8f + ((v == 1 || v == 2) ? 0.1f : 0); arr[v][7] = fr(i, 12) * 1.5f - 0.8f + (v >= 2 ? 0.1f : 0); arr[v][8] = 0; }
            glEnableClientState(GL_VERTEX_ARRAY); glEnableClientState(GL_COLOR_ARRAY); glEnableClientState(GL_TEXTURE_COORD_ARRAY);
            glTexCoordPointer(2, GL_FLOAT, 36, arr[0]); glColorPointer(4, GL_FLOAT, 36, arr[0] + 2); glVertexPointer(3, GL_FLOAT, 36, arr[0] + 6);
            glDrawArrays(GL_QUADS, 0, 4);
            glDisableClientState(GL_VERTEX_ARRAY); glDisableClientState(GL_COLOR_ARRAY); glDisableClientState(GL_TEXTURE_COORD_ARRAY);
        }
    }
    /* 6. texture-bit push/pop: a value repeated after the pop must reach GL */
    params(texa, GL_LINEAR, GL_LINEAR, GL_REPEAT);
    glPushAttrib(GL_TEXTURE_BIT); glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST); glPopAttrib();
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST); tri(500, 1, 0.2f);
    /* 7. glTexParameterf changes a value behind glTexParameteri */
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR); glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, (GLfloat)GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR); tri(501, 1, 0.2f);
    /* 9. matrix spans: empty, with geometry, nested, queried, across a mode switch; viewport repeats and changes */
    for (int i = 0; i < 24; i++) {
        float m[16] = {1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, fr(i, 30) * 0.4f - 0.2f, fr(i, 31) * 0.4f - 0.2f, 0, 1}; GLfloat g[16];
        glViewport(0, 0, 512, 512);
        glPushMatrix(); glMultMatrixf(m); glRotatef(fr(i, 32) * 90, 0, 0, 1); glPopMatrix();                 /* empty */
        glPushMatrix(); glTranslatef(0.1f, 0, 0); glPushMatrix(); glLoadIdentity(); glScalef(0.5f, 0.5f, 1); glPopMatrix();
        if (i & 1) tri(600 + i, 1, 0.3f);                                                                      /* geometry in the outer span */
        glPopMatrix();
        glPushMatrix(); glMultMatrixf(m); glGetFloatv(GL_MODELVIEW_MATRIX, g); q(*(unsigned *)&g[12]); glPopMatrix();
        glPushMatrix(); glOrtho(-1, 1, -1, 1, -1, 1); glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity(); glPopMatrix();
        glMatrixMode(GL_MODELVIEW); tri(700 + i, 0, 0.35f); glPopMatrix();
        glPushMatrix(); glMultMatrixf(m); glEnable(GL_BLEND); glBindTexture(GL_TEXTURE_2D, texa); glDisable(GL_BLEND); glPopMatrix();   /* state calls only */
        if (i % 6 == 2) { glViewport(64, 64, 256, 256); tri(800 + i, 1, 0.4f); glViewport(0, 0, 512, 512); }
        if (i % 6 == 4) { glPushAttrib(GL_VIEWPORT_BIT); glViewport(32, 32, 128, 128); glPopAttrib(); glViewport(32, 32, 128, 128); tri(900 + i, 1, 0.4f); glViewport(0, 0, 512, 512); }
        if (i % 8 == 5) { GLint d; glPushMatrix(); glGetIntegerv(GL_MODELVIEW_STACK_DEPTH, &d); q((unsigned)d); glPopMatrix(); glRasterPos2f(-0.5f, -0.5f); }
        /* 10. array draws and extension calls inside spans, after deferred enables (the interface renderer's pattern) */
        {
            static const GLushort ix[6] = {0, 1, 2, 0, 2, 3};
            for (int v = 0; v < 4; v++) { arr[v][0] = (v == 1 || v == 2); arr[v][1] = v >= 2; arr[v][2] = fr(i, 40); arr[v][3] = 0.5f; arr[v][4] = 0.8f; arr[v][5] = 0.9f;
                                          arr[v][6] = ((v == 1 || v == 2) ? 0.3f : 0); arr[v][7] = (v >= 2 ? 0.3f : 0); arr[v][8] = 0; }
            glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity(); glOrtho(-1, 1, -1, 1, -1, 1);
            glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity(); glMultMatrixf(m); glScalef(0.5f + fr(i, 41), 0.5f + fr(i, 42), 1);
            glDisable(GL_CULL_FACE); glEnable(GL_BLEND); if (p_mtc) p_mtc(0x84C0, arr[0]);
            glEnableClientState(GL_VERTEX_ARRAY); glEnableClientState(GL_COLOR_ARRAY);
            glColorPointer(4, GL_FLOAT, 36, arr[0] + 2); glVertexPointer(3, GL_FLOAT, 36, arr[0] + 6);
            if (i & 1) glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_SHORT, ix); else if (p_dre) p_dre(GL_TRIANGLES, 0, 3, 6, GL_UNSIGNED_SHORT, ix);
            glDisableClientState(GL_VERTEX_ARRAY); glDisableClientState(GL_COLOR_ARRAY);
            glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW); glDisable(GL_BLEND);
        }
    }
    /* 8. display list with enables compiled inside */
    glCallList(list); tri(502, 0, 0.25f);
    glDisable(GL_CULL_FACE); glDisable(GL_BLEND); glDisable(GL_ALPHA_TEST);
}
int main(void)
{
    WNDCLASSA wc = {0}; wc.lpfnWndProc = wp; wc.hInstance = GetModuleHandleA(0); wc.lpszClassName = "glcaps"; RegisterClassA(&wc);
    HWND w = CreateWindowA("glcaps", "glcaps", WS_OVERLAPPEDWINDOW | WS_VISIBLE, 0, 0, 512, 512, 0, 0, wc.hInstance, 0);
    HDC dc = GetDC(w);
    PIXELFORMATDESCRIPTOR pfd = { sizeof(pfd), 1, PFD_DRAW_TO_WINDOW | PFD_SUPPORT_OPENGL | PFD_DOUBLEBUFFER, PFD_TYPE_RGBA, 32 };
    pfd.cDepthBits = 24; SetPixelFormat(dc, ChoosePixelFormat(dc, &pfd), &pfd);
    HGLRC rc = wglCreateContext(dc); wglMakeCurrent(dc, rc);
    p_mtc = (void *)wglGetProcAddress("glMultiTexCoord4fvARB"); p_dre = (void *)wglGetProcAddress("glDrawRangeElementsEXT");
    if (!p_dre) p_dre = (void *)wglGetProcAddress("glDrawRangeElements");
    static unsigned char tex[64 * 64 * 4];
    for (int i = 0; i < 64 * 64; i++) { tex[i * 4] = (unsigned char)(i * 7); tex[i * 4 + 1] = (unsigned char)((i / 64) * 4); tex[i * 4 + 2] = (unsigned char)(((i % 64) ^ (i / 64)) * 4); tex[i * 4 + 3] = (unsigned char)(i & 255); }
    glGenTextures(1, &texa); glBindTexture(GL_TEXTURE_2D, texa); glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, 64, 64, 0, GL_RGBA, GL_UNSIGNED_BYTE, tex);
    for (int i = 0; i < 64 * 64 * 4; i++) tex[i] = (unsigned char)(255 - tex[i]);
    glGenTextures(1, &texb); glBindTexture(GL_TEXTURE_2D, texb); glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, 64, 64, 0, GL_RGBA, GL_UNSIGNED_BYTE, tex);
    list = glGenLists(1);
    glNewList(list, GL_COMPILE); glEnable(GL_BLEND); glDisable(GL_CULL_FACE); glEnable(GL_CULL_FACE); glDisable(GL_BLEND); glEnable(GL_ALPHA_TEST); glEndList();
    for (int f = 0; f < 400; f++) {
        MSG msg; while (PeekMessageA(&msg, 0, 0, 0, PM_REMOVE)) DispatchMessageA(&msg);
        scene(f % 4);
        if (f == 399) {
            static unsigned char px[512 * 512 * 4]; unsigned h = 2166136261u;
            glReadPixels(0, 0, 512, 512, GL_RGBA, GL_UNSIGNED_BYTE, px);
            for (int k = 0; k < (int)sizeof px; k++) h = (h ^ px[k]) * 16777619u;
            char mod[MAX_PATH] = "?"; GetModuleFileNameA(GetModuleHandleA("opengl32.dll"), mod, sizeof mod);
            printf("glcaps fbhash=%08x queries=%08x err=%04x opengl32=%s\n", h, qsum, glGetError(), mod); fflush(stdout);
        }
        SwapBuffers(dc);
        Sleep(5);
    }
    return 0;
}
