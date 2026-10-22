/* The class-upgrade ("classic") quests (NATIVE-QUEST-002); see quest.h.
 *
 * The classic quest manager [0x01d1e71c] (0x30dd0 bytes, ctor 0x009f47b2) holds Data\Local\Quest.bmd's 200
 * records of 1000 bytes at +0x14 (loader 0x009f4866: each record read and decoded with 0x00976855):
 *   record +0 s16 condition count, +2 s16 request count, +4 u16 NPC class, +6 name, +0x28 16 conditions of 0x28
 *   bytes (+1 type: 1 item, 2 monster; +2 u16 item group / monster; +4 item index; +5 item level; +8 s32 count;
 *   +0xc the request class compared with the requests' +1; +0xd + class: allowed; +0x1e s16 texts[4] (the
 *   Dialog(kor) indices by state)), +0x2a8 16 requests of 0x14 bytes (+1 class (-1 any); +2 u16 a quest that must
 *   be complete (-1 none); +4 / +6 u16 min / max level (0 none); +0xc s32 zen; +0x10 s16 the refusal text).
 * The manager's state: +0x10 class (low nibble, 0xff none), +0x30d54 50 bytes of 2-bit quest states (0 not
 * taken, 1 in progress, 2 complete, 3 can take), +0x30d86 the current quest, +0x30d87 the highest one, +0x30d8a the
 * Dialog index to show, +0x30d8c the state the manager acts on, +0x30d90 the zen, +0x30d98 / +0x30dac five
 * monsters and their kills.  The dialogue text and answers go to globals: [0x01cf17b0] the dialogue, 7 lines of
 * 0x26 bytes at 0x0bdc5b98 (count 0x0bdc5b94), the answers at 0x0bdc5ce8 (count 0x0bdc5ce4).
 *
 * The windows: NpcJobChangeQuest (manager + 0x108, 0x9c bytes, ctor 0x00beb7b4, vtable 0x01a95570) and
 * MyQuestInfo's tab 1 (ctor 0x00d4e90b, vtable 0x01aa4d48).  Packets: C1 C0 (the quest states, 0x01278f3a), C1 A1
 * (a quest's state, 0x0127a1db), C1 A4 (the kills, 0x01278f6c), C1 F6 1C (kills of the current quest,
 * 0x0124cbb0); requests C1 B3 (quest, 1) accept / complete, C1 F6 1C (the kills), C1 54 (closed), C1 66 35. */
#include "quest_internal.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define NJCQ "NpcJobChangeQuest"
#define MQI "MyQuestInfo"
#define REC 1000
#define LINE 0x26

typedef struct mu_classic {
    uint8_t cls;                          /* +0x10 */
    uint8_t states[50];                   /* +0x30d54 */
    uint8_t current, top, f88, f89;       /* +0x30d86 .. +0x30d89 */
    int16_t text;                         /* +0x30d8a */
    uint8_t state;                        /* +0x30d8c */
    int32_t zen;                          /* +0x30d90 */
    uint8_t pending;                      /* +0x30d95: the class comes with the next state change */
    int32_t monsters[5], kills[5];        /* +0x30d98, +0x30dac */
    /* the dialogue globals */
    int32_t dialog;                       /* [0x01cf17b0] */
    int32_t nlines;                       /* [0x0bdc5b94] */
    char lines[7][LINE];                  /* 0x0bdc5b98 */
    int32_t nanswers;                     /* [0x0bdc5ce4] */
    char answers[10][LINE];               /* 0x0bdc5ce8 */
    uint8_t first;                        /* [0x01d1de8c] */
    /* NpcJobChangeQuest's handler */
    uint8_t w_quest, w_state;             /* +0x78, +0x79 */
    int32_t w_items, w_mode;              /* +0x7c, +0x80 */
    int visible;
    /* tab 1's text (base +4: one line of 0x80, count +0x88) */
    char tab_text[0x80];
    int32_t tab_lines;
} mu_classic;

/* ---- data ---------------------------------------------------------------------------------------- */

long mu_classic_load(mu_quest_data *d, const uint8_t *file, size_t size)
{
    if (!d || !file)
        return -1;
    free(d->classic);
    d->classic = calloc(1, 200 * REC);
    if (!d->classic)
        return -1;
    static const uint8_t key[3] = {0xfc, 0xcf, 0xab};
    /* 0x009f4866: 200 reads of 1000 bytes (a short read leaves the rest zero), each decoded from phase 0 */
    for (size_t r = 0; r < 200; r++) {
        uint8_t *rec = d->classic + r * REC;
        size_t off = r * REC, n = off < size ? (size - off < REC ? size - off : REC) : 0;
        if (n)
            memcpy(rec, file + off, n);
        for (int i = 0; i < REC; i++)
            rec[i] ^= key[i % 3];
    }
    return 200;
}

static const uint8_t *record(const mu_quest_client *c, int q)
{
    const uint8_t *base = c->qs.data ? c->qs.data->classic : NULL;
    return base && q >= 0 && q < 200 ? base + (size_t)q * REC : NULL;
}

static int16_t s16(const uint8_t *p, int off)
{
    return (int16_t)(p[off] | p[off + 1] << 8);
}

static uint16_t u16(const uint8_t *p, int off)
{
    return (uint16_t)(p[off] | p[off + 1] << 8);
}

static int32_t s32(const uint8_t *p, int off)
{
    return (int32_t)((uint32_t)p[off] | (uint32_t)p[off + 1] << 8 | (uint32_t)p[off + 2] << 16 |
                     (uint32_t)p[off + 3] << 24);
}

