/* The quest windows' game side (NATIVE-QUEST-001): NpcQuestProgress, npcdialogue's quest list and
 * MyQuestInfo's quest tabs; see quest.h.  Every routine reports the client's effects into c->log. */
#include "quest_internal.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define NQP "NpcQuestProgress"
#define MQI "MyQuestInfo"
#define DLG "npcdialogue"

/* ---- invokes ---------------------------------------------------------------------------------- */

/* 0x00aae7e0(window, method, "%s %s ...", ...) with string arguments (each converted by the caller). */
static void invoke_s(mu_quest_client *c, const char *w, const char *m, int n, const char *const *s)
{
    char args[16384];
    size_t len = 0;
    args[len++] = '[';
    for (int i = 0; i < n; i++) {
        char q[8192];
        mu_quest_json(q, sizeof q, s[i]);
        len += (size_t)snprintf(args + len, sizeof args - len, "%s%s", i ? "," : "", q);
        if (len >= sizeof args)
            len = sizeof args - 1;
    }
    snprintf(args + len, sizeof args - len, "]");
    mu_quest_logf(&c->log, "invoke %s %s %s", w, m, args);
}

static void invoke_text(mu_quest_client *c, const char *w, const char *m, const char *s)
{
    const char *a[1] = {s};
    invoke_s(c, w, m, 1, a);
}

/* 0x00aaec81(window, text, method, separator): both converted, "%s %s"; nothing for a NULL text. */
static void invoke_divide(mu_quest_client *c, const char *w, const char *text, const char *m, const char *sep)
{
    if (!text)
        return;
    char a[8192], b[64];
    mu_quest_utf8(c, text, a, sizeof a);
    mu_quest_utf8(c, sep, b, sizeof b);
    const char *s[2] = {a, b};
    invoke_s(c, w, m, 2, s);
}

static void show(mu_quest_client *c, const char *w)
{
    mu_quest_logf(&c->log, "show %s", w);
}

static void hide(mu_quest_client *c, const char *w)
{
    mu_quest_logf(&c->log, "hide %s", w);
}

/* The packet builder (0x00d51baf head/opcode, 0x0095c204 byte, 0x009c06dd word) and its send 0x00d51d4f. */
static void send_packet(mu_quest_client *c, const uint8_t *body, int n, int encrypt)
{
    char hex[256];
    size_t len = 0;
    int total = n + 2;
    len += (size_t)snprintf(hex + len, sizeof hex - len, "c1 %02x", total);
    for (int i = 0; i < n; i++)
        len += (size_t)snprintf(hex + len, sizeof hex - len, " %02x", body[i]);
    mu_quest_logf(&c->log, "send %s | %d 0", hex, encrypt);
}

static void send_f6(mu_quest_client *c, uint8_t sub, const int32_t *words, int nwords, int encrypt)
{
    uint8_t b[32];
    int n = 0;
    b[n++] = 0xf6;
    b[n++] = sub;
    for (int i = 0; i < nwords; i++) {
        b[n++] = (uint8_t)(words[i] & 0xff);
        b[n++] = (uint8_t)((words[i] >> 8) & 0xff);
    }
    send_packet(c, b, n, encrypt);
}

static const char *utf8_text(mu_quest_client *c, int32_t gt, char *buf, size_t cap)
{
    return mu_quest_utf8(c, mu_quest_text(c, gt), buf, cap);
}

/* ---- NpcQuestProgress ------------------------------------------------------------------------- */

static void pages_clear(mu_quest_progress_window *w)
{
    for (int32_t i = 0; i < w->npages; i++)
        free(w->pages[w->page_first + i]);
    free(w->pages);
    w->pages = NULL;
    w->npages = w->page_first = 0;
}

static mu_quest *progress_quest(mu_quest_client *c)
{
    return c->progress.quest_ptr >= 0 ? mu_quest_get(&c->qs, c->progress.quest_ptr) : NULL;
}

void mu_quest_progress_onload(mu_quest_client *c)
{
    char a[512];
    invoke_text(c, NQP, "InitText", utf8_text(c, 0xe4, a, sizeof a));
    mu_quest_logf(&c->log, "invoke %s VisibleSelArrowBtn [0,0]", NQP);
}

