/* MyQuestInfo's guide quest tab (tab 0, ctor 0x00d4c27a, vtable 0x01aa4ca0) and its packets F6 0x50 / 0x51
 * (NATIVE-QUEST-002); see quest.h.  Every routine reports the client's effects into c->log. */
#include "quest_internal.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MQI "MyQuestInfo"

/* ---- data ------------------------------------------------------------------------------------------- */

static void free_guide(mu_quest_data *d)
{
    for (size_t k = 0; k < d->nguide_chapters; k++) {
        for (size_t i = 0; i < d->guide_chapters[k].nsteps; i++) {
            mu_guide_step *s = &d->guide_chapters[k].steps[i];
            free((char *)s->name);
            free((char *)s->info_name);
            free((char *)s->goal_name);
            free((int32_t *)s->classes);
            free((int32_t *)s->rewards);
        }
        free(d->guide_chapters[k].steps);
    }
    free(d->guide_chapters);
    d->guide_chapters = NULL;
    d->nguide_chapters = 0;
}

static void free_guide_strings(mu_guide_string *s, size_t n)
{
    for (size_t i = 0; i < n; i++)
        free(s[i].text);
    free(s);
}

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

static int split(const char *line, size_t len, const char **f, size_t *flen, int max)
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

/* Space-separated ints of a field into a new array; returns the count (-1 on error). */
static int32_t int_list(const char *s, size_t n, int32_t **out)
{
    *out = NULL;
    char *buf = malloc(n + 1);
    if (!buf)
        return -1;
    memcpy(buf, s, n);
    buf[n] = 0;
    int32_t count = 0, cap = 0;
    int32_t *v = NULL;
    for (char *p = buf; *p;) {
        while (*p == ' ')
            p++;
        if (!*p)
            break;
        char *end = NULL;
        long x = strtol(p, &end, 10);
        if (end == p) {
            free(v);
            free(buf);
            return -1;
        }
        if (count == cap) {
            cap = cap ? cap * 2 : 16;
            int32_t *nv = realloc(v, (size_t)cap * sizeof *v);
            if (!nv) {
                free(v);
                free(buf);
                return -1;
            }
            v = nv;
        }
        v[count++] = (int32_t)x;
        p = end;
    }
    free(buf);
    *out = v;
    return count;
}

long mu_guide_parse_steps(mu_quest_data *d, const char *text)
{
    if (!d || !text)
        return -1;
    free_guide(d);
    long total = 0;
    for (const char *line = text; *line;) {
        const char *eol = strchr(line, '\n');
        size_t len = eol ? (size_t)(eol - line) : strlen(line);
        const char *f[8];
        size_t fl[8];
        if (len && line[0] != '#' && split(line, len, f, fl, 8) == 7) {
            int32_t chapter = (int32_t)strtol(f[0], NULL, 10);
            int32_t *words = NULL, *classes = NULL, *rewards = NULL;
            int32_t nw = int_list(f[1], fl[1], &words);
            int32_t nc = int_list(f[5], fl[5], &classes);
            int32_t nr = int_list(f[6], fl[6], &rewards);
            if (chapter >= 0 && chapter < 1000 && nw == MU_GUIDE_STEP_WORDS && nc >= 0 && nr >= 0) {
                if ((size_t)chapter >= d->nguide_chapters) {
                    mu_guide_chapter *nc2 = realloc(d->guide_chapters, (size_t)(chapter + 1) * sizeof *nc2);
                    if (!nc2)
                        return -1;
                    memset(nc2 + d->nguide_chapters, 0, ((size_t)chapter + 1 - d->nguide_chapters) * sizeof *nc2);
                    d->guide_chapters = nc2;
                    d->nguide_chapters = (size_t)chapter + 1;
                }
                mu_guide_chapter *ch = &d->guide_chapters[chapter];
                mu_guide_step *ns = realloc(ch->steps, (ch->nsteps + 1) * sizeof *ns);
                if (!ns)
                    return -1;
                ch->steps = ns;
                mu_guide_step *s = &ch->steps[ch->nsteps++];
                memset(s, 0, sizeof *s);
                memcpy(s->w, words, sizeof s->w);
                s->name = unescape(f[2], fl[2]);
                s->info_name = unescape(f[3], fl[3]);
                s->goal_name = unescape(f[4], fl[4]);
                s->classes = classes;
                s->nclasses = nc;
                s->rewards = rewards;
                s->nrewards = nr / 3;
                classes = rewards = NULL;
                total++;
            }
            free(words);
            free(classes);
            free(rewards);
        }
        if (!eol)
            break;
        line = eol + 1;
    }
    return total;
}

