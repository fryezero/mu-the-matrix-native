/* The client's older effect system for skills and projectiles
 * (NATIVE-COMBAT-002). See skill_fx.h and docs/research/client-combat.md.
 * Build with -ffp-contract=off. */
#include "skill_fx.h"

#include <math.h>
#include <string.h>

#include "../record-math/record_math.h"
#include "../movement/client_movement.h"

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

static int effect_supported(int32_t type, int32_t sub)
{
    switch (type) {
    case MU_SFX_MODEL_ARROW: return sub == 0 || sub == 2;
    case MU_SFX_MODEL_FIRE: return sub == 1;
    case MU_SFX_BITMAP_THUNDER: return sub == 0;
    case MU_SFX_BITMAP_MAGIC_GROUND2: return sub == 1;
    case MU_SFX_MODEL_CIRCLE: case MU_SFX_MODEL_CIRCLE_LIGHT: case MU_SFX_MODEL_INFERNO:
    case MU_SFX_MODEL_LASER: case MU_SFX_TWISTING_SLASH: case MU_SFX_TWISTING_SWIRL:
        return sub == 0;
    case MU_SFX_MODEL_STONE1: case MU_SFX_MODEL_STONE2: return sub == 0 || sub == 1;
    default: return 0;
    }
}

static int is_hero_owner(const mu_sfx_effect *e, const mu_sfx_env *env)
{
    return env && env->hero_object >= 0 && e->owner == env->hero_object;
}

static void call_serial_step(const mu_sfx_env *env, mu_sfx_effect *e)
{
    mu_sfx_call c;
    memset(&c, 0, sizeof c);
    c.routine = MU_SFX_CALL_SERIAL;
    c.owner = MU_SFX_NO_OWNER;
    env_call(env, &c, e);
}

/* the hero's area attack request 0x013bc25e(skill, range, position, serial, key, 0, 5, 0) */
static void call_area(const mu_sfx_env *env, mu_sfx_effect *e, float range)
{
    mu_sfx_call c;
    memset(&c, 0, sizeof c);
    c.routine = MU_SFX_CALL_AREA;
    c.type = e->skill;
    c.scale = range;
    copy3(c.position, e->position);
    c.subtype = (uint8_t)e->serial;
    c.range = e->key;
    c.owner = MU_SFX_NO_OWNER;
    env_call(env, &c, e);
}