int mu_quest_progress_set(mu_quest_client *c, int32_t quest)
{
    mu_quest_progress_window *w = &c->progress;
    mu_quest *q = mu_quest_get(&c->qs, quest);
    const mu_quest_dialogue *g = mu_quest_dialogue_get(&c->qs, quest);
    w->quest_ptr = q ? quest : -1;
    if (!q || !g)
        return 0;
    w->quest = quest;
    /* 0x00fe7599: the pages in string-index order into the deque (+0x80 = the copy) */
    pages_clear(w);
    if (g->npages) {
        w->pages = calloc((size_t)g->npages, sizeof *w->pages);
        for (int32_t i = 0; w->pages && i < g->npages; i++)
            w->pages[w->npages++] = strdup(g->pages[i] ? g->pages[i] : "");
    }
    mu_quest_progress_show_page(c);
    return 1;
}

static void progress_conditions(mu_quest_client *c)
{
    mu_quest *q = progress_quest(c);
    int complete = q && q->state == 2;
    mu_quest_line cond, rew;
    mu_quest_condition(&c->host, q, c->font_default, &cond);
    mu_quest_reward(&c->host, q, c->font_default, c->font, &rew);
    char l1[512], l2[512];
    const char *s[2] = {utf8_text(c, 0xaf9, l1, sizeof l1), utf8_text(c, 0xafa, l2, sizeof l2)};
    invoke_s(c, NQP, "SetUPCText", 2, s);
    char h1[4096], h2[4096], u1[8192], u2[8192];
    mu_quest_html_line(cond.text, cond.color, 0, 1, h1, sizeof h1);
    mu_quest_html_line(rew.text, rew.color, 0, 1, h2, sizeof h2);
    const char *t[2] = {mu_quest_utf8(c, h1, u1, sizeof u1), mu_quest_utf8(c, h2, u2, sizeof u2)};
    invoke_s(c, NQP, "SetConditionRewardText", 2, t);
    mu_quest_progress_button(c, complete);
}

void mu_quest_progress_button(mu_quest_client *c, int complete)
{
    char a[512];
    invoke_text(c, NQP, "InitText", utf8_text(c, complete ? 0x119f : 0x3ea, a, sizeof a));
}

int mu_quest_progress_show_page(mu_quest_client *c)
{
    mu_quest_progress_window *w = &c->progress;
    mu_quest *q = progress_quest(c);
    int32_t st = q ? q->state : 0;
    if (q && st != 0 && st != 4) {
        const mu_quest_dialogue *g = mu_quest_dialogue_get(&c->qs, w->quest);
        if (g)
            invoke_divide(c, NQP, st == 2 ? g->complete : g->progress, "SetQuestMentDivide", "#");
        progress_conditions(c);
        w->mode = 2;
    } else {
        if (!w->npages) {
            /* no page left: the accept request C1 F6 72 (accept[1], quest) */
            int32_t words[2] = {q && q->record ? q->record->accept[1] : 0, w->quest & 0xffff};
            send_f6(c, 0x72, words, 2, 1);
            return 0;
        }
        char *text = w->pages[w->page_first];
        w->page_first++;
        w->npages--;
        invoke_divide(c, NQP, text, "SetQuestMentDivide", "#");
        free(text);
        char buf[512], line[512];
        mu_qarg a[2] = {{0, 1, NULL}, {1, 0, mu_quest_text(c, (w->npages != 0) != (MU_QUEST_MUTATION == 3) ? 0x40d : 0x1521)}};
        mu_quest_sprintf(line, sizeof line, "%d. %s", a, 2);
        snprintf(w->select, sizeof w->select, "%s;", line);
        mu_qarg b[2] = {{0, 2, NULL}, {1, 0, mu_quest_text(c, 0x40e)}};
        mu_quest_sprintf(buf, sizeof buf, "%d. %s", b, 2);
        size_t n = strlen(w->select);
        snprintf(w->select + n, sizeof w->select - n, "%s;", buf);
        w->mode = 1;
    }
    mu_quest_logf(&c->log, "invoke %s SetUIType [%d]", NQP, w->mode);
    return 1;
}

void mu_quest_progress_refresh(mu_quest_client *c)
{
    mu_quest_progress_window *w = &c->progress;
    char q[8192];
    mu_quest_json(q, sizeof q, w->wrapped);
    mu_quest_logf(&c->log, "invoke %s SetQuestMent [%s,0]", NQP, q);
    char u[8192];
    invoke_text(c, NQP, "SetSelectBtnContent", mu_quest_utf8(c, w->select, u, sizeof u));
}

