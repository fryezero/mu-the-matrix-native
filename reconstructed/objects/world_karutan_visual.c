/* Karutan handler slot 0x34, 0x00e1409c..0x00e14277, brazier 113. */
#include "world_visual_internal.h"
#include <math.h>
#include "worlds_b_internal.h"
#include "world_visual_slots.h"
#include "world_visual_slots2.h"
int mu_karutan_flames(const uint8_t *o, int32_t i, mu_obj_rand_fn rnd, void *c, mu_obj_log *l)
{
    if (mu_obj_i32(o, MU_OBJF_TYPE) != 0x71)
        return MU_OBJ_UNSUPPORTED;
    float pos[3];
    memcpy(pos, o + MU_OBJF_POSITION, 12);
    const float warm[3] = {1, 0.2f, 0}, white[3] = {1, 1, 1};
    wv_sprite(i, 0x7ef7, pos, 2.0f * mu_obj_f32(o, MU_OBJF_SCALE), warm, l);
    const int32_t choice = rnd(c) % 3;
    if (choice == 0)
        wv_particle(o, i, 0x8084, 0, white, 0, l);
    else if (choice == 1)
        wv_particle(o, i, 0x806e, 4, white, 0, l);
    else if (choice == 2)
        wv_particle(o, i, 0x8085, 0, white, 0, l);
    return MU_OBJ_OK;
}

/* RENDER-WORLDS-KARUTAN: the class slots of world-80 (worlds 80/81, vtable 0x01aa9a4c), custom 0x00e14596 (slot
 * 0x38, 969 instructions) and after 0x00e1543e (slot 0x3c, 502), whole. Their own code, not Test Area 121's: see
 * docs/research/client-worlds-karutan.md. The world manager passes types 0..300 only, so the custom slot's types
 * 0x877 and 0x87a..0x87d (0x00e149ac, 0x00e14aa3, 0x00e14b9a, 0x00e14d49, 0x00e14ff2) are left out. */
