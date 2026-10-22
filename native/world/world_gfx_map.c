/* The map overlay (hudMap) and the Move window (MoveCommand) over the GFx layer (NATIVE-MAP-001).
 * See world_gfx_map.h. */
#include "world_gfx_map.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../core/mu_lang.h"
#include "../gfx/mu_gfx_layer.h"

struct world_gfx_map {
    mu_gfx_layer *layer;
    mu_map_session *s;
    const char *root;
    int hud_inited;
    int32_t map_world;          /* world whose image and units the movie holds (-1: none) */
    char hud_path[160];
    int move_inited;
    char last[192];
};

static void jstr(char *out, size_t cap, const char *s)
{
    size_t n = 0;
    if (cap < 3)
        return;
    out[n++] = '"';
    for (; s && *s && n + 7 < cap; s++) {
        unsigned char c = (unsigned char)*s;
        if (c == '"' || c == '\\') {
            out[n++] = '\\';
            out[n++] = (char)c;
        } else if (c < 0x20 || c >= 0x7f) {
            n += (size_t)snprintf(out + n, cap - n, "\\u%04x", c < 0x20 ? c : '?');
        } else {
            out[n++] = (char)c;
        }
    }
    out[n++] = '"';
    out[n] = 0;
}

static const char *gt(world_gfx_map *m, int32_t index)
{
    return mu_map_text(m->s, index);
}

static void notice(world_gfx_map *m, const char *text)
{
    if (text && text[0])
        mu_gfx_layer_chat(m->layer, 3, "", text);   /* the client's chat notice (system line) */
}

/* ---- hudMap ------------------------------------------------------------------------------------------------ */

static void hud_init(world_gfx_map *m)
{
    /* the window's OnLoad 0x00c6b89f: InitData{MaxPartyCount 5, the key help texts} */
    char buf[2048], q[256];
    size_t n = (size_t)snprintf(buf, sizeof buf, "[{\"MaxPartyCount\":%d", MU_MAP_MAX_PARTY);
    for (int i = 0; i < 10 && n < sizeof buf; i++) {
        jstr(q, sizeof q, gt(m, mu_map_init_text[i]));
        n += (size_t)snprintf(buf + n, sizeof buf - n, ",\"%s\":%s", mu_map_init_members[i], q);
    }
    snprintf(buf + n, sizeof buf - n, "}]");
    mu_gfx_layer_invoke(m->layer, MU_GFX_MAIN, m->hud_path, "InitData", buf);
    m->hud_inited = 1;
}

static void hud_load_world(world_gfx_map *m)
{
    /* LoadWorldMap 0x00c6b116 (the world image) and the server's units (0xE7 records) */
    char name[64], buf[1024], q[160];
    m->map_world = m->s->world;
    mu_gfx_layer_invoke(m->layer, MU_GFX_MAIN, m->hud_path, "ClearWorldMap", "[]");
    if (!mu_map_session_load_map(m->s, m->root, name, sizeof name))
        return;
    jstr(q, sizeof q, name);
    snprintf(buf, sizeof buf, "[{\"fileName\":%s}]", q);
    mu_gfx_layer_invoke(m->layer, MU_GFX_MAIN, m->hud_path, "LoadWorldMap", buf);
    if (m->s->hud.shown)
        mu_gfx_layer_invoke(m->layer, MU_GFX_MAIN, m->hud_path, "setShowMap", "[true]");
}

static void hud_units(world_gfx_map *m)
{
    char buf[512], q[160];
    mu_gfx_layer_invoke(m->layer, MU_GFX_MAIN, m->hud_path, "delAllUnit", "[]");
    for (int i = 0; i < m->s->nunits; i++) {
        const mu_map_unit *u = &m->s->units[i];
        jstr(q, sizeof q, u->text);
        snprintf(buf, sizeof buf, "[{\"type\":%d,\"key\":%d,\"state\":%d,\"text\":%s,\"x\":%.9g,\"y\":%.9g}]", u->type,
                 u->key, u->state, q, (double)u->x, (double)u->y);
        mu_gfx_layer_invoke(m->layer, MU_GFX_MAIN, m->hud_path, "addUnit", buf);
    }
    m->s->units_dirty = 0;
}

