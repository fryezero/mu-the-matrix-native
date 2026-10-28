/* Trade item-instance display, assembled from the original option consumers.
 * The surrounding line layout is native policy. No option or language rows are embedded. */
#include "mu_social_item_view.h"
#include "mu_lang.h"
#include "../../reconstructed/social/item_present.h"
#include "../../reconstructed/hud/tooltip_html.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>
typedef struct arg {
    int kind, integer;
    double real;
    const char *text;
} arg;
static arg ai(int v) {
    return (arg){.integer = v};
}
static arg ar(double v) {
    return (arg){.kind = 1, .real = v};
}
static arg as(const char *v) {
    return (arg){.kind = 2, .text = v ? v : ""};
}
/* Validate each single conversion before calling host printf. Source strings
 * never become an unchecked variadic format, and text arguments remain data. */
static int format(char out[256], const char *pattern, const arg *args, size_t n) {
    size_t used = 0, a = 0;
    out[0] = 0;
    if (!pattern)
        return 0;
    for (size_t i = 0; pattern[i]; i++) {
        if (pattern[i] != '%') {
            if (used >= 255)
                return 0;
            out[used++] = pattern[i];
            continue;
        }
        if (pattern[i + 1] == '%') {
            if (used >= 255)
                return 0;
            out[used++] = '%';
            i++;
            continue;
        }
        size_t start = i;
        i++;
        while (pattern[i] && strchr("-+ #0", pattern[i]))
            i++;
        unsigned width = 0, precision = 0;
        while (pattern[i] >= '0' && pattern[i] <= '9') {
            width = width * 10 + (unsigned)(pattern[i++] - '0');
            if (width > 64)
                return 0;
        }
        if (pattern[i] == '.') {
            i++;
            while (pattern[i] >= '0' && pattern[i] <= '9') {
                precision = precision * 10 + (unsigned)(pattern[i++] - '0');
                if (precision > 9)
                    return 0;
            }
        }
        char c = pattern[i], spec[32], value[512];
        if (!c || !strchr("diufs", c) || i - start + 1 >= sizeof spec || a >= n)
            return 0;
        memcpy(spec, pattern + start, i - start + 1);
        spec[i - start + 1] = 0;
        int len;
        if (c == 's' && args[a].kind == 2)
            len = snprintf(value, sizeof value, spec, args[a].text);
        else if (c == 'f' && args[a].kind == 1)
            len = snprintf(value, sizeof value, spec, args[a].real);
        else if ((c == 'd' || c == 'i') && args[a].kind == 0)
            len = snprintf(value, sizeof value, spec, args[a].integer);
        else if (c == 'u' && args[a].kind == 0)
            len = snprintf(value, sizeof value, spec, (unsigned)args[a].integer);
        else
            return 0;
        a++;
        if (len < 0 || (size_t)len >= sizeof value || (size_t)len > 255 - used)
            return 0;
        memcpy(out + used, value, (size_t)len);
        used += (size_t)len;
    }
    out[used] = 0;
    return 1;
}
static const char *gt(const mu_social_item_view *v, int id, const char *fallback) {
    return mu_lang_text_or(v->lang, id, fallback);
}
static void line(mu_social_item_view *v, int color, const char *text) {
    if (!text || !*text)
        return;
    if (v->count >= MU_SOCIAL_OPTION_LINES) {
        v->unresolved++;
        return;
    }
    snprintf(v->text[v->count], sizeof v->text[0], "%s", text);
    v->color[v->count++] = color;
}
static void missing(mu_social_item_view *v, const char *family) {
    char text[256];
    snprintf(text, sizeof text, "%s: details unavailable", family);
    line(v, 10, text);
    v->unresolved++;
}
static void formatted(mu_social_item_view *v, int color, const char *pattern, const arg *args, size_t n,
                      const char *family) {
    char text[256];
    if (format(text, pattern, args, n))
        line(v, color, text);
    else
        missing(v, family);
}
static void number_line(mu_social_item_view *v, int color, const char *name, int value, int percent) {
    char text[256];
    snprintf(text, sizeof text, "%.210s %d%s", name ? name : "", value, percent ? "%" : "");
    line(v, color, text);
}
static int eval(const mu_social_item_tables *t, int family, int index, int a, int b, int count,
                double *value) {
    mu_social_formula_arg args[2] = {{MU_SOCIAL_FORMULA_INTEGER, a, 0}, {MU_SOCIAL_FORMULA_INTEGER, b, 0}};
    return mu_social_formula_value(t, family, index, args, (size_t)count, value) && isfinite(*value);
}
static int present_formula(void *user, int family, int index, const int32_t *values, size_t count,
                           double *out) {
    if (count > 4)
        return 0;
    mu_social_formula_arg args[4];
    for (size_t i = 0; i < count; i++)
        args[i] = (mu_social_formula_arg){MU_SOCIAL_FORMULA_INTEGER, values[i], 0};
    return mu_social_formula_value(user, family, index, args, count, out);
}
static void present_line(mu_social_item_view *v, int color, const char *pattern,
                         const mu_social_present_args *p, const char *family) {
    if (p->mode == 2) {
        for (int i = 0; i < p->count; i++)
            line(v, color, gt(v, p->global_text[i], ""));
        return;
    }
    if (p->mode != 1)
        return;
    arg a[3];
    for (int i = 0; i < p->count; i++)
        a[i] = p->kind[i] == 1   ? ar(p->real[i])
               : p->kind[i] == 3 ? as(gt(v, p->integer[i], ""))
                                 : ai(p->integer[i]);
    formatted(v, color, pattern, a, (size_t)p->count, family);
}
typedef struct view_context {
    const mu_social_item_tables *tables;
    mu_social_item_view *view;
    int unavailable;
} view_context;
static int final_formula(void *user, int family, int index, int a, int b, double *value) {
    view_context *ctx = user;
    return eval(ctx->tables, family, index, a, b, 2, value);
}
static int excellent_row(void *user, int family, int category, int id, int slot) {
    view_context *ctx = user;
    if (slot >= 0 && slot < 9)
        ctx->view->requested_excellent[slot] = id;
    if (family < 1 || family > 2)
        return 0;
    if (!mu_social_excellent_available(ctx->tables, family)) {
        ctx->unavailable = 1;
        return 0;
    }
    mu_social_excellent_row row;
    return mu_social_excellent_get(ctx->tables, family, category, id, &row);
}

