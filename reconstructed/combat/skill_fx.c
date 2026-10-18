/* The client's older effect system for skills and projectiles
 * (NATIVE-COMBAT-002). See skill_fx.h and docs/research/client-combat.md.
 * Build with -ffp-contract=off. */
#include "skill_fx.h"

#include <math.h>
#include <string.h>

#include "../record-math/record_math.h"

static float f32bits(uint32_t bits)
{
    float value;
    memcpy(&value, &bits, sizeof value);
    return value;
}

#define F_0_1 f32bits(0x3dcccccdu)   /* 0x01a7df04 */
#define F_0_2 f32bits(0x3e4ccccdu)   /* 0x01a7df08 */
#define F_0_3 f32bits(0x3e99999au)   /* 0x01a7e6e0 */
#define F_0_4 f32bits(0x3ecccccdu)   /* 0x01a7df0c */
#define F_0_8 f32bits(0x3f4ccccdu)   /* 0x01a7df18 */
#define F_0_9 f32bits(0x3f666666u)   /* 0x01a7edac */

static int32_t env_rand(const mu_sfx_env *env)
{
    return env && env->rand ? env->rand(env->context) : 0;
}

static float env_height(const mu_sfx_env *env, float x, float y)
{
    return env && env->height ? env->height(env->context, x, y) : 0.0f;
}

static const mu_sfx_object *env_object(const mu_sfx_env *env, int32_t index)
{
    if (index < 0 || !env || !env->object)
        return NULL;
    return env->object(env->context, index);
}

static int env_call(const mu_sfx_env *env, const mu_sfx_call *call, mu_sfx_effect *e)
{
    if (!env || !env->call)
        return call->routine == MU_SFX_CALL_ANIMATION;
    return env->call(env->context, call, e);
}

static void copy3(float out[3], const float in[3])
{
    out[0] = in[0];
    out[1] = in[1];
    out[2] = in[2];
}

/* C's signed remainder, as the client's `and eax, 0x8000000N; jns; dec; or; inc`. */
static int32_t smod(int32_t value, int32_t m)
{
    return value % m;
}

static void call_terrain_light(const mu_sfx_env *env, mu_sfx_effect *e, const float light[3], int32_t range)
{
    mu_sfx_call c;
    memset(&c, 0, sizeof c);
    c.routine = MU_SFX_CALL_TERRAIN_LIGHT;
    c.position[0] = e->position[0];
    c.position[1] = e->position[1];
    copy3(c.light, light);
    c.range = range;
    c.owner = MU_SFX_NO_OWNER;
    env_call(env, &c, e);
}

static void call_particle(const mu_sfx_env *env, mu_sfx_effect *e, int32_t bitmap, const float position[3],
                          const float angle[3], const float light[3], int32_t subtype, float scale, int32_t owner)
{
    mu_sfx_call c;
    memset(&c, 0, sizeof c);
    c.routine = MU_SFX_CALL_PARTICLE;
    c.type = bitmap;
    c.subtype = subtype;
    c.scale = scale;
    c.owner = owner;
    copy3(c.position, position);
    copy3(c.angle, angle);
    copy3(c.light, light);
    env_call(env, &c, e);
}

static void call_effect(const mu_sfx_env *env, mu_sfx_effect *e, int32_t type, const float position[3],
                        const float angle[3], const float light[3], int32_t subtype, int32_t owner)
{
    mu_sfx_call c;
    memset(&c, 0, sizeof c);
    c.routine = MU_SFX_CALL_EFFECT;
    c.type = type;
    c.subtype = subtype;
    c.owner = owner;
    copy3(c.position, position);
    copy3(c.angle, angle);
    copy3(c.light, light);
    env_call(env, &c, e);
}

static void call_joint(const mu_sfx_env *env, mu_sfx_effect *e, int32_t bitmap, const float position[3],
                       const float target[3], const float angle[3], int32_t subtype, int32_t owner, float scale)
{
    mu_sfx_call c;
    memset(&c, 0, sizeof c);
    c.routine = MU_SFX_CALL_JOINT;
    c.type = bitmap;
    c.subtype = subtype;
    c.owner = owner;
    c.scale = scale;
    copy3(c.position, position);
    copy3(c.target, target);
    copy3(c.angle, angle);
    env_call(env, &c, e);
}

