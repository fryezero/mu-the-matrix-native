/* Quests in the native client: libquest in a session with a local demo server (NATIVE-QUEST-001); see
 * mu_quest.h. */
#include "../behavior.h"
#include "../../core/mu_quest.h"
#include "../../session/mu_session_seed.h"
#include <unistd.h>
#define MU_QUEST_OFFERS 64
#define MU_QUEST_QUEUE 32

typedef struct mu_quest_offer
{
    int32_t npc, quest, state;
} mu_quest_offer;

typedef struct mu_quest_packet
{
    int32_t due;
    size_t size;
    uint8_t bytes[256];
} mu_quest_packet;

typedef struct quest_demo_stats
{
    uint32_t requests, answers, accepted, completed, given_up, progress, lists, events, invokes;
} quest_demo_stats;

typedef struct quest_demo
{
    mu_quest_data data;
    mu_quest_client client;
    int ready;
    mu_quest_offer offers[MU_QUEST_OFFERS];
    int32_t noffers;
    mu_quest_packet queue[MU_QUEST_QUEUE];
    int32_t nqueue;
    int32_t step, latency;
    int32_t world;
    int64_t zen, exp; /* demo rewards received */
    /* the host's executor for every non-packet effect line (invoke/value/show/hide/notice/msgbox/summary...) */
    void (*event)(void *user, const char *line);
    void *user;
    quest_demo_stats stats;
    char last[160];
    char log[48][160];
    int32_t log_count;
    /* NATIVE-QUEST-002 */
    int32_t guide_step, guide_count, guide_state; /* the demo's guide state (-1: no guide line) */
    uint8_t classic_states[50];                   /* the demo's class-upgrade states (2 bits each) */
    int32_t classic_count;                        /* quests the C0 packet carries (0: no classic line) */
    int32_t classic_kills[5][2];                  /* monster, kills of the current quest */
    /* The cross-map hook accepts a queued move. The host reports its result with travel_complete. */
    int (*travel)(void *user, int32_t world, int32_t x, int32_t y);
    int32_t travel_x, travel_y;
    uint32_t travels;
    uint8_t travel_answer; /* resume only after the queued destination has loaded */
} quest_demo;

#include <stdarg.h>
#include <stdlib.h>
#include <string.h>

#if defined(__clang__) || defined(__GNUC__)
__attribute__((format(printf, 2, 3)))
#endif
static void note(quest_demo *s, const char *fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(s->last, sizeof s->last, fmt, ap);
    va_end(ap);
    if (s->log_count < 48)
        snprintf(s->log[s->log_count++], sizeof s->log[0], "step %d: %s", s->step, s->last);
}

/* ---- the demo server ------------------------------------------------------------------------- */

static void queue(quest_demo *s, const uint8_t *bytes, size_t size)
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

static void put32(uint8_t *p, int32_t v)
{
    uint32_t word = (uint32_t)v;
    for (int i = 0; i < 4; i++)
        p[i] = (uint8_t)(word >> (i * 8));
}

static int32_t get16(const uint8_t *p)
{
    return (int32_t)(p[0] | p[1] << 8);
}

static void answer_result(quest_demo *s, uint8_t sub, int32_t quest, uint8_t result)
{
    uint8_t b[9] = {0xc1, 9, 0xf6, sub, 0, 0, 0, 0, result};
    put16(b + 6, quest);
    queue(s, b, sizeof b);
}

static void answer_progress(quest_demo *s, int32_t quest, int32_t count, int32_t state)
{
    uint8_t b[11] = {0xc1, 11, 0xf6, 0x75, 0, 0, 0, 0, 0, 0, (uint8_t)state};
    put16(b + 6, quest);
    put16(b + 8, count);
    queue(s, b, sizeof b);
    ++s->stats.progress;
}

static int32_t quest_state(const quest_demo *s, int32_t quest)
{
    int32_t f[4];
    return mu_quest_fields(&s->client, quest, f) ? f[0] : -1;
}

