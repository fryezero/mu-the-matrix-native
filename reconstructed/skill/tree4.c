/* The fourth skill tree (NATIVE-SKILL-003).  See tree4.h; the client addresses are named per routine. */
#include "tree4.h"

#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Planted mistakes for scripts/validate_skill_later.py --mutations (21..27; 0 = none). */
#ifndef MU_SKILL_MUTATION
#define MU_SKILL_MUTATION 0
#endif

/* ---- the table (0x010b499f / 0x010b4506 / 0x01098d4a / 0x0109a86e) -------------------------------------------- */

void mu_t4_table_init(mu_t4_table *t, int32_t min_columns)
{
    memset(t, 0, sizeof *t);
    t->min_columns = min_columns;
}

void mu_t4_table_free(mu_t4_table *t)
{
    for (int c = 0; c < t->nclasses; ++c) {
        for (int g = 0; g < t->classes[c].ngroups; ++g)
            free(t->classes[c].groups[g].rec);
        free(t->classes[c].groups);
    }
    free(t->classes);
    memset(t, 0, sizeof *t);
}

static int class_pos(const mu_t4_table *t, int32_t cls, int *at)
{
    int lo = 0, hi = t->nclasses;
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        if (t->classes[mid].cls < cls)
            lo = mid + 1;
        else
            hi = mid;
    }
    *at = lo;
    return lo < t->nclasses && t->classes[lo].cls == cls;
}

void mu_t4_table_class(mu_t4_table *t, int32_t cls)
{
    int at;
    if (class_pos(t, cls, &at))
        return;
    if (t->nclasses == t->cap) {
        t->cap = t->cap ? t->cap * 2 : 16;
        t->classes = realloc(t->classes, sizeof *t->classes * (size_t)t->cap);
    }
    memmove(t->classes + at + 1, t->classes + at, sizeof *t->classes * (size_t)(t->nclasses - at));
    memset(t->classes + at, 0, sizeof *t->classes);
    t->classes[at].cls = cls;
    ++t->nclasses;
}

const mu_t4_tclass *mu_t4_table_class_of(const mu_t4_table *t, int32_t cls)
{
    int at;
    return t && class_pos(t, cls, &at) ? &t->classes[at] : NULL;
}

static mu_t4_tgroup *tgroup_get(mu_t4_tclass *c, int32_t key, int create)
{
    int lo = 0, hi = c->ngroups;
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        if (c->groups[mid].key < key)
            lo = mid + 1;
        else
            hi = mid;
    }
    if (lo < c->ngroups && c->groups[lo].key == key)
        return &c->groups[lo];
    if (!create)
        return NULL;
    if (c->ngroups == c->cap) {
        c->cap = c->cap ? c->cap * 2 : 8;
        c->groups = realloc(c->groups, sizeof *c->groups * (size_t)c->cap);
    }
    memmove(c->groups + lo + 1, c->groups + lo, sizeof *c->groups * (size_t)(c->ngroups - lo));
    memset(c->groups + lo, 0, sizeof *c->groups);
    c->groups[lo].key = key;         /* 0x0109a802: +0 key, +4 rows 0, +8 empty map */
    ++c->ngroups;
    return &c->groups[lo];
}

static int rec_pos(const mu_t4_tgroup *g, int32_t index, int *at)
{
    int lo = 0, hi = g->nrec;
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        if (g->rec[mid].f[MU_T4_INDEX] < index)
            lo = mid + 1;
        else
            hi = mid;
    }
    *at = lo;
    return lo < g->nrec && g->rec[lo].f[MU_T4_INDEX] == index;
}

int mu_t4_table_row(mu_t4_table *t, int32_t cls, const int32_t *values, int columns)
{
    int at;
    if (columns < t->min_columns || columns < MU_T4_FIELDS)   /* 0x010b4531; 27 columns are read */
        return 0;
    if (!class_pos(t, cls, &at))                            /* 0x010b4569: the class must exist */
        return 0;
    mu_t4_record r;
    memset(&r, 0, sizeof r);
    for (int i = 0; i < 8; ++i)
        r.f[i] = values[i];
    for (int i = 0; i < 5; ++i) {                           /* alternating link pairs */
        r.f[MU_T4_CHILD + i] = values[8 + 2 * i];
        r.f[MU_T4_SHOW + i] = values[9 + 2 * i];
    }
    for (int i = 0; i < 9; ++i)
        r.f[MU_T4_COST + i] = values[18 + i];
    mu_t4_tgroup *g = tgroup_get(&t->classes[at], r.f[MU_T4_GROUP], 1);
    int pos;
    if (rec_pos(g, r.f[MU_T4_INDEX], &pos))                 /* 0x0109a82a: the first record stays */
        return 1;
    if (g->nrec == g->cap) {
        g->cap = g->cap ? g->cap * 2 : 32;
        g->rec = realloc(g->rec, sizeof *g->rec * (size_t)g->cap);
    }
    memmove(g->rec + pos + 1, g->rec + pos, sizeof *g->rec * (size_t)(g->nrec - pos));
    g->rec[pos] = r;
    ++g->nrec;
#if MU_SKILL_MUTATION == 21
    int32_t rows = r.f[MU_T4_INDEX] / 10;
#else
    int32_t rows = r.f[MU_T4_INDEX] / 10 + 1;               /* C division, as idiv */
#endif
    if (rows > g->rows)
        g->rows = rows;
    return 1;
}

const mu_t4_record *mu_t4_table_get(const mu_t4_table *t, int32_t cls, int32_t group, int32_t index)
{
    int at;
    if (!t || !class_pos(t, cls, &at))
        return NULL;
    mu_t4_tgroup *g = tgroup_get(&t->classes[at], group, 0);
    return g && rec_pos(g, index, &at) ? &g->rec[at] : NULL;
}

/* ---- a group state ------------------------------------------------------------------------------------------ */

int mu_t4_group_find(const mu_t4_group *g, int32_t index)
{
    int lo = 0, hi = g->nnodes;
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        if (g->nodes[mid].index < index)
            lo = mid + 1;
        else
            hi = mid;
    }
    return lo < g->nnodes && g->nodes[lo].index == index ? lo : -1;
}

static int list_has(const int16_t *list, int n, int v)
{
    for (int i = 0; i < n; ++i)
        if (list[i] == v)
            return 1;
    return 0;
}

static void list_add(int16_t *list, int *n, int v)
{
    if (*n < MU_T4_LINKS)
        list[(*n)++] = (int16_t)v;
}

static void list_remove(int16_t *list, int *n, int v)   /* std::list::remove: every occurrence */
{
    int k = 0;
    for (int i = 0; i < *n; ++i)
        if (list[i] != v)
            list[k++] = list[i];
    *n = k;
}

