/* The quest system singleton (NATIVE-QUEST-001); see quest.h. */
#include "quest_internal.h"

#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* 0x00fe1a06: 1..199 -> 2, below 400 (also index <= 0: the chain tests "index < 1 || index > 199" first)
 * -> 3, 400..599 -> 4, 600..999 -> 3, else -1. */
static int32_t category_exact(int32_t index)
{
    if (index >= 1 && index <= 199)
        return 2;
    if (index < 400)
        return 3;
    if (index < 600)
        return MU_QUEST_MUTATION == 1 && index == 400 ? 3 : 4;
    if (index < 1000)
        return 3;
    return -1;
}

int32_t mu_quest_category(int32_t index)
{
    return category_exact(index);
}

static int cmp_quest(const void *a, const void *b)
{
    int32_t x = ((const mu_quest *)a)->index, y = ((const mu_quest *)b)->index;
    return (x > y) - (x < y);
}

static int cmp_dialogue(const void *a, const void *b)
{
    int32_t x = ((const mu_quest_dialogue *)a)->index, y = ((const mu_quest_dialogue *)b)->index;
    return (x > y) - (x < y);
}

/* 0x00fe764a: the MUQuestString records of the quest in index order: type 1 title, 2 a page (map keyed by the
 * string index), 3 progress, 4 complete, 5 summary (assignments: the last one wins). */
static int build_dialogue(mu_quest_dialogue *g, const mu_quest_data *d, int32_t index)
{
    memset(g, 0, sizeof *g);
    g->index = index;
    g->title = g->progress = g->complete = g->summary = "";
    int32_t pages = 0;
    for (size_t i = 0; i < d->nstrings; i++)
        if (d->strings[i].quest == index && d->strings[i].type == 2)
            pages++;
    if (pages) {
        g->pages = calloc((size_t)pages, sizeof *g->pages);
        if (!g->pages)
            return -1;
    }
    for (size_t i = 0; i < d->nstrings; i++) {
        const mu_quest_string *s = &d->strings[i];
        if (s->quest != index)
            continue;
        switch (s->type) {
        case 1: g->title = s->text; break;
        case 2: g->pages[g->npages++] = s->text; break;
        case 3: g->progress = s->text; break;
        case 4: g->complete = s->text; break;
        case 5: g->summary = s->text; break;
        default: break;
        }
    }
    return 0;
}

int mu_quest_system_build(mu_quest_system *qs, const mu_quest_data *data)
{
    memset(qs, 0, sizeof *qs);
    qs->data = data;
    size_t n = data ? data->nrecords : 0;
    qs->quests = calloc(n ? n : 1, sizeof *qs->quests);
    qs->dialogues = calloc(n ? n : 1, sizeof *qs->dialogues);
    if (!qs->quests || !qs->dialogues)
        return -1;
    for (size_t i = 0; i < n; i++) {
        /* 0x00fe138b: the MUQuest record (0x0113e6de), a 0x38-byte quest object 0x00fdfc65 */
        const mu_quest_record *r = &data->records[i];
        mu_quest *q = &qs->quests[qs->nquests++];
        memset(q, 0, sizeof *q);
        q->record = r;
        q->index = r->index;
        q->f20 = r->f1c;
        q->f24 = r->f20;
        q->category = category_exact(r->index);
        /* 0x00fe15e9: a dialogue for the index (no MUQuest check) */
        if (build_dialogue(&qs->dialogues[qs->ndialogues++], data, r->index))
            return -1;
    }
    qsort(qs->quests, qs->nquests, sizeof *qs->quests, cmp_quest);
    qsort(qs->dialogues, qs->ndialogues, sizeof *qs->dialogues, cmp_dialogue);
    return 0;
}

void mu_quest_system_free(mu_quest_system *qs)
{
    if (!qs)
        return;
    for (size_t i = 0; i < qs->ndialogues; i++)
        free(qs->dialogues[i].pages);
    free(qs->quests);
    free(qs->dialogues);
    for (int k = 0; k < 3; k++)
        free(qs->active[k]);
    free(qs->items);
    free(qs->values);
    memset(qs, 0, sizeof *qs);
}

mu_quest *mu_quest_get(const mu_quest_system *qs, int32_t index)
{
    size_t lo = 0, hi = qs ? qs->nquests : 0;
    while (lo < hi) {
        size_t mid = (lo + hi) / 2;
        if (qs->quests[mid].index < index)
            lo = mid + 1;
        else
            hi = mid;
    }
    return qs && lo < qs->nquests && qs->quests[lo].index == index ? &qs->quests[lo] : NULL;
}