static int karutan_world(int32_t w) { return w == 80 || w == 81; }   /* 0x00e18ae9 */
int mu_slots_karutan_custom(const slot *s, int32_t world)
{
    /* 0x00e145b5..0x00e145ef: 0x00e18ae9 (80, 81), else 0x009dad2c (102), else the singleton 0x00c7dfcc's
     * 0x009d3e63 (103..106); all false answers 0 */
    if (!karutan_world(world) && world != 102 && (world < 103 || world > 106))
        return 0;
    switch (mu_obj_i32(s->o, MU_OBJF_TYPE)) {
    case 1: case 3: case 0x36: case 0x37: case 0x38: case 0x39: case 0x3a: case 0x3e: case 0x3f: case 0x77:
        set_after(s);   /* 0x00e146ce */
        return 1;
    case 0x42:   /* 0x00e146dc: from frame 19, SetAction 0x012affa4(o, rand() % 10 == 0); then the after flag */
        if (mu_obj_f32(s->o, MU_OBJF_FRAME) >= 19.0f)
            mu_obj_set_action(s->o, s->model->action_count,
                              s->model->rand_fn(s->model->rand_context) % 10 == 0 ? 1 : 0);
        set_after(s);
        return 1;
    case 0x81: {   /* 0x00e14727: the body, then mesh 1 grey-pulsed with 0x85bb and again with flags 0x44 */
        body(s, 2, BM(s), BL(s), U(s), V(s), -1);
        const float r = mu_obj_f32(s->b, MU_MDL_COLOR), g = mu_obj_f32(s->b, MU_MDL_COLOR + 4),
                    bl = mu_obj_f32(s->b, MU_MDL_COLOR + 8);   /* the vector 0x0095ea8e keeps the body colour */
        grey(s, wave(s, -2.5f) * 0.3f + 0.7f);                  /* 0x0185bdc4(-2.5, 0) */
        mesh(s, 1, 2, A(s), 1, BL(s), U(s), V(s), 0x85bb);
        color(s, r, g, bl);
        mesh(s, 1, 0x44, A(s), 1, BL(s), U(s), V(s), -1);
        return 1;
    }
    default:
        return 0;
    }
}
/* The after slot: world test 0x00e18ae9 only. The client's after pass 0x016d6949 runs in 0x50/0x51 (its world list). */
void mu_slots_karutan_after(const slot *s, int32_t world)
{
    if (!karutan_world(world))
        return;
    const int32_t t = mu_obj_i32(s->o, MU_OBJF_TYPE);
    switch (t) {
    case 1:   /* 0x00e154db */
        for (int32_t m = 1; m <= 3; ++m)
            mesh(s, m, 2, A(s), BM(s), BL(s), 0.0f, 0.0f, -1);
        mesh(s, 0, 0x42, A(s), BM(s), BL(s), 0.0f, 0.0f, -1);
        break;
    case 3: case 0x38: case 0x3e:   /* 0x00e15601 */
        body_std(s, H(s));
        break;
    case 0x36:   /* 0x00e15663 */
        mesh(s, 0, 0x42, A(s), 0, (csin(s->time * 0.002f) + 0.5f) * 0.5f + 1.0f, 0.0f, 0.0f, -1);
        break;
    case 0x37: case 0x39:   /* 0x00e156e8: StreamMesh 0 around a v scroll of (int)WorldTime % 10000 */
        stream(s, 0);
        mesh(s, 0, 0x42, A(s), BM(s), BL(s), U(s), tmod(s, 10000, 0.0001f, 0), -1);
        stream(s, 0xff);
        break;
    case 0x3a: case 0x3f: case 0x77: {   /* 0x00e1576a, 0x00e158bf, 0x00e15aa6 */
        const float p = (csin(s->time * 0.001f) + 1.0f) * 0.5f;
        if (t == 0x3f) {
            mesh(s, 0, 0x42, A(s), 0, BL(s), 0.0f, 0.0f, -1);
            mesh(s, 1, 2, A(s), BM(s), BL(s), 0.0f, 0.0f, -1);
            mesh(s, 2, 0x42, A(s), 2, p, 0.0f, 0.0f, -1);
            mesh(s, 3, 2, A(s), BM(s), BL(s), 0.0f, 0.0f, -1);
            break;
        }
        mesh(s, 0, 2, A(s), BM(s), BL(s), 0.0f, 0.0f, -1);
        mesh(s, 1, 0x42, A(s), 1, p, 0.0f, 0.0f, -1);
        if (t == 0x3a) {
            mesh(s, 3, 2, A(s), BM(s), BL(s), 0.0f, 0.0f, -1);
            mesh(s, 2, 0x42, A(s), BM(s), BL(s), 0.0f, 0.0f, -1);
        }
        break;
    }
    case 0x42:   /* 0x00e15a10 */
        mesh(s, 0, 2, A(s), BM(s), BL(s), 0.0f, 0.0f, -1);
        mesh(s, 1, 0x42, A(s), BM(s), BL(s), 0.0f, 0.0f, -1);
        break;
    default:
        break;
    }
}
/* Slot 0x24 0x00e13a5c: LoadBitmap("Object144\\sdsaferzone14B01_R.jpg", 0x85bb, 0x2601, 0x2900, 1, 0), type 0x81's */
int mu_slots_karutan_bitmap(int32_t world, int32_t index, const char **path, uint32_t *filter, uint32_t *wrap)
{
    if (!karutan_world(world) || index != 0x85bb)
        return 0;
    *path = "Object144\\sdsaferzone14B01_R.jpg";
    *filter = 0x2601;
    *wrap = 0x2900;
    return 1;
}
int32_t mu_slots_karutan_bitmaps(int32_t world, int32_t type, int32_t *out, int32_t room)
{
    if (!karutan_world(world) || type != 0x81 || room <= 0)
        return 0;
    out[0] = 0x85bb;
    return 1;
}

/* Complete primary methods 0x00e13a87/0x00e13a9e/0x00e13be4.
 * TransformPosition is supplied by the current object's posed model. */