static int cmp_key(const void *a, const void *b)
{
    const mu_guide_string *x = a, *y = b;
    return x->key < y->key ? -1 : x->key > y->key;
}

long mu_guide_parse_strings(mu_quest_data *d, const char *text)
{
    if (!d || !text)
        return -1;
    free_guide_strings(d->guide_titles, d->nguide_titles);
    free_guide_strings(d->guide_names, d->nguide_names);
    d->guide_titles = d->guide_names = NULL;
    d->nguide_titles = d->nguide_names = 0;
    size_t cap_t = 0, cap_n = 0;
    long total = 0;
    for (const char *line = text; *line;) {
        const char *eol = strchr(line, '\n');
        size_t len = eol ? (size_t)(eol - line) : strlen(line);
        const char *f[7];
        size_t fl[7];
        if (len && line[0] != '#' && split(line, len, f, fl, 7) == 6) {
            int kind = (int)strtol(f[0], NULL, 10);
            mu_guide_string g = {(int32_t)strtol(f[2], NULL, 10), (int32_t)strtol(f[3], NULL, 10),
                                 (int32_t)strtol(f[4], NULL, 10), NULL};
            int32_t where = (int32_t)strtol(f[1], NULL, 10);
            mu_guide_string **arr = kind == 1 ? &d->guide_titles : &d->guide_names;
            size_t *n = kind == 1 ? &d->nguide_titles : &d->nguide_names;
            size_t *cap = kind == 1 ? &cap_t : &cap_n;
            if (kind == 1 || kind == 2) {
                if (kind == 2)
                    g.key = where;
                g.text = unescape(f[5], fl[5]);
                if (*n == *cap) {
                    *cap = *cap ? *cap * 2 : 64;
                    mu_guide_string *na = realloc(*arr, *cap * sizeof *na);
                    if (!na)
                        return -1;
                    *arr = na;
                }
                (*arr)[(*n)++] = g;
                total++;
            }
        }
        if (!eol)
            break;
        line = eol + 1;
    }
    if (d->nguide_names)
        qsort(d->guide_names, d->nguide_names, sizeof *d->guide_names, cmp_key);
    return total;
}

void mu_guide_data_free(mu_quest_data *d);
void mu_guide_data_free(mu_quest_data *d)
{
    free_guide(d);
    free_guide_strings(d->guide_titles, d->nguide_titles);
    free_guide_strings(d->guide_names, d->nguide_names);
    d->guide_titles = d->guide_names = NULL;
    d->nguide_titles = d->nguide_names = 0;
}

static const mu_guide_string *guide_name(const mu_quest_data *d, int32_t key)
{
    size_t lo = 0, hi = d ? d->nguide_names : 0;
    while (lo < hi) {
        size_t mid = (lo + hi) / 2;
        if (d->guide_names[mid].key < key)
            lo = mid + 1;
        else
            hi = mid;
    }
    return lo < (d ? d->nguide_names : 0) && d->guide_names[lo].key == key ? &d->guide_names[lo] : NULL;
}

/* ---- the tab ---------------------------------------------------------------------------------------- */

static const mu_quest_data *data_of(const mu_quest_client *c)
{
    return c->qs.data;
}

static mu_guide_tab *tab(mu_quest_client *c)
{
    return c->guide;
}

static void list_clear(mu_guide_tab *t)
{
    t->nlist = 0;
}

