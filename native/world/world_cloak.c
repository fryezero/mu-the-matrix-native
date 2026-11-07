/* RENDER-ITEMS-CLOAK: the wings' physics capes in the world. See world_cloak.h. */
#include "world_cloak.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../../reconstructed/cloth/cloth.h"
#include "../core/mu_meshdraw.h"
#include "../core/mu_raster.h"
#include "../core/mu_textures.h"
#ifndef MU_WORLD_NO_GL
#include "../viewer/gl_backend.h"
#endif
#include "world_rt_internal.h"

#define CLOAK_SLOTS (1 + MU_WORLD_PLAYERS_MAX)

/* The cloth bitmaps of CreateCloth's wing cases, as LoadBitmap loads them (0x018252db.., 0x01827699): GL_LINEAR,
 * kundun_innocence2 and BlackCloak_3 with GL_REPEAT, the two sparkle halves with GL_CLAMP. */
static const struct { int32_t bitmap; const char *name; uint32_t wrap; } cloth_bitmaps[] = {
    {0x83f6, "kundun_innocence2.tga", 0x2901},
    {0x846b, "BlackCloak_3.tga", 0x2901},
    {0x83f7, "kundun_sparkle3.tga", 0x2900},
    {0x83f8, "kundun_sparkle3_1.tga", 0x2900},
};
enum { CLOTH_BITMAPS = 4 };

typedef struct cloak_slot {
    int16_t wing;
    uint32_t generation;
    uint32_t stepped;              /* the rendered frame of the last MoveCloth */
    int active;                    /* drawn since its OBJECT was made: stepped by world_cloak_frame every frame */
    int count;
    const mu_character *ch;        /* the character drawn (the hero's, or player list[key - 1]'s model) */
    mu_cloth cloths[MU_CLOTH_WINGS_MAX];
} cloak_slot;

typedef struct world_cloak {
    mu_cloth_globals g;
    uint32_t wind_at;              /* logic-step counter the wind walk has reached */
    int wind_started;
    cloak_slot *slots[CLOAK_SLOTS];
    mu_textures textures;
    int textures_state;            /* 0 not tried, 1 loaded, -1 failed */
    int32_t slot_of[CLOTH_BITMAPS];
#ifndef MU_WORLD_NO_GL
    mu_gl_backend gl;
    int gl_ready;
#endif
    world_cloak_stats stats;
} world_cloak;

static world_cloak *cloak_state(mu_world_rt *a)
{
    if (!a->cloak) {
        world_cloak *w = calloc(1, sizeof *w);
        if (!w)
            return NULL;
        mu_cloth_default_globals(&w->g);
        a->cloak = w;
    }
    return a->cloak;
}

static int load_textures(mu_world_rt *a, world_cloak *w)
{
    if (w->textures_state)
        return w->textures_state > 0;
    w->textures_state = -1;
    mu_bmd none;
    memset(&none, 0, sizeof none);
    if (mu_textures_load_specials(&w->textures, &none, NULL))
        return 0;
    char directory[4096];
    snprintf(directory, sizeof directory, "%s/Data/Item/texture", a->root ? a->root : ".");
    for (int i = 0; i < CLOTH_BITMAPS; ++i) {
        const int32_t index = cloth_bitmaps[i].bitmap;
        const char *dirs[1] = {directory}, *names[1] = {cloth_bitmaps[i].name};
        w->slot_of[i] = w->textures.count;
        if (mu_textures_add_extras(&w->textures, &index, dirs, names, 1, 0x2601, cloth_bitmaps[i].wrap))
            return 0;
    }
    w->textures_state = 1;
    return 1;
}

static int32_t texture_slot(const world_cloak *w, int32_t bitmap)
{
    for (int i = 0; i < CLOTH_BITMAPS; ++i)
        if (cloth_bitmaps[i].bitmap == bitmap)
            return w->slot_of[i];
    return -1;
}

/* ---- the GL calls of Render 0x00fd8bc2 onto a render backend: GL_QUADS as two triangles each ---- */

