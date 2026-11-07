/* The progress fixture's DEMO join rules (behaviors/progress.c, copied from core/mu_progress.c): the class start
 * stats and the HP/MP/SD/AG maxima for a class index, level and stats. DEMO server values, not client data:
 * the original client has no maxima formula. Its join answer 0x0124cc64 copies the server's eight words into
 * CharacterAttribute +0x68..+0x84 (docs/research/client-app-polish7.md). The level-1 Dark Knight values agree with
 * the live recording (1100/200/52/25, client-progression section 7). Shared by the fixture server and the world
 * seed (hero_join.h), so the session's maxima and the server's resource answers are one rule. */
#ifndef MU_FIXTURE_PROGRESS_DEMO_H
#define MU_FIXTURE_PROGRESS_DEMO_H
#include <stdint.h>

/* The class start stats str, agi, vit, ene, cmd of a class index (DEMO) */
static inline void mu_fx_progress_start_stats(int32_t cls, int32_t out[5])
{
    static const int16_t START[16][5] = {
        {18, 18, 15, 30, 0}, {28, 20, 25, 10, 0}, {22, 25, 20, 15, 0}, {26, 26, 26, 26, 0},
        {26, 20, 20, 15, 25}, {21, 21, 18, 23, 0}, {32, 27, 25, 20, 0}, {30, 30, 25, 24, 0},
        {13, 18, 14, 40, 0}, {28, 30, 15, 10, 0}, {20, 18, 20, 30, 0}, {15, 20, 15, 40, 0},
        {15, 20, 15, 40, 0}, {25, 28, 15, 10, 0}, {15, 25, 15, 30, 0}, {28, 22, 20, 12, 0}};
    for (int i = 0; i < 5; i++)
        out[i] = START[cls & 15][i];
}

/* HP, MP, SD, AG maxima (DEMO). base HP, HP per level x10, HP per vitality x10, base MP, MP per level x10, MP per
 * energy x10: the classic tables with the bases times 10, as this server gives a level-1 Dark Knight 1100 HP and
 * 200 MP (live). */
static inline void mu_fx_progress_demo_maxima(int32_t cls, int32_t level, const int32_t s[5], int32_t out[4])
{
    static const int16_t MAXIMA[16][6] = {
        {600, 10, 20, 600, 20, 20}, {1100, 20, 30, 200, 5, 10}, {800, 10, 20, 300, 15, 15}, {1100, 10, 20, 600, 10, 20},
        {900, 15, 20, 400, 10, 15}, {700, 10, 20, 400, 15, 15}, {1000, 13, 20, 400, 10, 15}, {1100, 20, 30, 200, 5, 10},
        {600, 10, 20, 600, 20, 20}, {1100, 20, 30, 200, 5, 10}, {800, 10, 20, 400, 15, 15}, {600, 10, 20, 600, 20, 20},
        {600, 10, 20, 600, 20, 20}, {1100, 20, 30, 200, 5, 10}, {700, 10, 20, 500, 15, 20}, {1100, 20, 30, 200, 5, 10}};
    const int16_t *m = MAXIMA[cls & 15];
    int32_t st[5];
    mu_fx_progress_start_stats(cls, st);
    int32_t lv = level > 1 ? level - 1 : 0;
    out[0] = m[0] + lv * m[1] / 10 + (s[2] - st[2]) * m[2] / 10;
    out[1] = m[3] + lv * m[4] / 10 + (s[3] - st[3]) * m[5] / 10;
    out[2] = (s[0] + s[1] + s[2] + s[3] + s[4]) * 6 / 10 + level * 3;
    out[3] = s[0] * 15 / 100 + s[1] * 2 / 10 + s[2] * 3 / 10 + s[3];
    for (int i = 0; i < 4; i++)
        if (out[i] < 1)
            out[i] = 1;
        else if (out[i] > 0xffff)
            out[i] = 0xffff;
}
#endif
