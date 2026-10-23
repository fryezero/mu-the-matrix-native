/* The fourth tree's side options (NATIVE-SKILL-003); see tree4.h. */
#include "tree4.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../hud/tooltip_html.h"

#ifndef MU_SKILL_MUTATION
#define MU_SKILL_MUTATION 0
#endif

#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wformat-nonliteral"
static void fmt_s(char *b, size_t n, const char *f, const char *s) { snprintf(b, n, f, s); }
static void fmt_si(char *b, size_t n, const char *f, const char *s, int a) { snprintf(b, n, f, s, a); }
static void fmt_ii(char *b, size_t n, const char *f, int a, int c) { snprintf(b, n, f, a, c); }
static void fmt_0(char *b, size_t n, const char *f) { snprintf(b, n, f, 0); }
#pragma clang diagnostic pop

static const char *gt(const mu_t4_env *env, int32_t id)
{
    const char *s = env->text ? env->text(env->user, id) : "";
    return s ? s : "";
}

/* ---- the table: 4thTreeSideOption ---------------------------------------------------------------------------- */

void mu_t4_side_table_init(mu_t4_side_table *t) { memset(t, 0, sizeof *t); }

void mu_t4_side_table_free(mu_t4_side_table *t)
{
    free(t->records);
    free(t->pairs);
    memset(t, 0, sizeof *t);
}

void mu_t4_side_table_record(mu_t4_side_table *t, const int32_t f[22])
{
    t->records = realloc(t->records, sizeof *t->records * (size_t)(t->nrecords + 1));
    memcpy(t->records[t->nrecords++].f, f, sizeof t->records->f);
}

void mu_t4_side_table_pair(mu_t4_side_table *t, int32_t category, int32_t index, int32_t group)
{
    t->pairs = realloc(t->pairs, sizeof *t->pairs * (size_t)(t->npairs + 1));
    t->pairs[t->npairs++] = (mu_t4_side_pair){category, index, group};
}

/* The class's records in file order (map +0x3c, vector). */
static int class_records(const mu_t4_side_table *t, int32_t cls, const mu_t4_side_record **out, int max)
{
    int n = 0;
    for (int i = 0; t && i < t->nrecords && n < max; ++i)
        if (t->records[i].f[0] == cls)
            out[n++] = &t->records[i];
    return n;
}

/* The categories of +0x44 in key order; each one's pairs in order. */
static int categories(const mu_t4_side_table *t, int32_t *keys, int max)
{
    int n = 0;
    for (int i = 0; t && i < t->npairs; ++i) {
        int seen = 0;
        for (int k = 0; k < n; ++k)
            if (keys[k] == t->pairs[i].category)
                seen = 1;
        if (!seen && n < max)
            keys[n++] = t->pairs[i].category;
    }
    for (int a = 1; a < n; ++a)
        for (int b = a; b > 0 && keys[b - 1] > keys[b]; --b) {
            int32_t x = keys[b];
            keys[b] = keys[b - 1];
            keys[b - 1] = x;
        }
    return n;
}

int mu_t4_side_category(const mu_t4_side_table *t, int32_t index, int32_t group)    /* 0x010b6f79 */
{
    int32_t keys[64];
    int n = categories(t, keys, 64);
    for (int k = 0; k < n; ++k)
        for (int i = 0; i < t->npairs; ++i)
            if (t->pairs[i].category == keys[k] && t->pairs[i].index == index && t->pairs[i].group == group)
                return keys[k];
    return -1;
}

/* ---- the window's side state (handler +0xb0, ctor 0x0109ca0a) ---------------------------------------------- */

