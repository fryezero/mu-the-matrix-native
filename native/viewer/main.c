/* mu-viewer: native macOS (and Linux) model viewer.
 *
 * Loads a client BMD model and its textures, animates it with the
 * reconstructed animation tick and pose builder, skins it with the
 * reconstructed CPU transform, and draws it through the ported mesh-draw loop
 * into OpenGL 2.1 immediate mode. Game logic advances in fixed 40 ms steps
 * like the client's frame driver (0x01851d39); rendering follows the display.
 *
 * Controls: left drag orbit, right drag (or shift+left) pan, wheel zoom,
 * Space play/pause, Left/Right previous/next action, Up/Down speed,
 * ',' '.' step frame (paused), M draw mode (2, 4, 0x1000, 1), L lighting,
 * T alpha test, C cull (state/off/on), F front face, G wireframe, S stop flag,
 * N/P next/previous model in the directory, R reset camera, O screenshot,
 * Esc/Q quit.
 *
 * Headless: --headless [--backend gl|soft] --out PNG [--compare].
 */
#define _POSIX_C_SOURCE 200809L /* lstat, opendir, strdup with -std=c11 on glibc */
#include <dirent.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <SDL.h>
#ifdef __APPLE__
#include <OpenGL/gl.h>
#else
#include <GL/gl.h>
#endif

#include "../core/mu_bmd.h"
#include "../core/mu_camera.h"
#include "../core/mu_model.h"
#include "../core/mu_options.h"
#include "../core/mu_png.h"
#include "../core/mu_raster.h"
#include "../core/mu_scene.h"
#include "../core/mu_textures.h"
#include "../../reconstructed/record-math/record_math.h"
#include "gl_backend.h"
#include "gl_headless.h"

typedef struct viewer {
    mu_options options;
    char path[4096];
    mu_bmd bmd;
    mu_model model;
    mu_textures textures;
    int loaded;
    mu_camera camera, home;
    int playing;
    float speed;
} viewer;

static int load_model(viewer *v, const char *path)
{
    char error[512];
    mu_bmd bmd;
    if (mu_bmd_load_file(path, &bmd, error, sizeof error) != MU_BMD_OK) {
        fprintf(stderr, "%s: %s\n", path, error);
        return 1;
    }
    mu_model model;
    if (mu_model_init(&model, &bmd, &v->options.params, error, sizeof error) != MU_MODEL_OK) {
        fprintf(stderr, "%s: %s\n", path, error);
        mu_bmd_free(&bmd);
        return 1;
    }
    if (v->loaded) {
        mu_model_free(&v->model);
        mu_bmd_free(&v->bmd);
        mu_textures_free(&v->textures);
    }
    v->bmd = bmd;
    v->model = model;
    mu_model_relocate(&v->model, &v->bmd);   /* both structs moved */
    snprintf(v->path, sizeof v->path, "%s", path);
    v->options.model_path = v->path;
    memset(&v->textures, 0, sizeof v->textures);
    if (!v->options.no_textures) {
        char directory[4096];
        if (v->options.texture_dir)
            snprintf(directory, sizeof directory, "%s", v->options.texture_dir);
        else
            mu_path_directory(path, directory, sizeof directory);
        mu_textures_load(&v->textures, &v->bmd, directory);
    }
    v->loaded = 1;
    mu_options_animate(&v->options, &v->model, NULL);
    mu_options_camera(&v->options, &v->model, &v->camera);
    v->home = v->camera;
    return 0;
}

static void draw(viewer *v, mu_render_backend *backend, mu_draw_stats *stats)
{
    mu_scene_draw_model(&v->model, &v->options.draw, backend, stats);
}