typedef struct cloak_sink {
    const world_cloak *w;
    const mu_render_backend *backend;
    mu_meshdraw_state state;
    int32_t texture;
    float rgba[4];
    float uv[4][2], xyz[4][3];
    int corner;
} cloak_sink;

static void s_state(void *context, int32_t wrapper)
{
    cloak_sink *s = context;
    mu_meshdraw_state_defaults(&s->state);
    s->state.texture = 1;
    switch (wrapper) {
    case MU_CLOTH_STATE_ALPHA_TEST:   /* EnableAlphaTest(1) 0x0184a990 (mu_meshdraw.c w_alpha) */
        s->state.blend = 1;
        s->state.src = MU_GL_SRC_ALPHA;
        s->state.dst = MU_GL_ONE_MINUS_SRC_ALPHA;
        s->state.cull = 0;
        s->state.depth_mask = 1;
        s->state.alpha_test = 1;
        break;
    case MU_CLOTH_STATE_BLEND_ONE:    /* EnableAlphaBlend 0x0184aa2b */
        s->state.blend = 1;
        s->state.src = MU_GL_ONE;
        s->state.dst = MU_GL_ONE;
        s->state.cull = 0;
        s->state.depth_mask = 0;
        s->state.alpha_test = 0;
        break;
    default:                          /* DisableAlphaBlend 0x0184a7f3 */
        s->state.blend = 0;
        s->state.cull = 1;
        s->state.depth_mask = 1;
        s->state.alpha_test = 0;
        break;
    }
}

static void s_bind(void *context, int32_t bitmap)
{
    cloak_sink *s = context;
    s->texture = texture_slot(s->w, bitmap);
}

static void s_color4(void *context, float r, float g, float b, float a)
{
    cloak_sink *s = context;
    s->rgba[0] = r;
    s->rgba[1] = g;
    s->rgba[2] = b;
    s->rgba[3] = a;
}

static void s_begin(void *context, uint32_t mode)
{
    (void)mode;   /* GL_QUADS */
    cloak_sink *s = context;
    s->corner = 0;
    s->backend->prepare(s->backend->context, &s->state, s->texture);
    s->backend->begin(s->backend->context);
}

static void s_texcoord(void *context, float u, float v)
{
    cloak_sink *s = context;
    s->uv[s->corner][0] = u;
    s->uv[s->corner][1] = v;
}

static void s_vertex(void *context, float x, float y, float z)
{
    cloak_sink *s = context;
    s->xyz[s->corner][0] = x;
    s->xyz[s->corner][1] = y;
    s->xyz[s->corner][2] = z;
    if (++s->corner < 4)
        return;
    static const int order[6] = {0, 1, 2, 0, 2, 3};
    const mu_meshdraw_sink *k = &s->backend->sink;
    for (int i = 0; i < 6; ++i) {
        k->texcoord(k->context, s->uv[order[i]][0], s->uv[order[i]][1]);
        k->color4(k->context, s->rgba[0], s->rgba[1], s->rgba[2], s->rgba[3]);
        k->vertex(k->context, s->xyz[order[i]]);
    }
    s->corner = 0;
}

static void s_end(void *context)
{
    cloak_sink *s = context;
    s->backend->end(s->backend->context);
}

/* ---- the character's calls ---- */

static void host_of(mu_cloth_host *h, const mu_character *ch, float alpha)
{
    memset(h, 0, sizeof *h);
    h->bones = ch->player_bones;   /* OBJECT +0x318: the Player pose (RenderCharacter poses into the OBJECT's bones) */
    h->bone_count = ch->player_bone_count;
    h->has_model = ch->player_loaded;
    h->body_scale = ch->params.scale;   /* the Player model's BodyScale / BodyOrigin are the OBJECT's at its pose */
    memcpy(h->body_origin, ch->params.position, sizeof h->body_origin);
    memcpy(h->angles, ch->params.angles, sizeof h->angles);
    h->alpha = alpha;
}

