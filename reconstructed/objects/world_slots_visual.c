/* RENDER-WORLDS-AFTER2: the custom render (slot 0x38) and after render (slot 0x3c) of the world classes beyond
 * Abyss of Atlans (world_abyss_visual.c). Each slot is thiscall(handler, object, model, 0) and starts with the
 * class's own world test. Logged: RenderBody 0x00966def and RenderMesh 0x00966e4a with their eight arguments,
 * the model's StreamMesh byte +0x94 (MU_OBJ_CALL_MODEL_STREAM) and body colour +0x54 (MU_OBJ_CALL_COLOR), which
 * are also written to `b` (the model fields), and a PlaySpeed store (MU_OBJ_CALL_PLAY_SPEED). The model frame the
 * slots read is b +0xac (the Animation frame argument), the action b +0xa8. Addresses per class in
 * docs/research/client-worlds-after2.md. */
#include "world_visual_internal.h"
#include <math.h>

typedef struct slot {
    uint8_t *o, *b;
    int32_t i;
    float time;
    const mu_slot_model *model;
    mu_obj_log *l;
} slot;

static float A(const slot *s) { return mu_obj_f32(s->o, MU_OBJF_ALPHA); }
static int32_t BM(const slot *s) { return mu_obj_i32(s->o, MU_OBJF_BLEND_MESH); }
static float BL(const slot *s) { return mu_obj_f32(s->o, MU_OBJF_BLEND_LIGHT); }
static float U(const slot *s) { return mu_obj_f32(s->o, MU_OBJF_BLEND_U); }
static float V(const slot *s) { return mu_obj_f32(s->o, MU_OBJF_BLEND_V); }
static int32_t H(const slot *s) { return mu_obj_i32(s->o, MU_OBJF_HIDDEN_MESH); }

static void mesh(const slot *s, int32_t m, uint32_t flags, float alpha, int32_t blend, float light, float u, float v,
                 int32_t texture)
{
    const uint32_t a[8] = {(uint32_t)m, flags, wv_bits(alpha), (uint32_t)blend, wv_bits(light), wv_bits(u),
                           wv_bits(v), (uint32_t)texture};
    wv_emit(s->l, MU_OBJ_CALL_MESH, s->i, a, 8);
}
/* RenderMesh(m, flags, alpha, blend mesh, blend light, u, v, texture) with the object's own fields */
static void mesh_std(const slot *s, int32_t m, uint32_t flags, int32_t texture)
{
    mesh(s, m, flags, A(s), BM(s), BL(s), U(s), V(s), texture);
}
/* RenderMesh(m, flags, alpha, m, light, u, v, -1): the mesh is its own blend mesh */
static void mesh_self(const slot *s, int32_t m, uint32_t flags, float light, float u, float v)
{
    mesh(s, m, flags, A(s), m, light, u, v, -1);
}
static void body(const slot *s, uint32_t flags, int32_t blend, float light, float u, float v, int32_t hidden)
{
    const uint32_t a[8] = {flags, wv_bits(A(s)), (uint32_t)blend, wv_bits(light), wv_bits(u), wv_bits(v),
                           (uint32_t)hidden, 0xffffffffu};
    wv_emit(s->l, MU_OBJ_CALL_BODY, s->i, a, 8);
}
static void body_std(const slot *s, int32_t hidden)
{
    body(s, 2, BM(s), BL(s), U(s), V(s), hidden);
}
static void stream(const slot *s, uint8_t value)
{
    const uint32_t a[1] = {value};
    s->b[0x94] = value;
    wv_emit(s->l, MU_OBJ_CALL_MODEL_STREAM, s->i, a, 1);
}
static void color(const slot *s, float r, float g, float bl)
{
    const uint32_t a[3] = {wv_bits(r), wv_bits(g), wv_bits(bl)};
    mu_obj_set_f32(s->b, MU_MDL_COLOR, r);
    mu_obj_set_f32(s->b, MU_MDL_COLOR + 4, g);
    mu_obj_set_f32(s->b, MU_MDL_COLOR + 8, bl);
    wv_emit(s->l, MU_OBJ_CALL_COLOR, s->i, a, 3);
}
static void grey(const slot *s, float v) { color(s, 1.0f * v, 1.0f * v, 1.0f * v); }
static void set_hidden(const slot *s, int32_t v) { mu_obj_set_i32(s->o, MU_OBJF_HIDDEN_MESH, v); }
static void set_after(const slot *s) { s->o[MU_OBJF_AFTER_CHARACTER] = 1; }
static float frame(const slot *s) { return mu_obj_f32(s->b, 0xac); }
static uint16_t action(const slot *s) { return mu_obj_u16(s->b, MU_MDL_ACTION); }

static int32_t cvtt(float v)   /* cvttss2si */
{
    return !(v >= -2147483648.0f && v < 2147483648.0f) ? INT32_MIN : (int32_t)v;
}
/* (float)((int)WorldTime % n) * k, or with the tick negated first */
static float tmod(const slot *s, int32_t n, float k, int negate)
{
    int32_t t = cvtt(s->time);
    if (negate)
        t = (int32_t)(0u - (uint32_t)t);
    return (float)(t % n) * k;
}
/* 0x0185bdc4(period, phase): (±cos + 1) / 2 of the clock phase (as mount_render.c's mu_hp_wave) */
static float wave_at(const slot *s, float period, float phase)
{
    float a = phase * 0.017453292f;
    a = (a * 1000.0f) / period + s->time;
    const int32_t t = !(a > -2147483904.0f && a < 2147483648.0f) ? INT32_MIN : (int32_t)a;
    const int32_t m = (int32_t)(6283.1855f / period);
    const float x = (float)(t % m) * 0.001f * period;
    const float w = 3.1415927f > x ? -(float)cos((double)x) : (float)cos((double)x);
    return (w + 1.0f) * 0.5f;
}
static float wave(const slot *s, float period) { return wave_at(s, period, 0.0f); }
static float csin(float x) { return (float)sin((double)x); }   /* 0x009681bd */

