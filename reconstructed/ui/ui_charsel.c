/* Reconstructed character-select window CCharSelMainWin (NATIVE-CHARSEL-001). See ui_charsel.h. */
#include "ui_charsel.h"

#include <stdio.h>
#include <string.h>

#define BITMAP_DECO 0x7b10       /* Interface\deco.tga */
#define BITMAP_CREATE 0x7b11     /* Interface\b_create.tga */
#define BITMAP_MENU 0x7b12       /* Interface\server_menu_b_all.tga */
#define BITMAP_CONNECT 0x7b13    /* Interface\b_connect.tga */
#define BITMAP_DELETE 0x7b14     /* Interface\b_delete.tga */

enum { BTN_CREATE, BTN_MENU, BTN_CONNECT, BTN_DELETE };

static void release_controls(mu_ui_ctx *ctx, mu_ui_win *base);

static uint32_t fbits(float value)
{
    uint32_t word;
    memcpy(&word, &value, sizeof word);
    return word;
}

static void gl_color4f(mu_ui_state *state, float r, float g, float b, float a)
{
    uint32_t words[4] = {fbits(r), fbits(g), fbits(b), fbits(a)};
    if (state->sink.call)
        state->sink.call(state->sink.user, MU_GL_COLOR4F, words, 4, NULL, 0);
}

const mu_ui_win_class mu_ui_charsel_win_class = {
    mu_ui_win_release,                        /* 0x0120ce41 */
    release_controls,                         /* 0x009a5164 */
    mu_ui_charsel_win_set_position,           /* 0x009a4be1 */
    mu_ui_charsel_win_cursor_in_win,          /* 0x009a4d9f */
    mu_ui_charsel_win_show,                   /* 0x009a4d2c */
    mu_ui_win_render,                         /* 0x0120d26d */
    mu_ui_win_no_controls,                    /* 0x00982877 */
    mu_ui_win_nop_delta,                      /* 0x0098290f */
    mu_ui_win_nop,                            /* 0x0098286e */
    mu_ui_charsel_win_update_while_active,    /* 0x009a5197 */
    mu_ui_charsel_win_render_controls,        /* 0x009a533d */
};

void mu_ui_charsel_win_init(mu_ui_charsel_win *win, mu_ui_charsel_input *input)
{
    memset(win, 0, sizeof *win);
    mu_ui_win_init(&win->win, &mu_ui_charsel_win_class);
    for (int i = 0; i < 2; ++i)
        mu_ui_sprite_init(&win->sprites[i]);
    for (int i = 0; i < 4; ++i)
        mu_ui_button_init(&win->buttons[i]);
    win->input = input;
}

static void release_controls(mu_ui_ctx *ctx, mu_ui_win *base)
{
    mu_ui_charsel_win *win = (mu_ui_charsel_win *)base;
    (void)ctx;
    for (int i = 0; i < 2; ++i) {        /* CSprite::Release 0x010ad814 */
        win->sprites[i].bitmap = NULL;
        win->sprites[i].has_frames = 0;
    }
}

static int live(const mu_ui_charsel_win *win, int32_t index)
{
    return index >= 0 && index < MU_UI_CHARSEL_SLOTS && win->input->slots[index].live;
}

void mu_ui_charsel_win_create(mu_ui_ctx *ctx, mu_ui_charsel_win *win)
{
    static const int16_t tips[3] = {0x6ae, 0x6cb, 0x6cc};
    mu_ui_state *state = ctx->state;
    mu_ui_sprite_create(state, &win->sprites[0], 0xbd, 0x67, BITMAP_DECO, 0, 0, 0, 0, 1.0f, 1.0f);
    mu_ui_sprite_create(state, &win->sprites[1], ctx->input.screen_width - 0x10a, 0x15, -1, 0, 0, 0, 0, 1.0f, 1.0f);
    win->sprites[1].red = 0;             /* 0x009a47be(0, 0, 0) */
    win->sprites[1].green = 0;
    win->sprites[1].blue = 0;
    win->sprites[1].alpha = 0x8f;        /* 0x009828d6 */
    mu_ui_button_create(ctx, &win->buttons[BTN_CREATE], 0x36, 0x1e, BITMAP_CREATE, 4, 2, 1, 3, -1, -1, -1, -1);
    mu_ui_button_create(ctx, &win->buttons[BTN_MENU], 0x36, 0x1e, BITMAP_MENU, 3, 2, 1, -1, -1, -1, -1, -1);
    mu_ui_button_create(ctx, &win->buttons[BTN_CONNECT], 0x36, 0x1e, BITMAP_CONNECT, 4, 2, 1, 3, -1, -1, -1, -1);
    mu_ui_button_create(ctx, &win->buttons[BTN_DELETE], 0x36, 0x1e, BITMAP_DELETE, 4, 2, 1, 3, -1, -1, -1, -1);
    int32_t button_w = mu_ui_sprite_width(&win->buttons[BTN_CREATE].sprite);
    int32_t button_h = mu_ui_sprite_height(&win->buttons[BTN_CREATE].sprite);
    mu_ui_win_create(ctx, &win->win, mu_ui_sprite_width(&win->sprites[1]) + button_w * 4 + 6, button_h, -2, 0);
    for (int i = 0; i < 4; ++i)
        mu_ui_win_register_button(&win->win, &win->buttons[i]);
    win->warning = 0;
    for (int32_t i = 0; i < 10; ++i)
        if (live(win, i) && (win->input->slots[i].flags & 0x10)) {
            win->warning = 1;
            break;
        }
    win->tip = tips[win->input->random % 3];
}