void mu_quest_progress_open(mu_quest_client *c)
{
    mu_quest_progress_window *w = &c->progress;
    char a[512], b[1024], d[512], e[256];
    const mu_quest_dialogue *g = mu_quest_dialogue_get(&c->qs, w->quest);
    utf8_text(c, 0xd84, a, sizeof a);
    mu_quest_utf8(c, g ? g->title : "", b, sizeof b);
    mu_quest *q = progress_quest(c);
    int32_t npc = q && q->record ? q->record->accept[5] : 0;
    const char *name = c->host.npc_name ? c->host.npc_name(c->host.user, npc) : NULL;
    mu_quest_utf8(c, name ? name : "", d, sizeof d);
    mu_quest_utf8(c, w->mode == 2 ? "" : c->hero_name, e, sizeof e);
    const char *s[4] = {a, b, d, e};
    invoke_s(c, NQP, "SetUIOpenText", 4, s);
    mu_quest_progress_refresh(c);
    mu_quest_logf(&c->log, "invoke %s SetPosLeftCenter []", NQP);
    show(c, NQP);
    w->visible = 1;
}

void mu_quest_progress_close(mu_quest_client *c)
{
    mu_quest_progress_window *w = &c->progress;
    w->quest_ptr = -1;
    pages_clear(w);
    w->quest = 0;
    uint8_t b[1] = {0x54};
    send_packet(c, b, 1, 0);
    hide(c, NQP);
    w->visible = 0;
}

int mu_quest_progress_select(mu_quest_client *c, int32_t index)
{
    if (c->progress.mode != 1)
        return 0;
    if (index == 0) {
        if (mu_quest_progress_show_page(c))
            mu_quest_progress_refresh(c);
    } else {
        mu_quest_progress_close(c);
    }
    return 1;
}

void mu_quest_progress_confirm(mu_quest_client *c)
{
    mu_quest *q = progress_quest(c);
    if (q && q->state == 2 && q->record) {
        int32_t words[3] = {q->record->accept[5], q->record->accept[1], c->progress.quest & 0xffff};
        send_f6(c, 0x74, words, 3, 1);
        return;
    }
    mu_quest_progress_close(c);
}

void mu_quest_progress_wrapped(mu_quest_client *c, const char *text)
{
    snprintf(c->progress.wrapped, sizeof c->progress.wrapped, "%s", text ? text : "");
}

int mu_quest_progress_callback(mu_quest_client *c, const char *name, double number, const char *text)
{
    if (!strcmp(name, "LeaveComplete")) {
        mu_quest_progress_close(c);
        return 1;
    }
    if (!strcmp(name, "onClickSelectBtn")) {
        mu_quest_progress_select(c, (int32_t)number);
        return 1;
    }
    if (!strcmp(name, "onClickbtnConfirm")) {
        mu_quest_progress_confirm(c);
        return 1;
    }
    if (!strcmp(name, "QuestDialogTextWidth")) {
        mu_quest_progress_wrapped(c, text);
        return 1;
    }
    return 0;
}

/* ---- npcdialogue's quest list ------------------------------------------------------------------- */

static const char *dialogue_word(mu_quest_client *c, int32_t id)
{
    return c->dialogue_word ? c->dialogue_word(c->host.user, id) : NULL;
}

/* 0x011ff794(dst, 1, 0x80, text, 500, 0, 0x3b, 0, 0): the text wrapped to 500 pixels with the dialogue font,
 * returning the line count.  MODELLED (font metrics): one line, the text cut to 0x7f bytes. */
static int32_t wrap_line(char *dst, const char *text)
{
    snprintf(dst, 0x80, "%s", text);
    return 1;
}

