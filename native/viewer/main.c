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
 * ',' '.' step frame (paused), M render flags (2, 0x42, 4, 0x1000, 0x4000, 1;
 * the mesh draw derives its mode from them), L lighting,
 * T alpha test, C cull (state/off/on), F front face, G wireframe, S stop flag,
 * N/P next/previous model in the directory, R reset camera, O screenshot,
 * Esc/Q quit.
 *
 * Headless: --headless [--backend gl|soft] --out PNG [--compare].
 * Windowed, the client time global (--client-time, milliseconds) advances with the
 * wall clock so the environment flags animate; headless keeps --client-time fixed.
 *
 * Character mode (any character option, e.g. --game-root DIR --class 1): the
 * positional model is Player.bmd (default DIR/Data/Player/Player.bmd); class
 * body parts, --part/--weapon/--wing items are assembled by mu_character
 * (reconstructed rotation position, keep-root pose builder and transform) and
 * drawn in the client's order. Left/Right change the Player action.
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
#include "../core/mu_character.h"
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
    int character;                /* character mode: the models below come from ch */
    mu_character ch;
} viewer;

/* Drawing targets: one model in model mode; the assembled items in character
 * mode, in the client order (body parts 5..0, weapons 0 and 1, wing). */
enum { MAX_TARGETS = MU_CHARACTER_ITEMS };
static int targets(viewer *v, const mu_model **models, const mu_textures **textures)
{
    if (!v->character) {
        models[0] = &v->model;
        textures[0] = &v->textures;
        return 1;
    }
    static const int order[MU_CHARACTER_ITEMS] = {5, 4, 3, 2, 1, 0, 6, 7, 8};
    int n = 0;
    for (int i = 0; i < MU_CHARACTER_ITEMS; ++i) {
        const mu_character_item *item = &v->ch.items[order[i]];
        if (!item->loaded)
            continue;
        models[n] = &item->model;
        textures[n++] = &item->textures;
    }
    return n;
}

static mu_model *animated(viewer *v) { return v->character ? &v->ch.player : &v->model; }
static const mu_bmd *animated_bmd(viewer *v) { return v->character ? &v->ch.player_bmd : &v->bmd; }
static void update(viewer *v)
{
    if (v->character)
        mu_character_update(&v->ch);
    else
        mu_model_update(&v->model);
}

static int load_character(viewer *v)
{
    char error[1024];
    if (mu_options_character(&v->options, &v->ch, error, sizeof error)) {
        fprintf(stderr, "%s\n", error);
        mu_character_free(&v->ch);
        return 1;
    }
    v->character = 1;
    snprintf(v->path, sizeof v->path, "%s", v->options.model_path ? v->options.model_path : "Player.bmd");
    mu_options_character_camera(&v->options, &v->ch, &v->camera);
    v->home = v->camera;
    return 0;
}

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

/* Draw options for one target: its bitmap records (GL names, component
 * counts) come from its textures. */
static mu_draw_options target_options(const viewer *v, const mu_textures *textures)
{
    mu_draw_options o = v->options.draw;
    o.textures = v->options.no_textures ? NULL : textures;
    return o;
}

/* Software path: one raster, textures switched per target. */
static void draw_soft(viewer *v, mu_raster *raster, mu_render_backend *backend, mu_draw_stats *stats)
{
    const mu_model *models[MAX_TARGETS];
    const mu_textures *textures[MAX_TARGETS];
    int n = targets(v, models, textures);
    for (int i = 0; i < n; ++i) {
        raster->textures = textures[i]->slots;
        raster->texture_count = textures[i]->count;
        raster->texture_filter = textures[i]->filter;
        raster->texture_wrap = textures[i]->wrap;
        const mu_draw_options o = target_options(v, textures[i]);
        mu_scene_draw_model(models[i], &o, backend, stats);
    }
}

/* GL path: one texture set (mu_gl_backend) per target. */
typedef struct gl_targets {
    mu_gl_backend gl[MAX_TARGETS];
    mu_render_backend backend[MAX_TARGETS];
    int count;
} gl_targets;

