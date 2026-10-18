/* mu-client: the client's scene flow natively, offline (NATIVE-SHELL-001).
 *
 * Title -> login (server select, OFFLINE DEMO account panel) -> character
 * select -> loading screen -> world -> Esc back to character select, run by
 * the reconstructed scene manager (client/shell.c) over the existing native
 * modules. There is no server connection: client/offline-session.* answers
 * what the network layer would (server list, login, character list, join).
 *
 *   mu-client --game-root ROOT [--session FILE] [--width W --height H]
 *             [--sound-table TSV] [--placement FILE] [--no-audio] [--seconds S]
 *   mu-client --game-root ROOT --headless --out-dir DIR [--backend gl|soft]
 *             [--frames N] [--every K] [--auto | --script "F:ACTION ..."] [--wav OUT.wav]
 *
 * Headless actions (frame numbers count dispatcher passes): enter, esc, left,
 * right, tab, back, text:STRING, click:group:N, click:server:N, click:X,Y,
 * wheel:+1/-1, quit. --auto plays the whole flow (server, login, select,
 * world, back to select, world again). Captures: every K-th frame, the first
 * frame of each scene visit and every title/loading frame.
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

#ifndef MU_CLIENT_NO_GL
#include <SDL.h>
#ifdef __APPLE__
#include <OpenGL/gl.h>
#else
#include <GL/gl.h>
#endif
#include "../login/login_gl.h"
#include "../viewer/gl_backend.h"
#include "../viewer/gl_headless.h"
#endif

#include "../core/mu_frame.h"
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
    const char *root, *session, *out_dir, *backend, *sound_table, *placement, *wav_path, *font;
    const char *world_objects, *charsel_objects, *login_objects;
    int32_t width, height, frames, every, headless, audio, quiet, autoplay;
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
    SDL_Window *window;
    GLuint screen_texture;
    int32_t dw, dh;
    double scale;
    SDL_AudioDeviceID audio_device;
    mu_login_gl *login_gl;   /* NATIVE-LOGIN-001 */
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
    if (f->headless) {
        char tag[32];
        snprintf(tag, sizeof tag, "present%02d", f->presents);
        write_png(f, rgba, tag);
        f->now += 40;
        return;
    }
#ifndef MU_CLIENT_NO_GL
    screen_quad(f, rgba);
    SDL_GL_SwapWindow(f->window);
    SDL_PumpEvents();
#endif
}

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
    SDL_Delay(ms);
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
    if (view == MU_SHELL_VIEW_2D) {
        for (size_t i = 0; i < bytes; i += 4) {
            f->pixels[i] = f->pixels[i + 1] = f->pixels[i + 2] = 0;
            f->pixels[i + 3] = 255;
        }
    } else if (f->gl) {
#ifndef MU_CLIENT_NO_GL
        if (view == MU_SHELL_VIEW_LOGIN && f->login_gl)
            mu_login_gl_draw(f->login_gl, mu_shell_login(f->shell), f->width, f->height);
        else if (view == MU_SHELL_VIEW_CHARSEL)
            mu_charsel_embed_draw_gl(mu_shell_charsel(f->shell), f->width, f->height);
        else
            mu_world_embed_draw_gl(mu_shell_world(f->shell), f->width, f->height);
        glFinish();
        mu_gl_read(f->width, f->height, f->pixels);
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
    mu_shell_overlay(f->shell, f->pixels);
}

/* ---- scripted input ---- */