/* ---- Bloody Tarkan 140 (0x8c): custom 0x00d9a2ed, after 0x00d9ac50, world test 0x00d9bd83 ---- */
static int tarkan_custom(const slot *s)
{
    switch (mu_obj_i32(s->o, MU_OBJF_TYPE)) {
    case 0x50:
        mesh_std(s, 0, 2, -1);
        mesh_self(s, 1, 0x42, wave(s, -1.0f) * 0.5f + 0.5f, U(s), V(s));
        return 1;
    case 0x11: case 0x12:
        return 1;
    case 0x1f:
        stream(s, 3);
        mesh(s, 3, 2, A(s), BM(s), BL(s), tmod(s, 0x4b0, 0.00083f, 0), V(s), -1);
        stream(s, 0xff);
        mesh_std(s, 1, 2, -1);
        mesh_self(s, 1, 0x42, wave(s, -1.0f), U(s), V(s));
        mesh_std(s, 1, 0x44, -1);
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 2, 2, -1);
        mesh_std(s, 4, 2, -1);
        mesh_std(s, 5, 2, -1);
        return 1;
    case 0x44: case 0x46:
        mesh_std(s, 2, 2, -1);
        return 1;
    case 0x5c:
        for (int32_t m = 0; m < 5; ++m)
            mesh_std(s, m, 2, -1);
        mesh_self(s, 4, 0x42, 1.0f, U(s), V(s));
        mesh_std(s, 4, 0x44, -1);
        return 1;
    case 0x60: {
        stream(s, 0);
        const float uv = tmod(s, 50000, 5e-05f, 1);
        mesh(s, 0, 2, A(s), BM(s), BL(s), uv, uv, -1);
        stream(s, 0xff);
        return 1;
    }
    case 0x61: case 0x62:
        stream(s, 0);
        mu_obj_set_f32(s->o, MU_OBJF_BLEND_V, tmod(s, 10000, 0.0002f, 1));
        mesh_std(s, 0, 2, -1);
        stream(s, 0xff);
        return 1;
    default:
        return 0;
    }
}
static void tarkan_after(const slot *s)
{
    switch (mu_obj_i32(s->o, MU_OBJF_TYPE)) {
    case 0x11: case 0x12:
        mesh(s, 0, 0x42, A(s), 0, wave(s, -1.0f) * 0.3f + 0.7f, U(s), V(s), -1);
        break;
    case 0x44:
        mesh(s, 0, 2, A(s), 0, 1.5f, U(s), V(s), -1);
        mesh_self(s, 1, 2, (wave(s, -1.0f) * 0.5f + 0.5f) * 1.0f, U(s), V(s));
        break;
    case 0x46:
        mesh(s, 0, 2, A(s), 0, 1.0f, U(s), V(s), -1);
        mesh_self(s, 1, 2, wave(s, -1.0f) * 0.5f + 0.5f, U(s), V(s));
        break;
    default:
        break;
    }
}

/* ---- Ignis Volcano 138 (0x8a): custom 0x00e05f25, after 0x00e0709e, world test 0x00e0895c ---- */
static int ignis_custom(const slot *s)
{
    const float w = wave(s, -1.0f);
    if (s->o[MU_OBJF_AFTER_CHARACTER])
        return 1;
    switch (mu_obj_i32(s->o, MU_OBJF_TYPE)) {
    case 0x1d: case 0x1e:
        stream(s, 0);
        mesh(s, 0, 2, 1.0f, -1, BL(s), U(s), tmod(s, 100000, 0.0001f, 1), -1);
        stream(s, 1);
        mesh(s, 1, 2, 1.0f, -1, BL(s), U(s), tmod(s, 100000, 0.0001f, 1), -1);
        return 1;
    case 0x1f:
        for (int32_t m = 0; m < 5; ++m)
            mesh_std(s, m, 2, -1);
        mesh_self(s, 5, 0x42, w * 0.9f + 0.1f, U(s), V(s));
        return 1;
    case 0x20: case 0x21: case 0x22: case 0x23: case 0x24: case 0x25:
        mesh_self(s, 0, 2, w * 0.5f + 0.4f, U(s), V(s));
        return 1;
    case 0x4f:
        mesh(s, 0, 2, 1.0f, -1, BL(s), U(s), tmod(s, 100000, 0.0001f, 1), -1);
        return 1;
    case 0x5a: case 0x5b: case 0x5c: case 0x5d: case 0x90: case 0x9b: case 0xa3:
        mesh_std(s, 0, 2, -1);
        mesh_self(s, 1, 0x42, w * 0.7f + 0.3f, U(s), V(s));
        return 1;
    case 0x5f:
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 1, 2, -1);
        mesh_self(s, 2, 0x42, w * 0.9f + 0.1f, U(s), V(s));
        mesh_self(s, 3, 0x42, w * 0.7f + 0.3f, tmod(s, 100000, 0.0002f, 0), U(s));
        return 1;
    case 0x94:
        mesh(s, 0, 2, A(s), BM(s), BL(s), U(s), tmod(s, 100000, 0.0001f, 1), -1);
        return 1;
    case 0xaa:
        mesh(s, 0, 2, A(s), 0, BL(s), U(s), tmod(s, 100000, 0.0004f, 1), -1);
        return 1;
    case 0xab: case 0xae:
        for (int32_t m = 0; m < 4; ++m)
            mesh_std(s, m, 2, -1);
        mesh_self(s, 4, 2, w * 0.9f + 0.1f, U(s), tmod(s, 100000, 0.0001f, 1));
        return 1;
    case 0xac:
        if (frame(s) > 1.0f && 29.0f > frame(s))
            mesh(s, 0, 2, A(s), 0, BL(s), U(s), tmod(s, 100000, 0.0004f, 1), -1);
        return 1;
    case 0xad:
        body(s, 2, BM(s), BL(s), U(s), V(s), -1);
        mesh_self(s, 3, 2, w * 0.8f + 0.2f, U(s), V(s));
        return 1;
    case 0xb1: {
        const float w10 = wave(s, -10.0f);
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 1, 2, -1);
        if (action(s) == 0)
            mesh_self(s, 2, 2, w10 * 0.9f + 0.1f, U(s), V(s));
        else
            mesh_std(s, 2, 0x42, -1);
        return 1;
    }
    default:
        return 0;
    }
}
static void ignis_after(const slot *s)
{
    if (mu_obj_i32(s->o, MU_OBJF_TYPE) == 0x2d)
        body(s, 2, BM(s), BL(s), U(s), V(s), -1);
}

