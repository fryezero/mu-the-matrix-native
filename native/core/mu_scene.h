#ifndef MU_SCENE_H
#define MU_SCENE_H

#include <stdint.h>

#include "mu_meshdraw.h"
#include "mu_model.h"
#include "mu_textures.h"

/* Draws one model with the port of the client's body 0x012bb35a and mesh
 * draw 0x012b8d1d (mu_meshdraw), whose GL call stream was compared with the
 * actual routine under emulation. The backend receives the GL-shaped calls:
 * `gl` (optional) gets every call literally; `prepare` gets the effective
 * fixed-function state and texture just before each glBegin, for backends
 * that do not issue GL (the software rasterizer).
 *
 * Viewer choices (not client facts), documented in native-viewer.md:
 *  - bitmap index of texture slot k is MU_SCENE_TEXTURE_BASE + k, GL name k+1;
 *    the environment bitmaps use their client indices and names after the
 *    model's; a missing texture binds name 0;
 *  - texture type table zero (0x012b3e2e fills it with 0 at load), mesh flag
 *    byte zero (written 0 at 0x012b3edd), sub-object records from the texture
 *    names as the loader builds them (mu_meshdraw_sub_from_name), skin fields
 *    zero; textures loaded by the item rule supply the texture types, +0xa4
 *    and +0xa6 (mu_textures, RENDER-ITEMS-TEX-002);
 *  - no bitmap keeps its pixels (the client frees model texture pixels after
 *    the upload), so mode 0x8000 stops with MU_MESHDRAW_FAULT where the
 *    client would read through a null pointer;
 *  - each call starts from the scene defaults of 0x0184adc7 (alpha test off,
 *    texture/depth/cull/depth mask on, blend off, fog setting off) with the
 *    model colour taken from the parameters (the client keeps both across
 *    calls). */

#define MU_SCENE_TEXTURE_BASE 0x9000

typedef struct mu_render_backend {
    void *context;
    /* Effective state and texture slot (index into mu_textures, -1 none) before glBegin. */
    void (*prepare)(void *context, const mu_meshdraw_state *state, int32_t texture);
    void (*begin)(void *context);   /* glBegin(GL_TRIANGLES) */
    void (*end)(void *context);     /* glEnd() */
    mu_meshdraw_sink sink;
    /* Optional: every GL call as recorded (state calls included). */
    const mu_gl_sink *gl;
} mu_render_backend;

typedef struct mu_draw_options {
    uint32_t flags;              /* render flags (default 2, the dominant immediate of the body wrapper) */
    float alpha;
    int32_t select;              /* [ebp+0x20]: uv-offset mesh / highlight texture slot (-1 none, <= -2 all) */
    float color_scale;           /* [ebp+0x24]: highlight colour scale */
    float u_offset, v_offset;
    int32_t skip_mesh;           /* body [ebp+0x2c] */
    int32_t texture;             /* [ebp+0x30]: bitmap override, -1 none */
    float time;                  /* global 0x06fce370 (milliseconds) */
    float env_vector[3];         /* global 0x0a381de0 (flag 0x800) */
    const mu_textures *textures; /* optional: component counts and specials */
    uint8_t alpha_test;          /* viewer override: force alpha test on (not a client reading) */
    int8_t cull;                 /* viewer override: -1 follow the stream, 0 off, 1 on */
    /* NATIVE-RENDERCHAR-001 (zero = previous behaviour):
     * mesh_plus_one: 0 draws the body 0x012bb35a, k > 0 only mesh k-1 through
     * the mesh draw 0x012b8d1d (the RenderMesh default-buffer wrapper);
     * fields: model fields the world render writes before a pass (NULL = the
     * model parameters' colour, other fields zero). */
    int32_t mesh_plus_one;
    const struct mu_draw_model_fields *fields;
} mu_draw_options;

/* Model fields of one world-render pass (renderchar.h mu_rc_draw). */
typedef struct mu_draw_model_fields {
    float color[3];              /* +0x54 body light */
    int32_t hide_typed;          /* +0x40 */
    float alt_color[3];          /* +0x44 */
    uint8_t alt_on_skin;         /* +0xca */
    uint8_t flag_a5;             /* +0xa5 */
} mu_draw_model_fields;

void mu_draw_default_options(mu_draw_options *options);

typedef struct mu_draw_stats {
    long meshes, corners, refused, faulted;
} mu_draw_stats;

int mu_scene_draw_model(const mu_model *model, const mu_draw_options *options, const mu_render_backend *backend,
                        mu_draw_stats *stats);

/* The client-shaped inputs the scene builds for a model (for recorders that
 * export the case, see mu_meshdraw_case.h). Arrays stay owned by `scene`. */
typedef struct mu_scene_inputs {
    mu_meshdraw_model model;
    mu_meshdraw_mesh *meshes;
    int32_t *texture_index, *texture_type;
    mu_meshdraw_globals globals;
    mu_meshdraw_args args;
    int32_t skip;
    mu_gl_cache cache;
    uint8_t (*subs)[5];          /* mesh +0x1c records (meshes[i].sub points here or is NULL) */
    mu_bitmap *bitmaps;          /* bitmap_count entries */
    int32_t *bitmap_index;
    int32_t bitmap_count;
} mu_scene_inputs;
int mu_scene_inputs_build(const mu_model *model, const mu_draw_options *options, mu_scene_inputs *inputs);
void mu_scene_inputs_free(mu_scene_inputs *inputs);
const mu_bitmap *mu_scene_bitmap(void *inputs, int32_t index);

#endif