int mu_karutan_create(const uint8_t *o)
{
    (void)o;
    return 0; /* create */
}
int mu_karutan_move(uint8_t *o, int32_t i, const mu_obj_move_inputs *in, mu_obj_log *log)
{
    if (in->world != 80 && in->world != 81)
        return 0;
    switch (mu_obj_i32(o, MU_OBJF_TYPE)) {
    case 0x71: {
        const float s = (float)(in->rand_fn(in->context) % 4 + 3) * 0.1f;
        const float light[3] = {s, s * 0.6f, s * 0.2f};
        mu_obj_event *e = wb_event(log, MU_OBJ_CALL_ADD_LIGHT, i);
        wb_float(e, mu_obj_f32(o, MU_OBJF_POSITION));
        wb_float(e, mu_obj_f32(o, MU_OBJF_POSITION + 4));
        wb_vec(e, light);
        wb_arg(e, 3);
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
        return 1;
    }
    case 0x72: case 0x73: case 0x74: case 0x76:
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
        return 1;
    case 0x87: {
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
        mu_obj_event *e = wb_event(log, MU_OBJ_CALL_SOUND, i);
        wb_arg(e, 0x5a5); wb_arg(e, 0); wb_arg(e, 0);
        return 1;
    }
    default: return 0;
    }
}
static void karutan_particle(const uint8_t *o, int32_t i, int32_t id, int32_t sub,
                             const float light[3], float scale, int owner, mu_obj_log *log)
{
    mu_obj_event *e = wb_event(log, MU_OBJ_CALL_PARTICLE, i);
    float p[3], a[3];
    wb_get(o, MU_OBJF_POSITION, p); wb_get(o, MU_OBJF_ANGLE, a);
    wb_arg(e, (uint32_t)id); wb_vec(e, p); wb_vec(e, a); wb_vec(e, light);
    wb_arg(e, (uint32_t)sub); wb_float(e, scale); wb_arg(e, (uint32_t)owner);
}
int mu_karutan_visual(const uint8_t *o, int32_t i, int32_t world, float time,
                       mu_obj_rand_fn random, mu_world_bone_fn bone, void *context, mu_obj_log *log)
{
    if (world != 80 && world != 81)
        return 0;
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    if (t == 66 || t == 72) {
        if (!bone) return 1; /* Host records a missing current pose, never reuses stale bones. */
        const float w = (float)sin((double)(float)((double)time * 0.0004));
        /* The original comparison preserves negative zero. */
        const float pulse = (w < 0.0f ? -w : w) * 0.4f;
        if (t == 66) {
            const float light[3] = {pulse * 1.9f, pulse * 1.1f, pulse * 1.1f};
            for (int k = 0; k < 2; ++k) {
                const float local[3] = {10, 0, k ? 6.0f : -6.0f};
                float pos[3]; bone(context, 13 + k, local, pos);
                wv_sprite(i, 0x7f6b, pos, 1.2f, light, log);
            }
        } else {
            const float light[3] = {pulse * 1.3f, pulse * 1.3f, pulse * 1.9f};
            const float dim[3] = {0.15f, 0.15f, 0.15f}, local[3] = {20, 0, 0};
            for (int k = 0; k < 2; ++k) {
                float pos[3]; bone(context, 11 - k * 4, local, pos);
                wv_sprite(i, k ? 0x7f26 : 0x7ef7, pos, k == 0 ? 2.0f : 4.0f, light, log);
                wv_sprite(i, 0x7f26, pos, 1.5f, dim, log);
            }
        }
        return 1;
    }
    if (t == 113) {
        mu_karutan_flames(o, i, random, context, log);
        return 1;
    }
    const float scale = mu_obj_f32(o, MU_OBJF_SCALE);
    if (t == 114) {
        const float light[3] = {0.2f, 0.2f, 0.2f};
        if (random(context) % 3 == 0)
            karutan_particle(o, i, 0x801c, 16, light, scale, 0, log);
    } else if (t == 115) {
        const float light[3] = {0.04f, 0.04f, 0.04f};
        if (mu_obj_i32(o, MU_OBJF_HIDDEN_MESH) != -2)
            for (int j = 0; j < 20; ++j)
                karutan_particle(o, i, 0x7f89, 0, light, scale, 1, log);
    } else if (t == 116) {
        if (random(context) % 8 == 0) {
            const float light[3] = {0.5f, 0.9f, 0.5f};
            float object_light[3]; wb_get(o, MU_OBJF_LIGHT, object_light);
            karutan_particle(o, i, 0x7f5a, 69, light, scale, 0, log);
            karutan_particle(o, i, 0x7f5a, 13, object_light, mu_obj_f32(o, MU_OBJF_SCALE) * 2.0f, 1, log);
        }
    } else if (t == 118) {
        const float light[3] = {0.27f, 0.2f, 0.1f};
        if (mu_obj_i32(o, MU_OBJF_HIDDEN_MESH) != -2)
            for (int j = 0; j < 4; ++j)
                karutan_particle(o, i, 0x7f89, 0, light, scale, 1, log);
    } else return 0;
    return 1;
}
