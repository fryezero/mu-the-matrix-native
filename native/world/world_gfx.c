/* The GFx interface over mu-world's 3D view (NATIVE-GFX-002); see world_gfx.h. */
#include "world_gfx.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../core/mu_hud.h"
#include "../core/mu_hud_tip.h"
#include "../gfx/mu_gfx_layer.h"
#include "../gfx/mu_gfx_sdl.h"

struct world_gfx {
    mu_gfx_layer *layer;
    mu_hud_tip_tables tables;
    const char *root;
    mu_hud_inventory *scratch;
};

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
    mu_gfx_layer_config cfg = {movie_dir, NULL, width, height, shared, 0, 1, tooltip, g, NULL, scale};
    if (getenv("MU_GFX_LOG"))
        cfg.log = fopen(getenv("MU_GFX_LOG"), "w");
    g->layer = mu_gfx_layer_open(&cfg, error, error_size);
    if (!g->layer) {
        world_gfx_close(g);
        return NULL;
    }
    demo_items(g);
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
    mu_gfx_layer_advance(g->layer, dt_ms);
    if (draw)
        mu_gfx_layer_draw_gl(g->layer);
}

void world_gfx_report(world_gfx *g, char *out, size_t cap)
{
    mu_gfx_layer_stats st;
    mu_gfx_layer_stats_get(g ? g->layer : NULL, &st);
    long renders = 0;
    for (int m = 0; m < MU_GFX_MOVIES; m++)
        renders += st.renders[m];
    snprintf(out, cap, "\"gfx\": {\"shared\": %d, \"renders\": %ld, \"callbacks\": %ld, \"invokes\": %ld, "
                       "\"inventory_open\": %d, \"tooltips\": %d}",
             st.shared, renders, st.callbacks, st.invokes, mu_gfx_layer_is_open(g ? g->layer : NULL, MU_GFX_INVENTORY),
             g && g->tables.have_tooltip);
}
