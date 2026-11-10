#include "visual.h"
#include "../movement/client_movement.h"
#include <math.h>
#include <string.h>

void mu_mv_setup(mu_mv_state *s, const mu_mv_info *info, const mu_mv_owner *owner)
{
    memset(s, 0, sizeof *s);
    s->model = info->item + 0xae6;
    s->key = owner->key;
    s->scale = info->scale;
    memcpy(s->offset, info->offset, sizeof s->offset);
    memcpy(s->angle, owner->angle, sizeof s->angle);
    for (int k = 0; k < 3; ++k)
        s->position[k] = owner->position[k] + s->offset[k];
    s->radius = sqrtf(info->offset[0] * info->offset[0] + info->offset[1] * info->offset[1]);
}

int32_t mu_mv_select(mu_mv_state *s, const mu_mv_info *info, const mu_mv_owner *owner, int32_t keys,
                     int32_t rand_value)
{
    const float x = s->position[0] - owner->position[0], y = s->position[1] - owner->position[1];
    const float distance = sqrtf(x * x + y * y);
    int32_t action = -1;
    switch (s->state) {
    case 0:
        if (distance > s->radius)
            action = 2;
        else if (rand_value % 500 == 0)
            action = 1;
        break;
    case 1:
        if (distance > s->radius)
            action = 2;
        else if (s->frame + info->speed[s->state] >= (float)keys)
            action = 0;
        break;
    case 2:
        if (!owner->moving && s->radius + 10.0f >= distance && keys >= 0 &&
            s->frame + info->speed[s->state] >= (float)keys)
            action = 0;
        break;
    case 3:
    case 4:
        if (s->frame + info->speed[s->state] >= (float)keys)
            action = 0;
        break;
    default:
        break;
    }
    if (action >= 0)
        s->state = action;
    return action;
}

void mu_mv_spring(mu_mv_state *s, const float from[3], const float target[3], float out[3])
{
    float result[3];
    for (int k = 0; k < 3; ++k) {
        s->force[k] = from[k] - target[k];
        s->force[k] = -1.4f * s->force[k];
        s->step[k] = 20.0f * s->velocity[k];
        s->delta[k] = s->force[k] - s->velocity[k];
        s->acceleration[k] = (1.0f / 25.0f) * s->delta[k];
        s->step[k] = s->step[k] + s->acceleration[k];
        result[k] = from[k] + s->step[k];
    }
    memcpy(out, result, sizeof result);
}

void mu_mv_follow(mu_mv_state *s, const mu_mv_info *info, const mu_mv_owner *owner)
{
    if (s->state == 0) {
        for (int k = 0; k < 3; ++k)
            s->target[k] = owner->position[k] + s->offset[k];
    } else if (s->state == 2) {
        memcpy(s->target, owner->position, sizeof s->target);
        s->target[2] = s->target[2] + info->offset[2];
        float heading = mu_create_angle(s->position[0], s->position[1], owner->position[0], owner->position[1]);
        s->angle[2] = mu_turn_angle2(s->angle[2], heading, 10.0f);
        mu_mv_spring(s, s->position, s->target, s->position);
    }
}

int mu_mv_alive(int has_object, int has_owner_object, int object_live, int scene, int owner_live, int owner_kind)
{
    if (!has_object || !has_owner_object || !object_live)
        return 0;
    return scene != 6 || (owner_live && owner_kind == 1);
}

int mu_mv_visible(int has_object, int object_live, int frustum, int32_t key, int32_t owner_key)
{
    return has_object && object_live == 1 && frustum == 1 && key == owner_key;
}
