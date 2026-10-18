/* mu-gfx-window: the GFx interface layer in a window of its own
 * (NATIVE-GFX-001 prototype, rebuilt on mu_gfx_layer in NATIVE-GFX-002).
 *
 * Plays main (bottom bar), InventoryFrame, InfoPopup, CharacterInfoFrame and
 * chat through native/gfx/mu_gfx_layer.c over a plain background, in an
 * SDL2 + OpenGL 2.1 window, headless through an offscreen GL context
 * (--headless-gl: the same GL compositor and IOSurface path as the window)
 * or headless on the CPU (--headless, read-back players).
 *
 * Usage:
 *   mu-gfx-window --gfx DIR [--size 1280x800] [--headless | --headless-gl] [--out-dir DIR] [--script]
 *                 [--frames N] [--bench] [--open] [--readback] [--full-stage] [--scale S] [--log FILE]
 *                 [--standalone] [--double]
 * --scale S: pixels per point (2 = Retina); --size stays in points.
 * NATIVE-GFX-003: a DIR with base.swf (and ExternalBase, ImageData, main,
 * Chat, ... converted) plays the HUD as the client's base movie;
 * --standalone keeps the NATIVE-GFX-002 main/chat players; --double gives
 * every shared movie two surfaces (no GPU wait before drawing).
 * DIR holds the movies converted with
 *   gfxconvert.py --bridge --transparent --var _root.isClient=true --fontconfig English --font-subset latin
 *     --movie main --movie InventoryFrame --movie InfoPopup --movie CharacterInfoFrame --movie chat
 * The movies and every output are client-derived: keep them local. */
#define _POSIX_C_SOURCE 200809L
#include <math.h>
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

#include "gl_headless.h"
#include "mu_gfx_layer.h"
#include "mu_gfx_sdl.h"
#include "mu_png.h"

static double now_ms(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec * 1000.0 + ts.tv_nsec / 1e6;
}

static void background_pixel(int w, int h, int x, int y, uint8_t *px)
{
    float fy = (float)y / (float)h, fx = (float)x / (float)w;
    float checker = (((x / 64) + (y / 64)) & 1) ? 0.04f : 0.0f;
    px[0] = (uint8_t)(255 * (0.20f + 0.15f * fy + checker));
    px[1] = (uint8_t)(255 * (0.09f + 0.05f * fx + checker));
    px[2] = (uint8_t)(255 * (0.12f + 0.10f * (1 - fy) + checker));
    px[3] = 255;
}

static void background_gl(int w, int h)
{
    glViewport(0, 0, w, h);
    glMatrixMode(GL_PROJECTION);
    glLoadIdentity();
    glOrtho(0, w, h, 0, -1, 1);
    glMatrixMode(GL_MODELVIEW);
    glLoadIdentity();
    glDisable(GL_DEPTH_TEST);
    glDisable(GL_TEXTURE_2D);
    glBegin(GL_QUADS);
    glColor3f(0.20f, 0.09f, 0.22f); glVertex2f(0, 0); glVertex2f((float)w, 0);
    glColor3f(0.35f, 0.14f, 0.12f); glVertex2f((float)w, (float)h); glVertex2f(0, (float)h);
    glEnd();
}

static void read_gl(int w, int h, uint8_t *rgba)
{
    size_t row = (size_t)w * 4;
    uint8_t *tmp = malloc(row * (size_t)h);
    if (!tmp)
        return;
    glPixelStorei(GL_PACK_ALIGNMENT, 1);
    glReadPixels(0, 0, w, h, GL_RGBA, GL_UNSIGNED_BYTE, tmp);
    for (int y = 0; y < h; y++)
        memcpy(rgba + row * (size_t)y, tmp + row * (size_t)(h - 1 - y), row);
    free(tmp);
}

/* ---- scripted demo (headless and --script) --------------------------------------- */

typedef struct step { double at; const char *what; } step;

