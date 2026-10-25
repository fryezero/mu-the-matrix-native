/* parts/hero.c (WORLD-RT-001): the hero's parts in RenderCharacter's order, each with its shadow (item render
 * 0x0176ce74, NATIVE-PARTICLE-001).  The hero's character and its motion (mu_walk) are the runtime's; this part
 * owns the GL item sets and opens the characters' draw phase. */
#include <string.h>

#include "../../core/mu_perf.h"
#include "../../core/mu_scene.h"
#ifndef MU_WORLD_NO_GL
#include "../../viewer/gl_backend.h"
#endif
#include "../world_rt_internal.h"

static void hero_draw_soft(struct mu_world_rt *a, void *self, mu_world_draw *d)
{
    (void)self;
    mu_raster *raster = d->raster;
    mu_render_backend backend;
    mu_raster_backend(raster, &backend);
    mu_draw_options options;
    mu_draw_default_options(&options);
    raster->linear = 1;
    raster->front_ccw = 1;
    if (a->has_character)
        for (int n = 0; n < MU_CHARACTER_ITEMS; ++n) {
            const mu_character_item *item = &a->ch.items[mu_world_draw_order[n]];
            if (!item->loaded)
                continue;
            raster->textures = item->textures.slots;
            raster->texture_count = item->textures.count;
            raster->texture_filter = item->textures.filter;
            raster->texture_wrap = item->textures.wrap;
            if (a->has_particles)
                mu_world_particles_character_shadow(&a->particles, &item->model, &item->bmd, &backend);
            options.textures = &item->textures;   /* bitmap GL names and component counts */
            mu_draw_stats ds = {0, 0, 0, 0};
            mu_scene_draw_model(&item->model, &options, &backend, &ds);
        }
}

#ifndef MU_WORLD_NO_GL
typedef struct hero_part {
    mu_gl_backend items[MU_CHARACTER_ITEMS];
} hero_part;

static void hero_gl_setup(struct mu_world_rt *a, void *self)
{
    hero_part *p = self;
    for (int i = 0; i < MU_CHARACTER_ITEMS; ++i) {
        memset(&p->items[i], 0, sizeof p->items[i]);
        const mu_character_item *item = &a->ch.items[i];
        if (a->has_character && item->loaded)
            mu_gl_upload(&p->items[i], &item->textures, 0);
        p->items[i].batch = a->batch;
    }
}

static void hero_gl_teardown(struct mu_world_rt *a, void *self)
{
    (void)a;
    hero_part *p = self;
    for (int i = 0; i < MU_CHARACTER_ITEMS; ++i)
        mu_gl_release(&p->items[i]);
}

/* The characters' phase: the hero, then the players, helpers and actors parts; the actors part closes it. */
static void hero_draw_gl(struct mu_world_rt *a, void *self, mu_world_draw *d)
{
    hero_part *p = self;
    mu_draw_options options;
    mu_draw_default_options(&options);
    d->perf = mu_perf_begin();
    if (a->batch)
        mu_gl_batch_session_begin(a->batch);
    if (a->has_character)
        for (int n = 0; n < MU_CHARACTER_ITEMS; ++n) {
            const mu_character_item *item = &a->ch.items[mu_world_draw_order[n]];
            if (!item->loaded)
                continue;
            mu_render_backend backend;
            mu_gl_backend_bind(&p->items[mu_world_draw_order[n]], &backend);
            if (a->has_particles)   /* the part's shadow (item render 0x0176ce74, NATIVE-PARTICLE-001) */
                mu_world_particles_character_shadow(&a->particles, &item->model, &item->bmd, &backend);
            options.textures = &item->textures;   /* bitmap GL names and component counts */
            mu_draw_stats ds = {0, 0, 0, 0};
            mu_scene_draw_model(&item->model, &options, &backend, &ds);
        }
}
#endif

const mu_world_part_ops mu_part_hero = {
    .name = "hero",
#ifndef MU_WORLD_NO_GL
    .state_size = sizeof(hero_part),
    .draw_gl = hero_draw_gl,
    .gl_setup = hero_gl_setup,
    .gl_teardown = hero_gl_teardown,
#endif
    .draw_soft = hero_draw_soft,
};
