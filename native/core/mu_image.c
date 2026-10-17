/* Texture loading for the native viewer. See mu_image.h. */
#define _POSIX_C_SOURCE 200809L /* lstat, opendir, strdup with -std=c11 on glibc */
#include "mu_image.h"

#include <ctype.h>
#include <dirent.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#if MU_HAVE_JPEG
#include <setjmp.h>
#include <jpeglib.h>
#endif

static int image_error(char *error, size_t size, const char *format, ...)
{
    if (error && size) {
        va_list list;
        va_start(list, format);
        vsnprintf(error, size, format, list);
        va_end(list);
    }
    return MU_IMAGE_ERROR;
}

static uint32_t le16(const uint8_t *p) { return (uint32_t)(p[0] | (p[1] << 8)); }
static uint32_t le32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

void mu_image_free(mu_image *image)
{
    if (image) {
        free(image->rgba);
        memset(image, 0, sizeof *image);
    }
}

static int allocate(mu_image *image, int32_t width, int32_t height, char *error, size_t size)
{
    if (width <= 0 || height <= 0 || width > 16384 || height > 16384)
        return image_error(error, size, "Image dimensions outside supported limits");
    image->width = width;
    image->height = height;
    image->rgba = malloc((size_t)width * (size_t)height * 4);
    if (!image->rgba)
        return image_error(error, size, "Out of memory");
    return MU_IMAGE_OK;
}

int mu_image_decode_tga(const uint8_t *data, size_t size, mu_image *image, char *error, size_t error_size)
{
    memset(image, 0, sizeof *image);
    if (size < 18)
        return image_error(error, error_size, "Truncated TGA header");
    unsigned id_length = data[0], colormap_type = data[1], type = data[2];
    unsigned map_first = le16(data + 3), map_length = le16(data + 5), map_depth = data[7];
    int32_t width = (int32_t)le16(data + 12), height = (int32_t)le16(data + 14);
    unsigned depth = data[16], descriptor = data[17];
    if (colormap_type > 1 || !(type == 1 || type == 2 || type == 3 || type == 9 || type == 10 || type == 11))
        return image_error(error, error_size, "Unsupported TGA type %u", type);
    if (descriptor & 0xc0)
        return image_error(error, error_size, "Interleaved TGA not supported");
    const int mapped = type == 1 || type == 9, grey = type == 3 || type == 11, rle = type >= 9;
    if ((mapped && depth != 8) || (grey && depth != 8) || (!mapped && !grey && depth != 16 && depth != 24 && depth != 32))
        return image_error(error, error_size, "Unsupported TGA depth %u", depth);
    size_t offset = 18 + id_length;
    const uint8_t *palette = NULL;
    unsigned map_bytes = (map_depth + 7) / 8;
    if (colormap_type) {
        if (map_depth != 15 && map_depth != 16 && map_depth != 24 && map_depth != 32)
            return image_error(error, error_size, "Unsupported TGA colour map depth");
        palette = data + offset;
        size_t bytes = (size_t)map_length * map_bytes;
        if (offset > size || bytes > size - offset)
            return image_error(error, error_size, "Truncated TGA colour map");
        offset += bytes;
    }
    if (mapped && !palette)
        return image_error(error, error_size, "Colour-mapped TGA without a map");
    if (allocate(image, width, height, error, error_size))
        return MU_IMAGE_ERROR;
    image->channels = grey ? 1 : (mapped ? (map_depth == 32 ? 4 : 3) : (depth == 32 ? 4 : (depth == 16 ? 4 : 3)));
    const unsigned bytes = (depth + 7) / 8;
    const size_t total = (size_t)width * (size_t)height;
    size_t index = 0;
    while (index < total) {
        size_t count = 1;
        int repeat = 0;
        if (rle) {
            if (offset >= size)
                goto truncated;
            unsigned header = data[offset++];
            count = (header & 0x7f) + 1;
            repeat = (header & 0x80) != 0;
        }
        uint8_t pixel[4] = {0, 0, 0, 255};
        for (size_t k = 0; k < count && index < total; ++k) {
            if (!repeat || k == 0) {
                if (bytes > size - offset)
                    goto truncated;
                const uint8_t *src = data + offset;
                offset += bytes;
                if (grey) {
                    pixel[0] = pixel[1] = pixel[2] = src[0];
                    pixel[3] = 255;
                } else if (mapped) {
                    unsigned entry = src[0];
                    if (entry < map_first || entry - map_first >= map_length) {
                        mu_image_free(image);
                        return image_error(error, error_size, "TGA colour index outside map");
                    }
                    const uint8_t *e = palette + (size_t)(entry - map_first) * map_bytes;
                    if (map_bytes >= 3) {
                        pixel[0] = e[2]; pixel[1] = e[1]; pixel[2] = e[0];
                        pixel[3] = map_bytes == 4 ? e[3] : 255;
                    } else {
                        unsigned v = le16(e);
                        pixel[0] = (uint8_t)(((v >> 10) & 31) * 255 / 31);
                        pixel[1] = (uint8_t)(((v >> 5) & 31) * 255 / 31);
                        pixel[2] = (uint8_t)((v & 31) * 255 / 31);
                        pixel[3] = 255;
                    }
                } else if (bytes == 2) {
                    unsigned v = le16(src);
                    pixel[0] = (uint8_t)(((v >> 10) & 31) * 255 / 31);
                    pixel[1] = (uint8_t)(((v >> 5) & 31) * 255 / 31);
                    pixel[2] = (uint8_t)((v & 31) * 255 / 31);
                    pixel[3] = ((descriptor & 15) == 0 || (v & 0x8000)) ? 255 : 0;
                } else {
                    pixel[0] = src[2]; pixel[1] = src[1]; pixel[2] = src[0];
                    pixel[3] = bytes == 4 ? src[3] : 255;
                }
            }
            size_t x = index % (size_t)width, y = index / (size_t)width;
            if (descriptor & 0x10)
                x = (size_t)width - 1 - x;
            if (!(descriptor & 0x20))
                y = (size_t)height - 1 - y;   /* bottom-left origin: flip to top-down rows */
            memcpy(image->rgba + 4 * (y * (size_t)width + x), pixel, 4);
            index++;
        }
    }
    return MU_IMAGE_OK;
truncated:
    mu_image_free(image);
    return image_error(error, error_size, "Truncated TGA pixel data");
}

