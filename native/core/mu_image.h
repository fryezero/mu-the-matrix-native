#ifndef MU_IMAGE_H
#define MU_IMAGE_H

#include <stddef.h>
#include <stdint.h>

/* Texture loading for the native viewer.
 *
 * Wrapper removal follows asset-recovery/recover_images.py exactly
 * (docs/research/client-image-data.md):
 *   .ozj  24-byte prefix, JPEG payload (eight files carry TGA instead);
 *   .ozt  bytes 4..7 removed, TGA payload;
 *   .ozb  duplicated 4-byte prefix removed, BMP payload.
 * Decoded pixels are RGBA8, rows top to bottom. TGA honours its origin bit;
 * BMP bottom-up rows are flipped. JPEG needs libjpeg (MU_HAVE_JPEG); without
 * it JPEG payloads report an error. How the client itself uploads rows,
 * filters and wraps textures has not been recovered.
 */

typedef struct mu_image {
    int32_t width, height;
    int32_t channels;      /* channels in the source (3 or 4; 1 for greyscale) */
    uint8_t *rgba;         /* width*height*4, owned */
} mu_image;

enum { MU_IMAGE_OK = 0, MU_IMAGE_ERROR = 1 };

int mu_image_decode_wrapped(const uint8_t *data, size_t size, const char *extension, mu_image *image,
                            char *error, size_t error_size);
int mu_image_decode_tga(const uint8_t *data, size_t size, mu_image *image, char *error, size_t error_size);
int mu_image_decode_bmp(const uint8_t *data, size_t size, mu_image *image, char *error, size_t error_size);
int mu_image_decode_jpeg(const uint8_t *data, size_t size, mu_image *image, char *error, size_t error_size);
int mu_image_load_file(const char *path, mu_image *image, char *error, size_t error_size);
void mu_image_free(mu_image *image);
int mu_image_have_jpeg(void);

/* Resolves a BMD texture name (e.g. "skin01.jpg") to an existing wrapped file
 * in directory: same stem, extension mapped .jpg->.ozj, .tga->.ozt,
 * .bmp->.ozb, matched case-insensitively. Returns 1 and fills out on success. */
int mu_image_resolve(const char *directory, const char *texture, char *out, size_t out_size);

#endif
