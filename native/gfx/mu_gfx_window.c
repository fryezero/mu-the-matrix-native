/* mu-gfx-window: NATIVE-GFX-001 prototype.
 *
 * Plays two of the client's GFx movies with Ruffle (through native/gfx/mugfx)
 * inside a native SDL2 + OpenGL 2.1 window, or headless into PNG files, and
 * wires the game side for them the way the client's GFx boundary works
 * (docs/research/client-hud.md, docs/research/native-gfx.md):
 *
 *   main            bottom bar; the game feeds setHPMP / setExp with demo values
 *                   every 40 ms logic step and answers its "main" ExternalInterface
 *                   channel (onLoad, onHotKey, onResize ...);
 *   InventoryFrame  opened/closed by the game (SetVisible) on the bottom bar's
 *                   inventory hotkey or the I key; its callbacks UIInit,
 *                   requestWindowPos, requestSlotInfo, requestItemSlotClick/Over/Out
 *                   and CloseWindow drive the reconstructed item grid
 *                   (reconstructed/hud/inv_grid.c) and the reconstructed slot pass
 *                   (item_slots.c), which places the item stand-ins (coloured boxes
 *                   in place of RenderItem3D models) over the movie.
 *
 * Usage:
 *   mu-gfx-window --gfx DIR [--size 1280x800] [--headless --out-dir DIR] [--script]
 *                 [--frames N] [--bench] [--log FILE]
 * DIR holds main.swf and InventoryFrame.swf converted with
 *   gfxconvert.py --bridge --transparent --var _root.isClient=true
 * The movies and every output are client-derived: keep them local.
 */
#include <math.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <time.h>

#include <SDL.h>
#ifdef __APPLE__
#define GL_SILENCE_DEPRECATION 1
#include <OpenGL/gl.h>
#else
#include <GL/gl.h>
#endif

#include "inv_grid.h"
#include "item_slots.h"
#include "mu_png.h"
#include "mugfx.h"

#define MAX_ITEMS 12

typedef struct Game Game;

typedef struct Movie {
    const char *name;
    MuGfx *g;
    uint8_t *rgba;
    GLuint tex;
    int has_frame;
    Game *game;
    double advance_ms, render_ms, capture_ms, upload_ms;
    long renders;
} Movie;

struct Game {
    int w, h;
    Movie hud, inv;
    char hud_path[128];     /* from main's onLoad (targetPath) */
    char inv_uid[64];       /* from UIInit */
    char inv_path[96];
    int inv_open;
    float win_x, win_y;     /* requestWindowPos */
    float slot_x, slot_y, slot_w, slot_h, gap_x, gap_y;
    int have_slot;
    mu_grid grid;
    mu_grid_item items[MAX_ITEMS];
    float item_rgb[MAX_ITEMS][3];
    int n_items;
    int held;               /* items[] index on the cursor, or -1 */
    int hover;              /* slot index under the cursor, or -1 */
    double mouse_x, mouse_y;
    double time_ms;         /* game time */
    double next_step_ms;    /* next 40 ms logic step */
    long steps;
    FILE *log;
    long calls;
    char reply[256];
};

static double now_ms(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec * 1000.0 + ts.tv_nsec / 1e6;
}

static void logf_(Game *G, const char *fmt, ...)
{
    if (!G->log)
        return;
    va_list ap;
    va_start(ap, fmt);
    fprintf(G->log, "[%8.1f] ", G->time_ms);
    vfprintf(G->log, fmt, ap);
    fputc('\n', G->log);
    va_end(ap);
    fflush(G->log);
}

/* ---- tiny JSON helpers for the callback arguments (arrays of scalars/objects) */

static int json_numbers(const char *s, double *out, int max)
{
    int n = 0, depth = 0, in_str = 0;
    for (const char *p = s; *p && n < max; p++) {
        if (in_str) {
            if (*p == '\\' && p[1]) p++;
            else if (*p == '"') in_str = 0;
            continue;
        }
        if (*p == '"') { in_str = 1; continue; }
        if (*p == '{' || *p == '[') { depth++; continue; }
        if (*p == '}' || *p == ']') { depth--; continue; }
        if (depth == 1 && (*p == '-' || (*p >= '0' && *p <= '9'))) {
            char *end;
            out[n++] = strtod(p, &end);
            p = end - 1;
        }
    }
    return n;
}

static int json_string(const char *s, int index, char *out, size_t cap)
{
    int n = 0, depth = 0;
    for (const char *p = s; *p; p++) {
        if (*p == '{' || *p == '[') { depth++; continue; }
        if (*p == '}' || *p == ']') { depth--; continue; }
        if (*p == '"') {
            const char *q = p + 1;
            while (*q && *q != '"') { if (*q == '\\' && q[1]) q++; q++; }
            if (depth == 1 && n++ == index) {
                size_t len = (size_t)(q - p - 1);
                if (len >= cap) len = cap - 1;
                memcpy(out, p + 1, len);
                out[len] = 0;
                return 1;
            }
            p = q;
        }
    }
    return 0;
}

