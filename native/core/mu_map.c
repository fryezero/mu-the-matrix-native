/* Maps and travel in the native client (NATIVE-MAP-001).  See mu_map.h. */
#include "mu_map.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#include "mu_lang.h"

#define DEMO_STRIFE_KEY 0x2a   /* the live client's strife list on MTM-1: Vulcanus only (0x00bdbf82's 1-key branch) */

const char *mu_map_text(const mu_map_session *s, int32_t index)
{
    const char *t = s->lang ? mu_lang_text(s->lang, index) : NULL;
    if (t)
        return t;
    /* a miss: the client's lookup 0x011753c3 returns "[Text] error index : %d" (never an empty text, which
     * every name rule of the move window would match) */
    mu_map_session *owner = (mu_map_session *)s;
    char *buf = owner->text_ring[owner->text_next++ & 3];
    snprintf(buf, sizeof owner->text_ring[0], "[Text] error index : %d", (int)index);
    return buf;
}

const char *mu_map_world_name(const mu_map_session *s, int32_t world)
{
    const char *n = s->lang ? mu_lang_map_name(s->lang, world) : NULL;
    return n ? n : "";
}

static const mu_move_record *lookup(void *user, int32_t key)
{
    mu_map_session *s = user;
    for (int i = 0; i < s->nrecords; i++)
        if (s->records[i].key == key)
            return &s->records[i];
    return NULL;
}

static const char *text_cb(void *user, int32_t index)
{
    return mu_map_text(user, index);
}

static const mu_gate *gate_lookup(void *user, int32_t index)
{
    mu_map_session *s = user;
    for (int i = 0; i < s->ngates; i++)
        if (s->gates[i].index == index)
            return &s->gates[i];
    return NULL;
}

static uint32_t rnd(mu_map_session *s)
{
    s->rng = s->rng * 1103515245u + 12345u;
    return s->rng >> 8;
}

static int by_id(const void *a, const void *b)
{
    const mu_move_record *x = a, *y = b;
    return x->id != y->id ? (x->id < y->id ? -1 : 1) : (x->key < y->key ? -1 : x->key > y->key);
}

void mu_map_session_init(mu_map_session *s, const mu_lang *lang, int32_t world, int32_t tile_x, int32_t tile_y)
{
    memset(s, 0, sizeof *s);
    s->lang = lang;
    s->world = world;
    s->tile_x = tile_x;
    s->tile_y = tile_y;
    s->rng = 0x5eedu;
    s->zen = 10000000;
    s->hero.level = 1600;          /* demo: level 400 + master level 1200 */
    s->hero.strife_ok = 1;
    for (int i = 0; i < 5; i++)
        s->favourites[i].flag = s->favourites[i].key = 0xffff;
    if (!lang)
        return;
    size_t n = mu_lang_move_count(lang);
    for (size_t i = 0; i < n && s->nrecords < MU_MAP_MOVES_MAX; i++) {
        const mu_lang_move *m = mu_lang_move_at(lang, i);
        mu_move_record *r = &s->records[s->nrecords++];
        r->key = m->index;
        r->id = m->id;
        r->name = m->name ? m->name : "";
        r->server_name = m->server_name ? m->server_name : "";
        r->zen = m->zen;
        r->min_level = m->min_level;
        r->max_level = m->max_level;
        r->gate = m->gate;
        r->x44 = m->x44;
        r->x48 = m->x48;
        r->x4c = m->x4c;
    }
    /* the table's key list is the script's line order; the live manager holds it by record id (entry +8 == id) */
    mu_move_record sorted[MU_MAP_MOVES_MAX];
    memcpy(sorted, s->records, sizeof(mu_move_record) * (size_t)s->nrecords);
    qsort(sorted, (size_t)s->nrecords, sizeof sorted[0], by_id);
    for (int i = 0; i < s->nrecords; i++)
        s->keys[i] = sorted[i].key;
    s->nentries = mu_move_build(s->keys, s->nrecords, lookup, s, s->entries, MU_MAP_MOVES_MAX);
    for (int32_t index = 0; index < 4096 && s->ngates < MU_MAP_GATES_MAX; index++) {
        const mu_lang_gate *g = mu_lang_gate_get(lang, index);
        if (!g)
            continue;
        mu_gate *o = &s->gates[s->ngates++];
        o->index = g->index;
        o->flag = g->flag;
        o->world = g->world;
        o->x1 = g->x1;
        o->y1 = g->y1;
        o->x2 = g->x2;
        o->y2 = g->y2;
        o->target = g->target;
        o->dir = g->dir;
        o->min_level = g->min_level;
        o->max_level = g->max_level;
    }
}

void mu_map_set_position(mu_map_session *s, int32_t world, int32_t tile_x, int32_t tile_y)
{
    s->world = world;
    s->tile_x = tile_x;
    s->tile_y = tile_y;
}

/* ---- map overlay ---------------------------------------------------------------------------------------- */

