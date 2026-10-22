/* Character progression in the native client (NATIVE-PROGRESS-001); see mu_progress.h. */
#include "mu_progress.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ---- the environment of the reconstructed routines -------------------------------------------- */

static void env_emit(void *user, const char *line);

static const char *env_text(void *user, int32_t index)
{
    if (index == 0x10be) {   /* the speed row's format (the client's GlobalText 4286) */
        mu_progress *q = user;
        const char *t = q->global_text ? q->global_text(q->context, index) : NULL;
        return t && *t ? t : "%d / %d";
    }
    mu_progress *p = user;
    const char *t = p->global_text ? p->global_text(p->context, index) : NULL;
    if (t && *t)
        return t;
    /* stand-ins with the client's format conversions (GlobalText 0x1e6 / 0x6d6, NATIVE-LANG-001 when loaded) */
    if (index == 0x1e6)
        return "Obtained %lld Exp";
    if (index == 0x6d6)
        return "Master EXP achievement %lld";
    return "";
}

static int env_window(void *user, uint32_t getter)
{
    (void)user;
    /* the main frame (exp bar, HP/MP), the level window and the master window exist in the HUD */
    return getter == 0x0095c50b || getter == 0x0095c5da || getter == 0x009a19ae;
}

static uint8_t *env_character(void *user, int32_t key, int32_t *index)
{
    mu_progress *p = user;
    if (key < 0)
        return NULL;
    *index = key;
    return p->monster;
}

static mu_prg_env make_env(mu_progress *p)
{
    mu_prg_env e;
    memset(&e, 0, sizeof e);
    e.user = p;
    e.attr = p->attr;
    e.hero_class = p->hero[0x12];
    e.emit = env_emit;
    e.global_text = env_text;
    e.window = env_window;
    e.hero = p->hero;
    e.character = env_character;
    return e;
}

static void env_emit(void *user, const char *line)
{
    mu_progress *p = user;
    if (!strncmp(line, "invoke setExpData ", 18)) {
        snprintf(p->exp_json, sizeof p->exp_json, "%s", line + 18);
        p->exp_dirty = 1;
    } else if (!strcmp(line, "call 00a00f4a")) {
        mu_prg_level_exp(p->attr);   /* the hero's level experience (verified) */
    } else if (!strcmp(line, "call 00a00fb7")) {
        mu_progress_recalc(p);       /* the stat machine's recalculation flag: recalculated at once */
    } else if (!strcmp(line, "call 00c51256")) {
        mu_prg_env e = make_env(p);
        mu_prg_exp_bar(&e, &p->bar, 0x546);   /* 0x016963bf: 1350 on a normal server */
    } else if (!strcmp(line, "call 00b40380")) {
        mu_prg_env e = make_env(p);   /* the character window's speed row (the window is always open here) */
        mu_prg_speed_row(&e, p->attr[MU_PRG_A_CLASS] & 15, p->speed_row, 1);
    } else if (!strncmp(line, "call 00b3e33f 15 \"", 18)) {
        size_t n = 0;
        for (const char *s = line + 18; *s && *s != '"' && n + 1 < sizeof p->speed_text; s++)
            p->speed_text[n++] = *s;
        p->speed_text[n] = 0;
    }
    if (!strncmp(line, "call 00b45", 10) || !strncmp(line, "call 00b3e", 10))
        p->hero_dirty = 1;
    if (p->line)
        p->line(p->context, line);
}

/* ---- DEMO server rules ---------------------------------------------------------------------------- */

static const int16_t START[16][5] = {
    {18, 18, 15, 30, 0}, {28, 20, 25, 10, 0}, {22, 25, 20, 15, 0}, {26, 26, 26, 26, 0},
    {26, 20, 20, 15, 25}, {21, 21, 18, 23, 0}, {32, 27, 25, 20, 0}, {30, 30, 25, 24, 0},
    {13, 18, 14, 40, 0}, {28, 30, 15, 10, 0}, {20, 18, 20, 30, 0}, {15, 20, 15, 40, 0},
    {15, 20, 15, 40, 0}, {25, 28, 15, 10, 0}, {15, 25, 15, 30, 0}, {28, 22, 20, 12, 0}};