/* ---- Kanturu Underground 137 (0x89): custom 0x00e092f4, after 0x00e0ab2a, world test 0x00e0df03 ---- */
static int kanturu_custom(const slot *s)
{
    switch (mu_obj_i32(s->o, MU_OBJF_TYPE)) {
    case 1: case 2: case 0x1c: {
        const float x = csin(s->time * 0.001f);
        set_hidden(s, 1);
        body_std(s, H(s));
        mesh_self(s, 1, 2, x + 1.63f, U(s), V(s));
        return 1;
    }
    case 7:
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 1, 6, 0x7f1f);
        mesh_std(s, 1, 0x42, 0x802e);
        mesh_std(s, 1, 2, -1);
        mesh_std(s, 2, 6, 0x7f1f);
        mesh_std(s, 2, 0x42, 0x802d);
        mesh_std(s, 2, 2, -1);
        mesh_std(s, 3, 2, 0x802c);
        mesh_std(s, 3, 2, -1);
        return 1;
    case 8: case 0x5c: case 0x5d: case 0x5e: case 0x5f: case 0x60: case 0x4c: case 0x7c:
        set_after(s);
        return 1;
    case 0xa:
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 3, 2, -1);
        set_after(s);
        return 1;
    case 0xc: {
        set_hidden(s, 0);
        stream(s, 1);
        body(s, 2, BM(s), BL(s), U(s), tmod(s, 2000, 0.0005f, 1), H(s));
        stream(s, 0xff);
        const float uv = tmod(s, 2000, 0.0005f, 0);
        mesh(s, 0, 2, A(s), 0, BL(s), uv, uv, -1);
        mesh_std(s, 0, 0x84, 0x7f1f);
        return 1;
    }
    case 0x6e:
        mesh_std(s, 3, 2, -1);
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 1, 2, -1);
        mesh_std(s, 6, 2, -1);
        mesh_std(s, 6, 0xc4, 0x7f1f);
        set_after(s);
        return 1;
    case 0xd: case 0x6b: case 0x6d:
        stream(s, 1);
        body(s, 2, BM(s), BL(s), U(s), tmod(s, 2000, 0.0005f, 1), H(s));
        stream(s, 0xff);
        return 1;
    case 0xe:
        mesh_std(s, 0, 2, -1);
        mesh_self(s, 1, 2, BL(s), U(s), tmod(s, 2000, 0.0005f, 1));
        return 1;
    case 0xf: case 0x10:
        set_hidden(s, 3);
        body_std(s, H(s));
        mesh_self(s, 3, 2, BL(s), U(s), tmod(s, 2000, 0.0005f, 1));
        return 1;
    case 0x1b:
        set_hidden(s, 2);
        stream(s, 4);
        body(s, 2, BM(s), BL(s), U(s), tmod(s, 2000, 0.0005f, 1), H(s));
        set_after(s);
        return 1;
    case 0x1f: case 0x21:
        set_hidden(s, 0);
        body_std(s, H(s));
        set_after(s);
        return 1;
    case 0x23: case 0x24: case 0x3a:
        set_hidden(s, 1);
        body_std(s, H(s));
        set_after(s);
        return 1;
    case 0x26:
        mesh_self(s, 0, 2, BL(s), U(s), V(s));
        return 1;
    case 0x3b: case 0x64: case 0x65:
        set_hidden(s, 3);
        body_std(s, H(s));
        set_after(s);
        return 1;
    case 0x3e: case 0x3f:
        set_hidden(s, 2);
        body_std(s, H(s));
        set_after(s);
        return 1;
    case 0x57: case 0x58: case 0x59: case 0x5a: case 0x5b: {
        const float x = csin(s->time * 0.001f) + 1.53f;
        mesh_self(s, 0, 2, 1.0f > x ? x : 1.0f, U(s), V(s));
        return 1;
    }
    default:
        return 0;
    }
}
static void kanturu_after(const slot *s)
{
    switch (mu_obj_i32(s->o, MU_OBJF_TYPE)) {
    case 8: case 0x5c: case 0x5d: case 0x5e: case 0x5f: case 0x60:
        mesh_std(s, 0, 2, H(s));
        mesh(s, 1, 2, A(s), 1, BL(s), U(s), V(s), H(s));
        mesh_std(s, 1, 0x44, 0x7f1f);
        break;
    case 0xa:
        mesh_self(s, 1, 2, BL(s), U(s), V(s));
        mesh_self(s, 2, 2, BL(s), U(s), V(s));
        mesh_std(s, 2, 0x44, 0x7f1f);
        break;
    case 0x1b:
        stream(s, 0xff);
        mesh_std(s, 2, 0x42, -1);
        break;
    case 0x1f: case 0x21:
        mesh_self(s, 0, 2, BL(s), U(s), V(s));
        break;
    case 0x23: case 0x24: case 0x3a:
        mesh_self(s, 1, 2, BL(s), U(s), V(s));
        break;
    case 0x3b: case 0x64:
        mesh_self(s, 3, 2, BL(s), U(s), V(s));
        break;
    case 0x3e: case 0x3f:
        mesh_self(s, 2, 2, BL(s), U(s), V(s));
        break;
    case 0x4c:   /* glPushMatrix/glPopMatrix (0x012b7e53/0x012b7e65) around it change no value */
        grey(s, 0.4f);
        mesh_std(s, 0, 0x42, -1);
        mesh_std(s, 0, 0x20080, 0x7f1f);
        break;
    case 0x65:
        mesh(s, 3, 2, A(s), 2, BL(s), U(s), V(s), -1);
        break;
    case 0x6e:
        mesh_self(s, 5, 2, BL(s), U(s), tmod(s, 2000, 0.0005f, 1));
        mesh_std(s, 2, 2, -1);
        mesh_self(s, 4, 2, BL(s), U(s), V(s));
        break;
    case 0x7c:
        body_std(s, H(s));
        break;
    default:
        break;
    }
}

/* ---- Twisted Karutan 142 (0x8e): custom 0x00e677a9, after 0x00e68c6a, world test 0x00e6bd5a ---- */
static void play_speed(const slot *s, float value)
{
    const uint32_t a[3] = {(uint32_t)mu_obj_i32(s->o, MU_OBJF_TYPE), mu_obj_u16(s->o, MU_OBJF_ACTION),
                           wv_bits(value)};
    wv_emit(s->l, MU_OBJ_CALL_PLAY_SPEED, s->i, a, 3);
}
static int karutan2_custom(const slot *s)
{
    const int32_t t = mu_obj_i32(s->o, MU_OBJF_TYPE);
    switch (t) {
    case 1: body_std(s, 4); return 1;
    case 3: case 0xa7: case 0xa8: case 0xa9: case 0xaa: body_std(s, 3); return 1;
    case 0x3a:
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 3, 2, -1);
        return 1;
    case 0xb:
        mesh_std(s, 0, 2, -1);
        grey(s, wave(s, -2.5f) * 0.6f + 0.4f);
        mesh_self(s, 1, 2, BL(s), U(s), V(s));
        return 1;
    case 0x9e:
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 2, 2, -1);
        grey(s, wave(s, -2.5f) * 0.6f + 0.4f);
        mesh_self(s, 1, 2, BL(s), U(s), V(s));
        return 1;
    case 0x39: case 0x9b: case 0x9c: case 0x9d: case 0x9f: body_std(s, H(s)); return 1;
    case 0x42: mesh_std(s, 0, 2, -1); return 1;
    case 0x6b:
        play_speed(s, 5.0f);
        body_std(s, 0);
        return 1;
    case 0x77: {
        mesh_std(s, 0, 2, -1);
        const float r = mu_obj_f32(s->b, MU_MDL_COLOR), g = mu_obj_f32(s->b, MU_MDL_COLOR + 4),
                    bl = mu_obj_f32(s->b, MU_MDL_COLOR + 8);
        grey(s, wave(s, -2.5f) * 0.4f + 0.6f);
        mesh(s, 0, 2, A(s), 0, BL(s), U(s), V(s), 0x8538);
        color(s, r, g, bl);
        return 1;
    }
    case 0xc3:
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 1, 2, -1);
        mesh_std(s, 2, 2, -1);
        grey(s, wave(s, -3.0f) * 0.4f + 0.6f);
        mesh_self(s, 3, 2, BL(s), U(s), V(s));
        return 1;
    case 0xc6: body_std(s, 1); return 1;
    case 0x38: case 0x3e: case 0x71: case 0x72: case 0x73: case 0x74: case 0x76: case 0x78: case 0x79: case 0x7a:
    case 0x7b: case 0x7c: case 0x7d: case 0xa0: case 0xa1: case 0xa3: case 0xab: case 0xac: case 0xad: case 0xae:
    case 0xaf: case 0xb0: case 0xb1: case 0xb2: case 0xc4: case 0xc5:
        return 1;
    default:
        return 0;
    }
}
static void karutan2_after(const slot *s)
{
    const int32_t t = mu_obj_i32(s->o, MU_OBJF_TYPE);
    switch (t) {
    case 1: mesh_self(s, 4, 2, BL(s), U(s), V(s)); break;
    case 3: case 0xa7: case 0xa8: case 0xa9: case 0xaa: mesh_std(s, 3, 0x42, -1); break;
    case 0x36:
        mesh(s, 0, 0x42, A(s), 0, (csin(s->time * 0.002f) + 0.5f) * 0.5f + 1.0f, 0.0f, 0.0f, -1);
        break;
    case 0x37:
        stream(s, 0);
        mesh(s, 0, 0x42, A(s), BM(s), BL(s), U(s), tmod(s, 10000, 0.0001f, 0), -1);
        stream(s, 0xff);
        break;
    case 0x38: case 0xab: case 0xac: case 0xad: case 0xae: case 0xaf: case 0xb0: case 0xb1: case 0xb2:
        mesh_std(s, 0, 0x42, -1);
        mesh_std(s, 0, 0x42, -1);
        break;
    case 0x39:
        body_std(s, H(s));
        body_std(s, H(s));
        break;
    case 0x3a:
        mesh_self(s, 1, 2, BL(s), U(s), V(s));
        mesh_self(s, 2, 2, BL(s), U(s), V(s));
        break;
    case 0x3e: body_std(s, H(s)); break;
    case 0x42: mesh_self(s, 1, 2, BL(s), U(s), V(s)); break;
    case 0x78: case 0x79: case 0x7a: case 0x7b: case 0x7c: case 0x7d:
        grey(s, wave(s, -2.5f) * 0.6f + 0.4f);
        mesh_self(s, 0, 2, BL(s), U(s), V(s));
        break;
    case 0xa2:
        grey(s, wave(s, -2.5f) * 0.3f + 0.7f);
        mesh_self(s, 0, 2, BL(s), U(s), V(s));
        break;
    case 0xa3:
        grey(s, wave(s, -2.5f) * 0.3f + 0.7f);
        mesh_self(s, 0, 2, BL(s), U(s), V(s));
        mesh_self(s, 0, 2, BL(s), U(s), V(s));
        break;
    case 0xc5: mesh(s, 0, 2, A(s), -1, BL(s), U(s), V(s), -1); break;
    case 0xc6: mesh_self(s, 1, 2, BL(s), U(s), V(s)); break;
    default: break;
    }
}

