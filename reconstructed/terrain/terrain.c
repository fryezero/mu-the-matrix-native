/* Authored C for the client's terrain loaders and tile renderer. See terrain.h
 * and docs/research/client-terrain.md for the instruction-level reading. */
#include "terrain.h"

#include <math.h>
#include <stdint.h>
#include <string.h>

#include "../record-math/record_math.h"

int32_t mu_terrain_index(int32_t x, int32_t y) { return (int32_t)((uint32_t)y * 256u + (uint32_t)x); } /* wraps like imul/add */

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

int mu_terrain_world_handler_flag(int32_t w)
{
    /* 0x00ea488e registers one handler per class; the constructors of the
     * handlers of 0x86..0x91 store byte +4 = 1 (e.g. 0x00d83d84 for 0x86). */
    if (w >= 0x86 && w <= 0x91)
        return 1;
    static const int32_t registered[] = {0x39, 0x3a, 0x3e, 0x3f, 0x40, 0x45, 0x46, 0x47, 0x48, 0x4f, 0x50,
                                         0x51, 0x52, 0x5b, 0x5c, 0x5d, 0x5e, 0x5f, 0x60, 0x64, 0x65, 0x6e,
                                         0x6f, 0x70, 0x71, 0x72, 0x73, 0x74, 0x75, 0x76, 0x77, 0x78, 0x79,
                                         0x7a, 0x7b, 0x7c, 0x7d, 0x7e, 0x7f, 0x80, 0x81, 0x82, 0x83, 0x84,
                                         0x85};
    for (size_t i = 0; i < sizeof registered / sizeof registered[0]; ++i)
        if (registered[i] == w)
            return 0;
    return -1;
}

