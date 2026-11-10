#include "../charsel_rt_internal.h"
#include "../charsel_items.h"
#include "../../core/mu_data.h"

const mu_charsel_item_draw *mu_charsel_rt_item(const mu_charsel_rt *a, int entry, int slot)
{
    if (!a || entry < 0 || entry >= a->s->list.count || slot < 1 || slot >= MU_CHARACTER_ITEMS ||
        !a->item_records[entry][slot])
        return NULL;
    return &a->item_draws[entry][slot];
}

static int open_items(mu_charsel_rt *a)
{
    mu_data_table table = {0};
    int have = 0, any = 0;
    for (int e = 0; e < a->s->list.count; ++e)
        for (int slot = 1; slot < MU_CHARACTER_ITEMS; ++slot) {
            const mu_charsel_entry *entry = &a->s->list.entries[e];
            mu_renderchar_glow *g = &a->item_draws[e][slot].glow;
            if (!entry->items[slot][0] || !a->s->characters[e].items[slot].loaded ||
                !mu_charsel_record_glow(&entry->records[slot], slot, g))
                continue;
            if (!any) {
                char path[4096];
                for (int k = 0; k < 2 && !have; ++k) {
                    mu_data_free(&table);
                    snprintf(path, sizeof path, "%s/Data/Local/%s", a->options.root, k ? "item.bmd" : "Item.bmd");
                    have = mu_data_load(path, NULL, &table) == 0 && table.result.status == 0;
                }
                a->item_lang = mu_lang_load_default();
                any = 1;
            }
            a->item_records[e][slot] = 1;
            mu_item item;
            if (have && mu_item_find(&table, (uint32_t)entry->records[slot].code, &item) == 0) {
                g->has_record = 1;
                g->kind_a = item.attributes.kind_a;
                g->kind_b = item.attributes.kind_b;
                g->item_kind = item.attributes.type;
            }
        }
    mu_data_free(&table);
    return 0;
}

static void close_items(mu_charsel_rt *a)
{
    mu_lang_free(a->item_lang);
    a->item_lang = NULL;
}

static void draw_item(mu_charsel_rt *a, int slot, const mu_draw_options *options,
                      const mu_render_backend *backend, mu_draw_stats *stats)
{
    const int entry = a->s->draw_entry;
    const mu_character *ch = &a->s->characters[entry];
    const mu_character_item *item = &ch->items[slot];
    if (!a->item_records[entry][slot]) {
        mu_scene_draw_model(&item->model, options, backend, stats);
        return;
    }
    mu_charsel_item_draw *draw = &a->item_draws[entry][slot];
    /* RenderLinkItem clears model +0x50 at 0x012bdb19. A draw-local view
     * preserves the assembly and the file-only fallback's lighting. */
    mu_model model = item->model;
    if (slot >= MU_CHARACTER_PART_SLOTS)
        model.params.lighting = 0;
    mu_renderchar_env env;
    mu_renderchar_default_env(&env);
    env.lang = a->item_lang;
    env.time = a->s->map->time;
    env.particles = a->s->has_particles ? &a->s->particles : NULL;
    env.frame_counter = &a->s->frames;
    long counts[2] = {0};
    env.pre_counts = counts;
    if (slot >= MU_CHARACTER_PART_SLOTS) {
        env.item_bones = item->bones;
        const float *origin = item->model.params.origin;
        env.item_out_of_view = !mu_terrain_test_frustum_2d(a->s->frustum.x2d, a->s->frustum.y2d,
            MU_CHARSEL_SCENE, origin[0] * 0.01f, origin[1] * 0.01f, -20.0f);
        env.item_owner = 1u + (uint32_t)(entry * MU_CHARACTER_ITEMS + slot);
        if (env.particles)
            mu_world_particles_item_owner_refresh(env.particles, env.item_owner, origin);
    }
    mu_renderchar_owner owner = {0}, *owner_ptr = NULL;
    if (slot < MU_CHARACTER_PART_SLOTS && ch->player_bones &&
        (mu_rc_item_owner_fx(draw->glow.type) || mu_rc_item_rank5(draw->glow.type))) {
        owner.bones = ch->player_bones;
        owner.bone_count = ch->player_bone_count;
        memcpy(owner.angle, ch->params.angles, sizeof owner.angle);
        owner_ptr = &owner;
    }
    mu_renderchar_stats rs = {0};
    mu_renderchar_draw_item_owner(&model, &draw->glow, &env, ch->params.light, 1.0f,
                                  options, backend, stats, &rs, owner_ptr);
    draw->passes += rs.passes;
    draw->special += rs.special;
    draw->effects += counts[0] + owner.effects;
    draw->refused += counts[1] + owner.refused;
    if (env.particles && slot >= MU_CHARACTER_PART_SLOTS)
        draw->effects += mu_renderchar_link_effects(&item->model, item->bones, draw->glow.type, env.particles);
}

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
        draw_item(a, draw_order[n], &options, &backend, &ds);
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
    .open = open_items,
    .close = close_items,
    .draw_soft = draw_soft,
#ifndef MU_CHARSEL_NO_GL
    .draw_gl = draw_gl,
    .gl_setup = gl_setup,
    .gl_teardown = gl_teardown,
#endif
};
