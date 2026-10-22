/* Display selectors 16bc789/cd0dfe, socket 10a9fdf, harmony cd241f. */
#include "item_display.h"
#include <limits.h>
#include <math.h>
#include <string.h>
static int valid(int code) {
    return code >= 0 && code <= 0x2c00;
}
static int contains(int x, const int *a, size_t n) {
    for (size_t i = 0; i < n; i++)
        if (a[i] == x)
            return 1;
    return 0;
}
static int truncate_i32(double value) {
    if (!isfinite(value) || value < INT32_MIN || value >= 2147483648.0)
        return INT32_MIN;
    return (int32_t)value;
}
int mu_social_normalized_slot(uint8_t slot) {
    return slot >= 0xec && slot <= 0xee ? slot - 0xe0 : slot;
}
int mu_social_ordinary_display(int code, int a, unsigned id, int value, int context,
                               mu_social_display_value *out) {
    static const int text[] = {0x58,  0x59,  0x6a1, 0x5a,  0x5b,  0x57,  0x5c,   0x276,  0x278, 0x279,
                               0x2e7, 0x2e8, 0x2ea, 0x43f, 0x440, 0x3bf, 0x1337, 0x1943, 0x1944};
    static const int ancient[] = {45, 47, 48, 49, 46, 56};
    memset(out, 0, sizeof *out);
    id &= 0xffff;
    if (id >= sizeof text / sizeof *text)
        return 0;
    out->text = text[id];
    out->integer = value;
    out->kind = 1;
    if (id == 6 && code >= 0x1a0e && code <= 0x1a12)
        out->suppressed = 1;
    if (id == 5 && (uint8_t)context && valid(code) && contains(a, ancient, 6))
        out->text = 0x1a6c;
    if (id == 12)
        out->kind = 0;
    if (id == 17 || id == 18) {
        float v = (float)value;
        v = v / 10.0f;
        out->real = (double)v;
        out->kind = 2;
    }
    return 1;
}
static int label(int code, int a, int b, int mode) {
    static const int kinds_b[] = {12, 13, 30, 78, 84, 89, 90, 114, 115};
    static const int kinds_a[] = {47, 48, 49, 56};
    if (valid(code) && contains(b, kinds_b, 9))
        return 0xa3;
    if (valid(code) && b == 14)
        return 0x478;
    if (valid(code) && mode == 2 && contains(a, kinds_a, 4))
        return 0x1469;
    return 0xa2;
}
int mu_social_excellent_display(int code, int a, int b, int category, int mode, int id, double value,
                                int hero_known, int hero_level, int record_level,
                                mu_social_display_value *out) {
    memset(out, 0, sizeof *out);
    if (mode < 0 || mode > 3)
        return 0;
    out->kind = mode == 0 ? 1 : mode == 1 ? 3 : mode == 2 ? 4 : 0;
    if (mode == 0 || mode == 1)
        out->integer = truncate_i32(value);
    if (mode == 1 || mode == 2)
        out->label = label(code, a, b, mode);
    if (mode == 2) {
        if (!hero_known || !hero_level)
            return 0;
        double v = floor((value / ((double)hero_level / 20.0) + 0.05) * 10.0) / 10.0;
        if (id == 10 && category == 2) {
            float base = (float)(uint16_t)record_level;
            base = base / 100.0f;
            v = floor(((double)base + 0.05) * 10.0) / 10.0;
            out->label = 0x1469;
        }
        out->real = (double)(float)v;
    }
#ifdef MU_SOCIAL2_MUTATION_DISPLAY_LABEL
    out->label = 0xa2;
#endif
    return 1;
}
int mu_social_socket_display(int type, float input, int hp_known, int max_hp, int mp_known, int max_mp,
                             mu_social_display_value *out) {
    memset(out, 0, sizeof *out);
    if (type < 1 || type > 5)
        return 0;
    float value = input;
    if (type == 3)
        value = value / 10.0f;
    if (type == 4 || type == 5) {
        if ((type == 4 && !hp_known) || (type == 5 && !mp_known))
            return 0;
        value = (float)(uint16_t)(type == 4 ? max_hp : max_mp) / input;
    }
    out->real = (double)value;
    out->integer = truncate_i32((double)value);
    out->kind = type == 3 ? 2 : 1;
#ifdef MU_SOCIAL2_MUTATION_SOCKET_NARROW
    if (type == 4)
        out->integer = truncate_i32((double)(float)max_hp / input);
#endif
    return 1;
}
int mu_social_harmony_visible(const mu_social_item_wire *w, const mu_social_item_context *c) {
    mu_social_item_decoded d;
    mu_social_item_convert(w, c, &d);
    if (!(uint16_t)d.harmony_kind || (valid(w->code) && c->grade == 2))
        return 0;
    if (valid(w->code) && (d.ancient & 0x33) && c->kind_b == 0x36)
        return 0;
    if (d.period)
        return 0;
    if (c->normalized_slot < 15 && !(valid(w->code) && c->grade == 4) && !c->slot_flags[0] &&
        !c->slot_flags[1] && !c->slot_flags[2] && !c->slot_flags[3])
        return 0;
    static const int excluded[] = {8, 12, 19, 20, 25, 26, 28, 34};
    return c->grade != 5 && !contains(c->kind_a, excluded, 8) && c->kind_b != 0x4c && c->kind_b != 0x6a;
}
