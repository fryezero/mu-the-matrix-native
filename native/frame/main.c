/* mu-frame-window: SDL2 + OpenGL front end of the native frame-loop skeleton
 * (NATIVE-FRAME-001).
 *
 * The loop is the client's frame driver: logic in fixed 40 ms steps from an
 * accumulator, the frame started from GetTickCount (SDL_GetTicks), and a cap
 * that sleeps 40 - elapsed milliseconds after the swap (25 FPS). Camera,
 * zoom, picking and input state are the reconstructed client routines; the
 * terrain is a flat placeholder and the hero walks in a straight line.
 *
 *   mu-frame-window [MODEL.bmd] [--width W --height H] [--seconds S]
 *   mu-frame-window [MODEL.bmd] --headless --frames N --out-dir DIR   (CGL/GLX offscreen)
 *   mu-frame-window --gl-check     compare the reference camera matrices with the GL driver
 *
 * Input (client mapping): left click moves (hold to follow the cursor),
 * Shift holds position, mouse wheel zooms (FOV 35/30/20 with the client's
 * pitch and height transition), keys are scanned once per logic step into the
 * client's four-state table and logged with the client action they map to.
 * Esc twice (or closing the window) quits.
 */
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#include <SDL.h>
#ifdef __APPLE__
#include <OpenGL/gl.h>
#include <OpenGL/glu.h>
#else
#include <GL/gl.h>
#include <GL/glu.h>
#endif

#include "../core/mu_bmd.h"
#include "../core/mu_frame.h"
#include "../core/mu_model.h"
#include "../core/mu_png.h"
#include "../core/mu_scene.h"
#include "../core/mu_textures.h"
#include "../viewer/gl_backend.h"
#include "../viewer/gl_headless.h"

typedef struct hero_model {
    int loaded;
    mu_bmd bmd;
    mu_model model;
    mu_textures textures;
    mu_model_params params;
    uint16_t action;
} hero_model;

static int load_model(hero_model *h, const char *path)
{
    char error[512];
    memset(h, 0, sizeof *h);
    if (mu_bmd_load_file(path, &h->bmd, error, sizeof error) != MU_BMD_OK) {
        fprintf(stderr, "%s: %s\n", path, error);
        return 1;
    }
    mu_model_default_params(&h->params);
    if (mu_model_init(&h->model, &h->bmd, &h->params, error, sizeof error) != MU_MODEL_OK) {
        fprintf(stderr, "%s: %s\n", path, error);
        return 1;
    }
    char directory[4096];
    mu_path_directory(path, directory, sizeof directory);
    mu_textures_load(&h->textures, &h->bmd, directory);
    h->loaded = 1;
    return 0;
}

static void animate_model(hero_model *h, const mu_frame_world *w, int32_t steps)
{
    if (!h->loaded)
        return;
    uint16_t action = (w->moving && h->bmd.action_count > 2) ? 2 : 0;  /* placeholder action choice */
    if (action != h->action) {
        h->action = action;
        mu_model_set_state(&h->model, action, 0.0f, 0.0f, action);
    }
    uint8_t loop;
    for (int32_t k = 0; k < steps; ++k)
        mu_model_tick(&h->model, 0.25f, &loop);
    memcpy(h->params.origin, w->hero, sizeof w->hero);
    h->params.angles[2] = w->hero_angle;
    mu_model_apply_params(&h->model, &h->params);
    mu_model_update(&h->model);
}

static void draw(const mu_frame_world *w, hero_model *hero, mu_gl_backend *gl)
{
    static const uint8_t sky[4] = {28, 34, 48, 255};
    mu_gl_frame((int32_t)w->view.window_width, (int32_t)w->view.window_height, sky, w->view.modelview,
                w->view.projection);
    glViewport(w->view.gl_viewport[0], w->view.gl_viewport[1], w->view.gl_viewport[2], w->view.gl_viewport[3]);
    mu_render_backend backend;
    mu_gl_backend_bind(gl, &backend);
    mu_frame_draw_world(w, &backend, 26, !hero->loaded);
    if (hero->loaded) {
        mu_draw_options options;
        mu_draw_default_options(&options);
        mu_draw_stats stats = {0, 0, 0};
        mu_scene_draw_model(&hero->model, &options, &backend, &stats);
    }
}

static uint32_t pack(int x, int y)
{
    return ((uint32_t)(uint16_t)y << 16) | (uint16_t)x;
}

/* ---- GL driver check ---- */

static int ulps(float a, float b)
{
    int32_t ia, ib;
    memcpy(&ia, &a, 4);
    memcpy(&ib, &b, 4);
    if (ia < 0)
        ia = (int32_t)0x80000000 - ia;
    if (ib < 0)
        ib = (int32_t)0x80000000 - ib;
    return abs(ia - ib);
}

