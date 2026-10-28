/* Ambient flyers: MoveBoids 0x00c9eb04 and RenderBoids 0x00c9fd8d with their
 * movers (NATIVE-ENV-001). Comparisons follow the client's comiss/jcc
 * pairs, so NaN inputs take the same branches. */
#include <string.h>

#include "env.h"
#include "env_internal.h"
#include "../record-math/record_math.h"

static uint16_t attribute_at(const mu_env_inputs *in, int32_t tile)
{
    return in->attributes ? in->attributes[(uint32_t)tile & 0xffffu] : 0;
}

/* FadeAlpha 0x012af883. */
void env_fade_alpha(mu_env_object *o)
{
    if (o->alpha_enable) {
        if (o->alpha_target > o->alpha) {
            o->alpha = o->alpha + 0.05f;
            if (o->alpha > 1.0f)
                o->alpha = 1.0f;
        } else if (o->alpha > o->alpha_target) {
            o->alpha = o->alpha - 0.05f;
            if (0.0f > o->alpha)
                o->alpha = 0.0f;
        }
    } else {
        o->alpha = (o->alpha_target - o->alpha) * o->alpha_speed + o->alpha;
    }
    if (o->field_a8 > o->alpha)
        o->field_a8 = o->alpha;
}

static int32_t iabs(int32_t v)   /* 0x01983135: cdq; xor; sub */
{
    uint32_t s = (uint32_t)(v >> 31);
    return (int32_t)(((uint32_t)v ^ s) - s);
}

/* CreateAngle 0x012aeced: integer heading of (x2, y2) seen from (x1, y1). */
static int32_t create_angle(float x1, float y1, float x2, float y2)
{
    float q = (x2 - x1) == 0.0f ? 0.0f : (y1 - y2) / (x2 - x1);
    int32_t a = mu_env_cvttss2si(env_atan(q) * 57.2957763671875f);
    if (x1 > x2)
        a = (int32_t)((uint32_t)a + 180u);
    if (a < 0)
        a = (int32_t)((uint32_t)a + 360u);
    a = (int32_t)(360u - (uint32_t)a);
    return a % 360;
}

/* TurnAngle 0x012aef0c: turns the integer heading toward target by at most step. */
static int32_t turn_angle(int32_t angle, int32_t target, int32_t step)
{
    int32_t d = iabs((int32_t)((uint32_t)angle - (uint32_t)target)), r = 0;
    if (angle > target) {
        int32_t m = step < d ? step : d;
        r = d < iabs((int32_t)((uint32_t)target + 360u - (uint32_t)angle)) ? (int32_t)(0u - (uint32_t)m) : m;
        if (MU_ENV_MUTATION == 10)
            r = (int32_t)(0u - (uint32_t)r);
    }
    if (angle < target) {
        int32_t m = step < d ? step : d;
        r = d < iabs((int32_t)((uint32_t)angle + 360u - (uint32_t)target)) ? m : (int32_t)(0u - (uint32_t)m);
    }
    return (int32_t)((uint32_t)angle + (uint32_t)r + 360u) % 360;
}

/* MoveBoidFlock 0x012af9a9(o, index, list, count): steering from the live
 * neighbours within 400 units (2D). */
void env_flock(mu_env *env, mu_env_object *o, int32_t index, mu_env_object *list, int32_t count)
{
    (void)env;
    int32_t n = 0;
    float sx = 0.0f, sy = 0.0f;
    for (int32_t j = 0; j < count; ++j) {
        const mu_env_object *t = &list[j];
        if (!t->live || j == index)
            continue;
        float d[3] = {o->position[0] - t->position[0], o->position[1] - t->position[1],
                      o->position[2] - t->position[2]};
        float dist = env_sqrt(d[0] * d[0] + d[1] * d[1]);
        if (!((MU_ENV_MUTATION == 2 ? 500.0f : 400.0f) > dist))
            continue;
        float ax = t->direction[0] - t->position[0], ay = t->direction[1] - t->position[1];
        if (80.0f > dist) {
            ax = ax - (t->direction[0] - o->position[0]);
            ay = ay - (t->direction[1] - o->position[1]);
        } else {
            ax = (t->direction[0] - o->position[0]) + ax;
            ay = (t->direction[1] - o->position[1]) + ay;
        }
        float len = env_sqrt(ax * ax + ay * ay);
        sx = ax / len + sx;
        sy = ay / len + sy;
        ++n;
    }
    if (n <= 0)
        return;
    sx = sx / (float)n + o->position[0];
    sy = sy / (float)n + o->position[1];
    int32_t step = mu_env_cvttss2si(o->gravity);
    int32_t target = create_angle(o->position[0], o->position[1], sx, sy);
    o->angle[2] = (float)turn_angle(mu_env_cvttss2si(o->angle[2]), target, step);
}

