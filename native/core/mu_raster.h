#ifndef MU_RASTER_H
#define MU_RASTER_H

#include <stdint.h>

#include "mu_image.h"
#include "mu_meshdraw.h"
#include "mu_scene.h"

/* Deterministic software rasterizer implementing the fixed-function subset
 * the mesh draw uses: GL_TRIANGLES from consecutive vertex triples (a
 * four-corner record shifts later triangles exactly as in GL), current
 * texcoord/colour semantics, clamped vertex colours, near/far clipping,
 * back-face culling (counter-clockwise front), LEQUAL depth test, GL_MODULATE
 * with GL_REPEAT (or clamp to edge for GL_CLAMP textures) and nearest or
 * bilinear sampling per texture, alpha test (GREATER ref), blending with the
 * six factors used by the client, round-to-nearest unorm8
 * output. It exists for headless renders with stable hashes: all arithmetic
 * is binary32/64 basic operations, so with -ffp-contract=off the output is
 * bit-identical across IEEE hosts. It is a viewer reference, not a model of
 * any particular GPU. */

typedef struct mu_raster_vertex {
    float position[3], texcoord[2], color[4];
} mu_raster_vertex;

typedef struct mu_raster {
    int32_t width, height;
    uint8_t *color;            /* RGBA8, rows top to bottom */
    float *depth;
    float view[16], projection[16];
    const mu_image *const *textures;  /* per texture slot (mu_textures), may be NULL entries (white) */
    int32_t texture_count;
    const uint32_t *texture_filter;   /* optional per slot: GL_NEAREST / GL_LINEAR */
    const uint32_t *texture_wrap;     /* optional per slot: GL_REPEAT / GL_CLAMP */
    int linear;                /* 1 forces bilinear for every texture, 0 follows texture_filter */
    float alpha_reference;     /* alpha test GREATER reference */
    uint8_t front_ccw;         /* 1: counter-clockwise front faces (GL default) */
    mu_meshdraw_state state;
    const mu_image *texture;
    int32_t texture_slot;
    float current_texcoord[2], current_color[4];
    mu_raster_vertex *vertices;
    int32_t vertex_count, vertex_capacity;
    long triangles, fragments;
    int primitive;             /* mode of the open primitive (4, 6 or 7) */
} mu_raster;

int mu_raster_init(mu_raster *raster, int32_t width, int32_t height);
void mu_raster_free(mu_raster *raster);
void mu_raster_clear(mu_raster *raster, const uint8_t rgba[4]);
/* Primitive assembly for callers other than the scene driver (terrain):
 * mode 4 GL_TRIANGLES, 6 GL_TRIANGLE_FAN (fanned from vertex 0), 7 GL_QUADS
 * (each quad split 0-1-2, 0-2-3). Vertices come through the backend sink. */
void mu_raster_set(mu_raster *raster, const mu_meshdraw_state *state, const mu_image *texture, int linear);
void mu_raster_begin_mode(mu_raster *raster, int mode);
void mu_raster_end_mode(mu_raster *raster);
/* Backend for mu_scene_draw_model. */
void mu_raster_backend(mu_raster *raster, mu_render_backend *backend);

#endif