int mu_sfx_effect_create(mu_sfx_effect *e, int32_t type, int32_t subtype, const float position[3],
                         const float angle[3], const float light[3], int32_t owner, float scale,
                         const mu_sfx_info *info, const mu_sfx_env *env)
{
    memset(e, 0, sizeof *e);
    if (!effect_supported(type, subtype))
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
    case MU_SFX_MODEL_CIRCLE:
        /* 0x013cff78 */
        e->lifetime = 45;
        e->blend_mesh = 0;
        if (subtype == 0 && is_hero_owner(e, env)) {
            e->serial = env->serial;
            call_serial_step(env, e);
            call_area(env, e, 300.0f);
        }
        break;
    case MU_SFX_MODEL_CIRCLE_LIGHT:
        /* 0x013d00c2 */
        e->lifetime = 40;
        e->blend_mesh = 0;
        break;
    case MU_SFX_MODEL_INFERNO:
        /* 0x013c9ba4, subtype 0: 0x013c9bfc */
        e->blend_mesh = -2;
        e->scale = F_0_9;
        e->velocity = 0.5f;
        e->light[0] = e->light[1] = e->light[2] = F_0_8;
        e->lifetime = 15;
        if (is_hero_owner(e, env) && subtype < 2) {
            e->serial = env->serial;
            call_area(env, e, 400.0f);
        }
        break;
    case MU_SFX_MODEL_LASER:
        /* 0x013ce3ea, subtype 0 */
        e->lifetime = 1;
        e->blend_mesh = 0;
        e->blend_light = e->light[0];
        e->scale = f32bits(0x3fa66666u);   /* 1.3 */
        e->field_80 = 0x80;                /* RenderObject draws it with flags 0x82 */
        break;
    case MU_SFX_TWISTING_SLASH:
        /* 0x013ce7e5 */
        e->lifetime = 5;
        call_serial_step(env, e);
        break;
    case MU_SFX_TWISTING_SWIRL:
        /* 0x013ce80d */
        e->lifetime = 25;
        e->serial = env ? env->serial : 0;
        break;
    case MU_SFX_MODEL_STONE1:
    case MU_SFX_MODEL_STONE2: {
        /* 0x013d49a0: subtype 0 flings the stone out (0x013d49cc), subtype 1 lifts it (0x013d4b0a) */
        float v[3] = {0.0f, 0.0f, 0.0f}, m[12];
        if (subtype == 0)
            v[1] = (float)(smod(env_rand(env), 256) + 64) * F_0_1;
        e->lifetime = smod(env_rand(env), 16) + 32;
        e->scale = (float)(smod(env_rand(env), 4) + 8) * F_0_1;
        e->angle[2] = (float)(env_rand(env) % 360);
        mu_angle_matrix(e->angle, m);
        mu_vector_rotate(v, m, e->direction);
        e->gravity = (float)(smod(env_rand(env), 16) + 8);
        break;
    }
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
    if (!effect_supported(type, sub))
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
    case MU_SFX_MODEL_CIRCLE:
        /* 0x01457a30 */
        e->blend_light = (float)e->lifetime * F_0_1;
        break;
    case MU_SFX_MODEL_CIRCLE_LIGHT: {
        /* 0x014581dd, subtype 0 */
        int32_t odds = 4;
        if (e->lifetime >= 30)
            e->blend_light = (float)(40 - e->lifetime) * F_0_1;
        else
            e->blend_light = (float)e->lifetime * F_0_1;
        e->blend_u = -(float)e->lifetime * f32bits(0x3c23d70au);   /* 0.01 */
        {
            mu_sfx_call q;
            memset(&q, 0, sizeof q);
            q.routine = MU_SFX_CALL_QUAKE;
            q.scale = (float)(env_rand(env) % 6 - 6) * F_0_1;
            q.owner = MU_SFX_NO_OWNER;
            env_call(env, &q, e);
        }
        if (env_rand(env) % odds == 0) {
            /* a stone flies out of the circle */
            float v[3] = {0.0f, 0.0f, 0.0f}, a[3] = {0.0f, 0.0f, 0.0f}, m[12], p[3];
            v[1] = (float)(env_rand(env) % 300);
            a[2] = (float)(env_rand(env) % 360);
            mu_angle_matrix(a, m);
            mu_vector_rotate(v, m, p);
            p[0] = p[0] + e->position[0];
            p[1] = p[1] + e->position[1];
            p[2] = p[2] + e->position[2];
            call_effect(env, e, MU_SFX_MODEL_STONE1 + smod(env_rand(env), 2), p, e->angle, e->light, 1,
                        MU_SFX_NO_OWNER);
        }
        light[0] = lum * 1.0f;
        light[1] = lum * F_0_8;
        light[2] = lum * F_0_2;
        call_terrain_light(env, e, light, 4);
        break;
    }
    case MU_SFX_MODEL_INFERNO:
        /* 0x0144e52d, subtype 0 (< 4, not 2) */
        e->blend_light = (float)e->lifetime / 20.0f;
        light[0] = -lum * 0.5f;
        light[1] = -lum * 0.5f;
        light[2] = -lum * 0.5f;
        call_terrain_light(env, e, light, 5);
        break;
    case MU_SFX_MODEL_LASER:
        /* 0x0144f626, subtype 0: nothing */
        break;
    case MU_SFX_TWISTING_SLASH:
        /* 0x0144f7ae: one swirl piece per step, subtype 4 - LifeTime, owned by the caster */
        {
            mu_sfx_call c;
            memset(&c, 0, sizeof c);
            c.routine = MU_SFX_CALL_EFFECT;
            c.type = MU_SFX_TWISTING_SWIRL;
            c.subtype = 4 - e->lifetime;
            c.owner = e->owner;
            copy3(c.position, e->position);
            copy3(c.angle, e->angle);
            copy3(c.light, e->light);
            env_call(env, &c, e);
        }
        break;
    case MU_SFX_TWISTING_SWIRL: {
        /* 0x0144f829: the piece circles the caster's feet */
        switch (sub) {
        case 1: e->alpha = f32bits(0x3f19999au); break;   /* 0.6 */
        case 2: e->alpha = 0.5f; break;
        case 3: e->alpha = F_0_4; break;
        case 4: e->alpha = F_0_3; break;
        default: break;
        }
        const mu_sfx_object *o = env_object(env, e->owner);
        int16_t weapon = o ? o->weapon : 0;
        float reach[3] = {0.0f, (weapon >= 0x600 && weapon < 0x800) ? -180.0f : -150.0f, 0.0f}, m[12], p[3];
        mu_angle_matrix(e->angle, m);
        mu_vector_rotate(reach, m, p);
        e->position[0] = p[0] + e->start[0];
        e->position[1] = p[1] + e->start[1];
        e->position[2] = p[2] + e->start[2];
        e->angle[2] = e->angle[2] - 18.0f;
        call_particle(env, e, 0x7f5a, e->position, e->angle, e->light, 3, 1.0f, MU_SFX_NO_OWNER);
        light[0] = lum * F_0_3;
        light[1] = lum * F_0_3;
        light[2] = lum * F_0_3;
        call_terrain_light(env, e, light, 3);
        light[0] = light[1] = light[2] = 1.0f;
        for (int k = 0; k < 4; ++k) {
            float a[3], q[3];
            a[0] = (float)(env_rand(env) % 60 - 30);
            a[1] = 0.0f;
            a[2] = (float)(env_rand(env) % 30 + 90);
            a[0] = a[0] + e->angle[0];
            a[1] = a[1] + e->angle[1];
            a[2] = a[2] + e->angle[2];
            copy3(q, e->position);
            q[0] = (float)(env_rand(env) % 20 - 10) + q[0];
            q[1] = (float)(env_rand(env) % 20 - 10) + q[1];
            call_joint(env, e, 0x7fd5, q, q, a, 0, MU_SFX_NO_OWNER, 10.0f);
            if (k == 0)
                call_particle(env, e, 0x7f25, q, a, light, 0, 1.0f, MU_SFX_NO_OWNER);
        }
        {
            float q[3];
            copy3(q, e->position);
            q[2] = q[2] + 20.0f;
            const float glow[3] = {1.0f, F_0_8, f32bits(0x3f19999au)};
            mu_sfx_call c;
            memset(&c, 0, sizeof c);
            c.routine = 0x01692eb7;   /* CreateSprite(flare01 0x7ef7, pos, 2, light, the effect, 0) */
            c.type = 0x7ef7;
            copy3(c.position, q);
            c.scale = 2.0f;
            copy3(c.light, glow);
            c.owner = -2;
            env_call(env, &c, e);
        }
        break;
    }
    case MU_SFX_MODEL_STONE1:
    case MU_SFX_MODEL_STONE2:
        if (sub == 0) {
            /* 0x01459d34: bounce on the ground */
            e->position[0] = e->position[0] + e->direction[0];
            e->position[1] = e->position[1] + e->direction[1];
            e->position[2] = e->position[2] + e->direction[2];
            e->direction[0] = F_0_9 * e->direction[0];
            e->direction[1] = F_0_9 * e->direction[1];
            e->direction[2] = F_0_9 * e->direction[2];
            e->position[2] = e->position[2] + e->gravity;
            e->gravity = e->gravity - 3.0f;
            float h = env_height(env, e->position[0], e->position[1]);
            if (h > e->position[2]) {
                e->position[2] = h;
                e->gravity = -e->gravity * 0.5f;
                e->lifetime = e->lifetime - 4;
                e->angle[0] = e->angle[0] - e->scale * 128.0f;
            } else {
                e->angle[0] = e->angle[0] - e->scale * 32.0f;
            }
            if (env_rand(env) % 10 == 0)
                call_particle(env, e, MU_SFX_BITMAP_FIRE, e->position, e->angle, e->light, env_rand(env) % 3 + 1,
                              1.0f, MU_SFX_NO_OWNER);
        } else {
            /* 0x0145a0d2: rises */
            float m[12], p[3];
            mu_angle_matrix(e->angle, m);
            mu_vector_rotate(e->direction, m, p);
            e->position[0] = e->position[0] + p[0];
            e->position[1] = e->position[1] + p[1];
            e->position[2] = e->position[2] + p[2];
            e->direction[0] = F_0_9 * e->direction[0];
            e->direction[1] = F_0_9 * e->direction[1];
            e->direction[2] = F_0_9 * e->direction[2];
            e->position[2] = e->position[2] + e->gravity;
            e->gravity = e->gravity + 0.5f;
        }
        break;
    default:
        break;
    }

    /* after the switch 0x014eca00: types 0x453, 0x454, 0x461, ... skip the
     * animation and the motion (0x014ecb6e) */
    if (type == MU_SFX_TWISTING_SLASH || type == MU_SFX_TWISTING_SWIRL)
        goto lifetime;
    /* the animation of model types */
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

