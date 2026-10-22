/* The quest summary HUD (QuestSummary / winQuestSummary: the handler's routines 0x00c89f80..0x00c8ae30) and the
 * QuestProgressInfo notice movie (NATIVE-QUEST-002); see quest.h.
 *
 * QuestSummary is a GFx window of the second UI layer (0x01d22c60): its values are built with 0x00af068c (object)
 * / 0x00af06d2 (array) and members, set with 0x00c8fac2 ("_root.<window>.<method>" with a value: logged
 * "value QuestSummary METHOD [json]") and its window calls 0x00c8f9e8 ("call QuestSummary METHOD"). */
#include "quest_internal.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define QS_WIN "QuestSummary"
#define MQI "MyQuestInfo"

static mu_quest_summary *hud(mu_quest_client *c)
{
    return c->summary ? c->hud : NULL;
}

/* JSON text of one object member (the value model of the validator). */
static size_t put_str(char *out, size_t cap, size_t n, const char *key, const char *value, int first)
{
    char q[8192];
    mu_quest_json(q, sizeof q, value);
    n += (size_t)snprintf(out + n, cap - n, "%s\"%s\":%s", first ? "" : ",", key, q);
    return n < cap ? n : cap - 1;
}

static size_t put_num(char *out, size_t cap, size_t n, const char *key, double value, int first)
{
    n += (size_t)snprintf(out + n, cap - n, "%s\"%s\":%.17g", first ? "" : ",", key, value);
    return n < cap ? n : cap - 1;
}

static size_t put_bool(char *out, size_t cap, size_t n, const char *key, int value, int first)
{
    n += (size_t)snprintf(out + n, cap - n, "%s\"%s\":%s", first ? "" : ",", key, value ? "true" : "false");
    return n < cap ? n : cap - 1;
}

static const mu_guide_step *guide_entry(mu_quest_client *c, mu_quest_summary *h)
{
    if (h->guide_index < 0)
        return NULL;
    /* the client keeps a pointer into the tab's list: a rebuilt list shows through it */
    if (c->guide && (size_t)h->guide_index < c->guide->nlist)
        return &c->guide->list[h->guide_index];
    /* a cleared list: the destroyed entry keeps its words, its strings are empty */
    h->guide_copy.name = h->guide_copy.info_name = h->guide_copy.goal_name = "";
    return &h->guide_copy;
}

void mu_summary_show(mu_quest_client *c)
{
    if (hud(c)) {
        mu_quest_logf(&c->log, "call %s openWindow", QS_WIN);
        c->hud->visible = 1;
    }
}

static void summary_hide(mu_quest_client *c)
{
    mu_quest_logf(&c->log, "call %s closeWindow", QS_WIN);
    c->hud->visible = 0;
}

/* 0x00c8ad60 */
static void summary_visibility(mu_quest_client *c)
{
    mu_quest_summary *h = c->hud;
    int any = MU_QUEST_MUTATION == 8 ? 0 : h->guide_index >= 0 || h->nquests > 0 || h->other > 0;
    if (any && !h->blocked)
        mu_summary_show(c);
    else
        summary_hide(c);
}

