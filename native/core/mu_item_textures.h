/* Item model textures as the client registers and loads them (RENDER-ITEMS-TEX-001,
 * docs/research/client-render-items-tex.md).
 *
 * Mesh textures follow the loader that opened the model:
 *  - item models with an ItemModelFile record are loaded on first use by GetModel 0x00eaa8cf through 0x00cd558e:
 *    record folder + "Texture\" + mesh name, then the bitmap-name map (reconstructed/objects/item_texture.h); the
 *    name map also holds the files the startup LoadBitmap calls load (mu_startup_bitmaps.inc). Each slot takes the
 *    upload parameters of the bitmap it keeps (RENDER-ITEMS-TEX-002): the item loader's GL_NEAREST, GL_CLAMP, or for
 *    a name-map hit those of the bitmap's first load. The loader's TextureType, the field_ flag (+0xa6) and the
 *    wearer's skin shift (+0xa4) go to the mesh draw through mu_textures;
 *  - the special models the startup routines open (0x3890.., mu_gi_special_models) and the class parts
 *    (0x3700 + part * 0x50 + n, 0x0182bb43) use OpenTexture 0x0181fbe9 with the subfolder of their startup call
 *    ("Item\", "Monster\" for 0x38a2, "Player\");
 *  - anything else keeps the model folder (viewer choice).
 * Bitmap overrides: the body executor names client bitmaps by index (0x84d9.. rank-5 blue, 0x8239, Chrome01, ...).
 * The client registers them with LoadBitmap 0x0185baac in its startup routines; the native table
 * (mu_item_bitmaps.inc, scripts/validate_item_textures.py --emit-table) holds each index the item draws can name
 * with its path, filter and wrap. The overrides of one type are found by probing the body executor over levels,
 * options, light and time, and appended as extra bitmaps (mu_textures_add_extras).
 * Skin meshes (RENDER-ITEMS-TEX-002): a special mesh name keeps 0x7725 skin, 0x7776 hair, 0x77c7/0x7818/0x7869 HQskin
 * or 0x78ba HQhair; the mesh draw binds that index + model +0xa4. RenderCharacter writes +0xa4 =
 * mu_character_skin_index(class byte) (0x0139d6a2) into each part model it draws (0x0136a4bd), so worn armour takes
 * its wearer's class skin; a model no character has drawn keeps 0. The startup routine 0x0182a8fe registers those
 * bitmaps (mu_item_bitmaps.inc). */
#ifndef MU_ITEM_TEXTURES_H
#define MU_ITEM_TEXTURES_H

#include <stdint.h>

#include "mu_bmd.h"
#include "mu_character.h"
#include "mu_data.h"
#include "mu_textures.h"

enum { MU_ITEM_TEXTURES_REPORT = 8 };
enum { MU_ITEM_RULE_FOLDER = 0, MU_ITEM_RULE_ITEM = 1, MU_ITEM_RULE_OPEN_TEXTURE = 2 };

typedef struct mu_item_textures_stats {
    int32_t rule;              /* MU_ITEM_RULE_* */
    int32_t missing_meshes;    /* textured meshes (not a special name) left without a bitmap */
    int32_t name_map;          /* meshes answered by the name map */
    int32_t special_meshes;    /* meshes with a special name (skin, hide, hair, HQ...): the client index is kept */
    int32_t typed_meshes;      /* meshes with TextureType nude_/cotton_/cotton2_ (mu_textures.texture_type) */
    int32_t bitmaps;           /* override bitmaps the type's draws name (specials excluded) */
    int32_t missing_bitmaps;   /* of those, not registered or not installed */
    int32_t missing_index[MU_ITEM_TEXTURES_REPORT];
} mu_item_textures_stats;

/* Loads the textures of item model `type` (client model index) whose BMD was read from model_path. items may be
 * NULL (no ItemModelFile records: folder rule). stats may be NULL. Returns 0, or 1 when out of memory. */
int mu_item_textures_load(mu_textures *textures, const mu_bmd *model, const mu_data_table *items,
                          const char *game_root, int32_t type, const char *model_path, mu_item_textures_stats *stats);

/* RENDER-ITEMS-TEX-002: sets model +0xa4 to the skin index of a wearer's class byte (0x0139d6a2), as RenderCharacter
 * does for the part models it draws, and adds the skin bitmaps that index selects for the model's skin meshes.
 * _shift takes the index itself. Returns 0, or 1 when out of memory. */
int mu_item_textures_wear(mu_textures *textures, const char *game_root, uint8_t class_byte);
int mu_item_textures_wear_shift(mu_textures *textures, const char *game_root, int8_t shift);

/* RENDER-ITEMS-TEX-002: 1 for the model types RenderCharacter's part slots hold (0x0136a39a..): the helm..boots item
 * groups 7..11 (0x18e6..0x22e5) and the class parts 0x3700 + part * 0x50 + n. */
int mu_item_textures_is_part(int32_t type);

/* RENDER-ITEMS-TEX-002: for loaders that read textures from the model folder before they know the item type. When a
 * client rule applies to `type` (mu_item_textures_load's rule is not the folder), *textures is freed and replaced;
 * returns 1 then, else 0 with *textures unchanged. */
int mu_item_textures_reload(mu_textures *textures, const mu_bmd *model, const mu_data_table *items,
                            const char *game_root, int32_t type, const char *model_path);

/* RENDER-ITEMS-TEX-002: an in-world character item (hero, players, NPCs drawn as players) loaded from the model
 * folder by mu_character_set_item. Reloads it by the client rule for `type` (no change when type < 0 or the folder
 * rule applies) and, for the part slots 1..5, wears class_byte (< 0: none). Returns 0, or 1 when out of memory. */
int mu_item_textures_character(mu_character *character, int slot, const mu_data_table *items, const char *game_root,
                               int32_t type, int32_t class_byte);

/* RENDER-ITEMS-TEX-002 (native choice, for loaders that only have a model path): the model type of the first
 * ItemModelFile record whose game_root + folder + file is `path` (case-insensitive, either slash); else the class
 * part type the file name gives (Data/Player/<Part>ClassNN.bmd); -1 when neither. */
int32_t mu_item_textures_type_of_path(const mu_data_table *items, const char *game_root, const char *path);

/* The override bitmaps the body executor can name for `type` (probed), specials excluded; returns the count. */
int32_t mu_item_textures_overrides(int32_t type, const mu_data_table *items, int32_t *out, int32_t capacity);

/* The LoadBitmap registration of a client bitmap index: path relative to Data ("Item\texture\x.jpg"), filter and
 * wrap. Returns 0 when the index is not in the item table. */
int mu_item_bitmap_registration(int32_t index, const char **path, uint32_t *filter, uint32_t *wrap);

#endif
