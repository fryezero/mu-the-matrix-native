/* MUQuest / MUQuestString / ItemLevelTooltip plaintext (NATIVE-QUEST-001); see quest.h. */
#include "quest.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* The converter's escapes: \t \n \r \\ \xHH. */
static char *unescape(const char *s, size_t n)
{
    char *out = malloc(n + 1);
    if (!out)
        return NULL;
    size_t k = 0;
    for (size_t i = 0; i < n; i++) {
        if (s[i] == '\\' && i + 1 < n) {
            char c = s[i + 1];
            if (c == 'x' && i + 3 < n) {
                char hex[3] = {s[i + 2], s[i + 3], 0};
                out[k++] = (char)strtol(hex, NULL, 16);
                i += 3;
                continue;
            }
            out[k++] = c == 't' ? '\t' : c == 'n' ? '\n' : c == 'r' ? '\r' : c;
            i++;
            continue;
        }
        out[k++] = s[i];
    }
    out[k] = 0;
    return out;
}

/* Splits one line into at most `max` TAB-separated fields (pointers into the line, lengths). */
static int fields(const char *line, size_t len, const char **f, size_t *flen, int max)
{
    int n = 0;
    size_t start = 0;
    for (size_t i = 0; i <= len && n < max; i++) {
        if (i == len || line[i] == '\t') {
            f[n] = line + start;
            flen[n] = i - start;
            n++;
            start = i + 1;
        }
    }
    return n;
}

static int ints(const char *s, size_t n, int32_t *out, int count)
{
    char buf[1024];
    if (n >= sizeof buf)
        return 0;
    memcpy(buf, s, n);
    buf[n] = 0;
    char *p = buf;
    for (int i = 0; i < count; i++) {
        char *end = NULL;
        long v = strtol(p, &end, 10);
        if (end == p)
            return 0;
        out[i] = (int32_t)v;
        p = end;
    }
    return 1;
}

static int32_t int_field(const char *s, size_t n)
{
    char buf[32];
    if (n >= sizeof buf)
        n = sizeof buf - 1;
    memcpy(buf, s, n);
    buf[n] = 0;
    return (int32_t)strtol(buf, NULL, 10);
}

/* Iterates the non-comment lines of a text. */
typedef struct line_iter {
    const char *p;
} line_iter;

static int next_line(line_iter *it, const char **line, size_t *len)
{
    while (it->p && *it->p) {
        const char *s = it->p, *e = strchr(s, '\n');
        size_t n = e ? (size_t)(e - s) : strlen(s);
        it->p = e ? e + 1 : s + n;
        if (n && s[n - 1] == '\r')
            n--;
        if (!n || s[0] == '#')
            continue;
        *line = s;
        *len = n;
        return 1;
    }
    return 0;
}

static int cmp_record(const void *a, const void *b)
{
    int32_t x = ((const mu_quest_record *)a)->index, y = ((const mu_quest_record *)b)->index;
    return (x > y) - (x < y);
}

static int cmp_string(const void *a, const void *b)
{
    int32_t x = ((const mu_quest_string *)a)->index, y = ((const mu_quest_string *)b)->index;
    return (x > y) - (x < y);
}

static int cmp_tip(const void *a, const void *b)
{
    int32_t x = ((const mu_quest_level_tip *)a)->key, y = ((const mu_quest_level_tip *)b)->key;
    return (x > y) - (x < y);
}

static void free_records(mu_quest_data *d)
{
    for (size_t i = 0; i < d->nrecords; i++)
        free(d->records[i].name);
    free(d->records);
    d->records = NULL;
    d->nrecords = 0;
}

static void free_strings(mu_quest_data *d)
{
    for (size_t i = 0; i < d->nstrings; i++)
        free(d->strings[i].text);
    free(d->strings);
    d->strings = NULL;
    d->nstrings = 0;
}

static void free_tips(mu_quest_data *d)
{
    for (size_t i = 0; i < d->nlevel_tips; i++)
        free(d->level_tips[i].name);
    free(d->level_tips);
    d->level_tips = NULL;
    d->nlevel_tips = 0;
}

/* std::map insert semantics: the first record of a key stays (stable sort, then drop repeats). */
static size_t unique_sorted(void *base, size_t n, size_t size, int (*cmp)(const void *, const void *),
                            void (*drop)(void *))
{
    /* stable insertion sort (the first record of a key stays first) */
    char *b = base;
    char tmp[sizeof(mu_quest_record) + sizeof(mu_quest_string) + sizeof(mu_quest_level_tip)];
    for (size_t i = 1; i < n; i++) {
        size_t j = i;
        memcpy(tmp, b + i * size, size);
        while (j > 0 && cmp(b + (j - 1) * size, tmp) > 0) {
            memcpy(b + j * size, b + (j - 1) * size, size);
            j--;
        }
        memcpy(b + j * size, tmp, size);
    }
    size_t k = 0;
    for (size_t i = 0; i < n; i++) {
        if (k && cmp(b + (k - 1) * size, b + i * size) == 0) {
            drop(b + i * size);
            continue;
        }
        if (k != i)
            memcpy(b + k * size, b + i * size, size);
        k++;
    }
    return k;
}

static void drop_record(void *p) { free(((mu_quest_record *)p)->name); }
static void drop_string(void *p) { free(((mu_quest_string *)p)->text); }
static void drop_tip(void *p) { free(((mu_quest_level_tip *)p)->name); }

