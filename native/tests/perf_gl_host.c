/* Test host for the NATIVE-PERF-001 GL paths (synthetic streams, no client data).
 *
 *   perf-gl-host ui W H      the same 2D call stream through core/mu_ui_raster.c (software) and
 *                            viewer/ui_gl.c (GPU) over the same background; prints
 *                            {"pixels", "differing", "max_delta", "above2", "uploads", "primitives"}
 *   perf-gl-host batch W H   a terrain-like stream (fans and quads, texture and blend changes, an
 *                            incomplete quad, glColor3 after glColor4) and a mesh-like stream (GL_TRIANGLES)
 *                            drawn immediately and through viewer/gl_batch.c; prints
 *                            {"identical", "differing", "primitives", "draws", "state_calls", "state_applied"}
 *
 * Offscreen GL (viewer/gl_headless.c); exits 3 when no context is available. */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef __APPLE__
#include <OpenGL/gl.h>
#else
#include <GL/gl.h>
#endif

#include "../core/mu_ui_raster.h"
#include "../viewer/gl_batch.h"
#include "../viewer/gl_headless.h"
#include "../viewer/ui_gl.h"

#define W_GL_PROJECTION 0x1701u
#define W_GL_MODELVIEW 0x1700u

static int32_t W, H;

static uint32_t fw(float f)
{
    uint32_t w;
    memcpy(&w, &f, 4);
    return w;
}

static void call(mu_ui_sink *s, int op, const uint32_t *w, int n) { s->call(s->user, op, w, n, NULL, 0); }
static void call1(mu_ui_sink *s, int op, uint32_t a) { call(s, op, &a, 1); }
static void call2(mu_ui_sink *s, int op, uint32_t a, uint32_t b)
{
    uint32_t w[2] = {a, b};
    call(s, op, w, 2);
}

static void ortho(mu_ui_sink *s, double l, double r, double b, double t)
{
    uint32_t w[8];
    double d[4] = {l, r, b, t};
    memcpy(w, d, sizeof d);
    call(s, MU_GLU_ORTHO2D, w, 8);
}

static void color4(mu_ui_sink *s, float r, float g, float b, float a)
{
    uint32_t w[4] = {fw(r), fw(g), fw(b), fw(a)};
    call(s, MU_GL_COLOR4F, w, 4);
}

static void tex(mu_ui_sink *s, float u, float v) { call2(s, MU_GL_TEXCOORD2F, fw(u), fw(v)); }
static void vtx(mu_ui_sink *s, float x, float y) { call2(s, MU_GL_VERTEX2F, fw(x), fw(y)); }

static void quad(mu_ui_sink *s, float x, float y, float w, float h)
{
    call1(s, MU_GL_BEGIN, 7);
    tex(s, 0, 0); vtx(s, x, y);
    tex(s, 1, 0); vtx(s, x + w, y);
    tex(s, 1, 1); vtx(s, x + w, y + h);
    tex(s, 0, 1); vtx(s, x, y + h);
    call(s, MU_GL_END, NULL, 0);
}

static void texture(mu_ui_sink *s, uint32_t name, int32_t tw, int32_t th, int rgb, uint32_t filter)
{
    size_t c = rgb ? 3 : 4;
    uint8_t *p = malloc((size_t)tw * (size_t)th * c);
    for (int32_t y = 0; y < th; ++y)
        for (int32_t x = 0; x < tw; ++x) {
            uint8_t *q = p + ((size_t)y * (size_t)tw + (size_t)x) * c;
            q[0] = (uint8_t)(x * 255 / (tw - 1));
            q[1] = (uint8_t)(y * 255 / (th - 1));
            q[2] = (uint8_t)(((x / 4 + y / 4) & 1) ? 220 : 40);
            if (!rgb)
                q[3] = (uint8_t)((x + y) * 255 / (tw + th - 2));
        }
    call2(s, MU_GL_BINDTEXTURE, 0x0de1, name);
    uint32_t w[9] = {0x0de1, 0, rgb ? 3u : 4u, (uint32_t)tw, (uint32_t)th, 0, rgb ? 0x1907u : 0x1908u, 0x1401, 0};
    s->call(s->user, MU_GL_TEXIMAGE2D, w, 9, p, (size_t)tw * (size_t)th * c);
    uint32_t pm[3] = {0x0de1, 0x2801, filter}, pg[3] = {0x0de1, 0x2800, filter};
    call(s, MU_GL_TEXPARAMETERI, pm, 3);
    call(s, MU_GL_TEXPARAMETERI, pg, 3);
    free(p);
}

