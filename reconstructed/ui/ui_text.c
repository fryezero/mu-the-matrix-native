/* Reconstructed GDI text path (NATIVE-UI-001).  See ui_text.h. */
#include "ui_text.h"

#include <string.h>

#define BITMAP_FONT 0x7532u

static void emit(mu_ui_state *state, int op, const uint32_t *words, int count, const void *data, size_t bytes)
{
    if (state->sink.call)
        state->sink.call(state->sink.user, op, words, count, data, bytes);
}

int32_t mu_ui_text_dib_stride(int32_t width)
{
    return ((width * 0x18 + 0x1f) & ~0x1f) >> 3;
}

void mu_ui_text_init(mu_ui_text *text, const mu_ui_state *state)
{
    text->dib_width = mu_ui_cvtt(640.0f * state->screen_rate_x);
    text->dib_height = -mu_ui_cvtt(-(480.0f * state->screen_rate_y));   /* biHeight is negative (top-down) */
    text->back_color = 0;
    text->text_color = 0xffffffffu;
}

void mu_ui_text_set_color(mu_ui_text *text, uint8_t r, uint8_t g, uint8_t b, uint8_t a)
{
    text->text_color = (uint32_t)r + ((uint32_t)g << 8) + ((uint32_t)b << 16) + ((uint32_t)a << 24);
}

void mu_ui_text_set_back_color(mu_ui_text *text, uint8_t r, uint8_t g, uint8_t b, uint8_t a)
{
    text->back_color = (uint32_t)r + ((uint32_t)g << 8) + ((uint32_t)b << 16) + ((uint32_t)a << 24);
}

void mu_ui_text_extent(mu_ui_state *state, mu_ui_text *text, const char *string, int length, int32_t *cx,
                       int32_t *cy)
{
    uint32_t words[1] = {(uint32_t)length};
    *cx = 0;
    *cy = 0;
    emit(state, MU_GDI_GETTEXTEXTENT, words, 1, string, (size_t)length);
    if (text->gdi.extent)
        text->gdi.extent(text->gdi.user, string, length, cx, cy);
}

void mu_ui_render_text(mu_ui_state *state, mu_ui_text *text, int32_t x, int32_t y, const char *string,
                       int32_t box_width, int32_t box_height, int32_t sort, int32_t out_size[2])
{
    int32_t size_cx, size_cy, clip, offset_x, text_width, chunks, flag, i;
    float pos_x, pos_y, box_w, box_h, width, height;
    float rate_x = state->screen_rate_x, rate_y = state->screen_rate_y;
    size_t length;

    if (string == NULL || (string[0] == 0 && box_width == 0))
        return;
    length = strlen(string);
    if (length == 0 && box_width == 0)
        return;
    mu_ui_text_extent(state, text, string, (int)length, &size_cx, &size_cy);
    if (string[0] == 0)
        mu_ui_text_extent(state, text, "0", 1, &size_cx, &size_cy);
    pos_x = (float)x * rate_x;
    pos_y = (float)y * rate_y;
    box_w = (float)box_width * rate_x;
    box_h = (float)box_height * rate_y;
    width = (float)size_cx;
    height = (float)size_cy;
    if (box_w == 0.0f)
        box_w = (float)size_cx;
    if (box_h == 0.0f)
        box_h = (float)size_cy;
    offset_x = 0;
    clip = 0;
    switch (sort) {
    case 2:
        if (width > box_w) {
            clip = mu_ui_cvtt(width - box_w);
            width = box_w;
        }
        break;
    case 1:
        if (width > box_w)
            width = box_w;
        break;
    case 3:
        if (width > box_w) {
            clip = mu_ui_cvtt((width - box_w) / 2.0f);
            width = box_w;
        } else {
            offset_x = mu_ui_cvtt((box_w - width) / 2.0f);
        }
        break;
    case 4:
    case 7:
        if (width > box_w) {
            clip = mu_ui_cvtt(width - box_w);
            width = box_w;
        } else {
            offset_x = mu_ui_cvtt(box_w - width);
        }
        if (sort == 7)
            pos_x = pos_x - box_w;
        break;
    case 8:
        if (width > box_w) {
            clip = mu_ui_cvtt((width - box_w) / 2.0f);
            width = box_w;
        } else {
            offset_x = mu_ui_cvtt((box_w - width) / 2.0f);
        }
        pos_x = pos_x - box_w / 2.0f;
        break;
    default:
        break;
    }
    if (text->back_color != 0) {
        uint32_t color[4] = {text->back_color & 0xff, (text->back_color >> 8) & 0xff,
                             (text->back_color >> 16) & 0xff, text->back_color >> 24};
        mu_ui_enable_alpha_test(state, 1);
        emit(state, MU_GL_COLOR4UB, color, 4, NULL, 0);
        mu_ui_render_color(state, pos_x / rate_x, pos_y / rate_y, box_w / rate_x, box_h / rate_y, 0.0f, 0);
        mu_ui_end_render_color(state);
    }
    if (string[0] != '\n') {
        uint32_t back = 0, fore = 0xffffff, out[3] = {0, 0, (uint32_t)length};
        emit(state, MU_GDI_SETBKCOLOR, &back, 1, NULL, 0);
        emit(state, MU_GDI_SETTEXTCOLOR, &fore, 1, NULL, 0);
        emit(state, MU_GDI_TEXTOUT, out, 3, string, length);
        if (text->gdi.text_out && text->dib)
            text->gdi.text_out(text->gdi.user, text->dib, mu_ui_text_dib_stride(text->dib_width), text->dib_width,
                               text->dib_height, 0, 0, string, (int)length);
    }
    text_width = mu_ui_cvtt(width);
    flag = (text_width % 256) >= 0 ? 1 : 0;
    chunks = mu_ui_cvtt(width / 256.0f + (float)flag);
    for (i = 0; i < chunks; ++i) {
        int32_t chunk_width = 0x100, chunk_height = mu_ui_cvtt(height);
        if (i == chunks - 1)
            chunk_width = text_width % 256;
        mu_ui_write_text(state, text, i * 256 * 3 + clip, chunk_width, chunk_height);
        mu_ui_upload_text(state, text, mu_ui_cvtt((float)(i << 8) + pos_x + (float)offset_x),
                          mu_ui_cvtt(pos_y), chunk_width, chunk_height);
    }
    if (out_size) {
        out_size[0] = mu_ui_cvtt(width / rate_x);
        out_size[1] = mu_ui_cvtt(height / rate_y);
    }
}

