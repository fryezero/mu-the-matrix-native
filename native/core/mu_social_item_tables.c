/* Original option-table schemas/accessor semantics; no game rows compiled in. */
#include "mu_social_item_tables.h"
#include "../../reconstructed/items/item_sets.h"
#include "mu_lang.h"
#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct option_row {
    int kind;
    int32_t v[40];
    int fields;
    char *text;
} option_row;
struct mu_social_item_tables {
    mu_lang *lang;
    mu_data_table excellent[2], socket, harmony, formula, set_type, set_option;
    const mu_data_table *items;
    mu_gi_sets *sets;
    option_row *rows;
    size_t count;
    uint32_t available;
};
enum { GUARD_NAME = 1, GUARD_VALUE, GUARD_BONUS_NAME, GUARD_BONUS, ADVANCED, ARTIFACT_NAME, ARTIFACT };
enum { EARRING_PAIR = 9 };
static uint32_t u32(const uint8_t *p) {
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}
static int32_t i32(const uint8_t *p) {
    return (int32_t)u32(p);
}
static int okay(const mu_data_table *t) {
    return t->bytes && t->result.status == MU_DATA_OK;
}
static void load(mu_data_table *t, const char *root, const char *name) {
    if (!root)
        return;
    char path[4096];
    snprintf(path, sizeof path, "%s/Data/Local/%s", root, name);
    if (mu_data_load(path, NULL, t) != 0 || !okay(t))
        mu_data_free(t);
}
static int hex(int c) {
    return c >= '0' && c <= '9'   ? c - '0'
           : c >= 'a' && c <= 'f' ? c - 'a' + 10
           : c >= 'A' && c <= 'F' ? c - 'A' + 10
                                  : -1;
}
static char *unescape(const char *s) {
    size_t n = strlen(s);
    char *out = malloc(n + 1);
    if (!out)
        return NULL;
    size_t k = 0;
    for (size_t i = 0; i < n; i++) {
        unsigned char c = (unsigned char)s[i];
        if (c == '\\') {
            if (++i == n) {
                free(out);
                return NULL;
            }
            c = (unsigned char)s[i];
            if (c == 'n')
                c = '\n';
            else if (c == 'r')
                c = '\r';
            else if (c == 't')
                c = '\t';
            else if (c == 'x' && i + 2 < n && hex(s[i + 1]) >= 0 && hex(s[i + 2]) >= 0) {
                c = (unsigned char)((hex(s[i + 1]) << 4) | hex(s[i + 2]));
                i += 2;
            } else if (c != '\\') {
                free(out);
                return NULL;
            }
        }
        if (!c) {
            free(out);
            return NULL;
        }
        out[k++] = (char)c;
    }
    out[k] = 0;
    return out;
}
static const struct {
    const char *name;
    int fields;
} schemas[] = {
    {"guardian_name", 1},     {"guardian_value", 6}, {"guardian_bonus_name", 1}, {"guardian_bonus", 9},
    {"advanced", 7},          {"artifact_name", 2},  {"artifact", 27},           {"earring_primary", 3},
    {"earring_pair", 8},      {"earring_value", 5},  {"earring_name", 2},        {"pentagram", 9},
    {"pentagram_option", 16}, {"jewel", 28},         {"ertel_set", 14},          {"ertel_text", 2}};
