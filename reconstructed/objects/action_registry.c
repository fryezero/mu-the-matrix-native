/* RENDER-WORLDS-AFTER5: the object action registry 0x01ec7d5c (action_registry.h). */
#include "action_registry.h"

#include <math.h>
#include <stddef.h>

enum { OBJ_LOOPS = 0x30, OBJ_LIMIT = 0x34 };   /* int counters of the handlers 2, 3 (loops) and 7 (latch) */

uint32_t mu_anim_key(int32_t type, int32_t action)
{
    return 1000u * (uint32_t)action + (uint32_t)type;
}

const mu_anim_entry *mu_anim_find(const mu_anim_inputs *in, int32_t type, int32_t action)
{
    const uint32_t key = mu_anim_key(type, action);
    for (int32_t k = 0; in->entries && k < in->count; ++k)
        if (mu_anim_key(in->entries[k].type, in->entries[k].action) == key)
            return &in->entries[k];
    return NULL;
}

static int32_t back(const mu_anim_entry *e)
{
    return e->extra[e->extra_count - 1];   /* 0x00ce486d */
}

/* ---- SetAction handlers (+0x24), 0x00ce1460.. ---- */
static int set_handler(uint8_t *o, const mu_anim_entry *e, const mu_anim_inputs *in)
{
    switch (e->handler) {
    case 0: case 1: case 4: case 5: case 6: case 7:
        mu_obj_set_f32(o, MU_OBJF_VELOCITY, e->speed);
        return MU_ANIM_APPLIED;
    case 2: case 3: {   /* 0x00ce149c, 0x00ce1501: a random first loop limit within [extra[0], extra[1]) */
        mu_obj_set_f32(o, MU_OBJF_VELOCITY, e->speed);
        mu_obj_set_i32(o, OBJ_LOOPS, 0);
        if (e->extra_count < 2 || e->extra[1] == e->extra[0])
            return MU_ANIM_UNSUPPORTED;   /* the client divides by the span */
        const int32_t r = in->rand_fn(in->context);
        mu_obj_set_i32(o, OBJ_LIMIT, e->extra[0] + r % (e->extra[1] - e->extra[0]));
        return MU_ANIM_APPLIED;
    }
    case 8:   /* 0x00ce15de: the alpha rate from extra[6] when the vector has more than six */
        if (e->extra_count > 6)
            mu_obj_set_f32(o, MU_OBJF_ALPHA_RATE, (float)e->extra[6] * 0.00999999978f);
        return MU_ANIM_APPLIED;
    default:
        return MU_ANIM_UNSUPPORTED;
    }
}

int mu_action_set(uint8_t *o, int32_t action, const mu_anim_inputs *in)
{
    if (!o)
        return MU_ANIM_NONE;
    const int32_t type = mu_obj_i32(o, MU_OBJF_TYPE);
    int32_t count = 0;
    int16_t keys = 0;
    uint8_t lock = 0;
    if (!in->model(in->context, type, action, &count, &keys, &lock) || !(action < (int32_t)(int16_t)count))
        return MU_ANIM_NONE;
    if ((int32_t)mu_obj_u16(o, MU_OBJF_ACTION) != action) {
        mu_obj_set_u16(o, MU_OBJF_PRIOR_ACTION, mu_obj_u16(o, MU_OBJF_ACTION));
        mu_obj_set_f32(o, MU_OBJF_PRIOR_FRAME, mu_obj_f32(o, MU_OBJF_FRAME));
        mu_obj_set_u16(o, MU_OBJF_ACTION, (uint16_t)action);
        mu_obj_set_f32(o, MU_OBJF_FRAME, 0.0f);
    }
    const mu_anim_entry *e = mu_anim_find(in, type, action);
    return e ? set_handler(o, e, in) : MU_ANIM_NONE;
}

/* ---- tick handlers (+0x18), 0x00ce1646.. ---- */

/* The end of the current action: frame +0xd0 >= keys - speed (keys - 1 first when the action locks positions and
 * `locked` asks for it). False for a NaN frame (comiss; jb). */
static int at_end(const uint8_t *o, const mu_anim_entry *e, int16_t keys, uint8_t lock, int locked)
{
    float limit = (float)keys;
    if (locked && lock)
        limit = limit - 1.0f;
    return mu_obj_f32(o, MU_OBJF_FRAME) >= limit - e->speed;
}

/* The hero's x/y distance (sqrt 0x00961a07 rounds the root of the widened sum to binary32). */
static float hero_distance(const uint8_t *o, const mu_anim_inputs *in)
{
    const float dx = in->hero[0] - mu_obj_f32(o, MU_OBJF_POSITION);
    const float dy = in->hero[1] - mu_obj_f32(o, MU_OBJF_POSITION + 4);
    const float sum = dx * dx + dy * dy;
    return (float)sqrt((double)sum);
}

