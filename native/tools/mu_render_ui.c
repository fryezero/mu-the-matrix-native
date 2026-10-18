/* `mu-render ui`: headless renders of the client's 2D screens (NATIVE-UI-001).
 *
 *   mu-render ui title --root GAME [--size 1024x768] [--progress 37/100] [--variant s5|battle] --out t.png
 *   mu-render ui login --root GAME [--size 1024x768] [--font Tahoma] [--version 10000] --out l.png
 *   mu-render ui text  --font Tahoma --size 800x600 --string "..." --out t.png
 *   mu-render ui servers --root GAME [--size 1024x768] [--list FILE] [--select N] [--frames "x,y,d,u;..."]
 *                        [--fixed-font FACE] [--text565 T] [--text566 T] [--text567 T] --out s.png
 *
 * The draw calls come from the reconstructed client routines in
 * reconstructed/ui (validated against the client by scripts/validate_ui.py);
 * mu_ui_raster executes them in software.  Prints a JSON summary with the
 * SHA-256 of the raw framebuffer.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../core/mu_png.h"
#include "../core/mu_ui_assets.h"
#include "../core/mu_ui_font.h"
#include "../core/mu_ui_raster.h"
#include "../../reconstructed/ui/ui2d.h"
#include "../../reconstructed/ui/ui_login.h"
#include "../../reconstructed/ui/ui_server.h"
#include "../../reconstructed/ui/ui_text.h"

typedef struct ui_options {
    const char *screen, *root, *out, *font, *version, *string, *variant, *text454, *text455, *format456;
    const char *list, *frames, *fixed_font, *text565, *text566, *text567;
    int32_t select;
    float clear_gray;     /* servers: clear colour (the 3D login world is not rendered) */
    int no_text;          /* servers: blank every string (masks for comparisons) */
    float fade;
    int32_t width, height;
    uint32_t now, total;
} ui_options;

static int parse(ui_options *o, int argc, char **argv)
{
    memset(o, 0, sizeof *o);
    o->width = 1024;
    o->height = 768;
    o->now = 37;
    o->total = 100;
    o->font = "Tahoma";
    o->fade = 10.0f;
    o->variant = "s5";
    o->root = getenv("MU_GAME_ROOT");
    o->select = -2;
    o->fixed_font = NULL;
    if (argc < 3)
        return 1;
    o->screen = argv[2];
    for (int i = 3; i < argc; ++i) {
        const char *a = argv[i], *v = i + 1 < argc ? argv[i + 1] : NULL;
        if (!strcmp(a, "--root") && v) { o->root = v; ++i; }
        else if (!strcmp(a, "--out") && v) { o->out = v; ++i; }
        else if (!strcmp(a, "--font") && v) { o->font = v; ++i; }
        else if (!strcmp(a, "--version") && v) { o->version = v; ++i; }
        else if (!strcmp(a, "--string") && v) { o->string = v; ++i; }
        else if (!strcmp(a, "--variant") && v) { o->variant = v; ++i; }
        else if (!strcmp(a, "--text454") && v) { o->text454 = v; ++i; }
        else if (!strcmp(a, "--text455") && v) { o->text455 = v; ++i; }
        else if (!strcmp(a, "--format456") && v) { o->format456 = v; ++i; }
        else if (!strcmp(a, "--fade") && v) { o->fade = (float)atof(v); ++i; }
        else if (!strcmp(a, "--list") && v) { o->list = v; ++i; }
        else if (!strcmp(a, "--frames") && v) { o->frames = v; ++i; }
        else if (!strcmp(a, "--fixed-font") && v) { o->fixed_font = v; ++i; }
        else if (!strcmp(a, "--text565") && v) { o->text565 = v; ++i; }
        else if (!strcmp(a, "--text566") && v) { o->text566 = v; ++i; }
        else if (!strcmp(a, "--text567") && v) { o->text567 = v; ++i; }
        else if (!strcmp(a, "--select") && v) { o->select = atoi(v); ++i; }
        else if (!strcmp(a, "--clear") && v) { o->clear_gray = (float)atof(v); ++i; }
        else if (!strcmp(a, "--no-text")) { o->no_text = 1; }
        else if (!strcmp(a, "--size") && v) {
            if (sscanf(v, "%dx%d", &o->width, &o->height) != 2 || o->width < 16 || o->height < 16 ||
                o->width > 4096 || o->height > 4096)
                return 1;
            ++i;
        } else if (!strcmp(a, "--progress") && v) {
            if (sscanf(v, "%u/%u", &o->now, &o->total) != 2)
                return 1;
            ++i;
        } else {
            fprintf(stderr, "unknown option %s\n", a);
            return 1;
        }
    }
    return 0;
}

