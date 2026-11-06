/* RENDER-WORLDS-SLOTS: the custom render (slot 0x38) and after render (slot 0x3c) of the world classes the
 * RENDER-WORLDS-AFTER lanes left: thiscall(handler, object, model, index). Each slot runs its own world test on
 * the current world [0x01cf15fc] (Ferea 112 has none) and tests the object and model pointers where the client
 * does. Logged as in world_slots_visual.c. Addresses in docs/research/client-worlds-slots.md. */
#include "world_visual_slots.h"

/* ---- Loren Market 79 (custom 0x00e6ce2d, after 0x00e6d062, world test 0x00e6eccc) and Event square 114
 * (0x00e1f6ca, 0x00e1f8ff, 0x00e20416): one body behind two world tests ---- */
static int market_custom(const slot *s)
{
    switch (mu_obj_i32(s->o, MU_OBJF_TYPE)) {
    case 8: case 0x1e:
        set_after(s);
        return 1;
    case 0x32: {   /* glColor3fv(model +0x54) before each block changes no value */
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 1, 2, -1);
        mesh_std(s, 3, 2, -1);
        float x = wave(s, -1.2f) + 0.4f;
        if (x > 1.0f)
            x = 1.0f;
        mesh(s, 2, 2, A(s), -2, BL(s) * x, U(s), V(s), -1);
        return 1;
    }
    default:
        return 0;
    }
}
static void market_after(const slot *s)
{
    switch (mu_obj_i32(s->o, MU_OBJF_TYPE)) {
    case 8: {
        for (int32_t m = 2; m <= 4; ++m)
            mesh(s, m, 2, A(s), BM(s), BL(s), 0.0f, 0.0f, -1);
        const float u = csin(s->time * 0.0007f) * 0.05f, v = csin(s->time * 0.001f) * 0.05f;
        mesh(s, 1, 0x42, A(s), 1, 0.3f, U(s), tmod(s, 10000, 0.001f, 1), -1);
        mesh(s, 0, 0x42, A(s), 0, 0.3f, u, v, -1);
        break;
    }
    case 0x1e:
        body_std(s, H(s));
        break;
    case 0x44:
        mesh(s, 0, 0x42, A(s), 0, BL(s), U(s), V(s), -1);
        break;
    default:
        break;
    }
}
static int market_world(int32_t cls, int32_t world) { return world == (cls == 114 ? 0x72 : 0x4f); }

