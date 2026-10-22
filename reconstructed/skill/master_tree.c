/* The master skill tree (NATIVE-SKILL-002); see master_tree.h. */
#include "master_tree.h"

#include <stdarg.h>
#include <stdio.h>
#include <string.h>

#ifndef MU_SKILL_MUTATION
#define MU_SKILL_MUTATION 0
#endif

static uint32_t rd32(const uint8_t *p) { return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24; }
static uint16_t rd16(const uint8_t *p) { return (uint16_t)(p[0] | p[1] << 8); }
static float rdf(const uint8_t *p)
{
    uint32_t u = rd32(p);
    float f;
    memcpy(&f, &u, 4);
    return f;
}

static void copy_text(char *dst, size_t cap, const uint8_t *src)
{
    size_t i = 0;
    for (; i + 1 < cap && src[i]; i++)
        dst[i] = (char)src[i];
    dst[i] = 0;
}

void mu_master_node_decode(const uint8_t r[24], mu_master_node *n)
{
    n->slot = r[0];
    n->x1 = r[1];
    n->mask = rd16(r + 2);
    n->group = r[4];
    n->cost = r[5];
    n->max_level = r[6];
    n->arrow = r[7];
    n->prereq1 = (int32_t)rd32(r + 8);
    n->prereq2 = (int32_t)rd32(r + 0xc);
    n->skill = (int32_t)rd32(r + 0x10);
    n->formula = (int32_t)rd32(r + 0x14);
}

void mu_master_tip_decode(const uint8_t r[808], mu_master_tip *t)
{
    t->skill = (int32_t)rd32(r);
    t->mask = (int16_t)rd16(r + 4);
    copy_text(t->rank_line, sizeof t->rank_line, r + 0x6);
    copy_text(t->desc, sizeof t->desc, r + 0x46);
    copy_text(t->cost_line, sizeof t->cost_line, r + 0x146);
    copy_text(t->brand_line, sizeof t->brand_line, r + 0x166);
    copy_text(t->rank_req, sizeof t->rank_req, r + 0x1a6);
    copy_text(t->pre1, sizeof t->pre1, r + 0x226);
    copy_text(t->pre2, sizeof t->pre2, r + 0x2a6);
}

void mu_master_init(mu_master_tree *t)
{
    memset(t, 0, sizeof *t);
}

uint16_t mu_master_spent(const mu_master_tree *t, int group)
{
    return group >= 0 && group < 3 ? rd16(t->state + 2 * group) : 0;
}

static void add_spent(mu_master_tree *t, int group, int v)
{
    if (group < 0 || group > 2)
        return;
    uint16_t s = (uint16_t)(rd16(t->state + 2 * group) + v);
    t->state[2 * group] = (uint8_t)s;
    t->state[2 * group + 1] = (uint8_t)(s >> 8);
}

/* The handler's byte at +off (0x78..0xb7): the rank rule indexes +0x7e + group * 10 + rank, which for tree 3 or
 * a rank past 9 reaches the fields after the table (rank 0 reads the byte before the row). */
static uint8_t *handler_byte(mu_master_tree *t, int off)
{
    if (off >= 0x78 && off < 0x9c)
        return &t->state[off - 0x78];
    if (off == 0x9c)
        return &t->pending_cost;
    if (off >= 0x9d && off < 0xa0)
        return &t->pad9d[off - 0x9d];
    if (off >= 0xa0 && off < 0xa4)
        return (uint8_t *)&t->pending_skill + (off - 0xa0);
    if (off >= 0xa4 && off < 0xa8)
        return (uint8_t *)&t->mask + (off - 0xa4);
    if (off >= 0xa8 && off < 0xac)
        return (uint8_t *)&t->gt_names + (off - 0xa8);
    if (off >= 0xac && off < 0xb0)
        return (uint8_t *)&t->gt_title + (off - 0xac);
    if (off >= 0xb0 && off < 0xb4)
        return (uint8_t *)&t->icon_w + (off - 0xb0);
    if (off >= 0xb4 && off < 0xb8)
        return (uint8_t *)&t->icon_h + (off - 0xb4);
    return NULL;
}