static double json_field(const char *s, const char *key, double fallback)
{
    char pat[64];
    snprintf(pat, sizeof pat, "\"%s\":", key);
    const char *p = strstr(s, pat);
    return p ? strtod(p + strlen(pat), NULL) : fallback;
}

/* ---- game -> movie ------------------------------------------------------ */

static const char *invoke(Movie *m, const char *path, const char *method, const char *fmt, ...)
{
    char args[1024];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(args, sizeof args, fmt, ap);
    va_end(ap);
    const char *r = mugfx_invoke(m->g, path, method, args);
    logf_(m->game, "%s <- %s.%s(%s) = %s", m->name, path, method, args, r ? r : "(queued)");
    return r;
}

static void slot_states(Game *G)
{
    if (!G->inv_path[0])
        return;
    /* The movie colours a cell's background by state (frames of
     * MuItemSlot_icons01); the client informs it through the status refresh
     * 0x00c94193.  Occupied cells: state 2, free: 1 (prototype choice). */
    char list[512];
    size_t n = 0;
    for (int i = 0; i < G->grid.cols * G->grid.rows; i++)
        n += (size_t)snprintf(list + n, sizeof list - n, "%s%d", i ? "," : "", G->grid.cells[i] ? 2 : 1);
    invoke(&G->inv, G->inv_path, "SetSlotStateAll", "[0,\"%s\"]", list);
}

static void set_inventory(Game *G, int open)
{
    if (!G->inv_path[0])
        return;
    G->inv_open = open;
    invoke(&G->inv, G->inv_path, "SetVisible", "[%s]", open ? "true" : "false");
}

static void feed_hud(Game *G)
{
    if (!G->hud_path[0])
        return;
    double t = G->time_ms / 1000.0;
    int max_hp = 117918, max_mp = 18526, max_sd = 24000, max_ag = 9000;
    int hp = (int)(max_hp * (0.55 + 0.45 * sin(t * 0.9)));
    int mp = (int)(max_mp * (0.5 + 0.5 * cos(t * 0.6)));
    int sd = (int)(max_sd * (0.5 + 0.5 * sin(t * 1.3 + 1.0)));
    int ag = (int)(max_ag * (0.5 + 0.5 * sin(t * 0.4 + 2.0)));
    invoke(&G->hud, G->hud_path, "setHPMP",
           "[{\"isToxic\":%s,\"hp\":%d,\"maxHp\":%d,\"mp\":%d,\"maxMp\":%d,\"Shield\":%d,\"ShieldMax\":%d,"
           "\"SkillMana\":%d,\"SkillManaMax\":%d}]",
           fmod(t, 12.0) > 9.0 ? "true" : "false", hp, max_hp, mp, max_mp, sd, max_sd, ag, max_ag);
}

/* ---- movie -> game ------------------------------------------------------ */

static void inventory_click(Game *G, int index)
{
    int cols = G->grid.cols;
    if (index < 0 || index >= cols * G->grid.rows)
        return;
    if (G->held < 0) {
        mu_grid_item *it = mu_grid_item_at(&G->grid, index);
        if (it && G->grid.cells[index]) {
            G->held = (int)(it - G->items);
            mu_grid_remove(&G->grid, it);
            logf_(G, "game: pick item %u (%dx%d) from cell %d", it->id, it->width, it->height, index);
        }
    } else {
        mu_grid_item *it = &G->items[G->held];
        int col = index % cols, row = index / cols;
        if (mu_grid_fits(&G->grid, col, row, it->width, it->height)) {
            mu_grid_place(&G->grid, col, row, it);
            logf_(G, "game: drop item %u at cell %d (%d,%d)", it->id, index, col, row);
            G->held = -1;
        } else {
            logf_(G, "game: item %u does not fit at cell %d", it->id, index);
        }
    }
    slot_states(G);
}

