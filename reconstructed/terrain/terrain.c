/* Authored C for the client's terrain loaders and tile renderer. See terrain.h
 * and docs/research/client-terrain.md for the instruction-level reading. */
#include "terrain.h"

#include <math.h>
#include <string.h>

int32_t mu_terrain_index(int32_t x, int32_t y) { return y * 256 + x; }

int32_t mu_terrain_index_repeat(int32_t x, int32_t y) { return (y & 255) * 256 + (x & 255); }

static int inside(int32_t index) { return index >= 0 && index < MU_TERRAIN_CELLS; }

void mu_terrain_xor3(uint8_t *buffer, int32_t length, const uint8_t key[3])
{
    for (int32_t i = 0; i < length; ++i)
        buffer[i] = (uint8_t)(buffer[i] ^ key[i % 3]);
}

int mu_terrain_parse_map(const uint8_t *plain, size_t length, uint8_t *layer1, uint8_t *layer2, float *alpha,
                         int32_t *map_number)
{
    if (!plain || length < 2u + 3u * MU_TERRAIN_CELLS)
        return MU_TERRAIN_BAD_SIZE;
    *map_number = plain[1];
    memcpy(layer1, plain + 2, MU_TERRAIN_CELLS);
    memcpy(layer2, plain + 2 + MU_TERRAIN_CELLS, MU_TERRAIN_CELLS);
    const uint8_t *source = plain + 2 + 2 * MU_TERRAIN_CELLS;
    for (int32_t i = 0; i < MU_TERRAIN_CELLS; ++i)
        alpha[i] = (float)source[i] / 255.0f; /* cvtsi2ss; divss [0x01a7df30] */
    return MU_TERRAIN_OK;
}

int mu_terrain_parse_attributes(uint8_t *plain, size_t length, const uint8_t key[3], uint16_t *attributes,
                                int32_t *map_number)
{
    if (!plain || (length != 0x20004u && length != 0x10004u))
        return MU_TERRAIN_BAD_SIZE;
    const int wide = length == 0x20004u;
    mu_terrain_xor3(plain, (int32_t)length, key);
    const uint8_t version = plain[0], width = plain[2], height = plain[3];
    *map_number = plain[1];
    if (wide) {
        for (int32_t i = 0; i < MU_TERRAIN_CELLS; ++i)
            attributes[i] = (uint16_t)(plain[4 + 2 * i] | plain[5 + 2 * i] << 8);
    } else {
        for (int32_t i = 0; i < MU_TERRAIN_CELLS; ++i)
            attributes[i] = plain[4 + i];
    }
    int corrupt = !(version == 0 && width == 0xff && height == 0xff);
    for (int32_t i = 0; i < MU_TERRAIN_CELLS; ++i) {
        attributes[i] = (uint16_t)(attributes[i] & 0xfaff);
        if ((attributes[i] & 0xff) >= 0x80)
            corrupt = 1;
    }
    return corrupt ? MU_TERRAIN_CORRUPT : MU_TERRAIN_OK;
}

float mu_terrain_height_scale(int32_t world_index) { return world_index == 0x37 ? 3.0f : 1.5f; }

int mu_terrain_height_bytes(const uint8_t *file, size_t size, float scale, float *height)
{
    const size_t start = 4u + 0x438u;
    if (!file || size < start + MU_TERRAIN_CELLS)
        return MU_TERRAIN_BAD_SIZE;
    for (int32_t i = 0; i < MU_TERRAIN_CELLS; ++i)
        height[i] = (float)file[start + (size_t)i] * scale;
    return MU_TERRAIN_OK;
}

int mu_terrain_height_rgb(const uint8_t *file, size_t size, float *height)
{
    const size_t start = 4u + 14u + 40u;
    if (!file || size < start + 3u * MU_TERRAIN_CELLS)
        return MU_TERRAIN_BAD_SIZE;
    for (int32_t i = 0; i < MU_TERRAIN_CELLS; ++i) {
        const uint8_t *p = file + start + 3u * (size_t)i;
        uint32_t value = (uint32_t)p[2] | (uint32_t)p[1] << 8 | (uint32_t)p[0] << 16;
        /* cvtsi2sd + unsigned correction, cvtsd2ss, then addss -500.0f. */
        float converted = (float)(double)value;
        height[i] = converted + -500.0f;
    }
    return MU_TERRAIN_OK;
}