lifetime:
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

/* ---------------------------------------------------------------- particles */

int mu_sfx_particle_create(mu_sfx_particle *p, int32_t type, const float position[3], const float angle[3],
                           const float light[3], int32_t subtype, float scale, int32_t owner, int32_t arg8,
                           const mu_sfx_env *env)
{
    memset(p, 0, sizeof *p);
    int supported = owner < 0 && ((type == MU_SFX_BITMAP_FIRE && (subtype == 0 || subtype == 5)) ||
                                  (type == MU_SFX_BITMAP_THUNDER && subtype == 0) ||
                                  (type == MU_SFX_BITMAP_SPARK3 && (subtype == 0 || subtype == 1)));
    if (!supported)
        return 0;
    /* common initialisation 0x015ae7e4..0x015aebed */
    p->live = 1;
    p->type = type;
    p->tex_type = type;
    p->subtype = subtype;
    copy3(p->position, position);
    copy3(p->start, position);
    copy3(p->light, light);
    p->scale = scale;
    p->gravity = 0.0f;
    p->lifetime = 2;
    p->frame = 0;
    p->owner = owner;
    p->rotation = 0.0f;
    p->moving = 1;
    p->time = 0.0f;
    p->arg8 = arg8;
    copy3(p->angle, angle);
    copy3(p->start_angle, angle);
    p->velocity[0] = p->velocity[1] = p->velocity[2] = 0.0f;
    p->owner_position[0] = p->owner_position[1] = p->owner_position[2] = 0.0f;
    switch (type) {
    case MU_SFX_BITMAP_FIRE:
        /* subtype 0: 0x015ba5b3; subtypes 5 and 17: 0x015ba7e1 (the scale argument counts) */
        p->lifetime = 24;
        p->velocity[0] = 0.0f;
        p->velocity[1] = -(float)(smod(env_rand(env), 16) + 32) * F_0_1;
        p->velocity[2] = 0.0f;
        if (subtype == 0)
            p->scale = (float)(smod(env_rand(env), 64) + 128) * f32bits(0x3c23d70au);   /* 0.01 */
        else
            p->scale = (float)(smod(env_rand(env), 64) + 128) * scale * f32bits(0x3c23d70au);
        p->rotation = (float)(env_rand(env) % 360);
        break;
    case MU_SFX_BITMAP_THUNDER:
        /* 0x015bda75 */
        p->scale = (float)(smod(env_rand(env), 8) + 6) * scale * F_0_1;
        p->rotation = (float)(env_rand(env) % 360);
        p->gravity = 20.0f;
        break;
    case MU_SFX_BITMAP_SPARK3:
        /* subtype 1: 0x015dd4c7 */
        if (subtype == 1) {
            float m[12];
            static const float burst[3] = {0.0f, -50.0f, 0.0f};
            p->angle[0] = (float)(env_rand(env) % 360);
            p->angle[1] = (float)(env_rand(env) % 360);
            p->angle[2] = (float)(env_rand(env) % 360);
            mu_angle_matrix(p->angle, m);
            mu_vector_rotate(burst, m, p->velocity);
        }
        break;
    default:
        break;
    }
    return 1;
}