static const char *on_call(void *user, const char *name, const char *args)
{
    Movie *m = user;
    Game *G = m->game;
    G->calls++;
    logf_(G, "%s -> %s %s", m->name, name, args);
    double v[8];
    int n = json_numbers(args, v, 8);
    char s[128];
    if (m == &G->hud) {
        if (!strcmp(name, "main") && json_string(args, 0, s, sizeof s)) {
            if (!strcmp(s, "onLoad")) {
                char path[128];
                if (json_string(args, 1, path, sizeof path))
                    snprintf(G->hud_path, sizeof G->hud_path, "%s", path);
            } else if (!strcmp(s, "onHotKey")) {
                int key = (int)json_field(args, "keyCode", 0);
                if (key == 'I' || key == 'V')
                    set_inventory(G, !G->inv_open);
            }
        }
        return NULL;
    }
    if (!strcmp(name, "UIInit") && json_string(args, 0, s, sizeof s)) {
        snprintf(G->inv_uid, sizeof G->inv_uid, "%s", s);
        snprintf(G->inv_path, sizeof G->inv_path, "_level0.%s", s);
    } else if (!strcmp(name, "requestWindowPos") && n >= 2) {
        G->win_x = (float)v[0];
        G->win_y = (float)v[1];
    } else if (!strcmp(name, "requestSlotInfo") && n >= 5 && v[4] == 0) {
        G->slot_x = (float)v[0];
        G->slot_y = (float)v[1];
        G->slot_w = (float)v[2];
        G->slot_h = (float)v[3];
        G->have_slot = 1;
    } else if (!strcmp(name, "CloseWindow")) {
        set_inventory(G, 0);        /* queued: we are inside the movie */
    } else if (!strcmp(name, "requestItemSlotClick") && n >= 1) {
        inventory_click(G, (int)v[0]);
    } else if (!strcmp(name, "requestItemSlotOver") && n >= 1) {
        G->hover = (int)v[0];
    } else if (!strcmp(name, "requestItemSlotOut")) {
        G->hover = -1;
    }
    return NULL;
}

/* ---- setup ---------------------------------------------------------------- */

static int open_movie(Game *G, Movie *m, const char *dir, const char *name)
{
    char path[1024], err[512];
    snprintf(path, sizeof path, "%s/%s.swf", dir, name);
    m->name = name;
    m->game = G;
    m->g = mugfx_open(path, G->w, G->h, err, sizeof err);
    if (!m->g) {
        fprintf(stderr, "mu-gfx-window: %s: %s\n", path, err);
        return 0;
    }
    m->rgba = calloc((size_t)G->w * (size_t)G->h, 4);
    mugfx_set_callback(m->g, on_call, m);
    return 1;
}

static void setup_game(Game *G)
{
    mu_grid_construct(&G->grid);
    mu_grid_init(&G->grid, 1, 0, 0, 0, 8, 8, 0);   /* 0x00ab7277(1, 8, 8, 1): inventory page */
    static const int sizes[][2] = {{1, 3}, {2, 2}, {1, 1}, {2, 3}, {1, 2}, {1, 1}, {2, 2}, {1, 1}, {2, 4}};
    static const float rgb[][3] = {{.85f, .35f, .25f}, {.35f, .55f, .9f}, {.95f, .8f, .3f}, {.55f, .75f, .4f},
                                   {.7f, .45f, .85f}, {.3f, .8f, .8f}, {.9f, .55f, .2f}, {.8f, .8f, .8f},
                                   {.6f, .3f, .3f}};
    G->held = -1;
    G->hover = -1;
    for (int i = 0; i < (int)(sizeof sizes / sizeof sizes[0]) && i < MAX_ITEMS; i++) {
        mu_grid_item *it = &G->items[G->n_items];
        it->id = (uint32_t)(i + 1);
        it->code = 0x100 + i;
        it->width = (uint8_t)sizes[i][0];
        it->height = (uint8_t)sizes[i][1];
        int col, row;
        if (!mu_grid_find_free(&G->grid, it->width, it->height, &col, &row))
            continue;
        mu_grid_place(&G->grid, col, row, it);
        memcpy(G->item_rgb[G->n_items], rgb[i], sizeof rgb[i]);
        G->n_items++;
    }
}

