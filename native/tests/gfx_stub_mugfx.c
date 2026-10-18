/* A stand-in libmugfx for the GFx layer's portable tests (NATIVE-GFX-002).
 *
 * Implements the mugfx ABI 2 without Ruffle: each "movie" is a small state
 * machine that answers the layer the way the converted client movies do
 * (static readings of their ActionScript, docs/research/native-gfx.md):
 * InventoryFrame reports UIInit/requestSlotInfo/requestWindowPos and turns
 * clicks on its 8 x 8 page into requestItemSlotClick/ClickR/Over/Out; main
 * reports onLoad on onFileLoad and onHotKey from onKeyUp; chat reports
 * onLoad, keeps a text buffer and reports onEnterText from onPushText; the
 * other windows report UIInit.  Calls made from inside a callback are queued
 * and run afterwards, as mugfx does.  Every invoke is appended to the file
 * named by $MUGFX_STUB_LOG.  Synthetic: no client data. */
#define _POSIX_C_SOURCE 200809L
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../gfx/mugfx/include/mugfx.h"

typedef struct pending { MuGfx *g; char path[128], method[64], *args; } pending;

struct MuGfx {
    char name[64];
    mugfx_callback cb;
    void *user;
    int stage_w, stage_h, vx, vy, vw, vh;   /* stage and view in points */
    double scale;                          /* viewport pixels per point */
    int visible, rendered;
    float win_x, win_y;
    int hover, press, last_vk, edit;
    char text[256];
    char reply[512];
    uint64_t calls;
};

static int in_cb;
static pending queue[64];
static int nqueue;

static void logline(const char *fmt, const char *a, const char *b, const char *c, const char *d)
{
    const char *path = getenv("MUGFX_STUB_LOG");
    if (!path)
        return;
    FILE *f = fopen(path, "a");
    if (!f)
        return;
    fprintf(f, fmt, a, b, c, d);
    fputc('\n', f);
    fclose(f);
}

static void call(MuGfx *g, const char *name, const char *args)
{
    if (!g->cb)
        return;
    g->calls++;
    int was = in_cb;
    in_cb = 1;
    g->cb(g->user, name, args);
    in_cb = was;
}

static void callf(MuGfx *g, const char *name, const char *fmt, double a, double b)
{
    char args[256];
    snprintf(args, sizeof args, fmt, a, b);
    call(g, name, args);
}

static int is(const MuGfx *g, const char *name) { return !strcmp(g->name, name); }

/* Content rectangle of a movie in stage pixels (what getBounds reports). */
static void bounds(const MuGfx *g, float r[4])
{
    if (is(g, "InventoryFrame")) { r[0] = g->win_x; r[1] = g->win_y; r[2] = 332; r[3] = 639; }
    else if (is(g, "main")) { r[0] = 179; r[1] = 658; r[2] = 921; r[3] = 145; }
    else if (is(g, "chat")) { r[0] = 0; r[1] = 562; r[2] = 610; r[3] = 130; }
    else if (is(g, "CharacterInfoFrame")) { r[0] = 0; r[1] = 0; r[2] = 350; r[3] = 640; }
    else { r[0] = 900; r[1] = 300; r[2] = 200; r[3] = 100; }
}

static void stage_point(const MuGfx *g, double x, double y, double *sx, double *sy)
{
    *sx = x / g->scale + g->vx;
    *sy = y / g->scale + g->vy;
}

static int cell_at(const MuGfx *g, double sx, double sy)
{
    double cx = (sx - g->win_x - 24.75) / 26.0, cy = (sy - g->win_y - 370.0) / 26.0;
    if (cx < 0 || cy < 0 || cx >= 8 || cy >= 8)
        return -1;
    return (int)cy * 8 + (int)cx;
}

