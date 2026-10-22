/* The fourth tree's tooltip and icons (NATIVE-SKILL-003); see tree4.h. */
#include "tree4.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "skill_tooltip.h"

#ifndef MU_SKILL_MUTATION
#define MU_SKILL_MUTATION 0
#endif

#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wformat-nonliteral"
/* The client's sprintf with the table's two arguments (int, int) or (string, int). */
static void fmt_ii(char *buf, size_t cap, const char *fmt, int a, int b) { snprintf(buf, cap, fmt, a, b); }
static void fmt_si(char *buf, size_t cap, const char *fmt, const char *a, int b) { snprintf(buf, cap, fmt, a, b); }
#pragma clang diagnostic pop

static const char *gt(const mu_t4_env *env, int32_t id)
{
    const char *s = env->text ? env->text(env->user, id) : "";
    return s ? s : "";
}

const mu_t4_tip *mu_t4_tip_of(const mu_t4_tip *tips, int ntips, int32_t skill)
{
    int lo = 0, hi = ntips;
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        if (tips[mid].id < skill)
            lo = mid + 1;
        else
            hi = mid;
    }
    return lo < ntips && tips[lo].id == skill ? &tips[lo] : NULL;
}

/* One table format with the record's value kind (+0x34): -1 the text as is, 0 an int (truncated), 1 a double. */
static void value_text(char *out, size_t cap, const char *fmt, int32_t kind, float value)
{
    if (kind == -1)
        mu_skill_format(out, cap, fmt, 0, 0, 0.0, NULL);           /* sprintf(buf, text): the text is the format */
    else if (kind == 0)
        mu_skill_format(out, cap, fmt, 'i', (int32_t)value, 0.0, NULL);
    else if (kind == 1)
        mu_skill_format(out, cap, fmt, 'f', 0, (double)value, NULL);
    else
        out[0] = 0;
}

int mu_t4_parent_open(const mu_t4_group *g, int32_t index)
{
    int at = mu_t4_group_find(g, index);
    if (at < 0)
        return 0;
    const mu_t4_node *n = &g->nodes[at];
    for (int i = 0; i < n->nparents; ++i) {
        const mu_t4_node *p = &g->nodes[n->parents[i]];
        if (p->rec->f[MU_T4_TYPE] == 3 && p->open == 1)
            return 0;
        if (p->level >= p->rec->f[MU_T4_OPEN])
            return 1;
    }
    return 0;
}

