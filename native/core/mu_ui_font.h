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

/* The four fonts CreateFonts 0x0182a0da makes (NATIVE-UI-002), keyed by the
 * HFONT handle values the reconstruction passes to SelectObject.  The
 * set's GDI callbacks draw with the font selected last. */
enum { MU_UI_FONT_SET_SIZE = 4, MU_UI_FONT_SET_MAX = 8 };
typedef struct mu_ui_font_set {
    mu_ui_font fonts[MU_UI_FONT_SET_MAX];    /* normal, bold, big, fixed, then fonts windows create */
    mu_ui_gdi gdi[MU_UI_FONT_SET_MAX];
    uint32_t handles[MU_UI_FONT_SET_MAX];
    int count;
    int current;
} mu_ui_font_set;

/* face: GlobalText[0]; fixed_face: GlobalText[18]. */
int mu_ui_font_set_open(mu_ui_font_set *set, const char *face, const char *fixed_face, uint32_t window_width,
                        const uint32_t handles[MU_UI_FONT_SET_SIZE]);
void mu_ui_font_set_close(mu_ui_font_set *set);
/* A further CreateFontA (a window's own font); returns its handle, 0 when full. */
uint32_t mu_ui_font_set_add(mu_ui_font_set *set, const char *face, int32_t height, int32_t weight);
/* SelectObject(dc, handle); unknown handles leave the selection unchanged. */
void mu_ui_font_set_select(mu_ui_font_set *set, uint32_t handle);
mu_ui_gdi mu_ui_font_set_gdi(mu_ui_font_set *set);

#endif
