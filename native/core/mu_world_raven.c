/* The Dark Raven in the walk-around world (NATIVE-HELPERS-002). See mu_world_raven.h. */
#include "mu_world_raven.h"

#include <math.h>
#include <string.h>

#include "mu_character.h"
#include "mu_particles.h"
#include "mu_walk.h"
#include "mu_world_helpers.h"
#include "mu_world_players.h"
#include "../../reconstructed/environment/env.h"
#include "../../reconstructed/movement/client_movement.h"
#include "../../reconstructed/objects/object_render.h"
#include "../../reconstructed/particles/particles.h"
#include "../../reconstructed/terrain/terrain.h"

int32_t mu_world_raven_hero_value(int32_t item, int32_t state)
{
    if (item != MU_RV_ITEM_DARK_RAVEN)
        return -1;
    return state >= 1 && state <= 3 ? state : 1;
}

/* the character model of an owner (bones of its last pose) */
static struct mu_character *owner_character(mu_world_raven *rv, int32_t owner)
{
    mu_world_helpers *w = rv->w;
    if (owner == 0)
        return w->hero_character;
    if (w->players && owner - 1 < w->players->count)
        return &w->players->list[owner - 1].model;
    return NULL;
}

/* ---------------------------------------------------------------- host */

static int h_has_model(void *c, int32_t index)
{
    mu_world_raven *rv = c;
    if (index == MU_RV_MODEL_PLAYER)
        return 1;   /* the owners' Player model (the characters draw it) */
    if (rv->w->no_assets)
        return 1;
    mu_wh_model *m = mu_world_helpers_model(rv->w, index);
    return m && m->loaded;
}

static int32_t h_action_keys(void *c, int32_t model, int32_t action)
{
    mu_world_raven *rv = c;
    (void)model;   /* the owner's Player model */
    struct mu_character *ch = owner_character(rv, 0);
    if (!ch || !ch->player_loaded || action < 0 || action >= ch->player_bmd.action_count)
        return 1;
    return ch->player_bmd.actions[action].keys;
}

static int h_animate(void *c, mu_rv_object *o, int32_t index, float speed)
{
    mu_world_raven *rv = c;
    mu_wh_model *m = mu_world_helpers_model(rv->w, index);
    if (!m || !m->loaded || m->bmd.action_count <= 0)
        return 1;
    uint8_t loop = 0;
    mu_model_set_state(&m->model, o->action, o->frame, o->prior_frame, o->prior_action);
    int r = mu_model_tick(&m->model, speed, &loop);
    (void)r;
    o->frame = mu_model_frame(&m->model);
    o->prior_frame = mu_model_prior_frame(&m->model);
    o->prior_action = mu_model_prior_action(&m->model);
    return loop;   /* the tick's AL */
}

static void h_set_action(void *c, mu_rv_object *o, int32_t action)
{
    mu_world_raven *rv = c;
    mu_wh_model *m = mu_world_helpers_model(rv->w, o->type);
    int32_t count = m && m->loaded ? m->bmd.action_count : 0;
    mu_move_set_action(&o->action, &o->prior_action, &o->frame, &o->prior_frame, count, action);
}

static int h_bone(void *c, int32_t which, int32_t owner, int32_t bone)
{
    mu_world_raven *rv = c;
    if (which == MU_RV_OWNER_OBJECT) {
        struct mu_character *ch = owner_character(rv, owner);
        return ch && ch->player_loaded && bone >= 0 && bone < ch->player_bone_count;
    }
    const mu_rv_pet *p = &rv->r.pets[owner];
    mu_wh_model *m = mu_world_helpers_model(rv->w, p->object.type);
    return m && m->loaded && bone >= 0 && bone < m->bmd.bone_count && mu_model_bone_matrices(&m->model);
}

/* the bone point VectorTransform(vector, bone) of an owner's Player pose (model space, translate 0 pose) */
static int owner_point(mu_world_raven *rv, int32_t owner, int32_t bone, const float v[3], float out[3])
{
    struct mu_character *ch = owner_character(rv, owner);
    if (!ch || !ch->player_loaded || !ch->player_bones || bone < 0 || bone >= ch->player_bone_count)
        return 0;
    mu_pt_transform_position(ch->player_bones + 12 * bone, v, out, 0, 1.0f, NULL);
    return 1;
}