int mu_sfx_particle_move(mu_sfx_particle *p, float time_step)
{
    /* loop head 0x01616f12: records without life are erased */
    if (p->lifetime <= 0 || !p->live)
        return 0;
    if (p->moving) {
        /* MovePosition 0x012af52d */
        float m[12], d[3];
        mu_angle_matrix(p->angle, m);
        mu_vector_rotate(p->velocity, m, d);
        p->position[0] = p->position[0] + d[0];
        p->position[1] = p->position[1] + d[1];
        p->position[2] = p->position[2] + d[2];
    }
    switch (p->type) {
    case MU_SFX_BITMAP_FIRE:
        /* subtype 0: 0x01628302; 5: 0x016283f6 (also turns) */
        p->gravity = p->gravity + f32bits(0x3b83126fu);   /* 0.004 */
        p->scale = p->scale - f32bits(0x3d23d70au);       /* 0.04 */
        if (p->subtype == 5)
            p->rotation = p->rotation + 5.0f;
        p->frame = (23 - p->lifetime) / 6;
        p->position[2] = p->gravity * 10.0f + p->position[2];
        break;
    case MU_SFX_BITMAP_THUNDER:
        /* 0x0162bee7 */
        p->rotation = p->rotation + p->gravity;
        break;
    case MU_SFX_BITMAP_SPARK3:
        /* 0x01650c17 / 0x01650c74 */
        p->scale = p->scale - (p->subtype == 1 ? 2.0f : 0.5f);
        if (F_0_2 > p->scale)
            p->live = 0;
        break;
    default:
        break;
    }
    /* tail 0x0168ee31 */
    p->lifetime = p->lifetime - 1;
    p->time = p->time + time_step;
    return 1;
}

