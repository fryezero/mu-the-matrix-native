/* The character window's "+" buttons and the stat request (NATIVE-PROGRESS-001).  See progress.h. */
#include <string.h>

#include "progress_internal.h"

int32_t mu_prg_stat_button(const uint8_t *a, double row)
{
    static const double ROWS[5] = {8.0, 13.0, 24.0, 29.0, 42.0};
    if (mu_prg_u16(a, MU_PRG_A_POINTS) == 0)
        return -1;
    for (int i = 0; i < 5; i++)
        if (row == ROWS[i])
            return MU_PROGRESS_MUTATION == 7 && i == 4 ? 3 : i;
    return -1;
}

int mu_prg_stat_request(const mu_prg_env *e, uint32_t *last, uint32_t now, int32_t stat, uint8_t packet[5])
{
    if (now - *last < 100u)
        return 0;
    *last = now;
    packet[0] = 0xc1;
    packet[1] = 5;
    packet[2] = 0x01;
    packet[3] = 0x00;
    packet[4] = (uint8_t)stat;
    mu_prg_emitf(e, "call 00d51d4f 0 0");
    mu_prg_emitf(e, "call 00a6ac96 19 0 0");
    return 5;
}