/* base HP, HP per level x10, HP per vitality x10, base MP, MP per level x10, MP per energy x10 (DEMO) */
static const int16_t MAXIMA[16][6] = {
    {60, 10, 20, 60, 20, 20}, {110, 20, 30, 20, 5, 10}, {80, 10, 20, 30, 15, 15}, {110, 10, 20, 60, 10, 20},
    {90, 15, 20, 40, 10, 15}, {70, 10, 20, 40, 15, 15}, {100, 13, 20, 40, 10, 15}, {110, 20, 30, 20, 5, 10},
    {60, 10, 20, 60, 20, 20}, {110, 20, 30, 20, 5, 10}, {80, 10, 20, 40, 15, 15}, {60, 10, 20, 60, 20, 20},
    {60, 10, 20, 60, 20, 20}, {110, 20, 30, 20, 5, 10}, {70, 10, 20, 50, 15, 20}, {110, 20, 30, 20, 5, 10}};

void mu_progress_demo_maxima(int32_t cls, int32_t level, const int32_t s[5], int32_t out[4])
{
    const int16_t *m = MAXIMA[cls & 15];
    const int16_t *st = START[cls & 15];
    int32_t lv = level > 1 ? level - 1 : 0;
    out[0] = m[0] + lv * m[1] / 10 + (s[2] - st[2]) * m[2] / 10;
    out[1] = m[3] + lv * m[4] / 10 + (s[3] - st[3]) * m[5] / 10;
    out[2] = (s[0] + s[1] + s[2] + s[3] + s[4]) * 12 / 10 + level * 10;
    out[3] = s[0] * 15 / 100 + s[1] * 2 / 10 + s[2] * 3 / 10 + s[3];
    for (int i = 0; i < 4; i++)
        if (out[i] < 1)
            out[i] = 1;
        else if (out[i] > 0xffff)
            out[i] = 0xffff;
}

int64_t mu_progress_demo_kill_exp(int32_t server_class, int32_t rate)
{
    int64_t l = 1 + (server_class < 0 ? 0 : server_class) % 40;
    return (l + 25) * l / 3 * (rate > 0 ? rate : 1);
}

static int32_t points_per_level(int32_t cls)
{
    return cls == 3 || cls == 4 || cls == 6 ? 7 : 5;
}

static void queue(mu_progress *p, int32_t kind, const uint8_t *data, int32_t size)
{
    if (p->npending >= MU_PROGRESS_PENDING)
        return;
    mu_progress_packet *q = &p->pending[p->npending++];
    memset(q, 0, sizeof *q);
    q->due = p->step + (p->config.latency_steps > 0 ? p->config.latency_steps : 0);
    q->kind = kind;
    memcpy(q->data, data, (size_t)size);
    q->size = size;
}

static void put16(uint8_t *b, int off, int32_t v)
{
    b[off] = (uint8_t)v;
    b[off + 1] = (uint8_t)(v >> 8);
}

/* DEMO: attack and magic speed divisors of agility per class index */
static const uint8_t SPEED_DIV[16][2] = {{20, 10}, {15, 20}, {50, 50}, {15, 20}, {10, 10}, {20, 20}, {9, 9}, {15, 15},
                                         {20, 10}, {15, 20}, {15, 15}, {20, 10}, {20, 10}, {15, 20}, {20, 10}, {15, 20}};

static void server_speed_packet(mu_progress *p)
{
    int32_t cls = p->attr[MU_PRG_A_CLASS] & 15;
    int32_t agi = p->server_stats[1] + mu_prg_u16(p->attr, MU_PRG_A_ADD_DEX);
    uint8_t b[0x0c] = {0xc1, 0x0c, 0x55, 0x94};
    int32_t atk = agi / SPEED_DIV[cls][0], mag = agi / SPEED_DIV[cls][1];
    b[4] = (uint8_t)atk;
    b[5] = (uint8_t)(atk >> 8);
    b[8] = (uint8_t)mag;
    b[9] = (uint8_t)(mag >> 8);
    queue(p, MU_PRGK_SPEED, b, (int32_t)sizeof b);
}

static void server_stats_packet(mu_progress *p)
{
    uint8_t b[0x1c] = {0xc1, 0x1c, 0x55, 0x57};
    static const size_t ADD[5] = {MU_PRG_A_ADD_STR, MU_PRG_A_ADD_DEX, MU_PRG_A_ADD_VIT, MU_PRG_A_ADD_ENE,
                                  MU_PRG_A_ADD_CMD};
    for (int i = 0; i < 5; i++) {
        put16(b, 4 + 4 * i, p->server_stats[i]);
        put16(b, 6 + 4 * i, mu_prg_u16(p->attr, ADD[i]));
    }
    memcpy(b + 0x18, &p->stat_window.rate, 4);
    queue(p, MU_PRGK_STATS, b, (int32_t)sizeof b);
}

