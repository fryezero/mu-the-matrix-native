/* The set-item prefix: the set manager's build (0x009de132, 0x009debe4) and lookup 0x009e0551. See item_sets.h. */
#include "item_sets.h"

#include <stdlib.h>
#include <string.h>

typedef struct set_entry {
    int32_t code;                   /* entry +0 (-1 from the constructor 0x009e7125) */
    uint8_t bits;                   /* entry +0x34 (0 from the constructor) */
} set_entry;

typedef struct item_set {
    uint16_t index;                 /* set +0 */
    char *name, *name2;             /* set +4, +0x1c (std::string) */
    size_t name_len;
    set_entry *entries;             /* entry list (0x009e8302, stride 0x38) */
    size_t nentries, centries;
    set_entry (*pairs)[2];          /* legendary pair list at +0x4c (0x01078226) */
    size_t npairs, cpairs;
} item_set;

struct mu_gi_sets {
    item_set **order;               /* the std::map<std::string, set *> in key order */
    size_t count, cap;
};

static char *copy_cstr(const uint8_t *s, size_t limit, size_t *len)
{
    size_t n = 0;
    while (n < limit && s[n])
        ++n;
    char *out = malloc(n + 1);
    if (out) {
        memcpy(out, s, n);
        out[n] = 0;
    }
    *len = n;
    return out;
}

/* std::less<std::string>: memcmp over the shorter length, then the length */
static int key_compare(const char *a, size_t na, const char *b, size_t nb)
{
    int c = memcmp(a, b, na < nb ? na : nb);
    if (c)
        return c;
    return na < nb ? -1 : na > nb;
}

static void free_set(item_set *s)
{
    if (!s)
        return;
    free(s->name);
    free(s->name2);
    free(s->entries);
    free(s->pairs);
    free(s);
}

/* insert by name unless the name is present (then the new set is dropped) */
static void insert_set(mu_gi_sets *m, item_set *s)
{
    size_t lo = 0, hi = m->count;
    while (lo < hi) {
        size_t mid = (lo + hi) / 2;
        int c = key_compare(m->order[mid]->name, m->order[mid]->name_len, s->name, s->name_len);
        if (c < 0)
            lo = mid + 1;
        else
            hi = mid;
    }
    if (lo < m->count && !key_compare(m->order[lo]->name, m->order[lo]->name_len, s->name, s->name_len)) {
        free_set(s);
        return;
    }
    if (m->count == m->cap) {
        size_t ncap = m->cap ? m->cap * 2 : 64;
        item_set **no = realloc(m->order, ncap * sizeof *no);
        if (!no) {
            free_set(s);
            return;
        }
        m->order = no;
        m->cap = ncap;
    }
    memmove(m->order + lo + 1, m->order + lo, (m->count - lo) * sizeof *m->order);
    m->order[lo] = s;
    ++m->count;
}

static item_set *new_set(uint16_t index, const uint8_t *name, size_t name_limit, const uint8_t *name2,
                         size_t name2_limit)
{
    item_set *s = calloc(1, sizeof *s);
    if (!s)
        return NULL;
    size_t n2;
    s->index = index;
    s->name = copy_cstr(name, name_limit, &s->name_len);
    s->name2 = copy_cstr(name2, name2_limit, &n2);
    if (!s->name || !s->name2) {
        free_set(s);
        return NULL;
    }
    return s;
}

static void push_entry(item_set *s, set_entry e)
{
    if (s->nentries == s->centries) {
        size_t ncap = s->centries ? s->centries * 2 : 8;
        set_entry *ne = realloc(s->entries, ncap * sizeof *ne);
        if (!ne)
            return;
        s->entries = ne;
        s->centries = ncap;
    }
    s->entries[s->nentries++] = e;
}

/* 0x0107717c: the legendary pair list */
static void push_legendary(item_set *s, const int32_t codes[4], set_entry e)
{
    if (!s->npairs) {
        for (int i = 0; i < 2; ++i) {
            set_entry p[2] = {{codes[2 * i], 0}, {codes[2 * i + 1], 0}};
            if (p[0].code == -1 && p[1].code == -1)
                continue;
            if (s->npairs == s->cpairs) {
                size_t ncap = s->cpairs ? s->cpairs * 2 : 2;
                set_entry (*np)[2] = realloc(s->pairs, ncap * sizeof *np);
                if (!np)
                    return;
                s->pairs = np;
                s->cpairs = ncap;
            }
            s->pairs[s->npairs][0] = p[0];
            s->pairs[s->npairs][1] = p[1];
            ++s->npairs;
        }
    }
    for (size_t i = 0; i < s->npairs; ++i)
        for (int j = 0; j < 2; ++j)
            if (s->pairs[i][j].code == e.code)
                s->pairs[i][j] = e;
}

