/* Reconstructed per-window GFx render pass 0x00abfcca (NATIVE-HUD-001).
 *
 * The GFx manager keeps its open windows in a std::list (manager +4).  For
 * each window the pass draws the movie, then a 3D item pass over it with a
 * pixel orthographic projection, then a 2D overlay pass.  The GL calls go
 * through UI-001's sink (reconstructed/ui/ui2d.h) with the extra operations
 * below; the window's own work is reported as events.
 */
#ifndef MU_HUD_ITEM_PASS_H
#define MU_HUD_ITEM_PASS_H

#include <stdint.h>

#include "../ui/ui2d.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Extra platform calls (same word conventions as enum mu_ui_op). */
enum {
    MU_HUD_GL_PUSHATTRIB = 100, MU_HUD_GL_POPATTRIB, MU_HUD_GL_ORTHO, MU_HUD_GL_GETFLOATV, MU_HUD_GL_TRANSLATEF,
    MU_HUD_WINDOW_DISPLAY,      /* window vtable +0x1c (GFx movie display); word: window id */
    MU_HUD_WINDOW_ITEMS,        /* vtable +0x20 (the item pass, e.g. 0x00ab6130); word: window id */
    MU_HUD_WINDOW_OVERLAY       /* vtable +0x24; word: window id */
};

typedef struct mu_hud_window {
    uint32_t id;                /* the window object (opaque word) */
    uint8_t identity;           /* one of the three windows exempt from the NewUI test (0x0095f5d7, InfoPopup 0x009e819e, 0x00ac16af) */
    uint8_t excluded;           /* the window 0x00ac16d0 returns: never drawn here */
    float alpha;                /* +0x50 */
} mu_hud_window;

/* Camera globals the pass reads and writes. */
typedef struct mu_hud_camera {
    float matrix[3][4];         /* 0x0bdc5918: modelview read back by 0x0184a569 */
    float saved[3][4];          /* 0x0bdc5948 (0x0185038d / 0x018503e0) */
    float position[3];          /* 0x0bdc5ab4: camera position */
    float eye[3];               /* 0x0bdc5984: written by the camera restore 0x0184b705 */
    float rate[2], saved_rate[2];   /* 0x0bdc58cc/d0 and 0x0bdc58d4/d8 */
} mu_hud_camera;

/* glGetFloatv(GL_MODELVIEW_MATRIX) answer, column-major (platform boundary). */
typedef void (*mu_hud_get_modelview)(void *user, float m[16]);

/* 0x00abfcca: `windows` in drawing order.  The client walks its std::list
 * with reverse iterators, so the drawing order is the list order reversed
 * (the most recently added window first).  `ui_hidden` = NewUI windows 0x45,
 * 0x37 or 0x3e visible. */
void mu_hud_window_pass(mu_ui_state *state, mu_hud_camera *camera, const mu_hud_window *windows, int32_t count,
                        int ui_hidden, mu_hud_get_modelview get_modelview, void *user);

#ifdef __cplusplus
}
#endif

#endif