int mu_sfx_particle_render(const mu_sfx_particle *p, const mu_sfx_bitmap_info *bitmap, uint8_t mode,
                           mu_sfx_sprite *sprite)
{
    if (mode == 1 && p->position[2] > 350.0f)
        return 0;
    if (mode == 2 && 300.0f >= p->position[2])
        return 0;
    memset(sprite, 0, sizeof *sprite);
    float width = bitmap->width * p->scale, height = bitmap->height * p->scale;
    sprite->additive = bitmap->components == 3;
    sprite->bitmap = p->tex_type;
    copy3(sprite->position, p->position);
    copy3(sprite->light, p->light);
    sprite->axes = 4;
    sprite->width = width;
    sprite->height = height;
    sprite->rotation = p->rotation;
    sprite->u = 0.0f;
    sprite->v = 0.0f;
    sprite->uw = 1.0f;
    sprite->vh = 1.0f;
    if (p->type == MU_SFX_BITMAP_FIRE) {
        /* 0x01597adf (subtype 0: the angle's x as rotation) / 0x015978bb */
        sprite->width = width * 0.25f;
        sprite->rotation = p->subtype == 0 ? p->angle[0] : p->rotation;
        sprite->u = (float)(p->frame % 4) * 0.25f;
        sprite->uw = 0.25f;
    }
    return 1;
}

void mu_sfx_sprite_corners(const float camera[12], const mu_sfx_sprite *s, float corners[4][3], float uv[4][2])
{
    float eye[3];
    for (int r = 0; r < 3; ++r)
        eye[r] = ((camera[4 * r] * s->position[0] + camera[4 * r + 1] * s->position[1]) +
                  camera[4 * r + 2] * s->position[2]) + camera[4 * r + 3];
    float w = s->width * 0.5f, h = s->height * 0.5f;
    if (s->rotation == 0.0f) {
        const float sx[4] = {-1.0f, 1.0f, 1.0f, -1.0f}, sy[4] = {-1.0f, -1.0f, 1.0f, 1.0f};
        for (int k = 0; k < 4; ++k) {
            corners[k][0] = sx[k] < 0.0f ? eye[0] - w : eye[0] + w;
            corners[k][1] = sy[k] < 0.0f ? eye[1] - h : eye[1] + h;
            corners[k][2] = eye[2];
        }
    } else {
        float a[3] = {0.0f, 0.0f, 0.0f}, m[12];
        if (s->axes & 1)
            a[0] = s->rotation;
        if (s->axes & 2)
            a[1] = s->rotation;
        if (s->axes & 4)
            a[2] = s->rotation;
        mu_angle_matrix(a, m);
        const float local[4][3] = {{-w, -h, 0.0f}, {w, -h, 0.0f}, {w, h, 0.0f}, {-w, h, 0.0f}};
        for (int k = 0; k < 4; ++k) {
            mu_vector_rotate(local[k], m, corners[k]);
            corners[k][0] = corners[k][0] + eye[0];
            corners[k][1] = corners[k][1] + eye[1];
            corners[k][2] = corners[k][2] + eye[2];
        }
    }
    uv[0][0] = s->u;
    uv[0][1] = s->v;
    uv[1][0] = s->u + s->uw;
    uv[1][1] = s->v;
    uv[2][0] = s->u + s->uw;
    uv[2][1] = s->v + s->vh;
    uv[3][0] = s->u;
    uv[3][1] = s->v + s->vh;
}

