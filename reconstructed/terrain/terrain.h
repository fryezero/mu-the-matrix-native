#ifndef MU_TERRAIN_RECON_H
#define MU_TERRAIN_RECON_H

#include <stddef.h>
#include <stdint.h>

/* Authored C for the client's terrain loaders and tile renderer
 * (docs/research/client-terrain.md). Names are ours; each function lists the
 * client routine it follows. Arrays are the client's 256 x 256 grids, index
 * y * 256 + x, passed as explicit host pointers instead of the client's fixed
 * globals (heights 0x0b6f5420, normals 0x0b7f5430, attributes 0x0b795420,
 * layers 0x0b735420/0x0b745420, alpha 0x0b755420, light map 0x0bb75430,
 * primary light 0x0bab5430, frame light 0x0b9f5430, second light map
 * 0x0bc35430, wave 0x0b634ea8). All float work is binary32 in the client's
 * operation order unless noted; build with -ffp-contract=off.
 *
 * The client bounds nothing. These functions check sizes and indices and
 * refuse instead (an authored convention); within bounds they produce the
 * client's values. */

#define MU_TERRAIN_SIDE 256
#define MU_TERRAIN_CELLS 65536

enum {
    MU_TERRAIN_OK = 0,
    MU_TERRAIN_BAD_SIZE = 1,      /* input shorter or longer than the client accepts */
    MU_TERRAIN_CORRUPT = 2,       /* attribute header or values rejected by the client */
    MU_TERRAIN_BAD_INDEX = 3,     /* a cell index outside the grid */
    MU_TERRAIN_UNSUPPORTED = 4    /* a world- or flag-specific client path not reconstructed */
};

/* 0x016d34cd: y * 256 + x (no wrap). */
int32_t mu_terrain_index(int32_t x, int32_t y);
/* 0x016d34db: (y & 255) * 256 + (x & 255). */
int32_t mu_terrain_index_repeat(int32_t x, int32_t y);

/* 0x00976855: buffer[i] ^= key[i % 3] for 0 <= i < length (signed remainder of
 * a nonnegative index). The client's key lives at 0x01cf0448, outside the
 * captured image data; the attribute files fix it as fc cf ab (see the
 * finding). length <= 0 touches nothing. */
void mu_terrain_xor3(uint8_t *buffer, int32_t length, const uint8_t key[3]);

/* Tail of the map loader 0x016c991d after decryption: byte 0 is ignored,
 * byte 1 is the map number (returned in *map_number), then 65536 layer-1
 * bytes, 65536 layer-2 bytes and 65536 alpha bytes stored as byte / 255.0f.
 * The client reads exactly these 196,610 bytes whatever the decrypted length;
 * here a shorter input is refused. */
int mu_terrain_parse_map(const uint8_t *plain, size_t length, uint8_t *layer1, uint8_t *layer2, float *alpha,
                         int32_t *map_number);

/* Tail of the attribute loader 0x016c9da0 after decryption. length must be
 * 0x20004 (16-bit cells) or 0x10004 (8-bit cells, widened); anything else is
 * MU_TERRAIN_BAD_SIZE. The buffer is XORed in place with the three-byte key,
 * cells are copied from offset 4 and masked with 0xfaff. The result is
 * MU_TERRAIN_CORRUPT when the header is not (0, map, 255, 255) or any masked
 * cell has a low byte >= 0x80; the masked cells are written in every case, as
 * in the client. *map_number receives header byte 1. */
int mu_terrain_parse_attributes(uint8_t *plain, size_t length, const uint8_t key[3], uint16_t *attributes,
                                int32_t *map_number);

/* 0x016c8391 (the 8-bit height file): reads 65536 bytes from file offset
 * 4 + 0x438 (the BMP header is skipped by a fixed count, not parsed), row y of
 * the file is row y of the grid, and each byte is multiplied by `scale`
 * (1.5f, or 3.0f for world index 0x37). Needs size >= 4 + 0x438 + 65536. */
