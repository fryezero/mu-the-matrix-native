/* Reconstructed legacy window/widget layer (NATIVE-UI-002).  See ui_widget.h. */
#include "ui_widget.h"

#include <string.h>

static void emit(mu_ui_state *state, int op, const uint32_t *words, int count)
{
    if (state->sink.call)
        state->sink.call(state->sink.user, op, words, count, NULL, 0);
}

/* ---- context: text facade, GlobalText, events --------------------------- */

void mu_ui_ctx_set_font(mu_ui_ctx *ctx, uint32_t font)
{
    emit(ctx->state, MU_GDI_SELECTOBJECT, &font, 1);
}

void mu_ui_ctx_set_text_color(mu_ui_ctx *ctx, uint32_t color)
{
    if (ctx->text)
        ctx->text->text_color = color;
}

void mu_ui_ctx_set_back_color(mu_ui_ctx *ctx, uint32_t color)
{
    if (ctx->text)
        ctx->text->back_color = color;
}

void mu_ui_ctx_render_text(mu_ui_ctx *ctx, int32_t x, int32_t y, const char *string, int32_t box_width,
                           int32_t box_height, int32_t sort)
{
    if (ctx->text)
        mu_ui_render_text(ctx->state, ctx->text, x, y, string, box_width, box_height, sort, NULL);
}

const char *mu_ui_ctx_global_text(mu_ui_ctx *ctx, int32_t index)
{
    const char *text = ctx->global_text ? ctx->global_text(ctx->global_text_user, index) : NULL;
    return text ? text : "";
}

void mu_ui_ctx_event(mu_ui_ctx *ctx, int32_t event, int32_t argument)
{
    uint32_t words[2] = {(uint32_t)event, (uint32_t)argument};
    emit(ctx->state, MU_UI_EVENT, words, 2);
}

/* ---- CButton ------------------------------------------------------------- */

void mu_ui_button_init(mu_ui_button *button)
{
    memset(button, 0, sizeof *button);
}

void mu_ui_button_release(mu_ui_button *button)
{
    button->has_text = 0;          /* ReleaseText 0x00986e46 */
    button->text[0] = 0;
    button->color_count = 0;
}

void mu_ui_button_create(mu_ui_ctx *ctx, mu_ui_button *button, int32_t width, int32_t height, int32_t texture,
                         int32_t max_frame, int32_t down, int32_t over, int32_t disable, int32_t check_up,
                         int32_t check_down, int32_t check_over, int32_t check_disable)
{
    int32_t frames[MU_UI_SPRITE_MAX_FRAMES][2];
    int32_t i;
    mu_ui_button_release(button);
    for (i = 0; i < max_frame && i < MU_UI_SPRITE_MAX_FRAMES; ++i) {
        frames[i][0] = 0;
        frames[i][1] = height * i;            /* frames are stacked vertically in the texture */
    }
    mu_ui_sprite_create_frames(ctx->state, &button->sprite, width, height, texture, max_frame,
                               (const int32_t (*)[2])frames, 0, 0, 0, 0, 1.0f, 1.0f);
    mu_ui_sprite_set_action(&button->sprite, 0, max_frame - 1, 0.0, 1);
    button->image_map[MU_UI_BTN_UP] = 0;
    button->image_map[MU_UI_BTN_DOWN] = down > -1 ? down : 0;
    button->image_map[MU_UI_BTN_OVER] = over > -1 ? over : 0;
    button->image_map[MU_UI_BTN_DISABLE] = disable;
    button->image_map[MU_UI_BTN_CHECK_UP] = check_up;
    button->image_map[MU_UI_BTN_CHECK_DOWN] = check_down > -1 ? check_down : button->image_map[MU_UI_BTN_CHECK_UP];
    button->image_map[MU_UI_BTN_CHECK_OVER] = check_over > -1 ? check_over : button->image_map[MU_UI_BTN_CHECK_UP];
    button->image_map[MU_UI_BTN_CHECK_DISABLE] = check_disable;
    button->check = 0;
    button->click = 0;
    button->active = 1;
    button->enable = 1;
}

void mu_ui_button_set_text(mu_ui_button *button, const char *text, const uint32_t *colors)
{
    int i;
    mu_ui_button_release(button);
    strncpy(button->text, text, MU_UI_BUTTON_TEXT_MAX - 1);
    button->text[MU_UI_BUTTON_TEXT_MAX - 1] = 0;
    button->has_text = 1;
    button->color_count = button->image_map[MU_UI_BTN_CHECK_UP] > -1 ? 8 : 4;
    for (i = 0; i < button->color_count; ++i)
        button->text_colors[i] = colors[i];
}

