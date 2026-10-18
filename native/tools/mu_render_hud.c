/* `mu-render ui inventory|tooltip` (NATIVE-HUD-001).
 *
 *   mu-render ui inventory [--root GAME] [--size 1722x1048] [--items "code[:level],..."] [--hover N]
 *                          [--time MS] [--item-scale K] [--font FACE] [--hero S,A,E,L] --out inv.png
 *   mu-render ui tooltip   [--root GAME] --item CODE[:LEVEL] [--size WxH] [--html-out FILE] --out tip.png
 *
 * The client's inventory and tooltip are GFx (Scaleform) movies; their frames
 * are not reconstructed.  The tool draws a plain stand-in panel and cell grid
 * at the movie's measured geometry, then runs the reconstructed game side:
 * the item grid (placement by Item.bmd width/height), the slot pass and
 * RenderItem3D (model, position, rotation, scale), and draws the item models
 * with the native model pipeline under the client's orthographic item pass.
 * Tooltips: itemtooltip/itemtooltiptext lines through the reconstructed
 * formatter cases and the InfoPopup HTML assembly; the HTML is shown with the
 * UI-001 text path (GDI boundary: CoreText).  Without --root everything is
 * synthetic.  Renders and decoded text stay local.
 */
#define _POSIX_C_SOURCE 200809L /* strdup, strtok_r with -std=c11 on glibc */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../core/mu_bmd.h"
#include "../core/mu_data.h"
#include "../core/mu_hud.h"
#include "../core/mu_model.h"
#include "../core/mu_png.h"
#include "../core/mu_raster.h"
#include "../core/mu_scene.h"
#include "../core/mu_textures.h"
#include "../core/mu_ui_assets.h"
#include "../core/mu_ui_font.h"
#include "../core/mu_ui_raster.h"
#include "../../reconstructed/hud/tooltip_format.h"
#include "../../reconstructed/hud/tooltip_html.h"
#include "../../reconstructed/ui/ui2d.h"
#include "../../reconstructed/ui/ui_text.h"

typedef struct hud_options {
    const char *screen, *root, *out, *items, *font, *html_out, *item;
    int32_t width, height, hover, time_ms;
    float item_scale;
    int hero[4];
} hud_options;

static int parse(hud_options *o, int argc, char **argv)
{
    memset(o, 0, sizeof *o);
    o->width = 1722;
    o->height = 1048;
    o->hover = -1;
    o->time_ms = 0;
    o->item_scale = 200.0f;
    o->font = "Tahoma";
    o->root = getenv("MU_GAME_ROOT");
    o->hero[0] = o->hero[1] = o->hero[2] = 65535;
    o->hero[3] = 1600;
    if (argc < 3)
        return 1;
    o->screen = argv[2];
    for (int i = 3; i < argc; ++i) {
        const char *a = argv[i], *v = i + 1 < argc ? argv[i + 1] : NULL;
        if (!strcmp(a, "--root") && v) { o->root = v; ++i; }
        else if (!strcmp(a, "--out") && v) { o->out = v; ++i; }
        else if (!strcmp(a, "--items") && v) { o->items = v; ++i; }
        else if (!strcmp(a, "--item") && v) { o->item = v; ++i; }
        else if (!strcmp(a, "--font") && v) { o->font = v; ++i; }
        else if (!strcmp(a, "--html-out") && v) { o->html_out = v; ++i; }
        else if (!strcmp(a, "--hover") && v) { o->hover = atoi(v); ++i; }
        else if (!strcmp(a, "--time") && v) { o->time_ms = atoi(v); ++i; }
        else if (!strcmp(a, "--item-scale") && v) { o->item_scale = (float)atof(v); ++i; }
        else if (!strcmp(a, "--no-root")) { o->root = NULL; }
        else if (!strcmp(a, "--hero") && v) {
            if (sscanf(v, "%d,%d,%d,%d", &o->hero[0], &o->hero[1], &o->hero[2], &o->hero[3]) != 4)
                return 1;
            ++i;
        } else if (!strcmp(a, "--size") && v) {
            if (sscanf(v, "%dx%d", &o->width, &o->height) != 2 || o->width < 64 || o->height < 64 ||
                o->width > 4096 || o->height > 4096)
                return 1;
            ++i;
        } else {
            fprintf(stderr, "unknown option %s\n", a);
            return 1;
        }
    }
    return 0;
}