/* A 2D frame like the client's: textured quads (nearest and linear, RGB and RGBA), blend modes,
 * colour-only quads, a fan, the alpha test, a back-facing quad under culling, a texture re-upload
 * between draws (the font texture pattern). Coordinates on whole pixels. */
static void ui_stream(mu_ui_sink *s)
{
    uint32_t vp[4] = {0, 0, (uint32_t)W, (uint32_t)H};
    call1(s, MU_GL_MATRIXMODE, W_GL_PROJECTION);
    call(s, MU_GL_PUSHMATRIX, NULL, 0);
    call(s, MU_GL_LOADIDENTITY, NULL, 0);
    call(s, MU_GL_VIEWPORT, vp, 4);
    ortho(s, 0, W, 0, H);
    call1(s, MU_GL_MATRIXMODE, W_GL_MODELVIEW);
    call(s, MU_GL_PUSHMATRIX, NULL, 0);
    call(s, MU_GL_LOADIDENTITY, NULL, 0);
    call1(s, MU_GL_DISABLE, 0x0b44);   /* cull off */
    texture(s, 11, 16, 16, 0, 0x2600);
    texture(s, 12, 32, 8, 1, 0x2600);
    call1(s, MU_GL_ENABLE, 0x0de1);
    call2(s, MU_GL_BINDTEXTURE, 0x0de1, 11);
    color4(s, 1, 1, 1, 1);
    quad(s, 8, 8, 64, 64);                          /* nearest, 4x magnified, opaque */
    call1(s, MU_GL_ENABLE, 0x0be2);
    call2(s, MU_GL_BLENDFUNC, 0x302, 0x303);        /* SRC_ALPHA, ONE_MINUS_SRC_ALPHA */
    quad(s, 40, 40, 64, 64);
    call2(s, MU_GL_BLENDFUNC, 1, 1);                /* additive */
    call2(s, MU_GL_BINDTEXTURE, 0x0de1, 12);
    color4(s, 0.5f, 0.75f, 1, 1);
    quad(s, 120, 16, 128, 32);
    call1(s, MU_GL_DISABLE, 0x0de1);                /* colour only */
    call2(s, MU_GL_BLENDFUNC, 0x302, 0x303);
    color4(s, 0, 0, 0, 0.5f);
    quad(s, 0, 100, (float)W, 24);
    color4(s, 0.2f, 0.9f, 0.3f, 1);                 /* a fan */
    call1(s, MU_GL_BEGIN, 6);
    vtx(s, 200, 120); vtx(s, 240, 120); vtx(s, 240, 160); vtx(s, 200, 160);
    call(s, MU_GL_END, NULL, 0);
    call1(s, MU_GL_ENABLE, 0x0de1);
    call1(s, MU_GL_ENABLE, 0x0bc0);                 /* alpha test GL_GREATER 0.25 */
    call2(s, MU_GL_BINDTEXTURE, 0x0de1, 11);
    color4(s, 1, 1, 1, 1);
    quad(s, 160, 60, 32, 32);
    call1(s, MU_GL_DISABLE, 0x0bc0);
    call1(s, MU_GL_ENABLE, 0x0b44);                 /* cull on: a clockwise quad is dropped */
    call1(s, MU_GL_BEGIN, 7);
    vtx(s, 10, 140); vtx(s, 10, 180); vtx(s, 50, 180); vtx(s, 50, 140);
    call(s, MU_GL_END, NULL, 0);
    call1(s, MU_GL_DISABLE, 0x0b44);
    texture(s, 11, 16, 16, 0, 0x2600);              /* re-upload after a draw used it */
    quad(s, 260, 8, 32, 32);
    call1(s, MU_GL_MATRIXMODE, W_GL_MODELVIEW);
    call(s, MU_GL_POPMATRIX, NULL, 0);
    call1(s, MU_GL_MATRIXMODE, W_GL_PROJECTION);
    call(s, MU_GL_POPMATRIX, NULL, 0);
}

