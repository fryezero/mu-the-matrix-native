/* In-world camera. See client_world_camera.h. */
#include "client_world_camera.h"

#include <math.h>
#include <string.h>

uint32_t mu_tick_timer_elapsed(const mu_tick_timer *t, uint32_t now)
{
    if (t->done == 1)
        return t->duration;
    if (t->start == 0)
        return 0;
    return now - t->start;
}

void mu_tick_timer_update(mu_tick_timer *t, uint32_t now)
{
    if (t->duration == 0) {
        t->done = 1;
        return;
    }
    t->done = 0;
    if (t->start == 0) {
        t->start = now;
        return;
    }
    if (now - t->start > t->duration) {
        t->start = now;
        t->done = 1;
    }
}

float mu_camera_lerp_steps(float a, float b, int32_t i, int32_t n)
{
    if (i >= n)
        return b;
    if (i <= 0)
        return a;
    float value = (float)i * (b - a);
    value = value / (float)n;
    return value + a;
}

float mu_camera_ease(float a, float b, float t, int32_t n, int forward)
{
    if (t >= (float)n)
        return b;
    if (0.0f >= t)
        return a;
    int32_t i = mu_cvtt(t);
    float from = a, to = b;
    if (!forward) {
        i = mu_cvtt((float)n - t);
        from = b;
        to = a;
    }
    float diff = (float)fabs((double)(to - from));
    float acceleration = diff * 2.0f;
    acceleration = acceleration / (float)n;
    float deceleration = -(acceleration / (float)n);
    float step = (float)i * acceleration;
    float curve = deceleration / 2.0f;
    curve = curve * (float)i;
    curve = curve * (float)i;
    step = step + curve;
    if (to > from)
        return step + from;
    return from - step;
}

static int fov_follows_world(const mu_world_camera *c)
{
    /* 0x01851a7f */
    if (c->scene != 6)
        return 1;
    return c->world == 6 || (c->world >= 0x45 && c->world <= 0x4a);
}

static float world_far(const mu_world_camera *c, float base)
{
    /* 0x0098ac45 */
    float value = base * c->far_scale[0];
    value = value * c->far_scale[1];
    return value * c->far_scale[2];
}

/* Offset (0, y, 0) rotated by the yaw-only angles a and added. */
static void add_rotated(const float angles[3], float y, float position[3])
{
    float matrix[12], offset[3] = {0.0f, y, 0.0f}, rotated[3];
    mu_angle_matrix(angles, matrix);
    mu_vector_irotate(offset, matrix, rotated);
    for (int i = 0; i < 3; ++i)
        position[i] = position[i] + rotated[i];
}

void mu_world_camera_enter(mu_world_camera *c, mu_client_view *v)
{
    v->angle[2] = -45.0f;
    c->zoom_timer.done = 1;
    c->zoom_index = 2;
    c->fov_to = c->world_fov;
    c->fov_from = c->fov_to;
    memcpy(c->position_start, v->position, sizeof c->position_start);
    memcpy(c->angle_start, v->angle, sizeof c->angle_start);
}