/* body colour saved, set grey, one mesh, restored (the 0x00cfc922 copies around a RenderMesh) */
static void grey_mesh(const slot *s, float v, int32_t m, uint32_t flags, int32_t blend, int32_t texture)
{
    const float r = mu_obj_f32(s->b, MU_MDL_COLOR), g = mu_obj_f32(s->b, MU_MDL_COLOR + 4),
                bl = mu_obj_f32(s->b, MU_MDL_COLOR + 8);
    grey(s, v);
    if (blend == INT32_MIN)
        mesh_std(s, m, flags, texture);
    else
        mesh(s, m, flags, A(s), blend, BL(s), U(s), V(s), texture);
    color(s, r, g, bl);
}

/* ---- Old Kethotum 135 (0x87): custom 0x00e3ae5e, after 0x00e3c739, world test 0x00e3dd42; and the shared
 * cases of Burning Kethotum 136 (0x88): custom 0x00d94eef, after 0x00d97384, world test 0x00d99c0f ---- */
static int kethotum_common(const slot *s, int32_t t)
{
    switch (t) {
    case 0x15:
        return 1;
    case 0x16: case 0x29: case 0x5c: case 0x74:
        mesh_std(s, 1, 2, -1);
        mesh_std(s, 2, 2, -1);
        return 1;
    case 0x17:
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 2, 2, -1);
        grey(s, wave(s, -2.5f) * 0.4f + 0.4f);
        mesh_self(s, 1, 2, BL(s), U(s), V(s));
        return 1;
    case 0x1b:
        mesh_std(s, 0, 2, -1);
        grey(s, wave(s, -1.5f) * 0.2f + 0.7f);
        mesh(s, 1, 2, A(s), -2, BL(s), U(s), V(s), -1);
        return 1;
    case 0x5d: case 0x5e: case 0x5f: case 0x60: case 0x61: {
        mesh_std(s, 0, 2, -1);
        const float v = wave(s, -1.0f) * 0.37f + 0.46f;
        grey(s, v);
        mesh(s, 1, 2, A(s), -2, v, U(s), V(s), -1);
        return 1;
    }
    case 0x6b:
        mesh_std(s, 0, 2, -1);
        grey(s, wave(s, -2.5f) * 0.3f + 0.2f);
        mesh_self(s, 1, 2, BL(s), U(s), V(s));
        return 1;
    case 0x78: case 0x79: case 0x7a: case 0x7b:
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 1, 2, -1);
        grey_mesh(s, wave(s, -1.5f) * 0.4f + 0.4f, 2, 2, 2, -1);
        return 1;
    case 0x82: case 0x83:
        mesh_std(s, 0, 2, -1);
        grey_mesh(s, wave(s, -1.5f) * 0.5f + 0.5f, 0, 2, 0, t == 0x82 ? 0x8341 : 0x8342);
        return 1;
    case 0x84:
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 1, 2, -1);
        mesh_std(s, 4, 2, -1);
        mesh_std(s, 5, 2, -1);
        stream(s, 2);
        mesh(s, 2, 2, A(s), BM(s), BL(s), U(s), tmod(s, 100000, 0.0001f, 1), -1);
        stream(s, 3);
        mesh(s, 3, 2, A(s), BM(s), BL(s), U(s), tmod(s, 100000, 0.0004f, 1), -1);
        stream(s, 0xff);
        return 1;
    case 0x85:
        for (int32_t m = 0; m < 4; ++m)
            mesh_std(s, m, 2, -1);
        stream(s, 4);
        mesh(s, 4, 2, A(s), BM(s), BL(s), U(s), tmod(s, 100000, 0.0001f, 1), -1);
        stream(s, 0xff);
        return 1;
    default:
        return -1;
    }
}
static int kethotum1_custom(const slot *s)
{
    const int r = kethotum_common(s, mu_obj_i32(s->o, MU_OBJF_TYPE));
    return r < 0 ? 0 : r;
}
static void kethotum1_after(const slot *s)
{
    const int32_t t = mu_obj_i32(s->o, MU_OBJF_TYPE);
    switch (t) {
    case 0x12: case 0x15: case 0x89: case 0x8a:
        body_std(s, H(s));
        break;
    case 0x16: case 0x29: case 0x5c: case 0x74:
        grey_mesh(s, wave(s, -1.5f) * 0.3f + 0.7f, 0, 0x42, INT32_MIN, -1);
        if (t == 0x74)
            mesh_std(s, 3, 2, -1);
        break;
    case 0x87:
        mesh(s, 0, 2, A(s), 0, wave(s, -1.7f) * 0.55f + 0.45f, U(s), V(s), H(s));
        break;
    default:
        break;
    }
}
static int kethotum2_custom(const slot *s)
{
    const int32_t t = mu_obj_i32(s->o, MU_OBJF_TYPE);
    switch (t) {
    case 0x18:
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 1, 2, -1);
        mesh_self(s, 2, 2, BL(s), U(s), V(s));
        return 1;
    case 0x19:
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 1, 2, -1);
        mesh_std(s, 3, 2, -1);
        return 1;
    case 0x6c:
        mesh_std(s, 0, 2, -1);
        mesh_self(s, 1, 2, BL(s), U(s), V(s));
        return 1;
    case 0x86:
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 1, 2, -1);
        grey_mesh(s, wave(s, -1.5f) * 0.4f + 0.4f, 2, 2, 2, -1);
        return 1;
    case 0x87: case 0x89:
        mesh_std(s, 0, 2, -1);
        grey_mesh(s, wave(s, -1.5f) * 0.4f + 0.4f, 1, 2, 1, -1);
        return 1;
    case 0x9f:
        mesh_std(s, 0, 2, -1);
        mesh_self(s, 1, 2, BL(s), U(s), V(s));
        grey_mesh(s, wave(s, -1.5f) * 0.4f + 0.4f, 2, 2, 2, -1);
        return 1;
    case 0xb3: {
        const float k = wave(s, -2.0f) * 0.2f + 0.25f;
        color(s, mu_obj_f32(s->b, MU_MDL_COLOR) * k, mu_obj_f32(s->b, MU_MDL_COLOR + 4) * k,
              mu_obj_f32(s->b, MU_MDL_COLOR + 8) * k);
        mesh_self(s, 0, 2, BL(s), U(s), V(s));
        mesh_self(s, 1, 2, BL(s), U(s), V(s));
        return 1;
    }
    case 0xb5:
        mesh(s, 0, 2, 1.0f, BM(s), BL(s), U(s), V(s), -1);
        return 1;
    case 0xc1: case 0xc2:
        mesh_std(s, 0, 2, -1);
        mesh(s, 1, 2, A(s), 1, wave(s, -1.5f) * 0.6f + 0.3f, U(s), V(s), -1);
        return 1;
    default:
        break;
    }
    if (t >= 0x99 && t <= 0x9c) {   /* every mesh; a mesh whose texture sub record reads 1 glows */
        for (int32_t m = 0; s->model && m < s->model->mesh_count; ++m) {
            if (s->model->sub_flag[m] == 1)
                mesh(s, m, 0x42, A(s), -2, wave_at(s, -1.5f, (float)mu_obj_i32(s->o, 0x60)) * 0.7f + 0.3f, U(s),
                     V(s), -1);
            else
                mesh_std(s, m, 2, -1);
        }
        return 1;
    }
    const int r = kethotum_common(s, t);
    return r < 0 ? 0 : r;
}
static void kethotum2_after(const slot *s)
{
    const int32_t t = mu_obj_i32(s->o, MU_OBJF_TYPE);
    switch (t) {
    case 0x12: case 0x15:
        body_std(s, H(s));
        break;
    case 0x16: case 0x29: case 0x5c: case 0x74:
        grey_mesh(s, wave(s, -1.5f) * 0.3f + 0.7f, 0, 0x42, INT32_MIN, -1);
        if (t == 0x74)
            mesh_std(s, 3, 2, -1);
        break;
    case 0x18: case 0x19: case 0x6c: {
        float v = wave(s, -1.5f) * 0.6f + 0.4f;
        if (v > 0.8f)
            v = 0.8f;
        const float r = mu_obj_f32(s->b, MU_MDL_COLOR), g = mu_obj_f32(s->b, MU_MDL_COLOR + 4),
                    bl = mu_obj_f32(s->b, MU_MDL_COLOR + 8);
        grey(s, v);
        if (t == 0x6c) {
            mesh_self(s, 1, 2, BL(s), U(s), V(s));
            stream(s, 2);
            mesh_self(s, 2, 2, BL(s), tmod(s, 100000, 0.0002f, 1), V(s));
            stream(s, 0xff);
        } else {
            mesh_self(s, 2, 2, BL(s), U(s), V(s));
            if (t == 0x18) {
                stream(s, 3);
                mesh_self(s, 3, 2, BL(s), tmod(s, 100000, 0.0002f, 1), V(s));
                stream(s, 0xff);
            }
        }
        color(s, r, g, bl);
        break;
    }
    case 0xb5: {
        mesh(s, 2, 2, 0.7f, 2, BL(s), U(s), V(s), -1);
        mesh(s, 3, 2, 0.7f, 3, BL(s), U(s), V(s), -1);
        mesh(s, 4, 2, 0.7f, 4, BL(s), U(s), V(s), -1);
        const float r = mu_obj_f32(s->b, MU_MDL_COLOR), g = mu_obj_f32(s->b, MU_MDL_COLOR + 4),
                    bl = mu_obj_f32(s->b, MU_MDL_COLOR + 8);
        float k = mu_obj_f32(s->o, 0xc8);   /* comiss/jb: NaN and values below 0.7 are kept */
        if (k >= 0.7f)
            k = 0.7f;
        color(s, k * r, k * g, k * bl);
        mesh(s, 1, 2, mu_obj_f32(s->o, 0xc8), 1, BL(s), U(s), V(s), 0x8343);
        color(s, r, g, bl);
        break;
    }
    default:
        break;
    }
}