void mu_summary_update(mu_quest_client *c)
{
    mu_quest_summary *h = hud(c);
    if (!h)
        return;
    static char arr[65536];
    size_t n = 0;
    int count = 0;
    n += (size_t)snprintf(arr + n, sizeof arr - n, "[");
    const mu_guide_step *s = guide_entry(c, h);
    if (s) {
        char name[2048], req[2048], text[1024];
        mu_quest_html_line(s->name ? s->name : "", mu_quest_list_color(s->w[2], s->w[0x34 / 4]), 0, 1, name,
                           sizeof name);
        if (s->w[0] & 0xff) {
            mu_quest_html_line(mu_quest_text(c, 0x1411), mu_quest_rgba(0xe6, 0xe6, 0xe6, 0xfa), 0, 1, req, sizeof req);
        } else {
            if (mu_guide_level_ok(c, s->w[1])) {
                mu_guide_goal_text(c, s->w[1], text, sizeof text);
            } else {
                mu_qarg a = {0, s->w[0x40 / 4], NULL};
                mu_quest_sprintf(text, sizeof text, mu_quest_text(c, 0x141b), &a, 1);
            }
            mu_quest_html_line(text, mu_quest_rgba(0x8c, 0x8c, 0x8c, 0xfa), 0, 1, req, sizeof req);
        }
        n += (size_t)snprintf(arr + n, sizeof arr - n, "%s{", count ? "," : "");
        n = put_num(arr, sizeof arr, n, "Category", 1.0, 1);
        n = put_num(arr, sizeof arr, n, "Index", (double)s->w[1], 0);
        n = put_str(arr, sizeof arr, n, "Name", name, 0);
        n = put_str(arr, sizeof arr, n, "Requirement", req, 0);
        n = put_bool(arr, sizeof arr, n, "Completion", s->w[0] & 0xff, 0);
        n += (size_t)snprintf(arr + n, sizeof arr - n, "}");
        count++;
    }
    for (int32_t k = 0; k < h->nquests; k++) {
        mu_quest *q = mu_quest_get(&c->qs, h->quests[k]);
        if (!q)
            continue;
        const mu_quest_dialogue *g = mu_quest_dialogue_get(&c->qs, q->index);
        char name[2048], req[2048], text[1100];
        mu_quest_html_line(g ? g->title : (q->record && q->record->name ? q->record->name : ""), 0xffffffffu, 0, 1,
                           name, sizeof name);
        int complete = q->state == 2;
        if (complete) {
            int32_t gt = q->record && q->record->accept[4] == 2 ? 0x1547 : 0x141f;
            mu_quest_html_line(mu_quest_text(c, gt), mu_quest_rgba(0xe6, 0xe6, 0xe6, 0xfa), 0, 1, req, sizeof req);
        } else {
            int32_t need = q->record ? q->record->accept[6] : 0;
            if (c->hero_level_total < need) {
                mu_qarg a = {0, need, NULL};
                mu_quest_sprintf(text, sizeof text, mu_quest_text(c, 0x141b), &a, 1);
            } else {
                mu_quest_line line;
                mu_quest_condition(&c->host, q, c->font_default, &line);
                snprintf(text, sizeof text, "%s", line.text);
            }
            mu_quest_html_line(text, mu_quest_rgba(0x8c, 0x8c, 0x8c, 0xfa), 0, 1, req, sizeof req);
        }
        n += (size_t)snprintf(arr + n, sizeof arr - n, "%s{", count ? "," : "");
        n = put_num(arr, sizeof arr, n, "Category", 2.0, 1);
        n = put_num(arr, sizeof arr, n, "Index", (double)q->index, 0);
        n = put_str(arr, sizeof arr, n, "Name", name, 0);
        n = put_str(arr, sizeof arr, n, "Requirement", req, 0);
        n = put_bool(arr, sizeof arr, n, "Completion", complete, 0);
        n += (size_t)snprintf(arr + n, sizeof arr - n, "}");
        count++;
        if (n >= sizeof arr - 2)
            break;
    }
    snprintf(arr + n, sizeof arr - n, "]");
    mu_quest_logf(&c->log, "value %s SetQuestList [%s]", QS_WIN, arr);
    summary_visibility(c);
}

void mu_summary_guide_set(mu_quest_client *c, int32_t index)
{
    mu_quest_summary *h = hud(c);
    if (!h)
        return;
    h->guide_index = index;
    if (index >= 0 && c->guide && (size_t)index < c->guide->nlist)
        h->guide_copy = c->guide->list[index];
    mu_summary_update(c);
}

void mu_summary_guide_refresh(mu_quest_client *c)
{
    mu_quest_summary *h = hud(c);
    if (h && h->guide_shown && c->guide)
        mu_guide_summary_update(c);
}

static int find_quest(const mu_quest_summary *h, int32_t index, int32_t *at)
{
    int32_t lo = 0, hi = h->nquests;
    while (lo < hi) {
        int32_t mid = (lo + hi) / 2;
        if (h->quests[mid] < index)
            lo = mid + 1;
        else
            hi = mid;
    }
    *at = lo;
    return lo < h->nquests && h->quests[lo] == index;
}

void mu_summary_add(mu_quest_client *c, int32_t index)
{
    mu_quest_summary *h = hud(c);
    if (!h)
        return;
    int32_t at;
    if (!find_quest(h, index, &at) && h->nquests < (int32_t)(sizeof h->quests / sizeof h->quests[0])) {
        memmove(&h->quests[at + 1], &h->quests[at], (size_t)(h->nquests - at) * sizeof h->quests[0]);
        h->quests[at] = index;
        h->nquests++;
    }
    mu_summary_update(c);
}

