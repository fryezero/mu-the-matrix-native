/* Hero movement. See client_movement.h. */
#include "client_movement.h"

#include <math.h>

#include "../record-math/record_math.h"

/* x86 CVTTSS2SI: truncation, INT32_MIN for NaN and out-of-range values. */
static int32_t cvtt(float value)
{
    if (!(value > -2147483904.0f && value < 2147483648.0f))
        return INT32_MIN;
    return (int32_t)value;
}

/* 0x0184f8ff: negates when 0 > v (so -0 and NaN pass through). */
static float client_fabs(float v)
{
    if (0.0f > v)
        return -v;
    return v;
}

float mu_create_angle(float x1, float y1, float x2, float y2)
{
    float nx = x2 - x1;
    float ny = y2 - y1;
    if (0.0001f > client_fabs(nx))
        return 0.0f > ny ? 0.0f : 180.0f;
    if (0.0001f > client_fabs(ny))
        return 0.0f > nx ? 270.0f : 90.0f;
    float ratio = ny / nx;
    float a = (float)atan((double)ratio);      /* 0x012b2bca -> 0x012b2d60 -> CRT atan */
    float angle = a / 3.14159274f;             /* 0x40490fdb */
    angle = angle * 180.0f;
    angle = angle + 90.0f;
    float result;
    if (0.0f > nx && ny >= 0.0f)
        result = angle + 180.0f;
    else if (0.0f > nx && 0.0f > ny)
        result = angle + 180.0f;
    else if (nx >= 0.0f && 0.0f > ny)
        result = angle;
    else
        result = angle;
    return result;
}

float mu_far_angle(float angle, float target, uint8_t abs_flag)
{
    if (0.0f > angle)
        angle = angle + 360.0f;
    if (0.0f > target)
        target = target + 360.0f;
    float d = target - angle;
    if (180.0f > angle) {
        if (target >= angle + 180.0f) {
            d = 360.0f - target;
            d = d + angle;
        }
    } else if (angle - 180.0f > target) {
        d = 360.0f - angle;
        d = d + target;
    }
    if (abs_flag == 1 && 0.0f > d)
        d = -d;
    return d;
}

float mu_turn_angle2(float a, float target, float step)
{
    if (0.0f > a)
        a = a + 360.0f;
    if (0.0f > target)
        target = target + 360.0f;
    if (180.0f > a) {
        float low = a - step;
        if (target >= a + step && a + 180.0f > target)
            return a + step;
        if (low >= 0.0f && (target >= a + 180.0f || low > target))
            return a - step;
        if (0.0f > low && target >= a + 180.0f && low + 360.0f > target) {
            float value = a - step;
            return value + 360.0f;
        }
        return target;
    }
    float high = a + step;
    if (a - step > target && target >= a - 180.0f)
        return a - step;
    if (360.0f > high && (a - 180.0f > target || target >= high))
        return a + step;
    if (high >= 360.0f && a - 180.0f > target && target >= high - 360.0f) {
        float value = a + step;
        return value - 360.0f;
    }
    return target;
}

int mu_move_path(mu_path *p, int32_t tile[2], float position[3], float angles[3], uint8_t turn)
{
    uint8_t success = 0;
    if ((int32_t)p->current >= (int32_t)p->count)
        return success;
    if (p->current_float == 0) {
        int32_t cell = (int32_t)p->current + 1;
        if (cell > (int32_t)p->count - 1)
            cell = (int32_t)p->count - 1;
        tile[0] = p->x[cell];
        tile[1] = p->y[cell];
    }
    float px[4], py[4];
    for (int32_t i = 0; i < 4; ++i) {
        int32_t cell = (int32_t)p->current + i - 1;
        if (cell < 0)
            cell = 0;
        else if (cell > (int32_t)p->count - 1)
            cell = (int32_t)p->count - 1;
        float v = (float)p->x[cell] + 0.5f;
        px[i] = v * 100.0f;
        v = (float)p->y[cell] + 0.5f;
        py[i] = v * 100.0f;
    }
    float tx = 0.0f, ty = 0.0f;
    switch (p->current_float) {
    case 0:
        tx = px[0] * -0.0703125f + px[1] * 0.8671875f;
        tx = tx + px[2] * 0.2265625f;
        tx = tx + px[3] * -0.0234375f;
        ty = py[0] * -0.0703125f + py[1] * 0.8671875f;
        ty = ty + py[2] * 0.2265625f;
        ty = ty + py[3] * -0.0234375f;
        break;
    case 1:
        tx = px[0] * -0.0625f + px[1] * 0.5625f;
        tx = tx + px[2] * 0.5625f;
        tx = tx + px[3] * -0.0625f;
        ty = py[0] * -0.0625f + py[1] * 0.5625f;
        ty = ty + py[2] * 0.5625f;
        ty = ty + py[3] * -0.0625f;
        break;
    case 2:
        tx = px[0] * -0.0234375f + px[1] * 0.2265625f;
        tx = tx + px[2] * 0.8671875f;
        tx = tx + px[3] * -0.0703125f;
        ty = py[0] * -0.0234375f + py[1] * 0.2265625f;
        ty = ty + py[2] * 0.8671875f;
        ty = ty + py[3] * -0.0703125f;
        break;
    case 3:
        tx = px[2];
        ty = py[2];
        break;
    default:
        break;
    }
    float dx = position[0] - tx;
    float dy = position[1] - ty;
    float sum = dx * dx + dy * dy;
    float distance = (float)sqrt((double)sum);   /* 0x00961a07 */
    if (cvtt(distance) <= 30) {
        p->current_float = (uint8_t)(p->current_float + 1);
        if ((int32_t)p->current_float > 3) {
            p->current_float = 0;
            p->current = (uint8_t)(p->current + 1);
            if ((int32_t)p->current >= (int32_t)p->count - 1) {
                p->current = (uint8_t)(p->count - 1);
                tile[0] = p->x[p->current];
                tile[1] = p->y[p->current];
                position[0] = tx;
                position[1] = ty;
                success = 1;
            }
        }
    }
    if (!success && turn) {
        float angle = mu_create_angle(position[0], position[1], tx, ty);
        float far = mu_far_angle(angles[2], angle, 1);
        if (far >= 45.0f)
            angles[2] = angle;
        else
            angles[2] = mu_turn_angle2(angles[2], angle, far * 0.5f);
    }
    return success;
}

