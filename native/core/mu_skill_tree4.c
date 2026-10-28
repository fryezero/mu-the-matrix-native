/* The fourth skill tree in the native client (NATIVE-SKILL-003); see mu_skill_tree4.h. */
#include "mu_skill_tree4.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "mu_skill.h"
#include "../../reconstructed/hud/tooltip_html.h"

#include "mu_skill_tree4_internal.h"

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

static const char *skill_name(void *u, int32_t skill)
{
    mu_skill_tree4 *t = u;
    const mu_skill_record *r = t->book ? mu_skill_book_record(t->book, skill) : NULL;
    return r ? r->name : "";
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

static int hexv(char c)
{
    return c >= '0' && c <= '9' ? c - '0' : c >= 'a' && c <= 'f' ? c - 'a' + 10 : c >= 'A' && c <= 'F' ? c - 'A' + 10 : -1;
}

/* scripts/live_lang_to_plain.py's escape(): \\ \t \n \r \xNN. */
static void unescape(char *out, size_t cap, const char *s, size_t n)
{
    size_t o = 0;
    for (size_t i = 0; i < n && o + 1 < cap; ++i) {
        if (s[i] == '\\' && i + 1 < n) {
            char c = s[++i];
            if (c == 'x' && i + 2 < n + 1 && hexv(s[i + 1]) >= 0 && hexv(s[i + 2]) >= 0) {
                out[o++] = (char)(hexv(s[i + 1]) * 16 + hexv(s[i + 2]));
                i += 2;
            } else {
                out[o++] = c == 't' ? '\t' : c == 'n' ? '\n' : c == 'r' ? '\r' : c;
            }
        } else {
            out[o++] = s[i];
        }
    }
    out[o] = 0;
}

static void load_extras(mu_skill_tree4 *t, const char *dir)
{
    char path[1024], line[2048];
    snprintf(path, sizeof path, "%s/tree4_tips.tsv", dir ? dir : ".");
    FILE *f = fopen(path, "r");
    if (f) {
        while (fgets(line, sizeof line, f)) {
            if (line[0] == '#' || line[0] == '\n')
                continue;
            line[strcspn(line, "\r\n")] = 0;
            char *field[6];
            int n = 0;
            for (char *p = line; n < 6; ++n) {
                field[n] = p;
                char *tab = strchr(p, '\t');
                if (!tab) {
                    ++n;
                    break;
                }
                *tab = 0;
                p = tab + 1;
            }
            if (n < 6)
                continue;
            t->tips = realloc(t->tips, sizeof *t->tips * (size_t)(t->ntips + 1));
            mu_t4_tip *tip = &t->tips[t->ntips++];
            memset(tip, 0, sizeof *tip);
            tip->id = (int32_t)strtol(field[0], NULL, 10);
            tip->kind = (int32_t)strtol(field[1], NULL, 10);
            tip->show_next = (uint8_t)strtol(field[2], NULL, 10);
            tip->fixed = (uint8_t)strtol(field[3], NULL, 10);
            unescape(tip->desc, sizeof tip->desc, field[4], strlen(field[4]));
            unescape(tip->next, sizeof tip->next, field[5], strlen(field[5]));
        }
        fclose(f);
        for (int a = 1; a < t->ntips; ++a)          /* the export is in key order already; keep it sorted */
            for (int b = a; b > 0 && t->tips[b - 1].id > t->tips[b].id; --b) {
                mu_t4_tip x = t->tips[b];
                t->tips[b] = t->tips[b - 1];
                t->tips[b - 1] = x;
            }
    }
    snprintf(path, sizeof path, "%s/tree4_side.tsv", dir ? dir : ".");
    f = fopen(path, "r");
    if (f) {
        while (fgets(line, sizeof line, f)) {
            int32_t v[22];
            int n = 0;
            char *p = strchr(line, '\t'), *end;
            if (line[0] == '#' || !p)
                continue;
            for (++p; n < 22; ++n) {
                long x = strtol(p, &end, 10);
                if (end == p)
                    break;
                v[n] = (int32_t)x;
                p = end;
            }
            if (!strncmp(line, "record", 6) && n == 22)
                mu_t4_side_table_record(&t->side, v);
            else if (!strncmp(line, "pair", 4) && n == 3)
                mu_t4_side_table_pair(&t->side, v[0], v[1], v[2]);
        }
        fclose(f);
    }
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
    mu_t4_side_table_init(&t->side);
    t->book = book;
    load(t, lang_dir);
    load_extras(t, lang_dir);
    mu_t4_window_init(&t->window, &t->table);
    mu_t4_window_set_side(&t->window, &t->side);
    t->env.user = t;
    t->env.skill_info = skill_info;
    t->env.hero_has = hero_has;
    t->env.master_level = master_level;
    t->env.skill_name = skill_name;
    t->cls = -1;
    return t;
}

void mu_skill_tree4_close(mu_skill_tree4 *t)
{
    if (!t)
        return;
    mu_t4_window_free(&t->window);
    mu_t4_table_free(&t->table);
    mu_t4_side_table_free(&t->side);
    free(t->tips);
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

int mu_skill_tree4_tooltip(mu_skill_tree4 *t, int side, int32_t index, char *title, size_t title_cap, char *body,
                           size_t body_cap, int32_t pos[2])
{
    if (!t || !t->book)
        return 0;
    mu_skill_tip_env tenv;
    mu_skill_book_tip_env(t->book, &tenv);
    mu_skill_tip *tip = calloc(1, sizeof *tip);
    char *ti = malloc(4096), *bo = malloc(65536);
    int ok = tip && ti && bo &&
             (side ? mu_t4_side_tooltip(&t->window, &tenv, &t->env, t->tips, t->ntips, index, tip, NULL, pos)
                   : mu_t4_tooltip(&t->window, &tenv, &t->env, t->tips, t->ntips, index, tip, NULL, pos));
    if (ok) {
        mu_skill_tooltip_html(tip, ti, 4096, bo, 65536);
        mu_latin1_to_utf8(title, title_cap, ti);
        mu_latin1_to_utf8(body, body_cap, bo);
    }
    free(tip);
    free(ti);
    free(bo);
    return ok;
}

void mu_skill_tree4_icons(mu_skill_tree4 *t, float x0, float y0, float scale, mu_t4_draw_fn draw, void *user)
{
    if (t && t->book)
        mu_t4_icons(&t->window, mu_skill_book_env(t->book), x0, y0, scale, 1.0f, 1.0f, draw, user);
}
