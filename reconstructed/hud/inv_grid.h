/* Reconstructed item grid of the pinned client's GFx item windows (NATIVE-HUD-001).
 *
 * In this client the inventory, the extension bags, the warehouse, the shops
 * and the mix windows are GFx (Scaleform) movies.  The movie only draws the
 * frame; the game keeps the item placement in a small grid object (0x4c bytes,
 * constructor 0x00ad322b) per page.  The inventory has one 8 x 8 page
 * (0x00ab7277(type 1, 8, 8, 1) in the GFx registry 0x00ac4a79), the extension
 * bags two 8 x 4 pages.
 *
 * The client object layout (thiscall methods on it):
 *
 *   +0x00 u32   0xff (constructor)            +0x2c i32  columns
 *   +0x04       sub-object (0x0095e383)       +0x30 i32  rows
 *   +0x0c ptr   owner frame                   +0x34 i32  page index
 *   +0x10       std::vector<item*> items      +0x38 i32* cell array, columns*rows words
 *   +0x1c i32   x                             +0x3c i32  (-1 after reset)
 *   +0x20 i32   y                             +0x40 u8   flag
 *   +0x24 i32   pixel width  (columns*26)     +0x44 i32  grid type (1 inventory, 2 bag, 0xc ...)
 *   +0x28 i32   pixel height (rows*26)        +0x48 u8, +0x49 u8 flags (0, 1 after reset)
 *
 * A cell holds the id word (+0x64) of the item covering it, 0 when free.  An
 * item object's top-left cell is (+0x69 column, +0x6a row); its size is the
 * Item.bmd record's width/height (+0x25a/+0x25b, NATIVE-DATA-002).
 *
 * Every function names the client routine it restates.  Client quirks are
 * kept: the fit test checks only the linear cell index, so a wide item may
 * wrap into the next row; pixel-to-cell divides by 20 although the extent is
 * 26 pixels per cell.
 */
#ifndef MU_HUD_INV_GRID_H
#define MU_HUD_INV_GRID_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define MU_GRID_MAX_ITEMS 256
#define MU_GRID_MAX_CELLS 1024

typedef struct mu_grid_item {
    uint32_t id;          /* +0x64: word stored in the cells */
    int32_t code;         /* +0x10: item code, -1 = none */
    uint8_t col, row;     /* +0x69, +0x6a */
    uint8_t width, height;/* Item.bmd +0x25a, +0x25b */
} mu_grid_item;

/* Events the grid raises towards the rest of the client (not reconstructed). */
enum {
    MU_GRID_EV_STATUS = 1,   /* 0x00c94193(item, grid type, -1): item status refresh */
    MU_GRID_EV_REFRESH = 2,  /* 0x00ad86dc(grid): push the page to the GFx movie */
    MU_GRID_EV_LASTPAGE = 3  /* type 0xc only: owner page count check, 0x00adaccf/0x00c06911 */
};
typedef void (*mu_grid_event)(void *user, int event, const mu_grid_item *item);

typedef struct mu_grid {
    uint32_t field_00;              /* 0xff */
    uint32_t owner;                 /* +0x0c (opaque word) */
    int32_t x, y;                   /* +0x1c, +0x20 */
    int32_t pixel_w, pixel_h;       /* +0x24, +0x28 */
    int32_t cols, rows;             /* +0x2c, +0x30 */
    int32_t page;                   /* +0x34 */
    int32_t has_cells;              /* +0x38 != 0 */
    int32_t field_3c;               /* +0x3c */
    uint8_t flag_40;                /* +0x40 */
    int32_t type;                   /* +0x44 */
    uint8_t flag_48, flag_49;       /* +0x48, +0x49 */
    uint32_t cells[MU_GRID_MAX_CELLS];
    mu_grid_item *items[MU_GRID_MAX_ITEMS];  /* the vector at +0x10, in order */
    int32_t item_count;
    int32_t owner_pages;            /* type 0xc: the owner's page count (0x00adaccf) */
    int overflow;                   /* a fill or a remembered cell fell outside (authored report) */
    mu_grid_event event;
    void *user;
} mu_grid;

/* Constructor 0x00ad322b (with reset 0x00ad32d7). */
void mu_grid_construct(mu_grid *g);
/* 0x00ad32d7: clear the scalar fields (+0x0c..+0x49). */
void mu_grid_reset(mu_grid *g);
/* 0x00ad341d(type, owner, x, y, cols, rows, page): fails (0) when a cell
 * array exists or the item vector is not empty.  The client allocates the
 * cell array with new[] and zeroes it; here cols*rows must fit
 * MU_GRID_MAX_CELLS (returns 0 otherwise, an authored limit). */
int mu_grid_init(mu_grid *g, int32_t type, uint32_t owner, int32_t x, int32_t y, int32_t cols, int32_t rows,
                 int32_t page);

