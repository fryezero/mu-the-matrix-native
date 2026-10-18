/* Reconstructed credits window (NATIVE-UI-002).  See ui_credit.h. */
#include "ui_credit.h"

#include <string.h>

#define BITMAP_CREDIT_DECO 0x7b14     /* Interface\deco.tga */
#define BITMAP_CREDIT_LOGO 0x7b1c     /* Interface\cr_mu_lo.tga */
#define BITMAP_CREDIT_IMAGE 0x7fa7    /* + 0, 1: the illustration pair */

static const char *const CREDIT_IMAGES[8][2] = {
    {"Interface\\im1_1.jpg", "Interface\\im1_2.jpg"}, {"Interface\\im2_1.jpg", "Interface\\im2_2.jpg"},
    {"Interface\\im3_1.jpg", "Interface\\im3_2.jpg"}, {"Interface\\im4_1.jpg", "Interface\\im4_2.jpg"},
    {"Interface\\im5_1.jpg", "Interface\\im5_2.jpg"}, {"Interface\\im6_1.jpg", "Interface\\im6_2.jpg"},
    {"Interface\\im7_1.jpg", "Interface\\im7_2.jpg"}, {"Interface\\im8_1.jpg", "Interface\\im8_2.jpg"}};

static void emit(mu_ui_state *state, int op, const uint32_t *words, int count, const void *data, size_t bytes)
{
    if (state->sink.call)
        state->sink.call(state->sink.user, op, words, count, data, bytes);
}

static void release_controls(mu_ui_ctx *ctx, mu_ui_win *base);

const mu_ui_win_class mu_ui_credit_win_class = {
    mu_ui_win_release,                       /* 0x0120ce41 */
    release_controls,                        /* 0x009d958c */
    mu_ui_win_set_position,                  /* 0x0120ceb4 */
    mu_ui_credit_win_cursor_in_win,          /* 0x009d94a9 */
    mu_ui_credit_win_show,                   /* 0x009d9432 */
    mu_ui_win_render,                        /* 0x0120d26d */
    mu_ui_win_no_controls,                   /* 0x00982877 */
    mu_ui_win_nop_delta,                     /* 0x0098290f */
    mu_ui_win_nop,                           /* 0x0098286e */
    mu_ui_credit_win_update_while_active,    /* 0x009d95e4 */
    mu_ui_credit_win_render_controls,        /* 0x009d9632 */
};

/* cvttsd2si */
static int32_t cvtt_d(double value)
{
    if (!(value > -2147483649.0 && value < 2147483648.0))
        return INT32_MIN;
    return (int32_t)value;
}

/* alpha +/- (short)(int)(255 * delta / period), in 16-bit arithmetic */
static int16_t fade(uint8_t alpha, double delta, double period, int sign)
{
    int16_t step = (int16_t)cvtt_d(255.0 * delta / period);
    return (int16_t)(sign > 0 ? (int16_t)alpha + step : (int16_t)alpha - step);
}

static mu_ui_credit_record record(const mu_ui_credit_win *win, int32_t index)
{
    mu_ui_credit_record none = {MU_UI_CREDIT_END, ""};     /* out of range: the table's fallback record */
    if (win->credits && index >= 0 && index < win->credits->count)
        return win->credits->records[index];
    return none;
}

void mu_ui_credit_win_init(mu_ui_credit_win *win, const mu_ui_credits *credits)
{
    memset(win, 0, sizeof *win);
    mu_ui_win_init(&win->win, &mu_ui_credit_win_class);
    win->credits = credits;
}

static void release_controls(mu_ui_ctx *ctx, mu_ui_win *base)
{
    mu_ui_credit_win *win = (mu_ui_credit_win *)base;
    int i;
    for (i = 0; i < 7; ++i)
        win->sprites[i].has_frames = 0;                   /* CSprite::Release */
    if (win->font) {
        emit(ctx->state, MU_GDI_DELETEOBJECT, &win->font, 1, NULL, 0);
        win->font = 0;
    }
}