static void init_movies(Game *G)
{
    mugfx_start(G->hud.g);
    mugfx_start(G->inv.g);
    /* main.gfx places its Frame.Main clip as "mc" on the root timeline; the
     * client learns the path from the clip's EventCall("onLoad", targetPath),
     * which the UI loader triggers through onFileLoad.  The prototype plays
     * that loader (prototype choice). */
    invoke(&G->hud, "_level0.mc", "onFileLoad", "[]");
    if (G->hud_path[0]) {
        invoke(&G->hud, G->hud_path, "InitMenuInfo",
               "[{\"IngameShop\":{\"keyCode\":88,\"key\":\"X\",\"label\":\"In-game shop\"},"
               "\"CharacterInfo\":{\"keyCode\":67,\"key\":\"C\",\"label\":\"Character\"},"
               "\"Inventory\":{\"label\":\"Inventory\",\"subMenu\":[{\"keyCode\":73,\"key\":\"I\",\"label\":\"Inventory\"},"
               "{\"keyCode\":75,\"key\":\"K\",\"label\":\"Gremory case\"}]},"
               "\"Quest\":{\"keyCode\":84,\"key\":\"T\",\"label\":\"Quest\"},"
               "\"Community\":{\"label\":\"Community\",\"subMenu\":[{\"keyCode\":70,\"key\":\"F\",\"label\":\"Friends\"}]},"
               "\"System\":{\"label\":\"System\",\"subMenu\":[{\"keyCode\":27,\"key\":\"ESC\",\"label\":\"System\"}]}}]");
        feed_hud(G);
    }
    if (G->inv_path[0]) {
        invoke(&G->inv, G->inv_path, "InitText",
               "[{\"Title\":\"Inventory\",\"Zen\":\"<font color='#FFCC19'>182,790,999</font>\","
               "\"Ruud\":\"<font color='#FFCC19'>411,067</font>\",\"Artifact\":\"Artifact\","
               "\"PrivateStore\":\"Personal S\",\"ExtensionBag\":\"Expanded\",\"Repair\":\"Repair\","
               "\"Divide\":\"Divide\",\"Disassemble\":\"Disassemb\",\"Bundle\":\"Bundle\"}]");
        /* Right-aligned like the live client window (Align_RightCenter = 4). */
        invoke(&G->inv, G->inv_path, "SetAlign", "[4]");
        invoke(&G->inv, G->inv_path, "SetWindowSize", "[%d,%d]", G->w, G->h - 120);
        /* Gap between cells: the second slot's offset minus the cell width
         * (the movie reports only slot 0; prototype choice, not a client fact). */
        char p0[160], p1[160];
        snprintf(p0, sizeof p0, "%s.mcInventoryFrame.isSlot0._x", G->inv_path);
        snprintf(p1, sizeof p1, "%s.mcInventoryFrame.isSlot1._x", G->inv_path);
        const char *a = mugfx_get_variable(G->inv.g, p0);
        double x0 = a ? atof(a) : 0;
        const char *b = mugfx_get_variable(G->inv.g, p1);
        double x1 = b ? atof(b) : 0;
        snprintf(p1, sizeof p1, "%s.mcInventoryFrame.isSlot8._y", G->inv_path);
        snprintf(p0, sizeof p0, "%s.mcInventoryFrame.isSlot0._y", G->inv_path);
        a = mugfx_get_variable(G->inv.g, p0);
        double y0 = a ? atof(a) : 0;
        b = mugfx_get_variable(G->inv.g, p1);
        double y8 = b ? atof(b) : 0;
        G->gap_x = (float)(x1 - x0) - G->slot_w;
        G->gap_y = (float)(y8 - y0) - G->slot_h;
        logf_(G, "game: slot origin (%.1f, %.1f) cell %.1fx%.1f gap %.2f/%.2f", G->slot_x, G->slot_y, G->slot_w,
              G->slot_h, G->gap_x, G->gap_y);
        slot_states(G);
    }
}

/* ---- item stand-ins through the reconstructed slot pass ------------------- */

typedef struct ItemRect { float x, y, w, h; int item; } ItemRect;
typedef struct RectList { ItemRect r[MAX_ITEMS]; int n; Game *G; } RectList;

static void emit_rect(void *user, const mu_slot_call *call)
{
    RectList *L = user;
    Game *G = L->G;
    if (L->n >= MAX_ITEMS)
        return;
    /* 640 x 480 units back to window pixels (0x0184a18f, top-left origin here). */
    ItemRect *r = &L->r[L->n++];
    r->x = call->x / mu_gfx_rate_x(G->w);
    r->y = call->y / mu_gfx_rate_y(G->h);
    r->w = call->w / mu_gfx_rate_x(G->w);
    r->h = call->h / mu_gfx_rate_y(G->h);
    r->item = (int)(call->item - G->items);
}

static int item_rects(Game *G, RectList *L)
{
    L->n = 0;
    L->G = G;
    if (!G->have_slot)
        return 0;
    mu_slot_page page = {&G->grid, G->slot_x, G->slot_y, G->slot_w, G->slot_h, G->gap_x, G->gap_y};
    mu_slot_frame frame = {G->inv_open, MU_ALIGN_TOP_LEFT, G->win_x, G->win_y, 1.0f, 1.0f, &page, 1, 1};
    return mu_slot_pass(&frame, G->w, G->h, mu_gfx_rate_x(G->w), mu_gfx_rate_y(G->h), NULL, emit_rect, L);
}

/* ---- frame loop ----------------------------------------------------------- */

static void advance(Game *G, double dt)
{
    G->time_ms += dt;
    while (G->time_ms >= G->next_step_ms) {     /* the client's 40 ms logic step */
        G->next_step_ms += 40.0;
        G->steps++;
        feed_hud(G);
    }
    Movie *ms[2] = {&G->hud, &G->inv};
    for (int i = 0; i < 2; i++) {
        double t = now_ms();
        mugfx_advance(ms[i]->g, dt);
        ms[i]->advance_ms += now_ms() - t;
    }
}

