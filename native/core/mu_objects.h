/* Static map objects for the native port (NATIVE-OBJECTS-001,
 * docs/research/client-objects.md).
 *
 * Client rules (reconstructed/objects, instruction-compared by
 * scripts/validate_objects.py):
 *   - EncTerrain<folder>.obj: the object loader 0x016d9ac5 decodes the whole
 *     file with the v12 rolling decoder and walks version, map number, count
 *     and the version-dependent records; OpenWorld 0x0182876e accepts the
 *     file only when the map number byte equals the folder number;
 *   - object type == model index; the model file of a type comes from the
 *     model pass 0x018392db (Lorencia's named table, else
 *     Data/Object<folder>/Object<type+1>.bmd).
 *
 * BOUNDARY: the installed EncTerrain*.obj files do not decode with the
 * client's own loader instructions (OpenWorld would refuse all 84). The
 * transformation that makes them readable happens outside the captured
 * main.exe code (see the finding); mu_objects_load_installed reports
 * MU_OBJECTS_FILE_REFUSED for them. Records can also come from a decoded
 * plaintext file (mu_objects_load_plain_file, same layout after the decode)
 * or from mu_objects_gallery, a labelled demo layout that puts one object of
 * every model the world loads on the terrain. Neither is client placement.
 *
 * Rendering choices (viewer, not client readings): action 0 at frame 0, the
 * body light is the terrain's primary light at the object's tile (white for
 * the gallery, so that every model is visible), objects whose model failed to
 * load are skipped. */
#ifndef MU_OBJECTS_H
#define MU_OBJECTS_H

#include <stddef.h>
#include <stdio.h>
#include <stdint.h>

#include "../../reconstructed/objects/objects.h"
#include "../../reconstructed/objects/object_render.h"
#include "mu_bmd.h"
#include "mu_model.h"
#include "mu_raster.h"
#include "mu_terrain.h"
#include "mu_textures.h"
#include "mu_scene.h"
#include "mu_effect.h"

#define MU_OBJECT_TYPES 512

enum {
    MU_OBJECTS_FILE_OK = 0,
    MU_OBJECTS_FILE_MISSING = 1,      /* no EncTerrain<folder>.obj (the client shows "file not found") */
    MU_OBJECTS_FILE_REFUSED = 2,      /* map number byte != folder: OpenWorld shows "file corrupted" */
    MU_OBJECTS_FILE_TRUNCATED = 3,    /* count runs past the plaintext (the client would read past it) */
    MU_OBJECTS_FILE_ERROR = 4
};

typedef struct mu_object_model {
    int32_t type;
    int loaded;
    char path[1024];
    mu_bmd bmd;
    mu_model model;
    mu_textures textures;
} mu_object_model;

/* ---- NATIVE-OBJECTS-002: the client's object lifecycle (reconstructed/objects/object_render.h) ---- */

#define MU_OBJECT_PARTICLES 1024
#define MU_OBJECT_STEP_LIGHTS 1024

typedef struct mu_object_light {
    float x, y, rgb[3];
    int32_t range;
} mu_object_light;

/* Stand-in for the client's legacy particle system (CreateParticle 0x0168fafd is not
 * reconstructed): a billboard of the particle's bitmap that rises and fades over its life. */
typedef struct mu_object_particle {
    float position[3], light[3];
    int32_t bitmap, sub, life, age;
    float scale;
} mu_object_particle;

/* NATIVE-LOGIN-001: CreateSprite calls of the login world's RenderObjectVisual (one frame each; the
 * client's sprite list is redrawn and cleared by RenderSprites every frame). */
#define MU_OBJECT_SPRITES 512
#define MU_OBJECT_BITMAPS 8
typedef struct mu_object_sprite {
    int32_t bitmap;
    float position[3], scale, light[3], rotation;
} mu_object_sprite;

/* One RenderMesh call of an after-character render (login world slot 0x3c). */
typedef struct mu_object_mesh {
    mu_draw_options options;          /* mesh_plus_one, flags, alpha, blend mesh, light, uv, texture */
    mu_draw_model_fields fields;      /* model colour +0x54 at the call */
} mu_object_mesh;
struct mu_objects;
struct mu_env;

