/* The character select's GFx list in the native client (NATIVE-CHARSEL-003); see charsel_list_gfx.h. */
#define _POSIX_C_SOURCE 200809L
#define _DARWIN_C_SOURCE 1
#include "charsel_list_gfx.h"

#include <dlfcn.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#ifdef __APPLE__
#include <mach-o/dyld.h>
#endif

#include "../../reconstructed/charsel/charsel_gfx.h"
#include "../../reconstructed/model-codec/character.h"
#include "../gfx/mugfx/include/mugfx.h"

#define WINDOW_PATH "_level0.g_mcCharacterSelect"
#define LIST_PATH WINDOW_PATH ".mcCharacterSelect.mcCharacterSelectList"

typedef struct api {
    void *dl;
    int (*abi_version)(void);
    MuGfx *(*open)(const char *, int, int, char *, size_t);
    void (*close)(MuGfx *);
    void (*set_callback)(MuGfx *, mugfx_callback, void *);
    void (*start)(MuGfx *);
    void (*advance)(MuGfx *, double);
    int (*needs_render)(MuGfx *);
    int (*render)(MuGfx *, uint8_t *, size_t);
    const char *(*invoke)(MuGfx *, const char *, const char *, const char *);
    const char *(*get_variable)(MuGfx *, const char *);
    int (*mouse)(MuGfx *, int, int, double, double);
    int (*hit_test)(MuGfx *, double, double);
    int (*set_view)(MuGfx *, int, int, int, int, int, int, double);
} api;

struct mu_charsel_list_gfx {
    api a;
    MuGfx *movie;
    mu_charsel_session *s;
    mu_csg_window window;
    mu_csg_env env;
    mu_charsel_text_fn text;
    void *text_user;
    int32_t width, height;     /* pixels */
    double scale;
    uint8_t *pixels;
    int have_pixels;
    FILE *log;
    mu_charsel_list_gfx_stats stats;
    char gt[64];
    char class_text[64];
};

/* ---- libmugfx ---- */

static int exe_dir(char *out, size_t cap)
{
    char path[4096];
#ifdef __APPLE__
    uint32_t size = sizeof path;
    if (_NSGetExecutablePath(path, &size) != 0)
        return 0;
#else
    ssize_t n = readlink("/proc/self/exe", path, sizeof path - 1);
    if (n <= 0)
        return 0;
    path[n] = 0;
#endif
    char *slash = strrchr(path, '/');
    if (!slash)
        return 0;
    *slash = 0;
    snprintf(out, cap, "%s", path);
    return 1;
}

static int api_load(api *a, const char *explicit_path, char *error, size_t cap)
{
#ifdef __APPLE__
    const char *lib = "libmugfx.dylib";
#else
    const char *lib = "libmugfx.so";
#endif
    char candidates[4][4096], dir[4096];
    int n = 0;
    if (explicit_path)
        snprintf(candidates[n++], sizeof candidates[0], "%s", explicit_path);
    if (getenv("MU_GFX_LIB"))
        snprintf(candidates[n++], sizeof candidates[0], "%s", getenv("MU_GFX_LIB"));
    if (exe_dir(dir, sizeof dir))
        snprintf(candidates[n++], sizeof candidates[0], "%s/../gfx/mugfx/target/release/%s", dir, lib);
    snprintf(candidates[n++], sizeof candidates[0], "native/gfx/mugfx/target/release/%s", lib);
    for (int i = 0; i < n && !a->dl; i++)
        a->dl = dlopen(candidates[i], RTLD_NOW | RTLD_LOCAL);
    if (!a->dl) {
        snprintf(error, cap, "libmugfx not found (native/gfx/build-mugfx.sh or MU_GFX_LIB): %s", dlerror());
        return -1;
    }
#define SYM(field, name)                                                                                     \
    do {                                                                                                       \
        *(void **)&a->field = dlsym(a->dl, name);                                                              \
        if (!a->field) {                                                                                       \
            snprintf(error, cap, "libmugfx lacks %s", name);                                                   \
            return -1;                                                                                         \
        }                                                                                                      \
    } while (0)
    SYM(abi_version, "mugfx_abi_version");
    if (a->abi_version() != MUGFX_ABI_VERSION) {
        snprintf(error, cap, "libmugfx ABI %d, expected %d", a->abi_version(), MUGFX_ABI_VERSION);
        return -1;
    }
    SYM(open, "mugfx_open");
    SYM(close, "mugfx_close");
    SYM(set_callback, "mugfx_set_callback");
    SYM(start, "mugfx_start");
    SYM(advance, "mugfx_advance");
    SYM(needs_render, "mugfx_needs_render");
    SYM(render, "mugfx_render");
    SYM(invoke, "mugfx_invoke");
    SYM(get_variable, "mugfx_get_variable");
    SYM(mouse, "mugfx_mouse");
    SYM(hit_test, "mugfx_hit_test");
    SYM(set_view, "mugfx_set_view");
#undef SYM
    return 0;
}