void mu_t4_side_index(const mu_t4_window *w, const mu_t4_env *env)                  /* 0x00c2436e */
{
    int32_t keys[64];
    int n = categories(w->side, keys, 64);
    size_t cap = 256, len = 0;
    char *s = malloc(cap);
    if (!s)
        return;
    len = (size_t)snprintf(s, cap, "[[");
    /* 0x010b6f25(i): the category whose key is i (positions 0..count-1); an absent key reads the default */
    for (int i = 0; i < n; ++i) {
        char item[64];
        int first = 1;
        if (len + 8 >= cap)
            s = realloc(s, cap *= 2);
        len += (size_t)snprintf(s + len, cap - len, "%s[", i ? "," : "");
        for (int k = 0; w->side && k < w->side->npairs; ++k) {
            const mu_t4_side_pair *p = &w->side->pairs[k];
            if (p->category != i)
                continue;
            int m = snprintf(item, sizeof item, "%s{\"SlotNumber\":%d,\"SkillPage\":%d}", first ? "" : ",", p->index,
                             p->group);
            first = 0;
            while (len + (size_t)m + 8 >= cap)
                s = realloc(s, cap *= 2);
            memcpy(s + len, item, (size_t)m + 1);
            len += (size_t)m;
        }
        len += (size_t)snprintf(s + len, cap - len, "]");
    }
    if (len + 4 >= cap)
        s = realloc(s, cap + 8);
    snprintf(s + len, 4, "]]");
    if (env->invoke)
        env->invoke(env->user, "SetSideOptionIndex", s);
    free(s);
}

static void side_reset(mu_t4_window *w)
{
    for (int i = 0; i < MU_T4_SIDE; ++i) {
        mu_t4_side_entry *e = &w->side_entry[i];
        memset(e, 0, sizeof *e);
        e->category = (uint8_t)(i >> 2);
        e->slot = (uint8_t)(i % 4);
        e->state = 1;
        e->stage = 1;
    }
    w->nside_points = 0;
}

/* 0x00c2a4bc: each category's points = the levels of its slots (type 2 excluded) -> +0x10 map. */
static void side_points(mu_t4_window *w)
{
    int32_t keys[64];
    int n = categories(w->side, keys, 64);
    for (int i = 0; i < n; ++i) {
        int32_t sum = 0;
        for (int k = 0; k < w->side->npairs; ++k) {
            const mu_t4_side_pair *p = &w->side->pairs[k];
            if (p->category != i)
                continue;
            int gp = -1;
            for (int g = 0; g < w->ngroups; ++g)
                if (w->groups[g].id == p->group)
                    gp = g;
            if (gp < 0)
                continue;
            int at = mu_t4_group_find(&w->groups[gp], p->index);
            if (at < 0)
                continue;
            const mu_t4_node *nd = &w->groups[gp].nodes[at];
            if (nd->rec->f[MU_T4_TYPE] == 2)
                continue;
            sum += nd->level;
        }
        int found = 0;
        for (int k = 0; k < w->nside_points; ++k)
            if (w->side_points[k][0] == i) {
                w->side_points[k][1] = sum;
                found = 1;
            }
        if (!found && w->nside_points < 64) {
            w->side_points[w->nside_points][0] = i;
            w->side_points[w->nside_points][1] = sum;
            ++w->nside_points;
        }
    }
}

static int32_t points_of(const mu_t4_window *w, int32_t category)                 /* 0x0109cdc6 */
{
    for (int k = 0; k < w->nside_points; ++k)
        if (w->side_points[k][0] == category)
            return w->side_points[k][1];
    return 0;
}

/* 0x0096fe90(out, text, rgba (ABGR), bold, line break), as reconstructed/quest/quest_text.c. */
static void html_rgba(char *out, size_t cap, const char *text, uint32_t color, int bold)
{
    out[0] = 0;
    if (!text || !*text || !strcmp(text, "\n"))
        return;
    char esc[2048];
    size_t n = 0;
    for (const char *p = text; *p && n + 5 < sizeof esc; ++p) {
        if (*p == '<') {
            memcpy(esc + n, "&lt;", 4);
            n += 4;
        } else {
            esc[n++] = *p;
        }
    }
    esc[n] = 0;
    uint32_t rgb = ((color & 0xff0000u) >> 16) | (color & 0xff00u) | ((color & 0xffu) << 16);
    if (bold == 1)
        snprintf(out, cap, "<font color='#%06x'><b>%s</b></font><BR>", rgb, esc);   /* line break 1 */
    else
        snprintf(out, cap, "<font color='#%06x'>%s</font><BR>", rgb, esc);
}