static int gl_check(void)
{
    char error[256];
    if (mu_gl_headless_begin(64, 64, error, sizeof error)) {
        fprintf(stderr, "headless GL: %s\n", error);
        return 1;
    }
    int worst_mv = 0, worst_proj = 0, exact_mv = 0, exact_proj = 0, cases = 0;
    double worst_abs = 0;
    uint32_t seed = 12345;
    for (int k = 0; k < 2000; ++k) {
        mu_client_view v;
        memset(&v, 0, sizeof v);
        seed = seed * 1103515245u + 12345u;
        v.window_width = 640u + (seed >> 20) % 2000u;
        seed = seed * 1103515245u + 12345u;
        v.window_height = 480u + (seed >> 20) % 1200u;
        seed = seed * 1103515245u + 12345u;
        v.fov = k % 3 ? 35.0f : 10.0f + (float)((seed >> 16) % 60);
        v.view_near = 20.0f;
        v.view_far = 2000.0f + (float)(k % 7) * 200.0f;
        seed = seed * 1103515245u + 12345u;
        v.angle[0] = k % 2 ? -48.5f : -(float)((seed >> 16) % 9000) / 100.0f;
        v.angle[1] = k % 5 == 0 ? (float)((seed >> 8) % 500) / 100.0f : 0.0f;
        v.angle[2] = k % 4 ? -45.0f : (float)((seed >> 4) % 36000) / 100.0f - 180.0f;
        seed = seed * 1103515245u + 12345u;
        v.position[0] = (float)((seed >> 8) % 2560000) / 100.0f;
        seed = seed * 1103515245u + 12345u;
        v.position[1] = (float)((seed >> 8) % 2560000) / 100.0f;
        v.position[2] = 850.0f - (float)(k % 300);
        v.top_view = (uint8_t)(k % 17 == 0);
        mu_view_begin_opengl(&v, 0, 0, 640, 480);
        /* the client's own GL calls, executed by this machine's GL driver */
        glMatrixMode(GL_PROJECTION);
        glLoadIdentity();
        gluPerspective((double)v.fov, (double)((float)v.screen_width / (float)v.screen_height), (double)v.view_near,
                       (double)(v.view_far * 1.4f));
        glMatrixMode(GL_MODELVIEW);
        glLoadIdentity();
        glRotatef(v.angle[1], 0.0f, 1.0f, 0.0f);
        if (!v.top_view)
            glRotatef(v.angle[0], 1.0f, 0.0f, 0.0f);
        glRotatef(v.angle[2], 0.0f, 0.0f, 1.0f);
        glTranslatef(-v.position[0], -v.position[1], -v.position[2]);
        float mv[16], pr[16];
        glGetFloatv(GL_MODELVIEW_MATRIX, mv);
        glGetFloatv(GL_PROJECTION_MATRIX, pr);
        int m1 = 0, m2 = 0;
        for (int i = 0; i < 16; ++i) {
            int d = ulps(mv[i], v.modelview[i]);
            if (d > m1)
                m1 = d;
            double a = fabs((double)mv[i] - (double)v.modelview[i]);
            if (a > worst_abs)
                worst_abs = a;
            d = ulps(pr[i], v.projection[i]);
            if (d > m2)
                m2 = d;
        }
        exact_mv += m1 == 0;
        exact_proj += m2 == 0;
        if (m1 > worst_mv)
            worst_mv = m1;
        if (m2 > worst_proj)
            worst_proj = m2;
        ++cases;
    }
    printf("{\"gl_renderer\": \"%s\", \"cases\": %d, \"modelview_bit_exact\": %d, \"modelview_max_ulp\": %d,"
           " \"modelview_max_abs\": %.9g, \"projection_bit_exact\": %d, \"projection_max_ulp\": %d}\n",
           mu_gl_renderer(), cases, exact_mv, worst_mv, worst_abs, exact_proj, worst_proj);
    mu_gl_headless_end();
    return 0;
}

/* ---- headless run ---- */

