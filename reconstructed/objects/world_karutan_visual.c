/* Karutan handler slot 0x34, 0x00e1409c..0x00e14277, brazier 113. */
#include "world_visual_internal.h"
#include <math.h>
#include "worlds_b_internal.h"
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

/* Slot 0x38 0x00e146ce; 66 also changes action above frame 35, outside this flag slice. */
int mu_karutan_defer(uint8_t *o)
{
    switch (mu_obj_i32(o, MU_OBJF_TYPE)) {
    case 1:
    case 3:
    case 0x36:
    case 0x37:
    case 0x38:
    case 0x39:
    case 0x3a:
    case 0x3e:
    case 0x3f:
    case 0x42:
    case 0x77:
        o[MU_OBJF_AFTER_CHARACTER] = 1;
        return 1;
    default:
        return 0;
    }
}
int mu_karutan_after(uint8_t *o, int32_t i, float time, mu_obj_log *l)
{
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    const float light = mu_obj_f32(o, MU_OBJF_BLEND_LIGHT), u = mu_obj_f32(o, MU_OBJF_BLEND_U),
                v = mu_obj_f32(o, MU_OBJF_BLEND_V);
    const int32_t b = mu_obj_i32(o, MU_OBJF_BLEND_MESH);
    switch (t) {
    case 3:
    case 0x38:
    case 0x3e:
        wv_body(o, i, l);
        break;
    case 1:
        for (int k = 1; k <= 3; ++k)
            wv_mesh(o, i, k, 2, b, light, 0, 0, l);
        wv_mesh(o, i, 0, 0x42, b, light, 0, 0, l);
        break;
    case 0x36: {
        const float pulse = ((float)sin((double)(time * 0.002f)) + 0.5f) * 0.5f + 1.0f;
        wv_mesh(o, i, 0, 0x42, 0, pulse, 0, 0, l);
        break;
    }
    case 0x3a:
    case 0x3f:
    case 0x77: {
        const float pulse = ((float)sin((double)(time * 0.001f)) + 1.0f) * 0.5f;
        if (t == 0x3f)
            wv_mesh(o, i, 0, 0x42, 0, light, 0, 0, l);
        else
            wv_mesh(o, i, 0, 2, b, light, 0, 0, l);
        if (t == 0x77) {
            wv_mesh(o, i, 1, 0x42, 1, pulse, 0, 0, l);
            break;
        }
        wv_mesh(o, i, 1, t == 0x3f ? 2u : 0x42u, t == 0x3f ? b : 1, t == 0x3f ? light : pulse, 0, 0, l);
        if (t == 0x3a) {
            wv_mesh(o, i, 3, 2, b, light, 0, 0, l);
            wv_mesh(o, i, 2, 0x42, b, light, 0, 0, l);
        } else {
            wv_mesh(o, i, 2, 0x42, 2, pulse, 0, 0, l);
            wv_mesh(o, i, 3, 2, b, light, 0, 0, l);
        }
        break;
    }
    case 0x42:
        wv_mesh(o, i, 0, 2, b, light, 0, 0, l);
        wv_mesh(o, i, 1, 0x42, b, light, 0, 0, l);
        break;
    case 0x37:
    case 0x39:
        wv_mesh(o, i, 0, 0x42, b, light, u, (float)((int32_t)time % 10000) * 0.0001f, l);
        break;
    default:
        return MU_OBJ_UNSUPPORTED;
    }
    (void)v;
    return MU_OBJ_OK;
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
        const float wave = (float)sin((double)(float)((double)time * 0.0004));
        /* The original comparison preserves negative zero. */
        const float pulse = (wave < 0.0f ? -wave : wave) * 0.4f;
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