/* 0x00be8bdc(entries): the entries' line counts into pages of at most 13 lines (4 pages). */
static void dialog_pages(mu_quest_client *c, int32_t entries)
{
    mu_quest_dialog_list *d = &c->dialog;
    d->page = 0;
    d->page_count = 0;
    memset(d->page_lines, 0, sizeof d->page_lines);
    memset(d->page_entries, 0, sizeof d->page_entries);
    for (int32_t i = 0; i < entries && i < 21; i++) {
        d->page_entries[d->page_count]++;
        d->page_lines[d->page_count] += d->line_count[i];
        if (d->page_lines[d->page_count] > 13) {
            d->page_entries[d->page_count]--;
            d->page_lines[d->page_count] -= d->line_count[i];
            d->page_count++;
            if (d->page_count == 4)
                break;
            d->page_entries[d->page_count]++;
            d->page_lines[d->page_count] += d->line_count[i];
        }
    }
    mu_quest_logf(&c->log, "invoke %s VisibleSelArrowBtn [0,%d]", DLG, d->page_count < 1 ? 0 : 1);
}

/* 0x00be8724: SetDialogueMent(the movie's wrapped text, its page) and the current page's lines. */
static void dialog_ment(mu_quest_client *c, const char *wrapped, int32_t ment_page)
{
    mu_quest_dialog_list *d = &c->dialog;
    char q[8192];
    mu_quest_json(q, sizeof q, wrapped ? wrapped : "");
    mu_quest_logf(&c->log, "invoke %s SetDialogueMent [%s,%d]", DLG, q, ment_page);
    int32_t start = 0;
    for (int32_t i = 0; i < d->page && i < 4; i++)
        start += d->page_lines[i];
    char ss[4096] = "";
    for (int32_t i = 0; d->page < 4 && i < d->page_lines[d->page] && start + i < 21; i++) {
        size_t n = strlen(ss);
        snprintf(ss + n, sizeof ss - n, "%s;", d->lines[start + i]);
    }
    char u[8192];
    invoke_text(c, DLG, "SetSelectBtnContent", mu_quest_utf8(c, ss, u, sizeof u));
}

void mu_quest_dialog_quests(mu_quest_client *c, const int32_t *quests, int32_t n)
{
    mu_quest_dialog_list *d = &c->dialog;
    d->list_mode = 1;
    const char *text = dialogue_word(c, n < 1 ? 0x5de : 0x5dd);
    invoke_divide(c, DLG, text, "SetDialogueMentDivide", ";");
    memset(d->quests, 0, sizeof d->quests);
    memset(d->lines, 0, sizeof d->lines);
    memset(d->line_count, 0, sizeof d->line_count);
    int32_t total = 0;
    d->options = n + 1;
    /* the loop runs over the n entries; its "leave" branch (entry n, QuestWords 0x3ef) is never reached */
    for (int32_t i = 0; i < d->options - (MU_QUEST_MUTATION == 5 ? 0 : 1) && i < 20; i++) {
        if (quests[i] < 0)
            continue;               /* a NULL entry */
        const mu_quest *q = mu_quest_get(&c->qs, quests[i]);
        if (!q)
            continue;
        d->quests[i] = q->index;
        char buf[0x100];
        mu_qarg a = {0, i + 1, NULL};
        mu_quest_sprintf(buf, sizeof buf, "%d. [Q]", &a, 1);
        const mu_quest_dialogue *g = mu_quest_dialogue_get(&c->qs, q->index);
        const char *title = g ? g->title : (q->record ? q->record->name : "");
        size_t len = strlen(buf);
        snprintf(buf + len, sizeof buf - len, "%s", title ? title : "");
        if (total >= 21)
            break;
        d->line_count[i] = wrap_line(d->lines[total], buf);
        total += d->line_count[i];
        if (total > 0x15)
            break;
    }
    dialog_pages(c, d->options);
    dialog_ment(c, d->wrapped, d->ment_page);
    d->choice = 0;
    mu_quest_logf(&c->log, "invoke %s VisibleSelArrowBtn [0,0]", DLG);
}

int mu_quest_dialog_choice(mu_quest_client *c, int32_t choice, int *leave)
{
    mu_quest_dialog_list *d = &c->dialog;
    if (leave)
        *leave = 0;
    if (!d->list_mode)
        return 0;
    d->choice = choice;
    if (choice == d->options) {
        d->list_mode = 0;
        if (leave)
            *leave = 1;
        mu_quest_logf(&c->log, "dialogue state 0");     /* 0x00be86de(0): the dialogue's own state 0 */
        return 1;
    }
    int32_t quest = choice >= 1 && choice <= 20 ? d->quests[choice - 1] : 0;
    mu_quest_progress_set(c, quest);
    if (!c->progress.visible) {
        if (d->visible) {
            /* 0x00be8565: npcdialogue closes (C1 54, hide) */
            d->text_state = 0;
            d->list_mode = 0;
            uint8_t b[1] = {0x54};
            send_packet(c, b, 1, 0);
            hide(c, DLG);
            d->visible = 0;
        }
        mu_quest_progress_open(c);
    } else {
        mu_quest_progress_refresh(c);
    }
    return 1;
}