/* ---- Nixies Lake 113 (0x71): custom 0x00e347a8, after 0x00e3628c, world test 0x00e34404 ---- */
static void nixies_glass(const slot *s, int32_t m)   /* mesh, its 0x8245 reflection (flags 6), its own glow */
{
    mesh_std(s, m, 2, -1);
    mesh_std(s, m, 6, 0x8245);
    mesh_self(s, m, 0x42, BL(s), U(s), V(s));
}
static int nixies_custom(const slot *s)
{
    switch (mu_obj_i32(s->o, MU_OBJF_TYPE)) {
    case 0x14:
        mesh_std(s, 0, 2, -1);
        mesh(s, 0, 0x42, A(s), 0, BL(s), U(s), V(s), 0x8246);
        return 1;
    case 0x24:
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 2, 2, -1);
        stream(s, 1);
        mesh_std(s, 1, 2, -1);
        stream(s, 0xff);
        return 1;
    case 0x25: mesh_std(s, 1, 2, -1); return 1;
    case 0x26:
        mesh_std(s, 0, 2, -1);
        mesh_self(s, 1, 0x42, BL(s), U(s), V(s));
        return 1;
    case 0x28:
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 2, 2, -1);
        mesh_std(s, 4, 2, -1);
        mesh_std(s, 1, 0x44, 0x8245);
        mesh_self(s, 3, 0x42, wave(s, -2.0f) * 0.7f + 0.3f, U(s), V(s));
        return 1;
    case 0x29:
        mesh_std(s, 2, 2, -1);
        mesh_std(s, 5, 2, -1);
        return 1;
    case 0x2a:
        mesh_std(s, 1, 2, -1);
        mesh_std(s, 3, 2, -1);
        mesh_self(s, 2, 0x42, BL(s), U(s), V(s));
        return 1;
    case 0x2b:
        mesh_std(s, 3, 2, -1);
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 0, 6, 0x8245);
        mesh_self(s, 0, 0x42, BL(s), U(s), V(s));
        mesh_self(s, 1, 0x42, BL(s), U(s), V(s));
        mesh_self(s, 2, 0x42, BL(s), U(s), V(s));
        return 1;
    case 0x2c:
        mesh_std(s, 0, 2, -1);
        mesh(s, 0, 0x42, A(s), 0, BL(s), U(s), V(s), 0x8247);
        return 1;
    case 0x2d:
        mesh_std(s, 1, 2, -1);
        mesh(s, 1, 0x42, A(s), 1, BL(s), U(s), V(s), 0x8247);
        return 1;
    case 0x2e:
        body(s, 2, BM(s), BL(s), U(s), V(s), -1);
        mesh(s, 0, 0x42, A(s), 0, BL(s), U(s), V(s), 0x8249);
        mesh(s, 1, 0x42, A(s), 1, BL(s), U(s), V(s), 0x824a);
        return 1;
    case 0x32: case 0x33: case 0x34: case 0x66: case 0x67: case 0x68:   /* glPush/PopMatrix around the second */
        mesh_std(s, 0, 2, -1);
        mesh(s, 0, 0x20080, A(s), -2, BL(s), U(s), V(s), 0x8245);
        return 1;
    case 0x35:
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 1, 2, -1);
        mesh_self(s, 2, 0x42, BL(s), U(s), V(s));
        nixies_glass(s, 3);
        return 1;
    case 0x69:
        mesh_std(s, 1, 2, -1);
        nixies_glass(s, 2);
        nixies_glass(s, 3);
        nixies_glass(s, 4);
        return 1;
    case 0x6a: case 0x6b: case 0x7e: mesh_std(s, 0, 2, -1); return 1;
    case 0x72:
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 1, 2, -1);
        return 1;
    case 0x80:
        mesh_std(s, 1, 2, -1);
        mesh(s, 0, 0x20080, A(s), -2, BL(s), U(s), V(s), 0x8245);
        return 1;
    case 0x84:
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 3, 2, -1);
        mesh_self(s, 1, 0x42, BL(s), U(s), V(s));
        mesh_self(s, 2, 0x42, BL(s), U(s), V(s));
        return 1;
    case 0x8a:
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 1, 2, -1);
        mesh_std(s, 4, 2, -1);
        mesh_self(s, 2, 0x42, BL(s), U(s), V(s));
        mesh_self(s, 3, 0x42, BL(s), U(s), V(s));
        return 1;
    case 0x8b:
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 1, 2, -1);
        mesh_std(s, 3, 2, -1);
        return 1;
    case 0x8d:
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 1, 2, -1);
        mesh_std(s, 4, 2, -1);
        return 1;
    default:
        return 0;
    }
}
static void nixies_after(const slot *s)
{
    switch (mu_obj_i32(s->o, MU_OBJF_TYPE)) {
    case 0x14: case 0x2c: case 0x6a: case 0x7e: mesh_self(s, 1, 0x42, BL(s), U(s), V(s)); break;
    case 0x25: mesh_self(s, 0, 0x42, wave(s, -2.0f) * 0.6f + 0.4f, U(s), V(s)); break;
    case 0x26: {
        const float w1 = wave(s, -2.0f), w2 = wave_at(s, -2.0f, 180.0f);
        mesh_self(s, 2, 0x42, w1, U(s), V(s));
        mesh_self(s, 3, 0x42, w2, U(s), V(s));
        break;
    }
    case 0x27: mesh_self(s, 0, 0x42, wave(s, -2.0f) * 0.5f + 0.5f, U(s), V(s)); break;
    case 0x28: mesh_self(s, 5, 0x42, BL(s), U(s), V(s)); break;
    case 0x29:
        mesh_self(s, 0, 0x42, BL(s), U(s), V(s));
        mesh_self(s, 1, 0x42, BL(s), U(s), V(s));
        mesh_self(s, 3, 0x42, BL(s), U(s), V(s));
        mesh_self(s, 4, 0x42, BL(s), U(s), V(s));
        break;
    case 0x2a: case 0x2d: case 0x69: case 0x6c: mesh_self(s, 0, 0x42, BL(s), U(s), V(s)); break;
    case 0x35: mesh_self(s, 4, 0x42, BL(s), U(s), V(s)); break;
    case 0x6b: {
        const float w = wave(s, -2.0f) * 0.5f + 0.5f;
        mesh_self(s, 1, 0x42, w, U(s), V(s));
        mesh_self(s, 2, 0x42, w, U(s), V(s));
        break;
    }
    case 0x72: {
        const float w = wave(s, -2.0f) * 0.5f + 0.5f;
        mesh_self(s, 2, 0x42, w, U(s), V(s));
        mesh_self(s, 3, 0x42, w, U(s), V(s));
        mesh_self(s, 4, 0x42, w, U(s), V(s));
        break;
    }
    case 0x8b:
        mesh_self(s, 2, 0x42, BL(s), U(s), V(s));
        mesh_self(s, 4, 0x42, BL(s), U(s), V(s));
        break;
    case 0x8d:
        mesh_self(s, 2, 0x42, BL(s), U(s), V(s));
        mesh_self(s, 3, 0x42, BL(s), U(s), V(s));
        break;
    default:
        break;
    }
}