int mu_terrain_height_bytes(const uint8_t *file, size_t size, float scale, float *height);
float mu_terrain_height_scale(int32_t world_index);

/* 0x016c8746 (the 24-bit height file used by some worlds): from offset
 * 4 + 14 + 40, three bytes per cell, value = b2 | b1 << 8 | b0 << 16,
 * height = (float)value - 500.0f. Needs size >= 58 + 3 * 65536. */
int mu_terrain_height_rgb(const uint8_t *file, size_t size, float *height);

/* 0x016c9868: 1 when the client loads the 24-bit height file for this world
 * index. Static part only: indices 0x2a, 0x3f, 0x52..0x5a, 0x64, 0x65,
 * 0x6e..0x70, 0x7a..0x85. The routine finally asks a configuration object
 * (0x00ea594b / 0x00ea2713, a virtual call) that was not resolved; the
 * returned *unresolved is 1 when that call would decide. */
int mu_terrain_height_is_rgb(int32_t world_index, int *unresolved);

/* 0x0185b243: width and height from the BMP info header (file offsets 22 and
 * 26), then width*height pixels of three bytes from offset 58 (bfOffBits is
 * ignored), each stored as (byte2, byte1, byte0) / 255.0f. capacity is the
 * number of RGB triples available in out. */
int mu_terrain_light_bmp(const uint8_t *file, size_t size, float *out, int32_t capacity, int32_t *pixels);

/* 0x016cb624 (TerrainLight_2): the same layout and loop as
 * mu_terrain_light_bmp, stored as byte / 255.0f * 2.0f - 1.0f with the third
 * byte in component 0. The client zeroes the grid when the file is absent. */
int mu_terrain_light_offset_bmp(const uint8_t *file, size_t size, float *out, int32_t capacity, int32_t *pixels);

/* 0x00d01206: zeroes out, then the unnormalized cross product of (b - a) and
 * (c - a) in the client's order, length = (double)(float)sqrt((double)(x*x +
 * y*y + z*z)), and out[k] = (float)((double)n[k] / length) unless length ==
 * 0.0. */
void mu_terrain_face_normal(const float a[3], const float b[3], const float c[3], float out[3]);

/* 0x016c8ab6: per cell, the face normal of
 * ((x+1)*100, y*100, h(x+1, y)), ((x+1)*100, (y+1)*100, h(x+1, y+1)),
 * (x*100, (y+1)*100, h(x, y+1)) with repeat indexing. */
void mu_terrain_normals(const float *height, float *normal);

/* 0x016c8ce6: luminosity = clamp(n . L + 0.5f, 0, 1) with L = (0.5, -0.5,
 * 0.5), or (0.5, -1, 1) for world index 30; primary = light_map *
 * luminosity per channel. A NaN luminosity stays NaN. */
void mu_terrain_primary_light(const float *normal, const float *light_map, int32_t world_index, float *primary);

/* Tile corners as built by 0x016ccda5 for one tile at grid (xi, yi) and float
 * position (xf, yf):
 *   index[0] = (xi, yi), [1] = (xi+lod, yi), [2] = (xi+lod, yi+lod), [3] = (xi, yi+lod)
 *   corner k = (xf*100 (+100 for k = 1, 2), yf*100 (+100 for k = 2, 3), height[index[k]])
 *   corner k z = water_height when attributes[index[k]] & 0x40.
 * Returns 0 and builds nothing when attributes[index[0]] & 8 and not picking
 * (the client skips the tile), 1 when built, -MU_TERRAIN_BAD_INDEX when an
 * index leaves the grid (the client would read past the arrays). */
int mu_terrain_tile_corners(const uint16_t *attributes, const float *height, float water_height, float xf, float yf,
                            int32_t xi, int32_t yi, int32_t lod, int picking, int32_t index[4], float corner[12]);

