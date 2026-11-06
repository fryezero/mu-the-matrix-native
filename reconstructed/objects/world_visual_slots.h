/* The slot context and draw helpers of the class custom (0x38) and after (0x3c) renders, shared by
 * world_slots_visual.c (RENDER-WORLDS-AFTER2/3) and world_slots_more_visual.c (RENDER-WORLDS-SLOTS). */
#ifndef MU_WORLD_VISUAL_SLOTS_H
#define MU_WORLD_VISUAL_SLOTS_H
#include "world_visual_internal.h"
#include <math.h>

typedef struct slot {
    uint8_t *o, *b;
    int32_t i;
    float time;
    const mu_slot_model *model;
    mu_obj_log *l;
} slot;

static inline float A(const slot *s) { return mu_obj_f32(s->o, MU_OBJF_ALPHA); }
static inline int32_t BM(const slot *s) { return mu_obj_i32(s->o, MU_OBJF_BLEND_MESH); }
static inline float BL(const slot *s) { return mu_obj_f32(s->o, MU_OBJF_BLEND_LIGHT); }
static inline float U(const slot *s) { return mu_obj_f32(s->o, MU_OBJF_BLEND_U); }
static inline float V(const slot *s) { return mu_obj_f32(s->o, MU_OBJF_BLEND_V); }
static inline int32_t H(const slot *s) { return mu_obj_i32(s->o, MU_OBJF_HIDDEN_MESH); }

static inline void mesh(const slot *s, int32_t m, uint32_t flags, float alpha, int32_t blend, float light, float u, float v,
                 int32_t texture)
{
    const uint32_t a[8] = {(uint32_t)m, flags, wv_bits(alpha), (uint32_t)blend, wv_bits(light), wv_bits(u),
                           wv_bits(v), (uint32_t)texture};
    wv_emit(s->l, MU_OBJ_CALL_MESH, s->i, a, 8);
}
/* RenderMesh(m, flags, alpha, blend mesh, blend light, u, v, texture) with the object's own fields */
static inline void mesh_std(const slot *s, int32_t m, uint32_t flags, int32_t texture)
{
    mesh(s, m, flags, A(s), BM(s), BL(s), U(s), V(s), texture);
}
/* RenderMesh(m, flags, alpha, m, light, u, v, -1): the mesh is its own blend mesh */
static inline void mesh_self(const slot *s, int32_t m, uint32_t flags, float light, float u, float v)
{
    mesh(s, m, flags, A(s), m, light, u, v, -1);
}
static inline void body(const slot *s, uint32_t flags, int32_t blend, float light, float u, float v, int32_t hidden)
{
    const uint32_t a[8] = {flags, wv_bits(A(s)), (uint32_t)blend, wv_bits(light), wv_bits(u), wv_bits(v),
                           (uint32_t)hidden, 0xffffffffu};
    wv_emit(s->l, MU_OBJ_CALL_BODY, s->i, a, 8);
}
static inline void body_std(const slot *s, int32_t hidden)
{
    body(s, 2, BM(s), BL(s), U(s), V(s), hidden);
}
static inline void stream(const slot *s, uint8_t value)
{
    const uint32_t a[1] = {value};
    s->b[0x94] = value;
    wv_emit(s->l, MU_OBJ_CALL_MODEL_STREAM, s->i, a, 1);
}
static inline void color(const slot *s, float r, float g, float bl)
{
    const uint32_t a[3] = {wv_bits(r), wv_bits(g), wv_bits(bl)};
    mu_obj_set_f32(s->b, MU_MDL_COLOR, r);
    mu_obj_set_f32(s->b, MU_MDL_COLOR + 4, g);
    mu_obj_set_f32(s->b, MU_MDL_COLOR + 8, bl);
    wv_emit(s->l, MU_OBJ_CALL_COLOR, s->i, a, 3);
}
static inline void grey(const slot *s, float v) { color(s, 1.0f * v, 1.0f * v, 1.0f * v); }
static inline void set_hidden(const slot *s, int32_t v) { mu_obj_set_i32(s->o, MU_OBJF_HIDDEN_MESH, v); }
static inline void set_after(const slot *s) { s->o[MU_OBJF_AFTER_CHARACTER] = 1; }
static inline float frame(const slot *s) { return mu_obj_f32(s->b, 0xac); }
static inline uint16_t action(const slot *s) { return mu_obj_u16(s->b, MU_MDL_ACTION); }

static inline int32_t cvtt(float v)   /* cvttss2si */
{
    return !(v >= -2147483648.0f && v < 2147483648.0f) ? INT32_MIN : (int32_t)v;
}
/* (float)((int)WorldTime % n) * k, or with the tick negated first */
static inline float tmod(const slot *s, int32_t n, float k, int negate)
{
    int32_t t = cvtt(s->time);
    if (negate)
        t = (int32_t)(0u - (uint32_t)t);
    return (float)(t % n) * k;
}
/* 0x0185bdc4(period, phase): (±cos + 1) / 2 of the clock phase (as mount_render.c's mu_hp_wave) */
static inline float wave_at(const slot *s, float period, float phase)
{
    float a = phase * 0.017453292f;
    a = (a * 1000.0f) / period + s->time;
    const int32_t t = !(a > -2147483904.0f && a < 2147483648.0f) ? INT32_MIN : (int32_t)a;
    const int32_t m = (int32_t)(6283.1855f / period);
    const float x = (float)(t % m) * 0.001f * period;
    const float w = 3.1415927f > x ? -(float)cos((double)x) : (float)cos((double)x);
    return (w + 1.0f) * 0.5f;
}
static inline float wave(const slot *s, float period) { return wave_at(s, period, 0.0f); }
static inline float csin(float x) { return (float)sin((double)x); }   /* 0x009681bd */
/* RENDER-WORLDS-SLOTS (world_slots_more_visual.c): the class of `world` among the classes it adds (or -1), and its
 * custom (returns handled) and after slots with their own world tests. */
int mu_slots_more_class(int32_t world);
int mu_slots_more_custom(int32_t cls, const slot *s, int32_t world);
void mu_slots_more_after(int32_t cls, const slot *s, int32_t world);
int mu_slots_more_bitmap(int32_t world, int32_t index, const char **path, uint32_t *filter, uint32_t *wrap);
int32_t mu_slots_more_bitmaps(int32_t world, int32_t type, int32_t *out, int32_t room);
/* RENDER-WORLDS-SLOTS2 (world_slots2_visual.c): the classes it adds (62, 69..72, 82, 95, 100, 110 and Arca War 92
 * on 92/96/101/111), behind RENDER-WORLDS-SLOTS's in the same chain. */
int mu_slots2_class(int32_t world);
int mu_slots2_custom(int32_t cls, const slot *s, int32_t world);
void mu_slots2_after(int32_t cls, const slot *s, int32_t world);
int mu_slots2_bitmap(int32_t world, int32_t index, const char **path, uint32_t *filter, uint32_t *wrap);
int32_t mu_slots2_bitmaps(int32_t world, int32_t type, int32_t *out, int32_t room);
#endif