static void list_push(mu_guide_tab *t, const mu_guide_step *s)
{
    if (t->nlist == t->cap) {
        size_t cap = t->cap ? t->cap * 2 : 32;
        mu_guide_step *n = realloc(t->list, cap * sizeof *n);
        if (!n)
            return;
        t->list = n;
        t->cap = cap;
    }
    t->list[t->nlist++] = *s;
}

#define DONE(s) ((uint8_t)((s)->w[0] & 0xff))
#define ID(s) ((s)->w[1])
#define STATE(s) ((s)->w[2])
#define W(s, off) ((s)->w[(off) / 4])

static const char *utf8(const mu_quest_client *c, const char *s, char *buf, size_t cap)
{
    return mu_quest_utf8(c, s, buf, cap);
}

int32_t mu_guide_find(const mu_quest_client *c, int32_t step)
{
    const mu_guide_tab *t = c->guide;
    for (size_t i = 0; t && i < t->nlist; i++)
        if (ID(&t->list[i]) == step)
            return (int32_t)i;
    return -1;
}

int32_t mu_guide_step_at(const mu_quest_client *c, int32_t index)
{
    const mu_guide_tab *t = c->guide;
    if (t && (uint32_t)index < t->nlist)
        return ID(&t->list[index]);
    return -1;
}

int mu_guide_level_ok(const mu_quest_client *c, int32_t step)
{
    const mu_guide_tab *t = c->guide;
    uint32_t i = (uint32_t)mu_guide_find(c, step);
    if (!t || i >= t->nlist)
        return 0;
    return W(&t->list[i], 0x40) > c->hero_level ? 0 : 1;
}

int32_t mu_guide_chapter_of(const mu_quest_client *c, int32_t step)
{
    const mu_quest_data *d = data_of(c);
    if (step == -1 || !d)
        return -1;
    for (size_t k = 0; k < d->nguide_chapters; k++) {
        const mu_guide_chapter *ch = &d->guide_chapters[k];
        if (!ch->nsteps)
            continue;   /* the client would read the element before the chapter's start */
        if (step <= ID(&ch->steps[ch->nsteps - 1]))
            return (int32_t)k + 1;
    }
    return -1;
}

int32_t mu_guide_next(const mu_quest_client *c, int32_t step)
{
    const mu_guide_tab *t = c->guide;
    const mu_quest_data *d = data_of(c);
    int32_t cur = mu_guide_chapter_of(c, step);
    if (!t || !t->nlist)
        return -1;
    int32_t last = mu_guide_chapter_of(c, ID(&t->list[t->nlist - 1]));
    if (cur == last && step < mu_guide_step_at(c, (int32_t)t->nlist - 1)) {
        int32_t i = mu_guide_find(c, t->current);
        return mu_guide_step_at(c, i + 1);
    }
    if (!d || (uint32_t)last >= d->nguide_chapters)
        return -2;
    const mu_guide_chapter *ch = &d->guide_chapters[last];
    int cls = c->hero_class & 0xf;
    for (size_t i = 0; i < ch->nsteps; i++) {
        const mu_guide_step *s = &ch->steps[i];
        int32_t flag = cls < s->nclasses ? s->classes[cls] : 0;
        if (flag != 0 && step < ID(s))
            return ID(s);
    }
    return -1;
}

void mu_guide_rebuild(mu_quest_client *c)
{
    mu_guide_tab *t = tab(c);
    const mu_quest_data *d = data_of(c);
    if (!t)
        return;
    int32_t ch = mu_guide_chapter_of(c, t->current) - 1;
    if (ch > -1 && d && (size_t)ch < d->nguide_chapters) {
        list_clear(t);
        const mu_guide_chapter *chap = &d->guide_chapters[ch];
        int cls = c->hero_class & 0xf;
        for (size_t i = 0; i < chap->nsteps; i++) {
            mu_guide_step s = chap->steps[i];
            int32_t flag = cls < s.nclasses ? s.classes[cls] : 0;
            if (flag == 0)
                continue;
            const mu_guide_string *g = guide_name(d, ID(&s));
            if (g)
                s.name = g->text;
            if (t->current > ID(&s))
                STATE(&s) = 3;
            else if (t->current < ID(&s))
                STATE(&s) = 0;
            else
                STATE(&s) = 1;
            if (W(&s, 0x30) == 1)
                list_push(t, &s);
        }
    }
    if (c->summary)
        mu_summary_guide_refresh(c);
}

