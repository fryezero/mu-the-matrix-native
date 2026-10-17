/* mu-terrain: headless front end of the native terrain mode (NATIVE-TERRAIN-001).
 *
 *   mu-terrain info    ROOT --world N            JSON load report of Data/World<folder>
 *   mu-terrain render  ROOT --world N --out PNG  software-rasterized view; prints the
 *                      [--width W --height H --target X,Y --yaw D --pitch D
 *                       --distance U --fov D --time MS --box X0,Y0,X1,Y1 --seed S --no-textures]
 *                                                SHA-256 of the raw RGBA pixels
 *   mu-terrain decrypt FILE                      EncTerrain .map/.att plaintext to stdout
 *   mu-terrain export  ROOT --world N            grids as raw little-endian arrays + JSON trailer
 *   mu-terrain scan    ROOT                      load every Data/World* folder (read-only)
 *
 * ROOT is the game directory that contains Data/. Nothing under ROOT is written.
 */
#define _POSIX_C_SOURCE 200809L
#include <dirent.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../core/mu_camera.h"
#include "../core/mu_png.h"
#include "../core/mu_raster.h"
#include "../core/mu_terrain.h"

typedef struct args {
    const char *command, *root, *out;
    int32_t world, width, height;
    float target[2], yaw, pitch, distance, fov, time;
    int have_target, textures;
    int32_t box[4];
    uint32_t seed;
} args;

static int parse(args *a, int argc, char **argv)
{
    memset(a, 0, sizeof *a);
    a->world = 0;
    a->width = 960;
    a->height = 600;
    a->yaw = -90.0f;
    a->pitch = 45.0f;
    a->distance = 0.0f;
    a->fov = 50.0f;
    a->textures = 1;
    a->seed = 1;
    a->box[0] = 0;
    a->box[1] = 0;
    a->box[2] = 251;
    a->box[3] = 251;
    if (argc < 3)
        return 1;
    a->command = argv[1];
    a->root = argv[2];
    for (int i = 3; i < argc; ++i) {
        const char *k = argv[i];
        const char *v = i + 1 < argc ? argv[i + 1] : NULL;
        if (!strcmp(k, "--no-textures")) {
            a->textures = 0;
            continue;
        }
        if (!v)
            return 1;
        ++i;
        if (!strcmp(k, "--world")) a->world = atoi(v);
        else if (!strcmp(k, "--out")) a->out = v;
        else if (!strcmp(k, "--width")) a->width = atoi(v);
        else if (!strcmp(k, "--height")) a->height = atoi(v);
        else if (!strcmp(k, "--yaw")) a->yaw = strtof(v, NULL);
        else if (!strcmp(k, "--pitch")) a->pitch = strtof(v, NULL);
        else if (!strcmp(k, "--distance")) a->distance = strtof(v, NULL);
        else if (!strcmp(k, "--fov")) a->fov = strtof(v, NULL);
        else if (!strcmp(k, "--time")) a->time = strtof(v, NULL);
        else if (!strcmp(k, "--seed")) a->seed = (uint32_t)strtoul(v, NULL, 10);
        else if (!strcmp(k, "--target")) {
            if (sscanf(v, "%f,%f", &a->target[0], &a->target[1]) != 2)
                return 1;
            a->have_target = 1;
        } else if (!strcmp(k, "--box")) {
            if (sscanf(v, "%d,%d,%d,%d", &a->box[0], &a->box[1], &a->box[2], &a->box[3]) != 4)
                return 1;
        } else
            return 1;
    }
    return 0;
}