int mu_image_decode_bmp(const uint8_t *data, size_t size, mu_image *image, char *error, size_t error_size)
{
    memset(image, 0, sizeof *image);
    if (size < 54 || data[0] != 'B' || data[1] != 'M')
        return image_error(error, error_size, "Not a BMP image");
    uint32_t pixels = le32(data + 10), header = le32(data + 14);
    int32_t width = (int32_t)le32(data + 18), height = (int32_t)le32(data + 22);
    unsigned bpp = le16(data + 28), compression = le32(data + 30), colours = le32(data + 46);
    if (header < 40 || (compression != 0 && !(compression == 3 && bpp == 32)))
        return image_error(error, error_size, "Unsupported BMP compression %u", compression);
    if (bpp != 8 && bpp != 24 && bpp != 32)
        return image_error(error, error_size, "Unsupported BMP depth %u", bpp);
    int top_down = height < 0;
    if (top_down)
        height = -height;
    if (allocate(image, width, height, error, error_size))
        return MU_IMAGE_ERROR;
    image->channels = bpp == 32 ? 4 : 3;
    const uint8_t *palette = data + 14 + header;
    if (bpp == 8 && colours == 0)
        colours = 256;
    if (bpp == 8 && (14 + (size_t)header + 4 * (size_t)colours > size))
        return mu_image_free(image), image_error(error, error_size, "Truncated BMP palette");
    size_t stride = (((size_t)width * bpp + 31) / 32) * 4;
    if (pixels > size || stride * (size_t)height > size - pixels)
        return mu_image_free(image), image_error(error, error_size, "Truncated BMP pixel data");
    for (int32_t row = 0; row < height; ++row) {
        const uint8_t *src = data + pixels + stride * (size_t)row;
        int32_t y = top_down ? row : height - 1 - row;
        uint8_t *dst = image->rgba + 4 * (size_t)y * (size_t)width;
        for (int32_t x = 0; x < width; ++x, dst += 4) {
            if (bpp == 8) {
                unsigned entry = src[x];
                if (entry >= colours)
                    return mu_image_free(image), image_error(error, error_size, "BMP colour index outside palette");
                const uint8_t *e = palette + 4 * entry;
                dst[0] = e[2]; dst[1] = e[1]; dst[2] = e[0]; dst[3] = 255;
            } else {
                const uint8_t *p = src + (size_t)x * (bpp / 8);
                dst[0] = p[2]; dst[1] = p[1]; dst[2] = p[0];
                dst[3] = bpp == 32 ? p[3] : 255;
            }
        }
    }
    return MU_IMAGE_OK;
}

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
#endif

