/* mu-client: the client's scene flow natively, offline (NATIVE-SHELL-001).
 *
 * Title -> login (server select, OFFLINE DEMO account panel) -> character
 * select -> loading screen -> world -> Esc back to character select, run by
 * the reconstructed scene manager (client/shell.c) over the existing native
 * modules. There is no server connection: client/offline-session.* answers
 * what the network layer would (server list, login, character list, join).
 *
 *   mu-client --game-root ROOT [--session FILE] [--width W --height H]
 *             [--sound-table TSV] [--placement FILE] [--players FILE] [--no-audio] [--seconds S]
 *   mu-client --game-root ROOT --headless --out-dir DIR [--backend gl|soft]
 *             [--frames N] [--every K] [--auto | --script "F:ACTION ..."] [--wav OUT.wav]
 *   --gfx DIR [--gfx-open inventory,character]: the client's GFx interface
 *             in the world scene (NATIVE-GFX-003, as mu-world --gfx; GL only)
 *             and the character select's list CharacterSelect.swf
 *             (NATIVE-CHARSEL-003; also in mu-shell) [--gfx-log FILE]
 *   NATIVE-APP-001: --combat --items --npc [--npc-demo FILE] --no-names --no-env
 *             --no-particles pass mu-world's features to the world scene;
 *             --label TEXT replaces the offline label's first line and
 *             --title TEXT the window title's prefix (the preview app)
 *
 * Headless actions (frame numbers count dispatcher passes): enter, esc, left,
 * right, tab, back, text:STRING, click:group:N, click:server:N, click:X,Y,
 * click:row:N and dblclick:row:N (the GFx character list), dblclick:X,Y,
 * wheel:+1/-1, quit. NATIVE-CHARCREATE-001 (with --gfx): click:create,
 * click:menu, click:connect, click:delete (CCharSelMainWin's buttons),
 * click:class:N, click:createname, click:createok, click:createcancel (the
 * create panel), click:msgok, click:msgcancel, click:msginput (the Caution
 * box), click:menu:exit|server|option|character|close (winSystemMenu).
 *   --store FILE: the OFFLINE DEMO character store (characters created and
 *             deleted in character select); the window defaults to
 *             ~/Library/Application Support/MuTheMatrixNative/offline-characters.txt,
 *             headless runs keep changes in memory; --no-store: never. --auto plays the whole flow (server, login, select,
 * world, back to select, world again). Captures: every K-th frame, the first
 * frame of each scene visit and every title/loading frame.
 *
 * NATIVE-PERF-001: the window is resizable and goes full screen (green button,
 * Ctrl-Cmd-F, --fullscreen); the 2D layer draws on the GPU (viewer/ui_gl.c;
 * --cpu-overlay: the software raster over a read-back frame, as headless);
 * --perf FILE logs per-phase frame times (native/tools/perf_report.py);
 * --auto --hold SCENE plays the flow in the window and stays in SCENE;
 * MU_EXIT_WITH_PARENT=1 (the preview app) quits when the launcher is gone.
 *
 * Built twice: build/mu-client (SDL2 + OpenGL window, headless GL or
 * software) and, with MU_CLIENT_NO_GL, build/mu-shell (headless software
 * only, no SDL2; the portable tests use it).
 */
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#ifndef MU_CLIENT_NO_GL
#include <SDL.h>
#ifdef __APPLE__
#include <IOSurface/IOSurface.h>
#include <OpenGL/CGLIOSurface.h>
#include <OpenGL/OpenGL.h>
#include <OpenGL/gl.h>
#include <OpenGL/glext.h>
#else
#include <GL/gl.h>
#endif
#include "../login/login_gl.h"
#include "../viewer/gl_backend.h"
#include "../viewer/gl_headless.h"
#include "../viewer/ui_gl.h"
#include "../world/world_gfx.h"
#include "../world/world_gfx_options.h"
#include "../gfx/mu_gfx_layer.h"
#endif

#include "../core/mu_frame.h"
#include "../core/mu_perf.h"
#include "../core/mu_png.h"
#include "../core/mu_raster.h"
#include "../core/mu_wav.h"
#include "shell.h"

#define MAX_ACTIONS 128

typedef struct action {
    int32_t frame;
    char what[64];
} action;

typedef struct front {
    const char *root, *session, *out_dir, *backend, *sound_table, *placement, *players, *wav_path, *font;
    const char *helper;               /* NATIVE-HELPERS-001: --helper ITEM [--helper-state N] (DEMO) */
    int32_t helper_state;
    const char *world_objects, *charsel_objects, *login_objects;
    const char *gfx_dir, *gfx_open;   /* NATIVE-GFX-003: the GFx interface in the world scene */
    const char *gfx_log;              /* NATIVE-CHARSEL-003 */
    const char *store;                /* NATIVE-CHARCREATE-001: the OFFLINE DEMO character store */
    int no_store;
    char store_default[4096];
    int double_click;                 /* the scripted click is a double click */
    const char *label, *title, *npc_demo;                      /* NATIVE-APP-001 */
    int combat, items, npc, no_names, no_env, no_particles;
    int progress;   /* NATIVE-PROGRESS-001 */
    int32_t width, height, frames, every, headless, audio, quiet, autoplay;
    int32_t hold_scene;               /* NATIVE-PERF-001: --hold SCENE stops the autoplay there (0: never) */
    const char *perf_path;            /* NATIVE-PERF-001: --perf FILE, --perf-sync */
    int perf_sync;
    int gpu_overlay;                  /* NATIVE-PERF-001: the 2D layer on the GPU (window default; --cpu-overlay,
                                       * headless --gpu-overlay) */
    int fullscreen;                   /* NATIVE-PERF-001: --fullscreen (macOS full screen, Ctrl-Cmd-F toggles) */
    char shot[4096];                  /* a window capture due after this frame's compose (O key, shot:NAME) */
    float seconds;
    action actions[MAX_ACTIONS];
    int32_t action_count;
    mu_shell *shell;
    int gl;
    uint8_t *pixels;
    mu_raster raster;
    uint32_t now;            /* virtual clock (headless) */
    int32_t frame;
    int32_t captures, presents;
    int32_t scene_frames[8];  /* frames per scene */
    int32_t visit[8];         /* visits per scene */
    int32_t frames_in_scene, last_scene;
    char last_png[4096];
    /* wav */
    float *wav;
    size_t wav_frames, wav_capacity;
    uint64_t audio_frames;
    uint32_t audio_start;
    /* scripted click and key releases */
    int click_stage, click_x, click_y;
    int32_t release_frame[16], release_vk[16], release_count;
#ifndef MU_CLIENT_NO_GL
    world_gfx *gfx;
    uint32_t gfx_clock;
    SDL_Window *window;
    GLuint screen_texture;
    int32_t dw, dh;
    double scale;
    SDL_AudioDeviceID audio_device;
    mu_login_gl *login_gl;   /* NATIVE-LOGIN-001 */
    GLuint image_texture;    /* NATIVE-PERF-001: the GFx character list's frame */
    int32_t image_w, image_h;
    GLuint surface_texture;
    uint32_t surface_seed;
#endif
} front;

static int write_png(front *f, const uint8_t *rgba, const char *tag)
{
    if (!f->out_dir)
        return 0;
    char path[4096], hash[65];
    snprintf(path, sizeof path, "%s/frame-%04d-s%d-%s.png", f->out_dir, f->frame, mu_shell_scene(f->shell), tag);
    if (mu_png_write(path, rgba, f->width, f->height)) {
        fprintf(stderr, "cannot write %s\n", path);
        return 1;
    }
    mu_sha256_hex(rgba, (uint64_t)f->width * (uint64_t)f->height * 4, hash);
    ++f->captures;
    snprintf(f->last_png, sizeof f->last_png, "%s", path);
    if (!f->quiet)
        printf("{\"frame\": %d, \"scene\": %d, \"tag\": \"%s\", \"tick\": %u, \"sha256\": \"%s\", \"png\": \"%s\"}\n",
               f->frame, mu_shell_scene(f->shell), tag, f->now, hash, path);
    return 0;
}