const mu_quest_dialogue *mu_quest_dialogue_get(const mu_quest_system *qs, int32_t index)
{
    size_t lo = 0, hi = qs ? qs->ndialogues : 0;
    while (lo < hi) {
        size_t mid = (lo + hi) / 2;
        if (qs->dialogues[mid].index < index)
            lo = mid + 1;
        else
            hi = mid;
    }
    return qs && lo < qs->ndialogues && qs->dialogues[lo].index == index ? &qs->dialogues[lo] : NULL;
}

int mu_quest_has_category(const mu_quest_system *qs, int32_t category)
{
    (void)qs;
    return category >= MU_QUEST_CATEGORY_FIRST && category <= MU_QUEST_CATEGORY_LAST;
}

/* sorted int / pair sets */
static size_t lower_int(const int32_t *a, size_t n, int32_t key)
{
    size_t lo = 0, hi = n;
    while (lo < hi) {
        size_t mid = (lo + hi) / 2;
        if (a[mid] < key)
            lo = mid + 1;
        else
            hi = mid;
    }
    return lo;
}

static size_t lower_pair(const mu_quest_pair *a, size_t n, int32_t key)
{
    size_t lo = 0, hi = n;
    while (lo < hi) {
        size_t mid = (lo + hi) / 2;
        if (a[mid].key < key)
            lo = mid + 1;
        else
            hi = mid;
    }
    return lo;
}

static int pair_find(const mu_quest_pair *a, size_t n, int32_t key, size_t *at)
{
    size_t i = lower_pair(a, n, key);
    *at = i;
    return i < n && a[i].key == key;
}

static int pair_set(mu_quest_pair **a, size_t *n, size_t *cap, int32_t key, int32_t value)
{
    size_t i;
    if (pair_find(*a, *n, key, &i)) {
        (*a)[i].value = value;
        return 0;
    }
    if (*n == *cap) {
        size_t c = *cap ? *cap * 2 : 16;
        mu_quest_pair *g = realloc(*a, c * sizeof *g);
        if (!g)
            return -1;
        *a = g;
        *cap = c;
    }
    memmove(*a + i + 1, *a + i, (*n - i) * sizeof **a);
    (*a)[i].key = key;
    (*a)[i].value = value;
    (*n)++;
    return 0;
}

static void pair_erase(mu_quest_pair *a, size_t *n, int32_t key)
{
    size_t i;
    if (pair_find(a, *n, key, &i)) {
        memmove(a + i, a + i + 1, (*n - i - 1) * sizeof *a);
        (*n)--;
    }
}

int32_t mu_quest_item_value(const mu_quest_system *qs, int32_t code)
{
    size_t i;
    return qs && pair_find(qs->items, qs->nitems, code, &i) ? qs->items[i].value : -1;
}

int mu_quest_value_get(const mu_quest_system *qs, int32_t index, int32_t *value)
{
    size_t i;
    if (!qs || !pair_find(qs->values, qs->nvalues, index, &i))
        return 0;
    if (value)
        *value = qs->values[i].value;
    return 1;
}

size_t mu_quest_active(const mu_quest_system *qs, int32_t category, const int32_t **indices)
{
    if (!qs || category < MU_QUEST_CATEGORY_FIRST || category > MU_QUEST_CATEGORY_LAST) {
        if (indices)
            *indices = NULL;
        return 0;
    }
    int k = category - MU_QUEST_CATEGORY_FIRST;
    if (indices)
        *indices = qs->active[k];
    return qs->nactive[k];
}

int mu_quest_is_active(const mu_quest_system *qs, int32_t category, int32_t index)
{
    const int32_t *a;
    size_t n = mu_quest_active(qs, category, &a);
    size_t i = lower_int(a, n, index);
    return i < n && a[i] == index;
}

/* ---- the event log ---------------------------------------------------------------------------- */

void mu_quest_log_clear(mu_quest_log *log)
{
    if (!log)
        return;
    log->len = 0;
    log->lines = 0;
    if (log->text)
        log->text[0] = 0;
}

void mu_quest_log_free(mu_quest_log *log)
{
    if (!log)
        return;
    free(log->text);
    memset(log, 0, sizeof *log);
}