/* ---- class names: 0x0139cc2e(class, 1) (static reading) ----
 * code = (tier - 1) << 4 | (class & 0xf) (0x0139cab9 = the skin index 0x0139d6a2), then a switch on the code
 * to a GlobalText index; codes 9 and 10 take another text accessor (not read here). */
static const int16_t CLASS_TEXT[][2] = {
    {0, 20},    {16, 25},   {32, 1669}, {1, 21},    {17, 26},   {33, 1668}, {2, 22},    {18, 27},   {34, 1670},
    {3, 23},    {35, 1671}, {4, 24},    {36, 1672}, {5, 1687},  {21, 1688}, {37, 1689}, {6, 3150},  {38, 3151},
    {7, 4588},  {39, 4589}, {48, 5163}, {49, 5164}, {50, 5165}, {51, 5167}, {52, 5168}, {53, 5166}, {54, 5169},
    {55, 5170}, {8, 5368},  {24, 5400}, {40, 5401}, {56, 5414}, {11, 5914}, {27, 5915}, {43, 5916}, {59, 5917},
    {12, 5923}, {28, 5924}, {44, 5925}, {60, 5926}, {13, 6058}, {29, 6059}, {45, 6060}, {61, 6061}, {64, 6286},
    {65, 6287}, {66, 6288}, {67, 6290}, {68, 6291}, {69, 6289}, {70, 6292}, {71, 6293}, {72, 6294}, {73, 6295},
    {74, 6296}, {75, 6297}, {76, 6298}, {77, 6299}, {14, 6652}, {30, 6653}, {46, 6654}, {62, 6655}, {78, 6656},
    {15, 6802}, {31, 6803}, {47, 6804}, {63, 6805}, {79, 6806}};

int32_t mu_charsel_class_name_text(uint8_t class_byte)
{
    const int code = mu_character_skin_index(class_byte);
    for (size_t i = 0; i < sizeof CLASS_TEXT / sizeof CLASS_TEXT[0]; ++i)
        if (CLASS_TEXT[i][0] == code)
            return CLASS_TEXT[i][1];
    return -1;
}

/* ---- the window's environment ---- */

static const char *gt(mu_charsel_list_gfx *g, int32_t index)
{
    const char *s = g->text ? g->text(g->text_user, index) : NULL;
    if (s && *s)
        return s;
    snprintf(g->gt, sizeof g->gt, "GT%d", index);   /* stand-in: the Lang.mpr tables are local (MU_LANG_DIR) */
    return g->gt;
}

static const char *env_text(void *c, int32_t index) { return gt(c, index); }