#define ACT(k) (0x28 + (k) * 0x28)
#define REQ(k) (0x2a8 + (k) * 0x14)

/* Dialog(kor): the text (0x010eb205), the answers' count (0x010eb349), text (0x010eb3a8), action (0x010eb258)
 * and next dialogue (0x010eb2d1); a missing dialogue gives the table's default ("no dialog", no answers). */
static const mu_dialog *dialog_find(const mu_quest_client *c, int32_t key)
{
    const mu_quest_data *d = c->qs.data;
    size_t lo = 0, hi = d ? d->ndialogs : 0;
    while (lo < hi) {
        size_t mid = (lo + hi) / 2;
        if (d->dialogs[mid].key < key)
            lo = mid + 1;
        else
            hi = mid;
    }
    return d && lo < d->ndialogs && d->dialogs[lo].key == key ? &d->dialogs[lo] : NULL;
}

static const char *dialog_text(const mu_quest_client *c, int32_t key)
{
    const mu_dialog *g = dialog_find(c, key);
    return g ? (g->text ? g->text : "") : "no dialog";
}

static int32_t dialog_answers(const mu_quest_client *c, int32_t key)
{
    const mu_dialog *g = dialog_find(c, key);
    return g ? g->nanswers : 0;
}

/* ---- the client's helpers ------------------------------------------------------------------------- */

/* 0x01859f23(text, lines, max_lines, length): lines cut at `length` bytes, moved back to the last blank when it is
 * fewer than min(length / 2, 10) bytes back; returns the line count. */
static int cut_text(const char *text, char *dst, int max_lines, int length)
{
    const char *start = text, *blank = NULL, *p;
    char *out = dst;
    int line = 0;
    for (p = text; *p;) {
        int k = 1;                        /* _mbclen */
        if (length <= (int)(p + k - start)) {
            if (blank) {
                int back = length / 2 < 0xb ? length / 2 : 10;
                if ((int)(p - blank) < back) {
                    out -= p - 1 - blank;
                    p = blank + 1;
                }
            }
            start = p;
            *out = 0;
            if (max_lines - 1 <= line)
                break;
            line++;
            out = dst + line * length;
            blank = NULL;
        }
        memcpy(out, p, (size_t)k);
        if (*p == ' ')
            blank = p;
        out += k;
        p += k;
    }
    *out = 0;
    return line + 1;
}

static const char *html_color(int32_t color)
{
    static const char *const TABLE[22] = {
        "#FFFFFF", "#7FB2FF", "#FF3319", "#FFCC19", "#19FF7F", "#A00000", "#FF19FF", "#0000A0", "#A06600",
        "#00FF00", "#666666", "#CC7FCC", "#B266FF", "#E56B0A", "#800080", "#FFFF00", "#00B0F0", "#00B050",
        "#CCFF00", "#00FFFF", "#BCBCBC", "#C1C469"};
    return (uint32_t)color <= 0x15 ? TABLE[color] : "#FFFFFF";
}

/* 0x00ab4dc0(out, text, colour index, bold) */
static void html_index(const char *text, int32_t color, int bold, char *out, size_t cap)
{
    out[0] = 0;
    if (!text || !*text || !strcmp(text, "\n"))
        return;
    char esc[2048];
    size_t n = 0;
    for (const char *p = text; *p && n + 5 < sizeof esc; p++) {
        if (*p == '<') {
            memcpy(esc + n, "&lt;", 4);
            n += 4;
        } else {
            esc[n++] = *p;
        }
    }
    esc[n] = 0;
    if (bold == 1)
        snprintf(out, cap, "<font color='%s'><b>%s</b></font><br>", html_color(color), esc);
    else
        snprintf(out, cap, "<font color='%s'>%s</font><br>", html_color(color), esc);
}

static const char *utf8(const mu_quest_client *c, const char *s, char *buf, size_t cap)
{
    return mu_quest_utf8(c, s, buf, cap);
}

static int master_class(uint8_t cls)       /* 0x0139d89f */
{
    int k = cls & 0xf;
    return k == 3 || k == 4 || k == 6 || k == 7;
}

/* ---- the manager ---------------------------------------------------------------------------------- */

static mu_classic *cq(mu_quest_client *c)
{
    if (!c->classic) {
        c->classic = calloc(1, sizeof *c->classic);
        if (c->classic) {
            c->classic->cls = 0xff;      /* 0x009f47b2 (the kills stay as allocated: zero here) */
            c->classic->w_mode = -1;     /* NpcJobChangeQuest's ctor 0x00beb7b4 */
        }
    }
    return c->classic;
}

void mu_classic_free(mu_quest_client *c)
{
    if (!c)
        return;
    free(c->classic);
    c->classic = NULL;
}

int mu_classic_state_of(mu_quest_client *c, int32_t quest)            /* 0x009f4bf3 */
{
    mu_classic *m = cq(c);
    int32_t r = quest % 4;
    int32_t at = quest / 4;
    if (!m || at < 0 || at >= 50)
        return 0;
    return (m->states[at] >> ((r * 2) & 0x1f)) & (MU_QUEST_MUTATION == 11 ? 1 : 3);
}

int mu_classic_state(mu_quest_client *c, int32_t quest)               /* 0x009f4d91 */
{
    mu_classic *m = cq(c);
    if (!m)
        return 0;
    int32_t q = quest == -1 ? m->current : quest;
    int v = mu_classic_state_of(c, q);
    if (quest == -1)
        m->state = (uint8_t)v;
    return v;
}

static int allowed(const mu_classic *m, const uint8_t *rec, int k)
{
    return rec[ACT(k) + 0xd + m->cls] != 0;
}

