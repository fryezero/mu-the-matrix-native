/* Stand-in drawing of the overhead labels (NATIVE-NAMES-001); see mu_label.h. */
#include "mu_label.h"

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int mu_label_fonts_open(mu_label_fonts *f, const char *face)
{
    static const int32_t sizes[MU_LABEL_SIZES] = {12, 14, 16};
    memset(f, 0, sizeof *f);
    int any = 0;
    for (int i = 0; i < MU_LABEL_SIZES; ++i) {
        f->size[i] = sizes[i];
        f->open[i] = mu_ui_font_open(&f->font[i], face ? face : "Arial", sizes[i], 400) == 0;
        any |= f->open[i];
    }
    return any ? 0 : 1;
}

void mu_label_fonts_close(mu_label_fonts *f)
{
    for (int i = 0; i < MU_LABEL_SIZES; ++i)
        if (f->open[i])
            mu_ui_font_close(&f->font[i]);
    memset(f, 0, sizeof *f);
}

static mu_ui_font *pick(mu_label_fonts *f, int32_t size)
{
    int best = -1;
    int32_t bd = 1 << 30;
    for (int i = 0; i < MU_LABEL_SIZES; ++i) {
        if (!f->open[i])
            continue;
        int32_t d = abs(f->size[i] - size);
        if (d < bd) {
            bd = d;
            best = i;
        }
    }
    return best < 0 ? NULL : &f->font[best];
}

void mu_label_extent(mu_label_fonts *f, int32_t size, const char *text, int32_t *cx, int32_t *cy)
{
    *cx = *cy = 0;
    mu_ui_font *font = pick(f, size);
    if (!font)
        return;
    mu_ui_gdi gdi = mu_ui_font_gdi(font);
    int n = (int)strlen(text);
    if (n)
        gdi.extent(gdi.user, text, n, cx, cy);
    else
        *cy = font->height;
}

/* ---- the HTML subset ---- */

#define SPANS 64
#define TEXT 256

typedef struct span {
    char text[TEXT];
    uint32_t rgb;
    int32_t size, line, x, w, h;
} span;

static int attr(const char *tag, const char *name, char *out, size_t cap)
{
    const char *p = strstr(tag, name);
    if (!p)
        return 0;
    p += strlen(name);
    while (*p == ' ' || *p == '=')
        ++p;
    char q = (*p == '\'' || *p == '"') ? *p++ : 0;
    size_t n = 0;
    while (*p && (q ? *p != q : (*p != ' ' && *p != '>')) && n + 1 < cap)
        out[n++] = *p++;
    out[n] = 0;
    return 1;
}

static int parse(const char *html, uint32_t rgb0, int32_t size0, span *spans)
{
    uint32_t stack_rgb[8] = {rgb0};
    int32_t stack_size[8] = {size0};
    int depth = 0, n = 0, line = 0;
    span *cur = NULL;
    for (const char *p = html; *p;) {
        if (*p == '<') {
            const char *e = strchr(p, '>');
            if (!e)
                break;
            char tag[160];
            size_t len = (size_t)(e - p - 1) < sizeof tag - 1 ? (size_t)(e - p - 1) : sizeof tag - 1;
            memcpy(tag, p + 1, len);
            tag[len] = 0;
            for (char *t = tag; *t; ++t)
                *t = (char)tolower((unsigned char)*t);
            if (!strncmp(tag, "font", 4) && depth < 7) {
                char v[32];
                ++depth;
                stack_rgb[depth] = stack_rgb[depth - 1];
                stack_size[depth] = stack_size[depth - 1];
                if (attr(tag, "color", v, sizeof v) && v[0] == '#')
                    stack_rgb[depth] = (uint32_t)strtoul(v + 1, NULL, 16);
                if (attr(tag, "size", v, sizeof v))
                    stack_size[depth] = atoi(v);
            } else if (!strcmp(tag, "/font") && depth > 0)
                --depth;
            else if (!strcmp(tag, "br") || !strcmp(tag, "br/") || !strcmp(tag, "/p"))
                ++line;
            cur = NULL;
            p = e + 1;
            continue;
        }
        char ch = *p++;
        if (ch == '&') {
            static const struct { const char *name; char ch; } ents[] = {
                {"lt;", '<'}, {"gt;", '>'}, {"amp;", '&'}, {"quot;", '"'}, {"apos;", '\''}, {"nbsp;", ' '}};
            for (size_t i = 0; i < sizeof ents / sizeof ents[0]; ++i)
                if (!strncmp(p, ents[i].name, strlen(ents[i].name))) {
                    ch = ents[i].ch;
                    p += strlen(ents[i].name);
                    break;
                }
        }
        if (ch == '\n') {
            ++line;
            cur = NULL;
            continue;
        }
        if (!cur || cur->rgb != stack_rgb[depth] || cur->size != stack_size[depth] || cur->line != line) {
            if (n >= SPANS)
                break;
            cur = &spans[n++];
            memset(cur, 0, sizeof *cur);
            cur->rgb = stack_rgb[depth];
            cur->size = stack_size[depth];
            cur->line = line;
        }
        size_t l = strlen(cur->text);
        if (l + 1 < TEXT) {
            cur->text[l] = ch;
            cur->text[l + 1] = 0;
        }
    }
    return n;
}

