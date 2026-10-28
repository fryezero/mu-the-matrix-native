/* Weather particles: MoveLeaves 0x01537a43 with the creators and movers of
 * the ported worlds, RenderLeaves 0x01538145 (NATIVE-ENV-001). */
#include "env.h"
#include "env_internal.h"
#include "../record-math/record_math.h"

static uint16_t att(const mu_env_inputs *in, int32_t tile)
{
    return in->attributes ? in->attributes[(uint32_t)tile & 0xffffu] : 0;
}

static uint8_t layer(const mu_env_inputs *in, int32_t tile)
{
    return in->layer1 ? in->layer1[(uint32_t)tile & 0xffffu] : 0;
}

static void particle(mu_env *env, int32_t bitmap, const mu_env_leaf *l)
{
    if (env->host.create_particle)
        env->host.create_particle(env->host.context, bitmap, l->position, l->angle, l->light, 0, 1.0f);
}

/* Position around the hero: x + rand()%1600 - 800, y + rand()%1400 - 500. */
static void around_xy(mu_env *env, const mu_env_inputs *in, float out[2])
{
    out[0] = (float)(mu_env_rand(env) % 1600 - 800) + in->hero_position[0];
    out[1] = (float)(mu_env_rand(env) % 1400 - 500) + in->hero_position[1];
}

/* 0x0153959d (world 0) and 0x01539ace (worlds 3, 7, 0x80..0x82): drifting leaf. */
static void create_drift(mu_env *env, const mu_env_inputs *in, mu_env_leaf *l)
{
    float p[3];
    l->texture = MU_ENV_BITMAP_LEAF1;
    around_xy(env, in, p);
    p[2] = (float)(mu_env_rand(env) % 300 + 50) + in->hero_position[2];
    for (int k = 0; k < 3; ++k)
        l->position[k] = p[k];
    for (int k = 0; k < 3; ++k)
        l->start[k] = p[k];
    l->velocity[0] = -(float)(mu_env_rand(env) % 64 + 64) * 0.1f;
    if (MU_ENV_MUTATION != 5 && in->camera_position[1] + 400.0f > p[1])
        l->velocity[0] = -l->velocity[0] + 3.2f;
    l->velocity[1] = (float)(mu_env_rand(env) % 32 - 16) * 0.1f;
    l->velocity[2] = (float)(mu_env_rand(env) % 32 - 16) * 0.1f;
    l->turn[0] = (float)(mu_env_rand(env) % 16 - 8) * 0.1f;
    l->turn[1] = (float)(mu_env_rand(env) % 64 - 32) * 0.1f;
    l->turn[2] = (float)(mu_env_rand(env) % 16 - 8) * 0.1f;
}

/* 0x0153939c (world 2): snow, one big flake (leaf02, scale 10) in ten. */
static void create_snow(mu_env *env, const mu_env_inputs *in, mu_env_leaf *l)
{
    l->texture = MU_ENV_BITMAP_LEAF1;
    l->scale = MU_ENV_MUTATION == 6 ? 6.0f : 5.0f;
    if (mu_env_rand(env) % 10 == 0) {
        l->texture = MU_ENV_BITMAP_LEAF2;
        l->scale = 10.0f;
    }
    float p[2];
    around_xy(env, in, p);
    l->position[0] = p[0];
    l->position[1] = p[1];
    l->position[2] = (float)(mu_env_rand(env) % 200 + 200) + in->hero_position[2];
    l->angle[0] = -30.0f;
    l->angle[1] = 0.0f;
    l->angle[2] = 0.0f;
    float v[3] = {0.0f, 0.0f, -(float)(mu_env_rand(env) % 16 + 8)}, m[3][4];
    mu_angle_matrix(l->angle, m);
    mu_vector_rotate(v, m, l->velocity);
}