static void usage(const char *self)
{
    fprintf(stderr, "usage: %s ui title|login|text|servers [--root GAME] [--size WxH] [--out PNG] [--progress N/T]\n"
                    "          [--variant s5|battle] [--font FACE] [--version 5CHARS] [--string TEXT]\n"
                    "          [--text454 TEXT] [--text455 TEXT] [--format456 FMT] [--fade F]\n"
                    "          servers: [--list FILE] [--select N] [--frames \"x,y,down,up;...\"] [--fixed-font FACE]\n"
                    "                   [--text565 TEXT] [--text566 TEXT] [--text567 TEXT] [--clear GRAY] [--no-text]\n", self);
}

typedef struct texture_entry {
    uint32_t index;
    const char *path;
    uint32_t filter, wrap;
} texture_entry;

/* Title-scene textures as loaded by 0x0185ad63 (all LINEAR; lo_lo REPEAT). */
static const texture_entry TITLE_TEXTURES[] = {
    {0x7b81, "Interface\\New_lo_back_01.jpg", 0x2601, 0x2900},
    {0x7b82, "Interface\\New_lo_back_02.jpg", 0x2601, 0x2900},
    {0x7b83, "Interface\\MU_TITLE.tga", 0x2601, 0x2900},
    {0x7b84, "Interface\\lo_121518.tga", 0x2601, 0x2900},
    {0x7b85, "Interface\\New_lo_webzen_logo.tga", 0x2601, 0x2900},
    {0x7b86, "Interface\\lo_lo.jpg", 0x2601, 0x2901},
    {0x7b87, "Interface\\lo_back_s5_03.jpg", 0x2601, 0x2900},
    {0x7b88, "Interface\\lo_back_s5_04.jpg", 0x2601, 0x2900},
};
static const char *TITLE_S5[6] = {"Interface\\lo_back_s5_im01.jpg", "Interface\\lo_back_s5_im02.jpg",
                                  "Interface\\lo_back_s5_im03.jpg", "Interface\\lo_back_s5_im04.jpg",
                                  "Interface\\lo_back_s5_im05.jpg", "Interface\\lo_back_s5_im06.jpg"};
static const char *TITLE_BATTLE[6] = {"Interface\\MuBattle_loading01.jpg", "Interface\\MuBattle_loading02.jpg",
                                      "Interface\\MuBattle_loading03.jpg", "Interface\\MuBattle_loading04.jpg",
                                      "Interface\\MuBattle_loading05.jpg", "Interface\\MuBattle_loading06.jpg"};

static int load(mu_ui_assets *assets, mu_ui_state *state, const texture_entry *e, int *loaded)
{
    int r = mu_ui_assets_load(assets, state, e->path, e->index, e->filter, e->wrap);
    if (r == MU_UI_TEXTURE_LOADED)
        ++*loaded;
    else
        fprintf(stderr, "texture %#x %s: %s\n", e->index, e->path, r < 0 ? "missing" : "not loaded");
    return r;
}

