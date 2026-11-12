/* ITEMS-UI-001: 0x016c246e..0x016c248b and cursor test 0x00ec4bf2.
 * Slots arrive in 640x480 coordinates. Truncate each field separately,
 * then compare signed integers, with x86's wrapping endpoint additions. */
#ifndef MU_ITEMS_UI_H
#define MU_ITEMS_UI_H

#include <stdint.h>
#include <string.h>

static inline int32_t mu_items_ui_trunc(float value)
{
    return value >= -2147483648.0f && value < 2147483648.0f ? (int32_t)value : INT32_MIN;
}

static inline int32_t mu_items_ui_add(int32_t a, int32_t b)
{
    uint32_t bits = (uint32_t)a + (uint32_t)b;
    int32_t result;
    memcpy(&result, &bits, sizeof result);
    return result;
}

static inline int mu_items_ui_cursor(const float slot[4], int32_t mouse_x, int32_t mouse_y)
{
    int32_t x = mu_items_ui_trunc(slot[0]), y = mu_items_ui_trunc(slot[1]);
    int32_t w = mu_items_ui_trunc(slot[2]), h = mu_items_ui_trunc(slot[3]);
    return mouse_x >= x && mouse_x < mu_items_ui_add(x, w) &&
           mouse_y >= y && mouse_y < mu_items_ui_add(y, h);
}

/* WM_MOUSEMOVE 0x0121012c..0x012101f7: divide by screen/virtual size,
 * truncate, clamp. The layer supplies window points, after Retina scaling. */
static inline int32_t mu_items_ui_mouse(double point, int32_t screen, int32_t extent)
{
    int32_t value = mu_items_ui_trunc((float)point / ((float)screen / (float)extent));
    return value < 0 ? 0 : value > extent ? extent : value;
}

#endif
