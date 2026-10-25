/* behaviors/progress.c: core/mu_progress.c's DEMO server, ported to the fixture: it keeps the
 * server's view of the hero and answers with real frames through the session's transport.
 *
 * Copied, not moved: core/mu_progress.c stays unchanged until mu-walk / mu-world read the session
 * (stage 2, after WORLD-RT-001). Every rule below is the demo's choice (labelled DEMO there, kept
 * here verbatim): the kill experience (L + 25) * L / 3 times the rate with L = 1 + class % 40, five
 * free points per level (seven for class indices 3, 4, 6), the per-class HP/MP/SD/AG maxima and
 * start stats, the attack/magic speed divisors, a stat point accepted while points remain. The
 * level thresholds use the client's own experience table (mu_prg_exp_table, verified).
 *
 * What changed from the demo: the server keeps its own state (level, experience within the level,
 * stats, points) instead of reading the client's attribute record, and its answers are frames on
 * the game connection, due `latency` steps after the event:
 *   join            0x55 0x57 (the stats) and 0x55 0x94 (the speeds), what the demo applied at its join
 *   kill CLASS [KEY] 0x16 (as C1: the client refuses a plaintext 0x16 with its 4D 02 00 16 report
 *                   until the fixture can send C3), then A0 06 when the server's experience reaches next
 *   kill random     the same with a class from the fixture's rng (seeded runs)
 *   levelup         A0 06 at once
 *   master          A0 22 + A0 60 (a third-class hero's master level up)
 *   respawn map=M x=X y=Y dir=D money=Z   A0 30
 * and to the client's stat request (C1 05 01 00 STAT after XorData) A0 11, then 0x55 0x57 and, for
 * agility, 0x55 0x94.
 */
#include "../behavior.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../../../reconstructed/progress/progress.h"

#define PENDING 64

typedef struct fx_answer {
    uint32_t due;
    uint8_t bytes[64];
    size_t size;
} fx_answer;

typedef struct fx_progress {
    int32_t exp_rate, latency, kill_head;
    uint8_t class_byte;
    int32_t level, master_level, master_points;
    int64_t exp, next, master_exp, master_next;
    int32_t points;
    int32_t stats[5];
    fx_answer pending[PENDING];
    int npending;
} fx_progress;

/* ---- DEMO tables (core/mu_progress.c) ------------------------------------------------------- */

static const int16_t START[16][5] = {
    {18, 18, 15, 30, 0}, {28, 20, 25, 10, 0}, {22, 25, 20, 15, 0}, {26, 26, 26, 26, 0},
    {26, 20, 20, 15, 25}, {21, 21, 18, 23, 0}, {32, 27, 25, 20, 0}, {30, 30, 25, 24, 0},
    {13, 18, 14, 40, 0}, {28, 30, 15, 10, 0}, {20, 18, 20, 30, 0}, {15, 20, 15, 40, 0},
    {15, 20, 15, 40, 0}, {25, 28, 15, 10, 0}, {15, 25, 15, 30, 0}, {28, 22, 20, 12, 0}};

static const int16_t MAXIMA[16][6] = {
    {600, 10, 20, 600, 20, 20}, {1100, 20, 30, 200, 5, 10}, {800, 10, 20, 300, 15, 15}, {1100, 10, 20, 600, 10, 20},
    {900, 15, 20, 400, 10, 15}, {700, 10, 20, 400, 15, 15}, {1000, 13, 20, 400, 10, 15}, {1100, 20, 30, 200, 5, 10},
    {600, 10, 20, 600, 20, 20}, {1100, 20, 30, 200, 5, 10}, {800, 10, 20, 400, 15, 15}, {600, 10, 20, 600, 20, 20},
    {600, 10, 20, 600, 20, 20}, {1100, 20, 30, 200, 5, 10}, {700, 10, 20, 500, 15, 20}, {1100, 20, 30, 200, 5, 10}};

static const uint8_t SPEED_DIV[16][2] = {{20, 10}, {15, 20}, {50, 50}, {15, 20}, {10, 10}, {20, 20}, {9, 9}, {15, 15},
                                         {20, 10}, {15, 20}, {15, 15}, {20, 10}, {20, 10}, {15, 20}, {20, 10}, {15, 20}};

