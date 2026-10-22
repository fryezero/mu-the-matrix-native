/* Quests in the native client: libquest in a session with a local demo server (NATIVE-QUEST-001); see
 * mu_quest.h. */
#include "mu_quest.h"

#include <stdarg.h>
#include <stdlib.h>
#include <string.h>

#if defined(__clang__) || defined(__GNUC__)
__attribute__((format(printf, 2, 3)))
#endif
static void note(mu_quest_session *s, const char *fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(s->last, sizeof s->last, fmt, ap);
    va_end(ap);
    if (s->log_count < 48)
        snprintf(s->log[s->log_count++], sizeof s->log[0], "step %d: %s", s->step, s->last);
}

/* ---- the demo server ------------------------------------------------------------------------- */

static void queue(mu_quest_session *s, const uint8_t *bytes, size_t size)
{
    if (s->nqueue >= MU_QUEST_QUEUE || size > sizeof s->queue[0].bytes)
        return;
    mu_quest_packet *p = &s->queue[s->nqueue++];
    p->due = s->step + s->latency;
    p->size = size;
    memcpy(p->bytes, bytes, size);
    p->bytes[1] = (uint8_t)size;
}

static void put16(uint8_t *p, int32_t v)
{
    p[0] = (uint8_t)(v & 0xff);
    p[1] = (uint8_t)((v >> 8) & 0xff);
}

static int32_t get16(const uint8_t *p)
{
    return (int32_t)(p[0] | p[1] << 8);
}

static void answer_result(mu_quest_session *s, uint8_t sub, int32_t quest, uint8_t result)
{
    uint8_t b[9] = {0xc1, 9, 0xf6, sub, 0, 0, 0, 0, result};
    put16(b + 6, quest);
    queue(s, b, sizeof b);
}

static void answer_progress(mu_quest_session *s, int32_t quest, int32_t count, int32_t state)
{
    uint8_t b[11] = {0xc1, 11, 0xf6, 0x75, 0, 0, 0, 0, 0, 0, (uint8_t)state};
    put16(b + 6, quest);
    put16(b + 8, count);
    queue(s, b, sizeof b);
    ++s->stats.progress;
}

static int32_t quest_state(const mu_quest_session *s, int32_t quest)
{
    int32_t f[4];
    return mu_quest_fields(&s->client, quest, f) ? f[0] : -1;
}

void mu_quest_session_npc_list(mu_quest_session *s, int32_t npc)
{
    uint8_t b[256] = {0xc1, 0, 0xf6, 0x71};
    int32_t n = 0;
    size_t at = 6;
    for (int32_t i = 0; i < s->noffers && at + 6 + 4 <= sizeof b; i++) {
        const mu_quest_offer *o = &s->offers[i];
        if (o->npc != npc || !mu_quest_get(&s->client.qs, o->quest))
            continue;
        int32_t st = quest_state(s, o->quest);
        if (st <= 0)
            st = o->state;
        put16(b + at, 0);
        put16(b + at + 2, o->quest);
        b[at + 4] = (uint8_t)st;
        b[at + 5] = 0;
        at += 6;
        n++;
    }
    put16(b + 4, n);
    memset(b + at, 0, 4);                 /* the sub-code's XOR salt (the layer outside libquest) */
    at += 4;
    ++s->stats.lists;
    note(s, "demo server: NPC %d lists %d quest(s)", npc, n);
    queue(s, b, at);
}

/* ---- NATIVE-QUEST-002: the guide and class-upgrade demo ------------------------------------------------ */

static const mu_guide_step *guide_step(const mu_quest_session *s, int32_t id)
{
    for (size_t k = 0; k < s->data.nguide_chapters; k++)
        for (size_t i = 0; i < s->data.guide_chapters[k].nsteps; i++)
            if (s->data.guide_chapters[k].steps[i].w[1] == id)
                return &s->data.guide_chapters[k].steps[i];
    return NULL;
}

static void guide_send(mu_quest_session *s, int32_t step, int32_t count, int32_t state)
{
    uint8_t b[8] = {0xc1, 8, 0xf6, 0x50, 0, 0, (uint8_t)count, (uint8_t)state};
    put16(b + 4, step);
    s->guide_step = step;
    s->guide_count = count;
    s->guide_state = state;
    queue(s, b, sizeof b);
}

static int classic_state_of(const mu_quest_session *s, int32_t q)
{
    return q >= 0 && q < 200 ? (s->classic_states[q / 4] >> ((q % 4) * 2)) & 3 : 0;
}