/* ---- 2D helpers -------------------------------------------------------- */

static void call(mu_ui_state *s, int op, const uint32_t *w, int n)
{
    s->sink.call(s->sink.user, op, w, n, NULL, 0);
}

static uint32_t fb(float f)
{
    uint32_t w;
    memcpy(&w, &f, 4);
    return w;
}

/* A solid rectangle in window pixels (origin top left) with source-alpha blending. */
static void fill_rect(mu_ui_state *s, float x, float y, float w, float h, float r, float g, float b, float a)
{
    uint32_t off = 0x0de1, blend = 0x0be2, mode = 6, fan[2] = {0x302, 0x303};
    call(s, MU_GL_DISABLE, &off, 1);
    call(s, MU_GL_ENABLE, &blend, 1);
    call(s, MU_GL_BLENDFUNC, fan, 2);
    uint32_t c[4] = {fb(r), fb(g), fb(b), fb(a)};
    call(s, MU_GL_COLOR4F, c, 4);
    call(s, MU_GL_BEGIN, &mode, 1);
    const float H = (float)s->window_height;
    const float px[4][2] = {{x, H - y}, {x, H - y - h}, {x + w, H - y - h}, {x + w, H - y}};
    for (int k = 0; k < 4; k++) {
        uint32_t v[2] = {fb(px[k][0]), fb(px[k][1])};
        call(s, MU_GL_VERTEX2F, v, 2);
    }
    call(s, MU_GL_END, NULL, 0);
    call(s, MU_GL_DISABLE, &blend, 1);
    s->texture_2d = 0;
    s->blend_mode = 0;
}

static void hex_rgb(const char *hex, uint8_t rgb[3])
{
    unsigned v = 0xffffff;
    sscanf(hex + 1, "%x", &v);
    rgb[0] = (uint8_t)(v >> 16);
    rgb[1] = (uint8_t)(v >> 8);
    rgb[2] = (uint8_t)v;
}

/* ---- tooltip lines ----------------------------------------------------- */

enum { MAX_LINES = 40 };

typedef struct tip {
    char text[MAX_LINES][256];
    int32_t color[MAX_LINES];
    int32_t count, unsupported, from_tables;
} tip;

typedef struct tables {
    mu_data_table items, tooltip, text;
    int have_items, have_tooltip, have_text;
} tables;

static void load_tables(const char *root, tables *t)
{
    memset(t, 0, sizeof *t);
    if (!root)
        return;
    char path[4096];
    snprintf(path, sizeof path, "%s/Data/Local/item.bmd", root);
    t->have_items = mu_data_load(path, NULL, &t->items) == 0 && t->items.result.status == 0;
    snprintf(path, sizeof path, "%s/Data/Local/itemtooltip.bmd", root);
    t->have_tooltip = mu_data_load(path, NULL, &t->tooltip) == 0;
    snprintf(path, sizeof path, "%s/Data/Local/itemtooltiptext.bmd", root);
    t->have_text = mu_data_load(path, NULL, &t->text) == 0;
}

static void free_tables(tables *t)
{
    if (t->have_items)
        mu_data_free(&t->items);
    if (t->have_tooltip)
        mu_data_free(&t->tooltip);
    if (t->have_text)
        mu_data_free(&t->text);
}

static int16_t s16(const uint8_t *p) { return (int16_t)(p[0] | p[1] << 8); }