static void click(front *f, int32_t x, int32_t y)
{
    f->click_x = x;
    f->click_y = y;
    mu_shell_mouse_move(f->shell, x, y);
    f->click_stage = 1;
}

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
    } else if (sscanf(what, "click:%d,%d", &x, &y) == 2) {
        click(f, x, y);
    } else if (sscanf(what, "wheel:%d", &n) == 1) {
        mu_shell_wheel(s, n);
    } else if (!strcmp(what, "quit")) {
        mu_shell_request_quit(s);
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
    if (scene == MU_SCENE_LOGIN) {
        if (k == 8) what = "click:group:0";
        else if (k == 16) what = "click:server:0";
        else if (k == 22) what = "text:demo";
        else if (k == 24) what = "tab";
        else if (k == 25) what = "text:secret";
        else if (k == 28) what = "enter";
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
    c.world_objects = f->world_objects;
    c.charsel_objects = f->charsel_objects;
    c.login_objects = f->login_objects;
    c.title_step_ms = 0;
    c.quiet = f->quiet;
    mu_shell_platform p = {f, on_present, on_ticks, on_opened, on_closing, on_pause};
    f->shell = mu_shell_new(&c, &p, error, sizeof error);
    if (!f->shell) {
        fprintf(stderr, "%s\n", error);
        return 1;
    }
    f->last_scene = mu_shell_scene(f->shell);
    f->visit[f->last_scene & 7] = 1;
    int status = 0;
    for (f->frame = 0; f->frame < f->frames && !mu_shell_quit(f->shell); ++f->frame) {
        click_step(f);
        for (int32_t i = 0; i < f->action_count; ++i)
            if (f->actions[i].frame == f->frame)
                do_action(f, f->actions[i].what);
        if (f->autoplay)
            autoplay(f);
        int before = mu_shell_scene(f->shell);
        mu_shell_frame(f->shell, f->now);
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
    }
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
    printf("]}\n");
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
    f->window = SDL_CreateWindow("Mu The Matrix (native, offline demo)", SDL_WINDOWPOS_CENTERED,
                                 SDL_WINDOWPOS_CENTERED, f->width, f->height,
                                 SDL_WINDOW_OPENGL | SDL_WINDOW_ALLOW_HIGHDPI);
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
    c.world_objects = f->world_objects;
    c.charsel_objects = f->charsel_objects;
    c.login_objects = f->login_objects;
    c.title_step_ms = 150;
    c.quiet = f->quiet;
    mu_shell_platform p = {f, on_present, on_ticks, on_opened, on_closing, on_pause};
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
    while (!mu_shell_quit(f->shell)) {
        SDL_Event e;
        while (SDL_PollEvent(&e)) {
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
                if (e.type == SDL_KEYDOWN && vk == 0x4f && mu_shell_scene(f->shell) != MU_SCENE_LOGIN) {
                    mu_png_write("mu-client-screenshot.png", f->pixels, f->width, f->height);   /* O */
                }
            } else if (e.type == SDL_TEXTINPUT) {
                for (const char *t = e.text.text; *t; ++t)
                    mu_shell_char(f->shell, (unsigned char)*t);
            }
        }
        uint32_t now = SDL_GetTicks();
        mu_shell_frame(f->shell, now);
        if (mu_shell_quit(f->shell))
            break;
        compose(f);
        screen_quad(f, f->pixels);
        SDL_GL_SwapWindow(f->window);
        ++frames;
        int32_t sleep = mu_shell_end_frame(f->shell, SDL_GetTicks());
        if (sleep > 0)
            SDL_Delay((uint32_t)sleep);
        audio_pump(f, SDL_GetTicks());
        if (frames % 25 == 0) {
            static const char *names[8] = {"", "", "title", "login", "loading", "character select", "world", ""};
            char title[160];
            int scene = mu_shell_scene(f->shell);
            snprintf(title, sizeof title, "Mu The Matrix (native, OFFLINE DEMO)  scene %d %s  %.1f fps", scene,
                     names[scene & 7], (double)frames * 1000.0 / (double)(SDL_GetTicks() - start + 1));
            SDL_SetWindowTitle(f->window, title);
        }
        if (f->seconds > 0 && (SDL_GetTicks() - start) / 1000.0 >= f->seconds)
            break;
    }
    printf("{\"frames\": %u, \"seconds\": %.2f, \"scene\": %d}\n", frames, (SDL_GetTicks() - start) / 1000.0,
           mu_shell_scene(f->shell));
    mu_shell_free(f->shell);
    f->shell = NULL;
    if (f->screen_texture)
        glDeleteTextures(1, &f->screen_texture);
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
            "                 [--sound-table TSV] [--placement FILE] [--no-audio] [--seconds S]\n"
            "                 [--world-objects DIR] [--charsel-objects DIR] [--login-objects DIR] [--objects-dir DIR]\n"
            "                 [--headless --out-dir DIR --backend gl|soft --frames N --every K]\n"
            "                 [--auto | --script \"F:ACTION ...\"] [--wav OUT.wav] [--quiet]\n");
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
        else return usage();
    }
    if (!f.root || f.width < 64 || f.height < 64 || f.width > 8192 || f.height > 8192 || f.frames < 1)
        return usage();
    f.pixels = malloc((size_t)f.width * (size_t)f.height * 4);
    if (!f.pixels)
        return 1;
#ifndef MU_CLIENT_NO_GL
    int status = f.headless ? headless(&f) : windowed(&f);
#else
    int status = headless(&f);
#endif
    free(f.pixels);
    return status;
}
