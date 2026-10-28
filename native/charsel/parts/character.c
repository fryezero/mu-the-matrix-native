#include "../charsel_rt_internal.h"

static const int draw_order[MU_CHARACTER_ITEMS] = {5, 4, 3, 2, 1, 0, 6, 7, 8};

/* The drawn character's parts in the client's order, each after its shadow (RenderCharacter 0x01363260: the
 * shadow first, then the parts; the item render's shadow block, NATIVE-CHARSEL-002). */
typedef void (*part_backend_fn)(mu_charsel_rt *a, int entry, int part, mu_render_backend *out);

static void draw_character(mu_charsel_rt *a, part_backend_fn part_backend, mu_raster *raster)
{
    mu_charsel_session *s = a->s;
    if (s->draw_entry < 0)
        return;
    mu_draw_options options;
    mu_draw_default_options(&options);
    const mu_character *ch = &s->characters[s->draw_entry];
    for (int n = 0; n < MU_CHARACTER_ITEMS; ++n) {
        const mu_character_item *item = &ch->items[draw_order[n]];
        if (!item->loaded)
            continue;
        mu_render_backend backend;
        part_backend(a, s->draw_entry, draw_order[n], &backend);
        if (raster) {
            raster->textures = item->textures.slots;
            raster->texture_count = item->textures.count;
            raster->texture_filter = item->textures.filter;
            raster->texture_wrap = item->textures.wrap;
        }
        if (s->has_particles && mu_world_particles_character_shadow(&s->particles, &item->model, &item->bmd, &backend))
            ++s->shadows;
        options.textures = &item->textures;
        mu_draw_stats ds = {0, 0, 0, 0};
        mu_scene_draw_model(&item->model, &options, &backend, &ds);
    }
    if (raster) {
        raster->textures = NULL;
        raster->texture_count = 0;
        raster->texture_filter = NULL;
        raster->texture_wrap = NULL;
    }
}

static void soft_part_backend(mu_charsel_rt *a, int entry, int part, mu_render_backend *out)
{
    (void)entry;
    (void)part;
    mu_raster_backend(a->soft_raster, out);
}
static void draw_soft(mu_charsel_rt *a, mu_charsel_draw *d)
{
    mu_raster *raster = d->raster;
    a->soft_raster = raster;
    raster->linear = 1;
    raster->front_ccw = 1;
    draw_character(a, soft_part_backend, raster);   /* RenderCharacter(shown) */
}

#ifndef MU_CHARSEL_NO_GL
static void gl_part_backend(mu_charsel_rt *a, int entry, int part, mu_render_backend *out)
{
    mu_gl_backend_bind(&a->character.items[entry][part], out);
}
static void draw_gl(mu_charsel_rt *a, mu_charsel_draw *d)
{
    (void)d;
    glDisable(GL_BLEND);
    glDepthMask(GL_TRUE);
    draw_character(a, gl_part_backend, NULL);   /* RenderCharacter(shown), each part after its shadow */
}

static void gl_setup(mu_charsel_rt *a)
{
    for (int e = 0; e < MU_CHARSEL_MAX_ENTRIES; ++e)
        for (int i = 0; i < MU_CHARACTER_ITEMS; ++i) {
            memset(&a->character.items[e][i], 0, sizeof a->character.items[e][i]);
            if (a->s->character_loaded[e] && a->s->characters[e].items[i].loaded)
                mu_gl_upload(&a->character.items[e][i], &a->s->characters[e].items[i].textures, 0);
        }
}

static void gl_teardown(mu_charsel_rt *a)
{
    for (int e = 0; e < MU_CHARSEL_MAX_ENTRIES; ++e)
        for (int i = 0; i < MU_CHARACTER_ITEMS; ++i)
            mu_gl_release(&a->character.items[e][i]);
}
#endif

const mu_charsel_part_ops mu_charsel_character_part = {
    .draw_soft = draw_soft,
#ifndef MU_CHARSEL_NO_GL
    .draw_gl = draw_gl,
    .gl_setup = gl_setup,
    .gl_teardown = gl_teardown,
#endif
};
