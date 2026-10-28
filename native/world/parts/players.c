/* parts/players.c (WORLD-RT-001): other players from a DEMO players file (NATIVE-PLAYERS-001, --players FILE,
 * --no-players, --player-range N): the demo server's packets, MoveCharacters' remote step and the animation step
 * each tick; RenderCharacter's parts through RenderObjDraw's passes each frame.  SESSION-VIEWPORT-001 later feeds
 * the same records from 0x12/0x3d/0x14/0x17/0x3f frames. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../../core/mu_renderchar.h"
#ifndef MU_WORLD_NO_GL
#include "../../viewer/gl_backend.h"
#endif
#include "../world_rt_internal.h"

static int players_open(struct mu_world_rt *a, void *self)
{
    (void)self;
    char error[1024];
    if (a->players_file && !a->no_players) {   /* NATIVE-PLAYERS-001: the demo server's players */
        a->players = calloc(1, sizeof *a->players);
        if (!a->players || mu_world_players_load(a->players, a->root, &a->walk, a->map, a->players_file, 0, error,
                                                 sizeof error)) {
            fprintf(stderr, "players: %s\n", a->players ? error : "out of memory");
            return 1;
        }
        if (a->player_range > 0)
            a->players->view_range = a->player_range;
        mu_world_players_attach(a->players, a->names, a->combat);
    }
    return 0;
}

static void players_close(struct mu_world_rt *a, void *self)
{
    (void)self;
    if (a->players) {
        mu_world_players_free(a->players);
        free(a->players);
        a->players = NULL;
    }
}

static void players_frame(struct mu_world_rt *a, void *self, uint32_t now)
{
    (void)self;
    (void)now;
    if (a->players)
        mu_world_players_frame(a->players);
}

/* NATIVE-PLAYERS-001: one part / weapon / wing of another player through RenderObjDraw's passes (the level
 * glow, excellent and ancient passes of NATIVE-RENDERCHAR-001; class parts and special types take the plain
 * pass) with the character light and the object alpha (the dead fade). */
static void player_item_draw(mu_world_rt *a, int32_t i, int item, const mu_render_backend *backend, float alpha)
{
    const mu_world_player *q = &a->players->list[i];
    const mu_character_item *it = &q->model.items[item];
    mu_renderchar_glow glow;
    int has_record;
    mu_world_players_glow(a->players, i, item, &glow.type, &glow.level, &glow.option1, &glow.ext, &has_record,
                          &glow.kind_a, &glow.kind_b, &glow.item_kind);
    glow.has_record = has_record;
    mu_renderchar_env env;
    mu_renderchar_default_env(&env);   /* the EnchantEffect colours of the Lang tables (MU_LANG_DIR) when present */
    env.time = a->map->time;
    env.quality = 5;
    if (a->ground)   /* the same glow colour as the ground items (--glow-color) when the table is absent */
        memcpy(env.glow_color, a->ground->config.glow_color, sizeof env.glow_color);
    else {
        env.glow_color[0] = 0.4f;   /* viewer parameter, as the NATIVE-RENDERCHAR-001 sheets */
        env.glow_color[1] = 0.6f;
        env.glow_color[2] = 1.0f;
    }
    mu_draw_options options;
    mu_draw_default_options(&options);
    options.textures = &it->textures;
    mu_draw_stats ds = {0, 0, 0, 0};
    mu_renderchar_stats rs = {0, 0};
    mu_renderchar_draw_item(&it->model, &glow, &env, q->model.params.light, alpha, &options, backend, &ds, &rs);
    if ((item >= MU_CHARACTER_PART_SLOTS || glow.type == 0x389c || glow.type == 0x389d) && a->has_particles)
        mu_renderchar_link_effects(&it->model,
            item < MU_CHARACTER_PART_SLOTS ? q->model.player_bones : it->bones, glow.type, &a->particles);
}

static void players_draw_soft(struct mu_world_rt *a, void *self, mu_world_draw *d)
{
    (void)self;
    mu_raster *raster = d->raster;
    mu_render_backend backend;
    mu_raster_backend(raster, &backend);
    for (int32_t i = 0; a->players && i < a->players->count; ++i) {   /* NATIVE-PLAYERS-001 */
        float alpha = mu_world_players_alpha(a->players, i);
        if (alpha <= 0.0f)
            continue;
        const mu_world_player *q = &a->players->list[i];
        for (int n = 0; n < MU_CHARACTER_ITEMS; ++n) {
            const mu_character_item *item = &q->model.items[mu_world_draw_order[n]];
            if (!item->loaded)
                continue;
            raster->textures = item->textures.slots;
            raster->texture_count = item->textures.count;
            raster->texture_filter = item->textures.filter;
            raster->texture_wrap = item->textures.wrap;
            if (a->has_particles)
                mu_world_particles_character_shadow(&a->particles, &item->model, &item->bmd, &backend);
            player_item_draw(a, i, mu_world_draw_order[n], &backend, alpha);
        }
    }
}