void mu_guide_init(mu_quest_client *c)
{
    mu_guide_tab *t = tab(c);
    if (!t || !t->nlist)
        return;
    static char ss[65536];
    size_t n = 0;
    ss[0] = 0;
    int32_t focus = -1;
    for (size_t i = 0; i < t->nlist; i++) {
        const mu_guide_step *s = &t->list[i];
        uint32_t color = mu_quest_list_color(STATE(s), W(s, 0x34));
        char text[1024], html[4096];
        snprintf(text, sizeof text, "%s%s", STATE(s) == 3 ? "   " : "-  ", s->name ? s->name : "");
        mu_quest_html_line(text, color, 0, 1, html, sizeof html);
        n += (size_t)snprintf(ss + n, sizeof ss - n, "%s;", html);
        if (n >= sizeof ss)
            n = sizeof ss - 1;
        if (focus == -1 && STATE(s) == 1) {
            focus = (int32_t)i;
            if (t->selected > 1000000 || t->selected < 0)
                t->selected = (int32_t)i;
        }
    }
    static char u[65536];
    utf8(c, ss, u, sizeof u);
    mu_quest_invoke(c, MQI, "SetGuideQuestList", "%s %d", u, focus);
    mu_quest_invoke(c, MQI, "SetGuideQuestListFocus", "%d", focus);
}

void mu_guide_close(mu_quest_client *c)
{
    if (!tab(c))
        return;
    mu_guide_set_check(c, 0);
    mu_quest_invoke(c, MQI, "SetGuideChapterCheckBox", "%d", 0);
}

void mu_guide_clear(mu_quest_client *c)
{
    mu_guide_tab *t = tab(c);
    if (!t)
        return;
    t->current = -1;
    list_clear(t);
    mu_quest_invoke(c, MQI, "GuideDisabled", "%d", 0);
    mu_quest_invoke(c, MQI, "SetGuideQuestList", "%s %d", ";;;;;;", -1);
}

void mu_guide_goal_text(const mu_quest_client *c, int32_t step, char *out, size_t cap)
{
    const mu_guide_tab *t = c->guide;
    out[0] = 0;
    int32_t i = mu_guide_find(c, step);
    if (i < 0 || !t)
        return;
    const mu_guide_step *s = &t->list[i];
    int32_t kind = W(s, 0x8c), count = 0;
    if (STATE(s) == 3) {
        snprintf(out, cap, "%s", mu_quest_text(c, 0x1237));
        return;
    }
    if (STATE(s) == 1)
        count = t->count;
    const char *name = s->name ? s->name : "";
    if (kind == 1 || kind == 2) {
        mu_qarg a[3] = {{1, 0, name}, {0, count, NULL}, {0, W(s, 0x98), NULL}};
        mu_quest_sprintf(out, cap, "%s x %d/%d", a, 3);
    } else if (kind == 3 || kind == 4 || kind == 5) {
        mu_qarg a[1] = {{1, 0, name}};
        mu_quest_sprintf(out, cap, "%s", a, 1);
    }
}

void mu_guide_level_text(const mu_quest_client *c, int32_t step, char *out, size_t cap)
{
    const mu_guide_tab *t = c->guide;
    out[0] = 0;
    int32_t i = mu_guide_find(c, step);
    if (i < 0 || !t)
        return;
    const mu_guide_step *s = &t->list[i];
    char text[512];
    mu_qarg a = {0, W(s, 0x40), NULL};
    mu_quest_sprintf(text, sizeof text, mu_quest_text(c, 0x141e), &a, 1);
    uint32_t color = mu_guide_level_ok(c, ID(s)) ? mu_quest_rgba(200, 200, 200, 200) : mu_quest_rgba(0xb4, 0x32, 0x32, 0xfa);
    mu_quest_html_line(text, color, 0, 1, out, cap);
}

