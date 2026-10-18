/* Reconstructed server-select window CServerSelWin (NATIVE-UI-002).
 *
 * The window lives at CUIMng+0xab0 and is created by CreateLoginScene
 * 0x011e2dc0 through Create 0x01075554 (vtable 0x01ab7398, 0x3b98 bytes):
 *
 *   25 group buttons (Interface\cha_bt.tga, 0x7b0e): 5 on top, 10 left, 10 right
 *   20 server buttons (Interface\server_b2_all.tga, 0x7b0f), each with a load
 *      gauge (Interface\server_b2_loding.jpg, 0x7b10)
 *   2 column decorations and 2 selection arrows (Interface\server_deco_all.tga)
 *   a CWinEx notice box of 10 lines (server_ex01/02/03) showing two text rows
 *
 * The server list itself belongs to CServerListManager (0x01072152).  It is
 * an input here: mu_ui_server_list mirrors the fields the window reads,
 * in the manager's iteration order.  Nothing in this module talks to the
 * network; choosing a group or a server emits MU_UI_EVENT.
 */
#ifndef MU_UI_SERVER_H
#define MU_UI_SERVER_H

#include "ui_widget.h"

#ifdef __cplusplus
extern "C" {
#endif

enum { MU_UI_SERVER_NAME_MAX = 64, MU_UI_GROUP_TEXT_MAX = 256, MU_UI_GROUP_SERVERS_MAX = 20,
       MU_UI_SERVER_GROUPS_MAX = 64 };

typedef struct mu_ui_server {
    int32_t slot;                     /* +0x04: index inside the group (GetServer 0x010713f8 matches it) */
    int32_t percent;                  /* +0x10: load 0..100; 0x80 or more means not selectable */
    uint8_t type;                     /* +0x14: name colour set 0..3 */
    char name[MU_UI_SERVER_NAME_MAX]; /* +0x15 */
} mu_ui_server;

enum { MU_UI_GROUP_LEFT = 0, MU_UI_GROUP_RIGHT = 1, MU_UI_GROUP_TOP = 2 };

typedef struct mu_ui_server_group {
    int32_t id;                       /* +0x04 (0x11 and 0x27 select extra notice texts) */
    uint8_t type;                     /* +0x08: 2 draws the name in the second colour set */
    int32_t position;                 /* +0x0c: MU_UI_GROUP_* */
    int32_t button;                   /* +0x10: written by UpdateDisplay */
    char name[MU_UI_SERVER_NAME_MAX]; /* +0x30 */
    char description[MU_UI_GROUP_TEXT_MAX];  /* +0x12f */
    int server_count;
    mu_ui_server servers[MU_UI_GROUP_SERVERS_MAX];
} mu_ui_server_group;

typedef struct mu_ui_server_list {
    int group_count;
    mu_ui_server_group groups[MU_UI_SERVER_GROUPS_MAX];   /* manager (std::map) order */
    char notice[MU_UI_GROUP_TEXT_MAX];                   /* +0x134 */
} mu_ui_server_list;

enum { MU_UI_SSW_GROUPS = 25, MU_UI_SSW_SERVERS = 20, MU_UI_SSW_TEXT_LINE = 0x53 };

typedef struct mu_ui_server_win {
    mu_ui_win win;
    mu_ui_button groups[MU_UI_SSW_GROUPS];      /* +0x40 */
    mu_ui_button servers[MU_UI_SSW_SERVERS];    /* +0x1620 */
    mu_ui_gauge gauges[MU_UI_SSW_SERVERS];      /* +0x27a0 */
    mu_ui_sprite decos[2];                      /* +0x37e0 */
    mu_ui_sprite arrows[2];                     /* +0x3930 */
    mu_ui_winex description;                    /* +0x3a80 */
    int32_t group_count;                        /* +0x3acc */
    int32_t left_count;                         /* +0x3ad0 */
    int32_t right_count;                        /* +0x3ad4 */
    int32_t server_count;                       /* +0x3ad8 */
    uint8_t flag_3adc;                          /* +0x3adc (cleared, never read here) */
    int32_t top_count;                          /* +0x3ae0 */
    int32_t selected;                           /* +0x3ae4: selected group button, -1 none */
    mu_ui_server_group *group;                  /* +0x3ae8: selected group */
    char text[2][MU_UI_SSW_TEXT_LINE];          /* +0x3aec: notice box rows */
    mu_ui_server_list *list;                    /* CServerListManager::Instance() */
} mu_ui_server_win;

extern const mu_ui_win_class mu_ui_server_win_class;

void mu_ui_server_win_init(mu_ui_server_win *win, mu_ui_server_list *list);        /* ctor 0x01075387 */
void mu_ui_server_win_create(mu_ui_ctx *ctx, mu_ui_server_win *win);               /* 0x01075554 */
void mu_ui_server_win_set_position(mu_ui_ctx *ctx, mu_ui_win *win, int32_t x, int32_t y); /* 0x0107592f */
void mu_ui_server_win_update_display(mu_ui_ctx *ctx, mu_ui_server_win *win);       /* 0x01075bc2 */
int mu_ui_server_win_cursor_in_win(mu_ui_ctx *ctx, mu_ui_win *win, int32_t area);  /* 0x010760d4 */
void mu_ui_server_win_update_while_active(mu_ui_ctx *ctx, mu_ui_win *win, double delta); /* 0x01076a24 */
void mu_ui_server_win_render_controls(mu_ui_ctx *ctx, mu_ui_win *win);             /* 0x01076c1e */

/* CreateLoginScene's placement: centred on the CInput screen size. */
void mu_ui_server_win_place(mu_ui_ctx *ctx, mu_ui_server_win *win);
/* CUIMng::ShowWin 0x011e34ec as the server-list handler calls it, then
 * UpdateDisplay (what the client does when a server list arrives). */
void mu_ui_server_win_open(mu_ui_ctx *ctx, mu_ui_server_win *win);

#ifdef __cplusplus
}
#endif
#endif
