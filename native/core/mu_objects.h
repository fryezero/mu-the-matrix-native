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
#include <stdint.h>

#include "../../reconstructed/objects/objects.h"
#include "mu_bmd.h"
#include "mu_model.h"
#include "mu_terrain.h"
#include "mu_textures.h"

#define MU_OBJECT_TYPES 300

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
int mu_objects_load_plain_file(mu_objects *objects, const char *path, char *error, size_t error_size);
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

/* Case-insensitive resolution of a path relative to game_root ("Data/..."). */
int mu_objects_resolve(const char *game_root, const char *relative, char *out, size_t size);

#endif
