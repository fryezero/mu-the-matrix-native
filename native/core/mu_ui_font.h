#ifndef MU_UI_FONT_H
#define MU_UI_FONT_H

/* The GDI side of the client's text path (NATIVE-UI-001).
 *
 * The client creates its fonts with CreateFontA (0x0182a0da: positive cell
 * height, FW_NORMAL/FW_BOLD, NONANTIALIASED_QUALITY, face GlobalText[0]),
 * measures with GetTextExtentPointA and draws with TextOutA at (0, 0) in
 * opaque mode, white on black, into a 24-bit DIB.  These are Windows
 * platform calls; this module provides a macOS replacement with CoreText:
 *
 *   cell height  = CreateFontA nHeight (ascent + descent, GDI's positive
 *                  height convention), point size scaled to match;
 *   advances     = per-glyph advances rounded to whole pixels;
 *   rasterising  = antialiasing off, glyph pixels >= 50% coverage are white,
 *                  the text cell is filled black first (OPAQUE mode).
 *
 * GDI hinting and glyph shapes are not reproduced exactly.  Without
 * CoreText (Linux), or with the face "@box", a deterministic box
 * placeholder font keeps layout testable.
 */

#include <stdint.h>

#include "../../reconstructed/ui/ui_text.h"

typedef struct mu_ui_font {
    int32_t height;        /* CreateFontA nHeight */
    int32_t weight;
    int32_t ascent;        /* whole pixels */
    double point_size;
    void *ct_font;         /* CTFontRef on macOS */
    char face[128];
    int backend;           /* 1 CoreText, 0 placeholder */
} mu_ui_font;

int mu_ui_font_open(mu_ui_font *font, const char *face, int32_t height, int32_t weight);
void mu_ui_font_close(mu_ui_font *font);
/* GDI callbacks for mu_ui_text, bound to `font`. */
mu_ui_gdi mu_ui_font_gdi(mu_ui_font *font);

#endif