static const uint8_t *tooltip_record(const tables *t, int32_t code)
{
    if (!t->have_tooltip)
        return NULL;
    for (size_t i = 0; (i + 1) * 136 <= t->tooltip.size; i++) {
        const uint8_t *r = t->tooltip.bytes + i * 136;
        if (r[4] == 0)
            break;
        if (((int32_t)r[0] << 9) + s16(r + 2) == code)
            return r;
    }
    return NULL;
}

static const uint8_t *tooltip_text(const tables *t, int32_t id)
{
    if (!t->have_text || t->text.size < 4)
        return NULL;
    uint32_t n = (uint32_t)t->text.bytes[0] | (uint32_t)t->text.bytes[1] << 8 | (uint32_t)t->text.bytes[2] << 16 |
                 (uint32_t)t->text.bytes[3] << 24;
    for (uint32_t i = 0; i < n && 4 + (size_t)(i + 1) * 260 <= t->text.size; i++) {
        const uint8_t *r = t->text.bytes + 4 + (size_t)i * 260;
        if ((r[0] | r[1] << 8) == id)
            return r;
    }
    return NULL;
}

static void add_line(tip *tp, const char *text, int32_t color)
{
    if (tp->count >= MAX_LINES)
        return;
    snprintf(tp->text[tp->count], sizeof tp->text[0], "%s", text);
    tp->color[tp->count++] = color;
}

/* The table-driven part of the builder 0x00f0eb44: name line, then up to 15
 * configured lines through the formatter cases.  Not reconstructed (and not
 * drawn): the runtime-patched header (0x00f0edf1) and GlobalText lines, price,
 * set/socket/excellent/harmony blocks and the full name-colour rules. */
static void build_tip(const hud_options *o, const tables *t, const mu_hud_item *it, tip *tp)
{
    memset(tp, 0, sizeof *tp);
    mu_ttf_item item = {it->durability, it->durability, 0, 0, 0, 0};
    mu_ttf_inputs in;
    memset(&in, 0, sizeof in);
    in.hero_strength = (uint16_t)o->hero[0];
    in.hero_agility = (uint16_t)o->hero[1];
    in.hero_energy = (uint16_t)o->hero[2];
    in.hero_level = o->hero[3];
    in.manager_1c = -1;
    if (it->has_record) {
        const mu_item_attributes *a = &it->record.attributes;
        item.defense = a->defense;
        item.magic_power = (int32_t)a->magic_power;
        item.attack_speed = a->attack_speed;
        in.req_strength = a->require_strength;           /* base values: the level formula 0x00ccf659 is not reconstructed */
        in.req_agility = a->require_dexterity;
        in.req_energy = a->require_energy;
        in.req_level = a->require_level;
        in.kind_a_3 = a->kind_a == 3;
    }
    const uint8_t *rec = tooltip_record(t, it->code);
    char name[160];
    if (rec && s16(rec + 0x4a) == -1 && it->has_record)
        snprintf(name, sizeof name, "%s", it->record.name);
    else if (rec)
        snprintf(name, sizeof name, "%.64s", (const char *)rec + 4);
    else
        snprintf(name, sizeof name, "%s", it->name);
    if ((!rec || rec[0x48]) && it->level > 0) {
        size_t n = strlen(name);
        snprintf(name + n, sizeof name - n, " +%d", it->level);
    }
    add_line(tp, name, rec ? rec[0x44] : 3);
    if (!rec) {
        static const struct { int32_t type; const char *fmt; } SYN[] = {
            {4, "Dur [%d/%d]"}, {5, "Lv %d"}, {6, "Str %d"}, {202, "(need %d str)"}, {101, "Speed %d"}};
        for (size_t k = 0; k < sizeof SYN / sizeof SYN[0]; k++) {
            char out[0x100];
            int32_t color = 0, tc[MAX_LINES] = {0};
            if (mu_tooltip_format(out, SYN[k].fmt, SYN[k].type, &item, it->level, &in, tp->count, &color, tc) == 0 &&
                out[0])
                add_line(tp, out, color);
        }
        return;
    }
    tp->from_tables = 1;
    for (int i = 0; i < 15; i++) {
        int32_t id = s16(rec + 0x4c + 4 * i);
        const uint8_t *tr = tooltip_text(t, id);
        if (!tr)
            break;                                      /* the builder stops at the first missing text */
        int32_t color = rec[0x4e + 4 * i], type = s16(tr + 0x102);
        char fmt[257];
        memcpy(fmt, tr + 2, 256);
        fmt[256] = 0;
        if (type == -1) {
            add_line(tp, fmt, color);
            continue;
        }
        char out[0x100];
        int32_t tc[MAX_LINES + 1];
        for (int k = 0; k < tp->count; k++)
            tc[k] = tp->color[k];
        if (mu_tooltip_format(out, fmt, type, &item, it->level, &in, tp->count, &color, tc) != 0) {
            tp->unsupported++;
            continue;
        }
        for (int k = 0; k < tp->count; k++)
            tp->color[k] = tc[k];
        if (out[0])
            add_line(tp, out, color);
    }
}