static const char *env_class(void *c, int32_t class_byte)
{
    mu_charsel_list_gfx *g = c;
    static const char *const BASE[16] = {"Dark Wizard", "Dark Knight", "Fairy Elf", "Magic Gladiator", "Dark Lord",
                                         "Summoner", "Rage Fighter", "Grow Lancer", "Rune Wizard", "Slayer",
                                         "Gun Crusher", "Light Wizard", "Lemuria Mage", "Illusion Knight",
                                         "Alchemist", "Class 15"};
    int32_t index = mu_charsel_class_name_text((uint8_t)class_byte);
    const char *s = index >= 0 && g->text ? g->text(g->text_user, index) : NULL;
    snprintf(g->class_text, sizeof g->class_text, "%s", s && *s ? s : BASE[class_byte & 0xf]);
    return g->class_text;
}

static uint8_t *env_character(void *c, int32_t index)
{
    mu_charsel_list_gfx *g = c;
    if (index < 0 || index >= MU_CHARSEL_CHARACTERS)
        return NULL;
    return g->s->records + (size_t)index * MU_CHARSEL_RECORD;
}

static void logline(mu_charsel_list_gfx *g, const char *kind, const char *a, const char *b)
{
    if (g->log) {
        fprintf(g->log, "%s %s %s\n", kind, a, b ? b : "");
        fflush(g->log);
    }
}

static void env_emit(void *c, const char *line)
{
    mu_charsel_list_gfx *g = c;
    logline(g, "line", line, NULL);
    if (!strncmp(line, "invoke ", 7)) {
        char method[64];
        const char *rest = line + 7, *space = strchr(rest, ' ');
        size_t n = space ? (size_t)(space - rest) : strlen(rest);
        if (n >= sizeof method)
            n = sizeof method - 1;
        memcpy(method, rest, n);
        method[n] = 0;
        g->a.invoke(g->movie, WINDOW_PATH, method, space ? space + 1 : "[]");
        g->stats.invokes++;
    } else if (!strncmp(line, "call 0185a75a", 13)) {
        g->s->enter_requests++;   /* the loading scene's start (the shell answers it) */
        g->stats.enters++;
    } else if (!strncmp(line, "call 00b49bf4 1", 15) || !strncmp(line, "call 00b49eca", 13)) {
        g->stats.create_requests++;
        snprintf(g->stats.status, sizeof g->stats.status,
                 "OFFLINE DEMO: creating a character needs the server (nothing created)");
    }
}

/* ---- JSON arguments of a callback ---- */

static int parse_args(const char *s, mu_csg_arg *out, char strings[][128], int max)
{
    int n = 0;
    while (*s && *s != '[')
        ++s;
    if (*s)
        ++s;
    while (*s && n < max) {
        while (*s == ' ' || *s == ',')
            ++s;
        if (*s == ']' || !*s)
            break;
        mu_csg_arg *a = &out[n];
        memset(a, 0, sizeof *a);
        if (*s == '"') {
            size_t k = 0;
            for (++s; *s && *s != '"'; ++s) {
                if (*s == '\\' && s[1])
                    ++s;
                if (k + 1 < sizeof strings[0])
                    strings[n][k++] = *s;
            }
            strings[n][k] = 0;
            if (*s)
                ++s;
            a->type = 4;
            a->string = strings[n];
        } else if (!strncmp(s, "true", 4) || !strncmp(s, "false", 5)) {
            a->type = 2;
            a->number = *s == 't' ? 1.0 : 0.0;
            s += *s == 't' ? 4 : 5;
        } else {
            char *end;
            a->type = 3;
            a->number = strtod(s, &end);
            if (end == s)
                break;
            s = end;
        }
        ++n;
    }
    return n;
}

static void list_step(mu_charsel_list_gfx *g)
{
    /* CreateCharacterScene 0x01851540's GFx call: a live character -> 0x00b4b82c, else 0x00b4b927 */
    int any = 0;
    for (int32_t i = 0; i < MU_CSG_ROWS; ++i) {
        uint8_t *c = env_character(g, g->window.slots[i]);
        any |= c && c[MU_CHARSEL_OBJECT];
    }
    if (any)
        mu_csg_fill_and_show(&g->window, &g->env);
    else
        mu_csg_build_list(&g->window, &g->env);
}

