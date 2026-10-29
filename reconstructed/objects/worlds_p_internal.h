/* RENDER-WORLDS-P helpers shared by the two Kethotum classes (one move template, different sound ids). */
#ifndef MU_WORLDS_P_INTERNAL_H
#define MU_WORLDS_P_INTERNAL_H
#include "worlds_p.h"
#include "worlds_b_internal.h"
static inline float wp_bits(uint32_t u)
{
    float f;
    memcpy(&f, &u, 4);
    return f;
}
/* Hero distance in the ground plane: 0x00961a07 sqrt of the float sum, rounded to float. */
static inline float wp_distance(const uint8_t *o, const mu_wp_move_inputs *in)
{
    const float dx = in->hero[0] - mu_obj_f32(o, MU_OBJF_POSITION);
    const float dy = in->hero[1] - mu_obj_f32(o, MU_OBJF_POSITION + 4);
    float d = dx * dx;
    d = d + dy * dy;
    return (float)sqrt((double)d);
}
/* SetAction 0x012affa4 with the object's own model. */
static inline void wp_set_action(uint8_t *o, const mu_wp_model *m, int32_t action)
{
    if (!m || action >= m->action_count || mu_obj_u16(o, MU_OBJF_ACTION) == action)
        return;
    mu_obj_set_u16(o, MU_OBJF_PRIOR_ACTION, mu_obj_u16(o, MU_OBJF_ACTION));
    mu_obj_set_f32(o, MU_OBJF_PRIOR_FRAME, mu_obj_f32(o, MU_OBJF_FRAME));
    mu_obj_set_u16(o, MU_OBJF_ACTION, (uint16_t)action);
    mu_obj_set_f32(o, MU_OBJF_FRAME, 0.0f);
}
static inline void wp_sound(mu_obj_log *log, int32_t i, uint32_t id) { wb_sound(log, i, id, 0, 0); }
/* Frame counters of the swinging objects: +0x30 swings done, +0x34 swings before the next rest. */
#define WP_SWINGS 0x30
#define WP_SWING_LIMIT 0x34
#define WP_PHASE 0x64
/* Create: every action of the model at 0.3; action 1 of the listed types then scaled. */
static inline void wp_speeds(mu_wp_model *m)
{
    for (int32_t k = 0; m && k < m->action_count; ++k)
        m->speed[k] = 0.3f;
}
/* Types 0x16/0x29/0x5c/0x74: swing (action 1) when the hero is near, rest (0) a random 15..24 times. */
static inline int wp_swing(uint8_t *o, int32_t i, const mu_wp_move_inputs *in, mu_obj_log *log)
{
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    if (mu_obj_u16(o, MU_OBJF_ACTION) == 1 && 1000.0f >= wp_distance(o, in)) {
        const float f = mu_obj_f32(o, MU_OBJF_FRAME);
        if (t == 0x16)
            wp_sound(log, i, 0x549);
        else if (t == 0x5c && f > 0.85f && 1.0f > f)
            wp_sound(log, i, 0x548);
    }
    const mu_wp_model *m = in->model;
    if (!m)
        return 0;
    const uint16_t a = mu_obj_u16(o, MU_OBJF_ACTION);
    const float s = m->speed[a] + in->frame_time;
    if (mu_obj_f32(o, MU_OBJF_FRAME) >= (float)m->keys[a] - s) {
        if (a == 0) {
            if (mu_obj_i32(o, WP_SWINGS) == mu_obj_i32(o, WP_SWING_LIMIT))
                wp_set_action(o, m, 1);
            mu_obj_set_i32(o, WP_SWINGS, mu_obj_i32(o, WP_SWINGS) + 1);
        } else if (a == 1) {
            wp_set_action(o, m, 0);
            mu_obj_set_i32(o, WP_SWING_LIMIT, in->rand_fn(in->context) % 10 + 15);
            mu_obj_set_i32(o, WP_SWINGS, 0);
        }
    }
    return 1;
}
/* Types 0x77/0x81: open (1, 2) within 300 of the hero, close (3, back to 0) beyond. */
static inline int wp_gate(uint8_t *o, int32_t i, const mu_wp_move_inputs *in, mu_obj_log *log)
{
    const mu_wp_model *m = in->model;
    if (!m)
        return 0;
    const uint16_t a = mu_obj_u16(o, MU_OBJF_ACTION);
    const float s = m->speed[a] + in->frame_time;
    const float d = wp_distance(o, in);
    const int ended = mu_obj_f32(o, MU_OBJF_FRAME) >= (float)m->keys[a] - s;
    if (d >= 300.0f) {
        if ((a == 1 && ended) || a == 2) {
            wp_sound(log, i, 0x55c);
            wp_set_action(o, m, 3);
        } else if (a == 3 && ended) {
            wp_set_action(o, m, 0);
        }
    } else if (a == 0) {
        wp_sound(log, i, 0x55b);
        wp_set_action(o, m, 1);
    } else if (a == 1 && ended) {
        wp_set_action(o, m, 2);
    } else if (a == 3 && ended) {
        wp_sound(log, i, 0x55b);
        wp_set_action(o, m, 1);
    }
    return 1;
}
static inline int wp_near_sound(const uint8_t *o, int32_t i, const mu_wp_move_inputs *in, float limit,
                                uint32_t id, mu_obj_log *log)
{
    if (limit >= wp_distance(o, in))
        wp_sound(log, i, id);
    return 1;
}
#endif