int mu_map_session_load_map(mu_map_session *s, const char *game_root, char *name, size_t cap)
{
    char file[64], path[4096];
    mu_map_navimap_name(s->world, file, sizeof file);
    if (name)
        snprintf(name, cap, "%s", file);
    s->hud.available = 0;
    if (game_root) {
        /* the client asks for ./Data/Interface/GFx/Navimap/<name>; the installed folder is NaviMap and the
         * files carry upper-case names (case-insensitive on Windows) */
        struct stat st;
        snprintf(path, sizeof path, "%s/Data/Interface/GFx/NaviMap/%s", game_root, file);
        if (!stat(path, &st))
            s->hud.available = 1;
        else {
            char upper[64];
            snprintf(upper, sizeof upper, "Navimap%02d.OZP", (int)(s->world + 1));
            snprintf(path, sizeof path, "%s/Data/Interface/GFx/NaviMap/%s", game_root, upper);
            if (!stat(path, &st))
                s->hud.available = 1;
        }
    }
    return s->hud.available;
}

void mu_map_bind_overlay(mu_map_session *s, const struct mu_session *overlay)
{
    s->overlay = overlay;
    ++s->overlay_epoch;
}

void mu_map_toggle(mu_map_session *s, int show, mu_map_show_result *out)
{
    mu_map_show(&s->hud, show, s->world, s->tile_x, s->tile_y, out);
    if (out->notice)
        snprintf(s->notice, sizeof s->notice, "%s", mu_map_text(s, MU_MAP_TEXT_UNAVAILABLE));
}

/* ---- move window ---------------------------------------------------------------------------------------- */

static void prepare_window(mu_map_session *s)
{
    int32_t strife = DEMO_STRIFE_KEY;
    mu_move_set_strife(s->entries, s->nentries, &strife, 1, lookup, s);
    s->hero.zen = s->zen > 0x7fffffff ? 0x7fffffff : (int32_t)s->zen;
    mu_move_availability(s->entries, s->nentries, &s->hero, lookup, text_cb, s);
}

void mu_map_move_sort(mu_map_session *s, int32_t order)
{
    s->sort_order = order;
    mu_move_sort(s->entries, s->nentries, order);
}

int mu_map_move_rows(mu_map_session *s, mu_move_row *rows, int max)
{
    prepare_window(s);
    mu_move_sort(s->entries, s->nentries, s->sort_order);
    int n = 0;
    for (int i = 0; i < s->nentries && n < max; i++, n++)
        mu_move_row_make(&s->entries[i], i, &s->hero, mu_move_is_favourite(s->favourites, s->entries[i].key2),
                         lookup, text_cb, s, &rows[n]);
    s->move_open = 1;
    return n;
}

/* The demo server: a target gate's rectangle, a tile in it, the teleport. */
static int land_on_gate(mu_map_session *s, int32_t gate_index, uint16_t number)
{
    const mu_gate *t = gate_lookup(s, gate_index);
    if (!t)
        return 0;
    int32_t w = t->x2 - t->x1 + 1, h = t->y2 - t->y1 + 1;
    int32_t x = t->x1 + (w > 0 ? (int32_t)(rnd(s) % (uint32_t)w) : 0);
    int32_t y = t->y1 + (h > 0 ? (int32_t)(rnd(s) % (uint32_t)h) : 0);
    uint8_t p[16];
    mu_map_teleport_packet(t->world, x, y, t->dir, number, p, sizeof p);
    mu_teleport_parse(p, 11, &s->teleport);
    s->pending = 1;
    snprintf(s->last, sizeof s->last, "teleport world %d tile %d,%d dir %d (gate %d)", t->world, x, y, t->dir,
             gate_index);
    return 1;
}

static int demo_move(mu_map_session *s, int32_t key)
{
    const mu_move_record *r = lookup(s, key);
    if (!r) {
        snprintf(s->last, sizeof s->last, "move %d: no such map", key);
        return 0;
    }
    int64_t cost = mu_move_required_zen(r, &s->hero);
    if (s->hero.level < r->min_level || s->zen < cost) {
        snprintf(s->last, sizeof s->last, "move %d refused (level %d/%d, zen %lld/%lld)", key, s->hero.level,
                 r->min_level, (long long)s->zen, (long long)cost);
        return 0;
    }
    s->zen -= cost;
    return land_on_gate(s, r->gate, (uint16_t)r->gate);
}

int mu_map_move_click(mu_map_session *s, int32_t index, mu_move_click_result *out)
{
    mu_move_click(s->entries, s->nentries, index, s->world, 0, 0, out);
    if (!out->accepted) {
        snprintf(s->last, sizeof s->last, "move row %d not available", index);
        return 0;
    }
    s->move_open = 0;   /* the click closes the window */
    return demo_move(s, s->entries[index].key2);
}

/* ---- gates ------------------------------------------------------------------------------------------------- */

