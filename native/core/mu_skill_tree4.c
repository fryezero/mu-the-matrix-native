/* The fourth skill tree in the native client (NATIVE-SKILL-003); see mu_skill_tree4.h. */
#include "mu_skill_tree4.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "mu_skill.h"

#define DEMO_NODES 1024

typedef struct demo_node { int32_t group, index, level; } demo_node;

struct mu_skill_tree4 {
    mu_t4_table table;
    size_t records;
    mu_t4_window window;
    mu_t4_env env;
    mu_skill_book *book;
    int32_t cls;
    /* OFFLINE DEMO server state */
    mu_skill_tree4_host host;
    demo_node demo[DEMO_NODES];
    int ndemo;
    int32_t points;
};

static int skill_info(void *u, int32_t skill, int *byte0, int *use_type)
{
    mu_skill_tree4 *t = u;
    const mu_skill_record *r = t->book ? mu_skill_book_record(t->book, skill) : NULL;
    *byte0 = r ? 0 : 1;              /* the default record of an absent key has a non-zero first byte */
    *use_type = r ? r->use_type : 0;
    return 1;
}

static int hero_has(void *u, int32_t skill)
{
    mu_skill_tree4 *t = u;
    const mu_skill_hero *h = t->book ? mu_skill_book_hero(t->book) : NULL;
    if (!h)
        return 0;
    for (int i = 0; i < h->count; ++i)
        if (h->skills[i] == skill)
            return 1;
    return 0;
}

static int master_level(void *u, int32_t skill)
{
    mu_skill_tree4 *t = u;
    return t->book ? mu_master_level(mu_skill_book_master(t->book), skill) : 0;
}

static const char *h_text(void *u, int32_t i)
{
    mu_skill_tree4 *t = u;
    const char *s = t->host.text ? t->host.text(t->host.user, i) : "";
    return s ? s : "";
}

static void h_invoke(void *u, const char *name, const char *json)
{
    mu_skill_tree4 *t = u;
    if (t->host.invoke)
        t->host.invoke(t->host.user, name, json);
}

static void h_msgbox(void *u, const char *text)
{
    mu_skill_tree4 *t = u;
    if (t->host.msgbox)
        t->host.msgbox(t->host.user, text);
}

static void h_confirm(void *u, int id, const char *text)
{
    mu_skill_tree4 *t = u;
    if (t->host.confirm)
        t->host.confirm(t->host.user, id, text);
}

void mu_skill_tree4_set_host(mu_skill_tree4 *t, const mu_skill_tree4_host *host)
{
    if (!t)
        return;
    memset(&t->host, 0, sizeof t->host);
    if (host)
        t->host = *host;
    t->env.text = h_text;
    t->env.invoke = h_invoke;
    t->env.msgbox = h_msgbox;
    t->env.confirm = h_confirm;
}

static void load(mu_skill_tree4 *t, const char *dir)
{
    char path[1024];
    snprintf(path, sizeof path, "%s/tree4.tsv", dir ? dir : ".");
    FILE *f = fopen(path, "r");
    if (!f)
        return;
    char line[1024];
    int min_columns = 22;
    while (fgets(line, sizeof line, f)) {          /* the header carries the minimum column count (+0x38) */
        const char *m = strstr(line, "min_columns ");
        if (line[0] == '#') {
            if (m)
                min_columns = atoi(m + 12);
            continue;
        }
    }
    rewind(f);
    mu_t4_table_init(&t->table, min_columns);
    while (fgets(line, sizeof line, f)) {
        if (line[0] == '#' || line[0] == '\n')
            continue;
        if (!strncmp(line, "class\t", 6)) {
            mu_t4_table_class(&t->table, (int32_t)strtol(line + 6, NULL, 10));
            continue;
        }
        int32_t v[32];
        int n = 0;
        char *p = line, *end;
        while (n < 32) {
            long x = strtol(p, &end, 10);
            if (end == p)
                break;
            v[n++] = (int32_t)x;
            p = end;
        }
        if (n < 1 + MU_T4_FIELDS)
            continue;
        if (mu_t4_table_row(&t->table, v[0], v + 1, MU_T4_FIELDS)) {
            ++t->records;
            if (n > 1 + MU_T4_FIELDS && v[1 + MU_T4_FIELDS]) {
                mu_t4_record *r = (mu_t4_record *)mu_t4_table_get(&t->table, v[0], v[2], v[1]);
                if (r)
                    r->hidden = 1;
            }
        }
    }
    fclose(f);
}

