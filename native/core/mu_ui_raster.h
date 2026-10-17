#ifndef MU_UI_RASTER_H
#define MU_UI_RASTER_H

/* Deterministic software implementation of the OpenGL 1.x subset the
 * client's 2D interface layer uses (NATIVE-UI-001).  It is a mu_ui_sink:
 * the reconstructed routines in reconstructed/ui emit their calls into it.
 *
 * Supported: matrix stacks with glLoadIdentity/gluOrtho2D/gluPerspective,
 * glViewport, immediate-mode GL_TRIANGLE_FAN/GL_QUADS/GL_TRIANGLES with
 * glColor and glTexCoord, texture objects (RGB/RGBA, NEAREST/LINEAR,
 * CLAMP/REPEAT), GL_MODULATE, alpha test (GL_GREATER 0.25, as the client's
 * camera setup 0x0184adc7 leaves it), blending, back-face culling and
 * glClear.  GDI calls are ignored here (mu_ui_font implements them).
 * The framebuffer is RGBA8 with row 0 at the bottom, like GL.
 */

#include <stddef.h>
#include <stdint.h>

#include "../../reconstructed/ui/ui2d.h"

typedef struct mu_ui_texture_object {
    uint32_t name;
    int32_t width, height;
    uint8_t *rgba;
    uint32_t min_filter, mag_filter, wrap_s, wrap_t;
} mu_ui_texture_object;

enum { MU_UI_RASTER_MAX_TEXTURES = 512, MU_UI_RASTER_STACK = 8, MU_UI_RASTER_MAX_VERTICES = 64 };

typedef struct mu_ui_vertex {
    double x, y, z, w;     /* clip coordinates */
    float u, v;
    float color[4];
} mu_ui_vertex;

typedef struct mu_ui_raster {
    int32_t width, height;
    uint8_t *rgba;
    double projection[MU_UI_RASTER_STACK][16];
    double modelview[MU_UI_RASTER_STACK][16];
    int projection_depth, modelview_depth;
    uint32_t matrix_mode;
    int32_t viewport[4];
    uint8_t texture_2d, blend, alpha_test, cull_face;
    uint32_t blend_src, blend_dst;
    uint32_t alpha_func;
    float alpha_ref;
    float clear_color[4];
    uint32_t bound_texture;
    mu_ui_texture_object textures[MU_UI_RASTER_MAX_TEXTURES];
    int texture_count;
    float color[4];
    float texcoord[2];
    uint32_t primitive;
    int in_begin;
    mu_ui_vertex vertices[MU_UI_RASTER_MAX_VERTICES];
    int vertex_count;
    /* statistics */
    long primitives, triangles, fragments, unsupported;
} mu_ui_raster;

size_t mu_ui_raster_sizeof(void);   /* for ctypes callers */
int mu_ui_raster_init(mu_ui_raster *raster, int32_t width, int32_t height);
void mu_ui_raster_free(mu_ui_raster *raster);
/* mu_ui_sink callback; user is the raster. */
void mu_ui_raster_call(void *user, int op, const uint32_t *words, int count, const void *data, size_t bytes);
mu_ui_sink mu_ui_raster_sink(mu_ui_raster *raster);
/* Copy the framebuffer top row first (for PNG output). */
void mu_ui_raster_read_top_down(const mu_ui_raster *raster, uint8_t *out);

#endif