int mu_terrain_height_is_rgb(int32_t w, int *unresolved)
{
    if (unresolved)
        *unresolved = 0;
    if (w == 0x2a || w == 0x3f || (w >= 0x52 && w <= 0x5a) || w == 0x64 || w == 0x65 || w == 0x6e || w == 0x6f ||
        w == 0x70 || w == 0x7a || (w >= 0x7b && w <= 0x7f) || (w >= 0x80 && w <= 0x82) || w == 0x83 || w == 0x84 ||
        w == 0x85)
        return 1;
    return mu_terrain_world_handler_flag(w) == 1; /* 0x00ea594b -> 0x00ea2713 -> vtable slot 1 */
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
static int world_lava(int32_t w) { return w == 0x3f || (w >= 0x52 && w <= 0x5a); }  /* 0x00e94004 || 0x00e3068f */
static int world_additive(int32_t w) { return w == 7 || (w >= 0x80 && w <= 0x82); } /* 0x016a88ae */
static int world_chaos(int32_t w) { return (w >= 0x12 && w <= 0x17) || w == 0x35 || w == 0x61; }

int mu_terrain_world_has_special_paths(int32_t w)
{
    return (w == 0x71 || w == 0x91 ? 1 : 0) | (world_chaos(w) ? 2 : 0);
}

/* cvttss2si: out-of-range and NaN give 0x80000000. */
static int32_t cvtt(float v)
{
    if (!(v > -2147483904.0f && v < 2147483648.0f))
        return INT32_MIN;
    return (int32_t)v;
}

int32_t mu_terrain_animated_texture(int32_t frame_counter) { return MU_TERRAIN_TEXTURE_TILE + 200 + frame_counter; }

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

static int uv_for(const mu_terrain_scene *scene, int32_t texture, float xf, float yf, int small, const float offset[2],
                  float k, const int32_t index[4], float uv[8])
{
    float width = 0.0f, height = 0.0f;
    if (!scene->texture_size || !scene->texture_size(scene->texture_context, texture, &width, &height))
        return 0; /* the client would dereference a null bitmap */
    mu_terrain_tile_uv(width, height, xf, yf, small, offset, scene->wave, k, index, uv);
    return 1;
}

/* Texture scroll terms of 0x016cff65 (layer-1 faces). t = (int)time. */
typedef struct scroll {
    float forward, backward, cosine; /* (t % m) / m, -(t % m) / m, ((cos(time * 1e-4) + 1) * .5) * .5 */
} scroll;

static float scroll_forward(int32_t t, int32_t m) { return (float)(t % m) / (float)m; }
static float scroll_backward(int32_t t, int32_t m) { return -(float)(t % m) / (float)m; } /* xorps sign, divss */

static float cosine_term(float time)
{
    float c = (float)cos((double)(time * 0.0001f)); /* 0x009fa223 */
    return ((c + 1.0f) * 0.5f) * 0.5f;
}

static void water_particle(const mu_terrain_scene *scene, float xf, float yf)
{
    /* 0x016d02c2: world 0x22, rand() % 50 == 0 -> CreateParticle(0x7f90, ...) */
    if (!scene->random)
        return;
    if (scene->random(scene->effect_context) % 50 != 0)
        return;
    static const float light[3] = {0.3f, 0.4f, 0.2f};
    float position[3];
    float base = xf * 100.0f;
    position[0] = base + (float)(scene->random(scene->effect_context) % 100 + 1) * 1.0f;
    base = yf * 100.0f;
    position[1] = base + (float)(scene->random(scene->effect_context) % 100 + 1) * 1.0f;
    position[2] = scene->hero_z + 10.0f;
    if (scene->effect)
        scene->effect(scene->effect_context, 0x7f90, position, light);
}

/* Layer-1 offsets of 0x016d005f..0x016d0e66. */
static void layer1_scroll(const mu_terrain_scene *scene, int32_t layer, float xf, float yf, float offset[2], float *k)
{
    const int32_t w = scene->world_index;
    const int32_t t = cvtt(scene->time);
#define GENERIC() do { offset[0] = scroll_forward(t, 20000); offset[1] = cosine_term(scene->time); *k = 0.0015f; } while (0)
    if (layer == 5) {
        if (w == 0x1e) {
            offset[0] = scroll_backward(t, 20000);
            offset[1] = cosine_term(scene->time);
            *k = 0.0015f;
        } else if (w == 0x5e) {
            offset[0] = scroll_backward(t, 20000);
            offset[1] = scroll_forward(t, 20000);
            *k = 0.0015f;
        } else if (w == 0x7a) {
            offset[0] = scroll_forward(t, 50000);
            float c = (float)cos((double)(scene->time * 0.0001f));
            offset[1] = (c + 1.0f) * 0.1f;
            *k = 0.0015f;
        } else if (w == 0x8d) {
            offset[0] = 0.0f;
            offset[1] = 0.0f;
            *k = 0.0f;
        } else {
            GENERIC();
        }
        if (w == 0x22)
            water_particle(scene, xf, yf);
    }
    if (world_lava(w)) {
        if (layer == 0xb) /* Object64\song_lava1 */
            GENERIC();
    } else if (w == 0x6e || w == 0x64 || w == 0x65 || w == 0x6f) {
        if (layer == 6)
            GENERIC();
    } else if (w == 0x70) {
        if (layer >= 0x15 && layer <= 0x18) {
            const float f = scroll_forward(t, 30000), b = scroll_backward(t, 30000), c = cosine_term(scene->time);
            offset[0] = layer == 0x15 || layer == 0x18 ? c : (layer == 0x16 ? f : b);
            offset[1] = layer == 0x15 ? f : (layer == 0x18 ? b : c);
            *k = 0.002f;
        }
    } else if (w == 0x7a) {
        if (layer == 0x10)
            GENERIC();
    } else if (w == 0x8a || w == 0x8c || w == 0x8d) {
        /* direction per tile: 0 = (+u, cos), 1 = (cos, -v), 2 = (-u, cos), 3 = (cos, +v) */
        int direction = -1;
        if (w == 0x8a)
            direction = layer == 0x20 ? 2 : layer == 0x21 ? 3 : layer == 0x22 ? 1 : -1;
        else if (w == 0x8c)
            direction = layer == 0x14 ? 1 : layer == 0x15 ? 2 : layer == 0x16 ? 3 : -1;
        else if (layer == 0x17 || layer == 0x1e)
            direction = 0;
        else if (layer == 0x18 || layer == 0x1f)
            direction = 1;
        else if (layer == 0x19 || layer == 0x20)
            direction = 2;
        else if (layer == 0x1a || layer == 0x21)
            direction = 3;
        if (direction >= 0) {
            const float c = cosine_term(scene->time);
            if (direction == 0) { offset[0] = scroll_forward(t, 20000); offset[1] = c; }
            if (direction == 1) { offset[0] = c; offset[1] = scroll_backward(t, 20000); }
            if (direction == 2) { offset[0] = scroll_backward(t, 20000); offset[1] = c; }
            if (direction == 3) { offset[0] = c; offset[1] = scroll_forward(t, 20000); }
            *k = 0.0015f;
        }
    }
#undef GENERIC
}

/* RenderFace 0x016cf46c: the blend state per world and texture, then one fan. */
static int render_face(const mu_terrain_scene *scene, int32_t layer, const int32_t index[4], const float corner[12],
                       const float uv[8], const mu_terrain_sink *s)
{
    const int32_t w = scene->world_index;
    int alpha = layer == 0xe;
    if (w == 0x27) {
        if (layer == 0x64)
            return MU_TERRAIN_OK; /* nothing drawn */
        alpha = layer == 3;
    } else if ((w >= 0x62 && w <= 0x63) || (w >= 0x2d && w <= 0x32)) { /* 0x0095fba9 */
        alpha = layer == 4;
    } else if (w == 0x33) {
        alpha = layer == 2;
    } else if (w >= 0x45 && w <= 0x4a) {
        alpha = layer == 10;
    } else if (w == 0x50 || w == 0x51) { /* 0x00e18ae9 */
        alpha = layer == 12;
    } else if (w == 0x5b || w == 0x5c) {
        alpha = layer == 9;
    }
    if (alpha)
        s->state(s->context, MU_TERRAIN_STATE_ALPHA, 1);
    else
        s->state(s->context, MU_TERRAIN_STATE_OPAQUE, 0);
    if ((w == 0x71 || w == 0x91) && scene->detail >= 4 && (scene->attributes[index[0]] & 0x2000))
        return MU_TERRAIN_UNSUPPORTED; /* 0x016cf5f0 / 0x016cf761 overlay faces (texture 0x7722) */
    const int32_t texture = MU_TERRAIN_TEXTURE_TILE + layer;
    s->bind(s->context, texture);
    s->begin(s->context, MU_TERRAIN_GL_TRIANGLE_FAN);
    for (int c = 0; c < 4; ++c)
        emit_corner(s, &uv[2 * c], scene->light, scene->light2, index[c], &corner[3 * c]);
    s->end(s->context);
    return MU_TERRAIN_OK;
}

/* 0x016cfbac: the 0x4000 face (texture 0x7723, World114\TileBright), additive. */
static int neighbour_face(const mu_terrain_scene *scene, int32_t xi, int32_t yi, const float uv[8],
                          const float corner[12], const mu_terrain_sink *s)
{
    const int32_t around[4] = {mu_terrain_index(xi - 1, yi), mu_terrain_index(xi + 1, yi), mu_terrain_index(xi, yi + 1),
                               mu_terrain_index(xi, yi - 1)};
    for (int k = 0; k < 4; ++k)
        if (!inside(around[k]))
            return MU_TERRAIN_BAD_INDEX; /* the client reads outside the attribute grid */
    s->bind(s->context, 0x7723);
    int edge = 0;
    for (int k = 0; k < 4; ++k)
        if (!(scene->attributes[around[k]] & 0x4000))
            edge = 1;
    s->state(s->context, MU_TERRAIN_STATE_ADDITIVE, 0);
    const float rgb = 0.8f, a = edge ? 0.5f : 0.8f;
    s->begin(s->context, MU_TERRAIN_GL_TRIANGLE_FAN);
    for (int c = 0; c < 4; ++c) {
        s->texcoord(s->context, uv[2 * c], uv[2 * c + 1]);
        s->color4(s->context, rgb, rgb, rgb, a);
        s->vertex(s->context, &corner[3 * c]);
    }
    s->end(s->context);
    s->state(s->context, MU_TERRAIN_STATE_OPAQUE, 0);
    return MU_TERRAIN_OK;
}

static int opaque_tile(const mu_terrain_scene *scene, float xf, float yf, int32_t xi, int32_t yi,
                       const int32_t index[4], const float corner[12], const mu_terrain_sink *s,
                       mu_terrain_tile_stats *stats)
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
        layer1_scroll(scene, layer, xf, yf, offset, &k);
    }
    float uv[8];
    const int32_t texture = MU_TERRAIN_TEXTURE_TILE + layer;
    if (!uv_for(scene, texture, xf, yf, 0, offset, k, index, uv))
        return MU_TERRAIN_UNSUPPORTED;
    int status = render_face(scene, layer, index, corner, uv, s);
    if (status == MU_TERRAIN_OK)
        stats->faces++;
    if (scene->detail >= 4 && neighbour) {
        int n = neighbour_face(scene, xi, yi, uv, corner, s);
        if (n > status)
            status = n;
    }
    int any = 0;
    for (int c = 0; c < 4; ++c)
        if (scene->alpha[index[c]] > 0.0f) /* comiss; ja */
            any = 1;
    if (!any)
        return status;
    const int32_t layer2 = scene->layer2[i0];
    if ((world_additive(w) && layer2 == 5) || (w == 0x85 && layer2 == 4)) {
        /* 0x016d0f7e: animated additive layer, 16-texel UV scale, no scroll */
        const int32_t animated = mu_terrain_animated_texture(scene->frame_counter);
        const float zero[2] = {0.0f, 0.0f};
        if (!uv_for(scene, animated, xf, yf, 1, zero, 0.0f, index, uv))
            return MU_TERRAIN_UNSUPPORTED;
        s->state(s->context, MU_TERRAIN_STATE_ADDITIVE, 0); /* 0x016cfb70 */
        s->bind(s->context, animated);
        s->begin(s->context, MU_TERRAIN_GL_TRIANGLE_FAN);
        for (int c = 0; c < 4; ++c) {
            s->texcoord(s->context, uv[2 * c], uv[2 * c + 1]);
            const float a = scene->alpha[index[c]];
            const float rgb[3] = {a, a, a}; /* glColor3f(alpha, alpha, alpha) */
            s->color3(s->context, rgb);
            s->vertex(s->context, &corner[3 * c]);
        }
        s->end(s->context);
        stats->alpha_faces++;
        return status;
    }
    if (!layer1_drawn)
        return status;
    if (layer2 != 5) {
        offset[0] = 0.0f;
        offset[1] = 0.0f;
    }
    if (layer2 == 0xff)
        return status;
    const int32_t texture2 = MU_TERRAIN_TEXTURE_TILE + layer2;
    if (!uv_for(scene, texture2, xf, yf, 0, offset, 0.0f, index, uv))
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
                           : opaque_tile(scene, xf, yf, xi, yi, index, corner, sink, stats);
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


