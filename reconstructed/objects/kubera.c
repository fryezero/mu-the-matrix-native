/* Kubera Mine, worlds 123..127 (predicate 0x00e1e4b6). Create 0x00e19bb3 (type table 0x00e19dfb/0x00e19e1b),
 * move 0x00e19ed0, visual 0x00e1b5fb. */
#include "worlds_q_internal.h"

static int kubera_world(int32_t world) { return world >= 0x7b && world <= 0x7f; }

int mu_kubera_create(uint8_t *o, int32_t index, const mu_q_inputs *in, mu_obj_log *log)
{
    if (!kubera_world(in->world) || !o)
        return 0;
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    switch (t) {
    case 29: case 30: case 72: case 94: case 109: case 118: case 119: case 120: case 121: case 126: case 131:
    case 146: case 147: case 159: case 160:
        o[MU_OBJF_AFTER_CHARACTER] = 1;
        mu_obj_set_f32(o, MU_OBJF_RANGE, -300.0f);
        break;
    case 0: case 1: case 23: case 35: case 37: case 43: case 44: case 45: case 64: case 81: case 93: case 103:
    case 107: case 125: case 140: case 145: case 154:   /* entry 0x00e19c21, inside the case above */
        mu_obj_set_f32(o, MU_OBJF_RANGE, -300.0f);
        break;
    case 132: case 135:
        mu_obj_set_f32(o, MU_OBJF_VELOCITY, 0.349999994f);
        break;
    case 134:
        o[MU_OBJF_AFTER_CHARACTER] = 1;
        mu_obj_set_f32(o, MU_OBJF_VELOCITY, 0.349999994f);
        mu_obj_set_f32(o, MU_OBJF_RANGE, -300.0f);
        break;
    case 158:
        mu_obj_set_f32(o, MU_OBJF_RANGE, -600.0f);
        memcpy(o + MU_OBJF_START, o + MU_OBJF_POSITION, 12);
        memcpy(o + 0x140, o + MU_OBJF_ANGLE, 12);
        in->handler->kubera_object = o;
        wb_arg(wb_event(log, MU_OBJ_CALL_REGISTER, index), 1);
        break;
    case 15: case 47: case 52: {   /* every action of the type's model: PlaySpeed 0.3, no loop */
        int32_t count;
        uint8_t *table = q_actions(in, o, &count);
        for (int32_t k = 0; table && k < count; ++k) {
            const float speed = 0.300000012f;
            memcpy(table + 16 * k + 4, &speed, 4);
            table[16 * k + 0xa] = 0;
        }
        break;
    }
    default:
        if (t >= 161 && t <= 180 && t != 173 && t != 174)
            mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
        break;
    }
    return 1;
}

/* The record of the current action, read without a bounds test (model +0x30 + action * 16). Natively an
 * action outside the table reads as a zero record. */
static const uint8_t *record_of(const uint8_t *table, int32_t count, const uint8_t *o)
{
    static const uint8_t zero[16];
    const int32_t action = mu_obj_u16(o, MU_OBJF_ACTION);
    return action < count ? table + 16 * action : zero;
}

/* Types 15 and 47: at the end of the action, count +0x64 down and, at zero, step 0 -> 1 -> 2 -> 3 -> 0;
 * actions 0 and 2 then hold for rand % 10 + 5 cycles. */
static void step_actions(uint8_t *o, const uint8_t *table, int32_t count, const mu_q_inputs *in)
{
    if (!q_action_ended(o, record_of(table, count, o)))
        return;
    int32_t action = mu_obj_u16(o, MU_OBJF_ACTION);
    mu_obj_set_i32(o, 0x64, mu_obj_i32(o, 0x64) - 1);
    if (mu_obj_i32(o, 0x64) <= 0) {
        mu_obj_set_i32(o, 0x64, 1);
        action = action >= 3 ? 0 : action + 1;
        if (action == 0 || action == 2)
            mu_obj_set_i32(o, 0x64, in->rand_fn(in->context) % 10 + 5);
    }
    q_set_action(in, o, action);
}

static float hero_distance(const uint8_t *o, const mu_q_inputs *in)
{
    const float dx = in->hero[0] - mu_obj_f32(o, MU_OBJF_POSITION),
                dy = in->hero[1] - mu_obj_f32(o, MU_OBJF_POSITION + 4);
    return (float)sqrt((double)(dx * dx + dy * dy));   /* 0x00961a07 */
}

static void stop_sound(mu_obj_log *log, int32_t i, uint32_t id)
{
    mu_obj_event *e = wb_event(log, MU_Q_STOP_SOUND, i);
    wb_arg(e, id);
    wb_arg(e, 1);
}