static const char *run_invoke(MuGfx *g, const char *path, const char *method, const char *args)
{
    logline("%s %s.%s %s", g->name, path, method, args);
    snprintf(g->reply, sizeof g->reply, "null");
    if (!strcmp(method, "getBounds")) {
        float r[4];
        bounds(g, r);
        snprintf(g->reply, sizeof g->reply, "{\"xMax\":%.1f,\"xMin\":%.1f,\"yMax\":%.1f,\"yMin\":%.1f}", r[0] + r[2],
                 r[0], r[1] + r[3], r[1]);
    } else if (is(g, "main")) {
        if (!strcmp(method, "onFileLoad"))
            call(g, "main", "[\"onLoad\",\"_level0.mc\"]");
        else if (!strcmp(method, "onKeyUp") && (g->last_vk == 73 || g->last_vk == 67 || g->last_vk == 27))
            callf(g, "main", "[\"onHotKey\",{\"keyCode\":%.1f}]", g->last_vk, 0);
    } else if (is(g, "chat")) {
        if (!strcmp(method, "onFileLoad"))
            call(g, "chat", "[\"onLoad\",\"_level0.mc\"]");
        else if (!strcmp(method, "getText"))
            snprintf(g->reply, sizeof g->reply, "\"%s\"", g->text);
        else if (!strcmp(method, "OpenEditText")) {
            g->edit = 1;
            call(g, "fscommand", "[\"TextInput\",\"focusIn\"]");
        } else if (!strcmp(method, "CloseEditText")) {
            g->edit = 0;
            g->text[0] = 0;
            call(g, "fscommand", "[\"TextInput\",\"focusOut\"]");
        } else if (!strcmp(method, "onPushText")) {
            char msg[400];
            snprintf(msg, sizeof msg, "[\"onEnterText\",{\"text\":\"%s\",\"type\":1.0,\"wisper\":\"\"}]", g->text);
            g->text[0] = 0;
            call(g, "chat", msg);
        }
    } else if (is(g, "InventoryFrame")) {
        if (!strcmp(method, "SetAlign")) {
            g->win_x = (float)(g->stage_w - 332);
            g->win_y = 20;
            callf(g, "requestWindowPos", "[%.1f,%.1f]", g->win_x, g->win_y);
        } else if (!strcmp(method, "SetVisible")) {
            g->visible = strstr(args, "true") != NULL;
        }
    } else if (!strcmp(method, "SetVisible")) {
        g->visible = strstr(args, "true") != NULL;
    }
    return g->reply;
}

static void drain(void)
{
    while (!in_cb && nqueue) {
        pending p = queue[0];
        memmove(queue, queue + 1, (size_t)(nqueue - 1) * sizeof queue[0]);
        nqueue--;
        run_invoke(p.g, p.path, p.method, p.args);
        free(p.args);
    }
}

int mugfx_abi_version(void) { return MUGFX_ABI_VERSION; }

void mugfx_adapter(char *out, size_t cap) { snprintf(out, cap, "stub"); }

MuGfx *mugfx_open(const char *path, int width, int height, char *err, size_t cap)
{
    MuGfx *g = calloc(1, sizeof *g);
    if (!g) {
        snprintf(err, cap, "out of memory");
        return NULL;
    }
    const char *base = strrchr(path, '/');
    snprintf(g->name, sizeof g->name, "%s", base ? base + 1 : path);
    char *dot = strstr(g->name, ".swf");
    if (dot)
        *dot = 0;
    g->stage_w = g->vw = width;
    g->stage_h = g->vh = height;
    g->scale = 1.0;
    g->hover = g->press = -1;
    return g;
}

MuGfx *mugfx_open_shared(const char *path, int width, int height, char *err, size_t cap)
{
    (void)path; (void)width; (void)height;
    snprintf(err, cap, "stub: no IOSurface");
    return NULL;
}

void mugfx_close(MuGfx *g) { free(g); }

void mugfx_set_callback(MuGfx *g, mugfx_callback cb, void *user)
{
    g->cb = cb;
    g->user = user;
}

void mugfx_start(MuGfx *g)
{
    if (is(g, "InventoryFrame")) {
        call(g, "UIInit", "[\"g_mcInventory\"]");
        call(g, "requestSlotInfo", "[24.75,370.0,26.0,26.0,0.0]");
        g->win_x = 348;
        g->win_y = 40;
        call(g, "requestWindowPos", "[348.0,40.0]");
    } else if (is(g, "InfoPopup")) {
        call(g, "UIInit", "[\"g_mcInfoPopup\"]");
    } else if (is(g, "CharacterInfoFrame")) {
        call(g, "UIInit", "[\"g_CharacterInfoFrame\"]");
    }
    drain();
}

void mugfx_advance(MuGfx *g, double dt) { (void)g; (void)dt; drain(); }

int mugfx_needs_render(MuGfx *g) { return !g->rendered; }

int mugfx_render(MuGfx *g, uint8_t *rgba, size_t cap)
{
    size_t need = (size_t)(g->vw * g->scale) * (size_t)(g->vh * g->scale) * 4;
    if (cap < need)
        return -2;
    memset(rgba, 0, need);
    g->rendered = 1;
    return 0;
}

int mugfx_render_shared(MuGfx *g, int wait) { (void)g; (void)wait; return -2; }

void mugfx_gpu_wait(void) {}

void *mugfx_iosurface(MuGfx *g, int *w, int *h, uint32_t *seed) { (void)g; (void)w; (void)h; (void)seed; return NULL; }