static void show(world_gfx_map *m, int b)
{
    mu_map_show_result r;
    mu_map_toggle(m->s, b, &r);
    if (r.notice)
        notice(m, m->s->notice);
    if (r.set_show) {
        mu_gfx_layer_invoke(m->layer, MU_GFX_MAIN, m->hud_path, "setShowMap", r.shown ? "[true]" : "[false]");
        /* C1 E7 01: the server answers with the world's units (the demo sends them again) */
        if (r.shown) {
            mu_map_demo_units(m->s);
            hud_units(m);
        }
    }
    snprintf(m->last, sizeof m->last, "map %s%s", r.set_show ? (r.shown ? "shown" : "hidden") : "unchanged",
             r.notice ? " (notice)" : "");
}

static void channel(void *user, const char *name, const char *args)
{
    world_gfx_map *m = user;
    if (strcmp(name, "hudMap"))
        return;
    if (strstr(args, "\"showMap\"")) {   /* ["showMap", true|false] */
        const char *comma = strchr(args, ',');
        show(m, comma && strstr(comma, "true") != NULL);
    }
}

/* ---- Move window ------------------------------------------------------------------------------------------- */

static const struct { const char *member; int32_t text; } MOVE_TEXT[] = {
    /* the window's OnLoad (static reading of 0x00bdb5d5..0x00bdb765): InitFixtedText */
    {"mainTitle", 0x3a5}, {"strife", 0xbac}, {"mapName", 0x3a6}, {"limitLv", 0x3a7}, {"reqZen", 0x3a8},
    {"favorite", 0x1426}, {"favoriteTitle", 0x1442}, {"showMap", 0xd66}, {"close", 0x3ea}, {"sortOrder", 0x14dd},
    {"sortDifficult", 0x14de}, {"sortName", 0x14df},
};

static void move_init(world_gfx_map *m)
{
    const char *path = mu_gfx_layer_path(m->layer, MU_GFX_MOVE_COMMAND);
    char buf[4096], q[256];
    size_t n = (size_t)snprintf(buf, sizeof buf, "[{");
    for (size_t i = 0; i < sizeof MOVE_TEXT / sizeof MOVE_TEXT[0]; i++) {
        jstr(q, sizeof q, gt(m, MOVE_TEXT[i].text));
        n += (size_t)snprintf(buf + n, sizeof buf - n, "%s\"%s\":%s", i ? "," : "", MOVE_TEXT[i].member, q);
    }
    snprintf(buf + n, sizeof buf - n, "}]");
    mu_gfx_layer_invoke(m->layer, MU_GFX_MOVE_COMMAND, path, "InitFixtedText", buf);
    mu_gfx_layer_invoke(m->layer, MU_GFX_MOVE_COMMAND, path, "ClearMapInfo", "[]");
    m->move_inited = 1;
}