int mu_image_have_jpeg(void) { return MU_HAVE_JPEG ? 1 : 0; }

int mu_image_decode_jpeg(const uint8_t *data, size_t size, mu_image *image, char *error, size_t error_size)
{
    memset(image, 0, sizeof *image);
#if MU_HAVE_JPEG
    struct jpeg_decompress_struct info;
    jpeg_failure failure;
    uint8_t *volatile row = NULL;
    info.err = jpeg_std_error(&failure.manager);
    failure.manager.error_exit = jpeg_exit;
    if (setjmp(failure.jump)) {
        jpeg_destroy_decompress(&info);
        free(row);
        mu_image_free(image);
        return image_error(error, error_size, "Invalid JPEG data");
    }
    jpeg_create_decompress(&info);
    jpeg_mem_src(&info, (unsigned char *)(uintptr_t)data, (unsigned long)size);
    jpeg_read_header(&info, TRUE);
    info.out_color_space = JCS_RGB;
    jpeg_start_decompress(&info);
    if (allocate(image, (int32_t)info.output_width, (int32_t)info.output_height, error, error_size)) {
        jpeg_destroy_decompress(&info);
        return MU_IMAGE_ERROR;
    }
    image->channels = 3;
    row = malloc((size_t)info.output_width * 3);
    if (!row)
        longjmp(failure.jump, 1);
    while (info.output_scanline < info.output_height) {
        JSAMPROW rows[1] = {row};
        size_t y = info.output_scanline;
        jpeg_read_scanlines(&info, rows, 1);
        uint8_t *dst = image->rgba + 4 * y * (size_t)image->width;
        for (int32_t x = 0; x < image->width; ++x) {
            dst[4 * x] = row[3 * x];
            dst[4 * x + 1] = row[3 * x + 1];
            dst[4 * x + 2] = row[3 * x + 2];
            dst[4 * x + 3] = 255;
        }
    }
    jpeg_finish_decompress(&info);
    jpeg_destroy_decompress(&info);
    free(row);
    return MU_IMAGE_OK;
#else
    (void)data;
    (void)size;
    return image_error(error, error_size, "Built without JPEG support");
#endif
}

static int extension_is(const char *extension, const char *expected)
{
    if (!extension)
        return 0;
    for (; *extension && *expected; ++extension, ++expected)
        if (tolower((unsigned char)*extension) != *expected)
            return 0;
    return *extension == 0 && *expected == 0;
}

