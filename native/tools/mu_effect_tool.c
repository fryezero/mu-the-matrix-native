/* mu-effect: headless driver of the reconstructed effect system (NATIVE-FX-001).
 *
 *   mu-effect render EIN --out PNG [--frames N]   frame N (after N update+draw steps)
 *   mu-effect sheet  EIN --out PNG [--frames N] [--every K] [--columns C]
 *                                                  contact sheet of every K-th frame
 *   mu-effect dump   EIN --out FILE [--frames N]  per-frame vertex streams (binary, tests)
 *   mu-effect scan   ROOT                          run every Data/Effect .ein file (read-only)
 *
 * Options: --root DIR (installation root for the texture path; default derived
 * from ROOT/Data/Effect/x.ein), --dt S (default 0.1, the client's per-frame
 * effect step 0x01cf103c), --seed N (MSVC rand seed, default 1), --size WxH,
 * --yaw/--pitch DEG, --distance D, --target X,Y,Z, --background R,G,B,
 * --nearest, --no-texture.
 */
#define _POSIX_C_SOURCE 200809L
#include <dirent.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>

#include "../core/mu_camera.h"
#include "../core/mu_effect.h"
#include "../core/mu_png.h"
#include "../core/mu_raster.h"

typedef struct tool_options {
    const char *command, *input, *output, *root;
    int32_t frames, every, columns;
    float dt;
    uint32_t seed;
    int32_t width, height;
    float yaw, pitch, distance;
    float target[3];
    int target_set, distance_set;
    uint8_t background[4];
    int nearest, no_texture;
} tool_options;

static void usage(void)
{
    fprintf(stderr,
            "usage: mu-effect render|sheet|dump EIN [--out FILE] [--frames N] [--every K] [--columns C]\n"
            "                 [--root DIR] [--dt S] [--seed N] [--size WxH] [--yaw D] [--pitch D]\n"
            "                 [--distance D] [--target X,Y,Z] [--background R,G,B] [--nearest] [--no-texture]\n"
            "       mu-effect scan ROOT\n");
}

static int parse(tool_options *o, int argc, char **argv)
{
    memset(o, 0, sizeof *o);
    o->frames = 20;
    o->every = 2;
    o->columns = 5;
    o->dt = 0.1f;
    o->seed = 1;
    o->width = 320;
    o->height = 320;
    o->yaw = -90.0f;
    o->pitch = 20.0f;
    o->distance = 8.0f;
    o->background[0] = 16;
    o->background[1] = 16;
    o->background[2] = 20;
    o->background[3] = 255;
    if (argc < 3)
        return 1;
    o->command = argv[1];
    o->input = argv[2];
    for (int i = 3; i < argc; ++i) {
        const char *a = argv[i];
        const char *v = i + 1 < argc ? argv[i + 1] : NULL;
        if (!strcmp(a, "--nearest")) { o->nearest = 1; continue; }
        if (!strcmp(a, "--no-texture")) { o->no_texture = 1; continue; }
        if (!v) return 1;
        ++i;
        if (!strcmp(a, "--out")) o->output = v;
        else if (!strcmp(a, "--root")) o->root = v;
        else if (!strcmp(a, "--frames")) o->frames = atoi(v);
        else if (!strcmp(a, "--every")) o->every = atoi(v);
        else if (!strcmp(a, "--columns")) o->columns = atoi(v);
        else if (!strcmp(a, "--dt")) o->dt = strtof(v, NULL);
        else if (!strcmp(a, "--seed")) o->seed = (uint32_t)strtoul(v, NULL, 0);
        else if (!strcmp(a, "--size")) {
            if (sscanf(v, "%dx%d", &o->width, &o->height) != 2) return 1;
        } else if (!strcmp(a, "--yaw")) o->yaw = strtof(v, NULL);
        else if (!strcmp(a, "--pitch")) o->pitch = strtof(v, NULL);
        else if (!strcmp(a, "--distance")) { o->distance = strtof(v, NULL); o->distance_set = 1; }
        else if (!strcmp(a, "--target")) {
            if (sscanf(v, "%f,%f,%f", &o->target[0], &o->target[1], &o->target[2]) != 3) return 1;
            o->target_set = 1;
        } else if (!strcmp(a, "--background")) {
            int r, g, b;
            if (sscanf(v, "%d,%d,%d", &r, &g, &b) != 3) return 1;
            o->background[0] = (uint8_t)r;
            o->background[1] = (uint8_t)g;
            o->background[2] = (uint8_t)b;
        } else return 1;
    }
    if (o->frames < 0 || o->every < 1 || o->columns < 1 || o->width < 8 || o->height < 8 || o->width > 4096 ||
        o->height > 4096)
        return 1;
    return 0;
}

