/* World loading and rendering for the native viewer. See mu_terrain.h. */
#include "mu_terrain.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../../reconstructed/model-codec/model_codec.h"

/* model-recovery/modulus.cpp (Crypto++), linked as C. */
int mu_modulus_decrypt(const unsigned char *input, size_t length, unsigned char *output, size_t capacity,
                       size_t *written, char *error, size_t error_capacity);

static const uint8_t att_key[3] = {0xfc, 0xcf, 0xab};

int32_t mu_world_folder(int32_t w)
{
    if ((w >= 0x0b && w <= 0x11) || w == 0x34)   /* 0x009dacec */
        return 12;
    if ((w >= 0x18 && w <= 0x1d) || w == 0x24)   /* 0x009b0418 */
        return 25;
    if ((w >= 0x12 && w <= 0x17) || w == 0x35 || w == 0x61) /* 0x009dacb8 */
        return 19;
    if (w == 0x66)                               /* 0x009dad2c */
        return 0x67;
    if (w >= 0x52 && w <= 0x5a)                  /* 0x00e3068f (current world) */
        return 0x53;
    if (w >= 0x7b && w <= 0x7f)                  /* 0x00e1e4b6 */
        return 0x7c;
    return w + 1;
}

static int alpha_tile_world(int32_t w, int32_t index)
{
    switch (index) {
    case 2: return w == 0x33;
    case 3: return w == 0x27;
    case 9: return w == 0x5b || w == 0x5c;
    case 10: return w == 0x49 || w == 0x4a;
    case 12: return w == 0x50 || w == 0x51;
    default: return 0;
    }
}

const char *mu_world_bitmap_file(int32_t w, int32_t bitmap, char *buffer, size_t size, int *linear)
{
    static const char *const tiles[14] = {"TileGrass01.jpg", "TileGrass02.jpg", "TileGround01.jpg",
                                          "TileGround02.jpg", "TileGround03.jpg", "TileWater01.jpg",
                                          "TileWood01.jpg", "TileRock01.jpg", "TileRock02.jpg", "TileRock03.jpg",
                                          "TileRock04.jpg", "TileRock05.jpg", "TileRock06.jpg", "TileRock07.jpg"};
    static const char *const alpha_names[5] = {NULL, NULL, "AlphaTileGround01.Tga", "AlphaTileGround02.Tga", NULL};
    static const char *const grass_low[5] = {"TileGrass01.tga", "TileGrass02.tga", "TileGrass03.tga",
                                             "TileGrass04.tga", "TileGrass05.tga"};
    static const char *const grass_high[14] = {"TileGrass01.tga", "TileGrass02.tga", "TileGround01.tga",
                                               "TileGround02.tga", "TileGround03.tga", "TileWater01.tga",
                                               "TileWood01.tga", "TileRock01.tga", "TileRock02.tga",
                                               "TileRock03.tga", "TileRock04.tga", "TileRock05.tga",
                                               "TileRock06.tga", "TileRock07.tga"};
    const int32_t i = bitmap - MU_TERRAIN_TEXTURE_TILE;
    const int special = w == 0x3f || (w >= 0x52 && w <= 0x5a); /* 0x00e94004 / 0x00e3068f */
    *linear = 0;
    const char *name = NULL;
    if (i >= 0 && i < 14) {
        name = tiles[i];
        if (alpha_tile_world(w, i))
            name = (i == 2 || i == 3) ? alpha_names[i] : "AlphaTile01.Tga";
        if (i == 11 && special)
            return snprintf(buffer, size, "../Object64/song_lava1.jpg") < (int)size ? buffer : NULL;
    } else if (i == 14) {
        name = "AlphaTile01.Tga";
    } else if (i >= 15 && i <= 98) {
        snprintf(buffer, size, "ExtTile%02d.jpg", i - 14);
        return buffer;
    } else if (i >= 100 && i <= 113) {
        const int32_t k = i - 100;
        if (k == 0 && special) {
            *linear = 1;
            name = "TileGrass01_R.jpg";
        } else if (k == 1 && w == 0x25) {
            return NULL;
        } else if (w >= 0x8d) {
            name = grass_high[k];
        } else if (k < 5) {
            name = grass_low[k];
        }
    } else if (i >= 115 && i <= 198) {
        snprintf(buffer, size, "ExtTile%02d.tga", i - 114);
        return buffer;
    }
    if (!name)
        return NULL;
    snprintf(buffer, size, "%s", name);
    return buffer;
}

