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
/* 0x0185bdc4(period, 0): (±cos + 1) / 2 of the clock phase (as mount_render.c's mu_hp_wave) */
static float wave(const slot *s, float period)
{
    float a = 0.0f * 0.017453292f;
    a = (a * 1000.0f) / period + s->time;
    const int32_t t = !(a > -2147483904.0f && a < 2147483648.0f) ? INT32_MIN : (int32_t)a;
    const int32_t m = (int32_t)(6283.1855f / period);
    const float x = (float)(t % m) * 0.001f * period;
    const float w = 3.1415927f > x ? -(float)cos((double)x) : (float)cos((double)x);
    return (w + 1.0f) * 0.5f;
}
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

/* ---- dispatch ---- */
typedef int (*custom_fn)(const slot *);
typedef void (*after_fn)(const slot *);
static const struct {
    int32_t world;
    custom_fn custom;
    after_fn after;
} classes[] = {
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
int mu_class_custom(int32_t cls, uint8_t *o, uint8_t *b, int32_t i, int32_t world, float time, mu_obj_log *l)
{
    const int k = find(cls);
    if (k < 0 || world != cls || !o || !b)
        return 0;
    const slot s = {o, b, i, time, l};
    return classes[k].custom(&s);
}
void mu_class_after(int32_t cls, uint8_t *o, uint8_t *b, int32_t i, int32_t world, float time, mu_obj_log *l)
{
    const int k = find(cls);
    if (k < 0 || world != cls || !o || !b)
        return;
    const slot s = {o, b, i, time, l};
    classes[k].after(&s);
}