static uint8_t *rank_byte(mu_master_tree *t, int group, int rank)
{
    return handler_byte(t, 0x7e + group * 10 + rank);
}

uint8_t mu_master_rank_seen(const mu_master_tree *t, int group, int rank)
{
    const uint8_t *b = handler_byte((mu_master_tree *)t, 0x7e + group * 10 + rank);
    return b ? *b : 0;
}

static void clear_state(mu_master_tree *t)            /* 0x00baf523 */
{
    memset(t->state, 0, sizeof t->state);
}

/* ---- the class switch ---------------------------------------------------------------------------------- */

int mu_master_class(mu_master_tree *t, int code)
{
    static const int32_t mask[16] = {0x2, 0x1, 0x4, 0x10, 0x20, 0x8, 0x40, 0x80, 0x100, 0x200, 0x400, 0x800, 0x1000,
                                     0x2000, 0x4000, 0x8000};
    static const int32_t names[16] = {0x6d7, 0x6db, 0x6df, 0x6e3, 0x6e7, 0xc40, 0xd02, 0x11fe, 0x1515, 0x159a, 0x16a0,
                                      0x1720, 0x1729, 0x17af, 0x1a03, 0x1a99};
    static const int32_t title[3][16] = {
        {0x685, 0x684, 0x686, 0x687, 0x688, 0x699, 0xc4f, 0x11ed, 0x1519, 0x1598, 0x169c, 0x171c, 0x1725, 0x17ac, 0x19fe,
         0x1a94},
        {0x142b, 0x142c, 0x142d, 0x142f, 0x1430, 0x142e, 0x1431, 0x1432, 0x1526, 0x1599, 0x169d, 0x171d, 0x1726, 0x17ad,
         0x19ff, 0x1a95},
        {0x188e, 0x188f, 0x1890, 0x1892, 0x1893, 0x1891, 0x1894, 0x1895, 0x1896, 0x1897, 0x1898, 0x1899, 0x189a, 0x189b,
         0x1a00, 0x1a96}};
    code &= 0xff;
    if (code < 0x20 || code > 0x4f)
        return 0;
    int stage = (code - 0x20) >> 4, base = code & 0xf;
    t->mask = mask[base];
    t->gt_names = names[base];
    t->gt_title = title[stage][base];
    return 1;
}

/* ---- the maps ------------------------------------------------------------------------------------------ */

const mu_master_node *mu_master_node_at(const mu_master_tree *t, int slot)
{
    for (int i = 0; i < t->nnodes; i++)
        if (t->nodes[i].slot == (uint8_t)slot)
            return &t->nodes[i];
    return NULL;
}

const mu_master_tip *mu_master_tip_of(const mu_master_tree *t, int32_t skill)
{
    for (int i = 0; i < t->ntips; i++)
        if (t->tips[i]->skill == skill)
            return t->tips[i];
    return NULL;
}

static int learned_at(const mu_master_tree *t, int32_t skill, int *at)
{
    int lo = 0, hi = t->nlearned;
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        if ((uint32_t)t->learned[mid].skill < (uint32_t)skill)    /* map<unsigned> order */
            lo = mid + 1;
        else
            hi = mid;
    }
    *at = lo;
    return lo < t->nlearned && t->learned[lo].skill == skill;
}

const mu_master_entry *mu_master_find(const mu_master_tree *t, int32_t skill)
{
    int at;
    return learned_at(t, skill, &at) ? &t->learned[at].e : NULL;
}

static int learned_insert(mu_master_tree *t, int32_t skill, const mu_master_entry *e)   /* std::map::insert */
{
    int at;
    if (learned_at(t, skill, &at) || t->nlearned >= MU_MASTER_LEARNED)
        return 0;
    memmove(t->learned + at + 1, t->learned + at, (size_t)(t->nlearned - at) * sizeof *t->learned);
    t->learned[at].skill = skill;
    t->learned[at].e = *e;
    t->nlearned++;
    return 1;
}

static void learned_erase(mu_master_tree *t, int32_t skill)
{
    int at;
    if (!learned_at(t, skill, &at))
        return;
    memmove(t->learned + at, t->learned + at + 1, (size_t)(t->nlearned - at - 1) * sizeof *t->learned);
    t->nlearned--;
}

