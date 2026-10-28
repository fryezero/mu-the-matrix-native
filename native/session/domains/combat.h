#ifndef MU_SESSION_COMBAT_H
#define MU_SESSION_COMBAT_H
#include "combat_wire.h"
typedef struct mu_session mu_session;
#define MU_COMBAT_HISTORY 128
/* Ordered handler outputs for presentation. Damage never implies death. */
typedef struct mu_combat_frame_event {
    uint64_t seq;
    uint8_t kind; /* 1 damage, 2 die, 3 action */
    uint16_t key, skill, target;
    mu_combat_damage damage;
    uint8_t drop[19];
} mu_combat_frame_event;
size_t mu_session_combat_events(const mu_session *s,uint64_t *cursor,mu_combat_frame_event *out,size_t cap,uint32_t *lost);
uint64_t mu_session_combat_count(const mu_session *s,unsigned kind);
uint16_t mu_session_combat_hero_key(const mu_session *s);
#endif
