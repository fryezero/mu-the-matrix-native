/* `mu-render ui`: headless renders of the client's 2D screens (NATIVE-UI-001).
 *
 *   mu-render ui title --root GAME [--size 1024x768] [--progress 37/100] [--variant s5|battle] --out t.png
 *   mu-render ui login --root GAME [--size 1024x768] [--font Tahoma] [--version 1.04.05] --out l.png
 *   mu-render ui text  --font Tahoma --size 800x600 --string "..." --out t.png
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
#include "../../reconstructed/ui/ui_text.h"

typedef struct ui_options {
    const char *screen, *root, *out, *font, *version, *string, *variant, *text454, *text455, *format456;
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
    fprintf(stderr, "usage: %s ui title|login|text [--root GAME] [--size WxH] [--out PNG] [--progress N/T]\n"
                    "          [--variant s5|battle] [--font FACE] [--version 5CHARS] [--string TEXT]\n"
                    "          [--text454 TEXT] [--text455 TEXT] [--format456 FMT] [--fade F]\n", self);
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
 * placeholders. */
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
    const char *version = o->version ? o->version : "?????";
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
    strings.text454 = o->text454 ? o->text454 : "Copyright (c) WEBZEN, INC. All rights reserved.";
    strings.text455 = o->text455 ? o->text455 : "  Mu The Matrix";
    strings.format456 = o->format456 ? o->format456 : "Version %s";
    for (int i = 0; i < 5; ++i)
        strings.version_bytes[i] = (uint8_t)((unsigned char)(version[i] ? version[i] : ' ') + i + 1);
    clear(&state);
    mu_ui_begin_bitmap(&state);
    mu_ui_login_overlay(&state, &text, &fade, 640, &strings);
    mu_ui_end_bitmap(&state);
    int result = finish(o, &raster, "login", loaded, 3);
    fprintf(stderr, "login: font %s %s (%d px), strings %s\n", font.face,
            font.backend ? "CoreText" : "placeholder", font.height,
            o->text454 || o->text455 || o->format456 ? "from options" : "placeholders");
    free(text.dib);
    mu_ui_font_close(&font);
    mu_ui_assets_free(&assets);
    mu_ui_raster_free(&raster);
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
    usage(argv[0]);
    return 2;
}
