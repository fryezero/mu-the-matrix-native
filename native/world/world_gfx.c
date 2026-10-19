/* The GFx interface over mu-world's 3D view (NATIVE-GFX-002/003); see world_gfx.h. */
#include "world_gfx.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../core/mu_hud.h"
#include "../core/mu_hud_tip.h"
#include "../core/mu_lang.h"
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
                               .text = mu_lang_shared() ? lang_text : NULL, .text_user = (void *)mu_lang_shared()};
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