/* ---------------------------------------------------------------------------
 * NATIVE-TERRAIN-002
 * ------------------------------------------------------------------------- */

void mu_terrain_frame_light(const float *primary, float *light, int32_t x_min, int32_t y_min, int32_t x_max,
                            int32_t y_max)
{
    for (int32_t y = y_min; y <= y_max + 3; ++y)
        for (int32_t x = x_min; x <= x_max + 3; ++x) {
            const int32_t i = mu_terrain_index_repeat(x, y);
            memcpy(&light[3 * i], &primary[3 * i], 3 * sizeof(float)); /* mov, bit for bit */
        }
}

static float sqrt_client(float v) { return (float)sqrt((double)v); } /* 0x00961a07 */

void mu_terrain_add_light(float x, float y, const float light[3], int32_t range, float *buffer)
{
    const float rf = (float)range;
    const float xf = x / 100.0f, yf = y / 100.0f;
    const int32_t xi = cvtt(xf), yi = cvtt(yf);
    const int32_t y0 = (int32_t)((uint32_t)yi - (uint32_t)range), y1 = (int32_t)((uint32_t)yi + (uint32_t)range);
    float row = (float)y0;
    for (int32_t yy = y0; yy <= y1; ++yy, row = row + 1.0f) {
        const int32_t x0 = (int32_t)((uint32_t)xi - (uint32_t)range), x1 = (int32_t)((uint32_t)xi + (uint32_t)range);
        float column = (float)x0;
        for (int32_t xx = x0; xx <= x1; ++xx, column = column + 1.0f) {
            const float dx = xf - column, dy = yf - row;
            float d = dx * dx;
            d = d + dy * dy;
            const float lf = (rf - sqrt_client(d)) / rf;
            if (lf > 0.0f) {
                float *p = &buffer[3 * mu_terrain_index_repeat(xx, yy)];
                for (int k = 0; k < 3; ++k) {
                    float v = light[k] * lf;
                    p[k] = v + p[k];
                    if (0.0f > p[k])
                        p[k] = 0.0f;
                }
            }
            if (xx == INT32_MAX)
                break;
        }
        if (yy == INT32_MAX)
            break;
    }
}

