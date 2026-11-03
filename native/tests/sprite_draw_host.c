/* SPRITE-DRAW-001: one CreateSprite of a registered bitmap in front of the camera produces pixels through the
 * shared sprite pass (RenderSprites 0x0169270e, RenderSprite 0x0184c39c) in the software raster and in GL (the
 * --backend gl path of the fidelity tour), for the additive, alpha and opaque-then-alpha blends.  The same sprite
 * 1.5 half-angles above the view axis (where Acheron's bone sprites sit at the DATA-ACQ-002 tile) draws none. */
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../core/mu_particles.h"
#include "../core/mu_raster.h"
#include "../viewer/gl_backend.h"
#include "../viewer/gl_headless.h"

#ifdef __APPLE__
#include <OpenGL/gl.h>
#else
#include <GL/gl.h>
#endif

enum { W = 128, H = 96 };
static mu_world_particles particles;
static const uint8_t background[4] = {0, 0, 0, 255};

static void perspective(float fov_deg, float aspect, float n, float f, float m[16])
{
    const float t = 1.0f / tanf(fov_deg * 3.14159265f / 360.0f);
    memset(m, 0, 16 * sizeof *m);
    m[0] = t / aspect;
    m[5] = t;
    m[10] = (f + n) / (n - f);
    m[11] = -1.0f;
    m[14] = 2.0f * f * n / (n - f);
}

/* The client's view (a rotation and translation): x right, z up, looking along +y from (0, -400, 0). */
static void view_matrix(float m[16])
{
    static const float v[16] = {1, 0, 0, 0, 0, 0, -1, 0, 0, 1, 0, 0, 0, 0, -400, 1};
    memcpy(m, v, sizeof v);
}

static int lit(const uint8_t *rgba)
{
    int n = 0;
    for (int i = 0; i < W * H; ++i)
        n += rgba[4 * i] > 8 || rgba[4 * i + 1] > 8 || rgba[4 * i + 2] > 8;
    return n;
}

/* 400 units ahead of the eye; the vertical half-angle is 30 degrees, so z = 346 is 1.5 half-angles up */
static float sprite_z;

static void sprite(int32_t bitmap, int32_t blend)
{
    const float at[3] = {0.0f, 0.0f, sprite_z}, light[3] = {1.0f, 1.0f, 1.0f};
    assert(mu_world_particles_sprite(&particles, bitmap, at, 4.0f, light, -1, 0.0f, blend, 4) >= 0);
}

static int raster_pixels(int32_t bitmap, int32_t blend)
{
    mu_raster r;
    assert(mu_raster_init(&r, W, H) == 0);
    mu_raster_clear(&r, background);
    view_matrix(r.view);
    perspective(60.0f, (float)W / (float)H, 10.0f, 5000.0f, r.projection);
    sprite(bitmap, blend);
    mu_world_particles_draw_raster(&particles, &r, r.view);
    assert(particles.stats.drawn_sprites == 1);
    const int n = lit(r.color);
    mu_raster_free(&r);
    return n;
}

static int gl_target(void *context, const mu_world_particles *p, mu_render_backend *out)
{
    (void)p;
    mu_gl_backend_bind(context, out);
    return 0;
}

static int gl_pixels(mu_gl_backend *gl, int32_t bitmap, int32_t blend)
{
    float view[16], projection[16];
    view_matrix(view);
    perspective(60.0f, (float)W / (float)H, 10.0f, 5000.0f, projection);
    mu_gl_frame(W, H, background, view, projection);
    sprite(bitmap, blend);
    const mu_world_particles_target target = {gl, gl_target};
    mu_world_particles_draw(&particles, view, &target);
    assert(particles.stats.drawn_sprites == 1);
    glFinish();
    uint8_t *rgba = malloc((size_t)W * H * 4);
    assert(rgba);
    mu_gl_read(W, H, rgba);
    const int n = lit(rgba);
    free(rgba);
    return n;
}

static void run(int *raster, int *gpu, int have_gl)
{
    /* flare01 (32x32 in the fixture): additive (blend 0), alpha (2) and the opaque-then-alpha pair (4) */
    static const int32_t blends[3] = {0, 2, 4};
    for (int i = 0; i < 3; ++i)
        raster[i] = raster_pixels(MU_PT_BITMAP_FLARE, blends[i]);
    if (have_gl) {
        mu_gl_backend gl;
        memset(&gl, 0, sizeof gl);
        mu_gl_upload(&gl, &particles.bitmaps, 0);
        for (int i = 0; i < 3; ++i)
            gpu[i] = gl_pixels(&gl, MU_PT_BITMAP_FLARE, blends[i]);
        mu_gl_release(&gl);
    }
}

int main(int argc, char **argv)
{
    assert(argc == 2);
    char error[256];
    assert(mu_world_particles_open(&particles, argv[1], NULL, 0, 1, 0, error, sizeof error) == 0);
    const int have_gl = mu_gl_headless_begin(W, H, error, sizeof error) == 0;
    int raster[3], gpu[3] = {-1, -1, -1}, raster_above[3], gpu_above[3] = {-1, -1, -1};
    int raster_high[3], gpu_high[3] = {-1, -1, -1};
    sprite_z = 0.0f;
    run(raster, gpu, have_gl);
    sprite_z = 173.0f;   /* 0.75 half-angles up: still in the view */
    run(raster_high, gpu_high, have_gl);
    sprite_z = 346.0f;
    run(raster_above, gpu_above, have_gl);
    if (have_gl)
        mu_gl_headless_end();
    printf("ahead: raster %d %d %d, gl %d %d %d; above the view: raster %d %d %d, gl %d %d %d%s\n", raster[0],
           raster[1], raster[2], gpu[0], gpu[1], gpu[2], raster_above[0], raster_above[1], raster_above[2],
           gpu_above[0], gpu_above[1], gpu_above[2], have_gl ? "" : " (no GL)");
    mu_world_particles_close(&particles);
    for (int i = 0; i < 3; ++i) {
        /* the 128-unit quad spans about 23 x 23 pixels here */
        assert(raster[i] > 400 && raster_high[i] > 400 && raster_above[i] == 0);
        assert(!have_gl || (gpu[i] > 400 && gpu_high[i] > 400 && gpu_above[i] == 0));
    }
    puts("one sprite ahead of the camera draws pixels, the same sprite above the view none: OK");
    return 0;
}