/* MoveBoidFlight 0x00ca3e2f(o, index). */
static void boid_flight(mu_env *env, const mu_env_inputs *in, mu_env_object *o, int32_t index)
{
    if (o->ai == 2)
        return;
    if (o->type != MU_ENV_MODEL_BUTTERFLY || mu_env_rand(env) % 4 == 0)
        env_flock(env, o, index, env->boids, MU_ENV_BOIDS);
    mu_angle_matrix(o->angle, o->matrix);
    float v[3];
    if (env_atlans(in->world)) {
        if (5.0f > o->phase) {
            if (index < 35)
                v[0] = (float)(mu_env_rand(env) % 16 + 8) * o->scale;
            else
                v[0] = (float)(mu_env_rand(env) % 16 + 16) * o->scale;
            v[1] = 0.0f;
            v[2] = o->direction[2];
            o->gravity = 15.0f;
        } else {
            v[0] = (float)(mu_env_rand(env) % 32 + 32) * o->scale;
            v[1] = 0.0f;
            v[2] = o->direction[2];
            o->gravity = 5.0f;
        }
        o->phase = o->phase + 0.1f;
        if (o->phase >= 10.0f)
            o->phase = 0.0f;
    } else {
        v[0] = o->scale * 25.0f;
        v[1] = 0.0f;
        v[2] = o->direction[2];
    }
    float p[3];
    mu_vector_rotate(v, o->matrix, p);
    o->position[0] = o->position[0] + p[0];
    o->position[1] = o->position[1] + p[1];
    o->position[2] = o->position[2] + p[2];
    o->direction[0] = 3.0f * p[0] + o->position[0];
    o->direction[1] = 3.0f * p[1] + o->position[1];
    float dx = o->position[0] - in->hero_position[0], dy = o->position[1] - in->hero_position[1];
    float dist = env_sqrt(dx * dx + dy * dy);
    float range = 1500.0f;
    if (o->type == 0x7c4)
        range = 4000.0f;
    else if (o->type == 0x7c6)
        range = 3000.0f;
    else if (in->world != 0x33 && mu_env_rand(env) % 512 == 0)
        env_set_live(env, o, 0);
    if (dist >= range)
        env_set_live(env, o, 0);
}

/* MoveBird 0x00ca2dcb (birds and crows). */
static void move_bird(mu_env *env, const mu_env_inputs *in, mu_env_object *o)
{
    if (o->ai == 0) {
        int32_t t = mu_env_cvttss2si(in->world_time) % 8192;
        if (t < 0x800) {
            float d0 = o->position[0] - in->hero_position[0], d1 = o->position[1] - in->hero_position[1];
            float dist = env_sqrt(d0 * d0 + d1 * d1);
            if (dist >= (MU_ENV_MUTATION == 3 ? 300.0f : 200.0f) && 400.0f >= dist)
                o->ai = 1;
        }
        o->scale = 1.0f;
        o->position[2] = (float)(mu_env_rand(env) % 16 - 8) + o->position[2];
        if (200.0f > o->position[2])
            o->direction[2] = 10.0f;
        else if (o->position[2] > 600.0f)
            o->direction[2] = -10.0f;
    }
    if (o->ai == 1) {
        o->direction[2] = -20.0f;
        float h = env_terrain(env, o->position[0], o->position[1]);
        if (h > o->position[2]) {
            o->ai = 3;
            o->scale = 1.1f;
            o->direction[2] = 20.0f;
            o->action = 0;
        }
    }
    if (o->ai == 2) {
        if (in->hero_action >= 0x32 || mu_env_rand(env) % 256 == 0) {
            o->ai = 3;
            o->scale = 1.1f;
            o->direction[2] = 20.0f;
            o->action = 0;
        }
    }
    if (o->ai == 3) {
        o->position[2] = (float)(mu_env_rand(env) % 16 - 8) + o->position[2];
        o->scale = o->scale - 0.005f;
        if (1.0f >= o->scale)
            o->ai = 0;
    }
}

