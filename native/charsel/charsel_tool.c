#include "../data/manifest.h"
/* mu-charsel: the character-select scene natively (NATIVE-CHARSEL-001).
 *
 * One window (SDL2 + OpenGL 2.1) or a headless run (CGL/GLX offscreen, or the
 * deterministic software rasterizer) of a scene-5 session (core/mu_charsel):
 * World94's terrain under its camera record, up to five synthetic characters
 * assembled by the character module and placed by the client's slot code, the
 * selected character drawn with the client's selection highlight.
 *
 *   mu-charsel --game-root ROOT [--list FILE] [--slot N] [--marker X,Y[,Z]]
 *              [--width W --height H] [--seconds S]
 *   mu-charsel --game-root ROOT --headless --frames N --out-dir DIR [--backend soft|gl] [--every K]
 *              [--cycle F] [--enter F] [--quiet]
 *
 * --cycle F selects the next list entry every F frames (the GFx list in the
 * client); --enter F presses Enter on frame F (the scene tick then asks for
 * the loading scene, which is reported). In the window: 1..5 select a list
 * entry, Left/Right step through it, Enter is the client's Enter, Esc twice
 * quits, O saves a PNG.
 *
 * Built twice: build/mu-charsel-window (SDL2 + OpenGL) and, with
 * MU_CHARSEL_NO_GL, build/mu-charsel (software only, `make -C native`); the
 * second is also reached as `mu-render charsel`.
 */
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#ifndef MU_CHARSEL_NO_GL
#include <SDL.h>
#ifdef __APPLE__
#include <OpenGL/gl.h>
#else
#include <GL/gl.h>
#endif
#endif

#include "charsel_rt_internal.h"
#include "../core/mu_charsel_ui.h"
#include "../core/mu_objects.h"
#include "../core/mu_perf.h"
#include "../core/mu_png.h"
#include "../core/mu_raster.h"
#include "../core/mu_scene.h"
#include "../core/mu_terrain.h"
#ifndef MU_CHARSEL_NO_GL
#include "../viewer/gl_backend.h"
#include "../viewer/gl_batch.h"
#include "../viewer/gl_headless.h"
#endif

typedef struct app {
    mu_charsel_rt_options options;
    mu_charsel_rt *rt;
    const char *out_dir, *backend, *objects_out;
    int32_t frames, every, headless, quiet, cycle, enter_frame;
    float seconds;
} app;

/* ---- reports ---- */

static void report_frame(const app *a, int32_t frame, uint32_t now, const char *hash, const char *png)
{
    const mu_charsel_session *s = a->rt->s;
    const mu_client_view *v = &s->frame.view;
    float pos[3] = {0, 0, 0}, scale = 0;
    int32_t action = -1;
    float anim = 0;
    if (s->draw_entry >= 0) {
        const mu_character *ch = &s->characters[s->draw_entry];
        memcpy(pos, ch->params.position, sizeof pos);
        scale = ch->params.scale;
        action = mu_model_action(&ch->player);
        anim = mu_model_frame(&ch->player);
    }
    printf("{\"frame\": %d, \"tick\": %u, \"steps\": %u, \"selected\": %d, \"shown\": %d, \"drawn_entry\": %d,"
           " \"position\": [%.2f, %.2f, %.2f], \"scale\": %.3f, \"action\": %d, \"frame_anim\": %.3f,"
           " \"decals\": %d, \"particles\": %d, \"enter_requests\": %d, \"fov\": %.3f, \"angle\": [%.2f, %.2f, %.2f],"
           " \"eye\": [%.2f, %.2f, %.2f], \"far\": %.2f, \"objects_drawn\": %ld, \"after_meshes\": %ld,"
           " \"sprites\": %d, \"live_particles\": %u, \"billboards\": %ld, \"shadows\": %ld,"
           " \"effect_models\": %u, \"pick\": %d, \"sha256\": \"%s\", \"png\": \"%s\"}\n",
           frame, now, s->steps, s->selected, s->shown, s->draw_entry, (double)pos[0], (double)pos[1], (double)pos[2],
           (double)scale, action, (double)anim, s->decal_count, s->particles_created, s->enter_requests, (double)v->fov,
           (double)v->angle[0], (double)v->angle[1], (double)v->angle[2], (double)v->position[0],
           (double)v->position[1], (double)v->position[2], (double)v->view_far, s->objects_drawn, s->after_meshes,
           s->frame_sprites, s->particles.stats.live, s->billboards, s->shadows, s->particles.stats.drawn_effect_models,
           s->pick, hash ? hash : "", png ? png : "");
}