static void render_movies(Game *G, int force)
{
    Movie *ms[2] = {&G->hud, &G->inv};
    for (int i = 0; i < 2; i++) {
        Movie *m = ms[i];
        if (m == &G->inv && !G->inv_open)
            continue;   /* the GFx manager does not display hidden windows */
        if (!force && m->has_frame && !mugfx_needs_render(m->g))
            continue;
        if (mugfx_render(m->g, m->rgba, (size_t)G->w * (size_t)G->h * 4) == 0) {
            MuGfxStats st;
            mugfx_stats(m->g, &st);
            m->render_ms += st.last_render_ms;
            m->capture_ms += st.last_capture_ms;
            m->renders++;
            m->has_frame = 2;   /* 2 = needs upload */
        }
    }
}

static void background_pixel(Game *G, int x, int y, uint8_t *px)
{
    float fy = (float)y / (float)G->h, fx = (float)x / (float)G->w;
    float checker = (((x / 64) + (y / 64)) & 1) ? 0.04f : 0.0f;
    px[0] = (uint8_t)(255 * (0.20f + 0.15f * fy + checker));
    px[1] = (uint8_t)(255 * (0.09f + 0.05f * fx + checker));
    px[2] = (uint8_t)(255 * (0.12f + 0.10f * (1 - fy) + checker));
    px[3] = 255;
}

static void blend(uint8_t *dst, const uint8_t *src)
{
    unsigned a = src[3];
    for (int c = 0; c < 3; c++)
        dst[c] = (uint8_t)((src[c] * a + dst[c] * (255 - a)) / 255);
}

static void composite_cpu(Game *G, uint8_t *out)
{
    for (int y = 0; y < G->h; y++)
        for (int x = 0; x < G->w; x++)
            background_pixel(G, x, y, out + ((size_t)y * G->w + x) * 4);
    Movie *ms[2] = {&G->hud, &G->inv};
    for (int i = 0; i < 2; i++) {
        if (!ms[i]->has_frame || (ms[i] == &G->inv && !G->inv_open))
            continue;
        size_t n = (size_t)G->w * G->h;
        for (size_t p = 0; p < n; p++)
            if (ms[i]->rgba[p * 4 + 3])
                blend(out + p * 4, ms[i]->rgba + p * 4);
    }
    RectList L;
    item_rects(G, &L);
    for (int i = 0; i <= L.n; i++) {
        float rx, ry, rw, rh;
        const float *rgb;
        if (i < L.n) {
            rx = L.r[i].x; ry = L.r[i].y; rw = L.r[i].w; rh = L.r[i].h;
            rgb = G->item_rgb[L.r[i].item];
        } else if (G->held >= 0 && G->inv_open) {
            rw = G->items[G->held].width * G->slot_w;
            rh = G->items[G->held].height * G->slot_h;
            rx = (float)G->mouse_x - rw / 2;
            ry = (float)G->mouse_y - rh / 2;
            rgb = G->item_rgb[G->held];
        } else {
            break;
        }
        for (int y = (int)ry + 2; y < (int)(ry + rh) - 2; y++)
            for (int x = (int)rx + 2; x < (int)(rx + rw) - 2; x++) {
                if (x < 0 || y < 0 || x >= G->w || y >= G->h)
                    continue;
                int edge = y < (int)ry + 4 || x < (int)rx + 4 || y >= (int)(ry + rh) - 4 || x >= (int)(rx + rw) - 4;
                uint8_t src[4] = {(uint8_t)(255 * rgb[0] * (edge ? 0.6f : 1)), (uint8_t)(255 * rgb[1] * (edge ? 0.6f : 1)),
                                  (uint8_t)(255 * rgb[2] * (edge ? 0.6f : 1)), 200};
                blend(out + ((size_t)y * G->w + x) * 4, src);
            }
    }
}

