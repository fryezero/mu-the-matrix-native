/* Overhead text: the game side of hudPlayerName (NATIVE-NAMES-001).  See
 * overhead_names.h and docs/research/client-overhead-text.md. */
#include "overhead_names.h"

#include <math.h>
#include <stdio.h>
#include <string.h>

static void copy_text(char *out, size_t cap, const char *s)
{
    if (!cap)
        return;
    snprintf(out, cap, "%s", s ? s : "");
}

int32_t mu_hn_cvtt(float value)
{
    if (!(value > -2147483904.0f && value < 2147483648.0f))   /* NaN and out of range: the integer indefinite */
        return INT32_MIN;
    return (int32_t)value;
}

int32_t mu_hn_hp_percent(uint32_t hp, uint32_t max)
{
    /* cvtsi2sd + the unsigned correction (0x01bd3050), cvtsd2ss, divss, mulss 100 */
    float a = (float)(double)hp, b = (float)(double)max;
    float q = a / b;
    q = q * 100.0f;
    return mu_hn_cvtt(q);
}

/* ---- the handler ---- */

void mu_hn_window_init(mu_hn_window *w)
{
    memset(w, 0, sizeof *w);
    w->item_height = 0x23;
    w->item_offset = 5;
    w->height_player = 0xb4;
    w->height_wing = 0xcd;
    w->height_ride_a = 0xdc;
    w->height_ride_b = 0xe1;
    w->height_ride_c = 0x118;
    w->height_ride = 0xf0;
    w->height_state = 0x12c;
    w->height_ride_d = 0x140;
    w->monster_view = 1;
    w->selected = -1;
    w->item_view = 1;
}

mu_hn_entry *mu_hn_find(mu_hn_window *w, int32_t key)
{
    for (int32_t i = 0; i < w->count; ++i)
        if (w->entries[i].key == key)
            return &w->entries[i];
    return NULL;
}

void mu_hn_set_mc(mu_hn_window *w, int32_t key, int has_mc)
{
    mu_hn_entry *e = mu_hn_find(w, key);
    if (!e)
        return;
    e->has_mc = (uint8_t)(has_mc != 0);
    /* PlayerName.setData sets the clip's _visible from isShow; MonsterName leaves it visible */
    e->mc_visible = (uint8_t)(e->type == MU_HN_PLAYER ? e->addinfo_show : 1);
}

static mu_hn_entry *insert_entry(mu_hn_window *w, const mu_hn_entry *e)
{
    if (w->count >= MU_HN_ENTRIES)
        return NULL;
    int32_t i = w->count;
    while (i > 0 && w->entries[i - 1].key > e->key) {
        w->entries[i] = w->entries[i - 1];
        --i;
    }
    w->entries[i] = *e;
    w->count++;
    return &w->entries[i];
}

static void entry_defaults(mu_hn_entry *e)   /* 0x00c8734a */
{
    memset(e, 0, sizeof *e);
    e->key = -1;
    e->show = 1;
}

/* ---- helpers ---- */

int32_t mu_hn_head_height(const mu_hn_window *w, const mu_hn_character *c, const mu_hn_env *env)
{
    int32_t h = c->height;
    if (c->kind != MU_HN_PLAYER)
        return h;
    if (env->state2 && env->state2(env->context, c))
        return w->height_state;
    int32_t ride = c->ride;
    if (ride == 0xffff) {
        h = c->wing != -1 ? w->height_wing : w->height_player;
        if (c->monster_class == 0x271 || c->monster_class == 0x272)
            h = (int32_t)c->height - w->height_player + h;
        else if (c->monster_class == -1) {
            int32_t base = c->class_byte & 0xf;   /* 0x0095f5cc */
            if (base == 6 || base == 11)
                h += 0x14;
            else if (base == 15)
                h += 0x1e;
        }
        return h;
    }
    switch (ride) {
    case 0x1a02: h = w->height_ride_a; break;
    case 0x1a03: h = w->height_ride_b; break;
    case 0x1a04: case 0x19d7: case 0x184b: case 0x184c: case 0x1853: case 0x1854: case 0x185d: case 0x185e:
    case 0x28f7: h = w->height_ride_c; break;
    case 0x1a25: case 0x19e3: case 0x19e4: h = w->height_ride; break;
    case 0x1833: case 0x1834: case 0x1835: case 0x1836: h = w->height_ride_d; break;
    default: h = w->height_ride; break;
    }
    if (c->monster_class == 0x271 || c->monster_class == 0x272) {
        int32_t d = (int32_t)c->height - w->height_player;
        h += d / 2;                               /* cdq; sub; sar: toward zero */
    }
    return h;
}

