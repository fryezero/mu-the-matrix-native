/* mu-frame: headless run of the native frame-loop skeleton (NATIVE-FRAME-001).
 *
 *   mu-frame [MODEL.bmd] [--frames N] [--every K] [--out-dir DIR] [--width W --height H]
 *            [--work MS] [--quiet]
 *
 * Simulates the client's frame driver with a virtual tick clock: each frame
 * runs the due 40 ms logic steps, the client camera (MoveMainCamera,
 * BeginOpengl, CreateScreenVector), a software render, and the frame cap
 * (the virtual clock advances by --work milliseconds of render time plus
 * the cap's Sleep). A fixed input script exercises click-to-move, the wheel
 * FOV zoom and a few hotkeys. Every K-th frame (and the frames around each
 * scripted event) is written as PNG; one JSON line per frame reports the
 * camera state and the image SHA-256. Without a model the hero is a box.
 * Terrain is a flat placeholder grid (not client data).
 */
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#include "../core/mu_bmd.h"
#include "../core/mu_frame.h"
#include "../core/mu_model.h"
#include "../core/mu_png.h"
#include "../core/mu_raster.h"
#include "../core/mu_scene.h"
#include "../core/mu_textures.h"

typedef struct event {
    int32_t frame;
    uint32_t message, wparam;
    int32_t x, y; /* 640x480 virtual position for mouse messages */
} event;

/* The input script (frame numbers at 25 FPS). */
static const event script[] = {
    {8, 0x200, 0, 470, 320},          /* move the cursor */
    {9, 0x201, 1, 470, 320},          /* left down: click-to-move */
    {10, 0x202, 0, 470, 320},         /* left up */
    {20, 0x100, 0x49, 0, 0},          /* I down (UI panel hotkey) */
    {22, 0x101, 0x49, 0, 0},
    {45, 0x20a, 120u << 16, 470, 320}, /* wheel up: FOV 35 -> 30 */
    {70, 0x20a, 120u << 16, 470, 320}, /* wheel up: FOV 30 -> 20 */
    {95, 0x200, 0, 140, 140},
    {96, 0x201, 1, 140, 140},          /* second click, other direction */
    {97, 0x202, 0, 140, 140},
    {130, 0x20a, (uint32_t)(0x10000 - 120) << 16, 140, 140}, /* wheel down: 20 -> 30 */
    {150, 0x20a, (uint32_t)(0x10000 - 120) << 16, 140, 140}, /* wheel down: 30 -> 35 */
};