/* ---- the scene --------------------------------------------------------- */

typedef struct scene {
    mu_ui_raster ui;
    mu_ui_state state;
    mu_ui_assets assets;
    mu_ui_text text;
    mu_ui_font font;
} scene;

static int scene_open(scene *sc, const hud_options *o)
{
    if (mu_ui_raster_init(&sc->ui, o->width, o->height))
        return 1;
    memset(&sc->state, 0, sizeof sc->state);
    sc->state.sink = mu_ui_raster_sink(&sc->ui);
    sc->state.lookup = mu_ui_assets_lookup;
    sc->state.lookup_user = &sc->assets;
    mu_ui_state_init(&sc->state, (uint32_t)o->width, (uint32_t)o->height);
    mu_ui_assets_init(&sc->assets, o->root);
    if (mu_ui_assets_load(&sc->assets, &sc->state, "Interface\\FontInput.tga", 0x7532, 0x2600, 0x2900) !=
        MU_UI_TEXTURE_LOADED)
        mu_ui_assets_add(&sc->assets, &sc->state, 0x7532, 256, 32, NULL);
    mu_ui_font_spec spec = mu_ui_font_for((uint32_t)o->width, MU_UI_FONT_NORMAL);
    mu_ui_font_open(&sc->font, o->font, spec.height, spec.weight);
    memset(&sc->text, 0, sizeof sc->text);
    sc->text.gdi = mu_ui_font_gdi(&sc->font);
    mu_ui_text_init(&sc->text, &sc->state);
    sc->text.dib = calloc((size_t)mu_ui_text_dib_stride(sc->text.dib_width) * (size_t)sc->text.dib_height, 1);
    uint32_t color[4] = {fb(0.09f), fb(0.08f), fb(0.10f), fb(1.0f)}, mask = 0x4100;
    call(&sc->state, MU_GL_CLEARCOLOR, color, 4);
    call(&sc->state, MU_GL_CLEAR, &mask, 1);
    return 0;
}

static void scene_close(scene *sc)
{
    free(sc->text.dib);
    mu_ui_font_close(&sc->font);
    mu_ui_assets_free(&sc->assets);
    mu_ui_raster_free(&sc->ui);
}

/* Text in window pixels (top-left origin), converted to RenderText's 640 x 480 units. */
static void draw_text(scene *sc, float x, float y, float box_w, const char *s, const uint8_t rgb[3])
{
    mu_ui_enable_alpha_test(&sc->state, 1);            /* texture on, alpha test (as the login overlay) */
    uint32_t one[4] = {fb(1.0f), fb(1.0f), fb(1.0f), fb(1.0f)};
    call(&sc->state, MU_GL_COLOR4F, one, 4);           /* RenderBitmap modulates with the current colour */
    mu_ui_text_set_color(&sc->text, rgb[0], rgb[1], rgb[2], 255);
    mu_ui_render_text(&sc->state, &sc->text, (int32_t)(x / sc->state.screen_rate_x),
                      (int32_t)(y / sc->state.screen_rate_y), s, (int32_t)(box_w / sc->state.screen_rate_x), 0, 3,
                      NULL);
}