static void report_json(FILE *f, const mu_world *w)
{
    const mu_world_report *r = &w->report;
    long tw_height = 0, noground = 0, layer_hist[256] = {0}, alpha_partial = 0;
    for (int32_t i = 0; i < MU_TERRAIN_CELLS; ++i) {
        tw_height += (w->attributes[i] & 0x40) != 0;
        noground += (w->attributes[i] & 8) != 0;
        layer_hist[w->layer1[i]]++;
        alpha_partial += w->alpha[i] > 0.0f && w->alpha[i] < 1.0f;
    }
    float lo = w->height[0], hi = w->height[0];
    for (int32_t i = 1; i < MU_TERRAIN_CELLS; ++i) {
        if (w->height[i] < lo) lo = w->height[i];
        if (w->height[i] > hi) hi = w->height[i];
    }
    fprintf(f, "{\"world\": %d, \"folder\": %d, \"map_status\": %d, \"map_number\": %d, \"att_status\": %d, "
               "\"att_number\": %d, \"att_bytes\": %zu, \"height_rgb\": %d, \"height_rgb_unresolved\": %d, "
               "\"height_status\": %d, \"height_min\": %.3f, \"height_max\": %.3f, \"light_status\": %d, "
               "\"light2_status\": %d, \"obj_status\": %d, \"obj_version\": %d, \"obj_count\": %d, "
               "\"bitmaps_loaded\": %d, \"bitmaps_missing\": %d, \"tw_height_cells\": %ld, \"noground_cells\": %ld, "
               "\"partial_alpha_cells\": %ld, \"special_paths\": %d, \"layer1_used\": [",
            w->world, r->folder, r->map_status, r->map_number, r->att_status, r->att_number, r->att_plain_bytes,
            r->height_rgb, r->height_rgb_unresolved, r->height_status, (double)lo, (double)hi, r->light_status,
            r->light2_status, r->obj_status, r->obj_version, r->obj_count, r->bitmaps_loaded, r->bitmaps_missing,
            tw_height, noground, alpha_partial, mu_terrain_world_has_special_paths(w->world));
    int first = 1;
    for (int k = 0; k < 256; ++k)
        if (layer_hist[k]) {
            fprintf(f, "%s%d", first ? "" : ", ", k);
            first = 0;
        }
    fprintf(f, "]}\n");
}

static mu_world *load(const args *a, int textures)
{
    char error[512];
    mu_world *w = mu_world_load(a->root, a->world, a->seed, textures, error, sizeof error);
    if (!w)
        fprintf(stderr, "%s\n", error);
    return w;
}

static int command_render(const args *a)
{
    mu_world *w = load(a, a->textures);
    if (!w)
        return 1;
    mu_world_frame(w, a->time);
    mu_raster raster;
    if (mu_raster_init(&raster, a->width, a->height)) {
        mu_world_free(w);
        return 1;
    }
    raster.front_ccw = 1;
    mu_camera camera;
    memset(&camera, 0, sizeof camera);
    float x = a->have_target ? a->target[0] : 12800.0f, y = a->have_target ? a->target[1] : 12800.0f;
    camera.target[0] = x;
    camera.target[1] = y;
    camera.target[2] = mu_world_height_at(w, x, y);
    camera.yaw = a->yaw;
    camera.pitch = a->pitch;
    camera.distance = a->distance > 0.0f ? a->distance : 30000.0f;
    camera.fov_y = a->fov;
    camera.near_plane = 50.0f;
    camera.far_plane = 80000.0f;
    mu_camera_view(&camera, raster.view);
    mu_camera_projection(&camera, (float)a->width / (float)a->height, raster.projection);
    static const uint8_t background[4] = {0, 0, 0, 255};
    mu_raster_clear(&raster, background);
    mu_world_draw_stats stats;
    int status = mu_world_draw_raster(w, &raster, a->box[0], a->box[1], a->box[2], a->box[3], &stats);
    char hash[65];
    mu_sha256_hex(raster.color, (uint64_t)a->width * (uint64_t)a->height * 4, hash);
    int failed = a->out && mu_png_write(a->out, raster.color, a->width, a->height);
    printf("{\"sha256\": \"%s\", \"status\": %d, \"faces\": %ld, \"alpha_faces\": %ld, \"grass\": %ld, "
           "\"skipped\": %ld, \"unsupported\": %ld, \"missing_texture_binds\": %ld, \"triangles\": %ld, "
           "\"fragments\": %ld}\n",
           hash, status, stats.tiles.faces, stats.tiles.alpha_faces, stats.tiles.grass, stats.tiles.skipped,
           stats.tiles.unsupported, stats.missing_texture_binds, raster.triangles, raster.fragments);
    mu_raster_free(&raster);
    mu_world_free(w);
    return failed;
}

static int command_decrypt(const char *path)
{
    FILE *f = fopen(path, "rb");
    if (!f)
        return 1;
    fseek(f, 0, SEEK_END);
    long n = ftell(f);
    fseek(f, 0, SEEK_SET);
    uint8_t *raw = malloc((size_t)n + 1);
    size_t got = raw ? fread(raw, 1, (size_t)n, f) : 0;
    fclose(f);
    if (!raw || got != (size_t)n)
        return 1;
    const char *dot = strrchr(path, '.');
    const char *magic = dot && (!strcmp(dot, ".att") || !strcmp(dot, ".ATT")) ? "ATT\x01" : "MAP\x01";
    size_t size = 0;
    char error[256];
    uint8_t *plain = mu_world_decrypt(raw, (size_t)n, magic, &size, error, sizeof error);
    free(raw);
    if (!plain) {
        fprintf(stderr, "%s: %s\n", path, error);
        return 1;
    }
    fwrite(plain, 1, size, stdout);
    free(plain);
    return 0;
}

