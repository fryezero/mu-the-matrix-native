/* mu-render: headless front end of the native viewer core.
 *
 *   mu-render info    MODEL                 JSON summary of the checked model
 *   mu-render dump    MODEL --out FILE ...  bone matrices and transform outputs after
 *                                           the requested ticks/pose (golden-data tests)
 *   mu-render corners MODEL --out FILE ...  the GL-shaped call stream of every mesh
 *                                           (mesh-draw equivalence tests)
 *   mu-render render  MODEL --out PNG ...   software-rasterized frame; prints the
 *                                           SHA-256 of the raw RGBA pixels
 *   mu-render image   FILE --out RAW        decode a wrapped/plain texture to 8-byte header
 *                                           (width, height) + RGBA8 rows, top row first
 *   mu-render scan    ROOT                  load/animate/skin/draw every *.bmd under ROOT
 *                                           and print per-version counts (read-only)
 *   mu-render character [PLAYER] --out PNG  software-rendered assembled character (Player.bmd
 *                                           skeleton, class parts, weapons, wing); see --class
 *   mu-render chardump  [PLAYER] --out FILE shared Player bones, item bones and every part/item
 *                                           transform output (character golden tests)
 */
#define _POSIX_C_SOURCE 200809L /* lstat, opendir, strdup with -std=c11 on glibc */
#include <dirent.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

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

static void json_string(FILE *f, const char *s)
{
    fputc('"', f);
    for (; *s; ++s) {
        unsigned char c = (unsigned char)*s;
        if (c == '"' || c == '\\')
            fprintf(f, "\\%c", c);
        else if (c < 0x20 || c >= 0x7f)
            fprintf(f, "\\u%04x", c);
        else
            fputc(c, f);
    }
    fputc('"', f);
}

static int load(const mu_options *o, mu_bmd *bmd, mu_model *model)
{
    char error[512];
    if (!o->model_path) {
        fprintf(stderr, "no model given\n");
        return 1;
    }
    if (mu_bmd_load_file(o->model_path, bmd, error, sizeof error) != MU_BMD_OK) {
        fprintf(stderr, "%s: %s\n", o->model_path, error);
        return 1;
    }
    if (model && mu_model_init(model, bmd, &o->params, error, sizeof error) != MU_MODEL_OK) {
        fprintf(stderr, "%s: %s\n", o->model_path, error);
        mu_bmd_free(bmd);
        return 1;
    }
    return 0;
}

static int command_info(const mu_options *o)
{
    mu_bmd bmd;
    if (load(o, &bmd, NULL))
        return 1;
    printf("{\"version\": %d, \"name\": ", bmd.version);
    json_string(stdout, bmd.name);
    printf(", \"meshes\": %d, \"bones\": %d, \"actions\": %d, \"payload_bytes\": %u, \"parsed_bytes\": %u,"
           " \"bone_stream\": %u, \"keys\": [", bmd.mesh_count, bmd.bone_count, bmd.action_count, bmd.payload_size,
           bmd.parsed_size, bmd.bone_stream);
    for (int32_t a = 0; a < bmd.action_count; ++a)
        printf("%s%d", a ? ", " : "", bmd.actions[a].keys);
    printf("], \"locks\": [");
    for (int32_t a = 0; a < bmd.action_count; ++a)
        printf("%s%d", a ? ", " : "", bmd.actions[a].lock_positions);
    printf("], \"mesh_list\": [");
    for (int32_t i = 0; i < bmd.mesh_count; ++i) {
        const mu_bmd_mesh *m = &bmd.meshes[i];
        printf("%s{\"vertices\": %d, \"normals\": %d, \"uvs\": %d, \"polygons\": %d, \"texture_index\": %d, \"texture\": ",
               i ? ", " : "", m->vertex_count, m->normal_count, m->uv_count, m->polygon_count, m->texture_index);
        json_string(stdout, m->texture);
        printf("}");
    }
    printf("]}\n");
    mu_bmd_free(&bmd);
    return 0;
}

static void put_u32(FILE *f, uint32_t v)
{
    uint8_t b[4] = {(uint8_t)v, (uint8_t)(v >> 8), (uint8_t)(v >> 16), (uint8_t)(v >> 24)};
    fwrite(b, 1, 4, f);
}