static void draw_tip(scene *sc, const tip *tp, float x, float y, int32_t *box_out)
{
    int32_t widest = 0, line_h = sc->font.height + 2;
    for (int i = 0; i < tp->count; i++) {
        int32_t cx = 0, cy = 0;
        mu_ui_text_extent(&sc->state, &sc->text, tp->text[i], (int)strlen(tp->text[i]), &cx, &cy);
        if (cx > widest)
            widest = cx;
    }
    float w = (float)widest + 24.0f, h = (float)(tp->count * line_h) + 16.0f;
    if (x + w > (float)sc->ui.width)
        x = (float)sc->ui.width - w - 4.0f;
    if (y + h > (float)sc->ui.height)
        y = (float)sc->ui.height - h - 4.0f;
    if (x < 0) x = 0;
    if (y < 0) y = 0;
    mu_ui_begin_bitmap(&sc->state);
    fill_rect(&sc->state, x, y, w, h, 0.0f, 0.0f, 0.0f, 0.82f);
    for (int i = 0; i < tp->count; i++) {
        uint8_t rgb[3];
        hex_rgb(mu_tooltip_color_hex(tp->color[i]), rgb);
        draw_text(sc, x, y + 8.0f + (float)(i * line_h), w, tp->text[i], rgb);
    }
    mu_ui_end_bitmap(&sc->state);
    if (box_out) {
        box_out[0] = (int32_t)x; box_out[1] = (int32_t)y; box_out[2] = (int32_t)w; box_out[3] = (int32_t)h;
    }
}

static int write_html(const char *path, const tip *tp)
{
    mu_tooltip_line lines[MAX_LINES];
    for (int i = 0; i < tp->count; i++)
        lines[i] = (mu_tooltip_line){tp->text[i], tp->color[i], 0, 0};
    size_t n = mu_tooltip_html(NULL, 0, lines, tp->count, NULL);
    char *html = malloc(n + 1), *utf = malloc(2 * n + 1);
    if (!html || !utf) {
        free(html);
        free(utf);
        return 1;
    }
    mu_tooltip_html(html, n + 1, lines, tp->count, NULL);
    mu_latin1_to_utf8(utf, 2 * n + 1, html);
    FILE *f = fopen(path, "wb");
    if (f) {
        fputs(utf, f);
        fclose(f);
    }
    free(html);
    free(utf);
    return f ? 0 : 1;
}

static int finish(const hud_options *o, scene *sc, const char *extra)
{
    size_t bytes = (size_t)sc->ui.width * (size_t)sc->ui.height * 4;
    uint8_t *top = malloc(bytes);
    if (!top)
        return 1;
    mu_ui_raster_read_top_down(&sc->ui, top);
    char digest[65];
    mu_sha256_hex(top, bytes, digest);
    int bad = o->out && mu_png_write(o->out, top, sc->ui.width, sc->ui.height);
    printf("{\"screen\": \"%s\", \"width\": %d, \"height\": %d, %s, \"framebuffer_sha256\": \"%s\"}\n", o->screen,
           sc->ui.width, sc->ui.height, extra, digest);
    free(top);
    return bad;
}

