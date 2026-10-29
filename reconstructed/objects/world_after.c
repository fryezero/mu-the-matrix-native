/* RenderObjects_AfterCharacter 0x016d6949 for every world (RENDER-WORLDS-AFTER); its after-render bodies
 * exist for the four A world groups and Abyss of Atlans 1-3. Login/character select keep their handlers. */
#include "../terrain/terrain.h"
#include "world_visual_internal.h"
int mu_noria_defer(uint8_t *);
int mu_elbeland_defer(uint8_t *);
int mu_raklion_defer(uint8_t *);
int mu_karutan_defer(uint8_t *);
int mu_elbeland_after(uint8_t *, int32_t, float, mu_obj_log *);
void mu_elbeland_after_sprites(const uint8_t *, int32_t, mu_world_bone_fn, void *, mu_obj_log *);
int mu_raklion_after(uint8_t *, int32_t, float, mu_obj_log *);
int mu_karutan_after(uint8_t *, int32_t, float, mu_obj_log *);
int mu_world_after_enabled(int32_t w)
{
    return w == 3 || w == 0x33 || w == 0x39 || w == 0x3a || w == 0x50 || w == 0x51;
}
int mu_world_defer(uint8_t *o, int32_t w)
{
    if (w == 3)
        return mu_noria_defer(o);
    if (w == 0x33)
        return mu_elbeland_defer(o);
    if (w == 0x39 || w == 0x3a)
        return mu_raklion_defer(o);
    if (w == 0x50 || w == 0x51)
        return mu_karutan_defer(o);
    return 0;
}
/* The four A worlds' types of 0x017fe909 (kept for callers that only need the type set). */
int mu_world_after_special(const uint8_t *o, int32_t w)
{
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    return (w == 3 && t == 0x13) || (w == 0x33 && t == 0x59) || ((w == 0x39 || w == 0x3a) && t == 0x4c);
}
/* RENDER-WORLDS-AFTER. Byte +5 of the current world handler (slot 8, 0x00d5cb7c): the base constructor
 * 0x00d5c99f clears it and only the constructors of the classes of worlds 134..145 set it to 1 (static). */
int mu_world_class_after(int32_t w)
{
    return w >= 134 && w <= 145;
}
/* The world test of 0x016d6949 (0x016d694f..0x016d6b30), the class answer given as class_flag. */
int mu_world_after_gate(int32_t w, int class_flag)
{
    return (w >= 0x25 && w <= 0x2a) || (w >= 0x2d && w <= 0x32) || w == 0x62 || w == 0x63 ||   /* 0x0095fba9 */
           w == 0x33 || w == 0x38 || w == 0x39 || w == 0x3a || w == 0x3f || (w >= 0x52 && w <= 0x5a) ||
           w == 0x4f || w == 0x50 || w == 0x51 || (w >= 0x5b && w <= 0x5e) || w == 3 || w == 0x21 ||
           w == 0x36 || (w >= 0x45 && w <= 0x4a) || (w >= 0x6e && w <= 0x71) || (w >= 0x7a && w <= 0x85) ||
           w == 8 || class_flag;
}
/* Worlds whose second pass has a native after-render (the A worlds, Abyss of Atlans 1-3 and the classes of
 * world_slots_visual.c). */
int mu_world_after_native(int32_t w)
{
    return mu_world_after_enabled(w) || (w >= 0x80 && w <= 0x82) || mu_class_slots(w);   /* RENDER-WORLDS-AFTER2 */
}
static int own_range(const uint8_t *o, const mu_obj_render_inputs *in, float range)
{
    const float x = mu_obj_f32(o, MU_OBJF_POSITION) * 0.01f, y = mu_obj_f32(o, MU_OBJF_POSITION + 4) * 0.01f;
    return mu_terrain_test_frustum_2d(in->x2d, in->y2d, in->scene_state, x, y, range);
}
static int in_list(int32_t t, const int32_t *list, int n)
{
    for (int k = 0; k < n; ++k)
        if (t == list[k])
            return 1;
    return 0;
}
/* The class answer (slot 0x14 through 0x00ea27b4). The base 0x00d5cbd6 answers no; the overrides of
 * worlds 134..145 (0x00d83fd8 ... 0x00d7556d) test their own types at the object range. */