static void players_report_frame(const struct mu_world_rt *a, const void *self, int32_t frame)
{
    (void)self;
    if (a->players)
        mu_world_players_report_frame(a->players, stdout, frame);
}

static void players_report_summary(const struct mu_world_rt *a, const void *self)
{
    (void)self;
    if (a->players)
        mu_world_players_report_summary(a->players, stdout, a->quiet);
}

#ifndef MU_WORLD_NO_GL
typedef struct players_part {
    mu_gl_backend player_gl[MU_WORLD_PLAYERS_MAX][MU_CHARACTER_ITEMS];
    uint32_t player_gl_gen[MU_WORLD_PLAYERS_MAX];
} players_part;

static void players_gl_teardown(struct mu_world_rt *a, void *self)
{
    (void)a;
    players_part *p = self;
    for (int32_t i = 0; i < MU_WORLD_PLAYERS_MAX; ++i)
        for (int n = 0; n < MU_CHARACTER_ITEMS; ++n)
            if (p->player_gl[i][n].textures)
                mu_gl_release(&p->player_gl[i][n]);
}

/* RenderCharacter's ordered parts. Upload before opening the remote-player
 * batch; helpers still use direct GL after this session ends. */
static void players_draw_gl(struct mu_world_rt *a, void *self, mu_world_draw *d)
{
    (void)d;
    players_part *p = self;
    if (a->batch && a->players)
        mu_gl_batch_session_end(a->batch);
    const char *baseline = getenv("MU_PERF_002_BASELINE");
    int batch = a->batch && a->players && !(baseline && atoi(baseline));
    for (int32_t i = 0; a->players && i < a->players->count; ++i) {
        float alpha = mu_world_players_alpha(a->players, i);
        if (alpha <= 0.0f)
            continue;
        const mu_world_player *q = &a->players->list[i];
        if (p->player_gl_gen[i] != q->creates) {   /* the parts were (re)loaded at a viewport: new textures */
            for (int n = 0; n < MU_CHARACTER_ITEMS; ++n)
                if (p->player_gl[i][n].textures)
                    mu_gl_release(&p->player_gl[i][n]);
            memset(p->player_gl[i], 0, sizeof p->player_gl[i]);
            p->player_gl_gen[i] = q->creates;
        }
        for (int n = 0; n < MU_CHARACTER_ITEMS; ++n) {
            const mu_character_item *item = &q->model.items[mu_world_draw_order[n]];
            if (!item->loaded)
                continue;
            mu_gl_backend *gl = &p->player_gl[i][mu_world_draw_order[n]];
            if (!gl->textures)
                mu_gl_upload(gl, &item->textures, 0);
        }
    }
    if (batch) mu_gl_batch_session_begin(a->batch);
    for (int32_t i = 0; a->players && i < a->players->count; ++i) {
        float alpha = mu_world_players_alpha(a->players, i);
        if (alpha <= 0.0f) continue;
        const mu_world_player *q = &a->players->list[i];
        for (int n = 0; n < MU_CHARACTER_ITEMS; ++n) {
            const mu_character_item *item = &q->model.items[mu_world_draw_order[n]];
            if (!item->loaded) continue;
            mu_gl_backend *gl = &p->player_gl[i][mu_world_draw_order[n]];
            gl->batch = batch ? a->batch : NULL;
            mu_render_backend backend;
            mu_gl_backend_bind(gl, &backend);
            if (a->has_particles)
                mu_world_particles_character_shadow(&a->particles, &item->model, &item->bmd, &backend);
            player_item_draw(a, i, mu_world_draw_order[n], &backend, alpha);
        }
    }
    if (batch) mu_gl_batch_session_end(a->batch);
}
#endif

const mu_world_part_ops mu_part_players = {
    .name = "players",
#ifndef MU_WORLD_NO_GL
    .state_size = sizeof(players_part),
    .draw_gl = players_draw_gl,
    .gl_teardown = players_gl_teardown,
#endif
    .open = players_open,
    .close = players_close,
    .frame = players_frame,
    .draw_soft = players_draw_soft,
    .report_frame = players_report_frame,
    .report_summary = players_report_summary,
};