/* Draws one item model into `r` with the RenderObjectScreen object state. */
static int draw_model(const hud_options *o, mu_raster *r, const mu_hud_item *it, const mu_hud_item_draw *d,
                      long *triangles)
{
    (void)o;
    if (!it->model_path[0])
        return 0;
    mu_bmd bmd;
    char error[256];
    if (mu_bmd_load_file(it->model_path, &bmd, error, sizeof error) != MU_BMD_OK)
        return 0;
    mu_model_params params;
    mu_model_default_params(&params);
    params.body_scale = d->out.scale;
    memcpy(params.origin, d->out.position, sizeof params.origin);
    memcpy(params.angles, d->out.angle, sizeof params.angles);
    if (d->out.select)                                 /* RenderObjectScreen: hovered items spin */
        params.angles[1] = (float)o->time_ms * 0.2f;
    /* RenderObjectScreen 0x016c2f50 (static reading): armour-part models
     * 0x18e6..0x1ae5 get model height -160, ten less for item type 4. */
    if (d->out.model >= 0x18e6 && d->out.model < 0x1ae6) {
        params.height = -160.0f;
        if (it->has_record && it->record.attributes.type == 4)
            params.height -= 10.0f;
    }
    mu_model model;
    if (mu_model_init(&model, &bmd, &params, error, sizeof error) != MU_MODEL_OK) {
        mu_bmd_free(&bmd);
        return 0;
    }
    mu_model_set_state(&model, 0, 0.0f, 0.0f, 0);
    mu_model_update(&model);
    mu_textures textures;
    char directory[1024];
    snprintf(directory, sizeof directory, "%s", it->model_path);
    char *slash = strrchr(directory, '/');
    if (slash)
        slash[1] = 0;
    mu_textures_load(&textures, &bmd, directory);
    r->textures = textures.slots;
    r->texture_count = textures.count;
    r->texture_filter = textures.filter;
    r->texture_wrap = textures.wrap;
    mu_render_backend backend;
    mu_raster_backend(r, &backend);
    mu_draw_options draw;
    mu_draw_default_options(&draw);
    draw.textures = &textures;
    mu_draw_stats stats = {0, 0, 0, 0};
    long before = r->triangles;
    mu_scene_draw_model(&model, &draw, &backend, &stats);
    *triangles += r->triangles - before;
    r->textures = NULL;
    r->texture_count = 0;
    mu_textures_free(&textures);
    mu_model_free(&model);
    mu_bmd_free(&bmd);
    return 1;
}

static const int32_t SYNTHETIC_ITEMS[][2] = {
    {0, 7}, {1, 3}, {512 * 6 + 2, 9}, {512 * 7 + 5, 0}, {512 * 14 + 13, 0}, {512 * 14 + 14, 0}, {512 * 14 + 16, 0},
    {512 * 12 + 15, 0}, {512 * 14 + 22, 0}, {512 * 13 + 8, 0}, {512 * 13 + 9, 0}, {512 * 14 + 3, 0},
};