static void demo_maxima(int32_t cls, int32_t level, const int32_t s[5], int32_t out[4])
{
    const int16_t *m = MAXIMA[cls & 15];
    const int16_t *st = START[cls & 15];
    int32_t lv = level > 1 ? level - 1 : 0;
    out[0] = m[0] + lv * m[1] / 10 + (s[2] - st[2]) * m[2] / 10;
    out[1] = m[3] + lv * m[4] / 10 + (s[3] - st[3]) * m[5] / 10;
    out[2] = (s[0] + s[1] + s[2] + s[3] + s[4]) * 6 / 10 + level * 3;
    out[3] = s[0] * 15 / 100 + s[1] * 2 / 10 + s[2] * 3 / 10 + s[3];
    for (int i = 0; i < 4; i++)
        if (out[i] < 1)
            out[i] = 1;
        else if (out[i] > 0xffff)
            out[i] = 0xffff;
}

static int64_t demo_kill_exp(int32_t server_class, int32_t rate)
{
    int64_t l = 1 + (server_class < 0 ? 0 : server_class) % 40;
    return (l + 25) * l / 3 * (rate > 0 ? rate : 1);
}

static int32_t points_per_level(int32_t cls)
{
    return cls == 3 || cls == 4 || cls == 6 ? 7 : 5;
}

/* ---- answers ---------------------------------------------------------------------------------- */

static void put16(uint8_t *b, int off, int32_t v)
{
    b[off] = (uint8_t)v;
    b[off + 1] = (uint8_t)(v >> 8);
}

static void queue(fx_progress *p, mu_fixture_ctx *ctx, const uint8_t *b, size_t n, uint32_t delay)
{
    if (p->npending >= PENDING || n > sizeof p->pending[0].bytes)
        return;
    fx_answer *a = &p->pending[p->npending++];
    a->due = mu_fx_step(ctx) + delay;
    memcpy(a->bytes, b, n);
    a->size = n;
}

static void speed_frame(fx_progress *p, mu_fixture_ctx *ctx)
{
    int32_t cls = p->class_byte & 15;
    int32_t agi = p->stats[1];
    uint8_t b[0x0c] = {0xc1, 0x0c, 0x55, 0x94};
    int32_t atk = 20 + agi / SPEED_DIV[cls][0], mag = 20 + agi / SPEED_DIV[cls][1];
    put16(b, 4, atk);
    put16(b, 8, mag);
    queue(p, ctx, b, sizeof b, (uint32_t)p->latency);
}

static void stats_frame(fx_progress *p, mu_fixture_ctx *ctx)
{
    uint8_t b[0x1c] = {0xc1, 0x1c, 0x55, 0x57};
    for (int i = 0; i < 5; i++) {
        put16(b, 4 + 4 * i, p->stats[i]);
        put16(b, 6 + 4 * i, 0);   /* added stats: no items or buffs on the fixture's hero */
    }
    /* +0x18: the window's float row (0.0) */
    queue(p, ctx, b, sizeof b, (uint32_t)p->latency);
}

static void level_up(fx_progress *p, mu_fixture_ctx *ctx)
{
    int32_t cls = p->class_byte & 15;
    if (p->level >= 400)
        return;
    p->level++;
    p->points += points_per_level(cls);
    p->exp = 0;   /* DEMO: the rest of the experience is dropped at the level up */
    p->next = mu_prg_exp_table(p->level + 1) - mu_prg_exp_table(p->level);
    int32_t mx[4];
    demo_maxima(cls, p->level, p->stats, mx);
    uint8_t b[0x18] = {0xc1, 0x18, 0xa0, 0x06};
    put16(b, 4, p->level);
    put16(b, 6, p->points);
    for (int i = 0; i < 4; i++)
        put16(b, 8 + 2 * i, mx[i]);
    queue(p, ctx, b, sizeof b, (uint32_t)p->latency);
}