static void call_plain(const mu_sfx_env *env, mu_sfx_effect *e, int32_t routine)
{
    mu_sfx_call c;
    memset(&c, 0, sizeof c);
    c.routine = routine;
    c.type = e->type;
    c.subtype = e->subtype;
    c.owner = -2;
    env_call(env, &c, e);
}

/* ---------------------------------------------------------------- CreateEffect */

int mu_sfx_effect_create(mu_sfx_effect *e, int32_t type, int32_t subtype, const float position[3],
                         const float angle[3], const float light[3], int32_t owner, float scale,
                         const mu_sfx_info *info, const mu_sfx_env *env)
{
    memset(e, 0, sizeof *e);
    int supported = (type == MU_SFX_MODEL_ARROW && (subtype == 0 || subtype == 2)) ||
                    (type == MU_SFX_MODEL_FIRE && subtype == 1) ||
                    (type == MU_SFX_BITMAP_THUNDER && subtype == 0) ||
                    (type == MU_SFX_BITMAP_MAGIC_GROUND2 && subtype == 1);
    if (!supported)
        return 0;
    mu_sfx_info none;
    if (!info) {
        memset(&none, 0, sizeof none);
        info = &none;
    }
    /* common initialisation 0x013c1002..0x013c137a */
    e->live = 1;
    e->type = type;
    e->subtype = subtype;
    e->flag5 = 1;
    e->field_68 = -1;
    e->blend_mesh = -1;
    e->blend_light = 1.0f;
    e->blend_u = 0.0f;
    e->blend_v = 0.0f;
    e->frame = 0.0f;
    e->flag_c = 0;
    e->alpha = 1.0f;
    e->prior_frame = 0.0f;
    /* comiss 0, scale; jb: the scale is kept when 0 < scale (or unordered) */
    e->scale = (0.0f < scale || isnan(scale)) ? scale : F_0_9;
    e->scale_arg = scale;
    e->owner = owner;
    const mu_sfx_object *o = env_object(env, owner);
    if (owner >= 0) {
        if (o)
            copy3(e->start, o->position);
        e->start[2] = env_height(env, e->start[0], e->start[1]);
    }
    e->velocity = F_0_3;
    e->key = info->key;
    e->client_hit = (uint8_t)info->word4;
    e->skill = info->skill;
    e->field_80 = 0;
    e->field_78 = 0;
    e->action = 0;
    e->info6 = (uint8_t)info->word6;
    e->field_364 = info->field8;
    e->field_58 = info->field18;
    e->field_2e4 = info->field1c;
    copy3(e->light, light);
    copy3(e->angle, angle);
    copy3(e->position, position);
    e->direction[0] = e->direction[1] = e->direction[2] = 0.0f;

    switch (type) {
    case MU_SFX_MODEL_ARROW: {
        /* 0x013cb34d */
        e->blend_mesh = 1;
        e->velocity = 1.0f;
        e->lifetime = 30;
        uint16_t s = info->word4;
        if (subtype != 6 && s != 0x7e7 && s != 0x7fc && s != 0x7fd && s != 0x7fe && s != 0x2d7) {
            float m[12], p[3];
            static const float offset[3] = {-10.0f, -60.0f, 135.0f};
            mu_angle_matrix(e->angle, m);
            mu_vector_rotate(offset, m, p);
            e->position[0] = e->position[0] + p[0];
            e->position[1] = e->position[1] + p[1];
            e->position[2] = e->position[2] + p[2];
        }
        /* the type chain's default 0x013cd0f2 */
        e->scale = F_0_8;
        e->direction[1] = -70.0f;
        if (subtype == 2 || subtype == 6) {
            /* 0x013cd121: a 0x46c effect follows the arrow */
            call_effect(env, e, 0x46c, e->position, e->angle, e->light, 0, -2);
            e->field_78 = 0;
            e->client_hit = 1;
        }
        e->serial = env ? env->serial : 0;     /* 0x013cd66f */
        break;
    }
    case MU_SFX_MODEL_FIRE: {
        /* 0x013d2f05; subtype 1 takes the default branch 0x013d4086 */
        e->blend_mesh = 1;
        e->lifetime = 60;
        e->scale = (float)(8 + smod(env_rand(env), 4)) * F_0_1;
        e->position[2] = e->position[2] + 120.0f;
        e->direction[0] = 0.0f;
        e->direction[1] = -50.0f;
        e->direction[2] = 0.0f;
        break;
    }
    case MU_SFX_BITMAP_THUNDER:
        /* 0x013c5bc1 */
        e->lifetime = 20;
        e->direction[0] = 0.0f;
        e->direction[1] = -60.0f;
        e->direction[2] = 0.0f;
        e->position[2] = e->position[2] + 100.0f;
        break;
    case MU_SFX_BITMAP_MAGIC_GROUND2:
        /* 0x013c80a3 */
        e->lifetime = 20;
        break;
    default:
        break;
    }
    return 1;
}

