/* Overhead names in the native world (NATIVE-NAMES-001); see mu_names.h. */
#include "mu_names.h"

#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void logf_(mu_names *n, const char *fmt, ...)
{
    if (n->log_count >= 16)
        return;
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(n->log[n->log_count++], sizeof n->log[0], fmt, ap);
    va_end(ap);
}

static void project_bridge(void *context, const float position[3], float *x, float *y)
{
    mu_names *n = context;
    if (n->project)
        n->project(n->project_context, position, x, y);
    else
        *x = *y = 0.0f;
}

void mu_names_init(mu_names *n)
{
    memset(n, 0, sizeof *n);
    mu_hn_window_init(&n->window);
    n->hero_slot = -1;
    n->env.context = n;
    n->env.project = project_bridge;
    n->env.duel_key = -1;
    n->env.name_option = 1;          /* DEMO: the option byte comes from the server/option.ini; names shown */
    n->env.gt_level_format = NULL;   /* "%s[%d]" (GlobalText[4595] of the installed client) */
}

void mu_names_set_sink(mu_names *n, const mu_names_sink *sink)
{
    if (sink)
        n->sink = *sink;
    else
        memset(&n->sink, 0, sizeof n->sink);
}

mu_hn_character *mu_names_find(mu_names *n, int32_t key)
{
    for (int i = 0; i < MU_NAMES_MAX; ++i)
        if (n->used[i] && n->chars[i].key == key)
            return &n->chars[i];
    return NULL;
}

mu_hn_character *mu_names_character(mu_names *n, int32_t key)
{
    mu_hn_character *c = mu_names_find(n, key);
    if (c)
        return c;
    for (int i = 0; i < MU_NAMES_MAX; ++i)
        if (!n->used[i]) {
            n->used[i] = 1;
            c = &n->chars[i];
            memset(c, 0, sizeof *c);
            c->key = (int16_t)key;
            c->guild = -1;
            c->wing = -1;
            c->ride = 0xffff;
            c->monster_class = -1;
            c->live = 1;
            c->pk = 3;
            return c;
        }
    return NULL;
}

void mu_names_set_hero(mu_names *n, int32_t key)
{
    mu_hn_character *c = mu_names_character(n, key);
    n->hero_slot = c ? (int32_t)(c - n->chars) : -1;
    n->env.hero = c;
}

static const mu_hn_character *lookup(void *context, int32_t key)
{
    return mu_names_find(context, key);
}

/* ---- the movie model ---- */

static mu_names_plate *plate(mu_names *n, int32_t key)
{
    for (int32_t i = 0; i < n->plate_count; ++i)
        if (n->plates[i].key == key)
            return &n->plates[i];
    return NULL;
}

static void apply(mu_names *n, const mu_hn_op *o)
{
    n->stats.ops++;
    if (o->kind == MU_HN_OP_REMOVE) {
        mu_names_plate *p = plate(n, o->key);
        if (p) {
            int32_t i = (int32_t)(p - n->plates);
            memmove(p, p + 1, (size_t)(n->plate_count - i - 1) * sizeof *p);
            n->plate_count--;
        }
        return;
    }
    mu_names_plate *p = plate(n, o->key);
    if (!p)
        return;
    switch (o->kind) {
    case MU_HN_OP_INFO_VISIBLE: p->info_visible = (uint8_t)(o->number != 0); break;
    case MU_HN_OP_MC_VISIBLE: p->mc_visible = 1; break;
    case MU_HN_OP_NAME_SHOW: p->name_show = (uint8_t)(o->number != 0); break;
    case MU_HN_OP_SET_HP: p->hp = (int32_t)o->number; n->stats.hp_updates++; break;
    case MU_HN_OP_HP_SHOW: p->hp_show = (uint8_t)(o->number != 0); break;
    case MU_HN_OP_HP_VISIBLE: p->hp_show = (uint8_t)(o->number != 0); break;
    case MU_HN_OP_ELEMENTAL: p->elemental = (int32_t)o->number; break;
    case MU_HN_OP_GENS: p->gens = (int32_t)o->number; break;
    case MU_HN_OP_GUILD: snprintf(p->guild, sizeof p->guild, "%s", o->text); break;
    case MU_HN_OP_SERVER: snprintf(p->server, sizeof p->server, "%s", o->text); break;
    case MU_HN_OP_STRIFE: p->strife = (uint8_t)(o->number != 0); break;
    case MU_HN_OP_POSITION:
        p->x = (float)o->number;
        p->y = (float)o->y;
        p->mc_visible = 1;
        n->stats.positions++;
        break;
    case MU_HN_OP_TOP: p->order = ++n->order; break;
    case MU_HN_OP_MESSAGE:
        snprintf(p->message, sizeof p->message, "%s", o->text);
        p->message_until = n->now + (uint32_t)o->number;
        n->stats.messages++;
        break;
    default: break;
    }
}

