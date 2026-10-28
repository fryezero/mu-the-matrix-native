#define _POSIX_C_SOURCE 200809L /* stat with -std=c11 on glibc */
/* Native in-game interface pieces (see mu_hud.h). */
#include "mu_hud.h"
#include "../../reconstructed/items/ground_items.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

static const uint8_t TRS_KEY[3] = {0xfc, 0xcf, 0xab};   /* the tables' XOR key (NATIVE-DATA-001) */

int mu_hud_trs_load(const char *path, mu_hud_trs_table *table)
{
    memset(table, 0, sizeof *table);
    FILE *f = fopen(path, "rb");
    if (!f)
        return -1;
    fseek(f, 0, SEEK_END);
    long size = ftell(f);
    fseek(f, 0, SEEK_SET);
    uint8_t *raw = size > 0 ? malloc((size_t)size) : NULL;
    if (!raw || fread(raw, 1, (size_t)size, f) != (size_t)size) {
        fclose(f);
        free(raw);
        return -1;
    }
    fclose(f);
    uint32_t count = (uint32_t)raw[0] | (uint32_t)raw[1] << 8 | (uint32_t)raw[2] << 16 | (uint32_t)raw[3] << 24;
    if (size < 8 || (uint64_t)count * 32u + 8u != (uint64_t)size) {
        free(raw);
        return -2;
    }
    table->codes = malloc(sizeof *table->codes * (count ? count : 1));
    table->values = malloc(sizeof *table->values * (count ? count : 1));
    if (!table->codes || !table->values) {
        free(raw);
        mu_hud_trs_free(table);
        return -1;
    }
    for (uint32_t i = 0; i < count; i++) {
        uint8_t rec[32];
        for (int k = 0; k < 32; k++)                   /* each record is its own decode unit */
            rec[k] = raw[4 + 32 * i + (uint32_t)k] ^ TRS_KEY[k % 3];
        memcpy(&table->codes[i], rec, 4);
        memcpy(table->values[i], rec + 4, 28);
    }
    table->count = (int32_t)count;
    free(raw);
    return 0;
}

void mu_hud_trs_free(mu_hud_trs_table *table)
{
    free(table->codes);
    free(table->values);
    memset(table, 0, sizeof *table);
}

int mu_hud_trs_find(const mu_hud_trs_table *table, int32_t code, float scale_factor, mu_item_trs *out)
{
    if (table) {
        for (int32_t i = 0; i < table->count; i++) {
            if (table->codes[i] != (uint32_t)code)
                continue;
            const float *v = table->values[i];
            out->offset_x = v[0];
            out->offset_y = v[1];
            out->rotation[0] = v[3];
            out->rotation[1] = v[4];
            out->rotation[2] = v[5];
            out->scale = v[6] * scale_factor;
            return 1;
        }
    }
    out->offset_x = 0.5f;                              /* default record 0x06fbaa40 (0x008dcce0) */
    out->offset_y = 0.5f;
    out->rotation[0] = -90.0f;
    out->rotation[1] = 0.0f;
    out->rotation[2] = 0.0f;
    out->scale = 0.55f;
    return 0;
}

void mu_hud_inventory_init(mu_hud_inventory *inv)
{
    memset(inv, 0, sizeof *inv);
    mu_grid_construct(&inv->grid);
    mu_grid_init(&inv->grid, 1, 0, 0, 0, 8, 8, 0);
}

static void model_path(const char *root, const mu_item *item, char *out, size_t size)
{
    char rel[600];
    snprintf(rel, sizeof rel, "%s%s", item->folder, item->file);
    for (char *p = rel; *p; p++)
        if (*p == '\\')
            *p = '/';
    snprintf(out, size, "%s/%s", root, rel);
    struct stat st;
    if (stat(out, &st) != 0)
        out[0] = 0;
}

int mu_hud_item_model_path(const mu_data_table *items, const char *game_root, int32_t model, char *out, size_t size)
{
    if (!size)
        return 0;
    out[0] = 0;
    if (!game_root)
        return 0;
    char special[256];
    if (mu_gi_special_model_file(model, special, sizeof special)) {
        int n = snprintf(out, size, "%s/%s", game_root, special);
        if (n < 0 || (size_t)n >= size) {
            out[0] = 0;
            return 0;
        }
        for (char *p = out; *p; ++p)
            if (*p == '\\') *p = '/';
        struct stat st;
        if (stat(out, &st) != 0)
            out[0] = 0;
    } else {
        mu_item record;
        if (items && mu_item_model(items, model, &record) == 1)
            model_path(game_root, &record, out, size);
    }
    return out[0] != 0;
}

int mu_hud_inventory_add(mu_hud_inventory *inv, const mu_data_table *items, const char *game_root, int32_t code,
                         int32_t level, uint8_t w, uint8_t h)
{
    if (inv->count >= MU_HUD_MAX_ITEMS)
        return -1;
    mu_hud_item *it = &inv->items[inv->count];
    memset(it, 0, sizeof *it);
    it->code = code;
    it->level = level;
    if (items && mu_item_find(items, (uint32_t)code, &it->record) == 0) {
        it->has_record = 1;
        w = it->record.attributes.width;
        h = it->record.attributes.height;
        memcpy(it->name, it->record.name, sizeof it->name);
        if (game_root)
            model_path(game_root, &it->record, it->model_path, sizeof it->model_path);
        it->durability = mu_item_max_durability_at(&it->record, level, 0, 0);
    } else {
        snprintf(it->name, sizeof it->name, "Item %d", code);
        it->durability = 20;
    }
    if (w == 0 || h == 0)
        return -1;
    int32_t col, row;
    if (!mu_grid_find_free(&inv->grid, w, h, &col, &row))
        return -1;
    if ((row + h - 1) * inv->grid.cols + col + w - 1 >= inv->grid.cols * inv->grid.rows)
        return -1;
    it->grid.id = (uint32_t)(inv->count + 1);
    it->grid.code = code;
    it->grid.width = w;
    it->grid.height = h;
    if (!mu_grid_place(&inv->grid, col, row, &it->grid))
        return -1;
    return inv->count++;
}