static int finish(const ui_options *o, mu_ui_raster *raster, const char *screen, int loaded, int texts)
{
    size_t bytes = (size_t)raster->width * (size_t)raster->height * 4;
    uint8_t *top = malloc(bytes);
    char digest[65];
    if (!top)
        return 1;
    mu_ui_raster_read_top_down(raster, top);
    mu_sha256_hex(top, bytes, digest);
    if (o->out && mu_png_write(o->out, top, raster->width, raster->height)) {
        fprintf(stderr, "cannot write %s\n", o->out);
        free(top);
        return 1;
    }
    printf("{\"screen\": \"%s\", \"width\": %d, \"height\": %d, \"textures\": %d, \"texts\": %d, "
           "\"primitives\": %ld, \"triangles\": %ld, \"fragments\": %ld, \"unsupported\": %ld, "
           "\"framebuffer_sha256\": \"%s\"%s%s%s}\n",
           screen, raster->width, raster->height, loaded, texts, raster->primitives, raster->triangles,
           raster->fragments, raster->unsupported, digest, o->out ? ", \"png\": \"" : "", o->out ? o->out : "",
           o->out ? "\"" : "");
    free(top);
    return 0;
}

static void clear(mu_ui_state *state)
{
    uint32_t color[4] = {0, 0, 0, 0x3f800000u};
    uint32_t mask = 0x4100;
    state->sink.call(state->sink.user, MU_GL_CLEARCOLOR, color, 4, NULL, 0);
    state->sink.call(state->sink.user, MU_GL_CLEAR, &mask, 1, NULL, 0);
}

static int render_title(const ui_options *o)
{
    mu_ui_raster raster;
    mu_ui_assets assets;
    mu_ui_state state;
    mu_ui_title *title = calloc(1, sizeof *title);
    int loaded = 0;
    if (!title || mu_ui_raster_init(&raster, o->width, o->height))
        return 1;
    memset(&state, 0, sizeof state);
    state.sink = mu_ui_raster_sink(&raster);
    state.lookup = mu_ui_assets_lookup;
    state.lookup_user = &assets;
    mu_ui_state_init(&state, (uint32_t)o->width, (uint32_t)o->height);
    mu_ui_assets_init(&assets, o->root);
    for (size_t i = 0; i < sizeof TITLE_TEXTURES / sizeof TITLE_TEXTURES[0]; ++i)
        load(&assets, &state, &TITLE_TEXTURES[i], &loaded);
    for (int i = 0; i < 6; ++i) {
        texture_entry e = {0x7b89u + (uint32_t)i, strcmp(o->variant, "battle") ? TITLE_S5[i] : TITLE_BATTLE[i],
                           0x2601, 0x2900};
        load(&assets, &state, &e, &loaded);
    }
    mu_ui_title_create(&state, title, o->width, o->height);
    clear(&state);
    mu_ui_title_render(&state, title, o->now, o->total);
    int result = finish(o, &raster, "title", loaded, 0);
    mu_ui_assets_free(&assets);
    mu_ui_raster_free(&raster);
    free(title);
    return result;
}

static int render_text(const ui_options *o)
{
    mu_ui_raster raster;
    mu_ui_assets assets;
    mu_ui_state state;
    mu_ui_text text;
    mu_ui_font font;
    if (mu_ui_raster_init(&raster, o->width, o->height))
        return 1;
    memset(&state, 0, sizeof state);
    state.sink = mu_ui_raster_sink(&raster);
    state.lookup = mu_ui_assets_lookup;
    state.lookup_user = &assets;
    mu_ui_state_init(&state, (uint32_t)o->width, (uint32_t)o->height);
    mu_ui_assets_init(&assets, o->root);
    mu_ui_assets_add(&assets, &state, 0x7532, 256, 32, NULL);
    mu_ui_font_spec spec = mu_ui_font_for((uint32_t)o->width, MU_UI_FONT_NORMAL);
    mu_ui_font_open(&font, o->font, spec.height, spec.weight);
    memset(&text, 0, sizeof text);
    text.gdi = mu_ui_font_gdi(&font);
    mu_ui_text_init(&text, &state);
    text.dib = calloc((size_t)mu_ui_text_dib_stride(text.dib_width) * (size_t)text.dib_height, 1);
    clear(&state);
    mu_ui_begin_bitmap(&state);
    mu_ui_enable_alpha_test(&state, 1);
    const char *lines[3] = {o->string ? o->string : "The quick brown fox jumps over the lazy dog 0123456789",
                            "MU The Matrix - native 2D text path", "Version 1.04.05"};
    for (int i = 0; i < 3; ++i) {
        mu_ui_text_set_color(&text, 255, (uint8_t)(i == 2 ? 200 : 255), (uint8_t)(i == 1 ? 120 : 255), 255);
        mu_ui_render_text(&state, &text, 20, 20 + 20 * i, lines[i], 0, 0, 1, NULL);
    }
    mu_ui_end_bitmap(&state);
    int result = finish(o, &raster, "text", 1, 3);
    free(text.dib);
    mu_ui_font_close(&font);
    mu_ui_assets_free(&assets);
    mu_ui_raster_free(&raster);
    return result;
}

