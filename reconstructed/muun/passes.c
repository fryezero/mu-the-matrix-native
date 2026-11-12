#include "passes.h"
#include <math.h>
#include <string.h>
static float number(const uint8_t *r, int offset)
{
    float f;
    memcpy(&f, r + offset, sizeof f);
    return f;
}
static int32_t integer(const uint8_t *r, int offset)
{
    int32_t i;
    memcpy(&i, r + offset, sizeof i);
    return i;
}
/* 0x0185bdc4(a, 0), SSE binary32 clock arithmetic and CRT cosine. */
static float wave(float a, float time)
{
    float divisor = 6283.1855f / a;
    if (!(divisor >= -2147483648.0f && divisor < 2147483648.0f)) return NAN;
    int32_t period = (int32_t)divisor;
    if (!period || period == -1) return NAN;
    int32_t tick = !(time >= -2147483648.0f && time < 2147483648.0f) ? INT32_MIN : (int32_t)time;
    float y = (float)(tick % period) * 0.001f * a;
    float value = (float)cos((double)y);
    if (3.1415927f > y) value = -value;
    return (value + 1.0f) * 0.5f;
}
void mu_mv_mesh_pass(const uint8_t r[300], const float color[3], float alpha, int32_t blend,
                     float light, int32_t texture, float time, mu_mv_pass *out)
{
    out->mesh = integer(r, 4);
    out->flags = integer(r, 0x124);
    out->blend = blend;
    out->light = light;
    out->alpha = alpha;
    out->texture = texture;
    memcpy(out->color, color, sizeof out->color);
    if (r[0x129]) {
        out->blend = out->mesh;
        out->light = r[0x128] ? wave(-number(r, 0x118), time) *
            (number(r, 0x120) - number(r, 0x11c)) + number(r, 0x11c) : number(r, 0x11c);
    }
    if (r[0x12b]) out->alpha = number(r, 0x114);
    if (r[0x12a]) memcpy(out->color, r + 0x108, sizeof out->color);
}
int32_t mu_mv_command_action(int32_t category)
{
    switch (category) {
    case 50: case 53: return 3;
    case 51: case 52: case 54: case 55: return 4;
    default: return -1;
    }
}

float mu_mv_shadow_alpha(int32_t world, int option, int owner_kind, float owner_alpha, float record_alpha)
{
    if (world == 10 || world == 132 || (world >= 24 && world <= 29) || world == 36 || option) return 0.0f;
    float alpha = owner_kind == 2 ? owner_alpha : record_alpha;
    return world == 7 || (world >= 128 && world <= 130) ? (alpha != 0.0f ? 0.2f : 0.0f) : alpha;
}