void mu_summary_remove(mu_quest_client *c, int32_t index)
{
    mu_quest_summary *h = hud(c);
    if (!h)
        return;
    int32_t at;
    if (find_quest(h, index, &at)) {
        memmove(&h->quests[at], &h->quests[at + 1], (size_t)(h->nquests - at - 1) * sizeof h->quests[0]);
        h->nquests--;
        mu_summary_update(c);
    }
}

void mu_summary_clear(mu_quest_client *c)
{
    mu_quest_summary *h = hud(c);
    if (!h)
        return;
    h->nquests = 0;
    mu_summary_update(c);
}

void mu_summary_onload(mu_quest_client *c)
{
    if (!hud(c))
        return;
    char title[1024];
    size_t n = (size_t)snprintf(title, sizeof title, "{");
    n = put_str(title, sizeof title, n, "title", mu_quest_text(c, 0x1478), 1);
    snprintf(title + n, sizeof title - n, "}");
    mu_quest_logf(&c->log, "value %s setTextInfo [%s]", QS_WIN, title);
}

int mu_summary_callback(mu_quest_client *c, const char *name, int32_t category, int32_t index)
{
    /* 0x00c89dfb: OnClickQuest(category, index), onLoad, onButtonClose */
    if (!strcmp(name, "OnClickQuest")) {
        mu_summary_click(c, category, index);
        return 1;
    }
    if (!strcmp(name, "onLoad")) {
        mu_summary_onload(c);
        mu_quest_logf(&c->log, "invoke %s setCloseLock [true]", QS_WIN);
        return 1;
    }
    if (!strcmp(name, "onButtonClose")) {
        if (c->hud)
            c->hud->guide_shown = 0;
        return 1;
    }
    return 0;
}

void mu_summary_click(mu_quest_client *c, int32_t kind, int32_t quest)
{
    if (c->hud && c->hud->other_window)
        return;   /* the window at manager + 0x290 is open */
    if (kind == 1) {
        mu_guide_tab *t = c->guide;
        if (t && t->complete)
            mu_guide_request(c, 0x51);
        if (!c->info.visible)
            mu_quest_info_open(c);
        if (c->info.tab != 0)
            mu_quest_invoke(c, MQI, "SelectTab", "%d", 0);
        int32_t sel = t ? mu_guide_find(c, t->current) : -1;
        /* 0x00be4558: the current tab's show (vtable +0x10) */
        if (c->info.tab == 0)
            mu_guide_show(c, sel);
        else {
            mu_quest_tab *qt = mu_quest_info_tab(c, c->info.tab);
            if (qt)
                mu_quest_tab_show(c, qt, sel);
        }
        mu_quest_invoke(c, MQI, "SetGuideQuestListFocus", "%d", t ? t->selected : 0);
    } else if (kind == 2) {
        mu_quest *q = mu_quest_get(&c->qs, quest);
        if (!q)
            return;
        mu_quest_tab *qt = mu_quest_info_tab(c, q->category);
        if (!qt)
            return;
        if (q->state == 2) {
            mu_quest_tab_action(c, qt, quest);
            return;
        }
        if (!c->info.visible)
            mu_quest_info_open(c);
        if (c->info.tab != q->category)
            mu_quest_invoke(c, MQI, "SelectTab", "%d", q->category);
        /* 0x00d500e0: the quest's row among the category's active quests */
        const int32_t *act = NULL;
        size_t n = mu_quest_active(&c->qs, qt->category, &act);
        for (size_t i = 0; i < n; i++)
            if (act[i] == quest) {
                mu_quest_invoke(c, MQI, "SelectQuest", "%d %d", qt->category, (int32_t)i);
                break;
            }
    }
}

/* ---- QuestProgressInfo -------------------------------------------------------------------------- */

void mu_quest_progress_info_onload(mu_quest_client *c)
{
    char u[512];
    mu_quest_utf8(c, mu_quest_text(c, 0x1237), u, sizeof u);
    mu_quest_invoke(c, "QuestProgressInfo", "InitText", "%s", u);
    if ((float)(double)c->screen_width > 1024.0f)
        mu_quest_logf(&c->log, "scalemode QuestProgressInfo 2");
}

void mu_quest_progress_info(mu_quest_client *c)
{
    mu_quest_show(c, "QuestProgressInfo");
    mu_quest_invoke(c, "QuestProgressInfo", "PlayAnimation", "");
}