static int kind_for(const char *name) {
    for (size_t i = 0; i < sizeof schemas / sizeof *schemas; i++)
        if (!strcmp(name, schemas[i].name))
            return (int)i + 1;
    return 0;
}
int mu_social_item_table_available(const mu_social_item_tables *t, const char *family) {
    int kind = family ? kind_for(family) : 0;
    return t && kind && !!(t->available & (1u << (unsigned)kind));
}
static void load_lang(mu_social_item_tables *t, const char *dir) {
    if (!dir)
        return;
    char path[4096];
    snprintf(path, sizeof path, "%s/social-options.tsv", dir);
    FILE *f = fopen(path, "rb");
    if (!f)
        return;
    char line[8192];
    while (fgets(line, sizeof line, f)) {
        size_t n = strlen(line);
        if (!n)
            continue;
        if (line[0] == '#') {
            char name[64], tail;
            if (sscanf(line, "# available %63s %c", name, &tail) == 1) {
                int kind = kind_for(name);
                if (kind)
                    t->available |= 1u << (unsigned)kind;
            }
            continue;
        }
        if (line[n - 1] != '\n' && !feof(f)) {
            int c;
            while ((c = fgetc(f)) != EOF && c != '\n') {
            }
            continue;
        }
        while (n && (line[n - 1] == '\n' || line[n - 1] == '\r'))
            line[--n] = 0;
        char *p = strchr(line, '\t');
        if (!p)
            continue;
        *p++ = 0;
        int kind = 0, fields = 0;
        for (size_t i = 0; i < sizeof schemas / sizeof *schemas; i++)
            if (!strcmp(line, schemas[i].name)) {
                kind = (int)i + 1;
                fields = schemas[i].fields;
                break;
            }
        if (!kind)
            continue;
        option_row row = {0};
        row.kind = kind;
        row.fields = fields;
        int good = 1;
        for (int i = 0; i < fields; i++) {
            char *tab = strchr(p, '\t');
            if (!tab) {
                good = 0;
                break;
            }
            *tab = 0;
            char *end;
            errno = 0;
            long v = strtol(p, &end, 10);
            if (errno || end == p || *end || v < INT32_MIN || v > INT32_MAX) {
                good = 0;
                break;
            }
            row.v[i] = (int32_t)v;
            p = tab + 1;
        }
        if (!good || strchr(p, '\t'))
            continue;
        row.text = unescape(p);
        if (!row.text)
            continue;
        option_row *rows = realloc(t->rows, (t->count + 1) * sizeof *rows);
        if (!rows) {
            free(row.text);
            break;
        }
        t->rows = rows;
        t->rows[t->count++] = row;
        t->available |= 1u << (unsigned)kind;
    }
    fclose(f);
}
static const option_row *find(const mu_social_item_tables *t, int kind, int key, int second) {
    if (t)
        for (size_t i = 0; i < t->count; i++) {
            const option_row *r = t->rows + i;
            if (r->kind == kind && r->v[0] == key && (second == INT_MIN || r->v[1] == second))
                return r;
        }
    return NULL;
}
static int has_record(void *context, int32_t code) {
    const mu_social_item_tables *t = context;
    mu_item it;
    return t->items && code >= 0 && mu_item_find(t->items, (uint32_t)code, &it) == 0;
}
static int legendary(void *context, int32_t type, int32_t codes[4]) {
    const mu_social_item_tables *t = context;
    return mu_lang_legendary(t->lang, type, codes);
}
static void build_sets(mu_social_item_tables *t) {
    if (!okay(&t->set_type) || !okay(&t->set_option))
        return;
    mu_gi_set_inputs in = {0};
    in.context = t;
    in.has_record = has_record;
    in.legendary = legendary;
    in.set_type = t->set_type.bytes + t->set_type.result.records_offset;
    in.set_option = t->set_option.bytes + t->set_option.result.records_offset;
    const mu_lang_cash_set *sets;
    const mu_lang_cash_item *items;
    in.cash_set_count = mu_lang_cash_sets(t->lang, &sets);
    in.cash_item_count = mu_lang_cash_items(t->lang, &items);
    const char **names = calloc(in.cash_set_count ? in.cash_set_count : 1, sizeof *names);
    const char **names2 = calloc(in.cash_set_count ? in.cash_set_count : 1, sizeof *names2);
    int32_t *triples = calloc(in.cash_item_count ? in.cash_item_count * 3 : 1, sizeof *triples);
    if (names && names2 && triples) {
        for (size_t i = 0; i < in.cash_set_count; i++) {
            names[i] = sets[i].name;
            names2[i] = sets[i].name2;
        }
        for (size_t i = 0; i < in.cash_item_count; i++) {
            triples[3 * i] = items[i].group;
            triples[3 * i + 1] = items[i].index;
            triples[3 * i + 2] = items[i].set;
        }
        in.cash_names = names;
        in.cash_names2 = names2;
        in.cash_items = triples;
        t->sets = mu_gi_sets_build(&in);
    }
    free(names);
    free(names2);
    free(triples);
}
mu_social_item_tables *mu_social_item_tables_load(const char *root, const char *lang,
                                                  const mu_data_table *items) {
    mu_social_item_tables *t = calloc(1, sizeof *t);
    if (!t)
        return NULL;
    t->items = items;
    t->lang = mu_lang_load(lang ? lang : getenv("MU_LANG_DIR"));
    load(&t->excellent[0], root, "excellentcommonoption.bmd");
    load(&t->excellent[1], root, "excellentwingoption.bmd");
    load(&t->socket, root, "socketitem.bmd");
    load(&t->harmony, root, "jewelofharmonyoption.bmd");
    load(&t->formula, root, "formuladata.bmd");
    load(&t->set_type, root, "itemsettype.bmd");
    load(&t->set_option, root, "itemsetoption.bmd");
    load_lang(t, lang);
    build_sets(t);
    return t;
}
void mu_social_item_tables_free(mu_social_item_tables *t) {
    if (!t)
        return;
    for (size_t i = 0; i < t->count; i++)
        free(t->rows[i].text);
    free(t->rows);
    mu_gi_sets_free(t->sets);
    for (int i = 0; i < 2; i++)
        mu_data_free(t->excellent + i);
    mu_data_free(&t->socket);
    mu_data_free(&t->harmony);
    mu_data_free(&t->formula);
    mu_data_free(&t->set_type);
    mu_data_free(&t->set_option);
    mu_lang_free(t->lang);
    free(t);
}
int mu_social_excellent_available(const mu_social_item_tables *t, int family) {
    return t && family >= 1 && family <= 2 && okay(t->excellent + family - 1);
}
int mu_social_excellent_get(const mu_social_item_tables *t, int family, int category, int id,
                            mu_social_excellent_row *out) {
    if (!t || family < 1 || family > 2 || category < 0 || category > 255 || id < 0 || id > 255)
        return 0;
    const mu_data_table *a = t->excellent + family - 1;
    if (!okay(a))
        return 0;
    const uint8_t *row = NULL;
    for (uint32_t i = 0; i < a->result.records; i++) {
        const uint8_t *r = a->bytes + a->result.records_offset + (size_t)i * 120;
        if (r[0] == category && r[1] == id) {
            row = r;
            break;
        } /* cd51fe uses unique-key insert. */
    }
    if (!row)
        return 0;
    memset(out, 0, sizeof *out);
    memcpy(out->text, row + 2, 100);
    out->value_type = row[0x66];
    out->value = i32(row + 0x68);
    out->format = i32(row + 0x6c);
    memcpy(out->equipment, row + 0x70, 7);
    return 1;
}
int mu_social_socket_get(const mu_social_item_tables *t, int group, int index, mu_social_socket_row *out) {
    if (!t || !okay(&t->socket) || group < 0 || group > 2 || index < 0 || index >= 50)
        return 0;
    const uint8_t *r = t->socket.bytes + ((size_t)group * 50 + (size_t)index) * 168;
    memset(out, 0, sizeof *out);
    out->index = i32(r);
    out->element = i32(r + 4);
    out->option = i32(r + 8);
    memcpy(out->name, r + 12, 64);
    out->value_type = (int8_t)r[0x4c];
    for (int i = 0; i < 20; i++)
        out->values[i] = i32(r + 0x50 + 4 * i);
    memcpy(out->requirements, r + 0xa0, 6);
    return 1;
}
int mu_social_harmony_get(const mu_social_item_tables *t, int group, int id, mu_social_harmony_row *out) {
    if (!t || !okay(&t->harmony) || group < 0 || group > 2 || id < 1 || id > 250)
        return 0;
    const uint8_t *r = t->harmony.bytes + ((size_t)group * 250 + (size_t)(id - 1)) * 180;
    memset(out, 0, sizeof *out);
    out->id = i32(r);
    memcpy(out->name, r + 4, 60);
    out->min_level = i32(r + 0x40);
    for (int i = 0; i < 14; i++) {
        out->values[i] = i32(r + 0x44 + 4 * i);
        out->zen[i] = i32(r + 0x7c + 4 * i);
    }
    return 1;
}
int mu_social_guardian_get(const mu_social_item_tables *t, int base, int selector,
                           mu_social_guardian_option *out) {
    const option_row *r = find(t, GUARD_VALUE, selector, base);
    if (!r)
        return 0;
    const option_row *text = find(t, GUARD_NAME, selector, INT_MIN);
    *out = (mu_social_guardian_option){r->v[2], r->v[3], r->v[5], text ? text->text : NULL};
    return 1;
}
int mu_social_guardian_bonus_get(const mu_social_item_tables *t, int base, int selector,
                                 mu_social_guardian_option out[2]) {
    const option_row *r = find(t, GUARD_BONUS, selector, base);
    if (!r)
        return 0;
    for (int i = 0; i < 2; i++) {
        int k = 3 + 3 * i;
        const option_row *text = find(t, GUARD_BONUS_NAME, r->v[k], INT_MIN);
        out[i] = (mu_social_guardian_option){r->v[k], r->v[k + 1], 0, text ? text->text : NULL};
    }
    return 1;
}
int mu_social_artifact_get(const mu_social_item_tables *t, int selector, mu_social_artifact_row *out) {
    const option_row *r = find(t, ARTIFACT, selector, INT_MIN);
    if (!r)
        return 0;
    out->selector = r->v[0];
    out->text_id = r->v[1];
    out->name = r->text;
    for (int i = 0; i < 10; i++)
        for (int j = 0; j < 2; j++)
            out->pairs[i][j] = r->v[2 + 2 * i + j];
    for (int i = 0; i < 5; i++)
        out->tail[i] = r->v[22 + i];
    return 1;
}
const char *mu_social_artifact_text(const mu_social_item_tables *t, int id, int *format) {
    const option_row *r = find(t, ARTIFACT_NAME, id, INT_MIN);
    if (!r)
        return NULL;
    if (format)
        *format = r->v[1];
    return r->text;
}
int mu_social_advanced_get(const mu_social_item_tables *t, int group, int id, mu_social_advanced_row *out) {
    const option_row *r = find(t, ADVANCED, group, id);
    if (!r)
        return 0;
    out->group = group;
    out->id = id;
    out->name = r->text;
    out->format = r->v[6];
    for (int i = 0; i < 4; i++)
        out->values[i] = r->v[2 + i];
    return 1;
}
const char *mu_social_formula_get(const mu_social_item_tables *t, int family, int id) {
    if (!t || !okay(&t->formula))
        return NULL;
    const mu_data_table *a = &t->formula;
    size_t offset = 8;
    uint32_t groups = u32(a->bytes + 4);
    for (uint32_t g = 0; g < groups; g++) {
        if (offset > a->size || a->size - offset < 8)
            return NULL;
        int32_t f = i32(a->bytes + offset);
        uint32_t n = u32(a->bytes + offset + 4);
        offset += 8;
        if (n > (a->size - offset) / 260)
            return NULL;
        if (f == family)
            for (uint32_t i = 0; i < n; i++) {
                const uint8_t *r = a->bytes + offset + (size_t)i * 260;
                if (i32(r) == id && memchr(r + 4, 0, 256))
                    return (const char *)r + 4;
            }
        offset += (size_t)n * 260;
    }
    return NULL;
}
const char *mu_social_ancient_prefix(const mu_social_item_tables *t, int code, uint8_t bits, uint8_t kind_b) {
    return t ? mu_gi_set_prefix(t->sets, code, bits, kind_b) : "";
}
size_t mu_social_item_table_rows(const mu_social_item_tables *t) {
    return t ? t->count : 0;
}