/* The login scene's 2D layer (0x01857ed9, 0x01858108..0x018588ac) over a
 * black frame: the 3D login world, the UI-manager windows and the cursor are
 * not part of this slice.  GlobalText[454..456] (encrypted Data\Lang.mpr)
 * and the version bytes (packed third section) are inputs; the defaults are
 * the strings observed on the live screen. */
static int render_login(const ui_options *o)
{
    static const texture_entry LOGIN_TEXTURES[] = {
        {0x7b1e, "Logo\\MU-logo.tga", 0x2601, 0x2900},
        {0x7b1f, "Logo\\MU-logo_g.tga", 0x2601, 0x2900},
        {0x7532, "Interface\\FontInput.tga", 0x2600, 0x2900},
    };
    mu_ui_raster raster;
    mu_ui_assets assets;
    mu_ui_state state;
    mu_ui_text text;
    mu_ui_font font;
    mu_ui_login_text strings;
    const char *version = o->version ? o->version : "10000";
    float fade = o->fade - 0.02f;     /* the overlay adds 0.02 before drawing */
    int loaded = 0;
    if (mu_ui_raster_init(&raster, o->width, o->height))
        return 1;
    memset(&state, 0, sizeof state);
    state.sink = mu_ui_raster_sink(&raster);
    state.lookup = mu_ui_assets_lookup;
    state.lookup_user = &assets;
    mu_ui_state_init(&state, (uint32_t)o->width, (uint32_t)o->height);
    mu_ui_assets_init(&assets, o->root);
    for (size_t i = 0; i < sizeof LOGIN_TEXTURES / sizeof LOGIN_TEXTURES[0]; ++i)
        load(&assets, &state, &LOGIN_TEXTURES[i], &loaded);
    if (!mu_ui_assets_lookup(&assets, 0x7532))
        mu_ui_assets_add(&assets, &state, 0x7532, 256, 32, NULL);
    mu_ui_font_spec spec = mu_ui_font_for((uint32_t)o->width, MU_UI_FONT_NORMAL);
    mu_ui_font_open(&font, o->font, spec.height, spec.weight);
    memset(&text, 0, sizeof text);
    text.gdi = mu_ui_font_gdi(&font);
    mu_ui_text_init(&text, &state);
    text.dib = calloc((size_t)mu_ui_text_dib_stride(text.dib_width) * (size_t)text.dib_height, 1);
    memset(&strings, 0, sizeof strings);
    /* Defaults: the strings the installed client showed in a live capture on
     * 2026-10-17 (read off the screen; the encrypted text file is not decoded). */
    strings.text454 = o->text454 ? o->text454 : "Mu The Matrix, Private Server Since 2005 / ";
    strings.text455 = o->text455 ? o->text455 : "  COPYRIGHT WEBZEN, INC. ALL RIGHTS RESERVED.";
    strings.format456 = o->format456 ? o->format456 : "Ver %s";
    for (int i = 0; i < 5; ++i)
        strings.version_bytes[i] = (uint8_t)((unsigned char)(version[i] ? version[i] : ' ') + i + 1);
    clear(&state);
    mu_ui_begin_bitmap(&state);
    mu_ui_login_overlay(&state, &text, &fade, 640, &strings);
    mu_ui_end_bitmap(&state);
    int result = finish(o, &raster, "login", loaded, 3);
    fprintf(stderr, "login: font %s %s (%d px), strings %s\n", font.face,
            font.backend ? "CoreText" : "placeholder", font.height,
            o->text454 || o->text455 || o->format456 ? "from options" : "observed live defaults");
    free(text.dib);
    mu_ui_font_close(&font);
    mu_ui_assets_free(&assets);
    mu_ui_raster_free(&raster);
    return result;
}