static void draw_gl(Game *G)
{
    glViewport(0, 0, G->w, G->h);
    glMatrixMode(GL_PROJECTION);
    glLoadIdentity();
    glOrtho(0, G->w, G->h, 0, -1, 1);
    glMatrixMode(GL_MODELVIEW);
    glLoadIdentity();
    glDisable(GL_DEPTH_TEST);
    glDisable(GL_TEXTURE_2D);
    glBegin(GL_QUADS);
    glColor3f(0.20f, 0.09f, 0.22f); glVertex2f(0, 0); glVertex2f((float)G->w, 0);
    glColor3f(0.35f, 0.14f, 0.12f); glVertex2f((float)G->w, (float)G->h); glVertex2f(0, (float)G->h);
    glEnd();
    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    Movie *ms[2] = {&G->hud, &G->inv};
    for (int i = 0; i < 2; i++) {
        Movie *m = ms[i];
        if (!m->has_frame || (m == &G->inv && !G->inv_open))
            continue;
        if (!m->tex) {
            glGenTextures(1, &m->tex);
            glBindTexture(GL_TEXTURE_2D, m->tex);
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, G->w, G->h, 0, GL_RGBA, GL_UNSIGNED_BYTE, NULL);
        }
        glBindTexture(GL_TEXTURE_2D, m->tex);
        if (m->has_frame == 2) {
            double t = now_ms();
            glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, G->w, G->h, GL_RGBA, GL_UNSIGNED_BYTE, m->rgba);
            m->upload_ms += now_ms() - t;
            m->has_frame = 1;
        }
        glEnable(GL_TEXTURE_2D);
        glColor4f(1, 1, 1, 1);
        glBegin(GL_QUADS);
        glTexCoord2f(0, 0); glVertex2f(0, 0);
        glTexCoord2f(1, 0); glVertex2f((float)G->w, 0);
        glTexCoord2f(1, 1); glVertex2f((float)G->w, (float)G->h);
        glTexCoord2f(0, 1); glVertex2f(0, (float)G->h);
        glEnd();
        glDisable(GL_TEXTURE_2D);
    }
    RectList L;
    item_rects(G, &L);
    for (int i = 0; i <= L.n; i++) {
        float rx, ry, rw, rh;
        const float *rgb;
        if (i < L.n) {
            rx = L.r[i].x; ry = L.r[i].y; rw = L.r[i].w; rh = L.r[i].h;
            rgb = G->item_rgb[L.r[i].item];
        } else if (G->held >= 0 && G->inv_open) {
            rw = G->items[G->held].width * G->slot_w;
            rh = G->items[G->held].height * G->slot_h;
            rx = (float)G->mouse_x - rw / 2;
            ry = (float)G->mouse_y - rh / 2;
            rgb = G->item_rgb[G->held];
        } else {
            break;
        }
        glColor4f(rgb[0], rgb[1], rgb[2], 0.8f);
        glBegin(GL_QUADS);
        glVertex2f(rx + 2, ry + 2); glVertex2f(rx + rw - 2, ry + 2);
        glVertex2f(rx + rw - 2, ry + rh - 2); glVertex2f(rx + 2, ry + rh - 2);
        glEnd();
    }
    glDisable(GL_BLEND);
}

/* ---- scripted demo (headless and --script) -------------------------------- */

typedef struct Step { double at_ms; const char *what; } Step;

static void slot_center(Game *G, int index, double *x, double *y)
{
    int col = index % G->grid.cols, row = index / G->grid.cols;
    *x = G->win_x + G->slot_x + col * (G->slot_w + G->gap_x) + G->slot_w / 2;
    *y = G->win_y + G->slot_y + row * (G->slot_h + G->gap_y) + G->slot_h / 2;
}

static void mouse(Game *G, int kind, double x, double y)
{
    G->mouse_x = x;
    G->mouse_y = y;
    if (kind == 0) {
        if (G->inv_open)
            mugfx_mouse(G->inv.g, 0, 0, x, y);
        mugfx_mouse(G->hud.g, 0, 0, x, y);
        return;
    }
    /* Clicks go to the inventory when the cursor is over its frame, else the bar. */
    double fw = 0, fh = 0;
    if (G->inv_open) {
        char p[160];
        snprintf(p, sizeof p, "%s.mcInventoryFrame._width", G->inv_path);
        const char *s = mugfx_get_variable(G->inv.g, p);
        fw = s ? atof(s) : 0;
        snprintf(p, sizeof p, "%s.mcInventoryFrame._height", G->inv_path);
        s = mugfx_get_variable(G->inv.g, p);
        fh = s ? atof(s) : 0;
    }
    int over_inv = G->inv_open && x >= G->win_x && x < G->win_x + fw && y >= G->win_y && y < G->win_y + fh;
    mugfx_mouse(over_inv ? G->inv.g : G->hud.g, kind, 0, x, y);
}