int mu_image_decode_wrapped(const uint8_t *data, size_t size, const char *extension, mu_image *image,
                            char *error, size_t error_size)
{
    memset(image, 0, sizeof *image);
    if (extension_is(extension, ".ozj")) {
        if (size > 27 && data[24] == 0xff && data[25] == 0xd8 && data[26] == 0xff)
            return mu_image_decode_jpeg(data + 24, size - 24, image, error, error_size);
        if (size > 48 && memcmp(data, data + 24, 24) == 0 && data[24] == 0 && data[25] == 0 && data[26] == 2)
            return mu_image_decode_tga(data + 24, size - 24, image, error, error_size);
        return image_error(error, error_size, "No supported image signature at observed offset 24");
    }
    if (extension_is(extension, ".ozb")) {
        if (size < 8 || memcmp(data, data + 4, 4) != 0 || data[4] != 'B' || data[5] != 'M')
            return image_error(error, error_size, "Not an observed duplicated-prefix BMP wrapper");
        if (size - 4 < 54 || le32(data + 6) != size - 4)
            return image_error(error, error_size, "BMP declared length mismatch");
        return mu_image_decode_bmp(data + 4, size - 4, image, error, error_size);
    }
    if (extension_is(extension, ".ozt")) {
        static const uint8_t zeros[4] = {0, 0, 0, 0};
        if (size < 22 || (memcmp(data + 4, data, 4) != 0 && memcmp(data + 4, zeros, 4) != 0))
            return image_error(error, error_size, "Unrecognized TGA wrapper prefix");
        uint8_t *payload = malloc(size - 4);
        if (!payload)
            return image_error(error, error_size, "Out of memory");
        memcpy(payload, data, 4);
        memcpy(payload + 4, data + 8, size - 8);
        int status = mu_image_decode_tga(payload, size - 4, image, error, error_size);
        free(payload);
        return status;
    }
    if (extension_is(extension, ".tga"))
        return mu_image_decode_tga(data, size, image, error, error_size);
    if (extension_is(extension, ".bmp"))
        return mu_image_decode_bmp(data, size, image, error, error_size);
    if (extension_is(extension, ".jpg") || extension_is(extension, ".jpeg"))
        return mu_image_decode_jpeg(data, size, image, error, error_size);
    return image_error(error, error_size, "Unsupported image extension");
}

int mu_image_load_file(const char *path, mu_image *image, char *error, size_t error_size)
{
    memset(image, 0, sizeof *image);
    FILE *file = fopen(path, "rb");
    if (!file)
        return image_error(error, error_size, "Cannot open image");
    fseek(file, 0, SEEK_END);
    long length = ftell(file);
    rewind(file);
    if (length <= 0 || length > 64L * 1024 * 1024) {
        fclose(file);
        return image_error(error, error_size, "Image size outside supported limits");
    }
    uint8_t *data = malloc((size_t)length);
    if (!data || fread(data, 1, (size_t)length, file) != (size_t)length) {
        free(data);
        fclose(file);
        return image_error(error, error_size, "Cannot read image");
    }
    fclose(file);
    const char *extension = strrchr(path, '.');
    int status = mu_image_decode_wrapped(data, (size_t)length, extension, image, error, error_size);
    free(data);
    return status;
}

int mu_image_resolve(const char *directory, const char *texture, char *out, size_t out_size)
{
    const char *base = texture;
    for (const char *p = texture; *p; ++p)
        if (*p == '\\' || *p == '/')
            base = p + 1;
    const char *dot = strrchr(base, '.');
    if (!dot || dot == base)
        return 0;
    const char *mapped;
    if (extension_is(dot, ".jpg") || extension_is(dot, ".jpeg"))
        mapped = ".ozj";
    else if (extension_is(dot, ".tga"))
        mapped = ".ozt";
    else if (extension_is(dot, ".bmp"))
        mapped = ".ozb";
    else
        return 0;
    size_t stem = (size_t)(dot - base);
    DIR *dir = opendir(directory);
    if (!dir)
        return 0;
    struct dirent *entry;
    int found = 0;
    while ((entry = readdir(dir)) != NULL) {
        const char *name = entry->d_name;
        size_t length = strlen(name);
        if (length != stem + strlen(mapped))
            continue;
        int same = 1;
        for (size_t k = 0; k < stem && same; ++k)
            same = tolower((unsigned char)name[k]) == tolower((unsigned char)base[k]);
        if (!same || !extension_is(name + stem, mapped))
            continue;
        snprintf(out, out_size, "%s/%s", directory, name);
        found = 1;
        break;
    }
    closedir(dir);
    return found;
}
