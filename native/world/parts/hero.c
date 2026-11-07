/* parts/hero.c (WORLD-RT-001): the hero's parts in RenderCharacter's order, each with its shadow (item render
 * 0x0176ce74, NATIVE-PARTICLE-001).  The hero's character and its motion (mu_walk) are the runtime's; this part
 * owns the GL item sets and opens the characters' draw phase. */
#include <string.h>

#include "../../core/mu_perf.h"
#include "../../core/mu_scene.h"
#include "../../core/mu_renderchar.h"
#ifndef MU_WORLD_NO_GL
#include "../../viewer/gl_backend.h"
#endif
#include "../world_rt_internal.h"

static void hero_item_draw(mu_world_rt *a, int index, const mu_draw_options *options,
                           const mu_render_backend *backend)
{
    const mu_character_item *item = &a->ch.items[index];
    mu_renderchar_glow glow = {0};
    if (a->hero_glow_set[index])   /* HERO-ITEMS-001: the slot SetCharacterClass 0x01394870 wrote from the record */
        glow = a->hero_glow[index];
    else   /* no equipment record (class parts, files outside Item.bmd): infer standard model names */
        glow.type = mu_renderchar_type_from_path(item->path);
    mu_renderchar_env env;
    mu_renderchar_default_env(&env);
    env.lang = a->lang;
    env.time = a->map->time;
    env.particles = a->has_particles ? &a->particles : NULL;
    if (a->ground)   /* the players' glow colour (parts/players.c) when the EnchantEffect table is absent */
        memcpy(env.glow_color, a->ground->config.glow_color, sizeof env.glow_color);
    else {
        env.glow_color[0] = 0.4f;
        env.glow_color[1] = 0.6f;
        env.glow_color[2] = 1.0f;
    }
    if (index >= MU_CHARACTER_PART_SLOTS)   /* RenderLinkItem: the weapon's / wing's own pose (RENDER-ITEMS-CALLERS-001) */
        world_rt_item_pre(a, &env, MU_WORLD_PRE_HERO, glow.type, &item->model, item->bones, (uint32_t)index);
    mu_draw_stats ds = {0};
    /* RENDER-EFFECTS-021: worn armour with an owner-effect program draws with the hero's OBJECT owner */
    mu_renderchar_owner owner_data,
        *owner = index < MU_CHARACTER_PART_SLOTS ? world_rt_part_owner(a, &owner_data, glow.type, &a->ch) : NULL;
    mu_renderchar_draw_item_owner(&item->model, &glow, &env, a->ch.params.light, 1.0f, options, backend, &ds, NULL,
                                  owner);
    if (owner)
        world_rt_part_owner_done(a, MU_WORLD_PRE_HERO, owner);
    if ((index >= MU_CHARACTER_PART_SLOTS || glow.type == 0x389c || glow.type == 0x389d) && a->has_particles)
        mu_renderchar_link_effects(&item->model,
            index < MU_CHARACTER_PART_SLOTS ? a->ch.player_bones : item->bones, glow.type, &a->particles);
}

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
            hero_item_draw(a, mu_world_draw_order[n], &options, &backend);
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
    d->perf = mu_perf_begin(a->perf);
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
            hero_item_draw(a, mu_world_draw_order[n], &options, &backend);
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
