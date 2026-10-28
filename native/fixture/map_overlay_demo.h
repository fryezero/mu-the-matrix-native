#ifndef MU_MAP_OVERLAY_DEMO_H
#define MU_MAP_OVERLAY_DEMO_H
#include "../../reconstructed/map/map.h"
struct mu_lang;
struct mu_fixture;
void *mu_fixture_behavior_state(struct mu_fixture *, const char *);
/* Fixture-only synthetic placement policy. Called once when the offline world opens. */
void mu_map_overlay_demo_world(void *state, const struct mu_lang *lang, const mu_gate *gates, int count,
                               int world);
void mu_map_overlay_demo_npc(void *state, int key, const char *name, int x, int y);
#endif