int mu_t4_tooltip(const mu_t4_window *w, const mu_skill_tip_env *tenv, const mu_t4_env *env, const mu_t4_tip *tips,
                  int ntips, int32_t index, mu_skill_tip *out, uint8_t header[MU_SKILL_TIP_LINES], int32_t pos[2])
{
    memset(out, 0, sizeof *out);
    if (header)
        memset(header, 0, MU_SKILL_TIP_LINES);
    if (w->cur_group < 0)
        return 0;
    const mu_t4_group *g = &w->groups[w->cur_group];
    int at = mu_t4_group_find(g, index);
    if (at < 0)
        return 0;
    const mu_t4_node *n = &g->nodes[at];
    const mu_t4_record *r = n->rec;
    char buf[0x200];
    int line;
    if (r->f[MU_T4_TYPE] == 3) {                                    /* 0x00c2986a: the branch's own tooltip */
        mu_skill_tip_set(out, 0, NULL, 3, -1);
        mu_skill_format(buf, sizeof buf, "%s", 's', 0, 0.0, gt(env, 0x1492));
        mu_skill_tip_set(out, 0, buf, -1, 1);
        mu_skill_format(buf, sizeof buf, "%s", 's', 0, 0.0, gt(env, 0x1493));
        line = mu_skill_tip_put(tenv, out, buf, 1, 0) + 1;     /* the count includes one line it does not write */
    } else {
        const mu_skill_record *sr = mu_skill_record_of(tenv->skills, n->skill);
        mu_skill_tip_set(out, 0, NULL, 3, -1);
        mu_skill_format(buf, sizeof buf, "%s", 's', 0, 0.0, sr->name);
        mu_skill_tip_set(out, 0, buf, -1, 1);
        fmt_ii(buf, sizeof buf, gt(env, 0x1428), n->level, r->f[MU_T4_MAX]);   /* level / maximum */
        mu_skill_tip_set(out, 1, buf, -1, -1);
        line = 2;
        const mu_t4_tip *tip = mu_t4_tip_of(tips, ntips, n->skill);
        mu_t4_tip none = {0};
        if (!tip) {
            none.kind = -1;
            tip = &none;                                             /* the table's default record (+0x44) */
        }
        buf[0] = 0;
        if (!tip->fixed) {
            float v = 0.0f;
            if (tip->kind != -1)
                v = n->level == 0 ? (tenv->formula ? tenv->formula(tenv->user, 3, r->f[MU_T4_TIP], r->f[MU_T4_COST])
                                                    : 0.0f)
                                  : n->value;
            value_text(buf, sizeof buf, tip->desc, tip->kind, v);
        }
        line = mu_skill_tip_put(tenv, out, buf, line, 0);
        if (tip->show_next && n->level > 0 && n->level < r->f[MU_T4_MAX]) {
            mu_skill_format(buf, sizeof buf, gt(env, 0xd00), 0, 0, 0.0, NULL);
            line = mu_skill_tip_put(tenv, out, buf, line, 4);
            if (header && line >= 0 && line < MU_SKILL_TIP_LINES)
                header[line] = 1;
            value_text(buf, sizeof buf, tip->next, tip->kind, n->next);
            line = mu_skill_tip_put(tenv, out, buf, line, 0);
        }
        mu_skill_format(buf, sizeof buf, gt(env, 0xd01), 0, 0, 0.0, NULL);
        line = mu_skill_tip_put(tenv, out, buf, line, 1);
        if (header && line >= 0 && line < MU_SKILL_TIP_LINES)
            header[line] = 1;
        mu_skill_format(buf, sizeof buf, gt(env, 0x1433), 'i', r->f[MU_T4_COST], 0.0, NULL);
        line = mu_skill_tip_put(tenv, out, buf, line, w->points < r->f[MU_T4_COST] + (MU_SKILL_MUTATION == 28) ? 2 : 0);
        /* the first parent only: a branch asks level 10, another parent its opening level */
        for (int i = 0; i < n->nparents; ++i) {
            const mu_t4_node *p = &g->nodes[n->parents[i]];
            if (p->rec->f[MU_T4_TYPE] == 3)
                mu_skill_format(buf, sizeof buf, gt(env, 0x142a), 'i', 10, 0.0, NULL);
            else if (p->rec->f[MU_T4_OPEN] > 0)
                mu_skill_format(buf, sizeof buf, gt(env, 0x142a), 'i', p->rec->f[MU_T4_OPEN], 0.0, NULL);
            else
                break;
            line = mu_skill_tip_put(tenv, out, buf, line, mu_t4_parent_open(g, index) ? 0 : 2);
            break;
        }
        if (r->f[MU_T4_REQ_SKILL] > 0) {
            int color = mu_t4_req_ok(g, env, index) ? 0 : 2;
            const mu_skill_record *q = mu_skill_record_of(tenv->skills, r->f[MU_T4_REQ_SKILL]);
            if (r->f[MU_T4_REQ_LEVEL] > -1) {
                fmt_si(buf, sizeof buf, gt(env, 0x143b), q->name, r->f[MU_T4_REQ_LEVEL]);
            } else {
                mu_skill_format(buf, sizeof buf, gt(env, 0x1429), 's', 0, 0.0, q->name);
            }
            line = mu_skill_tip_put(tenv, out, buf, line, color);
        }
        for (int k = 0; k < 2; ++k) {
            int32_t skill = r->f[k ? MU_T4_PRE2 : MU_T4_PRE1], level = r->f[k ? MU_T4_PRE2_LEVEL : MU_T4_PRE1_LEVEL];
            if (skill <= -1)
                continue;
            int color = mu_t4_prereq_ok(g, index) ? 0 : 2;
            const mu_skill_record *q = mu_skill_record_of(tenv->skills, skill);
            if (level > -1) {
                fmt_si(buf, sizeof buf, gt(env, 0x144a), q->name, level);
            } else {
                mu_skill_format(buf, sizeof buf, gt(env, 0x1429), 's', 0, 0.0, q->name);
            }
            line = mu_skill_tip_put(tenv, out, buf, line, color);
        }
    }
    out->count = line;
    if (pos) {
        pos[0] = n->rect[0];
        pos[1] = n->rect[1];
    }
    return line;
}

