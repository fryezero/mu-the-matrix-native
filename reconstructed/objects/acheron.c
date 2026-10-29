/* Acheron, worlds 91/92 (predicate 0x00d6a614). Create 0x00d6a6d7, move 0x00d6a7aa, visual 0x00d6ae34.
 * None of the three tests the object pointer. */
#include "worlds_q_internal.h"

static int acheron_world(int32_t world) { return world == 0x5b || world == 0x5c; }

int mu_acheron_create(uint8_t *o, const mu_q_inputs *in)
{
    if (!acheron_world(in->world))
        return 0;
    mu_obj_set_i32(o, 0x64, 0);
    switch (mu_obj_i32(o, MU_OBJF_TYPE)) {
    case 27: case 29:
        mu_obj_set_f32(o, MU_OBJF_RANGE, -3000.0f);
        break;
    case 60: case 61: case 62:
        mu_obj_set_f32(o, MU_OBJF_RANGE, -428.571442f);
        break;
    case 38: case 54: case 55: case 56: case 57: case 69: case 80:
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
        break;
    default:
        break;
    }
    return 1;
}

/* s = (rand % n + 3) * 0.1 */
static float flicker(const mu_q_inputs *in, int32_t n) { return (float)(in->rand_fn(in->context) % n + 3) * 0.1f; }

static void light_at(mu_obj_log *log, int32_t i, const uint8_t *o, const float rgb[3], int32_t range)
{
    q_add_light(log, i, mu_obj_f32(o, MU_OBJF_POSITION), mu_obj_f32(o, MU_OBJF_POSITION + 4), rgb, range);
}

/* Types 16 and 52: at the end of the action, a countdown at +0x64 alternates actions 0 and 1. */
static void cycle(uint8_t *o, const uint8_t *record, const mu_q_inputs *in)
{
    if (!q_action_ended(o, record))
        return;
    if (mu_obj_i32(o, 0x64) <= 0) {
        mu_obj_set_i32(o, 0x64, in->rand_fn(in->context) % 3 + 4);
        q_set_action(in, o, 1);
    } else {
        q_set_action(in, o, 0);
        mu_obj_set_i32(o, 0x64, mu_obj_i32(o, 0x64) - 1);
    }
}

int mu_acheron_move(uint8_t *o, int32_t index, const mu_q_inputs *in, mu_obj_log *log)
{
    if (!acheron_world(in->world))
        return 0;
    /* 0x00eaaa44's record is copied whole; the original reads through a null record (no model or an
     * action outside the table), which is taken here as a zero record. */
    static const uint8_t zero[16];
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    switch (t) {
    case 9: {
        const float s = flicker(in, 2), rgb[3] = {s * 1.2f, s * 0.5f, s * 0.7f};
        light_at(log, index, o, rgb, 2);
        return 1;
    }
    case 16: {
        const uint8_t *record = q_action_at(in, o);
        if (!record)
            record = zero;
        /* action 1 scales the colour by |sin(frame / keys * 3.14)|, which the next line overwrites */
        const float s = flicker(in, 2), rgb[3] = {s * 1.2f, s * 0.6f, s * 0.4f};
        light_at(log, index, o, rgb, 3);
        cycle(o, record, in);
        return 1;
    }
    case 22:
        mu_obj_set_f32(o, MU_OBJF_BLEND_V, mu_obj_f32(o, MU_OBJF_BLEND_V) - 0.01f);
        return 1;
    case 23: case 24:
        mu_obj_set_f32(o, MU_OBJF_BLEND_V, mu_obj_f32(o, MU_OBJF_BLEND_V) - 0.02f);
        return 1;
    case 25: case 26:
        mu_obj_set_f32(o, MU_OBJF_BLEND_V, mu_obj_f32(o, MU_OBJF_BLEND_V) - 0.03f);
        return 1;
    case 52: {
        const uint8_t *record = q_action_at(in, o);
        cycle(o, record ? record : zero, in);
        return 1;
    }
    case 73: {
        const float s = flicker(in, 4), rgb[3] = {s * 0.2f, s * 0.6f, s};
        light_at(log, index, o, rgb, 3);
        return 1;
    }
    case 78:
        mu_obj_set_f32(o, MU_OBJF_BLEND_U, mu_obj_f32(o, MU_OBJF_BLEND_U) + 0.01f);
        return 1;
    case 100: {
        const float s = flicker(in, 2), rgb[3] = {s * 0.4f, s * 0.7f, s * 1.2f};
        light_at(log, index, o, rgb, 2);
        return 1;
    }
    default:
        return 0;
    }
}

