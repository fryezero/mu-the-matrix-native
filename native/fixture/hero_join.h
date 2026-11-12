/* The offline demo hero's join HP/MP/SD/AG, current = maximum (APP-POLISH-003, APP-POLISH-007).
 *
 * The original client has no class/level/stat formula for these maxima: the join answer 0x0124cc64 copies the
 * server's words into CharacterAttribute +0x68..+0x84, and only server answers write them afterwards
 * (docs/research/client-app-polish7.md). Sources, in order:
 *   1. the recorded level-1 Dark Knight (FryeZEN2, MTM-1, 2026-10-22, docs/research/client-progression.md
 *      sections 1, 7): class byte 1, level 1, stats 28/20/25/10/0 -> 1100/200/52/25;
 *   2. otherwise the progress fixture's DEMO join maxima (progress_demo.h) for the class, level and stats the
 *      fixture server is given for this hero (mu_skills_demo_hero: the offline session's "hero" line, else the
 *      class start stats at level 1, or the seed's own level). The server's resource answers (A0/30, A0/06,
 *      A0/11) use the same rule, so the HUD's current and maximum values agree.
 * The same authored join supplies level and unspent points to the development seed.
 * Fixture data for the offline demo characters only. */
#ifndef MU_FIXTURE_HERO_JOIN_H
#define MU_FIXTURE_HERO_JOIN_H
#include <string.h>
#include "../session/mu_session_seed.h"
#include "progress_demo.h"
#include "skills_demo.h"
static inline void mu_fixture_hero_join(mu_session_seed *seed, const mu_skills_demo_join *join)
{
    static const int32_t RECORDED_STATS[5] = {28, 20, 25, 10, 0};
    int32_t cls = seed->class_byte & 15, level = seed->level > 0 ? seed->level : 1, stats[5];
    mu_fx_progress_start_stats(cls, stats);
    if (cls != 4)
        stats[4] = 0;
    if (join && join->has_stats) {
        level = join->level > 0 ? join->level : 1;
        seed->level = level;
        seed->points = join->points;
        memcpy(stats, join->stats, sizeof stats);
    }
    if (seed->class_byte == 1 && level == 1 && !memcmp(stats, RECORDED_STATS, sizeof stats)) {
        seed->vitals[0] = 1100;
        seed->vitals[1] = 200;
        seed->vitals[2] = 52;
        seed->vitals[3] = 25;
        return;
    }
    mu_fx_progress_demo_maxima(cls, level, stats, seed->vitals);
}
#endif