/* ---- server select (NATIVE-UI-002) ------------------------------------ */

/* Login-scene textures used by CServerSelWin, as the loader 0x0182a34c
 * loads them (GL_NEAREST; the notice-box corner and sides GL_REPEAT). */
static const texture_entry SERVER_TEXTURES[] = {
    {0x7b0e, "Interface\\cha_bt.tga", 0x2600, 0x2900},
    {0x7b0f, "Interface\\server_b2_all.tga", 0x2600, 0x2900},
    {0x7b10, "Interface\\server_b2_loding.jpg", 0x2600, 0x2900},
    {0x7b11, "Interface\\server_deco_all.tga", 0x2600, 0x2900},
    {0x7b19, "Interface\\server_ex03.tga", 0x2600, 0x2901},
    {0x7b1a, "Interface\\server_ex01.tga", 0x2600, 0x2900},
    {0x7b1b, "Interface\\server_ex02.jpg", 0x2600, 0x2901},
};

static const uint32_t FONT_HANDLES[4] = {0x0f0f0001u, 0x0f0f0002u, 0x0f0f0003u, 0x0f0f0004u};

enum { MAX_EVENTS = 64 };
typedef struct screen_sink {
    mu_ui_sink raster;
    mu_ui_font_set *fonts;
    int events[MAX_EVENTS][2];
    int event_count, sounds;
} screen_sink;

static void screen_call(void *user, int op, const uint32_t *words, int count, const void *data, size_t bytes)
{
    screen_sink *s = user;
    if (op == MU_GDI_SELECTOBJECT && count >= 1)
        mu_ui_font_set_select(s->fonts, words[0]);
    else if (op == MU_UI_EVENT && count >= 2 && s->event_count < MAX_EVENTS) {
        s->events[s->event_count][0] = (int)words[0];
        s->events[s->event_count][1] = (int)words[1];
        s->event_count++;
    } else if (op == MU_UI_SOUND)
        s->sounds++;
    s->raster.call(s->raster.user, op, words, count, data, bytes);
}

typedef struct global_texts {
    const char *t565, *t566, *t567;
} global_texts;

static const char *global_text(void *user, int32_t index)
{
    const global_texts *t = user;
    switch (index) {
    case 0x235: return t->t565;
    case 0x236: return t->t566;
    case 0x237: return t->t567;
    default: return "";
    }
}

static void copy_text(char *dst, size_t size, const char *src)
{
    snprintf(dst, size, "%s", src);
}

/* A synthetic list (no live server data): one left group, one right group. */
static void synthetic_list(mu_ui_server_list *list)
{
    static const char *names[7] = {"Native-1 [PvP]", "Native-2 [PvP]", "Native-3 [NoPvP]", "Native-4 [NoPvP] Event",
                                   "Native-5 [PvP] Arena", "Native-6 VIP", "Native-7 VIP 400+"};
    static const int percents[7] = {35, 80, 12, 100, 55, 3, 0};
    memset(list, 0, sizeof *list);
    copy_text(list->notice, sizeof list->notice, "Synthetic server list rendered by the native client layer.");
    list->group_count = 2;
    mu_ui_server_group *g = &list->groups[0];
    g->id = 1;
    g->position = MU_UI_GROUP_LEFT;
    g->button = -1;
    copy_text(g->name, sizeof g->name, "Native");
    copy_text(g->description, sizeof g->description,
              "Native arm64 server select / reconstructed CServerSelWin, synthetic data");
    g->server_count = 7;
    for (int i = 0; i < 7; ++i) {
        g->servers[i].slot = i;
        g->servers[i].percent = percents[i];
        g->servers[i].type = (uint8_t)(i % 4);
        copy_text(g->servers[i].name, sizeof g->servers[i].name, names[i]);
    }
    g = &list->groups[1];
    g->id = 2;
    g->type = 2;
    g->position = MU_UI_GROUP_RIGHT;
    g->button = -1;
    copy_text(g->name, sizeof g->name, "Test");
    copy_text(g->description, sizeof g->description, "Second synthetic group");
    g->server_count = 2;
    for (int i = 0; i < 2; ++i) {
        g->servers[i].slot = i;
        g->servers[i].percent = 20 + 30 * i;
        copy_text(g->servers[i].name, sizeof g->servers[i].name, i ? "Test-2" : "Test-1");
    }
}