void mu_quest_logf(mu_quest_log *log, const char *fmt, ...)
{
    if (!log)
        return;
    va_list ap;
    va_start(ap, fmt);
    va_list cp;
    va_copy(cp, ap);
    int need = vsnprintf(NULL, 0, fmt, cp);
    va_end(cp);
    if (need < 0) {
        va_end(ap);
        return;
    }
    size_t want = log->len + (size_t)need + 2;
    if (want > log->cap) {
        size_t c = log->cap ? log->cap : 1024;
        while (c < want)
            c *= 2;
        char *g = realloc(log->text, c);
        if (!g) {
            va_end(ap);
            return;
        }
        log->text = g;
        log->cap = c;
    }
    vsnprintf(log->text + log->len, (size_t)need + 1, fmt, ap);
    va_end(ap);
    log->len += (size_t)need;
    log->text[log->len++] = '\n';
    log->text[log->len] = 0;
    log->lines++;
}

/* ---- activation (with the client's side effects) ----------------------------------------------- */

static int active_add(mu_quest_system *qs, int k, int32_t index)
{
    size_t i = lower_int(qs->active[k], qs->nactive[k], index);
    if (i < qs->nactive[k] && qs->active[k][i] == index)
        return 0;
    if (qs->nactive[k] == qs->cap_active[k]) {
        size_t c = qs->cap_active[k] ? qs->cap_active[k] * 2 : 16;
        int32_t *g = realloc(qs->active[k], c * sizeof *g);
        if (!g)
            return -1;
        qs->active[k] = g;
        qs->cap_active[k] = c;
    }
    memmove(qs->active[k] + i + 1, qs->active[k] + i, (qs->nactive[k] - i) * sizeof(int32_t));
    qs->active[k][i] = index;
    qs->nactive[k]++;
    return 1;
}

static void active_remove(mu_quest_system *qs, int k, int32_t index)
{
    size_t i = lower_int(qs->active[k], qs->nactive[k], index);
    if (i < qs->nactive[k] && qs->active[k][i] == index) {
        memmove(qs->active[k] + i, qs->active[k] + i + 1, (qs->nactive[k] - i - 1) * sizeof(int32_t));
        qs->nactive[k]--;
    }
}

/* 0x00fe16e4 */
mu_quest *mu_quest_activate(mu_quest_client *c, int32_t index)
{
    mu_quest_system *qs = &c->qs;
    mu_quest *q = mu_quest_get(qs, index);
    if (!q)
        return NULL;
    /* 0x00fe1506(quest +0x28) then 0x00fdfdee: insert when the quest's category is the category's id */
    if (q->category >= MU_QUEST_CATEGORY_FIRST && q->category <= MU_QUEST_CATEGORY_LAST)
        active_add(qs, q->category - MU_QUEST_CATEGORY_FIRST, q->index);
    /* an item goal (type 1): 0x00fe2711(code, accept[1]) inserts when the code is absent */
    if (q->record && q->record->goal[1] == 1) {
        int32_t code = q->record->goal[2] * 0x200 + q->record->goal[3];
        size_t at;
        if (!pair_find(qs->items, qs->nitems, code, &at))
            pair_set(&qs->items, &qs->nitems, &qs->cap_items, code, q->record->accept[1]);
    }
    if (c->summary)
        mu_quest_logf(&c->log, "summary add %d", q->index);
    return q;
}

/* 0x00fe17db */
void mu_quest_deactivate(mu_quest_client *c, int32_t index)
{
    mu_quest_system *qs = &c->qs;
    int32_t cat = category_exact(index);
    if (cat >= MU_QUEST_CATEGORY_FIRST && cat <= MU_QUEST_CATEGORY_LAST)
        active_remove(qs, cat - MU_QUEST_CATEGORY_FIRST, index);
    mu_quest *q = mu_quest_get(qs, index);
    if (q && q->record && q->record->goal[1] == 1) {
        /* 0x00fe2763: erase when present with the same value */
        int32_t code = q->record->goal[2] * 0x200 + q->record->goal[3];
        size_t at;
        if (pair_find(qs->items, qs->nitems, code, &at) && qs->items[at].value == q->record->accept[1])
            pair_erase(qs->items, &qs->nitems, code);
    }
    if (c->summary)
        mu_quest_logf(&c->log, "summary remove %d", index);
}

/* 0x00fe18c4 */
void mu_quest_reset_active(mu_quest_client *c)
{
    for (int k = 0; k < 3; k++)
        c->qs.nactive[k] = 0;
    c->qs.nitems = 0;
    if (c->summary)
        mu_quest_logf(&c->log, "summary clear");
}

void mu_quest_value_set(mu_quest_system *qs, int32_t index, int32_t value)
{
    pair_set(&qs->values, &qs->nvalues, &qs->cap_values, index, value);
}

void mu_quest_value_erase(mu_quest_system *qs, int32_t index)
{
    pair_erase(qs->values, &qs->nvalues, index);
}