void mu_ui_button_show(mu_ui_button *button, int show)
{
    mu_ui_sprite_show(&button->sprite, show);
    if (!(uint8_t)show)
        button->click = 0;
}

int mu_ui_button_cursor_in(const mu_ui_ctx *ctx, const mu_ui_button *button)
{
    if (!button->active)
        return 0;
    return mu_ui_sprite_contains(&button->sprite, ctx->input.cursor_x, ctx->input.cursor_y);
}

static void button_state(mu_ui_button *button, int index)
{
    mu_ui_sprite_set_now_frame(&button->sprite, button->image_map[index]);
    if (button->has_text)   /* the client reads past a 4-entry table for check states without check frames */
        button->text_color = index < button->color_count ? button->text_colors[index] : 0;
}

void mu_ui_button_update(mu_ui_ctx *ctx, mu_ui_button *button, double delta)
{
    const mu_ui_input *in = &ctx->input;
    if (0.0 > delta)
        return;
    if (!button->sprite.show)
        return;
    button->text_add_y = 0.5f;
    if (button->enable) {
        if (mu_ui_button_cursor_in(ctx, button) && in->lbutton_down)
            ctx->held_button = button;
        button->click = 0;
        if (in->lbutton_up) {
            if (mu_ui_button_cursor_in(ctx, button) && ctx->held_button == button) {
                uint32_t sound = 0x19;
                button->click = 1;
                emit(ctx->state, MU_UI_SOUND, &sound, 1);    /* PlayBuffer(25, 0, 0) 0x00a6ac96 */
                if (button->image_map[MU_UI_BTN_CHECK_UP] > -1)
                    button->check = button->check ? 0 : 1;
            }
            if (ctx->held_button == button)
                ctx->held_button = NULL;
        }
        if (mu_ui_button_cursor_in(ctx, button) && ctx->held_button == NULL) {
            button_state(button, button->check ? MU_UI_BTN_CHECK_OVER : MU_UI_BTN_OVER);
        } else if (mu_ui_button_cursor_in(ctx, button) && ctx->held_button == button) {
            button->text_add_y = 1.5f;
            button_state(button, button->check ? MU_UI_BTN_CHECK_DOWN : MU_UI_BTN_DOWN);
        } else {
            button_state(button, button->check ? MU_UI_BTN_CHECK_UP : MU_UI_BTN_UP);
        }
    } else {
        button->click = 0;
        if (in->lbutton_up && ctx->held_button == button)
            ctx->held_button = NULL;
        button_state(button, button->check ? MU_UI_BTN_CHECK_DISABLE : MU_UI_BTN_DISABLE);
    }
}

void mu_ui_button_render(mu_ui_ctx *ctx, const mu_ui_button *button)
{
    mu_ui_state *state = ctx->state;
    int32_t cx = 0, cy = 0, x, y, width;
    float rel_y;
    if (!button->sprite.show)
        return;
    if (!button->enable) {
        if (button->check && button->image_map[MU_UI_BTN_CHECK_DISABLE] < 0)
            return;
        if (!button->check && button->image_map[MU_UI_BTN_DISABLE] < 0)
            return;
    }
    mu_ui_sprite_render(state, &button->sprite);
    if (!button->has_text)
        return;
    mu_ui_ctx_set_text_color(ctx, button->text_color);
    mu_ui_ctx_set_back_color(ctx, 0);
    mu_ui_ctx_set_font(ctx, ctx->fonts.fixed);
    if (ctx->text)
        mu_ui_text_extent(state, ctx->text, button->text, (int)strlen(button->text), &cx, &cy);
    rel_y = (float)(mu_ui_sprite_height(&button->sprite) - cy) / 2.0f;
    width = mu_ui_cvtt((float)mu_ui_sprite_width(&button->sprite) / state->screen_rate_x);
    y = mu_ui_cvtt(((float)mu_ui_sprite_y(&button->sprite) + rel_y) / state->screen_rate_y + button->text_add_y);
    x = mu_ui_cvtt((float)mu_ui_sprite_x(&button->sprite) / state->screen_rate_x);
    mu_ui_ctx_render_text(ctx, x, y, button->text, width, 0, 3);
}

/* ---- CWin ----------------------------------------------------------------- */

