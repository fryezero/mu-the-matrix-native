/* Reconstructed server-select window (NATIVE-UI-002).  See ui_server.h. */
#include "ui_server.h"

#include <string.h>

#define BITMAP_GROUP_BUTTON 0x7b0e    /* Interface\cha_bt.tga */
#define BITMAP_SERVER_BUTTON 0x7b0f   /* Interface\server_b2_all.tga */
#define BITMAP_SERVER_GAUGE 0x7b10    /* Interface\server_b2_loding.jpg */
#define BITMAP_SERVER_DECO 0x7b11     /* Interface\server_deco_all.tga */
#define BITMAP_NOTICE_CORNER 0x7b19   /* Interface\server_ex03.tga */
#define BITMAP_NOTICE_EDGE 0x7b1a     /* Interface\server_ex01.tga */
#define BITMAP_NOTICE_SIDE 0x7b1b     /* Interface\server_ex02.jpg */

static void release_controls(mu_ui_ctx *ctx, mu_ui_win *base);

const mu_ui_win_class mu_ui_server_win_class = {
    mu_ui_win_release,                       /* 0x0120ce41 */
    release_controls,                        /* 0x010763a6 */
    mu_ui_server_win_set_position,           /* 0x0107592f */
    mu_ui_server_win_cursor_in_win,          /* 0x010760d4 */
    mu_ui_win_show,                          /* 0x010760bd calls CWin::Show */
    mu_ui_win_render,                        /* 0x0120d26d */
    mu_ui_win_no_controls,                   /* 0x00982877 */
    mu_ui_win_nop_delta,                     /* 0x0098290f */
    mu_ui_win_nop,                           /* 0x0098286e */
    mu_ui_server_win_update_while_active,    /* 0x01076a24 */
    mu_ui_server_win_render_controls,        /* 0x01076c1e */
};

void mu_ui_server_win_init(mu_ui_server_win *win, mu_ui_server_list *list)
{
    memset(win, 0, sizeof *win);
    mu_ui_win_init(&win->win, &mu_ui_server_win_class);
    mu_ui_winex_init(&win->description);
    win->list = list;
}

static void release_controls(mu_ui_ctx *ctx, mu_ui_win *base)
{
    mu_ui_server_win *win = (mu_ui_server_win *)base;
    int i;
    for (i = 0; i < 2; ++i) {
        win->decos[i].has_frames = 0;        /* CSprite::Release 0x010ad814 */
        win->arrows[i].has_frames = 0;
    }
    win->description.win.cls->release(ctx, &win->description.win);
}

void mu_ui_server_win_create(mu_ui_ctx *ctx, mu_ui_server_win *win)
{
    static const mu_ui_image_info decos[2] = {{BITMAP_SERVER_DECO, 0, 0, 0x44, 0x5f},
                                              {BITMAP_SERVER_DECO, 0x44, 0, 0x44, 0x5f}};
    static const mu_ui_image_info arrows[2] = {{BITMAP_SERVER_DECO, 0x88, 0, 0x17, 0x1d},
                                               {BITMAP_SERVER_DECO, 0x88, 0x1e, 0x17, 0x1d}};
    static const mu_ui_image_info notice[5] = {{BITMAP_NOTICE_CORNER, 0, 0, 4, 4},
                                               {BITMAP_NOTICE_EDGE, 0, 0, 0x200, 6},
                                               {BITMAP_NOTICE_EDGE, 0, 6, 0x200, 6},
                                               {BITMAP_NOTICE_SIDE, 0, 0, 3, 4},
                                               {BITMAP_NOTICE_SIDE, 3, 0, 3, 4}};
    int i;
    mu_ui_win_create(ctx, &win->win, 0, 0, -2, 0);
    win->selected = -1;
    for (i = 0; i < MU_UI_SSW_GROUPS; ++i) {
        mu_ui_button_create(ctx, &win->groups[i], 0x6c, 0x1a, BITMAP_GROUP_BUTTON, 4, 2, 1, -1, 3, -1, -1, -1);
        mu_ui_win_register_button(&win->win, &win->groups[i]);
    }
    for (i = 0; i < MU_UI_SSW_SERVERS; ++i) {
        mu_ui_button_create(ctx, &win->servers[i], 0xc1, 0x1a, BITMAP_SERVER_BUTTON, 3, 2, 1, -1, -1, -1, -1, -1);
        mu_ui_win_register_button(&win->win, &win->servers[i]);
        mu_ui_gauge_create(ctx->state, &win->gauges[i], 0xa0, 4, BITMAP_SERVER_GAUGE, NULL, 1, 1.0f, 1.0f);
    }
    mu_ui_sprite_create_image(ctx->state, &win->decos[0], &decos[0], 8, 0x13, 0, 0, 1.0f, 1.0f);
    mu_ui_sprite_create_image(ctx->state, &win->decos[1], &decos[1], 0x3c, 0x13, 0, 0, 1.0f, 1.0f);
    mu_ui_sprite_create_image(ctx->state, &win->arrows[0], &arrows[0], 1, 2, 0, 0, 1.0f, 1.0f);
    mu_ui_sprite_create_image(ctx->state, &win->arrows[1], &arrows[1], 0x17, 2, 0, 0, 1.0f, 1.0f);
    mu_ui_winex_create(ctx, &win->description, notice, 1, 10);
    mu_ui_winex_set_line(&win->description, 10);
    mu_ui_win_set_size(&win->win, 0x1d1, win->description.win.height + 0x22c, 3);
}