float mu_terrain_water_move(int32_t w, float time)
{
    const int32_t t = cvtt(time);
    if (w == 8)
        return (float)(t % 40000) * 2.5e-5f;
    if (w == 0x2a)
        return (float)(t % 50000) * 2e-5f;
    if (w == 0x5e)
        return (float)(t % 20000) * 0.0001f;
    return (float)(t % 20000) * 5e-5f;
}

static int32_t clamp_box_bound(int32_t v) { return v < 0 ? 0 : (v > 251 ? 251 : v); }

void mu_terrain_frustum_create(float aspect, float view_far, float fov, const float modelview[12],
                               const float camera_position[3], mu_terrain_frustum *f)
{
    const float distance = view_far * 0.9f;
    float angle = fov * 0.5f;
    angle = angle * 3.141592f;  /* binary32 0x40490fd8 */
    angle = angle / 180.0f;
    const float t = (float)tan((double)angle); /* 0x00a0cf72 */
    float width = t * distance;
    width = width * aspect;
    width = width + 100.0f;
    float height = width * 3.0f;
    height = height / 4.0f;
    const float corner[5][3] = {{0.0f, 0.0f, 0.0f},
                                {-width, height, -distance},
                                {width, height, -distance},
                                {width, -height, -distance},
                                {-width, -height, -distance}};
    float min_x = 25600.0f, min_y = 25600.0f, max_x = 0.0f, max_y = 0.0f;
    for (int i = 0; i < 5; ++i) {
        float r[3];
        mu_vector_irotate(corner[i], modelview, r); /* 0x00cfff3c */
        for (int k = 0; k < 3; ++k)
            f->vertex[i][k] = r[k] + camera_position[k];
        if (min_x > f->vertex[i][0]) min_x = f->vertex[i][0];
        if (min_y > f->vertex[i][1]) min_y = f->vertex[i][1];
        if (f->vertex[i][0] > max_x) max_x = f->vertex[i][0];
        if (f->vertex[i][1] > max_y) max_y = f->vertex[i][1];
    }
    const int32_t step = 4;
    f->x_min = clamp_box_bound(cvtt(min_x / 100.0f) / step * step - step);
    f->y_min = clamp_box_bound(cvtt(min_y / 100.0f) / step * step - step);
    f->x_max = clamp_box_bound(cvtt(max_x / 100.0f) / step * step + step);
    f->y_max = clamp_box_bound(cvtt(max_y / 100.0f) / step * step + step);
    mu_terrain_face_normal(f->vertex[0], f->vertex[1], f->vertex[2], f->normal[0]);
    mu_terrain_face_normal(f->vertex[0], f->vertex[2], f->vertex[3], f->normal[1]);
    mu_terrain_face_normal(f->vertex[0], f->vertex[3], f->vertex[4], f->normal[2]);
    mu_terrain_face_normal(f->vertex[0], f->vertex[4], f->vertex[1], f->normal[3]);
    mu_terrain_face_normal(f->vertex[3], f->vertex[2], f->vertex[1], f->normal[4]);
    for (int i = 0; i < 5; ++i) {
        const float *v = f->vertex[i == 4 ? 1 : 0];
        float dot = v[0] * f->normal[i][0];
        dot = dot + v[1] * f->normal[i][1];
        dot = dot + v[2] * f->normal[i][2];
        f->d[i] = -dot;
    }
}