/* the windows ask with the hero's class (hero + 0x12, 0x0095f5cc), not the manager's */
static int allowed_hero(const mu_quest_client *c, const uint8_t *rec, int k)
{
    return rec[ACT(k) + 0xd + (c->hero_class & 0xf)] != 0;
}

int32_t mu_classic_lacking(mu_quest_client *c, int32_t code, int32_t count, int32_t level)   /* 0x009f52ab */
{
    int32_t have = c->host.classic_item ? c->host.classic_item(c->host.user, code, count, level) : 0;
    return count - have < 0 ? 0 : count - have;
}

int32_t mu_classic_kills(mu_quest_client *c, int32_t monster)         /* 0x009f52fe */
{
    mu_classic *m = cq(c);
    for (int i = 0; m && i < 5; i++)
        if (monster == m->monsters[i])
            return m->kills[i];
    return 0;
}

static int32_t answer_state(mu_quest_client *c, uint8_t answer);

/* 0x009f436e: the first allowed condition's text for `which`; none: the previous quest's */
static int16_t text_for(mu_quest_client *c, const uint8_t *rec, int which)
{
    mu_classic *m = cq(c);
    for (int k = 0; k < s16(rec, 0); k++)
        if (allowed(m, rec, k))
            return s16(rec, ACT(k) + 0x1e + which * 2);
    m->current = (uint8_t)(m->current - 1);
    answer_state(c, 0xff);
    return m->text;
}

/* 0x009f43f0(record, check_zen): the requests of the allowed conditions' class */
static int requests_ok(mu_quest_client *c, const uint8_t *rec, int check_zen)
{
    mu_classic *m = cq(c);
    for (int k = 0; k < s16(rec, 0); k++) {
        if (!allowed(m, rec, k))
            continue;
        int8_t want = (int8_t)rec[ACT(k) + 0xc];
        for (int j = 0; j < s16(rec, 2); j++) {
            int8_t cls = (int8_t)rec[REQ(j) + 1];
            if (cls != want && cls != -1)
                continue;
            int16_t need_quest = s16(rec, REQ(j) + 2);
            if (need_quest != -1 && mu_classic_state_of(c, need_quest) != 2) {
                m->text = s16(rec, REQ(j) + 0x10);
                m->state = 5;
                return 0;
            }
            if (u16(rec, REQ(j) + 4) != 0 && c->hero_level_total < u16(rec, REQ(j) + 4)) {
                m->text = s16(rec, REQ(j) + 0x10);
                m->state = 5;
                return 0;
            }
            if (u16(rec, REQ(j) + 6) != 0 && (int32_t)u16(rec, REQ(j) + 6) < c->hero_level) {
                m->text = s16(rec, REQ(j) + 0x10);
                m->state = 5;
                return 0;
            }
            int32_t zen = s32(rec, REQ(j) + 0xc);
            if (zen == 0) {
                m->zen = 0;
            } else if (!check_zen) {
                m->zen = zen;
            } else {
                m->zen = zen;
                if (c->money < (uint32_t)m->zen) {
                    m->text = s16(rec, REQ(j) + 0x10);
                    m->state = 5;
                    return 0;
                }
            }
        }
    }
    return 1;
}

/* 0x009f4654: every allowed condition met (items in the inventory, the kills) */
static int conditions_met(mu_quest_client *c, const uint8_t *rec)
{
    mu_classic *m = cq(c);
    for (int k = 0; k < s16(rec, 0); k++) {
        if (!allowed(m, rec, k))
            continue;
        uint8_t type = rec[ACT(k) + 1];
        if (type == 1) {
            int32_t code = u16(rec, ACT(k) + 2) * 0x200 + rec[ACT(k) + 4];
            if (mu_classic_lacking(c, code, s32(rec, ACT(k) + 8), rec[ACT(k) + 5])) {
                m->text = text_for(c, rec, 1);
                return 0;
            }
        } else if (type == 2) {
            int found = 0;
            for (int i = 0; i < 5; i++)
                if (m->monsters[i] == (int32_t)u16(rec, ACT(k) + 2) && s32(rec, ACT(k) + 8) <= m->kills[i]) {
                    found = 1;
                    break;
                }
            if (!found) {
                m->text = text_for(c, rec, 1);
                return 0;
            }
        }
    }
    return 1;
}

/* 0x009f4244(answer): the state the manager acts on and the Dialog index it shows */
static int32_t answer_state(mu_quest_client *c, uint8_t answer)
{
    mu_classic *m = cq(c);
    if (c->hero_class != 0xff && m->pending) {
        m->pending = 0;
        m->cls = c->hero_class & 0xf;
    }
    const uint8_t *rec = record(c, m->current);
    if (answer == 0xff)
        mu_classic_state(c, -1);
    else
        m->state = answer;
    if (!rec)
        return m->state;
    if (m->state == 1) {
        if (conditions_met(c, rec)) {
            m->text = text_for(c, rec, 2);
            m->state = 1;
        }
    } else if (m->state == 2) {
        m->text = text_for(c, rec, 3);
    } else if (m->state == 3 && requests_ok(c, rec, 0)) {
        m->text = text_for(c, rec, 0);
    }
    return m->state;
}

int32_t mu_classic_answer(mu_quest_client *c, int32_t answer)         /* 0x009f4244 */
{
    return answer_state(c, (uint8_t)answer);
}