static int32_t index_repeat(int32_t x, int32_t y)
{
    return (int32_t)(((uint32_t)y & 0xffu) << 8) + (int32_t)((uint32_t)x & 0xffu);   /* 0x016d34db */
}

float mu_request_terrain_height(const float *height, const uint16_t *wall, float special_height,
                                int32_t scene_state, float x, float y)
{
    if (scene_state == 1 || scene_state == 2 || scene_state == 4)
        return 0.0f;
    if (0.0f > x || 0.0f > y)
        return 0.0f;
    x = x / 100.0f;
    y = y / 100.0f;
    uint32_t index = (uint32_t)cvtt(y) * 256u + (uint32_t)cvtt(x);   /* 0x016d34cd, no wrap */
    if (index >= 0x10000u)
        return special_height;
    if (wall[index] & 0x40)
        return special_height;
    int32_t xi = cvtt(x), yi = cvtt(y);
    float xd = x - (float)xi;
    float yd = y - (float)yi;
    int32_t i1 = index_repeat(xi, yi), i2 = index_repeat(xi, yi + 1);
    int32_t i3 = index_repeat(xi + 1, yi), i4 = index_repeat(xi + 1, yi + 1);
    float left = height[i2] - height[i1];
    left = left * yd;
    left = left + height[i1];
    float right = height[i4] - height[i3];
    right = right * yd;
    right = right + height[i3];
    float value = right - left;
    value = value * xd;
    return value + left;
}

/* run < 10: 15, < 20: 16, else 17 (the shared helper ladder). */
static float ladder(uint8_t run)
{
    if (run < 10)
        return 15.0f;
    if (run < 20)
        return 16.0f;
    return 17.0f;
}

float mu_character_move_speed(const mu_move_speed_input *in, uint8_t *run)
{
    float speed = (float)in->move_speed;
    if (in->object_type == 0xa91 && in->object_kind == 1) {
        if (in->special_state) {
            *run = 40;
            return 8.0f;
        }
        speed = *run < 40 ? 12.0f : 15.0f;
        int32_t helper = in->helper_type;
        if (helper == 0xffff)
            helper = in->mount_type;
        if (helper != 0xffff) {
            switch (helper) {
            case 0x1833: case 0x1834: case 0x1835: case 0x1836: case 0x1853: case 0x1854: case 0x185d: case 0x185e:
            case 0x184b: case 0x184c: case 0x19d7: case 0x19e3: case 0x19e4:
                speed = ladder(*run);
                break;
            case 0x1a02: case 0x1a03:
                if (in->subtype != 0x431 && in->subtype != 0x432) {
                    *run = 40;
                    speed = 15.0f;
                }
                break;
            case 0x1a04: case 0x28f7:
                if (in->safe_zone) {
                    speed = ladder(*run);
                } else {
                    *run = 40;
                    speed = 17.0f;
                }
                break;
            case 0x1a25:
                if (*run < 10)
                    speed = 15.0f;
                else if (*run < 20)
                    speed = 16.0f;
                else
                    speed = in->helper_option > 0 ? 19.0f : 17.0f;
                break;
            default:
                break;
            }
        }
        if (in->mounted_item) {
            if (in->safe_zone) {
                speed = ladder(*run);
            } else {
                *run = 40;
                speed = 17.0f;
            }
        }
        if (helper == 0xffff && in->wing_type != -1 && !in->safe_zone && in->subtype != 0x431 &&
            in->subtype != 0x432) {
            int16_t wing = in->wing_type;
            *run = 40;
            speed = (wing == 0x22eb || wing == 0x230a || wing == 0x248d || wing == 0x2495) ? 16.0f : 15.0f;
        }
        if (in->transformed) {
            *run = 40;
            speed = 20.0f;
        }
    }
    if (in->world_runs) {
        *run = 40;
        speed = 15.0f;
    }
    if (in->stunned)
        return 17.0f;
    if (in->buffs & MU_BUFF_18B)
        speed = (float)((double)speed + in->buff_18b_bonus);
    if (in->buffs & (MU_BUFF_38 | MU_BUFF_B8 | MU_BUFF_BA | MU_BUFF_D1 | MU_BUFF_D2 | MU_BUFF_F0))
        speed = speed * 0.5f;
    else if (in->buffs & MU_BUFF_56)
        speed = speed * 0.33f;
    else if (in->buffs & MU_BUFF_112)
        speed = speed * 0.5f;
    else if (in->buffs & MU_BUFF_116)
        speed = speed * 0.5f;
    if (in->buffs & MU_BUFF_20) {
        *run = 40;
        speed = 20.0f;
    }
    return speed;
}