static void emit(mu_names *n, int32_t type, const mu_hn_op *ops, int32_t count)
{
    for (int32_t i = 0; i < count; ++i) {
        apply(n, &ops[i]);
        if (ops[i].kind == MU_HN_OP_REMOVE) {
            if (n->sink.remove_info)
                n->sink.remove_info(n->sink.user, ops[i].key, (int32_t)ops[i].number);
        } else if (n->sink.op)
            n->sink.op(n->sink.user, type, &ops[i]);
    }
}

static int32_t type_of(mu_names *n, int32_t key)
{
    mu_hn_entry *e = mu_hn_find(&n->window, key);
    return e ? e->type : 0;
}

/* ---- the calls ---- */

int mu_names_add(mu_names *n, int32_t key)
{
    mu_hn_character *c = mu_names_find(n, key);
    if (!c)
        return 0;
    mu_hn_info info;
    if (!mu_hn_add_info(&n->window, c, &n->env, &info)) {
        n->stats.skipped++;
        return 0;
    }
    n->stats.added++;
    if (n->sink.add_info)
        n->sink.add_info(n->sink.user, &info);
    if (n->plate_count < MU_NAMES_MAX) {
        mu_names_plate *p = &n->plates[n->plate_count++];
        memset(p, 0, sizeof *p);
        p->key = info.key;
        p->type = info.type;
        p->x = info.x;
        p->y = info.y;
        /* PlayerName.setData: _visible = isShow; MonsterInfoMC.setData: _visible = isShow */
        p->mc_visible = (uint8_t)(info.type == MU_HN_PLAYER ? info.is_show : 1);
        p->info_visible = (uint8_t)(info.type == MU_HN_PLAYER ? 1 : info.is_show);
        p->hp_show = info.hp_show;
        p->name_show = info.name_show;
        p->strife = info.strife;
        p->hp = info.hp;
        p->elemental = info.elemental;
        p->gens = info.gens_frame;
        p->mark = info.mark;
        snprintf(p->name, sizeof p->name, "%s", info.name);
        snprintf(p->guild, sizeof p->guild, "%s", info.guild);
        snprintf(p->server, sizeof p->server, "%s", info.server);
        p->order = ++n->order;
    }
    mu_hn_set_mc(&n->window, key, 1);   /* the movie's addMC event (handler 0x00c81842) */
    logf_(n, "addInfo %d type %d %.40s", (int)info.key, (int)info.type, info.name);
    return 1;
}

void mu_names_remove(mu_names *n, int32_t key, int forget)
{
    mu_hn_character *c = mu_names_find(n, key);
    if (!c)
        return;
    mu_hn_op op;
    int32_t type = type_of(n, key);
    if (mu_hn_remove(&n->window, c, &op)) {
        n->stats.removed++;
        emit(n, type, &op, 1);
    }
    if (n->hovered_current == c)
        n->hovered_current = NULL;
    if (forget) {
        n->used[c - n->chars] = 0;
        if (n->env.hero == c) {
            n->env.hero = NULL;
            n->hero_slot = -1;
        }
    }
}

void mu_names_set_hp(mu_names *n, int32_t key, uint32_t hp, uint32_t max)
{
    mu_hn_op op;
    if (mu_hn_set_hp(&n->window, key, hp, max, &op))
        emit(n, type_of(n, key), &op, 1);
}

