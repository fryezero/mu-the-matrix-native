/* Reconstructed login-scene 2D overlay (NATIVE-UI-001).  See ui_login.h. */
#include "ui_login.h"

#include <stdio.h>
#include <string.h>

static void emit(mu_ui_state *state, int op, const uint32_t *words, int count)
{
    if (state->sink.call)
        state->sink.call(state->sink.user, op, words, count, NULL, 0);
}

static uint32_t fbits(float value)
{
    uint32_t word;
    memcpy(&word, &value, 4);
    return word;
}

void mu_ui_login_version(const uint8_t bytes[5], char out[6])
{
    for (uint32_t i = 0; i < 5; ++i)
        out[i] = (char)(uint8_t)((uint32_t)bytes[i] - (i + 1));
    out[5] = 0;
}

/* sprintf(buffer, format, version) for the one-%s format the client passes. */
static void format_version(char *out, size_t size, const char *format, const char *version)
{
    size_t n = 0;
    for (const char *p = format; *p && n + 1 < size; ++p) {
        if (p[0] == '%' && p[1] == 's') {
            for (const char *v = version; *v && n + 1 < size; ++v)
                out[n++] = *v;
            ++p;
        } else if (p[0] == '%' && p[1] == '%') {
            out[n++] = '%';
            ++p;
        } else {
            out[n++] = *p;
        }
    }
    out[n] = 0;
}

void mu_ui_login_overlay(mu_ui_state *state, mu_ui_text *text, float *fade, uint32_t screen_width640,
                         const mu_ui_login_text *strings)
{
    char buffer[260], version[6];
    int32_t cx, cy;
    uint32_t words[4];
    mu_ui_bitmap *logo;
    float rate_x, rate_y, width, height, x, y, u_width, v_height, v;

    *fade = *fade + 0.02f;
    if (*fade > 10.0f)
        *fade = 10.0f;
    mu_ui_enable_alpha_blend(state);
    v = *fade - 0.3f;
    words[0] = words[1] = words[2] = words[3] = fbits(v);
    emit(state, MU_GL_COLOR4F, words, 4);
    mu_ui_enable_alpha_test(state, 1);
    words[0] = words[1] = words[2] = words[3] = fbits(*fade);
    emit(state, MU_GL_COLOR4F, words, 4);

    logo = state->lookup ? state->lookup(state->lookup_user, 0x7b1e) : NULL;   /* FindTexture 0x00c97c2d */
    rate_x = 640.0f / (float)(double)state->window_width;
    rate_y = 480.0f / (float)(double)state->window_height;
    width = (float)(logo ? logo->image_width : 0) * rate_x;
    height = (float)(logo ? logo->image_height : 0) * rate_y;
    u_width = ((float)(logo ? logo->image_width : 0) - 0.5f) / (logo ? logo->width : 0.0f);
    v_height = ((float)(logo ? logo->image_height : 0) - 0.5f) / (logo ? logo->height : 0.0f);
    y = (float)(double)state->window_height * 0.05f;
    x = (float)(double)state->window_width * 0.5f * rate_x - width * 0.5f;
    mu_ui_render_color_bitmap(state, 0x7b1f, x, y, width, height, 0.0f, 0.0f, u_width, v_height, 0x4cffffffu);
    mu_ui_render_color_bitmap(state, 0x7b1e, x, y, width, height, 0.0f, 0.0f, u_width, v_height, 0xffffffffu);

    /* g_pRenderText->SetFont(g_hFont): SelectObject on the font DC (GDI boundary) */
    words[0] = words[1] = words[2] = fbits(1.0f);
    emit(state, MU_GL_COLOR3F, words, 3);
    mu_ui_text_set_back_color(text, 0, 0, 0, 0);
    mu_ui_text_set_color(text, 0xff, 0xff, 0xff, 0xff);

    snprintf(buffer, sizeof buffer, "%s", strings->text454 ? strings->text454 : "");
    mu_ui_text_extent(state, text, buffer, (int)strlen(buffer), &cx, &cy);
    mu_ui_render_text(state, text, (int32_t)(0x12cu - (uint32_t)cx * 0x280u / state->window_width),
                      (int32_t)(0x1e0u - (uint32_t)cy * 0x280u / state->window_width - 1u), buffer, 0, 0, 1, NULL);

    snprintf(buffer, sizeof buffer, "%s", strings->text455 ? strings->text455 : "");
    mu_ui_text_extent(state, text, buffer, (int)strlen(buffer), &cx, &cy);
    mu_ui_render_text(state, text, 0x12c, (int32_t)(0x1e0u - (uint32_t)cy * 0x280u / state->window_width - 1u),
                      buffer, 0, 0, 1, NULL);

    mu_ui_login_version(strings->version_bytes, version);
    format_version(buffer, sizeof buffer, strings->format456 ? strings->format456 : "", version);
    mu_ui_text_extent(state, text, buffer, (int)strlen(buffer), &cx, &cy);
    mu_ui_render_text(state, text,
                      (int32_t)(screen_width640 - (uint32_t)cx * 0x1e0u / state->window_height - 0xau),
                      (int32_t)(0x1e0u - (uint32_t)cy * 0x280u / state->window_width - 1u), buffer, 0, 0, 1, NULL);
}
