#include "client_wheel.h"

/* 0x016bc355 */
int32_t mu_client_screen_width(mu_ui_window_open open, void *context)
{
    int32_t width;
    static const int32_t narrow[] = {0x0d, 0x10, 0x03, 0x15, 0x06, 0x16, 0x17, 0x18, 0x04, 0x12, 0x0a, 0x05, 0x19,
                                     0x1a, 0x13, 0x14, 0x38, 0x3b, 0x46, 0x41, 0x42, 0x43, 0x3f, 0x48, 0x47};
    static const int32_t wide[] = {0x08, 0x0c, 0x09, 0x07, 0x0e, 0x0f, 0x39, 0x49};
    int two = 0;
    if (open(context, 0x0d) && open(context, 0x10))
        two = 1;
    for (unsigned i = 0; !two && i < sizeof wide / sizeof wide[0]; ++i)
        if (open(context, wide[i]))
            two = 1;
    if (two)
        width = 260;
    else if (open(context, 0x10) && (open(context, 0x04) || open(context, 0x42)))
        width = 260;
    else if (open(context, 0x10) && open(context, 0x0b))
        width = 260;
    else if (open(context, 0x1b))
        width = 260;
    else {
        width = 640;
        for (unsigned i = 0; i < sizeof narrow / sizeof narrow[0]; ++i)
            if (open(context, narrow[i])) {
                width = 450;
                break;
            }
    }
    if (open(context, 0x4a))
        width = 260;
    else if (open(context, 0x4b))
        width = 70;
    return width;
}

static uint32_t client_point(const mu_wheel_env *e, uint32_t lparam, int32_t *x, int32_t *y)
{
    *x = (int32_t)(int16_t)(lparam & 0xffffu) - e->origin_x;
    *y = (int32_t)(int16_t)(lparam >> 16) - e->origin_y;
    return ((uint32_t)*x & 0xffffu) | (((uint32_t)*y & 0xffffu) << 16);
}

/* 0x00aefb79 for WM_MOUSEWHEEL (case 0x00aefff8): 1 = consumed. */
static int ui_layer(mu_mouse *m, const mu_wheel_env *e, uint32_t wparam, uint32_t lparam, int32_t *calls)
{
    if (e->hero_busy || !e->base_movie || e->focus_window_shown)
        return 0;
    int32_t x, y;
    uint32_t point = client_point(e, lparam, &x, &y);
    if (e->dispatch(e->context, (*calls)++, MU_WM_MOUSEWHEEL, wparam, point))
        return 1;
    int32_t delta = (int16_t)(wparam >> 16);
    int32_t lines = delta * 128 / 120 / 120 * 3;
    e->event(e->context, 4, (float)x, (float)y, (float)lines);
    m->wheel = delta / 120;
    if (e->hit_test(e->context, (float)x, (float)y)) {
        e->event(e->context, 8, 0.0f, 0.0f, 0.0f);
        return 1;
    }
    if (e->hit_test(e->context, (float)(int32_t)(lparam & 0xffffu), (float)(int32_t)(lparam >> 16))) {
        e->event(e->context, 8, 0.0f, 0.0f, 0.0f);
        return 1;
    }
    return 0;
}

int mu_client_mouse_wheel(mu_world_camera *c, mu_client_view *v, mu_mouse *m, const mu_wheel_env *e,
                          uint32_t wparam, uint32_t lparam, int32_t min_index, uint8_t *ui_flag)
{
    int32_t calls = 0;
    if (ui_layer(m, e, wparam, lparam, &calls)) {   /* 0x012102ed */
        m->left_push = 0;
        m->left_pop = 1;
        m->left = 0;
        *ui_flag = 1;
        return MU_WHEEL_UI_LAYER;
    }
    int stage = MU_WHEEL_UI_GUARD;
    int32_t x, y;
    uint32_t point = client_point(e, lparam, &x, &y);
    int32_t delta = (int16_t)(wparam >> 16);
    if (!e->dispatch(e->context, calls, MU_WM_MOUSEWHEEL, wparam, point) && !e->chat_in_view &&
        e->gfx_input && !e->gfx_window6) {
        /* 0x018588d9 */
        stage = MU_WHEEL_HANDLER_GUARD;
        if (!e->window_open(e->context, 0x3e) && c->world != 0x8b &&
            mu_world_camera_wheel(c, v, (float)delta / 40.0f, min_index))
            stage = MU_WHEEL_ZOOM;
    }
    m->wheel = delta / 120;
    /* 0x01211083 */
    m->left_double = 0;
    if (m->left_pop == 1 && (m->last_click_x != m->x || m->last_click_y != m->y))
        m->left_pop = 0;
    return stage;
}