static void move_list(world_gfx_map *m)
{
    /* the list builder 0x00bdd08d: SetMoveMapList, ClearFavorMap, AddMoveMapDataByMapIndex per favourite */
    const char *path = mu_gfx_layer_path(m->layer, MU_GFX_MOVE_COMMAND);
    static mu_move_row rows[MU_MAP_MOVES_MAX];
    int n = mu_map_move_rows(m->s, rows, MU_MAP_MOVES_MAX);
    size_t cap = 256 + (size_t)n * 512, k = 0;
    char *buf = malloc(cap), q[4][160];
    if (!buf)
        return;
    k += (size_t)snprintf(buf + k, cap - k, "[[");
    for (int i = 0; i < n; i++) {
        jstr(q[0], sizeof q[0], rows[i].strife);
        jstr(q[1], sizeof q[1], rows[i].map);
        k += (size_t)snprintf(buf + k, cap - k,
                              "%s{\"orderIdx\":\"%d\",\"strStrife\":%s,\"strMap\":%s,\"strLv\":\"%s\",\"strZen\":\"%s\","
                              "\"btnChecked\":%s,\"bDisabled\":%d,\"mapIdx\":%d,\"btnVisible\":true}",
                              i ? "," : "", rows[i].order_idx, q[0], q[1], rows[i].level, rows[i].zen,
                              rows[i].checked ? "true" : "false", rows[i].disabled, rows[i].map_idx);
    }
    snprintf(buf + k, cap - k, "]]");
    mu_gfx_layer_invoke(m->layer, MU_GFX_MOVE_COMMAND, path, "SetMoveMapList", buf);
    free(buf);
    mu_gfx_layer_invoke(m->layer, MU_GFX_MOVE_COMMAND, path, "ClearFavorMap", "[]");
    for (int i = 0; i < 5; i++)
        if (m->s->favourites[i].flag != 0xffff) {
            char a[32];
            snprintf(a, sizeof a, "[\"%d\"]", m->s->favourites[i].key);
            mu_gfx_layer_invoke(m->layer, MU_GFX_MOVE_COMMAND, path, "AddMoveMapDataByMapIndex", a);
        }
    char order[16];
    snprintf(order, sizeof order, "[%d]", m->s->sort_order);
    mu_gfx_layer_invoke(m->layer, MU_GFX_MOVE_COMMAND, path, "SetMenuSortOrder", order);
}

static void move_show(world_gfx_map *m, int open)
{
    if (!mu_gfx_layer_path(m->layer, MU_GFX_MOVE_COMMAND)[0])
        return;
    if (open) {
        if (!m->move_inited)
            move_init(m);
        move_list(m);
    }
    m->s->move_open = open;
    mu_gfx_layer_show(m->layer, MU_GFX_MOVE_COMMAND, open);
}

static int first_number(const char *args)
{
    const char *p = args;
    while (*p && !(*p == '-' || (*p >= '0' && *p <= '9')))
        p++;
    return atoi(p);
}

int world_gfx_map_click(world_gfx_map *m, int index)
{
    mu_move_click_result r;
    int travel = mu_map_move_click(m->s, index, &r);
    snprintf(m->last, sizeof m->last, "move click %d: %s", index, m->s->last);
    if (r.accepted)
        move_show(m, 0);
    return travel;
}

static void window(void *user, int movie, const char *name, const char *args)
{
    world_gfx_map *m = user;
    if (movie != MU_GFX_MOVE_COMMAND)
        return;
    if (!strcmp(name, "UIInit"))
        move_init(m);
    else if (!strcmp(name, "CloseWindow") || !strcmp(name, "onCloseBtnClick"))
        move_show(m, 0);
    else if (!strcmp(name, "ScrollListChange"))
        world_gfx_map_click(m, first_number(args));
    else if (!strcmp(name, "SortMapList")) {
        mu_map_move_sort(m->s, first_number(args));
        move_list(m);
    } else if (!strcmp(name, "onClickbtnShowMap")) {
        /* the client: hudMap's onShowMap(true) through its window (0x00bdeadf -> 0x00c6b2b0) */
        mu_gfx_layer_invoke(m->layer, MU_GFX_MAIN, m->hud_path, "onShowMap", "[true]");
    } else if (!strcmp(name, "AddFavoriteMap")) {
        int i = first_number(args);
        for (int k = 0; i >= 0 && i < m->s->nentries && k < 5; k++)
            if (m->s->favourites[k].flag == 0xffff) {
                m->s->favourites[k].flag = 0;
                m->s->favourites[k].key = (uint16_t)m->s->entries[i].key2;
                break;
            }
    } else if (!strcmp(name, "DeleteFavoriteMap")) {
        int i = first_number(args), seen = 0;
        for (int k = 0; k < 5; k++)
            if (m->s->favourites[k].flag != 0xffff && seen++ == i) {
                m->s->favourites[k].flag = m->s->favourites[k].key = 0xffff;
                break;
            }
    } else if (!strcmp(name, "FavoriteListFull")) {
        notice(m, gt(m, 0x1427));
    }
}