typedef struct mu_objects_runtime {
    int ready;
    struct mu_env *environment; /* optional shared boid pool for Elbeland */
    uint8_t hero_safe;
    mu_obj_event startup_effects[12];
    int32_t startup_effect_count;
    uint8_t *images;                  /* count * MU_OBJ_SIZE: client OBJECT images */
    uint8_t **pointers;
    int32_t *next;
    mu_obj_world world;               /* sector lists in creation order */
    uint8_t model_fields[MU_MDL_SIZE];
    uint32_t seed;                    /* MSVC rand state (the client's rand() is shared; seed 1 here) */
    int32_t render_counter;           /* 0x06fc9c90 */
    mu_obj_event *events;
    int32_t event_capacity;
    int32_t *draw_list, draw_count;   /* RenderObject calls of the last render pass, in order */
    mu_object_light lights[MU_OBJECT_STEP_LIGHTS];  /* AddTerrainLight calls of the last move pass */
    int32_t light_count;
    mu_object_particle particles[MU_OBJECT_PARTICLES];
    int32_t particle_count;
    mu_image fire, smoke;             /* Effect/Fire01.jpg 0x7f3c, Effect/smoke01.jpg 0x7f5a */
    float velocity[MU_OBJECT_TYPES];  /* live sidecar (.velocity) for speeds set outside CreateObject */
    uint8_t velocity_set[MU_OBJECT_TYPES];
    int32_t velocity_types;
    int32_t create_unsupported, created, outside;
    uint32_t steps;
    long ticks, moved, light_events, particle_events, sound_events, move_unsupported;
    long drawn, draw_unsupported, draw_skipped, culled;
    /* NATIVE-LOGIN-001 */
    uint32_t now_ms;                  /* timeGetTime of the step and the frame (mu_objects_set_clock) */
    float play_speed[MU_OBJECT_TYPES];   /* action 0 PlaySpeeds set by a world handler's creation hook */
    uint8_t play_speed_set[MU_OBJECT_TYPES];
    mu_object_sprite sprites[MU_OBJECT_SPRITES];
    int32_t sprite_count;
    int32_t bitmap_ids[MU_OBJECT_BITMAPS];
    mu_image bitmaps[MU_OBJECT_BITMAPS]; /* effect bitmaps of the sprites and particles, by client index */
    int32_t bitmap_count;
    int32_t *after_list, after_count; /* RenderObjects_AfterCharacter draws of the last frame */
    long sprite_events, after_meshes;
    /* NATIVE-PARTICLE-001: when set, CreateParticle calls of the move pass go to `particle` (instead of the
     * stand-in list) and RenderObjectVisual 0x017f9758 is `visual`, called by mu_objects_prepare_index after
     * RenderObject (model: the posed model, NULL when the object was not posed). */
    void (*particle)(void *context, int32_t bitmap, const float position[3], const float angle[3],
                     const float light[3], int32_t subtype, float scale, int32_t owner);
    void (*visual)(void *context, struct mu_objects *objects, int32_t index, int has_model, mu_object_model *model);
    /* NATIVE-JOINT-001: when set, the login world's CreateSprite calls (slot 0x34) go to `sprite` instead of
     * the stand-in list (owner: the object index, -1 none). */
    void (*sprite)(void *context, int32_t bitmap, const float position[3], float scale, const float light[3],
                   int32_t owner, float rotation, int32_t blend, int32_t axes);
    /* NATIVE-CHARSEL-002: the character-select world's CreateEffect calls (slot 0x34: stardr01 0x5ac, 0x59a);
     * owner: the object index, -1 none. */
    void (*effect)(void *context, int32_t type, int32_t subtype, const float position[3], const float angle[3],
                   const float light[3], int32_t owner);
    long effect_events;
    void *hook_context;
} mu_objects_runtime;

typedef struct mu_objects {
    int32_t world, folder;
    int status;                       /* MU_OBJECTS_FILE_* of the last load */
    char source[32];                  /* "installed", "plain", "gallery" */
    mu_object_header header;
    mu_object_record *records;
    int32_t count;
    mu_object_model *models[MU_OBJECT_TYPES];
    int32_t models_loaded, models_missing, types_used;
    int32_t skipped_types;            /* records whose type is outside 0..299 */
    float uniform_light;              /* > 0: body light (v, v, v) instead of the terrain light */
    uint8_t hidden_type[MU_OBJECT_TYPES]; /* types the running client marked +0x68 = -2 (not drawn) */
    int32_t hidden_types;
    mu_objects_runtime rt;            /* NATIVE-OBJECTS-002 */
} mu_objects;

void mu_objects_init(mu_objects *objects, int32_t world);
void mu_objects_free(mu_objects *objects);

/* Folder number used for EncTerrain<n>.obj: the terrain folder (OpenWorld). */
int32_t mu_objects_world_folder(int32_t world);

/* Reads Data/World<folder>/EncTerrain<folder>.obj, decodes it like the
 * client and applies OpenWorld's map-number check. Returns the
 * MU_OBJECTS_FILE_* status; records are kept only for MU_OBJECTS_FILE_OK. */