/* Dry run with the same seed: bounding box of every vertex the effect emits
 * over the requested frames (the simulation is deterministic). */
static int effect_bounds(const tool_options *o, float lo[3], float hi[3])
{
    mu_effect e;
    char error[512];
    if (mu_effect_load_file(&e, o->input, o->root, o->seed, error, sizeof error) != MU_EFFECT_OK)
        return 0;
    mu_fx_camera fx;
    float eye[3] = {e.fx.position[0], e.fx.position[1] - 10.0f, e.fx.position[2] + 3.0f};
    mu_effect_camera(&fx, eye, e.fx.position);
    int any = 0;
    for (int32_t f = 0; f < o->frames; ++f) {
        mu_effect_update(&e, o->dt);
        uint32_t n = mu_fx_draw(&e.fx, &fx, 0, e.vertices, NULL);
        for (uint32_t i = 0; i < n; ++i)
            for (int k = 0; k < 3; ++k) {
                float v = e.vertices[i].position[k];
                if (!(v == v) || v > 1e6f || v < -1e6f)
                    continue;
                if (!any || v < lo[k]) lo[k] = v;
                if (!any || v > hi[k]) hi[k] = v;
                if (k == 2) any = 1;
            }
    }
    mu_effect_free(&e);
    return any;
}

static void setup_camera(const tool_options *o, const mu_effect *e, mu_camera *camera, mu_fx_camera *fx)
{
    memset(camera, 0, sizeof *camera);
    float lo[3] = {0, 0, 0}, hi[3] = {0, 0, 0};
    if (!o->target_set && !o->distance_set && effect_bounds(o, lo, hi)) {
        double r2 = 0.0;
        for (int k = 0; k < 3; ++k) {
            camera->target[k] = (float)(((double)lo[k] + (double)hi[k]) * 0.5);
            double half = ((double)hi[k] - (double)lo[k]) * 0.5;
            r2 += half * half;
        }
        double radius = r2 > 0.0625 ? sqrt(r2) : 0.25;
        camera->fov_y = 45.0f;
        camera->distance = (float)(radius / mu_det_sin(22.5 * 3.14159265358979 / 180.0) * 1.05);
        camera->near_plane = camera->distance * 0.01f;
        camera->far_plane = camera->distance + (float)radius * 4.0f;
        camera->yaw = o->yaw;
        camera->pitch = o->pitch;
        float eye[3];
        mu_camera_eye(camera, eye);
        mu_effect_camera(fx, eye, camera->target);
        return;
    }
    camera->target[0] = o->target_set ? o->target[0] : e->fx.position[0];
    camera->target[1] = o->target_set ? o->target[1] : e->fx.position[1];
    camera->target[2] = o->target_set ? o->target[2] : e->fx.position[2] + 1.0f;
    camera->yaw = o->yaw;
    camera->pitch = o->pitch;
    camera->distance = o->distance;
    camera->fov_y = 45.0f;
    camera->near_plane = 0.05f;
    camera->far_plane = 1000.0f;
    float eye[3];
    mu_camera_eye(camera, eye);
    mu_effect_camera(fx, eye, camera->target);
}

/* One client frame: update, then draw (the draw marks the effect drawn, which
 * the next particle update requires). */
static uint32_t frame(mu_effect *e, const tool_options *o, const mu_fx_camera *fx, mu_raster *raster)
{
    mu_effect_update(e, o->dt);
    if (raster)
        return mu_effect_draw(e, fx, raster);
    return mu_fx_draw(&e->fx, fx, e->texture_loaded, e->vertices, NULL);
}