static void classic_set(mu_quest_session *s, int32_t q, int state)
{
    if (q < 0 || q >= 200)
        return;
    uint8_t *b = &s->classic_states[q / 4];
    *b = (uint8_t)((*b & ~(3 << ((q % 4) * 2))) | (state & 3) << ((q % 4) * 2));
    uint8_t a1[5] = {0xc1, 5, 0xa1, (uint8_t)q, *b};
    queue(s, a1, sizeof a1);
}

static void travel(mu_quest_session *s, int32_t world, int32_t x, int32_t y, const char *what)
{
    ++s->travels;
    int done = s->travel ? s->travel(s->user, world, x, y) : 0;
    note(s, "demo server: %s: move the hero to world %d (%d, %d)%s", what, world, x, y,
         done ? "" : " - cross-map travel hook (NATIVE-MAP-001), not played");
}

static void guide_request(mu_quest_session *s, const uint8_t *p, size_t n)
{
    int32_t id = n >= 8 ? (int32_t)((uint32_t)p[4] | (uint32_t)p[5] << 8 | (uint32_t)p[6] << 16 | (uint32_t)p[7] << 24) : s->guide_step;
    const mu_guide_step *g = guide_step(s, id);
    switch (p[3]) {
    case 0x51: {                          /* reward: QuestProgressInfo, then the next step */
        uint8_t r[7] = {0xc1, 7, 0xf6, 0x51, 0, 0, 1};
        queue(s, r, sizeof r);
        if (g) {
            s->zen += g->w[0xb8 / 4] > 0 ? g->w[0xb8 / 4] : 0;
            s->exp += g->w[0xb4 / 4] > 0 ? g->w[0xb4 / 4] : 0;
        }
        note(s, "demo server: guide step %d rewarded", id);
        guide_send(s, id, 0, 3);
        break;
    }
    case 0x52:
    case 0x53:
        note(s, "demo server: guide step %d %s", id, p[3] == 0x52 ? "given up" : "chapter aborted");
        guide_send(s, id, 0, 3);
        break;
    case 0x54:
        if (g)
            travel(s, g->w[0xa8 / 4], g->w[0xac / 4], g->w[0xb0 / 4], "guide Go Now");
        break;
    case 0x55:
        if (g && g->w[0x8c / 4] == 5) {
            note(s, "demo server: guide step %d reached", id);
            guide_send(s, id, 0, 2);
        }
        break;
    default:
        break;
    }
}