static void move_cloth(world_cloak *w, cloak_slot *s, const mu_cloth_host *h)   /* MoveCloth 0x01362f24 */
{
    for (int i = 0; i < s->count; ++i) {
        if (!s->cloths[i].owner)
            continue;
        w->stats.steps++;
        if (!mu_cloth_move2(&s->cloths[i], h, &w->g, 0.005f, 5)) {
            s->count = 0;   /* DeleteCloth 0x0137aafe */
            return;
        }
    }
}

static void set_globals(const mu_world_rt *a, world_cloak *w)
{
    w->g.time = a->map ? a->map->time : 0.0f;   /* 0x06fce370 */
    w->g.logic_steps = (int32_t)a->walk.frame.clock.logic_steps;   /* 0x0bdc5eb0 */
    w->g.world = a->world;
}

static void wind_catch_up(mu_world_rt *a, world_cloak *w)
{
    const uint32_t steps = a->walk.frame.clock.logic_steps;
    if (!w->wind_started) {
        w->wind_at = steps;
        w->wind_started = 1;
    }
    uint32_t n = steps - w->wind_at;
    if (n > 1000)
        n = 1000;
    for (uint32_t k = 0; k < n; ++k)
        for (int j = 0; j < 5; ++j)   /* the frame driver's five manager steps 0x01851eee..0x01851f07 */
            mu_cloth_wind_step(&w->g);
    w->stats.wind_steps += n;
    w->wind_at = steps;
}

void world_cloak_draw(mu_world_rt *a, int32_t key, uint32_t generation, const mu_character *ch,
                      const mu_cloth_gate_in *gate, uint16_t action, uint16_t prior_action, float alpha,
                      mu_raster *raster, void *batch)
{
    const int16_t wing_type = gate->wing_type;
    if (key < 0 || key >= CLOAK_SLOTS || !ch || !ch->player_loaded)
        return;
    if (!a->cloak && !mu_cloth_wing_cloths(wing_type))   /* no state (and no report line) before a cloth wing */
        return;
    world_cloak *w = cloak_state(a);
    if (!w)
        return;
    cloak_slot *s = w->slots[key];
    if (!s) {
        if (!mu_cloth_wing_cloths(wing_type))   /* nothing to keep for a wing without a cloth case */
            return;
        s = w->slots[key] = calloc(1, sizeof *s);
        if (!s)
            return;
        s->wing = wing_type;
        s->generation = generation;
    }
    if (s->wing != wing_type || s->generation != generation) {   /* the OBJECT changed: its cloths go */
        s->count = 0;
        s->active = 0;
        s->wing = wing_type;
        s->generation = generation;
    }
    if (!w->wind_started)
        world_cloak_frame(a);
    set_globals(a, w);
    mu_cloth_host h;
    host_of(&h, ch, alpha);
    s->ch = ch;
    const uint32_t frame = a->walk.frame.clock.frames;
    if (!s->active || s->stepped != frame) {   /* first drawn frame: this frame's MoveCloth has not run */
        move_cloth(w, s, &h);
        s->stepped = frame;
    }
    s->active = 1;
    mu_cloth_gate_in in = *gate;
    in.world = a->world;
    mu_cloth_gate_out out;
    mu_cloth_gate(&in, &out);
    if (!out.render) {
        w->stats.gated++;
        return;
    }
    if (s->count == 0) {   /* RenderCloth: CreateCloth while the OBJECT has none, then its MoveCloth */
        s->count = mu_cloth_wing_create(s->cloths, wing_type, &h);
        w->stats.created += (uint32_t)s->count;
        if (s->count > 0)
            move_cloth(w, s, &h);
    }
    if (s->count == 0 || !mu_cloth_draw_allowed(action, prior_action, gate->class_index) || !load_textures(a, w))
        return;
    mu_render_backend backend;
    const mu_image *const *saved = NULL;
    int32_t saved_count = 0;
    const uint32_t *saved_filter = NULL, *saved_wrap = NULL;
    if (raster) {
        saved = raster->textures;
        saved_count = raster->texture_count;
        saved_filter = raster->texture_filter;
        saved_wrap = raster->texture_wrap;
        raster->textures = w->textures.slots;
        raster->texture_count = w->textures.count;
        raster->texture_filter = w->textures.filter;
        raster->texture_wrap = w->textures.wrap;
        mu_raster_backend(raster, &backend);
    } else {
#ifndef MU_WORLD_NO_GL
        if (!w->gl_ready) {
            memset(&w->gl, 0, sizeof w->gl);
            mu_gl_upload(&w->gl, &w->textures, 0);
            w->gl_ready = 1;
        }
        w->gl.batch = batch;
        mu_gl_backend_bind(&w->gl, &backend);
#else
        (void)batch;
        return;
#endif
    }
    cloak_sink sink;
    memset(&sink, 0, sizeof sink);
    sink.w = w;
    sink.backend = &backend;
    sink.texture = -1;
    mu_meshdraw_state_defaults(&sink.state);
    mu_cloth_sink cs = {&sink, s_state, s_bind, s_color4, s_begin, s_texcoord, s_vertex, s_end};
    for (int i = 0; i < s->count; ++i)
        if (s->cloths[i].owner && mu_cloth_render(&s->cloths[i], &h, out.light, &cs) == MU_CLOTH_OK)
            w->stats.drawn++;
    if (raster) {
        raster->textures = saved;
        raster->texture_count = saved_count;
        raster->texture_filter = saved_filter;
        raster->texture_wrap = saved_wrap;
    }
}