static void background(uint8_t *rgba)
{
    for (int32_t y = 0; y < H; ++y)
        for (int32_t x = 0; x < W; ++x) {
            uint8_t *p = rgba + ((size_t)y * (size_t)W + (size_t)x) * 4;
            p[0] = (uint8_t)(x * 7);
            p[1] = (uint8_t)(y * 5);
            p[2] = 90;
            p[3] = 255;
        }
}

static int ui_mode(void)
{
    /* software */
    mu_ui_raster r;
    if (mu_ui_raster_init(&r, W, H))
        return 1;
    background(r.rgba);   /* rows bottom-up in both, the same picture */
    mu_ui_sink rs = mu_ui_raster_sink(&r);
    ui_stream(&rs);
    /* GPU: the background as a texture-less draw of the same pixels */
    uint8_t *bg = malloc((size_t)W * (size_t)H * 4);
    background(bg);
    glViewport(0, 0, W, H);
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
    glWindowPos2i(0, 0);
    glDrawPixels(W, H, GL_RGBA, GL_UNSIGNED_BYTE, bg);
    mu_ui_raster empty;
    mu_ui_raster_init(&empty, 4, 4);
    mu_ui_gl *g = mu_ui_gl_new(&empty, W, H);
    mu_ui_sink gs = mu_ui_gl_sink(g);
    mu_ui_gl_begin(g);
    ui_stream(&gs);
    mu_ui_gl_end(g);
    glFinish();
    uint8_t *out = malloc((size_t)W * (size_t)H * 4);
    glPixelStorei(GL_PACK_ALIGNMENT, 1);
    glReadPixels(0, 0, W, H, GL_RGBA, GL_UNSIGNED_BYTE, out);   /* bottom-up, as the raster */
    long differing = 0, above = 0;
    int worst = 0;
    for (size_t i = 0; i < (size_t)W * (size_t)H; ++i) {
        int d = 0;
        for (int k = 0; k < 3; ++k) {
            int e = abs((int)r.rgba[i * 4 + k] - (int)out[i * 4 + k]);
            if (e > d)
                d = e;
        }
        if (d) {
            ++differing;
            if (d > 2 && getenv("PERF_GL_HOST_DEBUG") && above < 40)
                fprintf(stderr, "diff at %d,%d: %d %d %d / %d %d %d\n", (int)(i % (size_t)W), (int)(i / (size_t)W),
                        r.rgba[i * 4], r.rgba[i * 4 + 1], r.rgba[i * 4 + 2], out[i * 4], out[i * 4 + 1], out[i * 4 + 2]);
            if (d > 2)
                ++above;
            if (d > worst)
                worst = d;
        }
    }
    mu_ui_gl_stats st;
    mu_ui_gl_stats_get(g, &st);
    printf("{\"pixels\": %d, \"differing\": %ld, \"max_delta\": %d, \"above2\": %ld, \"uploads\": %ld, "
           "\"primitives\": %ld, \"triangles\": %ld}\n",
           W * H, differing, worst, above, st.uploads, st.primitives, st.triangles);
    mu_ui_gl_free(g);
    mu_ui_raster_free(&empty);
    mu_ui_raster_free(&r);
    free(bg);
    free(out);
    return 0;
}

/* ---- batch ---- */

typedef struct sink {
    mu_gl_batch *b;   /* NULL: immediate */
} sink;

