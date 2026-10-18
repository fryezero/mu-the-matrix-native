/* Ambient swimmers and crawlers: MoveFishs 0x00ca05b3 and RenderFishs
 * 0x00ca1cf7 (NATIVE-ENV-001). */
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

static int32_t tile_of(const float position[3])
{
    return env_tile_index(mu_env_cvttss2si(position[0] / 100.0f), mu_env_cvttss2si(position[1] / 100.0f));
}

/* 0x012afd99: the models MoveFishs steers. */
static int fish_type(int32_t type)
{
    static const int32_t list[13] = {0x198, 0x199, 0x19a, 0x19b, 0x19c, 0x19d, 0x19e, 0x19f, 0x1a0,
                                     0x196, 0x197, 0x198, 0x1b3};
    for (int i = 0; i < 13; ++i)
        if (type == list[i])
            return 1;
    return 0;
}

static int spawn_allowed(const mu_env_inputs *in, int32_t tile)
{
    const int32_t w = in->world;
    const uint16_t a = att(in, tile);
    if (w == 0 && layer(in, tile) == 5)
        return 1;
    if (w == 1 && a < 8)
        return 1;
    if (w == 6 && a < 8)
        return 1;
    if (w == 7 && (a == 0 || a == 2))
        return 1;
    if (env_kalima(w) && (a == 0 || a == 2))
        return 1;
    if ((w == 0x21 || w == 0x36) && (a == 0 || a == 2))   /* 0x00d61f81 */
        return 1;
    if ((w == 8 || w == 0x22) && (a == 0 || a == 2))
        return 1;
    if (env_deep_dungeon(w) && a < 8)
        return 1;
    if (env_abyss(w) && ((a & 0x800) || (a & 0x1000)))
        return 1;
    if (w == 0x85)   /* 0x00d83ada */
        return 1;
    if (w == 0x86)   /* 0x00d8b139 */
        return a == 0 || a == 2;
    return 0;
}

static void copy3(float out[3], const float in[3])
{
    out[0] = in[0];
    out[1] = in[1];
    out[2] = in[2];
}

static void effect(mu_env *env, int32_t bitmap, const mu_env_object *o, float scale, int32_t argument)
{
    if (env->host.create_effect)
        env->host.create_effect(env->host.context, bitmap, o, scale, argument);
}