/* ---------------------------------------------------------------- MoveEffect */

void mu_sfx_effect_advance(mu_sfx_effect *e, int rotate)
{
    /* 0x0150df8e */
    if (rotate) {
        float a[3], m[12], p[3];
        copy3(a, e->angle);
        mu_angle_matrix(a, m);
        mu_vector_rotate(e->direction, m, p);
        e->position[0] = e->position[0] + p[0];
        e->position[1] = e->position[1] + p[1];
        e->position[2] = e->position[2] + p[2];
    } else {
        e->position[0] = e->position[0] + e->direction[0];
        e->position[1] = e->position[1] + e->direction[1];
        e->position[2] = e->position[2] + e->direction[2];
    }
}

void mu_sfx_check_magic(mu_sfx_effect *e, const mu_sfx_env *env)
{
    /* 0x013be199 */
    const mu_sfx_object *t = env_object(env, e->owner);
    if (!t || !t->live || !t->visible)
        return;
    float dx = e->position[0] - t->position[0];
    float dy = e->position[1] - t->position[1];
    float d = (float)sqrt((double)(dx * dx + dy * dy));
    if (!(100.0f >= d))
        return;
    e->lifetime = 1;
    static const float white[3] = {1.0f, 1.0f, 1.0f};
    if (e->type == MU_SFX_MODEL_FIRE && e->subtype == 1) {
        for (int k = 0; k < 2; ++k) {
            int32_t stone = MU_SFX_MODEL_STONE1 + smod(env_rand(env), 2);
            call_effect(env, e, stone, e->position, e->angle, e->light, 0, MU_SFX_NO_OWNER);
        }
    } else if (e->type == MU_SFX_BITMAP_THUNDER) {
        call_particle(env, e, MU_SFX_BITMAP_SPARK3, e->position, e->angle, white, 1, 6.0f, MU_SFX_NO_OWNER);
    }
}

static void check(const mu_sfx_env *env, mu_sfx_effect *e, int32_t routine)
{
    if (!env || env->report_checks || routine == MU_SFX_CALL_CHECK_ARROW)
        call_plain(env, e, routine);
    else
        mu_sfx_check_magic(e, env);
}

/* Heal 0x0142d83b: three JointEnergy01 ribbons converge on the effect. */
static void heal_joints(mu_sfx_effect *e, const mu_sfx_env *env)
{
    static const float reach[3] = {0.0f, -200.0f, 0.0f};
    for (int k = 0; k < 3; ++k) {
        float a[3], m[12], p[3], s[3];
        a[0] = (float)(env_rand(env) % 90);
        a[1] = 0.0f;
        a[2] = (float)(env_rand(env) % 360);
        mu_angle_matrix(a, m);
        mu_vector_rotate(reach, m, p);
        s[0] = e->position[0] - p[0];
        s[1] = e->position[1] - p[1];
        s[2] = e->position[2] - p[2];
        s[2] = s[2] + 120.0f;
        call_joint(env, e, MU_SFX_BITMAP_JOINT_ENERGY, s, e->position, a, e->subtype == 5 ? 11 : e->subtype,
                   e->owner, 5.0f);
    }
}

