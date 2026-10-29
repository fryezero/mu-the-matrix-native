/* Item model textures as the client registers and loads them (RENDER-ITEMS-TEX-001,
 * docs/research/client-render-items-tex.md).
 *
 * Mesh textures follow the loader that opened the model:
 *  - item models with an ItemModelFile record are loaded on first use by GetModel 0x00eaa8cf through 0x00cd558e:
 *    record folder + "Texture\" + mesh name (GL_NEAREST, GL_CLAMP), then the bitmap-name map
 *    (reconstructed/objects/item_texture.h);
 *  - the special models the startup routines open (0x3890.., mu_gi_special_models) and the class parts
 *    (0x3700 + part * 0x50 + n, 0x0182bb43) use OpenTexture 0x0181fbe9 with the subfolder of their startup call
 *    ("Item\", "Monster\" for 0x38a2, "Player\");
 *  - anything else keeps the model folder (viewer choice).
 * Bitmap overrides: the body executor names client bitmaps by index (0x84d9.. rank-5 blue, 0x8239, Chrome01, ...).
 * The client registers them with LoadBitmap 0x0185baac in its startup routines; the native table
 * (mu_item_bitmaps.inc, scripts/validate_item_textures.py --emit-table) holds each index the item draws can name
 * with its path, filter and wrap. The overrides of one type are found by probing the body executor over levels,
 * options, light and time, and appended as extra bitmaps (mu_textures_add_extras). */
#ifndef MU_ITEM_TEXTURES_H
#define MU_ITEM_TEXTURES_H

#include <stdint.h>

#include "mu_bmd.h"
#include "mu_data.h"
#include "mu_textures.h"

enum { MU_ITEM_TEXTURES_REPORT = 8 };
enum { MU_ITEM_RULE_FOLDER = 0, MU_ITEM_RULE_ITEM = 1, MU_ITEM_RULE_OPEN_TEXTURE = 2 };

typedef struct mu_item_textures_stats {
    int32_t rule;              /* MU_ITEM_RULE_* */
    int32_t missing_meshes;    /* textured meshes (not a special name) left without a bitmap */
    int32_t name_map;          /* meshes answered by the name map */
    int32_t special_meshes;    /* meshes with a special name (skin, hide, hair, HQ...): the client index is kept */
    int32_t typed_meshes;      /* meshes with TextureType nude_/cotton_/cotton2_ (not applied by the mesh draw) */
    int32_t bitmaps;           /* override bitmaps the type's draws name (specials excluded) */
    int32_t missing_bitmaps;   /* of those, not registered or not installed */
    int32_t missing_index[MU_ITEM_TEXTURES_REPORT];
} mu_item_textures_stats;

/* Loads the textures of item model `type` (client model index) whose BMD was read from model_path. items may be
 * NULL (no ItemModelFile records: folder rule). stats may be NULL. Returns 0, or 1 when out of memory. */
int mu_item_textures_load(mu_textures *textures, const mu_bmd *model, const mu_data_table *items,
                          const char *game_root, int32_t type, const char *model_path, mu_item_textures_stats *stats);

/* The override bitmaps the body executor can name for `type` (probed), specials excluded; returns the count. */
int32_t mu_item_textures_overrides(int32_t type, const mu_data_table *items, int32_t *out, int32_t capacity);

/* The LoadBitmap registration of a client bitmap index: path relative to Data ("Item\texture\x.jpg"), filter and
 * wrap. Returns 0 when the index is not in the item table. */
int mu_item_bitmap_registration(int32_t index, const char **path, uint32_t *filter, uint32_t *wrap);

#endif
