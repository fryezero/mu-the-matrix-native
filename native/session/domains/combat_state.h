#ifndef MU_DOM_COMBAT_STATE_H
#define MU_DOM_COMBAT_STATE_H
#include "combat.h"
typedef struct mu_dom_combat {
    mu_combat_frame_event events[MU_COMBAT_HISTORY];
    uint64_t next;
    uint64_t count[5];
    uint16_t hero_key;
    uint16_t last_damage[400];
    uint8_t killing_skill[400];
} mu_dom_combat;
#endif
