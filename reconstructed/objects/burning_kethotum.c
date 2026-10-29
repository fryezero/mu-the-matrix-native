/* Burning Kethotum, world 136 (0x88), vtable 0x01aa6d38. Create 0x00d9381e, move 0x00d93b31, visual 0x00d97186;
 * world predicate 0x00d99c0f. Move shares the Old Kethotum template and adds braziers 0xa5 and the 0xb5 cycle. */
#include "worlds_p_internal.h"
#include "world_visual_internal.h"
int mu_burning_kethotum_create(uint8_t *o, int32_t world, mu_wp_model *m, mu_obj_rand_fn rnd, void *c)
{
    if (world != 0x88 || !o)
        return 0;
    wp_speeds(m);
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    if (t >= 0xa0 && t <= 0xaa)
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
    switch (t) {
    case 2: case 0x17: case 0x18: case 0x26: case 0x5a: case 0x66: case 0x6a: case 0x86: case 0x87: case 0xb3:
        mu_obj_set_f32(o, MU_OBJF_RANGE, -300.0f);
        break;
    case 0x15: case 0x3b:
        mu_obj_set_f32(o, MU_OBJF_RANGE, -600.0f);
        break;
    default:
        break;
    }
    switch (t) {
    case 0x12: case 0x15: case 0x18: case 0x19: case 0x6c:
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
    case 0x99: case 0x9a: case 0x9b: case 0x9c:
        mu_obj_set_i32(o, 0x60, (rnd(c) % 18 + 1) * 10);
        break;
    case 0xb5:
        mu_obj_set_i32(o, WP_SWING_LIMIT, rnd(c) % 4 + 1);
        m->speed[1] = m->speed[1] * 0.9f;
        o[MU_OBJF_AFTER_CHARACTER] = 1;
        break;
    default:
        break;
    }
    return 1;
}

/* Type 0xa5: warm flicker, range by scale. */
static int brazier(const uint8_t *o, int32_t i, const mu_wp_move_inputs *in, mu_obj_log *log)
{
    wp_near_sound(o, i, in, 400.0f, 0x54b, log);
    const float s = (float)(in->rand_fn(in->context) % 4 + 3) * 0.1f;
    const float scale = mu_obj_f32(o, MU_OBJF_SCALE);
    const int32_t range = 1.15f > scale ? 1 : 1.35 > (double)scale ? 2 : 3;
    wb_light(log, i, o, s, s * 0.6f, s * 0.2f, range);
    return 1;
}

/* Type 0xb5: the four red .ein effects (when none is attached), then a rest/rise/fall cycle on actions 0..2.
 * +0x38 is the glow flag, +0xc8 its level. */