/* 0x00ad4e69(index, w, h): every cell index + r*cols + c (r < h, c < w) is
 * below cols*rows and free.  No column-edge test. */
int mu_grid_fits_index(const mu_grid *g, int32_t index, int32_t w, int32_t h);
/* 0x00ad4ee4(col, row, w, h) = fits_index(row*cols + col, w, h). */
int mu_grid_fits(const mu_grid *g, int32_t col, int32_t row, int32_t w, int32_t h);
/* 0x00ad4ff4(col, row, item): 0 for a null item, else fits with the item's size. */
int mu_grid_item_fits(const mu_grid *g, int32_t col, int32_t row, const mu_grid_item *item);
/* 0x00ad49fb(w, h, &col, &row): first (row-major) position where fits() holds. */
int mu_grid_find_free(const mu_grid *g, int32_t w, int32_t h, int32_t *col, int32_t *row);
/* 0x00ad4994(w, h): first index where fits_index() holds and index%cols < cols-(w-1); -1 if none. */
int32_t mu_grid_find_free_index(const mu_grid *g, int32_t w, int32_t h);
/* 0x00ad4a6d: number of free cells. */
int32_t mu_grid_count_empty(const mu_grid *g);
/* 0x00ad4ad9(w, h, limit): greedy count of w x h placements (stops at limit),
 * remembering up to 128 taken cells; returns the count.  The client writes
 * past its 128-entry stack list for larger counts; here those cells are
 * ignored and *overflow is set (authored). */
int32_t mu_grid_count_fits(const mu_grid *g, int32_t w, int32_t h, int32_t limit, int *overflow);

/* 0x00ad4cb1: (x, y, x + pixel_w, y + pixel_h). */
void mu_grid_rect(const mu_grid *g, int32_t rect[4]);
/* 0x00ad4f11(px, py): x <= px < right and y <= py < bottom. */
int mu_grid_pt_in(const mu_grid *g, int32_t px, int32_t py);
/* 0x00ad4f51(rect): rect inside the grid rectangle (edges inclusive). */
int mu_grid_rect_in(const mu_grid *g, const int32_t rect[4]);
/* 0x00ad4d43(px, py, &col, &row): (px - x)/20, (py - y)/20 inside the rectangle. */
int mu_grid_pixel_cell(const mu_grid *g, int32_t px, int32_t py, int32_t *col, int32_t *row);
/* 0x00ad4da5(px, py): row*cols + col, or -1. */
int32_t mu_grid_pixel_index(const mu_grid *g, int32_t px, int32_t py);
/* 0x00ad5037(px, py, item): 0 for a null item or a pixel outside, else item_fits. */
int mu_grid_item_fits_pixel(const mu_grid *g, int32_t px, int32_t py, const mu_grid_item *item);
/* 0x00ad4c51 / 0x00ad4cf6 */
void mu_grid_set_position(mu_grid *g, int32_t x, int32_t y);
void mu_grid_set_pixel_size(mu_grid *g, int32_t w, int32_t h);

/* 0x00ad37c9(col, row, item): bounds check, set the item's cell, fill its
 * cells with the id, append it, raise STATUS and REFRESH (and LASTPAGE for
 * type 0xc when owner_pages - 1 == page).  Returns 0 without changes for a
 * null item or a cell outside; the cells are not tested for being free.  A
 * fill past the cell array (the client writes past its heap block) is
 * skipped and sets overflow.  Fails (0) when the authored capacity
 * MU_GRID_MAX_ITEMS is reached. */
int mu_grid_place(mu_grid *g, int32_t col, int32_t row, mu_grid_item *item);
/* 0x00ad3775(index, item) = place(index % cols, index / cols, item); 0 for an index outside. */
int mu_grid_place_index(mu_grid *g, int32_t index, mu_grid_item *item);
/* 0x00ad3a4e(item): erase the first vector entry equal to item and clear its
 * cells; REFRESH (and LASTPAGE) is raised even when the item is absent. */
void mu_grid_remove(mu_grid *g, const mu_grid_item *item);
/* 0x00ad403c(id): first item whose id equals id, else NULL. */
mu_grid_item *mu_grid_find_id(const mu_grid *g, uint32_t id);
/* 0x00ad3fd9(index): find_id(cells[index]); NULL for an index outside.  A
 * free cell (0) finds an item whose id is 0, if any. */
mu_grid_item *mu_grid_item_at(const mu_grid *g, int32_t index);
/* 0x00ad3c57(code): an item with this code (16-bit sign-extended compare). */
int mu_grid_has_code(const mu_grid *g, int16_t code);
/* 0x00ad47f1(w, h, index): free the cell at index alone, test find_free_index(w, h) != -1, restore. */
int mu_grid_can_move(mu_grid *g, int32_t w, int32_t h, int32_t index);

#ifdef __cplusplus
}
#endif

#endif