/* List file: "notice TEXT", "group left|right|top TYPE ID NAME|DESCRIPTION",
 * "server PERCENT TYPE NAME" (servers belong to the last group). */
static int read_list(const char *path, mu_ui_server_list *list)
{
    char line[512];
    FILE *f = fopen(path, "r");
    if (!f)
        return 1;
    memset(list, 0, sizeof *list);
    while (fgets(line, sizeof line, f)) {
        char *nl = strchr(line, '\n');
        if (nl)
            *nl = 0;
        if (!strncmp(line, "notice ", 7)) {
            copy_text(list->notice, sizeof list->notice, line + 7);
        } else if (!strncmp(line, "group ", 6) && list->group_count < MU_UI_SERVER_GROUPS_MAX) {
            char where[16];
            int type, id, used = 0;
            if (sscanf(line + 6, "%15s %d %d %n", where, &type, &id, &used) < 3)
                continue;
            mu_ui_server_group *g = &list->groups[list->group_count++];
            g->position = !strcmp(where, "right") ? MU_UI_GROUP_RIGHT : !strcmp(where, "top") ? MU_UI_GROUP_TOP
                                                                                                : MU_UI_GROUP_LEFT;
            g->type = (uint8_t)type;
            g->id = id;
            g->button = -1;
            char *rest = line + 6 + used, *bar = strchr(rest, '|');
            if (bar) {
                *bar = 0;
                copy_text(g->description, sizeof g->description, bar + 1);
            }
            copy_text(g->name, sizeof g->name, rest);
        } else if (!strncmp(line, "server ", 7) && list->group_count > 0) {
            mu_ui_server_group *g = &list->groups[list->group_count - 1];
            int percent, type, used = 0;
            if (g->server_count >= MU_UI_GROUP_SERVERS_MAX ||
                sscanf(line + 7, "%d %d %n", &percent, &type, &used) < 2)
                continue;
            mu_ui_server *s = &g->servers[g->server_count];
            s->slot = g->server_count++;
            s->percent = percent;
            s->type = (uint8_t)type;
            copy_text(s->name, sizeof s->name, line + 7 + used);
        }
    }
    fclose(f);
    return 0;
}