static void jstr(char **s, size_t *n, size_t *cap, const char *text)
{
    for (const unsigned char *p = (const unsigned char *)text;; ++p) {
        char tmp[8];
        size_t k;
        if (!*p)
            tmp[0] = '"', k = 1;
        else if (*p == '"' || *p == '\\')
            tmp[0] = '\\', tmp[1] = (char)*p, k = 2;
        else if (*p == '\n')
            tmp[0] = '\\', tmp[1] = 'n', k = 2;
        else if (*p < 0x20 || *p >= 0x80)
            k = (size_t)snprintf(tmp, sizeof tmp, "\\u%04x", *p);
        else
            tmp[0] = (char)*p, k = 1;
        while (*n + k + 64 >= *cap)
            *s = realloc(*s, *cap *= 2);
        memcpy(*s + *n, tmp, k);
        *n += k;
        (*s)[*n] = 0;
        if (!*p)
            break;
    }
}

void mu_t4_side_refresh(mu_t4_window *w, const mu_t4_env *env)                     /* 0x00c2aa33 */
{
    if (!w->side_ready)
        return;
    side_points(w);
    const mu_t4_side_record *recs[64];
    int nrec = class_records(w->side, w->cls, recs, 64);
    size_t cap = 1024, len = 0;
    char *s = malloc(cap);
    if (!s)
        return;
    len = (size_t)snprintf(s, cap, "[[");
    int written = 0;
    for (int i = 0; i < nrec; ++i) {
        const mu_t4_side_record *r = recs[i];
        if (i >= MU_T4_SIDE + 1)
            break;
        mu_t4_side_entry *e = i < MU_T4_SIDE ? &w->side_entry[i] : NULL;   /* 0x0109cc42 */
        if (!e)
            continue;
        const char *name = "";
        if (env->skill_name)
            name = env->skill_name(env->user, r->f[3]);
        int32_t pts = points_of(w, e->category);
        int lock = 0, stage = 0;
        if (pts < r->f[4]) {
            lock = 2;
            e->state = 1;
            e->locked = 1;
        } else if (pts < r->f[7] + (MU_SKILL_MUTATION == 29)) {
            if (e->level >= r->f[6])
                lock = 2, e->locked = 1;
            else
                lock = 1, e->locked = 0;
            e->state = 2;
        } else if (pts < r->f[10]) {
            if (e->level >= r->f[12])
                lock = 3, e->locked = 1;
            else if (e->level >= r->f[9])
                lock = 2, e->locked = 1;
            else
                lock = 1, e->locked = 0;
            e->state = 3;
        } else {
            lock = 1;
            e->state = 4;
            e->locked = 0;
            if (e->level >= r->f[12])
                lock = 3, e->locked = 1;
        }
        if (e->level > r->f[6]) {
            if (e->level > r->f[9])
                stage = 3, e->stage = 4;
            else if (e->level >= r->f[12])
                stage = 4, e->stage = 4;
            else
                stage = 2, e->stage = 3;
        } else if (pts >= r->f[4]) {
            stage = 1, e->stage = 2;
        } else {
            stage = 0, e->stage = 1;
        }
        char head[0x100], line[0x800], text[0x1000], tmp[0x100];
        text[0] = 0;
        head[0] = 0;
        if (e->category == 0) {
            if (lock == 2)
                fmt_s(head, sizeof head, gt(env, 0x1494), name);
            else
                fmt_si(head, sizeof head, gt(env, 0x1495), name, stage);
            mu_tooltip_html_line(line, sizeof line, head, 3, 0);
        } else if (e->category == 1) {
            if (lock == 2)
                fmt_s(head, sizeof head, gt(env, 0x1497), name);
            else
                fmt_si(head, sizeof head, gt(env, 0x1498), name, stage);
            html_rgba(line, sizeof line, head, 0xffee9ae0u, 1);
        } else {
            line[0] = 0;
        }
        strncat(text, line, sizeof text - strlen(text) - 1);
        switch (stage) {
        case 0: case 1: case 2: {
            static const int field[3] = {4, 7, 10};
            fmt_0(tmp, sizeof tmp, gt(env, 0x1496));
            strncat(text, tmp, sizeof text - strlen(text) - 1);
            strncat(text, "\n", sizeof text - strlen(text) - 1);
            fmt_ii(tmp, sizeof tmp, gt(env, 0x149a), r->f[field[stage]], stage + 1);
            strncat(text, tmp, sizeof text - strlen(text) - 1);
            strncat(text, "\n", sizeof text - strlen(text) - 1);
            break;
        }
        case 3: case 4:
            fmt_0(tmp, sizeof tmp, gt(env, 0x149b));
            strncat(text, tmp, sizeof text - strlen(text) - 1);
            strncat(text, "\n", sizeof text - strlen(text) - 1);
            break;
        }
        while (len + 128 >= cap)
            s = realloc(s, cap *= 2);
        len += (size_t)snprintf(s + len, cap - len, "%s{\"tooltipText\":\"", written++ ? "," : "");
        jstr(&s, &len, &cap, text);
        while (len + 128 >= cap)
            s = realloc(s, cap *= 2);
        len += (size_t)snprintf(s + len, cap - len, ",\"skillPoint\":%d,\"lockState\":%d,\"bgState\":%d}", e->level,
                                lock, e->category == 1 ? 2 : 1);
    }
    for (int i = written; i < nrec; ++i) {
        while (len + 16 >= cap)
            s = realloc(s, cap *= 2);
        len += (size_t)snprintf(s + len, cap - len, "%snull", i ? "," : "");
    }
    while (len + 4 >= cap)
        s = realloc(s, cap *= 2);
    snprintf(s + len, cap - len, "]]");
    if (env->invoke)
        env->invoke(env->user, "CreateSideOption", s);
    free(s);
}

