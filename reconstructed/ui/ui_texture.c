/* Reconstructed interface texture decoders (NATIVE-UI-001).  See ui_texture.h. */
#include "ui_texture.h"

#include <stdlib.h>
#include <string.h>

#define GL_TEXTURE_2D 0x0de1u

static void emit(mu_ui_state *state, int op, const uint32_t *words, int count, const void *data, size_t bytes)
{
    if (state->sink.call)
        state->sink.call(state->sink.user, op, words, count, data, bytes);
}

int32_t mu_ui_texture_size(int32_t n)
{
    int32_t i, size = 0;
    for (i = 1; i <= 0x400; i <<= 1) {
        size = i;
        if (i >= n)
            break;
    }
    return size;
}

int mu_ui_texture_keeps_buffer(uint32_t index, int jpeg)
{
    if (index == 0x7532 || index == 0x7def || index == 0x7bd1)
        return 1;
    return jpeg && index > 0x851a && index < 0x851c;
}

static void upload(mu_ui_state *state, mu_ui_bitmap *bitmap, uint32_t filter, uint32_t wrap, int rgba)
{
    uint32_t gen = 1;
    uint32_t bind[2] = {GL_TEXTURE_2D, bitmap->texture};
    uint32_t image[9] = {GL_TEXTURE_2D, 0, rgba ? 4u : 3u, (uint32_t)(int32_t)bitmap->width,
                         (uint32_t)(int32_t)bitmap->height, 0, rgba ? 0x1908u : 0x1907u, 0x1401, 0};
    uint32_t parameter[3] = {GL_TEXTURE_2D, 0, 0};
    size_t bytes = (size_t)(int32_t)bitmap->width * (size_t)(int32_t)bitmap->height * bitmap->components;
    emit(state, MU_GL_GENTEXTURES, &gen, 1, NULL, 0);
    emit(state, MU_GL_BINDTEXTURE, bind, 2, NULL, 0);
    emit(state, MU_GL_TEXIMAGE2D, image, 9, bitmap->buffer, bytes);
    if (rgba) {
        float modulate = 8448.0f;
        uint32_t env[3] = {0x2300, 0x2200, 0};
        memcpy(&env[2], &modulate, 4);
        emit(state, MU_GL_TEXENVF, env, 3, NULL, 0);
    }
    parameter[1] = 0x2800; parameter[2] = filter;
    emit(state, MU_GL_TEXPARAMETERI, parameter, 3, NULL, 0);
    parameter[1] = 0x2801;
    emit(state, MU_GL_TEXPARAMETERI, parameter, 3, NULL, 0);
    parameter[1] = 0x2802; parameter[2] = wrap;
    emit(state, MU_GL_TEXPARAMETERI, parameter, 3, NULL, 0);
    parameter[1] = 0x2803;
    emit(state, MU_GL_TEXPARAMETERI, parameter, 3, NULL, 0);
}

int mu_ui_open_tga(mu_ui_state *state, const uint8_t *file, size_t size, uint32_t index, uint32_t filter,
                   uint32_t wrap, uint32_t texture_name, mu_ui_bitmap *bitmap)
{
    int16_t width, height;
    int8_t bits;
    int32_t texture_w, texture_h, row, column;
    size_t source, buffer_bytes;
    uint8_t *buffer;
    if (size < 22)
        return MU_UI_TEXTURE_FAILED;
    memcpy(&width, file + 16, 2);
    memcpy(&height, file + 18, 2);
    bits = (int8_t)file[20];
    if (bits != 0x20 || width > 0x400 || height > 0x400)
        return MU_UI_TEXTURE_FAILED;
    if (width > 0 && height > 0 && (size_t)22 + (size_t)width * (size_t)height * 4 > size)
        return MU_UI_TEXTURE_FAILED;    /* client: out-of-bounds heap read */
    texture_w = mu_ui_texture_size(width);
    texture_h = mu_ui_texture_size(height);
    buffer_bytes = (size_t)texture_w * (size_t)texture_h * 4;
    buffer = calloc(buffer_bytes, 1);
    if (!buffer)
        return MU_UI_TEXTURE_FAILED;
    memset(bitmap, 0, sizeof *bitmap);
    bitmap->index = index;
    bitmap->width = (float)texture_w;
    bitmap->height = (float)texture_h;
    bitmap->components = 4;
    bitmap->image_width = width;
    bitmap->image_height = height;
    bitmap->buffer = buffer;
    source = 22;
    for (row = 0; row < height; ++row) {
        const uint8_t *src = file + source;
        uint8_t *dst = buffer + (size_t)((height - 1 - row) * texture_w * 4);
        source += (size_t)width * 4;
        for (column = 0; column < width; ++column) {
            dst[0] = src[2];
            dst[1] = src[1];
            dst[2] = src[0];
            dst[3] = src[3];
            src += 4;
            dst += 4;
        }
    }
    bitmap->texture = texture_name;
    upload(state, bitmap, filter, wrap, 1);
    return MU_UI_TEXTURE_LOADED;
}

int mu_ui_open_jpeg(mu_ui_state *state, const uint8_t *file, size_t size, uint32_t index, uint32_t filter,
                    uint32_t wrap, uint32_t texture_name, mu_ui_jpeg_decoder decode, mu_ui_jpeg_release release,
                    void *user, mu_ui_bitmap *bitmap)
{
    mu_ui_jpeg_image image;
    int32_t texture_w, texture_h, row_stride, scanline;
    int32_t offset = 0, buffer_bytes;
    uint8_t *buffer;
    memset(&image, 0, sizeof image);
    if (!decode || !decode(user, size > 24 ? file + 24 : file + size, size > 24 ? size - 24 : 0, &image))
        return MU_UI_TEXTURE_FAILED;
    if ((uint32_t)image.width > 0x400 || (uint32_t)image.height > 0x400) {
        if (release)
            release(user, &image);
        return MU_UI_TEXTURE_SKIPPED;
    }
    texture_w = mu_ui_texture_size(image.width);
    texture_h = mu_ui_texture_size(image.height);
    buffer_bytes = texture_w * texture_h * 3;
    buffer = calloc((size_t)buffer_bytes, 1);
    if (!buffer) {
        if (release)
            release(user, &image);
        return MU_UI_TEXTURE_FAILED;
    }
    memset(bitmap, 0, sizeof *bitmap);
    bitmap->index = index;
    bitmap->width = (float)texture_w;
    bitmap->height = (float)texture_h;
    bitmap->components = 3;
    bitmap->image_width = image.width;
    bitmap->image_height = image.height;
    bitmap->buffer = buffer;
    row_stride = image.width * image.components;
    for (scanline = 0; scanline < image.height; ++scanline) {
        int32_t target = scanline * texture_w * 3, copy = row_stride;
        if (offset + row_stride > buffer_bytes)
            break;
        /* read_scanlines advances output_scanline first: row (scanline+1)-1.
         * A four-component (CMYK) row is wider than a texture row; the client
         * then writes past its buffer, the reconstruction stops at the end. */
        if (target + copy > buffer_bytes)
            copy = buffer_bytes - target;
        memcpy(buffer + target, image.pixels + (size_t)scanline * (size_t)row_stride, (size_t)copy);
        offset += row_stride;
    }
    if (release)
        release(user, &image);
    bitmap->texture = texture_name;
    upload(state, bitmap, filter, wrap, 0);
    return MU_UI_TEXTURE_LOADED;
}
