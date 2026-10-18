#ifndef MU_HUD_H
#define MU_HUD_H

/* Native in-game interface pieces (NATIVE-HUD-001).
 *
 * The client's in-game windows are GFx (Scaleform) movies; their frames are
 * not reconstructed.  This module runs the reconstructed game side
 * (reconstructed/hud) for an inventory: the item grid, the slot pass and
 * RenderItem3D's general path, which give each item's model, position,
 * rotation and scale for the orthographic item pass, and the tooltip text
 * pipeline (formatter cases, HTML assembly).
 *
 * Inputs that come from places outside the restored code are explicit:
 *   - item render info (translate/rotate/scale) from Data/Local/itemtrsdata.bmd
 *     (counted 32-byte records, each its own decode unit; the client's loader
 *     is not in the restored text).  Record = u32 code + 7 floats; the second
 *     float pair are the slot offset factors, floats 4..6 the rotation and
 *     float 7 the scale (the constant third float, 2000, is dropped).  This
 *     mapping is an inference from the editor's save routine 0x0112052f and
 *     the value ranges.  The scale used is that float times an authored
 *     calibration factor (default 200): the client's own special cases and
 *     default record use 0.2 .. 0.6, the file 0.001 .. 0.004;
 *   - the GFx movie's slot geometry (requestSlotInfo) and window position,
 *     measured from a live window capture at 1722 x 1048.
 */

#include <stdint.h>

#include "mu_data.h"
#include "../../reconstructed/hud/inv_grid.h"
#include "../../reconstructed/hud/item_slots.h"

typedef struct mu_hud_trs_table {
    int32_t count;
    uint32_t *codes;
    float (*values)[7];
} mu_hud_trs_table;

/* Load itemtrsdata.bmd. Returns 0, -1 when unreadable, -2 when malformed. */
int mu_hud_trs_load(const char *path, mu_hud_trs_table *table);
void mu_hud_trs_free(mu_hud_trs_table *table);
/* Render info for `code` (first record with the code); the client's default
 * record (0x008dcce0: offsets 0.5/0.5, rotation -90,0,0, scale 0.55) when absent
 * or when table is NULL.  Returns 1 when a record was found. */
int mu_hud_trs_find(const mu_hud_trs_table *table, int32_t code, float scale_factor, mu_item_trs *out);

enum { MU_HUD_MAX_ITEMS = 64 };

typedef struct mu_hud_item {
    int32_t code, level;
    uint8_t excellent;
    uint8_t durability;
    char name[65];
    char model_path[1024];      /* resolved model file, "" when unknown */
    int has_record;
    mu_item record;
    mu_grid_item grid;
} mu_hud_item;

typedef struct mu_hud_inventory {
    mu_grid grid;
    mu_hud_item items[MU_HUD_MAX_ITEMS];
    int32_t count;
} mu_hud_inventory;

/* An 8 x 8 inventory page (0x00ab7277(1, 8, 8, 1)). */
void mu_hud_inventory_init(mu_hud_inventory *inv);
/* Adds an item at the first free place (0x00ad49fb); size from Item.bmd
 * when items/game_root are given, else w x h.  Returns the item index or
 * -1 when it does not fit. */
int mu_hud_inventory_add(mu_hud_inventory *inv, const mu_data_table *items, const char *game_root, int32_t code,
                         int32_t level, uint8_t w, uint8_t h);

/* Geometry of the GFx inventory window in screen pixels (inputs). */
typedef struct mu_hud_window_geometry {
    int32_t align;              /* movie view alignment */
    float movie_x, movie_y;     /* +0x70, +0x74 (1024 x 768 design space) */
    float slot_x, slot_y, cell_w, cell_h, gap_x, gap_y;   /* requestSlotInfo */
    float scale, alpha;
} mu_hud_window_geometry;

/* The values measured from the live capture (1722 x 1048 window, right-aligned). */
mu_hud_window_geometry mu_hud_inventory_geometry_live(void);

/* One item of the pass: slot call, RenderItem3D outcome and its outputs. */
typedef struct mu_hud_item_draw {
    int32_t item;               /* index into inv->items */
    mu_slot_call slot;
    int status;                 /* MU_ITEM3D_* */
    mu_item3d_out out;
    float cell_rect[4];         /* x, y, w, h of the item's cells, window pixels, origin top left */
} mu_hud_item_draw;

/* Runs the slot pass and RenderItem3D for every item; returns the count. */
int32_t mu_hud_inventory_pass(const mu_hud_inventory *inv, const mu_hud_window_geometry *geo, int32_t screen_w,
                              int32_t screen_h, const mu_hud_trs_table *trs, float scale_factor,
                              int32_t hover_item, mu_hud_item_draw *draws, int32_t max);

/* Column-major glOrtho(0, W, 0, H, 20, 2000) of the item pass 0x00abfcca. */
void mu_hud_item_projection(int32_t screen_w, int32_t screen_h, float m[16]);

#endif
