/* The client's skill table row parser (NATIVE-SKILL-001); see skill_table.h. */
#include "skill_table.h"

#include <stdlib.h>
#include <string.h>

#ifndef MU_SKILL_MUTATION
#define MU_SKILL_MUTATION 0
#endif

/* boost lexical_cast<unsigned> main loop (lcast_ret_unsigned): digits are taken from the last one, the
 * multiplier tracks overflow and a non-zero digit may not push past the maximum. */
static int lcast_unsigned(const char *begin, const char *end, uint32_t *out)
{
    if (begin >= end)
        return 0;
    const char *p = end - 1;
    if (*p < '0' || *p > '9')
        return 0;
    uint32_t value = (uint32_t)(*p - '0'), multiplier = 1;
    int overflowed = 0;
    const uint32_t maxv = 0xffffffffu;
    for (--p; p >= begin; --p) {
        overflowed = overflowed || (maxv / 10 < multiplier);
        multiplier *= 10;
        if (*p < '0' || *p > '9')
            return 0;
        uint32_t digit = (uint32_t)(*p - '0');
        uint32_t sub = multiplier * digit;
        if (digit && (overflowed || maxv / digit < multiplier || maxv - sub < value))
            return 0;
        value += sub;
    }
    *out = value;
    return 1;
}

int mu_skill_lexical_int(const char *text, size_t length, int32_t *out)
{
    if (!length)
        return 0;
    const char *begin = text, *end = text + length;
    int minus = *begin == '-';
    if (minus || *begin == '+')
        ++begin;
    uint32_t u;
    if (!lcast_unsigned(begin, end, &u))
        return 0;
    if (minus) {
        if (u > 0x80000000u)
            return 0;
        *out = (int32_t)(0u - u);
    } else {
#if MU_SKILL_MUTATION == 1
        if (u > 0x7ffffffeu)          /* planted: off-by-one range */
#else
        if (u > 0x7fffffffu)
#endif
            return 0;
        *out = (int32_t)u;
    }
    return 1;
}

int mu_skill_lexical_bool(const char *text, size_t length, uint8_t *out)
{
    if (!length)
        return 0;
    const char *start = text, *last = text + length - 1;
    int value = *last == '1';
    if (!value && *last != '0')
        return 0;
    if (start != last) {
        if (*start == '+' || (*start == '-' && !value))
            ++start;
        for (; start != last; ++start)
            if (*start != '0')
                return 0;
    }
    *out = (uint8_t)value;
    return 1;
}

long mu_skill_unquote(const char *text, size_t length, char *out, size_t cap)
{
    /* last = rfind('"'), first = find('"'); the name is substr(first + 1, last - first - 1) only when
     * first < last and first == 0 (npos compares as -1 in the client's int compare). */
    long last = -1, first = -1;
    for (size_t i = length; i-- > 0;)
        if (text[i] == '"') {
            last = (long)i;
            break;
        }
    for (size_t i = 0; i < length; i++)
        if (text[i] == '"') {
            first = (long)i;
            break;
        }
    if (!(first < last && first == 0))
        return -1;
    size_t n = (size_t)(last - first - 1);
    if (cap) {
        size_t copy = n < cap - 1 ? n : cap - 1;
        if (copy)
            memcpy(out, text + 1, copy);
        out[copy] = 0;
    }
    return (long)n;
}

int mu_skill_parse_row(const char *const *cols, const size_t *lens, size_t ncols, mu_skill_record *out)
{
    if (ncols < MU_SKILL_MIN_COLUMNS)
        return MU_SKILL_ROW_FEW;
    if (ncols < MU_SKILL_COLUMNS)
        return MU_SKILL_ROW_SHORT;
    mu_skill_record r;
    memset(&r, 0, sizeof r);
    memcpy(r.name, "null", 5);          /* the record constructor 0x0116dcb9's name */
    size_t c = 0;
#define LEN(i) (lens ? lens[i] : strlen(cols[i]))
#define INT(dst)                                                    \
    do {                                                            \
        if (!mu_skill_lexical_int(cols[c], LEN(c), &(dst)))         \
            return MU_SKILL_ROW_BAD;                                \
        c++;                                                        \
    } while (0)
    INT(r.index);
    mu_skill_unquote(cols[c], LEN(c), r.name, sizeof r.name);
    c++;
    INT(r.level);
    INT(r.damage);
    INT(r.mana);
    INT(r.ag);
    INT(r.distance);
    INT(r.delay);
#if MU_SKILL_MUTATION == 2
    INT(r.req_strength);              /* planted: energy and strength columns swapped */
    INT(r.req_energy);
#else
    INT(r.req_energy);
    INT(r.req_strength);
#endif
    INT(r.req_dexterity);
    INT(r.req_command);
    INT(r.req_vitality);
    INT(r.mastery);
    INT(r.x54);
    INT(r.use_type);
    INT(r.brand);
    INT(r.x60);
    for (int i = 0; i < 3; i++)
        INT(r.rank[i]);
    for (int i = 0; i < 16; i++)
        INT(r.classes[i]);
    INT(r.x74);
    INT(r.x78);
    INT(r.master_factor);
    INT(r.x80);
    INT(r.x84);
    INT(r.x88);
    INT(r.icon);
    INT(r.type);
    if (!mu_skill_lexical_bool(cols[c], LEN(c), &r.x94))
        return MU_SKILL_ROW_BAD;
    c++;
    INT(r.x98);
    INT(r.x9c);
    INT(r.xa0);
    INT(r.xa4);
    INT(r.xa8);
    INT(r.xac);
    INT(r.xb0);
    INT(r.weapon);
    for (int k = 0; k < 2; k++) {
        int32_t first, second;
        INT(first);
        if (first != -1) {
            /* the second column is read only here; the index advances either way */
            if (!mu_skill_lexical_int(cols[c], LEN(c), &second))
                return MU_SKILL_ROW_BAD;
            r.pairs[r.npairs][0] = first;
            r.pairs[r.npairs][1] = second;
            r.npairs++;
        }
        c++;
    }
    INT(r.imprint);
    int32_t flag;
    INT(flag);
    r.xc8 = flag != 0;
    INT(r.damage_type);
#undef INT
#undef LEN
    r.skip = 0;
    *out = r;
    return MU_SKILL_ROW_OK;
}

static size_t lower_bound(const mu_skill_table *t, int32_t index)
{
    size_t lo = 0, hi = t->count;
    while (lo < hi) {
        size_t mid = (lo + hi) / 2;
        if (t->records[mid].index < index)
            lo = mid + 1;
        else
            hi = mid;
    }
    return lo;
}

int mu_skill_table_add(mu_skill_table *t, const mu_skill_record *record)
{
    size_t at = lower_bound(t, record->index);
    if (at < t->count && t->records[at].index == record->index)
        return 0;
    if (t->count == t->capacity) {
        size_t capacity = t->capacity ? t->capacity * 2 : 256;
        mu_skill_record *grown = realloc(t->records, capacity * sizeof *grown);
        if (!grown)
            return -1;
        t->records = grown;
        t->capacity = capacity;
    }
    memmove(t->records + at + 1, t->records + at, (t->count - at) * sizeof *t->records);
    t->records[at] = *record;
    t->count++;
    return 1;
}

const mu_skill_record *mu_skill_table_get(const mu_skill_table *t, int32_t index)
{
    if (!t || !t->count)
        return NULL;
    size_t at = lower_bound(t, index);
    return at < t->count && t->records[at].index == index ? &t->records[at] : NULL;
}

void mu_skill_table_free(mu_skill_table *t)
{
    free(t->records);
    memset(t, 0, sizeof *t);
}
