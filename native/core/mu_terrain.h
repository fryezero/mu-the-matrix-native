#ifndef MU_TERRAIN_H
#define MU_TERRAIN_H

#include <stddef.h>
#include <stdint.h>

/* Terrain of one world, laid out like the client's globals, and the client's
 * per-tile draw rules (NATIVE-TERRAIN-001, docs/research/native-terrain.md).
 *
 * Every routine below names the client routine it reconstructs. Arrays are
 * indexed y*256 + x like TERRAIN_INDEX 0x016d34cd; the repeat variant
 * 0x016d34db wraps both coordinates to 0..255. All float work is binary32 in
 * the client's operation order unless a comment names a binary64 step, so the
 * module must be built with -ffp-contract=off. Results that depend on client
 * state this module does not have (runtime world tables, the CRT random
 * sequence, the texture manager) are parameters with documented defaults. */

#define MU_TERRAIN_SIZE 256
#define MU_TERRAIN_CELLS 65536

enum { MU_TERRAIN_OK = 0, MU_TERRAIN_ERROR = 1, MU_TERRAIN_MISMATCH = 2 };

/* Attribute bits read by the renderer (word array 0x0b795420). */
#define MU_TW_NOGROUND 0x0008   /* tile not drawn (0x016ccde2) */
#define MU_TW_HEIGHT 0x0040     /* corner height replaced by the special height (0x016ccfd6) */
#define MU_TW_2000 0x2000       /* extra face in worlds 113/145 (not ported) */
#define MU_TW_LAYER1 0x4000     /* forces layer 1 and the neighbour face (0x016cffb6) */

typedef struct mu_terrain {
    int32_t world;                 /* client world index ([0x01cf15fc]) */
    uint8_t layer1[MU_TERRAIN_CELLS];   /* 0x0b735420 */
    uint8_t layer2[MU_TERRAIN_CELLS];   /* 0x0b745420 */
    float alpha[MU_TERRAIN_CELLS];      /* 0x0b755420, byte / 255.0f */
    uint16_t attribute[MU_TERRAIN_CELLS]; /* 0x0b795420, after the 0xfaff mask */
    float height[MU_TERRAIN_CELLS];     /* 0x0b6f5420 */
    float light_file[MU_TERRAIN_CELLS * 3];    /* 0x0bb75430 TerrainLight, r g b in 0..1 */
    float light_offset[MU_TERRAIN_CELLS * 3];  /* 0x0bc35430 TerrainLight_2, zero without the file */
    float normal[MU_TERRAIN_CELLS * 3];        /* 0x0b7f5430 */
    float primary_light[MU_TERRAIN_CELLS * 3]; /* 0x0bab5430 */
    float frame_light[MU_TERRAIN_CELLS * 3];   /* 0x0b9f5430, primary plus dynamic lights */
    float wind[MU_TERRAIN_CELLS];              /* 0x0b634ea8 */
    float wind2[MU_TERRAIN_CELLS];             /* 0x0b674ea8 (worlds with a second wind) */
    float grass_column[MU_TERRAIN_CELLS];      /* 0x0b5f4ea8, (rand() % 4) / 4.0f */
    uint8_t grass_mask[MU_TERRAIN_CELLS];      /* 0x0b5e4ea8, 1 = grass allowed */
    float special_height;          /* [0x01cf15dc] */
    float water_move;              /* [0x0b6b4ea8] */
    uint8_t grass_pass;            /* [0x01cf15d8]: second (grass) pass enabled */
    int32_t map_number;            /* from the .map header */
    int32_t att_number;            /* from the .att header */
} mu_terrain;

mu_terrain *mu_terrain_create(int32_t world);
void mu_terrain_destroy(mu_terrain *terrain);

/* Folder number of a world (0x018308d6): world+1 except the event-map groups
 * the routine names (Blood Castle 11..17/52 -> 12, Chaos Castle 18..23/53/97 ->
 * 19, Kalima 24..29/36 -> 25 through 0x009b0418, ...). Groups that depend on
 * runtime objects are not resolved and return world+1. */
int32_t mu_terrain_folder(int32_t world);

/* Clears layers and alpha and fills the grass column table (0x016ceed5):
 * layer1 = 0, layer2 = 0xff, alpha = 0, column[i] = (rand() % 4) / 4.0f with
 * the C remainder of a signed value. `seed` drives the MSVC rand() LCG
 * (x = x*214013 + 2531011, value = (x >> 16) & 0x7fff); the client's actual
 * seed and prior rand() calls are unknown, 1 is the CRT default. */
void mu_terrain_reset(mu_terrain *terrain, uint32_t seed);

/* ---- file formats ---- */

/* EncTerrain<N>.map (0x016c991d). "MAP\x01" + Modulus envelope (the BMD v14
 * cipher, routine 0x016ced37, decoded with model-recovery/modulus.cpp), or
 * without that prefix the v12 rolling cipher 0x0098c5f2. Plaintext: version
 * byte, map number byte, 64 KiB layer 1, 64 KiB layer 2, 64 KiB alpha bytes.
 * The client does not check the length; this reader requires at least
 * 2 + 3*65536 plaintext bytes and reports extra bytes in *extra. */