void mu_hn_name_text(const mu_hn_character *c, const mu_hn_env *env, char *out, size_t cap)
{
    const char *fmt = env->gt_level_format ? env->gt_level_format : "%s[%d]";
    if (c->name_kind == 2)
        snprintf(out, cap, fmt, c->name, (int)c->level + 0x258);
    else if (c->name_kind == 1)
        snprintf(out, cap, fmt, c->name, (int)c->level);
    else
        copy_text(out, cap, c->name);
}

static const char *const class_colors[22] = {
    "#FFFFFF", "#7FB2FF", "#FF3319", "#FFCC19", "#19FF7F", "#A00000", "#FF19FF", "#0000A0", "#A06600", "#00FF00",
    "#B2B2B2", "#CC7FCC", "#B266FF", "#E56B0A", "#800080", "#FFFF00", "#00B0F0", "#00B050", "#CCFF00", "#00FFFF",
    "#BCBCBC", "#C1C469"};

const char *mu_hn_class_color(int32_t index)
{
    return (uint32_t)index <= 0x15 ? class_colors[index] : "#FFFFFF";
}

const char *mu_hn_pk_color(int32_t pk)
{
    switch (pk) {
    case 0: return "#96FFF0";
    case 1: return "#568CEE";
    case 2: return "#8CB1EE";
    case 3: return "#FFDC00";
    case 4: return "#FF9600";
    case 5: return "#FF4400";
    default: return "#FF0000";
    }
}

const char *mu_hn_guild_color(const mu_hn_character *c, const mu_hn_env *env)
{
    if (c == env->hero)
        return "#C8FF00";
    switch (c->guild_relation) {
    case 0: return "#FFFFFF";
    case 2: case 8: return "#FF0000";
    default: return "#C8FF00";
    }
}

void mu_hn_guild_text(const mu_hn_character *c, const mu_hn_env *env, char *out, size_t cap)
{
    copy_text(out, cap, "");
    if (c->guild == -1 || !env->guild)
        return;
    const char *name = NULL, *second = NULL;
    env->guild(env->context, c->guild, &name, &second);
    if (!name || !name[0])
        return;
    if (second && second[0])
        snprintf(out, cap, "%s - %s", name, second);
    else
        copy_text(out, cap, name);
}

int32_t mu_hn_gens_frame(const mu_hn_character *c, const mu_hn_env *env)
{
    if (!c->gens)
        return 0x1d;
    if (env->gens_option && env->hero && c->guild != env->hero->guild)
        return 0x1d;
    int32_t rank = c->gens_rank;
    if (rank < 1 || rank > 0xe)
        rank = 0xe;
    return ((int32_t)c->gens - 1) * 0xe + rank;
}

int mu_hn_strife_gens(const mu_hn_character *c, const mu_hn_env *env)
{
    if (env->hero_gm)
        return 0;
    if (env->gens_world && env->hero && c->gens != env->hero->gens)
        return 1;
    if (env->gens_option && env->hero && c->guild != env->hero->guild)
        return 1;
    return 0;
}

/* ---- addInfo ---- */

