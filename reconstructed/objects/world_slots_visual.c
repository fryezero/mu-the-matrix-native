/* RENDER-WORLDS-AFTER2: the custom render (slot 0x38) and after render (slot 0x3c) of the world classes beyond
 * Abyss of Atlans (world_abyss_visual.c). Each slot is thiscall(handler, object, model, 0) and starts with the
 * class's own world test. Logged: RenderBody 0x00966def and RenderMesh 0x00966e4a with their eight arguments,
 * the model's StreamMesh byte +0x94 (MU_OBJ_CALL_MODEL_STREAM) and body colour +0x54 (MU_OBJ_CALL_COLOR), which
 * are also written to `b` (the model fields), and a PlaySpeed store (MU_OBJ_CALL_PLAY_SPEED). The model frame the
 * slots read is b +0xac (the Animation frame argument), the action b +0xa8. Addresses per class in
 * docs/research/client-worlds-after2.md. */
#include "world_visual_internal.h"
#include <math.h>
#include <stdio.h>

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

/* ---- Scorched Canyon 131 (0x83): custom 0x00e43842, after 0x00e43fab, world test 0x00e45d40 ---- */
/* every mesh; a mesh whose texture sub record reads 1 glows with `light`, the others are plain */
static void glow_meshes(const slot *s, float period, float phase, float scale, float bias)
{
    for (int32_t m = 0; s->model && m < s->model->mesh_count; ++m)
        if (s->model->sub_flag[m] == 1)
            mesh(s, m, 0x42, A(s), -2, wave_at(s, period, phase) * scale + bias, U(s), V(s), -1);
        else
            mesh_std(s, m, 2, -1);
}
/* the clock phase of the wave (period -1.5, phase in radians): -(x) * 0.1 */
static float scorched_scroll(const slot *s, float radians)
{
    const int32_t t = cvtt(radians * 1000.0f / -1.5f + s->time);
    return -((float)(t % -4188) * 0.001f * -1.5f) * 0.1f;
}
static int scorched_custom(const slot *s)
{
    if (s->o[MU_OBJF_AFTER_CHARACTER] == 1)
        return 1;
    const int32_t t = mu_obj_i32(s->o, MU_OBJF_TYPE);
    switch (t) {
    case 0x1d: case 0x2d: case 0x59:
        glow_meshes(s, -1.5f, 0.0f, 0.8f, 0.2f);
        return 1;
    case 0x9d: case 0xb1: case 0xb2: case 0xb3: case 0xb4: case 0xb5: case 0xb6: case 0xb7: case 0xb8: case 0xb9:
    case 0xbb: case 0xbc: case 0xbd: case 0xbe: case 0xbf: case 0xc0: case 0xc1: case 0xc2: case 0xc3: case 0xc4:
    case 0xc5: case 0xc6:
        glow_meshes(s, -0.7f, 0.0f, 0.3f, 0.2f);
        return 1;
    case 0x88: case 0x8a: case 0x8b: case 0x8c: case 0x8e: case 0x8f: case 0x93: case 0x94: case 0x95:
        glow_meshes(s, -1.5f, (float)mu_obj_i32(s->o, 0x60), 0.7f, 0.3f);
        return 1;
    case 0x10: {
        const float w = wave_at(s, -1.5f, 180.0f);
        stream(s, 0);
        mesh(s, 0, 0x42, A(s), -2, w, scorched_scroll(s, 3.14159274f), V(s), -1);
        return 1;
    }
    case 0x11: {
        const float w = wave(s, -1.5f);
        stream(s, 0);
        mesh(s, 0, 0x42, A(s), -2, w, scorched_scroll(s, 0.0f), V(s), -1);
        return 1;
    }
    default:
        return 0;
    }
}
static void scorched_after(const slot *s)
{
    const int32_t t = mu_obj_i32(s->o, MU_OBJF_TYPE);
    switch (t) {
    case 0x5a:
        mesh_std(s, 0, 2, -1);
        mesh(s, 1, 0x42, A(s), -2, wave(s, -1.5f) * 0.8f + 0.2f, U(s), V(s), -1);
        stream(s, 2);
        mesh(s, 2, 2, A(s), BM(s), BL(s), U(s), tmod(s, 4000, -0.00025f, 0), -1);
        break;
    case 0x6a:
        mesh(s, 0, 0x42, A(s), -2, wave_at(s, -1.5f, (float)mu_obj_i32(s->o, 0x60)) * 0.6f + 0.4f, U(s), V(s), -1);
        break;
    case 0x28: case 0x4f: case 0xa8: case 0xb2: case 0xb3: case 0xb5: case 0xba: case 0xc5: case 0xc7:
        if ((t >= 0xb1 && t <= 0x12b) || t == 0xa8)
            glow_meshes(s, -0.7f, 0.0f, 0.3f, 0.2f);
        else
            glow_meshes(s, -1.5f, 0.0f, 0.8f, 0.2f);
        break;
    default:
        break;
    }
}

/* ---- Red Smoke Icarus 132 (0x84): custom 0x00e00d4c, after 0x00e010b6, world test 0x00e0558b ---- */
static int icarus2_custom(const slot *s)
{
    if (s->o[MU_OBJF_AFTER_CHARACTER])
        return 1;
    switch (mu_obj_i32(s->o, MU_OBJF_TYPE)) {
    case 0x1e:
        stream(s, 0);
        mesh(s, 0, 2, A(s), BM(s), BL(s), tmod(s, 200000, 5e-06f, 1) + U(s), V(s), -1);
        stream(s, 0xff);
        return 1;
    case 0x7c4:   /* above the world manager's 0..300: never reached from an object */
        color(s, 0.02f, 0.05f, 0.15f);
        return 1;
    default:
        return 0;
    }
}
static void icarus2_after(const slot *s)
{
    const int32_t t = mu_obj_i32(s->o, MU_OBJF_TYPE);
    if (t == 0x1c) {
        mesh_self(s, 0, 2, BL(s), U(s), V(s));
        mesh_self(s, 1, 2, BL(s), U(s), V(s));
        mesh_self(s, 2, 2, wave(s, -3.0f) * 0.6f + 0.4f, U(s), V(s));
    } else if (t >= 6 && t <= 0x3c && t != 0xb && !(t >= 0x17 && t <= 0x1b) && t != 0x1e &&
               !(t >= 0x2c && t <= 0x2e)) {
        body(s, 2, BM(s), BL(s), U(s), V(s), -1);
    }
}