void mu_ui_credit_win_create(mu_ui_ctx *ctx, mu_ui_credit_win *win)
{
    int32_t width = ctx->input.screen_width, height = ctx->input.screen_height, font_height = 10, i;
    float sx, sy;
    const char *face;
    mu_ui_win_create(ctx, &win->win, width, height, -1, 0);
    win->win.background->alpha = 0xff;                   /* 0x009828ea */
    sx = (float)width / 800.0f;
    sy = (float)height / 600.0f;
    mu_ui_sprite_create_frames(ctx->state, &win->sprites[2], 0xbd, 0x67, BITMAP_CREDIT_DECO, 0, NULL, 0, 0, 0, 0,
                               1.0f, 1.0f);
    mu_ui_sprite_create_frames(ctx->state, &win->sprites[3], 0x122, 0x29, BITMAP_CREDIT_LOGO, 0, NULL, 0, 0, 0, 0,
                               sx, sy);
    for (i = 4; i <= 6; ++i) {
        mu_ui_sprite_create_frames(ctx->state, &win->sprites[i], 0x320, 0x2a, -1, 0, NULL, 0, 0, 0, 0, sx, sy);
        win->sprites[i].red = win->sprites[i].green = win->sprites[i].blue = 0;   /* 0x009a47be */
    }
    win->image_state = 0;
    for (i = 0; i < 8; ++i) {
        win->paths[i][0] = CREDIT_IMAGES[i][0];
        win->paths[i][1] = CREDIT_IMAGES[i][1];
    }
    switch (width) {
    case 0x320: font_height = 0xe; break;
    case 0x400: font_height = 0x12; break;
    case 0x500: font_height = 0x18; break;
    default: break;
    }
    face = mu_ui_ctx_global_text(ctx, 0);
    if (!face[0])
        face = NULL;
    {
        uint32_t words[13] = {(uint32_t)font_height, 0, 0, 0, 0x2bc, 0, 0, 0, ctx->charset, 0, 0, 3, 0};
        emit(ctx->state, MU_GDI_CREATEFONT, words, 13, face, face ? strlen(face) : 0);
        win->font = ctx->platform.create_font
                    ? ctx->platform.create_font(ctx->platform.user, font_height, 0x2bc, ctx->charset, 3, face) : 0;
    }
    mu_ui_credit_win_layout(ctx, win);
}

void mu_ui_credit_win_layout(mu_ui_ctx *ctx, mu_ui_credit_win *win)
{
    static const uint32_t factor_bits = 0x3f60da74u;     /* 0.8783333f at 0x01a7f574 */
    float factor;
    int32_t y, i;
    memcpy(&factor, &factor_bits, 4);
    mu_ui_sprite_set_position(&win->sprites[0], 0, 0x7e, 3);
    mu_ui_sprite_set_position(&win->sprites[1], 0x190, 0x7e, 3);
    mu_ui_sprite_set_position(&win->sprites[3], 0xf1, 0x21c, 3);
    y = mu_ui_cvtt((float)ctx->input.screen_height * factor);
    mu_ui_sprite_set_position(&win->sprites[2], ctx->input.screen_width - mu_ui_sprite_width(&win->sprites[2]),
                              y - mu_ui_sprite_height(&win->sprites[2]), 3);
    for (i = 4; i <= 6; ++i)
        mu_ui_sprite_set_position(&win->sprites[i], 0, (i - 4) * 0x2a, 3);
}

/* 0x009d9b3b */
static void load_images(mu_ui_ctx *ctx, mu_ui_credit_win *win)
{
    float sx = (float)ctx->input.screen_width / 800.0f, sy = (float)ctx->input.screen_height / 600.0f;
    int i;
    for (i = 0; i < 2; ++i) {
        const char *path = win->paths[win->image][i];
        uint32_t words[5] = {BITMAP_CREDIT_IMAGE + (uint32_t)i, 0x2601, 0x2900, 1, 0};
        emit(ctx->state, MU_UI_LOADBITMAP, words, 5, path, strlen(path));
        if (ctx->platform.load_bitmap)
            ctx->platform.load_bitmap(ctx->platform.user, path, words[0], 0x2601, 0x2900);
        mu_ui_sprite_create_frames(ctx->state, &win->sprites[i], 0x190, 0x190, (int32_t)words[0], 0, NULL, 0, 0, 0,
                                   0, sx, sy);
        win->sprites[i].alpha = 0;
        mu_ui_sprite_show(&win->sprites[i], 1);
    }
    mu_ui_sprite_set_position(&win->sprites[0], 0, 0x7e, 3);
    mu_ui_sprite_set_position(&win->sprites[1], 0x190, 0x7e, 3);
}