void mu_guide_buttons(mu_quest_client *c)
{
    mu_guide_tab *t = tab(c);
    if (!t)
        return;
    char a[512], b[512];
    utf8(c, mu_quest_text(c, t->complete ? 0x141f : 0x1420), a, sizeof a);
    mu_quest_invoke(c, MQI, "ChangeGuideGiveUpOrMoveButtonLabel", "%s", a);
    utf8(c, mu_quest_text(c, t->check ? 0x1423 : 0xb07), b, sizeof b);
    mu_quest_invoke(c, MQI, "ChangeGuideGiveUpButtonLabel", "%s", b);
    int d = 1, e = 1;
    if (t->selected > -1 && (uint32_t)t->selected < t->nlist && STATE(&t->list[t->selected]) == 1)
        d = e = 0;
    if (!mu_guide_level_ok(c, mu_guide_step_at(c, t->selected)))
        d = e = 1;
    if (t->complete)
        d = 1;
    mu_quest_invoke(c, MQI, "SetDisableGuideQuestButton", "%d %d", d, e);
}

void mu_guide_conditions(mu_quest_client *c, int32_t index)
{
    mu_guide_tab *t = tab(c);
    if (!t || index < 0 || (size_t)index >= t->nlist)
        return;
    const mu_guide_step *s = &t->list[index];
    uint32_t color = mu_quest_rgba(100, 0x82, 0xe6, 0xfa);
    char exp[512], zen[512], hexp[1024], hzen[1024], uexp[1024], uzen[1024];
    mu_qarg ae = {0, W(s, 0xb4), NULL}, az = {0, W(s, 0xb8), NULL};
    mu_quest_sprintf(exp, sizeof exp, mu_quest_text(c, 0x141c), &ae, 1);
    mu_quest_sprintf(zen, sizeof zen, mu_quest_text(c, 0x141d), &az, 1);
    mu_quest_html_line(exp, color, 0, 1, hexp, sizeof hexp);
    mu_quest_html_line(zen, color, 0, 1, hzen, sizeof hzen);
    utf8(c, hexp, uexp, sizeof uexp);
    utf8(c, hzen, uzen, sizeof uzen);
    char items[3][1024], uitems[3][1024];
    for (int k = 0; k < 3; k++)
        items[k][0] = 0;
    for (int k = 0; k < 3; k++) {
        if (k >= s->nrewards)
            continue;   /* the client reads past the vector: the loader writes exactly three */
        const int32_t *r = &s->rewards[k * 3];
        if (r[1] <= 0)
            continue;
        int32_t code = r[0] * 0x200 + r[1];
        if (code >= 0x21e9 || code < 0)
            continue;
        const char *name = c->host.item_record_name ? c->host.item_record_name(c->host.user, code) : NULL;
        if (!name)
            continue;
        char line[512];
        mu_qarg a[2] = {{1, 0, name}, {0, r[2], NULL}};
        mu_quest_sprintf(line, sizeof line, "%s x %d", a, 2);
        mu_quest_html_line(line, color, 0, 1, items[k], sizeof items[k]);
    }
    for (int k = 0; k < 3; k++)
        utf8(c, items[k], uitems[k], sizeof uitems[k]);
    mu_quest_invoke(c, MQI, "SetGuideQuestReward", "%s %s %s %s %s", uexp, uzen, uitems[0], uitems[1], uitems[2]);
}

void mu_guide_show(mu_quest_client *c, int32_t index)
{
    mu_guide_tab *t = tab(c);
    if (!t || index < 0 || (size_t)index >= t->nlist)
        return;
    t->selected = index;
    const mu_guide_step *s = &t->list[index];
    char goal[2048], level[2048], hgoal[4096], ugoal[4096], ulevel[4096];
    mu_guide_goal_text(c, ID(s), goal, sizeof goal);
    mu_guide_level_text(c, ID(s), level, sizeof level);
    uint32_t color = STATE(s) == 1 ? mu_quest_rgba(0xe6, 0xe6, 0xe6, 0xfa) : mu_quest_rgba(0x8c, 0x8c, 0x8c, 0xfa);
    mu_quest_html_line(goal, color, 0, 1, hgoal, sizeof hgoal);
    utf8(c, hgoal, ugoal, sizeof ugoal);
    utf8(c, level, ulevel, sizeof ulevel);
    mu_quest_invoke(c, MQI, "SetGuideQuestRequirement", "%s %s", ugoal, ulevel);
    mu_guide_conditions(c, index);
    mu_guide_buttons(c);
}

