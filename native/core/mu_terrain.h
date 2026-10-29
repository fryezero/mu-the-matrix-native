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
#define MU_WORLD_EXTRA 8          /* other bitmaps (decal textures such as Effect\flare01.jpg 0x7ef7) */

typedef struct mu_world_report {
    int32_t folder;
    int32_t tile_folder;   /* Data/World<n> of the tile bitmaps (0x01829457) */
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
    mu_terrain_signed_grid *signed_grid;
    float *reflection_uv;
    float hero_position[3], camera_position[3];
    uint32_t terrain_random, terrain_steps;
    uint8_t chaos_state;
    float camera_shake;
    void (*terrain_effect)(void *, int32_t, const float *, const float *);
    void *terrain_effect_context;

    /* NATIVE-TERRAIN-002 */
    int32_t frame_counter;                 /* [0x0b6b53e0], animated layer frame 0..31 */
    int32_t box[4];                        /* visible box of the last frame update */
    mu_image extra[MU_WORLD_EXTRA];
    int32_t extra_id[MU_WORLD_EXTRA];
    uint8_t extra_linear[MU_WORLD_EXTRA], extra_clamp[MU_WORLD_EXTRA];
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

void mu_world_terrain_view(mu_world *world, const float hero[3], const float camera[3]);

/* Per-frame update for time t (ms): frame light = primary light (no dynamic
 * lights), wave grids of 0x016ca4fa over the whole map. */
void mu_world_frame(mu_world *world, float time);

/* Client frame order (NATIVE-TERRAIN-002): the frame update copies the
 * primary light over the visible box (0x016ca4fa, mu_terrain_frame_light) and
 * computes the waves there, light sources add to the frame light
 * (mu_terrain_add_light) and RenderTerrain draws. frame_counter follows the
 * clock at one step per 40 ms (the client's logic step), modulo 32. */
void mu_world_frame_box(mu_world *world, float time, int32_t x0, int32_t y0, int32_t x1, int32_t y1);
void mu_world_add_light(mu_world *world, float x, float y, const float rgb[3], int32_t range);

/* Loads another client bitmap under id (e.g. 0x7ef7 "Effect/flare01.jpg",
 * the most used decal texture) for decals. Returns 0 on success. */
int mu_world_load_extra(mu_world *world, const char *root, int32_t id, const char *relative, int linear, int clamp);

/* A client-like view: CreateFrustrum's box from the camera's modelview rows
 * (mu_terrain_frustum_create, aspect = screen_width / 640 as the main scene
 * passes it) and CreateFrustrum2D around `hero` with the zoom-mode table.
 * view_far and camera_angle_x are inputs the client keeps in its camera
 * module (not part of this milestone). */
int mu_world_client_frustum(const mu_world *world, const float modelview_rows[12], const float camera_position[3],
                            const float hero[3], float camera_angle_x, int32_t screen_width, int32_t zoom_mode,
                            float view_far, float fov, mu_terrain_frustum *frustum);
/* The same with CreateFrustrum2D's camera-object inputs of zoom mode 0 (NATIVE-CHARSEL-002): camera_scale =
 * 0x0098ac7c (screen_width / 640 * Distance * Z_Distance * manager scale) and distance_2400 = 0x0098ac45(2400)
 * (2400 * Distance * Z_Distance * manager scale), from the scene's camera record in scenes 3 and 5;
 * mu_world_client_frustum passes 1 and 2400. */
int mu_world_client_frustum_scaled(const mu_world *world, const float modelview_rows[12], const float camera_position[3],
                                   const float hero[3], float camera_angle_x, int32_t screen_width, int32_t zoom_mode,
                                   float view_far, float fov, float camera_scale, float distance_2400,
                                   mu_terrain_frustum *frustum);

/* Scene view for reconstructed/terrain (pointers into world). */
void mu_world_scene(mu_world *world, mu_terrain_scene *scene);

typedef struct mu_world_draw_stats {
    mu_terrain_tile_stats tiles;
    long missing_texture_binds;
} mu_world_draw_stats;

/* Draws the box (tile coordinates, inclusive, client order) into a software
 * raster frame: RenderTerrain's opaque pass, then the alpha state and the
 * grass pass when the world draws them, or Kalima's signed-grid mesh.
 * State mapping and alpha reference 0.25 follow the recovered GL setup. */
int mu_world_draw_raster(mu_world *world, mu_raster *raster, int32_t x0, int32_t y0, int32_t x1, int32_t y1,
                         mu_world_draw_stats *stats);

/* RenderTerrain with the client's frustum tests (mu_terrain_render). */
int mu_world_draw_raster_view(mu_world *world, mu_raster *raster, const mu_terrain_frustum *frustum,
                              int32_t scene_state, int top_view, mu_world_draw_stats *stats);

/* One decal (RenderTerrainAlphaBitmap) under the given wrapper state. */
long mu_world_decal_raster(mu_world *world, mu_raster *raster, int32_t texture, float x, float y, float size_x,
                           float size_y, const float rgb[3], float rotation, float alpha, float height, int follow,
                           int flip, int32_t state);

/* Looks up a loaded bitmap by client id (terrain bitmaps and extras); *clamp
 * receives 1 for GL_CLAMP loads (may be NULL). */
const mu_image *mu_world_bitmap_wrap(const mu_world *world, int32_t id, int *linear, int *clamp);
const mu_image *mu_world_bitmap(const mu_world *world, int32_t id, int *linear);

/* GL-state mapping of the three state wrappers (docs/research/client-skinning.md). */
void mu_world_state(int32_t state, int32_t argument, mu_meshdraw_state *out);

/* Height at a world position (bilinear in the tile), viewer helper. */
float mu_world_height_at(const mu_world *world, float x, float y);

#endif