static void s_enable(sink *s, GLenum cap, int on)
{
    if (s->b)
        mu_gl_batch_enable(s->b, cap, on);
    else if (on)
        glEnable(cap);
    else
        glDisable(cap);
}
static void s_blend(sink *s, GLenum a, GLenum b)
{
    if (s->b)
        mu_gl_batch_blend_func(s->b, a, b);
    else
        glBlendFunc(a, b);
}
static void s_mask(sink *s, int on)
{
    if (s->b)
        mu_gl_batch_depth_mask(s->b, on);
    else
        glDepthMask(on ? GL_TRUE : GL_FALSE);
}
static void s_bind(sink *s, GLuint t)
{
    if (s->b)
        mu_gl_batch_bind_texture(s->b, t);
    else
        glBindTexture(GL_TEXTURE_2D, t);
}
static void s_begin(sink *s, GLenum m)
{
    if (s->b)
        mu_gl_batch_begin(s->b, m);
    else
        glBegin(m);
}
static void s_end(sink *s)
{
    if (s->b)
        mu_gl_batch_end(s->b);
    else
        glEnd();
}
static void s_tex(sink *s, float u, float v)
{
    if (s->b)
        mu_gl_batch_texcoord(s->b, u, v);
    else
        glTexCoord2f(u, v);
}
static void s_c3(sink *s, float r, float g, float b)
{
    if (s->b)
        mu_gl_batch_color4(s->b, r, g, b, 1.0f);
    else
        glColor3f(r, g, b);
}
static void s_c4(sink *s, float r, float g, float b, float a)
{
    if (s->b)
        mu_gl_batch_color4(s->b, r, g, b, a);
    else
        glColor4f(r, g, b, a);
}
static void s_v(sink *s, float x, float y, float z)
{
    const float v[3] = {x, y, z};
    if (s->b)
        mu_gl_batch_vertex(s->b, v);
    else
        glVertex3fv(v);
}

static GLuint make_texture(int seed)
{
    uint8_t p[16 * 16 * 4];
    for (int i = 0; i < 16 * 16; ++i) {
        p[i * 4] = (uint8_t)(i * (seed + 3));
        p[i * 4 + 1] = (uint8_t)(i * 7 + seed * 40);
        p[i * 4 + 2] = (uint8_t)(255 - i);
        p[i * 4 + 3] = (uint8_t)((i * 13) & 0xff);
    }
    GLuint t;
    glGenTextures(1, &t);
    glBindTexture(GL_TEXTURE_2D, t);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, 16, 16, 0, GL_RGBA, GL_UNSIGNED_BYTE, p);
    return t;
}

/* A height field of tiles: per tile a fan with its layer texture (two textures in runs), every fifth tile
 * an alpha layer (blend, depth mask off) and an additive neighbour face; grass as quads with a trailing
 * incomplete quad; then mesh triangles with the full state re-applied before each mesh. */