void mu_ui_write_text(mu_ui_state *state, mu_ui_text *text, int32_t offset, int32_t width, int32_t height)
{
    int32_t screen_w = mu_ui_cvtt(640.0f * state->screen_rate_x);
    int32_t screen_h = mu_ui_cvtt(480.0f * state->screen_rate_y);
    int32_t stride = ((screen_w * 0x18 + 0x1f) & ~0x1f) >> 3;
    mu_ui_bitmap *font = state->lookup ? state->lookup(state->lookup_user, BITMAP_FONT) : NULL;
    int32_t row, column;
    if (!font || !font->buffer || !text->dib)
        return;
    for (row = 0; row < height; ++row) {
        int32_t source = row * stride + offset;
        int32_t target = (row << 8) << 2;
        for (column = 0; column < width; ++column) {
            if (source > stride * screen_h || target > 0x8000)
                return;
            if (text->dib[source] == 0xff)
                memcpy(font->buffer + target, &text->text_color, 4);
            else
                memset(font->buffer + target, 0, 4);
            source += 3;
            target += 4;
        }
    }
}

void mu_ui_upload_text(mu_ui_state *state, mu_ui_text *text, int32_t x, int32_t y, int32_t width,
                       int32_t height)
{
    mu_ui_bitmap *font = state->lookup ? state->lookup(state->lookup_user, BITMAP_FONT) : NULL;
    float u = 0.0f, v = 0.0f, u_width, v_height;
    (void)text;
    if (!font)
        return;
    if (x < 0) {
        u = ((float)(-x) + 0.01f) / font->width;
        width += x;
        x = 0;
    } else if (x + width > (int32_t)state->window_width) {
        width = (int32_t)state->window_width - x;
    }
    if (y < 0) {
        v = ((float)(-y) + 0.01f) / font->height;
        height += y;
        y = 0;
    } else if (y + height > (int32_t)state->window_height) {
        height = (int32_t)state->window_height - y;
    }
    if (width > 0 && height > 0 && x + width > 0 && y + height > 0) {
        uint32_t bind[2] = {0x0de1, font->texture};
        int32_t tw = mu_ui_cvtt(font->width), th = mu_ui_cvtt(font->height);
        uint32_t image[9] = {0x0de1, 0, font->components, (uint32_t)tw, (uint32_t)th, 0, 0x1908, 0x1401, 0};
        emit(state, MU_GL_BINDTEXTURE, bind, 2, NULL, 0);
        emit(state, MU_GL_TEXIMAGE2D, image, 9, font->buffer,
             font->buffer ? (size_t)tw * (size_t)th * font->components : 0);
        u_width = ((float)width + 0.01f) / font->width;
        v_height = ((float)height + 0.01f) / font->height;
        mu_ui_render_bitmap(state, (int32_t)BITMAP_FONT, (float)x, (float)y, (float)width, (float)height, u, v,
                            u_width, v_height, 0, 0, 0.0f);
    }
}

int32_t mu_ui_font_height(uint32_t window_width)
{
    if (window_width < 0x320)
        return 0xc;
    if (window_width < 0x400)
        return 0xd;
    if (window_width < 0x500)
        return 0xe;
    if (window_width < 0x690)
        return 0xf;
    return 0x10;
}

mu_ui_font_spec mu_ui_font_for(uint32_t window_width, int which)
{
    mu_ui_font_spec spec;
    int32_t base = mu_ui_font_height(window_width) - 1;
    spec.quality = 3;
    spec.face_text = 0;
    switch (which) {
    case MU_UI_FONT_BOLD:
        spec.height = base;
        spec.weight = 700;
        break;
    case MU_UI_FONT_BIG:
        spec.height = base << 1;
        spec.weight = 700;
        break;
    case MU_UI_FONT_FIXED:
        spec.height = 0xd - 1;
        spec.weight = 400;
        spec.face_text = 18;
        break;
    default:
        spec.height = base;
        spec.weight = 400;
        break;
    }
    return spec;
}
