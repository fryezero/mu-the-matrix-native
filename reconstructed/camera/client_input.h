#ifndef MU_CLIENT_INPUT_H
#define MU_CLIENT_INPUT_H

/* Keyboard and mouse input of the client (NATIVE-FRAME-001,
 * docs/research/client-camera-input.md). Authored names.
 *
 * Keyboard: the client polls all 256 virtual keys with GetAsyncKeyState
 * once per 40 ms logic step (0x00ec5475, called at the top of each step in
 * the frame driver) into a four-state table at 0x01ec91c0. Mouse buttons are
 * polled the same way (VK 1, 2, 4) and are also tracked from window
 * messages into the legacy globals below by the window procedure
 * 0x0120fee3 (registered through an IGC.dll wrapper, treated as opaque). */

#include <stdint.h>

enum {
    MU_KEY_NONE = 0,    /* up */
    MU_KEY_RELEASE = 1, /* released this step */
    MU_KEY_PRESS = 2,   /* pressed this step */
    MU_KEY_REPEAT = 3   /* held */
};

typedef struct mu_key_input {
    uint8_t state[256];
} mu_key_input;

/* What the scan reads from the system for one step. */
typedef struct mu_key_sample {
    uint8_t active;              /* window-active byte 0x06fc9cb5; 0: no scan, queries false */
    uint8_t down[256];           /* GetAsyncKeyState(vk) & 0x8000 */
    uint8_t game_foreground;     /* GetForegroundWindow() == game window 0x06fc9c94 */
    uint8_t focus_is_foreground; /* GetFocus() == GetForegroundWindow() */
    uint8_t key_message_down;    /* 0x0bdc5982: WM_KEYDOWN sets, WM_KEYUP clears */
} mu_key_sample;

/* 0x00ec5475. Down and foreground: NONE/RELEASE -> PRESS (except Esc and
 * Tab while no WM_KEYDOWN is pending and the focus is the foreground
 * window: unchanged), PRESS -> REPEAT. Otherwise REPEAT/PRESS -> RELEASE,
 * RELEASE -> NONE. */
void mu_key_scan(mu_key_input *keys, const mu_key_sample *sample);
/* 0x00ec5577 / 0x00ec55ac / 0x00ec55e2 / 0x00ec5618 (wrappers 0x00ec537f,
 * 0x00ec5393, 0x00ec53a7, 0x00ec53bb): state == NONE/RELEASE/PRESS/REPEAT,
 * always 0 while inactive. */
int mu_key_is(const mu_key_input *keys, uint8_t active, int vk, int state);

/* Legacy mouse globals written by the window procedure 0x0120fee3. */
typedef struct mu_mouse {
    int32_t x, y;                       /* MouseX/MouseY 0x0bdc5ad8/dc, 640x480 virtual */
    float scale_x, scale_y;             /* 0x06fbcd94/98: window size / (640, 480) */
    uint8_t left, left_push, left_pop;  /* 0x0bdc5981, 0x0bdc599c, 0x0bdc5983 */
    uint8_t left_double;                /* 0x0bdc59a0 */
    uint8_t right, right_push, right_pop;  /* 0x0bdc599d, 0x0bdc599f, 0x0bdc599e */
    uint8_t middle, middle_push, middle_pop; /* 0x0bdc59a1, 0x0bdc59a3, 0x0bdc59a2 */
    int32_t wheel;                      /* 0x0bdc59a4: (short)HIWORD(wParam) / 120 */
    int32_t last_click_x, last_click_y; /* 0x06fc9e58/5c, at WM_LBUTTONUP */
    int32_t idle;                       /* 0x06fc9e4c, cleared by every button message */
} mu_mouse;

enum {
    MU_WM_MOUSEMOVE = 0x200,
    MU_WM_LBUTTONDOWN = 0x201,
    MU_WM_LBUTTONUP = 0x202,
    MU_WM_LBUTTONDBLCLK = 0x203,
    MU_WM_RBUTTONDOWN = 0x204,
    MU_WM_RBUTTONUP = 0x205,
    MU_WM_MBUTTONDOWN = 0x207,
    MU_WM_MBUTTONUP = 0x208,
    MU_WM_MOUSEWHEEL = 0x20a
};

/* One window message (the guards on the hero state and UI capture that
 * precede the left/right button cases are the caller's: pass only
 * messages the client would accept). WM_MOUSEMOVE: x =
 * cvtt((short)LOWORD(lParam) / scale_x), y likewise, then clamped to
 * 0..640 / 0..480. Returns, for WM_MOUSEWHEEL, the zoom delta the client
 * passes to the camera ((short)HIWORD(wParam) / 40.0f), else 0. */
float mu_mouse_message(mu_mouse *mouse, uint32_t message, uint32_t wparam, uint32_t lparam);

#endif