/* ---- Acheron 91 (0x5b): custom 0x00d6c427, after 0x00d6d3d7, world test 0x00d6a614 (0x5b or 0x5c). The custom
 * render has no null test. Types 0x87e..0x888 (not 0x880) go to 0x00d73cd7; the world manager calls slot 0x38
 * only for types 0..300, so objects never reach it (not reconstructed: answered 0 here). ---- */
static float fabs_sin(const slot *s, double k)   /* fabs 0x01983660 of sin((float)(WorldTime * k)) */
{
    const float x = csin((float)((double)s->time * k));
    return (float)fabs((double)x);
}
static void mesh_dark(const slot *s, int32_t m)   /* RenderMesh(m, 2, alpha, -2, ...) */
{
    mesh(s, m, 2, A(s), -2, BL(s), U(s), V(s), -1);
}
static int acheron_custom(const slot *s)
{
    switch (mu_obj_i32(s->o, MU_OBJF_TYPE)) {
    case 7: case 8: case 0x11: case 0x16: case 0x17: case 0x18: case 0x19: case 0x1a: case 0x1c: case 0x1e:
    case 0x1f: case 0x20: case 0x21: case 0x24: case 0x2f: case 0x3d: case 0x3e: case 0x47: case 0x48: case 0x4d:
    case 0x4e: case 0x4f: case 0x5a: case 0x5b: case 0x5d: case 0x65: case 0x66:
        break;
    case 9: case 0xe: case 0x1b: case 0x33: case 0x3b: case 0x57: case 0x59: case 0x5c: case 0x64: case 0x6b:
    case 0x6c: case 0x6d:
        mesh_std(s, 0, 2, -1);
        break;
    case 0xf: case 0x3c:
        mesh_std(s, 1, 2, -1);
        break;
    case 0x10: case 0x34:
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 1, 2, -1);
        break;
    case 0x41:
        mesh_std(s, 2, 2, -1);
        break;
    case 0x42:
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 2, 2, -1);
        break;
    case 0x4c: case 0x58:
        mesh_std(s, 2, 2, -1);
        mesh_std(s, 1, 2, -1);
        break;
    case 0x6e:
        mesh_std(s, 0, 2, -1);
        body_std(s, H(s));
        break;
    case 0x30: {
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 1, 2, 0x8150);
        const float v = fabs_sin(s, 0.0014) * 1.0f + 0.6f;
        mesh(s, 1, 2, A(s), -2, v, U(s), V(s), 0x814f);
        mesh(s, 1, 2, A(s), -2, v, U(s), V(s), 0x814f);
        mesh_std(s, 1, 2, -1);
        return 1;
    }
    case 0x44:
        mesh_std(s, 0, 2, 0x8152);
        stream(s, 0);
        mesh(s, 0, 2, A(s), -2, BL(s), U(s), tmod(s, 4000, 0.00025f, 0), 0x8151);
        stream(s, 0xff);
        mesh_std(s, 0, 2, -1);
        return 1;
    default:
        return 0;
    }
    set_after(s);
    return 1;
}
static void acheron_after(const slot *s)
{
    switch (mu_obj_i32(s->o, MU_OBJF_TYPE)) {
    case 7: case 8: case 0x16: case 0x17: case 0x18: case 0x19: case 0x1a: case 0x1e: case 0x1f: case 0x20:
    case 0x21: case 0x24: case 0x2f: case 0x3d: case 0x3e: case 0x47: case 0x48: case 0x4e: case 0x5a: case 0x5b:
    case 0x5d: case 0x65: case 0x66:
        body_std(s, H(s));
        break;
    case 9:
        stream(s, 2);
        mesh(s, 2, 2, A(s), -2, BL(s), U(s), tmod(s, 10000, 0.00032f, 0), -1);
        stream(s, 0xff);
        mesh_dark(s, 1);
        break;
    case 0xe: case 0x33: case 0x57: case 0x59: case 0x64: mesh_dark(s, 1); break;
    case 0xf:
        stream(s, 0);
        mesh(s, 0, 2, A(s), -2, BL(s), U(s), tmod(s, 10000, 0.0001f, 0), -1);
        stream(s, 0xff);
        break;
    case 0x10: case 0x34: mesh_dark(s, 2); break;
    case 0x11:   /* glPush/PopMatrix around the second */
        mesh_dark(s, 0);
        mesh(s, 0, 0x20080, 0.35f, 0, BL(s), U(s), V(s), 0x7f1f);
        break;
    case 0x1b: case 0x5c: {
        const float x = csin(s->time * 0.001f);
        stream(s, 2);
        mesh(s, 2, 2, A(s), -2, BL(s), x * 0.18f, tmod(s, 10000, 0.0001f, 0), -1);
        stream(s, 2);
        mesh(s, 1, 2, A(s), -2, x * 0.8f + 1.0f, U(s), V(s), -1);
        stream(s, 0xff);
        break;
    }
    case 0x1c:
        body(s, 2, BM(s), fabs_sin(s, 0.0005) * 0.3f + 0.5f, U(s), V(s), H(s));
        break;
    case 0x3b:
        mesh_dark(s, 2);
        mesh_dark(s, 1);
        break;
    case 0x3c: case 0x4d: case 0x58: mesh_dark(s, 0); break;
    case 0x41:
        mesh(s, 2, 0x240, A(s), -2, BL(s), U(s), V(s), -1);
        mesh(s, 0, 0x44, A(s), -2, BL(s), U(s), V(s), -1);
        stream(s, 1);
        mesh(s, 1, 2, A(s), -2, BL(s), U(s), tmod(s, 10000, 0.001f, 0), -1);
        stream(s, 0xff);
        break;
    case 0x42:
        mesh(s, 1, 0x20080, A(s), -2, BL(s), U(s), V(s), 0x7f1f);
        break;
    case 0x4c:
        mesh_dark(s, 0);
        stream(s, 3);
        mesh(s, 3, 2, A(s), -2, BL(s), U(s), tmod(s, 10000, 0.0003f, 0), -1);
        stream(s, 0xff);
        break;
    case 0x4f:
        mesh(s, 0, 2, A(s), -2, 1.0f, U(s), V(s), -1);
        mesh(s, 0, 0x20080, 0.7f, 0, BL(s), U(s), V(s), 0x7f1f);
        break;
    case 0x6b: case 0x6c: case 0x6d:
        mesh(s, 1, 2, A(s), -2, fabs_sin(s, 0.001) * 0.99f, U(s), V(s), -1);
        break;
    case 0x6e:
        mesh_dark(s, 2);
        mesh(s, 1, 0x20080, A(s), -2, BL(s), U(s), V(s), 0x7f1f);
        break;
    default:
        break;
    }
}