/* ---- Ferea 112 (custom 0x00de8a10, after 0x00de9eab; no world test, both test the object and model) ---- */
/* RenderMesh with an explicit alpha (the slot passes 1.0 instead of the object's) */
static void mesh_a(const slot *s, int32_t m, uint32_t flags, float alpha, int32_t blend, float light, float u, float v,
                   int32_t texture)
{
    const uint32_t a[8] = {(uint32_t)m, flags, wv_bits(alpha), (uint32_t)blend, wv_bits(light), wv_bits(u),
                           wv_bits(v), (uint32_t)texture};
    wv_emit(s->l, MU_OBJ_CALL_MESH, s->i, a, 8);
}
static void body_a(const slot *s, float alpha, int32_t blend, float light, float u, float v, int32_t texture)
{
    const uint32_t a[8] = {2, wv_bits(alpha), (uint32_t)blend, wv_bits(light), wv_bits(u), wv_bits(v), 0xffffffffu,
                           (uint32_t)texture};
    wv_emit(s->l, MU_OBJ_CALL_BODY, s->i, a, 8);
}
/* (float)((int)WorldTime % n) * 0.0001 * k * 2 - 1: the scroll phase of the after slot and types 0x57/0x5f */
static float ferea_scroll(const slot *s, int32_t n, float k)
{
    return (float)(cvtt(s->time) % n) * 1e-4f * k * 2.0f - 1.0f;
}
static int ferea_custom(const slot *s)
{
    switch (mu_obj_i32(s->o, MU_OBJF_TYPE)) {
    case 0x27: {   /* the door: meshes at full alpha, mesh 3 scrolled by the opening (action 1) or closing (2) */
        static const int32_t solid[] = {0, 1, 2, 4, 5};
        for (int k = 0; k < 5; ++k)
            mesh_a(s, solid[k], 2, 1.0f, -1, 1.0f, 0.0f, 0.0f, -1);
        const uint16_t act = mu_obj_u16(s->o, MU_OBJF_ACTION);
        if (act == 1)
            mu_obj_set_f32(s->o, MU_OBJF_BLEND_V, V(s) + 0.1f);
        else if (act == 2)
            mu_obj_set_f32(s->o, MU_OBJF_BLEND_V, V(s) - 0.1f);
        stream(s, 3);
        mesh_a(s, 3, 2, 1.0f, -1, BL(s), U(s), V(s), -1);
        return 1;
    }
    case 0x2b: case 0x33: case 0x72:
        return 1;
    case 0x4b: case 0x51:
        mesh_std(s, 0, 2, -1);
        mesh(s, 0, 0x44, A(s), 0, BL(s), U(s), V(s), -1);
        mesh_std(s, 1, 2, -1);
        mesh_std(s, 5, 2, -1);
        return 1;
    case 0x57: case 0x5f: {
        const float x = (float)(cvtt(s->time) % 5000) * 1e-4f * 2.0f * 2.0f - 1.0f;
        for (int32_t m = 0; m <= 3; ++m)
            mesh_std(s, m, 2, -1);
        mesh_std(s, 3, 0x42, -1);
        mesh(s, 4, 2, A(s), 4, BL(s), U(s), -x, -1);
        return 1;
    }
    case 0x73: {
        const float w = (csin(s->time * 0.002f) + 1.0f) * 0.5f * 0.5f + 0.5f;
        mesh_std(s, 0, 2, -1);
        mesh_a(s, 1, 2, 1.0f, 1, w, U(s), V(s), -1);
        mesh_std(s, 2, 2, -1);
        return 1;
    }
    case 0x7b: {   /* the statue: hs_statueB while the handler's door state (+0x48) is 2 or 3 */
        const int32_t state = s->model->handler_state;
        body_a(s, 1.0f, -1, BL(s), 0.0f, 0.0f, state == 3 || state == 2 ? 0x8225 : -1);
        return 1;
    }
    case 0x8a: {
        const float w = (csin(s->time * 0.002f) + 1.0f) * 0.3f + 0.2f;
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 1, 2, -1);
        mesh(s, 2, 2, A(s), 2, BL(s), U(s), V(s), -1);
        mesh(s, 3, 2, A(s), 3, w, U(s), V(s), -1);
        mesh_std(s, 4, 2, -1);
        return 1;
    }
    case 0x99: case 0x9b:
        mesh_std(s, 0, 2, -1);
        return 1;
    case 0x9a: {
        const float w = (float)((double)(csin(s->time * 0.002f) + 1.0f) * 0.3 + 0.20000000298023224);
        mesh_std(s, 0, 2, -1);
        mesh(s, 1, 2, A(s), 1, w, U(s), V(s), -1);
        return 1;
    }
    default:   /* types 0x607, 0x8c6 and 0x8c7 are above the world manager's 300 */
        return 0;
    }
}
static void ferea_after(const slot *s)
{
    const int32_t t = mu_obj_i32(s->o, MU_OBJF_TYPE);
    switch (t) {
    case 0x2b:
        body(s, 2, BM(s), BL(s), U(s), V(s), -1);
        break;
    case 0x33:
        body(s, 2, -1, 1.0f, 0.0f, 0.0f, -1);
        break;
    case 0x4b: case 0x51: {
        const float a = (csin(s->time * 0.007f) + 2.0f) * 0.5f, x = ferea_scroll(s, 0x8238, 0.3f);
        mesh(s, 2, 2, A(s), 2, BL(s), U(s), V(s), -1);
        mesh(s, 3, 2, A(s), 3, t == 0x51 ? 0.7f : 1.0f, U(s), V(s), -1);
        mesh(s, 4, 2, A(s), 4, a, U(s), -x, -1);
        mesh(s, 6, 2, A(s), 6, BL(s), U(s), V(s), -1);
        break;
    }
    case 0x57: {
        const float x = ferea_scroll(s, 0x1a0b, 1.5f);
        mesh(s, 5, 2, A(s), 5, BL(s), x, -x, -1);
        break;
    }
    case 0x72: {
        const float x = ferea_scroll(s, 0x8238, 0.3f);
        mesh(s, 0, 2, A(s), 0, BL(s), x, -x, -1);
        break;
    }
    case 0x99:
        mesh(s, 1, 2, A(s), 1, BL(s), U(s), ferea_scroll(s, 0x2711, 1.0f), -1);
        mesh(s, 2, 2, A(s), 2, BL(s), U(s), U(s), -1);   /* the client passes U as v */
        break;
    case 0x9b: {
        const float x = ferea_scroll(s, 0x411c, 0.6f);
        mesh(s, 1, 2, A(s), 1, BL(s), U(s), V(s), -1);
        mesh(s, 2, 2, A(s), 2, BL(s), x, -x, -1);
        break;
    }
    default:
        break;
    }
}