typedef struct hero_model {
    int loaded;
    mu_bmd bmd;
    mu_model model;
    mu_textures textures;
    mu_model_params params;
    uint16_t action;
    float frame;
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

/* Placeholder animation: action 0 standing, action 2 walking when the model
 * has it (the usual MU monster layout; not a client reading). */
static void animate_model(hero_model *h, const mu_frame_world *w, int32_t steps)
{
    if (!h->loaded)
        return;
    uint16_t action = (w->moving && h->bmd.action_count > 2) ? 2 : 0;
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

static int is_saved(int32_t frame, int32_t every)
{
    if (every > 0 && frame % every == 0)
        return 1;
    for (size_t i = 0; i < sizeof script / sizeof script[0]; ++i)
        if (script[i].message == 0x201 || script[i].message == 0x20a)
            if (frame == script[i].frame + 1 || frame == script[i].frame + 14)
                return 1;
    return 0;
}

int main(int argc, char **argv)
{
    const char *model_path = NULL, *out_dir = NULL;
    int32_t frames = 180, every = 30, width = 800, height = 600, work = 12, quiet = 0;
    for (int i = 1; i < argc; ++i) {
        const char *a = argv[i];
        if (!strcmp(a, "--frames") && i + 1 < argc) frames = atoi(argv[++i]);
        else if (!strcmp(a, "--every") && i + 1 < argc) every = atoi(argv[++i]);
        else if (!strcmp(a, "--out-dir") && i + 1 < argc) out_dir = argv[++i];
        else if (!strcmp(a, "--width") && i + 1 < argc) width = atoi(argv[++i]);
        else if (!strcmp(a, "--height") && i + 1 < argc) height = atoi(argv[++i]);
        else if (!strcmp(a, "--work") && i + 1 < argc) work = atoi(argv[++i]);
        else if (!strcmp(a, "--quiet")) quiet = 1;
        else if (a[0] != '-' && !model_path) model_path = a;
        else {
            fprintf(stderr, "usage: mu-frame [MODEL.bmd] [--frames N] [--every K] [--out-dir DIR] [--width W]"
                            " [--height H] [--work MS] [--quiet]\n");
            return 2;
        }
    }
    if (width < 64 || height < 64 || width > 4096 || height > 4096 || frames < 1) {
        fprintf(stderr, "bad size or frame count\n");
        return 2;
    }
    if (out_dir && mkdir(out_dir, 0755) && errno != EEXIST) {
        fprintf(stderr, "cannot create %s\n", out_dir);
        return 1;
    }
    hero_model hero;
    memset(&hero, 0, sizeof hero);
    if (model_path && load_model(&hero, model_path))
        return 1;
    static mu_frame_world world;
    mu_frame_world_init(&world, (uint32_t)width, (uint32_t)height, 128, 128);
    mu_raster raster;
    if (mu_raster_init(&raster, width, height)) {
        fprintf(stderr, "raster allocation failed\n");
        return 1;
    }
    raster.linear = 1;
    raster.front_ccw = 1;
    if (hero.loaded) {
        raster.textures = hero.textures.slots;
        raster.texture_count = hero.textures.count;
    }
    mu_render_backend backend;
    mu_raster_backend(&raster, &backend);
    const uint8_t sky[4] = {28, 34, 48, 255};
    uint32_t now = 100000;
    size_t next = 0;
    world.clock.frame_tick = now;
    unsigned long total_steps = 0;
    for (int32_t frame = 0; frame < frames; ++frame) {
        while (next < sizeof script / sizeof script[0] && script[next].frame == frame) {
            const event *e = &script[next++];
            uint32_t lparam = 0;
            if (e->message >= 0x200 && e->message <= 0x20a) {
                uint32_t px = (uint32_t)((float)e->x * world.mouse.scale_x);
                uint32_t py = (uint32_t)((float)e->y * world.mouse.scale_y);
                lparam = (py << 16) | px;
                if (e->message != 0x200)
                    mu_frame_world_message(&world, 0x200, 0, lparam);
            }
            if (e->message == 0x100 || e->message == 0x101)
                mu_frame_world_key(&world, (int)e->wparam, e->message == 0x100);
            mu_frame_world_message(&world, e->message, e->wparam, lparam);
        }
        int32_t steps = mu_frame_world_update(&world, now);
        total_steps += (unsigned long)steps;
        animate_model(&hero, &world, steps);
        mu_frame_world_begin_render(&world, now);
        int save = out_dir && is_saved(frame, every);
        char hash[65] = "";
        long triangles = 0;
        if (save) {
            memcpy(raster.view, world.view.modelview, sizeof raster.view);
            memcpy(raster.projection, world.view.projection, sizeof raster.projection);
            mu_raster_clear(&raster, sky);
            triangles = mu_frame_draw_world(&world, &backend, 26, !hero.loaded);
            if (hero.loaded) {
                mu_draw_options options;
                mu_draw_default_options(&options);
                mu_draw_stats stats = {0, 0, 0};
                mu_scene_draw_model(&hero.model, &options, &backend, &stats);
            }
            mu_sha256_hex(raster.color, (uint64_t)width * (uint64_t)height * 4, hash);
            char path[4096];
            snprintf(path, sizeof path, "%s/frame-%03d.png", out_dir, frame);
            if (mu_png_write(path, raster.color, width, height)) {
                fprintf(stderr, "cannot write %s\n", path);
                return 1;
            }
        }
        now += (uint32_t)work;
        int32_t sleep = mu_frame_world_end_render(&world);
        if (sleep > 0)
            now += (uint32_t)sleep;
        if (!quiet && (save || frame == frames - 1)) {
            const mu_client_view *v = &world.view;
            printf("{\"frame\": %d, \"tick\": %u, \"logic_steps\": %lu, \"fov\": %.4f, \"far\": %.1f,"
                   " \"angle\": [%.4f, %.4f, %.4f], \"eye\": [%.3f, %.3f, %.3f], \"distance\": %.3f,"
                   " \"hero\": [%.2f, %.2f, %.2f], \"target_tile\": [%d, %d], \"moving\": %d, \"picks\": %d,"
                   " \"hits\": %d, \"triangles\": %ld, \"sha256\": \"%s\"}\n",
                   frame, now, total_steps, (double)v->fov, (double)v->view_far, (double)v->angle[0],
                   (double)v->angle[1], (double)v->angle[2], (double)v->position[0], (double)v->position[1],
                   (double)v->position[2], (double)world.camera.distance, (double)world.hero[0], (double)world.hero[1],
                   (double)world.hero[2], world.target_tile[0], world.target_tile[1], world.moving, world.picks,
                   world.pick_hits, triangles, hash);
        }
    }
    if (!quiet)
        for (int32_t i = 0; i < world.log_count; ++i)
            printf("{\"log\": \"%s\"}\n", world.log[i]);
    mu_raster_free(&raster);
    if (hero.loaded) {
        mu_textures_free(&hero.textures);
        mu_model_free(&hero.model);
        mu_bmd_free(&hero.bmd);
    }
    return 0;
}