uint8_t mu_master_level(const mu_master_tree *t, int32_t skill)
{
    const mu_master_entry *e = mu_master_find(t, skill);
    return e ? e->level : 0;
}

float mu_master_value(const mu_master_tree *t, int32_t skill)
{
    const mu_master_entry *e = mu_master_find(t, skill);
    return e ? e->value : 0.0f;
}

uint8_t mu_master_flag(const mu_master_tree *t, int32_t skill)
{
    const mu_master_entry *e = mu_master_find(t, skill);
    return e ? e->flag : 0;
}

int mu_master_is_master(int32_t skill)
{
    return (uint32_t)skill >= 0x12c && (uint32_t)skill <= 0x3a1;
}

float mu_master_chain(const mu_master_tree *t, const mu_skill_env *env, int32_t skill, int32_t flag)
{
    if (!mu_master_is_master(skill))
        return 0.0f;
    float sum = 0.0f;
    for (int32_t s = skill; s != 0; s = mu_skill_brand_of(env, s))
        if ((int32_t)mu_master_flag(t, s) == flag)
            sum += mu_master_value(t, s);
    return sum;
}

float mu_master_kind_sum(const mu_master_tree *t, const mu_skill_env *env, int32_t skill, int kind)
{
    if (skill == 0 || !mu_master_is_master(skill) || (uint8_t)kind == 0 || (uint8_t)kind >= 5)
        return 0.0f;
    float sum = 0.0f;
    for (int32_t s = skill; s != 0;) {
        const mu_skill_record *r = mu_skill_record_of(env, s);
        if (r->x98 == (uint8_t)kind)
            sum += mu_master_value(t, s);
        s = r->brand;
        if (s == 0x4b)
            break;
    }
    return sum;
}

/* ---- build ----------------------------------------------------------------------------------------------- */

static void invokef(const mu_master_env *env, const char *name, const char *fmt, ...)
    __attribute__((format(printf, 3, 4)));
static void invokef(const mu_master_env *env, const char *name, const char *fmt, ...)
{
    if (!env || !env->invoke)
        return;
    char buf[4096];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(buf, sizeof buf, fmt, ap);
    va_end(ap);
    env->invoke(env->user, name, buf);
}

void mu_master_build(mu_master_tree *t, const mu_master_env *env, const mu_master_node *nodes, int nnodes,
                     const mu_master_tip *tips, int ntips)
{
    t->nnodes = 0;                                       /* 0x00bb5a0a */
    for (int i = 0; i < nnodes && i < 0x800; i++) {
        if (nodes[i].slot == 0)
            break;
        if (!(nodes[i].mask & t->mask))
            continue;
        if (mu_master_node_at(t, nodes[i].slot))
            break;                                       /* the first repeated slot stops the build */
        if (t->nnodes >= MU_MASTER_NODES)
            break;
        int at = t->nnodes;                              /* keep the map's slot order */
        while (at > 0 && t->nodes[at - 1].slot > nodes[i].slot) {
            t->nodes[at] = t->nodes[at - 1];
            at--;
        }
        t->nodes[at] = nodes[i];
        t->nnodes++;
    }
    t->ntips = 0;                                        /* 0x00bb59f2 */
    for (int i = 0; i < ntips && i < 0x800; i++) {
        if (tips[i].skill == 0)
            break;
        if (!((uint16_t)tips[i].mask & t->mask))
            continue;
        if (mu_master_tip_of(t, tips[i].skill))
            break;
        if (t->ntips >= MU_MASTER_TIPS)
            break;
        int at = t->ntips;
        while (at > 0 && (uint32_t)t->tips[at - 1]->skill > (uint32_t)tips[i].skill) {
            t->tips[at] = t->tips[at - 1];
            at--;
        }
        t->tips[at] = &tips[i];
        t->ntips++;
    }
    char list[4096];                                     /* 0x00bb04ac */
    size_t n = 0;
    list[0] = 0;
    for (int i = 0; i < t->nnodes; i++) {
        invokef(env, "SetArrowDirection", "%d %d", t->nodes[i].slot, t->nodes[i].arrow);
        int w = snprintf(list + n, sizeof list - n, "%d,", t->nodes[i].slot);
        if (w > 0 && (size_t)w < sizeof list - n)
            n += (size_t)w;
    }
    invokef(env, "SetSkillSlot", "%s", list);
}

