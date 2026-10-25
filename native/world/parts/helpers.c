/* parts/helpers.c (WORLD-RT-001): pets and mounts (NATIVE-HELPERS-001/002): --helper ITEM [--helper-state N]
 * gives the hero one (DEMO), the players' come from their viewport records; MoveBugs and the mount manager's
 * move loop after MoveCharacters, RenderBugs, the mount render loop and the Imps. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef MU_WORLD_NO_GL
#include "../../viewer/gl_backend.h"
#endif
#include "../world_rt_internal.h"

/* NATIVE-HELPERS-001: SetPlayerStop / SetPlayerWalk ask the rider action 0x0106c382 while the owner rides. */
static int hero_ride(void *context, mu_walk *walk, int32_t how)
{
    mu_world_rt *a = context;
    (void)walk;
    return a->helpers ? mu_world_helpers_ride(a->helpers, 0, how) : 0;
}

static int player_ride(void *context, int32_t player, int32_t how)
{
    mu_world_rt *a = context;
    return a->helpers ? mu_world_helpers_ride(a->helpers, 1 + player, how) : 0;
}

static int helpers_open(struct mu_world_rt *a, void *self)
{
    (void)self;
    char error[1024];
    if (!a->no_helpers && (a->helper_arg || a->players)) {   /* NATIVE-HELPERS-001 */
        int32_t state = 0, item = -1;
        if (a->helper_arg) {
            item = mu_world_helpers_parse(a->helper_arg, &state);
            if (item == -2) {
                fprintf(stderr, "helpers: unknown helper '%s'\n", a->helper_arg);
                return 1;
            }
            if (a->helper_state >= 0)
                state = a->helper_state;
        }
        a->helpers = calloc(1, sizeof *a->helpers);
        if (!a->helpers || mu_world_helpers_open(a->helpers, a->root, a->map, &a->walk, a->players, item, state,
                                                 0x5eed1e1u, 0, error, sizeof error)) {
            fprintf(stderr, "%s\n", a->helpers ? error : "helpers: out of memory");
            return 1;
        }
        if (a->has_particles)
            mu_world_helpers_attach_particles(a->helpers, &a->particles);
        if (a->has_character)
            mu_world_helpers_attach_hero(a->helpers, &a->ch);
        a->walk.ride_hook = hero_ride;
        a->walk.ride_context = a;
        if (a->players) {
            a->players->ride_hook = player_ride;
            a->players->ride_context = a;
        }
    }
    return 0;
}

static void helpers_close(struct mu_world_rt *a, void *self)
{
    (void)self;
    if (a->helpers) {   /* NATIVE-HELPERS-001 */
        mu_world_helpers_close(a->helpers);
        free(a->helpers);
        a->helpers = NULL;
    }
}

/* NATIVE-HELPERS-001: MoveBugs, the mount manager's move loop (after MoveCharacters). */
static void helpers_tick(struct mu_world_rt *a, void *self)
{
    (void)self;
    if (a->helpers)
        mu_world_helpers_step(a->helpers);
}

static void helpers_draw_soft(struct mu_world_rt *a, void *self, mu_world_draw *d)
{
    (void)self;
    if (a->helpers)   /* NATIVE-HELPERS-001 */
        mu_world_helpers_draw_raster(a->helpers, d->raster, a->legacy_box ? NULL : &a->frustum,
                                     a->has_character ? &a->ch : NULL);
}

static void helpers_report_frame(const struct mu_world_rt *a, const void *self, int32_t frame)
{
    (void)self;
    if (a->helpers)
        mu_world_helpers_report_frame(a->helpers, stdout, frame);
}

static void helpers_report_summary(const struct mu_world_rt *a, const void *self)
{
    (void)self;
    if (a->helpers)
        mu_world_helpers_report_summary(a->helpers, stdout, a->quiet);
}

#ifndef MU_WORLD_NO_GL
typedef struct helpers_part {
    mu_gl_backend helper_gl[MU_WH_MODELS];
    mu_world_rt *rt;               /* the runtime of the running draw (the helper callbacks' context) */
} helpers_part;

static void helpers_gl_teardown(struct mu_world_rt *a, void *self)
{
    (void)a;
    helpers_part *p = self;
    for (int32_t i = 0; i < MU_WH_MODELS; ++i)
        if (p->helper_gl[i].textures)
            mu_gl_release(&p->helper_gl[i]);
    memset(p->helper_gl, 0, sizeof p->helper_gl);
}

/* NATIVE-HELPERS-001: the helper models load on demand; their textures upload on first use. */
static int helper_gl_backend(void *context, const mu_world_helpers *w, int32_t slot, mu_render_backend *out)
{
    helpers_part *p = context;
    if (slot < 0 || slot >= MU_WH_MODELS || !w->models[slot].loaded)
        return 1;
    if (!p->helper_gl[slot].textures)
        mu_gl_upload(&p->helper_gl[slot], &w->models[slot].textures, 0);
    mu_gl_backend_bind(&p->helper_gl[slot], out);
    return 0;
}

/* The mounts' RenderBodyShadow with the colour 0x0103d281 sends (EnableAlphaTest blend). */
static void helper_gl_shadow(void *context, const mu_world_helpers *w, int32_t slot, const float rgba[4])
{
    helpers_part *p = context;
    mu_world_rt *a = p->rt;
    mu_render_backend backend;
    if (!a->has_particles || helper_gl_backend(p, w, slot, &backend))
        return;
    mu_world_particles_shadow(&a->particles, &w->models[slot].model, &w->models[slot].bmd, rgba, &backend);
}

/* NATIVE-HELPERS-002: a functor's second RenderBodyShadow over meshes first..end. */
static void helper_gl_shadow_range(void *context, const mu_world_helpers *w, int32_t slot, const float rgba[4],
                                   int32_t first, int32_t end)
{
    helpers_part *p = context;
    mu_world_rt *a = p->rt;
    mu_render_backend backend;
    if (!a->has_particles || helper_gl_backend(p, w, slot, &backend))
        return;
    mu_world_particles_shadow_range(&a->particles, &w->models[slot].model, &w->models[slot].bmd, rgba, first, end,
                                    &backend);
}

/* NATIVE-HELPERS-001: RenderBugs, the mount render loop, the Imps (own backends, direct: outside the batch
 * session, which the players part already ended when there are players). */
static void helpers_draw_gl(struct mu_world_rt *a, void *self, mu_world_draw *d)
{
    (void)d;
    helpers_part *p = self;
    if (a->helpers) {
        if (a->batch && !a->players)
            mu_gl_batch_session_end(a->batch);
        p->rt = a;
        mu_world_helpers_target target = {p, helper_gl_backend, helper_gl_shadow, helper_gl_shadow_range};
        mu_world_helpers_draw(a->helpers, a->legacy_box ? NULL : &a->frustum, a->has_character ? &a->ch : NULL,
                              &target);
        glDisable(GL_BLEND);
        glDepthMask(GL_TRUE);
        glDisable(GL_ALPHA_TEST);
        if (a->batch && !a->players)
            mu_gl_batch_session_begin(a->batch);
    }
}
#endif

const mu_world_part_ops mu_part_helpers = {
    .name = "helpers",
#ifndef MU_WORLD_NO_GL
    .state_size = sizeof(helpers_part),
    .draw_gl = helpers_draw_gl,
    .gl_teardown = helpers_gl_teardown,
#endif
    .open = helpers_open,
    .close = helpers_close,
    .tick = helpers_tick,
    .draw_soft = helpers_draw_soft,
    .report_frame = helpers_report_frame,
    .report_summary = helpers_report_summary,
};