/* ---- the hero ------------------------------------------------------------------------------------------ */

void mu_progress_default_config(mu_progress_config *c)
{
    memset(c, 0, sizeof *c);
    c->class_byte = 0x01;
    c->level = 1;
    c->exp_rate = 1;
    c->latency_steps = 2;
}

void mu_progress_recalc(mu_progress *p)
{
    mu_prg_env e = make_env(p);
    static const int32_t zero[5] = {0, 0, 0, 0, 0};
    mu_prg_calc_class(&e, p->attr[MU_PRG_A_CLASS] & 15, zero);
    mu_prg_calc_totals(p->attr, p->machine, zero);
    p->hero_dirty = 1;
}

void mu_progress_init(mu_progress *p, const mu_progress_config *config)
{
    void (*line)(void *, const char *) = p->line;
    void *context = p->context;
    const char *(*text)(void *, int32_t) = p->global_text;
    memset(p, 0, sizeof *p);
    p->line = line;
    p->context = context;
    p->global_text = text;
    p->now_ms = 100000;   /* GetTickCount of a running session (the request throttle compares with 0 at first) */
    if (config)
        p->config = *config;
    else
        mu_progress_default_config(&p->config);
    uint8_t *a = p->attr;
    int32_t cls = p->config.class_byte & 15;
    p->hero[0x12] = p->config.class_byte;
    a[MU_PRG_A_CLASS] = p->config.class_byte;
    mu_prg_set32(a, MU_PRG_A_LEVEL, (uint32_t)(p->config.level > 0 ? p->config.level : 1));
    mu_prg_set32(a, MU_PRG_A_MLEVEL, (uint32_t)p->config.master_level);
    static const size_t BASE[5] = {MU_PRG_A_STRENGTH, MU_PRG_A_DEXTERITY, MU_PRG_A_VITALITY, MU_PRG_A_ENERGY,
                                   MU_PRG_A_COMMAND};
    for (int i = 0; i < 5; i++) {
        int32_t v = p->config.stats[i] > 0 ? p->config.stats[i] : START[cls][i];
        if (i == 4 && cls != 4 && p->config.stats[i] <= 0)
            v = 0;
        p->server_stats[i] = v;
        mu_prg_set16(a, BASE[i], (uint32_t)v);
    }
    mu_prg_set16(a, MU_PRG_A_POINTS, (uint32_t)p->config.points);
    int32_t mx[4];
    mu_progress_demo_maxima(cls, mu_prg_i32(a, MU_PRG_A_LEVEL), p->server_stats, mx);
    mu_prg_set32(a, MU_PRG_A_LIFE_MAX, (uint32_t)mx[0]);
    mu_prg_set32(a, MU_PRG_A_LIFE, (uint32_t)mx[0]);
    mu_prg_set32(a, MU_PRG_A_MANA_MAX, (uint32_t)mx[1]);
    mu_prg_set32(a, MU_PRG_A_MANA, (uint32_t)mx[1]);
    mu_prg_set32(a, MU_PRG_A_SHIELD_MAX, (uint32_t)mx[2]);
    mu_prg_set32(a, MU_PRG_A_AG_MAX, (uint32_t)mx[3]);
    mu_prg_level_exp(a);
    mu_prg_set64(a, MU_PRG_A_EXP, (uint64_t)(p->config.exp > 0 ? p->config.exp : 0));
    int64_t ml = p->config.master_level, base = mu_prg_i32(a, MU_PRG_A_LEVEL);
    mu_prg_set64(a, MU_PRG_A_MNEXT_EXP,
                 (uint64_t)(mu_prg_exp_table(base + ml + 1) - mu_prg_exp_table(base + ml)));
    for (int i = 0; i < 5; i++) {
        p->stat_window.shown[2 * i] = (uint16_t)p->server_stats[i];
        p->stat_window.total[i] = (uint16_t)p->server_stats[i];
    }
    mu_progress_recalc(p);
    mu_prg_env e = make_env(p);
    mu_prg_exp_bar(&e, &p->bar, 0x546);
    server_speed_packet(p);
    snprintf(p->last, sizeof p->last, "join: class %d level %d", cls, mu_prg_i32(a, MU_PRG_A_LEVEL));
}

