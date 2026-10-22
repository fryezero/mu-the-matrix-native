/* Client texture upload rules. See mu_textures.h. */
#include "mu_textures.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define GL_NEAREST_ 0x2600u
#define GL_LINEAR_ 0x2601u
#define GL_CLAMP_ 0x2900u
#define GL_REPEAT_ 0x2901u

/* LoadBitmap calls 0x01822025..0x01822705 (path, index, filter, wrap). */
const mu_texture_special mu_texture_specials[MU_TEXTURE_SPECIAL_COUNT] = {
    {0x7fcf, "Chrome02.jpg", GL_NEAREST_, GL_CLAMP_},
    {0x800b, "2.jpg", GL_LINEAR_, GL_REPEAT_},
    {0x800c, "flame_chrome.jpg", GL_LINEAR_, GL_REPEAT_},
    {0x8005, "Chrome06.jpg", GL_NEAREST_, GL_CLAMP_},
    {0x7f1f, "Chrome01.jpg", GL_LINEAR_, GL_REPEAT_},
    {0x7f66, "Shiny01.jpg", GL_LINEAR_, GL_CLAMP_},
};

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

static int fail(char *error, size_t size, const char *message)
{
    if (error && size)
        snprintf(error, size, "%s", message);
    return MU_IMAGE_ERROR;
}

/* Smallest power of two >= n, as the loaders' doubling loops (n <= 1024). */
static int32_t pot(int32_t n)
{
    int32_t p = 1;
    while (p < n)
        p <<= 1;
    return p;
}

static int padded(mu_image *out, int32_t width, int32_t height)
{
    memset(out, 0, sizeof *out);
    out->width = pot(width);
    out->height = pot(height);
    out->rgba = calloc((size_t)out->width * (size_t)out->height, 4);
    return out->rgba != NULL;
}

int mu_texture_upload_bytes(const uint8_t *data, size_t size, char kind, mu_image *image, int8_t *components,
                            char *error, size_t error_size)
{
    memset(image, 0, sizeof *image);
    *components = 0;
    if (kind == 't') {
        /* 0x00c988fc: fixed offsets from the start of the .ozt file. */
        if (size < 22)
            return fail(error, error_size, "TGA rule: file too short");
        const int32_t width = (int16_t)(data[16] | data[17] << 8), height = (int16_t)(data[18] | data[19] << 8);
        if ((int8_t)data[20] != 32 || width > 1024 || height > 1024)
            return fail(error, error_size, "TGA rule: needs 32-bit pixels and sides <= 1024");
        if (width <= 0 || height <= 0 || 22 + (size_t)width * (size_t)height * 4 > size)
            return fail(error, error_size, "TGA rule: pixel data beyond the file (the client would read past it)");
        if (!padded(image, width, height))
            return fail(error, error_size, "out of memory");
        const uint8_t *src = data + 22;
        for (int32_t y = 0; y < height; ++y) {
            uint8_t *dst = image->rgba + ((size_t)(height - 1 - y) * (size_t)image->width) * 4;
            for (int32_t x = 0; x < width; ++x, src += 4, dst += 4) {
                dst[0] = src[2];
                dst[1] = src[1];
                dst[2] = src[0];
                dst[3] = src[3];
            }
        }
        image->channels = 4;
        *components = 4;
        return MU_IMAGE_OK;
    }
    if (kind == 'j') {
        /* 0x00c982ea: fseek(24), libjpeg scanlines into rows 0..height-1. */
        if (size < 24)
            return fail(error, error_size, "JPEG rule: file too short");
        mu_image decoded;
        if (mu_image_decode_jpeg(data + 24, size - 24, &decoded, error, error_size) != MU_IMAGE_OK)
            return MU_IMAGE_ERROR;
        if (decoded.width > 1024 || decoded.height > 1024) {
            mu_image_free(&decoded);
            return fail(error, error_size, "JPEG rule: sides must be <= 1024");
        }
        if (!padded(image, decoded.width, decoded.height)) {
            mu_image_free(&decoded);
            return fail(error, error_size, "out of memory");
        }
        for (int32_t y = 0; y < decoded.height; ++y)
            for (int32_t x = 0; x < decoded.width; ++x) {
                const uint8_t *s = decoded.rgba + ((size_t)y * (size_t)decoded.width + (size_t)x) * 4;
                uint8_t *d = image->rgba + ((size_t)y * (size_t)image->width + (size_t)x) * 4;
                d[0] = s[0];
                d[1] = s[1];
                d[2] = s[2];
                d[3] = 255;
            }
        mu_image_free(&decoded);
        image->channels = 3;
        *components = 3;
        return MU_IMAGE_OK;
    }
    return fail(error, error_size, "no client loader for this texture name");
}

int mu_texture_upload_file(const char *path, char kind, mu_image *image, int8_t *components, char *error,
                           size_t error_size)
{
    FILE *f = fopen(path, "rb");
    if (!f)
        return fail(error, error_size, "cannot open texture");
    uint8_t *data = NULL;
    long length = -1;
    if (fseek(f, 0, SEEK_END) == 0)
        length = ftell(f);
    if (length < 0 || length > (64L << 20) || fseek(f, 0, SEEK_SET) != 0) {
        fclose(f);
        return fail(error, error_size, "cannot size texture");
    }
    data = malloc((size_t)length + 1);
    if (!data || fread(data, 1, (size_t)length, f) != (size_t)length) {
        free(data);
        fclose(f);
        return fail(error, error_size, "cannot read texture");
    }
    fclose(f);
    int status = mu_texture_upload_bytes(data, (size_t)length, kind, image, components, error, error_size);
    free(data);
    return status;
}

