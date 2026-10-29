/* The client's older effect system for skills and projectiles
 * (NATIVE-COMBAT-002). See skill_fx.h and docs/research/client-combat.md.
 * Build with -ffp-contract=off. */
#include "skill_fx.h"
#include "../objects/world_warp.h"

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

static double f64bits(uint64_t bits)
{
    double value;
    memcpy(&value, &bits, sizeof value);
    return value;
}

#define F_0_01 f32bits(0x3c23d70au)  /* 0x01a7df00 */
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

/* cvttss2si: INT32_MIN for NaN and out-of-range values. */
static int32_t trunc_i32(float value)
{
    if (!(value > -2147483904.0f && value < 2147483648.0f))
        return INT32_MIN;
    return (int32_t)value;
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

/* RENDER-EFFECTS-004: CreateEffect with its info key word (the pieces' scale = key / 100);
 * the call carries the key in range. */
static void call_effect_key(const mu_sfx_env *env, mu_sfx_effect *e, int32_t type, const float position[3],
                            const float angle[3], const float light[3], int32_t owner, uint16_t key)
{
    mu_sfx_call c;
    memset(&c, 0, sizeof c);
    c.routine = MU_SFX_CALL_EFFECT;
    c.type = type;
    c.owner = owner;
    c.range = key;
    copy3(c.position, position);
    copy3(c.angle, angle);
    copy3(c.light, light);
    env_call(env, &c, e);
}

static void call_sound(const mu_sfx_env *env, mu_sfx_effect *e, int32_t sound)
{
    mu_sfx_call c;
    memset(&c, 0, sizeof c);
    c.routine = MU_SFX_CALL_SOUND;
    c.type = sound;
    c.owner = MU_SFX_NO_OWNER;
    env_call(env, &c, e);
}

/* TerrainWall[0x016d34cd(x / 100, y / 100)] */
static uint16_t call_wall(const mu_sfx_env *env, mu_sfx_effect *e, float x, float y)
{
    mu_sfx_call c;
    memset(&c, 0, sizeof c);
    c.routine = MU_SFX_CALL_WALL;
    c.subtype = trunc_i32(x / 100.0f);
    c.range = trunc_i32(y / 100.0f);
    c.owner = -2;
    return (uint16_t)(env && env->call ? env->call(env->context, &c, e) : 0);
}

/* VectorNormalize 0x00cff0d3 (the length it returns is unused here) */
static void vector_normalize(float v[3])
{
    const float length = sqrtf(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]);
    if (f32bits(0x358637bdu) > length) {   /* 1e-6 */
        v[0] = v[1] = v[2] = 0.0f;
        return;
    }
    for (int k = 0; k < 3; ++k)
        v[k] = v[k] / length;
}

static void kill_effect(const mu_sfx_env *env, mu_sfx_effect *e);

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

/* SetLive 0x0129f4a5(o, 0): live 0, then the record's cleanup 0x009b0451 (NATIVE-HELPERS-002). */
static void kill_effect(const mu_sfx_env *env, mu_sfx_effect *e)
{
    e->live = 0;
    call_plain(env, e, MU_SFX_CALL_KILL);
}

static uint32_t env_time(const mu_sfx_env *env)
{
    return env && env->time_ms ? env->time_ms(env->context) : 0u;
}

/* Fenrir's lightning 0x013e0fcd: a flash on a random bone of its owner's model (or a drift above it). */
static void fenrir_lightning_flash(mu_sfx_effect *e, const mu_sfx_env *env)
{
    static const float zero[3] = {0.0f, 0.0f, 0.0f};
    int32_t bone = -1;
    const int32_t r = smod(env_rand(env), 30);
    if (r >= 1 && r <= 2) {
        bone = 10;
    } else if (r == 3) {
        e->scale = e->scale - F_0_2;
        bone = 14;
    } else if (r >= 4 && r <= 5) {
        bone = 2;
    } else if (r >= 6 && r <= 7) {
        e->scale = e->scale - F_0_2;
        bone = smod(env_rand(env), 2) == 0 ? 0x32 : 0x33;
    } else if (r == 8) {
        e->scale = e->scale - F_0_2;
        bone = 0x35;
    } else if (r >= 9 && r <= 10) {
        kill_effect(env, e);
        e->alpha = 0.0f;
    } else {
        e->scale = e->scale + F_0_1;
        e->position[0] = (float)(smod(env_rand(env), 240) - 120) + e->position[0];
        e->position[1] = (float)(smod(env_rand(env), 10) - 5) + e->position[1];
        e->position[2] = e->position[2] + 110.0f;
    }
    if (bone >= 0 && env && env->owner_bone)   /* TransformPosition(owner model, bone, (0, 0, 0), position, 0) */
        env->owner_bone(env->context, e->owner, bone, zero, e->position);
    /* 0x013e12d0: CreateSprite(flare01, position, 2, light - 0.3, the effect, 0, 0, 4) */
    mu_sfx_call c;
    memset(&c, 0, sizeof c);
    c.routine = 0x01692eb7;
    c.type = 0x7ef7;
    copy3(c.position, e->position);
    c.scale = 2.0f;
    for (int k = 0; k < 3; ++k)
        c.light[k] = e->light[k] - F_0_3;
    c.owner = -2;
    env_call(env, &c, e);
}

/* Inferno ring's burst 0x013c07f4, subtype 0. Creator services are recorded by the validator. */
void mu_sfx_inferno_burst(const float position[3], uint8_t visible, const mu_sfx_env *env)
{
    mu_sfx_effect e;
    memset(&e, 0, sizeof e);
    float p[3] = {position[0], position[1], position[2] + 80.0f};
    const float white[3] = {1.0f, 1.0f, 1.0f};
    float angle[3] = {0.0f, 0.0f, 0.0f};
    for (int k = 0; k < 20; ++k) {
        angle[0] = (float)(smod(env_rand(env), 60) + 150);
        angle[2] = (float)smod(env_rand(env), 30);
        call_particle(env, &e, 0x7f25, p, angle, white, 2, 1.0f, -1);
    }
    if (visible) {
        const float gray[3] = {f32bits(0x3f333333u), f32bits(0x3f333333u), f32bits(0x3f333333u)};
        call_particle(env, &e, 0x7f54, p, angle, gray, 0, 1.0f, -1);
    }
}

/* ---------------------------------------------------------------- CreateEffect */