/* ---- DEMO server ---------------------------------------------------------------------------------- */

static void server_level_up(mu_progress *p)
{
    uint8_t *a = p->attr;
    int32_t cls = a[MU_PRG_A_CLASS] & 15;
    int32_t level = mu_prg_i32(a, MU_PRG_A_LEVEL) + 1;
    if (level > 400)
        return;
    int32_t points = mu_prg_u16(a, MU_PRG_A_POINTS) + points_per_level(cls);
    int32_t mx[4];
    mu_progress_demo_maxima(cls, level, p->server_stats, mx);
    uint8_t b[0x18] = {0xc1, 0x18, 0xa0, 0x06};
    put16(b, 4, level);
    put16(b, 6, points);
    for (int i = 0; i < 4; i++)
        put16(b, 8 + 2 * i, mx[i]);
    for (int i = 0; i < 4; i++)
        put16(b, 0x10 + 2 * i, mu_prg_u16(a, MU_PRG_A_ADD_POINT + 2 * (size_t)i));
    queue(p, MU_PRGK_LEVELUP, b, (int32_t)sizeof b);
}

static void server_master_up(mu_progress *p)
{
    uint8_t *a = p->attr;
    int32_t ml = mu_prg_i32(a, MU_PRG_A_MLEVEL) + 1;
    uint8_t up[0x0c] = {0xc1, 0x0c, 0xa0, 0x22};
    put16(up, 4, ml);
    put16(up, 6, mu_prg_i32(a, MU_PRG_A_MPOINTS) + 1);
    put16(up, 8, mu_prg_i32(a, MU_PRG_A_M34));
    put16(up, 0xa, mu_prg_i32(a, MU_PRG_A_M3C));
    queue(p, MU_PRGK_MASTER_UP, up, (int32_t)sizeof up);
    uint8_t ex[0x18] = {0xc1, 0x18, 0xa0, 0x60};
    put16(ex, 4, ml);
    int64_t lv = mu_prg_i32(a, MU_PRG_A_LEVEL) + ml;
    uint64_t next = (uint64_t)(mu_prg_exp_table(lv + 1) - mu_prg_exp_table(lv));
    for (int i = 0; i < 8; i++) {
        ex[6 + i] = 0;   /* master experience restarts */
        ex[0xe + i] = (uint8_t)(next >> (56 - 8 * i));
    }
    put16(ex, 0x16, mu_prg_i32(a, MU_PRG_A_M34));
    queue(p, MU_PRGK_MASTER_EXP, ex, (int32_t)sizeof ex);
}

void mu_progress_kill(mu_progress *p, int32_t server_class, int32_t monster_key)
{
    uint8_t *a = p->attr;
    int64_t gain = mu_progress_demo_kill_exp(server_class, p->config.exp_rate);
    if (gain > 0xffff)
        gain = 0xffff;   /* the packet's word */
    int32_t key = (monster_key & 0x7fff) | 0x8000;
    uint8_t b[10] = {0xc1, 10, 0x16, (uint8_t)(key >> 8), (uint8_t)key, (uint8_t)(gain >> 8), (uint8_t)gain, 0, 0, 0};
    queue(p, MU_PRGK_KILL, b, (int32_t)sizeof b);
    p->kills++;
    snprintf(p->last, sizeof p->last, "kill: class %d exp %lld (DEMO)", server_class, (long long)gain);
    /* the server's view of the experience after this kill decides the level up */
    int third = (p->hero[0x12] >> 5 & 1) == 1;
    uint64_t pending = 0;
    for (int i = 0; i < p->npending; i++) {
        if (p->pending[i].kind == MU_PRGK_LEVELUP || p->pending[i].kind == MU_PRGK_MASTER_UP)
            return;   /* the level up is on its way */
        if (p->pending[i].kind == MU_PRGK_KILL)
            pending += (uint64_t)(p->pending[i].data[5] << 8 | p->pending[i].data[6]);
    }
    if (third && mu_prg_i32(a, MU_PRG_A_LEVEL) >= 400) {
        if (mu_prg_u64(a, MU_PRG_A_MEXP) + pending >= mu_prg_u64(a, MU_PRG_A_MNEXT_EXP))
            server_master_up(p);
    } else if (!third && mu_prg_u64(a, MU_PRG_A_EXP) + pending >= mu_prg_u64(a, MU_PRG_A_NEXT_EXP)) {
        server_level_up(p);
    }
    snprintf(p->last, sizeof p->last, "kill: class %d exp %lld (DEMO)", server_class, (long long)gain);
}

