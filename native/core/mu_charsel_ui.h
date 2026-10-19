#ifndef MU_CHARSEL_UI_H
#define MU_CHARSEL_UI_H

/* The character-select scene's legacy 2D window (NATIVE-CHARSEL-001):
 * CCharSelMainWin (reconstructed/ui/ui_charsel.c) created and placed as
 * CUIMng::CreateCharacterScene 0x011e2f2a does, fed from the session's
 * CHARACTER records, drawn by the deterministic 2D software GL over a
 * finished 3D frame (the client draws its 2D layer over the 3D framebuffer).
 *
 * Not drawn: the GFx character list, the GFx create/menu interfaces, the
 * server-message window (CUIMng +0x63a8) and the cursor. GlobalText (the
 * tip line 0x6ae/0x6cb/0x6cc, the warning lines 0x1b4/0x1b5) comes from the
 * tables read from the client (NATIVE-LANG-001, MU_LANG_DIR); without them
 * the tip line uses the string observed on the live screen. */

#include <stdint.h>

#include "../../reconstructed/ui/ui_charsel.h"
#include "mu_charsel.h"
#include "mu_ui_assets.h"
#include "mu_ui_font.h"
#include "mu_ui_raster.h"

typedef struct mu_charsel_ui {
    mu_ui_raster raster;
    mu_ui_assets assets;
    mu_ui_state state;
    mu_ui_text text;
    mu_ui_font_set fonts;
    mu_ui_ctx ctx;
    mu_ui_sink inner;
    mu_ui_charsel_input input;
    mu_ui_charsel_win win;
    int32_t textures, events[16][2], event_count, sounds;
} mu_charsel_ui;

/* Returns 0 on success. tip may be NULL (GlobalText, else the live string). */
int mu_charsel_ui_init(mu_charsel_ui *ui, const char *game_root, int32_t width, int32_t height, const char *font,
                       const mu_charsel_session *s, const char *tip);
void mu_charsel_ui_free(mu_charsel_ui *ui);
/* Refreshes the window's inputs from the records and selection, runs
 * UpdateDisplay, and one CWin::Update frame with the given cursor (window
 * pixels) and button edges. */
void mu_charsel_ui_update(mu_charsel_ui *ui, const mu_charsel_session *s, int32_t cursor_x, int32_t cursor_y,
                          uint8_t down, uint8_t up);
/* Draws the window over rgba (top-down RGBA8, width x height of init). */
void mu_charsel_ui_render(mu_charsel_ui *ui, uint8_t *rgba);

#endif