static int key(void *user, int vk)
{
    world_gfx_map *m = user;
    if (vk == 'M') {          /* layer choice, as the other window hotkeys: the client's key scan is not reconstructed */
        move_show(m, !m->s->move_open);
        return 1;
    }
    if (vk == 27 && m->s->move_open) {
        move_show(m, 0);
        return 1;
    }
    return 0;
}

/* ---- public ------------------------------------------------------------------------------------------------ */

world_gfx_map *world_gfx_map_open(struct mu_gfx_layer *layer, mu_map_session *s, const char *game_root)
{
    if (!layer || !s)
        return NULL;
    world_gfx_map *m = calloc(1, sizeof *m);
    if (!m)
        return NULL;
    m->layer = layer;
    m->s = s;
    m->root = game_root;
    m->map_world = -1;
    mu_gfx_map_hooks hooks = {m, channel, window, key};
    mu_gfx_layer_set_map_hooks(layer, &hooks);
    return m;
}

void world_gfx_map_close(world_gfx_map *m)
{
    if (!m)
        return;
    mu_gfx_layer_set_map_hooks(m->layer, NULL);
    free(m);
}

void world_gfx_map_frame(world_gfx_map *m, const float hero_pos[2], float hero_angle_z)
{
    if (!m)
        return;
    const char *path = mu_gfx_layer_channel_path(m->layer, "hudMap");
    if (!path || !path[0])
        return;
    if (strcmp(path, m->hud_path)) {   /* (re)loaded movie */
        snprintf(m->hud_path, sizeof m->hud_path, "%s", path);
        m->hud_inited = 0;
        m->map_world = -1;
    }
    if (!m->hud_inited)
        hud_init(m);
    if (m->map_world != m->s->world) {
        hud_load_world(m);
        if (m->s->hud.shown) {
            mu_map_demo_units(m->s);
            hud_units(m);
        }
    }
    mu_map_hud_frame f;
    mu_map_hud_update(&m->s->hud, 1, 1, hero_pos, hero_angle_z, &f);
    char p[256], v[64];
    if (f.set_rotation) {   /* the hero marker (baseMovie's hero = hudMap._hero) */
        snprintf(p, sizeof p, "%s._hero._rotation", m->hud_path);
        snprintf(v, sizeof v, "%.17g", f.rotation);
        mu_gfx_layer_set_variable(m->layer, MU_GFX_MAIN, p, v);
    }
    if (f.set_position) {   /* the map (baseMovie's map = mcWideScale.mcRot._map) */
        snprintf(p, sizeof p, "%s.mcWideScale.mcRot._map._x", m->hud_path);
        snprintf(v, sizeof v, "%.17g", f.map_x);
        mu_gfx_layer_set_variable(m->layer, MU_GFX_MAIN, p, v);
        snprintf(p, sizeof p, "%s.mcWideScale.mcRot._map._y", m->hud_path);
        snprintf(v, sizeof v, "%.17g", f.map_y);
        mu_gfx_layer_set_variable(m->layer, MU_GFX_MAIN, p, v);
    }
}

int world_gfx_map_action(world_gfx_map *m, const char *verb, int arg)
{
    if (!m)
        return 0;
    if (!strcmp(verb, "tab")) {   /* the movie's Tab: onShowMap(!shown) -> showMap */
        show(m, !m->s->hud.shown);
        return 1;
    }
    if (!strcmp(verb, "move")) {
        move_show(m, !m->s->move_open);
        return 1;
    }
    if (!strcmp(verb, "sort")) {
        mu_map_move_sort(m->s, arg);
        if (m->s->move_open)
            move_list(m);
        return 1;
    }
    if (!strcmp(verb, "click"))
        return world_gfx_map_click(m, arg);
    return 0;
}

const char *world_gfx_map_last(const world_gfx_map *m)
{
    return m ? m->last : "";
}