void mu_quest_session_request(mu_quest_session *s, const uint8_t *p, size_t n)
{
    ++s->stats.requests;
    if (n >= 3 && p[0] == 0xc1 && p[2] == 0x54)
        return;                           /* the NPC window closed */
    if (n >= 5 && p[0] == 0xc1 && p[2] == 0xb3) {
        /* a class-upgrade quest: taken (3 -> 1) or completed (1 -> 2) */
        int32_t q = p[3], st = classic_state_of(s, q);
        if (st == 3 || st == 0) {
            classic_set(s, q, 1);
            note(s, "demo server: class-upgrade quest %d taken", q);
        } else if (st == 1) {
            classic_set(s, q, 2);
            note(s, "demo server: class-upgrade quest %d completed", q);
        }
        return;
    }
    if (n >= 4 && p[0] == 0xc1 && p[2] == 0xf6 && p[3] == 0x1c) {
        uint8_t b[64] = {0xc1, 0, 0xf6, 0x1c, 0, 0};
        int32_t k = 0;
        for (int i = 0; i < 5; i++)
            if (s->classic_kills[i][0] > 0) {
                put16(b + 6 + k * 4, s->classic_kills[i][0]);
                b[8 + k * 4] = (uint8_t)s->classic_kills[i][1];
                b[9 + k * 4] = 0;
                k++;
            }
        b[4] = s->client.classic ? (uint8_t)mu_classic_current(&s->client) : 0;
        b[5] = (uint8_t)k;
        queue(s, b, (size_t)(6 + k * 4));
        return;
    }
    if (n >= 4 && p[0] == 0xc1 && p[2] == 0xf6 && p[3] >= 0x51 && p[3] <= 0x57) {
        guide_request(s, p, n);
        return;
    }
    if (n >= 8 && p[0] == 0xc1 && p[2] == 0xf6 && (p[3] == 0x76 || p[3] == 0x7a)) {
        int32_t quest = get16(p + 6);
        const mu_quest *q = mu_quest_get(&s->client.qs, quest);
        if (q && q->record && p[3] == 0x7a)
            travel(s, q->record->goal[8], q->record->goal[9], q->record->goal[10], "quest Go Now");
        else if (q && q->record && q->record->goal[1] == 5)
            answer_progress(s, quest, 0, 2);
        return;
    }
    if (n < 4 || p[0] != 0xc1 || p[2] != 0xf6)
        return;
    switch (p[3]) {
    case 0x71:
        if (n >= 6)
            mu_quest_session_npc_list(s, get16(p + 4));
        break;
    case 0x72:
        if (n >= 8) {
            int32_t quest = get16(p + 6);
            const mu_quest *q = mu_quest_get(&s->client.qs, quest);
            note(s, "demo server: quest %d accepted", quest);
            answer_result(s, 0x72, quest, 0);
            ++s->stats.accepted;
            if (q && q->record && (q->record->goal[1] == 4 || q->record->goal[1] == 5 || q->record->goal[1] == 6))
                answer_progress(s, quest, 0, 2);   /* talk goals: done once accepted (demo) */
        }
        break;
    case 0x73:
        if (n >= 8) {
            answer_result(s, 0x73, get16(p + 6), 0);
            ++s->stats.given_up;
            note(s, "demo server: quest %d given up", get16(p + 6));
        }
        break;
    case 0x74:
        if (n >= 10) {
            int32_t quest = get16(p + 8);
            const mu_quest *q = mu_quest_get(&s->client.qs, quest);
            if (q && q->state == 2 && q->record) {
                s->zen += q->record->goal[12] > 0 ? q->record->goal[12] : 0;
                s->exp += q->record->goal[11] > 0 ? q->record->goal[11] : 0;
                answer_result(s, 0x74, quest, 0);
                ++s->stats.completed;
                note(s, "demo server: quest %d completed (zen %d, exp %d)", quest, q->record->goal[12],
                     q->record->goal[11]);
                if (s->event) {   /* the reward packets of a server are not modelled: a labelled chat line */
                    char line[160];
                    snprintf(line, sizeof line, "demo Quest complete (demo server): %d zen, %d exp",
                             q->record->goal[12] > 0 ? q->record->goal[12] : 0,
                             q->record->goal[11] > 0 ? q->record->goal[11] : 0);
                    s->event(s->user, line);
                }
            } else {
                answer_result(s, 0x74, quest, 4);
                note(s, "demo server: quest %d not complete", quest);
            }
        }
        break;
    default:
        break;
    }
}

void mu_quest_session_kill(mu_quest_session *s, int32_t monster_class, int32_t world)
{
    /* NATIVE-QUEST-002: the guide's hunt step and the class-upgrade kills */
    const mu_guide_step *g = s->guide_state == 1 ? guide_step(s, s->guide_step) : NULL;
    if (g && g->w[0x8c / 4] == 2 && g->w[0x90 / 4] == monster_class) {
        int32_t need = g->w[0x98 / 4], count = s->guide_count + 1;
        guide_send(s, s->guide_step, count, count >= need ? 2 : 1);
        note(s, "demo server: guide step %d progress %d/%d", s->guide_step, count, need);
    }
    for (int i = 0; i < 5; i++)
        if (s->classic_kills[i][0] == monster_class)
            s->classic_kills[i][1]++;
    for (int32_t cat = MU_QUEST_CATEGORY_FIRST; cat <= MU_QUEST_CATEGORY_LAST; cat++) {
        const int32_t *a;
        size_t n = mu_quest_active(&s->client.qs, cat, &a);
        for (size_t i = 0; i < n; i++) {
            const mu_quest *q = mu_quest_get(&s->client.qs, a[i]);
            if (!q || !q->record || q->state != 1)
                continue;
            const int32_t *g = q->record->goal;
            if (!((g[1] == 2 && g[2] == monster_class) || (g[1] == 8 && g[8] == world)))
                continue;
            int32_t count = q->count + 1;
            answer_progress(s, q->index, count, count >= g[4] ? 2 : 1);
            note(s, "demo server: quest %d progress %d/%d", q->index, count, g[4]);
        }
    }
}

void mu_quest_session_progress(mu_quest_session *s, int32_t quest, int32_t count)
{
    const mu_quest *q = mu_quest_get(&s->client.qs, quest);
    if (!q || !q->record)
        return;
    answer_progress(s, quest, count, count >= q->record->goal[4] ? 2 : 1);
}

/* ---- the client's effects ----------------------------------------------------------------------- */