/* ---------------------------------------------------------------- joints */

static void joint_cross(mu_sfx_joint *j, const float m[12], int tail)
{
    /* corners 0..3 of a tail: pos + R(-w/2, 0, 0), R(w/2, 0, 0), R(0, 0, -w/2), R(0, 0, w/2) */
    float half_neg = -j->scale * 0.5f, half = j->scale * 0.5f;
    const float local[4][3] = {{half_neg, 0.0f, 0.0f}, {half, 0.0f, 0.0f}, {0.0f, 0.0f, half_neg},
                               {0.0f, 0.0f, half}};
    for (int c = 0; c < 4; ++c) {
        float p[3];
        mu_vector_rotate(local[c], m, p);
        j->tails[tail][c][0] = j->position[0] + p[0];
        j->tails[tail][c][1] = j->position[1] + p[1];
        j->tails[tail][c][2] = j->position[2] + p[2];
    }
}

int mu_sfx_joint_create(mu_sfx_joint *j, int32_t type, const float position[3], const float target_position[3],
                        const float angle[3], int32_t subtype, int32_t target, float scale, uint16_t key,
                        uint16_t skill, uint8_t byte10, uint16_t word13, int32_t arg14, const mu_sfx_env *env)
{
    int supported = (type == MU_SFX_BITMAP_JOINT_ENERGY && subtype == 1) ||
                    (type == MU_SFX_BITMAP_JOINT_SPIRIT && subtype == 0);
    if (!supported)
        return 0;
    /* common part 0x0153b0a6 */
    j->live = 1;
    j->type = type;
    j->tex_type = type;
    j->subtype = subtype;
    j->render_type = 1;
    j->faces = 3;
    j->reached = 0;
    j->key = key;
    j->skill = skill;
    j->velocity = 0.0f;
    j->target = -1;
    j->tail_update = 1;
    j->field_64 = 0;
    j->field_a24 = 0;
    j->field_a25 = 0;
    j->field_a3c = byte10;
    j->field_a44 = word13;
    copy3(j->position, position);
    j->time = 0.0f;
    copy3(j->start, j->position);
    copy3(j->angle, angle);
    j->brightness = 1.0f;
    j->field_a54 = 0.0f;
    j->moving = 1;
    j->field_a60 = arg14;
    j->light[0] = j->light[1] = j->light[2] = 1.0f;
    j->jitter[0] = j->jitter[1] = j->jitter[2] = 0.0f;
    if (target < 0)
        copy3(j->target_position, target_position);   /* 0x0153b385: no target object */
    j->target = target;
    j->num_tails = 0;
    {
        /* the first tail, from the record's previous width (0x0153b676) */
        float m[12];
        mu_angle_matrix(j->angle, m);
        joint_cross(j, m, 0);
    }
    switch (type) {
    case MU_SFX_BITMAP_JOINT_ENERGY:
        /* 0x0153e28e */
        j->lifetime = 12;
        j->scale = scale;
        j->max_tails = 2;
        j->velocity = 0.0f;
        break;
    case MU_SFX_BITMAP_JOINT_SPIRIT:
        /* 0x01540809, subtype 0: 0x01540836 */
        j->render_type = 3;
        j->serial = env ? env->serial : 0;
        j->velocity = 70.0f;
        j->lifetime = 49;
        j->scale = scale;
        j->max_tails = 6;
        if (j->skill == 0x7f5) {
            /* 0x01540893: an additive purple variant */
            j->render_type = 1;
            j->light[0] = f32bits(0x3ea3d70au);   /* 0.32 */
            j->light[1] = f32bits(0x3e2e147bu);   /* 0.17 */
            j->light[2] = F_0_4;
        }
        break;
    default:
        break;
    }
    if (j->max_tails > MU_SFX_JOINT_TAILS)
        j->max_tails = MU_SFX_JOINT_TAILS;   /* 0x0155361d */
    return 1;
}

/* MoveHumming 0x012af2f1(position, angle, target, turn) */
static void move_humming(const float position[3], float angle[3], const float target[3], float turn)
{
    float a = mu_create_angle(position[0], position[1], target[0], target[1]);
    angle[2] = mu_turn_angle2(angle[2], a, turn);
    float d[3] = {position[0] - target[0], position[1] - target[1], position[2] - target[2]};
    float h = (float)sqrt((double)(d[0] * d[0] + d[1] * d[1]));
    float b = mu_create_angle(position[2], h, target[2], 0.0f);
    angle[0] = mu_turn_angle2(angle[0], 360.0f - b, turn);
}