static int render_servers(const ui_options *o)
{
    static const texture_entry FONT_AND_LOGO[] = {
        {0x7b1e, "Logo\\MU-logo.tga", 0x2601, 0x2900},
        {0x7b1f, "Logo\\MU-logo_g.tga", 0x2601, 0x2900},
        {0x7532, "Interface\\FontInput.tga", 0x2600, 0x2900},
    };
    mu_ui_raster raster;
    mu_ui_assets assets;
    mu_ui_state state;
    mu_ui_text text;
    mu_ui_font_set fonts;
    mu_ui_login_text strings;
    mu_ui_ctx ctx;
    screen_sink sink;
    global_texts texts;
    mu_ui_server_list *list = calloc(1, sizeof *list);
    mu_ui_server_win *win = calloc(1, sizeof *win);
    float fade = o->fade - 0.02f;
    int loaded = 0, result;
    if (!list || !win || mu_ui_raster_init(&raster, o->width, o->height))
        return 1;
    if (o->list ? read_list(o->list, list) : (synthetic_list(list), 0)) {
        fprintf(stderr, "cannot read %s\n", o->list);
        return 1;
    }
    if (o->no_text) {
        list->notice[0] = 0;
        for (int g = 0; g < list->group_count; ++g) {
            list->groups[g].name[0] = list->groups[g].description[0] = 0;
            for (int i = 0; i < list->groups[g].server_count; ++i)
                list->groups[g].servers[i].name[0] = 0;
        }
    }
    memset(&state, 0, sizeof state);
    memset(&sink, 0, sizeof sink);
    sink.raster = mu_ui_raster_sink(&raster);
    sink.fonts = &fonts;
    state.sink.user = &sink;
    state.sink.call = screen_call;
    state.lookup = mu_ui_assets_lookup;
    state.lookup_user = &assets;
    mu_ui_state_init(&state, (uint32_t)o->width, (uint32_t)o->height);
    mu_ui_assets_init(&assets, o->root);
    for (size_t i = 0; i < sizeof FONT_AND_LOGO / sizeof FONT_AND_LOGO[0]; ++i)
        load(&assets, &state, &FONT_AND_LOGO[i], &loaded);
    for (size_t i = 0; i < sizeof SERVER_TEXTURES / sizeof SERVER_TEXTURES[0]; ++i)
        load(&assets, &state, &SERVER_TEXTURES[i], &loaded);
    if (!mu_ui_assets_lookup(&assets, 0x7532))
        mu_ui_assets_add(&assets, &state, 0x7532, 256, 32, NULL);
    mu_ui_font_set_open(&fonts, o->font, o->fixed_font ? o->fixed_font : o->font, (uint32_t)o->width, FONT_HANDLES);
    memset(&text, 0, sizeof text);
    text.gdi = mu_ui_font_set_gdi(&fonts);
    mu_ui_text_init(&text, &state);
    text.dib = calloc((size_t)mu_ui_text_dib_stride(text.dib_width) * (size_t)text.dib_height, 1);

    /* The client strings read off the live screen (Data\Lang.mpr is not decoded). */
    texts.t565 = o->no_text ? "" : o->text565 ? o->text565 : "Mu The Matrix Private Server";
    texts.t566 = o->no_text ? "" : o->text566 ? o->text566 : "More than 20 years Online";
    texts.t567 = o->no_text ? "" : o->text567 ? o->text567 : "enjoy our community!";
    memset(&ctx, 0, sizeof ctx);
    ctx.state = &state;
    ctx.text = &text;
    ctx.input.screen_width = o->width;
    ctx.input.screen_height = o->height;
    ctx.fonts.normal = FONT_HANDLES[0];
    ctx.fonts.bold = FONT_HANDLES[1];
    ctx.fonts.big = FONT_HANDLES[2];
    ctx.fonts.fixed = FONT_HANDLES[3];
    ctx.global_text = global_text;
    ctx.global_text_user = &texts;

    /* CreateLoginScene: Create + centre; the server-list reply: ShowWin + UpdateDisplay. */
    mu_ui_server_win_init(win, list);
    mu_ui_server_win_create(&ctx, win);
    mu_ui_server_win_place(&ctx, win);
    mu_ui_server_win_open(&ctx, win);

    /* Choosing a group the way a player does: a click on its button (hover,
     * press, release) through CWin::Update; the click handler checks the
     * button and requests the list, whose reply runs UpdateDisplay. */
    int32_t select = o->select;
    if (select == -2)
        for (int i = 0; i < list->group_count; ++i)
            if (list->groups[i].button >= 0) {
                select = list->groups[i].button;
                break;
            }
    char clicks[160] = "";
    if (select >= 0 && select < MU_UI_SSW_GROUPS) {
        const mu_ui_sprite *b = &win->groups[select].sprite;
        int32_t cx = mu_ui_sprite_x(b) + mu_ui_sprite_width(b) / 2, cy = mu_ui_sprite_y(b) + mu_ui_sprite_height(b) / 2;
        snprintf(clicks, sizeof clicks, "%d,%d,0,0;%d,%d,1,0;%d,%d,0,1;", cx, cy, cx, cy, cx, cy);
    }
    /* Without explicit frames the cursor is parked off screen afterwards;
     * with frames, one more idle frame keeps the last cursor position (so
     * hover and pressed states stay visible). */
    char script[4096], idle[64] = "-1000,-1000,0,0";
    if (o->frames) {
        int lx = -1000, ly = -1000, d, u, n = 0;
        for (const char *p = o->frames; *p;) {
            while (*p == ';' || *p == ' ')
                ++p;
            if (sscanf(p, "%d,%d,%d,%d%n", &lx, &ly, &d, &u, &n) != 4)
                break;
            p += n;
        }
        snprintf(idle, sizeof idle, "%d,%d,0,0", lx, ly);
    }
    snprintf(script, sizeof script, "%s%s;%s", clicks, o->frames ? o->frames : "", idle);

    /* Input frames through CWin::Update (hover, press, click); the last one
     * parks the cursor, as every client frame updates before it renders. */
    for (const char *p = script; p && *p;) {
        int x, y, down, up, n = 0, before = sink.event_count;
        while (*p == ';' || *p == ' ')
            ++p;
        if (sscanf(p, "%d,%d,%d,%d%n", &x, &y, &down, &up, &n) != 4)
            break;
        ctx.input.cursor_x = x;
        ctx.input.cursor_y = y;
        ctx.input.lbutton_down = (uint8_t)down;
        ctx.input.lbutton_up = (uint8_t)up;
        mu_ui_win_update(&ctx, &win->win, 40.0);
        for (int e = before; e < sink.event_count; ++e)
            if (sink.events[e][0] == MU_UI_EVENT_SERVER_GROUP)
                mu_ui_server_win_update_display(&ctx, win);   /* the list reply the client waits for */
        p += n;
    }
    ctx.input.lbutton_down = ctx.input.lbutton_up = 0;

    memset(&strings, 0, sizeof strings);
    strings.text454 = o->no_text ? "\n" : o->text454 ? o->text454 : "Mu The Matrix, Private Server Since 2005 / ";
    strings.text455 = o->no_text ? "\n" : o->text455 ? o->text455 : "  COPYRIGHT WEBZEN, INC. ALL RIGHTS RESERVED.";
    strings.format456 = o->no_text ? "\n%s" : o->format456 ? o->format456 : "Ver %s";
    for (int i = 0; i < 5; ++i) {
        const char *version = o->version ? o->version : "10000";
        strings.version_bytes[i] = (uint8_t)((unsigned char)(version[i] ? version[i] : ' ') + i + 1);
    }
    {
        uint32_t color[4], mask = 0x4100;
        float gray = o->clear_gray;
        memcpy(&color[0], &gray, 4);
        color[1] = color[2] = color[0];
        color[3] = 0x3f800000u;
        state.sink.call(state.sink.user, MU_GL_CLEARCOLOR, color, 4, NULL, 0);
        state.sink.call(state.sink.user, MU_GL_CLEAR, &mask, 1, NULL, 0);
    }
    mu_ui_begin_bitmap(&state);
    mu_ui_ctx_set_font(&ctx, ctx.fonts.normal);
    mu_ui_login_overlay(&state, &text, &fade, 640, &strings);   /* 0x01858108..: logo and copyright lines */
    /* (the GFx movie with MENU/CREDIT renders here in the client; not reproduced) */
    win->win.cls->render(&ctx, &win->win);                       /* CUIMng::Render 0x011e348b */
    mu_ui_end_bitmap(&state);
    result = finish(o, &raster, "servers", loaded, 0);
    printf("{\"groups\": %d, \"selected\": %d, \"servers\": %d, \"events\": [", win->group_count, win->selected,
           win->server_count);
    for (int e = 0; e < sink.event_count; ++e)
        printf("%s[%d, %d]", e ? ", " : "", sink.events[e][0], sink.events[e][1]);
    printf("], \"sounds\": %d}\n", sink.sounds);
    free(text.dib);
    mu_ui_font_set_close(&fonts);
    mu_ui_assets_free(&assets);
    mu_ui_raster_free(&raster);
    free(win);
    free(list);
    return result;
}

int mu_render_ui_main(int argc, char **argv)
{
    ui_options o;
    if (parse(&o, argc, argv)) {
        usage(argv[0]);
        return 2;
    }
    if (!strcmp(o.screen, "title"))
        return render_title(&o);
    if (!strcmp(o.screen, "text"))
        return render_text(&o);
    if (!strcmp(o.screen, "login"))
        return render_login(&o);
    if (!strcmp(o.screen, "servers"))
        return render_servers(&o);
    usage(argv[0]);
    return 2;
}
