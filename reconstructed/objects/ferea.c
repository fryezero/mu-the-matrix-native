/* Ferea, world 112. Create 0x00de5cb0, move 0x00de5de2 and visual 0x00de6405 (RENDER-WORLDS-Q2); none tests
 * the world. */
#include "worlds_q_internal.h"
#include "charsel_world.h"

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

/* ---- RENDER-WORLDS-Q2: the visual slot 0x00de6405 (ret 8; false without object or model) ---- */

/* The bone names each type looks up through 0x0129f18a(std::string name, 0) (data 0x01aa8314..0x01aa8398). */
static const char *const ferea_bones_17[] = {"mansionA007", NULL};
static const char *const ferea_bones_36[] = {"e01", "e02", "e03", "e04", "e05", "e06", NULL};
static const char *const ferea_bones_75[] = {"Point02", "Point03", "objSphere002", NULL};
static const char *const ferea_bones_87[] = {"Bone21", "Bone01", NULL};
static const char *const ferea_bones_95[] = {"e01", "e02", "e04", "e03", "e05", "e06", "e08", "e07", NULL};
static const char *const ferea_bones_123[] = {"Crowd01", NULL};
static const char *const ferea_bones_129[] = {"Bone02", NULL};
static const char *const ferea_bones_148[] = {"E01", NULL};

const char *const *mu_ferea_visual_bones(int32_t type)
{
    switch (type) {
    case 17: return ferea_bones_17;
    case 36: return ferea_bones_36;
    case 75: case 81: return ferea_bones_75;
    case 87: return ferea_bones_87;
    case 95: return ferea_bones_95;
    case 123: return ferea_bones_123;
    case 129: return ferea_bones_129;
    case 148: return ferea_bones_148;
    default: return NULL;
    }
}

/* TransformPosition(bone matrix of `name`, local, out): the name was resolved before any request. */
static void ferea_bone(const mu_q_inputs *in, const char *name, const float local[3], float out[3])
{
    in->bone(in->context, in->bone_index(in->context, name), local, out);
}

/* CreateEffect(type, position, angle, light, sub, 0, -1, 0, 0, 0, scale, -1, 0, 0): no owner. */
static void ferea_effect(mu_obj_log *log, int32_t i, uint32_t type, const float p[3], const float a[3],
                         const float l[3], uint32_t sub, float scale)
{
    mu_obj_event *e = wb_event(log, MU_OBJ_CALL_EFFECT, i);
    wb_arg(e, type);
    wb_vec(e, p);
    wb_vec(e, a);
    wb_vec(e, l);
    wb_arg(e, sub);
    wb_arg(e, 0);
    wb_float(e, scale);
}

/* (float)(int) by cvttss2si: the integer indefinite for NaN and out-of-range values. */
static int32_t ferea_trunc(float v)
{
    return wb_int(v);
}

/* rand_range(0, hi, 1) == 0, the gate of most particles. */
static int ferea_zero(const mu_q_inputs *in, float hi)
{
    return q_rand_range(in, 0.0f, hi, 1) == 0.0f;
}