/* 0x016cfd4c: texture coordinates of one face. scale = 16 when small, else
 * 64; su = scale / width, sv = scale / height; u0 = xf * su, v0 = yf * sv;
 *   uv0 = (u0 + o0, v0 + o1 + wave[i0] * k)
 *   uv1 = (u0 + su + o0, v0 + o1 + wave[i1] * k)
 *   uv2 = (u0 + su + o0, v0 + sv + o1 + wave[i1] * k)   (index 1, as in the client)
 *   uv3 = (u0 + o0, v0 + sv + o1 + wave[i0] * k)        (index 0, as in the client)
 * width and height are the bound bitmap's float fields +0x204/+0x208. */
void mu_terrain_tile_uv(float width, float height, float xf, float yf, int small, const float offset[2],
                        const float *wave, float k, const int32_t index[4], float uv[8]);

/* GL-shaped output of the tile renderer. state() reports the client's state
 * wrapper calls: MU_TERRAIN_STATE_OPAQUE is 0x0184a7f3 (blend off, cull on,
 * depth mask on, alpha test off), MU_TERRAIN_STATE_ALPHA is 0x0184a990(arg)
 * (SRC_ALPHA / ONE_MINUS_SRC_ALPHA, cull off, depth mask on when arg, alpha
 * test on), MU_TERRAIN_STATE_ADDITIVE is 0x0184aa2b (ONE / ONE, cull off,
 * depth mask off, alpha test off). bind() is the cached bind 0x0184acf6 with
 * the client's texture id. */
enum { MU_TERRAIN_STATE_OPAQUE = 1, MU_TERRAIN_STATE_ALPHA = 2, MU_TERRAIN_STATE_ADDITIVE = 3 };
enum { MU_TERRAIN_GL_TRIANGLE_FAN = 6, MU_TERRAIN_GL_QUADS = 7 };
enum { MU_TERRAIN_TEXTURE_TILE = 0x7630, MU_TERRAIN_TEXTURE_GRASS = 0x7694 };

typedef struct mu_terrain_sink {
    void *context;
    void (*state)(void *context, int32_t state, int32_t argument);
    void (*bind)(void *context, int32_t texture);
    void (*begin)(void *context, int32_t mode);
    void (*texcoord)(void *context, float s, float t);
    void (*color3)(void *context, const float rgb[3]);
    void (*color4)(void *context, float r, float g, float b, float a);
    void (*vertex)(void *context, const float xyz[3]);
    void (*end)(void *context);
} mu_terrain_sink;

/* Bitmap size lookup for a client texture id; returns 0 when the id has no
 * loaded bitmap (the client's lookup returns null). */
typedef int (*mu_terrain_texture_size)(void *context, int32_t texture, float *width, float *height);

/* Everything the tile renderer reads. light is the per-frame light grid
 * (0x0b9f5430; equal to the primary light when no dynamic light is added),
 * light2 the second light map (0x0bc35430, zero when absent). */
typedef struct mu_terrain_scene {
    int32_t world_index;          /* [0x01cf15fc], 0-based (folder number - 1) */
    const uint8_t *layer1, *layer2;
    const float *alpha;
    const uint16_t *attributes;
    const float *height;
    const float *light, *light2;
    const float *wave;            /* 65536 floats, 0x0b634ea8 */
    const float *wave2;           /* 65536 floats, 0x0b674ea8 (second sway, some worlds) */
    const float *grass_offset;    /* 256 floats used */
    const uint8_t *grass_map;     /* 65536 bytes, 1 = grass allowed */
    float water_height;           /* [0x01cf15dc] */
    float time;                   /* [0x06fce370], milliseconds */
    int32_t detail;               /* configuration value compared with 4 */
    uint8_t grass_disabled;       /* [0x0b7f5428] */
    mu_terrain_texture_size texture_size;
    void *texture_context;
} mu_terrain_scene;

typedef struct mu_terrain_tile_stats {
    long faces, alpha_faces, grass, skipped, unsupported;
} mu_terrain_tile_stats;

/* 1 when 0x016cff65 or 0x016cf46c has a world-specific branch for this world
 * index (water variants, animated or additive layers, extra faces). Those
 * branches are not reconstructed; mu_terrain_draw_tile reports them. */