int mu_terrain_frustum_2d_params_for(int32_t w, int32_t mode, int32_t screen_width, float camera_scale,
                                     float distance_2400, mu_terrain_frustum_2d_params *p)
{
    static const float far_distance[6] = {0.0f, 2700.0f, 3000.0f, 3300.0f, 3400.0f, 3400.0f};
    static const float width_far[6] = {0.0f, 1200.0f, 1300.0f, 1500.0f, 1600.0f, 1600.0f};
    static const float width_near[6] = {0.0f, 540.0f, 540.0f, 580.0f, 660.0f, 660.0f};
    memset(p, 0, sizeof *p);
    if (mode >= 1 && mode <= 5) {
        float s = (float)screen_width / 640.0f;
        s = s + 0.1f;
        p->distance = far_distance[mode];
        p->near_offset = p->distance * 0.19f;
        p->back_offset = p->distance * 0.47f;
        p->width_far = width_far[mode] * s;
        p->width_near = width_near[mode] * s;
        return 1;
    }
    if (mode == 0) {
        const float s = w == 0x8b ? 5.0f : camera_scale;
        p->distance = distance_2400;
        p->near_offset = p->distance * 0.19f;
        p->back_offset = p->distance * (w == 0x3f ? 0.35f : 0.47f);
        p->width_far = (w == 0x3f ? 1900.0f : 1190.0f) * s;
        p->width_near = 540.0f * s;
        return 1;
    }
    return 0;
}