static int tick_handler(uint8_t *o, const mu_anim_entry *e, int16_t keys, uint8_t lock, const mu_anim_inputs *in)
{
    switch (e->handler) {
    case 0:
        return MU_ANIM_APPLIED;
    case 1:   /* 0x00ce165c: the last action of the vector at the end */
        if (at_end(o, e, keys, lock, 0)) {
            if (e->extra_count < 1)
                return MU_ANIM_UNSUPPORTED;
            mu_action_set(o, back(e), in);
        }
        return MU_ANIM_APPLIED;
    case 2:   /* 0x00ce1737: after +0x34 loops */
        if (at_end(o, e, keys, lock, 0)) {
            if (mu_obj_i32(o, OBJ_LOOPS) >= mu_obj_i32(o, OBJ_LIMIT)) {
                if (e->extra_count < 1)
                    return MU_ANIM_UNSUPPORTED;
                mu_action_set(o, back(e), in);
            }
            mu_obj_set_i32(o, OBJ_LOOPS, mu_obj_i32(o, OBJ_LOOPS) + 1);
        }
        return MU_ANIM_APPLIED;
    case 3:   /* 0x00ce1830: after +0x34 loops, a random action of extra[2..] */
        if (at_end(o, e, keys, lock, 0)) {
            if (mu_obj_i32(o, OBJ_LOOPS) >= mu_obj_i32(o, OBJ_LIMIT)) {
                if (e->extra_count <= 2)
                    return MU_ANIM_UNSUPPORTED;   /* the client divides by size - 2 */
                const uint32_t r = (uint32_t)in->rand_fn(in->context);
                mu_action_set(o, e->extra[r % (uint32_t)(e->extra_count - 2) + 2], in);
            }
            mu_obj_set_i32(o, OBJ_LOOPS, mu_obj_i32(o, OBJ_LOOPS) + 1);
        }
        return MU_ANIM_APPLIED;
    case 5:   /* 0x00ce1b61: by the action's own step extra[0] */
    case 7: { /* 0x00ce20c2: the same, with a latch +0x34 */
        if (e->extra_count < 1)
            return MU_ANIM_UNSUPPORTED;
        const int seven = e->handler == 7;
        switch (e->extra[0]) {
        case 0: {   /* the hero comes nearer than param */
            const float d = hero_distance(o, in), p = (float)e->param;
            if (!seven) {
                if (p > d)
                    mu_action_set(o, back(e), in);
            } else if (p > d) {
                if (mu_obj_i32(o, OBJ_LIMIT) == 0)
                    mu_action_set(o, back(e), in);
            } else if (d > p) {
                mu_obj_set_i32(o, OBJ_LIMIT, 0);
            }
            break;
        }
        case 2:
            if (!seven) {   /* the hero leaves param */
                if (hero_distance(o, in) > (float)e->param)
                    mu_action_set(o, back(e), in);
            } else if (at_end(o, e, keys, lock, 1)) {
                mu_obj_set_i32(o, OBJ_LIMIT, mu_obj_i32(o, OBJ_LIMIT) + 1);
                mu_action_set(o, back(e), in);
            }
            break;
        case 1: case 3:
            if (at_end(o, e, keys, lock, 0))
                mu_action_set(o, back(e), in);
            break;
        default:
            break;
        }
        return MU_ANIM_APPLIED;
    }
    default:   /* 4, 6, 8: the hero's box against the object's (0x018500bf), not ported */
        return MU_ANIM_UNSUPPORTED;
    }
}

int mu_action_tick(uint8_t *o, const mu_anim_inputs *in, int *found)
{
    *found = 0;
    if (!o)
        return MU_ANIM_NONE;
    const int32_t type = mu_obj_i32(o, MU_OBJF_TYPE);
    const int32_t action = (int32_t)mu_obj_u16(o, MU_OBJF_ACTION);
    const mu_anim_entry *e = mu_anim_find(in, type, action);
    if (!e)
        return MU_ANIM_NONE;
    int32_t count = 0;
    int16_t keys = 0;
    uint8_t lock = 0;
    if (!in->model(in->context, type, action, &count, &keys, &lock))
        return MU_ANIM_NONE;
    *found = 1;
    if (action >= (int32_t)(int16_t)count)
        return MU_ANIM_UNSUPPORTED;   /* the handlers read the action record unchecked */
    return tick_handler(o, e, keys, lock, in);
}

int mu_anim_class_world(int32_t world)
{
    /* world-handler-coverage.md: 57, 58, 62..64, 69..72, 79..82, 91..96, 100, 101, 110..145 */
    return (world >= 57 && world <= 58) || (world >= 62 && world <= 64) || (world >= 69 && world <= 72) ||
           (world >= 79 && world <= 82) || (world >= 91 && world <= 96) || world == 100 || world == 101 ||
           (world >= 110 && world <= 145);
}