int mu_terrain_height_is_rgb(int32_t w, int *unresolved)
{
    if (unresolved)
        *unresolved = 0;
    if (w == 0x2a || w == 0x3f || (w >= 0x52 && w <= 0x5a) || w == 0x64 || w == 0x65 || w == 0x6e || w == 0x6f ||
        w == 0x70 || w == 0x7a || (w >= 0x7b && w <= 0x7f) || (w >= 0x80 && w <= 0x82) || w == 0x83 || w == 0x84 ||
        w == 0x85)
        return 1;
    if (unresolved)
        *unresolved = 1;
    return 0;
}

static uint32_t read32(const uint8_t *p) { return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24; }

int mu_terrain_light_bmp(const uint8_t *file, size_t size, float *out, int32_t capacity, int32_t *pixels)
{
    if (!file || size < 58u)
        return MU_TERRAIN_BAD_SIZE;
    const int32_t width = (int32_t)read32(file + 4 + 14 + 4), height = (int32_t)read32(file + 4 + 14 + 8);
    const int64_t count = (int64_t)width * (int64_t)height;
    if (width < 0 || height < 0 || count > capacity || (uint64_t)count * 3u > size - 58u)
        return MU_TERRAIN_BAD_SIZE;
    for (int64_t i = 0; i < count; ++i) {
        const uint8_t *p = file + 58 + 3 * i;
        out[3 * i + 0] = (float)p[2] / 255.0f;
        out[3 * i + 1] = (float)p[1] / 255.0f;
        out[3 * i + 2] = (float)p[0] / 255.0f;
    }
    if (pixels)
        *pixels = (int32_t)count;
    return MU_TERRAIN_OK;
}

int mu_terrain_light_offset_bmp(const uint8_t *file, size_t size, float *out, int32_t capacity, int32_t *pixels)
{
    if (!file || size < 58u)
        return MU_TERRAIN_BAD_SIZE;
    const int32_t width = (int32_t)read32(file + 4 + 14 + 4), height = (int32_t)read32(file + 4 + 14 + 8);
    const int64_t count = (int64_t)width * (int64_t)height;
    if (width < 0 || height < 0 || count > capacity || (uint64_t)count * 3u > size - 58u)
        return MU_TERRAIN_BAD_SIZE;
    for (int64_t i = 0; i < count; ++i) {
        const uint8_t *p = file + 58 + 3 * i;
        for (int k = 0; k < 3; ++k) {
            float v = (float)p[2 - k] / 255.0f;
            v = v * 2.0f;
            out[3 * i + k] = v - 1.0f;
        }
    }
    if (pixels)
        *pixels = (int32_t)count;
    return MU_TERRAIN_OK;
}

void mu_terrain_face_normal(const float a[3], const float b[3], const float c[3], float out[3])
{
    out[2] = 0.0f;
    out[1] = 0.0f;
    out[0] = 0.0f;
    float t10 = b[1] - a[1];
    float t18 = t10 * (c[2] - a[2]);
    float t14 = c[1] - a[1];
    float nx = t18 - t14 * (b[2] - a[2]);
    float t1c = b[2] - a[2];
    float t24 = t1c * (c[0] - a[0]);
    float t20 = c[2] - a[2];
    float ny = t24 - t20 * (b[0] - a[0]);
    float t28 = b[0] - a[0];
    float t30 = t28 * (c[1] - a[1]);
    float t2c = c[0] - a[0];
    float nz = t30 - t2c * (b[1] - a[1]);
    float sum = nx * nx;
    sum = sum + ny * ny;
    sum = sum + nz * nz;
    /* 0x009b0c87 -> 0x00961a07: CRT sqrt of the widened value, stored as
     * float, reloaded and spilled as double by the caller. */
    double length = (double)(float)sqrt((double)sum);
    if (length == 0.0)
        return;
    out[0] = (float)((double)nx / length);
    out[1] = (float)((double)ny / length);
    out[2] = (float)((double)nz / length);
}