/* ---- Gray Aida 134 (0x86): custom 0x00d84d0e, after 0x00d868f7, world test 0x00d8b139 ---- */
static int aida_custom(const slot *s)
{
    switch (mu_obj_i32(s->o, MU_OBJF_TYPE)) {
    case 0: return 1;
    case 0x4f: case 0x50: case 0x51: case 0x52: case 0x53: mesh_std(s, 1, 2, -1); return 1;
    default: return 0;
    }
}
static void aida_after(const slot *s)
{
    switch (mu_obj_i32(s->o, MU_OBJF_TYPE)) {
    case 0x3b: case 0x3e: case 0x5c:
        break;
    case 0x29:
        body_std(s, H(s));
        grey(s, 0.52f);
        stream(s, 0);
        mesh_std(s, 0, 0x42, -1);
        stream(s, 0xff);
        break;
    case 0x4f: case 0x50: case 0x51: case 0x52: case 0x53:
        mesh_std(s, 0, 0x42, -1);
        mesh_std(s, 2, 0x42, -1);
        break;
    default:   /* 0x19 and every other selected type */
        body_std(s, H(s));
        break;
    }
}

/* ---- Old Kethotum's neighbour 139 (0x8b): custom 0x00d9c19a answers no, after 0x00d9c1b4 draws nothing ---- */
static int none_custom(const slot *s) { (void)s; return 0; }
static void none_after(const slot *s) { (void)s; }

/* ==== RENDER-WORLDS-AFTER3: the custom/after slots of 133, 141, 143, 144 and 145 (client-worlds-after3.md).
 * Types above 300 (133's 0x199..0x19e, 141's 0x40e) are never passed by the world manager and are left. ==== */
static void body_t(const slot *s, uint32_t flags, int32_t blend, float light, float u, float v, int32_t hidden,
                   int32_t texture)
{
    const uint32_t a[8] = {flags, wv_bits(A(s)), (uint32_t)blend, wv_bits(light), wv_bits(u), wv_bits(v),
                           (uint32_t)hidden, (uint32_t)texture};
    wv_emit(s->l, MU_OBJ_CALL_BODY, s->i, a, 8);
}
/* RenderMesh(m, flags, alpha, m, light, u, v, texture): the mesh is its own blend mesh */
static void mesh_own(const slot *s, int32_t m, uint32_t flags, float light, int32_t texture)
{
    mesh(s, m, flags, A(s), m, light, U(s), V(s), texture);
}
typedef struct saved_color {
    float c[3];
} saved_color;
static saved_color save_color(const slot *s)
{
    const saved_color k = {{mu_obj_f32(s->b, MU_MDL_COLOR), mu_obj_f32(s->b, MU_MDL_COLOR + 4),
                            mu_obj_f32(s->b, MU_MDL_COLOR + 8)}};
    return k;
}
static void restore_color(const slot *s, saved_color k) { color(s, k.c[0], k.c[1], k.c[2]); }
static void set_light(const slot *s, float v)   /* OBJECT +0xec, the object light */
{
    for (uint32_t q = 0; q < 3; ++q)
        mu_obj_set_f32(s->o, MU_OBJF_LIGHT + 4 * q, v);
}
/* 0x8320/0x8348/0x838a/0x848e/0x8589 + (int)(WorldTime * 0.015) % 32: the class's 32 water bitmaps */
static int32_t water(const slot *s, int32_t base) { return base + cvtt(s->time * 0.015f) % 32; }
/* the scrolling water body of 133 (types 6, 0xaa) and 143 (type 0): StreamMesh 0, then the whole body */
static void water_body(const slot *s, int32_t n, float k)
{
    const float w = wave(s, -1.5f);
    set_light(s, 0.2f);
    stream(s, 0);
    const float t = tmod(s, n, k, 0);
    body_t(s, 0x42, BM(s), BL(s), -t, w * 0.011f - t, -1, -1);
    stream(s, 0xff);
}

