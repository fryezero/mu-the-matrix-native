/* SYS-MISC-001a WIP. Pure BossHPUI window arithmetic, not a receive handler. */
#ifndef MU_MISC_H
#define MU_MISC_H
#include <stdint.h>
typedef struct mu_misc_boss_bar {
    int32_t unit, segments, remaining, current_colour, next_colour;
} mu_misc_boss_bar;
/* 0x00b360b1, 0x00b35d65, 0x00b35d89 and 0x00b35c40. */
void mu_misc_boss_init(mu_misc_boss_bar *bar);
int32_t mu_misc_boss_colour(int32_t index);
int32_t mu_misc_boss_gauge(const mu_misc_boss_bar *bar, int32_t hp, int32_t maximum);
/* Host guards refuse zero divisors/nonpositive segment counts before the original arithmetic.
 * No packet, transport, send or game-state mutation belongs to this module. */
int mu_misc_boss_set_maximum(mu_misc_boss_bar *bar, int32_t maximum);
int mu_misc_boss_update(mu_misc_boss_bar *bar, int32_t hp);
#endif