/* ---- Vulcanus 63 (custom 0x00e8f515, after 0x00e8ff20, world test 0x00e94004: 0x3f) ---- */
static void vulc_sprite(const slot *s, const float p[3], const float light[3])   /* CreateSprite 0x01692eb7 */
{
    wv_sprite(s->i, 0x7ef7, p, mu_obj_f32(s->o, MU_OBJF_SCALE) * 5.0f, light, s->l);
}
/* CreateParticle 0x0168fafd(0x7f5a, point, object angle, light, sub, scale * 1.5, no owner) */
static void vulc_particle(const slot *s, const float p[3], const float light[3], int32_t sub)
{
    uint32_t a[13] = {0x7f5a};
    memcpy(a + 1, p, 12);
    memcpy(a + 4, s->o + MU_OBJF_ANGLE, 12);
    memcpy(a + 7, light, 12);
    a[10] = (uint32_t)sub;
    a[11] = wv_bits(mu_obj_f32(s->o, MU_OBJF_SCALE) * 1.5f);
    a[12] = 0;
    wv_emit(s->l, MU_OBJ_CALL_PARTICLE, s->i, a, 13);
}
/* the lava statues 0x43/0x44: the scrolling body (StreamMesh 1), mesh 0 and its red 0x44 glow, two flares on
 * bone 6 (its origin and 350 below), then a spark from bone 4 inside a frame window */
static int vulcanus_statue(const slot *s, int32_t t)
{
    stream(s, 1);
    body(s, 2, BM(s), BL(s), U(s), tmod(s, 10000, 1e-4f, 0), -1);
    stream(s, 0xff);
    mesh_std(s, 0, 2, -1);
    color(s, 1.0f, 0.0f, 0.0f);
    const float red[3] = {1.0f, 0.0f, 0.0f};
    mesh_a(s, 0, 0x44, 0.2f, 0, 0.2f, U(s), V(s), -1);
    const float origin[3] = {0.0f, 0.0f, 0.0f}, below[3] = {0.0f, 0.0f, -350.0f};
    float p[3];
    if (s->model->bone) {
        s->model->bone(s->model->bone_context, 6, origin, p);
        vulc_sprite(s, p, red);
        s->model->bone(s->model->bone_context, 6, below, p);
        vulc_sprite(s, p, red);
    }
    if (t == 0x43) {   /* the eyes: shut between frames 35 and 37; between 1 and 2 they open on a 2 in 1000 */
        float f = mu_obj_f32(s->o, MU_OBJF_FRAME);
        if (f >= 35.0f && 37.0f >= f) {
            const uint16_t shut = 0xffff;   /* the object's u16 +0x54 */
            memcpy(s->o + 0x54, &shut, 2);
        }
        f = mu_obj_f32(s->o, MU_OBJF_FRAME);
        if (f >= 1.0f && 2.0f >= f && (int16_t)mu_obj_u16(s->o, 0x54) != 1) {
            mu_obj_set_f32(s->o, MU_OBJF_FRAME, 1.0f);
            const int32_t r = s->model->rand_fn(s->model->rand_context) % 1000;
            const uint16_t value = r >= 0 && r < 2 ? 1 : 0xffff;
            memcpy(s->o + 0x54, &value, 2);
        }
        const float light[3] = {0.4f, 0.1f, 0.1f}, side[3] = {-150.0f, 0.0f, 0.0f};
        if (s->model->bone) {
            s->model->bone(s->model->bone_context, 4, side, p);
            f = mu_obj_f32(s->o, MU_OBJF_FRAME);
            if (f >= 35.0f && 50.0f > f)
                vulc_particle(s, p, light, 0x3f);
        }
    } else {
        const float light[3] = {0.3f, 0.1f, 0.1f};
        float local[3];
        local[0] = (float)(s->model->rand_fn(s->model->rand_context) % 20) - 30.0f;
        local[1] = (float)(s->model->rand_fn(s->model->rand_context) % 20) - 30.0f;
        local[2] = 0.0f;
        const float f = mu_obj_f32(s->o, MU_OBJF_FRAME);
        if (s->model->bone) {
            s->model->bone(s->model->bone_context, 4, local, p);
            if (f >= 7.0f && 13.0f > f)
                vulc_particle(s, p, light, 0x12);
        }
    }
    return 1;
}
static int vulcanus_custom(const slot *s)
{
    const int32_t t = mu_obj_i32(s->o, MU_OBJF_TYPE);
    switch (t) {
    case 0xf:
        stream(s, 0);
        body(s, 2, BM(s), BL(s), U(s), tmod(s, 10000, 1e-4f, 1), -1);
        stream(s, 0xff);
        return 1;
    case 0x43: case 0x44:
        return vulcanus_statue(s, t);
    case 0x46:
        return 1;
    default:   /* types 0x842..0x848 are above the world manager's 300 */
        return 0;
    }
}
static void vulcanus_after(const slot *s)
{
    switch (mu_obj_i32(s->o, MU_OBJF_TYPE)) {
    case 0x10:
        body(s, 2, 0, (csin(s->time * 0.002f) + 1.0f) * 0.5f, U(s), V(s), H(s));
        break;
    case 0x46:
        body(s, 2, BM(s), BL(s), U(s), V(s), -1);
        break;
    default:
        break;
    }
}

