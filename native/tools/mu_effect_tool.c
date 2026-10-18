/* mu-effect: headless driver of the reconstructed effect system (NATIVE-FX-001).
 *
 *   mu-effect render EIN --out PNG [--frames N]   frame N (after N update+draw steps)
 *   mu-effect sheet  EIN --out PNG [--frames N] [--every K] [--columns C]
 *                                                  contact sheet of every K-th frame
 *   mu-effect dump   EIN --out FILE [--frames N]  per-frame vertex streams (binary, tests)
 *   mu-effect scan   ROOT                          run every Data/Effect .ein file (read-only)
 *   mu-effect scene  ROOT --out PNG [--world N] [--target X,Y] [--effect SPEC]... [--demo]
 *                    [--frames N] [--size WxH] [--yaw D] [--pitch D] [--distance U] [--fov D] [--flat]
 *                    [--sheet K]
 *                    several effects created by name through the EffectManager
 *                    model (template cache, clones, octree, frustum render) over
 *                    the world's terrain (NATIVE-FX-002). SPEC is
 *                    "Data\Effect\name.ein@DX,DY,DZ[@SCALE]": an instance at
 *                    (DX, DY, DZ) relative to an anchor object standing on the
 *                    terrain at target + (DX, DY); --demo places the effects of
 *                    the client's call sites (see docs/research/client-effect-manager.md).
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
#include "../core/mu_effect_scene.h"
#include "../core/mu_terrain.h"
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
            "       mu-effect scan ROOT\n"
            "       mu-effect scene ROOT --out PNG [--world N] [--target X,Y] [--effect PATH@DX,DY,DZ[@SCALE]]...\n"
            "                 [--demo] [--frames N] [--size WxH] [--yaw D] [--pitch D] [--distance U] [--fov D]\n"
            "                 [--flat] [--sheet K]\n");
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
        for (uint32_t node = 0; node < e.node_count; ++node) {
            uint32_t n = mu_effect_draw_node(&e, node, &fx, NULL);
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
    return mu_effect_draw(e, fx, raster);   /* every node of the tree; NULL raster fills only */
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
           " \"rand_calls\": %llu, \"nodes\": %u, \"sha256\": \"%s\"}\n",
           e->texture_loaded, e->frame, e->fx.count, vertices, e->fx.faulted, (unsigned long long)e->rng.calls,
           e->node_count, hash ? hash : "");
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
    for (int32_t i = 0; i < o->frames; ++i) {   /* the root node's stream; children are filled too */
        mu_effect_update(&e, o->dt);
        vertices = mu_effect_draw_node(&e, 0, &fx, NULL);
        uint32_t header[2] = {vertices, e.fx.count};
        fwrite(header, sizeof header, 1, f);
        fwrite(e.vertices, sizeof(mu_fx_vertex), vertices, f);
        for (uint32_t node = 1; node < e.node_count; ++node)
            mu_effect_draw_node(&e, node, &fx, NULL);
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

/* ---- scene mode (NATIVE-FX-002) ---- */

typedef struct scene_spec {
    char path[256];
    float offset[3];   /* anchor offset on the terrain (x, y) and effect height (z) */
    float scale;
    float local[3];    /* effect position relative to the anchor object (client factory argument) */
} scene_spec;

/* Effects of the client's hard-coded factory calls (static reading, see the
 * finding): the map-object group of 0x00d93599 (four effects, position
 * (0, 0, -20), bone 20) and the monster attachments of 0x0137fbac. Offsets
 * spread them over the ground around the target. */
static const scene_spec DEMO[] = {
    {"Data\\Effect\\fire09-red01.ein", {-600, 0, 120}, 35.0f, {0, 0, -20}},
    {"Data\\Effect\\Sparkle21-red01.ein", {-600, 0, 120}, 50.0f, {0, 0, -20}},
    {"Data\\Effect\\smoke17-red01.ein", {-600, 0, 120}, 50.0f, {0, 0, -20}},
    {"Data\\Effect\\twinkle10-red02.ein", {-600, 0, 120}, 200.0f, {0, 0, -20}},
    {"Data\\Effect\\twister02-cyan01.ein", {0, 300, 0}, 90.0f, {0, 0, 0}},
    {"Data\\Effect\\twister03-cyan01.ein", {0, 300, 0}, 230.0f, {0, 0, 0}},
    {"Data\\Effect\\leaf_particle_F2e.ein", {500, -100, 0}, 9.0f, {0, 0, 70}},
    {"Data\\Effect\\sparkle20-red01.ein", {200, -500, 80}, 16.0f, {0, 0, 0}},
    {"Data\\Effect\\fire10-red01.ein", {200, -500, 80}, 18.0f, {0, 0, 0}},
    {"Data\\Effect\\Lighting03-blue01.ein", {-200, -350, 150}, 60.0f, {0, 0, 0}},
};

static int parse_spec(const char *text, scene_spec *spec)
{
    memset(spec, 0, sizeof *spec);
    spec->scale = 1.0f;
    const char *at = strchr(text, '@');
    if (!at || (size_t)(at - text) >= sizeof spec->path)
        return 1;
    memcpy(spec->path, text, (size_t)(at - text));
    if (sscanf(at + 1, "%f,%f,%f", &spec->offset[0], &spec->offset[1], &spec->offset[2]) != 3)
        return 1;
    const char *second = strchr(at + 1, '@');
    if (second)
        spec->scale = strtof(second + 1, NULL);
    return 0;
}

static int command_scene(int argc, char **argv)
{
    const char *root = argv[2], *out = NULL;
    int32_t world_index = 0, frames = 30, width = 640, height = 400, sheet = 0;
    float target[2] = {13000.0f, 13000.0f}, yaw = -60.0f, pitch = 35.0f, distance = 2600.0f, fov = 45.0f;
    int flat = 0, demo = 0;
    scene_spec specs[64];
    int spec_count = 0;
    for (int i = 3; i < argc; ++i) {
        const char *a = argv[i], *v = i + 1 < argc ? argv[i + 1] : NULL;
        if (!strcmp(a, "--flat")) { flat = 1; continue; }
        if (!strcmp(a, "--demo")) { demo = 1; continue; }
        if (!v) return 2;
        ++i;
        if (!strcmp(a, "--out")) out = v;
        else if (!strcmp(a, "--world")) world_index = atoi(v);
        else if (!strcmp(a, "--frames")) frames = atoi(v);
        else if (!strcmp(a, "--sheet")) sheet = atoi(v);
        else if (!strcmp(a, "--size")) { if (sscanf(v, "%dx%d", &width, &height) != 2) return 2; }
        else if (!strcmp(a, "--target")) { if (sscanf(v, "%f,%f", &target[0], &target[1]) != 2) return 2; }
        else if (!strcmp(a, "--yaw")) yaw = strtof(v, NULL);
        else if (!strcmp(a, "--pitch")) pitch = strtof(v, NULL);
        else if (!strcmp(a, "--distance")) distance = strtof(v, NULL);
        else if (!strcmp(a, "--fov")) fov = strtof(v, NULL);
        else if (!strcmp(a, "--effect")) {
            if (spec_count == 64 || parse_spec(v, &specs[spec_count])) return 2;
            spec_count++;
        } else return 2;
    }
    if (demo)
        for (size_t k = 0; k < sizeof DEMO / sizeof DEMO[0] && spec_count < 64; ++k)
            specs[spec_count++] = DEMO[k];
    if (spec_count == 0 || frames < 1 || width < 8 || height < 8 || width > 4096 || height > 4096 || sheet < 0)
        return 2;
    char error[512];
    mu_world *world = NULL;
    if (!flat) {
        world = mu_world_load(root, world_index, 1, 1, error, sizeof error);
        if (!world) {
            fprintf(stderr, "%s\n", error);
            return 1;
        }
        mu_world_frame(world, 0.0f);
    }
    mu_effect_scene scene;
    if (mu_effect_scene_init(&scene, root, 1) != MU_EFFECT_OK) {
        mu_world_free(world);
        return 1;
    }
    mu_effect_scene_set_world(&scene, world);
    for (int k = 0; k < spec_count; ++k) {
        float anchor[3] = {target[0] + specs[k].offset[0], target[1] + specs[k].offset[1], 0.0f};
        anchor[2] = (world ? mu_world_height_at(world, anchor[0], anchor[1]) : 0.0f) + specs[k].offset[2];
        static const float zero[3] = {0.0f, 0.0f, 0.0f};
        int id = mu_effect_scene_create(&scene, specs[k].path, specs[k].local, zero, specs[k].scale, 0, 0, NULL, 0,
                                        0.0f, error, sizeof error);
        if (id < 0) {
            fprintf(stderr, "%s: %s\n", specs[k].path, error);
            mu_effect_scene_free(&scene);
            mu_world_free(world);
            return 1;
        }
        float matrix[16];
        mu_effect_object_matrix(matrix, anchor, 1.0f);   /* owner path: object scale 1 at the anchor */
        mu_effect_scene_attach(&scene, (uint32_t)id, matrix);
    }
    mu_camera camera;
    memset(&camera, 0, sizeof camera);
    camera.target[0] = target[0];
    camera.target[1] = target[1];
    camera.target[2] = (world ? mu_world_height_at(world, target[0], target[1]) : 0.0f) + 100.0f;
    camera.yaw = yaw;
    camera.pitch = pitch;
    camera.distance = distance;
    camera.fov_y = fov;
    camera.near_plane = 20.0f;
    camera.far_plane = 20000.0f;
    float eye[3];
    mu_camera_eye(&camera, eye);
    mu_raster raster;
    if (mu_raster_init(&raster, width, height)) {
        mu_effect_scene_free(&scene);
        mu_world_free(world);
        return 1;
    }
    raster.front_ccw = 1;
    mu_camera_view(&camera, raster.view);
    mu_camera_projection(&camera, (float)width / (float)height, raster.projection);
    int32_t tiles = sheet ? (frames + sheet - 1) / sheet : 1;
    int32_t columns = tiles < 4 ? tiles : 4, rows = (tiles + columns - 1) / columns;
    int32_t sw = columns * width, sh = rows * height;
    uint8_t *image = calloc((size_t)sw * (size_t)sh * 4u, 1);
    if (!image) {
        mu_raster_free(&raster);
        mu_effect_scene_free(&scene);
        mu_world_free(world);
        return 1;
    }
    int32_t cx = (int32_t)(target[0] / 100.0f), cy = (int32_t)(target[1] / 100.0f);
    int32_t box[4] = {cx - 40 < 0 ? 0 : cx - 40, cy - 40 < 0 ? 0 : cy - 40, cx + 40 > 251 ? 251 : cx + 40,
                      cy + 40 > 251 ? 251 : cy + 40};
    static const uint8_t background[4] = {12, 14, 20, 255};
    uint32_t visible = 0, drawn = 0;
    int32_t tile = 0;
    for (int32_t f = 1; f <= frames; ++f) {
        mu_effect_scene_update(&scene, 0.1f);   /* the client's per-frame effect step 0x01cf103c */
        int shown = sheet ? f % sheet == 0 : f == frames;
        if (shown) {
            mu_raster_clear(&raster, background);
            if (world) {
                mu_world_draw_stats stats;
                mu_world_draw_raster(world, &raster, box[0], box[1], box[2], box[3], &stats);
            }
        }
        visible = mu_effect_scene_render(&scene, eye, camera.target, fov, (float)width / (float)height,
                                         camera.near_plane, camera.far_plane, shown ? &raster : NULL);
        drawn = scene.vertices_drawn;
        if (shown && tile < tiles) {
            int32_t tx = tile % columns, ty = tile / columns;
            for (int32_t y = 0; y < height; ++y)
                memcpy(image + 4u * ((size_t)(ty * height + y) * (size_t)sw + (size_t)(tx * width)),
                       raster.color + 4u * (size_t)y * (size_t)width, 4u * (size_t)width);
            tile++;
        }
    }
    char hash[65];
    mu_sha256_hex(image, (uint64_t)sw * (uint64_t)sh * 4u, hash);
    int status = 0;
    if (out && mu_png_write(out, image, sw, sh)) {
        fprintf(stderr, "cannot write %s\n", out);
        status = 1;
    }
    uint32_t nodes = 0;
    for (uint32_t i = 0; i < scene.instance_count; ++i)
        nodes += mu_fx_tree_count(&scene.instances[i].fx);
    printf("{\"instances\": %u, \"templates\": %u, \"nodes\": %u, \"frames\": %d, \"visible\": %u, "
           "\"vertices\": %u, \"rand_calls\": %llu, \"world\": %d, \"sha256\": \"%s\"}\n",
           scene.instance_count, scene.template_count, nodes, frames, visible, drawn,
           (unsigned long long)scene.rng.calls, world ? world_index : -1, hash);
    free(image);
    mu_raster_free(&raster);
    mu_effect_scene_free(&scene);
    mu_world_free(world);
    return status;
}

int main(int argc, char **argv)
{
    tool_options o;
    if (argc >= 3 && !strcmp(argv[1], "scene")) {
        int status = command_scene(argc, argv);
        if (status == 2)
            usage();
        return status;
    }
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