static float max_client(float a, float b) { return a > b ? a : b; } /* 0x0184f93f */

int mu_terrain_frustum_2d(int32_t w, const float position[3], const float camera_angle[3],
                          const mu_terrain_frustum_2d_params *params, int wide, float x2d[4], float y2d[4])
{
    if (w == 0x49 || w == 6)
        return MU_TERRAIN_UNSUPPORTED;
    float width_far = params->width_far, width_near = params->width_near;
    if (wide) {
        width_far = width_far * 1.51f;
        width_near = width_near * 1.2f;
    }
    const float base = (w == 0x86 || w == 0x8b) ? 67.0f : 71.0f;
    float a = base + camera_angle[0];
    a = a * 0.017453292f; /* binary32 0x3c8efa35 */
    float c = (float)cos((double)a);
    c = c * 10.0f;
    c = c - 9.2f;
    const float lift = max_client(0.0f, c) * params->distance;
    float far_y = params->distance - params->back_offset;
    far_y = far_y + lift;
    const float near_y = params->near_offset - params->back_offset;
    const float p[4][3] = {{-width_far, far_y, 0.0f}, {width_far, far_y, 0.0f}, {width_near, near_y, 0.0f},
                           {-width_near, near_y, 0.0f}};
    const float angle[3] = {0.0f, 0.0f, 45.0f};
    float matrix[12];
    mu_angle_matrix(angle, matrix); /* 0x00cff32a */
    for (int i = 0; i < 4; ++i) {
        float r[3];
        mu_vector_rotate(p[i], matrix, r); /* 0x00d000ad */
        for (int k = 0; k < 3; ++k)
            r[k] = r[k] + position[k];
        x2d[i] = r[0] * 0.01f;
        y2d[i] = r[1] * 0.01f;
    }
    return MU_TERRAIN_OK;
}