/* ---- Swamp of Darkness 122 (custom 0x00e54752, after 0x00e555d2, world test 0x00e543a1: 0x7a) ---- */
static void dark_glow(const slot *s, int32_t m, float light, int32_t texture, int n)
{
    for (int k = 0; k < n; ++k)
        mesh(s, m, 0x42, A(s), m, light, U(s), V(s), texture);
}
static int dark_custom(const slot *s)
{
    const int32_t t = mu_obj_i32(s->o, MU_OBJF_TYPE);
    switch (t) {
    case 0x27: case 0x29: case 0x70:
        return 1;
    case 0x3b:
        mesh_std(s, 1, 2, -1);
        mesh(s, 0, 0x42, A(s), 0, BL(s), U(s), V(s), -1);
        return 1;
    case 0x58: case 0x6b: case 0x6c: case 0x6d:
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 1, 2, -1);
        dark_glow(s, 2, t == 0x6d ? 0.8f : wave(s, -2.0f) * 0.7f + 0.3f, -1, t == 0x58 ? 1 : t == 0x6d ? 2 : 3);
        return 1;
    case 0x7b: case 0x7c: case 0x7d: case 0x7f: case 0x80:
        mesh_std(s, 0, 2, -1);
        dark_glow(s, 1, wave(s, -2.0f) * 0.5f + 0.5f, -1, 3);
        return 1;
    case 0x7e:   /* with the Chrome09 reflection 0x8245 (flags 6) */
        mesh_std(s, 0, 2, -1);
        mesh_std(s, 1, 2, -1);
        mesh_std(s, 1, 6, 0x8245);
        dark_glow(s, 1, BL(s), -1, 1);
        dark_glow(s, 2, BL(s), -1, 1);
        return 1;
    case 0x83: case 0x84: case 0x85:   /* the crocodiles: body, then three glows of hsCrocodileA_R 0x8273 */
        body(s, 2, BM(s), BL(s), U(s), V(s), -1);
        dark_glow(s, 1, wave(s, -1.0f) * 0.9f + 0.1f, 0x8273, 3);
        return 1;
    default:
        return 0;
    }
}
static void dark_after(const slot *s)
{
    switch (mu_obj_i32(s->o, MU_OBJF_TYPE)) {
    case 0x27: case 0x29:
        dark_glow(s, 0, BL(s), -1, 1);
        break;
    case 0x58: case 0x6b:
        dark_glow(s, 3, BL(s), -1, 1);
        break;
    case 0x6c:
        dark_glow(s, 3, wave(s, -2.0f) * 0.5f + 0.5f, -1, 2);
        dark_glow(s, 4, BL(s), -1, 1);
        break;
    case 0x70:
        body(s, 2, BM(s), wave(s, -0.6f) * 0.5f + 0.5f, U(s), V(s), H(s));
        break;
    default:
        break;
    }
}

/* ---- Kubera 123..127 (custom 0x00e1a5df, after 0x00e1b6f5, world test 0x00e1e4b6: 0x7b..0x7f) ----
 * The handler's bitmap fields +0x1c..+0x48 (twelve words), written per world by the class loader (slot 0x24,
 * 0x00e18efb) after its LoadBitmap calls; the constructor 0x00e18da5 clears +0x1c..+0x24 and +0x38..+0x48. */