static int command_dump(const mu_options *o)
{
    mu_bmd bmd;
    mu_model model;
    if (load(o, &bmd, &model))
        return 1;
    uint8_t loop = 1;
    int status = mu_options_animate(o, &model, &loop);
    if (status != MU_MODEL_OK) {
        fprintf(stderr, "animation failed\n");
        mu_model_free(&model);
        mu_bmd_free(&bmd);
        return 1;
    }
    FILE *f = o->output ? fopen(o->output, "wb") : NULL;
    if (!f) {
        fprintf(stderr, "cannot open output\n");
        mu_model_free(&model);
        mu_bmd_free(&bmd);
        return 1;
    }
    fwrite("MUVD", 1, 4, f);
    put_u32(f, 1);
    put_u32(f, (uint32_t)bmd.bone_count);
    put_u32(f, (uint32_t)bmd.mesh_count);
    fwrite(mu_model_bone_matrices(&model), 0x30, (size_t)bmd.bone_count, f);
    for (int32_t i = 0; i < bmd.mesh_count; ++i) {
        uint32_t nv = (uint32_t)bmd.meshes[i].vertex_count, nn = (uint32_t)bmd.meshes[i].normal_count;
        put_u32(f, nv);
        put_u32(f, nn);
        fwrite(mu_model_vertices(&model, i), 12, nv, f);
        fwrite(mu_model_normals(&model, i), 12, nn, f);
        fwrite(mu_model_lights(&model, i), 4, nn, f);
        fwrite(mu_model_secondary_lights(&model, i), 4, nn, f);
    }
    fwrite(mu_model_box(&model), 4, 12, f);
    fclose(f);
    printf("{\"frame\": %.9g, \"prior_frame\": %.9g, \"prior_action\": %u, \"action\": %u, \"loop\": %u, \"posed\": %d}\n",
           (double)mu_model_frame(&model), (double)mu_model_prior_frame(&model), mu_model_prior_action(&model),
           mu_model_action(&model), loop, model.posed);
    mu_model_free(&model);
    mu_bmd_free(&bmd);
    return 0;
}

/* Recorder backend: op stream of everything the scene driver emits. */
typedef struct recorder {
    FILE *file;
    uint32_t mesh, count;
} recorder;

enum { OP_TEXCOORD = 1, OP_COLOR3 = 2, OP_COLOR4 = 3, OP_VERTEX = 4, OP_BEGIN = 5, OP_END = 6, OP_PREPARE = 7 };

static void record(recorder *r, uint32_t op, float a, float b, float c, float d)
{
    float values[4] = {a, b, c, d};
    put_u32(r->file, r->mesh);
    put_u32(r->file, op);
    fwrite(values, 4, 4, r->file);
    r->count++;
}

static void rec_prepare(void *context, const mu_meshdraw_state *s, int32_t mesh)
{
    recorder *r = context;
    r->mesh = (uint32_t)mesh;
    uint32_t packed = (uint32_t)s->blend | (uint32_t)s->depth_test << 1 | (uint32_t)s->depth_mask << 2 |
                      (uint32_t)s->cull << 3 | (uint32_t)s->alpha_test << 4 | (uint32_t)s->texture << 5 |
                      (uint32_t)s->src << 8 | (uint32_t)s->dst << 12;
    record(r, OP_PREPARE, (float)packed, 0, 0, 0);
}
static void rec_begin(void *context) { record(context, OP_BEGIN, 0, 0, 0, 0); }
static void rec_end(void *context) { record(context, OP_END, 0, 0, 0, 0); }
static void rec_texcoord(void *context, float s, float t) { record(context, OP_TEXCOORD, s, t, 0, 0); }
static void rec_color3(void *context, const float c[3]) { record(context, OP_COLOR3, c[0], c[1], c[2], 0); }
static void rec_color4(void *context, float r, float g, float b, float a) { record(context, OP_COLOR4, r, g, b, a); }
static void rec_vertex(void *context, const float v[3]) { record(context, OP_VERTEX, v[0], v[1], v[2], 0); }

static void recorder_backend(recorder *r, mu_render_backend *b)
{
    memset(b, 0, sizeof *b);
    b->context = r;
    b->prepare = rec_prepare;
    b->begin = rec_begin;
    b->end = rec_end;
    b->sink.context = r;
    b->sink.texcoord = rec_texcoord;
    b->sink.color3 = rec_color3;
    b->sink.color4 = rec_color4;
    b->sink.vertex = rec_vertex;
}