/* ---- headless ---- */
static int render_soft(viewer *v, uint8_t *pixels)
{
    mu_raster raster;
    if (mu_raster_init(&raster, v->options.width, v->options.height))
        return 1;
    raster.linear = !v->options.nearest;
    raster.front_ccw = !v->options.front_cw;
    raster.textures = v->textures.slots;
    raster.texture_count = v->textures.count;
    mu_camera_view(&v->camera, raster.view);
    mu_camera_projection(&v->camera, (float)v->options.width / (float)v->options.height, raster.projection);
    mu_raster_clear(&raster, v->options.background);
    mu_render_backend backend;
    mu_raster_backend(&raster, &backend);
    mu_draw_stats stats = {0, 0, 0};
    draw(v, &backend, &stats);
    memcpy(pixels, raster.color, (size_t)v->options.width * (size_t)v->options.height * 4);
    mu_raster_free(&raster);
    return 0;
}

static int render_gl(viewer *v, uint8_t *pixels)
{
    char error[256];
    const int32_t w = v->options.width, h = v->options.height;
    if (mu_gl_headless_begin(w, h, error, sizeof error)) {
        fprintf(stderr, "headless GL: %s\n", error);
        return 1;
    }
    mu_gl_backend gl;
    memset(&gl, 0, sizeof gl);
    gl.front_cw = v->options.front_cw;
    mu_gl_upload(&gl, v->textures.slots, v->textures.count, v->options.nearest);
    float view[16], projection[16];
    mu_camera_view(&v->camera, view);
    mu_camera_projection(&v->camera, (float)w / (float)h, projection);
    mu_gl_frame(w, h, v->options.background, view, projection);
    mu_render_backend backend;
    mu_gl_backend_bind(&gl, &backend);
    mu_draw_stats stats = {0, 0, 0};
    draw(v, &backend, &stats);
    glFinish();
    mu_gl_read(w, h, pixels);
    fprintf(stderr, "GL renderer: %s\n", mu_gl_renderer());
    mu_gl_release(&gl);
    mu_gl_headless_end();
    return 0;
}

static int headless(viewer *v)
{
    const size_t size = (size_t)v->options.width * (size_t)v->options.height * 4;
    uint8_t *pixels = malloc(size), *other = malloc(size);
    if (!pixels || !other)
        return 1;
    int gl = !strcmp(v->options.backend, "gl");
    if (gl ? render_gl(v, pixels) : render_soft(v, pixels))
        return 1;
    char hash[65];
    mu_sha256_hex(pixels, size, hash);
    if (v->options.output && mu_png_write(v->options.output, pixels, v->options.width, v->options.height)) {
        fprintf(stderr, "cannot write %s\n", v->options.output);
        return 1;
    }
    printf("{\"backend\": \"%s\", \"sha256\": \"%s\", \"width\": %d, \"height\": %d", gl ? "gl" : "soft", hash,
           v->options.width, v->options.height);
    if (v->options.compare) {
        if (gl ? render_soft(v, other) : render_gl(v, other))
            return 1;
        size_t pixels_total = size / 4, differ = 0, over8 = 0;
        unsigned max = 0;
        double sum = 0;
        for (size_t i = 0; i < pixels_total; ++i) {
            unsigned worst = 0;
            for (int k = 0; k < 3; ++k) {
                int d = (int)pixels[4 * i + (size_t)k] - (int)other[4 * i + (size_t)k];
                unsigned a = (unsigned)(d < 0 ? -d : d);
                if (a > worst)
                    worst = a;
                sum += a;
            }
            differ += worst != 0;
            over8 += worst > 8;
            if (worst > max)
                max = worst;
        }
        char other_hash[65];
        mu_sha256_hex(other, size, other_hash);
        printf(", \"other_sha256\": \"%s\", \"differing_pixels\": %zu, \"pixels_over_8\": %zu, \"max_channel_diff\": %u,"
               " \"mean_channel_diff\": %.4f", other_hash, differ, over8, max, sum / (double)(pixels_total * 3));
    }
    printf("}\n");
    free(pixels);
    free(other);
    return 0;
}

