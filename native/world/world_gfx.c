/* The GFx interface over mu-world's 3D view (NATIVE-GFX-002/003); see world_gfx.h. */
#include "world_gfx.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../core/mu_hud.h"
#include "../core/mu_hud_tip.h"
#include "../core/mu_lang.h"
#include "../core/mu_npc.h"
#include "../gfx/mu_gfx_layer.h"
#include "../gfx/mu_gfx_sdl.h"
#include "world_gfx_game.h"

struct world_gfx {
    mu_gfx_layer *layer;
    mu_hud_tip_tables tables;
    const char *root;
    mu_hud_inventory *scratch;
    wg_items *items;            /* item models over the windows and in the hotkey image (NATIVE-GFX-003) */
    double time_ms;
    int skills;
    /* NATIVE-NPC-001: the demo vault contents */
    mu_npc_item npc_storage[MU_NPC_ITEMS];
    int npc_storage_count;
};

/* GlobalText for the layer's labels: the tables read from the client
 * (NATIVE-LANG-001, MU_LANG_DIR). */
static const char *lang_text(void *user, int32_t index)
{
    return mu_lang_text(user, index);
}

/* The skill table the game sends to ASData (SkillInfo builder 0x00c5ebaa:
 * Index, Magic_Icon, Name, Delay, SkillUseType, MasteryType; records whose
 * first byte is set are skipped) from the client's Skill(Kor) table. */
static int lang_skills(const mu_lang *lang, mu_gfx_skill *out, int max)
{
    int n = 0;
    for (size_t i = 0; i < mu_lang_skill_count(lang) && n < max; i++) {
        const mu_lang_skill *s = mu_lang_skill_at(lang, i);
        if (s->skip)
            continue;
        mu_gfx_skill *k = &out[n++];
        memset(k, 0, sizeof *k);
        k->index = s->index;
        k->icon = s->icon;
        k->delay = s->delay;
        k->use_type = s->use_type;
        k->mastery = s->mastery;
        mu_lang_ascii(k->name, sizeof k->name, s->name);
    }
    return n;
}

/* The InfoPopup HTML of an item through the tooltip pipeline (core/mu_hud_tip). */
static int tooltip(void *user, int32_t code, int32_t level, char *html, size_t cap)
{
    world_gfx *g = user;
    if (!g->tables.have_tooltip || !g->scratch)
        return 1;
    mu_hud_inventory_init(g->scratch);
    int k = mu_hud_inventory_add(g->scratch, g->tables.have_items ? &g->tables.items : NULL, g->root, code, level, 1, 1);
    if (k < 0)
        return 1;
    const mu_gfx_hero *h = mu_gfx_layer_hero(g->layer);
    const int hero[4] = {h->strength, h->agility, h->energy, h->level + h->master_level};
    mu_hud_tip tip;
    mu_hud_tip_build(&g->tables, &g->scratch->items[k], hero, &tip);
    mu_hud_tip_html(&tip, html, cap);
    return 0;
}

/* NATIVE-NPC-001: a demo price from the item's Item.bmd value fields (+0x28c
 * fixed zen, else value * value * 10 / 12 from +0x288, NATIVE-DATA-002's
 * reading); the client's own price routine is not reconstructed.  Levels add
 * 50 % each (demo). */
static int64_t demo_price(void *user, int32_t code, int32_t level)
{
    world_gfx *g = user;
    int64_t base = 100;
    if (g->scratch && g->tables.have_items) {
        mu_hud_inventory_init(g->scratch);
        int k = mu_hud_inventory_add(g->scratch, &g->tables.items, g->root, code, level, 1, 1);
        if (k >= 0 && g->scratch->items[k].has_record) {
            const mu_item_attributes *r = &g->scratch->items[k].record.attributes;
            base = r->zen ? (int64_t)r->zen : (int64_t)r->value * r->value * 10 / 12;
            if (base < 10)
                base = 10;
        }
    }
    for (int32_t i = 0; i < level && i < 15; i++)
        base += base / 2;
    return base;
}

