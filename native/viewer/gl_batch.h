#ifndef MU_GL_BATCH_H
#define MU_GL_BATCH_H

/* Draw batching for the immediate-mode GL streams of the 3D view
 * (NATIVE-PERF-001).
 *
 * The reconstructed terrain tile renderer and mesh draw emit the client's GL
 * call stream literally (glBegin, a glTexCoord/glColor/glVertex per corner,
 * glEnd, state calls in between); compared with the client under emulation,
 * that stream stays as it is.  On macOS each glBegin/glEnd pair is a Metal
 * draw with its own state validation, and that, not the arithmetic, was the
 * cost of the terrain and object passes (docs/research/native-performance.md).
 * mu_gl_batch sits between the stream and GL:
 *
 *   - state calls are compared with the state this batch applied last and
 *     dropped when they change nothing (the stream re-applies the whole state
 *     before every mesh);
 *   - consecutive primitives drawn with the same state, texture and mode are
 *     collected (current texture coordinate and colour as immediate mode
 *     keeps them) and drawn by one glDrawArrays (GL_TRIANGLES, GL_QUADS) or
 *     glMultiDrawArrays (GL_TRIANGLE_FAN: the same fans), in the same order;
 *   - anything that changes state first draws what is pending.
 *
 * The same primitives with the same vertex values reach the rasterizer in
 * the same order, so the image is the same (checked pixel for pixel, see the
 * note).  A session (begin .. end) must not be interleaved with direct GL
 * calls: the state shadow is only valid inside it.  end draws the rest and
 * leaves GL's current colour and texture coordinate as immediate mode would. */

#include <stdint.h>

typedef struct mu_gl_batch mu_gl_batch;

typedef struct mu_gl_batch_stats {
    long primitives;     /* glBegin .. glEnd pairs received */
    long draws;          /* GL draw calls issued */
    long vertices;
    long state_calls;    /* state calls received */
    long state_applied;  /* ... that changed GL state */
} mu_gl_batch_stats;

mu_gl_batch *mu_gl_batch_new(void);
void mu_gl_batch_free(mu_gl_batch *b);

void mu_gl_batch_session_begin(mu_gl_batch *b);
void mu_gl_batch_session_end(mu_gl_batch *b);
void mu_gl_batch_flush(mu_gl_batch *b);

/* State (GL enums; texture is a GL texture name for GL_TEXTURE_2D). */
void mu_gl_batch_enable(mu_gl_batch *b, uint32_t capability, int on);
void mu_gl_batch_blend_func(mu_gl_batch *b, uint32_t src, uint32_t dst);
void mu_gl_batch_depth_mask(mu_gl_batch *b, int on);
void mu_gl_batch_front_face(mu_gl_batch *b, uint32_t mode);
void mu_gl_batch_polygon_mode(mu_gl_batch *b, uint32_t mode);
void mu_gl_batch_bind_texture(mu_gl_batch *b, uint32_t name);

/* Immediate mode: GL_TRIANGLES, GL_QUADS or GL_TRIANGLE_FAN. */
void mu_gl_batch_begin(mu_gl_batch *b, uint32_t mode);
void mu_gl_batch_texcoord(mu_gl_batch *b, float s, float t);
void mu_gl_batch_color4(mu_gl_batch *b, float r, float g, float bl, float a);
void mu_gl_batch_vertex(mu_gl_batch *b, const float xyz[3]);
void mu_gl_batch_end(mu_gl_batch *b);

void mu_gl_batch_stats_get(const mu_gl_batch *b, mu_gl_batch_stats *out);
void mu_gl_batch_stats_reset(mu_gl_batch *b);

#endif