static const int32_t kubera_fields[5][12] = {
    {0x82af, 0x82b0, 0x82be, 0x82c3, 0x82c4, 0x82c5, 0x82c6, 0x82b9, 0x82a1, 0x82a2, 0x82ab, 0x82ac},
    {0x82b7, 0x82b8, 0x82bf, 0x82c7, 0x82c8, 0x82c9, 0x82ca, 0x82ba, 0x829b, 0x829c, 0x82a5, 0x82a6},
    {0x82b5, 0x82b6, 0x82c0, 0x82cb, 0x82cc, 0x82cd, 0x82ce, 0x82bb, 0x82a3, 0x82a4, 0x82ad, 0x82ae},
    {0x82b1, 0x82b2, 0x82c1, 0x82cf, 0x82d0, 0x82d1, 0x82d2, 0x82bc, 0x829d, 0x829e, 0x82a7, 0x82a8},
    {0x82b3, 0x82b4, 0x82c2, 0x82d3, 0x82d4, 0x82d5, 0x82d6, 0x82bd, 0x829f, 0x82a0, 0x82a9, 0x82aa},
};
static int kubera_world(int32_t world) { return world >= 0x7b && world <= 0x7f; }
/* handler +off (0x1c..0x48) of the current world's loader */
static int32_t kh(int32_t world, int32_t off) { return kubera_fields[world - 0x7b][(off - 0x1c) / 4]; }
/* types 0x2f/0x34: the gem mesh k scrolls while action 1 (backwards) or 3 plays from frame 3 to the last key */
static void kubera_gems(const slot *s, int32_t k)
{
    for (int32_t m = 0; m < s->model->mesh_count; ++m) {
        if (m != k) {
            mesh_std(s, m, 2, -1);
            continue;
        }
        stream(s, (uint8_t)k);
        const uint16_t act = mu_obj_u16(s->o, MU_OBJF_ACTION);
        const float f = mu_obj_f32(s->o, MU_OBJF_FRAME), last = (float)(s->model->action_frames - 1);
        const float r = (float)(cvtt(s->time) % 4000);
        if (act == 1 && f >= 3.0f && last >= f)
            mesh(s, k, 2, A(s), BM(s), BL(s), -r * 0.002f, V(s), -1);
        else if (act == 3 && f >= 3.0f && last >= f)
            mesh(s, k, 2, A(s), BM(s), BL(s), r * 0.002f, V(s), -1);
        else
            mesh_std(s, k, 2, -1);
    }
}
static int kubera_custom(const slot *s, int32_t world)
{
    const int32_t t = mu_obj_i32(s->o, MU_OBJF_TYPE);
    switch (t) {
    case 0x1d: case 0x1e: case 0x48: case 0x5e: case 0x6d: case 0x76: case 0x77: case 0x78: case 0x79: case 0x83:
    case 0x86: case 0x92: case 0x93: case 0x9f: case 0xa0:
        return 1;
    case 0x2f:
        kubera_gems(s, 5);
        return 1;
    case 0x34:
        kubera_gems(s, 7);
        return 1;
    case 0x4c:
        for (int32_t m = 0; m < s->model->mesh_count; ++m) {
            if (m != 3) {
                mesh_std(s, m, 2, -1);
                continue;
            }
            const float w = wave(s, -3.0f) * 0.2f + 0.7f;
            grey(s, 1.0f);
            mesh(s, 3, 0x42, A(s), -2, w, U(s), V(s), -1);
        }
        return 1;
    case 0x71: case 0x72: case 0x73: case 0x74: case 0x75: {
        /* the stone's meshes with the world's crystal bitmaps, then its last mesh again with Chrome 0x829a */
        static const struct {
            int32_t type, n, field[4];
        } rows[] = {{0x71, 4, {0x28, 0x2c, 0x30, 0x34}}, {0x72, 4, {0x2c, 0x28, 0x30, 0x34}},
                    {0x73, 3, {0x28, 0x30, 0x34}}, {0x74, 3, {0x2c, 0x28, 0x34}}, {0x75, 2, {0x1c, 0x20}}};
        const int r = t - 0x71;
        for (int32_t m = 0; m < rows[r].n; ++m)
            mesh(s, m, m == rows[r].n - 1 ? 0x42u : 2u, A(s), BM(s), BL(s), U(s), V(s), kh(world, rows[r].field[m]));
        mesh(s, rows[r].n - 1, 0x20000, A(s), -2, BL(s), U(s), V(s), 0x829a);
        return 1;
    }
    case 0x8b:
        mesh(s, 0, 0x42, A(s), BM(s), BL(s), U(s), V(s), kh(world, 0x24));
        return 1;
    case 0x8c: {
        for (int32_t m = 0; m < s->model->mesh_count; ++m)
            if (m != 3)
                mesh_std(s, m, 2, -1);
        const float w = wave(s, -3.0f) * 0.2f + 0.8f;
        mesh(s, 3, 0x42, A(s), -2, w, U(s), V(s), -1);
        mesh(s, 3, 0x42, A(s), -2, w, U(s), V(s), -1);
        return 1;
    }
    default:
        return 0;
    }
}
static void kubera_after(const slot *s, int32_t world)
{
    const float w = wave(s, -3.0f) * 0.2f + 0.8f;
    const int32_t t = mu_obj_i32(s->o, MU_OBJF_TYPE);
    switch (t) {
    case 0x1d: case 0x1e: case 0x48: case 0x5e: case 0x7e: case 0x92: case 0x93: case 0x9f:
        body_std(s, H(s));
        break;
    case 0x6d: case 0x76: case 0x77: case 0x78: case 0x79: {
        /* the five worlds' gate colours by type (handler +0x40 / +0x48 of worlds 0x7c, 0x7e, 0x7f, 0x7b, 0x7d) */
        static const int32_t glow[5][2] = {{0x829c, 0x82a6}, {0x829e, 0x82a8}, {0x82a0, 0x82aa}, {0x82a2, 0x82ac},
                                           {0x82a4, 0x82ae}};
        const int k = t == 0x6d ? 0 : t - 0x75;
        for (int32_t m = 0; m < s->model->mesh_count; ++m) {
            if (m == 0xd)
                mesh(s, 0xd, 0x42, A(s), -2, w, U(s), V(s), -1);
            else
                mesh_std(s, m, 2, -1);
            if (m == 8) {
                mesh(s, 8, 0x42, A(s), -2, w, U(s), V(s), glow[k][0]);
                mesh(s, 8, 0x20000, A(s), -2, BL(s), U(s), V(s), glow[k][0]);
            } else if (m == 9) {
                mesh(s, 9, 0x42, A(s), -2, w, U(s), V(s), glow[k][1]);
            }
        }
        break;
    }
    case 0xa0:
        for (int32_t m = 0; m < s->model->mesh_count; ++m) {
            if (m == 0xd) {
                mesh(s, 0xd, 0x42, A(s), -2, w, U(s), V(s), kh(world, 0x38));
            } else if (m == 8) {
                mesh(s, 8, 2, A(s), BM(s), BL(s), U(s), V(s), kh(world, 0x3c));
                mesh(s, 8, 0x42, A(s), -2, w, U(s), V(s), kh(world, 0x40));
                mesh(s, 8, 0x20000, A(s), -2, BL(s), U(s), V(s), kh(world, 0x40));
            } else if (m == 9) {
                mesh(s, 9, 2, A(s), BM(s), BL(s), U(s), V(s), kh(world, 0x44));
                mesh(s, 9, 0x42, A(s), -2, w, U(s), V(s), kh(world, 0x48));
            } else {
                mesh_std(s, m, 2, -1);
            }
        }
        break;
    case 0x86:
        for (int32_t m = 0; m < s->model->mesh_count; ++m)
            if (m != 2 && m != 3)
                mesh_std(s, m, 2, -1);
        mesh(s, 2, 0x42, A(s), BM(s), w, U(s), V(s), -1);
        mesh(s, 3, 0x42, A(s), BM(s), w, U(s), V(s), -1);
        break;
    default:
        break;
    }
}
/* Kubera's LoadBitmap registrations (loader 0x00e18efb, all under Object124, filter 0x2601) that its slots bind;
 * wrap 0x2900 for the ten sd_Amethyst0nA / hs_attGateA colour sheets, else 0x2901 */