int mu_map_gate_step(mu_map_session *s, uint32_t now_ms, mu_gate_result *out)
{
    mu_gate_hero h;
    memset(&h, 0, sizeof h);
    h.world = s->world;
    h.tile_x = s->tile_x;
    h.tile_y = s->tile_y;
    h.level = s->hero.level;
    h.loading_world = s->loading_world;
    h.wings_kind6 = s->hero.wings_slot;
    h.helper_type = s->hero.helper_type;
    h.helper_flies = s->hero.helper_flies;
    /* the request flag (+6): set by a request, cleared by the next test (here: when the answer is taken).  The
     * 3 s time (+8) is only set for the Lorencia <-> world 30 pair, its default lets every other request pass. */
    h.throttle = s->gate_sent || (s->gate_last_ms && (uint32_t)(now_ms - s->gate_last_ms) < 3000u);
    mu_gate_check(s->gates, s->ngates, gate_lookup, s, &h, out);
    s->loading_world = out->loading_world;
    if (out->refused == 1) {
        char buf[192];
        snprintf(buf, sizeof buf, "%s", mu_map_text(s, MU_GATE_TEXT_LEVEL));
        char *d = strstr(buf, "%d");
        if (d) {
            char tail[192];
            snprintf(tail, sizeof tail, "%s", d + 2);
            snprintf(d, sizeof buf - (size_t)(d - buf), "%d%s", (int)gate_lookup(s, out->gate)->min_level, tail);
        }
        snprintf(s->notice, sizeof s->notice, "%s", buf);
    } else if (out->refused == 2) {
        snprintf(s->notice, sizeof s->notice, "%s", mu_map_text(s, MU_GATE_TEXT_WINGS));
    }
    if (!out->packet_length)
        return 0;
    s->gate_sent = 1;   /* cleared when the teleport is taken (the client clears +6 on its next test) */
    if ((s->world == 0 || s->world == 0x1e) && out->helper_stop)
        s->gate_last_ms = now_ms ? now_ms : 1;
    const mu_gate *g = gate_lookup(s, out->gate);
    return g ? land_on_gate(s, g->target, (uint16_t)g->index) : 0;
}

/* ---- travel API ---------------------------------------------------------------------------------------------- */

void mu_map_step(mu_map_session *s)
{
    /* MoveHero 0x016a9150 counts LoadingWorld down once per logic step (the world render waits while >= 30) */
    if (s->loading_world > 0 && s->loading_world != 9999999)
        s->loading_world--;
}

int mu_map_teleport_packet(int32_t world, int32_t x, int32_t y, int32_t dir, uint16_t number, uint8_t *out, size_t cap)
{
    if (cap < 11)
        return 0;
    const uint8_t p[11] = {0xc3, 11, 0x1c, 0, (uint8_t)number, (uint8_t)(number >> 8), (uint8_t)world,
                           (uint8_t)(world >> 8), (uint8_t)x, (uint8_t)y, (uint8_t)dir};
    memcpy(out, p, sizeof p);
    return 11;
}

int mu_map_travel_to(mu_map_session *s, int32_t world, int32_t tile_x, int32_t tile_y)
{
    uint8_t p[16];
    mu_map_teleport_packet(world, tile_x, tile_y, 1, 1, p, sizeof p);
    mu_teleport_parse(p, 11, &s->teleport);
    s->pending = 1;
    snprintf(s->last, sizeof s->last, "travel world %d tile %d,%d", world, tile_x, tile_y);
    return 1;
}

int mu_map_travel_move(mu_map_session *s, int32_t key)
{
    return demo_move(s, key);
}

int mu_map_respawn(mu_map_session *s, int32_t world, int32_t *out_world, int32_t *tile_x, int32_t *tile_y)
{
    int32_t gate = world == 2 ? 22 : world == 3 ? 27 : world == 51 ? 267 : 17;   /* DEMO */
    if (!land_on_gate(s, gate, (uint16_t)gate))
        return 0;
    if (out_world)
        *out_world = s->teleport.world;
    if (tile_x)
        *tile_x = s->teleport.x;
    if (tile_y)
        *tile_y = s->teleport.y;
    snprintf(s->last, sizeof s->last, "respawn world %d tile %d,%d (gate %d)", (int)s->teleport.world,
             (int)s->teleport.x, (int)s->teleport.y, (int)gate);
    return 1;
}

int mu_map_take_teleport(mu_map_session *s, mu_teleport *out)
{
    if (!s->pending)
        return 0;
    *out = s->teleport;
    s->pending = 0;
    s->gate_sent = 0;
    s->loading_world = out->number ? MU_TELEPORT_LOADING_WORLD : 0;
    /* Number zero moves the hero without reading a new world into the client's globals. */
    if (!out->number)
        out->world = (uint16_t)s->world;
    s->world = out->world;
    s->tile_x = out->x;
    s->tile_y = out->y;
    return 1;
}