static int command_corners(const mu_options *o)
{
    mu_bmd bmd;
    mu_model model;
    if (load(o, &bmd, &model))
        return 1;
    if (mu_options_animate(o, &model, NULL) != MU_MODEL_OK) {
        fprintf(stderr, "animation failed\n");
        return 1;
    }
    recorder r = {o->output ? fopen(o->output, "wb") : NULL, 0, 0};
    if (!r.file) {
        fprintf(stderr, "cannot open output\n");
        return 1;
    }
    mu_render_backend backend;
    recorder_backend(&r, &backend);
    mu_draw_stats stats = {0, 0, 0};
    mu_scene_draw_model(&model, &o->draw, &backend, &stats);
    fclose(r.file);
    printf("{\"records\": %u, \"meshes\": %ld, \"corners\": %ld, \"refused\": %ld}\n", r.count, stats.meshes,
           stats.corners, stats.refused);
    mu_model_free(&model);
    mu_bmd_free(&bmd);
    return 0;
}

static int command_render(const mu_options *o)
{
    mu_bmd bmd;
    mu_model model;
    if (load(o, &bmd, &model))
        return 1;
    if (mu_options_animate(o, &model, NULL) != MU_MODEL_OK) {
        fprintf(stderr, "animation failed\n");
        return 1;
    }
    mu_textures textures;
    memset(&textures, 0, sizeof textures);
    if (!o->no_textures) {
        char directory[4096];
        if (o->texture_dir)
            snprintf(directory, sizeof directory, "%s", o->texture_dir);
        else
            mu_path_directory(o->model_path, directory, sizeof directory);
        mu_textures_load(&textures, &bmd, directory);
    }
    mu_raster raster;
    if (mu_raster_init(&raster, o->width, o->height)) {
        fprintf(stderr, "bad image size\n");
        return 1;
    }
    raster.linear = !o->nearest;
    raster.front_ccw = !o->front_cw;
    raster.textures = textures.slots;
    raster.texture_count = textures.count;
    mu_camera camera;
    mu_options_camera(o, &model, &camera);
    mu_camera_view(&camera, raster.view);
    mu_camera_projection(&camera, (float)o->width / (float)o->height, raster.projection);
    mu_raster_clear(&raster, o->background);
    mu_render_backend backend;
    mu_raster_backend(&raster, &backend);
    mu_draw_stats stats = {0, 0, 0};
    mu_scene_draw_model(&model, &o->draw, &backend, &stats);
    char hash[65];
    mu_sha256_hex(raster.color, (uint64_t)o->width * (uint64_t)o->height * 4, hash);
    if (o->output && mu_png_write(o->output, raster.color, o->width, o->height)) {
        fprintf(stderr, "cannot write %s\n", o->output);
        return 1;
    }
    printf("{\"sha256\": \"%s\", \"width\": %d, \"height\": %d, \"meshes\": %ld, \"corners\": %ld, \"refused\": %ld,"
           " \"triangles\": %ld, \"fragments\": %ld, \"textures_missing\": %d}\n",
           hash, o->width, o->height, stats.meshes, stats.corners, stats.refused, raster.triangles, raster.fragments,
           textures.missing);
    mu_raster_free(&raster);
    mu_textures_free(&textures);
    mu_model_free(&model);
    mu_bmd_free(&bmd);
    return 0;
}

static int command_image(const mu_options *o)
{
    mu_image image;
    char error[256];
    if (mu_image_load_file(o->model_path, &image, error, sizeof error) != MU_IMAGE_OK) {
        fprintf(stderr, "%s: %s\n", o->model_path, error);
        return 1;
    }
    size_t size = (size_t)image.width * (size_t)image.height * 4;
    char hash[65];
    mu_sha256_hex(image.rgba, size, hash);
    if (o->output) {
        FILE *f = fopen(o->output, "wb");
        if (!f)
            return 1;
        put_u32(f, (uint32_t)image.width);
        put_u32(f, (uint32_t)image.height);
        fwrite(image.rgba, 1, size, f);
        fclose(f);
    }
    printf("{\"width\": %d, \"height\": %d, \"channels\": %d, \"sha256\": \"%s\", \"jpeg\": %d}\n", image.width,
           image.height, image.channels, hash, mu_image_have_jpeg());
    mu_image_free(&image);
    return 0;
}

