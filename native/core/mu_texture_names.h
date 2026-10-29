/* The client's bitmap-name map and OpenTexture retries for world object models (RENDER-WORLDS-G2).
 *
 * OpenTexture 0x0181fbe9 (reconstructed/objects/texture_lookup.c) looks a mesh texture up in the model's own
 * folder, then in the map of names already loaded (first load wins), then in Data/Item/ and Data/Item/Texture/.
 * When a world's objects are opened, that map holds the textures of the startup opener 0x01832af3 and of the
 * world pass's own extra models (mu_tl_startup / mu_tl_world_preloads). This module rebuilds that map from the
 * installed files, once per process for the startup part and per world for the extras, and answers the lookup
 * with an installed file path. Textures of models opened by the other startup routines, and of earlier worlds the
 * client has not released, are not in the rebuilt map. */
#ifndef MU_TEXTURE_NAMES_H
#define MU_TEXTURE_NAMES_H

#include <stddef.h>
#include <stdint.h>

/* The installed file OpenTexture(subfolder, name) uses in world `world`, as a path under game_root; *step is the
 * MU_TL_* step that found it. Returns 1 with a file, 0 when the client would use a special or no bitmap. */
int mu_texture_names_find(const char *game_root, int32_t world, const char *subfolder, const char *name,
                          char *path, size_t size, int *step);

/* Item models (RENDER-ITEMS-TEX-001): the same map as it stands (the startup part is built on first use; the
 * current world's extras are kept). With folder (an ItemModelFile record folder, "Data\Item\") the item loader's
 * step mu_it_open runs, *type receiving the mesh's TextureType; otherwise OpenTexture with subfolder. Returns 1 with
 * the installed file, 0 for a special (*special = its index, else 0) or missing bitmap; *step as
 * mu_texture_names_find. */
/* RENDER-ITEMS-TEX-002: the upload parameters of the bitmap an item mesh keeps (those of its first load: a name-map
 * hit keeps the startup LoadBitmap's or the first model's, a load by the item loader 0x00cd558e has GL_NEAREST,
 * GL_CLAMP) and the field_ flag (model +0xa6). */
typedef struct mu_texture_names_upload {
    uint32_t filter, wrap;     /* 0 when no file answers */
    int field;
} mu_texture_names_upload;
int mu_texture_names_item(const char *game_root, const char *folder, const char *subfolder, const char *name,
                          char *path, size_t size, int32_t *type, int32_t *special, int *step,
                          mu_texture_names_upload *upload);

/* Counters of the rebuilt map (tests and reports). */
typedef struct mu_texture_names_stats {
    int32_t names;            /* map entries */
    int32_t startup_models;   /* startup models decoded */
    int32_t world_models;     /* the current world's extra models decoded */
    int32_t world;
} mu_texture_names_stats;
void mu_texture_names_get_stats(mu_texture_names_stats *out);

/* Drops the rebuilt map (tests). */
void mu_texture_names_reset(void);

#endif
