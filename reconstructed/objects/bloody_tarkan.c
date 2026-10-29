/* Bloody Tarkan, world 140 (0x8c), vtable 0x01aa6e74. Create 0x00d9a022, move 0x00d9a0ad, visual 0x00d9ac33;
 * world predicate 0x00d9bd83. */
#include "worlds_p_internal.h"
int mu_bloody_tarkan_create(uint8_t *o, int32_t world)
{
    if (world != 0x8c || !o)
        return 0;
    switch (mu_obj_i32(o, MU_OBJF_TYPE)) {
    case 0x11: case 0x12: case 0x44: case 0x46:
        o[MU_OBJF_AFTER_CHARACTER] = 1;
        break;
    case 0x51: case 0x52: case 0x5f: case 0x64: case 0x65:
        mu_obj_set_i32(o, MU_OBJF_HIDDEN_MESH, -2);
        break;
    default:
        break;
    }
    return 1;
}

int mu_bloody_tarkan_move(uint8_t *o, int32_t i, int32_t world, float time, mu_obj_rand_fn rnd, void *c,
                          mu_obj_log *log)
{
    if (world != 0x8c || !o)
        return 0;
    switch (mu_obj_i32(o, MU_OBJF_TYPE)) {
    case 0x51: {
        const float s = (float)(rnd(c) % 4 + 3) * 0.1f;
        wb_light(log, i, o, s * 0.8f, s * 0.3f, s * 0.04f, 3);
        return 1;
    }
    case 0x13: {
        const float x = (mu_obj_f32(o, MU_OBJF_ANGLE + 8) * 100.0f + time) * 0.002f;
        const float pulse = (float)sin((double)x) * 0.15f + 0.65f;
        mu_obj_set_i32(o, MU_OBJF_BLEND_MESH, 0);
        mu_obj_set_f32(o, MU_OBJF_BLEND_LIGHT, pulse);
        mu_obj_event *e = wb_event(log, MU_WP_CLAMPED_LIGHT, i);
        wb_float(e, mu_obj_f32(o, MU_OBJF_POSITION));
        wb_float(e, mu_obj_f32(o, MU_OBJF_POSITION + 4));
        wb_float(e, pulse); wb_float(e, pulse * 0.6f); wb_float(e, pulse * 0.2f);
        wb_arg(e, 3);
        return 1;
    }
    default:
        return 0;
    }
}

int mu_bloody_tarkan_visual(const uint8_t *o, int present)
{
    (void)o; (void)present;
    return 0;
}

static int32_t cvtt(float v)
{
    return v != v || v < -2147483648.0f || v >= 2147483648.0f ? INT32_MIN : (int32_t)v;
}
void mu_bloody_tarkan_add_light_clamped(float x, float y, const float light[3], int32_t range, float *buffer)
{
    const float rf = (float)range;
    const float xf = x / 100.0f, yf = y / 100.0f;
    const int32_t xi = cvtt(xf), yi = cvtt(yf);
    const int32_t y0 = (int32_t)((uint32_t)yi - (uint32_t)range), y1 = (int32_t)((uint32_t)yi + (uint32_t)range);
    float row = (float)y0;
    for (int32_t yy = y0; yy <= y1; ++yy, row = row + 1.0f) {
        const int32_t x0 = (int32_t)((uint32_t)xi - (uint32_t)range), x1 = (int32_t)((uint32_t)xi + (uint32_t)range);
        float column = (float)x0;
        for (int32_t xx = x0; xx <= x1; ++xx, column = column + 1.0f) {
            const float dx = xf - column, dy = yf - row;
            float d = dx * dx;
            d = d + dy * dy;
            const float lf = (rf - (float)sqrt((double)d)) / rf;
            if (lf > 0.0f) {
                float *p = &buffer[3 * (((yy & 0xff) << 8) + (xx & 0xff))];
                for (int k = 0; k < 3; ++k) {
                    p[k] = light[k] * lf + p[k];
                    if (0.0f > p[k])
                        p[k] = 0.0f;
                    else if (p[k] > 1.0f)
                        p[k] = 1.0f;
                }
            }
            if (xx == INT32_MAX)
                break;
        }
        if (yy == INT32_MAX)
            break;
    }
}