/* MoveButterfly 0x00ca2ba7. */
static void move_butterfly(mu_env *env, mu_env_object *o)
{
    if (mu_env_rand(env) % 32 == 0) {
        o->angle[2] = (float)(mu_env_rand(env) % 360);
        o->direction[2] = (float)(mu_env_rand(env) % 15 - 7) * 1.0f;
    }
    o->direction[2] = (float)(mu_env_rand(env) % 15 - 7) * 0.2f + o->direction[2];
    float h = env_terrain(env, o->position[0], o->position[1]);
    if (h + 50.0f > o->position[2]) {
        o->direction[2] = o->direction[2] * 0.8f;
        o->direction[2] = o->direction[2] + 1.0f;
    }
    if (o->position[2] > h + 300.0f) {
        o->direction[2] = o->direction[2] * 0.8f;
        o->direction[2] = o->direction[2] - 1.0f;
    }
    o->position[2] = (float)(mu_env_rand(env) % 15 - 7) * 0.3f + o->position[2];
}

/* MoveBat 0x00ca2acd. */
static void move_bat(mu_env *env, mu_env_object *o)
{
    o->position[2] = env_terrain(env, o->position[0], o->position[1]);
    o->position[2] = -env_fabs(env_sin(o->phase)) * 150.0f + 350.0f + o->position[2];
    o->phase = o->phase + 0.2f;
}

/* Spawn position of the common boid setup and of the Atlans shoal. */
static void spawn_position(mu_env *env, const mu_env_inputs *in, mu_env_object *o)
{
    o->position[0] = (float)(mu_env_rand(env) % 1024 - 512) + in->hero_position[0];
    o->position[1] = (float)(mu_env_rand(env) % 1024 - 512) + in->hero_position[1];
    o->position[2] = in->hero_position[2];
    float h = env_terrain(env, o->position[0], o->position[1]);
    o->position[2] = h + (float)(mu_env_rand(env) % 200 + 150);
}

/* AtlansShoal 0x00ca27b1: returns 1 in every world (so the creators after it
 * never run and the common setup is skipped). */
static int atlans_shoal(mu_env *env, const mu_env_inputs *in, mu_env_object *o)
{
    if (!env_atlans(in->world))
        return 1;
    if (128.0f > in->hero_position[1] * 0.01f) {
        o->type = (mu_env_rand(env) % 2) + 0x199;
        o->gravity = 15.0f;
        o->alpha_enable = 1;
        o->velocity = 0.8f;
        o->field_c4 = 10.0f;
        o->field_68 = -1;
        o->field_74 = -1;
        o->phase = (float)(mu_env_rand(env) % 314) * 0.01f;
        o->scale = mu_env_rand(env) % 100 < 90 ? 0.3f : 0.25f;
        o->flag_05 = 0;
        o->angle[0] = o->angle[1] = o->angle[2] = 0.0f;
        o->light[0] = o->light[1] = o->light[2] = 1.0f;
        spawn_position(env, in, o);
    } else {
        env_set_live(env, o, 0);
    }
    return 1;
}

