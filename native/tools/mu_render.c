#include "../data/manifest.h"
/* mu-render: headless front end of the native viewer core.
 *
 *   mu-render info    MODEL                 JSON summary of the checked model
 *   mu-render dump    MODEL --out FILE ...  bone matrices and transform outputs after
 *                                           the requested ticks/pose (golden-data tests)
 *   mu-render corners MODEL --out FILE ...  the literal GL call stream of the body/mesh-draw
 *                                           port (--case-out FILE also writes its inputs)
 *   mu-render replay  CASE --out FILE      run a mesh-draw case file through the port
 *                                           (--tables-out FILE: tables each mesh draw wrote)
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
 *   mu-render actor --type CLASS | --monster TYPE | --npc INDEX --action A --time T --out PNG
 *                                           animated monster/NPC (client action speeds, SetAction,
 *                                           animation step); --frames N --strip PNG --gif GIF
 */
#define _POSIX_C_SOURCE 200809L /* lstat, opendir, strdup with -std=c11 on glibc */
#include <dirent.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#include "../core/mu_actor.h"
#include "mu_render_world.h"
#include "../core/mu_bmd.h"
#include "../core/mu_camera.h"
#include "../core/mu_character.h"
#include "../core/mu_gif.h"
#include "../core/mu_hud_tip.h"
#include "../core/mu_item_textures.h"
#include "../core/mu_meshdraw_case.h"
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
    printf("], \"strict_anomalies\": %d, \"anomalies\": [", bmd.strict_anomalies);
    for (int32_t i = 0; i < bmd.anomaly_count; ++i) {
        const mu_bmd_anomaly *x = &bmd.anomalies[i];
        printf("%s{\"kind\": \"%s\", \"strict\": %d, \"a\": %d, \"b\": %d, \"c\": %d, \"value\": %d, \"offset\": ",
               i ? ", " : "", mu_bmd_anomaly_name(x->kind), x->strict, x->a, x->b, x->c, x->value);
        if (x->offset == UINT32_MAX)
            printf("null}");
        else
            printf("%u}", x->offset);
    }
    printf("], \"unresolved_bones\": [");
    for (int32_t i = 0, first = 1; i < bmd.bone_count; ++i)
        if (bmd.bones[i].unresolved) {
            printf("%s%d", first ? "" : ", ", i);
            first = 0;
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

/* Recorder: the literal GL call stream (u32 op, u32 words[4] per call). */
typedef struct recorder {
    FILE *file;
    uint32_t count;
} recorder;

static void record_call(void *context, uint32_t op, const uint32_t w[4])
{
    recorder *r = context;
    put_u32(r->file, op);
    for (int k = 0; k < 4; ++k)
        put_u32(r->file, w[k]);
    r->count++;
}

static void ignore_tc(void *c, float s, float t) { (void)c; (void)s; (void)t; }
static void ignore_c3(void *c, const float v[3]) { (void)c; (void)v; }
static void ignore_c4(void *c, float r, float g, float b, float a) { (void)c; (void)r; (void)g; (void)b; (void)a; }
static void ignore_v(void *c, const float v[3]) { (void)c; (void)v; }

static void load_textures(const mu_options *o, const mu_bmd *bmd, mu_textures *textures)
{
    memset(textures, 0, sizeof *textures);
    if (o->no_textures)
        return;
    char directory[4096];
    if (o->texture_dir)
        snprintf(directory, sizeof directory, "%s", o->texture_dir);
    else
        mu_path_directory(o->model_path, directory, sizeof directory);
    mu_textures_load(textures, bmd, directory);
}

static int write_case(const char *path, const mu_model *model, const mu_draw_options *draw)
{
    mu_scene_inputs in;
    if (mu_scene_inputs_build(model, draw, &in))
        return 1;
    mu_meshdraw_call call = {0, in.skip, in.args};
    FILE *f = fopen(path, "wb");
    int status = !f || mu_meshdraw_case_write(f, &in.globals, &in.cache, &in.model, in.bitmaps, in.bitmap_index,
                                              in.bitmap_count, &call, 1);
    if (f)
        fclose(f);
    mu_scene_inputs_free(&in);
    return status;
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
    mu_textures textures;
    load_textures(o, &bmd, &textures);
    mu_draw_options draw = o->draw;
    draw.textures = o->no_textures ? NULL : &textures;
    if (o->case_output && write_case(o->case_output, &model, &draw)) {
        fprintf(stderr, "cannot write case\n");
        return 1;
    }
    recorder r = {o->output ? fopen(o->output, "wb") : NULL, 0};
    if (!r.file) {
        fprintf(stderr, "cannot open output\n");
        return 1;
    }
    mu_gl_sink sink = {&r, record_call};
    mu_render_backend backend;
    memset(&backend, 0, sizeof backend);
    backend.sink = (mu_meshdraw_sink){NULL, ignore_tc, ignore_c3, ignore_c4, ignore_v};
    backend.gl = &sink;
    mu_draw_stats stats = {0, 0, 0, 0};
    mu_scene_draw_model(&model, &draw, &backend, &stats);
    fclose(r.file);
    printf("{\"records\": %u, \"meshes\": %ld, \"corners\": %ld, \"refused\": %ld, \"faulted\": %ld, "
           "\"textures_missing\": %d}\n", r.count, stats.meshes, stats.corners, stats.refused, stats.faulted,
           textures.missing);
    mu_textures_free(&textures);
    mu_model_free(&model);
    mu_bmd_free(&bmd);
    return 0;
}

/* replay CASE --out STREAM [--tables-out FILE]: run a case file through the port. */
typedef struct table_writer { FILE *file; } table_writer;
static void write_tables(void *context, int32_t mesh, int32_t light_count, const float *light, int32_t texcoord_count,
                         const float *texcoords)
{
    table_writer *t = context;
    if (!t->file)
        return;
    put_u32(t->file, (uint32_t)mesh);
    put_u32(t->file, (uint32_t)light_count);
    fwrite(light, 4, 3 * (size_t)light_count, t->file);
    put_u32(t->file, (uint32_t)texcoord_count);
    fwrite(texcoords, 4, 2 * (size_t)texcoord_count, t->file);
}

static int command_replay(const mu_options *o)
{
    FILE *f = fopen(o->model_path, "rb");
    if (!f) {
        fprintf(stderr, "cannot open case\n");
        return 1;
    }
    fseek(f, 0, SEEK_END);
    long size = ftell(f);
    fseek(f, 0, SEEK_SET);
    uint8_t *data = malloc(size > 0 ? (size_t)size : 1);
    if (!data || size <= 0 || fread(data, 1, (size_t)size, f) != (size_t)size) {
        fclose(f);
        free(data);
        fprintf(stderr, "cannot read case\n");
        return 1;
    }
    fclose(f);
    mu_meshdraw_case c;
    int bad = mu_meshdraw_case_read(data, (size_t)size, &c);
    free(data);
    if (bad) {
        fprintf(stderr, "malformed case\n");
        return 1;
    }
    recorder r = {o->output ? fopen(o->output, "wb") : NULL, 0};
    if (!r.file) {
        fprintf(stderr, "cannot open output\n");
        mu_meshdraw_case_free(&c);
        return 1;
    }
    table_writer tables = {o->tables_output ? fopen(o->tables_output, "wb") : NULL};
    float *colours = malloc(sizeof(float) * 3 * MU_MESHDRAW_MAX_ENTRIES);
    float *table = malloc(sizeof(float) * 2 * (MU_MESHDRAW_MAX_ENTRIES + 1));
    mu_meshdraw_scratch scratch = {colours, table, &tables, write_tables};
    mu_gl_sink sink = {&r, record_call};
    mu_meshdraw_counts counts = {0, 0, 0, 0, 0};
    const int faulted = mu_meshdraw_case_run(&c, &sink, &scratch, &counts) == MU_MESHDRAW_FAULT;
    /* A fault record (op 0x102), then the final caches and model colour as one
     * trailing record each (ops 0x100, 0x101). */
    if (faulted) {
        const uint32_t none[4] = {0, 0, 0, 0};
        record_call(&r, 0x102, none);
    }
    uint32_t cache[4] = {(uint32_t)c.cache.depth_test | (uint32_t)c.cache.cull << 8 | (uint32_t)c.cache.depth_mask << 16 |
                             (uint32_t)c.cache.alpha_test << 24,
                         (uint32_t)c.cache.texture | (uint32_t)c.cache.fog << 8, (uint32_t)c.cache.blend,
                         (uint32_t)c.cache.bound};
    record_call(&r, 0x100, cache);
    uint32_t colour[4] = {0, 0, 0, 0};
    memcpy(colour, c.model.color, 12);
    record_call(&r, 0x101, colour);
    fclose(r.file);
    if (tables.file)
        fclose(tables.file);
    free(colours);
    free(table);
    printf("{\"records\": %u, \"drawn\": %ld, \"returned\": %ld, \"refused\": %ld, \"faulted\": %ld, "
           "\"corners\": %ld}\n", r.count, counts.drawn, counts.returned, counts.refused, counts.faulted, counts.corners);
    mu_meshdraw_case_free(&c);
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
    load_textures(o, &bmd, &textures);
    mu_raster raster;
    if (mu_raster_init(&raster, o->width, o->height)) {
        fprintf(stderr, "bad image size\n");
        return 1;
    }
    raster.linear = o->linear;
    raster.texture_filter = textures.filter;
    raster.texture_wrap = textures.wrap;
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
    mu_draw_options draw = o->draw;
    draw.textures = o->no_textures ? NULL : &textures;
    mu_draw_stats stats = {0, 0, 0, 0};
    mu_scene_draw_model(&model, &draw, &backend, &stats);
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
                                     {&state, null_tc, null_c3, null_c4, null_v}, NULL};
        mu_draw_options options;
        mu_draw_default_options(&options);
        mu_draw_stats stats = {0, 0, 0, 0};
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

/* Writes the frames side by side (--strip) and as an animated GIF (--gif). */
static int write_animation(const mu_options *o, const uint8_t *frames)
{
    int status = 0;
    size_t frame_bytes = (size_t)o->width * (size_t)o->height * 4;
    if (o->strip_path) {
        int32_t strip_width = o->width * o->frames;
        uint8_t *strip = malloc(frame_bytes * (size_t)o->frames);
        if (!strip)
            return 1;
        for (int32_t y = 0; y < o->height; ++y)
            for (int32_t n = 0; n < o->frames; ++n)
                memcpy(strip + ((size_t)y * (size_t)strip_width + (size_t)n * (size_t)o->width) * 4,
                       frames + frame_bytes * (size_t)n + (size_t)y * (size_t)o->width * 4, (size_t)o->width * 4);
        if (mu_png_write(o->strip_path, strip, strip_width, o->height)) {
            fprintf(stderr, "cannot write %s\n", o->strip_path);
            status = 1;
        }
        free(strip);
    }
    if (o->gif_path && mu_gif_write(o->gif_path, frames, o->width, o->height, o->frames, 4 * o->frame_steps)) {
        fprintf(stderr, "cannot write %s\n", o->gif_path);
        status = 1;
    }
    return status;
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
    /* RENDER-ITEMS-TEX-002: with a game root, each item takes the client's item texture rule (its type from the
     * record that names the file, or the class part file name) and the parts the class's skin index (+0xa4). */
    if (o->game_root && !o->no_textures) {
        mu_hud_tip_tables tables;
        mu_hud_tip_tables_load(o->game_root, &tables);
        const mu_data_table *items = tables.have_items ? &tables.items : NULL;
        for (int i = 0; i < MU_CHARACTER_ITEMS; ++i)
            if (c.items[i].loaded)
                mu_item_textures_character(&c, i, items, o->game_root,
                                           mu_item_textures_type_of_path(items, o->game_root, c.items[i].path),
                                           o->class_byte);
        mu_hud_tip_tables_free(&tables);
    }
    mu_raster raster;
    if (mu_raster_init(&raster, o->width, o->height)) {
        fprintf(stderr, "bad image size\n");
        return 1;
    }
    raster.linear = o->linear;
    raster.front_ccw = !o->front_cw;
    mu_camera camera;
    mu_options_character_camera(o, &c, &camera);
    mu_camera_view(&camera, raster.view);
    mu_camera_projection(&camera, (float)o->width / (float)o->height, raster.projection);
    size_t frame_bytes = (size_t)o->width * (size_t)o->height * 4;
    uint8_t *frames = malloc(frame_bytes * (size_t)o->frames);
    if (!frames) {
        mu_raster_free(&raster);
        mu_character_free(&c);
        return 1;
    }
    float speed = mu_character_action_speed(&c, mu_model_action(&c.player));
    if (o->player_action < 0)
        speed = o->speed;
    mu_draw_stats stats = {0, 0, 0, 0};
    int missing = 0, items = 0;
    char hash[65] = "";
    for (int32_t n = 0; n < o->frames; ++n) {
        if (n) {
            /* Further frames (--frames): advance the Player animation, then pose and skin again. */
            for (int32_t step = 0; step < o->frame_steps; ++step)
                mu_character_tick(&c, speed, NULL);
            if (mu_character_update(&c) != MU_MODEL_OK) {
                fprintf(stderr, "character update failed\n");
                break;
            }
        }
        mu_raster_clear(&raster, o->background);
        mu_render_backend backend;
        mu_raster_backend(&raster, &backend);
        missing = items = 0;
        /* Client order: body parts 5..0, weapons 0 and 1, wing. */
        static const int order[MU_CHARACTER_ITEMS] = {5, 4, 3, 2, 1, 0, 6, 7, 8};
        for (int k = 0; k < MU_CHARACTER_ITEMS; ++k) {
            const mu_character_item *item = &c.items[order[k]];
            if (!item->loaded)
                continue;
            raster.textures = item->textures.slots;
            raster.texture_count = item->textures.count;
            raster.texture_filter = item->textures.filter;
            raster.texture_wrap = item->textures.wrap;
            mu_draw_options draw = o->draw;   /* the item's bitmap records (GL names, component counts) */
            draw.textures = o->no_textures ? NULL : &item->textures;
            mu_scene_draw_model(&item->model, &draw, &backend, &stats);
            missing += item->textures.missing;
            items++;
        }
        memcpy(frames + frame_bytes * (size_t)n, raster.color, frame_bytes);
        if (n == 0)
            mu_sha256_hex(raster.color, frame_bytes, hash);
    }
    int status = 0;
    if (o->output && mu_png_write(o->output, frames, o->width, o->height)) {
        fprintf(stderr, "cannot write %s\n", o->output);
        status = 1;
    }
    status |= write_animation(o, frames);
    printf("{\"sha256\": \"%s\", \"width\": %d, \"height\": %d, \"items\": %d, \"meshes\": %ld, \"corners\": %ld,"
           " \"refused\": %ld, \"triangles\": %ld, \"textures_missing\": %d, \"action\": %u, \"speed\": %.9g,"
           " \"frame\": %.9g}\n",
           hash, o->width, o->height, items, stats.meshes, stats.corners, stats.refused, raster.triangles, missing,
           mu_model_action(&c.player), (double)speed, (double)mu_model_frame(&c.player));
    free(frames);
    mu_raster_free(&raster);
    mu_character_free(&c);
    return status;
}

static int command_actor(const mu_options *o)
{
    static mu_actor actor;
    char error[1024];
    const char *root = o->game_root ? o->game_root : getenv("MU_GAME_ROOT");
    mu_actor_spec spec;
    if (!o->actor_by) {
        fprintf(stderr, "actor needs --type CLASS, --monster TYPE or --npc INDEX\n");
        return 2;
    }
    if (mu_actor_resolve(root, o->actor_by, o->actor_id, &spec, error, sizeof error)) {
        fprintf(stderr, "%s\n", error);
        return 1;
    }
    if (o->scale_set)
        spec.scale = o->params.body_scale;
    if (mu_actor_load(&actor, &spec, &o->params, o->no_textures, error, sizeof error)) {
        fprintf(stderr, "%s: %s\n", spec.path, error);
        return 1;
    }
    mu_actor_set_action(&actor, o->action);
    int32_t steps = (int32_t)(o->time / 0.04f + 0.5f);
    uint8_t loop = 1;
    for (int32_t step = 0; step < steps; ++step)
        mu_actor_step(&actor, &loop);
    mu_raster raster;
    if (mu_raster_init(&raster, o->width, o->height)) {
        fprintf(stderr, "bad image size\n");
        mu_actor_free(&actor);
        return 1;
    }
    raster.linear = o->linear;
    raster.front_ccw = !o->front_cw;
    raster.textures = actor.textures.slots;
    raster.texture_count = actor.textures.count;
    raster.texture_filter = actor.textures.filter;
    raster.texture_wrap = actor.textures.wrap;
    mu_draw_options draw = o->draw;   /* the actor's bitmap records (GL names, component counts) */
    draw.textures = o->no_textures ? NULL : &actor.textures;
    size_t frame_bytes = (size_t)o->width * (size_t)o->height * 4;
    uint8_t *frames = malloc(frame_bytes * (size_t)o->frames);
    if (!frames) {
        mu_raster_free(&raster);
        mu_actor_free(&actor);
        return 1;
    }
    mu_camera camera;
    mu_draw_stats stats = {0, 0, 0, 0};
    char hash[65] = "";
    float first_frame = 0.0f;
    for (int32_t n = 0; n < o->frames; ++n) {
        if (n)
            for (int32_t step = 0; step < o->frame_steps; ++step)
                mu_actor_step(&actor, &loop);
        if (mu_actor_update(&actor)) {
            fprintf(stderr, "pose/skin failed\n");
            free(frames);
            mu_raster_free(&raster);
            mu_actor_free(&actor);
            return 1;
        }
        if (n == 0) {
            first_frame = mu_actor_frame(&actor);
            mu_options_camera(o, &actor.model, &camera);   /* framed once, on the first frame */
            mu_camera_view(&camera, raster.view);
            mu_camera_projection(&camera, (float)o->width / (float)o->height, raster.projection);
        }
        mu_raster_clear(&raster, o->background);
        mu_render_backend backend;
        mu_raster_backend(&raster, &backend);
        mu_scene_draw_model(&actor.model, &draw, &backend, &stats);
        memcpy(frames + frame_bytes * (size_t)n, raster.color, frame_bytes);
        if (n == 0)
            mu_sha256_hex(raster.color, frame_bytes, hash);
    }
    int status = 0;
    if (o->output && mu_png_write(o->output, frames, o->width, o->height)) {
        fprintf(stderr, "cannot write %s\n", o->output);
        status = 1;
    }
    status |= write_animation(o, frames);
    printf("{\"file\": ");
    json_string(stdout, spec.path);
    printf(", \"server_class\": %d, \"monster_type\": %d, \"npc_index\": %d, \"model_index\": %d, \"scale\": %.9g,"
           " \"actions\": %d, \"action\": %u, \"action_speed\": %.9g, \"action_loop\": %d, \"unset_actions\": %u,"
           " \"open_status\": %d, \"steps\": %d, \"first_frame\": %.9g, \"last_frame\": %.9g, \"last_speed\": %.9g,"
           " \"loop\": %u, \"frames\": %d, \"sha256_first\": \"%s\", \"meshes\": %ld, \"textures_missing\": %d}\n",
           spec.server_class, spec.monster_type, spec.npc_index, spec.model_index, (double)spec.scale,
           mu_actor_action_count(&actor), mu_actor_action(&actor),
           (double)mu_actor_action_speed(&actor, mu_actor_action(&actor)),
           mu_actor_action_loop(&actor, mu_actor_action(&actor)), actor.unset_actions, actor.open_status, steps,
           (double)first_frame, (double)mu_actor_frame(&actor), (double)actor.last_speed, loop, o->frames, hash,
           stats.meshes, actor.textures.missing);
    free(frames);
    mu_raster_free(&raster);
    mu_actor_free(&actor);
    return status;
}

int mu_render_ui_main(int argc, char **argv);
int mu_charsel_tool_main(int argc, char **argv);

int main(int argc, char **argv)
{
    if (!mu_native_data_check_args(argc, argv)) return 1;
    if (argc >= 2 && !strcmp(argv[1], "ui"))
        return mu_render_ui_main(argc, argv);
    if (argc >= 2 && !strcmp(argv[1], "charsel"))   /* NATIVE-CHARSEL-001, headless software scene */
        return mu_charsel_tool_main(argc - 1, argv + 1);
    if (argc < 2) {
        fprintf(stderr, "usage: %s info|dump|corners|replay|render|image|scan|character|chardump|actor MODEL|CASE|ROOT [options]\n"
                        "       %s ui title|text ... (see mu-render ui)\n"
                        "       %s charsel --game-root ROOT ... (character-select scene)\n",
                argv[0], argv[0], argv[0]);
        mu_options_usage(argv[0]);
        return 2;
    }
    if (mu_record_math_environment_supported() != 1) {
        fprintf(stderr, "host floating-point environment unsupported by record-math\n");
        return 2;
    }
    if (mu_render_world_args(&argc, argv))   /* NATIVE-RENDERCHAR-001 world-mode options */
        return 2;
    mu_options o;
    mu_options_defaults(&o);
    if (mu_options_parse(&o, argc, argv, 2)) {
        mu_options_usage(argv[0]);
        return 2;
    }
    const char *command = argv[1];
    if (!o.model_path && strcmp(command, "character") && strcmp(command, "chardump") && strcmp(command, "actor")) {
        fprintf(stderr, "%s needs MODEL or ROOT\n", command);
        return 2;
    }
    if (!strcmp(command, "info"))
        return command_info(&o);
    if (!strcmp(command, "dump"))
        return command_dump(&o);
    if (!strcmp(command, "corners"))
        return command_corners(&o);
    if (!strcmp(command, "replay"))
        return command_replay(&o);
    if (!strcmp(command, "render"))
        return command_render(&o);
    if (!strcmp(command, "image"))
        return command_image(&o);
    if (!strcmp(command, "scan"))
        return command_scan(&o);
    if (!strcmp(command, "character"))
        return mu_render_world_active() ? mu_render_world_character(&o) : command_character(&o);
    if (!strcmp(command, "chardump"))
        return command_chardump(&o);
    if (!strcmp(command, "actor"))
        return mu_render_world_active() ? mu_render_world_actor(&o) : command_actor(&o);
    fprintf(stderr, "unknown command %s\n", command);
    return 2;
}
