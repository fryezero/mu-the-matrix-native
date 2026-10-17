/* Reconstructed 2D overlay of the login scene (NATIVE-UI-001).
 *
 * The login-scene render 0x01857ed9 (scene state 3) draws the 3D login world
 * first (out of scope here), then, between BeginBitmap and EndBitmap
 * (0x01858108..0x018588ac):
 *   - a fade value [0x0bdc5b80] += 0.02 per frame, capped at 10;
 *   - EnableAlphaBlend, glColor4f(fade - 0.3), EnableAlphaTest(1), glColor4f(fade);
 *   - the MU logo glow Logo\MU-logo_g.tga (0x7b1f, colour 0x4cffffff) and the
 *     logo Logo\MU-logo.tga (0x7b1e, colour 0xffffffff), both sized from the
 *     logo's image size, centred, at y = window height * 0.05 (640x480 units);
 *   - three GDI text lines: GlobalText[454] right-aligned at x = 300,
 *     GlobalText[455] at x = 300, and sprintf(GlobalText[456], version) at the
 *     right edge, all on the bottom line;
 *   - then the scene's UI manager and cursor (not part of this slice).
 * GlobalText strings come from the encrypted Data\Lang.mpr and the version
 * bytes from the packed third section; both are inputs here.
 */
#ifndef MU_UI_LOGIN_H
#define MU_UI_LOGIN_H

#include "ui2d.h"
#include "ui_text.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct mu_ui_login_text {
    const char *text454;        /* GlobalText[0x1c6] */
    const char *text455;        /* GlobalText[0x1c7] */
    const char *format456;      /* GlobalText[0x1c8], one %s */
    uint8_t version_bytes[5];   /* 0x01cf100c..: each byte minus (i + 1) gives a character */
} mu_ui_login_text;

/* Advances *fade as the client does once per rendered frame, then draws.
 * screen_width640: 0x016bc355 (640 with no side windows open). */
void mu_ui_login_overlay(mu_ui_state *state, mu_ui_text *text, float *fade, uint32_t screen_width640,
                         const mu_ui_login_text *strings);

/* The decoded version string (5 characters, no separators: the client's
 * separator branch tests i % 1 and never fires). */
void mu_ui_login_version(const uint8_t bytes[5], char out[6]);

#ifdef __cplusplus
}
#endif
#endif
