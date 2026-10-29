/* Kanturu Underground, world 137. Create 0x00e08cd8, move 0x00e08f8a, visual 0x00e0a4bb; predicate 0x00e0df03. */
#include "worlds_p2.h"
#include "worlds_b_internal.h"
#include "icarus.h"
#include "../movement/client_movement.h"
int mu_kanturu_ug_create(uint8_t *o, int32_t index, int32_t world, mu_obj_rand_fn random, void *ctx,
                         mu_obj_log *log)
{
    if (world != 137 || !o) return 0;
    o[MU_OBJF_LIGHT_DYNAMIC] = 0;
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    mu_obj_event *e = wb_event(log, MU_OBJ_CALL_PLAY_SPEED, index);   /* every action of the model: 0.3 */
    wb_arg(e, (uint32_t)t); wb_arg(e, MU_OBJ_PLAY_SPEED_ALL); wb_float(e, 0.3f);
    switch (t) {
    case 40: case 45: case 46: case 47: case 48: case 49: case 50: case 51: case 52: case 54: case 55: case 56:
    case 65: case 66: case 67: case 68: case 106: case 111: case 114: case 115: case 116: case 117: case 120:
    case 121: case 122:
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2); break;
    default: break;
    }
    if (t == 3) wb_arg(wb_event(log, MU_OBJ_CALL_REGISTER, index), 0);
    if (t >= 125 && t <= 127) mu_obj_set_i32(o, 0x34, random(ctx) % 30 + 20);
    switch (t) {
    case 0: case 2: case 9: case 17: case 18: case 22: case 25: case 27: case 28: case 42: case 57: case 59:
    case 60: case 64: case 76: case 79: case 81: case 85: case 92: case 93: case 94: case 95: case 96:
        mu_obj_set_f32(o, MU_OBJF_RANGE, -300.0f); break;
    default: break;
    }
    return 1;
}
static void set_action(uint8_t *o, int32_t count, int32_t action)   /* SetAction 0x012affa4 */
{
    uint16_t a = mu_obj_u16(o, MU_OBJF_ACTION), prior = mu_obj_u16(o, MU_OBJF_PRIOR_ACTION);
    float frame = mu_obj_f32(o, MU_OBJF_FRAME), prior_frame = mu_obj_f32(o, MU_OBJF_PRIOR_FRAME);
    mu_move_set_action(&a, &prior, &frame, &prior_frame, count, action);
    mu_obj_set_u16(o, MU_OBJF_ACTION, a); mu_obj_set_u16(o, MU_OBJF_PRIOR_ACTION, prior);
    mu_obj_set_f32(o, MU_OBJF_FRAME, frame); mu_obj_set_f32(o, MU_OBJF_PRIOR_FRAME, prior_frame);
}
int mu_kanturu_ug_move(uint8_t *o, int32_t index, const mu_obj_move_inputs *in, mu_kanturu_ug_action_fn table,
                       float frame_time, mu_obj_log *log)
{
    if (in->world != 137 || !o) return 0;
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    switch (t) {
    case 10: {
        mu_obj_set_f32(o, MU_OBJF_VELOCITY, 0.04f);
        float l = (float)sin((double)(in->time * 0.0015f)) + 1.0f;
        if (0.1f >= l) l = 0.1f;
        else if (l >= 0.9f) l = 0.9f;
        mu_obj_set_f32(o, MU_OBJF_BLEND_LIGHT, l);
        return 1;
    }
    case 38: {
        const float l = (float)sin((double)(in->time * 0.001f)) + 1.0f;
        mu_obj_set_f32(o, MU_OBJF_BLEND_LIGHT, 1.0f > l ? l : 1.0f);
        return 1;
    }
    case 44:
        mu_obj_set_f32(o, MU_OBJF_VELOCITY, 0.02f);
        return 1;
    case 125: case 126: case 127: break;
    default: return 0;
    }
    if (!table) {   /* native host: after the animation tick */
        wb_event(log, MU_KANTURU_UG_ACTION_STEP, index);
        return 1;
    }
    const int32_t action = mu_obj_u16(o, MU_OBJF_ACTION);
    int32_t count = 0;
    int16_t keys = 0;
    float speed = 0.0f;
    if (!table(in->context, t, action, &count, &keys, &speed)) return 0;
    const float last = (float)keys - 1.0f, step = speed + frame_time;
    if (!(mu_obj_f32(o, MU_OBJF_FRAME) >= last - step)) return 1;
    static const struct { int16_t next, wait; } k[3] = {{1, 1}, {2, 25}, {3, 1}};
    int32_t counter = mu_obj_i32(o, 0x30);
    if (action > 3) return 1;
    if (counter >= mu_obj_i32(o, 0x34)) {
        set_action(o, count, action == 3 ? 0 : k[action].next);
        counter = 0;
        mu_obj_set_i32(o, 0x30, 0);
        mu_obj_set_i32(o, 0x34, action == 3 ? in->rand_fn(in->context) % 30 + 20 : k[action].wait);
    }
    mu_obj_set_i32(o, 0x30, counter + 1);
    return 1;
}
static void joint(mu_obj_log *log, int32_t i, uint32_t type, const float p[3], const float target[3],
                  const float a[3], uint32_t sub, uint32_t owner, float scale)
{
    mu_obj_event *e = wb_event(log, MU_ICARUS_JOINT, i);
    wb_arg(e, type); wb_vec(e, p); wb_vec(e, target); wb_vec(e, a);
    wb_arg(e, sub); wb_arg(e, owner); wb_float(e, scale);
}
int mu_kanturu_ug_visual(const uint8_t *o, int32_t i, int has_model, float time, mu_obj_rand_fn random,
                         mu_login_bone_fn bone, void *ctx, mu_obj_log *log)
{
    if (!o || !has_model) return 0;
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    const float scale = mu_obj_f32(o, MU_OBJF_SCALE);
    float p[3], a[3];
    wb_get(o, MU_OBJF_POSITION, p); wb_get(o, MU_OBJF_ANGLE, a);
    switch (t) {
    case 54: case 120: case 65: case 121: case 66: case 122: {
        const int first = t == 54 || t == 120, second = t == 65 || t == 121;
        if (random(ctx) % (first ? 20 : second ? 10 : 5) != 0) return 1;
        const float base = 30.0f * scale;
        const int32_t r = random(ctx), d = wb_int(10.0f * scale);
        if (d == 0) return 1;   /* the client divides by zero here; never requested */
        joint(log, i, 0x7f7d, p, p, a, first ? 14u : second ? 15u : 12u, (uint32_t)first, base + (float)(r % d));
        return 1;
    }
    case 8: case 92: case 93: case 94: case 95: case 96: break;
    default: return 0;
    }
    const float s = ((float)sin((double)(time * 0.001f)) + 1.0f) * 0.5f;
    const float zero[3] = {0, 0, 0}, light[3] = {s, s, s};
    float b[3] = {0, 0, 0};
    if (!bone) return 1;   /* no posed bones: the host counts the refusal */
    bone(ctx, 4, zero, b);
    mu_obj_event *e = wb_event(log, MU_OBJ_CALL_PARTICLE, i);
    wb_arg(e, 0x7f2b); wb_vec(e, b); wb_vec(e, a); wb_vec(e, light); wb_arg(e, 0); wb_float(e, 1.5f); wb_arg(e, 0);
    e = wb_event(log, MU_OBJ_CALL_SPRITE, i);
    wb_arg(e, 0x7f26); wb_vec(e, b); wb_float(e, 10.0f); wb_vec(e, light);
    wb_float(e, 0.0f); wb_arg(e, 1); wb_arg(e, 0); wb_arg(e, 4);
    float from[3] = {b[0], b[1], b[2]}, to[3] = {b[0], b[1], b[2]};
    from[0] = from[0] - 50.0f;
    from[0] = from[0] - (float)(random(ctx) % 100);
    to[0] = (float)(random(ctx) % 80) + to[0];
    from[1] = from[1] - (float)(random(ctx) % 50);
    to[1] = (float)(random(ctx) % 50) + to[1];
    from[2] = from[2] + 10.0f;
    to[2] = to[2] + 10.0f;
    if (random(ctx) % 20 == 0) joint(log, i, 0x7f7c, from, to, a, 0x12, 0, 40.0f);
    return 1;
}