static const char *on_call(void *user, const char *name, const char *args)
{
    mu_charsel_list_gfx *g = user;
    g->stats.callbacks++;
    snprintf(g->stats.last_callback, sizeof g->stats.last_callback, "%s", name);
    logline(g, "callback", name, args);
    if (!strcmp(name, "UIInit")) {
        /* the window's initialisation 0x00b4915b (the base check 0x00aadbc3 holds once the movie is loaded) */
        mu_csg_init(&g->window, &g->env);
        /* the client creates the movie with the login scene, whose creation (0x01851804..: 0x018519b5,
         * 0x018519d3, static reading) closes the create panel and runs show(0): SetSelectVisible(false) hides
         * the list and, with the movie's own 12 test rows still loaded, its scroll bar, which then stays hidden
         * for the ten rows of the real list (as on the live screen) */
        mu_csg_show(&g->window, &g->env, 0);
        list_step(g);
        g->stats.ready = 1;
        return NULL;
    }
    mu_csg_arg a[8];
    char strings[8][128];
    int n = parse_args(args, a, strings, 8);
    mu_csg_callback(&g->window, &g->env, name, a, n);
    return NULL;
}

/* ---- public ---- */

mu_charsel_list_gfx *mu_charsel_list_gfx_open(const mu_charsel_list_gfx_config *c, mu_charsel_session *session,
                                              char *error, size_t cap)
{
    mu_charsel_list_gfx *g = calloc(1, sizeof *g);
    if (!g) {
        snprintf(error, cap, "out of memory");
        return NULL;
    }
    g->s = session;
    g->width = c->width;
    g->height = c->height;
    g->scale = c->scale > 0 ? c->scale : 1.0;
    g->text = c->text;
    g->text_user = c->text_user;
    if (c->log_path)
        g->log = fopen(c->log_path, "a");
    /* the window: rows map to CharactersClient 0..9 (0x00b4c117 numbers them), all ten usable offline */
    g->window.row = 0;
    g->window.count = MU_CSG_ROWS;
    for (int32_t i = 0; i < MU_CSG_ROWS; ++i)
        g->window.slots[i] = (uint8_t)i;
    for (int32_t i = 0; i < session->list.count; ++i)
        if (session->list.entries[i].slot == session->selected && session->selected < MU_CSG_ROWS)
            g->window.row = session->selected;
    mu_csg_env *e = &g->env;
    e->context = g;
    e->character = env_character;
    e->global_text = env_text;
    e->class_name = env_class;
    e->emit = env_emit;
    e->selected = &session->selected;
    e->shown = &session->shown;
    e->slot_mode = 0;
    e->slot_limit = MU_CSG_ROWS;
    e->enter_refused = 0;      /* CCharSelMainWin 0x009a5029: offline nothing refuses */
    e->base_ready = 1;
    char path[4096];
    snprintf(path, sizeof path, "%s/CharacterSelect.swf", c->movie_dir);
    if (access(path, R_OK) != 0) {
        snprintf(error, cap, "%s missing (convert CharacterSelect with native/gfx/gfxconvert.py --bridge)", path);
        mu_charsel_list_gfx_close(g);
        return NULL;
    }
    if (api_load(&g->a, c->lib_path, error, cap)) {
        mu_charsel_list_gfx_close(g);
        return NULL;
    }
    /* the movie's stage is the window in points */
    const int sw = (int)lround(g->width / g->scale), sh = (int)lround(g->height / g->scale);
    g->movie = g->a.open(path, sw, sh, error, cap);
    if (!g->movie) {
        mu_charsel_list_gfx_close(g);
        return NULL;
    }
    g->a.set_view(g->movie, sw, sh, 0, 0, sw, sh, g->scale);
    g->pixels = malloc((size_t)g->width * (size_t)g->height * 4);
    g->a.set_callback(g->movie, on_call, g);
    g->a.start(g->movie);
    g->a.advance(g->movie, 0.0);
    return g;
}