/* ---- MyQuestInfo -------------------------------------------------------------------------------- */

mu_quest_tab *mu_quest_info_tab(mu_quest_client *c, int32_t tab)
{
    if (tab < 0 || tab > 5)
        return NULL;
    for (int k = 0; k < 3; k++)
        if (c->info.tabs[k].category == tab)
            return &c->info.tabs[k];
    return NULL;
}

/* JSON of one {..} member list builder */
typedef struct jbuf {
    char s[32768];
    size_t n;
} jbuf;

static void jput(jbuf *j, const char *t)
{
    size_t l = strlen(t);
    if (j->n + l + 1 < sizeof j->s) {
        memcpy(j->s + j->n, t, l);
        j->n += l;
        j->s[j->n] = 0;
    }
}

static void jnum(jbuf *j, const char *name, double v)
{
    char t[128];
    snprintf(t, sizeof t, "\"%s\":%.17g", name, v);
    jput(j, t);
}

static void jstr(jbuf *j, const char *name, const char *v)
{
    char q[8192], t[8400];
    mu_quest_json(q, sizeof q, v);
    snprintf(t, sizeof t, "\"%s\":%s", name, q);
    jput(j, t);
}

static void jbool(jbuf *j, const char *name, int v)
{
    char t[128];
    snprintf(t, sizeof t, "\"%s\":%s", name, v ? "true" : "false");
    jput(j, t);
}

void mu_quest_info_onload(mu_quest_client *c)
{
    static const struct { const char *name; int32_t gt; } T[] = {
        {"Title", 0xd49}, {"TabTypeTitle", 0x153b}, {"QuestGiveUpButton", 0xb07}, {"QuestLeaveButton", 0x1420},
        {"Condition", 0xaf9}, {"Reward", 0xafa}, {"JobChange", 0xb05}, {"EventMap", 0xf2a},
        {"EventMapEnterTime", 0xd54}, {"EventMapEnterLevel", 0xd55}};
    jbuf j = {"", 0};
    jput(&j, "[{");
    for (size_t i = 0; i < sizeof T / sizeof T[0]; i++) {
        char a[1024];
        if (i)
            jput(&j, ",");
        jstr(&j, T[i].name, utf8_text(c, T[i].gt, a, sizeof a));
    }
    jput(&j, "}]");
    mu_quest_logf(&c->log, "value %s InitText %s", MQI, j.s);
    mu_quest_logf(&c->log, "invoke %s SetPosCenter []", MQI);
    mu_quest_info_tab_buttons(c);
}

/* 0x00be4922: CreateTabButtons with every tab of the map (0 guide 0x1479, 1 job change 0xb05, 2..4 the quest
 * tabs), in key order, each {Index, Name, NewQuest false} at its index. */
void mu_quest_info_tab_buttons(mu_quest_client *c)
{
    static const int32_t TITLE[5] = {0x1479, 0xb05, 0x1522, 0x1523, 0x1524};
    jbuf j = {"", 0};
    jput(&j, "[[");
    for (int t = 0; t < 5; t++) {
        char a[1024];
        if (t)
            jput(&j, ",");
        jput(&j, "{");
        jnum(&j, "Index", t);
        jput(&j, ",");
        jstr(&j, "Name", utf8_text(c, TITLE[t], a, sizeof a));
        jput(&j, ",");
        jbool(&j, "NewQuest", 0);
        jput(&j, "}");
    }
    jput(&j, "]]");
    mu_quest_logf(&c->log, "value %s CreateTabButtons %s", MQI, j.s);
}