/* 0x015398de (worlds 0xa, 0x84): rain for index < rain level * 200 / 100. */
static int create_icarus_rain(mu_env *env, const mu_env_inputs *in, mu_env_leaf *l, int32_t index)
{
    int32_t limit = (int32_t)((uint32_t)env->rain_level * 200u) / 100;
    if (index >= limit)
        return 0;
    l->texture = MU_ENV_BITMAP_RAIN;
    float p[2];
    around_xy(env, in, p);
    l->position[0] = p[0];
    l->position[1] = p[1];
    l->position[2] = (float)(mu_env_rand(env) % 200 + 200) + in->hero_position[2];
    l->angle[0] = -30.0f;
    l->angle[1] = 0.0f;
    l->angle[2] = 0.0f;
    float v[3] = {0.0f, 0.0f, -(float)(mu_env_rand(env) % 24 + 20)}, m[3][4];
    mu_angle_matrix(l->angle, m);
    mu_vector_rotate(v, m, l->velocity);
    return 1;
}

/* Tormenta Island rain 0x00e53c14: created, moved once, and on the ground
 * half of the time at once (splash 0x771c one time in four, else 0x771d). */
static void create_tormenta_drop(mu_env *env, const mu_env_inputs *in, mu_env_leaf *l)
{
    l->texture = MU_ENV_BITMAP_RAIN;
    float p[2];
    around_xy(env, in, p);
    l->position[0] = p[0];
    l->position[1] = p[1];
    l->position[2] = (float)(mu_env_rand(env) % 300) + in->hero_position[2] + 50.0f;
    l->angle[0] = -60.0f;
    l->angle[1] = 10.0f;
    l->angle[2] = 0.0f;
    float v[3] = {0.0f, 0.0f, -(float)(mu_env_rand(env) % 24 + 30)}, m[3][4];
    mu_angle_matrix(l->angle, m);
    mu_vector_rotate(v, m, l->velocity);
    for (int k = 0; k < 3; ++k)
        l->position[k] = l->position[k] + l->velocity[k];
    int32_t tile = env_tile_index(mu_env_cvttss2si(l->position[0] / 100.0f),
                                  mu_env_cvttss2si(l->position[1] / 100.0f));
    if ((att(in, tile) & 8) || layer(in, tile) == 0xe)
        return;
    float h = env_terrain(env, l->position[0], l->position[1]);
    if (mu_env_rand(env) % 2 == 0)
        return;
    l->live = 0;
    l->position[2] = h + 10.0f;
    if (mu_env_rand(env) % 4 == 0) {
        particle(env, MU_ENV_BITMAP_RAIN_SPLASH, l);
    } else {
        l->light[0] = l->light[1] = l->light[2] = 0.9f;
        particle(env, MU_ENV_BITMAP_RAIN_RING, l);
    }
}

/* Tormenta world class, vtable slot 0x64 (0x00e5377c). */
static int create_tormenta(mu_env *env, const mu_env_inputs *in, mu_env_leaf *l)
{
    if (!env_tormenta(in->world))
        return 0;
    mu_env_world_object *t = &env->tormenta;
    int32_t tile = env_tile_index(in->hero_tile[0], in->hero_tile[1]);
    if (att(in, tile) & 0x800) {
        t->rain = in->frame_time * (MU_ENV_MUTATION == 7 ? 0.2f : 0.3f) + t->rain;
        t->rain = t->rain >= t->rain_max ? t->rain_max : t->rain;
    } else {
        t->rain = t->rain - in->frame_time * 0.15f;
        t->rain = 0.0f >= t->rain ? 0.0f : t->rain;
    }
    float room = t->rain_max + 1.0f - t->rain;
    if (0.0f >= room || 0.0f >= t->rain) {
        l->live = 0;
    } else if (mu_env_rand(env) % mu_env_cvttss2si(room) == 0) {
        create_tormenta_drop(env, in, l);
    }
    return 1;
}

static void add3(float a[3], const float b[3])
{
    a[0] = a[0] + b[0];
    a[1] = a[1] + b[1];
    a[2] = a[2] + b[2];
}

static void jitter(mu_env *env, float v[3], int32_t span, int32_t half, float factor)
{
    v[0] = (float)(mu_env_rand(env) % span - half) * factor + v[0];
    v[1] = (float)(mu_env_rand(env) % span - half) * factor + v[1];
    v[2] = (float)(mu_env_rand(env) % span - half) * factor + v[2];
}

