#ifndef MU_GIF_H
#define MU_GIF_H

#include <stdint.h>

/* Minimal animated GIF89a writer for headless renders: a fixed 6x7x6 colour
 * cube (252 entries, ordered by red, green, blue levels) with nearest-level
 * mapping, and an LZW stream that sends a clear code before the code width
 * would grow past 9 bits (valid, uncompressed-size output). frames holds
 * count RGBA8 images of width x height, top row first. delay is in 1/100 s;
 * the animation loops forever. Returns 0 on success. */
int mu_gif_write(const char *path, const uint8_t *frames, int32_t width, int32_t height, int32_t count,
                 int32_t delay);

#endif