/* ---- WAV (headless) ---- */

static void wav_pump(front *f, uint32_t now)
{
    if (!f->wav_path)
        return;
    uint64_t due = (uint64_t)(now - f->audio_start) * mu_shell_audio_rate(f->shell) / 1000u;
    if (due <= f->audio_frames)
        return;
    uint32_t frames = (uint32_t)(due - f->audio_frames);
    if (f->wav_frames + frames > f->wav_capacity) {
        size_t capacity = f->wav_capacity ? f->wav_capacity * 2 : 1u << 20;
        while (capacity < f->wav_frames + frames)
            capacity *= 2;
        float *grown = realloc(f->wav, capacity * 2 * sizeof *grown);
        if (!grown)
            return;
        f->wav = grown;
        f->wav_capacity = capacity;
    }
    mu_shell_mix(f->shell, f->wav + f->wav_frames * 2, frames);
    f->wav_frames += frames;
    f->audio_frames += frames;
}

/* ---- platform callbacks ---- */

#ifndef MU_CLIENT_NO_GL
static void screen_quad(front *f, const uint8_t *rgba)
{
    glViewport(0, 0, f->dw, f->dh);
    glMatrixMode(GL_PROJECTION);
    glLoadIdentity();
    glOrtho(0, 1, 1, 0, -1, 1);
    glMatrixMode(GL_MODELVIEW);
    glLoadIdentity();
    glDisable(GL_DEPTH_TEST);
    glDisable(GL_BLEND);
    glDisable(GL_CULL_FACE);
    glDisable(GL_ALPHA_TEST);
    glDisable(GL_LIGHTING);
    glDisable(GL_FOG);
    glEnable(GL_TEXTURE_2D);
    if (!f->screen_texture) {
        glGenTextures(1, &f->screen_texture);
        glBindTexture(GL_TEXTURE_2D, f->screen_texture);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, f->dw, f->dh, 0, GL_RGBA, GL_UNSIGNED_BYTE, NULL);
    }
    glBindTexture(GL_TEXTURE_2D, f->screen_texture);
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
    glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, f->dw, f->dh, GL_RGBA, GL_UNSIGNED_BYTE, rgba);
    glTexEnvi(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_REPLACE);
    glColor4f(1, 1, 1, 1);
    glBegin(GL_QUADS);
    glTexCoord2f(0, 0); glVertex2f(0, 0);
    glTexCoord2f(1, 0); glVertex2f(1, 0);
    glTexCoord2f(1, 1); glVertex2f(1, 1);
    glTexCoord2f(0, 1); glVertex2f(0, 1);
    glEnd();
    glTexEnvi(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE);
    glBindTexture(GL_TEXTURE_2D, 0);
}
#endif

static void on_present(void *user, const uint8_t *rgba)
{
    front *f = user;
    ++f->presents;
#ifndef MU_CLIENT_NO_GL
    if (!rgba && f->headless) {   /* NATIVE-PERF-001: the GPU 2D layer drew into the back buffer */
        glFinish();
        mu_gl_read(f->width, f->height, f->pixels);
        rgba = f->pixels;
    }
#endif
    if (f->headless) {
        char tag[32];
        snprintf(tag, sizeof tag, "present%02d", f->presents);
        write_png(f, rgba, tag);
        f->now += 40;
        return;
    }
#ifndef MU_CLIENT_NO_GL
    if (rgba)
        screen_quad(f, rgba);
    SDL_GL_SwapWindow(f->window);
    SDL_PumpEvents();
#endif
}

#ifndef MU_CLIENT_NO_GL
/* ---- NATIVE-PERF-001: the shell's 2D layer on the GPU (viewer/ui_gl.c) ---- */

static int on_ui_target(void *user, const mu_ui_raster *raster, int32_t w, int32_t h, mu_ui_sink *out)
{
    (void)user;
    mu_ui_gl *g = mu_ui_gl_new(raster, w, h);
    if (!g)
        return 1;
    *out = mu_ui_gl_sink(g);
    return 0;
}

static void on_ui_target_free(void *user, const mu_ui_sink *sink)
{
    (void)user;
    mu_ui_gl_free(sink->user);
}

static void on_ui_begin(void *user) { (void)user; mu_ui_gl_begin(NULL); }
static void on_ui_end(void *user) { (void)user; mu_ui_gl_end(NULL); }

/* The GFx character list over the frame: straight alpha, as mu_charsel_list_gfx_composite; uploaded only when
 * the movie rendered a new frame. */
static void on_image(void *user, const uint8_t *rgba, int32_t w, int32_t h, int changed)
{
    front *f = user;
    if (!f->image_texture) {
        glGenTextures(1, &f->image_texture);
        changed = 1;
    }
    glBindTexture(GL_TEXTURE_2D, f->image_texture);
    if (changed || w != f->image_w || h != f->image_h) {
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
        if (w != f->image_w || h != f->image_h)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, rgba);
        else
            glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, w, h, GL_RGBA, GL_UNSIGNED_BYTE, rgba);
        f->image_w = w;
        f->image_h = h;
    }
    glViewport(0, 0, w, h);
    glMatrixMode(GL_PROJECTION);
    glPushMatrix();
    glLoadIdentity();
    glOrtho(0, 1, 1, 0, -1, 1);
    glMatrixMode(GL_MODELVIEW);
    glPushMatrix();
    glLoadIdentity();
    glEnable(GL_TEXTURE_2D);
    glDisable(GL_CULL_FACE);
    glDisable(GL_ALPHA_TEST);
    glEnable(GL_BLEND);
    glBlendFuncSeparate(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA, GL_ZERO, GL_ONE);   /* colour only, like the CPU blend */
    glColor4f(1, 1, 1, 1);
    glBegin(GL_QUADS);
    glTexCoord2f(0, 0); glVertex2f(0, 0);
    glTexCoord2f(1, 0); glVertex2f(1, 0);
    glTexCoord2f(1, 1); glVertex2f(1, 1);
    glTexCoord2f(0, 1); glVertex2f(0, 1);
    glEnd();
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    glMatrixMode(GL_PROJECTION);
    glPopMatrix();
    glMatrixMode(GL_MODELVIEW);
    glPopMatrix();
    glBindTexture(GL_TEXTURE_2D, 0);
}

/* NATIVE-CHARCREATE-001's create panel, menu and Caution boxes composite in software over the frame: read it
 * back while they are open, and write the result over the whole framebuffer. */
static uint8_t *on_read_frame(void *user)
{
    front *f = user;
    glFinish();
    mu_gl_read(f->width, f->height, f->pixels);
    return f->pixels;
}

static void on_write_frame(void *user, const uint8_t *rgba)
{
    front *f = user;
    screen_quad(f, rgba);
}