void mu_t4_icons(const mu_t4_window *w, const mu_skill_env *skills, float x0, float y0, float scale, float ratio_x,
                 float ratio_y, mu_t4_draw_fn draw, void *user)
{
    if (w->cur_group < 0 || !draw || w->hidden)
        return;
    const float cw = 0.0390625f, ch = 0.0546875f;                    /* 0x01a91938 / 0x01a9193c */
    if (w->branch_visible) {
        /* the branch popup: its choices at the movie's positions (+0xc4), the side size, white (-1) */
        for (int i = 0; i < w->nbranch; ++i) {
            int32_t icon = mu_skill_record_of(skills, w->branch[i])->icon;
            float x = (x0 + scale * w->branch_pos[i][0]) * ratio_x, y = (y0 + scale * w->branch_pos[i][1]) * ratio_y;
            float wd = scale * w->side_size[0] * ratio_x, ht = scale * w->side_size[1] * ratio_y;
            draw(user, 0x7e1c, x, y, wd, ht, (float)(icon % 25) * cw, (float)(icon / 25) * ch, cw, ch, 0xffffffffu);
        }
        return;
    }
    const mu_t4_group *g = &w->groups[w->cur_group];
    for (int i = 0; i < g->nnodes; ++i) {
        const mu_t4_node *n = &g->nodes[i];
        int32_t icon = mu_skill_record_of(skills, n->skill)->icon;
        if (n->skill == -1)
            icon = 0x1c1;
        if (!n->open)
            continue;
        float x = (x0 + (float)n->rect[0] * scale) * ratio_x, y = (y0 + (float)n->rect[1] * scale) * ratio_y;
        float wd = (float)(n->rect[2] - n->rect[0]) * scale * ratio_x;
        float ht = (float)(n->rect[3] - n->rect[1]) * scale * ratio_y;
        uint32_t color = n->avail ? 0xffffffffu : MU_SKILL_MUTATION == 30 ? 0xff787878u : 0xff3c3c3cu; /* 0x00b4c6aa */
        draw(user, 0x7e1c, x, y, wd, ht, (float)(icon % 25) * cw, (float)(icon / 25) * ch, cw, ch, color);
    }
    if (!w->side_ready || !w->side)
        return;
    /* the side options: the record's skill icon, then f[19]/f[19]/f[20]/f[21] by the entry's stage (+0x14),
       grey at stage 1 */
    int k = 0;
    for (int i = 0; i < w->side->nrecords; ++i) {
        const mu_t4_side_record *r = &w->side->records[i];
        if (r->f[0] != w->cls)
            continue;
        int idx = k++;
        if (idx >= MU_T4_SIDE)
            continue;
        const mu_t4_side_entry *e = &w->side_entry[idx];
        int32_t icon = mu_skill_record_of(skills, r->f[3])->icon;
        uint32_t color = 0xffffffffu;
        if (e->stage == 1)
            color = 0xff3c3c3cu, icon = r->f[19];
        else if (e->stage == 2)
            icon = r->f[19];
        else if (e->stage == 3)
            icon = r->f[20];
        else if (e->stage == 4)
            icon = r->f[21];
        float x = (x0 + scale * w->side_pos[idx][0]) * ratio_x, y = (y0 + scale * w->side_pos[idx][1]) * ratio_y;
        float wd = scale * w->side_size[0] * ratio_x, ht = scale * w->side_size[1] * ratio_y;
        draw(user, 0x7e1c, x, y, wd, ht, (float)(icon % 25) * cw, (float)(icon / 25) * ch, cw, ch, color);
    }
}

/* ---- texts ---------------------------------------------------------------------------------------------- */

#include "../hud/tooltip_html.h"

static void jstr_append(char **s, size_t *n, size_t *cap, const char *text)
{
    for (const unsigned char *p = (const unsigned char *)text; ; ++p) {
        char tmp[8];
        size_t k;
        if (!*p) {
            tmp[0] = '"';
            k = 1;
        } else if (*p == '"' || *p == '\\') {
            tmp[0] = '\\', tmp[1] = (char)*p;
            k = 2;
        } else if (*p == '\n') {
            tmp[0] = '\\', tmp[1] = 'n';
            k = 2;
        } else if (*p < 0x20 || *p >= 0x80) {
            k = (size_t)snprintf(tmp, sizeof tmp, "\\u%04x", *p);
        } else {
            tmp[0] = (char)*p;
            k = 1;
        }
        if (*n + k + 1 >= *cap) {
            *cap = (*cap + k) * 2 + 64;
            *s = realloc(*s, *cap);
        }
        memcpy(*s + *n, tmp, k);
        *n += k;
        (*s)[*n] = 0;
        if (!*p)
            break;
    }
}