/* 1 while the slot's character is still drawn with the OBJECT its cloths were made for. */
static int slot_live(const mu_world_rt *a, int key, const cloak_slot *s)
{
    if (key == WORLD_CLOAK_HERO)
        return a->has_character && s->ch == &a->ch;
    const int32_t i = key - 1;
    if (!a->players || i >= a->players->count)
        return 0;
    const mu_world_player *q = &a->players->list[i];
    return s->ch == &q->model && q->creates == s->generation && mu_world_players_alpha(a->players, i) > 0.0f;
}

void world_cloak_frame(mu_world_rt *a)
{
    world_cloak *w = a->cloak;
    if (!w)
        return;
    wind_catch_up(a, w);
    set_globals(a, w);
    const uint32_t frame = a->walk.frame.clock.frames;
    for (int key = 0; key < CLOAK_SLOTS; ++key) {   /* RenderCharacter's MoveCloth 0x0136ab80 of this frame */
        cloak_slot *s = w->slots[key];
        if (!s || !s->active)
            continue;
        if (!slot_live(a, key, s)) {
            s->active = 0;
            continue;
        }
        if (s->count == 0 || s->stepped == frame)
            continue;
        mu_cloth_host h;
        host_of(&h, s->ch, 1.0f);
        move_cloth(w, s, &h);
        s->stepped = frame;
    }
}

void world_cloak_reset(mu_world_rt *a)
{
    world_cloak *w = a->cloak;
    if (!w)
        return;
    for (int i = 0; i < CLOAK_SLOTS; ++i) {
        free(w->slots[i]);
        w->slots[i] = NULL;
    }
}

void world_cloak_gl_teardown(mu_world_rt *a)
{
#ifndef MU_WORLD_NO_GL
    world_cloak *w = a->cloak;
    if (w && w->gl_ready) {
        mu_gl_release(&w->gl);
        w->gl_ready = 0;
    }
#else
    (void)a;
#endif
}

void world_cloak_free(mu_world_rt *a)
{
    world_cloak *w = a->cloak;
    if (!w)
        return;
    world_cloak_reset(a);
    mu_textures_free(&w->textures);
    free(w);
    a->cloak = NULL;
}

void world_cloak_stats_get(const mu_world_rt *a, world_cloak_stats *out)
{
    memset(out, 0, sizeof *out);
    const world_cloak *w = a->cloak;
    if (!w)
        return;
    *out = w->stats;
    out->wind = w->g.wind;
}
