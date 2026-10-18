/* Reconstructed credits window CCreditWin (NATIVE-UI-002).
 *
 * The login scene's CREDIT button is part of a GFx movie
 * (winLoginSceneBottomUI, handler 0x00c704ea "onCreditClick"); it shows
 * this legacy window, CUIMng+0x4648 (vtable 0x01a7f53c, constructor
 * 0x009d8de1, Create 0x009d8ea3).  It covers the screen in black and
 * cycles eight pairs of illustrations (Interface\im1_1.jpg .. im8_2.jpg,
 * loaded on demand as textures 0x7fa7/0x7fa8) with a logo and a corner
 * decoration, while the credit records (an input here; the client reads
 * them from its credit file into the table at 0x06fbac20) fade in under
 * three black bars: a title row, a subtitle row and up to four names.
 */
#ifndef MU_UI_CREDIT_H
#define MU_UI_CREDIT_H

#include "ui_widget.h"

#ifdef __cplusplus
extern "C" {
#endif

enum { MU_UI_CREDIT_END = 0, MU_UI_CREDIT_TITLE = 1, MU_UI_CREDIT_SUBTITLE = 2, MU_UI_CREDIT_NAME = 3 };

typedef struct mu_ui_credit_record {
    int32_t type;                     /* record +0 */
    const char *text;                 /* record +4 (std::string) */
} mu_ui_credit_record;

typedef struct mu_ui_credits {
    int32_t count;
    const mu_ui_credit_record *records;
} mu_ui_credits;

typedef struct mu_ui_credit_win {
    mu_ui_win win;
    mu_ui_sprite sprites[7];          /* +0x40: 0,1 illustrations; 2 decoration; 3 logo; 4..6 text bars */
    int32_t image_state;              /* +0x4d8: 0 idle, 1 fade in, 2 hold, 3 fade out */
    double image_timer;               /* +0x4e0 */
    uint8_t image;                    /* +0x4e8: illustration pair 0..7 */
    const char *paths[8][2];          /* +0x4ec */
    uint32_t font;                    /* +0x52c: bold CreateFontA handle */
    int32_t next;                     /* +0x530: next credit record */
    int32_t name_count;               /* +0x534 */
    int32_t rows[2];                  /* +0x538: title and subtitle records */
    int32_t names[4];                 /* +0x540 */
    int32_t text_states[3];           /* +0x550: per bar, 1 fade out (reveal), 2 shown, 3 fade in (hide) */
    double text_timer;                /* +0x560 */
    const mu_ui_credits *credits;     /* the table at 0x06fbac20 */
} mu_ui_credit_win;

extern const mu_ui_win_class mu_ui_credit_win_class;

void mu_ui_credit_win_init(mu_ui_credit_win *win, const mu_ui_credits *credits);   /* ctor 0x009d8de1 */
void mu_ui_credit_win_create(mu_ui_ctx *ctx, mu_ui_credit_win *win);               /* 0x009d8ea3 */
void mu_ui_credit_win_layout(mu_ui_ctx *ctx, mu_ui_credit_win *win);               /* 0x009d92ec */
void mu_ui_credit_win_show(mu_ui_ctx *ctx, mu_ui_win *win, int show);              /* 0x009d9432 */
int mu_ui_credit_win_cursor_in_win(mu_ui_ctx *ctx, mu_ui_win *win, int32_t area);  /* 0x009d94a9 */
void mu_ui_credit_win_update_while_active(mu_ui_ctx *ctx, mu_ui_win *win, double delta); /* 0x009d95e4 */
void mu_ui_credit_win_render_controls(mu_ui_ctx *ctx, mu_ui_win *win);             /* 0x009d9632 */

#ifdef __cplusplus
}
#endif
#endif