/* Prints a JSON string value (escapes quotes, backslashes and control bytes). */
static void print_json_string(const char *text)
{
    putchar('"');
    for (const unsigned char *p = (const unsigned char *)(text ? text : ""); *p; ++p) {
        if (*p == '"' || *p == '\\')
            printf("\\%c", *p);
        else if (*p < 0x20 || *p >= 0x7f)
            printf("\\u%04x", *p);
        else
            putchar(*p);
    }
    putchar('"');
}

static void print_summary(const mu_effect *e, const char *hash, uint32_t vertices)
{
    printf("{\"name\": ");
    print_json_string(e->fx.name);
    printf(", \"type\": %d, \"texture\": ", e->fx.type);
    print_json_string(e->fx.texture);
    printf(", \"texture_loaded\": %d, \"frames\": %u, \"particles\": %u, \"vertices\": %u, \"faulted\": %d,"
           " \"rand_calls\": %llu, \"sha256\": \"%s\"}\n",
           e->texture_loaded, e->frame, e->fx.count, vertices, e->fx.faulted, (unsigned long long)e->rng.calls,
           hash ? hash : "");
}

static int load(const tool_options *o, mu_effect *e)
{
    char error[512];
    if (mu_effect_load_file(e, o->input, o->root, o->seed, error, sizeof error) != MU_EFFECT_OK) {
        fprintf(stderr, "%s: %s\n", o->input, error);
        return 1;
    }
    if (o->no_texture && e->texture_loaded) {
        mu_image_free(&e->texture);
        e->texture_loaded = 0;
    }
    return 0;
}

static int command_render(const tool_options *o)
{
    mu_effect e;
    if (load(o, &e))
        return 1;
    mu_camera camera;
    mu_fx_camera fx;
    setup_camera(o, &e, &camera, &fx);
    mu_raster raster;
    if (mu_raster_init(&raster, o->width, o->height))
        return 1;
    raster.linear = !o->nearest;
    mu_camera_view(&camera, raster.view);
    mu_camera_projection(&camera, (float)o->width / (float)o->height, raster.projection);
    uint32_t vertices = 0;
    for (int32_t f = 0; f < o->frames; ++f) {
        int last = f + 1 == o->frames;
        if (last)
            mu_raster_clear(&raster, o->background);
        vertices = frame(&e, o, &fx, last ? &raster : NULL);
    }
    if (o->frames == 0)
        mu_raster_clear(&raster, o->background);
    char hash[65];
    mu_sha256_hex(raster.color, (uint64_t)o->width * (uint64_t)o->height * 4u, hash);
    int status = 0;
    if (o->output && mu_png_write(o->output, raster.color, o->width, o->height)) {
        fprintf(stderr, "cannot write %s\n", o->output);
        status = 1;
    }
    print_summary(&e, hash, vertices);
    mu_raster_free(&raster);
    mu_effect_free(&e);
    return status;
}

static int command_sheet(const tool_options *o)
{
    mu_effect e;
    if (load(o, &e))
        return 1;
    mu_camera camera;
    mu_fx_camera fx;
    setup_camera(o, &e, &camera, &fx);
    int32_t tiles = (o->frames + o->every - 1) / o->every;
    if (tiles < 1)
        tiles = 1;
    int32_t columns = o->columns < tiles ? o->columns : tiles;
    int32_t rows = (tiles + columns - 1) / columns;
    int32_t sw = columns * o->width, sh = rows * o->height;
    uint8_t *sheet = calloc((size_t)sw * (size_t)sh * 4u, 1);
    mu_raster raster;
    if (!sheet || mu_raster_init(&raster, o->width, o->height)) {
        free(sheet);
        return 1;
    }
    raster.linear = !o->nearest;
    mu_camera_view(&camera, raster.view);
    mu_camera_projection(&camera, (float)o->width / (float)o->height, raster.projection);
    int32_t tile = 0;
    uint32_t vertices = 0;
    for (int32_t f = 1; f <= o->frames; ++f) {
        int shown = f % o->every == 0;
        if (shown)
            mu_raster_clear(&raster, o->background);
        vertices = frame(&e, o, &fx, shown ? &raster : NULL);
        if (shown && tile < tiles) {
            int32_t tx = tile % columns, ty = tile / columns;
            for (int32_t y = 0; y < o->height; ++y)
                memcpy(sheet + 4u * ((size_t)(ty * o->height + y) * (size_t)sw + (size_t)(tx * o->width)),
                       raster.color + 4u * (size_t)y * (size_t)o->width, 4u * (size_t)o->width);
            tile++;
        }
    }
    char hash[65];
    mu_sha256_hex(sheet, (uint64_t)sw * (uint64_t)sh * 4u, hash);
    int status = 0;
    if (o->output && mu_png_write(o->output, sheet, sw, sh)) {
        fprintf(stderr, "cannot write %s\n", o->output);
        status = 1;
    }
    print_summary(&e, hash, vertices);
    free(sheet);
    mu_raster_free(&raster);
    mu_effect_free(&e);
    return status;
}