/* ---- windowed ---- */
static void step_model(viewer *v, int direction)
{
    char directory[4096];
    mu_path_directory(v->path, directory, sizeof directory);
    DIR *dir = opendir(directory);
    if (!dir)
        return;
    char **names = NULL;
    size_t count = 0;
    struct dirent *entry;
    while ((entry = readdir(dir)) != NULL) {
        size_t n = strlen(entry->d_name);
        if (n > 4 && (!strcmp(entry->d_name + n - 4, ".bmd") || !strcmp(entry->d_name + n - 4, ".BMD"))) {
            char **grown = realloc(names, sizeof *names * (count + 1));
            if (!grown)
                break;
            names = grown;
            names[count++] = strdup(entry->d_name);
        }
    }
    closedir(dir);
    for (size_t i = 0; i + 1 < count; ++i)
        for (size_t j = i + 1; j < count; ++j)
            if (strcmp(names[j], names[i]) < 0) {
                char *t = names[i];
                names[i] = names[j];
                names[j] = t;
            }
    const char *current = strrchr(v->path, '/');
    current = current ? current + 1 : v->path;
    size_t at = 0;
    for (size_t i = 0; i < count; ++i)
        if (!strcmp(names[i], current))
            at = i;
    for (size_t tries = 0; tries < count; ++tries) {
        at = (at + count + (size_t)(direction > 0 ? 1 : count - 1)) % count;
        char path[4096];
        snprintf(path, sizeof path, "%s/%s", directory, names[at]);
        v->options.action = 0;
        v->options.frame = 0;
        v->options.prior_action = 0;
        v->options.prior_frame = 0;
        if (load_model(v, path) == 0)
            break;
    }
    for (size_t i = 0; i < count; ++i)
        free(names[i]);
    free(names);
}

static void set_action(viewer *v, int delta)
{
    int32_t n = v->bmd.action_count;
    if (n <= 0)
        return;
    uint16_t old = mu_model_action(&v->model);
    float frame = mu_model_frame(&v->model);
    int32_t next = ((int32_t)old + delta + n) % n;
    /* Viewer action change: blend from the current pose (the client's own
     * action-change code, object +0x2a/+0x2c/+0xd4, has not been traced). */
    mu_model_set_state(&v->model, (uint16_t)next, 0.0f, (float)(int)frame, old);
    mu_model_update(&v->model);
}

static void title(viewer *v, SDL_Window *window)
{
    static const char *mode_names[] = {"2", "4", "0x1000", "1"};
    int mode_index = v->options.draw.mode == 4 ? 1 : v->options.draw.mode == 0x1000 ? 2 : v->options.draw.mode == 1 ? 3 : 0;
    const char *name = strrchr(v->path, '/');
    char text[512];
    uint16_t action = mu_model_action(&v->model);
    snprintf(text, sizeof text, "%s  v%d  action %u/%d (%d keys)  frame %.2f  speed %.3f%s  mode %s%s%s",
             name ? name + 1 : v->path, v->bmd.version, action, v->bmd.action_count,
             v->bmd.action_count ? v->bmd.actions[action < v->bmd.action_count ? action : 0].keys : 0,
             (double)mu_model_frame(&v->model), (double)v->speed, v->playing ? "" : " (paused)", mode_names[mode_index],
             v->options.params.lighting ? "" : "  unlit", v->textures.missing ? "  [missing textures]" : "");
    SDL_SetWindowTitle(window, text);
}

static void screenshot(viewer *v, int32_t w, int32_t h)
{
    uint8_t *pixels = malloc((size_t)w * (size_t)h * 4);
    if (!pixels)
        return;
    mu_gl_read(w, h, pixels);
    const char *path = v->options.output ? v->options.output : "mu-viewer-shot.png";
    if (mu_png_write(path, pixels, w, h) == 0)
        fprintf(stderr, "saved %s\n", path);
    free(pixels);
}