long mu_quest_parse_records(mu_quest_data *d, const char *text)
{
    free_records(d);
    size_t cap = 64, n = 0;
    mu_quest_record *r = calloc(cap, sizeof *r);
    if (!r)
        return -1;
    line_iter it = {text};
    const char *line;
    size_t len;
    while (next_line(&it, &line, &len)) {
        const char *f[6];
        size_t fl[6];
        if (fields(line, len, f, fl, 6) < 6)
            continue;
        if (n == cap) {
            mu_quest_record *g = realloc(r, cap * 2 * sizeof *r);
            if (!g)
                break;
            r = g;
            cap *= 2;
        }
        mu_quest_record *q = &r[n];
        memset(q, 0, sizeof *q);
        q->index = int_field(f[0], fl[0]);
        q->f1c = int_field(f[2], fl[2]);
        q->f20 = int_field(f[3], fl[3]);
        if (!ints(f[4], fl[4], q->accept, MU_QUEST_ACCEPT_INTS) || !ints(f[5], fl[5], q->goal, MU_QUEST_GOAL_INTS))
            continue;
        q->name = unescape(f[1], fl[1]);
        if (!q->name)
            break;
        n++;
    }
    n = unique_sorted(r, n, sizeof *r, cmp_record, drop_record);
    d->records = r;
    d->nrecords = n;
    return (long)n;
}

long mu_quest_parse_strings(mu_quest_data *d, const char *text)
{
    free_strings(d);
    size_t cap = 256, n = 0;
    mu_quest_string *s = calloc(cap, sizeof *s);
    if (!s)
        return -1;
    line_iter it = {text};
    const char *line;
    size_t len;
    while (next_line(&it, &line, &len)) {
        const char *f[4];
        size_t fl[4];
        if (fields(line, len, f, fl, 4) < 4)
            continue;
        if (n == cap) {
            mu_quest_string *g = realloc(s, cap * 2 * sizeof *s);
            if (!g)
                break;
            s = g;
            cap *= 2;
        }
        s[n].index = int_field(f[0], fl[0]);
        s[n].type = int_field(f[1], fl[1]);
        s[n].quest = int_field(f[2], fl[2]);
        s[n].text = unescape(f[3], fl[3]);
        if (!s[n].text)
            break;
        n++;
    }
    n = unique_sorted(s, n, sizeof *s, cmp_string, drop_string);
    d->strings = s;
    d->nstrings = n;
    return (long)n;
}

long mu_quest_parse_level_tips(mu_quest_data *d, const char *text)
{
    free_tips(d);
    size_t cap = 64, n = 0;
    mu_quest_level_tip *t = calloc(cap, sizeof *t);
    if (!t)
        return -1;
    line_iter it = {text};
    const char *line;
    size_t len;
    while (next_line(&it, &line, &len)) {
        const char *f[5];
        size_t fl[5];
        if (fields(line, len, f, fl, 5) < 5)
            continue;
        if (n == cap) {
            mu_quest_level_tip *g = realloc(t, cap * 2 * sizeof *t);
            if (!g)
                break;
            t = g;
            cap *= 2;
        }
        t[n].key = int_field(f[0], fl[0]);
        t[n].group = int_field(f[1], fl[1]);
        t[n].index = int_field(f[2], fl[2]);
        t[n].level = int_field(f[3], fl[3]);
        t[n].name = unescape(f[4], fl[4]);
        if (!t[n].name)
            break;
        n++;
    }
    n = unique_sorted(t, n, sizeof *t, cmp_tip, drop_tip);
    d->level_tips = t;
    d->nlevel_tips = n;
    return (long)n;
}

static char *read_file(const char *dir, const char *name)
{
    char path[4096];
    snprintf(path, sizeof path, "%s/%s", dir, name);
    FILE *f = fopen(path, "rb");
    if (!f)
        return NULL;
    fseek(f, 0, SEEK_END);
    long n = ftell(f);
    fseek(f, 0, SEEK_SET);
    char *buf = n >= 0 ? malloc((size_t)n + 1) : NULL;
    if (buf) {
        size_t got = fread(buf, 1, (size_t)n, f);
        buf[got] = 0;
    }
    fclose(f);
    return buf;
}

long mu_quest_load_dir(mu_quest_data *d, const char *dir)
{
    if (!d || !dir)
        return 0;
    char *t = read_file(dir, "quests.tsv");
    long n = 0;
    if (t) {
        n = mu_quest_parse_records(d, t);
        free(t);
    }
    if ((t = read_file(dir, "queststrings.tsv"))) {
        mu_quest_parse_strings(d, t);
        free(t);
    }
    if ((t = read_file(dir, "itemleveltip.tsv"))) {
        mu_quest_parse_level_tips(d, t);
        free(t);
    }
    return n < 0 ? 0 : n;
}

void mu_quest_data_free(mu_quest_data *d)
{
    if (!d)
        return;
    free_records(d);
    free_strings(d);
    free_tips(d);
}

const mu_quest_record *mu_quest_record_get(const mu_quest_data *d, int32_t index)
{
    if (!d)
        return NULL;
    size_t lo = 0, hi = d->nrecords;
    while (lo < hi) {
        size_t mid = (lo + hi) / 2;
        if (d->records[mid].index < index)
            lo = mid + 1;
        else
            hi = mid;
    }
    return lo < d->nrecords && d->records[lo].index == index ? &d->records[lo] : NULL;
}
