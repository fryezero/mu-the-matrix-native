#ifndef MU_PNG_H
#define MU_PNG_H

#include <stdint.h>

/* Minimal RGBA8 PNG writer (stored deflate blocks, no external library).
 * Rows are written top to bottom. Returns 0 on success. */
int mu_png_write(const char *path, const uint8_t *rgba, int32_t width, int32_t height);

/* SHA-256 of a byte span, as 64 lowercase hex digits plus NUL. Used to hash
 * raw framebuffer pixels independently of PNG encoding. */
void mu_sha256_hex(const uint8_t *data, uint64_t size, char out[65]);

#endif