static void h_transform(void *c, int32_t model, int32_t which, int32_t owner, int32_t bone, const float v[3],
                        float out[3], int translate)
{
    mu_world_raven *rv = c;
    (void)model;
    if (which == MU_RV_OWNER_OBJECT) {   /* translate 0 (the raven's perch): model space */
        if (owner_point(rv, owner, bone, v, out) && translate) {
            const mu_rv_owner *w = &rv->owners[owner];
            for (int k = 0; k < 3; ++k)
                out[k] = out[k] * w->scale + w->position[k];
        }
        return;
    }
    /* the sparkles: the pet's bone in the world. VIEWER CHOICE: the client takes the Player model's scale and
     * origin for a bone of the pet's own pose (static reading); the pet's own origin is used here. */
    const mu_rv_pet *p = &rv->r.pets[owner];
    mu_wh_model *m = mu_world_helpers_model(rv->w, p->object.type);
    if (m && m->loaded)
        mu_world_particles_bone_position(&m->model, bone, v, out);
}

static void h_transform_base(void *c, int32_t model, int32_t which, int32_t owner, int32_t bone, const float base[3],
                             const float v[3], float out[3])
{
    mu_world_raven *rv = c;
    (void)model, (void)which;
    float p[3];
    if (!owner_point(rv, owner, bone, v, p))
        return;
    float s = rv->owners[owner].scale;   /* 0x012b6d2a: BodyScale * VectorTransform + base */
    for (int k = 0; k < 3; ++k)
        out[k] = s * p[k] + base[k];
}

static void h_particle(void *c, int32_t bitmap, const float p[3], const float a[3], const float l[3], int32_t sub,
                       float scale)
{
    mu_world_raven *rv = c;
    rv->stats.sparkles++;
    if (rv->w->particles)
        mu_world_particles_create(rv->w->particles, bitmap, p, a, l, sub, scale);
}

static float h_terrain(void *c, float x, float y)
{
    mu_world_raven *rv = c;
    const mu_world *map = rv->w->map;
    return mu_request_terrain_height(map->height, map->attributes, map->water_height, 6, x, y);
}

static uint16_t h_wall(void *c, int32_t x, int32_t y)
{
    mu_world_raven *rv = c;
    const mu_world *map = rv->w->map;
    return map->attributes[(y & 0xff) * 256 + (x & 0xff)];   /* TerrainWall[0x016d34db(x, y)] */
}

static void h_body_angle(void *c, int32_t model, float angle[3])
{
    (void)c, (void)model;
    angle[0] = angle[1] = angle[2] = 0.0f;   /* the model's last RenderObject angle (+0x84): not tracked */
}

void mu_world_raven_init(mu_world_raven *rv, struct mu_world_helpers *w, uint32_t seed)
{
    memset(rv, 0, sizeof *rv);
    rv->w = w;
    mu_rv_host host;
    memset(&host, 0, sizeof host);
    host.context = rv;
    host.has_model = h_has_model;
    host.action_keys = h_action_keys;
    host.animate = h_animate;
    host.set_action = h_set_action;
    host.bone = h_bone;
    host.transform = h_transform;
    host.transform_base = h_transform_base;
    host.particle = h_particle;
    host.terrain_height = h_terrain;
    host.terrain_wall = h_wall;
    host.body_angle = h_body_angle;
    mu_rv_init(&rv->r, seed, rv->owners, MU_WH_OWNERS < MU_RV_OWNERS ? MU_WH_OWNERS : MU_RV_OWNERS, &host);
    rv->r.requested = 1;   /* offline: the pet-info request is never sent */
    for (int32_t i = 0; i < MU_RV_OWNERS; ++i)
        rv->applied[i] = -1;
}

/* ---------------------------------------------------------------- step */

