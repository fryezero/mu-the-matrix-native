#ifndef MU_WORLDS_B_INTERNAL_H
#define MU_WORLDS_B_INTERNAL_H
#include "worlds_b.h"
#include <math.h>
#include <string.h>
static inline mu_obj_event *wb_event(mu_obj_log *l, uint32_t call, int32_t i)
{
    if (!l)
        return NULL;
    if (l->count >= l->capacity) {
        l->overflow = 1;
        return NULL;
    }
    mu_obj_event *e = &l->events[l->count++];
    memset(e, 0, sizeof *e);
    e->call = call;
    e->object = i;
    return e;
}
static inline void wb_arg(mu_obj_event *e, uint32_t a)
{
    if (e && e->count < MU_OBJ_EVENT_ARGS)
        e->args[e->count++] = a;
}
static inline void wb_float(mu_obj_event *e, float a)
{
    uint32_t b;
    memcpy(&b, &a, 4);
    wb_arg(e, b);
}
static inline void wb_vec(mu_obj_event *e, const float *p)
{
    for (int k = 0; k < 3; ++k)
        wb_float(e, p[k]);
}
static inline void wb_get(const uint8_t *o, uint32_t off, float *p)
{
    memcpy(p, o + off, 12);
}
static inline void wb_light(mu_obj_log *log, int32_t i, const uint8_t *o, float l, float g, float b, int32_t range)
{
    mu_obj_event *e = wb_event(log, MU_OBJ_CALL_ADD_LIGHT, i);
    wb_float(e, mu_obj_f32(o, MU_OBJF_POSITION));
    wb_float(e, mu_obj_f32(o, MU_OBJF_POSITION + 4));
    wb_float(e, l);
    wb_float(e, g);
    wb_float(e, b);
    wb_arg(e, (uint32_t)range);
}
static inline void wb_particle(mu_obj_log *log, int32_t i, const uint8_t *o, uint32_t bitmap, const float *p,
                               uint32_t sub, float scale)
{
    float a[3], l[3];
    wb_get(o, MU_OBJF_ANGLE, a);
    wb_get(o, MU_OBJF_LIGHT, l);
    mu_obj_event *e = wb_event(log, MU_OBJ_CALL_PARTICLE, i);
    wb_arg(e, bitmap);
    wb_vec(e, p);
    wb_vec(e, a);
    wb_vec(e, l);
    wb_arg(e, sub);
    wb_float(e, scale);
}
static inline void wb_sound(mu_obj_log *log, int32_t i, uint32_t id, uint32_t owner, uint32_t loop)
{
    mu_obj_event *e = wb_event(log, MU_OBJ_CALL_SOUND, i);
    wb_arg(e, id);
    wb_arg(e, owner);
    wb_arg(e, loop);
}
static inline int32_t wb_int(float v)
{
    return !isfinite(v) || v < -2147483648.0f || v >= 2147483648.0f ? INT32_MIN : (int32_t)v;
}
static inline float wb_scroll(float time, int32_t mod, float rate)
{
    return (float)((int32_t)(0u - (uint32_t)wb_int(time)) % mod) * rate;
}
#endif