void mu_master_position(mu_master_tree *t, int slot, float x, float y, float scale, float ratio_x, float ratio_y)
{
    t->icon_w = scale * 26.0f * ratio_x;
    t->icon_h = scale * 37.0f * ratio_y;
    slot &= 0xff;
    if (!t->pos[slot].has) {
        t->pos[slot].has = 1;
        t->pos[slot].x = x;
        t->pos[slot].y = y;
    }
}

/* ---- texts ------------------------------------------------------------------------------------------------- */

static const char *gtext(const mu_master_env *env, int32_t index)
{
    const char *s = env && env->text ? env->text(env->user, index) : NULL;
    return s ? s : "";
}

#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wformat-nonliteral"
static void fmt_int(char *buf, size_t cap, const char *fmt, int v) { snprintf(buf, cap, fmt, v); }
static void fmt_double(char *buf, size_t cap, const char *fmt, double v) { snprintf(buf, cap, fmt, v); }
#pragma clang diagnostic pop

void mu_master_set_text(const mu_master_tree *t, const mu_master_env *env, int mask)
{
    char buf[1024];
    if (mask & 1)
        invokef(env, "SetText", "%d %s", 1, gtext(env, t->gt_title));
    if (mask & 2) {
        fmt_int(buf, sizeof buf, gtext(env, 0x6d2), env->level_sum);
        invokef(env, "SetText", "%d %s", 2, buf);
    }
    if (mask & 4) {
        fmt_int(buf, sizeof buf, gtext(env, 0x6d3), env->points);
        invokef(env, "SetText", "%d %s", 4, buf);
    }
    if ((mask & 8) && env->next_exp != 0) {
        double next = (double)env->next_exp, exp = (double)env->exp;
        double top = exp > next ? exp : next;
        float pct = (float)(exp / top) * 100.0f;
        fmt_double(buf, sizeof buf, gtext(env, 0xd07), (double)pct);
        invokef(env, "SetText", "%d %s", 8, buf);
    }
    for (int i = 0; i < 3; i++)
        if (mask & (0x10 << i)) {
            fmt_int(buf, sizeof buf, gtext(env, t->gt_names + i), mu_master_spent(t, i));
            invokef(env, "SetText", "%d %s", 0x10 << i, buf);
        }
}

/* ---- the checks and the click ------------------------------------------------------------------------------ */

static void msgbox(const mu_master_env *env, int owner, const char *text)
{
    if (env && env->msgbox)
        env->msgbox(env->user, owner, text);
}