int mu_hn_add_info(mu_hn_window *w, const mu_hn_character *c, const mu_hn_env *env, mu_hn_info *info)
{
    if (!c)
        return 0;
    if (mu_hn_find(w, c->key))
        return 0;
    if (c->kind == MU_HN_PLAYER) {
        if (c->monster_class == 0x396)
            return 0;
    } else if (c->kind != MU_HN_MONSTER)
        return 0;
    mu_hn_entry e;
    entry_defaults(&e);
    e.key = c->key;
    e.type = c->kind;
    float z = (float)c->height + c->position[2];
    char base[MU_HN_TEXT];
    if (c->kind == MU_HN_MONSTER) {
        mu_hn_name_text(c, env, base, sizeof base);
        copy_text(e.name, sizeof e.name, base);
        int special = c->monster_class == 0x2a9 || c->monster_class == 0x2b2;   /* 0x00aa0f0f */
        if (!special && env->hero_level < (int32_t)c->level)
            snprintf(e.name, sizeof e.name, "<font color='%s' size='12'>%s</font>", mu_hn_class_color(2), base);
    } else {
        mu_hn_name_text(c, env, base, sizeof base);
        if (z == 0.0f)
            z = (float)w->height_player;
        snprintf(e.name, sizeof e.name, "<font color='%s' size='14'>%s</font>", mu_hn_pk_color(c->pk), base);
        if (env->duel_key == c->key && env->hero && !strcmp(c->duel_name, env->hero->name)) {
            e.hp_show = 1;
            e.hp = env->duel_hp;
        } else {
            e.hp_show = 0;
            e.hp = 0;
        }
    }
    float position[3] = {c->position[0], c->position[1], z}, sx = 0.0f, sy = 0.0f;
    if (env->project)
        env->project(env->context, position, &sx, &sy);
    e.show = w->monster_view;
    e.x = (float)mu_hn_cvtt(sx);
    e.y = (float)mu_hn_cvtt(sy);
    e.hp = mu_hn_hp_percent(c->hp, c->max_hp);
    e.elemental = c->elemental;
    for (int i = 0; i < 4; ++i)
        e.att[i] = c->resist[i];
    for (int i = 0; i < 3; ++i)
        e.damage_type[i] = (uint8_t)(env->damage_type && env->damage_type(env->context, c->monster_class, i) != 0);
    e.name_show = env->name_option;
    e.strife = (uint8_t)mu_hn_strife_gens(c, env);
    e.gens = mu_hn_gens_frame(c, env);
    mu_hn_guild_text(c, env, e.guild, sizeof e.guild);
    copy_text(e.server, sizeof e.server, c->server);
    if (!insert_entry(w, &e))
        return 0;
    if (env->world == 0x8b && c->kind == MU_HN_MONSTER)   /* 0x00da9d49, after the insert: only the movie's copy */
        e.show = 0;
    mu_hn_find(w, e.key)->addinfo_show = e.show;
    if (info) {
        memset(info, 0, sizeof *info);
        info->key = e.key;
        info->type = e.type;
        copy_text(info->name, sizeof info->name, e.name);
        copy_text(info->guild, sizeof info->guild, e.guild);
        copy_text(info->server, sizeof info->server, e.server);
        info->elemental = e.elemental;
        info->mark = c->mark;
        info->x = e.x;
        info->y = e.y;
        info->hp = e.hp;
        info->is_show = e.show;
        info->hp_show = e.hp_show;
        info->name_show = e.name_show;
        info->strife = e.strife;
        info->gens_frame = e.gens;
        memcpy(info->att, e.att, sizeof info->att);
        memcpy(info->damage_type, e.damage_type, sizeof info->damage_type);
    }
    return 1;
}

static size_t json_quote(char *out, size_t cap, const char *s)
{
    size_t n = 0;
#define PUT(ch) do { if (n + 1 < cap) out[n] = (ch); n++; } while (0)
    PUT('"');
    for (const unsigned char *p = (const unsigned char *)s; *p; ++p) {
        if (*p == '"' || *p == '\\') {
            PUT('\\');
            PUT((char)*p);
        } else if (*p < 0x20) {
            char u[8];
            snprintf(u, sizeof u, "\\u%04x", *p);
            for (char *q = u; *q; ++q)
                PUT(*q);
        } else
            PUT((char)*p);
    }
    PUT('"');
#undef PUT
    if (cap)
        out[n < cap ? n : cap - 1] = 0;
    return n;
}