/* ---- scan ---- */
typedef struct scan_counts {
    long files, loaded, rejected, init_failed, animated, posed, anim_failed, meshes, refused_meshes, corners;
    long four_corner, max_bones, max_meshes, max_entries, vertices;
} scan_counts;

typedef struct null_sink_state { long n; } null_sink_state;
static void null_prepare(void *c, const mu_meshdraw_state *s, int32_t m) { (void)c; (void)s; (void)m; }
static void null_begin(void *c) { (void)c; }
static void null_end(void *c) { (void)c; }
static void null_tc(void *c, float s, float t) { (void)c; (void)s; (void)t; }
static void null_c3(void *c, const float v[3]) { (void)c; (void)v; }
static void null_c4(void *c, float r, float g, float b, float a) { (void)c; (void)r; (void)g; (void)b; (void)a; }
static void null_v(void *c, const float v[3]) { (void)v; ((null_sink_state *)c)->n++; }

static void scan_file(const char *path, scan_counts counts[16], FILE *log)
{
    FILE *f = fopen(path, "rb");
    uint8_t header[4] = {0, 0, 0, 0};
    if (!f)
        return;
    size_t got = fread(header, 1, 4, f);
    fclose(f);
    if (got < 4 || memcmp(header, "BMD", 3) != 0)
        return;
    int slot = header[3] < 16 ? header[3] : 0;
    scan_counts *c = &counts[slot];
    c->files++;
    mu_bmd bmd;
    char error[512];
    if (mu_bmd_load_file(path, &bmd, error, sizeof error) != MU_BMD_OK) {
        c->rejected++;
        if (log)
            fprintf(log, "reject\t%d\t%s\t%s\n", header[3], path, error);
        return;
    }
    c->loaded++;
    if (bmd.bone_count > c->max_bones) c->max_bones = bmd.bone_count;
    if (bmd.mesh_count > c->max_meshes) c->max_meshes = bmd.mesh_count;
    for (int32_t i = 0; i < bmd.mesh_count; ++i) {
        const mu_bmd_mesh *m = &bmd.meshes[i];
        if (m->vertex_count > c->max_entries) c->max_entries = m->vertex_count;
        if (m->normal_count > c->max_entries) c->max_entries = m->normal_count;
        c->vertices += m->vertex_count;
        for (int32_t p = 0; p < m->polygon_count; ++p)
            c->four_corner += bmd.payload[m->polygon_offset + 64u * (uint32_t)p] == 4;
    }
    mu_model model;
    if (mu_model_init(&model, &bmd, NULL, error, sizeof error) != MU_MODEL_OK) {
        c->init_failed++;
        if (log)
            fprintf(log, "init\t%d\t%s\t%s\n", header[3], path, error);
        mu_bmd_free(&bmd);
        return;
    }
    /* Middle of the first action with keys, blended from frame 0, plus one tick. */
    int32_t action = 0;
    while (action < bmd.action_count && bmd.actions[action].keys <= 0)
        action++;
    if (action >= bmd.action_count)
        action = 0;
    float frame = bmd.action_count ? (float)bmd.actions[action].keys * 0.5f + 0.25f : 0.0f;
    mu_model_set_state(&model, (uint16_t)action, frame, 0.0f, (uint16_t)action);
    uint8_t loop;
    int ok = mu_model_tick(&model, 0.25f, &loop) == MU_MODEL_OK && mu_model_update(&model) == MU_MODEL_OK;
    if (!ok) {
        c->anim_failed++;
        if (log)
            fprintf(log, "animate\t%d\t%s\n", header[3], path);
    } else {
        c->animated++;
        c->posed += model.posed;
        null_sink_state state = {0};
        mu_render_backend backend = {&state, null_prepare, null_begin, null_end,
                                     {&state, null_tc, null_c3, null_c4, null_v}};
        mu_draw_options options;
        mu_draw_default_options(&options);
        mu_draw_stats stats = {0, 0, 0};
        mu_scene_draw_model(&model, &options, &backend, &stats);
        c->meshes += stats.meshes;
        c->refused_meshes += stats.refused;
        c->corners += stats.corners;
    }
    mu_model_free(&model);
    mu_bmd_free(&bmd);
}