static uint8_t *read_file(const char *path, size_t *size)
{
    FILE *f = fopen(path, "rb");
    if (!f)
        return NULL;
    uint8_t *data = NULL;
    if (fseek(f, 0, SEEK_END) == 0) {
        long n = ftell(f);
        if (n >= 0 && n <= (64L << 20) && fseek(f, 0, SEEK_SET) == 0) {
            data = malloc((size_t)n + 1);
            if (data && fread(data, 1, (size_t)n, f) != (size_t)n) {
                free(data);
                data = NULL;
            }
            *size = (size_t)n;
        }
    }
    fclose(f);
    return data;
}

uint8_t *mu_world_decrypt(const uint8_t *file, size_t size, const char magic[4], size_t *plain_size, char *error,
                          size_t error_size)
{
    *plain_size = 0;
    if (size >= 4 && memcmp(file, magic, 4) == 0) {
        if (size < 4 + 34) {
            snprintf(error, error_size, "envelope shorter than its prefix");
            return NULL;
        }
        uint8_t *plain = malloc(size - 4 - 34 + 1);
        size_t written = 0;
        if (!plain || mu_modulus_decrypt(file + 4, size - 4, plain, size - 4 - 34, &written, error, error_size)) {
            free(plain);
            return NULL;
        }
        *plain_size = written;
        return plain;
    }
    if (size > 0x7fffffff) {
        snprintf(error, error_size, "file too large");
        return NULL;
    }
    uint8_t *plain = malloc(size + 1);
    if (!plain)
        return NULL;
    mu_bmd12_decode(plain, file, (int32_t)size);   /* 0x0098c5f2 */
    *plain_size = size;
    return plain;
}

static int world_path(char *out, size_t size, const char *root, int32_t folder, const char *name)
{
    return snprintf(out, size, "%s/Data/World%d/%s", root, folder, name) < (int)size;
}

static void load_bitmaps(mu_world *w, const char *root, int32_t folder)
{
    char directory[1024], name[128], resolved[1200], message[256];
    snprintf(directory, sizeof directory, "%s/Data/World%d", root, folder);
    for (int32_t i = 0; i < MU_WORLD_BITMAPS; ++i) {
        int linear = 0;
        if (!mu_world_bitmap_file(w->world, MU_TERRAIN_TEXTURE_TILE + i, name, sizeof name, &linear))
            continue;
        const char *slash = strrchr(name, '/');
        char sub[1024];
        const char *dir = directory, *file = name;
        if (slash) {   /* "../Object64/x.jpg" */
            snprintf(sub, sizeof sub, "%s/Data/Object64", root);
            dir = sub;
            file = slash + 1;
        }
        if (!mu_image_resolve(dir, file, resolved, sizeof resolved)) {
            if (i < 15 || (i >= 100 && i < 114))
                w->report.bitmaps_missing++;
            continue;
        }
        if (mu_image_load_file(resolved, &w->bitmaps[i], message, sizeof message) == MU_IMAGE_OK) {
            w->bitmap_linear[i] = (uint8_t)linear;
            w->report.bitmaps_loaded++;
        } else {
            memset(&w->bitmaps[i], 0, sizeof w->bitmaps[i]);
            w->report.bitmaps_missing++;
        }
    }
}

