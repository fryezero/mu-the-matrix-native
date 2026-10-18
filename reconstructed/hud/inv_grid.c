/* Reconstructed item grid (see inv_grid.h).  Each function restates the
 * client routine named in its comment; loop orders and bounds follow the
 * client's instructions. */
#include "inv_grid.h"

#include <string.h>

static void raise_event(const mu_grid *g, int event, const mu_grid_item *item)
{
    if (g->event)
        g->event(g->user, event, item);
}

void mu_grid_reset(mu_grid *g)                         /* 0x00ad32d7 */
{
    g->owner = 0;
    g->y = 0;
    g->x = 0;
    g->pixel_h = 0;
    g->pixel_w = 0;
    g->rows = 0;
    g->cols = 0;
    g->page = 0;
    g->has_cells = 0;
    g->field_3c = -1;
    g->flag_40 = 0;
    g->type = -1;
    g->flag_48 = 0;
    g->flag_49 = 1;
}

void mu_grid_construct(mu_grid *g)                     /* 0x00ad322b */
{
    mu_grid_event event = g->event;
    void *user = g->user;
    memset(g, 0, sizeof *g);
    g->event = event;
    g->user = user;
    g->field_00 = 0xff;
    mu_grid_reset(g);
}

int mu_grid_init(mu_grid *g, int32_t type, uint32_t owner, int32_t x, int32_t y, int32_t cols, int32_t rows,
                 int32_t page)                         /* 0x00ad341d */
{
    if (g->has_cells || g->item_count != 0)
        return 0;
    if (cols < 0 || rows < 0 || (int64_t)cols * rows > MU_GRID_MAX_CELLS)
        return 0;                                      /* authored capacity */
    g->type = type;
    g->owner = owner;
    g->x = x;
    g->y = y;
    g->pixel_w = cols * 0x1a;
    g->pixel_h = rows * 0x1a;
    g->cols = cols;
    g->rows = rows;
    g->page = page;
    g->has_cells = 1;
    memset(g->cells, 0, sizeof g->cells);
    return 1;
}

int mu_grid_fits_index(const mu_grid *g, int32_t index, int32_t w, int32_t h)   /* 0x00ad4e69 */
{
    int32_t total = g->cols * g->rows;
    for (int32_t r = 0; r < h; r++) {
        for (int32_t c = 0; c < w; c++) {
            int32_t cell = r * g->cols + index + c;
            if (cell >= total)
                return 0;
            if (cell < 0)
                return 0;                              /* authored: the client reads before its block */
            if (g->cells[cell] != 0)
                return 0;
        }
    }
    return 1;
}

int mu_grid_fits(const mu_grid *g, int32_t col, int32_t row, int32_t w, int32_t h)   /* 0x00ad4ee4 */
{
    return mu_grid_fits_index(g, row * g->cols + col, w, h);
}

int mu_grid_item_fits(const mu_grid *g, int32_t col, int32_t row, const mu_grid_item *item)   /* 0x00ad4ff4 */
{
    if (!item)
        return 0;
    return mu_grid_fits(g, col, row, item->width, item->height);
}

int mu_grid_find_free(const mu_grid *g, int32_t w, int32_t h, int32_t *col, int32_t *row)   /* 0x00ad49fb */
{
    for (int32_t r = 0; r < g->rows; r++) {
        for (int32_t c = 0; c < g->cols; c++) {
            if (mu_grid_fits(g, c, r, w, h)) {
                *col = c;
                *row = r;
                return 1;
            }
        }
    }
    return 0;
}

int32_t mu_grid_find_free_index(const mu_grid *g, int32_t w, int32_t h)   /* 0x00ad4994 */
{
    for (int32_t i = 0; i < g->cols * g->rows; i++) {
        if (mu_grid_fits_index(g, i, w, h) && i % g->cols < g->cols - (w - 1))
            return i;
    }
    return -1;
}

int32_t mu_grid_count_empty(const mu_grid *g)          /* 0x00ad4a6d */
{
    int32_t n = 0;
    for (int32_t r = 0; r < g->rows; r++)
        for (int32_t c = 0; c < g->cols; c++)
            if (g->cells[r * g->cols + c] == 0)
                n++;
    return n;
}

int32_t mu_grid_count_fits(const mu_grid *g, int32_t w, int32_t h, int32_t limit, int *overflow)   /* 0x00ad4ad9 */
{
    int32_t taken[128];
    int32_t ntaken = 0, count = 0;
    for (int k = 0; k < 128; k++)
        taken[k] = -1;                                 /* 0x00ada7d8(list, 0x80, &-1) */
    if (overflow)
        *overflow = 0;
    for (int32_t r = 0; r <= g->rows - h; r++) {
        int32_t c = 0;
        while (c <= g->cols - w) {
            int32_t index = r * g->cols + c;
            int seen = 0;
            for (int k = 0; k < 128; k++) {
                if (taken[k] == index) {
                    seen = 1;
                    break;
                }
            }
            if (seen) {
                c++;
                continue;
            }
            if (g->cells[index] != 0) {
                c++;
                continue;
            }
            if (!mu_grid_fits_index(g, index, w, h)) {
                c++;
                continue;
            }
            count++;
            if (count == limit)
                return count;
            for (int32_t rr = r; rr < r + h; rr++) {
                for (int32_t cc = c; cc < c + w; cc++) {
                    if (ntaken < 128)
                        taken[ntaken] = rr * g->cols + cc;
                    else if (overflow)
                        *overflow = 1;                 /* the client writes past its list */
                    ntaken++;
                }
            }
            c += w;
        }
    }
    return count;
}