#ifdef __APPLE__
/* The list rendered into an IOSurface (mugfx shared rendering): sampled in place, premultiplied alpha. */
static void on_surface(void *user, void *iosurface, int32_t w, int32_t h, uint32_t seed)
{
    front *f = user;
    if (!f->surface_texture)
        glGenTextures(1, &f->surface_texture);
    glBindTexture(GL_TEXTURE_RECTANGLE_ARB, f->surface_texture);
    if (seed != f->surface_seed || !f->surface_seed) {
        CGLTexImageIOSurface2D(CGLGetCurrentContext(), GL_TEXTURE_RECTANGLE_ARB, GL_RGBA8, w, h, GL_BGRA,
                               GL_UNSIGNED_INT_8_8_8_8_REV, (IOSurfaceRef)iosurface, 0);
        glTexParameteri(GL_TEXTURE_RECTANGLE_ARB, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
        glTexParameteri(GL_TEXTURE_RECTANGLE_ARB, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
        f->surface_seed = seed;
    }
    glViewport(0, 0, w, h);
    glMatrixMode(GL_PROJECTION);
    glPushMatrix();
    glLoadIdentity();
    glOrtho(0, w, h, 0, -1, 1);
    glMatrixMode(GL_MODELVIEW);
    glPushMatrix();
    glLoadIdentity();
    glDisable(GL_TEXTURE_2D);
    glEnable(GL_TEXTURE_RECTANGLE_ARB);
    glDisable(GL_CULL_FACE);
    glDisable(GL_ALPHA_TEST);
    glEnable(GL_BLEND);
    glBlendFuncSeparate(GL_ONE, GL_ONE_MINUS_SRC_ALPHA, GL_ZERO, GL_ONE);   /* premultiplied, colour only */
    glColor4f(1, 1, 1, 1);
    glBegin(GL_QUADS);
    glTexCoord2f(0, 0); glVertex2f(0, 0);
    glTexCoord2f((float)w, 0); glVertex2f((float)w, 0);
    glTexCoord2f((float)w, (float)h); glVertex2f((float)w, (float)h);
    glTexCoord2f(0, (float)h); glVertex2f(0, (float)h);
    glEnd();
    glDisable(GL_TEXTURE_RECTANGLE_ARB);
    glBindTexture(GL_TEXTURE_RECTANGLE_ARB, 0);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    glMatrixMode(GL_PROJECTION);
    glPopMatrix();
    glMatrixMode(GL_MODELVIEW);
    glPopMatrix();
}
#endif
#endif

static uint32_t on_ticks(void *user)
{
    front *f = user;
#ifndef MU_CLIENT_NO_GL
    if (!f->headless)
        return SDL_GetTicks();
#endif
    return f->now;
}

static void on_pause(void *user, uint32_t ms)
{
    front *f = user;
    if (f->headless) {
        f->now += ms;
        return;
    }
#ifndef MU_CLIENT_NO_GL
    mu_sleep_ms(ms);
#endif
}

static void on_opened(void *user, int kind, void *embed)
{
    front *f = user;
    (void)f;
    (void)kind;
    (void)embed;
#ifndef MU_CLIENT_NO_GL
    if (!f->gl)
        return;
    if (kind == MU_SHELL_EMBED_LOGIN) {
        f->login_gl = mu_login_gl_setup(embed);
        return;
    }
    if (kind == MU_SHELL_EMBED_CHARSEL)
        mu_charsel_embed_gl_setup(embed);
    else
        mu_world_embed_gl_setup(embed);
    if (!f->headless && kind == MU_SHELL_EMBED_WORLD)
        mu_world_embed_resize(embed, f->dw, f->dh);
    if (kind == MU_SHELL_EMBED_WORLD && f->gfx_dir && !f->gfx) {
        /* The GFx interface over the world scene, as mu-world --gfx (the
         * client's GFx manager draws after the 3D pass in the main scene). */
        char error[512];
        f->gfx = world_gfx_open(f->gfx_dir, f->root, f->width, f->height, f->headless ? 1.0 : f->scale, 1,
                                f->gfx_open, error, sizeof error);
        if (!f->gfx)
            fprintf(stderr, "gfx: %s (continuing without the interface)\n", error);
        else
            mu_world_embed_set_gfx(embed, f->gfx, f->headless ? 1.0 : f->scale);
        f->gfx_clock = on_ticks(f);
    }
#endif
}

static void on_closing(void *user, int kind, void *embed)
{
    front *f = user;
    (void)f;
    (void)kind;
    (void)embed;
#ifndef MU_CLIENT_NO_GL
    if (!f->gl)
        return;
    if (kind == MU_SHELL_EMBED_LOGIN) {
        mu_login_gl_teardown(f->login_gl);
        f->login_gl = NULL;
        return;
    }
    if (kind == MU_SHELL_EMBED_WORLD && f->gfx) {
        mu_world_embed_set_gfx(embed, NULL, 1.0);
        world_gfx_close(f->gfx);
        f->gfx = NULL;
    }
    if (kind == MU_SHELL_EMBED_CHARSEL)
        mu_charsel_embed_gl_teardown(embed);
    else
        mu_world_embed_gl_teardown(embed);
#endif
}

/* ---- one frame: 3D view (GL or software), the 2D layer ---- */

static void compose(front *f)
{
    size_t bytes = (size_t)f->width * (size_t)f->height * 4;
    int view = mu_shell_view(f->shell);
#ifndef MU_CLIENT_NO_GL
    int gpu = f->gl && mu_shell_gpu_overlay(f->shell);   /* NATIVE-PERF-001: no read back */
    if (gpu && view == MU_SHELL_VIEW_2D) {
        glViewport(0, 0, f->width, f->height);
        glClearColor(0.0f, 0.0f, 0.0f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT);
    }
    if (gpu && view == MU_SHELL_VIEW_2D) {
    } else
#endif
    if (view == MU_SHELL_VIEW_2D) {
        for (size_t i = 0; i < bytes; i += 4) {
            f->pixels[i] = f->pixels[i + 1] = f->pixels[i + 2] = 0;
            f->pixels[i + 3] = 255;
        }
    } else if (f->gl) {
#ifndef MU_CLIENT_NO_GL
        if (view == MU_SHELL_VIEW_LOGIN && f->login_gl) {
            double perf = mu_perf_begin();
            mu_login_gl_draw(f->login_gl, mu_shell_login(f->shell), f->width, f->height);
            mu_perf_end(MU_PERF_SCENE, perf);
        } else if (view == MU_SHELL_VIEW_CHARSEL) {
            double perf = mu_perf_begin();
            mu_charsel_embed_draw_gl(mu_shell_charsel(f->shell), f->width, f->height);
            mu_perf_end(MU_PERF_SCENE, perf);
        } else {
            mu_world_embed *w = mu_shell_world(f->shell);
            mu_world_embed_draw_gl(w, f->width, f->height);
            if (f->gfx) {
                double perf = mu_perf_begin();
                uint32_t now = on_ticks(f);
                const mu_walk *walk = mu_world_embed_walk(w);
                world_gfx_set_location(f->gfx, mu_world_embed_folder(w) - 1, walk->hero.position[0],
                                       walk->hero.position[1]);
                world_gfx_frame(f->gfx, (double)(now - f->gfx_clock), 1);
                f->gfx_clock = now;
                int menu = wg_options_take_request(world_gfx_options(f->gfx));   /* NATIVE-PROGRESS-001 */
                if (menu >= 0)
                    mu_shell_world_menu(f->shell, menu);
                mu_perf_end(MU_PERF_GFX, perf);
            }
        }
        if (!gpu) {
            double perf = mu_perf_begin();
            glFinish();
            mu_gl_read(f->width, f->height, f->pixels);
            mu_perf_end(MU_PERF_OVERLAY, perf);
        }
#endif
    } else {
        if (view == MU_SHELL_VIEW_LOGIN)
            mu_login_draw_soft(mu_shell_login(f->shell), &f->raster);
        else if (view == MU_SHELL_VIEW_CHARSEL)
            mu_charsel_embed_draw_soft(mu_shell_charsel(f->shell), &f->raster);
        else
            mu_world_embed_draw_soft(mu_shell_world(f->shell), &f->raster);
        memcpy(f->pixels, f->raster.color, bytes);
    }
    double perf = mu_perf_begin();
    mu_shell_overlay(f->shell, f->pixels);
    mu_perf_end(MU_PERF_OVERLAY, perf);
#ifndef MU_CLIENT_NO_GL
    if (gpu && f->headless && f->out_dir) {   /* captures read the finished frame back */
        glFinish();
        mu_gl_read(f->width, f->height, f->pixels);
    }
#endif
}

/* ---- scripted input ---- */

static void click(front *f, int32_t x, int32_t y)
{
    f->click_x = x;
    f->click_y = y;
    mu_shell_mouse_move(f->shell, x, y);
    f->click_stage = 1;
    f->double_click = 0;
}

#ifndef MU_CLIENT_NO_GL
static void toggle_fullscreen(front *f);
#endif

static void do_action(front *f, const char *what)
{
    mu_shell *s = f->shell;
    int32_t x, y, n;
    if (!f->quiet)
        fprintf(stderr, "frame %d (scene %d): %s\n", f->frame, mu_shell_scene(s), what);
    if (!strcmp(what, "enter") || !strcmp(what, "esc") || !strcmp(what, "left") || !strcmp(what, "right") ||
        !strcmp(what, "tab") || !strcmp(what, "back")) {
        int vk = !strcmp(what, "enter") ? 0x0d : !strcmp(what, "esc") ? 0x1b : !strcmp(what, "left") ? 0x25
               : !strcmp(what, "right") ? 0x27 : !strcmp(what, "tab") ? 0x09 : 0x08;
#ifndef MU_CLIENT_NO_GL
        if (f->gfx && mu_shell_scene(s) == MU_SCENE_MAIN &&   /* NATIVE-PROGRESS-001: Esc opens the system menu */
            mu_gfx_layer_key(world_gfx_layer(f->gfx), 1, vk, (uint32_t)vk, 0)) {
            mu_gfx_layer_key(world_gfx_layer(f->gfx), 0, vk, (uint32_t)vk, 0);
            return;
        }
#endif
        mu_shell_key(s, vk, 1);
        if (f->release_count < 16) {   /* held for three frames, like a key press the scan can see */
            f->release_frame[f->release_count] = f->frame + 3;
            f->release_vk[f->release_count++] = vk;
        }
    } else if (!strncmp(what, "text:", 5)) {
        for (const char *p = what + 5; *p; ++p)
            mu_shell_char(s, (unsigned char)*p);
    } else if (sscanf(what, "click:group:%d", &n) == 1) {
        if (mu_shell_server_group_button(s, n, &x, &y))
            click(f, x, y);
    } else if (sscanf(what, "click:server:%d", &n) == 1) {
        if (mu_shell_server_button(s, n, &x, &y))
            click(f, x, y);
    } else if (sscanf(what, "click:row:%d", &n) == 1 || sscanf(what, "dblclick:row:%d", &n) == 1) {
        if (mu_shell_charsel_row(s, n, &x, &y)) {
            click(f, x, y);
            f->double_click = what[0] == 'd';
        }
    } else if (!strncmp(what, "click:", 6) && mu_shell_charsel_control(s, what + 6, &x, &y)) {
        click(f, x, y);   /* NATIVE-CHARCREATE-001: create, delete, menu, class:N, createok, msgok, menu:exit ... */
        if (!f->quiet)
            fprintf(stderr, "  %s at %d,%d\n", what + 6, x, y);
    } else if (sscanf(what, "dblclick:%d,%d", &x, &y) == 2) {
        click(f, x, y);
        f->double_click = 1;
    } else if (sscanf(what, "click:%d,%d", &x, &y) == 2) {
#ifndef MU_CLIENT_NO_GL
        if (f->gfx && mu_shell_scene(s) == MU_SCENE_MAIN) {   /* NATIVE-PROGRESS-001: the GFx windows first */
            mu_gfx_layer *l = world_gfx_layer(f->gfx);
            mu_gfx_layer_mouse(l, 0, 0, x, y);
            if (mu_gfx_layer_mouse(l, 1, 0, x, y)) {
                mu_gfx_layer_mouse(l, 2, 0, x, y);
                return;
            }
            mu_gfx_layer_mouse(l, 2, 0, x, y);
        }
#endif
        click(f, x, y);
    } else if (sscanf(what, "wheel:%d", &n) == 1) {
        mu_shell_wheel(s, n);
    } else if (!strcmp(what, "quit")) {
        mu_shell_request_quit(s);
#ifndef MU_CLIENT_NO_GL
    } else if (sscanf(what, "resize:%d,%d", &x, &y) == 2 && f->window) {   /* NATIVE-PERF-001: window points */
        SDL_SetWindowSize(f->window, x, y);
    } else if (!strcmp(what, "fullscreen") && f->window) {
        toggle_fullscreen(f);
    } else if (!strncmp(what, "shot:", 5) && f->window) {   /* a window capture into --out-dir */
        snprintf(f->shot, sizeof f->shot, "%s/%s.png", f->out_dir ? f->out_dir : ".", what + 5);
#endif
    } else {
        fprintf(stderr, "unknown action %s\n", what);
    }
}

static void click_step(front *f)
{
    for (int32_t i = 0; i < f->release_count;) {
        if (f->release_frame[i] <= f->frame) {
            mu_shell_key(f->shell, f->release_vk[i], 0);
            f->release_frame[i] = f->release_frame[f->release_count - 1];
            f->release_vk[i] = f->release_vk[--f->release_count];
        } else {
            ++i;
        }
    }
    if (f->click_stage == 1) {
        mu_shell_mouse_button(f->shell, 0, 1);
        f->click_stage = 2;
    } else if (f->click_stage == 2) {
        mu_shell_mouse_button(f->shell, 0, 0);
        if (f->double_click) {   /* the second press of a double click in the same pass */
            mu_shell_mouse_button(f->shell, 0, 1);
            mu_shell_mouse_button(f->shell, 0, 0);
            f->double_click = 0;
        }
        f->click_stage = 3;
    } else if (f->click_stage == 3) {
        mu_shell_mouse_move(f->shell, -1000, -1000);
        f->click_stage = 0;
    }
}

/* The whole flow, keyed to the scene and the frames spent in it. */
static void autoplay(front *f)
{
    int scene = mu_shell_scene(f->shell), k = f->frames_in_scene, v = f->visit[scene & 7];
    const char *what = NULL;
    if (f->hold_scene && scene == f->hold_scene)
        return;   /* NATIVE-PERF-001: stay in this scene (profiling runs) */
    if (scene == MU_SCENE_LOGIN) {
        if (k == 8) what = "click:group:0";
        else if (k == 16) what = "click:server:0";
        else if (k == 22) what = "text:demo";
        else if (k == 24) what = "tab";
        else if (k == 25) what = "text:secret";
        else if (k == 28) what = "enter";
    } else if (scene == MU_SCENE_CHARACTER && mu_shell_charsel_gfx(f->shell)) {
        /* NATIVE-CHARSEL-003: through the GFx list: click the second row, then double-click it to play */
        if (v == 1 && k == 12) what = "click:row:1";
        else if (v == 1 && k == 24) what = "dblclick:row:1";
        else if (v >= 2 && k == 10) what = "enter";
    } else if (scene == MU_SCENE_CHARACTER) {
        if (v == 1 && k == 12) what = "right";
        else if (k == (v == 1 ? 24 : 10)) what = "enter";
    } else if (scene == MU_SCENE_MAIN) {
        if (k == 10) what = "wheel:1";
        else if (v == 1 && k == 40) what = "esc";
        else if (v >= 2 && k == 25) what = "quit";
    }
    if (what)
        do_action(f, what);
}

static int parse_script(front *f, const char *text)
{
    f->action_count = 0;
    for (const char *p = text; *p && f->action_count < MAX_ACTIONS;) {
        while (*p == ' ' || *p == ';')
            ++p;
        if (!*p)
            break;
        action *a = &f->actions[f->action_count];
        int used = 0;
        if (sscanf(p, "%d:%63[^ ;]%n", &a->frame, a->what, &used) != 2)
            return 1;
        ++f->action_count;
        p += used;
    }
    return 0;
}

/* NATIVE-APP-001: the offline label and mu-world's features for the world scene. */
static void world_options(const front *f, mu_shell_config *c)
{
    c->label = f->label;
    c->world_combat = f->combat;
    c->world_progress = f->progress;
    c->world_items = f->items;
    c->world_npc = f->npc;
    c->npc_demo = f->npc_demo;
    c->world_no_names = f->no_names;
    c->world_no_env = f->no_env;
    c->world_no_particles = f->no_particles;
    c->helper = f->helper;
    c->helper_state = f->helper_state;
}

/* ---- headless ---- */

static void note_scene(front *f)
{
    int scene = mu_shell_scene(f->shell);
    if (scene != f->last_scene) {
        f->last_scene = scene;
        f->frames_in_scene = 0;
        f->visit[scene & 7]++;
    } else {
        f->frames_in_scene++;
    }
}

static int headless(front *f)
{
    char error[256];
    if (f->out_dir && mkdir(f->out_dir, 0755) && errno != EEXIST) {
        fprintf(stderr, "cannot create %s\n", f->out_dir);
        return 1;
    }
#ifndef MU_CLIENT_NO_GL
    f->gl = f->backend && !strcmp(f->backend, "gl");
    if (f->gl && mu_gl_headless_begin(f->width, f->height, error, sizeof error)) {
        fprintf(stderr, "headless GL: %s\n", error);
        return 1;
    }
    f->dw = f->width;   /* screen_quad's size (the GPU 2D layer's frame write) */
    f->dh = f->height;
#else
    if (f->backend && strcmp(f->backend, "soft")) {
        fprintf(stderr, "mu-shell renders with the software rasterizer only (--backend soft)\n");
        return 2;
    }
    f->gl = 0;
#endif
    if (!f->gl && mu_raster_init(&f->raster, f->width, f->height)) {
        fprintf(stderr, "raster allocation failed\n");
        return 1;
    }
    f->now = 100000;
    f->audio_start = f->now;
    mu_shell_config c;
    memset(&c, 0, sizeof c);
    c.root = f->root;
    c.session_path = f->session;
    c.font = f->font;
    c.width = f->width;
    c.height = f->height;
    c.audio = f->audio;
    c.sound_table = f->sound_table;
    c.placement = f->placement;
    world_options(f, &c);
    c.players = f->players;
    c.world_objects = f->world_objects;
    c.charsel_objects = f->charsel_objects;
    c.login_objects = f->login_objects;
    c.title_step_ms = 0;
    c.quiet = f->quiet;
    c.gfx_dir = f->gfx_dir;
    c.gfx_log = f->gfx_log;
    c.gfx_scale = 1.0;
    c.store_path = f->no_store ? NULL : f->store;   /* headless: in memory unless --store */
    mu_shell_platform p = {f, on_present, on_ticks, on_opened, on_closing, on_pause, NULL, NULL, NULL, NULL, NULL,
                           NULL, NULL, NULL};
#ifndef MU_CLIENT_NO_GL
    if (f->gl && f->gpu_overlay) {   /* NATIVE-PERF-001 */
        p.ui_target = on_ui_target;
        p.ui_target_free = on_ui_target_free;
        p.ui_begin = on_ui_begin;
        p.ui_end = on_ui_end;
        p.image = on_image;
        p.read_frame = on_read_frame;
        p.write_frame = on_write_frame;
#ifdef __APPLE__
        p.surface = on_surface;
#endif
    }
#endif
    f->shell = mu_shell_new(&c, &p, error, sizeof error);
    if (!f->shell) {
        fprintf(stderr, "%s\n", error);
        return 1;
    }
    f->last_scene = mu_shell_scene(f->shell);
    f->visit[f->last_scene & 7] = 1;
    int status = 0;
    if (f->perf_path && mu_perf_open(f->perf_path, f->perf_sync))
        fprintf(stderr, "cannot write %s\n", f->perf_path);
#ifndef MU_CLIENT_NO_GL
    mu_perf_set_sync(glFinish);
#endif
    for (f->frame = 0; f->frame < f->frames && !mu_shell_quit(f->shell); ++f->frame) {
        double perf = mu_perf_begin();
        click_step(f);
        for (int32_t i = 0; i < f->action_count; ++i)
            if (f->actions[i].frame == f->frame)
                do_action(f, f->actions[i].what);
        if (f->autoplay)
            autoplay(f);
        mu_perf_end(MU_PERF_EVENTS, perf);
        perf = mu_perf_begin();
        int before = mu_shell_scene(f->shell);
        mu_shell_frame(f->shell, f->now);
        mu_perf_end(MU_PERF_LOGIC, perf);
        note_scene(f);
        int scene = mu_shell_scene(f->shell);
        f->scene_frames[scene & 7]++;
        compose(f);
        int save = f->out_dir && ((f->every > 0 && f->frame % f->every == 0) || f->frames_in_scene == 0 ||
                                  scene != before || f->frame == f->frames - 1);
        if (save && write_png(f, f->pixels, "frame")) {
            status = 1;
            break;
        }
        f->now += 12;   /* virtual render time, then the client's cap */
        int32_t sleep = mu_shell_end_frame(f->shell, f->now);
        if (sleep > 0)
            f->now += (uint32_t)sleep;
        wav_pump(f, f->now);
        mu_perf_frame(mu_shell_scene(f->shell));   /* headless: no cap sleep, the frame time is its work */
    }
    mu_perf_close();
    const char *const *lines;
    int32_t transitions = mu_shell_transitions(f->shell, &lines);
    const mu_scenemgr_globals *g = mu_shell_globals(f->shell);
    const mu_offline_session *session = mu_shell_session(f->shell);
    printf("{\"summary\": true, \"renderer\": \"%s\", \"frames\": %d, \"scene\": %d, \"captures\": %d, "
           "\"presents\": %d, \"scene_frames\": {\"2\": %d, \"3\": %d, \"4\": %d, \"5\": %d, \"6\": %d}, "
           "\"visits\": {\"3\": %d, \"5\": %d, \"6\": %d}, \"protocol\": %d, \"world\": %d, \"selected_hero\": %d, "
           "\"hero_slot\": %d, \"hero_class\": %u, \"logins\": %d, \"server\": [%d, %d], \"status\": \"%s\", "
           "\"transitions\": [",
#ifndef MU_CLIENT_NO_GL
           f->gl ? mu_gl_renderer() : "software",
#else
           "software",
#endif
           f->frame, mu_shell_scene(f->shell), f->captures, f->presents, f->scene_frames[2], f->scene_frames[3],
           f->scene_frames[4], f->scene_frames[5], f->scene_frames[6], f->visit[3], f->visit[5], f->visit[6],
           g->protocol, g->world, g->selected_hero, mu_shell_hero_slot(f->shell), mu_shell_hero_class(f->shell),
           session->logins, session->server_group, session->server_slot, mu_shell_status(f->shell));
    for (int32_t i = 0; i < transitions; ++i)
        printf("%s\"%s\"", i ? ", " : "", lines[i]);
    long cc[6];
    mu_shell_charsel_counts(f->shell, cc);   /* NATIVE-CHARSEL-003 */
    mu_charsel_create_stats cs;
    long rebuilds = 0;
    mu_shell_charsel_create_stats(f->shell, &cs, &rebuilds);   /* NATIVE-CHARCREATE-001 */
    char last[200];
    size_t n = 0;
    for (const char *p = cs.last_message; *p && n + 3 < sizeof last; ++p) {
        if (*p == '"' || *p == '\\')
            last[n++] = '\\';
        last[n++] = (char)((unsigned char)*p < 0x20 ? ' ' : *p);
    }
    last[n] = 0;
    printf("], \"charsel\": {\"picks\": %ld, \"pick_hits\": %ld, \"double_clicks\": %ld, \"gfx_callbacks\": %ld, "
           "\"gfx_enters\": %ld, \"create_requests\": %ld}, \"charcreate\": {\"create_open\": %d, \"menu_open\": %d, "
           "\"caution_open\": %d, \"preview_class\": %d, \"board\": [%d, %d, %d, %d], \"creates\": %ld, "
           "\"created\": %ld, \"refused\": %ld, \"deletes\": %ld, \"deleted\": %ld, \"messages\": %ld, "
           "\"menu_events\": %ld, \"preview_frames\": %ld, \"rebuilds\": %ld, \"last_message\": \"%s\", "
           "\"characters\": %d}}\n",
           cc[0], cc[1], cc[2], cc[3], cc[4], cc[5], cs.create_open, cs.menu_open, cs.caution_open, cs.preview_class,
           cs.board[0], cs.board[1], cs.board[2], cs.board[3], cs.creates, cs.created, cs.refused, cs.deletes,
           cs.deleted, cs.messages, cs.menu_events, cs.preview_frames, rebuilds, last, session->characters.count);
    if (f->wav_path && f->wav_frames &&
        mu_wav_write16(f->wav_path, f->wav, (uint32_t)f->wav_frames, 2, mu_shell_audio_rate(f->shell))) {
        fprintf(stderr, "cannot write %s\n", f->wav_path);
        status = 1;
    }
    mu_shell_free(f->shell);
    f->shell = NULL;
#ifndef MU_CLIENT_NO_GL
    if (f->gl)
        mu_gl_headless_end();
#endif
    if (!f->gl)
        mu_raster_free(&f->raster);
    free(f->wav);
    return status;
}

/* ---- window ---- */

#ifndef MU_CLIENT_NO_GL
/* NATIVE-PERF-001: the window changed size (a drag, the green button, Ctrl-Cmd-F, another display): the
 * drawable, the shell's 2D layer and 3D views, and the GFx interface follow. */
static void apply_resize(front *f)
{
    int dw = 0, dh = 0, ww = 0, wh = 0;
    SDL_GL_GetDrawableSize(f->window, &dw, &dh);
    SDL_GetWindowSize(f->window, &ww, &wh);
    if (dw < 64 || dh < 64 || ww <= 0)
        return;
    f->scale = (double)dw / (double)ww;
    if (dw == f->dw && dh == f->dh)
        return;
    uint8_t *pixels = realloc(f->pixels, (size_t)dw * (size_t)dh * 4);
    if (!pixels)
        return;
    f->pixels = pixels;
    f->dw = f->width = dw;
    f->dh = f->height = dh;
    if (f->screen_texture) {   /* recreated at the new size by screen_quad */
        glDeleteTextures(1, &f->screen_texture);
        f->screen_texture = 0;
    }
    mu_shell_resize(f->shell, dw, dh);
    if (f->gfx)
        world_gfx_resize(f->gfx, dw, dh);
    if (!f->quiet)
        fprintf(stderr, "window: %d x %d pixels (%d x %d points)\n", dw, dh, ww, wh);
}

static void toggle_fullscreen(front *f)
{
    int on = (SDL_GetWindowFlags(f->window) & SDL_WINDOW_FULLSCREEN) != 0;
    SDL_SetWindowFullscreen(f->window, on ? 0 : SDL_WINDOW_FULLSCREEN_DESKTOP);
    f->fullscreen = !on;
}

/* macOS refuses a full-screen request while another full-screen Space is still closing (a client started
 * right after the previous one quit): ask again while the window has not reached the display's size. */
static void fullscreen_retry(front *f)
{
    if (!f->fullscreen)
        return;
    SDL_DisplayMode mode;
    int ww = 0, wh = 0;
    SDL_GetWindowSize(f->window, &ww, &wh);
    if (SDL_GetDesktopDisplayMode(SDL_GetWindowDisplayIndex(f->window), &mode) != 0 ||
        (ww >= mode.w && wh >= mode.h))
        return;
    SDL_SetWindowFullscreen(f->window, 0);
    SDL_SetWindowFullscreen(f->window, SDL_WINDOW_FULLSCREEN_DESKTOP);
}

static void audio_open(front *f)
{
    if (!f->audio)
        return;
    if (SDL_InitSubSystem(SDL_INIT_AUDIO) != 0)
        return;
    SDL_AudioSpec want, have;
    memset(&want, 0, sizeof want);
    want.freq = (int)mu_shell_audio_rate(f->shell);
    want.format = AUDIO_F32SYS;
    want.channels = 2;
    want.samples = 1024;
    f->audio_device = SDL_OpenAudioDevice(NULL, 0, &want, &have, 0);
    if (f->audio_device)
        SDL_PauseAudioDevice(f->audio_device, 0);
}

static void audio_pump(front *f, uint32_t now)
{
    if (!f->audio_device)
        return;
    uint64_t due = (uint64_t)(now + 120 - f->audio_start) * mu_shell_audio_rate(f->shell) / 1000u;
    if (due <= f->audio_frames)
        return;
    uint32_t frames = (uint32_t)(due - f->audio_frames);
    uint32_t rate = mu_shell_audio_rate(f->shell);
    if (frames > rate)
        frames = rate;
    static float buffer[2 * 48000];
    mu_shell_mix(f->shell, buffer, frames);
    f->audio_frames += frames;
    SDL_QueueAudio(f->audio_device, buffer, frames * 2 * (uint32_t)sizeof(float));
}

static int windowed(front *f)
{
    if (SDL_Init(SDL_INIT_VIDEO) != 0) {
        fprintf(stderr, "SDL_Init: %s\n", SDL_GetError());
        return 1;
    }
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 2);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 1);
    SDL_GL_SetAttribute(SDL_GL_DEPTH_SIZE, 24);
    SDL_GL_SetAttribute(SDL_GL_DOUBLEBUFFER, 1);
    /* NATIVE-PERF-001: resizable, with macOS full screen (the green button; Ctrl-Cmd-F) in its own Space */
    SDL_SetHint(SDL_HINT_VIDEO_MAC_FULLSCREEN_SPACES, "1");
    f->window = SDL_CreateWindow(f->title ? f->title : "Mu The Matrix (native, offline demo)", SDL_WINDOWPOS_CENTERED,
                                 SDL_WINDOWPOS_CENTERED, f->width, f->height,
                                 SDL_WINDOW_OPENGL | SDL_WINDOW_ALLOW_HIGHDPI | SDL_WINDOW_RESIZABLE);
    if (f->window) {
        SDL_SetWindowMinimumSize(f->window, 640, 480);
        if (f->fullscreen)
            SDL_SetWindowFullscreen(f->window, SDL_WINDOW_FULLSCREEN_DESKTOP);
    }
    SDL_GLContext context = f->window ? SDL_GL_CreateContext(f->window) : NULL;
    if (!context) {
        fprintf(stderr, "SDL: %s\n", SDL_GetError());
        return 1;
    }
    SDL_GL_SetSwapInterval(0);   /* the client caps with Sleep, not vsync */
    SDL_GL_GetDrawableSize(f->window, &f->dw, &f->dh);
    f->scale = (double)f->dw / (double)f->width;
    int32_t window_w = f->width;
    f->width = f->dw;           /* everything works in drawable pixels */
    f->height = f->dh;
    f->pixels = realloc(f->pixels, (size_t)f->width * (size_t)f->height * 4);
    f->gl = 1;
    mu_shell_config c;
    memset(&c, 0, sizeof c);
    c.root = f->root;
    c.session_path = f->session;
    c.font = f->font;
    c.width = f->width;
    c.height = f->height;
    c.audio = f->audio;
    c.sound_table = f->sound_table;
    c.placement = f->placement;
    world_options(f, &c);
    c.players = f->players;
    c.world_objects = f->world_objects;
    c.charsel_objects = f->charsel_objects;
    c.login_objects = f->login_objects;
    c.title_step_ms = 150;
    c.quiet = f->quiet;
    c.gfx_dir = f->gfx_dir;
    c.gfx_log = f->gfx_log;
    c.gfx_scale = f->scale;
    /* NATIVE-CHARCREATE-001: the window keeps the characters created offline (--store, --no-store) */
    if (!f->no_store && !f->store && getenv("HOME")) {
        snprintf(f->store_default, sizeof f->store_default,
                 "%s/Library/Application Support/MuTheMatrixNative/offline-characters.txt", getenv("HOME"));
        f->store = f->store_default;
    }
    c.store_path = f->no_store ? NULL : f->store;
    mu_shell_platform p = {f, on_present, on_ticks, on_opened, on_closing, on_pause, NULL, NULL, NULL, NULL, NULL,
                           NULL, NULL, NULL};
#ifndef MU_CLIENT_NO_GL
    if (f->gl && f->gpu_overlay) {   /* NATIVE-PERF-001 */
        p.ui_target = on_ui_target;
        p.ui_target_free = on_ui_target_free;
        p.ui_begin = on_ui_begin;
        p.ui_end = on_ui_end;
        p.image = on_image;
        p.read_frame = on_read_frame;
        p.write_frame = on_write_frame;
#ifdef __APPLE__
        p.surface = on_surface;
#endif
    }
#endif
    char error[256];
    f->shell = mu_shell_new(&c, &p, error, sizeof error);
    if (!f->shell) {
        fprintf(stderr, "%s\n", error);
        return 1;
    }
    audio_open(f);
    f->audio_start = SDL_GetTicks();
    uint32_t start = SDL_GetTicks(), frames = 0;
    (void)window_w;
    if (f->perf_path && mu_perf_open(f->perf_path, f->perf_sync))
        fprintf(stderr, "cannot write %s\n", f->perf_path);
    mu_perf_set_sync(glFinish);
    f->last_scene = mu_shell_scene(f->shell);
    f->visit[f->last_scene & 7] = 1;
    uint32_t fps_start = start, fps_frames = 0;
    /* NATIVE-PERF-001: the preview app's launcher sets MU_EXIT_WITH_PARENT; the client quits when the launcher
     * is gone (re-parented), so a killed launcher does not leave the game running */
    const char *with_parent = getenv("MU_EXIT_WITH_PARENT");
    pid_t parent = with_parent && with_parent[0] == '1' ? getppid() : 0;
    int resized = 1;   /* a full-screen start or a display with another scale */
    while (!mu_shell_quit(f->shell)) {
        if (parent && getppid() != parent) {
            fprintf(stderr, "the launcher is gone: quitting\n");
            break;
        }
        double perf = mu_perf_begin();
        /* NATIVE-PERF-001: the frame starts before the event pump, as the client's idle loop reads the clock
         * before PeekMessage; the login/title cap Sleep(40 - elapsed) then covers the whole pass */
        uint32_t now = SDL_GetTicks();
        SDL_Event e;
        while (SDL_PollEvent(&e)) {
            if (e.type == SDL_WINDOWEVENT && (e.window.event == SDL_WINDOWEVENT_SIZE_CHANGED ||
                                              e.window.event == SDL_WINDOWEVENT_RESIZED)) {
                resized = 1;
                continue;
            }
            if (e.type == SDL_KEYDOWN && e.key.keysym.scancode == SDL_SCANCODE_F &&
                (e.key.keysym.mod & KMOD_GUI) && (e.key.keysym.mod & KMOD_CTRL)) {
                if (!e.key.repeat)
                    toggle_fullscreen(f);   /* the macOS full-screen shortcut, not a game key */
                continue;
            }
            if (e.type == SDL_KEYDOWN && !e.key.repeat && (e.key.keysym.scancode == SDL_SCANCODE_PRINTSCREEN ||
                                                          e.key.keysym.scancode == SDL_SCANCODE_F13) &&
                mu_shell_scene(f->shell) != MU_SCENE_LOGIN) {   /* the screenshot (O opens the options window) */
                snprintf(f->shot, sizeof f->shot, "mu-client-screenshot.png");
                continue;
            }
            if (f->gfx && mu_shell_scene(f->shell) == MU_SCENE_MAIN && world_gfx_event(f->gfx, &e, f->scale))
                continue;   /* the GFx interface took it */
            if (e.type == SDL_QUIT) {
                mu_shell_request_quit(f->shell);
            } else if (e.type == SDL_MOUSEMOTION) {
                mu_shell_mouse_move(f->shell, (int32_t)(e.motion.x * f->scale), (int32_t)(e.motion.y * f->scale));
            } else if (e.type == SDL_MOUSEBUTTONDOWN || e.type == SDL_MOUSEBUTTONUP) {
                mu_shell_mouse_move(f->shell, (int32_t)(e.button.x * f->scale), (int32_t)(e.button.y * f->scale));
                int button = e.button.button == SDL_BUTTON_LEFT ? 0 : e.button.button == SDL_BUTTON_RIGHT ? 1 : 2;
                mu_shell_mouse_button(f->shell, button, e.type == SDL_MOUSEBUTTONDOWN);
            } else if (e.type == SDL_MOUSEWHEEL) {
                mu_shell_wheel(f->shell, e.wheel.y);
            } else if (e.type == SDL_KEYDOWN || e.type == SDL_KEYUP) {
                if (e.type == SDL_KEYDOWN && e.key.repeat)
                    continue;
                int vk = mu_vk_from_hid((int)e.key.keysym.scancode);
                mu_shell_key(f->shell, vk, e.type == SDL_KEYDOWN);
                if (e.type == SDL_KEYDOWN && vk == 0x4f && mu_shell_scene(f->shell) != MU_SCENE_LOGIN)
                    snprintf(f->shot, sizeof f->shot, "mu-client-screenshot.png");   /* O, read before the swap */
            } else if (e.type == SDL_TEXTINPUT) {
                for (const char *t = e.text.text; *t; ++t)
                    mu_shell_char(f->shell, (unsigned char)*t);
            }
        }
        if (frames == 75 || frames == 150)   /* after the full-screen animation (about 1 s) */
            fullscreen_retry(f);
        if (resized) {
            apply_resize(f);
            resized = 0;
        }
        /* NATIVE-PERF-001: the scripted flow (--auto [--hold SCENE], --script) in the window as headless */
        f->frame = (int32_t)frames;
        click_step(f);
        for (int32_t i = 0; i < f->action_count; ++i)
            if (f->actions[i].frame == f->frame)
                do_action(f, f->actions[i].what);
        if (f->autoplay)
            autoplay(f);
        mu_perf_end(MU_PERF_EVENTS, perf);
        perf = mu_perf_begin();
        mu_shell_frame(f->shell, now);
        mu_perf_end(MU_PERF_LOGIC, perf);
        note_scene(f);
        if (mu_shell_quit(f->shell))
            break;
        compose(f);
        perf = mu_perf_begin();
        if (!mu_shell_gpu_overlay(f->shell))
            screen_quad(f, f->pixels);
        mu_perf_end(MU_PERF_PRESENT, perf);
        if (f->shot[0]) {   /* the finished frame, still in the back buffer */
            glFinish();
            mu_gl_read(f->width, f->height, f->pixels);
            if (mu_png_write(f->shot, f->pixels, f->width, f->height))
                fprintf(stderr, "cannot write %s\n", f->shot);
            else if (!f->quiet)
                fprintf(stderr, "capture %s (%d x %d)\n", f->shot, f->width, f->height);
            f->shot[0] = 0;
        }
        perf = mu_perf_begin();
        SDL_GL_SwapWindow(f->window);
        mu_perf_end(MU_PERF_SWAP, perf);
        ++frames;
        perf = mu_perf_now();
        audio_pump(f, SDL_GetTicks());   /* before the cap: it is the host's, the cap measures the whole pass */
        int32_t sleep = mu_shell_end_frame(f->shell, SDL_GetTicks());
        if (sleep > 0)
            mu_sleep_ms((uint32_t)sleep);   /* NATIVE-PERF-001: the host Sleep without oversleep */
        if (mu_perf_enabled())
            mu_perf_add(MU_PERF_SLEEP, mu_perf_now() - perf);
        mu_perf_frame(mu_shell_scene(f->shell));
        if (frames % 25 == 0) {
            static const char *names[8] = {"", "", "title", "login", "loading", "character select", "world", ""};
            char title[400];
            int scene = mu_shell_scene(f->shell);
            /* NATIVE-PERF-001: the rate of the last 25 frames (the run's average counted the loading) */
            uint32_t t = SDL_GetTicks();
            snprintf(title, sizeof title, "%s  scene %d %s  %.1f fps",
                     f->title ? f->title : "Mu The Matrix (native, OFFLINE DEMO)", scene, names[scene & 7],
                     (double)(frames - fps_frames) * 1000.0 / (double)(t - fps_start + 1));
            fps_start = t;
            fps_frames = frames;
            SDL_SetWindowTitle(f->window, title);
        }
        if (f->seconds > 0 && (SDL_GetTicks() - start) / 1000.0 >= f->seconds)
            break;
    }
    printf("{\"frames\": %u, \"seconds\": %.2f, \"scene\": %d, \"drawable\": [%d, %d], \"gpu_overlay\": %s}\n",
           frames, (SDL_GetTicks() - start) / 1000.0, mu_shell_scene(f->shell), f->dw, f->dh,
           mu_shell_gpu_overlay(f->shell) ? "true" : "false");
    mu_perf_close();
    mu_shell_free(f->shell);
    f->shell = NULL;
    if (f->screen_texture)
        glDeleteTextures(1, &f->screen_texture);
    if (f->image_texture)
        glDeleteTextures(1, &f->image_texture);
    if (f->surface_texture)
        glDeleteTextures(1, &f->surface_texture);
    if (f->audio_device)
        SDL_CloseAudioDevice(f->audio_device);
    SDL_GL_DeleteContext(context);
    SDL_DestroyWindow(f->window);
    SDL_Quit();
    return 0;
}
#endif