/* ---- Temple of Arnil 133 (0x85): custom 0x00d80cea, after 0x00d81c49, world test 0x00d83ada ---- */
static int arnil_custom(const slot *s)
{
    switch (mu_obj_i32(s->o, MU_OBJF_TYPE)) {
    case 6: case 0xe: case 0x7b: case 0x80: case 0x8f: case 0xaa:
        return 1;
    case 0x84: case 0x86:
        mesh_std(s, 0, 2, -1);
        return 1;
    case 0x1b: {
        const float w = wave(s, -1.5f) * 0.4f + 0.2f;
        mesh_std(s, 0, 2, -1);
        grey(s, w);
        mesh_std(s, 1, 0x42, -1);
        return 1;
    }
    case 0x4d: case 0x4e: case 0x4f: case 0x50: case 0x51: case 0x67: {
        const float w = wave(s, -1.5f) * (mu_obj_i32(s->o, MU_OBJF_TYPE) == 0x67 ? 0.4f : 0.8f) + 0.2f;
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 1, 2, -1);
        grey(s, w);
        mesh(s, 2, 0x42, A(s), BM(s), w, U(s), V(s), -1);
        return 1;
    }
    case 0x60: case 0x62: case 0x63: case 0x64: case 0x65: case 0x66: {
        const float w = wave(s, -1.5f) * 0.8f + 0.2f;
        mesh_std(s, 0, 2, -1);
        grey(s, w);
        mesh(s, 1, 0x42, A(s), BM(s), w, U(s), V(s), -1);
        return 1;
    }
    case 0x91: case 0x94: {   /* StreamMesh k for mesh k; 0x94 stops after mesh 3 and leaves it set */
        const float t = tmod(s, 0x4b0, 0.00083f, 0);
        const int last = mu_obj_i32(s->o, MU_OBJF_TYPE) == 0x91 ? 5 : 3;
        mesh_std(s, 0, 2, -1);
        for (int32_t m = 1; m <= last; ++m) {
            stream(s, (uint8_t)m);
            if (m == 2 || m == 4)
                mesh(s, m, 2, A(s), BM(s), BL(s), -t * (m == 2 ? 4.0f : 2.0f), V(s), -1);
            else
                mesh(s, m, 2, A(s), BM(s), BL(s), U(s), t * (m == 1 ? 2.0f : 1.0f), -1);
        }
        if (last == 5)
            stream(s, 0xff);
        return 1;
    }
    case 0x92: {
        const float t = tmod(s, 0x4b0, 0.00083f, 0);
        stream(s, 0);
        mesh(s, 0, 2, A(s), BM(s), BL(s), U(s), t, -1);
        return 1;
    }
    default:
        return 0;
    }
}
static void arnil_after(const slot *s)
{
    switch (mu_obj_i32(s->o, MU_OBJF_TYPE)) {
    case 6: case 0xaa:
        water_body(s, 1000000, 1e-05f);
        break;
    case 0x80: {
        const float w = wave(s, -1.5f) * 0.7f + 0.3f;
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 1, 0x42, -1);
        mesh_std(s, 3, 0x42, -1);
        mesh_std(s, 4, 0x42, -1);
        grey(s, w);
        mesh(s, 2, 0x42, A(s), BM(s), w, U(s), V(s), -1);
        break;
    }
    case 0x84: case 0x86:
        mesh(s, 1, 0x42, A(s), 1, BL(s), U(s), V(s), -1);
        break;
    case 0x8f:
        body_t(s, 2, BM(s), BL(s), U(s), V(s), H(s), water(s, 0x8320));
        break;
    default:
        body_std(s, H(s));
        break;
    }
}

/* ---- Swamp of Destruction 144 (0x90): custom 0x00e46e94, after 0x00e48f1c, world test 0x00e4bb8d ---- */
static int swamp_custom(const slot *s)
{
    const int32_t t = mu_obj_i32(s->o, MU_OBJF_TYPE);
    switch (t) {
    case 3: case 4: case 6: case 0xb:
        body(s, 2, BM(s), BL(s), U(s), V(s), -1);
        mesh(s, 0, 2, A(s), 0, wave(s, -1.5f) * 0.5f + 0.5f, U(s), V(s),
             t == 3 ? 0x8344 : t == 4 ? 0x8345 : t == 6 ? 0x8346 : 0x8347);
        return 1;
    case 0xd:
        mesh(s, 0, 2, A(s), -1, -1.0f, U(s), V(s), -1);
        mesh(s, 1, 2, A(s), 1, wave(s, -4.0f) * 0.5f + 0.7f, U(s), V(s), -1);
        return 1;
    case 0x20: case 0x40: case 0x4c:
        return 1;
    case 0x7c: case 0x7d: case 0x7e: case 0x7f: case 0x80: {
        const float w = wave(s, -1.0f) * 0.6f + 0.4f;
        mesh(s, 0, 2, A(s), -1, w, U(s), V(s), -1);
        mesh(s, 1, 2, A(s), -1, w, U(s), V(s), -1);
        mesh(s, 2, 2, A(s), 2, w, U(s), V(s), -1);
        mesh(s, 3, 2, A(s), 3, w, tmod(s, 50000, 0.0002f, 0), V(s), -1);
        return 1;
    }
    case 0x86: case 0x87:   /* the colour copies around mesh 1 change nothing */
        mesh_std(s, 0, 2, -1);
        mesh(s, 1, 2, A(s), 1, wave(s, -1.5f) * 0.6f + 0.3f, U(s), V(s), -1);
        return 1;
    case 0x89: case 0x8a: {
        mesh_std(s, 0, 2, -1);
        const float w = wave(s, -1.5f);
        const saved_color k = save_color(s);
        grey(s, t == 0x89 ? w * 0.5f + 0.5f : w * 0.4f + 0.6f);
        mesh(s, 0, 2, A(s), 0, BL(s), U(s), V(s), t == 0x89 ? 0x8341 : 0x8342);
        restore_color(s, k);
        return 1;
    }
    case 0x99:
        mesh(s, 0, 0x42, A(s), 0, wave(s, -1.5f) * 0.5f + 0.5f, U(s), V(s), -1);
        return 1;
    default:
        return 0;
    }
}
static void swamp_after(const slot *s)
{
    if (!s->o[MU_OBJF_LIVE])
        return;
    switch (mu_obj_i32(s->o, MU_OBJF_TYPE)) {
    case 0x20:
        mesh(s, 0, 2, A(s), 0, BL(s), U(s), tmod(s, 100000, 0.0004f, 1), -1);
        break;
    case 0x40:
        body_t(s, 2, BM(s), BL(s), U(s), V(s), H(s), water(s, 0x8348));
        break;
    default:
        body_std(s, H(s));
        break;
    }
}

/* ---- 145 (0x91): custom 0x00d76059 (no world test: an alpha below 0.9 answers handled), after 0x00d77d18,
 * world test 0x00d79e40 ---- */