static void scan_tree(const char *root, scan_counts counts[16], FILE *log)
{
    DIR *dir = opendir(root);
    if (!dir)
        return;
    struct dirent *entry;
    while ((entry = readdir(dir)) != NULL) {
        if (entry->d_name[0] == '.')
            continue;
        char path[4096];
        snprintf(path, sizeof path, "%s/%s", root, entry->d_name);
        struct stat info;
        if (lstat(path, &info) != 0)
            continue;
        if (S_ISDIR(info.st_mode)) {
            scan_tree(path, counts, log);
        } else if (S_ISREG(info.st_mode)) {
            size_t n = strlen(entry->d_name);
            if (n > 4 && (!strcmp(entry->d_name + n - 4, ".bmd") || !strcmp(entry->d_name + n - 4, ".BMD") ||
                          !strcmp(entry->d_name + n - 4, ".Bmd")))
                scan_file(path, counts, log);
        }
    }
    closedir(dir);
}

static int command_scan(const mu_options *o)
{
    scan_counts counts[16];
    memset(counts, 0, sizeof counts);
    FILE *log = o->output ? fopen(o->output, "w") : NULL;
    scan_tree(o->model_path, counts, log);
    if (log)
        fclose(log);
    printf("{");
    int first = 1;
    for (int v = 0; v < 16; ++v) {
        const scan_counts *c = &counts[v];
        if (!c->files)
            continue;
        printf("%s\"%d\": {\"files\": %ld, \"loaded\": %ld, \"rejected\": %ld, \"init_failed\": %ld, \"animated\": %ld,"
               " \"posed\": %ld, \"anim_failed\": %ld, \"meshes\": %ld, \"refused_meshes\": %ld, \"corners\": %ld,"
               " \"four_corner_polygons\": %ld, \"vertices\": %ld, \"max_bones\": %ld, \"max_meshes\": %ld,"
               " \"max_entries\": %ld}",
               first ? "" : ", ", v, c->files, c->loaded, c->rejected, c->init_failed, c->animated, c->posed,
               c->anim_failed, c->meshes, c->refused_meshes, c->corners, c->four_corner, c->vertices, c->max_bones,
               c->max_meshes, c->max_entries);
        first = 0;
    }
    printf("}\n");
    return 0;
}

/* ---- character ---- */
static void dump_meshes(FILE *f, const mu_bmd *bmd, const mu_model *model)
{
    for (int32_t i = 0; i < bmd->mesh_count; ++i) {
        uint32_t nv = (uint32_t)bmd->meshes[i].vertex_count, nn = (uint32_t)bmd->meshes[i].normal_count;
        put_u32(f, nv);
        put_u32(f, nn);
        fwrite(mu_model_vertices(model, i), 12, nv, f);
        fwrite(mu_model_normals(model, i), 12, nn, f);
        fwrite(mu_model_lights(model, i), 4, nn, f);
        fwrite(mu_model_secondary_lights(model, i), 4, nn, f);
    }
    fwrite(mu_model_box(model), 4, 12, f);
}

static int command_chardump(const mu_options *o)
{
    static mu_character c;
    char error[1024];
    if (mu_options_character(o, &c, error, sizeof error)) {
        fprintf(stderr, "%s\n", error);
        mu_character_free(&c);
        return 1;
    }
    FILE *f = o->output ? fopen(o->output, "wb") : NULL;
    if (!f) {
        fprintf(stderr, "cannot open output\n");
        mu_character_free(&c);
        return 1;
    }
    /* "MUCD", version, Player bone count, Player bones after its pose, then per
     * item slot 0..8: loaded flag, bone count and bones (weapons and wing:
     * their own matrices right after their pose; parts: 0), mesh count, the
     * MUVD-style mesh outputs and box. */
    fwrite("MUCD", 1, 4, f);
    put_u32(f, 1);
    put_u32(f, (uint32_t)c.player_bone_count);
    fwrite(c.player_bones, 0x30, (size_t)c.player_bone_count, f);
    for (int i = 0; i < MU_CHARACTER_ITEMS; ++i) {
        const mu_character_item *item = &c.items[i];
        put_u32(f, (uint32_t)item->loaded);
        if (!item->loaded)
            continue;
        uint32_t bones = item->bones ? (uint32_t)item->bmd.bone_count : 0;
        put_u32(f, bones);
        if (bones)
            fwrite(item->bones, 0x30, bones, f);
        put_u32(f, (uint32_t)item->bmd.mesh_count);
        dump_meshes(f, &item->bmd, &item->model);
    }
    fclose(f);
    printf("{\"frame\": %.9g, \"prior_frame\": %.9g, \"prior_action\": %u, \"action\": %u, \"posed\": %d, \"items\": [",
           (double)mu_model_frame(&c.player), (double)mu_model_prior_frame(&c.player),
           mu_model_prior_action(&c.player), mu_model_action(&c.player), c.player.posed);
    for (int i = 0; i < MU_CHARACTER_ITEMS; ++i) {
        printf("%s", i ? ", " : "");
        if (c.items[i].loaded)
            json_string(stdout, c.items[i].path);
        else
            printf("null");
    }
    printf("]}\n");
    mu_character_free(&c);
    return 0;
}

