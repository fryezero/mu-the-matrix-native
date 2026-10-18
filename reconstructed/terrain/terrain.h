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
 * index. Literal checks: 0x2a, 0x3f, 0x52..0x5a, 0x64, 0x65, 0x6e..0x70,
 * 0x7a..0x85. Otherwise the routine asks the current world handler
 * ([[0x01ec91b8] + 0x10], set by OpenWorld through 0x00ea468f) through its
 * vtable slot 1, which every handler class inherits from 0x00d5cbe3 (return
 * byte +4). See mu_terrain_world_handler_flag. *unresolved is always 0 now
 * (kept for the NATIVE-TERRAIN-001 signature). */
int mu_terrain_height_is_rgb(int32_t world_index, int *unresolved);

/* The world handler table built by 0x00ea488e (one shared handler object per
 * class, registered for the listed worlds): -1 when no handler is registered
 * (0x00ea2713 then returns 0), else the handler's byte +4, which the base
 * constructor 0x00d5c99f clears and only the constructors of the handlers of
 * worlds 0x86..0x91 set to 1. */
int mu_terrain_world_handler_flag(int32_t world_index);

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
    /* NATIVE-TERRAIN-002 (appended; zero = the NATIVE-TERRAIN-001 behaviour) */
    int32_t frame_counter;        /* [0x0b6b53e0]: (n + 1) % 32 per 40 ms logic step, animated layer frame */
    int (*random)(void *context); /* CRT rand() 0x01989721 for the world-0x22 water particles; NULL skips them */
    void (*effect)(void *context, int32_t type, const float position[3], const float light[3]);
    void *effect_context;         /* passed to random() and effect() */
    float hero_z;                 /* hero position z ([0x0a39d754] + 0x33ac + 8) used by those particles */
} mu_terrain_scene;

typedef struct mu_terrain_tile_stats {
    long faces, alpha_faces, grass, skipped, unsupported;
} mu_terrain_tile_stats;

/* Unported world-specific paths of 0x016cff65 / 0x016cf46c (NATIVE-TERRAIN-002
 * ported the water/lava scrolls, the per-world blend states, the additive
 * animated layer, the 0x4000 neighbour face and the world-0x22 particles):
 * bit 1 = the 0x2000 overlay faces of worlds 0x71 and 0x91 at graphics option
 * >= 4 (reported per tile as MU_TERRAIN_UNSUPPORTED), bit 2 = the Chaos
 * Castle per-face effects 0x009dc0b1 (worlds 0x12..0x17, 0x35, 0x61; effect
 * spawns only, the terrain stream is drawn). 0 for every other world. */
int mu_terrain_world_has_special_paths(int32_t world_index);

/* 0x016ccda5 followed by 0x016cff65 for one tile. pass 0 is the opaque pass
 * ([0x0b5e3ea0] = 0): one face of layer 1 (or of layer 2 when all four alpha
 * values are >= 1 and attribute bit 0x4000 is clear) with the world's UV
 * scroll and blend state, the 0x4000 neighbour face at detail >= 4, then
 * either the additive animated layer (worlds 7, 0x80..0x82, 0x85) or the
 * alpha face of layer 2 when any alpha value is > 0. pass 2 is the grass
 * pass: a GL_QUADS blade where every alpha is <= 0, grass is enabled and the
 * layer-1 grass bitmap exists. Returns MU_TERRAIN_OK, MU_TERRAIN_UNSUPPORTED
 * (nothing emitted for that part) for a 0x2000 overlay face or a missing
 * bitmap the client would dereference, or MU_TERRAIN_BAD_INDEX. */
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

/* ---------------------------------------------------------------------------
 * NATIVE-TERRAIN-002: dynamic lights, animated tiles, frustum, decals.
 * ------------------------------------------------------------------------- */

/* Light copy of the per-frame update 0x016ca4fa: frame light = primary light
 * for rows y_min..y_max+3 and columns x_min..x_max+3 of the visible box
 * (repeat indexing 0x016d34db), bit for bit. The rest of `light` is left
 * as it was (the client keeps last frame's values there). */
void mu_terrain_frame_light(const float *primary, float *light, int32_t x_min, int32_t y_min, int32_t x_max,
                            int32_t y_max);