int mu_label_html(mu_label_fonts *f, const char *html, uint32_t rgb0, int32_t size0, int align, int shadow,
                  mu_label_image *out)
{
    memset(out, 0, sizeof *out);
    span *spans = calloc(SPANS, sizeof *spans);
    if (!spans)
        return 1;
    int n = parse(html ? html : "", rgb0, size0, spans);
    int lines = 0;
    for (int i = 0; i < n; ++i) {
        mu_label_extent(f, spans[i].size, spans[i].text, &spans[i].w, &spans[i].h);
        if (spans[i].line + 1 > lines)
            lines = spans[i].line + 1;
    }
    int32_t line_w[32] = {0}, line_h[32] = {0}, width = 0, height = 0;
    if (lines > 32)
        lines = 32;
    for (int i = 0; i < n; ++i) {
        if (spans[i].line >= 32)
            continue;
        spans[i].x = line_w[spans[i].line];
        line_w[spans[i].line] += spans[i].w;
        if (spans[i].h > line_h[spans[i].line])
            line_h[spans[i].line] = spans[i].h;
    }
    for (int l = 0; l < lines; ++l) {
        if (!line_h[l])
            line_h[l] = size0;
        if (line_w[l] > width)
            width = line_w[l];
        height += line_h[l];
    }
    if (width <= 0 || height <= 0) {
        free(spans);
        return 0;
    }
    width += 2;
    height += 2;
    out->width = width;
    out->height = height;
    out->rgba = calloc((size_t)width * (size_t)height, 4);
    if (!out->rgba) {
        free(spans);
        return 1;
    }
    for (int i = 0; i < n; ++i) {
        span *s = &spans[i];
        if (s->line >= 32 || s->w <= 0)
            continue;
        mu_ui_font *font = pick(f, s->size);
        if (!font)
            continue;
        int32_t y0 = 0;
        for (int l = 0; l < s->line; ++l)
            y0 += line_h[l];
        int32_t x0 = s->x + (align ? (width - 2 - line_w[s->line]) / 2 : 0);
        int32_t stride = ((s->w * 24 + 31) & ~31) >> 3;
        uint8_t *dib = calloc((size_t)stride * (size_t)s->h, 1);
        if (!dib)
            continue;
        mu_ui_gdi gdi = mu_ui_font_gdi(font);
        gdi.text_out(gdi.user, dib, stride, s->w, s->h, 0, 0, s->text, (int)strlen(s->text));
        for (int pass = shadow ? 0 : 1; pass < 2; ++pass)
            for (int32_t y = 0; y < s->h; ++y)
                for (int32_t x = 0; x < s->w; ++x) {
                    uint8_t v = dib[y * stride + x * 3];
                    if (!v)
                        continue;
                    int32_t X = x0 + x + (pass ? 0 : 1), Y = y0 + y + (pass ? 0 : 1);
                    if (X < 0 || Y < 0 || X >= width || Y >= height)
                        continue;
                    uint8_t *o = out->rgba + ((size_t)Y * (size_t)width + (size_t)X) * 4;
                    if (pass) {
                        o[0] = (uint8_t)(s->rgb >> 16);
                        o[1] = (uint8_t)(s->rgb >> 8);
                        o[2] = (uint8_t)s->rgb;
                        o[3] = v;
                    } else if (!o[3]) {
                        o[0] = o[1] = o[2] = 0;
                        o[3] = (uint8_t)(v * 3 / 4);
                    }
                }
        free(dib);
    }
    free(spans);
    return 0;
}

void mu_label_image_free(mu_label_image *image)
{
    free(image->rgba);
    memset(image, 0, sizeof *image);
}

static void blend_px(uint8_t *p, uint8_t r, uint8_t g, uint8_t b, float a)
{
    if (a <= 0.0f)
        return;
    if (a > 1.0f)
        a = 1.0f;
    p[0] = (uint8_t)((float)p[0] * (1.0f - a) + (float)r * a + 0.5f);
    p[1] = (uint8_t)((float)p[1] * (1.0f - a) + (float)g * a + 0.5f);
    p[2] = (uint8_t)((float)p[2] * (1.0f - a) + (float)b * a + 0.5f);
    float da = (float)p[3] / 255.0f;
    p[3] = (uint8_t)((da + a * (1.0f - da)) * 255.0f + 0.5f);
}

void mu_label_blend(uint8_t *frame, int32_t width, int32_t height, const mu_label_image *img, int32_t x, int32_t y,
                    float alpha)
{
    if (!img->rgba)
        return;
    for (int32_t j = 0; j < img->height; ++j) {
        int32_t Y = y + j;
        if (Y < 0 || Y >= height)
            continue;
        for (int32_t i = 0; i < img->width; ++i) {
            int32_t X = x + i;
            if (X < 0 || X >= width)
                continue;
            const uint8_t *s = img->rgba + ((size_t)j * (size_t)img->width + (size_t)i) * 4;
            if (s[3])
                blend_px(frame + ((size_t)Y * (size_t)width + (size_t)X) * 4, s[0], s[1], s[2],
                         (float)s[3] / 255.0f * alpha);
        }
    }
}

void mu_label_fill(uint8_t *frame, int32_t width, int32_t height, int32_t x, int32_t y, int32_t w, int32_t h,
                   const uint8_t rgba[4])
{
    for (int32_t Y = y < 0 ? 0 : y; Y < y + h && Y < height; ++Y)
        for (int32_t X = x < 0 ? 0 : x; X < x + w && X < width; ++X)
            blend_px(frame + ((size_t)Y * (size_t)width + (size_t)X) * 4, rgba[0], rgba[1], rgba[2],
                     (float)rgba[3] / 255.0f);
}

void mu_label_frame(uint8_t *frame, int32_t width, int32_t height, int32_t x, int32_t y, int32_t w, int32_t h,
                    const uint8_t rgba[4])
{
    mu_label_fill(frame, width, height, x, y, w, 1, rgba);
    mu_label_fill(frame, width, height, x, y + h - 1, w, 1, rgba);
    mu_label_fill(frame, width, height, x, y + 1, 1, h - 2, rgba);
    mu_label_fill(frame, width, height, x + w - 1, y + 1, 1, h - 2, rgba);
}
