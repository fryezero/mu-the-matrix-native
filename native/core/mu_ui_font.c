/* GDI text boundary for the 2D layer.  See mu_ui_font.h. */
#include "mu_ui_font.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef __APPLE__
#include <CoreFoundation/CoreFoundation.h>
#include <CoreGraphics/CoreGraphics.h>
#include <CoreText/CoreText.h>
#endif

static void fill_cell(uint8_t *dib, int32_t stride, int32_t width, int32_t height, int32_t cx, int32_t cy)
{
    for (int32_t y = 0; y < cy && y < height; ++y)
        memset(dib + (size_t)y * (size_t)stride, 0, (size_t)(cx < width ? cx : width) * 3);
}

/* ---- placeholder backend ---------------------------------------------- */

static int32_t box_advance(const mu_ui_font *font, unsigned char c)
{
    int32_t w = font->height / 2;
    if (c == ' ')
        return w / 2 > 1 ? w / 2 : 2;
    return w > 3 ? w : 3;
}

static void box_extent(void *user, const char *text, int length, int32_t *cx, int32_t *cy)
{
    const mu_ui_font *font = user;
    int32_t w = 0;
    for (int i = 0; i < length; ++i)
        w += box_advance(font, (unsigned char)text[i]);
    *cx = w;
    *cy = font->height;
}

static void box_text_out(void *user, uint8_t *dib, int32_t stride, int32_t width, int32_t height, int32_t x0,
                         int32_t y0, const char *text, int length)
{
    const mu_ui_font *font = user;
    int32_t cx, cy, x = x0;
    box_extent(user, text, length, &cx, &cy);
    fill_cell(dib, stride, width, height, cx, cy);
    for (int i = 0; i < length; ++i) {
        int32_t a = box_advance(font, (unsigned char)text[i]);
        if (text[i] != ' ') {
            int32_t top = y0 + font->height / 5, bottom = y0 + font->height - font->height / 5;
            for (int32_t y = top; y < bottom && y < height; ++y)
                for (int32_t xx = x; xx < x + a - 1 && xx < width; ++xx)
                    if (y == top || y == bottom - 1 || xx == x || xx == x + a - 2)
                        memset(dib + (size_t)y * (size_t)stride + (size_t)xx * 3, 0xff, 3);
        }
        x += a;
    }
}

/* ---- CoreText backend ------------------------------------------------- */

#ifdef __APPLE__
static int ct_glyphs(const mu_ui_font *font, const char *text, int length, CGGlyph *glyphs, int32_t *advances)
{
    UniChar chars[1024];
    CGSize sizes[1024];
    if (length > 1024)
        length = 1024;
    for (int i = 0; i < length; ++i)
        chars[i] = (UniChar)(unsigned char)text[i];          /* code page 1252 subset: Latin-1 */
    CTFontGetGlyphsForCharacters((CTFontRef)font->ct_font, chars, glyphs, length);
    CTFontGetAdvancesForGlyphs((CTFontRef)font->ct_font, kCTFontOrientationHorizontal, glyphs, sizes, length);
    for (int i = 0; i < length; ++i)
        advances[i] = (int32_t)lround(sizes[i].width);
    return length;
}

static void ct_extent(void *user, const char *text, int length, int32_t *cx, int32_t *cy)
{
    const mu_ui_font *font = user;
    CGGlyph glyphs[1024];
    int32_t advances[1024], w = 0;
    int n = ct_glyphs(font, text, length, glyphs, advances);
    for (int i = 0; i < n; ++i)
        w += advances[i];
    *cx = w;
    *cy = font->height;
}

static void ct_text_out(void *user, uint8_t *dib, int32_t stride, int32_t width, int32_t height, int32_t x0,
                        int32_t y0, const char *text, int length)
{
    const mu_ui_font *font = user;
    CGGlyph glyphs[1024];
    int32_t advances[1024], cx = 0;
    CGPoint positions[1024];
    int n = ct_glyphs(font, text, length, glyphs, advances);
    for (int i = 0; i < n; ++i) {
        positions[i] = CGPointMake((CGFloat)cx, 0);
        cx += advances[i];
    }
    int32_t cell_w = cx, cell_h = font->height;
    fill_cell(dib, stride, width, height, cell_w, cell_h);
    if (cell_w <= 0 || cell_h <= 0)
        return;
    uint8_t *gray = calloc((size_t)cell_w * (size_t)cell_h, 1);
    if (!gray)
        return;
    CGColorSpaceRef space = CGColorSpaceCreateDeviceGray();
    CGContextRef ctx = CGBitmapContextCreate(gray, (size_t)cell_w, (size_t)cell_h, 8, (size_t)cell_w, space,
                                             (CGBitmapInfo)kCGImageAlphaNone);
    CGColorSpaceRelease(space);
    if (ctx) {
        CGContextSetShouldAntialias(ctx, false);
        CGContextSetShouldSmoothFonts(ctx, false);
        CGContextSetAllowsFontSubpixelPositioning(ctx, false);
        CGContextSetShouldSubpixelPositionFonts(ctx, false);
        CGContextSetGrayFillColor(ctx, 1.0, 1.0);
        /* CoreGraphics is y-up: the baseline lies `ascent` pixels below the cell top. */
        CGContextSetTextPosition(ctx, 0, 0);
        CGContextTranslateCTM(ctx, 0, (CGFloat)(cell_h - font->ascent));
        CTFontDrawGlyphs((CTFontRef)font->ct_font, glyphs, positions, (size_t)n, ctx);
        CGContextFlush(ctx);
        CGContextRelease(ctx);
        /* bitmap row 0 is the top row */
        for (int32_t y = 0; y < cell_h; ++y) {
            int32_t ty = y0 + y;
            if (ty < 0 || ty >= height)
                continue;
            for (int32_t x = 0; x < cell_w; ++x) {
                int32_t tx = x0 + x;
                if (tx < 0 || tx >= width)
                    continue;
                if (gray[(size_t)y * (size_t)cell_w + (size_t)x] >= 128)
                    memset(dib + (size_t)ty * (size_t)stride + (size_t)tx * 3, 0xff, 3);
            }
        }
    }
    free(gray);
}
#endif