/* 0x0109fc9b: link a node's children (f[8..12]) recursively. */
static void link_node(mu_t4_group *g, int pos)
{
    if (pos < 0)
        return;
    for (int i = 0; i < 5; ++i) {
        int32_t child = g->nodes[pos].rec->f[MU_T4_CHILD + i];
        if (child == -1)
            continue;
        int c = mu_t4_group_find(g, child);
        if (c < 0)
            continue;
        mu_t4_node *cn = &g->nodes[c], *pn = &g->nodes[pos];
        if (!list_has(cn->parents, cn->nparents, pos))       /* 0x0109e01c */
            list_add(cn->parents, &cn->nparents, pos);
        if (!list_has(pn->children, pn->nchildren, c)) {     /* 0x0109e054 */
            list_add(pn->children, &pn->nchildren, c);
            pn->leaf = 0;
        }
        link_node(g, c);
    }
}

int mu_t4_req_ok(const mu_t4_group *g, const mu_t4_env *env, int32_t index)
{
    int pos = mu_t4_group_find(g, index);
    if (pos < 0)
        return 0;
    const mu_t4_record *r = g->nodes[pos].rec;
    if (r->f[MU_T4_REQ_SKILL] <= 0)
        return 1;
    int byte0 = 0, use = 0;
    if (!env->skill_info || !env->skill_info(env->user, r->f[MU_T4_REQ_SKILL], &byte0, &use))
        byte0 = 0, use = 0;   /* the default record: zero */
    if (byte0)
        return 0;
    if (use == 3 || use == 4)
        return (env->master_level ? env->master_level(env->user, r->f[MU_T4_REQ_SKILL]) : 0) >=
               r->f[MU_T4_REQ_LEVEL];
    return env->hero_has && env->hero_has(env->user, r->f[MU_T4_REQ_SKILL]);
}

int mu_t4_group_find_skill(const mu_t4_group *g, int32_t skill)
{
    for (int i = 0; i < g->nnodes; ++i)
        if (g->nodes[i].skill == skill)
            return g->nodes[i].index;
    return -1;
}

int mu_t4_prereq_ok(const mu_t4_group *g, int32_t index)
{
    int pos = mu_t4_group_find(g, index);
    if (pos < 0)
        return 0;
    const mu_t4_record *r = g->nodes[pos].rec;
    for (int k = 0; k < 2; ++k) {
        int32_t skill = r->f[k ? MU_T4_PRE2 : MU_T4_PRE1], level = r->f[k ? MU_T4_PRE2_LEVEL : MU_T4_PRE1_LEVEL];
        if (skill <= -1)
            continue;
        int p = mu_t4_group_find(g, mu_t4_group_find_skill(g, skill));
        if (p < 0 || g->nodes[p].level < level)
            return 0;
    }
    return 1;
}

int mu_t4_sibling_free(const mu_t4_group *g, int32_t index)
{
    int pos = mu_t4_group_find(g, index);
    if (pos < 0)
        return 0;
    for (int i = 0; i < g->nnodes; ++i) {
        if (g->nodes[i].index == index)
            continue;
        if (g->nodes[pos].rec->f[MU_T4_SIBLING] == g->nodes[i].rec->f[MU_T4_SIBLING] && g->nodes[i].level > 0)
            return 0;
    }
    return 1;
}

int mu_t4_has_sibling(const mu_t4_group *g, int32_t index)
{
    int pos = mu_t4_group_find(g, index);
    if (pos < 0)
        return 0;
    for (int i = 0; i < g->nnodes; ++i) {
        if (g->nodes[i].index == index)
            continue;
        if (g->nodes[pos].rec->f[MU_T4_SIBLING] == g->nodes[i].rec->f[MU_T4_SIBLING])
            return 1;
    }
    return 0;
}

int mu_t4_branch_parent(const mu_t4_group *g, int32_t index)
{
    int pos = mu_t4_group_find(g, index);
    if (pos < 0)
        return 0;
    const mu_t4_node *n = &g->nodes[pos];
    if (n->level > 0)
        return 0;
    for (int i = 0; i < n->nparents; ++i)
        if (g->nodes[n->parents[i]].rec->f[MU_T4_TYPE] == 3)
            return 1;
    return 0;
}

int mu_t4_can_learn(const mu_t4_group *g, const mu_t4_env *env, int32_t index)
{
    return mu_t4_req_ok(g, env, index) && mu_t4_prereq_ok(g, index) && mu_t4_sibling_free(g, index) &&
           !mu_t4_branch_parent(g, index);
}