static int command_export(const args *a)
{
    mu_world *w = load(a, 1);
    if (!w)
        return 1;
    mu_world_frame(w, a->time);
    fwrite(w->height, 4, MU_TERRAIN_CELLS, stdout);
    fwrite(w->layer1, 1, MU_TERRAIN_CELLS, stdout);
    fwrite(w->layer2, 1, MU_TERRAIN_CELLS, stdout);
    fwrite(w->alpha, 4, MU_TERRAIN_CELLS, stdout);
    fwrite(w->attributes, 2, MU_TERRAIN_CELLS, stdout);
    fwrite(w->light, 4, 3 * MU_TERRAIN_CELLS, stdout);
    fwrite(w->light2, 4, 3 * MU_TERRAIN_CELLS, stdout);
    fwrite(w->wave, 4, MU_TERRAIN_CELLS, stdout);
    fwrite(w->wave2, 4, MU_TERRAIN_CELLS, stdout);
    fwrite(w->grass_offset, 4, MU_TERRAIN_CELLS, stdout);
    fwrite(w->grass_map, 1, MU_TERRAIN_CELLS, stdout);
    fwrite(w->light_map, 4, 3 * MU_TERRAIN_CELLS, stdout);
    printf("{\"time\": %.3f, \"water_height\": %.3f, \"bitmaps\": {", (double)w->time, (double)w->water_height);
    int first = 1;
    for (int32_t i = 0; i < MU_WORLD_BITMAPS; ++i)
        if (w->bitmaps[i].width > 0) {
            printf("%s\"%d\": [%d, %d]", first ? "" : ", ", MU_TERRAIN_TEXTURE_TILE + i, w->bitmaps[i].width,
                   w->bitmaps[i].height);
            first = 0;
        }
    printf("}}");
    mu_world_free(w);
    return 0;
}

static int command_scan(const args *a)
{
    char data[2048];
    snprintf(data, sizeof data, "%s/Data", a->root);
    DIR *d = opendir(data);
    if (!d)
        return 1;
    int folders[512], count = 0;
    struct dirent *e;
    while ((e = readdir(d)) && count < 512)
        if (!strncmp(e->d_name, "World", 5) && e->d_name[5] >= '0' && e->d_name[5] <= '9')
            folders[count++] = atoi(e->d_name + 5);
    closedir(d);
    for (int i = 0; i < count; ++i)
        for (int j = i + 1; j < count; ++j)
            if (folders[j] < folders[i]) {
                int t = folders[i];
                folders[i] = folders[j];
                folders[j] = t;
            }
    int loaded = 0;
    for (int i = 0; i < count; ++i) {
        args b = *a;
        b.world = folders[i] - 1;
        char error[512];
        mu_world *w = mu_world_load(a->root, b.world, 1, 0, error, sizeof error);
        if (!w) {
            printf("{\"folder\": %d, \"error\": \"%s\"}\n", folders[i], error);
            continue;
        }
        loaded++;
        report_json(stdout, w);
        mu_world_free(w);
    }
    fprintf(stderr, "%d of %d world folders loaded\n", loaded, count);
    return 0;
}

int main(int argc, char **argv)
{
    if (argc >= 3 && !strcmp(argv[1], "decrypt"))
        return command_decrypt(argv[2]);
    args a;
    if (parse(&a, argc, argv)) {
        fprintf(stderr, "usage: mu-terrain info|render|export|scan ROOT [--world N] [options]\n"
                        "       mu-terrain decrypt FILE\n");
        return 2;
    }
    if (!strcmp(a.command, "info")) {
        mu_world *w = load(&a, 1);
        if (!w)
            return 1;
        report_json(stdout, w);
        mu_world_free(w);
        return 0;
    }
    if (!strcmp(a.command, "render"))
        return command_render(&a);
    if (!strcmp(a.command, "export"))
        return command_export(&a);
    if (!strcmp(a.command, "scan"))
        return command_scan(&a);
    fprintf(stderr, "unknown command %s\n", a.command);
    return 2;
}
