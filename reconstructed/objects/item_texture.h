/* The item model loader's texture step (RENDER-ITEMS-TEX-001; docs/research/client-render-items-tex.md).
 *
 * Item models are not opened by OpenTexture 0x0181fbe9. GetModel 0x00eaa8cf loads a model index on first use from
 * its ItemModelFile record through 0x00cd558e(index, record folder +8, record file +0x10c). After the BMD opens,
 * every mesh gets IndexTexture 0x7530 and TextureType 0, then:
 *   - TextureType: _strnicmp prefix "nude_" -> 1, else "cotton2_" -> 3, else "cotton_" -> 2;
 *   - IndexTexture: _strnicmp prefixes "skin_" / "level" -> 0x7725, "hid" -> 0x791a, "hair_" -> 0x7776; strncmp
 *     "field_" -> model +0xa6 = 1, LoadImage(folder + "Texture\" + name), then LoadImage(folder + "Texture\" +
 *     name[6..] with its last four characters replaced by ".tga"), the second result dropped; _strnicmp "HQskin_"
 *     -> 0x77c7, "HQskin3" -> 0x7869, "HQskin2" -> 0x7818, "HQskin" / "HQlevel" -> 0x77c7, "HQhair_" / "HQhair"
 *     -> 0x78ba; anything else LoadImage(folder + "Texture\" + name, GL_NEAREST, GL_CLAMP) whatever its extension;
 *   - when IndexTexture is still 0x7530: the bitmap-name map (0x00c97e0c, key = the mesh name); a hit reuses that
 *     bitmap (0x00c97730(index, its file, GL_NEAREST, GL_CLAMP)) and stores its index, a miss shows
 *     "ItemTextureFile does not exist : [file - path]" and leaves 0x7530.
 * There is no model-folder, Data\Item\ or OpenTexture retry. The host type is OpenTexture's (texture_lookup.h). */
#ifndef MU_ITEM_TEXTURE_H
#define MU_ITEM_TEXTURE_H

#include <stdint.h>

#include "texture_lookup.h"

enum { MU_IT_PLAIN = 0, MU_IT_NUDE = 1, MU_IT_COTTON = 2, MU_IT_COTTON2 = 3 };

/* One mesh: returns IndexTexture. *type receives TextureType, *field is set to 1 for a field_ name (model +0xa6;
 * untouched otherwise), *step (optional) is MU_TL_DIRECT for a load or special, MU_TL_NAME_MAP for a name-map hit
 * and MU_TL_MISSING for the message. Paths are limited to the client's 256-byte buffers. A field_ name with fewer
 * than four characters after the prefix throws std::out_of_range in the client; here it returns MU_TL_DEFAULT
 * without requests and *step = 0. */
int32_t mu_it_open(const mu_tl_host *h, const char *folder, const char *name, int32_t *type, int *field, int *step);

/* RENDER-ITEMS-TEX-002: the wearer's skin. RenderCharacter's part loop (0x0136a39a..) fetches each part slot's model
 * and writes model +0xa4 = 0x0139d6a2(character +0x12 class byte) (0x0136a4a9..0x0136a4c3); the item loader leaves
 * +0xa4 = 0 (memset 0x00cd5623). The mesh draw (0x012b8e78..) binds a skin IndexTexture (0x7725, 0x7776, 0x77c7,
 * 0x7818, 0x7869, 0x78ba) plus +0xa4 (movsx); other indices are unchanged. */
int8_t mu_it_part_skin(uint8_t class_byte);
int32_t mu_it_skin_bitmap(int32_t index_texture, int8_t skin);

#endif
