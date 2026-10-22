/* The client's joint pool (NATIVE-JOINT-001). See joints.h and
 * docs/research/client-joints.md. Build with -ffp-contract=off. */
#include "joints.h"

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
#define F_0_4 f32bits(0x3ecccccdu)   /* 0x01a7df0c */
#define F_0_8 f32bits(0x3f4ccccdu)   /* 0x01a7df18 */
#define F_0_6 f32bits(0x3f19999au)
#define F_0_01 f32bits(0x3c23d70au)
#define F_0_33 f32bits(0x3ea8f5c3u)  /* 0x01a7ed98 */
#define F_0_08 f32bits(0x3da3d70au)  /* 0x01a7e914 */
#define F_0_005 f32bits(0x3ba3d70au) /* 0x01a7e4c8 */
#define F_0_0006 f32bits(0x3a1d4952u) /* 0x01a8009c */
#define F_0_001 f32bits(0x3a83126fu) /* 0x01a7e308 */
#define F_TINY f32bits(0x358637bdu)  /* 0x01a80990, 1e-6 (the near-zero test 0x00a72592) */

static int32_t jrand(const mu_jt_env *env)
{
    return env && env->rand ? env->rand(env->context) : 0;
}

static float jheight(const mu_jt_env *env, float x, float y)
{
    return env && env->height ? env->height(env->context, x, y) : 0.0f;
}

static const mu_jt_object *jobject(const mu_jt_env *env, int32_t index)
{
    if (index < 0 || !env || !env->object)
        return NULL;
    return env->object(env->context, index);
}

static void jcall(const mu_jt_env *env, const mu_jt_call *call)
{
    if (env && env->call)
        env->call(env->context, call);
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

/* idiv with the client's operands; a zero divisor faults in the client (the
 * C returns 0, not reached by the supported kinds' inputs). */
static int32_t imod(int32_t value, int32_t divisor)
{
    if (divisor == 0 || (divisor == -1 && value == INT32_MIN))
        return 0;
    return value % divisor;
}

/* 0x00cee2cb: degrees to radians through double. */
static float radians(float degrees)
{
    return (float)((double)degrees * 0.017453292519943295);
}

/* 0x009fa20d / 0x00968117: the C runtime cos / sin of a float, rounded to float. */
static float fcos(float x)
{
    return (float)cos((double)x);
}

static float fsin(float x)
{
    return (float)sin((double)x);
}

/* The vector normalisation 0x00cfd0cc -> 0x00cfd15f: the length through the
 * double square root 0x00961a07; a length inside (-1e-6, 1e-6) zeroes the
 * vector (0x00cfcf7b), otherwise it is multiplied by 1 / length. */
static void normalize3(float v[3])
{
    float length = (float)sqrt((double)(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]));
    if (F_TINY > length && length > -F_TINY) {
        v[0] = v[1] = v[2] = 0.0f;
        return;
    }
    float k = 1.0f / length;
    v[0] = v[0] * k;
    v[1] = v[1] * k;
    v[2] = v[2] * k;
}

int mu_jt_kind_supported(int32_t type, int32_t subtype)
{
    switch (type) {
    case MU_JT_BITMAP_ENERGY:
        return subtype == 1;
    case MU_JT_BITMAP_SPIRIT:
        return subtype == 0;
    case MU_JT_BITMAP_SPARK:
        return subtype == 0;
    case MU_JT_BITMAP_FLARE:
        return subtype == 0;   /* NATIVE-HELPERS-002 */
    case MU_JT_TYPE_THUNDER_BOLT:
        return subtype >= 0x10 && subtype <= 0x1a;
    default:
        return 0;
    }
}