/* AddTerrainLight 0x016cacfc(x, y, light, range, buffer): x, y in world
 * units. xf = x / 100, yf = y / 100, xi = (int)xf, yi = (int)yf; rows
 * yi-range..yi+range outer, columns xi-range..xi+range inner, with float
 * counters; lf = (range - sqrt(dx*dx + dy*dy)) / range (dx = xf - column,
 * dy = yf - row, sqrt of the widened value rounded to float, 0x00961a07);
 * where lf > 0: buffer[repeat(x, y)][k] = light[k] * lf + buffer[k], then
 * clamped below at 0 (no upper clamp). The client calls it from 204 sites
 * (objects, characters, items, effects, the selected character of the
 * character scene 0x01857a0c) between the light copy and RenderTerrain. */
void mu_terrain_add_light(float x, float y, const float light[3], int32_t range, float *buffer);

/* RenderTerrain's store to [0x0b6b4ea8] (a texture offset no routine in the
 * captured text reads): world 8 (t % 40000) * 2.5e-5f, 0x2a (t % 50000) *
 * 2e-5f, 0x5e (t % 20000) * 1e-4f, else (t % 20000) * 5e-5f, t = (int)time.
 * Only when not picking. */
float mu_terrain_water_move(int32_t world_index, float time);

/* Additive animated layer texture of RenderTerrainFace (worlds 7, 0x80..0x82
 * on layer-2 tiles 5, world 0x85 on layer-2 tiles 4): 0x7630 + 200 +
 * frame_counter, i.e. the 32 bitmaps 0x76f8 + n that the world loader
 * 0x018392db loads from Object131\wt%02d.jpg (worlds 0x80..0x82) or
 * Object8\wt%02d.jpg (every other world), GL_LINEAR/GL_REPEAT. */
int32_t mu_terrain_animated_texture(int32_t frame_counter);

/* Frustum of CreateFrustrum 0x016cba24 (aspect, position, flag). */
typedef struct mu_terrain_frustum {
    float vertex[5][3];      /* 0x0bdb5430: apex (camera) then the four far corners */
    float normal[5][3];      /* 0x0bdb546c: FaceNormalize of (0,1,2) (0,2,3) (0,3,4) (0,4,1) (3,2,1) */
    float d[5];              /* 0x0b6b53e4: -(v . n), v = vertex 0 for faces 0..3, vertex 1 for face 4 */
    int32_t x_min, y_min, x_max, y_max; /* 0x0b6b53f8, 0x0b6b53fc, 0x01cf15e0, 0x01cf15e4 */
    float x2d[4], y2d[4];    /* 0x0b6b5400, 0x0b6b5410: CreateFrustrum2D polygon in tile units */
} mu_terrain_frustum;

/* The 3D part of 0x016cba24, up to its CreateFrustrum2D call:
 *   distance = view_far * 0.9f ([0x01cf1630])
 *   width = tan(fov * 0.5f * 3.141592f / 180.0f) * distance * aspect + 100.0f
 *           (fov [0x01cf1634], tan of the widened value rounded to float)
 *   height = width * 3.0f / 4.0f
 *   corners (0,0,0), (-w, h, -d), (w, h, -d), (w, -h, -d), (-w, -h, -d)
 *   vertex[i] = VectorIRotate(corner, modelview) + camera_position
 * modelview is the 3x4 row-major matrix the client reads with
 * glGetFloatv(GL_MODELVIEW_MATRIX) (0x0184a569: m[i][j] = gl[4j + i]).
 * The bounding box of the five vertices starts at (25600, 25600, 0, 0); each
 * bound is (int)(v / 100) / 4 * 4 -+ 4 and clamped to 0..251. */
void mu_terrain_frustum_create(float aspect, float view_far, float fov, const float modelview[12],
                               const float camera_position[3], mu_terrain_frustum *frustum);

/* Distances of CreateFrustrum2D 0x016d20d9 (selected by the camera zoom
 * mode, see mu_terrain_frustum_2d_params). */
typedef struct mu_terrain_frustum_2d_params {
    float distance;        /* [ebp-0x10] */
    float near_offset;     /* [ebp-0x2c] */
    float back_offset;     /* [ebp-0x28] */
    float width_far;       /* [ebp-0x20] */
    float width_near;      /* [ebp-0x24] */
} mu_terrain_frustum_2d_params;