/* 0x009f4fc8(dialog): the dialogue's text (7 lines) and its answers ("%d) %s"), or "Conversation is over" */
void mu_classic_text(mu_quest_client *c, int32_t dialog)
{
    mu_classic *m = cq(c);
    m->dialog = dialog;
    memset(m->lines, 0, sizeof m->lines);
    m->nlines = cut_text(dialog_text(c, dialog), &m->lines[0][0], 7, LINE);
    m->nanswers = 0;
    memset(m->answers, 0, sizeof m->answers);
    int32_t last = 0, n = dialog_answers(c, dialog);
    const mu_dialog *g = dialog_find(c, dialog);
    for (int32_t k = 0; k < n && k < 10; k++) {
        char buf[512];
        snprintf(buf, sizeof buf, "%d) %s", k + 1, g && g->answers[k].text ? g->answers[k].text : "");
        cut_text(buf, m->answers[k], 1, LINE);
        m->nanswers++;
        last = k;
    }
    if (n == 0) {
        char buf[512];
        snprintf(buf, sizeof buf, "%d) %s", last + 1, mu_quest_text(c, 0x261));
        snprintf(m->answers[0], LINE, "%s", buf);
        m->nanswers = 1;
    }
}

void mu_classic_show(mu_quest_client *c, int32_t quest)               /* 0x009f4cb2 */
{
    mu_classic *m = cq(c);
    if (quest != -1)
        m->current = (uint8_t)quest;
    answer_state(c, 0xff);
    mu_classic_text(c, m->text);
}

void mu_classic_show_top(mu_quest_client *c, int32_t quest)           /* 0x009f4c3f */
{
    mu_classic *m = cq(c);
    if (quest != -1)
        m->current = (uint8_t)quest;
    m->f89 = 2;
    uint8_t keep = m->current;
    m->current = m->top;
    answer_state(c, 0xff);
    mu_classic_text(c, m->text);
    m->current = keep;
}

static void hero_byte_29(mu_quest_client *c)
{
    c->hero_flag29 = mu_classic_state_of(c, 3) == 2;
}

/* C1 C0 (0x01278f3a -> 0x009f4a08(states +4, count +3, the hero's class)) */
void mu_classic_receive_states(mu_quest_client *c, const uint8_t *p, size_t size)
{
    mu_classic *m = cq(c);
    if (!m || size < 4)
        return;
    int32_t count = p[3];
    m->pending = 1;
    m->first = 0;
    m->cls = c->hero_class & 0xf;
    memset(m->states, 0, sizeof m->states);
    size_t n = (size_t)(count / 4 + 1);
    if (n > sizeof m->states)
        n = sizeof m->states;
    memcpy(m->states, p + 4, size >= 4 + n ? n : size - 4);
    int32_t i;
    if (m->cls == 1) {
        for (i = 0; i < count && mu_classic_state(c, i) == 2; i++)
            ;
    } else if (!master_class(m->cls)) {
        for (i = 0; i < count && (i == 3 || mu_classic_state(c, i) == 2); i++)
            ;
    } else {
        for (i = 4; i < count && mu_classic_state(c, i) == 2; i++)
            ;
    }
    m->current = m->top = (uint8_t)i;
    hero_byte_29(c);
}

/* C1 A1 (0x0127a1db: 0x009f4b61(quest +3, state byte +4), then the windows) */
void mu_classic_receive_state(mu_quest_client *c, const uint8_t *p, size_t size)
{
    mu_classic *m = cq(c);
    if (!m || size < 5)
        return;
    uint8_t q = p[3];
    if (q >= 200)
        return;                         /* malformed packet: the manager has 200 packed states */
    m->current = q;
    m->top = q <= m->top ? m->top : q;
    m->states[m->current >> 2] = p[4];
    hero_byte_29(c);
    mu_quest_logf(&c->log, "classic refresh");      /* 0x00f2bb92()->0x00f2b53d, manager 0x00ac9c74 */
    mu_classic_open(c);
}

/* C1 A4 (0x01278f6c -> 0x009f4e61(+8)): five (monster, kills) pairs */
void mu_classic_receive_kills(mu_quest_client *c, const uint8_t *p, size_t size)
{
    mu_classic *m = cq(c);
    if (!m || size < 8 + 40)
        return;
    for (int i = 0; i < 5; i++) {
        m->monsters[i] = s32(p, 8 + i * 8);
        m->kills[i] = s32(p, 12 + i * 8);
    }
}

/* C1 F6 1C (0x0124cbb0): kills of the current quest (+4 quest, +5 count, u16 monster +6 / count +8 per 4 bytes) */
void mu_classic_receive_kill_list(mu_quest_client *c, const uint8_t *p, size_t size)
{
    mu_classic *m = cq(c);
    if (!m || size < 6)
        return;
    if (p[4] == m->current) {
        for (int i = 0; i < p[5] && (size_t)(8 + i * 4) < size; i++) {
            if (i < 5) {
                m->monsters[i] = u16(p, 6 + i * 4);
                m->kills[i] = p[8 + i * 4];
            }
        }
    }
    if (c->info.visible)
        mu_quest_logf(&c->log, "MyQuestInfo refresh");   /* 0x00be4901 */
}

/* ---- MyQuestInfo tab 1 (0x00d4dd38) --------------------------------------------------------------- */