void mu_move_main_camera(mu_world_camera *c, mu_client_view *v, uint32_t now)
{
    if (fov_follows_world(c))
        v->fov = c->world_fov;
    v->angle[0] = 0.0f;
    v->angle[1] = 0.0f;
    if (v->top_view) {
        v->view_far = 3200.0f;
        v->position[0] = c->hero_position[0];
        v->position[1] = c->hero_position[1];
        v->position[2] = v->view_far;
    } else {
        /* far plane */
        if (c->world == 0x33)
            v->view_far = 3220.0f;
        else if (c->event_world)
            v->view_far = 3700.0f;
        else if (c->hero_byte4 == 1 && (c->world == 0x5b || c->world == 0x5c))
            v->view_far = 3000.0f;
        else
            switch (c->zoom_level) {
            case 0:
                if (c->scene == 3 || c->scene == 5)
                    v->view_far = world_far(c, 2400.0f);
                else if (c->far_2300)
                    v->view_far = 2300.0f;
                else
                    v->view_far = world_far(c, 2000.0f);
                break;
            case 1: v->view_far = 2500.0f; break;
            case 2: v->view_far = 2600.0f; break;
            case 3: v->view_far = 2950.0f; break;
            case 4: case 5: v->view_far = 3200.0f; break;
            default: break;
            }
        /* offset behind the hero: (0, -distance, 0) rotated by the yaw only */
        float base[3] = {0.0f, -c->distance, 0.0f}, matrix[12], offset[3];
        mu_angle_matrix(v->angle, matrix);
        mu_vector_irotate(base, matrix, offset);
        if (c->scene == 6) {
            /* 0x00ec3394: the override vector unless it is all zero, else the hero */
            if (c->camera_override[0] != 0.0f || c->camera_override[1] != 0.0f || c->camera_override[2] != 0.0f)
                memcpy(base, c->camera_override, sizeof base);
            else
                memcpy(base, c->hero_position, sizeof base);
        }
        if (c->zoom_object_active) {
            c->hero_position[2] = 300.0f;
            c->zoom_level = c->zoom_object_level;
        } else {
            c->zoom_level = 0;
        }
        for (int i = 0; i < 3; ++i)
            v->position[i] = base[i] + offset[i];
        v->position[2] = c->hero_position[2];
        if (c->hero_tile_wall & 0x40) {
            c->water_height = 1201.0f;
            v->position[2] = c->water_height;
        }
        float height = c->distance - 150.0f;
        v->position[2] = height + v->position[2];

        if (c->scene == 5 || c->scene == 3) {
            /* 0x018553f3 / 0x0185555a (NATIVE-CHARSEL-001): the character-select and
             * login scenes take the angles and the position of the world's camera
             * record (0x0098647b()->+0xc: +0 angle, +0xc position) and skip the
             * pitch and zoom block (jump to 0x01855a27). */
            memcpy(v->angle, c->scene_angle, sizeof v->angle);
            memcpy(v->position, c->scene_position, sizeof v->position);
            goto earthquake;
        }
        v->angle[0] = -48.5f;
        if (c->world != 0x8b) {
            int zooming = c->fov_from != c->fov_to || c->world_fov != v->fov;
            if (zooming) {
                if (c->zoom_timer.done == 1) {
                    float diff = c->world_fov - v->fov;
                    v->angle[0] = v->angle[0] - mu_camera_lerp_steps(0.0f, 30.8f, mu_cvtt(diff), 26);
                    v->position[2] = v->position[2] - mu_camera_lerp_steps(0.0f, 580.0f, mu_cvtt(diff), 26);
                } else {
                    float t = (float)(double)mu_tick_timer_elapsed(&c->zoom_timer, now);
                    int32_t n = (int32_t)c->zoom_timer.duration;
                    v->angle[0] = mu_camera_ease(c->angle_start[0], c->angle_end[0], t, n, 1);
                    t = (float)(double)mu_tick_timer_elapsed(&c->zoom_timer, now);
                    v->position[2] = mu_camera_ease(c->position_start[2], c->position_end[2], t, n, 1);
                    t = (float)(double)mu_tick_timer_elapsed(&c->zoom_timer, now);
                    v->fov = mu_camera_ease(c->fov_from, c->fov_to, t, n, 1);
                }
            }
            if (c->zoom_timer.done == 0) {
                mu_tick_timer_update(&c->zoom_timer, now);
                if (c->zoom_timer.done == 1)
                    v->fov = c->fov_to;
            }
        }
    earthquake:
        v->angle[0] = v->angle[0] + c->earthquake;
        if (c->hero_tile_wall & 0x80) {
            if (200.0f >= c->lift)
                c->lift = c->lift + 10.0f;
        } else if (c->lift > 0.0f) {
            c->lift = c->lift - 10.0f;
        }
        if (c->lift > 0.0f || 0.0f > c->lift) {
            const float lift_angles[3] = {0.0f, 0.0f, -45.0f};
            add_rotated(lift_angles, c->lift, v->position);
        }
    }
    if (c->world == 5) {
        float x = c->world_time * 0.0005f;
        float s = (float)sin((double)x);
        v->angle[0] = s * 2.0f + v->angle[0];
        x = c->world_time * 0.0008f;
        s = (float)sin((double)x);
        v->angle[1] = s * 2.5f + v->angle[1];
        return;
    }
    float target;
    switch (c->zoom_level) {
    case 0: target = 1000.0f; break;
    case 1: target = 1100.0f; break;
    case 2: target = 1200.0f; break;
    case 3: target = 1300.0f; break;
    case 4: target = 1400.0f; break;
    case 5: target = c->zoom_level5_distance; break;
    default: return;
    }
    c->distance_target = target;
    float step = c->distance_target - c->distance;
    step = step / 3.0f;
    c->distance = step + c->distance;
}

void mu_world_camera_apply_zoom(mu_world_camera *c, mu_client_view *v, int32_t min_index)
{
    const int32_t count = 3;
    float table[5] = {20.0f, 30.0f, c->world_fov, 50.0f, 65.0f};
    if (min_index > c->zoom_index)
        c->zoom_index = min_index;
    if (count - 1 < c->zoom_index)
        c->zoom_index = count - 1;
    c->fov_from = v->fov;
    c->fov_to = table[c->zoom_index];
    float diff = c->world_fov - c->fov_to;
    float pitch_drop = mu_camera_lerp_steps(0.0f, 30.8f, mu_cvtt(diff), 26);
    float height_drop = mu_camera_lerp_steps(0.0f, 580.0f, mu_cvtt(diff), 26);
    if (c->zoom_timer.done == 1) {
        c->zoom_timer.duration = 500;
        c->zoom_timer.start = 0;
        c->zoom_timer.done = 0;
        memcpy(c->position_start, v->position, sizeof c->position_start);
        memcpy(c->angle_start, v->angle, sizeof c->angle_start);
    }
    float height = c->distance - 150.0f;
    height = height + c->hero_position[2];
    c->angle_end[0] = -48.5f - pitch_drop;
    c->position_end[2] = height - height_drop;
}

int mu_world_camera_wheel(mu_world_camera *c, mu_client_view *v, float delta, int32_t min_index)
{
    if (fov_follows_world(c) || c->zoom_timer.done == 0)
        return 0;
    if (delta > 0.0f)
        --c->zoom_index;
    else
        ++c->zoom_index;
    mu_world_camera_apply_zoom(c, v, min_index);
    return 1;
}