/* 0x0153a634 (worlds 0, 0xa, 0x84). */
static int move_lorencia(mu_env *env, const mu_env_inputs *in, mu_env_leaf *l)
{
    const int32_t w = in->world;
    if (!(w == 0 || w == 0xa || w == 0x84))
        return 0;
    if (l->texture == MU_ENV_BITMAP_RAIN) {
        add3(l->position, l->velocity);
        float h = env_terrain(env, l->position[0], l->position[1]);
        if (h > l->position[2]) {
            l->live = 0;
            l->position[2] = h + 10.0f;
            if (w != 0xa && w != 0x84)
                particle(env, MU_ENV_BITMAP_RAIN_SPLASH, l);
        }
        return 1;
    }
    jitter(env, l->velocity, 16, 8, 0.1f);
    add3(l->position, l->velocity);
    l->turn[0] = (float)(mu_env_rand(env) % 8 - 4) * 0.02f + l->turn[0];
    l->turn[1] = (float)(mu_env_rand(env) % 16 - 8) * 0.02f + l->turn[1];
    l->turn[2] = (float)(mu_env_rand(env) % 8 - 4) * 0.02f + l->turn[2];
    add3(l->angle, l->turn);
    float d[3] = {l->start[0] - l->position[0], l->start[1] - l->position[1], l->start[2] - l->position[2]};
    float dd = d[0] * d[0] + d[1] * d[1] + d[2] * d[2];
    if (dd >= 200000.0f)
        l->live = 0;
    return 1;
}

/* Tormenta world class, vtable slot 0x68 (0x00e538ec). */
static int move_tormenta(mu_env *env, const mu_env_inputs *in, mu_env_leaf *l)
{
    if (!env_tormenta(in->world))
        return 0;
    jitter(env, l->velocity, 16, 8, 0.1f);
    add3(l->position, l->velocity);
    l->alpha = l->alpha + 0.03f;
    float h = env_terrain(env, l->position[0], l->position[1]);
    if (h >= l->position[2]) {
        l->light[0] = l->light[0] - 0.3f;
        l->light[1] = l->light[1] - 0.3f;
        l->light[2] = l->light[2] - 0.3f;
        if (0.0f >= l->light[0])
            l->live = 0;
    }
    return 1;
}

/* 0x0153ac06: ground contact fades the light, otherwise a random walk. */
static void move_default(mu_env *env, mu_env_leaf *l)
{
    float h = env_terrain(env, l->position[0], l->position[1]);
    if (h >= l->position[2]) {
        l->position[2] = h;
        l->light[0] = l->light[0] - (MU_ENV_MUTATION == 9 ? 0.04f : 0.05f);
        l->light[1] = l->light[1] - (MU_ENV_MUTATION == 9 ? 0.04f : 0.05f);
        l->light[2] = l->light[2] - (MU_ENV_MUTATION == 9 ? 0.04f : 0.05f);
        if (0.0f >= l->light[0])
            l->live = 0;
    } else {
        jitter(env, l->velocity, 16, 8, 0.1f);
        add3(l->position, l->velocity);
    }
}

static int32_t leaf_count(const mu_env *env, const mu_env_inputs *in, int32_t *rain_target)
{
    const int32_t w = in->world;
    int32_t count = env_devil_square(w) ? 200 : 80;
    int32_t tile = env_tile_index(in->hero_tile[0], in->hero_tile[1]);
    (void)env;
    if (w == 0xa || w == 0x84) {
        *rain_target = 100;
    } else if (env_chaos_castle(w)) {
        *rain_target = 100;
        count = 80;
    } else if (w == 0x1e) {
        count = 40;
    } else if (w == 0x37) {
        count = 80;
    } else if (w == 0x22) {
        if (in->event_state == 1)
            count = 60;
        else if (in->event_state == 2)
            count = 50;
    } else if (w == 0x64 || w == 0x65) {
        uint16_t a = att(in, tile);
        count = (a & 0x800) ? 80 : (a & 0x1000) ? 100 : 0;
    } else if (w == 0x6e || w == 0x6f) {
        if (!(att(in, tile) & 0x800))
            count = 0;
    } else if (w == 0x71) {
        count = 200;
    } else if (w == 0x7a) {
        count = (att(in, tile) & 0x800) ? 80 : 100;
    } else if (w == 0x83 || w == 0x85 || w == 0x88 || w == 0x8d || w == 0x8e) {
        count = 80;
    }
    return count;
}