static int barrier_ok = 1;
static void batch_stream(sink *s, const GLuint tex[3])
{
    glEnable(GL_DEPTH_TEST);
    glDepthFunc(GL_LEQUAL);
    glEnable(GL_TEXTURE_2D);
    for (int ty = 0; ty < 12; ++ty)
        for (int tx = 0; tx < 16; ++tx) {
            float x0 = (float)tx / 8.0f - 1.0f, y0 = (float)ty / 6.0f - 1.0f, x1 = x0 + 0.125f, y1 = y0 + 1.0f / 6.0f;
            float z = 0.1f * sinf((float)(tx + ty));
            s_enable(s, GL_BLEND, 0);
            s_mask(s, 1);
            s_bind(s, tex[(tx / 3 + ty) & 1]);
            s_begin(s, GL_TRIANGLE_FAN);
            s_tex(s, 0, 0); s_c3(s, 0.8f, 0.7f, 0.6f + 0.02f * (float)tx); s_v(s, x0, y0, z);
            s_tex(s, 1, 0); s_c3(s, 0.9f, 0.8f, 0.7f); s_v(s, x1, y0, z + 0.01f);
            s_tex(s, 1, 1); s_c3(s, 0.7f, 0.9f, 0.8f); s_v(s, x1, y1, z);
            s_tex(s, 0, 1); s_c3(s, 0.6f, 0.6f, 0.9f); s_v(s, x0, y1, z - 0.01f);
            s_end(s);
            if ((tx + ty) % 5 == 0) {
                s_enable(s, GL_BLEND, 1);
                s_blend(s, GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
                s_mask(s, 0);
                s_bind(s, tex[2]);
                s_begin(s, GL_TRIANGLE_FAN);
                s_tex(s, 0, 0); s_c4(s, 1, 1, 1, 0.3f); s_v(s, x0, y0, z);
                s_tex(s, 1, 0); s_c4(s, 1, 1, 1, 0.6f); s_v(s, x1, y0, z + 0.01f);
                s_tex(s, 1, 1); s_c4(s, 1, 1, 1, 0.9f); s_v(s, x1, y1, z);
                s_tex(s, 0, 1); s_c4(s, 1, 1, 1, 0.1f); s_v(s, x0, y1, z - 0.01f);
                s_end(s);
                s_blend(s, GL_ONE, GL_ONE);
                s_begin(s, GL_TRIANGLE_FAN);   /* additive, colour kept from glColor4 above */
                s_v(s, x0, y0, z); s_v(s, x1, y0, z + 0.01f); s_v(s, x1, y1, z);
                s_end(s);
            }
        }
    if (s->b) mu_gl_batch_flush(s->b);
    GLint bound;
    glGetIntegerv(GL_TEXTURE_BINDING_2D, &bound);
    barrier_ok &= (GLuint)bound == tex[0] && glIsEnabled(GL_BLEND) == GL_FALSE;
    /* Offscreen primitives cross the capture chunk boundary without extra fill. */
    for (int i = 0; i < 24000; ++i) {
        s_begin(s, GL_TRIANGLES);
        s_v(s, 10, 10, 0); s_v(s, 11, 10, 0); s_v(s, 10, 11, 0);
        s_end(s);
    }
    s_enable(s, GL_BLEND, 0);
    s_mask(s, 1);
    s_enable(s, GL_ALPHA_TEST, 1);
    s_bind(s, tex[1]);
    for (int i = 0; i < 20; ++i) {   /* grass quads; the last one incomplete */
        float x = (float)i / 10.0f - 1.0f;
        s_begin(s, GL_QUADS);
        s_tex(s, 0, 0); s_c3(s, 0.5f, 1, 0.5f); s_v(s, x, -0.5f, 0.2f);
        s_tex(s, 1, 0); s_v(s, x + 0.08f, -0.5f, 0.2f);
        s_tex(s, 1, 1); s_v(s, x + 0.08f, -0.3f, 0.1f);
        s_tex(s, 0, 1); s_v(s, x, -0.3f, 0.1f);
        if (i == 19) {
            s_v(s, x, -0.2f, 0.1f);
            s_v(s, x + 0.05f, -0.2f, 0.1f);
        }
        s_end(s);
    }
    s_enable(s, GL_ALPHA_TEST, 0);
    for (int m = 0; m < 30; ++m) {   /* meshes: the whole state again before each */
        s_enable(s, GL_BLEND, m % 7 == 0);
        s_blend(s, GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
        s_enable(s, GL_DEPTH_TEST, 1);
        s_mask(s, 1);
        s_enable(s, GL_CULL_FACE, m % 3 != 0);
        s_enable(s, GL_TEXTURE_2D, m % 11 != 0);
        s_bind(s, tex[m % 2]);
        s_begin(s, GL_TRIANGLES);
        for (int t = 0; t < 6; ++t) {
            float cx = (float)(m % 6) / 3.0f - 0.9f, cy = (float)(m / 6) / 3.0f - 0.8f;
            float a = (float)t * 1.047f;
            s_tex(s, 0.5f, 0.5f); s_c4(s, 1, 0.5f, 0.2f, 0.8f); s_v(s, cx, cy, 0.3f);
            s_tex(s, 1, 0); s_v(s, cx + 0.1f * cosf(a), cy + 0.1f * sinf(a), 0.25f);
            s_tex(s, 0, 1); s_v(s, cx + 0.1f * cosf(a + 1.047f), cy + 0.1f * sinf(a + 1.047f), 0.25f);
        }
        s_end(s);
    }
}

static int batch_mode(void)
{
    GLuint tex[3] = {make_texture(1), make_texture(2), make_texture(3)};
    uint8_t *img[2];
    mu_gl_batch_stats stats;
    long uploads = 0, failures = 0;
    int binding_restored = 1;
    GLuint external_buffer;
    glGenBuffers(1, &external_buffer);
    glBindBuffer(GL_ARRAY_BUFFER, external_buffer);
    memset(&stats, 0, sizeof stats);
    for (int pass = 0; pass < 2; ++pass) {
        glViewport(0, 0, W, H);
        glClearColor(0.1f, 0.2f, 0.3f, 1.0f);
        glClearDepth(1.0);
        glDepthMask(GL_TRUE);
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
        glMatrixMode(GL_PROJECTION);
        glLoadIdentity();
        glMatrixMode(GL_MODELVIEW);
        glLoadIdentity();
        glAlphaFunc(GL_GREATER, 0.25f);
        glColor4f(1, 1, 1, 1);
        sink s = {pass ? mu_gl_batch_new() : NULL};
        if (s.b)
            mu_gl_batch_session_begin(s.b);
        batch_stream(&s, tex);
        if (s.b) {
            mu_gl_batch_session_end(s.b);
            mu_gl_batch_stats_get(s.b, &stats);
            mu_gl_batch_upload_stats(s.b, &uploads, &failures);
            GLint binding;
            glGetIntegerv(GL_ARRAY_BUFFER_BINDING, &binding);
            binding_restored &= (GLuint)binding == external_buffer;
            mu_gl_batch_free(s.b);
        }
        glFinish();
        img[pass] = malloc((size_t)W * (size_t)H * 4);
        glPixelStorei(GL_PACK_ALIGNMENT, 1);
        glReadPixels(0, 0, W, H, GL_RGBA, GL_UNSIGNED_BYTE, img[pass]);
    }
    binding_restored &= glIsBuffer(external_buffer) == GL_TRUE;
    glDeleteBuffers(1, &external_buffer);
    long differing = 0;
    for (size_t i = 0; i < (size_t)W * (size_t)H; ++i)
        if (memcmp(img[0] + i * 4, img[1] + i * 4, 3))
            ++differing;
    printf("{\"identical\": %s, \"differing\": %ld, \"primitives\": %ld, \"draws\": %ld, \"state_calls\": %ld, "
           "\"state_applied\": %ld, \"vertices\": %ld, \"uploads\": %ld, \"upload_failures\": %ld, \"binding_restored\": %d, \"barrier_ok\": %d}\n",
           differing ? "false" : "true", differing, stats.primitives, stats.draws, stats.state_calls,
           stats.state_applied, stats.vertices, uploads, failures, binding_restored, barrier_ok);
    free(img[0]);
    free(img[1]);
    return 0;
}

int main(int argc, char **argv)
{
    if (argc < 4) {
        fprintf(stderr, "usage: perf-gl-host ui|batch W H\n");
        return 2;
    }
    W = atoi(argv[2]);
    H = atoi(argv[3]);
    char error[256];
    if (mu_gl_headless_begin(W, H, error, sizeof error)) {
        fprintf(stderr, "headless GL: %s\n", error);
        return 3;
    }
    int status = !strcmp(argv[1], "ui") ? ui_mode() : !strcmp(argv[1], "batch") ? batch_mode() : 2;
    mu_gl_headless_end();
    return status;
}