void mu_names_hover(mu_names *n, int32_t key)
{
    const mu_hn_character *c = key >= 0 ? mu_names_find(n, key) : NULL;
    mu_hn_op ops[2];
    int32_t count = mu_hn_track_selection(&n->window, &n->hovered_current, c, ops);
    if (count) {
        n->stats.selections++;
        for (int32_t i = 0; i < count; ++i)
            emit(n, type_of(n, ops[i].key), &ops[i], 1);
    }
}

void mu_names_set_monster_view(mu_names *n, int view)
{
    mu_hn_set_monster_view(&n->window, view);
}

int32_t mu_names_chat(mu_names *n, const char *name, const char *text, int gm)
{
    int32_t flag, skip;
    int32_t type = mu_hn_chat_route(text, gm, &flag, &skip);
    if (flag >= 0) {
        const mu_hn_character *list[MU_NAMES_MAX];
        int32_t count = 0;
        for (int i = 0; i < MU_NAMES_MAX; ++i)
            if (n->used[i])
                list[count++] = &n->chars[i];
        mu_hn_op op;
        if (mu_hn_chat_bubble(&n->window, list, count, name, text + skip, flag, &op))
            emit(n, type_of(n, op.key), &op, 1);
    }
    return type;
}

void mu_names_update(mu_names *n, void (*project)(void *context, const float position[3], float *x, float *y),
                     void *context, uint32_t now)
{
    n->project = project;
    n->project_context = context;
    n->now = now;
    static mu_hn_op ops[MU_NAMES_MAX * 16];
    int32_t count = mu_hn_update(&n->window, lookup, &n->env, ops, (int32_t)(sizeof ops / sizeof ops[0]));
    for (int32_t i = 0; i < count; ++i)
        emit(n, type_of(n, ops[i].key), &ops[i], 1);
    for (int32_t i = 0; i < n->plate_count; ++i)   /* HudChat's setInterval(validateNow, time) */
        if (n->plates[i].message[0] && (int32_t)(now - n->plates[i].message_until) >= 0)
            n->plates[i].message[0] = 0;
    n->stats.frames++;
}

/* ---- stand-in drawing ---- */

static const uint8_t BOX[4] = {16, 12, 8, 170}, EDGE[4] = {120, 96, 60, 220}, BAR_BACK[4] = {30, 0, 0, 200},
                     BAR_HP[4] = {214, 24, 24, 255}, BAR_EDGE[4] = {0, 0, 0, 230};

static void hp_bar(uint8_t *frame, int32_t width, int32_t height, int32_t x, int32_t y, int32_t hp)
{
    /* mcMonsterHP / mcPlayerHP: a 109 x 11 frame, the value bar at (3, 3) (TweenProgress setValue(hp, 100)) */
    mu_label_fill(frame, width, height, x, y, 109, 11, BAR_BACK);
    mu_label_frame(frame, width, height, x, y, 109, 11, BAR_EDGE);
    int32_t w = hp < 0 ? 0 : hp > 100 ? 103 : hp * 103 / 100;
    mu_label_fill(frame, width, height, x + 3, y + 3, w, 5, BAR_HP);
}

static void bubble(mu_label_fonts *fonts, uint8_t *frame, int32_t width, int32_t height, float ox, float oy,
                   const char *msg)
{
    /* HudChat: _txt (autoSize) at (-w/2, -(h + 14)), _bg the text box grown by 8 / 5 pixels */
    char esc[MU_HN_TEXT * 2];
    size_t k = 0;
    for (const char *s = msg; *s && k + 6 < sizeof esc; ++s) {   /* the field is plain text, not HTML */
        if (*s == '<') { memcpy(esc + k, "&lt;", 4); k += 4; }
        else if (*s == '&') { memcpy(esc + k, "&amp;", 5); k += 5; }
        else esc[k++] = *s;
    }
    esc[k] = 0;
    mu_label_image img;
    if (mu_label_html(fonts, esc, 0xffffff, 12, 0, 0, &img) || !img.rgba)
        return;
    int32_t w = img.width + 6, h = img.height + 4;
    int32_t tx = (int32_t)ox - w / 2, ty = (int32_t)oy - (h + 14);
    mu_label_fill(frame, width, height, tx - 8, ty - 5, w + 16, h + 10, BOX);
    mu_label_frame(frame, width, height, tx - 8, ty - 5, w + 16, h + 10, EDGE);
    mu_label_blend(frame, width, height, &img, tx + 3, ty + 2, 1.0f);
    mu_label_image_free(&img);
}

