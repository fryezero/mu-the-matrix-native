/* Reconstructed interface texture loading of the pinned client (NATIVE-UI-001).
 *
 * LoadBitmap 0x0185baac prefixes "Data\" and calls CGlobalBitmap::LoadImage
 * 0x00c97730 on the global table 0x0bdc5f00, which dispatches on the
 * extension: "jpg" -> OpenJpeg 0x00c982ea reads <name>.OZJ, "tga" -> OpenTga
 * 0x00c988fc reads <name>.OZT.  These functions restate the two decoders'
 * pixel handling and GL uploads.  JPEG entropy decoding is the client's
 * statically linked IJG libjpeg (jpeg_CreateDecompress version 62, struct
 * size 0x1b0); it is a library boundary supplied by mu_ui_jpeg_decoder.
 */
#ifndef MU_UI_TEXTURE_H
#define MU_UI_TEXTURE_H

#include "ui2d.h"

#ifdef __cplusplus
extern "C" {
#endif

enum {
    MU_UI_TEXTURE_FAILED = 0,     /* the client returns false */
    MU_UI_TEXTURE_LOADED = 1,     /* bitmap created and uploaded */
    MU_UI_TEXTURE_SKIPPED = 2     /* JPEG larger than 1024: client returns true, no bitmap */
};

/* OpenTga: the OZT payload after the 4-byte wrapper is read with fixed
 * offsets (width int16 @16, height int16 @18, bits byte @20, pixels @22);
 * the TGA id length, colour map, image type and origin bit are ignored.
 * 32 bits per pixel and width/height <= 1024 are required.  Rows are
 * flipped and BGRA becomes RGBA in a power-of-two RGBA buffer.  The client
 * reads past short files (undefined); the reconstruction refuses them.
 * Padding outside the image is zero here and uninitialised in the client.
 * `buffer` is malloc'ed into bitmap->buffer and kept (the caller frees). */
int mu_ui_open_tga(mu_ui_state *state, const uint8_t *file, size_t size, uint32_t index, uint32_t filter,
                   uint32_t wrap, uint32_t texture_name, mu_ui_bitmap *bitmap);

typedef struct mu_ui_jpeg_image {
    int32_t width, height, components;  /* cinfo output_width/height/output_components */
    uint8_t *pixels;                    /* height rows of width*components bytes (decoder-owned) */
} mu_ui_jpeg_image;
/* Decode `data` (the OZJ bytes after the 24-byte header skip).  Return 0 on
 * a libjpeg error (the client's setjmp path returns false). */
typedef int (*mu_ui_jpeg_decoder)(void *user, const uint8_t *data, size_t size, mu_ui_jpeg_image *image);
typedef void (*mu_ui_jpeg_release)(void *user, mu_ui_jpeg_image *image);

int mu_ui_open_jpeg(mu_ui_state *state, const uint8_t *file, size_t size, uint32_t index, uint32_t filter,
                    uint32_t wrap, uint32_t texture_name, mu_ui_jpeg_decoder decode, mu_ui_jpeg_release release,
                    void *user, mu_ui_bitmap *bitmap);

/* Power-of-two size loop shared by both decoders: the smallest 1 << k >= n,
 * capped at 1024; 1 for n <= 1. */
int32_t mu_ui_texture_size(int32_t n);

/* Indices whose pixel buffer the client keeps after upload. */
int mu_ui_texture_keeps_buffer(uint32_t index, int jpeg);

#ifdef __cplusplus
}
#endif
#endif