/* ---- the pre-move slot 0x74 (the world manager 0x00ea2c2b calls it before the registry tick and slot 0x30).
 * Imperial Guardian 69 0x00dd2fae; 70/71/72 0x00dd886b/0x00dde51d/0x00de5441 call the world-69 handler's slot
 * (0x00dd8a3c(0x45)), so `state` is that handler's +0x14; Loren Market 79 0x00e6dd0a (its world test result is
 * discarded); Karutan 80/81 0x00e189af; Swamp of Darkness 122 0x00e5e1a4. Logged: PlayBuffer 0x00a6ac96
 * (id, 1 when the object is passed, 0). ---- */
static void play(mu_obj_log *l, int32_t i, uint32_t id, uint32_t owner)
{
    const uint32_t a[3] = {id, owner, 0};
    wv_emit(l, MU_OBJ_CALL_SOUND, i, a, 3);
}
int mu_class_premove(int32_t cls, const uint8_t *o, int32_t i, int32_t world, int32_t state, mu_obj_rand_fn rnd,
                     void *c, mu_obj_log *l)
{
    switch (cls) {
    case 69: case 70: case 71: case 72:
        if (!o || world < 0x45 || world > 0x4a)
            return 1;
        if (world >= 0x48)
            play(l, i, 0x38f, 0);
        else if (state >= 1 && state <= 3)
            play(l, i, (uint32_t)(0x38b + state), 0);
        return 1;
    case 79:
        return 1;
    case 80: case 81: {
        const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
        if (t == 0x3a || t == 0x42)
            play(l, i, 0x3db, 1);
        return 1;
    }
    case 122: {
        if (!o)
            return 1;
        switch (mu_obj_i32(o, MU_OBJF_TYPE)) {
        case 0x1a:
            if (rnd(c) % 50 == 0)
                play(l, i, 0x4d4, 0);
            break;
        case 0x83: case 0x84:
            if (mu_obj_u16(o, MU_OBJF_ACTION) == 1)
                play(l, i, 0x4d2, 0);
            break;
        case 0x85:
            if (rnd(c) % 150 == 0)
                play(l, i, 0x4d2, 0);
            break;
        case 0xa1:
            play(l, i, 0x4d3, 0);
            break;
        case 0xa8: {   /* 0x00e5ea60: tile x 0xa3..0xca and y 0..0x27 keep it quiet */
            const int32_t x = cvtt(mu_obj_f32(o, MU_OBJF_POSITION) / 100.0f);
            const int32_t y = cvtt(mu_obj_f32(o, MU_OBJF_POSITION + 4) / 100.0f);
            if (!(x >= 0xa3 && x <= 0xca && y >= 0 && y <= 0x27))
                play(l, i, 0x4d5, 0);
            break;
        }
        default:
            break;
        }
        return 1;
    }
    default:
        return 0;
    }
}

/* ---- bitmaps the slots bind to a model mesh (RenderMesh's texture argument) ----
 * LoadBitmap 0x0185baac(name, index, filter, wrap, 1, 0) under Data\: the class loader (slot 0x24) for the
 * world's own files, the startup loaders for the shared ones (sites in client-worlds-after2.md). Chrome01 0x7f1f
 * is one of the model texture specials (mu_texture_specials) and needs no entry. */
