/* Interface texture table.  See mu_ui_assets.h. */
#include "mu_ui_assets.h"

#include <ctype.h>
#include <dirent.h>
#include <setjmp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>

#if MU_HAVE_JPEG
#include <jpeglib.h>
#endif

void mu_ui_assets_init(mu_ui_assets *assets, const char *game_root)
{
    memset(assets, 0, sizeof *assets);
    snprintf(assets->root, sizeof assets->root, "%s", game_root ? game_root : ".");
    assets->next_texture = 1;
}

void mu_ui_assets_free(mu_ui_assets *assets)
{
    for (int i = 0; i < assets->count; ++i)
        free(assets->bitmaps[i].buffer);
    assets->count = 0;
}

mu_ui_bitmap *mu_ui_assets_lookup(void *user, uint32_t index)
{
    mu_ui_assets *assets = user;
    for (int i = 0; i < assets->count; ++i)
        if (assets->bitmaps[i].index == index)
            return &assets->bitmaps[i];
    return NULL;
}

static mu_ui_bitmap *slot(mu_ui_assets *assets, uint32_t index)
{
    mu_ui_bitmap *existing = mu_ui_assets_lookup(assets, index);
    if (existing) {
        free(existing->buffer);
        existing->buffer = NULL;
        return existing;
    }
    if (assets->count >= MU_UI_ASSETS_MAX)
        return NULL;
    return &assets->bitmaps[assets->count++];
}

/* Find `name` in directory `dir` ignoring case; writes the joined path. */
static int match_entry(const char *dir, const char *name, char *out, size_t out_size)
{
    DIR *d = opendir(dir);
    struct dirent *entry;
    if (!d)
        return 0;
    while ((entry = readdir(d)) != NULL) {
        if (!strcasecmp(entry->d_name, name)) {
            snprintf(out, out_size, "%s/%s", dir, entry->d_name);
            closedir(d);
            return 1;
        }
    }
    closedir(d);
    return 0;
}

int mu_ui_assets_resolve(const char *root, const char *client_path, char *out, size_t out_size)
{
    char current[2048], next[2048], part[512];
    const char *p = client_path;
    snprintf(current, sizeof current, "%s", root);
    while (*p) {
        size_t n = 0;
        while (*p && *p != '\\' && *p != '/' && n + 1 < sizeof part)
            part[n++] = *p++;
        part[n] = 0;
        while (*p == '\\' || *p == '/')
            ++p;
        if (!n)
            continue;
        if (!match_entry(current, part, next, sizeof next))
            return 0;
        snprintf(current, sizeof current, "%s", next);
    }
    snprintf(out, out_size, "%s", current);
    return 1;
}

static uint8_t *read_file(const char *path, size_t *size)
{
    FILE *f = fopen(path, "rb");
    uint8_t *data;
    long n;
    if (!f)
        return NULL;
    if (fseek(f, 0, SEEK_END) || (n = ftell(f)) < 0 || fseek(f, 0, SEEK_SET)) {
        fclose(f);
        return NULL;
    }
    data = malloc((size_t)n + 1);
    if (data && fread(data, 1, (size_t)n, f) != (size_t)n) {
        free(data);
        data = NULL;
    }
    fclose(f);
    *size = (size_t)n;
    return data;
}

int mu_ui_assets_load(mu_ui_assets *assets, mu_ui_state *state, const char *client_path, uint32_t index,
                      uint32_t filter, uint32_t wrap)
{
    char path[1100], wrapped[1100], resolved[2048];
    const char *dot;
    int jpeg;
    size_t size = 0;
    uint8_t *data;
    mu_ui_bitmap loaded;
    int result;
    snprintf(path, sizeof path, "Data\\%s", client_path);
    dot = strrchr(path, '.');
    if (!dot)
        return MU_UI_TEXTURE_FAILED;
    if (!strcasecmp(dot + 1, "jpg"))
        jpeg = 1;
    else if (!strcasecmp(dot + 1, "tga"))
        jpeg = 0;
    else
        return MU_UI_TEXTURE_FAILED;           /* LoadImage accepts only these two */
    snprintf(wrapped, sizeof wrapped, "%.*s.%s", (int)(dot - path), path, jpeg ? "OZJ" : "OZT");
    if (!mu_ui_assets_resolve(assets->root, wrapped, resolved, sizeof resolved)) {
        ++assets->missing;
        snprintf(assets->last_error, sizeof assets->last_error, "missing %s", wrapped);
        return -1;
    }
    data = read_file(resolved, &size);
    if (!data)
        return -1;
    memset(&loaded, 0, sizeof loaded);
    if (jpeg)
        result = mu_ui_open_jpeg(state, data, size, index, filter, wrap, assets->next_texture, mu_ui_libjpeg_decode,
                                 mu_ui_libjpeg_release, NULL, &loaded);
    else
        result = mu_ui_open_tga(state, data, size, index, filter, wrap, assets->next_texture, &loaded);
    free(data);
    if (result == MU_UI_TEXTURE_LOADED) {
        mu_ui_bitmap *target = slot(assets, index);
        if (!target) {
            free(loaded.buffer);
            return MU_UI_TEXTURE_FAILED;
        }
        ++assets->next_texture;
        if (!mu_ui_texture_keeps_buffer(index, jpeg)) {
            free(loaded.buffer);
            loaded.buffer = NULL;
        }
        *target = loaded;
    } else if (result == MU_UI_TEXTURE_FAILED) {
        ++assets->failed;
        snprintf(assets->last_error, sizeof assets->last_error, "decoder refused %s", wrapped);
    }
    return result;
}