static int class_select(uint8_t *o, int32_t w, const mu_obj_render_inputs *in)
{
    static const int32_t w142[] = {0x36, 0x37, 0x38, 0x39, 0x3e, 0xa2, 0xa3, 0xab, 0xac, 0xad, 0xae, 0xc5};
    static const int32_t w143[] = {4, 0x1c, 0x21, 0x72, 0x85};
    static const int32_t w145[] = {0x13, 0x2d, 0x2e, 0x31, 0x88, 0x89, 0x8a, 0x8b, 0x8c, 0x8e};
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    const float r = mu_obj_f32(o, MU_OBJF_RANGE);
    switch (w) {
    case 134: return t == 0 && own_range(o, in, r);
    case 136: return t == 0x18 && own_range(o, in, r);
    case 138: return t == 0x2d && own_range(o, in, r);
    case 141: return (t == 0x1f || t == 0x20) && own_range(o, in, r);
    case 142:
        if (!in_list(t, w142, 12))
            return 0;
        mu_obj_set_f32(o, MU_OBJF_RANGE, t == 0xc5 ? -1500.0f : -800.0f);
        return own_range(o, in, mu_obj_f32(o, MU_OBJF_RANGE));
    case 143: return t == 0 || (in_list(t, w143, 5) && own_range(o, in, r));
    case 144: return (t == 0x40 || t == 0x20) && own_range(o, in, r);
    case 145: return o[MU_OBJF_LIVE] && in_list(t, w145, 10) && own_range(o, in, r);
    default: return 0;   /* 135, 137, 139, 140 and the base class answer no */
    }
}
/* 0x017fe909: drawn by the second pass whatever its sector, live byte and +0xa. A failed world case
 * falls through to the class answer. */