static void report_summary(const app *a, const char *renderer)
{
    const mu_charsel_session *s = a->rt->s;
    printf("{\"summary\": true, \"renderer\": \"%s\", \"world\": %d, \"folder\": %d, \"camera_key\": %d,"
           " \"camera_angle\": [%.3f, %.3f, %.3f], \"camera_position\": [%.3f, %.3f, %.3f], \"fov\": %.3f,"
           " \"characters\": %d, \"marker1\": [%.2f, %.2f, %.2f], \"steps\": %u, \"frames\": %u,"
           " \"enter_requests\": %d, \"objects\": %d, \"objects_drawn\": %ld, \"lifecycle\": %d,"
           " \"objects_created\": %d, \"object_steps\": %u, \"particles_created\": %llu, \"sprites_created\": %llu,"
           " \"effects_created\": %llu, \"effects_unsupported\": %llu, \"terrain_lights\": %ld, \"object_models\": %d,"
           " \"object_models_missing\": %d, \"draw_list\": %d, \"after_character\": %d}\n",
           renderer, MU_CHARSEL_WORLD, s->map->report.folder, s->info.key, (double)s->info.angle[0],
           (double)s->info.angle[1], (double)s->info.angle[2], (double)s->info.position[0],
           (double)s->info.position[1], (double)s->info.position[2], (double)s->info.fov, s->list.count,
           (double)s->scene.position[1][0], (double)s->scene.position[1][1], (double)s->scene.position[1][2], s->steps,
           s->frames, s->enter_requests, a->rt->has_objects ? a->rt->objects.count : 0, a->rt->objects_drawn, s->has_objects,
           s->has_objects ? s->objects->rt.created : 0, s->has_objects ? s->objects->rt.steps : 0u,
           (unsigned long long)s->particles.stats.created, (unsigned long long)s->particles.stats.sprites_created,
           (unsigned long long)s->particles.stats.effects_created,
           (unsigned long long)s->particles.stats.effects_unsupported,
           s->has_objects ? s->objects->rt.light_events : 0L, a->rt->has_objects ? a->rt->objects.models_loaded : 0,
           a->rt->has_objects ? a->rt->objects.models_missing : 0, s->has_objects ? s->objects->rt.draw_count : 0,
           s->has_objects ? s->objects->rt.after_count : 0);
    for (int32_t i = 0; i < s->list.count; ++i) {
        const mu_charsel_entry *e = &s->list.entries[i];
        const uint8_t *r = s->records + (size_t)e->slot * MU_CHARSEL_RECORD;
        float scale;
        memcpy(&scale, r + MU_CHARSEL_OBJECT + MU_OBJ_SCALE, sizeof scale);
        uint16_t parts[6];
        for (int k = 0; k < 6; ++k)
            memcpy(&parts[k], r + MU_CHAR_PARTS + MU_CHAR_PART_SIZE * k, 2);
        printf("{\"entry\": %d, \"slot\": %d, \"class\": %u, \"level\": %u, \"name\": \"%s\", \"scale\": %.3f,"
               " \"parts\": [%d, %d, %d, %d, %d, %d], \"stand_action\": %d}\n",
               i, e->slot, e->class_byte, e->level, e->name, (double)scale, (int16_t)parts[0], (int16_t)parts[1],
               (int16_t)parts[2], (int16_t)parts[3], (int16_t)parts[4], (int16_t)parts[5],
               s->character_loaded[i] ? mu_model_action(&s->characters[i].player) : -1);
    }
}

/* ---- headless ---- */

static void press_enter(app *a, int down)
{
    mu_charsel_key(a->rt->s, 0x0d, down);
}

