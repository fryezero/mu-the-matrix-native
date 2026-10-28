/* parts/marker.c (WORLD-RT-001): a viewer aid (not a client reading): a flat marker on the clicked point while the
 * hero walks there.  The client draws a cursor effect instead. */
#include <string.h>

#include "../../core/mu_perf.h"
#ifndef MU_WORLD_NO_GL
#include "../../viewer/gl_backend.h"
#endif
#include "../world_rt_internal.h"

static void marker(const mu_world_rt *a, const mu_render_backend *b)
{
    const mu_walk *w = &a->walk;
    if (!w->hero.movement)
        return;
    mu_meshdraw_state state;
    mu_meshdraw_state_defaults(&state);   /* depth test and writes on, blend off (ONE, ZERO) */
    state.cull = 0;
    state.texture = 0;
    b->prepare(b->context, &state, -1);
    b->begin(b->context);
    const float red[3] = {0.95f, 0.2f, 0.1f};
    float c[3] = {(float)w->target[0] * 100.0f + 50.0f, (float)w->target[1] * 100.0f + 50.0f, 0.0f};
    c[2] = mu_request_terrain_height(a->map->height, a->map->attributes, a->map->water_height, 6, c[0], c[1]) + 3.0f;
    const float s = 28.0f;
    float p[4][3] = {{c[0], c[1] - s, c[2]}, {c[0] + s, c[1], c[2]}, {c[0], c[1] + s, c[2]}, {c[0] - s, c[1], c[2]}};
    const int tri[6] = {0, 1, 2, 0, 2, 3};
    for (int i = 0; i < 6; ++i) {
        b->sink.color3(b->sink.context, red);
        b->sink.vertex(b->sink.context, p[tri[i]]);
    }
    b->end(b->context);
}

static void marker_draw_soft(struct mu_world_rt *a, void *self, mu_world_draw *d)
{
    (void)self;
    mu_render_backend backend;
    mu_raster_backend(d->raster, &backend);
    marker(a, &backend);
}

#ifndef MU_WORLD_NO_GL
/* The last of the environment's phase (opened by the env part). */
static void marker_draw_gl(struct mu_world_rt *a, void *self, mu_world_draw *d)
{
    (void)self;
    mu_gl_backend plain;
    memset(&plain, 0, sizeof plain);
    mu_render_backend backend;
    mu_gl_backend_bind(&plain, &backend);
    marker(a, &backend);
    mu_perf_end(a->perf, MU_PERF_ENV, d->perf);
}
#endif

const mu_world_part_ops mu_part_marker = {
    .name = "marker",
#ifndef MU_WORLD_NO_GL
    .draw_gl = marker_draw_gl,
#endif
    .draw_soft = marker_draw_soft,
};