int mu_terrain_test_frustum_2d(const float x2d[4], const float y2d[4], int32_t scene_state, float x, float y,
                               float range)
{
    if (scene_state >= 1 && scene_state <= 4)
        return 1;
    int32_t j = 3;
    for (int32_t i = 0; i < 4; j = i, ++i) {
        float a = x2d[i] - x;
        a = a * (y2d[j] - y);
        float b = x2d[j] - x;
        b = b * (y2d[i] - y);
        const float d = a - b;
        if (range >= d) /* comiss range, d; jb */
            return 0;
    }
    return 1;
}

static int walk_view(const mu_terrain_scene *scene, int32_t pass, const mu_terrain_frustum *f, int32_t scene_state,
                     int top_view, const mu_terrain_sink *sink, mu_terrain_tile_stats *stats)
{
    int worst = MU_TERRAIN_OK;
    float by = (float)f->y_min;
    for (int32_t y = f->y_min; y <= f->y_max; y += 4, by = by + 4.0f) {
        float bx = (float)f->x_min;
        for (int32_t x = f->x_min; x <= f->x_max; x += 4, bx = bx + 4.0f) {
            if (!mu_terrain_test_frustum_2d(f->x2d, f->y2d, scene_state, bx + 2.0f, by + 2.0f, -80.0f) && !top_view)
                continue;
            float ty = by;
            for (int32_t j = 0; j < 4; ++j) {
                float tx = bx;
                for (int32_t i = 0; i < 4; ++i) {
                    if (mu_terrain_test_frustum_2d(f->x2d, f->y2d, scene_state, tx + 0.5f, ty + 0.5f, 0.0f) ||
                        top_view) {
                        int status = mu_terrain_draw_tile(scene, pass, tx, ty, x + i, y + j, sink, stats);
                        if (status > worst)
                            worst = status;
                    }
                    tx = tx + 1.0f;
                }
                ty = ty + 1.0f;
            }
        }
    }
    return worst;
}

int mu_terrain_render(const mu_terrain_scene *scene, const mu_terrain_frustum *frustum, int32_t scene_state,
                      int top_view, int alpha_layers, const mu_terrain_sink *sink, mu_terrain_tile_stats *stats)
{
    sink->state(sink->context, MU_TERRAIN_STATE_OPAQUE, 0);
    int worst = walk_view(scene, 0, frustum, scene_state, top_view, sink, stats);
    sink->state(sink->context, MU_TERRAIN_STATE_ALPHA, 1);
    const int32_t w = scene->world_index;
    if (alpha_layers && !world_additive(w) && w != 0x5e) {
        int status = walk_view(scene, 2, frustum, scene_state, top_view, sink, stats);
        if (status > worst)
            worst = status;
    }
    return worst;
}

/* 0x016d2050 */
static int decal_tile_allowed(const mu_terrain_scene *scene, float x, float y)
{
    const int32_t i = mu_terrain_index(cvtt(x), cvtt(y));
    if (i < 0 || i >= MU_TERRAIN_CELLS)
        return 0;
    if (scene->attributes[i] & 0x200)
        return 0;
    if (scene->world_index == 0x8d && ((scene->attributes[i] & 8) || scene->layer1[i] == 0xe))
        return 0;
    return 1;
}

/* 0x016d197d with lodf = 1, lodi = 1 and no per-vertex light (the decal
 * caller passes 0): corners at x*100, y*100 (+100), z = height[index] +
 * height or z = height. */