/* 0x00be4732: UpdateQuestChecked: tabs 2..4, NewQuest when an active quest of the category is not seen. */
void mu_quest_info_checked(mu_quest_client *c)
{
    jbuf j = {"", 0};
    jput(&j, "[[");
    for (int32_t t = 2; t <= 4; t++) {
        int fresh = 0;
        const int32_t *a;
        size_t n = mu_quest_active(&c->qs, t, &a);
        for (size_t i = 0; i < n && !fresh; i++) {
            const mu_quest *q = mu_quest_get(&c->qs, a[i]);
            if (q && !q->seen)
                fresh = 1;
        }
        if (t > 2)
            jput(&j, ",");
        jput(&j, "{");
        jnum(&j, "TabType", t);
        jput(&j, ",");
        jbool(&j, "NewQuest", fresh);
        jput(&j, "}");
    }
    jput(&j, "]]");
    mu_quest_logf(&c->log, "value %s UpdateQuestChecked %s", MQI, j.s);
}

/* tab +0x18 (0x00d4f37c) */
static void tab_visible(mu_quest_client *c, int a, int b)
{
    mu_quest_logf(&c->log, "invoke %s VisibleContent [%d,%d]", MQI, a, b);
}

void mu_quest_tab_list(mu_quest_client *c, mu_quest_tab *t)
{
    jbuf j = {"", 0};
    jput(&j, "[[");
    const int32_t *a;
    size_t n = mu_quest_active(&c->qs, t->category, &a);
    if (n) {
        for (size_t i = 0; i < n; i++) {
            const mu_quest *q = mu_quest_get(&c->qs, a[i]);
            if (!q)
                continue;
            const mu_quest_dialogue *g = mu_quest_dialogue_get(&c->qs, q->index);
            char name[1024], cut[0x40], u[2048];
            mu_qarg args[2] = {{0, (int32_t)i + 1, NULL}, {1, 0, g ? g->title : (q->record ? q->record->name : "")}};
            mu_quest_sprintf(name, sizeof name, "%d. %s", args, 2);
            /* 0x011ff6fc(dst, 0x40, src): MODELLED (the client fits the text to 64 bytes with its font) */
            snprintf(cut, sizeof cut, "%s", name);
            if (i)
                jput(&j, ",");
            jput(&j, "{");
            jnum(&j, "Index", (double)(uint32_t)i);
            jput(&j, ",");
            jnum(&j, "QuestIndex", q->index);
            jput(&j, ",");
            jstr(&j, "Name", mu_quest_utf8(c, cut, u, sizeof u));
            jput(&j, ",");
            jbool(&j, "NewQuest", !q->seen);
            jput(&j, "}");
        }
    } else {
        /* no active quest: the base text (0x00fdc814, GlobalText 0xb09) as the only entry */
        snprintf(t->base_text, sizeof t->base_text, "%s", mu_quest_text(c, 0xb09));
        tab_visible(c, 0, 0);
        char ss[512], u[2048];
        snprintf(ss, sizeof ss, "%s\n", t->base_text);
        jput(&j, "{");
        jnum(&j, "Index", 0);
        jput(&j, ",");
        jnum(&j, "QuestIndex", 0);
        jput(&j, ",");
        jstr(&j, "Name", mu_quest_utf8(c, ss, u, sizeof u));
        jput(&j, ",");
        jbool(&j, "NewQuest", 0);
        jput(&j, "}");
    }
    jput(&j, "]]");
    mu_quest_logf(&c->log, "value %s SetMyQuestList %s", MQI, j.s);
}

void mu_quest_tab_init(mu_quest_client *c, mu_quest_tab *t)
{
    snprintf(t->base_text, sizeof t->base_text, "%s", mu_quest_text(c, 0xb09));
    tab_visible(c, 0, 0);
    mu_quest_logf(&c->log, "invoke %s SetDisableGiveUpBtn [1]", MQI);
    mu_quest_tab_list(c, t);
}