static const step SCRIPT[] = {
    {400, "shot 1-hud"},
    {500, "key I"},                     /* window hotkey (layer key scan) */
    {1300, "shot 2-inventory"},
    {1400, "hover 9"},
    {1900, "shot 3-tooltip"},
    {2000, "rclick 9"},                 /* GFx onReleaseAux -> requestItemSlotClickR */
    {2100, "click 9"},
    {2200, "hover 41"},
    {2500, "shot 4-item-held"},
    {2600, "click 41"},
    {2700, "move 640 300"},
    {3000, "shot 5-item-moved"},
    {3100, "key C"},
    {3900, "shot 6-character"},
    {4000, "key Enter"},
    {4100, "text hello from the Mac"},
    {4150, "compose  ime"},             /* IME composition (preedit) */
    {4300, "shot 7-chat-typing"},
    {4350, "text  IME"},                /* the IME commits */
    {4400, "key Enter"},
    {4800, "shot 8-chat-sent"},
    {4900, "key 2"},
    {5300, "shot 9-skill"},
    {5400, "close inventory"},
    {5500, "key Esc"},
    {6200, "shot 10-closed"},
};
#define SCRIPT_STEPS ((int)(sizeof SCRIPT / sizeof SCRIPT[0]))

static int vk_of(const char *name)
{
    if (!strcmp(name, "Enter")) return 13;
    if (!strcmp(name, "Esc")) return 27;
    return (unsigned char)name[0];
}

static double g_scale = 1.0;

static void run_step(mu_gfx_layer *L, const char *what, char *shot, size_t cap, FILE *log)
{
    double x, y;
    shot[0] = 0;
    if (log)
        fprintf(log, "script: %s\n", what);
    if (!strncmp(what, "shot ", 5)) {
        snprintf(shot, cap, "%s", what + 5);
    } else if (!strncmp(what, "key ", 4)) {
        int vk = vk_of(what + 4);
        uint32_t ch = vk >= 'A' && vk <= 'Z' ? (uint32_t)(vk + 32) : (vk >= '0' && vk <= '9' ? (uint32_t)vk : 0);
        mu_gfx_layer_key(L, 1, vk, ch, 0);
        mu_gfx_layer_key(L, 0, vk, ch, 0);
    } else if (!strncmp(what, "text ", 5)) {
        mu_gfx_layer_text(L, what + 5);
    } else if (!strncmp(what, "compose ", 8)) {
        mu_gfx_layer_compose(L, what + 8, (int)strlen(what + 8));
    } else if (!strncmp(what, "hover ", 6) && mu_gfx_layer_cell_center(L, atoi(what + 6), &x, &y)) {
        mu_gfx_layer_mouse(L, 0, 0, x, y);
    } else if (!strncmp(what, "click ", 6) && mu_gfx_layer_cell_center(L, atoi(what + 6), &x, &y)) {
        mu_gfx_layer_mouse(L, 0, 0, x, y);
        mu_gfx_layer_mouse(L, 1, 0, x, y);
        mu_gfx_layer_mouse(L, 2, 0, x, y);
    } else if (!strncmp(what, "rclick ", 7) && mu_gfx_layer_cell_center(L, atoi(what + 7), &x, &y)) {
        mu_gfx_layer_mouse(L, 0, 0, x, y);
        mu_gfx_layer_mouse(L, 1, 1, x, y);
        mu_gfx_layer_mouse(L, 2, 1, x, y);
    } else if (!strncmp(what, "move ", 5)) {
        sscanf(what + 5, "%lf %lf", &x, &y);
        x *= g_scale;   /* script points -> window pixels */
        y *= g_scale;
        mu_gfx_layer_mouse(L, 0, 0, x, y);
    } else if (!strcmp(what, "close inventory")) {
        /* The movie's own close button: its clip bounds include a wide
         * transparent hit area; aim at the top-left icon (layer choice). */
        char p[192];
        snprintf(p, sizeof p, "%s.mcInventoryFrame.btnClose", mu_gfx_layer_path(L, MU_GFX_INVENTORY));
        const char *r = mu_gfx_layer_invoke(L, MU_GFX_INVENTORY, p, "getBounds", "[\"_level0\"]");
        double bx = 0, by = 0;
        const char *px = r ? strstr(r, "\"xMin\":") : NULL, *py = r ? strstr(r, "\"yMin\":") : NULL;
        if (px) bx = atof(px + 7);
        if (py) by = atof(py + 7);
        x = bx + 10;
        y = by + 10;
        mu_gfx_layer_mouse(L, 0, 0, x, y);
        mu_gfx_layer_mouse(L, 1, 0, x, y);
        mu_gfx_layer_mouse(L, 2, 0, x, y);
    }
}

