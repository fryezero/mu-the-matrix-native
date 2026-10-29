/* Ferea, world 112. Create 0x00de5cb0 and move 0x00de5de2; neither tests the world. The visual slot
 * 0x00de6405 (2,328 instructions) is not reconstructed. */
#include "worlds_q_internal.h"

int mu_ferea_create(uint8_t *o, const mu_q_inputs *in)
{
    if (!o)
        return 0;
    switch (mu_obj_i32(o, MU_OBJF_TYPE)) {
    case 10: case 18: case 22: case 26: case 29: case 31: case 34: case 37: case 60: case 65: case 84: case 97:
    case 98: case 106: case 114: case 126: case 127: case 137: case 152: case 153: case 154:
        mu_obj_set_f32(o, MU_OBJF_RANGE, -400.0f);
        return 1;
    case 39:   /* the handler keeps the object and gives it the current state as its action */
        in->handler->ferea_object = o;
        q_set_action(in, o, in->handler->ferea_state);
        return 1;
    default:
        return 0;
    }
}

/* AddTerrainLight(x, y, colour * q_rand_range(lo, hi, steps), 1, frame light). */
static void light(const mu_q_inputs *in, mu_obj_log *log, int32_t i, float x, float y, const float colour[3],
                  float lo, float hi, uint32_t steps)
{
    const float r = q_rand_range(in, lo, hi, steps), rgb[3] = {colour[0] * r, colour[1] * r, colour[2] * r};
    q_add_light(log, i, x, y, rgb, 1);
}

int mu_ferea_move(uint8_t *o, int32_t index, const mu_q_inputs *in, mu_obj_log *log)
{
    if (!o)
        return 0;
    const float x = mu_obj_f32(o, MU_OBJF_POSITION), y = mu_obj_f32(o, MU_OBJF_POSITION + 4);
    switch (mu_obj_i32(o, MU_OBJF_TYPE)) {
    case 6: case 9: case 28: case 32: case 33: case 71: case 128: case 129: case 130: case 140: case 141: case 142:
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
        return 1;
    case 17: {
        const float colour[3] = {0.800000012f, 0.300000012f, 0.200000003f};
        light(in, log, index, x, y, colour, 0.0f, 0.159999996f, 100);
        return 1;
    }
    case 43:
        mu_obj_set_f32(o, MU_OBJF_BLEND_V, mu_obj_f32(o, MU_OBJF_BLEND_V) - 0.0199999996f);
        return 1;
    case 51: {
        const int32_t tx = in->hero_tile[0], ty = in->hero_tile[1];
        const int inside = tx >= 21 && tx <= 48 && ty >= 106 && ty <= 138;
        mu_obj_set_f32(o, MU_OBJF_ALPHA_TARGET, inside ? 0.100000001f : 1.0f);
        return 1;
    }
    case 123: {
        /* A light 80 units behind the object along its heading (angle z in degrees). */
        float colour[3] = {0.0f, 0.449999988f, 0.449999988f};
        if (in->handler->ferea_state == 3)   /* 0x00cfcede assigns the scalar to all three */
            colour[0] = colour[1] = colour[2] = 0.300000012f;
        const float r = q_rand_range(in, 0.300000012f, 0.600000024f, 10);
        const float dx = x - x, dy = (y - 80.0f) - y;
        const float a = mu_obj_f32(o, MU_OBJF_ANGLE + 8) * 0.0174532924f;
        const float lx = q_cos(a) * dx + x - q_sin(a) * dy;
        const float ly = q_sin(a) * dx + y + q_cos(a) * dy;
        const float rgb[3] = {colour[0] * r, colour[1] * r, colour[2] * r};
        q_add_light(log, index, lx, ly, rgb, 1);
        return 1;
    }
    case 72: {
        const float colour[3] = {1.0f, 0.200000003f, 0.0f};
        light(in, log, index, x, y, colour, 0.300000012f, 0.800000012f, 10);
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
        return 1;
    }
    default:
        return 0;
    }
}