int mu_world_after_select(uint8_t *o, const mu_obj_render_inputs *in)
{
    static const int32_t w70[] = {0x2b, 0x33, 0x4b, 0x51, 0x57, 0x72, 0x99, 0x9b};
    const int32_t w = in->world, t = mu_obj_i32(o, MU_OBJF_TYPE);
    const float r = mu_obj_f32(o, MU_OBJF_RANGE);
    int hit = 0;
    switch (w) {
    case 3: hit = t == 0x13 && own_range(o, in, -600.0f); break;
    case 0x21: case 0x36: hit = (t == 0x19 || t == 0x29) && own_range(o, in, -600.0f); break;
    case 0x25:   /* its own test (live, type 0x5f and type 0x74) never holds; it continues with 0x33's */
    case 0x33: hit = t == 0x59 && own_range(o, in, -400.0f); break;
    case 0x39: case 0x3a: hit = t == 0x4c && own_range(o, in, -600.0f); break;
    case 0x3f: case 0x52: hit = (t == 0x10 || t == 0x43 || t == 0x44) && own_range(o, in, -600.0f); break;
    case 0x5b: case 0x5c: hit = (t == 0x1b || (t >= 0x3c && t <= 0x3e)) && own_range(o, in, r); break;
    case 0x6e: case 0x6f: hit = (t == 6 || t == 0x11 || t == 0x96) && own_range(o, in, r); break;
    case 0x70: hit = in_list(t, w70, 8) && own_range(o, in, r); break;
    case 0x71: hit = t == 0x6a && own_range(o, in, r); break;
    case 0x7a: hit = t == 0x58 && own_range(o, in, r); break;
    case 0x7b: case 0x7c: case 0x7d: case 0x7e: case 0x7f: hit = t == 0x86 && own_range(o, in, r); break;
    case 0x80: case 0x81: case 0x82:
        hit = (t == 0x17 || t == 0x28 || t == 0x29 || t == 0x2c) && own_range(o, in, r);
        break;
    case 0x83: hit = (t == 0xb2 || t == 0x6a) && own_range(o, in, r); break;
    case 0x85: hit = t == 6 || (o[MU_OBJF_AFTER_CHARACTER] && own_range(o, in, r)); break;
    default: break;
    }
    return hit || class_select(o, w, in);
}
static void after_draw(mu_obj_log *log, int32_t k)
{
    const uint32_t a[3] = {0, 0, 0};
    wv_emit(log, MU_OBJ_CALL_AFTER_DRAW, k, a, 3);
}
int mu_world_after_pass_ex(mu_obj_world *w, const mu_obj_render_inputs *in, const mu_world_after_inputs *a,
                           int32_t *counter, mu_obj_log *log)
{
    if (!mu_world_after_gate(in->world, a->class_flag))
        return MU_OBJ_UNSUPPORTED;
    const float bias = in->world == 10 ? -10.0f : 0.0f;
    if (counter) {
        if (*counter > 40)
            *counter = 0;
        ++*counter;
    }
    /* 0x009a645f: world 0x27 outside tower states 3..5 draws only type 0x4be */
    const int tower = in->world == 0x27 && (a->tower_state < 3 || a->tower_state > 5);
    const float block = in->world == 0x86 ? -300.0f : -180.0f;   /* 0x00d8b139 */
    for (int32_t i = 0; i < 16; ++i)
        for (int32_t j = 0; j < 16; ++j) {
            const int32_t s = i * 16 + j;
            w->block_visible[s] = (uint8_t)mu_terrain_test_frustum_2d(
                in->x2d, in->y2d, in->scene_state, (float)(i * 16 + 8), (float)(j * 16 + 8), block);
            for (int32_t k = w->head[s]; k >= 0; k = w->next[k]) {
                uint8_t *o = w->objects[k];
                if (tower) {
                    if (mu_obj_i32(o, MU_OBJF_TYPE) == 0x4be)
                        after_draw(log, k);
                    continue;
                }
                if (mu_world_after_select(o, in)) {   /* may rewrite the range (class 142) */
                    o[MU_OBJF_VISIBLE] = (uint8_t)own_range(o, in, mu_obj_f32(o, MU_OBJF_RANGE) + bias);
                    after_draw(log, k);
                    continue;
                }
                if ((!w->block_visible[s] && !in->top_view) || !o[MU_OBJF_LIVE] || o[MU_OBJF_AFTER_CHARACTER] != 1)
                    continue;
                o[MU_OBJF_VISIBLE] = (uint8_t)own_range(o, in, mu_obj_f32(o, MU_OBJF_RANGE) + bias);
                if (!o[MU_OBJF_VISIBLE] && !in->top_view)
                    continue;
                /* world 2 type 0x64: hero level >= 0x35 for the master class (0x0139d89f == 1), else 0x50 */
                if (in->world == 2 && mu_obj_i32(o, MU_OBJF_TYPE) == 0x64 &&
                    a->level < (a->master_class ? 0x35 : 0x50))
                    continue;
                after_draw(log, k);
            }
        }
    return MU_OBJ_OK;
}
int mu_world_after_pass(mu_obj_world *w, const mu_obj_render_inputs *in, int32_t *counter, mu_obj_log *log)
{
    const mu_world_after_inputs a = {(uint8_t)mu_world_class_after(in->world), 0, 0, 0};
    return mu_world_after_pass_ex(w, in, &a, counter, log);
}
int mu_world_after_render(uint8_t *o, int32_t i, int32_t w, float time, mu_obj_log *l, mu_world_bone_fn bone,
                          void *c)
{
    if (w == 3 && mu_obj_i32(o, MU_OBJF_TYPE) == 0x13) {
        wv_body(o, i, l);
        return MU_OBJ_OK;
    }
    if (w == 0x33) {
        int status = mu_elbeland_after(o, i, time, l);
        mu_elbeland_after_sprites(o, i, bone, c, l);
        return status;
    }
    if (w == 0x39 || w == 0x3a)
        return mu_raklion_after(o, i, time, l);
    if (w == 0x50 || w == 0x51)
        return mu_karutan_after(o, i, time, l);
    if (w >= 0x80 && w <= 0x82)
        return mu_abyss_after(w, o, i, w, l) ? MU_OBJ_OK : MU_OBJ_UNSUPPORTED;
    return MU_OBJ_UNSUPPORTED;
}
/* RENDER-WORLDS-AFTER: the world tests of the world-group hooks CreateObject (0x016d99c4..0x016d9aa8) and
 * MoveObject (0x01801554..0x01801653) call before the world manager's class create/move, which is last in
 * both chains. Nonzero when the test at `address` passes in world w. */
int mu_world_chain_predicate(uint32_t address, int32_t w)
{
    switch (address) {
    case 0x9dacb8: return (w >= 0x12 && w <= 0x17) || w == 0x35 || w == 0x61;   /* Chaos Castle */
    case 0x9b0418: return (w >= 0x18 && w <= 0x1d) || w == 0x24;                /* Kalima */
    case 0x95fb7c: return w == 0x1e;
    case 0xdfbbbb: return w == 0x1f;
    case 0xd61f81: return w == 0x21 || w == 0x36;
    case 0xdabe97: return w == 0x22;
    case 0xe74a3b: return w == 0x25;
    case 0xe7dcd7: return w == 0x28;
    case 0xe843df: return w == 0x26;
    case 0xe84513: return w == 0x27;
    case 0xd53d11: return w == 0x29;
    case 0xd53d32: return w == 0x2a;
    case 0xe309a7: return w == 0x33 || w == 0x49 || w == 0x4a;
    case 0xe309d9: return w == 0x49 || w == 0x4a;
    case 0xe5f48a: return w == 0x38;
    case 0x95fba9: return w == 0x2d || w == 0x2e || w == 0x2f || w == 0x30 || w == 0x31 || w == 0x32 ||
                          w == 0x62 || w == 0x63;
    default: return 0;
    }
}