static int headless(app *a)
{
#ifndef MU_CHARSEL_NO_GL
    char error[256];
    int gl = a->backend && !strcmp(a->backend, "gl");
#else
    const int gl = 0;
    if (a->backend && strcmp(a->backend, "soft")) {
        fprintf(stderr, "this build renders with the software rasterizer only (--backend soft)\n");
        return 2;
    }
#endif
    if (a->out_dir && mkdir(a->out_dir, 0755) && errno != EEXIST) {
        fprintf(stderr, "cannot create %s\n", a->out_dir);
        return 1;
    }
#ifndef MU_CHARSEL_NO_GL
    if (gl && mu_gl_headless_begin(a->options.width, a->options.height, error, sizeof error)) {
        fprintf(stderr, "headless GL: %s\n", error);
        return 1;
    }
    if (gl)
        mu_charsel_rt_gl_setup(a->rt);
#endif
    mu_raster raster;
    memset(&raster, 0, sizeof raster);
    if (!gl && mu_raster_init(&raster, a->options.width, a->options.height)) {
        fprintf(stderr, "raster allocation failed\n");
        return 1;
    }
    size_t bytes = (size_t)a->options.width * (size_t)a->options.height * 4;
    uint8_t *pixels = malloc(bytes);
    if (!pixels)
        return 1;
    uint32_t now = 100000;
    a->rt->s->frame.clock.frame_tick = now;
    for (int32_t frame = 0; frame < a->frames; ++frame) {
        if (a->cycle > 0 && frame > 0 && frame % a->cycle == 0)
            mu_charsel_rt_select_next(a->rt, 1);
        if (frame == a->enter_frame)
            press_enter(a, 1);
        else if (frame == a->enter_frame + 3)
            press_enter(a, 0);
        mu_charsel_update(a->rt->s, now);
        if (a->rt->ui)
            mu_charsel_ui_update(a->rt->ui, a->rt->s, -1000, -1000, 0, 0);
        mu_charsel_begin_render(a->rt->s, now);
        int save = a->out_dir && a->every > 0 && (frame % a->every == 0 || frame == a->frames - 1);
        char hash[65] = "", path[4096] = "";
        if (!save)
            mu_charsel_frame_objects(a->rt->s);   /* the frame's RenderObjects pass without output (NATIVE-CHARSEL-002) */
        if (save) {
            if (gl) {
#ifndef MU_CHARSEL_NO_GL
                mu_charsel_rt_draw_gl(a->rt, a->options.width, a->options.height);
                glFinish();
                mu_gl_read(a->options.width, a->options.height, pixels);
#endif
            } else {
                mu_charsel_rt_draw_soft(a->rt, &raster);
                memcpy(pixels, raster.color, bytes);
            }
            if (a->rt->ui)
                mu_charsel_ui_render(a->rt->ui, pixels);   /* the 2D layer over the 3D frame */
            mu_sha256_hex(pixels, bytes, hash);
            snprintf(path, sizeof path, "%s/frame-%04d.png", a->out_dir, frame);
            if (mu_png_write(path, pixels, a->options.width, a->options.height)) {
                fprintf(stderr, "cannot write %s\n", path);
                return 1;
            }
        }
        if (!a->quiet && (save || frame == a->frames - 1))
            report_frame(a, frame, now, save ? hash : NULL, save ? path : NULL);
        now += 12;
        int32_t sleep = mu_charsel_end_render(a->rt->s);
        if (sleep > 0)
            now += (uint32_t)sleep;
    }
    if (a->objects_out && a->rt->s->has_objects) {   /* the objects' state for the live comparison (NATIVE-CHARSEL-002) */
        FILE *f = fopen(a->objects_out, "w");
        for (int32_t i = 0; f && i < a->rt->s->objects->count; ++i) {
            const uint8_t *o = mu_objects_object_image(a->rt->s->objects, i);
            if (!o)
                continue;
            fprintf(f, "%d %d %.3f %.3f %.3f %u %u %.6f\n", i, mu_obj_i32(o, MU_OBJF_TYPE),
                    (double)mu_obj_f32(o, MU_OBJF_POSITION), (double)mu_obj_f32(o, MU_OBJF_POSITION + 4),
                    (double)mu_obj_f32(o, MU_OBJF_POSITION + 8), o[MU_OBJF_VISIBLE], o[MU_OBJF_AFTER_CHARACTER],
                    (double)mu_obj_f32(o, MU_OBJF_BLEND_V));
        }
        if (f)
            fclose(f);
    }
#ifndef MU_CHARSEL_NO_GL
    report_summary(a, gl ? mu_gl_renderer() : "software");
    if (gl) {
        mu_charsel_rt_gl_teardown(a->rt);
        mu_gl_headless_end();
    }
#else
    report_summary(a, "software");
#endif
    free(pixels);
    if (!gl)
        mu_raster_free(&raster);
    return 0;
}

#ifndef MU_CHARSEL_NO_GL
/* ---- window ---- */

static uint32_t pack(int x, int y)
{
    return ((uint32_t)(uint16_t)y << 16) | (uint16_t)x;
}