int mu_terrain_decode_map(mu_terrain *terrain, const uint8_t *file, size_t size, size_t *extra, char *error,
                          size_t error_size);

/* EncTerrain<N>.att (0x016c9da0). "ATT\x01" + Modulus envelope, or the v12
 * rolling cipher; then the three-byte XOR 0x00976855 with key FC CF AB (key
 * bytes at 0x01cf0448 are uncaptured; inferred from the plaintext structure).
 * Plaintext of 0x20004 (word attributes) or 0x10004 (byte attributes) bytes:
 * version 0, map number, width 0xff, height 0xff, attributes. Each attribute
 * is stored & 0xfaff; any low byte >= 0x80 or a bad header makes the client
 * return -1 ("file corrupted"), reported here as MU_TERRAIN_MISMATCH. */
int mu_terrain_decode_att(mu_terrain *terrain, const uint8_t *file, size_t size, char *error, size_t error_size);

/* Plaintext record of EncTerrain<N>.obj (0x016d9ac5): after the v12 rolling
 * decoder, version byte, map number byte, int16 count, then per record by
 * version: int16 type, float position[3], float angle[3], float scale,
 * (>=1) two bytes, (>=2) one byte, (>=3) float[3], (>=4) one byte,
 * (>=5) two floats. Record sizes 30, 32, 33, 45, 46, 54 bytes. */
typedef struct mu_terrain_object {
    int16_t type;
    float position[3], angle[3], scale;
    uint8_t extra1[2], extra2, extra4;
    float extra3[3], extra5[2];
} mu_terrain_object;

typedef struct mu_terrain_objects {
    int32_t version, map_number, count;
    mu_terrain_object *objects;
} mu_terrain_objects;

int32_t mu_terrain_obj_record_size(int32_t version);
/* Decodes and parses; MU_TERRAIN_MISMATCH when the decoded header does not fit
 * the file length (installed files of this build: see the finding). */
int mu_terrain_decode_obj(const uint8_t *file, size_t size, mu_terrain_objects *out, char *error,
                          size_t error_size);
void mu_terrain_objects_free(mu_terrain_objects *objects);

/* TerrainHeight.OZB, 8-bit rule 0x016c8391: the client skips 4 bytes, reads
 * 0x438 + 0x10000 bytes and takes heights from offset 0x438 of that block
 * (file offset 0x43c), row after row with no flip and without reading the BMP
 * header; height = byte * 1.5f (world 55: * 3.0f). Needs 0x1043c bytes. */
int mu_terrain_height_8bit(mu_terrain *terrain, const uint8_t *file, size_t size, char *error, size_t error_size);
/* 24-bit rule 0x016c8746: skips 4 + 14 + 40 bytes; per cell value =
 * b[2] | b[1] << 8 | b[0] << 16 converted through binary64 and then
 * height = (float)value + -500.0f. Needs 4 + 54 + 3*65536 bytes. */
int mu_terrain_height_24bit(mu_terrain *terrain, const uint8_t *file, size_t size, char *error, size_t error_size);
/* World test 0x016c9868 choosing the 24-bit loader: 1 or 0 from the literal
 * checks, -1 when the answer comes from the runtime world object
 * (0x00ea594b/0x00ea2713), which is not statically recoverable. */
int mu_terrain_world_uses_24bit_height(int32_t world);

/* TerrainLight.OZB (0x0185b243 via 0x016cb561): skips 4 bytes, reads the
 * 14-byte file header and 40-byte info header, then width*height pixels of
 * three bytes (B, G, R) from file offset 58 in file order, stored as
 * r, g, b = byte / 255.0f. Row padding and bfOffBits are ignored. */
int mu_terrain_light_ozb(mu_terrain *terrain, const uint8_t *file, size_t size, char *error, size_t error_size);
/* TerrainLight_2.OZB (0x016cb624): same layout, offset = byte / 255.0f * 2.0f
 * - 1.0f with R in component 0. Without the file the offsets are zero. */
int mu_terrain_light_offset_ozb(mu_terrain *terrain, const uint8_t *file, size_t size, char *error,
                                size_t error_size);

/* ---- derived data ---- */

/* CreateTerrainNormal 0x016c8ab6 with FaceNormalize 0x00d01206. */
void mu_terrain_normals(mu_terrain *terrain);
/* CreateTerrainLight 0x016c8ce6: light (0.5, -0.5, 0.5), world 30
 * (0.5, -1, 1); lum = clamp(n.L + 0.5, 0, 1); primary = file light * lum. */
void mu_terrain_primary_light(mu_terrain *terrain);

/* Visible tile box used by the per-frame update (client globals
 * [0x0b6b53f8], [0x0b6b53fc], [0x01cf15e0], [0x01cf15e4]). */
