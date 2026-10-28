#ifndef MU_MONSTERS_DEMO_H
#define MU_MONSTERS_DEMO_H
#include "../core/mu_world_actors.h"
typedef struct mu_monster_spec {
    int32_t server_class, x, y, direction, wander;
    char label[48];
} mu_monster_spec;
int mu_monsters_parse(const char *text, mu_monster_spec *specs, int32_t *count, char *error, size_t cap);
void mu_monsters_demo_observe(void *state, const mu_world_actors *view);
const mu_monster_spec *mu_monsters_demo_spec(void *state, int32_t index);
#endif