static void script_step(Game *G, int k, char *shot, size_t cap)
{
    double x, y;
    shot[0] = 0;
    switch (k) {
    case 0: snprintf(shot, cap, "1-hud"); break;
    case 1:
        logf_(G, "script: hotkey I (as the bottom bar's onHotKey would)");
        set_inventory(G, 1);
        break;
    case 2: snprintf(shot, cap, "2-inventory-open"); break;
    case 3: slot_center(G, 9, &x, &y); mouse(G, 0, x, y); break;     /* hover the 2x2 item */
    case 4: slot_center(G, 9, &x, &y); mouse(G, 1, x, y); mouse(G, 2, x, y); break;
    case 5: slot_center(G, 41, &x, &y); mouse(G, 0, x, y); snprintf(shot, cap, "3-item-held"); break;
    case 6: slot_center(G, 41, &x, &y); mouse(G, 1, x, y); mouse(G, 2, x, y); break;
    case 7: snprintf(shot, cap, "4-item-moved"); break;
    case 8: {
        char p[160];
        snprintf(p, sizeof p, "%s.mcInventoryFrame.btnClose._x", G->inv_path);
        const char *s = mugfx_get_variable(G->inv.g, p);
        double bx = s ? atof(s) : 0;
        snprintf(p, sizeof p, "%s.mcInventoryFrame.btnClose._y", G->inv_path);
        s = mugfx_get_variable(G->inv.g, p);
        double by = s ? atof(s) : 0;
        snprintf(p, sizeof p, "%s.mcInventoryFrame.btnClose._width", G->inv_path);
        s = mugfx_get_variable(G->inv.g, p);
        double bw = s ? atof(s) : 0;
        /* The clip's bounds include a wide transparent hit area; aim at its
         * top-left icon (prototype choice). */
        x = G->win_x + bx + 10;
        y = G->win_y + by + 10;
        logf_(G, "script: close button local (%.1f, %.1f) w %.1f; click at (%.0f, %.0f)", bx, by, bw, x, y);
        mouse(G, 0, x, y);
        mouse(G, 1, x, y);
        mouse(G, 2, x, y);
        break;
    }
    case 9: snprintf(shot, cap, "5-closed"); break;
    }
}

static const double SCRIPT_AT[] = {400, 600, 1400, 1600, 1800, 2300, 2500, 3000, 3200, 4000};
#define SCRIPT_STEPS ((int)(sizeof SCRIPT_AT / sizeof SCRIPT_AT[0]))

/* ---- main ----------------------------------------------------------------- */