static int headless(const char *model_path, int32_t width, int32_t height, int32_t frames, const char *out_dir)
{
    char error[256];
    if (out_dir && mkdir(out_dir, 0755) && errno != EEXIST) {
        fprintf(stderr, "cannot create %s\n", out_dir);
        return 1;
    }
    if (mu_gl_headless_begin(width, height, error, sizeof error)) {
        fprintf(stderr, "headless GL: %s\n", error);
        return 1;
    }
    hero_model hero;
    memset(&hero, 0, sizeof hero);
    if (model_path && load_model(&hero, model_path))
        return 1;
    mu_gl_backend gl;
    memset(&gl, 0, sizeof gl);
    if (hero.loaded)
        mu_gl_upload(&gl, hero.textures.slots, hero.textures.count, 0);
    static mu_frame_world world;
    mu_frame_world_init(&world, (uint32_t)width, (uint32_t)height, 128, 128);
    uint8_t *pixels = malloc((size_t)width * (size_t)height * 4);
    if (!pixels)
        return 1;
    uint32_t now = 100000;
    world.clock.frame_tick = now;
    for (int32_t frame = 0; frame < frames; ++frame) {
        /* the client picks with the ray of the previous render pass, so the
         * cursor moves one frame before the click */
        if (frame == 3)
            mu_frame_world_message(&world, 0x200, 0, pack(width * 3 / 4, height * 2 / 3));
        if (frame == 4)
            mu_frame_world_message(&world, 0x201, 1, pack(width * 3 / 4, height * 2 / 3));
        if (frame == 5)
            mu_frame_world_message(&world, 0x202, 0, pack(width * 3 / 4, height * 2 / 3));
        if (frame == 30)
            mu_frame_world_message(&world, 0x20a, 120u << 16, pack(width * 3 / 4, height * 2 / 3));
        int32_t steps = mu_frame_world_update(&world, now);
        animate_model(&hero, &world, steps);
        mu_frame_world_begin_render(&world, now);
        draw(&world, &hero, &gl);
        glFinish();
        if (out_dir && (frame % 15 == 14 || frame == frames - 1)) {
            mu_gl_read(width, height, pixels);
            char path[4096], hash[65];
            snprintf(path, sizeof path, "%s/gl-frame-%03d.png", out_dir, frame);
            mu_png_write(path, pixels, width, height);
            mu_sha256_hex(pixels, (uint64_t)width * (uint64_t)height * 4, hash);
            printf("{\"frame\": %d, \"fov\": %.3f, \"pitch\": %.3f, \"hero\": [%.1f, %.1f], \"target_tile\": [%d, %d],"
                   " \"sha256\": \"%s\", \"png\": \"%s\"}\n", frame, (double)world.view.fov, (double)world.view.angle[0],
                   (double)world.hero[0], (double)world.hero[1], world.target_tile[0], world.target_tile[1], hash, path);
        }
        now += 12;
        int32_t sleep = mu_frame_world_end_render(&world);
        if (sleep > 0)
            now += (uint32_t)sleep;
    }
    printf("{\"gl_renderer\": \"%s\", \"frames\": %d, \"logic_steps\": %u}\n", mu_gl_renderer(), frames,
           world.clock.logic_steps);
    free(pixels);
    mu_gl_release(&gl);
    mu_gl_headless_end();
    return 0;
}

/* ---- window ---- */

