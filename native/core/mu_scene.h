#ifndef MU_SCENE_H
#define MU_SCENE_H

#include <stdint.h>

#include "mu_meshdraw.h"
#include "mu_model.h"

/* Drives one model through a rendering backend in the client's per-mesh
 * order (docs/research/client-skinning.md, "Mesh draw GL sequence"):
 *   1. pre-loop colour when the lighting flag is clear;
 *   2. per-normal colour pass when the light byte is set;
 *   3. state from the render flags and the mesh texture bind;
 *   4. glBegin(GL_TRIANGLES); 5. the per-corner stream; 6. glEnd.
 * Steps 2 and 5 are the ported loop code (mu_meshdraw); 1 and 3 follow the
 * static reading. The backend receives GL-shaped calls only, so an OpenGL
 * backend issues literally the client's immediate-mode call sequence. */

typedef struct mu_render_backend {
    void *context;
    /* State and texture for mesh `mesh` (backend maps it to a texture). */
    void (*prepare)(void *context, const mu_meshdraw_state *state, int32_t mesh);
    void (*begin)(void *context);   /* glBegin(GL_TRIANGLES) */
    void (*end)(void *context);     /* glEnd() */
    mu_meshdraw_sink sink;
} mu_render_backend;

typedef struct mu_draw_options {
    int32_t mode;                /* draw mode for every mesh (2 = mesh UVs) */
    uint32_t flags;              /* render flags */
    float alpha;
    float u_offset, v_offset;
    int32_t uv_offset_mesh;      /* mesh index receiving the UV offset, -1 for none */
    uint8_t alpha_test;          /* viewer option: force alpha test on (not a client reading) */
    int8_t cull;                 /* viewer override: -1 follow the state reading, 0 off, 1 on */
} mu_draw_options;

void mu_draw_default_options(mu_draw_options *options);

typedef struct mu_draw_stats {
    long meshes, corners, refused;
} mu_draw_stats;

/* Draws every mesh. Scratch buffers are allocated internally. The per-normal
 * texcoord table that modes 4/0x1000/0x80000/0x100000 read (client global
 * 0x072acfd8) is filled by a writer that has not been recovered; the viewer
 * substitutes 0.5 + 0.5 * (rotated normal x, y) and labels it as such. */
int mu_scene_draw_model(const mu_model *model, const mu_draw_options *options, const mu_render_backend *backend,
                        mu_draw_stats *stats);

#endif