static void gl_targets_upload(viewer *v, gl_targets *t, int front_cw, int wireframe)
{
    const mu_model *models[MAX_TARGETS];
    const mu_textures *textures[MAX_TARGETS];
    t->count = targets(v, models, textures);
    for (int i = 0; i < t->count; ++i) {
        memset(&t->gl[i], 0, sizeof t->gl[i]);
        t->gl[i].front_cw = front_cw;
        t->gl[i].wireframe = wireframe;
        mu_gl_upload(&t->gl[i], textures[i], v->options.linear);
        mu_gl_backend_bind(&t->gl[i], &t->backend[i]);
    }
}

static void gl_targets_release(gl_targets *t)
{
    for (int i = 0; i < t->count; ++i)
        mu_gl_release(&t->gl[i]);
    t->count = 0;
}

static void gl_targets_set(gl_targets *t, int front_cw, int wireframe)
{
    for (int i = 0; i < t->count; ++i) {
        t->gl[i].front_cw = front_cw;
        t->gl[i].wireframe = wireframe;
    }
}

static void draw_gl(viewer *v, gl_targets *t, mu_draw_stats *stats)
{
    const mu_model *models[MAX_TARGETS];
    const mu_textures *textures[MAX_TARGETS];
    int n = targets(v, models, textures);
    for (int i = 0; i < n && i < t->count; ++i) {
        const mu_draw_options o = target_options(v, textures[i]);
        mu_scene_draw_model(models[i], &o, &t->backend[i], stats);
    }
}

/* ---- headless ---- */
static int render_soft(viewer *v, uint8_t *pixels)
{
    mu_raster raster;
    if (mu_raster_init(&raster, v->options.width, v->options.height))
        return 1;
    raster.linear = v->options.linear;
    raster.front_ccw = !v->options.front_cw;
    mu_camera_view(&v->camera, raster.view);
    mu_camera_projection(&v->camera, (float)v->options.width / (float)v->options.height, raster.projection);
    mu_raster_clear(&raster, v->options.background);
    mu_render_backend backend;
    mu_raster_backend(&raster, &backend);
    mu_draw_stats stats = {0, 0, 0, 0};
    draw_soft(v, &raster, &backend, &stats);
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
    static gl_targets t;
    gl_targets_upload(v, &t, v->options.front_cw, 0);
    float view[16], projection[16];
    mu_camera_view(&v->camera, view);
    mu_camera_projection(&v->camera, (float)w / (float)h, projection);
    mu_gl_frame(w, h, v->options.background, view, projection);
    mu_draw_stats stats = {0, 0, 0, 0};
    draw_gl(v, &t, &stats);
    glFinish();
    mu_gl_read(w, h, pixels);
    fprintf(stderr, "GL renderer: %s\n", mu_gl_renderer());
    gl_targets_release(&t);
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
    mu_model *model = animated(v);
    int32_t n = animated_bmd(v)->action_count;
    if (n <= 0)
        return;
    uint16_t old = mu_model_action(model);
    float frame = mu_model_frame(model);
    int32_t next = ((int32_t)old + delta + n) % n;
    /* Viewer action change: blend from the current pose (the client's own
     * action-change code, object +0x2a/+0x2c/+0xd4, has not been traced). */
    mu_model_set_state(model, (uint16_t)next, 0.0f, (float)(int)frame, old);
    update(v);
}