void mu_ui_server_win_set_position(mu_ui_ctx *ctx, mu_ui_win *base, int32_t x, int32_t y)
{
    mu_ui_server_win *win = (mu_ui_server_win *)base;
    mu_ui_win *desc = &win->description.win;
    int32_t group_w, group_h, server_w, desc_h, side_y, right_x, top_x, top_y, i, k = 0;
    mu_ui_win_set_position(ctx, base, x, y);
    group_w = mu_ui_sprite_width(&win->groups[0].sprite);
    group_h = mu_ui_sprite_height(&win->groups[0].sprite);
    server_w = mu_ui_sprite_width(&win->servers[0].sprite);
    desc_h = desc->height;
    side_y = base->height + y - (group_h * 11 + desc_h + 10);
    right_x = x + group_w + server_w + 0x38;
    top_x = (base->width - group_w) / 2 + x;
    top_y = base->height + y - group_h - 5 - desc_h;
    for (i = 0; i < 5; ++i) {
        top_y -= group_h;
        mu_ui_sprite_set_position(&win->groups[k++].sprite, top_x, top_y, 3);
    }
    for (i = 0; i < 10; ++i)
        mu_ui_sprite_set_position(&win->groups[k++].sprite, x, group_h * i + side_y, 3);
    for (i = 0; i < 10; ++i)
        mu_ui_sprite_set_position(&win->groups[k++].sprite, right_x, group_h * i + side_y, 3);
    desc->cls->set_position(ctx, desc, x - (desc->width - base->width) / 2, base->height + y - desc->height);
    mu_ui_sprite_set_position(&win->decos[0], mu_ui_sprite_x(&win->groups[5].sprite),
                              mu_ui_sprite_y(&win->groups[5].sprite), 3);
    mu_ui_sprite_set_position(&win->decos[1], mu_ui_sprite_x(&win->groups[15].sprite) + 0x6c,
                              mu_ui_sprite_y(&win->groups[15].sprite), 3);
}

/* 0x01076683 */
static void show_group_buttons(mu_ui_server_win *win)
{
    int show = win->win.show, i = 0;
    for (; i < win->top_count; ++i)
        mu_ui_button_show(&win->groups[i], show);
    for (; i < 5; ++i)
        mu_ui_button_show(&win->groups[i], 0);
    for (i = 5; i < win->left_count + 5; ++i)
        mu_ui_button_show(&win->groups[i], show);
    for (; i < 15; ++i)
        mu_ui_button_show(&win->groups[i], 0);
    for (i = 15; i < win->right_count + 15; ++i)
        mu_ui_button_show(&win->groups[i], show);
    for (; i < 25; ++i)
        mu_ui_button_show(&win->groups[i], 0);
}

/* 0x010767b9 */
static void show_decos(mu_ui_server_win *win)
{
    mu_ui_sprite_show(&win->decos[0], win->left_count > 0 ? win->win.show : 0);
    mu_ui_sprite_show(&win->decos[1], win->right_count > 0 ? win->win.show : 0);
}

