/* Host and test accessors of reconstructed/quest (NATIVE-QUEST-001); see quest.h. */
#include "quest_internal.h"

#include <limits.h>
#include <stdio.h>
#include <string.h>

size_t mu_quest_client_size(void)
{
    return sizeof(mu_quest_client);
}

const char *mu_quest_log_text(const mu_quest_client *c)
{
    return c && c->log.text ? c->log.text : "";
}

int32_t mu_quest_client_field(mu_quest_client *c, const char *name, int set, int32_t value)
{
    struct { const char *name; int32_t *p; uint8_t *b; int *i; } F[] = {
        {"progress.visible", NULL, NULL, &c->progress.visible},
        {"progress.quest", &c->progress.quest, NULL, NULL},
        {"progress.quest_ptr", &c->progress.quest_ptr, NULL, NULL},
        {"progress.mode", &c->progress.mode, NULL, NULL},
        {"progress.pages", &c->progress.npages, NULL, NULL},
        {"info.visible", NULL, NULL, &c->info.visible},
        {"info.tab", &c->info.tab, NULL, NULL},
        {"info.first_open", NULL, &c->info.first_open, NULL},
        {"info.selected2", &c->info.tabs[0].selected, NULL, NULL},
        {"info.selected3", &c->info.tabs[1].selected, NULL, NULL},
        {"info.selected4", &c->info.tabs[2].selected, NULL, NULL},
        {"dialog.visible", NULL, NULL, &c->dialog.visible},
        {"dialog.list_mode", NULL, &c->dialog.list_mode, NULL},
        {"dialog.options", &c->dialog.options, NULL, NULL},
        {"dialog.choice", &c->dialog.choice, NULL, NULL},
        {"summary", NULL, NULL, &c->summary},
        {"font", (int32_t *)&c->font, NULL, NULL},
        {"font_default", (int32_t *)&c->font_default, NULL, NULL},
        {"world", &c->world, NULL, NULL},
    };
    for (size_t k = 0; k < sizeof F / sizeof F[0]; k++) {
        if (strcmp(F[k].name, name))
            continue;
        if (F[k].p) {
            if (set)
                *F[k].p = value;
            return *F[k].p;
        }
        if (F[k].b) {
            if (set)
                *F[k].b = (uint8_t)value;
            return *F[k].b;
        }
        if (set)
            *F[k].i = (int)value;
        return *F[k].i;
    }
    return INT32_MIN;
}

int mu_quest_fields(const mu_quest_client *c, int32_t index, int32_t out[4])
{
    const mu_quest *q = mu_quest_get(&c->qs, index);
    if (!q) {
        memset(out, 0, 4 * sizeof *out);
        return 0;
    }
    out[0] = q->state;
    out[1] = q->count;
    out[2] = q->seen;
    out[3] = q->category;
    return 1;
}

int mu_quest_set_fields(mu_quest_client *c, int32_t index, int32_t state, int32_t count, int32_t seen)
{
    mu_quest *q = mu_quest_get(&c->qs, index);
    if (!q)
        return 0;
    q->state = state;
    q->count = count;
    q->seen = (uint8_t)seen;
    return 1;
}

const char *mu_quest_maps_text(const mu_quest_client *c)
{
    static char buf[65536];
    size_t n = 0;
    buf[0] = 0;
    n += (size_t)snprintf(buf + n, sizeof buf - n, "items:");
    for (size_t i = 0; i < c->qs.nitems && n < sizeof buf; i++)
        n += (size_t)snprintf(buf + n, sizeof buf - n, "%d=%d,", c->qs.items[i].key, c->qs.items[i].value);
    if (n < sizeof buf)
        n += (size_t)snprintf(buf + n, sizeof buf - n, " values:");
    for (size_t i = 0; i < c->qs.nvalues && n < sizeof buf; i++)
        n += (size_t)snprintf(buf + n, sizeof buf - n, "%d=%d,", c->qs.values[i].key, c->qs.values[i].value);
    for (int32_t k = 2; k <= 4 && n < sizeof buf; k++) {
        const int32_t *a;
        size_t m = mu_quest_active(&c->qs, k, &a);
        n += (size_t)snprintf(buf + n, sizeof buf - n, " active%d:", k);
        for (size_t i = 0; i < m && n < sizeof buf; i++)
            n += (size_t)snprintf(buf + n, sizeof buf - n, "%d,", a[i]);
    }
    return buf;
}

void mu_quest_set_hero(mu_quest_client *c, const char *name)
{
    snprintf(c->hero_name, sizeof c->hero_name, "%s", name ? name : "");
}

void mu_quest_set_dialogue_words(mu_quest_client *c, const char *(*word)(void *user, int32_t id))
{
    c->dialogue_word = word;
}

void mu_quest_dialog_set_text(mu_quest_client *c, const char *wrapped, int32_t page)
{
    snprintf(c->dialog.wrapped, sizeof c->dialog.wrapped, "%s", wrapped ? wrapped : "");
    c->dialog.ment_page = page;
}

void mu_quest_client_log_clear(mu_quest_client *c)
{
    mu_quest_log_clear(&c->log);
}

void mu_quest_set_sink(mu_quest_client *c, void (*sink)(void *user, const char *line), void *user)
{
    c->log.sink = sink;
    c->log.sink_user = user;
}
