#ifndef MU_MESHDRAW_H
#define MU_MESHDRAW_H

#include <stdint.h>

/* Platform-neutral port of the client's mesh draw routine 0x012b8d1d.
 *
 * Source: the per-corner loop 0x012ba8a0..0x012bb229 and the per-normal
 * colour precompute 0x012b968c..0x012b996c as decoded in
 * mac-play/hotpatch/meshdraw-notes.md and implemented in
 * mac-play/hotpatch/meshdraw.c (md_run, md_light_run), whose call stream was
 * reported equal to the original loop over about 9.5M in-game meshes. Here
 * the same rules take explicit host pointers instead of the routine's frame
 * and fixed client addresses, and emit through a GL-shaped sink, so the same
 * code drives OpenGL immediate mode, a software rasterizer or a recorder.
 *
 * Per corner, by draw mode (the routine's local [ebp-0x38]):
 *   2                    texcoord(t (+uv offset when apply_uv_offset));
 *                        then colour(light colour of n[j]) when light_colors
 *   4                    colour(model colour); texcoord(normal table entry of n[j])
 *   0x1000, 0x80000,
 *   0x100000             colour(model colour); texcoord(normal table entry + uv offset)
 *   0x8000               not portable (client calls mutate alpha/colour): refused
 *   anything else        no attributes (1 and 0x40 in the client)
 * then the vertex, by render flags (first match):
 *   0x20                 planar projection about the model origin (constants 2000, 4000, 5)
 *   0x400 (without 0x20) not portable (client sine wobble): refused
 *   0x200000             skip the vertex when voff > z of the triangle's first three corners
 *   otherwise            vertex(transform output of v[j])
 * colour(c) is color3(c) when alpha >= 0.99f, else color4(c, alpha) (C >=, so NaN takes color4).
 * All float work is binary32 in the original order; build with -ffp-contract=off.
 *
 * The client bounds no index. This module checks every index against the
 * supplied counts and refuses the mesh instead (an authored convention).
 */

typedef struct mu_meshdraw_sink {
    void *context;
    void (*texcoord)(void *context, float s, float t);
    void (*color3)(void *context, const float rgb[3]);
    void (*color4)(void *context, float r, float g, float b, float a);
    void (*vertex)(void *context, const float xyz[3]);
} mu_meshdraw_sink;

typedef struct mu_meshdraw_mesh {
    const uint8_t *triangles;      /* mesh +0x18: 0x24-byte records (u8 corners, int16 v[4] at +2, n[4] at +0xa, t[4] at +0x12) */
    int32_t triangle_count;        /* mesh +0xa */
    const float *texcoords;        /* mesh +0x14: two floats per texcoord */
    int32_t texcoord_count;
    const float *vertices;         /* transform output for this mesh, three floats per vertex */
    int32_t vertex_count;
    const float *light_colors;     /* per-normal colours (client 0x089c2120 + mesh*0x2bf20), three floats per normal */
    const float *normal_texcoords; /* per-normal texcoords (client 0x072acfd8), two floats per normal */
    int32_t normal_count;
    const float *model_color;      /* model +0x54 */
    const float *origin;           /* model +0x78 */
} mu_meshdraw_mesh;

typedef struct mu_meshdraw_params {
    int32_t mode;                  /* [ebp-0x38] */
    uint32_t flags;                /* [ebp+0x0c] render flags */
    float alpha;                   /* [ebp+0x1c] */
    float u_offset, v_offset;      /* [ebp+0x28], [ebp+0x2c] */
    uint8_t apply_uv_offset;       /* [ebp-0x31] */
    uint8_t light_colors;          /* [ebp-0x21]: model +0x50 and mesh != model +0x94 */
} mu_meshdraw_params;

enum {
    MU_MESHDRAW_OK = 0,
    MU_MESHDRAW_CLIENT_CALLS = 1,  /* mode 0x8000 or flag 0x400: needs client routines */
    MU_MESHDRAW_BAD_INDEX = 2      /* index outside the supplied counts */
};

#define MU_MESHDRAW_ALPHA_THRESHOLD 0.99f  /* binary32 at 0x01a82fe0 */

/* Emits the corner stream of one mesh (between glBegin(GL_TRIANGLES) and
 * glEnd). *corners receives the number of corners visited. */
int mu_meshdraw_corners(const mu_meshdraw_mesh *mesh, const mu_meshdraw_params *params,
                        const mu_meshdraw_sink *sink, long *corners);

/* Per-normal colour precompute (0x012b968c): for n < count,
 *   secondary_select == 1: out[n][k] = secondary[n]*color[k] + 0.2f
 *   otherwise:             out[n][k] = light[n]*color[k]. */
void mu_meshdraw_light_colors(const float *light, const float *secondary, int32_t count, const float color[3],
                              uint8_t secondary_select, float *out);

/* Pre-loop colour (static reading, docs/research/client-skinning.md step 1):
 * when the model's lighting flag is clear, color3(model colour) at alpha >=
 * 0.99, else color4(model colour, alpha). Returns 1 when a call was emitted. */
int mu_meshdraw_pre_color(uint8_t lighting, const float color[3], float alpha, const mu_meshdraw_sink *sink);

/* Fixed-function state chosen from the render flags. This follows the static
 * reading of the client's state wrappers (client-skinning.md, "State
 * wrappers"); it is not instruction-verified and the branch structure around
 * it was not decoded in full. */
enum { MU_BLEND_ZERO, MU_BLEND_ONE, MU_BLEND_SRC_COLOR, MU_BLEND_ONE_MINUS_SRC_COLOR, MU_BLEND_SRC_ALPHA,
       MU_BLEND_ONE_MINUS_SRC_ALPHA };
typedef struct mu_meshdraw_state {
    uint8_t blend, depth_test, depth_mask, cull, alpha_test, texture;
    uint8_t src, dst;
} mu_meshdraw_state;
void mu_meshdraw_state_for(uint32_t flags, float alpha, mu_meshdraw_state *state);

#endif
