/* Old Kethotum, world 135 (0x87), vtable 0x01aaaf18. Create 0x00e3a4dc, move 0x00e3a719, visual 0x00e3c137;
 * world predicate 0x00e3dd42. */
#include "worlds_p_internal.h"
#include "world_visual_internal.h"
#include "charsel_world.h"
int mu_old_kethotum_create(uint8_t *o, int32_t world, mu_wp_model *m, mu_obj_rand_fn rnd, void *c)
{
    if (world != 0x87 || !o)
        return 0;
    wp_speeds(m);
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    if (t >= 0xa0 && t <= 0xaa)
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
    switch (t) {
    case 0x17: case 0x26: case 0x5a: case 0x66: case 0x6a:
        mu_obj_set_f32(o, MU_OBJF_RANGE, -300.0f);
        break;
    case 0x15: case 0x3b:
        mu_obj_set_f32(o, MU_OBJF_RANGE, -600.0f);
        break;
    default:
        break;
    }
    switch (t) {
    case 0x0f: case 0x10:
        mu_obj_set_i32(o, WP_PHASE, rnd(c) % 10 * 300);
        break;
    case 0x12: case 0x15: case 0x18: case 0x87: case 0x89: case 0x8a:
        o[MU_OBJF_AFTER_CHARACTER] = 1;
        break;
    case 0x16: case 0x29: case 0x5c: case 0x74:
        m->speed[1] = m->speed[1] * 1.03f;
        o[MU_OBJF_AFTER_CHARACTER] = 1;
        mu_obj_set_i32(o, WP_SWING_LIMIT, rnd(c) % 10 + 15);
        break;
    case 0x77: case 0x81:
        m->speed[1] = m->speed[1] * 1.01f;
        break;
    default:
        break;
    }
    return 1;
}

int mu_old_kethotum_move(uint8_t *o, int32_t i, const mu_wp_move_inputs *in, mu_obj_log *log)
{
    if (in->world != 0x87 || !o)
        return 0;
    switch (mu_obj_i32(o, MU_OBJF_TYPE)) {
    case 0x17:
        wp_near_sound(o, i, in, 800.0f, 0x557, log);
        return 0;
    case 0x28:
        mu_obj_set_f32(o, MU_OBJF_BLEND_V, mu_obj_f32(o, MU_OBJF_BLEND_V) - 0.02f);
        return wp_near_sound(o, i, in, 1300.0f, 0x54c, log);
    case 0x16: case 0x29: case 0x5c: case 0x74:
        return wp_swing(o, i, in, log);
    case 0x77: case 0x81:
        return wp_gate(o, i, in, log);
    case 0xa0:
        return wp_near_sound(o, i, in, 400.0f, 0x54b, log);
    default:
        return 0;
    }
}

static void ok_particle(int32_t i, int32_t id, const float pos[3], const float angle[3], const float light[3],
                        int32_t sub, float scale, mu_obj_log *log)
{
    mu_obj_event *e = wb_event(log, MU_OBJ_CALL_PARTICLE, i);
    wb_arg(e, (uint32_t)id); wb_vec(e, pos); wb_vec(e, angle); wb_vec(e, light);
    wb_arg(e, (uint32_t)sub); wb_float(e, scale); wb_arg(e, 0);
}
int mu_old_kethotum_visual(const uint8_t *o, int32_t i, int present, float time, mu_obj_rand_fn rnd,
                           mu_world_bone_fn bone, void *c, mu_obj_log *log)
{
    if (!o || !present)
        return 0;
    const float zero[3] = {0, 0, 0};
    switch (mu_obj_i32(o, MU_OBJF_TYPE)) {
    case 0x0f: {
        if (!bone)
            return 0;
        const float wave = (float)sin((double)((float)(wb_int(time) % 3000) * wp_bits(0x3a89304fu)));
        float pos[3];
        bone(c, 4, zero, pos);
        if (rnd(c) % 7 == 0) {
            const float light[3] = {0.6f, 1.0f, 1.0f};
            float angle[3];
            wb_get(o, MU_OBJF_ANGLE, angle);
            ok_particle(i, 0x7efa, pos, angle, light, 2, 0.25f, log);
        }
        const float glow[3] = {0.2f, 0.65f, 0.65f};
        wv_sprite(i, 0x7ef7, pos, 1.5f + wave * 0.1f, glow, log);
        const float rise = (float)sin((double)(time * 0.001f + (float)mu_obj_i32(o, WP_PHASE))) - 0.5f;
        if (rise > 0.0f) {
            const float up[3] = {0, 0, 1}, light[3] = {0.3f, 0.95f, 0.95f};
            ok_particle(i, 0x7f26, pos, up, light, 0xe, 0.06f, log);
        }
        return 0;
    }
    case 0x10: {
        if (!bone)
            return 0;
        static const int32_t bones[6] = {5, 6, 7, 11, 14, 15};
        const float dim[3] = {0.15f, 0.15f, 0.15f};
        for (int k = 0; k < 6; ++k) {
            const float x = (float)((double)((float)mu_obj_i32(o, WP_PHASE) + time) * 0.0002 * (double)k);
            const float wave = (float)sin((double)x);
            /* 0x0184f8ff compares with zero, so negative zero stays negative. */
            const float pulse = (wave < 0.0f ? -wave : wave) * 0.4f;
            const float light[3] = {pulse * 1.3f, pulse * 1.3f, pulse * 1.9f};
            float pos[3];
            bone(c, bones[k], zero, pos);
            wv_sprite(i, 0x7f26, pos, 2.0f, light, log);
            wv_sprite(i, 0x7f26, pos, 1.5f, dim, log);
        }
        return 0;
    }
    case 0xa5:
        if (rnd(c) % 100 == 0) {
            const float light[3] = {1, 1, 1};
            float pos[3], angle[3];
            wb_get(o, MU_OBJF_POSITION, pos); wb_get(o, MU_OBJF_ANGLE, angle);
            mu_obj_event *e = wb_event(log, MU_OBJ_CALL_EFFECT, i);
            wb_arg(e, 0x59a); wb_vec(e, pos); wb_vec(e, angle); wb_vec(e, light);
            wb_arg(e, 3); wb_arg(e, 1); wb_float(e, 0.0f);
        }
        return 0;
    default:
        return 0;
    }
}