void mu_ui_win_nop(mu_ui_ctx *ctx, mu_ui_win *win) { (void)ctx; (void)win; }
int mu_ui_win_no_controls(mu_ui_ctx *ctx, mu_ui_win *win) { (void)ctx; (void)win; return 0; }
void mu_ui_win_nop_delta(mu_ui_ctx *ctx, mu_ui_win *win, double delta) { (void)ctx; (void)win; (void)delta; }

const mu_ui_win_class mu_ui_win_base_class = {
    mu_ui_win_release,           /* 0x0120ce41 */
    mu_ui_win_nop,                     /* 0x009828c4 */
    mu_ui_win_set_position,      /* 0x0120ceb4 */
    mu_ui_win_cursor_in_win,     /* 0x0120cf39 */
    mu_ui_win_show,              /* 0x0120d090 */
    mu_ui_win_render,            /* 0x0120d26d */
    mu_ui_win_no_controls,                   /* 0x00982877 */
    mu_ui_win_nop_delta,                  /* 0x0098290f */
    mu_ui_win_nop,                     /* 0x0098286e */
    mu_ui_win_nop_delta,                  /* 0x0107537c */
    mu_ui_win_nop,                     /* 0x009828cd */
};

void mu_ui_win_init(mu_ui_win *win, const mu_ui_win_class *cls)
{
    memset(win, 0, sizeof *win);
    win->cls = cls;
}

void mu_ui_win_release(mu_ui_ctx *ctx, mu_ui_win *win)
{
    int i;
    win->cls->release_controls(ctx, win);
    for (i = 0; i < win->button_count; ++i)
        mu_ui_button_release(win->buttons[i]);
    win->button_count = 0;
    win->background = NULL;
}

void mu_ui_win_create(mu_ui_ctx *ctx, mu_ui_win *win, int32_t width, int32_t height, int32_t texture, int tile)
{
    win->cls->release(ctx, win);
    if (texture > -2) {
        win->background = &win->background_storage;
        mu_ui_sprite_init(win->background);
        mu_ui_sprite_create_frames(ctx->state, win->background, width, height, texture, 0, NULL, 0, 0, tile, 0,
                                   1.0f, 1.0f);
        if (texture == -1) {
            win->background->alpha = 0x80;
            win->background->red = 0;
            win->background->green = 0;
            win->background->blue = 0;
        }
    }
    win->y = 0;
    win->x = 0;
    win->temp_x = win->x;
    win->temp_y = win->y;
    win->held_x = win->temp_x;
    win->held_y = win->temp_y;
    win->width = width;
    win->height = height;
    win->show = 0;
    win->active = 0;
    win->docking = 0;
    win->state = MU_UI_WS_NORMAL;
}

void mu_ui_win_register_button(mu_ui_win *win, mu_ui_button *button)
{
    if (win->button_count < MU_UI_WIN_MAX_BUTTONS)
        win->buttons[win->button_count++] = button;
}

void mu_ui_win_set_position(mu_ui_ctx *ctx, mu_ui_win *win, int32_t x, int32_t y)
{
    (void)ctx;
    win->x = x;
    win->y = y;
    if (win->background)
        mu_ui_sprite_set_position(win->background, x, y, 3);
}

void mu_ui_win_set_size(mu_ui_win *win, int32_t width, int32_t height, int32_t which)
{
    if (which & 1)
        win->width = width;
    if (which & 2)
        win->height = height;
    if (win->background)
        mu_ui_sprite_set_size(win->background, width, height, which);
}

static int in_rect(const mu_ui_ctx *ctx, int32_t left, int32_t top, int32_t right, int32_t bottom)
{
    int32_t x = ctx->input.cursor_x, y = ctx->input.cursor_y;
    return x >= left && x < right && y >= top && y < bottom;   /* SetRect + PtInRect */
}

int mu_ui_win_cursor_in_win(mu_ui_ctx *ctx, mu_ui_win *win, int32_t area)
{
    int i;
    if (!win->show)
        return 0;
    switch (area) {
    case MU_UI_WA_ALL:
        return in_rect(ctx, win->x, win->y, win->x + win->width, win->y + win->height);
    case MU_UI_WA_MOVE:
        return in_rect(ctx, win->x, win->y, win->x + win->width, win->y + 0x1a);
    case MU_UI_WA_BUTTON:
        for (i = 0; i < win->button_count; ++i)
            if (mu_ui_button_cursor_in(ctx, win->buttons[i]))
                return 1;
        return win->cls->cursor_in_controls(ctx, win) ? 1 : 0;
    default:
        return 0;
    }
}