void mu_terrain_normals(const float *height, float *normal)
{
    for (int32_t y = 0; y < 256; ++y) {
        for (int32_t x = 0; x < 256; ++x) {
            const int32_t index = mu_terrain_index(x, y);
            float b[3], c[3], d[3];
            b[0] = (float)(x + 1) * 100.0f;
            b[1] = (float)y * 100.0f;
            b[2] = height[mu_terrain_index_repeat(x + 1, y)];
            c[0] = (float)(x + 1) * 100.0f;
            c[1] = (float)(y + 1) * 100.0f;
            c[2] = height[mu_terrain_index_repeat(x + 1, y + 1)];
            d[0] = (float)x * 100.0f;
            d[1] = (float)(y + 1) * 100.0f;
            d[2] = height[mu_terrain_index_repeat(x, y + 1)];
            mu_terrain_face_normal(b, c, d, &normal[3 * index]);
        }
    }
}

void mu_terrain_primary_light(const float *normal, const float *light_map, int32_t world_index, float *primary)
{
    float l[3];
    if (world_index == 30) {
        l[0] = 0.5f;
        l[1] = -1.0f;
        l[2] = 1.0f;
    } else {
        l[0] = 0.5f;
        l[1] = -0.5f;
        l[2] = 0.5f;
    }
    for (int32_t y = 0; y < 256; ++y) {
        for (int32_t x = 0; x < 256; ++x) {
            const int32_t i = mu_terrain_index(x, y);
            const float *n = &normal[3 * i];
            float lum = n[0] * l[0];
            lum = lum + n[1] * l[1];
            lum = lum + n[2] * l[2];
            lum = lum + 0.5f;
            if (0.0f > lum) /* comiss 0, lum; jbe */
                lum = 0.0f;
            else if (lum > 1.0f)
                lum = 1.0f;
            for (int k = 0; k < 3; ++k)
                primary[3 * i + k] = light_map[3 * i + k] * lum;
        }
    }
}

int mu_terrain_tile_corners(const uint16_t *attributes, const float *height, float water_height, float xf, float yf,
                            int32_t xi, int32_t yi, int32_t lod, int picking, int32_t index[4], float corner[12])
{
    index[0] = mu_terrain_index(xi, yi);
    if (!inside(index[0]))
        return -MU_TERRAIN_BAD_INDEX;
    if ((attributes[index[0]] & 8) && !picking)
        return 0;
    index[1] = mu_terrain_index(xi + lod, yi);
    index[2] = mu_terrain_index(xi + lod, yi + lod);
    index[3] = mu_terrain_index(xi, yi + lod);
    for (int k = 1; k < 4; ++k)
        if (!inside(index[k]))
            return -MU_TERRAIN_BAD_INDEX;
    const float x = xf * 100.0f, y = yf * 100.0f;
    corner[0] = x;
    corner[1] = y;
    corner[2] = height[index[0]];
    corner[3] = x + 100.0f;
    corner[4] = y;
    corner[5] = height[index[1]];
    corner[6] = x + 100.0f;
    corner[7] = y + 100.0f;
    corner[8] = height[index[2]];
    corner[9] = x;
    corner[10] = y + 100.0f;
    corner[11] = height[index[3]];
    for (int k = 0; k < 4; ++k)
        if (attributes[index[k]] & 0x40)
            corner[3 * k + 2] = water_height;
    return 1;
}

void mu_terrain_tile_uv(float width, float height, float xf, float yf, int small, const float offset[2],
                        const float *wave, float k, const int32_t index[4], float uv[8])
{
    const float scale = small ? 16.0f : 64.0f;
    const float su = scale / width, sv = scale / height;
    const float u0 = xf * su, v0 = yf * sv;
    uv[0] = u0 + offset[0];
    uv[1] = (v0 + offset[1]) + wave[index[0]] * k;
    uv[2] = (u0 + su) + offset[0];
    uv[3] = (v0 + offset[1]) + wave[index[1]] * k;
    uv[4] = (u0 + su) + offset[0];
    uv[5] = ((v0 + sv) + offset[1]) + wave[index[1]] * k;
    uv[6] = u0 + offset[0];
    uv[7] = ((v0 + sv) + offset[1]) + wave[index[0]] * k;
}