static void spawn(mu_env *env, const mu_env_inputs *in, mu_env_object *o, int32_t tile)
{
    const int32_t w = in->world;
    env_set_live(env, o, 1);
    o->alpha = 0.0f;
    o->alpha_target = 1.0f;
    o->field_74 = -1;
    o->light[0] = o->light[1] = o->light[2] = 0.5f;
    o->angle[0] = o->angle[1] = o->angle[2] = 0.0f;
    o->flag_05 = 1;
    o->alpha_enable = 1;
    o->subtype = 0;
    o->field_68 = -1;
    o->timer = mu_env_rand(env) % 128;
    o->velocity = (float)(mu_env_rand(env) % 4 + 4) * 0.1f;
    o->gravity = 13.0f;
    o->flag_01 = 1;
    switch (w) {
    case 0:
        o->type = MU_ENV_MODEL_FISH;
        o->alpha_target = (float)(mu_env_rand(env) % 2 + 2) * 0.1f;
        o->scale = 0.6f / o->velocity;
        break;
    case 1:
    case 0x74: case 0x75: case 0x76: case 0x77: case 0x78:
        o->type = MU_ENV_MODEL_RAT;
        o->scale = 0.6f / o->velocity;
        break;
    case 6:
        o->type = MU_ENV_MODEL_BUG;
        o->scale = 0.6f / o->velocity;
        break;
    case 8:
    case 0x21:
    case 0x86:
        o->type = MU_ENV_MODEL_FISH;
        o->velocity = (float)(mu_env_rand(env) % 4 + 8) * 0.1f;
        o->scale = 2.5f / o->velocity;
        o->gravity = 9.0f;
        o->timer = 100;
        copy3(o->start, o->position);
        effect(env, 0x7fd6, o, 30.0f, 4);
        break;
    case 0x22:
        if (!in->hero_safe_zone) {
            o->type = 0x1b3;
            o->velocity = (float)(mu_env_rand(env) % 4 + 8) * 0.1f;
            o->scale = (float)(mu_env_rand(env) % 8 + 1) * 0.1f / o->velocity;
            copy3(o->start, o->position);
            o->gravity = 1.0f;
            o->timer = 100;
            effect(env, 0x7ff9, o, 30.0f, 0);
        } else {
            env_set_live(env, o, 0);
        }
        break;
    case 7:
        o->velocity = (float)(mu_env_rand(env) % 2 + 8) * 0.1f;
        if (128.0f > in->hero_position[1] * 0.01f) {
            o->type = mu_env_rand(env) % 4 + 0x19b;
            o->scale = 1.0f / o->velocity;
            o->gravity = mu_env_rand(env) % 2 == 0 ? 2.0f : 3.0f;
        } else {
            o->type = mu_env_rand(env) % 2 + 0x19f;
            if (o->type == 0x19f || o->type == 0x1a0) {
                o->field_74 = 0;
                o->field_a8 = 1.0f;
            }
            o->scale = 0.5f / o->velocity;
            o->gravity = mu_env_rand(env) % 2 == 0 ? 1.0f : 2.0f;
        }
        o->phase = (float)(mu_env_rand(env) % 32) * 0.1f;
        {
            float h = env_terrain(env, o->position[0], o->position[1]);
            o->position[2] = h + (float)(mu_env_rand(env) % 150 + 50);
        }
        break;
    case 0x80:
    case 0x81:
    case 0x82: {
        o->velocity = (float)(mu_env_rand(env) % 2 + 8) * 0.1f;
        uint16_t a = att(in, tile);
        if (a & 0x800) {
            o->type = mu_env_rand(env) % 4 + 0x19b;
            o->scale = 1.0f / o->velocity;
            o->gravity = (float)(mu_env_rand(env) % 2 + 2);
        } else if (a & 0x1000) {
            o->type = mu_env_rand(env) % 2 + 0x19f;
            if (o->type == 0x19f || o->type == 0x1a0) {
                o->field_74 = 0;
                o->field_a8 = 1.0f;
            }
            o->scale = 0.5f / o->velocity;
            o->gravity = (float)(mu_env_rand(env) % 2 + 1);
        }
        o->phase = (float)(mu_env_rand(env) % 32) * 0.1f;
        {
            float h = env_terrain(env, o->position[0], o->position[1]);
            o->position[2] = h + (float)(mu_env_rand(env) % 150 + 50);
        }
        break;
    }
    case 0x85:
        o->alpha_target = (float)(mu_env_rand(env) % 2 + 2) * 0.1f;
        o->velocity = (float)(mu_env_rand(env) % 2 + 8) * 0.1f;
        o->type = mu_env_rand(env) % 6 + 0x199;
        o->scale = 1.0f / o->velocity;
        o->gravity = (float)(mu_env_rand(env) % 2 + 2);
        o->phase = (float)(mu_env_rand(env) % 32) * 0.1f;
        o->position[2] = -(float)(mu_env_rand(env) % 20);
        break;
    default:
        break;
    }
    if (env_kalima(w)) {
        o->type = -1;
        o->velocity = (float)(mu_env_rand(env) % 4 + 8) * 0.1f;
        o->scale = 2.5f / o->velocity;
        o->gravity = 9.0f;
        o->timer = 0x46;
        effect(env, 0x7f79, o, 50.0f, 8);
    }
}

static void turn_around(mu_env_object *o)
{
    o->angle[2] = o->angle[2] + 180.0f;
    if (o->angle[2] >= 360.0f)
        o->angle[2] = o->angle[2] - 360.0f;
    o->subtype++;
}

