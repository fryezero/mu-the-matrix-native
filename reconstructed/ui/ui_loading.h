#ifndef MU_UI_LOADING_H
#define MU_UI_LOADING_H

/* CLoadingScene (0x2a8 bytes, NATIVE-SHELL-001): the loading screen the
 * loading scene 0x01851adc draws between character select and the world.
 * Four CSprites (vector at +8, constructed by 0x00cdb6ca) on the textures
 * 0x7b81..0x7b84 (Interface\LSBg01_1..4.JPG): a 2x2 tiling of an 800x600
 * picture (400x512 over 400x88), scaled to the screen height and centred
 * horizontally. No progress gauge. */

#include "ui2d.h"

#ifdef __cplusplus
extern "C" {
#endif

enum { MU_UI_LOADING_SPRITES = 4 };
typedef struct mu_ui_loading {
    mu_ui_sprite sprites[MU_UI_LOADING_SPRITES];
} mu_ui_loading;

/* Create 0x00cdb74c; screen_width/height: CInput 0x009828b5 / 0x009828a6. */
void mu_ui_loading_create(mu_ui_state *state, mu_ui_loading *loading, int32_t screen_width, int32_t screen_height);
/* Render 0x00cdb94f (between the caller's BeginBitmap and EndBitmap). */
void mu_ui_loading_render(mu_ui_state *state, const mu_ui_loading *loading);

#ifdef __cplusplus
}
#endif
#endif