void mu_ui_charsel_win_set_position(mu_ui_ctx *ctx, mu_ui_win *base, int32_t x, int32_t y)
{
    mu_ui_charsel_win *win = (mu_ui_charsel_win *)base;
    mu_ui_win_set_position(ctx, base, x, y);
    int32_t w = mu_ui_sprite_width(&win->buttons[BTN_CREATE].sprite);
    mu_ui_sprite_set_position(&win->buttons[BTN_CREATE].sprite, x, y, 3);
    mu_ui_sprite_set_position(&win->buttons[BTN_MENU].sprite, x + w + 1, y, 3);
    mu_ui_sprite_set_position(&win->sprites[1], mu_ui_sprite_x(&win->buttons[BTN_MENU].sprite) + w + 2, y + 5, 3);
    int32_t right = base->width + x;
    mu_ui_sprite_set_position(&win->sprites[0], right - (mu_ui_sprite_width(&win->sprites[0]) - 0x16), y - 0x3b, 3);
    mu_ui_sprite_set_position(&win->buttons[BTN_DELETE].sprite, right - w, y, 3);
    mu_ui_sprite_set_position(&win->buttons[BTN_CONNECT].sprite, right - (w + w + 1), y, 3);
}

int mu_ui_charsel_win_cursor_in_win(mu_ui_ctx *ctx, mu_ui_win *base, int32_t area)
{
    if (!base->show)
        return 0;
    if (area == MU_UI_WA_MOVE)
        return 0;
    return mu_ui_win_cursor_in_win(ctx, base, area);
}

void mu_ui_charsel_win_show(mu_ui_ctx *ctx, mu_ui_win *base, int show)
{
    mu_ui_charsel_win *win = (mu_ui_charsel_win *)base;
    mu_ui_win_show(ctx, base, show);
    for (int i = 0; i < 2; ++i)
        mu_ui_sprite_show(&win->sprites[i], show);
    for (int i = 0; i < 4; ++i)
        mu_ui_button_show(&win->buttons[i], show);
}

static void open_create(mu_ui_ctx *ctx)
{
    /* 0x00b49bf4(1) on GFx +0x22c, 0x009a5920(0), 0x00b4b684() */
    mu_ui_ctx_event(ctx, MU_UI_EVENT_CHARSEL_CREATE, 0);
}

void mu_ui_charsel_win_update_display(mu_ui_ctx *ctx, mu_ui_charsel_win *win)
{
    const mu_ui_charsel_input *in = win->input;
    win->buttons[BTN_CREATE].enable = 0;
    if (!in->flag_95f75d) {
        if (in->slot_mode) {
            for (int32_t i = 0; i < in->slot_count; ++i) {
                if (i >= MU_UI_CHARSEL_SLOTS)
                    break;            /* records beyond the synthetic table count as live */
                if (!live(win, i)) {
                    win->buttons[BTN_CREATE].enable = 1;
                    break;
                }
            }
        } else {
            for (int32_t i = 0; i < 10; ++i)
                if (!live(win, i)) {
                    win->buttons[BTN_CREATE].enable = 1;
                    break;
                }
        }
    }
    if (in->selected > -1) {
        win->buttons[BTN_CONNECT].enable = 1;
        if (!in->flag_95f75d)
            win->buttons[BTN_DELETE].enable = 1;
    } else {
        win->buttons[BTN_CONNECT].enable = 0;
        win->buttons[BTN_DELETE].enable = 0;
    }
    if (in->flag_95f75d || in->gfx_create_open)
        return;
    for (int32_t i = 0; i < 10; ++i)
        if (live(win, i))
            return;
    open_create(ctx);   /* an empty list opens the create-character interface */
}