static void tab_conditions(mu_quest_client *c, mu_quest_tab *t, int32_t quest)
{
    char l1[512], l2[512];
    const char *s[2] = {utf8_text(c, 0xaf9, l1, sizeof l1), utf8_text(c, 0xafa, l2, sizeof l2)};
    invoke_s(c, MQI, "SetUPCText", 2, s);
    char c1[8192] = "", r1[8192] = "";
    if (mu_quest_is_active(&c->qs, t->category, quest)) {
        const mu_quest *q = mu_quest_get(&c->qs, quest);
        mu_quest_line cond, rew;
        mu_quest_condition(&c->host, q, c->font_default, &cond);
        mu_quest_reward(&c->host, q, c->font_default, c->font, &rew);
        char h1[4096], h2[4096];
        mu_quest_html_line(cond.text, cond.color, 0, 1, h1, sizeof h1);
        mu_quest_html_line(rew.text, rew.color, 0, 1, h2, sizeof h2);
        mu_quest_utf8(c, h1, c1, sizeof c1);
        mu_quest_utf8(c, h2, r1, sizeof r1);
    }
    const char *u[2] = {c1, r1};
    invoke_s(c, MQI, "SetConditionReward", 2, u);
}

static void tab_buttons(mu_quest_client *c, mu_quest_tab *t, int32_t quest)
{
    int give = 0, move = 0;
    int32_t label = 0x1420;
    if (mu_quest_is_active(&c->qs, t->category, quest)) {
        const mu_quest *q = mu_quest_get(&c->qs, quest);
        int done = q && q->state == 2;
        give = MU_QUEST_MUTATION == 6 ? 1 : !done;
        move = 1;
        if (done)
            label = q->record && q->record->accept[4] == 2 ? 0x1547 : 0x141f;
    }
    char a[512], u[8192];
    mu_quest_json(u, sizeof u, utf8_text(c, label, a, sizeof a));
    mu_quest_logf(&c->log, "invoke %s UpdateQuestButtonState [%s,%s,%s]", MQI, give ? "true" : "false",
                  move ? "true" : "false", u);
}

void mu_quest_tab_show(mu_quest_client *c, mu_quest_tab *t, int32_t quest)
{
    mu_quest *q = mu_quest_get(&c->qs, quest);
    if (q && !q->seen) {
        q->seen = 1;
        int32_t words[2] = {q->record ? q->record->accept[1] : 0, quest & 0xffff};
        send_f6(c, 0x77, words, 2, 0);
        mu_quest_info_checked(c);
    }
    tab_conditions(c, t, quest);
    tab_buttons(c, t, quest);
    tab_visible(c, 1, 1);
}

void mu_quest_tab_select(mu_quest_client *c, mu_quest_tab *t, int32_t quest)
{
    t->selected = quest;
    /* 0x00d501c8: SetMyQuestDivide(the summary, or the title when the summary is empty) */
    const mu_quest_dialogue *g = mu_quest_dialogue_get(&c->qs, quest);
    if (!g)
        invoke_divide(c, MQI, "", "SetMyQuestDivide", ";");
    else
        invoke_divide(c, MQI, g->summary && *g->summary ? g->summary : g->title, "SetMyQuestDivide", ";");
    mu_quest_tab_show(c, t, quest);
}

void mu_quest_tab_action(mu_quest_client *c, mu_quest_tab *t, int32_t quest)
{
    if (!mu_quest_is_active(&c->qs, t->category, quest))
        return;
    mu_quest *q = mu_quest_get(&c->qs, quest);
    if (!q || !q->record)
        return;
    if (q->state == 2) {
        /* 0x00d5060e: C1 F6 7D (accept[1], quest) when accept[4] == 2, else C1 F6 74 (0, accept[1], quest) */
        if (q->record->accept[4] == 2) {
            int32_t w[2] = {q->record->accept[1], q->index & 0xffff};
            send_f6(c, 0x7d, w, 2, 0);
        } else {
            int32_t w[3] = {0, q->record->accept[1], q->index & 0xffff};
            send_f6(c, 0x74, w, 3, 1);
        }
    } else {
        /* 0x00d5029b: the move to the quest's target (hero position, world, path or the move request):
         * static only, not reconstructed */
        mu_quest_logf(&c->log, "move %d (not played)", q->index);
    }
}

void mu_quest_info_open(mu_quest_client *c)
{
    mu_quest_info_window *w = &c->info;
    if (w->first_open) {
        w->first_open = 0;
        w->tab = 0;
    }
    mu_quest_logf(&c->log, "invoke %s SetUIType [%d]", MQI, w->tab);
    mu_quest_logf(&c->log, "classicquest -1");
    mu_quest_tab *t = mu_quest_info_tab(c, w->tab);
    if (t)
        mu_quest_tab_init(c, t);
    else
        mu_quest_logf(&c->log, "tab %d init (not played)", w->tab);
    mu_quest_info_checked(c);
    show(c, MQI);
    w->visible = 1;
}