#define MU_OBJF_FADE_188 0x188   /* f32, type 0x99's glow alpha */
static void play(mu_obj_log *l, int32_t i, uint32_t id, uint32_t owner);
static int m145_custom(const slot *s)
{
    if (0.9f > A(s))
        return 1;
    switch (mu_obj_i32(s->o, MU_OBJF_TYPE)) {
    case 0x13: case 0x2d: case 0x2e: case 0x31:
        return 1;
    case 0x54: case 0x55:
        body(s, 2, BM(s), BL(s), U(s), V(s), -1);
        mesh(s, 0, 2, A(s), 0, wave(s, -1.5f) * 0.6f + 0.4f, U(s), V(s), 0x83ab);
        return 1;
    case 0x56: case 0x57: case 0x5a: case 0x5b:
        mesh_std(s, 0, 2, -1);
        mesh(s, 1, 0x42, A(s), 1, wave(s, -1.5f) * 0.6f + 0.4f, U(s), V(s), -1);
        return 1;
    case 0x5d:
        mesh(s, 0, 0x42, A(s), 0, wave(s, -1.5f) * 0.6f + 0.4f, U(s), V(s), -1);
        mesh_std(s, 1, 2, -1);
        return 1;
    case 0x5f:
        for (int32_t m = 0; m < 4; ++m)
            mesh_std(s, m, 2, -1);
        mesh_own(s, 3, 2, BL(s), 0x83b0);
        mesh_own(s, 4, 2, wave(s, -1.0f) * 0.6f + 0.4f, -1);
        mesh_own(s, 5, 2, wave(s, -1.0f) * 0.6f + 0.4f, -1);
        mesh_own(s, 6, 0x42, BL(s), -1);
        return 1;
    case 0x61:
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 1, 2, -1);
        mesh_own(s, 2, 2, wave(s, -1.5f) * 0.6f + 0.4f, -1);
        mesh_std(s, 3, 2, -1);
        mesh_own(s, 3, 0x42, wave(s, -1.5f) * 0.6f + 0.4f, 0x83ac);
        mesh_std(s, 4, 2, -1);
        return 1;
    case 0x71:
        mesh_std(s, 0, 2, -1);
        mesh_own(s, 1, 2, wave(s, -1.5f) * 0.6f + 0.4f, -1);
        return 1;
    case 0x77:
        for (int32_t m = 0; m < 4; ++m)
            mesh_std(s, m, 2, -1);
        for (int32_t m = 4; m < 7; ++m)
            mesh_own(s, m, 2, A(s) * wave(s, -1.5f) * 0.6f + 0.4f, -1);
        return 1;
    case 0x88: case 0x89: case 0x8a: case 0x8b: case 0x8c:
        mesh_std(s, 0, 2, -1);
        return 1;
    case 0x8e:
        mesh_std(s, 0, 2, -1);
        mesh_own(s, 0, 2, A(s) * wave(s, -1.5f) * 0.5f + 1.5f, 0x83ad);
        return 1;
    case 0x98:
        for (int32_t m = 0; m <= 0xd; ++m)
            if (m != 0xb)
                mesh_std(s, m, 2, -1);
        return 1;
    case 0x99: {   /* the glow fades in while the model's action is not 0; action 2 past frame 1 plays 0x5b4 */
        mesh(s, 0, 2, 1.0f, BM(s), BL(s), U(s), V(s), -1);
        float f = mu_obj_f32(s->o, MU_OBJF_FADE_188);
        f = action(s) != 0 ? f + 0.03f : f - 0.01f;
        mu_obj_set_f32(s->o, MU_OBJF_FADE_188, f);
        if (action(s) == 2 && (float)(int16_t)mu_obj_u16(s->b, 0xb4) > 1.0f)
            play(s->l, s->i, 0x5b4, 0);
        f = f > 0.0f ? f : 0.0f;   /* 0x0184f93f, then 0x0184f927 */
        f = f > 1.0f ? 1.0f : f;
        mu_obj_set_f32(s->o, MU_OBJF_FADE_188, f);
        mesh(s, 1, 0x42, f, 1, f, U(s), V(s), -1);
        return 1;
    }
    case 0xa0: case 0xa1: case 0xa4:
        mesh(s, 0, 2, A(s), 0, wave(s, -1.5f) * 0.2f + 0.8f, U(s), V(s), -1);
        return 1;
    default:
        return 0;
    }
}
static void m145_after(const slot *s)
{
    switch (mu_obj_i32(s->o, MU_OBJF_TYPE)) {
    case 0x31:
        body_t(s, 2, BM(s), BL(s), U(s), V(s), H(s), water(s, 0x838a));
        break;
    case 0x88: case 0x89: case 0x8a: case 0x8b: case 0x8c:
        mesh_own(s, 1, 2, A(s), -1);
        mesh_own(s, 2, 0x42, A(s), -1);
        mesh(s, 2, 0x44, 0.3f, 2, BL(s), U(s), V(s), -1);
        break;
    case 0x8e:
        mesh_own(s, 2, 2, A(s), -1);
        mesh_own(s, 1, 2, A(s), -1);
        mesh(s, 2, 0x44, 0.3f, 2, BL(s), U(s), V(s), -1);
        break;
    case 0x98:
        mesh_own(s, 0xb, 2, wave(s, -1.5f) * 0.6f + 0.4f, -1);
        break;
    default:
        body_std(s, H(s));
        break;
    }
}

/* ---- Kardamahal 143 (0x8f): custom 0x00e0f4bc, after 0x00e118fd, world test 0x00e136f3. The custom slot keeps
 * the body colour in a vector object (0x0095ea8e .. 0x0095eda9) around its textured meshes. ---- */