int mu_ui_font_open(mu_ui_font *font, const char *face, int32_t height, int32_t weight)
{
    memset(font, 0, sizeof *font);
    font->height = height;
    font->weight = weight;
    snprintf(font->face, sizeof font->face, "%s", face ? face : "Tahoma");
    font->ascent = (height * 4 + 2) / 5;
#ifdef __APPLE__
    if (strcmp(font->face, "@box") != 0) {
        char name[160];
        snprintf(name, sizeof name, "%s%s", font->face, weight >= 700 ? " Bold" : "");
        CFStringRef cf = CFStringCreateWithCString(NULL, name, kCFStringEncodingUTF8);
        CTFontRef probe = CTFontCreateWithName(cf, 100.0, NULL);
        CFRelease(cf);
        if (probe) {
            double ascent = CTFontGetAscent(probe), descent = CTFontGetDescent(probe);
            if (ascent + descent > 0) {
                font->point_size = 100.0 * (double)height / (ascent + descent);
                CTFontRef sized = CTFontCreateCopyWithAttributes(probe, (CGFloat)font->point_size, NULL, NULL);
                if (sized) {
                    font->ct_font = (void *)sized;
                    font->ascent = (int32_t)lround(ascent * font->point_size / 100.0);
                    font->backend = 1;
                }
            }
            CFRelease(probe);
        }
    }
#endif
    return font->backend ? 0 : 1;
}

void mu_ui_font_close(mu_ui_font *font)
{
#ifdef __APPLE__
    if (font->ct_font)
        CFRelease((CTFontRef)font->ct_font);
#endif
    font->ct_font = NULL;
}

mu_ui_gdi mu_ui_font_gdi(mu_ui_font *font)
{
    mu_ui_gdi gdi;
    gdi.user = font;
#ifdef __APPLE__
    if (font->backend == 1) {
        gdi.extent = ct_extent;
        gdi.text_out = ct_text_out;
        return gdi;
    }
#endif
    gdi.extent = box_extent;
    gdi.text_out = box_text_out;
    return gdi;
}

/* ---- font set (NATIVE-UI-002) ------------------------------------------ */

static void set_extent(void *user, const char *text, int length, int32_t *cx, int32_t *cy)
{
    mu_ui_font_set *set = user;
    mu_ui_gdi *gdi = &set->gdi[set->current];
    gdi->extent(gdi->user, text, length, cx, cy);
}

static void set_text_out(void *user, uint8_t *dib, int32_t stride, int32_t width, int32_t height, int32_t x,
                         int32_t y, const char *text, int length)
{
    mu_ui_font_set *set = user;
    mu_ui_gdi *gdi = &set->gdi[set->current];
    gdi->text_out(gdi->user, dib, stride, width, height, x, y, text, length);
}

int mu_ui_font_set_open(mu_ui_font_set *set, const char *face, const char *fixed_face, uint32_t window_width,
                        const uint32_t handles[MU_UI_FONT_SET_SIZE])
{
    int failed = 0;
    memset(set, 0, sizeof *set);
    for (int i = 0; i < MU_UI_FONT_SET_SIZE; ++i) {
        mu_ui_font_spec spec = mu_ui_font_for(window_width, i);
        failed |= mu_ui_font_open(&set->fonts[i], i == MU_UI_FONT_FIXED ? fixed_face : face, spec.height,
                                  spec.weight);
        set->gdi[i] = mu_ui_font_gdi(&set->fonts[i]);
        set->handles[i] = handles[i];
    }
    set->count = MU_UI_FONT_SET_SIZE;
    set->current = MU_UI_FONT_NORMAL;
    return failed;
}

uint32_t mu_ui_font_set_add(mu_ui_font_set *set, const char *face, int32_t height, int32_t weight)
{
    if (set->count >= MU_UI_FONT_SET_MAX)
        return 0;
    int i = set->count++;
    mu_ui_font_open(&set->fonts[i], face, height, weight);
    set->gdi[i] = mu_ui_font_gdi(&set->fonts[i]);
    set->handles[i] = 0x0f0f1000u + (uint32_t)i;
    return set->handles[i];
}

void mu_ui_font_set_close(mu_ui_font_set *set)
{
    for (int i = 0; i < set->count; ++i)
        mu_ui_font_close(&set->fonts[i]);
}

void mu_ui_font_set_select(mu_ui_font_set *set, uint32_t handle)
{
    for (int i = 0; i < set->count; ++i)
        if (set->handles[i] == handle)
            set->current = i;
}

mu_ui_gdi mu_ui_font_set_gdi(mu_ui_font_set *set)
{
    mu_ui_gdi gdi;
    gdi.user = set;
    gdi.extent = set_extent;
    gdi.text_out = set_text_out;
    return gdi;
}