/* 0x009d94e1: the end record closes the window and returns to the server list */
static void finish(mu_ui_ctx *ctx, mu_ui_credit_win *win)
{
    (void)win;
    mu_ui_ctx_event(ctx, MU_UI_EVENT_HIDE_WINDOW, 0);
    mu_ui_ctx_event(ctx, MU_UI_EVENT_CREDITS_DONE, 0);
    mu_ui_ctx_event(ctx, MU_UI_EVENT_MUSIC_STOP, 1);
    mu_ui_ctx_event(ctx, MU_UI_EVENT_MUSIC_PLAY, 0x15);
}

/* 0x009d9eb2 */
static void next_credits(mu_ui_ctx *ctx, mu_ui_credit_win *win)
{
    int32_t type = record(win, win->next).type, k;
    if (type == MU_UI_CREDIT_END) {
        uint32_t sound = 0x19;
        emit(ctx->state, MU_UI_SOUND, &sound, 1, NULL, 0);
        finish(ctx, win);
    } else if (type == MU_UI_CREDIT_TITLE) {
        win->rows[0] = win->next++;
    } else if (type == MU_UI_CREDIT_SUBTITLE) {
        win->rows[1] = win->next++;
    }
    for (k = 0; k < 4; ++k) {
        if (record(win, win->next).type != MU_UI_CREDIT_NAME)
            break;
        win->names[k] = win->next++;
    }
    win->name_count = k;
}

/* 0x009d9ab2 */
static void start(mu_ui_ctx *ctx, mu_ui_credit_win *win)
{
    int i;
    win->image_state = 1;
    win->image_timer = 0.0;
    win->image = 0;
    load_images(ctx, win);
    for (i = 0; i < 3; ++i)
        win->text_states[i] = 1;
    win->text_timer = 0.0;
    win->next = 0;
    win->name_count = 0;
    next_credits(ctx, win);
}

void mu_ui_credit_win_show(mu_ui_ctx *ctx, mu_ui_win *base, int show)
{
    mu_ui_credit_win *win = (mu_ui_credit_win *)base;
    int i;
    mu_ui_win_show(ctx, base, show);
    for (i = 0; i < 7; ++i)
        mu_ui_sprite_show(&win->sprites[i], show);
    mu_ui_sprite_show(&win->sprites[2], 0);
    if ((uint8_t)show)
        start(ctx, win);
    else
        win->image_state = 0;
}

int mu_ui_credit_win_cursor_in_win(mu_ui_ctx *ctx, mu_ui_win *win, int32_t area)
{
    if (!win->show)
        return 0;
    if (area == MU_UI_WA_MOVE)
        return 0;
    return mu_ui_win_cursor_in_win(ctx, win, area);
}

/* 0x009d9fc2: the black bar over text row `row` */
static void text_fade(mu_ui_ctx *ctx, mu_ui_credit_win *win, int row, double delta)
{
    int32_t *state = &win->text_states[row];
    mu_ui_sprite *bar = &win->sprites[row + 4];
    int16_t alpha;
    switch (*state) {
    case 1:
        alpha = fade(bar->alpha, delta, 300.0, -1);
        if (alpha <= 0) {
            *state = 2;
            alpha = 0;
        }
        bar->alpha = (uint8_t)alpha;
        break;
    case 2:
        if (row != 2)
            break;
        win->text_timer = win->text_timer + delta;
        if (win->text_timer > 2300.0) {
            win->text_states[2] = 3;
            win->text_timer = 0.0;
            if (record(win, win->next).type != MU_UI_CREDIT_NAME) {
                win->text_states[1] = 3;
                if (record(win, win->next).type != MU_UI_CREDIT_SUBTITLE)
                    win->text_states[0] = 3;
            }
        }
        break;
    case 3:
        alpha = fade(bar->alpha, delta, 300.0, 1);
        if (alpha >= 0xff) {
            *state = 1;
            alpha = 0xff;
            if (row == 2)
                next_credits(ctx, win);
        }
        bar->alpha = (uint8_t)alpha;
        break;
    default:
        break;
    }
}