void mu_guide_chapter_change(mu_quest_client *c, int32_t step)
{
    mu_guide_tab *t = tab(c);
    const mu_quest_data *d = data_of(c);
    if (!t)
        return;
    t->current = step;
    mu_quest_invoke(c, MQI, "SetGuideChapterCheckBox", "%d", 0);
    mu_guide_rebuild(c);
    mu_guide_init(c);
    int32_t ch = mu_guide_chapter_of(c, t->current);
    const char *name = d && ch - 1 >= 0 && (size_t)(ch - 1) < d->nguide_titles ? d->guide_titles[ch - 1].text : "";
    char u[1024];
    utf8(c, name ? name : "", u, sizeof u);
    mu_quest_invoke(c, MQI, "SetChapterName", "%s", u);
}

void mu_guide_set_check(mu_quest_client *c, int check)
{
    mu_guide_tab *t = tab(c);
    if (!t)
        return;
    t->check = (uint8_t)check;
    if (!check)
        mu_guide_buttons(c);
    else
        mu_quest_invoke(c, MQI, "SetDisableGuideQuestButton", "%d %d", 0, 1);
    mu_quest_invoke(c, MQI, "SetGuideQuestListSelected", "%d", t->check);
}

void mu_guide_set_state(mu_quest_client *c, int32_t index, int32_t state)
{
    mu_guide_tab *t = tab(c);
    if (!t || index < 0 || (size_t)index >= t->nlist)
        return;
    mu_guide_step *s = &t->list[index];
    STATE(s) = state;
    uint32_t color = mu_quest_list_color(STATE(s), W(s, 0x34));
    char text[1024], html[4096], u[4096];
    snprintf(text, sizeof text, "%s%s", state == 3 ? "   " : "-  ", s->name ? s->name : "");
    mu_quest_html_line(text, color, 0, 1, html, sizeof html);
    utf8(c, html, u, sizeof u);
    mu_quest_invoke(c, MQI, "GuideQuestStateChange", "%s %d %d", u, index, STATE(s));
}

int mu_guide_summary_update(mu_quest_client *c)
{
    mu_guide_tab *t = tab(c);
    if (!t)
        return 0;
    int32_t i = mu_guide_find(c, t->current);
    if (i > -1 && STATE(&t->list[i]) == 1) {
        if (c->summary)
            mu_summary_guide_set(c, i);
        return 1;
    }
    if (c->summary)
        mu_summary_guide_set(c, -1);
    return 0;
}

/* ---- packets -------------------------------------------------------------------------------------- */