static item_set *find_index(const mu_gi_sets *m, int32_t index)
{
    for (size_t i = 0; i < m->count; ++i)
        if ((int32_t)m->order[i]->index == index)
            return m->order[i];
    return NULL;
}

static int legendary_holds(const mu_gi_set_inputs *in, int32_t type, int32_t code, int32_t codes[4])
{
    if (!in->legendary || !in->legendary(in->context, type, codes))
        return 0;
    for (int k = 0; k < 4; ++k)
        if (codes[k] == code)
            return 1;
    return 0;
}

mu_gi_sets *mu_gi_sets_build(const mu_gi_set_inputs *in)
{
    mu_gi_sets *m = calloc(1, sizeof *m);
    if (!m)
        return NULL;
    /* 0x009de132, part 1: the ItemSetOption sets 1..999 */
    for (int32_t i = 1; i < MU_GI_SET_OPTIONS && in->set_option; ++i) {
        const uint8_t *r = in->set_option + (size_t)i * MU_GI_SET_OPTION_BYTES;
        if (!r[0])
            continue;
        item_set *s = new_set((uint16_t)i, r, MU_GI_SET_OPTION_BYTES, r + 0x40, MU_GI_SET_OPTION_BYTES - 0x40);
        if (s)
            insert_set(m, s);
    }
    /* part 2: the ItemSetType words of every code */
    static const uint8_t bits[4] = {1, 2, 0x10, 0x20};
    for (int32_t code = 0; code < MU_GI_SET_CODES && in->set_type; ++code) {
        const uint8_t *r = in->set_type + (size_t)code * MU_GI_SET_TYPE_BYTES;
        for (int k = 0; k < 4; ++k) {
            uint16_t type = (uint16_t)(r[2 * k] | r[2 * k + 1] << 8);
            if (!type)
                continue;
            if (!in->has_record || !in->has_record(in->context, code))
                continue;                                   /* the client shows a message box and goes on */
            set_entry e = {code, bits[k]};
            item_set *s = find_index(m, type);
            if (!s)
                continue;
            int32_t codes[4];
            if (legendary_holds(in, type, code, codes))
                push_legendary(s, codes, e);
            else
                push_entry(s, e);
        }
    }
    /* 0x009debe4: CashItemSetOption */
    int32_t base = 0;
    for (size_t i = m->count; i < MU_GI_SET_OPTIONS && in->set_option; ++i)
        if (in->set_option[i * MU_GI_SET_OPTION_BYTES])
            base = (int32_t)i;
    base += 1;
    for (size_t i = 0; i < in->cash_set_count; ++i) {
        const char *n1 = in->cash_names[i], *n2 = in->cash_names2[i];
        if (!n1 || !*n1)
            continue;
        item_set *s = new_set((uint16_t)(base + 1 + (int32_t)i), (const uint8_t *)n1, strlen(n1),
                              (const uint8_t *)n2, strlen(n2));
        if (s)
            insert_set(m, s);
    }
    for (size_t i = 0; i < in->cash_item_count; ++i) {
        const int32_t *t = in->cash_items + 3 * i;
        int16_t index = (int16_t)((int16_t)t[2] + (int16_t)base);
        if (!index)
            continue;
        int32_t code = t[0] * 0x200 + t[1];
        if (!in->has_record || !in->has_record(in->context, code))
            continue;
        item_set *s = find_index(m, index);
        if (s)
            push_entry(s, (set_entry){code, 1});
    }
    return m;
}

void mu_gi_sets_free(mu_gi_sets *m)
{
    if (!m)
        return;
    for (size_t i = 0; i < m->count; ++i)
        free_set(m->order[i]);
    free(m->order);
    free(m);
}

size_t mu_gi_sets_count(const mu_gi_sets *m)
{
    return m ? m->count : 0;
}

const char *mu_gi_set_prefix(const mu_gi_sets *m, int32_t code, uint8_t set_bits, uint8_t kind_b)
{
    if (!m)
        return "";
    uint8_t want = (uint8_t)(set_bits & 0x33);
    for (size_t i = 0; i < m->count; ++i) {
        const item_set *s = m->order[i];
        for (size_t k = 0; k < s->nentries; ++k)
            if (s->entries[k].code == code && (s->entries[k].bits == want || kind_b == 0x79))
                return s->name2;
        for (size_t k = 0; k < s->npairs; ++k)
            for (int j = 0; j < 2; ++j)
                if (s->pairs[k][j].code == code && s->pairs[k][j].bits == want)
                    return s->name2;
    }
    return "";
}