int main(int argc, char **argv)
{
    const char *dir = NULL, *out_dir = NULL, *log_path = NULL;
    int headless = 0, script = 0, bench = 0, frames = 0, baseline = 0, open_inv = 0;
    static Game G;
    G.w = 1280;
    G.h = 800;
    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--gfx") && i + 1 < argc) dir = argv[++i];
        else if (!strcmp(argv[i], "--out-dir") && i + 1 < argc) out_dir = argv[++i];
        else if (!strcmp(argv[i], "--log") && i + 1 < argc) log_path = argv[++i];
        else if (!strcmp(argv[i], "--size") && i + 1 < argc) sscanf(argv[++i], "%dx%d", &G.w, &G.h);
        else if (!strcmp(argv[i], "--frames") && i + 1 < argc) frames = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--headless")) headless = 1;
        else if (!strcmp(argv[i], "--script")) script = 1;
        else if (!strcmp(argv[i], "--bench")) bench = 1;
        else if (!strcmp(argv[i], "--baseline")) baseline = 1;
        else if (!strcmp(argv[i], "--open")) open_inv = 1;        /* inventory open from the start */   /* measure the window without movie renders */
        else {
            fprintf(stderr, "usage: %s --gfx DIR [--size WxH] [--headless --out-dir DIR] [--script] "
                            "[--frames N] [--bench] [--baseline] [--open] [--log FILE]\n", argv[0]);
            return 2;
        }
    }
    if (!dir) {
        fprintf(stderr, "mu-gfx-window: --gfx DIR is required\n");
        return 2;
    }
    G.log = log_path ? fopen(log_path, "w") : (headless ? stdout : NULL);
    char adapter[256];
    mugfx_adapter(adapter, sizeof adapter);
    fprintf(stderr, "mu-gfx-window: Ruffle adapter %s, %dx%d\n", adapter, G.w, G.h);

    SDL_Window *win = NULL;
    SDL_GLContext ctx = NULL;
    if (!headless) {
        if (SDL_Init(SDL_INIT_VIDEO) != 0) {
            fprintf(stderr, "SDL_Init: %s\n", SDL_GetError());
            return 1;
        }
        SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 2);
        SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 1);
        SDL_GL_SetAttribute(SDL_GL_DOUBLEBUFFER, 1);
        win = SDL_CreateWindow("mu-gfx-window (GFx movies via Ruffle)", SDL_WINDOWPOS_CENTERED,
                               SDL_WINDOWPOS_CENTERED, G.w, G.h, SDL_WINDOW_OPENGL);
        ctx = win ? SDL_GL_CreateContext(win) : NULL;
        if (!ctx) {
            fprintf(stderr, "SDL window/GL: %s\n", SDL_GetError());
            return 1;
        }
        SDL_GL_SetSwapInterval(bench ? 0 : 1);
    }
    if (!open_movie(&G, &G.hud, dir, "main") || !open_movie(&G, &G.inv, dir, "InventoryFrame"))
        return 1;
    setup_game(&G);
    init_movies(&G);
    if (open_inv)
        set_inventory(&G, 1);
    if (!G.hud_path[0] || !G.inv_path[0])
        fprintf(stderr, "mu-gfx-window: warning: movie paths not reported (hud '%s', inventory '%s')\n",
                G.hud_path, G.inv_path);

    uint8_t *shot = headless ? malloc((size_t)G.w * G.h * 4) : NULL;
    int next_script = 0, running = 1;
    long frame = 0;
    double dt = 1000.0 / 60.0, last = now_ms(), wall0 = now_ms();
    struct rusage ru0;
    getrusage(RUSAGE_SELF, &ru0);
    if (headless && !frames)
        frames = script ? (int)(SCRIPT_AT[SCRIPT_STEPS - 1] / dt) + 2 : 120;
    double frame_ms_total = 0;
    while (running) {
        double t0 = now_ms();
        if (!headless) {
            SDL_Event e;
            while (SDL_PollEvent(&e)) {
                if (e.type == SDL_QUIT || (e.type == SDL_KEYDOWN && e.key.keysym.sym == SDLK_ESCAPE))
                    running = 0;
                else if (e.type == SDL_KEYDOWN && e.key.keysym.sym == SDLK_i)
                    set_inventory(&G, !G.inv_open);
                else if (e.type == SDL_MOUSEMOTION)
                    mouse(&G, 0, e.motion.x, e.motion.y);
                else if (e.type == SDL_MOUSEBUTTONDOWN && e.button.button == SDL_BUTTON_LEFT)
                    mouse(&G, 1, e.button.x, e.button.y);
                else if (e.type == SDL_MOUSEBUTTONUP && e.button.button == SDL_BUTTON_LEFT)
                    mouse(&G, 2, e.button.x, e.button.y);
            }
            double now = now_ms();
            dt = headless || bench ? 1000.0 / 60.0 : now - last;
            last = now;
        }
        advance(&G, dt);
        char name[64] = "";
        while ((script || headless) && next_script < SCRIPT_STEPS && G.time_ms >= SCRIPT_AT[next_script]) {
            if (script || headless)
                script_step(&G, next_script, name, sizeof name);
            next_script++;
            if (name[0])
                break;
        }
        if (!baseline)
            render_movies(&G, bench);
        if (headless) {
            if (name[0] && out_dir) {
                char path[1024];
                composite_cpu(&G, shot);
                snprintf(path, sizeof path, "%s/%s.png", out_dir, name);
                mu_png_write(path, shot, G.w, G.h);
                fprintf(stderr, "mu-gfx-window: wrote %s\n", path);
            }
        } else {
            draw_gl(&G);
            SDL_GL_SwapWindow(win);
        }
        frame_ms_total += now_ms() - t0;
        frame++;
        if (frames && frame >= frames)
            running = 0;
    }
    struct rusage ru1;
    getrusage(RUSAGE_SELF, &ru1);
    double wall = now_ms() - wall0;
    double cpu = (ru1.ru_utime.tv_sec - ru0.ru_utime.tv_sec + ru1.ru_stime.tv_sec - ru0.ru_stime.tv_sec) * 1000.0 +
                 (ru1.ru_utime.tv_usec - ru0.ru_utime.tv_usec + ru1.ru_stime.tv_usec - ru0.ru_stime.tv_usec) / 1000.0;
    Movie *ms[2] = {&G.hud, &G.inv};
    printf("{\"frames\": %ld, \"wall_ms\": %.1f, \"cpu_ms\": %.1f, \"cpu_per_frame_ms\": %.3f, "
           "\"frame_ms\": %.3f, \"logic_steps\": %ld, \"external_calls\": %ld, \"adapter\": \"%s\", \"movies\": {",
           frame, wall, cpu, cpu / (double)frame, frame_ms_total / (double)frame, G.steps, G.calls, adapter);
    for (int i = 0; i < 2; i++) {
        Movie *m = ms[i];
        double r = m->renders ? (double)m->renders : 1;
        printf("%s\"%s\": {\"renders\": %ld, \"advance_ms\": %.3f, \"render_ms\": %.3f, \"capture_ms\": %.3f, "
               "\"upload_ms\": %.3f}", i ? ", " : "", m->name, m->renders, m->advance_ms / (double)frame,
               m->render_ms / r, m->capture_ms / r, m->upload_ms / r);
    }
    printf("}, \"inventory_open\": %d, \"held\": %d}\n", G.inv_open, G.held);
    mugfx_close(G.hud.g);
    mugfx_close(G.inv.g);
    if (win) {
        SDL_GL_DeleteContext(ctx);
        SDL_DestroyWindow(win);
        SDL_Quit();
    }
    return 0;
}
