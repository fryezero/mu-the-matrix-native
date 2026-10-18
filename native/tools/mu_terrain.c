/* mu-terrain: headless front end of the native terrain mode (NATIVE-TERRAIN-001).
 *
 *   mu-terrain info    ROOT --world N            JSON load report of Data/World<folder>
 *   mu-terrain render  ROOT --world N --out PNG  software-rasterized view; prints the
 *                      [--width W --height H --target X,Y --yaw D --pitch D
 *                       --distance U --fov D --time MS --box X0,Y0,X1,Y1 --seed S --no-textures
 *                       --light X,Y,R,G,B,RANGE ...   AddTerrainLight sources (NATIVE-TERRAIN-002)
 *                       --decal X,Y,SIZE,ROTATION ... Effect\flare01 decals (additive)
 *                       --detail N                    graphics option (>= 4: 0x4000 neighbour faces)
 *                       --frustum HX,HY [--zoom M --camera-angle D --view-far U --top-view]
 *                                                     client visibility around the hero position
 *                       --legacy]                     NATIVE-TERRAIN-001 behaviour (whole box, no lights)
 *                                                SHA-256 of the raw RGBA pixels
 *                      [--objects installed|gallery|PLAIN_FILE   static map objects (NATIVE-OBJECTS-001)
 *                       --object-tile X,Y --object-columns N --object-spacing U   gallery layout
 *                       --object-steps N]   the client's object lifecycle (NATIVE-OBJECTS-002): CreateObject,
 *                                           N MoveObjects steps (animation, object lights), RenderObject
 *                      [--light-report 1]   with --object-steps: one JSON line per drawn object with its
 *                                           RenderObject pose and light inputs and per-normal lights (NATIVE-LIGHT-001)
 *   mu-terrain objects ROOT --world N [--objects installed|gallery|PLAIN_FILE]
 *                                                JSON: object file status, records, type -> model file
 *   mu-terrain decrypt FILE                      EncTerrain .map/.att plaintext to stdout
 *   mu-terrain export  ROOT --world N            grids as raw little-endian arrays + JSON trailer
 *   mu-terrain scan    ROOT                      load every Data/World* folder (read-only)
 *
 * ROOT is the game directory that contains Data/. Nothing under ROOT is written.
 */
#define _POSIX_C_SOURCE 200809L
#include <dirent.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../core/mu_camera.h"
#include "../core/mu_objects.h"
#include "../core/mu_png.h"
#include "../core/mu_scene.h"
#include "../core/mu_raster.h"
#include "../core/mu_terrain.h"