/* 0x01076598 */
static void place_arrows(mu_ui_server_win *win)
{
    const mu_ui_sprite *group;
    if (win->selected == -1)
        return;
    if (win->selected >= 0 && win->selected <= 10) {
        group = &win->groups[win->selected].sprite;
        mu_ui_sprite_set_position(&win->arrows[0], mu_ui_sprite_x(group) + 0x6c, mu_ui_sprite_y(group), 3);
    } else if (win->selected > 10 && win->selected < 25) {
        group = &win->groups[win->selected].sprite;
        mu_ui_sprite_set_position(&win->arrows[1], mu_ui_sprite_x(group), mu_ui_sprite_y(group), 3);
    }
}

/* 0x01076434 */
static void place_servers(mu_ui_server_win *win)
{
    int32_t x, server_h, column_h, list_h, y0, start_y, i;
    if (win->selected == -1)
        return;
    x = mu_ui_sprite_x(&win->groups[5].sprite) + mu_ui_sprite_width(&win->groups[0].sprite) + 0x1c;
    server_h = mu_ui_sprite_height(&win->servers[0].sprite);
    column_h = mu_ui_sprite_height(&win->groups[5].sprite) * 10;
    list_h = server_h * win->server_count;
    y0 = mu_ui_sprite_y(&win->groups[5].sprite);
    start_y = column_h > list_h ? y0 : y0 - (list_h - column_h);
    for (i = 0; i < win->group->server_count && i < MU_UI_SSW_SERVERS; ++i) {
        mu_ui_sprite_set_position(&win->servers[i].sprite, x, server_h * i + start_y, 3);
        mu_ui_gauge_set_position(&win->gauges[i], mu_ui_sprite_x(&win->servers[i].sprite) + 0x10,
                                 mu_ui_sprite_y(&win->servers[i].sprite) + 0x13);
    }
}

/* 0x01076852 */
static void show_arrows(mu_ui_server_win *win)
{
    int show = win->win.show;
    if (win->selected >= 0 && win->selected <= 10) {
        mu_ui_sprite_show(&win->arrows[0], show);
        mu_ui_sprite_show(&win->arrows[1], 0);
    } else if (win->selected > 10 && win->selected < 25) {
        mu_ui_sprite_show(&win->arrows[0], 0);
        mu_ui_sprite_show(&win->arrows[1], show);
    } else {
        mu_ui_sprite_show(&win->arrows[0], 0);
        mu_ui_sprite_show(&win->arrows[1], 0);
    }
}

/* 0x01076937 */
static void show_servers(mu_ui_ctx *ctx, mu_ui_server_win *win)
{
    mu_ui_win *desc = &win->description.win;
    int i;
    if (win->selected == -1) {
        desc->cls->show(ctx, desc, 0);
        return;
    }
    for (i = 0; i < win->server_count && i < MU_UI_SSW_SERVERS; ++i) {
        mu_ui_button_show(&win->servers[i], win->win.show);
        mu_ui_gauge_show(&win->gauges[i], win->win.show);
    }
    for (; i < MU_UI_SSW_SERVERS; ++i) {
        mu_ui_button_show(&win->servers[i], 0);
        mu_ui_gauge_show(&win->gauges[i], 0);
    }
    desc->cls->show(ctx, desc, win->win.show);
}

static mu_ui_server_group *group_by_button(mu_ui_server_list *list, int32_t button)
{
    int i;
    for (i = 0; list && i < list->group_count; ++i)
        if (list->groups[i].button == button)
            return &list->groups[i];
    return NULL;
}