int mu_ferea_visual(const uint8_t *o, int32_t index, int model_present, const mu_q_inputs *in, mu_obj_log *log)
{
    if (!o || !model_present)
        return 0;
    const int32_t type = mu_obj_i32(o, MU_OBJF_TYPE);
    const char *const *names = mu_ferea_visual_bones(type);
    if (names) {   /* the client faults on a missing bone (TransformPosition of a null matrix) */
        if (!in->bone || !in->bone_index)
            return -1;
        for (int k = 0; names[k]; ++k)
            if (in->bone_index(in->context, names[k]) < 0)
                return -1;
    }
    float pos[3], angle[3];
    wb_get(o, MU_OBJF_POSITION, pos);
    wb_get(o, MU_OBJF_ANGLE, angle);
    const float scale = mu_obj_f32(o, MU_OBJF_SCALE), zero[3] = {0.0f, 0.0f, 0.0f}, white[3] = {1.0f, 1.0f, 1.0f};
    switch (type) {
    case 6:
        return 1;
    case 9: {
        const uint32_t phase = in->now_ms % 100u;
        if (ferea_zero(in, 10.0f) && phase < 30u) {
            const float l[3] = {0.0500000007f, 0.0500000007f, 0.0f};
            q_particle(log, index, 0x7f89, pos, angle, l, 0x1c, scale, 1);
        }
        return 1;
    }
    case 17: {
        const float s = q_rand_range(in, 0.579999983f, 0.75999999f, 100) * scale;
        float b[3];
        ferea_bone(in, names[0], zero, b);
        const float top[3] = {b[0], b[1], b[2] + 25.0f}, fire[3] = {1.0f, 0.200000003f, 0.0f};
        ferea_effect(log, index, 0x413, b, angle, white, 0xa, s);
        q_sprite(log, index, 0x7ef7, top, 2.0f * scale, fire, 0.0f);
        goto smoke;
    }
    case 28: case 32: case 33: case 130: {
        static const float lights[4][3] = {{0.0f, 0.0299999993f, 0.0f}, {0.0299999993f, 0.0f, 0.0599999987f},
                                           {0.0500000007f, 0.0f, 0.0f}, {0.0299999993f, 0.0299999993f, 0.0700000003f}};
        if (ferea_zero(in, 4.0f))
            q_particle(log, index, 0x7f89, pos, angle, lights[type == 28 ? 0 : type == 32 ? 1 : type == 33 ? 2 : 3],
                       0x1b, scale, 1);
        return 1;
    }
    case 36: {
        const float glow[3] = {1.29999995f, 1.29999995f, 1.89999998f}, dim[3] = {0.150000006f, 0.150000006f, 0.150000006f};
        for (uint32_t k = 0; names[k]; ++k) {
            const float base = (float)mu_obj_i32(o, 0x64) + in->time;
            const float arg = (float)((double)base * 0.0002 * (double)k);
            const float sine = q_sin(arg), s = (sine < 0.0f ? -sine : sine) * 0.400000006f;   /* 0x0184f8ff */
            float b[3];
            ferea_bone(in, names[k], zero, b);
            const float l[3] = {glow[0] * s, glow[1] * s, glow[2] * s};
            q_sprite(log, index, 0x7f26, b, 2.0f, l, 0.0f);
            q_sprite(log, index, 0x7f26, b, 1.5f, dim, 0.0f);
        }
        return 1;
    }
    case 71:
    smoke: {
        const float l[3] = {0.300000012f, 0.200000003f, 0.200000003f}, p[3] = {pos[0], pos[1], pos[2] + 110.0f};
        if (ferea_zero(in, 4.0f))
            q_particle(log, index, 0x7f5a, p, angle, l, 0x45, scale, 1);
        return 1;
    }
    case 72: {
        const float fire[3] = {1.0f, 0.200000003f, 0.0f};
        ferea_effect(log, index, 0x413, pos, angle, white, 0xa, scale);
        q_sprite(log, index, 0x7ef7, pos, 2.0f * scale, fire, 0.0f);
        return 1;
    }
    case 75: case 81: {
        const float blue[3] = {0.5f, 0.800000012f, 1.0f}, orange[3] = {1.0f, 0.5f, 0.0f};
        if (!ferea_zero(in, 1.0f))
            q_particle(log, index, 0x7efa, pos, angle, type == 81 ? orange : blue, 6, 1.0f, 1);
        for (int k = 0; names[k]; ++k) {
            float b[3];
            ferea_bone(in, names[k], zero, b);
            q_sprite(log, index, 0x7ef7, b, 1.5f, blue, 0.0f);
        }
        return 1;
    }
    case 87: {
        float b[3];
        ferea_bone(in, names[0], zero, b);
        const float up[3] = {b[0], b[1], b[2] + 30.0f}, at[3] = {b[0], b[1], b[2]};
        q_particle(log, index, 0x801c, up, angle, white, 0xe, scale * 0.699999988f, 0);
        if (ferea_zero(in, 2.0f))
            q_particle(log, index, 0x801b, at, angle, white, 2, scale * 0.400000006f, 0);
        ferea_bone(in, names[1], zero, b);
        const float up2[3] = {b[0], b[1], b[2] + 45.0f};
        q_particle(log, index, 0x801c, up2, angle, white, 0xe, scale, 0);
        if (ferea_zero(in, 2.0f))
            q_particle(log, index, 0x801b, up2, angle, white, 2, scale, 0);
        return 1;
    }
    case 95: {
        float b[3];
        for (int k = 0; k < 4; ++k) {
            ferea_bone(in, names[k], zero, b);
            q_particle(log, index, 0x801c, b, angle, white, 0xe, scale * 0.5f, 0);
            if (ferea_zero(in, 2.0f))
                q_particle(log, index, 0x801b, b, angle, white, 2, scale * 0.5f, 0);
        }
        for (int k = 4; k < 8; ++k) {
            ferea_bone(in, names[k], zero, b);
            const float up[3] = {b[0], b[1], b[2] + 15.0f};
            q_particle(log, index, 0x801c, b, angle, white, 0xe, scale, 0);
            if (ferea_zero(in, 2.0f))
                q_particle(log, index, 0x801b, up, angle, white, 2, scale, 0);
        }
        return 1;
    }
    case 123: {
        float l[3] = {0.100000001f, 0.899999976f, 0.899999976f};
        if (in->handler->ferea_state == 3 || in->handler->ferea_state == 2) {
            l[0] = 0.899999976f;
            l[1] = l[2] = 0.200000003f;
        }
        const float s = q_rand_range(in, 0.546000004f, 0.713999987f, 1000) * scale;
        float b[3];
        ferea_bone(in, names[0], zero, b);
        ferea_effect(log, index, 0x413, b, angle, l, 0x11, s);
        const float dim[3] = {l[0] * 0.300000012f, l[1] * 0.300000012f, l[2] * 0.300000012f};
        const float up[3] = {b[0], b[1], b[2] + 40.0f};
        if (ferea_zero(in, 4.0f))
            q_particle(log, index, 0x7f5a, up, angle, dim, 0x45, scale, 1);
        return 1;
    }
    case 128:
        if (ferea_zero(in, 34.0f)) {
            const float r = q_rand_range(in, 0.0299999993f, 0.479999989f, 100), l[3] = {r, r, r};
            q_particle(log, index, 0x7dea, pos, angle, l, 0, scale, 1);
        }
        return 1;
    case 129: {
        const float w = q_sin((angle[2] * 5.0f + in->time) * 0.00200000009f) * 0.300000012f + 0.699999988f;
        const float l[3] = {w / 1.70000005f, w, w};
        float b[3];
        ferea_bone(in, names[0], zero, b);
        q_sprite(log, index, 0x8021, b, w * 1.5f, l, 0.0f);
        return 1;
    }
    case 140:
        if (ferea_zero(in, 1.0f))
            q_particle(log, index, 0x801a, pos, angle, white, 2, scale, 0);
        return 1;
    case 141:
        q_particle(log, index, 0x801c, pos, angle, white, 4, scale, 0);
        return 1;
    case 142:
        if (ferea_zero(in, 2.0f))
            q_particle(log, index, 0x801b, pos, angle, white, 2, scale, 0);
        return 1;
    case 148: {
        float b[3];
        ferea_bone(in, names[0], zero, b);
        const float r = (float)(ferea_trunc(in->time) % 3600) * 0.100000001f;
        float l[3] = {0.400000006f, q_sin(in->time * 0.699999988f) * 0.200000003f + 0.300000012f + 0.5f, 0.400000006f};
        q_sprite(log, index, 0x7f67, b, scale * 0.400000006f * 1.20000005f, l, -r);
        l[0] = 0.100000001f, l[1] = 0.400000006f, l[2] = 0.980000019f;
        q_sprite(log, index, 0x8145, b, scale * 0.400000006f * 0.349999994f, l, r);
        if (ferea_zero(in, 2.0f)) {
            l[0] = 0.400000006f, l[1] = 0.400000006f, l[2] = 1.0f;
            b[2] += 15.0f;
            q_particle(log, index, 0x8017, b, angle, l, 0, scale * 0.400000006f * 1.79999995f, 0);
        }
        return 1;
    }
    default:
        return 0;
    }
}