static int decal_tile(const mu_terrain_scene *scene, float xf, float yf, const float uv[4][3], float alpha,
                      float height, int follow, int flip, const mu_terrain_sink *s)
{
    (void)alpha;
    const int32_t xi = cvtt(xf), yi = cvtt(yf);
    if (xi < 0 || yi < 0 || xi >= 0xff || yi >= 0xff)
        return 0;
    const float size = 100.0f * 1.0f;
    const float x = xf * 100.0f, y = yf * 100.0f;
    const int32_t index[4] = {mu_terrain_index(xi, yi), mu_terrain_index(xi + 1, yi), mu_terrain_index(xi + 1, yi + 1),
                              mu_terrain_index(xi, yi + 1)};
    float corner[4][3] = {{x, y, 0.0f}, {x + size, y, 0.0f}, {x + size, y + size, 0.0f}, {x, y + size, 0.0f}};
    for (int k = 0; k < 4; ++k)
        corner[k][2] = follow ? scene->height[index[k]] + height : height;
    s->begin(s->context, MU_TERRAIN_GL_TRIANGLE_FAN);
    for (int k = 0; k < 4; ++k) {
        const float u = uv[k][0];
        const float v = flip ? 1.0f - uv[k][1] : uv[k][1];
        s->texcoord(s->context, u, v);
        s->vertex(s->context, corner[k]);
    }
    s->end(s->context);
    return 1;
}

long mu_terrain_decal(const mu_terrain_scene *scene, int32_t texture, float x, float y, float size_x, float size_y,
                      const float light[3], float rotation, float alpha, float height, int follow, int flip,
                      const mu_terrain_sink *s)
{
    if (alpha == 1.0f)
        s->color3(s->context, light);
    else
        s->color4(s->context, light[0], light[1], light[2], alpha);
    const float angle[3] = {0.0f, 0.0f, rotation};
    float matrix[12];
    mu_angle_matrix(angle, matrix);
    s->bind(s->context, texture);
    const float mxf = x / 100.0f, myf = y / 100.0f;
    const int32_t mxi = cvtt(mxf), myi = cvtt(myf);
    float size = size_x >= size_y ? size_x : size_y; /* comiss; jb */
    float half = 0.5f * size;
    const float tu = ((float)mxi - mxf) + half;
    const float tv = ((float)myi - myf) + half;
    const float su = 1.0f / size, sv = 1.0f / size;
    size = (float)(cvtt(size) + 1);
    const float aspect = size_x / size_y;
    long fans = 0;
    for (float ty = -size; size >= ty; ty = ty + 1.0f) {
        for (float tx = -size; size >= tx; tx = tx + 1.0f) {
            if (!decal_tile_allowed(scene, (float)mxi + tx, (float)myi + ty))
                continue;
            float c[4][3];
            c[0][0] = (tu + tx) * su;
            c[0][1] = (tv + ty) * sv;
            c[1][0] = ((tu + tx) + 1.0f) * su;
            c[1][1] = (tv + ty) * sv;
            c[2][0] = ((tu + tx) + 1.0f) * su;
            c[2][1] = ((tv + ty) + 1.0f) * sv;
            c[3][0] = (tu + tx) * su;
            c[3][1] = ((tv + ty) + 1.0f) * sv;
            float r[4][3];
            for (int k = 0; k < 4; ++k) {
                c[k][2] = 0.0f;
                c[k][0] = c[k][0] - 0.5f;
                c[k][1] = c[k][1] - 0.5f;
                mu_vector_rotate(c[k], matrix, r[k]);
                r[k][0] = r[k][0] * aspect;
                r[k][0] = r[k][0] + 0.5f;
                r[k][1] = r[k][1] + 0.5f;
            }
            fans += decal_tile(scene, (float)mxi + tx, (float)myi + ty, (const float(*)[3])r, alpha, height, follow,
                               flip, s);
        }
    }
    return fans;
}