void mu_env_move_fishs(mu_env *env, const mu_env_inputs *in)
{
    const int32_t w = in->world;
    for (int32_t i = 0; i < MU_ENV_FISHS; ++i) {
        if (!(env_water_world(w) || w == 8 || w == 0x22 || w == 0x85) && i >= 3)
            continue;
        mu_env_object *o = &env->fishs[i];
        if (!o->live) {
            o->position[0] = (float)(mu_env_rand(env) % 1024 - 512) + in->hero_position[0];
            o->position[1] = (float)(mu_env_rand(env) % 1024 - 512) + in->hero_position[1];
            o->position[2] = in->hero_position[2];
            int32_t tile = tile_of(o->position);
            if (spawn_allowed(in, tile))
                spawn(env, in, o, tile);
        }
        if (!o->live)
            continue;
        if (o->type != -1) {
            if (env->host.has_model && !env->host.has_model(env->host.context, o->type))
                return;
            if (env->host.animate)
                env->host.animate(env->host.context, o, o->scale * 0.5f);
        }
        if (o->type == 0x19f || o->type == 0x1a0) {
            o->field_a8 = env_sin(o->phase) * 0.4f + 0.5f;
            o->phase = o->phase + 0.1f;
        }
        if (fish_type(o->type)) {
            env_set_action(env, o, (o->type == MU_ENV_MODEL_BUG || o->type == 0x1b3) ? 1 : 0);
            env_flock(env, o, i, env->fishs, MU_ENV_FISHS);
            mu_angle_matrix(o->angle, o->matrix);
            float v[3] = {(float)(mu_env_rand(env) % 4 + 6) * o->scale, 0.0f, 0.0f}, p[3];
            mu_vector_rotate(v, o->matrix, p);
            o->position[0] = o->position[0] + p[0];
            o->position[1] = o->position[1] + p[1];
            o->position[2] = o->position[2] + p[2];
            if (!env_water_world(w) && w != 0x85)
                o->position[2] = env_terrain(env, o->position[0], o->position[1]);
            o->direction[0] = 3.0f * p[0] + o->position[0];
            o->direction[1] = 3.0f * p[1] + o->position[1];
            int32_t tile = tile_of(o->position);
            uint16_t a = att(in, tile);
            if (w == 8 || env_kalima(w) || w == 0x21 || w == 0x36 || w == 0x86) {
                if (a == 1 || a >= 8)
                    turn_around(o);
                else if (o->subtype > 0)
                    o->subtype--;
                if (env_kalima(w) && o->timer <= 1)
                    env_set_live(env, o, 0);
            } else {
                if ((o->type == MU_ENV_MODEL_FISH && layer(in, tile) != (MU_ENV_MUTATION == 4 ? 4 : 5)) ||
                    (o->type == MU_ENV_MODEL_RAT && a >= 8) || (w == 7 && (a == 1 || a >= 8)) ||
                    (env_abyss(w) && a == 1))
                    turn_around(o);
                else if (o->subtype > 0)
                    o->subtype--;
            }
            if (o->subtype >= 2)
                env_set_live(env, o, 0);
            if (o->type == MU_ENV_MODEL_FISH || o->type == 0x1b3)
                copy3(o->start, o->position);
            float dx = o->position[0] - in->hero_position[0], dy = o->position[1] - in->hero_position[1];
            float dist = env_sqrt(dx * dx + dy * dy);
            if (dist >= 1500.0f)
                env_set_live(env, o, 0);
            if (600.0f > dist && o->type == MU_ENV_MODEL_RAT && mu_env_rand(env) % 256 == 0)
                env_sound(env, 0xf, o, 0);
        } else {
            env_set_action(env, o, 0);
        }
        o->timer--;
        if (o->timer <= 0 && o->type != MU_ENV_MODEL_BUG && mu_env_rand(env) % 64 == 0)
            o->timer = mu_env_rand(env) % 128;
        env_fade_alpha(o);
    }
}

void mu_env_render_fishs(mu_env *env, const mu_env_inputs *in, const mu_env_render_host *r)
{
    for (int32_t i = 0; i < MU_ENV_FISHS; ++i) {
        mu_env_object *o = &env->fishs[i];
        o->angle[2] = o->angle[2] + 90.0f;
        if (o->live) {
            o->visible = (uint8_t)(r->frustum ? r->frustum(r->context, o->position[0] * 0.01f,
                                                            o->position[1] * 0.01f, -20.0f) : 1);
            if (o->visible && o->type != -1) {
                if (r->draw_object)
                    r->draw_object(r->context, o, 0);
                if (!(o->type == 0x19f || o->type == 0x1a0) && in->world != 0xa && in->world != 0x84 &&
                    in->world != 0x85) {
                    if (r->alpha_test)
                        r->alpha_test(r->context, 1);
                    if (r->color4)
                        r->color4(r->context, 0.0f, 0.0f, 0.0f, 0.2f);
                    if (r->has_model && !r->has_model(r->context, o->type))
                        return;
                    float origin[3] = {o->position[0], o->position[1], 0.0f};
                    origin[2] = env_terrain(env, o->position[0], o->position[1]);
                    if (r->shadow)
                        r->shadow(r->context, o, origin);
                }
            }
        }
        o->angle[2] = o->angle[2] - 90.0f;
    }
}