void mu_charsel_list_gfx_close(mu_charsel_list_gfx *g)
{
    if (!g)
        return;
    if (g->movie)
        g->a.close(g->movie);
    if (g->a.dl)
        dlclose(g->a.dl);
    if (g->log)
        fclose(g->log);
    free(g->pixels);
    free(g);
}

int mu_charsel_list_gfx_mouse(mu_charsel_list_gfx *g, int kind, int button, double x, double y)
{
    if (!g || !g->movie)
        return 0;
    int over = g->a.hit_test(g->movie, x, y);
    if (over || kind == 0 || kind == 2)
        g->a.mouse(g->movie, kind, button, x, y);   /* moves and releases always reach it (hover states) */
    return over;
}

void mu_charsel_list_gfx_select_slot(mu_charsel_list_gfx *g, int32_t slot)
{
    if (!g)
        return;
    for (int32_t row = 0; row < MU_CSG_ROWS; ++row)
        if (g->window.slots[row] == slot) {
            char args[32];
            snprintf(args, sizeof args, "[%d]", row);
            mu_csg_select_row(&g->window, &g->env, row, 0);
            g->a.invoke(g->movie, WINDOW_PATH, "SelectIndex", args);
            return;
        }
}

void mu_charsel_list_gfx_advance(mu_charsel_list_gfx *g, double dt_ms)
{
    if (g && g->movie)
        g->a.advance(g->movie, dt_ms);
}

void mu_charsel_list_gfx_composite(mu_charsel_list_gfx *g, uint8_t *rgba, int32_t width, int32_t height)
{
    if (!g || !g->movie || !g->pixels || width != g->width || height != g->height)
        return;
    if (!g->have_pixels || g->a.needs_render(g->movie)) {
        if (g->a.render(g->movie, g->pixels, (size_t)width * (size_t)height * 4) == 0) {
            g->have_pixels = 1;
            g->stats.renders++;
        }
    }
    if (!g->have_pixels)
        return;
    const size_t n = (size_t)width * (size_t)height;
    for (size_t i = 0; i < n; ++i) {   /* straight alpha over the frame */
        const uint8_t *s = g->pixels + 4 * i;
        uint8_t *d = rgba + 4 * i;
        const unsigned a = s[3];
        if (!a)
            continue;
        for (int k = 0; k < 3; ++k)
            d[k] = (uint8_t)((s[k] * a + d[k] * (255u - a) + 127u) / 255u);
    }
}

void mu_charsel_list_gfx_stats_get(const mu_charsel_list_gfx *g, mu_charsel_list_gfx_stats *out)
{
    memset(out, 0, sizeof *out);
    if (!g)
        return;
    *out = g->stats;
    out->row = g->window.row;
}

static double variable(mu_charsel_list_gfx *g, const char *path, double fallback)
{
    const char *v = g->a.get_variable(g->movie, path);
    if (!v || !*v || !strcmp(v, "null"))
        return fallback;
    char *end;
    double d = strtod(v, &end);
    return end == v ? fallback : d;
}

int mu_charsel_list_gfx_row_center(const mu_charsel_list_gfx *gc, int32_t row, double *x, double *y)
{
    mu_charsel_list_gfx *g = (mu_charsel_list_gfx *)gc;
    if (!g || !g->movie || row < 0 || row >= MU_CSG_ROWS)
        return 0;
    /* SetSelectVisible places the list at (window width - width * scale - 50, window height / 8); rows 55
     * apart (SetCharSelArrow) */
    double lx = variable(g, LIST_PATH "._x", NAN), ly = variable(g, LIST_PATH "._y", NAN);
    double lw = variable(g, LIST_PATH "._width", NAN), rh = variable(g, LIST_PATH ".rowHeight", 55.0);
    if (isnan(lx) || isnan(ly) || isnan(lw))
        return 0;
    *x = (lx + lw / 2.0) * g->scale;
    *y = (ly + rh * (row + 0.5)) * g->scale;
    return 1;
}