static int windowed(app *a)
{
    if (SDL_Init(SDL_INIT_VIDEO) != 0) {
        fprintf(stderr, "SDL_Init: %s\n", SDL_GetError());
        return 1;
    }
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 2);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 1);
    SDL_GL_SetAttribute(SDL_GL_DEPTH_SIZE, 24);
    SDL_GL_SetAttribute(SDL_GL_DOUBLEBUFFER, 1);
    SDL_Window *window = SDL_CreateWindow("mu-charsel", SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED, a->options.width,
                                          a->options.height, SDL_WINDOW_OPENGL | SDL_WINDOW_ALLOW_HIGHDPI);
    SDL_GLContext context = window ? SDL_GL_CreateContext(window) : NULL;
    if (!context) {
        fprintf(stderr, "SDL: %s\n", SDL_GetError());
        return 1;
    }
    SDL_GL_SetSwapInterval(0);
    int dw, dh;
    SDL_GL_GetDrawableSize(window, &dw, &dh);
    double scale = (double)dw / (double)a->options.width;
    mu_charsel_session *s = a->rt->s;
    s->frame.view.window_width = (uint32_t)dw;
    s->frame.view.window_height = (uint32_t)dh;
    s->frame.mouse.scale_x = (float)dw / 640.0f;
    s->frame.mouse.scale_y = (float)dh / 480.0f;
    mu_charsel_rt_gl_setup(a->rt);
    s->frame.clock.frame_tick = SDL_GetTicks();
    uint32_t start = SDL_GetTicks(), frames = 0;
    int running = 1, escapes = 0;
    while (running) {
        SDL_Event e;
        while (SDL_PollEvent(&e)) {
            if (e.type == SDL_QUIT) {
                running = 0;
            } else if (e.type == SDL_MOUSEMOTION) {
                mu_charsel_message(s, MU_WM_MOUSEMOVE, 0, pack((int)(e.motion.x * scale), (int)(e.motion.y * scale)));
            } else if (e.type == SDL_KEYDOWN || e.type == SDL_KEYUP) {
                int vk = mu_vk_from_hid((int)e.key.keysym.scancode);
                int down = e.type == SDL_KEYDOWN;
                mu_charsel_key(s, vk, down);
                mu_charsel_message(s, down ? 0x100u : 0x101u, (uint32_t)vk, 0);
                if (down && !e.key.repeat && vk == 0x1b && ++escapes >= 2)
                    running = 0;
                else if (down && vk != 0x1b)
                    escapes = 0;
                if (down && !e.key.repeat && vk >= 0x31 && vk < 0x31 + s->list.count)
                    mu_charsel_select(s, s->list.entries[vk - 0x31].slot);
                if (down && !e.key.repeat && (vk == 0x25 || vk == 0x27))
                    mu_charsel_rt_select_next(a->rt, vk == 0x27 ? 1 : -1);
                if (down && !e.key.repeat && vk == 0x4f) {
                    uint8_t *pixels = malloc((size_t)dw * (size_t)dh * 4);
                    if (pixels) {
                        mu_gl_read(dw, dh, pixels);
                        mu_png_write("mu-charsel-screenshot.png", pixels, dw, dh);
                        free(pixels);
                    }
                }
            }
        }
        uint32_t now = SDL_GetTicks();
        mu_charsel_update(s, now);
        mu_charsel_begin_render(s, now);
        mu_charsel_rt_draw_gl(a->rt, dw, dh);
        SDL_GL_SwapWindow(window);
        ++frames;
        int32_t sleep = mu_charsel_end_render(s);
        if (sleep > 0)
            mu_sleep_ms((uint32_t)sleep);   /* NATIVE-PERF-001: the host Sleep without oversleep */
        if (frames % 25 == 0) {
            int32_t i = mu_charsel_entry_of(s, s->selected);
            char title[200];
            snprintf(title, sizeof title, "mu-charsel  World94  %s (class 0x%02x, level %u)  Enter requests %d  %.1f fps",
                     i >= 0 ? s->list.entries[i].name : "-", i >= 0 ? s->list.entries[i].class_byte : 0,
                     i >= 0 ? s->list.entries[i].level : 0, s->enter_requests,
                     (double)frames * 1000.0 / (double)(SDL_GetTicks() - start + 1));
            SDL_SetWindowTitle(window, title);
        }
        if (a->seconds > 0 && (SDL_GetTicks() - start) / 1000.0 >= a->seconds)
            running = 0;
    }
    double elapsed = (SDL_GetTicks() - start) / 1000.0;
    printf("{\"frames\": %u, \"seconds\": %.2f, \"fps\": %.2f, \"logic_steps\": %u, \"enter_requests\": %d}\n", frames,
           elapsed, elapsed > 0 ? frames / elapsed : 0.0, s->steps, s->enter_requests);
    mu_charsel_rt_gl_teardown(a->rt);
    SDL_GL_DeleteContext(context);
    SDL_DestroyWindow(window);
    SDL_Quit();
    return 0;
}
#endif