void mu_guide_receive_state(mu_quest_client *c, const uint8_t *p, size_t size)
{
    mu_guide_tab *t = tab(c);
    if (!t || size < 8)
        return;
    int32_t step = p[4] | p[5] << 8;
    uint8_t count = p[6], state = p[7];
    if (t->current == -1) {
        t->complete = 0;
        mu_guide_chapter_change(c, step);
        mu_guide_show(c, t->selected);
        if (c->summary && c->hud && c->hud->guide_shown)
            mu_summary_show(c);
    }
    if (state == 2) {
        t->complete = 1;
        int32_t i = mu_guide_find(c, step);
        if (i != -1)
            t->list[i].w[0] = (t->list[i].w[0] & ~0xff) | 1;
        if (c->summary) {
            mu_summary_show(c);
            c->hud->guide_shown = 1;
        }
    }
    if (state == 3 || state == 4) {
        int32_t next = mu_guide_next(c, step);
        if (next > -1) {
            step = next;
        } else if (next == -2) {
            list_clear(t);
            mu_quest_invoke(c, MQI, "GuideDisabled", "%d", 1);
            mu_quest_invoke(c, MQI, "SetGuideQuestList", "%s %d", ";;;;;;", -1);
            mu_quest_invoke(c, MQI, "SetGuideQuestReward", "%s %s %s %s %s", "", "", "", "", "");
            mu_quest_invoke(c, MQI, "SetGuideQuestRequirement", "%s %s", "", "");
        }
    }
    if (step != t->current) {
        int32_t old_ch = mu_guide_chapter_of(c, t->current);
        int32_t new_ch = mu_guide_chapter_of(c, step);
        if (new_ch < 0)
            return;
        t->current = step;
        if (state != 2)
            t->complete = 0;
        if (old_ch != new_ch)
            mu_guide_chapter_change(c, t->current);
        for (size_t i = 0; i < t->nlist; i++) {
            if (ID(&t->list[i]) >= t->current) {
                mu_guide_set_state(c, (int32_t)i, 1);
                break;
            }
            mu_guide_set_state(c, (int32_t)i, 3);
        }
        t->selected = mu_guide_find(c, step);
        mu_quest_invoke(c, MQI, "SetGuideQuestListFocus", "%d", t->selected);
    }
    if (t->count != count) {
        t->count = count;
        if (mu_guide_step_at(c, t->selected) == step)
            mu_guide_show(c, t->selected);
    }
    mu_guide_buttons(c);
    if (c->summary)
        mu_summary_guide_refresh(c);
}

void mu_guide_receive_result(mu_quest_client *c, const uint8_t *p, size_t size)
{
    if (size < 7)
        return;
    switch (p[6]) {
    case 1:
        mu_quest_logf(&c->log, "layer QuestProgressInfo 8");
        mu_quest_progress_info(c);
        break;
    case 2:
        mu_quest_notice(c, mu_quest_text(c, 0x11b4));
        break;
    case 3:
        mu_quest_notice(c, mu_quest_text(c, 0x177));
        break;
    }
}

/* ---- requests and buttons ------------------------------------------------------------------------ */

static void send_f6_id(mu_quest_client *c, uint8_t sub, int32_t id)
{
    uint8_t b[6] = {0xf6, sub, (uint8_t)id, (uint8_t)(id >> 8), (uint8_t)(id >> 16), (uint8_t)(id >> 24)};
    mu_quest_send(c, b, 6, 1, 0);
}

void mu_guide_request(mu_quest_client *c, int32_t sub)
{
    mu_guide_tab *t = tab(c);
    if (!t)
        return;
    switch (sub) {
    case 0x51:
        send_f6_id(c, 0x51, t->current);
        break;
    case 0x53:  /* 0x00d4bc78: the selected entry's step, then the path reset */
        send_f6_id(c, 0x53, mu_guide_step_at(c, t->selected));
        if (c->host.path_reset)
            c->host.path_reset(c->host.user);
        mu_quest_logf(&c->log, "path reset");
        break;
    case 0x54:  /* 0x00d4bd28: the server moves the hero to the step's map (cross-map travel: NATIVE-MAP-001) */
    case 0x55:
        send_f6_id(c, (uint8_t)sub, t->current);
        break;
    case 0x57: {
        uint8_t b[2] = {0xf6, 0x57};
        mu_quest_send(c, b, 2, 1, 0);
        break;
    }
    }
}