void mu_t4_side_create(mu_t4_window *w, const mu_t4_env *env)                       /* 0x00c242b6 */
{
    side_reset(w);
    w->side_ready = 1;
    mu_t4_side_refresh(w, env);
}

void mu_t4_side_set(mu_t4_window *w, int a, int b, int level, float value, float next)   /* 0x00c2a9cd */
{
    int i = a * 4 + b;
    if (!w->side_ready || i < 0 || i >= MU_T4_SIDE)
        return;      /* the client's index check admits the vector's size: one past the eight entries */
    mu_t4_side_entry *e = &w->side_entry[i];
    memset(e, 0, sizeof *e);
    e->category = (uint8_t)a;
    e->slot = (uint8_t)b;
    e->level = (uint8_t)level;
    e->value = value;
    e->next = next;
    e->state = 1;
    e->stage = 1;
}

/* ---- the side tooltip (OnBtnOverSideOption 0x00c29a29) -------------------------------------------------------- */

#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wformat-nonliteral"
static void fmt_i(char *b, size_t n, const char *f, int a) { snprintf(b, n, f, a); }
static void fmt_d(char *b, size_t n, const char *f, double a) { snprintf(b, n, f, a); }
#pragma clang diagnostic pop

int mu_t4_side_tooltip(mu_t4_window *w, const mu_skill_tip_env *tenv, const mu_t4_env *env, const mu_t4_tip *tips,
                       int ntips, int32_t index, mu_skill_tip *out, uint8_t header[MU_SKILL_TIP_LINES],
                       int32_t pos[2])
{
    memset(out, 0, sizeof *out);
    if (header)
        memset(header, 0, MU_SKILL_TIP_LINES);
    if (!w->side_ready)
        return 0;
    const mu_t4_side_record *recs[64];
    int nrec = class_records(w->side, w->cls, recs, 64);
    if (index < 0 || index >= nrec || index >= MU_T4_SIDE)
        return 0;
    const mu_t4_side_record *r = recs[index];
    mu_t4_side_entry *e = &w->side_entry[index];
    char buf[0x200];
    fmt_i(buf, sizeof buf, "[%d]", e->category);
    if (env->invoke)
        env->invoke(env->user, "SelectSideOptionCategory", buf);
    const mu_skill_record *sr = mu_skill_record_of(tenv->skills, r->f[3]);
    mu_skill_tip_set(out, 0, NULL, 3, -1);
    mu_skill_format(buf, sizeof buf, "%s", 's', 0, 0.0, sr->name);
    mu_skill_tip_set(out, 0, buf, -1, 1);
    int line = 1;
    static const int maxfield[5] = {0, 6, 6, 9, 12};
    if (e->state >= 1 && e->state <= 4) {
        fmt_ii(buf, sizeof buf, gt(env, 0x1428), e->level, r->f[maxfield[e->state]]);
        mu_skill_tip_set(out, line, buf, -1, -1);
    }
    ++line;
    const mu_t4_tip *tip = mu_t4_tip_of(tips, ntips, r->f[3]);
    mu_t4_tip none = {0};
    if (!tip) {
        none.kind = -1;
        tip = &none;
    }
    buf[0] = 0;
    if (!tip->fixed) {
        float v = e->level == 0 ? (tenv->formula ? tenv->formula(tenv->user, 3, r->f[15], r->f[5]) : 0.0f) : e->value;
        if (tip->kind == -1)
            mu_skill_format(buf, sizeof buf, tip->desc, 0, 0, 0.0, NULL);
        else if (tip->kind == 0)
            fmt_i(buf, sizeof buf, tip->desc, (int)v);
        else if (tip->kind == 1)
            fmt_d(buf, sizeof buf, tip->desc, (double)v);
    }
    line = mu_skill_tip_put(tenv, out, buf, line, 0);
    if (tip->show_next && e->level > 0 && e->level < r->f[12]) {
        mu_skill_format(buf, sizeof buf, gt(env, 0xd00), 0, 0, 0.0, NULL);
        line = mu_skill_tip_put(tenv, out, buf, line, 4);
        if (header && line >= 0 && line < MU_SKILL_TIP_LINES)
            header[line] = 1;
        float v = e->next;
        if (tip->kind == -1)
            mu_skill_format(buf, sizeof buf, tip->next, 0, 0, 0.0, NULL);
        else if (tip->kind == 0)
            fmt_i(buf, sizeof buf, tip->next, (int)v);
        else if (tip->kind == 1)
            fmt_d(buf, sizeof buf, tip->next, (double)v);
        line = mu_skill_tip_put(tenv, out, buf, line, 0);
    }
    mu_skill_format(buf, sizeof buf, gt(env, 0x1490), 0, 0, 0.0, NULL);
    line = mu_skill_tip_put(tenv, out, buf, line, 1);
    int32_t need = r->f[10], top = r->f[12];
    switch (e->state) {
    case 1: top = r->f[6]; need = r->f[4]; break;
    case 2: top = r->f[9]; need = r->f[7]; break;
    case 3: case 4: top = r->f[12]; need = r->f[10]; break;
    default: break;
    }
    int32_t pts = points_of(w, e->category);
    if (e->state == 4) {
        mu_skill_format(buf, sizeof buf, gt(env, 0x149b), 0, 0, 0.0, NULL);
        line = mu_skill_tip_put(tenv, out, buf, line, 0);
    } else {
        if (e->category == 0)
            fmt_i(buf, sizeof buf, gt(env, 0x148e), need - pts);
        else if (e->category == 1)
            fmt_i(buf, sizeof buf, gt(env, 0x148f), need - pts);
        line = mu_skill_tip_put(tenv, out, buf, line, 2);
        fmt_ii(buf, sizeof buf, gt(env, 0x1491), e->state, top);
        mu_skill_tip_set(out, line, buf, -1, -1);
        ++line;
    }
    out->count = line;
    if (pos) {
        pos[0] = (int32_t)w->side_pos[index][0];
        pos[1] = (int32_t)w->side_pos[index][1];
    }
    return line;
}