void demo_npc_list(quest_demo *s, int32_t npc)
{
    uint8_t b[256] = {0xc1, 0, 0xf6, 0x71};
    int32_t n = 0;
    size_t at = 6;
    for (int32_t i = 0; i < s->noffers && at + 6 + 4 <= sizeof b; i++)
    {
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
    memset(b + at, 0, 4); /* opaque synthetic trailer; no hash bytes recovered */
    at += 4;
    ++s->stats.lists;
    note(s, "demo server: NPC %d lists %d quest(s)", npc, n);
    queue(s, b, at);
}

/* ---- NATIVE-QUEST-002: the guide and class-upgrade demo ------------------------------------------------ */

static const mu_guide_step *guide_step(const quest_demo *s, int32_t id)
{
    for (size_t k = 0; k < s->data.nguide_chapters; k++)
        for (size_t i = 0; i < s->data.guide_chapters[k].nsteps; i++)
            if (s->data.guide_chapters[k].steps[i].w[1] == id)
                return &s->data.guide_chapters[k].steps[i];
    return NULL;
}

static void guide_send(quest_demo *s, int32_t step, int32_t count, int32_t state)
{
    uint8_t b[8] = {0xc1, 8, 0xf6, 0x50, 0, 0, (uint8_t)count, (uint8_t)state};
    put16(b + 4, step);
    s->guide_step = step;
    s->guide_count = count;
    s->guide_state = state;
    queue(s, b, sizeof b);
}

static int classic_state_of(const quest_demo *s, int32_t q)
{
    return q >= 0 && q < 200 ? (s->classic_states[q / 4] >> ((q % 4) * 2)) & 3 : 0;
}

static void classic_set(quest_demo *s, int32_t q, int state)
{
    if (q < 0 || q >= 200)
        return;
    uint8_t *b = &s->classic_states[q / 4];
    *b = (uint8_t)((*b & ~(3 << ((q % 4) * 2))) | (state & 3) << ((q % 4) * 2));
    uint8_t a1[5] = {0xc1, 5, 0xa1, (uint8_t)q, *b};
    queue(s, a1, sizeof a1);
}

void demo_classic_talk(quest_demo *s)
{
    int32_t q = mu_classic_current(&s->client);
    if (q < 0 || q >= 200 || !s->data.classic)
        return;
    uint8_t b[5] = {0xc1, 5, 0xa1, (uint8_t)q, s->classic_states[q / 4]};
    queue(s, b, sizeof b);
    note(s, "demo server: class-upgrade NPC, quest %d", q);
}

static void travel(quest_demo *s, int32_t world, int32_t x, int32_t y, const char *what, uint8_t answer)
{
    ++s->travels;
    s->travel_answer = answer;
    note(s, "demo server: %s: world %d (%d, %d)", what, world, x, y);
    s->world = world;
    /* Fixture metadata, not a new service opcode. The adapter observes these server fields. */
    s->travel_x = x;
    s->travel_y = y;
}

void demo_travel_complete(quest_demo *s, int success)
{
    if (success && s->travel_answer)
    {
        uint8_t b[4] = {0xc1, 4, 0xf6, s->travel_answer};
        queue(s, b, sizeof b);
    }
    s->travel_answer = 0;
}

static void guide_request(quest_demo *s, const uint8_t *p, size_t n)
{
    int32_t id =
        n >= 8 ? (int32_t)((uint32_t)p[4] | (uint32_t)p[5] << 8 | (uint32_t)p[6] << 16 | (uint32_t)p[7] << 24)
               : s->guide_step;
    const mu_guide_step *g = guide_step(s, id);
    switch (p[3])
    {
    case 0x51:
    { /* reward: QuestProgressInfo, then the next step */
        uint8_t r[7] = {0xc1, 7, 0xf6, 0x51, 0, 0, 1};
        queue(s, r, sizeof r);
        if (g)
        {
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
            travel(s, g->w[0xa8 / 4], g->w[0xac / 4], g->w[0xb0 / 4], "guide Go Now", 0x56);
        break;
    case 0x55:
        if (g && g->w[0x8c / 4] == 5)
        {
            note(s, "demo server: guide step %d reached", id);
            guide_send(s, id, 0, 2);
        }
        break;
    default:
        break;
    }
}

static void demo_request(quest_demo *s, const uint8_t *p, size_t n)
{
    ++s->stats.requests;
    if (n >= 3 && p[0] == 0xc1 && p[2] == 0x54)
        return; /* the NPC window closed */
    if (n >= 5 && p[0] == 0xc1 && p[2] == 0xb3)
    {
        /* a class-upgrade quest: taken (3 -> 1) or completed (1 -> 2) */
        int32_t q = p[3], st = classic_state_of(s, q);
        if (st == 3 || st == 0)
        {
            int32_t monsters[5];
            int32_t count = mu_classic_monsters(&s->client, monsters, 5);
            for (int i = 0; i < 5; i++)
            {
                s->classic_kills[i][0] = i < count ? monsters[i] : -1;
                s->classic_kills[i][1] = i < count ? 0 : -1;
            }
            classic_set(s, q, 1);
            note(s, "demo server: class-upgrade quest %d taken", q);
        }
        else if (st == 1)
        {
            classic_set(s, q, 2);
            for (int i = 0; i < 5; i++)
                s->classic_kills[i][0] = s->classic_kills[i][1] = -1;
            note(s, "demo server: class-upgrade quest %d completed", q);
        }
        return;
    }
    if (n >= 4 && p[0] == 0xc1 && p[2] == 0xf6 && p[3] == 0x1c)
    {
        uint8_t b[64] = {0xc1, 0, 0xf6, 0x1c, 0, 0};
        int32_t k = 0;
        for (int i = 0; i < 5; i++)
            if (s->classic_kills[i][0] > 0)
            {
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
    if (n >= 4 && p[0] == 0xc1 && p[2] == 0xf6 && p[3] >= 0x51 && p[3] <= 0x57)
    {
        guide_request(s, p, n);
        return;
    }
    if (n >= 8 && p[0] == 0xc1 && p[2] == 0xf6 && (p[3] == 0x76 || p[3] == 0x7a))
    {
        int32_t quest = get16(p + 6);
        const mu_quest *q = mu_quest_get(&s->client.qs, quest);
        if (q && q->record && p[3] == 0x7a)
            travel(s, q->record->goal[8], q->record->goal[9], q->record->goal[10], "quest Go Now", 0x7b);
        else if (q && q->record && q->record->goal[1] == 5)
            answer_progress(s, quest, 0, 2);
        return;
    }
    if (n < 4 || p[0] != 0xc1 || p[2] != 0xf6)
        return;
    switch (p[3])
    {
    case 0x71:
        if (n >= 6)
            demo_npc_list(s, get16(p + 4));
        break;
    case 0x72:
        if (n >= 8)
        {
            int32_t quest = get16(p + 6);
            const mu_quest *q = mu_quest_get(&s->client.qs, quest);
            note(s, "demo server: quest %d accepted", quest);
            answer_result(s, 0x72, quest, 0);
            ++s->stats.accepted;
            if (q && q->record && (q->record->goal[1] == 4 || q->record->goal[1] == 5 || q->record->goal[1] == 6))
                answer_progress(s, quest, 0, 2); /* talk goals: done once accepted (demo) */
        }
        break;
    case 0x73:
        if (n >= 8)
        {
            answer_result(s, 0x73, get16(p + 6), 0);
            ++s->stats.given_up;
            note(s, "demo server: quest %d given up", get16(p + 6));
        }
        break;
    case 0x74:
        if (n >= 10)
        {
            int32_t quest = get16(p + 8);
            const mu_quest *q = mu_quest_get(&s->client.qs, quest);
            if (q && q->state == 2 && q->record)
            {
                s->zen += q->record->goal[12] > 0 ? q->record->goal[12] : 0;
                s->exp += q->record->goal[11] > 0 ? q->record->goal[11] : 0;
                answer_result(s, 0x74, quest, 0);
                ++s->stats.completed;
                note(s, "demo server: quest %d completed (zen %d, exp %d)", quest, q->record->goal[12],
                     q->record->goal[11]);
                if (s->event)
                { /* the reward packets of a server are not modelled: a labelled chat line */
                    char line[160];
                    snprintf(line, sizeof line, "demo Quest complete (demo server): %d zen, %d exp",
                             q->record->goal[12] > 0 ? q->record->goal[12] : 0,
                             q->record->goal[11] > 0 ? q->record->goal[11] : 0);
                    s->event(s->user, line);
                }
            }
            else
            {
                answer_result(s, 0x74, quest, 4);
                note(s, "demo server: quest %d not complete", quest);
            }
        }
        break;
    default:
        break;
    }
}

void demo_kill(quest_demo *s, int32_t monster_class, int32_t world)
{
    /* NATIVE-QUEST-002: the guide's hunt step and the class-upgrade kills */
    const mu_guide_step *g = s->guide_state == 1 ? guide_step(s, s->guide_step) : NULL;
    if (g && g->w[0x8c / 4] == 2 && g->w[0x90 / 4] == monster_class)
    {
        int32_t need = g->w[0x98 / 4], count = s->guide_count + 1;
        guide_send(s, s->guide_step, count, count >= need ? 2 : 1);
        note(s, "demo server: guide step %d progress %d/%d", s->guide_step, count, need);
    }
    int classic_changed = 0;
    for (int i = 0; i < 5; i++)
        if (classic_state_of(s, mu_classic_current(&s->client)) == 1 && s->classic_kills[i][0] >= 0 &&
            s->classic_kills[i][0] == monster_class)
        {
            s->classic_kills[i][1]++;
            classic_changed = 1;
        }
    if (classic_changed)
    {
        uint8_t b[48] = {0xc1, 48, 0xa4};
        for (int i = 0; i < 5; i++)
        {
            put32(b + 8 + i * 8, s->classic_kills[i][0]);
            put32(b + 12 + i * 8, s->classic_kills[i][1]);
        }
        queue(s, b, sizeof b);
    }
    for (int32_t cat = MU_QUEST_CATEGORY_FIRST; cat <= MU_QUEST_CATEGORY_LAST; cat++)
    {
        const int32_t *a;
        size_t n = mu_quest_active(&s->client.qs, cat, &a);
        for (size_t i = 0; i < n; i++)
        {
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

void demo_progress(quest_demo *s, int32_t quest, int32_t count)
{
    const mu_quest *q = mu_quest_get(&s->client.qs, quest);
    if (!q || !q->record)
        return;
    answer_progress(s, quest, count, count >= q->record->goal[4] ? 2 : 1);
}

int32_t demo_offers(quest_demo *s, const char *text)
{
    s->noffers = 0;
    for (const char *p = text; p && *p;)
    {
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
        while ((word = strtok_r(NULL, " \t\r", &save)) && s->noffers < MU_QUEST_OFFERS)
        {
            mu_quest_offer *o = &s->offers[s->noffers++];
            o->npc = (int32_t)strtol(npc, NULL, 0);
            o->quest = (int32_t)strtol(word, NULL, 0);
            const char *colon = strchr(word, ':');
            o->state = colon ? (int32_t)strtol(colon + 1, NULL, 0) : 0;
        }
    }
    return s->noffers;
}

void demo_demo_state(quest_demo *s, const char *text)
{
    s->guide_step = -1;
    for (const char *p = text; p && *p;)
    {
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
        if (word && !strcmp(word, "guide") && (word = strtok_r(NULL, " \t\r", &save)))
        {
            int32_t step = 0, count = 0, state = 1;
            sscanf(word, "%d:%d:%d", &step, &count, &state);
            guide_send(s, step, count, state);
        }
        else if (word && !strcmp(word, "classic"))
        {
            while ((word = strtok_r(NULL, " \t\r", &save)))
            {
                int32_t q = -1, st = 0;
                if (sscanf(word, "%d:%d", &q, &st) == 2 && q >= 0 && q < 200)
                {
                    s->classic_states[q / 4] =
                        (uint8_t)((s->classic_states[q / 4] & ~(3 << ((q % 4) * 2))) | (st & 3) << ((q % 4) * 2));
                    if (q + 1 > s->classic_count)
                        s->classic_count = q + 1;
                }
            }
        }
    }
    if (s->classic_count)
    {
        uint8_t b[64] = {0xc1, 0, 0xc0, (uint8_t)s->classic_count};
        size_t bytes = (size_t)(s->classic_count / 4 + 1);
        memcpy(b + 4, s->classic_states, bytes < sizeof s->classic_states ? bytes : sizeof s->classic_states);
        queue(s, b, 4 + bytes);
    }
}

long demo_load_classic(quest_demo *s, const char *root)
{
    char path[2048];
    snprintf(path, sizeof path, "%s/Data/Local/quest.bmd", root ? root : ".");
    FILE *f = fopen(path, "rb");
    if (!f)
    {
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

static void *quest_open(mu_fixture_ctx *ctx, const char *args, char *error, size_t cap)
{
    (void)ctx;
    (void)error;
    (void)cap;
    quest_demo *s = calloc(1, sizeof *s);
    if (!s)
        return NULL;
    s->latency = mu_fx_arg_int(args, "latency", 4);
    s->guide_step = -1;
    for (int i = 0; i < 5; i++)
        s->classic_kills[i][0] = s->classic_kills[i][1] = -1;
    const char *dir = getenv("MU_LANG_DIR");
    if (dir)
        mu_quest_load_dir(&s->data, dir);
    mu_quest_client_init(&s->client, &s->data, NULL);
    s->client.play_tabs = s->client.play_move = 1;
    return s;
}
static int quest_request(void *self, mu_fixture_ctx *ctx, const mu_fixture_request *rq)
{
    (void)ctx;
    if (rq->opcode != 0xf6 && rq->opcode != 0xb3 && rq->opcode != 0x54)
        return 0;
    demo_request(self, rq->bytes, rq->length);
    return 1;
}
static void quest_step(void *self, mu_fixture_ctx *ctx, uint32_t now)
{
    (void)now;
    quest_demo *s = self;
    s->step = (int32_t)mu_fx_step(ctx);
    for (int i = 0; i < s->nqueue;)
    {
        if (s->queue[i].due > s->step)
        {
            ++i;
            continue;
        }
        mu_quest_packet q = s->queue[i];
        memmove(s->queue + i, s->queue + i + 1, (size_t)(--s->nqueue - i) * sizeof q);
        mu_packet p;
        mu_packet_begin(&p, q.bytes[0], q.bytes[2]);
        mu_packet_add(&p, q.bytes + 3, q.size - 3, 0);
        if (mu_fx_send(ctx, MU_CONN_GAME, &p, 0))
            continue;
        ++s->stats.answers;
        /* This is the fixture's server model. It never writes the session's client. */
        if (!(q.bytes[2] == 0xf6 && (q.bytes[3] == 0x70 || q.bytes[3] == 0x71)))
            mu_quest_receive(&s->client, q.bytes, q.size);
        if (q.size >= 8 && q.bytes[2] == 0xf6 && q.bytes[3] == 0x50 && s->client.guide)
        {
            s->guide_step = s->client.guide->current;
            s->guide_count = s->client.guide->count;
            s->guide_state = q.bytes[7] >= 3 ? 1 : q.bytes[7];
        }
    }
}
static int quest_command(void *self, mu_fixture_ctx *ctx, const char *cmd, char *error, size_t cap)
{
    (void)ctx;
    quest_demo *s = self;
    int a, b, c;
    if (sscanf(cmd, "count %d %d %d", &a, &b, &c) == 3)
        answer_progress(s, a, b, c);
    else if (sscanf(cmd, "accept %d", &a) == 1)
        answer_result(s, 0x72, a, 0);
    else if (sscanf(cmd, "giveup %d", &a) == 1)
        answer_result(s, 0x73, a, 0);
    else if (sscanf(cmd, "complete %d", &a) == 1)
        answer_result(s, 0x74, a, 0);
    else if (sscanf(cmd, "classic-state %d %d", &a, &b) == 2)
        classic_set(s, a, b);
    else if (sscanf(cmd, "travel %d %d %d", &a, &s->travel_x, &s->travel_y) == 3)
    {
        s->world = a;
        s->travel_answer = 0x56;
        ++s->travels;
    }
    else if (sscanf(cmd, "kill %d %d", &a, &b) == 2)
        demo_kill(s, a, b);
    else if (sscanf(cmd, "progress %d %d", &a, &b) == 2)
        demo_progress(s, a, b);
    else if (sscanf(cmd, "resume %d", &a) == 1)
        demo_travel_complete(s, a);
    else if (!strcmp(cmd, "talk"))
        demo_classic_talk(s);
    else if (!strncmp(cmd, "offers ", 7))
        demo_offers(s, cmd + 7);
    else if (!strncmp(cmd, "state ", 6))
        demo_demo_state(s, cmd + 6);
    else if (!strncmp(cmd, "classic ", 8))
        demo_load_classic(s, cmd + 8);
    else
    {
        snprintf(error, cap, "unknown quest command: %s", cmd);
        return -1;
    }
    return 0;
}
static void quest_close(void *self)
{
    quest_demo *s = self;
    mu_quest_client_free(&s->client);
    mu_quest_data_free(&s->data);
    free(s);
}
const mu_fixture_behavior mu_fx_quest = {"quest",    quest_open,    quest_request,
                                         quest_step, quest_command, quest_close};

/* Legacy demo-tool facade. It owns a fixture and a session, never client state. */
static quest_demo *server(mu_quest_session *s)
{
    return mu_fixture_behavior_state(s->fixture, "quest");
}
static void replay(mu_quest_session *s)
{
    mu_cue c[32];
    uint32_t lost;
    size_t n;
    while ((n = mu_session_cues(s->session, &s->cursor, c, 32, &lost)))
    {
        if (lost)
            s->cue_size = 0;
        for (size_t i = 0; i < n; i++)
        {
            if (c[i].kind != MU_CUE_WINDOW || strcmp(c[i].u.window.movie, "quest"))
                continue;
            if (c[i].u.window.args[1])
                s->cue_size = 0;
            else if (!s->cue_size)
                continue;
            size_t len = strlen(c[i].u.window.json);
            if (s->cue_size + len >= sizeof s->cue_line)
            {
                s->cue_size = 0;
                continue;
            }
            memcpy(s->cue_line + s->cue_size, c[i].u.window.json, len + 1);
            s->cue_size += len;
            if (!c[i].u.window.args[0])
            {
                ++s->stats.events;
                if (!strncmp(s->cue_line, "invoke ", 7) || !strncmp(s->cue_line, "value ", 6))
                    ++s->stats.invokes;
                if (s->event)
                    s->event(s->user, s->cue_line);
                s->cue_size = 0;
            }
        }
    }
}
int mu_quest_session_open(mu_quest_session *s, const char *dir, const char *demo_text, const mu_quest_host *host,
                          char *err, size_t cap)
{
    memset(s, 0, sizeof *s);
    char path[] = "/tmp/mu-quest-XXXXXX";
    int fd = mkstemp(path);
    if (fd < 0)
        return 1;
    FILE *f = fdopen(fd, "w");
    if (!f)
    {
        close(fd);
        unlink(path);
        snprintf(err, cap, "cannot create quest fixture");
        return 1;
    }
    fprintf(f, "endpoint game 127.0.0.1:55999\nuse quest latency=4\n");
    fclose(f);
    const char *scenario = getenv("MU_QUEST_SCENARIO");
    mu_fixture_options fo = {.scenario = scenario && *scenario ? scenario : path, .seed = 1};
    s->fixture = mu_fixture_open(&fo, err, cap);
    unlink(path);
    if (!s->fixture)
        return 1;
    if (!server(s))
    {
        snprintf(err, cap, "quest scenario must use quest behavior");
        mu_quest_session_close(s);
        return 1;
    }
    s->transport = mu_fixture_transport(s->fixture);
    mu_session_config cfg = {.transport = s->transport};
    mu_fixture_endpoint(s->fixture, "game", &cfg.connect_server);
    mu_session_seed seed = {.place = {.world = 0}, .level = 1};
    s->session = mu_session_open_seeded(&cfg, &seed, err, cap);
    if (!s->session || mu_session_quest_bind(s->session, dir, host))
    {
        mu_quest_session_close(s);
        snprintf(err, cap, "no quest tables");
        return 1;
    }
    s->client = mu_session_quest(s->session);
    /* The fixture needs the same static definitions, its own state. */
    quest_demo *d = server(s);
    if (dir && !d->data.nrecords)
    {
        mu_quest_client_free(&d->client);
        mu_quest_load_dir(&d->data, dir);
        mu_quest_client_init(&d->client, &d->data, NULL);
        d->client.play_tabs = 1;
    }
    demo_offers(d, demo_text);
    demo_demo_state(d, demo_text);
    s->cursor = mu_session_cue_cursor(s->session);
    s->ready = 1;
    return 0;
}
void mu_quest_session_close(mu_quest_session *s)
{
    if (!s)
        return;
    mu_session_close(s->session);
    mu_transport_free(s->transport);
    mu_fixture_close(s->fixture);
    memset(s, 0, sizeof *s);
}
void mu_quest_session_step(mu_quest_session *s)
{
    if (!s || !s->ready)
        return;
    /* Compatibility tool context; the session remains the only receive-handler owner. */
    quest_demo *d = server(s);
    d->client.hero_class = s->client->hero_class;
    d->client.hero_level = s->client->hero_level;
    d->client.hero_level_total = s->client->hero_level_total;
    mu_transport_flush(s->transport);
    mu_transport_poll(s->transport, (uint32_t)(++s->step * 40));
    mu_session_pump(s->session, (uint32_t)(s->step * 40));
    mu_sim sim = mu_session_sim_begin(s->session);
    mu_session_step(s->session, MU_DOMAIN_QUEST, &sim);
    mu_session_sim_end(s->session, &sim);
    if (d->travels > s->travels)
    {
        s->travels = d->travels;
        s->travel_answer = d->travel_answer;
        if (!s->travel || !s->travel(s->user, d->world, d->travel_x, d->travel_y))
            demo_travel_complete(d, 0);
    }
    uint32_t events = s->stats.events, invokes = s->stats.invokes;
    memcpy(&s->stats, &d->stats, sizeof s->stats);
    s->stats.events = events;
    s->stats.invokes = invokes;
    replay(s);
}
void mu_quest_session_npc_list(mu_quest_session *s, int32_t npc)
{
    mu_session_quest_window(s->session, MU_Q_NPC_LIST, NULL, NULL, npc, 0);
}
void mu_quest_session_classic_talk(mu_quest_session *s)
{
    demo_classic_talk(server(s));
}
void mu_quest_session_kill(mu_quest_session *s, int32_t m, int32_t w)
{
    demo_kill(server(s), m, w);
}
void mu_quest_session_progress(mu_quest_session *s, int32_t q, int32_t n)
{
    demo_progress(server(s), q, n);
}
void mu_quest_session_demo_state(mu_quest_session *s, const char *t)
{
    demo_demo_state(server(s), t);
}
int32_t mu_quest_session_offers(mu_quest_session *s, const char *t)
{
    return demo_offers(server(s), t);
}
long mu_quest_session_load_classic(mu_quest_session *s, const char *r)
{
    demo_load_classic(server(s), r);
    return mu_session_quest_classic(s->session, r);
}
void mu_quest_session_travel_complete(mu_quest_session *s, int ok)
{
    demo_travel_complete(server(s), ok);
    s->travel_answer = 0;
}
void mu_quest_session_toggle_info(mu_quest_session *s)
{
    mu_session_quest_window(s->session, MU_Q_TOGGLE, NULL, NULL, 0, 0);
    replay(s);
}
size_t mu_quest_session_size(void)
{
    return sizeof(mu_quest_session);
}
mu_quest_client *mu_quest_session_client(mu_quest_session *s)
{
    return (mu_quest_client *)s->client;
}
void mu_quest_session_set_event(mu_quest_session *s, void (*fn)(void *, const char *), void *u)
{
    s->event = fn;
    s->user = u;
}
void mu_quest_session_set_travel(mu_quest_session *s, int (*fn)(void *, int32_t, int32_t, int32_t))
{
    s->travel = fn;
}
void mu_quest_session_report(const mu_quest_session *s, FILE *out)
{
    if (!s || !s->ready)
        return;
    mu_session_status st;
    mu_session_status_get(s->session, &st);
    fprintf(out,
            "{\"quest\":{\"quests\":%zu,\"requests\":%u,\"answers\":%u,\"accepted\":%u,\"completed\":%u,"
            "\"progress\":%u,\"unbound\":%u,\"undecodable\":%u,\"active\":[",
            s->client->qs.nquests, s->stats.requests, s->stats.answers, s->stats.accepted, s->stats.completed,
            s->stats.progress, st.unhandled, st.undecodable);
    int first = 1;
    for (int cat = 2; cat <= 4; cat++)
    {
        const int32_t *a;
        size_t n = mu_quest_active(&s->client->qs, cat, &a);
        for (size_t i = 0; i < n; i++)
        {
            int32_t fields[4];
            mu_quest_fields(s->client, a[i], fields);
            fprintf(out, "%s{\"quest\":%d,\"state\":%d,\"count\":%d}", first ? "" : ",", a[i], fields[0],
                    fields[1]);
            first = 0;
        }
    }
    fprintf(out, "]}}\n");
}

int mu_quest_session_window(mu_quest_session *s, mu_quest_action a, const char *event, const char *text, double x,
                            double y)
{
    int rc = mu_session_quest_window(s->session, a, event, text, x, y);
    replay(s);
    return rc;
}

int mu_quest_session_command(mu_quest_session *s, const char *command)
{
    char error[256];
    return quest_command(server(s), NULL, command, error, sizeof error);
}
