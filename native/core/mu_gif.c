#include "mu_gif.h"

#include <stdio.h>
#include <stdlib.h>

static const int levels[3] = {6, 7, 6};

static int level(int value, int count) { return (value * (count - 1) + 127) / 255; }

typedef struct bit_writer {
    FILE *f;
    uint8_t block[255];
    int fill;
    uint32_t bits;
    int nbits;
} bit_writer;

static void flush_block(bit_writer *w)
{
    if (!w->fill)
        return;
    fputc(w->fill, w->f);
    fwrite(w->block, 1, (size_t)w->fill, w->f);
    w->fill = 0;
}

static void put_code(bit_writer *w, uint32_t code, int width)
{
    w->bits |= code << w->nbits;
    w->nbits += width;
    while (w->nbits >= 8) {
        w->block[w->fill++] = (uint8_t)w->bits;
        w->bits >>= 8;
        w->nbits -= 8;
        if (w->fill == 255)
            flush_block(w);
    }
}

static void put16(FILE *f, int v) { fputc(v & 0xff, f); fputc((v >> 8) & 0xff, f); }

int mu_gif_write(const char *path, const uint8_t *frames, int32_t width, int32_t height, int32_t count, int32_t delay)
{
    if (width <= 0 || height <= 0 || width > 0xffff || height > 0xffff || count <= 0)
        return 1;
    FILE *f = fopen(path, "wb");
    if (!f)
        return 1;
    fwrite("GIF89a", 1, 6, f);
    put16(f, width);
    put16(f, height);
    fputc(0xf7, f);   /* global colour table, 8 bits, 256 entries */
    fputc(0, f);
    fputc(0, f);
    for (int i = 0; i < 256; ++i) {
        int r = 0, g = 0, b = 0;
        if (i < 252) {
            r = (i / (levels[1] * levels[2])) * 255 / (levels[0] - 1);
            g = ((i / levels[2]) % levels[1]) * 255 / (levels[1] - 1);
            b = (i % levels[2]) * 255 / (levels[2] - 1);
        }
        fputc(r, f), fputc(g, f), fputc(b, f);
    }
    /* NETSCAPE2.0 loop extension: loop forever. */
    fwrite("\x21\xff\x0bNETSCAPE2.0\x03\x01\x00\x00\x00", 1, 19, f);
    size_t pixels = (size_t)width * (size_t)height;
    for (int32_t frame = 0; frame < count; ++frame) {
        const uint8_t *rgba = frames + pixels * 4 * (size_t)frame;
        fwrite("\x21\xf9\x04\x04", 1, 4, f);   /* graphic control: dispose = leave */
        put16(f, delay);
        fputc(0, f);
        fputc(0, f);
        fputc(0x2c, f);
        put16(f, 0);
        put16(f, 0);
        put16(f, width);
        put16(f, height);
        fputc(0, f);
        fputc(8, f);   /* LZW minimum code size */
        bit_writer w = {f, {0}, 0, 0, 0};
        const uint32_t clear = 256, end = 257;
        int pending = 0;   /* codes emitted since the last clear */
        put_code(&w, clear, 9);
        for (size_t p = 0; p < pixels; ++p) {
            int index = level(rgba[4 * p], levels[0]) * levels[1] * levels[2] +
                        level(rgba[4 * p + 1], levels[1]) * levels[2] + level(rgba[4 * p + 2], levels[2]);
            put_code(&w, (uint32_t)index, 9);
            /* The decoder adds a table entry per code after the first; clear before it reaches 512. */
            if (++pending == 254) {
                put_code(&w, clear, 9);
                pending = 0;
            }
        }
        put_code(&w, end, 9);
        if (w.nbits)
            put_code(&w, 0, 8 - w.nbits);
        flush_block(&w);
        fputc(0, f);
    }
    fputc(0x3b, f);
    return fclose(f) ? 1 : 0;
}