/* Character after the dot of the name's extension (the resolver tests ext[1]). */
static char kind_of(const char *name)
{
    const char *dot = strrchr(name, '.');
    if (!dot || !dot[1])
        return 0;
    char c = dot[1];
    return (char)(c >= 'A' && c <= 'Z' ? c - 'A' + 'a' : c);
}

static int allocate(mu_textures *t, int32_t model_count)
{
    memset(t, 0, sizeof *t);
    t->model_count = model_count;
    t->count = model_count + MU_TEXTURE_SPECIAL_COUNT;
    t->images = calloc((size_t)t->count, sizeof *t->images);
    t->slots = calloc((size_t)t->count, sizeof *t->slots);
    t->components = calloc((size_t)t->count, sizeof *t->components);
    t->filter = calloc((size_t)t->count, sizeof *t->filter);
    t->wrap = calloc((size_t)t->count, sizeof *t->wrap);
    return t->images && t->slots && t->components && t->filter && t->wrap;
}

int mu_textures_load_with_effects(mu_textures *t, const mu_bmd *model, const char *directory,
                                  const char *effect_directory)
{
    if (!allocate(t, model->mesh_count))
        return 1;
    for (int32_t i = 0; i < t->model_count; ++i) {
        t->filter[i] = GL_NEAREST_;
        t->wrap[i] = GL_REPEAT_;
        char path[4096], error[256];
        const char kind = kind_of(model->meshes[i].texture);
        if ((kind != 't' && kind != 'j') || !mu_image_resolve(directory, model->meshes[i].texture, path, sizeof path) ||
            mu_texture_upload_file(path, kind, &t->images[i], &t->components[i], error, sizeof error) != MU_IMAGE_OK) {
            t->missing++;
            continue;
        }
        t->slots[i] = &t->images[i];
    }
    char effects[4096];
    if (effect_directory)
        snprintf(effects, sizeof effects, "%s", effect_directory);
    else
        snprintf(effects, sizeof effects, "%s/../Effect", directory);
    for (int32_t k = 0; k < MU_TEXTURE_SPECIAL_COUNT; ++k) {
        const int32_t s = t->model_count + k;
        t->filter[s] = mu_texture_specials[k].filter;
        t->wrap[s] = mu_texture_specials[k].wrap;
        char path[4096], error[256];
        if (mu_image_resolve(effects, mu_texture_specials[k].file, path, sizeof path) &&
            mu_texture_upload_file(path, 'j', &t->images[s], &t->components[s], error, sizeof error) == MU_IMAGE_OK)
            t->slots[s] = &t->images[s];
    }
    return 0;
}

int mu_textures_load(mu_textures *t, const mu_bmd *model, const char *directory)
{
    return mu_textures_load_with_effects(t, model, directory, NULL);
}

int mu_textures_add_extras(mu_textures *t, const int32_t *index, const char *const *directories,
                           const char *const *names, int32_t count, uint32_t filter, uint32_t wrap)
{
    if (count <= 0)
        return 0;
    const int32_t total = t->count + count;
    mu_image *images = realloc(t->images, (size_t)total * sizeof *images);
    if (images)
        t->images = images;
    const mu_image **slots = realloc(t->slots, (size_t)total * sizeof *slots);
    if (slots)
        t->slots = slots;
    int8_t *components = realloc(t->components, (size_t)total * sizeof *components);
    if (components)
        t->components = components;
    uint32_t *filters = realloc(t->filter, (size_t)total * sizeof *filters);
    if (filters)
        t->filter = filters;
    uint32_t *wraps = realloc(t->wrap, (size_t)total * sizeof *wraps);
    if (wraps)
        t->wrap = wraps;
    int32_t *extra = realloc(t->extra_index, (size_t)(t->extra_count + count) * sizeof *extra);
    if (extra)
        t->extra_index = extra;
    if (!images || !slots || !components || !filters || !wraps || !extra)
        return 1;
    for (int32_t i = 0; i < t->count; ++i)   /* the images moved */
        if (t->slots[i])
            t->slots[i] = &t->images[i];
    for (int32_t j = 0; j < count; ++j) {
        const int32_t s = t->count + j;
        memset(&t->images[s], 0, sizeof t->images[s]);
        t->slots[s] = NULL;
        t->components[s] = 0;
        t->filter[s] = filter;
        t->wrap[s] = wrap;
        t->extra_index[t->extra_count + j] = index[j];
        char path[4096], error[256];
        const char kind = kind_of(names[j] ? names[j] : "");
        if (names[j] && directories[j] && (kind == 'j' || kind == 't') &&
            mu_image_resolve(directories[j], names[j], path, sizeof path) &&
            mu_texture_upload_file(path, kind, &t->images[s], &t->components[s], error, sizeof error) == MU_IMAGE_OK)
            t->slots[s] = &t->images[s];
    }
    t->count = total;
    t->extra_count += count;
    return 0;
}

void mu_textures_free(mu_textures *t)
{
    for (int32_t i = 0; i < t->count; ++i)
        mu_image_free(&t->images[i]);
    free(t->images);
    free(t->slots);
    free(t->components);
    free(t->filter);
    free(t->wrap);
    free(t->extra_index);
    memset(t, 0, sizeof *t);
}