static void master_up(fx_progress *p, mu_fixture_ctx *ctx)
{
    p->master_level++;
    p->master_points++;
    uint8_t up[0x0c] = {0xc1, 0x0c, 0xa0, 0x22};
    put16(up, 4, p->master_level);
    put16(up, 6, p->master_points);
    queue(p, ctx, up, sizeof up, (uint32_t)p->latency);
    uint8_t ex[0x18] = {0xc1, 0x18, 0xa0, 0x60};
    put16(ex, 4, p->master_level);
    int64_t lv = p->level + p->master_level;
    uint64_t next = (uint64_t)(mu_prg_exp_table(lv + 1) - mu_prg_exp_table(lv));
    for (int i = 0; i < 8; i++)
        ex[0xe + i] = (uint8_t)(next >> (56 - 8 * i));   /* master experience restarts at 0 */
    p->master_exp = 0;
    p->master_next = (int64_t)next;
    queue(p, ctx, ex, sizeof ex, (uint32_t)p->latency);
}

static int kill(fx_progress *p, mu_fixture_ctx *ctx, int32_t server_class, int32_t key)
{
    int64_t gain = demo_kill_exp(server_class, p->exp_rate);
    if (gain > 0xffff)
        gain = 0xffff;   /* the packet's word */
    int32_t k = (key & 0x7fff) | 0x8000;
    uint8_t b[10] = {(uint8_t)p->kill_head, 10, 0x16, (uint8_t)(k >> 8), (uint8_t)k, (uint8_t)(gain >> 8),
                     (uint8_t)gain, 0, 0, 0};
    queue(p, ctx, b, sizeof b, (uint32_t)p->latency);
    int third = (p->class_byte >> 5 & 1) == 1;
    if (third && p->level >= 400) {
        p->master_exp += gain;
        if (p->master_exp >= p->master_next)
            master_up(p, ctx);
    } else {
        p->exp += gain;
        if (p->exp >= p->next)
            level_up(p, ctx);
    }
    return 0;
}

static void respawn(fx_progress *p, mu_fixture_ctx *ctx, const char *args)
{
    int32_t cls = p->class_byte & 15, mx[4];
    demo_maxima(cls, p->level, p->stats, mx);
    uint8_t b[0x20];
    memset(b, 0, sizeof b);
    b[0] = 0xc1;
    b[1] = (uint8_t)sizeof b;
    b[2] = 0xa0;
    b[3] = 0x30;
    b[4] = (uint8_t)mu_fx_arg_int(args, "x", 0);
    b[5] = (uint8_t)mu_fx_arg_int(args, "y", 0);
    put16(b, 6, mu_fx_arg_int(args, "map", 0));
    b[8] = (uint8_t)mu_fx_arg_int(args, "dir", 1);
    for (int i = 0; i < 4; i++)
        put16(b, 0xa + 2 * i, mx[i]);
    int third = (p->class_byte >> 5 & 1) == 1;
    uint64_t total = third ? (uint64_t)p->master_exp : (uint64_t)mu_prg_exp_table(p->level) + (uint64_t)p->exp;
    for (int i = 0; i < 8; i++)
        b[0x12 + i] = (uint8_t)(total >> (56 - 8 * i));
    uint32_t money = (uint32_t)mu_fx_arg_int(args, "money", 0);
    for (int i = 0; i < 4; i++)
        b[0x1c + i] = (uint8_t)(money >> (8 * i));
    queue(p, ctx, b, sizeof b, (uint32_t)p->latency);
}

/* ---- the behaviour ------------------------------------------------------------------------------- */

static void *progress_open(mu_fixture_ctx *ctx, const char *args, char *error, size_t error_size)
{
    (void)ctx;
    fx_progress *p = calloc(1, sizeof *p);
    if (!p) {
        snprintf(error, error_size, "out of memory");
        return NULL;
    }
    p->exp_rate = mu_fx_arg_int(args, "exp_rate", 1);
    p->latency = mu_fx_arg_int(args, "latency", 2);
    if (p->latency < 0)
        p->latency = 0;
    char head[8] = "c1";
    mu_fx_arg_str(args, "kill_head", head, sizeof head);
    if (strcmp(head, "c1") != 0) {
        snprintf(error, error_size, "kill_head=%s: only c1 until the fixture has the CryptoModule", head);
        free(p);
        return NULL;
    }
    p->kill_head = 0xc1;
    p->class_byte = (uint8_t)mu_fx_arg_int(args, "class", 0x01);
    p->level = mu_fx_arg_int(args, "level", 1);
    p->points = mu_fx_arg_int(args, "points", 0);
    p->master_level = mu_fx_arg_int(args, "master_level", 0);
    int32_t cls = p->class_byte & 15;
    for (int i = 0; i < 5; i++)
        p->stats[i] = (i == 4 && cls != 4) ? 0 : START[cls][i];
    p->next = mu_prg_exp_table(p->level + 1) - mu_prg_exp_table(p->level);
    int64_t lv = p->level + p->master_level;
    p->master_next = mu_prg_exp_table(lv + 1) - mu_prg_exp_table(lv);
    return p;
}