void mu_classic_tab_refresh(mu_quest_client *c)       /* 0x00d4e45c, tab vtable +0x30: no F6 1C request */
{
    mu_classic *m = cq(c);
    if (!m)
        return;
    if (mu_classic_state_of(c, m->current) != 1)
        return;
    const uint8_t *rec = record(c, m->current);
    if (!rec)
        return;
    int32_t row = 0;
    for (int k = 0; k < s16(rec, 0); k++) {
        if (!allowed_hero(c, rec, k))
            continue;
        uint8_t type = rec[ACT(k) + 1];
        if (type == 1) {
            int32_t code = u16(rec, ACT(k) + 2) * 0x200 + rec[ACT(k) + 4];
            int32_t count = s32(rec, ACT(k) + 8), level = rec[ACT(k) + 5];
            int32_t color = mu_classic_lacking(c, code, count, level) ? 2 : 9;
            char name[256] = "", line[512], html[1024], u[1024];
            if (c->host.item_level_name)
                c->host.item_level_name(c->host.user, code, level, name, sizeof name);
            snprintf(line, sizeof line, "%s x %d", name, count);
            html_index(line, color, 0, html, sizeof html);
            mu_quest_invoke(c, MQI, "SetJobChangeItem", "%d %s", row, utf8(c, html, u, sizeof u));
            row++;
        } else if (type == 2) {
            int32_t mon = u16(rec, ACT(k) + 2), need = s32(rec, ACT(k) + 8);
            int32_t have = mu_classic_kills(c, mon), color = 9;
            if (have < need)
                color = 2;
            else
                have = need;
            const char *name = c->host.npc_name ? c->host.npc_name(c->host.user, mon) : NULL;
            char line[512], html[1024], u[1024];
            snprintf(line, sizeof line, "%s x %d/%d", name ? name : "", have, need);
            html_index(line, color, 0, html, sizeof html);
            mu_quest_invoke(c, MQI, "SetJobChangeMob", "%d %s", row, utf8(c, html, u, sizeof u));
            row++;
        }
    }
}

void mu_classic_tab_init(mu_quest_client *c)
{
    mu_classic *m = cq(c);
    if (!m)
        return;
    uint8_t b[2] = {0xf6, 0x1c};
    mu_quest_send(c, b, 2, 0, 0);                       /* 0x00d4ef4f */
    const uint8_t *top = record(c, m->top);
    char name[64] = "", un[256];
    if (top)
        snprintf(name, sizeof name, "%.32s", (const char *)top + 6);
    utf8(c, name, un, sizeof un);
    static char text[1024], ut[2048];
    size_t n = 0;
    text[0] = 0;
    for (int32_t i = 0; i < m->nlines; i++)
        n += (size_t)snprintf(text + n, sizeof text - n, "%s\n", m->lines[i]);
    utf8(c, text, ut, sizeof ut);
    int32_t st = answer_state(c, 0xff);
    int32_t gt = st == 0 || st == 3 || st == 5 ? 0x3a2 : st == 1 ? 0x3a3 : st == 2 ? 0x3a4 : -1;
    if (gt >= 0) {
        /* 0x00fdc814: the text through the wrap into the tab's line (200 px, ';' cuts) */
        memset(m->tab_text, 0, sizeof m->tab_text);
        m->tab_lines = mu_quest_wrap(c, m->tab_text, 1, 0x80, mu_quest_text(c, gt), 200, 0, ";", 0, 0,
                                     c->wrap_scale);
    }
    char s[0x100], us[0x200];
    n = 0;
    s[0] = 0;
    for (int32_t i = 0; i < m->tab_lines && i < 1; i++)
        n += (size_t)snprintf(s + n, sizeof s - n, "%s\n", m->tab_text);
    utf8(c, s, us, sizeof us);
    mu_quest_invoke(c, MQI, "SetJobChange", "%s %s %s", un, ut, us);
    mu_classic_tab_refresh(c);
}

/* ---- NpcJobChangeQuest ---------------------------------------------------------------------------- */

void mu_classic_onload(mu_quest_client *c)            /* 0x00beb8b6 */
{
    char a[256], b[256];
    utf8(c, mu_quest_text(c, 0xc6), a, sizeof a);
    utf8(c, mu_quest_text(c, 0xd83), b, sizeof b);
    mu_quest_invoke(c, NJCQ, "InitText", "%s %s", a, b);
}

/* 0x00bec5dd: the conditions into SetQuestItem / SetQuestItemThreePiece / SetQuestMob; 1 when all are met */
static int window_conditions(mu_quest_client *c)
{
    mu_classic *m = cq(c);
    const uint8_t *rec = record(c, m->current);
    if (!rec)
        return 0;
    int ok = 1;
    static char items[4096], mobs[4096];
    size_t ni = 0, nm = 0;
    items[0] = mobs[0] = 0;
    m->w_items = 0;
    for (int k = 0; k < s16(rec, 0); k++) {
        if (!allowed_hero(c, rec, k))
            continue;
        uint8_t type = rec[ACT(k) + 1];
        if (type == 1) {
            m->w_items++;
            int32_t code = u16(rec, ACT(k) + 2) * 0x200 + rec[ACT(k) + 4];
            int32_t count = s32(rec, ACT(k) + 8), level = rec[ACT(k) + 5];
            int32_t lack = mu_classic_lacking(c, code, count, level);
            ok = lack == 0;
            char name[256] = "", line[512], html[1024];
            if (c->host.item_level_name)
                c->host.item_level_name(c->host.user, code, level, name, sizeof name);
            snprintf(line, sizeof line, "%s x %d", name, count);
            html_index(line, lack ? 2 : 9, 0, html, sizeof html);
            ni += (size_t)snprintf(items + ni, sizeof items - ni, "%s;", html);
            m->w_mode = m->w_items < 2 ? 2 : 3;
        } else if (type == 2) {
            m->w_mode = 1;
            int32_t mon = u16(rec, ACT(k) + 2), need = s32(rec, ACT(k) + 8);
            int32_t have = mu_classic_kills(c, mon), color = 9;
            if (have < need) {
                color = 2;
                ok = 0;
            } else {
                have = need;
            }
            const char *name = c->host.npc_name ? c->host.npc_name(c->host.user, mon) : NULL;
            char line[512], html[1024];
            snprintf(line, sizeof line, "%s x %d/%d", name ? name : "", have, need);
            html_index(line, color, 0, html, sizeof html);
            nm += (size_t)snprintf(mobs + nm, sizeof mobs - nm, "%s;", line);   /* the plain line (not the HTML) */
            (void)html;
        }
        if (ni >= sizeof items - 1)
            ni = sizeof items - 2;
        if (nm >= sizeof mobs - 1)
            nm = sizeof mobs - 2;
    }
    static char u[8192];
    if (items[0]) {
        utf8(c, items, u, sizeof u);
        if (m->w_mode == 2)
            mu_quest_invoke(c, NJCQ, "SetQuestItem", "%s", u);
        else if (m->w_mode == 3)
            mu_quest_invoke(c, NJCQ, "SetQuestItemThreePiece", "%s", u);
    } else if (mobs[0]) {
        utf8(c, mobs, u, sizeof u);
        mu_quest_invoke(c, NJCQ, "SetQuestMob", "%s", u);
    }
    return ok;
}