/* Name and size of an item code from Item.bmd (the inventory's source). */
static void item_info(world_gfx *g, int32_t code, int32_t level, mu_gfx_slot_item *out)
{
    memset(out, 0, sizeof *out);
    out->code = code;
    out->level = level;
    out->width = 1;
    out->height = 2;
    snprintf(out->name, sizeof out->name, "Item %d", (int)code);
    if (g->scratch && g->tables.have_items) {
        mu_hud_inventory_init(g->scratch);
        int k = mu_hud_inventory_add(g->scratch, &g->tables.items, g->root, code, level, 1, 2);
        if (k >= 0) {
            out->width = g->scratch->items[k].grid.width;
            out->height = g->scratch->items[k].grid.height;
            snprintf(out->name, sizeof out->name, "%s", g->scratch->items[k].name);
        }
    }
    out->price = demo_price(g, code, level);
}

/* Demo inventory (layer choice): a weapon, armour pieces, potions and a ring;
 * sizes and names from Item.bmd when the game root has it. */
static void demo_items(world_gfx *g)
{
    static const int32_t ITEMS[][2] = {{0 * 512 + 5, 9}, {7 * 512 + 1, 7}, {8 * 512 + 1, 11}, {9 * 512 + 1, 7},
                                       {14 * 512 + 3, 0}, {14 * 512 + 4, 0}, {6 * 512 + 2, 5}, {13 * 512 + 8, 0},
                                       {4 * 512 + 8, 0}};
    for (size_t i = 0; i < sizeof ITEMS / sizeof ITEMS[0]; i++) {
        int32_t code = ITEMS[i][0], level = ITEMS[i][1];
        uint8_t w = 1, h = 2;
        char name[96];
        snprintf(name, sizeof name, "Item %d", (int)code);
        if (g->scratch && g->tables.have_items) {
            mu_hud_inventory_init(g->scratch);
            int k = mu_hud_inventory_add(g->scratch, &g->tables.items, g->root, code, level, 1, 2);
            if (k >= 0) {
                w = g->scratch->items[k].grid.width;
                h = g->scratch->items[k].grid.height;
                snprintf(name, sizeof name, "%s", g->scratch->items[k].name);
            }
        }
        mu_gfx_layer_add_item(g->layer, code, level, w, h, name);
    }
}

world_gfx *world_gfx_open(const char *movie_dir, const char *game_root, int width, int height, double scale,
                          int shared, const char *open, char *error, size_t error_size)
{
    world_gfx *g = calloc(1, sizeof *g);
    if (!g) {
        snprintf(error, error_size, "out of memory");
        return NULL;
    }
    g->root = game_root;
    g->scratch = malloc(sizeof *g->scratch);
    mu_hud_tip_tables_load(game_root, &g->tables);
    g->items = game_root && !getenv("MU_GFX_NO_ITEM_MODELS") ? wg_items_open(game_root) : NULL;
    mu_gfx_layer_config cfg = {.movie_dir = movie_dir, .width = width, .height = height, .shared = shared, .demo = 1,
                               .tooltip = tooltip, .tooltip_user = g, .scale = scale,
                               .items = g->items ? wg_items_draw : NULL, .icons = g->items && !getenv("MU_GFX_NO_ICON_MODELS") ? wg_items_icons : NULL,
                               .items_user = g->items,
                               .double_buffer = !getenv("MU_GFX_SINGLE_BUFFER"),
                               .text = mu_lang_shared() ? lang_text : NULL, .text_user = (void *)mu_lang_shared(),
                               .price = demo_price};
    if (getenv("MU_GFX_LOG"))
        cfg.log = fopen(getenv("MU_GFX_LOG"), "w");
    g->layer = mu_gfx_layer_open(&cfg, error, error_size);
    if (!g->layer) {
        world_gfx_close(g);
        return NULL;
    }
    demo_items(g);
    mu_gfx_skill *skills = malloc(1024 * sizeof *skills);
    if (skills) {
        g->skills = mu_lang_skill_count(mu_lang_shared()) ? lang_skills(mu_lang_shared(), skills, 1024)
                                                          : wg_skills_load(game_root, skills, 1024);
        if (g->skills > 0)
            mu_gfx_layer_set_skills(g->layer, skills, g->skills);
        free(skills);
    }
    if (open) {
        if (strstr(open, "inventory"))
            mu_gfx_layer_show(g->layer, MU_GFX_INVENTORY, 1);
        if (strstr(open, "character"))
            mu_gfx_layer_show(g->layer, MU_GFX_CHARACTER, 1);
    }
    return g;
}