void mu_move_character_position(const mu_position_input *in, float position[3], const float angles[3], float *timer)
{
    float matrix[12];
    mu_angle_matrix(angles, matrix);
    float velocity[3] = {0.0f, -in->speed, 0.0f}, step[3];
    mu_vector_rotate(velocity, matrix, step);
    position[0] = position[0] + step[0];
    position[1] = position[1] + step[1];
    position[2] = position[2] + step[2];
    int plain = in->world == -1 || in->helper_type != 0x1a03 || in->safe_zone == 1;
    float ground = mu_request_terrain_height(in->height, in->wall, in->special_height, in->scene_state, position[0],
                                             position[1]);
    if (plain)
        position[2] = ground;
    else if (in->world == 8 || in->world == 10 || in->world == 0x84)
        position[2] = ground + 90.0f;
    else
        position[2] = ground + 30.0f;
    if (in->object_type == 0x7a7) {
        float s = (float)sin((double)*timer);   /* 0x009681bd */
        s = client_fabs(s);
        float bob = -s * 70.0f;
        bob = bob + 70.0f;
        position[2] = bob + position[2];
    }
    *timer = *timer + 0.15f;
}

int mu_set_action(uint16_t *action, uint16_t *prior_action, float *frame, float *prior_frame, int32_t action_count,
                  int32_t new_action)
{
    if (new_action >= action_count)
        return 0;
    if ((int32_t)*action == new_action)
        return 0;
    *prior_action = *action;
    *prior_frame = *frame;
    *action = (uint16_t)new_action;
    *frame = 0.0f;
    return 1;
}

static int base_class(uint8_t class_byte)
{
    return class_byte & 0xf;   /* 0x0095f5cc */
}

/* Per base class (low nibble), from emulating 0x0139002a and 0x01391e55 for
 * every class byte in the minimal domain (see the header). */
static const uint8_t walk_female[16] = {0, 0, 1, 0, 0, 1, 0, 1, 1, 1, 0, 0, 1, 0, 1, 0};
static const uint8_t stop_action[16] = {1, 1, 2, 1, 1, 3, 1, 5, 6, 6, 1, 1, 2, 1, 6, 8};

uint8_t mu_player_walk_run(uint8_t class_byte, uint8_t safe_zone, int32_t world, uint8_t run)
{
    if (safe_zone == 1 && world != 0x84)
        run = 0;
    if (run >= 40)
        return run;
    if (safe_zone && world != 0x84)
        return run;
    int c = base_class(class_byte);
    if (c == 3 || c == 4 || c == 6 || c == 7)
        run = (uint8_t)(run + 1);
    return run;
}

int32_t mu_player_walk_action(uint8_t class_byte, uint8_t run, float *speed)
{
    int c = base_class(class_byte);
    if (run >= 40) {
        if (c == 11) {
            *speed = 0.35f;   /* not rewritten by SetPlayerWalk: the loader value */
            return MU_PLAYER_RUN_CLASS11;
        }
        *speed = c == 6 ? 0.28f : 0.34f;
        return MU_PLAYER_RUN;
    }
    *speed = c == 6 ? 0.32f : 0.33f;
    return walk_female[c] ? MU_PLAYER_WALK_FEMALE : MU_PLAYER_WALK_MALE;
}

int32_t mu_player_stop_action(uint8_t class_byte)
{
    return stop_action[base_class(class_byte)];
}

float mu_player_stop_speed(int32_t action)
{
    switch (action) {
    case 1: case 2: case 5: case 6: case 8: return 0.28f;
    case 3: return 0.24f;
    default: return 0.0f;
    }
}