mu_skill_tree4 *mu_skill_tree4_open(const char *lang_dir, mu_skill_book *book)
{
    mu_skill_tree4 *t = calloc(1, sizeof *t);
    if (!t)
        return NULL;
    mu_t4_table_init(&t->table, 22);
    t->book = book;
    load(t, lang_dir);
    mu_t4_window_init(&t->window, &t->table);
    t->env.user = t;
    t->env.skill_info = skill_info;
    t->env.hero_has = hero_has;
    t->env.master_level = master_level;
    t->cls = -1;
    return t;
}

void mu_skill_tree4_close(mu_skill_tree4 *t)
{
    if (!t)
        return;
    mu_t4_window_free(&t->window);
    mu_t4_table_free(&t->table);
    free(t);
}

size_t mu_skill_tree4_records(const mu_skill_tree4 *t) { return t ? t->records : 0; }
mu_t4_window *mu_skill_tree4_window(mu_skill_tree4 *t) { return t ? &t->window : NULL; }
mu_t4_env *mu_skill_tree4_env(mu_skill_tree4 *t) { return t ? &t->env : NULL; }

void mu_skill_tree4_enter(mu_skill_tree4 *t, int32_t class_index)
{
    if (!t)
        return;
    t->cls = class_index;
    mu_t4_set_class(&t->window, class_index);
    t->ndemo = 0;
}

int mu_skill_tree4_receive(mu_skill_tree4 *t, const uint8_t *packet, size_t size)
{
    if (!t || size < 4)
        return 0;
    int op = packet[0] == 0xc1 ? packet[2] : packet[0] == 0xc2 && size > 3 ? packet[3] : -1;
    if (op != 0x7e)
        return 0;
    return mu_t4_receive(&t->window, &t->env, packet, size);
}

/* ---- OFFLINE DEMO server ---------------------------------------------------------------------------------- */

static demo_node *demo_at(mu_skill_tree4 *t, int32_t group, int32_t index)
{
    for (int i = 0; i < t->ndemo; ++i)
        if (t->demo[i].group == group && t->demo[i].index == index)
            return &t->demo[i];
    return NULL;
}

/* DEMO: the hero meets the fourth tree's master requirements (f[21] of use type 3/4 at f[22]): the server's full
 * A0 10 list again with those Master nodes raised to the level (existing entries keep theirs). */
static void demo_requirements(mu_skill_tree4 *t, const mu_t4_tclass *c)
{
    mu_master_tree *tree = t->book ? mu_skill_book_master(t->book) : NULL;
    if (!tree || !c)
        return;
    static uint8_t packet[12 + 16 * MU_MASTER_NODES];
    memset(packet, 0, sizeof packet);
    packet[0] = 0xc2;
    packet[3] = 0xa0;
    packet[4] = 0x10;
    int count = 0;
    for (int i = 0; i < tree->nnodes && count < MU_MASTER_NODES; ++i) {
        const mu_master_node *node = &tree->nodes[i];
        int level = mu_master_level(tree, node->skill);
        for (int g = 0; g < c->ngroups; ++g)
            for (int k = 0; k < c->groups[g].nrec; ++k) {
                const mu_t4_record *r = &c->groups[g].rec[k];
                const mu_skill_record *sr = mu_skill_book_record(t->book, r->f[MU_T4_REQ_SKILL]);
                if (r->f[MU_T4_REQ_SKILL] == node->skill && sr && (sr->use_type == 3 || sr->use_type == 4) &&
                    r->f[MU_T4_REQ_LEVEL] > level)
                    level = r->f[MU_T4_REQ_LEVEL];
            }
        if (level <= 0)
            continue;
        uint8_t *e = packet + 12 + 16 * count++;
        float value = 25.0f, next = 30.0f;          /* DEMO values, as mu_skill_book_demo_master_login */
        e[0] = node->slot;
        e[1] = (uint8_t)level;
        memcpy(e + 4, &value, 4);
        memcpy(e + 8, &next, 4);
        e[12] = 1;
    }
    size_t size = 12 + 16 * (size_t)count;
    packet[1] = (uint8_t)(size >> 8);
    packet[2] = (uint8_t)size;
    memcpy(packet + 8, &count, 4);
    mu_skill_book_receive(t->book, packet, size);
}