static void colored(const slot *s, float r, float g, float bl, int32_t m, int32_t texture)
{
    const saved_color k = save_color(s);
    color(s, r, g, bl);
    mesh_own(s, m, 2, BL(s), texture);
    mesh_own(s, m, 0x44, BL(s), -1);
    mesh_own(s, 1, 2, BL(s), -1);
    restore_color(s, k);
}
static int kardamahal_custom(const slot *s)
{
    const int32_t t = mu_obj_i32(s->o, MU_OBJF_TYPE);
    switch (t) {
    case 0: case 0x1c: case 0x21:
        return 1;
    case 0x6f: case 0x71: case 0x7b: case 0xaa: {
        body(s, 2, BM(s), BL(s), U(s), V(s), -1);
        const saved_color k = save_color(s);
        const float w = wave(s, -2.5f) * (t == 0x71 ? 0.6f : 0.3f) + (t == 0x71 ? 0.4f : 0.7f);
        grey(s, w);
        const int32_t m = t == 0x7b ? 7 : t == 0xaa ? 1 : 0;
        mesh_own(s, m, 2, BL(s), t == 0x6f ? 0x85b7 : t == 0x71 ? 0x85aa : t == 0x7b ? 0x85b8 : 0x85bb);
        restore_color(s, k);
        if (t == 0x71)
            mesh_own(s, 1, 2, BL(s), 0x85ab);
        else if (t != 0x6f)
            mesh_own(s, m, 0x44, BL(s), -1);
        return 1;
    }
    case 0x73: {
        body(s, 2, BM(s), BL(s), U(s), V(s), -1);
        const saved_color k = save_color(s);
        const float w = wave(s, -2.5f) * 0.6f + 0.4f;
        grey(s, w);
        grey(s, w);
        mesh_own(s, 6, 2, BL(s), 0x85ac);
        restore_color(s, k);
        mesh_own(s, 6, 0x44, BL(s), -1);
        grey(s, w);
        mesh_own(s, 7, 2, BL(s), 0x85ad);
        restore_color(s, k);
        grey(s, w);
        mesh_own(s, 4, 2, BL(s), -1);
        restore_color(s, k);
        mesh_own(s, 4, 0x44, BL(s), -1);
        grey(s, w);
        mesh_own(s, 5, 2, BL(s), -1);
        restore_color(s, k);
        return 1;
    }
    case 0x7e: case 0x7f: case 0x80: case 0x81: case 0x82: {
        body(s, 2, BM(s), BL(s), U(s), V(s), 1);
        const float x = wave(s, -2.5f) * 0.6f + 0.4f;
        switch (t) {
        case 0x7e: colored(s, 0.74f * x, 0.17f * x, 0.62f * x, 2, 0x85ae); break;
        case 0x7f: colored(s, x * 0.77f, x * 0.74f, x * 0.63f, 2, 0x85af); break;
        case 0x80: colored(s, x, x * 0.6f, x * 0.2f, 2, 0x85b0); break;
        case 0x81: colored(s, x * 0.1f, x * 0.41f, x * 0.8f, 2, 0x85b1); break;
        default: colored(s, x * 0.12f, x * 0.58f, x * 0.32f, 2, 0x85b2); break;
        }
        return 1;
    }
    case 0x85:
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 1, 2, -1);
        return 1;
    case 0x8c:
        mesh(s, 0, 2, A(s), 0, BL(s), U(s), V(s), -1);
        return 1;
    case 0x96: case 0x97: case 0x98: case 0x99:
        stream(s, 0);
        mesh(s, 0, 2, A(s), BM(s), BL(s), tmod(s, 100000, 8e-05f, 0), V(s), -1);
        stream(s, 0xff);
        return 1;
    default:
        return 0;
    }
}
static void kardamahal_after(const slot *s)
{
    switch (mu_obj_i32(s->o, MU_OBJF_TYPE)) {
    case 0:
        s->o[MU_OBJF_LIGHT_FULL] = 0;
        s->o[MU_OBJF_LIGHT_ENABLE] = 0;
        water_body(s, 500000, 2e-05f);
        break;
    case 4: case 0x21: case 0x72:
        body_std(s, H(s));
        break;
    case 0x1c:
        body_t(s, 2, BM(s), BL(s), U(s), V(s), H(s), water(s, 0x8589));
        break;
    case 0x71: {   /* AddTerrainLight 0x016cacfc(x, y, light, 3, frame light) */
        if (!s->model || !s->model->rand_fn)
            break;
        float l = (float)(s->model->rand_fn(s->model->rand_context) % 4 + 3) * 0.1f * 0.4f;
        l = l + 0.4f;
        const uint32_t a[6] = {wv_bits(mu_obj_f32(s->o, MU_OBJF_POSITION)),
                               wv_bits(mu_obj_f32(s->o, MU_OBJF_POSITION + 4)), wv_bits(l * 1.0f),
                               wv_bits(l * 0.2f), wv_bits(l * 0.1f), 3};
        wv_emit(s->l, MU_OBJ_CALL_ADD_LIGHT, s->i, a, 6);
        break;
    }
    case 0x85:
        mesh(s, 2, 2, A(s), 2, BL(s), (float)(cvtt(s->time) % 3000) / 3000.0f, V(s), -1);
        break;
    default:
        break;
    }
}

/* ---- Tormenta Island 141 (0x8d): custom 0x00e4cbd7 (types 0x7d..0x9a through the table 0x00e4eed3), after
 * 0x00e4f952, world test 0x00e54061 ---- */