/* 0x01553ba6(j, matrix, 0) */
static void joint_tail_shift(mu_sfx_joint *j, const float m[12])
{
    j->num_tails = j->num_tails + 1;
    if (j->num_tails > j->max_tails - 1)
        j->num_tails = j->max_tails - 1;
    for (int i = j->num_tails - 1; i >= 0; --i)
        for (int c = 0; c < 4; ++c)
            copy3(j->tails[i + 1][c], j->tails[i][c]);
    joint_cross(j, m, 0);
}

int mu_sfx_joint_move(mu_sfx_joint *j, const mu_sfx_env *env, float time_step, int wall_scene, uint16_t wall,
                      int is_hero_target)
{
    int supported = (j->type == MU_SFX_BITMAP_JOINT_ENERGY && j->subtype == 1) ||
                    (j->type == MU_SFX_BITMAP_JOINT_SPIRIT && j->subtype == 0);
    if (!supported)
        return 0;
    float m[12] = {0};
    float d0 = j->position[0] - j->target_position[0];
    float d1 = j->position[1] - j->target_position[1];
    if (j->moving) {
        mu_angle_matrix(j->angle, m);
        if (!(j->velocity == 0.0f)) {
            float v[3] = {0.0f, -j->velocity, 0.0f}, p[3];
            mu_vector_rotate(v, m, p);
            j->position[0] = j->position[0] + p[0];
            j->position[1] = j->position[1] + p[1];
            j->position[2] = j->position[2] + p[2];
        }
    }
    const mu_sfx_object *t = env_object(env, j->target);
    switch (j->type) {
    case MU_SFX_BITMAP_JOINT_ENERGY: {
        /* 0x0155ccae, subtype 1 */
        j->velocity = j->velocity + 4.0f;
        if (j->target < 0)
            break;
        float goal[3] = {0.0f, 0.0f, 0.0f};
        if (t)
            copy3(goal, t->position);
        goal[2] = goal[2] + 120.0f;
        move_humming(j->position, j->angle, goal, 10.0f);
        float l = (float)(12 - j->lifetime) * F_0_1;
        j->light[0] = l * F_0_4;
        j->light[1] = l * f32bits(0x3f19999au);   /* 0.6 */
        j->light[2] = l * 1.0f;
        if (j->lifetime == 1) {
            /* the arrival flash: CreateSprite(Shiny02 0x7f67, goal, (rand % 8 + 8) * 0.2, light, target, rand % 360) */
            mu_sfx_call c;
            memset(&c, 0, sizeof c);
            c.routine = MU_SFX_CALL_SPRITE;
            c.type = 0x7f67;
            c.angle[0] = (float)(env_rand(env) % 360);
            c.scale = (float)(smod(env_rand(env), 8) + 8) * F_0_2;
            copy3(c.position, goal);
            copy3(c.light, j->light);
            c.owner = j->target;
            env_call(env, &c, NULL);
        }
        break;
    }
    case MU_SFX_BITMAP_JOINT_SPIRIT: {
        /* 0x01561038, subtype 0: 0x0156105e */
        if (j->scale == 80.0f) {
            /* the wide spirit leaves a Laser01 (0x421) effect each step */
            call_effect(env, NULL, 0x421, j->position, j->angle, j->light, 0, MU_SFX_NO_OWNER);
            if (wall_scene && (wall & 0x100)) {
                j->velocity = 0.0f;
                j->lifetime = (int32_t)((float)j->lifetime / 5.0f);
                goto tail;
            }
            if (j->lifetime % 15 == 0 && is_hero_target) {
                mu_sfx_call c;
                memset(&c, 0, sizeof c);
                c.routine = MU_SFX_CALL_AREA_ATTACK;
                c.type = j->skill;
                c.scale = 150.0f;
                copy3(c.position, j->position);
                c.subtype = j->serial;
                c.owner = -1;
                env_call(env, &c, NULL);
            }
        }
        if (j->target < 0)
            break;
        if (t)
            copy3(j->target_position, t->position);
        j->target_position[2] = j->target_position[2] + 80.0f;
        float dist = (float)sqrt((double)(d0 * d0 + d1 * d1));
        move_humming(j->position, j->angle, j->target_position, 10.0f);
        if (!j->reached && j->velocity * 2.0f >= dist)
            j->reached = 1;
        j->jitter[0] = (float)(smod(env_rand(env), 32) - 16) * F_0_2 + j->jitter[0];
        j->jitter[2] = (float)(smod(env_rand(env), 32) - 16) * F_0_8 + j->jitter[2];
        j->angle[0] = j->angle[0] + j->jitter[0];
        j->angle[2] = j->angle[2] + j->jitter[2];
        j->jitter[0] = j->jitter[0] * f32bits(0x3f19999au);   /* 0.6 */
        j->jitter[2] = j->jitter[2] * F_0_8;
        float h = env_height(env, j->position[0], j->position[1]);
        if (h + 100.0f > j->position[2]) {
            j->jitter[0] = 0.0f;
            j->angle[0] = -5.0f;
        }
        if (j->position[2] > h + 400.0f) {
            j->jitter[0] = 0.0f;
            j->angle[0] = 5.0f;
        }
        if (j->skill != 0x7f5) {
            float l = (float)j->lifetime * F_0_1;
            j->light[0] = l;
            j->light[1] = l;
            j->light[2] = l;
            float dark = -(float)(smod(env_rand(env), 4) + 4) * f32bits(0x3c23d70au);   /* 0.01 */
            const float shade[3] = {dark, dark, dark};
            mu_sfx_call c;
            memset(&c, 0, sizeof c);
            c.routine = MU_SFX_CALL_TERRAIN_LIGHT;
            c.position[0] = j->position[0];
            c.position[1] = j->position[1];
            copy3(c.light, shade);
            c.range = 4;
            c.owner = MU_SFX_NO_OWNER;
            env_call(env, &c, NULL);
        }
        break;
    }
    default:
        break;
    }
tail:
    /* 0x015896fb */
    if (j->tail_update)
        joint_tail_shift(j, m);
    j->time = j->time + time_step;
    j->lifetime = j->lifetime - 1;
    if (j->lifetime < 0)
        j->live = 0;
    return 1;
}