static void title(viewer *v, SDL_Window *window)
{
    const char *name = strrchr(v->path, '/');
    char text[512];
    const mu_bmd *bmd = animated_bmd(v);
    mu_model *model = animated(v);
    uint16_t action = mu_model_action(model);
    int missing = v->textures.missing;
    if (v->character)
        for (int i = 0; i < MU_CHARACTER_ITEMS; ++i)
            missing += v->ch.items[i].loaded ? v->ch.items[i].textures.missing : 0;
    snprintf(text, sizeof text, "%s%s  v%d  action %u/%d (%d keys)  frame %.2f  speed %.3f%s  flags 0x%x%s%s",
             v->character ? "character " : "", name ? name + 1 : v->path, bmd->version, action, bmd->action_count,
             bmd->action_count ? bmd->actions[action < bmd->action_count ? action : 0].keys : 0,
             (double)mu_model_frame(model), (double)v->speed, v->playing ? "" : " (paused)", v->options.draw.flags,
             v->options.params.lighting ? "" : "  unlit", missing ? "  [missing textures]" : "");
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
    static gl_targets t;
    int front_cw = v->options.front_cw, wireframe = 0;
    gl_targets_upload(v, &t, front_cw, wireframe);

    const float time0 = v->options.draw.time;
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
                    mu_model *model = animated(v);
                    const mu_bmd *bmd = animated_bmd(v);
                    uint16_t action = mu_model_action(model);
                    float frame = (float)(int)mu_model_frame(model) + (event.key.keysym.sym == SDLK_PERIOD ? 1.0f : -1.0f);
                    int32_t keys = bmd->action_count ? bmd->actions[action < bmd->action_count ? action : 0].keys : 0;
                    if (keys > 0)
                        frame = (float)(((int)frame % keys + keys) % keys);
                    mu_model_set_state(model, action, frame, frame, action);
                    update(v);
                    break;
                }
                case SDLK_m: {
                    static const uint32_t cycle[] = {2, 0x42, 4, 0x1000, 0x4000, 1};
                    size_t k = 0;
                    while (k < sizeof cycle / sizeof cycle[0] && cycle[k] != v->options.draw.flags)
                        ++k;
                    v->options.draw.flags = cycle[(k + 1) % (sizeof cycle / sizeof cycle[0])];
                    break;
                }
                case SDLK_l:
                    v->options.params.lighting = !v->options.params.lighting;
                    if (v->character) {
                        v->ch.params.lighting = v->options.params.lighting;
                    } else {
                        v->model.params.lighting = v->options.params.lighting;
                        mu_model_apply_params(&v->model, &v->model.params);
                    }
                    update(v);
                    break;
                case SDLK_t: v->options.draw.alpha_test = !v->options.draw.alpha_test; break;
                case SDLK_c: v->options.draw.cull = (int8_t)(v->options.draw.cull == -1 ? 0 : v->options.draw.cull == 0 ? 1 : -1); break;
                case SDLK_f: front_cw = !front_cw; gl_targets_set(&t, front_cw, wireframe); break;
                case SDLK_g: wireframe = !wireframe; gl_targets_set(&t, front_cw, wireframe); break;
                case SDLK_s: {
                    mu_model *model = animated(v);
                    uint16_t action = mu_model_action(model);
                    mu_model_set_action_stop(model, action, (uint8_t)!mu_model_action_stop(model, action));
                    break;
                }
                case SDLK_r: v->camera = v->home; break;
                case SDLK_n: case SDLK_p:
                    if (v->character)
                        break;
                    gl_targets_release(&t);
                    step_model(v, event.key.keysym.sym == SDLK_n ? 1 : -1);
                    gl_targets_upload(v, &t, front_cw, wireframe);
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
                mu_model_tick(animated(v), v->speed, &loop);
                stepped = 1;
            }
        }
        if (stepped)
            update(v);
        int w, h;
        SDL_GL_GetDrawableSize(window, &w, &h);
        float view[16], projection[16];
        mu_camera_view(&v->camera, view);
        mu_camera_projection(&v->camera, (float)w / (float)(h ? h : 1), projection);
        mu_gl_frame(w, h, v->options.background, view, projection);
        v->options.draw.time = time0 + (float)((double)(now - start) * 1000.0 / (double)frequency);
        mu_draw_stats stats = {0, 0, 0, 0};
        draw_gl(v, &t, &stats);
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
    gl_targets_release(&t);
    SDL_GL_DeleteContext(context);
    SDL_DestroyWindow(window);
    SDL_Quit();
    return 0;
}

int mu_terrain_viewer_main(int argc, char **argv);  /* viewer/terrain_view.c */

int main(int argc, char **argv)
{
    if (argc > 1 && !strcmp(argv[1], "--terrain"))
        return mu_terrain_viewer_main(argc, argv);
    if (mu_record_math_environment_supported() != 1) {
        fprintf(stderr, "host floating-point environment unsupported by record-math\n");
        return 2;
    }
    static viewer v;
    mu_options_defaults(&v.options);
    v.options.width = 1024;
    v.options.height = 768;
    if (mu_options_parse(&v.options, argc, argv, 1) || (!v.options.model_path && !v.options.character)) {
        mu_options_usage(argv[0]);
        return 2;
    }
    if (v.options.character ? load_character(&v) : load_model(&v, v.options.model_path))
        return 1;
    v.playing = 1;
    v.speed = v.options.speed;
    int status = v.options.headless ? headless(&v) : windowed(&v);
    if (v.character) {
        mu_character_free(&v.ch);
    } else {
        mu_model_free(&v.model);
        mu_bmd_free(&v.bmd);
        mu_textures_free(&v.textures);
    }
    return status;
}