typedef struct mu_terrain_box {
    int32_t x0, y0, x1, y1;
} mu_terrain_box;

/* Per-frame terrain update 0x016ca4fa for the given wall-clock time in
 * milliseconds ([0x06fce370]): frame light = primary light over the box
 * grown by 3 (repeat index), then the wind table over the box grown by 3 and
 * clamped to 255. Ported branches: world 8, worlds 57/58 and the default
 * (sin(x*5 + speed) * 10 or 60). `alternate_wind` is the global [0x01ec3254]
 * selecting the faster speed. Worlds that use 0x00e18ae9, 110/111, 141..144
 * also fill wind2; those branches are ported with the predicate as a
 * parameter-free world list (see the finding). Dynamic lights are not added. */
void mu_terrain_frame(mu_terrain *terrain, float world_time, const mu_terrain_box *box, int alternate_wind);
/* Water move of RenderTerrain 0x016cd468 ([0x0b6b4ea8]). */
void mu_terrain_water_move(mu_terrain *terrain, float world_time);

/* ---- per-tile draw ---- */

/* State wrappers called by the tile routines (docs/research/client-skinning.md). */
enum {
    MU_TERRAIN_STATE_OPAQUE = 1,   /* 0x0184a7f3: blend off, cull on, depth mask on, alpha test off */
    MU_TERRAIN_STATE_ALPHA = 2,    /* 0x0184a990(1): blend SRC_ALPHA/1-SRC_ALPHA, cull off, alpha test on */
    MU_TERRAIN_STATE_ADDITIVE = 3  /* 0x0184aa2b: blend ONE/ONE, cull off, depth mask off */
};
enum { MU_TERRAIN_FAN = 6, MU_TERRAIN_QUADS = 7 };

/* GL-shaped sink: the order of calls equals the client's import calls. */
typedef struct mu_terrain_sink {
    void *context;
    void (*state)(void *context, int state);
    void (*bind)(void *context, int32_t bitmap);   /* client bitmap index, e.g. 0x7630 + tile */
    void (*begin)(void *context, int mode);
    void (*texcoord)(void *context, float s, float t);
    void (*color3fv)(void *context, const float rgb[3]);
    void (*color3f)(void *context, float r, float g, float b);
    void (*color4f)(void *context, float r, float g, float b, float a);
    void (*vertex3fv)(void *context, const float xyz[3]);
    void (*end)(void *context);
} mu_terrain_sink;

/* Texture sizes FaceTexture 0x016cfd4c divides by (bitmap +0x204/+0x208).
 * width/height <= 0 means the bitmap is absent (the grass pass then skips the
 * tile like 0x00c97ce3 returning null; a face would divide by zero in the
 * client, here it is skipped and counted). */
typedef struct mu_terrain_bitmaps {
    float width[0x200], height[0x200];   /* index = bitmap - 0x7630 */
} mu_terrain_bitmaps;

typedef struct mu_terrain_draw {
    const mu_terrain *terrain;
    const mu_terrain_bitmaps *bitmaps;
    float world_time;              /* [0x06fce370] */
    int32_t option_level;          /* [[0x01d22c7c]+0x2c]: graphics option gating the 0x4000 face */
    long faces, skipped, refused;
} mu_terrain_draw;

/* RenderTerrainTile 0x016ccda5 (lod 1, flag 0) and RenderTerrainFace
 * 0x016cff65 for pass 0 (faces) or 2 (grass), tile (xi, yi), xf = xi,
 * yf = yi. Returns 1 when something was emitted. Per-world special cases
 * that this port does not implement make the tile count as refused. */
int mu_terrain_draw_tile(mu_terrain_draw *draw, int32_t xi, int32_t yi, int pass, const mu_terrain_sink *sink);

/* Order of RenderTerrainBlock 0x016d2e8e / 0x016d2d81 over a box (4x4 blocks,
 * y outer), without the frustum tests: every tile with 0 <= xi, yi <= 254
 * inside the box is drawn (the client's box reaches 255, where indices run
 * into the next row or array; the viewer stops at 254). */
void mu_terrain_draw_pass(mu_terrain_draw *draw, const mu_terrain_box *box, int pass, const mu_terrain_sink *sink);

/* Height at a world position (bilinear over the four corners), for cameras.
 * Viewer helper, not the client's 0x016cc9e2. */
float mu_terrain_height_at(const mu_terrain *terrain, float x, float y);

/* Bitmap file names (0x01829457): file for bitmap index `bitmap` relative to
 * Data/World<folder>, e.g. "TileGrass01.jpg". Returns NULL for indices the
 * routine does not load. Worlds with replacement files (AlphaTile*, lava,
 * TileGrass01_R) follow the literal world checks; checks against runtime
 * objects use the default branch. filter receives 0x2600 (GL_NEAREST) or
 * 0x2601 (GL_LINEAR) as passed to the loader. */
const char *mu_terrain_bitmap_file(int32_t world, int32_t bitmap, char *buffer, size_t size, int32_t *filter);

#endif