const char *mugfx_invoke(MuGfx *g, const char *path, const char *method, const char *args)
{
    if (in_cb) {
        if (nqueue < 64) {
            pending *p = &queue[nqueue++];
            p->g = g;
            snprintf(p->path, sizeof p->path, "%s", path);
            snprintf(p->method, sizeof p->method, "%s", method);
            p->args = strdup(args ? args : "[]");
        }
        return NULL;
    }
    const char *r = run_invoke(g, path, method, args ? args : "[]");
    static char copy[512];
    snprintf(copy, sizeof copy, "%s", r);
    drain();
    return copy;
}

int mugfx_set_variable(MuGfx *g, const char *path, const char *value) { (void)g; (void)path; (void)value; return 0; }

const char *mugfx_get_variable(MuGfx *g, const char *path)
{
    if (strstr(path, "isSlot0._x")) return "24.75";
    if (strstr(path, "isSlot1._x")) return "50.75";
    if (strstr(path, "isSlot0._y")) return "370";
    if (strstr(path, "isSlot8._y")) return "396";
    (void)g;
    return "null";
}

int mugfx_hit_test(MuGfx *g, double x, double y)
{
    double sx, sy;
    stage_point(g, x, y, &sx, &sy);
    float r[4];
    bounds(g, r);
    if (is(g, "InventoryFrame") && !g->visible)
        return 0;
    if (is(g, "chat") && !g->edit)
        return 0;   /* the chat view is hitTestDisable while not editing */
    return sx >= r[0] && sy >= r[1] && sx < r[0] + r[2] && sy < r[1] + r[3];
}

int mugfx_mouse(MuGfx *g, int kind, int button, double x, double y)
{
    double sx, sy;
    stage_point(g, x, y, &sx, &sy);
    if (!is(g, "InventoryFrame") || !g->visible) {
        drain();
        return 0;
    }
    int cell = cell_at(g, sx, sy);
    if (kind == 0 && cell != g->hover) {
        if (g->hover >= 0)
            callf(g, "requestItemSlotOut", "[%.1f]", g->hover, 0);
        if (cell >= 0)
            callf(g, "requestItemSlotOver", "[%.1f]", cell, 0);
        g->hover = cell;
    } else if (kind == 1) {
        g->press = cell;
        if (cell < 0 && sx >= g->win_x + 300 && sy < g->win_y + 30)
            g->press = 1000;   /* the close button */
    } else if (kind == 2) {
        if (g->press == 1000 && sx >= g->win_x + 300 && sy < g->win_y + 30)
            call(g, "CloseWindow", "[]");
        else if (cell >= 0 && cell == g->press)
            callf(g, button == 1 ? "requestItemSlotClickR" : "requestItemSlotClick", "[%.1f]", cell, 0);
        g->press = -1;
    }
    drain();
    return 1;
}

int mugfx_cursor(MuGfx *g) { return g->hover >= 0 ? 1 : 0; }

int mugfx_key(MuGfx *g, int kind, int vk, uint32_t cp, int mods)
{
    (void)cp; (void)mods;
    if (kind == 0)
        g->last_vk = vk;
    if (kind == 0 && vk == 8 && g->edit && g->text[0])
        g->text[strlen(g->text) - 1] = 0;
    return 0;
}

int mugfx_text(MuGfx *g, const char *utf8)
{
    if (!g->edit)
        return 0;
    strncat(g->text, utf8, sizeof g->text - strlen(g->text) - 1);
    return 1;
}

int mugfx_text_focus(MuGfx *g) { return g->edit; }

int mugfx_set_view(MuGfx *g, int stage_w, int stage_h, int x, int y, int w, int h, double scale)
{
    g->scale = scale > 0 ? scale : 1.0;
    g->stage_w = stage_w;
    g->stage_h = stage_h;
    if (w > 0 && h > 0) {
        g->vx = x; g->vy = y; g->vw = w; g->vh = h;
    } else {
        g->vx = g->vy = 0; g->vw = stage_w; g->vh = stage_h;
    }
    g->rendered = 0;
    return 0;
}

void mugfx_size(MuGfx *g, int *w, int *h)
{
    if (w) *w = (int)(g->vw * g->scale);
    if (h) *h = (int)(g->vh * g->scale);
}

void mugfx_stats(MuGfx *g, MuGfxStats *out)
{
    memset(out, 0, sizeof *out);
    out->external_calls = g->calls;
}

int mugfx_register_font(const char *name, const char *path, int style) { (void)name; (void)path; (void)style; return 0; }

const char *mugfx_fonts_used(MuGfx *g) { (void)g; return ""; }