static int32_t wanted(mu_world_raven *rv, int32_t owner)
{
    mu_world_helpers *w = rv->w;
    if (owner == 0)
        return w->walk ? mu_world_raven_hero_value(w->who[0].helper_item, w->who[0].ride_state) : -1;
    if (!w->players || owner - 1 >= w->players->count)
        return -1;
    const mu_world_player *q = &w->players->list[owner - 1];
    if (!q->in_view)
        return -1;
    /* DEMO: the pet byte the server sends for the character (the packet handler 0x01219294's call of 0x00c92bea) */
    return q->spec.raven >= 1 && q->spec.raven <= 3 ? q->spec.raven : -1;
}

static void sync_owner(mu_world_raven *rv, int32_t owner)
{
    mu_world_helpers *w = rv->w;
    const mu_hp_owner *h = &w->owners[owner];
    mu_rv_owner *o = &rv->owners[owner];
    struct mu_character *ch = owner_character(rv, owner);
    o->live = h->live;
    o->hero = (uint8_t)(owner == 0);
    o->safe = h->safe_zone;
    o->action = h->action;
    o->type = h->type;
    memcpy(o->position, h->position, sizeof o->position);
    o->tile[0] = (int32_t)(h->position[0] / 100.0f);
    o->tile[1] = (int32_t)(h->position[1] / 100.0f);
    o->ride = w->who[owner].ride == 0xffff ? 0 : w->who[owner].ride;
    o->scale = ch ? ch->params.scale : 1.0f;
    if (owner == 0 && w->walk)
        o->frame = w->walk->hero.frame;
    else if (owner > 0 && w->players && owner - 1 < w->players->count)
        o->frame = w->players->list[owner - 1].frame;
    o->buff_12 = h->buff_12;
    o->buff_3d = o->buff_b2 = o->buff_118 = 0;
    const mu_hp_mount *m = w->who[owner].key < 0 ? NULL : mu_hp_mount_find(&w->mounts, w->who[owner].key);
    o->has_mount = (uint8_t)(m != NULL);
    o->mount_offset_z = m ? m->offset[2] : 0.0f;
    o->mount_state2 = (uint8_t)(m && m->kind == 2);
    o->has_info = 1;   /* the hero's pet record: present, its level byte the level word (DEMO) */
    o->info_type = 5;
    o->info_level = (uint8_t)o->pet_level;
}

void mu_world_raven_step(mu_world_raven *rv)
{
    mu_world_helpers *w = rv->w;
    rv->inputs.world = w->map ? w->map->world : 0;
    rv->inputs.tick++;
    rv->stats.live = 0;
    for (int32_t owner = 0; owner < MU_WH_OWNERS && owner < MU_RV_OWNERS; ++owner) {
        int32_t want = wanted(rv, owner);
        sync_owner(rv, owner);
        if (want != rv->applied[owner]) {
            mu_rv_set_type(&rv->r, &rv->inputs, owner, (uint8_t)(want < 0 ? 0 : want));
            rv->applied[owner] = want;
            rv->stats.sets++;
            if (rv->r.pets[owner].live)
                rv->stats.creates++;
        }
        if (!rv->r.pets[owner].live || !rv->owners[owner].live)
            continue;
        mu_rv_move(&rv->r, &rv->inputs, owner);   /* MoveCharacter's per-character call 0x00c930df */
        rv->stats.moves++;
        rv->stats.live++;
    }
    rv->stats.steps++;
}

/* ---------------------------------------------------------------- draw */

typedef struct draw_context {
    mu_world_raven *rv;
    const mu_terrain_frustum *frustum;
    const mu_world_helpers_target *target;
    long drawn;
} draw_context;

static int r_frustum(void *c, float x, float y, float range)
{
    draw_context *d = c;
    if (!d->frustum)
        return 1;
    return mu_terrain_test_frustum_2d(d->frustum->x2d, d->frustum->y2d, 6, x, y, range);
}

static float d_sine(void *c, float x)
{
    (void)c;
    return (float)sin((double)x);
}

/* 0x0185bdc4(a, b) (static reading): ((cos-shaped wave of WorldTime) + 1) / 2 */
static float d_wave(void *c, float a, int32_t b)
{
    draw_context *d = c;
    float t = d->rv->world_time;
    float period = 6283.19f / a;
    int32_t ip = (int32_t)period;
    int32_t it = (int32_t)(((float)b * 0.0174533f * 1000.0f) / a + t);
    float x = (float)(ip ? it % ip : 0) * 0.001f * a;
    float cs = (float)cos((double)x);
    float v = 3.14159f <= x ? cs : -cs;
    return (v + 1.0f) * 0.5f;
}