static int by_order(const void *a, const void *b)
{
    const mu_names_plate *p = *(const mu_names_plate *const *)a, *q = *(const mu_names_plate *const *)b;
    if (p->type != q->type)   /* the monster container lies below the player container */
        return p->type == MU_HN_MONSTER ? -1 : 1;
    return p->order < q->order ? -1 : p->order > q->order;
}

void mu_names_draw(const mu_names *n, mu_label_fonts *fonts, uint8_t *frame, int32_t width, int32_t height)
{
    const mu_names_plate *list[MU_NAMES_MAX];
    int32_t count = 0;
    for (int32_t i = 0; i < n->plate_count; ++i)
        list[count++] = &n->plates[i];
    qsort(list, (size_t)count, sizeof list[0], by_order);
    for (int32_t i = 0; i < count; ++i) {
        const mu_names_plate *p = list[i];
        if (!p->mc_visible)
            continue;
        float x = p->x, y = p->y;
        if (p->type == MU_HN_MONSTER) {
            /* MonsterName: _info at (-62, -23); MonsterInfoMC: _txName (2, 2) 121 wide centred, _hp at (6, 18) */
            if (p->info_visible) {
                mu_label_image img;
                if (!mu_label_html(fonts, p->name, 0xffffff, 12, 1, 1, &img) && img.rgba) {
                    int32_t bx = (int32_t)x - 62 + 2, by = (int32_t)y - 23 + 2;
                    mu_label_blend(frame, width, height, &img, bx + (121 - img.width) / 2, by, 1.0f);
                    mu_label_image_free(&img);
                }
                hp_bar(frame, width, height, (int32_t)x - 62 + 6, (int32_t)y - 23 + 18, p->hp);
            }
            if (p->message[0])
                bubble(fonts, frame, width, height, x, y - 26.0f, p->message);
            continue;
        }
        /* PlayerNameMC.updateMoviePos: [server<br>][guild<br>]name, centred, bottom 10 above the clip */
        char html[MU_HN_TEXT * 3 + 16] = "";
        if (p->server[0])
            snprintf(html + strlen(html), sizeof html - strlen(html), "%s<br>", p->server);
        if (p->guild[0] && !p->strife)
            snprintf(html + strlen(html), sizeof html - strlen(html), "%s<br>", p->guild);
        if (!p->strife)
            snprintf(html + strlen(html), sizeof html - strlen(html), "%s", p->name);
        mu_label_image img;
        int32_t text_h = 21;
        if (!mu_label_html(fonts, html, 0xffffff, 12, 1, 1, &img)) {
            if (img.rgba)
                text_h = img.height;
            int32_t ty = (int32_t)y - text_h - 10;
            if (p->hp_show) {
                hp_bar(frame, width, height, (int32_t)x - 54, (int32_t)y - 10 - 11, p->hp);
                ty -= 11;
            }
            if (p->name_show && img.rgba)
                mu_label_blend(frame, width, height, &img, (int32_t)x - img.width / 2, ty, 1.0f);
            mu_label_image_free(&img);
        }
        if (p->message[0])   /* PlayerName.setMessage: _y = _info.getChatY() - 16 */
            bubble(fonts, frame, width, height, x, y - (float)text_h - 16.0f, p->message);
    }
}

void mu_names_report(const mu_names *n, char *out, size_t cap)
{
    const mu_names_stats *s = &n->stats;
    snprintf(out, cap,
             "\"names\": {\"plates\": %d, \"added\": %u, \"removed\": %u, \"skipped\": %u, \"frames\": %u, "
             "\"ops\": %u, \"positions\": %u, \"messages\": %u, \"hp_updates\": %u, \"selections\": %u}",
             (int)n->plate_count, s->added, s->removed, s->skipped, s->frames, s->ops, s->positions, s->messages,
             s->hp_updates, s->selections);
}
