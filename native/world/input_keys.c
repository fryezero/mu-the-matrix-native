#include "input_keys.h"

/* 0x00ec5475..0x00ec5576. The OS queries are supplied by the caller. */
void mu_input_scan(uint8_t state[256], const uint8_t down[256], int enabled,
                   int foreground, int escape_tab_allowed, int active_is_foreground)
{
    if (!enabled) return;
    for (int k = 0; k < 256; ++k) {
        if (down[k] && foreground) {
            if (state[k] == 0 || state[k] == 1) {
                if ((k == 27 || k == 9) && !escape_tab_allowed && active_is_foreground)
                    continue;
                state[k] = 2;
            } else if (state[k] == 2) state[k] = 3;
        } else if (state[k] == 3 || state[k] == 2) state[k] = 1;
        else if (state[k] == 1) state[k] = 0;
    }
}

/* Key branches of 0x00efbfd2. Context eligibility belongs to the window handlers.
 * Ctrl+Z and Ctrl+X are separate branches, not aliases of the unmodified keys. */
int mu_input_menu(int vk, int mods)
{
    if (mods == 2 && vk == 'Z') return 20;
    if (mods == 2 && vk == 'X') return 21;
    if (mods) return -1;
    switch (vk) {
    case 'Y': return 13; case 'I': return 14; case 'C': return 1;
    case 'Q': return 16; case 'W': return 17; case 'E': return 18; case 'R': return 19;
    case 'X': return 0; case 'T': return 2; case 'M': return 4; case 'O': return 5;
    case 'J': return 6; case 'P': return 7; case 'F': return 9; case 'G': return 10;
    case 'B': return 11; case 'N': return 12; case 'K': return 15;
    default: return -1;
    }
}