void mu_classic_window_state(mu_quest_client *c)      /* 0x00bebd9f */
{
    mu_classic *m = cq(c);
    m->w_mode = -1;
    m->w_quest = m->current;
    m->w_state = (uint8_t)mu_classic_state_of(c, m->w_quest);
    if (m->w_state == 1) {
        if (window_conditions(c) == 1)
            mu_quest_invoke(c, NJCQ, "SetDisableBtn", "%d", 0);
        else
            mu_quest_invoke(c, NJCQ, "SetDisableBtn", "%d", 1);
    } else if (m->w_state == 3) {
        m->w_mode = 0;
        char zen[128], u[256];
        if (c->host.money_text)
            c->host.money_text(c->host.user, (double)m->zen, zen, sizeof zen);
        else
            snprintf(zen, sizeof zen, "%d", m->zen);
        mu_quest_invoke(c, NJCQ, "SetRequireZen", "%s", utf8(c, zen, u, sizeof u));
    }
    mu_quest_invoke(c, NJCQ, "SetUIType", "%d", m->w_mode);
}

static void window_names(mu_quest_client *c)          /* 0x00bebf28 */
{
    mu_classic *m = cq(c);
    char npc[256] = "", quest[256] = "", a[512], b[512];
    int q = master_class(c->hero_class) && m->first ? 2 : m->w_quest;
    const uint8_t *rec = record(c, q);
    const char *name = rec && c->host.npc_name ? c->host.npc_name(c->host.user, u16(rec, 4)) : NULL;
    snprintf(npc, sizeof npc, "%s", name ? name : "");
    const uint8_t *cur = record(c, m->current);
    if (c->target_class < 0 || !(master_class(c->hero_class) && (c->target_class == 0xe5 || c->target_class == 0xeb)))
        snprintf(quest, sizeof quest, "%.32s", cur ? (const char *)cur + 6 : "");
    mu_quest_invoke(c, NJCQ, "SetText", "%s %s", utf8(c, npc, a, sizeof a), utf8(c, quest, b, sizeof b));
}

static void window_text(mu_quest_client *c)           /* 0x00bec138 */
{
    mu_classic *m = cq(c);
    static char s[1024], u[2048];
    size_t n = 0;
    s[0] = 0;
    for (int32_t i = 0; i < m->nlines && i < 7; i++)
        n += (size_t)snprintf(s + n, sizeof s - n, "%s", m->lines[i]);
    mu_quest_invoke(c, NJCQ, "SetQuestText", "%s", utf8(c, s, u, sizeof u));
}

static void window_answers(mu_quest_client *c)        /* 0x00bec247 */
{
    mu_classic *m = cq(c);
    static char s[1024], u[2048];
    size_t n = 0;
    s[0] = 0;
    for (int32_t i = 0; i < m->nanswers && i < 10; i++)
        if (m->answers[i][0])
            n += (size_t)snprintf(s + n, sizeof s - n, "%s;", m->answers[i]);
    mu_quest_invoke(c, NJCQ, "SetSelectBtnContent", "%s", utf8(c, s, u, sizeof u));
}

void mu_classic_open(mu_quest_client *c)              /* 0x00bec39b */
{
    mu_classic_show(c, -1);
    mu_classic_window_state(c);
    window_names(c);
    window_text(c);
    window_answers(c);
    mu_quest_invoke(c, NJCQ, "SetPosLeftCenter", "");
    mu_quest_show(c, NJCQ);
    cq(c)->visible = 1;
}

void mu_classic_close(mu_quest_client *c)             /* 0x00bec3f0 */
{
    uint8_t b[1] = {0x54};
    mu_quest_send(c, b, 1, 0, 0);
    mu_quest_hide(c, NJCQ);
    cq(c)->visible = 0;
}

int mu_classic_visible(const mu_quest_client *c)
{
    return c && c->classic && c->classic->visible;
}

/* 0x009f4eeb: the accept request when the requests allow it, else the refusal dialogue */
static int accept(mu_quest_client *c)
{
    mu_classic *m = cq(c);
    const uint8_t *rec = record(c, m->current);
    int ok = rec && requests_ok(c, rec, 1);
    if (ok) {
        uint8_t b[3] = {0xb3, m->top, 1};
        mu_quest_send(c, b, 3, 1, 0);
    } else {
        mu_classic_text(c, m->text);
    }
    return !ok;
}

