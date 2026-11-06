/* APP-POLISH-003: recorded level-1 Dark Knight join data, not a server formula.
 * FryeZEN2, MTM-1, 2026-10-22: docs/research/client-progression.md sections 1, 7.
 * Other profiles remain unavailable; do not extrapolate this observation. */
#ifndef MU_FIXTURE_HERO_JOIN_H
#define MU_FIXTURE_HERO_JOIN_H
#include "../session/mu_session_seed.h"
static inline void mu_fixture_hero_join(mu_session_seed *seed)
{
    if (seed->class_byte != 1 || seed->level > 1) return;
    seed->vitals[0] = 1100;
    seed->vitals[1] = 200;
    seed->vitals[2] = 52;
    seed->vitals[3] = 25;
}
#endif
