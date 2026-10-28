/* parts/env.c (WORLD-RT-001): the client's ambient life and weather (NATIVE-ENV-001, core/mu_env): every logic
 * step MoveLeaves (behind the tick's guard), MoveBoids and MoveFishs; every frame the render routines' models and
 * particles and the world's clear colour (--no-env disables it, --env-tga-leaves loads the leaf .tga the client
 * unloads, a viewer option). */
#include <stdio.h>
#include <string.h>

#include "../../core/mu_perf.h"
#ifndef MU_WORLD_NO_GL
#include "../../viewer/gl_backend.h"
#endif
#include "../world_rt_internal.h"

static int env_open(struct mu_world_rt *a, void *self)
{
    (void)self;
    char error[1024];
    if (!a->no_env) {
        if (mu_world_env_open(&a->env, a->root, a->map, a->world, a->env_seed, 0, a->env_tga, error, sizeof error)) {
            fprintf(stderr, "environment: %s\n", error);
            return 1;
        }
        a->has_env = 1;
        a->env.sound = world_rt_ambient_sound;
        a->env.sound_context = a;
    }
    return 0;
}

static void env_close(struct mu_world_rt *a, void *self)
{
    (void)self;
    if (a->has_env)
        mu_world_env_close(&a->env);
}

/* MoveLeaves (guarded), MoveBoids, MoveFishs in the tick's order. */
static void env_tick(struct mu_world_rt *a, void *self)
{
    (void)self;
    const mu_walk *w = &a->walk;
    const mu_hero *h = &w->hero;
    if (a->has_env) {
        mu_world_env_hero hero = {{h->position[0], h->position[1], h->position[2]}, {h->tile[0], h->tile[1]},
                                  h->action, h->safe_zone, mu_hero_tile(a->map->layer1, h->position[0],
                                                                        h->position[1])};
        mu_world_env_step(&a->env, &hero, w->frame.view.position, (float)w->frame.clock.frame_tick);
        if (a->has_sound)
            a->sound.rain = a->env.env.rain_level;   /* 0x0a3a9acc for the per-frame audio block */
    }
}

static void env_draw_soft(struct mu_world_rt *a, void *self, mu_world_draw *d)
{
    (void)self;
    const mu_client_view *v = &a->walk.frame.view;
    if (a->has_env)
        mu_world_env_draw_raster(&a->env, d->raster, v->modelview, a->legacy_box ? NULL : &a->frustum);
}

static void env_report_summary(const struct mu_world_rt *a, const void *self)
{
    (void)self;
    if (a->has_env) {
        const mu_world_env_stats *e = &a->env.stats;
        printf("{\"env\": true, \"world\": %d, \"models\": %d, \"leaf_bitmap\": %d, \"steps\": %u,"
               " \"leaf_steps\": %u, \"max_boids\": %u, \"max_fishs\": %u, \"max_leaves\": %u, \"sounds\": %u,"
               " \"bird\": %u, \"bat\": %u, \"rat\": %u, \"particles\": %u, \"inits\": %u, \"kills\": %u,"
               " \"rand_calls\": %llu, \"rain_level\": %d, \"tormenta_rain\": %.3f}\n",
               a->env.world, a->env.model_count, a->env.bitmap_present[0], e->steps, e->leaf_steps, e->max_boids,
               e->max_fishs, e->max_leaves, e->sounds, e->sound_bird, e->sound_bat, e->sound_rat, e->particles,
               e->inits, e->kills, (unsigned long long)a->env.env.rand_calls, a->env.env.rain_level,
               (double)a->env.env.tormenta.rain);
    }
}

#ifndef MU_WORLD_NO_GL
typedef struct env_part {
    mu_gl_backend env_gl[MU_WORLD_ENV_MODELS + 1];   /* models, then the weather bitmaps */
} env_part;

static void env_gl_setup(struct mu_world_rt *a, void *self)
{
    env_part *p = self;
    memset(p->env_gl, 0, sizeof p->env_gl);
    for (int32_t i = 0; a->has_env && i < a->env.model_count; ++i)
        if (a->env.models[i].loaded)
            mu_gl_upload(&p->env_gl[i], &a->env.models[i].textures, 0);
    if (a->has_env)
        mu_gl_upload(&p->env_gl[MU_WORLD_ENV_MODELS], &a->env.bitmaps, 0);
}

static void env_gl_teardown(struct mu_world_rt *a, void *self)
{
    (void)a;
    env_part *p = self;
    for (int32_t i = 0; i <= MU_WORLD_ENV_MODELS; ++i)
        if (p->env_gl[i].textures)
            mu_gl_release(&p->env_gl[i]);
}

static int env_gl_backend(void *context, const mu_world_env *e, int32_t slot, mu_render_backend *out)
{
    env_part *p = context;
    (void)e;
    mu_gl_backend_bind(&p->env_gl[slot < 0 ? MU_WORLD_ENV_MODELS : slot], out);
    return 0;
}

/* Opens the environment's phase (the marker part closes it). */
static void env_draw_gl(struct mu_world_rt *a, void *self, mu_world_draw *d)
{
    const mu_client_view *v = &a->walk.frame.view;
    d->perf = mu_perf_begin(a->perf);
    if (a->has_env) {
        mu_world_env_target target = {self, env_gl_backend};
        mu_world_env_draw(&a->env, v->modelview, a->legacy_box ? NULL : &a->frustum, &target);
        glDisable(GL_BLEND);
        glDepthMask(GL_TRUE);
        glDisable(GL_ALPHA_TEST);
    }
}
#endif

const mu_world_part_ops mu_part_env = {
    .name = "env",
#ifndef MU_WORLD_NO_GL
    .state_size = sizeof(env_part),
    .draw_gl = env_draw_gl,
    .gl_setup = env_gl_setup,
    .gl_teardown = env_gl_teardown,
#endif
    .open = env_open,
    .close = env_close,
    .tick = env_tick,
    .draw_soft = env_draw_soft,
    .report_summary = env_report_summary,
};
