/* CLoadingScene 0x00cdb6ca / 0x00cdb74c / 0x00cdb94f (NATIVE-SHELL-001). */
#include "ui_loading.h"

static int32_t cvtt(float value)
{
    return (int32_t)value;   /* cvttss2si */
}

void mu_ui_loading_create(mu_ui_state *state, mu_ui_loading *loading, int32_t screen_width, int32_t screen_height)
{
    static const int32_t heights[MU_UI_LOADING_SPRITES] = {0x200, 0x200, 0x58, 0x58};
    float scale = (float)screen_height / 600.0f;
    for (int32_t i = 0; i < MU_UI_LOADING_SPRITES; ++i) {
        mu_ui_sprite_init(&loading->sprites[i]);
        mu_ui_sprite_create(state, &loading->sprites[i], 0x190, heights[i], 0x7b81 + i, 0, 0, 0, 0, scale, scale);
        mu_ui_sprite_show(&loading->sprites[i], 1);
    }
    float x = ((float)screen_width - 800.0f * scale) / 2.0f;
    x = x / scale;
    mu_ui_sprite_set_position(&loading->sprites[0], cvtt(x), 0, 3);
    mu_ui_sprite_set_position(&loading->sprites[1], cvtt(x + 400.0f), 0, 3);
    mu_ui_sprite_set_position(&loading->sprites[2], cvtt(x), 0x200, 3);
    mu_ui_sprite_set_position(&loading->sprites[3], cvtt(x + 400.0f), 0x200, 3);
}

void mu_ui_loading_render(mu_ui_state *state, const mu_ui_loading *loading)
{
    for (int32_t i = 0; i < MU_UI_LOADING_SPRITES; ++i)
        mu_ui_sprite_render(state, &loading->sprites[i]);
}