int mu_objects_load_installed(mu_objects *objects, const char *game_root, char *error, size_t error_size);
/* Records from a decoded plaintext (the bytes after the v12 decode). The map
 * number check is applied the same way. */
int mu_objects_load_plain(mu_objects *objects, const uint8_t *plain, size_t size, char *error, size_t error_size);
/* An optional sidecar next to the file (same name, extension .hidden) lists, one per line, the types whose
 * objects the running client had marked +0x68 = -2; mu_objects_place skips them (live reading, see the
 * finding). */
int mu_objects_load_plain_file(mu_objects *objects, const char *path, char *error, size_t error_size);
/* Local decoded files for several worlds: <directory>/EncTerrain<folder>.plain (the naming of
 * scripts/live_objects_to_plain.py outputs). MU_OBJECTS_FILE_MISSING when the world has none. */
int mu_objects_load_dir(mu_objects *objects, const char *directory, char *error, size_t error_size);
/* Demo layout: one record per type whose model file exists, in rows of
 * `columns` starting at tile (tile_x, tile_y), spaced `spacing` world units,
 * standing on the terrain (z from mu_world_height_at). Not client data. */
int mu_objects_gallery(mu_objects *objects, const char *game_root, const mu_world *map, int32_t tile_x, int32_t tile_y,
                       int32_t columns, float spacing, char *error, size_t error_size);

/* Loads the model of every type the records use (textures unless
 * no_textures). Missing files are counted, not fatal. */
int mu_objects_load_models(mu_objects *objects, const char *game_root, int no_textures);

/* Places object `index` (origin, angles, body scale, light) and poses and
 * skins its model. Returns the model to draw, or NULL when it has none. */
mu_object_model *mu_objects_place(mu_objects *objects, int32_t index, const mu_world *map);

/* 1 when object `index` stands inside the tile box [x0, x1] x [y0, y1] (inclusive; a viewer
 * cull, the client walks visible sectors instead). */
int mu_objects_in_box(const mu_objects *objects, int32_t index, int32_t x0, int32_t y0, int32_t x1, int32_t y1);

/* Places and draws every object inside the tile box through the mesh-draw port into a
 * software raster (textures bound per model). Returns the number drawn. */
long mu_objects_draw_raster(mu_objects *objects, const mu_world *map, mu_raster *raster, int32_t x0, int32_t y0,
                            int32_t x1, int32_t y1);

/* ---- NATIVE-OBJECTS-002 ----
 *
 * mu_objects_start builds the client OBJECT of every record with CreateObject (mu_obj_create: sector,
 * generic fields, world type defaults for Lorencia and Tormenta Island) and links the sector lists.
 * Worlds whose creation case is not reconstructed keep the generic fields and take the live sidecars
 * (.hidden types). The constructor value +0xe0 = 0.1 (alpha rate) is the live reading. */
int mu_objects_start(mu_objects *objects, const char *game_root);
void mu_objects_runtime_free(mu_objects *objects);
/* Objects whose animation frame is not 0 (they have been ticked through keys). */
int32_t mu_objects_animated(const mu_objects *objects);

typedef struct mu_objects_step_inputs {
    int32_t scene_state;              /* 0x01d1df70 (6 in the world) */
    int32_t hero_tile;                /* HeroTile 0x0b437c10 */
    float time;                       /* 0x06fce370 (ms) */
    float hero[3];
    const float *x2d, *y2d;           /* last CreateFrustrum2D polygon (Tormenta slot 0x1c) */
} mu_objects_step_inputs;

/* One logic step: MoveObjects (mu_obj_move_pass) with MoveObject for the objects it names
 * (mu_obj_move), the animation tick of each through its model (mu_model_tick), particle and
 * light events. Call after the frame light copy; the AddTerrainLight calls are kept in rt.lights
 * and applied by mu_objects_apply_lights. Advances the stand-in particles one step. */
void mu_objects_step(mu_objects *objects, const mu_objects_step_inputs *inputs);
int mu_objects_worlds_b_records(mu_objects *objects);
const char *mu_objects_worlds_b_model(int32_t world, int32_t type);

/* Re-applies the last step's AddTerrainLight calls to the frame light (after each copy). */
void mu_objects_apply_lights(const mu_objects *objects, mu_world *map);

/* RenderObjects (mu_obj_render_pass) for the frustum polygon: sector and object visibility and
 * the draw list rt.draw_list. */
void mu_objects_visibility(mu_objects *objects, const mu_terrain_frustum *frustum, int32_t scene_state);

/* RenderObject (mu_obj_render) for draw-list entry k: body light from the terrain light, pose at
 * the object's animation frame, and the RenderBody arguments in *options (flags, alpha, blend
 * mesh, blend light, uv offsets, hidden mesh). Returns the model to draw, or NULL. */