/* Binary dump: per frame u32 vertex count, u32 particle count, then the
 * vertex records (36 bytes each). */
static int command_dump(const tool_options *o)
{
    mu_effect e;
    if (load(o, &e))
        return 1;
    if (!o->output) {
        fprintf(stderr, "dump needs --out\n");
        mu_effect_free(&e);
        return 1;
    }
    FILE *f = fopen(o->output, "wb");
    if (!f) {
        mu_effect_free(&e);
        return 1;
    }
    mu_camera camera;
    mu_fx_camera fx;
    setup_camera(o, &e, &camera, &fx);
    uint32_t vertices = 0;
    for (int32_t i = 0; i < o->frames; ++i) {
        vertices = frame(&e, o, &fx, NULL);
        uint32_t header[2] = {vertices, e.fx.count};
        fwrite(header, sizeof header, 1, f);
        fwrite(e.vertices, sizeof(mu_fx_vertex), vertices, f);
    }
    fclose(f);
    print_summary(&e, NULL, vertices);
    mu_effect_free(&e);
    return 0;
}

static int command_scan(const tool_options *o)
{
    char directory[4096];
    snprintf(directory, sizeof directory, "%s/Data/Effect", o->input);
    DIR *d = opendir(directory);
    if (!d) {
        fprintf(stderr, "cannot open %s\n", directory);
        return 1;
    }
    long files = 0, particle = 0, billboard = 0, failed = 0, faulted = 0, textured = 0, max_particles = 0;
    struct dirent *entry;
    while ((entry = readdir(d)) != NULL) {
        size_t n = strlen(entry->d_name);
        if (n < 5 || strcasecmp(entry->d_name + n - 4, ".ein"))
            continue;
        tool_options local = *o;
        char path[8192];
        snprintf(path, sizeof path, "%s/%s", directory, entry->d_name);
        local.input = path;
        local.root = o->input;
        mu_effect e;
        char error[512];
        files++;
        if (mu_effect_load_file(&e, path, o->input, o->seed, error, sizeof error) != MU_EFFECT_OK) {
            failed++;
            continue;
        }
        mu_camera camera;
        mu_fx_camera fx;
        setup_camera(&local, &e, &camera, &fx);
        long peak = 0;
        for (int32_t i = 0; i < local.frames; ++i) {
            frame(&e, &local, &fx, NULL);
            if ((long)e.fx.count > peak)
                peak = (long)e.fx.count;
        }
        if (peak > max_particles)
            max_particles = peak;
        particle += e.fx.type == MU_FX_PARTICLE_SYSTEM;
        billboard += e.fx.type == MU_FX_BILLBOARD;
        faulted += e.fx.faulted;
        textured += e.texture_loaded;
        mu_effect_free(&e);
    }
    closedir(d);
    printf("{\"files\": %ld, \"particle_systems\": %ld, \"billboards\": %ld, \"failed\": %ld, \"faulted\": %ld,"
           " \"textures_loaded\": %ld, \"max_particles\": %ld, \"frames\": %d}\n",
           files, particle, billboard, failed, faulted, textured, max_particles, o->frames);
    return failed ? 1 : 0;
}

int main(int argc, char **argv)
{
    tool_options o;
    if (argc >= 2 && !strcmp(argv[1], "scan") && argc >= 3) {
        if (parse(&o, argc, argv))
            return 2;
        return command_scan(&o);
    }
    if (parse(&o, argc, argv)) {
        usage();
        return 2;
    }
    if (!strcmp(o.command, "render"))
        return command_render(&o);
    if (!strcmp(o.command, "sheet"))
        return command_sheet(&o);
    if (!strcmp(o.command, "dump"))
        return command_dump(&o);
    usage();
    return 2;
}
