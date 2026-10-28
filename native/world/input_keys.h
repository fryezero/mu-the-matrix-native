/* INPUT-001: recovered scan, and menu-id lookup. No platform or session dependencies. */
#ifndef MU_INPUT_KEYS_H
#define MU_INPUT_KEYS_H
#include <stdint.h>
void mu_input_scan(uint8_t state[256], const uint8_t down[256], int enabled,
                   int foreground, int escape_tab_allowed, int active_is_foreground);
/* Modifiers: shift=1, control=2, alt=4. -1 means no menu dispatch in this bounded lookup. */
int mu_input_menu(int vk, int mods);
#endif