int mu_social_option_find(const mu_social_item_tables *t, const char *kind, const int32_t *keys, size_t nkeys,
                          int32_t values[40], const char **text) {
    if (!t || !kind)
        return 0;
    int k = 0;
    for (size_t i = 0; i < sizeof schemas / sizeof *schemas; i++)
        if (!strcmp(kind, schemas[i].name)) {
            k = (int)i + 1;
            break;
        }
    if (!k)
        return 0;
    for (size_t i = 0; i < t->count; i++) {
        const option_row *r = t->rows + i;
        if (r->kind != k || nkeys > (size_t)r->fields)
            continue;
        size_t j = 0;
        for (; j < nkeys && r->v[j] == keys[j]; j++) {
        }
        if (j != nkeys)
            continue;
        if (values)
            memcpy(values, r->v, sizeof r->v);
        if (text)
            *text = r->text;
        return r->fields;
    }
    return 0;
}
int mu_social_formula_value(const mu_social_item_tables *t, int family, int id,
                            const mu_social_formula_arg *args, size_t n, double *value) {
    if (!t || !okay(&t->formula))
        return 0;
    int status = mu_social_formula_evaluate(mu_social_formula_get(t, family, id), args, n, value);
    return status == MU_SOCIAL_FORMULA_OK || status == MU_SOCIAL_FORMULA_MISSING;
}