static void sink(void *user, const char *line)
{
    mu_quest_session *s = user;
    ++s->stats.events;
    if (!strncmp(line, "send ", 5)) {
        uint8_t bytes[256];
        size_t n = 0;
        for (const char *p = line + 5; *p && *p != '|' && n < sizeof bytes;) {
            char *end = NULL;
            long v = strtol(p, &end, 16);
            if (end == p)
                break;
            bytes[n++] = (uint8_t)v;
            p = end;
            while (*p == ' ')
                p++;
        }
        mu_quest_session_request(s, bytes, n);
        return;
    }
    if (!strncmp(line, "invoke ", 7) || !strncmp(line, "value ", 6))
        ++s->stats.invokes;
    if (s->event)
        s->event(s->user, line);
}

int32_t mu_quest_session_offers(mu_quest_session *s, const char *text)
{
    s->noffers = 0;
    for (const char *p = text; p && *p;) {
        const char *eol = strchr(p, '\n');
        size_t n = eol ? (size_t)(eol - p) : strlen(p);
        char line[1024];
        if (n >= sizeof line)
            n = sizeof line - 1;
        memcpy(line, p, n);
        line[n] = 0;
        p += eol ? n + 1 : n;
        char *hash = strchr(line, '#');
        if (hash)
            *hash = 0;
        char *save = NULL, *word = strtok_r(line, " \t\r", &save);
        if (!word || strcmp(word, "quest"))
            continue;
        char *npc = strtok_r(NULL, " \t\r", &save);
        if (!npc)
            continue;
        while ((word = strtok_r(NULL, " \t\r", &save)) && s->noffers < MU_QUEST_OFFERS) {
            mu_quest_offer *o = &s->offers[s->noffers++];
            o->npc = (int32_t)strtol(npc, NULL, 0);
            o->quest = (int32_t)strtol(word, NULL, 0);
            const char *colon = strchr(word, ':');
            o->state = colon ? (int32_t)strtol(colon + 1, NULL, 0) : 0;
        }
    }
    return s->noffers;
}

void mu_quest_session_demo_state(mu_quest_session *s, const char *text)
{
    s->guide_step = -1;
    for (const char *p = text; p && *p;) {
        const char *eol = strchr(p, '\n');
        size_t n = eol ? (size_t)(eol - p) : strlen(p);
        char line[1024];
        if (n >= sizeof line)
            n = sizeof line - 1;
        memcpy(line, p, n);
        line[n] = 0;
        p += eol ? n + 1 : n;
        char *hash = strchr(line, '#');
        if (hash)
            *hash = 0;
        char *save = NULL, *word = strtok_r(line, " \t\r", &save);
        if (word && !strcmp(word, "guide") && (word = strtok_r(NULL, " \t\r", &save))) {
            int32_t step = 0, count = 0, state = 1;
            sscanf(word, "%d:%d:%d", &step, &count, &state);
            guide_send(s, step, count, state);
        } else if (word && !strcmp(word, "classic")) {
            while ((word = strtok_r(NULL, " \t\r", &save))) {
                int32_t q = -1, st = 0;
                if (sscanf(word, "%d:%d", &q, &st) == 2 && q >= 0 && q < 200) {
                    s->classic_states[q / 4] = (uint8_t)((s->classic_states[q / 4] & ~(3 << ((q % 4) * 2))) |
                                                         (st & 3) << ((q % 4) * 2));
                    if (q + 1 > s->classic_count)
                        s->classic_count = q + 1;
                }
            }
        }
    }
    if (s->classic_count) {
        uint8_t b[64] = {0xc1, 0, 0xc0, (uint8_t)s->classic_count};
        size_t bytes = (size_t)(s->classic_count / 4 + 1);
        memcpy(b + 4, s->classic_states, bytes);
        queue(s, b, 4 + bytes);
    }
}

long mu_quest_session_load_classic(mu_quest_session *s, const char *root)
{
    char path[2048];
    snprintf(path, sizeof path, "%s/Data/Local/quest.bmd", root ? root : ".");
    FILE *f = fopen(path, "rb");
    if (!f) {
        snprintf(path, sizeof path, "%s/Data/Local/Quest.bmd", root ? root : ".");
        f = fopen(path, "rb");
    }
    if (!f)
        return -1;
    uint8_t *buf = malloc(200000);
    size_t n = buf ? fread(buf, 1, 200000, f) : 0;
    fclose(f);
    long r = buf ? mu_classic_load(&s->data, buf, n) : -1;
    free(buf);
    /* the class-upgrade manager's monsters: the demo counts the current quest's monster conditions */
    return r;
}

