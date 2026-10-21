/* The character select's GFx list in the native client (NATIVE-CHARSEL-003); see charsel_list_gfx.h. */
#define _POSIX_C_SOURCE 200809L
#define _DARWIN_C_SOURCE 1
#include "charsel_list_gfx.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "../../reconstructed/charsel/charcreate.h"
#include "../../reconstructed/charsel/charsel_gfx.h"
#include "charsel_create_gfx.h"
#include "charsel_mugfx.h"

#define WINDOW_PATH "_level0.g_mcCharacterSelect"
#define LIST_PATH WINDOW_PATH ".mcCharacterSelect.mcCharacterSelectList"

typedef mu_charsel_mugfx api;

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
    mu_charsel_create *create;   /* NATIVE-CHARCREATE-001: the create panel, delete flow, messages, menu */
};

/* ---- class names: 0x0139cc2e(class, 1) ----
 * NATIVE-CHARCREATE-001 executed the switch in Unicorn for every class byte (codes 9/25/41/57 and
 * 10/26/42/58 included, default GlobalText 2305); reconstructed/charsel/charcreate.c holds the table. */
int32_t mu_charsel_class_name_text(uint8_t class_byte)
{
    return mu_ccr_class_name_text(class_byte, 1);
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
    /* the delete request's password never reaches the log */
    logline(g, "line", strncmp(line, "call 00b4c76a", 13) ? line : "call 00b4c76a (delete request)", NULL);
    if (!strncmp(line, "call 00b49bf4 1", 15)) {
        g->stats.create_requests++;
        snprintf(g->stats.status, sizeof g->stats.status,
                 g->create ? "OFFLINE DEMO: create panel (characters are kept in the local store)"
                           : "OFFLINE DEMO: creating a character needs the server (nothing created)");
    }
    if (mu_charsel_create_line(g->create, line))
        return;
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
    } else if (!strncmp(line, "call 00b49eca", 13)) {
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
        if (g->create) {
            /* NATIVE-CHARCREATE-001: the window's slot +0x10 0x00b496d4 (the GFx manager calls it for every window,
             * static): +0x9c = 0 and SetCreateBoardInfo, which the movie answers with the preview rectangle; the
             * character list's handler sets the daily creation counts (UpdateCreateCount 0x00b49d0d) */
            mu_charsel_create_line(g->create, "call 009a5920 0");
            g->a.invoke(g->movie, WINDOW_PATH, "SetCreateBoardInfo", "[]");
            mu_charsel_create_ready(g->create);
        }
        g->stats.ready = 1;
        return NULL;
    }
    mu_csg_arg a[8];
    char strings[8][128];
    int n = parse_args(args, a, strings, 8);
    if (g->create && n > 0 && a[0].type == 4) {   /* the callback's text, before the window's dispatch */
        if (!strcmp(name, "OnEnterCharacterName"))
            mu_charsel_create_stash(g->create, a[0].string, NULL);
        else if (!strcmp(name, "UpdateInput"))
            mu_charsel_create_stash(g->create, NULL, a[0].string);
    }
    if (g->create) {   /* window +0x79: a pending delete blocks the callbacks while the movie is busy */
        mu_charsel_create_stats cs;
        mu_charsel_create_stats_get(g->create, &cs);
        g->env.window_flag_79 = cs.caution_open;
        g->env.gfx_busy = cs.caution_open;   /* 0x00aae6f9: the Caution window is modal */
    }
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
    if (mu_charsel_mugfx_load(&g->a, c->lib_path, error, cap)) {
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
    if (c->create) {   /* NATIVE-CHARCREATE-001 */
        mu_charsel_create_config cc;
        memset(&cc, 0, sizeof cc);
        cc.movie_dir = c->movie_dir;
        cc.game_root = c->game_root;
        cc.width = g->width;
        cc.height = g->height;
        cc.scale = g->scale;
        cc.text = c->text;
        cc.text_user = c->text_user;
        cc.lang_dir = c->lang_dir;
        cc.hooks = c->hooks;
        cc.created = c->created;
        cc.limit = c->limit;
        g->create = mu_charsel_create_open(&cc, &g->a, &g->window, &g->env, error, cap);
    }
    g->a.set_callback(g->movie, on_call, g);
    g->a.start(g->movie);
    g->a.advance(g->movie, 0.0);
    return g;
}

