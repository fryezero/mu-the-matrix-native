#ifndef MU_PNG_H
#define MU_PNG_H

#include <stdint.h>

/* Minimal RGBA8 PNG writer (stored deflate blocks, no external library).
 * Rows are written top to bottom. Returns 0 on success. */
int mu_png_write(const char *path, const uint8_t *rgba, int32_t width, int32_t height);

/* The same file with every alpha byte written as 0xff (REGRESS-003). For window captures: the window is opaque
 * and shows only the colour channels, but terrain layers, grass and other blended draws leave framebuffer alpha
 * below 1, which viewers then composite as flat light-grey patches. The caller's buffer (and any hash of it) is
 * left untouched. */
int mu_png_write_opaque(const char *path, const uint8_t *rgba, int32_t width, int32_t height);

/* SHA-256 of a byte span, as 64 lowercase hex digits plus NUL. Used to hash
 * raw framebuffer pixels independently of PNG encoding. */
void mu_sha256_hex(const uint8_t *data, uint64_t size, char out[65]);

#endif