int mu_t4_group_init(mu_t4_group *g, const mu_t4_tgroup *tg, const mu_t4_env *env)
{
    memset(g, 0, sizeof *g);
    g->id = tg->key;
    g->rows = tg->rows;
    g->kind = 0;
    g->nodes = calloc((size_t)(tg->nrec ? tg->nrec : 1), sizeof *g->nodes);
    g->roots = calloc((size_t)(tg->nrec ? tg->nrec : 1), sizeof *g->roots);
    if (!g->nodes || !g->roots)
        return 0;
    for (int i = 0; i < tg->nrec; ++i) {
        const mu_t4_record *r = &tg->rec[i];
        if (r->hidden)
            continue;
        /* records are unique and sorted by index: the node map keeps that order */
        mu_t4_node *n = &g->nodes[g->nnodes];
        memset(n, 0, sizeof *n);
        n->index = r->f[MU_T4_INDEX];
        n->leaf = 1;
        n->open = 1;
        n->rec = r;
        n->skill = r->f[MU_T4_SKILL];
        n->level = 0;
        ++g->nnodes;
    }
    /* the second pass keeps the client's order of side effects: roots and availability per record */
    for (int i = 0; i < g->nnodes; ++i) {
        mu_t4_node *n = &g->nodes[i];
#if MU_SKILL_MUTATION == 22
        if (n->index % 10 == 0) {
#else
        if (n->index % 10 == 0 && n->rec->f[MU_T4_TYPE] != 3) {
#endif
            g->roots[g->nroots++] = (int16_t)i;               /* map keyed by index: already sorted */
            if (mu_t4_req_ok(g, env, n->index))
                n->avail = 1;
        }
        if (n->rec->f[MU_T4_TYPE] == 2)
            g->kind = 2;
    }
    for (int i = 0; i < g->nroots; ++i)                       /* 0x0109fc40 */
        link_node(g, g->roots[i]);
    return 1;
}

void mu_t4_group_free(mu_t4_group *g)
{
    free(g->nodes);
    free(g->roots);
    memset(g, 0, sizeof *g);
}

void mu_t4_set_level(mu_t4_group *g, const mu_t4_env *env, int32_t index, int32_t level, float value, float next)
{
    int pos = mu_t4_group_find(g, index);
    if (pos < 0)
        return;
    mu_t4_node *n = &g->nodes[pos];
    n->level = level;
    n->value = value;
    n->next = next;
    if (n->level >= n->rec->f[MU_T4_COST]) {                  /* +0x48: the siblings close */
        for (int i = 0; i < g->nnodes; ++i) {
            if (g->nodes[i].index == index)
                continue;
            if (n->rec->f[MU_T4_SIBLING] == g->nodes[i].rec->f[MU_T4_SIBLING])
                g->nodes[i].avail = 0;
        }
    }
    /* 0x0109fd1a: at the opening level the children that can be learned become available */
#if MU_SKILL_MUTATION == 23
    if (n->level > n->rec->f[MU_T4_OPEN]) {
#else
    if (n->level >= n->rec->f[MU_T4_OPEN]) {
#endif
        for (int i = 0; i < n->nchildren; ++i) {
            mu_t4_node *c = &g->nodes[n->children[i]];
            if (mu_t4_can_learn(g, env, c->index))
                c->avail = 1;
        }
    }
    /* 0x0109fddc: every node with prerequisites follows them */
    for (int i = 0; i < g->nnodes; ++i) {
        mu_t4_node *m = &g->nodes[i];
        const mu_t4_record *r = m->rec;
        int has1 = 0, has2 = 0, ok1 = 0, ok2 = 0;
        if (r->f[MU_T4_PRE1] > -1) {
            has1 = 1;
            int p = mu_t4_group_find(g, mu_t4_group_find_skill(g, r->f[MU_T4_PRE1]));
            if (p >= 0 && g->nodes[p].level >= r->f[MU_T4_PRE1_LEVEL])
                ok1 = 1;
        }
        if (r->f[MU_T4_PRE2] > -1) {
            has2 = 1;
            int p = mu_t4_group_find(g, mu_t4_group_find_skill(g, r->f[MU_T4_PRE2]));
            if (p >= 0 && g->nodes[p].level >= r->f[MU_T4_PRE2_LEVEL])
                ok2 = 1;
        }
        if (has1 && !has2)
            m->avail = (uint8_t)ok1;
        else if (!has1 && has2)
            m->avail = (uint8_t)ok2;
        else if (has1 && has2)
            m->avail = (uint8_t)(ok1 && ok2);
    }
    /* 0x0109ffac: a learned child of a branch node closes the branch and stays available */
    for (int i = 0; i < n->nparents; ++i) {
        mu_t4_node *p = &g->nodes[n->parents[i]];
        if (p->rec->f[MU_T4_TYPE] == 3 && n->level > 0) {
            p->open = 0;
            n->avail = 1;
        }
    }
}

/* 0x0109f9c0: the first branch node down the first-child chain. */
static int branch_below(const mu_t4_group *g, int pos)
{
    if (pos < 0)
        return -1;
    const mu_t4_node *n = &g->nodes[pos];
    for (int i = 0; i < n->nchildren; ++i) {
        int c = n->children[i];
        if (g->nodes[c].rec->f[MU_T4_TYPE] == 3)
            return c;
        return branch_below(g, c);
    }
    return -1;
}

void mu_t4_branch_cleanup(mu_t4_group *g)
{
    for (int r = 0; r < g->nroots; ++r) {
        int b = branch_below(g, g->roots[r]);
        if (b < 0)
            continue;
        mu_t4_node *bn = &g->nodes[b];
        int learned = 0;
        for (int i = 0; i < bn->nchildren; ++i)
            if (g->nodes[bn->children[i]].level > 0)
                learned = 1;
        if (learned)
            bn->open = 0;
        /* every child of the branch drops its other parents */
        for (int i = 0; i < bn->nchildren; ++i) {
            mu_t4_node *c = &g->nodes[bn->children[i]];
            int16_t copy[MU_T4_LINKS];
            int nc = c->nparents;
            memcpy(copy, c->parents, sizeof copy);
            for (int k = 0; k < nc; ++k)
                if (copy[k] != b)
                    list_remove(c->parents, &c->nparents, copy[k]);
        }
        /* every other node drops children it shares with the branch */
        for (int i = 0; i < g->nnodes; ++i) {
            if (i == b)
                continue;
            mu_t4_node *o = &g->nodes[i];
            for (int k = 0; k < o->nchildren;) {
                int child = o->children[k];
                if (list_has(bn->children, bn->nchildren, child)) {
                    list_remove(o->children, &o->nchildren, child);
                    k = 0;
                } else {
                    ++k;
                }
            }
        }
    }
}

/* ---- JSON output for the movie invokes -------------------------------------------------------------------- */

typedef struct jbuf { char *s; size_t n, cap; } jbuf;

static void jput(jbuf *b, const char *fmt, ...)
{
    va_list ap;
    for (;;) {
        va_start(ap, fmt);
        int k = vsnprintf(b->s + b->n, b->cap - b->n, fmt, ap);
        va_end(ap);
        if (k < 0)
            return;
        if (b->n + (size_t)k < b->cap) {
            b->n += (size_t)k;
            return;
        }
        b->cap = (b->cap + (size_t)k) * 2 + 256;
        b->s = realloc(b->s, b->cap);
    }
}

/* A JSON string of client bytes (Latin-1 code points; the movie layer converts). */
static void jstr(jbuf *b, const char *s)
{
    jput(b, "\"");
    for (; *s; ++s) {
        unsigned char c = (unsigned char)*s;
        if (c == '"' || c == '\\')
            jput(b, "\\%c", c);
        else if (c == '\n')
            jput(b, "\\n");
        else if (c < 0x20)
            jput(b, "\\u%04x", c);
        else if (c < 0x80)
            jput(b, "%c", c);
        else
            jput(b, "\\u%04x", c);
    }
    jput(b, "\"");
}

static void invokef(const mu_t4_env *env, const char *name, const char *fmt, ...)
{
    char buf[512];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(buf, sizeof buf, fmt, ap);
    va_end(ap);
    if (env->invoke)
        env->invoke(env->user, name, buf);
}

/* Invoke 0x00aaf3ef(name, value): one GFx value; the host's argument list is [value]. */
static void invoke_value(const mu_t4_env *env, const char *name, const char *value)
{
    if (!env->invoke)
        return;
    jbuf b = {0};
    jput(&b, "[%s]", value);
    env->invoke(env->user, name, b.s);
    free(b.s);
}

/* ---- the window ----------------------------------------------------------------------------------------------- */

void mu_t4_window_init(mu_t4_window *w, const mu_t4_table *table)
{
    memset(w, 0, sizeof *w);
    w->table = table;
    w->cls = -1;
    w->pend_group = w->pend_index = -1;
    w->cur_group = -1;
    w->side_pending[0] = w->side_pending[1] = w->side_pending[2] = -1;
}

void mu_t4_window_set_side(mu_t4_window *w, const struct mu_t4_side_table *side) { w->side = side; }

static void window_reset(mu_t4_window *w)   /* 0x00c23e5f */
{
    w->cur_group = -1;
    w->side_ready = 0;                      /* +0xb0 deleted */
    for (int i = 0; i < w->ngroups; ++i)
        mu_t4_group_free(&w->groups[i]);
    free(w->groups);
    w->groups = NULL;
    w->ngroups = 0;
    free(w->skill8);
    w->skill8 = NULL;
    w->nskill8 = 0;
    for (int i = 0; i < w->ntabs; ++i)
        free(w->tabs[i].groups);
    free(w->tabs);
    w->tabs = NULL;
    w->ntabs = 0;
}

void mu_t4_window_free(mu_t4_window *w)
{
    window_reset(w);
}

void mu_t4_set_class(mu_t4_window *w, int32_t cls)
{
    w->cls = cls;
}

void mu_t4_set_points(mu_t4_window *w, const mu_t4_env *env, int32_t points)
{
    w->points = points;
    char text[512];
    const char *fmt = env->text ? env->text(env->user, 0x144d) : "";
    snprintf(text, sizeof text, fmt ? fmt : "", points);
    jbuf b = {0};
    jput(&b, "[");
    jstr(&b, text);
    jput(&b, "]");
    if (env->invoke)
        env->invoke(env->user, "SetRemainPoint", b.s);
    free(b.s);
}

static int group_pos(const mu_t4_window *w, int32_t id)
{
    for (int i = 0; i < w->ngroups; ++i)
        if (w->groups[i].id == id)
            return i;
    return -1;
}

static mu_t4_tab *tab_of(const mu_t4_window *w, int32_t key)
{
    for (int i = 0; i < w->ntabs; ++i)
        if (w->tabs[i].key == key)
            return &w->tabs[i];
    return NULL;
}

void mu_t4_build(mu_t4_window *w, const mu_t4_env *env)
{
    window_reset(w);
    w->cur_tab = 0;
    const mu_t4_tclass *c = mu_t4_table_class_of(w->table, w->cls);
    int ng = c ? c->ngroups : 0;
    w->groups = calloc((size_t)(ng ? ng : 1), sizeof *w->groups);
    w->tabs = calloc((size_t)(ng ? ng : 1), sizeof *w->tabs);
    for (int gi = 0; gi < ng; ++gi) {
        const mu_t4_tgroup *tg = &c->groups[gi];
        if (tg->key < 0)
            continue;
        mu_t4_group g;
        mu_t4_group_init(&g, tg, env);
        /* +0x90 insert: the class's groups have unique keys in key order */
        w->groups[w->ngroups] = g;
        mu_t4_group *gs = &w->groups[w->ngroups++];
        for (int i = 0; i < gs->nnodes; ++i) {
            int byte0 = 0, use = 0;
            if (env->skill_info)
                env->skill_info(env->user, gs->nodes[i].skill, &byte0, &use);
            if (use != 8)
                continue;
            int at = 0;
            while (at < w->nskill8 && w->skill8[at].skill < gs->nodes[i].skill)
                ++at;
            if (at < w->nskill8 && w->skill8[at].skill == gs->nodes[i].skill)
                continue;   /* map insert keeps the first */
            w->skill8 = realloc(w->skill8, sizeof *w->skill8 * (size_t)(w->nskill8 + 1));
            memmove(w->skill8 + at + 1, w->skill8 + at, sizeof *w->skill8 * (size_t)(w->nskill8 - at));
            w->skill8[at] = (mu_t4_skill_node){gs->nodes[i].skill, w->ngroups - 1, i};
            ++w->nskill8;
        }
        mu_t4_tab *tab = tab_of(w, gs->kind);
        if (!tab) {
            int at = 0;
            while (at < w->ntabs && w->tabs[at].key < gs->kind)
                ++at;
            memmove(w->tabs + at + 1, w->tabs + at, sizeof *w->tabs * (size_t)(w->ntabs - at));
            memset(w->tabs + at, 0, sizeof *w->tabs);
            w->tabs[at].key = gs->kind;
            w->tabs[at].groups = calloc((size_t)(ng ? ng : 1), sizeof(int32_t));
            ++w->ntabs;
            tab = &w->tabs[at];
        }
        tab->groups[tab->count++] = gs->id;                    /* 0x010a2320 */
    }
    if (env->invoke)
        env->invoke(env->user, "RequestSlotUIInfo", "[]");
    mu_t4_set_tab_info(w, env);
}

void mu_t4_set_tab_info(const mu_t4_window *w, const mu_t4_env *env)
{
    jbuf b = {0};
    jput(&b, "[");
    for (int i = 0; i < w->ntabs; ++i) {
        const mu_t4_tab *t = &w->tabs[i];
        jput(&b, "%s{\"TabIndex\":%d,\"GroupIndexList\":[", i ? "," : "", t->key);
        for (int k = 0; k < t->count; ++k)
            jput(&b, "%s%d", k ? "," : "", t->groups[k]);
        jput(&b, "]}");
    }
    jput(&b, "]");
    invoke_value(env, "SetTabInfo", b.s);
    free(b.s);
}

static int slot_bg(const mu_t4_group *g, const mu_t4_record *r)
{
    if (mu_t4_has_sibling(g, r->f[MU_T4_INDEX]))
        return 2;
    switch (r->f[MU_T4_TYPE]) {
    case 0: return 1;
    case 1: return 4;
    case 2: return 3;
    default: return 1;
    }
}

static int link_shown(const mu_t4_node *child, const mu_t4_record *r)   /* 0x00c2b9c8 */
{
    for (int i = 0; i < 5; ++i) {
        if (r->f[MU_T4_CHILD + i] < 0)
            continue;
        if (child->rec->f[MU_T4_INDEX] == r->f[MU_T4_CHILD + i])
            return r->f[MU_T4_SHOW + i] == 1;
    }
    return 0;
}

static void slots_json(const mu_t4_window *w, const mu_t4_group *g, int full, jbuf *b)
{
    (void)w;
    jput(b, "{\"GroupIndex\":%d", g->id);
    if (full)
        jput(b, ",\"UIGroup\":%d", g->kind);
    jput(b, ",\"SlotInfo\":[");
    for (int i = 0; i < g->nnodes; ++i) {
        const mu_t4_node *n = &g->nodes[i];
        const mu_t4_record *r = n->rec;
        jput(b, "%s{\"Index\":%d", i ? "," : "", r->f[MU_T4_INDEX]);
        if (full)
            jput(b, ",\"CurrentPoint\":%d", n->level);
        jput(b, ",\"MaxPoint\":%d,\"Type\":%d,\"SlotBG\":%d}", r->f[MU_T4_MAX], r->f[MU_T4_TYPE],
             full ? slot_bg(g, r) : 0);
    }
    jput(b, "]}");
}

void mu_t4_slots(const mu_t4_window *w, const mu_t4_env *env, int32_t group)
{
    int gp = group_pos(w, group);
    if (gp < 0)
        return;
    const mu_t4_group *g = &w->groups[gp];
    jbuf b = {0};
    jput(&b, "{\"GroupIndex\":%d,\"UIGroup\":%d,\"SlotInfo\":[", g->id, g->kind);
    for (int i = 0; i < g->nnodes; ++i) {
        const mu_t4_node *n = &g->nodes[i];
        const mu_t4_record *r = n->rec;
        jput(&b, "%s{\"Index\":%d,\"CurrentPoint\":%d,\"MaxPoint\":%d,\"Type\":%d,\"SlotBG\":%d}", i ? "," : "",
             r->f[MU_T4_INDEX], n->level, r->f[MU_T4_MAX], r->f[MU_T4_TYPE], slot_bg(g, r));
    }
    jput(&b, "],\"LinkInfo\":[");
    int nlinks = 0;
    for (int i = 0; i < g->nnodes; ++i) {
        const mu_t4_node *n = &g->nodes[i];
        for (int k = 0; k < n->nchildren; ++k) {
            const mu_t4_node *c = &g->nodes[n->children[k]];
            if (!link_shown(c, n->rec))
                continue;
            jput(&b, "%s{\"From\":%d,\"To\":%d,\"LinkState\":%d}", nlinks ? "," : "", n->index, c->index,
                 n->rec->f[MU_T4_TYPE] == 2 ? (MU_SKILL_MUTATION == 27 ? 3 : 4) : 2);
            ++nlinks;
        }
    }
    for (int k = nlinks; k < g->nnodes * 5; ++k)
        jput(&b, "%snull", k ? "," : "");
    jput(&b, "]}");
    invoke_value(env, "SetSkillSlots", b.s);
    invoke_value(env, "SetSkillSlotLinkInfo", b.s);
    free(b.s);
    (void)slots_json;
}

static void group_links_json(const mu_t4_group *g, const mu_t4_node *n, int32_t index, jbuf *b, int *count)
{
    /* parents: the first hidden link ends the loop */
    for (int i = 0; i < n->nparents; ++i) {
        const mu_t4_node *p = &g->nodes[n->parents[i]];
        if (!link_shown(n, p->rec))
            break;
        if (p->level >= p->rec->f[MU_T4_OPEN] && n->level > 0) {
            jput(b, "%s{\"From\":%d,\"To\":%d,\"LinkState\":%d}", *count ? "," : "", p->index, index,
                 n->rec->f[MU_T4_TYPE] == 2 ? 3 : 1);
            ++*count;
        }
    }
    for (int i = 0; i < n->nchildren; ++i) {
        const mu_t4_node *c = &g->nodes[n->children[i]];
        if (!link_shown(c, n->rec))
            break;
        if (!n->open) {
            if (c->level > 0) {
                jput(b, "%s{\"From\":%d,\"To\":%d,\"LinkState\":1}", *count ? "," : "", index, c->index);
                ++*count;
            }
        } else if (c->level >= c->rec->f[MU_T4_COST]) {
            jput(b, "%s{\"From\":%d,\"To\":%d,\"LinkState\":%d}", *count ? "," : "", index, c->index,
                 c->rec->f[MU_T4_TYPE] == 2 ? 3 : 1);
            ++*count;
        }
    }
}

void mu_t4_entry_links(const mu_t4_window *w, const mu_t4_env *env, int32_t index, int32_t group)
{
    int gp = group_pos(w, group);
    if (gp < 0)
        return;
    const mu_t4_group *g = &w->groups[gp];
    int pos = mu_t4_group_find(g, index);
    if (pos < 0)
        return;
    jbuf b = {0};
    int count = 0;
    jput(&b, "{\"GroupIndex\":%d,\"LinkInfo\":[", group);
    group_links_json(g, &g->nodes[pos], index, &b, &count);
    jput(&b, "]}");
    invoke_value(env, "SetSkillSlotLinkInfo", b.s);
    free(b.s);
}

void mu_t4_entry(mu_t4_window *w, const mu_t4_env *env, int32_t index, int32_t group, int32_t level, float value,
                 float next)
{
    int gp = group_pos(w, group);
    if (gp < 0)
        return;
    mu_t4_group *g = &w->groups[gp];
    mu_t4_set_level(g, env, index, level, value, next);
    if (w->cur_group >= 0 && w->groups[w->cur_group].id == group) {
        invokef(env, "SetSkillPoint", "[%d,%d]", index, level);
        int pos = mu_t4_group_find(g, index);
        if (pos >= 0 && !g->nodes[pos].open)
            invokef(env, "SetSkillSlotVisible", "[%d,false]", g->nodes[pos].index);
    }
    /* 0x00c262e8: the info popup shows this tree's tooltip -> it is rebuilt for the index (0x00c29007) */
    if (env->popup_shows_tree && env->popup_shows_tree(env->user) && env->event)
        env->event(env->user, "tooltip", index);
}

void mu_t4_refresh_group(const mu_t4_window *w, const mu_t4_env *env, int32_t group)
{
    int gp = group_pos(w, group);
    if (gp < 0)
        return;
    const mu_t4_group *g = &w->groups[gp];
    jbuf b = {0};
    jput(&b, "{\"GroupIndex\":%d,\"SlotInfo\":[", group);
    for (int i = 0; i < g->nnodes; ++i) {
        const mu_t4_record *r = g->nodes[i].rec;
        int bg;
        if (r->f[MU_T4_TYPE] == 1)
            bg = 4;
        else if (r->f[MU_T4_TYPE] == 2)
            bg = 3;
        else if ((w->side ? mu_t4_side_category(w->side, r->f[MU_T4_INDEX], group)
                          : env->side_category ? env->side_category(env->user, r->f[MU_T4_INDEX], group) : -1) == 1)
            bg = 2;
        else
            bg = 1;
        jput(&b, "%s{\"Index\":%d,\"MaxPoint\":%d,\"Type\":%d,\"SlotBG\":%d}", i ? "," : "", r->f[MU_T4_INDEX],
             r->f[MU_T4_MAX], r->f[MU_T4_TYPE], bg);
    }
    jput(&b, "],\"LinkInfo\":[");
    int nlinks = 0;
    for (int i = 0; i < g->nnodes; ++i) {
        const mu_t4_node *n = &g->nodes[i];
        for (int k = 0; k < n->nchildren; ++k) {
            const mu_t4_node *c = &g->nodes[n->children[k]];
            if (!link_shown(c, n->rec))
                continue;
            int state = mu_t4_has_sibling(g, c->index) ? 2 : n->rec->f[MU_T4_TYPE] == 2 ? 4 : 2;
            jput(&b, "%s{\"From\":%d,\"To\":%d,\"LinkState\":%d}", nlinks ? "," : "", n->index, c->index, state);
            ++nlinks;
        }
    }
    for (int k = nlinks; k < g->nnodes * 5; ++k)
        jput(&b, "%snull", k ? "," : "");
    jput(&b, "]}");
    invoke_value(env, "SetSkillSlots", b.s);
    invoke_value(env, "SetSkillSlotLinkInfo", b.s);
    free(b.s);
    /* each node again through the entry routines (their side effects run), then its point */
    for (int i = 0; i < w->groups[gp].nnodes; ++i) {
        const mu_t4_node *n = &w->groups[gp].nodes[i];
        int32_t index = n->rec->f[MU_T4_INDEX], level = n->level;
        float value = n->value, next = n->next;
        mu_t4_entry((mu_t4_window *)w, env, index, group, level, value, next);
        mu_t4_entry_links(w, env, index, group);
        invokef(env, "SetSkillPoint", "[%d,%d]", index, w->groups[gp].nodes[i].level);
    }
}

void mu_t4_refresh_all(mu_t4_window *w, const mu_t4_env *env)
{
    for (int i = 0; i < w->ngroups; ++i) {
        mu_t4_branch_cleanup(&w->groups[i]);
        if (w->cur_group >= 0 && w->groups[w->cur_group].id == w->groups[i].id)
            mu_t4_refresh_group(w, env, w->groups[i].id);
    }
}

void mu_t4_show_page(mu_t4_window *w, const mu_t4_env *env, int32_t page)
{
    mu_t4_tab *t = tab_of(w, w->cur_tab);
#if MU_SKILL_MUTATION == 25
    if (!t || page < 0 || page > t->count)
        return;
#else
    if (!t || page < 0 || page >= t->count)
        return;
#endif
    t->page = page;
    int32_t gid = t->groups[page];
    int gp = group_pos(w, gid);
    if (gp < 0)
        return;
    w->cur_group = gp;
    invokef(env, "SetCurrentPage", "[%d,%d]", t->key, page);
    mu_t4_slots(w, env, w->groups[gp].id);
    mu_t4_refresh_all(w, env);
}

void mu_t4_change_tab(mu_t4_window *w, const mu_t4_env *env, int32_t tab)
{
    mu_t4_tab *t = tab_of(w, tab);
    if (!t)
        return;
    w->cur_tab = tab;
    mu_t4_show_page(w, env, t->page);
}

void mu_t4_step_page(mu_t4_window *w, const mu_t4_env *env, int step)
{
    const mu_t4_tab *t = tab_of(w, w->cur_tab);
    mu_t4_show_page(w, env, (t ? t->page : 0) + step);
}

void mu_t4_slot_rect(mu_t4_window *w, int32_t index, float x, float y, float width, float height)
{
    for (int gi = 0; gi < w->ngroups; ++gi) {
        int pos = mu_t4_group_find(&w->groups[gi], index);
        if (pos < 0)
            continue;
        mu_t4_node *n = &w->groups[gi].nodes[pos];
        n->rect[0] = (int32_t)x;
        n->rect[1] = (int32_t)y;
        n->rect[2] = (int32_t)(x + width);
        n->rect[3] = (int32_t)(y + height);
    }
}

int mu_t4_branch_learned(const mu_t4_window *w, int32_t group, int32_t index)
{
    int gp = group_pos(w, group);
    if (gp < 0)
        return 0;
    const mu_t4_group *g = &w->groups[gp];
    int pos = mu_t4_group_find(g, index);
    if (pos < 0)
        return 0;   /* the client reads a null node here; the validator keeps indices present */
    const mu_t4_node *n = &g->nodes[pos];
    int found = 0;
    for (int i = 0; i < n->nparents; ++i)
        if (g->nodes[n->parents[i]].rec->f[MU_T4_TYPE] == 3 && n->level == 1)
            found = 1;
    return found;
}

static void enh_put(mu_t4_node *n, int32_t skill, int32_t value)
{
    int at = 0;
    while (at < n->nenh && n->enh_skill[at] < skill)
        ++at;
    if (at < n->nenh && n->enh_skill[at] == skill) {
        n->enh_value[at] = value;
        return;
    }
    if (n->nenh >= MU_T4_LINKS)
        return;
    memmove(n->enh_skill + at + 1, n->enh_skill + at, sizeof(int32_t) * (size_t)(n->nenh - at));
    memmove(n->enh_value + at + 1, n->enh_value + at, sizeof(int32_t) * (size_t)(n->nenh - at));
    n->enh_skill[at] = skill;
    n->enh_value[at] = value;
    ++n->nenh;
}

/* 0x00c2a28b(start, node): learned nodes (level >= f[18]) whose skill has use type 7 go into start's map, and the
 * walk continues through the children; a missing skill record stops the branch. */
static void skill8_walk(mu_t4_group *g, const mu_t4_env *env, mu_t4_node *start, int pos)
{
    mu_t4_node *n = &g->nodes[pos];
    if (n->level < n->rec->f[MU_T4_COST])
        return;
    int byte0 = 1, use = 0;
    if (env->skill_info)
        env->skill_info(env->user, n->skill, &byte0, &use);
    if (byte0)
        return;
    if (use == 7)
        enh_put(start, n->skill, (int32_t)n->value);
    for (int i = 0; i < n->nchildren; ++i)
        skill8_walk(g, env, start, n->children[i]);
}

void mu_t4_skill8_refresh(mu_t4_window *w, const mu_t4_env *env)
{
    for (int i = 0; i < w->nskill8; ++i) {
        mu_t4_group *g = &w->groups[w->skill8[i].group];
        mu_t4_node *n = &g->nodes[w->skill8[i].node];
        n->nenh = 0;
        skill8_walk(g, env, n, w->skill8[i].node);
    }
}

int mu_t4_enhancement(const mu_t4_window *w, int32_t skill, int32_t enh, int32_t *value)
{
    for (int i = 0; i < w->nskill8; ++i) {
        if (w->skill8[i].skill != skill)
            continue;
        const mu_t4_node *n = &w->groups[w->skill8[i].group].nodes[w->skill8[i].node];
        for (int k = 0; k < n->nenh; ++k)
            if (n->enh_skill[k] == enh) {
                *value = n->enh_value[k];
                return 1;
            }
    }
    return 0;
}

void mu_t4_message(const mu_t4_env *env, int kind)
{
    int32_t id = kind == 1 ? 0xcff : kind == 2 ? 0xcfe : kind == 3 ? 0x912 : -1;
    if (id < 0 || !env->msgbox)
        return;
    env->msgbox(env->user, env->text ? env->text(env->user, id) : "");
}

/* The branch popup's explanation: the GlobalText split at '#' (getline) and joined with "\n" while text remains. */
static void branch_explain(const char *src, char *out, size_t cap)
{
    size_t n = 0, len = strlen(src);
    const char *p = src;
    out[0] = 0;
    while (*p || p == src) {
        const char *e = strchr(p, '#');
        size_t k = e ? (size_t)(e - p) : strlen(p);
        if (n + k < cap) {
            memcpy(out + n, p, k);
            n += k;
            out[n] = 0;
        }
        if (n != len && n + 1 < cap) {
            out[n++] = '\n';
            out[n] = 0;
        }
        if (!e)
            break;
        p = e + 1;
    }
}

int mu_t4_click(mu_t4_window *w, const mu_t4_env *env, int32_t index)
{
    if (w->cur_group < 0)
        return 0;
    mu_t4_group *g = &w->groups[w->cur_group];
    int pos = mu_t4_group_find(g, index);
    if (pos < 0)
        return 0;
    mu_t4_node *n = &g->nodes[pos];
    const mu_t4_record *r = n->rec;
    if (r->f[MU_T4_TYPE] == 3) {
        w->nbranch = 0;                                       /* +0xf0 cleared */
        if (!n->avail) {
            mu_t4_message(env, 1);
            return 0;
        }
        jbuf b = {0};
        jput(&b, "[");
        for (int i = 0; i < n->nchildren; ++i) {
            const mu_t4_node *c = &g->nodes[n->children[i]];
            if (w->nbranch < MU_T4_LINKS)
                w->branch[w->nbranch++] = c->skill;
            int32_t gt = c->skill == 0x400 ? 0x15db : c->skill == 0x401 ? 0x15dc : c->skill == 0x402 ? 0x15dd : -1;
            char text[MU_T4_TEXT];
            branch_explain(gt >= 0 && env->text ? env->text(env->user, gt) : "", text, sizeof text);
            jput(&b, "%s{\"skillExplain\":", i ? "," : "");
            jstr(&b, text);
            jput(&b, ",\"skillGroup\":%d,\"skillIndex\":%d}", c->rec->f[MU_T4_GROUP], c->rec->f[MU_T4_INDEX]);
        }
        jput(&b, "]");
        w->branch_visible = 1;
        invokef(env, "VisibleSetBranchSkill", "[true]");
        invoke_value(env, "SetBranchSkillInfo", b.s);
        free(b.s);
        return 0;
    }
    if (n->level >= r->f[MU_T4_MAX]) {
        mu_t4_message(env, 2);
        return 0;
    }
#if MU_SKILL_MUTATION == 24
    if (w->points <= r->f[MU_T4_COST]) {
#else
    if (w->points < r->f[MU_T4_COST]) {
#endif
        mu_t4_message(env, 3);
        return 0;
    }
    if (!n->avail || !mu_t4_can_learn(g, env, index)) {
        mu_t4_message(env, 1);
        return 0;
    }
    w->pend_group = g->id;
    w->pend_index = index;
    char text[MU_T4_TEXT], cost[512];
    const char *fmt = env->text ? env->text(env->user, 0x143f) : "";
    snprintf(cost, sizeof cost, fmt ? fmt : "", r->f[MU_T4_COST]);
    snprintf(text, sizeof text, "%s\n%s", env->text ? env->text(env->user, 0x6eb) : "", cost);
    if (env->confirm)
        env->confirm(env->user, 0x73, text);
    return 1;
}

int mu_t4_confirm(mu_t4_window *w, int result, uint8_t *group, uint16_t *skill, uint16_t *index)
{
    int sent = 0;
    if (result == 0) {
        const mu_t4_record *r = mu_t4_table_get(w->table, w->cls, w->pend_group, w->pend_index);
        if (r && !r->hidden) {
            *group = (uint8_t)r->f[MU_T4_GROUP];
            *skill = (uint16_t)r->f[MU_T4_SKILL];
            *index = (uint16_t)r->f[MU_T4_INDEX];
            sent = 1;
        }
        w->pend_group = w->pend_index = -1;
    }
    return sent;
}

size_t mu_t4_request(uint8_t *out, size_t cap, uint8_t group, uint16_t skill, uint16_t index)
{
    if (cap < 9)
        return 0;
    out[0] = 0xc1;
    out[1] = 9;
    out[2] = 0x7e;
    out[3] = 1;
    out[4] = group;
    out[5] = (uint8_t)skill;
    out[6] = (uint8_t)(skill >> 8);
    out[7] = (uint8_t)index;
    out[8] = (uint8_t)(index >> 8);
    return 9;
}

static uint16_t rd16(const uint8_t *p) { return (uint16_t)(p[0] | p[1] << 8); }
static uint32_t rd32(const uint8_t *p) { return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24; }
static float rdf(const uint8_t *p) { uint32_t v = rd32(p); float f; memcpy(&f, &v, 4); return f; }

int mu_t4_receive(mu_t4_window *w, const mu_t4_env *env, const uint8_t *p, size_t size)
{
    if (size < 4)
        return 0;
    int sub = p[0] == 0xc1 ? p[3] : p[0] == 0xc2 && size > 4 ? p[4] : -1;
    switch (sub) {
    case 2: {                                                   /* 0x0127f539 */
        if (size < 0xb)
            return 0;
        mu_t4_set_points(w, env, rd16(p + 5));
        mu_t4_build(w, env);
        uint32_t count = rd32(p + 7);
        for (uint32_t i = 0; i < count && 0xb + 12 * (size_t)i + 12 <= size; ++i) {
            const uint8_t *e = p + 0xb + 12 * i;
            mu_t4_entry(w, env, rd16(e + 1), e[0], e[3], rdf(e + 4), rdf(e + 8));
            mu_t4_entry_links(w, env, rd16(e + 1), e[0]);
        }
        mu_t4_show_page(w, env, 0);
        mu_t4_skill8_refresh(w, env);
        return 1;
    }
    case 1:                                                     /* 0x0125051f */
        if (size < 5)
            return 0;
        if (p[4] == 1 && size >= 0x13) {
            mu_t4_set_points(w, env, rd16(p + 5));
            mu_t4_entry(w, env, rd16(p + 9), p[7], p[8], rdf(p + 0xb), rdf(p + 0xf));
            mu_t4_entry_links(w, env, rd16(p + 9), p[7]);
            mu_t4_skill8_refresh(w, env);
            mu_t4_side_refresh(w, env);                         /* 0x00c2aa33 (once 7E 06 created +0xb0) */
            if (mu_t4_branch_learned(w, p[7], rd16(p + 9)))
                mu_t4_refresh_all(w, env);
        } else if (p[4] == 4) {
            mu_t4_message(env, 1);
        } else if (p[4] == 7) {
            mu_t4_message(env, MU_SKILL_MUTATION == 26 ? 1 : 3);
        }
        return 1;
    case 3:                                                     /* 0x0127f679 */
        if (size < 6)
            return 0;
        mu_t4_set_points(w, env, rd16(p + 4));
        return 1;
    case 6: {                                                   /* 0x012225fe: the side options */
        if (size < 9)
            return 0;
        mu_t4_side_create(w, env);
        uint32_t count = rd32(p + 5);
        for (uint32_t i = 0; i < count && 9 + 11 * (size_t)i + 11 <= size; ++i) {
            const uint8_t *e = p + 9 + 11 * i;
            mu_t4_side_set(w, e[0], e[1], e[2], rdf(e + 3), rdf(e + 7));
        }
        mu_t4_side_refresh(w, env);
        return 1;
    }
    case 5:                                                     /* 0x012226ca: a side option learned */
        if (size < 5)
            return 0;
        if (p[4] == 1 && size >= 0x12) {
            mu_t4_side_set(w, p[5], p[9], p[8], rdf(p + 0xa), rdf(p + 0xe));
            mu_t4_set_points(w, env, rd16(p + 6));
            mu_t4_side_refresh(w, env);
            /* the side popup's tooltip again when it shows this tree (0x00c29a29) and the stats (0x00a00fb7) */
            if (env->event)
                env->event(env->user, "stats", 0);
        } else if (p[4] == 4) {
            mu_t4_message(env, 1);
        } else if (p[4] == 7) {
            mu_t4_message(env, 3);
        }
        return 1;
    default:
        return 0;
    }
}

/* The runtime state as JSON (validator and debugging): groups with their nodes and lists, tabs, fields. */
size_t mu_t4_dump(const mu_t4_window *w, char *out, size_t cap)
{
    jbuf b = {0};
    jput(&b, "{\"cls\":%d,\"points\":%d,\"pend\":[%d,%d],\"tab\":%d,\"cur\":%d,\"groups\":[", w->cls, w->points,
         w->pend_group, w->pend_index, w->cur_tab, w->cur_group >= 0 ? w->groups[w->cur_group].id : -1);
    for (int gi = 0; gi < w->ngroups; ++gi) {
        const mu_t4_group *g = &w->groups[gi];
        jput(&b, "%s{\"id\":%d,\"rows\":%d,\"kind\":%d,\"roots\":[", gi ? "," : "", g->id, g->rows, g->kind);
        for (int i = 0; i < g->nroots; ++i)
            jput(&b, "%s%d", i ? "," : "", g->nodes[g->roots[i]].index);
        jput(&b, "],\"nodes\":[");
        for (int i = 0; i < g->nnodes; ++i) {
            const mu_t4_node *n = &g->nodes[i];
            jput(&b, "%s[%d,%d,%d,%d,%.17g,%.17g,%d,%d,[", i ? "," : "", n->index, n->leaf, n->skill, n->level,
                 (double)n->value, (double)n->next, n->avail, n->open);
            for (int k = 0; k < n->nparents; ++k)
                jput(&b, "%s%d", k ? "," : "", g->nodes[n->parents[k]].index);
            jput(&b, "],[");
            for (int k = 0; k < n->nchildren; ++k)
                jput(&b, "%s%d", k ? "," : "", g->nodes[n->children[k]].index);
            jput(&b, "],[");
            for (int k = 0; k < n->nenh; ++k)
                jput(&b, "%s[%d,%d]", k ? "," : "", n->enh_skill[k], n->enh_value[k]);
            jput(&b, "]]");
        }
        jput(&b, "]}");
    }
    jput(&b, "],\"tabs\":[");
    for (int i = 0; i < w->ntabs; ++i) {
        const mu_t4_tab *t = &w->tabs[i];
        jput(&b, "%s[%d,%d,%d,[", i ? "," : "", t->key, t->page, t->count);
        for (int k = 0; k < t->count; ++k)
            jput(&b, "%s%d", k ? "," : "", t->groups[k]);
        jput(&b, "]]");
    }
    jput(&b, "],\"skill8\":[");
    for (int i = 0; i < w->nskill8; ++i)
        jput(&b, "%s[%d,%d]", i ? "," : "", w->skill8[i].skill, w->groups[w->skill8[i].group].nodes[w->skill8[i].node].index);
    jput(&b, "],\"branch\":[");
    for (int i = 0; i < w->nbranch; ++i)
        jput(&b, "%s%d", i ? "," : "", w->branch[i]);
    jput(&b, "],\"branch_visible\":%d,\"side\":", w->branch_visible);
    if (!w->side_ready) {
        jput(&b, "null}");
    } else {
        jput(&b, "{\"entries\":[");
        for (int i = 0; i < MU_T4_SIDE; ++i) {
            const mu_t4_side_entry *e = &w->side_entry[i];
            jput(&b, "%s[%d,%d,%d,%.17g,%.17g,%d,%d,%d]", i ? "," : "", e->category, e->slot, e->level, (double)e->value,
                 (double)e->next, e->locked, e->state, e->stage);
        }
        jput(&b, "],\"points\":[");
        for (int i = 0; i < w->nside_points; ++i)
            jput(&b, "%s[%d,%d]", i ? "," : "", w->side_points[i][0], w->side_points[i][1]);
        jput(&b, "]}}");
    }
    size_t n = b.n;
    if (out && cap) {
        size_t k = n < cap - 1 ? n : cap - 1;
        memcpy(out, b.s, k);
        out[k] = 0;
    }
    free(b.s);
    return n;
}
