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
    case 79: case 114:
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