void mu_classic_choice(mu_quest_client *c, int32_t choice)   /* 0x00bec46a */
{
    mu_classic *m = cq(c);
    const mu_dialog *g = dialog_find(c, m->dialog);
    int32_t action = g && (uint32_t)choice < (uint32_t)g->nanswers ? g->answers[choice].action : -1;
    int refused = 0;
    if (action == 1) {
        refused = accept(c);
    } else if (action == 2) {
        mu_classic_close(c);
    } else if (action == 3) {
        uint8_t b[3] = {0xb3, m->w_quest, 1};   /* handler +0x78 */
        mu_quest_send(c, b, 3, 1, 0);
    } else if (action == 4) {
        mu_quest_logf(&c->log, "classic item piece request (not played)");   /* 0x00bed7d8 */
        mu_classic_close(c);
    } else if (action == 5) {
        uint8_t b[2] = {0x66, 0x35};
        mu_quest_send(c, b, 2, 0, 0);
        mu_classic_close(c);
    }
    int32_t next = g && (uint32_t)choice < (uint32_t)g->nanswers ? g->answers[choice].next : -1;
    if (next > 0 && !refused)
        mu_classic_text(c, next);
    window_text(c);
    window_answers(c);
}

/* 0x009f5147 / 0x00becb32: the complete request when every condition is met */
void mu_classic_complete(mu_quest_client *c)
{
    mu_classic *m = cq(c);
    const uint8_t *rec = record(c, m->current);
    int ready = 0;
    if (m->state == 1 && rec) {
        for (int k = 0; k < s16(rec, 0); k++) {
            if (!allowed(m, rec, k))
                continue;
            uint8_t type = rec[ACT(k) + 1];
            if (type == 1) {
                ready = 1;
                int32_t code = u16(rec, ACT(k) + 2) * 0x200 + rec[ACT(k) + 4];
                if (mu_classic_lacking(c, code, s32(rec, ACT(k) + 8), rec[ACT(k) + 5]))
                    return;
            } else if (type == 2) {
                ready = 1;
                int found = 0;
                for (int i = 0; i < 5; i++)
                    if (m->monsters[i] == (int32_t)u16(rec, ACT(k) + 2) && s32(rec, ACT(k) + 8) <= m->kills[i]) {
                        found = 1;
                        break;
                    }
                if (!found)
                    return;
            }
        }
    }
    if (ready) {
        uint8_t b[3] = {0xb3, m->current, 1};
        mu_quest_send(c, b, 3, 1, 0);
    }
}

int mu_classic_callback(mu_quest_client *c, const char *name, double number)   /* 0x00becc09 */
{
    if (!strcmp(name, "LeaveComplete")) {
        mu_classic_close(c);
        return 1;
    }
    if (!strcmp(name, "onClickbtnCompleteMob") || !strcmp(name, "onClickbtnCompleteItem") ||
        !strcmp(name, "onClickbtnCompleteItemPiece")) {
        mu_classic_complete(c);
        return 1;
    }
    if (!strcmp(name, "onClickSelectBtn")) {
        mu_classic_choice(c, (int32_t)number);
        mu_classic_window_state(c);
        return 1;
    }
    return 0;
}

/* The window's keys (0x00beb9c4): Esc, 1..3 (returns 1 when the key closed it). */
int mu_classic_key(mu_quest_client *c, int key)
{
    if (key == 0x1b) {
        mu_quest_invoke(c, NJCQ, "onCloseBtnClick", "");
        return 1;
    }
    if (key >= '1' && key <= '3') {
        mu_classic_choice(c, key - '1');
        mu_classic_window_state(c);
    }
    return 0;
}

const char *mu_classic_state_text(mu_quest_client *c)
{
    static char out[2048];
    mu_classic *m = cq(c);
    size_t n = (size_t)snprintf(out, sizeof out, "cls=%d cur=%d top=%d text=%d state=%d zen=%d f89=%d pend=%d dlg=%d "
                                "lines=%d answers=%d mode=%d wq=%d ws=%d items=%d kills=",
                                m->cls, m->current, m->top, m->text, m->state, m->zen, m->f89, m->pending, m->dialog,
                                m->nlines, m->nanswers, m->w_mode, m->w_quest, m->w_state, m->w_items);
    for (int i = 0; i < 5; i++)
        n += (size_t)snprintf(out + n, sizeof out - n, "%d:%d,", m->monsters[i], m->kills[i]);
    n += (size_t)snprintf(out + n, sizeof out - n, " states=");
    for (int i = 0; i < 50; i++)
        n += (size_t)snprintf(out + n, sizeof out - n, "%02x", m->states[i]);
    for (int i = 0; i < m->nlines && i < 7; i++)
        n += (size_t)snprintf(out + n, sizeof out - n, " L%d=%s", i, m->lines[i]);
    for (int i = 0; i < m->nanswers && i < 10; i++)
        n += (size_t)snprintf(out + n, sizeof out - n, " A%d=%s", i, m->answers[i]);
    return out;
}

/* ---- Dialog(kor) plaintext ------------------------------------------------------------------------ */

static char *unescape_field(const char *s, size_t n)
{
    char *out = malloc(n + 1);
    if (!out)
        return NULL;
    size_t k = 0;
    for (size_t i = 0; i < n; i++) {
        if (s[i] == '\\' && i + 1 < n) {
            char ch = s[i + 1];
            if (ch == 'x' && i + 3 < n) {
                char hex[3] = {s[i + 2], s[i + 3], 0};
                out[k++] = (char)strtol(hex, NULL, 16);
                i += 3;
                continue;
            }
            out[k++] = ch == 't' ? '\t' : ch == 'n' ? '\n' : ch == 'r' ? '\r' : ch;
            i++;
            continue;
        }
        out[k++] = s[i];
    }
    out[k] = 0;
    return out;
}