static int windowed(const char *model_path, int32_t width, int32_t height, double seconds)
{
    if (SDL_Init(SDL_INIT_VIDEO) != 0) {
        fprintf(stderr, "SDL_Init: %s\n", SDL_GetError());
        return 1;
    }
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 2);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 1);
    SDL_GL_SetAttribute(SDL_GL_DEPTH_SIZE, 24);
    SDL_GL_SetAttribute(SDL_GL_DOUBLEBUFFER, 1);
    SDL_Window *window = SDL_CreateWindow("mu-frame-window", SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED, width,
                                          height, SDL_WINDOW_OPENGL | SDL_WINDOW_ALLOW_HIGHDPI);
    if (!window) {
        fprintf(stderr, "SDL_CreateWindow: %s\n", SDL_GetError());
        return 1;
    }
    SDL_GLContext context = SDL_GL_CreateContext(window);
    if (!context) {
        fprintf(stderr, "SDL_GL_CreateContext: %s\n", SDL_GetError());
        return 1;
    }
    SDL_GL_SetSwapInterval(0);  /* the client caps with Sleep, not vsync */
    int dw, dh;
    SDL_GL_GetDrawableSize(window, &dw, &dh);
    double scale = (double)dw / (double)width;
    hero_model hero;
    memset(&hero, 0, sizeof hero);
    if (model_path && load_model(&hero, model_path))
        return 1;
    mu_gl_backend gl;
    memset(&gl, 0, sizeof gl);
    if (hero.loaded)
        mu_gl_upload(&gl, hero.textures.slots, hero.textures.count, 0);
    static mu_frame_world world;
    mu_frame_world_init(&world, (uint32_t)dw, (uint32_t)dh, 128, 128);
    world.clock.frame_tick = SDL_GetTicks();
    uint32_t start = SDL_GetTicks(), frames = 0;
    int running = 1, escapes = 0;
    int32_t printed = 0;
    while (running) {
        SDL_Event e;
        while (SDL_PollEvent(&e)) {
            if (e.type == SDL_QUIT) {
                running = 0;
            } else if (e.type == SDL_MOUSEMOTION) {
                mu_frame_world_message(&world, 0x200, 0, pack((int)(e.motion.x * scale), (int)(e.motion.y * scale)));
            } else if (e.type == SDL_MOUSEBUTTONDOWN || e.type == SDL_MOUSEBUTTONUP) {
                int down = e.type == SDL_MOUSEBUTTONDOWN;
                uint32_t message = e.button.button == SDL_BUTTON_LEFT ? (down ? 0x201 : 0x202)
                                 : e.button.button == SDL_BUTTON_RIGHT ? (down ? 0x204 : 0x205)
                                 : (down ? 0x207 : 0x208);
                mu_frame_world_message(&world, message, 0, pack((int)(e.button.x * scale), (int)(e.button.y * scale)));
            } else if (e.type == SDL_MOUSEWHEEL) {
                int delta = e.wheel.y * 120;
                mu_frame_world_message(&world, 0x20a, (uint32_t)(uint16_t)delta << 16, 0);
            } else if (e.type == SDL_KEYDOWN || e.type == SDL_KEYUP) {
                int vk = mu_vk_from_hid((int)e.key.keysym.scancode);
                int down = e.type == SDL_KEYDOWN;
                mu_frame_world_key(&world, vk, down);
                mu_frame_world_message(&world, down ? 0x100 : 0x101, (uint32_t)vk, 0);
                if (down && !e.key.repeat && vk == 0x1b && ++escapes >= 2)
                    running = 0;
                else if (down && vk != 0x1b)
                    escapes = 0;
            }
        }
        int32_t steps = mu_frame_world_update(&world, SDL_GetTicks());
        animate_model(&hero, &world, steps);
        mu_frame_world_begin_render(&world, SDL_GetTicks());
        draw(&world, &hero, &gl);
        SDL_GL_SwapWindow(window);
        ++frames;
        int32_t sleep = mu_frame_world_end_render(&world);
        if (sleep > 0)
            SDL_Delay((uint32_t)sleep);
        for (; printed < world.log_count; ++printed)
            printf("%s\n", world.log[printed]);
        if (world.log_count == MU_FRAME_LOG) {
            world.log_count = 0;
            printed = 0;
        }
        if (seconds > 0 && (SDL_GetTicks() - start) / 1000.0 >= seconds)
            running = 0;
    }
    double elapsed = (SDL_GetTicks() - start) / 1000.0;
    printf("{\"frames\": %u, \"seconds\": %.2f, \"fps\": %.2f, \"logic_steps\": %u}\n", frames, elapsed,
           elapsed > 0 ? frames / elapsed : 0.0, world.clock.logic_steps);
    mu_gl_release(&gl);
    SDL_GL_DeleteContext(context);
    SDL_DestroyWindow(window);
    SDL_Quit();
    return 0;
}

int main(int argc, char **argv)
{
    const char *model = NULL, *out_dir = NULL;
    int32_t width = 1024, height = 768, frames = 60;
    double seconds = 0;
    int headless_mode = 0, check = 0;
    for (int i = 1; i < argc; ++i) {
        const char *a = argv[i];
        if (!strcmp(a, "--width") && i + 1 < argc) width = atoi(argv[++i]);
        else if (!strcmp(a, "--height") && i + 1 < argc) height = atoi(argv[++i]);
        else if (!strcmp(a, "--seconds") && i + 1 < argc) seconds = atof(argv[++i]);
        else if (!strcmp(a, "--frames") && i + 1 < argc) frames = atoi(argv[++i]);
        else if (!strcmp(a, "--out-dir") && i + 1 < argc) out_dir = argv[++i];
        else if (!strcmp(a, "--headless")) headless_mode = 1;
        else if (!strcmp(a, "--gl-check")) check = 1;
        else if (a[0] != '-' && !model) model = a;
        else {
            fprintf(stderr, "usage: mu-frame-window [MODEL.bmd] [--width W] [--height H] [--seconds S]\n"
                            "       mu-frame-window [MODEL.bmd] --headless --frames N --out-dir DIR\n"
                            "       mu-frame-window --gl-check\n");
            return 2;
        }
    }
    if (width < 64 || height < 64 || width > 8192 || height > 8192)
        return 2;
    if (check)
        return gl_check();
    if (headless_mode)
        return headless(model, width, height, frames, out_dir);
    return windowed(model, width, height, seconds);
}