void mu_ui_server_win_update_display(mu_ui_ctx *ctx, mu_ui_server_win *win)
{
    /* Text colours per button state; group buttons have check frames, so
     * SetText copies eight entries (the client keeps each set twice). */
    static const uint32_t group_colors[2][8] = {
        {0xffe2e2e2u, 0xffe2e2e2u, 0xffffffffu, 0, 0xffe2e2e2u, 0xffe2e2e2u, 0xffffffffu, 0},
        {0xff79ffffu, 0xff79ffffu, 0xffc1eeffu, 0, 0xff79ffffu, 0xff79ffffu, 0xffc1eeffu, 0}};
    static const uint32_t server_colors[4][4] = {{0xffe2e2e2u, 0xffe2e2e2u, 0xffffffffu, 0},
                                                 {0xff79ffffu, 0xff79ffffu, 0xffc1eeffu, 0},
                                                 {0xff00b4ffu, 0xff00b4ffu, 0xff27d9ffu, 0},
                                                 {0xff00b4ffu, 0xff00b4ffu, 0xff27d9ffu, 0}};
    mu_ui_server_list *list = win->list;
    mu_ui_win *desc = &win->description.win;
    int i;
    win->group = NULL;
    win->group_count = 0;
    win->server_count = 0;
    win->left_count = 0;
    win->right_count = 0;
    win->top_count = 0;
    win->flag_3adc = 0;
    win->group_count = list ? list->group_count : 0;              /* 0x01072928 */
    if (win->group_count < 1)
        return;
    for (i = 0; i < list->group_count; ++i) {                     /* SetFirst 0x01072838 / GetNext 0x01072859 */
        mu_ui_server_group *group = &list->groups[i];
        int32_t index;
        if (group->position == MU_UI_GROUP_TOP) {
            if (win->top_count >= 5)
                continue;
            index = win->top_count;
            mu_ui_button_set_text(&win->groups[index], group->name, group_colors[group->type == 2]);
            group->button = index;
            win->top_count++;
        } else if (group->position == MU_UI_GROUP_LEFT) {
            if (win->left_count >= 10)
                continue;
            index = win->left_count + 5;
            mu_ui_button_set_text(&win->groups[index], group->name, group_colors[group->type == 2]);
            group->button = index;
            win->left_count++;
        } else if (group->position == MU_UI_GROUP_RIGHT) {
            if (win->right_count >= 10)
                continue;
            index = win->right_count + 15;
            mu_ui_button_set_text(&win->groups[index], group->name, group_colors[group->type == 2]);
            group->button = index;
            win->right_count++;
        }
    }
    show_group_buttons(win);
    show_decos(win);
    memset(win->text, 0, sizeof win->text);
    if (win->selected != -1)
        win->group = group_by_button(list, win->selected);       /* 0x010728b9 */
    if (win->group == NULL) {
        if (strlen(list->notice)) {                               /* 0x01072821 */
            mu_ui_cut_text(list->notice, &win->text[0][0], 2, MU_UI_SSW_TEXT_LINE);
            desc->cls->show(ctx, desc, win->win.show);
        }
        return;
    }
    win->server_count = win->group->server_count;                 /* 0x010713e1 */
    if (win->server_count < 1)
        return;
    for (i = 0; i < win->group->server_count && i < MU_UI_SSW_SERVERS; ++i) {
        const mu_ui_server *server = &win->group->servers[i];
        /* The colour row is picked by server->type (the pinned capture has a
         * runtime patch at 0x01076018 here; see client-ui-widgets.md). */
        mu_ui_button_set_text(&win->servers[i], server->name, server_colors[server->type & 3]);
        mu_ui_gauge_set_value(&win->gauges[i], (uint32_t)server->percent, 100);
    }
    mu_ui_cut_text(win->group->description, &win->text[0][0], 2, MU_UI_SSW_TEXT_LINE);
    place_arrows(win);
    place_servers(win);
    show_arrows(win);
    show_servers(ctx, win);
}

int mu_ui_server_win_cursor_in_win(mu_ui_ctx *ctx, mu_ui_win *win, int32_t area)
{
    if (!win->show)
        return 0;
    if (area == MU_UI_WA_MOVE)
        return 0;
    return mu_ui_win_cursor_in_win(ctx, win, area);
}