static int windowed(viewer *v)
{
    if (SDL_Init(SDL_INIT_VIDEO) != 0) {
        fprintf(stderr, "SDL_Init: %s\n", SDL_GetError());
        return 1;
    }
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 2);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 1);
    SDL_GL_SetAttribute(SDL_GL_DEPTH_SIZE, 24);
    SDL_GL_SetAttribute(SDL_GL_DOUBLEBUFFER, 1);
    SDL_Window *window = SDL_CreateWindow("mu-viewer", SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED,
                                          v->options.width, v->options.height,
                                          SDL_WINDOW_OPENGL | SDL_WINDOW_RESIZABLE | SDL_WINDOW_ALLOW_HIGHDPI);
    if (!window) {
        fprintf(stderr, "SDL_CreateWindow: %s\n", SDL_GetError());
        return 1;
    }
    SDL_GLContext context = SDL_GL_CreateContext(window);
    if (!context) {
        fprintf(stderr, "SDL_GL_CreateContext: %s\n", SDL_GetError());
        return 1;
    }
    SDL_GL_SetSwapInterval(1);
    fprintf(stderr, "GL renderer: %s, version %s\n", glGetString(GL_RENDERER), glGetString(GL_VERSION));
    mu_gl_backend gl;
    memset(&gl, 0, sizeof gl);
    gl.front_cw = v->options.front_cw;
    mu_gl_upload(&gl, v->textures.slots, v->textures.count, v->options.nearest);
    mu_render_backend backend;
    mu_gl_backend_bind(&gl, &backend);

    uint64_t frequency = SDL_GetPerformanceFrequency(), last = SDL_GetPerformanceCounter(), start = last;
    double accumulator = 0;
    int running = 1, dragging = 0, panning = 0;
    uint64_t frames = 0;
    while (running) {
        SDL_Event event;
        while (SDL_PollEvent(&event)) {
            if (event.type == SDL_QUIT)
                running = 0;
            else if (event.type == SDL_MOUSEBUTTONDOWN) {
                int shift = (SDL_GetModState() & KMOD_SHIFT) != 0;
                if (event.button.button == SDL_BUTTON_LEFT && !shift)
                    dragging = 1;
                else
                    panning = 1;
            } else if (event.type == SDL_MOUSEBUTTONUP) {
                dragging = panning = 0;
            } else if (event.type == SDL_MOUSEMOTION) {
                if (dragging) {
                    v->camera.yaw -= (float)event.motion.xrel * 0.4f;
                    v->camera.pitch += (float)event.motion.yrel * 0.4f;
                    if (v->camera.pitch > 89.0f) v->camera.pitch = 89.0f;
                    if (v->camera.pitch < -89.0f) v->camera.pitch = -89.0f;
                } else if (panning) {
                    float view[16];
                    mu_camera_view(&v->camera, view);
                    float scale = v->camera.distance * 0.0015f;
                    for (int k = 0; k < 3; ++k)
                        v->camera.target[k] += (-(float)event.motion.xrel * view[4 * k] +
                                                (float)event.motion.yrel * view[4 * k + 1]) * scale;
                }
            } else if (event.type == SDL_MOUSEWHEEL) {
                float factor = event.wheel.y > 0 ? 0.9f : 1.1f;
                v->camera.distance *= factor;
                v->camera.near_plane *= factor;
                v->camera.far_plane *= factor;
            } else if (event.type == SDL_KEYDOWN) {
                switch (event.key.keysym.sym) {
                case SDLK_ESCAPE: case SDLK_q: running = 0; break;
                case SDLK_SPACE: v->playing = !v->playing; break;
                case SDLK_RIGHT: set_action(v, 1); break;
                case SDLK_LEFT: set_action(v, -1); break;
                case SDLK_UP: v->speed *= 1.25f; break;
                case SDLK_DOWN: v->speed /= 1.25f; break;
                case SDLK_PERIOD: case SDLK_COMMA: {
                    uint16_t action = mu_model_action(&v->model);
                    float frame = (float)(int)mu_model_frame(&v->model) + (event.key.keysym.sym == SDLK_PERIOD ? 1.0f : -1.0f);
                    int32_t keys = v->bmd.action_count ? v->bmd.actions[action < v->bmd.action_count ? action : 0].keys : 0;
                    if (keys > 0)
                        frame = (float)(((int)frame % keys + keys) % keys);
                    mu_model_set_state(&v->model, action, frame, frame, action);
                    mu_model_update(&v->model);
                    break;
                }
                case SDLK_m: {
                    int32_t m = v->options.draw.mode;
                    v->options.draw.mode = m == 2 ? 4 : m == 4 ? 0x1000 : m == 0x1000 ? 1 : 2;
                    break;
                }
                case SDLK_l:
                    v->options.params.lighting = !v->options.params.lighting;
                    v->model.params.lighting = v->options.params.lighting;
                    mu_model_apply_params(&v->model, &v->model.params);
                    mu_model_update(&v->model);
                    break;
                case SDLK_t: v->options.draw.alpha_test = !v->options.draw.alpha_test; break;
                case SDLK_c: v->options.draw.cull = (int8_t)(v->options.draw.cull == -1 ? 0 : v->options.draw.cull == 0 ? 1 : -1); break;
                case SDLK_f: gl.front_cw = !gl.front_cw; break;
                case SDLK_g: gl.wireframe = !gl.wireframe; break;
                case SDLK_s: {
                    uint16_t action = mu_model_action(&v->model);
                    mu_model_set_action_stop(&v->model, action, (uint8_t)!mu_model_action_stop(&v->model, action));
                    break;
                }
                case SDLK_r: v->camera = v->home; break;
                case SDLK_n: case SDLK_p:
                    mu_gl_release(&gl);
                    step_model(v, event.key.keysym.sym == SDLK_n ? 1 : -1);
                    mu_gl_upload(&gl, v->textures.slots, v->textures.count, v->options.nearest);
                    break;
                case SDLK_o: {
                    int w, h;
                    SDL_GL_GetDrawableSize(window, &w, &h);
                    screenshot(v, w, h);
                    break;
                }
                default: break;
                }
            }
        }
        uint64_t now = SDL_GetPerformanceCounter();
        accumulator += (double)(now - last) / (double)frequency;
        last = now;
        if (accumulator > 0.4)
            accumulator = 0.4;
        int stepped = 0;
        while (accumulator >= 0.040) {   /* fixed 40 ms logic step */
            accumulator -= 0.040;
            if (v->playing) {
                uint8_t loop;
                mu_model_tick(&v->model, v->speed, &loop);
                stepped = 1;
            }
        }
        if (stepped)
            mu_model_update(&v->model);
        int w, h;
        SDL_GL_GetDrawableSize(window, &w, &h);
        float view[16], projection[16];
        mu_camera_view(&v->camera, view);
        mu_camera_projection(&v->camera, (float)w / (float)(h ? h : 1), projection);
        mu_gl_frame(w, h, v->options.background, view, projection);
        mu_draw_stats stats = {0, 0, 0};
        draw(v, &backend, &stats);
        SDL_GL_SwapWindow(window);
        frames++;
        if ((frames & 31) == 0)
            title(v, window);
        if (v->options.seconds > 0 && (double)(now - start) / (double)frequency >= (double)v->options.seconds) {
            if (v->options.output)
                screenshot(v, w, h);
            running = 0;
        }
    }
    fprintf(stderr, "frames=%llu seconds=%.2f\n", (unsigned long long)frames,
            (double)(SDL_GetPerformanceCounter() - start) / (double)frequency);
    mu_gl_release(&gl);
    SDL_GL_DeleteContext(context);
    SDL_DestroyWindow(window);
    SDL_Quit();
    return 0;
}

int main(int argc, char **argv)
{
    if (mu_record_math_environment_supported() != 1) {
        fprintf(stderr, "host floating-point environment unsupported by record-math\n");
        return 2;
    }
    static viewer v;
    mu_options_defaults(&v.options);
    v.options.width = 1024;
    v.options.height = 768;
    if (mu_options_parse(&v.options, argc, argv, 1) || !v.options.model_path) {
        mu_options_usage(argv[0]);
        return 2;
    }
    if (load_model(&v, v.options.model_path))
        return 1;
    v.playing = 1;
    v.speed = v.options.speed;
    int status = v.options.headless ? headless(&v) : windowed(&v);
    mu_model_free(&v.model);
    mu_bmd_free(&v.bmd);
    mu_textures_free(&v.textures);
    return status;
}