void mu_env_move_boids(mu_env *env, const mu_env_inputs *in)
{
    const int32_t w = in->world;
    int32_t tile = env_tile_index(mu_env_cvttss2si(in->hero_position[0] / 100.0f),
                                  mu_env_cvttss2si(in->hero_position[1] / 100.0f));
    uint16_t att = attribute_at(in, tile);
    for (int32_t i = 0; i < MU_ENV_BOIDS; ++i) {
        int skip = 0, allow = 1;
        if (w == 7 || w == 0x80 || w == 0x81 || w == 0x82) {
        } else if (w == 0xa || w == 0x84) {
            if (i >= 13)
                skip = 1;
        } else if (w == 0x33) {
            if (i >= 2)
                skip = 1;
        } else if (env_kalima(w)) {
            if (i > 1)
                skip = 1;
            if (mu_env_rand(env) % 10 != 0)
                allow = 0;
        } else if (i >= (MU_ENV_MUTATION == 1 ? 6 : 5)) {
            skip = 1;
        }
        if (skip)
            return;
        mu_env_object *o = &env->boids[i];
        if (!o->live && allow) {
            int spawn = 0;
            if (w == 0 || w == 1 || w == 3 || w == 4 || w == 0xa || w == 0x84)
                spawn = 1;
            else if (w == 7 && (att == 0 || att == 2))
                spawn = 1;
            else if (env_blood_castle(w) || env_kalima(w) || env_deep_dungeon(w))
                spawn = 1;
            else {
                if (w == 0x33 && i < 1 && mu_env_rand(env) % 500 == 0 && !in->hero_safe_zone)
                    spawn = 1;
                else if (env_abyss(w) && (att & 0x800))
                    spawn = 1;
            }
            if (spawn) {
                int handled = 0;
                mu_env_object_init(env, o);
                env_set_live(env, o, 1);
                o->scale = 1.0f;
                o->flag_05 = 1;
                o->timer = 0;
                o->subtype = 0;
                o->light[0] = o->light[1] = o->light[2] = 0.5f;
                o->alpha = 0.0f;
                o->alpha_target = 1.0f;
                o->gravity = 13.0f;
                o->ai = 0;
                o->action = 0;
                if (w == 0) {
                    o->type = MU_ENV_MODEL_BIRD;
                } else if (w == 1 || w == 4) {
                    o->type = MU_ENV_MODEL_BAT;
                } else if (w == 3) {
                    o->type = MU_ENV_MODEL_BUTTERFLY;
                    o->scale = 0.3f;
                    o->flag_05 = 0;
                    o->light[0] = o->light[1] = o->light[2] = 1.0f;
                } else if (env_blood_castle(w)) {
                    o->type = MU_ENV_MODEL_CROW;
                } else if (w == 0x33) {
                    o->type = MU_ENV_MODEL_ELBELAND;
                    o->scale = 0.0f;
                    o->field_a8 = 0.0f;
                    o->field_170[0] = (float)(mu_env_rand(env) % 314) / 100.0f;
                    o->position[1] = o->position[1] + 5.0f;
                    o->pass = 1;
                } else if (env_deep_dungeon(w)) {
                    o->type = MU_ENV_MODEL_BAT;
                } else {
                    handled = env_icarus_create(env, in, o, i);
                    if (!handled) handled = atlans_shoal(env, in, o);
                }
                if (handled != 1) {
                    o->alpha_enable = 1;
                    o->velocity = 0.8f;
                    o->field_c4 = 10.0f;
                    o->field_68 = -1;
                    o->field_74 = -1;
                    o->phase = (float)(mu_env_rand(env) % 314) * 0.01f;
                    spawn_position(env, in, o);
                    o->angle[0] = o->angle[1] = o->angle[2] = 0.0f;
                }
            }
        }
        if (!o->live)
            continue;
        if (env->host.has_model && !env->host.has_model(env->host.context, o->type))
            return;
        float speed = 1.0f;
        if (o->type == 0x7c4 || o->type == 0x7c6)
            speed = 0.5f;
        if (w == 51 && env->host.action_speed)
            speed = env->host.action_speed(env->host.context, o);
        if (env->host.animate)
            env->host.animate(env->host.context, o, speed);
        switch (o->type) {
        case MU_ENV_MODEL_BAT:
            move_bat(env, o);
            break;
        case MU_ENV_MODEL_BUTTERFLY:
            move_butterfly(env, o);
            break;
        case MU_ENV_MODEL_BIRD:
        case MU_ENV_MODEL_CROW:
            move_bird(env, in, o);
            break;
        case 0x472:
            if (w == 10) env_icarus_emitter_move(env, in, o, i);
            break;
        case 0x1a3:
        case 0x1a4:
            env_elbeland_move(env, in, o);
            break;
        default:   /* 0x7c6 mover is not ported */
            break;
        }
        boid_flight(env, in, o, i);
        if (o->timer <= 0 && env_atlans(w) && att == 1) {
            o->angle[2] = o->angle[2] + 180.0f;
            if (o->angle[2] >= 360.0f)
                o->angle[2] = o->angle[2] - 360.0f;
            o->timer = 10;
            o->subtype++;
        }
        if (!(o->type == 0x1a3 || o->type == 0x1a4) && o->subtype >= 2)
            env_set_live(env, o, 0);
        o->timer--;
        float dx = o->position[0] - in->hero_position[0], dy = o->position[1] - in->hero_position[1];
        float dist = env_sqrt(dx * dx + dy * dy);
        if (600.0f > dist) {
            if (o->type == MU_ENV_MODEL_BIRD) {
                if (mu_env_rand(env) % 512 == 0)
                    env_sound(env, 0xc, o, 0);    /* aBird1 */
                if (mu_env_rand(env) % 512 == 0)
                    env_sound(env, 0xd, o, 0);    /* aBird2 */
            } else if (o->type == MU_ENV_MODEL_BAT) {
                if (mu_env_rand(env) % 256 == 0)
                    env_sound(env, 0xe, o, 0);    /* aBat */
            } else if (o->type == MU_ENV_MODEL_CROW) {
                if (att == 1 && mu_env_rand(env) % 128 == 0)
                    env_sound(env, 0x8a, o, 0);
            }
        }
        env_fade_alpha(o);
    }
}

