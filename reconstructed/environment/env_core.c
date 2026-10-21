/* State, rand(), ObjectInit and the client layout of the environment module
 * (NATIVE-ENV-001). */
#include <math.h>
#include <string.h>

#include "env.h"
#include "env_internal.h"

int32_t mu_env_cvttss2si(float value)
{
    if (!(value > -2147483904.0f && value < 2147483648.0f))   /* NaN or outside int32 */
        return INT32_MIN;
    return (int32_t)value;
}

int32_t mu_env_rand(mu_env *env)
{
    env->rand_state = env->rand_state * 214013u + 2531011u;
    env->rand_calls++;
    return (int32_t)((env->rand_state >> 16) & 0x7fff);
}

float env_sin(float x) { return (float)sin((double)x); }    /* 0x009681bd over CRT sin 0x01985700 */
float env_cos(float x) { return (float)cos((double)x); }    /* 0x009fa223 over CRT cos 0x0198c4d0 */
float env_sqrt(float x) { return (float)sqrt((double)x); }  /* 0x00961a07 over CRT sqrt 0x019856f0 */
float env_atan(float x) { return (float)atan((double)x); }  /* 0x012b2d60 over CRT atan 0x01997190 */
float env_fabs(float x) { return 0.0f > x ? -x : x; }       /* 0x0184f8ff */

int32_t env_tile_index(int32_t x, int32_t y)   /* 0x016d34db */
{
    return (int32_t)(((uint32_t)y & 0xffu) << 8) + (x & 0xff);
}

float env_terrain(mu_env *env, float x, float y)
{
    return env->host.terrain_height ? env->host.terrain_height(env->host.context, x, y) : 0.0f;
}

void env_sound(mu_env *env, int32_t id, const mu_env_object *o, int32_t loop)
{
    if (env->host.play_sound)
        env->host.play_sound(env->host.context, id, o, loop);
}

void env_set_action(mu_env *env, mu_env_object *o, int32_t action)
{
    if (env->host.set_action)
        env->host.set_action(env->host.context, o, action);
}

/* SetLive 0x0129f4a5: stores the byte; 0 also runs the cleanup 0x009b0451. */
void env_set_live(mu_env *env, mu_env_object *o, uint8_t live)
{
    o->live = live;
    if (!live && env->host.kill)
        env->host.kill(env->host.context, o);
}

void mu_env_object_init(mu_env *env, mu_env_object *o)
{
    memset(o, 0, sizeof *o);
    o->alpha_speed = 0.1f;   /* +0xe0 */
    if (env && env->host.init)
        env->host.init(env->host.context, o);
}

void mu_env_init(mu_env *env, uint32_t rand_seed, const mu_env_host *host)
{
    memset(env, 0, sizeof *env);
    env->rand_state = rand_seed;
    if (host)
        env->host = *host;
    for (int i = 0; i < MU_ENV_BOIDS; ++i)
        mu_env_object_init(NULL, &env->boids[i]);
    for (int i = 0; i < MU_ENV_FISHS; ++i)
        mu_env_object_init(NULL, &env->fishs[i]);
    env->tormenta.weather = 1;      /* 0x00e4be37 */
    env->tormenta.rain_max = 10.0f;
    env->tormenta.rain = 0.0f;
}

/* ---- client layout ---- */