/* The zoom-mode switch of 0x016d20d9 ([0x0bdb5880], 0..5) for the main
 * scene (scene state 5, world not 6):
 *   mode 1..5: s = screen_width / 640.0f + 0.1f; distance 2700, 3000, 3300,
 *              3400, 3400; offsets distance * 0.19f and distance * 0.47f;
 *              widths (1200, 540), (1300, 540), (1500, 580), (1600, 660),
 *              (1600, 660) times s;
 *   mode 0:    s = camera_scale (0x0098ac7c: screen_width / 640 * [c+0xc]->+0x1c
 *              * +0x18 * [c+0x10]); distance = distance_2400 (0x0098ac45(2400.0f));
 *              offsets 0.19 / 0.47 (0.35 in world 0x3f), widths 1190*s (1900*s
 *              in 0x3f), 540*s. (Outside scene states 3 and 5 world 0x8b uses
 *              s = 5; scene state 3 never takes the 0x3f variant.)
 * Returns 0 for an unknown mode (the client then keeps zeros). */
int mu_terrain_frustum_2d_params_for(int32_t world_index, int32_t mode, int32_t screen_width, float camera_scale,
                                     float distance_2400, mu_terrain_frustum_2d_params *params);

/* The geometric part of 0x016d20d9 after the switch:
 *   wide (second argument): width_far *= 1.51f, width_near *= 1.2f
 *   lift = max(0, cos((a + camera_angle[0]) * 0.017453292f) * 10 - 9.2f) * distance,
 *          a = 71 (67 in worlds 0x86 and 0x8b), max = 0x0184f93f
 *   p0 = (-wf, (distance - back) + lift, 0), p1 = (wf, same, 0),
 *   p2 = (wn, near - back, 0),               p3 = (-wn, same, 0)
 *   angle = (0, 0, 45) (world 0x49 and the "webzen" world 6 use the camera
 *          angle instead: not reconstructed, returns MU_TERRAIN_UNSUPPORTED)
 *   x2d[i] = (VectorRotate(p_i, AngleMatrix(angle))[0] + position[0]) * 0.01f,
 *   y2d likewise with component 1.
 * The routine first re-applies the camera field of view when the camera
 * object's value differs from [0x01cf1634]; that side effect is not part of
 * this function. */
int mu_terrain_frustum_2d(int32_t world_index, const float position[3], const float camera_angle[3],
                          const mu_terrain_frustum_2d_params *params, int wide, float x2d[4], float y2d[4]);

/* TestFrustrum2D 0x016ccce7(x, y, range): 1 when scene_state ([0x01d1df70])
 * is 1..4, else for i = 0..3 with j the previous corner (3 for i = 0):
 * d = (x2d[i] - x) * (y2d[j] - y) - (x2d[j] - x) * (y2d[i] - y); returns 0 as
 * soon as range >= d (comiss), 1 after the four edges. */
int mu_terrain_test_frustum_2d(const float x2d[4], const float y2d[4], int32_t scene_state, float x, float y,
                               float range);

/* RenderTerrain 0x016cd468 (not picking) with the client's visibility:
 * blocks of 4 x 4 tiles over the frustum box, a block is walked when
 * TestFrustrum2D(bx + 2, by + 2, -80) passes or top_view ([0x0bdc58b7]) is
 * set, a tile when TestFrustrum2D(x + 0.5, y + 0.5, 0) passes or top_view.
 * Same passes and states as mu_terrain_draw. */
int mu_terrain_render(const mu_terrain_scene *scene, const mu_terrain_frustum *frustum, int32_t scene_state,
                      int top_view, int alpha_layers, const mu_terrain_sink *sink, mu_terrain_tile_stats *stats);

/* RenderTerrainAlphaBitmap 0x016cdd5f(texture, x, y, size_x, size_y, light,
 * rotation, alpha, height, follow, flip): a texture laid on the terrain
 * (shadows, magic circles, selection rings; 460 call sites). glColor3fv(light)
 * when alpha == 1 (ucomiss), else glColor4f(light, alpha); bind(texture);
 * then for every tile y, x in -n..n (float counters, n = (int)max(size_x,
 * size_y) + 1) around (int)(x / 100), (int)(y / 100) that 0x016d2050 accepts
 * (index in range, attribute bit 0x200 clear; world 0x8d also refuses bit 8
 * and layer-1 tile 14), the texture coordinates of the four tile corners,
 * rotated about (0.5, 0.5) by AngleMatrix(0, 0, rotation) and stretched by
 * size_x / size_y in u, go to 0x016d197d: one GL_TRIANGLE_FAN with corners at
 * terrain height + height (follow != 0) or at height, v flipped (1 - v) when
 * flip != 0. Returns the number of fans. */
long mu_terrain_decal(const mu_terrain_scene *scene, int32_t texture, float x, float y, float size_x, float size_y,
                      const float light[3], float rotation, float alpha, float height, int follow, int flip,
                      const mu_terrain_sink *sink);

#endif