void mu_ui_server_win_update_while_active(mu_ui_ctx *ctx, mu_ui_win *base, double delta)
{
    mu_ui_server_win *win = (mu_ui_server_win *)base;
    int32_t i, j;
    if (0.0 > delta)
        return;
    for (i = 0; i < MU_UI_SSW_GROUPS; ++i) {
        if (!win->groups[i].click)
            continue;
        if (win->selected != -1)
            win->groups[win->selected].check = 0;
        win->groups[i].check = 1;
        win->selected = i;
        mu_ui_ctx_event(ctx, MU_UI_EVENT_SERVER_GROUP, i);
    }
    if (win->group == NULL)
        return;
    for (i = 0; i < win->server_count; ++i) {
        const mu_ui_server *server = NULL;
        if (i >= MU_UI_SSW_SERVERS || !win->servers[i].click)
            continue;
        for (j = 0; j < win->group->server_count; ++j)        /* GetServer 0x010713f8 */
            if (win->group->servers[j].slot == i) {
                server = &win->group->servers[j];
                break;
            }
        if (server == NULL)
            return;
        if (server->percent < 0x80) {
            mu_ui_ctx_event(ctx, MU_UI_EVENT_HIDE_WINDOW, 0);
            mu_ui_ctx_event(ctx, MU_UI_EVENT_SERVER_CONNECT, i);
            return;
        }
    }
}

void mu_ui_server_win_render_controls(mu_ui_ctx *ctx, mu_ui_win *base)
{
    mu_ui_server_win *win = (mu_ui_server_win *)base;
    mu_ui_state *state = ctx->state;
    mu_ui_win *desc = &win->description.win;
    int i;
    desc->cls->render(ctx, desc);
    mu_ui_ctx_set_font(ctx, ctx->fonts.fixed);
    mu_ui_ctx_set_text_color(ctx, 0xffffffffu);
    mu_ui_ctx_set_back_color(ctx, 0);
    for (i = 0; i < 2; ++i) {
        if (win->group_count >= 3)
            mu_ui_sprite_render(state, &win->decos[i]);
        mu_ui_sprite_render(state, &win->arrows[i]);
        mu_ui_ctx_render_text(ctx, mu_ui_cvtt((float)(desc->x + 0xb) / state->screen_rate_x),
                              mu_ui_cvtt((float)(desc->y + 0xc + i * 0x14) / state->screen_rate_y), win->text[i],
                              0, 0, 1);
    }
    mu_ui_win_render_buttons(ctx, base);
    if (win->group == NULL)
        return;
    for (i = 0; i < win->server_count && i < MU_UI_SSW_SERVERS; ++i)
        mu_ui_gauge_render(state, &win->gauges[i]);
    mu_ui_ctx_set_text_color(ctx, 0xffffffffu);
    mu_ui_ctx_render_text(ctx, 0x5a, 0x68, mu_ui_ctx_global_text(ctx, 0x235), 0, 0, 1);
    mu_ui_ctx_render_text(ctx, 0x5a, 0x77, mu_ui_ctx_global_text(ctx, 0x236), 0, 0, 1);
    mu_ui_ctx_render_text(ctx, 0x5a, 0x86, mu_ui_ctx_global_text(ctx, 0x237), 0, 0, 1);
    if (win->group->id == 0x11 || win->group->id == 0x27) {
        mu_ui_ctx_set_text_color(ctx, 0xffffffffu);
        mu_ui_ctx_render_text(ctx, 0x1a4, 0x9f, mu_ui_ctx_global_text(ctx, 0x10f3), 0, 0, 1);
        mu_ui_ctx_render_text(ctx, 0x1a4, 0xae, mu_ui_ctx_global_text(ctx, 0x10f4), 0, 0, 1);
    } else if (win->group->type == 2) {
        mu_ui_ctx_set_text_color(ctx, 0xffffffffu);
        mu_ui_ctx_render_text(ctx, 0x1a4, 0x9f, mu_ui_ctx_global_text(ctx, 0x1225), 0, 0, 1);
        mu_ui_ctx_render_text(ctx, 0x1a4, 0xae, mu_ui_ctx_global_text(ctx, 0x1226), 0, 0, 1);
    }
}

void mu_ui_server_win_place(mu_ui_ctx *ctx, mu_ui_server_win *win)
{
    win->win.cls->set_position(ctx, &win->win, (ctx->input.screen_width - win->win.width) / 2,
                               (ctx->input.screen_height - win->win.height) / 2);
}

void mu_ui_server_win_open(mu_ui_ctx *ctx, mu_ui_server_win *win)
{
    win->win.cls->show(ctx, &win->win, 1);
    mu_ui_win_set_active(&win->win, 1);     /* CUIMng::SetTop activates the top window on the next update */
    mu_ui_server_win_update_display(ctx, win);
}