int mu_sfx_joint_render(const mu_sfx_joint *j, uint8_t mode, float color[3], int32_t *render_type,
                        mu_sfx_joint_quad *quads, int max)
{
    if (!j->live || j->num_tails <= 0 || !j->faces)
        return 0;
    if (mode == 1 && j->field_64 == 2)
        return 0;
    if (mode == 2 && j->field_64 == 1)
        return 0;
    *render_type = j->render_type;
    color[0] = j->light[0] * j->brightness;
    color[1] = j->light[1] * j->brightness;
    color[2] = j->light[2] * j->brightness;
    int n = 0;
    float span = (float)(j->max_tails - 1);
    for (int i = 0; i < j->num_tails; ++i) {
        float u0 = (float)(j->num_tails - i) / span;
        float u1 = (float)(j->num_tails - (i + 1)) / span;
        if ((j->faces & 1) && n < max) {
            mu_sfx_joint_quad *q = &quads[n++];
            copy3(q->position[0], j->tails[i][2]);
            copy3(q->position[1], j->tails[i][3]);
            copy3(q->position[2], j->tails[i + 1][3]);
            copy3(q->position[3], j->tails[i + 1][2]);
            q->uv[0][0] = u0; q->uv[0][1] = 1.0f;
            q->uv[1][0] = u0; q->uv[1][1] = 0.0f;
            q->uv[2][0] = u1; q->uv[2][1] = 0.0f;
            q->uv[3][0] = u1; q->uv[3][1] = 1.0f;
        }
        if ((j->faces & 2) && n < max) {
            mu_sfx_joint_quad *q = &quads[n++];
            copy3(q->position[0], j->tails[i][0]);
            copy3(q->position[1], j->tails[i][1]);
            copy3(q->position[2], j->tails[i + 1][1]);
            copy3(q->position[3], j->tails[i + 1][0]);
            q->uv[0][0] = u0; q->uv[0][1] = 0.0f;
            q->uv[1][0] = u0; q->uv[1][1] = 1.0f;
            q->uv[2][0] = u1; q->uv[2][1] = 1.0f;
            q->uv[3][0] = u1; q->uv[3][1] = 0.0f;
        }
    }
    return n;
}
