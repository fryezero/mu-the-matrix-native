/* Elbeland boids, MoveBoids helpers 0x00ca33c3 and 0x00ca3ce1. */
#include "env_internal.h"

/* Floating heading 0x012aed9e, including its axis thresholds. */
static float heading(float x, float y, float tx, float ty)
{
    float dx = tx - x, dy = ty - y;
    if (0.0001f > env_fabs(dx)) return 0.0f > dy ? 0.0f : 180.0f;
    if (0.0001f > env_fabs(dy)) return 0.0f > dx ? 270.0f : 90.0f;
    float a = (env_atan(dy / dx) / 3.1415927410125732f) * 180.0f + 90.0f;
    return 0.0f > dx ? a + 180.0f : a;
}

void env_elbeland_move(mu_env *env, const mu_env_inputs *in, mu_env_object *o)
{
    if (o->type == 0x1a4) { /* ambient typhoon, 0x00ca3ce1 */
        o->velocity = 1.0f;
        if (mu_env_rand(env) % 500 == 0)
            o->field_170[0] = (float)(mu_env_rand(env) % 314) / 100.0f;
        o->position[0] = env_sin(o->field_170[0]) * 2.0f + o->position[0];
        o->position[1] = env_cos(o->field_170[0]) * 2.0f + o->position[1];
        o->angle[2] = 0.0f;
        if (1.0f > o->field_a8) o->field_a8 = o->field_a8 + 0.1f;
        return;
    }
    /* Type-62 object's fixed pool slot, 0x00ca33c3. Animation runs first. */
    if (o->subtype == 0 && mu_env_rand(env) % 120 == 0) {
        o->subtype = 1;
        o->frame = 0.0f;
    } else if (o->subtype == 1 && o->frame == 24.0f) {
        o->subtype = 2;
    } else if (o->subtype == 2 && o->frame == 0.0f) {
        o->subtype = 0;
    } else if (o->subtype == 0) {
        o->frame = 0.0f;
    }
    float time = in->world_time * 0.001f, yaw = 0.0f;
    if (o->ai == 0 || o->ai == 2) {
        int reverse = o->ai == 2;
        o->field_170[0] = (reverse ? env_sin(time) : env_cos(time)) * o->gravity;
        o->field_170[1] = (reverse ? env_cos(time) : env_sin(time)) * o->gravity;
        yaw = heading(o->position[0], o->position[1], o->position[0] + o->field_170[0],
                      o->position[1] + o->field_170[1]);
        float *v = o->field_170;
        if (v[2] == 0.0f && (reverse ? v[1] > v[0] : v[0] > v[1])) v[2] = 1.0f;
        else if (v[2] == 1.0f && (reverse ? v[0] > v[1] : v[1] > v[0])) v[2] = 2.0f;
        else if (v[2] == 2.0f && (reverse ? v[1] > v[0] : v[0] > v[1])) {
            o->ai = reverse ? 0 : 2;
            v[2] = 0.0f;
            v[0] = (reverse ? env_cos(time) : env_sin(time)) * o->gravity;
            v[1] = (reverse ? env_sin(time) : env_cos(time)) * o->gravity;
            yaw = heading(o->position[0], o->position[1], o->position[0] + v[0], o->position[1] + v[1]);
        }
    }
    o->position[0] = o->position[0] + o->field_170[0];
    o->position[1] = o->position[1] + o->field_170[1];
    o->position[2] = env_sin(in->world_time * 0.0005f) * 1.0f + o->position[2];
    o->angle[1] = env_sin(time) * 0.4f + o->angle[1];
    o->angle[2] = yaw + 270.0f;
}
