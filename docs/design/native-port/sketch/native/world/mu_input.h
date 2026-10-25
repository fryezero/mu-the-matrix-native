/* INPUT-001 (sketch): input messages in Win32 form, the shape mu_walk_message already takes.
 *
 * Front ends translate SDL events into these and hand them to mu_world_rt_input (in the world)
 * or to the shell (other scenes). The router runs the client's order:
 *   1. the GFx layer (first refusal: an open window or the HUD under the cursor)
 *   2. the key scan 0x00ec5475 (verified) -> panel bindings (static table, INPUT-001 recovers names)
 *   3. skill/item hotkeys (digits cast via the skills domain's current bar; Alt/Space ground items;
 *      Q/W/E/R potions; ...)
 *   4. walk/attack (mu_walk: left click; MoveHero's attack case through the combat part)
 * Steps 2-4 end in mu_session_submit or in view-local UI state (a panel opens); never in a
 * direct write to replicated state.
 */
#ifndef MU_INPUT_H
#define MU_INPUT_H
#include <stdint.h>

typedef struct mu_input_msg {
    uint32_t message;               /* WM_KEYDOWN, WM_KEYUP, WM_CHAR, WM_LBUTTONDOWN, WM_MOUSEMOVE, WM_MOUSEWHEEL ... */
    uint32_t wparam, lparam;
    uint32_t time_ms;               /* GetMessageTime equivalent (scripted runs: virtual ticks) */
} mu_input_msg;

/* Script form for verification (verify-mu-native --script "FRAME:ACTION"): the same messages,
 * so one input script drives mu-world, mu-client and (through the Wine track's injector) the
 * original client. */
int mu_input_parse_script(const char *text, mu_input_msg *out, int32_t *frames, int cap);

#endif
