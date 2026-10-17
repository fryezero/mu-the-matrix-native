/* Reconstructed GDI text path of the pinned client (NATIVE-UI-001).
 *
 * CUIRenderTextOriginal (vtable 0x01ac4c68) draws text with GDI into a
 * screen-sized 24-bit top-down DIB section, converts the DIB to the RGBA
 * font texture BITMAP_FONT (0x7532, Interface\FontInput.tga) and draws that
 * texture with RenderBitmap.  The GDI calls (GetTextExtentPointA, TextOutA,
 * SetBkColor, SetTextColor) are the platform boundary: mu_ui_gdi supplies
 * them.  Font creation (0x0182a0da) is described by mu_ui_font_height and
 * mu_ui_font_spec.
 */
#ifndef MU_UI_TEXT_H
#define MU_UI_TEXT_H

#include "ui2d.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct mu_ui_gdi {
    void *user;
    /* GetTextExtentPointA(hdc, text, length, &size) with the selected font. */
    void (*extent)(void *user, const char *text, int length, int32_t *cx, int32_t *cy);
    /* TextOutA(hdc, x, y, text, length) after SetBkColor(0) and
     * SetTextColor(0xffffff): opaque black cells, white glyphs, written into
     * the 24-bit DIB (rows `stride` bytes apart, top-down, B,G,R order). */
    void (*text_out)(void *user, uint8_t *dib, int32_t stride, int32_t width, int32_t height, int32_t x,
                     int32_t y, const char *text, int length);
} mu_ui_gdi;

typedef struct mu_ui_text {
    mu_ui_gdi gdi;
    uint8_t *dib;           /* +0x0c: DIB bits */
    int32_t dib_width;      /* (int)(640 * rate x) */
    int32_t dib_height;     /* (int)(480 * rate y) */
    uint32_t text_color;    /* +0x10: r | g<<8 | b<<16 | a<<24, default 0xffffffff */
    uint32_t back_color;    /* +0x14: same packing, default 0 */
} mu_ui_text;

/* CUIRenderTextOriginal::Create 0x0119fcf6: DIB size and default colours.
 * The caller allocates dib (dib_stride(width) * height bytes). */
void mu_ui_text_init(mu_ui_text *text, const mu_ui_state *state);
int32_t mu_ui_text_dib_stride(int32_t width);              /* ((w*24 + 31) & ~31) >> 3 */
void mu_ui_text_set_color(mu_ui_text *text, uint8_t r, uint8_t g, uint8_t b, uint8_t a);       /* 0x0119fe9b */
void mu_ui_text_set_back_color(mu_ui_text *text, uint8_t r, uint8_t g, uint8_t b, uint8_t a);  /* 0x0119fedf */

/* RenderText 0x0119ff3e (vtable slot 11).  sort: 1 left, 2 right-clip,
 * 3 centre, 4 right, 7 right of x, 8 centred on x.  out_size may be NULL. */
void mu_ui_render_text(mu_ui_state *state, mu_ui_text *text, int32_t x, int32_t y, const char *string,
                       int32_t box_width, int32_t box_height, int32_t sort, int32_t out_size[2]);
/* A direct GetTextExtentPointA call on the font DC (as the login scene makes). */
void mu_ui_text_extent(mu_ui_state *state, mu_ui_text *text, const char *string, int length, int32_t *cx,
                       int32_t *cy);
/* WriteText 0x011a0431 and UploadText 0x011a054e. */
void mu_ui_write_text(mu_ui_state *state, mu_ui_text *text, int32_t offset, int32_t width, int32_t height);
void mu_ui_upload_text(mu_ui_state *state, mu_ui_text *text, int32_t x, int32_t y, int32_t width,
                       int32_t height);

/* Font sizes chosen by 0x0182a0da from the window width; heights passed to
 * CreateFontA are font_height - 1 (normal and bold), 2*(font_height - 1)
 * (big, bold) and 12 (fixed). */
int32_t mu_ui_font_height(uint32_t window_width);

enum { MU_UI_FONT_NORMAL, MU_UI_FONT_BOLD, MU_UI_FONT_BIG, MU_UI_FONT_FIXED };
typedef struct mu_ui_font_spec {
    int32_t height;          /* CreateFontA nHeight (cell height) */
    int32_t weight;          /* FW_NORMAL 400 or FW_BOLD 700 */
    int32_t quality;         /* NONANTIALIASED_QUALITY (3) for every font */
    int32_t face_text;       /* GlobalText index of the face name (0, or 18 for fixed) */
} mu_ui_font_spec;
mu_ui_font_spec mu_ui_font_for(uint32_t window_width, int which);

#ifdef __cplusplus
}
#endif
#endif