int32_t mu_progress_button(mu_progress *p, double row)
{
    int32_t stat = mu_prg_stat_button(p->attr, row);
    if (stat < 0)
        return -1;
    mu_prg_env e = make_env(p);
    uint8_t req[5];
    if (!mu_prg_stat_request(&e, &p->last_request, p->now_ms, stat, req))
        return -1;
    p->requests++;
    /* DEMO server: accepted while the server's points remain */
    int32_t points = mu_prg_u16(p->attr, MU_PRG_A_POINTS);
    uint8_t b[0x0c] = {0xc1, 0x0c, 0xa0, 0x11, (uint8_t)stat};
    if (points > 0 && p->server_stats[stat] < 0xffff) {
        p->server_stats[stat]++;
        p->accepted++;
        int32_t mx[4];
        mu_progress_demo_maxima(p->attr[MU_PRG_A_CLASS] & 15, mu_prg_i32(p->attr, MU_PRG_A_LEVEL), p->server_stats,
                                mx);
        b[4] = (uint8_t)(0x10 | stat);
        put16(b, 6, stat == 3 ? mx[1] : mx[0]);
        put16(b, 8, mx[2]);
        put16(b, 0xa, mx[3]);
        queue(p, MU_PRGK_POINT, b, (int32_t)sizeof b);
        server_stats_packet(p);
        if (stat == 1)
            server_speed_packet(p);
    } else {
        queue(p, MU_PRGK_POINT, b, (int32_t)sizeof b);
    }
    snprintf(p->last, sizeof p->last, "request: stat %d (row %g)", stat, row);
    return stat;
}

void mu_progress_step(mu_progress *p)
{
    p->step++;
    p->now_ms += 40;
    int32_t kept = 0;
    for (int32_t i = 0; i < p->npending; i++) {
        mu_progress_packet q = p->pending[i];
        if (q.due > p->step) {
            p->pending[kept++] = q;
            continue;
        }
        mu_prg_env e = make_env(p);
        switch (q.kind) {
        case MU_PRGK_KILL: {
            uint8_t report[5];
            memset(p->monster, 0, sizeof p->monster);
            mu_prg_recv_kill_exp(&e, q.data, 1, report);
            break;
        }
        case MU_PRGK_LEVELUP:
            mu_prg_recv_levelup(&e, q.data);
            p->level_ups++;
            snprintf(p->last, sizeof p->last, "level up: %d", mu_prg_i32(p->attr, MU_PRG_A_LEVEL));
            break;
        case MU_PRGK_POINT:
            mu_prg_recv_point(&e, q.data);
            break;
        case MU_PRGK_STATS:
            mu_prg_recv_stats(&e, &p->stat_window, q.data);
            for (int k = 0; k < 5; k++)   /* what the window shows from now on (layer bookkeeping) */
                p->stat_window.shown[2 * k] = (uint16_t)(q.data[4 + 4 * k] | q.data[5 + 4 * k] << 8);
            break;
        case MU_PRGK_MASTER_UP:
            mu_prg_recv_master_levelup(&e, q.data);
            p->master_level_ups++;
            break;
        case MU_PRGK_MASTER_EXP:
            mu_prg_recv_master_exp(&e, q.data);
            break;
        case MU_PRGK_SPEED:
            mu_prg_recv_speed(&e, q.data);
            break;
        default:
            break;
        }
        p->hero_dirty = 1;
    }
    p->npending = kept;
}