static const struct {
    int32_t index;
    const char *path;
    uint32_t wrap;
} kubera_bitmaps[] = {
    {0x829a, "Object124\\sdchrome01.jpg", 0x2901},
    {0x829b, "Object124\\sd_Amethyst05A.jpg", 0x2900}, {0x829c, "Object124\\hsAmethystblue_R.jpg", 0x2901},
    {0x829d, "Object124\\sd_Amethyst04A.jpg", 0x2900}, {0x829e, "Object124\\hsAmethystgreen_R.jpg", 0x2901},
    {0x829f, "Object124\\sd_Amethyst06A.jpg", 0x2900}, {0x82a0, "Object124\\hsAmethystpurple_R.jpg", 0x2901},
    {0x82a1, "Object124\\sd_Amethyst03A.jpg", 0x2900}, {0x82a2, "Object124\\hsAmethystred_R.jpg", 0x2901},
    {0x82a3, "Object124\\sd_Amethyst07A.jpg", 0x2900}, {0x82a4, "Object124\\hsAmethystyellow_R.jpg", 0x2901},
    {0x82a5, "Object124\\hs_attGateAblue.jpg", 0x2900}, {0x82a6, "Object124\\hsattGateAblue_R.jpg", 0x2901},
    {0x82a7, "Object124\\hs_attGateAgreen.jpg", 0x2900}, {0x82a8, "Object124\\hsattGateAgreen_R.jpg", 0x2901},
    {0x82a9, "Object124\\hs_attGateApurple.jpg", 0x2900}, {0x82aa, "Object124\\hsattGateApurple_R.jpg", 0x2901},
    {0x82ab, "Object124\\hs_attGateAred.jpg", 0x2900}, {0x82ac, "Object124\\hsattGateAred_R.jpg", 0x2901},
    {0x82ad, "Object124\\hs_attGateAyellow.jpg", 0x2900}, {0x82ae, "Object124\\hsattGateAyellow_R.jpg", 0x2901},
    {0x82af, "Object124\\sd_gemstone02A_Red.jpg", 0x2901}, {0x82b0, "Object124\\sd_gemstone02A_Red_R.jpg", 0x2901},
    {0x82b1, "Object124\\sd_gemstone02A_Green.jpg", 0x2901},
    {0x82b2, "Object124\\sd_gemstone02A_Green_R.jpg", 0x2901},
    {0x82b3, "Object124\\sd_gemstone02A_Purple.jpg", 0x2901},
    {0x82b4, "Object124\\sd_gemstone02A_Purple_R.jpg", 0x2901},
    {0x82b5, "Object124\\sd_gemstone02A_Yellow.jpg", 0x2901},
    {0x82b6, "Object124\\sd_gemstone02A_Yellow_R.jpg", 0x2901},
    {0x82b7, "Object124\\sd_gemstone02A_Blue.jpg", 0x2901}, {0x82b8, "Object124\\sd_gemstone02A_Blue_R.jpg", 0x2901},
    {0x82b9, "Object124\\hsattGateA04r_R.jpg", 0x2901}, {0x82ba, "Object124\\hsattGateA04b_R.jpg", 0x2901},
    {0x82bb, "Object124\\hsattGateA04y_R.jpg", 0x2901}, {0x82bc, "Object124\\hsattgatea04g_r.jpg", 0x2901},
    {0x82bd, "Object124\\hsattGateA04p_R.jpg", 0x2901},
    {0x82be, "Object124\\texred_R.jpg", 0x2901}, {0x82bf, "Object124\\texblue_R.jpg", 0x2901},
    {0x82c0, "Object124\\texyellow_R.jpg", 0x2901}, {0x82c1, "Object124\\texgreen_R.jpg", 0x2901},
    {0x82c2, "Object124\\texpurple_R.jpg", 0x2901},
    {0x82c3, "Object124\\sd_Amethyst03A_Red01.jpg", 0x2901}, {0x82c4, "Object124\\sd_Amethyst03A_Red02.jpg", 0x2901},
    {0x82c5, "Object124\\sd_Amethyst03A_Red03.jpg", 0x2901}, {0x82c6, "Object124\\sdAmethyst03ARed_R.jpg", 0x2901},
    {0x82c7, "Object124\\sd_Amethyst03A_Blue01.jpg", 0x2901},
    {0x82c8, "Object124\\sd_Amethyst03A_Blue02.jpg", 0x2901},
    {0x82c9, "Object124\\sd_Amethyst03A_Blue03.jpg", 0x2901}, {0x82ca, "Object124\\sdAmethyst03ABlue_R.jpg", 0x2901},
    {0x82cb, "Object124\\sd_Amethyst03A_Yellow01.jpg", 0x2901},
    {0x82cc, "Object124\\sd_Amethyst03A_Yellow02.jpg", 0x2901},
    {0x82cd, "Object124\\sd_Amethyst03A_Yellow03.jpg", 0x2901},
    {0x82ce, "Object124\\sdAmethyst03AYellow_R.jpg", 0x2901},
    {0x82cf, "Object124\\sd_Amethyst03A_Green01.jpg", 0x2901},
    {0x82d0, "Object124\\sd_Amethyst03A_Green02.jpg", 0x2901},
    {0x82d1, "Object124\\sd_Amethyst03A_Green03.jpg", 0x2901},
    {0x82d2, "Object124\\sdAmethyst03AGreen_R.jpg", 0x2901},
    {0x82d3, "Object124\\sd_Amethyst03A_Purple01.jpg", 0x2901},
    {0x82d4, "Object124\\sd_Amethyst03A_Purple02.jpg", 0x2901},
    {0x82d5, "Object124\\sd_Amethyst03A_Purple03.jpg", 0x2901},
    {0x82d6, "Object124\\sdAmethyst03APurple_R.jpg", 0x2901},
};
/* the bitmaps Kubera's slots bind for objects of `type` in `world` */
static int32_t kubera_uses(int32_t world, int32_t type, int32_t *out, int32_t room)
{
    static const struct {
        int32_t type, field[5];
    } rows[] = {{0x71, {0x28, 0x2c, 0x30, 0x34}}, {0x72, {0x2c, 0x28, 0x30, 0x34}}, {0x73, {0x28, 0x30, 0x34}},
                {0x74, {0x2c, 0x28, 0x34}}, {0x75, {0x1c, 0x20}}, {0x8b, {0x24}},
                {0xa0, {0x38, 0x3c, 0x40, 0x44, 0x48}}};
    static const int32_t gates[5][3] = {{0x6d, 0x829c, 0x82a6}, {0x76, 0x829e, 0x82a8}, {0x77, 0x82a0, 0x82aa},
                                        {0x78, 0x82a2, 0x82ac}, {0x79, 0x82a4, 0x82ae}};
    int32_t n = 0;
    if (!kubera_world(world))
        return 0;
    for (size_t r = 0; r < sizeof rows / sizeof rows[0]; ++r)
        if (rows[r].type == type)
            for (int j = 0; j < 5 && rows[r].field[j] && n < room; ++j)
                out[n++] = kh(world, rows[r].field[j]);
    if (type >= 0x71 && type <= 0x75 && n < room)
        out[n++] = 0x829a;
    for (int r = 0; r < 5; ++r)
        if (gates[r][0] == type)
            for (int j = 1; j < 3 && n < room; ++j)
                out[n++] = gates[r][j];
    return n;
}