int mu_env_move_leaves(mu_env *env, const mu_env_inputs *in)
{
    const int32_t w = in->world;
    int32_t count = leaf_count(env, in, &env->rain_target);
    if (env->rain_level > env->rain_target)
        env->rain_level--;
    else if (env->rain_level < env->rain_target)
        env->rain_level++;
    env->wind_8ca8 = (int32_t)((uint32_t)mu_env_cvttss2si(env_sin(in->world_time * 0.001f)) * 10u + 30u);
    env->wind_8cac = (int32_t)((uint32_t)mu_env_cvttss2si(env_sin(in->world_time * 0.0005f + 50.0f)) * 20u);
    env->wind_8cb0 = (int32_t)((uint32_t)env->wind_8cb0 + 20u) % 2000;
    for (int32_t i = 0; i < count; ++i) {
        mu_env_leaf *l = &env->leaves[i];
        if (!l->live) {
            l->light[0] = l->light[1] = l->light[2] = 1.0f;
            l->live = 1;
            /* 0x01538c67 / 0x01538feb (Devil Square, Chaos Castle rain) are not ported. */
            if (w == 0) {
                create_drift(env, in, l);
                continue;
            }
            if ((w == 0xa || w == 0x84) && create_icarus_rain(env, in, l, i))
                continue;
            if (w == 2) {
                create_snow(env, in, l);
                continue;
            }
            if (w == 57 || w == 58) {
                mu_env_raklion_snow(env, in, l);
                continue;
            }
            if (w == 3 || env_atlans(w)) {
                create_drift(env, in, l);
                continue;
            }
            /* the event-world creators return 0 outside their worlds; the
             * world manager reaches the Tormenta class */
            if (create_tormenta(env, in, l))
                continue;
            continue;
        }
        if (move_lorencia(env, in, l))
            continue;
        if (move_tormenta(env, in, l))
            continue;
        move_default(env, l);
    }
    return 1;
}

int mu_env_leaves_active(int32_t world, int32_t hero_tile, int world_object_weather)
{
    const int32_t w = world;
    if (w == 0 && hero_tile != 4)
        return 1;
    if (w == 2 && hero_tile != 3 && hero_tile < 10)
        return 1;
    if (w == 3 || w == 7 || env_devil_square(w) || (w >= 0x67 && w <= 0x6a) || w == 0xa || env_chaos_castle(w) ||
        w == 0x1e || w == 0x1f || w == 0x21 || w == 0x36 || w == 0x22 || w == 0x2a || env_event_leaf_world(w) ||
        w == 0x5f || w == 0x60 || w == 0x64 || w == 0x65 || w == 0x6e || w == 0x6f || w == 0x71 || w == 0x72 ||
        w == 0x79 || w == 0x7a || (w >= 0x7b && w <= 0x7f) || env_abyss(w) || w == 0x83 || w == 0x84 || w == 0x85)
        return 1;
    return world_object_weather != 0;
}

/* RenderPlane3D 0x0184c121: corners (-w,-w,-h), (w,w,-h), (w,w,h), (-w,-w,h)
 * through VectorTransform 0x00d002b2 with the angle matrix (translation 0). */
static void plane(const mu_env_render_host *r, const mu_env_leaf *l, float width, float height)
{
    float m[3][4], c[4][3];
    const float local[4][3] = {{-width, -width, -height}, {width, width, -height}, {width, width, height},
                               {-width, -width, height}};
    mu_angle_matrix(l->angle, m);
    for (int k = 0; k < 4; ++k)
        mu_vector_transform(local[k], m, c[k]);
    if (r->plane)
        r->plane(r->context, l->position, (const float(*)[3])c, 1);
}