void mu_grid_rect(const mu_grid *g, int32_t rect[4])   /* 0x00ad4cb1 */
{
    rect[0] = g->x;
    rect[1] = g->y;
    rect[2] = rect[0] + g->pixel_w;
    rect[3] = rect[1] + g->pixel_h;
}

int mu_grid_pt_in(const mu_grid *g, int32_t px, int32_t py)   /* 0x00ad4f11 */
{
    int32_t r[4];
    mu_grid_rect(g, r);
    return px >= r[0] && px < r[2] && py >= r[1] && py < r[3];
}

int mu_grid_rect_in(const mu_grid *g, const int32_t rect[4])   /* 0x00ad4f51 */
{
    int32_t r[4];
    mu_grid_rect(g, r);
    return rect[0] >= r[0] && rect[2] <= r[2] && rect[1] >= r[1] && rect[3] <= r[3];
}

int mu_grid_pixel_cell(const mu_grid *g, int32_t px, int32_t py, int32_t *col, int32_t *row)   /* 0x00ad4d43 */
{
    int32_t r[4];
    mu_grid_rect(g, r);
    if (!(px >= r[0] && px < r[2] && py >= r[1] && py < r[3]))
        return 0;
    *col = (px - r[0]) / 20;
    *row = (py - r[1]) / 20;
    return 1;
}

int32_t mu_grid_pixel_index(const mu_grid *g, int32_t px, int32_t py)   /* 0x00ad4da5 */
{
    int32_t col, row;
    if (!mu_grid_pixel_cell(g, px, py, &col, &row))
        return -1;
    return row * g->cols + col;
}

int mu_grid_item_fits_pixel(const mu_grid *g, int32_t px, int32_t py, const mu_grid_item *item)   /* 0x00ad5037 */
{
    int32_t col, row;
    if (!item)
        return 0;
    if (!mu_grid_pixel_cell(g, px, py, &col, &row))
        return 0;
    return mu_grid_item_fits(g, col, row, item);
}

void mu_grid_set_position(mu_grid *g, int32_t x, int32_t y)   /* 0x00ad4c51 */
{
    g->x = x;
    g->y = y;
}

void mu_grid_set_pixel_size(mu_grid *g, int32_t w, int32_t h)   /* 0x00ad4cf6 */
{
    g->pixel_w = w;
    g->pixel_h = h;
}

static void after_change(mu_grid *g)
{
    raise_event(g, MU_GRID_EV_REFRESH, NULL);         /* 0x00ad86dc */
    if (g->type == 0xc && g->owner != 0 && g->owner_pages - 1 == g->page)
        raise_event(g, MU_GRID_EV_LASTPAGE, NULL);    /* 0x00adaccf, 0x00c06911 */
}

static void fill(mu_grid *g, const mu_grid_item *item, uint32_t value)
{
    int32_t total = g->cols * g->rows;
    for (int32_t r = 0; r < item->height; r++) {
        for (int32_t c = 0; c < item->width; c++) {
            int32_t cell = item->col + ((item->row + r) * g->cols + c);
            if (cell < 0 || cell >= total) {
                g->overflow = 1;                       /* client: write outside the block */
                continue;
            }
            g->cells[cell] = value;
        }
    }
}

int mu_grid_place(mu_grid *g, int32_t col, int32_t row, mu_grid_item *item)   /* 0x00ad37c9 */
{
    if (!item || col < 0 || row < 0 || col >= g->cols || row >= g->rows)
        return 0;
    if (g->item_count >= MU_GRID_MAX_ITEMS)
        return 0;                                      /* authored capacity */
    item->col = (uint8_t)col;
    item->row = (uint8_t)row;
    fill(g, item, item->id);
    g->items[g->item_count++] = item;                  /* vector push_back 0x00adc0c7 */
    raise_event(g, MU_GRID_EV_STATUS, item);           /* 0x00c94193(item, type, -1) */
    after_change(g);
    return 1;
}

int mu_grid_place_index(mu_grid *g, int32_t index, mu_grid_item *item)   /* 0x00ad3775 */
{
    if (index < 0 || index >= g->cols * g->rows)
        return 0;
    return mu_grid_place(g, index % g->cols, index / g->cols, item);
}

void mu_grid_remove(mu_grid *g, const mu_grid_item *item)   /* 0x00ad3a4e */
{
    for (int32_t i = 0; i < g->item_count; i++) {
        if (g->items[i] != item)
            continue;
        memmove(&g->items[i], &g->items[i + 1], (size_t)(g->item_count - i - 1) * sizeof g->items[0]);
        g->item_count--;                               /* vector erase 0x00adbf69 */
        fill(g, item, 0);
        break;
    }
    after_change(g);
}

mu_grid_item *mu_grid_find_id(const mu_grid *g, uint32_t id)   /* 0x00ad403c */
{
    for (int32_t i = 0; i < g->item_count; i++)
        if (g->items[i]->id == id)
            return g->items[i];
    return NULL;
}

mu_grid_item *mu_grid_item_at(const mu_grid *g, int32_t index)   /* 0x00ad3fd9 */
{
    if (index < 0 || index >= g->cols * g->rows)
        return NULL;
    return mu_grid_find_id(g, g->cells[index]);
}

int mu_grid_has_code(const mu_grid *g, int16_t code)   /* 0x00ad3c57 */
{
    for (int32_t i = 0; i < g->item_count; i++)
        if (g->items[i]->code == (int32_t)code)
            return 1;
    return 0;
}

int mu_grid_can_move(mu_grid *g, int32_t w, int32_t h, int32_t index)   /* 0x00ad47f1 */
{
    uint32_t saved = g->cells[index];
    g->cells[index] = 0;
    int ok = mu_grid_find_free_index(g, w, h) != -1;
    g->cells[index] = saved;
    return ok;
}