/* 0x009d9cc0: the illustration pair */
static void image_fade(mu_ui_ctx *ctx, mu_ui_credit_win *win, double delta)
{
    int16_t alpha;
    switch (win->image_state) {
    case 1:
        alpha = fade(win->sprites[0].alpha, delta, 2000.0, 1);
        if (alpha >= 0xff) {
            win->image_state = 2;
            alpha = 0xff;
        }
        win->sprites[0].alpha = (uint8_t)alpha;
        win->sprites[1].alpha = (uint8_t)alpha;
        break;
    case 2:
        win->image_timer = win->image_timer + delta;
        if (win->image_timer > 22000.0) {
            win->image_state = 3;
            win->image_timer = 0.0;
        }
        break;
    case 3:
        alpha = fade(win->sprites[0].alpha, delta, 2000.0, -1);
        if (alpha <= 0) {
            uint8_t next = (uint8_t)(win->image + 1);
            win->image_state = 1;
            alpha = 0;
            win->image = next;
            win->image = next == 8 ? 0 : win->image;
            load_images(ctx, win);
        }
        win->sprites[0].alpha = (uint8_t)alpha;
        win->sprites[1].alpha = (uint8_t)alpha;
        break;
    default:
        break;
    }
}

void mu_ui_credit_win_update_while_active(mu_ui_ctx *ctx, mu_ui_win *base, double delta)
{
    mu_ui_credit_win *win = (mu_ui_credit_win *)base;
    int row;
    for (row = 0; row <= 2; ++row)
        text_fade(ctx, win, row, delta);
    image_fade(ctx, win, delta);
}

void mu_ui_credit_win_render_controls(mu_ui_ctx *ctx, mu_ui_win *base)
{
    mu_ui_credit_win *win = (mu_ui_credit_win *)base;
    mu_ui_state *state = ctx->state;
    uint32_t cap = 0x0bc0;                                /* GL_ALPHA_TEST, raw (the cache is not updated) */
    int32_t width = ctx->input.screen_width, box;
    int i;
    emit(state, MU_GL_DISABLE, &cap, 1, NULL, 0);
    for (i = 0; i <= 3; ++i)
        mu_ui_sprite_render(state, &win->sprites[i]);
    mu_ui_ctx_set_font(ctx, win->font);
    mu_ui_ctx_set_text_color(ctx, 0xffe2e2e2u);
    mu_ui_ctx_set_back_color(ctx, 0);
    box = mu_ui_cvtt((float)width / state->screen_rate_x);
    mu_ui_ctx_render_text(ctx, 0, 0x14, record(win, win->rows[0]).text, box, 0, 3);
    mu_ui_ctx_render_text(ctx, 0, 0x2e, record(win, win->rows[1]).text, box, 0, 3);
    mu_ui_ctx_set_text_color(ctx, 0xffc1eeffu);
    switch (win->name_count) {
    case 1:
        mu_ui_ctx_render_text(ctx, 0, 0x48, record(win, win->names[0]).text, box, 0, 3);
        break;
    case 2:
        box = mu_ui_cvtt((float)(width / 4) / state->screen_rate_x);
        mu_ui_ctx_render_text(ctx, 0xa0, 0x48, record(win, win->names[0]).text, box, 0, 3);
        mu_ui_ctx_render_text(ctx, 0x140, 0x48, record(win, win->names[1]).text, box, 0, 3);
        break;
    case 3:
        box = mu_ui_cvtt((float)(width / 3) / state->screen_rate_x);
        mu_ui_ctx_render_text(ctx, 0, 0x48, record(win, win->names[0]).text, box, 0, 3);
        mu_ui_ctx_render_text(ctx, 0xd5, 0x48, record(win, win->names[1]).text, box, 0, 3);
        mu_ui_ctx_render_text(ctx, 0x1aa, 0x48, record(win, win->names[2]).text, box, 0, 3);
        break;
    case 4:
        box = mu_ui_cvtt((float)(width / 4) / state->screen_rate_x);
        mu_ui_ctx_render_text(ctx, 0, 0x48, record(win, win->names[0]).text, box, 0, 3);
        mu_ui_ctx_render_text(ctx, 0xa0, 0x48, record(win, win->names[1]).text, box, 0, 3);
        mu_ui_ctx_render_text(ctx, 0x140, 0x48, record(win, win->names[2]).text, box, 0, 3);
        mu_ui_ctx_render_text(ctx, 0x1e0, 0x48, record(win, win->names[3]).text, box, 0, 3);
        break;
    default:
        break;
    }
    for (i = 4; i <= 6; ++i)
        mu_ui_sprite_render(state, &win->sprites[i]);
    emit(state, MU_GL_ENABLE, &cap, 1, NULL, 0);
    mu_ui_win_render_buttons(ctx, base);
}
