/* domains/hero_state.h (sketch, PRIVATE): the hero's replicated records, in the client's layouts.
 *
 * Storage is the client record, not a native re-description: the verified progress handlers
 * (reconstructed/progress) read and write these bytes at the client's offsets, and
 * live-readers/memread can read the same records from the original for comparison. The typed
 * view (domains/hero.h) is derived from them on read; nothing keeps a second copy.
 *
 * Moves here from: core/mu_progress.c (attr, machine, hero, stat window, bar, last_request),
 * gfx/mu_gfx_layer.c mu_gfx_hero (demo values, deleted), and the four Zen counters
 * (mu_map_session.zen, mu_social_session.zen, mu_gfx_hero.zen, mu_quest_session.zen) -> money.
 */
#ifndef MU_DOM_HERO_STATE_H
#define MU_DOM_HERO_STATE_H
#include "../../../reconstructed/progress/progress.h"

typedef struct mu_dom_hero {
    uint8_t attr[MU_PRG_ATTR_SIZE];          /* CharacterAttribute (class byte at +0x187, HP +0x68, ...) */
    uint8_t machine[MU_PRG_MACHINE_SIZE];    /* the stat machine's totals */
    uint8_t record[0x400];                   /* the hero CHARACTER's replicated part (class +0x12, name +0x44 ...);
                                              * its motion offsets (+0x180/+0x184, o+0x158) are refreshed from the
                                              * world port immediately before each handler call that reads them */
    uint32_t money;                          /* CharacterMachine +0x2d70: THE zen. Shop, mix, trade, warp cost and
                                              * the quest client's mirror all read this field */
    mu_prg_stat_window stat_window;          /* handler-owned window copy (0x55 57 writes it) */
    mu_prg_bar_cache bar;
    uint32_t last_stat_request;              /* 0x01d22d4c: the 100 ms stat-request throttle */
    char name[11];
} mu_dom_hero;

#endif