/* 0x011ff622(lo, hi, steps) (static reading): lo + (rand() % (steps * (hi - lo))) / steps, clamped */
static float d_random_float(void *c, float lo, float hi, int32_t steps)
{
    draw_context *d = c;
    float span = (float)steps * (hi - lo);
    int32_t n = (int32_t)span;
    int32_t r = mu_rv_rand(&d->rv->r);
    float v = lo + (float)(n > 0 ? r % n : 0) / (float)steps;
    return v < lo ? lo : (v > hi ? hi : v);
}

static float d_terrain(void *c, float x, float y)
{
    draw_context *d = c;
    return h_terrain(d->rv, x, y);
}

/* RenderObject 0x016d4fe4 for the pet's OBJECT: the setup's pose, then the render registry's functor. */
static void r_object(void *c, const mu_rv_object *o, int32_t owner, int32_t a3)
{
    draw_context *d = c;
    mu_world_raven *rv = d->rv;
    mu_world_helpers *w = rv->w;
    (void)a3;
    mu_wh_model *m = mu_world_helpers_model(w, o->type);
    if (!m || !m->loaded || o->alpha <= 0.01f)
        return;
    mu_model_params p = m->model.params;
    for (int k = 0; k < 3; ++k) {
        p.origin[k] = o->position[k];
        p.angles[k] = o->angle[k];
    }
    float frame_light[3] = {0.0f, 0.0f, 0.0f};
    if (w->map)
        mu_obj_terrain_light(w->map->light, 6, 1, o->position[0], o->position[1], frame_light);
    mu_env_object e;   /* the body light 0x017ec3d8 (as the helpers' draw) */
    memset(&e, 0, sizeof e);
    e.flag_05 = o->lighting;
    memcpy(e.light, o->light, sizeof e.light);
    mu_env_body_light(&e, frame_light, p.color, &p.lighting);
    p.light_ambient = MU_ENV_LIGHT_AMBIENT;
    p.light_scale = MU_ENV_LIGHT_SCALE;
    p.light_minimum = MU_ENV_LIGHT_MINIMUM;
    p.body_scale = o->scale;
    p.pose_translate = 1;
    p.transform_translate = 0;
    mu_model_apply_params(&m->model, &p);
    mu_model_set_state(&m->model, o->action, o->frame, o->prior_frame, o->prior_action);
    if (mu_model_pose(&m->model) != MU_MODEL_OK || mu_model_transform_all(&m->model) != MU_MODEL_OK)
        return;
    mu_rv_draw_inputs in;
    memset(&in, 0, sizeof in);
    in.world = rv->inputs.world;
    in.time = rv->world_time;
    in.dim_world = (uint8_t)(in.world == 7 || (in.world >= 0x80 && in.world <= 0x82));
    memcpy(in.color, p.color, sizeof in.color);
    mu_rv_draw_host h = {d, d_sine, d_wave, d_random_float, d_terrain};
    mu_rv_draw_list list;
    mu_rv_object copy = *o;
    if (o->type == MU_RV_MODEL_SOUL) {
        mu_rv_draw_soul(&copy, &in, &h, &list);
        rv->r.pets[owner].object.angle[2] = copy.angle[2];   /* the functor turns the soul */
        rv->stats.souls++;
    } else {
        mu_rv_draw_raven(o, &in, &h, &list);
    }
    rv->stats.drawn++;
    if (!d->target)
        return;
    mu_render_backend backend;
    int32_t slot = mu_world_helpers_model_slot(w, m);
    if (d->target->backend(d->target->context, w, slot, &backend))
        return;
    for (int32_t i = 0; i < list.count; ++i) {
        const mu_rv_draw *e = &list.items[i];
        if (e->kind == MU_RV_DRAW_BODY || e->kind == MU_RV_DRAW_MESH) {
            if (e->texture >= 0) {   /* VIEWER CHOICE: the overlay bitmaps 0x7fa5 / 0x7f1f are not loaded */
                rv->stats.skipped++;
                continue;
            }
            mu_draw_options options;
            mu_draw_default_options(&options);
            options.textures = &m->textures;
            options.flags = (uint32_t)e->flags;
            options.alpha = e->alpha < 1.0f ? e->alpha : 1.0f;
            options.select = e->blend_mesh;
            options.color_scale = e->blend_light;
            options.u_offset = e->uv[0];
            options.v_offset = e->uv[1];
            options.mesh_plus_one = e->kind == MU_RV_DRAW_MESH ? e->mesh + 1 : 0;
            if (e->kind == MU_RV_DRAW_BODY)
                options.skip_mesh = e->hidden;
            options.time = rv->world_time;
            mu_draw_model_fields fields;
            memset(&fields, 0, sizeof fields);
            memcpy(fields.color, e->color, sizeof fields.color);
            options.fields = &fields;
            mu_draw_stats ds = {0, 0, 0, 0};
            if (!mu_scene_draw_model(&m->model, &options, &backend, &ds))
                rv->stats.draws++;
        } else if (e->kind == MU_RV_DRAW_SPRITE && w->particles) {
            mu_world_particles_sprite(w->particles, e->bitmap, e->vector, e->scale, e->light, -1, 0.0f, 0, 4);
            rv->stats.sprites++;
        } else if (e->kind == MU_RV_DRAW_PARTICLE && w->particles) {
            mu_world_particles_create(w->particles, e->bitmap, e->vector, o->angle, e->light, e->subtype, e->scale);
            rv->stats.particles++;
        } else if (e->kind == MU_RV_DRAW_SHADOW && d->target->shadow) {
            const float rgba[4] = {0.0f, 0.0f, 0.0f, e->alpha};
            d->target->shadow(d->target->context, w, slot, rgba);
            rv->stats.shadows++;
        }
    }
    d->drawn++;
}