#define F(field, offset, size) {offsetof(mu_env_object, field), offset, size}
static const struct { size_t local, client, size; } object_fields[] = {
    F(live, 0x00, 1), F(flag_01, 0x01, 1), F(flag_05, 0x05, 1), F(pass, 0x0a, 1), F(visible, 0x0b, 1),
    F(alpha_enable, 0x0c, 1), F(ai, 0x29, 1), F(action, 0x2a, 2), F(prior_action, 0x2c, 2),
    F(type, 0x5c, 4), F(subtype, 0x60, 4), F(field_68, 0x68, 4), F(timer, 0x6c, 4), F(field_74, 0x74, 4),
    F(velocity, 0xa0, 4), F(field_a8, 0xa8, 4), F(phase, 0xb4, 4), F(scale, 0xbc, 4), F(field_c4, 0xc4, 4),
    F(gravity, 0xc8, 4), F(frame, 0xd0, 4), F(prior_frame, 0xd4, 4), F(alpha_target, 0xd8, 4),
    F(alpha, 0xdc, 4), F(alpha_speed, 0xe0, 4), F(light, 0xec, 12), F(direction, 0xf8, 12),
    F(position, 0x158, 12), F(angle, 0x164, 12), F(field_170, 0x170, 12), F(start, 0x188, 12),
    F(matrix, 0x2e8, 48),
};
#undef F
#define F(field, offset, size) {offsetof(mu_env_leaf, field), offset, size}
static const struct { size_t local, client, size; } leaf_fields[] = {
    F(live, 0x08, 1), F(texture, 0x0c, 4), F(scale, 0x18, 4), F(position, 0x20, 12), F(angle, 0x2c, 12),
    F(light, 0x38, 12), F(alpha, 0x44, 4), F(rotation, 0x60, 4), F(velocity, 0x70, 12), F(turn, 0x7c, 12),
    F(start, 0x88, 12),
};
#undef F

void mu_env_object_store(const mu_env_object *o, uint8_t out[MU_ENV_OBJECT_BYTES])
{
    for (size_t i = 0; i < sizeof object_fields / sizeof object_fields[0]; ++i)
        memcpy(out + object_fields[i].client, (const uint8_t *)o + object_fields[i].local, object_fields[i].size);
}

void mu_env_object_load(mu_env_object *o, const uint8_t in[MU_ENV_OBJECT_BYTES])
{
    for (size_t i = 0; i < sizeof object_fields / sizeof object_fields[0]; ++i)
        memcpy((uint8_t *)o + object_fields[i].local, in + object_fields[i].client, object_fields[i].size);
}

void mu_env_object_mask(uint8_t out[MU_ENV_OBJECT_BYTES])
{
    memset(out, 0, MU_ENV_OBJECT_BYTES);
    for (size_t i = 0; i < sizeof object_fields / sizeof object_fields[0]; ++i)
        memset(out + object_fields[i].client, 1, object_fields[i].size);
}

void mu_env_leaf_store(const mu_env_leaf *l, uint8_t out[MU_ENV_LEAF_BYTES])
{
    for (size_t i = 0; i < sizeof leaf_fields / sizeof leaf_fields[0]; ++i)
        memcpy(out + leaf_fields[i].client, (const uint8_t *)l + leaf_fields[i].local, leaf_fields[i].size);
}

void mu_env_leaf_load(mu_env_leaf *l, const uint8_t in[MU_ENV_LEAF_BYTES])
{
    for (size_t i = 0; i < sizeof leaf_fields / sizeof leaf_fields[0]; ++i)
        memcpy((uint8_t *)l + leaf_fields[i].local, in + leaf_fields[i].client, leaf_fields[i].size);
}

void mu_env_leaf_mask(uint8_t out[MU_ENV_LEAF_BYTES])
{
    memset(out, 0, MU_ENV_LEAF_BYTES);
    for (size_t i = 0; i < sizeof leaf_fields / sizeof leaf_fields[0]; ++i)
        memset(out + leaf_fields[i].client, 1, leaf_fields[i].size);
}

/* RenderObject's body light 0x017ec3d8 under ObjectInit's +6 = +7 = 1 (see env.h). */
void mu_env_body_light(const mu_env_object *o, const float frame_light[3], float color[3], uint8_t *lighting)
{
    *lighting = o->flag_05;                          /* model +0x50 = object +5 */
    for (int k = 0; k < 3; ++k)
        color[k] = frame_light[k] + o->light[k];     /* +6 set: no 0.1 factor */
}