void mu_env_render_leaves(mu_env *env, const mu_env_inputs *in, const mu_env_render_host *r)
{
    const int32_t w = in->world;
    if (w == 2 || w == 7 || w == 0xa || (w >= 0x39 && w <= 0x3a) || w == 0x3e || w == 0x3f ||
        (w >= 0x52 && w <= 0x5a) || w == 0x45 || w == 0x46 || w == 0x47 || w == 0x4f || w == 0x5f || w == 0x60 ||
        w == 0x64 || w == 0x65 || w == 0x6e || w == 0x6f || w == 0x71 || w == 0x72 || w == 0x79 || w == 0x7a ||
        (w >= 0x7b && w <= 0x7f) || env_abyss(w) || w == 0x83 || w == 0x84 || w == 0x85 || w == 0x88 || w == 0x89 ||
        w == 0x8a || w == 0x8c || w == 0x8d || w == 0x90) {
        if (r->alpha_blend)
            r->alpha_blend(r->context);
    } else if (env_chaos_castle(w)) {
        if (r->alpha_test)
            r->alpha_test(r->context, 1);
    } else if (w == 0x1e || w == 0x37 || w == 0x2a) {
        if (r->alpha_blend)
            r->alpha_blend(r->context);
    } else if (w == 0x8f) {
        return;
    } else if (r->alpha_test) {
        r->alpha_test(r->context, 1);
    }
    int32_t count = 200, tile = env_tile_index(in->hero_tile[0], in->hero_tile[1]);
    if (w == 0x64 || w == 0x65) {
        uint16_t a = att(in, tile);
        count = (a & 0x800) ? 80 : (a & 0x1000) ? 100 : 0;
    } else if (w == 0x6e || w == 0x6f) {
        if (!(att(in, tile) & 0x800))
            count = 0;
    } else if (w == 0x7a) {
        count = (att(in, tile) & 0x800) ? 80 : 100;
    } else if (w == 0x85) {
        count = 80;
    } else if (w == 0x8b) {
        count = 0;
    } else if (w == 0x8d || w == 0x8e) {
        count = 80;
    }
    if (r->color3)
        r->color3(r->context, 1.0f, 1.0f, 1.0f);
    for (int32_t i = 0; i < count; ++i) {
        const mu_env_leaf *l = &env->leaves[i];
        if (!l->live)
            continue;
        if (r->has_bitmap && !r->has_bitmap(r->context, l->texture))
            continue;
        if (r->bind)
            r->bind(r->context, l->texture);
        if (w == 2 || (w >= 0x39 && w <= 0x3a) || w == 0x3e || w == 0x79) {
            if (r->billboard)
                r->billboard(r->context, l->texture, l->position, l->scale, l->scale, l->light);
            continue;
        }
        if (w == 0x71)
            continue;   /* rotated sprites by the hero tile, not ported */
        if (w == 0x83 || w == 0x88) {
            if (att(in, tile) & 0x800) {
                if (r->color3)
                    r->color3(r->context, l->alpha, l->alpha, l->alpha);
                plane(r, l, l->scale * 2.0f, l->scale * 4.0f);
            }
            continue;
        }
        if (w == 0x84) {
            if (r->color3)
                r->color3(r->context, 0.7f, 0.7f, 0.7f);
            plane(r, l, 1.0f, 20.0f);
            continue;
        }
        /* the world manager's render (Tormenta: slot 0x6c returns 0) */
        if (env_chaos_castle(w))
            plane(r, l, l->turn[0], l->turn[1]);
        else if (l->texture == MU_ENV_BITMAP_RAIN) {
            if (w != 0x22 || in->event_state == 1)
                plane(r, l, 1.0f, 20.0f);
        } else if (l->texture == 0x7fe8)
            plane(r, l, l->scale * 2.0f, l->scale * 4.0f);
        else
            plane(r, l, 3.0f, 3.0f);
    }
}

void mu_env_billboard_quad(const float camera[3][4], const float position[3], float width, float height,
                           float out[4][3])
{
    float p[3];
    mu_vector_transform(position, camera, p);
    const float w = width * 0.5f, h = height * 0.5f;
    out[0][0] = p[0] - w; out[0][1] = p[1] - h; out[0][2] = p[2];
    out[1][0] = p[0] + w; out[1][1] = p[1] - h; out[1][2] = p[2];
    out[2][0] = p[0] + w; out[2][1] = p[1] + h; out[2][2] = p[2];
    out[3][0] = p[0] - w; out[3][1] = p[1] + h; out[3][2] = p[2];
}

int mu_env_billboard_color(int32_t bitmap, int32_t components, const float light[3], float rgba[4])
{
    rgba[0] = light[0];
    rgba[1] = light[1];
    rgba[2] = light[2];
    rgba[3] = 1.0f;
    if (components == 3)
        return 3;
    if (bitmap != 0x7f49 && bitmap != 0x7df3)
        rgba[3] = light[0];
    return 4;
}