void mu_charsel_list_gfx_close(mu_charsel_list_gfx *g)
{
    if (!g)
        return;
    mu_charsel_create_close(g->create);
    if (g->movie)
        g->a.close(g->movie);
    mu_charsel_mugfx_unload(&g->a);
    if (g->log)
        fclose(g->log);
    free(g->pixels);
    free(g);
}

int mu_charsel_list_gfx_mouse(mu_charsel_list_gfx *g, int kind, int button, double x, double y)
{
    if (!g || !g->movie)
        return 0;
    if (mu_charsel_create_mouse(g->create, kind, button, x, y))   /* the Caution box (modal), then the menu */
        return 1;
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
    if (g)
        mu_charsel_create_advance(g->create, dt_ms);
}

void mu_charsel_list_gfx_composite(mu_charsel_list_gfx *g, uint8_t *rgba, int32_t width, int32_t height)
{
    if (!g || !g->movie || !g->pixels || width != g->width || height != g->height)
        return;
    /* the window's render hook draws the creation preview before the movie (0x00b49cd7) */
    mu_charsel_create_draw_preview(g->create, rgba, width, height);
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
    mu_charsel_create_draw_windows(g->create, rgba, width, height);   /* the menu, then the Caution box */
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

/* ---- NATIVE-CHARCREATE-001 ---- */

void mu_charsel_list_gfx_event(mu_charsel_list_gfx *g, int32_t code, int32_t argument)
{
    if (g)
        mu_charsel_create_event(g->create, code, argument);
}

void mu_charsel_list_gfx_menu(mu_charsel_list_gfx *g)
{
    if (g)
        mu_charsel_create_menu_toggle(g->create);
}

void mu_charsel_list_gfx_close_panel(mu_charsel_list_gfx *g)
{
    if (g)
        mu_charsel_create_close_panel(g->create);
}

int mu_charsel_list_gfx_key(mu_charsel_list_gfx *g, int vk, int down)
{
    if (!g || !g->movie)
        return 0;
    if (mu_charsel_create_key(g->create, vk, down))
        return 1;
    mu_charsel_create_stats cs;
    mu_charsel_create_stats_get(g->create, &cs);
    if (cs.create_open) {   /* the panel's name box has the focus (SetCreateVisible: tiCharacterName.SetFocus) */
        g->a.key(g->movie, down ? 0 : 1, vk, vk == 0x0d ? '\r' : vk == 0x08 ? 8 : 0, 0);
        return vk != 0x1b;   /* Esc still reaches the scene tick (it closes the panel) */
    }
    return 0;
}

int mu_charsel_list_gfx_text(mu_charsel_list_gfx *g, const char *utf8)
{
    if (!g || !g->movie)
        return 0;
    if (mu_charsel_create_text(g->create, utf8))
        return 1;
    mu_charsel_create_stats cs;
    mu_charsel_create_stats_get(g->create, &cs);
    if (cs.create_open) {
        g->a.text(g->movie, utf8);
        return 1;
    }
    return 0;
}

void mu_charsel_list_gfx_rebind(mu_charsel_list_gfx *g, mu_charsel_session *session)
{
    if (!g)
        return;
    g->s = session;
    g->env.selected = &session->selected;
    g->env.shown = &session->shown;
    mu_charsel_create_rebind(g->create, &g->env);
    /* CreateCharacterScene's GFx call again: the list from the new records */
    list_step(g);
}

void mu_charsel_list_gfx_create_stats(const mu_charsel_list_gfx *g, mu_charsel_create_stats *out)
{
    mu_charsel_create_stats_get(g ? g->create : NULL, out);
}

void mu_charsel_list_gfx_create_done(mu_charsel_list_gfx *g)
{
    if (g)
        mu_charsel_create_clear_rebuild(g->create);
}

int mu_charsel_list_gfx_control(const mu_charsel_list_gfx *gc, const char *name, double *x, double *y)
{
    mu_charsel_list_gfx *g = (mu_charsel_list_gfx *)gc;
    if (!g || !g->movie)
        return 0;
    return mu_charsel_create_control(g->create, g->movie, WINDOW_PATH, name, x, y);
}