int main(int argc, char **argv)
{
    const char *dir = NULL, *out_dir = NULL, *log_path = NULL;
    int headless = 0, headless_gl = 0, script = 0, bench = 0, frames = 0, open_inv = 0, readback = 0, full = 0;
    int standalone = 0, double_buffer = 0;
    int w = 1280, h = 800;
    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--gfx") && i + 1 < argc) dir = argv[++i];
        else if (!strcmp(argv[i], "--out-dir") && i + 1 < argc) out_dir = argv[++i];
        else if (!strcmp(argv[i], "--log") && i + 1 < argc) log_path = argv[++i];
        else if (!strcmp(argv[i], "--size") && i + 1 < argc) sscanf(argv[++i], "%dx%d", &w, &h);
        else if (!strcmp(argv[i], "--scale") && i + 1 < argc) g_scale = atof(argv[++i]);
        else if (!strcmp(argv[i], "--frames") && i + 1 < argc) frames = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--headless")) headless = 1;
        else if (!strcmp(argv[i], "--headless-gl")) headless_gl = 1;
        else if (!strcmp(argv[i], "--script")) script = 1;
        else if (!strcmp(argv[i], "--bench")) bench = 1;
        else if (!strcmp(argv[i], "--open")) open_inv = 1;
        else if (!strcmp(argv[i], "--readback")) readback = 1;
        else if (!strcmp(argv[i], "--full-stage")) full = 1;
        else if (!strcmp(argv[i], "--standalone")) standalone = 1;
        else if (!strcmp(argv[i], "--double")) double_buffer = 1;
        else {
            fprintf(stderr, "usage: %s --gfx DIR [--size WxH] [--headless|--headless-gl] [--out-dir DIR] [--script]\n"
                            "       [--frames N] [--bench] [--open] [--readback] [--full-stage] [--scale S] [--log FILE]\n"
                            "       [--standalone] [--double]\n", argv[0]);
            return 2;
        }
    }
    if (!dir) {
        fprintf(stderr, "mu-gfx-window: --gfx DIR is required\n");
        return 2;
    }
    if (!(g_scale > 0))
        g_scale = 1.0;
    w = (int)(w * g_scale);   /* --size is in points; the drawable is in pixels */
    h = (int)(h * g_scale);
    FILE *log = log_path ? fopen(log_path, "w") : NULL;
    SDL_Window *win = NULL;
    SDL_GLContext ctx = NULL;
    char error[512];
    int gl = !headless;
    if (headless_gl) {
        if (mu_gl_headless_begin(w, h, error, sizeof error)) {
            fprintf(stderr, "headless GL: %s\n", error);
            return 1;
        }
    } else if (!headless) {
        if (SDL_Init(SDL_INIT_VIDEO) != 0) {
            fprintf(stderr, "SDL_Init: %s\n", SDL_GetError());
            return 1;
        }
        SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 2);
        SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 1);
        SDL_GL_SetAttribute(SDL_GL_DOUBLEBUFFER, 1);
        win = SDL_CreateWindow("mu-gfx-window (GFx movies via Ruffle)", SDL_WINDOWPOS_CENTERED,
                               SDL_WINDOWPOS_CENTERED, w, h, SDL_WINDOW_OPENGL);
        ctx = win ? SDL_GL_CreateContext(win) : NULL;
        if (!ctx) {
            fprintf(stderr, "SDL window/GL: %s\n", SDL_GetError());
            return 1;
        }
        SDL_GL_SetSwapInterval(bench ? 0 : 1);
        SDL_StartTextInput();
    }
    mu_gfx_layer_config cfg = {.movie_dir = dir, .width = w, .height = h, .shared = gl && !readback, .full_stage = full,
                               .demo = 1, .log = log, .scale = g_scale, .standalone = standalone,
                               .double_buffer = double_buffer};
    double t_open = now_ms();
    mu_gfx_layer *L = mu_gfx_layer_open(&cfg, error, sizeof error);
    if (!L) {
        fprintf(stderr, "mu-gfx-window: %s\n", error);
        return 1;
    }
    double open_ms = now_ms() - t_open;
    static const struct { int code, level, w, h; const char *name; } DEMO[] = {
        {0, 9, 1, 3, "Kris"}, {3584, 7, 2, 2, "Bronze Helm"}, {7171, 0, 1, 1, "Healing Potion"},
        {2048, 11, 2, 3, "Dragon Armor"}, {1024, 0, 1, 2, "Short Bow"}, {7174, 0, 1, 1, "Mana Potion"},
        {3072, 5, 2, 2, "Small Shield"}, {7180, 0, 1, 1, "Apple"}, {2560, 13, 2, 4, "Lighting Sword"}};
    for (size_t i = 0; i < sizeof DEMO / sizeof DEMO[0]; i++)
        mu_gfx_layer_add_item(L, DEMO[i].code, DEMO[i].level, DEMO[i].w, DEMO[i].h, DEMO[i].name);
    if (open_inv)
        mu_gfx_layer_show(L, MU_GFX_INVENTORY, 1);
    mu_gfx_layer_set_location(L, "World 1", 135, 10);   /* map names are GlobalText: placeholder */

    uint8_t *shot = (headless || headless_gl) ? malloc((size_t)w * h * 4) : NULL;
    int next = 0, running = 1;
    long frame = 0;
    double dt = 1000.0 / 60.0, last = now_ms(), wall0 = now_ms(), t_game = 0, frame_total = 0;
    struct rusage ru0;
    getrusage(RUSAGE_SELF, &ru0);
    if ((headless || headless_gl) && !frames)
        frames = script || out_dir ? (int)(SCRIPT[SCRIPT_STEPS - 1].at / dt) + 2 : 120;
    while (running) {
        double t0 = now_ms();
        if (win) {
            SDL_Event e;
            while (SDL_PollEvent(&e)) {
                if (e.type == SDL_QUIT)
                    running = 0;
                else if (!mu_gfx_sdl_event(L, &e, 1.0) && e.type == SDL_KEYDOWN &&
                         e.key.keysym.sym == SDLK_ESCAPE)
                    running = 0;
            }
            double now = now_ms();
            dt = bench ? 1000.0 / 60.0 : now - last;
            last = now;
            static int cursor = -1;
            int c = mu_gfx_layer_cursor(L);
            if (c != cursor) {
                static SDL_Cursor *cursors[3];
                const SDL_SystemCursor ids[3] = {SDL_SYSTEM_CURSOR_ARROW, SDL_SYSTEM_CURSOR_HAND, SDL_SYSTEM_CURSOR_IBEAM};
                int k = c >= 0 && c < 3 ? c : 0;
                if (!cursors[k])
                    cursors[k] = SDL_CreateSystemCursor(ids[k]);
                SDL_SetCursor(cursors[k]);
                cursor = c;
            }
        }
        mu_gfx_layer_advance(L, dt);
        t_game += dt;
        char name[64] = "";
        while ((script || headless || headless_gl) && next < SCRIPT_STEPS && t_game >= SCRIPT[next].at) {
            run_step(L, SCRIPT[next].what, name, sizeof name, log);
            next++;
            if (name[0])
                break;
        }
        if (headless) {
            if (name[0] && out_dir) {
                for (int y = 0; y < h; y++)
                    for (int x = 0; x < w; x++)
                        background_pixel(w, h, x, y, shot + ((size_t)y * w + x) * 4);
                mu_gfx_layer_composite(L, shot, w, h);
            }
        } else {
            background_gl(w, h);
            mu_gfx_layer_draw_gl(L);
            if (win)
                SDL_GL_SwapWindow(win);
            else if (name[0] && out_dir) {
                glFinish();
                read_gl(w, h, shot);
            }
        }
        if (name[0] && out_dir) {
            char path[1024];
            snprintf(path, sizeof path, "%s/%s.png", out_dir, name);
            mu_png_write(path, shot, w, h);
            fprintf(stderr, "mu-gfx-window: wrote %s\n", path);
        }
        frame_total += now_ms() - t0;
        frame++;
        if (frames && frame >= frames)
            running = 0;
    }
    struct rusage ru1;
    getrusage(RUSAGE_SELF, &ru1);
    double wall = now_ms() - wall0;
    double cpu = (ru1.ru_utime.tv_sec - ru0.ru_utime.tv_sec + ru1.ru_stime.tv_sec - ru0.ru_stime.tv_sec) * 1000.0 +
                 (ru1.ru_utime.tv_usec - ru0.ru_utime.tv_usec + ru1.ru_stime.tv_usec - ru0.ru_stime.tv_usec) / 1000.0;
    mu_gfx_layer_stats st;
    mu_gfx_layer_stats_get(L, &st);
    static const char *const NAMES[MU_GFX_MOVIES] = {"main", "InventoryFrame", "InfoPopup", "CharacterInfoFrame", "chat"};
    printf("{\"frames\": %ld, \"wall_ms\": %.1f, \"cpu_per_frame_ms\": %.3f, \"frame_ms\": %.3f, \"open_ms\": %.1f, "
           "\"shared\": %d, \"gpu_wait_ms\": %.3f, \"logic_steps\": %ld, \"callbacks\": %ld, \"invokes\": %ld, \"view_changes\": %ld, \"movies\": {",
           frame, wall, cpu / (double)frame, frame_total / (double)frame, open_ms, st.shared,
           st.gpu_waits ? st.gpu_wait_ms / (double)st.gpu_waits : 0.0, st.steps, st.callbacks,
           st.invokes, st.view_changes);
    for (int m = 0; m < MU_GFX_MOVIES; m++) {
        double r = st.renders[m] ? (double)st.renders[m] : 1;
        printf("%s\"%s\": {\"renders\": %ld, \"render_ms\": %.3f, \"capture_ms\": %.3f, \"upload_ms\": %.3f, "
               "\"view\": [%d, %d, %d, %d]}", m ? ", " : "", NAMES[m], st.renders[m], st.render_ms[m] / r,
               st.capture_ms[m] / r, st.upload_ms[m] / r, st.view[m][0], st.view[m][1], st.view[m][2], st.view[m][3]);
    }
    printf("}, \"inventory_open\": %d, \"character_open\": %d, \"held\": %d, \"chat_sent\": \"%s\"}\n",
           mu_gfx_layer_is_open(L, MU_GFX_INVENTORY), mu_gfx_layer_is_open(L, MU_GFX_CHARACTER),
           mu_gfx_layer_held(L), mu_gfx_layer_last_sent(L));
    mu_gfx_layer_close(L);
    if (headless_gl)
        mu_gl_headless_end();
    if (win) {
        SDL_GL_DeleteContext(ctx);
        SDL_DestroyWindow(win);
        SDL_Quit();
    }
    if (log)
        fclose(log);
    free(shot);
    return 0;
}