void mu_ui_win_show(mu_ui_ctx *ctx, mu_ui_win *win, int show)
{
    (void)ctx;
    if (win->background)
        mu_ui_sprite_show(win->background, show);
    win->show = (uint8_t)show;
    if (!win->show)
        win->active = 0;
}

void mu_ui_win_set_active(mu_ui_win *win, int active)
{
    win->active = (uint8_t)active;
}

void mu_ui_win_update(mu_ui_ctx *ctx, mu_ui_win *win, double delta)
{
    const mu_ui_input *in = &ctx->input;
    int i;
    if (!win->show)
        return;
    if (in->lbutton_up)
        win->state = MU_UI_WS_NORMAL;
    if (win->state == MU_UI_WS_NORMAL)
        for (i = 0; i < win->button_count; ++i)
            mu_ui_button_update(ctx, win->buttons[i], delta);
    win->cls->update_while_show(ctx, win, delta);
    if (!win->active)
        return;
    if (in->lbutton_down && win->cls->cursor_in_win(ctx, win, MU_UI_WA_MOVE)) {
        win->held_x = in->cursor_x;
        win->held_y = in->cursor_y;
        win->temp_x = win->x;
        win->temp_y = win->y;
        win->state = MU_UI_WS_MOVE;
    }
    if (win->state == MU_UI_WS_MOVE) {
        win->temp_x = in->cursor_x - win->held_x + win->temp_x;
        win->temp_y = in->cursor_y - win->held_y + win->temp_y;
        if (!win->docking)
            win->cls->set_position(ctx, win, win->temp_x, win->temp_y);
        win->held_x = in->cursor_x;
        win->held_y = in->cursor_y;
    }
    win->cls->check_additional_state(ctx, win);
    win->cls->update_while_active(ctx, win, delta);
}

void mu_ui_win_render(mu_ui_ctx *ctx, mu_ui_win *win)
{
    if (!win->show)
        return;
    if (win->background)
        mu_ui_sprite_render(ctx->state, win->background);
    win->cls->render_controls(ctx, win);
}

void mu_ui_win_render_buttons(mu_ui_ctx *ctx, mu_ui_win *win)
{
    int i;
    for (i = 0; i < win->button_count; ++i)
        mu_ui_button_render(ctx, win->buttons[i]);
}

void mu_ui_win_active_buttons(mu_ui_win *win, int active)
{
    int i;
    for (i = 0; i < win->button_count; ++i)
        win->buttons[i]->active = (uint8_t)active;   /* 0x0120d363 */
}

/* ---- CWinEx --------------------------------------------------------------- */

const mu_ui_win_class mu_ui_winex_class = {
    mu_ui_winex_release,                 /* 0x0120d69e */
    mu_ui_win_nop,                             /* 0x009828c4 */
    mu_ui_winex_set_position,            /* 0x0120d73c */
    mu_ui_winex_cursor_in_win,           /* 0x0120da21 */
    mu_ui_winex_show,                    /* 0x0120db2c */
    mu_ui_winex_render,                  /* 0x0120db7e */
    mu_ui_win_no_controls,                           /* 0x00982877 */
    mu_ui_win_nop_delta,                          /* 0x0098290f */
    mu_ui_winex_check_additional_state,  /* 0x0120dbc7 */
    mu_ui_win_nop_delta,                          /* 0x0107537c */
    mu_ui_win_nop,                             /* 0x009828cd */
};

void mu_ui_winex_init(mu_ui_winex *win)
{
    memset(win, 0, sizeof *win);
    win->win.cls = &mu_ui_winex_class;
}

void mu_ui_winex_release(mu_ui_ctx *ctx, mu_ui_win *win)
{
    int i;
    win->cls->release_controls(ctx, win);
    for (i = 0; i < win->button_count; ++i)
        mu_ui_button_release(win->buttons[i]);
    win->button_count = 0;
    win->background = NULL;          /* delete[] of the five frame sprites */
}