static int render_inventory(const hud_options *o)
{
    tables t;
    load_tables(o->root, &t);
    mu_hud_trs_table trs;
    char path[4096];
    int have_trs = 0;
    if (o->root) {
        snprintf(path, sizeof path, "%s/Data/Local/itemtrsdata.bmd", o->root);
        have_trs = mu_hud_trs_load(path, &trs) == 0;
    }
    mu_hud_inventory inv;
    mu_hud_inventory_init(&inv);
    int placed = 0, rejected = 0;
    if (o->items) {
        char *list = strdup(o->items), *save = NULL;
        for (char *tok = strtok_r(list, ",", &save); tok; tok = strtok_r(NULL, ",", &save)) {
            int code = 0, level = 0;
            sscanf(tok, "%d:%d", &code, &level);
            int k = mu_hud_inventory_add(&inv, t.have_items ? &t.items : NULL, o->root, code, level, 1, 2);
            k >= 0 ? placed++ : rejected++;
        }
        free(list);
    } else {
        for (size_t i = 0; i < sizeof SYNTHETIC_ITEMS / sizeof SYNTHETIC_ITEMS[0]; i++) {
            uint8_t w = (uint8_t)(1 + i % 2), h = (uint8_t)(1 + i % 3);
            int k = mu_hud_inventory_add(&inv, t.have_items ? &t.items : NULL, o->root, SYNTHETIC_ITEMS[i][0],
                                         SYNTHETIC_ITEMS[i][1], w, h);
            k >= 0 ? placed++ : rejected++;
        }
    }
    mu_hud_window_geometry geo = mu_hud_inventory_geometry_live();
    mu_hud_item_draw draws[MU_HUD_MAX_ITEMS];
    int32_t n = mu_hud_inventory_pass(&inv, &geo, o->width, o->height, have_trs ? &trs : NULL, o->item_scale,
                                      o->hover, draws, MU_HUD_MAX_ITEMS);
    scene sc;
    if (scene_open(&sc, o))
        return 1;
    /* stand-in frame: the GFx InventoryFrame movie is not reconstructed */
    float gx = mu_frame_x(geo.align, geo.movie_x, o->width) + geo.slot_x * geo.scale;
    float gy = mu_frame_y(geo.align, geo.movie_y, o->height) + geo.slot_y * geo.scale;
    float cw = geo.cell_w * geo.scale, ch = geo.cell_h * geo.scale;
    mu_ui_begin_bitmap(&sc.state);
    fill_rect(&sc.state, gx - 14.0f, gy - 320.0f, 8 * cw + 28.0f, 8 * ch + 360.0f, 0.13f, 0.10f, 0.09f, 1.0f);
    fill_rect(&sc.state, gx - 8.0f, gy - 312.0f, 8 * cw + 16.0f, 26.0f, 0.30f, 0.07f, 0.06f, 1.0f);
    for (int r = 0; r < 8; r++)
        for (int c = 0; c < 8; c++) {
            int used = inv.grid.cells[r * 8 + c] != 0;
            fill_rect(&sc.state, gx + (float)c * cw, gy + (float)r * ch, cw - 1.0f, ch - 1.0f, used ? 0.17f : 0.06f,
                      used ? 0.22f : 0.06f, used ? 0.10f : 0.06f, 1.0f);
        }
    uint8_t white[3] = {235, 225, 200};
    draw_text(&sc, gx - 8.0f, gy - 306.0f, 8 * cw + 16.0f, "Inventory (stand-in frame)", white);
    mu_ui_end_bitmap(&sc.state);
    /* the orthographic item pass 0x00abfcca */
    mu_raster r;
    if (mu_raster_init(&r, o->width, o->height)) {
        scene_close(&sc);
        return 1;
    }
    uint8_t clear[4] = {0, 0, 0, 0};
    mu_raster_clear(&r, clear);
    mu_ui_raster_read_top_down(&sc.ui, r.color);
    for (int k = 0; k < 16; k++)
        r.view[k] = (k % 5 == 0) ? 1.0f : 0.0f;
    mu_hud_item_projection(o->width, o->height, r.projection);
    r.front_ccw = 1;
    int drawn = 0, special = 0, missing = 0;
    long triangles = 0;
    for (int32_t k = 0; k < n; k++) {
        const mu_hud_item *it = &inv.items[draws[k].item];
        if (draws[k].status == MU_ITEM3D_SPECIAL) {
            special++;
            continue;
        }
        if (draws[k].status != MU_ITEM3D_DRAW)
            continue;
        if (getenv("MU_HUD_DEBUG"))
            fprintf(stderr, "item %d code %d model %#x cell %.1f,%.1f %.1fx%.1f pos %.1f,%.1f,%.1f scale %.4f "
                    "angle %.0f,%.0f,%.0f\n", draws[k].item, it->code, draws[k].out.model, draws[k].cell_rect[0],
                    draws[k].cell_rect[1], draws[k].cell_rect[2], draws[k].cell_rect[3], draws[k].out.position[0],
                    draws[k].out.position[1], draws[k].out.position[2], draws[k].out.scale, draws[k].out.angle[0],
                    draws[k].out.angle[1], draws[k].out.angle[2]);
        if (draw_model(o, &r, it, &draws[k], &triangles))
            drawn++;
        else
            missing++;
    }
    for (int32_t y = 0; y < o->height; y++)
        memcpy(sc.ui.rgba + (size_t)(o->height - 1 - y) * (size_t)o->width * 4,
               r.color + (size_t)y * (size_t)o->width * 4, (size_t)o->width * 4);
    mu_raster_free(&r);
    int32_t box[4] = {0, 0, 0, 0}, tip_lines = 0, unsupported = 0;
    if (o->hover >= 0 && o->hover < inv.count) {
        tip tp;
        build_tip(o, &t, &inv.items[o->hover], &tp);
        for (int32_t k = 0; k < n; k++)
            if (draws[k].item == o->hover)
                draw_tip(&sc, &tp, draws[k].cell_rect[0] - 200.0f, draws[k].cell_rect[1] + draws[k].cell_rect[3],
                         box);
        if (o->html_out)
            write_html(o->html_out, &tp);
        tip_lines = tp.count;
        unsupported = tp.unsupported;
    }
    char extra[512];
    snprintf(extra, sizeof extra,
             "\"items_placed\": %d, \"items_rejected\": %d, \"slot_calls\": %d, \"models_drawn\": %d, "
             "\"special\": %d, \"models_missing\": %d, \"triangles\": %ld, \"render_info\": \"%s\", "
             "\"tooltip_lines\": %d, \"tooltip_unsupported\": %d, \"tooltip_box\": [%d, %d, %d, %d]",
             placed, rejected, n, drawn, special, missing, triangles, have_trs ? "itemtrsdata" : "default",
             tip_lines, unsupported, box[0], box[1], box[2], box[3]);
    int result = finish(o, &sc, extra);
    scene_close(&sc);
    if (have_trs)
        mu_hud_trs_free(&trs);
    free_tables(&t);
    return result;
}

