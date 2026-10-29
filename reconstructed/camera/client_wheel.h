#ifndef MU_CLIENT_WHEEL_H
#define MU_CLIENT_WHEEL_H

/* RENDER-TIME-003 (docs/research/client-render-time.md, "Zoom refusal and visible objects"). Authored names.
 *
 * GetScreenWidth 0x016bc355: the width of the 3D view in 640x480 units. It is 640 with no side window open,
 * 450 with one, 260 with two (or a wide one) and 70 for window 0x4b. The window size never enters it: the world
 * render passes it to BeginOpengl (0x018577e8, 0x01859411), to CreateFrustrum as aspect = width / 640
 * (0x0185784f, 0x018596ac) and, through 0x0098c6b4, to the CreateFrustrum2D scale (0x016d23fc). */

#include <stdint.h>

#include "client_camera.h"
#include "client_input.h"
#include "client_world_camera.h"

/* NewUI window-open query 0x00f2aba9 on 0x00f2bb92() for the window id. */
typedef int (*mu_ui_window_open)(void *context, int32_t id);

int32_t mu_client_screen_width(mu_ui_window_open open, void *context);

/* The WM_MOUSEWHEEL route of the window procedure 0x0120fee3.
 *
 * 1. Default case 0x012102cf: the UI layer 0x01d22c60 handler 0x00aefb79 sees the message first. It declines
 *    (returns 0) when the hero byte +0x190 is set, when its base movie (base.swf, layer +0x88) is absent, or when
 *    the GFx manager's window +0x254 is shown. Otherwise, after 0x00af0245 (not part of the route), the wheel case
 *    0x00aefff8 converts lParam to a client point (lParam - ClientToScreen(0,0)) and:
 *      - consumes it when the GFx mouse dispatch 0x00ac9800 reports it handled;
 *      - sends base.swf a wheel event (type 4, client x, y, lines = ((delta << 7) / 120) / 120 * 3), stores
 *        MouseWheel = delta / 120, and consumes it when base.swf hit-tests (HitTest(x, y, 3)) at the client
 *        point, or at the raw 16-bit lParam (a screen point for this message), each time sending event 8.
 *    A consumed message clears LPush/LButton, sets LPop and 0x0b436573, and the procedure returns 0.
 * 2. Case 0x0121069d: the client point again; MouseWheel = delta / 120 is stored after the guards. The zoom
 *    handler is called unless the GFx dispatch reports the wheel handled, the chat window ([0x01d22c6c] +0x68,
 *    InMouseViewBox) holds the mouse, or the GFx input object [0x01d22c0c] +0x70 is missing or its +0xc is set.
 * 3. Wheel handler 0x018588d9: refused while NewUI window 0x3e is open or in world 0x8b (0x00da9d49), then
 *    mu_world_camera_wheel (the world-FOV scenes, the zoom-settled flag, the index and 0x0185a9bf).
 * 4. Common exit 0x01211083 (not for a consumed message): clears the double click; LPop is cleared when the last
 *    click is not at MouseX/Y. */
typedef struct mu_wheel_env {
    void *context;
    /* 0x00ac9800; call = 0 for the first dispatch of this message, 1 for the second */
    int (*dispatch)(void *context, int32_t call, uint32_t message, uint32_t wparam, uint32_t point);
    int (*hit_test)(void *context, float x, float y);                                    /* base.swf vtable +0xc0 */
    void (*event)(void *context, int32_t type, float x, float y, float lines);           /* base.swf vtable +0xb4 */
    int (*window_open)(void *context, int32_t id);                                       /* 0x00f2aba9 */
    int32_t origin_x, origin_y;     /* ClientToScreen(hwnd, (0, 0)) */
    uint8_t hero_busy;              /* [0x0a39d754] != 0 and its byte +0x190 != 0 */
    uint8_t base_movie;             /* [0x01d22c60 + 0x88] != 0 */
    uint8_t focus_window_shown;     /* [GFx manager + 0x254] != 0 and 0x00aae6f9() */
    uint8_t chat_in_view;           /* [0x01d22c6c] +0x68 */
    uint8_t gfx_input;              /* [GFx manager + 0x70] != 0 */
    uint8_t gfx_window6;            /* [[GFx manager + 0x70] + 0xc] */
} mu_wheel_env;

enum {
    MU_WHEEL_UI_LAYER = 1,          /* consumed by the UI layer: no zoom, procedure returns 0 */
    MU_WHEEL_UI_GUARD = 2,          /* case 0x0121069d did not call the handler */
    MU_WHEEL_HANDLER_GUARD = 3,     /* 0x018588d9 refused (window 0x3e, world 0x8b, world FOV, not settled) */
    MU_WHEEL_ZOOM = 4               /* the zoom index changed and 0x0185a9bf ran */
};

/* Returns the stage; *ui_flag is set to 1 for MU_WHEEL_UI_LAYER (0x0b436573). */
int mu_client_mouse_wheel(mu_world_camera *camera, mu_client_view *view, mu_mouse *mouse, const mu_wheel_env *env,
                          uint32_t wparam, uint32_t lparam, int32_t min_index, uint8_t *ui_flag);

#endif