static void check_objects(mu_world *w, const char *root, int32_t folder)
{
    char name[64], path[1200];
    snprintf(name, sizeof name, "EncTerrain%d.obj", folder);
    size_t size = 0;
    uint8_t *raw = world_path(path, sizeof path, root, folder, name) ? read_file(path, &size) : NULL;
    if (!raw) {
        w->report.obj_status = -1;
        return;
    }
    uint8_t *plain = malloc(size + 1);
    if (plain && size >= 4 && size <= 0x7fffffff) {
        mu_bmd12_decode(plain, raw, (int32_t)size);   /* the decoder 0x016d9ac5 calls */
        static const int32_t record[6] = {30, 32, 33, 45, 46, 54};
        int32_t version = plain[0], count = (int16_t)(plain[2] | plain[3] << 8);
        w->report.obj_version = version;
        w->report.obj_count = count;
        /* The client checks only the map number; the header must also fit the length. */
        w->report.obj_status = version >= 0 && version <= 5 && count >= 0 &&
                                       (size_t)4 + (size_t)count * (size_t)record[version] == size &&
                                       plain[1] == (folder & 0xff)
                                   ? 0
                                   : 2;
    }
    free(plain);
    free(raw);
}

mu_world *mu_world_load(const char *root, int32_t world, uint32_t seed, int textures, char *error, size_t error_size)
{
    mu_world *w = calloc(1, sizeof *w);
    if (!w) {
        snprintf(error, error_size, "out of memory");
        return NULL;
    }
    w->world = world;
    const int32_t folder = mu_world_folder(world);
    w->report.folder = folder;
    w->water_height = 0.0f;
    char name[64], path[1200], message[256];
    size_t size = 0, plain_size = 0;
    uint8_t *raw, *plain;

    snprintf(name, sizeof name, "EncTerrain%d.map", folder);
    raw = world_path(path, sizeof path, root, folder, name) ? read_file(path, &size) : NULL;
    plain = raw ? mu_world_decrypt(raw, size, "MAP\x01", &plain_size, message, sizeof message) : NULL;
    free(raw);
    if (!plain) {
        snprintf(error, error_size, "%s: missing or undecodable", path);
        mu_world_free(w);
        return NULL;
    }
    w->report.map_status = mu_terrain_parse_map(plain, plain_size, w->layer1, w->layer2, w->alpha,
                                                &w->report.map_number);
    free(plain);

    snprintf(name, sizeof name, "EncTerrain%d.att", folder);
    raw = world_path(path, sizeof path, root, folder, name) ? read_file(path, &size) : NULL;
    plain = raw ? mu_world_decrypt(raw, size, "ATT\x01", &plain_size, message, sizeof message) : NULL;
    free(raw);
    if (!plain) {
        snprintf(error, error_size, "%s: missing or undecodable", path);
        mu_world_free(w);
        return NULL;
    }
    w->report.att_plain_bytes = plain_size;
    w->report.att_status = mu_terrain_parse_attributes(plain, plain_size, att_key, w->attributes,
                                                       &w->report.att_number);
    free(plain);
    if (w->report.map_status || w->report.att_status == MU_TERRAIN_BAD_SIZE) {
        snprintf(error, error_size, "World%d: map status %d, attribute status %d", folder, w->report.map_status,
                 w->report.att_status);
        mu_world_free(w);
        return NULL;
    }

    raw = world_path(path, sizeof path, root, folder, "TerrainHeight.OZB") ? read_file(path, &size) : NULL;
    if (!raw) {
        snprintf(error, error_size, "%s: missing", path);
        mu_world_free(w);
        return NULL;
    }
    int unresolved = 0;
    int rgb = mu_terrain_height_is_rgb(world, &unresolved);
    if (unresolved)   /* decided by a runtime object in the client; the viewer uses the file length */
        rgb = size >= 58u + 3u * MU_TERRAIN_CELLS;
    w->report.height_rgb = rgb;
    w->report.height_rgb_unresolved = unresolved;
    w->report.height_status = rgb ? mu_terrain_height_rgb(raw, size, w->height)
                                  : mu_terrain_height_bytes(raw, size, mu_terrain_height_scale(world), w->height);
    free(raw);
    if (w->report.height_status) {
        snprintf(error, error_size, "World%d: height file refused", folder);
        mu_world_free(w);
        return NULL;
    }

    int32_t pixels = 0;
    raw = world_path(path, sizeof path, root, folder, "TerrainLight.OZB") ? read_file(path, &size) : NULL;
    w->report.light_status = raw ? mu_terrain_light_bmp(raw, size, w->light_map, MU_TERRAIN_CELLS, &pixels) : -1;
    if (!raw)   /* the client loads nothing; the viewer lights the map white */
        for (int32_t i = 0; i < 3 * MU_TERRAIN_CELLS; ++i)
            w->light_map[i] = 1.0f;
    free(raw);
    raw = world_path(path, sizeof path, root, folder, "TerrainLight_2.OZB") ? read_file(path, &size) : NULL;
    w->report.light2_status = raw ? mu_terrain_light_offset_bmp(raw, size, w->light2, MU_TERRAIN_CELLS, &pixels) : -1;
    free(raw);

    mu_terrain_normals(w->height, w->normal);
    mu_terrain_primary_light(w->normal, w->light_map, world, w->primary);
    uint32_t state = seed;
    mu_terrain_grass_offsets(&state, w->grass_offset);
    memset(w->grass_map, 1, sizeof w->grass_map);   /* 0x016caadb */
    check_objects(w, root, folder);
    if (textures)
        load_bitmaps(w, root, folder);
    mu_world_frame(w, 0.0f);
    return w;
}