void mu_quest_info_close(mu_quest_client *c)
{
    mu_quest_info_window *w = &c->info;
    /* the current tab's vtable +8: nothing for the quest tabs (0x00d4f2d5 returns 1) */
    if (!mu_quest_info_tab(c, w->tab))
        mu_quest_logf(&c->log, "tab %d close (not played)", w->tab);
    uint8_t b[1] = {0x54};
    send_packet(c, b, 1, 0);
    hide(c, MQI);
    w->visible = 0;
}

void mu_quest_info_select_tab(mu_quest_client *c, int32_t tab)
{
    c->info.tab = tab;
    mu_quest_tab *t = mu_quest_info_tab(c, tab);
    if (t)
        mu_quest_tab_init(c, t);
    else
        mu_quest_logf(&c->log, "tab %d init (not played)", tab);
}

void mu_quest_tab_text_width(mu_quest_client *c, mu_quest_tab *t, int32_t lines, const char *text)
{
    (void)t;
    (void)lines;               /* the tab keeps the line count (+0x88) and the text (+0x8c) */
    char u[8192];
    invoke_text(c, MQI, "SetMyQuest", mu_quest_utf8(c, text ? text : "", u, sizeof u));
}

int mu_quest_info_callback(mu_quest_client *c, const char *name, const double *v, int n, const char *text)
{
    mu_quest_tab *t = mu_quest_info_tab(c, c->info.tab);
    if (!strcmp(name, "QuestTextWidth")) {
        if (t)
            mu_quest_tab_text_width(c, t, n >= 1 ? (int32_t)v[0] : 0, text);
        return 1;
    }
    if (!strcmp(name, "LeaveComplete") || !strcmp(name, "CloseWindow")) {
        mu_quest_info_close(c);
        return 1;
    }
    if (!strcmp(name, "OnSelectTab") && n >= 1) {
        mu_quest_info_select_tab(c, (int32_t)v[0]);
        return 1;
    }
    if (!strcmp(name, "OnSelectQuest") && n >= 2) {
        if (t)
            mu_quest_tab_select(c, t, (int32_t)v[1]);
        return 1;
    }
    if (!strcmp(name, "onClickbtnLeaveQuestImmediately")) {
        if (t)
            mu_quest_tab_action(c, t, t->selected);
        return 1;
    }
    if (!strcmp(name, "onClickbtnQuestGiveUp")) {
        /* a message box (id 0x2d); its OK (0x00be436d(0x2d, 0)) sends C1 F6 73 (accept[1], quest) */
        mu_quest_logf(&c->log, "msgbox giveup 0x2d");
        return 1;
    }
    return 0;
}

/* The give-up message box's OK (0x00be436d(0x2d, 0)). */
void mu_quest_info_giveup_ok(mu_quest_client *c)
{
    mu_quest_tab *t = mu_quest_info_tab(c, c->info.tab);
    const mu_quest *q = t ? mu_quest_get(&c->qs, t->selected) : NULL;
    if (q && q->record) {
        int32_t w[2] = {q->record->accept[1], q->index & 0xffff};
        send_f6(c, 0x73, w, 2, 1);
    }
}


/* ---- client ------------------------------------------------------------------------------------- */

int mu_quest_client_init(mu_quest_client *c, const mu_quest_data *data, const mu_quest_host *host)
{
    memset(c, 0, sizeof *c);
    if (host)
        c->host = *host;
    if (!c->host.data)
        c->host.data = data;
    if (mu_quest_system_build(&c->qs, data))
        return -1;
    c->progress.quest_ptr = -1;
    c->progress.mode = -1;
    c->info.first_open = 1;
    static const int32_t TITLE[3] = {0x1522, 0x1523, 0x1524};
    for (int k = 0; k < 3; k++) {
        c->info.tabs[k].category = k + 2;
        snprintf(c->info.tabs[k].title, sizeof c->info.tabs[k].title, "%s", mu_quest_text(c, TITLE[k]));
    }
    return 0;
}

void mu_quest_client_free(mu_quest_client *c)
{
    if (!c)
        return;
    pages_clear(&c->progress);
    mu_quest_system_free(&c->qs);
    mu_quest_log_free(&c->log);
}