int mu_acheron_visual_bones(int32_t type)
{
    switch (type) {
    case 9: return 17;
    case 16: return 28;
    case 31: return 8;
    case 52: return 3;
    case 73: return 1;
    case 89: return 25;
    case 93: return 11;
    case 100: return 25;
    default: return -1;
    }
}

static void bone_at(const mu_q_inputs *in, int32_t bone, float out[3])
{
    static const float local[3] = {0.0f, 0.0f, 0.0f};
    in->bone(in->context, bone, local, out);
}

/* TransformPosition of the bone, then a CreateSprite 0x8155 there. */
static void bone_sprite(const mu_q_inputs *in, mu_obj_log *log, int32_t i, int32_t bone, float scale,
                        const float light[3])
{
    float p[3];
    bone_at(in, bone, p);
    q_sprite(log, i, 0x8155, p, scale, light, 0.0f);
}

int mu_acheron_visual(const uint8_t *o, int32_t index, const mu_q_inputs *in, mu_obj_log *log)
{
    if (!acheron_world(in->world))
        return 0;
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    if (mu_acheron_visual_bones(t) >= 0 && !in->bone)
        return -1;
    float pos[3], angle[3];
    wb_get(o, MU_OBJF_POSITION, pos);
    wb_get(o, MU_OBJF_ANGLE, angle);
    const float scale = mu_obj_f32(o, MU_OBJF_SCALE), white[3] = {1.0f, 1.0f, 1.0f};
    switch (t) {
    case 9: {
        const float a[3] = {0.937254906f, 0.188235298f, 0.219607845f}, b[3] = {0.937254906f, 0.278431386f,
                            0.301960796f}, c[3] = {1.0f, 0.160784319f, 0.141176477f};
        bone_sprite(in, log, index, 6, 1.5f, a);
        bone_sprite(in, log, index, 11, 1.5f, b);
        bone_sprite(in, log, index, 17, 1.5f, c);
        return 1;
    }
    case 16: {
        float c = 0.3f;
        if (mu_obj_u16(o, MU_OBJF_ACTION) == 1)
            c = q_sin(mu_obj_f32(o, MU_OBJF_FRAME) / 24.0f * 3.1400001f) * 0.699999988f + c;
        const float light[3] = {0.980000019f * c, 0.579999983f * c, 0.579999983f * c};
        for (int32_t k = 10; k <= 28; k += 6)
            bone_sprite(in, log, index, k, 4.5f, light);
        return 1;
    }
    case 31: {
        const float a[3] = {0.980000019f, 0.939999998f, 0.939999998f}, b[3] = {0.779999971f, 0.439999998f, 0.75f},
                    c[3] = {0.579999983f, 0.0700000003f, 0.560000002f};
        bone_sprite(in, log, index, 6, 1.0f, a);
        bone_sprite(in, log, index, 7, 1.2f, b);
        bone_sprite(in, log, index, 8, 0.8f, c);
        return 1;
    }
    case 38:
        if (in->rand_fn(in->context) % 6 == 0) {
            const float light[3] = {0.0199999996f, 0.0199999996f, 0.0500000007f};
            q_particle(log, index, 0x7f89, pos, angle, light, 0x14, scale, 1);
        }
        return 1;
    case 52: {
        const float s = q_sin((float)(wb_int(in->time) % 3000) * 0.00104666676f) * 0.1f;
        float p[3];
        bone_at(in, 3, p);
        if (in->rand_fn(in->context) % 7 == 0) {
            const float light[3] = {0.600000024f, 1.0f, 1.0f};
            q_particle(log, index, 0x7efa, p, angle, light, 2, 0.25f, 0);
        }
        const float glow[3] = {0.200000003f, 0.649999976f, 0.649999976f};
        q_sprite(log, index, 0x7ef7, p, 1.5f + s, glow, 0.0f);
        if (mu_obj_u16(o, MU_OBJF_ACTION) == 1) {
            const float up[3] = {0.0f, 0.0f, 1.0f}, light[3] = {0.300000012f, 0.949999988f, 0.949999988f};
            q_particle(log, index, 0x7f26, p, up, light, 0xe, 0.0599999987f, 0);
        }
        return 1;
    }
    case 54:
        if (in->rand_fn(in->context) % 2 == 0)
            q_particle(log, index, 0x801a, pos, angle, white, 2, scale, 0);
        return 1;
    case 55:
        q_particle(log, index, 0x801c, pos, angle, white, 0xe, scale * 2.0f, 0);
        return 1;
    case 56:
        if (in->rand_fn(in->context) % 3 == 0)
            q_particle(log, index, 0x801b, pos, angle, white, 2, scale, 0);
        return 1;
    case 57:
        if (in->rand_fn(in->context) % 100 == 0)
            q_effect(log, index, o, 0x59a, white, 3, 0);
        return 1;
    case 69:
        if (in->rand_fn(in->context) % 3 == 0) {
            const float light[3] = {0.400000006f, 0.600000024f, 0.699999988f};
            q_particle(log, index, 0x802a, pos, angle, light, 1, 1.0f, 0);
        }
        return 1;
    case 73: {
        float p[3];
        bone_at(in, 1, p);
        float light[3] = {0.400000006f, q_sin(in->time * 0.699999988f) * 0.200000003f + 0.300000012f + 0.5f,
                          0.400000006f};
        const float s = (float)(in->rand_fn(in->context) % 30) / 60.0f;
        const float r = (float)(wb_int(in->time) % 3600) * 0.100000001f;
        q_sprite(log, index, 0x7f67, p, 1.20000005f + s, light, -r);
        light[0] = 0.5f; light[1] = 1.0f; light[2] = 0.980000019f;
        q_sprite(log, index, 0x8145, p, 0.349999994f, light, r);
        if (in->rand_fn(in->context) % 3 == 0) {
            p[2] += 15.0f;
            q_particle(log, index, 0x8017, p, angle, white, 0, scale * 1.79999995f, 0);
        }
        return 1;
    }
    case 80:
        if (in->rand_fn(in->context) % 8 == 0) {
            const float light[3] = {0.980000019f, 0.899999976f, 0.899999976f};
            q_particle(log, index, 0x7f5a, pos, angle, light, 0x45, scale, 0);
        }
        return 1;
    case 89: {
        const float light[3] = {0.159999996f, 0.0799999982f, 0.600000024f};
        for (int32_t k = 18; k < 26; ++k) {
            const float s = k == 18 || (k >= 20 && k <= 23) ? 1.79999995f : 0.699999988f;
            float p[3];
            bone_at(in, k, p);
            q_sprite(log, index, 0x8155, p, s, light, 0.0f);
            q_sprite(log, index, 0x8155, p, s, light, 0.0f);
        }
        return 1;
    }
    case 93:
        for (int32_t k = 0; k < 15; ++k) {
            float s;
            if (k == 6 || k == 10 || k == 11)
                s = 0.449999988f;
            else if (k == 3 || k == 7)
                s = 0.699999988f;
            else
                continue;
            const float c = flicker(in, 2) * 2.0f, light[3] = {c, c, c};
            bone_sprite(in, log, index, k, s, light);
        }
        return 1;
    case 100: {
        const float light[3] = {0.270000011f, 0.560000002f, 0.860000014f};
        bone_sprite(in, log, index, 6, 1.20000005f, light);
        bone_sprite(in, log, index, 17, 1.20000005f, light);
        bone_sprite(in, log, index, 25, 1.20000005f, light);
        bone_sprite(in, log, index, 16, 0.800000012f, light);
        bone_sprite(in, log, index, 24, 0.800000012f, light);
        bone_sprite(in, log, index, 15, 0.600000024f, light);
        return 1;
    }
    default:
        return 0;
    }
}