/* RenderBoids 0x00c9fd8d(pass). */
void mu_env_render_boids(mu_env *env, const mu_env_inputs *in, uint8_t pass, const mu_env_render_host *r)
{
    for (int32_t i = 0; i < MU_ENV_BOIDS; ++i) {
        mu_env_object *o = &env->boids[i];
        if (o->pass != pass)
            continue;
        if (o->type != 0x472 && MU_ENV_MUTATION != 8)
            o->angle[2] = o->angle[2] + 90.0f;
        if (o->live) {
            o->visible = (uint8_t)(r->frustum ? r->frustum(r->context, o->position[0] * 0.01f,
                                                            o->position[1] * 0.01f, -20.0f) : 1);
            if (o->visible) {
                if (o->type == 0x472)
                    continue;
                if (r->draw_object)
                    r->draw_object(r->context, o, 1);
                if (r->has_model && !r->has_model(r->context, o->type))
                    return;
                if (o->type == MU_ENV_MODEL_BUTTERFLY) {
                    float k = (float)(mu_env_rand(env) % 32 + 64) * 0.01f;
                    float light[3] = {k * 0.2f, k * 0.4f, k * 0.4f};
                    if (r->sprite)
                        r->sprite(r->context, 0x7ef7, o->position, 1.0f, light, o);
                } else if (o->type == MU_ENV_MODEL_CROW) {
                    /* the eyes: bone 1 of the model's transform 0x06fce398 */
                    float eye[3], v[3] = {-5.0f, 0.0f, 0.0f};
                    if (r->bone_position)
                        r->bone_position(r->context, o, 1, v, eye);
                    float k = (float)(mu_env_rand(env) % 32 + 128) * 0.01f;
                    float light[3] = {k * 1.0f, k * 0.2f, 0.0f};
                    if (r->sprite)
                        r->sprite(r->context, 0x7ef7, eye, 0.1f, light, o);
                    v[0] = 5.0f;
                    if (r->bone_position)
                        r->bone_position(r->context, o, 1, v, eye);
                    if (r->sprite)
                        r->sprite(r->context, 0x7ef7, eye, 0.1f, light, o);
                }
                if (o->type == 0x1a4 && env->host.create_particle_owned)
                    env->host.create_particle_owned(env->host.context, 0x7f89, o->position, o->angle, o->light, 18, o->velocity, o);
                if (in->world != 0xa && in->world != 0x84) {
                    if (r->alpha_test)
                        r->alpha_test(r->context, 1);
                    if (o->type == 0x1a3) {
                        if (r->color4)
                            r->color4(r->context, 0.0f, 0.0f, 0.0f, o->field_c4 == 0.0f ? 0.0f : 1.0f);
                    } else if (r->color4) {
                        r->color4(r->context, 0.0f, 0.0f, 0.0f, 0.2f);
                    }
                    if (!(in->world == 0x33 && o->type == 0x1a4)) {
                        float origin[3] = {o->position[0], o->position[1], 0.0f};
                        origin[2] = env_terrain(env, o->position[0], o->position[1]);
                        if (r->shadow)
                            r->shadow(r->context, o, origin);
                    }
                }
            }
        }
        if (o->type != 0x472 && MU_ENV_MUTATION != 8)
            o->angle[2] = o->angle[2] - 90.0f;
    }
}