static int cmp_dialog(const void *a, const void *b)
{
    const mu_dialog *x = a, *y = b;
    return x->key < y->key ? -1 : x->key > y->key;
}

void mu_dialog_free(mu_quest_data *d);
void mu_dialog_free(mu_quest_data *d)
{
    for (size_t i = 0; d && i < d->ndialogs; i++) {
        free(d->dialogs[i].text);
        for (int32_t k = 0; k < d->dialogs[i].nanswers; k++)
            free(d->dialogs[i].answers[k].text);
        free(d->dialogs[i].answers);
    }
    if (d) {
        free(d->dialogs);
        d->dialogs = NULL;
        d->ndialogs = 0;
    }
}

/* dialog.tsv: key TAB text; dialoganswers.tsv: key TAB position TAB next TAB action TAB text */
long mu_dialog_parse(mu_quest_data *d, const char *texts, const char *answers)
{
    if (!d || !texts)
        return -1;
    mu_dialog_free(d);
    size_t cap = 0;
    for (const char *line = texts; *line;) {
        const char *eol = strchr(line, '\n');
        size_t len = eol ? (size_t)(eol - line) : strlen(line);
        const char *tab = memchr(line, '\t', len);
        if (len && line[0] != '#' && tab) {
            if (d->ndialogs == cap) {
                cap = cap ? cap * 2 : 256;
                mu_dialog *n = realloc(d->dialogs, cap * sizeof *n);
                if (!n)
                    return -1;
                d->dialogs = n;
            }
            mu_dialog *g = &d->dialogs[d->ndialogs++];
            memset(g, 0, sizeof *g);
            g->key = (int32_t)strtol(line, NULL, 10);
            g->text = unescape_field(tab + 1, len - (size_t)(tab + 1 - line));
        }
        if (!eol)
            break;
        line = eol + 1;
    }
    if (d->ndialogs)
        qsort(d->dialogs, d->ndialogs, sizeof *d->dialogs, cmp_dialog);
    for (const char *line = answers ? answers : ""; *line;) {
        const char *eol = strchr(line, '\n');
        size_t len = eol ? (size_t)(eol - line) : strlen(line);
        if (len && line[0] != '#') {
            const char *f[5];
            size_t fl[5];
            int nf = 0;
            size_t start = 0;
            for (size_t i = 0; i <= len && nf < 5; i++)
                if (i == len || (line[i] == '\t' && nf < 4)) {
                    f[nf] = line + start;
                    fl[nf++] = i - start;
                    start = i + 1;
                }
            if (nf == 5) {
                mu_dialog key = {(int32_t)strtol(f[0], NULL, 10), NULL, NULL, 0};
                mu_dialog *g = bsearch(&key, d->dialogs, d->ndialogs, sizeof *d->dialogs, cmp_dialog);
                int32_t pos = (int32_t)strtol(f[1], NULL, 10);
                if (g && pos == g->nanswers) {
                    mu_dialog_answer *na = realloc(g->answers, (size_t)(g->nanswers + 1) * sizeof *na);
                    if (na) {
                        g->answers = na;
                        na[g->nanswers].next = (int32_t)strtol(f[2], NULL, 10);
                        na[g->nanswers].action = (int32_t)strtol(f[3], NULL, 10);
                        na[g->nanswers].text = unescape_field(f[4], fl[4]);
                        g->nanswers++;
                    }
                }
            }
        }
        if (!eol)
            break;
        line = eol + 1;
    }
    return (long)d->ndialogs;
}

void mu_classic_set_first(mu_quest_client *c, int first)   /* [0x01d1de8c] (tests and hosts) */
{
    mu_classic *m = cq(c);
    if (m)
        m->first = (uint8_t)first;
}

int32_t mu_classic_current(mu_quest_client *c)   /* +0x30d86 */
{
    mu_classic *m = cq(c);
    return m ? m->current : 0;
}

/* The current quest's monster conditions (for a host's kill counting): up to max monsters, returns the count. */
int32_t mu_classic_monsters(mu_quest_client *c, int32_t *out, int32_t max)
{
    mu_classic *m = cq(c);
    const uint8_t *rec = m ? record(c, m->current) : NULL;
    int32_t n = 0;
    for (int k = 0; rec && k < s16(rec, 0) && n < max; k++)
        if (allowed(m, rec, k) && rec[ACT(k) + 1] == 2)
            out[n++] = u16(rec, ACT(k) + 2);
    return n;
}

/* C1 86 (0x0127a0e0): a quest's state set by the server (+3 quest, +4 result, +5 the packed state byte): result 0
 * sets it (0x009f4b61), resets the kills when it became complete, refreshes and opens NpcJobChangeQuest; result 2
 * is a message box (GlobalText 0x15bd). */
void mu_classic_receive_result(mu_quest_client *c, const uint8_t *p, size_t size)
{
    mu_classic *m = cq(c);
    if (!m || size < 6 || p[3] >= 200)
        return;
    if (p[4] == 0) {
        uint8_t q = p[3];
        m->current = q;
        m->top = q <= m->top ? m->top : q;
        m->states[m->current >> 2] = p[5];
        hero_byte_29(c);
        if (mu_classic_state(c, q) == 2)
            for (int i = 0; i < 5; i++)
                m->monsters[i] = m->kills[i] = -1;
        mu_quest_logf(&c->log, "classic refresh");
        mu_classic_open(c);
    } else if (p[4] == 2) {
        /* The MsgBoxes receiver is ECX; the first argument (the callback owner) is null. */
        mu_quest_msgbox(c, "?0", 0, mu_quest_text(c, 0x15bd), "", 0, 0, 0);
    }
}