/* ---- dispatch ---- */
static int more_class(int32_t world)
{
    switch (world) {
    case 63: case 79: case 112: case 114: case 122:
        return world;
    case 123: case 124: case 125: case 126: case 127:
        return 123;
    default:
        return -1;
    }
}
int mu_slots_more_class(int32_t world) { return more_class(world); }
int mu_slots_more_custom(int32_t cls, const slot *s, int32_t world)
{
    switch (more_class(cls)) {
    case 79: case 114:
        return s->b && market_world(cls, world) ? market_custom(s) : 0;
    case 112:
        return s->o && s->b ? ferea_custom(s) : 0;
    case 63:
        return world == 0x3f ? vulcanus_custom(s) : 0;
    case 122:
        return world == 0x7a && s->o && s->b ? dark_custom(s) : 0;
    case 123:
        return kubera_world(world) && s->o && s->b ? kubera_custom(s, world) : 0;
    default:
        return 0;
    }
}
void mu_slots_more_after(int32_t cls, const slot *s, int32_t world)
{
    switch (more_class(cls)) {
    case 79: case 114:
        if (market_world(cls, world))
            market_after(s);
        break;
    case 112:
        if (s->o && s->b)
            ferea_after(s);
        break;
    case 63:
        if (world == 0x3f)
            vulcanus_after(s);
        break;
    case 122:
        if (world == 0x7a && s->o && s->b)
            dark_after(s);
        break;
    case 123:
        if (kubera_world(world) && s->o && s->b)
            kubera_after(s, world);
        break;
    default:
        break;
    }
}
/* the LoadBitmap registration of bitmap `index` in `world` (the class loaders of these classes) */
int mu_slots_more_bitmap(int32_t world, int32_t index, const char **path, uint32_t *filter, uint32_t *wrap)
{
    if (world == 112 && index == 0x8225) {   /* Ferea's loader 0x00de5977 */
        *path = "Object113\\hs_statueB.jpg";
        *filter = 0x2601;
        *wrap = 0x2900;
        return 1;
    }
    if (world == 122 && index == 0x8273) {   /* the shared object-bitmap site 0x0184187c */
        *path = "Object123\\hsCrocodileA_R.jpg";
        *filter = 0x2601;
        *wrap = 0x2900;
        return 1;
    }
    for (size_t k = 0; kubera_world(world) && k < sizeof kubera_bitmaps / sizeof kubera_bitmaps[0]; ++k)
        if (kubera_bitmaps[k].index == index) {
            *path = kubera_bitmaps[k].path;
            *filter = 0x2601;
            *wrap = kubera_bitmaps[k].wrap;
            return 1;
        }
    return 0;
}
int32_t mu_slots_more_bitmaps(int32_t world, int32_t type, int32_t *out, int32_t room)
{
    if (world == 112 && type == 0x7b && room > 0) {
        out[0] = 0x8225;
        return 1;
    }
    if (world == 122 && (type == 0x7e || (type >= 0x83 && type <= 0x85)) && room > 0) {
        out[0] = type == 0x7e ? 0x8245 : 0x8273;   /* 0x8245: Effect\Chrome09 (every world) */
        return 1;
    }
    return kubera_uses(world, type, out, room);
}
/* the handler's bitmap words +0x1c..+0x48 after the class loader of `world` (0 outside Kubera's worlds) */
int mu_slots_more_handler(int32_t world, int32_t out[12])
{
    if (!kubera_world(world))
        return 0;
    for (int k = 0; k < 12; ++k)
        out[k] = kubera_fields[world - 0x7b][k];
    return 1;
}