void mu_world_free(mu_world *w)
{
    if (!w)
        return;
    for (int32_t i = 0; i < MU_WORLD_BITMAPS; ++i)
        mu_image_free(&w->bitmaps[i]);
    free(w);
}

void mu_world_frame(mu_world *w, float time)
{
    w->time = time;
    memcpy(w->light, w->primary, sizeof w->light);
    mu_terrain_wave(w->world, time, 0, 0, 0, 255, 255, w->wave, w->wave2);
}

static int texture_size(void *context, int32_t texture, float *width, float *height)
{
    const mu_world *w = context;
    const int32_t i = texture - MU_TERRAIN_TEXTURE_TILE;
    if (i < 0 || i >= MU_WORLD_BITMAPS || w->bitmaps[i].width <= 0)
        return 0;
    *width = (float)w->bitmaps[i].width;
    *height = (float)w->bitmaps[i].height;
    return 1;
}

void mu_world_scene(mu_world *w, mu_terrain_scene *s)
{
    memset(s, 0, sizeof *s);
    s->world_index = w->world;
    s->layer1 = w->layer1;
    s->layer2 = w->layer2;
    s->alpha = w->alpha;
    s->attributes = w->attributes;
    s->height = w->height;
    s->light = w->light;
    s->light2 = w->light2;
    s->wave = w->wave;
    s->wave2 = w->wave2;
    s->grass_offset = w->grass_offset;
    s->grass_map = w->grass_map;
    s->water_height = w->water_height;
    s->time = w->time;
    s->detail = w->detail;
    s->texture_size = texture_size;
    s->texture_context = w;
}

void mu_world_state(int32_t state, int32_t argument, mu_meshdraw_state *o)
{
    memset(o, 0, sizeof *o);
    o->texture = 1;
    o->depth_test = 1;
    switch (state) {
    case MU_TERRAIN_STATE_ALPHA:   /* 0x0184a990 */
        o->blend = 1;
        o->src = MU_BLEND_SRC_ALPHA;
        o->dst = MU_BLEND_ONE_MINUS_SRC_ALPHA;
        o->depth_mask = argument ? 1 : 0;
        o->alpha_test = 1;
        o->cull = 0;
        break;
    case MU_TERRAIN_STATE_ADDITIVE: /* 0x0184aa2b */
        o->blend = 1;
        o->src = MU_BLEND_ONE;
        o->dst = MU_BLEND_ONE;
        o->depth_mask = 0;
        o->cull = 0;
        break;
    default:                        /* 0x0184a7f3 */
        o->depth_mask = 1;
        o->cull = 1;
        break;
    }
}

