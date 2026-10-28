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
    uint8_t death_flag[400],attack_time[400];
    int16_t target_index[400];
    float voice[400];
} mu_dom_combat;
#endif