static int usage(void)
{
    fprintf(stderr, "usage: mu-charsel --game-root ROOT [--list FILE] [--slot N] [--marker X,Y[,Z]]\n"
                    "                  [--width W --height H] [--seconds S]\n"
                    "                  [--headless --frames N --out-dir DIR --backend soft|gl --every K]\n"
                    "                  [--cycle F] [--enter F] [--no-ui] [--font FACE] [--tip TEXT] [--quiet]\n"
                    "                  [--objects-dir DIR]   local decoded EncTerrain94.plain: objects + markers\n"
                    "                  [--objects-out FILE]  per object: index type x y z visible(+0xb) after(+0xa) blend_v\n");
    return 2;
}

int mu_charsel_tool_main(int argc, char **argv);

int mu_charsel_tool_main(int argc, char **argv)
{
    if (!mu_native_data_check_args(argc, argv)) return 1;
    app a;
    memset(&a, 0, sizeof a);
    mu_charsel_rt_default_options(&a.options);
    a.frames = 50;
    a.every = 10;
    a.enter_frame = -10;
#ifdef MU_CHARSEL_NO_GL
    a.headless = 1;
    a.backend = "soft";
#else
    a.backend = "gl";
#endif
    for (int i = 1; i < argc; ++i) {
        const char *k = argv[i], *v = i + 1 < argc ? argv[i + 1] : NULL;
        if (!strcmp(k, "--headless")) { a.headless = 1; continue; }
        if (!strcmp(k, "--quiet")) { a.quiet = 1; continue; }
        if (!strcmp(k, "--no-ui")) { a.options.no_ui = 1; continue; }
        if (!v)
            return usage();
        ++i;
        if (!strcmp(k, "--game-root")) a.options.root = v;
        else if (!strcmp(k, "--list")) a.options.list_path = v;
        else if (!strcmp(k, "--objects-dir")) a.options.objects_dir = v;
        else if (!strcmp(k, "--objects-out")) a.objects_out = v;
        else if (!strcmp(k, "--slot")) a.options.slot = atoi(v);
        else if (!strcmp(k, "--marker")) {
            a.options.marker[2] = 169.5f;
            if (sscanf(v, "%f,%f,%f", &a.options.marker[0], &a.options.marker[1], &a.options.marker[2]) < 2)
                return usage();
            a.options.marker_given = 1;
        }
        else if (!strcmp(k, "--width")) a.options.width = atoi(v);
        else if (!strcmp(k, "--height")) a.options.height = atoi(v);
        else if (!strcmp(k, "--seconds")) a.seconds = strtof(v, NULL);
        else if (!strcmp(k, "--frames")) a.frames = atoi(v);
        else if (!strcmp(k, "--every")) a.every = atoi(v);
        else if (!strcmp(k, "--cycle")) a.cycle = atoi(v);
        else if (!strcmp(k, "--enter")) a.enter_frame = atoi(v);
        else if (!strcmp(k, "--out-dir")) a.out_dir = v;
        else if (!strcmp(k, "--backend")) a.backend = v;
        else if (!strcmp(k, "--font")) a.options.font = v;
        else if (!strcmp(k, "--tip")) a.options.tip = v;
        else return usage();
    }
    if (!a.options.root || a.options.width < 64 || a.options.height < 64 || a.options.width > 8192 || a.options.height > 8192 || a.frames < 1)
        return usage();
    a.options.no_ui = a.options.no_ui || !a.headless;
    char error[512];
    a.rt = mu_charsel_rt_open(&a.options, error, sizeof error);
    if (!a.rt)
        return 1;
#ifndef MU_CHARSEL_NO_GL
    int status = a.headless ? headless(&a) : windowed(&a);
#else
    int status = headless(&a);
#endif
    mu_charsel_rt_close(a.rt);
    return status;
}
