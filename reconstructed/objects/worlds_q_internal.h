#ifndef MU_WORLDS_Q_INTERNAL_H
#define MU_WORLDS_Q_INTERNAL_H
#include "worlds_q.h"
#include "worlds_b_internal.h"

/* The type's action table (NULL without a model) and its count. */
static inline uint8_t *q_actions(const mu_q_inputs *in, const uint8_t *o, int32_t *count)
{
    *count = 0;
    return in->actions ? in->actions(in->context, mu_obj_i32(o, MU_OBJF_TYPE), count) : NULL;
}
static inline float q_speed(const uint8_t *record) { float v; memcpy(&v, record + 4, 4); return v; }
static inline int16_t q_keys(const uint8_t *record) { int16_t v; memcpy(&v, record + 8, 2); return v; }

/* 0x00eaaa44(type, action): the action's record, NULL without a model or outside 0..count-1 (0x012bcf9d). */
static inline const uint8_t *q_action_at(const mu_q_inputs *in, const uint8_t *o)
{
    int32_t count;
    const uint8_t *table = q_actions(in, o, &count);
    const int32_t action = mu_obj_u16(o, MU_OBJF_ACTION);
    return table && action < count ? table + 16 * action : NULL;
}

/* frame >= keys - PlaySpeed (comiss: false for NaN). */
static inline int q_action_ended(const uint8_t *o, const uint8_t *record)
{
    return mu_obj_f32(o, MU_OBJF_FRAME) >= (float)q_keys(record) - q_speed(record);
}

/* SetAction 0x012affa4(o, action). */
static inline void q_set_action(const mu_q_inputs *in, uint8_t *o, int32_t action)
{
    int32_t count;
    if (!q_actions(in, o, &count) || action >= count || mu_obj_u16(o, MU_OBJF_ACTION) == action)
        return;
    mu_obj_set_u16(o, MU_OBJF_PRIOR_ACTION, mu_obj_u16(o, MU_OBJF_ACTION));
    mu_obj_set_f32(o, MU_OBJF_PRIOR_FRAME, mu_obj_f32(o, MU_OBJF_FRAME));
    mu_obj_set_u16(o, MU_OBJF_ACTION, (uint16_t)action);
    mu_obj_set_f32(o, MU_OBJF_FRAME, 0.0f);
}

/* 0x011ff622: a random value of [lo, hi] in 1/steps steps. */
static inline float q_rand_range(const mu_q_inputs *in, float lo, float hi, uint32_t steps)
{
    const float s = (float)(double)steps;
    const int32_t a = wb_int(s * lo), b = wb_int(s * hi);
    float x = (float)(in->rand_fn(in->context) % (b - a + 1) + a) / s;
    if (lo > x)
        x = lo;
    else if (x > hi)
        x = hi;
    return x;
}

static inline float q_sin(float x) { return (float)sin((double)x); }   /* 0x009681bd */
static inline float q_cos(float x) { return (float)cos((double)x); }   /* 0x009fa223 */

static inline void q_add_light(mu_obj_log *log, int32_t i, float x, float y, const float rgb[3], int32_t range)
{
    mu_obj_event *e = wb_event(log, MU_OBJ_CALL_ADD_LIGHT, i);
    wb_float(e, x);
    wb_float(e, y);
    wb_vec(e, rgb);
    wb_arg(e, (uint32_t)range);
}

/* CreateParticle(bitmap, position, angle, light, sub, scale, owner ? object : 0, 0). */
static inline void q_particle(mu_obj_log *log, int32_t i, uint32_t bitmap, const float p[3], const float a[3],
                              const float l[3], uint32_t sub, float scale, int owner)
{
    mu_obj_event *e = wb_event(log, MU_OBJ_CALL_PARTICLE, i);
    wb_arg(e, bitmap);
    wb_vec(e, p);
    wb_vec(e, a);
    wb_vec(e, l);
    wb_arg(e, sub);
    wb_float(e, scale);
    wb_arg(e, owner ? 1u : 0u);
}

/* CreateSprite(bitmap, position, scale, light, object, rotation, 0, 4, {1, 1, 1.0}). */
static inline void q_sprite(mu_obj_log *log, int32_t i, uint32_t bitmap, const float p[3], float scale,
                            const float l[3], float rotation)
{
    mu_obj_event *e = wb_event(log, MU_OBJ_CALL_SPRITE, i);
    wb_arg(e, bitmap);
    wb_vec(e, p);
    wb_float(e, scale);
    wb_vec(e, l);
    wb_float(e, rotation);
    wb_arg(e, 1);
    wb_arg(e, 0);
    wb_arg(e, 4);
}

/* CreateEffect(type, position, angle, light, sub, object, -1, 0, key, 0, 0.0, -1, 0, 0). */
static inline void q_effect(mu_obj_log *log, int32_t i, const uint8_t *o, uint32_t type, const float l[3],
                            uint32_t sub, uint16_t key)
{
    float p[3], a[3];
    wb_get(o, MU_OBJF_POSITION, p);
    wb_get(o, MU_OBJF_ANGLE, a);
    mu_obj_event *e = wb_event(log, MU_Q_KEYED_EFFECT, i);
    wb_arg(e, type);
    wb_vec(e, p);
    wb_vec(e, a);
    wb_vec(e, l);
    wb_arg(e, sub);
    wb_arg(e, key);
}
#endif
