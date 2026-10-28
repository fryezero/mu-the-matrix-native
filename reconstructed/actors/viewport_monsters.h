/* VIEWPORT-MONSTER-001. 0x0122c426, bounded record/placement fields.
 * Creation uses the existing world-0/rand-0 extracted class table. See finding. */
#ifndef MU_VIEWPORT_MONSTERS_H
#define MU_VIEWPORT_MONSTERS_H
#include "../players/remote_players.h"
typedef struct mu_monster_viewport {
    int32_t size;
    uint16_t key, server_class, level;
    uint32_t max_hp, hp;
    uint8_t created, special, x, y, target[2], direction, elemental;
    uint8_t flag_34, object_43, state, effect, buff_count;
    uint16_t words[4], buff_type[56];
    uint32_t buff_value[56];
} mu_monster_viewport;
int mu_monster_viewport_record(const uint8_t *p, int32_t length, mu_monster_viewport *v);
int mu_monster_character_create(mu_rp_character *c, const mu_monster_viewport *v);
void mu_monster_viewport_apply(mu_rp_character *c, const mu_monster_viewport *v, const mu_rp_env *env);
#endif