long mu_world_raven_draw(mu_world_raven *rv, const mu_terrain_frustum *frustum, const mu_world_helpers_target *target)
{
    draw_context d = {rv, frustum, target, 0};
    mu_rv_render_host rh = {&d, r_frustum, r_object};
    rv->world_time += 40.0f;
    for (int32_t owner = 0; owner < MU_WH_OWNERS && owner < MU_RV_OWNERS; ++owner)
        if (rv->r.pets[owner].live && rv->owners[owner].live)
            mu_rv_render(&rv->r, &rv->inputs, owner, &rh);   /* RenderCharacter's call 0x00c9314f */
    return d.drawn;
}

void mu_world_raven_report_frame(const mu_world_raven *rv, FILE *out)
{
    for (int32_t owner = 0; owner < MU_RV_OWNERS; ++owner) {
        const mu_rv_pet *p = &rv->r.pets[owner];
        if (!p->live)
            continue;
        fprintf(out, "{\"raven\": %d, \"model\": %d, \"ai\": %d, \"action\": %d, \"alpha\": %.2f, \"position\": [%.1f, %.1f, %.1f], \"angle\": [%.1f, %.1f], \"direction\": [%.2f, %.2f]}\n",
                owner, p->object.type, p->object.ai, p->object.action, (double)p->object.alpha,
                (double)p->object.position[0], (double)p->object.position[1], (double)p->object.position[2], (double)p->object.angle[0], (double)p->object.angle[2], (double)p->object.direction[1], (double)p->object.direction[2]);
    }
}

void mu_world_raven_report_summary(const mu_world_raven *rv, FILE *out)
{
    const mu_world_raven_stats *s = &rv->stats;
    fprintf(out, "{\"raven\": {\"steps\": %u, \"sets\": %u, \"creates\": %u, \"moves\": %u, \"live\": %u, \"drawn\": %u,"
                 " \"souls\": %u, \"sparkles\": %u, \"sprites\": %u, \"particles\": %u, \"shadows\": %u, \"draws\": %u,"
                 " \"skipped\": %u, \"rand_calls\": %llu}}\n",
            s->steps, s->sets, s->creates, s->moves, s->live, s->drawn, s->souls, s->sparkles, s->sprites,
            s->particles, s->shadows, s->draws, s->skipped, (unsigned long long)rv->r.rand_calls);
}