int mu_quest_session_open(mu_quest_session *s, const char *lang_dir, const char *demo_text, const mu_quest_host *host,
                          char *error, size_t error_size)
{
    memset(s, 0, sizeof *s);
    s->latency = 4;
    const char *dir = lang_dir ? lang_dir : getenv("MU_LANG_DIR");
    if (!dir || mu_quest_load_dir(&s->data, dir) <= 0) {
        snprintf(error, error_size, "no quest tables (quests.tsv in MU_LANG_DIR: a langread snapshot taken with "
                                    "node:0x137c=0x118, scripts/live_lang_to_plain.py)");
        mu_quest_data_free(&s->data);
        return 1;
    }
    if (mu_quest_client_init(&s->client, &s->data, host)) {
        snprintf(error, error_size, "out of memory");
        mu_quest_data_free(&s->data);
        return 1;
    }
    mu_quest_set_sink(&s->client, sink, s);
    s->client.font = 1;
    s->client.font_default = 1;
    /* NATIVE-QUEST-002: the HUD's handler, MyQuestInfo's tabs 0 / 1 and the quest tabs' move are played */
    mu_quest_enable_hud(&s->client);
    s->client.play_tabs = 1;
    s->client.play_move = 1;
    mu_quest_session_offers(s, demo_text);
    mu_quest_session_demo_state(s, demo_text);
    s->ready = 1;
    return 0;
}

void mu_quest_session_close(mu_quest_session *s)
{
    if (!s || !s->ready)
        return;
    mu_quest_client_free(&s->client);
    mu_quest_data_free(&s->data);
    s->ready = 0;
}

void mu_quest_session_step(mu_quest_session *s)
{
    if (!s || !s->ready)
        return;
    ++s->step;
    for (int32_t i = 0; i < s->nqueue;) {
        if (s->queue[i].due > s->step) {
            i++;
            continue;
        }
        mu_quest_packet p = s->queue[i];
        memmove(&s->queue[i], &s->queue[i + 1], (size_t)(s->nqueue - i - 1) * sizeof s->queue[0]);
        s->nqueue--;
        ++s->stats.answers;
        mu_quest_receive(&s->client, p.bytes, p.size);   /* the client's F6 handlers (verified) */
    }
}

void mu_quest_session_toggle_info(mu_quest_session *s)
{
    if (!s || !s->ready)
        return;
    if (s->client.info.visible)
        mu_quest_info_close(&s->client);
    else
        mu_quest_info_open(&s->client);
}

void mu_quest_session_report(const mu_quest_session *s, FILE *out)
{
    if (!s || !s->ready)
        return;
    fprintf(out, "{\"quest\": {\"quests\": %zu, \"strings\": %zu, \"offers\": %d, \"requests\": %u, \"answers\": %u, "
                 "\"accepted\": %u, \"completed\": %u, \"given_up\": %u, \"progress\": %u, \"lists\": %u, "
                 "\"events\": %u, \"invokes\": %u, \"zen\": %lld, \"exp\": %lld, \"active\": [",
            s->data.nrecords, s->data.nstrings, s->noffers, s->stats.requests, s->stats.answers, s->stats.accepted,
            s->stats.completed, s->stats.given_up, s->stats.progress, s->stats.lists, s->stats.events,
            s->stats.invokes, (long long)s->zen, (long long)s->exp);
    int first = 1;
    for (int32_t cat = MU_QUEST_CATEGORY_FIRST; cat <= MU_QUEST_CATEGORY_LAST; cat++) {
        const int32_t *a;
        size_t n = mu_quest_active(&s->client.qs, cat, &a);
        for (size_t i = 0; i < n; i++) {
            int32_t f[4];
            mu_quest_fields(&s->client, a[i], f);
            fprintf(out, "%s{\"quest\": %d, \"state\": %d, \"count\": %d}", first ? "" : ", ", a[i], f[0], f[1]);
            first = 0;
        }
    }
    fprintf(out, "], \"last\": \"%s\", \"log\": [", s->last);
    for (int32_t i = 0; i < s->log_count; i++)
        fprintf(out, "%s\"%s\"", i ? ", " : "", s->log[i]);
    fprintf(out, "]}}\n");
}

size_t mu_quest_session_size(void)
{
    return sizeof(mu_quest_session);
}

mu_quest_client *mu_quest_session_client(mu_quest_session *s)
{
    return &s->client;
}

void mu_quest_session_set_event(mu_quest_session *s, void (*event)(void *user, const char *line), void *user)
{
    s->event = event;
    s->user = user;
}