void world_gfx_close(world_gfx *g)
{
    if (!g)
        return;
    mu_gfx_layer_close(g->layer);
    wg_items_close(g->items);
    mu_hud_tip_tables_free(&g->tables);
    free(g->scratch);
    free(g);
}

int world_gfx_event(world_gfx *g, const SDL_Event *e, double scale)
{
    return g ? mu_gfx_sdl_event(g->layer, e, scale) : 0;
}

void world_gfx_frame(world_gfx *g, double dt_ms, int draw)
{
    if (!g)
        return;
    g->time_ms += dt_ms;
    wg_items_set_time(g->items, g->time_ms);
    mu_gfx_layer_advance(g->layer, dt_ms);
    if (draw)
        mu_gfx_layer_draw_gl(g->layer);
}

void world_gfx_set_location(world_gfx *g, int world, float x, float y)
{
    if (!g)
        return;
    /* The top menu's map name: the map-name function 0x016baaa6 over the
     * GlobalText read from the client (NATIVE-LANG-001); without the tables
     * the data folder's name stands in.  Cells are 100 world units. */
    char name[64];
    const char *map = mu_lang_map_name(mu_lang_shared(), world);
    if (map)
        mu_lang_ascii(name, sizeof name, map);
    else
        snprintf(name, sizeof name, "World %d", world + 1);
    mu_gfx_layer_set_location(g->layer, name, (int)(x / 100.0f), (int)(y / 100.0f));
}

void world_gfx_report(world_gfx *g, char *out, size_t cap)
{
    mu_gfx_layer_stats st;
    mu_gfx_layer_stats_get(g ? g->layer : NULL, &st);
    long renders = 0;
    for (int m = 0; m < MU_GFX_MOVIES; m++)
        renders += st.renders[m];
    long drawn = 0, missing = 0, icons = 0;
    wg_items_counts(g ? g->items : NULL, &drawn, &missing, &icons);
    snprintf(out, cap, "\"gfx\": {\"shared\": %d, \"renders\": %ld, \"callbacks\": %ld, \"invokes\": %ld, "
                       "\"inventory_open\": %d, \"tooltips\": %d, \"base_mode\": %d, \"skills\": %d, "
                       "\"item_models\": %ld, \"item_models_missing\": %ld, \"icon_models\": %ld}",
             st.shared, renders, st.callbacks, st.invokes, mu_gfx_layer_is_open(g ? g->layer : NULL, MU_GFX_INVENTORY),
             g && g->tables.have_tooltip, mu_gfx_layer_base_mode(g ? g->layer : NULL), g ? g->skills : 0, drawn,
             missing, icons);
}

/* NATIVE-NAMES-001: the layer, for the hudPlayerName game side (world_names_gfx.c). */
mu_gfx_layer *world_gfx_layer(world_gfx *g)
{
    return g ? g->layer : NULL;
}

/* ---- NPC windows (NATIVE-NPC-001) ---- */

static void npc_title(const mu_npc_open *o, const char *label, char *out, size_t cap)
{
    /* Npcname(kor): for npcdialogue the dialogue NPC the result names (0x00fdc96c(class) stores its name for
     * SetTitle, static), otherwise the clicked NPC's class */
    int32_t index = o->kind == MU_NPC_WINDOW_DIALOG && o->window.dialogue >= 0 ? o->window.dialogue : o->server_class;
    const mu_lang_npc *npc = mu_lang_npc_get(mu_lang_shared(), index);
    if (npc && npc->name && npc->name[0])
        mu_lang_ascii(out, cap, npc->name);
    else
        snprintf(out, cap, "%s", label && label[0] ? label : "NPC");
}