typedef struct raster_context {
    mu_world *world;
    mu_raster *raster;
    mu_render_backend backend;
    mu_meshdraw_state state;
    const mu_image *texture;
    int linear;
    long missing;
} raster_context;

static void r_state(void *c, int32_t state, int32_t argument)
{
    raster_context *x = c;
    mu_world_state(state, argument, &x->state);
    mu_raster_set(x->raster, &x->state, x->texture, x->linear);
}

static void r_bind(void *c, int32_t texture)
{
    raster_context *x = c;
    const int32_t i = texture - MU_TERRAIN_TEXTURE_TILE;
    x->texture = NULL;
    x->linear = 0;
    if (i >= 0 && i < MU_WORLD_BITMAPS && x->world->bitmaps[i].width > 0) {
        x->texture = &x->world->bitmaps[i];
        x->linear = x->world->bitmap_linear[i];
    } else {
        x->missing++;
    }
    mu_raster_set(x->raster, &x->state, x->texture, x->linear);
}

static void r_begin(void *c, int32_t mode) { mu_raster_begin_mode(((raster_context *)c)->raster, mode); }
static void r_end(void *c) { mu_raster_end_mode(((raster_context *)c)->raster); }

static void r_texcoord(void *c, float s, float t)
{
    raster_context *x = c;
    x->backend.sink.texcoord(x->backend.sink.context, s, t);
}

static void r_color3(void *c, const float rgb[3])
{
    raster_context *x = c;
    x->backend.sink.color3(x->backend.sink.context, rgb);
}

static void r_color4(void *c, float r, float g, float b, float a)
{
    raster_context *x = c;
    x->backend.sink.color4(x->backend.sink.context, r, g, b, a);
}

static void r_vertex(void *c, const float xyz[3])
{
    raster_context *x = c;
    x->backend.sink.vertex(x->backend.sink.context, xyz);
}

int mu_world_draw_raster(mu_world *w, mu_raster *raster, int32_t x0, int32_t y0, int32_t x1, int32_t y1,
                         mu_world_draw_stats *stats)
{
    raster_context x;
    memset(&x, 0, sizeof x);
    x.world = w;
    x.raster = raster;
    mu_raster_backend(raster, &x.backend);
    mu_world_state(MU_TERRAIN_STATE_OPAQUE, 0, &x.state);
    mu_terrain_sink sink = {&x, r_state, r_bind, r_begin, r_texcoord, r_color3, r_color4, r_vertex, r_end};
    mu_terrain_scene scene;
    mu_world_scene(w, &scene);
    mu_world_draw_stats local;
    memset(&local, 0, sizeof local);
    int status = mu_terrain_draw(&scene, x0, y0, x1, y1, mu_terrain_alpha_layers(w->world), &sink, &local.tiles);
    local.missing_texture_binds = x.missing;
    if (stats)
        *stats = local;
    return status;
}

float mu_world_height_at(const mu_world *w, float x, float y)
{
    float fx = x / 100.0f, fy = y / 100.0f;
    if (fx < 0.0f) fx = 0.0f;
    if (fy < 0.0f) fy = 0.0f;
    if (fx > 254.999f) fx = 254.999f;
    if (fy > 254.999f) fy = 254.999f;
    int32_t xi = (int32_t)fx, yi = (int32_t)fy;
    float ax = fx - (float)xi, ay = fy - (float)yi;
    const float *h = w->height;
    float a = h[yi * 256 + xi] + (h[yi * 256 + xi + 1] - h[yi * 256 + xi]) * ax;
    float b = h[(yi + 1) * 256 + xi] + (h[(yi + 1) * 256 + xi + 1] - h[(yi + 1) * 256 + xi]) * ax;
    return a + (b - a) * ay;
}
