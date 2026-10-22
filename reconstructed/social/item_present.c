#include "item_present.h"
#include <limits.h>
#include <math.h>
#include <string.h>
#include <stdio.h>
static int i32(double v) {
    return !isfinite(v) || v < INT32_MIN || v >= 2147483648.0 ? INT32_MIN : (int32_t)v;
}
static int formula(const mu_social_present_env *e, int family, int index, const int32_t *args, size_t n,
                   double *v) {
    return e && e->formula && e->formula(e->context, family, index, args, n, v);
}
void mu_social_guardian_construct(int base, const uint8_t selectors[5], int enabled,
                                  mu_social_guardian_lookup lookup, void *user,
                                  mu_social_guardian_entry ordinary[4], int *n,
                                  mu_social_guardian_entry bonus[2], int *nb) {
    *n = *nb = 0;
    if (!enabled || !lookup)
        return;
    int32_t values[6], unused[6];
    for (int i = 0; i < 4; i++) {
        int key = selectors[i];
#ifdef MU_SOCIAL2_MUTATION_GUARD_SELECTOR
        if (key == 255)
            continue;
#endif
        if (!lookup(user, 0, key, (uint16_t)base, values))
            continue;
        ordinary[*n] =
            (mu_social_guardian_entry){values[0], values[1], values[2], key, lookup(user, 1, key, 0, unused)};
        (*n)++;
    }
    if (lookup(user, 2, selectors[4], (uint16_t)base, values))
        for (int i = 0; i < 2; i++) {
            bonus[*nb] = (mu_social_guardian_entry){values[3 * i], values[3 * i + 1], 0, values[3 * i],
                                                    lookup(user, 3, values[3 * i], 0, unused)};
            (*nb)++;
        }
}
int mu_social_guardian_present(int bonus, int id, int index, int aux, int L, const mu_social_present_env *e,
                               mu_social_present_args *out) {
    memset(out, 0, sizeof *out);
    int32_t level = (L >> 3) & 15;
    if ((!bonus && id == 1000) || (!bonus && id == 1001) || (bonus && id == -1)) {
        out->mode = 2;
        out->count = id == 1001 ? 2 : 1;
        out->global_text[0] = bonus ? 0x15a7 : 0x15a6;
        if (id == 1001)
            out->global_text[1] = 0x1654;
        return 1;
    }
    if (!bonus && (id < 0 || id > 4))
        return 0;
    double value;
    if (!formula(e, 8, index, &level, 1, &value))
        return -1;
    out->mode = 1;
    out->count = 1;
    out->integer[0] = i32(value);
    if (!bonus && (id == 2 || id == 3)) {
        out->count = 2;
        out->integer[0] = aux;
#ifdef MU_SOCIAL2_MUTATION_GUARD_FLOAT
        value = (double)i32(value);
#endif
        out->kind[1] = 1;
        out->real[1] = (double)(float)value;
    }
    return 1;
}
int mu_social_artifact_construct(const mu_social_artifact_option *row, int selector, int raw, int level,
                                 const mu_social_present_env *e, mu_social_artifact_entry *out) {
    memset(out, 0, sizeof *out);
    if (!row)
        return 0;
    if (!row->divisor)
        return -1;
    double value = raw;
    if (level > 0) {
        int32_t args[4] = {raw, level, raw, level};
#ifdef MU_SOCIAL2_MUTATION_ARTIFACT_ARGS
        args[2] = args[3] = 0;
#endif
        if (!formula(e, 11, row->formula_index, args, 4, &value))
            return -1;
    }
    out->selector = selector;
    out->text_id = row->text_id;
    out->display_value = i32(value);
    out->raw_value = raw;
    out->threshold_flag = raw >= row->threshold;
    for (int i = 0; i < 10; i++)
        if (row->pairs[i][0] == raw) {
            out->position = i + 1;
            break;
        }
    if (!row->divisor)
        return -1;
    out->position_percent = (100 * out->position) / row->divisor;
    return 1;
}
int mu_social_artifact_present(const mu_social_artifact_entry *entry, int present, int format,
                               mu_social_present_args *out) {
    memset(out, 0, sizeof *out);
    if (!present)
        return 0;
    out->mode = 1;
    out->count = format == 0 ? 1 : 2;
    out->kind[0] = 2;
    out->integer[0] = entry->text_id;
    out->integer[1] = entry->display_value;
    if (format < 0 || format > 2)
        out->count = 0;
    out->global_text[0] = entry->position ? 0x19f8 : 0;
    out->global_text[1] = entry->position;
#ifdef MU_SOCIAL2_MUTATION_ARTIFACT_WRAP
    out->global_text[0] = 0;
#endif
    return 1;
}
int mu_social_earring_present(int id, int format, int value, int present, int level, int other,
                              int other_level, const mu_social_present_env *e, mu_social_present_args *out) {
    memset(out, 0, sizeof *out);
    id = (uint8_t)id;
    out->mode = 1;
    out->kind[0] = 2;
    out->integer[0] = id;
    out->count = 1;
    if (!present)
        return 1;
    int result = value;
    if (id >= 28 && id <= 31) {
        int32_t a = level;
        double v;
        if (!formula(e, 9, value, &a, 1, &v))
            return -1;
        result = i32(v);
        if (other) {
            a = other_level;
            if (!formula(e, 9, value, &a, 1, &v))
                return -1;
#ifdef MU_SOCIAL2_MUTATION_EARRING_TRUNC
            result = i32((double)result + v + 0.75);
#else
            result = (int32_t)((uint32_t)result + (uint32_t)i32(v));
#endif
        }
    }
    out->count = 2;
    out->integer[1] = result;
    out->global_text[0] = format == 2;
    return 1;
}
int mu_social_pentagram_present(int required, const int32_t rank[4], const mu_social_present_env *e,
                                mu_social_present_args *out) {
    memset(out, 0, sizeof *out);
    int32_t a[2] = {(uint16_t)required, rank[1]};
    double value;
    if (!formula(e, 1, 7 + rank[2], a, 2, &value))
        return -1;
    out->mode = 1;
    out->count = 3;
    out->global_text[0] = 0x4ae + rank[2];
    out->kind[0] = 3;
    out->integer[0] = (int32_t)(0xe98u + (uint32_t)rank[0]);
    out->integer[1] = i32(value);
    out->integer[2] = rank[1];
    return 1;
}
int mu_social_errtel_plan(int count, const uint8_t slots[5], int grade, mu_social_errtel_line out[5]) {
    if ((uint8_t)count < 1 || (uint8_t)count > 5)
        return 0;
    if ((uint8_t)grade)
        return -1;
    int n = 0;
    for (int i = 0; i < 5; i++) {
        int32_t keys[3];
        if (!mu_social_errtel_request(slots[i], i, keys))
            continue;
        out[n] = (mu_social_errtel_line){keys[0], n + 1, keys[2], keys[1]};
        n++;
    }
    return n;
}
int mu_social_errtel_request(uint8_t byte, int physical, int32_t keys[3]) {
    keys[0] = physical + 1;
#ifdef MU_SOCIAL2_MUTATION_ERRTEL_POSITION
    keys[0] = 1;
#endif
    keys[1] = byte & 15;
    keys[2] = byte >> 4;
    return byte != 255;
}
int mu_social_errtel_present(const int32_t values[11], int level, mu_social_present_args *out) {
    memset(out, 0, sizeof *out);
    if ((unsigned)level >= 11)
        return 0;
    out->mode = 1;
    out->count = 1;
    out->integer[0] = values[level];
    return 1;
}
int mu_social_advanced_present(int format, int value, mu_social_present_args *out) {
    memset(out, 0, sizeof *out);
    if (format != 1 && format != 2)
        return 0;
    out->mode = 1;
    out->count = 2;
    out->kind[0] = 2;
    out->integer[1] = value;
    out->global_text[0] = format == 2;
    return 1;
}
int mu_social_advanced_threshold(const int32_t thresholds[4], int value) {
    for (int i = 0; i < 4; i++)
        if (thresholds[i]
#ifdef MU_SOCIAL2_MUTATION_ADVANCED_THRESHOLD
            >
#else
            >=
#endif
            value)
            return i;
    return 0;
}

size_t mu_social_present_literal(char *out, size_t cap, const char *name, int value, int prefix_only,
                                 int percents) {
    if (!cap)
        return 0;
    int n = prefix_only ? snprintf(out, cap, "%s +", name ? name : "")
                        : snprintf(out, cap, "%s +%d%s", name ? name : "", value,
                                   percents == 2   ? "%%"
                                   : percents == 1 ? "%"
                                                   : "");
    return n < 0 ? 0 : (size_t)n;
}