/* WorldTime-independent countdown at +0xb4 by the frame time. */
static void count_down(uint8_t *o, const mu_q_inputs *in)
{
    if (mu_obj_f32(o, MU_OBJF_TIMER) > 0.0f)
        mu_obj_set_f32(o, MU_OBJF_TIMER, mu_obj_f32(o, MU_OBJF_TIMER) - in->frame_time);
}

int mu_kubera_move(uint8_t *o, int32_t index, const mu_q_inputs *in, mu_obj_log *log)
{
    if (!kubera_world(in->world) || !o)
        return 0;
    int32_t count;
    const uint8_t *table = q_actions(in, o, &count);
    if (!table)
        return 0;
    switch (mu_obj_i32(o, MU_OBJF_TYPE)) {
    case 47:
        if (hero_distance(o, in) <= 900.0f) {
            const uint16_t action = mu_obj_u16(o, MU_OBJF_ACTION);
            if (action == 1 && mu_obj_f32(o, MU_OBJF_FRAME) <= 2.0f)
                wb_sound(log, index, 0x4f4, 0, 0);
            else if (action == 3 && mu_obj_f32(o, MU_OBJF_FRAME) <= 2.0f)
                wb_sound(log, index, 0x4f3, 0, 0);
        }
        step_actions(o, table, count, in);
        break;
    case 15:
        step_actions(o, table, count, in);
        break;
    case 52:
        if (hero_distance(o, in) <= 500.0f) {
            if (mu_obj_u16(o, MU_OBJF_ACTION) != 2) {
                stop_sound(log, index, 0x4f2);
                wb_sound(log, index, 0x4f1, 0, 0);
                q_set_action(in, o, 1);
                if (q_action_ended(o, record_of(table, count, o)))
                    q_set_action(in, o, 2);
            }
        } else if (mu_obj_u16(o, MU_OBJF_ACTION) != 0) {
            q_set_action(in, o, 3);
            const uint8_t *record = record_of(table, count, o);
            if (mu_obj_f32(o, MU_OBJF_FRAME) >= (float)(q_keys(record) / 2)) {
                stop_sound(log, index, 0x4f1);
                wb_sound(log, index, 0x4f2, 0, 0);
            }
            if (q_action_ended(o, record))
                q_set_action(in, o, 0);
        } else {
            q_set_action(in, o, 0);
        }
        break;
    case 100: {
        count_down(o, in);
        const uint8_t *record = record_of(table, count, o);
        if (q_action_ended(o, record))
            mu_obj_set_f32(o, MU_OBJF_TIMER, (float)(in->rand_fn(in->context) % 7 + 2));
        if (q_speed(record) >= mu_obj_f32(o, MU_OBJF_FRAME)) {
            if (0.0f >= mu_obj_f32(o, MU_OBJF_TIMER))
                q_set_action(in, o, 0);
            else
                mu_obj_set_f32(o, MU_OBJF_FRAME, 0.0f);
        }
        break;
    }
    case 127: case 132: case 134: case 135:
        if (q_action_ended(o, record_of(table, count, o))) {
            mu_obj_set_f32(o, MU_OBJF_FRAME, 0.0f);
            mu_obj_set_f32(o, MU_OBJF_PRIOR_FRAME, 0.0f);
        }
        break;
    case 145:
        count_down(o, in);
        if (mu_obj_u16(o, MU_OBJF_ACTION) == 1 && q_action_ended(o, record_of(table, count, o))) {
            mu_obj_set_f32(o, MU_OBJF_TIMER, (float)(in->rand_fn(in->context) % 15 + 15));
            q_set_action(in, o, 0);
        } else if (0.0f >= mu_obj_f32(o, MU_OBJF_TIMER)) {
            q_set_action(in, o, 1);
        }
        break;
    case 158:
        if (mu_obj_i32(o, 0x64) == 0)
            mu_obj_set_f32(o, MU_OBJF_FRAME, 0.0f);
        else if (mu_obj_i32(o, 0x64) == 1)
            q_set_action(in, o, 0);
        break;
    default:
        break;
    }
    return 1;
}

int mu_kubera_visual(const uint8_t *o, int32_t index, int model_present, const mu_q_inputs *in, mu_obj_log *log)
{
    if (!kubera_world(in->world) || !o || !model_present)
        return 0;
    if (mu_obj_i32(o, MU_OBJF_TYPE) == 161 && in->rand_fn(in->context) % 80 == 1) {
        const float light[3] = {0.300000012f, 0.300000012f, 0.300000012f};
        q_effect(log, index, o, 0x195, light, 0, (uint16_t)wb_int(mu_obj_f32(o, MU_OBJF_SCALE)));
    }
    return 1;
}
