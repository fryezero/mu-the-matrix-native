#ifndef MU_UI_GL_H
#define MU_UI_GL_H

/* The client's 2D interface calls straight on OpenGL (NATIVE-PERF-001).
 *
 * The reconstructed 2D layer (reconstructed/ui) emits its GL calls through a
 * mu_ui_sink; core/mu_ui_raster.c gives them meaning in software, over a
 * copy of the 3D frame read back from the GPU.  mu_ui_gl is the same sink on
 * the GPU, over the 3D frame still in the framebuffer: no glFinish, no read
 * back, no full-frame upload.  It follows mu_ui_raster's semantics so both
 * paths draw the same picture up to rounding (native/tests: the synthetic
 * call streams through both; the private scene comparison in
 * docs/research/native-performance.md):
 *
 *   - state the raster keeps (texture/blend/alpha-test/cull enables, blend
 *     factors, bound texture, colour, texture coordinate, viewport, both
 *     matrix stacks in double precision) is tracked here and applied before
 *     each primitive, so the 3D pass in between frames does not leak in;
 *   - GL_QUADS and fans are drawn as the raster splits them ((0,1,2),
 *     (0,2,3)), at most 64 vertices per glBegin, other modes skipped;
 *   - depth test and fog have no effect (the raster has no depth buffer),
 *     texturing is always GL_MODULATE, the alpha test is GL_GREATER 0.25;
 *   - the raster samples the base level for the mipmap filters, so they map
 *     to GL_NEAREST / GL_LINEAR; textures are converted to RGBA as the raster
 *     does (short data reads as zero);
 *   - glClear clears colour only.
 *
 * Textures created before the sink was attached are taken from the raster's
 * texture table the first time they are bound (`raster`, may be NULL). */

#include <stddef.h>
#include <stdint.h>

#include "../core/mu_ui_raster.h"

typedef struct mu_ui_gl mu_ui_gl;

mu_ui_gl *mu_ui_gl_new(const mu_ui_raster *raster, int32_t width, int32_t height);
void mu_ui_gl_free(mu_ui_gl *g);   /* deletes its GL textures (needs the context) */
void mu_ui_gl_resize(mu_ui_gl *g, int32_t width, int32_t height);
/* mu_ui_sink callback; user is the mu_ui_gl. */
void mu_ui_gl_call(void *user, int op, const uint32_t *words, int count, const void *data, size_t bytes);
mu_ui_sink mu_ui_gl_sink(mu_ui_gl *g);
/* Before a series of calls on a framebuffer the 3D pass used: GL state for 2D
 * (depth test and writes off, MODULATE, ...); after: the 3D pass's defaults
 * (depth test on, writes on, blend off). */
void mu_ui_gl_begin(mu_ui_gl *g);
void mu_ui_gl_end(mu_ui_gl *g);
/* statistics */
typedef struct mu_ui_gl_stats {
    long primitives, triangles, uploads, unsupported;
} mu_ui_gl_stats;
void mu_ui_gl_stats_get(const mu_ui_gl *g, mu_ui_gl_stats *out);

#endif
