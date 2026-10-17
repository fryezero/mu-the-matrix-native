/* Keyboard scan and window-message mouse state. See client_input.h. */
#include "client_input.h"

#include "client_camera.h"

void mu_key_scan(mu_key_input *keys, const mu_key_sample *s)
{
    if (!s->active)
        return;
    for (int vk = 0; vk < 256; ++vk) {
        uint8_t *state = &keys->state[vk];
        if (s->down[vk] && s->game_foreground) {
            if (*state == MU_KEY_NONE || *state == MU_KEY_RELEASE) {
                if ((vk == 0x1b || vk == 0x09) && !s->key_message_down && s->focus_is_foreground)
                    continue;
                *state = MU_KEY_PRESS;
            } else if (*state == MU_KEY_PRESS) {
                *state = MU_KEY_REPEAT;
            }
        } else if (*state == MU_KEY_REPEAT || *state == MU_KEY_PRESS) {
            *state = MU_KEY_RELEASE;
        } else if (*state == MU_KEY_RELEASE) {
            *state = MU_KEY_NONE;
        }
    }
}

int mu_key_is(const mu_key_input *keys, uint8_t active, int vk, int state)
{
    if (!active)
        return 0;
    return keys->state[vk & 0xff] == state;
}

float mu_mouse_message(mu_mouse *m, uint32_t message, uint32_t wparam, uint32_t lparam)
{
    switch (message) {
    case MU_WM_MOUSEMOVE:
        m->x = mu_cvtt((float)(int16_t)(lparam & 0xffff) / m->scale_x);
        m->y = mu_cvtt((float)(int16_t)(lparam >> 16) / m->scale_y);
        if (m->x < 0)
            m->x = 0;
        if (m->x > 640)
            m->x = 640;
        if (m->y < 0)
            m->y = 0;
        if (m->y > 480)
            m->y = 480;
        return 0.0f;
    case MU_WM_LBUTTONDOWN:
        m->idle = 0;
        m->left_pop = 0;
        if (!m->left)
            m->left_push = 1;
        m->left = 1;
        return 0.0f;
    case MU_WM_LBUTTONUP:
        m->idle = 0;
        m->left_push = 0;
        m->left_pop = 1;
        m->left = 0;
        m->last_click_x = m->x;
        m->last_click_y = m->y;
        return 0.0f;
    case MU_WM_LBUTTONDBLCLK:
        m->idle = 0;
        m->left_double = 1;
        return 0.0f;
    case MU_WM_RBUTTONDOWN:
        m->idle = 0;
        m->right_pop = 0;
        if (!m->right)
            m->right_push = 1;
        m->right = 1;
        return 0.0f;
    case MU_WM_RBUTTONUP:
        m->idle = 0;
        m->right_push = 0;
        if (m->right)
            m->right_pop = 1;
        m->right = 0;
        return 0.0f;
    case MU_WM_MBUTTONDOWN:
        m->idle = 0;
        m->middle_pop = 0;
        if (!m->middle)
            m->middle_push = 1;
        m->middle = 1;
        return 0.0f;
    case MU_WM_MBUTTONUP:
        m->idle = 0;
        m->middle_push = 0;
        if (m->middle)
            m->middle_pop = 1;
        m->middle = 0;
        return 0.0f;
    case MU_WM_MOUSEWHEEL: {
        int32_t delta = (int16_t)(wparam >> 16);
        m->wheel = delta / 120;
        return (float)delta / 40.0f;
    }
    default:
        return 0.0f;
    }
}