mu_hud_window_geometry mu_hud_inventory_geometry_live(void)
{
    /* Live capture 2026-10-17, 1722 x 1048 client area: the grid's top-left
     * cell at window (1416, 540), 26-pixel cells, no gap; the inventory movie
     * is aligned to the right edge (TopRight). */
    mu_hud_window_geometry g = {MU_ALIGN_TOP_RIGHT, 1416.0f - (1722.0f - 1024.0f), 540.0f, 0.0f, 0.0f,
                                26.0f, 26.0f, 0.0f, 0.0f, 1.0f, 1.0f};
    return g;
}

typedef struct pass_ctx {
    const mu_hud_inventory *inv;
    mu_hud_item_draw *draws;
    int32_t count, max;
} pass_ctx;

static void pass_emit(void *user, const mu_slot_call *call)
{
    pass_ctx *c = user;
    if (c->count >= c->max)
        return;
    mu_hud_item_draw *d = &c->draws[c->count++];
    memset(d, 0, sizeof *d);
    d->slot = *call;
    d->item = -1;
    for (int32_t i = 0; i < c->inv->count; i++)
        if (&c->inv->items[i].grid == call->item)
            d->item = i;
}

int32_t mu_hud_inventory_pass_at(const mu_hud_inventory *inv, const mu_hud_window_geometry *geo, int32_t screen_w,
                              int32_t screen_h, const mu_hud_trs_table *trs, float scale_factor,
                              int32_t hover_item, float time, mu_hud_item_draw *draws, int32_t max)
{
    mu_slot_page page = {&inv->grid, geo->slot_x, geo->slot_y, geo->cell_w, geo->cell_h, geo->gap_x, geo->gap_y};
    mu_slot_frame frame = {1, geo->align, geo->movie_x, geo->movie_y, geo->alpha, geo->scale, &page, 1, 1};
    float rx = mu_gfx_rate_x(screen_w), ry = mu_gfx_rate_y(screen_h);
    pass_ctx ctx = {inv, draws, 0, max};
    mu_slot_pass(&frame, screen_w, screen_h, rx, ry, NULL, pass_emit, &ctx);
    for (int32_t k = 0; k < ctx.count; k++) {
        mu_hud_item_draw *d = &draws[k];
        const mu_hud_item *it = &inv->items[d->item];
        mu_slot_wrapper_in win;
        memset(&win, 0, sizeof win);
        win.code = it->code;
        win.level_word = it->level << 3;
        win.excellent = it->excellent;
        win.element = -1;
        win.x = d->slot.x;
        win.y = d->slot.y;
        win.w = d->slot.w;
        win.h = d->slot.h;
        win.a1c = d->slot.page_type;
        win.a20 = d->slot.page_flag;
        win.a28 = d->slot.type8_seen;
        win.a2c = d->slot.frame_id;
        win.a38 = -1;
        win.a40 = 1;
        win.frame_active = 1;
        win.cursor_in = (uint8_t)(d->item == hover_item);
        mu_item3d_in sys;
        memset(&sys, 0, sizeof sys);
        sys.cursor_in = win.cursor_in;
        sys.time = time;
        mu_hud_trs_find(trs, it->code, scale_factor, &sys.trs);
        if (it->has_record) {
            sys.kind_b_6a = it->record.attributes.kind_b == 0x6a;
            sys.kind_a_22 = it->record.attributes.kind_a == 0x22;
        }
        sys.frame_scale = geo->scale;
        sys.rate_x = rx;
        sys.rate_y = ry;
        mu_slot_wrapper_out wout;
        mu_slot_wrapper(1, &win, &sys, &wout);
        d->status = mu_item3d(&wout.item3d, &d->out);
        d->cell_rect[0] = d->slot.x / rx;
        d->cell_rect[1] = d->slot.y / ry;
        d->cell_rect[2] = d->slot.w / rx;
        d->cell_rect[3] = d->slot.h / ry;
    }
    return ctx.count;
}

int32_t mu_hud_inventory_pass(const mu_hud_inventory *inv, const mu_hud_window_geometry *geo, int32_t screen_w,
                              int32_t screen_h, const mu_hud_trs_table *trs, float scale_factor,
                              int32_t hover_item, mu_hud_item_draw *draws, int32_t max)
{
    return mu_hud_inventory_pass_at(inv, geo, screen_w, screen_h, trs, scale_factor, hover_item, 0.0f, draws, max);
}

void mu_hud_item_projection(int32_t screen_w, int32_t screen_h, float m[16])
{
    const double l = 0, r = screen_w, b = 0, t = screen_h, n = 20, f = 2000;
    for (int k = 0; k < 16; k++)
        m[k] = 0;
    m[0] = (float)(2 / (r - l));
    m[5] = (float)(2 / (t - b));
    m[10] = (float)(-2 / (f - n));
    m[12] = (float)(-(r + l) / (r - l));
    m[13] = (float)(-(t + b) / (t - b));
    m[14] = (float)(-(f + n) / (f - n));
    m[15] = 1;
}