static void glow_pair(const slot *s, int32_t m0, int32_t t0, int32_t m1, int32_t t1)   /* wave(-1) glows */
{
    const float w = wave(s, -1.0f) * 0.5f + 0.5f;
    mesh_own(s, m0, 0x42, w, t0);
    if (m1 >= 0)
        mesh_own(s, m1, 0x42, w, t1);
}
static int tormenta_custom(const slot *s)
{
    const int32_t t = mu_obj_i32(s->o, MU_OBJF_TYPE);
    switch (t) {
    case 0xc: case 0x48:
        body(s, 2, BM(s), BL(s), U(s), V(s), -1);
        return 1;
    case 0x14: {
        body(s, 2, BM(s), BL(s), U(s), V(s), -1);
        const float w = wave(s, -1.0f) * 0.5f + 0.5f;
        mesh_own(s, 0, 0x42, w, 0x84be);
        mesh_own(s, 1, 0x42, w, 0x84bf);
        mesh_own(s, 2, 0x42, w, 0x84c0);
        return 1;
    }
    case 0x88: {
        body(s, 2, BM(s), BL(s), U(s), V(s), -1);
        const float w = wave(s, -1.0f) * 0.5f + 0.5f;
        mesh_own(s, 0, 0x42, w, 0x84bb);
        mesh_own(s, 1, 0x42, w, 0x84bc);
        mesh_own(s, 2, 0x42, w, 0x84bd);
        return 1;
    }
    case 0x15: case 0x94: case 0x95: case 0x96: case 0x97: case 0x98: case 0x99: case 0x9a: {
        static const int32_t tex[8][2] = {{0x84c1, 0x84c2}, {0x84c3, 0x84c4}, {0x84c5, 0x84c6}, {0x84c7, 0x84c8},
                                          {0x84ca, 0x84c9}, {0x84cc, -1}, {0x84cb, -1}, {0x84cb, 0x84cc}};
        const int k = t == 0x15 ? 0 : t - 0x93;
        body(s, 2, BM(s), BL(s), U(s), V(s), -1);
        glow_pair(s, 0, tex[k][0], tex[k][1] < 0 ? -1 : 1, tex[k][1]);
        return 1;
    }
    case 0x1e: case 0x1f: case 0x20: case 0x22: case 0x41:
        return 1;
    case 0x2c: {   /* drawn only while 1 <= model frame < the frame count of the object's action (table +8) */
        const float n = s->model ? (float)s->model->action_frames : 0.0f;
        if (!(frame(s) >= 1.0f && n > frame(s)))
            return 1;
    }
    /* fall through */
    case 0x2b:
        mesh(s, 0, 2, A(s), 0, BL(s), U(s), tmod(s, 100000, 0.0004f, 1), -1);
        return 1;
    case 0x4b: case 0x50:
        mesh_std(s, 1, 2, -1);
        mesh_std(s, 2, 2, -1);
        return 1;
    case 0x4c: case 0x4d: case 0x4e:
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 1, 2, -1);
        return 1;
    case 0x4f:
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 2, 2, -1);
        return 1;
    case 0x76:
        mesh_std(s, 0, 2, -1);
        return 1;
    case 0x78: case 0x86: case 0x87:
        mesh_std(s, 0, 2, -1);
        glow_pair(s, 1, -1, -1, -1);
        return 1;
    case 0x79: case 0x7a: case 0x7b: {
        const int32_t n = t == 0x79 ? 5 : 4, first = t == 0x7b ? 2 : 0, count = t == 0x79 ? 3 : 2;
        for (int32_t m = 0; m < n; ++m)
            mesh_std(s, m, 2, -1);
        for (int32_t m = first; m < first + count; ++m)
            mesh_own(s, m, 0x42, 0.5f, -1);
        return 1;
    }
    case 0x7c: case 0x7d: case 0x7e: case 0x7f: case 0x80:
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 1, 2, -1);
        mesh_std(s, 3, 2, -1);
        mesh_std(s, 4, 2, -1);
        glow_pair(s, 2, -1, 5, -1);
        return 1;
    case 0x89:
        body(s, 0x42, BM(s), wave(s, -0.8f) * 0.4f + 0.6f, U(s), V(s), -1);
        return 1;
    case 0x8a: case 0x8b: case 0x8c: case 0x8d: case 0x8e: {
        mesh_std(s, 0, 2, -1);
        const float w = wave(s, -1.0f) * 0.5f + 0.5f;
        mesh_own(s, 1, 0x42, w, -1);
        mesh(s, 2, 0x42, A(s), 2, w, U(s), tmod(s, 100000, 0.0001f, 0), -1);
        return 1;
    }
    default:
        return 0;
    }
}
static void tormenta_after(const slot *s)
{
    const int32_t t = mu_obj_i32(s->o, MU_OBJF_TYPE);
    switch (t) {
    case 0xc:
        mesh(s, 0, 0x42, A(s), 0, BL(s), U(s), V(s), -1);
        break;
    case 0x48:
        mesh(s, 1, 0x42, A(s), 1, BL(s), U(s), V(s), -1);
        break;
    case 0x41:
        body_t(s, 2, BM(s), BL(s), U(s), V(s), H(s), water(s, 0x848e));
        break;
    case 0x4b: case 0x50: {
        const float w = wave(s, -1.0f) * 0.5f + 0.5f;
        mesh_own(s, 0, 0x42, w, -1);
        mesh_own(s, 1, 0x42, w, t == 0x4b ? 0x84af : 0x84b9);
        mesh_own(s, 2, 0x42, w, t == 0x4b ? 0x84b0 : 0x84ba);
        break;
    }
    case 0x4c: case 0x4d: case 0x4e: {
        const float w = wave(s, -1.0f) * 0.5f + 0.5f;
        const int32_t k = 0x84b1 + 2 * (t - 0x4c);
        mesh_own(s, 2, 0x42, w, -1);
        mesh_own(s, 0, 0x42, w, k);
        mesh_own(s, 1, 0x42, w, k + 1);
        break;
    }
    case 0x4f: {
        const float w = wave(s, -1.0f) * 0.5f + 0.5f;
        mesh_own(s, 1, 0x42, w, -1);
        mesh_own(s, 0, 0x42, w, 0x84b7);
        mesh_own(s, 2, 0x42, w, 0x84b8);
        break;
    }
    case 0x76: {
        const float w = wave(s, -1.0f) * 0.5f + 0.5f;
        mesh(s, 1, 0x42, A(s), 2, w, U(s), V(s), -1);
        mesh(s, 2, 0x42, A(s), 2, w, tmod(s, 0x4b0, 0.00083f, 0), V(s), -1);
        break;
    }
    case 0x79:
        glow_pair(s, 5, -1, -1, -1);
        break;
    case 0x7a: case 0x7b:
        glow_pair(s, 4, -1, -1, -1);
        break;
    default:
        body_std(s, H(s));
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
    /* RENDER-WORLDS-AFTER3: the class loaders (slot 0x24) of 141, 143, 144, 145 */
    {141, 0x84af, "Object142\\sostone0101_R.jpg", 0x2601, 0x2901},
    {141, 0x84b0, "Object142\\sostone0102_R.jpg", 0x2601, 0x2901},
    {141, 0x84b2, "Object142\\sostone0201_R.jpg", 0x2601, 0x2901},
    {141, 0x84b1, "Object142\\sostone0202_R.jpg", 0x2601, 0x2901},
    {141, 0x84b3, "Object142\\sostone0301_R.jpg", 0x2601, 0x2901},
    {141, 0x84b4, "Object142\\sostone0302_R.jpg", 0x2601, 0x2901},
    {141, 0x84b6, "Object142\\sostone0401_R.jpg", 0x2601, 0x2901},
    {141, 0x84b5, "Object142\\sostone0402_R.jpg", 0x2601, 0x2901},
    {141, 0x84b7, "Object142\\sostone0501_R.jpg", 0x2601, 0x2901},
    {141, 0x84b8, "Object142\\sostone0502_R.jpg", 0x2601, 0x2901},
    {141, 0x84ba, "Object142\\sostone0601_R.jpg", 0x2601, 0x2901},
    {141, 0x84b9, "Object142\\sostone0602_R.jpg", 0x2601, 0x2901},
    {141, 0x84bb, "Object142\\sotodoA01_R.jpg", 0x2601, 0x2901},
    {141, 0x84bc, "Object142\\sotodoA02_R.jpg", 0x2601, 0x2901},
    {141, 0x84bd, "Object142\\sotodoA03_R.jpg", 0x2601, 0x2901},
    {141, 0x84be, "Object142\\sotodoB01_R.jpg", 0x2601, 0x2901},
    {141, 0x84bf, "Object142\\sotodoB02_R.jpg", 0x2601, 0x2901},
    {141, 0x84c0, "Object142\\sotodoB03_R.jpg", 0x2601, 0x2901},
    {141, 0x84c2, "Object142\\sotodoB04_R.jpg", 0x2601, 0x2901},
    {141, 0x84c1, "Object142\\sotodoB05_R.jpg", 0x2601, 0x2901},
    {141, 0x84c4, "Object142\\sotodoC01_R.jpg", 0x2601, 0x2901},
    {141, 0x84c3, "Object142\\sotodoC02_R.jpg", 0x2601, 0x2901},
    {141, 0x84c6, "Object142\\sotodoC03_R.jpg", 0x2601, 0x2901},
    {141, 0x84c5, "Object142\\sotodoC04_R.jpg", 0x2601, 0x2901},
    {141, 0x84c7, "Object142\\sotodoC05_R.jpg", 0x2601, 0x2901},
    {141, 0x84c8, "Object142\\sotodoC06_R.jpg", 0x2601, 0x2901},
    {141, 0x84c9, "Object142\\sototoD01_R.jpg", 0x2601, 0x2901},
    {141, 0x84ca, "Object142\\sototoD02_R.jpg", 0x2601, 0x2901},
    {141, 0x84cb, "Object142\\sototoD03_R.jpg", 0x2601, 0x2901},
    {141, 0x84cc, "Object142\\sototoD04_R.jpg", 0x2601, 0x2901},
    {143, 0x85aa, "Object144\\hsFieldLighting01_R.jpg", 0x2601, 0x2900},
    {143, 0x85ab, "Object144\\hsFieldLighting02_R.jpg", 0x2601, 0x2900},
    {143, 0x85ac, "Object144\\hsMegalithSpaceB02_R.jpg", 0x2601, 0x2900},
    {143, 0x85ad, "Object144\\hsMegalithSpaceD02_R.jpg", 0x2601, 0x2900},
    {143, 0x85ae, "Object144\\hsAttributesDarkness02_R.jpg", 0x2601, 0x2900},
    {143, 0x85af, "Object144\\hsAttributesEarthA02_R.jpg", 0x2601, 0x2900},
    {143, 0x85b0, "Object144\\hsAttributesFireA02_R.jpg", 0x2601, 0x2900},
    {143, 0x85b1, "Object144\\hsAttributesWaterA02_R.jpg", 0x2601, 0x2900},
    {143, 0x85b2, "Object144\\hsAttributesWindA02_R.jpg", 0x2601, 0x2900},
    {143, 0x85b7, "Object144\\sdsaferzone05B_R.jpg", 0x2601, 0x2900},
    {143, 0x85b8, "Object144\\sdsaferzone14B_R.jpg", 0x2601, 0x2900},
    {143, 0x85bb, "Object144\\sdsaferzone14B01_R.jpg", 0x2601, 0x2900},
    {144, 0x8341, "Object145\\hsBurntwoodA01_R.jpg", 0x2601, 0x2900},
    {144, 0x8342, "Object145\\hsBurntwoodA02_R.jpg", 0x2601, 0x2900},
    {144, 0x8344, "Object145\\sostone10_R.jpg", 0x2601, 0x2900},
    {144, 0x8345, "Object145\\soMyobi01_R.jpg", 0x2601, 0x2900},
    {144, 0x8346, "Object145\\soGuan01_R.jpg", 0x2601, 0x2900},
    {144, 0x8347, "Object145\\soMyobi02_R.jpg", 0x2601, 0x2900},
    {145, 0x83ab, "Object146\\hsAquilasDecoA03_R.jpg", 0x2601, 0x2901},
    {145, 0x83ac, "Object146\\hsAquilasSafezonStageA06_R.jpg", 0x2601, 0x2901},
    {145, 0x83ad, "Object146\\hsChandelierB01_R.jpg", 0x2601, 0x2901},
    {145, 0x83b0, "Object146\\hsEagleStatueA01_R.jpg", 0x2601, 0x2901},
};
/* The 32 water bitmaps a class loader registers in a loop (Object<world + 1>\wt%02d_R.jpg, GL_LINEAR, GL_REPEAT):
 * 133 0x8320 (0x00d80941), 141 0x848e, 143 0x8589, 144 0x8348 (0x00e465ca), 145 0x838a. */
static const struct {
    int32_t world, base;
} waters[] = {{133, 0x8320}, {141, 0x848e}, {143, 0x8589}, {144, 0x8348}, {145, 0x838a}};
static char water_paths[sizeof waters / sizeof waters[0]][32][24];
int mu_world_slot_bitmap(int32_t world, int32_t index, const char **path, uint32_t *filter, uint32_t *wrap)
{
    for (size_t k = 0; k < sizeof waters / sizeof waters[0]; ++k)
        if (waters[k].world == world && index >= waters[k].base && index < waters[k].base + 32) {
            char *name = water_paths[k][index - waters[k].base];
            snprintf(name, sizeof water_paths[0][0], "Object%d\\wt%02d_R.jpg", (int)world + 1,
                     (int)(index - waters[k].base));
            *path = name;
            *filter = 0x2601;
            *wrap = 0x2901;
            return 1;
        }
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
int32_t mu_world_slot_bitmaps(int32_t world, int32_t type, int32_t out[MU_WORLD_SLOT_BITMAPS])
{
    static const struct {
        int32_t world, type, base;
    } water_uses[] = {{133, 0x8f, 0x8320}, {141, 0x41, 0x848e}, {143, 0x1c, 0x8589}, {144, 0x40, 0x8348},
                      {145, 0x31, 0x838a}};
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
        /* RENDER-WORLDS-AFTER3 */
        {141, 0x14, {0x84be, 0x84bf, 0x84c0}}, {141, 0x15, {0x84c1, 0x84c2}}, {141, 0x88, {0x84bb, 0x84bc, 0x84bd}},
        {141, 0x94, {0x84c3, 0x84c4}}, {141, 0x95, {0x84c5, 0x84c6}}, {141, 0x96, {0x84c7, 0x84c8}},
        {141, 0x97, {0x84ca, 0x84c9}}, {141, 0x98, {0x84cc}}, {141, 0x99, {0x84cb}}, {141, 0x9a, {0x84cb, 0x84cc}},
        {141, 0x4b, {0x84af, 0x84b0}}, {141, 0x4c, {0x84b1, 0x84b2}}, {141, 0x4d, {0x84b3, 0x84b4}},
        {141, 0x4e, {0x84b5, 0x84b6}}, {141, 0x4f, {0x84b7, 0x84b8}}, {141, 0x50, {0x84b9, 0x84ba}},
        {143, 0x6f, {0x85b7}}, {143, 0x71, {0x85aa, 0x85ab}}, {143, 0x73, {0x85ac, 0x85ad}}, {143, 0x7b, {0x85b8}},
        {143, 0x7e, {0x85ae}}, {143, 0x7f, {0x85af}}, {143, 0x80, {0x85b0}}, {143, 0x81, {0x85b1}},
        {143, 0x82, {0x85b2}}, {143, 0xaa, {0x85bb}},
        {144, 3, {0x8344}}, {144, 4, {0x8345}}, {144, 6, {0x8346}}, {144, 0xb, {0x8347}}, {144, 0x89, {0x8341}},
        {144, 0x8a, {0x8342}},
        {145, 0x54, {0x83ab}}, {145, 0x55, {0x83ab}}, {145, 0x61, {0x83ac}}, {145, 0x8e, {0x83ad}},
        {145, 0x5f, {0x83b0}},
    };
    int32_t n = 0;
    for (size_t k = 0; k < sizeof water_uses / sizeof water_uses[0]; ++k)
        if (water_uses[k].world == world && water_uses[k].type == type)
            for (int32_t j = 0; j < 32; ++j)
                out[n++] = water_uses[k].base + j;
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
    {91, acheron_custom, acheron_after}, {113, nixies_custom, nixies_after}, {131, scorched_custom, scorched_after},
    {132, icarus2_custom, icarus2_after}, {134, aida_custom, aida_after}, {135, kethotum1_custom, kethotum1_after},
    {136, kethotum2_custom, kethotum2_after}, {137, kanturu_custom, kanturu_after}, {138, ignis_custom, ignis_after},
    {139, none_custom, none_after},
    {140, tarkan_custom, tarkan_after}, {142, karutan2_custom, karutan2_after},
    {133, arnil_custom, arnil_after}, {141, tormenta_custom, tormenta_after},   /* RENDER-WORLDS-AFTER3 */
    {143, kardamahal_custom, kardamahal_after}, {144, swamp_custom, swamp_after}, {145, m145_custom, m145_after},
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
static int custom_world_test(int32_t cls, int32_t world)
{
    return cls == 145 || world_test(cls, world);   /* 145's custom slot has none */
}
int mu_class_custom(int32_t cls, uint8_t *o, uint8_t *b, int32_t i, int32_t world, float time,
                    const mu_slot_model *model, mu_obj_log *l)
{
    const int k = find(cls);
    if (k < 0 || !custom_world_test(cls, world) || !o || !b)
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