static void json_number(char *out, size_t cap, double v)
{
    if (v == floor(v) && fabs(v) < 1e15)
        snprintf(out, cap, "%.0f", v);
    else
        snprintf(out, cap, "%.9g", v);
}

size_t mu_hn_info_json(const mu_hn_info *in, char *out, size_t cap)
{
    char name[MU_HN_TEXT * 2], guild[MU_HN_TEXT * 2], server[MU_HN_TEXT * 2], x[32], y[32];
    json_quote(name, sizeof name, in->name);
    json_quote(guild, sizeof guild, in->guild);
    json_quote(server, sizeof server, in->server);
    json_number(x, sizeof x, in->x);
    json_number(y, sizeof y, in->y);
    int n = snprintf(out, cap,
                     "{\"key\":%d,\"type\":%d,\"name\":%s,\"GuildName\":%s,\"ServerName\":%s,\"elemental\":%d,"
                     "\"mark\":%d,\"x\":%s,\"y\":%s,\"hp\":%d,\"isShow\":%s,\"isPlayerHpShow\":%s,"
                     "\"isPlayerNameShow\":%s,\"isStrifeGens\":%s,\"GensFrame\":%d,\"attArray\":["
                     "{\"att\":%d},{\"att\":%d},{\"att\":%d},{\"att\":%d}],\"damageTypeArray\":["
                     "{\"damagetype\":%s},{\"damagetype\":%s},{\"damagetype\":%s}]}",
                     in->key, in->type, name, guild, server, in->elemental, in->mark, x, y, in->hp,
                     in->is_show ? "true" : "false", in->hp_show ? "true" : "false",
                     in->name_show ? "true" : "false", in->strife ? "true" : "false", in->gens_frame, in->att[0],
                     in->att[1], in->att[2], in->att[3], in->damage_type[0] ? "true" : "false",
                     in->damage_type[1] ? "true" : "false", in->damage_type[2] ? "true" : "false");
    return n < 0 ? 0 : (size_t)n;
}

/* ---- the per-frame update ---- */

typedef struct op_sink {
    mu_hn_op *ops;
    int32_t n, max;
} op_sink;

static void emit(op_sink *s, int32_t key, int32_t kind, double number, double y, const char *text)
{
    if (s->n < s->max) {
        mu_hn_op *o = &s->ops[s->n];
        memset(o, 0, sizeof *o);
        o->key = key;
        o->kind = kind;
        o->number = number;
        o->y = y;
        copy_text(o->text, sizeof o->text, text);
    }
    s->n++;
}

