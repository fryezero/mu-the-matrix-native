#ifndef MU_UI_ASSETS_H
#define MU_UI_ASSETS_H

/* Interface texture table for the native 2D layer (NATIVE-UI-001).
 *
 * mu_ui_assets_load follows LoadBitmap 0x0185baac and CGlobalBitmap::
 * LoadImage 0x00c97730: "Data\" + the client path, extension "jpg" ->
 * OpenJpeg on <stem>.OZJ, "tga" -> OpenTga on <stem>.OZT, resolved
 * case-insensitively below the game root.  Decoding and uploads run through
 * reconstructed/ui/ui_texture.c; JPEG entropy decoding uses libjpeg
 * (mu_ui_libjpeg_decode).  The table is the lookup behind mu_ui_state (the
 * client's Bitmaps.GetTexture). */

#include <stddef.h>
#include <stdint.h>

#include "../../reconstructed/ui/ui2d.h"
#include "../../reconstructed/ui/ui_texture.h"

enum { MU_UI_ASSETS_MAX = 128 };

typedef struct mu_ui_assets {
    char root[1024];
    mu_ui_bitmap bitmaps[MU_UI_ASSETS_MAX];
    int count;
    uint32_t next_texture;
    int missing, failed;
    char last_error[256];
} mu_ui_assets;

void mu_ui_assets_init(mu_ui_assets *assets, const char *game_root);
void mu_ui_assets_free(mu_ui_assets *assets);
/* Returns MU_UI_TEXTURE_LOADED/FAILED/SKIPPED, or -1 if the file is missing. */
int mu_ui_assets_load(mu_ui_assets *assets, mu_ui_state *state, const char *client_path, uint32_t index,
                      uint32_t filter, uint32_t wrap);
mu_ui_bitmap *mu_ui_assets_lookup(void *assets, uint32_t index);
/* Adds a bitmap without a file (synthetic tests); buffer is copied. */
mu_ui_bitmap *mu_ui_assets_add(mu_ui_assets *assets, mu_ui_state *state, uint32_t index, int32_t width,
                               int32_t height, const uint8_t *rgba);

/* Resolve "Data\Interface\x.OZT" below root case-insensitively. */
int mu_ui_assets_resolve(const char *root, const char *client_path, char *out, size_t out_size);

/* libjpeg decoder with the library defaults (ISLOW DCT, fancy upsampling,
 * no colour-space override), as the client's OpenJpeg calls IJG 6b. */
int mu_ui_libjpeg_decode(void *user, const uint8_t *data, size_t size, mu_ui_jpeg_image *image);
void mu_ui_libjpeg_release(void *user, mu_ui_jpeg_image *image);
int mu_ui_libjpeg_available(void);

#endif