int mu_social_earring_pair_get(const mu_social_item_tables *t, int primary, int32_t out[40]) {
    if (!t)
        return 0;
    for (size_t i = 0; i < t->count; i++) {
        const option_row *r = t->rows + i;
        if (r->kind == EARRING_PAIR && (r->v[0] == primary || r->v[1] == primary)) {
            memcpy(out, r->v, sizeof r->v);
            return 1;
        }
    }
    return 0;
}

int mu_social_guardian_lookup_row(void *user, int kind, int key, int base, int32_t out[6]) {
    const mu_social_item_tables *t = user;
    int32_t row[40];
    const char *text;
    const char *table = kind == 0   ? "guardian_value"
                        : kind == 1 ? "guardian_name"
                        : kind == 2 ? "guardian_bonus"
                                    : "guardian_bonus_name";
    int32_t keys[2] = {key, base};
    if (!mu_social_option_find(t, table, keys, (kind == 0 || kind == 2) ? 2u : 1u, row, &text))
        return 0;
    if (kind == 0) {
        out[0] = row[2];
        out[1] = row[3];
        out[2] = row[5];
    }
    if (kind == 2)
        for (int i = 0; i < 6; i++)
            out[i] = row[3 + i];
    return 1;
}

const mu_lang *mu_social_item_tables_lang(const mu_social_item_tables *t) { return t ? t->lang : NULL; }
