#ifndef MU_LABEL_H
#define MU_LABEL_H

/* Text labels over the 3D view, drawn without the GFx player (NATIVE-NAMES-001).
 *
 * The client draws overhead names, monster HP bars, chat bubbles and ground
 * item labels with the GFx movie hudPlayerName; when the native session
 * runs without mugfx/Ruffle (headless software renders, CI, --gfx absent)
 * these helpers draw a stand-in: the movies' HTML subset rendered with the
 * GDI text boundary (mu_ui_font: CoreText on macOS, the box font elsewhere)
 * into RGBA images, and composited into an RGBA frame.  Faces, the shadow
 * and box colours are viewer choices, not client readings.  One helper for
 * every overhead label (names, bubbles, item labels). */

#include <stddef.h>
#include <stdint.h>

#include "mu_ui_font.h"

#define MU_LABEL_SIZES 3

typedef struct mu_label_fonts {
    mu_ui_font font[MU_LABEL_SIZES];     /* 12, 14 and 16 pixel cells (GFx font size attributes) */
    int32_t size[MU_LABEL_SIZES];
    int open[MU_LABEL_SIZES];
} mu_label_fonts;

typedef struct mu_label_image {
    int32_t width, height;
    uint8_t *rgba;                        /* top row first, straight alpha */
} mu_label_image;

/* Opens the faces (face NULL: "Arial"; "@box" forces the placeholder font). */
int mu_label_fonts_open(mu_label_fonts *fonts, const char *face);
void mu_label_fonts_close(mu_label_fonts *fonts);

/* Text extent of plain text at a font size (nearest opened size). */
void mu_label_extent(mu_label_fonts *fonts, int32_t size, const char *text, int32_t *cx, int32_t *cy);

/* Renders the HTML subset of the movies' text fields: <font color='#RRGGBB'
 * size='N'>, <br>, <p ...>, &lt; &gt; &amp; &quot;; other tags are dropped.
 * Lines are centred (align 1) or left aligned (0).  A one-pixel shadow is
 * drawn under the glyphs when shadow is set.  Returns 0 on success. */
int mu_label_html(mu_label_fonts *fonts, const char *html, uint32_t default_rgb, int32_t default_size, int align,
                  int shadow, mu_label_image *out);
void mu_label_image_free(mu_label_image *image);

/* Alpha-blends an image into an RGBA frame (top row first) at (x, y). */
void mu_label_blend(uint8_t *frame, int32_t width, int32_t height, const mu_label_image *image, int32_t x, int32_t y,
                    float alpha);
/* Fills a rectangle with a straight-alpha colour. */
void mu_label_fill(uint8_t *frame, int32_t width, int32_t height, int32_t x, int32_t y, int32_t w, int32_t h,
                   const uint8_t rgba[4]);
/* Rectangle outline, one pixel. */
void mu_label_frame(uint8_t *frame, int32_t width, int32_t height, int32_t x, int32_t y, int32_t w, int32_t h,
                    const uint8_t rgba[4]);

#endif