mu_object_model *mu_objects_prepare(mu_objects *objects, int32_t k, const mu_world *map, int32_t scene_state,
                                    mu_draw_options *options);

/* The same for object index i (callers that walk objects without the render pass). */
mu_object_model *mu_objects_prepare_index(mu_objects *objects, int32_t index, const mu_world *map, int32_t scene_state,
                                          mu_draw_options *options);

/* NATIVE-LIGHT-001: one JSON line per drawable object (every object RenderObject draws), posed as RenderObject
 * poses it: {"object_light": index, "type", "scale", "origin", "angles", "action", "prior_action", "frame",
 * "prior_frame", "pose_translate", "transform_translate", "light_override", "ambient", "light_scale",
 * "light_minimum", "lighting", "color": [r, g, b], "model": file, "lights": [[mesh 0 light values], ...]} (binary32 values
 * printed exactly, at most 64 values per mesh, 8 meshes). Re-runs RenderObject; diagnostics, tests and
 * scripts/validate_model_light.py. */
void mu_objects_light_report(mu_objects *objects, const mu_world *map, int32_t scene_state, FILE *out);

/* Stand-in particle quads (4 vertices each) with their draw state; bitmap 0 fire, 1 smoke.
 * Returns the vertex count written (capacity in vertices). */
uint32_t mu_objects_particle_quads(const mu_objects *objects, int32_t bitmap, const float eye[3],
                                   const float target[3], mu_fx_vertex *vertices, uint32_t capacity,
                                   mu_fx_draw_state *state);

/* Software raster: visibility, every prepared object, then the particles. Returns objects drawn. */
long mu_objects_render_raster(mu_objects *objects, const mu_world *map, mu_raster *raster,
                              const mu_terrain_frustum *frustum, int32_t scene_state, const float eye[3],
                              const float target[3]);

/* ---- NATIVE-LOGIN-001: the login world's handler in the runtime (reconstructed/objects/login_world.h) ----
 *
 * World 0x5e runs CGMLogInScene_Ex: its creation hook (types 0x26/0x36 hidden, range -428.571, the ship's
 * action PlaySpeed 0.23), move hook (scroll, pulsing blend light), custom render (+0xa), RenderObjectVisual
 * (lantern sprites, mist particles: stand-in billboards) and, after the characters, the ship's glow meshes.
 * NATIVE-CHARSEL-002: world 0x5d runs CGMCharacterScene_Ex the same way (reconstructed/objects/charsel_world.h):
 * creation (markers and emitters hidden), move (scroll, the lamps' AddTerrainLight), the custom render (the
 * after-character types, the pedestal's mesh 1), RenderObjectVisual (sprites, particles, CreateEffect through
 * rt.effect) and the after-character pass (RenderBody, the pedestal's glow mesh 0). */

/* timeGetTime for the next step and frame (the pulse of 0x00cfec8d). */
void mu_objects_set_clock(mu_objects *objects, uint32_t now_ms);
/* RenderObjects_AfterCharacter (mu_login_after_pass) for the frustum polygon: rt.after_list.
 * Worlds other than 0x5e and (NATIVE-CHARSEL-002) 0x5d: none. */
void mu_objects_after_visibility(mu_objects *objects, const mu_terrain_frustum *frustum, int32_t scene_state);
/* The after-character draw of rt.after_list[k]: the RenderObject setup (body light, pose) and the
 * world's slot 0x3c, whose RenderMesh calls (and, in world 0x5d, RenderBody calls: mesh_plus_one 0) land
 * in meshes (at most capacity). Returns the model, or NULL; *count receives the mesh calls. */
mu_object_model *mu_objects_prepare_after(mu_objects *objects, int32_t k, const mu_world *map, int32_t scene_state,
                                          mu_object_mesh *meshes, int32_t capacity, int32_t *count);
/* Stand-in billboards (sprites of this frame and particles) of bitmap table entry `slot`
 * (rt.bitmap_ids[slot]), 4 vertices each, additive. Returns the vertex count. */
uint32_t mu_objects_billboard_quads(const mu_objects *objects, int32_t slot, const float eye[3],
                                    const float target[3], mu_fx_vertex *vertices, uint32_t capacity,
                                    mu_fx_draw_state *state);
/* The client OBJECT image of object `index` (MU_OBJF_* offsets), NULL before mu_objects_start. */
uint8_t *mu_objects_object_image(mu_objects *objects, int32_t index);

/* Case-insensitive resolution of a path relative to game_root ("Data/..."). */
int mu_objects_resolve(const char *game_root, const char *relative, char *out, size_t size);

#endif