static const struct {
    int32_t world, index;   /* world -1: every world */
    const char *path;
    uint32_t filter, wrap;
} bitmaps[] = {
    {-1, 0x802c, "Npc\\khs_kan2gate001.jpg", 0x2601, 0x2900},
    {-1, 0x802d, "Npc\\khs_kan2gate003.jpg", 0x2601, 0x2900},
    {-1, 0x802e, "Npc\\khs_kan2gate004.jpg", 0x2601, 0x2900},
    {-1, 0x8245, "Effect\\Chrome09.jpg", 0x2601, 0x2901},
    {-1, 0x8246, "Object114\\hstreeuniversalD01_R.jpg", 0x2601, 0x2900},
    {-1, 0x8247, "Object114\\hswindattributeA02_R.jpg", 0x2601, 0x2900},
    {-1, 0x8249, "Object114\\hswindattributeC01_R.jpg", 0x2601, 0x2900},
    {-1, 0x824a, "Object114\\hswindattributeC02_R.jpg", 0x2601, 0x2900},
    {-1, 0x814f, "Object92\\cuttree01A_R.jpg", 0x2601, 0x2900},
    {-1, 0x8150, "Object92\\cuttree01A_base.jpg", 0x2601, 0x2900},
    {-1, 0x8151, "Object92\\jung03_R.jpg", 0x2601, 0x2901},
    {-1, 0x8152, "Object92\\jung03_base.jpg", 0x2601, 0x2901},
    {128, 0x82de, "Object131\\HSCrystalPlantB_R.jpg", 0x2601, 0x2901},
    {128, 0x82df, "Object131\\so_light01.jpg", 0x2601, 0x2901},
    {129, 0x82de, "Object131\\HSCrystalPlantB_R.jpg", 0x2601, 0x2901},
    {129, 0x82df, "Object131\\so_light01.jpg", 0x2601, 0x2901},
    {130, 0x82de, "Object131\\HSCrystalPlantB_R.jpg", 0x2601, 0x2901},
    {130, 0x82df, "Object131\\so_light01.jpg", 0x2601, 0x2901},
    {135, 0x8341, "Object136\\hsBurntwoodA01_R.jpg", 0x2601, 0x2900},
    {135, 0x8342, "Object136\\hsBurntwoodA02_R.jpg", 0x2601, 0x2900},
    {136, 0x8341, "Object137\\hsBurntwoodA01_R.jpg", 0x2601, 0x2900},
    {136, 0x8342, "Object137\\hsBurntwoodA02_R.jpg", 0x2601, 0x2900},
    {136, 0x8343, "Object137\\hsvallistaA02_R.jpg", 0x2601, 0x2900},
    {142, 0x8538, "Object143\\solived01_R.jpg", 0x2601, 0x2901},
};
int mu_world_slot_bitmap(int32_t world, int32_t index, const char **path, uint32_t *filter, uint32_t *wrap)
{
    for (size_t k = 0; k < sizeof bitmaps / sizeof bitmaps[0]; ++k)
        if (bitmaps[k].index == index && (bitmaps[k].world == world || bitmaps[k].world < 0)) {
            *path = bitmaps[k].path;
            *filter = bitmaps[k].filter;
            *wrap = bitmaps[k].wrap;
            return 1;
        }
    return 0;
}
/* The bitmaps the custom and after slots of `world` name for objects of `type` (Chrome01 0x7f1f included). */
int32_t mu_world_slot_bitmaps(int32_t world, int32_t type, int32_t out[4])
{
    static const struct {
        int32_t world, type, list[4];
    } uses[] = {
        {91, 0x30, {0x8150, 0x814f}}, {91, 0x44, {0x8152, 0x8151}}, {91, 0x11, {0x7f1f}}, {91, 0x42, {0x7f1f}},
        {91, 0x4f, {0x7f1f}}, {91, 0x6e, {0x7f1f}},
        {113, 0x14, {0x8246}}, {113, 0x28, {0x8245}}, {113, 0x2b, {0x8245}}, {113, 0x32, {0x8245}},
        {113, 0x33, {0x8245}}, {113, 0x34, {0x8245}}, {113, 0x35, {0x8245}}, {113, 0x66, {0x8245}},
        {113, 0x67, {0x8245}}, {113, 0x68, {0x8245}}, {113, 0x69, {0x8245}}, {113, 0x80, {0x8245}},
        {113, 0x2c, {0x8247}}, {113, 0x2d, {0x8247}}, {113, 0x2e, {0x8249, 0x824a}},
        {128, 0x29, {0x82de}}, {128, 0x34, {0x82df}}, {129, 0x29, {0x82de}}, {129, 0x34, {0x82df}},
        {130, 0x29, {0x82de}}, {130, 0x34, {0x82df}},
        {135, 0x82, {0x8341}}, {135, 0x83, {0x8342}}, {136, 0x82, {0x8341}}, {136, 0x83, {0x8342}},
        {136, 0xb5, {0x8343}},
        {137, 7, {0x7f1f, 0x802e, 0x802d, 0x802c}}, {137, 0xc, {0x7f1f}}, {137, 0x6e, {0x7f1f}},
        {137, 8, {0x7f1f}}, {137, 0x5c, {0x7f1f}}, {137, 0x5d, {0x7f1f}}, {137, 0x5e, {0x7f1f}},
        {137, 0x5f, {0x7f1f}}, {137, 0x60, {0x7f1f}}, {137, 0xa, {0x7f1f}}, {137, 0x4c, {0x7f1f}},
        {142, 0x77, {0x8538}},
    };
    int32_t n = 0;
    for (size_t k = 0; k < sizeof uses / sizeof uses[0]; ++k)
        if (uses[k].world == world && uses[k].type == type)
            for (int j = 0; j < 4 && uses[k].list[j]; ++j)
                out[n++] = uses[k].list[j];
    return n;
}

/* ---- dispatch ---- */
typedef int (*custom_fn)(const slot *);
typedef void (*after_fn)(const slot *);
static const struct {
    int32_t world;
    custom_fn custom;
    after_fn after;
} classes[] = {
    {91, acheron_custom, acheron_after}, {113, nixies_custom, nixies_after}, {135, kethotum1_custom, kethotum1_after}, {136, kethotum2_custom, kethotum2_after},
    {137, kanturu_custom, kanturu_after}, {138, ignis_custom, ignis_after},
    {140, tarkan_custom, tarkan_after}, {142, karutan2_custom, karutan2_after},
};
static int find(int32_t cls)
{
    for (int k = 0; k < (int)(sizeof classes / sizeof classes[0]); ++k)
        if (classes[k].world == cls)
            return k;
    return -1;
}
int mu_class_slots(int32_t world)
{
    return find(world) >= 0;
}
static int world_test(int32_t cls, int32_t world)
{
    return world == cls || (cls == 91 && world == 92);   /* 0x00d6a614 */
}
int mu_class_custom(int32_t cls, uint8_t *o, uint8_t *b, int32_t i, int32_t world, float time,
                    const mu_slot_model *model, mu_obj_log *l)
{
    const int k = find(cls);
    if (k < 0 || !world_test(cls, world) || !o || !b)
        return 0;
    const slot s = {o, b, i, time, model, l};
    return classes[k].custom(&s);
}
void mu_class_after(int32_t cls, uint8_t *o, uint8_t *b, int32_t i, int32_t world, float time,
                    const mu_slot_model *model, mu_obj_log *l)
{
    const int k = find(cls);
    if (k < 0 || !world_test(cls, world) || !o || !b)
        return;
    const slot s = {o, b, i, time, model, l};
    classes[k].after(&s);
}