static void update_player(mu_hn_window *w, mu_hn_entry *e, const mu_hn_character *c, const mu_hn_env *env,
                          op_sink *s)
{
    (void)w;
    int32_t key = e->key;
    uint8_t opt = env->name_option;
    uint8_t show = 1;
    if (!opt && c->elemental == 0 && c->key != env->duel_key && !e->flag_a0)
        show = 0;
    if (e->show != show)
        e->show = show;
    if (!e->mc_visible) {                                     /* GetDisplayInfo: hidden -> visible */
        e->mc_visible = 1;
        emit(s, key, MU_HN_OP_MC_VISIBLE, 1, 0, NULL);
    }
    if (e->name_show != opt) {
        e->name_show = opt;
        emit(s, key, MU_HN_OP_NAME_SHOW, opt, 0, NULL);
    }
    uint8_t hp_show = 0;
    if (c->key == env->duel_key && env->hero && !strcmp(c->duel_name, env->hero->name))
        hp_show = 1;
    int hero_bar = (env->hero_bar_a || env->hero_bar_b) && env->hero && env->hero->key == c->key;
    if (!hp_show) {
        int32_t member_hp = 0;
        int found = env->party_hp && env->party_hp(env->context, c->name, &member_hp);
        if (found && opt) {
            hp_show = 1;
            if (e->hp != member_hp) {
                e->hp = member_hp;
                emit(s, key, MU_HN_OP_SET_HP, member_hp, 0, NULL);
            }
        } else if (hero_bar) {
            hp_show = 1;
            float pct = (float)env->hero_hp / (float)env->hero_max_hp;
            pct = pct * 100.0f;
            int32_t hp = mu_hn_cvtt(pct);
            if (e->hp != hp) {
                e->hp = hp;
                emit(s, key, MU_HN_OP_SET_HP, hp, 0, NULL);
            }
        }
    }
    if (e->hp_show != hp_show) {
        e->hp_show = hp_show;
        emit(s, key, MU_HN_OP_HP_SHOW, hp_show, 0, NULL);
        emit(s, key, MU_HN_OP_HP_VISIBLE, hp_show, 0, NULL);
    } else if (hero_bar) {
        e->hp_show = hp_show;
        emit(s, key, MU_HN_OP_HP_VISIBLE, hp_show, 0, NULL);
    }
    if (e->elemental != c->elemental) {
        e->elemental = c->elemental;
        emit(s, key, MU_HN_OP_ELEMENTAL, e->elemental, 0, NULL);
    }
    int32_t gens = mu_hn_gens_frame(c, env);
    if (e->gens != gens) {
        e->gens = gens;
        emit(s, key, MU_HN_OP_GENS, gens, 0, NULL);
    }
    char guild[MU_HN_TEXT];
    mu_hn_guild_text(c, env, guild, sizeof guild);
    if (strcmp(e->guild, guild)) {
        copy_text(e->guild, sizeof e->guild, guild);
        char html[MU_HN_TEXT * 2];
        html[0] = 0;
        if (guild[0])
            snprintf(html, sizeof html, "<font color='%s' size='12'>&lt; %s &gt;</font>", mu_hn_guild_color(c, env),
                     guild);
        emit(s, key, MU_HN_OP_GUILD, 0, 0, html);
    }
    if (env->server_flag && strcmp(e->server, c->server)) {
        copy_text(e->server, sizeof e->server, c->server);
        char html[MU_HN_TEXT * 2];
        snprintf(html, sizeof html, "<font size='12'>&lt; %s &gt;</font>", c->server);
        emit(s, key, MU_HN_OP_SERVER, 0, 0, html);
    }
    uint8_t strife = (uint8_t)mu_hn_strife_gens(c, env);
    if (e->strife != strife) {
        e->strife = strife;
        emit(s, key, MU_HN_OP_STRIFE, strife, 0, NULL);
    }
}

int32_t mu_hn_update(mu_hn_window *w, const mu_hn_character *(*character)(void *context, int32_t key),
                     const mu_hn_env *env, mu_hn_op *ops, int32_t max)
{
    op_sink s = {ops, 0, max};
    for (int32_t i = 0; i < w->count; ++i) {
        mu_hn_entry *e = &w->entries[i];
        if (!e->has_mc)
            continue;
        const mu_hn_character *c = character ? character(env->context, e->key) : NULL;
        if (!c)
            continue;
        int32_t height = mu_hn_head_height(w, c, env);
        if (e->type == MU_HN_MONSTER) {
            uint8_t show = w->monster_view;
            if (w->selected == e->key)
                show = 1;
            if (e->show != show) {
                e->show = show;
                emit(&s, e->key, MU_HN_OP_INFO_VISIBLE, show, 0, NULL);
            }
        } else if (e->type == MU_HN_PLAYER)
            update_player(w, e, c, env, &s);
        float position[3] = {c->position[0], c->position[1], (float)height + c->position[2]};
        float x = 0.0f, y = 0.0f;
        if (env->project)
            env->project(env->context, position, &x, &y);
        if (!(e->x == x) || !(e->y == y)) {
            e->x = x;
            e->y = y;
            e->mc_visible = 1;
            emit(&s, e->key, MU_HN_OP_POSITION, (double)x, (double)y, NULL);
        }
    }
    return s.n < max ? s.n : max;
}

/* ---- setHp, removeInfo, selection ---- */