/* World predicates used by the renderer (0x00e94004, 0x00e3068f, 0x009dacec,
 * 0x016a88ae, 0x0095fba9, 0x00e18ae9, 0x009dacb8). */
static int world_no_grass(int32_t w) { return (w >= 0x0b && w <= 0x11) || w == 0x34; }

int mu_terrain_world_has_special_paths(int32_t w)
{
    /* 0x016cff65 opaque pass: water variants and per-texture branches. */
    if (w == 0x1e || w == 0x5e || w == 0x7a || w == 0x8d || w == 0x22 || w == 0x3f || (w >= 0x52 && w <= 0x5a) ||
        w == 0x64 || w == 0x65 || w == 0x6e || w == 0x6f || w == 0x70 || w == 0x8a || w == 0x8c)
        return 1;
    /* additive layer 2 (0x016a88ae: 7, 0x80..0x82) and world 0x85 */
    if (w == 7 || (w >= 0x80 && w <= 0x82) || w == 0x85)
        return 1;
    /* 0x016cf46c face blends and extra faces */
    if (w == 0x27 || (w >= 0x2d && w <= 0x32) || w == 0x62 || w == 0x63 || w == 0x33 || (w >= 0x45 && w <= 0x4a) ||
        w == 0x50 || w == 0x51 || w == 0x5b || w == 0x5c || w == 0x71 || w == 0x91)
        return 1;
    /* 0x009dc0b1 random effects at the start of every face */
    if ((w >= 0x12 && w <= 0x17) || w == 0x35 || w == 0x61)
        return 1;
    return 0;
}

static void emit_corner(const mu_terrain_sink *s, const float uv[2], const float *light, const float *light2,
                        int32_t index, const float corner[3])
{
    s->texcoord(s->context, uv[0], uv[1]);
    float rgb[3];
    for (int k = 0; k < 3; ++k)
        rgb[k] = light[3 * index + k] + light2[3 * index + k]; /* 0x00cfca74 */
    s->color3(s->context, rgb);
    s->vertex(s->context, corner);
}

static void emit_alpha_corner(const mu_terrain_sink *s, const float uv[2], const mu_terrain_scene *scene,
                              int32_t index, const float corner[3])
{
    s->texcoord(s->context, uv[0], uv[1]);
    float rgb[3];
    for (int k = 0; k < 3; ++k)
        rgb[k] = scene->light[3 * index + k] + scene->light2[3 * index + k];
    s->color4(s->context, rgb[0], rgb[1], rgb[2], scene->alpha[index]);
    s->vertex(s->context, corner);
}

static int uv_for(const mu_terrain_scene *scene, int32_t texture, float xf, float yf, const float offset[2], float k,
                  const int32_t index[4], float uv[8])
{
    float width = 0.0f, height = 0.0f;
    if (!scene->texture_size || !scene->texture_size(scene->texture_context, texture, &width, &height))
        return 0; /* the client would dereference a null bitmap */
    mu_terrain_tile_uv(width, height, xf, yf, 0, offset, scene->wave, k, index, uv);
    return 1;
}

