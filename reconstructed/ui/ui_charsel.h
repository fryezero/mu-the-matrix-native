/* Reconstructed character-select window CCharSelMainWin (NATIVE-CHARSEL-001).
 *
 * The window lives at CUIMng+0x4bb0 and is created by
 * CUIMng::CreateCharacterScene 0x011e2f2a through Create 0x009a492e
 * (vtable 0x01a7ec20, 0x518 bytes):
 *
 *   sprite 0: Interface\deco.tga (0x7b10), 189 x 103
 *   sprite 1: an untextured black bar (alpha 0x8f), screen width - 0x10a wide,
 *             21 high, carrying a tip line (GlobalText 0x6ae, 0x6cb or 0x6cc)
 *   buttons:  0 create (b_create.tga 0x7b11), 1 menu (server_menu_b_all.tga
 *             0x7b12), 2 connect (b_connect.tga 0x7b13), 3 delete
 *             (b_delete.tga 0x7b14), 54 x 30 each
 *
 * The character list and the other subsystems the window asks are inputs
 * (mu_ui_charsel_input). What the buttons start (the GFx create-character
 * and menu interfaces, the delete confirmation, entering the game) is
 * emitted as MU_UI_EVENT_CHARSEL_*.
 */
#ifndef MU_UI_CHARSEL_H
#define MU_UI_CHARSEL_H

#include "ui_widget.h"

#ifdef __cplusplus
extern "C" {
#endif

enum { MU_UI_CHARSEL_SLOTS = 16 };

/* The CHARACTER fields the window reads, for CharactersClient[0..15]. */
typedef struct mu_ui_charsel_slot {
    uint8_t live;            /* OBJECT +0 (CHARACTER +0x3254) */
    uint8_t flags;           /* CHARACTER +0x14 (0x10: warning lines; 0x12: delete refused) */
    uint8_t byte_17;         /* CHARACTER +0x17 (not 0xff: delete refused) */
    uint16_t level;          /* CHARACTER +0x144 */
    uint8_t byte_3634;       /* CHARACTER +0x3634 (1: delete refused) */
    char name[32];           /* CHARACTER +0x3658 */
} mu_ui_charsel_slot;

typedef struct mu_ui_charsel_input {
    mu_ui_charsel_slot slots[MU_UI_CHARSEL_SLOTS];
    int32_t selected;        /* SelectedHero 0x01cf1864 */
    uint8_t flag_95f75d;     /* 0x0095f75d()->+4 (0x0095fb99) */
    int32_t slot_mode;       /* 0x0185bdbd() */
    int32_t slot_count;      /* 0x010a5cf2()->0x010a5dca(), used when slot_mode != 0 */
    uint8_t gfx_create_open; /* GFx manager +0x22c -> 0x009a59f6() */
    uint8_t gfx_movie_busy;  /* GFx manager +0x90 -> 0x00aae6f9() */
    uint8_t gfx_blocked;     /* GFx manager +0x22c -> 0x009a5a06() */
    uint8_t enter_refused;   /* CCharSelMainWin 0x009a5029(SelectedHero), not reconstructed */
    uint8_t server_flag;     /* 0x01072152()->0x01072a96() */
    int32_t random;          /* rand() 0x01989721 at Create (the tip line) */
} mu_ui_charsel_input;

typedef struct mu_ui_charsel_win {
    mu_ui_win win;
    mu_ui_sprite sprites[2];          /* +0x40 */
    mu_ui_button buttons[4];          /* +0x190 */
    uint8_t warning;                  /* +0x510 */
    int16_t tip;                      /* +0x512: GlobalText index */
    mu_ui_charsel_input *input;
} mu_ui_charsel_win;

/* Events (MU_UI_EVENT words: code, argument). */
enum {
    MU_UI_EVENT_CHARSEL_CREATE = 0x20,   /* GFx create-character interface: 0x00b49bf4(1) on +0x22c, 0x009a5920(0),
                                            0x00b4b684() */
    MU_UI_EVENT_CHARSEL_MENU = 0x21,     /* GFx menu: 0x009a5792 handle -> 0x00c8c8b1 */
    MU_UI_EVENT_CHARSEL_CONNECT = 0x22,  /* 0x0185a75a(0): the loading scene (enter the game) */
    MU_UI_EVENT_CHARSEL_MESSAGE = 0x23,  /* delete refused: GFx message box with GlobalText (argument) */
    MU_UI_EVENT_CHARSEL_NOTICE = 0x24,   /* delete refused by level: CUIMng 0x011e3598(0x83, 0) */
    MU_UI_EVENT_CHARSEL_CONFIRM = 0x25   /* delete confirmation (GlobalText 0x6b0 with the name) for SelectedHero */
};

extern const mu_ui_win_class mu_ui_charsel_win_class;

void mu_ui_charsel_win_init(mu_ui_charsel_win *win, mu_ui_charsel_input *input);      /* ctor 0x009a4838 */
void mu_ui_charsel_win_create(mu_ui_ctx *ctx, mu_ui_charsel_win *win);               /* 0x009a492e */
void mu_ui_charsel_win_set_position(mu_ui_ctx *ctx, mu_ui_win *win, int32_t x, int32_t y); /* 0x009a4be1 */
int mu_ui_charsel_win_cursor_in_win(mu_ui_ctx *ctx, mu_ui_win *win, int32_t area);  /* 0x009a4d9f */
void mu_ui_charsel_win_show(mu_ui_ctx *ctx, mu_ui_win *win, int show);              /* 0x009a4d2c */
void mu_ui_charsel_win_update_display(mu_ui_ctx *ctx, mu_ui_charsel_win *win);      /* 0x009a4dd7 */
void mu_ui_charsel_win_update_while_active(mu_ui_ctx *ctx, mu_ui_win *win, double delta); /* 0x009a5197 */
void mu_ui_charsel_win_render_controls(mu_ui_ctx *ctx, mu_ui_win *win);            /* 0x009a533d */
void mu_ui_charsel_win_delete(mu_ui_ctx *ctx, mu_ui_charsel_win *win);             /* 0x009a553c */

/* CreateCharacterScene's placement: (0x16, screen height - window height - 0xe). */
void mu_ui_charsel_win_place(mu_ui_ctx *ctx, mu_ui_charsel_win *win);

#ifdef __cplusplus
}
#endif
#endif