int32_t mu_hn_set_hp(mu_hn_window *w, int32_t key, uint32_t hp, uint32_t max, mu_hn_op *op)
{
    mu_hn_entry *e = mu_hn_find(w, key);
    if (!e)
        return 0;
    int32_t pct = 0;
    if (hp && max)
        pct = mu_hn_hp_percent(hp, max);
    if (!e->has_mc || e->hp == pct)
        return 0;
    e->hp = pct;
    op_sink s = {op, 0, 1};
    emit(&s, key, MU_HN_OP_SET_HP, pct, 0, NULL);
    return 1;
}

int32_t mu_hn_remove(mu_hn_window *w, const mu_hn_character *c, mu_hn_op *op)
{
    if (!c)
        return 0;
    mu_hn_entry *e = mu_hn_find(w, c->key);
    if (!e)
        return 0;
    int32_t i = (int32_t)(e - w->entries);
    memmove(&w->entries[i], &w->entries[i + 1], (size_t)(w->count - i - 1) * sizeof *e);
    w->count--;
    op_sink s = {op, 0, 1};
    emit(&s, c->key, MU_HN_OP_REMOVE, c->kind, 0, NULL);
    return 1;
}

int32_t mu_hn_select(mu_hn_window *w, int32_t key, mu_hn_op *op)
{
    w->selected = key;
    if (w->selected == -1 || !w->monster_view)
        return 0;
    mu_hn_entry *e = mu_hn_find(w, key);
    if (!e || !e->has_mc)
        return 0;
    op_sink s = {op, 0, 1};
    emit(&s, key, MU_HN_OP_TOP, 0, 0, NULL);
    return 1;
}

void mu_hn_set_monster_view(mu_hn_window *w, int view)
{
    w->monster_view = (uint8_t)view;
}

int32_t mu_hn_track_selection(mu_hn_window *w, const mu_hn_character **current, const mu_hn_character *hovered,
                              mu_hn_op *ops)
{
    int32_t n = 0;
    if (hovered) {
        if (*current == hovered)
            return 0;
        if (*current) {
            n += mu_hn_select(w, -1, ops + n);
            *current = NULL;
        }
        *current = hovered;
        n += mu_hn_select(w, hovered->key, ops + n);
    } else if (*current) {
        n += mu_hn_select(w, -1, ops + n);
        *current = NULL;
    }
    return n;
}

/* ---- chat ---- */

int32_t mu_hn_chat_bubble(mu_hn_window *w, const mu_hn_character *const *characters, int32_t n, const char *name,
                          const char *text, int32_t flag, mu_hn_op *op)
{
    for (int32_t i = 0; i < n; ++i) {
        const mu_hn_character *c = characters[i];
        if (!c || !c->live)
            continue;
        if (strcmp(c->name, name))
            continue;
        char msg[MU_HN_TEXT];
        snprintf(msg, sizeof msg, "%s: %s", c->name, text);
        int32_t time = flag == 1 ? 0x9c40 : 0x2710;
        mu_hn_entry *e = mu_hn_find(w, c->key);
        if (!e || !e->has_mc)
            return 0;
        op_sink s = {op, 0, 1};
        emit(&s, c->key, MU_HN_OP_MESSAGE, time, 0, msg);
        return 1;
    }
    return 0;
}

int32_t mu_hn_chat_route(const char *text, int gm, int32_t *bubble_flag, int32_t *skip)
{
    *bubble_flag = -1;
    *skip = 0;
    if (text[0] == '~') {
        *skip = 1;
        return 5;
    }
    if (text[0] == '@' && text[1] == '@') {
        *skip = 2;
        return 7;
    }
    if (text[0] == '@') {
        *skip = 1;
        return 6;
    }
    if (text[0] == '$') {
        *skip = 1;
        return 9;
    }
    if (text[0] == '#') {
        *skip = 1;
        *bubble_flag = gm ? 0 : 1;
        return gm ? 8 : 1;
    }
    *bubble_flag = 0;
    return gm ? 8 : 1;
}