static int opaque_tile(const mu_terrain_scene *scene, float xf, float yf, const int32_t index[4],
                       const float corner[12], const mu_terrain_sink *s, mu_terrain_tile_stats *stats)
{
    const int32_t w = scene->world_index;
    const int32_t i0 = index[0];
    const uint16_t att = scene->attributes[i0];
    const int neighbour = (att & 0x4000) != 0;
    float offset[2] = {0.0f, 0.0f};
    float k = 0.0f;
    int32_t layer;
    int layer1_drawn;
    int all_opaque = 1;
    for (int c = 0; c < 4; ++c)
        if (!(scene->alpha[index[c]] >= 1.0f)) /* comiss; jb */
            all_opaque = 0;
    if (all_opaque && !neighbour) {
        layer = scene->layer2[i0];
        layer1_drawn = 0;
    } else {
        layer = scene->layer1[i0];
        layer1_drawn = 1;
        if (layer == 5) {
            if (w == 0x1e || w == 0x5e || w == 0x7a || w == 0x8d)
                return MU_TERRAIN_UNSUPPORTED;
            /* 0x016d0238: water scroll. */
            int32_t t = (int32_t)scene->time; /* cvttss2si */
            offset[0] = (float)(t % 20000) / 20000.0f;
            float c = (float)cos((double)(scene->time * 0.0001f)); /* 0x009fa223 */
            offset[1] = ((c + 1.0f) * 0.5f) * 0.5f;
            k = 0.0015f;
        }
        if (w == 0x22)
            return MU_TERRAIN_UNSUPPORTED;
    }
    if (mu_terrain_world_has_special_paths(w))
        return MU_TERRAIN_UNSUPPORTED;
    float uv[8];
    const int32_t texture = MU_TERRAIN_TEXTURE_TILE + layer;
    if (!uv_for(scene, texture, xf, yf, offset, k, index, uv))
        return MU_TERRAIN_UNSUPPORTED;
    /* 0x016cf46c generic path */
    if (layer == 0xe)
        s->state(s->context, MU_TERRAIN_STATE_ALPHA, 1);
    else
        s->state(s->context, MU_TERRAIN_STATE_OPAQUE, 0);
    s->bind(s->context, texture);
    s->begin(s->context, MU_TERRAIN_GL_TRIANGLE_FAN);
    for (int c = 0; c < 4; ++c)
        emit_corner(s, &uv[2 * c], scene->light, scene->light2, index[c], &corner[3 * c]);
    s->end(s->context);
    stats->faces++;
    int status = MU_TERRAIN_OK;
    if (scene->detail >= 4 && neighbour)
        status = MU_TERRAIN_UNSUPPORTED; /* 0x016cfbac neighbour face, texture 0x7723 */
    int any = 0;
    for (int c = 0; c < 4; ++c)
        if (scene->alpha[index[c]] > 0.0f) /* comiss; ja */
            any = 1;
    if (!any)
        return status;
    if (!layer1_drawn)
        return status;
    const int32_t layer2 = scene->layer2[i0];
    if (layer2 != 5) {
        offset[0] = 0.0f;
        offset[1] = 0.0f;
    }
    if (layer2 == 0xff)
        return status;
    const int32_t texture2 = MU_TERRAIN_TEXTURE_TILE + layer2;
    if (!uv_for(scene, texture2, xf, yf, offset, 0.0f, index, uv))
        return MU_TERRAIN_UNSUPPORTED;
    /* 0x016cfb31 */
    s->state(s->context, MU_TERRAIN_STATE_ALPHA, 1);
    s->bind(s->context, texture2);
    s->begin(s->context, MU_TERRAIN_GL_TRIANGLE_FAN);
    for (int c = 0; c < 4; ++c)
        emit_alpha_corner(s, &uv[2 * c], scene, index[c], &corner[3 * c]);
    s->end(s->context);
    stats->alpha_faces++;
    return status;
}