mu_ui_bitmap *mu_ui_assets_add(mu_ui_assets *assets, mu_ui_state *state, uint32_t index, int32_t width,
                               int32_t height, const uint8_t *rgba)
{
    mu_ui_bitmap *target = slot(assets, index);
    size_t bytes = (size_t)width * (size_t)height * 4;
    uint32_t words[9] = {0x0de1, 0, 4, (uint32_t)width, (uint32_t)height, 0, 0x1908, 0x1401, 0};
    uint32_t bind[2] = {0x0de1, 0};
    if (!target)
        return NULL;
    memset(target, 0, sizeof *target);
    target->index = index;
    target->width = (float)width;
    target->height = (float)height;
    target->image_width = width;
    target->image_height = height;
    target->components = 4;
    target->texture = assets->next_texture++;
    target->buffer = malloc(bytes);
    if (target->buffer && rgba)
        memcpy(target->buffer, rgba, bytes);
    else if (target->buffer)
        memset(target->buffer, 0, bytes);
    bind[1] = target->texture;
    if (state->sink.call) {
        state->sink.call(state->sink.user, MU_GL_BINDTEXTURE, bind, 2, NULL, 0);
        state->sink.call(state->sink.user, MU_GL_TEXIMAGE2D, words, 9, target->buffer, bytes);
    }
    return target;
}

/* ---- libjpeg ------------------------------------------------------------ */

#if MU_HAVE_JPEG
typedef struct jpeg_failure {
    struct jpeg_error_mgr manager;
    jmp_buf jump;
} jpeg_failure;

static void jpeg_exit(j_common_ptr info)
{
    jpeg_failure *failure = (jpeg_failure *)(void *)info->err;
    longjmp(failure->jump, 1);
}

static void jpeg_silent(j_common_ptr info, int level)
{
    (void)info;
    (void)level;
}
#endif

int mu_ui_libjpeg_available(void)
{
    return MU_HAVE_JPEG ? 1 : 0;
}

int mu_ui_libjpeg_decode(void *user, const uint8_t *data, size_t size, mu_ui_jpeg_image *image)
{
    (void)user;
    memset(image, 0, sizeof *image);
#if MU_HAVE_JPEG
    struct jpeg_decompress_struct info;
    jpeg_failure failure;
    uint8_t *volatile pixels = NULL;
    if (size == 0)
        return 0;
    info.err = jpeg_std_error(&failure.manager);
    failure.manager.error_exit = jpeg_exit;
    failure.manager.emit_message = jpeg_silent;
    if (setjmp(failure.jump)) {
        jpeg_destroy_decompress(&info);
        free(pixels);
        memset(image, 0, sizeof *image);
        return 0;
    }
    jpeg_create_decompress(&info);
    jpeg_mem_src(&info, (unsigned char *)(uintptr_t)data, (unsigned long)size);
    jpeg_read_header(&info, TRUE);
    jpeg_start_decompress(&info);
    image->width = (int32_t)info.output_width;
    image->height = (int32_t)info.output_height;
    image->components = info.output_components;
    if (info.output_width > 0x400 || info.output_height > 0x400) {
        /* the client stops here (returns true without a bitmap) */
        jpeg_destroy_decompress(&info);
        return 1;
    }
    size_t stride = (size_t)info.output_width * (size_t)info.output_components;
    pixels = malloc(stride * info.output_height + 1);
    if (!pixels)
        longjmp(failure.jump, 1);
    while (info.output_scanline < info.output_height) {
        JSAMPROW rows[1] = {pixels + stride * info.output_scanline};
        jpeg_read_scanlines(&info, rows, 1);
    }
    jpeg_finish_decompress(&info);
    jpeg_destroy_decompress(&info);
    image->pixels = pixels;
    return 1;
#else
    (void)data;
    (void)size;
    return 0;
#endif
}

void mu_ui_libjpeg_release(void *user, mu_ui_jpeg_image *image)
{
    (void)user;
    free(image->pixels);
    image->pixels = NULL;
}