void mu_ui_winex_create(mu_ui_ctx *ctx, mu_ui_winex *win, const mu_ui_image_info info[5], int32_t line_min,
                        int32_t line_max)
{
    mu_ui_sprite *s = win->sprites;
    int i;
    win->win.cls->release(ctx, &win->win);
    for (i = 0; i < 5; ++i)
        mu_ui_sprite_init(&s[i]);
    win->win.background = s;
    mu_ui_sprite_create_image(ctx->state, &s[MU_UI_WINEX_BACK], &info[0], 0, 0, 1, 0, 1.0f, 1.0f);
    mu_ui_sprite_create_image(ctx->state, &s[MU_UI_WINEX_TOP], &info[1], 0, 0, 0, 0, 1.0f, 1.0f);
    mu_ui_sprite_create_image(ctx->state, &s[MU_UI_WINEX_BOTTOM], &info[2], 0, 0, 0, 0, 1.0f, 1.0f);
    mu_ui_sprite_create_image(ctx->state, &s[MU_UI_WINEX_LEFT], &info[3], 0, 0, 1, 0, 1.0f, 1.0f);
    mu_ui_sprite_create_image(ctx->state, &s[MU_UI_WINEX_RIGHT], &info[4], 0, 0, 1, 0, 1.0f, 1.0f);
    mu_ui_sprite_set_size(&s[MU_UI_WINEX_BACK], mu_ui_sprite_width(&s[MU_UI_WINEX_TOP]) - 6, 0, 1);
    win->win.y = 0;
    win->win.x = 0;
    win->win.temp_x = win->win.x;
    win->win.temp_y = win->win.y;
    win->win.held_x = win->win.temp_x;
    win->win.held_y = win->win.temp_y;
    win->win.show = 0;
    win->win.active = 0;
    win->win.docking = 0;
    win->win.state = MU_UI_WS_NORMAL;
    win->win.width = mu_ui_sprite_width(&s[MU_UI_WINEX_TOP]);
    win->win.height = mu_ui_sprite_height(&s[MU_UI_WINEX_TOP]) + mu_ui_sprite_height(&s[MU_UI_WINEX_BOTTOM]) +
                      mu_ui_sprite_height(&s[MU_UI_WINEX_LEFT]);
    win->line_min = line_min;
    win->lines = line_min;
    win->line_max = line_max;
}

int32_t mu_ui_winex_set_line(mu_ui_winex *win, int32_t lines)
{
    mu_ui_sprite *s = win->sprites;
    int32_t old, total;
    lines = lines < win->line_min ? win->line_min : (lines > win->line_max ? win->line_max : lines);
    if (win->lines == lines)
        return win->lines;
    old = win->lines;
    win->lines = lines;
    total = mu_ui_sprite_texture_height(&s[MU_UI_WINEX_LEFT]) * win->lines;
    mu_ui_sprite_set_size(&s[MU_UI_WINEX_LEFT], 0, total, 2);
    mu_ui_sprite_set_size(&s[MU_UI_WINEX_RIGHT], 0, total, 2);
    mu_ui_sprite_set_position(&s[MU_UI_WINEX_BOTTOM], 0,
                              mu_ui_sprite_y(&s[MU_UI_WINEX_LEFT]) + mu_ui_sprite_height(&s[MU_UI_WINEX_LEFT]), 2);
    win->win.height = mu_ui_sprite_height(&s[MU_UI_WINEX_BOTTOM]) +
                      (mu_ui_sprite_height(&s[MU_UI_WINEX_TOP]) + total);
    mu_ui_sprite_set_size(&s[MU_UI_WINEX_BACK], 0, win->win.height - 6, 2);
    return old;
}

void mu_ui_winex_set_position(mu_ui_ctx *ctx, mu_ui_win *base, int32_t x, int32_t y)
{
    mu_ui_winex *win = (mu_ui_winex *)base;
    mu_ui_sprite *s = win->sprites;
    (void)ctx;
    mu_ui_sprite_set_position(&s[MU_UI_WINEX_TOP], x, y, 3);
    mu_ui_sprite_set_position(&s[MU_UI_WINEX_BACK], x + 3, y + 3, 3);
    mu_ui_sprite_set_position(&s[MU_UI_WINEX_LEFT], x, mu_ui_sprite_height(&s[MU_UI_WINEX_TOP]) + y, 3);
    mu_ui_sprite_set_position(&s[MU_UI_WINEX_RIGHT],
                              mu_ui_sprite_width(&s[MU_UI_WINEX_TOP]) + x - mu_ui_sprite_width(&s[MU_UI_WINEX_RIGHT]),
                              mu_ui_sprite_y(&s[MU_UI_WINEX_LEFT]), 3);
    mu_ui_sprite_set_position(&s[MU_UI_WINEX_BOTTOM], x,
                              mu_ui_sprite_y(&s[MU_UI_WINEX_LEFT]) + mu_ui_sprite_height(&s[MU_UI_WINEX_LEFT]), 3);
    base->x = x;
    base->y = y;
}