/* RequestSideOptionUIPos(index, x, y) 0x00c2b4b3 / RequestSideOptionUISize(w, h) 0x00c2b580. */
void mu_t4_side_rect(mu_t4_window *w, int32_t index, float x, float y)
{
    if (index >= 0 && index < MU_T4_SIDE) {
        w->side_pos[index][0] = x;
        w->side_pos[index][1] = y;
    }
}

void mu_t4_side_size(mu_t4_window *w, float width, float height)
{
    w->side_size[0] = width;
    w->side_size[1] = height;
}

/* ---- OnBtnClickSideOption 0x00c2a5ad and the confirm box 0x79 ------------------------------------------------- */

void mu_t4_message(const mu_t4_env *env, int kind);

int mu_t4_side_click(mu_t4_window *w, const mu_t4_env *env, int32_t index)
{
    if (!w->side_ready)
        return 0;
    const mu_t4_side_record *recs[64];
    int nrec = class_records(w->side, w->cls, recs, 64);
    if (index < 0 || index >= MU_T4_SIDE)
        return 0;
    mu_t4_side_record zero = {{0}};
    const mu_t4_side_record *r = index < nrec ? recs[index] : &zero;
    mu_t4_side_entry *e = &w->side_entry[index];
    if (e->locked) {
        mu_t4_message(env, 2);
        return 0;
    }
    if (e->state == 1) {
        mu_t4_message(env, 1);
        return 0;
    }
    int32_t top = 0, cost = 0;
    switch (e->state) {
    case 2: top = r->f[6]; cost = r->f[5]; break;
    case 3: top = r->f[9]; cost = r->f[8]; break;
    case 4: top = r->f[12]; cost = r->f[11]; break;
    default: break;
    }
    if (w->points < cost) {
        mu_t4_message(env, 3);
        return 0;
    }
    char buf[0x100];
    if (r->f[3] == 0x472 || r->f[3] == 0x477 || r->f[3] == 0x4d9 || r->f[3] == 0x4da) {
        int ex = r->f[3] >= 0x4d9;
        snprintf(buf, sizeof buf, "[%d,%d,%d]", e->level, w->points, top);
        if (env->invoke) {
            env->invoke(env->user, "SetCurrentSideOptionSkillPoint", buf);
            env->invoke(env->user, ex ? "VisibleStatPointEx" : "VisibleStatPoint", "[true]");
        }
        w->side_pending[0] = e->category;
        w->side_pending[1] = e->slot;
        w->side_pending[2] = e->level;
        if (env->event)
            env->event(env->user, "statpanel", r->f[3]);     /* 0x00c26ed3(0, 0, 0, 0, 0): not reconstructed */
        return 0;
    }
    w->side_pending[0] = e->category;
    w->side_pending[1] = e->slot;
    w->side_pending[2] = e->level;
    char text[0x400], cost_line[0x100];
    int32_t shown = e->state == 2 ? r->f[5] : e->state == 3 ? r->f[8] : e->state == 4 ? r->f[11] : 0;
    cost_line[0] = 0;
    if (e->state >= 2 && e->state <= 4)
        fmt_i(cost_line, sizeof cost_line, gt(env, 0x143f), shown);
    snprintf(text, sizeof text, "%s\n%s", gt(env, 0x6eb), cost_line);
    if (env->confirm)
        env->confirm(env->user, 0x79, text);
    return 1;
}

int mu_t4_side_confirm(mu_t4_window *w, int result, uint8_t *category, uint8_t *slot, uint8_t *level)
{
    int sent = 0;
    if (result == 0 && w->side_pending[0] != -1 && w->side_pending[1] != -1) {
        *category = (uint8_t)w->side_pending[0];
        *slot = (uint8_t)w->side_pending[1];
        *level = (uint8_t)(w->side_pending[2] + 1);
        sent = 1;
    }
    if (result == 0)
        w->side_pending[0] = w->side_pending[1] = w->side_pending[2] = -1;
    return sent;
}

size_t mu_t4_side_request(uint8_t *out, size_t cap, uint8_t category, uint8_t slot, uint8_t level)
{
    if (cap < 7)
        return 0;
    out[0] = 0xc1;
    out[1] = 7;
    out[2] = 0x7e;
    out[3] = 5;
    out[4] = category;
    out[5] = slot;
    out[6] = level;
    return 7;
}
