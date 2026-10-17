#ifndef MU_TEXTURES_H
#define MU_TEXTURES_H

#include <stdint.h>

#include "mu_bmd.h"
#include "mu_image.h"

/* Per-mesh texture set for a model: each mesh's 32-byte texture name is
 * resolved next to the model file (or in an explicit directory) through
 * mu_image_resolve and decoded with mu_image_load_file. Missing or
 * undecodable textures leave a NULL entry (drawn white) and are counted. */
typedef struct mu_textures {
    int32_t count;
    mu_image *images;          /* count entries; width 0 means missing */
    const mu_image **slots;    /* count entries, NULL for missing */
    int32_t missing;
} mu_textures;

int mu_textures_load(mu_textures *textures, const mu_bmd *model, const char *directory);
void mu_textures_free(mu_textures *textures);

/* Directory part of a path ("." when none), written to out. */
void mu_path_directory(const char *path, char *out, unsigned long size);

#endif
