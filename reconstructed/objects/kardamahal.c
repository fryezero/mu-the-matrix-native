/* Kardamahal, world 143. Create 0x00e0ea04, move 0x00e0ed1c, visual 0x00e117e8; predicate 0x00e136f3. */
#include "worlds_r2.h"
#include "worlds_b_internal.h"
int mu_kardamahal_create(uint8_t *o, int32_t world)
{
    if (world != 143 || !o) return 0;
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    switch (t) {
    case 0:
        mu_obj_set_f32(o, MU_OBJF_POSITION + 8, 64.0f);
        o[MU_OBJF_AFTER_CHARACTER] = 1;
        o[MU_OBJF_LIGHT_FULL] = 0;
        o[MU_OBJF_LIGHT_ENABLE] = 0;
        o[MU_OBJF_VISIBLE] = 0;
        break;
    case 4: case 28: case 114:
        o[MU_OBJF_AFTER_CHARACTER] = 1; break;
    case 34: case 35: case 36: case 37: case 38: case 39: case 40: case 41: case 42: case 43: case 44: case 45:
    case 46: case 47: case 69: case 106: case 107: case 109:
        o[MU_OBJF_LIGHT_DYNAMIC] = 0; break;
    case 78: mu_obj_set_f32(o, MU_OBJF_RANGE, -50.0f); break;
    case 110: mu_obj_set_f32(o, MU_OBJF_RANGE, -230.0f); break;
    case 115: mu_obj_set_f32(o, MU_OBJF_RANGE, -150.0f); break;
    case 124: mu_obj_set_f32(o, MU_OBJF_RANGE, -100.0f); break;
    case 161: case 162: case 163: case 164: case 165: case 166: case 167: case 169: case 171: case 172:
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2); break;
    case 168:
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
        mu_obj_set_f32(o, MU_OBJF_RANGE, -50.0f);
        break;
    default: break;
    }
    if (t >= 34 && t <= 47) {   /* z - 0.0f, kept (quiets a signalling NaN as the client's subss does) */
        volatile float zero = 0.0f;
        mu_obj_set_f32(o, MU_OBJF_POSITION + 8, mu_obj_f32(o, MU_OBJF_POSITION + 8) - zero);
    }
    return 1;
}
static const char *const bone_names[8] = {"E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009"};
const char *mu_kardamahal_bone_name(int32_t k) { return k >= 0 && k < 8 ? bone_names[k] : 0; }
int mu_kardamahal_move(uint8_t *o, int32_t index, const mu_obj_move_inputs *in, mu_obj_log *log)
{
    if (in->world != 143 || !o) return 0;
    const int32_t t = mu_obj_i32(o, MU_OBJF_TYPE);
    switch (t) {
    case 113: {
        const float base = 0.4f;
        float s = (float)(in->rand_fn(in->context) % 4 + 3) * 0.1f * base;
        s = s + base;
        wb_light(log, index, o, s * 1.0f, s * 0.2f, s * 0.1f, 3);
        return 1;
    }
    case 115: {
        if (!in->has_model) return 1;
        const float base = 0.4f;
        float s = (float)(in->rand_fn(in->context) % 4 + 3) * 0.1f * (1.0f - base);
        s = s + base;
        mu_obj_event *e = wb_event(log, MU_KARDAMAHAL_BONE_LIGHTS, index);
        wb_float(e, s * 1.0f); wb_float(e, s * 0.2f); wb_float(e, s * 0.1f); wb_arg(e, 4);
        return 1;
    }
    case 126: case 127: case 128: case 129: case 130: {
        const float base = 0.4f;
        float s = (float)(in->rand_fn(in->context) % 4 + 3) * 0.1f * base;
        s = s + base;
        static const float rgb[5][3] = {{0.74f, 0.17f, 0.62f}, {1.2f, 0.84f, 0.53f}, {1.0f, 0.2f, 0.1f},
                                        {0.1f, 0.41f, 0.8f}, {0.12f, 0.58f, 0.32f}};
        const float *k = rgb[t - 126];
        if (t == 128) wb_light(log, index, o, s, s * k[1], s * k[2], 2);
        else wb_light(log, index, o, s * k[0], s * k[1], s * k[2], 2);
        return 1;
    }
    case 133: wb_sound(log, index, 0x5a6, 0, 0); return 1;
    case 146: case 149:
        if (mu_obj_u16(o, MU_OBJF_ACTION) == 2) wb_sound(log, index, 0x5a9, 0, 0);
        return 1;
    case 150: case 151: case 152:
        wb_sound(log, index, in->rand_fn(in->context) % 2 == 0 ? 0x5a7 : 0x5a8, 0, 0);
        return 1;
    case 167: wb_sound(log, index, 0x5a4, 0, 0); return 1;
    case 169: wb_sound(log, index, 0x5a5, 0, 0); return 1;
    default: return 0;
    }
}
int mu_kardamahal_visual(const uint8_t *o, int32_t i, int has_model, mu_obj_rand_fn random, void *ctx,
                         mu_obj_log *log)
{
    if (!o || !has_model) return 0;
    if (mu_obj_i32(o, MU_OBJF_TYPE) == 161 && random(ctx) % 80 == 1) {
        float p[3], a[3], l[3];
        wb_get(o, MU_OBJF_POSITION, p); wb_get(o, MU_OBJF_ANGLE, a); wb_get(o, MU_OBJF_LIGHT, l);
        mu_obj_event *e = wb_event(log, MU_R2_EFFECT, i);
        wb_arg(e, 0x195); wb_vec(e, p); wb_vec(e, a); wb_vec(e, l); wb_arg(e, 0); wb_arg(e, 1);
        wb_arg(e, (uint16_t)wb_int(mu_obj_f32(o, MU_OBJF_SCALE)));
    }
    return 1;
}