static int usage(void)
{
    fprintf(stderr,
            "usage: mu-client --game-root ROOT [--session FILE] [--width W --height H] [--font FACE]\n"
            "                 [--sound-table TSV] [--placement FILE] [--players FILE] [--helper ITEM] [--helper-state N]\n"
            "                 [--no-audio] [--seconds S]\n"
            "                 [--world-objects DIR] [--charsel-objects DIR] [--login-objects DIR] [--objects-dir DIR]\n"
            "                 [--headless --out-dir DIR --backend gl|soft --frames N --every K]\n"
            "                 [--auto | --script \"F:ACTION ...\"] [--wav OUT.wav] [--quiet]\n"
            "                 [--gfx DIR [--gfx-open inventory,character] [--gfx-log FILE]]\n"
            "                 [--combat] [--items] [--npc] [--npc-demo FILE] [--no-names] [--no-env] [--no-particles]\n"
            "                 [--progress]   experience, levels and stat points (demo server)\n"
            "                 [--label TEXT] [--title TEXT] [--store FILE | --no-store]\n"
            "                 [--fullscreen] [--perf FILE [--perf-sync]] [--hold SCENE] [--cpu-overlay | --gpu-overlay]\n");
    return 2;
}

int main(int argc, char **argv)
{
    static front f;
    memset(&f, 0, sizeof f);
    f.width = 1280;
    f.height = 800;
    f.frames = 400;
    f.every = 0;
    f.audio = 1;
    f.font = "Tahoma";
    f.helper_state = -1;   /* NATIVE-HELPERS-001: the helper name's ride state */
#ifdef MU_CLIENT_NO_GL
    f.headless = 1;
    f.backend = "soft";
#else
    f.backend = "gl";
#endif
    for (int i = 1; i < argc; ++i) {
        const char *k = argv[i], *v = i + 1 < argc ? argv[i + 1] : NULL;
        if (!strcmp(k, "--headless")) { f.headless = 1; continue; }
        if (!strcmp(k, "--quiet")) { f.quiet = 1; continue; }
        if (!strcmp(k, "--no-audio")) { f.audio = 0; continue; }
        if (!strcmp(k, "--auto")) { f.autoplay = 1; continue; }
        if (!strcmp(k, "--combat")) { f.combat = 1; continue; }   /* NATIVE-APP-001 */
        if (!strcmp(k, "--progress")) { f.progress = 1; continue; }   /* NATIVE-PROGRESS-001 */
        if (!strcmp(k, "--items")) { f.items = 1; continue; }
        if (!strcmp(k, "--npc")) { f.npc = 1; continue; }
        if (!strcmp(k, "--no-names")) { f.no_names = 1; continue; }
        if (!strcmp(k, "--no-env")) { f.no_env = 1; continue; }
        if (!strcmp(k, "--no-particles")) { f.no_particles = 1; continue; }
        if (!strcmp(k, "--no-store")) { f.no_store = 1; continue; }
        if (!strcmp(k, "--perf-sync")) { f.perf_sync = 1; continue; }   /* NATIVE-PERF-001 */
        if (!strcmp(k, "--gpu-overlay")) { f.gpu_overlay = 1; continue; }
        if (!strcmp(k, "--fullscreen")) { f.fullscreen = 1; continue; }
        if (!strcmp(k, "--cpu-overlay")) { f.gpu_overlay = -1; continue; }
        if (!v)
            return usage();
        ++i;
        if (!strcmp(k, "--game-root")) f.root = v;
        else if (!strcmp(k, "--session")) f.session = v;
        else if (!strcmp(k, "--width")) f.width = atoi(v);
        else if (!strcmp(k, "--height")) f.height = atoi(v);
        else if (!strcmp(k, "--font")) f.font = v;
        else if (!strcmp(k, "--sound-table")) f.sound_table = v;
        else if (!strcmp(k, "--placement")) f.placement = v;
        else if (!strcmp(k, "--players")) f.players = v;
        else if (!strcmp(k, "--helper")) f.helper = v;
        else if (!strcmp(k, "--helper-state")) f.helper_state = atoi(v);
        else if (!strcmp(k, "--world-objects")) f.world_objects = v;
        else if (!strcmp(k, "--charsel-objects")) f.charsel_objects = v;
        else if (!strcmp(k, "--login-objects")) f.login_objects = v;
        else if (!strcmp(k, "--objects-dir")) f.world_objects = f.charsel_objects = f.login_objects = v;
        else if (!strcmp(k, "--seconds")) f.seconds = strtof(v, NULL);
        else if (!strcmp(k, "--out-dir")) f.out_dir = v;
        else if (!strcmp(k, "--backend")) f.backend = v;
        else if (!strcmp(k, "--frames")) f.frames = atoi(v);
        else if (!strcmp(k, "--every")) f.every = atoi(v);
        else if (!strcmp(k, "--wav")) f.wav_path = v;
        else if (!strcmp(k, "--script")) { if (parse_script(&f, v)) return usage(); }
        else if (!strcmp(k, "--gfx")) f.gfx_dir = v;
        else if (!strcmp(k, "--gfx-open")) f.gfx_open = v;
        else if (!strcmp(k, "--gfx-log")) f.gfx_log = v;
        else if (!strcmp(k, "--npc-demo")) { f.npc_demo = v; f.npc = 1; }
        else if (!strcmp(k, "--label")) f.label = v;
        else if (!strcmp(k, "--title")) f.title = v;
        else if (!strcmp(k, "--store")) f.store = v;
        else if (!strcmp(k, "--perf")) f.perf_path = v;
        else if (!strcmp(k, "--hold")) { f.hold_scene = atoi(v); f.autoplay = 1; }
        else return usage();
    }
    if (!f.root || f.width < 64 || f.height < 64 || f.width > 8192 || f.height > 8192 || f.frames < 1)
        return usage();
    f.pixels = malloc((size_t)f.width * (size_t)f.height * 4);
    if (!f.pixels)
        return 1;
#ifndef MU_CLIENT_NO_GL
    f.gpu_overlay = f.headless ? f.gpu_overlay == 1 : f.gpu_overlay > 0 || (f.gpu_overlay == 0 && !mu_perf_baseline());
    int status = f.headless ? headless(&f) : windowed(&f);
#else
    int status = headless(&f);
#endif
    free(f.pixels);
    return status;
}