static int effect_supported(int32_t type, int32_t sub)
{
    if (mu_world_warp_type(type))
        return 1;
    switch (type) {
    case MU_SFX_MODEL_ARROW: return sub == 0 || sub == 2;
    case MU_SFX_MODEL_FIRE: return sub == 0 || sub == 1;
    case MU_SFX_MODEL_ICE: case MU_SFX_MODEL_POISON: case MU_SFX_MODEL_ICE_DEBRIS: case MU_SFX_MODEL_WAVE: return sub == 0;
    case 0x7f4e: case MU_SFX_BITMAP_THUNDER: return sub == 0;
    case MU_SFX_BITMAP_MAGIC_GROUND2: return sub == 0 || sub == 1;   /* sub 0: the level-up ground (NATIVE-PROGRESS-001) */
    case MU_SFX_MODEL_CIRCLE: case MU_SFX_MODEL_CIRCLE_LIGHT: case MU_SFX_MODEL_INFERNO:
    case MU_SFX_MODEL_LASER: case MU_SFX_TWISTING_SLASH: case MU_SFX_TWISTING_SWIRL:
        return sub == 0;
    case MU_SFX_MODEL_STONE1: case MU_SFX_MODEL_STONE2: return sub == 0 || sub == 1;
    case MU_SFX_MODEL_DUNGEON_STONE: return sub == 0;   /* RENDER-EFFECTS-005 */
    case MU_SFX_MODEL_TORNADO: return sub == 0;
    case MU_SFX_MODEL_STAR_DRAGON: case MU_SFX_MODEL_STAR_GLINT: return sub == 0 || sub == 1;
    /* NATIVE-HELPERS-002: the mounts' flying step, Fenrir's lightning and paw marks */
    case 0x6f3: return sub >= 0 && sub <= 2;
    case 0x6f6: case 0x8438: return sub == 0;
    case MU_SFX_BITMAP_SHOCKWAVE: return sub == 1;
    case MU_SFX_MODEL_FENRIR_LIGHTNING: return sub == 0;
    case MU_SFX_FENRIR_STEP: return sub >= 1 && sub <= 5;
    case MU_SFX_MODEL_CLOUD: return sub == 0;
    case MU_SFX_BITMAP_FLARE: return sub == 0;
    /* RENDER-EFFECTS-004: Rageful Blow (0x461 stores a random subtype) and its pieces */
    case MU_SFX_RAGEFUL_BLOW: return 1;
    case MU_SFX_MODEL_GUARDIAN_WING: return sub == 4;
    case MU_SFX_MODEL_QUAKE1: case MU_SFX_MODEL_QUAKE5: case MU_SFX_MODEL_QUAKE8: return sub == 0 || sub == 1;
    case MU_SFX_MODEL_QUAKE2: return sub >= 0 && sub <= 2;
    case MU_SFX_MODEL_QUAKE3: case MU_SFX_MODEL_QUAKE4: case MU_SFX_MODEL_QUAKE7:
    case MU_SFX_MODEL_FLASHING: case MU_SFX_MODEL_TAIL:
        return sub == 0;
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
                         const float angle[3], float light[3], int32_t owner, float scale,
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

    if (mu_world_warp_type(type)) {
        mu_world_warp_create(e, light, env);
        return 1;
    }
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
    case 0x6f3:                                   /* 0x01408b9d: claw */
        e->lifetime = e->field_70 = 60;
        e->scale = e->scale_arg = scale;
        e->alpha = 1.0f;
        break;
    case MU_SFX_BITMAP_FLARE: {                   /* 0x013c7082, subtype 0: Icarus's rising cloud puff */
        e->light[0] = e->light[1] = e->light[2] = F_0_3;
        const float pitch = f32bits(0x3f9c61abu);    /* 1.2217306 (70 degrees, 0x01acd818) */
        const float yaw = 30.0f * f32bits(0x40490fdbu) / 180.0f;
        const float speed = (float)(smod(env_rand(env), 5) + 9) * 0.5f;
        const float horizontal = (float)cos((double)pitch) * speed;
        e->direction[0] = horizontal * (float)sin((double)yaw);
        e->direction[1] = (float)cos((double)pitch) * speed * (float)cos((double)yaw);
        e->direction[2] = (float)sin((double)pitch) * speed;
        e->scale = 3.0f;
        e->lifetime = 400;
        break;
    }
    case MU_SFX_MODEL_CLOUD:                      /* 0x013d7a72: Icarus's cloud layer */
        e->lifetime = 2;
        e->blend_mesh = 0;
        e->scale = 14.0f;
        e->position[1] = e->position[1] + 200.0f;
        e->position[2] = e->position[2] - 190.0f;
        e->flag5 = 0;
        break;
    case 0x6f6:                                   /* 0x0141818d: tail light emitter */
        e->lifetime = e->field_70 = 12;
        e->scale = scale;
        break;
    case 0x8438:                                  /* 0x014181cf: paw rune */
        e->lifetime = e->field_70 = 20;
        e->scale_arg = scale;
        e->scale = 0.0f;
        e->alpha = 1.0f;
        break;
    case MU_SFX_BITMAP_SHOCKWAVE:
        /* NATIVE-HELPERS-002, 0x013dbe3b, subtype 1: the flying step's shock ring */
        e->lifetime = 20;
        e->scale = ((float)smod(env_rand(env), 10) + 10.0f) / 10.0f;
        break;
    case MU_SFX_MODEL_FENRIR_LIGHTNING: {
        /* NATIVE-HELPERS-002, 0x013e0e16, subtype 0: a lightning model at a random turn, flashing on its owner */
        e->lifetime = 100;
        e->scale = (float)smod(env_rand(env), 100) * f32bits(0x3b03126fu) + F_0_3;   /* 0.002 */
        e->field_64 = 0;
        e->alpha = f32bits(0x3f333333u);   /* 0.7 */
        e->angle[0] = (float)smod(env_rand(env), 360);
        e->angle[1] = (float)smod(env_rand(env), 360);
        e->angle[2] = (float)smod(env_rand(env), 360);
        copy3(e->light, light);
        const mu_sfx_object *o = env_object(env, owner);
        int16_t keys = 1;
        if (o && env->model && env->model(env->context, o->type, 0, &keys))   /* the owner's model 0x00eaa8cf */
            fenrir_lightning_flash(e, env);
        break;
    }
    case MU_SFX_FENRIR_STEP:
        if (subtype == 5) {   /* 0x013e20ea */
            e->field_70 = e->lifetime = 20;
            break;
        }
        /* NATIVE-HELPERS-002, 0x013e210c (subtypes other than 5): a lightning mark at a paw */
        e->lifetime = 200;
        e->field_64 = 0;
        copy3(e->position, position);
        copy3(e->light, light);
        e->alpha = 1.0f;
        e->time_mark = env_time(env);
        e->position[2] = 0.0f;
        break;
    /* RENDER-EFFECTS-002: the basic Ice, Poison and Power Wave model cases. */
    case MU_SFX_MODEL_ICE:                                  /* 0x013d01a5 */
        e->lifetime = 50;
        e->scale = F_0_8;
        e->velocity = 1.0f;
        e->angle[0] = 0.0f;
        e->blend_mesh = 0;
        break;
    case MU_SFX_MODEL_POISON:                                  /* 0x013d71c9 */
        e->blend_mesh = 1;
        e->lifetime = 40;
        e->scale = 1.0f;
        break;
    case MU_SFX_MODEL_WAVE:                                  /* 0x013cf050 */
        e->blend_mesh = 0;
        e->lifetime = 20;
        e->direction[1] = -60.0f;
        break;
    case MU_SFX_MODEL_ICE_DEBRIS: {                                /* 0x013d5d55, Ice debris */
        e->blend_mesh = 0;
        e->blend_light = F_0_3;
        float v[3] = {0.0f, (float)(smod(env_rand(env), 256) + 64) * F_0_1, 0.0f};
        e->position[2] = e->position[2] + 50.0f;
        e->lifetime = smod(env_rand(env), 16) + 32;
        e->scale = (float)(smod(env_rand(env), 4) + 8) * F_0_1;
        e->angle[2] = (float)smod(env_rand(env), 360);
        float m[12];
        mu_angle_matrix(e->angle, m);
        mu_vector_rotate(v, m, e->direction);
        e->gravity = (float)(smod(env_rand(env), 16) + 8);
        break;
    }
    case MU_SFX_MODEL_FIRE: {
        /* 0x013d2f05, Meteorite subtype 0; Fire Ball takes 0x013d4086. */
        if (subtype == 0) {
            e->blend_mesh = 1;
            e->lifetime = 40;
            e->scale = (float)(10 + smod(env_rand(env), 8)) * F_0_1;
            e->position[0] = ((float)smod(env_rand(env), 32) + 130.0f) + e->position[0];
            e->position[2] = e->position[2] + 400.0f;
            e->direction[2] = -50.0f;
            e->angle[0] = 0.0f; e->angle[1] = 20.0f; e->angle[2] = 0.0f;
            break;
        }
        e->blend_mesh = 1;
        e->lifetime = 60;
        e->scale = (float)(8 + smod(env_rand(env), 4)) * F_0_1;
        e->position[2] = e->position[2] + 120.0f;
        e->direction[0] = 0.0f;
        e->direction[1] = -50.0f;
        e->direction[2] = 0.0f;
        break;
    }
    case 0x7f4e: {                                /* 0x013c6a04, Aqua Beam subtype 0 */
        e->lifetime = 20;
        e->light[0] = 0.5f; e->light[1] = f32bits(0x3f333333u); e->light[2] = 1.0f;
        const float v[3] = {0.0f, -50.0f, 0.0f};
        float m[12];
        e->scale = 16.0f;
        mu_angle_matrix(e->angle, m);
        mu_vector_rotate(v, m, e->direction);
        /* Hero-only area requests and source-position writeback are outside this visual adapter. */
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
    /* RENDER-EFFECTS-004: Rageful Blow. 0x461 is the flying weapon; the EarthQuake01..08,
     * flashing and tail models 0x462..0x46b are its impact pieces, scaled by the info key / 100. */
    case MU_SFX_MODEL_GUARDIAN_WING: {             /* 0x013e4f55, subtype 4: 0x013e4f6f */
        float old[3];
        copy3(old, e->position);
        for (int k = 0; k < 3; ++k)
            e->position[k] = (float)(smod(env_rand(env), 20) - 10) * 4.0f + e->position[k];
        for (int k = 0; k < 3; ++k)
            e->direction[k] = old[k] - e->position[k];
        vector_normalize(e->direction);
        const int32_t drift = trunc_i32((float)(smod(env_rand(env), 10) - 5) * f32bits(0x3da3d70au));   /* 0.08 */
        for (int k = 0; k < 3; ++k)
            e->direction[k] = (float)drift + e->direction[k];
        const float step = (float)(smod(env_rand(env), 20) - 10);
        e->scale = step * (e->scale * f32bits(0x3cf5c28fu)) + e->scale;   /* 0.03 */
        e->lifetime = 25;
        e->alpha = F_0_3;
        e->gravity = F_0_1;
        for (int k = 0; k < 3; ++k)
            e->angle[k] = (float)smod(env_rand(env), 360);
        for (int k = 0; k < 3; ++k)
            e->spin[k] = (float)(smod(env_rand(env), 10) - 5);
        break;
    }
    case MU_SFX_RAGEFUL_BLOW:                     /* 0x013ce830 */
        e->heading = e->angle[0];
        e->heading_yz[0] = e->angle[1];
        e->heading_yz[1] = e->angle[2];
        copy3(e->impact, e->position);
        e->lifetime = 20;
        e->subtype = smod(env_rand(env), 100);
        e->angle[2] = e->angle[2] + 330.0f;
        e->heading = e->heading + 80.0f;
        e->heading_yz[1] = e->heading_yz[1] + 180.0f;
        e->gravity = 50.0f;
        e->serial = env ? env->serial : 0;
        call_serial_step(env, e);
        break;
    case MU_SFX_MODEL_QUAKE1:                     /* 0x013cea0a */
        if (subtype == 0 || subtype == 1) {
            e->lifetime = subtype == 0 ? 35 : 60;
            e->scale = (float)(int16_t)info->key / 100.0f;
            e->blend_mesh = 0;
        }
        break;
    case MU_SFX_MODEL_QUAKE2:                     /* 0x013cea7b, subtype 2: 0x013cead7 */
        e->lifetime = subtype == 2 ? 50 : 20;
        e->scale = (float)(int16_t)info->key / 100.0f;
        e->blend_mesh = 0;
        if (subtype == 1)
            e->field_80 = 0x80;
        break;
    case MU_SFX_MODEL_QUAKE3:                     /* 0x013ceb08 */
        e->lifetime = 35;
        e->scale = (float)(int16_t)info->key / 100.0f;
        break;
    case MU_SFX_MODEL_QUAKE4:                     /* 0x013ceb32 */
        e->lifetime = 35;
        e->scale = (float)(int16_t)info->key / 100.0f;
        e->blend_mesh = 0;
        break;
    case MU_SFX_MODEL_QUAKE5:                     /* 0x013ceb63 */
    case MU_SFX_MODEL_QUAKE7:                     /* 0x013cebd1 */
    case MU_SFX_MODEL_QUAKE8:                     /* 0x013cec02 */
        e->lifetime = 40;
        e->scale = (float)(int16_t)info->key / 100.0f;
        e->blend_mesh = 0;
        if (subtype == 1 && type != MU_SFX_MODEL_QUAKE7)
            e->field_80 = 0x80;
        break;
    case MU_SFX_MODEL_FLASHING:                   /* 0x013c94a8 */
        e->blend_mesh = 0;
        e->blend_light = 1.5f;
        e->scale = 0.5f;
        e->lifetime = 15;
        e->position[2] = e->position[2] - 15.0f;
        e->light[0] = e->light[1] = e->light[2] = 1.0f;
        break;
    case MU_SFX_MODEL_TAIL:                       /* 0x013c956a */
        e->blend_mesh = -2;
        e->lifetime = 6;
        e->scale = 1.0f;
        e->gravity = 80.0f;
        e->light[0] = e->light[1] = e->light[2] = 0.5f;
        e->angle[0] = 0.0f;
        e->angle[1] = 0.0f;
        e->angle[2] = 45.0f;
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
    case MU_SFX_MODEL_DUNGEON_STONE: {
        /* RENDER-EFFECTS-005, 0x013d6f51: a falling stone flung along the object's angle */
        float v[3], m[12], d[3];
        e->lifetime = smod(env_rand(env), 16) + 24;
        e->scale = scale;
        e->gravity = -(float)smod(env_rand(env), 4);
        v[0] = (float)(smod(env_rand(env), 64) - 32);
        v[1] = -(float)(smod(env_rand(env), 32) + 50);
        v[2] = (float)(smod(env_rand(env), 128) + 200);
        mu_angle_matrix(e->angle, m);
        mu_vector_rotate(v, m, d);
        e->position[0] = e->position[0] + d[0];
        e->position[1] = e->position[1] + d[1];
        e->position[2] = e->position[2] + d[2];
        break;
    }
    case MU_SFX_MODEL_STAR_DRAGON: {
        /* 0x013f41b4 (NATIVE-CHARSEL-003): the sky dragon of the character select, emitted by World94's objects
         * 0x27/0x28 (CGMCharacterScene_Ex slot 0x34) */
        e->angle[0] = 0.0f;
        e->angle[1] = 310.0f;
        e->angle[2] = 90.0f;
        e->position[1] = ((float)smod(env_rand(env), 600) - 300.0f) + e->position[1];
        e->blend_mesh = 0;
        e->velocity = 1.0f;
        if (subtype == 0) {
            e->lifetime = 70;
            e->direction[0] = -25.0f;
            e->scale = 1.0f;
        } else {
            e->lifetime = 130;
            e->direction[0] = -15.0f;
            e->scale = f32bits(0x3f333333u);   /* 0.7 */
        }
        const float glint_light[3] = {0.5f, 0.5f, 0.5f};
        float at[3] = {0.0f, 0.0f, 0.0f};
        int16_t keys = 1;
        if (env && env->model && !env->model(env->context, type, e->action, &keys))
            return 1;   /* no model: CreateEffect returns 0 here (0x013f438c), the record stays */
        {
            mu_sfx_call c;
            memset(&c, 0, sizeof c);
            c.routine = MU_SFX_CALL_POSE;
            c.type = type;
            c.owner = -2;
            env_call(env, &c, e);
        }
        {
            mu_sfx_call c;
            memset(&c, 0, sizeof c);
            c.routine = MU_SFX_CALL_BONE;
            c.type = type;
            c.range = 1;
            c.owner = -2;
            env_call(env, &c, e);
            if (env && env->bone)
                env->bone(env->context, e, 1, at);
            else
                copy3(at, e->position);
        }
        /* CreateEffect(0x5ad, bone 1, angle, (0.5, 0.5, 0.5), subtype, this effect, -1, ...) */
        call_effect(env, e, MU_SFX_MODEL_STAR_GLINT, at, e->angle, glint_light, subtype, -2);
        break;
    }
    case MU_SFX_MODEL_STAR_GLINT:
        /* 0x013f4457 */
        e->blend_mesh = 0;
        e->velocity = 1.0f;
        if (subtype == 0) {
            e->lifetime = 70;
            e->direction[0] = -25.0f;
            e->scale = 0.5f;
        } else {
            e->lifetime = 130;
            e->direction[0] = -15.0f;
            e->scale = F_0_3;
        }
        break;
    case MU_SFX_MODEL_TORNADO: {
        /* 0x013c3eab (NATIVE-JOINT-001): a field tornado a few tiles around the position, drifting */
        e->field_6 = 0;
        e->flag5 = 0;
        e->light[0] = 1.0f + e->light[0];
        e->light[1] = 1.0f + e->light[1];
        e->light[2] = 1.0f + e->light[2];
        e->lifetime = 150;
        e->field_70 = e->lifetime;
        e->flag_c = 1;
        e->alpha = 1.0f;
        e->scale = 1.0f;
        e->blend_light = 1.0f;
        e->velocity = F_0_3;
        e->heading = (float)smod(env_rand(env), 314) / 100.0f;
        e->field_68 = -1;
        e->blend_mesh = -1;
        e->angle[0] = e->angle[1] = e->angle[2] = 0.0f;
        float dx = (float)(smod(env_rand(env), 20) - 10);
        float dy = (float)(smod(env_rand(env), 20) - 10);
        e->direction[0] = dx * e->scale;
        e->direction[1] = dy * e->scale;
        e->direction[2] = 0.0f;
        e->position[0] = (float)smod(env_rand(env), 512) + e->position[0] - 256.0f;
        e->position[1] = (float)smod(env_rand(env), 512) + e->position[1] - 256.0f;
        e->position[2] = env_height(env, e->position[0], e->position[1]);
        e->frame = 1.0f;
        /* PlayBuffer(0x582, o, 0) when the hero ([0x0a39d754] + 0x33ac) is within 800 */
        const mu_sfx_object *hero = env ? env_object(env, env->hero_object) : NULL;
        if (hero) {
            float hx = e->position[0] - hero->position[0];
            float hy = e->position[1] - hero->position[1];
            float d = (float)sqrt((double)(hx * hx + hy * hy));
            if (800.0f > d) {
                mu_sfx_call c;
                memset(&c, 0, sizeof c);
                c.routine = MU_SFX_CALL_SOUND;
                c.type = 0x582;
                c.owner = -2;
                env_call(env, &c, e);
            }
        }
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

    if (mu_world_warp_type(type))
        mu_world_warp_move(e, env ? env->world_time : 0.0f);
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
    case MU_SFX_MODEL_ICE:                                  /* 0x0146b979 */
        if (e->frame >= 5.0f) {
            e->velocity = 0.0f;
            if (smod(env_rand(env), 2) == 0) {
                float p[3];
                p[0] = e->position[0] + (float)(smod(env_rand(env), 64) - 32);
                p[1] = e->position[1] + (float)(smod(env_rand(env), 64) - 32);
                p[2] = e->position[2] + (float)(smod(env_rand(env), 128) + 32);
                call_particle(env, e, 0x7f5a, p, e->angle, e->light, 0, 1.0f, -1);
            }
            e->alpha = e->alpha - f32bits(0x3d4ccccd); /* 0.05 */
            if (e->alpha < 0.0f)
                kill_effect(env, e);
        }
        light[0] = -lum * F_0_4;
        light[1] = -lum * F_0_3;
        light[2] = -lum * F_0_2;
        call_terrain_light(env, e, light, 2);
        break;
    case MU_SFX_MODEL_POISON:                                  /* 0x0144f50b */
        e->blend_light = (float)e->lifetime * F_0_1;
        e->alpha = (float)e->lifetime * F_0_1;
        light[0] = lum * F_0_3;
        light[1] = lum;
        light[2] = lum * f32bits(0x3f19999a);       /* 0.6 */
        call_terrain_light(env, e, light, 2);
        break;
    case MU_SFX_MODEL_WAVE:                                  /* 0x01453c6c */
        e->blend_light = (float)e->lifetime * F_0_1;
        e->blend_u = -(float)e->lifetime * F_0_2;
        for (int k = 0; k < 4; ++k)
            call_particle(env, e, 0x7f5a, e->position, e->angle, e->light, 3, 1.0f, -1);
        light[0] = lum * F_0_3;
        light[1] = lum * f32bits(0x3f19999a);
        light[2] = lum;
        call_terrain_light(env, e, light, 3);
        break;
    case MU_SFX_MODEL_ICE_DEBRIS: {                                /* 0x0145d25b */
        for (int k = 0; k < 3; ++k)
            e->position[k] = e->position[k] + e->direction[k];
        e->direction[0] = F_0_9 * e->direction[0];
        e->direction[1] = F_0_9 * e->direction[1];
        e->direction[2] = F_0_9 * e->direction[2];
        e->position[2] = e->position[2] + e->gravity;
        e->gravity = e->gravity - 3.0f;
        float ground = env_height(env, e->position[0], e->position[1]);
        if (ground > e->position[2]) {
            e->position[2] = ground;
            e->gravity = -e->gravity * 0.5f;
            e->lifetime -= 4;
            e->angle[0] = e->angle[0] - e->scale * 128.0f;
        } else {
            e->angle[0] = e->angle[0] - e->scale * 32.0f;
        }
        if (smod(env_rand(env), 10) == 0)
            call_particle(env, e, 0x7f5a, e->position, e->angle, e->light, 0, 1.0f, -1);
        break;
    }
    case MU_SFX_MODEL_FIRE:
        /* 0x0146c821..0x0146cd92: Meteorite terrain contact, before generic motion. */
        if (sub == 0) {
            float ground = env_height(env, e->position[0], e->position[1]) + 0.0f;
            /* Ordinary-world predicate is false in the bounded native adapter. */
            if (ground > e->position[2]) {
                e->position[2] = ground;
                e->direction[0] = e->direction[1] = e->direction[2] = 0.0f;
                float p[3] = {e->position[0], e->position[1], e->position[2] + 80.0f};
                for (int k = 0; k < 6; ++k)
                    call_effect(env, e, MU_SFX_MODEL_STONE1 + smod(env_rand(env), 2),
                                e->position, e->angle, e->light, 0, -1);
                call_particle(env, e, 0x7f54, p, e->angle, light, 0, 1.0f, -1);
                kill_effect(env, e);
            }
        }
        /* 0x0146d591..0x0146db20, shared fire trail and light */
        e->blend_light = sub == 0 ? (float)(smod(env_rand(env), 4) + 4) * F_0_1 : 0.0f;
        light[0] = lum * 1.0f;
        light[1] = lum * F_0_1;
        light[2] = lum * 0.0f;
        call_terrain_light(env, e, light, 2);
        call_particle(env, e, MU_SFX_BITMAP_FIRE, e->position, e->angle, light, 5, 1.0f, MU_SFX_NO_OWNER);
        if (sub == 1) check(env, e, MU_SFX_CALL_CHECK_MAGIC);
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
        /* 0x0143fbda, subtypes >= 1 except 4, 6..13, 19; subtype 0 (the level-up ground, NATIVE-PROGRESS-001)
         * has no case */
        if (sub >= 1)
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
    case MU_SFX_MODEL_CLOUD:
        break;
    case MU_SFX_BITMAP_FLARE:
        /* 0x0144ce38, subtype 0: the puff rises and slows, leaving a flare particle */
        e->position[0] = e->position[0] + e->direction[0];
        e->position[1] = e->position[1] + e->direction[1];
        e->position[2] = e->position[2] + e->direction[2];
        e->direction[2] = e->direction[2] - F_0_01;
        call_particle(env, e, MU_SFX_BITMAP_FLARE, e->position, e->angle, e->light, 1, e->scale, MU_SFX_NO_OWNER);
        if (-2.0f > e->direction[2])
            e->lifetime = 0;
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
    /* RENDER-EFFECTS-004: Rageful Blow, ordinary worlds (the special-world predicate 0x009b0418 false). */
    case MU_SFX_RAGEFUL_BLOW: {                                   /* 0x01450a73 */
        float a[3] = {0.0f, 0.0f, 0.0f}, d[3] = {0.0f, 0.0f, 0.0f}, m[12], p[3];
        uint16_t key = 0x96;
        int32_t hit_at = 11, quake_at = 10;
        const mu_sfx_object *o = env_object(env, e->owner);
        if (e->skill == 0x7fb) {
            hit_at = 5;
            quake_at = 4;
        }
        if (e->lifetime == hit_at) {
            const float bright[3] = {1.0f, 1.0f, 1.0f};
            if (e->client_hit != 3 && e->skill != 0x7fb) {
                d[0] = -25.0f;
                d[1] = -80.0f;
                d[2] = 0.0f;
                mu_angle_matrix(o ? o->angle : a, m);
                mu_vector_rotate(d, m, p);
                for (int k = 0; k < 3; ++k)
                    e->impact[k] = p[k] + e->position[k];
            }
            e->impact[2] = env_height(env, e->impact[0], e->impact[1]) + 25.0f;
            call_particle(env, e, 0x7f54, e->impact, a, bright, 0, 0.5f, MU_SFX_NO_OWNER);
            if (e->client_hit == 0) {
                for (int k = 0; k < 8; ++k) {
                    float q[3];
                    a[0] = (float)smod(env_rand(env), 60) - 60.0f;
                    a[1] = 0.0f;
                    a[2] = (float)(smod(env_rand(env), 30) + 90);
                    for (int i = 0; i < 3; ++i)
                        a[i] = a[i] + e->angle[i];
                    copy3(q, e->impact);
                    q[0] = (float)(smod(env_rand(env), 20) - 10) + q[0];
                    q[1] = (float)(smod(env_rand(env), 20) - 10) + q[1];
                    call_joint(env, e, 0x7fd5, q, q, a, 0, MU_SFX_NO_OWNER, 10.0f);
                    if (k == 0)
                        call_particle(env, e, 0x7f25, q, a, light, 0, 1.0f, MU_SFX_NO_OWNER);
                }
            }
            a[0] = a[1] = a[2] = 0.0f;
            if (e->client_hit == 0)
                call_effect_key(env, e, MU_SFX_MODEL_FLASHING, e->impact, a, e->light, MU_SFX_NO_OWNER, 0xffff);
            e->impact[2] = e->impact[2] - 27.0f;
            if (o && o->type != 0x804 && o->type != 0x962) {
                call_effect_key(env, e, MU_SFX_MODEL_QUAKE3, e->impact, a, e->light, -2, key);
                call_effect_key(env, e, MU_SFX_MODEL_QUAKE1, e->impact, a, e->light, -2, key);
                call_effect_key(env, e, MU_SFX_MODEL_QUAKE2, e->impact, a, e->light, -2, key);
            }
            for (int k = 0; k < 5; ++k) {
                d[0] = 0.0f;
                d[1] = (float)(smod(env_rand(env), 150) + 100);
                d[2] = 0.0f;
                a[0] = 0.0f;
                a[1] = 0.0f;
                a[2] = (float)e->subtype + (float)k * 72.0f;
                mu_angle_matrix(a, m);
                mu_vector_rotate(d, m, p);
                for (int i = 0; i < 3; ++i)
                    p[i] = p[i] + e->impact[i];
                p[2] = p[2] + 3.0f;
                key = (uint16_t)(smod(env_rand(env), 50) + 40);
                a[0] = 0.0f;
                a[1] = 0.0f;
                a[2] = (float)(smod(env_rand(env), 30) - 15) + 45.0f;
                uint16_t wall = call_wall(env, e, p[0], p[1]);
                if ((wall & 4) || (wall & 8) || (wall & 0x10))
                    continue;
                p[2] = env_height(env, p[0], p[1]) + 3.0f;
                call_effect_key(env, e, MU_SFX_MODEL_QUAKE4, p, a, e->light, e->owner, key);
                call_effect_key(env, e, MU_SFX_MODEL_QUAKE5, p, a, e->light, e->owner, key);
            }
            goto lifetime;
        }
        if (e->lifetime == quake_at) {
            float points[5][3], turn[5];
            for (int k = 0; k < 5; ++k) {
                copy3(points[k], e->impact);
                turn[k] = 0.0f;
            }
            int32_t side = 0;
            for (int i = 0; i < 4; ++i) {
                d[0] = 0.0f;
                d[1] = (float)smod(env_rand(env), 15) + 85.0f;
                d[2] = 0.0f;
                if (i >= 3)
                    side = env_rand(env);
                for (int j = 0; j < 5; ++j) {
                    int32_t step = side % 2 == 0 ? smod(env_rand(env), 30) + 50 : -(smod(env_rand(env), 30) + 50);
                    turn[j] = (float)step + turn[j];
                    a[2] = (float)((smod(env_rand(env), 10) + 62) * j) + turn[j];
                    mu_angle_matrix(a, m);
                    mu_vector_rotate(d, m, p);
                    for (int k = 0; k < 3; ++k)
                        points[j][k] = p[k] + points[j][k];
                    uint16_t wall = call_wall(env, e, points[j][0], points[j][1]);
                    if ((wall & 4) && (wall & 8) && (wall & 0x10))
                        continue;
                    points[j][2] = env_height(env, points[j][0], points[j][1]) + 3.0f;
                    a[2] = a[2] + 270.0f;
                    call_effect_key(env, e, MU_SFX_MODEL_QUAKE7, points[j], a, e->light, e->owner, 0x64);
                    call_effect_key(env, e, MU_SFX_MODEL_QUAKE8, points[j], a, e->light, e->owner, 0x64);
                }
                side = side + 1;
            }
            e->lifetime = 0;
            call_sound(env, e, 0x97);
            goto lifetime;
        }
        /* 0x01451cdb: the weapon's hop over the impact point */
        float t = (float)e->lifetime, speed = 15.0f;
        if (e->lifetime > 9 && e->lifetime < 16) {
            t = 12.5f;
            speed = 18.0f;
            if (e->lifetime == 15)
                e->gravity = e->gravity * -1.0f;
        }
        if (e->client_hit == 0 && e->lifetime == 13) {
            float base[3], q[3];
            a[0] = a[1] = a[2] = 0.0f;
            d[0] = -25.0f;
            d[1] = -40.0f;
            d[2] = 0.0f;
            mu_angle_matrix(o ? o->angle : a, m);
            mu_vector_rotate(d, m, p);
            for (int k = 0; k < 3; ++k)
                base[k] = p[k] + e->position[k];
            for (int k = 0; k < 4; ++k) {
                copy3(q, base);
                q[2] = base[2] - (float)(k * 50);
                call_effect_key(env, e, MU_SFX_MODEL_TAIL, q, a, e->light, MU_SFX_NO_OWNER, 0xffff);
            }
            base[0] = (float)(smod(env_rand(env), 30) + 20) + base[0];
            base[2] = (float)(smod(env_rand(env), 500) - 250) + base[2];
            for (int k = 0; k < 4; ++k) {
                copy3(q, base);
                q[2] = base[2] - (float)(k * 30);
                call_effect_key(env, e, MU_SFX_MODEL_TAIL, q, a, e->light, MU_SFX_NO_OWNER, 0xffff);
            }
            call_sound(env, e, 0x96);
        }
        {
            float w = (20.0f - t) * speed;
            e->angle[0] = e->angle[0] + 80.0f;
            float x = (float)((double)w * f64bits(0x400921fafc8b007aull) / 180.0);
            e->direction[1] = (float)sin((double)x) * 260.0f;
            copy3(e->position, e->impact);
            if (12.5 > (double)t || (double)t > 12.5)
                e->gravity = e->gravity + 8.0f;
            else
                e->gravity = e->gravity - 8.0f;
            const float spin[3] = {e->heading, e->heading_yz[0], e->heading_yz[1]};
            mu_angle_matrix(spin, m);
            mu_vector_rotate(e->direction, m, p);
            for (int k = 0; k < 3; ++k)
                e->position[k] = p[k] + e->impact[k];
            e->position[2] = e->position[2] + e->gravity;
            e->position[2] = e->position[2] + 200.0f;
        }
        goto lifetime;
    }
    case MU_SFX_MODEL_GUARDIAN_WING:                              /* 0x0146b64c, subtype 4 */
        for (int k = 0; k < 3; ++k)
            e->light[k] = e->light[k] * f32bits(0x3f7851ecu);   /* 0.97 */
        e->alpha = e->alpha * f32bits(0x3f7851ecu);
        for (int k = 0; k < 3; ++k)
            e->angle[k] = e->spin[k] + e->angle[k];
        break;
    case MU_SFX_MODEL_QUAKE1:                                     /* 0x01452410 */
        e->blend_light = (float)e->lifetime * F_0_1 / 3.0f;
        if (e->lifetime < 10)
            e->position[2] = e->position[2] - 0.5f;
        if (e->lifetime > 15 && e->lifetime % 3 == 0) {
            mu_sfx_call q;
            memset(&q, 0, sizeof q);
            q.routine = MU_SFX_CALL_QUAKE;
            q.scale = (float)(env_rand(env) % 8 - 4) * F_0_1;
            q.owner = MU_SFX_NO_OWNER;
            env_call(env, &q, e);
        }
        break;
    case MU_SFX_MODEL_QUAKE3:                                     /* 0x014524b4 */
        e->blend_light = (float)e->lifetime * F_0_1 / 10.0f;
        if (e->lifetime < 13)
            e->position[2] = e->position[2] - 0.5f;
        break;
    case MU_SFX_MODEL_QUAKE4:                                     /* 0x014528f2 */
    case MU_SFX_MODEL_QUAKE7:                                     /* 0x01452d78 */
        e->blend_light = (float)e->lifetime * F_0_1 / 3.0f;
        if (e->lifetime < 10)
            e->position[2] = e->position[2] - 0.5f;
        break;
    case MU_SFX_MODEL_QUAKE2:                                     /* 0x01452517 */
    case MU_SFX_MODEL_QUAKE5:                                     /* 0x014529b8 */
    case MU_SFX_MODEL_QUAKE8: {                                   /* 0x01452ddb */
        const int quake2 = type == MU_SFX_MODEL_QUAKE2;
        const int32_t full = quake2 ? 10 : 30, sink = quake2 ? 5 : 15;
        if (quake2 && e->scale > 50.0f)
            e->lifetime = 0;
        if (type == MU_SFX_MODEL_QUAKE8) {
            if (e->lifetime >= 30)
                e->blend_light = (float)(40 - e->lifetime) * F_0_1;
            else
                e->blend_light = (float)e->lifetime * F_0_1;
            if (e->lifetime < 15)
                e->position[2] = e->position[2] - 0.5f;
            if (e->lifetime >= 13 && env_rand(env) % 5 == 0) {
                /* 0x01452e74: a point 10 above, computed and not used */
            }
        } else if (e->lifetime >= full) {
            e->blend_light = (float)((quake2 ? 20 : 40) - e->lifetime) * F_0_1;
        } else {
            if (e->lifetime < sink)
                e->position[2] = e->position[2] - 0.5f;
            e->blend_light = (float)e->lifetime * F_0_1;
            if (e->lifetime >= 5 && env_rand(env) % (quake2 ? 10 : 15) == 0) {
                float v[3] = {0.0f, 0.0f, 0.0f}, r[3] = {0.0f, 0.0f, 0.0f}, m[12], q[3];
                v[1] = (float)(env_rand(env) % 150);
                r[2] = (float)(env_rand(env) % 360);
                mu_angle_matrix(r, m);
                mu_vector_rotate(v, m, q);
                for (int k = 0; k < 3; ++k)
                    q[k] = q[k] + e->position[k];
                int32_t stone = smod(env_rand(env), 2) + MU_SFX_MODEL_STONE1;
                call_effect_key(env, e, stone, q, e->angle, e->light, MU_SFX_NO_OWNER, 0xffff);
            }
        }
        e->blend_u = -(float)e->lifetime * F_0_01;
        const mu_sfx_object *o = env_object(env, e->owner);
        if (e->owner != MU_SFX_NO_OWNER && o) {
            if (o->type == 0x804) {
                light[0] = lum * 0.0f;
                light[1] = lum * 0.0f;
                light[2] = lum * 1.0f;
            } else {
                light[0] = lum * 1.0f;
                light[1] = lum * 0.0f;
                light[2] = lum * 0.0f;
            }
        }
        call_terrain_light(env, e, light, 1);
        break;
    }
    case MU_SFX_MODEL_FLASHING:                                   /* 0x0144e1d7 */
        if (e->scale > 2.0f) {
            e->scale = e->scale + F_0_1;
            e->position[0] = e->position[0] - 1.0f;
            e->position[2] = e->position[2] - 1.5f;
            e->blend_light = (float)e->lifetime / 30.0f;
        } else {
            e->scale = e->scale + f32bits(0x3f99999au);           /* 1.2 */
            e->position[0] = e->position[0] - f32bits(0x3f99999au);
            e->position[2] = e->position[2] - f32bits(0x3fe66666u);   /* 1.8 */
        }
        light[0] = light[1] = light[2] = -lum * 0.5f;
        call_terrain_light(env, e, light, 5);
        break;
    case MU_SFX_MODEL_TAIL:                                       /* 0x0144e3d9 */
        e->position[2] = e->position[2] - e->gravity;
        e->gravity = e->gravity + 60.0f;
        e->blend_light = (float)e->lifetime / 20.0f;
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
    case MU_SFX_MODEL_DUNGEON_STONE: {                           /* RENDER-EFFECTS-005, 0x0146b809 */
        e->position[2] = e->position[2] + e->gravity;
        e->gravity = e->gravity - 1.0f;
        float h = env_height(env, e->position[0], e->position[1]);
        if (h > e->position[2]) {
            e->position[2] = h;
            e->gravity = -e->gravity * F_0_4;
            e->lifetime = e->lifetime - 4;
            e->direction[1] = e->direction[1] - 2.0f;
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
    case 0x6f3:                                   /* 0x014b6090 */
        e->scale -= e->scale_arg / (float)e->field_70;
        e->alpha -= e->scale_arg / (float)e->field_70;
        break;
    case 0x6f6: {                                 /* 0x014d01c9 */
        call_particle(env, e, 0x8086, e->position, e->angle, e->light, 0x18, e->scale, MU_SFX_NO_OWNER);
        const float k = (float)smod(env_rand(env), 20) / 25.0f + f32bits(0x3e19999au);
        mu_sfx_call c;
        memset(&c, 0, sizeof c);
        c.routine = 0x01692eb7;
        c.type = 0x7ef7;
        c.scale = e->scale * 2.5f;
        c.owner = -2;
        c.light[0] = k * F_0_3;
        c.light[1] = k * f32bits(0x3ee66666u);
        c.light[2] = k * 1.0f;
        copy3(c.position, e->position);
        env_call(env, &c, e);
        break;
    }
    case 0x8438:                                  /* 0x014d050c */
        if (e->lifetime < e->field_70 / 2)
            e->alpha -= 1.0f / (float)(e->field_70 / 2);
        e->scale = e->scale_arg / (float)e->field_70 + e->scale;
        break;
    case MU_SFX_BITMAP_SHOCKWAVE:
        /* NATIVE-HELPERS-002, 0x014756bd, subtype 1: grows and jitters; 0x01476ab6: lights up and fades */
        e->scale = (float)smod(env_rand(env), 5) / 10.0f + e->scale;
        e->position[0] = ((float)smod(env_rand(env), 8) - 4.0f) + e->position[0];
        e->position[1] = ((float)smod(env_rand(env), 8) - 4.0f) + e->position[1];
        if (0.0f > e->scale)
            e->scale = 0.0f;
        if (sub >= 0 && sub <= 3) {
            float l = e->lifetime > 20 ? (float)(40 - e->lifetime) / 20.0f : (float)e->lifetime / 20.0f;
            e->light[0] = e->light[1] = e->light[2] = l;
        }
        break;
    case MU_SFX_MODEL_FENRIR_LIGHTNING:
        /* NATIVE-HELPERS-002, 0x0147c1b4, subtype 0: fades in by 0.3, then out, and turns */
        if (e->live) {
            if (e->field_64 == 0) {
                e->alpha = e->alpha + F_0_3;
                if (e->alpha >= 1.0f) {
                    e->field_64 = 1;
                    e->alpha = 1.0f;
                }
                if (0.0f > e->alpha)
                    e->alpha = 1.0f;
            } else if (e->field_64 == 1) {
                e->alpha = e->alpha - F_0_3;
                if (!(0.0f < e->alpha)) {
                    e->alpha = 0.0f;
                    kill_effect(env, e);
                }
            }
            for (int k = 0; k < 3; ++k)
                e->angle[k] = e->angle[k] + f32bits(0x3e19999au);   /* 0.15 */
        }
        break;
    case MU_SFX_FENRIR_STEP: {
        /* NATIVE-HELPERS-002, 0x0147cbac (subtypes other than 5): fades in its state's colour, steps its sheet
         * every 200 ms of real time */
        if (e->live != 1)   /* IsLive 0x0095f977 on the effect itself */
            break;
        if (sub == 5) {   /* 0x0147cbc6 */
            e->field_64 = trunc_i32(5.0f - (float)e->lifetime / ((float)e->field_70 * F_0_2));
            e->alpha -= 1.0f / (float)e->field_70;
            break;
        }
        e->angle[0] = e->angle[0] + F_0_1;
        static const uint8_t fade[5][3] = {{0, 0, 0}, {0, 1, 1}, {1, 1, 0}, {1, 0, 1}, {0, 0, 1}};
        for (int k = 0; k < 3; ++k)
            if (fade[sub][k])
                e->light[k] = e->light[k] - f32bits(0x3d4ccccdu);   /* 0.05 */
        e->alpha = e->alpha - f32bits(0x3d4ccccdu);
        if (!(0.0f < e->alpha))
            kill_effect(env, e);
        if ((uint32_t)(env_time(env) - e->time_mark) > 200u) {
            e->field_64 = e->field_64 + 1;
            if (e->field_64 > 4)
                kill_effect(env, e);
            e->time_mark = env_time(env);
        }
        break;
    }
    case MU_SFX_MODEL_TORNADO: {
        /* 0x01435ef3 (NATIVE-JOINT-001): a new heading one step in 500, a drift of 2 along it, shorter
         * on tiles with attribute bit 8, the blend light fading with the lifetime, its own animation */
        if (env_rand(env) % 500 == 0)
            e->heading = (float)(env_rand(env) % 314) / 100.0f;
        e->position[0] = (float)sin((double)e->heading) * 2.0f + e->position[0];
        e->position[1] = (float)cos((double)e->heading) * 2.0f + e->position[1];
        e->angle[2] = 0.0f;
        {
            float tx = e->position[0] / 100.0f, ty = e->position[1] / 100.0f;
            mu_sfx_call c;
            memset(&c, 0, sizeof c);
            c.routine = MU_SFX_CALL_ATTRIBUTE;
            c.subtype = trunc_i32(tx);
            c.range = trunc_i32(ty);
            c.owner = -2;
            int attribute = env && env->call ? env->call(env->context, &c, e) : 0;
            if (attribute & 8)
                e->lifetime = trunc_i32((float)e->lifetime * F_0_9);
        }
        e->blend_light = (float)(e->lifetime + 1) / 150.0f;
        int16_t keys = 1;
        int has_model = env && env->model ? env->model(env->context, type, e->action, &keys) : 1;
        if (has_model) {
            mu_sfx_call c;
            memset(&c, 0, sizeof c);
            c.routine = MU_SFX_CALL_ANIMATION;
            c.type = type;
            c.scale = e->velocity;
            c.owner = -2;
            env_call(env, &c, e);
        }
        goto lifetime;   /* 0x014ecc1f: no generic animation or motion */
    }
    default:
        break;
    }

    /* after the switch 0x014eca00: types 0x453, 0x454, 0x461, ... skip the
     * animation and the motion (0x014ecb6e) */
    if (type == MU_SFX_TWISTING_SLASH || type == MU_SFX_TWISTING_SWIRL || type == MU_SFX_RAGEFUL_BLOW)
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
        } else if (type == 0x7ef7 && sub == 0 && (e->lifetime & 1)) {
            /* 0x0150cc17: the cloud puff moves once more on an odd LifeTime (NATIVE-FIDELITY-002) */
            return mu_sfx_effect_move(e, env);
        }
        /* subtype 3 (MODEL_FIRE) with an odd LifeTime moves twice (not reconstructed) */
        return 1;
    }
    if (e->lifetime <= 0) {
        call_plain(env, e, MU_SFX_CALL_DELETE);
        e->live = 0;
    }
    e->lifetime = e->lifetime - 1;
    return 1;
}

int mu_sfx_effect_decal(const mu_sfx_effect *e, int32_t world, mu_sfx_decal *out)
{
    memset(out, 0, sizeof *out);
    out->texture = e->type;
    out->size = e->scale;
    copy3(out->light, e->light);
    if (e->type == 0x6f3 && e->subtype >= 0 && e->subtype <= 2) { /* 0x01527c4e */
        static const int32_t textures[] = {0x7fdd, 0x7fe0, 0x8098};
        out->texture = textures[e->subtype];
        for (int k = 0; k < 3; ++k) out->light[k] = e->alpha * e->light[k];
    } else if (e->type == 0x8438 && e->subtype == 0) { /* 0x0152d6a6 */
        out->rotation = e->angle[2];
        for (int k = 0; k < 3; ++k) out->light[k] = e->light[k] * e->alpha;
    } else if (e->type == MU_SFX_FENRIR_STEP && e->subtype >= 1 && e->subtype <= 5) { /* 0x0151a5c7 */
        out->texture = MU_SFX_BITMAP_LIGHTING_A + (e->subtype == 5 ? e->field_64 : e->field_64 % 5);
        out->size = 0.6f;
    } else if (e->type == MU_SFX_BITMAP_SHOCKWAVE && e->subtype == 1) { /* 0x01514ded / 0x015158df */
        out->rotation = -e->angle[2];
        out->flat = (world >= 0x18 && world <= 0x1d) || world == 0x24;
    } else {
        return 0;
    }
    return 1;
}

/* RenderEffects 0x01519c06..0x0151a401, ordinary-world Aqua Beam subtype 0.
 * This path emits sprites, then the light at the following point, twenty times. */
void mu_sfx_aqua_render(mu_sfx_effect *e, const mu_sfx_env *env)
{
    if (!e->live || e->type != 0x7f4e || e->subtype != 0) return;
    mu_sfx_effect at = *e;
    for (int k = 0; k < 20; ++k) {
        mu_sfx_call c;
        memset(&c, 0, sizeof c);
        c.routine = 0x01692eb7;
        c.type = MU_SFX_BITMAP_SPARK3;
        c.owner = -2;
        c.scale = e->scale;
        copy3(c.position, at.position);
        copy3(c.light, e->light);
        env_call(env, &c, e);
        for (int j = 0; j < 3; ++j) at.position[j] += e->direction[j];
        call_terrain_light(env, &at, e->light, 2);
    }
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

/* The joint module (reconstructed/joints) reads its services through
 * mu_jt_env; these adapters forward them to the skill environment. */
static int32_t jt_rand(void *context)
{
    return env_rand(context);
}

static float jt_height(void *context, float x, float y)
{
    return env_height(context, x, y);
}

static const mu_jt_object *jt_object(void *context, int32_t index)
{
    return env_object(context, index);
}

static void jt_call(void *context, const mu_jt_call *call)
{
    const mu_sfx_env *env = context;
    if (env && env->call)
        env->call(env->context, call, NULL);
}

static void jt_env(const mu_sfx_env *env, mu_jt_env *out)
{
    memset(out, 0, sizeof *out);
    out->context = (void *)(uintptr_t)env;
    out->rand = jt_rand;
    out->height = jt_height;
    out->object = jt_object;
    out->call = jt_call;
    out->serial = env ? env->serial : 0;
}

int mu_sfx_joint_create(mu_sfx_joint *j, int32_t type, const float position[3], const float target_position[3],
                        const float angle[3], int32_t subtype, int32_t target, float scale, uint16_t key,
                        uint16_t skill, uint8_t byte10, uint16_t word13, int32_t arg14, const mu_sfx_env *env)
{
    mu_jt_env e;
    jt_env(env, &e);
    return mu_jt_create(j, type, position, target_position, angle, subtype, target, scale, key, skill, byte10,
                        word13, arg14, &e);
}

int mu_sfx_joint_move(mu_sfx_joint *j, const mu_sfx_env *env, float time_step, int wall_scene, uint16_t wall,
                      int is_hero_target)
{
    mu_jt_env e;
    jt_env(env, &e);
    const mu_jt_move_inputs in = {time_step, wall_scene, wall, 0, is_hero_target};
    return mu_jt_move(j, &e, &in);
}

typedef struct quad_sink {
    mu_sfx_joint_quad *quads;
    int max, count, corner;
    int colored;
    float color[3];
} quad_sink;

static void qs_color(void *context, float r, float g, float b)
{
    quad_sink *q = context;
    if (q->colored)
        return;
    q->color[0] = r;
    q->color[1] = g;
    q->color[2] = b;
    q->colored = 1;
}

static void qs_begin(void *context, int32_t mode)
{
    (void)mode;
    ((quad_sink *)context)->corner = 0;
}

static void qs_texcoord(void *context, float u, float v)
{
    quad_sink *q = context;
    if (q->count < q->max && q->corner < 4) {
        q->quads[q->count].uv[q->corner][0] = u;
        q->quads[q->count].uv[q->corner][1] = v;
    }
}

static void qs_vertex(void *context, const float v[3])
{
    quad_sink *q = context;
    if (q->count < q->max && q->corner < 4)
        copy3(q->quads[q->count].position[q->corner], v);
    q->corner++;
}

static void qs_end(void *context)
{
    quad_sink *q = context;
    if (q->corner == 4 && q->count < q->max)
        q->count++;
}

int mu_sfx_joint_render(const mu_sfx_joint *j, uint8_t mode, float color[3], int32_t *render_type,
                        mu_sfx_joint_quad *quads, int max)
{
    quad_sink q;
    memset(&q, 0, sizeof q);
    q.quads = quads;
    q.max = max;
    const mu_jt_gl gl = {&q, NULL, NULL, qs_color, qs_begin, qs_texcoord, qs_vertex, qs_end};
    if (mu_jt_render(j, mode, 0.0f, &gl) <= 0)
        return 0;
    *render_type = j->render_type;
    copy3(color, q.colored ? q.color : j->light);
    return q.count;
}

/* ------------------------------------------------------------------------
 * RENDER-EFFECTS-004: the item object initialiser 0x016da00b and Rageful
 * Blow's weapon draw 0x01532bd2. */

void mu_sfx_item_object_init(mu_sfx_effect *e, const mu_sfx_env *env)
{
    const float clock = env ? env->world_time : 0.0f;
    e->light[0] = e->light[1] = e->light[2] = F_0_3;
    e->flag5 = 1;
    e->flag_c = 0;
    e->field_4 = 0;
    e->velocity = 0.0f;
    e->field_c0 = 50.0f;
    e->prior_frame = 0.0f;
    e->frame = 0.0f;
    e->prior_action = 0;
    e->action = 0;
    e->field_68 = -1;
    e->gravity = 0.0f;
    e->alpha = 1.0f;
    e->blend_mesh = -1;
    e->blend_light = 1.0f;
    e->blend_u = 0.0f;
    e->blend_v = 0.0f;
    e->field_68 = -1;
    e->scale = F_0_8;
    call_plain(env, e, MU_SFX_CALL_ITEM_LINKS);   /* 0x01295f18 on +0x358 */
    const int32_t t = e->type;
    if (t >= 0x10e6 && t <= 0x14f3)
        e->scale = f32bits(0x3f333333u);          /* 0.7 */
    const float slow = (float)sin((double)(clock * f32bits(0x3b83126fu)));   /* WorldTime * 0.004 */
    switch (t) {
    case 0xa99: case 0xa9a: case 0xa9b: case 0xa9c: case 0xa9d: case 0xa9e: case 0xa9f: case 0xaa0: case 0xaa1:
    case 0x26e7:
        e->scale = 1.0f;
        break;
    case 0xaeb: case 0xaf3: case 0x24e6: case 0x14ef:
        e->blend_mesh = 1;
        break;
    case 0xaf0: case 0x10e6: case 0xeec: case 0x16f1: case 0x16f2: case 0x16f3: case 0x1702:
        e->blend_mesh = 1;
        e->blend_light = (float)sin((double)(clock * f32bits(0x3b83126fu))) * F_0_3 + f32bits(0x3f333333u);
        break;
    case 0xaf4: case 0xb0d:
        e->blend_mesh = 1;
        e->blend_u = (float)(env_rand(env) % 10) * F_0_1;
        e->blend_light = slow * F_0_3 + f32bits(0x3f333333u);
        break;
    case 0xb05: case 0xeed: case 0xf0b: case 0x1711: case 0x16f6:
        e->field_68 = 2;
        break;
    case 0x10f0:
        e->field_68 = 1;
        break;
    case 0xeea:
        e->blend_mesh = 1;
        e->blend_light = slow * F_0_2 + F_0_8;
        break;
    case 0xeeb: case 0x22e6: case 0x236a:
        e->blend_mesh = 0;
        break;
    case 0x10ef:
        e->blend_v = -(float)(trunc_i32(clock) % 2000) * f32bits(0x3a03126fu);   /* 0.0005 */
        break;
    case 0x14e6:
        e->blend_mesh = 2;
        break;
    case 0x12ec: case 0x12f3: case 0x12f4: case 0x14ec:
        e->blend_mesh = -2;
        e->blend_light = slow * F_0_3 + f32bits(0x3f333333u);
        break;
    case 0x12f6: case 0x14ee: case 0x1516:
        e->blend_mesh = -2;
        e->blend_light = slow * F_0_2 + F_0_9;
        break;
    case 0x14eb: case 0x150c: case 0x1513:
        e->blend_mesh = 2;
        e->blend_u = (float)(env_rand(env) % 10) * F_0_1;
        e->blend_v = (float)(env_rand(env) % 10) * F_0_1;
        break;
    case 0x16f4: case 0x1701: case 0x170b:
        e->blend_mesh = 1;
        e->blend_u = (float)(env_rand(env) % 10) * F_0_1;
        e->blend_v = (float)(env_rand(env) % 10) * F_0_1;
        break;
    case 0x14ed:
        e->blend_mesh = 1;
        e->blend_light = (float)(env_rand(env) % 11) * F_0_1;
        break;
    case 0x14f1:
        e->blend_mesh = 2;
        e->blend_light = slow * F_0_3 + f32bits(0x3f333333u);
        break;
    case 0x18fe: case 0x1cfe:
        e->blend_light = (float)sin((double)(clock * f32bits(0x3a83126fu))) * F_0_4 + f32bits(0x3f19999au);
        break;
    case 0x248e: case 0x22e9:
        e->scale = 0.5f;
        e->blend_mesh = 0;
        break;
    case 0x26fb:
        e->scale = 0.5f;
        break;
    case 0x28e6:
        e->scale = f32bits(0x3f333333u);
        break;
    default:
        break;
    }
}

int mu_sfx_rageful_weapon(mu_sfx_effect *e, const float terrain_light[3], uint8_t hero_byte, const mu_sfx_env *env,
                          mu_sfx_weapon_draw *out)
{
    memset(out, 0, sizeof *out);
    if (e->skill == 0x7f8 || e->skill == 0x7fb)
        return 0;
    if (!((float)e->lifetime > 10.0f) || e->client_hit != 0)
        return 0;
    const float alpha = e->alpha;
    const mu_sfx_object *o = env_object(env, e->owner);
    const int32_t model = (o ? o->weapon : 0) + 0xae6;
    int16_t keys = 1;
    if (env && env->model && !env->model(env->context, model, 0, &keys))
        return 0;
    out->model = model;
    out->hero_class = (uint8_t)(hero_byte & 0xf);
    out->action = e->action;
    copy3(out->origin, e->position);
    const float type = (float)e->type, gravity = e->gravity;
    e->type = model;
    mu_sfx_item_object_init(e, env);
    e->gravity = gravity;
    for (int k = 0; k < 3; ++k)
        out->light[k] = terrain_light[k] + e->light[k];
    copy3(out->angle, e->angle);
    out->head_angle[0] = e->heading;
    out->head_angle[1] = e->heading_yz[0];
    out->head_angle[2] = e->heading_yz[1];
    out->frame = e->frame;
    out->prior_frame = e->prior_frame;
    out->prior_action = e->prior_action;
    out->alpha = alpha;
    out->level = (int32_t)(o ? o->level : 0) << 3;
    e->type = (int32_t)(int16_t)trunc_i32(type);
    return 1;
}

/* ------------------------------------------------------------------------
 * RENDER-EFFECTS-004: CreateArrows 0x0158d5bd and CreateArrow 0x0158cf57. */

static const int16_t special_bows[] = {0x12f8, 0x12f9, 0x12fc, 0x12fd, 0x12fe, 0x12ff, 0x1300, 0x1302, 0x1304, 0x1305,
                                       0x130a, 0x130c, 0x130e, 0x131e, 0x1320, 0x1323, 0x1326, 0x1329, 0x132c, 0x132f};

static void arrow_shot(mu_sfx_arrow_shots *out, const float angle[3], int32_t last)
{
    if (out->count < MU_SFX_ARROW_SHOTS) {
        copy3(out->angle[out->count], angle);
        out->last[out->count] = last;
    }
    ++out->count;
}

int mu_sfx_create_arrows(const mu_sfx_archer *a, float angle[3], uint16_t skill, uint16_t flag, uint16_t index,
                         mu_sfx_arrow_shots *out)
{
    memset(out, 0, sizeof *out);
    if (index == 0x34 || index == 0x1a0 || index == 0x33 || index == 0x1a8 || index == 0x2e) {
        arrow_shot(out, angle, 0);
        out->serial_steps = 1;
        return 1;
    }
    if (flag != 1) {                                   /* 0x0158dfa2 */
        arrow_shot(out, angle, 0);
    } else {
        float saved[3];
        copy3(saved, angle);
        const int32_t last = a->tree_value;
        int special = 0;
        for (size_t i = 0; i < sizeof special_bows / sizeof special_bows[0]; ++i)
            special |= a->weapon == special_bows[i];
        if (special && (skill == 0x7fc || skill == 0x7ff)) {   /* 0x0158d900 */
            const float s = skill == 0x7ff ? 0.5f : 8.0f;
            if (skill != 0x7ff)
                arrow_shot(out, angle, last);
            angle[2] = 8.0f * s + angle[2];
            arrow_shot(out, angle, last);
            angle[2] = 8.0f * s + angle[2];
            arrow_shot(out, angle, last);
            angle[2] = angle[2] - 24.0f * s;
            arrow_shot(out, angle, last);
            angle[2] = angle[2] - 8.0f * s;
            arrow_shot(out, angle, last);
        } else if (special && a->master_1a2) {          /* 0x0158daa9 */
            arrow_shot(out, angle, last);
            angle[2] = angle[2] + 8.0f;
            arrow_shot(out, angle, last);
            angle[2] = angle[2] + 8.0f;
            arrow_shot(out, angle, last);
            angle[2] = angle[2] - 24.0f;
            arrow_shot(out, angle, last);
            angle[2] = angle[2] - 8.0f;
            arrow_shot(out, angle, last);
            out->serial_steps = 1;
        } else if (a->master_1a2 || special) {          /* 0x0158dd55 / 0x0158dbfc */
            angle[2] = angle[2] + 5.0f;
            arrow_shot(out, angle, last);
            angle[2] = angle[2] + 10.0f;
            arrow_shot(out, angle, last);
            angle[2] = angle[2] - 20.0f;
            arrow_shot(out, angle, last);
            angle[2] = angle[2] - 10.0f;
            arrow_shot(out, angle, last);
            out->serial_steps = 1;
        } else {                                        /* 0x0158de8b: Triple Shot's three arrows */
            arrow_shot(out, angle, last);
            angle[2] = angle[2] + 15.0f;
            arrow_shot(out, angle, last);
            angle[2] = angle[2] - 30.0f;
            arrow_shot(out, angle, last);
            out->serial_steps = 1;
        }
        copy3(angle, saved);
    }
    if (a->weapon == 0x12f9)
        out->bow_sparks = 1;   /* 0x0158dfdc: fifteen sparks at the bow's bone, not reconstructed */
    return out->count;
}

/* The arrow model a bow (item model type) shoots: the two jump tables at 0x0158d2b8 and 0x0158d34e. */
static int32_t arrow_type(int32_t bow)
{
    switch (bow) {
    case 0x12ee: case 0x12ef: return 0x43c;
    case 0x12f0: return 0x440;
    case 0x12f1: return 0x43e;
    case 0x12f2: return 0x43d;
    case 0x12f3: return 0x443;
    case 0x12f4: return 0x442;
    case 0x12f6: return 0x458;
    case 0x12f8: return 0x471;
    case 0x12f9: return 0x474;
    case 0x1300: return 0x5b0;
    case 0x1304: return 0x45e;
    case 0x12e6: case 0x12e7: case 0x12e9: case 0x12ea: case 0x12eb: case 0x1301: return MU_SFX_MODEL_ARROW;
    case 0x12e8: return 0x43f;
    case 0x12ec: return 0x441;
    case 0x12f7: case 0x1303: return 0x459;
    case 0x12fa: return 0x47f;
    case 0x12fb: return 0x45a;
    case 0x12fc: return 0x45b;
    case 0x12fd: return 0x45c;
    case 0x12fe: return 0x525;
    case 0x12ff: return 0x5b1;
    case 0x1302: return 0x45d;
    case 0x1305: return 0x60a;
    case 0x130a: return 0x60d;
    case 0x130c: return 0x60e;
    case 0x130e: return 0x60f;
    case 0x131e: return 0x610;
    case 0x1320: return 0x612;
    case 0x1323: return 0x613;
    case 0x1326: return 0x614;
    case 0x1329: return 0x615;
    case 0x132c: return 0x616;
    case 0x132f: return 0x617;
    default: return -1;
    }
}

int mu_sfx_create_arrow(const mu_sfx_archer *a, const float position[3], const float angle[3], uint16_t skill,
                        uint16_t flag, uint16_t index, int32_t last, const mu_sfx_env *env, mu_sfx_arrow_effect *out)
{
    memset(out, 0, sizeof *out);
    int32_t bow = a->weapon;
    if (a->is_hero) {
        bow = a->hero_weapon;
        if (bow != -1)
            bow = bow + 0xae6;
    }
    int32_t subtype = 0;
    if (index == 0x34 || index == 0x1a0) {
        subtype = 2;
        out->sounds[out->sound_count++] = 0x55;
    }
    if (index == 0x33 || index == 0x1a8)
        out->sounds[out->sound_count++] = 0x82;
    if (flag == 2)
        subtype = 0x63;
    uint16_t field8 = 0xffff;
    copy3(out->position, position);
    if (index != 0x7e7 && index != 0x7fc && index != 0x7fd && index != 0x7fe && index != 0x2d7)
        out->position[2] = env_height(env, out->position[0], out->position[1]);
    copy3(out->angle, angle);
    if (a->mastery == 0x33 || a->mastery == 0x2d7 || a->mastery == 0x7fe)
        field8 = a->field_364;
    out->subtype = subtype;
    out->info.key = a->key;
    out->info.skill = skill;
    out->info.word4 = flag;
    if (index == 0x2e) {                                /* 0x0158d18f: CreateEffect 0x49d at the target */
        out->routine = MU_SFX_CALL_EFFECT;
        out->type = 0x49d;
        out->subtype = 0;
        out->owner = MU_SFX_ARROW_OWNER_TARGET;
        out->info.field8 = 0xffff;
        return 1;
    }
    out->info.field8 = field8;
    out->info.field18 = last;
    out->routine = MU_SFX_CALL_ARROW_EFFECT;
    if (a->special) {                                   /* 0x0158d232 */
        out->type = 0x6a9;
        out->owner = MU_SFX_ARROW_OWNER_CHARACTER;
        out->sounds[out->sound_count++] = -0x524;       /* 0x00a6ad76(0x524, 1) */
        out->sounds[out->sound_count++] = 0x524;
        return 1;
    }
    out->type = arrow_type(bow);
    out->owner = MU_SFX_ARROW_OWNER_OBJECT;
    if (out->type == -1)
        out->routine = 0;
    return out->routine != 0;
}
