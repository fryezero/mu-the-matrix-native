/* domains/hero_state.h (PRIVATE): the hero's replicated records, in the client's layouts.
 *
 * Storage is the client record, not a native re-description: the verified progress handlers
 * (reconstructed/progress) read and write these bytes at the client's offsets, and
 * live-readers/memread can read the same records from the original for comparison. The typed view
 * (domains/hero.h) is derived from them on read; nothing keeps a second copy.
 *
 * Moves here from core/mu_progress.c (attr, machine, hero, stat window, bar, last_request, speed
 * row) - mu_progress.c itself stays until its world/GFx callers read the session (stage 2) - and,
 * later, the four Zen counters (mu_map_session.zen, mu_social_session.zen, mu_gfx_hero.zen,
 * mu_quest_session.zen) -> money.
 */
#ifndef MU_DOM_HERO_STATE_H
#define MU_DOM_HERO_STATE_H
#include "../../../reconstructed/progress/progress.h"

#define MU_HERO_RECORD_SIZE 0x400u
#define MU_HERO_TILE_OFFSET 0x180u   /* CHARACTER +0x180/+0x184: the tile (motion zone) */

typedef struct mu_dom_hero {
    uint8_t attr[MU_PRG_ATTR_SIZE];          /* CharacterAttribute (class byte at +0x187, HP +0x68, ...) */
    uint8_t machine[MU_PRG_MACHINE_SIZE];    /* the stat machine's totals */
    uint8_t record[MU_HERO_RECORD_SIZE];     /* the hero CHARACTER's replicated part (class +0x12); its tile
                                              * (+0x180/+0x184) is refreshed from the world port before each
                                              * handler call */
    uint32_t money;                          /* CharacterMachine +0x2d70: THE zen (0xA0 0x30 +0x1c) */
    mu_prg_stat_window stat_window;          /* handler-owned window copy (0x55 57 writes it) */
    mu_prg_bar_cache bar;                    /* the HUD bar's cache, window +0x88 (the client never writes it) */
    uint16_t speed_row[2];                   /* the speed row's last values (window +0xbc, +0xbe) */
    char speed_text[32];
    char exp_json[256];                      /* the last setExpData object */
    uint32_t last_stat_request;              /* 0x01d22d4c: the 100 ms stat-request throttle */
    char name[11];
    int recalculated;                        /* the stat machine ran (the derived rows are valid) */
    /* per handler call (the env adapter) */
    uint32_t handler;                        /* the client handler being run (cue provenance) */
    int16_t cue_key;                         /* the character key the frame names (damage cues), -1 */
    int send_seen;                           /* the handler called Send 0x00d51d4f ... */
    int32_t send_args[2];                    /* ... with these arguments */
} mu_dom_hero;

#endif