int mu_terrain_world_has_special_paths(int32_t world_index);

/* 0x016ccda5 followed by 0x016cff65 for one tile, generic world path.
 * pass 0 is the opaque pass ([0x0b5e3ea0] = 0): one face of layer 1 (or of
 * layer 2 when all four alpha values are >= 1), then the alpha face of layer
 * 2 when any alpha value is > 0 and layer 1 was drawn. pass 2 is the grass
 * pass: a GL_QUADS blade where every alpha is <= 0, grass is enabled and
 * the layer-1 grass bitmap exists. Returns MU_TERRAIN_OK, or
 * MU_TERRAIN_UNSUPPORTED (nothing emitted for the unsupported part) when the
 * tile reaches a branch listed in mu_terrain_world_has_special_paths, the
 * 0x4000 neighbour face, or the additive layer-2 faces; or
 * MU_TERRAIN_BAD_INDEX. */
int mu_terrain_draw_tile(const mu_terrain_scene *scene, int32_t pass, float xf, float yf, int32_t xi, int32_t yi,
                         const mu_terrain_sink *sink, mu_terrain_tile_stats *stats);

/* 0x016cd468 with the block walk 0x016d2e8e / 0x016d2d81 and every
 * visibility test treated as passed: pass 0 under the opaque state, then (when
 * alpha layers are present and the world draws them) the alpha state with
 * depth mask and pass 2. Tiles are visited in the client's order over the
 * inclusive tile box, whose bounds the client clamps to 0..251 in steps of
 * four. Returns the worst status seen. */
int mu_terrain_draw(const mu_terrain_scene *scene, int32_t x_min, int32_t y_min, int32_t x_max, int32_t y_max,
                    int alpha_layers, const mu_terrain_sink *sink, mu_terrain_tile_stats *stats);

/* [0x01cf15d8] as set by the map loader 0x016c991d: 0 for the world indices
 * of 0x009dacb8 (0x12..0x17, 0x35, 0x61) and for 30, else 1. */
int mu_terrain_alpha_layers(int32_t world_index);

/* 0x016ceed5: grass column offsets (rand() % 4) / 4.0f for 65536 entries,
 * drawn from the supplied generator state (the client uses its CRT rand(),
 * whose seed at map load is unknown). The MSVC rand() recurrence is used:
 * state = state * 214013 + 2531011, value = (state >> 16) & 0x7fff. */
void mu_terrain_grass_offsets(uint32_t *rand_state, float *offset);

/* The wave grids of 0x016ca4fa for one frame (the light copy of the same
 * routine is the caller's). phase = ((int)time % 720000) * 0.002f, or
 * ((int)time % 36000) * 0.01f when `alternate` ([0x01ec3254]) is set; the
 * second phase is ((int)time % 36000) * 0.008f with scale 15 for worlds
 * 0x50, 0x51, 0x90, 0x6e, 0x6f, 0x8d and 0x8e. Per cell over rows y_min..
 * min(y_max+3, 255) and columns x_min..min(x_max+3, 255), x as a float
 * counter starting at x_min:
 *   world 8:            wave = sin(x*50 + phase) * 10
 *   0x50, 0x51:         wave = sin(x*50 + phase) * 10, wave2 = sin(x*50 + phase2) * 15
 *   0x39, 0x3a:         wave = sin(x*50 + phase) * 60
 *   0x6e, 0x6f:         as 0x50 (x*50)
 *   0x8d, 0x8e:         wave = sin(x*5 + phase) * 10, wave2 = sin(x*5 + phase2) * 15
 *   others:             wave = sin(x*5 + phase) * 10
 * sin is the CRT sin of the widened argument (0x009681bd -> 0x01985700),
 * here the host's binary64 sin, rounded to float. wave2 may be NULL when the
 * world does not write it. */
void mu_terrain_wave(int32_t world_index, float time, int alternate, int32_t x_min, int32_t y_min, int32_t x_max,
                     int32_t y_max, float *wave, float *wave2);

#endif