static int grass_tile(const mu_terrain_scene *scene, float xf, int32_t yi, const int32_t index[4], float corner[12],
                      const mu_terrain_sink *s, mu_terrain_tile_stats *stats)
{
    const int32_t i0 = index[0];
    for (int c = 0; c < 4; ++c)
        if (scene->alpha[index[c]] > 0.0f)
            return MU_TERRAIN_OK;
    if (scene->grass_disabled || world_no_grass(scene->world_index))
        return MU_TERRAIN_OK;
    if (scene->layer1[i0] >= 0x63)
        return MU_TERRAIN_OK;
    if (!scene->grass_map[i0]) /* 0x016cab03 */
        return MU_TERRAIN_OK;
    const int32_t texture = MU_TERRAIN_TEXTURE_GRASS + scene->layer1[i0];
    float width = 0.0f, height = 0.0f;
    if (!scene->texture_size || !scene->texture_size(scene->texture_context, texture, &width, &height))
        return MU_TERRAIN_OK; /* 0x00c97ce3 returned null */
    const int32_t w = scene->world_index;
    const float blade = height * 2.0f;
    s->bind(s->context, texture);
    if (w == 0x3f || (w >= 0x52 && w <= 0x5a)) /* 0x00e94004 / 0x00e3068f */
        s->state(s->context, MU_TERRAIN_STATE_ADDITIVE, 0);
    const float step = 0.25f;
    float u = xf * step;
    u = u + scene->grass_offset[yi & 0xff]; /* [ebp+0x14] is the row */
    float uv[8] = {u, 0.0f, u + step, 0.0f, u + step, 1.0f, u, 1.0f};
    /* 0x016d127a: corner 3 = corner 0 and corner 1 = corner 2 (the blade
     * stands on the tile diagonal), then corners 0 and 1 are raised by the
     * blade height, moved by -50 in x and swayed in y. */
    memcpy(&corner[9], &corner[0], 3 * sizeof(float));
    memcpy(&corner[3], &corner[6], 3 * sizeof(float));
    corner[2] = corner[2] + blade;
    corner[5] = corner[5] + blade;
    corner[0] = corner[0] + -50.0f;
    corner[3] = corner[3] + -50.0f;
    const int second = w == 0x50 || w == 0x51 || w == 0x90 || ((w == 0x6e || w == 0x6f) && scene->layer1[i0] == 4) ||
                       w == 0x8d || w == 0x8e;
    const float *sway = second ? scene->wave2 : scene->wave;
    if (!sway)
        return MU_TERRAIN_UNSUPPORTED;
    corner[1] = corner[1] + sway[index[0]];
    corner[4] = corner[4] + sway[index[1]];
    s->begin(s->context, MU_TERRAIN_GL_QUADS);
    for (int c = 0; c < 4; ++c) {
        s->texcoord(s->context, uv[2 * c], uv[2 * c + 1]);
        s->color3(s->context, &scene->light[3 * index[c]]);
        s->vertex(s->context, &corner[3 * c]);
    }
    s->end(s->context);
    if (w == 0x3f || (w >= 0x52 && w <= 0x5a))
        s->state(s->context, MU_TERRAIN_STATE_OPAQUE, 0);
    stats->grass++;
    return MU_TERRAIN_OK;
}

int mu_terrain_draw_tile(const mu_terrain_scene *scene, int32_t pass, float xf, float yf, int32_t xi, int32_t yi,
                         const mu_terrain_sink *sink, mu_terrain_tile_stats *stats)
{
    int32_t index[4];
    float corner[12];
    int built = mu_terrain_tile_corners(scene->attributes, scene->height, scene->water_height, xf, yf, xi, yi, 1, 0,
                                        index, corner);
    if (built < 0)
        return -built;
    if (built == 0) {
        stats->skipped++;
        return MU_TERRAIN_OK;
    }
    int status = pass == 2 ? grass_tile(scene, xf, yi, index, corner, sink, stats)
                           : opaque_tile(scene, xf, yf, index, corner, sink, stats);
    if (status == MU_TERRAIN_UNSUPPORTED)
        stats->unsupported++;
    return status;
}

static int32_t clamp_box(int32_t v) { return v < 0 ? 0 : (v > 251 ? 251 : v); }

static int walk(const mu_terrain_scene *scene, int32_t pass, int32_t x_min, int32_t y_min, int32_t x_max,
                int32_t y_max, const mu_terrain_sink *sink, mu_terrain_tile_stats *stats)
{
    int worst = MU_TERRAIN_OK;
    /* 0x016d2e8e: blocks of 4 starting at the box minimum; 0x016d2d81: 4 x 4 tiles. */
    float by = (float)y_min;
    for (int32_t y = y_min; y <= y_max; y += 4, by = by + 4.0f) {
        float bx = (float)x_min;
        for (int32_t x = x_min; x <= x_max; x += 4, bx = bx + 4.0f) {
            float ty = by;
            for (int32_t j = 0; j < 4; ++j) {
                float tx = bx;
                for (int32_t i = 0; i < 4; ++i) {
                    int status = mu_terrain_draw_tile(scene, pass, tx, ty, x + i, y + j, sink, stats);
                    if (status > worst)
                        worst = status;
                    tx = tx + 1.0f;
                }
                ty = ty + 1.0f;
            }
        }
    }
    return worst;
}