static const float ein_life[4] = {35.0f, 50.0f, 50.0f, 200.0f};
static int cycle(uint8_t *o, int32_t i, const mu_wp_move_inputs *in, mu_obj_log *log)
{
    if (!in->has_effects) {
        const float base[3] = {0, 0, 0}, raised[3] = {0, 0, -20.0f};
        for (int k = 0; k < 4; ++k) {
            mu_obj_event *e = wb_event(log, MU_WP_EIN_EFFECT, i);
            wb_arg(e, (uint32_t)k); wb_vec(e, raised); wb_vec(e, base); wb_float(e, ein_life[k]);
        }
        if ((in->effects_valid & 15) == 15)
            for (int k = 0; k < 4; ++k) {
                mu_obj_event *e = wb_event(log, MU_WP_EIN_ATTACH, i);
                wb_arg(e, (uint32_t)k); wb_arg(e, 0x14); wb_arg(e, 1); wb_arg(e, 0); wb_float(e, 0.0f);
            }
    }
    const mu_wp_model *m = in->model;
    if (!m)
        return 0;
    const float last = (float)(m->keys[mu_obj_u16(o, MU_OBJF_ACTION)] - 1);
    o[0x38] = 0;
    const float dt = in->frame_time;
    switch (mu_obj_u16(o, MU_OBJF_ACTION)) {
    case 0:
        mu_obj_set_f32(o, 0xc8, 0.0f);
        if (mu_obj_f32(o, MU_OBJF_FRAME) > 3.0f && 1200.0f > wp_distance(o, in))
            wp_sound(log, i, 0x559);
        break;
    case 1:
        mu_obj_set_f32(o, 0xc8, dt * 0.5f + mu_obj_f32(o, 0xc8));
        if (mu_obj_f32(o, 0xc8) > 0.65f)
            o[0x38] = 1;
        break;
    case 2: {
        const float f = mu_obj_f32(o, MU_OBJF_FRAME);
        if (f > 7.0f && 8.0f > f)
            wp_near_sound(o, i, in, 1200.0f, 0x55a, log);
        o[0x38] = 1;
        mu_obj_set_f32(o, 0xc8, mu_obj_f32(o, 0xc8) - dt * 0.4f);
        if (last / 5.0f > mu_obj_f32(o, MU_OBJF_FRAME)) {
            mu_obj_set_f32(o, 0xc8, dt * 0.5f + mu_obj_f32(o, 0xc8));
            if (mu_obj_f32(o, 0xc8) >= 1.0f)
                mu_obj_set_f32(o, 0xc8, 1.0f);
        } else if (0.1f > mu_obj_f32(o, 0xc8)) {
            o[0x38] = 0;
        }
        break;
    }
    default:
        break;
    }
    const uint16_t a = mu_obj_u16(o, MU_OBJF_ACTION);
    const float s = m->speed[a] + dt;
    const float limit = (float)(m->keys[a] - 1);
    const float f = mu_obj_f32(o, MU_OBJF_FRAME);
    if (a == 0) {
        if (f >= limit - s) {
            wp_set_action(o, m, 1);
            mu_obj_set_f32(o, MU_OBJF_FRAME, 0.0f);
        }
    } else if (a == 1) {
        if (f >= limit) {
            if (mu_obj_i32(o, WP_SWINGS) >= mu_obj_i32(o, WP_SWING_LIMIT))
                wp_set_action(o, m, 2);
            mu_obj_set_i32(o, WP_SWINGS, mu_obj_i32(o, WP_SWINGS) + 1);
            mu_obj_set_f32(o, MU_OBJF_FRAME, s);
        }
    } else if (a == 2) {
        if (f >= limit - s) {
            mu_obj_set_i32(o, WP_SWING_LIMIT, in->rand_fn(in->context) % 4 + 1);
            mu_obj_set_i32(o, WP_SWINGS, 0);
            wp_set_action(o, m, 0);
            mu_obj_set_f32(o, MU_OBJF_FRAME, 0.0f);
        }
    }
    return 1;
}

int mu_burning_kethotum_move(uint8_t *o, int32_t i, const mu_wp_move_inputs *in, mu_obj_log *log)
{
    if (in->world != 0x88 || !o)
        return 0;
    switch (mu_obj_i32(o, MU_OBJF_TYPE)) {
    case 0x19:
        wp_near_sound(o, i, in, 800.0f, 0x558, log);
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
    case 0xa5:
        return brazier(o, i, in, log);
    case 0xb5:
        return cycle(o, i, in, log);
    default:
        return 0;
    }
}

/* Type 0xa5: a scale-2 warm flare and one of three fire particles. */
int mu_burning_kethotum_visual(const uint8_t *o, int32_t i, int present, mu_obj_rand_fn rnd, void *c, mu_obj_log *log)
{
    if (!o || !present || mu_obj_i32(o, MU_OBJF_TYPE) != 0xa5)
        return 0;
    float pos[3];
    wb_get(o, MU_OBJF_POSITION, pos);
    const float warm[3] = {1.0f, 0.2f, 0.0f}, white[3] = {1, 1, 1};
    wv_sprite(i, 0x7ef7, pos, 2.0f * mu_obj_f32(o, MU_OBJF_SCALE), warm, log);
    const int32_t choice = rnd(c) % 3;
    if (choice == 0)
        wv_particle(o, i, 0x8084, 0, white, 0, log);
    else if (choice == 1)
        wv_particle(o, i, 0x806e, 4, white, 0, log);
    else
        wv_particle(o, i, 0x8085, 0, white, 0, log);
    return 0;
}
