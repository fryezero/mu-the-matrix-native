#ifndef MU_TEXTURES_H
#define MU_TEXTURES_H

#include <stddef.h>
#include <stdint.h>

#include "mu_bmd.h"
#include "mu_image.h"

/* Model textures as the client uploads them (docs/research/client-meshdraw-exec.md,
 * "Textures"; static reading of OpenTexture 0x0181fbe9, the name resolver
 * 0x0181fead and the loaders 0x00c982ea (JPEG) / 0x00c988fc (TGA)):
 *
 *  - texture names ending in 't' (.tga) load the .ozt file with the TGA rule,
 *    names ending in 'j' (.jpg) load the .ozj file with the JPEG rule, other
 *    names give no texture;
 *  - TGA rule: width/height/depth read at file offsets 16/18/20, depth must be
 *    32 and both sides <= 1024, 32-bit BGRA pixels read raw from offset 22
 *    (ID length, colour map, RLE and the origin bit are ignored), file row y
 *    stored at memory row height-1-y, swizzled to RGBA; 4 components;
 *  - JPEG rule: libjpeg on the bytes after a 24-byte prefix, sides <= 1024,
 *    scanline y stored at memory row y; 3 components;
 *  - both copy the image into the top-left corner of a power-of-two buffer
 *    (the uninitialized client padding is zero here) and upload it with
 *    glTexImage2D level 0 (no mipmaps), GL_MODULATE;
 *  - model textures use GL_NEAREST for MIN and MAG and GL_REPEAT (1,045 of
 *    1,058 OpenTexture calls; TGA always GL_NEAREST).
 * Memory row 0 is GL's first row (texcoord t = 0).
 *
 * The six environment bitmaps bound by the mesh draw's flag group are loaded
 * from an Effect directory when one is found (best effort, never counted as
 * missing). */

enum { MU_TEXTURE_SPECIAL_COUNT = 6 };

typedef struct mu_textures {
    int32_t count;             /* model_count + MU_TEXTURE_SPECIAL_COUNT */
    int32_t model_count;       /* one per BMD texture slot (= mesh) */
    mu_image *images;          /* count entries; width 0 means missing */
    const mu_image **slots;    /* count entries, NULL for missing */
    int8_t *components;        /* 3, 4, or 0 when missing */
    uint32_t *filter;          /* GL_NEAREST / GL_LINEAR, MIN and MAG */
    uint32_t *wrap;            /* GL_REPEAT / GL_CLAMP */
    int32_t missing;           /* missing model textures */
    /* NATIVE-HELPERS-002: extra client bitmaps a model's passes name by index (after the specials; 0 = none) */
    int32_t extra_count;
    int32_t *extra_index;
} mu_textures;

/* Client bitmap index and file of each environment bitmap. */
typedef struct mu_texture_special {
    int32_t index;
    const char *file;          /* relative to the Effect directory */
    uint32_t filter, wrap;
} mu_texture_special;
extern const mu_texture_special mu_texture_specials[MU_TEXTURE_SPECIAL_COUNT];

/* Loads the model textures from `directory` and the environment bitmaps
 * from `directory`/../Effect (or `effect_directory` when not NULL). */
int mu_textures_load(mu_textures *textures, const mu_bmd *model, const char *directory);
/* Uploads an installed file into a mesh slot that mu_textures_load left empty (OpenTexture's later steps,
 * mu_texture_names). Returns 0 on success. */
int mu_textures_set_file(mu_textures *textures, const mu_bmd *model, int32_t index, const char *path);
int mu_textures_load_with_effects(mu_textures *textures, const mu_bmd *model, const char *directory,
                                  const char *effect_directory);
void mu_textures_free(mu_textures *textures);
/* NATIVE-HELPERS-002: appends client bitmaps after the specials: index[j] loaded from names[j] (the client's
 * name, .jpg / .tga, resolved to the OZJ / OZT file) in directories[j]; a missing file leaves its slot empty.
 * Returns 0, or 1 when out of memory. */
int mu_textures_add_extras(mu_textures *textures, const int32_t *index, const char *const *directories,
                           const char *const *names, int32_t count, uint32_t filter, uint32_t wrap);

/* Client upload of one wrapped file: kind 't' (TGA rule) or 'j' (JPEG rule).
 * Fills a power-of-two RGBA image (rows in upload order) and the component
 * count. */
int mu_texture_upload_file(const char *path, char kind, mu_image *image, int8_t *components, char *error,
                           size_t error_size);
int mu_texture_upload_bytes(const uint8_t *data, size_t size, char kind, mu_image *image, int8_t *components,
                            char *error, size_t error_size);

/* Directory part of a path ("." when none), written to out. */
void mu_path_directory(const char *path, char *out, unsigned long size);

#endif