static int command_character(const mu_options *o)
{
    static mu_character c;
    char error[1024];
    if (mu_options_character(o, &c, error, sizeof error)) {
        fprintf(stderr, "%s\n", error);
        mu_character_free(&c);
        return 1;
    }
    mu_raster raster;
    if (mu_raster_init(&raster, o->width, o->height)) {
        fprintf(stderr, "bad image size\n");
        return 1;
    }
    raster.linear = !o->nearest;
    raster.front_ccw = !o->front_cw;
    mu_camera camera;
    mu_options_character_camera(o, &c, &camera);
    mu_camera_view(&camera, raster.view);
    mu_camera_projection(&camera, (float)o->width / (float)o->height, raster.projection);
    mu_raster_clear(&raster, o->background);
    mu_render_backend backend;
    mu_raster_backend(&raster, &backend);
    mu_draw_stats stats = {0, 0, 0};
    int missing = 0, items = 0;
    /* Client order: body parts 5..0, weapons 0 and 1, wing. */
    static const int order[MU_CHARACTER_ITEMS] = {5, 4, 3, 2, 1, 0, 6, 7, 8};
    for (int n = 0; n < MU_CHARACTER_ITEMS; ++n) {
        const mu_character_item *item = &c.items[order[n]];
        if (!item->loaded)
            continue;
        raster.textures = item->textures.slots;
        raster.texture_count = item->textures.count;
        mu_scene_draw_model(&item->model, &o->draw, &backend, &stats);
        missing += item->textures.missing;
        items++;
    }
    char hash[65];
    mu_sha256_hex(raster.color, (uint64_t)o->width * (uint64_t)o->height * 4, hash);
    if (o->output && mu_png_write(o->output, raster.color, o->width, o->height)) {
        fprintf(stderr, "cannot write %s\n", o->output);
        return 1;
    }
    printf("{\"sha256\": \"%s\", \"width\": %d, \"height\": %d, \"items\": %d, \"meshes\": %ld, \"corners\": %ld,"
           " \"refused\": %ld, \"triangles\": %ld, \"textures_missing\": %d}\n",
           hash, o->width, o->height, items, stats.meshes, stats.corners, stats.refused, raster.triangles, missing);
    mu_raster_free(&raster);
    mu_character_free(&c);
    return 0;
}

int main(int argc, char **argv)
{
    if (argc < 2) {
        fprintf(stderr, "usage: %s info|dump|corners|render|image|scan|character|chardump MODEL|ROOT [options]\n", argv[0]);
        mu_options_usage(argv[0]);
        return 2;
    }
    if (mu_record_math_environment_supported() != 1) {
        fprintf(stderr, "host floating-point environment unsupported by record-math\n");
        return 2;
    }
    mu_options o;
    mu_options_defaults(&o);
    if (mu_options_parse(&o, argc, argv, 2)) {
        mu_options_usage(argv[0]);
        return 2;
    }
    const char *command = argv[1];
    if (!strcmp(command, "info"))
        return command_info(&o);
    if (!strcmp(command, "dump"))
        return command_dump(&o);
    if (!strcmp(command, "corners"))
        return command_corners(&o);
    if (!strcmp(command, "render"))
        return command_render(&o);
    if (!strcmp(command, "image"))
        return command_image(&o);
    if (!strcmp(command, "scan"))
        return command_scan(&o);
    if (!strcmp(command, "character"))
        return command_character(&o);
    if (!strcmp(command, "chardump"))
        return command_chardump(&o);
    fprintf(stderr, "unknown command %s\n", command);
    return 2;
}