int mu_ui_winex_cursor_in_win(mu_ui_ctx *ctx, mu_ui_win *win, int32_t area)
{
    if (!win->show)
        return 0;
    if (area == MU_UI_WA_RESIZE_BOTTOM) {
        if (in_rect(ctx, win->x, win->y + win->height - 5, win->x + win->width, win->y + win->height))
            return 1;
    } else if (area == MU_UI_WA_RESIZE_TOP) {
        if (in_rect(ctx, win->x, win->y, win->x + win->width, win->y + 4))
            return 1;
    }
    return mu_ui_win_cursor_in_win(ctx, win, area);
}

void mu_ui_winex_show(mu_ui_ctx *ctx, mu_ui_win *base, int show)
{
    mu_ui_winex *win = (mu_ui_winex *)base;
    int i;
    (void)ctx;
    for (i = 0; i < 5; ++i)
        mu_ui_sprite_show(&win->sprites[i], show);
    base->show = (uint8_t)show;
    if (!base->show)
        base->active = 0;
}

void mu_ui_winex_render(mu_ui_ctx *ctx, mu_ui_win *base)
{
    mu_ui_winex *win = (mu_ui_winex *)base;
    int i;
    if (!base->show)
        return;
    for (i = 0; i < 5; ++i)
        mu_ui_sprite_render(ctx->state, &win->sprites[i]);
    base->cls->render_controls(ctx, base);
}

void mu_ui_winex_check_additional_state(mu_ui_ctx *ctx, mu_ui_win *base)
{
    mu_ui_winex *win = (mu_ui_winex *)base;
    mu_ui_sprite *s = win->sprites;
    const mu_ui_input *in = &ctx->input;
    int32_t distance, line_height;
    if (in->lbutton_down) {
        if (base->cls->cursor_in_win(ctx, base, MU_UI_WA_RESIZE_TOP)) {
            win->resize_base = mu_ui_sprite_texture_height(&s[MU_UI_WINEX_LEFT]) * win->lines + base->y;
            base->state = MU_UI_WS_RESIZE_BOTTOM;
        }
        if (base->cls->cursor_in_win(ctx, base, MU_UI_WA_RESIZE_BOTTOM)) {
            win->resize_base = base->y + mu_ui_sprite_height(&s[MU_UI_WINEX_TOP]) +
                               mu_ui_sprite_height(&s[MU_UI_WINEX_BOTTOM]);
            base->state = MU_UI_WS_RESIZE_TOP;
        }
    }
    if (base->state == MU_UI_WS_RESIZE_TOP) {
        distance = in->cursor_y - win->resize_base;
        line_height = mu_ui_sprite_texture_height(&s[MU_UI_WINEX_LEFT]);
        if (distance < line_height * win->line_min)
            mu_ui_winex_set_line(win, win->line_min);
        else
            mu_ui_winex_set_line(win, distance / line_height + 1);
    } else if (base->state == MU_UI_WS_RESIZE_BOTTOM) {
        distance = win->resize_base - in->cursor_y;
        line_height = mu_ui_sprite_texture_height(&s[MU_UI_WINEX_LEFT]);
        if (distance < line_height * win->line_min)
            mu_ui_winex_set_line(win, win->line_min);
        else
            mu_ui_winex_set_line(win, distance / line_height + 1);
        base->cls->set_position(ctx, base, base->x,
                                win->resize_base - mu_ui_sprite_texture_height(&s[MU_UI_WINEX_LEFT]) * win->lines);
    }
}

/* ---- CutText ---------------------------------------------------------------- */

int32_t mu_ui_cut_text(const char *src, char *dst, int32_t lines, int32_t width)
{
    int32_t line = 0, length = 0;
    const char *line_start = src, *space = NULL, *p = src;
    char *out = dst;
    for (; *p; p += length, out += length) {
        length = 1;                                  /* _mbclen */
        if ((int32_t)(p - line_start) + length >= width) {
            if (space) {
                int32_t limit = width / 2 > 10 ? 10 : width / 2;
                if ((int32_t)(p - space) < limit) {
                    out -= (p - space) - 1;
                    p = space + 1;
                }
            }
            line_start = p;
            *out = 0;
            if (line >= lines - 1)
                break;
            ++line;
            out = dst + line * width;
            space = NULL;
        }
        memcpy(out, p, (size_t)length);
        if (*p == ' ')
            space = p;
    }
    *out = 0;
    return line + 1;
}