/* corners 0..3 of tail `tail`: pos + R(-w/2, 0, 0), R(w/2, 0, 0), R(0, 0, -w/2), R(0, 0, w/2) */
static void joint_cross(mu_jt_joint *j, const float m[12], int tail)
{
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

void mu_jt_tail_shift(mu_jt_joint *j, const float m[12])
{
    j->num_tails = j->num_tails + 1;
    if (j->num_tails > j->max_tails - 1)
        j->num_tails = j->max_tails - 1;
    for (int i = j->num_tails - 1; i >= 0; --i)
        if (i + 1 < MU_JT_TAILS)
            for (int c = 0; c < 4; ++c)
                copy3(j->tails[i + 1][c], j->tails[i][c]);
    joint_cross(j, m, 0);
}

/* ------------------------------------------------------------------------ CreateJoint */

/* 0x7f7d's target point: start + R(angle) * (rand % 2a - a, rand % 2a - a, -length). */
static void bolt_target(mu_jt_joint *j, const mu_jt_env *env, int32_t a, float length)
{
    float d[3], m[12], r[3];
    d[0] = (float)(imod(jrand(env), a * 2) - a);
    d[1] = (float)(imod(jrand(env), a * 2) - a);
    d[2] = -length;
    mu_angle_matrix(j->angle, m);
    mu_vector_rotate(d, m, r);
    j->target_position[0] = j->start[0] + r[0];
    j->target_position[1] = j->start[1] + r[1];
    j->target_position[2] = j->start[2] + r[2];
}

/* CreateJoint 0x7f7d 0x01545bdf, subtypes 0x10..0x1a 0x0154732a..0x015485b7.
 * Returns 0 when the case returns before the tail clamp (width <= 0). */
static int create_thunder_bolt(mu_jt_joint *j, int32_t target, float scale, const mu_jt_env *env)
{
    j->scale = scale;
    j->tex_type = MU_JT_BITMAP_THUNDER;
    if (!(0.0f < j->scale) && !isnan(j->scale))
        return 0;   /* 0x01553637: no clamp, max_tails and lifetime keep the record's previous values */
    j->tex_type = MU_JT_BITMAP_THUNDER;
    j->max_tails = 50;
    j->lifetime = 20;
    if (j->subtype == 0x16 || j->subtype == 0x17) {
        /* 0x01547ca6: the phase of the ring's bright segments */
        int32_t half = j->max_tails / 2;
        j->phase = imod(trunc_i32(env ? env->world_time : 0.0f), half);
    }
    copy3(j->start, j->position);
    switch (j->subtype) {
    case 0x10:
    case 0x11:
        bolt_target(j, env, 50, j->scale * 300.0f);
        break;
    case 0x12:
    case 0x13:
        bolt_target(j, env, 100, 300.0f);
        break;
    case 0x14:
    case 0x15:
    case 0x16:
    case 0x17:
        copy3(j->target_position, j->start);
        break;
    case 0x18:
    case 0x19:
        bolt_target(j, env, 50, j->scale * 10.0f);
        break;
    case 0x1a:
        bolt_target(j, env, 50, j->scale * 50.0f);
        break;
    default:
        break;
    }
    /* the light of the object the joint is created for (+0xec; the client reads through a NULL target) */
    const mu_jt_object *o = jobject(env, target);
    if (o)
        copy3(j->light, o->light);
    return 1;
}

int mu_jt_create(mu_jt_joint *j, int32_t type, const float position[3], const float target_position[3],
                 const float angle[3], int32_t subtype, int32_t target, float scale, uint16_t key, uint16_t skill,
                 uint8_t byte10, uint16_t word13, int32_t arg14, const mu_jt_env *env)
{
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
    int supported = mu_jt_kind_supported(type, subtype);
    switch (type) {
    case MU_JT_BITMAP_ENERGY:
        if (subtype != 1)
            break;
        /* 0x0153e28e */
        j->lifetime = 12;
        j->scale = scale;
        j->max_tails = 2;
        j->velocity = 0.0f;
        break;
    case MU_JT_BITMAP_SPIRIT:
        if (subtype != 0)
            break;
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
    case MU_JT_BITMAP_SPARK:
        if (subtype != 0)
            break;
        /* 0x0154323e, subtype 0: 0x01543264 */
        j->scale = 2.0f;
        j->velocity = (float)(imod(jrand(env), 20) + 6);
        j->lifetime = imod(jrand(env), 8) + 8;
        j->max_tails = 2;
        j->light[0] = j->light[1] = j->light[2] = 1.0f;
        break;
    case MU_JT_TYPE_THUNDER_BOLT:
        if (!supported)
            break;
        if (!create_thunder_bolt(j, target, scale, env))
            return 1;
        break;
    case MU_JT_BITMAP_FLARE: {
        if (subtype != 0)
            break;
        /* NATIVE-HELPERS-002, 0x015496cb, subtype 0: a flare circling its target, the lap set by the key */
        j->lifetime = 100;
        j->max_tails = 20;
        j->scale = 10.0f;
        j->scale = scale;
        j->jitter[2] = (float)imod(jrand(env), 150) / 100.0f;
        j->jitter[1] = (float)(imod(jrand(env), 500) - 250);
        j->velocity = 40.0f;
        if (j->scale > 10.0f) {
            j->lifetime = 50;
            j->jitter[2] = (float)(imod(jrand(env), 250) + 200) / 100.0f;
        }
        const mu_jt_object *t = jobject(env, j->target);   /* the client reads the target's light (never NULL) */
        j->light[0] = t ? t->light[0] : 0.0f;
        j->light[1] = t ? t->light[1] : 0.0f;
        j->light[2] = t ? t->light[2] : 0.0f;
        copy3(j->target_position, target_position);       /* 0x0154bfad */
        break;
    }
    default:
        break;
    }
    if (j->max_tails > MU_JT_TAILS)
        j->max_tails = MU_JT_TAILS;   /* 0x0155361d */
    return supported;
}

/* ------------------------------------------------------------------------ MoveJoint */

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

static void add_rotated(mu_jt_joint *j, const float v[3], const float m[12])
{
    float r[3];
    mu_vector_rotate(v, m, r);
    j->position[0] = j->position[0] + r[0];
    j->position[1] = j->position[1] + r[1];
    j->position[2] = j->position[2] + r[2];
}

/* The Shiny02 flash at the start of every bolt and arc: CreateSprite(0x7f67, start, 1, light, NULL,
 * rand % 360, 0, 4, the default sheet). */
static void start_flash(mu_jt_joint *j, const mu_jt_env *env)
{
    mu_jt_call c;
    memset(&c, 0, sizeof c);
    c.routine = MU_JT_CALL_SPRITE;
    c.type = MU_JT_BITMAP_SHINY2;
    c.angle[0] = (float)imod(jrand(env), 360);
    copy3(c.position, j->start);
    c.scale = 1.0f;
    copy3(c.light, j->light);
    c.owner = -1;
    c.subtype = 0;   /* blend */
    c.range = 4;     /* rotation axes */
    jcall(env, &c);
}

/* The step from the start toward the target: (target - start), normalised, times length / max_tails. */
static void bolt_step(const mu_jt_joint *j, float length, float d[3])
{
    d[0] = j->target_position[0] - j->start[0];
    d[1] = j->target_position[1] - j->start[1];
    d[2] = j->target_position[2] - j->start[2];
    normalize3(d);
    float k = length / (float)j->max_tails;
    d[0] = d[0] * k;
    d[1] = d[1] * k;
    d[2] = d[2] * k;
}

/* (rand % (int)(2w) - (int)w, rand % (int)(2w), 0): the second rand() is the x offset. */
static void bolt_jitter(const mu_jt_env *env, float w, float v[3])
{
    int32_t span = trunc_i32(w * 2.0f);
    int32_t r1 = imod(jrand(env), span);
    v[1] = (float)r1;
    int32_t r2 = imod(jrand(env), span);
    v[0] = (float)(r2 - trunc_i32(w));
    v[2] = 0.0f;
}

/* The jagged bolts 0x10/0x11 (0x015737a6), 0x18 (0x01576c79), 0x19/0x1a (0x01577476): rebuilt from
 * the start every step; the head walks max_tails - 1 steps, jittered in the first and third parts and
 * pushed sideways by w in the second, with one tail per step. */
static void move_bolt(mu_jt_joint *j, const mu_jt_env *env)
{
    const float s = j->scale;
    float length, width, w;
    int32_t t1, t2, walk;
    switch (j->subtype) {
    case 0x10:
    case 0x11:
        length = j->scale * 300.0f;
        width = j->subtype == 0x10 ? 50.0f * s * ((float)j->lifetime + 1.0f) / 20.0f
                                   : 75.0f * s * ((float)j->lifetime + 1.0f) / 20.0f;
        w = 9.0f * s + 1.0f;
        t1 = 0x23;
        t2 = 0x1e;
        walk = 1;
        break;
    case 0x18:
        length = j->scale * 10.0f;
        width = 60.0f * s * ((float)j->lifetime + 1.0f) / 20.0f;
        w = 6.0f * s + 1.0f;
        t1 = 0x23;
        t2 = 0x1e;
        walk = 0;   /* 0x18 computes the step toward the target but never adds it */
        break;
    default:   /* 0x19, 0x1a */
        length = j->subtype == 0x19 ? j->scale * 10.0f : j->scale * 50.0f;
        width = 50.0f * s * ((float)j->lifetime + 1.0f) / 20.0f;
        w = 4.0f * s + 1.0f;
        t1 = 0x19;
        t2 = 0x14;
        walk = 1;
        break;
    }
    copy3(j->position, j->start);
    float m[12];
    mu_angle_matrix(j->angle, m);
    start_flash(j, env);
    float d[3];
    bolt_step(j, length, d);
    j->scale = width;
    mu_jt_tail_shift(j, m);
    for (int32_t i = 1; i < j->max_tails; ++i) {
        if (walk) {
            j->position[0] = j->position[0] + d[0];
            j->position[1] = j->position[1] + d[1];
            j->position[2] = j->position[2] + d[2];
        }
        float v[3];
        if (i >= 1 && i < j->max_tails - t1) {
            bolt_jitter(env, w, v);
            add_rotated(j, v, m);
        } else if (j->max_tails - t1 <= i && i < j->max_tails - t2) {
            v[0] = w;
            v[1] = 0.0f;
            v[2] = 0.0f;
            add_rotated(j, v, m);
        } else if (j->max_tails - t2 <= i && i < j->max_tails - 5) {
            bolt_jitter(env, w, v);
            add_rotated(j, v, m);
        }
        mu_jt_tail_shift(j, m);
    }
    j->scale = s;
}

/* The arcs 0x12 (0x015740c4) and 0x13 (0x015746e6): the step toward the target plus a polynomial bow in
 * x and y and a jitter of +-30 times a tenth of the width. */
static void move_arc(mu_jt_joint *j, const mu_jt_env *env)
{
    const float s = j->scale;
    const float length = 300.0f;
    copy3(j->position, j->start);
    float m[12];
    mu_angle_matrix(j->angle, m);
    start_flash(j, env);
    float d[3];
    bolt_step(j, length, d);
    j->scale = ((float)j->lifetime + 1.0f) * 75.0f / 20.0f;
    mu_jt_tail_shift(j, m);
    const float w = 30.0f;
    const float k = s * F_0_1;
    for (int32_t i = 1; i < j->max_tails; ++i) {
        j->position[0] = j->position[0] + d[0];
        j->position[1] = j->position[1] + d[1];
        j->position[2] = j->position[2] + d[2];
        float bow;
        if (j->subtype == 0x12)
            bow = F_0_005 * s * s * (float)(i * 3 * i - i * 150 + 1250);
        else
            bow = F_0_0006 * s * s * (float)(i - 30) * (float)(i * 2 * i - i * 105 + 750);
        int32_t span = trunc_i32(w * 2.0f);
        float r[3];
        for (int q = 0; q < 3; ++q)
            r[q] = (float)(imod(jrand(env), span) - trunc_i32(w)) * k;
        float v[3] = {bow + r[0], bow + r[1], r[2]};
        add_rotated(j, v, m);
        mu_jt_tail_shift(j, m);
    }
    j->scale = s;
}

/* The rings 0x14..0x17 (0x01574d17, 0x01575536, 0x01575d57, 0x015764e4): max_tails - 2 points around
 * the start at 100 times the width (0x15/0x17: 1.5 times that in y), each lifted by a random height whose
 * range depends on the point's place in a travelling pattern; every point is a tail of its own (the head
 * steps out, the tail shifts, the head steps back) and the first point closes the ring. */
static void move_ring(mu_jt_joint *j, const mu_jt_env *env)
{
    const float s = j->scale;
    float m[12];
    mu_angle_matrix(j->angle, m);
    copy3(j->position, j->start);
    if (j->subtype == 0x14)
        j->scale = (float)(j->lifetime + 1) * 60.0f / 20.0f;
    else
        j->scale = ((float)j->lifetime + 1.0f) * 60.0f / 20.0f;
    float v[3] = {0.0f, 0.0f, 0.0f}, r[3] = {0.0f, 0.0f, 0.0f}, first[3] = {0.0f, 0.0f, 0.0f};
    const float radius = s * 100.0f;
    const int stretched = j->subtype == 0x15 || j->subtype == 0x17;
    const int travelling = j->subtype == 0x14 || j->subtype == 0x15;
    for (int32_t k = 0; k < j->max_tails - 2; ++k) {
        float a = (float)k * 360.0f / (float)(j->max_tails - 2);
        float j1 = (float)(imod(jrand(env), 6) - 3);
        float j2 = (float)(imod(jrand(env), 6) - 3);
        v[0] = (radius + j1) * fcos(radians(a));
        v[1] = ((stretched ? radius * 1.5f : radius) + j2) * fsin(radians(a));
        float low = 0.0f, range = 3.0f;
        if (travelling) {
            float u = (float)(j->max_tails - 1 - k) / (float)(j->max_tails - 1);
            float t = (float)imod(trunc_i32(env ? env->world_time : 0.0f), 1000) * F_0_001;
            float p = (u + t - (float)trunc_i32(u + t)) * (float)j->max_tails;
            if ((p >= 29.0f && 32.0f >= p) || (p >= 41.0f && 45.0f >= p)) {
                low = 0.0f;
                range = 10.0f;
            } else if ((p >= 35.0f && 39.0f >= p) || (p >= 5.0f && 8.0f >= p)) {
                low = 10.0f;
                range = 15.0f;
            } else if (p >= 15.0f && 20.0f >= p) {
                low = 5.0f;
                range = 10.0f;
            }
        } else {
            const int32_t ph = j->phase;
            if ((ph + 0x1d <= k && k <= ph + 0x20) || (ph + 0x29 <= k && k <= ph + 0x2d)) {
                range = 10.0f;
            } else if ((ph + 0x23 <= k && k <= ph + 0x27) || (ph + 5 <= k && k <= ph + 8)) {
                low = 10.0f;
                range = 15.0f;
            } else if (ph + 0xf <= k && k <= ph + 0x14) {
                low = 5.0f;
                range = 10.0f;
            }
        }
        /* 0x0185ca80: +1 on an odd rand(), -1 on an even one */
        float sign = imod(jrand(env), 2) != 0 ? 1.0f : -1.0f;
        v[2] = sign * ((float)imod(jrand(env), trunc_i32(range)) + low);
        mu_angle_matrix(j->angle, m);
        mu_vector_rotate(v, m, r);
        j->position[0] = j->position[0] + r[0];
        j->position[1] = j->position[1] + r[1];
        j->position[2] = j->position[2] + r[2];
        mu_jt_tail_shift(j, m);
        j->position[0] = j->position[0] - r[0];
        j->position[1] = j->position[1] - r[1];
        j->position[2] = j->position[2] - r[2];
        if (k == 0)
            copy3(first, v);
    }
    mu_angle_matrix(j->angle, m);
    mu_vector_rotate(first, m, r);
    j->position[0] = j->position[0] + r[0];
    j->position[1] = j->position[1] + r[1];
    j->position[2] = j->position[2] + r[2];
    mu_jt_tail_shift(j, m);
    j->scale = s;
}

int mu_jt_move(mu_jt_joint *j, const mu_jt_env *env, const mu_jt_move_inputs *in)
{
    if (!mu_jt_kind_supported(j->type, j->subtype))
        return 0;
    const mu_jt_move_inputs zero = {0.0f, 0, 0, 0};
    if (!in)
        in = &zero;
    float m[12] = {0};
    float d0 = j->position[0] - j->target_position[0];
    float d1 = j->position[1] - j->target_position[1];
    if (j->moving) {
        mu_angle_matrix(j->angle, m);
        if (!(j->velocity == 0.0f)) {
            float v[3] = {0.0f, -j->velocity, 0.0f};
            add_rotated(j, v, m);
        }
    }
    const mu_jt_object *t = jobject(env, j->target);
    switch (j->type) {
    case MU_JT_BITMAP_ENERGY: {
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
        j->light[1] = l * F_0_6;
        j->light[2] = l * 1.0f;
        if (j->lifetime == 1) {
            /* the arrival flash: CreateSprite(Shiny02 0x7f67, goal, (rand % 8 + 8) * 0.2, light, target, rand % 360) */
            mu_jt_call c;
            memset(&c, 0, sizeof c);
            c.routine = MU_JT_CALL_SPRITE;
            c.type = MU_JT_BITMAP_SHINY2;
            c.angle[0] = (float)(jrand(env) % 360);
            c.scale = (float)(jrand(env) % 8 + 8) * F_0_2;
            copy3(c.position, goal);
            copy3(c.light, j->light);
            c.owner = j->target;
            c.subtype = 0;   /* blend */
            c.range = 4;     /* rotation axes */
            jcall(env, &c);
        }
        break;
    }
    case MU_JT_BITMAP_SPIRIT: {
        /* 0x01561038, subtype 0: 0x0156105e */
        if (j->scale == 80.0f) {
            /* the wide spirit leaves a Laser01 (0x421) effect each step */
            mu_jt_call c;
            memset(&c, 0, sizeof c);
            c.routine = MU_JT_CALL_EFFECT;
            c.type = 0x421;
            c.owner = -1;
            copy3(c.position, j->position);
            copy3(c.angle, j->angle);
            copy3(c.light, j->light);
            jcall(env, &c);
            if (in->wall_scene && (in->wall & 0x100)) {
                j->velocity = 0.0f;
                j->lifetime = (int32_t)((float)j->lifetime / 5.0f);
                goto tail;
            }
            if (j->lifetime % 15 == 0 && in->is_hero_target) {
                memset(&c, 0, sizeof c);
                c.routine = MU_JT_CALL_AREA_ATTACK;
                c.type = j->skill;
                c.scale = 150.0f;
                copy3(c.position, j->position);
                c.subtype = j->serial;
                c.owner = -1;
                jcall(env, &c);
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
        j->jitter[0] = (float)(jrand(env) % 32 - 16) * F_0_2 + j->jitter[0];
        j->jitter[2] = (float)(jrand(env) % 32 - 16) * F_0_8 + j->jitter[2];
        j->angle[0] = j->angle[0] + j->jitter[0];
        j->angle[2] = j->angle[2] + j->jitter[2];
        j->jitter[0] = j->jitter[0] * F_0_6;
        j->jitter[2] = j->jitter[2] * F_0_8;
        float h = jheight(env, j->position[0], j->position[1]);
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
            float dark = -(float)(jrand(env) % 4 + 4) * F_0_01;
            mu_jt_call c;
            memset(&c, 0, sizeof c);
            c.routine = MU_JT_CALL_TERRAIN_LIGHT;
            c.position[0] = j->position[0];
            c.position[1] = j->position[1];
            c.light[0] = c.light[1] = c.light[2] = dark;
            c.range = 4;
            c.owner = -1;
            jcall(env, &c);
        }
        break;
    }
    case MU_JT_BITMAP_SPARK:
        /* 0x0156977b: subtype 0 has no case (the head's forward motion only) */
        break;
    case MU_JT_BITMAP_FLARE: {
        /* NATIVE-HELPERS-002, 0x01578049, subtype 0: the head on a circle around the target position */
        float a;
        if ((int16_t)j->key != -1)
            a = ((float)j->lifetime + j->jitter[1]) / (float)(int16_t)j->key;
        else
            a = ((float)j->lifetime + j->jitter[1]) * F_0_1;
        j->position[0] = fcos(a) * j->velocity + j->target_position[0];
        j->position[1] = j->target_position[1] - fsin(a) * j->velocity;
        j->position[2] = j->position[2] + j->jitter[2];
        /* 0x0157c288: fading over the last ten steps */
        if (j->lifetime < 10)
            for (int k = 0; k < 3; ++k)
                j->light[k] = j->light[k] / 1.3f;
        /* 0x0157c344: a thin ring stops (and stops shifting its tails) when its target attacks */
        if (40.0f > j->scale && t) {
            const uint16_t act = t->action;
            if ((act >= 0x32 && act < 0x6f) || (act >= 0x89 && act <= 0x8d)) {
                j->subtype = 1;
                j->tail_update = 0;
                j->lifetime = j->lifetime > 10 ? 10 : j->lifetime;
            }
        }
        break;
    }
    case MU_JT_TYPE_THUNDER_BOLT:
        /* 0x0156fb0f */
        switch (j->subtype) {
        case 0x10: case 0x11: case 0x18: case 0x19: case 0x1a:
            move_bolt(j, env);
            break;
        case 0x12: case 0x13:
            move_arc(j, env);
            break;
        default:
            move_ring(j, env);
            break;
        }
        break;
    default:
        break;
    }
tail:
    /* 0x015896fb (0x7fd6 subtype 0x36 shifts with argument 1, not ported) */
    if (j->tail_update)
        mu_jt_tail_shift(j, m);
    j->time = j->time + in->time_step;
    j->lifetime = j->lifetime - 1;
    if (j->lifetime < 0)
        j->live = 0;
    /* (0x7f78 / 0x7fdd subtypes 4 and 0xc move a second time when LifeTime % 12 != 0; not supported kinds) */
    return 1;
}

/* ------------------------------------------------------------------------ RenderJoints */

static void gl_state(const mu_jt_gl *gl, int32_t wrapper, int32_t argument)
{
    if (gl && gl->state)
        gl->state(gl->context, wrapper, argument);
}

static void gl_color(const mu_jt_gl *gl, float r, float g, float b)
{
    if (gl && gl->color3)
        gl->color3(gl->context, r, g, b);
}

static void gl_quad(const mu_jt_gl *gl, const float *p0, const float *p1, const float *p2, const float *p3,
                    const float uv[4][2])
{
    if (!gl)
        return;
    const float *p[4] = {p0, p1, p2, p3};
    if (gl->begin)
        gl->begin(gl->context, MU_JT_GL_QUADS);
    for (int k = 0; k < 4; ++k) {
        if (gl->texcoord)
            gl->texcoord(gl->context, uv[k][0], uv[k][1]);
        if (gl->vertex)
            gl->vertex(gl->context, p[k]);
    }
    if (gl->end)
        gl->end(gl->context);
}

int mu_jt_render(const mu_jt_joint *j, uint8_t mode, float world_time, const mu_jt_gl *gl)
{
    if (!j->live || j->num_tails <= 0 || !j->faces)
        return 0;
    if (mode == 1 && j->field_64 == 2)
        return 0;
    if (mode == 2 && j->field_64 == 1)
        return 0;
    switch (j->render_type) {
    case 1: gl_state(gl, MU_JT_STATE_ADD, 0); break;
    case 2: gl_state(gl, MU_JT_STATE_ALPHA, 1); break;
    case 3: gl_state(gl, MU_JT_STATE_SUBTRACT, 0); break;
    case 4: gl_state(gl, MU_JT_STATE_ADD_INVERSE, 0); break;
    default: break;
    }
    /* the record colour: none for 0x7fd5 (its subtype 5 binds the texture an extra time) */
    if (j->type != MU_JT_BITMAP_SPARK)
        gl_color(gl, j->light[0] * j->brightness, j->light[1] * j->brightness, j->light[2] * j->brightness);
    if (gl && gl->bind)
        gl->bind(gl->context, j->tex_type);
    const int bolt = j->type == MU_JT_BITMAP_THUNDER || j->type == MU_JT_TYPE_THUNDER_BOLT;
    int quads = 0;
    for (int32_t i = 0; i < j->num_tails && i + 1 < MU_JT_TAILS; ++i) {
        /* 0x0158a088: tails a kind skips */
        if (j->type == 0x7f5a && j->subtype == 0 && i < 1)
            continue;
        if (j->type == MU_JT_BITMAP_ENERGY && (j->subtype == 9 || j->subtype == 0xa) && i == j->num_tails - 1)
            continue;
        float u0, u1;
        if (j->field_a24) {
            u0 = (float)(j->num_tails - i) / 16.0f;
            u1 = (float)(j->num_tails - (i + 1)) / 16.0f;
        } else if (j->field_a25 == 3) {
            u0 = 1.0f - (float)i / (float)(j->max_tails - 1);
            u1 = 1.0f - (float)(i + 1) / (float)(j->max_tails - 1);
        } else if (j->field_a25 == 4) {
            u0 = (float)(j->num_tails - i) / (float)j->num_tails;
            u1 = (float)(j->num_tails - (i + 1)) / (float)j->num_tails;
        } else if (j->field_a25 == 5) {
            u0 = 1.0f - (float)(j->num_tails - i) / (float)j->num_tails;
            u1 = 1.0f - (float)(j->num_tails - (i + 1)) / (float)j->num_tails;
        } else {
            u0 = (float)(j->num_tails - i) / (float)(j->max_tails - 1);
            u1 = (float)(j->num_tails - (i + 1)) / (float)(j->max_tails - 1);
        }
        /* 0x0158a27e */
        float t = (float)imod(trunc_i32(world_time), 1000) * F_0_001;
        if (bolt) {
            u0 = u0 * 2.0f;
            u1 = u1 * 2.0f;
            u0 = u0 - t;
            u1 = u1 - t;
        }
        if (j->type == 0x7f81 && j->reached)
            continue;
        if ((j->type == 0x7fde && j->subtype >= 0 && j->subtype <= 4) || (j->subtype >= 0xb && j->subtype <= 0xd)) {
            int32_t half = (j->max_tails - 1) / 2;
            u0 = (float)(j->num_tails - i) / (float)half;
            u1 = (float)(j->num_tails - (i + 1)) / (float)half;
            u0 = u0 - t;
            u1 = u1 - t;
        }
        if (j->field_a24) {
            t = t * 2.0f;
            u0 = u0 * 2.0f;
            u1 = u1 * 2.0f;
            u0 = u0 - t;
            u1 = u1 - t;
        }
        if (j->type == MU_JT_TYPE_THUNDER_BOLT) {
            /* 0x0158ad67: the bolt's per-tail colour */
            float f = 1.0f;
            switch (j->subtype) {
            case 0x10: case 0x11: case 0x12: case 0x13: case 0x18: case 0x19: case 0x1a:
                u0 = (t + 1.0f) * F_0_33 + u0;
                u1 = (t + 1.0f) * F_0_33 + u1;
                f = (float)(i + 10) / (float)j->num_tails * (float)j->lifetime * F_0_08;
                break;
            case 0x14: case 0x15: case 0x16: case 0x17:
                u0 = u0 - t;
                u0 = 0.0f > u0 ? u0 + 2.0f : u0;
                u1 = u1 - t;
                u1 = 0.0f > u1 ? u1 + 2.0f : u1;
                f = (float)j->lifetime * F_0_1;
                break;
            default:
                break;
            }
            gl_color(gl, j->light[0] * f, j->light[1] * f, j->light[2] * f);
        }
        float v0 = 0.0f, v1 = 1.0f;
        float a = u0, b = u1;
        if (j->field_a25 == 1) {
            v0 = 1.0f;
            v1 = 0.0f;
        } else if (j->field_a25 == 2) {
            a = 1.0f - a;
            b = 1.0f - b;
        }
        if (j->faces & 1) {
            const float uv[4][2] = {{a, v1}, {a, v0}, {b, v0}, {b, v1}};
            gl_quad(gl, j->tails[i][2], j->tails[i][3], j->tails[i + 1][3], j->tails[i + 1][2], uv);
            ++quads;
        }
        if (j->faces & 2) {
            if (bolt) {
                a = t * 2.0f + a;
                b = t * 2.0f + b;
            }
            const float uv[4][2] = {{a, v0}, {a, v1}, {b, v1}, {b, v0}};
            gl_quad(gl, j->tails[i][0], j->tails[i][1], j->tails[i + 1][1], j->tails[i + 1][0], uv);
            ++quads;
        }
    }
    return quads;
}