void mu_progress_get_view(const mu_progress *p, mu_progress_view *v)
{
    const uint8_t *a = p->attr;
    memset(v, 0, sizeof *v);
    v->class_index = a[MU_PRG_A_CLASS] & 15;
    v->stage = mu_prg_class_stage(p->hero[0x12]);
    v->level = mu_prg_i32(a, MU_PRG_A_LEVEL);
    v->master_level = mu_prg_master_level(a);
    v->points = mu_prg_u16(a, MU_PRG_A_POINTS);
    v->master_points = mu_prg_i32(a, MU_PRG_A_MPOINTS);
    v->exp = (int64_t)mu_prg_u64(a, MU_PRG_A_EXP);
    v->next_exp = (int64_t)mu_prg_u64(a, MU_PRG_A_NEXT_EXP);
    v->master_exp = (int64_t)mu_prg_u64(a, MU_PRG_A_MEXP);
    v->master_next = (int64_t)mu_prg_u64(a, MU_PRG_A_MNEXT_EXP);
    static const size_t BASE[5] = {MU_PRG_A_STRENGTH, MU_PRG_A_DEXTERITY, MU_PRG_A_VITALITY, MU_PRG_A_ENERGY,
                                   MU_PRG_A_COMMAND};
    static const size_t ADD[5] = {MU_PRG_A_ADD_STR, MU_PRG_A_ADD_DEX, MU_PRG_A_ADD_VIT, MU_PRG_A_ADD_ENE,
                                  MU_PRG_A_ADD_CMD};
    for (int i = 0; i < 5; i++) {
        v->stats[i] = mu_prg_u16(a, BASE[i]);
        v->added[i] = mu_prg_u16(a, ADD[i]);
    }
    v->life = mu_prg_i32(a, MU_PRG_A_LIFE);
    v->life_max = mu_prg_i32(a, MU_PRG_A_LIFE_MAX);
    v->mana = mu_prg_i32(a, MU_PRG_A_MANA);
    v->mana_max = mu_prg_i32(a, MU_PRG_A_MANA_MAX);
    v->shield_max = mu_prg_i32(a, MU_PRG_A_SHIELD_MAX);
    v->ag_max = mu_prg_i32(a, MU_PRG_A_AG_MAX);
    v->dmg_min = mu_prg_u16(a, MU_PRG_A_DMG_MIN_R);
    v->dmg_max = mu_prg_u16(a, MU_PRG_A_DMG_MAX_R);
    v->dmg_min_left = mu_prg_u16(a, MU_PRG_A_DMG_MIN_L);
    v->dmg_max_left = mu_prg_u16(a, MU_PRG_A_DMG_MAX_L);
    v->atk_rate = mu_prg_u16(a, MU_PRG_A_ATK_RATE);
    v->pvp_rate = mu_prg_u16(a, MU_PRG_A_PVP_RATE);
    v->defense = mu_prg_u16(a, MU_PRG_A_DEFENSE);
    v->def_rate = mu_prg_u16(a, MU_PRG_A_DEF_RATE);
    v->pvp_defrate = mu_prg_u16(a, MU_PRG_A_PVP_DEFRATE);
    v->magic_min = mu_prg_u16(a, MU_PRG_A_MAGIC_MIN);
    v->magic_max = mu_prg_u16(a, MU_PRG_A_MAGIC_MAX);
    v->curse_min = mu_prg_u16(a, MU_PRG_A_CURSE_MIN);
    v->curse_max = mu_prg_u16(a, MU_PRG_A_CURSE_MAX);
    v->atk_speed = mu_prg_u16(a, MU_PRG_A_ATK_SPEED);
    v->magic_speed = mu_prg_u16(a, MU_PRG_A_MAGIC_SPEED);
    snprintf(v->speed_text, sizeof v->speed_text, "%s", p->speed_text);
}

int mu_progress_script_parse(mu_progress_script *s, const char *text)
{
    memset(s, 0, sizeof *s);
    const char *p = text;
    while (p && *p) {
        while (*p == ' ' || *p == ',')
            p++;
        if (!*p)
            break;
        if (s->count >= MU_PROGRESS_SCRIPT_MAX)
            return -1;
        mu_progress_script_item *it = &s->items[s->count];
        char *end;
        it->frame = (int32_t)strtol(p, &end, 10);
        if (end == p || *end != ':')
            return -1;
        p = end + 1;
        size_t n = 0;
        while (*p && *p != ':' && *p != ' ' && n + 1 < sizeof it->verb)
            it->verb[n++] = *p++;
        it->verb[n] = 0;
        if (*p == ':') {
            it->a = (int32_t)strtol(p + 1, &end, 0);
            p = end;
        }
        while (*p && *p != ' ')
            p++;
        s->count++;
    }
    return s->count;
}
