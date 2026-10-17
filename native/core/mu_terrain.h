#ifndef MU_TERRAIN_NATIVE_H
#define MU_TERRAIN_NATIVE_H

#include <stddef.h>
#include <stdint.h>

#include "../../reconstructed/terrain/terrain.h"
#include "mu_image.h"
#include "mu_raster.h"

/* World loading and rendering for the native viewer (NATIVE-TERRAIN-001).
 *
 * The client rules live in reconstructed/terrain (instruction-compared, see
 * docs/research/client-terrain.md). This layer adds what the client does
 * through its file system and texture manager: it decrypts the installed
 * files, resolves the tile bitmaps of the world folder, keeps the 256 x 256
 * grids in one place and adapts the GL-shaped tile stream to the software
 * rasterizer (here) or OpenGL (viewer/). */

#define MU_WORLD_BITMAPS 0x200   /* bitmap ids 0x7630 .. 0x782f */

typedef struct mu_world_report {
    int32_t folder;
    int map_status, att_status, height_status, light_status, light2_status, obj_status;
    int32_t map_number, att_number;
    size_t att_plain_bytes;
    int height_rgb, height_rgb_unresolved;
    int32_t obj_version, obj_count;
    int32_t bitmaps_loaded, bitmaps_missing;
} mu_world_report;

typedef struct mu_world {
    int32_t world;                         /* client world index (folder - 1 for ordinary worlds) */
    uint8_t layer1[MU_TERRAIN_CELLS], layer2[MU_TERRAIN_CELLS];
    float alpha[MU_TERRAIN_CELLS];
    uint16_t attributes[MU_TERRAIN_CELLS];
    float height[MU_TERRAIN_CELLS];
    float light_map[3 * MU_TERRAIN_CELLS], light2[3 * MU_TERRAIN_CELLS];
    float normal[3 * MU_TERRAIN_CELLS], primary[3 * MU_TERRAIN_CELLS], light[3 * MU_TERRAIN_CELLS];
    float wave[MU_TERRAIN_CELLS], wave2[MU_TERRAIN_CELLS];
    float grass_offset[MU_TERRAIN_CELLS];
    uint8_t grass_map[MU_TERRAIN_CELLS];
    float water_height, time;
    int32_t detail;
    mu_image bitmaps[MU_WORLD_BITMAPS];    /* width 0 = not loaded */
    uint8_t bitmap_linear[MU_WORLD_BITMAPS];
    mu_world_report report;
} mu_world;

/* Folder number Data/World<n> of a world index (0x018308d6, literal groups
 * only: Blood Castle -> 12, Chaos Castle -> 19, Kalima 0x009b0418 -> 25,
 * else world + 1). */
int32_t mu_world_folder(int32_t world);

/* File name (relative to Data/World<folder>, client spelling, e.g.
 * "TileGrass01.jpg") of a terrain bitmap id as loaded by 0x01829457, or NULL.
 * *linear receives 1 for the GL_LINEAR (0x2601) loads, 0 for GL_NEAREST. */
const char *mu_world_bitmap_file(int32_t world, int32_t bitmap, char *buffer, size_t size, int *linear);

/* Decrypts an EncTerrain .map/.att file: "MAP\x01"/"ATT\x01" + Modulus
 * envelope (the BMD v14 cipher), otherwise the v12 rolling cipher. Returns a
 * malloc'ed plaintext and its length, or NULL. */
uint8_t *mu_world_decrypt(const uint8_t *file, size_t size, const char magic[4], size_t *plain_size, char *error,
                          size_t error_size);

/* Loads Data/World<folder> of world index `world` under root (the game
 * directory containing Data/). textures = 0 skips bitmap decoding. The grass
 * column table uses the MSVC rand() recurrence from `seed` (client seed
 * unknown). Returns NULL with a message when the .map, .att or height file is
 * missing or refused. */
mu_world *mu_world_load(const char *root, int32_t world, uint32_t seed, int textures, char *error, size_t error_size);
void mu_world_free(mu_world *world);

/* Per-frame update for time t (ms): frame light = primary light (no dynamic
 * lights), wave grids of 0x016ca4fa over the whole map. */
void mu_world_frame(mu_world *world, float time);

/* Scene view for reconstructed/terrain (pointers into world). */
void mu_world_scene(mu_world *world, mu_terrain_scene *scene);

typedef struct mu_world_draw_stats {
    mu_terrain_tile_stats tiles;
    long missing_texture_binds;
} mu_world_draw_stats;

/* Draws the box (tile coordinates, inclusive, client order) into a software
 * raster frame: RenderTerrain's opaque pass, then the alpha state and the
 * grass pass when the world draws them. State mapping and the alpha
 * reference (0.25) are viewer choices for what the client sets elsewhere. */
int mu_world_draw_raster(mu_world *world, mu_raster *raster, int32_t x0, int32_t y0, int32_t x1, int32_t y1,
                         mu_world_draw_stats *stats);

/* GL-state mapping of the three state wrappers (docs/research/client-skinning.md). */
void mu_world_state(int32_t state, int32_t argument, mu_meshdraw_state *out);

/* Height at a world position (bilinear in the tile), viewer helper. */
float mu_world_height_at(const mu_world *world, float x, float y);

#endif