void mu_ui_charsel_win_update_while_active(mu_ui_ctx *ctx, mu_ui_win *base, double delta)
{
    mu_ui_charsel_win *win = (mu_ui_charsel_win *)base;
    if (0.0 > delta)
        return;
    if (win->input->gfx_movie_busy || win->input->gfx_blocked)
        return;
    if (win->buttons[BTN_CONNECT].click) {
        if (win->input->enter_refused != 1)   /* 0x009a5236: only 1 refuses */
            mu_ui_ctx_event(ctx, MU_UI_EVENT_CHARSEL_CONNECT, 0);
    } else if (win->buttons[BTN_MENU].click) {
        mu_ui_ctx_event(ctx, MU_UI_EVENT_CHARSEL_MENU, 0);
    } else if (win->buttons[BTN_CREATE].click) {
        open_create(ctx);
    } else if (win->buttons[BTN_DELETE].click) {
        mu_ui_charsel_win_delete(ctx, win);
    }
}

void mu_ui_charsel_win_delete(mu_ui_ctx *ctx, mu_ui_charsel_win *win)
{
    const mu_ui_charsel_input *in = win->input;
    int32_t index = in->selected;
    /* the character table gives NULL only outside 0..399; slots past the
     * synthetic table are refused here */
    if (index < 0 || index >= MU_UI_CHARSEL_SLOTS)
        return;
    const mu_ui_charsel_slot *c = &in->slots[index];
    if (c->byte_17 != 0xff) {
        mu_ui_ctx_event(ctx, MU_UI_EVENT_CHARSEL_MESSAGE, 0x676);
        return;
    }
    if (!in->server_flag && c->level >= 0x2bc) {
        mu_ui_ctx_event(ctx, MU_UI_EVENT_CHARSEL_NOTICE, 0x83);
        return;
    }
    if (c->flags & 0x12) {
        mu_ui_ctx_event(ctx, MU_UI_EVENT_CHARSEL_MESSAGE, 0x1a1);
        return;
    }
    if (c->byte_3634 == 1) {
        mu_ui_ctx_event(ctx, MU_UI_EVENT_CHARSEL_MESSAGE, 0x166e);
        return;
    }
    mu_ui_ctx_event(ctx, MU_UI_EVENT_CHARSEL_CONFIRM, index);
}

void mu_ui_charsel_win_render_controls(mu_ui_ctx *ctx, mu_ui_win *base)
{
    mu_ui_charsel_win *win = (mu_ui_charsel_win *)base;
    mu_ui_state *state = ctx->state;
    for (int i = 0; i < 2; ++i)
        mu_ui_sprite_render(state, &win->sprites[i]);
    mu_ui_enable_alpha_test(state, 1);                 /* 0x0184a990(1) */
    gl_color4f(state, 1.0f, 1.0f, 1.0f, 1.0f);
    mu_ui_ctx_set_font(ctx, ctx->fonts.fixed);
    mu_ui_ctx_set_text_color(ctx, 0xffffffffu);
    mu_ui_ctx_set_back_color(ctx, 0);
    mu_ui_ctx_set_text_color(ctx, 0xff27d9ffu);
    const mu_ui_sprite *bar = &win->sprites[1];
    mu_ui_ctx_render_text(ctx, mu_ui_cvtt((float)mu_ui_sprite_x(bar) / state->screen_rate_x),
                          mu_ui_cvtt((float)(mu_ui_sprite_y(bar) + 7) / state->screen_rate_y),
                          mu_ui_ctx_global_text(ctx, win->tip),
                          mu_ui_cvtt((float)mu_ui_sprite_width(bar) / state->screen_rate_x), 0, 3);
    if (win->warning) {
        if (ctx->text) {
            mu_ui_text_set_color(ctx->text, 0, 0, 0, 0xff);           /* 0x011a0998: black text */
            mu_ui_text_set_back_color(ctx->text, 0xff, 0xff, 0, 0x80);/* 0x011a09f3: translucent yellow box */
        }
        mu_ui_ctx_render_text(ctx, 0x140, 0x14a, mu_ui_ctx_global_text(ctx, 0x1b4), 0, 0, 8);
        mu_ui_ctx_render_text(ctx, 0x140, 0x15c, mu_ui_ctx_global_text(ctx, 0x1b5), 0, 0, 8);
    }
    mu_ui_win_render_buttons(ctx, base);
}

void mu_ui_charsel_win_place(mu_ui_ctx *ctx, mu_ui_charsel_win *win)
{
    win->win.cls->set_position(ctx, &win->win, 0x16, ctx->input.screen_height - win->win.height - 0xe);
}