void world_gfx_npc_open(world_gfx *g, const mu_npc_open *o, const char *label)
{
    if (!g || !o)
        return;
    char title[96];
    npc_title(o, label, title, sizeof title);
    const mu_npc_demo_row *row = o->demo;
    if (o->kind == MU_NPC_WINDOW_DIALOG) {
        static char text[4096], options[13][96];
        mu_gfx_npc_dialog d;
        memset(&d, 0, sizeof d);
        d.title = title;
        size_t n = 0;
        text[0] = 0;
        for (int i = 0; row && i < row->dialog_count && n < sizeof text; i++) {
            const char *line = mu_lang_dialog(mu_lang_shared(), row->dialog[i]);
            char clean[2048];
            if (line)
                mu_lang_ascii(clean, sizeof clean, line);
            else
                snprintf(clean, sizeof clean, "Dialog %d", (int)row->dialog[i]);
            n += (size_t)snprintf(text + n, sizeof text - n, "%s%s", n ? ";" : "", clean);   /* the client's line separator */
        }
        if (!text[0])
            snprintf(text, sizeof text, "(demo dialogue)");
        d.text = text;
        for (int i = 0; row && i < row->option_count && i < 13; i++) {
            const char *line = mu_lang_dialog(mu_lang_shared(), row->options[i]);
            if (line)
                mu_lang_ascii(options[i], sizeof options[i], line);
            else
                snprintf(options[i], sizeof options[i], "Dialog %d", (int)row->options[i]);
            d.options[d.noptions++] = options[i];
        }
        if (!d.noptions) {
            snprintf(options[0], sizeof options[0], "Close");
            d.options[d.noptions++] = options[0];
        }
        d.hide_contribute = o->window.dialogue == 0x248 || o->window.dialogue == 0x2fc || o->window.dialogue == 0x2fd ||
                       o->window.dialogue == 0x3ab || o->window.dialogue == 0x3ac;
        mu_gfx_layer_npc_dialog(g->layer, &d);
    } else if (o->kind == MU_NPC_WINDOW_SHOP) {
        static mu_gfx_slot_item items[MU_NPC_ITEMS];
        int n = 0;
        for (int i = 0; row && i < row->shop_count && n < MU_NPC_ITEMS; i++)
            item_info(g, row->shop[i].code, row->shop[i].level, &items[n++]);
        mu_gfx_layer_npc_shop(g->layer, title, o->repair, o->shop_tabs, items, n);
    } else if (o->kind == MU_NPC_WINDOW_STORAGE) {
        static mu_gfx_slot_item items[MU_NPC_ITEMS];
        int n = 0;
        for (int i = 0; i < g->npc_storage_count && n < MU_NPC_ITEMS; i++)
            item_info(g, g->npc_storage[i].code, g->npc_storage[i].level, &items[n++]);
        mu_gfx_layer_storage(g->layer, "Vault", items, n);
    }
}

void world_gfx_npc_close_all(world_gfx *g)
{
    if (g)
        mu_gfx_layer_npc_close(g->layer);
}

int world_gfx_npc_window(world_gfx *g)
{
    return g ? mu_gfx_layer_npc_window(g->layer) >= 0 : 0;
}

int world_gfx_npc_action(world_gfx *g, const char *verb, const char *arg)
{
    return g ? mu_gfx_layer_npc_action(g->layer, verb, arg ? atoi(arg) : 0) : 0;
}

const char *world_gfx_npc_last(world_gfx *g)
{
    return g ? mu_gfx_layer_npc_last(g->layer) : "";
}

void world_gfx_npc_storage(world_gfx *g, const mu_npc_item *items, int n)
{
    if (!g)
        return;
    g->npc_storage_count = n > MU_NPC_ITEMS ? MU_NPC_ITEMS : n;
    memcpy(g->npc_storage, items, (size_t)g->npc_storage_count * sizeof *items);
}