int mu_master_points_ok(const mu_master_env *env, int16_t points, const mu_master_node *n, int16_t level)
{
    if (level == (int16_t)n->max_level) {
        msgbox(env, 0, gtext(env, 0xcfe));
        return 0;
    }
#if MU_SKILL_MUTATION == 16
    if (points <= (int16_t)n->cost) {
#else
    if (points < (int16_t)n->cost) {
#endif
        char buf[0x104];
        fmt_int(buf, sizeof buf, gtext(env, 0xcfd), n->cost - points);
        msgbox(env, 0, buf);
        return 0;
    }
    return 1;
}

int mu_master_prereq_ok(const mu_master_tree *t, int32_t p1, int32_t p2)
{
    if (p1 == 0)
        return 1;
    const mu_master_entry *e = mu_master_find(t, p1);
    if (!e || e->level < 10)
        return 0;
    if (p2 != 0) {
        e = mu_master_find(t, p2);
        if (!e || e->level < 10)
            return 0;
    }
    return 1;
}

int mu_master_rank_ok(mu_master_tree *t, uint8_t group, uint8_t rank, uint8_t level)
{
    uint8_t *b = rank_byte(t, group, rank);
    if (b && *b < level)
        *b = level;
    if (rank == 1)
        return 1;
    uint8_t *p = rank_byte(t, group, rank - 1);
    return p && *p >= 10;
}

int mu_master_brand_ok(const mu_skill_env *env, const mu_skill_hero *hero, int32_t skill, uint8_t level)
{
    int32_t b = mu_skill_brand_of(env, skill);
    if (b == 0)
        return 1;
    const mu_skill_record *r = mu_skill_record_of(env, b);
    if (r->index == 0)
        return 0;
    if (r->use_type == 4)
        return 1;
    if (level != 0)
        return 1;
    for (int i = 0; i < 0x96; i++)
        if (hero->skills[i] == b)
            return 1;
    return 0;
}

int mu_master_click(mu_master_tree *t, const mu_master_env *env, const mu_skill_hero *hero, int slot)
{
    const mu_master_node *pn = mu_master_node_at(t, slot);
    if (!pn)
        return 0;
    mu_master_node n = *pn;
    const mu_skill_record *r = mu_skill_record_of(env->skills, n.skill);
    uint8_t level = mu_master_level(t, n.skill);
    if (env->event)
        env->event(env->user, "sound", 0x19);         /* 0x00a6ac96(0x19, 0, 0) */
    if (!mu_master_points_ok(env, (int16_t)env->points, &n, level))
        return 0;
    if (!mu_master_prereq_ok(t, n.prereq1, n.prereq2) || !mu_master_rank_ok(t, n.group, (uint8_t)r->x74, level) ||
        !mu_master_brand_ok(env->skills, hero, n.skill, level)) {
        msgbox(env, 1, gtext(env, 0xcff));
        return 0;
    }
    if (env->special_item && !env->special_item(env->user, n.skill)) {
        msgbox(env, 1, gtext(env, 0xd08));
        return 0;
    }
    t->pending_cost = n.cost;
    t->pending_skill = n.skill;
    char cost[0x100], text[0x400];
    fmt_int(cost, sizeof cost, gtext(env, 0x6ec), n.cost);
    snprintf(text, sizeof text, "%s\n%s", gtext(env, 0x6eb), cost);
    if (env->confirm)
        env->confirm(env->user, 0x47, text);
    return 1;
}

int mu_master_confirm(const mu_master_tree *t, int id, int result, int32_t *skill)
{
    if (id != 0x47 || result != 0)
        return 0;
    if (skill)
        *skill = t->pending_skill;
    return 1;
}

size_t mu_master_request(uint8_t *out, size_t cap, int32_t skill)
{
    if (cap < 8)
        return 0;
    out[0] = 0xc1;
    out[1] = 8;
    out[2] = 0x01;
    out[3] = 0x16;
    for (int i = 0; i < 4; i++)
        out[4 + i] = (uint8_t)((uint32_t)skill >> (8 * i));
    return 8;
}

/* ---- the server's answers ----------------------------------------------------------------------------------- */

void mu_master_list_entry(mu_master_tree *t, const mu_master_env *env, int slot, int level, float value, float next,
                          int flag)
{
    const mu_master_node *n = mu_master_node_at(t, slot);
    if (n) {
        mu_master_entry e = {(uint8_t)level, value, next, (uint8_t)flag};
        learned_insert(t, n->skill, &e);
#if MU_SKILL_MUTATION == 17
        add_spent(t, n->group, n->cost);
#else
        add_spent(t, n->group, (uint8_t)level);
#endif
        invokef(env, "SetRank", "%d %d", (uint8_t)slot, (uint8_t)level);
    }
    mu_master_set_text(t, env, 0x70);
}

int mu_master_receive_list(mu_master_tree *t, const mu_master_env *env, const uint8_t *p, size_t size)
{
    if (size < 0xc)
        return 0;
    t->nlearned = 0;                                     /* 0x00bb72f0 */
    clear_state(t);
    uint32_t count = rd32(p + 8);
    for (uint32_t i = 0; i < count; i++) {
        size_t e = 0xc + 16 * (size_t)i;
        if (e + 0xd > size)
            break;
        mu_master_list_entry(t, env, p[e], p[e + 1], rdf(p + e + 4), rdf(p + e + 8), p[e + 0xc]);
    }
    if (env->event)
        env->event(env->user, "stats", 0);               /* 0x00a00fb7 */
    return 1;
}

void mu_master_hero_upgrade(const mu_skill_env *env, mu_skill_hero *hero, int32_t skill)
{
    if (!mu_master_is_master(skill))
        return;
    const mu_skill_record *r = mu_skill_record_of(env, skill);
    if (r->use_type != 4 || r->brand == 0)
        return;
    uint8_t twice = r->x94;
    for (int i = 0; i < hero->count; i++)
        if (hero->skills[i] == r->brand) {
            hero->skills[i] = (uint16_t)skill;
            if (twice != 1)
                return;
            twice = 0;
        }
}

static void learn_entry(mu_master_tree *t, const mu_master_env *env, int slot, int level, float value, float next,
                        int flag, int popup_visible)         /* 0x00bb26a8 */
{
    const mu_master_node *n = mu_master_node_at(t, slot);
    int32_t skill = n ? n->skill : 0;
    learned_erase(t, skill);
    mu_master_entry e = {(uint8_t)level, value, next, (uint8_t)flag};
    if (!learned_insert(t, skill, &e))
        return;
    if (n)
        add_spent(t, n->group, n->cost);
    mu_master_set_text(t, env, 0x74);
    invokef(env, "SetRank", "%d %d", (uint8_t)slot, (uint8_t)level);
    if (popup_visible && env->event)
        env->event(env->user, "tooltip", slot);          /* 0x00bb1183(slot) again */
}

int mu_master_receive_learn(mu_master_tree *t, const mu_master_env *env, mu_skill_world *w, const uint8_t *p,
                            size_t size, int popup_visible, int32_t *points)
{
    if (size < 0x1d)
        return 0;
    if (points)
        *points = (int16_t)rd16(p + 6);                  /* 0x00a00192: hero +0x34 */
    int result = p[4];
    if (result == 1) {
        int32_t skill = (int32_t)rd32(p + 0xc);
        mu_master_hero_upgrade(w->env, w->hero, skill);
        mu_skill_stamp_add(w->env, w->stamp, skill);
        mu_skill_keys_add(w->env, w->keys, w->stamp, skill, NULL);
        learn_entry(t, env, p[8], p[0x10], rdf(p + 0x14), rdf(p + 0x18), p[0x1c], popup_visible);
        if (env->event) {
            env->event(env->user, "tree_add", skill);    /* GfxMgr +0x1f8 -> 0x00c26ad8 */
            env->event(env->user, "stats", 0);
            env->event(env->user, "charinfo", 0);        /* GfxMgr +0x21c -> 0x00b40661 */
        }
    } else if (result == 6) {
        msgbox(env, 0, gtext(env, 0xd09));
    } else if (result == 7) {
        msgbox(env, 0, gtext(env, 0xd1a));
    }
    return 1;
}

/* ---- skill damage ------------------------------------------------------------------------------------------- */

int32_t mu_master_skill_damage(const mu_master_tree *t, const mu_skill_env *env, int32_t skill,
                               mu_master_formula_fn formula, void *user)
{
    int32_t base = mu_skill_master_base(env, skill), dmg = 0, bonus = 0;
    for (int32_t s = skill;;) {
        const mu_skill_record *r = mu_skill_record_of(env, s);
        if (s == base) {
            if (r->use_type == 4) {
                uint8_t lvl = mu_master_level(t, s);
                if (r->brand == 0 && lvl == 0)
                    dmg = (int32_t)(formula ? formula(user, 3, r->damage, r->master_factor) : 0.0);
                else
                    dmg = (int32_t)mu_master_value(t, s);
            } else {
                dmg = r->damage;
            }
#if MU_SKILL_MUTATION == 18
        } else if (r->use_type == 4) {
#else
        } else if (r->use_type == 4 && mu_master_flag(t, s) == 1) {
#endif
            bonus += (int32_t)mu_master_value(t, s);
        }
        if (r->brand == 0 || r->brand == 0x4b)
            break;
        s = r->brand;
    }
    return dmg + bonus;
}