int mu_skill_tree4_demo_login(mu_skill_tree4 *t, int32_t points)
{
    if (!t)
        return 0;
    const mu_t4_tclass *c = mu_t4_table_class_of(&t->table, t->cls);
    demo_requirements(t, c);
    t->points = points;
    t->ndemo = 0;
    for (int g = 0; c && g < c->ngroups; ++g)
        for (int i = 0; i < c->groups[g].nrec && t->ndemo < DEMO_NODES; ++i)
            t->demo[t->ndemo++] = (demo_node){c->groups[g].key, c->groups[g].rec[i].f[MU_T4_INDEX], 0};
    size_t size = 0xb + 12 * (size_t)t->ndemo;
    uint8_t *p = calloc(1, size);
    if (!p)
        return 0;
    p[0] = 0xc2;               /* C2 head (size big-endian), opcode +3, sub +4: points +5, count +7, entries +0xb */
    p[1] = (uint8_t)(size >> 8);
    p[2] = (uint8_t)size;
    p[3] = 0x7e;
    p[4] = 2;
    p[5] = (uint8_t)points;
    p[6] = (uint8_t)(points >> 8);
    uint32_t n = (uint32_t)t->ndemo;
    memcpy(p + 7, &n, 4);
    for (int i = 0; i < t->ndemo; ++i) {
        uint8_t *e = p + 0xb + 12 * i;
        e[0] = (uint8_t)t->demo[i].group;
        e[1] = (uint8_t)t->demo[i].index;
        e[2] = (uint8_t)(t->demo[i].index >> 8);
        e[3] = 0;
        float zero = 0;
        memcpy(e + 4, &zero, 4);
        memcpy(e + 8, &zero, 4);
    }
    int r = mu_t4_receive(&t->window, &t->env, p, size);
    free(p);
    return r;
}

int mu_skill_tree4_demo_request(mu_skill_tree4 *t, const uint8_t *packet, size_t size)
{
    if (!t || size < 9 || packet[0] != 0xc1 || packet[2] != 0x7e || packet[3] != 1)
        return 0;
    int32_t group = packet[4], index = packet[7] | packet[8] << 8;
    const mu_t4_record *r = mu_t4_table_get(&t->table, t->cls, group, index);
    demo_node *d = demo_at(t, group, index);
    uint8_t a[0x13] = {0xc1, 0x13, 0x7e, 1};
    if (!r || !d || d->level >= r->f[MU_T4_MAX] || t->points < r->f[MU_T4_COST]) {
        a[4] = 7;              /* the client's message 3: not enough points */
        return mu_t4_receive(&t->window, &t->env, a, sizeof a);
    }
    d->level += 1;
    t->points -= r->f[MU_T4_COST];
    a[4] = 1;
    a[5] = (uint8_t)t->points;
    a[6] = (uint8_t)(t->points >> 8);
    a[7] = (uint8_t)group;
    a[8] = (uint8_t)d->level;
    a[9] = (uint8_t)index;
    a[10] = (uint8_t)(index >> 8);
    float value = (float)d->level, next = (float)(d->level + 1);     /* DEMO stand-ins */
    memcpy(a + 0xb, &value, 4);
    memcpy(a + 0xf, &next, 4);
    return mu_t4_receive(&t->window, &t->env, a, sizeof a);
}