int mu_terrain_alpha_layers(int32_t w) { return !((w >= 0x12 && w <= 0x17) || w == 0x35 || w == 0x61 || w == 0x1e); }

int mu_terrain_draw(const mu_terrain_scene *scene, int32_t x_min, int32_t y_min, int32_t x_max, int32_t y_max,
                    int alpha_layers, const mu_terrain_sink *sink, mu_terrain_tile_stats *stats)
{
    x_min = clamp_box(x_min);
    y_min = clamp_box(y_min);
    x_max = clamp_box(x_max);
    y_max = clamp_box(y_max);
    sink->state(sink->context, MU_TERRAIN_STATE_OPAQUE, 0);
    int worst = walk(scene, 0, x_min, y_min, x_max, y_max, sink, stats);
    sink->state(sink->context, MU_TERRAIN_STATE_ALPHA, 1);
    const int32_t w = scene->world_index;
    if (alpha_layers && !(w == 7 || (w >= 0x80 && w <= 0x82)) && w != 0x5e) {
        int status = walk(scene, 2, x_min, y_min, x_max, y_max, sink, stats);
        if (status > worst)
            worst = status;
    }
    return worst;
}

void mu_terrain_grass_offsets(uint32_t *state, float *offset)
{
    for (int32_t i = 0; i < MU_TERRAIN_CELLS; ++i) {
        *state = *state * 214013u + 2531011u;
        int32_t value = (int32_t)((*state >> 16) & 0x7fff);
        offset[i] = (float)(value % 4) / 4.0f;
    }
}

static float sinf_client(float v) { return (float)sin((double)v); } /* 0x009681bd */

void mu_terrain_wave(int32_t w, float time, int alternate, int32_t x_min, int32_t y_min, int32_t x_max,
                     int32_t y_max, float *wave, float *wave2)
{
    const int32_t t = (int32_t)time; /* cvttss2si */
    float scale = 10.0f, phase, scale2 = 0.0f, phase2 = 0.0f;
    phase = alternate ? (float)(t % 36000) * 0.01f : (float)(t % 720000) * 0.002f;
    const int second = w == 0x50 || w == 0x51 || w == 0x90 || w == 0x6e || w == 0x6f || w == 0x8d || w == 0x8e;
    if (second) {
        scale2 = 15.0f;
        phase2 = (float)(t % 36000) * 0.008f;
    }
    for (int32_t y = y_min; y <= (y_max + 3 < 255 ? y_max + 3 : 255); ++y) {
        float xf = (float)x_min;
        for (int32_t x = x_min; x <= (x_max + 3 < 255 ? x_max + 3 : 255); ++x, xf = xf + 1.0f) {
            const int32_t i = mu_terrain_index(x, y);
            if (w == 8) {
                wave[i] = sinf_client(xf * 50.0f + phase) * scale;
            } else if (w == 0x50 || w == 0x51 || w == 0x6e || w == 0x6f) {
                wave[i] = sinf_client(xf * 50.0f + phase) * scale;
                if (wave2)
                    wave2[i] = sinf_client(xf * 50.0f + phase2) * scale2;
            } else if (w == 0x39 || w == 0x3a) {
                scale = 60.0f;
                wave[i] = sinf_client(xf * 50.0f + phase) * scale;
            } else if (w == 0x8d || w == 0x8e) {
                wave[i] = sinf_client(xf * 5.0f + phase) * scale;
                if (wave2)
                    wave2[i] = sinf_client(xf * 5.0f + phase2) * scale2;
            } else {
                wave[i] = sinf_client(xf * 5.0f + phase) * scale;
            }
        }
    }
}
