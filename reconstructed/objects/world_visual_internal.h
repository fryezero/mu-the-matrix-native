#ifndef MU_WORLD_VISUAL_INTERNAL_H
#define MU_WORLD_VISUAL_INTERNAL_H
#include "world_visual.h"
#include <string.h>
static inline uint32_t wv_bits(float f)
{
    uint32_t u;
    memcpy(&u, &f, 4);
    return u;
}
static inline void wv_emit(mu_obj_log *l, uint32_t call, int32_t i, const uint32_t *args, int32_t n)
{
    if (!l)
        return;
    if (l->count >= l->capacity) {
        l->overflow = 1;
        return;
    }
    mu_obj_event *e = &l->events[l->count++];
    memset(e, 0, sizeof *e);
    e->call = call;
    e->object = i;
    e->count = n;
    memcpy(e->args, args, (size_t)n * 4);
}
static inline void wv_particle(const uint8_t *o, int32_t i, int32_t id, int32_t sub, const float light[3],
                               int owner, mu_obj_log *l)
{
    uint32_t a[13] = {(uint32_t)id};
    memcpy(a + 1, o + MU_OBJF_POSITION, 12);
    memcpy(a + 4, o + MU_OBJF_ANGLE, 12);
    memcpy(a + 7, light, 12);
    a[10] = (uint32_t)sub;
    a[11] = wv_bits(mu_obj_f32(o, MU_OBJF_SCALE));
    a[12] = (uint32_t)owner;
    wv_emit(l, MU_OBJ_CALL_PARTICLE, i, a, 13);
}
static inline void wv_sprite(int32_t i, int32_t id, const float pos[3], float scale, const float light[3],
                             mu_obj_log *l)
{
    uint32_t a[12] = {(uint32_t)id};
    memcpy(a + 1, pos, 12);
    a[4] = wv_bits(scale);
    memcpy(a + 5, light, 12);
    a[8] = 0;
    a[9] = 1;
    a[10] = 0;
    a[11] = 4;
    wv_emit(l, MU_OBJ_CALL_SPRITE, i, a, 12);
}
static inline void wv_body(const uint8_t *o, int32_t i, mu_obj_log *l)
{
    uint32_t a[8] = {2, 0, 0, 0, 0, 0, 0, 0xffffffffu};
    memcpy(a + 1, o + MU_OBJF_ALPHA, 4);
    memcpy(a + 2, o + MU_OBJF_BLEND_MESH, 4);
    memcpy(a + 3, o + MU_OBJF_BLEND_LIGHT, 12);
    memcpy(a + 6, o + MU_OBJF_HIDDEN_MESH, 4);
    wv_emit(l, MU_OBJ_CALL_BODY, i, a, 8);
}
static inline void wv_mesh(const uint8_t *o, int32_t i, int32_t mesh, uint32_t flags, int32_t blend,
                           float light, float u, float v, mu_obj_log *l)
{
    uint32_t a[8] = {(uint32_t)mesh,  flags,          wv_bits(mu_obj_f32(o, MU_OBJF_ALPHA)),
                     (uint32_t)blend, wv_bits(light), wv_bits(u),
                     wv_bits(v),      0xffffffffu};
    wv_emit(l, MU_OBJ_CALL_MESH, i, a, 8);
}
#endif