int mu_sfx_effect_move(mu_sfx_effect *e, const mu_sfx_env *env)
{
    int32_t type = e->type, sub = e->subtype;
    int supported = (type == MU_SFX_MODEL_ARROW && (sub == 0 || sub == 2)) || (type == MU_SFX_MODEL_FIRE && sub == 1) ||
                    (type == MU_SFX_BITMAP_THUNDER && sub == 0) || (type == MU_SFX_BITMAP_MAGIC_GROUND2 && sub == 1);
    if (!supported)
        return 0;
    /* prologue 0x0142fd2d: Luminosity = (rand % 4 + 7) * 0.1, dimmed over the
     * last five steps */
    float lum = (float)(smod(env_rand(env), 4) + 7) * F_0_1;
    if (e->lifetime < 5) {
        lum = lum - (float)(5 - e->lifetime) * F_0_2;
        if (0.0f > lum)
            lum = 0.0f;
    }
    float light[3] = {1.0f, 1.0f, 1.0f};
    if (e->owner >= 0) {
        const mu_sfx_object *o = env_object(env, e->owner);
        if (o)
            copy3(e->start, o->position);
        e->start[2] = env_height(env, e->start[0], e->start[1]);
    }

    switch (type) {
    case MU_SFX_MODEL_ARROW:
        /* 0x01464abf */
        light[0] = lum * F_0_8;
        light[1] = lum * 0.5f;
        light[2] = lum * F_0_2;
        call_terrain_light(env, e, light, 2);
        call_particle(env, e, MU_SFX_BITMAP_FIRE, e->position, e->angle, light, 0, 1.0f, MU_SFX_NO_OWNER);
        check(env, e, MU_SFX_CALL_CHECK_ARROW);
        break;
    case MU_SFX_MODEL_FIRE:
        /* 0x0146bff4, subtype 1 */
        e->blend_light = 0.0f;
        light[0] = lum * 1.0f;
        light[1] = lum * F_0_1;
        light[2] = lum * 0.0f;
        call_terrain_light(env, e, light, 2);
        call_particle(env, e, MU_SFX_BITMAP_FIRE, e->position, e->angle, light, 5, 1.0f, MU_SFX_NO_OWNER);
        check(env, e, MU_SFX_CALL_CHECK_MAGIC);
        break;
    case MU_SFX_BITMAP_THUNDER:
        /* 0x014468ac, subtype 0 */
        lum = (float)e->lifetime * F_0_2;
        light[0] = light[1] = light[2] = lum;
        call_particle(env, e, MU_SFX_BITMAP_THUNDER, e->position, e->angle, light, 0, 1.0f, MU_SFX_NO_OWNER);
        call_particle(env, e, MU_SFX_BITMAP_SPARK3, e->position, e->angle, light, 0, 4.0f, MU_SFX_NO_OWNER);
        light[0] = lum * F_0_2;
        light[1] = lum * F_0_4;
        light[2] = lum * 1.0f;
        call_terrain_light(env, e, light, 2);
        check(env, e, MU_SFX_CALL_CHECK_MAGIC);
        break;
    case MU_SFX_BITMAP_MAGIC_GROUND2:
        /* 0x0143fbda, subtypes >= 1 except 4, 6..13, 19 */
        heal_joints(e, env);
        break;
    default:
        break;
    }

    /* after the switch 0x014eca00: the animation of model types */
    if (type >= 0x190 && type < 0x7a4) {
        int16_t keys = 1;
        int has_model = env && env->model ? env->model(env->context, type, e->action, &keys) : 1;
        if (!has_model)
            return 1;   /* 0x014ecd76: no model, nothing else this step */
        if (e->action != 0xff) {
            mu_sfx_call c;
            memset(&c, 0, sizeof c);
            c.routine = MU_SFX_CALL_ANIMATION;
            c.type = type;
            c.scale = e->velocity;
            c.owner = -2;
            if (!env_call(env, &c, e)) {
                e->frame = (float)keys;
                e->action = 0xff;
            }
        }
    }
    /* the second switch 0x014ece4f: Fire subtype 14 moves without rotation,
     * the default 0x0150df8e(o, 1) */
    if (!(type >= 0x7f4e && type <= 0x7f50))
        mu_sfx_effect_advance(e, !(type == MU_SFX_MODEL_FIRE && sub == 14));

    /* lifetime 0x0150cb88 */
    if (type == MU_SFX_MODEL_FIRE || type == 0x7ef7) {
        e->lifetime = e->lifetime - 1;
        if (e->lifetime <= 0) {
            call_plain(env, e, MU_SFX_CALL_DELETE);
            e->live = 0;
        }
        /* subtype 3 (MODEL_FIRE) / 0 (0x7ef7) with an odd LifeTime moves twice (not reconstructed) */
        return 1;
    }
    if (e->lifetime <= 0) {
        call_plain(env, e, MU_SFX_CALL_DELETE);
        e->live = 0;
    }
    e->lifetime = e->lifetime - 1;
    return 1;
}