static int render_tooltip(const hud_options *o)
{
    tables t;
    load_tables(o->root, &t);
    int code = 0, level = 0;
    if (o->item)
        sscanf(o->item, "%d:%d", &code, &level);
    mu_hud_inventory inv;
    mu_hud_inventory_init(&inv);
    if (mu_hud_inventory_add(&inv, t.have_items ? &t.items : NULL, o->root, code, level, 1, 1) < 0) {
        fprintf(stderr, "item %d does not fit\n", code);
        free_tables(&t);
        return 1;
    }
    scene sc;
    if (scene_open(&sc, o))
        return 1;
    tip tp;
    build_tip(o, &t, &inv.items[0], &tp);
    int32_t box[4];
    draw_tip(&sc, &tp, 16.0f, 16.0f, box);
    if (o->html_out)
        write_html(o->html_out, &tp);
    char extra[256];
    snprintf(extra, sizeof extra, "\"lines\": %d, \"unsupported\": %d, \"from_tables\": %d, \"box\": [%d, %d, %d, %d]",
             tp.count, tp.unsupported, tp.from_tables, box[0], box[1], box[2], box[3]);
    int result = finish(o, &sc, extra);
    scene_close(&sc);
    free_tables(&t);
    return result;
}

int mu_render_hud_main(int argc, char **argv)
{
    hud_options o;
    if (parse(&o, argc, argv)) {
        fprintf(stderr, "usage: %s ui inventory|tooltip [--root GAME] [--size WxH] [--items \"code[:level],...\"]\n"
                        "          [--hover N] [--time MS] [--item-scale K] [--item CODE[:LEVEL]] [--hero S,A,E,L]\n"
                        "          [--html-out FILE] [--font FACE] [--no-root] --out PNG\n", argv[0]);
        return 2;
    }
    if (!strcmp(o.screen, "inventory"))
        return render_inventory(&o);
    if (!strcmp(o.screen, "tooltip"))
        return render_tooltip(&o);
    return 2;
}