static int find(const mu_social_item_tables *t, const char *kind, int a, int b, int c, size_t n,
                int32_t out[40], const char **text) {
    int32_t keys[3] = {a, b, c};
    return mu_social_option_find(t, kind, keys, n, out, text);
}
static void display_line(mu_social_item_view *v, int color, const char *pattern,
                         const mu_social_display_value *d, const char *family) {
    if (d->suppressed)
        return;
    arg args[2];
    size_t n = 0;
    if (d->kind == 3 || d->kind == 4)
        args[n++] = as(gt(v, d->label, ""));
    if (d->kind == 1 || d->kind == 3)
        args[n++] = ai(d->integer);
    if (d->kind == 2 || d->kind == 4)
        args[n++] = ar(d->real);
    formatted(v, color, pattern, args, n, family);
}
static void sockets(const mu_social_item_tables *t, const mu_social_item_hero *h, mu_social_item_view *v) {
    mu_social_item_decoded *d = &v->decoded;
    if (!d->socket_count)
        return;
    line(v, 6, gt(v, 0xa5a, "Socket options"));
    if (d->seed_index[0] == 46) {
        arg a = ai(v->wire.code / 512 == 4 ? 5 : 3);
        formatted(v, 1, gt(v, 0x1336, "Socket attack option %d"), &a, 1, "Socket");
        return;
    }
    for (int i = 0; i < d->socket_count && i < 5; i++) {
        char prefix[64];
        snprintf(prefix, sizeof prefix, "Socket %d", i + 1);
        if (d->seed_index[i] == 255) {
            char text[256];
            snprintf(text, sizeof text, "%s: %s", prefix, gt(v, 0xa5c, "Empty socket"));
            line(v, 10, text);
            continue;
        }
        mu_social_socket_row row;
        int lev = d->seed_level[i];
        if (!mu_social_socket_get(t, 0, d->seed_index[i], &row) || lev < 0 || lev > 20) {
            missing(v, prefix);
            continue;
        }
        int raw = lev ? row.values[lev - 1] : row.value_type;
        mu_social_display_value value;
        if (!mu_social_socket_display((int8_t)row.value_type, (float)raw, h->hp_known, h->max_hp, h->mp_known,
                                      h->max_mp, &value)) {
            missing(v, prefix);
            continue;
        }
        char val[64], text[256];
        if (value.kind == 2)
            snprintf(val, sizeof val, "%3.1f", value.real);
        else
            snprintf(val, sizeof val, "%d%s", value.integer, row.value_type == 2 ? "%" : "");
        snprintf(text, sizeof text, "%s: %.80s %.100s %s", prefix, gt(v, 0xa4f + row.element, ""), row.name,
                 val);
        line(v, 1, text);
    }
    if (d->socket_bonus < 50) {
        mu_social_socket_row row;
        mu_social_display_value value;
        line(v, 6, gt(v, 0xa60, "Socket bonus"));
        if (mu_social_socket_get(t, 1, d->socket_bonus, &row) &&
            mu_social_socket_display((int8_t)row.value_type, (float)row.values[0], h->hp_known, h->max_hp,
                                     h->mp_known, h->max_mp, &value)) {
            char text[256];
            if (value.kind == 2)
                snprintf(text, sizeof text, "%s %3.1f", row.name, value.real);
            else
                snprintf(text, sizeof text, "%s %d%s", row.name, value.integer,
                         row.value_type == 2 ? "%" : "");
            line(v, 1, text);
        } else
            missing(v, "Socket bonus");
    }
}
static void guardian(const mu_social_item_tables *t, mu_social_item_view *v) {
    if (!mu_social_item_table_available(t, "guardian_value") ||
        !mu_social_item_table_available(t, "guardian_name"))
        missing(v, "Guardian options");
    if (!mu_social_item_table_available(t, "guardian_bonus") ||
        !mu_social_item_table_available(t, "guardian_bonus_name"))
        missing(v, "Guardian bonus options");
    const mu_social_item_decoded *d = &v->decoded;
    mu_social_guardian_entry ordinary[4], bonus[2];
    int n, nb;
    uint8_t selectors[5];
    for (int i = 0; i < 5; i++)
        selectors[i] = (uint8_t)d->guardian_keys[i];
    mu_social_guardian_construct(d->guardian_base, selectors, 1, mu_social_guardian_lookup_row, (void *)t,
                                 ordinary, &n, bonus, &nb);
    mu_social_present_env env = {(void *)t, present_formula};
    for (int b = 0; b < 2; b++) {
        if (b && nb)
            line(v, 3, gt(v, 0x1573, "Guardian bonus options"));
        for (int i = 0; i < (b ? nb : n); i++) {
            mu_social_guardian_entry *entry = b ? &bonus[i] : &ordinary[i];
            mu_social_present_args args;
            int ret = mu_social_guardian_present(b, entry->id, entry->index, entry->auxiliary,
                                                 v->wire.level_word, &env, &args);
            if (ret < 0) {
                missing(v, "Guardian option");
                continue;
            }
            int32_t row[40];
            const char *text = NULL;
            find(t, b ? "guardian_bonus_name" : "guardian_name", entry->name_key, 0, 0, 1, row, &text);
            if (ret)
                present_line(v, b ? 12 : 1, text ? text : "", &args, "Guardian option");
        }
    }
    line(v, 1, gt(v, 0xc34, "Guardian options"));
    if (v->wire.durability <= 50)
        line(v, 2, gt(v, 0x15a4, "Guardian durability is low"));
}
static void artifacts(const mu_social_item_tables *t, mu_social_item_view *v) {
    mu_social_present_env env = {(void *)t, present_formula};
    for (int i = 0; i < v->decoded.artifact_count; i++) {
        const int *request = v->decoded.artifact[i];
        mu_social_artifact_row row;
        if (!mu_social_artifact_get(t, request[0], &row)) {
            missing(v, "Artifact option");
            continue;
        }
        mu_social_artifact_option option = {.selector = row.selector,
                                            .text_id = row.text_id,
                                            .formula_index = row.tail[1],
                                            .threshold = row.tail[3],
                                            .divisor = row.tail[4]};
        memcpy(option.pairs, row.pairs, sizeof option.pairs);
        mu_social_artifact_entry entry;
        if (mu_social_artifact_construct(&option, request[0], request[1], request[2], &env, &entry) < 1) {
            missing(v, "Artifact option");
            continue;
        }
        int mode = 0;
        const char *name = mu_social_artifact_text(t, entry.text_id, &mode);
        mu_social_present_args args;
        if (!mu_social_artifact_present(&entry, name != NULL, mode, &args)) {
            missing(v, "Artifact option");
            continue;
        }
        char text[256] = "";
        if (args.count == 1)
            snprintf(text, sizeof text, "%s", name);
        else if (args.count == 2)
            mu_social_present_literal(text, sizeof text, name, args.integer[1], 0, mode == 2);
        int color = entry.threshold_flag ? 15 : 1;
        if (args.global_text[0]) {
            arg a[2] = {ai(args.global_text[1]), as(text)};
            formatted(v, color, gt(v, args.global_text[0], "Rank %d %s"), a, 2, "Artifact rank");
        } else
            line(v, color, text);
    }
}
static const char *element(const mu_social_item_view *v, int n) {
    return n >= 1 && n <= 5 ? gt(v, 0xe98 + n, "") : "";
}
static void elemental(const mu_social_item_tables *t, const mu_hud_tip_tables *base, const mu_item *item,
                      mu_social_item_view *v) {

    const mu_social_item_decoded *d = &v->decoded;
    int32_t row[40];
    const char *text;
    if (d->element > 5)
        missing(v, "Element");
    else if (d->element) {
        char label[256];
        snprintf(label, sizeof label, "Element: %s", element(v, d->element));
        line(v, 6, label);
    }
    if (v->context.kind_a == 25) {
        int displayed = 0;
        if (d->socket_count && item->attributes.pentagram_grade)
            for (int i = 3; i >= 0; i--) {
                const int *r = d->rank[i];
                if (r[3] == -1 || r[3] == 255)
                    continue;
                if (r[3] == 254) {
                    char label[64];
                    snprintf(label, sizeof label, "Elemental option slot %d", ++displayed);
                    line(v, 10, label);
                    continue;
                }
                if (r[0] < 1 || r[0] > 5)
                    continue;
                displayed++;
                if (r[2] == 0 || r[2] == 1) {
                    mu_social_present_env env = {(void *)t, present_formula};
                    mu_social_present_args args;
                    if (mu_social_pentagram_present(item->attributes.require_level, r, &env, &args) < 1) {
                        missing(v, "Elemental rank");
                        continue;
                    }
                    const char *pattern = mu_hud_tip_text(base, (uint16_t)args.global_text[0]);
                    if (!pattern) {
                        missing(v, "Elemental rank text");
                        continue;
                    }
                    present_line(v, 1, pattern, &args, "Elemental rank");
                }
            }
        if (find(t, "pentagram", v->wire.code, 0, 0, 1, row, &text)) {
            int ids[7];
            for (int i = 0; i < 7; i++)
                ids[i] = row[2 + i];
            for (int i = 0; i < 7; i++)
                if (ids[i]) {
                    if (!find(t, "pentagram_option", ids[i], 0, 0, 1, row, &text)) {
                        missing(v, "Pentagram option");
                        continue;
                    }
                    if (ids[i] == 28) {
                        int e1 = d->element + 1;
                        if (e1 > 5)
                            e1 -= 5;
                        int e2 = e1 + 1;
                        if (e2 > 5)
                            e2 -= 5;
                        if (e1 < 1 || e1 > 5 || e2 < 1 || e2 > 5) {
                            missing(v, "Pentagram element");
                            continue;
                        }
                        static const int labels[5] = {0x12d5, 0x12d7, 0x12d4, 0x12d6, 0x12d8};
                        arg a[2] = {as(gt(v, labels[e1 > 0 && e1 <= 5 ? e1 - 1 : 0], "")),
                                    as(gt(v, labels[e2 > 0 && e2 <= 5 ? e2 - 1 : 0], ""))};
                        formatted(v, 10, text, a, 2, "Pentagram option");
                    } else
                        formatted(v, 10, text, NULL, 0, "Pentagram option");
                    for (int j = 0; j < 5; j++) {
                        unsigned slot = (uint8_t)row[1 + 3 * j], rank = (uint8_t)row[2 + 3 * j],
                                 level = (uint8_t)row[3 + 3 * j];
                        if (slot == 255)
                            continue;
                        char req[256];
                        if (slot < 5)
                            snprintf(req, sizeof req, "Requires %.100s rank %u level %u (equipment needed)",
                                     gt(v, 0xf7c + (int)slot, "Errtel"), rank, level);
                        else if (slot == 5)
                            snprintf(req, sizeof req, "Requires pentagram level %u%s", level,
                                     d->level >= (int)level ? "" : " (not met)");
                        else
                            continue;
                        line(v, 10, req);
                    }
                }
        } else if (d->socket_count)
            missing(v, "Pentagram options");
        if (item->attributes.pentagram_grade && d->ancient) {
            if (find(t, "ertel_set", d->ancient, 0, 0, 1, row, &text))
                line(v, 10, text);
            else
                missing(v, "Elemental set");
            line(v, 10, "Set activation requires current equipment");
        }
        for (int i = 0; i < 5; i++)
            if (d->socket_raw[i] != 255) {
                char label[192];
                snprintf(label, sizeof label, "%s: embedded options need current equipment",
                         gt(v, 0xf7c + i, "Errtel"));
                line(v, 10, label);
                v->unresolved++;
            }
    } else if (v->context.kind_a == 26 || v->context.kind_b == 0x2c) {
        if (!mu_social_item_table_available(t, "jewel"))
            missing(v, "Errtel options");
        if (d->socket_count < 1 || d->socket_count > 5)
            return;
        if (item->attributes.pentagram_grade) {
            missing(v, "Mastery Errtel options");
            return;
        }
        arg count = ai(d->socket_count);
        formatted(v, 6, gt(v, 0xe57, "%d Rank Errtel"), &count, 1, "Errtel rank");
        uint8_t slots[5];
        for (int i = 0; i < 5; i++)
            slots[i] = (uint8_t)d->socket_raw[i];
        mu_social_errtel_line plan[5];
        int count_lines =
            mu_social_errtel_plan(d->socket_count, slots, item->attributes.pentagram_grade, plan);
        for (int i = 0; i < count_lines; i++) {
            int level = plan[i].level, opt = plan[i].option;
            arg a[2] = {ai(plan[i].ordinal), ai(level)};
            formatted(v, 6, gt(v, 0xe58, "%d Rank Option +%d"), a, 2, "Errtel rank");
            if (level > 10 || !find(t, "jewel", v->wire.code, plan[i].physical, opt, 3, row, &text)) {
                arg fallback = ai(opt);
                formatted(
                    v, 1,
                    gt(v, opt == 15 ? 0x1298 : 0xe5a, opt == 15 ? "Undesignated option" : "Unknown option %d"),
                    &fallback, 1, "Errtel option");
                continue;
            }
            mu_social_present_args args;
            mu_social_errtel_present(row + 6, level, &args);
            present_line(v, 1, text, &args, "Errtel option");
        }
    }
}
static void earring(const mu_social_item_tables *t, mu_social_item_view *v) {
    if (!mu_social_item_table_available(t, "earring_primary") ||
        !mu_social_item_table_available(t, "earring_name") ||
        !mu_social_item_table_available(t, "earring_value"))
        missing(v, "Earring options");
    if (!mu_social_item_table_available(t, "earring_pair"))
        missing(v, "Earring pair options");
    const mu_social_item_finalized *f = &v->finalized;
    int32_t row[40];
    const char *name;
    for (int bonus = 0; bonus < 2; bonus++) {
        int count = bonus ? f->bonus_count : f->special_count;
        if (bonus && count)
            line(v, 6, gt(v, 0x14c9, "Earring set options"));
        for (int i = 0; i < count; i++) {
            const int *o = bonus ? f->bonus[i] : f->special[i];
            int id = (uint8_t)o[0], rank = (uint8_t)o[1], tag = (uint8_t)o[2];
            if (!find(t, "earring_name", id, 0, 0, 1, row, &name)) {
                missing(v, "Earring option");
                continue;
            }
            int format_type = row[1];
            const char *text = name;
            int32_t tagrow[40];
            if (!find(t, "earring_value", tag, 0, 0, 1, tagrow, NULL)) {
                missing(v, "Earring value");
                continue;
            }
            int selected = find(t, "earring_value", tag, rank, 0, 2, row, NULL) != 0;
            mu_social_present_env env = {(void *)t, present_formula};
            mu_social_present_args args;
            if (mu_social_earring_present(id, format_type, selected ? row[3] : 0, selected, v->decoded.level,
                                          0, 0, &env, &args) < 1) {
                missing(v, "Earring value");
                continue;
            }
            char rendered[256];
            mu_social_present_literal(rendered, sizeof rendered, text, args.integer[1], args.count == 1,
                                      format_type == 2 ? 2 : 0);
            line(v, bonus ? 10 : 1, rendered);
        }
        if (bonus && count)
            line(v, 10, "Paired bonus requires equipped matching earrings");
    }
}
int mu_social_item_view_build(const mu_social_item_tables *t, const mu_hud_tip_tables *base,
                              const uint8_t bytes[15], const mu_social_item_hero *h, mu_social_item_view *v) {
    memset(v, 0, sizeof *v);
    v->lang = mu_social_item_tables_lang(t);
    mu_social_item_unpack(bytes, &v->wire);
    mu_item item;
    if (!base || !base->have_items || mu_item_find(&base->items, (uint32_t)v->wire.code, &item))
        return 0;
    const mu_item_attributes *a = &item.attributes;
    mu_social_item_context *c = &v->context;
    c->kind_a = a->kind_a;
    c->kind_b = a->kind_b;
    c->grade = a->type;
    c->skill = a->skill;
    c->base_level = a->level;
    c->normalized_slot = mu_social_normalized_slot(a->slot);
    c->slot_flags[0] = a->can_drop;
    c->slot_flags[1] = a->can_trade;
    c->slot_flags[2] = a->can_personal_store;
    c->slot_flags[3] = a->can_warehouse;
    c->can_trade = a->can_trade;
    c->capability = 1;
    mu_social_item_convert(&v->wire, c, &v->decoded);
    view_context ctx = {.tables = t, .view = v};
    for (int i = 0; i < 9; i++)
        v->requested_excellent[i] = 255;
    mu_social_item_final_env env = {.context = &ctx,
                                    .formula = final_formula,
                                    .excellent_row = excellent_row,
                                    .level_word = v->wire.level_word,
                                    .ancient = v->decoded.ancient,
                                    .enabled = 1,
                                    .class_byte = h->class_byte};
    int32_t row[40];
    const char *text;
    if (c->kind_a == 19 && find(t, "earring_primary", item.index, 0, 0, 1, row, NULL)) {
        int primary = row[1];
        env.special_tag = (uint8_t)row[2];
        env.special_row = 1;
        int found = mu_social_earring_pair_get(t, primary, row);
        if (found && row[0]) {
            env.special_enabled = 1;
            for (int i = 0; i < 3; i++) {
                env.special_bonus[i] = row[2 + i];
                env.special_lows[i] = (uint8_t)row[5 + i];
            }
        }
    }
    for (int i = 0; i < 9; i++)
        v->finalized.slots[i] = 255;
    for (int i = 0; i < 3; i++)
        v->finalized.slots[6 + i] = v->decoded.extra_excellent[i];
    if (c->kind_a == 19)
        for (int i = 0; i < 5; i++)
            v->finalized.slots[i] = v->decoded.special_raw[i];
    mu_social_item_finalize(&v->wire, c, &env, &v->finalized);
    v->excellent_known = !ctx.unavailable;
    c->excellent_resolved = ctx.unavailable ? -1 : v->finalized.excellent;

    mu_social_item_convert(&v->wire, c, &v->decoded);
    mu_hud_item hi = {.code = v->wire.code,
                      .level = v->decoded.level,
                      .excellent = (uint8_t)v->finalized.excellent,
                      .durability = v->wire.durability,
                      .has_record = 1,
                      .record = item};
    snprintf(hi.name, sizeof hi.name, "%s", item.name);
    int hero[4] = {h->strength, h->agility, h->energy, h->level};
    mu_hud_tip tip;
    uint8_t max =
        mu_item_max_durability_at(&item, v->decoded.level, v->finalized.excellent, v->decoded.ancient);
    mu_hud_tip_build_durability(base, &hi, hero, max, &tip);
    const char *prefix = mu_social_ancient_prefix(t, v->wire.code, (uint8_t)v->decoded.ancient, a->kind_b);
    for (int i = 0; i < tip.count; i++) {
        if (!i && prefix && *prefix) {
            char title[256];
            snprintf(title, sizeof title, "%.90s %.150s", prefix, tip.text[i]);
            line(v, tip.color[i], title);
        } else
            line(v, tip.color[i], tip.text[i]);
    }
    if (ctx.unavailable)
        missing(v, "Excellent options");
    if (v->decoded.ancient & 0x33)
        line(v, 10, "Ancient set options require equipped matching pieces");
    if (v->decoded.period)
        line(v, 10, v->decoded.expired ? "Period item: expired" : "Period item");
    if (v->finalized.skill) {
        const mu_lang_skill *skill = mu_lang_skill_get(v->lang, v->finalized.skill);
        char label[256];
        snprintf(label, sizeof label, "Skill: %s", skill ? skill->name : "available");
        line(v, 1, label);
    }
    for (int i = 0; i < v->finalized.count; i++) {
        mu_social_item_option option = v->finalized.options[i];
        mu_social_display_value display;
        if (mu_social_ordinary_display(v->wire.code, c->kind_a, (unsigned)option.id, (uint16_t)option.value,
                                       !!(v->decoded.ancient & 0x33), &display)) {
            text = mu_lang_text(v->lang, display.text);
            if (text)
                display_line(v, 1, text, &display, "Additional option");
            else
                missing(v, "Additional option");
        } else
            missing(v, "Additional option");
    }
    if (v->finalized.unresolved)
        missing(v, "Character-dependent option");
    int excellent_header = 0;
    if (c->kind_a != 19)
        for (int i = 0; i < 9; i++) {
            int id = v->finalized.slots[i];
            if (id == 255)
                continue;
            mu_social_excellent_row row_ex;
            if (!excellent_header++)
                line(v, 6, "Excellent options (preview)");
            if (!mu_social_excellent_get(t, v->finalized.family, v->finalized.category, id, &row_ex)) {
                missing(v, "Excellent option");
                continue;
            }
            double value;
            mu_social_display_value display;
            if (!mu_social_item_excellent_value(v->finalized.category, id, row_ex.value_type, row_ex.value,
                                                v->wire.level_word, c->base_level, h->level, &env, &value) ||
                !mu_social_excellent_display(v->wire.code, c->kind_a, c->kind_b, v->finalized.category,
                                             row_ex.format, id, value, h->known, h->level, c->base_level,
                                             &display)) {
                missing(v, "Excellent option");
                continue;
            }
            display_line(v, 1, row_ex.text, &display, "Excellent option");
        }
    if (mu_social_harmony_visible(&v->wire, c)) {
        int group = v->wire.code < 0        ? 3
                    : v->wire.code < 0xa00  ? 0
                    : v->wire.code < 0xc00  ? 1
                    : v->wire.code < 0x1800 ? 2
                                            : 3;
        if (c->kind_b == 0x4e || c->kind_b == 0x54)
            group = 1;
        mu_social_harmony_row hr;
        int id = v->decoded.harmony_kind, lev = v->decoded.harmony_level;
        if (group > 2 || id > (group ? 248 : 250) || lev < 0 || lev >= 14 ||
            !mu_social_harmony_get(t, group, id, &hr))
            missing(v, "Harmony option");
        else
            number_line(v, v->decoded.level >= lev ? 1 : 10, hr.name, hr.values[lev], group == 2 && id == 7);
    }
    if (v->decoded.advanced_slot >= 0) {
        mu_social_advanced_row row_a;
        if (mu_social_advanced_get(t, v->decoded.saved_group, v->decoded.advanced_option, &row_a)) {
            v->advanced_grade = mu_social_advanced_threshold(row_a.values, v->decoded.advanced_level);
            mu_social_present_args args;
            if (mu_social_advanced_present(row_a.format, v->decoded.advanced_level, &args)) {
                char rendered[256];
                mu_social_present_literal(rendered, sizeof rendered, row_a.name, args.integer[1], 0,
                                          args.global_text[0]);
                line(v, 1, rendered);
            }
        } else
            missing(v, "Advanced harmony option");
    }
    if (c->grade == 2)
        sockets(t, h, v);
    else if (c->kind_a == 20)
        guardian(t, v);
    else if (c->kind_a == 28)
        artifacts(t, v);
    else if (c->kind_a == 25 || c->kind_a == 26 || c->kind_b == 0x2c)
        elemental(t, base, &item, v);
    if (c->kind_a == 19)
        earring(t, v);
    return 1;
}
size_t mu_social_item_view_html(const mu_social_item_view *v, char *out, size_t cap) {
    mu_tooltip_line lines[MU_SOCIAL_OPTION_LINES];
    for (int i = 0; i < v->count; i++)
        lines[i] = (mu_tooltip_line){v->text[i], v->color[i], 0, 0};
    char ansi[32768];
    int bad;
    mu_tooltip_html(ansi, sizeof ansi, lines, v->count, &bad);
    return mu_latin1_to_utf8(out, cap, ansi);
}