static int progress_on_command(void *self, mu_fixture_ctx *ctx, const char *command, char *error, size_t error_size)
{
    fx_progress *p = self;
    char verb[16] = {0};
    int used = 0;
    sscanf(command, "%15s%n", verb, &used);
    const char *rest = command + used;
    if (!strcmp(verb, "join")) {
        stats_frame(p, ctx);
        speed_frame(p, ctx);
        return 0;
    }
    if (!strcmp(verb, "kill")) {
        char what[16] = {0};
        int key = 0x0100;
        int n = sscanf(rest, "%15s %i", what, &key);
        if (n < 1) {
            snprintf(error, error_size, "kill CLASS|random [KEY]");
            return -1;
        }
        int32_t cls = !strcmp(what, "random") ? (int32_t)(mu_fx_rand(ctx) % 40u) : (int32_t)strtol(what, NULL, 0);
        return kill(p, ctx, cls, key);
    }
    if (!strcmp(verb, "levelup")) {
        level_up(p, ctx);
        return 0;
    }
    if (!strcmp(verb, "master")) {
        master_up(p, ctx);
        return 0;
    }
    if (!strcmp(verb, "respawn")) {
        respawn(p, ctx, rest);
        return 0;
    }
    snprintf(error, error_size, "unknown progress command %s", verb);
    return -1;
}

static int progress_on_request(void *self, mu_fixture_ctx *ctx, const mu_fixture_request *rq)
{
    fx_progress *p = self;
    /* the stat request of 0x00b48aca, XorData undone: C1 05 01 00 STAT */
    if (rq->head != 0xc1 || rq->opcode != 0x01 || rq->length < 5 || rq->bytes[3] != 0)
        return 0;
    int32_t stat = rq->bytes[4];
    uint8_t b[0x0c] = {0xc1, 0x0c, 0xa0, 0x11, (uint8_t)stat};
    if (stat >= 0 && stat < 5 && p->points > 0 && p->stats[stat] < 0xffff) {
        p->stats[stat]++;
        p->points--;
        int32_t mx[4];
        demo_maxima(p->class_byte & 15, p->level, p->stats, mx);
        b[4] = (uint8_t)(0x10 | stat);
        put16(b, 6, stat == 3 ? mx[1] : mx[0]);
        put16(b, 8, mx[2]);
        put16(b, 0xa, mx[3]);
        queue(p, ctx, b, sizeof b, (uint32_t)p->latency);
        stats_frame(p, ctx);
        if (stat == 1)
            speed_frame(p, ctx);
    } else {
        queue(p, ctx, b, sizeof b, (uint32_t)p->latency);
    }
    return 1;
}

static void progress_on_step(void *self, mu_fixture_ctx *ctx, uint32_t now_ms)
{
    fx_progress *p = self;
    (void)now_ms;
    int kept = 0;
    for (int i = 0; i < p->npending; ++i) {
        fx_answer a = p->pending[i];
        if (a.due > mu_fx_step(ctx)) {
            p->pending[kept++] = a;
            continue;
        }
        /* through the verified builder: Begin(head, opcode) + the body, plain (no server XorData) */
        mu_packet pk;
        mu_packet_begin(&pk, a.bytes[0], a.bytes[2]);
        mu_packet_add(&pk, a.bytes + 3, a.size - 3, 0);
        mu_fx_send(ctx, MU_CONN_GAME, &pk, 0);
    }
    p->npending = kept;
}

static void progress_close(void *self)
{
    free(self);
}

const mu_fixture_behavior mu_fx_progress = {
    .name = "progress",
    .open = progress_open,
    .on_request = progress_on_request,
    .on_step = progress_on_step,
    .on_command = progress_on_command,
    .close = progress_close,
};