void mu_guide_giveup(mu_quest_client *c)
{
    mu_guide_tab *t = tab(c);
    if (!t)
        return;
    /* a function-local static (0x01ec8e98, first use: the time) and [0x01cf0e38]: one request per second per step */
    if (!c->throttle_init) {
        c->throttle_init = 1;
        c->throttle_until = c->time;
    }
    if (!(c->time > c->throttle_until + 1000.0f) && c->throttle_quest == t->current)
        return;
    c->throttle_until = c->time;
    if (t->check) {
        if (!t->nlist)
            return;   /* the client reads the entry before the list */
        int32_t need = W(&t->list[t->nlist - 1], 0x40);
        if (c->hero_level < need) {
            char html[1024];
            mu_quest_html_line(mu_quest_text(c, 0x1421), 0xfa, 0, 1, html, sizeof html);
            mu_quest_msgbox(c, MQI, 0x2f, html, "", 0, 1, 0);
        } else {
            char html[1024];
            mu_quest_html_line(mu_quest_text(c, 0x1422), 0xfa, 0, 1, html, sizeof html);
            mu_quest_msgbox2(c, MQI, 0x2e, html, mu_quest_text(c, 0x1423), 0, 0, 1, 0);
        }
        return;
    }
    if (c->host.path_reset)
        c->host.path_reset(c->host.user);
    mu_quest_logf(&c->log, "path reset");
    c->throttle_quest = t->current;
    send_f6_id(c, 0x52, t->current);
    mu_quest_notice(c, mu_quest_text(c, 0xb02));
}

void mu_guide_box(mu_quest_client *c, int32_t box, int32_t result)
{
    mu_guide_tab *t = tab(c);
    if (!t || box == 0x2f || result != 0 || !t->nlist)
        return;
    send_f6_id(c, 0x53, ID(&t->list[t->nlist - 1]));
    mu_quest_notice(c, mu_quest_text(c, 0xb02));
}

static void helper_toggle(mu_quest_client *c, int start)
{
    uint8_t b[3] = {0xbf, 0x51, (uint8_t)(start ? 0 : 1)};
    mu_quest_send(c, b, 3, 0, 0);
}

/* The arrival tail both "Go Now" routines share (the hero already stands on the target). */
void mu_quest_arrived_helper(mu_quest_client *c);
void mu_quest_arrived_helper(mu_quest_client *c)
{
    if (c->hero_safe)
        return;
    int available = c->host.helper_available ? c->host.helper_available(c->host.user) : 0;
    int running = c->host.helper_running ? c->host.helper_running(c->host.user) : 0;
    if (available && !running)
        helper_toggle(c, 1);
    if (c->helper_notice)
        mu_quest_logf(&c->log, "helper notice %s 20 150 2000", mu_quest_text(c, 0xdea));
}

void mu_guide_go(mu_quest_client *c)
{
    mu_guide_tab *t = tab(c);
    if (!t)
        return;
    if (t->complete) {
        mu_guide_request(c, 0x51);
        return;
    }
    int32_t i = mu_guide_find(c, t->current);
    if (!((int32_t)t->nlist > i) || i < 0)
        return;   /* i == -1 passes the client's signed test and reads before the list */
    if (c->host.helper_running && c->host.helper_running(c->host.user))
        helper_toggle(c, 0);
    if (c->info.visible) {
        mu_quest_info_close(c);
    }
    const mu_guide_step *s = &t->list[i];
    int32_t world = W(s, 0xa8), tx = W(s, 0xac), ty = W(s, 0xb0);
    int32_t hx = c->hero_x, hy = c->hero_y;
    if (world == c->world) {
        if (hx == tx && hy == ty) {
            if (c->host.path_reset)
                c->host.path_reset(c->host.user);
            mu_quest_logf(&c->log, "path reset");
            mu_guide_request(c, 0x55);
            mu_quest_arrived_helper(c);
            return;
        }
        int ok = c->host.path_start ? c->host.path_start(c->host.user, 2, hx, hy, tx, ty, 1, 1) : 0;
        mu_quest_logf(&c->log, "path start 2 %d %d %d %d 1 1 -> %d", hx, hy, tx, ty, ok);
        if (ok == 1) {
            int moved = c->host.send_move ? c->host.send_move(c->host.user) : 0;
            mu_quest_logf(&c->log, "sendmove -> %d", moved);
            if (moved == 1)
                c->hero_walk = 0;
            return;
        }
    }
    int ok = c->host.path_start ? c->host.path_start(c->host.user, 1, hx, hy, tx, ty, 1, 0) : 0;
    mu_quest_logf(&c->log, "path start 1 %d %d %d %d 1 0 -> %d", hx, hy, tx, ty, ok);
    mu_guide_request(c, 0x54);
}