static void member(char **s, size_t *n, size_t *cap, const char *name, const char *value)
{
    char head[64];
    snprintf(head, sizeof head, "%s\"%s\":\"", *n > 2 ? "," : "", name);
    size_t k = strlen(head);
    if (*n + k + 1 >= *cap) {
        *cap = (*cap + k) * 2 + 64;
        *s = realloc(*s, *cap);
    }
    memcpy(*s + *n, head, k + 1);
    *n += k;
    jstr_append(s, n, cap, value);
}

void mu_t4_set_text(const mu_t4_env *env)
{
    static const struct { const char *name; int32_t id; } plain[] = {
        {"SkillUpgradeTab", 0x1448}, {"ActiveSkillTab", 0x1449}, {"PassiveSkillOption", 0x149c},
        {"PassiveDebuffOption", 0x149d}, {"SelectDebuffTitle", 0x149e}, {"StatTitle", 0x14b1}, {"Btn_OK", 0xe4},
        {"Btn_Cancel", 0xe5}, {"AvailableStatText", 0x19ed}, {"AccumulatedStatText", 0x19ee},
        {"PointExpain", 0x19ef}};
    size_t cap = 512, n = 2;
    char *s = malloc(cap);
    if (!s)
        return;
    memcpy(s, "[{", 3);
    for (size_t i = 0; i < sizeof plain / sizeof plain[0]; ++i)
        member(&s, &n, &cap, plain[i].name, gt(env, plain[i].id));
    char buf[0x100];
    mu_skill_format(buf, sizeof buf, gt(env, 0x19f0), 'i', 0, 0.0, NULL);   /* sprintf(GT 0x19f0, 0) */
    member(&s, &n, &cap, "PointResult", buf);
    char html[0x800];
    mu_tooltip_html_line(html, sizeof html, gt(env, 0x149f), 1, 0);        /* 0x00ab4dc0(out, text, 1, 0) */
    member(&s, &n, &cap, "ExplainSelectDebuff", html);
    if (n + 3 >= cap)
        s = realloc(s, cap = n + 4);
    memcpy(s + n, "}]", 3);
    if (env->invoke)
        env->invoke(env->user, "SetText", s);
    free(s);
}

void mu_t4_show_level(const mu_t4_env *env, int32_t level_sum)
{
    char buf[0x100], json[0x200];
    mu_skill_format(buf, sizeof buf, gt(env, 0x144c), 'i', level_sum, 0.0, NULL);
    char *s = NULL;
    size_t n = 0, cap = 0;
    jstr_append(&s, &n, &cap, buf);
    snprintf(json, sizeof json, "[\"%s]", s ? s : "\"");
    free(s);
    if (env->invoke)
        env->invoke(env->user, "SetLevel", json);
}

/* SelectBranchSkill(group, index) 0x00c2b5f4: the branch popup's choice becomes the pending pair (+0x80/+0x84;
 * +0xd8/+0xdc keep it too), the confirm box 0x73 asks for the child's cost (no availability check here), and the
 * popup closes (0x00c2b88f(0)). */
int mu_t4_select_branch(mu_t4_window *w, const mu_t4_env *env, int32_t group, int32_t index)
{
    w->pend_group = group;
    w->pend_index = index;
    if (w->cur_group < 0)
        return 0;
    const mu_t4_group *g = &w->groups[w->cur_group];
    int at = mu_t4_group_find(g, index);
    if (at < 0)
        return 0;
    char cost[0x100], text[0x400];
    fmt_ii(cost, sizeof cost, gt(env, 0x143f), g->nodes[at].rec->f[MU_T4_COST], 0);
    snprintf(text, sizeof text, "%s\n%s", gt(env, 0x6eb), cost);
    if (env->confirm)
        env->confirm(env->user, 0x73, text);
    w->branch_visible = 0;
    if (env->invoke)
        env->invoke(env->user, "VisibleSetBranchSkill", "[false]");
    return 1;
}

/* RequestSelectBranchUIPos(index, x, y) 0x00c2b79d: the popup's choice positions (+0xc4). */
void mu_t4_branch_rect(mu_t4_window *w, int32_t index, float x, float y)
{
    if (index >= 0 && index < MU_T4_LINKS) {
        w->branch_pos[index][0] = x;
        w->branch_pos[index][1] = y;
    }
}
