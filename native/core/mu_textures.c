/* Per-mesh texture loading. See mu_textures.h. */
#include "mu_textures.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void mu_path_directory(const char *path, char *out, unsigned long size)
{
    const char *slash = strrchr(path, '/');
    if (!slash) {
        snprintf(out, size, ".");
        return;
    }
    size_t length = (size_t)(slash - path);
    if (length == 0)
        length = 1;
    if (length >= size)
        length = size - 1;
    memcpy(out, path, length);
    out[length] = 0;
}

int mu_textures_load(mu_textures *t, const mu_bmd *model, const char *directory)
{
    memset(t, 0, sizeof *t);
    t->count = model->mesh_count;
    t->images = calloc((size_t)(t->count ? t->count : 1), sizeof *t->images);
    t->slots = calloc((size_t)(t->count ? t->count : 1), sizeof *t->slots);
    if (!t->images || !t->slots)
        return 1;
    for (int32_t i = 0; i < t->count; ++i) {
        char path[4096], error[256];
        if (!mu_image_resolve(directory, model->meshes[i].texture, path, sizeof path) ||
            mu_image_load_file(path, &t->images[i], error, sizeof error) != MU_IMAGE_OK) {
            t->missing++;
            continue;
        }
        t->slots[i] = &t->images[i];
    }
    return 0;
}

void mu_textures_free(mu_textures *t)
{
    for (int32_t i = 0; i < t->count; ++i)
        mu_image_free(&t->images[i]);
    free(t->images);
    free(t->slots);
    memset(t, 0, sizeof *t);
}