typedef struct args {
    const char *command, *root, *out;
    int32_t world, width, height;
    float target[2], yaw, pitch, distance, fov, time;
    int have_target, textures;
    int32_t box[4];
    uint32_t seed;
    float lights[16][6];
    int light_count;
    float decals[16][4];
    int decal_count;
    int32_t detail, zoom;
    float hero[2], camera_angle, view_far;
    int have_frustum, top_view, legacy;
    const char *objects;          /* NULL, "installed", "gallery" or a plaintext file */
    int32_t object_tile[2], object_columns, object_steps, light_report;
    float object_spacing;
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
    a->zoom = 3;
    a->camera_angle = -48.5f;
    a->view_far = 3000.0f;
    a->object_tile[0] = 128;
    a->object_tile[1] = 128;
    a->object_columns = 12;
    a->object_spacing = 600.0f;
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
        if (!strcmp(k, "--top-view")) {
            a->top_view = 1;
            continue;
        }
        if (!strcmp(k, "--legacy")) {
            a->legacy = 1;
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
        else if (!strcmp(k, "--detail")) a->detail = atoi(v);
        else if (!strcmp(k, "--zoom")) a->zoom = atoi(v);
        else if (!strcmp(k, "--camera-angle")) a->camera_angle = strtof(v, NULL);
        else if (!strcmp(k, "--view-far")) a->view_far = strtof(v, NULL);
        else if (!strcmp(k, "--objects")) a->objects = v;
        else if (!strcmp(k, "--object-columns")) a->object_columns = atoi(v);
        else if (!strcmp(k, "--object-steps")) a->object_steps = atoi(v);
        else if (!strcmp(k, "--light-report")) a->light_report = atoi(v);
        else if (!strcmp(k, "--object-spacing")) a->object_spacing = strtof(v, NULL);
        else if (!strcmp(k, "--object-tile")) {
            if (sscanf(v, "%d,%d", &a->object_tile[0], &a->object_tile[1]) != 2)
                return 1;
        }
        else if (!strcmp(k, "--light")) {
            if (a->light_count >= 16)
                return 1;
            float *l = a->lights[a->light_count++];
            if (sscanf(v, "%f,%f,%f,%f,%f,%f", &l[0], &l[1], &l[2], &l[3], &l[4], &l[5]) != 6)
                return 1;
        } else if (!strcmp(k, "--decal")) {
            if (a->decal_count >= 16)
                return 1;
            float *d = a->decals[a->decal_count++];
            if (sscanf(v, "%f,%f,%f,%f", &d[0], &d[1], &d[2], &d[3]) != 4)
                return 1;
        } else if (!strcmp(k, "--frustum")) {
            if (sscanf(v, "%f,%f", &a->hero[0], &a->hero[1]) != 2)
                return 1;
            a->have_frustum = 1;
        }
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

/* Loads the requested object records (and, when models is set, their models). */
static int load_objects(const args *a, const mu_world *w, mu_objects *o, int models, char *error, size_t size)
{
    mu_objects_init(o, a->world);
    int status;
    if (!strcmp(a->objects, "installed"))
        status = mu_objects_load_installed(o, a->root, error, size);
    else if (!strcmp(a->objects, "gallery"))
        status = mu_objects_gallery(o, a->root, w, a->object_tile[0], a->object_tile[1], a->object_columns,
                                    a->object_spacing, error, size);
    else
        status = mu_objects_load_plain_file(o, a->objects, error, size);
    if (status == MU_OBJECTS_FILE_OK && models)
        mu_objects_load_models(o, a->root, !a->textures);
    return status;
}

static void objects_json(FILE *f, const mu_objects *o, const char *error, long drawn)
{
    fprintf(f, "\"objects\": {\"source\": \"%s\", \"status\": %d, \"error\": \"%s\", \"folder\": %d, "
               "\"version\": %u, \"map\": %u, \"count\": %d, \"types\": %d, \"models_loaded\": %d, "
               "\"models_missing\": %d, \"skipped_types\": %d, \"drawn\": %ld}",
            o->source, o->status, o->status == MU_OBJECTS_FILE_OK ? "" : error, o->folder, o->header.version,
            o->header.map, o->count, o->types_used, o->models_loaded, o->models_missing, o->skipped_types, drawn);
}

/* Draws every placed object through the mesh-draw port into the raster. */
static long draw_objects(mu_objects *o, const mu_world *w, mu_raster *raster)
{
    mu_render_backend backend;
    mu_raster_backend(raster, &backend);
    mu_draw_options options;
    mu_draw_default_options(&options);
    raster->linear = 1;
    long drawn = 0;
    for (int32_t i = 0; i < o->count; ++i) {
        mu_object_model *m = mu_objects_place(o, i, w);
        if (!m)
            continue;
        raster->textures = m->textures.slots;
        raster->texture_count = m->textures.count;
        raster->texture_filter = m->textures.filter;
        raster->texture_wrap = m->textures.wrap;
        options.textures = &m->textures;
        mu_draw_stats ds = {0, 0, 0, 0};
        if (!mu_scene_draw_model(&m->model, &options, &backend, &ds))
            ++drawn;
    }
    raster->textures = NULL;
    raster->texture_count = 0;
    raster->texture_filter = NULL;
    raster->texture_wrap = NULL;
    return drawn;
}

static int command_objects(const args *a)
{
    mu_world *w = load(a, 0);
    if (!w)
        return 1;
    args b = *a;
    if (!b.objects)
        b.objects = "installed";
    mu_objects o;
    char error[512] = "";
    load_objects(&b, w, &o, 0, error, sizeof error);
    printf("{\"world\": %d, ", a->world);
    objects_json(stdout, &o, error, 0);
    printf(", \"model_folder\": %d, \"records\": [", mu_objects_folder(a->world));
    for (int32_t i = 0; i < o.count; ++i) {
        const mu_object_record *r = &o.records[i];
        const float v[7] = {r->position[0], r->position[1], r->position[2], r->angle[0], r->angle[1], r->angle[2],
                            r->scale};
        printf("%s[%d", i ? ", " : "", r->type);
        for (int k = 0; k < 7; ++k) {   /* some installed records carry NaN fields: JSON null */
            if (isfinite(v[k]))
                printf(k == 6 ? ", %.4f" : ", %.3f", (double)v[k]);
            else
                printf(", null");
        }
        printf("]");
    }
    printf("], \"models\": {");
    int first = 1;
    for (int32_t t = 0; t < MU_OBJECT_TYPES; ++t) {
        char relative[512], path[2048];
        if (!mu_objects_model_file(a->world, t, relative, sizeof relative))
            continue;
        int exists = mu_objects_resolve(a->root, relative, path, sizeof path);
        printf("%s\"%d\": [\"%s\", %d]", first ? "" : ", ", t, relative, exists);
        first = 0;
    }
    printf("}}\n");
    mu_objects_free(&o);
    mu_world_free(w);
    return 0;
}

static int command_render(const args *a)
{
    mu_world *w = load(a, a->textures);
    if (!w)
        return 1;
    w->detail = a->detail;
    if (!a->legacy && a->decal_count)
        mu_world_load_extra(w, a->root, 0x7ef7, "Effect/flare01.jpg", 1, 1); /* 0x7ef7: LINEAR, CLAMP */
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
    mu_terrain_frustum frustum;
    int status, frustum_status = -1;
    if (a->have_frustum && !a->legacy) {
        /* the client's view around the hero: rows of the camera that looks at the hero */
        mu_camera client = camera;
        client.target[0] = a->hero[0];
        client.target[1] = a->hero[1];
        client.target[2] = mu_world_height_at(w, a->hero[0], a->hero[1]);
        client.yaw = -45.0f;                      /* the client's fixed CameraAngle[2] direction */
        client.pitch = 90.0f + a->camera_angle;
        client.distance = 1000.0f;
        float view[16], eye[3];
        mu_camera_view(&client, view);
        mu_camera_eye(&client, eye);
        float rows[12];
        for (int i = 0; i < 3; ++i)
            for (int j = 0; j < 4; ++j)
                rows[4 * i + j] = view[4 * j + i];
        const float hero[3] = {a->hero[0], a->hero[1], client.target[2]};
        frustum_status = mu_world_client_frustum(w, rows, eye, hero, a->camera_angle, a->width, a->zoom,
                                                 a->view_far, a->fov, &frustum);
        mu_world_frame_box(w, a->time, frustum.x_min, frustum.y_min, frustum.x_max, frustum.y_max);
    } else {
        mu_world_frame(w, a->time);
    }
    mu_objects objects;
    char object_error[512] = "";
    int objects_loaded = 0;
    if (a->objects) {
        objects_loaded = load_objects(a, w, &objects, 1, object_error, sizeof object_error) == MU_OBJECTS_FILE_OK;
        if (!objects_loaded)
            fprintf(stderr, "objects: %s\n", object_error);
    }
    if (objects_loaded && a->object_steps > 0 && !a->legacy) {
        /* NATIVE-OBJECTS-002: CreateObject, then MoveObjects steps of 40 ms; each step's lights after the
         * frame light copy, as the client's tick does */
        mu_objects_start(&objects, a->root);
        const float hx = a->have_frustum ? a->hero[0] : ((float)(a->box[0] + a->box[2]) * 0.5f + 0.5f) * 100.0f;
        const float hy = a->have_frustum ? a->hero[1] : ((float)(a->box[1] + a->box[3]) * 0.5f + 0.5f) * 100.0f;
        const int32_t tx = (int32_t)(hx / 100.0f) & 0xff, ty = (int32_t)(hy / 100.0f) & 0xff;
        for (int32_t step = 0; step < a->object_steps; ++step) {
            const float t = a->time - 40.0f * (float)(a->object_steps - 1 - step);
            mu_objects_step_inputs in = {6, w->layer1[(ty << 8) + tx], t, {hx, hy, 0.0f},
                                         a->have_frustum ? frustum.x2d : NULL, a->have_frustum ? frustum.y2d : NULL};
            mu_objects_step(&objects, &in);
        }
        mu_objects_apply_lights(&objects, w);
    }
    if (!a->legacy)
        for (int i = 0; i < a->light_count; ++i) {
            const float *l = a->lights[i];
            const float rgb[3] = {l[2], l[3], l[4]};
            mu_world_add_light(w, l[0], l[1], rgb, (int32_t)l[5]);
        }
    if (a->legacy) {
        w->detail = 0;
        status = mu_world_draw_raster(w, &raster, a->box[0], a->box[1], a->box[2], a->box[3], &stats);
    } else if (a->have_frustum)
        status = mu_world_draw_raster_view(w, &raster, &frustum, 5, a->top_view, &stats);
    else
        status = mu_world_draw_raster(w, &raster, a->box[0], a->box[1], a->box[2], a->box[3], &stats);
    long decal_fans = 0;
    if (!a->legacy)
        for (int i = 0; i < a->decal_count; ++i) {
            const float *d = a->decals[i];
            static const float white[3] = {1.0f, 1.0f, 1.0f};
            decal_fans += mu_world_decal_raster(w, &raster, 0x7ef7, d[0], d[1], d[2], d[2], white, d[3], 1.0f, 5.0f,
                                                1, 0, MU_TERRAIN_STATE_ADDITIVE);
        }
    long objects_drawn = 0;
    if (objects_loaded)
        objects_drawn = objects.rt.ready ? mu_objects_draw_raster(&objects, w, &raster, 0, 0, 255, 255)
                                         : draw_objects(&objects, w, &raster);
    if (objects_loaded && objects.rt.ready && a->light_report)   /* NATIVE-LIGHT-001 */
        mu_objects_light_report(&objects, w, 6, stdout);
    char hash[65];
    mu_sha256_hex(raster.color, (uint64_t)a->width * (uint64_t)a->height * 4, hash);
    int failed = a->out && mu_png_write(a->out, raster.color, a->width, a->height);
    printf("{\"sha256\": \"%s\", \"status\": %d, \"faces\": %ld, \"alpha_faces\": %ld, \"grass\": %ld, "
           "\"skipped\": %ld, \"unsupported\": %ld, \"missing_texture_binds\": %ld, \"triangles\": %ld, "
           "\"fragments\": %ld, \"lights\": %d, \"decal_fans\": %ld, \"frame_counter\": %d",
           hash, status, stats.tiles.faces, stats.tiles.alpha_faces, stats.tiles.grass, stats.tiles.skipped,
           stats.tiles.unsupported, stats.missing_texture_binds, raster.triangles, raster.fragments,
           a->legacy ? 0 : a->light_count, decal_fans, w->frame_counter);
    if (frustum_status >= 0)
        printf(", \"frustum_status\": %d, \"frustum_box\": [%d, %d, %d, %d], \"frustum_2d\": [%.3f, %.3f, %.3f, "
               "%.3f, %.3f, %.3f, %.3f, %.3f]",
               frustum_status, frustum.x_min, frustum.y_min, frustum.x_max, frustum.y_max, (double)frustum.x2d[0],
               (double)frustum.y2d[0], (double)frustum.x2d[1], (double)frustum.y2d[1], (double)frustum.x2d[2],
               (double)frustum.y2d[2], (double)frustum.x2d[3], (double)frustum.y2d[3]);
    if (a->objects) {
        printf(", ");
        objects_json(stdout, &objects, object_error, objects_drawn);
        mu_objects_free(&objects);
    }
    printf("}\n");
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
        fprintf(stderr, "usage: mu-terrain info|render|export|scan|objects ROOT [--world N] [options]\n"
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
    if (!strcmp(a.command, "objects"))
        return command_objects(&a);
    fprintf(stderr, "unknown command %s\n", a.command);
    return 2;
}
